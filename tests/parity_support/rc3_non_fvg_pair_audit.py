"""RC3 non-FVG same-origin pair audit (author decision B, 2026-09-17).

Test/validation tooling only. For every pair of non-FVG candle-pattern types
that end on the same candle in the same direction (unsealed FXCM, raw detector
outputs), counts co-occurrences, identical zones, zone containment and how often
the first type occurs WITHOUT the second (a strict specialization A => B has
zero). Order blocks and S/R zones are not candle-pattern origins.

    python -m tests.parity_support.rc3_non_fvg_pair_audit [base_dir]
"""

from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from decimal import Decimal
from itertools import combinations
from pathlib import Path
from typing import Any

from btmm_ai_scanner.config.enums import Timeframe
from btmm_ai_scanner.poi.configuration import PoiConfiguration
from btmm_ai_scanner.poi.enums import PoiType
from btmm_ai_scanner.poi.qualification import origin_key

__all__ = ["pair_counts"]

_EXCLUDED = frozenset(
    {
        PoiType.BUY_ORDER_BLOCK,
        PoiType.SELL_ORDER_BLOCK,
        PoiType.BUY_FAIR_VALUE_GAP,
        PoiType.SELL_FAIR_VALUE_GAP,
    }
)


def pair_counts(candidates: list[Any]) -> dict[str, Counter[str]]:
    groups: dict[Any, list[Any]] = defaultdict(list)
    types = Counter()
    for c in candidates:
        if c.poi_type in _EXCLUDED:
            continue
        groups[origin_key(c)].append(c)
        types[c.poi_type.value] += 1
    both: Counter[str] = Counter()
    same_zone: Counter[str] = Counter()
    a_in_b: Counter[str] = Counter()
    b_in_a: Counter[str] = Counter()
    for items in groups.values():
        for a, b in combinations(sorted(items, key=lambda c: c.poi_type.value), 2):
            if a.poi_type is b.poi_type:
                continue
            key = f"{a.poi_type.value}+{b.poi_type.value}"
            both[key] += 1
            if (a.zone_bottom, a.zone_top) == (b.zone_bottom, b.zone_top):
                same_zone[key] += 1
            if b.zone_bottom <= a.zone_bottom and a.zone_top <= b.zone_top:
                a_in_b[key] += 1
            if a.zone_bottom <= b.zone_bottom and b.zone_top <= a.zone_top:
                b_in_a[key] += 1
    return {
        "types": types,
        "both": both,
        "same_zone": same_zone,
        "a_in_b": a_in_b,
        "b_in_a": b_in_a,
    }


def main() -> int:  # pragma: no cover - manual measurement
    from tests.parity_support.rc3_poi_overlap_audit import (
        _DETECTORS,
        load_unsealed_segments,
    )

    repo = Path(__file__).resolve().parents[2]
    base = (
        Path(sys.argv[1])
        if len(sys.argv) > 1
        else repo / "artifacts" / "rc3_qual_aligned_v12"
    )
    out = repo / "artifacts" / "rc3_non_fvg_pairs"
    out.mkdir(parents=True, exist_ok=True)
    pconfig = PoiConfiguration(minimum_price_tick=Decimal("0.01"))
    report: dict[str, Any] = {}
    for stem, tf in (
        ("d1", Timeframe.D1), ("h4", Timeframe.H4), ("h1", Timeframe.H1),
        ("m15", Timeframe.M15), ("m5", Timeframe.M5),
    ):  # fmt: skip
        total: dict[str, Counter[str]] = {}
        for seg in load_unsealed_segments(
            base / f"ohlc_{stem}.csv", tf, out / "_n" / f"{stem}.csv"
        ):
            raw = [c for _n, det in _DETECTORS for c in det(seg, pconfig)]
            for k, v in pair_counts(raw).items():
                total[k] = total.get(k, Counter()) + v
        report[tf.value] = {k: dict(v) for k, v in total.items()}
        print(tf.value, json.dumps(dict(total["both"])), flush=True)
    (out / "non_fvg_pairs.json").write_text(json.dumps(report, indent=1), "utf-8")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
