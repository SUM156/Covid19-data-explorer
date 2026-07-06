"""
exceptions.py
=============
Custom exception hierarchy for the COVID data layer.
"""


class CovidDataError(Exception):
    """Base class for every error raised by this application."""


class ApiUnavailableError(CovidDataError):
    """Raised when the disease.sh API cannot be reached at all (network
    error, timeout, non-200 response) -- distinct from a successful
    response with unexpected/malformed content.
    """


class NoCachedDataError(CovidDataError):
    """Raised when the live API is unreachable AND no local cached
    snapshot exists to fall back to -- this means the app truly has
    no data source available.
    """


class CountryNotFoundError(CovidDataError):
    """Raised when a requested country has no data in the current dataset."""