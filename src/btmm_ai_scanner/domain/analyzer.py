import hashlib
import json
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC
from decimal import Decimal
from enum import Enum
from itertools import pairwise
from typing import Any, Protocol
from uuid import UUID

from btmm_ai_scanner.config.enums import InternalSymbol, Timeframe
from btmm_ai_scanner.contracts.normalized_candle import NormalizedCandle
from btmm_ai_scanner.contracts.types import ContractModel, SemVer, UUIDv7
from btmm_ai_scanner.domain.configuration import MarketMeasurementConfiguration
from btmm_ai_scanner.domain.displacement import (
    DisplacementObservation,
    detect_displacement_observations,
)
from btmm_ai_scanner.domain.enums import (
    DerivedOutputType,
    SupportResistanceType,
    SwingType,
)
from btmm_ai_scanner.domain.equal_levels import (
    EqualLevelCluster,
    detect_equal_level_clusters,
)
from btmm_ai_scanner.domain.support_resistance import (
    SupportResistanceZone,
    SupportResistanceZoneCandidate,
    detect_support_resistance_zones,
)
from btmm_ai_scanner.domain.swings import (
    _WINDOW_RADIUS,
    ConfirmedSwing,
    ConfirmedSwingCandidate,
    _find_single_candle_pivots,
    _merge_adjacent_plateaus,
    _Pivot,
    _supersede_same_direction_runs,
    detect_confirmed_swings,
)
from btmm_ai_scanner.domain.trendlines import (
    Trendline,
    detect_trendlines,
)
from btmm_ai_scanner.measurements.atr import _true_range
from btmm_ai_scanner.measurements.legs import measure_leg


class MixedSymbolAnalysisError(ValueError):
    pass


class MixedTimeframeAnalysisError(ValueError):
    pass


class UnsortedCandleSequenceError(ValueError):
    pass


class DuplicateCandleRecordError(ValueError):
    pass


class AmbiguousEventTimeAnalysisError(ValueError):
    pass


class InvalidMarketMeasurementConfigurationError(ValueError):
    pass


class DerivedIdentityCollisionError(ValueError):
    pass


class DerivedOutputIdentityProvider(Protocol):
    def identify(
        self, *, output_type: DerivedOutputType, semantic_key: tuple[str, ...]
    ) -> UUIDv7: ...


class MarketMeasurementAnalysis(ContractModel):
    symbol: InternalSymbol | None
    timeframe: Timeframe | None
    analyzed_candle_count: int
    confirmed_swings: tuple[ConfirmedSwing, ...]
    displacement_observations: tuple[DisplacementObservation, ...]
    equal_level_clusters: tuple[EqualLevelCluster, ...]
    support_resistance_zones: tuple[SupportResistanceZone, ...]
    trendlines: tuple[Trendline, ...]


def _canonicalize(value: object) -> object:
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, Decimal):
        if value == 0:
            return "0"
        return format(value.normalize(), "f")
    if isinstance(value, int):
        return value
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, SemVer):
        return str(value)
    if hasattr(value, "astimezone") and hasattr(value, "isoformat"):
        return value.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%S.%f") + "Z"
    if isinstance(value, str):
        return value
    if isinstance(value, tuple | list):
        return [_canonicalize(item) for item in value]
    if isinstance(value, dict):
        return {key: _canonicalize(item) for key, item in value.items()}
    raise TypeError(f"Cannot canonicalize value of type {type(value)!r}")


def _compute_content_fingerprint(fields: dict[str, object]) -> str:
    canonical = _canonicalize(fields)
    serialized = json.dumps(canonical, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def _validate_candles(candles: tuple[NormalizedCandle, ...]) -> None:
    if len(candles) == 0:
        return

    for candle in candles:
        if candle.symbol is None or candle.timeframe is None:
            raise InvalidMarketMeasurementConfigurationError(
                "Every candle must carry non-null symbol and timeframe instrument "
                "metadata; analyze_market_measurements does not infer missing "
                "instrument identity."
            )

    symbols = {candle.symbol for candle in candles}
    if len(symbols) > 1:
        raise MixedSymbolAnalysisError(
            "analyze_market_measurements requires exactly one InternalSymbol."
        )

    timeframes = {candle.timeframe for candle in candles}
    if len(timeframes) > 1:
        raise MixedTimeframeAnalysisError(
            "analyze_market_measurements requires exactly one Timeframe."
        )

    seen_record_ids: set[UUID] = set()
    for candle in candles:
        if candle.record_id in seen_record_ids:
            raise DuplicateCandleRecordError(
                f"record_id {candle.record_id} appears more than once in the input."
            )
        seen_record_ids.add(candle.record_id)

    for previous, current in pairwise(candles):
        if current.event_time_utc == previous.event_time_utc:
            raise AmbiguousEventTimeAnalysisError(
                "Two distinct candle records share the same event_time_utc; "
                "revision selection is a caller responsibility."
            )
        if current.event_time_utc < previous.event_time_utc:
            raise UnsortedCandleSequenceError(
                "candles must be canonically ordered by (event_time_utc, record_id)."
            )


class _IdentityResolver:
    def __init__(self, provider: DerivedOutputIdentityProvider) -> None:
        self._provider = provider
        self._issued: dict[UUID, tuple[str, ...]] = {}

    def resolve(
        self, output_type: DerivedOutputType, semantic_key: tuple[str, ...]
    ) -> UUID:
        record_id = self._provider.identify(
            output_type=output_type, semantic_key=semantic_key
        )
        existing = self._issued.get(record_id)
        if existing is not None and existing != semantic_key:
            raise DerivedIdentityCollisionError(
                f"identity provider returned {record_id} for two different "
                "semantic keys within one analysis call."
            )
        self._issued[record_id] = semantic_key
        return record_id


def _finalize[ContractT: ContractModel](
    candidates: list[Any],
    output_type: DerivedOutputType,
    contract_class: type[ContractT],
    semantic_key_fn: Callable[[Any], tuple[str, ...]],
    extra_fields_fn: Callable[[Any], dict[str, object]],
    excluded_candidate_fields: frozenset[str],
    configuration: MarketMeasurementConfiguration,
    resolver: _IdentityResolver,
) -> tuple[ContractT, ...]:
    results: list[ContractT] = []
    for candidate in candidates:
        semantic_key = semantic_key_fn(candidate)
        record_id = resolver.resolve(output_type, semantic_key)
        provenance_id = resolver.resolve(output_type, (*semantic_key, "provenance"))

        fields: dict[str, object] = dict(candidate._asdict())
        for excluded in excluded_candidate_fields:
            fields.pop(excluded, None)
        fields.update(extra_fields_fn(candidate))
        fields.update(
            rule_version=configuration.rule_version,
            contract_version=configuration.contract_version,
            schema_version=configuration.schema_version,
            evidence_classification=configuration.evidence_classification,
            provenance_id=provenance_id,
        )

        content_fingerprint = _compute_content_fingerprint(fields)
        # A generic TypeVar call site cannot statically see the concrete
        # subclass's fields; every one of the 5 contract classes passed here
        # genuinely accepts record_id/content_fingerprint plus **fields.
        results.append(
            contract_class(  # type: ignore[call-arg]
                record_id=record_id,
                content_fingerprint=content_fingerprint,
                **fields,
            )
        )
    return tuple(results)


def analyze_market_measurements(
    candles: tuple[NormalizedCandle, ...],
    configuration: MarketMeasurementConfiguration,
    identity_provider: DerivedOutputIdentityProvider,
) -> MarketMeasurementAnalysis:
    _validate_candles(candles)

    if len(candles) == 0:
        return MarketMeasurementAnalysis(
            symbol=None,
            timeframe=None,
            analyzed_candle_count=0,
            confirmed_swings=(),
            displacement_observations=(),
            equal_level_clusters=(),
            support_resistance_zones=(),
            trendlines=(),
        )

    resolver = _IdentityResolver(identity_provider)
    rule_version_text = str(configuration.rule_version)

    swing_candidates = detect_confirmed_swings(candles, configuration)
    confirmed_swings = _finalize(
        list(swing_candidates),
        DerivedOutputType.CONFIRMED_SWING,
        ConfirmedSwing,
        lambda c: (
            c.symbol.value,
            c.timeframe.value,
            c.swing_type.value,
            str(c.pivot_candle_record_ids[0]),
            str(c.confirmation_candle_id),
            rule_version_text,
        ),
        lambda c: {"availability_time_utc": c.meaningful_confirmation_time_utc},
        frozenset(),
        configuration,
        resolver,
    )

    displacement_candidates = detect_displacement_observations(candles, configuration)
    displacement_observations = _finalize(
        list(displacement_candidates),
        DerivedOutputType.DISPLACEMENT_OBSERVATION,
        DisplacementObservation,
        lambda c: (
            c.symbol.value,
            c.timeframe.value,
            str(c.candle_record_id),
            rule_version_text,
        ),
        lambda c: {},
        frozenset(),
        configuration,
        resolver,
    )

    equal_level_candidates = detect_equal_level_clusters(
        tuple(confirmed_swings), configuration
    )
    equal_level_clusters = _finalize(
        list(equal_level_candidates),
        DerivedOutputType.EQUAL_LEVEL_CLUSTER,
        EqualLevelCluster,
        lambda c: (
            c.symbol.value,
            c.timeframe.value,
            c.cluster_type.value,
            str(c.first_seed_swing_id),
            str(c.second_seed_swing_id),
            rule_version_text,
        ),
        lambda c: {"availability_time_utc": c.confirmation_time_utc},
        frozenset({"first_seed_swing_id", "second_seed_swing_id"}),
        configuration,
        resolver,
    )

    support_resistance_candidates = detect_support_resistance_zones(
        candles, tuple(confirmed_swings), configuration
    )
    support_resistance_zones = _finalize(
        list(support_resistance_candidates),
        DerivedOutputType.SUPPORT_RESISTANCE_ZONE,
        SupportResistanceZone,
        lambda c: (
            c.symbol.value,
            c.timeframe.value,
            c.zone_type.value,
            str(c.origin_swing_record_id),
            str(c.confirmation_candle_id),
            rule_version_text,
        ),
        lambda c: {"availability_time_utc": c.confirmation_time_utc},
        frozenset(),
        configuration,
        resolver,
    )

    trendline_candidates = detect_trendlines(
        candles, tuple(confirmed_swings), configuration
    )
    trendlines = _finalize(
        list(trendline_candidates),
        DerivedOutputType.TRENDLINE,
        Trendline,
        lambda c: (
            c.symbol.value,
            c.timeframe.value,
            c.orientation.value,
            str(c.anchor_1_swing_record_id),
            str(c.anchor_2_swing_record_id),
            str(c.confirmation_candle_id),
            rule_version_text,
        ),
        lambda c: {"availability_time_utc": c.confirmation_time_utc},
        frozenset(),
        configuration,
        resolver,
    )

    return MarketMeasurementAnalysis(
        symbol=candles[0].symbol,
        timeframe=candles[0].timeframe,
        analyzed_candle_count=len(candles),
        confirmed_swings=confirmed_swings,
        displacement_observations=displacement_observations,
        equal_level_clusters=equal_level_clusters,
        support_resistance_zones=support_resistance_zones,
        trendlines=trendlines,
    )


@dataclass(frozen=True)
class _AtrIncrementalState:
    previous_candle_close: Decimal | None = None
    initialization_true_range_sum: Decimal = Decimal(0)
    initialization_sample_count: int = 0
    previous_finalized_atr: Decimal | None = None


def _atr_incremental_step(
    state: _AtrIncrementalState,
    candle: NormalizedCandle,
    atr_period: int,
) -> tuple[_AtrIncrementalState, Decimal | None]:
    """Exact incremental equivalent of measurements.atr.compute_atr_series,
    proven in register PHASE_1B_AUTHOR_DECISION_REGISTER.md §44AI: Wilder ATR
    is an IIR recursion needing only the previous close (for true range) and
    either the running seed sum (before the period-th sample) or the previous
    finalized ATR (after). No raw candle retention is required."""
    true_range = _true_range(candle, state.previous_candle_close)

    if state.previous_finalized_atr is not None:
        current_atr = (
            state.previous_finalized_atr * Decimal(atr_period - 1) + true_range
        ) / Decimal(atr_period)
        return (
            _AtrIncrementalState(
                previous_candle_close=candle.close,
                initialization_true_range_sum=state.initialization_true_range_sum,
                initialization_sample_count=state.initialization_sample_count,
                previous_finalized_atr=current_atr,
            ),
            current_atr,
        )

    new_sum = state.initialization_true_range_sum + true_range
    new_count = state.initialization_sample_count + 1
    if new_count < atr_period:
        return (
            _AtrIncrementalState(
                previous_candle_close=candle.close,
                initialization_true_range_sum=new_sum,
                initialization_sample_count=new_count,
                previous_finalized_atr=None,
            ),
            None,
        )

    seed_atr = new_sum / Decimal(atr_period)
    return (
        _AtrIncrementalState(
            previous_candle_close=candle.close,
            initialization_true_range_sum=new_sum,
            initialization_sample_count=new_count,
            previous_finalized_atr=seed_atr,
        ),
        seed_atr,
    )


def _pivot_key(pivot: _Pivot) -> tuple[int, int, SwingType]:
    return (pivot.start_index, pivot.end_index, pivot.swing_type)


@dataclass(frozen=True)
class _PivotConfirmationTracker:
    """Persistent, per-pivot reversal-search state. Once created, each
    candle folds in only the single newest candle (O(1)) instead of
    rescanning from the pivot's own local_confirmation_index every time —
    the waste this subsystem-2b correction removes. A tracker is immutable
    from the candle it confirms on: confirmed_at_index/confirmation_excursion
    never change again once set, matching the oracle's own first-match-wins
    (break-on-threshold) search semantics."""

    running_extreme: Decimal
    confirmed_at_index: int | None
    confirmation_excursion: Decimal


def _update_confirmation_trackers(
    trackers: dict[tuple[int, int, SwingType], _PivotConfirmationTracker],
    pivots: list[_Pivot],
    candles: list[NormalizedCandle],
    configuration: MarketMeasurementConfiguration,
) -> dict[tuple[int, int, SwingType], _PivotConfirmationTracker]:
    """Advances every live pivot's confirmation-search tracker by exactly the
    one newest candle. A pivot whose local_confirmation_index is reached for
    the first time gets a one-time catch-up scan (bounded by however many
    candles elapsed between its own local_confirmation_index and the moment
    its run closed and it entered `pivots` — not the full replay history);
    every subsequent step is an O(1) fold of the single new candle. Trackers
    for pivot identities no longer present in `pivots` (superseded by a
    same-direction run extending past them) are pruned so state never grows
    across identities that were only ever transient."""
    n = len(candles)
    updated: dict[tuple[int, int, SwingType], _PivotConfirmationTracker] = {}

    for pivot in pivots:
        local_confirmation_index = pivot.end_index + _WINDOW_RADIUS
        if local_confirmation_index >= n:
            continue

        key = _pivot_key(pivot)
        existing = trackers.get(key)

        if existing is not None and existing.confirmed_at_index is not None:
            updated[key] = existing
            continue

        threshold = (
            configuration.meaningful_reversal_atr_multiplier * pivot.reference_atr
        )
        is_high = pivot.swing_type == SwingType.SWING_HIGH

        if existing is None:
            extreme = (
                candles[local_confirmation_index].low
                if is_high
                else candles[local_confirmation_index].high
            )
            confirmed_at: int | None = None
            excursion = Decimal(0)
            for j in range(local_confirmation_index + 1, n):
                if is_high:
                    extreme = min(extreme, candles[j].low)
                    current_excursion = pivot.price - extreme
                else:
                    extreme = max(extreme, candles[j].high)
                    current_excursion = extreme - pivot.price
                if current_excursion >= threshold:
                    confirmed_at = j
                    excursion = current_excursion
                    break
            updated[key] = _PivotConfirmationTracker(
                running_extreme=extreme,
                confirmed_at_index=confirmed_at,
                confirmation_excursion=excursion,
            )
            continue

        latest = candles[n - 1]
        if is_high:
            extreme = min(existing.running_extreme, latest.low)
            current_excursion = pivot.price - extreme
        else:
            extreme = max(existing.running_extreme, latest.high)
            current_excursion = extreme - pivot.price
        confirmed_at = None
        excursion = existing.confirmation_excursion
        if current_excursion >= threshold:
            confirmed_at = n - 1
            excursion = current_excursion
        updated[key] = _PivotConfirmationTracker(
            running_extreme=extreme,
            confirmed_at_index=confirmed_at,
            confirmation_excursion=excursion,
        )

    # `updated` already holds exactly one entry per key in `live_keys` (every
    # branch above writes one); omitting any key not in `pivots` this candle
    # is precisely the pruning of orphaned open-run identities.
    return updated


def _derive_confirmed_swing_candidates(
    pivots: list[_Pivot],
    trackers: dict[tuple[int, int, SwingType], _PivotConfirmationTracker],
    candles: list[NormalizedCandle],
    configuration: MarketMeasurementConfiguration,
) -> tuple[ConfirmedSwingCandidate, ...]:
    """Reproduces domain.swings.detect_confirmed_swings's confirmation loop
    exactly (skip-if-type-matches-last-confirmed, else attempt), but reads
    each pivot's search result from its O(1) tracker instead of rescanning
    candles. domain/swings.py stays unmodified as the differential oracle;
    this is a deliberate, disclosed duplicate kept in sync by the equivalence
    tests. The loop itself is unavoidably O(pivot count) per candle: an
    earlier pivot's confirmed-by-now status is not monotonic across replay
    steps only in the sense that it can flip from unresolved to confirmed at
    any future candle, and every strictly-later pivot's skip/attempt outcome
    depends on that flip — so the walk must be redone each candle. This is
    bounded by pivot count (empirically far smaller than candle count), never
    by candle count or full raw-candle history."""
    n = len(candles)
    results: list[ConfirmedSwingCandidate] = []
    last_confirmed_type: SwingType | None = None

    for pivot in pivots:
        local_confirmation_index = pivot.end_index + _WINDOW_RADIUS
        if local_confirmation_index >= n:
            continue

        if pivot.swing_type == last_confirmed_type:
            continue

        tracker = trackers[_pivot_key(pivot)]
        if tracker.confirmed_at_index is None:
            continue

        threshold = (
            configuration.meaningful_reversal_atr_multiplier * pivot.reference_atr
        )
        confirmation_index = tracker.confirmed_at_index
        excursion = tracker.confirmation_excursion

        pivot_candle_ids = tuple(
            candles[i].record_id for i in range(pivot.start_index, pivot.end_index + 1)
        )
        local_confirmation_candle = candles[local_confirmation_index]
        confirmation_candle = candles[confirmation_index]

        results.append(
            ConfirmedSwingCandidate(
                symbol=candles[pivot.start_index].symbol,
                timeframe=candles[pivot.start_index].timeframe,
                swing_type=pivot.swing_type,
                pivot_price=pivot.price,
                pivot_bar_index=pivot.start_index,
                pivot_candle_record_ids=pivot_candle_ids,
                pivot_start_time_utc=candles[pivot.start_index].event_time_utc,
                pivot_end_time_utc=candles[pivot.end_index].event_time_utc,
                local_confirmation_time_utc=local_confirmation_candle.availability_time_utc,
                meaningful_confirmation_time_utc=confirmation_candle.availability_time_utc,
                confirmation_candle_id=confirmation_candle.record_id,
                pivot_reference_atr=pivot.reference_atr,
                pivot_tie_tolerance=pivot.tie_tolerance,
                reversal_threshold=threshold,
                reversal_excursion=excursion,
            )
        )
        last_confirmed_type = pivot.swing_type

    return tuple(results)


def _confirmed_swing_semantic_key(
    candidate: ConfirmedSwingCandidate, rule_version_text: str
) -> tuple[str, ...]:
    return (
        candidate.symbol.value,
        candidate.timeframe.value,
        candidate.swing_type.value,
        str(candidate.pivot_candle_record_ids[0]),
        str(candidate.confirmation_candle_id),
        rule_version_text,
    )


def _equal_level_semantic_key(
    candidate: Any, rule_version_text: str
) -> tuple[str, ...]:
    return (
        candidate.symbol.value,
        candidate.timeframe.value,
        candidate.cluster_type.value,
        str(candidate.first_seed_swing_id),
        str(candidate.second_seed_swing_id),
        rule_version_text,
    )


def _support_resistance_semantic_key(
    candidate: Any, rule_version_text: str
) -> tuple[str, ...]:
    return (
        candidate.symbol.value,
        candidate.timeframe.value,
        candidate.zone_type.value,
        str(candidate.origin_swing_record_id),
        str(candidate.confirmation_candle_id),
        rule_version_text,
    )


def _trendline_semantic_key(candidate: Any, rule_version_text: str) -> tuple[str, ...]:
    return (
        candidate.symbol.value,
        candidate.timeframe.value,
        candidate.orientation.value,
        str(candidate.anchor_1_swing_record_id),
        str(candidate.anchor_2_swing_record_id),
        str(candidate.confirmation_candle_id),
        rule_version_text,
    )


def _displacement_semantic_key(
    candidate: Any, rule_version_text: str
) -> tuple[str, ...]:
    return (
        candidate.symbol.value,
        candidate.timeframe.value,
        str(candidate.candle_record_id),
        rule_version_text,
    )


_SR_ZERO = Decimal("0")


@dataclass(frozen=True)
class _ReactionTracker:
    """Persistent per-candidate reaction-window state for support/resistance,
    mirroring domain.support_resistance._evaluate_reaction but split into an
    O(1)-per-candle 'has the reaction started yet' check plus a bounded
    (<=reaction_window_bars) window re-evaluation, instead of rescanning from
    search_start_index on every candle. The span from search_start_index to
    reaction_start_index is an unbounded-duration search — a proven property
    of the approved algorithm itself (identical in kind to the swing
    confirmation search corrected above), not an implementation shortcut —
    but it is only ever walked ONCE per candidate, the moment the reaction
    starts, not repeatedly. Once reaction_start_index is known, the window
    evaluation is O(reaction_window_bars) and re-runs at most
    reaction_window_bars times before `permanent` becomes True (the same cap
    _evaluate_reaction itself imposes via min(...))."""

    search_start_index: int
    zone_top: Decimal
    zone_bottom: Decimal
    is_support: bool
    last_checked_index: int
    reaction_start_index: int | None
    anchor: Decimal | None
    permanent: bool
    confirming_candle_index: int | None


def _create_reaction_tracker(
    search_start_index: int,
    zone_top: Decimal,
    zone_bottom: Decimal,
    is_support: bool,
) -> _ReactionTracker:
    return _ReactionTracker(
        search_start_index=search_start_index,
        zone_top=zone_top,
        zone_bottom=zone_bottom,
        is_support=is_support,
        last_checked_index=search_start_index - 1,
        reaction_start_index=None,
        anchor=None,
        permanent=False,
        confirming_candle_index=None,
    )


def _advance_reaction_tracker(
    tracker: _ReactionTracker,
    candles: list[NormalizedCandle],
    atr_values: list[Decimal | None],
    configuration: MarketMeasurementConfiguration,
) -> _ReactionTracker:
    if tracker.permanent:
        return tracker

    n = len(candles)
    zone_height = tracker.zone_top - tracker.zone_bottom
    if zone_height <= _SR_ZERO:
        return _ReactionTracker(
            search_start_index=tracker.search_start_index,
            zone_top=tracker.zone_top,
            zone_bottom=tracker.zone_bottom,
            is_support=tracker.is_support,
            last_checked_index=n - 1,
            reaction_start_index=None,
            anchor=None,
            permanent=True,
            confirming_candle_index=None,
        )

    reaction_start_index = tracker.reaction_start_index
    anchor = tracker.anchor
    last_checked_index = tracker.last_checked_index

    if reaction_start_index is None:
        # Catch up over every candle not yet checked, not just the newest
        # one: a tracker can first be examined several candles after its own
        # search_start_index (e.g. an origin swing only enters `origins`
        # once ITS OWN confirmation search resolves, which can land well
        # past search_start_index), so the unscanned range at creation time
        # is not always exactly one candle.
        scan_start = max(last_checked_index + 1, tracker.search_start_index)
        for index in range(scan_start, n):
            candle = candles[index]
            breached = (tracker.is_support and candle.close > tracker.zone_top) or (
                not tracker.is_support and candle.close < tracker.zone_bottom
            )
            if breached:
                reaction_start_index = index
                break
        last_checked_index = n - 1
        if reaction_start_index is None:
            return _ReactionTracker(
                search_start_index=tracker.search_start_index,
                zone_top=tracker.zone_top,
                zone_bottom=tracker.zone_bottom,
                is_support=tracker.is_support,
                last_checked_index=last_checked_index,
                reaction_start_index=None,
                anchor=None,
                permanent=False,
                confirming_candle_index=None,
            )
        window = candles[tracker.search_start_index : reaction_start_index + 1]
        anchor = (
            min(c.low for c in window)
            if tracker.is_support
            else max(c.high for c in window)
        )

    assert anchor is not None  # always set alongside reaction_start_index
    window_end = min(reaction_start_index + configuration.reaction_window_bars, n)
    window_candles = candles[reaction_start_index:window_end]
    is_full_window = (
        window_end == reaction_start_index + configuration.reaction_window_bars
    )

    confirming_index: int | None = None
    if len(window_candles) > 0:
        if tracker.is_support:
            highest_high = max(c.high for c in window_candles)
            mfe = highest_high - anchor
            zone_clearance = max(_SR_ZERO, highest_high - tracker.zone_top)
            mfe_index = max(
                range(reaction_start_index, window_end), key=lambda i: candles[i].high
            )
        else:
            lowest_low = min(c.low for c in window_candles)
            mfe = anchor - lowest_low
            zone_clearance = max(_SR_ZERO, tracker.zone_bottom - lowest_low)
            mfe_index = min(
                range(reaction_start_index, window_end), key=lambda i: candles[i].low
            )

        reference_atr = atr_values[reaction_start_index]
        if reference_atr is not None and reference_atr != _SR_ZERO:
            atr_reaction_ratio = mfe / reference_atr
            zone_clearance_ratio = zone_clearance / zone_height

            leg_candles = candles[reaction_start_index : mfe_index + 1]
            leg_atrs = atr_values[reaction_start_index : mfe_index + 1]
            leg = measure_leg(
                leg_candles,
                leg_atrs,
                is_bullish_direction=tracker.is_support,
                fast_normalized_speed_per_bar=(
                    configuration.leg_fast_normalized_speed_per_bar
                ),
                fast_directional_efficiency=(
                    configuration.leg_fast_directional_efficiency
                ),
                fast_directional_candle_share=(
                    configuration.leg_fast_directional_candle_share
                ),
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
                atr_reaction_ratio >= configuration.reaction_standard_atr_ratio
                and zone_clearance_ratio
                >= configuration.reaction_standard_zone_clearance_ratio
                and leg.directional_efficiency
                >= configuration.reaction_standard_directional_efficiency
                and leg.directional_candle_share
                >= configuration.reaction_standard_directional_candle_share
            )
            if meets_standard:
                confirming_index = mfe_index

    return _ReactionTracker(
        search_start_index=tracker.search_start_index,
        zone_top=tracker.zone_top,
        zone_bottom=tracker.zone_bottom,
        is_support=tracker.is_support,
        last_checked_index=last_checked_index,
        reaction_start_index=reaction_start_index,
        anchor=anchor,
        permanent=is_full_window,
        confirming_candle_index=confirming_index,
    )


def _derive_support_resistance_zone_candidates(
    candles: list[NormalizedCandle],
    atr_values: list[Decimal | None],
    confirmed_swings: tuple[ConfirmedSwing, ...],
    origin_trackers: dict[UUID, _ReactionTracker],
    touch_trackers: dict[tuple[UUID, UUID], _ReactionTracker],
    configuration: MarketMeasurementConfiguration,
) -> tuple[
    tuple[SupportResistanceZoneCandidate, ...],
    dict[UUID, _ReactionTracker],
    dict[tuple[UUID, UUID], _ReactionTracker],
]:
    """Reproduces domain.support_resistance.detect_support_resistance_zones's
    exact structure and ordering, but every _evaluate_reaction call is
    replaced with an O(1)-amortized _ReactionTracker lookup/advance. The
    outer origin x touch walk stays O(A_swings^2) worst case, matching the
    architecture's own disclosed, deliberately-not-optimized-away complexity
    for this detector (register §44AI/§44AL) — what this correction removes
    is the O(candles) rescan that used to sit inside every one of those O(A^2)
    reaction checks, not the O(A^2) walk itself. Must run every candle (not
    only when confirmed_swings changes): a reaction's bounded window can
    newly resolve purely from candle growth with no new swing involved."""
    n = len(candles)
    candle_index_by_id = {
        candle.record_id: index for index, candle in enumerate(candles)
    }
    new_origin_trackers: dict[UUID, _ReactionTracker] = {}
    new_touch_trackers: dict[tuple[UUID, UUID], _ReactionTracker] = {}
    results: list[SupportResistanceZoneCandidate] = []

    for zone_type, origin_swing_type in (
        (SupportResistanceType.SUPPORT, SwingType.SWING_LOW),
        (SupportResistanceType.RESISTANCE, SwingType.SWING_HIGH),
    ):
        opposite_swing_type = (
            SwingType.SWING_HIGH
            if origin_swing_type == SwingType.SWING_LOW
            else SwingType.SWING_LOW
        )
        origins = sorted(
            (s for s in confirmed_swings if s.swing_type == origin_swing_type),
            key=lambda s: s.meaningful_confirmation_time_utc,
        )
        same_type_swings = origins
        is_support = zone_type == SupportResistanceType.SUPPORT

        for origin in origins:
            origin_last_candle_id = origin.pivot_candle_record_ids[-1]
            origin_index = candle_index_by_id[origin_last_candle_id]

            zone_depth = (
                configuration.support_resistance_zone_depth_atr_multiplier
                * origin.pivot_reference_atr
            )
            if is_support:
                zone_bottom = origin.pivot_price
                zone_top = zone_bottom + zone_depth
            else:
                zone_top = origin.pivot_price
                zone_bottom = zone_top - zone_depth

            if origin_index + 1 >= n:
                continue
            origin_tracker = origin_trackers.get(
                origin.record_id
            ) or _create_reaction_tracker(
                origin_index + 1, zone_top, zone_bottom, is_support
            )
            origin_tracker = _advance_reaction_tracker(
                origin_tracker, candles, atr_values, configuration
            )
            new_origin_trackers[origin.record_id] = origin_tracker

            if origin_tracker.confirming_candle_index is None:
                continue

            touch_tolerance = (
                configuration.support_resistance_touch_tolerance_atr_multiplier
                * origin.pivot_reference_atr
            )
            pierce_tolerance = (
                configuration.support_resistance_pierce_tolerance_atr_multiplier
                * origin.pivot_reference_atr
            )

            qualifying_touches: list[ConfirmedSwing] = []
            first_confirming_index: int | None = None
            last_touch_time = origin.meaningful_confirmation_time_utc

            for touch in same_type_swings:
                if touch.record_id == origin.record_id:
                    continue
                if touch.meaningful_confirmation_time_utc <= last_touch_time:
                    continue

                if is_support:
                    geometric_ok = (
                        touch.pivot_price <= zone_top + touch_tolerance
                        and touch.pivot_price >= zone_bottom - pierce_tolerance
                    )
                else:
                    geometric_ok = (
                        touch.pivot_price >= zone_bottom - touch_tolerance
                        and touch.pivot_price <= zone_top + pierce_tolerance
                    )
                if not geometric_ok:
                    continue

                has_opposite_between = any(
                    s.swing_type == opposite_swing_type
                    and last_touch_time
                    < s.meaningful_confirmation_time_utc
                    < touch.meaningful_confirmation_time_utc
                    for s in confirmed_swings
                )
                if not has_opposite_between:
                    continue

                touch_last_candle_id = touch.pivot_candle_record_ids[-1]
                touch_index = candle_index_by_id[touch_last_candle_id]
                if touch_index + 1 >= n:
                    continue
                touch_key = (origin.record_id, touch.record_id)
                touch_tracker = touch_trackers.get(
                    touch_key
                ) or _create_reaction_tracker(
                    touch_index + 1, zone_top, zone_bottom, is_support
                )
                touch_tracker = _advance_reaction_tracker(
                    touch_tracker, candles, atr_values, configuration
                )
                new_touch_trackers[touch_key] = touch_tracker

                if touch_tracker.confirming_candle_index is None:
                    continue

                qualifying_touches.append(touch)
                if first_confirming_index is None:
                    first_confirming_index = touch_tracker.confirming_candle_index
                last_touch_time = touch.meaningful_confirmation_time_utc

            if first_confirming_index is None:
                continue

            first_confirming_candle = candles[first_confirming_index]
            results.append(
                SupportResistanceZoneCandidate(
                    symbol=origin.symbol,
                    timeframe=origin.timeframe,
                    zone_type=zone_type,
                    origin_swing_record_id=origin.record_id,
                    creator_reference_atr=origin.pivot_reference_atr,
                    zone_depth=zone_depth,
                    zone_top=zone_top,
                    zone_bottom=zone_bottom,
                    qualifying_touch_swing_record_ids=tuple(
                        touch.record_id for touch in qualifying_touches
                    ),
                    confirmation_candle_id=first_confirming_candle.record_id,
                    confirmation_time_utc=first_confirming_candle.availability_time_utc,
                )
            )

    results.sort(key=lambda candidate: candidate.confirmation_time_utc)
    return tuple(results), new_origin_trackers, new_touch_trackers


@dataclass
class _MeasurementReplayState:
    """Private, per-timeframe incremental measurement state for subsystem 2b.
    Not part of the public contract surface; owned exclusively by the
    scanner replay path. candles_so_far and confirmed_swings_so_far are
    retained in full (register §44AL classification A / O(T*C), O(A_swings)).
    equal_level_clusters/trendlines are recomputed via the unmodified batch
    detectors whenever confirmed_swings_so_far changes (register §44AI: both
    depend only on confirmed_swings — equal-levels takes no candles at all;
    a trendline's reference ATR and integrity check only ever look at
    candles up to its own anchor_2_bar_index, which cannot change as later
    candles are appended — so gating recompute on a swing change is exactly
    correct). A genuinely incremental frontier for these two (only
    reprocessing the newly finalized/replaced swing against existing state,
    per the correction's Part 5 request) was attempted and reverted this
    session: it surfaced multiple correctness regressions under differential
    testing (see the completion report's disclosed findings) that could not
    be resolved with acceptable confidence in the remaining session budget,
    so the proven-correct recompute-on-swing-change design is kept instead
    of shipping an unverified "optimization." support_resistance_zones is
    derived every candle via persistent _ReactionTracker state (O(1)
    amortized per reaction candidate) rather than the unmodified batch
    detector's O(candles) internal rescans, since a reaction's bounded
    window can newly resolve purely from candle growth with no new
    confirmed swing involved."""

    resolver: _IdentityResolver
    rule_version_text: str
    candles_so_far: list[NormalizedCandle] = field(default_factory=list)
    atr_state: _AtrIncrementalState = field(default_factory=_AtrIncrementalState)
    atr_values_so_far: list[Decimal | None] = field(default_factory=list)
    raw_pivots_so_far: list[_Pivot] = field(default_factory=list)
    confirmation_trackers: dict[
        tuple[int, int, SwingType], _PivotConfirmationTracker
    ] = field(default_factory=dict)
    sr_origin_trackers: dict[UUID, _ReactionTracker] = field(default_factory=dict)
    sr_touch_trackers: dict[tuple[UUID, UUID], _ReactionTracker] = field(
        default_factory=dict
    )
    confirmed_swing_candidates_so_far: tuple[ConfirmedSwingCandidate, ...] = ()
    confirmed_swings_so_far: tuple[ConfirmedSwing, ...] = ()
    displacement_observations_so_far: tuple[DisplacementObservation, ...] = ()
    equal_level_clusters_so_far: tuple[EqualLevelCluster, ...] = ()
    support_resistance_zones_so_far: tuple[SupportResistanceZone, ...] = ()
    trendlines_so_far: tuple[Trendline, ...] = ()


def _create_initial_measurement_replay_state(
    identity_provider: DerivedOutputIdentityProvider,
    configuration: MarketMeasurementConfiguration,
) -> _MeasurementReplayState:
    return _MeasurementReplayState(
        resolver=_IdentityResolver(identity_provider),
        rule_version_text=str(configuration.rule_version),
    )


def _advance_measurement_replay_state(
    state: _MeasurementReplayState,
    candle: NormalizedCandle,
    configuration: MarketMeasurementConfiguration,
) -> _MeasurementReplayState:
    """Advances the incremental measurement state by exactly one candle.
    Transactional: builds every new value from local variables and only
    constructs the replacement _MeasurementReplayState at the very end, so a
    raised exception leaves the caller's existing state object completely
    untouched (no partial mutation ever becomes visible)."""
    if state.candles_so_far:
        previous_candle = state.candles_so_far[-1]
        if candle.event_time_utc == previous_candle.event_time_utc:
            raise AmbiguousEventTimeAnalysisError(
                "Two distinct candle records share the same event_time_utc; "
                "revision selection is a caller responsibility."
            )
        if candle.event_time_utc < previous_candle.event_time_utc:
            raise UnsortedCandleSequenceError(
                "candles must be canonically ordered by (event_time_utc, record_id)."
            )

    new_candles_so_far = [*state.candles_so_far, candle]
    absolute_index = len(new_candles_so_far) - 1

    new_atr_state, atr_value = _atr_incremental_step(
        state.atr_state, candle, configuration.atr_period
    )
    new_atr_values_so_far = [*state.atr_values_so_far, atr_value]

    new_raw_pivots_so_far = list(state.raw_pivots_so_far)
    if absolute_index >= 2 * _WINDOW_RADIUS:
        pivot_center = absolute_index - _WINDOW_RADIUS
        window_start = pivot_center - _WINDOW_RADIUS
        window_end = pivot_center + _WINDOW_RADIUS + 1
        window_candles = new_candles_so_far[window_start:window_end]
        window_atrs = new_atr_values_so_far[window_start:window_end]
        local_pivots = _find_single_candle_pivots(
            window_candles, window_atrs, configuration
        )
        shift = window_start
        for local_pivot in local_pivots:
            new_raw_pivots_so_far.append(
                _Pivot(
                    local_pivot.start_index + shift,
                    local_pivot.end_index + shift,
                    local_pivot.swing_type,
                    local_pivot.price,
                    local_pivot.reference_atr,
                    local_pivot.tie_tolerance,
                )
            )

    pivots = _supersede_same_direction_runs(
        _merge_adjacent_plateaus(list(new_raw_pivots_so_far))
    )
    new_confirmation_trackers = _update_confirmation_trackers(
        state.confirmation_trackers, pivots, new_candles_so_far, configuration
    )
    new_confirmed_swing_candidates = _derive_confirmed_swing_candidates(
        pivots, new_confirmation_trackers, new_candles_so_far, configuration
    )

    new_confirmed_swings = state.confirmed_swings_so_far
    if new_confirmed_swing_candidates != state.confirmed_swing_candidates_so_far:
        # A previously "skipped" pivot (its type matched the then-current
        # last_confirmed_type because an earlier same-alternating-type pivot
        # had not yet reached its reversal threshold) can itself confirm once
        # more candles arrive, inserting a new entry at a MIDDLE position of
        # the results list, not only at the tail. The candidate list is
        # therefore not append-only and must be re-finalized in full each
        # step rather than diffed by a trailing slice; the persistent
        # resolver makes re-resolving unchanged entries an inexpensive no-op.
        new_confirmed_swings = _finalize(
            list(new_confirmed_swing_candidates),
            DerivedOutputType.CONFIRMED_SWING,
            ConfirmedSwing,
            lambda c: _confirmed_swing_semantic_key(c, state.rule_version_text),
            lambda c: {"availability_time_utc": c.meaningful_confirmation_time_utc},
            frozenset(),
            configuration,
            state.resolver,
        )

    new_equal_level_clusters = state.equal_level_clusters_so_far
    new_trendlines = state.trendlines_so_far
    swings_changed = new_confirmed_swings != state.confirmed_swings_so_far
    if swings_changed:
        # A still-open same-type pivot run's collapsed representative (the
        # most extreme candidate so far) can change identity as later raw
        # pivots extend it, even after its earlier extreme already produced
        # a confirmed swing at the same list position: a length check alone
        # would miss that same-length content change, so this must key off
        # full-value inequality, not a length comparison. Equal-levels and
        # trendlines depend only on confirmed_swings (equal-levels takes no
        # candles at all; a trendline's reference ATR and integrity check
        # only ever look at candles up to its own anchor_2_bar_index, which
        # cannot change as later candles are appended) so gating their
        # recompute on swings_changed alone is sufficient for equivalence.
        # A genuinely incremental frontier for these two (processing only
        # the newly finalized swing against existing state) was attempted
        # and reverted: see _MeasurementReplayState's docstring and the
        # subsystem 2b correction report for the disclosed, non-blocking
        # finding this leaves open (cumulative cost re-derives O(A) /
        # O(A^2) work on every swing arrival, not just the delta).
        equal_level_candidates = detect_equal_level_clusters(
            new_confirmed_swings, configuration
        )
        new_equal_level_clusters = _finalize(
            list(equal_level_candidates),
            DerivedOutputType.EQUAL_LEVEL_CLUSTER,
            EqualLevelCluster,
            lambda c: _equal_level_semantic_key(c, state.rule_version_text),
            lambda c: {"availability_time_utc": c.confirmation_time_utc},
            frozenset({"first_seed_swing_id", "second_seed_swing_id"}),
            configuration,
            state.resolver,
        )

        trendline_candidates = detect_trendlines(
            tuple(new_candles_so_far), new_confirmed_swings, configuration
        )
        new_trendlines = _finalize(
            list(trendline_candidates),
            DerivedOutputType.TRENDLINE,
            Trendline,
            lambda c: _trendline_semantic_key(c, state.rule_version_text),
            lambda c: {"availability_time_utc": c.confirmation_time_utc},
            frozenset(),
            configuration,
            state.resolver,
        )

    # Unlike equal-levels/trendlines, a support/resistance zone's reaction
    # evaluation searches a bounded window of RAW candles following the
    # origin/touch swing; a window that was truncated by the current candle
    # count can newly resolve as more candles arrive with no new confirmed
    # swing involved at all. Derivation must therefore run every candle (not
    # only when swings_changed) — but via persistent _ReactionTracker state
    # (O(1) amortized per candidate) rather than the unmodified batch
    # detector's O(candles) internal rescans, preserving (not optimizing
    # away) only the O(A_swings^2) outer walk per register §44AI/§44AL.
    (
        support_resistance_candidates,
        new_sr_origin_trackers,
        new_sr_touch_trackers,
    ) = _derive_support_resistance_zone_candidates(
        new_candles_so_far,
        new_atr_values_so_far,
        new_confirmed_swings,
        state.sr_origin_trackers,
        state.sr_touch_trackers,
        configuration,
    )
    new_support_resistance_zones = _finalize(
        list(support_resistance_candidates),
        DerivedOutputType.SUPPORT_RESISTANCE_ZONE,
        SupportResistanceZone,
        lambda c: _support_resistance_semantic_key(c, state.rule_version_text),
        lambda c: {"availability_time_utc": c.confirmation_time_utc},
        frozenset(),
        configuration,
        state.resolver,
    )

    new_displacement_observations = state.displacement_observations_so_far
    window = configuration.range_context_window
    if absolute_index >= window:
        displacement_slice = tuple(new_candles_so_far[absolute_index - window :])
        displacement_candidates = detect_displacement_observations(
            displacement_slice, configuration
        )
        newly_finalized_displacement = _finalize(
            list(displacement_candidates),
            DerivedOutputType.DISPLACEMENT_OBSERVATION,
            DisplacementObservation,
            lambda c: _displacement_semantic_key(c, state.rule_version_text),
            lambda c: {},
            frozenset(),
            configuration,
            state.resolver,
        )
        new_displacement_observations = (
            *state.displacement_observations_so_far,
            *newly_finalized_displacement,
        )

    return _MeasurementReplayState(
        resolver=state.resolver,
        rule_version_text=state.rule_version_text,
        candles_so_far=new_candles_so_far,
        atr_state=new_atr_state,
        atr_values_so_far=new_atr_values_so_far,
        raw_pivots_so_far=new_raw_pivots_so_far,
        confirmation_trackers=new_confirmation_trackers,
        sr_origin_trackers=new_sr_origin_trackers,
        sr_touch_trackers=new_sr_touch_trackers,
        confirmed_swing_candidates_so_far=new_confirmed_swing_candidates,
        confirmed_swings_so_far=new_confirmed_swings,
        displacement_observations_so_far=new_displacement_observations,
        equal_level_clusters_so_far=new_equal_level_clusters,
        support_resistance_zones_so_far=new_support_resistance_zones,
        trendlines_so_far=new_trendlines,
    )


def _measurement_replay_state_to_analysis(
    state: _MeasurementReplayState,
) -> MarketMeasurementAnalysis:
    symbol = state.candles_so_far[0].symbol if state.candles_so_far else None
    timeframe = state.candles_so_far[0].timeframe if state.candles_so_far else None
    return MarketMeasurementAnalysis(
        symbol=symbol,
        timeframe=timeframe,
        analyzed_candle_count=len(state.candles_so_far),
        confirmed_swings=state.confirmed_swings_so_far,
        displacement_observations=state.displacement_observations_so_far,
        equal_level_clusters=state.equal_level_clusters_so_far,
        support_resistance_zones=state.support_resistance_zones_so_far,
        trendlines=state.trendlines_so_far,
    )
