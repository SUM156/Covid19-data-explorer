"""Unit tests for src/visualizer.py -- chart construction contracts."""

import pandas as pd
import plotly.graph_objects as go

from src.visualizer import (
    build_country_comparison_chart,
    build_rolling_average_chart,
    build_vaccination_correlation_chart,
    build_world_choropleth_map,
)


def test_rolling_average_chart_returns_figure():
    rolling_data = pd.DataFrame(
        {
            "date": pd.date_range("2026-01-01", periods=5),
            "daily_new": [10, 20, 15, 25, 30],
            "rolling_avg": [10, 15, 15, 17.5, 20],
        }
    )
    figure = build_rolling_average_chart(rolling_data)
    assert isinstance(figure, go.Figure)
    assert len(figure.data) == 2  # bar + line


def test_country_comparison_chart_returns_figure():
    comparison_data = pd.DataFrame(
        {
            "country": ["USA", "India"],
            "cases": [1000, 500],
            "active": [30, 15],
        }
    )
    figure = build_country_comparison_chart(comparison_data)
    assert isinstance(figure, go.Figure)
    assert len(figure.data) == 2  # total cases bar + active cases bar


def test_world_choropleth_map_returns_figure():
    countries = pd.DataFrame(
        {
            "country": ["USA", "India"],
            "iso3": ["USA", "IND"],
            "casesPerOneMillion": [3.0, 0.36],
        }
    )
    figure = build_world_choropleth_map(countries, metric="casesPerOneMillion")
    assert isinstance(figure, go.Figure)


def test_vaccination_correlation_chart_returns_figure():
    correlation_data = pd.DataFrame(
        {
            "country": ["USA", "India", "Brazil"],
            "vaccination_per_hundred": [180.0, 65.0, 140.0],
            "casesPerOneMillion": [3.0, 0.36, 5.0],
        }
    )
    figure = build_vaccination_correlation_chart(correlation_data)
    assert isinstance(figure, go.Figure)