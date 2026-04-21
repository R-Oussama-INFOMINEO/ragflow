import asyncio
import time

import aiohttp
from tenacity import retry, stop_after_attempt, wait_fixed

from ..base import BadRequestError, RagflowAPIBase, ServerError
from .video_dto import (
    IngestVideoRequest,
    IngestVideoResponse,
    WaitForCompletionRequest,
    WaitForCompletionResponse,
)


class VideoRagflowAPI(RagflowAPIBase):
    """
    Video ingestion and completion polling API.

    Covers functionality not available in the native RagFlow API:
    registering YouTube URLs as documents (Stellantis custom endpoint)
    and polling until parsing produces chunks.
    """

    def __init__(self, hostname: str, public_key: str = None, public_key_path: str = None, version: str = "v1"):
        """Initialize the Video API client."""
        super().__init__(hostname, public_key, public_key_path, version)
        self.stellantis_base_url = f"{hostname}/api/{version}/stellantis"
        self.dataset_base_url = f"{hostname}/api/{version}/datasets"

    @RagflowAPIBase.requires_token
    @retry(stop=stop_after_attempt(3), wait=wait_fixed(1))
    async def ingest_video(self, request: IngestVideoRequest, token: str) -> IngestVideoResponse:
        """
        Register a YouTube video URL as a document in a dataset.

        Args:
            request: IngestVideoRequest with dataset_id, url, and optional title
            token: Valid authentication token

        Returns:
            IngestVideoResponse with the registered document metadata

        Raises:
            ServerError: If the server returns a 5xx status
            BadRequestError: If the request is rejected (invalid dataset, bad URL, etc.)
        """
        url = f"{self.stellantis_base_url}/ingest/video"
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

        async with aiohttp.ClientSession() as session:
            async with session.post(
                url,
                json=request.model_dump(exclude_none=True),
                headers=headers,
            ) as response:
                if response.status >= 500:
                    raise ServerError(f"Ingest video failed with status {response.status}")
                res_json = await response.json()
                if res_json.get("code") != 0:
                    raise BadRequestError(f"Ingest video failed: {res_json.get('message')}")
                return IngestVideoResponse(**res_json["data"][0])

    @RagflowAPIBase.requires_token
    async def wait_for_completion(self, request: WaitForCompletionRequest, token: str) -> WaitForCompletionResponse:
        """
        Poll a dataset until parsing produces at least one chunk.

        Args:
            request: WaitForCompletionRequest with dataset_id, doc_id, timeout, poll_interval
            token: Valid authentication token

        Returns:
            WaitForCompletionResponse with status ("complete" or "timeout") and chunk_count

        Raises:
            ServerError: If the server returns a 5xx status on a polling attempt
        """
        url = self.dataset_base_url
        headers = {"Authorization": f"Bearer {token}"}
        params = {"page": 1, "page_size": 100}

        start = time.monotonic()

        while True:
            elapsed = time.monotonic() - start
            if elapsed >= request.timeout:
                return WaitForCompletionResponse(
                    status="timeout",
                    doc_id=request.doc_id,
                    chunk_count=0,
                )

            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(url, headers=headers, params=params) as response:
                        if response.status >= 500:
                            raise ServerError(f"Dataset poll failed with status {response.status}")
                        res_json = await response.json()

                for dataset in res_json.get("data", []):
                    if dataset.get("id") == request.dataset_id:
                        chunk_count = dataset.get("chunk_count", 0)
                        if chunk_count > 0:
                            return WaitForCompletionResponse(
                                status="complete",
                                doc_id=request.doc_id,
                                chunk_count=chunk_count,
                            )
                        break

            except ServerError:
                raise
            except Exception:
                pass  # tolerate transient connection/parse errors between ticks

            await asyncio.sleep(request.poll_interval)