import hashlib
import json
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, timedelta
from decimal import Decimal
from enum import Enum
from itertools import pairwise
from typing import Any, NamedTuple, cast
from uuid import UUID

from btmm_ai_scanner.btmm.configuration import BtmmConfiguration, validate_configuration
from btmm_ai_scanner.btmm.current_state import CurrentBtmmState
from btmm_ai_scanner.btmm.enums import BtmmDirection
from btmm_ai_scanner.btmm.lifecycle import (
    BtmmLifecycleTransition,
    TransitionCandidate,
    run_btmm_lifecycle,
)
from btmm_ai_scanner.btmm.lifecycle_scheduler import (
    BtmmSetupEventScheduler,
    advance_btmm_scheduler,
    create_btmm_scheduler,
)
from btmm_ai_scanner.btmm.observation import BtmmObservation
from btmm_ai_scanner.btmm.reviewed_evidence import BtmmReviewedEvidence
from btmm_ai_scanner.btmm.setup_delta import derive_btmm_setup_delta, is_btmm_eligible
from btmm_ai_scanner.config.enums import InternalSymbol, Timeframe
from btmm_ai_scanner.contracts.normalized_candle import NormalizedCandle
from btmm_ai_scanner.contracts.types import ContractModel, SemVer
from btmm_ai_scanner.domain import (
    DerivedIdentityCollisionError,
    DerivedOutputIdentityProvider,
    DuplicateCandleRecordError,
    MarketMeasurementAnalysis,
    MixedSymbolAnalysisError,
    UnsortedCandleSequenceError,
)
from btmm_ai_scanner.domain.enums import DerivedOutputType
from btmm_ai_scanner.measurements.atr import (
    IncrementalAtrState,
    advance_incremental_atr,
    compute_atr_series,
    initial_incremental_atr_state,
)
from btmm_ai_scanner.poi.analyzer import PoiAnalysis
from btmm_ai_scanner.poi.enums import PoiDirection, PoiLifecycleTransitionType
from btmm_ai_scanner.poi.lifecycle import LifecycleWalkResult as PoiLifecycleWalkResult
from btmm_ai_scanner.poi.lifecycle import PoiLifecycleTransition
from btmm_ai_scanner.poi.lifecycle import TransitionCandidate as PoiTransitionCandidate
from btmm_ai_scanner.poi.observation import PoiObservation

_TIMEFRAME_STRENGTH_RANK: dict[Timeframe, int] = {
    Timeframe.M1: 1,
    Timeframe.M5: 2,
    Timeframe.M15: 3,
}

_DIRECTION_MAP: dict[PoiDirection, BtmmDirection] = {
    PoiDirection.BULLISH: BtmmDirection.BULLISH_BTMM,
    PoiDirection.BEARISH: BtmmDirection.BEARISH_BTMM,
}


class DuplicateBtmmTimeframeInputError(ValueError):
    pass


class UnsortedBtmmTimeframeInputError(ValueError):
    pass


class InputPrefixMismatchError(ValueError):
    pass


class MissingSourcePoiRecordError(ValueError):
    pass


class ImpossibleBtmmLifecycleTransitionError(ValueError):
    pass


class BtmmTimeframeInput(NamedTuple):
    timeframe: Timeframe
    candles: tuple[NormalizedCandle, ...]
    measurement_analysis: MarketMeasurementAnalysis


class BtmmAnalysis(ContractModel):
    symbol: InternalSymbol | None
    analyzed_timeframes: tuple[Timeframe, ...]
    analyzed_candle_count_by_timeframe: tuple[int, ...]
    btmm_observations: tuple[BtmmObservation, ...]
    btmm_lifecycle_transitions: tuple[BtmmLifecycleTransition, ...]
    current_btmm_states: tuple[CurrentBtmmState, ...]


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
    if isinstance(value, timedelta):
        total_microseconds = (
            value.days * 86_400_000_000 + value.seconds * 1_000_000 + value.microseconds
        )
        return format(Decimal(total_microseconds) / Decimal(1_000_000), "f")
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
    configuration: BtmmConfiguration,
    resolver: _IdentityResolver,
    *,
    prior_reuse: dict[UUID, tuple[dict[str, object], ContractModel]] | None = None,
    new_reuse: dict[UUID, tuple[dict[str, object], ContractModel]] | None = None,
) -> tuple[ContractT, ...]:
    """A3-C: with ``prior_reuse``/``new_reuse`` (the incremental replay path) an
    unchanged finalized record is reused verbatim (no SHA-256, no construction).
    BTMM lifecycle transitions are immutable once emitted, so this is a permanent
    reuse; the batch oracle passes neither cache and is byte-for-byte unchanged.
    ``new_reuse`` is a caller-owned local published only on a successful advance."""
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


def _validate_bundle_candles(
    timeframe: Timeframe, candles: tuple[NormalizedCandle, ...]
) -> None:
    if len(candles) == 0:
        return

    seen_record_ids: set[UUID] = set()
    for candle in candles:
        if candle.record_id in seen_record_ids:
            raise DuplicateCandleRecordError(
                f"record_id {candle.record_id} appears more than once in the input."
            )
        seen_record_ids.add(candle.record_id)
        if candle.timeframe != timeframe:
            raise InputPrefixMismatchError(
                f"candle {candle.record_id} carries timeframe {candle.timeframe},"
                f" which disagrees with its declared bundle timeframe {timeframe}."
            )

    for previous, current in pairwise(candles):
        if current.event_time_utc <= previous.event_time_utc:
            raise UnsortedCandleSequenceError(
                "candles must be canonically ordered by strictly increasing"
                " event_time_utc."
            )


def _validate_timeframe_inputs(
    timeframe_inputs: tuple[BtmmTimeframeInput, ...],
) -> None:
    seen_timeframes: set[Timeframe] = set()

    for bundle in timeframe_inputs:
        if bundle.timeframe not in _TIMEFRAME_STRENGTH_RANK:
            raise UnsortedBtmmTimeframeInputError(
                f"timeframe {bundle.timeframe} is not a supported BTMM formation"
                " timeframe; only M1, M5, and M15 bundles are accepted."
            )
        if bundle.timeframe in seen_timeframes:
            raise DuplicateBtmmTimeframeInputError(
                f"timeframe {bundle.timeframe} appears in more than one bundle."
            )
        seen_timeframes.add(bundle.timeframe)

        _validate_bundle_candles(bundle.timeframe, bundle.candles)

        analysis = bundle.measurement_analysis
        if analysis.analyzed_candle_count != len(bundle.candles):
            raise InputPrefixMismatchError(
                "measurement_analysis.analyzed_candle_count does not match the"
                " number of candles supplied for the same bundle."
            )
        if len(bundle.candles) > 0:
            bundle_symbol = bundle.candles[0].symbol
            if analysis.symbol is not None and analysis.symbol != bundle_symbol:
                raise InputPrefixMismatchError(
                    "measurement_analysis.symbol disagrees with the bundle's own"
                    " candles."
                )
            if (
                analysis.timeframe is not None
                and analysis.timeframe != bundle.timeframe
            ):
                raise InputPrefixMismatchError(
                    "measurement_analysis.timeframe disagrees with the bundle's"
                    " own declared timeframe."
                )

    ranks = [_TIMEFRAME_STRENGTH_RANK[bundle.timeframe] for bundle in timeframe_inputs]
    if ranks != sorted(ranks):
        raise UnsortedBtmmTimeframeInputError(
            "timeframe_inputs must be supplied in ascending timeframe-strength order."
        )


def _validate_reviewed_evidence(
    reviewed_evidence: tuple[BtmmReviewedEvidence, ...],
    poi_by_record_id: dict[UUID, PoiObservation],
) -> None:
    seen_source_poi_ids: set[UUID] = set()
    for evidence in reviewed_evidence:
        if evidence.source_poi_record_id in seen_source_poi_ids:
            raise InputPrefixMismatchError(
                f"duplicate reviewed evidence supplied for source POI"
                f" {evidence.source_poi_record_id}; at most one snapshot per"
                " source POI per analyzer call is permitted."
            )
        seen_source_poi_ids.add(evidence.source_poi_record_id)

        source_poi = poi_by_record_id.get(evidence.source_poi_record_id)
        if source_poi is None:
            raise MissingSourcePoiRecordError(
                f"reviewed evidence references source_poi_record_id"
                f" {evidence.source_poi_record_id}, which is not present in the"
                " supplied PoiAnalysis."
            )
        if evidence.symbol != source_poi.symbol:
            raise InputPrefixMismatchError(
                "reviewed evidence symbol disagrees with its referenced source"
                " POI's own symbol."
            )
        if evidence.timeframe != source_poi.source_timeframe:
            raise InputPrefixMismatchError(
                "reviewed evidence timeframe disagrees with its referenced"
                " source POI's own source_timeframe."
            )


def _all_symbols(
    timeframe_inputs: tuple[BtmmTimeframeInput, ...],
    poi_analysis: PoiAnalysis,
    reviewed_evidence: tuple[BtmmReviewedEvidence, ...],
) -> set[InternalSymbol]:
    symbols: set[InternalSymbol] = set()
    for bundle in timeframe_inputs:
        for candle in bundle.candles:
            symbols.add(candle.symbol)
    for observation in poi_analysis.poi_observations:
        symbols.add(observation.symbol)
    for evidence in reviewed_evidence:
        symbols.add(evidence.symbol)
    return symbols


def analyze_btmm(
    timeframe_inputs: tuple[BtmmTimeframeInput, ...],
    poi_analysis: PoiAnalysis,
    reviewed_evidence: tuple[BtmmReviewedEvidence, ...],
    configuration: BtmmConfiguration,
    identity_provider: DerivedOutputIdentityProvider,
) -> BtmmAnalysis:
    validate_configuration(configuration)

    if len(timeframe_inputs) == 0 or len(poi_analysis.poi_observations) == 0:
        return BtmmAnalysis(
            symbol=None,
            analyzed_timeframes=(),
            analyzed_candle_count_by_timeframe=(),
            btmm_observations=(),
            btmm_lifecycle_transitions=(),
            current_btmm_states=(),
        )

    _validate_timeframe_inputs(timeframe_inputs)

    poi_by_record_id: dict[UUID, PoiObservation] = {
        observation.record_id: observation
        for observation in poi_analysis.poi_observations
    }
    _validate_reviewed_evidence(reviewed_evidence, poi_by_record_id)

    if len(_all_symbols(timeframe_inputs, poi_analysis, reviewed_evidence)) > 1:
        raise MixedSymbolAnalysisError(
            "analyze_btmm requires exactly one InternalSymbol across every"
            " supplied bundle, PoiObservation, and BtmmReviewedEvidence record."
        )

    resolver = _IdentityResolver(identity_provider)
    rule_version_text = str(configuration.rule_version)

    symbol: InternalSymbol | None = None
    for bundle in timeframe_inputs:
        if len(bundle.candles) > 0:
            symbol = bundle.candles[0].symbol
            break
    if symbol is None and len(poi_analysis.poi_observations) > 0:
        symbol = poi_analysis.poi_observations[0].symbol

    candles_by_timeframe: dict[Timeframe, tuple[NormalizedCandle, ...]] = {}
    atr_by_timeframe: dict[Timeframe, tuple[Decimal | None, ...]] = {}
    for bundle in timeframe_inputs:
        candles_by_timeframe[bundle.timeframe] = bundle.candles
        atr_by_timeframe[bundle.timeframe] = compute_atr_series(bundle.candles, 14)

    reviewed_evidence_by_poi: dict[UUID, BtmmReviewedEvidence] = {
        evidence.source_poi_record_id: evidence for evidence in reviewed_evidence
    }

    supported_timeframes = (
        configuration.formation_timeframes | configuration.supporting_only_timeframes
    )

    observations_list: list[BtmmObservation] = []
    all_transitions: list[TransitionCandidate] = []
    current_state_fields_by_setup: dict[UUID, Any] = {}
    setup_id_by_poi: dict[UUID, UUID] = {}

    for source_poi in poi_analysis.poi_observations:
        if source_poi.poi_type not in configuration.eligible_poi_types:
            continue
        if source_poi.source_timeframe not in supported_timeframes:
            continue

        semantic_key = (
            symbol.value if symbol is not None else source_poi.symbol.value,
            source_poi.source_timeframe.value,
            str(source_poi.record_id),
            rule_version_text,
        )
        record_id = resolver.resolve(DerivedOutputType.BTMM_OBSERVATION, semantic_key)
        provenance_id = resolver.resolve(
            DerivedOutputType.BTMM_OBSERVATION, (*semantic_key, "provenance")
        )
        setup_id_by_poi[source_poi.record_id] = record_id

        observation_fields: dict[str, object] = {
            "symbol": source_poi.symbol,
            "source_timeframe": source_poi.source_timeframe,
            "btmm_direction": _DIRECTION_MAP[source_poi.direction],
            "source_poi_record_id": source_poi.record_id,
            "source_poi_type": source_poi.poi_type,
            "source_poi_direction": source_poi.direction,
            "candidate_event_time_utc": source_poi.confirmation_time_utc,
            "availability_time_utc": source_poi.availability_time_utc,
            "rule_version": configuration.rule_version,
            "contract_version": configuration.contract_version,
            "schema_version": configuration.schema_version,
            "evidence_classification": configuration.evidence_classification,
            "provenance_id": provenance_id,
        }
        content_fingerprint = _compute_content_fingerprint(observation_fields)
        observations_list.append(
            BtmmObservation(
                record_id=record_id,
                content_fingerprint=content_fingerprint,
                **observation_fields,  # type: ignore[arg-type]
            )
        )

        bundle_candles = candles_by_timeframe.get(source_poi.source_timeframe, ())
        bundle_atr = atr_by_timeframe.get(source_poi.source_timeframe, ())

        walk = run_btmm_lifecycle(
            symbol=source_poi.symbol,
            source_timeframe=source_poi.source_timeframe,
            btmm_setup_record_id=record_id,
            source_poi=source_poi,
            candidate_availability_time_utc=source_poi.availability_time_utc,
            bundle_candles=bundle_candles,
            atr_values=bundle_atr,
            poi_lifecycle_transitions=poi_analysis.poi_lifecycle_transitions,
            reviewed_evidence=reviewed_evidence_by_poi.get(source_poi.record_id),
            configuration=configuration,
        )

        all_transitions.extend(walk.transitions)
        current_state_fields_by_setup[record_id] = walk.final_fields

    def transition_semantic_key(candidate: TransitionCandidate) -> tuple[str, ...]:
        trigger_reference = (
            str(candidate.triggering_candle_record_id)
            if candidate.triggering_candle_record_id is not None
            else (
                "reviewed:"
                + candidate.triggering_reviewed_evidence_availability_time_utc.isoformat()
                if candidate.triggering_reviewed_evidence_availability_time_utc
                is not None
                else "none"
            )
        )
        return (
            candidate.symbol.value,
            candidate.timeframe.value,
            str(candidate.btmm_setup_record_id),
            candidate.transition_type.value,
            trigger_reference,
            rule_version_text,
        )

    lifecycle_transitions = _finalize(
        list(all_transitions),
        DerivedOutputType.BTMM_LIFECYCLE_TRANSITION,
        BtmmLifecycleTransition,
        transition_semantic_key,
        lambda _c: {},
        frozenset(),
        configuration,
        resolver,
    )

    latest_transition_by_setup: dict[UUID, UUID] = {}
    for transition in lifecycle_transitions:
        latest_transition_by_setup[transition.btmm_setup_record_id] = (
            transition.record_id
        )

    current_states: list[CurrentBtmmState] = []
    for observation in observations_list:
        setup_id = observation.record_id
        state_fields = current_state_fields_by_setup[setup_id]

        semantic_key = (
            observation.symbol.value,
            observation.source_timeframe.value,
            str(observation.source_poi_record_id),
            rule_version_text,
        )
        record_id = resolver.resolve(DerivedOutputType.CURRENT_BTMM_STATE, semantic_key)
        provenance_id = resolver.resolve(
            DerivedOutputType.CURRENT_BTMM_STATE, (*semantic_key, "provenance")
        )

        fields: dict[str, object] = {
            "symbol": observation.symbol,
            "timeframe": observation.source_timeframe,
            "btmm_setup_record_id": setup_id,
            "btmm_direction": observation.btmm_direction,
            "source_poi_type": observation.source_poi_type,
            "primary_state": state_fields.primary_state,
            "formation_stage": state_fields.formation_stage,
            "market_direction_status": state_fields.market_direction_status,
            "analytical_framework_status": state_fields.analytical_framework_status,
            "session_status": state_fields.session_status,
            "accuracy_gate_status": state_fields.accuracy_gate_status,
            "interaction_class": state_fields.interaction_class,
            "reaction_gate_status": state_fields.reaction_gate_status,
            "reaction_classification": state_fields.reaction_classification,
            "reaction_speed_gate_status": state_fields.reaction_speed_gate_status,
            "reaction_speed_classification": state_fields.reaction_speed_classification,
            "formation_timeframe_gate_status": state_fields.formation_timeframe_gate_status,
            "volume_pillar_status": state_fields.volume_pillar_status,
            "liquidity_evidence_status": state_fields.liquidity_evidence_status,
            "liquidity_location": state_fields.liquidity_location,
            "liquidity_evidence_source": state_fields.liquidity_evidence_source,
            "reviewed_evidence_availability_time_utc": (
                state_fields.reviewed_evidence_availability_time_utc
            ),
            "cancellation_reason": state_fields.cancellation_reason,
            "blocked_reason": state_fields.blocked_reason,
            "latest_lifecycle_transition_id": latest_transition_by_setup.get(setup_id),
            "availability_time_utc": state_fields.availability_time_utc,
            "rule_version": configuration.rule_version,
            "contract_version": configuration.contract_version,
            "schema_version": configuration.schema_version,
            "evidence_classification": configuration.evidence_classification,
            "provenance_id": provenance_id,
        }
        content_fingerprint = _compute_content_fingerprint(fields)
        current_states.append(
            CurrentBtmmState(
                record_id=record_id,
                content_fingerprint=content_fingerprint,
                **fields,  # type: ignore[arg-type]
            )
        )

    observations = tuple(
        sorted(
            observations_list,
            key=lambda o: (
                o.availability_time_utc,
                o.source_timeframe.value,
                o.btmm_direction.value,
                str(o.source_poi_record_id),
                str(o.record_id),
            ),
        )
    )
    lifecycle_transitions = tuple(
        sorted(
            lifecycle_transitions,
            key=lambda t: (
                t.availability_time_utc,
                t.event_time_utc,
                t.transition_type.value,
                str(t.btmm_setup_record_id),
                str(t.record_id),
            ),
        )
    )
    current_states = sorted(
        current_states,
        key=lambda s: (s.symbol.value, s.timeframe.value, str(s.btmm_setup_record_id)),
    )

    return BtmmAnalysis(
        symbol=symbol,
        analyzed_timeframes=tuple(bundle.timeframe for bundle in timeframe_inputs),
        analyzed_candle_count_by_timeframe=tuple(
            len(bundle.candles) for bundle in timeframe_inputs
        ),
        btmm_observations=observations,
        btmm_lifecycle_transitions=lifecycle_transitions,
        current_btmm_states=tuple(current_states),
    )


# =====================================================================
# Subsystem 2e / A6-B2-C: private incremental BTMM replay state (single
# timeframe), wired to the accepted B2-A resumable cursor
# (btmm.lifecycle_cursor, via the B2-B persistent event-driven scheduler in
# btmm.lifecycle_scheduler). The public analyze_btmm above is preserved
# byte-for-byte and remains the sole semantic oracle; run_btmm_lifecycle is
# never called from the incremental hot path below.
#
# BTMM creates exactly one setup per BTMM-eligible source POI (keyed by the
# POI's own stable record_id). Setup construction, source-POI-transition
# routing, and reviewed-evidence routing are all driven by BOUNDED per-candle
# deltas -- never a scan of the full historical POI or setup universe:
#   * new/changed/removed POIs arrive as the POI incremental engine's own
#     bounded per-candle delta (exposed on _PoiReplayState as
#     new_pois_for_btmm / changed_pois_for_btmm / removed_poi_ids_for_btmm --
#     see poi.analyzer, A6-B2-C; zero new POI-side computation).
#   * newly-relevant source-POI lifecycle transitions (GENUINE_INVALIDATION_
#     CONFIRMED / FALSE_INVALIDATION_CONFIRMED -- the only two types
#     materialize_btmm_cursor ever reads) arrive via the POI scheduler's own
#     bounded scheduler.last_walks for this candle.
#   * reviewed evidence arrives as the externally-supplied set, diffed against
#     what this state has already relayed.
# advance_btmm_scheduler (B2-B, unmodified) turns these into the exact wake
# set and advances only those setups' B2-A cursors; every other setup is
# carried forward by reference.
#
# Observations and lifecycle transitions are held in content-addressed caches
# (observation_cache / transition_cache) so the per-candle work is exactly
# proportional to the bounded delta, not the historical setup count; the
# public BtmmAnalysis -- including CurrentBtmmState (A6-B2-C item 14) -- is
# materialized only when actually requested (_btmm_replay_state_to_analysis /
# _combine_btmm_replay_states), never inside the advance itself.
# =====================================================================


_RELEVANT_POI_TRANSITION_TYPES: frozenset[PoiLifecycleTransitionType] = frozenset(
    {
        PoiLifecycleTransitionType.GENUINE_INVALIDATION_CONFIRMED,
        PoiLifecycleTransitionType.FALSE_INVALIDATION_CONFIRMED,
    }
)


def _relay_poi_transition(
    candidate: PoiTransitionCandidate,
    resolver: _IdentityResolver,
    configuration: BtmmConfiguration,
) -> PoiLifecycleTransition:
    """A valid, internally-consistent PoiLifecycleTransition carrying exactly
    the fields materialize_btmm_cursor reads (poi_record_id, transition_type,
    availability_time_utc, triggering_candle_record_id, event_time_utc).
    Its record_id / content_fingerprint are BTMM-internal identities (resolved
    through BTMM's own resolver, under DerivedOutputType.POI_LIFECYCLE_
    TRANSITION reused only as an identity-space tag) — never published in any
    BtmmAnalysis output, so they need not match the id the POI engine's own
    (lazy, snapshot-only) finalization would eventually assign the same
    transition."""
    semantic_key = (
        candidate.symbol.value,
        candidate.timeframe.value,
        str(candidate.poi_record_id),
        candidate.transition_type.value,
        str(candidate.triggering_candle_record_id),
        "btmm-relay",
    )
    record_id = resolver.resolve(
        DerivedOutputType.POI_LIFECYCLE_TRANSITION, semantic_key
    )
    provenance_id = resolver.resolve(
        DerivedOutputType.POI_LIFECYCLE_TRANSITION, (*semantic_key, "provenance")
    )
    fields: dict[str, object] = {
        "symbol": candidate.symbol,
        "timeframe": candidate.timeframe,
        "poi_record_id": candidate.poi_record_id,
        "transition_type": candidate.transition_type,
        "triggering_candle_record_id": candidate.triggering_candle_record_id,
        "event_time_utc": candidate.event_time_utc,
        "availability_time_utc": candidate.availability_time_utc,
        "rule_version": configuration.rule_version,
        "contract_version": configuration.contract_version,
        "schema_version": configuration.schema_version,
        "evidence_classification": configuration.evidence_classification,
        "provenance_id": provenance_id,
    }
    return PoiLifecycleTransition(
        record_id=record_id,
        content_fingerprint=_compute_content_fingerprint(fields),
        **fields,  # type: ignore[arg-type]
    )


@dataclass
class _BtmmReplayState:
    """Private incremental BTMM state (A6-B2-C). Not part of the public
    contract surface; owned exclusively by the scanner replay path.
    analyze_btmm (and run_btmm_lifecycle) remain the unmodified batch oracle.

    Treated immutably: _advance_btmm_replay_state never mutates an existing
    instance, so a raised exception leaves the caller's state intact."""

    resolver: _IdentityResolver
    identity_provider: DerivedOutputIdentityProvider
    rule_version_text: str
    symbol: InternalSymbol | None = None
    analyzed_timeframes: tuple[Timeframe, ...] = ()
    analyzed_candle_count_by_timeframe: tuple[int, ...] = ()
    candles_so_far: tuple[NormalizedCandle, ...] = ()
    atr_state: IncrementalAtrState = field(
        default_factory=lambda: initial_incremental_atr_state(14)
    )
    atr_values_so_far: tuple[Decimal | None, ...] = ()
    # A6-B2-B: the persistent event-driven setup scheduler. Carried between
    # candles with structural sharing; only woken/new/changed/event-affected
    # setup cursors advance, the rest are reused by reference.
    scheduler: BtmmSetupEventScheduler | None = None
    # A3-B: immutable-observation reuse cache keyed by setup record_id ->
    # (fingerprint-determining fields, finalized object). A BtmmObservation is
    # immutable per setup, so the same object is reused verbatim for as long
    # as the setup exists; deleted on removal. Also the sole source of truth
    # for "which setups currently have a published observation" — no separate
    # growing tuple to keep in sync.
    observation_cache: dict[UUID, tuple[dict[str, object], BtmmObservation]] = field(
        default_factory=dict
    )
    # A3-C: immutable-lifecycle-transition reuse cache (record_id -> (fields,
    # finalized transition)). A BtmmLifecycleTransition never changes once
    # emitted, so it is reused verbatim; new entries are merged in only for
    # setups whose materialized walk was touched this candle (bounded).
    transition_cache: dict[UUID, tuple[dict[str, object], ContractModel]] = field(
        default_factory=dict
    )
    # A6-B2-C: which source POIs have already had a relevant (genuine/false
    # invalidation) transition relayed into the scheduler — both types are
    # terminal and emitted at most once per POI, so once relayed a POI's
    # further (e.g. tap-driven) scheduler wakes never re-relay it.
    relayed_relevant_poi_transitions: frozenset[UUID] = frozenset()
    # A6-B2-C: which source POIs' reviewed evidence has already been fed to
    # the scheduler — duplicate reviewed evidence per source POI is rejected
    # upstream, so this only ever grows by genuinely new arrivals.
    relayed_reviewed_evidence: frozenset[UUID] = frozenset()


def _create_initial_btmm_replay_state(
    identity_provider: DerivedOutputIdentityProvider,
    configuration: BtmmConfiguration,
) -> _BtmmReplayState:
    return _BtmmReplayState(
        resolver=_IdentityResolver(identity_provider),
        identity_provider=identity_provider,
        rule_version_text=str(configuration.rule_version),
        scheduler=create_btmm_scheduler(configuration),
    )


def _all_lifecycle_transitions_sorted(
    state: _BtmmReplayState,
) -> tuple[BtmmLifecycleTransition, ...]:
    transitions = [
        cast(BtmmLifecycleTransition, t)
        for _fields, t in state.transition_cache.values()
    ]
    return tuple(
        sorted(
            transitions,
            key=lambda t: (
                t.availability_time_utc,
                t.event_time_utc,
                t.transition_type.value,
                str(t.btmm_setup_record_id),
                str(t.record_id),
            ),
        )
    )


def _advance_btmm_replay_state(
    state: _BtmmReplayState,
    candle: NormalizedCandle,
    new_pois: Sequence[PoiObservation],
    changed_pois: Sequence[PoiObservation],
    removed_poi_ids: Sequence[UUID],
    poi_scheduler_last_walks: Mapping[UUID, PoiLifecycleWalkResult],
    reviewed_evidence: Sequence[BtmmReviewedEvidence],
    configuration: BtmmConfiguration,
    *,
    poi_observation_count: int,
) -> _BtmmReplayState:
    """Advance the incremental BTMM state by exactly one new candle plus the
    exact bounded per-candle POI delta (new/changed/removed BTMM-eligible
    source POIs), the POI scheduler's own bounded ``last_walks`` for this
    candle (source of newly-relevant source-POI transitions), and the current
    reviewed-evidence set. ``poi_observation_count`` is the O(1) current length
    of the POI engine's own ``poi_observations_so_far`` (not a scan) — it
    reproduces analyze_btmm's own empty guard exactly (``len(poi_analysis.
    poi_observations) == 0``), which fires on ANY POI observation existing
    (e.g. period levels, present from the first candle), not merely a BTMM-
    eligible one. Transactional: every value is built from locals and the
    replacement _BtmmReplayState is constructed only at the very end, so a
    raised exception (out-of-order candle) leaves the caller's state —
    including its scheduler and caches — untouched. Reproduces
    ``analyze_btmm((bundle,), poi_analysis, reviewed_evidence, ...)`` exactly,
    never calling run_btmm_lifecycle and never scanning the historical POI or
    setup universe."""
    if state.candles_so_far:
        previous_candle = state.candles_so_far[-1]
        if candle.event_time_utc <= previous_candle.event_time_utc:
            raise UnsortedCandleSequenceError(
                "candles must be canonically ordered by strictly increasing"
                " event_time_utc."
            )

    resolver = state.resolver
    identity_provider = state.identity_provider
    rule_version_text = state.rule_version_text
    assert state.scheduler is not None
    prior_scheduler = state.scheduler

    new_atr_state, atr_value = advance_incremental_atr(state.atr_state, candle)
    new_candles = (*state.candles_so_far, candle)
    new_atr_values = (*state.atr_values_so_far, atr_value)
    symbol = new_candles[0].symbol

    setup_delta = derive_btmm_setup_delta(
        new_pois,
        changed_pois,
        removed_poi_ids,
        identity_provider,
        rule_version_text,
        configuration,
    )

    # Observation cache: reuse-or-create for every BTMM-eligible new/changed
    # POI (bounded); remove entries whose source POI disappeared. A "changed"
    # POI (zone drift only, for SUPPORT_ZONE/RESISTANCE_ZONE) never actually
    # changes any BtmmObservation field (zone bounds are not part of it), so
    # its observation is always reused verbatim via the fields-equality check.
    new_obs_cache = dict(state.observation_cache)
    removed_setup_ids: list[UUID] = []
    for poi_id in setup_delta.removed_source_poi_ids:
        removed_setup_id = prior_scheduler.poi_to_setup.get(poi_id.int)
        if removed_setup_id is not None:
            removed_setup_ids.append(removed_setup_id)
            new_obs_cache.pop(removed_setup_id, None)

    eligible_touched_pois = [
        poi
        for poi in (*new_pois, *changed_pois)
        if is_btmm_eligible(poi, configuration)
    ]
    for poi in eligible_touched_pois:
        semantic_key = (
            symbol.value,
            poi.source_timeframe.value,
            str(poi.record_id),
            rule_version_text,
        )
        record_id = resolver.resolve(DerivedOutputType.BTMM_OBSERVATION, semantic_key)
        provenance_id = resolver.resolve(
            DerivedOutputType.BTMM_OBSERVATION, (*semantic_key, "provenance")
        )
        observation_fields: dict[str, object] = {
            "symbol": poi.symbol,
            "source_timeframe": poi.source_timeframe,
            "btmm_direction": _DIRECTION_MAP[poi.direction],
            "source_poi_record_id": poi.record_id,
            "source_poi_type": poi.poi_type,
            "source_poi_direction": poi.direction,
            "candidate_event_time_utc": poi.confirmation_time_utc,
            "availability_time_utc": poi.availability_time_utc,
            "rule_version": configuration.rule_version,
            "contract_version": configuration.contract_version,
            "schema_version": configuration.schema_version,
            "evidence_classification": configuration.evidence_classification,
            "provenance_id": provenance_id,
        }
        cached = new_obs_cache.get(record_id)
        if cached is not None and cached[0] == observation_fields:
            observation = cached[1]
        else:
            observation = BtmmObservation(
                record_id=record_id,
                content_fingerprint=_compute_content_fingerprint(observation_fields),
                **observation_fields,  # type: ignore[arg-type]
            )
        new_obs_cache[record_id] = (observation_fields, observation)

    # New POI-transition events: relay only the two relevant, terminal types,
    # and only once per source POI (bounded by poi_scheduler_last_walks, which
    # itself only names POIs actually advanced by the POI scheduler this
    # candle).
    new_relayed_transitions = set(state.relayed_relevant_poi_transitions)
    new_poi_transitions: list[PoiLifecycleTransition] = []
    for poi_record_id, poi_walk in poi_scheduler_last_walks.items():
        if poi_record_id in new_relayed_transitions:
            continue
        for poi_candidate in poi_walk.transitions:
            if poi_candidate.transition_type in _RELEVANT_POI_TRANSITION_TYPES:
                new_poi_transitions.append(
                    _relay_poi_transition(poi_candidate, resolver, configuration)
                )
                new_relayed_transitions.add(poi_record_id)
                break

    # New reviewed-evidence events: only genuinely new source-POI arrivals.
    new_relayed_evidence = set(state.relayed_reviewed_evidence)
    new_reviewed_evidence: list[BtmmReviewedEvidence] = []
    for evidence in reviewed_evidence:
        if evidence.source_poi_record_id not in new_relayed_evidence:
            new_reviewed_evidence.append(evidence)
            new_relayed_evidence.add(evidence.source_poi_record_id)

    new_scheduler = advance_btmm_scheduler(
        prior_scheduler,
        new_candles,
        new_atr_values,
        setup_delta=setup_delta,
        new_poi_transitions=tuple(new_poi_transitions),
        new_reviewed_evidence=tuple(new_reviewed_evidence),
    )

    # Transitions: finalize only the bounded set of setups the scheduler
    # actually advanced/reconciled this candle (new_scheduler.last_walks);
    # every other setup's previously-finalized transitions are carried
    # forward untouched via the merged cache (immutable once emitted).
    touched_candidates: list[TransitionCandidate] = []
    for walk in new_scheduler.last_walks.values():
        touched_candidates.extend(walk.transitions)

    def transition_semantic_key(candidate: TransitionCandidate) -> tuple[str, ...]:
        trigger_reference = (
            str(candidate.triggering_candle_record_id)
            if candidate.triggering_candle_record_id is not None
            else (
                "reviewed:"
                + candidate.triggering_reviewed_evidence_availability_time_utc.isoformat()
                if candidate.triggering_reviewed_evidence_availability_time_utc
                is not None
                else "none"
            )
        )
        return (
            candidate.symbol.value,
            candidate.timeframe.value,
            str(candidate.btmm_setup_record_id),
            candidate.transition_type.value,
            trigger_reference,
            rule_version_text,
        )

    touched_reuse: dict[UUID, tuple[dict[str, object], ContractModel]] = {}
    _finalize(
        touched_candidates,
        DerivedOutputType.BTMM_LIFECYCLE_TRANSITION,
        BtmmLifecycleTransition,
        transition_semantic_key,
        lambda _c: {},
        frozenset(),
        configuration,
        resolver,
        prior_reuse=state.transition_cache,
        new_reuse=touched_reuse,
    )
    new_transition_cache: dict[UUID, tuple[dict[str, object], ContractModel]] = {
        **state.transition_cache,
        **touched_reuse,
    }
    if removed_setup_ids:
        removed_setup_id_set = set(removed_setup_ids)
        new_transition_cache = {
            record_id: entry
            for record_id, entry in new_transition_cache.items()
            if getattr(entry[1], "btmm_setup_record_id", None)
            not in removed_setup_id_set
        }

    has_any_poi_observation = poi_observation_count > 0

    return _BtmmReplayState(
        resolver=resolver,
        identity_provider=identity_provider,
        rule_version_text=rule_version_text,
        symbol=symbol if has_any_poi_observation else None,
        analyzed_timeframes=(candle.timeframe,) if has_any_poi_observation else (),
        analyzed_candle_count_by_timeframe=(
            (len(new_candles),) if has_any_poi_observation else ()
        ),
        candles_so_far=new_candles,
        atr_state=new_atr_state,
        atr_values_so_far=new_atr_values,
        scheduler=new_scheduler,
        observation_cache=new_obs_cache,
        transition_cache=new_transition_cache,
        relayed_relevant_poi_transitions=frozenset(new_relayed_transitions),
        relayed_reviewed_evidence=frozenset(new_relayed_evidence),
    )


def _materialize_current_btmm_states(
    state: _BtmmReplayState,
) -> tuple[CurrentBtmmState, ...]:
    """A6-B2-C: build CurrentBtmmState lazily, on demand, from the persistent
    scheduler + observation cache — O(S) (S = live setup count) paid only when
    actually called (never inside the per-candle advance), matching
    analyze_btmm's own objects exactly (same identities, fingerprints,
    canonical ordering)."""
    assert state.scheduler is not None
    scheduler = state.scheduler
    resolver = state.resolver
    rule_version_text = state.rule_version_text
    configuration = scheduler.configuration

    # analyze_btmm computes latest_transition_by_setup by "last write wins" over
    # lifecycle_transitions in its PRE-sort (natural walk-emission) order -- the
    # public canonical sort (by availability_time_utc, event_time_utc,
    # transition_type.value, ...) happens strictly AFTER that reduction, so two
    # same-timestamp transitions (e.g. ENTERED_FORMING and ACCURACY_GATE_
    # CONFIRMED emitted on the same candle) must be reduced in emission order,
    # not alphabetical-by-type sorted order. state.transition_cache preserves
    # insertion order (a transition's dict position is fixed the first time it
    # is created, and _finalize's own per-candle candidate order mirrors each
    # setup's walk.transitions emission order exactly), so iterating its values
    # directly reproduces batch's pre-sort order.
    latest_transition_by_setup: dict[UUID, UUID] = {}
    for _fields, raw_transition in state.transition_cache.values():
        transition = cast(BtmmLifecycleTransition, raw_transition)
        latest_transition_by_setup[transition.btmm_setup_record_id] = (
            transition.record_id
        )

    current_states: list[CurrentBtmmState] = []
    for setup_id, (_fields, observation) in state.observation_cache.items():
        walk = scheduler.materialize_walk(setup_id)
        assert walk is not None
        state_fields = walk.final_fields

        semantic_key = (
            observation.symbol.value,
            observation.source_timeframe.value,
            str(observation.source_poi_record_id),
            rule_version_text,
        )
        record_id = resolver.resolve(DerivedOutputType.CURRENT_BTMM_STATE, semantic_key)
        provenance_id = resolver.resolve(
            DerivedOutputType.CURRENT_BTMM_STATE, (*semantic_key, "provenance")
        )
        fields: dict[str, object] = {
            "symbol": observation.symbol,
            "timeframe": observation.source_timeframe,
            "btmm_setup_record_id": setup_id,
            "btmm_direction": observation.btmm_direction,
            "source_poi_type": observation.source_poi_type,
            "primary_state": state_fields.primary_state,
            "formation_stage": state_fields.formation_stage,
            "market_direction_status": state_fields.market_direction_status,
            "analytical_framework_status": state_fields.analytical_framework_status,
            "session_status": state_fields.session_status,
            "accuracy_gate_status": state_fields.accuracy_gate_status,
            "interaction_class": state_fields.interaction_class,
            "reaction_gate_status": state_fields.reaction_gate_status,
            "reaction_classification": state_fields.reaction_classification,
            "reaction_speed_gate_status": state_fields.reaction_speed_gate_status,
            "reaction_speed_classification": state_fields.reaction_speed_classification,
            "formation_timeframe_gate_status": state_fields.formation_timeframe_gate_status,
            "volume_pillar_status": state_fields.volume_pillar_status,
            "liquidity_evidence_status": state_fields.liquidity_evidence_status,
            "liquidity_location": state_fields.liquidity_location,
            "liquidity_evidence_source": state_fields.liquidity_evidence_source,
            "reviewed_evidence_availability_time_utc": (
                state_fields.reviewed_evidence_availability_time_utc
            ),
            "cancellation_reason": state_fields.cancellation_reason,
            "blocked_reason": state_fields.blocked_reason,
            "latest_lifecycle_transition_id": latest_transition_by_setup.get(setup_id),
            "availability_time_utc": state_fields.availability_time_utc,
            "rule_version": configuration.rule_version,
            "contract_version": configuration.contract_version,
            "schema_version": configuration.schema_version,
            "evidence_classification": configuration.evidence_classification,
            "provenance_id": provenance_id,
        }
        current_states.append(
            CurrentBtmmState(
                record_id=record_id,
                content_fingerprint=_compute_content_fingerprint(fields),
                **fields,  # type: ignore[arg-type]
            )
        )

    return tuple(
        sorted(
            current_states,
            key=lambda s: (
                s.symbol.value,
                s.timeframe.value,
                str(s.btmm_setup_record_id),
            ),
        )
    )


def _btmm_replay_state_to_analysis(
    state: _BtmmReplayState, *, with_current_states: bool = True
) -> BtmmAnalysis:
    """Build the public BtmmAnalysis from the incremental state, matching
    analyze_btmm's shape exactly — including the empty-input case (no candles
    or no eligible POI observations => fully empty, analyzed_timeframes ==
    ()). ``with_current_states=False`` returns the identical analysis except
    with an empty ``current_btmm_states`` tuple, for callers (the per-group
    event-ledger reconciliation) that provably never read it; the objects are
    materialized once at the snapshot boundary."""
    observations = tuple(
        sorted(
            (obs for _fields, obs in state.observation_cache.values()),
            key=lambda o: (
                o.availability_time_utc,
                o.source_timeframe.value,
                o.btmm_direction.value,
                str(o.source_poi_record_id),
                str(o.record_id),
            ),
        )
    )
    lifecycle_transitions = _all_lifecycle_transitions_sorted(state)
    current_btmm_states = (
        _materialize_current_btmm_states(state) if with_current_states else ()
    )
    return BtmmAnalysis(
        symbol=state.symbol,
        analyzed_timeframes=state.analyzed_timeframes,
        analyzed_candle_count_by_timeframe=state.analyzed_candle_count_by_timeframe,
        btmm_observations=observations,
        btmm_lifecycle_transitions=lifecycle_transitions,
        current_btmm_states=current_btmm_states,
    )


def _combine_btmm_replay_states(
    btmm_states: dict[Timeframe, _BtmmReplayState],
    ordered_btmm_timeframes: tuple[Timeframe, ...],
    candle_counts: dict[Timeframe, int],
    symbol: InternalSymbol | None,
    combined_poi_observation_count: int,
    *,
    with_current_states: bool = True,
) -> BtmmAnalysis:
    """Combine the per-BTMM-timeframe incremental states (subsystem 2e) into
    the multi-timeframe BtmmAnalysis, reproducing analyze_btmm's shape
    exactly. Setups partition by their source POI's timeframe, so
    concatenating the per-timeframe states and re-sorting on analyze_btmm's
    own keys yields the identical combined result. The unchanged batch
    analyze_btmm remains the differential oracle; it is never used as the
    normal finalization path.

    Empty guard mirrors analyze_btmm exactly: no BTMM-eligible timeframe
    input, or no POI observations at all, => a fully empty analysis with
    analyzed_timeframes == ()."""
    if len(ordered_btmm_timeframes) == 0 or combined_poi_observation_count == 0:
        return BtmmAnalysis(
            symbol=None,
            analyzed_timeframes=(),
            analyzed_candle_count_by_timeframe=(),
            btmm_observations=(),
            btmm_lifecycle_transitions=(),
            current_btmm_states=(),
        )

    observations = tuple(
        observation
        for tf in ordered_btmm_timeframes
        for _fields, observation in btmm_states[tf].observation_cache.values()
    )
    lifecycle_transitions = tuple(
        transition
        for tf in ordered_btmm_timeframes
        for transition in _all_lifecycle_transitions_sorted(btmm_states[tf])
    )
    # A3-B: CurrentBtmmState objects are materialized (and fingerprinted) only
    # when this combine will publish them (finalization). The per-group ledger
    # path passes with_current_states=False and never reads them.
    current_states = (
        tuple(
            state
            for tf in ordered_btmm_timeframes
            for state in _materialize_current_btmm_states(btmm_states[tf])
        )
        if with_current_states
        else ()
    )

    observations_sorted = tuple(
        sorted(
            observations,
            key=lambda o: (
                o.availability_time_utc,
                o.source_timeframe.value,
                o.btmm_direction.value,
                str(o.source_poi_record_id),
                str(o.record_id),
            ),
        )
    )
    lifecycle_transitions_sorted = tuple(
        sorted(
            lifecycle_transitions,
            key=lambda t: (
                t.availability_time_utc,
                t.event_time_utc,
                t.transition_type.value,
                str(t.btmm_setup_record_id),
                str(t.record_id),
            ),
        )
    )
    current_states_sorted = tuple(
        sorted(
            current_states,
            key=lambda s: (
                s.symbol.value,
                s.timeframe.value,
                str(s.btmm_setup_record_id),
            ),
        )
    )

    return BtmmAnalysis(
        symbol=symbol,
        analyzed_timeframes=ordered_btmm_timeframes,
        analyzed_candle_count_by_timeframe=tuple(
            candle_counts[tf] for tf in ordered_btmm_timeframes
        ),
        btmm_observations=observations_sorted,
        btmm_lifecycle_transitions=lifecycle_transitions_sorted,
        current_btmm_states=current_states_sorted,
    )
