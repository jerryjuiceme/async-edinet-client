from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field

from .base import MessageBaseModel, ResultsBaseModel


class DoclistResult(ResultsBaseModel):
    doc_id: str = Field(alias="docID")
    doc_type_code: str = Field(alias="docTypeCode")
    filer_name: str = Field(alias="filerName")
    filer_name_eng: str | None = Field(default=None, alias="filerNameInEnglish")
    edinet_code: str = Field(alias="edinetCode")
    sec_code: str | None = Field(alias="secCode")
    period_start: date | None = Field(alias="periodStart")
    period_end: date | None = Field(alias="periodEnd")
    submit_date_time: datetime | None = Field(alias="submitDateTime")
    form_code: str | None = Field(alias="formCode")
    seq_number: int | None = Field(alias="seqNumber")
    fund_code: str | None = Field(alias="fundCode")
    doc_description: str = Field(alias="docDescription")
    jcn: str | None = Field(alias="JCN")
    xbrl_flag: bool | None = Field(alias="xbrlFlag")
    pdf_flag: bool | None = Field(alias="pdfFlag")
    csv_flag: bool | None = Field(alias="csvFlag")


class DocListMessage(BaseModel):
    request_type: Literal["daily", "interval"]
    date_from: date
    date_to: date
    count: int | None
    results: list[DoclistResult] | list[None]


class DocListSingleMessageMixIn(DocListMessage):
    status_code: int | None
    fetch_status: int | None
    message: str


class DocListMultiMessageMixIn(DocListMessage):
    status_code: list[dict[str, int]]
    fetch_status: list[dict[str, int | None]]
    message: list[dict[str, str | None]]


class DocListSingleMessage(MessageBaseModel, DocListSingleMessageMixIn): ...


class DocListMultiMessage(MessageBaseModel, DocListMultiMessageMixIn): ...
