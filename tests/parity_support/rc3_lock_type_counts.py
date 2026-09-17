"""P3 type counts on the same-session FXCM exports for a semantic-lock delta.

Test/validation tooling only. Runs the batch engine of whichever code tree is
on ``sys.path`` (so the same script measures an older commit from a worktree)
over every unsealed segment of each timeframe export and prints JSON counts of
ORDER BLOCK / ENGULFING records. Sealed bars are never loaded
(``load_unsealed_segments``).

    python -m tests.parity_support.rc3_lock_type_counts <data_root> <out.json>
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from decimal import Decimal
from pathlib import Path

from btmm_ai_scanner.config.enums import Timeframe
from btmm_ai_scanner.domain.analyzer import analyze_market_measurements
from btmm_ai_scanner.domain.configuration import MarketMeasurementConfiguration
from btmm_ai_scanner.historical_backtest.identity import (
    ContentAddressedIdentityProvider,
)
from btmm_ai_scanner.poi.analyzer import PoiTimeframeInput, analyze_pois
from btmm_ai_scanner.poi.configuration import PoiConfiguration
from tests.parity_support.rc3_poi_overlap_audit import load_unsealed_segments

_TYPES = ("BUY_ORDER_BLOCK", "SELL_ORDER_BLOCK", "BULLISH_ENGULFING", "BEARISH_ENGULFING")
_STEMS = (
    ("w1", Timeframe.W1),
    ("d1", Timeframe.D1),
    ("h4", Timeframe.H4),
    ("h1", Timeframe.H1),
    ("m15", Timeframe.M15),
    ("m5", Timeframe.M5),
)


def main() -> int:  # pragma: no cover - manual measurement
    data_root, out = Path(sys.argv[1]), Path(sys.argv[2])
    report: dict[str, dict[str, int]] = {}
    for stem, tf in _STEMS:
        counts: Counter[str] = Counter()
        for segment in load_unsealed_segments(
            data_root / "rc3_aligned" / f"ohlc_{stem}.csv",
            tf,
            out.parent / "_n" / f"{stem}.csv",
        ):
            identity = ContentAddressedIdentityProvider()
            measurement = analyze_market_measurements(
                segment,
                MarketMeasurementConfiguration(minimum_price_tick=Decimal("0.01")),
                identity,
            )
            pois = analyze_pois(
                (PoiTimeframeInput(tf, segment, measurement),),
                PoiConfiguration(minimum_price_tick=Decimal("0.01")),
                identity,
            )
            counts.update(
                o.poi_type.value
                for o in pois.poi_observations
                if o.poi_type.value in _TYPES
            )
        report[tf.value] = {t: counts[t] for t in _TYPES}
        print(tf.value, report[tf.value], flush=True)
    out.write_text(json.dumps(report, indent=1) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
