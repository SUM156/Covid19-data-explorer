"""Unit tests for src/data_loader.py -- live API + cache fallback
orchestration, and the raw-shape-to-DataFrame conversion logic.
"""

import json

import pandas as pd
import pytest

from src.data_loader import load_covid_dataset, _countries_list_to_dataframe, _historical_dict_to_dataframe
from src.exceptions import ApiUnavailableError, NoCachedDataError

SAMPLE_COUNTRIES_LIVE_SHAPE = [
    {
        "country": "USA",
        "countryInfo": {"iso3": "USA"},
        "continent": "North America",
        "population": 330000000,
        "cases": 1000,
        "todayCases": 10,
        "deaths": 20,
        "todayDeaths": 1,
        "recovered": 950,
        "active": 30,
        "casesPerOneMillion": 3.0,
        "deathsPerOneMillion": 0.06,
        "tests": 5000,
        "testsPerOneMillion": 15.0,
    }
]

SAMPLE_COUNTRIES_CACHED_SHAPE = [
    {
        "country": "USA",
        "iso3": "USA",
        "continent": "North America",
        "population": 330000000,
        "cases": 1000,
        "todayCases": 10,
        "deaths": 20,
        "todayDeaths": 1,
        "recovered": 950,
        "active": 30,
        "casesPerOneMillion": 3.0,
        "deathsPerOneMillion": 0.06,
        "tests": 5000,
        "testsPerOneMillion": 15.0,
    }
]


def test_countries_list_to_dataframe_extracts_iso3_from_nested_shape():
    """Live API nests iso3 under countryInfo -- must still end up as a
    flat 'iso3' column.
    """
    df = _countries_list_to_dataframe(SAMPLE_COUNTRIES_LIVE_SHAPE)
    assert df.iloc[0]["iso3"] == "USA"


def test_countries_list_to_dataframe_extracts_iso3_from_flat_shape():
    """Cached snapshot stores iso3 as a flat key -- must also work."""
    df = _countries_list_to_dataframe(SAMPLE_COUNTRIES_CACHED_SHAPE)
    assert df.iloc[0]["iso3"] == "USA"


def test_historical_dict_to_dataframe_parses_dates_and_sorts():
    timeline = {
        "cases": {"1/2/26": 200, "1/1/26": 100},
        "deaths": {"1/2/26": 5, "1/1/26": 3},
    }
    df = _historical_dict_to_dataframe(timeline)

    assert list(df.columns) == ["date", "cases", "deaths"]
    assert df.iloc[0]["cases"] == 100  # earlier date first after sort
    assert df.iloc[1]["cases"] == 200
    assert pd.api.types.is_datetime64_any_dtype(df["date"])


def test_load_covid_dataset_uses_live_api_when_available(monkeypatch):
    monkeypatch.setattr(
        "src.data_loader.fetch_countries_data", lambda: SAMPLE_COUNTRIES_LIVE_SHAPE
    )
    monkeypatch.setattr(
        "src.data_loader.fetch_historical_data",
        lambda country, last_days=180: {"timeline": {"cases": {"1/1/26": 100}, "deaths": {"1/1/26": 1}}},
    )
    monkeypatch.setattr(
        "src.data_loader.fetch_vaccination_coverage",
        lambda country: {"timeline": {"1/1/26": 500000}},
    )

    dataset = load_covid_dataset(historical_countries=["USA"])

    assert dataset.source == "live"
    assert len(dataset.countries) == 1
    assert "USA" in dataset.historical
    assert dataset.vaccination_totals["USA"] == 500000


def test_load_covid_dataset_falls_back_to_cache_when_api_unavailable(monkeypatch, tmp_path):
    def _raise(*args, **kwargs):
        raise ApiUnavailableError("simulated outage")

    monkeypatch.setattr("src.data_loader.fetch_countries_data", _raise)

    cache_file = tmp_path / "cache.json"
    cache_file.write_text(
        json.dumps(
            {
                "countries": SAMPLE_COUNTRIES_CACHED_SHAPE,
                "historical": {"USA": {"cases": {"1/1/26": 100}, "deaths": {"1/1/26": 1}}},
                "vaccination_totals": {"USA": 400000},
            }
        )
    )

    dataset = load_covid_dataset(cache_path=str(cache_file))

    assert dataset.source == "cached"
    assert len(dataset.countries) == 1
    assert dataset.vaccination_totals["USA"] == 400000


def test_load_covid_dataset_raises_when_api_down_and_no_cache(monkeypatch, tmp_path):
    def _raise(*args, **kwargs):
        raise ApiUnavailableError("simulated outage")

    monkeypatch.setattr("src.data_loader.fetch_countries_data", _raise)

    with pytest.raises(NoCachedDataError):
        load_covid_dataset(cache_path=str(tmp_path / "does_not_exist.json"))


def test_load_covid_dataset_raises_on_corrupted_cache(monkeypatch, tmp_path):
    def _raise(*args, **kwargs):
        raise ApiUnavailableError("simulated outage")

    monkeypatch.setattr("src.data_loader.fetch_countries_data", _raise)

    cache_file = tmp_path / "corrupted.json"
    cache_file.write_text("{not valid json")

    with pytest.raises(NoCachedDataError):
        load_covid_dataset(cache_path=str(cache_file))