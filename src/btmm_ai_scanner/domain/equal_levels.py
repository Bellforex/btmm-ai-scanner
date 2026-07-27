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
from btmm_ai_scanner.domain.configuration import MarketMeasurementConfiguration
from btmm_ai_scanner.domain.enums import EqualLevelType, SwingType
from btmm_ai_scanner.domain.swings import ConfirmedSwing

_TWO = Decimal("2")


class EqualLevelCluster(ContractModel):
    record_id: UUIDv7
    content_fingerprint: SHA256Fingerprint
    symbol: InternalSymbol
    timeframe: Timeframe
    cluster_type: EqualLevelType
    component_swing_record_ids: tuple[UUIDv7, ...]
    cluster_spread: Decimal
    equality_tolerance: Decimal
    reference_atr: Decimal
    zone_bottom: Decimal
    zone_top: Decimal
    representative_price: Decimal
    confirmation_time_utc: datetime
    availability_time_utc: datetime
    rule_version: SemVer
    contract_version: SemVer
    schema_version: SemVer
    evidence_classification: EvidenceClassification
    provenance_id: UUIDv7

    @property
    def liquidity_side(self) -> str:
        if self.cluster_type == EqualLevelType.EQUAL_HIGH:
            return "ABOVE_PRICE"
        return "BELOW_PRICE"

    @property
    def reference_price(self) -> Decimal:
        return self.representative_price


class EqualLevelClusterCandidate(NamedTuple):
    symbol: InternalSymbol
    timeframe: Timeframe
    cluster_type: EqualLevelType
    component_swing_record_ids: tuple[UUID, ...]
    first_seed_swing_id: UUID
    second_seed_swing_id: UUID
    cluster_spread: Decimal
    equality_tolerance: Decimal
    reference_atr: Decimal
    zone_bottom: Decimal
    zone_top: Decimal
    representative_price: Decimal
    confirmation_time_utc: datetime


def _median(values: list[Decimal]) -> Decimal:
    ordered = sorted(values)
    midpoint = len(ordered) // 2
    if len(ordered) % 2 == 1:
        return ordered[midpoint]
    return (ordered[midpoint - 1] + ordered[midpoint]) / _TWO


def _sweep_one_type(
    swings: list[ConfirmedSwing],
    cluster_type: EqualLevelType,
    configuration: MarketMeasurementConfiguration,
) -> list[EqualLevelClusterCandidate]:
    ordered = sorted(
        swings, key=lambda s: (s.meaningful_confirmation_time_utc, s.record_id)
    )

    results: list[EqualLevelClusterCandidate] = []
    members: list[ConfirmedSwing] = []

    def close_cluster() -> None:
        if len(members) < 2:
            return
        prices = [m.pivot_price for m in members]
        atrs = [m.pivot_reference_atr for m in members]
        reference_atr = _median(atrs)
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
                representative_price=(zone_bottom + zone_top) / _TWO,
                confirmation_time_utc=max(
                    m.meaningful_confirmation_time_utc for m in members
                ),
            )
        )

    for swing in ordered:
        if not members:
            members = [swing]
            continue

        candidate_prices = [m.pivot_price for m in members] + [swing.pivot_price]
        candidate_atrs = [m.pivot_reference_atr for m in members] + [
            swing.pivot_reference_atr
        ]
        reference_atr = _median(candidate_atrs)
        tolerance = configuration.equal_level_tolerance_atr_multiplier * reference_atr
        prospective_spread = max(candidate_prices) - min(candidate_prices)

        if prospective_spread <= tolerance:
            members.append(swing)
        else:
            close_cluster()
            members = [swing]

    close_cluster()
    return results


def detect_equal_level_clusters(
    confirmed_swings: tuple[ConfirmedSwing, ...],
    configuration: MarketMeasurementConfiguration,
) -> tuple[EqualLevelClusterCandidate, ...]:
    highs = [s for s in confirmed_swings if s.swing_type == SwingType.SWING_HIGH]
    lows = [s for s in confirmed_swings if s.swing_type == SwingType.SWING_LOW]

    results = _sweep_one_type(
        highs, EqualLevelType.EQUAL_HIGH, configuration
    ) + _sweep_one_type(lows, EqualLevelType.EQUAL_LOW, configuration)

    results.sort(key=lambda c: c.confirmation_time_utc)
    return tuple(results)
