"""Restart safety and paper-trading behaviour, on a scripted scanner source.

The scripted source (``tests/bot/support.py``) stands in for the scanner so
that the scenario contains real trading actions (fills, a target, a stop, a
cancel, skipped signals, a duplicate event). Every restart test compares the
full deterministic journal set against one uninterrupted run and asserts
that no simulated action was duplicated.
"""

from __future__ import annotations

from collections import Counter
from pathlib import Path

import pytest

from botdryrun.config import BotConfig
from botdryrun.engine import (
    BotEngine,
    EngineStateError,
    FeedRevisionError,
    RebuildDigestMismatchError,
    RunOutcome,
)
from botdryrun.store import StateStore
from tests.bot.support import (
    SCRIPT_BARS,
    SCRIPT_START,
    deterministic_journals,
    host_items,
    load,
    script_bars,
    scripted_source,
    session_times,
    static_loader,
    write_csv,
)


class SimulatedCrash(RuntimeError):
    pass


@pytest.fixture(scope="module")
def scenario(tmp_path_factory: pytest.TempPathFactory) -> tuple[BotConfig, list]:  # type: ignore[type-arg]
    root = tmp_path_factory.mktemp("script_data")
    times = session_times(SCRIPT_START, SCRIPT_BARS)
    write_csv(root / "M15.csv", times, script_bars())
    candles = load(root / "M15.csv")
    config = BotConfig.from_mapping(
        {
            "window_start_utc": times[0].isoformat(),
            "window_end_utc": times[-1].isoformat(),
            "dataset_root": str(root),
            "data_source": "CSV_DIR",
            "context_timeframes": [],
            "context_lookback_bars": 0,
        }
    )
    return config, host_items(candles)


def _engine(state: Path, config: BotConfig, items: list, fault=None) -> BotEngine:  # type: ignore[no-untyped-def,type-arg]
    return BotEngine(
        state,
        config,
        feed_loader=static_loader(items),
        scanner_source=scripted_source(),
        fault_injector=fault,
    )


def _run(state: Path, config: BotConfig, items: list, max_bars: int | None = None, fault=None):  # type: ignore[no-untyped-def,type-arg]
    engine = _engine(state, config, items, fault)
    try:
        return engine.run(max_bars)
    finally:
        engine.close()


@pytest.fixture(scope="module")
def baseline(tmp_path_factory: pytest.TempPathFactory, scenario) -> tuple[Path, dict[str, bytes]]:  # type: ignore[no-untyped-def]
    config, items = scenario
    state = tmp_path_factory.mktemp("baseline")
    report = _run(state, config, items)
    assert report.outcome is RunOutcome.COMPLETED
    assert report.processed_bars == SCRIPT_BARS
    return state, deterministic_journals(state)


def _no_duplicates(state: Path) -> None:
    store = StateStore(state)
    try:
        for table, key in (
            ("events", "event_id"),
            ("signals", "signal_id"),
            ("orders", "order_id"),
            ("positions", "position_id"),
            ("host_inputs", "event_ms"),
            ("bar_summary", "bar_index"),
        ):
            rows = [r[0] for r in store.query(f"SELECT {key} FROM {table}")]
            assert len(rows) == len(set(rows)), table
        # One signal per source event, one order per accepted signal.
        sources = Counter(r[0] for r in store.query("SELECT source_event_id FROM signals"))
        assert all(n == 1 for n in sources.values())
        assert store.scalar("SELECT COUNT(*) FROM orders") == store.scalar(
            "SELECT COUNT(*) FROM signals WHERE status='ACCEPTED'"
        )
        bars = [r[0] for r in store.query("SELECT bar_index FROM bar_summary ORDER BY bar_index")]
        assert bars == list(range(len(bars)))
    finally:
        store.close()


# ---------------------------------------------------------------------------
# The scenario itself (cold start)
# ---------------------------------------------------------------------------


def test_cold_start_trades_exactly_as_scripted(baseline) -> None:  # type: ignore[no-untyped-def]
    state, _ = baseline
    _no_duplicates(state)
    store = StateStore(state)
    try:
        signals = {
            r[0]: (r[1], r[2])
            for r in store.query("SELECT source_event_id, status, reason FROM signals")
        }
        by_poi = Counter()
        for event_id, (status, reason) in signals.items():
            by_poi[(event_id.split(":")[1], status, reason)] += 1
        assert by_poi[("0", "ACCEPTED", "PERMISSION_ENTERED_ACTIONABLE")] == 2
        assert by_poi[("1", "ACCEPTED", "PERMISSION_ENTERED_ACTIONABLE")] == 1
        assert by_poi[("2", "ACCEPTED", "PERMISSION_ENTERED_ACTIONABLE")] == 1
        assert by_poi[("3", "SKIPPED", "POI_NOT_FRESH")] == 1
        assert by_poi[("4", "ACCEPTED", "PERMISSION_ENTERED_ACTIONABLE")] == 1
        assert by_poi[("5", "SKIPPED", "PERMISSION_DIRECTION_MISMATCH")] == 1
        # POI 6 was actionable in every decision but never had an event.
        assert not any(k[0] == "6" for k in by_poi)
        assert len(signals) == 7

        orders = store.query("SELECT order_id FROM orders")
        statuses = Counter((poi, status, reason) for poi, status, reason in store.query(
            "SELECT poi_idx, status, reason FROM orders"))
        assert statuses[(1, "CANCELLED", "PERMISSION_LOST_ACTIONABLE")] == 1
        assert statuses[(2, "CANCELLED", "POI_TERMINAL")] == 1
        assert statuses[(0, "FILLED", "FILLED")] == 1
        assert statuses[(4, "FILLED", "FILLED")] == 1
        assert statuses[(0, "PENDING", "PLACED")] == 1
        assert len(orders) == 5

        trades = store.query(
            "SELECT poi_record_id, entry_price, entry_bar_index, exit_price, exit_bar_index, exit_reason, "
            "realized_pnl, quantity FROM positions ORDER BY entry_bar_index"
        )
        assert [(t[0], t[1], t[2], t[3], t[4], t[5]) for t in trades] == [
            ("poi-0", "99.00", 5, "101.00", 10, "TARGET"),
            ("poi-4", "99.50", 16, "99.00", 19, "STOP"),
        ]
        # fixed-fractional sizing: 1% of 10000 / 1.00 risk = 100 units
        assert trades[0][7] == "100.000"
        assert trades[0][6] == "200.00"
        # second trade: 1% of 10200 / 0.50 = 204 units, stopped: -102.00
        assert trades[1][7] == "204.000"
        assert trades[1][6] == "-102.00"
        assert store.query("SELECT balance FROM bar_summary ORDER BY bar_index DESC LIMIT 1")[0][0] == "10098.00"
        # the duplicate same-bar delivery was consumed once, and reported
        assert store.scalar("SELECT events_duplicate FROM bar_summary WHERE bar_index=14") == 1
        assert store.scalar("SELECT COUNT(*) FROM events WHERE poi_idx=4") == 1
    finally:
        store.close()


def test_determinism_two_replays_are_byte_identical(tmp_path: Path, scenario, baseline) -> None:  # type: ignore[no-untyped-def]
    config, items = scenario
    report = _run(tmp_path / "again", config, items)
    assert report.outcome is RunOutcome.COMPLETED
    assert deterministic_journals(tmp_path / "again") == baseline[1]


# ---------------------------------------------------------------------------
# Restarts
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "pause_after",
    [
        4,  # mid-day, with a pending order and no fill yet
        6,  # mid-day, POI0 position open, POI1 pending
        8,  # exactly at the 20:45 -> 22:00 session break (next trading day)
        17,  # next day, with an open position
    ],
)
def test_pause_and_restart_matches_uninterrupted(
    tmp_path: Path, scenario, baseline, pause_after: int  # type: ignore[no-untyped-def]
) -> None:
    config, items = scenario
    state = tmp_path / "state"
    first = _run(state, config, items, max_bars=pause_after)
    assert first.outcome is RunOutcome.PAUSED
    assert first.total_bars == pause_after
    # A NEW engine instance (the in-process equivalent of a new process).
    engine = BotEngine(state, feed_loader=static_loader(items), scanner_source=scripted_source())
    try:
        second = engine.run()
    finally:
        engine.close()
    assert second.outcome is RunOutcome.COMPLETED
    assert second.rebuilt_bars == pause_after
    assert second.processed_bars == SCRIPT_BARS - pause_after
    _no_duplicates(state)
    assert deterministic_journals(state) == baseline[1]


def test_restart_across_the_session_break_is_on_the_next_trading_day(scenario, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
    config, items = scenario
    state = tmp_path / "s"
    _run(state, config, items, max_bars=8)
    store = StateStore(state)
    try:
        last = store.query("SELECT event_utc, trading_day FROM bar_summary ORDER BY bar_index DESC LIMIT 1")[0]
        assert last == ("2026-08-17T20:45:00+00:00", "2026-08-17")
    finally:
        store.close()
    _run(state, config, items, max_bars=1)
    store = StateStore(state)
    try:
        last = store.query("SELECT event_utc, trading_day FROM bar_summary ORDER BY bar_index DESC LIMIT 1")[0]
        assert last == ("2026-08-17T22:00:00+00:00", "2026-08-18")
        assert store.scalar("SELECT COUNT(*) FROM incidents WHERE kind='MISSING_BARS'") == 0
    finally:
        store.close()


@pytest.mark.parametrize("crash_bar", [5, 10, 14, 16])
def test_crash_before_commit_reprocesses_the_bar_exactly_once(
    tmp_path: Path, scenario, baseline, crash_bar: int  # type: ignore[no-untyped-def]
) -> None:
    config, items = scenario
    state = tmp_path / "state"
    calls: list[int] = []

    def fault(stage: str, bar_index: int) -> None:
        if stage == "before_commit":
            calls.append(bar_index)
            if bar_index == crash_bar:
                raise SimulatedCrash("killed after the scanner step, before COMMIT")

    engine = _engine(state, config, items, fault)
    with pytest.raises(SimulatedCrash):
        engine.run()
    # the crashed engine refuses to continue in-process
    with pytest.raises(EngineStateError):
        engine.run()
    engine.close()

    store = StateStore(state)
    try:
        assert store.processed_bar_count() == crash_bar
        assert store.get_meta("status") == "RUNNING"
    finally:
        store.close()

    recovered: list[int] = []

    def watch(stage: str, bar_index: int) -> None:
        if stage == "before_commit":
            recovered.append(bar_index)

    engine = BotEngine(state, feed_loader=static_loader(items), scanner_source=scripted_source(), fault_injector=watch)
    try:
        report = engine.run()
    finally:
        engine.close()
    assert report.outcome is RunOutcome.COMPLETED
    assert report.rebuilt_bars == crash_bar
    # the crashed bar is processed exactly once more, and nothing before it
    assert recovered == list(range(crash_bar, SCRIPT_BARS))
    _no_duplicates(state)
    assert deterministic_journals(state) == baseline[1]


def test_crash_after_commit_does_not_reprocess(tmp_path: Path, scenario, baseline) -> None:  # type: ignore[no-untyped-def]
    config, items = scenario
    state = tmp_path / "state"

    def fault(stage: str, bar_index: int) -> None:
        if stage == "after_commit" and bar_index == 16:
            raise SimulatedCrash("killed right after COMMIT")

    engine = _engine(state, config, items, fault)
    with pytest.raises(SimulatedCrash):
        engine.run()
    engine.close()
    recovered: list[int] = []
    engine = BotEngine(
        state,
        feed_loader=static_loader(items),
        scanner_source=scripted_source(),
        fault_injector=lambda s, i: recovered.append(i) if s == "before_commit" else None,
    )
    try:
        report = engine.run()
    finally:
        engine.close()
    assert report.rebuilt_bars == 17
    assert recovered[0] == 17
    _no_duplicates(state)
    assert deterministic_journals(state) == baseline[1]


def test_resume_refuses_an_unclean_state_but_restart_recovers(tmp_path: Path, scenario) -> None:  # type: ignore[no-untyped-def]
    config, items = scenario
    state = tmp_path / "state"

    def fault(stage: str, bar_index: int) -> None:
        if stage == "before_commit" and bar_index == 3:
            raise SimulatedCrash

    engine = _engine(state, config, items, fault)
    with pytest.raises(SimulatedCrash):
        engine.run()
    engine.close()
    engine = BotEngine(state, feed_loader=static_loader(items), scanner_source=scripted_source())
    try:
        with pytest.raises(EngineStateError, match="restart"):
            engine.run(allow_unclean=False)
        assert engine.run(allow_unclean=True).outcome is RunOutcome.COMPLETED
    finally:
        engine.close()


def test_rebuild_digest_mismatch_fails_loudly(tmp_path: Path, scenario) -> None:  # type: ignore[no-untyped-def]
    config, items = scenario
    state = tmp_path / "state"
    _run(state, config, items, max_bars=6)
    store = StateStore(state)
    try:
        store.conn.execute("UPDATE bar_summary SET bar_digest='0'||substr(bar_digest,2) WHERE bar_index=3")
    finally:
        store.close()
    engine = BotEngine(state, feed_loader=static_loader(items), scanner_source=scripted_source())
    try:
        with pytest.raises(RebuildDigestMismatchError):
            engine.run()
        assert engine.status() == "REBUILD_MISMATCH"
        assert engine.store.processed_bar_count() == 6
    finally:
        engine.close()


def test_revised_feed_is_refused_on_restart(tmp_path: Path, scenario) -> None:  # type: ignore[no-untyped-def]
    config, items = scenario
    state = tmp_path / "state"
    _run(state, config, items, max_bars=6)
    # the source now serves a different bar 2
    root = tmp_path / "revised"
    bars = script_bars()
    bars[2] = (100.0, 100.4, 99.7, 100.1)
    times = session_times(SCRIPT_START, SCRIPT_BARS)
    write_csv(root / "M15.csv", times, bars)
    revised = host_items(load(root / "M15.csv"))
    engine = BotEngine(state, feed_loader=static_loader(revised), scanner_source=scripted_source())
    try:
        with pytest.raises(FeedRevisionError):
            engine.run()
    finally:
        engine.close()


def test_a_different_config_cannot_hijack_a_session(tmp_path: Path, scenario) -> None:  # type: ignore[no-untyped-def]
    from botdryrun.engine import SessionMismatchError

    config, items = scenario
    state = tmp_path / "state"
    _run(state, config, items, max_bars=2)
    with pytest.raises(SessionMismatchError):
        BotEngine(state, config.with_overrides(reward_risk=config.reward_risk + 1))
