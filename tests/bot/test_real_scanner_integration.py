"""The bot driving the REAL scanner (``level_a_replay``) on synthetic candles.

* the bot's daily P3/P5/P8 digests equal the RC3 daily authority's digests
  for the same series (the bot consumes, it does not fork);
* restart mid-run rebuilds the real kernel from persisted inputs, verifies
  every bar digest, and ends byte-identical to an uninterrupted run;
* a higher-TF candle never influences a bar before its availability;
* the CLI ``replay --max-bars`` / ``restart`` (a real new process) path
  matches an uninterrupted CLI run.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from botdryrun.engine import BotEngine, RunOutcome
from botdryrun.journals import DAILY_COLUMNS
from botdryrun.market_data import FeedKind, interleave
from botdryrun.scanner_adapter import LevelAScannerSource
from botdryrun.store import StateStore
from btmm_ai_scanner.config.enums import Timeframe
from tests.bot.support import (
    SCANNER_START,
    config_for,
    deterministic_journals,
    items_of,
    load,
    scanner_bars,
    session_times,
    static_loader,
    write_csv,
)
from tests.parity_support.level_a_replay import build_scanner_configuration
from tests.parity_support.rc3_daily_authority import run_daily_authority

BARS = 48
REPO_ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def data(tmp_path_factory: pytest.TempPathFactory):  # type: ignore[no-untyped-def]
    root = tmp_path_factory.mktemp("real_scanner")
    times = session_times(SCANNER_START, BARS)
    write_csv(root / "M15.csv", times, scanner_bars(BARS))
    return root, times, load(root / "M15.csv")


@pytest.fixture(scope="module")
def uninterrupted(tmp_path_factory: pytest.TempPathFactory, data):  # type: ignore[no-untyped-def]
    root, times, _ = data
    state = tmp_path_factory.mktemp("uninterrupted")
    engine = BotEngine(state, config_for(root, times))
    try:
        report = engine.run()
    finally:
        engine.close()
    assert report.outcome is RunOutcome.COMPLETED
    return state, deterministic_journals(state)


def test_daily_digests_equal_the_rc3_authority(data, uninterrupted) -> None:  # type: ignore[no-untyped-def]
    _, _, candles = data
    authority = run_daily_authority(
        host_timeframe=Timeframe.M15,
        host_series=candles,
        context_series={},
        configuration=build_scanner_configuration(
            required_timeframes=frozenset({Timeframe.M15}), optional_timeframes=frozenset()
        ),
    )
    state, _ = uninterrupted
    rows = (state / "journals" / "daily_authority_journal.csv").read_text(encoding="utf-8").splitlines()
    header = rows[0].split(",")
    assert tuple(header) == DAILY_COLUMNS
    bot_days = [dict(zip(header, line.split(","), strict=True)) for line in rows[1:]]
    assert len(bot_days) == len(authority.days) == 2  # crosses the session break
    for bot, auth in zip(bot_days, authority.days, strict=True):
        for key, value in auth.as_row().items():
            assert bot[key] == str(value), key
    assert authority.p8_events_total > 0
    manifest = json.loads((state / "journals" / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["period_digests_authority_fold"] == {
        "P3": authority.period_p3_digest,
        "P5": authority.period_p5_digest,
        "P8": authority.period_p8_digest,
    }


def test_two_replays_are_byte_identical(tmp_path: Path, data, uninterrupted) -> None:  # type: ignore[no-untyped-def]
    root, times, _ = data
    engine = BotEngine(tmp_path / "again", config_for(root, times))
    try:
        engine.run()
    finally:
        engine.close()
    assert deterministic_journals(tmp_path / "again") == uninterrupted[1]


def test_restart_rebuilds_the_real_kernel_and_matches(tmp_path: Path, data, uninterrupted) -> None:  # type: ignore[no-untyped-def]
    root, times, _ = data
    state = tmp_path / "state"
    config = config_for(root, times)
    engine = BotEngine(state, config)
    try:
        assert engine.run(max_bars=19).outcome is RunOutcome.PAUSED
    finally:
        engine.close()
    engine = BotEngine(state)  # config comes from the store
    try:
        report = engine.run(max_bars=15)  # crosses the 21:00->22:00 break
        assert report.outcome is RunOutcome.PAUSED and report.rebuilt_bars == 19
    finally:
        engine.close()
    engine = BotEngine(state)
    try:
        report = engine.run()
        assert report.outcome is RunOutcome.COMPLETED and report.rebuilt_bars == 34
    finally:
        engine.close()
    store = StateStore(state)
    try:
        verification = json.loads(store.get_meta("last_rebuild") or "{}")
        assert verification["verified"] is True and verification["bars"] == 34
        events = [r[0] for r in store.query("SELECT event_id FROM events")]
        assert len(events) == len(set(events)) > 0
    finally:
        store.close()
    assert deterministic_journals(state) == uninterrupted[1]


def test_higher_tf_candle_is_never_visible_before_its_availability(tmp_path: Path) -> None:
    """Truncate-and-extend on the context series: removing an H1 candle from
    the feed must not change any bar that closed before that candle became
    available; and a late-arriving copy is rejected, never applied."""
    m15_times = session_times(datetime(2026, 8, 18, 1, 0, tzinfo=UTC), 24)
    write_csv(tmp_path / "M15.csv", m15_times, scanner_bars(24))
    h1_times = session_times(datetime(2026, 8, 17, 16, 0, tzinfo=UTC), 14, timedelta(hours=1))
    h1_bars = [(100.0 + i, 101.5 + i, 99.0 + i, 101.0 + i) for i in range(14)]
    write_csv(tmp_path / "H1.csv", h1_times, h1_bars)
    host = load(tmp_path / "M15.csv")
    h1 = load(tmp_path / "H1.csv", Timeframe.H1)
    probe = next(c for c in h1 if c.availability_time_utc == datetime(2026, 8, 18, 3, 0, tzinfo=UTC))
    config = config_for(tmp_path, m15_times, context_timeframes=["H1"])

    def run(name: str, items: list) -> list[tuple[int, str, int]]:  # type: ignore[type-arg]
        engine = BotEngine(tmp_path / name, config, feed_loader=static_loader(items),
                           scanner_source=LevelAScannerSource())
        try:
            engine.run()
            rows = engine.store.query("SELECT bar_index, bar_digest, bar_ms FROM bar_summary ORDER BY bar_index")
            released = engine.store.query(
                "SELECT c.availability_ms, h.availability_ms FROM context_inputs c "
                "JOIN host_inputs h ON h.bar_index = MAX(c.released_at_bar_index, 0)"
            )
            for context_availability, host_availability in released:
                if context_availability >= int(host[0].availability_time_utc.timestamp() * 1000):
                    assert context_availability <= host_availability
            return [(int(r[0]), str(r[1]), int(r[2])) for r in rows]
        finally:
            engine.close()

    full = run("full", interleave(host, {Timeframe.H1: h1}))
    without = run("without", interleave(host, {Timeframe.H1: [c for c in h1 if c is not probe]}))
    probe_ms = int(probe.availability_time_utc.timestamp() * 1000)
    before = [r for r in full if r[2] < probe_ms]
    assert before and before == [r for r in without if r[2] < probe_ms]

    late_stream = [i for i in interleave(host, {Timeframe.H1: h1}) if i.candle is not probe]
    late_stream.append(items_of(FeedKind.CONTEXT, [probe])[0])
    late = run("late", late_stream)
    assert late == without


def test_cli_pause_and_restart_in_a_new_process_matches(tmp_path: Path, data, uninterrupted) -> None:  # type: ignore[no-untyped-def]
    root, times, _ = data
    env = {**os.environ, "PYTHONPATH": str(REPO_ROOT)}
    base = [sys.executable, "-m", "botdryrun"]
    window = ["--start", times[0].isoformat(), "--end", times[-1].isoformat(),
              "--dataset-root", str(root), "--data-source", "CSV_DIR",
              "--context-timeframes", "", "--context-lookback-bars", "0"]
    state = tmp_path / "cli"

    def call(*args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run([*base, *args], cwd=REPO_ROOT, env=env, capture_output=True, text=True, timeout=600)

    first = call("replay", "--state-dir", str(state), *window, "--max-bars", "20")
    assert first.returncode == 0, first.stderr
    assert json.loads(first.stdout)["outcome"] == "PAUSED"
    status = call("status", "--state-dir", str(state))
    assert json.loads(status.stdout)["bars_processed"] == 20
    second = call("restart", "--state-dir", str(state))
    assert second.returncode == 0, second.stderr
    report = json.loads(second.stdout)
    assert report["outcome"] == "COMPLETED" and report["rebuilt_bars"] == 20
    health = call("health", "--state-dir", str(state))
    assert health.returncode == 0, health.stdout
    assert json.loads(health.stdout)["digest_verification"]["verified"] is True
    assert deterministic_journals(state) == uninterrupted[1]
