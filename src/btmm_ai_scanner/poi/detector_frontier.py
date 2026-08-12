"""A6-A: exact incremental POI candidate-detection frontier.

The batch ``_detect_bundle_candidates`` reruns all ten detectors over the whole
growing prefix on every candle (O(prefix) per candle). This module reproduces
its output exactly while touching only the newly eligible/unresolved origin for
each detector, so the incremental replay hot path never rescans history and
never recomputes ``compute_atr_series(full_prefix, 14)``.

Exactness strategy per detector:

* Local, window-ending-at-``m`` detectors whose candidate depends only on its own
  bounded window (order blocks, fair value gaps, engulfing, single-candle
  reversals, three-candle stars, pressure wicks) and the delayed-confirmation
  reversal detector are evaluated by calling the **unchanged batch detector** on
  a bounded candle slice that is mathematically proven slice-exact for the
  window ending at the newest candle, then keeping only the candidate(s) newly
  confirmed at that candle. Their results are append-only and immutable.
* ``detect_bases`` is NOT slice-exact — it consumes a full-prefix Wilder ATR-14
  that is append-stable but not slice-stable. It is reproduced by a private
  per-departure evaluator that faithfully mirrors the batch inner body using the
  exact full-prefix incremental ATR-14 value ``atr[m-1]``. Never a suffix ATR.
* Period levels are held as bounded per-granularity running-extrema state
  (current window REPLACE each candle; previous window ADD/REMOVE on rollover).
* Reference zones are a 1:1 projection of the current incremental measurement
  support/resistance zones and equal-level clusters (ADD/REPLACE/REMOVE follow
  the upstream measurement records), reusing the prior tuple verbatim when the
  measurement records are unchanged.

The unchanged batch detectors and ``compute_atr_series`` remain the differential
oracle; every prefix is asserted equal to ``_detect_bundle_candidates`` in the
permanent tests.
"""

from dataclasses import dataclass, field, replace
from decimal import Decimal
from itertools import pairwise
from typing import Any

from btmm_ai_scanner.contracts.normalized_candle import NormalizedCandle
from btmm_ai_scanner.domain import MarketMeasurementAnalysis
from btmm_ai_scanner.measurements.atr import (
    IncrementalAtrState,
    advance_incremental_atr,
    initial_incremental_atr_state,
)
from btmm_ai_scanner.measurements.candle_metrics import total_range
from btmm_ai_scanner.poi.bases import BaseCandidate
from btmm_ai_scanner.poi.configuration import PoiConfiguration
from btmm_ai_scanner.poi.engulfing import detect_engulfing
from btmm_ai_scanner.poi.enums import PoiDirection, PoiStrengthTier, PoiType
from btmm_ai_scanner.poi.fair_value_gaps import detect_fair_value_gaps
from btmm_ai_scanner.poi.order_blocks import detect_order_blocks
from btmm_ai_scanner.poi.period_levels import (
    _GRANULARITIES,
    PeriodLevelCandidate,
)
from btmm_ai_scanner.poi.pressure_wicks import detect_pressure_wicks
from btmm_ai_scanner.poi.reference_zones import detect_reference_zones
from btmm_ai_scanner.poi.reversal_candles import detect_reversal_candles
from btmm_ai_scanner.poi.single_candle_reversals import detect_single_candle_reversals
from btmm_ai_scanner.poi.three_candle_stars import detect_three_candle_stars

_ATR_PERIOD = 14
_TWO = Decimal("2")
_ZERO = Decimal("0")

# Bounded look-back required by any detector's frontier: pressure wicks read the
# candle plus the 20 preceding candles for their median baseline (the largest
# window), so a 21-candle ring covers every detector (bases need base_max+1,
# reversal needs 7).
_RING_SIZE = 21


@dataclass(frozen=True)
class _PeriodGranularityState:
    """Bounded running state for one calendar granularity (day/week/month)."""

    current_start: Any = None
    current_end: Any = None
    current_first_availability: Any = None
    current_high_candle: NormalizedCandle | None = None
    current_low_candle: NormalizedCandle | None = None
    previous_start: Any = None
    previous_end: Any = None
    previous_first_availability: Any = None
    previous_high_candle: NormalizedCandle | None = None
    previous_low_candle: NormalizedCandle | None = None


@dataclass(frozen=True)
class PoiFrontierDelta:
    """A6-AΔ: the exact per-candle change to the candidate universe, computed
    from the frontier's own knowledge — never by diffing the full historical
    candidate list. ``new_candidates`` first appear this candle, ``changed_candidates``
    keep their identity but change content, ``removed_identities`` disappear.
    Applying (prev universe + new + changed - removed) reproduces the current
    filtered universe exactly (proven by the permanent delta differential).

    Append-only families contribute NEW only (this candle's ``step_candidates``);
    reference zones and period levels are the only mutable families, and their
    deltas are diffed over BOUNDED current sets (active SR/EL, <=12 period
    candidates), so there is no O(P) historical scan."""

    new_candidates: tuple[Any, ...] = ()
    changed_candidates: tuple[Any, ...] = ()
    removed_identities: tuple[Any, ...] = ()


_EMPTY_DELTA = PoiFrontierDelta()


def _candidate_identity(candidate: Any) -> Any:
    """Stable identity matching the observation semantic key's distinctions:
    period by (poi_type, window), reference by (poi_type, source zone id),
    append-only by (poi_type, source candles)."""
    if hasattr(candidate, "period_start_time_utc"):
        return (
            candidate.poi_type,
            "P",
            candidate.period_start_time_utc,
            candidate.period_end_time_utc,
        )
    if hasattr(candidate, "source_zone_record_id"):
        return (candidate.poi_type, "R", candidate.source_zone_record_id)
    return (candidate.poi_type, "A", candidate.source_candle_record_ids)


def _diff_bounded(
    old: tuple[Any, ...], new: tuple[Any, ...]
) -> tuple[list[Any], list[Any], list[Any]]:
    """NEW / CHANGED / REMOVED-identity over two BOUNDED candidate sets (reference
    or period), by identity + content equality."""
    old_by = {_candidate_identity(c): c for c in old}
    new_by = {_candidate_identity(c): c for c in new}
    new_c = [c for k, c in new_by.items() if k not in old_by]
    changed = [c for k, c in new_by.items() if k in old_by and old_by[k] != c]
    removed = [k for k in old_by if k not in new_by]
    return new_c, changed, removed


@dataclass(frozen=True)
class _DetectorFrontierState:
    """Private per-timeframe incremental detection state. Immutable; a new
    instance is produced each advance so a raised advance leaves the caller's
    state untouched (transactional)."""

    atr_state: IncrementalAtrState = field(
        default_factory=lambda: initial_incremental_atr_state(_ATR_PERIOD)
    )
    atr_series: tuple[Decimal | None, ...] = ()
    candle_ring: tuple[NormalizedCandle, ...] = ()
    append_only_candidates: tuple[Any, ...] = ()
    period_states: tuple[_PeriodGranularityState, ...] = ()
    # Reference-zone reuse: the source measurement (record_id, fingerprint)
    # signature the cached reference candidates were built from, and the cached
    # candidates themselves. Unchanged upstream => the identical tuple is reused.
    reference_signature: tuple[Any, ...] = ()
    reference_candidates: tuple[Any, ...] = ()
    # A6-AΔ: the previous candle's period candidates (bounded <=12), kept so the
    # next advance can diff them; and the delta emitted by the advance that
    # produced this state (transient per-advance output, consumed by the caller).
    period_candidates: tuple[Any, ...] = ()
    last_delta: PoiFrontierDelta = _EMPTY_DELTA


def create_initial_detector_frontier_state() -> _DetectorFrontierState:
    return _DetectorFrontierState(
        period_states=tuple(_PeriodGranularityState() for _ in _GRANULARITIES),
    )


# ---------------------------------------------------------------------------
# Bases: exact per-departure evaluator (faithful copy of detect_bases' inner
# body). detect_bases has NO cross-window state — every ``(start, length)`` pair
# is evaluated independently — so the set of bases over the full prefix equals
# the union over departures ``m`` of the bases whose departure candle is ``m``.
# Each such base depends only on ``candles[start:m+1]`` and ``atr[m-1]``.
# ---------------------------------------------------------------------------


def _evaluate_new_bases(
    ring: tuple[NormalizedCandle, ...],
    reference_atr: Decimal | None,
    configuration: PoiConfiguration,
) -> list[BaseCandidate]:
    """Evaluate every base whose departure candle is the newest ring candle,
    reproducing detect_bases exactly. ``reference_atr`` must be the exact
    full-prefix ATR-14 value at index ``m-1`` (``atr_values[end - 1]``)."""
    results: list[BaseCandidate] = []
    departure = ring[-1]
    departure_range = total_range(departure)
    if departure_range == 0:
        return results

    for length in range(
        configuration.base_min_candles, configuration.base_max_candles + 1
    ):
        # base_candles = candles[start:end] with end == m (departure index),
        # start == m - length; requires ``length`` real candles before departure.
        if length + 1 > len(ring):
            continue
        base_candles = ring[-(length + 1) : -1]

        max_base_range = max(total_range(c) for c in base_candles)
        if max_base_range == 0:
            continue
        if max_base_range > configuration.small_candle_ratio_standard * departure_range:
            continue

        ratio = departure_range / max_base_range
        if ratio < configuration.order_block_size_ratio_standard:
            continue

        base_high = max(c.high for c in base_candles)
        base_low = min(c.low for c in base_candles)
        base_height = base_high - base_low

        effective_reference_atr = reference_atr
        if effective_reference_atr is None or effective_reference_atr == _ZERO:
            effective_reference_atr = departure_range

        if (
            base_height
            > configuration.base_height_atr_multiplier * effective_reference_atr
        ):
            continue
        if (
            base_height
            > configuration.base_height_departure_multiplier * departure_range
        ):
            continue

        if base_height > 0:
            base_midpoint = (base_high + base_low) / _TWO
            drift_ok = all(
                abs(((c.high + c.low) / _TWO) - base_midpoint)
                <= configuration.base_midpoint_drift_ratio * base_height
                for c in base_candles
            )
            if not drift_ok:
                continue

        overlap_ok = True
        for left, right in pairwise(base_candles):
            overlap_top = min(left.high, right.high)
            overlap_bottom = max(left.low, right.low)
            overlap = max(_ZERO, overlap_top - overlap_bottom)
            min_range = min(total_range(left), total_range(right))
            if min_range == 0:
                continue
            if overlap / min_range < configuration.base_overlap_ratio_minimum:
                overlap_ok = False
                break
        if not overlap_ok:
            continue

        departure_bullish = (
            departure.close > departure.open and departure.close > base_high
        )
        departure_bearish = (
            departure.close < departure.open and departure.close < base_low
        )

        if departure_bullish:
            poi_type = PoiType.BASE_RALLY
            direction = PoiDirection.BULLISH
        elif departure_bearish:
            poi_type = PoiType.BASE_DROP
            direction = PoiDirection.BEARISH
        else:
            continue

        strong = (
            ratio >= configuration.order_block_size_ratio_strong
            and max_base_range
            <= configuration.small_candle_ratio_strong * departure_range
        )

        results.append(
            BaseCandidate(
                symbol=departure.symbol,
                timeframe=departure.timeframe,
                poi_type=poi_type,
                direction=direction,
                zone_top=base_high,
                zone_bottom=base_low,
                strength_tier=(
                    PoiStrengthTier.STRONG if strong else PoiStrengthTier.STANDARD
                ),
                source_candle_record_ids=(
                    *(c.record_id for c in base_candles),
                    departure.record_id,
                ),
                candidate_event_time_utc=base_candles[0].event_time_utc,
                confirmation_time_utc=departure.availability_time_utc,
                availability_time_utc=departure.availability_time_utc,
            )
        )

    return results


# ---------------------------------------------------------------------------
# Local + reversal frontiers via proven slice-exact batch-detector calls.
# ---------------------------------------------------------------------------


def _new_local_candidates(
    ring: tuple[NormalizedCandle, ...],
    configuration: PoiConfiguration,
) -> list[Any]:
    """Evaluate the local (window-ending-at-newest) and delayed-confirmation
    detectors on bounded slices, keeping only candidates newly confirmed at the
    newest ring candle. Each slice is proven to reproduce the corresponding
    full-prefix batch candidate exactly."""
    newest = ring[-1]
    candidates: list[Any] = []

    if len(ring) >= 2:
        candidates.extend(detect_order_blocks(ring[-2:], configuration))
        candidates.extend(detect_engulfing(ring[-2:], configuration))
    if len(ring) >= 3:
        candidates.extend(detect_fair_value_gaps(ring[-3:], configuration))
        candidates.extend(detect_three_candle_stars(ring[-3:], configuration))
    candidates.extend(detect_single_candle_reversals(ring[-1:], configuration))

    # Pressure wicks: candidate for the newest candle uses only itself and its
    # <=20 preceding candles (the full ring); keep only the newest candle's.
    candidates.extend(
        c
        for c in detect_pressure_wicks(ring, configuration)
        if c.source_candle_record_ids == (newest.record_id,)
    )

    # Reversal candles: origin in [m-3, m-1] confirmed by the first probe within
    # <=3 bars; the 7-candle slice covers every origin (lookback 3) confirmable
    # at the newest candle. Keep only those whose confirmation IS this candle.
    reversal_slice = ring[-7:]
    candidates.extend(
        c
        for c in detect_reversal_candles(reversal_slice, configuration)
        if c.confirmation_time_utc == newest.availability_time_utc
    )

    return candidates


# ---------------------------------------------------------------------------
# Period levels: bounded running-extrema state per granularity.
# ---------------------------------------------------------------------------


def _advance_period_granularity(
    state: _PeriodGranularityState,
    candle: NormalizedCandle,
    window_fn: Any,
) -> _PeriodGranularityState:
    start, end = window_fn(candle.event_time_utc)

    if state.current_start is None:
        return replace(
            state,
            current_start=start,
            current_end=end,
            current_first_availability=candle.availability_time_utc,
            current_high_candle=candle,
            current_low_candle=candle,
        )

    if start == state.current_start:
        new_high = state.current_high_candle
        new_low = state.current_low_candle
        assert new_high is not None
        assert new_low is not None
        # Strict comparison => the earliest extreme wins ties (matches the batch
        # ``_extreme_candidates`` ``> / <`` scan).
        if candle.high > new_high.high:
            new_high = candle
        if candle.low < new_low.low:
            new_low = candle
        return replace(
            state,
            current_high_candle=new_high,
            current_low_candle=new_low,
        )

    # Calendar rollover: the just-closed current window becomes previous; a new
    # current window opens with this candle as its (sole so far) extreme.
    return _PeriodGranularityState(
        current_start=start,
        current_end=end,
        current_first_availability=candle.availability_time_utc,
        current_high_candle=candle,
        current_low_candle=candle,
        previous_start=state.current_start,
        previous_end=state.current_end,
        previous_first_availability=state.current_first_availability,
        previous_high_candle=state.current_high_candle,
        previous_low_candle=state.current_low_candle,
    )


def _period_high_candidate(
    extreme: NormalizedCandle,
    poi_type: PoiType,
    period_start: Any,
    period_end: Any,
    availability: Any,
) -> PeriodLevelCandidate:
    return PeriodLevelCandidate(
        symbol=extreme.symbol,
        timeframe=extreme.timeframe,
        poi_type=poi_type,
        direction=PoiDirection.BEARISH,
        representative_price=extreme.high,
        source_candle_record_ids=(extreme.record_id,),
        period_start_time_utc=period_start,
        period_end_time_utc=period_end,
        candidate_event_time_utc=extreme.event_time_utc,
        confirmation_time_utc=availability,
        availability_time_utc=availability,
    )


def _period_low_candidate(
    extreme: NormalizedCandle,
    poi_type: PoiType,
    period_start: Any,
    period_end: Any,
    availability: Any,
) -> PeriodLevelCandidate:
    return PeriodLevelCandidate(
        symbol=extreme.symbol,
        timeframe=extreme.timeframe,
        poi_type=poi_type,
        direction=PoiDirection.BULLISH,
        representative_price=extreme.low,
        source_candle_record_ids=(extreme.record_id,),
        period_start_time_utc=period_start,
        period_end_time_utc=period_end,
        candidate_event_time_utc=extreme.event_time_utc,
        confirmation_time_utc=availability,
        availability_time_utc=availability,
    )


def _period_candidates(
    period_states: tuple[_PeriodGranularityState, ...],
    latest_candle: NormalizedCandle,
) -> list[PeriodLevelCandidate]:
    results: list[PeriodLevelCandidate] = []
    for state, granularity in zip(period_states, _GRANULARITIES, strict=True):
        (
            _window_fn,
            current_high_type,
            current_low_type,
            previous_high_type,
            previous_low_type,
        ) = granularity
        if state.current_start is None:
            continue
        assert state.current_high_candle is not None
        assert state.current_low_candle is not None
        # Current window: availability is the latest candle in the window (== the
        # candle just processed), matching ``current_window.candles[-1]``.
        results.append(
            _period_high_candidate(
                state.current_high_candle,
                current_high_type,
                state.current_start,
                state.current_end,
                latest_candle.availability_time_utc,
            )
        )
        results.append(
            _period_low_candidate(
                state.current_low_candle,
                current_low_type,
                state.current_start,
                state.current_end,
                latest_candle.availability_time_utc,
            )
        )
        if state.previous_start is not None:
            assert state.previous_high_candle is not None
            assert state.previous_low_candle is not None
            # Previous window: availability is the current window's FIRST candle
            # availability (``current_window.candles[0]``), fixed until rollover.
            rollover_availability = state.current_first_availability
            results.append(
                _period_high_candidate(
                    state.previous_high_candle,
                    previous_high_type,
                    state.previous_start,
                    state.previous_end,
                    rollover_availability,
                )
            )
            results.append(
                _period_low_candidate(
                    state.previous_low_candle,
                    previous_low_type,
                    state.previous_start,
                    state.previous_end,
                    rollover_availability,
                )
            )
    return results


# ---------------------------------------------------------------------------
# Reference zones: 1:1 projection of the current measurement SR zones / EL
# clusters (ADD/REPLACE/REMOVE follow upstream). Reuse the prior candidate tuple
# verbatim when the upstream records are unchanged (identity stability).
# ---------------------------------------------------------------------------


def _reference_signature(
    measurement_analysis: MarketMeasurementAnalysis,
) -> tuple[Any, ...]:
    return (
        tuple(
            (zone.record_id, zone.content_fingerprint)
            for zone in measurement_analysis.support_resistance_zones
        ),
        tuple(
            (cluster.record_id, cluster.content_fingerprint)
            for cluster in measurement_analysis.equal_level_clusters
        ),
    )


def advance_detector_frontier(
    state: _DetectorFrontierState,
    candle: NormalizedCandle,
    measurement_analysis: MarketMeasurementAnalysis,
    configuration: PoiConfiguration,
) -> tuple[_DetectorFrontierState, list[Any], tuple[Decimal | None, ...]]:
    """Advance the detection frontier by one candle. Returns the new frontier
    state, the full current candidate universe (identical set to
    ``_detect_bundle_candidates`` over the whole prefix, after the shared
    ``enabled_poi_types`` filter), and the exact full-prefix ATR-14 series (for
    the lifecycle walk). Transactional: every value is a local; the replacement
    state is built only at the end."""
    new_atr_state, atr_value = advance_incremental_atr(state.atr_state, candle)
    new_atr_series = (*state.atr_series, atr_value)

    new_ring = (*state.candle_ring, candle)[-_RING_SIZE:]

    # Append-only frontiers (local + reversal + bases). Bases use atr[m-1].
    reference_atr_prev = new_atr_series[-2] if len(new_atr_series) >= 2 else None
    step_candidates: list[Any] = _new_local_candidates(new_ring, configuration)
    step_candidates.extend(
        _evaluate_new_bases(new_ring, reference_atr_prev, configuration)
    )
    new_append_only = (*state.append_only_candidates, *step_candidates)

    # Period levels.
    new_period_states = tuple(
        _advance_period_granularity(granularity_state, candle, granularity[0])
        for granularity_state, granularity in zip(
            state.period_states, _GRANULARITIES, strict=True
        )
    )
    period_candidates = _period_candidates(new_period_states, candle)

    # Reference zones: reuse verbatim when upstream unchanged.
    new_signature = _reference_signature(measurement_analysis)
    if new_signature == state.reference_signature:
        new_reference_candidates = state.reference_candidates
    else:
        new_reference_candidates = tuple(
            detect_reference_zones(
                measurement_analysis.support_resistance_zones,
                measurement_analysis.equal_level_clusters,
            )
        )

    # A6-AΔ: exact bounded delta. Append-only families contribute this candle's
    # step_candidates as NEW (no history scan). Reference and period levels are
    # the only mutable families; diff their BOUNDED current sets. When the
    # reference signature is unchanged the tuple is reused verbatim => no ref delta.
    enabled = configuration.enabled_poi_types
    ref_new: list[Any] = []
    ref_changed: list[Any] = []
    ref_removed: list[Any] = []
    if new_reference_candidates is not state.reference_candidates:
        ref_new, ref_changed, ref_removed = _diff_bounded(
            state.reference_candidates, new_reference_candidates
        )
    period_new, period_changed, period_removed = _diff_bounded(
        state.period_candidates, tuple(period_candidates)
    )

    def _en(cands: list[Any]) -> tuple[Any, ...]:
        return tuple(c for c in cands if c.poi_type in enabled)

    def _en_ident(idents: list[Any]) -> tuple[Any, ...]:
        return tuple(i for i in idents if i[0] in enabled)

    delta = PoiFrontierDelta(
        new_candidates=(*_en(step_candidates), *_en(ref_new), *_en(period_new)),
        changed_candidates=(*_en(ref_changed), *_en(period_changed)),
        removed_identities=(*_en_ident(ref_removed), *_en_ident(period_removed)),
    )

    new_state = _DetectorFrontierState(
        atr_state=new_atr_state,
        atr_series=new_atr_series,
        candle_ring=new_ring,
        append_only_candidates=new_append_only,
        period_states=new_period_states,
        reference_signature=new_signature,
        reference_candidates=new_reference_candidates,
        period_candidates=tuple(period_candidates),
        last_delta=delta,
    )

    universe: list[Any] = [
        *new_append_only,
        *new_reference_candidates,
        *period_candidates,
    ]
    filtered = [c for c in universe if c.poi_type in enabled]
    return new_state, filtered, new_atr_series
