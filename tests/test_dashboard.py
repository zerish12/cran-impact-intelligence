
"""Lightweight checks for CRAN Impact Intelligence without starting Streamlit."""

import ast
from pathlib import Path

SOURCE = Path(__file__).resolve().parents[1] / "app_dash.py"


def _source():
    return SOURCE.read_text(encoding="utf-8")


def test_dashboard_file_exists():
    assert SOURCE.is_file(), (
        "The Streamlit entry point app_dash.py is missing"
    )


def test_python_syntax():
    ast.parse(_source(), filename=str(SOURCE))


def test_data_fetch_function_exists():
    tree = ast.parse(_source())

    names = {
        node.name
        for node in ast.walk(tree)
        if isinstance(
            node,
            (ast.FunctionDef, ast.AsyncFunctionDef)
        )
    }

    assert "fetch_daily" in names, (
        "Expected CRANlogs data-fetching function is missing"
    )


def test_required_dashboard_features():
    source = _source()

    for phrase in (
        "CRAN Impact Intelligence",
        "CRANlogs",
        "Refresh",
        "ORCID",
        "install.packages",
    ):
        assert phrase.lower() in source.lower(), (
            f"Missing expected dashboard feature: {phrase}"
        )


def test_streamlit_entrypoint_configured():
    source = _source()

    assert "st.set_page_config" in source

    assert (
        'layout="wide"' in source
        or "layout='wide'" in source
    )
