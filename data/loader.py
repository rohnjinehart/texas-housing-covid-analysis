"""
Data loader for Texas housing price data.

Primary source: Zillow Research ZHVI (Zillow Home Value Index) — Metro & US
public CSV, no API key needed.

Fallback / supplement: FRED API for Case-Shiller Dallas index and FHFA
all-transactions HPI for each MSA.

Covid pivot date: 2020-03-01 (WHO pandemic declaration month).
"""

import os
import io
import requests
import pandas as pd
import numpy as np
from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

COVID_PIVOT = pd.Timestamp("2020-03-01")
PRE_COVID_START = pd.Timestamp("2017-01-01")

CITIES = {
    "Dallas":      "Dallas, TX",
    "Houston":     "Houston, TX",
    "Austin":      "Austin, TX",
    "San Antonio": "San Antonio, TX",
}

ZHVI_METRO_URL = (
    "https://files.zillowstatic.com/research/public_csvs/zhvi/"
    "Metro_zhvi_uc_sfrcondo_tier_0.33_0.67_sm_sa_month.csv"
)

FRED_SERIES = {
    "Dallas":      "DAXRNSA",
    "Houston":     "HOUX",
    "Austin":      "ATNHPIUS12420Q",
    "San Antonio": "ATNHPIUS41700Q",
}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _fred_api_key() -> str | None:
    return os.getenv("FRED_API_KEY")


def _fetch_fred_series(series_id: str) -> pd.Series | None:
    key = _fred_api_key()
    if not key:
        return None
    try:
        from fredapi import Fred
        fred = Fred(api_key=key)
        s = fred.get_series(series_id)
        s.index = pd.to_datetime(s.index)
        s = s.resample("MS").interpolate(method="linear")
        return s
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Primary: Zillow ZHVI
# ---------------------------------------------------------------------------

LOCAL_ZHVI_PATH = os.path.join(os.path.dirname(__file__), "zhvi_metro.csv")


def load_zhvi_raw() -> pd.DataFrame:
    """Load ZHVI metro CSV from local file if present, otherwise download it."""
    if os.path.exists(LOCAL_ZHVI_PATH):
        return pd.read_csv(LOCAL_ZHVI_PATH)
    resp = requests.get(ZHVI_METRO_URL, timeout=60)
    resp.raise_for_status()
    return pd.read_csv(io.StringIO(resp.text))


def _parse_zhvi(df_raw: pd.DataFrame) -> pd.DataFrame:
    mask = df_raw["RegionName"].isin(CITIES.values())
    df = df_raw[mask].copy()

    inv = {v: k for k, v in CITIES.items()}
    df["city"] = df["RegionName"].map(inv)

    date_cols = [c for c in df.columns if len(c) == 10 and c[4] == "-"]
    df_long = df[["city"] + date_cols].melt(id_vars="city", var_name="date", value_name="zhvi")
    df_long["date"] = pd.to_datetime(df_long["date"])
    df_long = df_long.dropna(subset=["zhvi"])
    df_long = df_long[df_long["date"] >= PRE_COVID_START]
    return df_long.sort_values(["city", "date"]).reset_index(drop=True)


# ---------------------------------------------------------------------------
# Supplement: FRED (optional)
# ---------------------------------------------------------------------------

def load_fred_supplement() -> dict:
    out = {}
    for city, series_id in FRED_SERIES.items():
        s = _fetch_fred_series(series_id)
        if s is not None:
            out[city] = s
    return out


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def load_housing_data(zhvi_raw: pd.DataFrame) -> pd.DataFrame:
    """
    Return tidy long-form DataFrame:
      date, city, zhvi, yoy_pct, period
    """
    df = _parse_zhvi(zhvi_raw)

    df = df.sort_values(["city", "date"])
    df["yoy_pct"] = (
        df.groupby("city")["zhvi"]
        .pct_change(periods=12)
        .mul(100)
        .round(2)
    )

    df["period"] = np.where(df["date"] < COVID_PIVOT, "Pre-Covid", "Post-Covid")
    return df


def load_all(zhvi_raw: pd.DataFrame) -> tuple:
    housing = load_housing_data(zhvi_raw)
    fred = load_fred_supplement()
    return housing, fred
