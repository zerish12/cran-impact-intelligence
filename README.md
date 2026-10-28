# CRAN Impact Intelligence

A Streamlit dashboard showing published CRANlogs download activity for six R packages.

## Run locally

```bash
conda activate cran_monitor
python -m pip install -r requirements.txt
python -m streamlit run app_dash.py --server.port 8506
```

## Deployment

Upload `app_dash.py` and `requirements.txt` to a GitHub repository. On Streamlit Community Cloud, select `app_dash.py` as the entry point.

## Interpretation

Download counts are not unique users, citations, or instantaneous events. API data may lag or have missing dates. Missing records are not automatically counted as zero. Growth is only calculated when both 30-day windows have complete daily observations.
