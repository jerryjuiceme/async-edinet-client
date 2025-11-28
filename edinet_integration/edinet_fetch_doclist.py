import asyncio
from datetime import date as date_type, datetime, timedelta
import logging
from typing import Any, Literal

import httpx
import stamina

from .dependencies import BaseTranslator
from .edinet_fetch import EdinetBaseAPIFetcher
from .exceptions import (
    EdinetAPIAuthError,
    EdinetAPIError,
    EdinetAPIRateLimitError,
    EdinetClientError,
    EdinetServerError,
)
from .schemas import (
    DocListMultiMessage,
    DoclistResult,
    DocListSingleMessage,
)


logger = logging.getLogger(__name__)


class EdinetDoclistAPIFetcher(EdinetBaseAPIFetcher):
    ########################################
    #### Get List of Publisehed Reports ####
    ########################################

    async def fetch_single_doc_list(
        self,
        date: str | date_type,
        translator: BaseTranslator | None = None,
        docs_list_type: Literal[1, 2] = 2,
    ) -> DocListSingleMessage:
        """
        Fetch document list for a single date.

        Args:
            date: Date in YYYY-MM-DD format
            translator: Translator controller
            docs_list_type: Document type code (1-5)

        :param translator:
            You can use GoogleTranslator or BypassTranslator
            to enable translation or disable for particular func run,
            even when the global translator is already configured.

        Returns:
            DocListSingleMessage
            Pydantic model with metadata and filtered document results
        """
        date_str = self._validate_date(date)
        logger.info("Fetching documents for date: %s", date_str)
        date_obj = datetime.strptime(date_str, "%Y-%m-%d")

        async with self._get_client() as client:
            try:
                raw_data, status = await self._fetch_list(
                    date_str, client, docs_list_type
                )
                logger.debug("Status: %s", status)

                if translator is None:
                    translator = self.translator
                docs: list[DoclistResult] = await self._filter_docs(
                    raw_data.get("results"),
                    translator,
                )
                docklist: DocListSingleMessage = DocListSingleMessage(
                    status_code=int(status),
                    fetch_status=raw_data["metadata"].get("status"),
                    message=raw_data["metadata"].get("message"),
                    request_type="daily",
                    date_from=date_obj,
                    date_to=date_obj,
                    count=len(docs),
                    results=docs,
                )
                logger.info("Fetched %s documents for date: %s", len(docs), date)
                return docklist
            except Exception as e:
                logger.exception(
                    "Failed to fetch or process document list for %s",
                    date,
                )
                return DocListSingleMessage(
                    status_code=500,
                    fetch_status=None,
                    message=str(e),
                    request_type="daily",
                    date_from=date_obj,
                    date_to=date_obj,
                    count=None,
                    results=[],
                )

    async def fetch_date_interval_doc_list(
        self,
        date_from: str,
        date_to: str,
        translator: BaseTranslator | None = None,
        docs_list_type: Literal[1, 2] = 2,
    ) -> DocListMultiMessage:
        """
        Fetch document list for a date interval.

        Args:
            date_from: Start date in YYYY-MM-DD format
            date_to: End date in YYYY-MM-DD format
            translator: Translator controller

        :param translator:
            You can use GoogleTranslator or BypassTranslator
            to enable translation or disable for particular func run,
            even when the global translator is already configured.
        Returns:
            DocListMultiMessage
            Pydantic model with metadata and filtered document results


        """
        logger.info("Fetching document lists from %s to %s" % (date_from, date_to))
        date_cursor = datetime.strptime(self._validate_date(date_from), "%Y-%m-%d")
        date_end = datetime.strptime(self._validate_date(date_to), "%Y-%m-%d")
        res = dict(status_code=[], fetch_status=[], message=[], results=[])

        async with self._get_client() as client:
            while date_cursor <= date_end:
                date_str = date_cursor.strftime("%Y-%m-%d")
                try:
                    raw_data, status = await self._fetch_list(
                        date_str, client, docs_list_type
                    )
                    res["status_code"].append({date_str: int(status)})
                    res["fetch_status"].append(
                        {date_str: int(raw_data["metadata"].get("status"))}
                    )
                    res["message"].append(
                        {date_str: raw_data["metadata"].get("message")}
                    )
                    if translator is None:
                        translator = self.translator

                    docs = await self._filter_docs(raw_data.get("results"), translator)
                    if docs:
                        [res["results"].append(doc) for doc in docs]
                except Exception as e:
                    logger.warning("Skipping %s due to error: %s" % (date_str, e))
                    res["status_code"].append(
                        {date_str: getattr(e, "status_code", 500)}
                    )
                    res["message"].append({date_str: str(e)})
                await asyncio.sleep(self.fetch_interval)
                date_cursor += timedelta(days=1)

        results = DocListMultiMessage(
            request_type="interval",
            date_from=datetime.strptime(date_from, "%Y-%m-%d"),
            date_to=datetime.strptime(date_to, "%Y-%m-%d"),
            status_code=res["status_code"],
            fetch_status=res["fetch_status"],
            message=res["message"],
            count=len(res["results"]),
            results=res["results"],
        )
        logger.info(
            "Fetched %s documents from %s to %s",
            len(res["results"]),
            date_from,
            date_to,
        )
        return results

    ###########################
    #### PRIVATE METHODS  #####
    ###########################
    async def _fetch_list(
        self,
        date: str,
        client: httpx.AsyncClient,
        docs_list_type: int,
    ) -> tuple[dict[str, Any], int]:
        """
        Internal method to fetch document list with retry logic.

        Args:
            date: Date in YYYY-MM-DD format
            client: HTTP client instance
            docs_list_type: Document type code

        Returns:
            HTTP response object

        Raises:
            EdinetAPIError: When all retry attempts fail
        """
        params = {
            "date": date,
            "type": docs_list_type,
            "Subscription-Key": self.subscription_key,
        }
        # headers = {"Ocp-Apim-Subscription-Key": self.subscription_key}

        async for attempt in stamina.retry_context(
            on=(
                httpx.NetworkError,
                httpx.TimeoutException,
                EdinetServerError,
                EdinetAPIRateLimitError,
            ),
            attempts=self.retry_attempts,
            timeout=self.retry_timeout,
        ):
            with attempt:
                try:
                    response = await client.get(
                        self.URL_DOC_LIST,
                        params=params,
                    )
                    st_code: int = response.status_code
                    if st_code == self.ResponseStatus.SUCCESS.value:
                        return response.json(), st_code
                    elif st_code == self.ResponseStatus.AUTH_ERROR.value:
                        raise EdinetAPIAuthError(
                            "Authentication failed - check subscription key"
                        )
                    elif st_code == self.ResponseStatus.RATE_LIMIT_ERROR.value:
                        logger.warning("Rate limit exceeded, retrying...")
                        raise EdinetAPIRateLimitError("API rate limit exceeded")
                    elif st_code in self.RETRY_STATUS_CODES:
                        logger.warning("Server error %s, retry...", st_code)
                        raise EdinetAPIError("Server error: %d", st_code)
                    else:
                        # 400, 404 and other
                        raise EdinetClientError(f"Client error: {st_code}", st_code)

                except httpx.HTTPError as e:
                    logger.error("HTTP error on attempt for %s: %s" % (date, e))
                    raise EdinetAPIError(
                        f"Connection error: {e}",
                    )
                except Exception:
                    logger.exception("Unexpected error fetching doc list for %s", date)
                    raise EdinetAPIError("Unknown error after retries")
        raise EdinetAPIError("Unknown error after retries")

    async def _filter_docs(
        self,
        docs: list[dict] | None,
        translator: BaseTranslator,
    ) -> list[DoclistResult]:
        """
        Internal method to fetch document list with retry logic.

        Args:
            date: Date in YYYY-MM-DD format
            client: HTTP client instance
            docs_list_type: Document type code

        Returns:
            HTTP response object

        Raises:
            EdinetAPIError: When all retry attempts fail
        """
        filtered: list = []
        if docs is None:
            logger.info("No docs to filter")
            return filtered
        for doc in docs:
            if self._is_valid(doc):
                try:
                    doc["filerName"] = doc["filerName"].encode().decode("utf-8")
                    new_doc: DoclistResult = DoclistResult(**doc)
                    filtered.append(new_doc)
                except (AttributeError, UnicodeDecodeError) as e:
                    logger.debug("Skipping doc with invalid filerName: %s", e)
                await asyncio.sleep(0)  # Yield control

        # asynchronously translate filer names
        tasks = [self._translate(doc, translator) for doc in filtered]
        await asyncio.gather(*tasks)

        return filtered

    async def _translate(self, doc: DoclistResult, translator: BaseTranslator) -> None:
        """
        Internal method to translate document list asynchronously.
        """
        doc.filer_name_eng = await translator.translate(doc.filer_name)

    def _is_valid(self, doc: dict[str, Any]) -> bool:
        return (
            doc.get("filerName") is not None
            and doc.get("docTypeCode") in self.SUPPORTED_DOC_TYPES
        )

    def _validate_date(self, date: str | date_type) -> str:
        """Validate date format (YYYY-MM-DD)."""
        if isinstance(date, date_type):
            return date.strftime("%Y-%m-%d")

        try:
            datetime.strptime(date, "%Y-%m-%d")

        except ValueError:
            raise ValueError(
                "Invalid date format: %s. Expected YYYY-MM-DD",
                date,
            )
        else:
            return date
