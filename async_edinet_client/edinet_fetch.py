from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
import enum
import logging
from types import MappingProxyType
from typing import Final

import httpx

from .dependencies import (
    BaseTranslator,
    get_translator,
)


logger = logging.getLogger(__name__)


class EdinetBaseAPIFetcher:

    URL_API: Final = "https://api.edinet-fsa.go.jp/api/v2/"
    URL_DOC_LIST: Final = URL_API + "documents.json"
    URL_DOC: Final = URL_API + "documents/"

    SUPPORTED_DOC_TYPES: Final = MappingProxyType(
        {
            "160": "Semi-Annual Report",
            "140": "Quarterly Report",
            "120": "Securities Report",
            "030": "Securities Registration Statement",
            "040": "Amendment of Securities Registration Statement",
            "170": "Amendment of semi-annual report",
            "150": "Amendment of quarterly report",
            "130": "Amendment of securities report",
            "180": "Extraordinary Report",
            # "350": "Large Holding Report",
            # "030": "Securities Registration Statement",
        }
    )
    # HTTP status codes that should trigger retries
    RETRY_STATUS_CODES: Final = {429, 500, 502, 503, 504}

    class ResponseStatus(enum.Enum):
        SUCCESS = 200
        BAD_REQUEST = 400
        AUTH_ERROR = 401
        NOT_FOUND = 404
        RATE_LIMIT_ERROR = 429
        SERVER_ERROR = 500

    def __init__(  # noqa: PLR0913
        self,
        *,
        subscription_key: str,
        fetch_interval: float = 1.0,
        retry_attempts: int = 3,
        retry_timeout: int = 45,
        request_timeout: int = 30,
        description_translation: bool = True,
    ) -> None:
        """
        Initialize the Edinet API Fetcher.

        Args:
            subscription_key: API subscription key
            fetch_interval: Delay between API requests in seconds
            retry_attempts: Number of retry attempts for failed requests
            retry_timeout: Total timeout for retry attempts in seconds
            request_timeout: Individual request timeout in seconds
            description_translation: Enable description translation

        Default supported codes - doc_type_code:
            "160": "Semi-Annual Report"
            "140": "Quarterly Report"
            "120": "Securities Report"
            "030": "Securities Registration Statement"
            "040": "Amendment of Securities Registration Statement"
            "170": "Amendment of semi-annual report"
            "150": "Amendment of quarterly report"
            "130": "Amendment of securities report"
        """
        self.subscription_key = subscription_key
        self.fetch_interval = fetch_interval
        self.retry_attempts = retry_attempts
        self.retry_timeout = retry_timeout
        self.request_timeout = request_timeout
        self.description_translation = description_translation
        self.translator: BaseTranslator = get_translator(description_translation)

    #########################
    #### Client Manager #####
    #########################

    @asynccontextmanager
    async def _get_client(
        self,
        client: httpx.AsyncClient | None = None,
    ) -> AsyncGenerator[httpx.AsyncClient, None]:
        """Context manager for HTTP client with proper configuration."""
        """
        If client is provided — reuse it (do not close).
        If not — create and close own.
        """
        if client is not None:
            yield client
            return

        timeout = httpx.Timeout(self.request_timeout)
        limits = httpx.Limits(max_connections=15, max_keepalive_connections=7)

        async with httpx.AsyncClient(timeout=timeout, limits=limits) as new_client:
            yield new_client
