"""Unit tests for src/api_client.py -- HTTP layer, fully mocked (no
real network calls, per project sandbox network policy).
"""

import requests

import pytest

from src.api_client import fetch_countries_data, fetch_historical_data, fetch_vaccination_coverage
from src.exceptions import ApiUnavailableError


class _FakeResponse:
    """A minimal stand-in for `requests.Response` used across these tests."""

    def __init__(self, json_data, status_code=200):
        self._json_data = json_data
        self.status_code = status_code

    def json(self):
        return self._json_data

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"HTTP {self.status_code}")


def test_fetch_countries_data_returns_parsed_json(monkeypatch):
    fake_data = [{"country": "USA", "cases": 100}]
    monkeypatch.setattr(
        "src.api_client.requests.get", lambda *a, **k: _FakeResponse(fake_data)
    )

    result = fetch_countries_data()
    assert result == fake_data


def test_fetch_countries_data_raises_on_connection_error(monkeypatch):
    def _raise_connection_error(*args, **kwargs):
        raise requests.ConnectionError("no network")

    monkeypatch.setattr("src.api_client.requests.get", _raise_connection_error)

    with pytest.raises(ApiUnavailableError):
        fetch_countries_data()


def test_fetch_countries_data_raises_on_http_error(monkeypatch):
    monkeypatch.setattr(
        "src.api_client.requests.get", lambda *a, **k: _FakeResponse({}, status_code=500)
    )

    with pytest.raises(ApiUnavailableError):
        fetch_countries_data()


def test_fetch_historical_data_returns_parsed_json(monkeypatch):
    fake_data = {"country": "USA", "timeline": {"cases": {"1/1/26": 100}}}
    monkeypatch.setattr(
        "src.api_client.requests.get", lambda *a, **k: _FakeResponse(fake_data)
    )

    result = fetch_historical_data("USA", last_days=30)
    assert result == fake_data


def test_fetch_historical_data_raises_on_timeout(monkeypatch):
    def _raise_timeout(*args, **kwargs):
        raise requests.Timeout("timed out")

    monkeypatch.setattr("src.api_client.requests.get", _raise_timeout)

    with pytest.raises(ApiUnavailableError):
        fetch_historical_data("USA")


def test_fetch_vaccination_coverage_returns_parsed_json(monkeypatch):
    fake_data = {"country": "USA", "timeline": {"1/1/26": 500000}}
    monkeypatch.setattr(
        "src.api_client.requests.get", lambda *a, **k: _FakeResponse(fake_data)
    )

    result = fetch_vaccination_coverage("USA")
    assert result == fake_data


def test_fetch_vaccination_coverage_raises_on_error(monkeypatch):
    monkeypatch.setattr(
        "src.api_client.requests.get", lambda *a, **k: _FakeResponse({}, status_code=404)
    )

    with pytest.raises(ApiUnavailableError):
        fetch_vaccination_coverage("Nonexistent")