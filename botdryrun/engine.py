"""Replay engine: feed -> scanner -> events -> policy -> paper broker -> store.

RESTART RECOVERY (event-sourced)
--------------------------------
Scanner kernel objects cannot be serialized, so the store persists the
ordered INPUTS the scanner consumed (each processed host bar, and every
context candle together with the host bar it was released with) plus the
per-bar scanner digest and chain digest. Every ``run()`` — first start,
resume after a pause, or recovery after a crash — does the same thing:

1. load and validate the feed (``botdryrun.market_data``);
2. check the feed agrees with the persisted inputs for every processed bar
   (``FeedRevisionError`` otherwise — the source was revised);
3. re-run the scanner over the PERSISTED inputs for bars
   ``0..last_processed`` and require every rebuilt bar digest and the chain
   digest to equal the persisted ones (``RebuildDigestMismatchError``
   otherwise). Nothing is dispatched during this phase: events rebuilt here
   must already be in the processed-event set;
4. restore bot state (processed ids, orders, positions, ledger) from the
   store and continue with bar ``last_processed + 1``.

SCANNER PIN: before step 1, every run fingerprints the scanner source this
process imports and compares it with the pin (``botdryrun.scanner_pin``) and
with the pin recorded when the session was created. A mismatch refuses the
run (``ScannerPinMismatchError``) unless the engine was built with
``allow_scanner_mismatch=True``; every check -- including a refusal and an
override -- is recorded in ``scanner_pin_checks`` and the journal manifest.

Each bar's derived state is written in ONE sqlite transaction. A crash
before COMMIT leaves no trace of that bar, so on restart it is processed
exactly once; a crash after COMMIT is simply a completed bar.

The scanner iterator needs the host window up front
(``iter_level_a_bars`` is single-pass over a given series), so the engine
builds it over "persisted inputs + remaining validated feed" and steps it
one bar at a time. By the scanner's no-lookahead property (proven by
truncate-and-extend in ``tests/unit/test_rc3_daily_authority.py``) the output
for bar N never depends on bars after N.
"""

from __future__ import annotations

import json
import os
import sqlite3
import time
from collections.abc import Callable, Iterator, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from enum import StrEnum
from pathlib import Path

from botdryrun.broker import LedgerEntry, Order, PaperBroker, Position
from botdryrun.config import BotConfig, EntryMode
from botdryrun.domain import (
    GENESIS_CHAIN_DIGEST,
    ScannerBarSnapshot,
    ScannerSource,
    fold_chain_digest,
)
from botdryrun.events import P8EventConsumer
from botdryrun.intents import TRADE_INTENT_COLUMNS, build_trade_intents
from botdryrun.market_data import (
    FeedItem,
    ValidatedFeed,
    assemble_feed,
    candle_fingerprint,
    load_feed_items,
)
from botdryrun.policy import FixedFractionalRiskPolicy, PracticePolicy, Side
from botdryrun.safety import EXECUTION_MODE, assert_paper_mode
from botdryrun.scanner_pin import (
    ScannerPin,
    ScannerPinCheck,
    ScannerPinMismatchError,
    evaluate_scanner_pin,
    pinned,
    refusal_message,
)
from botdryrun.store import StateStore, pack_lines
from btmm_ai_scanner.config.enums import Timeframe
from btmm_ai_scanner.contracts.normalized_candle import NormalizedCandle

__all__ = [
    "BotEngine",
    "EngineStateError",
    "FeedRevisionError",
    "RebuildDigestMismatchError",
    "RunOutcome",
    "RunReport",
    "ScannerPinMismatchError",
    "SessionMismatchError",
]


class EngineStateError(RuntimeError):
    pass


class SessionMismatchError(EngineStateError):
    pass


class FeedRevisionError(EngineStateError):
    """The feed no longer matches inputs the bot already processed."""


class RebuildDigestMismatchError(EngineStateError):
    """Re-running the scanner over persisted inputs did not reproduce state."""


class RunOutcome(StrEnum):
    COMPLETED = "COMPLETED"
    PAUSED = "PAUSED"
    HALTED_GAP = "HALTED_GAP"
    HALTED_FEED_ERROR = "HALTED_FEED_ERROR"


@dataclass
class RunReport:
    outcome: RunOutcome
    run_no: int
    rebuilt_bars: int
    processed_bars: int
    total_bars: int
    last_bar_index: int | None
    last_bar_utc: str | None
    chain_digest: str
    rebuild_seconds: float
    process_seconds: float
    seconds_per_bar: float | None
    incidents: int
    feed_error: str | None = None
    scanner_pin: dict[str, object] | None = None
    notes: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, object]:
        return {
            "outcome": self.outcome.value,
            "run_no": self.run_no,
            "rebuilt_bars": self.rebuilt_bars,
            "processed_bars": self.processed_bars,
            "total_bars_processed_in_state": self.total_bars,
            "last_bar_index": self.last_bar_index,
            "last_bar_utc": self.last_bar_utc,
            "chain_digest": self.chain_digest,
            "rebuild_seconds": round(self.rebuild_seconds, 3),
            "process_seconds": round(self.process_seconds, 3),
            "seconds_per_bar": None if self.seconds_per_bar is None else round(self.seconds_per_bar, 3),
            "incidents": self.incidents,
            "feed_error": self.feed_error,
            "scanner_pin": self.scanner_pin,
            "execution_mode": EXECUTION_MODE,
        }


FaultInjector = Callable[[str, int], None]
FeedLoader = Callable[[BotConfig], Sequence[FeedItem]]


def _now() -> str:
    return datetime.now(tz=UTC).isoformat()


def _dec(value: object) -> Decimal | None:
    return None if value is None else Decimal(str(value))


def _txt(value: object) -> str | None:
    return None if value is None else str(value)


class BotEngine:
    def __init__(
        self,
        state_dir: Path,
        config: BotConfig | None = None,
        *,
        feed_loader: FeedLoader | None = None,
        scanner_source: ScannerSource | None = None,
        fault_injector: FaultInjector | None = None,
        command: str = "run",
        allow_scanner_mismatch: bool = False,
        scanner_pin: ScannerPin | None = None,
    ) -> None:
        self.state_dir = state_dir
        self.store = StateStore(state_dir)
        persisted = self.store.get_meta("config_json")
        if config is None:
            if persisted is None:
                raise EngineStateError(f"no bot session in {state_dir}; start one with 'replay'")
            config = BotConfig.from_json(persisted)
        elif persisted is None:
            self.store.set_meta("config_json", config.to_json())
            self.store.set_meta("status", "NEW")
            session_pin = scanner_pin or pinned()
            self.store.set_meta(
                "scanner_pin",
                json.dumps(
                    {
                        "commit": session_pin.commit,
                        "source_digest": session_pin.source_digest,
                        "fingerprint_version": session_pin.fingerprint_version,
                    },
                    sort_keys=True,
                ),
            )
        elif persisted != config.to_json():
            raise SessionMismatchError(
                f"{state_dir} already holds a session with a different configuration; "
                "use 'resume'/'restart' or a new --state-dir"
            )
        assert_paper_mode(config.execution_mode)
        self.config = config
        self._feed_loader: FeedLoader = feed_loader or load_feed_items
        if scanner_source is None:
            from botdryrun.scanner_adapter import LevelAScannerSource

            scanner_source = LevelAScannerSource(profile=config.scanner_profile)
        self._scanner = scanner_source
        self._pin = scanner_pin or pinned()
        self._allow_scanner_mismatch = allow_scanner_mismatch
        self._fault = fault_injector
        self._command = command
        self._poisoned = False
        self.risk = FixedFractionalRiskPolicy(config.risk_fraction, config.max_concurrent_positions)
        self.policy = PracticePolicy(config, self.risk)

    def close(self) -> None:
        self.store.close()

    # ------------------------------------------------------------------
    def status(self) -> str:
        return self.store.get_meta("status") or "NEW"

    def run(self, max_bars: int | None = None, *, allow_unclean: bool = True) -> RunReport:
        if self._poisoned:
            raise EngineStateError("engine crashed mid-bar; construct a new engine to recover")
        if not allow_unclean and self.status() == "RUNNING":
            raise EngineStateError(
                "state is RUNNING (a previous process did not stop cleanly); use 'restart'"
            )
        store = self.store
        cfg = self.config
        run_no = int(store.scalar("SELECT COALESCE(MAX(run_no),0)+1 FROM runs"))
        pin_check = self._check_scanner_pin(run_no)
        with store.transaction() as conn:
            conn.execute(
                "INSERT INTO runs(run_no,command,pid,started_wall_utc) VALUES(?,?,?,?)",
                (run_no, self._command, os.getpid(), _now()),
            )
            self._record_pin_check(conn, run_no, pin_check)
            store.set_meta("status", "RUNNING", conn)

        feed = assemble_feed(
            self._feed_loader(cfg),
            host_timeframe=Timeframe(cfg.host_timeframe),
            gap_policy=cfg.gap_policy,
        )
        with store.transaction() as conn:
            for inc in feed.incidents:
                conn.execute(
                    "INSERT OR IGNORE INTO incidents VALUES(?,?,?,?,?,?)",
                    (inc.incident_id, inc.kind, inc.severity.value, inc.timeframe, inc.event_utc, inc.detail),
                )

        processed = store.processed_bar_count()
        host_series, context_series = self._reconcile_inputs(feed, processed)
        iterator: Iterator[ScannerBarSnapshot] = self._scanner.iterate(
            Timeframe(cfg.host_timeframe), host_series, context_series
        )

        # ---- phase 1: rebuild + verify ---------------------------------
        t0 = time.perf_counter()
        chain = self._verify_rebuild(iterator, processed)
        rebuild_seconds = time.perf_counter() - t0
        with store.transaction() as conn:
            conn.execute(
                "UPDATE runs SET rebuilt_bars=?, rebuild_verified=1, rebuild_seconds=? WHERE run_no=?",
                (processed, rebuild_seconds, run_no),
            )
            store.set_meta(
                "last_rebuild",
                json.dumps({"run_no": run_no, "bars": processed, "verified": True}),
                conn,
            )

        # ---- phase 2: continue ----------------------------------------
        consumer = P8EventConsumer(r[0] for r in store.query("SELECT event_id FROM events"))
        broker = self._load_broker()
        poi_cache = {
            r[0]: (tuple(r[:14]), int(r[14]))
            for r in store.query(
                "SELECT record_id,poi_idx,poi_type,direction,family,source_timeframe,"
                "effective_timeframe,zone_top,zone_bottom,source_time_utc,availability_time_utc,"
                "fresh_active,terminal_reason,terminal_time_utc,first_seen_bar_index FROM pois"
            )
        }
        release_by_bar = self._release_schedule(feed, context_series)

        t1 = time.perf_counter()
        done = 0
        index = processed
        while index < len(host_series) and (max_bars is None or done < max_bars):
            ts = time.perf_counter()
            snapshot = next(iterator)
            scanner_seconds = time.perf_counter() - ts
            if snapshot.bar_index != index:
                raise EngineStateError(f"scanner yielded bar {snapshot.bar_index}, expected {index}")
            try:
                chain = self._step(
                    snapshot,
                    chain,
                    consumer,
                    broker,
                    poi_cache,
                    release_by_bar.get(index, []),
                    run_no,
                    scanner_seconds,
                )
            except BaseException:
                self._poisoned = True
                raise
            done += 1
            index += 1
        process_seconds = time.perf_counter() - t1

        feed_error: str | None = None
        if index < len(host_series):
            outcome = RunOutcome.PAUSED
        elif feed.fatal is not None:
            outcome = RunOutcome.HALTED_FEED_ERROR
            feed_error = f"{type(feed.fatal).__name__}: {feed.fatal}"
        elif feed.halted_on_gap:
            outcome = RunOutcome.HALTED_GAP
        else:
            outcome = RunOutcome.COMPLETED

        total = store.processed_bar_count()
        last_row = store.query(
            "SELECT bar_index,event_utc FROM bar_summary ORDER BY bar_index DESC LIMIT 1"
        )
        with store.transaction() as conn:
            conn.execute(
                "UPDATE runs SET ended_wall_utc=?, processed_bars=?, process_seconds=?, outcome=? WHERE run_no=?",
                (_now(), done, process_seconds, outcome.value, run_no),
            )
            store.set_meta("status", outcome.value, conn)
        incidents = int(store.scalar("SELECT COUNT(*) FROM incidents"))
        from botdryrun.journals import export_journals

        export_journals(store, self.state_dir / "journals")
        report = RunReport(
            outcome=outcome,
            run_no=run_no,
            rebuilt_bars=processed,
            processed_bars=done,
            total_bars=total,
            last_bar_index=int(last_row[0][0]) if last_row else None,
            last_bar_utc=str(last_row[0][1]) if last_row else None,
            chain_digest=chain,
            rebuild_seconds=rebuild_seconds,
            process_seconds=process_seconds,
            seconds_per_bar=(process_seconds / done) if done else None,
            incidents=incidents,
            feed_error=feed_error,
            scanner_pin=pin_check.as_dict(),
        )
        if outcome is RunOutcome.HALTED_FEED_ERROR and feed.fatal is not None:
            raise feed.fatal
        return report

    # ------------------------------------------------------------------
    def _check_scanner_pin(self, run_no: int) -> ScannerPinCheck:
        raw = self.store.get_meta("scanner_pin")
        session_digest = str(json.loads(raw)["source_digest"]) if raw else None
        check = evaluate_scanner_pin(
            self._pin,
            session_pinned_digest=session_digest,
            allow_mismatch=self._allow_scanner_mismatch,
        )
        if check.status == "MISMATCH_REFUSED":
            # Record the refusal; the session status is left untouched.
            with self.store.transaction() as conn:
                conn.execute(
                    "INSERT INTO runs(run_no,command,pid,started_wall_utc,ended_wall_utc,outcome) "
                    "VALUES(?,?,?,?,?,?)",
                    (run_no, self._command, os.getpid(), _now(), _now(), "REFUSED_SCANNER_PIN"),
                )
                self._record_pin_check(conn, run_no, check)
            raise ScannerPinMismatchError(refusal_message(check))
        return check

    def _record_pin_check(
        self, conn: sqlite3.Connection, run_no: int, check: ScannerPinCheck
    ) -> None:
        conn.execute(
            "INSERT INTO scanner_pin_checks VALUES(?,?,?,?,?,?,?,?)",
            (run_no, check.pinned_commit, check.pinned_digest, check.observed_digest,
             check.session_pinned_digest, check.file_count, check.status, int(check.overridden)),
        )
        if check.overridden:
            self.store.set_meta("scanner_pin_overridden", "1", conn)

    def _reconcile_inputs(
        self, feed: ValidatedFeed, processed: int
    ) -> tuple[list[NormalizedCandle], dict[Timeframe, list[NormalizedCandle]]]:
        store = self.store
        rows = store.query("SELECT bar_index,fingerprint,candle_json FROM host_inputs ORDER BY bar_index")
        if len(rows) != processed:
            raise EngineStateError("host input ledger and bar summaries disagree")
        if len(feed.host) < processed:
            raise FeedRevisionError(
                f"feed now has {len(feed.host)} valid host bars but {processed} were already processed"
            )
        host: list[NormalizedCandle] = []
        for (bar_index, fingerprint, candle_json), fed in zip(rows, feed.host, strict=False):
            if candle_fingerprint(fed) != fingerprint:
                raise FeedRevisionError(f"host bar {bar_index} differs from the persisted input")
            host.append(NormalizedCandle.model_validate_json(candle_json))
        host.extend(feed.host[processed:])

        persisted_ctx = store.query(
            "SELECT timeframe,fingerprint,candle_json,availability_ms,event_ms FROM context_inputs "
            "ORDER BY timeframe,availability_ms,event_ms"
        )
        persisted_fp = {r[1] for r in persisted_ctx}
        feed_released_fp: set[str] = set()
        context: dict[Timeframe, list[NormalizedCandle]] = {tf: [] for tf in feed.context}
        for tf_name, _fp, candle_json, _a, _e in persisted_ctx:
            context.setdefault(Timeframe(tf_name), []).append(
                NormalizedCandle.model_validate_json(candle_json)
            )
        for timeframe, candles in feed.context.items():
            for c in candles:
                key = (timeframe.value, int(c.event_time_utc.timestamp() * 1000))
                release = feed.release_index.get(key)
                if release is None:
                    continue
                if processed > 0 and release <= processed - 1:
                    feed_released_fp.add(candle_fingerprint(c))
                else:
                    context[timeframe].append(c)
        if processed > 0 and feed_released_fp != persisted_fp:
            raise FeedRevisionError("context candles already released differ from the persisted inputs")
        for series in context.values():
            series.sort(key=lambda c: (c.availability_time_utc, c.event_time_utc))
        return host, context

    def _release_schedule(
        self, feed: ValidatedFeed, context: dict[Timeframe, list[NormalizedCandle]]
    ) -> dict[int, list[NormalizedCandle]]:
        schedule: dict[int, list[NormalizedCandle]] = {}
        for timeframe, candles in context.items():
            for c in candles:
                key = (timeframe.value, int(c.event_time_utc.timestamp() * 1000))
                release = feed.release_index.get(key)
                if release is None:
                    continue
                # Warm-up candles (-1) are persisted with bar 0.
                schedule.setdefault(max(release, 0), []).append(c)
        return schedule

    def _verify_rebuild(self, iterator: Iterator[ScannerBarSnapshot], processed: int) -> str:
        chain = GENESIS_CHAIN_DIGEST
        if processed == 0:
            return chain
        rows = self.store.query("SELECT bar_index,bar_digest,chain_digest FROM bar_summary ORDER BY bar_index")
        known_events = {r[0] for r in self.store.query("SELECT event_id FROM events")}
        for bar_index, bar_digest, chain_digest in rows:
            snapshot = next(iterator)
            chain = fold_chain_digest(chain, snapshot.digest)
            if snapshot.bar_index != bar_index or snapshot.digest != bar_digest or chain != chain_digest:
                self.store.set_meta(
                    "last_rebuild",
                    json.dumps({"bars": processed, "verified": False, "failed_bar": bar_index}),
                )
                self.store.set_meta("status", "REBUILD_MISMATCH")
                raise RebuildDigestMismatchError(
                    f"rebuilt scanner digest differs from the persisted digest at bar {bar_index}"
                )
            for event in snapshot.events:
                if event.event_id not in known_events:
                    self.store.set_meta("status", "REBUILD_MISMATCH")
                    raise RebuildDigestMismatchError(
                        f"rebuild produced unknown event {event.event_id} at bar {bar_index}"
                    )
        return chain

    def _load_broker(self) -> PaperBroker:
        s = self.store
        orders = [
            Order(
                order_id=r[0], signal_id=r[1], poi_record_id=r[2], poi_idx=int(r[3]), side=Side(r[4]),
                entry_mode=EntryMode(r[5]), limit_price=_dec(r[6]), stop_price=Decimal(r[7]),
                target_price=_dec(r[8]), created_bar_index=int(r[9]), status=r[10],
                status_bar_index=int(r[11]), reason=r[12],
            )
            for r in s.query("SELECT * FROM orders")
        ]
        positions = [
            Position(
                position_id=r[0], order_id=r[1], poi_record_id=r[2], side=Side(r[3]),
                quantity=Decimal(r[4]), entry_price=Decimal(r[5]), entry_bar_index=int(r[6]),
                stop_price=Decimal(r[7]), target_price=Decimal(r[8]), status=r[9],
                exit_price=_dec(r[10]), exit_bar_index=None if r[11] is None else int(r[11]),
                exit_reason=r[12], realized_pnl=_dec(r[13]),
            )
            for r in s.query("SELECT * FROM positions")
        ]
        ledger = [
            LedgerEntry(int(r[0]), int(r[1]), r[2], r[3], Decimal(r[4]), Decimal(r[5]))
            for r in s.query("SELECT * FROM ledger ORDER BY seq")
        ]
        return PaperBroker(self.config, self.risk, orders=orders, positions=positions, ledger=ledger)

    # ------------------------------------------------------------------
    def _step(
        self,
        snap: ScannerBarSnapshot,
        chain: str,
        consumer: P8EventConsumer,
        broker: PaperBroker,
        poi_cache: dict[str, tuple[tuple[object, ...], int]],
        released: list[NormalizedCandle],
        run_no: int,
        scanner_seconds: float,
    ) -> str:
        i = snap.bar_index
        t_persist = time.perf_counter()
        broker.begin_bar()
        batch = consumer.consume(snap.events)
        execution = broker.process_bar(i, snap.candle)
        actions = self.policy.on_events(batch.new_events, snap, broker)
        intents = build_trade_intents(batch.new_events, snap, actions.signals)
        cancels = 0
        for cancel in actions.cancels:
            cancels += broker.cancel_for_poi(cancel.poi_record_id, cancel.reason, i)
        for signal in actions.signals:
            broker.place(signal)
        expired = broker.expire(i)
        equity = broker.equity(snap.candle.close)
        new_chain = fold_chain_digest(chain, snap.digest)
        candle = snap.candle

        with self.store.transaction() as conn:
            conn.execute(
                "INSERT INTO host_inputs VALUES(?,?,?,?,?,?)",
                (
                    i,
                    int(candle.event_time_utc.timestamp() * 1000),
                    int(candle.availability_time_utc.timestamp() * 1000),
                    snap.trading_day,
                    candle_fingerprint(candle),
                    candle.model_dump_json(),
                ),
            )
            for c in released:
                event_ms = int(c.event_time_utc.timestamp() * 1000)
                conn.execute(
                    "INSERT INTO context_inputs VALUES(?,?,?,?,?,?)",
                    (
                        c.timeframe.value,
                        event_ms,
                        int(c.availability_time_utc.timestamp() * 1000),
                        i,
                        candle_fingerprint(c),
                        c.model_dump_json(),
                    ),
                )
            changed = []
            for poi in snap.pois:
                row = poi.as_row()
                cached = poi_cache.get(poi.record_id)
                if cached is not None and cached[0] == row:
                    continue
                first_seen = cached[1] if cached is not None else i
                changed.append((*row, first_seen, i))
                poi_cache[poi.record_id] = (row, first_seen)
            conn.executemany(
                "INSERT INTO pois VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT(record_id) DO UPDATE SET "
                "poi_idx=excluded.poi_idx, poi_type=excluded.poi_type, direction=excluded.direction, "
                "family=excluded.family, source_timeframe=excluded.source_timeframe, "
                "effective_timeframe=excluded.effective_timeframe, "
                "zone_top=excluded.zone_top, zone_bottom=excluded.zone_bottom, "
                "source_time_utc=excluded.source_time_utc, availability_time_utc=excluded.availability_time_utc, "
                "fresh_active=excluded.fresh_active, terminal_reason=excluded.terminal_reason, "
                "terminal_time_utc=excluded.terminal_time_utc, last_changed_bar_index=excluded.last_changed_bar_index",
                changed,
            )
            conn.executemany(
                "INSERT INTO poi_decisions VALUES(?,?,?,?,?,?,?,?,?) ON CONFLICT(record_id) DO UPDATE SET "
                "poi_idx=excluded.poi_idx, bar_index=excluded.bar_index, permission=excluded.permission, "
                "permission_code=excluded.permission_code, actionable=excluded.actionable, "
                "final_score=excluded.final_score, lifecycle=excluded.lifecycle, btmm_valid=excluded.btmm_valid",
                [
                    (d.record_id, d.poi_idx, i, d.permission, d.permission_code, int(d.actionable),
                     d.final_score, d.lifecycle, int(d.btmm_valid))
                    for d in snap.decisions
                ],
            )
            conn.executemany(
                "INSERT INTO decision_rows(bar_index,record_id,poi_idx,permission,permission_code,"
                "actionable,final_score,lifecycle,btmm_valid,framework,fib_bucket,retracement_pct,"
                "range_position,sweep_before_poi,btmm_pretrade_reason,btmm_distraction,btmm_delay,"
                "btmm_wipeout,btmm_true_failure,poi_dwell_bars,poi_touch_count,"
                "poi_zone_return_count,interaction_episode) "
                "VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                [(i, *d.as_row()) for d in snap.decisions],
            )
            conn.executemany(
                "INSERT INTO trade_intents VALUES(" + ",".join("?" * len(TRADE_INTENT_COLUMNS)) + ")",
                [t.as_row() for t in intents],
            )
            for stream, lines in (("P3", snap.p3_lines), ("P5", snap.p5_lines), ("P8", snap.p8_lines)):
                conn.execute(
                    "INSERT INTO bar_lines VALUES(?,?,?,?,?)",
                    (i, stream, snap.trading_day, len(lines), pack_lines(lines)),
                )
            conn.executemany(
                "INSERT INTO events VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",
                [
                    (e.event_id, i, e.bar_ms, e.sequence_in_bar, e.event_type, e.poi_idx, e.poi_record_id,
                     int(e.poi_bullish), e.tier, int(e.btmm_valid), e.permission, e.lifecycle, e.terminal_reason)
                    for e in batch.new_events
                ],
            )
            conn.executemany(
                "INSERT INTO signals VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",
                [
                    (s.signal_id, s.source_event_id, s.bar_index, s.bar_ms, s.poi_idx, s.poi_record_id,
                     None if s.side is None else s.side.value, s.status, s.reason, s.entry_mode.value,
                     _txt(s.entry_price), _txt(s.stop_price), _txt(s.target_price))
                    for s in actions.signals
                ],
            )
            for order_id in sorted(broker.dirty_orders):
                o = broker.orders[order_id]
                conn.execute(
                    "INSERT OR REPLACE INTO orders VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (o.order_id, o.signal_id, o.poi_record_id, o.poi_idx, o.side.value, o.entry_mode.value,
                     _txt(o.limit_price), str(o.stop_price), _txt(o.target_price), o.created_bar_index,
                     o.status, o.status_bar_index, o.reason),
                )
            for position_id in sorted(broker.dirty_positions):
                p = broker.positions[position_id]
                conn.execute(
                    "INSERT OR REPLACE INTO positions VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (p.position_id, p.order_id, p.poi_record_id, p.side.value, str(p.quantity),
                     str(p.entry_price), p.entry_bar_index, str(p.stop_price), str(p.target_price), p.status,
                     _txt(p.exit_price), p.exit_bar_index, p.exit_reason, _txt(p.realized_pnl)),
                )
            conn.executemany(
                "INSERT INTO ledger VALUES(?,?,?,?,?,?)",
                [(e.seq, e.bar_index, e.kind, e.ref_id, str(e.amount), str(e.balance_after))
                 for e in broker.new_ledger],
            )
            conn.execute(
                "INSERT INTO bar_summary VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    i, snap.bar_ms, candle.event_time_utc.isoformat(), snap.trading_day, int(snap.primed),
                    len(snap.pois), snap.new_registry_pois, len(snap.decisions),
                    sum(1 for d in snap.decisions if d.actionable),
                    snap.fresh_at_close, snap.mitigated_at_close, snap.invalidated_at_close,
                    len(snap.events), sum(1 for e in snap.events if e.event_type == "POI_TERMINAL"),
                    len(batch.new_events), len(batch.duplicates),
                    len(actions.signals), len(intents), execution.fills, execution.exits, cancels + expired,
                    len(broker.open_positions()), len(broker.pending_orders()),
                    str(broker.balance), str(equity), snap.digest, new_chain,
                ),
            )
            self.store.set_meta("last_processed_bar_index", str(i), conn)
            self.store.set_meta("chain_digest", new_chain, conn)
            conn.execute(
                "INSERT OR REPLACE INTO bar_timing VALUES(?,?,?,?)",
                (i, run_no, scanner_seconds, time.perf_counter() - t_persist),
            )
            if self._fault is not None:
                self._fault("before_commit", i)
        if self._fault is not None:
            self._fault("after_commit", i)
        return new_chain
