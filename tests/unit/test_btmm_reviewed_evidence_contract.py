"""The reviewed-evidence contract that decides whether a BTMM setup confirms.

`analyze_btmm` takes a fourth input, `reviewed_evidence`, which the scanner does
not compute -- the caller supplies it, and `BtmmReviewedEvidence` validates that
its sources are human-reviewed. Both `BTMM_CONFIRMED` assignments in
`lifecycle.py` sit behind `_resolve_final_gates`, whose signature takes a
NON-optional record, so a run with no evidence cancels at
`lifecycle.py:407-414` instead.

That split is deliberate and is the P4 architecture:

* the ENGINE implements the whole state machine, confirmation included, and is
  provable against the Python oracle by supplying evidence fixtures;
* the current TradingView RUNTIME has no authorized transport for reviewed
  evidence, so it runs the `reviewed_evidence=()` contract and cannot reach
  confirmation.

A no-evidence run failing to confirm is therefore correct behaviour, not a
shortfall -- and nothing may ever paper over it by defaulting a gate to PASS or
by dressing a price calculation up as expert evidence. These tests pin both
halves so neither can drift.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any
from uuid import UUID

import pytest
from pydantic import ValidationError

from btmm_ai_scanner.btmm.analyzer import (
    BtmmTimeframeInput,
    InputPrefixMismatchError,
    MissingSourcePoiRecordError,
    analyze_btmm,
)
from btmm_ai_scanner.btmm.configuration import BtmmConfiguration
from btmm_ai_scanner.btmm.enums import (
    BtmmBlockedReason,
    BtmmCancellationReason,
    BtmmContextAlignmentStatus,
    BtmmEvidenceSource,
    BtmmFormationStage,
    BtmmLifecycleStatus,
    BtmmLifecycleTransitionType,
    BtmmLiquidityEvidenceStatus,
    BtmmSessionStatus,
    BtmmVolumePillarStatus,
)
from btmm_ai_scanner.btmm.reviewed_evidence import BtmmReviewedEvidence
from btmm_ai_scanner.config.enums import InternalSymbol, Timeframe
from btmm_ai_scanner.contracts.normalized_candle import NormalizedCandle
from btmm_ai_scanner.contracts.provenance_record import EvidenceClassification
from btmm_ai_scanner.contracts.raw_candle import CandleCompleteness, CandleVolumeKind
from btmm_ai_scanner.contracts.types import SemVer
from btmm_ai_scanner.domain import MarketMeasurementAnalysis, MixedSymbolAnalysisError
from btmm_ai_scanner.domain.enums import DerivedOutputType
from btmm_ai_scanner.poi.analyzer import PoiAnalysis
from btmm_ai_scanner.poi.enums import PoiDirection, PoiFamily, PoiType
from btmm_ai_scanner.poi.observation import PoiObservation

_FP = "a" * 64
_PROV = UUID("0193f450-1234-7abc-8def-abcdefabcdff")
_RAW = UUID("0193f450-1234-7abc-8def-abcdefabcdaa")
_T0 = datetime(2026, 1, 1, tzinfo=UTC)
_POI_ID = UUID("0193f450-aaaa-7000-8000-000000000001")
_OTHER_POI_ID = UUID("0193f450-aaaa-7000-8000-000000000009")
_MINUTES = {Timeframe.M1: 1, Timeframe.M5: 5, Timeframe.M15: 15}

#: M5 and M15 form setups; M1 is supporting-only. Same price action, so the
#: difference in outcome is the formation rule and nothing else.
_FORMATION_TFS = (Timeframe.M5, Timeframe.M15)
_ALL_TFS = (Timeframe.M1, Timeframe.M5, Timeframe.M15)


class _SequentialIdentity:
    def __init__(self) -> None:
        self._seen: dict[Any, UUID] = {}
        self._count = 0

    def identify(
        self, *, output_type: DerivedOutputType, semantic_key: tuple[str, ...]
    ) -> UUID:
        key = (output_type, semantic_key)
        if key not in self._seen:
            self._count += 1
            self._seen[key] = UUID(f"0193f450-0000-7000-8000-{self._count:012x}")
        return self._seen[key]


def _candle(
    timeframe: Timeframe, index: int, prices: tuple[str, str, str, str]
) -> NormalizedCandle:
    step = timedelta(minutes=_MINUTES[timeframe])
    event = _T0 + step * index
    available = event + step
    open_, high, low, close = prices
    return NormalizedCandle.model_validate(
        {
            "record_id": UUID(
                f"0193f4{_MINUTES[timeframe]:02d}-1234-7abc-8def-{index:012x}"
            ),
            "content_fingerprint": _FP,
            "raw_candle_id": _RAW,
            "provider": "FXCM",
            "source_reference": "fxcm",
            "source_symbol": "XAUUSD",
            "source_timeframe": timeframe.value,
            "symbol": InternalSymbol.XAUUSD,
            "timeframe": timeframe,
            "event_time_utc": event,
            "availability_time_utc": available,
            "processing_time_utc": available,
            "original_event_time": event,
            "original_availability_time": available,
            "original_timezone": "UTC",
            "open": Decimal(open_),
            "high": Decimal(high),
            "low": Decimal(low),
            "close": Decimal(close),
            "volume": None,
            "volume_kind": CandleVolumeKind.UNKNOWN,
            "completeness": CandleCompleteness.CONFIRMED_COMPLETE,
            "rule_version": SemVer.parse("0.1.0"),
            "contract_version": SemVer.parse("0.1.0"),
            "schema_version": SemVer.parse("0.1.0"),
            "provenance_id": _PROV,
        }
    )


def _candles(
    timeframe: Timeframe, *, strong_reaction: bool = True
) -> tuple[NormalizedCandle, ...]:
    """The shape that carries a setup all the way to the final gate: quiet
    approach, a sweep into the zone, then a reaction away from it."""
    out = [_candle(timeframe, i, ("105", "105.2", "104.8", "105")) for i in range(14)]
    out.append(_candle(timeframe, 14, ("105", "105.1", "100.5", "100.8")))
    out.append(_candle(timeframe, 15, ("100.8", "102.2", "100.7", "102.0")))
    if strong_reaction:
        out.append(_candle(timeframe, 16, ("102.0", "103.5", "101.9", "103.4")))
        out.append(_candle(timeframe, 17, ("103.4", "105.0", "103.3", "104.9")))
        out.append(_candle(timeframe, 18, ("104.9", "106.5", "104.8", "106.4")))
        out.append(_candle(timeframe, 19, ("106.4", "108.0", "106.3", "107.9")))
    else:
        out.append(_candle(timeframe, 16, ("102.0", "102.3", "101.8", "102.1")))
        out.append(_candle(timeframe, 17, ("102.1", "102.4", "101.9", "102.0")))
        out.append(_candle(timeframe, 18, ("102.0", "102.3", "101.7", "101.9")))
        out.append(_candle(timeframe, 19, ("101.9", "102.2", "101.6", "101.8")))
    return tuple(out)


def _poi(timeframe: Timeframe) -> PoiObservation:
    anchor = _candle(timeframe, 13, ("105", "105.2", "104.8", "105"))
    return PoiObservation(
        record_id=_POI_ID,
        content_fingerprint=_FP,
        symbol=InternalSymbol.XAUUSD,
        source_timeframe=timeframe,
        effective_timeframe=timeframe,
        family=PoiFamily.STRUCTURAL,
        poi_type=PoiType.SUPPORT_ZONE,
        direction=PoiDirection.BULLISH,
        zone_top=Decimal("101"),
        zone_bottom=Decimal("100"),
        representative_price=None,
        strength_tier=None,
        source_candle_record_ids=(),
        source_measurement_record_ids=(),
        merged_source_poi_record_ids=(),
        candidate_event_time_utc=anchor.event_time_utc,
        confirmation_time_utc=anchor.event_time_utc,
        availability_time_utc=anchor.availability_time_utc,
        rule_version=SemVer.parse("0.1.0"),
        contract_version=SemVer.parse("0.1.0"),
        schema_version=SemVer.parse("0.1.0"),
        evidence_classification=EvidenceClassification.ENGINEERING_PROVISIONAL,
        provenance_id=_PROV,
    )


def _evidence(
    timeframe: Timeframe,
    *,
    liquidity: BtmmLiquidityEvidenceStatus = BtmmLiquidityEvidenceStatus.PRESENT,
    market_direction: BtmmContextAlignmentStatus = BtmmContextAlignmentStatus.ALIGNED,
    framework: BtmmContextAlignmentStatus = BtmmContextAlignmentStatus.ALIGNED,
    session: BtmmSessionStatus = BtmmSessionStatus.ACTIVE,
    volume: BtmmVolumePillarStatus = BtmmVolumePillarStatus.SUPPORTS,
    context_source: BtmmEvidenceSource = BtmmEvidenceSource.EXPERT_LABELLED,
    liquidity_source: BtmmEvidenceSource = BtmmEvidenceSource.EXPERT_LABELLED,
    volume_source: BtmmEvidenceSource = BtmmEvidenceSource.EXPERT_LABELLED,
    poi_record_id: UUID = _POI_ID,
) -> BtmmReviewedEvidence:
    return BtmmReviewedEvidence(
        symbol=InternalSymbol.XAUUSD,
        timeframe=timeframe,
        source_poi_record_id=poi_record_id,
        market_direction_status=market_direction,
        analytical_framework_status=framework,
        session_status=session,
        liquidity_evidence_status=liquidity,
        volume_pillar_status=volume,
        context_input_source=context_source,
        liquidity_event_source=liquidity_source,
        volume_evidence_source=volume_source,
        availability_time_utc=_T0,
        rule_version=SemVer.parse("0.1.0"),
        contract_version=SemVer.parse("0.1.0"),
        schema_version=SemVer.parse("0.1.0"),
    )


def _run(
    timeframe: Timeframe,
    evidence: tuple[BtmmReviewedEvidence, ...] = (),
    *,
    strong_reaction: bool = True,
) -> Any:
    candles = _candles(timeframe, strong_reaction=strong_reaction)
    bundle = BtmmTimeframeInput(
        timeframe=timeframe,
        candles=candles,
        measurement_analysis=MarketMeasurementAnalysis(
            symbol=InternalSymbol.XAUUSD,
            timeframe=timeframe,
            analyzed_candle_count=len(candles),
            confirmed_swings=(),
            displacement_observations=(),
            equal_level_clusters=(),
            support_resistance_zones=(),
            trendlines=(),
        ),
    )
    poi_analysis = PoiAnalysis(
        symbol=InternalSymbol.XAUUSD,
        analyzed_timeframes=(timeframe,),
        analyzed_candle_count_by_timeframe=(0,),
        poi_observations=(_poi(timeframe),),
        poi_lifecycle_transitions=(),
        poi_overlap_relationships=(),
        current_poi_states=(),
    )
    return analyze_btmm(
        (bundle,),
        poi_analysis,
        evidence,
        BtmmConfiguration(minimum_price_tick=Decimal("0.01")),
        _SequentialIdentity(),
    )


def _state(result: Any) -> Any:
    assert len(result.current_btmm_states) == 1
    return result.current_btmm_states[0]


# --------------------------------------------------------------------------
# The runtime contract: no evidence
# --------------------------------------------------------------------------


@pytest.mark.parametrize("timeframe", _ALL_TFS)
def test_no_evidence_cancels_for_missing_liquidity(timeframe: Timeframe) -> None:
    """`lifecycle.py:407-414`. This is what the live TradingView runtime does."""
    state = _state(_run(timeframe))
    assert state.primary_state is BtmmLifecycleStatus.BTMM_CANCELLED
    assert state.cancellation_reason is BtmmCancellationReason.NO_LIQUIDITY_EVIDENCE
    assert state.formation_stage is BtmmFormationStage.FINAL_GATE_EVALUATION
    assert state.blocked_reason is None


@pytest.mark.parametrize("timeframe", _ALL_TFS)
def test_no_evidence_can_never_confirm(timeframe: Timeframe) -> None:
    """The architectural guard. If this ever fails, something has started
    satisfying a human-reviewed gate automatically."""
    result = _run(timeframe)
    assert _state(result).primary_state is not BtmmLifecycleStatus.BTMM_CONFIRMED
    types = {t.transition_type for t in result.btmm_lifecycle_transitions}
    assert BtmmLifecycleTransitionType.CONFIRMED not in types


# --------------------------------------------------------------------------
# The engine contract: evidence supplied
# --------------------------------------------------------------------------


@pytest.mark.parametrize("timeframe", _FORMATION_TFS)
def test_expert_labelled_evidence_confirms_on_a_formation_timeframe(
    timeframe: Timeframe,
) -> None:
    state = _state(_run(timeframe, (_evidence(timeframe),)))
    assert state.primary_state is BtmmLifecycleStatus.BTMM_CONFIRMED
    assert state.cancellation_reason is None
    assert state.blocked_reason is None


@pytest.mark.parametrize("timeframe", _FORMATION_TFS)
def test_hybrid_reviewed_evidence_also_confirms(timeframe: Timeframe) -> None:
    evidence = _evidence(
        timeframe,
        context_source=BtmmEvidenceSource.HYBRID_REVIEWED,
        liquidity_source=BtmmEvidenceSource.HYBRID_REVIEWED,
        volume_source=BtmmEvidenceSource.HYBRID_REVIEWED,
    )
    state = _state(_run(timeframe, (evidence,)))
    assert state.primary_state is BtmmLifecycleStatus.BTMM_CONFIRMED


def test_confirmation_emits_the_confirmed_transition() -> None:
    result = _run(Timeframe.M15, (_evidence(Timeframe.M15),))
    types = [t.transition_type for t in result.btmm_lifecycle_transitions]
    assert BtmmLifecycleTransitionType.CONFIRMED in types


def test_transitions_are_ordered_by_time_then_type_not_by_emission() -> None:
    """Confirmation shares its bar with the two reaction gates, and the output
    orders that group by transition-type name rather than by the order the walk
    emitted them. A Pine port has to reproduce this ordering, not its own."""
    result = _run(Timeframe.M15, (_evidence(Timeframe.M15),))
    rows = [
        (t.availability_time_utc, t.event_time_utc, t.transition_type.value)
        for t in result.btmm_lifecycle_transitions
    ]
    assert rows == sorted(rows)

    latest = max(row[0] for row in rows)
    final_bar = [row[2] for row in rows if row[0] == latest]
    assert final_bar == [
        BtmmLifecycleTransitionType.CONFIRMED.value,
        BtmmLifecycleTransitionType.REACTION_GATE_CONFIRMED.value,
        BtmmLifecycleTransitionType.REACTION_SPEED_GATE_CONFIRMED.value,
    ]


def test_m1_is_supporting_only_even_with_perfect_evidence() -> None:
    """Same price action and the same fully-aligned evidence that confirms on
    M5/M15 must block on M1, because the formation rule is a property of the
    POI's own timeframe."""
    state = _state(_run(Timeframe.M1, (_evidence(Timeframe.M1),)))
    assert state.primary_state is BtmmLifecycleStatus.BTMM_BLOCKED
    assert state.blocked_reason is BtmmBlockedReason.FORMATION_TIMEFRAME_NOT_CONFIRMED
    assert state.cancellation_reason is None


# --------------------------------------------------------------------------
# `_resolve_final_gates` precedence, in the order the source checks it
# --------------------------------------------------------------------------


def test_missing_liquidity_outranks_every_other_failure() -> None:
    """Liquidity is checked first, so it wins even when context, session and
    volume are all failing too."""
    evidence = _evidence(
        Timeframe.M15,
        liquidity=BtmmLiquidityEvidenceStatus.PENDING,
        market_direction=BtmmContextAlignmentStatus.MISALIGNED,
        session=BtmmSessionStatus.INACTIVE,
        volume=BtmmVolumePillarStatus.FAILS,
    )
    state = _state(_run(Timeframe.M15, (evidence,)))
    assert state.cancellation_reason is BtmmCancellationReason.NO_LIQUIDITY_EVIDENCE


def test_misaligned_context_outranks_session_and_volume() -> None:
    evidence = _evidence(
        Timeframe.M15,
        market_direction=BtmmContextAlignmentStatus.MISALIGNED,
        session=BtmmSessionStatus.INACTIVE,
        volume=BtmmVolumePillarStatus.FAILS,
    )
    state = _state(_run(Timeframe.M15, (evidence,)))
    assert state.cancellation_reason is BtmmCancellationReason.CONTEXT_REJECTED


def test_inactive_session_outranks_volume() -> None:
    evidence = _evidence(
        Timeframe.M15,
        session=BtmmSessionStatus.INACTIVE,
        volume=BtmmVolumePillarStatus.FAILS,
    )
    state = _state(_run(Timeframe.M15, (evidence,)))
    assert state.cancellation_reason is BtmmCancellationReason.SESSION_INACTIVE


def test_failed_volume_pillar_cancels() -> None:
    evidence = _evidence(Timeframe.M15, volume=BtmmVolumePillarStatus.FAILS)
    state = _state(_run(Timeframe.M15, (evidence,)))
    assert state.cancellation_reason is BtmmCancellationReason.VOLUME_PILLAR_FAILED


@pytest.mark.parametrize(
    "framework",
    [BtmmContextAlignmentStatus.PENDING, BtmmContextAlignmentStatus.UNKNOWN],
)
def test_unresolved_context_blocks_rather_than_cancels(
    framework: BtmmContextAlignmentStatus,
) -> None:
    """Not-yet-aligned is different from misaligned: it blocks, leaving the
    setup recoverable, instead of cancelling it."""
    evidence = _evidence(Timeframe.M15, framework=framework)
    state = _state(_run(Timeframe.M15, (evidence,)))
    assert state.primary_state is BtmmLifecycleStatus.BTMM_BLOCKED
    assert state.blocked_reason is BtmmBlockedReason.CONTEXT_UNKNOWN


@pytest.mark.parametrize(
    "volume",
    [
        BtmmVolumePillarStatus.PENDING,
        BtmmVolumePillarStatus.MISSING_DATA,
        BtmmVolumePillarStatus.UNRESOLVED,
    ],
)
def test_unresolved_volume_blocks_on_volume_review(
    volume: BtmmVolumePillarStatus,
) -> None:
    evidence = _evidence(Timeframe.M15, volume=volume)
    state = _state(_run(Timeframe.M15, (evidence,)))
    assert state.primary_state is BtmmLifecycleStatus.BTMM_BLOCKED
    assert state.blocked_reason is BtmmBlockedReason.VOLUME_REVIEW_PENDING


# --------------------------------------------------------------------------
# Evidence source validators -- these are what make the input "reviewed"
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "source",
    [
        BtmmEvidenceSource.EXPERT_LABELLED,
        BtmmEvidenceSource.HYBRID_REVIEWED,
        BtmmEvidenceSource.RULE_BASED_REVIEWED,
    ],
)
def test_context_and_liquidity_accept_the_three_reviewed_sources(
    source: BtmmEvidenceSource,
) -> None:
    _evidence(Timeframe.M15, context_source=source, liquidity_source=source)


@pytest.mark.parametrize(
    "source", [BtmmEvidenceSource.RULE_BASED, BtmmEvidenceSource.MODEL_PROPOSED]
)
def test_context_and_liquidity_reject_unreviewed_sources(
    source: BtmmEvidenceSource,
) -> None:
    with pytest.raises(ValidationError):
        _evidence(Timeframe.M15, context_source=source)
    with pytest.raises(ValidationError):
        _evidence(Timeframe.M15, liquidity_source=source)


@pytest.mark.parametrize(
    "source",
    [BtmmEvidenceSource.EXPERT_LABELLED, BtmmEvidenceSource.HYBRID_REVIEWED],
)
def test_volume_accepts_only_the_two_strictest_sources(
    source: BtmmEvidenceSource,
) -> None:
    _evidence(Timeframe.M15, volume_source=source)


@pytest.mark.parametrize(
    "source",
    [
        BtmmEvidenceSource.RULE_BASED_REVIEWED,
        BtmmEvidenceSource.RULE_BASED,
        BtmmEvidenceSource.MODEL_PROPOSED,
    ],
)
def test_volume_rejects_rule_based_review(source: BtmmEvidenceSource) -> None:
    """Volume is stricter than context and liquidity: RULE_BASED_REVIEWED is
    accepted for those and refused here, so a rule engine cannot supply it."""
    with pytest.raises(ValidationError):
        _evidence(Timeframe.M15, volume_source=source)


# --------------------------------------------------------------------------
# Matching evidence to a setup
# --------------------------------------------------------------------------


def test_evidence_for_an_unknown_poi_is_rejected_outright() -> None:
    """Evidence is not silently ignored when it addresses a POI that was not
    supplied -- the analyzer refuses the whole call."""
    stray = _evidence(Timeframe.M15, poi_record_id=_OTHER_POI_ID)
    with pytest.raises(MissingSourcePoiRecordError):
        _run(Timeframe.M15, (stray,))


def test_duplicate_evidence_for_one_poi_is_rejected() -> None:
    """At most one reviewed snapshot per POI per call; the analyzer does not
    pick a winner, it refuses."""
    first = _evidence(Timeframe.M15, volume=BtmmVolumePillarStatus.FAILS)
    second = _evidence(Timeframe.M15)
    with pytest.raises(InputPrefixMismatchError):
        _run(Timeframe.M15, (first, second))


def test_evidence_symbol_must_match_its_poi() -> None:
    evidence = _evidence(Timeframe.M15).model_copy(
        update={"symbol": InternalSymbol.EURUSD}
    )
    with pytest.raises((InputPrefixMismatchError, MixedSymbolAnalysisError)):
        _run(Timeframe.M15, (evidence,))


def test_evidence_timeframe_must_match_its_poi_source_timeframe() -> None:
    """A reviewed snapshot carries the timeframe it was reviewed on, and it has
    to agree with the POI it addresses."""
    evidence = _evidence(Timeframe.M5)  # POI below is on M15
    with pytest.raises(InputPrefixMismatchError):
        _run(Timeframe.M15, (evidence,))


def test_evidence_statuses_are_copied_onto_the_current_state() -> None:
    state = _state(_run(Timeframe.M15, (_evidence(Timeframe.M15),)))
    assert state.market_direction_status is BtmmContextAlignmentStatus.ALIGNED
    assert state.analytical_framework_status is BtmmContextAlignmentStatus.ALIGNED
    assert state.session_status is BtmmSessionStatus.ACTIVE
    assert state.volume_pillar_status is BtmmVolumePillarStatus.SUPPORTS
    assert state.liquidity_evidence_status is BtmmLiquidityEvidenceStatus.PRESENT


def test_a_weak_reaction_never_reaches_the_evidence_gates() -> None:
    """The market-data half runs first: if the reaction is too weak the setup
    dies before evidence is ever consulted, with or without it."""
    without = _state(_run(Timeframe.M15, (), strong_reaction=False))
    with_evidence = _state(
        _run(Timeframe.M15, (_evidence(Timeframe.M15),), strong_reaction=False)
    )
    assert without.primary_state is BtmmLifecycleStatus.BTMM_CANCELLED
    assert with_evidence.primary_state is BtmmLifecycleStatus.BTMM_CANCELLED
    assert without.cancellation_reason == with_evidence.cancellation_reason
    assert without.cancellation_reason is not (
        BtmmCancellationReason.NO_LIQUIDITY_EVIDENCE
    )
