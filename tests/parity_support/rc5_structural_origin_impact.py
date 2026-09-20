"""RC5 STRUCTURAL-ORIGIN-ONLY IMPACT.

Measures what the structural-origin gate alone does to a bounded real-data
window: how many reversal candidates it refuses as mid-leg texture, how many it
merely delays, and how far. It does NOT include same-origin authority
arbitration, DOJI, qualified sweeps or any other RC5 work -- those change the
numbers again and must be measured separately.

Both profiles run the SAME frozen bars through the SAME engine; only
``rc5_structural_origin`` differs. Everything reported is a difference between
those two runs, so no number here depends on a detector change.

Usage::

    python -m tests.parity_support.rc5_structural_origin_impact \\
        --ohlc artifacts/rc4_aligned_v2/ohlc_m15.csv --timeframe M15
"""

from __future__ import annotations

import argparse
import json
import statistics
from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path
from typing import Any

from btmm_ai_scanner.config.enums import Timeframe
from btmm_ai_scanner.domain.analyzer import analyze_market_measurements
from btmm_ai_scanner.domain.configuration import MarketMeasurementConfiguration
from btmm_ai_scanner.historical_backtest.identity import (
    ContentAddressedIdentityProvider,
)
from btmm_ai_scanner.poi.analyzer import PoiTimeframeInput, analyze_pois
from btmm_ai_scanner.poi.authority import REVERSAL_TYPES
from btmm_ai_scanner.poi.configuration import PoiConfiguration
from btmm_ai_scanner.poi.enums import PoiType
from tests.parity_support.v1a_csv_loader import load_v1a_csv

_TICK = Decimal("0.01")

#: Report groups, in the order the author asked for them.
_FAMILIES: tuple[tuple[str, frozenset[PoiType]], ...] = (
    ("B2S/S2B", frozenset({PoiType.BUY_TO_SELL_CANDLE, PoiType.SELL_TO_BUY_CANDLE})),
    ("ORDER BLOCK", frozenset({PoiType.BUY_ORDER_BLOCK, PoiType.SELL_ORDER_BLOCK})),
    ("STARS", frozenset({PoiType.MORNING_STAR, PoiType.EVENING_STAR})),
    ("ENGULFING", frozenset({PoiType.BULLISH_ENGULFING, PoiType.BEARISH_ENGULFING})),
    ("HAMMER/SHOOTING", frozenset({PoiType.HAMMER, PoiType.SHOOTING_STAR})),
    (
        "PRESSURE WICK",
        frozenset({PoiType.BULLISH_PRESSURE_WICK, PoiType.BEARISH_PRESSURE_WICK}),
    ),
    ("DOJI", frozenset({PoiType.DOJI})),
)


@dataclass
class FamilyImpact:
    rc4: int = 0
    rc5: int = 0
    refused: int = 0
    delayed: int = 0
    delay_bars: list[int] = field(default_factory=list)
    delay_seconds: list[float] = field(default_factory=list)


def _run(candles: tuple[Any, ...], timeframe: Timeframe, *, rc5: bool) -> Any:
    identity = ContentAddressedIdentityProvider()
    measurement = analyze_market_measurements(
        candles, MarketMeasurementConfiguration(minimum_price_tick=_TICK), identity
    )
    return analyze_pois(
        (PoiTimeframeInput(timeframe, candles, measurement),),
        PoiConfiguration(minimum_price_tick=_TICK, rc5_structural_origin=rc5),
        identity,
    )


def measure(candles: tuple[Any, ...], timeframe: Timeframe) -> dict[str, Any]:
    bar_of = {c.availability_time_utc: i for i, c in enumerate(candles)}

    def key(observation: Any) -> tuple[Any, ...]:
        return (observation.poi_type, observation.source_candle_record_ids)

    rc4 = {key(o): o for o in _run(candles, timeframe, rc5=False).poi_observations}
    rc5 = {key(o): o for o in _run(candles, timeframe, rc5=True).poi_observations}

    by_family: dict[str, FamilyImpact] = {name: FamilyImpact() for name, _ in _FAMILIES}
    by_type: dict[str, dict[str, int]] = {}
    reversal_rc4 = reversal_rc5 = 0

    def family_of(poi_type: PoiType) -> str | None:
        for name, members in _FAMILIES:
            if poi_type in members:
                return name
        return None

    for k, before in rc4.items():
        poi_type = k[0]
        if poi_type not in REVERSAL_TYPES:
            continue
        reversal_rc4 += 1
        name = family_of(poi_type)
        impact = by_family[name] if name else FamilyImpact()
        impact.rc4 += 1
        row = by_type.setdefault(
            poi_type.value, {"rc4": 0, "rc5": 0, "refused": 0, "delayed": 0}
        )
        row["rc4"] += 1
        after = rc5.get(k)
        if after is None:
            impact.refused += 1
            row["refused"] += 1
            continue
        reversal_rc5 += 1
        impact.rc5 += 1
        row["rc5"] += 1
        if after.availability_time_utc > before.availability_time_utc:
            impact.delayed += 1
            row["delayed"] += 1
            delta = (
                after.availability_time_utc - before.availability_time_utc
            ).total_seconds()
            impact.delay_seconds.append(delta)
            a = bar_of.get(after.availability_time_utc)
            b = bar_of.get(before.availability_time_utc)
            if a is not None and b is not None:
                impact.delay_bars.append(a - b)

    non_reversal_delta = sorted(
        {k[0].value for k in set(rc4) - set(rc5) if k[0] not in REVERSAL_TYPES}
    )
    invented = sorted({k[0].value for k in set(rc5) - set(rc4)})

    all_bars = [b for i in by_family.values() for b in i.delay_bars]
    all_seconds = [s for i in by_family.values() for s in i.delay_seconds]

    return {
        "timeframe": timeframe.value,
        "bars": len(candles),
        "window_start_utc": candles[0].event_time_utc.isoformat(),
        "window_end_utc": candles[-1].event_time_utc.isoformat(),
        "poi_total_rc4": len(rc4),
        "poi_total_rc5": len(rc5),
        "reversal_rc4": reversal_rc4,
        "reversal_rc5": reversal_rc5,
        "refused_mid_leg": reversal_rc4 - reversal_rc5,
        "delayed": sum(i.delayed for i in by_family.values()),
        "delay_bars_median": (statistics.median(all_bars) if all_bars else None),
        "delay_bars_max": max(all_bars) if all_bars else None,
        "delay_hours_median": (
            round(statistics.median(all_seconds) / 3600, 3) if all_seconds else None
        ),
        "delay_hours_max": (round(max(all_seconds) / 3600, 3) if all_seconds else None),
        "by_family": {
            name: {
                "rc4": i.rc4,
                "rc5": i.rc5,
                "refused": i.refused,
                "delayed": i.delayed,
                "delay_bars_median": (
                    statistics.median(i.delay_bars) if i.delay_bars else None
                ),
                "delay_bars_max": max(i.delay_bars) if i.delay_bars else None,
            }
            for name, i in by_family.items()
            if i.rc4
        },
        "by_type": dict(sorted(by_type.items())),
        #: These MUST both be empty. The gate may only remove or delay reversal
        #: families, and may never create a POI.
        "non_reversal_families_removed": non_reversal_delta,
        "families_invented": invented,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ohlc", type=Path, required=True)
    parser.add_argument("--timeframe", required=True)
    parser.add_argument("--bars", type=int, default=0, help="tail bars; 0 = all")
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()

    timeframe = Timeframe(args.timeframe)
    candles = load_v1a_csv(args.ohlc, timeframe)
    if args.bars:
        candles = candles[-args.bars :]
    report = measure(candles, timeframe)
    report["source"] = str(args.ohlc)
    text = json.dumps(report, indent=2)
    if args.out:
        args.out.write_text(text, encoding="utf-8")
    print(text)
    print(
        "\nFAMILY                 RC4   RC5  REFUSED  DELAYED  MED_BARS  MAX_BARS",
    )
    for name, row in report["by_family"].items():
        print(
            f"{name:<20} {row['rc4']:>5} {row['rc5']:>5} {row['refused']:>8}"
            f" {row['delayed']:>8} {row['delay_bars_median']!s:>9}"
            f" {row['delay_bars_max']!s:>9}"
        )
    assert not report["families_invented"], report["families_invented"]
    assert not report["non_reversal_families_removed"], report[
        "non_reversal_families_removed"
    ]


if __name__ == "__main__":
    main()


__all__ = ["FamilyImpact", "measure"]
