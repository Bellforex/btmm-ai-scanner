"""BTRC-T3 momentum / breakout / pullback engine tests.

Layer 1: direct, precise tests of each per-timeframe sub-engine with hand-built
scanner records. Layer 2: integration over a real ``ScannerAnalysis`` for
determinism, prefix causality, and incremental-vs-batch equivalence.
"""

import random
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

from btmm_ai_scanner.btmm.configuration import BtmmConfiguration
from btmm_ai_scanner.btrc import (
    BreakoutState,
    MomentumAcceleration,
    MomentumDirection,
    PullbackState,
    assess_breakout,
    assess_momentum,
    assess_pullback,
)
from btmm_ai_scanner.btrc.t3_configuration import MomentumBreakoutPullbackConfiguration
from btmm_ai_scanner.btrc.t3_engine import (
    _assess_timeframe_breakout,
    _assess_timeframe_momentum,
    _assess_timeframe_pullback,
)
from btmm_ai_scanner.config.enums import InternalSymbol, Timeframe
from btmm_ai_scanner.contracts.normalized_candle import NormalizedCandle
from btmm_ai_scanner.contracts.provenance_record import EvidenceClassification
from btmm_ai_scanner.contracts.raw_candle import CandleCompleteness, CandleVolumeKind
from btmm_ai_scanner.contracts.types import SemVer
from btmm_ai_scanner.domain.configuration import MarketMeasurementConfiguration
from btmm_ai_scanner.domain.displacement import DisplacementObservation
from btmm_ai_scanner.domain.enums import (
    DisplacementClassification,
    DisplacementDirection,
    EqualLevelType,
    SwingType,
)
from btmm_ai_scanner.domain.equal_levels import EqualLevelCluster
from btmm_ai_scanner.domain.swings import ConfirmedSwing
from btmm_ai_scanner.historical_backtest.identity import (
    ContentAddressedIdentityProvider,
)
from btmm_ai_scanner.poi.configuration import PoiConfiguration
from btmm_ai_scanner.scanner.analysis import ScannerAnalysis
from btmm_ai_scanner.scanner.analyzer import scan_market
from btmm_ai_scanner.scanner.configuration import (
    ReplayConfiguration,
    ScannerConfiguration,
)
from btmm_ai_scanner.scanner.enums import SnapshotRetentionPolicy
from btmm_ai_scanner.scanner.replay import run_scanner_replay
from btmm_ai_scanner.scanner.timeframe_input import ScannerTimeframeInput
from btmm_ai_scanner.structure.configuration import StructureConfiguration
from btmm_ai_scanner.structure.current_state import CurrentStructureState
from btmm_ai_scanner.structure.enums import StructureDirection, StructureTransitionType
from btmm_ai_scanner.structure.transitions import StructureTransition

_BASE = datetime(2026, 1, 1, tzinfo=UTC)
_FP = "a" * 64
_V = SemVer.parse("0.1.0")
_EC = EvidenceClassification.ENGINEERING_PROVISIONAL
_CFG = MomentumBreakoutPullbackConfiguration()
_M15 = Timeframe.M15


def _uid(n: int) -> UUID:
    return UUID(f"0193f350-1234-7abc-8def-{n:012x}")


def _disp(
    n: int,
    direction: DisplacementDirection,
    ratio: str,
    classification: DisplacementClassification = DisplacementClassification.NORMAL,
) -> DisplacementObservation:
    t = _BASE + timedelta(minutes=n)
    return DisplacementObservation(
        record_id=_uid(n),
        content_fingerprint=_FP,
        symbol=InternalSymbol.XAUUSD,
        timeframe=_M15,
        candle_record_id=_uid(10000 + n),
        event_time_utc=t,
        availability_time_utc=t,
        total_range=Decimal("2.0"),
        range_speed_ratio=Decimal(ratio),
        direction=direction,
        classification=classification,
        rule_version=_V,
        contract_version=_V,
        schema_version=_V,
        evidence_classification=_EC,
        provenance_id=_uid(20000 + n),
    )


def _transition(
    n: int, ttype: StructureTransitionType, minute: int
) -> StructureTransition:
    t = _BASE + timedelta(minutes=minute)
    before = StructureDirection.BULLISH
    after = StructureDirection.BULLISH
    return StructureTransition(
        record_id=_uid(n),
        content_fingerprint=_FP,
        symbol=InternalSymbol.XAUUSD,
        timeframe=_M15,
        transition_type=ttype,
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


def _equal_level(n: int, minute: int) -> EqualLevelCluster:
    t = _BASE + timedelta(minutes=minute)
    return EqualLevelCluster(
        record_id=_uid(n),
        content_fingerprint=_FP,
        symbol=InternalSymbol.XAUUSD,
        timeframe=_M15,
        cluster_type=EqualLevelType.EQUAL_HIGH,
        component_swing_record_ids=(_uid(30000 + n),),
        cluster_spread=Decimal("0.1"),
        equality_tolerance=Decimal("0.2"),
        reference_atr=Decimal("1.0"),
        zone_bottom=Decimal("109.9"),
        zone_top=Decimal("110.1"),
        representative_price=Decimal("110"),
        confirmation_time_utc=t,
        availability_time_utc=t,
        rule_version=_V,
        contract_version=_V,
        schema_version=_V,
        evidence_classification=_EC,
        provenance_id=_uid(40000 + n),
    )


def _swing(n: int, swing_type: SwingType, price: str, minute: int) -> ConfirmedSwing:
    t = _BASE + timedelta(minutes=minute)
    return ConfirmedSwing(
        record_id=_uid(n),
        content_fingerprint=_FP,
        symbol=InternalSymbol.XAUUSD,
        timeframe=_M15,
        swing_type=swing_type,
        pivot_price=Decimal(price),
        pivot_bar_index=minute,
        pivot_candle_record_ids=(_uid(1000 + n),),
        pivot_start_time_utc=t,
        pivot_end_time_utc=t,
        local_confirmation_time_utc=t,
        meaningful_confirmation_time_utc=t,
        confirmation_candle_id=_uid(2000 + n),
        pivot_reference_atr=Decimal("1"),
        pivot_tie_tolerance=Decimal("0.1"),
        reversal_threshold=Decimal("1"),
        reversal_excursion=Decimal("2"),
        availability_time_utc=t,
        rule_version=_V,
        contract_version=_V,
        schema_version=_V,
        evidence_classification=_EC,
        provenance_id=_uid(3000 + n),
    )


def _state(direction: StructureDirection) -> CurrentStructureState:
    return CurrentStructureState(
        record_id=_uid(8000),
        content_fingerprint=_FP,
        symbol=InternalSymbol.XAUUSD,
        timeframe=_M15,
        direction=direction,
        active_protected_high_swing_id=None,
        active_protected_low_swing_id=None,
        active_weak_high_swing_id=None,
        active_weak_low_swing_id=None,
        latest_transition_id=None,
        availability_time_utc=_BASE + timedelta(minutes=500),
        analyzed_swing_count=8,
        rule_version=_V,
        contract_version=_V,
        schema_version=_V,
        evidence_classification=_EC,
        provenance_id=_uid(9000),
    )


_BU = DisplacementDirection.BULLISH
_BE = DisplacementDirection.BEARISH
_NORMAL = DisplacementClassification.NORMAL
_FAST = DisplacementClassification.FAST
_VFAST = DisplacementClassification.VERY_FAST


# ---------------- momentum ----------------
def test_momentum_insufficient_is_neutral() -> None:
    m = _assess_timeframe_momentum(_M15, (), _CFG)
    assert m.direction is MomentumDirection.NEUTRAL
    assert m.acceleration is MomentumAcceleration.STEADY
    assert m.momentum_score == 0


def test_momentum_bullish() -> None:
    m = _assess_timeframe_momentum(
        _M15, (_disp(1, _BU, "1.2"), _disp(2, _BU, "1.3")), _CFG
    )
    assert m.direction is MomentumDirection.STRONG_BULLISH  # 2 consecutive same-dir


def test_momentum_bearish() -> None:
    m = _assess_timeframe_momentum(
        _M15, (_disp(1, _BE, "1.2"), _disp(2, _BE, "1.3")), _CFG
    )
    assert m.direction is MomentumDirection.STRONG_BEARISH


def test_momentum_single_normal_displacement_is_not_strong() -> None:
    m = _assess_timeframe_momentum(_M15, (_disp(1, _BU, "1.2", _NORMAL),), _CFG)
    assert m.direction is MomentumDirection.BULLISH  # not STRONG on one normal event


def test_momentum_single_very_fast_can_be_strong() -> None:
    m = _assess_timeframe_momentum(_M15, (_disp(1, _BU, "2.5", _VFAST),), _CFG)
    assert m.direction is MomentumDirection.STRONG_BULLISH


def test_momentum_accelerating() -> None:
    window = (_disp(1, _BU, "1.0"), _disp(2, _BU, "2.0"))
    assert (
        _assess_timeframe_momentum(_M15, window, _CFG).acceleration
        is MomentumAcceleration.ACCELERATING
    )


def test_momentum_decelerating() -> None:
    window = (_disp(1, _BU, "2.0"), _disp(2, _BU, "1.0"))
    assert (
        _assess_timeframe_momentum(_M15, window, _CFG).acceleration
        is MomentumAcceleration.DECELERATING
    )


def test_momentum_score_is_deterministic_and_bounded() -> None:
    window = (_disp(1, _BU, "1.5"), _disp(2, _BU, "1.5"))
    s1 = _assess_timeframe_momentum(_M15, window, _CFG).momentum_score
    s2 = _assess_timeframe_momentum(_M15, window, _CFG).momentum_score
    assert s1 == s2
    assert 0 <= s1 <= 100


# ---------------- breakout ----------------
_BOS = StructureTransitionType.BULLISH_BOS
_BULL_CHOCH = StructureTransitionType.BULLISH_CHOCH
_BEAR_CHOCH = StructureTransitionType.BEARISH_CHOCH


def test_breakout_weak_without_displacement() -> None:
    b = _assess_timeframe_breakout(_M15, (_transition(1, _BOS, 10),), (), ())
    assert b.breakout_state is BreakoutState.WEAK_BREAK


def test_breakout_valid_with_normal_displacement() -> None:
    b = _assess_timeframe_breakout(
        _M15, (_transition(1, _BOS, 10),), (), (_disp(10, _BU, "1.2", _NORMAL),)
    )
    assert b.breakout_state is BreakoutState.VALID_BREAK


def test_breakout_strong_with_fast_displacement() -> None:
    b = _assess_timeframe_breakout(
        _M15, (_transition(1, _BOS, 10),), (), (_disp(10, _BU, "1.6", _FAST),)
    )
    assert b.breakout_state is BreakoutState.STRONG_BREAK


def test_breakout_explosive_with_very_fast_displacement() -> None:
    b = _assess_timeframe_breakout(
        _M15, (_transition(1, _BOS, 10),), (), (_disp(10, _BU, "2.2", _VFAST),)
    )
    assert b.breakout_state is BreakoutState.EXPLOSIVE_BREAK


def test_breakout_liquidity_sweep_when_level_taken_after_break() -> None:
    b = _assess_timeframe_breakout(
        _M15, (_transition(1, _BOS, 10),), (_equal_level(2, 20),), ()
    )
    assert b.breakout_state is BreakoutState.LIQUIDITY_SWEEP


def test_breakout_failed_on_whipsaw_reversal() -> None:
    transitions = (_transition(1, _BULL_CHOCH, 10), _transition(2, _BEAR_CHOCH, 20))
    b = _assess_timeframe_breakout(_M15, transitions, (), ())
    assert b.breakout_state is BreakoutState.FAILED_BREAK


def test_breakout_history_not_rewritten_across_prefixes() -> None:
    # at the break: VALID; after a later whipsaw: FAILED. Each prefix keeps its
    # own reading (pure function of the prefix).
    valid = _assess_timeframe_breakout(
        _M15, (_transition(1, _BOS, 10),), (), (_disp(10, _BU, "1.2", _NORMAL),)
    )
    later = _assess_timeframe_breakout(
        _M15,
        (_transition(1, _BULL_CHOCH, 10), _transition(2, _BEAR_CHOCH, 20)),
        (),
        (),
    )
    assert valid.breakout_state is BreakoutState.VALID_BREAK
    assert later.breakout_state is BreakoutState.FAILED_BREAK


# ---------------- pullback ----------------
def test_pullback_none_without_impulse() -> None:
    p = _assess_timeframe_pullback(
        _M15, (), _state(StructureDirection.UNDETERMINED), (), _CFG
    )
    assert p.pullback_state is None


def _bullish_impulse(pullback_low: str) -> tuple[ConfirmedSwing, ...]:
    # origin low 100 -> high 110 (leg 10), pullback low retraces.
    return (
        _swing(1, SwingType.SWING_LOW, "100", 10),
        _swing(2, SwingType.SWING_HIGH, "110", 20),
        _swing(3, SwingType.SWING_LOW, pullback_low, 30),
    )


def test_pullback_shallow() -> None:
    p = _assess_timeframe_pullback(
        _M15, _bullish_impulse("107"), _state(StructureDirection.BULLISH), (), _CFG
    )
    assert p.pullback_state is PullbackState.SHALLOW_PULLBACK  # depth 0.3


def test_pullback_healthy() -> None:
    p = _assess_timeframe_pullback(
        _M15, _bullish_impulse("105"), _state(StructureDirection.BULLISH), (), _CFG
    )
    assert p.pullback_state is PullbackState.HEALTHY_PULLBACK  # depth 0.5


def test_pullback_deep_but_structurally_valid() -> None:
    p = _assess_timeframe_pullback(
        _M15, _bullish_impulse("102"), _state(StructureDirection.BULLISH), (), _CFG
    )
    assert p.pullback_state is PullbackState.DEEP_PULLBACK  # depth 0.8, still > origin


def test_pullback_structural_failure_when_origin_exceeded() -> None:
    p = _assess_timeframe_pullback(
        _M15, _bullish_impulse("99"), _state(StructureDirection.BULLISH), (), _CFG
    )
    assert p.pullback_state is PullbackState.STRUCTURAL_FAILURE  # depth > 1.0


# ---------------- integration -----------------
def _config() -> ScannerConfiguration:
    tick = Decimal("0.01")
    return ScannerConfiguration(
        measurement_configuration=MarketMeasurementConfiguration(
            minimum_price_tick=tick
        ),
        structure_configuration=StructureConfiguration(),
        poi_configuration=PoiConfiguration(minimum_price_tick=tick),
        btmm_configuration=BtmmConfiguration(minimum_price_tick=tick),
        required_timeframes=frozenset({_M15}),
        optional_timeframes=frozenset(),
    )


def _m15(n: int, seed: int) -> tuple[NormalizedCandle, ...]:
    rng = random.Random(seed)
    price = 100.0
    out: list[NormalizedCandle] = []
    for i in range(n):
        o = price
        c = o + rng.uniform(-1.5, 1.5)
        h = max(o, c) + rng.uniform(0, 0.8)
        low = min(o, c) - rng.uniform(0, 0.8)
        event = _BASE + timedelta(minutes=15 * i)
        avail = event + timedelta(minutes=15)
        out.append(
            NormalizedCandle.model_validate(
                {
                    "record_id": _uid(500000 + i),
                    "content_fingerprint": _FP,
                    "raw_candle_id": _uid(600000 + i),
                    "provider": "FXCM",
                    "source_reference": "fxcm-xauusd-m15",
                    "source_symbol": "XAUUSD",
                    "source_timeframe": "M15",
                    "symbol": InternalSymbol.XAUUSD,
                    "timeframe": _M15,
                    "event_time_utc": event,
                    "availability_time_utc": avail,
                    "processing_time_utc": avail,
                    "original_event_time": event,
                    "original_availability_time": avail,
                    "original_timezone": "UTC",
                    "open": Decimal(str(o)),
                    "high": Decimal(str(h)),
                    "low": Decimal(str(low)),
                    "close": Decimal(str(c)),
                    "volume": Decimal("10"),
                    "volume_kind": CandleVolumeKind.TICK,
                    "completeness": CandleCompleteness.CONFIRMED_COMPLETE,
                    "rule_version": _V,
                    "contract_version": _V,
                    "schema_version": _V,
                    "provenance_id": _uid(700000 + i),
                }
            )
        )
        price = c
    return tuple(out)


def _batch(candles: tuple[NormalizedCandle, ...]) -> ScannerAnalysis:
    return scan_market(
        (ScannerTimeframeInput(_M15, candles),),
        (),
        _config(),
        ContentAddressedIdentityProvider(),
    )


def _incremental(candles: tuple[NormalizedCandle, ...]) -> ScannerAnalysis:
    return run_scanner_replay(
        (ScannerTimeframeInput(_M15, candles),),
        (),
        _config(),
        ReplayConfiguration(
            snapshot_retention=SnapshotRetentionPolicy.FINAL_ONLY,
            verify_against_direct_batch=False,
        ),
        ContentAddressedIdentityProvider(),
    ).final_snapshot


def test_t3_deterministic_and_provenance_stable() -> None:
    analysis = _batch(_m15(120, 42))
    assert assess_momentum(analysis) == assess_momentum(analysis)
    assert assess_breakout(analysis) == assess_breakout(analysis)
    assert assess_pullback(analysis) == assess_pullback(analysis)


def test_t3_incremental_and_batch_equivalent() -> None:
    candles = _m15(120, 42)
    assert assess_momentum(_incremental(candles)) == assess_momentum(_batch(candles))
    assert assess_breakout(_incremental(candles)) == assess_breakout(_batch(candles))
    assert assess_pullback(_incremental(candles)) == assess_pullback(_batch(candles))


def test_t3_no_lookahead_prefix_causality() -> None:
    candles = _m15(60, 7)
    for k in (20, 40, 60):
        prefix = candles[:k]
        assert assess_momentum(_batch(prefix)) == assess_momentum(_incremental(prefix))
        assert assess_breakout(_batch(prefix)) == assess_breakout(_incremental(prefix))
        assert assess_pullback(_batch(prefix)) == assess_pullback(_incremental(prefix))
