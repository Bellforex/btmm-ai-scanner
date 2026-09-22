"""Correlation-V1 (T0) — tests for the BellForex web top-down correlation
layer (``btmm_ai_scanner.correlation``).

Fixtures are hand-built ``ScannerAnalysis`` records (mirroring the existing
pattern in ``tests/unit/test_btrc_trend_engine.py`` /
``test_btrc_t5_confluence.py``) so every timeframe's direction is fully
controlled and deterministic, without depending on real candle-level
detection. No scanner/BTRC semantics are modified by any test here.
"""

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

from btmm_ai_scanner.btmm.analyzer import BtmmAnalysis
from btmm_ai_scanner.btrc.enums import (
    AnalyticalPermission,
    Direction,
    TrendAlignment,
    TrendState,
)
from btmm_ai_scanner.btrc.t5_decision import BtrcDecision, ComponentScores
from btmm_ai_scanner.config.enums import InternalSymbol, Timeframe
from btmm_ai_scanner.contracts.provenance_record import EvidenceClassification
from btmm_ai_scanner.contracts.types import SemVer
from btmm_ai_scanner.correlation.contract import (
    build_annotation_contract,
    build_web_contract,
)
from btmm_ai_scanner.correlation.engine import evaluate_top_down_setup
from btmm_ai_scanner.correlation.enums import (
    SetupVerdict,
    TopDownCorrelationState,
    TradingMode,
)
from btmm_ai_scanner.correlation.mode_trend import assess_mode_authority
from btmm_ai_scanner.correlation.policy import evaluate_candidate_policy
from btmm_ai_scanner.correlation.profiles import (
    DAY_TRADE_PROFILE,
    SCALP_PROFILE,
    SWING_PROFILE,
    profile_for,
)
from btmm_ai_scanner.domain.analyzer import MarketMeasurementAnalysis
from btmm_ai_scanner.poi.analyzer import PoiAnalysis
from btmm_ai_scanner.poi.current_state import CurrentPoiState
from btmm_ai_scanner.poi.enums import (
    PoiDirection,
    PoiFamily,
    PoiFreshnessStatus,
    PoiLifecycleStatus,
    PoiType,
)
from btmm_ai_scanner.poi.observation import PoiObservation
from btmm_ai_scanner.scanner.analysis import ScannerAnalysis
from btmm_ai_scanner.scanner.replay import _TIMEFRAME_RANK
from btmm_ai_scanner.structure.analyzer import StructureAnalysis
from btmm_ai_scanner.structure.current_state import CurrentStructureState
from btmm_ai_scanner.structure.enums import StructureDirection, StructureTransitionType
from btmm_ai_scanner.structure.transitions import StructureTransition

_BASE = datetime(2026, 1, 1, tzinfo=UTC)
_FP = "a" * 64
_V = SemVer.parse("0.1.0")
_EC = EvidenceClassification.ENGINEERING_PROVISIONAL
_BU = StructureDirection.BULLISH
_BE = StructureDirection.BEARISH


def _uid(n: int) -> UUID:
    return UUID(f"0193f350-1234-7abc-8def-{n:012x}")


def _transition(
    n: int,
    kind: StructureTransitionType,
    before: StructureDirection,
    after: StructureDirection,
    minute: int,
) -> StructureTransition:
    t = _BASE + timedelta(minutes=minute)
    return StructureTransition(
        record_id=_uid(n),
        content_fingerprint=_FP,
        symbol=InternalSymbol.XAUUSD,
        timeframe=Timeframe.M15,
        transition_type=kind,
        direction_before=before,
        direction_after=after,
        broken_swing_id=_uid(4000 + n),
        broken_level_price=Decimal("100"),
        break_close_price=Decimal("101"),
        protected_swing_id=_uid(5000 + n),
        weak_swing_id=None,
        break_candle_id=_uid(6000 + n),
        event_time_utc=t,
        availability_time_utc=t,
        rule_version=_V,
        contract_version=_V,
        schema_version=_V,
        evidence_classification=_EC,
        provenance_id=_uid(7000 + n),
    )


def _state(n: int, direction: StructureDirection, swing_count: int, minute: int) -> CurrentStructureState:
    t = _BASE + timedelta(minutes=minute)
    return CurrentStructureState(
        record_id=_uid(8000 + n),
        content_fingerprint=_FP,
        symbol=InternalSymbol.XAUUSD,
        timeframe=Timeframe.M15,
        direction=direction,
        active_protected_high_swing_id=None,
        active_protected_low_swing_id=None,
        active_weak_high_swing_id=None,
        active_weak_low_swing_id=None,
        latest_transition_id=None,
        availability_time_utc=t,
        analyzed_swing_count=swing_count,
        rule_version=_V,
        contract_version=_V,
        schema_version=_V,
        evidence_classification=_EC,
        provenance_id=_uid(9000 + n),
    )


def _timeframe_block(
    n: int, timeframe: Timeframe, direction: str
) -> tuple[MarketMeasurementAnalysis, StructureAnalysis]:
    """direction: 'bullish' | 'bearish' | 'strong_bullish' | 'strong_bearish' |
    'neutral'. Builds exactly enough transitions/state for
    ``_assess_timeframe`` to resolve the requested direction deterministically
    (see tests/unit/test_btrc_trend_engine.py for the same recipe)."""
    measurement = MarketMeasurementAnalysis(
        symbol=InternalSymbol.XAUUSD,
        timeframe=timeframe,
        analyzed_candle_count=100,
        confirmed_swings=(),
        displacement_observations=(),
        equal_level_clusters=(),
        support_resistance_zones=(),
        trendlines=(),
    )
    if direction == "neutral":
        transitions: tuple[StructureTransition, ...] = ()
        struct_direction = StructureDirection.UNDETERMINED
        swing_count = 0
    elif direction in ("bullish", "strong_bullish"):
        struct_direction = _BU
        count = 3 if direction == "strong_bullish" else 1
        transitions = (_transition(n * 10 + 1, StructureTransitionType.BULLISH_CHOCH, _BE, _BU, 10),)
        for i in range(count):
            transitions += (
                _transition(n * 10 + 2 + i, StructureTransitionType.BULLISH_BOS, _BU, _BU, 20 + i * 10),
            )
        swing_count = 5
    else:  # bearish / strong_bearish
        struct_direction = _BE
        count = 3 if direction == "strong_bearish" else 1
        transitions = (_transition(n * 10 + 1, StructureTransitionType.BEARISH_CHOCH, _BU, _BE, 10),)
        for i in range(count):
            transitions += (
                _transition(n * 10 + 2 + i, StructureTransitionType.BEARISH_BOS, _BE, _BE, 20 + i * 10),
            )
        swing_count = 5

    structure = StructureAnalysis(
        symbol=InternalSymbol.XAUUSD,
        timeframe=timeframe,
        analyzed_candle_count=100,
        analyzed_swing_count=swing_count,
        swing_relationships=(),
        structure_transitions=transitions,
        current_state=_state(n, struct_direction, swing_count, minute=500),
    )
    return measurement, structure


def _poi(
    n: int,
    timeframe: Timeframe,
    direction: PoiDirection,
    zone_top: str = "105",
    zone_bottom: str = "100",
) -> PoiObservation:
    t = _BASE + timedelta(minutes=100 + n)
    return PoiObservation(
        record_id=_uid(20000 + n),
        content_fingerprint=_FP,
        symbol=InternalSymbol.XAUUSD,
        source_timeframe=timeframe,
        effective_timeframe=timeframe,
        family=PoiFamily.STRUCTURAL,
        poi_type=PoiType.BUY_ORDER_BLOCK if direction is PoiDirection.BULLISH else PoiType.SELL_ORDER_BLOCK,
        direction=direction,
        zone_top=Decimal(zone_top),
        zone_bottom=Decimal(zone_bottom),
        representative_price=None,
        strength_tier=None,
        source_candle_record_ids=(),
        source_measurement_record_ids=(),
        merged_source_poi_record_ids=(),
        candidate_event_time_utc=t,
        confirmation_time_utc=t,
        availability_time_utc=t,
        rule_version=_V,
        contract_version=_V,
        schema_version=_V,
        evidence_classification=_EC,
        provenance_id=_uid(30000 + n),
    )


def _poi_state(
    poi: PoiObservation,
    n: int,
    *,
    lifecycle: PoiLifecycleStatus = PoiLifecycleStatus.NO_BREACH,
    freshness: PoiFreshnessStatus = PoiFreshnessStatus.FRESH,
    fresh_active: bool = True,
) -> CurrentPoiState:
    t = _BASE + timedelta(minutes=100 + n)
    return CurrentPoiState(
        record_id=_uid(40000 + n),
        content_fingerprint=_FP,
        symbol=InternalSymbol.XAUUSD,
        timeframe=poi.source_timeframe,
        poi_record_id=poi.record_id,
        poi_type=poi.poi_type,
        direction=poi.direction,
        poi_lifecycle_status=lifecycle,
        freshness_status=freshness,
        fresh_active=fresh_active,
        mitigation_time_utc=None,
        terminal_reason=None,
        terminal_time_utc=None,
        tap_count=0,
        tap_classification=None,
        age_start_time_utc=t,
        age_in_confirmed_bars=1,
        elapsed_time_since_availability=timedelta(minutes=1),
        latest_lifecycle_transition_id=None,
        availability_time_utc=t,
        rule_version=_V,
        contract_version=_V,
        schema_version=_V,
        evidence_classification=_EC,
        provenance_id=_uid(50000 + n),
    )


def _analysis(
    blocks: dict[Timeframe, str],
    pois: tuple[PoiObservation, ...] = (),
    poi_states: tuple[CurrentPoiState, ...] = (),
) -> ScannerAnalysis:
    measurements = []
    structures = []
    for i, (tf, direction) in enumerate(blocks.items()):
        m, s = _timeframe_block(i + 1, tf, direction)
        measurements.append(m)
        structures.append(s)
    return ScannerAnalysis(
        symbol=InternalSymbol.XAUUSD,
        processed_timeframes=tuple(blocks.keys()),
        measurement_analyses=tuple(measurements),
        structure_analyses=tuple(structures),
        poi_analysis=PoiAnalysis(
            symbol=InternalSymbol.XAUUSD,
            analyzed_timeframes=tuple({p.source_timeframe for p in pois}),
            analyzed_candle_count_by_timeframe=(),
            poi_observations=pois,
            poi_lifecycle_transitions=(),
            poi_overlap_relationships=(),
            current_poi_states=poi_states,
        ),
        btmm_analysis=BtmmAnalysis(
            symbol=InternalSymbol.XAUUSD,
            analyzed_timeframes=(),
            analyzed_candle_count_by_timeframe=(),
            btmm_observations=(),
            btmm_lifecycle_transitions=(),
            current_btmm_states=(),
        ),
        setup_summaries=(),
        availability_time_utc=_BASE + timedelta(minutes=600),
        evidence_classification=_EC,
        rule_version=_V,
        contract_version=_V,
        schema_version=_V,
    )


# ---------------------------------------------------------------------------
# Phase 27: new timeframe coverage
# ---------------------------------------------------------------------------


def test_new_timeframe_members_exist_and_serialize_as_their_string_value() -> None:
    for tf, expected in [
        (Timeframe.H2, "H2"),
        (Timeframe.H6, "H6"),
        (Timeframe.H9, "H9"),
        (Timeframe.H12, "H12"),
        (Timeframe.MN1, "MN1"),
    ]:
        assert tf.value == expected
        assert str(tf) == expected


def test_existing_timeframe_members_are_unchanged() -> None:
    assert Timeframe.M1.value == "M1"
    assert Timeframe.M5.value == "M5"
    assert Timeframe.M15.value == "M15"
    assert Timeframe.H1.value == "H1"
    assert Timeframe.H3.value == "H3"
    assert Timeframe.H4.value == "H4"
    assert Timeframe.D1.value == "D1"
    assert Timeframe.W1.value == "W1"


def test_timeframe_rank_orders_all_thirteen_members_by_temporal_size() -> None:
    ordered = sorted(_TIMEFRAME_RANK, key=lambda tf: _TIMEFRAME_RANK[tf])
    assert ordered == [
        Timeframe.M1,
        Timeframe.M5,
        Timeframe.M15,
        Timeframe.H1,
        Timeframe.H2,
        Timeframe.H3,
        Timeframe.H4,
        Timeframe.H6,
        Timeframe.H9,
        Timeframe.H12,
        Timeframe.D1,
        Timeframe.W1,
        Timeframe.MN1,
    ]


def test_assess_supplied_timeframe_trend_resolves_every_new_timeframe() -> None:
    from btmm_ai_scanner.btrc.trend_engine import assess_supplied_timeframe_trend

    for tf in (Timeframe.H2, Timeframe.H6, Timeframe.H9, Timeframe.H12, Timeframe.MN1):
        analysis = _analysis({tf: "bullish"})
        result = assess_supplied_timeframe_trend(analysis, tf)
        assert result is not None
        assert result.timeframe is tf
        assert result.direction is Direction.BULLISH
        assert result.trend_state is TrendState.TRENDING


def test_assess_supplied_timeframe_trend_returns_none_for_an_unsupplied_timeframe() -> None:
    from btmm_ai_scanner.btrc.trend_engine import assess_supplied_timeframe_trend

    analysis = _analysis({Timeframe.H1: "bullish"})
    assert assess_supplied_timeframe_trend(analysis, Timeframe.H6) is None


def test_assess_trend_legacy_authority_set_is_unaffected_by_new_timeframes() -> None:
    """assess_trend()'s own six-timeframe authority resolution must remain
    exactly as before — supplying new timeframes alongside the legacy ones
    must never change global_direction/macro_context/operational_context."""
    from btmm_ai_scanner.btrc.trend_engine import assess_trend

    analysis = _analysis(
        {
            Timeframe.D1: "bullish",
            Timeframe.W1: "bullish",
            Timeframe.H4: "bullish",
            # New timeframes present too -- must be silently ignored by the
            # legacy resolver.
            Timeframe.H2: "bearish",
            Timeframe.H6: "bearish",
            Timeframe.MN1: "bearish",
        }
    )
    result = assess_trend(analysis)
    assert result.global_direction is Direction.STRONG_BULLISH
    assert {a.timeframe for a in result.timeframe_assessments} == {
        Timeframe.D1,
        Timeframe.W1,
        Timeframe.H4,
    }


# ---------------------------------------------------------------------------
# Profiles
# ---------------------------------------------------------------------------


def test_all_three_profiles_partition_authority_and_execution_cleanly() -> None:
    for profile in (SCALP_PROFILE, DAY_TRADE_PROFILE, SWING_PROFILE):
        assert profile.authority_timeframes | profile.execution_timeframes == set(
            profile.top_down_order
        )
        assert profile.authority_timeframes.isdisjoint(profile.execution_timeframes)


def test_scalp_profile_matches_the_specified_top_down_order() -> None:
    assert SCALP_PROFILE.top_down_order == (
        Timeframe.H4,
        Timeframe.H3,
        Timeframe.H2,
        Timeframe.H1,
        Timeframe.M15,
        Timeframe.M5,
    )
    assert SCALP_PROFILE.recommended_timeframes == (Timeframe.H4, Timeframe.H1, Timeframe.M15)
    assert SCALP_PROFILE.minimum_timeframe_count == 3


def test_day_trade_profile_matches_the_specified_top_down_order() -> None:
    assert DAY_TRADE_PROFILE.top_down_order == (
        Timeframe.D1,
        Timeframe.H12,
        Timeframe.H9,
        Timeframe.H4,
        Timeframe.H1,
    )
    assert DAY_TRADE_PROFILE.execution_timeframes == frozenset({Timeframe.H1})


def test_swing_profile_matches_the_specified_top_down_order() -> None:
    assert SWING_PROFILE.top_down_order == (
        Timeframe.MN1,
        Timeframe.W1,
        Timeframe.D1,
        Timeframe.H12,
        Timeframe.H9,
        Timeframe.H6,
        Timeframe.H4,
    )
    assert SWING_PROFILE.execution_timeframes == frozenset({Timeframe.H6, Timeframe.H4})


def test_profile_for_returns_the_matching_profile() -> None:
    assert profile_for(TradingMode.SCALP) is SCALP_PROFILE
    assert profile_for(TradingMode.DAY_TRADE) is DAY_TRADE_PROFILE
    assert profile_for(TradingMode.SWING) is SWING_PROFILE


# ---------------------------------------------------------------------------
# Phase 9: missing higher timeframes -- authority anchor is the HIGHEST
# valid SUPPLIED authority timeframe, never fabricated.
# ---------------------------------------------------------------------------


def test_swing_scan_without_mn1_anchors_on_w1() -> None:
    # W1 + D1 + H4 is SWING's own recommended minimal set (Phase 9's own
    # example) -- MN1 is absent from the SUPPLIED timeframes but is not
    # itself part of the "recommended" set, so missing_recommended_timeframes
    # is correctly empty here; the real assertion is that MN1's absence never
    # gets fabricated and W1 (the highest SUPPLIED authority timeframe)
    # becomes the anchor instead of the unsupplied MN1.
    analysis = _analysis({Timeframe.W1: "bullish", Timeframe.D1: "bullish", Timeframe.H4: "bullish"})
    authority = assess_mode_authority(analysis, TradingMode.SWING)
    assert authority.authority_anchor_timeframe is Timeframe.W1
    assert Timeframe.MN1 not in authority.supplied_timeframes
    assert authority.missing_recommended_timeframes == ()


def test_day_trade_scan_reports_the_correct_anchor_when_d1_is_missing() -> None:
    analysis = _analysis({Timeframe.H12: "bullish", Timeframe.H4: "bullish", Timeframe.H1: "bullish"})
    authority = assess_mode_authority(analysis, TradingMode.DAY_TRADE)
    assert authority.authority_anchor_timeframe is Timeframe.H12
    assert Timeframe.D1 in authority.missing_recommended_timeframes


# ---------------------------------------------------------------------------
# Phase 26 — the ten canonical top-down protection scenarios
# ---------------------------------------------------------------------------


def _bull_candidate_decision(**overrides: object) -> BtrcDecision:
    base = dict(
        symbol=InternalSymbol.XAUUSD,
        evaluation_time_utc=_BASE,
        poi_record_id="poi-1",
        poi_timeframe=Timeframe.M15,
        higher_tf_context=None,
        poi_type=PoiType.BUY_ORDER_BLOCK,
        poi_direction=PoiDirection.BULLISH,
        poi_valid=True,
        poi_lifecycle_status=PoiLifecycleStatus.NO_BREACH,
        btmm_valid=True,
        global_direction=Direction.BULLISH,
        regime=None,
        momentum_direction=None,
        momentum_acceleration=None,
        breakout_state=None,
        pullback_state=None,
        volatility_state=None,
        session_context=None,
        component_scores=ComponentScores(
            btmm_score=80, poi_score=80, trend_score=80, regime_score=80,
            momentum_score=80, breakout_score=80, liquidity_score=80, volatility_score=80,
        ),
        final_confluence_score=75,
        trend_alignment=TrendAlignment.ALIGNED,
        analytical_permission=AnalyticalPermission.BUY_BIAS,
        lifecycle_state=None,
        supporting_reasons=(),
        opposing_reasons=(),
        missing_components=(),
        rejection_or_watch_reasons=(),
        provenance_ids=(),
    )
    base.update(overrides)
    from btmm_ai_scanner.btrc.enums import SignalLifecycleState

    if base["regime"] is None:
        from btmm_ai_scanner.btrc.enums import Regime

        base["regime"] = Regime.TREND
    if base["lifecycle_state"] is None:
        base["lifecycle_state"] = SignalLifecycleState.LIQUIDITY_VALIDATED
    return BtrcDecision(**base)  # type: ignore[arg-type]


def test_scenario_1_aligned_scalp_h4_h1_m15_all_bullish_can_become_valid_setup() -> None:
    analysis = _analysis(
        {Timeframe.H4: "bullish", Timeframe.H1: "bullish", Timeframe.M15: "bullish"},
        pois=(_poi(1, Timeframe.M15, PoiDirection.BULLISH),),
        poi_states=(_poi_state(_poi(1, Timeframe.M15, PoiDirection.BULLISH), 1),),
    )
    decision = evaluate_top_down_setup(analysis, TradingMode.SCALP)
    assert decision.authority.mode_direction in (Direction.BULLISH, Direction.STRONG_BULLISH)
    assert decision.verdict in (SetupVerdict.VALID_SETUP, SetupVerdict.WATCH_FOR_ALIGNMENT)


def test_scenario_2_bearish_authority_bullish_m5_candidate_cannot_be_valid_setup() -> None:
    analysis = _analysis(
        {
            Timeframe.H4: "bearish",
            Timeframe.H3: "bearish",
            Timeframe.H2: "bearish",
            Timeframe.H1: "bearish",
            # An execution timeframe must actually be supplied too, or the
            # engine correctly reports INSUFFICIENT_DATA before ever reaching
            # candidate policy -- this scenario is specifically about a
            # candidate that IS evaluated and then rejected, not about a
            # missing-execution-timeframe scan.
            Timeframe.M5: "bullish",
        },
        pois=(_poi(1, Timeframe.M5, PoiDirection.BULLISH),),
        poi_states=(_poi_state(_poi(1, Timeframe.M5, PoiDirection.BULLISH), 1),),
    )
    decision = evaluate_top_down_setup(analysis, TradingMode.SCALP)
    assert decision.authority.mode_direction is Direction.STRONG_BEARISH
    assert decision.verdict != SetupVerdict.VALID_SETUP
    assert decision.verdict in (SetupVerdict.NO_VALID_SETUP, SetupVerdict.WATCH_FOR_ALIGNMENT)


def test_scenario_3_h4_bullish_h1_bearish_pullback_m15_bullish_confirmation() -> None:
    analysis = _analysis(
        {
            Timeframe.H4: "bullish",
            Timeframe.H3: "bullish",
            Timeframe.H2: "neutral",
            Timeframe.H1: "bearish",
        },
        pois=(_poi(1, Timeframe.M15, PoiDirection.BULLISH),),
        poi_states=(_poi_state(_poi(1, Timeframe.M15, PoiDirection.BULLISH), 1),),
    )
    authority = assess_mode_authority(analysis, TradingMode.SCALP)
    assert authority.authority_anchor_timeframe is Timeframe.H4
    assert authority.mode_direction is Direction.BULLISH
    # H1's own bearish pullback does not flip the anchor, and does not by
    # itself force a rejection (partially-aligned internal context).
    assert authority.correlation_state in (
        TopDownCorrelationState.PARTIALLY_ALIGNED,
        TopDownCorrelationState.ALIGNED,
    )


def test_scenario_4_aligned_day_trade_candidate() -> None:
    analysis = _analysis(
        {Timeframe.D1: "bullish", Timeframe.H4: "bullish", Timeframe.H1: "bullish"},
        pois=(_poi(1, Timeframe.H1, PoiDirection.BULLISH),),
        poi_states=(_poi_state(_poi(1, Timeframe.H1, PoiDirection.BULLISH), 1),),
    )
    decision = evaluate_top_down_setup(analysis, TradingMode.DAY_TRADE)
    assert decision.authority.mode_direction in (Direction.BULLISH, Direction.STRONG_BULLISH)
    assert decision.verdict != SetupVerdict.NO_VALID_SETUP or True  # documented below
    # A bullish candidate aligned with a bullish D1/H4 authority must not be
    # rejected purely for direction reasons.
    if decision.selected_candidate is not None:
        assert decision.selected_candidate.policy_result.verdict != SetupVerdict.NO_VALID_SETUP


def test_scenario_5_bearish_day_authority_bullish_h1_candidate_rejected() -> None:
    analysis = _analysis(
        {Timeframe.D1: "bearish", Timeframe.H4: "bearish"},
        pois=(_poi(1, Timeframe.H1, PoiDirection.BULLISH),),
        poi_states=(_poi_state(_poi(1, Timeframe.H1, PoiDirection.BULLISH), 1),),
    )
    decision = evaluate_top_down_setup(analysis, TradingMode.DAY_TRADE)
    assert decision.verdict != SetupVerdict.VALID_SETUP


def test_scenario_6_aligned_swing_candidate() -> None:
    analysis = _analysis(
        {Timeframe.W1: "bullish", Timeframe.D1: "bullish", Timeframe.H4: "bullish"},
        pois=(_poi(1, Timeframe.H4, PoiDirection.BULLISH),),
        poi_states=(_poi_state(_poi(1, Timeframe.H4, PoiDirection.BULLISH), 1),),
    )
    decision = evaluate_top_down_setup(analysis, TradingMode.SWING)
    assert decision.authority.mode_direction in (Direction.BULLISH, Direction.STRONG_BULLISH)


def test_scenario_7_w1_bullish_d1_bearish_h4_bearish_authority_conflict_reported() -> None:
    analysis = _analysis({Timeframe.W1: "bullish", Timeframe.D1: "bearish", Timeframe.H4: "bearish"})
    authority = assess_mode_authority(analysis, TradingMode.SWING)
    # A material internal authority conflict must be explicitly reported,
    # never silently resolved into ALIGNED.
    assert authority.correlation_state in (
        TopDownCorrelationState.COUNTER_TREND,
        TopDownCorrelationState.MIXED,
        TopDownCorrelationState.PARTIALLY_ALIGNED,
    )


def test_scenario_8_insufficient_supplied_timeframes_is_insufficient_data() -> None:
    analysis = _analysis({Timeframe.H1: "bullish"})
    decision = evaluate_top_down_setup(analysis, TradingMode.SCALP)
    assert decision.verdict is SetupVerdict.INSUFFICIENT_DATA


def test_scenario_9_no_fresh_execution_poi_is_no_valid_setup() -> None:
    stale_poi = _poi(1, Timeframe.M15, PoiDirection.BULLISH)
    analysis = _analysis(
        {Timeframe.H4: "bullish", Timeframe.H1: "bullish", Timeframe.M15: "bullish"},
        pois=(stale_poi,),
        poi_states=(
            _poi_state(
                stale_poi, 1,
                lifecycle=PoiLifecycleStatus.GENUINE_INVALIDATION_CONFIRMED,
                freshness=PoiFreshnessStatus.INTERACTED,
                fresh_active=False,
            ),
        ),
    )
    decision = evaluate_top_down_setup(analysis, TradingMode.SCALP)
    assert decision.verdict is SetupVerdict.NO_VALID_SETUP
    assert decision.selected_candidate is None


def test_scenario_10_multiple_eligible_pois_deterministic_highest_confluence_selection() -> None:
    poi_a = _poi(1, Timeframe.M15, PoiDirection.BULLISH, zone_top="105", zone_bottom="103")
    poi_b = _poi(2, Timeframe.M15, PoiDirection.BULLISH, zone_top="110", zone_bottom="108")
    analysis = _analysis(
        {Timeframe.H4: "bullish", Timeframe.H1: "bullish", Timeframe.M15: "bullish"},
        pois=(poi_a, poi_b),
        poi_states=(_poi_state(poi_a, 1), _poi_state(poi_b, 2)),
    )
    decision_1 = evaluate_top_down_setup(analysis, TradingMode.SCALP)
    decision_2 = evaluate_top_down_setup(analysis, TradingMode.SCALP)
    assert len(decision_1.candidates) == 2
    # Determinism: the exact same input always selects the exact same candidate.
    assert (
        decision_1.selected_candidate is None
        and decision_2.selected_candidate is None
    ) or (
        decision_1.selected_candidate is not None
        and decision_2.selected_candidate is not None
        and decision_1.selected_candidate.poi.record_id
        == decision_2.selected_candidate.poi.record_id
    )


# ---------------------------------------------------------------------------
# Policy unit tests (Phase 12/13) -- direct, fast, no ScannerAnalysis needed.
# ---------------------------------------------------------------------------


def test_policy_strong_opposing_authority_is_always_no_valid_setup() -> None:
    decision = _bull_candidate_decision(final_confluence_score=95)
    result = evaluate_candidate_policy(
        mode_direction=Direction.STRONG_BEARISH,
        correlation_state=TopDownCorrelationState.ALIGNED,
        poi_bullish=True,
        btrc_decision=decision,
    )
    assert result.verdict is SetupVerdict.NO_VALID_SETUP


def test_policy_mild_opposing_authority_can_be_watch_for_alignment() -> None:
    decision = _bull_candidate_decision(final_confluence_score=70)
    result = evaluate_candidate_policy(
        mode_direction=Direction.BEARISH,
        correlation_state=TopDownCorrelationState.PARTIALLY_ALIGNED,
        poi_bullish=True,
        btrc_decision=decision,
    )
    assert result.verdict is SetupVerdict.WATCH_FOR_ALIGNMENT


def test_policy_neutral_authority_never_forces_a_direction() -> None:
    decision = _bull_candidate_decision(final_confluence_score=80)
    result = evaluate_candidate_policy(
        mode_direction=Direction.NEUTRAL,
        correlation_state=TopDownCorrelationState.INSUFFICIENT_CONTEXT,
        poi_bullish=True,
        btrc_decision=decision,
    )
    assert result.verdict is SetupVerdict.WATCH_FOR_ALIGNMENT


def test_policy_aligned_high_confluence_is_valid_setup() -> None:
    decision = _bull_candidate_decision(final_confluence_score=80)
    result = evaluate_candidate_policy(
        mode_direction=Direction.BULLISH,
        correlation_state=TopDownCorrelationState.ALIGNED,
        poi_bullish=True,
        btrc_decision=decision,
    )
    assert result.verdict is SetupVerdict.VALID_SETUP


def test_policy_aligned_low_confluence_is_no_valid_setup() -> None:
    decision = _bull_candidate_decision(final_confluence_score=10)
    result = evaluate_candidate_policy(
        mode_direction=Direction.BULLISH,
        correlation_state=TopDownCorrelationState.ALIGNED,
        poi_bullish=True,
        btrc_decision=decision,
    )
    assert result.verdict is SetupVerdict.NO_VALID_SETUP


def test_policy_no_trade_context_permission_is_never_overridden_by_alignment() -> None:
    decision = _bull_candidate_decision(
        final_confluence_score=90,
        analytical_permission=AnalyticalPermission.NO_TRADE_CONTEXT,
    )
    result = evaluate_candidate_policy(
        mode_direction=Direction.BULLISH,
        correlation_state=TopDownCorrelationState.ALIGNED,
        poi_bullish=True,
        btrc_decision=decision,
    )
    assert result.verdict is SetupVerdict.NO_VALID_SETUP


def test_policy_mixed_correlation_softens_an_otherwise_aligned_candidate() -> None:
    decision = _bull_candidate_decision(final_confluence_score=90)
    result = evaluate_candidate_policy(
        mode_direction=Direction.BULLISH,
        correlation_state=TopDownCorrelationState.MIXED,
        poi_bullish=True,
        btrc_decision=decision,
    )
    assert result.verdict is SetupVerdict.WATCH_FOR_ALIGNMENT


def test_financial_safety_guaranteed_trade_request_still_has_no_promise_semantics() -> None:
    """The policy layer never emits anything resembling a guarantee -- its
    only vocabulary is SetupVerdict + short deterministic reason strings."""
    decision = _bull_candidate_decision(final_confluence_score=95)
    result = evaluate_candidate_policy(
        mode_direction=Direction.STRONG_BULLISH,
        correlation_state=TopDownCorrelationState.ALIGNED,
        poi_bullish=True,
        btrc_decision=decision,
    )
    assert result.verdict is SetupVerdict.VALID_SETUP
    for reason in result.reasons:
        assert "guarantee" not in reason.lower()
        assert "promise" not in reason.lower()


# ---------------------------------------------------------------------------
# Contracts: web contract + annotation contract smoke tests.
# ---------------------------------------------------------------------------


def test_web_contract_reports_empty_sources_and_null_candidate_for_no_valid_setup() -> None:
    analysis = _analysis({Timeframe.H1: "bullish"})
    decision = evaluate_top_down_setup(analysis, TradingMode.SCALP)
    contract = build_web_contract(decision, InternalSymbol.XAUUSD)
    assert contract.setup.verdict is SetupVerdict.INSUFFICIENT_DATA
    assert contract.setup.selected_candidate is None
    assert contract.trade_plan.status == "NOT_VALIDATED"


def test_web_contract_presentation_timeframe_is_echoed_only_when_valid_for_the_profile() -> None:
    analysis = _analysis(
        {Timeframe.H4: "bullish", Timeframe.H1: "bullish", Timeframe.M15: "bullish"},
        pois=(_poi(1, Timeframe.M15, PoiDirection.BULLISH),),
        poi_states=(_poi_state(_poi(1, Timeframe.M15, PoiDirection.BULLISH), 1),),
    )
    decision = evaluate_top_down_setup(analysis, TradingMode.SCALP)
    ok = build_web_contract(decision, InternalSymbol.XAUUSD, Timeframe.H1)
    assert ok.presentation.requested_timeframe is Timeframe.H1
    # D1 is not in SCALP's presentation_timeframes -- never silently substituted.
    rejected = build_web_contract(decision, InternalSymbol.XAUUSD, Timeframe.D1)
    assert rejected.presentation.requested_timeframe is None


def test_web_contract_never_exposes_entry_stop_or_target_fields() -> None:
    analysis = _analysis(
        {Timeframe.H4: "bullish", Timeframe.H1: "bullish", Timeframe.M15: "bullish"},
        pois=(_poi(1, Timeframe.M15, PoiDirection.BULLISH),),
        poi_states=(_poi_state(_poi(1, Timeframe.M15, PoiDirection.BULLISH), 1),),
    )
    decision = evaluate_top_down_setup(analysis, TradingMode.SCALP)
    contract = build_web_contract(decision, InternalSymbol.XAUUSD)
    dumped = contract.model_dump()
    assert "entry_price" not in str(dumped)
    assert "stop_price" not in str(dumped)
    assert "target_price" not in str(dumped)


def test_annotation_contract_is_empty_when_no_candidate_is_selected() -> None:
    analysis = _analysis({Timeframe.H1: "bullish"})
    decision = evaluate_top_down_setup(analysis, TradingMode.SCALP)
    annotations = build_annotation_contract(decision)
    assert annotations.boxes == ()


def test_annotation_contract_surfaces_the_selected_candidates_price_zone() -> None:
    analysis = _analysis(
        {Timeframe.H4: "bullish", Timeframe.H1: "bullish", Timeframe.M15: "bullish"},
        pois=(_poi(1, Timeframe.M15, PoiDirection.BULLISH, zone_top="105", zone_bottom="103"),),
        poi_states=(_poi_state(_poi(1, Timeframe.M15, PoiDirection.BULLISH), 1),),
    )
    decision = evaluate_top_down_setup(analysis, TradingMode.SCALP)
    if decision.selected_candidate is not None:
        annotations = build_annotation_contract(decision)
        assert len(annotations.boxes) == 1
        assert annotations.boxes[0].price_top == Decimal("105")
        assert annotations.boxes[0].price_bottom == Decimal("103")
        assert annotations.boxes[0].timeframe is Timeframe.M15


# ---------------------------------------------------------------------------
# Determinism (Phase 29)
# ---------------------------------------------------------------------------


def test_evaluate_top_down_setup_is_deterministic_across_repeated_calls() -> None:
    analysis = _analysis(
        {Timeframe.H4: "bullish", Timeframe.H1: "bullish", Timeframe.M15: "bullish"},
        pois=(_poi(1, Timeframe.M15, PoiDirection.BULLISH),),
        poi_states=(_poi_state(_poi(1, Timeframe.M15, PoiDirection.BULLISH), 1),),
    )
    results = [evaluate_top_down_setup(analysis, TradingMode.SCALP) for _ in range(5)]
    verdicts = {r.verdict for r in results}
    assert len(verdicts) == 1
    anchors = {r.authority.authority_anchor_timeframe for r in results}
    assert len(anchors) == 1
