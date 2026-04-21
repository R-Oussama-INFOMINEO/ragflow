#
#  Copyright 2024 The InfiniFlow Authors. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
#
"""
Shared entity classes for RAGFlow SDK.

These entities represent database models and are used across multiple modules
to ensure consistent data structures and avoid duplication.
"""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class LayoutRecognizer(str, Enum):
    """PDF layout recognition methods"""

    DEEPDOC = "DeepDOC"  # Default RAGFlow layout recognizer
    PLAIN_TEXT = "Plain Text"  # Simple text extraction without layout analysis
    MINERU = "MinerU"  # MinerU OCR engine (requires @MinerU suffix with model name)
    PADDLEOCR = "PaddleOCR"  # PaddleOCR engine (requires @PaddleOCR suffix with model name)
    DOCLING = "Docling"  # Docling parser
    TCADP = "TCADP"  # Tencent Cloud ADP parser
    # Vision models can also be used (e.g., "gpt-4o", "claude-3-5-sonnet-20241022")


class RaptorScope(str, Enum):
    """
    RAPTOR hierarchical summarization scope.
    """

    FILE = "file"  # Generate RAPTOR summaries for each file independently
    DATASET = "dataset"  # Generate RAPTOR summaries across the entire dataset


class GraphRAGMethod(str, Enum):
    """
    GraphRAG knowledge graph extraction methods.
    """

    LIGHT = "light"  # Lightweight extraction for faster processing
    FULL = "full"  # Full extraction with comprehensive graph analysis


class Permission(str, Enum):
    """Dataset permission levels"""

    ME = "me"  # Private to creator only
    TEAM = "team"  # Shared with team


class Language(str, Enum):
    """Supported languages"""

    ENGLISH = "English"
    CHINESE = "Chinese"


class RaptorConfig(BaseModel):
    """RAPTOR hierarchical summarization configuration"""

    use_raptor: bool = Field(default=False, description="Enable RAPTOR summarization")
    scope: RaptorScope | None = Field(default=None, description="Summarization scope (file or dataset level)")
    prompt: str | None = Field(default=None, description="Custom prompt for summarization")
    max_token: int | None = Field(default=None, description="Maximum tokens for summaries")
    threshold: float | None = Field(default=None, description="Similarity threshold for clustering")
    max_cluster: int | None = Field(default=None, description="Maximum number of clusters")
    random_seed: int | None = Field(default=None, description="Random seed for reproducibility")
    auto_disable_for_structured_data: bool | None = Field(
        default=None, description="Automatically disable RAPTOR for structured data"
    )


class GraphRAGConfig(BaseModel):
    """GraphRAG knowledge graph extraction configuration"""

    use_graphrag: bool = Field(default=False, description="Enable GraphRAG extraction")
    entity_types: list[str] | None = Field(default=None, description="Entity types to extract")
    method: GraphRAGMethod | None = Field(default=None, description="Extraction method (light or full)")
    resolution: bool | None = Field(default=False, description="Enable entity resolution and deduplication")
    community: bool | None = Field(default=False, description="Enable community detection in the graph")


class ParserConfig(BaseModel):
    """Comprehensive parser configuration for document processing"""

    # Page selection
    pages: list[list[int]] | None = Field(default=None, description="Page ranges to process")

    # Chunking settings
    chunk_token_num: int | None = Field(None, ge=1, le=8192, description="Maximum tokens per chunk")
    delimiter: str | None = Field(None, description="Delimiter for splitting text")

    # Layout and recognition
    layout_recognize: LayoutRecognizer | str | None = Field(
        None,
        description="PDF layout recognition method",
    )

    # Auto-generation settings
    auto_keywords: int | None = Field(None, ge=0, le=32, description="Number of keywords to auto-generate")
    auto_questions: int | None = Field(None, ge=0, le=10, description="Number of questions to auto-generate")

    # Context window sizes
    table_context_size: int | None = Field(None, ge=0, description="Number of context chunks around tables")
    image_context_size: int | None = Field(None, ge=0, description="Number of context chunks around images")

    # Table of Contents
    toc_extraction: bool | None = Field(None, description="Enable table of contents extraction")

    # Metadata extraction
    metadata: dict | None = Field(None, description="Metadata schema definition for extraction")
    enable_metadata: bool | None = Field(None, description="Enable metadata extraction from documents")

    # LLM and Other settings
    llm_id: str | None = Field(None, description="LLM ID for parsing/summarization")
    html4excel: bool | None = Field(None, description="Use HTML format for Excel tables")
    topn_tags: int | None = Field(None, ge=0, description="Number of top tags to generate")
    tag_kb_ids: list[str] | None = Field(None, description="Knowledge base IDs for tag-based chunking")
    task_page_size: int | None = Field(None, ge=1, description="Number of pages to process per task")

    # Advanced features
    raptor: RaptorConfig | None = Field(None, description="RAPTOR hierarchical summarization config")
    graphrag: GraphRAGConfig | None = Field(None, description="GraphRAG knowledge graph extraction config")
    entity_types: list[str] | None = Field(None, description="Entity types for knowledge_graph parser")

    # Video transcription settings
    whisper_backend: str = Field(
        default="youtube-transcript-api",
        description=(
            "Transcription backend for video documents. "
            "Valid values: 'youtube-transcript-api', 'faster-whisper', "
            "'openai-whisper', 'openai-api'"
        ),
    )
    whisper_model: str = Field(
        default="base",
        description=(
            "Model size for local Whisper backends (faster-whisper, openai-whisper). "
            "Valid values: 'tiny', 'base', 'small', 'medium', 'large'"
        ),
    )


class DocumentEntity(BaseModel):
    """
    Represents a document database record.

    Shared between Dataset and Document modules as documents are managed
    within datasets and accessed from both contexts.

    Fields map to the Document model in api/db/db_models.py
    """

    id: str = Field(..., description="Unique document identifier")
    kb_id: str = Field(..., description="Knowledge base (dataset) ID this document belongs to")
    name: str = Field(..., description="Document filename")
    type: str = Field(..., description="File type category (e.g., 'pdf', 'docx')")
    size: int = Field(..., description="File size in bytes")
    chunk_num: int = Field(default=0, description="Number of chunks created from this document")
    token_num: int = Field(default=0, description="Total number of tokens across all chunks")
    progress: float = Field(default=0.0, description="Processing progress (0.0 to 1.0)")
    progress_msg: str | None = Field(default=None, description="Current processing status message")
    run: str = Field(default="0", description="Processing run status: 0=unstart, 1=running, 2=cancel, 3=done, 4=fail")
    status: str = Field(default="1", description="Document status: 0=deleted, 1=active")
    parser_id: str = Field(..., description="Parser/chunking method ID (e.g., 'naive', 'deepdoc')")
    parser_config: ParserConfig = Field(default_factory=ParserConfig, description="Parser configuration settings")
    source_type: str = Field(default="local", description="Document source (e.g., 'local', 'web', 's3')")
    location: str = Field(..., description="Storage location/path")
    thumbnail: str | None = Field(default=None, description="Base64 thumbnail or image path")
    process_begin_at: datetime | None = Field(default=None, description="When processing started")
    process_duration: float = Field(default=0.0, description="Processing duration in seconds")
    created_by: str = Field(..., description="User ID who created this document")
    pipeline_id: str | None = Field(default=None, description="Pipeline ID if using custom pipeline")
    suffix: str = Field(..., description="File extension without dot")
    create_time: datetime | None = Field(default=None, description="Creation timestamp")
    update_time: datetime | None = Field(default=None, description="Last update timestamp")
    meta_fields: dict | None = Field(default_factory=dict, description="Additional metadata for the document")

    class Config:
        json_schema_extra = {
            "example": {
                "id": "doc123",
                "kb_id": "kb456",
                "name": "example.pdf",
                "type": "pdf",
                "size": 1024000,
                "chunk_num": 42,
                "token_num": 5000,
                "progress": 1.0,
                "progress_msg": "Completed",
                "run": "3",
                "status": "1",
                "parser_id": "deepdoc",
                "parser_config": {"chunk_token_num": 512},
                "source_type": "local",
                "location": "/path/to/file",
                "created_by": "user789",
                "suffix": "pdf",
            }
        }


class FileEntity(BaseModel):
    """
    Represents a file record in the file system.

    Used for file management operations across modules. Files can be
    documents, folders, or other file types in the virtual file system.

    Fields map to the File model in api/db/db_models.py
    """

    id: str = Field(..., description="Unique file identifier")
    parent_id: str = Field(..., description="Parent folder ID")
    tenant_id: str = Field(..., description="Tenant (user) ID who owns this file")
    name: str = Field(..., description="File or folder name")
    location: str | None = Field(default=None, description="Storage location/path")
    size: int = Field(default=0, description="File size in bytes (0 for folders)")
    type: str = Field(..., description="File type (e.g., 'folder', 'pdf', 'docx')")
    source_type: str = Field(default="", description="Source of the file (e.g., 'knowledgebase', 'local')")
    created_by: str = Field(..., description="User ID who created this file")
    create_time: datetime | None = Field(default=None, description="Creation timestamp")
    update_time: datetime | None = Field(default=None, description="Last update timestamp")

    class Config:
        json_schema_extra = {
            "example": {
                "id": "file123",
                "parent_id": "folder456",
                "tenant_id": "tenant789",
                "name": "documents",
                "type": "folder",
                "size": 0,
                "source_type": "knowledgebase",
                "created_by": "user789",
            }
        }


class UserEntity(BaseModel):
    """
    Represents a user record.

    Used for user information display and management across modules.
    Contains public user information (excludes sensitive fields like password).

    Fields map to the User model in api/db/db_models.py
    """

    id: str = Field(..., description="Unique user identifier")
    email: str = Field(..., description="User email address")
    nickname: str = Field(..., description="User display name")
    avatar: str | None = Field(default=None, description="Base64 avatar image or URL")
    language: str = Field(default="English", description="Preferred language (English or Chinese)")
    color_schema: str = Field(default="Bright", description="UI color scheme preference (Bright or Dark)")
    timezone: str = Field(default="UTC+8\tAsia/Shanghai", description="User timezone")
    status: str = Field(default="1", description="User status: 0=inactive, 1=active")
    is_superuser: bool = Field(default=False, description="Whether user has admin privileges")
    last_login_time: datetime | None = Field(default=None, description="Last login timestamp")
    login_channel: str | None = Field(default=None, description="Login method (e.g., 'password', 'github', 'google')")
    create_time: datetime | None = Field(default=None, description="Account creation timestamp")
    update_time: datetime | None = Field(default=None, description="Last update timestamp")

    class Config:
        json_schema_extra = {
            "example": {
                "id": "user123",
                "email": "user@example.com",
                "nickname": "John Doe",
                "language": "English",
                "color_schema": "Dark",
                "status": "1",
                "is_superuser": False,
                "login_channel": "password",
            }
        }


class ChunkEntity(BaseModel):
    """
    Represents a chunk/segment of a document.

    Chunks are created during document parsing and stored in elasticsearch/infinity
    for retrieval. Each chunk contains content, keywords, and metadata for RAG operations.

    Fields map to the chunk schema in rag/nlp/search.py and chunk operations
    in api/apps/chunk_app.py
    """

    id: str | None = Field(default=None, description="Unique chunk identifier (hash)")
    doc_id: str = Field(..., description="Parent document ID")
    kb_id: str | list[str] = Field(default_factory=list, description="Knowledge base IDs")
    docnm_kwd: str = Field(..., description="Document name keyword")
    content_with_weight: str = Field(..., description="Main chunk content text")
    content_ltks: str = Field(default="", description="Tokenized content")
    content_sm_ltks: str = Field(default="", description="Fine-grained tokenized content")
    important_kwd: list[str] = Field(default_factory=list, description="Important keywords extracted from content")
    question_kwd: list[str] = Field(default_factory=list, description="Question keywords for Q&A matching")
    image_id: str | None = Field(default=None, description="Associated image ID (img_id field)")
    available_int: int = Field(default=1, description="Availability status: 1=enabled, 0=disabled")
    positions: list[list] = Field(default_factory=list, description="Position information in document (position_int)")
    doc_type_kwd: str | None = Field(default=None, description="Document type keyword")
    create_time: datetime | None = Field(default=None, description="Creation timestamp")
    create_timestamp_flt: float | None = Field(default=None, description="Creation timestamp as float")
    title_tks: str | None = Field(default=None, description="Title tokens")

    # Specific retrieval attributes
    chunk_id: str | None = Field(default=None, description="Chunk ID (used interchangeably with id)")
    similarity: float | None = Field(default=None, description="Retrieval similarity score")
    term_similarity: float | None = Field(default=None, description="Term similarity score")
    vector_similarity: float | None = Field(default=None, description="Vector similarity score")
    knowledge_graph_kwd: str | None = Field(default=None, description="Knowledge graph chunk type (graph, mind_map)")
    raptor_kwd: str | None = Field(default=None, description="RAPTOR chunk indicator")
    mom_id: str | None = Field(default=None, description="Parent chunk ID for hierarchical structures (e.g. RAPTOR)")

    class Config:
        json_schema_extra = {
            "example": {
                "id": "abc123def456",
                "doc_id": "doc789",
                "kb_id": ["kb001"],
                "docnm_kwd": "example.pdf",
                "content_with_weight": "This is the chunk content with important information.",
                "important_kwd": ["information", "content"],
                "question_kwd": ["What is this about?"],
                "image_id": "kb001-img123.png",
                "available_int": 1,
                "positions": [[1, 100, 200, 50, 30]],
                "doc_type_kwd": "pdf",
                "chunk_id": "abc123def456",
                "similarity": 0.85,
                "knowledge_graph_kwd": "graph",
                "mom_id": "parent_chunk_id",
            }
        }


class DatasetEntity(BaseModel):
    """
    Represents a dataset (knowledge base) database record.

    Maps to the Knowledgebase model in api/db/db_models.py
    """

    id: str = Field(..., description="Unique dataset identifier")
    name: str = Field(..., description="Dataset name")
    avatar: str | None = Field(None, description="Base64 avatar image")
    description: str | None = Field(None, description="Dataset description")
    tenant_id: str = Field(..., description="Tenant (user) ID who owns this dataset")
    created_by: str = Field(..., description="User ID who created this dataset")
    language: str = Field(default="English", description="Dataset language")
    embd_id: str = Field(..., description="Embedding model ID")
    permission: str = Field(default="me", description="Access permission level")
    parser_id: str = Field(..., description="Default parser/chunking method")
    parser_config: ParserConfig = Field(default_factory=ParserConfig, description="Default parser configuration")
    similarity_threshold: float = Field(default=0.2, description="Similarity threshold for retrieval")
    vector_similarity_weight: float = Field(default=0.3, description="Weight for vector similarity")
    pagerank: int | None = Field(None, description="PageRank weight for retrieval")
    doc_num: int = Field(default=0, description="Number of documents")
    token_num: int = Field(default=0, description="Total number of tokens")
    chunk_num: int = Field(default=0, description="Total number of chunks")
    graphrag_task_id: str | None = Field(None, description="GraphRAG task ID if running")
    raptor_task_id: str | None = Field(None, description="RAPTOR task ID if running")
    mindmap_task_id: str | None = Field(None, description="Mindmap task ID if running")
    status: str = Field(default="1", description="Dataset status: 0=deleted, 1=active")
    create_time: str | int | float | None = Field(None, description="Creation timestamp")
    update_time: str | int | float | None = Field(None, description="Last update timestamp")


class TaskEntity(BaseModel):
    """
    Represents an asynchronous task record.

    Maps to the Task model in api/db/db_models.py
    """

    id: str = Field(..., description="Unique task identifier")
    doc_id: str | None = Field(None, description="Document ID if document-level task")
    from_page: int | None = Field(None, description="Starting page number")
    to_page: int | None = Field(None, description="Ending page number")
    task_type: str = Field(..., description="Task type (e.g., 'parse', 'graphrag')")
    priority: int | None = Field(None, description="Task priority")
    begin_at: str | None = Field(None, description="Task start timestamp")
    process_duration: float | None = Field(None, description="Processing duration in seconds")
    progress: float = Field(default=0.0, ge=0, le=1, description="Progress from 0 to 1")
    progress_msg: str | None = Field(None, description="Current progress message")
    retry_count: int = Field(default=0, description="Number of retries")
    digest: str | None = Field(None, description="Task digest/hash")
    chunk_ids: list[str] | None = Field(None, description="Generated chunk IDs")


class PipelineLogEntity(BaseModel):
    """
    Represents a pipeline operation log entry.

    Maps to the PipelineOperationLog model in api/db/db_models.py
    """

    id: str = Field(..., description="Unique log identifier")
    document_id: str | None = Field(None, description="Document ID if document-level operation")
    tenant_id: str = Field(..., description="Tenant ID")
    kb_id: str = Field(..., description="Dataset ID")
    pipeline_id: str | None = Field(None, description="Pipeline ID if custom pipeline")
    pipeline_title: str | None = Field(None, description="Pipeline title")
    parser_id: str = Field(..., description="Parser used")
    document_name: str | None = Field(None, description="Document name")
    document_suffix: str | None = Field(None, description="Document file extension")
    document_type: str | None = Field(None, description="Document type")
    source_from: str | None = Field(None, description="Source of operation")
    progress: float = Field(default=0.0, description="Operation progress")
    progress_msg: str | None = Field(None, description="Progress message")
    process_begin_at: str | None = Field(None, description="Operation start time")
    process_duration: float | None = Field(None, description="Duration in seconds")
    operation_status: str = Field(..., description="Operation status")
    task_type: str | None = Field(None, description="Task type")
    avatar: str | None = Field(None, description="Avatar/thumbnail")
    status: str = Field(default="1", description="Log status")
    create_time: str | None = Field(None, description="Creation timestamp")
    update_time: str | None = Field(None, description="Last update timestamp")


class ConnectorEntity(BaseModel):
    """
    Represents a data source connector configuration.

    Maps to the Connector model in api/db/db_models.py
    """

    id: str = Field(..., description="Unique connector identifier")
    tenant_id: str = Field(..., description="Tenant ID")
    name: str = Field(..., description="Connector name")
    source: str = Field(..., description="Data source type")
    input_type: str = Field(..., description="Input type (poll/event)")
    config: dict = Field(default_factory=dict, description="Connector configuration")
    refresh_freq: int = Field(default=0, description="Refresh frequency in seconds")
    prune_freq: int = Field(default=0, description="Prune frequency in seconds")
    timeout_secs: int = Field(default=3600, description="Timeout in seconds")
    indexing_start: str | None = Field(None, description="Indexing start time")
    status: str = Field(default="schedule", description="Connector status")


class TagEntity(BaseModel):
    """
    Represents a tag with metadata.

    Used for tag management operations.
    """

    name: str = Field(..., description="Tag name")
    count: int = Field(default=0, description="Number of documents with this tag")
    kb_ids: list[str] = Field(default_factory=list, description="Dataset IDs containing this tag")
