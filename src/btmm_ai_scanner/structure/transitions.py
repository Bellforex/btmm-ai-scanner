from datetime import datetime
from decimal import Decimal
from typing import NamedTuple
from uuid import UUID

from btmm_ai_scanner.config.enums import InternalSymbol, Timeframe
from btmm_ai_scanner.contracts.normalized_candle import NormalizedCandle
from btmm_ai_scanner.contracts.provenance_record import EvidenceClassification
from btmm_ai_scanner.contracts.types import (
    ContractModel,
    SemVer,
    SHA256Fingerprint,
    UUIDv7,
)
from btmm_ai_scanner.domain.enums import SwingType
from btmm_ai_scanner.domain.swings import ConfirmedSwing
from btmm_ai_scanner.structure.enums import (
    StructureDirection,
    StructureTransitionType,
    SwingRelationshipLabel,
)
from btmm_ai_scanner.structure.relationships import SwingRelationshipCandidate


class StructureTransition(ContractModel):
    record_id: UUIDv7
    content_fingerprint: SHA256Fingerprint
    symbol: InternalSymbol
    timeframe: Timeframe
    transition_type: StructureTransitionType
    direction_before: StructureDirection
    direction_after: StructureDirection
    broken_swing_id: UUIDv7
    broken_level_price: Decimal
    break_close_price: Decimal
    protected_swing_id: UUIDv7
    weak_swing_id: UUIDv7 | None
    break_candle_id: UUIDv7
    event_time_utc: datetime
    availability_time_utc: datetime
    rule_version: SemVer
    contract_version: SemVer
    schema_version: SemVer
    evidence_classification: EvidenceClassification
    provenance_id: UUIDv7


class StructureTransitionCandidate(NamedTuple):
    symbol: InternalSymbol
    timeframe: Timeframe
    transition_type: StructureTransitionType
    direction_before: StructureDirection
    direction_after: StructureDirection
    broken_swing_id: UUID
    broken_level_price: Decimal
    break_close_price: Decimal
    protected_swing_id: UUID
    weak_swing_id: UUID | None
    break_candle_id: UUID
    event_time_utc: datetime
    availability_time_utc: datetime


class StructureWalkResult(NamedTuple):
    transitions: tuple[StructureTransitionCandidate, ...]
    direction: StructureDirection
    protected_high: ConfirmedSwing | None
    protected_low: ConfirmedSwing | None
    weak_high: ConfirmedSwing | None
    weak_low: ConfirmedSwing | None
    last_change_availability: datetime | None
    analyzed_swing_count: int


_EVENT_CANDLE = 0
_EVENT_SWING_VISIBLE = 1
_EVENT_RELATIONSHIP = 2


def _most_recent_unbroken(
    visible: list[ConfirmedSwing], broken_ids: set[UUID]
) -> ConfirmedSwing | None:
    candidates = [s for s in visible if s.record_id not in broken_ids]
    if not candidates:
        return None
    return max(
        candidates,
        key=lambda s: (s.pivot_bar_index, s.pivot_start_time_utc, str(s.record_id)),
    )


def run_structure_walk(
    candles: tuple[NormalizedCandle, ...],
    confirmed_swings: tuple[ConfirmedSwing, ...],
    relationship_candidates: tuple[SwingRelationshipCandidate, ...],
) -> StructureWalkResult:
    candle_index_by_id = {c.record_id: index for index, c in enumerate(candles)}

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

    direction = StructureDirection.UNDETERMINED
    protected_high: ConfirmedSwing | None = None
    protected_low: ConfirmedSwing | None = None
    weak_high: ConfirmedSwing | None = None
    weak_low: ConfirmedSwing | None = None
    broken_ids: set[UUID] = set()
    weak_high_boundary_index = -1
    weak_low_boundary_index = -1

    latest_relationship_label: dict[SwingType, object] = {
        SwingType.SWING_HIGH: None,
        SwingType.SWING_LOW: None,
    }
    latest_relationship_swing: dict[SwingType, ConfirmedSwing | None] = {
        SwingType.SWING_HIGH: None,
        SwingType.SWING_LOW: None,
    }
    visible_swings_by_type: dict[SwingType, list[ConfirmedSwing]] = {
        SwingType.SWING_HIGH: [],
        SwingType.SWING_LOW: [],
    }

    transitions: list[StructureTransitionCandidate] = []
    last_change_availability: datetime | None = None

    for _availability_time_utc, kind, _tiebreak, payload in events:
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
                    if new_protected_low is None:
                        continue
                    broken_ids.add(broken_swing.record_id)
                    availability = max(
                        candle.availability_time_utc, broken_swing.availability_time_utc
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
                    if new_protected_high is None:
                        continue
                    broken_ids.add(broken_swing.record_id)
                    availability = max(
                        candle.availability_time_utc, broken_swing.availability_time_utc
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
                continue

            if bos_candidate is not None:
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
            latest_relationship_swing[relationship.swing_type] = (
                relationship.current_swing
            )

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

    return StructureWalkResult(
        transitions=tuple(transitions),
        direction=direction,
        protected_high=protected_high,
        protected_low=protected_low,
        weak_high=weak_high,
        weak_low=weak_low,
        last_change_availability=last_change_availability,
        analyzed_swing_count=len(confirmed_swings),
    )
