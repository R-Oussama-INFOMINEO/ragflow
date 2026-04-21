"""
ragflow_api._doctor
~~~~~~~~~~~~~~~~~~~

CLI entry-point for the ragflow-api "doctor" command.

Installed as the ``ragflow-api`` console script by Poetry / pip, so after
``pip install ragflow-api`` users simply run::

    ragflow-api doctor --url http://my-ragflow-server:9380

Or as a Python module::

    python -m ragflow_api doctor --url http://my-ragflow-server:9380
"""

from __future__ import annotations

import argparse
import sys

# ---------------------------------------------------------------------------
# Sub-command implementations
# ---------------------------------------------------------------------------


def _doctor(args: argparse.Namespace) -> int:
    """
    Run the comprehensive integration test suite against *args.url*.

    Returns the pytest exit code (0 = all passed).
    """
    try:
        import pytest
    except ImportError:
        print(
            "ERROR: 'pytest' is not installed.\nInstall it with:  pip install pytest pytest-asyncio",
            file=sys.stderr,
        )
        return 1

    from ragflow_api.tests import TESTS_DIR

    test_file = str(TESTS_DIR / "test_comprehensive_suite.py")

    pytest_args = [
        test_file,
        f"--ragflow-url={args.url}",
        "--override-ini=asyncio_mode=auto",
        "--override-ini=addopts=",  # ignore repo-level addopts (e.g. --strict-markers)
        "--tb=short",
    ]

    if args.verbose:
        pytest_args += ["-v", "-s"]
    else:
        pytest_args += ["-q"]

    if args.timeout:
        # Pass as a marker override via ini — individual tests handle their own timeouts
        pytest_args += [f"--override-ini=timeout={args.timeout}"]

    return pytest.main(pytest_args)


def _info(_args: argparse.Namespace) -> int:
    """Print library and server info."""
    import importlib.metadata as meta

    try:
        version = meta.version("ragflow-api")
    except meta.PackageNotFoundError:
        version = "unknown"

    from ragflow_api.tests import BUNDLED_TEST_PDF, TESTS_DIR

    print(f"ragflow-api  v{version}")
    print(f"Tests dir  : {TESTS_DIR}")
    print(f"Bundled PDF: {BUNDLED_TEST_PDF}")
    return 0


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(
        prog="ragflow-api",
        description=(
            "ragflow-api — Internal RAGFlow Python client toolkit.\n\n"
            "Sub-commands:\n"
            "  doctor   Run the end-to-end integration test suite against a server.\n"
            "  info     Show library and test asset paths.\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = root.add_subparsers(dest="command", required=True)

    # -- doctor ---------------------------------------------------------------
    doctor_p = sub.add_parser(
        "doctor",
        help="Run the comprehensive integration / health-check test suite.",
        description=(
            "Verifies that a RAGFlow server is fully operational by running the\n"
            "complete end-to-end workflow: user creation → dataset → document ingest →\n"
            "retrieval → KG → RAPTOR → Mindmap → cleanup."
        ),
    )
    doctor_p.add_argument(
        "--url",
        default="http://localhost:9380",
        metavar="URL",
        help="RAGFlow server base URL  (default: http://localhost:9380)",
    )
    doctor_p.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        default=True,
        help="Pass -v -s to pytest for detailed output (default: True).",
    )
    doctor_p.add_argument(
        "--quiet",
        "-q",
        dest="verbose",
        action="store_false",
        help="Suppress detailed pytest output.",
    )
    doctor_p.add_argument(
        "--timeout",
        type=int,
        default=None,
        metavar="SECONDS",
        help="Override individual step timeouts (seconds).",
    )

    # -- info -----------------------------------------------------------------
    sub.add_parser("info", help="Show library version and bundled test asset paths.")

    return root


# ---------------------------------------------------------------------------
# Entry-point
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> None:
    """Console script entry-point: ``ragflow-api``."""
    parser = build_parser()
    args = parser.parse_args(argv)

    dispatch = {
        "doctor": _doctor,
        "info": _info,
    }
    handler = dispatch.get(args.command)
    if handler is None:
        parser.print_help()
        sys.exit(1)

    sys.exit(handler(args))


if __name__ == "__main__":
    main()
