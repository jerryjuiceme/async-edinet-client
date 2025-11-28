import asyncio
import logging
import re
from typing import Any, Final

from .dependencies import BaseTranslator
from .schemas import (
    DocResult,
    MetadataExtract,
)


logger = logging.getLogger(__name__)


class DocProcessor:
    META_PATTERNS: Final = (
        "jpdei_cor:FilerNameInEnglishDEI",
        "jpdei_cor:SecurityCodeDEI",
        "jpdei_cor:AccountingStandardsDEI",
        "jpdei_cor:EDINETCodeDEI",
        "jpcrp_cor:CompanyNameInEnglishCoverPage",
        "jpdei_cor:WhetherConsolidatedFinancialStatementsArePreparedDEI",
        "jpdei_cor:TypeOfCurrentPeriodDEI",
        "jpdei_cor:CurrentFiscalYearStartDateDEI",
        "jpdei_cor:CurrentPeriodEndDateDEI",
        "jpdei_cor:CurrentFiscalYearEndDateDEI",
        "jpdei_cor:PreviousFiscalYearStartDateDEI",
        "jpdei_cor:ComparativePeriodEndDateDEI",
        "jpdei_cor:PreviousFiscalYearEndDateDEI",
        "jpdei_cor:AmendmentFlagDEI",
    )

    CONTEXT_PATTERNS: tuple[str, ...] = ("FilingDate", "Current", "Prior1")

    def __init__(self, custom_fields: list[str] | None) -> None:
        self.custom_fields = custom_fields

    async def process_raw_csv_data(
        self,
        raw_csv_data: list[dict[str, Any]],
        doc_id: str,
        translator: BaseTranslator,
    ) -> tuple[list[DocResult | None], int, MetadataExtract]:
        """
        Process raw CSV data and filter based on context ID patterns.
        """
        filtered_results = []
        metadata_container = {}
        business_description = ""
        # Context ID patterns to filter by

        try:
            for csv_file_data in raw_csv_data:
                filename = csv_file_data.get("filename", "unknown")
                csv_records = csv_file_data.get("data", [])

                if not csv_records:
                    logger.debug("No data in CSV file: %s", filename)
                    continue

                file_filtered_records = []

                for record in csv_records:
                    # Check if record has required fields
                    context_id = record.get("コンテキストID")
                    if not context_id:
                        continue

                    ### Filter by context ID patterns ###
                    context_id_str = str(context_id)
                    if any(
                        context_id_str.startswith(pattern)
                        for pattern in DocProcessor.CONTEXT_PATTERNS
                    ):
                        cleaned_record = DocResult(_source_file=filename, **record)

                        ### Extract metadata ###
                        if cleaned_record.element_id in DocProcessor.META_PATTERNS:
                            metadata_container[cleaned_record.element_id] = (
                                cleaned_record.value
                            )
                            continue
                        ### Extract business description ###
                        if self.pattern_match(
                            r".*DescriptionOfBusiness.*",
                            cleaned_record.element_id,
                        ):
                            translated = await translator.translate(
                                str(cleaned_record.value)
                            )
                            business_description = business_description + translated
                            continue

                        ### Filter by custom fields ###
                        if self.custom_fields is not None:
                            if cleaned_record.element_id in self.custom_fields:
                                file_filtered_records.append(cleaned_record)
                                continue
                            else:
                                continue
                        file_filtered_records.append(cleaned_record)

                    await asyncio.sleep(0)

                filtered_results.extend(file_filtered_records)
                logger.debug(
                    "Find %d records from %s", len(file_filtered_records), filename
                )
                await asyncio.sleep(0)

            logger.info(
                "Successfully processed %d records from %d CSV files for doc_id: %s",
                len(filtered_results),
                len(raw_csv_data),
                doc_id,
            )
            metadata_container["business_description"] = business_description
            metadata = MetadataExtract(**metadata_container)
            logger.debug("Metadata Found: %s", metadata.__dict__)

            # Return filtered results
            return (filtered_results, len(raw_csv_data), metadata)

        except Exception as e:
            logger.error("Error processing raw CSV data for doc_id %s: %s", doc_id, e)
            raise

    def pattern_match(self, pattern, text) -> bool:
        return bool(re.search(pattern, text))
