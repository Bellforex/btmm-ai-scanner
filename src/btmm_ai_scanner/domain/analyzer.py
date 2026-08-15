import bisect
import hashlib
import json
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
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
    EqualLevelType,
    SupportResistanceType,
    SwingType,
)
from btmm_ai_scanner.domain.equal_levels import (
    EqualLevelCluster,
    EqualLevelClusterCandidate,
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
from btmm_ai_scanner.persistent_map import PersistentMap


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
        # A6-F6F-B: forward memo (output_type, semantic_key) -> record_id. The
        # provider is a pure deterministic function of its inputs, so resolving a
        # semantic key already seen returns the identical id WITHOUT re-invoking
        # identify(). Under incremental replay the same historical candidate is
        # re-finalized every candle; this collapses O(N * A) identify() calls
        # (each a SHA-256 over the key) to O(A) -- one per distinct record -- with
        # byte-identical results. Not an algorithm change (§9): the exact same
        # provider is still the sole source of every id, just called less often.
        self._by_key: dict[tuple[DerivedOutputType, tuple[str, ...]], UUID] = {}

    def resolve(
        self, output_type: DerivedOutputType, semantic_key: tuple[str, ...]
    ) -> UUID:
        memo_key = (output_type, semantic_key)
        cached = self._by_key.get(memo_key)
        if cached is not None:
            return cached
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
        self._by_key[memo_key] = record_id
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
    *,
    prior_reuse: dict[UUID, tuple[dict[str, object], ContractModel]] | None = None,
    new_reuse: dict[UUID, tuple[dict[str, object], ContractModel]] | None = None,
) -> tuple[ContractT, ...]:
    """A3-C: with ``prior_reuse``/``new_reuse`` (the incremental replay path) a
    finalized record whose fingerprint-determining fields are byte-identical to
    the cached ones is reused verbatim — no SHA-256, no strict-pydantic
    construction — and recorded in ``new_reuse`` for the next advance. This is an
    exact mutable-frontier reuse: unchanged prefix records keep their object,
    genuinely changed records (supersession / middle insertion) differ in
    ``fields`` and are rebuilt. The batch oracle passes neither cache and is
    byte-for-byte unchanged; ``new_reuse`` is a caller-owned local published only
    on a successful advance."""
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

        # A generic TypeVar call site cannot statically see the concrete
        # subclass's fields; every one of the 5 contract classes passed here
        # genuinely accepts record_id/content_fingerprint plus **fields.
        if prior_reuse is not None:
            cached = prior_reuse.get(record_id)
            if cached is not None and cached[0] == fields:
                record = cached[1]
            else:
                record = contract_class(  # type: ignore[call-arg]
                    record_id=record_id,
                    content_fingerprint=_compute_content_fingerprint(fields),
                    **fields,
                )
            if new_reuse is not None:
                new_reuse[record_id] = (fields, record)
            results.append(record)  # type: ignore[arg-type]
            continue

        content_fingerprint = _compute_content_fingerprint(fields)
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


# =====================================================================
# A6-F6D-M2: incremental support/resistance replay frontier.
#
# _derive_support_resistance_zone_candidates above stays the UNMODIFIED
# semantic oracle. This frontier produces a byte-identical candidate tuple at
# every prefix while resuming each origin's walk from the earliest touch whose
# reaction tracker changed (never from touch zero) and stopping as soon as the
# sequential state (last_touch_time) re-converges. The confirmed-swing stream is
# append-only in confirmation-availability order with only rare removals (proven
# by test_sr_frontier_append_only), so: same-type additions append one touch to
# a shared per-zone registry (positions never shift); appended opposite swings
# never fall inside any existing has_opposite interval (no routing needed); only
# rare removals invalidate existing origins. Per-origin checkpoints live in a
# PersistentMap[int, datetime] keyed by registry position -- O(log n) set/get
# with structural sharing, so no O(m) tuple copy and no ancestor mutation.
# =====================================================================


@dataclass(frozen=True)
class _SrOriginState:
    origin: ConfirmedSwing
    is_support: bool
    zone_top: Decimal
    zone_bottom: Decimal
    zone_depth: Decimal
    touch_tolerance: Decimal
    pierce_tolerance: Decimal
    origin_pos: int
    origin_confirmed: bool
    ck: PersistentMap[datetime]
    qualifying: PersistentMap[ConfirmedSwing]
    candidate: SupportResistanceZoneCandidate | None


@dataclass(frozen=True)
class _SupportResistanceFrontier:
    origin_trackers: dict[UUID, _ReactionTracker] = field(default_factory=dict)
    touch_trackers: dict[tuple[UUID, UUID], _ReactionTracker] = field(
        default_factory=dict
    )
    non_permanent_origins: frozenset[UUID] = frozenset()
    non_permanent_touches: frozenset[tuple[UUID, UUID]] = frozenset()
    origin_states: dict[tuple[SupportResistanceType, UUID], _SrOriginState] = field(
        default_factory=dict
    )
    prior_swings: tuple[ConfirmedSwing, ...] = ()
    swing_ids: frozenset[UUID] = frozenset()
    zone_registry: dict[SupportResistanceType, PersistentMap[ConfirmedSwing]] = field(
        default_factory=dict
    )
    zone_registry_len: dict[SupportResistanceType, int] = field(default_factory=dict)
    zone_pos_by_id: dict[SupportResistanceType, dict[UUID, int]] = field(
        default_factory=dict
    )
    zone_opposite_times: dict[SupportResistanceType, tuple[datetime, ...]] = field(
        default_factory=dict
    )
    origin_zone: dict[UUID, SupportResistanceType] = field(default_factory=dict)
    # Zone-price routing index (A6-F6D-M2R): a persistent price-ordered map of
    # origins per zone type, so a newly appended same-type touch is routed only
    # to the origins whose zone band its price actually enters (one O(log A + k)
    # stabbing query) instead of every prior same-type origin (the O(A^2)
    # resume-call path M2 disclosed). Keys are composite ``price_ticks * STRIDE +
    # seq`` ints so distinct origins at the same price stay distinct and price
    # order is preserved; ``origin_price_key`` remembers each key for removal.
    # ``zone_max_upper`` / ``zone_max_pierce`` are the running max band half-
    # widths used to bound the pivot-price window (they only grow, so the window
    # is always a valid superset -- exact ``_sr_geometric_ok`` filters the rest).
    zone_price_index: dict[SupportResistanceType, PersistentMap[UUID]] = field(
        default_factory=dict
    )
    origin_price_key: dict[UUID, int] = field(default_factory=dict)
    zone_max_upper: dict[SupportResistanceType, Decimal] = field(default_factory=dict)
    zone_max_pierce: dict[SupportResistanceType, Decimal] = field(default_factory=dict)
    zone_next_seq: dict[SupportResistanceType, int] = field(default_factory=dict)


_SR_ZONE_SPECS = (
    (SupportResistanceType.SUPPORT, SwingType.SWING_LOW, SwingType.SWING_HIGH),
    (SupportResistanceType.RESISTANCE, SwingType.SWING_HIGH, SwingType.SWING_LOW),
)


def _sr_zone_geometry(
    origin: ConfirmedSwing,
    is_support: bool,
    configuration: MarketMeasurementConfiguration,
) -> tuple[Decimal, Decimal, Decimal, Decimal, Decimal]:
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
    touch_tolerance = (
        configuration.support_resistance_touch_tolerance_atr_multiplier
        * origin.pivot_reference_atr
    )
    pierce_tolerance = (
        configuration.support_resistance_pierce_tolerance_atr_multiplier
        * origin.pivot_reference_atr
    )
    return zone_top, zone_bottom, zone_depth, touch_tolerance, pierce_tolerance


# Stride between price-ticks in a composite routing key: price_ticks * STRIDE +
# seq. 2**32 leaves room for >4e9 distinct origins per exact tick before two
# origins could collide, far beyond any replay (a few thousand swings), while
# keeping strict price ordering across ticks.
_SR_PRICE_KEY_STRIDE = 1 << 32


def _sr_price_ticks(price: Decimal, min_tick: Decimal) -> int:
    return int(price // min_tick)


def _sr_stab_older_origins(
    price_index: PersistentMap[UUID],
    max_upper: Decimal,
    max_pierce: Decimal,
    is_support: bool,
    price: Decimal,
    min_tick: Decimal,
    states: dict[tuple[SupportResistanceType, UUID], _SrOriginState],
    zone_type: SupportResistanceType,
    before_pos: int,
) -> list[UUID]:
    """Route a new same-type touch at ``price`` to only the origins whose zone
    band actually contains it. A support origin i is entered iff
    ``pivot_i - pierce_i <= price <= pivot_i + depth_i + touch_i``, i.e.
    ``price - (depth_i+touch_i) <= pivot_i <= price + pierce_i``; resistance is
    mirrored. Bounding ``depth_i+touch_i`` by ``max_upper`` and ``pierce_i`` by
    ``max_pierce`` gives a pivot-price window that is a superset of the true
    hits; the exact ``_sr_geometric_ok`` check then removes the extras. Only
    origins strictly older than ``before_pos`` can gain this swing as a touch."""
    if is_support:
        lo_price = price - max_upper
        hi_price = price + max_pierce
    else:
        lo_price = price - max_pierce
        hi_price = price + max_upper
    # Pad one tick each side so integer truncation never drops a boundary hit.
    lo_ticks = _sr_price_ticks(lo_price, min_tick) - 1
    hi_ticks = _sr_price_ticks(hi_price, min_tick) + 1
    klo = max(0, lo_ticks) * _SR_PRICE_KEY_STRIDE
    khi = (hi_ticks + 1) * _SR_PRICE_KEY_STRIDE
    marked: list[UUID] = []
    for _key, oid in price_index.range(klo, khi):
        state = states.get((zone_type, oid))
        if state is None or state.origin_pos >= before_pos:
            continue
        # The window is a superset; confirm exact band membership (same predicate
        # the per-touch walk uses) before marking the origin dirty.
        if _sr_price_in_band(state, price):
            marked.append(oid)
    return marked


def _sr_has_opposite_between(
    opposite_times: tuple[datetime, ...],
    last_time: datetime,
    touch_time: datetime,
) -> bool:
    """True iff some opposite-type confirmed swing falls STRICTLY between
    ``last_time`` and ``touch_time`` -- the exact ``last_time < s < touch_time``
    predicate the oracle expresses as ``any(...)`` over all confirmed swings,
    answered here in O(log A) against the pre-sorted opposite-time index.

    ``bisect_left(touch_time)`` counts opposites strictly < touch_time (so an
    opposite exactly AT touch_time is excluded, matching ``s < touch_time``);
    ``bisect_right(last_time)`` counts opposites <= last_time (so an opposite
    exactly AT last_time is excluded, matching ``last_time < s``). Their
    difference is the count strictly inside the open interval."""
    return bisect.bisect_left(opposite_times, touch_time) > bisect.bisect_right(
        opposite_times, last_time
    )


def _sr_price_in_band(state: _SrOriginState, price: Decimal) -> bool:
    """Exact zone-band membership: whether ``price`` falls inside the origin's
    tolerance-padded zone (touch tolerance on the zone-facing side, pierce
    tolerance on the far side). The single source of truth shared by the walk's
    ``_sr_geometric_ok`` and the routing index's superset filter."""
    if state.is_support:
        return (
            price <= state.zone_top + state.touch_tolerance
            and price >= state.zone_bottom - state.pierce_tolerance
        )
    return (
        price >= state.zone_bottom - state.touch_tolerance
        and price <= state.zone_top + state.pierce_tolerance
    )


def _sr_geometric_ok(state: _SrOriginState, touch: ConfirmedSwing) -> bool:
    return _sr_price_in_band(state, touch.pivot_price)


def _sr_build_candidate(
    state: _SrOriginState,
    qualifying: PersistentMap[ConfirmedSwing],
    touch_trackers: dict[tuple[UUID, UUID], _ReactionTracker],
    candles: list[NormalizedCandle],
) -> SupportResistanceZoneCandidate | None:
    items = qualifying.items()
    if not items:
        return None
    first_touch = items[0][1]
    first_tracker = touch_trackers[(state.origin.record_id, first_touch.record_id)]
    first_confirming_index = first_tracker.confirming_candle_index
    assert first_confirming_index is not None
    first_confirming_candle = candles[first_confirming_index]
    return SupportResistanceZoneCandidate(
        symbol=state.origin.symbol,
        timeframe=state.origin.timeframe,
        zone_type=(
            SupportResistanceType.SUPPORT
            if state.is_support
            else SupportResistanceType.RESISTANCE
        ),
        origin_swing_record_id=state.origin.record_id,
        creator_reference_atr=state.origin.pivot_reference_atr,
        zone_depth=state.zone_depth,
        zone_top=state.zone_top,
        zone_bottom=state.zone_bottom,
        qualifying_touch_swing_record_ids=tuple(t.record_id for _pos, t in items),
        confirmation_candle_id=first_confirming_candle.record_id,
        confirmation_time_utc=first_confirming_candle.availability_time_utc,
    )


def _sr_resume_origin(
    state: _SrOriginState,
    from_pos: int,
    latest_dirty: int,
    registry: PersistentMap[ConfirmedSwing],
    registry_len: int,
    opposite_times: tuple[datetime, ...],
    new_touch_trackers: dict[tuple[UUID, UUID], _ReactionTracker],
    non_permanent_touches: set[tuple[UUID, UUID]],
    candles: list[NormalizedCandle],
    atr_values: list[Decimal | None],
    candle_index_by_id: dict[UUID, int],
    n: int,
    configuration: MarketMeasurementConfiguration,
) -> _SrOriginState:
    """Resume the origin walk from ``from_pos`` (a registry position in
    (origin_pos, registry_len]), stopping once the entering last_touch_time
    re-converges past ``latest_dirty``. Mutates the passed tracker dict / set for
    newly created touch trackers; ck/qualifying are path-copied."""
    if not state.origin_confirmed:
        return state
    origin_id = state.origin.record_id
    ck = state.ck
    qualifying = state.qualifying
    # Entering last_touch_time. With routing, intermediate geometric-miss touches
    # are never processed for this origin, so ck is sparse -- but a miss never
    # changes last_touch_time, so the checkpoint carried into ``from_pos`` is
    # exactly the value at the greatest stored position <= from_pos.
    floor = ck.floor_item(from_pos)
    assert floor is not None
    last_time = floor[1]
    j = from_pos
    while j < registry_len:
        touch = registry.get(j)
        old_next = ck.get(j + 1)
        was_qualified = j in qualifying
        qualified = False
        if touch is not None and _sr_geometric_ok(state, touch):
            touch_time = touch.meaningful_confirmation_time_utc
            if touch_time > last_time:
                touch_index = candle_index_by_id[touch.pivot_candle_record_ids[-1]]
                if touch_index + 1 < n:
                    has_opp = _sr_has_opposite_between(
                        opposite_times, last_time, touch_time
                    )
                    if has_opp:
                        touch_key = (origin_id, touch.record_id)
                        tracker = new_touch_trackers.get(touch_key)
                        if tracker is None:
                            tracker = _advance_reaction_tracker(
                                _create_reaction_tracker(
                                    touch_index + 1,
                                    state.zone_top,
                                    state.zone_bottom,
                                    state.is_support,
                                ),
                                candles,
                                atr_values,
                                configuration,
                            )
                            new_touch_trackers[touch_key] = tracker
                            if not tracker.permanent:
                                non_permanent_touches.add(touch_key)
                        if tracker.confirming_candle_index is not None:
                            qualified = True
        if qualified and not was_qualified:
            qualifying = qualifying.set(j, touch)  # type: ignore[arg-type]
        elif not qualified and was_qualified:
            qualifying = qualifying.delete(j)
        new_next = (
            touch.meaningful_confirmation_time_utc  # type: ignore[union-attr]
            if qualified
            else last_time
        )
        ck = ck.set(j + 1, new_next)
        last_time = new_next
        j += 1
        if j > latest_dirty and new_next == old_next:
            break
    candidate = _sr_build_candidate(state, qualifying, new_touch_trackers, candles)
    return _SrOriginState(
        origin=state.origin,
        is_support=state.is_support,
        zone_top=state.zone_top,
        zone_bottom=state.zone_bottom,
        zone_depth=state.zone_depth,
        touch_tolerance=state.touch_tolerance,
        pierce_tolerance=state.pierce_tolerance,
        origin_pos=state.origin_pos,
        origin_confirmed=state.origin_confirmed,
        ck=ck,
        qualifying=qualifying,
        candidate=candidate,
    )


def _advance_sr_frontier(
    prior: _SupportResistanceFrontier,
    candles: list[NormalizedCandle],
    atr_values: list[Decimal | None],
    confirmed_swings: tuple[ConfirmedSwing, ...],
    configuration: MarketMeasurementConfiguration,
) -> tuple[tuple[SupportResistanceZoneCandidate, ...], _SupportResistanceFrontier]:
    candle_index_by_id = {c.record_id: i for i, c in enumerate(candles)}
    n = len(candles)
    swings_changed = confirmed_swings is not prior.prior_swings

    new_origin_trackers = dict(prior.origin_trackers)
    new_touch_trackers = dict(prior.touch_trackers)
    np_origins = set(prior.non_permanent_origins)
    np_touches = set(prior.non_permanent_touches)

    dirty: dict[tuple[SupportResistanceType, UUID], tuple[int, int]] = {}

    def _mark(key: tuple[SupportResistanceType, UUID], pos: int) -> None:
        cur = dirty.get(key)
        if cur is None:
            dirty[key] = (pos, pos)
        else:
            dirty[key] = (min(cur[0], pos), max(cur[1], pos))

    for oid in prior.non_permanent_origins:
        old = prior.origin_trackers[oid]
        new = _advance_reaction_tracker(old, candles, atr_values, configuration)
        new_origin_trackers[oid] = new
        zone = prior.origin_zone.get(oid)
        if (
            zone is not None
            and new.confirming_candle_index != old.confirming_candle_index
        ):
            state = prior.origin_states[(zone, oid)]
            _mark((zone, oid), state.origin_pos + 1)
        if new.permanent:
            np_origins.discard(oid)
    for touch_key in prior.non_permanent_touches:
        old = prior.touch_trackers[touch_key]
        new = _advance_reaction_tracker(old, candles, atr_values, configuration)
        new_touch_trackers[touch_key] = new
        if new.confirming_candle_index != old.confirming_candle_index:
            oid = touch_key[0]
            zone = prior.origin_zone.get(oid)
            if zone is not None:
                pos = prior.zone_pos_by_id[zone].get(touch_key[1])
                if pos is not None:
                    _mark((zone, oid), pos)
        if new.permanent:
            np_touches.discard(touch_key)

    new_states = dict(prior.origin_states)
    new_registry = dict(prior.zone_registry)
    new_registry_len = dict(prior.zone_registry_len)
    new_pos_by_id = {z: dict(m) for z, m in prior.zone_pos_by_id.items()}
    new_opp = dict(prior.zone_opposite_times)
    new_origin_zone = dict(prior.origin_zone)
    new_price_index = dict(prior.zone_price_index)
    new_origin_price_key = dict(prior.origin_price_key)
    new_max_upper = dict(prior.zone_max_upper)
    new_max_pierce = dict(prior.zone_max_pierce)
    new_next_seq = dict(prior.zone_next_seq)
    new_swing_ids = prior.swing_ids
    min_tick = configuration.minimum_price_tick

    if swings_changed:
        new_swing_ids = frozenset(s.record_id for s in confirmed_swings)
        added_ids = new_swing_ids - prior.swing_ids
        removed_ids = prior.swing_ids - new_swing_ids
        by_id = {s.record_id: s for s in confirmed_swings}
        for zone_type, origin_type, opposite_type in _SR_ZONE_SPECS:
            is_support = zone_type == SupportResistanceType.SUPPORT
            registry: PersistentMap[ConfirmedSwing] = new_registry.get(
                zone_type, PersistentMap()
            )
            reg_len = new_registry_len.get(zone_type, 0)
            pos_by_id = new_pos_by_id.setdefault(zone_type, {})
            price_index = new_price_index.get(zone_type, PersistentMap[UUID]())
            max_upper = new_max_upper.get(zone_type, Decimal(0))
            max_pierce = new_max_pierce.get(zone_type, Decimal(0))
            for rid in removed_ids:
                pos = pos_by_id.pop(rid, None)
                if pos is not None:
                    registry = registry.delete(pos)
                    removed_state = new_states.get((zone_type, rid))
                    if removed_state is not None:
                        # Only earlier origins whose band contained the removed
                        # swing's price could have used it as a touch.
                        for oid2 in _sr_stab_older_origins(
                            price_index,
                            max_upper,
                            max_pierce,
                            is_support,
                            removed_state.origin.pivot_price,
                            min_tick,
                            new_states,
                            zone_type,
                            pos,
                        ):
                            _mark((zone_type, oid2), pos)
                    pk = new_origin_price_key.pop(rid, None)
                    if pk is not None:
                        price_index = price_index.delete(pk)
                new_states.pop((zone_type, rid), None)
                new_origin_zone.pop(rid, None)
            added_same = sorted(
                (
                    by_id[rid]
                    for rid in added_ids
                    if by_id[rid].swing_type == origin_type
                ),
                key=lambda s: (s.meaningful_confirmation_time_utc, str(s.record_id)),
            )
            for swing in added_same:
                pos = reg_len
                registry = registry.set(pos, swing)
                pos_by_id[swing.record_id] = pos
                reg_len += 1
                new_origin_zone[swing.record_id] = zone_type
                zt, zb, zd, tt, pt = _sr_zone_geometry(swing, is_support, configuration)
                upper_width = zd + tt
                if upper_width > max_upper:
                    max_upper = upper_width
                if pt > max_pierce:
                    max_pierce = pt
                # Route this new touch only to the older origins whose zone band
                # its price enters (one stabbing query), instead of every prior
                # same-type origin. price_index holds all older + earlier-in-batch
                # origins; the new swing is added below so it never stabs itself.
                for oid2 in _sr_stab_older_origins(
                    price_index,
                    max_upper,
                    max_pierce,
                    is_support,
                    swing.pivot_price,
                    min_tick,
                    new_states,
                    zone_type,
                    pos,
                ):
                    _mark((zone_type, oid2), pos)
                new_states[(zone_type, swing.record_id)] = _SrOriginState(
                    origin=swing,
                    is_support=is_support,
                    zone_top=zt,
                    zone_bottom=zb,
                    zone_depth=zd,
                    touch_tolerance=tt,
                    pierce_tolerance=pt,
                    origin_pos=pos,
                    origin_confirmed=False,
                    ck=PersistentMap[datetime]().set(
                        pos + 1, swing.meaningful_confirmation_time_utc
                    ),
                    qualifying=PersistentMap[ConfirmedSwing](),
                    candidate=None,
                )
                seq = new_next_seq.get(zone_type, 0)
                new_next_seq[zone_type] = seq + 1
                price_key = (
                    _sr_price_ticks(swing.pivot_price, min_tick)
                    * (_SR_PRICE_KEY_STRIDE)
                    + seq
                )
                price_index = price_index.set(price_key, swing.record_id)
                new_origin_price_key[swing.record_id] = price_key
                _mark((zone_type, swing.record_id), pos + 1)
            new_registry[zone_type] = registry
            new_registry_len[zone_type] = reg_len
            new_price_index[zone_type] = price_index
            new_max_upper[zone_type] = max_upper
            new_max_pierce[zone_type] = max_pierce
            new_opp[zone_type] = tuple(
                sorted(
                    s.meaningful_confirmation_time_utc
                    for s in confirmed_swings
                    if s.swing_type == opposite_type
                )
            )

    results: list[SupportResistanceZoneCandidate] = []
    for zone_type, _origin_type, _opp in _SR_ZONE_SPECS:
        registry = new_registry.get(zone_type, PersistentMap[ConfirmedSwing]())
        reg_len = new_registry_len.get(zone_type, 0)
        opp_times = new_opp.get(zone_type, ())
        for key, state in list(new_states.items()):
            if key[0] != zone_type:
                continue
            origin_tracker = new_origin_trackers.get(state.origin.record_id)
            if origin_tracker is None:
                origin_index = candle_index_by_id[
                    state.origin.pivot_candle_record_ids[-1]
                ]
                if origin_index + 1 < n:
                    origin_tracker = _advance_reaction_tracker(
                        _create_reaction_tracker(
                            origin_index + 1,
                            state.zone_top,
                            state.zone_bottom,
                            state.is_support,
                        ),
                        candles,
                        atr_values,
                        configuration,
                    )
                    new_origin_trackers[state.origin.record_id] = origin_tracker
                    if not origin_tracker.permanent:
                        np_origins.add(state.origin.record_id)
            confirmed = (
                origin_tracker is not None
                and origin_tracker.confirming_candle_index is not None
            )
            if confirmed != state.origin_confirmed:
                state = _SrOriginState(
                    origin=state.origin,
                    is_support=state.is_support,
                    zone_top=state.zone_top,
                    zone_bottom=state.zone_bottom,
                    zone_depth=state.zone_depth,
                    touch_tolerance=state.touch_tolerance,
                    pierce_tolerance=state.pierce_tolerance,
                    origin_pos=state.origin_pos,
                    origin_confirmed=confirmed,
                    ck=state.ck.set(
                        state.origin_pos + 1,
                        state.origin.meaningful_confirmation_time_utc,
                    ),
                    qualifying=state.qualifying if confirmed else PersistentMap(),
                    candidate=None,
                )
                new_states[key] = state
                _mark(key, state.origin_pos + 1)
            d = dirty.get(key)
            if d is not None and confirmed:
                state = _sr_resume_origin(
                    state,
                    d[0],
                    d[1],
                    registry,
                    reg_len,
                    opp_times,
                    new_touch_trackers,
                    np_touches,
                    candles,
                    atr_values,
                    candle_index_by_id,
                    n,
                    configuration,
                )
                new_states[key] = state
            elif d is not None and not confirmed:
                if state.candidate is not None or len(state.qualifying) > 0:
                    state = _SrOriginState(
                        origin=state.origin,
                        is_support=state.is_support,
                        zone_top=state.zone_top,
                        zone_bottom=state.zone_bottom,
                        zone_depth=state.zone_depth,
                        touch_tolerance=state.touch_tolerance,
                        pierce_tolerance=state.pierce_tolerance,
                        origin_pos=state.origin_pos,
                        origin_confirmed=False,
                        ck=state.ck,
                        qualifying=PersistentMap[ConfirmedSwing](),
                        candidate=None,
                    )
                    new_states[key] = state
            if state.candidate is not None:
                results.append(state.candidate)

    results.sort(key=lambda candidate: candidate.confirmation_time_utc)
    new_frontier = _SupportResistanceFrontier(
        origin_trackers=new_origin_trackers,
        touch_trackers=new_touch_trackers,
        non_permanent_origins=frozenset(np_origins),
        non_permanent_touches=frozenset(np_touches),
        origin_states=new_states,
        prior_swings=confirmed_swings,
        swing_ids=new_swing_ids,
        zone_registry=new_registry,
        zone_registry_len=new_registry_len,
        zone_pos_by_id=new_pos_by_id,
        zone_opposite_times=new_opp,
        origin_zone=new_origin_zone,
        zone_price_index=new_price_index,
        origin_price_key=new_origin_price_key,
        zone_max_upper=new_max_upper,
        zone_max_pierce=new_max_pierce,
        zone_next_seq=new_next_seq,
    )
    return tuple(results), new_frontier


# =====================================================================
# Subsystem 2b-final: exact incremental equal-level and trendline
# frontiers. These reproduce domain.equal_levels.detect_equal_level_clusters
# and domain.trendlines.detect_trendlines EXACTLY (both stay unmodified as
# the differential oracle) but avoid re-running the complete detector over
# the whole confirmed-swing history on every confirmed-swing change. They
# are disclosed duplicates kept in lockstep with the batch detectors by the
# permanent equivalence tests, exactly as _derive_confirmed_swing_candidates
# mirrors domain.swings.detect_confirmed_swings.
# =====================================================================


def _decimal_median(values: list[Decimal]) -> Decimal:
    # Identical to domain.equal_levels._median / domain.trendlines._median.
    ordered = sorted(values)
    midpoint = len(ordered) // 2
    if len(ordered) % 2 == 1:
        return ordered[midpoint]
    return (ordered[midpoint - 1] + ordered[midpoint]) / Decimal(2)


def _confirmed_swing_bar_index(swing: ConfirmedSwing) -> int:
    # The trendline detector keys a swing's bar to the candle index of its
    # LAST pivot candle. pivot_candle_record_ids covers candles
    # [pivot_bar_index .. end] contiguously, so end == start + len - 1. This
    # matches candle_index_by_id[swing.pivot_candle_record_ids[-1]] exactly.
    return swing.pivot_bar_index + len(swing.pivot_candle_record_ids) - 1


def _common_prefix_length(previous: tuple[Any, ...], current: tuple[Any, ...]) -> int:
    limit = min(len(previous), len(current))
    index = 0
    while index < limit and previous[index] == current[index]:
        index += 1
    return index


# ---- Incremental equal levels ---------------------------------------


def _equal_level_sort_key(swing: ConfirmedSwing) -> tuple[Any, UUID]:
    return (swing.meaningful_confirmation_time_utc, swing.record_id)


@dataclass(frozen=True)
class _EqualLevelTypeCache:
    """Per-cluster-type incremental greedy-sweep cache. `sorted_swings` is the
    confirmation-time-ordered swing sequence the sweep consumed; `checkpoints`
    records (sorted_index, emitted_count) at every run start (the sweep reset
    `members` to a fresh swing there, so every earlier cluster was already
    final); `candidates` is the emitted cluster list in sweep order. Because
    the greedy sweep's run boundaries depend only on swings within/adjacent to
    a run, resuming from the latest run start at or before the unchanged
    prefix reproduces the batch sweep exactly."""

    sorted_swings: tuple[ConfirmedSwing, ...] = ()
    checkpoints: tuple[tuple[int, int], ...] = ()
    candidates: tuple[EqualLevelClusterCandidate, ...] = ()


def _sweep_equal_levels_incremental(
    previous: _EqualLevelTypeCache,
    swings_of_type: list[ConfirmedSwing],
    cluster_type: EqualLevelType,
    configuration: MarketMeasurementConfiguration,
) -> _EqualLevelTypeCache:
    sorted_swings = tuple(sorted(swings_of_type, key=_equal_level_sort_key))
    if not sorted_swings:
        return _EqualLevelTypeCache()

    prefix = _common_prefix_length(previous.sorted_swings, sorted_swings)

    resume_index = 0
    resume_emitted = 0
    reused_checkpoints: tuple[tuple[int, int], ...] = ()
    for position, (checkpoint_index, emitted_count) in enumerate(previous.checkpoints):
        if checkpoint_index <= prefix:
            resume_index = checkpoint_index
            resume_emitted = emitted_count
            reused_checkpoints = previous.checkpoints[:position]
        else:
            break

    results: list[EqualLevelClusterCandidate] = list(
        previous.candidates[:resume_emitted]
    )
    checkpoints: list[tuple[int, int]] = list(reused_checkpoints)
    members: list[ConfirmedSwing] = []

    def close_cluster() -> None:
        if len(members) < 2:
            return
        prices = [m.pivot_price for m in members]
        atrs = [m.pivot_reference_atr for m in members]
        reference_atr = _decimal_median(atrs)
        zone_bottom = min(prices)
        zone_top = max(prices)
        results.append(
            EqualLevelClusterCandidate(
                symbol=members[0].symbol,
                timeframe=members[0].timeframe,
                cluster_type=cluster_type,
                component_swing_record_ids=tuple(m.record_id for m in members),
                first_seed_swing_id=members[0].record_id,
                second_seed_swing_id=members[1].record_id,
                cluster_spread=zone_top - zone_bottom,
                equality_tolerance=(
                    configuration.equal_level_tolerance_atr_multiplier * reference_atr
                ),
                reference_atr=reference_atr,
                zone_bottom=zone_bottom,
                zone_top=zone_top,
                representative_price=(zone_bottom + zone_top) / Decimal(2),
                confirmation_time_utc=max(
                    m.meaningful_confirmation_time_utc for m in members
                ),
            )
        )

    index = resume_index
    while index < len(sorted_swings):
        swing = sorted_swings[index]
        if not members:
            checkpoints.append((index, len(results)))
            members = [swing]
            index += 1
            continue

        candidate_prices = [m.pivot_price for m in members] + [swing.pivot_price]
        candidate_atrs = [m.pivot_reference_atr for m in members] + [
            swing.pivot_reference_atr
        ]
        reference_atr = _decimal_median(candidate_atrs)
        tolerance = configuration.equal_level_tolerance_atr_multiplier * reference_atr
        prospective_spread = max(candidate_prices) - min(candidate_prices)

        if prospective_spread <= tolerance:
            members.append(swing)
            index += 1
        else:
            close_cluster()
            members = []
            # Do not advance: this swing opens the next run on the next pass,
            # reproducing the batch sweep's close-then-restart-with-swing.

    close_cluster()

    return _EqualLevelTypeCache(
        sorted_swings=sorted_swings,
        checkpoints=tuple(checkpoints),
        candidates=tuple(results),
    )


def _advance_equal_levels_incremental(
    previous_high: _EqualLevelTypeCache,
    previous_low: _EqualLevelTypeCache,
    new_confirmed_swings: tuple[ConfirmedSwing, ...],
    configuration: MarketMeasurementConfiguration,
) -> tuple[
    _EqualLevelTypeCache, _EqualLevelTypeCache, list[EqualLevelClusterCandidate]
]:
    highs = [s for s in new_confirmed_swings if s.swing_type == SwingType.SWING_HIGH]
    lows = [s for s in new_confirmed_swings if s.swing_type == SwingType.SWING_LOW]
    high_cache = _sweep_equal_levels_incremental(
        previous_high, highs, EqualLevelType.EQUAL_HIGH, configuration
    )
    low_cache = _sweep_equal_levels_incremental(
        previous_low, lows, EqualLevelType.EQUAL_LOW, configuration
    )
    combined = list(high_cache.candidates) + list(low_cache.candidates)
    combined.sort(key=lambda c: c.confirmation_time_utc)
    return high_cache, low_cache, combined


@dataclass
class _MeasurementReplayState:
    """Private, per-timeframe incremental measurement state for subsystem 2b.
    Not part of the public contract surface; owned exclusively by the
    scanner replay path. candles_so_far and confirmed_swings_so_far are
    retained in full (register §44AL classification A / O(T*C), O(A_swings)).
    equal_level_clusters are derived incrementally when confirmed_swings_so_far
    changes (subsystem 2b-final) via a checkpoint-resume of its confirmation-time
    greedy sweep (equal_level_cache_high/low), reproducing the unmodified batch
    detector exactly (it remains the differential oracle). A6-F6F-A: trendlines
    are a category-D output (nothing in the incremental replay consumes them --
    structure reads confirmed swings, POI reads SR zones / equal levels), so NO
    trendline work runs on the per-candle advance; the whole history is derived
    on demand from the batch detector by _materialize_trendlines. This removes
    the per-candle O(A_swings^2)-cumulative trendline frontier from FINAL_ONLY,
    which only ever produced intermediate results the run discarded.
    support_resistance_zones is derived every candle via persistent
    _ReactionTracker state (O(1) amortized per reaction candidate) rather than
    the unmodified batch detector's O(candles) internal rescans, since a
    reaction's bounded window can newly resolve purely from candle growth with
    no new confirmed swing involved."""

    resolver: _IdentityResolver
    rule_version_text: str
    configuration: MarketMeasurementConfiguration
    candles_so_far: list[NormalizedCandle] = field(default_factory=list)
    atr_state: _AtrIncrementalState = field(default_factory=_AtrIncrementalState)
    atr_values_so_far: list[Decimal | None] = field(default_factory=list)
    raw_pivots_so_far: list[_Pivot] = field(default_factory=list)
    confirmation_trackers: dict[
        tuple[int, int, SwingType], _PivotConfirmationTracker
    ] = field(default_factory=dict)
    # A6-F6D: incremental support/resistance replay frontier (byte-identical to
    # _derive_support_resistance_zone_candidates at every prefix; that batch
    # helper remains the untouched oracle).
    sr_frontier: _SupportResistanceFrontier = field(
        default_factory=_SupportResistanceFrontier
    )
    confirmed_swing_candidates_so_far: tuple[ConfirmedSwingCandidate, ...] = ()
    confirmed_swings_so_far: tuple[ConfirmedSwing, ...] = ()
    # A6-F6C: displacement observations and trendlines are category-D outputs --
    # consumed only by the public MeasurementAnalysis / ledger, never by the
    # next-candle structure or POI logic. Their *candidates* are carried here and
    # the public records are finalized (resolved + fingerprinted) on demand by
    # _materialize_displacement / _materialize_trendlines at the analysis / ledger
    # boundary (finalize()/event_ledger() under the F6A lazy kernel), instead of
    # re-finalizing the whole cumulative set every candle / swing-change.
    displacement_candidates_so_far: tuple[Any, ...] = ()
    equal_level_clusters_so_far: tuple[EqualLevelCluster, ...] = ()
    support_resistance_zones_so_far: tuple[SupportResistanceZone, ...] = ()
    equal_level_cache_high: _EqualLevelTypeCache = field(
        default_factory=_EqualLevelTypeCache
    )
    equal_level_cache_low: _EqualLevelTypeCache = field(
        default_factory=_EqualLevelTypeCache
    )
    # A3-C: shared finalized-record reuse cache (record_id -> (fields, object))
    # spanning confirmed swings / clusters / zones / trendlines. record_ids are
    # globally unique across categories (derived from output_type + semantic_key),
    # so one map is exact. _finalize reuses the object for any record whose
    # fingerprint-determining fields are unchanged, rebuilding only the genuinely
    # dirty mutable-frontier records. Published only on a successful advance.
    finalize_reuse_cache: dict[UUID, tuple[dict[str, object], ContractModel]] = field(
        default_factory=dict
    )


def _create_initial_measurement_replay_state(
    identity_provider: DerivedOutputIdentityProvider,
    configuration: MarketMeasurementConfiguration,
) -> _MeasurementReplayState:
    return _MeasurementReplayState(
        resolver=_IdentityResolver(identity_provider),
        rule_version_text=str(configuration.rule_version),
        configuration=configuration,
    )


def _materialize_displacement(
    state: _MeasurementReplayState,
) -> tuple[DisplacementObservation, ...]:
    """A6-F6C: finalize displacement observations from the deferred candidates.
    Byte-identical to the pre-deferral per-candle finalize -- displacement is
    append-only and record ids/fingerprints are content-addressed, so finalizing
    the concatenated candidate stream once yields the same records in the same
    order."""
    return _finalize(
        list(state.displacement_candidates_so_far),
        DerivedOutputType.DISPLACEMENT_OBSERVATION,
        DisplacementObservation,
        lambda c: _displacement_semantic_key(c, state.rule_version_text),
        lambda c: {},
        frozenset(),
        state.configuration,
        state.resolver,
    )


def _materialize_trendlines(
    state: _MeasurementReplayState,
) -> tuple[Trendline, ...]:
    """A6-F6F-A: trendlines are a category-D output -- nothing in the incremental
    replay (structure consumes confirmed swings; POI consumes SR zones / equal
    levels) reads them, they are only ever published via MeasurementAnalysis /
    the event ledger / the final report. So NO trendline work runs on the
    per-candle advance; the complete history is derived on demand here straight
    from the UNMODIFIED batch detector over the confirmed-swing history, then
    finalized. This is byte-identical to the batch analysis by construction (the
    same ``detect_trendlines`` call the batch oracle uses at line ~371) and, for
    FINAL_ONLY, replaces the whole per-candle incremental frontier -- which only
    ever produced intermediate results the run threw away -- with a single
    end-of-run derivation. Callers that materialize per candle (ALL retention)
    pay one batch derivation per requested snapshot, which the differential
    tests still verify exactly."""
    trendline_candidates = detect_trendlines(
        tuple(state.candles_so_far),
        state.confirmed_swings_so_far,
        state.configuration,
    )
    return _finalize(
        list(trendline_candidates),
        DerivedOutputType.TRENDLINE,
        Trendline,
        lambda c: _trendline_semantic_key(c, state.rule_version_text),
        lambda c: {"availability_time_utc": c.confirmation_time_utc},
        frozenset(),
        state.configuration,
        state.resolver,
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

    # A3-C: reuse cache carried forward from the prior state (a local copy, so a
    # raised advance never mutates the caller's cache) and updated in place by
    # each _finalize below. Carrying it forward preserves reuse for categories
    # that are not re-finalized on this candle (e.g. swings when they did not
    # change), while re-finalized categories overwrite their entries.
    new_finalize_reuse: dict[UUID, tuple[dict[str, object], ContractModel]] = dict(
        state.finalize_reuse_cache
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
            prior_reuse=state.finalize_reuse_cache,
            new_reuse=new_finalize_reuse,
        )

    new_equal_level_clusters = state.equal_level_clusters_so_far
    new_equal_level_cache_high = state.equal_level_cache_high
    new_equal_level_cache_low = state.equal_level_cache_low
    swings_changed = new_confirmed_swings != state.confirmed_swings_so_far
    if swings_changed:
        # A still-open same-type pivot run's collapsed representative (the
        # most extreme candidate so far) can change identity as later raw
        # pivots extend it, even after its earlier extreme already produced
        # a confirmed swing at the same list position: a length check alone
        # would miss that same-length content change, so this must key off
        # full-value inequality, not a length comparison. Equal-levels depend
        # only on confirmed_swings, so gating on swings_changed is exactly
        # correct — and their re-derivation is incremental (subsystem 2b-final):
        # only the frontier of the confirmed-swing diff is reprocessed, not the
        # whole history, while reproducing the unmodified batch detector exactly
        # (it remains the differential oracle in the permanent equivalence
        # tests). A6-F6F-A: trendlines (category D, see _materialize_trendlines)
        # do NO per-candle work at all now -- they are derived on demand.
        (
            new_equal_level_cache_high,
            new_equal_level_cache_low,
            equal_level_candidates,
        ) = _advance_equal_levels_incremental(
            state.equal_level_cache_high,
            state.equal_level_cache_low,
            new_confirmed_swings,
            configuration,
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
            prior_reuse=state.finalize_reuse_cache,
            new_reuse=new_finalize_reuse,
        )

    # Unlike equal-levels, a support/resistance zone's reaction
    # evaluation searches a bounded window of RAW candles following the
    # origin/touch swing; a window that was truncated by the current candle
    # count can newly resolve as more candles arrive with no new confirmed
    # swing involved at all. Derivation must therefore run every candle (not
    # only when swings_changed) — but via persistent _ReactionTracker state
    # (O(1) amortized per candidate) rather than the unmodified batch
    # detector's O(candles) internal rescans, preserving (not optimizing
    # away) only the O(A_swings^2) outer walk per register §44AI/§44AL.
    support_resistance_candidates, new_sr_frontier = _advance_sr_frontier(
        state.sr_frontier,
        new_candles_so_far,
        new_atr_values_so_far,
        new_confirmed_swings,
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
        prior_reuse=state.finalize_reuse_cache,
        new_reuse=new_finalize_reuse,
    )

    # A6-F6C: detect displacement candidates this candle (bounded window) and
    # append them to the deferred candidate stream -- DO NOT finalize per candle.
    # _materialize_displacement finalizes the whole stream once at the boundary.
    new_displacement_candidates = state.displacement_candidates_so_far
    window = configuration.range_context_window
    if absolute_index >= window:
        displacement_slice = tuple(new_candles_so_far[absolute_index - window :])
        displacement_candidates = detect_displacement_observations(
            displacement_slice, configuration
        )
        new_displacement_candidates = (
            *state.displacement_candidates_so_far,
            *displacement_candidates,
        )

    return _MeasurementReplayState(
        resolver=state.resolver,
        rule_version_text=state.rule_version_text,
        configuration=state.configuration,
        candles_so_far=new_candles_so_far,
        atr_state=new_atr_state,
        atr_values_so_far=new_atr_values_so_far,
        raw_pivots_so_far=new_raw_pivots_so_far,
        confirmation_trackers=new_confirmation_trackers,
        sr_frontier=new_sr_frontier,
        confirmed_swing_candidates_so_far=new_confirmed_swing_candidates,
        confirmed_swings_so_far=new_confirmed_swings,
        displacement_candidates_so_far=new_displacement_candidates,
        equal_level_clusters_so_far=new_equal_level_clusters,
        support_resistance_zones_so_far=new_support_resistance_zones,
        equal_level_cache_high=new_equal_level_cache_high,
        equal_level_cache_low=new_equal_level_cache_low,
        finalize_reuse_cache=new_finalize_reuse,
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
        displacement_observations=_materialize_displacement(state),
        equal_level_clusters=state.equal_level_clusters_so_far,
        support_resistance_zones=state.support_resistance_zones_so_far,
        trendlines=_materialize_trendlines(state),
    )


def _measurement_replay_state_to_view(
    state: _MeasurementReplayState,
) -> MarketMeasurementAnalysis:
    """O(1) unvalidated projection for the FINAL_ONLY advance hot path (A6-F2).

    Field-identical to :func:`_measurement_replay_state_to_analysis`, but built
    via ``model_construct`` so it skips ``ContractModel``'s
    ``revalidate_instances="always"`` re-validation of every historical nested
    record. That per-candle re-validation of the whole cumulative measurement
    analysis (all confirmed swings / displacements / equal levels / SR zones /
    trendlines, each re-running UUIDv7 + fingerprint + cross-field validators)
    is the O(history)-per-candle -> O(N^2) advance-hot-path cost.

    Safe because every field is an already-validated immutable record pulled
    straight from the incremental state (nothing to normalise or coerce), and
    the public ``finalize()`` boundary still constructs the fully-validated
    analysis. The two builders produce byte-identical models (same field
    values, ``==``, serialization, and content fingerprint), proven by the
    scan_market differential across every bounded prefix.
    """
    symbol = state.candles_so_far[0].symbol if state.candles_so_far else None
    timeframe = state.candles_so_far[0].timeframe if state.candles_so_far else None
    # A6-F6C: the per-candle view feeds structure (confirmed_swings) and the POI
    # detector frontier (support_resistance_zones + equal_level_clusters). Neither
    # reads displacement_observations or trendlines, so they are left empty here
    # (deferred, category D) rather than finalized every candle. The fully-
    # materialized public analysis (_measurement_replay_state_to_analysis) still
    # populates them exactly at the finalize/ledger boundary.
    return MarketMeasurementAnalysis.model_construct(
        symbol=symbol,
        timeframe=timeframe,
        analyzed_candle_count=len(state.candles_so_far),
        confirmed_swings=state.confirmed_swings_so_far,
        displacement_observations=(),
        equal_level_clusters=state.equal_level_clusters_so_far,
        support_resistance_zones=state.support_resistance_zones_so_far,
        trendlines=(),
    )
