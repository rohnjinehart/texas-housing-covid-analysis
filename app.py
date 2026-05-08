"""
Texas Housing Market — Covid Impact Analysis
Streamlit dashboard comparing pre- and post-Covid housing prices across
Dallas, Houston, Austin, and San Antonio.

Run:  streamlit run app.py
"""

import streamlit as st
import pandas as pd
import numpy as np

from data.loader import load_zhvi_raw, load_all, CITIES, COVID_PIVOT
from analysis.stats import summary_table, monthly_change_summary, acceleration_since_covid
from charts.plots import (
    zhvi_time_series,
    yoy_change_chart,
    indexed_price_chart,
    cagr_bar_chart,
    yoy_boxplot,
    price_heatmap,
    acceleration_chart,
)

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Texas Housing: Covid Impact",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Cached data fetch
# ---------------------------------------------------------------------------

@st.cache_data(ttl=3600, show_spinner="Downloading Zillow ZHVI data…")
def _cached_zhvi() -> pd.DataFrame:
    return load_zhvi_raw()


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
st.sidebar.title("Texas Housing Dashboard")
st.sidebar.markdown("### Filters")

all_cities = list(CITIES.keys())
selected_cities = st.sidebar.multiselect(
    "Select cities",
    options=all_cities,
    default=all_cities,
)

date_range = st.sidebar.date_input(
    "Date range",
    value=[pd.Timestamp("2017-01-01"), pd.Timestamp("2025-12-31")],
    min_value=pd.Timestamp("2010-01-01"),
    max_value=pd.Timestamp("2026-04-01"),
)

st.sidebar.markdown("---")
st.sidebar.markdown(
    "**Data source:** [Zillow Research ZHVI](https://www.zillow.com/research/data/) "
    "— All Homes, Metro-level, monthly.  \n"
    "Covid pivot date: **March 2020**"
)

if not selected_cities:
    st.warning("Please select at least one city from the sidebar.")
    st.stop()

# ---------------------------------------------------------------------------
# Load & filter data
# ---------------------------------------------------------------------------
with st.spinner("Loading housing data…"):
    zhvi_raw = _cached_zhvi()
    df, fred = load_all(zhvi_raw)

start_date = pd.Timestamp(date_range[0])
end_date   = pd.Timestamp(date_range[1]) if len(date_range) > 1 else df["date"].max()

mask = (
    df["city"].isin(selected_cities) &
    (df["date"] >= start_date) &
    (df["date"] <= end_date)
)
df_filtered = df[mask].copy()

if df_filtered.empty:
    st.error("No data for the selected cities / date range.")
    st.stop()

summary = summary_table(df)   # always use full date range for stats
accel   = acceleration_since_covid(df)

# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------
st.title("🏠 Texas Housing Market: Covid Impact Analysis")
st.markdown(
    "This dashboard examines how the Covid-19 pandemic reshaped housing prices "
    "across the four major Texas metros — **Dallas**, **Houston**, **Austin**, and "
    "**San Antonio** — using Zillow's Home Value Index (ZHVI).  \n"
    f"The **Covid pivot** is set at **March 2020** (WHO pandemic declaration)."
)

# ---------------------------------------------------------------------------
# KPI row
# ---------------------------------------------------------------------------
kpi_cols = st.columns(len(selected_cities))
for col, city in zip(kpi_cols, selected_cities):
    row = summary[summary["City"] == city]
    if row.empty:
        continue
    row = row.iloc[0]
    city_df = df[df["city"] == city].sort_values("date")
    latest_val = city_df["zhvi"].iloc[-1]
    latest_date = city_df["date"].iloc[-1]
    pre_val = city_df.loc[city_df["date"] < COVID_PIVOT, "zhvi"]
    pre_last = pre_val.iloc[-1] if not pre_val.empty else np.nan
    delta = ((latest_val - pre_last) / pre_last * 100) if not np.isnan(pre_last) else 0

    col.metric(
        label=f"{city}",
        value=f"${latest_val:,.0f}",
        delta=f"{delta:+.1f}% since pre-Covid",
        help=f"Typical home value as of {latest_date.strftime('%b %Y')}",
    )

st.markdown("---")

# ---------------------------------------------------------------------------
# Tab layout
# ---------------------------------------------------------------------------
tab1, tab2, tab3, tab4 = st.tabs([
    "📈 Price Trends",
    "📊 Comparative Analysis",
    "📋 Statistics",
    "ℹ️ About",
])

# ── Tab 1: Price Trends ────────────────────────────────────────────────────
with tab1:
    st.subheader("Home Value Index Over Time")
    st.plotly_chart(zhvi_time_series(df_filtered, selected_cities), use_container_width=True)

    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Year-over-Year % Change")
        st.plotly_chart(yoy_change_chart(df_filtered, selected_cities), use_container_width=True)
    with c2:
        st.subheader("Indexed Price Growth (Base = Start of Range)")
        st.plotly_chart(indexed_price_chart(df_filtered, selected_cities), use_container_width=True)

    st.subheader("Annual Average Home Value Heatmap")
    st.plotly_chart(price_heatmap(df_filtered, selected_cities), use_container_width=True)

# ── Tab 2: Comparative Analysis ───────────────────────────────────────────
with tab2:
    st.subheader("Pre vs. Post-Covid Growth Rate (CAGR)")
    st.markdown(
        "CAGR = Compound Annual Growth Rate. Pre-Covid window spans from the start "
        "of available data to February 2020; post-Covid from March 2020 onward."
    )
    st.plotly_chart(cagr_bar_chart(summary[summary["City"].isin(selected_cities)]), use_container_width=True)

    c1, c2 = st.columns(2)
    with c1:
        st.subheader("YoY Distribution — Pre vs. Post Covid")
        st.plotly_chart(yoy_boxplot(df_filtered, selected_cities), use_container_width=True)
    with c2:
        st.subheader("Covid-Driven Price Acceleration")
        st.markdown(
            "How many percentage points faster (or slower) did each city "
            "appreciate post-Covid compared to its pre-Covid trend?"
        )
        st.plotly_chart(
            acceleration_chart(accel[accel["City"].isin(selected_cities)]),
            use_container_width=True,
        )

# ── Tab 3: Statistics ─────────────────────────────────────────────────────
with tab3:
    st.subheader("Summary Statistics by City")

    display_cols = [
        "City",
        "Pre-Covid Median ($)", "Post-Covid Median ($)",
        "Pre-Covid CAGR (%)", "Post-Covid CAGR (%)",
        "Pre-Covid Total Appr. (%)", "Post-Covid Total Appr. (%)",
        "Post-Covid Peak ($)", "Post-Covid Peak Date",
        "Peak-to-Current (%)",
        "YoY t-test p-value",
    ]
    disp = summary[summary["City"].isin(selected_cities)][display_cols].copy()
    disp["Post-Covid Peak Date"] = disp["Post-Covid Peak Date"].dt.strftime("%b %Y")
    disp["Pre-Covid Median ($)"] = disp["Pre-Covid Median ($)"].apply(lambda v: f"${v:,.0f}")
    disp["Post-Covid Median ($)"] = disp["Post-Covid Median ($)"].apply(lambda v: f"${v:,.0f}")
    disp["Post-Covid Peak ($)"] = disp["Post-Covid Peak ($)"].apply(lambda v: f"${v:,.0f}")

    st.dataframe(disp.set_index("City"), use_container_width=True)

    st.markdown("---")
    st.subheader("Average YoY% by City and Period")
    mc = monthly_change_summary(df[df["city"].isin(selected_cities)])
    st.dataframe(mc, use_container_width=True)

    st.markdown("---")
    st.subheader("Key Findings")
    for _, row in summary[summary["City"].isin(selected_cities)].iterrows():
        city = row["City"]
        accel_row = accel[accel["City"] == city]
        accel_pp = accel_row["CAGR Acceleration (pp)"].iloc[0] if not accel_row.empty else 0
        pval = row["YoY t-test p-value"]
        sig = "statistically significant (p < 0.05)" if pval < 0.05 else "not statistically significant"
        peak_date = row["Post-Covid Peak Date"]
        peak_date_str = peak_date.strftime("%b %Y") if not pd.isnull(peak_date) else "N/A"
        st.markdown(
            f"**{city}** — Post-Covid CAGR was **{row['Post-Covid CAGR (%)']:.1f}%** vs. "
            f"pre-Covid **{row['Pre-Covid CAGR (%)']:.1f}%** "
            f"({accel_pp:+.1f} pp acceleration). "
            f"The shift in monthly YoY growth is {sig} (p = {pval:.4f}).  \n"
            f"Median home value rose from **${row['Pre-Covid Median ($)']:,}** to "
            f"**${row['Post-Covid Median ($)']:,}**, "
            f"peaking at **${row['Post-Covid Peak ($)']:,}** in {peak_date_str}."
        )

# ── Tab 4: About ──────────────────────────────────────────────────────────
with tab4:
    st.subheader("About This Dashboard")
    st.markdown("""
**Data**
- **Zillow Home Value Index (ZHVI)** — Smoothed, seasonally adjusted, monthly home values
  for the 35th–65th percentile of the housing stock. Metro-level CSV downloaded directly
  from [Zillow Research](https://www.zillow.com/research/data/).
- Supplemental FRED data (Case-Shiller Dallas, FHFA HPI) available if a free
  [FRED API key](https://fred.stlouisfed.org/docs/api/api_key.html) is set in `.env`.

**Methodology**
- **Covid pivot:** March 2020 (WHO pandemic declaration).
- **CAGR:** Compound Annual Growth Rate computed from first to last value in each period.
- **YoY%:** Month-over-month 12-period lag on ZHVI.
- **t-test:** Welch's two-sample t-test comparing monthly YoY% distributions
  pre- vs. post-Covid (unequal variance assumed).

**Cities**
| Short Name | MSA |
|---|---|
| Dallas | Dallas-Fort Worth-Arlington, TX |
| Houston | Houston-The Woodlands-Sugar Land, TX |
| Austin | Austin-Round Rock-Georgetown, TX |
| San Antonio | San Antonio-New Braunfels, TX |

**Macro Context**
The pandemic catalysed several housing-market shocks simultaneously:
record-low mortgage rates (2020–2021), remote-work migration into Texas metros,
supply-chain constraints reducing new-home construction, and a subsequent rate
correction cycle (2022–2023) as the Fed raised rates aggressively.
This dashboard lets you visually and statistically decompose those effects.
    """)
