"""
ragflow_api.tests
~~~~~~~~~~~~~~~~~

Bundled integration / "doctor" test suite for :pypi:`ragflow-api`.

After installing the library anyone can verify their RAGFlow server is
functioning correctly:

**CLI (recommended)**::

    ragflow-api doctor --url http://localhost:9380

**Python -m shortcut**::

    python -m ragflow_api doctor --url http://localhost:9380

**Programmatic**::

    from ragflow_api.tests import run_doctor
    exit_code = run_doctor("http://localhost:9380")

**Bare pytest** (useful in CI)::

    python -m pytest $(python -c "import ragflow_api.tests as t; print(t.TESTS_DIR)") -v -s
"""

import os
import pathlib

# Absolute path to this tests/ package directory
TESTS_DIR: pathlib.Path = pathlib.Path(__file__).parent.resolve()

# Bundled minimal PDF used by the integration test
BUNDLED_TEST_PDF: pathlib.Path = TESTS_DIR / "data" / "test.pdf"


def get_test_file_path(prefer_local: str = "./test.pdf") -> str:
    """
    Return the path to the test PDF.

    Preference order:
    1. ``prefer_local`` if that file exists on disk (useful for dev / richer docs)
    2. The minimal PDF bundled inside the package

    Args:
        prefer_local: Path to check first (default ``./test.pdf``).

    Returns:
        Absolute path string to the PDF to use.
    """
    local = pathlib.Path(prefer_local)
    if local.is_file():
        return str(local.resolve())
    return str(BUNDLED_TEST_PDF)


def run_doctor(url: str = "http://localhost:9380", *, verbose: bool = True) -> int:
    """
    Run the comprehensive integration test suite against *url* and return the
    pytest exit code (0 = all passed).

    Args:
        url:     RAGFlow server base URL.
        verbose: Pass ``-v -s`` to pytest when ``True`` (default).

    Returns:
        pytest exit code integer — ``0`` means everything passed.
    """
    import pytest  # local import so pytest is optional at import time

    test_file = str(TESTS_DIR / "test_comprehensive_suite.py")
    args = [
        test_file,
        "--override-ini=asyncio_mode=auto",
        f"--ragflow-url={url}",
    ]
    if verbose:
        args += ["-v", "-s", "--tb=short"]

    return pytest.main(args)


__all__ = [
    "TESTS_DIR",
    "BUNDLED_TEST_PDF",
    "get_test_file_path",
    "run_doctor",
]
