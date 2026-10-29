"""CRAN Impact Intelligence — run with: streamlit run app_dash.py"""
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime, timedelta, timezone
import time
import math
from html import escape
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

/* Stage 3: Improve link-button readability */
.stLinkButton a {
    background-color: #243b5a !important;
    color: #ffffff !important;
    border: 1px solid #4b719e !important;
    border-radius: 10px !important;
    font-weight: 600 !important;
    text-decoration: none !important;
}

.stLinkButton a:hover {
    background-color: #315583 !important;
    color: #ffffff !important;
    border-color: #7dd3fc !important;
}

/* Improve keyboard accessibility */
.stLinkButton a:focus-visible {
    outline: 3px solid #7dd3fc !important;
    outline-offset: 2px;
}

/* Improve chart and supporting text readability */
.small-note {
    color: #d0ddf0;
    font-size: 0.9rem;
}

[data-testid="stCaptionContainer"] {
    color: #c4d5ec;
}

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
