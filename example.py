import asyncio
from datetime import datetime
import os
from pathlib import Path
from dotenv import load_dotenv


import async_edinet_client

load_dotenv()
app_port = os.environ["API_EDINET_API_KEY"]
log_level = os.environ["LOG_LEVEL"]

cur_dir = Path(__file__).parent
timestamp = f"{datetime.now().strftime('%Y-%m-%d_%H:%M:%S.%f')}.json"


ANNUAL_DOCS: list[str] = [
    "S100U05T",
    "S100U081",
    "S100TJG9",
    "S100TM9A",
    "S100VURP",
    "S100STJN",
    "S100STHT",
]


CUSTOM_FIELDS: list[str] = [
    "jppfs_cor:RedemptionPayableCLFND",
    "jppfs_cor:OperatingRevenueFND",
    "jppfs_cor:InvestmentTrustManagementFeeOEFND",
    "jppfs_cor:OperatingExpensesFND",
]


fetcher = async_edinet_client.EdinetAPIFetcher(subscription_key=app_port)


async def single_doc_list():
    single_result = await fetcher.get_filings_daily(
        "2024-07-12",
        bypass_translation=True,
    )
    file_path = cur_dir / f"docs_single_{timestamp}"
    _save_file(file_path, single_result.model_dump_json(indent=4, by_alias=True))


async def multi_doc_list():
    all_results = await fetcher.get_filings_period("2025-09-20", "2025-10-02")
    file_path = cur_dir / f"docs_multi_{timestamp}"
    _save_file(file_path, all_results.model_dump_json(indent=4, by_alias=True))


async def single_doc(doc: str = "S100WRZY") -> None:
    results = await fetcher.get_document(doc_id=doc)

    file_path = cur_dir / f"doc_output_{doc}_{timestamp}"
    _save_file(file_path, results.model_dump_json(indent=4, by_alias=True))


async def doc_custom_fields(doc: str = "S100WRZY") -> None:
    results = await fetcher.get_document(doc_id=doc, custom_fields=CUSTOM_FIELDS)

    file_path = cur_dir / f"doc_output_{doc}_{timestamp}"
    _save_file(file_path, results.model_dump_json(indent=4, by_alias=True))


def _save_file(file_path: Path, content: str) -> None:
    with open(file_path, mode="w") as file:
        file.write(content)


async def main():
    async_edinet_client.configure_logging(app_level=log_level, httpx_level="WARNING")

    await single_doc_list()
    await multi_doc_list()
    await single_doc()
    await doc_custom_fields()

    # collecting and saving multiple reports
    tasks = [asyncio.create_task(single_doc(doc)) for doc in ANNUAL_DOCS]
    await asyncio.gather(*tasks)


if __name__ == "__main__":
    asyncio.run(main())
