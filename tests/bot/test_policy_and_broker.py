"""Unit tests: P8 consumer, practice policy and paper broker fill model."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

import pytest

from botdryrun.broker import PaperBroker
from botdryrun.config import BotConfig, EntryMode
from botdryrun.domain import EventView, PoiView, ScannerBarSnapshot
from botdryrun.events import P8EventConsumer
from botdryrun.policy import (
    FixedFractionalRiskPolicy,
    PracticePolicy,
    Side,
    signal_id_for,
)
from tests.bot.support import load, session_times, write_csv

START = datetime(2026, 8, 18, 1, 0, tzinfo=UTC)


def _config(**kw: object) -> BotConfig:
    raw: dict[str, object] = {
        "window_start_utc": "2026-08-18T01:00:00Z",
        "window_end_utc": "2026-08-18T05:00:00Z",
        "dataset_root": ".",
        "data_source": "CSV_DIR",
        "context_timeframes": [],
    }
    raw.update(kw)
    return BotConfig.from_mapping(raw)


@pytest.fixture(scope="module")
def candles(tmp_path_factory: pytest.TempPathFactory):  # type: ignore[no-untyped-def]
    root: Path = tmp_path_factory.mktemp("pb")
    times = session_times(START, 6)
    bars = [
        (100.0, 100.3, 99.7, 100.0),
        (100.0, 100.3, 99.7, 100.0),
        (99.6, 99.8, 98.5, 99.0),  # opens below a 99.70 limit; low under a 99.00 stop
        (100.0, 101.0, 99.5, 100.5),
        (100.0, 102.5, 97.0, 100.0),  # both stop and target inside the range
        (98.0, 98.5, 97.5, 98.0),  # opens through a 98.50 long stop
    ]
    write_csv(root / "M15.csv", times, bars)
    return load(root / "M15.csv")


def _poi(idx: int, direction: str, bottom: str, top: str, fresh: bool = True) -> PoiView:
    return PoiView(
        record_id=f"poi-{idx}", poi_idx=idx, poi_type="X", direction=direction, family="X",
        source_timeframe="M15", effective_timeframe="M15", zone_top=Decimal(top),
        zone_bottom=Decimal(bottom), source_time_utc="", availability_time_utc="",
        fresh_active=fresh, terminal_reason=None if fresh else "MITIGATED", terminal_time_utc=None,
    )


def _event(event_type: str, idx: int, bar_ms: int = 1, permission: int = 0) -> EventView:
    return EventView(
        event_type=event_type, poi_idx=idx, bar_ms=bar_ms, sequence_in_bar=0,
        poi_record_id=f"poi-{idx}", poi_bullish=True, tier=1, btmm_valid=True,
        permission=permission, lifecycle=3, terminal_reason=None,
    )


def _snapshot(candle, pois, index: int = 0, events=()) -> ScannerBarSnapshot:  # type: ignore[no-untyped-def]
    return ScannerBarSnapshot(
        bar_index=index, bar_ms=1, candle=candle, trading_day="2026-08-18", primed=False,
        pois=tuple(pois), decisions=(), events=tuple(events), new_registry_pois=0,
        fresh_at_close=0, mitigated_at_close=0, invalidated_at_close=0,
        p3_lines=(), p5_lines=(), p8_lines=(), digest="",
    )


def _stack(**kw: object) -> tuple[BotConfig, PracticePolicy, PaperBroker]:
    config = _config(**kw)
    risk = FixedFractionalRiskPolicy(config.risk_fraction, config.max_concurrent_positions)
    return config, PracticePolicy(config, risk), PaperBroker(config, risk)


# ---------------------------------------------------------------------------
# P8 consumer
# ---------------------------------------------------------------------------


def test_duplicate_p8_event_is_consumed_once_including_after_restart() -> None:
    event = _event("PERMISSION_ENTERED_ACTIONABLE", 3, bar_ms=77)
    consumer = P8EventConsumer()
    first = consumer.consume([event, event])
    assert first.new_events == (event,)
    assert first.duplicates == (event,)
    assert consumer.consume([event]).new_events == ()
    # a restarted consumer seeded from the persisted processed-id set
    restarted = P8EventConsumer([event.event_id])
    assert restarted.consume([event]).new_events == ()
    # same type + POI at a LATER bar is a distinct native identity
    later = _event("PERMISSION_ENTERED_ACTIONABLE", 3, bar_ms=78)
    assert restarted.consume([later]).new_events == (later,)
    assert event.event_id == "PERMISSION_ENTERED_ACTIONABLE:3:77"


def test_signal_ids_are_derived_from_the_event_identity() -> None:
    a = _event("PERMISSION_ENTERED_ACTIONABLE", 1, 10)
    assert signal_id_for(a.event_id) == signal_id_for("PERMISSION_ENTERED_ACTIONABLE:1:10")
    assert signal_id_for(a.event_id) != signal_id_for("PERMISSION_ENTERED_ACTIONABLE:1:11")


# ---------------------------------------------------------------------------
# Policy
# ---------------------------------------------------------------------------


def test_permission_entered_produces_exactly_one_signal(candles) -> None:  # type: ignore[no-untyped-def]
    _, policy, broker = _stack()
    snap = _snapshot(candles[0], [_poi(0, "BULLISH", "99.00", "99.80")])
    actions = policy.on_events([_event("PERMISSION_ENTERED_ACTIONABLE", 0)], snap, broker)
    assert len(actions.signals) == 1
    signal = actions.signals[0]
    assert signal.status == "ACCEPTED" and signal.side is Side.LONG
    assert (signal.entry_price, signal.stop_price, signal.target_price) == (
        Decimal("99.80"), Decimal("99.00"), Decimal("101.40"),
    )
    broker.place(signal)
    broker.place(signal)  # same deterministic id -> still one order
    assert len(broker.orders) == 1
    # a second ENTERED for the same POI while the order is pending is skipped
    again = policy.on_events([_event("PERMISSION_ENTERED_ACTIONABLE", 0, bar_ms=2)], snap, broker)
    assert again.signals[0].status == "SKIPPED"
    assert again.signals[0].reason == "ALREADY_ACTIVE_FOR_POI"


def test_non_entry_events_and_bare_decisions_never_create_signals(candles) -> None:  # type: ignore[no-untyped-def]
    _, policy, broker = _stack()
    snap = _snapshot(candles[0], [_poi(0, "BULLISH", "99.00", "99.80")])
    for event_type in ("POI_ACTIVATED", "BTMM_VALIDATED", "PERMISSION_LOST_ACTIONABLE", "POI_TERMINAL"):
        assert policy.on_events([_event(event_type, 0)], snap, broker).signals == ()
    assert policy.on_events([], snap, broker).signals == ()


def test_terminal_poi_gets_no_signal_and_pending_is_cancelled(candles) -> None:  # type: ignore[no-untyped-def]
    _, policy, broker = _stack()
    fresh = _snapshot(candles[0], [_poi(0, "BULLISH", "99.00", "99.80")])
    broker.place(policy.on_events([_event("PERMISSION_ENTERED_ACTIONABLE", 0)], fresh, broker).signals[0])
    terminal = _snapshot(candles[1], [_poi(0, "BULLISH", "99.00", "99.80", fresh=False)], index=1)
    actions = policy.on_events(
        [_event("PERMISSION_ENTERED_ACTIONABLE", 0, bar_ms=2), _event("POI_TERMINAL", 0, bar_ms=2)],
        terminal,
        broker,
    )
    assert actions.signals[0].status == "SKIPPED"
    assert actions.signals[0].reason in ("ALREADY_ACTIVE_FOR_POI", "POI_NOT_FRESH")
    assert [c.reason for c in actions.cancels] == ["POI_TERMINAL"]
    assert broker.cancel_for_poi("poi-0", "POI_TERMINAL", 1) == 1
    assert broker.active_count() == 0
    # with nothing pending, a terminal POI is skipped for freshness
    later = policy.on_events([_event("PERMISSION_ENTERED_ACTIONABLE", 0, bar_ms=3)], terminal, broker)
    assert later.signals[0].reason == "POI_NOT_FRESH"


def test_permission_lost_cancels_pending(candles) -> None:  # type: ignore[no-untyped-def]
    _, policy, broker = _stack()
    snap = _snapshot(candles[0], [_poi(0, "BEARISH", "101.00", "101.50")])
    signal = policy.on_events([_event("PERMISSION_ENTERED_ACTIONABLE", 0, permission=1)], snap, broker).signals[0]
    assert signal.side is Side.SHORT and signal.entry_price == Decimal("101.00")
    broker.place(signal)
    actions = policy.on_events([_event("PERMISSION_LOST_ACTIONABLE", 0, bar_ms=2, permission=4)], snap, broker)
    for cancel in actions.cancels:
        broker.cancel_for_poi(cancel.poi_record_id, cancel.reason, 1)
    order = broker.orders[signal.signal_id]
    assert (order.status, order.reason) == ("CANCELLED", "PERMISSION_LOST_ACTIONABLE")


def test_max_concurrent_positions_is_enforced(candles) -> None:  # type: ignore[no-untyped-def]
    _, policy, broker = _stack(max_concurrent_positions=1)
    snap = _snapshot(candles[0], [_poi(0, "BULLISH", "99.0", "99.8"), _poi(1, "BULLISH", "98.0", "98.5")])
    actions = policy.on_events(
        [_event("PERMISSION_ENTERED_ACTIONABLE", 0), _event("PERMISSION_ENTERED_ACTIONABLE", 1)], snap, broker
    )
    assert [s.status for s in actions.signals] == ["ACCEPTED", "SKIPPED"]
    assert actions.signals[1].reason == "MAX_CONCURRENT_POSITIONS"


# ---------------------------------------------------------------------------
# Paper broker fill model
# ---------------------------------------------------------------------------


def test_limit_order_never_fills_on_its_creation_bar_then_fills_at_limit(candles) -> None:  # type: ignore[no-untyped-def]
    _, policy, broker = _stack()
    snap = _snapshot(candles[0], [_poi(0, "BULLISH", "99.00", "99.80")])
    broker.place(policy.on_events([_event("PERMISSION_ENTERED_ACTIONABLE", 0)], snap, broker).signals[0])
    # the order is never evaluated on the bar that created it
    assert broker.process_bar(0, candles[0]).fills == 0
    assert broker.process_bar(1, candles[1]).fills == 1  # low 99.70 <= limit 99.80
    position = next(iter(broker.positions.values()), None)
    assert position is not None
    assert position.entry_price == Decimal("99.80")


def test_limit_order_gapping_through_the_limit_fills_at_open(candles) -> None:  # type: ignore[no-untyped-def]
    _, policy, broker = _stack()
    snap = _snapshot(candles[1], [_poi(0, "BULLISH", "99.00", "99.70")], index=1)
    broker.place(policy.on_events([_event("PERMISSION_ENTERED_ACTIONABLE", 0)], snap, broker).signals[0])
    result = broker.process_bar(2, candles[2])  # opens 99.6 below the 99.70 limit, low 98.5 < stop 99.00
    assert result.fills == 1 and result.exits == 1
    position = next(iter(broker.positions.values()))
    assert position.entry_price == Decimal("99.60")
    assert (position.exit_reason, position.exit_price) == ("STOP", Decimal("99.00"))
    assert position.quantity == Decimal("166.666")
    assert position.realized_pnl == Decimal("-100.00")


def test_stop_first_when_stop_and_target_share_a_bar(candles) -> None:  # type: ignore[no-untyped-def]
    _, _, broker = _stack(entry_mode="NEXT_OPEN")
    from botdryrun.policy import SignalDecision

    signal = SignalDecision(
        signal_id="S1", source_event_id="E", bar_index=2, bar_ms=0, poi_idx=0, poi_record_id="poi-0",
        side=Side.LONG, status="ACCEPTED", reason="x", entry_mode=EntryMode.NEXT_OPEN,
        entry_price=None, stop_price=Decimal("99.00"), target_price=None,
    )
    broker.place(signal)
    fill = broker.process_bar(3, candles[3])  # fills at open 100.00, target 102.00; range 99.5-101
    assert fill.fills == 1 and fill.exits == 0
    position = broker.positions["S1"]
    assert position.target_price == Decimal("102.00")
    both = broker.process_bar(4, candles[4])  # low 97 <= stop AND high 102.5 >= target
    assert both.exits == 1
    assert (position.exit_reason, position.exit_price) == ("STOP", Decimal("99.00"))


def test_gap_through_stop_exits_at_open(candles) -> None:  # type: ignore[no-untyped-def]
    _, _, broker = _stack(entry_mode="NEXT_OPEN")
    from botdryrun.policy import SignalDecision

    broker.place(
        SignalDecision(
            signal_id="S2", source_event_id="E2", bar_index=3, bar_ms=0, poi_idx=0, poi_record_id="poi-0",
            side=Side.LONG, status="ACCEPTED", reason="x", entry_mode=EntryMode.NEXT_OPEN,
            entry_price=None, stop_price=Decimal("99.00"), target_price=None,
        )
    )
    broker.process_bar(4, candles[4])  # NEXT_OPEN fill bar: low 97 -> stopped on the fill bar
    assert broker.positions["S2"].exit_reason == "STOP"
    broker2 = _stack(entry_mode="NEXT_OPEN")[2]
    broker2.place(
        SignalDecision(
            signal_id="S3", source_event_id="E3", bar_index=2, bar_ms=0, poi_idx=0, poi_record_id="poi-0",
            side=Side.LONG, status="ACCEPTED", reason="x", entry_mode=EntryMode.NEXT_OPEN,
            entry_price=None, stop_price=Decimal("98.50"), target_price=None,
        )
    )
    broker2.process_bar(3, candles[3])  # fills at 100.00
    broker2.process_bar(5, candles[5])  # opens 98.00, below the 98.50 stop
    assert broker2.positions["S3"].exit_reason == "STOP_GAP"
    assert broker2.positions["S3"].exit_price == Decimal("98.0")


def test_pending_limit_orders_expire(candles) -> None:  # type: ignore[no-untyped-def]
    _, policy, broker = _stack(pending_expiry_bars=2)
    snap = _snapshot(candles[0], [_poi(0, "BULLISH", "90.00", "91.00")])
    signal = policy.on_events([_event("PERMISSION_ENTERED_ACTIONABLE", 0)], snap, broker).signals[0]
    broker.place(signal)
    assert broker.expire(1) == 0
    assert broker.expire(2) == 1
    assert broker.orders[signal.signal_id].status == "EXPIRED"


def test_costs_default_to_zero_and_are_applied_when_configured(candles) -> None:  # type: ignore[no-untyped-def]
    config = _config()
    assert config.slippage == 0 and config.commission_per_unit == 0
    _, _, broker = _stack(entry_mode="NEXT_OPEN", slippage="0.10", commission_per_unit="0.01")
    from botdryrun.policy import SignalDecision

    broker.place(
        SignalDecision(
            signal_id="S4", source_event_id="E4", bar_index=2, bar_ms=0, poi_idx=0, poi_record_id="poi-0",
            side=Side.LONG, status="ACCEPTED", reason="x", entry_mode=EntryMode.NEXT_OPEN,
            entry_price=None, stop_price=Decimal("99.00"), target_price=None,
        )
    )
    broker.process_bar(3, candles[3])
    position = broker.positions["S4"]
    assert position.entry_price == Decimal("100.10")
    assert [e.kind for e in broker.ledger] == ["COMMISSION_ENTRY"]
