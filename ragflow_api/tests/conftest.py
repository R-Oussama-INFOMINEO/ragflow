"""
conftest.py for the bundled ragflow_api.tests doctor suite.

Registers the ``--ragflow-url`` CLI option and provides shared fixtures.
"""

import pytest


def pytest_addoption(parser: pytest.Parser) -> None:
    """Add ``--ragflow-url`` to pytest CLI (safe — won't double-register)."""
    try:
        parser.addoption(
            "--ragflow-url",
            action="store",
            default="http://localhost:9380",
            help="Base URL of the RAGFlow server to run doctor tests against.",
        )
    except ValueError:
        pass  # already registered by a parent conftest


@pytest.fixture(scope="module")
def ragflow_url(request: pytest.FixtureRequest) -> str:
    """RAGFlow server base URL, from ``--ragflow-url`` or env RAGFLOW_BASE_URL."""
    import os

    return (
        request.config.getoption("--ragflow-url", default=None)
        or os.environ.get("RAGFLOW_BASE_URL", "http://localhost:9380")
    )


@pytest.fixture(scope="module")
def test_pdf_path() -> str:
    """Path to the test PDF: local ``./test.pdf`` if present, else the bundled one."""
    from ragflow_api.tests import get_test_file_path

    return get_test_file_path("./test.pdf")
