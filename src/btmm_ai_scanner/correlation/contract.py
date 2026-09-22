"""Correlation-V1 (T0) — the versioned web-facing output contract.

Built FROM ``TopDownCorrelationDecision`` (``btmm_ai_scanner.correlation.engine``),
never the other way around — the analytical engine's own internal result
never has to match a web-serialization shape 1:1. This does NOT replace
``ScannerAnalysis`` (``btmm_ai_scanner.scanner.analysis``); it is a NEW,
additional, versioned contract intended for the Bell Academy Hub web
integration (a later, separate phase — this repository does not call the
website and the website is not touched here).

Prices are Decimal, never float (matching the rest of the engine); the
future web renderer is responsible for its own price/time -> pixel mapping,
never this package (Phase 24: "Do not use pixels").
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from btmm_ai_scanner.btrc.enums import (
    AnalyticalPermission,
    BreakoutState,
    Direction,
    MomentumDirection,
    PullbackState,
    Regime,
    TrendAlignment,
    TrendState,
)
from btmm_ai_scanner.config.enums import InternalSymbol, Timeframe
from btmm_ai_scanner.contracts.types import ContractModel
from btmm_ai_scanner.correlation.engine import TopDownCorrelationDecision
from btmm_ai_scanner.correlation.enums import (
    SetupVerdict,
    TopDownCorrelationState,
    TradingMode,
)
from btmm_ai_scanner.poi.enums import PoiDirection, PoiLifecycleStatus, PoiType

_STRONG_DIRECTIONS = frozenset({Direction.STRONG_BULLISH, Direction.STRONG_BEARISH})


class WebAuthorityTimeframeContract(ContractModel):
    timeframe: Timeframe
    direction: Direction
    state: TrendState


class WebAuthorityContract(ContractModel):
    anchor_timeframe: Timeframe | None
    direction: Direction
    strength: str
    per_timeframe: tuple[WebAuthorityTimeframeContract, ...]


class WebCorrelationContract(ContractModel):
    state: TopDownCorrelationState
    supporting_reasons: tuple[str, ...]
    opposing_reasons: tuple[str, ...]


class WebSetupCandidateContract(ContractModel):
    poi_record_id: str
    poi_type: PoiType
    direction: PoiDirection
    zone_top: Decimal
    zone_bottom: Decimal
    source_timeframe: Timeframe
    lifecycle_status: PoiLifecycleStatus | None
    btmm_valid: bool
    analytical_permission: AnalyticalPermission
    trend_alignment: TrendAlignment
    confluence_score: int
    supporting_reasons: tuple[str, ...]
    opposing_reasons: tuple[str, ...]


class WebSetupContract(ContractModel):
    verdict: SetupVerdict
    execution_timeframe: Timeframe | None
    selected_candidate: WebSetupCandidateContract | None
    reasons: tuple[str, ...]


class WebTechnicalContextContract(ContractModel):
    """Present only when a candidate was selected — an evergreen INSUFFICIENT_DATA/
    NO_VALID_SETUP result has nothing to attach this to and every field is
    ``None``, never a fabricated value."""

    regime: Regime | None
    momentum: MomentumDirection | None
    breakout: BreakoutState | None
    pullback: PullbackState | None
    liquidity_evidence: tuple[str, ...]
    structure_evidence: tuple[str, ...]


class WebTradePlanContract(ContractModel):
    """Deliberately NOT entry/stop/target — see Phase 22/Phase 19: the
    validated-strategy work (entry, SL, TP, R:R policy) is future, separate,
    and explicitly not exposed from this engine."""

    status: str = "NOT_VALIDATED"


class WebPresentationContract(ContractModel):
    """A UI/output concern ONLY — never changes the POI source timeframe,
    execution timeframe or authority anchor (see Phase "Presentation
    timeframe policy"). ``requested_timeframe`` is echoed back only if it
    was one of the mode profile's ``presentation_timeframes``; otherwise
    ``None`` (never silently substituted)."""

    requested_timeframe: Timeframe | None


class WebProvenanceContract(ContractModel):
    source_scanner_rule_version: str
    source_record_ids: tuple[str, ...]


class TopDownWebContract(ContractModel):
    contract_version: str
    schema_version: str
    rule_version: str
    symbol: InternalSymbol | None
    mode: TradingMode
    evaluated_at_utc: datetime
    supplied_timeframes: tuple[Timeframe, ...]
    recommended_timeframes_missing: tuple[Timeframe, ...]
    authority: WebAuthorityContract
    correlation: WebCorrelationContract
    setup: WebSetupContract
    technical_context: WebTechnicalContextContract
    trade_plan: WebTradePlanContract
    presentation: WebPresentationContract
    provenance: WebProvenanceContract


def build_web_contract(
    decision: TopDownCorrelationDecision,
    symbol: InternalSymbol | None,
    requested_presentation_timeframe: Timeframe | None = None,
) -> TopDownWebContract:
    authority = decision.authority
    strength = "STRONG" if authority.mode_direction in _STRONG_DIRECTIONS else "NORMAL"

    presentation_timeframe = (
        requested_presentation_timeframe
        if requested_presentation_timeframe is not None
        and requested_presentation_timeframe in decision.profile.presentation_timeframes
        else None
    )

    selected = decision.selected_candidate
    setup_candidate: WebSetupCandidateContract | None = None
    technical_context = WebTechnicalContextContract(
        regime=None,
        momentum=None,
        breakout=None,
        pullback=None,
        liquidity_evidence=(),
        structure_evidence=(),
    )
    provenance_ids: tuple[str, ...] = ()
    execution_timeframe: Timeframe | None = None

    if selected is not None:
        poi = selected.poi
        btrc = selected.btrc_decision
        execution_timeframe = poi.source_timeframe
        setup_candidate = WebSetupCandidateContract(
            poi_record_id=str(poi.record_id),
            poi_type=poi.poi_type,
            direction=poi.direction,
            zone_top=poi.zone_top,
            zone_bottom=poi.zone_bottom,
            source_timeframe=poi.source_timeframe,
            lifecycle_status=btrc.poi_lifecycle_status,
            btmm_valid=btrc.btmm_valid,
            analytical_permission=btrc.analytical_permission,
            trend_alignment=btrc.trend_alignment,
            confluence_score=btrc.final_confluence_score,
            supporting_reasons=btrc.supporting_reasons,
            opposing_reasons=btrc.opposing_reasons,
        )
        technical_context = WebTechnicalContextContract(
            regime=btrc.regime,
            momentum=btrc.momentum_direction,
            breakout=btrc.breakout_state,
            pullback=btrc.pullback_state,
            liquidity_evidence=btrc.supporting_reasons,
            structure_evidence=btrc.opposing_reasons,
        )
        provenance_ids = btrc.provenance_ids

    return TopDownWebContract(
        contract_version=str(decision.contract_version),
        schema_version=str(decision.schema_version),
        rule_version=str(decision.rule_version),
        symbol=symbol,
        mode=decision.mode,
        evaluated_at_utc=decision.evaluated_at_utc,
        supplied_timeframes=authority.supplied_timeframes,
        recommended_timeframes_missing=authority.missing_recommended_timeframes,
        authority=WebAuthorityContract(
            anchor_timeframe=authority.authority_anchor_timeframe,
            direction=authority.mode_direction,
            strength=strength,
            per_timeframe=tuple(
                WebAuthorityTimeframeContract(
                    timeframe=tf.timeframe,
                    direction=tf.direction,
                    state=tf.trend_state,
                )
                for tf in authority.per_timeframe
            ),
        ),
        correlation=WebCorrelationContract(
            state=authority.correlation_state,
            supporting_reasons=authority.supporting_reasons,
            opposing_reasons=authority.opposing_reasons,
        ),
        setup=WebSetupContract(
            verdict=decision.verdict,
            execution_timeframe=execution_timeframe,
            selected_candidate=setup_candidate,
            reasons=decision.verdict_reasons,
        ),
        technical_context=technical_context,
        trade_plan=WebTradePlanContract(),
        presentation=WebPresentationContract(requested_timeframe=presentation_timeframe),
        provenance=WebProvenanceContract(
            source_scanner_rule_version=str(decision.rule_version),
            source_record_ids=provenance_ids,
        ),
    )


# --------------------------------------------------------------------------
# Annotation-data contract (Phase 24) — structured price/time coordinates
# for a FUTURE web renderer. No pixels, no drawing. Only the selected
# candidate's own POI zone is surfaced at T0; broadening this to every
# visible candidate/liquidity level is a natural, additive future extension.
# --------------------------------------------------------------------------


class AnnotationBox(ContractModel):
    kind: str
    price_top: Decimal
    price_bottom: Decimal
    timeframe: Timeframe
    label: str


class AnnotationContract(ContractModel):
    boxes: tuple[AnnotationBox, ...]


def build_annotation_contract(decision: TopDownCorrelationDecision) -> AnnotationContract:
    selected = decision.selected_candidate
    if selected is None:
        return AnnotationContract(boxes=())
    poi = selected.poi
    return AnnotationContract(
        boxes=(
            AnnotationBox(
                kind="candidate_poi_zone",
                price_top=poi.zone_top,
                price_bottom=poi.zone_bottom,
                timeframe=poi.source_timeframe,
                label=f"{poi.poi_type.value} ({poi.direction.value})",
            ),
        )
    )
