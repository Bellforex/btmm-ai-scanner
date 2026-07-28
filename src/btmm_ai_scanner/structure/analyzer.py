import hashlib
import json
from collections.abc import Callable
from datetime import UTC
from decimal import Decimal
from enum import Enum
from itertools import pairwise
from typing import Any
from uuid import UUID

from btmm_ai_scanner.config.enums import InternalSymbol, Timeframe
from btmm_ai_scanner.contracts.normalized_candle import NormalizedCandle
from btmm_ai_scanner.contracts.types import ContractModel, SemVer
from btmm_ai_scanner.domain import (
    AmbiguousEventTimeAnalysisError,
    DerivedIdentityCollisionError,
    DerivedOutputIdentityProvider,
    DuplicateCandleRecordError,
    MixedSymbolAnalysisError,
    MixedTimeframeAnalysisError,
    UnsortedCandleSequenceError,
)
from btmm_ai_scanner.domain.enums import DerivedOutputType
from btmm_ai_scanner.domain.swings import ConfirmedSwing
from btmm_ai_scanner.structure.configuration import StructureConfiguration
from btmm_ai_scanner.structure.current_state import CurrentStructureState
from btmm_ai_scanner.structure.relationships import (
    SwingRelationship,
    detect_swing_relationships,
)
from btmm_ai_scanner.structure.transitions import (
    StructureTransition,
    run_structure_walk,
)


class InvalidSwingReferenceError(ValueError):
    pass


class UnsortedSwingSequenceError(ValueError):
    pass


class InvalidStructureConfigurationError(ValueError):
    pass


class StructureAnalysis(ContractModel):
    symbol: InternalSymbol | None
    timeframe: Timeframe | None
    analyzed_candle_count: int
    analyzed_swing_count: int
    swing_relationships: tuple[SwingRelationship, ...]
    structure_transitions: tuple[StructureTransition, ...]
    current_state: CurrentStructureState | None


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
    configuration: StructureConfiguration,
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


def _validate_candles(candles: tuple[NormalizedCandle, ...]) -> None:
    if len(candles) == 0:
        return

    symbols = {candle.symbol for candle in candles}
    if len(symbols) > 1:
        raise MixedSymbolAnalysisError(
            "analyze_structure_state requires exactly one InternalSymbol."
        )

    timeframes = {candle.timeframe for candle in candles}
    if len(timeframes) > 1:
        raise MixedTimeframeAnalysisError(
            "analyze_structure_state requires exactly one Timeframe."
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


def _validate_swings(
    candles: tuple[NormalizedCandle, ...],
    confirmed_swings: tuple[ConfirmedSwing, ...],
) -> None:
    if len(confirmed_swings) == 0:
        return

    candle_by_id = {candle.record_id: candle for candle in candles}

    symbols = {swing.symbol for swing in confirmed_swings} | {
        candle.symbol for candle in candles
    }
    if len(symbols) > 1:
        raise MixedSymbolAnalysisError(
            "analyze_structure_state requires exactly one InternalSymbol."
        )
    timeframes = {swing.timeframe for swing in confirmed_swings} | {
        candle.timeframe for candle in candles
    }
    if len(timeframes) > 1:
        raise MixedTimeframeAnalysisError(
            "analyze_structure_state requires exactly one Timeframe."
        )

    seen_record_ids: set[UUID] = set()
    for swing in confirmed_swings:
        if swing.record_id in seen_record_ids:
            raise UnsortedSwingSequenceError(
                f"swing record_id {swing.record_id} appears more than once."
            )
        seen_record_ids.add(swing.record_id)

        for referenced_id in (
            *swing.pivot_candle_record_ids,
            swing.confirmation_candle_id,
        ):
            referenced_candle = candle_by_id.get(referenced_id)
            if referenced_candle is None:
                raise InvalidSwingReferenceError(
                    f"swing {swing.record_id} references candle {referenced_id}, "
                    "which is not present in the supplied candle tuple."
                )
            if (
                referenced_candle.availability_time_utc
                > swing.meaningful_confirmation_time_utc
            ):
                raise InvalidSwingReferenceError(
                    f"swing {swing.record_id} references candle {referenced_id}, "
                    "whose availability_time_utc is later than the swing's own"
                    " meaningful_confirmation_time_utc."
                )

    for previous, current in pairwise(confirmed_swings):
        previous_key = (
            previous.pivot_bar_index,
            previous.pivot_start_time_utc,
            previous.record_id,
        )
        current_key = (
            current.pivot_bar_index,
            current.pivot_start_time_utc,
            current.record_id,
        )
        if current_key < previous_key:
            raise UnsortedSwingSequenceError(
                "confirmed_swings must be canonically ordered by source"
                " chronology (pivot_bar_index, pivot_start_time_utc, record_id)."
            )
        if current.swing_type == previous.swing_type:
            raise UnsortedSwingSequenceError(
                "confirmed_swings must alternate between SWING_HIGH and"
                " SWING_LOW in source chronology."
            )


def _validate_instrument_metadata(
    candles: tuple[NormalizedCandle, ...],
    confirmed_swings: tuple[ConfirmedSwing, ...],
) -> None:
    for candle in candles:
        if candle.symbol is None or candle.timeframe is None:
            raise InvalidStructureConfigurationError(
                "candle carries a null symbol/timeframe; structural analysis"
                " requires fully-validated instrument metadata."
            )
    for swing in confirmed_swings:
        if swing.symbol is None or swing.timeframe is None:
            raise InvalidStructureConfigurationError(
                "swing carries a null symbol/timeframe; structural analysis"
                " requires fully-validated instrument metadata."
            )


def analyze_structure_state(
    candles: tuple[NormalizedCandle, ...],
    confirmed_swings: tuple[ConfirmedSwing, ...],
    configuration: StructureConfiguration,
    identity_provider: DerivedOutputIdentityProvider,
) -> StructureAnalysis:
    _validate_candles(candles)

    if len(candles) == 0:
        return StructureAnalysis(
            symbol=None,
            timeframe=None,
            analyzed_candle_count=0,
            analyzed_swing_count=0,
            swing_relationships=(),
            structure_transitions=(),
            current_state=None,
        )

    _validate_instrument_metadata(candles, confirmed_swings)
    _validate_swings(candles, confirmed_swings)

    resolver = _IdentityResolver(identity_provider)
    rule_version_text = str(configuration.rule_version)

    relationship_candidates = detect_swing_relationships(
        confirmed_swings, configuration
    )
    walk_result = run_structure_walk(candles, confirmed_swings, relationship_candidates)

    relationship_candidates_sorted = sorted(
        relationship_candidates,
        key=lambda c: (
            c.current_swing.pivot_bar_index,
            c.current_swing.pivot_start_time_utc,
            str(c.current_swing_record_id),
        ),
    )

    swing_relationships = _finalize(
        list(relationship_candidates_sorted),
        DerivedOutputType.SWING_RELATIONSHIP,
        SwingRelationship,
        lambda c: (
            c.symbol.value,
            c.timeframe.value,
            str(c.current_swing_record_id),
            str(c.predecessor_swing_record_id),
            rule_version_text,
        ),
        lambda c: {},
        frozenset({"current_swing", "predecessor_swing"}),
        configuration,
        resolver,
    )

    transitions_sorted = sorted(
        walk_result.transitions,
        key=lambda t: (
            t.availability_time_utc,
            t.event_time_utc,
            0 if t.transition_type.value.endswith("CHOCH") else 1,
            t.direction_after.value,
            str(t.broken_swing_id),
        ),
    )

    structure_transitions = _finalize(
        list(transitions_sorted),
        DerivedOutputType.STRUCTURE_TRANSITION,
        StructureTransition,
        lambda t: (
            t.symbol.value,
            t.timeframe.value,
            t.transition_type.value,
            str(t.broken_swing_id),
            rule_version_text,
        ),
        lambda t: {},
        frozenset(),
        configuration,
        resolver,
    )

    latest_transition_id = (
        structure_transitions[-1].record_id if structure_transitions else None
    )

    availability_time_utc = (
        walk_result.last_change_availability
        if walk_result.last_change_availability is not None
        else candles[-1].availability_time_utc
    )

    current_state_symbol = candles[0].symbol
    current_state_timeframe = candles[0].timeframe

    current_state_candidate = {
        "symbol": current_state_symbol,
        "timeframe": current_state_timeframe,
        "direction": walk_result.direction,
        "active_protected_high_swing_id": (
            walk_result.protected_high.record_id
            if walk_result.protected_high is not None
            else None
        ),
        "active_protected_low_swing_id": (
            walk_result.protected_low.record_id
            if walk_result.protected_low is not None
            else None
        ),
        "active_weak_high_swing_id": (
            walk_result.weak_high.record_id
            if walk_result.weak_high is not None
            else None
        ),
        "active_weak_low_swing_id": (
            walk_result.weak_low.record_id if walk_result.weak_low is not None else None
        ),
        "latest_transition_id": latest_transition_id,
        "availability_time_utc": availability_time_utc,
        "analyzed_swing_count": walk_result.analyzed_swing_count,
    }

    semantic_key = (
        current_state_symbol.value,
        current_state_timeframe.value,
        rule_version_text,
    )
    record_id = resolver.resolve(
        DerivedOutputType.CURRENT_STRUCTURE_STATE, semantic_key
    )
    provenance_id = resolver.resolve(
        DerivedOutputType.CURRENT_STRUCTURE_STATE, (*semantic_key, "provenance")
    )
    fields: dict[str, object] = dict(current_state_candidate)
    fields.update(
        rule_version=configuration.rule_version,
        contract_version=configuration.contract_version,
        schema_version=configuration.schema_version,
        evidence_classification=configuration.evidence_classification,
        provenance_id=provenance_id,
    )
    content_fingerprint = _compute_content_fingerprint(fields)
    current_state = CurrentStructureState(
        record_id=record_id,
        content_fingerprint=content_fingerprint,
        **fields,  # type: ignore[arg-type]
    )

    return StructureAnalysis(
        symbol=candles[0].symbol,
        timeframe=candles[0].timeframe,
        analyzed_candle_count=len(candles),
        analyzed_swing_count=len(confirmed_swings),
        swing_relationships=swing_relationships,
        structure_transitions=structure_transitions,
        current_state=current_state,
    )
