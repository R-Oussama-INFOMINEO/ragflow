from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class IngestVideoRequest(BaseModel):
    """Request to register a YouTube video URL as a document in a dataset."""

    dataset_id: str = Field(..., description="Target dataset ID")
    url: str = Field(..., description="YouTube URL (youtube.com/watch or youtu.be format)")
    title: str = Field(default="", description="Human-readable title stored with each chunk")


class WaitForCompletionRequest(BaseModel):
    """Request parameters for polling a document until parsing completes."""

    dataset_id: str = Field(..., description="Dataset containing the document")
    doc_id: str = Field(..., description="Document ID to monitor")
    timeout: int = Field(default=300, ge=1, description="Max seconds to wait before timing out")
    poll_interval: int = Field(default=5, ge=1, description="Seconds between status checks")


class IngestVideoResponse(BaseModel):
    """Response from registering a YouTube video document."""

    id: str = Field(..., description="Document ID")
    name: str = Field(..., description="Document name (title or URL)")
    dataset_id: str = Field(..., description="Dataset this document belongs to")
    location: str = Field(..., description="YouTube URL stored as document location")
    chunk_method: str = Field(..., description="Parser used — always 'video' for ingested videos")
    size: int = Field(default=0, description="File size in bytes (always 0 for URL-based documents)")
    suffix: str = Field(default="url", description="File extension — always 'url' for video documents")
    run: str = Field(default="UNSTART", description="Processing run status")
    type: Optional[str] = Field(default=None, description="File type category")
    source_type: Optional[str] = Field(default=None, description="Document source")
    thumbnail: Optional[str] = Field(default=None, description="Thumbnail (empty for video URLs)")
    pipeline_id: Optional[str] = Field(default=None, description="Pipeline ID if using custom pipeline")
    parser_config: Optional[Dict[str, Any]] = Field(default=None, description="Parser configuration inherited from dataset")
    created_by: Optional[str] = Field(default=None, description="Tenant ID of the creator")


class WaitForCompletionResponse(BaseModel):
    """Response from polling a document until parsing completes."""

    status: str = Field(..., description="Outcome: 'complete', 'timeout', or 'failed'")
    doc_id: str = Field(..., description="Document ID that was monitored")
    chunk_count: int = Field(default=0, description="Number of chunks produced (0 on timeout or failure)")