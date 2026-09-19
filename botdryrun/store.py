"""Persistent state (stdlib ``sqlite3``), one atomic transaction per bar.

Kernel objects are not serializable, so recovery is EVENT-SOURCED: the store
keeps the ordered, validated INPUTS processed so far (host bars and the
context candles released with each of them) plus the DERIVED state and the
per-bar scanner digest. On restart the engine re-runs the scanner over the
persisted inputs, requires every rebuilt bar digest to equal the persisted
one, and only then continues. See ``botdryrun.engine``.

Tables split into two groups:

* deterministic content (everything journals are exported from): inputs,
  bar summaries, canonical scanner lines, POI registry, P5 decisions (latest
  per POI, and every per-bar decision row with the RC4 market-framework
  fields), P8 events (= processed event ids), signals (= processed signal
  ids), paper trade intents, orders, positions, ledger, incidents;
* operational, NON-deterministic records: ``runs``, ``bar_timing``
  (wall-clock) and ``scanner_pin_checks`` (one row per run). They are never
  part of a journal digest.
"""

from __future__ import annotations

import sqlite3
import zlib
from collections.abc import Iterable, Iterator, Sequence
from contextlib import contextmanager
from pathlib import Path
from typing import Any

__all__ = ["SCHEMA_VERSION", "StateStore"]

SCHEMA_VERSION = "2"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS host_inputs (
    bar_index INTEGER PRIMARY KEY,
    event_ms INTEGER NOT NULL UNIQUE,
    availability_ms INTEGER NOT NULL,
    trading_day TEXT NOT NULL,
    fingerprint TEXT NOT NULL,
    candle_json TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS context_inputs (
    timeframe TEXT NOT NULL,
    event_ms INTEGER NOT NULL,
    availability_ms INTEGER NOT NULL,
    released_at_bar_index INTEGER NOT NULL,
    fingerprint TEXT NOT NULL,
    candle_json TEXT NOT NULL,
    PRIMARY KEY (timeframe, event_ms)
);
CREATE TABLE IF NOT EXISTS bar_summary (
    bar_index INTEGER PRIMARY KEY,
    bar_ms INTEGER NOT NULL,
    event_utc TEXT NOT NULL,
    trading_day TEXT NOT NULL,
    primed INTEGER NOT NULL,
    registry_size INTEGER NOT NULL,
    new_registry_pois INTEGER NOT NULL,
    evaluated INTEGER NOT NULL,
    actionable INTEGER NOT NULL,
    fresh_at_close INTEGER NOT NULL,
    mitigated_at_close INTEGER NOT NULL,
    invalidated_at_close INTEGER NOT NULL,
    p8_events INTEGER NOT NULL,
    p8_terminal_events INTEGER NOT NULL,
    events_consumed INTEGER NOT NULL,
    events_duplicate INTEGER NOT NULL,
    signals INTEGER NOT NULL,
    trade_intents INTEGER NOT NULL,
    fills INTEGER NOT NULL,
    exits INTEGER NOT NULL,
    cancels INTEGER NOT NULL,
    open_positions INTEGER NOT NULL,
    pending_orders INTEGER NOT NULL,
    balance TEXT NOT NULL,
    equity TEXT NOT NULL,
    bar_digest TEXT NOT NULL,
    chain_digest TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS bar_lines (
    bar_index INTEGER NOT NULL,
    stream TEXT NOT NULL,
    trading_day TEXT NOT NULL,
    n_lines INTEGER NOT NULL,
    blob BLOB NOT NULL,
    PRIMARY KEY (bar_index, stream)
);
CREATE TABLE IF NOT EXISTS pois (
    record_id TEXT PRIMARY KEY,
    poi_idx INTEGER,
    poi_type TEXT NOT NULL,
    direction TEXT NOT NULL,
    family TEXT NOT NULL,
    source_timeframe TEXT NOT NULL,
    effective_timeframe TEXT NOT NULL,
    zone_top TEXT NOT NULL,
    zone_bottom TEXT NOT NULL,
    source_time_utc TEXT NOT NULL,
    availability_time_utc TEXT NOT NULL,
    fresh_active INTEGER,
    terminal_reason TEXT,
    terminal_time_utc TEXT,
    first_seen_bar_index INTEGER NOT NULL,
    last_changed_bar_index INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS poi_decisions (
    record_id TEXT PRIMARY KEY,
    poi_idx INTEGER NOT NULL,
    bar_index INTEGER NOT NULL,
    permission TEXT NOT NULL,
    permission_code INTEGER NOT NULL,
    actionable INTEGER NOT NULL,
    final_score INTEGER NOT NULL,
    lifecycle TEXT NOT NULL,
    btmm_valid INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS decision_rows (
    bar_index INTEGER NOT NULL,
    record_id TEXT NOT NULL,
    poi_idx INTEGER NOT NULL,
    permission TEXT NOT NULL,
    permission_code INTEGER NOT NULL,
    actionable INTEGER NOT NULL,
    final_score INTEGER NOT NULL,
    lifecycle TEXT NOT NULL,
    btmm_valid INTEGER NOT NULL,
    framework TEXT,
    fib_bucket TEXT,
    retracement_pct TEXT,
    range_position TEXT,
    sweep_before_poi INTEGER NOT NULL,
    btmm_pretrade_reason TEXT,
    btmm_distraction INTEGER NOT NULL,
    btmm_delay INTEGER NOT NULL,
    btmm_wipeout INTEGER NOT NULL,
    btmm_true_failure INTEGER NOT NULL,
    poi_dwell_bars INTEGER NOT NULL,
    poi_touch_count INTEGER NOT NULL,
    poi_zone_return_count INTEGER NOT NULL,
    interaction_episode TEXT,
    PRIMARY KEY (bar_index, poi_idx)
);
CREATE TABLE IF NOT EXISTS trade_intents (
    intent_id TEXT PRIMARY KEY,
    source_event_id TEXT NOT NULL UNIQUE,
    bar_index INTEGER NOT NULL,
    bar_ms INTEGER NOT NULL,
    trading_day TEXT NOT NULL,
    poi_idx INTEGER NOT NULL,
    poi_record_id TEXT NOT NULL,
    direction TEXT NOT NULL,
    poi_type TEXT,
    source_timeframe TEXT,
    effective_timeframe TEXT,
    zone_bottom TEXT,
    zone_top TEXT,
    event_permission_code INTEGER NOT NULL,
    permission TEXT,
    final_score INTEGER,
    btmm_valid INTEGER NOT NULL,
    btmm_pretrade_reason TEXT,
    framework TEXT,
    range_position TEXT,
    fib_bucket TEXT,
    retracement_pct TEXT,
    sweep_before_poi INTEGER,
    interaction_episode TEXT,
    signal_id TEXT,
    signal_status TEXT,
    signal_reason TEXT,
    execution_mode TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS scanner_pin_checks (
    run_no INTEGER PRIMARY KEY,
    pinned_commit TEXT NOT NULL,
    pinned_digest TEXT NOT NULL,
    observed_digest TEXT NOT NULL,
    session_pinned_digest TEXT,
    file_count INTEGER NOT NULL,
    status TEXT NOT NULL,
    overridden INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS events (
    event_id TEXT PRIMARY KEY,
    bar_index INTEGER NOT NULL,
    bar_ms INTEGER NOT NULL,
    sequence_in_bar INTEGER NOT NULL,
    event_type TEXT NOT NULL,
    poi_idx INTEGER NOT NULL,
    poi_record_id TEXT NOT NULL,
    poi_bullish INTEGER NOT NULL,
    tier INTEGER NOT NULL,
    btmm_valid INTEGER NOT NULL,
    permission INTEGER NOT NULL,
    lifecycle INTEGER NOT NULL,
    terminal_reason TEXT
);
CREATE TABLE IF NOT EXISTS signals (
    signal_id TEXT PRIMARY KEY,
    source_event_id TEXT NOT NULL,
    bar_index INTEGER NOT NULL,
    bar_ms INTEGER NOT NULL,
    poi_idx INTEGER NOT NULL,
    poi_record_id TEXT NOT NULL,
    side TEXT,
    status TEXT NOT NULL,
    reason TEXT NOT NULL,
    entry_mode TEXT NOT NULL,
    entry_price TEXT,
    stop_price TEXT,
    target_price TEXT
);
CREATE TABLE IF NOT EXISTS orders (
    order_id TEXT PRIMARY KEY,
    signal_id TEXT NOT NULL,
    poi_record_id TEXT NOT NULL,
    poi_idx INTEGER NOT NULL,
    side TEXT NOT NULL,
    entry_mode TEXT NOT NULL,
    limit_price TEXT,
    stop_price TEXT NOT NULL,
    target_price TEXT,
    created_bar_index INTEGER NOT NULL,
    status TEXT NOT NULL,
    status_bar_index INTEGER NOT NULL,
    reason TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS positions (
    position_id TEXT PRIMARY KEY,
    order_id TEXT NOT NULL,
    poi_record_id TEXT NOT NULL,
    side TEXT NOT NULL,
    quantity TEXT NOT NULL,
    entry_price TEXT NOT NULL,
    entry_bar_index INTEGER NOT NULL,
    stop_price TEXT NOT NULL,
    target_price TEXT NOT NULL,
    status TEXT NOT NULL,
    exit_price TEXT,
    exit_bar_index INTEGER,
    exit_reason TEXT,
    realized_pnl TEXT
);
CREATE TABLE IF NOT EXISTS ledger (
    seq INTEGER PRIMARY KEY,
    bar_index INTEGER NOT NULL,
    kind TEXT NOT NULL,
    ref_id TEXT NOT NULL,
    amount TEXT NOT NULL,
    balance_after TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS incidents (
    incident_id TEXT PRIMARY KEY,
    kind TEXT NOT NULL,
    severity TEXT NOT NULL,
    timeframe TEXT NOT NULL,
    event_utc TEXT NOT NULL,
    detail TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS runs (
    run_no INTEGER PRIMARY KEY,
    command TEXT NOT NULL,
    pid INTEGER NOT NULL,
    started_wall_utc TEXT NOT NULL,
    ended_wall_utc TEXT,
    rebuilt_bars INTEGER NOT NULL DEFAULT 0,
    rebuild_verified INTEGER,
    rebuild_seconds REAL,
    processed_bars INTEGER NOT NULL DEFAULT 0,
    process_seconds REAL,
    outcome TEXT
);
CREATE TABLE IF NOT EXISTS bar_timing (
    bar_index INTEGER PRIMARY KEY,
    run_no INTEGER NOT NULL,
    scanner_seconds REAL NOT NULL,
    persist_seconds REAL NOT NULL
);
"""


def pack_lines(lines: Sequence[str]) -> bytes:
    return zlib.compress("\n".join(lines).encode("utf-8"), 6)


def unpack_lines(blob: bytes, n_lines: int) -> list[str]:
    if n_lines == 0:
        return []
    return zlib.decompress(blob).decode("utf-8").split("\n")


class StateStore:
    FILENAME = "bot_state.sqlite3"

    def __init__(self, state_dir: Path) -> None:
        state_dir.mkdir(parents=True, exist_ok=True)
        self.path = state_dir / self.FILENAME
        self.conn = sqlite3.connect(str(self.path), isolation_level=None)
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA synchronous=FULL")
        self.conn.executescript(_SCHEMA)
        if self.get_meta("schema_version") is None:
            self.set_meta("schema_version", SCHEMA_VERSION)

    def close(self) -> None:
        self.conn.close()

    # ------------------------------------------------------------------
    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        self.conn.execute("BEGIN IMMEDIATE")
        try:
            yield self.conn
        except BaseException:
            self.conn.execute("ROLLBACK")
            raise
        else:
            self.conn.execute("COMMIT")

    def get_meta(self, key: str) -> str | None:
        row = self.conn.execute("SELECT value FROM meta WHERE key=?", (key,)).fetchone()
        return None if row is None else str(row[0])

    def set_meta(self, key: str, value: str, conn: sqlite3.Connection | None = None) -> None:
        (conn or self.conn).execute(
            "INSERT INTO meta(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (key, value),
        )

    def query(self, sql: str, params: Iterable[Any] = ()) -> list[tuple[Any, ...]]:
        return [tuple(r) for r in self.conn.execute(sql, tuple(params)).fetchall()]

    def scalar(self, sql: str, params: Iterable[Any] = ()) -> Any:
        row = self.conn.execute(sql, tuple(params)).fetchone()
        return None if row is None else row[0]

    def processed_bar_count(self) -> int:
        return int(self.scalar("SELECT COUNT(*) FROM bar_summary"))
