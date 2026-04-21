import aiohttp
from tenacity import retry, stop_after_attempt, wait_fixed

from ..base import BadRequestError, NotFoundError, RagflowAPIBase, ServerError
from ..Dataset.dataset_dto import (
    BasicInfoResponse,
    CheckEmbeddingRequest,
    CheckEmbeddingResponse,
    # Requests
    CreateDatasetRequest,
    CreateDatasetResponse,
    DatasetDetailResponse,
    DeleteDatasetsRequest,
    DeletePipelineLogsRequest,
    GetBasicInfoRequest,
    GetMetaRequest,
    GetMetaResponse,
    KnowledgeGraphResponse,
    ListDatasetsRequest,
    ListDatasetsResponse,
    ListPipelineDatasetLogsRequest,
    ListPipelineLogsRequest,
    ListTagsRequest,
    ListTagsResponse,
    PipelineLogDetailRequest,
    PipelineLogDetailResponse,
    PipelineLogListResponse,
    RemoveTagsRequest,
    RenameTagRequest,
    TaskResponse,
    TaskStatusResponse,
    UnbindTaskRequest,
    UpdateDatasetRequest,
    UpdateDatasetResponse,
    UpdateMetadataSettingRequest,
    UpdateMetadataSettingResponse,
)


class DatasetRagflowAPI(RagflowAPIBase):
    """
    Dataset (Knowledge Base) management API.

    Provides methods for creating, updating, deleting, and listing datasets,
    as well as constructing and managing knowledge graphs, RAPTOR summaries, and mind maps.
    """

    def __init__(self, hostname: str, public_key: str = None, public_key_path: str = None, version: str = "v1"):
        """Initialize the Dataset API client."""
        super().__init__(hostname, public_key, public_key_path, version)
        self.dataset_url = f"{hostname}/{version}/kb"

    @RagflowAPIBase.requires_token
    @retry(stop=stop_after_attempt(3), wait=wait_fixed(1))
    async def create_dataset(
        self, create_dataset_request: CreateDatasetRequest, token: str, **kwargs
    ) -> CreateDatasetResponse:
        """
        Create a new dataset (knowledge base).

        Args:
            create_dataset_request: CreateDatasetRequest containing dataset configuration
            token: Valid authentication token
            **kwargs: Additional optional parameters

        Returns:
            CreateDatasetResponse containing the created dataset information including id.

        Raises:
            ServerError: If server returns non-200 status
            BadRequestError: If dataset creation fails

        Example:
            >>> from ragflow_api.Dataset import CreateDatasetRequest, ParserType
            >>> api = DatasetRagflowAPI("http://localhost:9380")
            >>> req = CreateDatasetRequest(name="My Dataset", parser_id=ParserType.MANUAL)
            >>> dataset = await api.create_dataset(req, token)
        """
        url = f"{self.dataset_url}/create"
        headers = {"Authorization": f"{token}", "Content-Type": "application/json"}
        async with (
            aiohttp.ClientSession() as session,
            session.post(url, json=create_dataset_request.model_dump(exclude_none=True), headers=headers) as response,
        ):
            if response.status != 200:
                raise ServerError(f"Create dataset failed with status {response.status}")
            res_json = await response.json()
            if res_json.get("code") != 0:
                raise BadRequestError(f"Create dataset failed: {res_json.get('message')}")
            return CreateDatasetResponse(kb_id=res_json.get("data", {}).get("kb_id"))

    @RagflowAPIBase.requires_token
    @retry(stop=stop_after_attempt(3), wait=wait_fixed(1))
    async def update_dataset(
        self, update_dataset_request: UpdateDatasetRequest, token: str, **kwargs
    ) -> UpdateDatasetResponse:
        """
        Update an existing dataset's configuration.

        Args:
            update_dataset_request: UpdateDatasetRequest with dataset ID and fields to update
            token: Valid authentication token
            **kwargs: Additional optional parameters

        Returns:
            UpdateDatasetResponse containing the updated dataset information

        Raises:
            ServerError: If server returns non-200 status
            BadRequestError: If update fails

        Example:
            >>> from ragflow_api.Dataset import UpdateDatasetRequest
            >>> req = UpdateDatasetRequest(kb_id="dataset_123", name="Updated Name")
            >>> result = await api.update_dataset(req, token)
        """
        url = f"{self.dataset_url}/update"
        headers = {"Authorization": f"{token}", "Content-Type": "application/json"}
        async with (
            aiohttp.ClientSession() as session,
            session.post(url, json=update_dataset_request.model_dump(exclude_none=True), headers=headers) as response,
        ):
            if response.status != 200:
                raise ServerError(f"Update dataset failed with status {response.status}")
            res_json = await response.json()
            if res_json.get("code") != 0:
                raise BadRequestError(f"Update dataset failed: {res_json.get('message')}")
            return UpdateDatasetResponse(**res_json.get("data", {}))

    @RagflowAPIBase.requires_token
    @retry(stop=stop_after_attempt(3), wait=wait_fixed(1))
    async def get_dataset_detail(self, dataset_id: str, token: str, **kwargs) -> DatasetDetailResponse:
        """
        Retrieve detailed information about a specific dataset.

        Args:
            dataset_id: The dataset ID to retrieve details for
            token: Valid authentication token
            **kwargs: Additional optional parameters

        Returns:
            DatasetDetailResponse containing dataset details including configuration, statistics, etc.

        Raises:
            ServerError: If server returns non-200 status
            NotFoundError: If dataset not found

        Example:
            >>> details = await api.get_dataset_detail("dataset_123", token)
            >>> print(details.name)
        """
        url = f"{self.dataset_url}/detail"
        headers = {"Authorization": f"{token}"}
        params = {"kb_id": dataset_id}
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params, headers=headers) as response:
                if response.status != 200:
                    raise ServerError(f"Get dataset detail failed with status {response.status}")
                res_json = await response.json()
                if res_json.get("code") != 0:
                    raise NotFoundError(f"Get dataset detail failed: {res_json.get('message')}")
                return DatasetDetailResponse(**res_json.get("data", {}))

    @RagflowAPIBase.requires_token
    @retry(stop=stop_after_attempt(3), wait=wait_fixed(1))
    async def delete_datasets(self, delete_datasets_request: DeleteDatasetsRequest, token: str, **kwargs) -> bool:
        """
        Delete one or more datasets.

        Args:
            delete_datasets_request: DeleteDatasetsRequest containing dataset ID(s) to delete
            token: Valid authentication token
            **kwargs: Additional optional parameters

        Returns:
            True if deletion successful, False otherwise

        Raises:
            ServerError: If server returns non-200 status

        Example:
            >>> from ragflow_api.Dataset import DeleteDatasetsRequest
            >>> req = DeleteDatasetsRequest(kb_id="dataset_123")
            >>> success = await api.delete_datasets(req, token)
        """
        url = f"{self.dataset_url}/rm"
        headers = {"Authorization": f"{token}", "Content-Type": "application/json"}
        async with (
            aiohttp.ClientSession() as session,
            session.post(url, json=delete_datasets_request.model_dump(exclude_none=True), headers=headers) as response,
        ):
            if response.status != 200:
                raise ServerError(f"Delete datasets failed with status {response.status}")
            res_json = await response.json()
            return res_json.get("code") == 0

    @RagflowAPIBase.requires_token
    @retry(stop=stop_after_attempt(3), wait=wait_fixed(1))
    async def list_datasets(
        self, list_datasets_request: ListDatasetsRequest, token: str, **kwargs
    ) -> ListDatasetsResponse:
        """
        List datasets with pagination and filtering.

        Args:
            list_datasets_request: ListDatasetsRequest with pagination and filter options
            token: Valid authentication token
            **kwargs: Additional optional parameters

        Returns:
            ListDatasetsResponse with 'kbs' (list of datasets) and 'total' (total count)

        Raises:
            ServerError: If server returns non-200 status
            BadRequestError: If request fails

        Example:
            >>> from ragflow_api.Dataset import ListDatasetsRequest
            >>> req = ListDatasetsRequest(page=1, page_size=30)
            >>> result = await api.list_datasets(req, token)
            >>> for dataset in result.kbs:
            ...     print(dataset["name"])
        """
        url = f"{self.dataset_url}/list"
        headers = {"Authorization": f"{token}", "Content-Type": "application/json"}
        # Extract query parameters
        params = {
            "page": list_datasets_request.page,
            "page_size": list_datasets_request.page_size,
            "orderby": list_datasets_request.orderby,
            "desc": str(list_datasets_request.desc).lower(),
        }
        if list_datasets_request.name:
            params["keywords"] = list_datasets_request.name
        if list_datasets_request.parser_id:
            params["parser_id"] = list_datasets_request.parser_id

        # Body can contain owner_ids
        body = {}
        if list_datasets_request.owner_ids:
            body["owner_ids"] = list_datasets_request.owner_ids

        async with aiohttp.ClientSession() as session:
            async with session.post(url, params=params, json=body, headers=headers) as response:
                if response.status != 200:
                    raise ServerError(f"List datasets failed with status {response.status}")
                res_json = await response.json()
                if res_json.get("code") != 0:
                    raise BadRequestError(f"List datasets failed: {res_json.get('message')}")
                data = res_json.get("data", {})
                return ListDatasetsResponse(kbs=data.get("kbs", []), total=data.get("total", 0))

    @RagflowAPIBase.requires_token
    @retry(stop=stop_after_attempt(3), wait=wait_fixed(1))
    async def construct_knowledge_graph(self, dataset_id: str, token: str, **kwargs) -> TaskResponse:
        """
        Start knowledge graph construction for a dataset using GraphRAG.

        Args:
            dataset_id: The dataset ID to construct knowledge graph for
            token: Valid authentication token
            **kwargs: Additional optional parameters

        Returns:
            TaskResponse containing construction job information

        Raises:
            ServerError: If server returns non-200 status
            BadRequestError: If construction fails to start

        Example:
            >>> await api.construct_knowledge_graph("dataset_123", token)
            >>> # Monitor status with get_knowledge_graph_status()
        """
        url = f"{self.dataset_url}/run_graphrag"
        headers = {"Authorization": f"{token}", "Content-Type": "application/json"}
        body = {"kb_id": dataset_id}
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=body, headers=headers) as response:
                if response.status != 200:
                    raise ServerError(f"Construct knowledge graph failed with status {response.status}")
                res_json = await response.json()
                if res_json.get("code") != 0:
                    raise BadRequestError(f"Construct knowledge graph failed: {res_json.get('message')}")
                data = res_json.get("data", {})
                print(f"DEBUG: construct_knowledge_graph response data: {data}")
                return TaskResponse(task_id=data.get("graphrag_task_id") or "")

    @RagflowAPIBase.requires_token
    @retry(stop=stop_after_attempt(3), wait=wait_fixed(1))
    async def retrieve_knowledge_graph(self, dataset_id: str, token: str, **kwargs) -> KnowledgeGraphResponse:
        """
        Retrieve the constructed knowledge graph data for a dataset.

        Args:
            dataset_id: The dataset ID to retrieve knowledge graph from
            token: Valid authentication token
            **kwargs: Additional optional parameters

        Returns:
            KnowledgeGraphResponse containing knowledge graph nodes and edges

        Raises:
            ServerError: If server returns non-200 status
            NotFoundError: If knowledge graph not found

        Example:
            >>> kg_data = await api.retrieve_knowledge_graph("dataset_123", token)
            >>> nodes = kg_data.graph.get("nodes", [])
            >>> edges = kg_data.graph.get("edges", [])
        """
        url = f"{self.dataset_url}/{dataset_id}/knowledge_graph"
        headers = {"Authorization": f"{token}"}
        async with aiohttp.ClientSession() as session, session.get(url, headers=headers) as response:
            if response.status != 200:
                raise ServerError(f"Retrieve knowledge graph failed with status {response.status}")
            res_json = await response.json()
            if res_json.get("code") != 0:
                raise NotFoundError(f"Retrieve knowledge graph failed: {res_json.get('message')}")
            return KnowledgeGraphResponse(**res_json.get("data", {}))

    @RagflowAPIBase.requires_token
    @retry(stop=stop_after_attempt(3), wait=wait_fixed(1))
    async def delete_knowledge_graph(self, dataset_id: str, token: str, **kwargs) -> bool:
        """
        Delete the knowledge graph for a dataset.

        Args:
            dataset_id: The dataset ID to delete knowledge graph from
            token: Valid authentication token
            **kwargs: Additional optional parameters

        Returns:
            True if deletion successful, False otherwise

        Raises:
            ServerError: If server returns non-200 status

        Example:
            >>> success = await api.delete_knowledge_graph("dataset_123", token)
        """
        url = f"{self.dataset_url}/{dataset_id}/knowledge_graph"
        headers = {"Authorization": f"{token}"}
        async with aiohttp.ClientSession() as session, session.delete(url, headers=headers) as response:
            if response.status != 200:
                raise ServerError(f"Delete knowledge graph failed with status {response.status}")
            res_json = await response.json()
            return res_json.get("code") == 0

    @RagflowAPIBase.requires_token
    @retry(stop=stop_after_attempt(3), wait=wait_fixed(1))
    async def get_knowledge_graph_status(self, dataset_id: str, token: str, **kwargs) -> TaskStatusResponse:
        """
        Get the construction status of a dataset's knowledge graph.

        Args:
            dataset_id: The dataset ID to check status for
            token: Valid authentication token
            **kwargs: Additional optional parameters

        Returns:
            TaskStatusResponse containing status information including progress (0-1)

        Raises:
            ServerError: If server returns non-200 status
            BadRequestError: If status check fails

        Example:
            >>> status = await api.get_knowledge_graph_status("dataset_123", token)
            >>> if status.progress == 1:
            ...     print("Knowledge graph construction complete")
        """
        url = f"{self.dataset_url}/trace_graphrag"
        headers = {"Authorization": f"{token}"}
        params = {"kb_id": dataset_id}
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params, headers=headers) as response:
                if response.status != 200:
                    raise ServerError(f"Get knowledge graph status failed with status {response.status}")
                res_json = await response.json()
                if res_json.get("code") != 0:
                    raise BadRequestError(f"Get knowledge graph status failed: {res_json.get('message')}")
                return TaskStatusResponse(**res_json.get("data", {}))

    @RagflowAPIBase.requires_token
    @retry(stop=stop_after_attempt(3), wait=wait_fixed(1))
    async def construct_raptor(self, dataset_id: str, token: str, **kwargs) -> TaskResponse:
        """
        Start RAPTOR (Recursive Abstractive Processing for Tree-Organized Retrieval) construction.

        RAPTOR creates hierarchical summaries of document chunks for improved retrieval.

        Args:
            dataset_id: The dataset ID to construct RAPTOR for
            token: Valid authentication token
            **kwargs: Additional optional parameters

        Returns:
            TaskResponse containing construction job information

        Raises:
            ServerError: If server returns non-200 status
            BadRequestError: If construction fails to start

        Example:
            >>> await api.construct_raptor("dataset_123", token)
            >>> # Monitor with get_raptor_status()
        """
        url = f"{self.dataset_url}/run_raptor"
        headers = {"Authorization": f"{token}", "Content-Type": "application/json"}
        body = {"kb_id": dataset_id}
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=body, headers=headers) as response:
                if response.status != 200:
                    raise ServerError(f"Construct RAPTOR failed with status {response.status}")
                res_json = await response.json()
                if res_json.get("code") != 0:
                    raise BadRequestError(f"Construct RAPTOR failed: {res_json.get('message')}")
                return TaskResponse(task_id=res_json.get("data", {}).get("raptor_task_id"))

    @RagflowAPIBase.requires_token
    @retry(stop=stop_after_attempt(3), wait=wait_fixed(1))
    async def get_raptor_status(self, dataset_id: str, token: str, **kwargs) -> TaskStatusResponse:
        """
        Get the construction status of a dataset's RAPTOR summaries.

        Args:
            dataset_id: The dataset ID to check status for
            token: Valid authentication token
            **kwargs: Additional optional parameters

        Returns:
            TaskStatusResponse containing status information including progress (0-1)

        Raises:
            ServerError: If server returns non-200 status
            BadRequestError: If status check fails

        Example:
            >>> status = await api.get_raptor_status("dataset_123", token)
            >>> print(f"RAPTOR progress: {status.progress * 100}%")
        """
        url = f"{self.dataset_url}/trace_raptor"
        headers = {"Authorization": f"{token}"}
        params = {"kb_id": dataset_id}
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params, headers=headers) as response:
                if response.status != 200:
                    raise ServerError(f"Get RAPTOR status failed with status {response.status}")
                res_json = await response.json()
                if res_json.get("code") != 0:
                    raise BadRequestError(f"Get RAPTOR status failed: {res_json.get('message')}")
                return TaskStatusResponse(**res_json.get("data", {}))

    @RagflowAPIBase.requires_token
    @retry(stop=stop_after_attempt(3), wait=wait_fixed(1))
    async def construct_mindmap(self, dataset_id: str, token: str, **kwargs) -> TaskResponse:
        """
        Start mind map generation for a dataset.

        Creates a visual mind map representation of the dataset's content.

        Args:
            dataset_id: The dataset ID to construct mind map for
            token: Valid authentication token
            **kwargs: Additional optional parameters

        Returns:
            TaskResponse containing construction job information

        Raises:
            ServerError: If server returns non-200 status
            BadRequestError: If construction fails to start

        Example:
            >>> await api.construct_mindmap("dataset_123", token)
            >>> # Monitor with get_mindmap_status()
        """
        url = f"{self.dataset_url}/run_mindmap"
        headers = {"Authorization": f"{token}", "Content-Type": "application/json"}
        body = {"kb_id": dataset_id}
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=body, headers=headers) as response:
                if response.status != 200:
                    raise ServerError(f"Construct Mindmap failed with status {response.status}")
                res_json = await response.json()
                if res_json.get("code") != 0:
                    raise BadRequestError(f"Construct Mindmap failed: {res_json.get('message')}")
                return TaskResponse(task_id=res_json.get("data", {}).get("mindmap_task_id"))

    @RagflowAPIBase.requires_token
    @retry(stop=stop_after_attempt(3), wait=wait_fixed(1))
    async def get_mindmap_status(self, dataset_id: str, token: str, **kwargs) -> TaskStatusResponse:
        """
        Get the construction status of a dataset's mind map.

        Args:
            dataset_id: The dataset ID to check status for
            token: Valid authentication token
            **kwargs: Additional optional parameters

        Returns:
            TaskStatusResponse containing status information including progress (0-1)

        Raises:
            ServerError: If server returns non-200 status
            BadRequestError: If status check fails

        Example:
            >>> status = await api.get_mindmap_status("dataset_123", token)
            >>> if status.progress == 1:
            ...     print("Mind map generation complete")
        """
        url = f"{self.dataset_url}/trace_mindmap"
        headers = {"Authorization": f"{token}"}
        params = {"kb_id": dataset_id}
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params, headers=headers) as response:
                if response.status != 200:
                    raise ServerError(f"Get Mindmap status failed with status {response.status}")
                res_json = await response.json()
                if res_json.get("code") != 0:
                    raise BadRequestError(f"Get Mindmap status failed: {res_json.get('message')}")
                return TaskStatusResponse(**res_json.get("data", {}))

    @RagflowAPIBase.requires_token
    @retry(stop=stop_after_attempt(3), wait=wait_fixed(1))
    async def update_metadata_setting(
        self, request: UpdateMetadataSettingRequest, token: str, **kwargs
    ) -> UpdateMetadataSettingResponse:
        """
        Update metadata extraction settings for a dataset.

        Args:
            request: UpdateMetadataSettingRequest containing metadata schema
            token: Valid authentication token
            **kwargs: Additional optional parameters

        Returns:
            UpdateMetadataSettingResponse with updated configuration

        Raises:
            ServerError: If server returns non-200 status
            BadRequestError: If update fails

        Example:
            >>> from ragflow_api.Dataset import UpdateMetadataSettingRequest
            >>> req = UpdateMetadataSettingRequest(kb_id="kb1", metadata={"field": "type"})
            >>> resp = await api.update_metadata_setting(req, token)
        """
        url = f"{self.dataset_url}/update_metadata_setting"
        headers = {"Authorization": f"{token}", "Content-Type": "application/json"}
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=request.model_dump(exclude_none=True), headers=headers) as response:
                if response.status != 200:
                    raise ServerError(f"Update metadata setting failed with status {response.status}")
                res_json = await response.json()
                if res_json.get("code") != 0:
                    raise BadRequestError(f"Update metadata setting failed: {res_json.get('message')}")
                return UpdateMetadataSettingResponse(**res_json.get("data", {}))

    @RagflowAPIBase.requires_token
    @retry(stop=stop_after_attempt(3), wait=wait_fixed(1))
    async def get_meta(self, request: GetMetaRequest, token: str, **kwargs) -> GetMetaResponse:
        """
        Get flattened metadata from multiple datasets.

        Args:
            request: GetMetaRequest containing dataset IDs
            token: Valid authentication token
            **kwargs: Additional optional parameters

        Returns:
            GetMetaResponse with flattened metadata structure

        Example:
            >>> from ragflow_api.Dataset import GetMetaRequest
            >>> req = GetMetaRequest(kb_ids=["kb1", "kb2"])
            >>> meta = await api.get_meta(req, token)
        """
        url = f"{self.dataset_url}/get_meta"
        headers = {"Authorization": f"{token}"}
        # Server expects kb_ids as comma-separated query parameter
        params = {"kb_ids": ",".join(request.kb_ids)}
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params, headers=headers) as response:
                if response.status != 200:
                    raise ServerError(f"Get meta failed with status {response.status}")
                res_json = await response.json()
                if res_json.get("code") != 0:
                    raise BadRequestError(f"Get meta failed: {res_json.get('message')}")
                return GetMetaResponse(metadata=res_json.get("data", {}))

    @RagflowAPIBase.requires_token
    @retry(stop=stop_after_attempt(3), wait=wait_fixed(1))
    async def list_tags(self, request: ListTagsRequest, token: str, **kwargs) -> ListTagsResponse:
        """
        List tags from one or more datasets.

        Args:
            request: ListTagsRequest with dataset ID(s)
            token: Valid authentication token
            **kwargs: Additional optional parameters

        Returns:
            ListTagsResponse containing list of tags
        """
        if request.kb_id:
            url = f"{self.dataset_url}/{request.kb_id}/tags"
        else:
            url = f"{self.dataset_url}/tags"

        headers = {"Authorization": f"{token}", "Content-Type": "application/json"}

        body = {}
        if request.kb_ids:
            body["kb_ids"] = request.kb_ids

        async with aiohttp.ClientSession() as session:
            if request.kb_id:
                async with session.get(url, headers=headers) as response:
                    if response.status != 200:
                        raise ServerError(f"List tags failed with status {response.status}")
                    res_json = await response.json()
                    if res_json.get("code") != 0:
                        raise BadRequestError(f"List tags failed: {res_json.get('message')}")
                    return ListTagsResponse(tags=res_json.get("data", []))
            else:
                async with session.post(url, json=body, headers=headers) as response:
                    if response.status != 200:
                        raise ServerError(f"List tags failed with status {response.status}")
                    res_json = await response.json()
                    if res_json.get("code") != 0:
                        raise BadRequestError(f"List tags failed: {res_json.get('message')}")
                    return ListTagsResponse(tags=res_json.get("data", []))

    @RagflowAPIBase.requires_token
    @retry(stop=stop_after_attempt(3), wait=wait_fixed(1))
    async def remove_tags(self, request: RemoveTagsRequest, token: str, **kwargs) -> bool:
        """
        Remove specific tags from a dataset.

        Args:
            request: RemoveTagsRequest with dataset ID and tags to remove
            token: Valid authentication token
            **kwargs: Additional optional parameters

        Returns:
            True if successful
        """
        url = f"{self.dataset_url}/{request.kb_id}/rm_tags"
        headers = {"Authorization": f"{token}", "Content-Type": "application/json"}
        body = {"tags": request.tags}

        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=body, headers=headers) as response:
                if response.status != 200:
                    raise ServerError(f"Remove tags failed with status {response.status}")
                res_json = await response.json()
                return res_json.get("code") == 0

    @RagflowAPIBase.requires_token
    @retry(stop=stop_after_attempt(3), wait=wait_fixed(1))
    async def rename_tag(self, request: RenameTagRequest, token: str, **kwargs) -> bool:
        """
        Rename a tag in a dataset.

        Args:
            request: RenameTagRequest with dataset ID, old tag, and new tag
            token: Valid authentication token
            **kwargs: Additional optional parameters

        Returns:
            True if successful
        """
        url = f"{self.dataset_url}/{request.kb_id}/rename_tag"
        headers = {"Authorization": f"{token}", "Content-Type": "application/json"}
        body = {"from_tag": request.from_tag, "to_tag": request.to_tag}

        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=body, headers=headers) as response:
                if response.status != 200:
                    raise ServerError(f"Rename tag failed with status {response.status}")
                res_json = await response.json()
                return res_json.get("code") == 0

    @RagflowAPIBase.requires_token
    @retry(stop=stop_after_attempt(3), wait=wait_fixed(1))
    async def get_basic_info(self, request: GetBasicInfoRequest, token: str, **kwargs) -> BasicInfoResponse:
        """
        Get basic statistics for a dataset.

        Args:
            request: GetBasicInfoRequest with dataset ID
            token: Valid authentication token
            **kwargs: Additional optional parameters

        Returns:
            BasicInfoResponse containing statistics
        """
        url = f"{self.dataset_url}/basic_info"
        headers = {"Authorization": f"{token}"}
        params = {"kb_id": request.kb_id}

        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params, headers=headers) as response:
                if response.status != 200:
                    raise ServerError(f"Get basic info failed with status {response.status}")
                res_json = await response.json()
                if res_json.get("code") != 0:
                    raise BadRequestError(f"Get basic info failed: {res_json.get('message')}")
                return BasicInfoResponse(**res_json.get("data", {}))

    @RagflowAPIBase.requires_token
    @retry(stop=stop_after_attempt(3), wait=wait_fixed(1))
    async def list_pipeline_logs(
        self, request: ListPipelineLogsRequest, token: str, **kwargs
    ) -> PipelineLogListResponse:
        """
        List pipeline operation logs with comprehensive filtering.

        Args:
            request: ListPipelineLogsRequest with pagination and filters
            token: Valid authentication token
            **kwargs: Additional optional parameters

        Returns:
            PipelineLogListResponse containing list of logs
        """
        url = f"{self.dataset_url}/list_pipeline_logs"
        headers = {"Authorization": f"{token}", "Content-Type": "application/json"}

        # Query parameters (from URL args in server)
        params = {
            "kb_id": request.kb_id,
            "page": request.page,
            "page_size": request.page_size,
            "orderby": request.orderby,
            "desc": str(request.desc).lower(),
        }
        if request.keywords:
            params["keywords"] = request.keywords
        if request.create_date_from:
            params["create_date_from"] = request.create_date_from
        if request.create_date_to:
            params["create_date_to"] = request.create_date_to

        # Body parameters (from request JSON in server)
        body = {}
        if request.operation_status:
            body["operation_status"] = request.operation_status
        if request.types:
            body["types"] = request.types
        if request.suffix:
            body["suffix"] = request.suffix

        async with aiohttp.ClientSession() as session:
            async with session.post(url, params=params, json=body, headers=headers) as response:
                if response.status != 200:
                    raise ServerError(f"List pipeline logs failed with status {response.status}")
                res_json = await response.json()
                if res_json.get("code") != 0:
                    raise BadRequestError(f"List pipeline logs failed: {res_json.get('message')}")
                data = res_json.get("data", {})
                return PipelineLogListResponse(logs=data.get("logs", []), total=data.get("total", 0))

    @RagflowAPIBase.requires_token
    @retry(stop=stop_after_attempt(3), wait=wait_fixed(1))
    async def list_pipeline_dataset_logs(
        self, request: ListPipelineDatasetLogsRequest, token: str, **kwargs
    ) -> PipelineLogListResponse:
        """
        List dataset-level pipeline operation logs.

        Args:
            request: ListPipelineDatasetLogsRequest with pagination and filters
            token: Valid authentication token
            **kwargs: Additional optional parameters

        Returns:
            PipelineLogListResponse containing list of logs
        """
        url = f"{self.dataset_url}/list_pipeline_dataset_logs"
        headers = {"Authorization": f"{token}", "Content-Type": "application/json"}

        # Query parameters (from URL args in server)
        params = {
            "kb_id": request.kb_id,
            "page": request.page,
            "page_size": request.page_size,
            "orderby": request.orderby,
            "desc": str(request.desc).lower(),
        }
        if request.create_date_from:
            params["create_date_from"] = request.create_date_from
        if request.create_date_to:
            params["create_date_to"] = request.create_date_to

        # Body parameters (from request JSON in server)
        body = {}
        if request.operation_status:
            body["operation_status"] = request.operation_status

        async with aiohttp.ClientSession() as session:
            async with session.post(url, params=params, json=body, headers=headers) as response:
                if response.status != 200:
                    raise ServerError(f"List pipeline dataset logs failed with status {response.status}")
                res_json = await response.json()
                if res_json.get("code") != 0:
                    raise BadRequestError(f"List pipeline dataset logs failed: {res_json.get('message')}")
                data = res_json.get("data", {})
                return PipelineLogListResponse(logs=data.get("logs", []), total=data.get("total", 0))

    @RagflowAPIBase.requires_token
    @retry(stop=stop_after_attempt(3), wait=wait_fixed(1))
    async def delete_pipeline_logs(self, request: DeletePipelineLogsRequest, token: str, **kwargs) -> bool:
        """
        Delete specific pipeline logs.

        Args:
            request: DeletePipelineLogsRequest with log IDs
            token: Valid authentication token
            **kwargs: Additional optional parameters

        Returns:
            True if successful
        """
        url = f"{self.dataset_url}/delete_pipeline_logs"
        headers = {"Authorization": f"{token}", "Content-Type": "application/json"}
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=request.model_dump(exclude_none=True), headers=headers) as response:
                if response.status != 200:
                    raise ServerError(f"Delete pipeline logs failed with status {response.status}")
                res_json = await response.json()
                return res_json.get("code") == 0

    @RagflowAPIBase.requires_token
    @retry(stop=stop_after_attempt(3), wait=wait_fixed(1))
    async def get_pipeline_log_detail(
        self, request: PipelineLogDetailRequest, token: str, **kwargs
    ) -> PipelineLogDetailResponse:
        """
        Get detailed information for a specific log.

        Args:
            request: PipelineLogDetailRequest with log ID
            token: Valid authentication token
            **kwargs: Additional optional parameters

        Returns:
            PipelineLogDetailResponse containing log details
        """
        url = f"{self.dataset_url}/pipeline_log_detail"
        headers = {"Authorization": f"{token}"}
        params = {"log_id": request.log_id}

        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params, headers=headers) as response:
                if response.status != 200:
                    raise ServerError(f"Get pipeline log detail failed with status {response.status}")
                res_json = await response.json()
                if res_json.get("code") != 0:
                    raise BadRequestError(f"Get pipeline log detail failed: {res_json.get('message')}")
                return PipelineLogDetailResponse(**res_json.get("data", {}))

    @RagflowAPIBase.requires_token
    @retry(stop=stop_after_attempt(3), wait=wait_fixed(1))
    async def unbind_task(self, request: UnbindTaskRequest, token: str, **kwargs) -> bool:
        """
        Unbind (cancel) a running task.

        Args:
            request: UnbindTaskRequest with dataset ID and task type
            token: Valid authentication token
            **kwargs: Additional optional parameters

        Returns:
            True if successful
        """
        url = f"{self.dataset_url}/unbind_task"
        headers = {"Authorization": f"{token}", "Content-Type": "application/json"}
        params = {"kb_id": request.kb_id, "pipeline_task_type": request.pipeline_task_type}
        async with aiohttp.ClientSession() as session:
            async with session.delete(url, params=params, headers=headers) as response:
                if response.status != 200:
                    raise ServerError(f"Unbind task failed with status {response.status}")
                res_json = await response.json()
                return res_json.get("code") == 0

    @RagflowAPIBase.requires_token
    @retry(stop=stop_after_attempt(3), wait=wait_fixed(1))
    async def check_embedding(self, request: CheckEmbeddingRequest, token: str, **kwargs) -> CheckEmbeddingResponse:
        """
        Verify embedding model compatibility by sampling chunks.

        Args:
            request: CheckEmbeddingRequest with dataset ID and model ID
            token: Valid authentication token
            **kwargs: Additional optional parameters

        Returns:
            CheckEmbeddingResponse with check results
        """
        url = f"{self.dataset_url}/check_embedding"
        headers = {"Authorization": f"{token}", "Content-Type": "application/json"}
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=request.model_dump(exclude_none=True), headers=headers) as response:
                if response.status != 200:
                    raise ServerError(f"Check embedding failed with status {response.status}")
                res_json = await response.json()
                if res_json.get("code") != 0:
                    raise BadRequestError(f"Check embedding failed: {res_json.get('message')}")
                return CheckEmbeddingResponse(**res_json.get("data", {}))
