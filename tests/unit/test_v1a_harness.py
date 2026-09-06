"""Protocol §17 determinism/integrity tests for the V1-A per-bar replay
driver (``tests/parity_support/v1a_harness.py``).

These tests deliberately use a SMALL bar count / lookback (a handful of
seconds each) — the harness's own wall-clock cost on the full 2903-bar DEV
set is a separate, long-running characterization run
(``tests/parity_support/v1a_run_dev.py``), not something a unit test suite
should pay for on every invocation.
"""

from __future__ import annotations

import dataclasses
import hashlib
import json
from pathlib import Path

import pytest

from btmm_ai_scanner.config.enums import Timeframe
from btmm_ai_scanner.historical_backtest.identity import (
    ContentAddressedIdentityProvider,
)
from btmm_ai_scanner.scanner.configuration import ReplayConfiguration
from btmm_ai_scanner.scanner.enums import SnapshotRetentionPolicy
from btmm_ai_scanner.scanner.replay import run_scanner_replay
from btmm_ai_scanner.scanner.timeframe_input import ScannerTimeframeInput
from tests.parity_support.v1a_csv_loader import (
    load_dev_bounded_context_capped,
    load_dev_only_m15,
)
from tests.parity_support.v1a_harness import (
    _CONTEXT_TIMEFRAMES,
    _merge_context_group,
    build_scanner_configuration,
    run_dev_replay,
)

_ROOT = Path(__file__).resolve().parents[2] / "artifacts" / "v1a_validation"
_SMALL_BARS = 12
_SMALL_LOOKBACK = 15


def _skip_if_no_data() -> None:
    if not (_ROOT / "v1a_raw_ohlc_full_loaded.csv").is_file():
        pytest.skip("V1-A raw OHLC artifacts not present on disk.")


def _canonical_events_digest(events: list) -> str:
    payload = json.dumps(
        [dataclasses.asdict(e) for e in events], sort_keys=True, default=str
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _canonical_registry_digest(registry: dict) -> str:
    rows = []
    for entry in registry.values():
        d = dataclasses.asdict(entry)
        d["record_id"] = str(d["record_id"])
        d["availability_time_utc"] = d["availability_time_utc"].isoformat()
        d["zone_top"] = str(d["zone_top"])
        d["zone_bottom"] = str(d["zone_bottom"])
        rows.append(d)
    payload = json.dumps(rows, sort_keys=True, default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# Determinism (protocol §17): running the pipeline twice over the same input
# must produce byte-identical output records and identical digests.
# ---------------------------------------------------------------------------


def test_dev_replay_is_deterministic_across_two_runs() -> None:
    _skip_if_no_data()
    result_a = run_dev_replay(
        dataset_root=_ROOT, pre_dev_lookback_bars=_SMALL_LOOKBACK, max_bars=_SMALL_BARS
    )
    result_b = run_dev_replay(
        dataset_root=_ROOT, pre_dev_lookback_bars=_SMALL_LOOKBACK, max_bars=_SMALL_BARS
    )
    assert _canonical_events_digest(result_a.events) == _canonical_events_digest(result_b.events)
    assert _canonical_registry_digest(result_a.poi_registry) == _canonical_registry_digest(
        result_b.poi_registry
    )
    assert result_a.atr_series == result_b.atr_series


# ---------------------------------------------------------------------------
# Kernel-driven substitution proven equivalent to the frozen protocol's own
# named recipe (SnapshotRetentionPolicy.ALL via run_scanner_replay).
# ---------------------------------------------------------------------------


def test_kernel_driven_matches_all_retention_replay() -> None:
    """Proves the harness's kernel-driven per-bar walk (used for tractable
    wall-clock -- see v1a_harness module docstring) produces the SAME
    ScannerAnalysis the frozen protocol's own named mechanism
    (``run_scanner_replay`` + ``SnapshotRetentionPolicy.ALL``) would, on a
    real slice of the DEV data, across every M15-aligned availability
    group."""
    _skip_if_no_data()
    n = 10
    lookback = 10
    dev = load_dev_only_m15(_ROOT)[:n]
    context = load_dev_bounded_context_capped(_ROOT, pre_dev_lookback_bars=lookback)
    bound = dev[-1].availability_time_utc
    bundles = [ScannerTimeframeInput(timeframe=Timeframe.M15, candles=dev)]
    for tf in _CONTEXT_TIMEFRAMES:
        candles = tuple(c for c in context[tf] if c.availability_time_utc <= bound)
        if candles:
            bundles.append(ScannerTimeframeInput(timeframe=tf, candles=candles))

    config = build_scanner_configuration()
    replay_config = ReplayConfiguration(
        snapshot_retention=SnapshotRetentionPolicy.ALL, verify_against_direct_batch=False
    )
    all_retention_result = run_scanner_replay(
        tuple(bundles), (), config, replay_config, ContentAddressedIdentityProvider()
    )
    m15_availabilities = {c.availability_time_utc for c in dev}
    all_retention_by_time = {
        snap.availability_time_utc: snap
        for snap in all_retention_result.snapshots
        if snap.availability_time_utc in m15_availabilities
    }
    assert len(all_retention_by_time) == n

    # Kernel-driven walk, mirroring run_dev_replay's own per-bar loop but
    # inline here (small scale) so the comparison is apples-to-apples.
    from btmm_ai_scanner.scanner.replay import IncrementalReplayKernel
    from tests.parity_support.v1a_harness import _TRACKED_TIMEFRAMES

    kernel = IncrementalReplayKernel(
        _TRACKED_TIMEFRAMES, config, ContentAddressedIdentityProvider(), ()
    )
    pointers = {tf: 0 for tf in _CONTEXT_TIMEFRAMES}
    context_sorted = {
        tf: sorted(
            (c for c in context[tf] if c.availability_time_utc <= bound),
            key=lambda c: c.availability_time_utc,
        )
        for tf in _CONTEXT_TIMEFRAMES
    }
    for candle in dev:
        group = _merge_context_group(context_sorted, pointers, candle.availability_time_utc)
        group = dict(group)
        group[Timeframe.M15] = (candle,)
        kernel.advance_group(group)
        snapshot = kernel.finalize()
        oracle_snapshot = all_retention_by_time[candle.availability_time_utc]

        kernel_dump = json.dumps(snapshot.model_dump(mode="json"), sort_keys=True, default=str)
        oracle_dump = json.dumps(
            oracle_snapshot.model_dump(mode="json"), sort_keys=True, default=str
        )
        assert kernel_dump == oracle_dump, (
            f"kernel-driven snapshot diverges from SnapshotRetentionPolicy.ALL "
            f"at {candle.availability_time_utc.isoformat()}"
        )


# ---------------------------------------------------------------------------
# Lookahead-injection mutation MUST be caught (protocol §17).
# ---------------------------------------------------------------------------


def test_merge_context_group_never_returns_a_future_candle() -> None:
    """Directed + mutation test on the exact boundary primitive the harness
    uses to gate every context candle: ``_merge_context_group`` must never
    return a candle whose own availability_time_utc exceeds the bound."""
    _skip_if_no_data()
    context = load_dev_bounded_context_capped(_ROOT, pre_dev_lookback_bars=5)
    h1 = context[Timeframe.H1]
    assert len(h1) >= 3
    bound = h1[1].availability_time_utc  # deliberately mid-series

    pointers = {tf: 0 for tf in _CONTEXT_TIMEFRAMES}
    group = _merge_context_group({Timeframe.H1: h1}, pointers, bound)
    returned = group.get(Timeframe.H1, ())
    assert all(c.availability_time_utc <= bound for c in returned)
    assert h1[2] not in returned  # the next (future-relative-to-bound) candle

    # Mutation: a lookahead bug that used `<` on the WRONG side (i.e. bound
    # computed one bar too far forward) would leak an extra future candle --
    # prove this scenario is distinguishable from the correct one.
    bugged_bound = h1[2].availability_time_utc
    pointers_bugged = {tf: 0 for tf in _CONTEXT_TIMEFRAMES}
    bugged_group = _merge_context_group({Timeframe.H1: h1}, pointers_bugged, bugged_bound)
    bugged_returned = bugged_group.get(Timeframe.H1, ())
    assert len(bugged_returned) != len(returned)
    assert h1[2] in bugged_returned


def test_lookahead_injection_changes_the_final_snapshot() -> None:
    """Direct proof that feeding a bar EARLY (before its own availability
    would allow) changes the produced ScannerAnalysis relative to the
    point-in-time-correct walk -- i.e. the harness's strict per-bar gating
    is load-bearing, not a no-op."""
    _skip_if_no_data()
    from btmm_ai_scanner.scanner.replay import IncrementalReplayKernel
    from tests.parity_support.v1a_harness import _TRACKED_TIMEFRAMES

    dev = load_dev_only_m15(_ROOT)[:6]
    config = build_scanner_configuration()

    # Correct: one bar per group, strictly in order.
    correct_kernel = IncrementalReplayKernel(
        _TRACKED_TIMEFRAMES, config, ContentAddressedIdentityProvider(), ()
    )
    for candle in dev[:4]:
        correct_kernel.advance_group({Timeframe.M15: (candle,)})
    correct_snapshot = correct_kernel.finalize()

    # Mutated: bar 5 (a future bar relative to the 4-bar point-in-time cut)
    # is injected into the SAME group as bar 4 -- a lookahead bug.
    bugged_kernel = IncrementalReplayKernel(
        _TRACKED_TIMEFRAMES, config, ContentAddressedIdentityProvider(), ()
    )
    for candle in dev[:3]:
        bugged_kernel.advance_group({Timeframe.M15: (candle,)})
    bugged_kernel.advance_group({Timeframe.M15: (dev[3], dev[4])})  # lookahead injected
    bugged_snapshot = bugged_kernel.finalize()

    correct_dump = json.dumps(correct_snapshot.model_dump(mode="json"), sort_keys=True, default=str)
    bugged_dump = json.dumps(bugged_snapshot.model_dump(mode="json"), sort_keys=True, default=str)
    assert correct_dump != bugged_dump
    assert correct_snapshot.availability_time_utc != bugged_snapshot.availability_time_utc


# ---------------------------------------------------------------------------
# POI idx stability, event->POI linkage, duplicate/overlapping events.
# ---------------------------------------------------------------------------


def test_poi_idx_assignment_stable_and_unique() -> None:
    _skip_if_no_data()
    result = run_dev_replay(
        dataset_root=_ROOT, pre_dev_lookback_bars=_SMALL_LOOKBACK, max_bars=_SMALL_BARS
    )
    idxs = [entry.poi_idx for entry in result.poi_registry.values()]
    assert len(idxs) == len(set(idxs))  # every POI gets a unique idx
    assert sorted(idxs) == list(range(len(idxs)))  # assigned densely from 0


def test_every_event_links_to_a_registered_poi() -> None:
    _skip_if_no_data()
    result = run_dev_replay(
        dataset_root=_ROOT, pre_dev_lookback_bars=_SMALL_LOOKBACK, max_bars=_SMALL_BARS
    )
    registered_ids = {str(k) for k in result.poi_registry}
    assert len(result.events) > 0
    for event in result.events:
        assert event.poi_record_id in registered_ids


def test_duplicate_and_overlapping_events_are_not_collapsed() -> None:
    """Two distinct event TYPES for the SAME POI on the SAME bar (e.g.
    POI_ACTIVATED and BTMM_VALIDATED both firing the bar a POI is created
    with BTMM already valid) must both survive as separate records -- the
    harness must never de-duplicate by (poi, bar) alone."""
    _skip_if_no_data()
    result = run_dev_replay(
        dataset_root=_ROOT, pre_dev_lookback_bars=_SMALL_LOOKBACK, max_bars=_SMALL_BARS
    )
    by_poi_and_bar: dict[tuple[str, int], set[str]] = {}
    for event in result.events:
        key = (event.poi_record_id, event.bar_index)
        by_poi_and_bar.setdefault(key, set()).add(event.event_type)
    multi_event_bars = [k for k, v in by_poi_and_bar.items() if len(v) > 1]
    assert len(multi_event_bars) > 0, (
        "expected at least one (poi, bar) pair with more than one distinct "
        "event type in this small sample -- if this ever fails on a larger "
        "sample it is not itself a bug, but it means this particular "
        "assertion needs a bigger fixture to stay meaningful."
    )


def test_poi_invalidation_directed() -> None:
    """Directed POI-invalidation test: every ``POI_TERMINAL`` event must
    carry ``poi_lifecycle_status == GENUINE_INVALIDATION_CONFIRMED`` -- the
    reused, closed P3 definition of terminal (never a new invalidation
    rule invented by this harness), and a bigger (but still fast) sample
    than the other directed tests' fixture, chosen because invalidation is
    comparatively rare in a 12-bar window."""
    _skip_if_no_data()
    result = run_dev_replay(dataset_root=_ROOT, pre_dev_lookback_bars=20, max_bars=60)
    terminal_events = [e for e in result.events if e.event_type == "POI_TERMINAL"]
    assert len(terminal_events) > 0, (
        "expected at least one POI_TERMINAL event in this sample -- if this "
        "ever fails, it does not necessarily mean the harness is broken, but "
        "the assertion below needs a bigger/different fixture to stay "
        "meaningful."
    )
    for event in terminal_events:
        assert event.poi_lifecycle_status == "GENUINE_INVALIDATION_CONFIRMED"
