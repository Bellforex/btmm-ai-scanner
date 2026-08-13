import hashlib
import json
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from enum import Enum
from itertools import pairwise
from typing import Any, NamedTuple
from uuid import UUID

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
from btmm_ai_scanner.poi.bases import detect_bases
from btmm_ai_scanner.poi.configuration import PoiConfiguration, validate_configuration
from btmm_ai_scanner.poi.current_state import CurrentPoiState
from btmm_ai_scanner.poi.detector_frontier import (
    _DetectorFrontierState,
    advance_detector_frontier,
    create_initial_detector_frontier_state,
)
from btmm_ai_scanner.poi.engulfing import detect_engulfing
from btmm_ai_scanner.poi.enums import (
    LIFECYCLE_ELIGIBLE_POI_TYPES,
    PoiDirection,
    PoiFamily,
    PoiFreshnessStatus,
    PoiLifecycleStatus,
    PoiStrengthTier,
    PoiType,
)
from btmm_ai_scanner.poi.fair_value_gaps import detect_fair_value_gaps
from btmm_ai_scanner.poi.lifecycle import (
    LifecycleWalkResult,
    PoiLifecycleTransition,
    TransitionCandidate,
    _classify_tap_count,
    _is_breach,
    _touches_zone,
    _zone_reference_atr,
    run_poi_lifecycle,
)
from btmm_ai_scanner.poi.lifecycle_scheduler import (
    PoiEventScheduler,
    PoiSpec,
    advance_scheduler,
    create_scheduler,
)
from btmm_ai_scanner.poi.observation import PoiObservation
from btmm_ai_scanner.poi.order_blocks import detect_order_blocks
from btmm_ai_scanner.poi.overlap import (
    PoiOverlapRelationship,
    compute_overlap_relationships,
    resolve_merges,
)
from btmm_ai_scanner.poi.period_levels import detect_period_levels
from btmm_ai_scanner.poi.pressure_wicks import detect_pressure_wicks
from btmm_ai_scanner.poi.reference_zones import detect_reference_zones
from btmm_ai_scanner.poi.reversal_candles import detect_reversal_candles
from btmm_ai_scanner.poi.scheduler_walk import cursor_walk_result
from btmm_ai_scanner.poi.single_candle_reversals import detect_single_candle_reversals
from btmm_ai_scanner.poi.three_candle_stars import detect_three_candle_stars

_TIMEFRAME_STRENGTH_RANK: dict[Timeframe, int] = {
    Timeframe.M1: 1,
    Timeframe.M5: 2,
    Timeframe.M15: 3,
    Timeframe.H1: 4,
    Timeframe.H3: 5,
    Timeframe.H4: 6,
    Timeframe.D1: 7,
    Timeframe.W1: 8,
}

_FAMILY_BY_POI_TYPE: dict[PoiType, PoiFamily] = {
    PoiType.BUY_ORDER_BLOCK: PoiFamily.VOLUME,
    PoiType.SELL_ORDER_BLOCK: PoiFamily.VOLUME,
    PoiType.BUY_FAIR_VALUE_GAP: PoiFamily.VOLUME,
    PoiType.SELL_FAIR_VALUE_GAP: PoiFamily.VOLUME,
    PoiType.BUY_TO_SELL_CANDLE: PoiFamily.VOLUME,
    PoiType.SELL_TO_BUY_CANDLE: PoiFamily.VOLUME,
    PoiType.BASE_RALLY: PoiFamily.VOLUME,
    PoiType.BASE_DROP: PoiFamily.VOLUME,
    PoiType.BULLISH_PRESSURE_WICK: PoiFamily.VOLUME,
    PoiType.BEARISH_PRESSURE_WICK: PoiFamily.VOLUME,
    PoiType.BULLISH_ENGULFING: PoiFamily.PRICE_ACTION,
    PoiType.BEARISH_ENGULFING: PoiFamily.PRICE_ACTION,
    PoiType.HAMMER: PoiFamily.PRICE_ACTION,
    PoiType.SHOOTING_STAR: PoiFamily.PRICE_ACTION,
    PoiType.MORNING_STAR: PoiFamily.PRICE_ACTION,
    PoiType.EVENING_STAR: PoiFamily.PRICE_ACTION,
    PoiType.SUPPORT_ZONE: PoiFamily.STRUCTURAL,
    PoiType.RESISTANCE_ZONE: PoiFamily.STRUCTURAL,
    PoiType.EQUAL_HIGHS_LIQUIDITY: PoiFamily.STRUCTURAL,
    PoiType.EQUAL_LOWS_LIQUIDITY: PoiFamily.STRUCTURAL,
    PoiType.PREVIOUS_DAY_HIGH: PoiFamily.STRUCTURAL,
    PoiType.PREVIOUS_DAY_LOW: PoiFamily.STRUCTURAL,
    PoiType.PREVIOUS_WEEK_HIGH: PoiFamily.STRUCTURAL,
    PoiType.PREVIOUS_WEEK_LOW: PoiFamily.STRUCTURAL,
    PoiType.PREVIOUS_MONTH_HIGH: PoiFamily.STRUCTURAL,
    PoiType.PREVIOUS_MONTH_LOW: PoiFamily.STRUCTURAL,
    PoiType.CURRENT_DAY_HIGH: PoiFamily.STRUCTURAL,
    PoiType.CURRENT_DAY_LOW: PoiFamily.STRUCTURAL,
    PoiType.CURRENT_WEEK_HIGH: PoiFamily.STRUCTURAL,
    PoiType.CURRENT_WEEK_LOW: PoiFamily.STRUCTURAL,
    PoiType.CURRENT_MONTH_HIGH: PoiFamily.STRUCTURAL,
    PoiType.CURRENT_MONTH_LOW: PoiFamily.STRUCTURAL,
}


class DuplicatePoiTimeframeInputError(ValueError):
    pass


class UnsortedPoiTimeframeInputError(ValueError):
    pass


class InputPrefixMismatchError(ValueError):
    pass


class MissingSourceRecordError(ValueError):
    pass


class ImpossiblePoiLifecycleTransitionError(ValueError):
    pass


class PoiTimeframeInput(NamedTuple):
    timeframe: Timeframe
    candles: tuple[NormalizedCandle, ...]
    measurement_analysis: MarketMeasurementAnalysis


class PoiAnalysis(ContractModel):
    symbol: InternalSymbol | None
    analyzed_timeframes: tuple[Timeframe, ...]
    analyzed_candle_count_by_timeframe: tuple[int, ...]
    poi_observations: tuple[PoiObservation, ...]
    poi_lifecycle_transitions: tuple[PoiLifecycleTransition, ...]
    poi_overlap_relationships: tuple[PoiOverlapRelationship, ...]
    current_poi_states: tuple[CurrentPoiState, ...]


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
    configuration: PoiConfiguration,
    resolver: _IdentityResolver,
    *,
    prior_reuse: dict[UUID, tuple[dict[str, object], ContractModel]] | None = None,
    new_reuse: dict[UUID, tuple[dict[str, object], ContractModel]] | None = None,
) -> tuple[ContractT, ...]:
    """A3-C: when ``prior_reuse``/``new_reuse`` are supplied (the incremental
    replay path), a finalized record whose fingerprint-determining fields are
    byte-identical to the cached ones is reused verbatim — no SHA-256, no
    strict-pydantic construction — and the surviving object is recorded in
    ``new_reuse`` for the next advance. Lifecycle transitions are immutable once
    emitted, so this is a permanent reuse; the batch oracle passes neither cache
    and is byte-for-byte unchanged. ``new_reuse`` is a caller-owned local dict
    published only on a successful advance (transactional)."""
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


def _refingerprint(observation: PoiObservation) -> PoiObservation:
    fields = observation.model_dump(exclude={"record_id", "content_fingerprint"})
    content_fingerprint = _compute_content_fingerprint(fields)
    return observation.model_copy(update={"content_fingerprint": content_fingerprint})


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
    timeframe_inputs: tuple[PoiTimeframeInput, ...],
) -> None:
    seen_timeframes: set[Timeframe] = set()
    all_symbols: set[InternalSymbol] = set()

    for bundle in timeframe_inputs:
        if bundle.timeframe in seen_timeframes:
            raise DuplicatePoiTimeframeInputError(
                f"timeframe {bundle.timeframe} appears in more than one bundle."
            )
        seen_timeframes.add(bundle.timeframe)

        _validate_bundle_candles(bundle.timeframe, bundle.candles)

        if len(bundle.candles) > 0:
            for candle in bundle.candles:
                all_symbols.add(candle.symbol)

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

            for zone in analysis.support_resistance_zones:
                if zone.symbol != bundle_symbol or zone.timeframe != bundle.timeframe:
                    raise MissingSourceRecordError(
                        f"support_resistance_zone {zone.record_id} does not belong"
                        " to this bundle's declared symbol/timeframe."
                    )
            for cluster in analysis.equal_level_clusters:
                if (
                    cluster.symbol != bundle_symbol
                    or cluster.timeframe != bundle.timeframe
                ):
                    raise MissingSourceRecordError(
                        f"equal_level_cluster {cluster.record_id} does not belong"
                        " to this bundle's declared symbol/timeframe."
                    )

    if len(all_symbols) > 1:
        raise MixedSymbolAnalysisError(
            "analyze_pois requires exactly one InternalSymbol across every"
            " supplied bundle."
        )

    ranks = [_TIMEFRAME_STRENGTH_RANK[bundle.timeframe] for bundle in timeframe_inputs]
    if ranks != sorted(ranks):
        raise UnsortedPoiTimeframeInputError(
            "timeframe_inputs must be supplied in ascending timeframe-strength order."
        )


def _detect_bundle_candidates(
    bundle: PoiTimeframeInput, configuration: PoiConfiguration
) -> list[Any]:
    candidates: list[Any] = []
    candidates.extend(detect_order_blocks(bundle.candles, configuration))
    candidates.extend(detect_fair_value_gaps(bundle.candles, configuration))
    candidates.extend(detect_reversal_candles(bundle.candles, configuration))
    candidates.extend(detect_bases(bundle.candles, configuration))
    candidates.extend(detect_pressure_wicks(bundle.candles, configuration))
    candidates.extend(detect_engulfing(bundle.candles, configuration))
    candidates.extend(detect_single_candle_reversals(bundle.candles, configuration))
    candidates.extend(detect_three_candle_stars(bundle.candles, configuration))
    candidates.extend(
        detect_reference_zones(
            bundle.measurement_analysis.support_resistance_zones,
            bundle.measurement_analysis.equal_level_clusters,
        )
    )
    candidates.extend(detect_period_levels(bundle.candles, configuration))
    return [c for c in candidates if c.poi_type in configuration.enabled_poi_types]


def _semantic_key_for_candidate(
    candidate: Any, rule_version_text: str
) -> tuple[str, ...]:
    if hasattr(candidate, "period_start_time_utc"):
        return (
            candidate.symbol.value,
            candidate.timeframe.value,
            candidate.poi_type.value,
            candidate.period_start_time_utc.isoformat(),
            candidate.period_end_time_utc.isoformat(),
            rule_version_text,
        )
    if hasattr(candidate, "source_zone_record_id"):
        return (
            candidate.symbol.value,
            candidate.timeframe.value,
            candidate.poi_type.value,
            str(candidate.source_zone_record_id),
            rule_version_text,
        )
    return (
        candidate.symbol.value,
        candidate.timeframe.value,
        candidate.poi_type.value,
        *(str(cid) for cid in candidate.source_candle_record_ids),
        rule_version_text,
    )


def _normalize_candidate_fields(candidate: Any) -> dict[str, object]:
    poi_type = candidate.poi_type
    family = _FAMILY_BY_POI_TYPE[poi_type]

    if hasattr(candidate, "period_start_time_utc"):
        zone_top = candidate.representative_price
        zone_bottom = candidate.representative_price
        representative_price = candidate.representative_price
        source_candle_record_ids = candidate.source_candle_record_ids
        source_measurement_record_ids: tuple[UUID, ...] = ()
        strength_tier = None
    elif hasattr(candidate, "source_zone_record_id"):
        zone_top = candidate.zone_top
        zone_bottom = candidate.zone_bottom
        representative_price = None
        source_candle_record_ids = ()
        source_measurement_record_ids = (candidate.source_zone_record_id,)
        strength_tier = None
    else:
        zone_top = candidate.zone_top
        zone_bottom = candidate.zone_bottom
        representative_price = None
        source_candle_record_ids = candidate.source_candle_record_ids
        source_measurement_record_ids = ()
        strength_tier = getattr(candidate, "strength_tier", None)
        if not isinstance(strength_tier, PoiStrengthTier):
            strength_tier = None

    return {
        "symbol": candidate.symbol,
        "source_timeframe": candidate.timeframe,
        "effective_timeframe": candidate.timeframe,
        "family": family,
        "poi_type": poi_type,
        "direction": candidate.direction,
        "zone_top": zone_top,
        "zone_bottom": zone_bottom,
        "representative_price": representative_price,
        "strength_tier": strength_tier,
        "source_candle_record_ids": source_candle_record_ids,
        "source_measurement_record_ids": source_measurement_record_ids,
        "merged_source_poi_record_ids": (),
        "candidate_event_time_utc": candidate.candidate_event_time_utc,
        "confirmation_time_utc": candidate.confirmation_time_utc,
        "availability_time_utc": candidate.availability_time_utc,
    }


def analyze_pois(
    timeframe_inputs: tuple[PoiTimeframeInput, ...],
    configuration: PoiConfiguration,
    identity_provider: DerivedOutputIdentityProvider,
) -> PoiAnalysis:
    validate_configuration(configuration)

    if len(timeframe_inputs) == 0:
        return PoiAnalysis(
            symbol=None,
            analyzed_timeframes=(),
            analyzed_candle_count_by_timeframe=(),
            poi_observations=(),
            poi_lifecycle_transitions=(),
            poi_overlap_relationships=(),
            current_poi_states=(),
        )

    _validate_timeframe_inputs(timeframe_inputs)

    resolver = _IdentityResolver(identity_provider)
    rule_version_text = str(configuration.rule_version)

    symbol: InternalSymbol | None = None
    for bundle in timeframe_inputs:
        if len(bundle.candles) > 0:
            symbol = bundle.candles[0].symbol
            break

    all_candidates: list[Any] = []
    for bundle in timeframe_inputs:
        all_candidates.extend(_detect_bundle_candidates(bundle, configuration))

    observations_list: list[PoiObservation] = []
    for candidate in all_candidates:
        semantic_key = _semantic_key_for_candidate(candidate, rule_version_text)
        record_id = resolver.resolve(DerivedOutputType.POI_OBSERVATION, semantic_key)
        provenance_id = resolver.resolve(
            DerivedOutputType.POI_OBSERVATION, (*semantic_key, "provenance")
        )
        fields = _normalize_candidate_fields(candidate)
        fields.update(
            rule_version=configuration.rule_version,
            contract_version=configuration.contract_version,
            schema_version=configuration.schema_version,
            evidence_classification=configuration.evidence_classification,
            provenance_id=provenance_id,
        )
        content_fingerprint = _compute_content_fingerprint(fields)
        observations_list.append(
            PoiObservation(
                record_id=record_id,
                content_fingerprint=content_fingerprint,
                **fields,  # type: ignore[arg-type]
            )
        )
    observations = tuple(observations_list)

    # Cross-timeframe merge and overlap resolution.
    merged_children, effective_timeframe_overrides = resolve_merges(observations)
    updated_observations: list[PoiObservation] = []
    for observation in observations:
        update: dict[str, object] = {}
        if observation.record_id in merged_children:
            update["merged_source_poi_record_ids"] = merged_children[
                observation.record_id
            ]
        if observation.record_id in effective_timeframe_overrides:
            update["effective_timeframe"] = effective_timeframe_overrides[
                observation.record_id
            ]
        if update:
            observation = _refingerprint(observation.model_copy(update=update))
        updated_observations.append(observation)
    observations = tuple(updated_observations)

    candles_by_timeframe: dict[Timeframe, tuple[NormalizedCandle, ...]] = {}
    atr_by_timeframe: dict[Timeframe, tuple[Decimal | None, ...]] = {}
    last_candle_time_by_timeframe: dict[Timeframe, datetime] = {}
    for bundle in timeframe_inputs:
        candles_by_timeframe[bundle.timeframe] = bundle.candles
        atr_by_timeframe[bundle.timeframe] = compute_atr_series(bundle.candles, 14)
        if len(bundle.candles) > 0:
            last_candle_time_by_timeframe[bundle.timeframe] = bundle.candles[
                -1
            ].availability_time_utc

    evaluated_at = max(
        last_candle_time_by_timeframe.values(),
        default=datetime(1970, 1, 1, tzinfo=UTC),
    )
    overlap_relationships = compute_overlap_relationships(observations, evaluated_at)

    all_transitions: list[TransitionCandidate] = []
    current_state_fields_by_poi: dict[UUID, dict[str, object]] = {}

    for observation in observations:
        bundle_candles = candles_by_timeframe.get(observation.source_timeframe, ())
        bundle_atr = atr_by_timeframe.get(observation.source_timeframe, ())

        if (
            observation.poi_type in LIFECYCLE_ELIGIBLE_POI_TYPES
            and len(bundle_candles) > 0
        ):
            walk = run_poi_lifecycle(
                bundle_candles,
                bundle_atr,
                observation.symbol,
                observation.source_timeframe,
                observation.record_id,
                observation.direction,
                observation.zone_top,
                observation.zone_bottom,
                observation.availability_time_utc,
                configuration,
            )
            all_transitions.extend(walk.transitions)
            if walk.last_seen_candle is not None:
                elapsed = (
                    walk.last_seen_candle.availability_time_utc
                    - observation.availability_time_utc
                )
            else:
                elapsed = (
                    observation.availability_time_utc
                    - observation.availability_time_utc
                )
            current_state_fields_by_poi[observation.record_id] = {
                "symbol": observation.symbol,
                "timeframe": observation.source_timeframe,
                "poi_record_id": observation.record_id,
                "poi_type": observation.poi_type,
                "direction": observation.direction,
                "poi_lifecycle_status": walk.final_status,
                "freshness_status": walk.freshness_status,
                "tap_count": walk.tap_count,
                "tap_classification": walk.tap_classification,
                "age_start_time_utc": observation.availability_time_utc,
                "age_in_confirmed_bars": walk.age_in_confirmed_bars,
                "elapsed_time_since_availability": elapsed,
                "availability_time_utc": observation.availability_time_utc,
            }
        else:
            last_candle_time = last_candle_time_by_timeframe.get(
                observation.source_timeframe
            )
            if last_candle_time is not None:
                elapsed = last_candle_time - observation.availability_time_utc
            else:
                elapsed = (
                    observation.availability_time_utc
                    - observation.availability_time_utc
                )
            current_state_fields_by_poi[observation.record_id] = {
                "symbol": observation.symbol,
                "timeframe": observation.source_timeframe,
                "poi_record_id": observation.record_id,
                "poi_type": observation.poi_type,
                "direction": observation.direction,
                "poi_lifecycle_status": PoiLifecycleStatus.NOT_APPLICABLE,
                "freshness_status": PoiFreshnessStatus.FRESH,
                "tap_count": 0,
                "tap_classification": None,
                "age_start_time_utc": observation.availability_time_utc,
                "age_in_confirmed_bars": 0,
                "elapsed_time_since_availability": elapsed,
                "availability_time_utc": observation.availability_time_utc,
            }

    def transition_semantic_key(candidate: TransitionCandidate) -> tuple[str, ...]:
        return (
            candidate.symbol.value,
            candidate.timeframe.value,
            str(candidate.poi_record_id),
            candidate.transition_type.value,
            str(candidate.triggering_candle_record_id),
            rule_version_text,
        )

    lifecycle_transitions = _finalize(
        list(all_transitions),
        DerivedOutputType.POI_LIFECYCLE_TRANSITION,
        PoiLifecycleTransition,
        transition_semantic_key,
        lambda _c: {},
        frozenset(),
        configuration,
        resolver,
    )

    latest_transition_by_poi: dict[UUID, UUID] = {}
    for transition in lifecycle_transitions:
        latest_transition_by_poi[transition.poi_record_id] = transition.record_id

    current_states: list[CurrentPoiState] = []
    for poi_record_id, state_fields in current_state_fields_by_poi.items():
        symbol_value = state_fields["symbol"]
        timeframe_value = state_fields["timeframe"]
        poi_type_value = state_fields["poi_type"]
        assert isinstance(symbol_value, InternalSymbol)
        assert isinstance(timeframe_value, Timeframe)
        assert isinstance(poi_type_value, PoiType)
        semantic_key = (
            symbol_value.value,
            timeframe_value.value,
            poi_type_value.value,
            str(poi_record_id),
            rule_version_text,
        )
        record_id = resolver.resolve(DerivedOutputType.CURRENT_POI_STATE, semantic_key)
        provenance_id = resolver.resolve(
            DerivedOutputType.CURRENT_POI_STATE, (*semantic_key, "provenance")
        )
        fields = dict(state_fields)
        fields["latest_lifecycle_transition_id"] = latest_transition_by_poi.get(
            poi_record_id
        )
        fields.update(
            rule_version=configuration.rule_version,
            contract_version=configuration.contract_version,
            schema_version=configuration.schema_version,
            evidence_classification=configuration.evidence_classification,
            provenance_id=provenance_id,
        )
        content_fingerprint = _compute_content_fingerprint(fields)
        current_states.append(
            CurrentPoiState(
                record_id=record_id,
                content_fingerprint=content_fingerprint,
                **fields,  # type: ignore[arg-type]
            )
        )

    observations = tuple(
        sorted(
            observations,
            key=lambda o: (
                o.availability_time_utc,
                o.source_timeframe.value,
                o.family.value,
                o.poi_type.value,
                o.direction.value,
                o.zone_bottom,
                o.zone_top,
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
                str(t.poi_record_id),
                str(t.record_id),
            ),
        )
    )
    overlap_relationships = tuple(
        sorted(
            overlap_relationships,
            key=lambda r: (
                r.evaluated_at_time_utc,
                str(r.poi_a_record_id),
                str(r.poi_b_record_id),
            ),
        )
    )
    current_states = sorted(
        current_states,
        key=lambda s: (
            s.symbol.value,
            s.timeframe.value,
            s.poi_type.value,
            str(s.poi_record_id),
        ),
    )

    return PoiAnalysis(
        symbol=symbol,
        analyzed_timeframes=tuple(bundle.timeframe for bundle in timeframe_inputs),
        analyzed_candle_count_by_timeframe=tuple(
            len(bundle.candles) for bundle in timeframe_inputs
        ),
        poi_observations=observations,
        poi_lifecycle_transitions=lifecycle_transitions,
        poi_overlap_relationships=overlap_relationships,
        current_poi_states=tuple(current_states),
    )


# =====================================================================
# Subsystem 2d: private incremental POI replay state (single timeframe).
#
# The public analyze_pois above is preserved byte-for-byte and remains the sole
# semantic oracle. This section adds a private, per-timeframe incremental engine
# that reproduces analyze_pois((single_bundle,), ...) EXACTLY at every candle
# prefix while making the dominant cost — the per-POI lifecycle walk — genuinely
# incremental instead of re-walking each POI's whole post-availability candle
# stream from scratch on every candle.
#
# Cross-timeframe merge is a no-op within one timeframe (resolve_merges only
# merges a child into a STRONGER-timeframe parent, and a single bundle has one
# timeframe), so it is deferred to the 2f orchestration kernel, exactly as the
# register's per-timeframe _PoiReplayState (§44S) and poi_states_by_timeframe
# (§44U) design intends. Detection, merge, overlap, observation/transition
# finalization, current-state building, and sorting all reuse the unchanged
# batch helpers, so they are exact by construction; only the lifecycle walk is
# made incremental. The lifecycle walk reuses the unchanged run_poi_lifecycle on
# the candle suffix anchored at each POI's first breach — breach detection is
# independent of the carried status, so a fresh walk over candles[first_breach:]
# reproduces every subsequent episode identically — combined with incremental
# tap counting and terminal-result caching. Pinned by permanent per-prefix
# differential tests against the batch oracle.
# =====================================================================


def _lifecycle_tolerance(
    candles: tuple[NormalizedCandle, ...],
    atr_values: tuple[Decimal | None, ...],
    index: int,
    zone_height: Decimal,
    min_tick: Decimal,
    atr_multiplier: Decimal,
    height_multiplier: Decimal,
) -> Decimal:
    """A faithful copy of run_poi_lifecycle's internal ``tolerance`` closure,
    used only to detect a POI's first breach identically to the batch oracle."""
    fallback = candles[index].high - candles[index].low
    reference_atr = _zone_reference_atr(atr_values, index, fallback)
    bound_a = atr_multiplier * reference_atr
    bound_b = height_multiplier * zone_height if zone_height > 0 else bound_a
    return max(Decimal("2") * min_tick, min(bound_a, bound_b))


class _PoiLifecycleWalkState(NamedTuple):
    """Per-POI incremental lifecycle state. Immutable; a new instance is built
    each advance so a failed transition never mutates the caller's state.

    Pre-breach candles are scanned once for the first breach (``scan_index``
    cursor); from the first breach onward the unchanged run_poi_lifecycle is
    re-run over ``candles[first_breach_index:]`` (bounded, exact) until the POI
    reaches a terminal genuine-invalidation, whose walk output is then cached.
    Taps/freshness/age are accumulated incrementally over ``candles[start_index:]``."""

    start_index: int | None
    start_search_index: int
    tap_index: int | None
    scan_index: int | None
    first_breach_index: int | None
    tap_count: int
    in_tap: bool
    terminal: bool
    cached_transitions: tuple[TransitionCandidate, ...]
    cached_status: PoiLifecycleStatus
    cached_last_seen_candle: NormalizedCandle | None


def _create_poi_lifecycle_walk_state() -> _PoiLifecycleWalkState:
    return _PoiLifecycleWalkState(
        start_index=None,
        start_search_index=0,
        tap_index=None,
        scan_index=None,
        first_breach_index=None,
        tap_count=0,
        in_tap=False,
        terminal=False,
        cached_transitions=(),
        cached_status=PoiLifecycleStatus.NO_BREACH,
        cached_last_seen_candle=None,
    )


def _advance_poi_lifecycle(
    prev: _PoiLifecycleWalkState,
    candles: tuple[NormalizedCandle, ...],
    atr_values: tuple[Decimal | None, ...],
    symbol: InternalSymbol,
    timeframe: Timeframe,
    poi_record_id: UUID,
    direction: PoiDirection,
    zone_top: Decimal,
    zone_bottom: Decimal,
    availability_time_utc: datetime,
    configuration: PoiConfiguration,
) -> tuple[_PoiLifecycleWalkState, LifecycleWalkResult]:
    n = len(candles)
    zone_height = zone_top - zone_bottom
    min_tick = configuration.minimum_price_tick

    # 1. Resolve the fixed start_index (first candle available strictly after the
    #    POI's own availability), scanning only candles not yet examined.
    start_index = prev.start_index
    start_search_index = prev.start_search_index
    tap_index = prev.tap_index
    scan_index = prev.scan_index
    if start_index is None:
        idx = start_search_index
        while idx < n:
            if candles[idx].availability_time_utc > availability_time_utc:
                start_index = idx
                break
            idx += 1
        if start_index is None:
            # No candle is visible after the POI's availability yet: exactly the
            # run_poi_lifecycle start_index == len(candles) case.
            return (
                prev._replace(start_search_index=n),
                LifecycleWalkResult(
                    transitions=(),
                    final_status=PoiLifecycleStatus.NO_BREACH,
                    freshness_status=PoiFreshnessStatus.FRESH,
                    tap_count=0,
                    tap_classification=None,
                    age_in_confirmed_bars=0,
                    last_seen_candle=None,
                ),
            )
        start_search_index = start_index
        tap_index = start_index
        scan_index = start_index

    assert tap_index is not None
    assert scan_index is not None

    # 2. Incremental tap/freshness accumulation over candles[start_index:].
    tap_count = prev.tap_count
    in_tap = prev.in_tap
    for idx in range(tap_index, n):
        touching = _touches_zone(candles[idx], zone_top, zone_bottom)
        if touching and not in_tap:
            tap_count += 1
            in_tap = True
        elif not touching:
            in_tap = False
    tap_index = n

    freshness_status = (
        PoiFreshnessStatus.INTERACTED if tap_count > 0 else PoiFreshnessStatus.FRESH
    )
    tap_classification = _classify_tap_count(tap_count)
    age_in_confirmed_bars = max(0, n - start_index)

    # 3. Breach walk (transitions / final_status / last_seen).
    terminal = prev.terminal
    first_breach_index = prev.first_breach_index
    cached_transitions = prev.cached_transitions
    cached_status = prev.cached_status
    cached_last_seen_candle = prev.cached_last_seen_candle

    if terminal:
        transitions = cached_transitions
        final_status = cached_status
        last_seen_candle = cached_last_seen_candle
    else:
        if first_breach_index is None:
            idx = scan_index
            while idx < n:
                overshoot = _lifecycle_tolerance(
                    candles,
                    atr_values,
                    idx,
                    zone_height,
                    min_tick,
                    configuration.zone_overshoot_tolerance_atr_multiplier,
                    configuration.zone_overshoot_tolerance_zone_height_multiplier,
                )
                if _is_breach(
                    candles[idx], direction, zone_top, zone_bottom, overshoot
                ):
                    first_breach_index = idx
                    break
                idx += 1
            scan_index = n if first_breach_index is None else first_breach_index

        if first_breach_index is None:
            transitions = ()
            final_status = PoiLifecycleStatus.NO_BREACH
            last_seen_candle = candles[n - 1] if start_index < n else None
        else:
            anchor = first_breach_index
            walk = run_poi_lifecycle(
                candles[anchor:],
                atr_values[anchor:],
                symbol,
                timeframe,
                poi_record_id,
                direction,
                zone_top,
                zone_bottom,
                availability_time_utc,
                configuration,
            )
            transitions = walk.transitions
            final_status = walk.final_status
            last_seen_candle = walk.last_seen_candle
            if final_status == PoiLifecycleStatus.GENUINE_INVALIDATION_CONFIRMED:
                terminal = True
                cached_transitions = transitions
                cached_status = final_status
                cached_last_seen_candle = last_seen_candle

    new_state = _PoiLifecycleWalkState(
        start_index=start_index,
        start_search_index=start_search_index,
        tap_index=tap_index,
        scan_index=scan_index,
        first_breach_index=first_breach_index,
        tap_count=tap_count,
        in_tap=in_tap,
        terminal=terminal,
        cached_transitions=cached_transitions,
        cached_status=cached_status,
        cached_last_seen_candle=cached_last_seen_candle,
    )
    result = LifecycleWalkResult(
        transitions=transitions,
        final_status=final_status,
        freshness_status=freshness_status,
        tap_count=tap_count,
        tap_classification=tap_classification,
        age_in_confirmed_bars=age_in_confirmed_bars,
        last_seen_candle=last_seen_candle,
    )
    return new_state, result


@dataclass
class _PoiReplayState:
    """Private, per-timeframe incremental POI state for subsystem 2d. Not part
    of the public contract surface; owned exclusively by the scanner replay
    path. analyze_pois (and run_poi_lifecycle) remain the unmodified batch
    oracle.

    §44S names three fields: timeframe, live_pois (full PoiObservation records
    for currently non-terminal-lifecycle POIs — required because CurrentPoiState
    carries only ids, not zone_top/zone_bottom), and current_states_by_poi. The
    remaining fields are proven-necessary private additions mirroring the 2b/2c
    precedent (the not-yet-built §44U event ledger will later subsume the
    accumulated public outputs): candles_so_far rebuilds the single-timeframe
    bundle each advance; lifecycle_states carries each POI's incremental walk;
    the *_so_far tuples hold the finalized public outputs (classification A).

    Treated immutably: _advance_poi_replay_state never mutates an existing
    instance, so a raised exception leaves the caller's state intact."""

    resolver: _IdentityResolver
    rule_version_text: str
    timeframe: Timeframe | None = None
    symbol: InternalSymbol | None = None
    candles_so_far: tuple[NormalizedCandle, ...] = ()
    # A6-B1-B: the persistent event-driven lifecycle scheduler replaces the
    # per-candle cursor dict. Carried between candles with structural sharing;
    # only woken/new/changed cursors advance, the rest are reused by reference.
    scheduler: PoiEventScheduler | None = None
    poi_observations_so_far: tuple[PoiObservation, ...] = ()
    # A6-B1-B7: lifecycle transitions and CurrentPoiState are no longer stored per
    # candle — they are (re)built on demand at the snapshot boundary by
    # _build_lifecycle_outputs from the scheduler + observations. The per-candle
    # advance does zero lifecycle-output assembly.
    # A3-A: immutable-observation reuse cache keyed by record_id ->
    # (fingerprint-determining fields, finalized object). Within one timeframe a
    # PoiObservation is immutable, so on every later candle the detected fields
    # for an already-seen record_id are byte-identical and the cached object
    # (and its fingerprint) is reused verbatim; only genuinely changed fields
    # trigger a rebuild. Published only on a successful advance, so a raised
    # advance leaves the prior cache intact (transactional).
    observation_cache: dict[UUID, tuple[dict[str, object], PoiObservation]] = field(
        default_factory=dict
    )
    # A6-A: private incremental detection frontier. Replaces the per-candle
    # _detect_bundle_candidates(full_prefix) + compute_atr_series(full_prefix, 14)
    # with exact append-only/running frontiers. Immutable; published only on a
    # successful advance (transactional).
    detector_frontier: _DetectorFrontierState = field(
        default_factory=create_initial_detector_frontier_state
    )
    # A6-B2-C: the exact bounded per-candle BTMM-eligible-subset delta, exposed
    # for the BTMM incremental engine to consume directly instead of re-deriving
    # it from a full poi_observations scan. Zero new computation: these are the
    # SAME PoiObservation objects already built above (read back via new_cache,
    # itself already built) for the SAME bounded new_specs/changed_specs the
    # scheduler itself consumes, plus the same removed_ids. Never read by
    # analyze_pois or any POI-only path; POI's own output/behavior is unchanged.
    new_pois_for_btmm: tuple[PoiObservation, ...] = ()
    changed_pois_for_btmm: tuple[PoiObservation, ...] = ()
    removed_poi_ids_for_btmm: tuple[UUID, ...] = ()
    # A6-F3-A: the append-only slice of ``observation_cache`` (local + base +
    # reversal families). These candidates are strictly append-only (never
    # changed, never removed), so once resolved/normalized/finalized their
    # observation is immutable and reused by reference for the rest of the
    # replay. Carrying this slice lets the per-candle advance resolve + normalize
    # + fingerprint only the *new* append-only suffix and the bounded reference/
    # period sets, instead of re-resolving the entire cumulative candidate
    # universe every candle (the O(history)-per-candle -> O(N^2) advance cost).
    append_only_cache: dict[UUID, tuple[dict[str, object], PoiObservation]] = field(
        default_factory=dict
    )


def _create_initial_poi_replay_state(
    identity_provider: DerivedOutputIdentityProvider,
    configuration: PoiConfiguration,
) -> _PoiReplayState:
    return _PoiReplayState(
        resolver=_IdentityResolver(identity_provider),
        rule_version_text=str(configuration.rule_version),
        scheduler=create_scheduler(configuration),
    )


def _observation_sort_key(
    o: PoiObservation,
) -> tuple[datetime, str, str, str, str, Decimal, Decimal, str]:
    return (
        o.availability_time_utc,
        o.source_timeframe.value,
        o.family.value,
        o.poi_type.value,
        o.direction.value,
        o.zone_bottom,
        o.zone_top,
        str(o.record_id),
    )


def _advance_poi_replay_state(
    state: _PoiReplayState,
    candle: NormalizedCandle,
    measurement_analysis: MarketMeasurementAnalysis,
    configuration: PoiConfiguration,
) -> _PoiReplayState:
    """Advance the incremental POI state by exactly one new candle plus the
    current single-timeframe measurement analysis (from the 2b measurement
    replay). Transactional: every value is built from locals and the replacement
    _PoiReplayState is constructed only at the very end, so a raised exception
    (out-of-order candle) leaves the caller's state — including its per-POI
    lifecycle_states — untouched. Reproduces analyze_pois((bundle,), ...) exactly
    while advancing each POI's lifecycle incrementally rather than re-walking it
    from scratch."""
    if state.candles_so_far:
        previous_candle = state.candles_so_far[-1]
        if candle.event_time_utc <= previous_candle.event_time_utc:
            raise UnsortedCandleSequenceError(
                "candles must be canonically ordered by strictly increasing"
                " event_time_utc."
            )

    new_candles = (*state.candles_so_far, candle)
    rule_version_text = state.rule_version_text
    resolver = state.resolver

    # A6-A: advance the incremental detection frontier by exactly this candle
    # instead of rerunning _detect_bundle_candidates over the whole prefix. The
    # returned candidate universe is the identical set (after the shared
    # enabled_poi_types filter), and atr_series is the exact full-prefix Wilder
    # ATR-14 the lifecycle walk requires (never recomputed from a suffix).
    new_detector_frontier, _all_candidates, atr_values = advance_detector_frontier(
        state.detector_frontier, candle, measurement_analysis, configuration
    )
    prior_cache = state.observation_cache
    enabled = configuration.enabled_poi_types
    unchanged_ids: set[UUID] = set()
    touched: list[PoiObservation] = []

    def _resolve_observation(
        candidate: Any,
    ) -> tuple[UUID, dict[str, object], PoiObservation, bool]:
        semantic_key = _semantic_key_for_candidate(candidate, rule_version_text)
        record_id = resolver.resolve(DerivedOutputType.POI_OBSERVATION, semantic_key)
        provenance_id = resolver.resolve(
            DerivedOutputType.POI_OBSERVATION, (*semantic_key, "provenance")
        )
        fields = _normalize_candidate_fields(candidate)
        fields.update(
            rule_version=configuration.rule_version,
            contract_version=configuration.contract_version,
            schema_version=configuration.schema_version,
            evidence_classification=configuration.evidence_classification,
            provenance_id=provenance_id,
        )
        # A3-A: reuse the immutable finalized object (and its fingerprint) when
        # the fingerprint-determining fields are byte-identical to the cached
        # ones; only a genuine field change pays the SHA-256 + construction.
        cached = prior_cache.get(record_id)
        if cached is not None and cached[0] == fields:
            return record_id, fields, cached[1], True
        return (
            record_id,
            fields,
            PoiObservation(
                record_id=record_id,
                content_fingerprint=_compute_content_fingerprint(fields),
                **fields,  # type: ignore[arg-type]
            ),
            False,
        )

    # A6-F3-A: the append-only families (local / base / reversal) are strictly
    # append-only in the detector frontier -- new candidates are appended to the
    # tail, never mutated or removed. So the prior append-only observation slice
    # is immutable and carried by reference; only this candle's newly appended
    # suffix is resolved/normalized/fingerprinted (O(new), not O(history)). This
    # replaces the per-candle re-resolution of the entire cumulative candidate
    # universe -- the dominant O(N^2) advance-hot-path cost.
    prior_append_only = state.detector_frontier.append_only_candidates
    all_append_only = new_detector_frontier.append_only_candidates
    new_append_only_cache = dict(state.append_only_cache)
    unchanged_ids.update(state.append_only_cache)
    for candidate in all_append_only[len(prior_append_only) :]:
        if candidate.poi_type not in enabled:
            continue
        record_id, fields, observation, _reused = _resolve_observation(candidate)
        new_append_only_cache[record_id] = (fields, observation)
        touched.append(observation)

    # Reference (measurement SR/EL projection) and period families are BOUNDED
    # mutable sets: rebuild them each candle from the current bounded candidates
    # (O(bounded)), reusing unchanged immutable objects via A3-A. Prior entries
    # are intentionally not carried -- a removed reference/period candidate then
    # simply does not reappear, exactly matching the full-universe rebuild it
    # replaces.
    bounded_entries: dict[UUID, tuple[dict[str, object], PoiObservation]] = {}
    for candidate in (
        *new_detector_frontier.reference_candidates,
        *new_detector_frontier.period_candidates,
    ):
        if candidate.poi_type not in enabled:
            continue
        record_id, fields, observation, reused = _resolve_observation(candidate)
        bounded_entries[record_id] = (fields, observation)
        if reused:
            unchanged_ids.add(record_id)
        else:
            touched.append(observation)

    new_cache = {**new_append_only_cache, **bounded_entries}

    # A3-A/A3-D: resolve_merges only ever pairs a child POI with a STRONGER-
    # timeframe parent, and _advance_poi_replay_state always processes exactly one
    # timeframe's bundle, so the merge is a proven no-op here (identical to the
    # single-active-timeframe skip in _combine_poi_replay_states). Skipping it
    # removes an O(obs^2) scan from the per-candle hot path with no output change;
    # cross-timeframe merges are still applied in _combine_poi_replay_states.

    # Lifecycle: A6-B1 event-driven scheduler. Advance the persistent scheduler by
    # exactly this candle plus the exact frontier NEW/CHANGED/REMOVED deltas — no
    # O(P) diff of the full observation set. Only woken/new/changed cursors advance
    # (their exact walk is captured in ``last_walks``); a dormant POI's cursor is
    # carried by reference and its walk reconstructed from its materialized state.
    assert state.scheduler is not None
    delta = new_detector_frontier.last_delta
    symbol_value_text = new_candles[0].symbol.value
    timeframe_value_text = candle.timeframe.value

    def _delta_specs(candidates: tuple[Any, ...]) -> list[PoiSpec]:
        # Built directly from the bounded delta candidates (each carries its
        # zone/direction/availability); no O(P) scan of the observation set. The
        # observation record_id is the resolver's content-addressed id for the
        # candidate's semantic key — identical to the id assigned in the
        # observation build above.
        specs: list[PoiSpec] = []
        for candidate in candidates:
            if candidate.poi_type in LIFECYCLE_ELIGIBLE_POI_TYPES:
                rid = resolver.resolve(
                    DerivedOutputType.POI_OBSERVATION,
                    _semantic_key_for_candidate(candidate, rule_version_text),
                )
                specs.append(
                    PoiSpec(
                        record_id=rid,
                        symbol=candidate.symbol,
                        timeframe=candidate.timeframe,
                        direction=candidate.direction,
                        zone_top=candidate.zone_top,
                        zone_bottom=candidate.zone_bottom,
                        availability_time_utc=candidate.availability_time_utc,
                    )
                )
        return specs

    new_specs = _delta_specs(delta.new_candidates)
    changed_specs = _delta_specs(delta.changed_candidates)
    removed_ids: list[UUID] = []
    for identity in delta.removed_identities:
        # Only reference SR zones (identity tag "R") are lifecycle-eligible mutable
        # POIs that can be removed; append-only families are never removed and
        # period/EL families are NOT_APPLICABLE.
        if identity[0] in LIFECYCLE_ELIGIBLE_POI_TYPES and identity[1] == "R":
            removed_key = (
                symbol_value_text,
                timeframe_value_text,
                identity[0].value,
                str(identity[2]),
                rule_version_text,
            )
            removed_ids.append(
                resolver.resolve(DerivedOutputType.POI_OBSERVATION, removed_key)
            )

    new_scheduler = advance_scheduler(
        state.scheduler,
        new_candles,
        atr_values,
        new_pois=new_specs,
        changed_pois=changed_specs,
        removed_ids=removed_ids,
    )

    # A6-B2-C: bounded BTMM-facing delta -- O(delta), reads back the same
    # PoiObservation objects new_cache already holds for these same record_ids.
    new_pois_for_btmm = tuple(new_cache[spec.record_id][1] for spec in new_specs)
    changed_pois_for_btmm = tuple(
        new_cache[spec.record_id][1] for spec in changed_specs
    )

    # A6-B1-B7: the per-candle advance no longer assembles lifecycle transitions
    # or CurrentPoiState — that O(P) work is deferred to
    # ``_build_lifecycle_outputs`` at the snapshot/finalization boundary (lazy).
    # The advance stores only the incremental scheduler + the sorted observations;
    # under FINAL_ONLY retention the lifecycle outputs are materialized once.
    #
    # A6-C: avoid a full O(P log P) re-sort of the entire observation history
    # every candle. `all_candidates` is already the complete O(P) frontier
    # rebuild (accepted baseline, unchanged here); what used to also cost
    # O(P log P) comparisons on top of that is now reduced to O(P) in the
    # common case. If literally nothing changed (every observation reused its
    # cached object, and no observation was added/removed), the prior sorted
    # tuple is reused verbatim. Otherwise the prior sorted tuple is filtered
    # down to the still-unchanged entries (preserving their relative order --
    # a sorted sequence stays sorted after removing elements) and only the
    # small new/changed subset is merged back in; a single `sorted()` call
    # over [retained-ascending-run] + [small-touched-run] lets Timsort merge
    # the two runs in near-linear time instead of re-sorting from scratch.
    # This never assumes where touched items belong in the final order (that
    # would be fragile); `sorted()` always produces the exact correct order
    # regardless, only the constant-factor comparison cost improves.
    if len(unchanged_ids) == len(new_cache) == len(state.poi_observations_so_far):
        observations_sorted = state.poi_observations_so_far
    else:
        retained = tuple(
            o for o in state.poi_observations_so_far if o.record_id in unchanged_ids
        )
        observations_sorted = tuple(
            sorted(retained + tuple(touched), key=_observation_sort_key)
        )
    return _PoiReplayState(
        resolver=resolver,
        rule_version_text=rule_version_text,
        timeframe=candle.timeframe,
        symbol=new_candles[0].symbol,
        candles_so_far=new_candles,
        scheduler=new_scheduler,
        poi_observations_so_far=observations_sorted,
        observation_cache=new_cache,
        detector_frontier=new_detector_frontier,
        new_pois_for_btmm=new_pois_for_btmm,
        changed_pois_for_btmm=changed_pois_for_btmm,
        removed_poi_ids_for_btmm=tuple(removed_ids),
        append_only_cache=new_append_only_cache,
    )


def _build_lifecycle_outputs(
    state: _PoiReplayState,
) -> tuple[
    tuple[PoiLifecycleTransition, ...],
    tuple[tuple[UUID, dict[str, object]], ...],
]:
    """A6-B1-B7: build the sorted lifecycle transitions and the CurrentPoiState
    materials from the stored scheduler + observations, on demand at the snapshot
    boundary (never in the per-candle advance). Byte-identical to what the batch
    ``analyze_pois`` produces. Each present lifecycle POI's exact walk comes from
    the scheduler's captured ``last_walks`` (woken/new/changed this candle) or is
    reconstructed from its dormant cursor's materialized state."""
    assert state.scheduler is not None
    scheduler = state.scheduler
    configuration = scheduler.configuration
    resolver = state.resolver
    rule_version_text = state.rule_version_text
    candle = state.candles_so_far[-1]
    last_candle_time = candle.availability_time_utc

    all_transitions: list[TransitionCandidate] = []
    current_state_fields_by_poi: dict[UUID, dict[str, object]] = {}

    for observation in state.poi_observations_so_far:
        if observation.poi_type in LIFECYCLE_ELIGIBLE_POI_TYPES:
            walk = scheduler.last_walks.get(observation.record_id)
            if walk is None:
                cursor = scheduler.materialize_cursor(observation.record_id)
                assert cursor is not None
                walk = cursor_walk_result(cursor, candle, configuration)
            all_transitions.extend(walk.transitions)
            if walk.last_seen_candle is not None:
                elapsed = (
                    walk.last_seen_candle.availability_time_utc
                    - observation.availability_time_utc
                )
            else:
                elapsed = (
                    observation.availability_time_utc
                    - observation.availability_time_utc
                )
            current_state_fields_by_poi[observation.record_id] = {
                "symbol": observation.symbol,
                "timeframe": observation.source_timeframe,
                "poi_record_id": observation.record_id,
                "poi_type": observation.poi_type,
                "direction": observation.direction,
                "poi_lifecycle_status": walk.final_status,
                "freshness_status": walk.freshness_status,
                "tap_count": walk.tap_count,
                "tap_classification": walk.tap_classification,
                "age_start_time_utc": observation.availability_time_utc,
                "age_in_confirmed_bars": walk.age_in_confirmed_bars,
                "elapsed_time_since_availability": elapsed,
                "availability_time_utc": observation.availability_time_utc,
            }
        else:
            elapsed = last_candle_time - observation.availability_time_utc
            current_state_fields_by_poi[observation.record_id] = {
                "symbol": observation.symbol,
                "timeframe": observation.source_timeframe,
                "poi_record_id": observation.record_id,
                "poi_type": observation.poi_type,
                "direction": observation.direction,
                "poi_lifecycle_status": PoiLifecycleStatus.NOT_APPLICABLE,
                "freshness_status": PoiFreshnessStatus.FRESH,
                "tap_count": 0,
                "tap_classification": None,
                "age_start_time_utc": observation.availability_time_utc,
                "age_in_confirmed_bars": 0,
                "elapsed_time_since_availability": elapsed,
                "availability_time_utc": observation.availability_time_utc,
            }

    def transition_semantic_key(candidate: TransitionCandidate) -> tuple[str, ...]:
        return (
            candidate.symbol.value,
            candidate.timeframe.value,
            str(candidate.poi_record_id),
            candidate.transition_type.value,
            str(candidate.triggering_candle_record_id),
            rule_version_text,
        )

    lifecycle_transitions = _finalize(
        list(all_transitions),
        DerivedOutputType.POI_LIFECYCLE_TRANSITION,
        PoiLifecycleTransition,
        transition_semantic_key,
        lambda _c: {},
        frozenset(),
        configuration,
        resolver,
    )
    lifecycle_transitions_sorted = tuple(
        sorted(
            lifecycle_transitions,
            key=lambda t: (
                t.availability_time_utc,
                t.event_time_utc,
                t.transition_type.value,
                str(t.poi_record_id),
                str(t.record_id),
            ),
        )
    )

    latest_transition_by_poi: dict[UUID, UUID] = {}
    for transition in lifecycle_transitions_sorted:
        latest_transition_by_poi[transition.poi_record_id] = transition.record_id

    current_state_materials_list: list[tuple[UUID, dict[str, object]]] = []
    for poi_record_id, state_fields in current_state_fields_by_poi.items():
        symbol_value = state_fields["symbol"]
        timeframe_value = state_fields["timeframe"]
        poi_type_value = state_fields["poi_type"]
        assert isinstance(symbol_value, InternalSymbol)
        assert isinstance(timeframe_value, Timeframe)
        assert isinstance(poi_type_value, PoiType)
        semantic_key = (
            symbol_value.value,
            timeframe_value.value,
            poi_type_value.value,
            str(poi_record_id),
            rule_version_text,
        )
        record_id = resolver.resolve(DerivedOutputType.CURRENT_POI_STATE, semantic_key)
        provenance_id = resolver.resolve(
            DerivedOutputType.CURRENT_POI_STATE, (*semantic_key, "provenance")
        )
        fields = dict(state_fields)
        fields["latest_lifecycle_transition_id"] = latest_transition_by_poi.get(
            poi_record_id
        )
        fields.update(
            rule_version=configuration.rule_version,
            contract_version=configuration.contract_version,
            schema_version=configuration.schema_version,
            evidence_classification=configuration.evidence_classification,
            provenance_id=provenance_id,
        )
        current_state_materials_list.append((record_id, fields))

    return lifecycle_transitions_sorted, tuple(current_state_materials_list)


def _materialize_current_poi_states(
    materials: tuple[tuple[UUID, dict[str, object]], ...],
) -> tuple[CurrentPoiState, ...]:
    """A3-A: construct the CurrentPoiState public objects from the deferred
    (record_id, fields) materials, computing each fingerprint exactly once here
    (at the snapshot boundary) instead of once per POI per candle. Byte-identical
    to the objects analyze_pois builds — same identities, same fingerprints, same
    canonical ordering."""
    return tuple(
        sorted(
            (
                CurrentPoiState(
                    record_id=record_id,
                    content_fingerprint=_compute_content_fingerprint(fields),
                    **fields,  # type: ignore[arg-type]
                )
                for record_id, fields in materials
            ),
            key=lambda s: (
                s.symbol.value,
                s.timeframe.value,
                s.poi_type.value,
                str(s.poi_record_id),
            ),
        )
    )


def _poi_replay_state_to_analysis(
    state: _PoiReplayState,
    *,
    with_overlap: bool = True,
    with_current_states: bool = True,
    with_lifecycle_transitions: bool = True,
) -> PoiAnalysis:
    """Build the public PoiAnalysis from the incremental single-timeframe state,
    matching analyze_pois's shape exactly — including the empty-input case.

    Overlap relationships are (re)computed here rather than in the per-candle
    advance: their ``evaluated_at_time_utc`` moves every candle, so a stored
    per-candle value could never be reused, and the pairwise scan is O(obs^2).
    Deferring it to materialization keeps the per-candle advance out of the
    super-quadratic regime; under the historical-backtest FINAL_ONLY retention
    the analysis is materialized once, so this O(obs^2) cost is paid once. The
    result is identical to analyze_pois (compute_overlap_relationships re-sorts
    each group internally, so the sorted-observation input is immaterial).

    ``with_overlap=False`` returns the identical analysis except with an empty
    ``poi_overlap_relationships`` tuple. It exists purely for internal callers
    that provably never read the single-timeframe overlap —
    ``_combine_poi_replay_states`` (which recomputes cross-timeframe overlap from
    the merged observations and never consults the per-timeframe overlap) and the
    per-candle BTMM feed (BTMM reads only ``poi_observations`` and
    ``poi_lifecycle_transitions``). Skipping the discarded O(obs^2) scan there
    removes it from the per-group and per-candle hot paths without changing any
    published output.

    ``with_lifecycle_transitions=False`` additionally skips
    ``_build_lifecycle_outputs`` -- the O(obs) walk that re-derives (and, via
    ``_finalize``, re-validates and re-fingerprints) every historical POI
    lifecycle transition -- and returns an empty ``poi_lifecycle_transitions``
    tuple. It exists for the per-group FINAL_ONLY orchestration combine, whose
    only consumer of the transitions (the private event ledger) reconciles them
    once at finalize from the single materialized final analysis, never per
    group. Combined with ``with_current_states=False`` this removes the entire
    lifecycle-output materialization from the per-group advance hot path, so the
    O(obs) walk is no longer paid once per availability group (the O(N^2)
    cumulative pathology). The full canonical tuple is still materialized -- once
    -- at snapshot/finalization, where ``with_lifecycle_transitions`` defaults to
    True, so every published output is byte-identical to before."""
    if not state.candles_so_far:
        return PoiAnalysis(
            symbol=None,
            analyzed_timeframes=(),
            analyzed_candle_count_by_timeframe=(),
            poi_observations=(),
            poi_lifecycle_transitions=(),
            poi_overlap_relationships=(),
            current_poi_states=(),
        )
    assert state.timeframe is not None
    if with_overlap:
        evaluated_at = state.candles_so_far[-1].availability_time_utc
        overlap_relationships = tuple(
            sorted(
                compute_overlap_relationships(
                    state.poi_observations_so_far, evaluated_at
                ),
                key=lambda r: (
                    r.evaluated_at_time_utc,
                    str(r.poi_a_record_id),
                    str(r.poi_b_record_id),
                ),
            )
        )
    else:
        overlap_relationships = ()
    if with_lifecycle_transitions or with_current_states:
        lifecycle_transitions_sorted, current_state_materials = (
            _build_lifecycle_outputs(state)
        )
    else:
        # Per-group FINAL_ONLY combine: neither the sorted transitions nor the
        # current-state materials are consumed, so the O(obs) historical walk is
        # skipped entirely (deferred to finalization).
        lifecycle_transitions_sorted, current_state_materials = (), ()
    current_poi_states = (
        _materialize_current_poi_states(current_state_materials)
        if with_current_states
        else ()
    )
    return PoiAnalysis(
        symbol=state.symbol,
        analyzed_timeframes=(state.timeframe,),
        analyzed_candle_count_by_timeframe=(len(state.candles_so_far),),
        poi_observations=state.poi_observations_so_far,
        poi_lifecycle_transitions=(
            lifecycle_transitions_sorted if with_lifecycle_transitions else ()
        ),
        poi_overlap_relationships=overlap_relationships,
        current_poi_states=current_poi_states,
    )


@dataclass(frozen=True)
class _PoiMergeCache:
    """A6-D: caches the expensive product of the cross-timeframe POI merge --
    resolve_merges's O(group_size^2) all-pairs scan, the per-observation
    re-fingerprint, and the final canonical sort -- keyed by an identity
    signature of the per-timeframe observation tuples that fed it. Per-timeframe
    PoiObservation tuples are immutable and only ever replaced wholesale by
    ``_advance_poi_replay_state`` (never mutated in place), so an unchanged
    ``id()`` for every active timeframe's tuple proves the merge input -- and
    therefore its output -- is byte-identical to the cached one. This is a
    correctness-transparent memoization: on a signature miss the exact same
    computation runs as before, so the result is always identical to a full
    recompute."""

    signature: tuple[tuple[Timeframe, int], ...]
    observations: tuple[PoiObservation, ...]


def _combine_poi_replay_states(
    poi_states: dict[Timeframe, _PoiReplayState],
    ordered_timeframes: tuple[Timeframe, ...],
    *,
    with_overlap: bool = True,
    with_lifecycle: bool = True,
    validated: bool = True,
    merge_cache: _PoiMergeCache | None = None,
) -> tuple[PoiAnalysis, _PoiMergeCache | None]:
    """Combine the per-timeframe incremental POI states (subsystem 2d) into the
    multi-timeframe PoiAnalysis, reproducing analyze_pois's cross-timeframe
    combination exactly: concatenate the per-timeframe observations, apply the
    unchanged cross-timeframe resolve_merges (a no-op within one timeframe, so it
    is skipped there), re-fingerprint merged observations, compute overlap, and
    sort every output on analyze_pois's own keys. Per-timeframe detection and
    lifecycle are already incremental; only the (bounded) cross-timeframe merge
    runs here. `with_overlap=False` skips the O(obs^2) overlap computation for
    callers (the per-group event-ledger reconciliation) that only need the
    observation/transition/current-state records; the overlap is materialized
    once at finalization. `with_lifecycle=False` additionally skips the per-
    timeframe ``_build_lifecycle_outputs`` walk (see
    ``_poi_replay_state_to_analysis``), returning an empty
    ``poi_lifecycle_transitions``; the per-group orchestration passes it because
    the only consumer -- the private event ledger -- reconciles the transitions
    once at finalize from the single materialized final analysis, never per
    group. The unchanged batch analyze_pois over the full prefix remains the
    differential oracle.

    Returns the analysis plus the (possibly reused, possibly freshly computed)
    merge cache for the caller to carry forward -- never mutated in place, so a
    caller that discards a failed attempt leaves its prior cache untouched."""
    active = tuple(tf for tf in ordered_timeframes if poi_states[tf].candles_so_far)
    if not active:
        return (
            PoiAnalysis(
                symbol=None,
                analyzed_timeframes=(),
                analyzed_candle_count_by_timeframe=(),
                poi_observations=(),
                poi_lifecycle_transitions=(),
                poi_overlap_relationships=(),
                current_poi_states=(),
            ),
            None,
        )

    # Per-timeframe overlap is never read here (cross-timeframe overlap is
    # recomputed below from the merged observations), so skip the discarded
    # O(obs^2) single-timeframe scan on every group and at finalization.
    # A3-A: CurrentPoiState is only materialized when this combine will publish
    # it (with_overlap=True, i.e. finalization). The per-group ledger path
    # (with_overlap=False) never reads current_poi_states, so their construction
    # is deferred out of the per-group hot path entirely.
    per_timeframe = {
        tf: _poi_replay_state_to_analysis(
            poi_states[tf],
            with_overlap=False,
            with_current_states=with_overlap,
            with_lifecycle_transitions=with_lifecycle,
        )
        for tf in ordered_timeframes
    }

    # A6-D: per_timeframe[tf].poi_observations is state.poi_observations_so_far
    # passed through unchanged (never copied), so its id() is a valid proxy for
    # "this timeframe's observation set is byte-identical to last call". If
    # every active timeframe's tuple identity matches the cached signature, the
    # ordinary bounded delta this call represents touched no observation this
    # combine cares about, and the full cross-TF merge rebuild is skipped
    # entirely -- not just the O(obs^2) resolve_merges scan, but also the
    # per-observation re-fingerprint loop and the final canonical sort.
    signature = tuple((tf, id(poi_states[tf].poi_observations_so_far)) for tf in active)
    if merge_cache is not None and merge_cache.signature == signature:
        observations = merge_cache.observations
        new_merge_cache = merge_cache
    else:
        observations_list: list[PoiObservation] = [
            observation
            for tf in ordered_timeframes
            for observation in per_timeframe[tf].poi_observations
        ]
        if len(active) > 1:
            merged_children, effective_timeframe_overrides = resolve_merges(
                tuple(observations_list)
            )
        else:
            # Merge only ever pairs a child with a STRONGER-timeframe parent, so
            # a single active timeframe can never merge: skip the O(obs^2) scan.
            merged_children, effective_timeframe_overrides = {}, {}
        updated_observations: list[PoiObservation] = []
        for observation in observations_list:
            update: dict[str, object] = {}
            if observation.record_id in merged_children:
                update["merged_source_poi_record_ids"] = merged_children[
                    observation.record_id
                ]
            if observation.record_id in effective_timeframe_overrides:
                update["effective_timeframe"] = effective_timeframe_overrides[
                    observation.record_id
                ]
            if update:
                observation = _refingerprint(observation.model_copy(update=update))
            updated_observations.append(observation)
        observations = tuple(sorted(updated_observations, key=_observation_sort_key))
        new_merge_cache = _PoiMergeCache(signature=signature, observations=observations)

    if with_overlap:
        evaluated_at = max(
            poi_states[tf].candles_so_far[-1].availability_time_utc for tf in active
        )
        # compute_overlap_relationships re-sorts each (symbol, direction) group
        # internally by record_id, so feeding it the already-merged/sorted
        # `observations` (instead of the pre-sort updated_observations list) is
        # immaterial to its result.
        overlap_relationships = compute_overlap_relationships(
            observations, evaluated_at
        )
    else:
        overlap_relationships = ()
    lifecycle_transitions = [
        transition
        for tf in ordered_timeframes
        for transition in per_timeframe[tf].poi_lifecycle_transitions
    ]
    current_states = [
        state
        for tf in ordered_timeframes
        for state in per_timeframe[tf].current_poi_states
    ]

    lifecycle_transitions_sorted = tuple(
        sorted(
            lifecycle_transitions,
            key=lambda t: (
                t.availability_time_utc,
                t.event_time_utc,
                t.transition_type.value,
                str(t.poi_record_id),
                str(t.record_id),
            ),
        )
    )
    overlap_sorted = tuple(
        sorted(
            overlap_relationships,
            key=lambda r: (
                r.evaluated_at_time_utc,
                str(r.poi_a_record_id),
                str(r.poi_b_record_id),
            ),
        )
    )
    current_states_sorted = tuple(
        sorted(
            current_states,
            key=lambda s: (
                s.symbol.value,
                s.timeframe.value,
                s.poi_type.value,
                str(s.poi_record_id),
            ),
        )
    )

    # A6-F2: the FINAL_ONLY advance hot path passes validated=False. This combined
    # analysis is a pure re-projection of already-validated per-timeframe records;
    # model_construct skips ContractModel's revalidate_instances="always"
    # re-validation of the whole cumulative POI set every availability group. The
    # public finalize() combine (with_overlap=True) keeps validated=True.
    builder = PoiAnalysis if validated else PoiAnalysis.model_construct
    return (
        builder(
            symbol=poi_states[active[0]].symbol,
            analyzed_timeframes=ordered_timeframes,
            analyzed_candle_count_by_timeframe=tuple(
                len(poi_states[tf].candles_so_far) for tf in ordered_timeframes
            ),
            poi_observations=observations,
            poi_lifecycle_transitions=lifecycle_transitions_sorted,
            poi_overlap_relationships=overlap_sorted,
            current_poi_states=current_states_sorted,
        ),
        new_merge_cache,
    )
