import asyncio
import logging
from pathlib import Path
import tempfile
from types import coroutine
from typing import Any
import zipfile

import chardet
import pandas as pd

from .dependencies import BaseTranslator
from .doc_processor import DocProcessor
from .schemas import (
    DocResult,
    ExtractDocMessage,
    FullDocMessage,
)


logger = logging.getLogger(__name__)


# Constants for CSV processing
COMMON_ENCODINGS: list[str] = [
    "utf-16",
    "utf-16le",
    "utf-16be",
    "utf-8",
    "shift-jis",
    "euc-jp",
    "iso-8859-1",
    "windows-1252",
]


######################
### Zip processing ###
######################


async def process_zip_file(
    path_to_zip_file: Path,
    doc_id: str,
    doc_type_code: str,  # Passed to process_raw_csv_data
    translator: BaseTranslator,
    custom_fields: list[str] | None,
) -> ExtractDocMessage[DocResult]:
    """
    Asynchronously extracts CSVs from a ZIP file, reads them, and processes
    them into structured data.

    """
    raw_csv_data_list: list[dict[str, Any]] = []
    # loop = asyncio.get_running_loop()
    extracted_result: ExtractDocMessage[DocResult] = ExtractDocMessage(
        doc_id=doc_id,
        doc_type_code=doc_type_code,
        total_csv_files=0,
        extract_status="fail",
        extract_message=None,
        results=[],
    )
    raw_processor = DocProcessor(custom_fields=custom_fields)
    try:
        # Use a real temporary directory that cleans up automatically
        with tempfile.TemporaryDirectory(prefix="edinet_unzip_") as temp_dir_str:
            temp_dir = Path(temp_dir_str)
            logger.debug("Created temporary directory: %s", temp_dir)

            try:
                await asyncio.to_thread(_sync_extract_zip, path_to_zip_file, temp_dir)
                logger.debug("Extracted '%s' to '%s'", path_to_zip_file.name, temp_dir)
            except zipfile.BadZipFile as e:
                msg = "Bad ZIP file: '%s'. Err: %s" % (path_to_zip_file, e)
                extracted_result.extract_message = msg
                logger.warning(msg)
                return extracted_result

            except Exception as e:  # Catch other extraction errors
                msg = "Error extracting '%s': %s" % (path_to_zip_file, e)
                extracted_result.extract_message = msg
                logger.error(msg)
                return extracted_result

            # Find all CSV files, excluding those in __MACOSX directories
            csv_file_paths = _find_csv_paths(temp_dir)

            if not csv_file_paths:
                msg = "No CSV files found in zip: '%s'" % path_to_zip_file.name
                extracted_result.extract_message = msg
                logger.warning(msg)
                return extracted_result

            logger.info(
                "Found %d CSV files to process in '%s'",
                len(csv_file_paths),
                path_to_zip_file.name,
            )

            # Read the CSV files asynchronously
            results = await _read_files(csv_file_paths)

            # Associate filenames with successfully read data
            valid_csv_paths = [
                fp for fp in csv_file_paths if not fp.name.lower().startswith("jpaud")
            ]
            for i, csv_records in enumerate(results):
                file_path = valid_csv_paths[i]  # Assumes order is maintained by gather
                if isinstance(csv_records, Exception):
                    logger.error(
                        "Error reading CSV file '%s': %s",
                        file_path.name,
                        csv_records,
                    )
                    continue
                if csv_records is not None:
                    raw_csv_data_list.append(
                        {"filename": file_path.name, "data": csv_records}
                    )
                else:
                    logger.warning(
                        "No data could be read from CSV: '%s'", file_path.name
                    )
                await asyncio.sleep(0)

            # Process the collected raw data
            # This part is CPU-bound data manipulation, so it can run synchronously
            # within the async function unless it's extremely heavy.

            pack = await raw_processor.process_raw_csv_data(
                raw_csv_data_list,
                doc_id,
                translator,
            )
            structured_data, total_csv_files, metadata = pack

            extracted_result.total_csv_files = total_csv_files
            extracted_result.results = structured_data
            extracted_result.extract_status = "success"
            logger.info(
                "Successfully processed structured data for '%s'",
                path_to_zip_file.name,
            )

    except Exception as e:
        msg = "Critical error processing zip file '%s': %s" % (path_to_zip_file, e)
        extracted_result.extract_message = msg
        logger.error(msg, exc_info=True)
        return extracted_result

    return FullDocMessage(**metadata.__dict__, **extracted_result.__dict__)


###############
### Helpers ###
###############

# --- Synchronous helpers for threading ---


def _sync_detect_encoding(file_path: Path) -> str | None:
    """Synchronous part of encoding detection for use in a thread."""
    try:
        with open(file_path, "rb") as file:
            raw_data = file.read(1024)  # Read only first 1024 bytes for speed
        if not raw_data:
            logger.warning(
                "File '%s' is empty, cannot detect encoding.", file_path.name
            )
            return None
        result = chardet.detect(raw_data)
        if result["encoding"]:
            logger.debug(
                "Detected encoding %s with confidence %.2f for %s",
                result["encoding"],
                result["confidence"],
                file_path.name,
            )
            return result["encoding"]
        else:
            logger.warning("Chardet could not detect encoding for %s.", file_path.name)
            return None
    except OSError as e:
        logger.error("Error detecting encoding for %s: %s", file_path, e)
        return None
    except Exception as e:  # Catch any other chardet related errors
        logger.error(
            "Unexpected error during encoding detection for %s: %s", file_path, e
        )
        return None


def _sync_read_csv_with_encoding(file_path: Path, encoding: str) -> pd.DataFrame | None:
    """Synchronous part of CSV reading for use in a thread."""
    try:
        df = pd.read_csv(
            file_path, encoding=encoding, sep="\t", dtype=str, low_memory=False
        )
        logger.debug("Successfully read %s with encoding %s", file_path.name, encoding)
        df = df.replace({float("nan"): None, "": None})
        return df
    except (UnicodeDecodeError, pd.errors.EmptyDataError, pd.errors.ParserError) as e:
        logger.debug(
            "Failed to read %s with encoding %s: %s", file_path.name, encoding, e
        )
        return None
    except Exception as e:
        logger.error(
            "An unexpected error occurred reading %s with encoding %s: %s",
            file_path.name,
            encoding,
            e,
        )
        return None


def _sync_extract_zip(zip_path: Path, extract_to_dir: Path) -> None:
    """Synchronous zip extraction for use in a thread."""
    with zipfile.ZipFile(zip_path, "r") as zip_ref:
        zip_ref.extractall(extract_to_dir)


def _find_csv_paths(temp_dir: Path) -> list[Path]:
    csv_file_paths: list[Path] = []
    for item in temp_dir.rglob("*.csv"):
        # Check if any part of the path contains __MACOSX
        if "__MACOSX" not in [part.name for part in item.parents]:
            csv_file_paths.append(item)
        else:
            logger.debug("Skipping file in __MACOSX directory: %s", item)
    return csv_file_paths


async def _read_files(csv_file_paths: list[Path]) -> list[Any | BaseException]:
    tasks: list[coroutine.Coroutine] = []
    for file_path in csv_file_paths:
        if file_path.name.lower().startswith("jpaud"):
            logger.debug("Skipping auditor report file: '%s'", file_path.name)
            continue
        tasks.append(read_csv_file(file_path))
    results = await asyncio.gather(*tasks, return_exceptions=True)

    return results


# --- Asynchronous Functions ---


async def detect_encoding(file_path: Path) -> str | None:
    """
    Detect encoding of a file asynchronously.
    File I/O and chardet are blocking, so run in a thread.
    """
    # loop = asyncio.get_running_loop()
    return await asyncio.to_thread(_sync_detect_encoding, file_path)


async def read_csv_file(file_path: Path) -> list[dict[str, Any]] | None:
    """
    Read a tab-separated CSV file asynchronously, trying multiple encodings.
    Pandas CSV reading is blocking, so run in a thread.
    """
    detected_encoding = await detect_encoding(file_path)

    encodings_to_try: list[str | None] = []
    if detected_encoding:
        encodings_to_try.append(detected_encoding)
    encodings_to_try.extend(COMMON_ENCODINGS)

    # Remove duplicates and None while preserving order
    unique_encodings: list[str] = []
    for enc in encodings_to_try:
        if enc and enc not in unique_encodings:
            unique_encodings.append(enc)

    # loop = asyncio.get_running_loop()
    for encoding in unique_encodings:
        df = await asyncio.to_thread(_sync_read_csv_with_encoding, file_path, encoding)
        if df is not None:
            return df.to_dict(orient="records")  # type: ignore

    logger.error(
        "Failed to read %s. Unable to determine correct encoding or format after trying: %s",
        file_path.name,
        ", ".join(filter(None, unique_encodings)),
    )
    return None


###############
### Logging ###
###############


def configure_logging_temporary(
    app_level: int | str = logging.INFO, httpx_level: int | str = logging.INFO
) -> None:
    app_formatter = logging.Formatter(
        "[%(asctime)s.%(msecs)03d] %(module)10s:line %(lineno)-3d %(levelname)-7s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    app_handler = logging.StreamHandler()
    app_handler.setFormatter(app_formatter)
    app_handler.setLevel(app_level)

    app_logger = logging.getLogger()
    app_logger.setLevel(app_level)
    app_logger.handlers = []
    app_logger.addHandler(app_handler)

    httpx_logger = logging.getLogger("httpx")
    httpx_logger.setLevel(httpx_level)
    httpx_logger.handlers = []
    httpx_logger.addHandler(app_handler)


def configure_logging_httpx(
    httpx_level: int | str = logging.INFO,
    app_formatter: logging.Formatter | None = None,
) -> None:
    if not app_formatter:
        app_formatter = logging.Formatter(
            "[%(asctime)s.%(msecs)03d] %(module)10s:line %(lineno)-3d %(levelname)-7s - %(message)s",  # Noqa
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    app_handler = logging.StreamHandler()
    app_handler.setFormatter(app_formatter)
    httpx_logger = logging.getLogger("httpx")
    httpx_logger.setLevel(httpx_level)
    httpx_logger.handlers = []
    httpx_logger.addHandler(app_handler)
