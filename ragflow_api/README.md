# RAGFlow API Python Client (`ragflow_api`)

A comprehensive **async** Python client library for interacting with the RAGFlow server API. The SDK provides a clean, type-safe, Pydantic-backed interface covering user management, knowledge base operations, document handling, chunk management, search, and team collaboration.

---

## Table of Contents

1. [Features](#features)
2. [Installation](#installation)
3. [Quick Start](#quick-start)
4. [Architecture](#architecture)
5. [Configuration](#configuration)
6. [API Modules](#api-modules)
   - [User API](#user-api)
   - [Dataset API](#dataset-api)
   - [Document API](#document-api)
   - [Search API](#search-api)
   - [Tenant API](#tenant-api)
   - [Unified PDF Utilities](#unified-pdf-utilities)
7. [DTOs & Entities Reference](#dtos--entities-reference)
8. [Error Handling](#error-handling)
9. [Advanced Patterns](#advanced-patterns)
10. [Complete End-to-End Example](#complete-end-to-end-example)

---

## Features

| Feature | Description |
|---|---|
| 🔐 **Authentication** | RSA-encrypted login, token management, API key generation |
| 📚 **Dataset Management** | Create, update, list, delete knowledge bases with full config |
| 🧠 **Knowledge Graph** | Start/monitor GraphRAG construction, retrieve graph data |
| 🌲 **RAPTOR** | Hierarchical summarization construction and status monitoring |
| 🗺️ **Mind Map** | Mind map generation and status tracking |
| 📄 **Document Lifecycle** | Upload, parse, rename, change parser, delete documents |
| 🧩 **Chunk Management** | List, create, update, switch (enable/disable), delete chunks |
| 🔍 **Retrieval** | Semantic + keyword search with KG, TOC, and cross-language support |
| 🖼️ **PDF Utilities** | Download & highlight original PDFs or extract relevant pages |
| 🏷️ **Metadata** | Per-document metadata with schema validation and batch updates |
| 📋 **Tags** | List, remove, rename tags across datasets |
| 👥 **Team Management** | Invite users, accept invitations, list/remove team members |
| 🛡️ **Type Safety** | Full Pydantic model support for all requests and responses |
| 🔄 **Auto-Retry** | Built-in tenacity retry logic (3 attempts, 1s wait) |

---

## Installation

```bash
# From the ragflow repository root
pip install aiohttp pydantic tenacity pycryptodome

# Optional: PyMuPDF for PDF highlighting utilities
pip install pymupdf
```

> **Python version**: 3.9+
> **Async runtime**: All API methods are `async` — use `asyncio.run()` or an async framework (FastAPI, etc.)

---

## Quick Start

```python
import asyncio
from ragflow_api import RagflowAPI
from ragflow_api.Dataset import CreateDatasetRequest
from ragflow_api.Document import RunDocumentRequest, DocumentInfosRequest
from ragflow_api.Search import RetrievalRequest

async def quick_start():
    # 1. Initialize unified client
    api = RagflowAPI("http://localhost:9380")

    # 2. Authenticate
    token = await api.user.get_token("user@example.com", "password123")

    # 3. Create a knowledge base
    dataset = await api.dataset.create_dataset(
        CreateDatasetRequest(name="My Knowledge Base"), token
    )
    kb_id = dataset.kb_id   # <-- kb_id from CreateDatasetResponse

    # 4. Upload a document
    docs = await api.document.upload(kb_id=kb_id, file_path="report.pdf", token=token)
    doc_id = docs[0].id     # <-- DocumentEntity list

    # 5. Parse the document
    await api.document.run(RunDocumentRequest(doc_ids=[doc_id], run="1"), token)

    # 6. Search
    api_key = await api.user.get_api_key(token)   # needed for /api/v1/retrieval
    results = await api.search.retrieval(
        RetrievalRequest(dataset_ids=[kb_id], question="What is the main finding?", top_k=5),
        api_key
    )
    for chunk in results.chunks:
        print(f"[{chunk.similarity:.3f}] {chunk.content[:120]}")

asyncio.run(quick_start())
```

---

## Architecture

```
ragflow_api/
├── ragflow_api.py          # RagflowAPI — unified entry point
├── base.py                 # RagflowAPIBase, all exception types
├── __init__.py             # Public exports, __version__
│
├── common/
│   ├── entities.py         # Shared Pydantic entity models (ChunkEntity, DocumentEntity, …)
│   └── dto.py              # BasePaginationRequest / BasePaginationResponse
│
├── User/
│   ├── user_api.py         # UserRagflowAPI
│   └── dto.py              # UpdateTenantInfoRequest, UpdateUserSettingRequest, …
│
├── Dataset/
│   ├── dataset_api.py      # DatasetRagflowAPI
│   └── dataset_dto.py      # CreateDatasetRequest, ParserType, CreateDatasetResponse, …
│
├── Document/
│   ├── document_api.py     # DocumentRagflowAPI
│   └── document_dto.py     # RunDocumentRequest, ListChunksRequest, …
│
├── Search/
│   ├── search_api.py       # SearchRagflowAPI
│   └── search_dto.py       # RetrievalRequest, RetrievalResponse, RetrievalChunk, …
│
└── Tenant/
    ├── tenant_api.py       # TenantRagflowAPI
    └── tenant_dto.py       # InviteUserRequest, InvitedUserResponse, …
```

The **`RagflowAPI`** class instantiates all five subclients and exposes them as attributes: `api.user`, `api.dataset`, `api.document`, `api.search`, `api.tenant`.

---

## Configuration

### Public Key for Password Encryption

Passwords are RSA-encrypted before leaving the client. The library resolves the public key in this order:

| Priority | Source |
|---|---|
| 1 | `public_key` constructor arg (raw PEM string) |
| 2 | `public_key_path` constructor arg (path to `.pem` file) |
| 3 | `conf/public.pem` relative to working directory |
| 4 | Built-in fallback key (RAGFlow default) |

```python
# Default (uses built-in key or conf/public.pem)
api = RagflowAPI("http://localhost:9380")

# Custom PEM file
api = RagflowAPI("http://localhost:9380", public_key_path="/etc/ragflow/public.pem")

# Inline PEM string
api = RagflowAPI("http://localhost:9380", public_key="-----BEGIN PUBLIC KEY-----\n...\n-----END PUBLIC KEY-----")

# Different API version
api = RagflowAPI("http://localhost:9380", version="v1")
```

### Two Token Types

RAGFlow uses two distinct bearer tokens:

| Token | How to get | Used for |
|---|---|---|
| **Session token** | `api.user.get_token()` | Most internal endpoints (`/v1/kb/...`, `/v1/document/...`, etc.) |
| **API key** | `api.user.get_api_key(session_token)` | External SDK endpoints (`/api/v1/retrieval`) |

```python
session_token = await api.user.get_token("user@example.com", "pw")
api_key = await api.user.get_api_key(session_token)   # "Bearer ragflow-xxxx"
```

---

## API Modules

### User API

`api.user` → `UserRagflowAPI`

| Method | Signature | Returns |
|---|---|---|
| `register_user` | `(email, nickname, password)` | `bool` |
| `login` | `(email, password)` | `dict` with `access_token` |
| `get_token` | `(email, password)` | `str` (token) |
| `get_team_info` | `(token)` | `dict` (tenant info) |
| `update_tenant_info` | `(token, UpdateTenantInfoRequest)` | `bool` |
| `update_user_setting` | `(token, UpdateUserSettingRequest)` | `bool` |
| `logout` | `(token)` | `bool` |
| `get_api_key` | `(token)` | `str` (`"Bearer ragflow-xxxx"`) |

```python
from ragflow_api.User import UserRagflowAPI

user_api = UserRagflowAPI("http://localhost:9380")

# Register
await user_api.register_user("alice@example.com", "Alice", "s3cr3t!")

# Login (returns full user data + access_token)
login_data = await user_api.login("alice@example.com", "s3cr3t!")
token = login_data["access_token"]

# Shortcut: get just the token
token = await user_api.get_token("alice@example.com", "s3cr3t!")

# Tenant info
team_info = await user_api.get_team_info(token)
tenant_id = team_info["tenant_id"]

# Get API key for external SDK endpoints
api_key = await user_api.get_api_key(token)

# Update LLM model binding
from ragflow_api.User.dto import UpdateTenantInfoRequest
await user_api.update_tenant_info(token, UpdateTenantInfoRequest(
    tenant_id=tenant_id,
    llm_id="gpt-4o",
    embd_id="text-embedding-3-large"
))

# Logout
await user_api.logout(token)
```

---

### Dataset API

`api.dataset` → `DatasetRagflowAPI`

#### CRUD

| Method | Signature | Returns |
|---|---|---|
| `create_dataset` | `(CreateDatasetRequest, token)` | `CreateDatasetResponse` |
| `update_dataset` | `(UpdateDatasetRequest, token)` | `UpdateDatasetResponse` |
| `get_dataset_detail` | `(dataset_id: str, token)` | `DatasetDetailResponse` |
| `delete_datasets` | `(DeleteDatasetsRequest, token)` | `bool` |
| `list_datasets` | `(ListDatasetsRequest, token)` | `ListDatasetsResponse` |

#### Knowledge Graph

| Method | Signature | Returns |
|---|---|---|
| `construct_knowledge_graph` | `(dataset_id, token)` | `TaskResponse` |
| `get_knowledge_graph_status` | `(dataset_id, token)` | `TaskStatusResponse` |
| `retrieve_knowledge_graph` | `(dataset_id, token)` | `KnowledgeGraphResponse` |
| `delete_knowledge_graph` | `(dataset_id, token)` | `bool` |

#### RAPTOR

| Method | Signature | Returns |
|---|---|---|
| `construct_raptor` | `(dataset_id, token)` | `TaskResponse` |
| `get_raptor_status` | `(dataset_id, token)` | `TaskStatusResponse` |

#### Mind Map

| Method | Signature | Returns |
|---|---|---|
| `construct_mindmap` | `(dataset_id, token)` | `TaskResponse` |
| `get_mindmap_status` | `(dataset_id, token)` | `TaskStatusResponse` |

#### Metadata & Tags

| Method | Signature | Returns |
|---|---|---|
| `update_metadata_setting` | `(UpdateMetadataSettingRequest, token)` | `UpdateMetadataSettingResponse` |
| `get_meta` | `(GetMetaRequest, token)` | `GetMetaResponse` |
| `get_basic_info` | `(GetBasicInfoRequest, token)` | `BasicInfoResponse` |
| `list_tags` | `(ListTagsRequest, token)` | `ListTagsResponse` |
| `remove_tags` | `(RemoveTagsRequest, token)` | `bool` |
| `rename_tag` | `(RenameTagRequest, token)` | `bool` |

#### Pipeline Logs

| Method | Signature | Returns |
|---|---|---|
| `list_pipeline_logs` | `(ListPipelineLogsRequest, token)` | `PipelineLogListResponse` |
| `list_pipeline_dataset_logs` | `(ListPipelineDatasetLogsRequest, token)` | `PipelineLogListResponse` |
| `delete_pipeline_logs` | `(DeletePipelineLogsRequest, token)` | `bool` |
| `get_pipeline_log_detail` | `(PipelineLogDetailRequest, token)` | `PipelineLogDetailResponse` |
| `unbind_task` | `(UnbindTaskRequest, token)` | `bool` |
| `check_embedding` | `(CheckEmbeddingRequest, token)` | `CheckEmbeddingResponse` |

```python
from ragflow_api.Dataset import (
    DatasetRagflowAPI,
    CreateDatasetRequest,
    UpdateDatasetRequest,
    ListDatasetsRequest,
    DeleteDatasetsRequest,
    ParserType,
)
from ragflow_api.common.entities import ParserConfig, GraphRAGConfig, RaptorConfig, Permission, Language

ds_api = DatasetRagflowAPI("http://localhost:9380")

# ── Create with advanced parser config ──────────────────────────────────────
create_req = CreateDatasetRequest(
    name="Technical Documentation",
    description="Company engineering docs",
    language=Language.ENGLISH,
    permission=Permission.TEAM,
    parser_id=ParserType.MANUAL,
    parser_config=ParserConfig(
        chunk_token_num=512,
        auto_keywords=5,
        auto_questions=3,
        toc_extraction=True,
        raptor=RaptorConfig(use_raptor=True, scope="dataset"),
        graphrag=GraphRAGConfig(use_graphrag=True, method="light"),
    ),
    similarity_threshold=0.2,
    vector_similarity_weight=0.3,
)
dataset = await ds_api.create_dataset(create_req, token)
kb_id = dataset.kb_id

# ── List ─────────────────────────────────────────────────────────────────────
result = await ds_api.list_datasets(ListDatasetsRequest(page=1, page_size=30), token)
for kb in result.kbs:
    print(f"{kb.id}  {kb.name}  docs={kb.doc_num}")

# ── Update ───────────────────────────────────────────────────────────────────
await ds_api.update_dataset(
    UpdateDatasetRequest(kb_id=kb_id, name="Renamed Base", pagerank=80), token
)

# ── Knowledge Graph construction ──────────────────────────────────────────────
await ds_api.construct_knowledge_graph(kb_id, token)

import asyncio
while True:
    status = await ds_api.get_knowledge_graph_status(kb_id, token)
    print(f"KG progress: {status.progress * 100:.0f}%  {status.progress_msg}")
    if status.progress >= 1.0:
        break
    await asyncio.sleep(10)

kg_data = await ds_api.retrieve_knowledge_graph(kb_id, token)
nodes = kg_data.graph.get("nodes", [])
edges = kg_data.graph.get("edges", [])

# ── RAPTOR ────────────────────────────────────────────────────────────────────
await ds_api.construct_raptor(kb_id, token)
while (await ds_api.get_raptor_status(kb_id, token)).progress < 1.0:
    await asyncio.sleep(10)

# ── Delete ────────────────────────────────────────────────────────────────────
await ds_api.delete_datasets(DeleteDatasetsRequest(kb_id=kb_id), token)
```

#### `ParserType` Enum Values

| Value | Description |
|---|---|
| `NAIVE` | Default general-purpose chunking |
| `MANUAL` | Manual / documentation style |
| `PAPER` | Academic papers |
| `BOOK` | Book-length documents |
| `PRESENTATION` | Slides / presentations |
| `LAWS` | Legal documents |
| `RESUME` | Resumes / CVs |
| `QA` | Q&A formatted documents |
| `TABLE` | Table-heavy documents |
| `PICTURE` | Image-heavy documents |
| `ONE` | Single chunk (no splitting) |
| `AUDIO` | Audio files |
| `EMAIL` | Email format |
| `KNOWLEDGE_GRAPH` | Knowledge graph extraction parser |
| `TAG` | Tag-based chunking |

---

### Document API

`api.document` → `DocumentRagflowAPI`

#### Document Lifecycle

| Method | Signature | Returns |
|---|---|---|
| `upload` | `(kb_id, file_path, token)` | `List[DocumentEntity]` |
| `upload_with_metadata` | `(kb_id, file_path, token, metadata)` | `List[dict]` |
| `upload_and_parse` | `(conversation_id, file_path, token)` | `List[str]` |
| `web_crawl` | `(WebCrawlRequest, token)` | `bool` |
| `create` | `(CreateDocumentRequest, token)` | `CreateDocumentResponse` |
| `run` | `(RunDocumentRequest, token)` | `bool` |
| `rename` | `(RenameDocumentRequest, token)` | `bool` |
| `change_parser` | `(ChangeParserRequest, token)` | `bool` |
| `change_status` | `(ChangeStatusRequest, token)` | `dict` |
| `rm` | `(DeleteDocumentsRequest, token)` | `bool` |
| `list_docs` | `(ListDocumentsRequest, token)` | `dict` |
| `doc_infos` | `(DocumentInfosRequest, token)` | `List[DocumentEntity]` |
| `metadata_summary` | `(MetadataSummaryRequest, token)` | `dict` |
| `set_metadata` | `(SetMetadataRequest, token)` | `bool` |
| `update_metadata_settings` | `(UpdateMetadataSettingsRequest, token)` | `UpdateMetadataSettingsResponse` |
| `batch_update_metadata` | `(BatchUpdateMetadataRequest, token)` | `BatchUpdateMetadataResponse` |
| `get_filters` | `(GetFiltersRequest, token)` | `GetFiltersResponse` |
| `download` | `(doc_id, token)` | `bytes` |
| `download_image` | `(image_id, token)` | `bytes` |
| `download_attachment` | `(attachment_id, token, ext)` | `bytes` |
| `get_thumbnails` | `(ThumbnailsRequest, token)` | `dict` |

#### Chunk Operations

| Method | Signature | Returns |
|---|---|---|
| `list_chunks` | `(ListChunksRequest, token)` | `ListChunksResponse` |
| `create_chunk` | `(CreateChunkRequest, token)` | `dict` |
| `get_chunk` | `(GetChunkRequest, token)` | `dict` |
| `update_chunk` | `(UpdateChunkRequest, token)` | `bool` |
| `switch_chunk` | `(SwitchChunkRequest, token)` | `bool` |
| `rm_chunks` | `(DeleteChunksRequest, token)` | `bool` |
| `get_knowledge_graph` | `(doc_id, token)` | `dict` |
| `retrieval` | `(RetrievalRequest, token)` | `RetrievalResponse` |

```python
from ragflow_api.Document import (
    DocumentRagflowAPI,
    RunDocumentRequest,
    ListDocumentsRequest,
    DocumentInfosRequest,
    ListChunksRequest,
    CreateChunkRequest,
    UpdateChunkRequest,
    SwitchChunkRequest,
    DeleteChunksRequest,
    SetMetadataRequest,
    ThumbnailsRequest,
    DeleteDocumentsRequest,
)

doc_api = DocumentRagflowAPI("http://localhost:9380")

# ── Upload ────────────────────────────────────────────────────────────────────
docs = await doc_api.upload(kb_id="<kb_id>", file_path="report.pdf", token=token)
doc_id = docs[0].id

# ── Upload with metadata in one call ─────────────────────────────────────────
results = await doc_api.upload_with_metadata(
    kb_id="<kb_id>",
    file_path="report.pdf",
    token=token,
    metadata={"category": "finance", "year": 2024, "tags": ["q1", "revenue"]},
)

# ── Parse ─────────────────────────────────────────────────────────────────────
await doc_api.run(RunDocumentRequest(doc_ids=[doc_id], run="1"), token)

# ── Poll until done ───────────────────────────────────────────────────────────
import asyncio
while True:
    info = await doc_api.doc_infos(DocumentInfosRequest(doc_ids=[doc_id]), token)
    if info[0].progress >= 1.0:
        break
    await asyncio.sleep(3)

# ── List documents with filters ───────────────────────────────────────────────
data = await doc_api.list_docs(
    ListDocumentsRequest(kb_id="<kb_id>", page=1, page_size=50),
    token,
)
for d in data.get("docs", []):
    print(d["name"], d["chunk_num"])

# ── List chunks ───────────────────────────────────────────────────────────────
chunks_resp = await doc_api.list_chunks(
    ListChunksRequest(doc_id=doc_id, page=1, size=50), token
)
for chunk in chunks_resp.chunks:
    print(f"[{chunk.id}] {chunk.content_with_weight[:80]}")

# ── Create a manual chunk ─────────────────────────────────────────────────────
new_chunk = await doc_api.create_chunk(
    CreateChunkRequest(
        doc_id=doc_id,
        content_with_weight="Custom chunk content manually added.",
        important_kwd=["custom", "manual"],
    ),
    token,
)

# ── Update a chunk ────────────────────────────────────────────────────────────
await doc_api.update_chunk(
    UpdateChunkRequest(
        doc_id=doc_id,
        chunk_id=chunks_resp.chunks[0].id,
        content_with_weight="Updated content.",
    ),
    token,
)

# ── Disable a chunk ───────────────────────────────────────────────────────────
await doc_api.switch_chunk(
    SwitchChunkRequest(doc_id=doc_id, chunk_ids=[chunks_resp.chunks[0].id], available_int=0),
    token,
)

# ── Download original PDF ─────────────────────────────────────────────────────
pdf_bytes = await doc_api.download(doc_id, token)
with open("original.pdf", "wb") as f:
    f.write(pdf_bytes)

# ── Download a chunk image ────────────────────────────────────────────────────
img_bytes = await doc_api.download_image("<image_id>", token)

# ── Set document metadata ─────────────────────────────────────────────────────
await doc_api.set_metadata(
    SetMetadataRequest(doc_id=doc_id, meta={"region": "EMEA", "quarter": "Q2"}),
    token,
)

# ── Delete document ───────────────────────────────────────────────────────────
await doc_api.rm(DeleteDocumentsRequest(doc_id=doc_id), token)
```

#### `RunDocumentRequest` — `run` field values

| Value | Meaning |
|---|---|
| `"1"` | Start / re-parse |
| `"2"` | Cancel processing |

#### Document processing `progress` field

`0.0` = not started → `1.0` = complete. Check `run` field for state:

| `run` | State |
|---|---|
| `"0"` | Not started |
| `"1"` | Running |
| `"2"` | Cancelled |
| `"3"` | Done |
| `"4"` | Failed |

---

### Search API

`api.search` → `SearchRagflowAPI`

| Method | Signature | Returns |
|---|---|---|
| `create_search_app` | `(CreateSearchAppRequest, token)` | `dict` |
| `update_search_app` | `(UpdateSearchAppRequest, token)` | `dict` |
| `detail_search_app` | `(search_id, token)` | `dict` |
| `list_search_apps` | `(ListSearchAppRequest, token)` | `dict` |
| `rm_search_app` | `(DeleteSearchAppRequest, token)` | `bool` |
| `retrieval` | `(RetrievalRequest, api_key)` | `RetrievalResponse` |

> ⚠️ The `retrieval` method uses the **`/api/v1/retrieval`** endpoint which requires a **Bearer API key** (not a session token). Use `api.user.get_api_key(token)` to obtain it.

```python
from ragflow_api.Search import (
    SearchRagflowAPI,
    RetrievalRequest,
    CreateSearchAppRequest,
    ListSearchAppRequest,
    DeleteSearchAppRequest,
)

search_api = SearchRagflowAPI("http://localhost:9380")

# ── Retrieval ─────────────────────────────────────────────────────────────────
api_key = await api.user.get_api_key(token)   # "Bearer ragflow-xxxx"

results = await search_api.retrieval(
    RetrievalRequest(
        dataset_ids=["<kb_id>"],
        question="What are the key risks in the report?",
        top_k=10,
        use_kg=True,              # include knowledge graph context
        toc_enhance=True,         # use TOC-aware retrieval
        keyword=True,             # enable keyword extraction
        similarity_threshold=0.2,
        vector_similarity_weight=0.3,
        highlight=True,
    ),
    api_key,
)

for chunk in results.chunks:
    print(f"Score={chunk.similarity:.3f}  Doc={chunk.document_keyword}")
    print(chunk.content[:200])
    print()

# ── Search apps ───────────────────────────────────────────────────────────────
app = await search_api.create_search_app(
    CreateSearchAppRequest(name="Finance Reports Search"), token
)
search_id = app["id"]

apps = await search_api.list_search_apps(ListSearchAppRequest(page=1, page_size=20), token)
await search_api.rm_search_app(DeleteSearchAppRequest(search_id=search_id), token)
```

#### `RetrievalRequest` Fields

| Field | Type | Default | Description |
|---|---|---|---|
| `dataset_ids` | `List[str]` | **required** | Dataset IDs to search in |
| `question` | `str` | **required** | Query string |
| `page` | `int` | `1` | Result page |
| `page_size` | `int` | `30` | Results per page |
| `document_ids` | `List[str]` | `[]` | Scope to specific documents |
| `use_kg` | `bool` | `False` | Include knowledge graph context |
| `toc_enhance` | `bool` | `False` | TOC-aware retrieval |
| `top_k` | `int` | `1024` | Maximum chunks to consider |
| `keyword` | `bool` | `False` | Enable keyword extraction |
| `similarity_threshold` | `float` | `0.0` | Minimum similarity to return |
| `vector_similarity_weight` | `float` | `0.3` | Weight of vector vs BM25 score |
| `rerank_id` | `str` | `None` | Reranker model ID |
| `cross_languages` | `List[str]` | `[]` | Languages for cross-lingual search |
| `metadata_condition` | `dict` | `{}` | Filter by document metadata |
| `highlight` | `bool` | `False` | Highlight matched terms |

#### `RetrievalResponse` Structure

```python
class RetrievalResponse:
    chunks: List[RetrievalChunk]   # ranked result chunks
    doc_aggs: List[DocumentAggregation]  # per-document hit counts
    total: int                     # total chunks found

class RetrievalChunk:
    id: str                        # chunk ID
    content: str                   # chunk text
    document_id: str               # source document ID
    dataset_id: str                # source dataset ID
    similarity: float              # combined similarity score (0–1)
    important_keywords: List[str]  # extracted keywords
    questions: List[str]           # generated questions
    document_keyword: str          # document filename
```

---

### Tenant API

`api.tenant` → `TenantRagflowAPI`

| Method | Signature | Returns |
|---|---|---|
| `invite_user` | `(tenant_id, InviteUserRequest, token)` | `InvitedUserResponse` |
| `list_invitations` | `(token)` | `List[InvitationEntity]` |
| `accept_invitation` | `(tenant_id, token)` | `bool` |
| `list_users` | `(tenant_id, token)` | `List[TenantMemberResponse]` |
| `remove_user` | `(tenant_id, user_id, token)` | `bool` |

```python
from ragflow_api.Tenant import TenantRagflowAPI, InviteUserRequest

tenant_api = TenantRagflowAPI("http://localhost:9380")

# Invite someone
result = await tenant_api.invite_user(
    tenant_id=tenant_id,
    invite_user_request=InviteUserRequest(email="colleague@example.com"),
    token=token,
)

# Accept an invitation (as the invitee)
invitations = await tenant_api.list_invitations(token)
for inv in invitations:
    print(f"Invited to: {inv.tenant_id}  role: {inv.role}")
await tenant_api.accept_invitation(invitations[0].tenant_id, token)

# List team members
members = await tenant_api.list_users(tenant_id, token)
for m in members:
    print(f"{m.nickname} <{m.email}>  role={m.role}")

# Remove a user
await tenant_api.remove_user(tenant_id, user_id="<user_id>", token=token)
```

---

### Unified PDF Utilities

The top-level `RagflowAPI` class provides two convenience methods that combine document download with PDF annotation using [PyMuPDF](https://pymupdf.readthedocs.io/).

| Method | Description |
|---|---|
| `download_pdf_and_highlight` | Downloads the full PDF and highlights all chunk positions |
| `download_pages_and_highlight` | Downloads only the pages containing chunk hits, then highlights |

> Requires `pip install pymupdf`

```python
api = RagflowAPI("http://localhost:9380")
api_key = await api.user.get_api_key(token)

results = await api.search.retrieval(
    RetrievalRequest(dataset_ids=[kb_id], question="quarterly revenue", top_k=5),
    api_key,
)

# Full PDF with highlights
paths = await api.download_pdf_and_highlight(
    chunks=results.chunks,       # list of RetrievalChunk objects
    output_dir="./highlighted/",
    token=token,
)
# Returns: {"<doc_id>": "./highlighted/highlighted_report.pdf", ...}

# Only highlight-relevant pages (smaller files)
paths = await api.download_pages_and_highlight(
    chunks=results.chunks,
    output_dir="./highlights_subset/",
    token=token,
)
```

> **Note:** Chunk position data (`positions` field on `ChunkEntity`) must be populated by the server for highlighting to work. It follows the format `[page_num, x0, x1, y0, y1]` (1-based page index).

---

## DTOs & Entities Reference

### Common Entities (`ragflow_api.common.entities`)

| Class | Description |
|---|---|
| `DocumentEntity` | Full document record (id, kb_id, name, type, size, progress, run, …) |
| `ChunkEntity` | A parsed chunk (id, doc_id, content_with_weight, positions, important_kwd, …) |
| `DatasetEntity` | Dataset / knowledge base record |
| `FileEntity` | File-system file record |
| `UserEntity` | User record (public fields only) |
| `TaskEntity` | Async task record (progress, task_type, …) |
| `PipelineLogEntity` | Pipeline operation log |
| `ConnectorEntity` | Data-source connector config |
| `TagEntity` | Tag with count and dataset associations |

### Common Config Classes (`ragflow_api.common.entities`)

| Class | Key Fields |
|---|---|
| `ParserConfig` | `chunk_token_num`, `auto_keywords`, `auto_questions`, `toc_extraction`, `layout_recognize`, `raptor`, `graphrag`, `html4excel`, `pages`, … |
| `RaptorConfig` | `use_raptor`, `scope` (`"file"` / `"dataset"`), `prompt`, `max_token`, `threshold`, `max_cluster` |
| `GraphRAGConfig` | `use_graphrag`, `method` (`"light"` / `"full"`), `entity_types`, `resolution`, `community` |

### Enums

| Enum | Values |
|---|---|
| `ParserType` | `NAIVE`, `MANUAL`, `PAPER`, `BOOK`, `PRESENTATION`, `LAWS`, `RESUME`, `QA`, `TABLE`, `PICTURE`, `ONE`, `AUDIO`, `EMAIL`, `KNOWLEDGE_GRAPH`, `TAG` |
| `Permission` | `ME`, `TEAM` |
| `Language` | `ENGLISH`, `CHINESE` |
| `RaptorScope` | `FILE`, `DATASET` |
| `GraphRAGMethod` | `LIGHT`, `FULL` |
| `LayoutRecognizer` | `DEEPDOC`, `PLAIN_TEXT`, `MINERU`, `PADDLEOCR`, `DOCLING`, `TCADP` |

---

## Error Handling

All exceptions derive from `RagflowAPIError`:

```python
from ragflow_api import (
    RagflowAPIError,      # base — catch-all
    UnauthorizedError,    # 401 — bad credentials or expired token
    ForbiddenError,       # 403 — insufficient permissions
    NotFoundError,        # 404 — resource not found
    BadRequestError,      # 400 — malformed request or business rule violation
    ValidationError,      # Pydantic / request-data validation failure
    ServerError,          # 5xx — internal server error
    TimeoutError,         # request timeout
)

try:
    token = await api.user.get_token("user@example.com", "wrong_pw")
except UnauthorizedError as e:
    print(f"Login failed: {e}")
except ServerError as e:
    print(f"Server down: {e}")
except RagflowAPIError as e:
    print(f"API error: {e}")
```

All methods that require a token will raise `ValueError("A valid token is required …")` if called without one (enforced by the `@requires_token` decorator).

---

## Advanced Patterns

### Waiting for Async Tasks

All three construction tasks (GraphRAG, RAPTOR, Mindmap) are async. Poll the corresponding status endpoint:

```python
async def wait_for_task(status_fn, dataset_id, token, poll_interval=10):
    """Generic poller for GraphRAG / RAPTOR / Mindmap tasks."""
    while True:
        status = await status_fn(dataset_id, token)
        print(f"  progress={status.progress:.0%}  msg={status.progress_msg}")
        if status.progress >= 1.0:
            return status
        if status.progress < 0:          # -1 indicates failure
            raise RuntimeError(f"Task failed: {status.progress_msg}")
        await asyncio.sleep(poll_interval)

# Usage
await api.dataset.construct_knowledge_graph(kb_id, token)
await wait_for_task(api.dataset.get_knowledge_graph_status, kb_id, token)
```

### Processing a Document Pipeline End-to-End

```python
async def ingest_document(api, kb_id, file_path, token, metadata=None):
    """Upload → parse → (optionally set metadata) → return doc_id."""
    # Upload
    docs = await api.document.upload(kb_id=kb_id, file_path=file_path, token=token)
    doc_id = docs[0].id

    # Parse
    await api.document.run(RunDocumentRequest(doc_ids=[doc_id], run="1"), token)

    # Wait for completion
    while True:
        info = await api.document.doc_infos(DocumentInfosRequest(doc_ids=[doc_id]), token)
        doc = info[0]
        if doc.run == "3":
            break
        if doc.run == "4":
            raise RuntimeError(f"Parsing failed: {doc.progress_msg}")
        await asyncio.sleep(5)

    # Set metadata
    if metadata:
        from ragflow_api.Document import SetMetadataRequest
        await api.document.set_metadata(SetMetadataRequest(doc_id=doc_id, meta=metadata), token)

    return doc_id
```

### Advanced Retrieval with Metadata Filtering

```python
results = await api.search.retrieval(
    RetrievalRequest(
        dataset_ids=[kb_id],
        question="revenue growth drivers",
        metadata_condition={"region": ["EMEA", "APAC"], "year": [2024]},
        top_k=20,
        similarity_threshold=0.15,
        vector_similarity_weight=0.5,
        use_kg=True,
    ),
    api_key,
)
```

### Cross-Language Retrieval

```python
results = await api.search.retrieval(
    RetrievalRequest(
        dataset_ids=[kb_id],
        question="analyse de rentabilité",       # French query
        cross_languages=["English", "French"],
        top_k=10,
    ),
    api_key,
)
```

---

## Complete End-to-End Example

```python
import asyncio
from ragflow_api import RagflowAPI
from ragflow_api.Dataset import CreateDatasetRequest, ParserType
from ragflow_api.Document import RunDocumentRequest, DocumentInfosRequest
from ragflow_api.Search import RetrievalRequest
from ragflow_api.common.entities import ParserConfig, GraphRAGConfig, RaptorConfig

async def full_pipeline():
    api = RagflowAPI("http://localhost:9380")

    # ── Auth ─────────────────────────────────────────────────────────────────
    email, password = "demo@company.com", "demo_password"
    await api.user.register_user(email, "Demo User", password)
    token = await api.user.get_token(email, password)
    api_key = await api.user.get_api_key(token)

    # ── Dataset ───────────────────────────────────────────────────────────────
    dataset = await api.dataset.create_dataset(
        CreateDatasetRequest(
            name="Annual Reports 2024",
            parser_id=ParserType.MANUAL,
            parser_config=ParserConfig(
                chunk_token_num=512,
                auto_keywords=5,
                auto_questions=3,
                toc_extraction=True,
                graphrag=GraphRAGConfig(use_graphrag=True, method="light"),
                raptor=RaptorConfig(use_raptor=True, scope="dataset"),
            ),
        ),
        token,
    )
    kb_id = dataset.kb_id
    print(f"Created dataset: {kb_id}")

    # ── Upload & parse ────────────────────────────────────────────────────────
    docs = await api.document.upload(kb_id=kb_id, file_path="annual_report_2024.pdf", token=token)
    doc_id = docs[0].id
    print(f"Uploaded document: {doc_id}")

    await api.document.run(RunDocumentRequest(doc_ids=[doc_id], run="1"), token)
    while True:
        info = await api.document.doc_infos(DocumentInfosRequest(doc_ids=[doc_id]), token)
        if info[0].run in ("3", "4"):
            break
        print(f"  Parsing... {info[0].progress:.0%}")
        await asyncio.sleep(5)
    print("Parsing complete.")

    # ── Knowledge Graph ───────────────────────────────────────────────────────
    await api.dataset.construct_knowledge_graph(kb_id, token)
    while True:
        s = await api.dataset.get_knowledge_graph_status(kb_id, token)
        print(f"  KG: {s.progress:.0%}")
        if s.progress >= 1.0:
            break
        await asyncio.sleep(15)

    # ── RAPTOR ────────────────────────────────────────────────────────────────
    await api.dataset.construct_raptor(kb_id, token)
    while True:
        s = await api.dataset.get_raptor_status(kb_id, token)
        print(f"  RAPTOR: {s.progress:.0%}")
        if s.progress >= 1.0:
            break
        await asyncio.sleep(15)

    # ── Retrieval ─────────────────────────────────────────────────────────────
    results = await api.search.retrieval(
        RetrievalRequest(
            dataset_ids=[kb_id],
            question="What are the major risks outlined in the annual report?",
            top_k=5,
            use_kg=True,
            toc_enhance=True,
        ),
        api_key,
    )

    print(f"\nTop {len(results.chunks)} results:")
    for i, chunk in enumerate(results.chunks, 1):
        print(f"\n[{i}] similarity={chunk.similarity:.3f}  doc={chunk.document_keyword}")
        print(f"    {chunk.content[:200].strip()}")

    # ── Download highlighted PDF ──────────────────────────────────────────────
    paths = await api.download_pages_and_highlight(results.chunks, "./output/", token)
    print(f"\nHighlighted PDFs: {paths}")

asyncio.run(full_pipeline())
```

---

## API Reference Index

| Module | File |
|---|---|
| `UserRagflowAPI` | `ragflow_api/User/user_api.py` |
| `DatasetRagflowAPI` | `ragflow_api/Dataset/dataset_api.py` |
| `DocumentRagflowAPI` | `ragflow_api/Document/document_api.py` |
| `SearchRagflowAPI` | `ragflow_api/Search/search_api.py` |
| `TenantRagflowAPI` | `ragflow_api/Tenant/tenant_api.py` |
| Dataset DTOs | `ragflow_api/Dataset/dataset_dto.py` |
| Document DTOs | `ragflow_api/Document/document_dto.py` |
| Search DTOs | `ragflow_api/Search/search_dto.py` |
| Shared Entities | `ragflow_api/common/entities.py` |
| Base & Exceptions | `ragflow_api/base.py` |

---

## License

See the main RAGFlow project license (`Apache 2.0`).
