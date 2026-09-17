"""RC3 POI qualification: raw pattern candidate -> qualified mapped POI.

Detection is not qualification (author, 2026-09-17). Raw detector output stays
auditable; a candidate reaches the mapped P3 registry only if it passes

1. **type-specific quality** and
2. **same-origin arbitration**.

Rules (author decisions, 2026-09-17):

* **FVG gap quality** -- a FAIR VALUE GAP is mapped only when its gap width is at
  least ``fvg_min_gap_atr_ratio`` (0.35) x Wilder ATR-14 of its departure
  (middle) candle. The ATR is known when the gap completes, so the decision uses
  no later bar. Without an ATR yet (warm-up) the gap cannot be qualified.
  Register §35J's middle-candle expansion rule was measured and NOT adopted: it
  rejected the author's approved M15 example (``BTRC_V1_RC3_FVG_QUALITY_AUDIT.md``).
* **Same-origin exclusivity** -- one originating formation maps one primary POI.
  An FVG whose departure candle is the final candle of a same-direction candle
  pattern (ENGULFING -- and therefore any ORDER BLOCK, which is always also an
  engulfing --, PRESSURE WICK, HAMMER, SHOOTING STAR, MORNING / EVENING STAR,
  BASE RALLY / DROP) is that pattern's imbalance, not a second POI: the pattern
  is primary, the FVG is ``SAME_ORIGIN_SUPPRESSED``. Every such pattern is
  available no later than the FVG, so arbitration never needs a future bar. An
  FVG departing from a later, independent candle is kept.

Market context (trend, leg, retracement, liquidity) is recorded for audit by
``tests/parity_support/rc3_poi_context_audit.py`` and is not a mapping gate: the
project authority states no automated context gate for these types.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum
from typing import Any
from uuid import UUID

from btmm_ai_scanner.poi.configuration import PoiConfiguration
from btmm_ai_scanner.poi.enums import PoiDirection, PoiType

__all__ = [
    "ARBITER_TYPES",
    "FVG_TYPES",
    "QualificationDecision",
    "QualificationReason",
    "fvg_passes_quality",
    "origin_key",
    "qualify_candidates",
]

FVG_TYPES = frozenset({PoiType.BUY_FAIR_VALUE_GAP, PoiType.SELL_FAIR_VALUE_GAP})
ARBITER_TYPES = frozenset(
    {
        PoiType.BULLISH_ENGULFING,
        PoiType.BEARISH_ENGULFING,
        PoiType.BULLISH_PRESSURE_WICK,
        PoiType.BEARISH_PRESSURE_WICK,
        PoiType.HAMMER,
        PoiType.SHOOTING_STAR,
        PoiType.MORNING_STAR,
        PoiType.EVENING_STAR,
        PoiType.BASE_RALLY,
        PoiType.BASE_DROP,
    }
)


class QualificationReason(StrEnum):
    MAPPED = "MAPPED"
    QUALITY_REJECT = "QUALITY_REJECT"
    SAME_ORIGIN_SUPPRESSED = "SAME_ORIGIN_SUPPRESSED"


@dataclass(frozen=True)
class QualificationDecision:
    candidate: Any
    reason: QualificationReason
    gap_atr_ratio: Decimal | None = None
    primary_type: PoiType | None = None


def origin_key(candidate: Any) -> tuple[UUID, PoiDirection]:
    """The originating formation of a candle pattern: its final candle."""
    return (candidate.source_candle_record_ids[-1], candidate.direction)


def _departure_key(fvg: Any) -> tuple[UUID, PoiDirection]:
    return (fvg.source_candle_record_ids[1], fvg.direction)


def fvg_passes_quality(
    fvg: Any, departure_atr: Decimal | None, configuration: PoiConfiguration
) -> tuple[bool, Decimal | None]:
    if departure_atr is None or departure_atr <= 0:
        return False, None
    ratio = (fvg.zone_top - fvg.zone_bottom) / departure_atr
    return ratio >= configuration.fvg_min_gap_atr_ratio, ratio


def qualify_candidates(
    candidates: Iterable[Any],
    atr_by_candle: Mapping[UUID, Decimal | None],
    configuration: PoiConfiguration,
    known_origins: Mapping[tuple[UUID, PoiDirection], PoiType] | None = None,
) -> tuple[list[Any], list[QualificationDecision]]:
    """Split raw candidates into mapped candidates and a decision per FVG.
    Non-FVG candidates pass unchanged (their quality is their frozen detector).
    ``known_origins`` adds arbiter patterns detected earlier (incremental)."""
    items = list(candidates)
    origins: dict[tuple[UUID, PoiDirection], PoiType] = dict(known_origins or {})
    for candidate in items:
        if candidate.poi_type in ARBITER_TYPES:
            origins.setdefault(origin_key(candidate), candidate.poi_type)
    mapped: list[Any] = []
    decisions: list[QualificationDecision] = []
    for candidate in items:
        if candidate.poi_type not in FVG_TYPES:
            mapped.append(candidate)
            continue
        ok, ratio = fvg_passes_quality(
            candidate,
            atr_by_candle.get(candidate.source_candle_record_ids[1]),
            configuration,
        )
        primary = origins.get(_departure_key(candidate))
        if primary is not None:
            decisions.append(
                QualificationDecision(
                    candidate,
                    QualificationReason.SAME_ORIGIN_SUPPRESSED,
                    ratio,
                    primary,
                )
            )
        elif not ok:
            decisions.append(
                QualificationDecision(
                    candidate, QualificationReason.QUALITY_REJECT, ratio
                )
            )
        else:
            decisions.append(
                QualificationDecision(candidate, QualificationReason.MAPPED, ratio)
            )
            mapped.append(candidate)
    return mapped, decisions
