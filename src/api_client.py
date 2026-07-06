"""
api_client.py
=============
Thin HTTP client for the disease.sh public COVID-19 API
(https://disease.sh). This module ONLY knows how to make HTTP
requests and parse JSON responses into plain Python dicts/lists -- it
has no fallback logic, no caching, and no opinion about what happens
if the API is unreachable. That decision-making lives in
`data_loader.py`, which is what keeps this module simple enough to
mock in tests with a single `requests.get` patch.
"""

from __future__ import annotations

from typing import Any, Dict, List

import requests

from src.exceptions import ApiUnavailableError

BASE_URL = "https://disease.sh/v3/covid-19"
REQUEST_TIMEOUT_SECONDS = 10


def fetch_countries_data() -> List[Dict[str, Any]]:
    """Fetch current-snapshot COVID data for every country.

    Returns:
        A list of per-country dicts (cases, deaths, recovered, active,
        population, continent, etc.) as returned by disease.sh.

    Raises:
        ApiUnavailableError: If the request fails (network error,
            timeout, or non-200 response).
    """
    url = f"{BASE_URL}/countries"
    try:
        response = requests.get(url, timeout=REQUEST_TIMEOUT_SECONDS)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as exc:
        raise ApiUnavailableError(f"Could not fetch country data from disease.sh: {exc}") from exc


def fetch_historical_data(country: str, last_days: int = 180) -> Dict[str, Any]:
    """Fetch a country's historical daily cases/deaths timeline.

    Args:
        country: Country name as recognized by disease.sh (e.g. "USA").
        last_days: How many most-recent days of history to fetch.

    Returns:
        A dict with a 'timeline' key containing 'cases' and 'deaths'
        sub-dicts mapping date strings to cumulative counts.

    Raises:
        ApiUnavailableError: If the request fails.
    """
    url = f"{BASE_URL}/historical/{country}"
    try:
        response = requests.get(
            url, params={"lastdays": last_days}, timeout=REQUEST_TIMEOUT_SECONDS
        )
        response.raise_for_status()
        return response.json()
    except requests.RequestException as exc:
        raise ApiUnavailableError(
            f"Could not fetch historical data for '{country}' from disease.sh: {exc}"
        ) from exc


def fetch_vaccination_coverage(country: str) -> Dict[str, Any]:
    """Fetch a country's cumulative vaccine doses administered timeline.

    Args:
        country: Country name as recognized by disease.sh.

    Returns:
        A dict with a 'timeline' key mapping date strings to
        cumulative total doses administered.

    Raises:
        ApiUnavailableError: If the request fails.
    """
    url = f"{BASE_URL}/vaccine/coverage/countries/{country}"
    try:
        response = requests.get(
            url, params={"lastdays": 1}, timeout=REQUEST_TIMEOUT_SECONDS
        )
        response.raise_for_status()
        return response.json()
    except requests.RequestException as exc:
        raise ApiUnavailableError(
            f"Could not fetch vaccination data for '{country}' from disease.sh: {exc}"
        ) from exc