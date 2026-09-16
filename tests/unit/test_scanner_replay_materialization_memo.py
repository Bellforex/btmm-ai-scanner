"""The finalize-time materialization memo is exact.

``IncrementalReplayKernel.finalize`` reuses a timeframe's materialized
measurement / structure / POI analysis when that timeframe's immutable replay
state object is unchanged since the previous finalize. These tests feed two
kernels identical groups -- one with the memo, one forced to rebuild every
time -- and require equal analyses at every step, and they prove the memo is
actually hit for an idle timeframe.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any

from btmm_ai_scanner.config.enums import Timeframe
from btmm_ai_scanner.contracts.normalized_candle import NormalizedCandle
from btmm_ai_scanner.historical_backtest.identity import (
    ContentAddressedIdentityProvider,
)
from btmm_ai_scanner.scanner.replay import IncrementalReplayKernel
from tests.parity_support.level_a_replay import build_scanner_configuration
from tests.parity_support.v1a_csv_loader import load_v1a_csv

_START = datetime(2026, 8, 10, 0, 0, tzinfo=UTC)


def _write(path: Path, rows: list[tuple[datetime, float, float, float, float]]) -> None:
    lines = ["time,open,high,low,close,volume"]
    for t, o, h, lo, c in rows:
        lines.append(
            f"{int(t.timestamp() * 1000)},{o:.2f},{h:.2f},{lo:.2f},{c:.2f},100"
        )
    path.write_text("\n".join(lines), encoding="utf-8")


def _series(
    tmp_path: Path,
) -> tuple[tuple[NormalizedCandle, ...], tuple[NormalizedCandle, ...]]:
    m15: list[tuple[datetime, float, float, float, float]] = []
    price = 100.0
    for i in range(160):
        step = 1.5 if (i // 12) % 2 == 0 else -1.3
        if i % 23 == 7:
            step *= 4  # displacement bars so real POIs appear
        o, c = price, price + step
        m15.append(
            (_START + timedelta(minutes=15 * i), o, max(o, c) + 0.3, min(o, c) - 0.3, c)
        )
        price = c
    h1 = []
    for k in range(0, len(m15) - 3, 4):
        chunk = m15[k : k + 4]
        h1.append(
            (
                chunk[0][0],
                chunk[0][1],
                max(r[2] for r in chunk),
                min(r[3] for r in chunk),
                chunk[-1][4],
            )
        )
    _write(tmp_path / "m15.csv", m15)
    _write(tmp_path / "h1.csv", h1)
    return load_v1a_csv(tmp_path / "m15.csv", Timeframe.M15), load_v1a_csv(
        tmp_path / "h1.csv", Timeframe.H1
    )


def _kernel() -> IncrementalReplayKernel:
    configuration = build_scanner_configuration(
        required_timeframes=frozenset({Timeframe.M15}),
        optional_timeframes=frozenset({Timeframe.H1}),
        minimum_price_tick=Decimal("0.01"),
    )
    return IncrementalReplayKernel(
        (Timeframe.H1, Timeframe.M15),
        configuration,
        ContentAddressedIdentityProvider(),
        (),
    )


def test_memoized_finalize_equals_rebuild_every_time(tmp_path: Path) -> None:
    m15, h1 = _series(tmp_path)
    memo = _kernel()
    rebuild = _kernel()

    def _always_build(kind: str, tf: Timeframe, state: object, build: Any) -> Any:
        return build(state)

    rebuild._materialize_once = _always_build  # type: ignore[method-assign]

    h1_by_close = {c.availability_time_utc: c for c in h1}
    hits: dict[str, int] = {}
    original = memo._materialize_once

    def _counting(kind: str, tf: Timeframe, state: object, build: Any) -> Any:
        cached = memo._materialized.get((kind, tf))
        if cached is not None and cached[0] is state and tf is Timeframe.H1:
            hits[kind] = hits.get(kind, 0) + 1
        return original(kind, tf, state, build)

    memo._materialize_once = _counting  # type: ignore[method-assign]
    for candle in m15:
        group: dict[Timeframe, tuple[NormalizedCandle, ...]] = {
            Timeframe.M15: (candle,)
        }
        if candle.availability_time_utc in h1_by_close:
            group[Timeframe.H1] = (h1_by_close[candle.availability_time_utc],)
        memo.advance_group(group)
        rebuild.advance_group(group)
        assert memo.finalize() == rebuild.finalize(), candle.event_time_utc
    # H1 is idle on three of every four M15 bars: the memo must be used.
    for kind in ("measurement", "structure", "poi_final"):
        assert hits.get(kind, 0) > len(m15) // 2, (kind, hits)
