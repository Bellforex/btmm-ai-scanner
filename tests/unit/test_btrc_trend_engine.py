"""BTRC-T1 deterministic trend-engine tests.

Two layers: (1) direct, precise tests of the per-timeframe state machine and the
global authority resolver using hand-built scanner structure records; (2)
integration tests over a real ``ScannerAnalysis`` from ``scan_market`` /
``run_scanner_replay`` proving determinism, no-lookahead, and incremental-vs-batch
equivalence. Synthetic fixtures only; no scanner semantics are modified.
"""

import random
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

from btmm_ai_scanner.btmm.configuration import BtmmConfiguration
from btmm_ai_scanner.btrc import Direction, TrendState, assess_trend
from btmm_ai_scanner.btrc.trend_configuration import TrendEngineConfiguration
from btmm_ai_scanner.btrc.trend_engine import _assess_timeframe, _resolve_global
from btmm_ai_scanner.config.enums import InternalSymbol, Timeframe
from btmm_ai_scanner.contracts.normalized_candle import NormalizedCandle
from btmm_ai_scanner.contracts.provenance_record import EvidenceClassification
from btmm_ai_scanner.contracts.raw_candle import CandleCompleteness, CandleVolumeKind
from btmm_ai_scanner.contracts.types import SemVer
from btmm_ai_scanner.domain.configuration import MarketMeasurementConfiguration
from btmm_ai_scanner.domain.enums import SwingType
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
_CFG = TrendEngineConfiguration()


def _uid(n: int) -> UUID:
    return UUID(f"0193f350-1234-7abc-8def-{n:012x}")


def _swing(n: int, swing_type: SwingType, price: str, minute: int) -> ConfirmedSwing:
    t = _BASE + timedelta(minutes=minute)
    return ConfirmedSwing(
        record_id=_uid(n),
        content_fingerprint=_FP,
        symbol=InternalSymbol.XAUUSD,
        timeframe=Timeframe.M15,
        swing_type=swing_type,
        pivot_price=Decimal(price),
        pivot_bar_index=n,
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


def _transition(
    n: int,
    transition_type: StructureTransitionType,
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
        transition_type=transition_type,
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


def _state(direction: StructureDirection, swing_count: int) -> CurrentStructureState:
    t = _BASE + timedelta(minutes=500)
    return CurrentStructureState(
        record_id=_uid(8000),
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
        provenance_id=_uid(9000),
    )


_BU = StructureDirection.BULLISH
_BE = StructureDirection.BEARISH
_UN = StructureDirection.UNDETERMINED
_BULLISH_BOS = StructureTransitionType.BULLISH_BOS
_BEARISH_BOS = StructureTransitionType.BEARISH_BOS
_BULLISH_CHOCH = StructureTransitionType.BULLISH_CHOCH
_BEARISH_CHOCH = StructureTransitionType.BEARISH_CHOCH


# ----- (1) direct per-timeframe state-machine tests -----
def test_insufficient_data_is_unknown_neutral() -> None:
    a = _assess_timeframe(Timeframe.M15, (), (), None, _CFG)
    assert a.trend_state is TrendState.UNKNOWN
    assert a.direction is Direction.NEUTRAL


def test_undetermined_structure_is_forming_neutral() -> None:
    a = _assess_timeframe(Timeframe.M15, (), (), _state(_UN, 3), _CFG)
    assert a.trend_state is TrendState.FORMING
    assert a.direction is Direction.NEUTRAL


def test_confirmed_bullish_sequence_is_trending_bullish() -> None:
    transitions = (
        _transition(1, _BULLISH_CHOCH, _BE, _BU, 10),
        _transition(2, _BULLISH_BOS, _BU, _BU, 20),
    )
    a = _assess_timeframe(Timeframe.M15, (), transitions, _state(_BU, 5), _CFG)
    assert a.trend_state is TrendState.TRENDING
    assert a.direction is Direction.BULLISH


def test_confirmed_bearish_sequence_is_trending_bearish() -> None:
    transitions = (
        _transition(1, _BEARISH_CHOCH, _BU, _BE, 10),
        _transition(2, _BEARISH_BOS, _BE, _BE, 20),
    )
    a = _assess_timeframe(Timeframe.M15, (), transitions, _state(_BE, 5), _CFG)
    assert a.trend_state is TrendState.TRENDING
    assert a.direction is Direction.BEARISH


def test_strong_bullish_requires_persistence() -> None:
    transitions = (
        _transition(1, _BULLISH_CHOCH, _BE, _BU, 10),
        _transition(2, _BULLISH_BOS, _BU, _BU, 20),
        _transition(3, _BULLISH_BOS, _BU, _BU, 30),
        _transition(4, _BULLISH_BOS, _BU, _BU, 40),
    )
    a = _assess_timeframe(Timeframe.M15, (), transitions, _state(_BU, 8), _CFG)
    assert a.continuation_streak == 3
    assert a.direction is Direction.STRONG_BULLISH
    assert a.trend_state is TrendState.TRENDING


def test_established_trend_reversal_choch_is_transition() -> None:
    # bullish trend established, then a bearish CHOCH -> TRANSITION (new trend
    # unconfirmed), and direction now reports the reversed side.
    transitions = (
        _transition(1, _BULLISH_CHOCH, _BE, _BU, 10),
        _transition(2, _BULLISH_BOS, _BU, _BU, 20),
        _transition(3, _BULLISH_BOS, _BU, _BU, 30),
        _transition(4, _BEARISH_CHOCH, _BU, _BE, 40),
    )
    a = _assess_timeframe(Timeframe.M15, (), transitions, _state(_BE, 9), _CFG)
    assert a.trend_state is TrendState.TRANSITION
    assert a.direction is Direction.BEARISH


def test_confirmed_reversal_eventually_trends_the_other_way() -> None:
    transitions = (
        _transition(1, _BULLISH_CHOCH, _BE, _BU, 10),
        _transition(2, _BULLISH_BOS, _BU, _BU, 20),
        _transition(3, _BEARISH_CHOCH, _BU, _BE, 40),
        _transition(4, _BEARISH_BOS, _BE, _BE, 50),
    )
    a = _assess_timeframe(Timeframe.M15, (), transitions, _state(_BE, 10), _CFG)
    assert a.direction is Direction.BEARISH
    assert a.trend_state is TrendState.TRENDING


def test_lower_high_while_bullish_is_exhausting() -> None:
    swings = (
        _swing(1, SwingType.SWING_HIGH, "110", 10),
        _swing(2, SwingType.SWING_HIGH, "108", 20),  # lower high
    )
    transitions = (
        _transition(1, _BULLISH_CHOCH, _BE, _BU, 5),
        _transition(2, _BULLISH_BOS, _BU, _BU, 15),
    )
    a = _assess_timeframe(Timeframe.M15, swings, transitions, _state(_BU, 6), _CFG)
    assert a.trend_state is TrendState.EXHAUSTING
    assert a.direction is Direction.BULLISH  # still bullish, not flipped


def test_alternating_choch_is_range() -> None:
    transitions = (
        _transition(1, _BULLISH_CHOCH, _BE, _BU, 10),
        _transition(2, _BEARISH_CHOCH, _BU, _BE, 20),
        _transition(3, _BULLISH_CHOCH, _BE, _BU, 30),
    )
    a = _assess_timeframe(Timeframe.M15, (), transitions, _state(_BU, 7), _CFG)
    assert a.trend_state is TrendState.RANGE


def test_one_opposite_swing_does_not_flip_a_bullish_timeframe() -> None:
    # An established bullish structure plus a single opposite (lower-high) swing —
    # with NO confirmed bearish CHOCH — must never report a bearish direction.
    transitions = (
        _transition(1, _BULLISH_CHOCH, _BE, _BU, 10),
        _transition(2, _BULLISH_BOS, _BU, _BU, 20),
        _transition(3, _BULLISH_BOS, _BU, _BU, 30),
    )
    swings = (
        _swing(1, SwingType.SWING_HIGH, "110", 25),
        _swing(2, SwingType.SWING_HIGH, "109", 35),  # one opposite move
    )
    a = _assess_timeframe(Timeframe.M15, swings, transitions, _state(_BU, 8), _CFG)
    assert a.direction in (Direction.BULLISH, Direction.STRONG_BULLISH)
    assert a.trend_state is not TrendState.TRANSITION


# ----- (1) global authority resolver tests -----
def test_global_bullish_d1_h4_with_bearish_h1_stays_bullish() -> None:
    resolved = _resolve_global(
        {
            Timeframe.D1: Direction.BULLISH,
            Timeframe.H4: Direction.BULLISH,
            Timeframe.H1: Direction.BEARISH,
        }
    )
    assert resolved is Direction.BULLISH


def test_global_bearish_d1_h4_with_bullish_h1_stays_bearish() -> None:
    resolved = _resolve_global(
        {
            Timeframe.D1: Direction.BEARISH,
            Timeframe.H4: Direction.BEARISH,
            Timeframe.H1: Direction.BULLISH,
        }
    )
    assert resolved is Direction.BEARISH


def test_strong_global_requires_w1_and_h4_agreement() -> None:
    assert (
        _resolve_global(
            {
                Timeframe.D1: Direction.BULLISH,
                Timeframe.W1: Direction.BULLISH,
                Timeframe.H4: Direction.BULLISH,
            }
        )
        is Direction.STRONG_BULLISH
    )
    assert (
        _resolve_global(
            {
                Timeframe.D1: Direction.BULLISH,
                Timeframe.W1: Direction.NEUTRAL,
                Timeframe.H4: Direction.BULLISH,
            }
        )
        is Direction.BULLISH
    )


def test_conflicting_higher_tf_is_deterministic_d1_primary() -> None:
    # D1 bullish primacy holds even when W1/H4 oppose; never STRONG.
    resolved = _resolve_global(
        {
            Timeframe.D1: Direction.BULLISH,
            Timeframe.W1: Direction.BEARISH,
            Timeframe.H4: Direction.BEARISH,
        }
    )
    assert resolved is Direction.BULLISH


def test_d1_neutral_uses_w1_h4_agreement() -> None:
    assert (
        _resolve_global(
            {
                Timeframe.D1: Direction.NEUTRAL,
                Timeframe.W1: Direction.BULLISH,
                Timeframe.H4: Direction.BULLISH,
            }
        )
        is Direction.BULLISH
    )
    assert (
        _resolve_global(
            {
                Timeframe.D1: Direction.NEUTRAL,
                Timeframe.W1: Direction.BULLISH,
                Timeframe.H4: Direction.BEARISH,
            }
        )
        is Direction.NEUTRAL
    )


def test_lower_timeframes_never_flip_global() -> None:
    base = {Timeframe.D1: Direction.STRONG_BULLISH, Timeframe.W1: Direction.BULLISH}
    for local in (Direction.BEARISH, Direction.STRONG_BEARISH, Direction.NEUTRAL):
        resolved = _resolve_global(
            {**base, Timeframe.H1: local, Timeframe.M15: local, Timeframe.M5: local}
        )
        assert resolved in (Direction.BULLISH, Direction.STRONG_BULLISH)


# ----- (2) integration over a real ScannerAnalysis -----
def _config(required: frozenset[Timeframe]) -> ScannerConfiguration:
    tick = Decimal("0.01")
    return ScannerConfiguration(
        measurement_configuration=MarketMeasurementConfiguration(
            minimum_price_tick=tick
        ),
        structure_configuration=StructureConfiguration(),
        poi_configuration=PoiConfiguration(minimum_price_tick=tick),
        btmm_configuration=BtmmConfiguration(minimum_price_tick=tick),
        required_timeframes=required,
        optional_timeframes=frozenset(),
    )


def _m15_candles(n: int, seed: int) -> tuple[NormalizedCandle, ...]:
    rng = random.Random(seed)
    price = 100.0
    candles: list[NormalizedCandle] = []
    for i in range(n):
        o = price
        c = o + rng.uniform(-1.5, 1.5)
        h = max(o, c) + rng.uniform(0, 0.8)
        low = min(o, c) - rng.uniform(0, 0.8)
        event = _BASE + timedelta(minutes=15 * i)
        avail = event + timedelta(minutes=15)
        candles.append(
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
                    "timeframe": Timeframe.M15,
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
    return tuple(candles)


def _batch(candles: tuple[NormalizedCandle, ...]) -> ScannerAnalysis:
    config = _config(frozenset({Timeframe.M15}))
    bundles = (ScannerTimeframeInput(Timeframe.M15, candles),)
    return scan_market(bundles, (), config, ContentAddressedIdentityProvider())


def _incremental(candles: tuple[NormalizedCandle, ...]) -> ScannerAnalysis:
    config = _config(frozenset({Timeframe.M15}))
    bundles = (ScannerTimeframeInput(Timeframe.M15, candles),)
    return run_scanner_replay(
        bundles,
        (),
        config,
        ReplayConfiguration(
            snapshot_retention=SnapshotRetentionPolicy.FINAL_ONLY,
            verify_against_direct_batch=False,
        ),
        ContentAddressedIdentityProvider(),
    ).final_snapshot


def test_assess_trend_is_deterministic_on_real_analysis() -> None:
    analysis = _batch(_m15_candles(120, 42))
    first = assess_trend(analysis)
    second = assess_trend(analysis)
    assert first == second
    assert any(a.timeframe is Timeframe.M15 for a in first.timeframe_assessments)


def test_incremental_and_batch_trend_assessments_are_equivalent() -> None:
    candles = _m15_candles(120, 42)
    assert assess_trend(_incremental(candles)) == assess_trend(_batch(candles))


def test_no_lookahead_prefix_assessment_matches_incremental() -> None:
    candles = _m15_candles(60, 7)
    for k in (20, 40, 60):
        prefix = candles[:k]
        assert assess_trend(_batch(prefix)) == assess_trend(_incremental(prefix))
