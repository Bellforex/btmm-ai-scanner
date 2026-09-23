"""Build ``NormalizedCandle`` records directly from HTTP-supplied raw bars,
for the internal scanner service boundary (``service/app.py``).

Deliberately bypasses the existing ``SourceCandleInput`` -> ``RawCandle`` ->
``normalize_raw_candle()`` ingestion chain (``btmm_ai_scanner.market_data``),
which resolves a candle's symbol/timeframe through the FXCM-only provider
registry in ``market_data/source_mapping.py``. That chain is a frozen,
reviewed part of the historical-backtest ingestion pipeline and is
deliberately NOT extended or touched here (see
docs/BTMM_SCANNER_WEB_INTEGRATION.md in the Bell Academy Hub repository) —
the caller (Bell Academy Hub) already resolves whatever a real market-data
vendor calls a symbol/timeframe into THIS project's own
``InternalSymbol``/``Timeframe`` enum values before ever calling this
service, so there is nothing left for a provider registry to resolve here.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from btmm_ai_scanner.config.enums import InternalSymbol, Timeframe
from btmm_ai_scanner.contracts.normalized_candle import NormalizedCandle
from btmm_ai_scanner.contracts.raw_candle import CandleCompleteness, CandleVolumeKind
from btmm_ai_scanner.contracts.types import SemVer
from btmm_ai_scanner.service.identity import (
    canonical_json_bytes,
    content_fingerprint,
    deterministic_uuid,
)
from btmm_ai_scanner.service.schemas import RawBar

# Matches the analytical engine's own convention (e.g.
# ``correlation/engine.py``'s ``TopDownCorrelationDecision`` defaults) — this
# service layer is additive plumbing, not a new analytical rule set, so it
# stamps the same "0.1.0" baseline rather than inventing its own version
# lineage.
_RULE_VERSION = SemVer.parse("0.1.0")
_CONTRACT_VERSION = SemVer.parse("0.1.0")
_SCHEMA_VERSION = SemVer.parse("0.1.0")

# Fallback minimum price ticks, used only when Bell Academy Hub does not
# supply a tick size of its own for a request. Ordinary, widely known market
# quoting conventions (XAUUSD to the cent, EURUSD/GBPUSD to the 5th decimal
# "pip point", BTCUSD to the cent, AAPL to the cent) — this only controls
# how finely price is measured, never any analytical verdict. A bare
# dict[symbol] subscript at the one call site (app.py's
# _build_scanner_configuration) means every InternalSymbol member MUST have
# an entry here or that request crashes — this was the first thing Bell
# Academy Hub's Phase 2C audit had to fix when adding BTCUSD/AAPL.
DEFAULT_MINIMUM_PRICE_TICK: dict[InternalSymbol, Decimal] = {
    InternalSymbol.XAUUSD: Decimal("0.01"),
    InternalSymbol.EURUSD: Decimal("0.00001"),
    InternalSymbol.GBPUSD: Decimal("0.00001"),
    InternalSymbol.BTCUSD: Decimal("0.01"),
    InternalSymbol.AAPL: Decimal("0.01"),
}


def _bar_identity_seed(
    *,
    symbol: InternalSymbol,
    timeframe: Timeframe,
    provider: str,
    bar: RawBar,
) -> bytes:
    return canonical_json_bytes(
        {
            "symbol": symbol.value,
            "timeframe": timeframe.value,
            "provider": provider,
            "event_time_utc": bar.time.astimezone(UTC).isoformat(),
            "open": str(bar.open),
            "high": str(bar.high),
            "low": str(bar.low),
            "close": str(bar.close),
            "volume": str(bar.volume) if bar.volume is not None else None,
        }
    )


def build_normalized_candle(
    *,
    symbol: InternalSymbol,
    timeframe: Timeframe,
    bar: RawBar,
    provider: str,
) -> NormalizedCandle:
    """Construct one strictly-validated ``NormalizedCandle`` from a single
    already-CLOSED HTTP-supplied bar.

    Deterministic and idempotent: the exact same ``(symbol, timeframe,
    provider, bar)`` always produces the exact same
    ``record_id``/``raw_candle_id``/``provenance_id``/``content_fingerprint``
    — retrying the same analyze request reconstructs byte-identical
    candles, never new ones. ``record_id`` and ``raw_candle_id`` are
    deliberately derived with different discriminator suffixes so they can
    never collide (``NormalizedCandle`` requires them to differ).
    """
    seed = _bar_identity_seed(symbol=symbol, timeframe=timeframe, provider=provider, bar=bar)
    raw_candle_id = deterministic_uuid(seed + b":raw_candle")
    record_id = deterministic_uuid(seed + b":normalized_record")
    provenance_id = deterministic_uuid(seed + b":provenance")
    fingerprint = content_fingerprint(seed)

    event_time_utc = bar.time.astimezone(UTC)
    processing_time_utc = datetime.now(UTC)
    # `availability_time_utc` must be strictly later than `event_time_utc`
    # (NormalizedCandle's own cross-field validator). Stamping the real
    # processing instant satisfies that for any historical bar, and also
    # satisfies CONFIRMED_COMPLETE's `processing_time_utc >=
    # availability_time_utc` requirement — this service only ever accepts
    # already-closed candles (see RawBar's docstring).
    availability_time_utc = processing_time_utc
    volume_kind = (
        CandleVolumeKind.TICK if bar.volume is not None else CandleVolumeKind.UNKNOWN
    )

    return NormalizedCandle(
        record_id=record_id,
        content_fingerprint=fingerprint,
        raw_candle_id=raw_candle_id,
        provider=provider,
        source_reference=(
            f"{provider}:{symbol.value}:{timeframe.value}:{event_time_utc.isoformat()}"
        ),
        source_symbol=symbol.value,
        source_timeframe=timeframe.value,
        symbol=symbol,
        timeframe=timeframe,
        event_time_utc=event_time_utc,
        availability_time_utc=availability_time_utc,
        processing_time_utc=processing_time_utc,
        original_event_time=bar.time,
        original_availability_time=availability_time_utc,
        original_timezone=str(bar.time.tzinfo),
        open=bar.open,
        high=bar.high,
        low=bar.low,
        close=bar.close,
        volume=bar.volume,
        volume_kind=volume_kind,
        completeness=CandleCompleteness.CONFIRMED_COMPLETE,
        rule_version=_RULE_VERSION,
        contract_version=_CONTRACT_VERSION,
        schema_version=_SCHEMA_VERSION,
        provenance_id=provenance_id,
    )
