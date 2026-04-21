# Changelog

All notable changes to `ragflow-api` will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [1.0.0] — 2026-02-23

### Added
- **Unified `RagflowAPI` client** — single entry-point aggregating all sub-modules.
- **`UserRagflowAPI`** — register, login, token/API-key management, team info, user settings.
- **`DatasetRagflowAPI`** — full CRUD for datasets, document ingestion, Knowledge Graph construction,
  RAPTOR hierarchical summarisation, Mindmap construction, pipeline log management, tag and metadata operations.
- **`DocumentRagflowAPI`** — document upload/download, run/cancel, metadata, thumbnails, chunk CRUD
  (create / list / get / update / delete / switch), and file-download utilities.
- **`SearchRagflowAPI`** — search-app CRUD and the `/retrieval` endpoint with support for
  `top_k`, `use_kg`, `toc_enhance`, cross-language search, metadata filtering, and re-ranking.
- **`TenantRagflowAPI`** — user invitation, role management, and invitation listing.
- **Common entities** — `ParserConfig`, `RaptorConfig`, `GraphRAGConfig`, all shared Pydantic models.
- **`RagflowAPIBase`** — RSA password encryption, URL construction, and `@requires_token` decorator.
- **`download_pdf_and_highlight`** / **`download_pages_and_highlight`** — PyMuPDF-powered
  chunk highlighting helpers on the top-level `RagflowAPI`.
- `pyproject.toml` (Poetry) for packaging, linting (`ruff`), type-checking (`mypy`) and testing (`pytest-asyncio`).
- `py.typed` PEP 561 marker for full IDE type-checking support.
- `conftest.py` with pytest fixtures for integration testing.
- Comprehensive integration test suite (`test_comprehensive_suite.py`) covering the full
  dataset → document → chunk → KG → RAPTOR → retrieval workflow.

### Dependencies
- `httpx ^0.27` — async HTTP client
- `pydantic ^2.7` — data validation
- `pycryptodome ^3.20` — RSA encryption
- `rich ^13.7` — terminal output / progress bars
- `pymupdf ^1.24` — PDF manipulation
- `anyio ^4.4` — async compatibility layer
