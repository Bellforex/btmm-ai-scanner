from datetime import datetime
from decimal import Decimal
from typing import NamedTuple
from uuid import UUID

from btmm_ai_scanner.config.enums import InternalSymbol, Timeframe
from btmm_ai_scanner.contracts.provenance_record import EvidenceClassification
from btmm_ai_scanner.contracts.types import (
    ContractModel,
    SemVer,
    SHA256Fingerprint,
    UUIDv7,
)
from btmm_ai_scanner.domain.enums import SwingType
from btmm_ai_scanner.domain.swings import ConfirmedSwing
from btmm_ai_scanner.structure.configuration import StructureConfiguration
from btmm_ai_scanner.structure.enums import SwingRelationshipLabel


class SwingRelationship(ContractModel):
    record_id: UUIDv7
    content_fingerprint: SHA256Fingerprint
    symbol: InternalSymbol
    timeframe: Timeframe
    swing_type: SwingType
    label: SwingRelationshipLabel
    current_swing_record_id: UUIDv7
    predecessor_swing_record_id: UUIDv7
    current_pivot_price: Decimal
    predecessor_pivot_price: Decimal
    availability_time_utc: datetime
    rule_version: SemVer
    contract_version: SemVer
    schema_version: SemVer
    evidence_classification: EvidenceClassification
    provenance_id: UUIDv7


class SwingRelationshipCandidate(NamedTuple):
    symbol: InternalSymbol
    timeframe: Timeframe
    swing_type: SwingType
    label: SwingRelationshipLabel
    current_swing_record_id: UUID
    predecessor_swing_record_id: UUID
    current_pivot_price: Decimal
    predecessor_pivot_price: Decimal
    availability_time_utc: datetime
    current_swing: ConfirmedSwing
    predecessor_swing: ConfirmedSwing


def _classify_label(
    current: ConfirmedSwing,
    predecessor: ConfirmedSwing,
    configuration: StructureConfiguration,
    is_high: bool,
) -> SwingRelationshipLabel:
    tolerance = (
        configuration.swing_relationship_equal_tolerance_atr_multiplier
        * current.pivot_reference_atr
    )
    if current.pivot_price > predecessor.pivot_price + tolerance:
        return (
            SwingRelationshipLabel.HIGHER_HIGH
            if is_high
            else SwingRelationshipLabel.HIGHER_LOW
        )
    if current.pivot_price < predecessor.pivot_price - tolerance:
        return (
            SwingRelationshipLabel.LOWER_HIGH
            if is_high
            else SwingRelationshipLabel.LOWER_LOW
        )
    return (
        SwingRelationshipLabel.EQUAL_HIGH
        if is_high
        else SwingRelationshipLabel.EQUAL_LOW
    )


def detect_swing_relationships(
    confirmed_swings: tuple[ConfirmedSwing, ...],
    configuration: StructureConfiguration,
) -> tuple[SwingRelationshipCandidate, ...]:
    highs = [s for s in confirmed_swings if s.swing_type == SwingType.SWING_HIGH]
    lows = [s for s in confirmed_swings if s.swing_type == SwingType.SWING_LOW]

    results: list[SwingRelationshipCandidate] = []
    for is_high, group in ((True, highs), (False, lows)):
        for index in range(1, len(group)):
            current = group[index]
            predecessor = group[index - 1]
            label = _classify_label(current, predecessor, configuration, is_high)
            availability = max(
                current.availability_time_utc, predecessor.availability_time_utc
            )
            results.append(
                SwingRelationshipCandidate(
                    symbol=current.symbol,
                    timeframe=current.timeframe,
                    swing_type=current.swing_type,
                    label=label,
                    current_swing_record_id=current.record_id,
                    predecessor_swing_record_id=predecessor.record_id,
                    current_pivot_price=current.pivot_price,
                    predecessor_pivot_price=predecessor.pivot_price,
                    availability_time_utc=availability,
                    current_swing=current,
                    predecessor_swing=predecessor,
                )
            )
    return tuple(results)
