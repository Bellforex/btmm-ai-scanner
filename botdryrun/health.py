"""Health monitor: a read-only view of a state directory."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from botdryrun.safety import EXECUTION_MODE
from botdryrun.store import StateStore

__all__ = ["health_report", "status_report"]


def _scanner_pin(store: StateStore) -> dict[str, Any]:
    raw = store.get_meta("scanner_pin")
    last = store.query(
        "SELECT run_no,status,observed_digest FROM scanner_pin_checks ORDER BY run_no DESC LIMIT 1"
    )
    return {
        "session_pin": json.loads(raw) if raw else None,
        "last_check": None
        if not last
        else {"run_no": last[0][0], "status": last[0][1], "observed_digest": last[0][2]},
        "override_ever_used": store.get_meta("scanner_pin_overridden") == "1",
    }


def status_report(state_dir: Path) -> dict[str, Any]:
    store = StateStore(state_dir)
    try:
        config = json.loads(store.get_meta("config_json") or "{}")
        last = store.query(
            "SELECT bar_index,event_utc,trading_day,balance,equity,open_positions,pending_orders "
            "FROM bar_summary ORDER BY bar_index DESC LIMIT 1"
        )
        return {
            "execution_mode": EXECUTION_MODE,
            "status": store.get_meta("status") or "NEW",
            "window_start_utc": config.get("window_start_utc"),
            "window_end_utc": config.get("window_end_utc"),
            "scanner_profile": config.get("scanner_profile"),
            "scanner_pin": _scanner_pin(store),
            "bars_processed": store.processed_bar_count(),
            "last_bar_index": last[0][0] if last else None,
            "last_bar_open_utc": last[0][1] if last else None,
            "last_trading_day": last[0][2] if last else None,
            "chain_digest": store.get_meta("chain_digest"),
        }
    finally:
        store.close()


def health_report(state_dir: Path) -> dict[str, Any]:
    store = StateStore(state_dir)
    try:
        status = store.get_meta("status") or "NEW"
        incidents = {
            str(sev): int(n)
            for sev, n in store.query("SELECT severity, COUNT(*) FROM incidents GROUP BY severity")
        }
        last = store.query(
            "SELECT bar_index,event_utc,balance,equity,open_positions,pending_orders "
            "FROM bar_summary ORDER BY bar_index DESC LIMIT 1"
        )
        rebuild_raw = store.get_meta("last_rebuild")
        rebuild = json.loads(rebuild_raw) if rebuild_raw else None
        runs = store.query(
            "SELECT run_no,command,rebuilt_bars,rebuild_seconds,processed_bars,process_seconds,outcome "
            "FROM runs ORDER BY run_no DESC LIMIT 1"
        )
        closed = store.query(
            "SELECT COUNT(*), COALESCE(SUM(CASE WHEN CAST(realized_pnl AS REAL) > 0 THEN 1 ELSE 0 END),0) "
            "FROM positions WHERE status='CLOSED'"
        )[0]
        problems: list[str] = []
        if incidents.get("CRITICAL"):
            problems.append("critical data incidents recorded")
        if status in ("REBUILD_MISMATCH", "HALTED_FEED_ERROR", "HALTED_GAP"):
            problems.append(f"status {status}")
        if status == "RUNNING":
            problems.append("status RUNNING: a process is active or stopped uncleanly (use restart)")
        if rebuild is not None and not rebuild.get("verified", False):
            problems.append("last rebuild digest verification FAILED")
        pin = _scanner_pin(store)
        if pin["override_ever_used"]:
            problems.append("a scanner pin mismatch was overridden (--allow-scanner-mismatch)")
        if pin["last_check"] is not None and pin["last_check"]["status"] == "MISMATCH_REFUSED":
            problems.append("last run was refused: scanner source does not match the pin")
        last_run = runs[0] if runs else None
        return {
            "execution_mode": EXECUTION_MODE,
            "live_broker": "DISABLED (no live execution path exists)",
            "healthy": not problems,
            "problems": problems,
            "status": status,
            "last_bar_index": last[0][0] if last else None,
            "last_bar_open_utc": last[0][1] if last else None,
            "bars_processed": store.processed_bar_count(),
            "incidents_by_severity": incidents,
            "digest_verification": rebuild,
            "scanner_pin": pin,
            "chain_digest": store.get_meta("chain_digest"),
            "open_positions": last[0][4] if last else 0,
            "pending_orders": last[0][5] if last else 0,
            "balance": last[0][2] if last else None,
            "equity": last[0][3] if last else None,
            "closed_paper_trades": int(closed[0]),
            "last_run": None
            if last_run is None
            else {
                "run_no": last_run[0],
                "command": last_run[1],
                "rebuilt_bars": last_run[2],
                "rebuild_seconds": last_run[3],
                "processed_bars": last_run[4],
                "process_seconds": last_run[5],
                "seconds_per_bar": (last_run[5] / last_run[4]) if last_run[4] else None,
                "outcome": last_run[6],
            },
        }
    finally:
        store.close()
