"""Journal export.

Every journal is rendered from the store with a fixed column order and a
fixed ``ORDER BY``, contains no wall-clock value, and is written with ``\\n``
line endings — so two replays of the same window produce byte-identical
files. ``manifest.json`` lists the sha256 of each deterministic journal.

Deterministic journals:
  decision_journal.csv       one row per processed host bar
  p5_decision_journal.csv    one row per P5-evaluated POI per bar, including
                             the RC4 market-framework fields
  event_journal.csv          consumed P8 events, native order
  trade_intent_journal.csv   one paper trade intent per consumed
                             PERMISSION_ENTERED_ACTIONABLE event
  signal_journal.csv         every signal decision (accepted and skipped)
  order_journal.csv          paper orders and their final status
  trade_journal.csv          paper positions (entries/exits/PnL)
  ledger_journal.csv         balance ledger
  daily_authority_journal.csv  one row per FXCM trading day
  poi_registry.csv           registered POIs, latest persisted state
  incident_journal.csv       data-quality incidents
Operational (NOT deterministic, excluded from the manifest digests):
  perf_bar_timing.csv, runs.csv
"""

from __future__ import annotations

import csv
import hashlib
import io
import json
from collections.abc import Sequence
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from botdryrun.domain import DECISION_ROW_FIELDS
from botdryrun.intents import TRADE_INTENT_COLUMNS
from botdryrun.policy import PRACTICE_POLICY_LABEL
from botdryrun.safety import EXECUTION_MODE
from botdryrun.store import StateStore, unpack_lines
from tests.parity_support.rc3_daily_authority import fold_period_digest

__all__ = ["DAILY_COLUMNS", "daily_authority_rows", "export_journals"]

DAILY_AUTHORITY_COLUMNS: tuple[str, ...] = (
    "trading_day",
    "first_bar_ms",
    "last_bar_ms",
    "first_bar_utc",
    "last_bar_utc",
    "bars_processed",
    "new_p3_pois",
    "total_registry_pois",
    "pois_fresh_at_close",
    "pois_mitigated_at_close",
    "pois_invalidated_at_close",
    "p5_rows",
    "p5_actionable",
    "p8_events",
    "p8_terminal_events",
    "p3_digest",
    "p5_digest",
    "p8_digest",
)
DAILY_COLUMNS: tuple[str, ...] = (
    *DAILY_AUTHORITY_COLUMNS,
    "trade_intents",
    "signals_accepted",
    "signals_skipped",
    "fills",
    "exits",
    "cancels_or_expiries",
    "realized_pnl",
    "end_balance",
    "end_equity",
    "trade_digest",
)

_DETERMINISTIC_QUERIES: dict[str, tuple[Sequence[str], str]] = {
    "decision_journal.csv": (
        (
            "bar_index", "bar_ms", "event_utc", "trading_day", "primed", "registry_size",
            "new_registry_pois", "evaluated", "actionable", "fresh_at_close",
            "mitigated_at_close", "invalidated_at_close", "p8_events", "p8_terminal_events",
            "events_consumed", "events_duplicate", "signals", "trade_intents", "fills", "exits",
            "cancels",
            "open_positions", "pending_orders", "balance", "equity", "bar_digest", "chain_digest",
        ),
        "SELECT * FROM bar_summary ORDER BY bar_index",
    ),
    "p5_decision_journal.csv": (
        ("bar_index", *DECISION_ROW_FIELDS),
        "SELECT bar_index," + ",".join(DECISION_ROW_FIELDS)
        + " FROM decision_rows ORDER BY bar_index, poi_idx",
    ),
    "trade_intent_journal.csv": (
        TRADE_INTENT_COLUMNS,
        "SELECT " + ",".join(f"t.{c}" for c in TRADE_INTENT_COLUMNS)
        + " FROM trade_intents t JOIN events e ON e.event_id = t.source_event_id "
        "ORDER BY t.bar_index, e.sequence_in_bar",
    ),
    "event_journal.csv": (
        (
            "event_id", "bar_index", "bar_ms", "sequence_in_bar", "event_type", "poi_idx",
            "poi_record_id", "poi_bullish", "tier", "btmm_valid", "permission", "lifecycle",
            "terminal_reason",
        ),
        "SELECT * FROM events ORDER BY bar_index, sequence_in_bar",
    ),
    "signal_journal.csv": (
        (
            "signal_id", "source_event_id", "bar_index", "bar_ms", "poi_idx", "poi_record_id",
            "side", "status", "reason", "entry_mode", "entry_price", "stop_price", "target_price",
        ),
        "SELECT * FROM signals ORDER BY bar_index, source_event_id",
    ),
    "order_journal.csv": (
        (
            "order_id", "signal_id", "poi_record_id", "poi_idx", "side", "entry_mode",
            "limit_price", "stop_price", "target_price", "created_bar_index", "status",
            "status_bar_index", "reason",
        ),
        "SELECT * FROM orders ORDER BY created_bar_index, order_id",
    ),
    "trade_journal.csv": (
        (
            "position_id", "order_id", "poi_record_id", "side", "quantity", "entry_price",
            "entry_bar_index", "stop_price", "target_price", "status", "exit_price",
            "exit_bar_index", "exit_reason", "realized_pnl",
        ),
        "SELECT * FROM positions ORDER BY entry_bar_index, position_id",
    ),
    "ledger_journal.csv": (
        ("seq", "bar_index", "kind", "ref_id", "amount", "balance_after"),
        "SELECT * FROM ledger ORDER BY seq",
    ),
    "poi_registry.csv": (
        (
            "record_id", "poi_idx", "poi_type", "direction", "family", "source_timeframe",
            "effective_timeframe", "zone_top", "zone_bottom", "source_time_utc",
            "availability_time_utc", "fresh_active", "terminal_reason", "terminal_time_utc",
            "first_seen_bar_index", "last_changed_bar_index",
        ),
        "SELECT * FROM pois ORDER BY first_seen_bar_index, record_id",
    ),
    "incident_journal.csv": (
        ("incident_id", "kind", "severity", "timeframe", "event_utc", "detail"),
        "SELECT * FROM incidents ORDER BY event_utc, incident_id",
    ),
}


def _csv(columns: Sequence[str], rows: Sequence[Sequence[Any]]) -> str:
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(columns)
    for row in rows:
        writer.writerow(["" if v is None else v for v in row])
    return buffer.getvalue()


def _utc_from_ms(ms: int) -> str:
    return datetime.fromtimestamp(ms / 1000, tz=UTC).isoformat()


def daily_authority_rows(store: StateStore) -> list[dict[str, Any]]:
    days: dict[str, dict[str, Any]] = {}
    hashes: dict[str, dict[str, Any]] = {}
    for row in store.query(
        "SELECT bar_index,bar_ms,trading_day,registry_size,new_registry_pois,evaluated,actionable,"
        "fresh_at_close,mitigated_at_close,invalidated_at_close,p8_events,p8_terminal_events,"
        "trade_intents,fills,exits,cancels,balance,equity FROM bar_summary ORDER BY bar_index"
    ):
        (_i, bar_ms, day, registry, new, evaluated, actionable, fresh, mitigated, invalidated,
         p8, p8t, intents, fills, exits, cancels, balance, equity) = row
        d = days.get(day)
        if d is None:
            d = days[day] = {
                "trading_day": day, "first_bar_ms": bar_ms, "first_bar_utc": _utc_from_ms(bar_ms),
                "bars_processed": 0, "new_p3_pois": 0, "p5_rows": 0, "p5_actionable": 0,
                "p8_events": 0, "p8_terminal_events": 0, "trade_intents": 0, "fills": 0, "exits": 0,
                "cancels_or_expiries": 0,
            }
            hashes[day] = {s: hashlib.sha256() for s in ("P3", "P5", "P8")}
        d["last_bar_ms"] = bar_ms
        d["last_bar_utc"] = _utc_from_ms(bar_ms)
        d["bars_processed"] += 1
        d["new_p3_pois"] += new
        d["total_registry_pois"] = registry
        d["pois_fresh_at_close"] = fresh
        d["pois_mitigated_at_close"] = mitigated
        d["pois_invalidated_at_close"] = invalidated
        d["p5_rows"] += evaluated
        d["p5_actionable"] += actionable
        d["p8_events"] += p8
        d["p8_terminal_events"] += p8t
        d["trade_intents"] += intents
        d["fills"] += fills
        d["exits"] += exits
        d["cancels_or_expiries"] += cancels
        d["end_balance"] = balance
        d["end_equity"] = equity
    for bar_index, stream, day, n_lines, blob in store.query(
        "SELECT bar_index,stream,trading_day,n_lines,blob FROM bar_lines ORDER BY bar_index, stream"
    ):
        h = hashes[day][stream]
        for line in unpack_lines(bytes(blob), int(n_lines)):
            h.update(line.encode("utf-8"))
            h.update(b"\n")
        del bar_index
    for day, d in days.items():
        d["p3_digest"] = hashes[day]["P3"].hexdigest()
        d["p5_digest"] = hashes[day]["P5"].hexdigest()
        d["p8_digest"] = hashes[day]["P8"].hexdigest()
        d["signals_accepted"] = 0
        d["signals_skipped"] = 0
        d["realized_pnl"] = Decimal("0")
        d["trade_hash"] = hashlib.sha256()
    day_of_bar = {int(r[0]): str(r[1]) for r in store.query("SELECT bar_index,trading_day FROM bar_summary")}
    for bar_index, status in store.query("SELECT bar_index,status FROM signals ORDER BY bar_index, signal_id"):
        d = days[day_of_bar[int(bar_index)]]
        d["signals_accepted" if status == "ACCEPTED" else "signals_skipped"] += 1
    for row in store.query("SELECT * FROM positions ORDER BY entry_bar_index, position_id"):
        exit_bar = row[11]
        if exit_bar is not None:
            d = days[day_of_bar[int(exit_bar)]]
            d["realized_pnl"] += Decimal(str(row[13]))
        line = "|".join("" if v is None else str(v) for v in row)
        days[day_of_bar[int(row[6])]]["trade_hash"].update(line.encode("utf-8") + b"\n")
    out: list[dict[str, Any]] = []
    for day in sorted(days):
        d = days[day]
        d["trade_digest"] = d.pop("trade_hash").hexdigest()
        d["realized_pnl"] = str(d["realized_pnl"])
        out.append({column: d[column] for column in DAILY_COLUMNS})
    return out


def export_journals(store: StateStore, out_dir: Path) -> dict[str, Any]:
    out_dir.mkdir(parents=True, exist_ok=True)
    digests: dict[str, str] = {}

    def write(name: str, text: str, deterministic: bool = True) -> None:
        data = text.encode("utf-8")
        (out_dir / name).write_bytes(data)
        if deterministic:
            digests[name] = hashlib.sha256(data).hexdigest()

    for name, (columns, sql) in _DETERMINISTIC_QUERIES.items():
        write(name, _csv(columns, store.query(sql)))

    daily = daily_authority_rows(store)
    write("daily_authority_journal.csv", _csv(DAILY_COLUMNS, [[d[c] for c in DAILY_COLUMNS] for d in daily]))

    write(
        "perf_bar_timing.csv",
        _csv(("bar_index", "run_no", "scanner_seconds", "persist_seconds"),
             store.query("SELECT * FROM bar_timing ORDER BY bar_index")),
        deterministic=False,
    )
    write(
        "runs.csv",
        _csv(
            ("run_no", "command", "pid", "started_wall_utc", "ended_wall_utc", "rebuilt_bars",
             "rebuild_verified", "rebuild_seconds", "processed_bars", "process_seconds", "outcome"),
            store.query("SELECT * FROM runs ORDER BY run_no"),
        ),
        deterministic=False,
    )

    config_json = store.get_meta("config_json") or "{}"
    config = json.loads(config_json)
    manifest: dict[str, Any] = {
        "execution_mode": EXECUTION_MODE,
        "disclaimer": (
            "DRY-RUN / PAPER SIMULATION ONLY. No live broker exists. "
            + PRACTICE_POLICY_LABEL
            + ". No profitability or production-readiness claim."
        ),
        "config": config,
        "scanner_profile": config.get("scanner_profile"),
        "bars_processed": store.processed_bar_count(),
        "last_processed_bar_index": store.get_meta("last_processed_bar_index"),
        "chain_digest": store.get_meta("chain_digest"),
        "period_digests_authority_fold": {
            stream: fold_period_digest(stream, [(d["trading_day"], d[f"{stream.lower()}_digest"]) for d in daily])
            for stream in ("P3", "P5", "P8")
        },
        "journal_sha256": dict(sorted(digests.items())),
    }
    combined = hashlib.sha256(
        "\n".join(f"{k}={v}" for k, v in sorted(digests.items())).encode("utf-8")
    ).hexdigest()
    manifest["journals_combined_sha256"] = combined
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    return manifest
