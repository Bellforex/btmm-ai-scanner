"""Forward closed-candle construction (A7A) — the FXCM adapter's candle half.

Turns a provider-native ``ProviderCandle`` into a canonical ``NormalizedCandle``
using the SAME closed-candle availability rule as the historical loader:
``availability_time = open_time + native timeframe duration``. Only providers /
timeframes registered in ``market_data.source_mapping`` are accepted (FXCM +
M1/M5/M15 for the pilot). Forming (``is_closed=False``) bars are rejected so
they can never influence scanner semantics.
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime, timedelta
from decimal import Decimal
from types import MappingProxyType

from pydantic import ValidationError

from btmm_ai_scanner.config.enums import Timeframe
from btmm_ai_scanner.contracts.normalized_candle import NormalizedCandle
from btmm_ai_scanner.contracts.raw_candle import CandleCompleteness, CandleVolumeKind
from btmm_ai_scanner.contracts.types import SemVer
from btmm_ai_scanner.forward.identity import (
    derive_forward_fingerprint,
    derive_forward_uuid,
)
from btmm_ai_scanner.forward.transport import ProviderCandle
from btmm_ai_scanner.market_data.source_mapping import (
    UnsupportedProviderError,
    UnsupportedProviderSymbolError,
    UnsupportedProviderTimeframeError,
    resolve_internal_symbol,
    resolve_timeframe,
)

_FORWARD_TIMEFRAME_DURATION: Mapping[Timeframe, timedelta] = MappingProxyType(
    {
        Timeframe.M1: timedelta(minutes=1),
        Timeframe.M5: timedelta(minutes=5),
        Timeframe.M15: timedelta(minutes=15),
    }
)

_VERSION = SemVer.parse("0.1.0")


class ForwardCandleRejection(Exception):
    """Raised when a provider row cannot become a canonical closed candle. The
    ``reason_code`` is a stable UPPER_SNAKE token the runner surfaces as a
    data-quality warning (the candle never reaches scanner semantics)."""

    def __init__(self, reason_code: str, message: str) -> None:
        super().__init__(message)
        self.reason_code = reason_code


def build_forward_closed_candle(
    row: ProviderCandle, *, ingestion_time_utc: datetime
) -> NormalizedCandle:
    """Build a canonical CLOSED ``NormalizedCandle`` from a provider row.

    Raises ``ForwardCandleRejection`` for forming bars, unsupported
    provider/symbol/timeframe, unsupported timeframe duration, or contract
    validation failure — never returns an incomplete candle."""
    if not row.is_closed:
        raise ForwardCandleRejection(
            "FORMING_CANDLE_REJECTED",
            "provider row is not a closed candle; refusing to feed scanner.",
        )
    try:
        symbol = resolve_internal_symbol(row.provider, row.source_symbol)
        timeframe = resolve_timeframe(row.provider, row.source_timeframe)
    except UnsupportedProviderError as exc:
        raise ForwardCandleRejection("UNSUPPORTED_PROVIDER", str(exc)) from exc
    except UnsupportedProviderSymbolError as exc:
        raise ForwardCandleRejection("UNSUPPORTED_PROVIDER_SYMBOL", str(exc)) from exc
    except UnsupportedProviderTimeframeError as exc:
        raise ForwardCandleRejection(
            "UNSUPPORTED_PROVIDER_TIMEFRAME", str(exc)
        ) from exc

    duration = _FORWARD_TIMEFRAME_DURATION.get(timeframe)
    if duration is None:
        raise ForwardCandleRejection(
            "TIMEFRAME_DURATION_UNSUPPORTED",
            f"forward pilot supports only M1/M5/M15; got {timeframe.value}.",
        )

    event_time = row.open_time_utc
    availability_time = event_time + duration
    volume_kind = (
        CandleVolumeKind.TICK if row.volume is not None else CandleVolumeKind.UNKNOWN
    )
    fingerprint = derive_forward_fingerprint(
        (
            row.provider,
            row.source_symbol,
            row.source_timeframe,
            event_time.isoformat(),
            _decimal_text(row.open),
            _decimal_text(row.high),
            _decimal_text(row.low),
            _decimal_text(row.close),
            _decimal_text(row.volume) if row.volume is not None else "None",
            CandleCompleteness.CONFIRMED_COMPLETE.value,
        )
    )
    identity_parts = (
        row.provider,
        row.source_symbol,
        row.source_timeframe,
        event_time.isoformat(),
    )
    source_reference = f"{row.provider.lower()}-{row.source_symbol.lower()}-forward"
    try:
        return NormalizedCandle(
            record_id=derive_forward_uuid("normalized", identity_parts),
            content_fingerprint=fingerprint,
            raw_candle_id=derive_forward_uuid("raw", identity_parts),
            provider=row.provider,
            source_reference=source_reference,
            source_symbol=row.source_symbol,
            source_timeframe=row.source_timeframe,
            symbol=symbol,
            timeframe=timeframe,
            event_time_utc=event_time,
            availability_time_utc=availability_time,
            processing_time_utc=ingestion_time_utc,
            original_event_time=event_time,
            original_availability_time=availability_time,
            original_timezone="UTC",
            open=row.open,
            high=row.high,
            low=row.low,
            close=row.close,
            volume=row.volume,
            volume_kind=volume_kind,
            completeness=CandleCompleteness.CONFIRMED_COMPLETE,
            rule_version=_VERSION,
            contract_version=_VERSION,
            schema_version=_VERSION,
            provenance_id=derive_forward_uuid("provenance", identity_parts),
        )
    except ValidationError as exc:
        raise ForwardCandleRejection(
            "NORMALIZED_CANDLE_VALIDATION_FAILED", str(exc)
        ) from exc


def _decimal_text(value: Decimal) -> str:
    return format(value.normalize(), "f")
