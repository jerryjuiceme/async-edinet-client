# async-edinet-client

[![Python 3.12–3.13](https://img.shields.io/badge/Python-3.12--3.13-000000?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![Last Commit](https://img.shields.io/github/last-commit/jerryjuiceme/async-edinet-client?style=for-the-badge&color=000000)](https://github.com/jerryjuiceme/async-edinet-client/commits)

![Pydantic](https://img.shields.io/badge/Pydantic-000000?style=for-the-badge&logo=pydantic&logoColor=white)
![HTTPX](https://img.shields.io/badge/HTTPX-000000?style=for-the-badge&logo=fastapi&logoColor=white)
![Translate](https://img.shields.io/badge/Google%20Translate-000000?style=for-the-badge&logo=google)

## Description

**async-edinet-client** is an asynchronous integration with EDINET (Electronic Disclosure for Investors' NETwork), the financial reporting registry for Japanese public companies.

This library enables the retrieval of specific financial and non-financial reports, as well as lists of filed reports for specific dates or periods. It utilizes **Pydantic** for data validation and transfer, and **HTTPX** for asynchronous API requests. Additionally, it features an asynchronous integration with **Google Translate** to automatically translate report descriptions and company/fund names from Japanese to English.

## Tech Stack

- **Language:** Python 3.12+
- **Validation:** Pydantic
- **HTTP Client:** HTTPX
- **Translation:** Google Translate
- **Package Manager:** uv

## Quickstart

To get started, initialize the fetcher with your API key. You can obtain a free API subscription key [here](https://disclosure2.edinet-fsa.go.jp/).

```py
import async_edinet_client
import asyncio


fetcher = async_edinet_client.EdinetAPIFetcher(subscription_key="YOUR_API_KEY")


async def get_reports():
    result = await fetcher.get_filings_daily("2024-07-12")
    print(result)


async def get_reports_for_period():
    result = await fetcher.get_filings_period("2024-07-12", "2024-07-12")
    print(result)


async def get_a_report():
    result = await fetcher.get_document(doc_id="S100WRZY")
    print(result)


async def main():
    await get_reports()
    await get_reports_for_period()
    await get_a_report()


if __name__ == "__main__":
    asyncio.run(main())
```

### Advanced Initialization

You can import and configure clients for fetching documents and filing lists separately if needed. Connection parameters (polling interval, retry attempts, timeouts) can be customized during object creation.

```py
from async_edinet_client import EdinetDocAPIFetcher, EdinetDoclistAPIFetcher

doclist_fetcher = EdinetDoclistAPIFetcher(
    subscription_key="YOUR_API_KEY",
    fetch_interval=0.5,
    description_translation=False,
)

document_fetcher = EdinetDocAPIFetcher(
    subscription_key="YOUR_API_KEY",
)
```

**`EdinetAPIFetcher` Arguments:**

- `subscription_key`: API subscription key.
- `fetch_interval`: Delay between API requests in seconds.
- `retry_attempts`: Number of retry attempts for failed requests.
- `retry_timeout`: Total timeout for retry attempts in seconds.
- `request_timeout`: Individual request timeout in seconds.
- `description_translation`: Enable or disable automatic description translation.

## Core Implementation

The library implements three main methods for data retrieval:

1.  `get_filings_daily(date="YYYY-MM-DD")`: Retrieves a list of reports published on a specific date.
2.  `get_filings_period(date_from="YYYY-MM-DD", date_to="YYYY-MM-DD")`: Retrieves a list of reports published over a specific time period.
3.  `get_document(doc_id="S100WRZY")`: Retrieves a specific company report using its document registration number.

## Automatic Translation

This library implements automatic translation of specific fields (such as company names and report descriptions) from Japanese to English. This is achieved asynchronously using a native Google Translate integration.

### ⚠️ Disclaimer

> Please remember that enabling translation to English results in additional requests to the Google API. This is especially relevant when fetching lists of reports over a period of time. Although these requests are performed asynchronously, waiting for the translation of 1000+ company names may take several dozen seconds.
>
> **If speed is critical for your application, it is recommended to disable translation.**

If a translation fails, no error will be raised. Instead, the field will be prefixed with: `"Not translated: "`.

### Disabling Translation

You can disable translation globally when creating the client object, or for specific function calls using the `bypass_translation` argument.

If `bypass_translation` is set to `True`, translation will be skipped for that specific call, even if the global translator is configured.

```py
fetcher = EdinetAPIFetcher(subscription_key="YOUR_API_KEY")

filings = await fetcher.get_filings_daily("2024-07-12", bypass_translation=True)
document = await fetcher.get_document(doc_id="S100WRZY", bypass_translation=True)
```

When translation is disabled, the relevant fields will contain the prefix: `"translation disabled: "`.

## Data Output & Serialization

Data validation and serialization are handled by **Pydantic**. By default, all functions return Pydantic models containing request metadata and nested results lists.

For financial reports (`get_document`), the metadata includes report type, filing dates, amendment status, etc., while the financial indicators are stored in a nested `results` list.

This structure allows for easy serialization into normalized JSON:

```py
result.model_dump_json(indent=4, by_alias=True)
```

### Flat Structure (CSV Ready)

For analytics or data denormalization purposes, every data object includes a `.flat()` method. This transforms the object into a flat structure (a list of dictionaries), where metadata is duplicated for every row. This is ideal for saving directly to CSV.

```py
import pandas as pd
from async_edinet_client import EdinetAPIFetcher

fetcher = EdinetAPIFetcher(subscription_key="YOUR_API_KEY")

document = await fetcher.get_document(doc_id="S100WRZY")

# Get the flat result list[dict]
flat_result = result.flat()
df = pd.DataFrame(flat_result)
df.to_csv("test.csv", index=False)
```

###

### Example Outputs

You can view examples of the output structures in the `example_outputs` directory:

- [Single Document JSON](example_outputs/document_example.json)
- [Daily Filings JSON](example_outputs/filings_daily_example.json)
- [Period Filings JSON](example_outputs/filings_interval_example.json)
- [Flattened Document CSV](example_outputs/flat_document_example.csv)
- [Flattened Filings CSV](example_outputs/flat_filings_example.csv)

## Filtering Document Types

When requesting lists of filed documents, you can filter to retrieve only specific report types. This is done using the `doc_types` parameter, which accepts a list of report code strings.

```py
reports = await fetcher.get_filings_daily("2024-07-12", doc_types=["180", "130", "120"])
```

```py
reports = await fetcher.get_filings_period("2024-07-12", "2024-07-12",  doc_types=["180", "130", "120"])
```

If not specified, the following default report types are fetched:

| Code    | Description                                    |
| :------ | :--------------------------------------------- |
| **160** | Semi-Annual Report                             |
| **140** | Quarterly Report                               |
| **120** | Securities Report                              |
| **030** | Securities Registration Statement              |
| **040** | Amendment of Securities Registration Statement |
| **170** | Amendment of semi-annual report                |
| **150** | Amendment of quarterly report                  |
| **130** | Amendment of securities report                 |
| **180** | Extraordinary Report                           |

## Document Attributes & Error Handling

### Raise on Error

The `get_document` method includes a `raise_on_error` parameter.

- **False (Default):** Errors are captured in the output with `extract_status="fail"` and a description in the `message` field. This is useful for pipelines that should not crash on a single failure.
- **True:** The method will raise an exception immediately upon failure.

```py
result = await fetcher.get_document(doc_id="S100WRZY", raise_on_error=True)
```

### Filtering Custom Fields

If you only need specific fields from a report, you can filter the results by passing a list of field names.

```py
CUSTOM_FIELDS = [
    "jppfs_cor:RedemptionPayableCLFND",
    "jppfs_cor:OperatingRevenueFND",
    "jppfs_cor:InvestmentTrustManagementFeeOEFND",
    "jppfs_cor:OperatingExpensesFND",
]

result = await fetcher.get_document(doc_id="S100WRZY", custom_fields=CUSTOM_FIELDS)
```

_Tip: Since XBRL taxonomies can be complex, it is recommended to first download a full report to identify the specific field names you require._

## Logging

The library uses the standard Python `logging` module. It does not configure logging handlers upon initialization, allowing it to integrate seamlessly into your existing logging setup.

### ❗ Important

We use **HTTPX** for requests. Since the EDINET API key is passed as a query parameter, there is a risk that your secret key may be logged by HTTPX debug logs. **We strongly recommend configuring HTTPX logging levels carefully.**

If you are running a standalone script or need a quick demo, you can use the provided helper methods to configure logging safely:

```py
import async_edinet_client

# Default: INFO for app, WARNING for httpx
async_edinet_client.configure_logging()

# Custom configuration
async_edinet_client.configure_logging(app_level="DEBUG", httpx_level="INFO")

# Configure only HTTPX logging (default WARNING)
async_edinet_client.configure_logging_httpx()
```

---

## HTTP Client Injection 

By default, the library manages the lifecycle of the HTTP client internally. Each API call will transparently create and close an `httpx.AsyncClient` with proper timeouts and connection limits.

However, **all public API methods support injecting an external `httpx.AsyncClient`**. This allows advanced users to **reuse an existing client**, enabling connection pooling, keep-alive, and seamless integration with application-level dependency injection (DI).

### Advanced Usage — Client Reuse

You can create an `httpx.AsyncClient` once and reuse it across multiple API calls.

```py
import httpx
from async_edinet_client import EdinetDocAPIFetcher

async with httpx.AsyncClient() as client:
    fetcher = EdinetDocAPIFetcher(subscription_key="YOUR_API_KEY")

    document = await fetcher.get_document(
        doc_id="S100TM9A",
        client=client,
    )
```

In this mode, the client is **borrowed** by the library and will **not** be closed after the request.

### FastAPI Integration (DI + Lifespan)

For web applications, the recommended approach is to create a shared HTTP client during application startup and inject it into handlers.

```py
@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.http_client = httpx.AsyncClient()
    yield
    await app.state.http_client.aclose()

```

```py
doc = await fetcher.get_document(
    "S100TM9A",
    client=request.app.state.http_client,
)

```
