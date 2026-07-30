import hashlib
import json
from collections.abc import Callable
from datetime import UTC, timedelta
from decimal import Decimal
from enum import Enum
from itertools import pairwise
from typing import Any, NamedTuple
from uuid import UUID

from btmm_ai_scanner.btmm.configuration import BtmmConfiguration, validate_configuration
from btmm_ai_scanner.btmm.current_state import CurrentBtmmState
from btmm_ai_scanner.btmm.enums import BtmmDirection
from btmm_ai_scanner.btmm.lifecycle import (
    BtmmLifecycleTransition,
    TransitionCandidate,
    run_btmm_lifecycle,
)
from btmm_ai_scanner.btmm.observation import BtmmObservation
from btmm_ai_scanner.btmm.reviewed_evidence import BtmmReviewedEvidence
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
from btmm_ai_scanner.measurements.atr import compute_atr_series
from btmm_ai_scanner.poi.analyzer import PoiAnalysis
from btmm_ai_scanner.poi.enums import PoiDirection
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
