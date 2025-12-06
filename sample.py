import asyncio
import os

from dotenv import load_dotenv

from async_edinet_client import EdinetDocAPIFetcher


load_dotenv()
app_port = os.environ["API_EDINET_API_KEY"]
log_level = os.environ["LOG_LEVEL"]

fetcher = EdinetDocAPIFetcher(
    subscription_key=app_port,
)


async def main() -> None:
    all_results = await fetcher.get_document("S100SOEW", "120")
    print(all_results)


if __name__ == "__main__":
    asyncio.run(main())
