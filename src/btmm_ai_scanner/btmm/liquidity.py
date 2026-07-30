from collections.abc import Sequence
from typing import NamedTuple
from uuid import UUID

from btmm_ai_scanner.btmm.enums import BtmmEvidenceSource, BtmmLiquidityLocation
from btmm_ai_scanner.poi.enums import PoiLifecycleTransitionType
from btmm_ai_scanner.poi.lifecycle import PoiLifecycleTransition


class AutomaticLiquidityEvidence(NamedTuple):
    liquidity_location: BtmmLiquidityLocation
    liquidity_evidence_source: BtmmEvidenceSource


def find_automatic_liquidity_evidence(
    poi_record_id: UUID,
    poi_lifecycle_transitions: Sequence[PoiLifecycleTransition],
) -> AutomaticLiquidityEvidence | None:
    for transition in poi_lifecycle_transitions:
        if (
            transition.poi_record_id == poi_record_id
            and transition.transition_type
            == PoiLifecycleTransitionType.FALSE_INVALIDATION_CONFIRMED
        ):
            return AutomaticLiquidityEvidence(
                liquidity_location=BtmmLiquidityLocation.LIQUIDITY_AFTER_POI,
                liquidity_evidence_source=BtmmEvidenceSource.RULE_BASED,
            )
    return None
