"""Unit tests for src/analytics.py."""

import pandas as pd
import pytest

from src.analytics import (
    build_country_comparison_table,
    build_vaccination_correlation_table,
    compute_case_fatality_rate,
    compute_rolling_average,
)
from src.exceptions import CountryNotFoundError


def _make_countries_df():
    return pd.DataFrame(
        [
            {
                "country": "USA",
                "population": 330_000_000,
                "cases": 1000,
                "deaths": 20,
                "recovered": 950,
                "active": 30,
                "casesPerOneMillion": 3.0,
                "deathsPerOneMillion": 0.06,
            },
            {
                "country": "India",
                "population": 1_400_000_000,
                "cases": 500,
                "deaths": 5,
                "recovered": 480,
                "active": 15,
                "casesPerOneMillion": 0.36,
                "deathsPerOneMillion": 0.0036,
            },
        ]
    )


# ---------------------------------------------------------------------
# compute_rolling_average
# ---------------------------------------------------------------------


def test_compute_rolling_average_calculates_daily_new_from_cumulative():
    historical = pd.DataFrame(
        {
            "date": pd.to_datetime(["2026-01-01", "2026-01-02", "2026-01-03"]),
            "cases": [100, 150, 220],
            "deaths": [1, 2, 4],
        }
    )
    result = compute_rolling_average(historical, column="cases")

    # First day has no prior day to diff against -> filled with 0
    assert result.iloc[0]["daily_new"] == 0
    assert result.iloc[1]["daily_new"] == 50  # 150 - 100
    assert result.iloc[2]["daily_new"] == 70  # 220 - 150


def test_compute_rolling_average_clips_negative_diffs_to_zero():
    """A data correction (cumulative count going DOWN) must not produce
    a negative 'daily new cases' -- clipped to 0 instead.
    """
    historical = pd.DataFrame(
        {
            "date": pd.to_datetime(["2026-01-01", "2026-01-02"]),
            "cases": [100, 90],  # a downward correction
            "deaths": [1, 1],
        }
    )
    result = compute_rolling_average(historical, column="cases")
    assert result.iloc[1]["daily_new"] == 0


def test_compute_rolling_average_window_size():
    historical = pd.DataFrame(
        {
            "date": pd.date_range("2026-01-01", periods=10),
            "cases": list(range(100, 1100, 100)),
            "deaths": [0] * 10,
        }
    )
    result = compute_rolling_average(historical, column="cases", window_days=3)
    # After enough days, rolling_avg should equal a plain 3-day average
    # of the (constant, since cases grow linearly) daily_new column.
    assert result.iloc[-1]["rolling_avg"] == pytest.approx(100.0)


# ---------------------------------------------------------------------
# build_country_comparison_table
# ---------------------------------------------------------------------


def test_build_country_comparison_table_filters_and_sorts():
    countries = _make_countries_df()
    result = build_country_comparison_table(countries, ["USA", "India"])

    assert len(result) == 2
    assert result.iloc[0]["country"] == "USA"  # higher cases first


def test_build_country_comparison_table_missing_country_raises():
    countries = _make_countries_df()
    with pytest.raises(CountryNotFoundError):
        build_country_comparison_table(countries, ["USA", "Atlantis"])


# ---------------------------------------------------------------------
# compute_case_fatality_rate
# ---------------------------------------------------------------------


def test_compute_case_fatality_rate_calculates_correctly():
    countries = _make_countries_df()
    result = compute_case_fatality_rate(countries)

    usa_row = result[result["country"] == "USA"].iloc[0]
    assert usa_row["case_fatality_rate"] == 2.0  # 20/1000 * 100


def test_compute_case_fatality_rate_zero_cases_returns_zero():
    countries = pd.DataFrame([{"country": "Nowhere", "cases": 0, "deaths": 0}])
    result = compute_case_fatality_rate(countries)
    assert result.iloc[0]["case_fatality_rate"] == 0.0


# ---------------------------------------------------------------------
# build_vaccination_correlation_table
# ---------------------------------------------------------------------


def test_build_vaccination_correlation_table_calculates_per_hundred():
    countries = _make_countries_df()
    vaccination_totals = {"USA": 330_000_000}  # 100 doses per 100 people exactly

    result = build_vaccination_correlation_table(countries, vaccination_totals)

    assert len(result) == 1
    assert result.iloc[0]["vaccination_per_hundred"] == 100.0


def test_build_vaccination_correlation_table_excludes_missing_countries():
    countries = _make_countries_df()
    vaccination_totals = {"USA": 330_000_000}  # India has no vaccination data

    result = build_vaccination_correlation_table(countries, vaccination_totals)
    assert "India" not in result["country"].values