"""PHASE 3-6: does the momentum Decimal-exact-vs-float64-wire representational
gap ever change a CANONICAL P5 decision (permission band / lifecycle), or is
it confined to the raw `momentum_score` diagnostic?

Test/parity tooling only — nothing in `src/` imports this, and it changes no
production semantics.

THE TWO SEPARATE BOUNDARIES, NAMED
--------------------------------------
1. **Wire parity** (Python-replay-of-the-P6-wire vs actual Pine): this is an
   IMPLEMENTATION requirement, not a representational limit -- Pine's port
   must implement banker's rounding by hand (never call `math.round`, which
   rounds ties away from zero), matching this repo's own `p2_digest.pine_round`
   precedent. Made exact by construction once implemented correctly; not what
   this module studies.
2. **High-precision vs wire-normalized** (original exact-Decimal Python vs the
   SAME data cast through the P6 wire's float64 encoding): the fundamentally
   unavoidable gap `test_t3_transport_sufficiency.py` already bounded --
   `momentum_score` (raw T3 score, 0-100) off by at most 1, `direction` always
   exact, `acceleration` only ties into STEADY. THIS is what this module
   studies: does that raw ±1 ever reach a canonical T5 decision?

WHY THIS IS A COMPUTED SEARCH, NOT A MANUAL PROOF
------------------------------------------------------
`t5_engine._weighted_final` rounds `weighted / total_weight` to the nearest
integer. A momentum-score shift of exactly 1 changes the T5 CONFLUENCE
momentum component (`50 +/- raw // 2`) by at most 1 (and, because of the
floor division's parity, by exactly 1 only on roughly half of all raw
values) -- and momentum's default weight is 1, so IN THE ABSTRACT a ±1 shift
in the weighted numerator absolutely CAN move `round(weighted/13)` across an
integer boundary (13 is odd, so exact .5 ties never occur, but the rounding
boundary is still just 1 unit of `weighted` away in the worst case). Whether
that abstract possibility is actually REACHABLE depends on whether the OTHER
seven components' own DISCRETE, SOURCE-DEFINED achievable score sets (not an
unconstrained 0-100 integer) can land the total exactly 1 unit short of the
44.5/64.5 rounding boundary. That is a combinatorial question with roughly
5 x 8 x 6 x 3 x 3 x 2 x 6 ~= 26,000 combinations -- small enough to brute-force
exhaustively rather than argue about informally.

ACHIEVABLE SCORE SETS, EACH TRACED TO ITS SOURCE TABLE
-----------------------------------------------------------
* trend  : {20, 50, 60, 80, 100}            -- COUNTER_TREND/NEUTRAL/PARTIAL/ALIGNED(plain)/ALIGNED(strong)
* regime : {30, 35, 40, 45, 50, 65, 80, 90}  -- t5_engine._REGIME_SCORE, all 8 Regime members
* breakout: {10, 25, 40, 50, 75, 90}         -- FAILED/WEAK/missing/VALID/STRONG/EXPLOSIVE
* poi    : {50, 60, 85}                      -- missing-tier/STANDARD/STRONG
* btmm   : {25, 70, 85}                      -- invalid/valid-opposing/valid-agreeing
* liquidity: {40, 60}                        -- placeholder, btmm_valid False/True
* volatility: {20, 40, 50, 60, 75, 100}      -- EXTREME/VERY_LOW/missing/HIGH/LOW/NORMAL
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import cache
from itertools import product

from btmm_ai_scanner.btrc.enums import MomentumDirection, TrendAlignment
from btmm_ai_scanner.btrc.t5_configuration import ConfluenceConfiguration

from .t5_aggregator_pine_model import weighted_final
from .t5_component_scores_pine_model import momentum_score as confluence_momentum_score

ACHIEVABLE: dict[str, tuple[int, ...]] = {
    "trend": (20, 50, 60, 80, 100),
    "regime": (30, 35, 40, 45, 50, 65, 80, 90),
    "breakout": (10, 25, 40, 50, 75, 90),
    "poi": (50, 60, 85),
    "btmm": (25, 70, 85),
    "liquidity": (40, 60),
    "volatility": (20, 40, 50, 60, 75, 100),
}
#: The seven non-momentum keys, order fixed for reproducible iteration.
OTHER_KEYS: tuple[str, ...] = (
    "trend", "regime", "breakout", "poi", "btmm", "liquidity", "volatility",
)
_CFG = ConfluenceConfiguration()
_WEIGHTS = dict(_CFG.weights)
_MAX_KNOWN_RAW_DELTA = 1  # test_t3_transport_sufficiency.py's proven bound


@dataclass(frozen=True)
class BoundaryCase:
    others: dict[str, int]
    raw_momentum_a: int
    raw_momentum_b: int
    momentum_direction: MomentumDirection
    poi_bullish: bool
    alignment: TrendAlignment
    final_a: int
    final_b: int
    permission_boundary_crossed: bool


def _others_weighted(others: dict[str, int]) -> int:
    return sum(others[k] * _WEIGHTS.get(k, 0) for k in OTHER_KEYS)


def _final_for(
    others: dict[str, int],
    raw_momentum: int,
    momentum_direction: MomentumDirection,
    poi_bullish: bool,
) -> int:
    m = confluence_momentum_score(momentum_direction, raw_momentum, poi_bullish)
    values = dict(others)
    values["momentum"] = m
    return weighted_final(values, _WEIGHTS)


def _crosses_band(a: int, b: int, bands: tuple[int, ...]) -> bool:
    """True if `a` and `b` fall on opposite sides of any `>=` band edge."""
    return any((a >= band) != (b >= band) for band in bands)


@cache
def search_for_boundary_crossings(
    bands: tuple[int, ...] = (45, 65),
) -> tuple[BoundaryCase, ...]:
    """Exhaustive (not sampled) search over every achievable combination of
    the seven other components x every raw T3 momentum score in [0, 100] x
    the known max wire delta, for both momentum directions and both POI
    sides. Direction and alignment do not depend on the momentum score at
    all (proven exact / independently derived respectively), so they are
    fixed per search rather than needlessly cross-multiplied -- the
    permission-boundary-crossing question is entirely about `final`.
    """
    findings: list[BoundaryCase] = []
    combos = list(product(*(ACHIEVABLE[k] for k in OTHER_KEYS)))
    directions = (MomentumDirection.BULLISH, MomentumDirection.STRONG_BULLISH, MomentumDirection.NEUTRAL)
    for combo in combos:
        others = dict(zip(OTHER_KEYS, combo, strict=True))
        for raw_a in range(0, 100 - _MAX_KNOWN_RAW_DELTA + 1):
            raw_b = raw_a + _MAX_KNOWN_RAW_DELTA
            for direction in directions:
                for poi_bullish in (True, False):
                    final_a = _final_for(others, raw_a, direction, poi_bullish)
                    final_b = _final_for(others, raw_b, direction, poi_bullish)
                    if final_a != final_b and _crosses_band(final_a, final_b, bands):
                        findings.append(
                            BoundaryCase(
                                others=others,
                                raw_momentum_a=raw_a,
                                raw_momentum_b=raw_b,
                                momentum_direction=direction,
                                poi_bullish=poi_bullish,
                                alignment=TrendAlignment.ALIGNED,  # see module docstring
                                final_a=final_a,
                                final_b=final_b,
                                permission_boundary_crossed=True,
                            )
                        )
    return tuple(findings)
