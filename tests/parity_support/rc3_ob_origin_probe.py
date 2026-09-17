"""Measure candidate ORDER BLOCK movement-origin rules on real FXCM exports.

Test/validation tooling only -- no scanner semantics are changed here. Every
candidate rule is built from the frozen swing primitive
(`domain/swings.py`) and evaluated strictly prefix by prefix, so a
classification at bar `p` only ever uses candles `0..p`.

Formation: the frozen OB detector's pair (origin = d-1, displacement = d).

Rule L (local pivot): the opposite-type raw single-candle pivot of the swing
window (radius 2, wick extreme, ATR tie tolerance) sits on the origin or the
displacement candle. Known at close of d+1 (pivot at d-1) or d+2 (pivot at d).

Rule M (meaningful swing): a meaningfully confirmed opposite-type swing whose
pivot span covers d-1 or d appears in the prefix swing list. Availability =
the first prefix in which it appears. Later disappearance is counted as a
supersession (repaint risk).
"""

from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any

from btmm_ai_scanner.config.enums import Timeframe
from btmm_ai_scanner.contracts.normalized_candle import NormalizedCandle
from btmm_ai_scanner.domain.configuration import MarketMeasurementConfiguration
from btmm_ai_scanner.domain.enums import SwingType
from btmm_ai_scanner.domain.swings import (
    _find_single_candle_pivots,
    detect_confirmed_swings,
)
from btmm_ai_scanner.measurements.atr import compute_atr_series
from btmm_ai_scanner.poi.configuration import PoiConfiguration
from btmm_ai_scanner.poi.order_blocks import detect_order_blocks
from tests.parity_support.rc3_poi_overlap_audit import load_unsealed_segments

__all__ = ["OriginVerdict", "probe_segment"]


@dataclass(frozen=True)
class OriginVerdict:
    direction: str
    origin_index: int
    displacement_index: int
    source_utc: str
    zone: tuple[str, str]
    local_index: int | None  # prefix index where rule L passes, else None
    meaningful_index: int | None  # first prefix where rule M passes
    meaningful_later_dropped: bool

    def as_dict(self) -> dict[str, Any]:
        return self.__dict__.copy()


def _local_pivot_prefix(
    candles: tuple[NormalizedCandle, ...],
    atr: list[Decimal | None],
    config: MarketMeasurementConfiguration,
    d: int,
    want: SwingType,
) -> int | None:
    best: int | None = None
    for pivot_at in (d - 1, d):
        known = pivot_at + 2
        if known >= len(candles) or pivot_at < 2:
            continue
        window = candles[: known + 1]
        pivots = _find_single_candle_pivots(window, atr[: known + 1], config)
        if any(
            p.swing_type == want
            and p.start_index == pivot_at
            and p.end_index == pivot_at
            for p in pivots
        ):
            best = known if best is None else min(best, known)
    return best


def probe_segment(
    candles: tuple[NormalizedCandle, ...],
    poi_config: PoiConfiguration,
    config: MarketMeasurementConfiguration,
    horizon: int = 40,
) -> list[OriginVerdict]:
    index_of = {c.record_id: i for i, c in enumerate(candles)}
    atr = list(compute_atr_series(candles, config.atr_period))
    obs = detect_order_blocks(candles, poi_config)
    prefix_swings: dict[int, set[tuple[str, int, int]]] = {}

    def swings_at(p: int) -> set[tuple[str, int, int]]:
        if p not in prefix_swings:
            found = detect_confirmed_swings(candles[: p + 1], config)
            prefix_swings[p] = {
                (
                    s.swing_type.value,
                    s.pivot_bar_index,
                    index_of[s.pivot_candle_record_ids[-1]],
                )
                for s in found
            }
        return prefix_swings[p]

    out: list[OriginVerdict] = []
    for ob in obs:
        o = index_of[ob.source_candle_record_ids[0]]
        d = index_of[ob.source_candle_record_ids[1]]
        bullish = ob.direction.value == "BULLISH"
        want = SwingType.SWING_LOW if bullish else SwingType.SWING_HIGH
        local = _local_pivot_prefix(candles, atr, config, d, want)
        meaningful: int | None = None
        key: tuple[str, int, int] | None = None
        for p in range(d, min(len(candles), d + horizon + 1)):
            hits = [
                s
                for s in swings_at(p)
                if s[0] == want.value and s[1] <= d and s[2] >= o
            ]
            if hits:
                meaningful, key = p, hits[0]
                break
        dropped = False
        if key is not None and meaningful is not None:
            for p in range(meaningful + 1, min(len(candles), meaningful + horizon + 1)):
                if key not in swings_at(p):
                    dropped = True
                    break
        out.append(
            OriginVerdict(
                direction=ob.direction.value,
                origin_index=o,
                displacement_index=d,
                source_utc=ob.candidate_event_time_utc.isoformat(),
                zone=(str(ob.zone_bottom), str(ob.zone_top)),
                local_index=local,
                meaningful_index=meaningful,
                meaningful_later_dropped=dropped,
            )
        )
    return out


def main() -> int:  # pragma: no cover - manual measurement
    repo = Path(__file__).resolve().parents[2]
    base = repo / "artifacts" / "rc3_aligned"
    out_dir = repo / "artifacts" / "rc3_ob_origin"
    out_dir.mkdir(parents=True, exist_ok=True)
    poi_config = PoiConfiguration(minimum_price_tick=Decimal("0.01"))
    config = MarketMeasurementConfiguration(minimum_price_tick=Decimal("0.01"))
    report: dict[str, Any] = {}
    for stem, tf in (
        ("h4", Timeframe.H4),
        ("h1", Timeframe.H1),
        ("m15", Timeframe.M15),
        ("d1", Timeframe.D1),
    ):
        verdicts: list[OriginVerdict] = []
        for seg in load_unsealed_segments(
            base / f"ohlc_{stem}.csv", tf, out_dir / "_n" / f"{stem}.csv"
        ):
            verdicts.extend(probe_segment(seg, poi_config, config))
        by_dir = Counter(v.direction for v in verdicts)
        loc = [v for v in verdicts if v.local_index is not None]
        mea = [v for v in verdicts if v.meaningful_index is not None]
        report[tf.value] = {
            "order_blocks": dict(by_dir),
            "rule_L_kept": dict(Counter(v.direction for v in loc)),
            "rule_L_delay_bars": dict(
                Counter(v.local_index - v.displacement_index for v in loc)
            ),
            "rule_M_kept": dict(Counter(v.direction for v in mea)),
            "rule_M_delay_bars": dict(
                Counter(v.meaningful_index - v.displacement_index for v in mea)
            ),
            "rule_M_later_dropped": sum(v.meaningful_later_dropped for v in mea),
            "L_and_M": sum(
                1
                for v in verdicts
                if v.local_index is not None and v.meaningful_index is not None
            ),
            "L_only": sum(
                1
                for v in verdicts
                if v.local_index is not None and v.meaningful_index is None
            ),
            "M_only": sum(
                1
                for v in verdicts
                if v.local_index is None and v.meaningful_index is not None
            ),
            "verdicts": [v.as_dict() for v in verdicts],
        }
        print(tf.value, {k: v for k, v in report[tf.value].items() if k != "verdicts"})
    (out_dir / "origin_probe.json").write_text(
        json.dumps(report, indent=1), encoding="utf-8"
    )
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
