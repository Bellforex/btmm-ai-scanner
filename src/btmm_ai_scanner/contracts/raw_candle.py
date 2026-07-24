from datetime import UTC, datetime
from decimal import Decimal
from enum import StrEnum

from pydantic import field_validator, model_validator

from btmm_ai_scanner.contracts.types import (
    ContractModel,
    SemVer,
    SHA256Fingerprint,
    UUIDv7,
)


class CandleCompleteness(StrEnum):
    CONFIRMED_COMPLETE = "CONFIRMED_COMPLETE"
    INCOMPLETE = "INCOMPLETE"
    UNKNOWN = "UNKNOWN"


class CandleVolumeKind(StrEnum):
    TICK = "TICK"
    TRADE = "TRADE"
    UNKNOWN = "UNKNOWN"


def require_aware_datetime(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("Datetime must be timezone-aware.")
    return value


def to_utc(value: datetime) -> datetime:
    return require_aware_datetime(value).astimezone(UTC)


def require_nonblank_stripped_text(value: str) -> str:
    if value == "" or value.strip() != value or value.strip() == "":
        raise ValueError(
            "Value must be nonempty and must not have leading, trailing, or"
            " whitespace-only content."
        )
    return value


def validate_price(value: Decimal) -> Decimal:
    if value <= 0:
        raise ValueError("Prices must be strictly greater than zero.")
    return value


def validate_volume(value: Decimal | None) -> Decimal | None:
    if value is not None and value < 0:
        raise ValueError("Volume must be greater than or equal to zero.")
    return value


class RawCandle(ContractModel):
    record_id: UUIDv7
    content_fingerprint: SHA256Fingerprint

    provider: str
    source_reference: str
    source_symbol: str
    source_timeframe: str

    event_time_utc: datetime
    availability_time_utc: datetime
    processing_time_utc: datetime

    original_event_time: datetime
    original_availability_time: datetime
    original_timezone: str

    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal

    volume: Decimal | None
    volume_kind: CandleVolumeKind
    completeness: CandleCompleteness

    rule_version: SemVer
    contract_version: SemVer
    schema_version: SemVer
    provenance_id: UUIDv7

    @field_validator(
        "provider",
        "source_reference",
        "source_symbol",
        "source_timeframe",
        "original_timezone",
    )
    @classmethod
    def _validate_source_strings(cls, value: str) -> str:
        return require_nonblank_stripped_text(value)

    @field_validator("event_time_utc", "availability_time_utc", "processing_time_utc")
    @classmethod
    def _normalize_canonical_timestamps(cls, value: datetime) -> datetime:
        return to_utc(value)

    @field_validator("original_event_time", "original_availability_time")
    @classmethod
    def _require_aware_original_timestamps(cls, value: datetime) -> datetime:
        return require_aware_datetime(value)

    @field_validator("open", "high", "low", "close")
    @classmethod
    def _validate_ohlc_prices(cls, value: Decimal) -> Decimal:
        return validate_price(value)

    @field_validator("volume")
    @classmethod
    def _validate_volume_value(cls, value: Decimal | None) -> Decimal | None:
        return validate_volume(value)

    @model_validator(mode="after")
    def _validate_cross_field_rules(self) -> "RawCandle":
        if self.original_event_time.astimezone(UTC) != self.event_time_utc:
            raise ValueError(
                "original_event_time must represent the same instant as event_time_utc."
            )
        if (
            self.original_availability_time.astimezone(UTC)
            != self.availability_time_utc
        ):
            raise ValueError(
                "original_availability_time must represent the same instant as"
                " availability_time_utc."
            )

        if not self.availability_time_utc > self.event_time_utc:
            raise ValueError("availability_time_utc must be later than event_time_utc.")
        if not self.processing_time_utc >= self.event_time_utc:
            raise ValueError(
                "processing_time_utc must be greater than or equal to event_time_utc."
            )
        if (
            self.completeness == CandleCompleteness.CONFIRMED_COMPLETE
            and not self.processing_time_utc >= self.availability_time_utc
        ):
            raise ValueError(
                "CONFIRMED_COMPLETE requires processing_time_utc to be greater"
                " than or equal to availability_time_utc."
            )

        if self.high < self.open or self.high < self.close or self.high < self.low:
            raise ValueError(
                "high must be greater than or equal to open, close, and low."
            )
        if self.low > self.open or self.low > self.close:
            raise ValueError("low must be less than or equal to open and close.")

        if self.volume_kind in (CandleVolumeKind.TICK, CandleVolumeKind.TRADE):
            if self.volume is None:
                raise ValueError(
                    "volume is required when volume_kind is TICK or TRADE."
                )
        return self
