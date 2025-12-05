import asyncio
from datetime import datetime
import logging
import os
from pathlib import Path
from dotenv import load_dotenv


from edinet_integration import (
    EdinetDocAPIFetcher,
    EdinetDoclistAPIFetcher,
    EdinetAPIFetcher,
    configure_logging,
)


load_dotenv()
app_port = os.environ["API_SUBSCRIPTION_KEY"]
log_level = os.environ["LOG_LEVEL"]

logger = logging.getLogger(__name__)
cur_dir = Path(__file__).parent
DOCS = dict(
    DOC1="E21815", DOC2="S100ST97", DOC3="dfds", DOC4="S100STJN", DOC5="S100STHT"
)

ANNUAL_DOCS = [
    "S100U05T",
    "S100U081",
    "S100TJG9",
    "S100TM9A",
    "S100VURP",
    "S100STJN",
    "S100STHT",
]


CUSTOM_FIELDS = [
    "jppfs_cor:RedemptionPayableCLFND",
    "jppfs_cor:OperatingRevenueFND",
    "jppfs_cor:InvestmentTrustManagementFeeOEFND",
    "jppfs_cor:OperatingExpensesFND",
]


def _save_file(file_path: Path, content: str) -> None:
    with open(file_path, mode="w") as file:
        file.write(content)


# doc_fetcher = EdinetDocAPIFetcher(
#         subscription_key=app_port,
#         fetch_interval=1,
#         description_translation=True,
#     )


async def main_doc(doc: str = "S100WRZY") -> None:
    # fetcher = EdinetDocAPIFetcher(
    #     subscription_key=app_port,
    #     fetch_interval=1,
    #     description_translation=True,
    # )

    fetcher = EdinetAPIFetcher(subscription_key=app_port)
    # DOC_TYPE = "140"
    results = await fetcher.get_document(
        doc_id=doc,
        # custom_fields=CUSTOM_FIELDS,
        # bypass_translation=True,
    )

    file_path = (
        cur_dir
        / f"doc_output_{doc}_{datetime.now().strftime('%Y-%m-%d_%H:%M:%S.%f')}.json"
    )
    _save_file(file_path, results.model_dump_json(indent=4, by_alias=True))


async def multi_doc_list():
    fetcher = EdinetDoclistAPIFetcher(
        subscription_key=app_port,
        fetch_interval=1,
    )
    all_results = await fetcher.fetch_date_interval_doc_list("2025-09-20", "2025-10-02")
    file_path = cur_dir / f"docs_multi{datetime.now().strftime('%Y-%m-%d_%H:%M')}.json"
    _save_file(file_path, all_results.model_dump_json(indent=4, by_alias=True))


async def single_doc_list():
    fetcher = EdinetDoclistAPIFetcher(
        subscription_key=app_port, fetch_interval=1, description_translation=True
    )
    # fetcher = EdinetAPIFetcher(subscription_key=app_port)
    single_result = await fetcher.fetch_single_doc_list(
        "2024-07-12", bypass_translation=True
    )
    file_path = cur_dir / f"docs_single{datetime.now().strftime('%Y-%m-%d_%H:%M')}.json"
    _save_file(file_path, single_result.model_dump_json(indent=4, by_alias=True))


async def wrong_date_doc_list():
    fetcher = EdinetDoclistAPIFetcher(
        subscription_key=app_port,
        fetch_interval=1,
    )
    single_result = await fetcher.fetch_single_doc_list("2028-07-12")
    file_path = cur_dir / f"docs_single{datetime.now().strftime('%Y-%m-%d_%H:%M')}.json"
    _save_file(file_path, single_result.model_dump_json(indent=4, by_alias=True))


async def main():
    # configure_logging(app_level="DEBUG", httpx_level=logging.WARNING)
    configure_logging(app_level=log_level, httpx_level=logging.WARNING)
    # tasks = [asyncio.create_task(main_doc(doc)) for doc in DOCS.values()]
    # tasks = [asyncio.create_task(main_doc(doc)) for doc in ANNUAL_DOCS]
    # tasks.append(asyncio.create_task(multi_doc_list()))
    # tasks.append(asyncio.create_task(single_doc_list()))
    # await wrong_date_doc_list()
    # await single_doc_list()
    # await multi_doc_list()
    await main_doc()
    # await asyncio.gather(*tasks)


if __name__ == "__main__":
    asyncio.run(main())
