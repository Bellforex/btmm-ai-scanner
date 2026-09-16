"""Market-data adapter: stream validation, calendar, sealed range."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from botdryrun.config import GapPolicy
from botdryrun.engine import BotEngine, RunOutcome
from botdryrun.market_data import (
    ConflictingDuplicateBarError,
    FeedKind,
    FxcmSessionCalendar,
    OutOfOrderBarError,
    SealedRangeRefusedError,
    assemble_feed,
    interleave,
)
from botdryrun.store import StateStore
from btmm_ai_scanner.config.enums import Timeframe
from tests.bot.support import (
    SCRIPT_START,
    config_for,
    items_of,
    load,
    scripted_source,
    session_times,
    static_loader,
    write_csv,
)
from tests.parity_support.rc3_daily_authority import (
    SEALED_FIRST_EVENT_UTC,
    SEALED_LAST_EVENT_UTC,
    load_level_a_window,
)

_DATA_ROOT = Path("C:/Users/user/Desktop/btmm-ai-scanner/artifacts/v1a_validation")
M15 = FxcmSessionCalendar(step=timedelta(minutes=15))


def _flat(n: int) -> list[tuple[float, float, float, float]]:
    return [(100.0, 100.3, 99.7, 100.0)] * n


@pytest.fixture()
def series(tmp_path: Path):  # type: ignore[no-untyped-def]
    times = session_times(SCRIPT_START, 12)
    write_csv(tmp_path / "M15.csv", times, _flat(12))
    candles = load(tmp_path / "M15.csv")
    alt = [(100.0, 100.9, 99.7, 100.0)] * 12
    write_csv(tmp_path / "alt" / "M15.csv", times, alt)
    return times, candles, load(tmp_path / "alt" / "M15.csv")


# ---------------------------------------------------------------------------
# Calendar
# ---------------------------------------------------------------------------


def test_session_break_and_weekend_are_not_gaps() -> None:
    thu_last = datetime(2026, 8, 20, 20, 45, tzinfo=UTC)
    assert M15.next_slot(thu_last) == datetime(2026, 8, 20, 22, 0, tzinfo=UTC)
    fri_last = datetime(2026, 8, 21, 20, 30, tzinfo=UTC)
    assert M15.next_slot(fri_last) == datetime(2026, 8, 23, 22, 0, tzinfo=UTC)
    assert M15.missing_slots_between(fri_last, datetime(2026, 8, 23, 22, 0, tzinfo=UTC)) == 0
    assert M15.missing_slots_between(thu_last, datetime(2026, 8, 20, 22, 30, tzinfo=UTC)) == 2
    assert not M15.is_slot(datetime(2026, 8, 20, 21, 0, tzinfo=UTC))
    assert not M15.is_slot(datetime(2026, 8, 21, 20, 45, tzinfo=UTC))


def test_real_fxcm_period_has_no_calendar_gaps() -> None:
    """The calendar is not a guess: on the whole acquired six-timeframe
    period (host bars only, no scanner) it flags zero missing bars."""
    if not (_DATA_ROOT / "v1a_raw_ohlc_full_loaded.csv").is_file():
        pytest.skip("FXCM artifacts not present")
    window = load_level_a_window(_DATA_ROOT, context_timeframes=(), context_lookback_bars=0)
    host = list(window.host_series)
    assert host
    feed = assemble_feed(items_of(FeedKind.HOST, host), host_timeframe=Timeframe.M15, gap_policy=GapPolicy.HALT)
    assert feed.incidents == ()
    assert len(feed.host) == len(host)


# ---------------------------------------------------------------------------
# Host stream validation
# ---------------------------------------------------------------------------


def test_identical_duplicate_bar_is_ignored_idempotently(series, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
    times, candles, _ = series
    stream = [*candles[:5], candles[4], candles[2], *candles[5:]]
    feed = assemble_feed(items_of(FeedKind.HOST, stream), host_timeframe=Timeframe.M15, gap_policy=GapPolicy.HALT)
    assert feed.fatal is None
    assert feed.host == tuple(candles)
    assert feed.duplicates_ignored == 2
    assert {i.kind for i in feed.incidents} == {"DUPLICATE_BAR_IGNORED"}
    # end to end: the bot processes each bar exactly once
    config = config_for(tmp_path, times)
    engine = BotEngine(tmp_path / "s", config, feed_loader=static_loader(items_of(FeedKind.HOST, stream)),
                       scanner_source=scripted_source())
    try:
        report = engine.run()
        assert report.outcome is RunOutcome.COMPLETED
        assert engine.store.processed_bar_count() == len(candles)
    finally:
        engine.close()


def test_conflicting_duplicate_bar_is_rejected_loudly(series, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
    times, candles, alt = series
    stream = [*candles[:6], alt[5], *candles[6:]]
    feed = assemble_feed(items_of(FeedKind.HOST, stream), host_timeframe=Timeframe.M15, gap_policy=GapPolicy.CONTINUE)
    assert isinstance(feed.fatal, ConflictingDuplicateBarError)
    assert len(feed.host) == 6
    config = config_for(tmp_path, times)
    engine = BotEngine(tmp_path / "s", config, feed_loader=static_loader(items_of(FeedKind.HOST, stream)),
                       scanner_source=scripted_source())
    try:
        with pytest.raises(ConflictingDuplicateBarError):
            engine.run()
        assert engine.status() == "HALTED_FEED_ERROR"
        assert engine.store.processed_bar_count() == 6
        assert engine.store.scalar("SELECT severity FROM incidents WHERE kind='ConflictingDuplicateBarError'") == "CRITICAL"
    finally:
        engine.close()


def test_out_of_order_bar_is_rejected(series, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
    times, candles, _ = series
    stream = [*candles[:4], candles[6], candles[5], *candles[7:]]
    feed = assemble_feed(items_of(FeedKind.HOST, stream), host_timeframe=Timeframe.M15, gap_policy=GapPolicy.CONTINUE)
    assert isinstance(feed.fatal, OutOfOrderBarError)
    config = config_for(tmp_path, times)
    engine = BotEngine(tmp_path / "s", config, feed_loader=static_loader(items_of(FeedKind.HOST, stream)),
                       scanner_source=scripted_source())
    try:
        with pytest.raises(OutOfOrderBarError):
            engine.run()
        # bars 0-3 and the (gap-continued) bar 6 were processed; 5 never was
        assert engine.store.processed_bar_count() == 5
    finally:
        engine.close()


@pytest.mark.parametrize("policy", [GapPolicy.CONTINUE, GapPolicy.HALT])
def test_missing_bar_is_an_incident_with_configurable_halt(series, tmp_path: Path, policy: GapPolicy) -> None:  # type: ignore[no-untyped-def]
    times, candles, _ = series
    stream = [c for i, c in enumerate(candles) if i != 3]
    config = config_for(tmp_path, times, gap_policy=policy.value)
    engine = BotEngine(tmp_path / "s", config, feed_loader=static_loader(items_of(FeedKind.HOST, stream)),
                       scanner_source=scripted_source())
    try:
        report = engine.run()
        incidents = engine.store.query("SELECT kind, severity, event_utc FROM incidents")
        assert incidents == [("MISSING_BARS", "WARNING", candles[4].event_time_utc.isoformat())]
        if policy is GapPolicy.HALT:
            assert report.outcome is RunOutcome.HALTED_GAP
            assert engine.store.processed_bar_count() == 3
        else:
            assert report.outcome is RunOutcome.COMPLETED
            assert engine.store.processed_bar_count() == len(candles) - 1
    finally:
        engine.close()


# ---------------------------------------------------------------------------
# Context (higher-TF) timing
# ---------------------------------------------------------------------------


@pytest.fixture()
def with_h1(tmp_path: Path):  # type: ignore[no-untyped-def]
    m15_times = session_times(datetime(2026, 8, 18, 1, 0, tzinfo=UTC), 16)
    write_csv(tmp_path / "M15.csv", m15_times, _flat(16))
    h1_times = session_times(datetime(2026, 8, 17, 23, 0, tzinfo=UTC), 6, timedelta(hours=1))
    write_csv(tmp_path / "H1.csv", h1_times, _flat(6))
    return load(tmp_path / "M15.csv"), load(tmp_path / "H1.csv", Timeframe.H1)


def test_context_candle_is_released_only_at_its_availability(with_h1) -> None:  # type: ignore[no-untyped-def]
    host, h1 = with_h1
    # deliver every H1 candle EARLY, before any host bar
    stream = [*items_of(FeedKind.CONTEXT, h1), *items_of(FeedKind.HOST, host)]
    feed = assemble_feed(stream, host_timeframe=Timeframe.M15, gap_policy=GapPolicy.HALT)
    assert feed.incidents == ()
    for candle in h1:
        key = ("H1", int(candle.event_time_utc.timestamp() * 1000))
        release = feed.release_index.get(key)
        if release is None:
            assert candle.availability_time_utc > host[-1].availability_time_utc
        elif release == -1:
            assert candle.availability_time_utc < host[0].availability_time_utc
        else:
            assert host[release].availability_time_utc >= candle.availability_time_utc
            if release > 0:
                assert host[release - 1].availability_time_utc < candle.availability_time_utc
    for bar_index in range(len(host)):
        for candle in feed.released_context(bar_index).get(Timeframe.H1, ()):
            assert candle.availability_time_utc <= host[bar_index].availability_time_utc


def test_late_context_candle_is_rejected_not_applied_retroactively(with_h1) -> None:  # type: ignore[no-untyped-def]
    host, h1 = with_h1
    on_time = interleave(host, {Timeframe.H1: h1})
    late_candle = h1[3]  # closes 03:00Z, inside the host window
    stream = [item for item in on_time if item.candle is not late_candle]
    stream.append(items_of(FeedKind.CONTEXT, [late_candle])[0])  # arrives after the last host bar
    feed = assemble_feed(stream, host_timeframe=Timeframe.M15, gap_policy=GapPolicy.HALT)
    assert feed.late_context_rejected == 1
    assert [i.kind for i in feed.incidents] == ["LATE_CONTEXT_CANDLE"]
    assert late_candle not in feed.context[Timeframe.H1]


# ---------------------------------------------------------------------------
# Sealed range
# ---------------------------------------------------------------------------


def test_sealed_range_window_is_refused(tmp_path: Path) -> None:
    times = session_times(datetime(2026, 7, 20, 1, 0, tzinfo=UTC), 8)
    assert SEALED_FIRST_EVENT_UTC <= times[0] <= SEALED_LAST_EVENT_UTC
    write_csv(tmp_path / "M15.csv", times, _flat(8))
    config = config_for(tmp_path, times)
    engine = BotEngine(tmp_path / "s", config, scanner_source=scripted_source())
    try:
        with pytest.raises(SealedRangeRefusedError):
            engine.run()
        assert engine.store.processed_bar_count() == 0
    finally:
        engine.close()


def test_sealed_host_bars_are_refused_even_from_an_injected_feed(tmp_path: Path) -> None:
    times = session_times(datetime(2026, 8, 3, 5, 0, tzinfo=UTC), 12)
    assert times[0] <= SEALED_LAST_EVENT_UTC < times[-1]
    write_csv(tmp_path / "M15.csv", times, _flat(12))
    candles = load(tmp_path / "M15.csv")
    with pytest.raises(SealedRangeRefusedError):
        assemble_feed(items_of(FeedKind.HOST, candles), host_timeframe=Timeframe.M15, gap_policy=GapPolicy.CONTINUE)
    config = config_for(tmp_path, times)
    engine = BotEngine(
        tmp_path / "s",
        config.with_overrides(window_start_utc=datetime(2026, 9, 1, tzinfo=UTC),
                              window_end_utc=datetime(2026, 9, 2, tzinfo=UTC)),
        feed_loader=static_loader(items_of(FeedKind.HOST, candles)),
        scanner_source=scripted_source(),
    )
    try:
        with pytest.raises(SealedRangeRefusedError):
            engine.run()
        assert engine.store.processed_bar_count() == 0
    finally:
        engine.close()
    store = StateStore(tmp_path / "s")
    try:
        assert store.scalar("SELECT COUNT(*) FROM host_inputs") == 0
    finally:
        store.close()
