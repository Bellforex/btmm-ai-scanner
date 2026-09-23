"""Shared loaders for the real FXCM captures the arrival tests reason over.

Kept out of a test module so both the arrival tests and the A/B size tests can
build the same candles from the same bytes.
"""

from __future__ import annotations

import csv
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from uuid import UUID

from btmm_ai_scanner.config.enums import InternalSymbol, Timeframe
from btmm_ai_scanner.contracts.normalized_candle import NormalizedCandle
from btmm_ai_scanner.contracts.raw_candle import CandleCompleteness, CandleVolumeKind
from btmm_ai_scanner.domain.configuration import MarketMeasurementConfiguration
from btmm_ai_scanner.domain.swings import detect_confirmed_swings
from btmm_ai_scanner.poi.leg_origin import (
    _STRUCTURE_CONFIGURATION,
    _as_swing,
    structure_direction_timeline,
)
from btmm_ai_scanner.structure.relationships import detect_swing_relationships
from btmm_ai_scanner.structure.transitions import run_structure_walk

_ARTIFACTS = Path(__file__).resolve().parents[2] / "artifacts"

#: The author's M15 forensic capture (FX:EURUSD, 300 bars).
M15_CSV = _ARTIFACTS / "rc5_m15_screenshot_capture" / "rc5_ohlc_m15_eurusd.csv"
#: The RC5 host captures (XAUUSD).
M45_CSV = _ARTIFACTS / "rc5_host_capture" / "rc5_ohlc_m45.csv"
H3_CSV = _ARTIFACTS / "rc5_host_capture" / "rc5_ohlc_h3.csv"


def load_capture(
    path: Path,
    timeframe: Timeframe,
    minutes: int,
    symbol: InternalSymbol,
    quantum: str,
) -> tuple[NormalizedCandle, ...]:
    out: list[NormalizedCandle] = []
    with path.open(newline="", encoding="utf-8") as handle:
        for index, row in enumerate(csv.DictReader(handle)):
            event = datetime.fromtimestamp(int(row["time"]) / 1000, UTC)
            avail = event + timedelta(minutes=minutes)
            out.append(
                NormalizedCandle.model_validate(
                    {
                        "record_id": UUID(f"0193f450-1234-7abc-8def-{index:012x}"),
                        "content_fingerprint": "a" * 64,
                        "raw_candle_id": UUID("0193f450-1234-7abc-8def-abcdefabcdaa"),
                        "provider": "FXCM",
                        "source_reference": "fxcm-capture",
                        "source_symbol": symbol.value,
                        "source_timeframe": timeframe.value,
                        "symbol": symbol,
                        "timeframe": timeframe,
                        "event_time_utc": event,
                        "availability_time_utc": avail,
                        "processing_time_utc": avail,
                        "original_event_time": event,
                        "original_availability_time": avail,
                        "original_timezone": "UTC",
                        "open": Decimal(row["open"]).quantize(Decimal(quantum)),
                        "high": Decimal(row["high"]).quantize(Decimal(quantum)),
                        "low": Decimal(row["low"]).quantize(Decimal(quantum)),
                        "close": Decimal(row["close"]).quantize(Decimal(quantum)),
                        "volume": Decimal(row["volume"]),
                        "volume_kind": CandleVolumeKind.TICK,
                        "completeness": CandleCompleteness.CONFIRMED_COMPLETE,
                        "rule_version": "1.0.0",
                        "contract_version": "1.0.0",
                        "schema_version": "1.0.0",
                        "provenance_id": UUID("0193f450-1234-7abc-8def-abcdefabcdff"),
                    }
                )
            )
    return tuple(out)


def m15_eurusd() -> tuple[NormalizedCandle, ...]:
    return load_capture(M15_CSV, Timeframe.M15, 15, InternalSymbol.EURUSD, "0.00001")


def m45_xauusd() -> tuple[NormalizedCandle, ...]:
    # M45 is not in `Timeframe`; the bars are carried under an H3 label, which
    # is a disclosed labelling compromise and affects nothing these tests assert.
    return load_capture(M45_CSV, Timeframe.H3, 45, InternalSymbol.XAUUSD, "0.01")


def h3_xauusd() -> tuple[NormalizedCandle, ...]:
    return load_capture(H3_CSV, Timeframe.H3, 180, InternalSymbol.XAUUSD, "0.01")


def structure_of(
    candles: tuple[NormalizedCandle, ...],
    measurement: MarketMeasurementConfiguration,
):
    """The SAME producer the context gate runs: swings -> relationships -> walk."""
    swings = tuple(_as_swing(s) for s in detect_confirmed_swings(candles, measurement))
    relationships = detect_swing_relationships(swings, _STRUCTURE_CONFIGURATION)
    walk = run_structure_walk(tuple(candles), swings, relationships)
    return structure_direction_timeline(walk, relationships), walk
