"""Wire-normalized Python replay of the P5 ATOMIC PARITY capture.

Test/parity tooling only — nothing in `src/` imports this, and it changes no
production semantics.

WHAT "WIRE-NORMALIZED" MEANS HERE
--------------------------------------
Per the campaign's own parity-authority framing: the comparison this module
supports is PINE <-> WIRE-NORMALIZED PYTHON, not Pine <-> original
high-precision Python. Every function this module calls
(`t1_trend_pine_model`, `t2_regime_pine_model`, `t3_pine_model`,
`t5_trend_pine_model`, `t5_component_scores_pine_model`,
`t5_aggregator_pine_model`) already reads ONLY the same 26-field wire Pine
itself reads -- reconstructed from a REAL captured `P5WIRE` line, not a
synthetic fixture. Its output is compared field-by-field against that same
bar's REAL captured `P5EVAL` decision. There is no recomputation from
higher-precision (Decimal) source data anywhere in this module.

TWO LAYERS, MATCHING THE CAPTURE'S OWN TWO LOG TAGS
--------------------------------------------------------
1. Bar-level ("upstream"): T1 (x3 contexts) + T2 + T3-momentum/breakout/
   pullback + T4-session + T5-global-direction/operational-context, computed
   ONCE per bar from the `P5WIRE` line alone. `compute_bar_level` returns
   these already re-encoded as the SAME Pine integer codes `P5EVAL` logs, so
   the comparison in the differential test is a plain `==`.
2. POI-level ("downstream" aggregator): alignment + all eight component
   scores + the weighted final + permission + lifecycle. This layer needs no
   wire at all beyond what a single `P5EVAL` row already logged (POI
   direction/tier, BTMM valid/bullish, and the bar-level fields the row
   itself carries) -- `compute_poi_level` is a pure function of one
   `P5EvalRow`'s own fields plus the weight/band configuration, which is
   ALSO logged verbatim on every row (`wBtmm`..`wVolatility`).

WHAT THIS MODULE DELIBERATELY DOES NOT ATTEMPT
----------------------------------------------------
T4 volatility (`p5VolState`/`p5VolAbnormal`/`p5VolSuitability`) is a
same-process host computation over the M15 candle window's own 300-bar ATR
history -- never carried on the 26-field MTF transport wire this capture
records, so there is no "wire" for this module to normalize against. Its
logged value is treated as an opaque, already-Pine-computed input at the
POI level (exactly how `t5_component_scores_pine_model.volatility_score`
treats it: pass-through, no independent re-derivation). This is a scope
limitation of what `P5WIRE` was designed to capture, not a gap papered over
-- see `docs/architecture/BTRC_V1_P5_BTRC_CLOSURE.md` for the explicit
disclosure.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from btmm_ai_scanner.btrc.enums import (
    AnalyticalPermission,
    Direction,
    MomentumAcceleration,
    MomentumDirection,
    Regime,
    SignalLifecycleState,
    TrendAlignment,
    TrendState,
    VolatilityState,
)
from btmm_ai_scanner.poi.enums import PoiStrengthTier

from .p5_atomic_capture_log import P5EvalRow, P5WireBar
from .p5_transport_contract import P5TransportRecord
from .p5x_capture_log import P5XRecord
from .t1_trend_pine_model import T1Result, assess_trend_from_transport
from .t2_regime_pine_model import regime_for_timeframe_from_transport
from .t3_pine_model import (
    breakout_from_transport,
    momentum_from_transport,
    pullback_from_transport,
)
from .t4_pine_model import T4SessionConfig, session_from_evaluation_time
from .t5_aggregator_pine_model import lifecycle as t5_lifecycle
from .t5_aggregator_pine_model import permission as t5_permission
from .t5_aggregator_pine_model import weighted_final as t5_weighted_final
from .t5_component_scores_pine_model import (
    btmm_score,
    liquidity_score,
    momentum_score,
    poi_score,
    regime_score,
    trend_alignment,
    trend_score,
    volatility_score,
)
from .t5_trend_pine_model import operational_context, resolve_global_direction

# -----------------------------------------------------------------------------
# Pine integer-code tables — transcribed directly from the C_* constant blocks
# in btmm_poi_btrc_scanner_p5_atomic_parity.pine (lines ~5059-5137). These are
# the SAME codes the P5EVAL/P5WIRE log lines carry, so encoding a Python enum
# result through these tables makes the differential a plain `==`.
# -----------------------------------------------------------------------------
C_ST_NA = -99

TREND_STATE_CODE: dict[TrendState, int] = {
    TrendState.UNKNOWN: 0,
    TrendState.FORMING: 1,
    TrendState.TRENDING: 2,
    TrendState.TRANSITION: 3,
    TrendState.EXHAUSTING: 4,
    TrendState.RANGE: 5,
}

REGIME_CODE: dict[Regime, int] = {
    Regime.UNCERTAIN: 0,
    Regime.TRANSITION: 1,
    Regime.TREND: 2,
    Regime.DECELERATION: 3,
    Regime.RANGE: 4,
    Regime.EXPANSION: 5,
    Regime.BREAKOUT_PENDING: 6,
    Regime.COMPRESSION: 7,
}

#: Shared by Direction (T1/T5) AND MomentumDirection (T3) -- Pine encodes both
#: through the same C_DIR2_* 5-way scale, keyed here by the enum's `.value`
#: string since the two Python enums are otherwise distinct types.
_DIR2_CODE_BY_NAME: dict[str, int] = {
    "NEUTRAL": 0,
    "BULLISH": 1,
    "STRONG_BULLISH": 2,
    "BEARISH": -1,
    "STRONG_BEARISH": -2,
}


def direction_code(direction: Direction) -> int:
    return _DIR2_CODE_BY_NAME[direction.value]


def momentum_direction_code(direction: MomentumDirection) -> int:
    return _DIR2_CODE_BY_NAME[direction.value]


MOMENTUM_ACCELERATION_CODE: dict[MomentumAcceleration, int] = {
    MomentumAcceleration.STEADY: 0,
    MomentumAcceleration.ACCELERATING: 1,
    MomentumAcceleration.DECELERATING: -1,
}

#: BreakoutState | None -> Pine code. None ("no break present", transWindowCount
#: == 0) is C_ST_NA, matching `f_p5T3Brk`'s own initial value.
BREAKOUT_STATE_CODE: dict[str, int] = {
    "NONE": C_ST_NA,
    "WEAK_BREAK": 1,
    "VALID_BREAK": 2,
    "STRONG_BREAK": 3,
    "EXPLOSIVE_BREAK": 4,
    "FAILED_BREAK": 5,
}

#: PullbackState | None -> Pine code. None is C_ST_NA, matching `f_p5T3Pb`'s
#: own initial value.
PULLBACK_STATE_CODE: dict[str, int] = {
    "NONE": C_ST_NA,
    "SHALLOW_PULLBACK": 1,
    "HEALTHY_PULLBACK": 2,
    "DEEP_PULLBACK": 3,
    "STRUCTURAL_FAILURE": 4,
}

SESSION_CODE: dict[str, int] = {
    "ASIAN": 0,
    "LONDON_PREOPEN": 1,
    "LONDON": 2,
    "NEW_YORK_PREOPEN": 3,
    "LONDON_NY_OVERLAP": 4,
    "NEW_YORK": 5,
    "POST_NY": 6,
}

ALIGNMENT_CODE: dict[TrendAlignment, int] = {
    TrendAlignment.ALIGNED: 0,
    TrendAlignment.PARTIAL: 1,
    TrendAlignment.NEUTRAL: 2,
    TrendAlignment.COUNTER_TREND: 3,
}

PERMISSION_CODE: dict[AnalyticalPermission, int] = {
    AnalyticalPermission.BUY_BIAS: 0,
    AnalyticalPermission.SELL_BIAS: 1,
    AnalyticalPermission.ALLOW_BOTH_CONTEXT: 2,
    AnalyticalPermission.COUNTER_TREND: 3,
    AnalyticalPermission.WATCH_ONLY: 4,
    AnalyticalPermission.NO_TRADE_CONTEXT: 5,
}

#: `f_p5Lifecycle` always starts past DETECTED (hasStructure is structurally
#: always true once the host has warmed) and never returns BTMM_VALIDATED
#: (provably unreachable, per the frozen T5-aggregator-sufficiency finding) --
#: so those two codes are declared but never produced by `compute_poi_level`.
LIFECYCLE_CODE: dict[SignalLifecycleState, int] = {
    SignalLifecycleState.DETECTED: 0,
    SignalLifecycleState.STRUCTURALLY_VALIDATED: 1,
    SignalLifecycleState.BTMM_VALIDATED: 2,
    SignalLifecycleState.POI_VALIDATED: 3,
    SignalLifecycleState.TREND_VALIDATED: 4,
    SignalLifecycleState.REGIME_VALIDATED: 5,
    SignalLifecycleState.MOMENTUM_VALIDATED: 6,
    SignalLifecycleState.LIQUIDITY_VALIDATED: 7,
}

#: `poiTier` on the wire: P3's own C_POI_TIER_* codes (0=NA, 1=STANDARD,
#: 2=STRONG) -- distinct from every C_* table above, transcribed from the
#: already-closed P3 registry contract, not from this file's own constants.
POI_TIER_BY_CODE: dict[int, PoiStrengthTier | None] = {
    0: None,
    1: PoiStrengthTier.STANDARD,
    2: PoiStrengthTier.STRONG,
}


def p5_transport_record_from_wire(record: P5XRecord) -> P5TransportRecord:
    """A captured `P5WIRE` timeframe block, decoded into the SAME
    `P5TransportRecord` the t1-t5 pine-model modules already accept -- field
    names and types match exactly (`P5XRecord.values` is keyed by the wire's
    own 26 field names)."""
    return P5TransportRecord(**record.values)  # type: ignore[arg-type]


@dataclass(frozen=True)
class BarLevel:
    """Every T1-T5-global/T2/T3/T4-session decision for one bar, computed
    from ONLY that bar's captured `P5WIRE` line, re-encoded as Pine's own
    integer codes -- directly comparable to a `P5EVAL` row's fields."""

    d1_trend: int
    w1_trend: int
    h4_trend: int
    d1_direction: int
    w1_direction: int
    h4_direction: int
    regime: int
    mom_dir: int
    mom_accel: int
    mom_raw: int
    brk: int
    brk_score_raw: int
    pb: int
    session: int
    global_dir: int
    oper_ctx: int


def _t1(p2_dir: int, swing_count: int, record: P5TransportRecord) -> T1Result:
    return assess_trend_from_transport(p2_direction=p2_dir, swing_count=swing_count, record=record)


def compute_bar_level(wire: P5WireBar) -> BarLevel:
    d1_record = p5_transport_record_from_wire(wire.timeframes["D1"])
    w1_record = p5_transport_record_from_wire(wire.timeframes["W1"])
    h4_record = p5_transport_record_from_wire(wire.timeframes["H4"])
    m15_record = p5_transport_record_from_wire(wire.timeframes["M15"])

    d1_t1 = _t1(wire.d1_p2_dir, wire.d1_swing_count, d1_record)
    w1_t1 = _t1(wire.w1_p2_dir, wire.w1_swing_count, w1_record)
    h4_t1 = _t1(wire.h4_p2_dir, wire.h4_swing_count, h4_record)

    # T2's global regime is always D1 in this deployment -- PRIMARY_ORDER's
    # first entry, exactly as `f_p5T2(d1Trend, d1Ext)` reads only D1. Mirrors
    # the Pine source's own dead-code justification (t2_regime_pine_model.py's
    # docstring, and the P5WIRE emitter's own comment).
    regime = regime_for_timeframe_from_transport(d1_t1.trend_state, d1_record)

    momentum = momentum_from_transport(m15_record)
    breakout = breakout_from_transport(m15_record)
    pullback = pullback_from_transport(wire.m15_p2_dir, m15_record)

    evaluation_time_utc = datetime.fromtimestamp(wire.bar / 1000, tz=UTC)
    session = session_from_evaluation_time(evaluation_time_utc, T4SessionConfig())

    global_dir = resolve_global_direction(d1_t1.direction, w1_t1.direction, h4_t1.direction)
    oper_ctx = operational_context(h4_t1.direction)

    return BarLevel(
        d1_trend=TREND_STATE_CODE[d1_t1.trend_state],
        w1_trend=TREND_STATE_CODE[w1_t1.trend_state],
        h4_trend=TREND_STATE_CODE[h4_t1.trend_state],
        d1_direction=direction_code(d1_t1.direction),
        w1_direction=direction_code(w1_t1.direction),
        h4_direction=direction_code(h4_t1.direction),
        regime=REGIME_CODE[regime],
        mom_dir=momentum_direction_code(momentum.direction),
        mom_accel=MOMENTUM_ACCELERATION_CODE[momentum.acceleration],
        mom_raw=momentum.momentum_score,
        brk=BREAKOUT_STATE_CODE[breakout.breakout_state.value if breakout.breakout_state else "NONE"],
        brk_score_raw=breakout.breakout_score,
        pb=PULLBACK_STATE_CODE[pullback.pullback_state.value if pullback.pullback_state else "NONE"],
        session=SESSION_CODE[session.value],
        global_dir=direction_code(global_dir),
        oper_ctx=direction_code(oper_ctx),
    )


#: The bar-level `P5EVAL` field name -> `BarLevel` attribute name it must
#: equal. Every row logged for the same bar carries an identical copy of
#: these fields (computed once per bar in the Pine source, before the
#: per-POI loop), so the differential test checks this mapping against EVERY
#: row, not just one representative row per bar.
BAR_LEVEL_EVAL_FIELDS: tuple[tuple[str, str], ...] = (
    ("d1Trend", "d1_trend"),
    ("w1Trend", "w1_trend"),
    ("h4Trend", "h4_trend"),
    ("regime", "regime"),
    ("momDir", "mom_dir"),
    ("momAccel", "mom_accel"),
    ("momRaw", "mom_raw"),
    ("brk", "brk"),
    ("brkScoreRaw", "brk_score_raw"),
    ("pb", "pb"),
    ("session", "session"),
    ("globalDir", "global_dir"),
    ("operCtx", "oper_ctx"),
)


@dataclass(frozen=True)
class PoiLevel:
    """Every POI-level T5 aggregator decision, computed from ONLY one
    `P5EvalRow`'s own logged fields (bar-level results + POI/BTMM state +
    the weight/band configuration, all of which the row itself carries) --
    directly comparable to that same row."""

    align: int
    s_trend: int
    s_regime: int
    s_momentum: int
    s_breakout: int
    s_poi: int
    s_btmm: int
    s_liquidity: int
    s_volatility: int
    final: int
    permission: int
    lifecycle: int


_FAVORABLE_REGIMES = {Regime.TREND, Regime.EXPANSION, Regime.BREAKOUT_PENDING}


def compute_poi_level(row: P5EvalRow) -> PoiLevel:
    v = row.values
    poi_bullish = row.poi_bullish

    global_dir = _direction_from_code(int(v["globalDir"]))
    oper_ctx = _direction_from_code(int(v["operCtx"]))
    regime = _regime_from_code(int(v["regime"]))
    mom_dir = _momentum_direction_from_code(int(v["momDir"]))
    tier = POI_TIER_BY_CODE[int(v["poiTier"])]
    btmm_valid = bool(v["btmmValid"])
    btmm_bullish = bool(v["btmmBullish"])
    vol_suitability = int(v["volSuitability"])

    alignment = trend_alignment(global_dir, oper_ctx, poi_bullish)
    s_trend = trend_score(alignment, global_dir)
    s_regime = regime_score(regime)
    # momentum_score's own `momentum_direction is None` branch is unreachable
    # here: `f_p5T3Mom` always returns a Pine direction code (NEUTRAL included)
    # once dispWindowCount > 0, and this capture only carries rows for warmed
    # bars -- so `mom_dir` is always a real `MomentumDirection`, never absent.
    s_momentum = momentum_score(mom_dir, int(v["momRaw"]), poi_bullish)
    s_breakout = int(v["brkScoreRaw"])  # pass-through, per f_p5T5 comment
    s_poi = poi_score(tier)
    s_btmm = btmm_score(btmm_valid, btmm_bullish, poi_bullish)
    s_liquidity = liquidity_score(btmm_valid)
    s_volatility = volatility_score(vol_suitability)

    weights = {
        "btmm": int(v["wBtmm"]),
        "poi": int(v["wPoi"]),
        "trend": int(v["wTrend"]),
        "regime": int(v["wRegime"]),
        "momentum": int(v["wMomentum"]),
        "breakout": int(v["wBreakout"]),
        "liquidity": int(v["wLiquidity"]),
        "volatility": int(v["wVolatility"]),
    }
    values = {
        "btmm": s_btmm,
        "poi": s_poi,
        "trend": s_trend,
        "regime": s_regime,
        "momentum": s_momentum,
        "breakout": s_breakout,
        "liquidity": s_liquidity,
        "volatility": s_volatility,
    }
    final = t5_weighted_final(values, weights)

    # Band/downgrade configuration is logged verbatim on the row too (the
    # weight fields) but the watch-only/high-confluence bands and the
    # extreme-volatility downgrade flag are NOT logged per-row -- they are
    # the fixed P5 defaults (45/65/true), the only values this capture was
    # ever produced under (P5's ENGINEERING-PROVISIONAL config, unchanged
    # from its declared `input.int` defaults for the whole capture session).
    vol_state = _VOLATILITY_STATE_BY_CODE[int(v["vol"])]
    perm, _reasons = t5_permission(
        alignment=alignment,
        poi_bullish=poi_bullish,
        final=final,
        watch_only_min=45,
        high_confluence_min=65,
        downgrade_on_extreme_volatility=True,
        volatility_state=vol_state,
    )

    momentum_aligned = s_momentum >= 60
    liquidity_ok = s_liquidity >= 60
    lc = t5_lifecycle(
        has_structure=True,
        btmm_valid=btmm_valid,
        alignment=alignment,
        favorable_regime=regime in _FAVORABLE_REGIMES,
        momentum_aligned=momentum_aligned,
        liquidity_ok=liquidity_ok,
    )

    return PoiLevel(
        align=ALIGNMENT_CODE[alignment],
        s_trend=s_trend,
        s_regime=s_regime,
        s_momentum=s_momentum,
        s_breakout=s_breakout,
        s_poi=s_poi,
        s_btmm=s_btmm,
        s_liquidity=s_liquidity,
        s_volatility=s_volatility,
        final=final,
        permission=PERMISSION_CODE[perm],
        lifecycle=LIFECYCLE_CODE[lc],
    )


POI_LEVEL_EVAL_FIELDS: tuple[tuple[str, str], ...] = (
    ("align", "align"),
    ("sTrend", "s_trend"),
    ("sRegime", "s_regime"),
    ("sMomentum", "s_momentum"),
    ("sBreakout", "s_breakout"),
    ("sPoi", "s_poi"),
    ("sBtmm", "s_btmm"),
    ("sLiquidity", "s_liquidity"),
    ("sVolatility", "s_volatility"),
    ("final", "final"),
    ("permission", "permission"),
    ("lifecycle", "lifecycle"),
)

_VOLATILITY_STATE_BY_CODE: dict[int, VolatilityState] = {
    0: VolatilityState.VERY_LOW,
    1: VolatilityState.LOW,
    2: VolatilityState.NORMAL,
    3: VolatilityState.HIGH,
    4: VolatilityState.EXTREME,
}

_DIR2_NAME_BY_CODE: dict[int, str] = {v: k for k, v in _DIR2_CODE_BY_NAME.items()}


def _direction_from_code(code: int) -> Direction:
    return Direction(_DIR2_NAME_BY_CODE[code])


def _momentum_direction_from_code(code: int) -> MomentumDirection:
    return MomentumDirection(_DIR2_NAME_BY_CODE[code])


_REGIME_NAME_BY_CODE: dict[int, Regime] = {v: k for k, v in REGIME_CODE.items()}


def _regime_from_code(code: int) -> Regime:
    return _REGIME_NAME_BY_CODE[code]


__all__ = [
    "BAR_LEVEL_EVAL_FIELDS",
    "POI_LEVEL_EVAL_FIELDS",
    "BarLevel",
    "PoiLevel",
    "compute_bar_level",
    "compute_poi_level",
    "p5_transport_record_from_wire",
]
