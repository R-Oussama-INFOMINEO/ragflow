from typing import Any

from pydantic import BaseModel, Field


class CreateSearchAppRequest(BaseModel):
    name: str = Field(..., description="Search app name")
    description: str | None = Field(None, description="Search app description")


class UpdateSearchAppRequest(BaseModel):
    search_id: str = Field(..., description="Search app ID")
    name: str = Field(..., description="Search app name")
    tenant_id: str = Field(..., description="Tenant ID")
    search_config: dict[str, Any] | None = Field(None, description="Search configuration")


from ragflow_api.common.dto import BasePaginationRequest


class ListSearchAppRequest(BasePaginationRequest):
    keywords: str | None = Field("", description="Keywords for filtering")
    owner_ids: list[str] | None = Field(default_factory=list, description="List of owner IDs")


class DeleteSearchAppRequest(BaseModel):
    search_id: str = Field(..., description="Search app ID to delete")


class RetrievalRequest(BaseModel):
    dataset_ids: list[str] = Field(..., description="List of dataset IDs to search in")
    question: str = Field(..., description="Search query/question")
    page: int = Field(1, ge=1)
    page_size: int = Field(30, ge=1)
    document_ids: list[str] | None = Field(default_factory=list, description="List of document IDs to filter")
    use_kg: bool = Field(False, description="Whether to use Knowledge Graph")
    toc_enhance: bool = Field(False, description="Whether to use Table of Contents enhancement")
    top_k: int = Field(1024, ge=1)
    cross_languages: list[str] | None = Field(
        default_factory=list, description="List of languages for cross-lingual search"
    )
    metadata_condition: dict[str, Any] | None = Field(default_factory=dict, description="Metadata filter")
    rerank_id: str | None = Field(None, description="Rerank model ID")
    keyword: bool = Field(False, description="Whether to use keyword extraction")
    similarity_threshold: float | None = Field(0.0, ge=0.0, le=1.0)
    vector_similarity_weight: float | None = Field(0.3, ge=0.0, le=1.0)
    highlight: bool | None = Field(False, description="Whether to highlight matched content")


class DocumentAggregation(BaseModel):
    count: int = Field(..., description="Number of results in this document")
    doc_id: str = Field(..., description="Document ID")
    doc_name: str = Field(..., description="Document name")


class RetrievalChunk(BaseModel):
    id: str | None = Field(default=None, description="Chunk ID")
    content: str = Field(..., description="Chunk content")
    document_id: str = Field(..., description="ID of the document")
    dataset_id: str = Field(..., description="ID of the dataset")
    similarity: float = Field(..., description="Similarity score")
    important_keywords: list[str] | None = Field(default_factory=list, description="Important keywords")
    questions: list[str] | None = Field(default_factory=list, description="Question keywords")
    document_keyword: str | None = Field(default="", description="Document name keyword")
    image_id: str | None = Field(default=None, description="Associated image ID")
    positions: list[list] = Field(default_factory=list, description="Position information in document")


class RetrievalResponse(BaseModel):
    chunks: list[RetrievalChunk] = Field(..., description="List of chunks retrieved")
    doc_aggs: list[DocumentAggregation] | None = Field(None, description="Document aggregations")
    total: int = Field(..., description="Total chunks found")
