"""
analytics.py
============
Pure aggregation and statistical functions over COVID data. Nothing
here imports Streamlit, Plotly, or the API client -- every function
takes a plain DataFrame/dict and returns a DataFrame or number,
matching the same pure-analytics pattern used in every dashboard
project in this portfolio (Day 21, Day 22).
"""

from __future__ import annotations

import pandas as pd

from src.exceptions import CountryNotFoundError


def compute_rolling_average(
    historical: pd.DataFrame, column: str = "cases", window_days: int = 7
) -> pd.DataFrame:
    """Compute a rolling average of new daily cases/deaths from a
    cumulative timeline.

    Args:
        historical: A DataFrame with columns [date, cases, deaths]
            holding CUMULATIVE counts (as disease.sh reports them).
        column: Which cumulative column to convert to a daily rolling
            average ('cases' or 'deaths').
        window_days: Rolling window size in days (default: 7, the
            standard epidemiological smoothing window that removes
            weekday/weekend reporting artifacts).

    Returns:
        A DataFrame with columns [date, daily_new, rolling_avg].
    """
    working = historical[["date", column]].copy()
    # disease.sh reports CUMULATIVE totals -- the day-over-day diff is
    # what actually represents "new cases today", which is what a
    # rolling average should smooth, not the ever-increasing cumulative
    # total itself.
    working["daily_new"] = working[column].diff().clip(lower=0).fillna(0)
    working["rolling_avg"] = working["daily_new"].rolling(window=window_days, min_periods=1).mean()
    return working[["date", "daily_new", "rolling_avg"]]


def build_country_comparison_table(countries: pd.DataFrame, selected: list[str]) -> pd.DataFrame:
    """Build a side-by-side comparison table for a set of countries.

    Args:
        countries: The full countries DataFrame.
        selected: Which country names to include.

    Returns:
        A DataFrame filtered to `selected`, with columns most relevant
        for comparison, sorted by total cases descending.

    Raises:
        CountryNotFoundError: If any name in `selected` isn't present
            in the dataset.
    """
    available = set(countries["country"])
    missing = [name for name in selected if name not in available]
    if missing:
        raise CountryNotFoundError(f"No data for country/countries: {missing}")

    filtered = countries[countries["country"].isin(selected)]
    columns = [
        "country",
        "cases",
        "deaths",
        "recovered",
        "active",
        "casesPerOneMillion",
        "deathsPerOneMillion",
    ]
    return filtered[columns].sort_values("cases", ascending=False).reset_index(drop=True)


def compute_case_fatality_rate(countries: pd.DataFrame) -> pd.DataFrame:
    """Compute case fatality rate (deaths / cases * 100) per country.

    Returns:
        The input DataFrame with an added 'case_fatality_rate' column
        (percent, rounded to 2 decimals). Countries with zero cases
        get a rate of 0.0 rather than a division-by-zero error.
    """
    result = countries.copy()
    result["case_fatality_rate"] = result.apply(
        lambda row: round(100 * row["deaths"] / row["cases"], 2) if row["cases"] > 0 else 0.0,
        axis=1,
    )
    return result


def build_vaccination_correlation_table(
    countries: pd.DataFrame, vaccination_totals: dict[str, int]
) -> pd.DataFrame:
    """Build a table pairing vaccination coverage with case rates, for
    correlation analysis (does higher vaccination coverage associate
    with lower cases-per-million?).

    Args:
        countries: The full countries DataFrame.
        vaccination_totals: Country name -> total cumulative doses.

    Returns:
        A DataFrame with columns [country, vaccination_per_hundred,
        casesPerOneMillion, deathsPerOneMillion]. Countries with no
        vaccination data available are excluded (there's nothing to
        correlate for them).
    """
    rows = []
    for _, row in countries.iterrows():
        country = row["country"]
        if country not in vaccination_totals or row["population"] <= 0:
            continue
        doses = vaccination_totals[country]
        vaccination_per_hundred = round(100 * doses / row["population"], 1)
        rows.append(
            {
                "country": country,
                "vaccination_per_hundred": vaccination_per_hundred,
                "casesPerOneMillion": row["casesPerOneMillion"],
                "deathsPerOneMillion": row["deathsPerOneMillion"],
            }
        )
    return pd.DataFrame(rows)