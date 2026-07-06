"""
visualizer.py
=============
Builds Plotly figures for the COVID dashboard, themed around a
consistent Navy Blue brand palette (matching the portfolio-wide brand
color) while using chart TYPES distinct from the other dashboards in
this portfolio -- an animated time-series, a choropleth world map, and
a correlation scatter plot, none of which appear in Day 21 or Day 22.
"""

from __future__ import annotations

import plotly.express as px
import plotly.graph_objects as go
import pandas as pd

# ---------------------------------------------------------------------
# Navy Blue brand palette -- the consistent color identity across every
# dashboard project in this portfolio. Individual projects vary their
# LAYOUT and CHART TYPES, but this palette stays the same everywhere,
# the way a real company's dashboards all share one brand color.
# ---------------------------------------------------------------------
NAVY_DARKEST = "#0A2647"
NAVY_DARK = "#144272"
NAVY_MEDIUM = "#205295"
NAVY_LIGHT = "#2C74B3"
NAVY_ACCENT = "#5FA8D3"
NAVY_SEQUENTIAL_SCALE = ["#0A2647", "#144272", "#205295", "#2C74B3", "#5FA8D3", "#A9D6E5"]


def build_rolling_average_chart(rolling_data: pd.DataFrame, label: str = "Cases") -> go.Figure:
    """Build a chart showing daily new counts (bars) with a 7-day
    rolling average overlaid (line) -- the standard epidemiological
    visualization for smoothing out weekday/weekend reporting noise.

    Args:
        rolling_data: Output of `analytics.compute_rolling_average`.
        label: What the counts represent (e.g. "Cases", "Deaths") --
            used in the chart title and legend.

    Returns:
        A Plotly `Figure` with bars + an overlaid rolling-average line.
    """
    figure = go.Figure()
    figure.add_trace(
        go.Bar(
            x=rolling_data["date"],
            y=rolling_data["daily_new"],
            name=f"Daily New {label}",
            marker_color=NAVY_ACCENT,
            opacity=0.5,
        )
    )
    figure.add_trace(
        go.Scatter(
            x=rolling_data["date"],
            y=rolling_data["rolling_avg"],
            name="7-Day Rolling Average",
            mode="lines",
            line=dict(color=NAVY_DARKEST, width=3),
        )
    )
    figure.update_layout(
        title=f"Daily New {label} (7-Day Rolling Average)",
        xaxis_title="Date",
        yaxis_title=f"New {label}",
        template="plotly_white",
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    return figure


def build_country_comparison_chart(comparison_data: pd.DataFrame) -> go.Figure:
    """Build a grouped bar chart comparing cases/deaths across countries.

    Args:
        comparison_data: Output of `analytics.build_country_comparison_table`.

    Returns:
        A Plotly `Figure` with grouped bars per country.
    """
    figure = go.Figure()
    figure.add_trace(
        go.Bar(
            x=comparison_data["country"],
            y=comparison_data["cases"],
            name="Total Cases",
            marker_color=NAVY_MEDIUM,
        )
    )
    figure.add_trace(
        go.Bar(
            x=comparison_data["country"],
            y=comparison_data["active"],
            name="Active Cases",
            marker_color=NAVY_ACCENT,
        )
    )
    figure.update_layout(
        title="Country Comparison — Total vs. Active Cases",
        barmode="group",
        template="plotly_white",
        xaxis_title="",
        yaxis_title="Cases",
    )
    return figure


def build_world_choropleth_map(countries: pd.DataFrame, metric: str = "casesPerOneMillion") -> go.Figure:
    """Build a world choropleth map colored by a per-country metric.

    Args:
        countries: The full countries DataFrame (must include 'iso3').
        metric: Which column to color the map by (e.g.
            'casesPerOneMillion', 'deathsPerOneMillion').

    Returns:
        A Plotly `Figure` choropleth map.
    """
    metric_labels = {
        "casesPerOneMillion": "Cases per Million",
        "deathsPerOneMillion": "Deaths per Million",
        "testsPerOneMillion": "Tests per Million",
    }
    label = metric_labels.get(metric, metric)

    figure = px.choropleth(
        countries,
        locations="iso3",
        color=metric,
        hover_name="country",
        color_continuous_scale=NAVY_SEQUENTIAL_SCALE,
        title=f"Global {label}",
    )
    figure.update_layout(
        template="plotly_white",
        geo=dict(showframe=False, showcoastlines=True, projection_type="natural earth"),
        coloraxis_colorbar=dict(title=label),
    )
    return figure


def build_vaccination_correlation_chart(correlation_data: pd.DataFrame) -> go.Figure:
    """Build a scatter plot of vaccination coverage vs. case rate, to
    visually explore whether higher vaccination associates with lower
    cases-per-million.

    Args:
        correlation_data: Output of
            `analytics.build_vaccination_correlation_table`.

    Returns:
        A Plotly `Figure` scatter plot with a trendline.
    """
    figure = px.scatter(
        correlation_data,
        x="vaccination_per_hundred",
        y="casesPerOneMillion",
        hover_name="country",
        trendline="ols",
        color_discrete_sequence=[NAVY_DARK],
        title="Vaccination Coverage vs. Cases per Million",
    )
    figure.update_traces(marker=dict(size=11, color=NAVY_MEDIUM, line=dict(width=1, color=NAVY_DARKEST)))
    figure.update_layout(
        template="plotly_white",
        xaxis_title="Vaccine Doses per 100 People",
        yaxis_title="Cases per Million",
    )
    return figure