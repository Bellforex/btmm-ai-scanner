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

* **Hammer / shooting star over pressure wick** (author decision B): when one
  candle is both HAMMER and BULLISH PRESSURE WICK (or SHOOTING STAR and BEARISH
  PRESSURE WICK) the named formation is primary; the wick is suppressed. No other
  non-FVG pair is ordered (``BTRC_V1_RC3_NON_FVG_ARBITRATION_MATRIX.md``).
* **RC4 profile only** (author decision 2026-09-19, ``rc4_fvg_quality``): the
  gap rule above is necessary but not sufficient. The FVG's departure candle
  must also be a genuine expansion -- the FROZEN displacement primitive must
  class it at least FAST (``range_speed_ratio`` >= ``displacement_fast_ratio``
  = 1.50 x the median range of the previous 20 bars, ``domain/displacement.py``)
  AND its range must strictly exceed the immediately preceding candle's range.
  No new multiplier is introduced: both numbers already exist. Separately, an
  FVG whose imbalance was already FULLY consumed between its formation and its
  (possibly much later, reversal-context) availability is not admitted --
  ``PRE_AVAILABILITY_CONSUMED``. That decision reads only bars already closed at
  the availability bar, so it adds no lookahead, and it does NOT change the
  frozen lifecycle rule: a pre-availability touch still never mitigates.

* **Structural context** (author decision A) is the hard gate after this step:
  ``poi/leg_origin.py`` maps a candidate only when the frozen P2 structure at its
  availability agrees with its direction, or when a later break makes its candle
  the origin of the confirmed leg (reversal context). Retracement, trendline,
  S/R and liquidity stay confluence metadata (``rc3_poi_context_audit.py``).
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Any
from uuid import UUID

from btmm_ai_scanner.contracts.normalized_candle import NormalizedCandle
from btmm_ai_scanner.domain.configuration import MarketMeasurementConfiguration
from btmm_ai_scanner.measurements.candle_metrics import (
    median_total_range,
    total_range,
)
from btmm_ai_scanner.poi.configuration import PoiConfiguration
from btmm_ai_scanner.poi.enums import PoiDirection, PoiType

__all__ = [
    "ARBITER_TYPES",
    "CONTEXT_GATED_TYPES",
    "FVG_TYPES",
    "DepartureMetrics",
    "QualificationDecision",
    "QualificationReason",
    "departure_metrics_by_candle",
    "fvg_passes_quality",
    "fvg_pre_availability_consumed",
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


_PRESSURE_WICKS = frozenset(
    {PoiType.BULLISH_PRESSURE_WICK, PoiType.BEARISH_PRESSURE_WICK}
)
# same candle, same direction: HAMMER is bullish, SHOOTING STAR is bearish
_WICK_SPECIALIZATIONS = frozenset({PoiType.HAMMER, PoiType.SHOOTING_STAR})
CONTEXT_GATED_TYPES = frozenset(
    {
        *FVG_TYPES,
        *ARBITER_TYPES,
        PoiType.BUY_TO_SELL_CANDLE,
        PoiType.SELL_TO_BUY_CANDLE,
    }
)


class QualificationReason(StrEnum):
    MAPPED = "MAPPED"
    QUALITY_REJECT = "QUALITY_REJECT"  # gap < 0.35 x ATR-14 (RC3 rule)
    SAME_ORIGIN_SUPPRESSED = "SAME_ORIGIN_SUPPRESSED"
    # RC4 profile only
    NO_DISPLACEMENT = "NO_DISPLACEMENT"
    PREDECESSOR_NOT_EXPANSIVE = "PREDECESSOR_NOT_EXPANSIVE"
    PRE_AVAILABILITY_CONSUMED = "PRE_AVAILABILITY_CONSUMED"


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


#: The frozen displacement window / threshold, read from the measurement
#: contract so this module never restates them (the tick is irrelevant here).
_DISPLACEMENT = MarketMeasurementConfiguration(minimum_price_tick=Decimal("0.01"))


@dataclass(frozen=True)
class DepartureMetrics:
    """The frozen expansion measurements of an FVG's departure (middle) candle.

    ``displacement_ratio`` is ``range_speed_ratio``: the candle's total range
    over the median total range of the previous ``range_context_window`` bars
    (the same primitive ``domain/displacement.py`` classifies). ``None`` while
    fewer than a full window of predecessors exists, exactly as an unknown ATR
    blocks the gap rule."""

    displacement_ratio: Decimal | None
    expands_predecessor: bool

    @property
    def is_fast(self) -> bool:
        return (
            self.displacement_ratio is not None
            and self.displacement_ratio >= _DISPLACEMENT.displacement_fast_ratio
        )


def departure_metrics_by_candle(
    candles: Sequence[NormalizedCandle],
    indexes: Iterable[int],
    window: int | None = None,
) -> dict[UUID, DepartureMetrics]:
    """``DepartureMetrics`` for the candles at ``indexes`` (departure candles),
    measured over the bars that precede each one."""
    size = window or _DISPLACEMENT.range_context_window
    out: dict[UUID, DepartureMetrics] = {}
    for index in indexes:
        if index <= 0 or index >= len(candles):
            continue
        candle = candles[index]
        preceding = candles[max(0, index - size) : index]
        ratio = (
            total_range(candle) / median_total_range(preceding)
            if len(preceding) >= size and median_total_range(preceding) > 0
            else None
        )
        out[candle.record_id] = DepartureMetrics(
            displacement_ratio=ratio,
            expands_predecessor=total_range(candle) > total_range(candles[index - 1]),
        )
    return out


def fvg_pre_availability_consumed(
    fvg: Any,
    availability_time_utc: datetime,
    candles: Sequence[NormalizedCandle],
) -> bool:
    """RC4: was the imbalance already fully filled by the time the candidate
    became available? Reads only candles closed at or before
    ``availability_time_utc`` and strictly after the formation completed, so it
    is causal at the availability bar. Full consumption = price traded to the
    far edge of the gap (a bullish gap is consumed at its bottom).

    The window starts at the THIRD source candle's close, read from the candle
    itself: the structural context gate rewrites a delayed candidate's
    ``confirmation_time_utc`` to its new availability, so that field cannot be
    used to find the formation."""
    bullish = fvg.direction is PoiDirection.BULLISH
    third = fvg.source_candle_record_ids[2]
    formation_end = next(
        (c.availability_time_utc for c in candles if c.record_id == third), None
    )
    if formation_end is None:
        return False
    for candle in candles:
        if candle.availability_time_utc <= formation_end:
            continue
        if candle.availability_time_utc > availability_time_utc:
            break
        if bullish and candle.low <= fvg.zone_bottom:
            return True
        if not bullish and candle.high >= fvg.zone_top:
            return True
    return False


def fvg_passes_quality(
    fvg: Any, departure_atr: Decimal | None, configuration: PoiConfiguration
) -> tuple[bool, Decimal | None]:
    if departure_atr is None or departure_atr <= 0:
        return False, None
    ratio = (fvg.zone_top - fvg.zone_bottom) / departure_atr
    return ratio >= configuration.fvg_min_gap_atr_ratio, ratio


def _rc4_departure_reject(
    fvg: Any, departure_metrics: Mapping[UUID, DepartureMetrics] | None
) -> QualificationReason | None:
    """RC4 displacement gate. ``None`` means the departure candle qualifies."""
    metrics = (departure_metrics or {}).get(fvg.source_candle_record_ids[1])
    if metrics is None or not metrics.is_fast:
        return QualificationReason.NO_DISPLACEMENT
    if not metrics.expands_predecessor:
        return QualificationReason.PREDECESSOR_NOT_EXPANSIVE
    return None


def qualify_candidates(
    candidates: Iterable[Any],
    atr_by_candle: Mapping[UUID, Decimal | None],
    configuration: PoiConfiguration,
    known_origins: Mapping[tuple[UUID, PoiDirection], PoiType] | None = None,
    departure_metrics: Mapping[UUID, DepartureMetrics] | None = None,
) -> tuple[list[Any], list[QualificationDecision]]:
    """Split raw candidates into mapped candidates and a decision per FVG.
    Non-FVG candidates pass unchanged (their quality is their frozen detector).
    ``known_origins`` adds arbiter patterns detected earlier (incremental)."""
    items = list(candidates)
    origins: dict[tuple[UUID, PoiDirection], PoiType] = dict(known_origins or {})
    for candidate in items:
        if candidate.poi_type in ARBITER_TYPES:
            origins.setdefault(origin_key(candidate), candidate.poi_type)
    specific = {
        origin_key(c): c.poi_type for c in items if c.poi_type in _WICK_SPECIALIZATIONS
    }
    mapped: list[Any] = []
    decisions: list[QualificationDecision] = []
    for candidate in items:
        if candidate.poi_type in _PRESSURE_WICKS:
            # Author decision B (2026-09-17): HAMMER / SHOOTING STAR is the more
            # specific named rejection formation of the same candle.
            named = specific.get(origin_key(candidate))
            if named is not None:
                decisions.append(
                    QualificationDecision(
                        candidate,
                        QualificationReason.SAME_ORIGIN_SUPPRESSED,
                        None,
                        named,
                    )
                )
                continue
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
        elif configuration.rc4_fvg_quality and (
            rc4_reason := _rc4_departure_reject(candidate, departure_metrics)
        ):
            # RC4 only: a material gap is not enough -- the departure candle
            # must be a real expansion (frozen displacement primitive).
            decisions.append(QualificationDecision(candidate, rc4_reason, ratio))
        else:
            decisions.append(
                QualificationDecision(candidate, QualificationReason.MAPPED, ratio)
            )
            mapped.append(candidate)
    return mapped, decisions
