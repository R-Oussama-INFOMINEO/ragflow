import asyncio
import io
import os
from typing import Any

import aiohttp
from tenacity import retry, stop_after_attempt, wait_fixed

from ragflow_api.common.entities import DocumentEntity
from ragflow_api.Search.search_dto import RetrievalRequest, RetrievalResponse

from ..base import BadRequestError, RagflowAPIBase, ServerError
from ..Document.document_dto import (
    BatchUpdateMetadataRequest,
    BatchUpdateMetadataResponse,
    ChangeParserRequest,
    ChangeStatusRequest,
    CreateChunkRequest,
    CreateDocumentRequest,
    # Response DTOs
    CreateDocumentResponse,
    DeleteChunksRequest,
    DeleteDocumentsRequest,
    DocumentInfosRequest,
    GetChunkRequest,
    GetFiltersRequest,
    GetFiltersResponse,
    ListChunksRequest,
    ListChunksResponse,
    ListDocumentsRequest,
    MetadataSummaryRequest,
    RenameDocumentRequest,
    RunDocumentRequest,
    SetMetadataRequest,
    SwitchChunkRequest,
    ThumbnailsRequest,
    UpdateChunkRequest,
    UpdateMetadataSettingsRequest,
    UpdateMetadataSettingsResponse,
    # New Request DTOs
    WebCrawlRequest,
)


class DocumentRagflowAPI(RagflowAPIBase):
    """
    Document and chunk management API.

    Provides methods for uploading, parsing, listing, and managing documents and their chunks.
    Includes support for thumbnails, images, attachments, and knowledge graph retrieval.
    """

    def __init__(self, hostname: str, public_key: str = None, public_key_path: str = None, version: str = "v1"):
        """Initialize the Document API client."""
        super().__init__(hostname, public_key, public_key_path, version)
        self.doc_base_url = f"{hostname}/{version}/document"
        self.chunk_base_url = f"{hostname}/{version}/chunk"

    @RagflowAPIBase.requires_token
    @retry(stop=stop_after_attempt(3), wait=wait_fixed(1))
    async def upload(self, kb_id: str, file_path: str, token: str, **kwargs) -> list[DocumentEntity]:
        """
        Upload a document file to a dataset.

        Args:
            kb_id: The dataset ID to upload to
            file_path: Local path to the file to upload
            token: Valid authentication token
            **kwargs: Additional optional parameters

        Returns:
            List of dictionaries containing uploaded document information

        Raises:
            ServerError: If server returns non-200 status
            BadRequestError: If upload fails

        Example:
            >>> result = await api.upload("dataset_123", "document.pdf", token)
            >>> doc_id = result[0]["id"]
        """
        url = f"{self.doc_base_url}/upload"
        headers = {"Authorization": f"{token}"}

        data = aiohttp.FormData()
        data.add_field("kb_id", kb_id)

        # Read file asynchronously to avoid blocking the event loop
        def read_file():
            with open(file_path, "rb") as f:
                return f.read()

        file_content = await asyncio.to_thread(read_file)
        data.add_field("file", io.BytesIO(file_content), filename=os.path.basename(file_path))

        async with aiohttp.ClientSession() as session:
            async with session.post(url, data=data, headers=headers) as response:
                if response.status != 200:
                    raise ServerError(f"Upload document failed with status {response.status}")
                res_json = await response.json()
                if res_json.get("code") != 0:
                    raise BadRequestError(f"Upload document failed: {res_json.get('message')}")

                docs = res_json.get("data", [])
                return [DocumentEntity(**doc) for doc in docs]

    @RagflowAPIBase.requires_token
    @retry(stop=stop_after_attempt(3), wait=wait_fixed(1))
    async def run(self, run_request: RunDocumentRequest, token: str, **kwargs) -> bool:
        """
        Start document parsing/processing.

        Args:
            run_request: RunDocumentRequest with document ID(s) to process
            token: Valid authentication token
            **kwargs: Additional optional parameters

        Returns:
            True if processing started successfully, False otherwise

        Raises:
            ServerError: If server returns non-200 status
            BadRequestError: If run fails

        Example:
            >>> from ragflow_api.Document import RunDocumentRequest
            >>> req = RunDocumentRequest(doc_ids=["doc_123"])
            >>> success = await api.run(req, token)
        """
        url = f"{self.doc_base_url}/run"
        headers = {"Authorization": f"{token}", "Content-Type": "application/json"}
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=run_request.model_dump(exclude_none=True), headers=headers) as response:
                if response.status != 200:
                    raise ServerError(f"Run document failed with status {response.status}")
                res_json = await response.json()
                if res_json.get("code") != 0:
                    raise BadRequestError(f"Run document failed: {res_json.get('message')}")
                return res_json.get("code") == 0

    @RagflowAPIBase.requires_token
    @retry(stop=stop_after_attempt(3), wait=wait_fixed(1))
    async def upload_and_parse(self, conversation_id: str, file_path: str, token: str, **kwargs) -> list[str]:
        """
        Upload a document and immediately parse it for a conversation.

        Args:
            conversation_id: The conversation ID to associate with
            file_path: Local path to the file to upload
            token: Valid authentication token
            **kwargs: Additional optional parameters

        Returns:
            List of parsed content strings

        Raises:
            ServerError: If server returns non-200 status
            BadRequestError: If upload and parse fails

        Example:
            >>> content = await api.upload_and_parse("conv_123", "doc.pdf", token)
        """
        url = f"{self.doc_base_url}/upload_and_parse"
        headers = {"Authorization": f"{token}"}

        data = aiohttp.FormData()
        data.add_field("conversation_id", conversation_id)

        # Read file asynchronously to avoid blocking the event loop
        def read_file():
            with open(file_path, "rb") as f:
                return f.read()

        file_content = await asyncio.to_thread(read_file)
        data.add_field("file", io.BytesIO(file_content), filename=os.path.basename(file_path))

        async with aiohttp.ClientSession() as session:
            async with session.post(url, data=data, headers=headers) as response:
                if response.status != 200:
                    raise ServerError(f"Upload and parse failed with status {response.status}")
                res_json = await response.json()
                if res_json.get("code") != 0:
                    raise BadRequestError(f"Upload and parse failed: {res_json.get('message')}")
                return res_json.get("data", [])

    @RagflowAPIBase.requires_token
    @retry(stop=stop_after_attempt(3), wait=wait_fixed(1))
    async def change_status(self, status_request: ChangeStatusRequest, token: str, **kwargs) -> dict[str, Any]:
        """
        Change the processing status of document(s).

        Args:
            status_request: ChangeStatusRequest with document ID(s) and new status
            token: Valid authentication token
            **kwargs: Additional optional parameters

        Returns:
            Dictionary containing status change result

        Raises:
            ServerError: If server returns non-200 status
            BadRequestError: If status change fails

        Example:
            >>> from ragflow_api.Document import ChangeStatusRequest
            >>> req = ChangeStatusRequest(doc_ids=["doc_123"], status="1")
            >>> result = await api.change_status(req, token)
        """
        url = f"{self.doc_base_url}/change_status"
        headers = {"Authorization": f"{token}", "Content-Type": "application/json"}
        async with (
            aiohttp.ClientSession() as session,
            session.post(url, json=status_request.model_dump(exclude_none=True), headers=headers) as response,
        ):
            if response.status != 200:
                raise ServerError(f"Change status failed with status {response.status}")
            res_json = await response.json()
            if res_json.get("code") != 0:
                raise BadRequestError(f"Change status failed: {res_json.get('message')}")
            return res_json.get("data", {})

    @RagflowAPIBase.requires_token
    @retry(stop=stop_after_attempt(3), wait=wait_fixed(1))
    async def doc_infos(self, infos_request: DocumentInfosRequest, token: str, **kwargs) -> list[DocumentEntity]:
        """
        Retrieve detailed information for multiple documents.

        Args:
            infos_request: DocumentInfosRequest with document IDs
            token: Valid authentication token
            **kwargs: Additional optional parameters

        Returns:
            List of dictionaries containing document information

        Raises:
            ServerError: If server returns non-200 status
            BadRequestError: If request fails

        Example:
            >>> from ragflow_api.Document import DocumentInfosRequest
            >>> req = DocumentInfosRequest(doc_ids=["doc_123", "doc_456"])
            >>> docs = await api.doc_infos(req, token)
        """
        url = f"{self.doc_base_url}/infos"
        headers = {"Authorization": f"{token}", "Content-Type": "application/json"}
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=infos_request.model_dump(exclude_none=True), headers=headers) as response:
                if response.status != 200:
                    raise ServerError(f"Get document infos failed with status {response.status}")
                res_json = await response.json()
                if res_json.get("code") != 0:
                    raise BadRequestError(f"Get document infos failed: {res_json.get('message')}")

                docs = res_json.get("data", [])
                return [DocumentEntity(**doc) for doc in docs]

    @RagflowAPIBase.requires_token
    @retry(stop=stop_after_attempt(3), wait=wait_fixed(1))
    async def metadata_summary(self, summary_request: MetadataSummaryRequest, token: str, **kwargs) -> dict[str, Any]:
        """
        Get metadata summary for documents in a dataset.

        Args:
            summary_request: MetadataSummaryRequest with dataset ID
            token: Valid authentication token
            **kwargs: Additional optional parameters

        Returns:
            Dictionary containing metadata summary statistics

        Raises:
            ServerError: If server returns non-200 status
            BadRequestError: If request fails

        Example:
            >>> from ragflow_api.Document import MetadataSummaryRequest
            >>> req = MetadataSummaryRequest(kb_id="dataset_123")
            >>> summary = await api.metadata_summary(req, token)
        """
        url = f"{self.doc_base_url}/metadata/summary"
        headers = {"Authorization": f"{token}", "Content-Type": "application/json"}
        async with (
            aiohttp.ClientSession() as session,
            session.post(url, json=summary_request.model_dump(exclude_none=True), headers=headers) as response,
        ):
            if response.status != 200:
                raise ServerError(f"Get metadata summary failed with status {response.status}")
            res_json = await response.json()
            if res_json.get("code") != 0:
                raise BadRequestError(f"Get metadata summary failed: {res_json.get('message')}")
            return res_json.get("data", {})

    @RagflowAPIBase.requires_token
    @retry(stop=stop_after_attempt(3), wait=wait_fixed(1))
    async def list_docs(self, list_request: ListDocumentsRequest, token: str, **kwargs) -> dict[str, Any]:
        """
        List documents in a dataset with pagination and filtering.

        Args:
            list_request: ListDocumentsRequest with dataset ID and filter options
            token: Valid authentication token
            **kwargs: Additional optional parameters

        Returns:
            Dictionary with 'docs' (list of documents) and 'total' (total count)

        Raises:
            ServerError: If server returns non-200 status
            BadRequestError: If request fails

        Example:
            >>> from ragflow_api.Document import ListDocumentsRequest
            >>> req = ListDocumentsRequest(kb_id="dataset_123", page=1, page_size=30)
            >>> result = await api.list_docs(req, token)
            >>> for doc in result.get("docs", []):
            ...     print(doc["name"])
        """
        url = f"{self.doc_base_url}/list"
        headers = {"Authorization": f"{token}", "Content-Type": "application/json"}

        # Extract query parameters
        params = {
            "kb_id": list_request.kb_id,
            "page": list_request.page,
            "page_size": list_request.page_size,
            "orderby": list_request.orderby,
            "desc": str(list_request.desc).lower(),
        }
        if list_request.keywords:
            params["keywords"] = list_request.keywords
        if list_request.create_time_from:
            params["create_time_from"] = list_request.create_time_from
        if list_request.create_time_to:
            params["create_time_to"] = list_request.create_time_to

        # Body parameters
        body = {
            "return_empty_metadata": list_request.return_empty_metadata,
            "run_status": list_request.run_status,
            "types": list_request.types,
            "suffix": list_request.suffix,
            "metadata_condition": list_request.metadata_condition,
            "metadata": list_request.metadata,
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(url, params=params, json=body, headers=headers) as response:
                if response.status != 200:
                    raise ServerError(f"List documents failed with status {response.status}")
                res_json = await response.json()
                if res_json.get("code") != 0:
                    raise BadRequestError(f"List documents failed: {res_json.get('message')}")
                return res_json.get("data", {})

    @RagflowAPIBase.requires_token
    @retry(stop=stop_after_attempt(3), wait=wait_fixed(1))
    async def rm(self, rm_request: DeleteDocumentsRequest, token: str, **kwargs) -> bool:
        """
        Delete one or more documents.

        Args:
            rm_request: DeleteDocumentsRequest with document ID(s) to delete
            token: Valid authentication token
            **kwargs: Additional optional parameters

        Returns:
            True if deletion successful, False otherwise

        Raises:
            ServerError: If server returns non-200 status

        Example:
            >>> from ragflow_api.Document import DeleteDocumentsRequest
            >>> req = DeleteDocumentsRequest(doc_ids=["doc_123"])
            >>> success = await api.rm(req, token)
        """
        url = f"{self.doc_base_url}/rm"
        headers = {"Authorization": f"{token}", "Content-Type": "application/json"}
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=rm_request.model_dump(exclude_none=True), headers=headers) as response:
                if response.status != 200:
                    raise ServerError(f"Remove documents failed with status {response.status}")
                res_json = await response.json()
                return res_json.get("code") == 0

    @RagflowAPIBase.requires_token
    @retry(stop=stop_after_attempt(3), wait=wait_fixed(1))
    async def download(self, doc_id: str, token: str, **kwargs) -> bytes:
        """
        Download the original document file.

        Args:
            doc_id: The document ID to download
            token: Valid authentication token
            **kwargs: Additional optional parameters

        Returns:
            Binary content of the document file

        Raises:
            ServerError: If server returns non-200 status

        Example:
            >>> content = await api.download("doc_123", token)
            >>> with open("downloaded.pdf", "wb") as f:
            ...     f.write(content)
        """
        url = f"{self.doc_base_url}/get/{doc_id}"
        headers = {"Authorization": f"{token}"}
        async with aiohttp.ClientSession() as session, session.get(url, headers=headers) as response:
            if response.status != 200:
                raise ServerError(f"Download original file failed with status {response.status}")
            return await response.read()

    @RagflowAPIBase.requires_token
    @retry(stop=stop_after_attempt(3), wait=wait_fixed(1))
    async def download_image(self, image_id: str, token: str, **kwargs) -> bytes:
        """
        Download an image extracted from a document.

        Args:
            image_id: The image ID to download
            token: Valid authentication token
            **kwargs: Additional optional parameters

        Returns:
            Binary content of the image file

        Raises:
            ServerError: If server returns non-200 status

        Example:
            >>> image_data = await api.download_image("img_123", token)
            >>> with open("image.png", "wb") as f:
            ...     f.write(image_data)
        """
        url = f"{self.doc_base_url}/image/{image_id}"
        headers = {"Authorization": f"{token}"}
        async with aiohttp.ClientSession() as session, session.get(url, headers=headers) as response:
            if response.status != 200:
                raise ServerError(f"Download image failed with status {response.status}")
            return await response.read()

    @RagflowAPIBase.requires_token
    @retry(stop=stop_after_attempt(3), wait=wait_fixed(1))
    async def get_thumbnails(self, thumbnails_request: ThumbnailsRequest, token: str, **kwargs) -> dict[str, str]:
        """
        Get thumbnail URLs for multiple documents.

        Args:
            thumbnails_request: ThumbnailsRequest with document IDs
            token: Valid authentication token
            **kwargs: Additional optional parameters

        Returns:
            Dictionary mapping document IDs to thumbnail URLs

        Raises:
            ServerError: If server returns non-200 status
            BadRequestError: If request fails

        Example:
            >>> from ragflow_api.Document import ThumbnailsRequest
            >>> req = ThumbnailsRequest(doc_ids=["doc_123", "doc_456"])
            >>> thumbnails = await api.get_thumbnails(req, token)
        """
        url = f"{self.doc_base_url}/thumbnails"
        headers = {"Authorization": f"{token}"}
        params = {"doc_ids": thumbnails_request.doc_ids}
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params, headers=headers) as response:
                if response.status != 200:
                    raise ServerError(f"Get thumbnails failed with status {response.status}")
                res_json = await response.json()
                if res_json.get("code") != 0:
                    raise BadRequestError(f"Get thumbnails failed: {res_json.get('message')}")
                return res_json.get("data", {})

    @RagflowAPIBase.requires_token
    @retry(stop=stop_after_attempt(3), wait=wait_fixed(1))
    async def download_attachment(self, attachment_id: str, token: str, ext: str = "markdown", **kwargs) -> bytes:
        """
        Download a document attachment in specified format.

        Args:
            attachment_id: The attachment ID to download
            token: Valid authentication token
            ext: Export format ("markdown", "txt", etc.), defaults to "markdown"
            **kwargs: Additional optional parameters

        Returns:
            Binary content of the attachment file

        Raises:
            ServerError: If server returns non-200 status

        Example:
            >>> content = await api.download_attachment("attach_123", token, ext="markdown")
            >>> with open("attachment.md", "wb") as f:
            ...     f.write(content)
        """
        url = f"{self.doc_base_url}/download/{attachment_id}"
        headers = {"Authorization": f"{token}"}
        params = {"ext": ext}
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params, headers=headers) as response:
                if response.status != 200:
                    raise ServerError(f"Download attachment failed with status {response.status}")
                return await response.read()

    @RagflowAPIBase.requires_token
    @retry(stop=stop_after_attempt(3), wait=wait_fixed(1))
    async def list_chunks(self, list_request: ListChunksRequest, token: str, **kwargs) -> ListChunksResponse:
        """
        List chunks for a document with pagination.

        Args:
            list_request: ListChunksRequest with document ID and pagination options
            token: Valid authentication token
            **kwargs: Additional optional parameters

        Returns:
            Dictionary containing list of chunks and pagination info

        Raises:
            ServerError: If server returns non-200 status
            BadRequestError: If request fails

        Example:
            >>> from ragflow_api.Document import ListChunksRequest
            >>> req = ListChunksRequest(doc_id="doc_123", page=1, page_size=30)
            >>> result = await api.list_chunks(req, token)
            >>> for chunk in result.get("chunks", []):
            ...     print(chunk["content_with_weight"])
        """
        url = f"{self.chunk_base_url}/list"
        headers = {"Authorization": f"{token}", "Content-Type": "application/json"}
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=list_request.model_dump(exclude_none=True), headers=headers) as response:
                if response.status != 200:
                    raise ServerError(f"List chunks failed with status {response.status}")
                res_json = await response.json()
                if res_json.get("code") != 0:
                    raise BadRequestError(f"List chunks failed: {res_json.get('message')}")

                return ListChunksResponse(**res_json.get("data", {}))

    @RagflowAPIBase.requires_token
    @retry(stop=stop_after_attempt(3), wait=wait_fixed(1))
    async def create_chunk(self, create_request: CreateChunkRequest, token: str, **kwargs) -> dict[str, Any]:
        """
        Create a new chunk for a document.

        Args:
            create_request: CreateChunkRequest with chunk content and metadata
            token: Valid authentication token
            **kwargs: Additional optional parameters

        Returns:
            Dictionary containing the created chunk information

        Raises:
            ServerError: If server returns non-200 status
            BadRequestError: If creation fails

        Example:
            >>> from ragflow_api.Document import CreateChunkRequest
            >>> req = CreateChunkRequest(doc_id="doc_123", content="New chunk content")
            >>> chunk = await api.create_chunk(req, token)
        """
        url = f"{self.chunk_base_url}/create"
        headers = {"Authorization": f"{token}", "Content-Type": "application/json"}
        async with (
            aiohttp.ClientSession() as session,
            session.post(url, json=create_request.model_dump(exclude_none=True), headers=headers) as response,
        ):
            if response.status != 200:
                raise ServerError(f"Create chunk failed with status {response.status}")
            res_json = await response.json()
            if res_json.get("code") != 0:
                raise BadRequestError(f"Create chunk failed: {res_json.get('message')}")
            return res_json.get("data", {})

    @RagflowAPIBase.requires_token
    @retry(stop=stop_after_attempt(3), wait=wait_fixed(1))
    async def get_chunk(self, get_request: GetChunkRequest, token: str, **kwargs) -> dict[str, Any]:
        """
        Retrieve a single chunk by its ID.

        Args:
            get_request: GetChunkRequest with the chunk ID to retrieve
            token: Valid authentication token
            **kwargs: Additional optional parameters

        Returns:
            Dictionary containing the chunk data

        Raises:
            ServerError: If server returns non-200 status
            BadRequestError: If the chunk is not found or request fails

        Example:
            >>> from ragflow_api.Document import GetChunkRequest
            >>> req = GetChunkRequest(chunk_id="chunk123")
            >>> chunk = await api.get_chunk(req, token)
        """
        url = f"{self.chunk_base_url}/get"
        headers = {"Authorization": f"{token}"}
        params = {"chunk_id": get_request.chunk_id}

        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params, headers=headers) as response:
                if response.status != 200:
                    raise ServerError(f"Get chunk failed with status {response.status}")
                res_json = await response.json()
                if res_json.get("code") != 0:
                    raise BadRequestError(f"Get chunk failed: {res_json.get('message')}")
                return res_json.get("data", {})

    @RagflowAPIBase.requires_token
    @retry(stop=stop_after_attempt(3), wait=wait_fixed(1))
    async def update_chunk(self, update_request: UpdateChunkRequest, token: str, **kwargs) -> bool:
        """
        Update an existing chunk's content and keywords.

        Args:
            update_request: UpdateChunkRequest with new content and metadata
            token: Valid authentication token
            **kwargs: Additional optional parameters

        Returns:
            True if update successful, False otherwise

        Raises:
            ServerError: If server returns non-200 status
            BadRequestError: If update fails

        Example:
            >>> from ragflow_api.Document import UpdateChunkRequest
            >>> req = UpdateChunkRequest(doc_id="doc123", chunk_id="chunk456", content_with_weight="New content")
            >>> success = await api.update_chunk(req, token)
        """
        url = f"{self.chunk_base_url}/set"
        headers = {"Authorization": f"{token}", "Content-Type": "application/json"}
        async with (
            aiohttp.ClientSession() as session,
            session.post(url, json=update_request.model_dump(exclude_none=True), headers=headers) as response,
        ):
            if response.status != 200:
                raise ServerError(f"Update chunk failed with status {response.status}")
            res_json = await response.json()
            if res_json.get("code") != 0:
                raise BadRequestError(f"Update chunk failed: {res_json.get('message')}")
            return res_json.get("code") == 0

    @RagflowAPIBase.requires_token
    @retry(stop=stop_after_attempt(3), wait=wait_fixed(1))
    async def switch_chunk(self, switch_request: SwitchChunkRequest, token: str, **kwargs) -> bool:
        """
        Enable or disable multiple chunks.

        Args:
            switch_request: SwitchChunkRequest with chunk IDs and new status
            token: Valid authentication token
            **kwargs: Additional optional parameters

        Returns:
            True if status change successful, False otherwise

        Raises:
            ServerError: If server returns non-200 status
            BadRequestError: If switch fails

        Example:
            >>> from ragflow_api.Document import SwitchChunkRequest
            >>> req = SwitchChunkRequest(doc_id="doc123", chunk_ids=["chunk456"], available_int=1)
            >>> success = await api.switch_chunk(req, token)
        """
        url = f"{self.chunk_base_url}/switch"
        headers = {"Authorization": f"{token}", "Content-Type": "application/json"}
        async with (
            aiohttp.ClientSession() as session,
            session.post(url, json=switch_request.model_dump(exclude_none=True), headers=headers) as response,
        ):
            if response.status != 200:
                raise ServerError(f"Switch chunks failed with status {response.status}")
            res_json = await response.json()
            if res_json.get("code") != 0:
                raise BadRequestError(f"Switch chunks failed: {res_json.get('message')}")
            return res_json.get("code") == 0

    @RagflowAPIBase.requires_token
    @retry(stop=stop_after_attempt(3), wait=wait_fixed(1))
    async def rm_chunks(self, rm_request: DeleteChunksRequest, token: str, **kwargs) -> bool:
        """
        Delete one or more chunks.

        Args:
            rm_request: DeleteChunksRequest with chunk ID(s) to delete
            token: Valid authentication token
            **kwargs: Additional optional parameters

        Returns:
            True if deletion successful, False otherwise

        Raises:
            ServerError: If server returns non-200 status

        Example:
            >>> from ragflow_api.Document import DeleteChunksRequest
            >>> req = DeleteChunksRequest(chunk_ids=["chunk_123"])
            >>> success = await api.rm_chunks(req, token)
        """
        url = f"{self.chunk_base_url}/rm"
        headers = {"Authorization": f"{token}", "Content-Type": "application/json"}
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=rm_request.model_dump(exclude_none=True), headers=headers) as response:
                if response.status != 200:
                    raise ServerError(f"Remove chunks failed with status {response.status}")
                res_json = await response.json()
                return res_json.get("code") == 0

    @RagflowAPIBase.requires_token
    @retry(stop=stop_after_attempt(3), wait=wait_fixed(1))
    async def get_knowledge_graph(self, doc_id: str, token: str, **kwargs) -> dict[str, Any]:
        """
        Retrieve the knowledge graph for a specific document.

        Args:
            doc_id: The document ID to retrieve knowledge graph from
            token: Valid authentication token
            **kwargs: Additional optional parameters

        Returns:
            Dictionary containing knowledge graph nodes and edges for the document

        Raises:
            ServerError: If server returns non-200 status
            BadRequestError: If request fails

        Example:
            >>> kg_data = await api.get_knowledge_graph("doc_123", token)
            >>> nodes = kg_data.get("nodes", [])
            >>> edges = kg_data.get("edges", [])
        """
        url = f"{self.chunk_base_url}/knowledge_graph"
        headers = {"Authorization": f"{token}"}
        params = {"doc_id": doc_id}
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params, headers=headers) as response:
                if response.status != 200:
                    raise ServerError(f"Get knowledge graph failed with status {response.status}")
                res_json = await response.json()
                if res_json.get("code") != 0:
                    raise BadRequestError(f"Get knowledge graph failed: {res_json.get('message')}")
                return res_json.get("data", {})

    @RagflowAPIBase.requires_token
    @retry(stop=stop_after_attempt(3), wait=wait_fixed(1))
    async def set_metadata(self, metadata_request: SetMetadataRequest, token: str, **kwargs) -> bool:
        """
        Set metadata for a document.

        Args:
            metadata_request: SetMetadataRequest with document ID and metadata dict
            token: Valid authentication token
            **kwargs: Additional optional parameters

        Returns:
            True if metadata was set successfully, False otherwise

        Raises:
            ServerError: If server returns non-200 status
            BadRequestError: If metadata format is invalid

        Example:
            >>> from ragflow_api.Document import SetMetadataRequest
            >>> req = SetMetadataRequest(
            ...     doc_id="doc_123",
            ...     meta={"category": "report", "year": 2024, "tags": ["finance", "q1"]}
            ... )
            >>> success = await api.set_metadata(req, token)
        """
        import json

        url = f"{self.doc_base_url}/set_meta"
        headers = {"Authorization": f"{token}", "Content-Type": "application/json"}

        # Server expects meta as JSON string, not object
        body = {"doc_id": metadata_request.doc_id, "meta": json.dumps(metadata_request.meta)}

        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=body, headers=headers) as response:
                if response.status != 200:
                    raise ServerError(f"Set metadata failed with status {response.status}")
                res_json = await response.json()
                if res_json.get("code") != 0:
                    raise BadRequestError(f"Set metadata failed: {res_json.get('message')}")
                return res_json.get("data", False)

    # ============================================================
    # New Document Methods
    # ============================================================

    @RagflowAPIBase.requires_token
    @retry(stop=stop_after_attempt(3), wait=wait_fixed(1))
    async def web_crawl(self, request: WebCrawlRequest, token: str, **kwargs) -> bool:
        """Crawl a URL and create a document from it."""
        url = f"{self.doc_base_url}/web_crawl"
        headers = {"Authorization": f"{token}"}

        data = aiohttp.FormData()
        data.add_field("kb_id", request.kb_id)
        data.add_field("name", request.name)
        data.add_field("url", request.url)

        async with aiohttp.ClientSession() as session:
            async with session.post(url, data=data, headers=headers) as response:
                if response.status != 200:
                    raise ServerError(f"Web crawl failed with status {response.status}")
                res_json = await response.json()
                if res_json.get("code") != 0:
                    raise BadRequestError(f"Web crawl failed: {res_json.get('message')}")
                return res_json.get("data", False)

    @RagflowAPIBase.requires_token
    @retry(stop=stop_after_attempt(3), wait=wait_fixed(1))
    async def create(self, request: CreateDocumentRequest, token: str, **kwargs) -> CreateDocumentResponse:
        """Create an empty/virtual document."""
        url = f"{self.doc_base_url}/create"
        headers = {"Authorization": f"{token}", "Content-Type": "application/json"}
        body = request.model_dump(exclude_none=True)

        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=body, headers=headers) as response:
                if response.status != 200:
                    raise ServerError(f"Create document failed with status {response.status}")
                res_json = await response.json()
                if res_json.get("code") != 0:
                    raise BadRequestError(f"Create document failed: {res_json.get('message')}")

                from ..common.entities import DocumentEntity

                doc_data = res_json.get("data", {})
                return CreateDocumentResponse(document=DocumentEntity(**doc_data))

    @RagflowAPIBase.requires_token
    @retry(stop=stop_after_attempt(3), wait=wait_fixed(1))
    async def rename(self, request: RenameDocumentRequest, token: str, **kwargs) -> bool:
        """Rename a document."""
        url = f"{self.doc_base_url}/rename"
        headers = {"Authorization": f"{token}", "Content-Type": "application/json"}
        body = request.model_dump(exclude_none=True)

        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=body, headers=headers) as response:
                if response.status != 200:
                    raise ServerError(f"Rename document failed with status {response.status}")
                res_json = await response.json()
                if res_json.get("code") != 0:
                    raise BadRequestError(f"Rename document failed: {res_json.get('message')}")
                return res_json.get("data", False)

    @RagflowAPIBase.requires_token
    @retry(stop=stop_after_attempt(3), wait=wait_fixed(1))
    async def change_parser(self, request: ChangeParserRequest, token: str, **kwargs) -> bool:
        """Change parser configuration for a document."""
        url = f"{self.doc_base_url}/change_parser"
        headers = {"Authorization": f"{token}", "Content-Type": "application/json"}
        body = request.model_dump(exclude_none=True)

        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=body, headers=headers) as response:
                if response.status != 200:
                    raise ServerError(f"Change parser failed with status {response.status}")
                res_json = await response.json()
                if res_json.get("code") != 0:
                    raise BadRequestError(f"Change parser failed: {res_json.get('message')}")
                return res_json.get("data", False)

    @RagflowAPIBase.requires_token
    @retry(stop=stop_after_attempt(3), wait=wait_fixed(1))
    async def update_metadata_settings(
        self, request: UpdateMetadataSettingsRequest, token: str, **kwargs
    ) -> UpdateMetadataSettingsResponse:
        """Update metadata settings (schema) for a document."""
        url = f"{self.doc_base_url}/update_metadata_setting"
        headers = {"Authorization": f"{token}", "Content-Type": "application/json"}
        body = request.model_dump(exclude_none=True)

        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=body, headers=headers) as response:
                if response.status != 200:
                    raise ServerError(f"Update metadata settings failed with status {response.status}")
                res_json = await response.json()
                if res_json.get("code") != 0:
                    raise BadRequestError(f"Update metadata settings failed: {res_json.get('message')}")

                from ..common.entities import DocumentEntity

                doc_data = res_json.get("data", {})
                return UpdateMetadataSettingsResponse(document=DocumentEntity(**doc_data))

    @RagflowAPIBase.requires_token
    @retry(stop=stop_after_attempt(3), wait=wait_fixed(1))
    async def get_filters(self, request: GetFiltersRequest, token: str, **kwargs) -> GetFiltersResponse:
        """Get filter aggregation statistics for a knowledge base."""
        url = f"{self.doc_base_url}/filter"
        headers = {"Authorization": f"{token}", "Content-Type": "application/json"}
        body = request.model_dump(exclude_none=True)

        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=body, headers=headers) as response:
                if response.status != 200:
                    raise ServerError(f"Get filters failed with status {response.status}")
                res_json = await response.json()
                if res_json.get("code") != 0:
                    raise BadRequestError(f"Get filters failed: {res_json.get('message')}")

                data = res_json.get("data", {})
                return GetFiltersResponse(total=data.get("total", 0), filter=data.get("filter", {}))

    @RagflowAPIBase.requires_token
    @retry(stop=stop_after_attempt(3), wait=wait_fixed(1))
    async def batch_update_metadata(
        self, request: BatchUpdateMetadataRequest, token: str, **kwargs
    ) -> BatchUpdateMetadataResponse:
        """Batch update or delete metadata for multiple documents."""
        url = f"{self.doc_base_url}/metadata/update"
        headers = {"Authorization": f"{token}", "Content-Type": "application/json"}
        body = request.model_dump(exclude_none=True)

        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=body, headers=headers) as response:
                if response.status != 200:
                    raise ServerError(f"Batch update metadata failed with status {response.status}")
                res_json = await response.json()
                if res_json.get("code") != 0:
                    raise BadRequestError(f"Batch update metadata failed: {res_json.get('message')}")

                data = res_json.get("data", {})
                return BatchUpdateMetadataResponse(
                    updated=data.get("updated", 0), matched_docs=data.get("matched_docs", 0)
                )

    @RagflowAPIBase.requires_token
    @retry(stop=stop_after_attempt(3), wait=wait_fixed(1))
    async def upload_with_metadata(
        self, kb_id: str, file_path: str, token: str, metadata: dict[str, Any] | None = None, **kwargs
    ) -> list[dict[str, Any]]:
        """
        Upload a document and set metadata in one operation.
        This is a convenience method combining upload() and set_metadata().

        Args:
            kb_id: The dataset ID to upload to
            file_path: Local path to the file to upload
            token: Valid authentication token
            metadata: Optional metadata dict to attach to the document
            **kwargs: Additional optional parameters

        Returns:
            List of dicts with document info and metadata status:
            [{"id": "doc_123", "name": "file.pdf", ..., "metadata_set": True}]

        Raises:
            ServerError: If server returns non-200 status
            BadRequestError: If upload or metadata setting fails

        Note:
            If metadata setting fails, the document is still uploaded successfully.
            The returned dict will include "metadata_set": False and "metadata_error": "..."

        Example:
            >>> docs = await api.upload_with_metadata(
            ...     kb_id="dataset_123",
            ...     file_path="report.pdf",
            ...     token=token,
            ...     metadata={"category": "report", "year": 2024, "tags": ["finance"]}
            ... )
            >>> print(f"Uploaded: {docs[0]['name']}, metadata set: {docs[0]['metadata_set']}")

            # Filter documents by metadata using list_docs
            >>> from ragflow_api.Document import ListDocumentsRequest
            >>> result = await api.list_docs(
            ...     ListDocumentsRequest(
            ...         kb_id="dataset_123",
            ...         metadata={"category": ["report"], "year": [2024]}
            ...     ),
            ...     token
            ... )
        """
        import logging

        from .document_dto import SetMetadataRequest

        # Upload the document first
        uploaded_docs = await self.upload(kb_id, file_path, token, **kwargs)

        # If no metadata provided, return upload result with metadata_set=False
        if not metadata:
            return [{**doc.model_dump(), "metadata_set": False} for doc in uploaded_docs]

        # Try to set metadata for each uploaded document
        results = []
        for doc in uploaded_docs:
            doc_id = doc.id
            metadata_set = False
            metadata_error = None
            try:
                meta_req = SetMetadataRequest(doc_id=doc_id, meta=metadata)
                success = await self.set_metadata(meta_req, token, **kwargs)
                metadata_set = success
            except Exception as e:
                # Log error but don't fail the whole operation
                logging.warning(f"Failed to set metadata for document {doc_id}: {e}")
                metadata_set = False
                metadata_error = str(e)

            doc_dict = doc.model_dump()
            doc_dict["metadata_set"] = metadata_set
            if metadata_error:
                doc_dict["metadata_error"] = metadata_error
            results.append(doc_dict)

        return results

    @RagflowAPIBase.requires_token
    @retry(stop=stop_after_attempt(3), wait=wait_fixed(1))
    async def retrieval(self, retrieval_request: RetrievalRequest, token: str, **kwargs) -> RetrievalResponse:
        """
        Execute chunk retrieval/search operation with document scope context.
        This provides capabilities like RAPTOR, Knowledge Graph (KG), and TOC enhancements.

        Args:
            retrieval_request: RetrievalRequest with search parameters
            token: Valid authentication token
            **kwargs: Additional optional parameters

        Returns:
            RetrievalResponse containing chunks and metadata

        Raises:
            ServerError: If server returns non-200 status
            BadRequestError: If retrieval fails

        Example:
            >>> from ragflow_api.Search.search_dto import RetrievalRequest
            >>> req = RetrievalRequest(dataset_ids=["dataset_123"], question="What is RAGFlow?")
            >>> results = await api.retrieval(req, token)
        """
        url = f"{self.hostname}/api/v1/retrieval"
        headers = {"Authorization": f"{token}", "Content-Type": "application/json"}
        async with (
            aiohttp.ClientSession() as session,
            session.post(url, json=retrieval_request.model_dump(exclude_none=True), headers=headers) as response,
        ):
            if response.status != 200:
                raise ServerError(f"Retrieval failed with status {response.status}")
            res_json = await response.json()
            if res_json.get("code") != 0:
                raise BadRequestError(f"Retrieval failed: {res_json.get('message')}")

            data = res_json.get("data", {})
            return RetrievalResponse(**data)
