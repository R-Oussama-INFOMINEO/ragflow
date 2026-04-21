from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field
from ragflow_api.common.entities import ChunkEntity, DocumentEntity
from ragflow_api.common.dto import BasePaginationRequest, BasePaginationResponse


class UploadDocumentRequest(BaseModel):
    kb_id: str = Field(..., description="Knowledge base ID")


class RunDocumentRequest(BaseModel):
    doc_ids: List[str] = Field(..., description="List of document IDs")
    run: Union[str, int] = Field(..., description="Run status (e.g., '1' for running, '2' for cancel)")
    delete: Optional[bool] = Field(False, description="Whether to delete existing chunks before running")
    apply_kb: Optional[bool] = Field(False, description="Whether to apply KB parser config")


class ChangeStatusRequest(BaseModel):
    doc_ids: List[str] = Field(..., description="List of document IDs")
    status: str = Field(..., description="Status to set ('0' or '1')")


class DocumentInfosRequest(BaseModel):
    doc_ids: List[str] = Field(..., description="List of document IDs")


class MetadataSummaryRequest(BaseModel):
    kb_id: str = Field(..., description="Knowledge base ID")
    doc_ids: Optional[List[str]] = Field(None, description="Optional list of document IDs")


class ListDocumentsRequest(BasePaginationRequest):
    kb_id: str = Field(..., description="Knowledge base ID")
    keywords: Optional[str] = Field("", description="Keywords for filtering")
    create_time_from: Optional[int] = Field(0)
    create_time_to: Optional[int] = Field(0)

    # Body parameters
    return_empty_metadata: bool = Field(False)
    run_status: List[str] = Field(default_factory=list)
    types: List[str] = Field(default_factory=list)
    suffix: List[str] = Field(default_factory=list)
    metadata_condition: Dict[str, Any] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class DeleteDocumentsRequest(BaseModel):
    doc_id: Union[str, List[str]] = Field(..., description="Document ID or list of document IDs to delete")


class ListChunksRequest(BaseModel):
    doc_id: str = Field(..., description="Document ID")
    page: int = Field(1, ge=1)
    size: int = Field(30, ge=1)
    keywords: Optional[str] = Field("", description="Keywords for filtering")
    available_int: Optional[int] = Field(None, description="Filter by available status")


class CreateChunkRequest(BaseModel):
    doc_id: str = Field(..., description="Document ID")
    content_with_weight: str = Field(..., description="Content of the chunk")
    important_kwd: Optional[List[str]] = Field(default_factory=list)
    question_kwd: Optional[List[str]] = Field(default_factory=list)
    tag_feas: Optional[Dict[str, Any]] = Field(None)


class DeleteChunksRequest(BaseModel):
    doc_id: str = Field(..., description="Document ID")
    chunk_ids: Union[str, List[str]] = Field(..., description="Chunk ID or list of chunk IDs to delete")


class ThumbnailsRequest(BaseModel):
    doc_ids: List[str] = Field(..., description="List of document IDs")


class SetMetadataRequest(BaseModel):
    """Request to set metadata for a document.

    Metadata values must be one of:
    - str, int, float
    - List[str], List[int], List[float]

    Example:
        {"category": "report", "year": 2024, "tags": ["finance", "q1"]}
    """

    doc_id: str = Field(..., description="Document ID")
    meta: Dict[str, Any] = Field(..., description="Metadata dictionary with str/int/float values or lists")


class WebCrawlRequest(BaseModel):
    """Request to crawl a URL and create a document."""
    kb_id: str = Field(..., description="Knowledge base ID")
    name: str = Field(..., description="Document name")
    url: str = Field(..., description="URL to crawl")


class CreateDocumentRequest(BaseModel):
    """Request to create an empty/virtual document."""
    kb_id: str = Field(..., description="Knowledge base ID")
    name: str = Field(..., description="Document name")


class RenameDocumentRequest(BaseModel):
    """Request to rename a document."""
    doc_id: str = Field(..., description="Document ID")
    name: str = Field(..., description="New document name")


class ChangeParserRequest(BaseModel):
    """Request to change parser configuration for a document."""
    doc_id: str = Field(..., description="Document ID")
    pipeline_id: Optional[str] = Field(None, description="Pipeline ID")
    parser_id: Optional[str] = Field(None, description="Parser ID (e.g., 'naive', 'deepdoc')")
    parser_config: Optional[Dict[str, Any]] = Field(None, description="Parser configuration settings")


class UpdateMetadataSettingsRequest(BaseModel):
    """Request to update metadata settings (schema) for a document."""
    doc_id: str = Field(..., description="Document ID")
    metadata: Dict[str, Any] = Field(..., description="Metadata schema/settings")


class GetFiltersRequest(BaseModel):
    """Request to get filter aggregation statistics for a knowledge base."""
    kb_id: str = Field(..., description="Knowledge base ID")
    keywords: Optional[str] = Field("", description="Search keywords")
    run_status: List[str] = Field(default_factory=list, description="Filter by run status")
    types: List[str] = Field(default_factory=list, description="Filter by file types")
    suffix: List[str] = Field(default_factory=list, description="Filter by file suffixes")


class BatchUpdateMetadataRequest(BaseModel):
    """Request to batch update or delete metadata for multiple documents."""
    kb_id: str = Field(..., description="Knowledge base ID")
    doc_ids: List[str] = Field(..., description="List of document IDs")
    updates: List[Dict[str, Any]] = Field(default_factory=list, description="List of updates: [{key, value}, ...]")
    deletes: List[Dict[str, str]] = Field(default_factory=list, description="List of deletions: [{key}, ...]")


class GetChunkRequest(BaseModel):
    """Request to get a single chunk."""
    chunk_id: str = Field(..., description="Chunk ID")


class UpdateChunkRequest(BaseModel):
    """Request to update a chunk's content and keywords."""
    doc_id: str = Field(..., description="Document ID")
    chunk_id: str = Field(..., description="Chunk ID")
    content_with_weight: str = Field(..., description="New chunk content")
    important_kwd: Optional[List[str]] = Field(None, description="Important keywords")
    question_kwd: Optional[List[str]] = Field(None, description="Question keywords")
    available_int: Optional[int] = Field(None, description="Availability status (0 or 1)")


class SwitchChunkRequest(BaseModel):
    """Request to enable or disable chunks."""
    doc_id: str = Field(..., description="Document ID")
    chunk_ids: List[str] = Field(..., description="List of chunk IDs")
    available_int: int = Field(..., description="Availability status: 1=enabled, 0=disabled")


# Response DTOs (only for complex returns - methods returning primitives return them directly)

class UploadDocumentResponse(BaseModel):
    """Response from uploading documents."""
    documents: List[DocumentEntity] = Field(..., description="List of uploaded documents")


class CreateDocumentResponse(BaseModel):
    """Response from creating a document."""
    document: DocumentEntity


class UpdateMetadataSettingsResponse(BaseModel):
    """Response from updating metadata settings."""
    document: DocumentEntity


class GetFiltersResponse(BaseModel):
    """Response from getting filter statistics."""
    total: int = Field(..., description="Total document count")
    filter: Dict[str, Any] = Field(..., description="Filter aggregation stats (status counts, type counts)")


class BatchUpdateMetadataResponse(BaseModel):
    """Response from batch metadata update."""
    updated: int = Field(..., description="Number of documents updated")
    matched_docs: int = Field(..., description="Number of documents matched")


class GetChunkResponse(BaseModel):
    """Response from getting a single chunk."""
    chunk: ChunkEntity


class ListDocumentsResponse(BasePaginationResponse):
    """Response from listing documents."""
    documents: List[DocumentEntity] = Field(..., description="List of documents")


class ListChunksResponse(BaseModel):
    """Response from listing chunks."""
    total: int = Field(..., description="Total chunk count")
    chunks: List[ChunkEntity] = Field(..., description="List of chunks")
    doc: DocumentEntity = Field(..., description="Parent document info")
