"""PHASE 3-6 of MEGA-AUTONOMOUS-20: does the proven momentum_score ±1
high-precision-vs-wire-normalized gap ever change a CANONICAL P5 decision?

RESULT: YES, ADVERSARIALLY REACHABLE. See
`docs/architecture/BTRC_V1_P5_FLOAT64_BOUNDARY_CLASSIFICATION.md` for the
full report. This file is the permanent, exhaustive, computed evidence for
that finding -- not a sampled estimate.

This does NOT mean the ±1 raw score commonly flips a real decision (the
search below intentionally explores every ACHIEVABLE-but-not-necessarily
CO-OCCURRING combination of component scores, adversarially, per the
project's own Phase 5 instruction: "construct cases where all other
component contributions place the total as close as possible to 45/65").
It means the theoretical possibility cannot be dismissed by a magnitude
argument alone (weight 1 of 13 "sounds small" but the rounding boundary is
exactly 1 unit of the weighted numerator away in the worst case) and must be
stated as a real, bounded risk rather than asserted away.
"""

from __future__ import annotations

from tests.parity_support.p5_float64_boundary_study import (
    ACHIEVABLE,
    OTHER_KEYS,
    search_for_boundary_crossings,
)


def test_achievable_score_sets_match_their_source_tables() -> None:
    """Pins the achievable-value claim itself, since the whole search is only
    as trustworthy as these sets are accurate."""
    assert ACHIEVABLE["trend"] == (20, 50, 60, 80, 100)
    assert ACHIEVABLE["regime"] == (30, 35, 40, 45, 50, 65, 80, 90)
    assert ACHIEVABLE["breakout"] == (10, 25, 40, 50, 75, 90)
    assert ACHIEVABLE["poi"] == (50, 60, 85)
    assert ACHIEVABLE["btmm"] == (25, 70, 85)
    assert ACHIEVABLE["liquidity"] == (40, 60)
    assert ACHIEVABLE["volatility"] == (20, 40, 50, 60, 75, 100)
    assert set(OTHER_KEYS) == set(ACHIEVABLE)


def test_exhaustive_boundary_crossing_search_is_reproducible_and_nonempty() -> None:
    """The definitive computed answer for Phase 6's classification. A nonempty
    result here means classification B applies (per the project's own
    Phase 6 rule): wire difference CAN change canonical output. This is
    reported, not silently absorbed into a false 'A: invariant' claim."""
    findings = search_for_boundary_crossings(bands=(45, 65))
    assert len(findings) > 0, (
        "if this ever becomes 0, the boundary-sensitivity finding no longer "
        "holds and BTRC_V1_P5_FLOAT64_BOUNDARY_CLASSIFICATION.md needs revision"
    )
    # A concrete, reproduced witness -- not just a count -- so the finding
    # stays falsifiable rather than a magic number.
    witness = findings[0]
    assert witness.raw_momentum_b == witness.raw_momentum_a + 1
    assert witness.final_a != witness.final_b
    assert (witness.final_a >= 45) != (witness.final_b >= 45) or (
        witness.final_a >= 65
    ) != (witness.final_b >= 65)


def test_every_crossing_is_explained_by_exactly_a_one_point_final_shift() -> None:
    """The mechanism claim, checked directly: every reported crossing has
    |final_a - final_b| == 1 -- never more, since a single raw-score delta of
    1 can change the T5 momentum component by at most 1, which (at weight 1)
    can change `weighted` by at most 1, which can change `round(weighted/13)`
    by at most 1. A crossing with a larger delta would indicate a bug in the
    search, not a bigger real-world risk."""
    findings = search_for_boundary_crossings(bands=(45, 65))
    assert findings
    for f in findings:
        assert abs(f.final_a - f.final_b) == 1, f
