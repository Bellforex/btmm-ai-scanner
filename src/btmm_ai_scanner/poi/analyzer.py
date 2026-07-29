import hashlib
import json
from collections.abc import Callable
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
from btmm_ai_scanner.poi.engulfing import detect_engulfing
from btmm_ai_scanner.poi.enums import (
    LIFECYCLE_ELIGIBLE_POI_TYPES,
    PoiFamily,
    PoiFreshnessStatus,
    PoiLifecycleStatus,
    PoiStrengthTier,
    PoiType,
)
from btmm_ai_scanner.poi.fair_value_gaps import detect_fair_value_gaps
from btmm_ai_scanner.poi.lifecycle import (
    PoiLifecycleTransition,
    TransitionCandidate,
    run_poi_lifecycle,
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
