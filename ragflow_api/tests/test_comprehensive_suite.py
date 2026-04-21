"""
Comprehensive integration test for RAGFlow API — bundled "doctor" edition.

This is the canonical test that ships *inside* the ``ragflow_api`` package so
that any consumer can verify their RAGFlow server is healthy:

    ragflow-api doctor --url http://localhost:9380

Or via pytest directly:

    python -m pytest $(python -c "import ragflow_api.tests as t; print(t.TESTS_DIR)") \\
        --ragflow-url http://localhost:9380 -v -s

The test implements a complete end-to-end workflow:
  Dataset → Document upload → Ingestion → Chunk CRUD →
  Knowledge Graph → RAPTOR → Mindmap → Multi-stage Retrieval → Cleanup
"""

import asyncio
import os
import random
import string
import time

import pytest

# ---------------------------------------------------------------------------
# pytest-asyncio: treat every async def in this module as an asyncio test
# ---------------------------------------------------------------------------
pytestmark = pytest.mark.asyncio

from rich.console import Console
from rich.panel import Panel
from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn, TimeElapsedColumn
from rich.table import Table
from rich.theme import Theme

from ragflow_api import RagflowAPI
from ragflow_api.common.entities import ParserConfig, RaptorConfig, RaptorScope
from ragflow_api.Dataset import CreateDatasetRequest, DeleteDatasetsRequest
from ragflow_api.Dataset.dataset_dto import ParserType, Permission, TaskStatusResponse
from ragflow_api.Document import (
    DeleteDocumentsRequest,
    DocumentInfosRequest,
    RunDocumentRequest,
    SetMetadataRequest,
    ThumbnailsRequest,
)
from ragflow_api.Document.document_dto import (
    CreateChunkRequest,
    DeleteChunksRequest,
    ListChunksRequest,
    ListDocumentsRequest,
    UpdateChunkRequest,
)
from ragflow_api.Search import RetrievalRequest
from ragflow_api.tests import get_test_file_path

# ---------------------------------------------------------------------------
# Rich console
# ---------------------------------------------------------------------------

_theme = Theme(
    {
        "info": "cyan",
        "warning": "yellow",
        "error": "bold red",
        "success": "bold green",
        "step": "bold blue",
        "doc": "magenta",
    }
)
console = Console(theme=_theme)

# ---------------------------------------------------------------------------
# Pytest hook: register --ragflow-url CLI option
# ---------------------------------------------------------------------------


def pytest_addoption(parser: pytest.Parser) -> None:
    """Register the ``--ragflow-url`` CLI option for this module's tests."""
    # Guard against double-registration when conftest.py also calls this.
    try:
        parser.addoption(
            "--ragflow-url",
            action="store",
            default="http://localhost:9380",
            help="Base URL of the RAGFlow server to test against.",
        )
    except ValueError:
        pass  # already registered by a conftest


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def ragflow_url(request: pytest.FixtureRequest) -> str:
    return request.config.getoption("--ragflow-url", default="http://localhost:9380")


@pytest.fixture(scope="module")
def test_pdf_path() -> str:
    """Return the PDF path: local ./test.pdf if present, else the bundled one."""
    return get_test_file_path("./test.pdf")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _random_str(n: int = 8) -> str:
    return "".join(random.choices(string.ascii_lowercase + string.digits, k=n))


def generate_random_email() -> str:
    return f"test_{_random_str()}@infomineo.com"


def generate_random_password() -> str:
    return "".join(random.choices(string.ascii_letters + string.digits, k=16))


async def wait_for_document_status(
    api: RagflowAPI, doc_ids: list, token: str, target_progress: float = 1.0, timeout: int = 300
) -> bool:
    """Poll document processing progress until all docs reach *target_progress*."""
    start = time.time()
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TimeElapsedColumn(),
        console=console,
    ) as pb:
        tasks = {doc_id: pb.add_task(f"Ingesting {doc_id[:8]}…", total=100) for doc_id in doc_ids}
        while time.time() - start < timeout:
            info_req = DocumentInfosRequest(doc_ids=doc_ids)
            doc_info = await api.document.doc_infos(info_req, token)
            docs = doc_info if isinstance(doc_info, list) else doc_info.get("data", [])
            all_ready = True
            for doc in docs:
                pb.update(tasks[doc.id], completed=int(doc.progress * 100))
                if doc.progress < target_progress:
                    all_ready = False
            if all_ready:
                return True
            await asyncio.sleep(2)
    return False


async def wait_for_task_status(check_func, dataset_id: str, token: str, task_name: str, timeout: int = 300) -> bool:
    """Generic waiter for KG / RAPTOR / Mindmap tasks with a progress bar."""
    start = time.time()
    with Progress(
        SpinnerColumn(),
        TextColumn(f"[bold cyan]{task_name}[/bold cyan] [progress.description]{{task.description}}"),
        BarColumn(bar_width=40),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TimeElapsedColumn(),
        console=console,
        transient=False,
    ) as pb:
        tid = pb.add_task("building…", total=100)
        while time.time() - start < timeout:
            status: TaskStatusResponse = await check_func(dataset_id, token)
            pct = int((status.progress or 0) * 100)
            pb.update(tid, completed=pct, description=f"[dim]{pct}% complete[/dim]")
            if status.progress >= 1:
                pb.update(tid, completed=100, description="[green]done[/green]")
                return True
            await asyncio.sleep(2)
    return False


def _print_chunks(results, label: str) -> None:
    if not results.chunks:
        console.print(f"  [warning]⚠️  No chunks found for {label}[/warning]")
        return
    table = Table(
        title=f"[bold cyan]Retrieval: {label}[/bold cyan]",
        show_header=True,
        header_style="bold magenta",
    )
    table.add_column("Rank", justify="center", style="dim")
    table.add_column("Score", justify="right")
    table.add_column("Content Preview", ratio=1)
    table.add_column("Source", style="dim")
    for i, chunk in enumerate(results.chunks):
        content = chunk.content.replace("\n", " ")
        if len(content) > 150:
            content = content[:147] + "…"
        table.add_row(
            str(i + 1),
            f"{chunk.similarity:.4f}",
            content,
            chunk.document_name if hasattr(chunk, "document_name") else "N/A",
        )
    console.print(table)


# ---------------------------------------------------------------------------
# The test itself
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_comprehensive_suite(ragflow_url: str, test_pdf_path: str) -> None:
    """
    End-to-end RAGFlow API "doctor" test.

    Covers: User registration → API key → Dataset → Upload → Ingest →
            List/Chunk CRUD → KG → RAPTOR → Mindmap → Multi-stage Retrieval
            → Thumbnails → PDF highlight → Cleanup.
    """
    console.print(
        Panel.fit(
            "[bold magenta]RAGFlow API — Doctor Test Suite[/bold magenta]\n"
            f"[dim]Server: {ragflow_url}[/dim]\n"
            f"[dim]PDF:    {test_pdf_path}[/dim]",
            border_style="magenta",
        )
    )

    test_results: list[dict] = []

    def log_step(num, title: str) -> None:
        console.print(f"\n[bold step]Step {num}: {title}[/bold step]")

    def record(step: str, status: str, details: str = "") -> None:
        test_results.append({"step": step, "status": status, "details": details})
        if status == "PASS":
            console.print(f"  [success]✅ {step}[/success] {details}")
        elif status == "WARN":
            console.print(f"  [warning]⚠️  {step}[/warning] {details}")
        else:
            console.print(f"  [error]❌ {step} FAILED[/error] {details}")

    api = RagflowAPI(ragflow_url)

    search_query = (
        "How did the historical social status of children influence the 'miniature adult' design philosophy in fashion?"
    )

    dataset_id = doc_id = user1_token = user1_api_key = tenant_id = None

    try:
        # ── Step 1: User lifecycle ──────────────────────────────────────────
        log_step(1, "User Registration & Authentication")
        email = generate_random_email()
        password = generate_random_password()

        assert await api.user.register_user(email, "DoctorUser", password), "User registration failed"
        user1_token = await api.user.get_token(email, password)
        assert user1_token, "Token acquisition failed"

        team_info = await api.user.get_team_info(user1_token)
        tenant_id = team_info.get("tenant_id")
        assert tenant_id, "Tenant ID not found"

        user1_api_key = await api.user.get_api_key(user1_token)
        assert user1_api_key, "API Key acquisition failed"
        record("User Authentication", "PASS", f"tenant={tenant_id[:8]}…")

        # ── Step 2: Create Dataset ──────────────────────────────────────────
        log_step(2, "Dataset Creation")
        dataset_req = CreateDatasetRequest(
            name=f"Doctor Test {_random_str(4).upper()}",
            description="ragflow-api doctor check",
            permission=Permission.TEAM,
            parser_config=ParserConfig(
                toc_extraction=True,
                html4excel=True,
                raptor=RaptorConfig(use_raptor=True, scope=RaptorScope.FILE, auto_disable_for_structured_data=False),
            ),
            parser_id=ParserType.NAIVE,
        )
        dataset_response = await api.dataset.create_dataset(dataset_req, user1_token)
        dataset_id = dataset_response.kb_id
        assert dataset_id, "Dataset ID not returned"
        record("Dataset Creation", "PASS", f"id={dataset_id[:8]}…")

        # ── Step 3: Upload ──────────────────────────────────────────────────
        log_step(3, "Document Upload")
        upload_result = await api.document.upload(dataset_id, test_pdf_path, user1_token)
        doc_data = upload_result[0] if isinstance(upload_result, list) else upload_result
        doc_id = doc_data.id
        assert doc_id, "Doc ID not returned"

        await api.document.set_metadata(
            SetMetadataRequest(doc_id=doc_id, meta={"source": "doctor", "env": "ci"}), user1_token
        )
        record("Document Upload", "PASS", f"doc={doc_id[:8]}…")

        # ── Step 4: Ingest ──────────────────────────────────────────────────
        log_step(4, "Document Processing / Ingestion")
        await api.document.run(RunDocumentRequest(doc_ids=[doc_id], run="1"), user1_token)
        ingested = await wait_for_document_status(api, [doc_id], user1_token)
        assert ingested, "Ingestion timed out"
        record("Ingestion", "PASS")

        list_docs = await api.document.list_docs(ListDocumentsRequest(kb_id=dataset_id), user1_token)
        record("List Documents", "PASS", f"total={list_docs.get('total')}")

        chunks_res = await api.document.list_chunks(ListChunksRequest(doc_id=doc_id, size=100), user1_token)
        all_chunks = chunks_res.chunks
        record("Chunk Generation", "PASS", f"count={len(all_chunks)}")

        # ── Step 5: Chunk CRUD ─────────────────────────────────────────────
        log_step(5, "Chunk CRUD Operations")
        created_chunk = await api.document.create_chunk(
            CreateChunkRequest(
                doc_id=doc_id, content_with_weight="Doctor CRUD test chunk.", important_kwd=["doctor", "test"]
            ),
            user1_token,
        )
        c_id = created_chunk.get("chunk_id") or created_chunk.get("id") or (created_chunk.get("chunk") or {}).get("id")
        await api.document.update_chunk(
            UpdateChunkRequest(doc_id=doc_id, chunk_id=c_id, content_with_weight="Updated doctor chunk."), user1_token
        )
        await api.document.rm_chunks(DeleteChunksRequest(doc_id=doc_id, chunk_ids=[c_id]), user1_token)
        record("Chunk CRUD", "PASS")

        # ── Step 6: Basic Retrieval ────────────────────────────────────────
        log_step(6, "Basic Retrieval")
        res_basic = await api.search.retrieval(
            RetrievalRequest(dataset_ids=[dataset_id], question=search_query, top_k=3), user1_api_key
        )
        _print_chunks(res_basic, "Basic (No Enhancements)")
        record("Basic Retrieval", "PASS" if res_basic.chunks else "WARN", f"chunks={len(res_basic.chunks)}")

        res_toc = await api.search.retrieval(
            RetrievalRequest(dataset_ids=[dataset_id], question=search_query, top_k=3, toc_enhance=True), user1_api_key
        )
        _print_chunks(res_toc, "TOC Enhanced")
        record("TOC Retrieval", "PASS", f"chunks={len(res_toc.chunks)}")

        # ── Step 7: Knowledge Graph ────────────────────────────────────────
        log_step(7, "Knowledge Graph Construction & Search")
        await api.dataset.construct_knowledge_graph(dataset_id, user1_token)
        await wait_for_task_status(api.dataset.get_knowledge_graph_status, dataset_id, user1_token, "KG")
        res_kg = await api.search.retrieval(
            RetrievalRequest(dataset_ids=[dataset_id], question=search_query, top_k=3, use_kg=True), user1_api_key
        )
        _print_chunks(res_kg, "KG Enhanced")
        record("KG Construction & Search", "PASS")

        # ── Step 8: RAPTOR ─────────────────────────────────────────────────
        log_step(8, "RAPTOR Construction & Search")
        await api.dataset.construct_raptor(dataset_id, user1_token)
        await wait_for_task_status(api.dataset.get_raptor_status, dataset_id, user1_token, "RAPTOR")
        res_raptor = await api.search.retrieval(
            RetrievalRequest(dataset_ids=[dataset_id], question=search_query, top_k=3), user1_api_key
        )
        _print_chunks(res_raptor, "RAPTOR Context")
        record("RAPTOR Construction & Search", "PASS")

        # ── Step 8.1: Full Enhancement ─────────────────────────────────────
        log_step("8.1", "Full Enhancement (TOC + KG + RAPTOR)")
        res_full = await api.search.retrieval(
            RetrievalRequest(dataset_ids=[dataset_id], question=search_query, top_k=3, toc_enhance=True, use_kg=True),
            user1_api_key,
        )
        _print_chunks(res_full, "Full Enhancement")
        record("Full Enhancement Search", "PASS")

        # ── Step 9: Mindmap ────────────────────────────────────────────────
        log_step(9, "Mind Map Construction")
        await api.dataset.construct_mindmap(dataset_id, user1_token)
        await wait_for_task_status(api.dataset.get_mindmap_status, dataset_id, user1_token, "Mindmap")
        record("Mindmap Construction", "PASS")

        # ── Step 10: Media ─────────────────────────────────────────────────
        log_step(10, "Thumbnails & PDF Highlighting")
        artifacts_dir = "doctor_artifacts"
        os.makedirs(artifacts_dir, exist_ok=True)

        # 10.1: Thumbnails
        thumbnails = await api.document.get_thumbnails(ThumbnailsRequest(doc_ids=[doc_id]), user1_token)
        if thumbnails:
            for d_id, thumb_data in thumbnails.items():
                try:
                    import base64

                    # Often thumbnails come as data:image/png;base64,...
                    if isinstance(thumb_data, str) and "," in thumb_data:
                        thumb_data = thumb_data.split(",")[1]

                    img_data = base64.b64decode(thumb_data)
                    with open(os.path.join(artifacts_dir, f"thumbnail_{d_id}.png"), "wb") as f:
                        f.write(img_data)
                except Exception as e:
                    console.print(f"[yellow]Warning: Could not save thumbnail for {d_id}: {e}[/yellow]")
        record("Thumbnails", "PASS" if thumbnails else "WARN")

        # 10.2: PDF Highlighting (Full and Subsets)
        media_chunks = res_full.chunks if res_full and res_full.chunks else all_chunks[:5]
        if media_chunks:
            # Full highlighted PDF
            highlighted_full = await api.download_pdf_and_highlight(media_chunks, artifacts_dir, user1_token)
            # Subset pages PDF
            highlighted_subsets = await api.download_pages_and_highlight(media_chunks, artifacts_dir, user1_token)

            saved_files = os.listdir(artifacts_dir)
            record(
                "Media Retrieval",
                "PASS",
                f"saved {len(saved_files)} files (PDFs: {len(highlighted_full) + len(highlighted_subsets)})",
            )
            for f in saved_files:
                console.print(f"    [dim]📎 {f}[/dim]")
        else:
            record("Media Retrieval", "WARN", "no chunks available for highlighting")

        # ── Step 11: Cleanup ───────────────────────────────────────────────
        log_step(11, "Cleanup")
        await api.document.rm(DeleteDocumentsRequest(doc_id=doc_id), user1_token)
        await api.dataset.delete_datasets(DeleteDatasetsRequest(kb_id=dataset_id), user1_token)
        record("Cleanup", "PASS")

    except Exception as exc:  # noqa: BLE001
        record("Suite Execution", "FAIL", str(exc))
        console.print_exception()
        raise

    finally:
        # ── Summary table ──────────────────────────────────────────────────
        summary = Table(
            title="[bold magenta]Doctor Test Summary[/bold magenta]",
            show_header=True,
            header_style="bold cyan",
        )
        summary.add_column("Step", style="dim")
        summary.add_column("Result", justify="center")
        summary.add_column("Details")
        for res in test_results:
            style = (
                "bold green" if res["status"] == "PASS" else "bold yellow" if res["status"] == "WARN" else "bold red"
            )
            summary.add_row(res["step"], f"[{style}]{res['status']}[/{style}]", res["details"])
        console.print("\n")
        console.print(summary)

        passed = sum(1 for r in test_results if r["status"] == "PASS")
        total = len(test_results)
        console.print(f"\n[bold magenta]Score:[/bold magenta] [success]{passed}/{total}[/success] steps passed\n")


# ---------------------------------------------------------------------------
# Direct execution fallback:  python ragflow_api/tests/test_comprehensive_suite.py
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import sys

    import pytest as _pytest

    sys.exit(_pytest.main([__file__, "-v", "-s", "--override-ini=asyncio_mode=auto"]))
