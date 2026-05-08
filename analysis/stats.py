"""
Statistical comparisons between pre-Covid and post-Covid housing periods.
Covid pivot: 2020-03-01
"""

import pandas as pd
import numpy as np
from scipy import stats

COVID_PIVOT = pd.Timestamp("2020-03-01")


def _split(df: pd.DataFrame, city: str) -> tuple[pd.Series, pd.Series]:
    city_df = df[df["city"] == city].sort_values("date")
    pre = city_df.loc[city_df["date"] < COVID_PIVOT, "zhvi"].dropna()
    post = city_df.loc[city_df["date"] >= COVID_PIVOT, "zhvi"].dropna()
    return pre, post


def summary_table(df: pd.DataFrame) -> pd.DataFrame:
    """
    Returns one row per city with key metrics:
      - Pre/Post median ZHVI
      - Total appreciation % (first to last in each period)
      - Annualised CAGR for each period
      - Peak ZHVI and peak date (post-Covid)
      - Peak-to-current drawdown %
      - t-test p-value comparing monthly YoY% distributions pre vs post
    """
    rows = []
    cities = df["city"].unique()

    for city in sorted(cities):
        pre, post = _split(df, city)

        def cagr(series: pd.Series) -> float:
            if len(series) < 2:
                return float("nan")
            years = (series.index[-1] - series.index[0]).days / 365.25
            if years <= 0:
                return float("nan")
            return ((series.iloc[-1] / series.iloc[0]) ** (1 / years) - 1) * 100

        # Re-attach dates for CAGR calculation
        city_df = df[df["city"] == city].sort_values("date")
        pre_s = city_df.loc[city_df["date"] < COVID_PIVOT].set_index("date")["zhvi"].dropna()
        post_s = city_df.loc[city_df["date"] >= COVID_PIVOT].set_index("date")["zhvi"].dropna()

        post_peak = post_s.max() if len(post_s) else float("nan")
        post_peak_date = post_s.idxmax() if len(post_s) else pd.NaT
        current = post_s.iloc[-1] if len(post_s) else float("nan")
        drawdown = ((current - post_peak) / post_peak * 100) if post_peak else float("nan")

        # YoY pct for t-test
        yoy_pre = city_df.loc[city_df["date"] < COVID_PIVOT, "yoy_pct"].dropna()
        yoy_post = city_df.loc[city_df["date"] >= COVID_PIVOT, "yoy_pct"].dropna()
        if len(yoy_pre) >= 2 and len(yoy_post) >= 2:
            _, pval = stats.ttest_ind(yoy_pre, yoy_post, equal_var=False)
        else:
            pval = float("nan")

        total_appr_pre = ((pre_s.iloc[-1] / pre_s.iloc[0]) - 1) * 100 if len(pre_s) >= 2 else float("nan")
        total_appr_post = ((post_s.iloc[-1] / post_s.iloc[0]) - 1) * 100 if len(post_s) >= 2 else float("nan")

        rows.append({
            "City": city,
            "Pre-Covid Median ($)": int(pre_s.median()) if len(pre_s) else float("nan"),
            "Post-Covid Median ($)": int(post_s.median()) if len(post_s) else float("nan"),
            "Pre-Covid Total Appr. (%)": round(total_appr_pre, 1),
            "Post-Covid Total Appr. (%)": round(total_appr_post, 1),
            "Pre-Covid CAGR (%)": round(cagr(pre_s), 2),
            "Post-Covid CAGR (%)": round(cagr(post_s), 2),
            "Post-Covid Peak ($)": int(post_peak) if not np.isnan(post_peak) else float("nan"),
            "Post-Covid Peak Date": post_peak_date,
            "Peak-to-Current (%)": round(drawdown, 1),
            "YoY t-test p-value": round(pval, 4) if not np.isnan(pval) else float("nan"),
        })

    return pd.DataFrame(rows)


def monthly_change_summary(df: pd.DataFrame) -> pd.DataFrame:
    """Return avg monthly YoY% by city and period."""
    return (
        df.groupby(["city", "period"])["yoy_pct"]
        .agg(["mean", "std", "min", "max"])
        .rename(columns={"mean": "Avg YoY%", "std": "Std Dev", "min": "Min YoY%", "max": "Max YoY%"})
        .round(2)
        .reset_index()
    )


def acceleration_since_covid(df: pd.DataFrame) -> pd.DataFrame:
    """
    For each city: how much faster/slower did prices rise post-Covid
    vs. pre-Covid annualised rate?
    """
    tbl = summary_table(df)[["City", "Pre-Covid CAGR (%)", "Post-Covid CAGR (%)"]].copy()
    tbl["CAGR Acceleration (pp)"] = (tbl["Post-Covid CAGR (%)"] - tbl["Pre-Covid CAGR (%)"]).round(2)
    return tbl
