"""The PINE-EQUIVALENT T3 momentum / breakout / pullback classification,
reading ONLY the transport wire.

Test/parity tooling only — nothing in `src/` imports this, and it changes no
production semantics.

WHY NO NEW TRANSPORT FIELD WAS NEEDED FOR ANY OF THE THREE
----------------------------------------------------------
Momentum's window is exactly `DISPLACEMENT_WINDOW_CAPACITY` (3), matching
`MomentumBreakoutPullbackConfiguration.momentum_window`'s own default -- the
same capacity the P6X campaign already sized for T2's regime. Breakout never
reads `equal_level_clusters` at all (LIQUIDITY_SWEEP is deliberately unemitted
in V1 -- see `t3_engine.py`'s own docstring), and the ONE thing it needs from
displacement history -- `_displacement_at`'s MAX classification matched on the
newest transition's availability time -- was already carried as
`dispClsAtTrans`, precomputed by the oracle rather than left for this module
to re-derive from a raw window it does not have. Pullback's three swing prices
(`pbImpulsePrice`/`pbOriginPrice`/`pbPullbackPrice`) and the `pbValid` flag are
likewise the oracle's own `_retracement_depth` output, already reduced to
exactly the three scalars the depth formula needs.

THE PULLBACK FORMULA IS DIRECTION-SYMMETRIC
--------------------------------------------
`_retracement_depth` writes two superficially different formulas for bullish
vs bearish. Substituting the transport's direction-neutral naming (impulse I,
origin O, pullback P) into both reduces to the SAME expression:

* bullish:  depth = (impulse_top - pullback_low)  / (impulse_top - origin_low)   = (I-P)/(I-O)
* bearish:  depth = (pullback_high - impulse_low) / (origin_high - impulse_low)  = (P-I)/(O-I) = (I-P)/(I-O)

So this module never branches on direction to compute depth -- only to decide
whether a pullback applies at all (`p2Dir == DIR_UNDETERMINED` short-circuits,
exactly as T1's own direction gate does). Proven, not just asserted, by the
randomized differential in `test_t3_transport_sufficiency.py`.

THE BREAKOUT WINDOW TRAP, AGAIN
--------------------------------
`ordered_transitions[-2]` (the FAILED_BREAK check's "immediately before") is
`trans{transWindowCount - 1}Type`, not a fixed slot -- the same left-aligned,
count-relative indexing T1's alternation window required. Getting this wrong
silently drops the FAILED_BREAK case for windows that are not exactly full.

MOMENTUM_SCORE AND ACCELERATION CROSS A REAL PRECISION BOUNDARY
-----------------------------------------------------------------
Every other classification in T1/T2/T3 only ever COMPARES the same lossy wire
float on both sides of the differential, which is exact regardless of the
Decimal-vs-float64 gap. `_momentum_score`'s `.to_integral_value()` and
`_acceleration`'s margin comparison are different in kind: they resolve an
EXACT Decimal tie (e.g. `recent_mean == earlier_mean * Decimal("1.15")`), and
an exact tie is exactly the case a float64 cast can perturb by less than one
ULP -- at which point Python's Decimal engine and Pine's own float64 math
(which this module reproduces, since that IS what the wire carries) can
legitimately disagree by the smallest possible amount. Proven bounded, not
unbounded noise, by `test_momentum_score_and_acceleration_tolerance_is_bounded`
in `test_t3_transport_sufficiency.py`: `momentum_score` never differs by more
than 1, and `acceleration` mismatches are always a STEADY<->non-STEADY tie
break, never ACCELERATING<->DECELERATING directly. `t5_engine._weighted_final`
only ever consumes `momentum_score` through `50 + momentum_score // 2`, which
absorbs an odd/even-parity half of all such off-by-ones outright.
"""

from __future__ import annotations

from dataclasses import dataclass

from btmm_ai_scanner.btrc.enums import (
    BreakoutState,
    MomentumAcceleration,
    MomentumDirection,
    PullbackState,
)

from .p5_transport_contract import (
    C_ST_NA,
    DIR_UNDETERMINED,
    DISP_CLS_VERY_FAST,
    DISP_DIR_BULLISH,
    DISPLACEMENT_WINDOW_CAPACITY,
    TR_BEARISH_CHOCH,
    TR_BULLISH_CHOCH,
    TRANSITION_WINDOW_CAPACITY,
    P5TransportRecord,
)

_CHOCH_CODES = (TR_BULLISH_CHOCH, TR_BEARISH_CHOCH)

#: `t3_engine._STRENGTH_BY_CLASSIFICATION`, keyed by the wire's integer
#: classification code (0 NORMAL / 1 FAST / 2 VERY_FAST) rather than the enum,
#: since that is what `dispClsAtTrans` actually carries.
_STRENGTH_BY_CODE: dict[int, tuple[BreakoutState, int]] = {
    0: (BreakoutState.VALID_BREAK, 50),
    1: (BreakoutState.STRONG_BREAK, 75),
    2: (BreakoutState.EXPLOSIVE_BREAK, 90),
}


# ------------------------------------------------------------------ momentum
@dataclass(frozen=True)
class T3MomentumConfig:
    momentum_window: int = 3
    momentum_strong_count: int = 2
    momentum_acceleration_margin: float = 0.15
    momentum_score_reference_ratio: float = 2.00


@dataclass(frozen=True)
class MomentumResult:
    direction: MomentumDirection
    acceleration: MomentumAcceleration
    momentum_score: int
    displacement_count: int


def momentum_from_transport(
    record: P5TransportRecord, config: T3MomentumConfig | None = None
) -> MomentumResult:
    cfg = config or T3MomentumConfig()
    if cfg.momentum_window > DISPLACEMENT_WINDOW_CAPACITY:
        raise ValueError(
            f"momentum_window {cfg.momentum_window} exceeds the transport's "
            f"{DISPLACEMENT_WINDOW_CAPACITY}-slot capacity"
        )
    dirs = [record.disp1Dir, record.disp2Dir, record.disp3Dir][: record.dispWindowCount]
    clses = [record.disp1Cls, record.disp2Cls, record.disp3Cls][: record.dispWindowCount]
    ratios = [record.disp1Ratio, record.disp2Ratio, record.disp3Ratio][
        : record.dispWindowCount
    ]
    # The wire window is LEFT-ALIGNED oldest -> newest, exactly as T1's
    # transition window is; trimming to the last `momentum_window` slots keeps
    # the newest entries, matching `_order_disp(...)[-config.momentum_window:]`.
    window_dirs = dirs[-cfg.momentum_window :] if cfg.momentum_window < len(dirs) else dirs
    window_clses = (
        clses[-cfg.momentum_window :] if cfg.momentum_window < len(clses) else clses
    )
    window_ratios = (
        ratios[-cfg.momentum_window :] if cfg.momentum_window < len(ratios) else ratios
    )
    n = len(window_dirs)

    if n == 0:
        return MomentumResult(
            direction=MomentumDirection.NEUTRAL,
            acceleration=MomentumAcceleration.STEADY,
            momentum_score=0,
            displacement_count=0,
        )

    bull = sum(1 for d in window_dirs if d == DISP_DIR_BULLISH)
    bear = n - bull
    has_very_fast = any(c == DISP_CLS_VERY_FAST for c in window_clses)
    strong = n >= cfg.momentum_strong_count or has_very_fast

    if bull > 0 and bear == 0:
        direction = (
            MomentumDirection.STRONG_BULLISH if strong else MomentumDirection.BULLISH
        )
    elif bear > 0 and bull == 0:
        direction = (
            MomentumDirection.STRONG_BEARISH if strong else MomentumDirection.BEARISH
        )
    elif bull > bear:
        direction = MomentumDirection.BULLISH
    elif bear > bull:
        direction = MomentumDirection.BEARISH
    else:
        direction = MomentumDirection.NEUTRAL

    acceleration = _acceleration(window_ratios, cfg.momentum_acceleration_margin)
    momentum_score = _momentum_score(
        window_ratios, bull, bear, cfg.momentum_score_reference_ratio
    )
    return MomentumResult(direction, acceleration, momentum_score, n)


def _acceleration(ratios: list[float | None], margin: float) -> MomentumAcceleration:
    if len(ratios) < 2:
        return MomentumAcceleration.STEADY
    vals = [r if r is not None else 0.0 for r in ratios]
    mid = len(vals) // 2
    earlier = vals[:mid] or vals[:1]
    recent = vals[mid:]
    earlier_mean = sum(earlier) / len(earlier)
    recent_mean = sum(recent) / len(recent)
    if earlier_mean == 0.0:
        return MomentumAcceleration.STEADY
    if recent_mean > earlier_mean * (1.0 + margin):
        return MomentumAcceleration.ACCELERATING
    if recent_mean < earlier_mean * (1.0 - margin):
        return MomentumAcceleration.DECELERATING
    return MomentumAcceleration.STEADY


def _momentum_score(
    ratios: list[float | None], bull: int, bear: int, reference_ratio: float
) -> int:
    vals = [r if r is not None else 0.0 for r in ratios]
    mean_ratio = sum(vals) / len(vals)
    magnitude = min(1.0, mean_ratio / reference_ratio)
    consistency = max(bull, bear) / len(vals)
    return round(magnitude * consistency * 100.0)


# ------------------------------------------------------------------ breakout
@dataclass(frozen=True)
class BreakoutResult:
    breakout_state: BreakoutState | None
    breakout_score: int


def breakout_from_transport(record: P5TransportRecord) -> BreakoutResult:
    if record.transWindowCount == 0:
        return BreakoutResult(None, 0)

    slots = [record.trans1Type, record.trans2Type, record.trans3Type, record.trans4Type]
    count = min(record.transWindowCount, TRANSITION_WINDOW_CAPACITY)
    populated = slots[:count]
    last = populated[-1]

    if count >= 2:
        prev = populated[-2]
        if last in _CHOCH_CODES and prev in _CHOCH_CODES and prev != last:
            return BreakoutResult(BreakoutState.FAILED_BREAK, 10)

    if record.dispClsAtTrans == C_ST_NA:
        return BreakoutResult(BreakoutState.WEAK_BREAK, 25)
    state, score = _STRENGTH_BY_CODE[record.dispClsAtTrans]
    return BreakoutResult(state, score)


# ------------------------------------------------------------------ pullback
@dataclass(frozen=True)
class T3PullbackConfig:
    pullback_shallow_max: float = 0.382
    pullback_deep_min: float = 0.618


@dataclass(frozen=True)
class PullbackResult:
    pullback_state: PullbackState | None


def pullback_from_transport(
    p2_direction: int,
    record: P5TransportRecord,
    config: T3PullbackConfig | None = None,
) -> PullbackResult:
    cfg = config or T3PullbackConfig()
    if p2_direction == DIR_UNDETERMINED:
        return PullbackResult(None)
    if not record.pbValid:
        return PullbackResult(None)

    impulse = record.pbImpulsePrice
    origin = record.pbOriginPrice
    pullback = record.pbPullbackPrice
    assert impulse is not None and origin is not None and pullback is not None
    depth = (impulse - pullback) / (impulse - origin)

    if depth > 1.0:
        return PullbackResult(PullbackState.STRUCTURAL_FAILURE)
    if depth <= cfg.pullback_shallow_max:
        return PullbackResult(PullbackState.SHALLOW_PULLBACK)
    if depth <= cfg.pullback_deep_min:
        return PullbackResult(PullbackState.HEALTHY_PULLBACK)
    return PullbackResult(PullbackState.DEEP_PULLBACK)
