import hashlib
import json
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from enum import Enum
from itertools import pairwise
from typing import Any, NamedTuple
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
from btmm_ai_scanner.domain.enums import DerivedOutputType, SwingType
from btmm_ai_scanner.domain.swings import ConfirmedSwing
from btmm_ai_scanner.structure.configuration import StructureConfiguration
from btmm_ai_scanner.structure.current_state import CurrentStructureState
from btmm_ai_scanner.structure.enums import (
    StructureDirection,
    StructureTransitionType,
    SwingRelationshipLabel,
)
from btmm_ai_scanner.structure.relationships import (
    SwingRelationship,
    SwingRelationshipCandidate,
    detect_swing_relationships,
)
from btmm_ai_scanner.structure.transitions import (
    StructureTransition,
    StructureTransitionCandidate,
    StructureWalkResult,
    _most_recent_unbroken,
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


# =====================================================================
# Subsystem 2c: private incremental structure replay state.
#
# The public analyze_structure_state above is preserved byte-for-byte and
# remains the sole semantic oracle. This section adds a private, per-timeframe
# incremental engine that reproduces analyze_structure_state EXACTLY at every
# candle prefix while only reprocessing the affected suffix of the structure
# walk, rather than re-walking the whole history on every candle.
#
# The structure walk (structure.transitions.run_structure_walk) is a single
# left-to-right fold over candle / swing-visibility / relationship events
# sorted by (availability_time, kind, tiebreak). It is a pure function of
# (candles, confirmed_swings, relationships). Confirmed swings are NOT
# append-only (subsystem 2b-final: a pending pivot can confirm out of order, a
# plateau representative can change, same-direction supersession can rewrite an
# existing entry's content without changing the tuple length), so the event
# stream can change at a MIDDLE position. The engine therefore diffs the newly
# built event stream against the previous one, finds the longest identical
# prefix, resumes the walk from the checkpoint taken just before the earliest
# changed event, and reprocesses only from there. The cutoff is derived from
# the actual event diff (never an arbitrary bar count) and the append-only
# common case (one new candle, no swing change) resumes from the final
# checkpoint and processes a single event.
#
# _process_structure_event replicates run_structure_walk's per-event branch
# logic exactly; the two are pinned together by the permanent per-prefix
# differential tests (identity, fingerprint, and full-StructureAnalysis
# equality against the untouched batch oracle), mirroring how subsystem 2b
# validates its incremental equal-level / trendline frontiers.
# =====================================================================

_EVENT_CANDLE = 0
_EVENT_SWING_VISIBLE = 1
_EVENT_RELATIONSHIP = 2


class _StructureWalkCheckpoint(NamedTuple):
    """Immutable snapshot of the full run_structure_walk mutable state after a
    processed event, sufficient to resume the walk from exactly that point."""

    direction: StructureDirection
    protected_high: ConfirmedSwing | None
    protected_low: ConfirmedSwing | None
    weak_high: ConfirmedSwing | None
    weak_low: ConfirmedSwing | None
    broken_ids: frozenset[UUID]
    weak_high_boundary_index: int
    weak_low_boundary_index: int
    latest_label_high: SwingRelationshipLabel | None
    latest_label_low: SwingRelationshipLabel | None
    latest_swing_high: ConfirmedSwing | None
    latest_swing_low: ConfirmedSwing | None
    visible_high: tuple[ConfirmedSwing, ...]
    visible_low: tuple[ConfirmedSwing, ...]
    transitions: tuple[StructureTransitionCandidate, ...]
    last_change_availability: datetime | None


_INITIAL_STRUCTURE_CHECKPOINT = _StructureWalkCheckpoint(
    direction=StructureDirection.UNDETERMINED,
    protected_high=None,
    protected_low=None,
    weak_high=None,
    weak_low=None,
    broken_ids=frozenset(),
    weak_high_boundary_index=-1,
    weak_low_boundary_index=-1,
    latest_label_high=None,
    latest_label_low=None,
    latest_swing_high=None,
    latest_swing_low=None,
    visible_high=(),
    visible_low=(),
    transitions=(),
    last_change_availability=None,
)


def _process_structure_event(
    previous: _StructureWalkCheckpoint,
    kind: int,
    payload: object,
    candle_index_by_id: dict[UUID, int],
) -> _StructureWalkCheckpoint:
    """Advance one merged event through the structure walk. A faithful replica
    of run_structure_walk's loop body; every branch, comparison, priority rule,
    and side effect matches the batch oracle line-for-line."""
    direction = previous.direction
    protected_high = previous.protected_high
    protected_low = previous.protected_low
    weak_high = previous.weak_high
    weak_low = previous.weak_low
    broken_ids: set[UUID] = set(previous.broken_ids)
    weak_high_boundary_index = previous.weak_high_boundary_index
    weak_low_boundary_index = previous.weak_low_boundary_index
    latest_relationship_label: dict[SwingType, object] = {
        SwingType.SWING_HIGH: previous.latest_label_high,
        SwingType.SWING_LOW: previous.latest_label_low,
    }
    latest_relationship_swing: dict[SwingType, ConfirmedSwing | None] = {
        SwingType.SWING_HIGH: previous.latest_swing_high,
        SwingType.SWING_LOW: previous.latest_swing_low,
    }
    visible_swings_by_type: dict[SwingType, list[ConfirmedSwing]] = {
        SwingType.SWING_HIGH: list(previous.visible_high),
        SwingType.SWING_LOW: list(previous.visible_low),
    }
    transitions: list[StructureTransitionCandidate] = list(previous.transitions)
    last_change_availability = previous.last_change_availability

    if kind == _EVENT_CANDLE:
        candle = payload
        assert isinstance(candle, NormalizedCandle)

        choch_candidate: tuple[bool, ConfirmedSwing] | None = None
        bos_candidate: tuple[bool, ConfirmedSwing] | None = None

        if direction == StructureDirection.BEARISH and protected_high is not None:
            if candle.close > protected_high.pivot_price:
                choch_candidate = (True, protected_high)
        if direction == StructureDirection.BULLISH and protected_low is not None:
            if candle.close < protected_low.pivot_price:
                choch_candidate = (False, protected_low)
        if direction == StructureDirection.BULLISH and weak_high is not None:
            if candle.close > weak_high.pivot_price:
                bos_candidate = (True, weak_high)
        if direction == StructureDirection.BEARISH and weak_low is not None:
            if candle.close < weak_low.pivot_price:
                bos_candidate = (False, weak_low)

        if choch_candidate is not None:
            is_high_side, broken_swing = choch_candidate
            if is_high_side:
                new_protected_low = _most_recent_unbroken(
                    visible_swings_by_type[SwingType.SWING_LOW], broken_ids
                )
                if new_protected_low is not None:
                    broken_ids.add(broken_swing.record_id)
                    availability = max(
                        candle.availability_time_utc,
                        broken_swing.availability_time_utc,
                    )
                    transitions.append(
                        StructureTransitionCandidate(
                            symbol=candle.symbol,
                            timeframe=candle.timeframe,
                            transition_type=StructureTransitionType.BULLISH_CHOCH,
                            direction_before=StructureDirection.BEARISH,
                            direction_after=StructureDirection.BULLISH,
                            broken_swing_id=broken_swing.record_id,
                            broken_level_price=broken_swing.pivot_price,
                            break_close_price=candle.close,
                            protected_swing_id=new_protected_low.record_id,
                            weak_swing_id=None,
                            break_candle_id=candle.record_id,
                            event_time_utc=candle.event_time_utc,
                            availability_time_utc=availability,
                        )
                    )
                    direction = StructureDirection.BULLISH
                    protected_high = None
                    protected_low = new_protected_low
                    weak_high = None
                    weak_low = None
                    weak_high_boundary_index = candle_index_by_id[candle.record_id]
                    last_change_availability = availability
            else:
                new_protected_high = _most_recent_unbroken(
                    visible_swings_by_type[SwingType.SWING_HIGH], broken_ids
                )
                if new_protected_high is not None:
                    broken_ids.add(broken_swing.record_id)
                    availability = max(
                        candle.availability_time_utc,
                        broken_swing.availability_time_utc,
                    )
                    transitions.append(
                        StructureTransitionCandidate(
                            symbol=candle.symbol,
                            timeframe=candle.timeframe,
                            transition_type=StructureTransitionType.BEARISH_CHOCH,
                            direction_before=StructureDirection.BULLISH,
                            direction_after=StructureDirection.BEARISH,
                            broken_swing_id=broken_swing.record_id,
                            broken_level_price=broken_swing.pivot_price,
                            break_close_price=candle.close,
                            protected_swing_id=new_protected_high.record_id,
                            weak_swing_id=None,
                            break_candle_id=candle.record_id,
                            event_time_utc=candle.event_time_utc,
                            availability_time_utc=availability,
                        )
                    )
                    direction = StructureDirection.BEARISH
                    protected_low = None
                    protected_high = new_protected_high
                    weak_low = None
                    weak_high = None
                    weak_low_boundary_index = candle_index_by_id[candle.record_id]
                    last_change_availability = availability
        elif bos_candidate is not None:
            is_high_side, broken_swing = bos_candidate
            availability = max(
                candle.availability_time_utc, broken_swing.availability_time_utc
            )
            broken_ids.add(broken_swing.record_id)
            if is_high_side:
                replacement_protected_low = _most_recent_unbroken(
                    visible_swings_by_type[SwingType.SWING_LOW], broken_ids
                )
                assert protected_low is not None
                new_protected_low = (
                    replacement_protected_low
                    if replacement_protected_low is not None
                    else protected_low
                )
                transitions.append(
                    StructureTransitionCandidate(
                        symbol=candle.symbol,
                        timeframe=candle.timeframe,
                        transition_type=StructureTransitionType.BULLISH_BOS,
                        direction_before=StructureDirection.BULLISH,
                        direction_after=StructureDirection.BULLISH,
                        broken_swing_id=broken_swing.record_id,
                        broken_level_price=broken_swing.pivot_price,
                        break_close_price=candle.close,
                        protected_swing_id=new_protected_low.record_id,
                        weak_swing_id=None,
                        break_candle_id=candle.record_id,
                        event_time_utc=candle.event_time_utc,
                        availability_time_utc=availability,
                    )
                )
                protected_low = new_protected_low
                weak_high = None
                weak_high_boundary_index = candle_index_by_id[candle.record_id]
            else:
                replacement_protected_high = _most_recent_unbroken(
                    visible_swings_by_type[SwingType.SWING_HIGH], broken_ids
                )
                assert protected_high is not None
                new_protected_high = (
                    replacement_protected_high
                    if replacement_protected_high is not None
                    else protected_high
                )
                transitions.append(
                    StructureTransitionCandidate(
                        symbol=candle.symbol,
                        timeframe=candle.timeframe,
                        transition_type=StructureTransitionType.BEARISH_BOS,
                        direction_before=StructureDirection.BEARISH,
                        direction_after=StructureDirection.BEARISH,
                        broken_swing_id=broken_swing.record_id,
                        broken_level_price=broken_swing.pivot_price,
                        break_close_price=candle.close,
                        protected_swing_id=new_protected_high.record_id,
                        weak_swing_id=None,
                        break_candle_id=candle.record_id,
                        event_time_utc=candle.event_time_utc,
                        availability_time_utc=availability,
                    )
                )
                protected_high = new_protected_high
                weak_low = None
                weak_low_boundary_index = candle_index_by_id[candle.record_id]
            last_change_availability = availability

    elif kind == _EVENT_SWING_VISIBLE:
        swing = payload
        assert isinstance(swing, ConfirmedSwing)
        visible_swings_by_type[swing.swing_type].append(swing)

        if (
            swing.swing_type == SwingType.SWING_HIGH
            and direction == StructureDirection.BULLISH
            and weak_high is None
            and swing.pivot_bar_index > weak_high_boundary_index
            and swing.record_id not in broken_ids
        ):
            weak_high = swing
            last_change_availability = (
                max(last_change_availability, swing.availability_time_utc)
                if last_change_availability is not None
                else swing.availability_time_utc
            )
        if (
            swing.swing_type == SwingType.SWING_LOW
            and direction == StructureDirection.BEARISH
            and weak_low is None
            and swing.pivot_bar_index > weak_low_boundary_index
            and swing.record_id not in broken_ids
        ):
            weak_low = swing
            last_change_availability = (
                max(last_change_availability, swing.availability_time_utc)
                if last_change_availability is not None
                else swing.availability_time_utc
            )

    else:  # _EVENT_RELATIONSHIP
        relationship = payload
        assert isinstance(relationship, SwingRelationshipCandidate)
        latest_relationship_label[relationship.swing_type] = relationship.label
        latest_relationship_swing[relationship.swing_type] = relationship.current_swing

        if direction == StructureDirection.UNDETERMINED:
            high_label = latest_relationship_label[SwingType.SWING_HIGH]
            low_label = latest_relationship_label[SwingType.SWING_LOW]
            if (
                high_label == SwingRelationshipLabel.HIGHER_HIGH
                and low_label == SwingRelationshipLabel.HIGHER_LOW
            ):
                direction = StructureDirection.BULLISH
                protected_low = latest_relationship_swing[SwingType.SWING_LOW]
                weak_high = latest_relationship_swing[SwingType.SWING_HIGH]
                last_change_availability = relationship.availability_time_utc
            elif (
                high_label == SwingRelationshipLabel.LOWER_HIGH
                and low_label == SwingRelationshipLabel.LOWER_LOW
            ):
                direction = StructureDirection.BEARISH
                protected_high = latest_relationship_swing[SwingType.SWING_HIGH]
                weak_low = latest_relationship_swing[SwingType.SWING_LOW]
                last_change_availability = relationship.availability_time_utc

    return _StructureWalkCheckpoint(
        direction=direction,
        protected_high=protected_high,
        protected_low=protected_low,
        weak_high=weak_high,
        weak_low=weak_low,
        broken_ids=frozenset(broken_ids),
        weak_high_boundary_index=weak_high_boundary_index,
        weak_low_boundary_index=weak_low_boundary_index,
        latest_label_high=latest_relationship_label[SwingType.SWING_HIGH],  # type: ignore[arg-type]
        latest_label_low=latest_relationship_label[SwingType.SWING_LOW],  # type: ignore[arg-type]
        latest_swing_high=latest_relationship_swing[SwingType.SWING_HIGH],
        latest_swing_low=latest_relationship_swing[SwingType.SWING_LOW],
        visible_high=tuple(visible_swings_by_type[SwingType.SWING_HIGH]),
        visible_low=tuple(visible_swings_by_type[SwingType.SWING_LOW]),
        transitions=tuple(transitions),
        last_change_availability=last_change_availability,
    )


def _structure_event_identity(kind: int, payload: object) -> tuple[object, ...]:
    """A hashable key capturing every field of an event that the walk reads or
    sorts on, so that any change (including a same-length swing-content
    rewrite or a shifted confirmation time) breaks the common-prefix match and
    forces the affected suffix to be reprocessed."""
    if kind == _EVENT_CANDLE:
        assert isinstance(payload, NormalizedCandle)
        return ("C", str(payload.record_id))
    if kind == _EVENT_SWING_VISIBLE:
        assert isinstance(payload, ConfirmedSwing)
        return (
            "S",
            str(payload.record_id),
            payload.pivot_bar_index,
            payload.pivot_start_time_utc.isoformat(),
            format(payload.pivot_price.normalize(), "f"),
            payload.swing_type.value,
            payload.meaningful_confirmation_time_utc.isoformat(),
            payload.availability_time_utc.isoformat(),
        )
    assert isinstance(payload, SwingRelationshipCandidate)
    return (
        "R",
        payload.label.value,
        payload.swing_type.value,
        str(payload.current_swing_record_id),
        str(payload.predecessor_swing_record_id),
        payload.current_swing.pivot_bar_index,
        payload.availability_time_utc.isoformat(),
        format(payload.current_swing.pivot_price.normalize(), "f"),
    )


def _build_sorted_structure_events(
    candles: tuple[NormalizedCandle, ...],
    confirmed_swings: tuple[ConfirmedSwing, ...],
    relationship_candidates: tuple[SwingRelationshipCandidate, ...],
) -> list[tuple[datetime, int, tuple[object, ...], object]]:
    """Reproduces run_structure_walk's event construction and sort exactly."""
    events: list[tuple[datetime, int, tuple[object, ...], object]] = []
    for event_candle in candles:
        events.append(
            (
                event_candle.availability_time_utc,
                _EVENT_CANDLE,
                (event_candle.event_time_utc, str(event_candle.record_id)),
                event_candle,
            )
        )
    for event_swing in confirmed_swings:
        events.append(
            (
                event_swing.meaningful_confirmation_time_utc,
                _EVENT_SWING_VISIBLE,
                (
                    event_swing.pivot_bar_index,
                    event_swing.pivot_start_time_utc,
                    str(event_swing.record_id),
                ),
                event_swing,
            )
        )
    for event_relationship in relationship_candidates:
        events.append(
            (
                event_relationship.availability_time_utc,
                _EVENT_RELATIONSHIP,
                (
                    event_relationship.current_swing.pivot_bar_index,
                    str(event_relationship.current_swing_record_id),
                ),
                event_relationship,
            )
        )
    events.sort(key=lambda event: (event[0], event[1], event[2]))
    return events


@dataclass
class _StructureReplayState:
    """Private, per-timeframe incremental structure state for subsystem 2c.
    Not part of the public contract surface; owned exclusively by the scanner
    replay path. analyze_structure_state (and run_structure_walk) remain the
    unmodified batch oracle.

    §44R names six fields (timeframe, current_state, and the four active
    protected/weak swings). The active swings are held as full ConfirmedSwing
    objects — not ids — because CurrentStructureState carries only swing ids,
    not their pivot_price, which future candle BOS/CHoCH evaluation requires.
    The remaining fields are proven-necessary private additions for the
    checkpoint-resume walk (mirroring the subsystem 2b _MeasurementReplayState
    precedent, which the not-yet-built §44U event ledger will later subsume):
    candles_so_far / confirmed_swings_so_far / relationship_candidates rebuild
    the event stream; event_identities + checkpoints locate and resume from the
    earliest changed event; swing_relationships_so_far / structure_transitions_
    so_far / current_state hold the finalized public outputs (classification A
    accumulation until the 2f ledger owns it).

    Treated immutably: _advance_structure_replay_state never mutates an
    existing instance, so a raised exception leaves the caller's state intact.
    """

    resolver: _IdentityResolver
    rule_version_text: str
    timeframe: Timeframe | None = None
    symbol: InternalSymbol | None = None
    candles_so_far: tuple[NormalizedCandle, ...] = ()
    confirmed_swings_so_far: tuple[ConfirmedSwing, ...] = ()
    relationship_candidates: tuple[SwingRelationshipCandidate, ...] = ()
    event_identities: tuple[tuple[object, ...], ...] = ()
    checkpoints: tuple[_StructureWalkCheckpoint, ...] = ()
    swing_relationships_so_far: tuple[SwingRelationship, ...] = ()
    structure_transitions_so_far: tuple[StructureTransition, ...] = ()
    current_state: CurrentStructureState | None = None
    active_protected_high_swing: ConfirmedSwing | None = None
    active_protected_low_swing: ConfirmedSwing | None = None
    active_weak_high_swing: ConfirmedSwing | None = None
    active_weak_low_swing: ConfirmedSwing | None = None


def _create_initial_structure_replay_state(
    identity_provider: DerivedOutputIdentityProvider,
    configuration: StructureConfiguration,
) -> _StructureReplayState:
    return _StructureReplayState(
        resolver=_IdentityResolver(identity_provider),
        rule_version_text=str(configuration.rule_version),
    )


def _finalize_structure_outputs(
    candles: tuple[NormalizedCandle, ...],
    confirmed_swings: tuple[ConfirmedSwing, ...],
    relationship_candidates: tuple[SwingRelationshipCandidate, ...],
    walk_result: StructureWalkResult,
    resolver: _IdentityResolver,
    configuration: StructureConfiguration,
    rule_version_text: str,
) -> tuple[
    tuple[SwingRelationship, ...],
    tuple[StructureTransition, ...],
    CurrentStructureState,
]:
    """Reproduces analyze_structure_state's post-walk finalization exactly
    (sort + derive identities/fingerprints + build current_state), operating on
    an incrementally produced walk_result instead of a full-batch one. Shares
    the module-level _finalize / _compute_content_fingerprint / _IdentityResolver
    helpers with the oracle; the persistent resolver makes re-deriving unchanged
    entries a no-op and keeps identities stable across prefixes."""
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
    return swing_relationships, structure_transitions, current_state


def _advance_structure_replay_state(
    state: _StructureReplayState,
    candle: NormalizedCandle,
    confirmed_swings: tuple[ConfirmedSwing, ...],
    configuration: StructureConfiguration,
) -> _StructureReplayState:
    """Advance the incremental structure state by exactly one new candle plus
    the current (possibly non-append-changed) confirmed swings from the
    measurement state. Transactional: every new value is built from locals and
    the replacement _StructureReplayState is constructed only at the very end,
    so a raised exception (out-of-order candle) leaves the caller's state
    object — including its checkpoint tuple — completely untouched.

    The confirmed-swing frontier is handled by rebuilding the sorted event
    stream, diffing it against the previous stream to find the longest
    identical prefix, and resuming the walk from the checkpoint just before the
    earliest changed event. The append-only common case resumes from the final
    checkpoint and processes only the new candle event."""
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

    new_candles = (*state.candles_so_far, candle)

    if confirmed_swings == state.confirmed_swings_so_far:
        relationship_candidates = state.relationship_candidates
    else:
        relationship_candidates = detect_swing_relationships(
            confirmed_swings, configuration
        )

    events = _build_sorted_structure_events(
        new_candles, confirmed_swings, relationship_candidates
    )
    identities = tuple(
        _structure_event_identity(kind, payload) for _, kind, _, payload in events
    )

    common_prefix = 0
    limit = min(len(state.event_identities), len(identities))
    while (
        common_prefix < limit
        and state.event_identities[common_prefix] == identities[common_prefix]
    ):
        common_prefix += 1

    candle_index_by_id = {c.record_id: index for index, c in enumerate(new_candles)}

    reused_checkpoints = list(state.checkpoints[:common_prefix])
    current_checkpoint = (
        reused_checkpoints[-1] if reused_checkpoints else _INITIAL_STRUCTURE_CHECKPOINT
    )
    for _, kind, _, payload in events[common_prefix:]:
        current_checkpoint = _process_structure_event(
            current_checkpoint, kind, payload, candle_index_by_id
        )
        reused_checkpoints.append(current_checkpoint)

    final_checkpoint = (
        reused_checkpoints[-1] if reused_checkpoints else _INITIAL_STRUCTURE_CHECKPOINT
    )

    walk_result = StructureWalkResult(
        transitions=final_checkpoint.transitions,
        direction=final_checkpoint.direction,
        protected_high=final_checkpoint.protected_high,
        protected_low=final_checkpoint.protected_low,
        weak_high=final_checkpoint.weak_high,
        weak_low=final_checkpoint.weak_low,
        last_change_availability=final_checkpoint.last_change_availability,
        analyzed_swing_count=len(confirmed_swings),
    )

    swing_relationships, structure_transitions, current_state = (
        _finalize_structure_outputs(
            new_candles,
            confirmed_swings,
            relationship_candidates,
            walk_result,
            state.resolver,
            configuration,
            state.rule_version_text,
        )
    )

    return _StructureReplayState(
        resolver=state.resolver,
        rule_version_text=state.rule_version_text,
        timeframe=new_candles[0].timeframe,
        symbol=new_candles[0].symbol,
        candles_so_far=new_candles,
        confirmed_swings_so_far=confirmed_swings,
        relationship_candidates=relationship_candidates,
        event_identities=identities,
        checkpoints=tuple(reused_checkpoints),
        swing_relationships_so_far=swing_relationships,
        structure_transitions_so_far=structure_transitions,
        current_state=current_state,
        active_protected_high_swing=final_checkpoint.protected_high,
        active_protected_low_swing=final_checkpoint.protected_low,
        active_weak_high_swing=final_checkpoint.weak_high,
        active_weak_low_swing=final_checkpoint.weak_low,
    )


def _structure_replay_state_to_analysis(
    state: _StructureReplayState,
) -> StructureAnalysis:
    """Build the public StructureAnalysis from the incremental state, matching
    analyze_structure_state's shape exactly — including the empty-input special
    case (symbol/timeframe None, zero counts, empty tuples, no current_state)."""
    if not state.candles_so_far:
        return StructureAnalysis(
            symbol=None,
            timeframe=None,
            analyzed_candle_count=0,
            analyzed_swing_count=0,
            swing_relationships=(),
            structure_transitions=(),
            current_state=None,
        )
    return StructureAnalysis(
        symbol=state.symbol,
        timeframe=state.timeframe,
        analyzed_candle_count=len(state.candles_so_far),
        analyzed_swing_count=len(state.confirmed_swings_so_far),
        swing_relationships=state.swing_relationships_so_far,
        structure_transitions=state.structure_transitions_so_far,
        current_state=state.current_state,
    )
