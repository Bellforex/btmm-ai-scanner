"""RC4 interaction-episode lifecycle contract (author-accepted for RC4 only).

RC3 (frozen): the first qualifying post-availability touch makes a POI
terminal on that bar.

RC4 profile: that first touch OPENS an interaction episode instead. The POI
stays in P5 / P8 evaluation while the BTMM pre-trade cycle is observed
(DISTRACTION before the touch, DELAY inside, WIPEOUT beyond + reclaim) and the
episode ends at the EARLIEST of
  1. true failure  -- beyond the far edge by more than the BTMM overshoot
     tolerance with no reclaim within 3 bars (P8 reason INVALIDATED), or
  2. the end of the 5-bar BTMM reaction window (P8 reason MITIGATED).
A POI invalidated before any touch, or promoted, is terminal at once (RC3).
Exactly one POI_TERMINAL; no event for that POI afterwards.
"""

from __future__ import annotations

from collections import defaultdict
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

import pytest

from btmm_ai_scanner.config.enums import Timeframe
from btmm_ai_scanner.framework import FrameworkTracker, InteractionEpisode
from btmm_ai_scanner.framework.engine import (
    detect_ranges,
    framework_context_for,
    sweep_timeline,
)
from btmm_ai_scanner.poi.enums import PoiTerminalReason
from tests.parity_support.p5_active_poi_loop_model import (
    rc4_is_terminal,
    rc4_terminal_reason,
)
from tests.unit.test_rc4_market_framework import (
    CFG,
    _context,
    _evaluate,
    _flat,
    _touch_rows,
)

MIT = PoiTerminalReason.MITIGATED
INV = PoiTerminalReason.INVALIDATED


# ---- the terminal predicate (truth table) -----------------------------------


@pytest.mark.parametrize(
    ("fresh", "reason", "episode", "terminal", "p8_reason"),
    [
        (True, None, None, False, None),  # untouched: waiting
        (False, MIT, "ACTIVE", False, MIT),  # touched: episode open, evaluable
        (False, MIT, "ENDED", True, MIT),  # window complete
        (False, MIT, "FAILED", True, INV),  # true failure ends it early
        (False, INV, None, True, INV),  # invalidated before any touch (RC3)
        (
            False,
            PoiTerminalReason.PROMOTED_TO_ORDER_BLOCK,
            None,
            True,
            PoiTerminalReason.PROMOTED_TO_ORDER_BLOCK,
        ),
    ],
)
def test_rc4_terminal_truth_table(fresh, reason, episode, terminal, p8_reason) -> None:
    state = SimpleNamespace(fresh_active=fresh, terminal_reason=reason)
    decision = SimpleNamespace(interaction_episode=episode)
    assert rc4_is_terminal(state, decision) is terminal
    assert rc4_terminal_reason(state, decision) == p8_reason


# ---- episode start / end and the penetration matrix -------------------------


def test_episode_start_is_the_first_touch_bar(tmp_path: Path) -> None:
    rows = _touch_rows([(100.5, 100.8, 99.5, 100.4), *_flat(4, 101.0)])
    ctx = _context(rows, tmp_path, "start")
    r = _evaluate(ctx, touch_index=20)
    touch = ctx.candles[20].availability_time_utc
    assert r.first_touch_time_utc == touch
    assert r.episode_start_time_utc == touch
    assert r.episode_end_time_utc == ctx.candles[24].availability_time_utc
    assert r.episode is InteractionEpisode.ENDED


def test_untouched_poi_has_no_episode(tmp_path: Path) -> None:
    r = _evaluate(_context(_flat(25), tmp_path, "none"), touch_index=None)
    assert r.episode is InteractionEpisode.NOT_TOUCHED
    assert r.episode_start_time_utc is None and r.episode_end_time_utc is None


def test_small_penetration_inside_tolerance_is_not_a_wipeout(tmp_path: Path) -> None:
    # ATR ~1.0 -> tolerance min(0.10 ATR, 0.25 * 2.0) ~0.10: a 0.05 poke is noise
    rows = _touch_rows(
        [(100.5, 100.8, 97.95, 99.9), (99.9, 102.0, 99.8, 101.6), *_flat(3, 102.0)]
    )
    r = _evaluate(_context(rows, tmp_path, "small"), touch_index=20)
    assert not r.wipeout and not r.true_failure
    assert r.episode is InteractionEpisode.ENDED


def test_deeper_penetration_with_reclaim_is_a_wipeout_not_a_failure(
    tmp_path: Path,
) -> None:
    rows = _touch_rows(
        [
            (100.5, 100.8, 97.0, 98.4),
            (98.4, 100.2, 98.2, 99.8),
            (99.8, 102.0, 99.7, 101.5),
        ]
    )
    r = _evaluate(_context(rows, tmp_path, "deep"), touch_index=20)
    assert r.wipeout and not r.true_failure and r.pretrade_valid


def test_penetration_without_reclaim_fails_and_ends_the_episode_early(
    tmp_path: Path,
) -> None:
    rows = _touch_rows(
        [
            (100.5, 100.8, 96.0, 96.5),
            (96.5, 97.0, 95.0, 95.5),
            (95.5, 96.0, 94.0, 94.5),
            (94.5, 95.0, 93.0, 93.5),  # 3 bars after penetration, no reclaim
        ]
    )
    ctx = _context(rows, tmp_path, "noreclaim")
    r = _evaluate(ctx, touch_index=20)
    assert r.true_failure and r.episode is InteractionEpisode.FAILED
    # earliest cause wins: bar 23 < the window end (bar 24)
    assert r.episode_end_time_utc == ctx.candles[23].availability_time_utc


def test_continued_acceptance_beyond_stays_failed(tmp_path: Path) -> None:
    rows = _touch_rows(
        [
            (100.5, 100.8, 96.0, 96.5),
            *[(96.0 - k, 96.5 - k, 95.0 - k, 95.5 - k) for k in range(6)],
        ]
    )
    r = _evaluate(_context(rows, tmp_path, "accept"), touch_index=20)
    assert r.true_failure and not r.pretrade_valid and not r.wipeout


def test_a_late_reclaim_does_not_undo_a_failure(tmp_path: Path) -> None:
    rows = _touch_rows(
        [
            (100.5, 100.8, 96.0, 96.5),
            (96.5, 97.0, 95.0, 95.5),
            (95.5, 96.0, 94.0, 94.5),
            (94.5, 95.0, 93.0, 93.5),  # failure fixed here
            (93.5, 101.0, 93.4, 100.8),  # reclaim after the fact
        ]
    )
    r = _evaluate(_context(rows, tmp_path, "late"), touch_index=20)
    assert r.true_failure and not r.wipeout and r.episode is InteractionEpisode.FAILED


# ---- real FXCM data: RC3 vs RC4 profile through the Level-A replay ----------

_DATASET = Path(__file__).resolve().parents[2] / "artifacts" / "v1a_validation"
_BARS = 60


def _run(rc4: bool):
    from tests.parity_support.level_a_replay import iter_level_a_bars
    from tests.parity_support.rc3_daily_authority import (
        WINDOW_START_EVENT_UTC,
        build_authority_configuration,
        load_level_a_window,
    )

    ctx_tfs = (Timeframe.M5, Timeframe.H1, Timeframe.H4, Timeframe.D1, Timeframe.W1)
    window = load_level_a_window(
        _DATASET,
        window_start_event_utc=WINDOW_START_EVENT_UTC,
        host_timeframe=Timeframe.M15,
        context_timeframes=ctx_tfs,
        max_bars=_BARS,
    )
    first_nonfresh: dict[int, int] = {}
    terminal_bars: dict[int, list[int]] = defaultdict(list)
    events_after: list[tuple[int, str]] = []
    episode_open_bars = 0
    host: list = []
    tracker = FrameworkTracker()
    final = None
    for bar in iter_level_a_bars(
        host_timeframe=Timeframe.M15,
        host_series=window.host_series,
        context_series=window.context_series,
        configuration=build_authority_configuration(
            host_timeframe=Timeframe.M15, context_timeframes=ctx_tfs
        ),
        rc3_freshness=True,
        rc4_framework=rc4,
    ):
        host.append(bar.candle)
        if rc4:  # an independent tracker over the same per-bar analyses
            final = framework_context_for(bar.analysis, Timeframe.M15, host, tracker)
            final_analysis = bar.analysis
        for poi_id in bar.evaluated_order:
            state = bar.state_by_id.get(poi_id)
            idx = bar.poi_idx_by_id[poi_id]
            if state is not None and not state.fresh_active:
                first_nonfresh.setdefault(idx, bar.bar_index)
            d = bar.decision_by_id[poi_id]
            if (
                d.interaction_episode == "ACTIVE"
                and state is not None
                and not state.fresh_active
            ):
                episode_open_bars += 1
        last_analysis = bar.analysis
        for ev in bar.events:
            if terminal_bars.get(ev.poi_idx):
                events_after.append((ev.poi_idx, ev.event_type.value))
            if ev.event_type.value == "POI_TERMINAL":
                terminal_bars[ev.poi_idx].append(bar.bar_index)
    fvgs = {
        (str(o.zone_bottom), str(o.zone_top), o.candidate_event_time_utc.isoformat())
        for o in last_analysis.poi_analysis.poi_observations
        if o.poi_type.value.endswith("FAIR_VALUE_GAP")
        and o.source_timeframe is Timeframe.M15
    }
    return {
        "fvgs": fvgs,
        "first_nonfresh": first_nonfresh,
        "terminal_bars": terminal_bars,
        "events_after": events_after,
        "episode_open_bars": episode_open_bars,
        "final_context": final,
        "final_analysis": final_analysis if rc4 else None,
        "host": host,
    }


@pytest.fixture(scope="module")
def runs():
    if not _DATASET.exists():
        pytest.skip("V1-A dataset not present")
    return {"rc3": _run(False), "rc4": _run(True)}


def test_terminal_exactly_once_and_nothing_after(runs) -> None:
    for name, r in runs.items():
        assert all(len(v) == 1 for v in r["terminal_bars"].values()), name
        assert r["events_after"] == [], name


def test_rc3_profile_keeps_first_touch_terminal(runs) -> None:
    r = runs["rc3"]
    assert r["episode_open_bars"] == 0
    for idx, bars in r["terminal_bars"].items():
        assert bars[0] == r["first_nonfresh"][idx]


def test_rc4_profile_opens_an_episode_bounded_by_the_reaction_window(runs) -> None:
    r = runs["rc4"]
    assert r["episode_open_bars"] > 0  # POIs really stay evaluable after the touch
    later = 0
    for idx, bars in r["terminal_bars"].items():
        start = r["first_nonfresh"][idx]
        assert start <= bars[0] <= start + CFG.episode_bars - 1
        later += bars[0] > start
    assert later > 0


def test_rc4_incremental_equals_batch_for_unrevised_levels(runs) -> None:
    """The append-only tracker (incremental) and a from-scratch batch timeline
    over the final swing set agree on every sweep of a swing level both see
    with the same price and availability."""
    r = runs["rc4"]
    ctx = r["final_context"]
    analysis = r["final_analysis"]
    m = next(x for x in analysis.measurement_analyses if x.timeframe is Timeframe.M15)
    s = next(x for x in analysis.structure_analyses if x.timeframe is Timeframe.M15)
    batch = sweep_timeline(
        r["host"],
        m.confirmed_swings,
        (),
        (),
        detect_ranges(s.structure_transitions, CFG),
        CFG,
    )
    swing_ids = {f"S{x.record_id}" for x in m.confirmed_swings}
    inc = {
        (e.level_id, e.bar_index, e.sweep_type, e.level_price)
        for e in ctx.events
        if e.level_id in swing_ids
    }
    bat = {(e.level_id, e.bar_index, e.sweep_type, e.level_price) for e in batch}
    assert inc and inc == bat
    assert Decimal(0) not in {e.level_price for e in batch}


def test_rc4_fvg_quality_is_rc4_only_and_strictly_more_selective(runs) -> None:
    """RC3 keeps every FVG its frozen contract mapped; the RC4 profile maps a
    strict subset (author decision 2026-09-19: displacement + predecessor
    expansion + not already consumed at availability)."""
    rc3, rc4 = runs["rc3"]["fvgs"], runs["rc4"]["fvgs"]
    assert rc4 < rc3, (len(rc3), len(rc4))
