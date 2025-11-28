from typing import Literal, TypeVar

from pydantic import BaseModel, Field, field_validator

from .base import MessageBaseModel, ResultsBaseModel


V = TypeVar("V")


class DocResult(ResultsBaseModel):
    element_id: str = Field(validation_alias="要素ID")
    item_name: str | None = Field(validation_alias="項目名")
    context_identifier: str = Field(validation_alias="コンテキストID")
    relative_period: str | None = Field(validation_alias="相対年度")
    consolidated_individual: str | None = Field(validation_alias="連結・個別")
    period_or_time: str | None = Field(validation_alias="期間・時点")
    currency_id: str = Field(validation_alias="ユニットID")
    reported_unit: str | None = Field(validation_alias="単位")
    value: int | float | str | None = Field(validation_alias="値")
    _source_file: str

    @field_validator("value", mode="before")
    @classmethod
    def smart_value_parser(cls, v: V) -> V:
        if isinstance(v, str):
            try:
                return int(v)
            except ValueError:
                try:
                    return float(v)
                except ValueError:
                    return v
        return v


class ExMixIn(BaseModel):
    doc_id: str
    doc_type_code: str
    total_csv_files: int
    extract_status: Literal["success", "fail"]
    extract_message: str | None


class ExtractDocMessage(MessageBaseModel, ExMixIn): ...


V = TypeVar("V")


class MetadataExtract(BaseModel):
    filer_name_eng: str | None = Field(
        default=None,
        validation_alias="jpdei_cor:FilerNameInEnglishDEI",
    )
    security_code: int | str | None = Field(
        default=None,
        validation_alias="jpdei_cor:SecurityCodeDEI",
    )
    accounting_standard: str | None = Field(
        default=None,
        validation_alias="jpdei_cor:AccountingStandardsDEI",
    )
    edinet_code: str | None = Field(
        default=None,
        validation_alias="jpdei_cor:EDINETCodeDEI",
    )
    company_name_cover_eng: str | None = Field(
        default=None,
        validation_alias="jpcrp_cor:CompanyNameInEnglishCoverPage",
    )
    consolidated: bool | str | None = Field(
        default=None,
        validation_alias="jpdei_cor:WhetherConsolidatedFinancialStatementsArePreparedDEI",
    )
    type_of_current_period: str | None = Field(
        default=None,
        validation_alias="jpdei_cor:TypeOfCurrentPeriodDEI",
    )
    current_year_start_date: str | None = Field(
        default=None,
        validation_alias="jpdei_cor:CurrentFiscalYearStartDateDEI",
    )
    current_period_end_date: str | None = Field(
        default=None,
        validation_alias="jpdei_cor:CurrentPeriodEndDateDEI",
    )
    current_fiscal_year_end_date: str | None = Field(
        default=None,
        validation_alias="jpdei_cor:CurrentFiscalYearEndDateDEI",
    )
    previous_fiscal_year_start_date: str | None = Field(
        default=None,
        validation_alias="jpdei_cor:PreviousFiscalYearStartDateDEI",
    )
    comparative_period_end_date: str | None = Field(
        default=None,
        validation_alias="jpdei_cor:ComparativePeriodEndDateDEI",
    )
    previous_fiscal_year_end_date: str | None = Field(
        default=None,
        validation_alias="jpdei_cor:PreviousFiscalYearEndDateDEI",
    )
    is_amendment: bool | None = Field(
        default=None,
        validation_alias="jpdei_cor:AmendmentFlagDEI",
    )
    business_description: str | None

    @field_validator("is_amendment", "consolidated", mode="before")
    @classmethod
    def smart_value_parser(cls, v: V) -> V:
        if isinstance(v, str):
            try:
                return bool(v)
            except ValueError:
                return v
        return v


class FullDocMessage(ExtractDocMessage, MetadataExtract): ...
