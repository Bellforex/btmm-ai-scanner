"""RC3 POI detector-overlap audit (Phase 1 of the POI classification campaign).

Test/validation tooling only. Runs the frozen candle-based POI detectors from
``src/`` over real FXCM XAUUSD same-session exports and classifies every case
where two or more detectors fire on overlapping formations:

A. SAME_SEMANTIC_FORMATION — identical source candles AND identical zone
   geometry (the same originating formation described twice).
B. DISTINCT_OVERLAPPING    — different source formations whose zones overlap.
C. AMBIGUOUS               — shared source candle(s) but different geometry or
   span (one pattern contains or extends the other).

Sealed validation lock: candles whose [event, availability] interval touches
the sealed out-of-sample range are removed and the series is split around it,
so no detector ever sees, and this audit never reports, a formation there.
Reference zones (S/R) and period levels are excluded here: they are derived
from swing / calendar outputs, not from a candle formation, so "same source
formation" is not defined for them; they are audited separately.
"""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from btmm_ai_scanner.config.enums import Timeframe
from btmm_ai_scanner.contracts.normalized_candle import NormalizedCandle
from btmm_ai_scanner.poi.bases import detect_bases
from btmm_ai_scanner.poi.configuration import PoiConfiguration
from btmm_ai_scanner.poi.engulfing import detect_engulfing
from btmm_ai_scanner.poi.fair_value_gaps import detect_fair_value_gaps
from btmm_ai_scanner.poi.order_blocks import detect_order_blocks
from btmm_ai_scanner.poi.pressure_wicks import detect_pressure_wicks
from btmm_ai_scanner.poi.reversal_candles import detect_reversal_candles
from btmm_ai_scanner.poi.single_candle_reversals import detect_single_candle_reversals
from btmm_ai_scanner.poi.three_candle_stars import detect_three_candle_stars
from tests.parity_support.rc3_aligned_capture import _load_export
from tests.parity_support.rc3_daily_authority import (
    SEALED_FIRST_EVENT_UTC,
    SEALED_LAST_EVENT_UTC,
)

__all__ = [
    "AuditRecord",
    "classify_overlaps",
    "load_unsealed_segments",
    "run_detectors",
]

_DETECTORS = (
    ("order_blocks", detect_order_blocks),
    ("fair_value_gaps", detect_fair_value_gaps),
    ("reversal_candles", detect_reversal_candles),
    ("bases", detect_bases),
    ("pressure_wicks", detect_pressure_wicks),
    ("engulfing", detect_engulfing),
    ("single_candle_reversals", detect_single_candle_reversals),
    ("three_candle_stars", detect_three_candle_stars),
)


@dataclass(frozen=True)
class AuditRecord:
    timeframe: str
    detector: str
    poi_type: str
    direction: str
    source_ids: tuple[str, ...]
    source_event_utc: str
    availability_utc: str
    top: Decimal
    bottom: Decimal
    tier: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "timeframe": self.timeframe,
            "detector": self.detector,
            "poi_type": self.poi_type,
            "direction": self.direction,
            "source_candles": len(self.source_ids),
            "source_event_utc": self.source_event_utc,
            "availability_utc": self.availability_utc,
            "top": str(self.top),
            "bottom": str(self.bottom),
            "tier": self.tier,
        }


def _touches_sealed(candle: NormalizedCandle) -> bool:
    return (
        candle.event_time_utc <= SEALED_LAST_EVENT_UTC
        and candle.availability_time_utc >= SEALED_FIRST_EVENT_UTC
    )


def load_unsealed_segments(
    export: Path, timeframe: Timeframe, scratch: Path
) -> list[tuple[NormalizedCandle, ...]]:
    candles = _load_export(export, timeframe, scratch)
    segments: list[list[NormalizedCandle]] = [[]]
    for candle in candles:
        if _touches_sealed(candle):
            if segments[-1]:
                segments.append([])
            continue
        segments[-1].append(candle)
    return [tuple(s) for s in segments if s]


def run_detectors(
    segments: Sequence[tuple[NormalizedCandle, ...]], configuration: PoiConfiguration
) -> list[AuditRecord]:
    records: list[AuditRecord] = []
    for segment in segments:
        for name, detector in _DETECTORS:
            for cand in detector(segment, configuration):
                records.append(
                    AuditRecord(
                        timeframe=cand.timeframe.value,
                        detector=name,
                        poi_type=cand.poi_type.value,
                        direction=cand.direction.value,
                        source_ids=tuple(str(x) for x in cand.source_candle_record_ids),
                        source_event_utc=cand.candidate_event_time_utc.isoformat(),
                        availability_utc=cand.availability_time_utc.isoformat(),
                        top=cand.zone_top,
                        bottom=cand.zone_bottom,
                        tier=getattr(cand, "strength_tier", None).value
                        if getattr(cand, "strength_tier", None) is not None
                        else "",
                    )
                )
    return records


def classify_overlaps(records: Sequence[AuditRecord]) -> dict[str, Any]:
    """Pairwise classification restricted to same timeframe + same direction.

    Pairs are generated through a shared-source-candle index and a
    price-sorted sweep, never an all-pairs scan over the whole set.
    """
    by_source: dict[tuple[str, str, str], list[int]] = defaultdict(list)
    for i, r in enumerate(records):
        for sid in r.source_ids:
            by_source[(r.timeframe, r.direction, sid)].append(i)

    same: Counter[tuple[str, str]] = Counter()
    ambiguous: Counter[tuple[str, str]] = Counter()
    seen: set[tuple[int, int]] = set()
    examples: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for idxs in by_source.values():
        for a_pos, a in enumerate(idxs):
            for b in idxs[a_pos + 1 :]:
                key = (min(a, b), max(a, b))
                if key in seen:
                    continue
                seen.add(key)
                ra, rb = records[key[0]], records[key[1]]
                if ra.poi_type == rb.poi_type:
                    continue
                pair = tuple(sorted((ra.poi_type, rb.poi_type)))
                if ra.source_ids == rb.source_ids and (ra.top, ra.bottom) == (
                    rb.top,
                    rb.bottom,
                ):
                    same[pair] += 1  # type: ignore[index]
                    label = "A:" + "+".join(pair)
                else:
                    ambiguous[pair] += 1  # type: ignore[index]
                    label = "C:" + "+".join(pair)
                if len(examples[label]) < 3:
                    examples[label].append({"a": ra.as_dict(), "b": rb.as_dict()})

    # B: distinct sources, overlapping zones (sweep by bottom within tf+direction)
    distinct: Counter[tuple[str, str]] = Counter()
    groups: dict[tuple[str, str], list[AuditRecord]] = defaultdict(list)
    for r in records:
        groups[(r.timeframe, r.direction)].append(r)
    for members in groups.values():
        members.sort(key=lambda r: r.bottom)
        active: list[AuditRecord] = []
        for r in members:
            active = [x for x in active if x.top >= r.bottom]
            for x in active:
                if set(x.source_ids) & set(r.source_ids):
                    continue
                if x.poi_type != r.poi_type:
                    distinct[tuple(sorted((x.poi_type, r.poi_type)))] += 1  # type: ignore[index]
            active.append(r)

    ob = [r for r in records if r.detector == "order_blocks"]
    eng_keys = {
        (r.timeframe, r.source_ids, r.top, r.bottom)
        for r in records
        if r.detector == "engulfing"
    }
    ob_also_engulfing = sum(
        1 for r in ob if (r.timeframe, r.source_ids, r.top, r.bottom) in eng_keys
    )
    return {
        "records": len(records),
        "by_type": dict(Counter(r.poi_type for r in records)),
        "A_same_semantic_formation": {"+".join(k): v for k, v in same.most_common()},
        "B_distinct_overlapping_top15": {
            "+".join(k): v for k, v in distinct.most_common(15)
        },
        "C_ambiguous_shared_source": {
            "+".join(k): v for k, v in ambiguous.most_common()
        },
        "order_blocks": len(ob),
        "order_blocks_identical_to_an_engulfing": ob_also_engulfing,
        "examples": dict(examples),
    }


def main() -> int:
    repo = Path(__file__).resolve().parents[2]
    base = repo / "artifacts" / "rc3_aligned"
    out = repo / "artifacts" / "rc3_poi_quality"
    out.mkdir(parents=True, exist_ok=True)
    configuration = PoiConfiguration(minimum_price_tick=Decimal("0.01"))
    report: dict[str, Any] = {
        "generated_utc": datetime.now(tz=UTC).isoformat(),
        "timeframes": {},
    }
    all_records: list[AuditRecord] = []
    for stem, tf in (
        ("w1", Timeframe.W1),
        ("d1", Timeframe.D1),
        ("h4", Timeframe.H4),
        ("h1", Timeframe.H1),
        ("m15", Timeframe.M15),
        ("m5", Timeframe.M5),
    ):
        segments = load_unsealed_segments(
            base / f"ohlc_{stem}.csv", tf, out / "_norm" / f"{stem}.csv"
        )
        records = run_detectors(segments, configuration)
        all_records.extend(records)
        report["timeframes"][tf.value] = {
            "candles": sum(len(s) for s in segments),
            "segments": len(segments),
            "first_utc": segments[0][0].event_time_utc.isoformat(),
            "last_utc": segments[-1][-1].event_time_utc.isoformat(),
            **classify_overlaps(records),
        }
    (out / "overlap_audit.json").write_text(
        json.dumps(report, indent=2, default=str), encoding="utf-8"
    )
    for tf, v in report["timeframes"].items():
        print(
            tf,
            v["candles"],
            "records",
            v["records"],
            "OB",
            v["order_blocks"],
            "OB==ENG",
            v["order_blocks_identical_to_an_engulfing"],
        )
        print("   A:", v["A_same_semantic_formation"])
        print("   C:", v["C_ambiguous_shared_source"])
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
