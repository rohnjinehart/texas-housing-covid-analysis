"""Plotly chart builders for the Texas Housing Covid Analysis dashboard."""

import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots

COVID_PIVOT = pd.Timestamp("2020-03-01")

CITY_COLORS = {
    "Dallas":      "#1f77b4",
    "Houston":     "#ff7f0e",
    "Austin":      "#2ca02c",
    "San Antonio": "#d62728",
}

_ANNOTATION_STYLE = dict(
    x=COVID_PIVOT,
    text="Covid Declared<br>(Mar 2020)",
    showarrow=True,
    arrowhead=2,
    ax=40,
    ay=-40,
    font=dict(size=11, color="#555"),
    bgcolor="rgba(255,255,255,0.8)",
    bordercolor="#aaa",
    borderwidth=1,
)


def _add_covid_line(fig: go.Figure, row: int = 1, col: int = 1) -> None:
    fig.add_vline(
        x=COVID_PIVOT.timestamp() * 1000,
        line_dash="dash",
        line_color="gray",
        line_width=1.5,
        row=row,
        col=col,
    )


# ---------------------------------------------------------------------------
# 1. Home Value Index Over Time (main trend chart)
# ---------------------------------------------------------------------------

def zhvi_time_series(df: pd.DataFrame, cities: list[str]) -> go.Figure:
    fig = go.Figure()
    for city in cities:
        cdf = df[df["city"] == city].sort_values("date")
        fig.add_trace(go.Scatter(
            x=cdf["date"],
            y=cdf["zhvi"],
            name=city,
            mode="lines",
            line=dict(color=CITY_COLORS.get(city), width=2.5),
            hovertemplate="%{x|%b %Y}<br>$%{y:,.0f}<extra>" + city + "</extra>",
        ))

    _add_covid_line(fig)
    fig.add_annotation(x=COVID_PIVOT, y=1, xref="x", yref="paper",
                       text="Mar 2020", showarrow=False,
                       font=dict(size=10, color="gray"), xanchor="left", yanchor="bottom")

    fig.update_layout(
        title="Zillow Home Value Index — Texas Major Metros",
        xaxis_title="",
        yaxis_title="Typical Home Value (USD)",
        yaxis_tickformat="$,.0f",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
        hovermode="x unified",
        template="plotly_white",
        height=480,
    )
    return fig


# ---------------------------------------------------------------------------
# 2. Year-over-Year % Change
# ---------------------------------------------------------------------------

def yoy_change_chart(df: pd.DataFrame, cities: list[str]) -> go.Figure:
    fig = go.Figure()
    for city in cities:
        cdf = df[df["city"] == city].sort_values("date").dropna(subset=["yoy_pct"])
        fig.add_trace(go.Scatter(
            x=cdf["date"],
            y=cdf["yoy_pct"],
            name=city,
            mode="lines",
            line=dict(color=CITY_COLORS.get(city), width=2),
            hovertemplate="%{x|%b %Y}<br>%{y:.1f}% YoY<extra>" + city + "</extra>",
        ))

    _add_covid_line(fig)
    fig.add_hline(y=0, line_dash="dot", line_color="black", line_width=1)
    fig.update_layout(
        title="Year-over-Year Home Price Change (%)",
        xaxis_title="",
        yaxis_title="YoY Change (%)",
        yaxis_ticksuffix="%",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
        hovermode="x unified",
        template="plotly_white",
        height=420,
    )
    return fig


# ---------------------------------------------------------------------------
# 3. Indexed comparison (base = Jan 2017 = 100)
# ---------------------------------------------------------------------------

def indexed_price_chart(df: pd.DataFrame, cities: list[str]) -> go.Figure:
    fig = go.Figure()
    base_date = df["date"].min()

    for city in cities:
        cdf = df[df["city"] == city].sort_values("date")
        base_val = cdf.loc[cdf["date"] == cdf["date"].min(), "zhvi"]
        if base_val.empty:
            base_val = cdf["zhvi"].iloc[0]
        else:
            base_val = base_val.iloc[0]

        cdf = cdf.copy()
        cdf["indexed"] = cdf["zhvi"] / base_val * 100

        fig.add_trace(go.Scatter(
            x=cdf["date"],
            y=cdf["indexed"],
            name=city,
            mode="lines",
            line=dict(color=CITY_COLORS.get(city), width=2.5),
            hovertemplate="%{x|%b %Y}<br>Index: %{y:.1f}<extra>" + city + "</extra>",
        ))

    _add_covid_line(fig)
    fig.add_hline(y=100, line_dash="dot", line_color="black", line_width=1)
    fig.update_layout(
        title=f"Indexed Home Prices (Base = {base_date.strftime('%b %Y')} = 100)",
        xaxis_title="",
        yaxis_title="Index (Base = 100)",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
        hovermode="x unified",
        template="plotly_white",
        height=450,
    )
    return fig


# ---------------------------------------------------------------------------
# 4. CAGR comparison bar chart (pre vs post)
# ---------------------------------------------------------------------------

def cagr_bar_chart(summary_df: pd.DataFrame) -> go.Figure:
    cities = summary_df["City"].tolist()
    fig = go.Figure(data=[
        go.Bar(
            name="Pre-Covid CAGR",
            x=cities,
            y=summary_df["Pre-Covid CAGR (%)"],
            marker_color="#6baed6",
            text=summary_df["Pre-Covid CAGR (%)"].apply(lambda v: f"{v:.1f}%"),
            textposition="outside",
        ),
        go.Bar(
            name="Post-Covid CAGR",
            x=cities,
            y=summary_df["Post-Covid CAGR (%)"],
            marker_color="#fd8d3c",
            text=summary_df["Post-Covid CAGR (%)"].apply(lambda v: f"{v:.1f}%"),
            textposition="outside",
        ),
    ])
    fig.update_layout(
        barmode="group",
        title="Annualised Home Price Growth (CAGR) — Pre vs. Post Covid",
        yaxis_title="CAGR (%)",
        yaxis_ticksuffix="%",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
        template="plotly_white",
        height=420,
    )
    return fig


# ---------------------------------------------------------------------------
# 5. Box plots: YoY distribution pre vs post
# ---------------------------------------------------------------------------

def yoy_boxplot(df: pd.DataFrame, cities: list[str]) -> go.Figure:
    fig = go.Figure()
    periods = ["Pre-Covid", "Post-Covid"]
    period_colors = {"Pre-Covid": "#6baed6", "Post-Covid": "#fd8d3c"}

    for period in periods:
        pdf = df[(df["period"] == period) & (df["city"].isin(cities))].dropna(subset=["yoy_pct"])
        fig.add_trace(go.Box(
            x=pdf["city"],
            y=pdf["yoy_pct"],
            name=period,
            marker_color=period_colors[period],
            boxmean=True,
        ))

    fig.add_hline(y=0, line_dash="dot", line_color="black", line_width=1)
    fig.update_layout(
        boxmode="group",
        title="Distribution of Monthly YoY Price Changes — Pre vs. Post Covid",
        yaxis_title="YoY Change (%)",
        yaxis_ticksuffix="%",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
        template="plotly_white",
        height=420,
    )
    return fig


# ---------------------------------------------------------------------------
# 6. Affordability heatmap: rolling 12-mo avg price by city × year
# ---------------------------------------------------------------------------

def price_heatmap(df: pd.DataFrame, cities: list[str]) -> go.Figure:
    hdf = df[df["city"].isin(cities)].copy()
    hdf["year"] = hdf["date"].dt.year
    pivot = hdf.groupby(["city", "year"])["zhvi"].mean().unstack("year")

    fig = go.Figure(data=go.Heatmap(
        z=pivot.values,
        x=[str(c) for c in pivot.columns],
        y=pivot.index.tolist(),
        colorscale="YlOrRd",
        text=[[f"${v:,.0f}" for v in row] for row in pivot.values],
        texttemplate="%{text}",
        textfont={"size": 11},
        colorbar=dict(title="Avg ZHVI ($)"),
        hoverongaps=False,
    ))
    fig.update_layout(
        title="Average Annual Home Value by City (ZHVI Heatmap)",
        xaxis_title="Year",
        yaxis_title="",
        template="plotly_white",
        height=350,
    )
    return fig


# ---------------------------------------------------------------------------
# 7. Acceleration scatter (CAGR delta)
# ---------------------------------------------------------------------------

def acceleration_chart(accel_df: pd.DataFrame) -> go.Figure:
    colors = [CITY_COLORS.get(c, "#333") for c in accel_df["City"]]
    fig = go.Figure(go.Bar(
        x=accel_df["City"],
        y=accel_df["CAGR Acceleration (pp)"],
        marker_color=colors,
        text=accel_df["CAGR Acceleration (pp)"].apply(lambda v: f"+{v:.1f} pp" if v >= 0 else f"{v:.1f} pp"),
        textposition="outside",
    ))
    fig.add_hline(y=0, line_dash="dot", line_color="black", line_width=1)
    fig.update_layout(
        title="Post-Covid CAGR Acceleration vs. Pre-Covid Baseline (percentage points)",
        yaxis_title="CAGR Δ (pp)",
        template="plotly_white",
        height=400,
    )
    return fig
