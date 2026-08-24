"""P1-SR-PERF-2 — test-only model of the incremental S/R reaction frontier.

The Pine port must publish a support/resistance zone on the exact bar the
reaction resolves (proved necessary in
``test_pine_p1_sr_candle_growth_semantics.py``), but recomputing the whole
detector on every confirmed bar exhausted TradingView's Basic budget. This
module develops and validates the replacement: a persistent reaction frontier
that advances a small amount of bounded state per candle instead of rescanning.

**Nothing here is production code.** It is the executable specification the Pine
implementation is transcribed from, and the harness that proves the
transcription's algorithm is exact.

Two things are compared at every prefix:

``_batch_walk``   ORACLE. The detector's outer walk, transcribed once, calling
                  the **production** ``_evaluate_reaction`` for every reaction.
                  Cross-checked against the fully production
                  ``detect_support_resistance_zones`` so the transcription
                  itself cannot drift (see
                  ``test_batch_walk_transcription_matches_production``).

``SRFrontier``    MODEL. The same walk with every ``_evaluate_reaction`` call
                  replaced by a persistent tracker lookup/advance — the design
                  the Pine frontier implements.

Why the ATR array is an explicit parameter
------------------------------------------
``detect_support_resistance_zones`` re-seeds Wilder ATR from the first candle of
whatever slice it is handed. Under a *sliding* window that makes the ATR at a
fixed bar change as the window advances, which would invalidate a tracker's
cached reaction (it pins ``atr[reaction_start]``). Pine does not have that
problem: its ATR advances incrementally from the start of the chart, so the
value at a given bar is fixed forever. The frontier is exact **only** under that
fixed-ATR contract, so both oracle and model take one full-history ATR series.
That is a real precondition of the design, and it is asserted directly by
``test_frontier_requires_position_stable_atr``.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

from btmm_ai_scanner.config.enums import InternalSymbol, Timeframe
from btmm_ai_scanner.contracts.normalized_candle import NormalizedCandle
from btmm_ai_scanner.contracts.provenance_record import EvidenceClassification
from btmm_ai_scanner.contracts.raw_candle import CandleCompleteness, CandleVolumeKind
from btmm_ai_scanner.contracts.types import SemVer
from btmm_ai_scanner.domain.configuration import MarketMeasurementConfiguration
from btmm_ai_scanner.domain.enums import SupportResistanceType, SwingType
from btmm_ai_scanner.domain.support_resistance import (
    _evaluate_reaction,
    detect_support_resistance_zones,
)
from btmm_ai_scanner.domain.swings import ConfirmedSwing, detect_confirmed_swings
from btmm_ai_scanner.measurements.atr import compute_atr_series
from btmm_ai_scanner.measurements.legs import measure_leg

_ZERO = Decimal("0")
_LOOKBACK = 300  # the Pine P1 rolling-history contract

_RAW_CANDLE_ID = UUID("0193f320-1234-7abc-8def-abcdefabcdaa")
_PROVENANCE_ID = UUID("0193f320-1234-7abc-8def-abcdefabcdff")
_FINGERPRINT = "a" * 64
_BASE_TIME = datetime(2026, 1, 1, tzinfo=UTC)
_CONFIG = MarketMeasurementConfiguration(minimum_price_tick=Decimal("0.01"))


# ---------------------------------------------------------------------------
# Fixture construction
# ---------------------------------------------------------------------------


def _record_id(index: int) -> UUID:
    return UUID(f"0193f320-1234-7abc-8def-{index:012x}")


def _candle(index: int, o: float, h: float, low: float, c: float) -> NormalizedCandle:
    event_time = _BASE_TIME + timedelta(minutes=index)
    availability = event_time + timedelta(minutes=1)
    return NormalizedCandle.model_validate(
        {
            "record_id": _record_id(index),
            "content_fingerprint": _FINGERPRINT,
            "raw_candle_id": _RAW_CANDLE_ID,
            "provider": "FXCM",
            "source_reference": "fxcm-xauusd-m1",
            "source_symbol": "XAUUSD",
            "source_timeframe": "M1",
            "symbol": InternalSymbol.XAUUSD,
            "timeframe": Timeframe.M1,
            "event_time_utc": event_time,
            "availability_time_utc": availability,
            "processing_time_utc": availability,
            "original_event_time": event_time,
            "original_availability_time": availability,
            "original_timezone": "UTC",
            "open": Decimal(str(round(o, 3))),
            "high": Decimal(str(round(h, 3))),
            "low": Decimal(str(round(low, 3))),
            "close": Decimal(str(round(c, 3))),
            "volume": Decimal("10"),
            "volume_kind": CandleVolumeKind.TICK,
            "completeness": CandleCompleteness.CONFIRMED_COMPLETE,
            "rule_version": SemVer.parse("0.1.0"),
            "contract_version": SemVer.parse("0.1.0"),
            "schema_version": SemVer.parse("0.1.0"),
            "provenance_id": _PROVENANCE_ID,
        }
    )


def _swing(
    swing_index: int,
    swing_type: SwingType,
    price: str,
    pivot_candle_index: int,
    candles: tuple[NormalizedCandle, ...],
    reference_atr: str = "2.0",
    confirmation_offset_minutes: int = 6,
) -> ConfirmedSwing:
    pivot_time = candles[pivot_candle_index].event_time_utc
    confirmation_time = pivot_time + timedelta(minutes=confirmation_offset_minutes)
    return ConfirmedSwing(
        record_id=_record_id(100_000 + swing_index),
        content_fingerprint=_FINGERPRINT,
        symbol=InternalSymbol.XAUUSD,
        timeframe=Timeframe.M1,
        swing_type=swing_type,
        pivot_price=Decimal(price),
        pivot_bar_index=pivot_candle_index,
        pivot_candle_record_ids=(candles[pivot_candle_index].record_id,),
        pivot_start_time_utc=pivot_time,
        pivot_end_time_utc=pivot_time,
        local_confirmation_time_utc=pivot_time + timedelta(minutes=2),
        meaningful_confirmation_time_utc=confirmation_time,
        confirmation_candle_id=candles[pivot_candle_index].record_id,
        pivot_reference_atr=Decimal(reference_atr),
        pivot_tie_tolerance=Decimal("0.02"),
        reversal_threshold=Decimal("0.5"),
        reversal_excursion=Decimal("1"),
        availability_time_utc=confirmation_time,
        rule_version=SemVer.parse("1.0.0"),
        contract_version=SemVer.parse("0.1.0"),
        schema_version=SemVer.parse("0.1.0"),
        evidence_classification=EvidenceClassification.ENGINEERING_PROVISIONAL,
        provenance_id=_PROVENANCE_ID,
    )


# ---------------------------------------------------------------------------
# Comparable projection of a zone candidate
# ---------------------------------------------------------------------------

Zone = tuple[str, str, Decimal, Decimal, tuple[str, ...], datetime]


def _project(candidate: object) -> Zone:
    """Semantic content of a zone candidate, UUID-independent where it can be."""
    return (
        candidate.zone_type.value,  # type: ignore[attr-defined]
        str(candidate.origin_swing_record_id),  # type: ignore[attr-defined]
        candidate.zone_top,  # type: ignore[attr-defined]
        candidate.zone_bottom,  # type: ignore[attr-defined]
        tuple(
            str(x)
            for x in candidate.qualifying_touch_swing_record_ids  # type: ignore[attr-defined]
        ),
        candidate.confirmation_time_utc,  # type: ignore[attr-defined]
    )


@dataclass(frozen=True)
class _Resolved:
    """A zone the walk decided to publish, in comparable form."""

    zone_type: str
    origin_id: str
    zone_top: Decimal
    zone_bottom: Decimal
    touch_ids: tuple[str, ...]
    confirmation_time: datetime

    def as_zone(self) -> Zone:
        return (
            self.zone_type,
            self.origin_id,
            self.zone_top,
            self.zone_bottom,
            self.touch_ids,
            self.confirmation_time,
        )


# ---------------------------------------------------------------------------
# ORACLE — the detector's outer walk, calling production _evaluate_reaction
# ---------------------------------------------------------------------------


def _zone_bounds(
    origin: ConfirmedSwing,
    is_support: bool,
    configuration: MarketMeasurementConfiguration,
) -> tuple[Decimal, Decimal, Decimal]:
    depth = (
        configuration.support_resistance_zone_depth_atr_multiplier
        * origin.pivot_reference_atr
    )
    if is_support:
        bottom = origin.pivot_price
        return depth, bottom + depth, bottom
    top = origin.pivot_price
    return depth, top, top - depth


def _batch_walk_resolved(
    candles: tuple[NormalizedCandle, ...],
    atr_values: tuple[Decimal | None, ...],
    swings: tuple[ConfirmedSwing, ...],
    configuration: MarketMeasurementConfiguration,
) -> list[_Resolved]:
    """Transcription of detect_support_resistance_zones' walk, ATR injected.

    Byte-for-byte the same control flow as
    ``domain/support_resistance.detect_support_resistance_zones``; the ONLY
    change is that the ATR series is supplied rather than re-derived, so a
    sliding window cannot silently re-seed it.
    """
    if not candles:
        return []
    index_by_id = {candle.record_id: i for i, candle in enumerate(candles)}
    results: list[_Resolved] = []

    for zone_type, origin_type in (
        (SupportResistanceType.SUPPORT, SwingType.SWING_LOW),
        (SupportResistanceType.RESISTANCE, SwingType.SWING_HIGH),
    ):
        opposite_type = (
            SwingType.SWING_HIGH
            if origin_type == SwingType.SWING_LOW
            else SwingType.SWING_LOW
        )
        origins = sorted(
            (s for s in swings if s.swing_type == origin_type),
            key=lambda s: s.meaningful_confirmation_time_utc,
        )
        is_support = zone_type == SupportResistanceType.SUPPORT

        for origin in origins:
            origin_index = index_by_id[origin.pivot_candle_record_ids[-1]]
            _, zone_top, zone_bottom = _zone_bounds(origin, is_support, configuration)

            origin_reaction = _evaluate_reaction(
                candles,
                atr_values,
                origin_index + 1,
                zone_top,
                zone_bottom,
                is_support,
                configuration,
            )
            if origin_reaction is None:
                continue

            touch_tol = (
                configuration.support_resistance_touch_tolerance_atr_multiplier
                * origin.pivot_reference_atr
            )
            pierce_tol = (
                configuration.support_resistance_pierce_tolerance_atr_multiplier
                * origin.pivot_reference_atr
            )
            qualifying: list[ConfirmedSwing] = []
            first_confirming: NormalizedCandle | None = None
            last_touch_time = origin.meaningful_confirmation_time_utc

            for touch in origins:
                if touch.record_id == origin.record_id:
                    continue
                if touch.meaningful_confirmation_time_utc <= last_touch_time:
                    continue
                if is_support:
                    geometric_ok = (
                        touch.pivot_price <= zone_top + touch_tol
                        and touch.pivot_price >= zone_bottom - pierce_tol
                    )
                else:
                    geometric_ok = (
                        touch.pivot_price >= zone_bottom - touch_tol
                        and touch.pivot_price <= zone_top + pierce_tol
                    )
                if not geometric_ok:
                    continue
                has_opposite = any(
                    s.swing_type == opposite_type
                    and last_touch_time
                    < s.meaningful_confirmation_time_utc
                    < touch.meaningful_confirmation_time_utc
                    for s in swings
                )
                if not has_opposite:
                    continue
                touch_index = index_by_id[touch.pivot_candle_record_ids[-1]]
                touch_reaction = _evaluate_reaction(
                    candles,
                    atr_values,
                    touch_index + 1,
                    zone_top,
                    zone_bottom,
                    is_support,
                    configuration,
                )
                if touch_reaction is None:
                    continue
                qualifying.append(touch)
                if first_confirming is None:
                    first_confirming = touch_reaction.confirming_candle
                last_touch_time = touch.meaningful_confirmation_time_utc

            if first_confirming is None:
                continue
            results.append(
                _Resolved(
                    zone_type=zone_type.value,
                    origin_id=str(origin.record_id),
                    zone_top=zone_top,
                    zone_bottom=zone_bottom,
                    touch_ids=tuple(str(t.record_id) for t in qualifying),
                    confirmation_time=first_confirming.availability_time_utc,
                )
            )

    return results


def _batch_walk_insertion_order(
    candles: tuple[NormalizedCandle, ...],
    atr_values: tuple[Decimal | None, ...],
    swings: tuple[ConfirmedSwing, ...],
    configuration: MarketMeasurementConfiguration,
) -> tuple[Zone, ...]:
    """The walk's PRE-SORT order: support orientation first, then resistance,
    each ascending by origin confirmation time. This is what the Pine array held
    before the P1-SR-ORDERING correction added the final sort."""
    return tuple(
        r.as_zone()
        for r in _batch_walk_resolved(candles, atr_values, swings, configuration)
    )


def _batch_walk(
    candles: tuple[NormalizedCandle, ...],
    atr_values: tuple[Decimal | None, ...],
    swings: tuple[ConfirmedSwing, ...],
    configuration: MarketMeasurementConfiguration,
) -> tuple[Zone, ...]:
    """Canonical order: Python's stable ascending sort on confirmation time."""
    results = _batch_walk_resolved(candles, atr_values, swings, configuration)
    results.sort(key=lambda r: r.confirmation_time)
    return tuple(r.as_zone() for r in results)


def selected_zone(zones: tuple[Zone, ...]) -> Zone | None:
    """What the Pine parity scalars publish: the canonically LAST zone."""
    return zones[-1] if zones else None


# ---------------------------------------------------------------------------
# MODEL — the incremental reaction frontier
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Tracker:
    """Absolute-indexed reaction state. Mirrors analyzer._ReactionTracker."""

    search_start_abs: int
    zone_top: Decimal
    zone_bottom: Decimal
    is_support: bool
    last_checked_abs: int
    reaction_start_abs: int | None
    anchor: Decimal | None
    permanent: bool
    confirming_abs: int | None


def create_tracker(
    search_start_abs: int, zone_top: Decimal, zone_bottom: Decimal, is_support: bool
) -> Tracker:
    return Tracker(
        search_start_abs=search_start_abs,
        zone_top=zone_top,
        zone_bottom=zone_bottom,
        is_support=is_support,
        last_checked_abs=search_start_abs - 1,
        reaction_start_abs=None,
        anchor=None,
        permanent=False,
        confirming_abs=None,
    )


def advance_tracker(
    tracker: Tracker,
    candles: list[NormalizedCandle],
    atr_values: list[Decimal | None],
    configuration: MarketMeasurementConfiguration,
) -> Tracker:
    """One step of the frontier. Returns a tracker whose ``confirming_abs``
    equals what ``_evaluate_reaction`` would return over ``candles``."""
    if tracker.permanent:
        return tracker

    n = len(candles)
    zone_height = tracker.zone_top - tracker.zone_bottom
    if zone_height <= _ZERO:
        return replace(
            tracker,
            last_checked_abs=n - 1,
            permanent=True,
            reaction_start_abs=None,
            anchor=None,
            confirming_abs=None,
        )

    reaction_start = tracker.reaction_start_abs
    anchor = tracker.anchor
    last_checked = tracker.last_checked_abs

    if reaction_start is None:
        # Each candle is examined at most ONCE per tracker, and only forward of
        # search_start — never a rescan. The running anchor is accumulated in the
        # same pass, which also keeps it valid after the window's left edge has
        # moved past search_start.
        scan_from = max(last_checked + 1, tracker.search_start_abs)
        for index in range(scan_from, n):
            candle = candles[index]
            value = candle.low if tracker.is_support else candle.high
            anchor = (
                value
                if anchor is None
                else (min(anchor, value) if tracker.is_support else max(anchor, value))
            )
            breached = (tracker.is_support and candle.close > tracker.zone_top) or (
                not tracker.is_support and candle.close < tracker.zone_bottom
            )
            if breached:
                reaction_start = index
                break
        last_checked = n - 1
        if reaction_start is None:
            return replace(
                tracker,
                last_checked_abs=last_checked,
                reaction_start_abs=None,
                anchor=anchor,
                permanent=False,
                confirming_abs=None,
            )

    assert anchor is not None
    window_end = min(reaction_start + configuration.reaction_window_bars, n)
    is_full_window = window_end == reaction_start + configuration.reaction_window_bars
    confirming: int | None = None
    if window_end > reaction_start:
        confirming = _resolve_window(
            tracker,
            candles,
            atr_values,
            reaction_start,
            window_end,
            anchor,
            configuration,
        )
    return replace(
        tracker,
        last_checked_abs=last_checked,
        reaction_start_abs=reaction_start,
        anchor=anchor,
        permanent=is_full_window,
        confirming_abs=confirming,
    )


def _resolve_window(
    tracker: Tracker,
    candles: list[NormalizedCandle],
    atr_values: list[Decimal | None],
    reaction_start: int,
    window_end: int,
    anchor: Decimal,
    configuration: MarketMeasurementConfiguration,
) -> int | None:
    """Bounded (<= reaction_window_bars) window evaluation.

    A line-for-line transcription of ``_evaluate_reaction``'s decision block,
    reading only ``candles[reaction_start:window_end]`` — never from
    ``search_start`` — and using the production ``measure_leg`` so the leg rules
    cannot drift. ``max``/``min`` over a range keep Python's first-extremum
    tie-break, which is what picks the MFE bar.
    """
    zone_height = tracker.zone_top - tracker.zone_bottom
    window = candles[reaction_start:window_end]
    if not window:
        return None

    if tracker.is_support:
        highest_high = max(c.high for c in window)
        mfe = highest_high - anchor
        zone_clearance = max(_ZERO, highest_high - tracker.zone_top)
        mfe_index = max(
            range(reaction_start, window_end), key=lambda i: candles[i].high
        )
    else:
        lowest_low = min(c.low for c in window)
        mfe = anchor - lowest_low
        zone_clearance = max(_ZERO, tracker.zone_bottom - lowest_low)
        mfe_index = min(range(reaction_start, window_end), key=lambda i: candles[i].low)

    reference_atr = atr_values[reaction_start]
    if reference_atr is None or reference_atr == _ZERO:
        return None

    leg = measure_leg(
        candles[reaction_start : mfe_index + 1],
        atr_values[reaction_start : mfe_index + 1],
        is_bullish_direction=tracker.is_support,
        fast_normalized_speed_per_bar=configuration.leg_fast_normalized_speed_per_bar,
        fast_directional_efficiency=configuration.leg_fast_directional_efficiency,
        fast_directional_candle_share=configuration.leg_fast_directional_candle_share,
        strong_fast_normalized_speed_per_bar=(
            configuration.leg_strong_fast_normalized_speed_per_bar
        ),
        strong_fast_directional_efficiency=(
            configuration.leg_strong_fast_directional_efficiency
        ),
        strong_fast_directional_candle_share=(
            configuration.leg_strong_fast_directional_candle_share
        ),
    )
    meets_standard = (
        mfe / reference_atr >= configuration.reaction_standard_atr_ratio
        and zone_clearance / zone_height
        >= configuration.reaction_standard_zone_clearance_ratio
        and leg.directional_efficiency
        >= configuration.reaction_standard_directional_efficiency
        and leg.directional_candle_share
        >= configuration.reaction_standard_directional_candle_share
    )
    return mfe_index if meets_standard else None


@dataclass
class Counters:
    """Per-replay work counters for the P1-SR-PERF-3 diagnostic harness.

    These record what the frontier ACTUALLY does, so the hot-path hypothesis can
    be tested against measurement instead of intuition. They never influence a
    result; deleting them would not change a single published zone.
    """

    bars_processed: int = 0
    swing_frontier_changes: int = 0
    swings_added: int = 0
    swings_removed: int = 0
    swings_unchanged: int = 0
    potential_pairs: int = 0
    actual_pair_visits: int = 0
    new_semantic_pairs: int = 0
    pair_dedup_hits: int = 0
    pair_retirements: int = 0
    tracker_advances: int = 0
    reaction_starts: int = 0
    trackers_resolved: int = 0
    trackers_rejected: int = 0
    trackers_permanent: int = 0
    max_active_trackers: int = 0
    walks: int = 0
    origin_visits: int = 0
    origin_reaction_lookups: int = 0
    opposite_cursor_steps: int = 0
    resolved_zones: int = 0
    published_zones: int = 0
    origin_folds_recomputed: int = 0
    origin_folds_reused: int = 0
    orientation_rebuilds: int = 0
    orientation_reuses: int = 0
    folds_invalidated_by_delta: int = 0
    delta_geometry_tests: int = 0
    sort_invocations: int = 0
    sorted_elements: int = 0
    temp_allocations: int = 0

    def snapshot(self) -> dict[str, int]:
        return dict(self.__dict__)


class SRFrontier:
    """Persistent S/R frontier over a rolling window of ``lookback`` candles.

    Per confirmed candle it advances only unresolved trackers, and re-runs the
    origin x touch walk only when the swing set or some tracker's resolution
    actually changed. Everything else is carried forward.
    """

    def __init__(
        self,
        configuration: MarketMeasurementConfiguration,
        lookback: int = _LOOKBACK,
    ) -> None:
        self._config = configuration
        self._lookback = lookback
        self.trackers: dict[tuple[int, int], Tracker] = {}
        self._cached: tuple[Zone, ...] = ()
        self._cached_swing_key: tuple[str, ...] | None = None
        self._first_bar = True
        # instrumentation, for the complexity claims in the perf document
        self.walk_count = 0
        self.advance_count = 0
        self.bar_count = 0
        self.counters = Counters()
        self._prev_swing_keys: frozenset[str] = frozenset()
        self.per_bar: list[dict[str, int]] = []
        # P1-SR-PERF-3 pair frontier: a per-origin fold result, kept until
        # something it depends on actually moves.
        self._origin_fold: dict[tuple[str, str], _Resolved | None] = {}
        self._orientation_cache: dict[
            str, tuple[list[ConfirmedSwing], list[datetime]]
        ] = {}
        self._orientation_key: tuple[str, ...] | None = None
        self._prev_swings: dict[str, ConfirmedSwing] = {}
        self._dirty_origins: set[int] = set()

    # -- helpers ---------------------------------------------------------
    @staticmethod
    def _swing_key(swings: tuple[ConfirmedSwing, ...]) -> tuple[str, ...]:
        return tuple(str(s.record_id) for s in swings)

    def _tracker_for(
        self,
        origin_abs: int,
        search_start_abs: int,
        zone_top: Decimal,
        zone_bottom: Decimal,
        is_support: bool,
        candles: list[NormalizedCandle],
        atr_values: list[Decimal | None],
    ) -> Tracker:
        key = (origin_abs, search_start_abs)
        tracker = self.trackers.get(key)
        if tracker is None:
            self.counters.new_semantic_pairs += 1
            tracker = create_tracker(
                search_start_abs, zone_top, zone_bottom, is_support
            )
            tracker = advance_tracker(tracker, candles, atr_values, self._config)
            self.advance_count += 1
            self.counters.tracker_advances += 1
            self.trackers[key] = tracker
        else:
            self.counters.pair_dedup_hits += 1
        return tracker

    # -- main ------------------------------------------------------------
    def advance(
        self,
        candles: list[NormalizedCandle],
        atr_values: list[Decimal | None],
        swings: tuple[ConfirmedSwing, ...],
        window_first_abs: int,
    ) -> tuple[Zone, ...]:
        """Advance by one confirmed candle and return the published zone set.

        ``candles``/``atr_values`` are absolute-indexed and grow at the right;
        ``window_first_abs`` is the left edge of the active P1 window.
        """
        self.bar_count += 1
        self.counters.bars_processed += 1
        bar_start = self.counters.snapshot()

        # (1) retire trackers whose origin has left the active window
        stale = [key for key in self.trackers if key[0] < window_first_abs]
        for key in stale:
            del self.trackers[key]
        self.counters.pair_retirements += len(stale)

        # (2) advance every unresolved tracker — this is the ONLY unconditional
        #     per-candle work, and it is O(active unresolved trackers)
        changed = False
        for key, tracker in list(self.trackers.items()):
            if tracker.permanent:
                continue
            advanced = advance_tracker(tracker, candles, atr_values, self._config)
            self.advance_count += 1
            self.counters.tracker_advances += 1
            if advanced.confirming_abs != tracker.confirming_abs:
                # key[0] is the origin's absolute index, so a changed reaction
                # names exactly the origin whose fold has to be re-run.
                self._dirty_origins.add(key[0])
            if (
                advanced.reaction_start_abs is not None
                and tracker.reaction_start_abs is None
            ):
                self.counters.reaction_starts += 1
            if advanced.permanent and not tracker.permanent:
                self.counters.trackers_permanent += 1
                if advanced.confirming_abs is None:
                    self.counters.trackers_rejected += 1
                else:
                    self.counters.trackers_resolved += 1
            if advanced != tracker:
                self.trackers[key] = advanced
                if (
                    advanced.confirming_abs != tracker.confirming_abs
                    or advanced.permanent != tracker.permanent
                ):
                    changed = True

        # (3) the walk's output is a pure function of (swings, tracker
        #     resolutions), so skip it when neither moved
        swing_key = self._swing_key(swings)

        # swing-frontier delta, by semantic key (diagnostic only)
        now_keys = frozenset(swing_key)
        added = now_keys - self._prev_swing_keys
        removed = self._prev_swing_keys - now_keys
        if added or removed:
            self.counters.swing_frontier_changes += 1
            self.counters.swings_added += len(added)
            self.counters.swings_removed += len(removed)
        self.counters.swings_unchanged += len(now_keys & self._prev_swing_keys)
        self._prev_swing_keys = now_keys
        self.counters.max_active_trackers = max(
            self.counters.max_active_trackers, len(self.trackers)
        )

        if not self._first_bar and not changed and swing_key == self._cached_swing_key:
            self.per_bar.append(self._bar_delta(bar_start))
            return self._cached
        self._first_bar = False
        self._cached_swing_key = swing_key
        self._cached = self._walk(
            candles, atr_values, swings, window_first_abs, self._dirty_origins
        )
        self._dirty_origins = set()
        self.walk_count += 1
        self.counters.walks += 1
        self.counters.published_zones += len(self._cached)
        self.per_bar.append(self._bar_delta(bar_start))
        return self._cached

    def _bar_delta(self, before: dict[str, int]) -> dict[str, int]:
        after = self.counters.snapshot()
        return {k: after[k] - before[k] for k in after}

    def _invalidate_from_delta(
        self,
        swings: tuple[ConfirmedSwing, ...],
        index_by_id: dict[UUID, int],
    ) -> None:
        """Drop only the per-origin folds a swing delta can actually change.

        Adding or removing a swing of the SAME type can only alter an origin's
        fold if that swing sits inside the origin's zone — the geometric test is
        the fold's first gate and depends on nothing else. A swing of the
        OPPOSITE type feeds the has-opposite-between test for every origin of
        that orientation, so it invalidates the orientation. Everything else
        survives.
        """
        now = {str(swing.record_id): swing for swing in swings}
        changed_keys = set(now) ^ set(self._prev_swings)
        if not changed_keys:
            self._prev_swings = now
            return
        changed = [
            now.get(key) or self._prev_swings[key] for key in sorted(changed_keys)
        ]
        self._prev_swings = now

        surviving = {str(swing.record_id) for swing in swings}
        for zone_type, origin_type in (
            (SupportResistanceType.SUPPORT, SwingType.SWING_LOW),
            (SupportResistanceType.RESISTANCE, SwingType.SWING_HIGH),
        ):
            is_support = zone_type == SupportResistanceType.SUPPORT
            same_type_delta = [s for s in changed if s.swing_type == origin_type]
            opposite_delta = [s for s in changed if s.swing_type != origin_type]

            if opposite_delta:
                # the has-opposite test changed for the whole orientation
                for key in [k for k in self._origin_fold if k[0] == zone_type.value]:
                    del self._origin_fold[key]
                    self.counters.folds_invalidated_by_delta += 1
                continue
            if not same_type_delta:
                continue

            for key in list(self._origin_fold):
                if key[0] != zone_type.value:
                    continue
                origin_id = key[1]
                if origin_id not in surviving:
                    del self._origin_fold[key]
                    self.counters.folds_invalidated_by_delta += 1
                    continue
                origin = now[origin_id]
                _, zone_top, zone_bottom = _zone_bounds(
                    origin, is_support, self._config
                )
                touch_tol = (
                    self._config.support_resistance_touch_tolerance_atr_multiplier
                    * origin.pivot_reference_atr
                )
                pierce_tol = (
                    self._config.support_resistance_pierce_tolerance_atr_multiplier
                    * origin.pivot_reference_atr
                )
                affected = False
                for swing in same_type_delta:
                    self.counters.delta_geometry_tests += 1
                    if is_support:
                        inside = (
                            swing.pivot_price <= zone_top + touch_tol
                            and swing.pivot_price >= zone_bottom - pierce_tol
                        )
                    else:
                        inside = (
                            swing.pivot_price >= zone_bottom - touch_tol
                            and swing.pivot_price <= zone_top + pierce_tol
                        )
                    if inside:
                        affected = True
                        break
                if affected:
                    del self._origin_fold[key]
                    self.counters.folds_invalidated_by_delta += 1

    def _walk(
        self,
        candles: list[NormalizedCandle],
        atr_values: list[Decimal | None],
        swings: tuple[ConfirmedSwing, ...],
        window_first_abs: int,
        dirty: set[int] | None = None,
    ) -> tuple[Zone, ...]:
        dirty = set() if dirty is None else dirty
        index_by_id = {candle.record_id: i for i, candle in enumerate(candles)}
        results: list[_Resolved] = []
        self.counters.temp_allocations += 1

        # P1-SR-PERF-3: the orientation lists are pure functions of the swing
        # set, so they survive a walk that fired because a reaction resolved.
        # When the swing set DOES change, the lists are rebuilt but the per-origin
        # folds are invalidated by DELTA rather than wholesale — see
        # _invalidate_from_delta.
        swing_identity = self._swing_key(swings)
        if self._orientation_key != swing_identity:
            self._orientation_cache = {}
            self._orientation_key = swing_identity
            self._invalidate_from_delta(swings, index_by_id)

        for zone_type, origin_type in (
            (SupportResistanceType.SUPPORT, SwingType.SWING_LOW),
            (SupportResistanceType.RESISTANCE, SwingType.SWING_HIGH),
        ):
            opposite_type = (
                SwingType.SWING_HIGH
                if origin_type == SwingType.SWING_LOW
                else SwingType.SWING_LOW
            )
            cached_lists = self._orientation_cache.get(zone_type.value)
            if cached_lists is None:
                origins = sorted(
                    (s for s in swings if s.swing_type == origin_type),
                    key=lambda s: s.meaningful_confirmation_time_utc,
                )
                opposite_times = sorted(
                    s.meaningful_confirmation_time_utc
                    for s in swings
                    if s.swing_type == opposite_type
                )
                self._orientation_cache[zone_type.value] = (origins, opposite_times)
                self.counters.orientation_rebuilds += 1
                self.counters.sort_invocations += 2
                self.counters.sorted_elements += len(origins) + len(opposite_times)
                self.counters.temp_allocations += 2
            else:
                origins, opposite_times = cached_lists
                self.counters.orientation_reuses += 1
            is_support = zone_type == SupportResistanceType.SUPPORT
            origin_count = len(origins)
            self.counters.potential_pairs += origin_count * max(0, origin_count - 1)

            for origin in origins:
                self.counters.origin_visits += 1
                origin_abs = index_by_id[origin.pivot_candle_record_ids[-1]]
                fold_key = (zone_type.value, str(origin.record_id))

                # Reuse this origin's previous fold unless one of ITS reactions
                # moved. Nothing else in the fold can change while the swing set
                # is fixed: geometry, ordering and the opposite-swing test are
                # all swing-derived.
                if fold_key in self._origin_fold and origin_abs not in dirty:
                    self.counters.origin_folds_reused += 1
                    cached_result = self._origin_fold[fold_key]
                    if cached_result is not None:
                        results.append(cached_result)
                    continue
                self.counters.origin_folds_recomputed += 1
                self.counters.origin_reaction_lookups += 1

                _, zone_top, zone_bottom = _zone_bounds(
                    origin, is_support, self._config
                )

                origin_tracker = self._tracker_for(
                    origin_abs,
                    origin_abs + 1,
                    zone_top,
                    zone_bottom,
                    is_support,
                    candles,
                    atr_values,
                )
                if origin_tracker.confirming_abs is None:
                    self._origin_fold[fold_key] = None
                    continue

                touch_tol = (
                    self._config.support_resistance_touch_tolerance_atr_multiplier
                    * origin.pivot_reference_atr
                )
                pierce_tol = (
                    self._config.support_resistance_pierce_tolerance_atr_multiplier
                    * origin.pivot_reference_atr
                )
                qualifying: list[ConfirmedSwing] = []
                first_confirming_abs: int | None = None
                last_touch_time = origin.meaningful_confirmation_time_utc
                cursor = 0

                for touch in origins:
                    self.counters.actual_pair_visits += 1
                    if touch.record_id == origin.record_id:
                        continue
                    if touch.meaningful_confirmation_time_utc <= last_touch_time:
                        continue
                    if is_support:
                        geometric_ok = (
                            touch.pivot_price <= zone_top + touch_tol
                            and touch.pivot_price >= zone_bottom - pierce_tol
                        )
                    else:
                        geometric_ok = (
                            touch.pivot_price >= zone_bottom - touch_tol
                            and touch.pivot_price <= zone_top + pierce_tol
                        )
                    if not geometric_ok:
                        continue
                    while (
                        cursor < len(opposite_times)
                        and opposite_times[cursor] <= last_touch_time
                    ):
                        cursor += 1
                        self.counters.opposite_cursor_steps += 1
                    has_opposite = (
                        cursor < len(opposite_times)
                        and opposite_times[cursor]
                        < touch.meaningful_confirmation_time_utc
                    )
                    if not has_opposite:
                        continue
                    touch_abs = index_by_id[touch.pivot_candle_record_ids[-1]]
                    touch_tracker = self._tracker_for(
                        origin_abs,
                        touch_abs + 1,
                        zone_top,
                        zone_bottom,
                        is_support,
                        candles,
                        atr_values,
                    )
                    if touch_tracker.confirming_abs is None:
                        continue
                    qualifying.append(touch)
                    if first_confirming_abs is None:
                        first_confirming_abs = touch_tracker.confirming_abs
                    last_touch_time = touch.meaningful_confirmation_time_utc

                if first_confirming_abs is None:
                    self._origin_fold[fold_key] = None
                    continue
                resolved = _Resolved(
                    zone_type=zone_type.value,
                    origin_id=str(origin.record_id),
                    zone_top=zone_top,
                    zone_bottom=zone_bottom,
                    touch_ids=tuple(str(t.record_id) for t in qualifying),
                    confirmation_time=candles[
                        first_confirming_abs
                    ].availability_time_utc,
                )
                self._origin_fold[fold_key] = resolved
                results.append(resolved)

        self.counters.resolved_zones += len(results)
        self.counters.sort_invocations += 1
        self.counters.sorted_elements += len(results)
        results.sort(key=lambda r: r.confirmation_time)
        return tuple(r.as_zone() for r in results)


# ---------------------------------------------------------------------------
# Harness
# ---------------------------------------------------------------------------


def _window(
    candles: tuple[NormalizedCandle, ...], end: int, lookback: int
) -> tuple[int, list[NormalizedCandle]]:
    first = max(0, end - lookback)
    return first, list(candles[first:end])


def _swings_in_window(
    swings: tuple[ConfirmedSwing, ...], window: list[NormalizedCandle]
) -> tuple[ConfirmedSwing, ...]:
    present = {candle.record_id for candle in window}
    return tuple(
        s for s in swings if all(rid in present for rid in s.pivot_candle_record_ids)
    )


def run_prefixes(
    candles: tuple[NormalizedCandle, ...],
    swings: tuple[ConfirmedSwing, ...],
    *,
    lookback: int = _LOOKBACK,
    start: int = 1,
) -> tuple[SRFrontier, list[tuple[int, tuple[Zone, ...], tuple[Zone, ...]]]]:
    """Drive oracle and model over every prefix; return per-prefix results."""
    atr_full = list(compute_atr_series(candles, _CONFIG.atr_period))
    frontier = SRFrontier(_CONFIG, lookback=lookback)
    rows: list[tuple[int, tuple[Zone, ...], tuple[Zone, ...]]] = []
    for end in range(start, len(candles) + 1):
        first, window = _window(candles, end, lookback)
        atr_window = atr_full[first:end]
        in_window = _swings_in_window(swings, window)
        oracle = _batch_walk(tuple(window), tuple(atr_window), in_window, _CONFIG)
        model = frontier.advance(list(candles[:end]), atr_full[:end], in_window, first)
        # the model is absolute-indexed; the oracle is window-indexed. Both
        # project to the same UUID/time content, so they compare directly.
        rows.append((end, oracle, model))
    return frontier, rows


def assert_prefix_equality(
    candles: tuple[NormalizedCandle, ...],
    swings: tuple[ConfirmedSwing, ...],
    *,
    lookback: int = _LOOKBACK,
    label: str = "",
) -> SRFrontier:
    frontier, rows = run_prefixes(candles, swings, lookback=lookback)
    for end, oracle, model in rows:
        assert model == oracle, (
            f"{label} frontier diverged at prefix {end}\n"
            f"  expected (oracle): {oracle}\n"
            f"  actual   (model) : {model}"
        )
    return frontier


# ---------------------------------------------------------------------------
# Fixtures for the required scenario matrix
# ---------------------------------------------------------------------------

_OHLC = tuple[float, float, float, float]

_FLAT: list[_OHLC] = [(100.0, 101.0, 99.0, 100.0)] * 20
_SUPPORT_ORIGIN: list[_OHLC] = [(100.0, 101.0, 96.0, 100.0)]
_STRONG_REACTION: list[_OHLC] = [
    (96.5, 98.0, 96.3, 97.8),
    (97.8, 100.0, 97.5, 99.8),
    (99.8, 102.0, 99.6, 101.8),
    (101.8, 104.0, 101.6, 103.8),
    (103.8, 106.0, 103.6, 105.8),
]
_GAP: list[_OHLC] = [(100.0, 101.0, 99.0, 100.0)] * 10
_SUPPORT_TOUCH: list[_OHLC] = [(100.0, 101.0, 96.05, 100.0)]
_TOUCH_REACTION: list[_OHLC] = [
    (96.55, 98.0, 96.35, 97.85),
    (97.85, 100.0, 97.55, 99.85),
    (99.85, 102.0, 99.65, 101.85),
    (101.85, 104.0, 101.65, 103.85),
    (103.85, 106.0, 103.65, 105.85),
]
_TAIL: list[_OHLC] = [(100.0, 101.0, 99.0, 100.0)] * 3
# A breach that never develops: closes creep just past the zone top and stall.
_WEAK_REACTION: list[_OHLC] = [
    (96.1, 96.35, 96.0, 96.3),
    (96.3, 96.4, 96.2, 96.32),
    (96.32, 96.42, 96.25, 96.34),
    (96.34, 96.44, 96.28, 96.36),
    (96.36, 96.46, 96.3, 96.38),
]
# Price pinned at/below the zone top: no close ever breaches, so no reaction.
_NO_BREACH: list[_OHLC] = [(96.05, 96.1, 95.9, 96.0)] * 12


def _build(prices: list[_OHLC]) -> tuple[NormalizedCandle, ...]:
    return tuple(_candle(i, *p) for i, p in enumerate(prices))


def _classic_support() -> tuple[
    tuple[NormalizedCandle, ...], tuple[ConfirmedSwing, ...]
]:
    prices = (
        _FLAT
        + _SUPPORT_ORIGIN
        + _STRONG_REACTION
        + _GAP
        + _SUPPORT_TOUCH
        + _TOUCH_REACTION
        + _TAIL
    )
    candles = _build(prices)
    swings = (
        _swing(1, SwingType.SWING_LOW, "96", 20, candles),
        _swing(3, SwingType.SWING_HIGH, "106", 25, candles),
        _swing(2, SwingType.SWING_LOW, "96.05", 36, candles),
    )
    return candles, swings


# ---------------------------------------------------------------------------
# The oracle transcription itself must not drift from production
# ---------------------------------------------------------------------------


def test_batch_walk_transcription_matches_production() -> None:
    """_batch_walk == detect_support_resistance_zones when ATR seeding agrees.

    Over a window that starts at candle 0 the injected full-history ATR is the
    same series production derives internally, so any difference would be a
    transcription error in the walk rather than an ATR artefact.
    """
    candles, swings = _classic_support()
    atr = compute_atr_series(candles, _CONFIG.atr_period)
    for end in range(1, len(candles) + 1):
        prefix = candles[:end]
        in_window = _swings_in_window(swings, list(prefix))
        mine = _batch_walk(prefix, atr[:end], in_window, _CONFIG)
        theirs = tuple(
            _project(z)
            for z in detect_support_resistance_zones(prefix, in_window, _CONFIG)
        )
        assert mine == theirs, f"walk transcription differs at prefix {end}"


# ---------------------------------------------------------------------------
# Scenario matrix — every case compared on EVERY prefix
# ---------------------------------------------------------------------------


def test_case_01_no_candidate_at_all() -> None:
    candles = _build(_FLAT + _STRONG_REACTION)
    assert_prefix_equality(candles, (), label="no-candidate")


def test_case_02_candidate_but_no_reaction_start() -> None:
    candles = _build(_FLAT + _SUPPORT_ORIGIN + _NO_BREACH)
    swings = (_swing(1, SwingType.SWING_LOW, "96", 20, candles),)
    assert_prefix_equality(candles, swings, label="no-reaction-start")


def test_case_03_reaction_starts_on_first_possible_candle() -> None:
    candles, swings = _classic_support()
    assert_prefix_equality(candles, swings, label="immediate-reaction")


def test_case_04_reaction_starts_several_candles_later() -> None:
    prices = (
        _FLAT
        + _SUPPORT_ORIGIN
        + _NO_BREACH
        + _STRONG_REACTION
        + _GAP
        + _SUPPORT_TOUCH
        + _TOUCH_REACTION
        + _TAIL
    )
    candles = _build(prices)
    swings = (
        _swing(1, SwingType.SWING_LOW, "96", 20, candles),
        _swing(3, SwingType.SWING_HIGH, "106", 37, candles),
        _swing(2, SwingType.SWING_LOW, "96.05", 48, candles),
    )
    assert_prefix_equality(candles, swings, label="delayed-reaction")


def test_case_05_06_07_reaction_window_fills_without_any_new_swing() -> None:
    """Partial fill, then exact resolution at the window boundary."""
    candles, swings = _classic_support()
    _, rows = run_prefixes(candles, swings)
    for end, oracle, model in rows:
        assert model == oracle, f"diverged at prefix {end}"
    published = [end for end, oracle, _ in rows if oracle]
    assert published, "fixture never publishes"
    assert published[0] > 37, "flip must land after the last swing pivot"


def test_case_08_09_qualifying_and_non_qualifying_reactions() -> None:
    qualifying, swings = _classic_support()
    assert_prefix_equality(qualifying, swings, label="qualifying")

    weak = _build(_FLAT + _SUPPORT_ORIGIN + _WEAK_REACTION + _TAIL)
    weak_swings = (_swing(1, SwingType.SWING_LOW, "96", 20, weak),)
    assert_prefix_equality(weak, weak_swings, label="non-qualifying")
    atr = compute_atr_series(weak, _CONFIG.atr_period)
    in_window = _swings_in_window(weak_swings, list(weak))
    assert _batch_walk(weak, atr, in_window, _CONFIG) == (), (
        "the weak fixture must not publish, or case 9 proves nothing"
    )


def test_case_10_11_12_multiple_trackers_origins_and_touches() -> None:
    prices = (
        _FLAT
        + _SUPPORT_ORIGIN
        + _STRONG_REACTION
        + _GAP
        + _SUPPORT_TOUCH
        + _TOUCH_REACTION
        + _GAP
        + _SUPPORT_TOUCH
        + _TOUCH_REACTION
        + _TAIL
    )
    candles = _build(prices)
    swings = (
        _swing(1, SwingType.SWING_LOW, "96", 20, candles),
        _swing(3, SwingType.SWING_HIGH, "106", 25, candles),
        _swing(2, SwingType.SWING_LOW, "96.05", 36, candles),
        _swing(5, SwingType.SWING_HIGH, "106", 41, candles),
        _swing(4, SwingType.SWING_LOW, "96.05", 52, candles),
    )
    frontier = assert_prefix_equality(candles, swings, label="multi")
    assert len(frontier.trackers) >= 2, "expected several concurrent trackers"


def test_case_13_14_15_rejection_permanence_and_stability_after() -> None:
    candles = _build(_FLAT + _SUPPORT_ORIGIN + _WEAK_REACTION + _FLAT + _TAIL)
    swings = (_swing(1, SwingType.SWING_LOW, "96", 20, candles),)
    frontier = assert_prefix_equality(candles, swings, label="rejected")
    trackers = list(frontier.trackers.values())
    assert trackers, "expected a tracker to have been created"
    assert all(t.permanent for t in trackers), (
        "a resolved reaction window must become permanent"
    )
    assert all(t.confirming_abs is None for t in trackers), (
        "the weak reaction must stay rejected"
    )


def test_case_16_new_swing_while_an_older_tracker_is_unresolved() -> None:
    prices = (
        _FLAT
        + _SUPPORT_ORIGIN
        + _NO_BREACH
        + _STRONG_REACTION
        + _GAP
        + _SUPPORT_TOUCH
        + _TOUCH_REACTION
        + _TAIL
    )
    candles = _build(prices)
    swings = (
        _swing(1, SwingType.SWING_LOW, "96", 20, candles),
        _swing(3, SwingType.SWING_HIGH, "106", 24, candles),
        _swing(2, SwingType.SWING_LOW, "96.05", 48, candles),
    )
    assert_prefix_equality(candles, swings, label="swing-during-unresolved")


def test_case_17_same_swing_set_across_the_bars_that_resolve_the_reaction() -> None:
    candles, swings = _classic_support()
    _, rows = run_prefixes(candles, swings)
    tail = [(end, oracle) for end, oracle, _ in rows if end >= 38]
    assert any(oracle for _, oracle in tail), "expected a publication in the tail"
    assert any(not oracle for _, oracle in tail), (
        "expected the tail to contain the pre-publication bars too"
    )


def test_case_18_to_21_rolling_window_edge_and_eviction() -> None:
    """A short lookback forces origin/touch eviction inside a small fixture.

    The frontier must keep publishing while the objects are in range and stop
    once the origin falls out — the same code path the 300-bar contract takes,
    just reached sooner.
    """
    candles, swings = _classic_support()
    for lookback in (14, 16, 18, 25, 30, 40, 45):
        frontier = assert_prefix_equality(
            candles, swings, lookback=lookback, label=f"lookback={lookback}"
        )
        assert all(key[0] >= 0 for key in frontier.trackers), "corrupt tracker key"
    # lookback 14 evicts the origin (pivot 20) well before the zone would
    # publish around prefix 39, so the outcome must genuinely differ.
    _, short = run_prefixes(candles, swings, lookback=14)
    _, long_run = run_prefixes(candles, swings, lookback=_LOOKBACK)
    assert not any(o for _, o, _ in short), (
        "with the origin evicted nothing may publish"
    )
    assert any(o for _, o, _ in long_run), (
        "the full-lookback run must publish, or eviction is untested"
    )


def test_case_22_deterministic_zone_ordering_is_preserved() -> None:
    """Support and resistance resolving together must come out time-ordered."""
    prices = (
        _FLAT
        + _SUPPORT_ORIGIN
        + _STRONG_REACTION
        + _GAP
        + _SUPPORT_TOUCH
        + _TOUCH_REACTION
        + _TAIL
    )
    candles = _build(prices)
    swings = (
        _swing(1, SwingType.SWING_LOW, "96", 20, candles),
        _swing(3, SwingType.SWING_HIGH, "106", 25, candles),
        _swing(2, SwingType.SWING_LOW, "96.05", 36, candles),
        _swing(6, SwingType.SWING_HIGH, "105.8", 29, candles),
        _swing(7, SwingType.SWING_LOW, "96.0", 31, candles),
        _swing(8, SwingType.SWING_HIGH, "105.85", 41, candles),
    )
    _, rows = run_prefixes(candles, swings)
    for end, oracle, model in rows:
        assert model == oracle, f"diverged at prefix {end}"
        times = [zone[5] for zone in model]
        assert times == sorted(times), f"zone ordering broken at prefix {end}"


# ---------------------------------------------------------------------------
# Seeded property coverage
# ---------------------------------------------------------------------------


def _random_stream(
    seed: int, length: int, swing_count: int
) -> tuple[tuple[NormalizedCandle, ...], tuple[ConfirmedSwing, ...]]:
    rng = random.Random(seed)
    prices: list[_OHLC] = []
    level = 100.0
    for _ in range(length):
        level += rng.uniform(-1.2, 1.2)
        span = rng.uniform(0.2, 2.5)
        open_ = level + rng.uniform(-span / 2, span / 2)
        close = level + rng.uniform(-span / 2, span / 2)
        high = max(open_, close) + rng.uniform(0.0, span)
        low = min(open_, close) - rng.uniform(0.0, span)
        prices.append((open_, high, low, close))
    candles = _build(prices)

    pivots = sorted(rng.sample(range(20, length - 8), swing_count))
    swings: list[ConfirmedSwing] = []
    for order, pivot in enumerate(pivots):
        is_low = rng.random() < 0.5
        price = candles[pivot].low if is_low else candles[pivot].high
        swings.append(
            _swing(
                1000 + order,
                SwingType.SWING_LOW if is_low else SwingType.SWING_HIGH,
                str(price),
                pivot,
                candles,
                reference_atr=str(round(rng.uniform(0.8, 3.0), 3)),
                confirmation_offset_minutes=rng.randint(3, 9),
            )
        )
    return candles, tuple(swings)


def test_property_frontier_matches_oracle_on_seeded_streams() -> None:
    """Every prefix of every seeded stream must agree with the oracle."""
    for seed in (1, 2, 3, 5, 8, 13, 21, 34):
        candles, swings = _random_stream(seed, length=160, swing_count=10)
        _, rows = run_prefixes(candles, swings, lookback=60)
        for end, oracle, model in rows:
            assert model == oracle, (
                f"seed={seed} prefix={end}\n  expected: {oracle}\n  actual  : {model}"
            )


def test_property_frontier_matches_oracle_across_the_300_bar_rollover() -> None:
    """A stream longer than the real contract, at the real lookback."""
    candles, swings = _random_stream(101, length=420, swing_count=26)
    _, rows = run_prefixes(candles, swings, lookback=_LOOKBACK)
    assert any(end > _LOOKBACK for end, _, _ in rows), "rollover not exercised"
    for end, oracle, model in rows:
        assert model == oracle, (
            f"300-bar rollover prefix={end}\n  expected: {oracle}\n  actual  : {model}"
        )


# ---------------------------------------------------------------------------
# Design preconditions and the work-avoidance claim
# ---------------------------------------------------------------------------


def test_frontier_requires_position_stable_atr() -> None:
    """The frontier pins atr[reaction_start]; a re-seeded ATR would break it.

    Production ``detect_support_resistance_zones`` re-derives ATR from the first
    candle of whatever slice it is given, so under a sliding window the value at
    a fixed bar moves. This documents that difference — Pine's ATR advances from
    the start of the chart, which is why the design holds there.
    """
    candles, _ = _random_stream(3, length=80, swing_count=4)
    full = compute_atr_series(candles, _CONFIG.atr_period)
    shifted = compute_atr_series(candles[5:], _CONFIG.atr_period)
    same_bar_full = full[40]
    same_bar_shifted = shifted[35]
    assert same_bar_full is not None and same_bar_shifted is not None
    assert same_bar_full != same_bar_shifted, (
        "if re-seeding ever stopped changing the ATR at a fixed bar, the "
        "full-history-ATR precondition could be relaxed"
    )


def test_frontier_skips_the_walk_on_most_bars() -> None:
    """The complexity claim: the walk is event-driven, not per-bar."""
    candles, swings = _classic_support()
    frontier, _ = run_prefixes(candles, swings)
    assert frontier.bar_count == len(candles)
    assert frontier.walk_count < frontier.bar_count, (
        "the frontier ran the walk on every bar — no work was avoided"
    )


def test_frontier_state_stays_bounded_by_the_window() -> None:
    """Tracker state must not grow without bound as the chart runs."""
    candles, swings = _random_stream(7, length=420, swing_count=26)
    frontier, _ = run_prefixes(candles, swings, lookback=_LOOKBACK)
    origins = {key[0] for key in frontier.trackers}
    assert all(origin >= len(candles) - _LOOKBACK for origin in origins), (
        "a tracker survived past its origin leaving the window"
    )


# ===========================================================================
# P1-SR-ORDERING — final result ordering and published-zone selection
#
# support_resistance.py:303 closes the detector with a STABLE ascending sort on
# confirmation_time_utc, and _finalize (analyzer.py:236-276) appends in candidate
# order without re-sorting, so that sequence is the canonical Python order.
# Nothing downstream selects a single "current" zone — POI iterates the whole
# tuple (poi/reference_zones.py:32).
#
# The Pine parity scalars P1_sr_top / P1_sr_bottom publish ONE zone: the last
# element of the resolved array, i.e. "the most recently confirmed zone" under
# that canonical order. Pine had no final sort, so its last element was instead
# "the last RESISTANCE zone by origin order" — a different zone whenever both
# directions qualify and the resistance one confirmed first.
# ===========================================================================

_ORD_ONE: list[_OHLC] = [(100.0, 101.0, 99.0, 100.0)]
_ORD_RES_ORIGIN: list[_OHLC] = [(100.0, 104.0, 99.0, 100.0)]
_ORD_RES_REACTION: list[_OHLC] = [
    (103.5, 103.7, 102.0, 102.2),
    (102.2, 102.5, 100.0, 100.2),
    (100.2, 100.4, 98.0, 98.2),
    (98.2, 98.4, 96.0, 96.2),
    (96.2, 96.4, 94.0, 94.2),
]
_ORD_RES_TOUCH: list[_OHLC] = [(100.0, 103.95, 99.0, 100.0)]
_ORD_RES_TOUCH_REACTION: list[_OHLC] = [
    (103.45, 103.65, 101.95, 102.15),
    (102.15, 102.45, 99.95, 100.15),
    (100.15, 100.35, 97.95, 98.15),
    (98.15, 98.35, 95.95, 96.15),
    (96.15, 96.35, 93.95, 94.15),
]


def _both_directions() -> tuple[
    tuple[NormalizedCandle, ...], tuple[ConfirmedSwing, ...]
]:
    """A resistance zone confirming EARLY and a support zone confirming LATE.

    That combination is what separates the two orderings: the walk emits support
    first, so the unsorted last element is the older resistance zone while the
    canonical last element is the newer support zone.
    """
    prices = (
        _ORD_ONE * 20  # 0..19
        + _ORD_RES_ORIGIN  # 20
        + _ORD_RES_REACTION  # 21..25
        + _ORD_ONE * 5  # 26..30
        + _ORD_RES_TOUCH  # 31
        + _ORD_RES_TOUCH_REACTION  # 32..36
        + _ORD_ONE * 3  # 37..39
        + _SUPPORT_ORIGIN  # 40
        + _STRONG_REACTION  # 41..45
        + _ORD_ONE * 5  # 46..50
        + _SUPPORT_TOUCH  # 51
        + _TOUCH_REACTION  # 52..56
        + _ORD_ONE * 3  # 57..59
    )
    candles = _build(prices)
    swings = (
        _swing(1, SwingType.SWING_HIGH, "104", 20, candles),
        _swing(2, SwingType.SWING_LOW, "94", 25, candles),
        _swing(3, SwingType.SWING_HIGH, "103.95", 31, candles),
        _swing(4, SwingType.SWING_LOW, "96", 40, candles),
        _swing(5, SwingType.SWING_HIGH, "106", 45, candles),
        _swing(6, SwingType.SWING_LOW, "96.05", 51, candles),
    )
    return candles, swings


def _canonical(
    candles: tuple[NormalizedCandle, ...], swings: tuple[ConfirmedSwing, ...]
) -> tuple[Zone, ...]:
    atr = compute_atr_series(candles, _CONFIG.atr_period)
    return _batch_walk(candles, atr, _swings_in_window(swings, list(candles)), _CONFIG)


def _insertion(
    candles: tuple[NormalizedCandle, ...], swings: tuple[ConfirmedSwing, ...]
) -> tuple[Zone, ...]:
    atr = compute_atr_series(candles, _CONFIG.atr_period)
    return _batch_walk_insertion_order(
        candles, atr, _swings_in_window(swings, list(candles)), _CONFIG
    )


def _assert_selection_matches_oracle(
    candles: tuple[NormalizedCandle, ...],
    swings: tuple[ConfirmedSwing, ...],
    *,
    lookback: int = _LOOKBACK,
    label: str = "",
) -> list[tuple[int, tuple[Zone, ...], tuple[Zone, ...]]]:
    """Model published zone == oracle published zone on EVERY prefix."""
    _, rows = run_prefixes(candles, swings, lookback=lookback)
    for end, oracle, model in rows:
        assert selected_zone(model) == selected_zone(oracle), (
            f"{label} published zone diverged at prefix {end}\n"
            f"  expected: {selected_zone(oracle)}\n"
            f"  actual  : {selected_zone(model)}"
        )
        times = [zone[5] for zone in model]
        assert times == sorted(times), f"{label} order broken at prefix {end}"
    return rows


def test_ordering_fixture_really_produces_both_directions() -> None:
    """Guard the guard: without two zones the divergence proves nothing."""
    candles, swings = _both_directions()
    zones = _canonical(candles, swings)
    assert len(zones) == 2, f"expected one zone per direction, got {len(zones)}"
    assert {zone[0] for zone in zones} == {"SUPPORT", "RESISTANCE"}


def test_documents_the_ordering_defect_pine_had() -> None:
    """Unsorted-last and canonical-last are genuinely different zones here.

    This is what made the missing final sort a semantic defect rather than a
    cosmetic one: the two orders disagree about which zone gets published.
    """
    candles, swings = _both_directions()
    canonical = _canonical(candles, swings)
    insertion = _insertion(candles, swings)

    assert sorted(canonical) == sorted(insertion), (
        "the two orders must contain the SAME zones — only the order differs"
    )
    assert selected_zone(insertion) != selected_zone(canonical), (
        "expected the pre-sort order to publish a different zone"
    )
    canonical_pick = selected_zone(canonical)
    insertion_pick = selected_zone(insertion)
    assert canonical_pick is not None and insertion_pick is not None
    assert canonical_pick[0] == "SUPPORT"
    assert insertion_pick[0] == "RESISTANCE"
    assert insertion_pick[5] < canonical_pick[5], (
        "the zone Pine used to publish should be the OLDER of the two"
    )


def test_random_streams_could_not_have_caught_the_ordering_defect() -> None:
    """Why §14's property coverage missed it: it never makes two zones."""
    multi = 0
    for seed in (1, 2, 3, 5, 8):
        candles, swings = _random_stream(seed, length=160, swing_count=12)
        atr = list(compute_atr_series(candles, _CONFIG.atr_period))
        for end in range(30, len(candles) + 1, 7):
            first = max(0, end - 60)
            window = list(candles[first:end])
            zones = _batch_walk(
                tuple(window),
                tuple(atr[first:end]),
                _swings_in_window(swings, window),
                _CONFIG,
            )
            multi += len(zones) >= 2
    assert multi == 0, (
        "the seeded streams now DO produce multi-zone states — the ordering "
        "tests below should be extended to use them"
    )


def test_ordering_case_01_single_support_result() -> None:
    candles, swings = _classic_support()
    _assert_selection_matches_oracle(candles, swings, label="single-support")


def test_ordering_case_02_two_support_results() -> None:
    prices = (
        _FLAT
        + _SUPPORT_ORIGIN
        + _STRONG_REACTION
        + _GAP
        + _SUPPORT_TOUCH
        + _TOUCH_REACTION
        + _GAP
        + _SUPPORT_TOUCH
        + _TOUCH_REACTION
        + _TAIL
    )
    candles = _build(prices)
    swings = (
        _swing(1, SwingType.SWING_LOW, "96", 20, candles),
        _swing(2, SwingType.SWING_HIGH, "106", 25, candles),
        _swing(3, SwingType.SWING_LOW, "96.05", 36, candles),
        _swing(4, SwingType.SWING_HIGH, "106", 41, candles),
        _swing(5, SwingType.SWING_LOW, "96.05", 52, candles),
    )
    _assert_selection_matches_oracle(candles, swings, label="two-support")


def test_ordering_case_03_two_resistance_results() -> None:
    prices = (
        _ORD_ONE * 20
        + _ORD_RES_ORIGIN
        + _ORD_RES_REACTION
        + _ORD_ONE * 10
        + _ORD_RES_TOUCH
        + _ORD_RES_TOUCH_REACTION
        + _ORD_ONE * 10
        + _ORD_RES_TOUCH
        + _ORD_RES_TOUCH_REACTION
        + _ORD_ONE * 3
    )
    candles = _build(prices)
    swings = (
        _swing(1, SwingType.SWING_HIGH, "104", 20, candles),
        _swing(2, SwingType.SWING_LOW, "94", 25, candles),
        _swing(3, SwingType.SWING_HIGH, "103.95", 36, candles),
        _swing(4, SwingType.SWING_LOW, "94", 41, candles),
        _swing(5, SwingType.SWING_HIGH, "103.95", 52, candles),
    )
    _assert_selection_matches_oracle(candles, swings, label="two-resistance")


def test_ordering_case_04_support_and_resistance_simultaneously() -> None:
    candles, swings = _both_directions()
    rows = _assert_selection_matches_oracle(candles, swings, label="both-directions")
    assert any(len(model) == 2 for _, _, model in rows), (
        "the fixture must reach a state with both directions published"
    )


def test_ordering_case_05_three_competing_results_per_direction() -> None:
    prices = (
        _FLAT
        + _SUPPORT_ORIGIN
        + _STRONG_REACTION
        + _ORD_ONE * 8
        + _SUPPORT_TOUCH
        + _TOUCH_REACTION
        + _ORD_ONE * 8
        + _SUPPORT_TOUCH
        + _TOUCH_REACTION
        + _ORD_ONE * 8
        + _SUPPORT_TOUCH
        + _TOUCH_REACTION
        + _TAIL
    )
    candles = _build(prices)
    swings = (
        _swing(1, SwingType.SWING_LOW, "96", 20, candles),
        _swing(2, SwingType.SWING_HIGH, "106", 25, candles),
        _swing(3, SwingType.SWING_LOW, "96.05", 34, candles),
        _swing(4, SwingType.SWING_HIGH, "106", 39, candles),
        _swing(5, SwingType.SWING_LOW, "96.05", 48, candles),
        _swing(6, SwingType.SWING_HIGH, "106", 53, candles),
        _swing(7, SwingType.SWING_LOW, "96.05", 62, candles),
    )
    _assert_selection_matches_oracle(candles, swings, label="three-competing")


def test_ordering_case_06_equal_timestamps_keep_insertion_order() -> None:
    """Python's sort is stable, so ties fall back to the walk's own order.

    The composite (confirmationTime, insertionIndex) key the Pine walk now uses
    reproduces that explicitly; this pins the expectation it must satisfy.
    """
    candles, swings = _both_directions()
    insertion = _insertion(candles, swings)
    assert len(insertion) == 2

    # Collapse the primary key so ONLY the stability rule decides the order.
    tied = list(enumerate(insertion))
    canonical_under_ties = [zone for _, zone in sorted(tied, key=lambda p: (0, p[0]))]
    assert canonical_under_ties == list(insertion), (
        "with all confirmation times equal the canonical order must be exactly "
        "the walk's insertion order — SUPPORT orientation first, then RESISTANCE"
    )


def test_ordering_case_07_window_removal_of_the_selected_result() -> None:
    """When the published zone's origin is evicted, the next one must take over."""
    candles, swings = _both_directions()
    for lookback in (18, 22, 26, 34, 45, _LOOKBACK):
        _assert_selection_matches_oracle(
            candles, swings, lookback=lookback, label=f"lookback={lookback}"
        )
    _, short = run_prefixes(candles, swings, lookback=18)
    _, full = run_prefixes(candles, swings, lookback=_LOOKBACK)
    assert [selected_zone(m) for _, _, m in short] != [
        selected_zone(m) for _, _, m in full
    ], "eviction must change the published zone, or the case is untested"


def test_ordering_case_08_09_newly_resolved_result_takes_over_only_when_it_should() -> (
    None
):
    """The later-confirming support zone must displace the earlier resistance."""
    candles, swings = _both_directions()
    _, rows = run_prefixes(candles, swings)
    seen_resistance = False
    seen_support_after = False
    for _, oracle, model in rows:
        assert selected_zone(model) == selected_zone(oracle)
        chosen = selected_zone(model)
        if chosen is not None and chosen[0] == "RESISTANCE":
            seen_resistance = True
        if seen_resistance and chosen is not None and chosen[0] == "SUPPORT":
            seen_support_after = True
    assert seen_resistance, "resistance must be published first"
    assert seen_support_after, (
        "the later-confirming support zone must become the published one"
    )


def test_ordering_case_10_candidate_retirement_clears_the_selection() -> None:
    """With every origin evicted, nothing may stay published."""
    candles, swings = _both_directions()
    _, rows = run_prefixes(candles, swings, lookback=8)
    for end, oracle, model in rows:
        assert selected_zone(model) == selected_zone(oracle), f"prefix {end}"
    assert all(model == () for _, _, model in rows), (
        "an 8-bar window cannot hold any origin, so nothing may publish"
    )


def test_ordering_case_11_identical_semantic_keys_deduplicate() -> None:
    """One origin yields exactly one zone, however many bars it survives."""
    candles, swings = _classic_support()
    _, rows = run_prefixes(candles, swings)
    for end, _, model in rows:
        origins = [zone[1] for zone in model]
        assert len(origins) == len(set(origins)), (
            f"prefix {end}: the same origin published twice — {origins}"
        )


def test_ordering_holds_across_the_300_bar_rollover() -> None:
    candles, swings = _random_stream(101, length=420, swing_count=26)
    _assert_selection_matches_oracle(candles, swings, label="rollover")


# ---------------------------------------------------------------------------
# P1-SR-PERF-3 — measured work characteristics of the CURRENT frontier.
#
# These are not aspirational. They pin what the implementation does today, so
# that the numbers quoted in the performance document stay honest and so a later
# pair-frontier change has a baseline to beat. Where the current architecture is
# known to be wasteful, the test says so plainly rather than asserting a property
# the code does not have.
# ---------------------------------------------------------------------------


def _dense_stream(
    seed: int = 4242, length: int = 900, swing_count: int = 60
) -> tuple[tuple[NormalizedCandle, ...], tuple[ConfirmedSwing, ...]]:
    return _random_stream(seed, length=length, swing_count=swing_count)


def test_tracker_advancement_is_cheap_and_unconditional() -> None:
    """The reaction frontier itself is not the cost.

    Advancing unresolved trackers is the only S/R work that must happen on every
    confirmed bar, and it stays at roughly one advance per bar.
    """
    candles, swings = _dense_stream()
    frontier, _ = run_prefixes(candles, swings, lookback=_LOOKBACK)
    counters = frontier.counters
    per_bar = counters.tracker_advances / counters.bars_processed
    assert per_bar < 5, f"tracker advances per bar unexpectedly high: {per_bar}"
    assert counters.tracker_advances > 0, "trackers never advanced"


def test_pair_frontier_reuses_folds_instead_of_re_enumerating() -> None:
    """The pair frontier must actually avoid re-deriving unchanged relationships.

    Before P1-SR-PERF-3 every walk re-ran every origin's fold. Now a fold is
    re-run only when one of ITS reactions moved, or when a swing delta can
    geometrically reach it. Both reuse paths must be exercised.
    """
    candles, swings = _dense_stream()
    frontier, _ = run_prefixes(candles, swings, lookback=_LOOKBACK)
    counters = frontier.counters
    assert counters.origin_folds_reused > 0, "no fold was ever reused"
    assert counters.orientation_reuses > 0, "orientation lists never reused"
    total_folds = counters.origin_folds_recomputed + counters.origin_folds_reused
    assert total_folds == counters.origin_visits, (
        "every origin visit must either recompute or reuse a fold"
    )
    reuse_share = counters.origin_folds_reused / total_folds
    assert reuse_share > 0.2, (
        f"fold reuse share {reuse_share:.2f} is too low to justify the frontier"
    )


def test_walk_does_not_fire_on_every_bar() -> None:
    """The swing/tracker change gate does avoid some work, just not enough."""
    candles, swings = _dense_stream()
    frontier, _ = run_prefixes(candles, swings, lookback=_LOOKBACK)
    counters = frontier.counters
    assert counters.walks < counters.bars_processed, "the gate saved nothing"


def test_pair_state_is_retired_as_the_window_slides() -> None:
    """Trackers must not accumulate once their origin leaves the window."""
    candles, swings = _dense_stream(length=1200, swing_count=80)
    frontier, _ = run_prefixes(candles, swings, lookback=_LOOKBACK)
    assert frontier.counters.pair_retirements > 0, "retirement never ran"


def test_state_stays_bounded_across_a_long_stream() -> None:
    """State size must track the 300-bar contract, not total history length."""
    short, short_swings = _dense_stream(length=700, swing_count=45)
    long_stream, long_swings = _dense_stream(seed=4243, length=2100, swing_count=135)

    short_frontier, _ = run_prefixes(short, short_swings, lookback=_LOOKBACK)
    long_frontier, _ = run_prefixes(long_stream, long_swings, lookback=_LOOKBACK)

    assert (
        long_frontier.counters.bars_processed
        >= 3 * short_frontier.counters.bars_processed
    )
    # tripling the stream must not triple the retained state
    assert long_frontier.counters.max_active_trackers < (
        3 * short_frontier.counters.max_active_trackers
    ), (
        "tracker state grew with total history instead of with the window: "
        f"{short_frontier.counters.max_active_trackers} -> "
        f"{long_frontier.counters.max_active_trackers}"
    )
    assert len(long_frontier.trackers) < 4 * _LOOKBACK, (
        f"live tracker count {len(long_frontier.trackers)} is not window-bounded"
    )


def test_counters_do_not_change_results() -> None:
    """Instrumentation must be inert: same fixture, same published zones."""
    candles, swings = _classic_support()
    _, rows = run_prefixes(candles, swings)
    for end, oracle, model in rows:
        assert model == oracle, f"counters perturbed the result at prefix {end}"


# ---------------------------------------------------------------------------
# Structured stress stream.
#
# The purely random stream above almost never satisfies the geometric touch test,
# so it exercises the frontier without ever publishing a zone — which would make
# a large campaign look impressive while proving very little. This generator
# tiles the zone-forming shape (origin dip, qualifying reaction, opposite swing,
# a second touch of the same level, its reaction) with seeded jitter, so
# publication, ordering, ties and retirement are all genuinely exercised.
# ---------------------------------------------------------------------------


def _structured_stream(
    seed: int, blocks: int = 12
) -> tuple[tuple[NormalizedCandle, ...], tuple[ConfirmedSwing, ...]]:
    rng = random.Random(seed)
    prices: list[_OHLC] = []
    swing_specs: list[tuple[int, SwingType, str]] = []
    level = 100.0

    for _block in range(blocks):
        level += rng.uniform(-3.0, 3.0)
        depth = rng.uniform(3.0, 5.0)
        drift = rng.uniform(0.02, 0.09)

        for _ in range(rng.randint(6, 12)):
            prices.append((level, level + 1.0, level - 1.0, level))

        origin_index = len(prices)
        origin_low = round(level - depth, 3)
        prices.append((level, level + 1.0, origin_low, level))
        swing_specs.append((origin_index, SwingType.SWING_LOW, str(origin_low)))

        base = origin_low + 0.5
        for step in range(5):
            low = base + step * 2.0
            prices.append((low, low + 2.0, low - 0.2, low + 1.8))
        peak_index = len(prices) - 1
        peak = round(prices[peak_index][1], 3)
        swing_specs.append((peak_index, SwingType.SWING_HIGH, str(peak)))

        for _ in range(rng.randint(5, 10)):
            prices.append((level, level + 1.0, level - 1.0, level))

        touch_index = len(prices)
        touch_low = round(origin_low + drift, 3)
        prices.append((level, level + 1.0, touch_low, level))
        swing_specs.append((touch_index, SwingType.SWING_LOW, str(touch_low)))

        base = touch_low + 0.5
        for step in range(5):
            low = base + step * 2.0
            prices.append((low, low + 2.0, low - 0.2, low + 1.8))

    for _ in range(4):
        prices.append((level, level + 1.0, level - 1.0, level))

    candles = _build(prices)
    swings = tuple(
        _swing(
            1000 + order,
            swing_type,
            price,
            index,
            candles,
            confirmation_offset_minutes=rng.randint(3, 8),
        )
        for order, (index, swing_type, price) in enumerate(swing_specs)
    )
    return candles, swings


def test_structured_stream_actually_publishes_zones() -> None:
    """The stress generator must exercise publication, not just empty results."""
    candles, swings = _structured_stream(1)
    frontier, rows = run_prefixes(candles, swings, lookback=_LOOKBACK)
    assert any(oracle for _, oracle, _ in rows), (
        "structured stream never publishes a zone — the stress campaign would "
        "be comparing empty tuples"
    )
    assert frontier.counters.published_zones > 0


def test_structured_streams_match_the_oracle_on_every_prefix() -> None:
    """Zone-producing streams, compared trajectory-wide against production."""
    for seed in range(1, 13):
        candles, swings = _structured_stream(seed)
        _, rows = run_prefixes(candles, swings, lookback=_LOOKBACK)
        for end, oracle, model in rows:
            assert model == oracle, (
                f"structured seed={seed} prefix={end}\n"
                f"  expected: {oracle}\n"
                f"  actual  : {model}"
            )


def test_confirmed_swings_are_ascending_by_pivot_end_time() -> None:
    """Load-bearing precondition for the Pine P1-SR-PERF-3 delta.

    The Pine transcription reconciles the swing snapshot with an O(A) two-cursor
    merge and looks swings up by binary search, both of which require
    ``detect_confirmed_swings`` to emit ascending ``pivot_end_time_utc``. That
    holds because the confirmation loop walks candidates in ascending pivot
    order, but it is an assumption worth failing loudly on rather than
    discovering as a silent Pine mis-reconciliation.
    """
    for seed in (11, 12, 13):
        candles, _ = _random_stream(seed, length=400, swing_count=20)
        for end in range(50, 401, 25):
            swings = detect_confirmed_swings(tuple(candles[:end]), _CONFIG)
            times = [s.pivot_end_time_utc for s in swings]
            assert times == sorted(times), (
                f"seed={seed} prefix={end}: confirmed swings are not ascending by "
                "pivot end time, which breaks the Pine merge delta"
            )
            assert len(set(times)) == len(times), (
                f"seed={seed} prefix={end}: duplicate pivot_end_time — the Pine "
                "semantic swing key would not be unique"
            )
