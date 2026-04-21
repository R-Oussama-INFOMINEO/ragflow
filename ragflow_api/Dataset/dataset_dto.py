from enum import Enum

from pydantic import BaseModel, Field, validator

from ragflow_api.common.dto import BasePaginationRequest, BasePaginationResponse
from ragflow_api.common.entities import (
    Language,
    ParserConfig,
    Permission,
)


class ParserType(str, Enum):
    """Document parser/chunking methods"""

    NAIVE = "naive"  # Default simple chunking
    PRESENTATION = "presentation"  # For presentation files
    LAWS = "laws"  # For legal documents
    MANUAL = "manual"  # For manual/documentation
    PAPER = "paper"  # For academic papers
    RESUME = "resume"  # For resumes/CVs
    BOOK = "book"  # For books
    QA = "qa"  # For Q&A format
    TABLE = "table"  # For table-heavy documents
    PICTURE = "picture"  # For image-heavy documents
    ONE = "one"  # Single chunk (no splitting)
    AUDIO = "audio"  # For audio files
    EMAIL = "email"  # For emails
    KNOWLEDGE_GRAPH = "knowledge_graph"  # For knowledge graph extraction
    TAG = "tag"  # For tag-based chunking


class CreateDatasetRequest(BaseModel):
    name: str = Field(..., max_length=128)
    avatar: str | None = Field(None, max_length=65535)
    description: str | None = Field(None, max_length=65535)
    language: Language | None = Field(None, description="Dataset language")
    embd_id: str | None = Field(None, max_length=128, description="Embedding model ID")
    permission: Permission | None = Field(Permission.ME, description="Access permission level")
    parser_id: ParserType | str | None = Field(None, max_length=32, description="Parser/chunking method")
    parser_config: ParserConfig | None = Field(None, description="Parser configuration")
    pipeline_id: str | None = Field(None, max_length=32, description="Pipeline ID (32-char hex)")
    similarity_threshold: float | None = Field(0.2, description="Similarity threshold for retrieval")
    vector_similarity_weight: float | None = Field(0.3, description="Weight for vector similarity")

    @validator("pipeline_id")
    def validate_pipeline_id(cls, v):
        if v is not None and (len(v) != 32 or not all(c in "0123456789abcdef" for c in v.lower())):
            raise ValueError("pipeline_id must be a 32-character lowercase hexadecimal string")
        return v.lower() if v else v


class UpdateDatasetRequest(BaseModel):
    kb_id: str = Field(..., max_length=32, description="Knowledge base ID to update")
    name: str | None = Field(None, max_length=128)
    avatar: str | None = Field(None, max_length=65535)
    description: str | None = Field(None, max_length=65535)
    language: Language | None = Field(None, description="Dataset language")
    embd_id: str | None = Field(None, max_length=128, description="Embedding model ID")
    permission: Permission | None = Field(None, description="Access permission level")
    parser_id: ParserType | str | None = Field(None, max_length=32, description="Parser/chunking method")
    parser_config: ParserConfig | None = Field(None, description="Parser configuration")
    pagerank: int | None = Field(None, ge=0, le=100, description="PageRank weight for retrieval")
    similarity_threshold: float | None = Field(None, description="Similarity threshold for retrieval")
    vector_similarity_weight: float | None = Field(None, description="Weight for vector similarity")
    connectors: list[dict] | None = Field(None, description="Connector configurations for data ingestion")


class DeleteDatasetsRequest(BaseModel):
    kb_id: str


class ListDatasetsRequest(BasePaginationRequest):
    name: str | None = None
    id: str | None = None
    parser_id: str | None = None
    owner_ids: list[str] | None = None


# ============================================================================
# New Request DTOs for Metadata, Tags, and Observability
# ============================================================================


class UpdateMetadataSettingRequest(BaseModel):
    """Update metadata extraction settings for a dataset"""

    kb_id: str = Field(..., max_length=32, description="Knowledge base ID")
    metadata: dict = Field(..., description="Metadata schema definition")
    enable_metadata: bool | None = Field(True, description="Enable metadata extraction")


class ListTagsRequest(BaseModel):
    """List tags from one or more datasets"""

    kb_id: str | None = Field(None, max_length=32, description="Single dataset ID")
    kb_ids: list[str] | None = Field(None, description="Multiple dataset IDs")


class RemoveTagsRequest(BaseModel):
    """Remove specific tags from a dataset"""

    kb_id: str = Field(..., max_length=32, description="Knowledge base ID")
    tags: list[str] = Field(..., description="Tags to remove")


class RenameTagRequest(BaseModel):
    """Rename a tag in a dataset"""

    kb_id: str = Field(..., max_length=32, description="Knowledge base ID")
    from_tag: str = Field(..., description="Current tag name")
    to_tag: str = Field(..., description="New tag name")


class GetMetaRequest(BaseModel):
    """Get flattened metadata from multiple datasets"""

    kb_ids: list[str] = Field(..., description="Dataset IDs to retrieve metadata from")


class GetBasicInfoRequest(BaseModel):
    """Get basic statistics for a dataset"""

    kb_id: str = Field(..., max_length=32, description="Knowledge base ID")


class ListPipelineLogsRequest(BasePaginationRequest):
    """List pipeline operation logs with comprehensive filtering"""

    kb_id: str = Field(..., max_length=32, description="Knowledge base ID")
    keywords: str | None = Field(None, description="Search keywords")
    operation_status: list[str] | None = Field(None, description="Filter by operation status")
    types: list[str] | None = Field(None, description="Filter by file types")
    suffix: list[str] | None = Field(None, description="Filter by file suffixes")
    create_date_from: str | None = Field(None, description="Start date (YYYY-MM-DD)")
    create_date_to: str | None = Field(None, description="End date (YYYY-MM-DD)")


class ListPipelineDatasetLogsRequest(BasePaginationRequest):
    """List dataset-level pipeline operation logs"""

    kb_id: str = Field(..., max_length=32, description="Knowledge base ID")
    operation_status: list[str] | None = Field(None, description="Filter by operation status")
    create_date_from: str | None = Field(None, description="Start date (YYYY-MM-DD)")
    create_date_to: str | None = Field(None, description="End date (YYYY-MM-DD)")


class DeletePipelineLogsRequest(BaseModel):
    """Delete specific pipeline logs"""

    log_ids: list[str] = Field(..., description="Log IDs to delete")


class PipelineLogDetailRequest(BaseModel):
    """Get detailed information for a specific log"""

    log_id: str = Field(..., description="Pipeline log ID")


class UnbindTaskRequest(BaseModel):
    """Unbind/cancel a running task"""

    kb_id: str = Field(..., max_length=32, description="Knowledge base ID")
    pipeline_task_type: str = Field(..., description="Task type to unbind: 'graphrag', 'raptor', or 'mindmap'")


class CheckEmbeddingRequest(BaseModel):
    """Check embedding model compatibility"""

    kb_id: str = Field(..., max_length=32, description="Knowledge base ID")
    embd_id: str = Field(..., description="Embedding model ID to check")
    check_num: int = Field(5, ge=1, le=100, description="Number of chunks to sample")


# ============================================================================
# New Response DTOs
# ============================================================================


class CreateDatasetResponse(BaseModel):
    """Response from dataset creation"""

    kb_id: str = Field(..., description="Created dataset ID")


class KBEntity(BaseModel):
    id: str
    name: str = ""
    description: str | None = ""
    avatar: str | None = None
    tenant_id: str = ""
    nickname: str = ""
    tenant_avatar: str | None = None
    language: str = "English"
    embd_id: str = ""
    permission: str = "me"
    parser_id: str = "naive"
    pipeline_id: str | None = None
    doc_num: int = 0
    token_num: int = 0
    chunk_num: int = 0
    update_time: int | float | str | None = None


class UpdateDatasetResponse(KBEntity):
    """Response from dataset update with full dataset object"""

    parser_config: ParserConfig | None = None
    pagerank: int | None = None
    similarity_threshold: float | None = None
    vector_similarity_weight: float | None = None
    connectors: list[dict] | None = None


class ListDatasetsResponse(BasePaginationResponse):
    """Response from list datasets"""

    kbs: list[KBEntity] = Field(..., description="List of datasets")
    total: int = Field(..., description="Total number of datasets")


class DatasetDetailResponse(KBEntity):
    """Response from get dataset detail with extended information"""

    created_by: str | None = None
    parser_config: ParserConfig = Field(default_factory=ParserConfig)
    pipeline_name: str | None = None
    pipeline_avatar: str | None = None
    similarity_threshold: float | None = None
    vector_similarity_weight: float | None = None
    pagerank: int | None = None
    status: str | None = None
    graphrag_task_id: str | None = None
    graphrag_task_finish_at: str | int | float | None = None
    raptor_task_id: str | None = None
    raptor_task_finish_at: str | int | float | None = None
    mindmap_task_id: str | None = None
    mindmap_task_finish_at: str | int | float | None = None
    create_time: str | int | float | None = None
    # Extended fields
    size: int | None = None
    connectors: list[dict] | None = None


# ... (intermediate classes skipped, assume they are preserved if I don't touch them? No, I must be careful with replace_file_content)
# Better to use multi_replace for separate chunks.


class ListTagsResponse(BaseModel):
    """Response from list tags"""

    tags: list[str] = Field(..., description="List of tag names")


class UpdateMetadataSettingResponse(BaseModel):
    """Response from metadata setting update"""

    id: str
    parser_config: dict


class GetMetaResponse(BaseModel):
    """Response from get metadata"""

    metadata: dict = Field(..., description="Flattened metadata structure")


class BasicInfoResponse(BaseModel):
    """Response from get basic info"""

    total_file_size: int | None = None
    total_file_num: int | None = None
    chunk_num: int | None = None
    document_amount: int | None = None
    # Observed fields
    cancelled: int | None = None
    download: int | None = None
    processing: int | None = None
    success: int | None = None
    failed: int | None = None
    retry: int | None = None


class PipelineLogListResponse(BasePaginationResponse):
    """Response from list pipeline logs"""

    logs: list[dict] = Field(..., description="List of pipeline logs")


class PipelineLogDetailResponse(BaseModel):
    """Response from get pipeline log detail"""

    id: str
    document_id: str | None = None
    kb_id: str
    operation_status: str
    operation_type: str
    create_time: str
    log: str | None = None


class TaskResponse(BaseModel):
    """Response from task creation (GraphRAG, RAPTOR, Mindmap)"""

    task_id: str = Field(..., description="Created task ID")


class TaskStatusResponse(BaseModel):
    """Response from task status check"""

    id: str | None = None
    doc_id: str | None = None
    task_type: str | None = None
    progress: float = Field(default=0.0, ge=-1, le=1, description="Progress from 0 to 1")
    progress_msg: str | None = None
    begin_at: str | None = None
    process_duration: float | None = None
    create_time: str | int | float | None = None
    update_time: str | int | float | None = None


class KnowledgeGraphResponse(BaseModel):
    """Response from knowledge graph retrieval"""

    graph: dict = Field(..., description="Knowledge graph structure")
    mind_map: dict = Field(..., description="Mind map structure")


class CheckEmbeddingResponse(BaseModel):
    """Response from embedding check"""

    summary: dict = Field(..., description="Summary of embedding check")
    results: list[dict] = Field(..., description="Detailed results for each chunk")


# ============================================================================
# Entity Classes for Dataset Module
# ============================================================================
