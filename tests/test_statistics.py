from datetime import date, timedelta
import math
import pandas as pd
import pytest
from quality_metrics import validate_daily, summarize

END = date(2026, 10, 27)


def daily(n=60, previous=10, current=20, package="VOWR"):
    return pd.DataFrame([{"Date": END - timedelta(days=i),
                          "Downloads": current if i < 30 else previous,
                          "Package": package} for i in range(n)])


def test_exact_7_30_60_day_windows_and_growth():
    summary, end = summarize(daily(), END - timedelta(days=59), END)
    r = summary.iloc[0]
    assert end == END
    assert r.Period_Downloads == 900
    assert r.Last_7_days == 140
    assert r.Last_30_days == 600
    assert r.Previous_30_days == 300
    assert r.Growth_30d_pct == pytest.approx(100)
    assert r.Coverage_pct == 100


def test_missing_day_is_not_zero_and_growth_is_undefined():
    data = daily()
    data = data[data.Date != END - timedelta(days=12)]
    summary, _ = summarize(data, END - timedelta(days=59), END)
    r = summary.iloc[0]
    assert r.Reported_Days == 59
    assert r.Coverage_pct == pytest.approx(98.3)
    assert r.Last_30_days == 580
    assert math.isnan(r.Growth_30d_pct)


def test_common_end_aligns_different_package_lags():
    a = daily(60, package="VOWR")
    b = daily(60, package="bewrs")
    b = b[b.Date != END]
    summary, end = summarize(pd.concat([a, b]), END - timedelta(days=59), END)
    assert end == END - timedelta(days=1)
    assert summary.loc[summary.Package.eq("VOWR"), "Period_Downloads"].iloc[0] == 880


def test_zero_previous_period_makes_growth_undefined():
    summary, _ = summarize(daily(previous=0), END - timedelta(days=59), END)
    assert math.isnan(summary.Growth_30d_pct.iloc[0])


def test_duplicate_days_are_aggregated():
    data = pd.DataFrame([{"Date": END, "Downloads": 3, "Package": "VOWR"},
                         {"Date": END, "Downloads": 4, "Package": "VOWR"}])
    result = validate_daily(data)
    assert len(result) == 1 and result.Downloads.iloc[0] == 7


@pytest.mark.parametrize("bad", [-1, 1.5, "not-a-number"])
def test_invalid_download_counts_rejected(bad):
    data = pd.DataFrame([{"Date": END, "Downloads": bad, "Package": "VOWR"}])
    with pytest.raises(ValueError):
        validate_daily(data)


def test_invalid_reporting_window_rejected():
    with pytest.raises(ValueError):
        summarize(daily(), END, END - timedelta(days=1))


def test_missing_required_column_rejected():
    with pytest.raises(ValueError):
        validate_daily(pd.DataFrame({"Date": [END], "Downloads": [1]}))
