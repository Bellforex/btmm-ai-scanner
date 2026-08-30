"""Test-side transcription of the Pine P3 POI detectors.

Test/parity tooling only — nothing in `src/` imports this, and it changes no
production semantics.

Pine cannot run locally, so this module is a faithful structural transcription
of the detector block in
`tradingview/btmm_poi_btrc_scanner_p3_dev.pine`. It is compared against the
PRODUCTION Python detectors, which are always the reference side. The model is
never the thing under test: if the two disagree, the Pine port is wrong.

WHY IT IS SHAPED LIKE THE FRONTIER, NOT LIKE THE BATCH
------------------------------------------------------
Production detectors are batch functions over an entire candle array. Pine
cannot do that: it sees one confirmed bar at a time and keeps a bounded window.
So this model runs the Pine loop — for each confirmed bar `t`, hand the
detectors a ring of the last `RING` candles ending at `t` and let them emit the
POIs whose CONFIRMING candle is `t`. Comparing that accumulated registry
against the production batch output therefore proves two things at once: the
per-detector semantics, and that the bounded ring loses nothing.

The ring is deliberately the exact production dependency bound (21 bars: a
pressure-wick candle plus its 20-bar baseline), so a detector that silently
needed more history would fail the differential test rather than pass by
accident.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from decimal import Decimal
from itertools import pairwise

from btmm_ai_scanner.contracts.normalized_candle import NormalizedCandle
from btmm_ai_scanner.measurements.atr import compute_atr_series
from btmm_ai_scanner.poi.configuration import PoiConfiguration

# ---- vocabulary (mirrors the C_POI_* constants in the Pine appendix) --------

TYPE_BUY_ORDER_BLOCK = 1
TYPE_SELL_ORDER_BLOCK = 2
TYPE_BUY_FAIR_VALUE_GAP = 3
TYPE_SELL_FAIR_VALUE_GAP = 4
TYPE_BUY_TO_SELL_CANDLE = 5
TYPE_SELL_TO_BUY_CANDLE = 6
TYPE_BASE_RALLY = 7
TYPE_BASE_DROP = 8
TYPE_BULLISH_PRESSURE_WICK = 9
TYPE_BEARISH_PRESSURE_WICK = 10
TYPE_BULLISH_ENGULFING = 11
TYPE_BEARISH_ENGULFING = 12
TYPE_HAMMER = 13
TYPE_SHOOTING_STAR = 14
TYPE_MORNING_STAR = 15
TYPE_EVENING_STAR = 16
TYPE_SUPPORT_ZONE = 17
TYPE_RESISTANCE_ZONE = 18

DIR_BULLISH = 1
DIR_BEARISH = -1

TIER_NA = 0
TIER_STANDARD = 1
TIER_STRONG = 2

#: Detector dependency windows, mirroring the C_POI_* constants.
PW_BASELINE_WINDOW = 20
REV_LOOKBACK = 3
REV_CONFIRM_WINDOW = 3

#: Pine's bounded detection ring: the widest production dependency window.
RING = 21

_ZERO = Decimal("0")
_TWO = Decimal("2")


@dataclass(frozen=True)
class ModelPoi:
    """One emitted POI, in the Pine projection (no UUIDs anywhere)."""

    poi_type: int
    direction: int
    zone_top: Decimal
    zone_bottom: Decimal
    tier: int
    src_first_time: int
    src_count: int
    src_last_time: int
    candidate_time: int
    confirm_time: int

    @property
    def identity(self) -> tuple[int, int, int, int]:
        """AD-1 identity: type over a contiguous source-candle run."""
        return (self.poi_type, self.src_first_time, self.src_count, self.src_last_time)


# ---- candle metrics (measurements/candle_metrics.py) ------------------------


def _range(c: NormalizedCandle) -> Decimal:
    return c.high - c.low


def _body(c: NormalizedCandle) -> Decimal:
    return abs(c.close - c.open)


def _body_eff(c: NormalizedCandle) -> Decimal:
    r = _range(c)
    return _ZERO if r == _ZERO else _body(c) / r


def _upper_wick(c: NormalizedCandle) -> Decimal:
    return c.high - max(c.open, c.close)


def _lower_wick(c: NormalizedCandle) -> Decimal:
    return min(c.open, c.close) - c.low


def _bull_close_pos(c: NormalizedCandle) -> Decimal:
    r = _range(c)
    return _ZERO if r == _ZERO else (c.close - c.low) / r


def _bear_close_pos(c: NormalizedCandle) -> Decimal:
    r = _range(c)
    return _ZERO if r == _ZERO else (c.high - c.close) / r


def _is_bull(c: NormalizedCandle) -> bool:
    return c.close > c.open


def _is_bear(c: NormalizedCandle) -> bool:
    return c.close < c.open


def _ms(c: NormalizedCandle, *, availability: bool = False) -> int:
    moment = c.availability_time_utc if availability else c.event_time_utc
    return int(moment.timestamp() * 1000)


# ---- detectors, transcribed from the Pine appendix --------------------------


def _detect_order_blocks(
    w: Sequence[NormalizedCandle], cfg: PoiConfiguration
) -> list[ModelPoi]:
    wn = len(w)
    if wn < 2:
        return []
    origin, displacement = w[wn - 2], w[wn - 1]
    origin_range = _range(origin)
    if origin_range == _ZERO:
        return []
    ratio = _range(displacement) / origin_range
    if ratio < cfg.order_block_size_ratio_standard:
        return []
    if _is_bear(origin) and _is_bull(displacement) and displacement.close > origin.high:
        poi_type, direction = TYPE_BUY_ORDER_BLOCK, DIR_BULLISH
    elif (
        _is_bull(origin) and _is_bear(displacement) and displacement.close < origin.low
    ):
        poi_type, direction = TYPE_SELL_ORDER_BLOCK, DIR_BEARISH
    else:
        return []
    tier = TIER_STRONG if ratio >= cfg.order_block_size_ratio_strong else TIER_STANDARD
    return [
        ModelPoi(
            poi_type,
            direction,
            origin.high,
            origin.low,
            tier,
            _ms(origin),
            2,
            _ms(displacement),
            _ms(origin),
            _ms(displacement, availability=True),
        )
    ]


def _detect_fvg(w: Sequence[NormalizedCandle], cfg: PoiConfiguration) -> list[ModelPoi]:
    del cfg
    wn = len(w)
    if wn < 3:
        return []
    first, _middle, third = w[wn - 3], w[wn - 2], w[wn - 1]
    if third.low > first.high:
        poi_type, direction = TYPE_BUY_FAIR_VALUE_GAP, DIR_BULLISH
        zone_top, zone_bottom = third.low, first.high
    elif third.high < first.low:
        poi_type, direction = TYPE_SELL_FAIR_VALUE_GAP, DIR_BEARISH
        zone_top, zone_bottom = first.low, third.high
    else:
        return []
    return [
        ModelPoi(
            poi_type,
            direction,
            zone_top,
            zone_bottom,
            TIER_NA,
            _ms(first),
            3,
            _ms(third),
            _ms(first),
            _ms(third, availability=True),
        )
    ]


def _detect_engulfing(
    w: Sequence[NormalizedCandle], cfg: PoiConfiguration
) -> list[ModelPoi]:
    wn = len(w)
    if wn < 2:
        return []
    engulfed, engulfing = w[wn - 2], w[wn - 1]
    engulfed_range = _range(engulfed)
    if engulfed_range == _ZERO:
        return []
    ratio = _range(engulfing) / engulfed_range
    if ratio < cfg.order_block_size_ratio_standard:
        return []
    if _is_bear(engulfed) and _is_bull(engulfing):
        poi_type, direction = TYPE_BULLISH_ENGULFING, DIR_BULLISH
    elif _is_bull(engulfed) and _is_bear(engulfing):
        poi_type, direction = TYPE_BEARISH_ENGULFING, DIR_BEARISH
    else:
        return []
    tier = TIER_STRONG if ratio >= cfg.order_block_size_ratio_strong else TIER_STANDARD
    return [
        ModelPoi(
            poi_type,
            direction,
            engulfed.high,
            engulfed.low,
            tier,
            _ms(engulfed),
            2,
            _ms(engulfing),
            _ms(engulfed),
            _ms(engulfing, availability=True),
        )
    ]


def _detect_stars(
    w: Sequence[NormalizedCandle], cfg: PoiConfiguration
) -> list[ModelPoi]:
    wn = len(w)
    if wn < 3:
        return []
    first, middle, third = w[wn - 3], w[wn - 2], w[wn - 1]
    if _range(middle) == _ZERO:
        return []
    middle_eff = _body_eff(middle)
    if middle_eff > cfg.doji_body_efficiency_standard:
        return []
    first_midpoint = (first.high + first.low) / _TWO
    if _is_bear(first) and _is_bull(third) and third.close > first_midpoint:
        poi_type, direction = TYPE_MORNING_STAR, DIR_BULLISH
    elif _is_bull(first) and _is_bear(third) and third.close < first_midpoint:
        poi_type, direction = TYPE_EVENING_STAR, DIR_BEARISH
    else:
        return []
    tier = (
        TIER_STRONG if middle_eff <= cfg.doji_body_efficiency_strong else TIER_STANDARD
    )
    return [
        ModelPoi(
            poi_type,
            direction,
            middle.high,
            middle.low,
            tier,
            _ms(first),
            3,
            _ms(third),
            _ms(first),
            _ms(third, availability=True),
        )
    ]


def _detect_single_candle_reversals(
    w: Sequence[NormalizedCandle], cfg: PoiConfiguration
) -> list[ModelPoi]:
    wn = len(w)
    if wn < 1:
        return []
    c = w[wn - 1]
    candle_range = _range(c)
    if candle_range == _ZERO:
        return []
    lw_share = _lower_wick(c) / candle_range
    uw_share = _upper_wick(c) / candle_range
    eff = _body_eff(c)
    hammer_ok = (
        lw_share >= cfg.hammer_shooting_star_wick_share_standard
        and eff <= cfg.hammer_shooting_star_body_efficiency_standard
        and uw_share <= cfg.hammer_shooting_star_opposite_wick_standard
    )
    star_ok = (
        uw_share >= cfg.hammer_shooting_star_wick_share_standard
        and eff <= cfg.hammer_shooting_star_body_efficiency_standard
        and lw_share <= cfg.hammer_shooting_star_opposite_wick_standard
    )
    if hammer_ok:
        poi_type, direction = TYPE_HAMMER, DIR_BULLISH
        zone_top, zone_bottom = min(c.open, c.close), c.low
        strong = (
            lw_share >= cfg.hammer_shooting_star_wick_share_strong
            and eff <= cfg.hammer_shooting_star_body_efficiency_strong
            and uw_share <= cfg.hammer_shooting_star_opposite_wick_strong
        )
    elif star_ok:
        poi_type, direction = TYPE_SHOOTING_STAR, DIR_BEARISH
        zone_top, zone_bottom = c.high, max(c.open, c.close)
        strong = (
            uw_share >= cfg.hammer_shooting_star_wick_share_strong
            and eff <= cfg.hammer_shooting_star_body_efficiency_strong
            and lw_share <= cfg.hammer_shooting_star_opposite_wick_strong
        )
    else:
        return []
    return [
        ModelPoi(
            poi_type,
            direction,
            zone_top,
            zone_bottom,
            TIER_STRONG if strong else TIER_STANDARD,
            _ms(c),
            1,
            _ms(c),
            _ms(c),
            _ms(c, availability=True),
        )
    ]


def _median_total_range(window: Sequence[NormalizedCandle]) -> Decimal:
    """`f_medianRange` / `median_total_range`: odd -> middle, even -> mean."""
    if len(window) == 0:
        return _ZERO
    ranges = sorted(_range(c) for c in window)
    mid = len(ranges) // 2
    if len(ranges) % 2 == 1:
        return ranges[mid]
    return (ranges[mid - 1] + ranges[mid]) / _TWO


def _detect_pressure_wicks(
    w: Sequence[NormalizedCandle], cfg: PoiConfiguration
) -> list[ModelPoi]:
    wn = len(w)
    if wn < 1:
        return []
    ci = wn - 1
    c = w[ci]
    candle_range = _range(c)
    if candle_range == _ZERO:
        return []

    prec_start = max(0, ci - PW_BASELINE_WINDOW)
    preceding = w[prec_start:ci]
    baseline = _median_total_range(preceding) if len(preceding) > 0 else candle_range
    range_context = candle_range / baseline if baseline > _ZERO else Decimal("1")

    lw = _lower_wick(c)
    uw = _upper_wick(c)
    lw_share = lw / candle_range
    uw_share = uw / candle_range
    eff = _body_eff(c)
    bull_pos = _bull_close_pos(c)
    bear_pos = _bear_close_pos(c)

    dominance_bull = uw == _ZERO or lw >= cfg.pressure_wick_dominance_standard * uw
    dominance_bear = lw == _ZERO or uw >= cfg.pressure_wick_dominance_standard * lw

    bull_candidate = (
        lw_share >= cfg.pressure_wick_share_standard
        and eff >= cfg.pressure_wick_body_efficiency_standard
        and dominance_bull
        and bull_pos >= cfg.pressure_wick_close_position_standard
    )
    bear_candidate = (
        uw_share >= cfg.pressure_wick_share_standard
        and eff >= cfg.pressure_wick_body_efficiency_standard
        and dominance_bear
        and bear_pos >= cfg.pressure_wick_close_position_standard
    )

    if bull_candidate:
        poi_type, direction = TYPE_BULLISH_PRESSURE_WICK, DIR_BULLISH
        zone_top, zone_bottom = min(c.open, c.close), c.low
        strong = (
            lw_share >= cfg.pressure_wick_share_strong
            and eff >= cfg.pressure_wick_body_efficiency_strong
            and lw >= cfg.pressure_wick_dominance_strong * uw
            and bull_pos >= cfg.pressure_wick_close_position_strong
            and range_context >= cfg.pressure_wick_range_context_strong
        )
    elif bear_candidate:
        poi_type, direction = TYPE_BEARISH_PRESSURE_WICK, DIR_BEARISH
        zone_top, zone_bottom = c.high, max(c.open, c.close)
        strong = (
            uw_share >= cfg.pressure_wick_share_strong
            and eff >= cfg.pressure_wick_body_efficiency_strong
            and uw >= cfg.pressure_wick_dominance_strong * lw
            and bear_pos >= cfg.pressure_wick_close_position_strong
            and range_context >= cfg.pressure_wick_range_context_strong
        )
    else:
        return []

    return [
        ModelPoi(
            poi_type,
            direction,
            zone_top,
            zone_bottom,
            TIER_STRONG if strong else TIER_STANDARD,
            _ms(c),
            1,
            _ms(c),
            _ms(c),
            _ms(c, availability=True),
        )
    ]


def _detect_reversal_candles(
    w: Sequence[NormalizedCandle], cfg: PoiConfiguration
) -> list[ModelPoi]:
    """Delayed confirmation: emit only when THIS bar is the first qualifying probe."""
    wn = len(w)
    out: list[ModelPoi] = []
    for k in range(1, REV_CONFIRM_WINDOW + 1):
        ci = wn - 1 - k
        if ci < REV_LOOKBACK:
            continue
        candidate = w[ci]
        baseline = max(_range(c) for c in w[ci - REV_LOOKBACK : ci])
        if baseline == _ZERO:
            continue
        ratio = _range(candidate) / baseline
        if ratio < cfg.reversal_candidate_size_ratio_standard:
            continue
        eff = _body_eff(candidate)
        if eff < cfg.reversal_body_efficiency_standard:
            continue

        if _is_bear(candidate):
            close_pos = _bear_close_pos(candidate)
            poi_type, direction = TYPE_SELL_TO_BUY_CANDLE, DIR_BULLISH
        elif _is_bull(candidate):
            close_pos = _bull_close_pos(candidate)
            poi_type, direction = TYPE_BUY_TO_SELL_CANDLE, DIR_BEARISH
        else:
            continue
        if close_pos < cfg.reversal_close_position_standard:
            continue

        midpoint = (candidate.high + candidate.low) / _TWO
        confirm_idx = -1
        probe_end = min(ci + 1 + REV_CONFIRM_WINDOW, wn)
        for p in range(ci + 1, probe_end):
            hit = (
                w[p].close > midpoint
                if direction == DIR_BULLISH
                else w[p].close < midpoint
            )
            if hit:
                confirm_idx = p
                break
        if confirm_idx != wn - 1:
            continue

        strong = (
            ratio >= cfg.reversal_candidate_size_ratio_strong
            and eff >= cfg.reversal_body_efficiency_strong
            and close_pos >= cfg.reversal_close_position_strong
        )
        out.append(
            ModelPoi(
                poi_type,
                direction,
                candidate.high,
                candidate.low,
                TIER_STRONG if strong else TIER_STANDARD,
                _ms(candidate),
                1,
                _ms(candidate),
                _ms(candidate),
                _ms(w[confirm_idx], availability=True),
            )
        )
    return out


#: The P3-I2 fixed-window detector group, in the Pine execution order.
Detector = Callable[[Sequence[NormalizedCandle], PoiConfiguration], list[ModelPoi]]

FIXED_WINDOW_DETECTORS: tuple[Detector, ...] = (
    _detect_order_blocks,
    _detect_fvg,
    _detect_engulfing,
    _detect_stars,
    _detect_single_candle_reversals,
)

#: P3-I3 adds the baseline / delayed-confirmation families.
NO_ATR_DETECTORS: tuple[Detector, ...] = (
    *FIXED_WINDOW_DETECTORS,
    _detect_pressure_wicks,
    _detect_reversal_candles,
)


def _detect_bases(
    w: Sequence[NormalizedCandle],
    atr_w: Sequence[Decimal | None],
    cfg: PoiConfiguration,
) -> list[ModelPoi]:
    """Every qualifying (start, length) emits its own POI, as production does."""
    wn = len(w)
    di = wn - 1
    out: list[ModelPoi] = []
    if di < cfg.base_min_candles:
        return out
    departure = w[di]
    departure_range = _range(departure)
    if departure_range == _ZERO:
        return out

    for length in range(cfg.base_min_candles, cfg.base_max_candles + 1):
        si = di - length
        if si < 0:
            continue
        base = w[si:di]
        max_base_range = max(_range(c) for c in base)
        if max_base_range == _ZERO:
            continue
        if max_base_range > cfg.small_candle_ratio_standard * departure_range:
            continue
        ratio = departure_range / max_base_range
        if ratio < cfg.order_block_size_ratio_standard:
            continue

        base_high = max(c.high for c in base)
        base_low = min(c.low for c in base)
        base_height = base_high - base_low

        atr_raw = atr_w[di - 1]
        reference_atr = (
            departure_range if atr_raw is None or atr_raw == _ZERO else atr_raw
        )
        if base_height > cfg.base_height_atr_multiplier * reference_atr:
            continue
        if base_height > cfg.base_height_departure_multiplier * departure_range:
            continue

        if base_height > _ZERO:
            base_midpoint = (base_high + base_low) / _TWO
            drift_ok = all(
                abs(((c.high + c.low) / _TWO) - base_midpoint)
                <= cfg.base_midpoint_drift_ratio * base_height
                for c in base
            )
            if not drift_ok:
                continue

        overlap_ok = True
        for left, right in pairwise(base):
            overlap_top = min(left.high, right.high)
            overlap_bottom = max(left.low, right.low)
            overlap = max(_ZERO, overlap_top - overlap_bottom)
            min_range = min(_range(left), _range(right))
            if min_range == _ZERO:
                continue
            if overlap / min_range < cfg.base_overlap_ratio_minimum:
                overlap_ok = False
                break
        if not overlap_ok:
            continue

        if _is_bull(departure) and departure.close > base_high:
            poi_type, direction = TYPE_BASE_RALLY, DIR_BULLISH
        elif _is_bear(departure) and departure.close < base_low:
            poi_type, direction = TYPE_BASE_DROP, DIR_BEARISH
        else:
            continue

        strong = (
            ratio >= cfg.order_block_size_ratio_strong
            and max_base_range <= cfg.small_candle_ratio_strong * departure_range
        )
        out.append(
            ModelPoi(
                poi_type,
                direction,
                base_high,
                base_low,
                TIER_STRONG if strong else TIER_STANDARD,
                _ms(base[0]),
                length + 1,
                _ms(departure),
                _ms(base[0]),
                _ms(departure, availability=True),
            )
        )
    return out


#: Detectors that consume the continuous ATR series.
AtrDetector = Callable[
    [Sequence[NormalizedCandle], Sequence[Decimal | None], PoiConfiguration],
    list[ModelPoi],
]

ATR_DETECTORS: tuple[AtrDetector, ...] = (_detect_bases,)


def run_frontier(
    candles: Sequence[NormalizedCandle],
    configuration: PoiConfiguration,
    detectors: tuple[Detector, ...] = NO_ATR_DETECTORS,
    atr_detectors: tuple[AtrDetector, ...] = ATR_DETECTORS,
    ring: int = RING,
) -> list[ModelPoi]:
    """Replay the Pine per-bar frontier and return the accumulated registry.

    Emission is exactly-once by identity, exactly as `f_poiEmit` guards with
    `f_poiFind`. The registry is append-only and never pruned.

    The ATR series is computed ONCE over the whole stream with the production
    function and sliced to each window, mirroring Pine's continuous `wAtr`.
    Recomputing it per window would diverge from production, which builds the
    series over the entire candle array.
    """
    atr_all = compute_atr_series(tuple(candles), 14)
    registry: list[ModelPoi] = []
    seen: set[tuple[int, int, int, int]] = set()
    for t in range(len(candles)):
        first = max(0, t + 1 - ring)
        window = candles[first : t + 1]
        window_atr = atr_all[first : t + 1]
        emitted: list[ModelPoi] = []
        for detector in detectors:
            emitted.extend(detector(window, configuration))
        for atr_detector in atr_detectors:
            emitted.extend(atr_detector(window, window_atr, configuration))
        for poi in emitted:
            if poi.identity not in seen:
                seen.add(poi.identity)
                registry.append(poi)
    return registry
