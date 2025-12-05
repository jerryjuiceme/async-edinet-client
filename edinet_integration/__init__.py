__all__ = [
    "EdinetAPIFetcher",
    "EdinetDocAPIFetcher",
    "EdinetDoclistAPIFetcher",
    "configure_logging",
    "configure_logging_httpx",
    "get_fetcher",
]

from .edinet_fetch_doclist import EdinetDoclistAPIFetcher
from .edinet_fetch_document import EdinetDocAPIFetcher
from .utils import (
    configure_logging_httpx,
    configure_logging_temporary as configure_logging,
)


__version__ = "0.1.0"
__author__ = "jerryjuiceme"
__description__ = "Edinet API Fetcher for Python."


class EdinetAPIFetcher(EdinetDocAPIFetcher, EdinetDoclistAPIFetcher):
    pass


def get_fetcher(api_key: str) -> EdinetAPIFetcher:
    """Get the EdinetAPIFetcher instance."""
    return EdinetAPIFetcher(subscription_key=api_key)
