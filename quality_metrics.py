"""Pure reference calculations for CRAN download-data quality audits.

Not imported by the Streamlit app in Stage 2; this is a testable reference
implementation, not a claim that the dashboard has been refactored.
"""
from datetime import date, timedelta
import pandas as pd

COLUMNS = ["Date", "Downloads", "Package"]


def validate_daily(frame: pd.DataFrame) -> pd.DataFrame:
    """Validate an already parsed daily table; do not invent missing days."""
    if not set(COLUMNS).issubset(frame.columns):
        raise ValueError("Missing required daily data columns")
    data = frame[COLUMNS].copy()
    data["Date"] = pd.to_datetime(data["Date"], errors="coerce")
    if data["Date"].isna().any() or data["Package"].isna().any():
        raise ValueError("Invalid dates or package names")
    if not (data["Date"].dt.normalize() == data["Date"]).all():
        raise ValueError("Dates must be daily, without time-of-day")
    numeric = pd.to_numeric(data["Downloads"], errors="coerce")
    if numeric.isna().any() or (numeric < 0).any() or (numeric % 1 != 0).any():
        raise ValueError("Download counts must be nonnegative integers")
    data["Downloads"] = numeric.astype("int64")
    return data.groupby(["Package", "Date"], as_index=False)["Downloads"].sum()


def summarize(frame: pd.DataFrame, start: date, end: date) -> tuple[pd.DataFrame, date]:
    """Align packages to earliest latest-observed day and compute metrics.

    Returns summary and common_end. Missing days are not filled with zeros.
    Growth is NaN unless the full current and previous 30-day windows exist.
    """
    if start > end:
        raise ValueError("start must be <= end")
    data = validate_daily(frame)
    data = data[data["Date"].dt.date.between(start, end)].copy()
    if data.empty:
        raise ValueError("No observations in reporting window")
    common_end = data.groupby("Package")["Date"].max().min().date()
    data = data[data["Date"].dt.date <= common_end]
    expected = (common_end - start).days + 1
    rows = []
    for pkg, part in data.groupby("Package"):
        day_counts = dict(zip(part["Date"].dt.date, part["Downloads"]))
        last7 = sum(v for d, v in day_counts.items() if common_end - timedelta(days=6) <= d <= common_end)
        last30 = sum(v for d, v in day_counts.items() if common_end - timedelta(days=29) <= d <= common_end)
        prev30 = sum(v for d, v in day_counts.items() if common_end - timedelta(days=59) <= d < common_end - timedelta(days=29))
        complete60 = all(common_end - timedelta(days=i) in day_counts for i in range(60))
        growth = 100 * (last30 / prev30 - 1) if complete60 and prev30 > 0 else float("nan")
        rows.append({"Package": pkg, "Period_Downloads": int(part["Downloads"].sum()),
                     "Last_7_days": int(last7), "Last_30_days": int(last30),
                     "Previous_30_days": int(prev30), "Growth_30d_pct": growth,
                     "Reported_Days": len(day_counts), "Expected_Days": expected,
                     "Coverage_pct": round(100 * len(day_counts) / expected, 1)})
    return pd.DataFrame(rows).sort_values("Package").reset_index(drop=True), common_end
