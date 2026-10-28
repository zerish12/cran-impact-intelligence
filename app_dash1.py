"""CRAN Impact Intelligence — run with: streamlit run app_dash.py"""
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime, timedelta, timezone
import time
import math
import requests
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

st.set_page_config(page_title="CRAN Impact Intelligence", page_icon="📦", layout="wide", initial_sidebar_state="collapsed")
PACKAGES = ["VOWR", "nhscancerwaits", "bewrs", "CRBHSF", "AdaptiveTrialsR", "BayesSurveillance"]
COLORS = dict(zip(PACKAGES, ["#38bdf8", "#a78bfa", "#34d399", "#fb7185", "#fbbf24", "#22d3ee"]))
API = "https://cranlogs.r-pkg.org/downloads/daily"
MIN_DATE = date(2012, 7, 1)

st.markdown("""<style>
:root {color-scheme:dark}
.stApp {background:linear-gradient(120deg,#091225,#101c34 55%,#121b30);color:#e8efff}
.block-container {padding-top:1.4rem;max-width:1650px;width:96%;padding-bottom:2.5rem}
[data-testid="stHeader"] {background:transparent}
[data-testid="stSidebar"] {display:none}
h1,h2,h3,p {color:#e8efff}
h1 {letter-spacing:-.045em}
[data-testid="stMetric"] {background:#182842;border:1px solid #304666;border-radius:17px;padding:18px;min-height:124px}
[data-testid="stMetricLabel"] {color:#b9c9e2}
[data-testid="stMetricValue"] {color:#fff}
[data-testid="stVerticalBlockBorderWrapper"] {border-color:#304666!important}
.stButton button[kind="primary"] {background:#2563eb;color:white;border:0}
.stTabs [data-baseweb="tab"] {color:#c5d5ee}
.stTabs [aria-selected="true"] {color:#67d3ff!important}
[data-testid="stSelectbox"] label,[data-testid="stMultiSelect"] label,[data-testid="stDateInput"] label {color:#cbd5e1!important}
[data-testid="stMarkdownContainer"] a {color:#7dd3fc}
.small-note {font-size:.82rem;color:#a8bbd4}
.hero {padding:22px 24px;border-radius:20px;background:linear-gradient(115deg,#152b4a,#12213a 55%,#1b2546);border:1px solid #304b73;margin-bottom:16px}
.hero .eyebrow {color:#7dd3fc;letter-spacing:.14em;font-size:.72rem;font-weight:750}
.hero .heading {font-size:2.25rem;letter-spacing:-.045em;font-weight:800;color:#f8fbff;margin:5px 0}
.hero .sub {color:#b6c8e2;font-size:.91rem}
.package-card {min-height:146px;background:#182842;border:1px solid #334969;border-radius:16px;padding:16px;margin-bottom:10px}
.package-card .name {font-size:.9rem;font-weight:700;color:#f1f5ff;overflow-wrap:anywhere}
.package-card .number {font-size:1.8rem;font-weight:800;color:#fff;margin:7px 0}
.package-card .detail {font-size:.78rem;color:#b4c7e0}
.package-card .line {height:5px;border-radius:8px;background:#34445c;margin-top:13px;overflow:hidden}
.package-card .fill {height:5px;border-radius:8px}
@media(max-width:800px){.block-container{width:100%;padding-left:1rem;padding-right:1rem}.hero .heading{font-size:1.65rem}}
.author-panel{padding:19px 24px;margin:0 0 20px;border:1px solid #385276;border-radius:16px;background:linear-gradient(115deg,#172844,#20395c);color:#fff}
.author-panel .author-label{font-size:.7rem;letter-spacing:.13em;font-weight:700;color:#a8c9ef}
.author-panel .author-name{font-size:1.4rem;font-weight:800;color:#fff;margin:7px 0 3px}
.author-panel .author-details{font-size:.87rem;color:#d4e2f4;line-height:1.7}
.author-panel a{color:#a8d5ff!important;text-decoration:none;font-weight:600}
</style>""", unsafe_allow_html=True)

@st.cache_data(ttl=900, show_spinner=False)
def fetch_daily(package, start, end):
    url = f"{API}/{start}:{end}/{package}"
    last_error = "Unknown API error"
    for attempt in range(3):
        try:
            response = requests.get(url, timeout=40, headers={"User-Agent": "CRAN-Impact-Intelligence/3.0"})
            if response.status_code in (429, 500, 502, 503, 504) and attempt < 2:
                time.sleep(attempt + 1)
                continue
            response.raise_for_status()
            payload = response.json()
            if isinstance(payload, list) and len(payload) == 1 and isinstance(payload[0], dict):
                payload = payload[0]
            if isinstance(payload, dict):
                if payload.get("error"):
                    raise ValueError(str(payload["error"]))
                records = payload.get("downloads")
            elif isinstance(payload, list):
                records = payload
            else:
                raise ValueError("Unexpected API JSON response")
            if not isinstance(records, list):
                return pd.DataFrame(columns=["Date", "Downloads", "Package"]), "No daily observations returned (check exact CRAN package name)"
            rows = []
            for item in records:
                if not isinstance(item, dict):
                    continue
                day, count = item.get("day", item.get("date")), item.get("downloads")
                if day is not None and isinstance(count, (int, float)) and count >= 0:
                    rows.append((day, count, package))
            frame = pd.DataFrame(rows, columns=["Date", "Downloads", "Package"])
            if frame.empty:
                return frame, "No valid daily observations in this reporting window"
            frame["Date"] = pd.to_datetime(frame["Date"], errors="coerce")
            frame = frame.dropna(subset=["Date"])
            frame = frame.groupby(["Package", "Date"], as_index=False)["Downloads"].sum()
            if frame.empty:
                return frame, "No parseable dates returned by API"
            return frame, None
        except (requests.RequestException, ValueError) as exc:
            last_error = str(exc)
            if attempt < 2:
                time.sleep(attempt + 1)
    return pd.DataFrame(columns=["Date", "Downloads", "Package"]), last_error

st.markdown('''<div class="hero"><div class="eyebrow">RESEARCH SOFTWARE • PUBLIC ANALYTICS</div><div class="heading">📦 CRAN Impact Intelligence</div><div class="sub">Six R packages · Published CRAN download activity · Transparent reporting and reproducible analytics</div></div>''', unsafe_allow_html=True)

# Verified author attribution is independent of the CRANlogs API.
st.markdown("""<section class="author-panel" aria-label="Author and maintainer">
<div class="author-label">AUTHOR &amp; RESEARCH SOFTWARE DEVELOPER</div>
<div class="author-name">Dr Muhammad Zahir Khan</div>
<div class="author-details">PhD in Applied Statistics · Applied Statistician<br>
Sole Author &amp; Maintainer of Six R Packages</div>
<div class="author-details" style="margin-top:10px">
<a href="https://orcid.org/0009-0005-7645-8960" target="_blank" rel="noopener noreferrer">ORCID: 0009-0005-7645-8960</a>
&nbsp; · &nbsp;
<a href="https://github.com/zerish12" target="_blank" rel="noopener noreferrer">GitHub: zerish12</a>
</div></section>""", unsafe_allow_html=True)

# Horizontal filters instead of an old-fashioned permanent sidebar.
left, mid, right, refresh_col = st.columns([1.65, 1.05, 1.05, .75], vertical_alignment="bottom")
with left:
    selected = st.multiselect("Packages", PACKAGES, default=PACKAGES, help="All six packages are selected by default.")
with mid:
    window = st.selectbox("Reporting period", ["Last 90 days", "Last 365 days", "Last 30 days", "All available", "Custom"], index=1)
with right:
    auto = st.selectbox("Automatic refresh", ["Off", "15 minutes", "30 minutes", "60 minutes"], index=2)
with refresh_col:
    manual_refresh = st.button("↻ Refresh", type="primary", width="stretch")

if manual_refresh:
    fetch_daily.clear()
    st.session_state["last_manual_refresh_utc"] = datetime.now(timezone.utc).strftime("%d %b %Y %H:%M:%S UTC")
    st.rerun()

if auto != "Off":
    # Streamlit fragments run while the browser session is active.
    # Clearing the cache ensures a scheduled refresh actually refetches data.
    interval_minutes = int(auto.split()[0])
    @st.fragment(run_every=f"{interval_minutes}m")
    def refresh_pulse():
        now = datetime.now(timezone.utc)
        stamp = int(now.timestamp() // (interval_minutes * 60))
        previous = st.session_state.get("refresh_stamp")
        if previous is None:
            st.session_state["refresh_stamp"] = stamp
        elif previous != stamp:
            st.session_state["refresh_stamp"] = stamp
            fetch_daily.clear()
            st.rerun(scope="app")
    refresh_pulse()
else:
    st.session_state.pop("refresh_stamp", None)

if st.session_state.get("last_manual_refresh_utc"):
    st.caption("↻ Manual refresh requested: " + st.session_state["last_manual_refresh_utc"] +
               " · CRANlogs may not yet have published newer daily observations.")

today = datetime.now(timezone.utc).date()
if window == "Custom":
    a, b = st.columns(2)
    with a:
        start = st.date_input("From", today - timedelta(days=365), min_value=MIN_DATE, max_value=today)
    with b:
        end = st.date_input("Through", today, min_value=MIN_DATE, max_value=today)
else:
    n = {"Last 30 days":30,"Last 90 days":90,"Last 365 days":365}.get(window)
    start = today - timedelta(days=n-1) if n else MIN_DATE
    end = today
if not selected:
    st.info("Select at least one package to begin.")
    st.stop()
if start > end:
    st.error("The start date must not be later than the end date.")
    st.stop()

frames, errors = [], {}
with st.spinner("Loading published CRANlogs data..."):
    with ThreadPoolExecutor(max_workers=min(6, len(selected))) as pool:
        jobs = {pool.submit(fetch_daily, p, start.isoformat(), end.isoformat()):p for p in selected}
        for job in as_completed(jobs):
            pkg = jobs[job]
            try:
                data, error = job.result()
                if error: errors[pkg] = error
                else: frames.append(data)
            except Exception as exc:
                errors[pkg] = str(exc)

if errors:
    with st.expander(f"⚠️ Data unavailable for {len(errors)} package(s)", expanded=True):
        for pkg, error in errors.items():
            st.warning(f"{pkg}: {error}")
        st.caption("Unavailable packages are not counted as zero; they are excluded from totals.")
if not frames:
    st.error("No valid daily observations were retrieved. Check the connection or choose another reporting window.")
    st.stop()

raw = pd.concat(frames, ignore_index=True)
raw = raw[(raw.Date.dt.date >= start) & (raw.Date.dt.date <= end)]
latest = raw.groupby("Package").Date.max()
common_end = latest.min()
df = raw[raw.Date <= common_end].copy()
# Compare only dates in the requested period, with a common latest published date.
# Missing daily records remain missing; they are never silently converted to zero.
expected_days = (common_end.date() - start).days + 1
coverage = df.groupby("Package").Date.nunique().to_dict()
coverage_gaps = {p: expected_days - int(coverage.get(p, 0)) for p in df.Package.unique()}
if any(v > 0 for v in coverage_gaps.values()):
    with st.expander("ℹ️ Reporting-day coverage", expanded=False):
        st.caption("Missing API dates are not assumed to represent zero downloads. Totals reflect returned observations only.")
        st.dataframe(pd.DataFrame([{"Package": p, "Reported days": coverage[p],
            "Calendar days": expected_days, "Unreported days": coverage_gaps[p]} for p in coverage]),
            hide_index=True, width="stretch")
cut7, cut30, cut60 = (common_end - pd.Timedelta(days=d) for d in (6,29,59))
summary = df.groupby("Package", as_index=False).agg(Period_Downloads=("Downloads","sum"), Reported_Days=("Date","nunique"))
for field, low, high in [("Last_7_days",cut7,common_end),("Last_30_days",cut30,common_end),("Previous_30_days",cut60,cut30-pd.Timedelta(days=1))]:
    values = df[(df.Date >= low)&(df.Date <= high)].groupby("Package").Downloads.sum()
    summary[field] = summary.Package.map(values).fillna(0).astype(int)
# Only calculate growth when both complete 30-day calendar windows are selected
# and each package has a record for every calendar date in those windows.
def valid_growth(pkg):
    dates = set(df.loc[df.Package.eq(pkg), "Date"].dt.normalize())
    return all((common_end - pd.Timedelta(days=i)).normalize() in dates for i in range(60))

summary["Growth_30d_pct"] = summary.apply(
    lambda r: 100 * (r.Last_30_days / r.Previous_30_days - 1)
    if r.Previous_30_days > 0 and valid_growth(r.Package) else float("nan"), axis=1)
summary["Coverage_pct"] = summary.Package.map(lambda p: round(100 * coverage.get(p, 0) / expected_days, 1))
summary = summary.sort_values("Period_Downloads", ascending=False)
total = int(summary.Period_Downloads.sum())
max_total = max(summary.Period_Downloads.max(),1)

st.caption(f"📅 Selected window: {start:%d %b %Y} – {end:%d %b %Y}   ·   Latest common published day: {common_end:%d %b %Y}   ·   Checked: {datetime.now(timezone.utc):%d %b %Y %H:%M UTC}")
if len(frames) < len(selected):
    st.info(f"Coverage: {len(frames)} of {len(selected)} selected packages. Totals are partial.")
if latest.max() != common_end:
    st.info("Package reporting dates differ. Comparisons use the earliest latest-published day.")
if start > cut60.date():
    st.caption("Note: growth rates require 60 complete calendar days; unavailable values are shown as blank.")

k1,k2,k3,k4 = st.columns(4)
k1.metric("Downloads · selected period",f"{total:,}")
k2.metric("Last 30 calendar days",f"{int(summary.Last_30_days.sum()):,}")
k3.metric("Last 7 calendar days",f"{int(summary.Last_7_days.sum()):,}")
k4.metric("Top package · period",str(summary.iloc[0].Package))

st.markdown("### Package portfolio")
card_rows = [PACKAGES[:3], PACKAGES[3:]]
lookup = summary.set_index("Package")
from html import escape
for row_packages in card_rows:
    cols = st.columns(3)
    for col,pkg in zip(cols,row_packages):
        with col:
            if pkg in lookup.index:
                r = lookup.loc[pkg]
                n = int(r.Period_Downloads)
                bar = min(100, 100*n/max_total)
                text = f"{int(r.Last_30_days):,} in last 30 days · {int(r.Last_7_days):,} in last 7"
                number = f"{n:,}"
            else:
                bar, text, number = 0, "Not selected / no available data", "—"
            st.markdown(f'''<div class="package-card"><div class="name">{escape(pkg)}</div><div class="number">{number}</div><div class="detail">{escape(text)}</div><div class="line"><div class="fill" style="width:{bar:.1f}%;background:{COLORS[pkg]}"></div></div></div>''',unsafe_allow_html=True)
            st.link_button("CRAN package ↗", f"https://cran.r-project.org/package={pkg}", width="stretch")

trend_tab, rank_tab, growth_tab, export_tab = st.tabs(["📈 Trends", "🏆 Comparison", "📊 Activity & growth", "⬇️ Export & methodology"])
with trend_tab:
    granularity = st.segmented_control("Time grouping",["Daily","Weekly","Monthly"],default="Monthly")
    freq = {"Daily":"D","Weekly":"W-MON","Monthly":"MS"}[granularity]
    trend = df.set_index("Date").groupby("Package").resample(freq).Downloads.sum().reset_index()
    fig = px.line(trend,x="Date",y="Downloads",color="Package",color_discrete_map=COLORS,markers=granularity!="Daily",template="plotly_dark")
    fig.update_layout(height=480,hovermode="x unified",legend=dict(orientation="h",y=-.2),paper_bgcolor="rgba(0,0,0,0)",plot_bgcolor="rgba(0,0,0,0)",margin=dict(t=20,b=25))
    st.plotly_chart(fig,width="stretch")
    st.caption("Published daily download counts; weekly/monthly buckets can be partial at the reporting boundaries.")
with rank_tab:
    fig=px.bar(summary,x="Package",y="Period_Downloads",color="Package",text="Period_Downloads",color_discrete_map=COLORS,template="plotly_dark")
    fig.update_traces(texttemplate="%{text:,}",textposition="outside")
    fig.update_layout(showlegend=False,height=440,paper_bgcolor="rgba(0,0,0,0)",plot_bgcolor="rgba(0,0,0,0)")
    st.plotly_chart(fig,width="stretch")
    st.dataframe(summary,hide_index=True,width="stretch")
with growth_tab:
    if summary.Growth_30d_pct.isna().any():
        st.info("Blank growth rates mean the two 30-day windows are incomplete, or the previous period has zero recorded downloads.")
    st.dataframe(summary[["Package","Last_7_days","Last_30_days","Previous_30_days","Growth_30d_pct"]],hide_index=True,width="stretch")
    # A portfolio daily total is valid only when all successfully loaded
    # packages have a record on that calendar date.
    n_packages = df.Package.nunique()
    daily = df.groupby("Date", as_index=False).agg(
        Downloads=("Downloads", "sum"), Packages_Reported=("Package", "nunique"))
    daily = daily.set_index("Date").reindex(pd.date_range(start, common_end.date(), freq="D"))
    daily.index.name = "Date"
    daily.loc[daily.Packages_Reported.ne(n_packages), "Downloads"] = float("nan")
    daily["Rolling_7_day"] = daily.Downloads.rolling(7, min_periods=7).mean()
    daily = daily.reset_index()
    fig=px.line(daily,x="Date",y=["Downloads","Rolling_7_day"],template="plotly_dark",labels={"value":"Downloads","variable":"Series"})
    fig.update_layout(height=420,paper_bgcolor="rgba(0,0,0,0)",plot_bgcolor="rgba(0,0,0,0)")
    st.plotly_chart(fig,width="stretch")
    st.caption("Seven-day rolling mean is shown only when all seven consecutive calendar dates have observations for every loaded package. Gaps remain missing.")
with export_tab:
    st.download_button("Download original daily records (CSV)",raw.to_csv(index=False).encode(),"cran_daily_records.csv","text/csv")
    st.download_button("Download aligned comparison records (CSV)",df.to_csv(index=False).encode(),"cran_aligned_records.csv","text/csv")
    st.download_button("Download comparison summary (CSV)",summary.to_csv(index=False).encode(),"cran_summary.csv","text/csv")
    st.dataframe(raw.sort_values(["Package","Date"]),hide_index=True,width="stretch")
    st.markdown("**Methodology:** Source: [CRANlogs](https://cranlogs.r-pkg.org/). Counts are published download events, not unique users, installations, citations, or live download events. Automated downloads may be included. Package availability and completeness of historical coverage are not guaranteed. All-time figures require selecting *All available*. The dashboard uses a shared latest-published date, but earlier missing reporting days are not filled. Growth rates require 60 complete calendar days. Packages with unavailable data are excluded.")

st.divider()
st.caption("© 2026 Dr Muhammad Zahir Khan · Research software portfolio · ORCID: 0009-0005-7645-8960 · Source: CRANlogs · Not an official CRAN analytics service")

# ==========================================================
# PACKAGE INSTALLATION AND DOCUMENTATION
# ==========================================================

st.markdown("---")
st.subheader("📦 Download and Install R Packages")

st.caption(
    "Install packages directly in R, visit their CRAN pages, "
    "or access the available source code."
)

cran_packages = [
    "VOWR",
    "nhscancerwaits",
    "bewrs",
    "CRBHSF",
]

github_packages = {
    "AdaptiveTrialsR": "zerish12/AdaptiveTrialsR",
    "BayesSurveillance": "zerish12/BayesSurveillance",
}

for package in cran_packages:
    with st.expander(f"📦 {package}", expanded=False):
        st.code(
            f'install.packages("{package}")',
            language="r"
        )

        col1, col2 = st.columns(2)

        with col1:
            st.link_button(
                "📥 CRAN Download",
                f"https://cran.r-project.org/package={package}",
                use_container_width=True
            )

        with col2:
            st.link_button(
                "📖 Documentation",
                f"https://cran.r-project.org/web/packages/"
                f"{package}/{package}.pdf",
                use_container_width=True
            )

for package, repo in github_packages.items():
    with st.expander(f"📦 {package} (GitHub)", expanded=False):
        st.code(
            f'remotes::install_github("{repo}")',
            language="r"
        )

        st.link_button(
            "💻 View GitHub Repository",
            f"https://github.com/{repo}",
            use_container_width=True
        )