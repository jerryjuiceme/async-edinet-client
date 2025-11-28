import asyncio
import os
from dotenv import load_dotenv
from edinet_integration import EdinetDoclistAPIFetcher, EdinetDocAPIFetcher

load_dotenv()
app_port = os.environ["API_SUBSCRIPTION_KEY"]
log_level = os.environ["LOG_LEVEL"]

fetcher = EdinetDocAPIFetcher(
    subscription_key=app_port,
)


async def main():
    all_results = await fetcher.get_document("S100SOEW", "120")
    print(all_results)


if __name__ == "__main__":
    asyncio.run(main())
