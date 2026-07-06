"""
data_loader.py
===============
Orchestrates data loading: tries the live disease.sh API first, and
transparently falls back to a bundled local JSON snapshot if the API
is unreachable (no internet, API downtime, or a sandboxed environment
with restricted network egress). This mirrors the same graceful-
degradation pattern used in the Day 18 SmartNotes AI provider --
external dependencies should never make an entire app unusable.

Every function here returns plain pandas DataFrames / dicts, never
raw API response shapes -- `analytics.py` and `visualizer.py` never
need to know whether the data came from a live HTTP call or a cached
file.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List

import pandas as pd

from src.api_client import fetch_countries_data, fetch_historical_data, fetch_vaccination_coverage
from src.exceptions import ApiUnavailableError, NoCachedDataError

logger = logging.getLogger(__name__)

DEFAULT_CACHE_PATH = "data/cached_covid_data.json"
DEFAULT_HISTORICAL_COUNTRIES = ["USA", "India", "Brazil", "Germany", "UK"]


@dataclass(frozen=True)
class CovidDataset:
    """A fully-loaded COVID dataset, regardless of where it came from.

    Attributes:
        countries: One row per country -- cases, deaths, population, etc.
        historical: Country name -> DataFrame with columns [date, cases,
            deaths], daily cumulative counts.
        vaccination_totals: Country name -> total cumulative doses
            administered (a single current snapshot number, not a
            timeline -- sufficient for a cases-vs-vaccination
            correlation scatter plot).
        source: 'live' if fetched from disease.sh just now, 'cached'
            if loaded from the local JSON snapshot. Shown in the UI so
            a user always knows how fresh the data is.
    """

    countries: pd.DataFrame
    historical: Dict[str, pd.DataFrame]
    vaccination_totals: Dict[str, int]
    source: str


def _countries_list_to_dataframe(countries_raw: List[dict]) -> pd.DataFrame:
    """Convert disease.sh's per-country dict list into a flat DataFrame.

    Normalizes the ISO3 country code from either shape it can arrive
    in: the LIVE API nests it under `countryInfo.iso3`, while the
    bundled cached snapshot stores it as a flat `iso3` key. Every
    downstream consumer (e.g. the choropleth map) just wants a flat
    `iso3` column and shouldn't need to know which source it came from.
    """
    normalized_rows = []
    for row in countries_raw:
        iso3 = row.get("iso3")
        if iso3 is None and isinstance(row.get("countryInfo"), dict):
            iso3 = row["countryInfo"].get("iso3")
        normalized_rows.append({**row, "iso3": iso3})

    dataframe = pd.DataFrame(normalized_rows)
    return dataframe[
        [
            "country",
            "iso3",
            "continent",
            "population",
            "cases",
            "todayCases",
            "deaths",
            "todayDeaths",
            "recovered",
            "active",
            "casesPerOneMillion",
            "deathsPerOneMillion",
            "tests",
            "testsPerOneMillion",
        ]
    ]


def _historical_dict_to_dataframe(timeline: dict) -> pd.DataFrame:
    """Convert disease.sh's {'cases': {date: n}, 'deaths': {date: n}}
    shape into a tidy DataFrame with columns [date, cases, deaths].
    """
    cases_series = pd.Series(timeline.get("cases", {}), name="cases")
    deaths_series = pd.Series(timeline.get("deaths", {}), name="deaths")

    combined = pd.concat([cases_series, deaths_series], axis=1).reset_index()
    combined.columns = ["date", "cases", "deaths"]
    combined["date"] = pd.to_datetime(combined["date"], format="%m/%d/%y")
    return combined.sort_values("date").reset_index(drop=True)


def _load_from_live_api(historical_countries: List[str]) -> CovidDataset:
    """Attempt to build a full dataset from the live disease.sh API.

    Raises:
        ApiUnavailableError: If any required API call fails.
    """
    countries_raw = fetch_countries_data()
    countries_df = _countries_list_to_dataframe(countries_raw)

    historical = {}
    for country in historical_countries:
        raw = fetch_historical_data(country)
        historical[country] = _historical_dict_to_dataframe(raw.get("timeline", {}))

    vaccination_totals = {}
    for row in countries_raw:
        country_name = row["country"]
        try:
            vax_raw = fetch_vaccination_coverage(country_name)
            timeline = vax_raw.get("timeline", {})
            latest_total = list(timeline.values())[-1] if timeline else 0
            vaccination_totals[country_name] = latest_total
        except ApiUnavailableError:
            # A single country's vaccine data being unavailable
            # shouldn't sink the whole dataset -- just skip it and
            # keep going with everyone else.
            logger.warning("Skipping vaccination data for %s (unavailable)", country_name)

    return CovidDataset(
        countries=countries_df,
        historical=historical,
        vaccination_totals=vaccination_totals,
        source="live",
    )


def _load_from_cache(cache_path: str) -> CovidDataset:
    """Load a dataset from the local bundled JSON snapshot.

    Raises:
        NoCachedDataError: If the cache file doesn't exist or can't be parsed.
    """
    path = Path(cache_path)
    if not path.exists():
        raise NoCachedDataError(
            f"No cached data found at '{cache_path}' and the live API is unreachable."
        )

    try:
        with path.open("r", encoding="utf-8") as cache_file:
            raw = json.load(cache_file)
    except (json.JSONDecodeError, OSError) as exc:
        raise NoCachedDataError(f"Cached data file at '{cache_path}' is corrupted: {exc}") from exc

    countries_df = _countries_list_to_dataframe(raw["countries"])
    historical = {
        country: _historical_dict_to_dataframe(timeline)
        for country, timeline in raw["historical"].items()
    }

    return CovidDataset(
        countries=countries_df,
        historical=historical,
        vaccination_totals=raw["vaccination_totals"],
        source="cached",
    )


def load_covid_dataset(
    historical_countries: List[str] | None = None,
    cache_path: str = DEFAULT_CACHE_PATH,
) -> CovidDataset:
    """Load a full COVID dataset, preferring live data but falling back
    to a local cache if the API is unreachable.

    Args:
        historical_countries: Which countries to fetch historical
            timelines for (fetching for ALL ~200 countries on every
            load would be slow and unnecessary for a dashboard that
            only shows a handful at a time).
        cache_path: Path to the local JSON snapshot to fall back to.

    Returns:
        A `CovidDataset` with `source` set to 'live' or 'cached' so
        the caller can be transparent with the end user about data
        freshness.

    Raises:
        NoCachedDataError: If the live API is unreachable AND no
            cached snapshot is available either.
    """
    countries = historical_countries or DEFAULT_HISTORICAL_COUNTRIES

    try:
        dataset = _load_from_live_api(countries)
        logger.info("Loaded live COVID data from disease.sh")
        return dataset
    except ApiUnavailableError as exc:
        logger.warning("Live API unavailable (%s), falling back to cached snapshot", exc)
        return _load_from_cache(cache_path)