# Texas Housing: Covid Impact Analysis

A Streamlit dashboard that compares housing prices across the four major Texas metros before and after the Covid-19 pandemic. Uses Zillow's Home Value Index as the primary data source.

**Cities covered:** Dallas, Houston, Austin, San Antonio  
**Covid pivot date:** March 2020 (WHO pandemic declaration)  
**Data range:** January 2017 onward

---

## Setup

```bash
pip install -r requirements.txt
streamlit run app.py
```

The app downloads the Zillow ZHVI metro CSV on first run (~4 MB) and caches it for one hour. To skip the download, place the CSV at `data/zhvi_metro.csv`. Download it from [Zillow Research](https://www.zillow.com/research/data/) under *Home Values → ZHVI All Homes (SFR, Condo/Co-op) → Metro & US*.

**Optional:** Add a free [FRED API key](https://fred.stlouisfed.org/docs/api/api_key.html) to a `.env` file to enable supplemental Case-Shiller and FHFA data:

```
FRED_API_KEY=your_key_here
```

---

## Data Source

**Zillow Home Value Index (ZHVI)** is a monthly, smoothed, seasonally adjusted estimate of the typical home value within a metro. It targets the 35th–65th percentile of the housing stock — not the median sale price — which makes it more stable and less sensitive to the mix of homes sold in any given month. Values represent what a typical mid-tier home is worth, not what recently sold homes transacted at.

The metro-level series used here map to the following MSAs:

| Label | MSA |
|---|---|
| Dallas | Dallas-Fort Worth-Arlington, TX |
| Houston | Houston-The Woodlands-Sugar Land, TX |
| Austin | Austin-Round Rock-Georgetown, TX |
| San Antonio | San Antonio-New Braunfels, TX |

---

## Dashboard Layout

### KPI Cards (top of page)

One card per selected city showing:
- Current ZHVI (most recent month in the data)
- Percentage change from the last pre-Covid reading (Feb 2020) to the current value

### Tab 1 — Price Trends

**Home Value Index Over Time**  
Raw ZHVI values plotted as a time series for each city. A vertical dashed line marks March 2020. This is the baseline view — it shows absolute price levels and lets you see when each city's price trajectory changed.

**Year-over-Year % Change**  
For each month, the percentage change in ZHVI compared to the same month 12 months prior. This removes seasonal effects and shows the rate of appreciation rather than the level. Spikes in 2021–2022 reflect the post-Covid demand surge; the deceleration and negative readings in 2023–2024 reflect the rate correction period.

**Indexed Price Growth**  
All cities rebased to 100 at the start of the selected date range. This normalizes for absolute price differences between cities so you can compare growth trajectories directly. A city at 150 has appreciated 50% from the base date regardless of its starting dollar value.

**Annual Average Home Value Heatmap**  
A grid of average ZHVI by city and calendar year, colored from low (yellow) to high (red). Makes it easy to see which city accelerated fastest in which year and how the post-Covid years compare to the pre-Covid baseline at a glance.

### Tab 2 — Comparative Analysis

**Pre vs. Post-Covid CAGR**  
Side-by-side grouped bar chart showing the annualized compound growth rate for each city in each period. See the CAGR definition below.

**YoY Distribution — Box Plots**  
For each city, two box plots show the distribution of all monthly YoY% readings in the pre-Covid period versus the post-Covid period. The box covers the interquartile range (25th–75th percentile), the line inside is the median, the diamond is the mean, and the whiskers extend to 1.5× IQR. Outliers are plotted individually. This shows not just whether prices rose faster post-Covid, but whether the distribution shifted, widened, or became more volatile.

**CAGR Acceleration**  
A single bar per city showing how many percentage points the post-Covid CAGR exceeds (or falls short of) the pre-Covid CAGR. A positive value means prices compounded faster post-Covid than pre-Covid.

### Tab 3 — Statistics

**Summary Table**

One row per city with the following columns:

| Column | Description |
|---|---|
| Pre-Covid Median ($) | Median ZHVI across all months from Jan 2017 through Feb 2020 |
| Post-Covid Median ($) | Median ZHVI across all months from Mar 2020 onward |
| Pre-Covid Total Appr. (%) | Cumulative appreciation from the first to the last month of the pre-Covid window |
| Post-Covid Total Appr. (%) | Cumulative appreciation from Mar 2020 to the most recent month |
| Pre-Covid CAGR (%) | Annualized compound growth rate over the pre-Covid window |
| Post-Covid CAGR (%) | Annualized compound growth rate over the post-Covid window |
| Post-Covid Peak ($) | Highest ZHVI recorded in the post-Covid period |
| Post-Covid Peak Date | Month in which the post-Covid peak occurred |
| Peak-to-Current (%) | Percentage drawdown from post-Covid peak to most recent value; negative means prices have pulled back from the peak |
| YoY t-test p-value | p-value from Welch's t-test (see below) |

**Average YoY% by City and Period**  
Mean, standard deviation, minimum, and maximum of all monthly YoY% readings grouped by city and period. Standard deviation here measures price volatility — how consistently prices were growing or contracting month to month.

**Key Findings**  
Auto-generated text summary for each city stating the CAGR before and after Covid, the acceleration in percentage points, whether the shift is statistically significant, and the peak value and date.

---

## Statistics Definitions

### CAGR (Compound Annual Growth Rate)

```
CAGR = (end_value / start_value) ^ (1 / years) - 1
```

Expresses the rate at which a value would have grown each year if it grew at a constant rate over the period. The pre-Covid window runs from the first available data point to Feb 2020; the post-Covid window runs from Mar 2020 to the latest data point. Both are expressed as percentages.

### Year-over-Year % Change (YoY)

```
YoY(t) = (ZHVI(t) - ZHVI(t-12)) / ZHVI(t-12) * 100
```

The percentage change in ZHVI compared to the same month one year earlier. Uses a 12-month lag so that each data point compares to the equivalent month in the prior year, eliminating seasonal variation.

### Total Appreciation

```
Total Appr. = (last_value / first_value - 1) * 100
```

Raw cumulative return over the full period, not annualized.

### Peak-to-Current Drawdown

```
Drawdown = (current - peak) / peak * 100
```

How far the most recent ZHVI sits below the post-Covid high. A value of -8% means prices have fallen 8% from their peak. A value of 0% means prices are at or above the peak.

### Welch's Two-Sample t-test

Tests whether the mean of monthly YoY% readings in the pre-Covid period is statistically different from the mean in the post-Covid period. Welch's variant is used instead of Student's t-test because it does not assume the two groups have equal variance — the post-Covid period had significantly higher variance in most cities.

- **Null hypothesis:** The mean YoY% is the same in both periods.
- **p-value < 0.05:** The difference in means is statistically significant at the 95% confidence level. The shift in the pace of appreciation is unlikely to be due to random variation.
- **p-value ≥ 0.05:** The evidence is insufficient to reject the hypothesis that the two periods have the same mean YoY%.

The t-test does not tell you how large the difference is (that is the CAGR acceleration figure) — it tells you how confident you can be that a real difference exists.

---

## Project Structure

```
app.py                  # Streamlit app entry point
data/
    loader.py           # Zillow CSV download, parsing, YoY calculation
analysis/
    stats.py            # CAGR, t-test, drawdown, summary table
charts/
    plots.py            # Plotly chart builders
requirements.txt
.env.example
```
