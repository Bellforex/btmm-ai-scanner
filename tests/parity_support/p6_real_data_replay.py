"""Blind Python replay of a digest-locked P6 capture.

Test/parity tooling only — nothing in `src/` imports this, and it changes no
production semantics.

WHY THIS IS "BLIND"
-------------------
The Pine surface digests exist in the same capture file as the raw candles, so it
would be trivially easy to write a replay that "agreed" with them. Nothing here
reads them. `replay_capture` takes ONLY the parsed raw candles, runs the
production oracle, and folds the result through the frozen digest contract. The
comparison against Pine is a separate step performed by the caller, on values
this module never saw.

That separation is the whole point. A replay that could see the target would
prove nothing about the port, and any later mismatch would be un-diagnosable
because the two sides would no longer be independent.

WHAT IT RECONSTRUCTS
--------------------
The capture stores prices as TICK INTEGERS, exactly as the Pine folded them, so
the reconstruction multiplies by the instrument tick rather than re-parsing a
decimal string. That keeps the two runtimes free of a float round-trip: the
integers Pine hashed are the integers Python hashes.

Each timeframe is replayed over its OWN captured history, whose length the
snapshot dictates — 1250 confirmed bars for the five requested contexts and the
host's full confirmed count for M15. The oracle then runs one continuous Wilder
recurrence over exactly those bars, which is what makes the ATR series match the
one Pine advanced incrementally.
"""

from __future__ import annotations

import importlib.util
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any
from uuid import UUID

_REPO = Path(__file__).resolve().parents[2]


def _load(name: str, relpath: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, _REPO / relpath)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


ORACLE = _load("_p6_replay_oracle", "tests/parity_support/p6_projection_oracle.py")
DIG = _load("_p6_replay_digest", "tests/parity_support/p6_digest.py")

from btmm_ai_scanner.config.enums import InternalSymbol, Timeframe  # noqa: E402
from btmm_ai_scanner.contracts.normalized_candle import NormalizedCandle  # noqa: E402
from btmm_ai_scanner.contracts.raw_candle import (  # noqa: E402
    CandleCompleteness,
    CandleVolumeKind,
)
from btmm_ai_scanner.contracts.types import SemVer  # noqa: E402

#: Capture timeframe label -> production timeframe.
TIMEFRAME = {
    "W1": Timeframe.W1,
    "D1": Timeframe.D1,
    "H4": Timeframe.H4,
    "H1": Timeframe.H1,
    "M15": Timeframe.M15,
    "M5": Timeframe.M5,
}

_FP = "c" * 64
_PROV = UUID("0193f6c0-0000-7abc-8def-abcdefabcd60")
_RAW = UUID("0193f6c0-0000-7abc-8def-abcdefabcd61")


def _moment(ms: int) -> datetime:
    return datetime.fromtimestamp(ms / 1000, tz=UTC)


def build_candles(
    timeframe: str,
    bars: tuple[dict[str, Any], ...],
    *,
    mintick: Decimal = DIG.MINTICK,
) -> tuple[NormalizedCandle, ...]:
    """Reconstruct production candles from captured tick integers."""
    out: list[NormalizedCandle] = []
    for bar in bars:
        event = _moment(bar["time_ms"])
        avail = _moment(bar["time_close_ms"])
        out.append(
            NormalizedCandle.model_validate(
                {
                    "record_id": UUID(f"0193f6c1-0000-7abc-8def-{bar['ordinal']:012x}"),
                    "content_fingerprint": _FP,
                    "raw_candle_id": _RAW,
                    "provider": "FXCM",
                    "source_reference": "fxcm",
                    "source_symbol": "XAUUSD",
                    "source_timeframe": TIMEFRAME[timeframe].value,
                    "symbol": InternalSymbol.XAUUSD,
                    "timeframe": TIMEFRAME[timeframe],
                    "event_time_utc": event,
                    "availability_time_utc": avail,
                    "processing_time_utc": avail,
                    "original_event_time": event,
                    "original_availability_time": avail,
                    "original_timezone": "UTC",
                    "open": Decimal(bar["open_ticks"]) * mintick,
                    "high": Decimal(bar["high_ticks"]) * mintick,
                    "low": Decimal(bar["low_ticks"]) * mintick,
                    "close": Decimal(bar["close_ticks"]) * mintick,
                    "volume": None,
                    "volume_kind": CandleVolumeKind.UNKNOWN,
                    "completeness": CandleCompleteness.CONFIRMED_COMPLETE,
                    "rule_version": SemVer.parse("0.1.0"),
                    "contract_version": SemVer.parse("0.1.0"),
                    "schema_version": SemVer.parse("0.1.0"),
                    "provenance_id": _PROV,
                }
            )
        )
    return tuple(out)


@dataclass(frozen=True)
class TimeframeReplay:
    timeframe: str
    rows: int
    values: dict[str, Any]
    surfaces: dict[str, tuple[int, int]]
    combined: tuple[int, int]


def replay_timeframe(
    timeframe: str,
    bars: tuple[dict[str, Any], ...],
    *,
    mintick: Decimal = DIG.MINTICK,
) -> TimeframeReplay:
    """Production oracle over one timeframe's captured history. Sees no Pine
    value of any kind."""
    candles = build_candles(timeframe, bars, mintick=mintick)
    projection = ORACLE.project_series(candles, terminals=1, mintick=mintick)[0]
    fields = dict(projection.compare_values())
    return TimeframeReplay(
        timeframe=timeframe,
        rows=len(candles),
        values=fields,
        surfaces=DIG.surface_digests(fields, mintick=mintick),
        combined=DIG.timeframe_digest(timeframe, fields, mintick=mintick),
    )


def replay_capture(
    raw_by_timeframe: dict[str, Any],
    *,
    mintick: Decimal = DIG.MINTICK,
) -> dict[str, TimeframeReplay]:
    """Replay every captured timeframe. Deterministic and Pine-blind."""
    return {
        timeframe: replay_timeframe(timeframe, capture.bars, mintick=mintick)
        for timeframe, capture in raw_by_timeframe.items()
    }
