from datetime import UTC, datetime
from typing import Generic, TypeVar

from pydantic import AliasGenerator, BaseModel, ConfigDict, field_serializer
from pydantic.alias_generators import to_camel


class ResultsBaseModel(BaseModel):
    """
    Schema for base results
    """

    model_config = ConfigDict(
        alias_generator=AliasGenerator(serialization_alias=to_camel),
        populate_by_name=True,
        from_attributes=True,
    )


T = TypeVar("T")


class MessageBaseModel(BaseModel, Generic[T]):
    """
    Schema for base message
    """

    process_date: datetime = datetime.now(UTC)
    results: list[T | None]

    model_config = ConfigDict(
        alias_generator=AliasGenerator(serialization_alias=to_camel),
        populate_by_name=True,
        from_attributes=True,
    )

    @field_serializer("process_date", when_used="json")
    def serialize_process_datetime(self, dt: datetime) -> str:
        return dt.strftime("%Y-%m-%d %H:%M:%S")

    def flat(self) -> list[dict]:
        meta = self.model_dump()
        structured_data = meta.pop("results")
        if structured_data:
            return [{**meta, **r} for r in structured_data]
        return [meta]
