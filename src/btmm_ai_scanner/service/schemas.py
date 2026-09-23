"""HTTP request/response schemas for the internal scanner service
(Phase 5 — "internal scanner API"). These are the ONLY models an external
caller (Bell Academy Hub's Laravel backend) needs to know about; the
analytical engine's own internal types (``ScannerAnalysis``, ``BtrcDecision``,
etc.) never cross this boundary directly.

Deliberately explicit request/response schemas (Phase 3's own requirement),
strict validation, no arbitrary/untyped payloads.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from btmm_ai_scanner.config.enums import InternalSymbol, Timeframe
from btmm_ai_scanner.correlation.contract import AnnotationContract, TopDownWebContract
from btmm_ai_scanner.correlation.enums import TradingMode

# A generous but bounded per-timeframe candle count — this is a request-size
# guard (Phase 3: "enforce request size limits"), not a data-quality
# decision; the caller is responsible for supplying a sensible lookback
# (see docs/BTMM_SCANNER_WEB_INTEGRATION.md "OHLC fetch").
MAX_CANDLES_PER_TIMEFRAME = 2000
MAX_TIMEFRAMES_PER_REQUEST = 13  # exactly the full Timeframe enum, never more


class RawBar(BaseModel):
    """One already-CLOSED OHLC bar. The service never infers or resamples —
    every bar the caller sends is treated as a confirmed, complete candle
    (see "Partial candle policy" in the integration doc); a still-forming
    bar must never be submitted here."""

    # Deliberately NOT strict=True: this is the true JSON boundary, and JSON
    # has no native Decimal/datetime type — strict mode would reject every
    # ordinary JSON request body (it requires already-constructed Decimal/
    # datetime instances, not the ISO strings/numeric strings any real HTTP
    # client sends). extra="forbid" still rejects unknown fields.
    model_config = ConfigDict(extra="forbid")

    time: datetime = Field(description="The bar's OPEN time, UTC or tz-aware.")
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal | None = None

    @field_validator("time")
    @classmethod
    def _require_aware(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("time must be timezone-aware.")
        return value

    @field_validator("open", "high", "low", "close")
    @classmethod
    def _require_positive(cls, value: Decimal) -> Decimal:
        if value <= 0:
            raise ValueError("OHLC prices must be strictly positive.")
        return value

    @field_validator("volume")
    @classmethod
    def _require_non_negative_volume(cls, value: Decimal | None) -> Decimal | None:
        if value is not None and value < 0:
            raise ValueError("volume must be greater than or equal to zero.")
        return value

    @model_validator(mode="after")
    def _require_consistent_ohlc(self) -> RawBar:
        # A clean, immediate 422 for a malformed bar here — rather than a
        # deep, harder-to-read failure inside NormalizedCandle's own
        # cross-field validator once this reaches candles.py.
        if self.high < self.open or self.high < self.close or self.high < self.low:
            raise ValueError("high must be greater than or equal to open, close, and low.")
        if self.low > self.open or self.low > self.close:
            raise ValueError("low must be less than or equal to open and close.")
        return self


class AnalyzeRequest(BaseModel):
    """POST /v1/analyze — Phase 5's own contract. Screenshots are
    deliberately NOT part of this schema (Phase 5: "Do NOT send screenshots
    to the deterministic Python endpoint. Screenshots are not analytical
    inputs for this engine.")."""

    model_config = ConfigDict(extra="forbid")

    request_id: str = Field(min_length=1, max_length=128)
    symbol: InternalSymbol
    mode: TradingMode
    presentation_timeframe: Timeframe | None = None
    # Keyed by Timeframe — pydantic validates each JSON string key against
    # the real enum, so an unsupported timeframe string is a 422, never
    # silently ignored.
    timeframes: dict[Timeframe, list[RawBar]]
    # Provenance/audit only (stamped onto the constructed candles' own
    # `provider` field) — never used to resolve symbol/timeframe strings;
    # the caller must already send real InternalSymbol/Timeframe values.
    source_provider: str = Field(default="BELLFOREX_WEB", min_length=1, max_length=64)

    @field_validator("timeframes")
    @classmethod
    def _validate_timeframe_bundle(
        cls, value: dict[Timeframe, list[RawBar]]
    ) -> dict[Timeframe, list[RawBar]]:
        if not value:
            raise ValueError("timeframes must not be empty.")
        if len(value) > MAX_TIMEFRAMES_PER_REQUEST:
            raise ValueError(
                f"timeframes must not contain more than {MAX_TIMEFRAMES_PER_REQUEST} entries."
            )
        for timeframe, bars in value.items():
            if not bars:
                raise ValueError(f"timeframes[{timeframe.value}] must not be empty.")
            if len(bars) > MAX_CANDLES_PER_TIMEFRAME:
                raise ValueError(
                    f"timeframes[{timeframe.value}] must not contain more than"
                    f" {MAX_CANDLES_PER_TIMEFRAME} candles."
                )
        return value


class AnalyzeResponse(BaseModel):
    """The full result — the versioned web contract plus the annotation
    contract, wrapped with request/service identity so Bell Academy Hub can
    always tell exactly which request and which scanner build produced it
    (Phase 4: version pinning)."""

    model_config = ConfigDict(extra="forbid", strict=True)

    request_id: str
    scanner_git_sha: str
    contract: TopDownWebContract
    annotations: AnnotationContract


class HealthResponse(BaseModel):
    """GET /health — Phase 6: safe metadata only, never environment,
    filesystem paths, secrets, or git credentials."""

    model_config = ConfigDict(extra="forbid", strict=True)

    status: str
    scanner_git_sha: str
    contract_version: str
    schema_version: str
    rule_version: str


class ErrorResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    error_code: str
    message: str
    request_id: str | None = None
