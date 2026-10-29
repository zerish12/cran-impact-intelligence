"""Offline contract tests for the *actual* fetch_daily in app_dash.py.

Extracting only its function definition avoids executing Streamlit UI at import.
All HTTP calls and sleeps are mocked; tests do not contact CRANlogs.
"""
import ast
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pandas as pd
import pytest
import requests

ROOT = Path(__file__).resolve().parents[1]


def fetch_under_test(monkeypatch, responses):
    source = ast.parse((ROOT / "app_dash.py").read_text(encoding="utf-8"))
    functions = [n for n in source.body if isinstance(n, ast.FunctionDef) and n.name == "fetch_daily"]
    assert len(functions) == 1, "Expected exactly one fetch_daily function"
    fn = functions[0]
    fn.decorator_list = []  # remove Streamlit cache decorator only in test copy
    module = ast.fix_missing_locations(ast.Module(body=[fn], type_ignores=[]))
    get = Mock(side_effect=responses)
    sleep = Mock()
    namespace = {"API": "https://cranlogs.r-pkg.org/downloads/daily",
                 "pd": pd, "requests": SimpleNamespace(get=get, RequestException=requests.RequestException),
                 "time": SimpleNamespace(sleep=sleep)}
    exec(compile(module, str(ROOT / "app_dash.py"), "exec"), namespace)
    return namespace["fetch_daily"], get, sleep


def response(payload, status=200):
    r = Mock()
    r.status_code = status
    r.json.return_value = payload
    if status >= 400:
        r.raise_for_status.side_effect = requests.HTTPError(f"HTTP {status}")
    return r


def test_valid_cranlogs_object_response(monkeypatch):
    fetch, get, _ = fetch_under_test(monkeypatch, [response({"downloads": [
        {"day": "2026-10-01", "downloads": 4}, {"day": "2026-10-02", "downloads": 7}]})])
    df, error = fetch("VOWR", "2026-10-01", "2026-10-02")
    assert error is None
    assert df.Downloads.tolist() == [4, 7]
    assert df.Package.tolist() == ["VOWR", "VOWR"]
    assert "VOWR" in get.call_args.args[0]
    assert get.call_args.kwargs["timeout"] > 0


def test_list_wrapped_response_and_duplicate_day():
    fetch, _, _ = fetch_under_test(None, [response([{"downloads": [
        {"day": "2026-10-01", "downloads": 2}, {"day": "2026-10-01", "downloads": 3}]}])])
    df, error = fetch("VOWR", "2026-10-01", "2026-10-01")
    assert error is None
    assert len(df) == 1 and df.Downloads.iloc[0] == 5


def test_empty_response_is_not_zero():
    fetch, _, _ = fetch_under_test(None, [response({"downloads": []})])
    df, error = fetch("VOWR", "2026-10-01", "2026-10-02")
    assert df.empty and error


def test_api_error_is_reported():
    fetch, _, sleep = fetch_under_test(None, [response({"error": "unavailable"})] * 3)
    df, error = fetch("VOWR", "2026-10-01", "2026-10-02")
    assert df.empty and "unavailable" in error
    assert sleep.call_count == 2


def test_retry_then_success_on_503():
    fetch, get, sleep = fetch_under_test(None, [response({}, 503), response({"downloads": [
        {"day": "2026-10-01", "downloads": 10}]})])
    df, error = fetch("VOWR", "2026-10-01", "2026-10-01")
    assert error is None and df.Downloads.sum() == 10
    assert get.call_count == 2 and sleep.call_count == 1


def test_network_timeout_exhausts_retries():
    fetch, get, _ = fetch_under_test(None, [requests.Timeout("timeout")] * 3)
    df, error = fetch("VOWR", "2026-10-01", "2026-10-01")
    assert df.empty and "timeout" in error and get.call_count == 3


def test_invalid_date_does_not_generate_fake_zero():
    fetch, _, _ = fetch_under_test(None, [response({"downloads": [
        {"day": "not-a-date", "downloads": 12}]})])
    df, error = fetch("VOWR", "2026-10-01", "2026-10-02")
    assert df.empty and error
