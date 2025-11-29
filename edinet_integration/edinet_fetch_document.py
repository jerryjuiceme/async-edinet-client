import logging
from pathlib import Path
import tempfile
from typing import Literal

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
from .schemas import ExtractDocMessage
from .utils import process_zip_file


logger = logging.getLogger(__name__)


class EdinetDocAPIFetcher(EdinetBaseAPIFetcher):
    async def get_document(
        self,
        doc_id: str,
        doc_type_code: Literal["160", "140", "120", "undefined"] = "undefined",
        translator: BaseTranslator | None = None,
        custom_fields: list[str] | None = None,
    ) -> ExtractDocMessage:
        """Fetches and processes a document from the EDINET API.

        Args:
            doc_id: Document ID
            doc_type_code: Document type code
            translator: Translator to use for description translation
            custom_fields: List of custom fields to extract

        Supported doc_type_code:
            "160": "Semi-Annual Report",
            "140": "Quarterly Report",
            "120": "Securities Report",
            "030": "Securities Registration Statement",
            "040": "Amendment of Securities Registration Statement",
            "170": "Amendment of semi-annual report",
            "150": "Amendment of quarterly report",
            "130": "Amendment of securities report",
        Example:
            doc = await fetcher.get_document("S100TM9A", "140")
        Returns:
            ExtractDocMessages
        """
        doc_type = "5"
        message = ExtractDocMessage(
            doc_id=doc_id,
            doc_type_code=doc_type_code,
            total_csv_files=0,
            extract_status="fail",
            extract_message=None,
            results=[],
        )
        async with self._get_client() as client:
            try:
                # download document
                content = await self._fetch_doc(doc_id, client, doc_type)

                if type(content) is not bytes:
                    msg = "Document %s parsing failed." % (doc_id)
                    logger.warning(msg)
                    message.extract_message = msg
                    return message
                logger.info("Document %s fetched", doc_id)

                # Open zip file
                with tempfile.NamedTemporaryFile(
                    suffix=".zip", delete=False
                ) as tmp_file:
                    tmp_path = Path(tmp_file.name)

                    try:
                        tmp_file.write(content)
                        tmp_file.flush()
                        real_translator = translator or self.translator

                        result = await process_zip_file(
                            tmp_path,
                            doc_id,
                            doc_type_code,
                            real_translator,
                            custom_fields,
                        )
                        logger.info("Document %s processed", doc_id)
                        return result
                    except KeyboardInterrupt:
                        if tmp_path.exists():
                            tmp_path.unlink()
                    finally:
                        if tmp_path.exists():
                            try:
                                tmp_path.unlink()
                            except Exception as e:
                                logger.warning(
                                    "Could not delete temp file %s: %s", tmp_path, e
                                )

            except EdinetAPIError as e:
                logger.error("Error fetching document %s: %s", doc_id, e)
                message.extract_message = str(e)
                return message

            except Exception as e:
                logger.exception(
                    "Failed to fetch or process individual document for %s",
                    doc_id,
                )
                message.extract_message = f"Critical error: {e!s}"
                return message

        return message

    async def _fetch_doc(
        self,
        doc_id: str,
        client: httpx.AsyncClient,
        doc_type: str,
    ) -> bytes | None:
        url: str = self.URL_DOC + doc_id
        params = {
            "type": doc_type,
            "Subscription-Key": self.subscription_key,
        }

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
                response = await client.get(url, params=params)
                st_code: int = response.status_code

                logger.debug("Status code %s", st_code)
                if st_code == self.ResponseStatus.SUCCESS.value:  # 200
                    try:
                        message = response.json()
                        logger.warning("Bad request: %s", message)
                        return message
                    except (UnicodeDecodeError, ValueError):
                        pass
                    return response.content

                elif st_code == self.ResponseStatus.BAD_REQUEST.value:  # 400
                    raise EdinetClientError(
                        f"Bad request (likely no CSV data for this doc): {st_code}",
                        st_code,
                    )
                elif st_code == self.ResponseStatus.NOT_FOUND.value:  # 404
                    raise EdinetClientError(f"Document {doc_id} not found", st_code)
                elif st_code == self.ResponseStatus.AUTH_ERROR.value:  # 401
                    raise EdinetAPIAuthError(
                        "Authentication failed - check subscription key",
                        st_code,
                    )
                elif st_code == self.ResponseStatus.RATE_LIMIT_ERROR.value:  # 429
                    logger.warning("Rate limit exceeded")
                    raise EdinetAPIRateLimitError("API rate limit exceeded", st_code)
                elif st_code >= self.ResponseStatus.SERVER_ERROR.value:  # 500
                    raise EdinetServerError(f"Server error {st_code}", st_code)

                raise EdinetAPIError(f"Unknown status {st_code}")

        raise EdinetAPIError("Retries exhausted")
