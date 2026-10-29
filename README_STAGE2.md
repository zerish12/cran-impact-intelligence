# Stage 2 — CRAN Impact Intelligence validation

## What this does

- **Does not modify `app_dash.py`** or the Streamlit deployment.
- `tests/test_api_validation.py` extracts and tests the real `fetch_daily` function from `app_dash.py` without launching Streamlit. It mocks HTTP and retries; no external API access required.
- `quality_metrics.py` is a **reference calculation module**, with `tests/test_statistics.py` checking window boundaries, missing data, growth, alignment, and invalid values.
- The reference calculations are **not yet used by the live dashboard**. Stage 3 can integrate them after review; do not describe them as live runtime validation.

## Upload to GitHub (on branch `stage2-api-validation`)

1. Create the branch from `main` using GitHub's branch selector.
2. Upload `quality_metrics.py` to repository root.
3. Upload `tests/test_api_validation.py` and `tests/test_statistics.py` under `tests/`.
4. Leave `app_dash.py`, `requirements.txt`, `.github/workflows/python-ci.yml`, and `tests/test_dashboard.py` unchanged.
5. Commit to branch `stage2-api-validation`.
6. Open a pull request from `stage2-api-validation` into `main`. The existing Python CI runs pytest and should discover the new tests.
7. Inspect the CI result and diff before merging. Only merge when checks pass.

## Run locally

```bash
python -m pip install -r requirements.txt pytest
python -m pytest -q tests/
```

## Caveats

The current app's parser drops malformed records and may accept fractional download counts; reference validation rejects such counts. These are intentionally *different policies* and are not claimed to be resolved by adding tests. The current app's KPI label 'Last 30 calendar days' may represent fewer days if a shorter reporting window is selected; this requires a later UI improvement. Existing CI checks run after a push; to prevent direct deployment of failing commits, configure branch protection and use PRs.
