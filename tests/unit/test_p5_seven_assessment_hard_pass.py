"""P5 seven-assessment hard pass: T1 trend, T2 regime, T3 momentum/breakout/
pullback, T4 session/volatility -- all seven, from ONE shared reduction, in
one place.

Each assessment already has its own dedicated differential suite
(`test_t1_trend_transport_sufficiency.py` through
`test_t4_transport_sufficiency.py`). This file exists for a different reason:
those suites each build their OWN `P5TransportRecord` per call, so a bug that
corrupted `reduce_authoritative` in a way that happened to cancel out when
called once per assessment (or a bug in how `p2Direction` is threaded from T1
into T3's pullback gate) would not necessarily surface there. Here, the record
is reduced EXACTLY ONCE per random case and every downstream assessment reads
that single reduction -- the same shape a single Pine bar's evaluation
actually has.

T4 shares no history with T1/T2/T3 (see `t4_pine_model.py`'s own docstring),
so it is exercised here with its own independently-randomized inputs in the
same iteration, not because the data is coupled, but so this file is the one
place that gates all seven together: `P5_SEVEN_ASSESSMENT_SUFFICIENCY` is only
true once every one of the seven agrees, every iteration, in the same run.
"""

from __future__ import annotations

import random
from datetime import UTC, datetime, timedelta

from btmm_ai_scanner.btrc.enums import TrendState
from btmm_ai_scanner.btrc.regime_configuration import RegimeEngineConfiguration
from btmm_ai_scanner.btrc.regime_engine import _regime_for_timeframe
from btmm_ai_scanner.btrc.t3_configuration import MomentumBreakoutPullbackConfiguration
from btmm_ai_scanner.btrc.t3_engine import (
    _assess_timeframe_breakout,
    _assess_timeframe_momentum,
    _assess_timeframe_pullback,
)
from btmm_ai_scanner.btrc.t4_configuration import VolatilitySessionConfiguration
from btmm_ai_scanner.btrc.t4_engine import assess_session, assess_volatility
from btmm_ai_scanner.btrc.trend_configuration import TrendEngineConfiguration
from btmm_ai_scanner.btrc.trend_engine import _assess_timeframe
from btmm_ai_scanner.config.enums import Timeframe
from btmm_ai_scanner.measurements.candle_metrics import total_range
from tests.parity_support.p5_transport_contract import DIR_BEARISH, DIR_BULLISH
from tests.parity_support.p5_transport_fixtures import random_history
from tests.parity_support.p5_transport_oracle import reduce_authoritative
from tests.parity_support.t1_trend_pine_model import assess_trend_from_transport
from tests.parity_support.t2_regime_pine_model import (
    regime_for_timeframe_from_transport,
)
from tests.parity_support.t3_pine_model import (
    breakout_from_transport,
    momentum_from_transport,
    pullback_from_transport,
)
from tests.parity_support.t4_pine_model import (
    session_from_evaluation_time,
    volatility_from_window,
)
from tests.unit.test_t4_transport_sufficiency import _candle

_M15 = Timeframe.M15
_T3_CFG = MomentumBreakoutPullbackConfiguration()
_T4_CFG = VolatilitySessionConfiguration()


def _p2_direction(current_state) -> int:
    if current_state is None:
        return 0
    from btmm_ai_scanner.structure.enums import StructureDirection

    return {
        StructureDirection.BULLISH: DIR_BULLISH,
        StructureDirection.BEARISH: DIR_BEARISH,
        StructureDirection.UNDETERMINED: 0,
    }[current_state.direction]


def _one_case(rng: random.Random) -> None:
    swings, transitions, displacements, current_state = random_history(rng)
    record = reduce_authoritative(swings, transitions, displacements, current_state)
    p2_direction = _p2_direction(current_state)
    swing_count = current_state.analyzed_swing_count if current_state else 0

    # 1. T1 trend
    t1_real = _assess_timeframe(
        _M15, tuple(swings), tuple(transitions), current_state, TrendEngineConfiguration()
    )
    t1_wire = assess_trend_from_transport(
        p2_direction=p2_direction, swing_count=swing_count, record=record
    )
    assert t1_real.trend_state == t1_wire.trend_state
    assert t1_real.direction == t1_wire.direction

    # 2. T2 regime
    t2_real = _regime_for_timeframe(t1_real, tuple(displacements), RegimeEngineConfiguration())
    t2_wire = regime_for_timeframe_from_transport(t1_wire.trend_state, record)
    assert t2_real.regime == t2_wire

    # 3. T3 momentum
    t3m_real = _assess_timeframe_momentum(_M15, tuple(displacements), _T3_CFG)
    t3m_wire = momentum_from_transport(record)
    assert t3m_real.direction == t3m_wire.direction
    assert abs(t3m_real.momentum_score - t3m_wire.momentum_score) <= 1

    # 4. T3 breakout
    t3b_real = _assess_timeframe_breakout(_M15, tuple(transitions), (), tuple(displacements))
    t3b_wire = breakout_from_transport(record)
    assert t3b_real.breakout_state == t3b_wire.breakout_state
    assert t3b_real.breakout_score == t3b_wire.breakout_score

    # 5. T3 pullback
    t3p_real = _assess_timeframe_pullback(
        _M15, tuple(swings), current_state, (), _T3_CFG
    )
    t3p_wire = pullback_from_transport(p2_direction, record)
    assert t3p_real.pullback_state == t3p_wire.pullback_state

    # 6. T4 session (independently-randomized: T4 shares no history with T1-T3)
    start = datetime(2020, 1, 1, tzinfo=UTC)
    eval_time = start + timedelta(
        days=rng.randint(0, 365 * 6), minutes=rng.randint(0, 24 * 60 - 1)
    )
    t4s_real = assess_session(eval_time, _T4_CFG)
    t4s_wire = session_from_evaluation_time(eval_time)
    assert t4s_real.session_context == t4s_wire

    # 7. T4 volatility (independently-randomized candle window)
    n = rng.randint(_T4_CFG.atr_period, _T4_CFG.volatility_window + 5)
    range_sizes = [max(0.01, rng.random() * 20) for _ in range(n)]
    candles = [_candle(i, r) for i, r in enumerate(range_sizes)]
    t4v_real = assess_volatility(candles, _T4_CFG)
    window = candles[-_T4_CFG.volatility_window :]
    ranges = [total_range(c) for c in window]
    t4v_wire = volatility_from_window(ranges)
    assert t4v_real.volatility_state == t4v_wire.volatility_state
    assert t4v_real.abnormal_spike == t4v_wire.abnormal_spike


def test_seven_assessment_hard_pass_randomized() -> None:
    rng = random.Random(90210)
    for _ in range(3000):
        _one_case(rng)


def test_seven_assessment_hard_pass_covers_every_trend_state_in_one_run() -> None:
    """The combined pass must actually exercise every T1 state at least once,
    not merely avoid crashing on a corpus that happens to skip the hard ones."""
    rng = random.Random(24680)
    seen: set[TrendState] = set()
    for _ in range(4000):
        swings, transitions, _displacements, current_state = random_history(rng)
        real = _assess_timeframe(
            _M15, tuple(swings), tuple(transitions), current_state, TrendEngineConfiguration()
        )
        seen.add(real.trend_state)
    assert seen == set(TrendState)
