"""RC3 structural context gate audit (author decision A, 2026-09-17).

Test/validation tooling only. Per timeframe (unsealed FXCM segments):

* direction segments of the frozen P2 walk (bootstrap + every BOS / CHOCH) with
  the context reasons of the candle patterns that became available inside each;
* before / after mapped counts per type: BEFORE = the qualified engine at
  ``be9bae1`` (quality + same-origin arbitration, no context gate), AFTER = the
  context-gated engine.

    python -m tests.parity_support.rc3_context_gate_audit [base_dir]
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from decimal import Decimal
from pathlib import Path
from typing import Any

from btmm_ai_scanner.config.enums import Timeframe
from btmm_ai_scanner.domain.analyzer import analyze_market_measurements
from btmm_ai_scanner.domain.configuration import MarketMeasurementConfiguration
from btmm_ai_scanner.historical_backtest.identity import (
    ContentAddressedIdentityProvider,
)
from btmm_ai_scanner.poi.leg_origin import (
    ContextReason,
    _direction_timeline,
    structure_context_decisions,
)
from btmm_ai_scanner.structure.configuration import StructureConfiguration
from btmm_ai_scanner.structure.relationships import detect_swing_relationships
from btmm_ai_scanner.structure.transitions import run_structure_walk
from tests.parity_support.rc3_qualification_coverage import coverage

__all__ = ["direction_segments"]

_MCONFIG = MarketMeasurementConfiguration(minimum_price_tick=Decimal("0.01"))


def direction_segments(segment, qualified) -> list[dict[str, Any]]:
    m = analyze_market_measurements(
        segment, _MCONFIG, ContentAddressedIdentityProvider()
    )
    swings = m.confirmed_swings
    walk = run_structure_walk(
        segment, swings, detect_swing_relationships(swings, StructureConfiguration())
    )
    times, dirs = _direction_timeline(
        walk, detect_swing_relationships(swings, StructureConfiguration())
    )
    decisions = structure_context_decisions(qualified, segment, swings)
    kinds = {t.availability_time_utc: t.transition_type.value for t in walk.transitions}
    bounds = [segment[0].availability_time_utc, *times, None]
    labels = ["UNDETERMINED", *(d.value for d in dirs)]
    out = []
    for i, label in enumerate(labels):
        lo, hi = bounds[i], bounds[i + 1]
        inside = [
            d
            for d in decisions
            if lo <= d.candidate.availability_time_utc
            and (hi is None or d.candidate.availability_time_utc < hi)
        ]
        out.append(
            {
                "from": lo.isoformat(),
                "to": hi.isoformat()
                if hi
                else segment[-1].availability_time_utc.isoformat(),
                "direction": label,
                "opened_by": "START" if i == 0 else kinds.get(lo, "BOOTSTRAP"),
                **{
                    r.value: sum(1 for d in inside if d.reason is r)
                    for r in ContextReason
                },
            }
        )
    return out


def main() -> int:  # pragma: no cover - manual measurement
    from btmm_ai_scanner.measurements.atr import compute_atr_series
    from btmm_ai_scanner.poi.configuration import PoiConfiguration
    from btmm_ai_scanner.poi.qualification import (
        CONTEXT_GATED_TYPES,
        qualify_candidates,
    )
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
    out = repo / "artifacts" / "rc3_context_gate"
    out.mkdir(parents=True, exist_ok=True)
    pconfig = PoiConfiguration(minimum_price_tick=Decimal("0.01"))
    report: dict[str, Any] = {}
    for stem, tf in (
        ("w1", Timeframe.W1), ("d1", Timeframe.D1), ("h4", Timeframe.H4),
        ("h1", Timeframe.H1), ("m15", Timeframe.M15), ("m5", Timeframe.M5),
    ):  # fmt: skip
        total: dict[str, Counter[str]] = {}
        segs: list[dict[str, Any]] = []
        for seg in load_unsealed_segments(
            base / f"ohlc_{stem}.csv", tf, out / "_n" / f"{stem}.csv"
        ):
            if len(seg) < 30:
                continue
            for k, v in coverage(seg).items():
                total[k] = total.get(k, Counter()) + v
            raw = [c for _n, det in _DETECTORS for c in det(seg, pconfig)]
            atr = compute_atr_series(seg, 14)
            q, _ = qualify_candidates(
                raw, {c.record_id: a for c, a in zip(seg, atr, strict=True)}, pconfig
            )
            segs.extend(
                direction_segments(
                    seg, [c for c in q if c.poi_type in CONTEXT_GATED_TYPES]
                )
            )
        before = total["arbitration"]
        after = total["mapped"]
        report[tf.value] = {
            "before_after": {
                t: [before[t], after[t]] for t in sorted(set(before) | set(after))
            },
            "reasons": {
                r.value: sum(total.get(r.value, Counter()).values())
                for r in ContextReason
            },
            "segments": segs,
        }
        print(
            tf.value,
            json.dumps(report[tf.value]["reasons"]),
            "segments",
            len(segs),
            flush=True,
        )
    (out / "context_gate_audit.json").write_text(json.dumps(report, indent=1), "utf-8")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
