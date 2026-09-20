"""P2-I8-PRE — consolidation review of the completed bounded Structure walk.

Everything in P2 up to I7 proved one mechanism at a time, or short chains of two.
This file exercises the walk as ONE state machine: composite fixtures that chain
all seven mechanisms in a single stream, a transition-cycle campaign, an
invariant audit, and a left-edge/truncation study that defines what a future
incremental frontier may and may not carry across a window advance.

Test-only. No production semantics are changed here.

THE CENTRAL ARCHITECTURAL FINDING
---------------------------------
Python already has a complete incremental structure engine
(`analyzer.py:478-1300`), and its design does NOT transfer to Pine unchanged:

* Python accumulates the **whole** history (`candles_so_far`) and keeps one
  `_StructureWalkCheckpoint` **per event**, so it can resume from any position.
* It must, because confirmed swings are **not append-only** — "a pending pivot
  can confirm out of order, a plateau representative can change, same-direction
  supersession can rewrite an existing entry" (`analyzer.py:490-494`). So it
  diffs the rebuilt event stream against the prior one, finds the longest
  identical prefix, and resumes from the checkpoint *before the earliest changed
  event*. The append-only case is only a fast path, never an assumption.
* Pine's walk is over a **sliding 300-bar window**. Python never truncates; Pine
  always does. So a Pine frontier has a problem Python does not have: state that
  is legitimately derived from candles which have since left the window.

`test_left_edge_advance_changes_outputs` measures exactly which outputs move when
the left edge advances, which is the list a frontier must be able to reconstruct.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

from btmm_ai_scanner.domain.enums import SwingType


def _load(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(
        name, Path(__file__).with_name(filename)
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


_fx = _load("_p2cons_fixtures", "test_structure_transitions_contract.py")
_bos = _load("_p2cons_bos", "test_p2_bos_parity.py")

_candle = _fx._candle
_swing = _fx._swing
_analyze = _fx._analyze
_pine_walk = _bos._pine_walk
_python_state = _bos._python_state

DIR_BULLISH, DIR_BEARISH = _bos.DIR_BULLISH, _bos.DIR_BEARISH
BULL_BOS, BEAR_BOS, BULL_CHOCH, BEAR_CHOCH = 1, -1, 2, -2
H, L = SwingType.SWING_HIGH, SwingType.SWING_LOW

LONG_BARS = 40


def _long_series(neutral: str, overrides=None):
    overrides = overrides or {}
    bars = []
    for i in range(LONG_BARS):
        spec = overrides.get(i, {})
        bars.append(
            _candle(
                i,
                spec.get("close", neutral),
                spec.get("high"),
                spec.get("low"),
                spec.get("open"),
            )
        )
    return tuple(bars)


def _build_long(specs, neutral, overrides=None):
    candles = _long_series(neutral, overrides)
    swings = tuple(
        _swing(i + 1, t, price, pivot, conf, candles)
        for i, (t, price, pivot, conf) in enumerate(specs)
    )
    return candles, swings


def _key(candles, pivot_bar):
    return candles[pivot_bar].event_time_utc


def _assert_parity(candles, swings):
    """Unified-model parity, reusing the I7 comparison."""
    reference, analysis = _python_state(candles, swings)
    walk = _pine_walk(candles, swings)
    assert walk.state() == reference
    expected = (
        walk.last_change if walk.last_change is not None
        else candles[-1].availability_time_utc
    )
    assert analysis.current_state.availability_time_utc == expected
    return walk, analysis


def _prefix_walks(candles, swings):
    walks = []
    for k in range(1, len(candles) + 1):
        prefix = candles[:k]
        visible = tuple(
            s for s in swings
            if s.meaningful_confirmation_time_utc <= prefix[-1].availability_time_utc
        )
        walks.append(_assert_parity(prefix, visible)[0])
    return walks


# ---------------------------------------------------------------------------
# Phase 6 — composite fixtures: all seven mechanisms in one stream
# ---------------------------------------------------------------------------
#
#   bootstrap BULLISH        (relationships HH + HL)
#   -> BOS #1                (candle 10 breaks the weak high)
#   -> weak re-arm           (H3, pivot 14 > boundary 10)
#   -> BOS #2                (candle 20 breaks the re-armed level)
#   -> CHOCH                 (candle 24 breaks the protected low)
#   -> post-CHOCH re-arm     (L4, pivot 26 > boundary 24)
#   -> post-CHOCH BOS        (candle 30 breaks the re-armed low)

_COMPOSITE_BULL = [
    (L, "100", 2, 3), (H, "110", 4, 5), (L, "102", 6, 7), (H, "112", 8, 9),
    (L, "104", 12, 13), (H, "120", 14, 15),
    (L, "95", 26, 27),
]
_COMPOSITE_BULL_OVR = {
    10: {"close": "113"},      # BOS #1
    20: {"close": "121"},      # BOS #2 on the re-armed high
    24: {"close": "103"},      # CHOCH  (103 < protected low 104)
    30: {"close": "94"},       # BOS #3 on the post-CHOCH re-armed low
}
_COMPOSITE_BULL_NEUTRAL = "105"

# Mirror: bootstrap BEARISH, BOS, re-arm, BOS, CHOCH, re-arm, BOS.
_COMPOSITE_BEAR = [
    (H, "110", 2, 3), (L, "100", 4, 5), (H, "108", 6, 7), (L, "98", 8, 9),
    (H, "106", 12, 13), (L, "90", 14, 15),
    (H, "130", 26, 27),
]
_COMPOSITE_BEAR_OVR = {
    10: {"close": "97"},
    20: {"close": "89"},
    24: {"close": "107"},
    30: {"close": "131"},
}
_COMPOSITE_BEAR_NEUTRAL = "103"


def test_composite_bullish_stream_reaches_all_seven_mechanisms() -> None:
    candles, swings = _build_long(
        _COMPOSITE_BULL, _COMPOSITE_BULL_NEUTRAL, _COMPOSITE_BULL_OVR
    )
    walks = _prefix_walks(candles, swings)
    final = walks[-1]

    codes = [t[0] for t in final.transitions]
    assert codes == [BULL_BOS, BULL_BOS, BEAR_CHOCH, BEAR_BOS], codes

    # 1 bootstrap
    assert any(w.direction == DIR_BULLISH for w in walks)
    # 2/4 two bullish BOS against DIFFERENT weak highs
    assert final.transitions[0][1] == _key(candles, 8)
    assert final.transitions[1][1] == _key(candles, 14), "the re-armed high"
    # 3 the re-arm between them
    high_trace = [w.weak_high for w in walks]
    high_distinct = [
        k for i, k in enumerate(high_trace) if i == 0 or k != high_trace[i - 1]
    ]
    assert high_distinct == [
        None, _key(candles, 8), None, _key(candles, 14), None
    ], high_distinct
    # 5 the CHOCH, which flips direction and consumes the protected low
    assert final.transitions[2][1] == _key(candles, 6 + 6), "protected low = L3"
    assert final.direction == DIR_BEARISH
    # 6 post-CHOCH re-arm on the LOW side
    low_trace = [w.weak_low for w in walks]
    low_distinct = [
        k for i, k in enumerate(low_trace) if i == 0 or k != low_trace[i - 1]
    ]
    assert low_distinct == [None, _key(candles, 26), None], low_distinct
    # 7 post-CHOCH BOS on that re-armed low
    assert final.transitions[3][1] == _key(candles, 26)


def test_composite_bearish_stream_reaches_all_seven_mechanisms() -> None:
    candles, swings = _build_long(
        _COMPOSITE_BEAR, _COMPOSITE_BEAR_NEUTRAL, _COMPOSITE_BEAR_OVR
    )
    walks = _prefix_walks(candles, swings)
    final = walks[-1]

    codes = [t[0] for t in final.transitions]
    assert codes == [BEAR_BOS, BEAR_BOS, BULL_CHOCH, BULL_BOS], codes
    assert final.direction == DIR_BULLISH
    low_trace = [w.weak_low for w in walks]
    low_distinct = [
        k for i, k in enumerate(low_trace) if i == 0 or k != low_trace[i - 1]
    ]
    assert low_distinct == [None, _key(candles, 8), None, _key(candles, 14), None]
    high_trace = [w.weak_high for w in walks]
    assert _key(candles, 26) in high_trace, "post-CHOCH re-arm on the HIGH side"


def test_composite_streams_have_zero_prefix_mismatches() -> None:
    for specs, neutral, overrides in (
        (_COMPOSITE_BULL, _COMPOSITE_BULL_NEUTRAL, _COMPOSITE_BULL_OVR),
        (_COMPOSITE_BEAR, _COMPOSITE_BEAR_NEUTRAL, _COMPOSITE_BEAR_OVR),
    ):
        candles, swings = _build_long(specs, neutral, overrides)
        walks = _prefix_walks(candles, swings)
        assert len(walks) == LONG_BARS


# ---------------------------------------------------------------------------
# Phase 7 — transition-cycle campaign
# ---------------------------------------------------------------------------

_CAMPAIGN = {
    "composite_bull": (_COMPOSITE_BULL, _COMPOSITE_BULL_NEUTRAL, _COMPOSITE_BULL_OVR),
    "composite_bear": (_COMPOSITE_BEAR, _COMPOSITE_BEAR_NEUTRAL, _COMPOSITE_BEAR_OVR),
    # Two direction changes in one stream: CHOCH, then CHOCH back.
    "double_flip": (
        [(L, "200", 2, 3), (H, "50", 4, 5), (L, "210", 6, 7), (H, "60", 8, 9)],
        "100",
        None,
    ),
    "bull_cycle_only": (
        [(L, "100", 2, 3), (H, "110", 4, 5), (L, "102", 6, 7), (H, "112", 8, 9),
         (L, "104", 12, 13), (H, "120", 14, 15)],
        "105",
        {10: {"close": "113"}, 20: {"close": "121"}},
    ),
    "bear_cycle_only": (
        [(H, "110", 2, 3), (L, "100", 4, 5), (H, "108", 6, 7), (L, "98", 8, 9),
         (H, "106", 12, 13), (L, "90", 14, 15)],
        "103",
        {10: {"close": "97"}, 20: {"close": "89"}},
    ),
    "quiet": (
        [(L, "100", 2, 3), (H, "110", 4, 5), (L, "102", 6, 7), (H, "112", 8, 9)],
        "105",
        None,
    ),
}


@pytest.mark.parametrize("name", sorted(_CAMPAIGN))
def test_campaign_prefix_parity(name: str) -> None:
    specs, neutral, overrides = _CAMPAIGN[name]
    candles, swings = _build_long(specs, neutral, overrides)
    _prefix_walks(candles, swings)


def _campaign_totals():
    totals = {
        "scenarios": 0, "prefixes": 0, "bull_bos": 0, "bear_bos": 0,
        "bull_choch": 0, "bear_choch": 0, "re_arms": 0, "flips": 0,
        "max_transitions": 0,
    }
    for specs, neutral, overrides in _CAMPAIGN.values():
        candles, swings = _build_long(specs, neutral, overrides)
        walks = _prefix_walks(candles, swings)
        totals["scenarios"] += 1
        totals["prefixes"] += len(walks)
        final = walks[-1]
        totals["max_transitions"] = max(
            totals["max_transitions"], len(final.transitions)
        )
        for code, *_ in final.transitions:
            totals[
                {BULL_BOS: "bull_bos", BEAR_BOS: "bear_bos",
                 BULL_CHOCH: "bull_choch", BEAR_CHOCH: "bear_choch"}[code]
            ] += 1
        previous = walks[0]
        for walk in walks[1:]:
            for before, after in (
                (previous.weak_high, walk.weak_high),
                (previous.weak_low, walk.weak_low),
            ):
                if before is None and after is not None and previous.transitions:
                    totals["re_arms"] += 1
            if walk.direction != previous.direction and previous.direction != 0:
                totals["flips"] += 1
            previous = walk
    return totals


def test_campaign_totals_and_diversity() -> None:
    """Diversity guard — the campaign must exercise the STATE MACHINE, not a
    single predicate. Every mode must be reached."""
    t = _campaign_totals()
    assert t["scenarios"] == 6
    assert t["prefixes"] == 6 * LONG_BARS == 240
    assert t["bull_bos"] > 0, t
    assert t["bear_bos"] > 0, t
    assert t["bull_choch"] > 0, t
    assert t["bear_choch"] > 0, t
    assert t["re_arms"] > 0, t
    assert t["flips"] > 0, t
    assert t["max_transitions"] >= 4, t


def test_at_least_one_scenario_has_multiple_direction_changes() -> None:
    multi = 0
    for specs, neutral, overrides in _CAMPAIGN.values():
        candles, swings = _build_long(specs, neutral, overrides)
        walks = _prefix_walks(candles, swings)
        flips = sum(
            1 for a, b in zip(walks, walks[1:], strict=False)
            if a.direction != b.direction and a.direction != 0
        )
        multi = max(multi, flips)
    assert multi >= 2, multi


def test_repeat_same_direction_bos_after_re_arm_is_reached() -> None:
    candles, swings = _build_long(*[
        _CAMPAIGN["bull_cycle_only"][i] for i in (0, 1, 2)
    ])
    walk, _ = _assert_parity(candles, swings)
    codes = [t[0] for t in walk.transitions]
    assert codes == [BULL_BOS, BULL_BOS], codes
    assert walk.transitions[0][1] != walk.transitions[1][1]


# ---------------------------------------------------------------------------
# Phase 8 — state-invariant audit
# ---------------------------------------------------------------------------

def _all_walks():
    for specs, neutral, overrides in _CAMPAIGN.values():
        candles, swings = _build_long(specs, neutral, overrides)
        yield candles, swings, _prefix_walks(candles, swings)


def test_invariant_weak_key_is_never_in_broken_keys() -> None:
    for _c, _s, walks in _all_walks():
        for w in walks:
            assert w.weak_high not in w.broken or w.weak_high is None
            assert w.weak_low not in w.broken or w.weak_low is None


def test_invariant_active_protected_key_is_never_broken() -> None:
    for _c, _s, walks in _all_walks():
        for w in walks:
            for key in (w.protected_high, w.protected_low):
                if key is not None:
                    assert key not in w.broken


def test_invariant_every_transition_broken_key_is_recorded_as_broken() -> None:
    for _c, _s, walks in _all_walks():
        for w in walks:
            for _code, broken, *_rest in w.transitions:
                assert broken in w.broken


def test_invariant_no_swing_is_consumed_twice() -> None:
    for _c, _s, walks in _all_walks():
        for w in walks:
            assert len(w.broken) == len(set(w.broken))
            assert len(w.broken) == len(w.transitions)


def test_invariant_bos_never_changes_direction_choch_always_does() -> None:
    for _c, _s, walks in _all_walks():
        previous = walks[0]
        for w in walks[1:]:
            new = w.transitions[len(previous.transitions):]
            if not new:
                assert w.direction == previous.direction or previous.direction == 0
            for code, *_ in new:
                if code in (BULL_BOS, BEAR_BOS):
                    assert w.direction == previous.direction
                else:
                    assert w.direction != previous.direction
            previous = w


def test_invariant_boundaries_never_move_backwards() -> None:
    for _c, _s, walks in _all_walks():
        previous = walks[0]
        for w in walks[1:]:
            assert w.weak_high_boundary >= previous.weak_high_boundary
            assert w.weak_low_boundary >= previous.weak_low_boundary
            previous = w


def test_invariant_a_re_arm_never_moves_a_boundary() -> None:
    for _c, _s, walks in _all_walks():
        previous = walks[0]
        for w in walks[1:]:
            armed = (
                (previous.weak_high is None and w.weak_high is not None)
                or (previous.weak_low is None and w.weak_low is not None)
            )
            if armed and len(w.transitions) == len(previous.transitions):
                assert w.weak_high_boundary == previous.weak_high_boundary
                assert w.weak_low_boundary == previous.weak_low_boundary
            previous = w


def test_invariant_bullish_implies_a_protected_low_once_bootstrapped() -> None:
    """CONDITIONAL: true after bootstrap, and it is exactly what makes the TD-A
    fallback unreachable."""
    for _c, _s, walks in _all_walks():
        for w in walks:
            if w.direction == DIR_BULLISH:
                assert w.protected_low is not None
                assert w.protected_high is None
            if w.direction == DIR_BEARISH:
                assert w.protected_high is not None
                assert w.protected_low is None


def test_invariant_latest_transition_is_the_last_emitted() -> None:
    for candles, swings, walks in _all_walks():
        _model, analysis = _assert_parity(candles, swings)
        if analysis.structure_transitions:
            assert analysis.current_state.latest_transition_id == (
                analysis.structure_transitions[-1].record_id
            )
        else:
            assert analysis.current_state.latest_transition_id is None
        del walks


def test_invariant_no_transition_references_an_unavailable_swing() -> None:
    for candles, swings, _walks in _all_walks():
        _model, analysis = _assert_parity(candles, swings)
        by_id = {s.record_id: s for s in swings}
        candle_by_id = {c.record_id: c for c in candles}
        for t in analysis.structure_transitions:
            broken = by_id[t.broken_swing_id]
            protected = by_id[t.protected_swing_id]
            break_candle = candle_by_id[t.break_candle_id]
            assert broken.meaningful_confirmation_time_utc <= (
                break_candle.availability_time_utc
            )
            assert protected.meaningful_confirmation_time_utc <= (
                break_candle.availability_time_utc
            )


# ---------------------------------------------------------------------------
# Phase 9 — left-edge / truncation study
# ---------------------------------------------------------------------------

def _window(candles, swings, start):
    """Simulate the sliding window: drop the leftmost `start` candles and every
    swing whose pivot has fallen out of the retained candle range."""
    kept_candles = candles[start:]
    kept_swings = tuple(s for s in swings if s.pivot_bar_index >= start)
    return kept_candles, kept_swings


def test_left_edge_advance_changes_outputs() -> None:
    """THE measurement a frontier design needs: which outputs move when the left
    edge advances, with the SAME final candle.

    Every truncation is still internally consistent (Pine and Python agree), but
    the RESULT differs from the untruncated run — so this state is legitimately
    window-dependent and a frontier must be able to reconstruct it, not assume it
    carries over.
    """
    candles, swings = _build_long(
        _COMPOSITE_BULL, _COMPOSITE_BULL_NEUTRAL, _COMPOSITE_BULL_OVR
    )
    full, _ = _assert_parity(candles, swings)

    changed: dict[str, int] = {}
    truncations = 0
    for start in (2, 6, 10, 14, 20, 24, 28):
        kept_candles, kept_swings = _window(candles, swings, start)
        if not kept_swings:
            continue
        walk, _ = _assert_parity(kept_candles, kept_swings)
        truncations += 1
        for field in ("direction", "protected_high", "protected_low",
                      "weak_high", "weak_low", "weak_high_boundary",
                      "weak_low_boundary"):
            if getattr(walk, field) != getattr(full, field):
                changed[field] = changed.get(field, 0) + 1
        if len(walk.transitions) != len(full.transitions):
            changed["transitions"] = changed.get("transitions", 0) + 1
        if walk.broken != full.broken:
            changed["broken"] = changed.get("broken", 0) + 1

    assert truncations >= 5, truncations
    # Every one of these is window-dependent in practice, which is the point.
    assert "direction" in changed, changed
    assert "transitions" in changed, changed
    assert "broken" in changed, changed
    assert changed, "truncation must actually change something"


def test_every_truncation_is_still_internally_consistent() -> None:
    """Pine and Python agree on each truncated window even though the windows
    disagree with each other — bounded semantics are self-consistent."""
    for specs, neutral, overrides in _CAMPAIGN.values():
        candles, swings = _build_long(specs, neutral, overrides)
        for start in range(0, LONG_BARS, 4):
            kept_candles, kept_swings = _window(candles, swings, start)
            if len(kept_candles) < 2:
                continue
            _assert_parity(kept_candles, kept_swings)


def test_boundary_indices_are_absolute_not_window_relative() -> None:
    """A frontier hazard: the boundary is compared against `pivot_bar_index`,
    which is an index into the SUPPLIED candle tuple. Re-basing the window
    re-bases both, so the comparison stays valid — but a persisted raw boundary
    would silently mean a different bar after the window slides.
    """
    candles, swings = _build_long(
        _COMPOSITE_BULL, _COMPOSITE_BULL_NEUTRAL, _COMPOSITE_BULL_OVR
    )
    full, _ = _assert_parity(candles, swings)
    shifted_candles, shifted_swings = _window(candles, swings, 2)
    shifted, _ = _assert_parity(shifted_candles, shifted_swings)

    assert full.weak_low_boundary >= 0
    assert shifted.weak_low_boundary >= 0
    assert shifted.weak_low_boundary != full.weak_low_boundary, (
        "the same structural break carries a different index after a re-base — "
        "a persisted boundary must be re-based or stored as a stable key"
    )
