from typing import Any

import aiohttp
from tenacity import retry, stop_after_attempt, wait_fixed

from ..base import BadRequestError, NotFoundError, RagflowAPIBase, ServerError
from ..Search.search_dto import (
    CreateSearchAppRequest,
    DeleteSearchAppRequest,
    DocumentAggregation,
    ListSearchAppRequest,
    RetrievalChunk,
    RetrievalRequest,
    RetrievalResponse,
    UpdateSearchAppRequest,
)


class SearchRagflowAPI(RagflowAPIBase):
    """
    Search application and retrieval API.

    Provides methods for creating and managing search apps, and performing
    chunk retrieval operations with optional knowledge graph integration.
    """

    def __init__(self, hostname: str, public_key: str = None, public_key_path: str = None, version: str = "v1"):
        """Initialize the Search API client."""
        super().__init__(hostname, public_key, public_key_path, version)
        self.search_base_url = f"{hostname}/{version}/search"
        self.chunk_base_url = f"{hostname}/{version}/chunk"

    @RagflowAPIBase.requires_token
    @retry(stop=stop_after_attempt(3), wait=wait_fixed(1))
    async def create_search_app(self, create_request: CreateSearchAppRequest, token: str, **kwargs) -> dict[str, Any]:
        """
        Create a new search application.

        Args:
            create_request: CreateSearchAppRequest with search app configuration
            token: Valid authentication token
            **kwargs: Additional optional parameters

        Returns:
            Dictionary containing the created search app information

        Raises:
            ServerError: If server returns non-200 status
            BadRequestError: If creation fails

        Example:
            >>> from ragflow_api.Search import CreateSearchAppRequest
            >>> req = CreateSearchAppRequest(name="My Search App")
            >>> search_app = await api.create_search_app(req, token)
        """
        url = f"{self.search_base_url}/create"
        headers = {"Authorization": f"{token}", "Content-Type": "application/json"}
        async with (
            aiohttp.ClientSession() as session,
            session.post(url, json=create_request.model_dump(exclude_none=True), headers=headers) as response,
        ):
            if response.status != 200:
                raise ServerError(f"Create search app failed with status {response.status}")
            res_json = await response.json()
            if res_json.get("code") != 0:
                raise BadRequestError(f"Create search app failed: {res_json.get('message')}")
            return res_json.get("data", {})

    @RagflowAPIBase.requires_token
    @retry(stop=stop_after_attempt(3), wait=wait_fixed(1))
    async def update_search_app(self, update_request: UpdateSearchAppRequest, token: str, **kwargs) -> dict[str, Any]:
        """
        Update an existing search application's configuration.

        Args:
            update_request: UpdateSearchAppRequest with search app ID and fields to update
            token: Valid authentication token
            **kwargs: Additional optional parameters

        Returns:
            Dictionary containing the updated search app information

        Raises:
            ServerError: If server returns non-200 status
            BadRequestError: If update fails

        Example:
            >>> from ragflow_api.Search import UpdateSearchAppRequest
            >>> req = UpdateSearchAppRequest(search_id="search_123", name="Updated Name")
            >>> result = await api.update_search_app(req, token)
        """
        url = f"{self.search_base_url}/update"
        headers = {"Authorization": f"{token}", "Content-Type": "application/json"}
        async with (
            aiohttp.ClientSession() as session,
            session.post(url, json=update_request.model_dump(exclude_none=True), headers=headers) as response,
        ):
            if response.status != 200:
                raise ServerError(f"Update search app failed with status {response.status}")
            res_json = await response.json()
            if res_json.get("code") != 0:
                raise BadRequestError(f"Update search app failed: {res_json.get('message')}")
            return res_json.get("data", {})

    @RagflowAPIBase.requires_token
    @retry(stop=stop_after_attempt(3), wait=wait_fixed(1))
    async def detail_search_app(self, search_id: str, token: str, **kwargs) -> dict[str, Any]:
        """
        Retrieve detailed information about a specific search application.

        Args:
            search_id: The search app ID to retrieve details for
            token: Valid authentication token
            **kwargs: Additional optional parameters

        Returns:
            Dictionary containing search app details and configuration

        Raises:
            ServerError: If server returns non-200 status
            NotFoundError: If search app not found

        Example:
            >>> details = await api.detail_search_app("search_123", token)
            >>> print(details["name"])
        """
        url = f"{self.search_base_url}/detail"
        headers = {"Authorization": f"{token}"}
        params = {"search_id": search_id}
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params, headers=headers) as response:
                if response.status != 200:
                    raise ServerError(f"Get search app detail failed with status {response.status}")
                res_json = await response.json()
                if res_json.get("code") != 0:
                    raise NotFoundError(f"Get search app detail failed: {res_json.get('message')}")
                return res_json.get("data", {})

    @RagflowAPIBase.requires_token
    @retry(stop=stop_after_attempt(3), wait=wait_fixed(1))
    async def list_search_apps(self, list_request: ListSearchAppRequest, token: str, **kwargs) -> dict[str, Any]:
        """
        List search applications with pagination and filtering.

        Args:
            list_request: ListSearchAppRequest with pagination and filter options
            token: Valid authentication token
            **kwargs: Additional optional parameters

        Returns:
            Dictionary containing list of search apps and pagination info

        Raises:
            ServerError: If server returns non-200 status
            BadRequestError: If request fails

        Example:
            >>> from ragflow_api.Search import ListSearchAppRequest
            >>> req = ListSearchAppRequest(page=1, page_size=30)
            >>> result = await api.list_search_apps(req, token)
            >>> for app in result.get("searches", []):
            ...     print(app["name"])
        """
        url = f"{self.search_base_url}/list"
        headers = {"Authorization": f"{token}", "Content-Type": "application/json"}

        params = {
            "keywords": list_request.keywords,
            "page": list_request.page,
            "page_size": list_request.page_size,
            "orderby": list_request.orderby,
            "desc": str(list_request.desc).lower(),
        }

        body = {"owner_ids": list_request.owner_ids}

        async with aiohttp.ClientSession() as session:
            async with session.post(url, params=params, json=body, headers=headers) as response:
                if response.status != 200:
                    raise ServerError(f"List search apps failed with status {response.status}")
                res_json = await response.json()
                if res_json.get("code") != 0:
                    raise BadRequestError(f"List search apps failed: {res_json.get('message')}")
                return res_json.get("data", {})

    @RagflowAPIBase.requires_token
    @retry(stop=stop_after_attempt(3), wait=wait_fixed(1))
    async def rm_search_app(self, rm_request: DeleteSearchAppRequest, token: str, **kwargs) -> bool:
        """
        Delete a search application.

        Args:
            rm_request: DeleteSearchAppRequest containing search app ID to delete
            token: Valid authentication token
            **kwargs: Additional optional parameters

        Returns:
            True if deletion successful, False otherwise

        Raises:
            ServerError: If server returns non-200 status

        Example:
            >>> from ragflow_api.Search import DeleteSearchAppRequest
            >>> req = DeleteSearchAppRequest(search_id="search_123")
            >>> success = await api.rm_search_app(req, token)
        """
        url = f"{self.search_base_url}/rm"
        headers = {"Authorization": f"{token}", "Content-Type": "application/json"}
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=rm_request.model_dump(exclude_none=True), headers=headers) as response:
                if response.status != 200:
                    raise ServerError(f"Remove search app failed with status {response.status}")
                res_json = await response.json()
                return res_json.get("code") == 0

    @RagflowAPIBase.requires_token
    @retry(stop=stop_after_attempt(3), wait=wait_fixed(1))
    async def retrieval(self, retrieval_request: RetrievalRequest, token: str, **kwargs) -> RetrievalResponse:
        """
        Execute chunk retrieval/search operation.
        make sure to use the api key no thte token.

        This provides generic search capabilities across datasets with optional
        knowledge graph integration. Can use a search app configuration via search_id
        or provide raw search parameters.

        Args:
            retrieval_request: RetrievalRequest with search parameters
            token: Valid authentication token
            **kwargs: Additional optional parameters

        Returns:
            Dictionary containing search results with chunks and relevance scores

        Raises:
            ServerError: If server returns non-200 status
            BadRequestError: If retrieval fails

        Example:
            >>> from ragflow_api.Search import RetrievalRequest
            >>> req = RetrievalRequest(
            ...     dataset_ids=["dataset_123"],
            ...     question="What is RAGFlow?",
            ...     use_kg=True,
            ...     top_k=10
            ... )
            >>> results = await api.retrieval(req, token)
            >>> for chunk in results.chunks:
            ...     print(f"Score: {chunk.similarity}, Content: {chunk.content}")
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
            if not isinstance(data, dict):
                return RetrievalResponse(chunks=[], doc_aggs=[], total=0)
            # SDK renames fields: chunk_id→id, content_with_weight→content, doc_id→document_id,
            # important_kwd→important_keywords, question_kwd→questions, docnm_kwd→document_keyword, kb_id→dataset_id
            chunks_raw = data.get("chunks", [])
            doc_aggs_raw = data.get("doc_aggs", {})
            total = data.get("total", len(chunks_raw) if isinstance(chunks_raw, list) else 0)
            chunks = []
            for c in chunks_raw if isinstance(chunks_raw, list) else []:
                if isinstance(c, dict):
                    dataset_id_val = c.get("dataset_id") or c.get("kb_id") or ""
                    if isinstance(dataset_id_val, list):
                        dataset_id_val = dataset_id_val[0] if dataset_id_val else ""
                    chunks.append(
                        RetrievalChunk(
                            id=c.get("id") or c.get("chunk_id"),
                            content=c.get("content") or c.get("content_with_weight") or "",
                            document_id=c.get("document_id") or c.get("doc_id") or "",
                            dataset_id=dataset_id_val,
                            similarity=c.get("similarity") or 0.0,
                            important_keywords=c.get("important_keywords") or c.get("important_kwd") or [],
                            questions=c.get("questions") or c.get("question_kwd") or [],
                            document_keyword=c.get("document_keyword") or c.get("docnm_kwd") or "",
                            image_id=c.get("image_id") or c.get("img_id"),
                            positions=c.get("positions") or c.get("position_int") or [],
                        )
                    )
            doc_aggs = []
            # doc_aggs may be a dict {doc_id: {doc_name, count}} or a list
            if isinstance(doc_aggs_raw, dict):
                for doc_id, info in doc_aggs_raw.items():
                    if isinstance(info, dict):
                        doc_aggs.append(
                            DocumentAggregation(
                                count=info.get("count", 0),
                                doc_id=doc_id,
                                doc_name=info.get("doc_name") or info.get("name") or "",
                            )
                        )
            elif isinstance(doc_aggs_raw, list):
                for d in doc_aggs_raw:
                    if isinstance(d, dict):
                        doc_aggs.append(
                            DocumentAggregation(
                                count=d.get("count", 0),
                                doc_id=d.get("doc_id") or d.get("id") or "",
                                doc_name=d.get("doc_name") or d.get("name") or "",
                            )
                        )
            return RetrievalResponse(chunks=chunks, doc_aggs=doc_aggs, total=total)
