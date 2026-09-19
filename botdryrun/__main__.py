"""Command line: ``python -m botdryrun <command> ...`` (run from the repo root).

Commands
  replay   start a new session over a window (or continue the same one)
  resume   continue a cleanly paused session
  restart  simulate a process restart: spawn a NEW process that rebuilds
           scanner state from the persisted inputs (verifying digests) and
           continues; accepts a session left RUNNING by a crash
  status   short JSON status
  health   JSON health report
  export   re-export the journals

Exit codes: 0 ok (completed or paused), 2 usage/config, 3 feed integrity
error, 4 rebuild digest mismatch / feed revision, 5 sealed-range refusal,
6 live trading refused, 7 halted on a data gap.

Scanner profile: ``--scanner-profile RC4`` (default; RC4 market framework)
or ``RC3``.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from botdryrun.config import BotConfig, ConfigError, parse_utc
from botdryrun.engine import (
    BotEngine,
    EngineStateError,
    FeedRevisionError,
    RebuildDigestMismatchError,
    RunOutcome,
)
from botdryrun.health import health_report, status_report
from botdryrun.market_data import FeedIntegrityError, SealedRangeRefusedError
from botdryrun.safety import LiveTradingForbiddenError


def _print(payload: Any) -> None:
    print(json.dumps(payload, indent=2, sort_keys=True, default=str))


def _window_from_args(args: argparse.Namespace) -> tuple[datetime | None, datetime | None]:
    if args.trading_day:
        day = datetime.fromisoformat(args.trading_day).date()
        start = parse_utc(f"{day - timedelta(days=1)}T22:00:00Z")
        end = parse_utc(f"{day + timedelta(days=args.days - 1)}T20:45:00Z")
        return start, end
    first = parse_utc(args.start) if args.start else None
    last = parse_utc(args.end) if args.end else None
    return first, last


def _build_config(args: argparse.Namespace) -> BotConfig:
    start, end = _window_from_args(args)
    overrides: dict[str, Any] = {
        "window_start_utc": start,
        "window_end_utc": end,
        "dataset_root": args.dataset_root,
        "data_source": args.data_source,
        "context_lookback_bars": args.context_lookback_bars,
        "gap_policy": args.gap_policy,
        "entry_mode": args.entry_mode,
        "scanner_profile": args.scanner_profile,
    }
    if args.context_timeframes is not None:
        overrides["context_timeframes"] = [t for t in args.context_timeframes.split(",") if t]
    if args.config:
        return BotConfig.load(Path(args.config), overrides)
    raw = {k: v for k, v in overrides.items() if v is not None}
    raw.setdefault("dataset_root", str(Path.cwd() / "artifacts" / "v1a_validation"))
    if "window_start_utc" not in raw or "window_end_utc" not in raw:
        raise ConfigError("give --start/--end, --trading-day [--days], or --config")
    return BotConfig.from_mapping(raw)


def _run(engine: BotEngine, max_bars: int | None, *, allow_unclean: bool) -> int:
    try:
        report = engine.run(max_bars, allow_unclean=allow_unclean)
    finally:
        engine.close()
    _print(report.as_dict())
    return 7 if report.outcome is RunOutcome.HALTED_GAP else 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m botdryrun", description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)

    replay = sub.add_parser("replay", help="start (or continue) a session over a window")
    replay.add_argument("--state-dir", required=True)
    replay.add_argument("--config")
    replay.add_argument("--start", help="first host bar OPEN, ISO UTC")
    replay.add_argument("--end", help="last host bar OPEN, ISO UTC (inclusive)")
    replay.add_argument("--trading-day", help="FXCM trading day YYYY-MM-DD (22:00Z previous day ..)")
    replay.add_argument("--days", type=int, default=1)
    replay.add_argument("--dataset-root")
    replay.add_argument("--data-source", choices=["FXCM_V1A", "CSV_DIR"])
    replay.add_argument("--context-timeframes", help="comma list, e.g. W1,D1,H4,H1,M5")
    replay.add_argument("--context-lookback-bars", type=int)
    replay.add_argument("--gap-policy", choices=["CONTINUE", "HALT"])
    replay.add_argument("--entry-mode", choices=["LIMIT_AT_ZONE", "NEXT_OPEN"])
    replay.add_argument("--scanner-profile", choices=["RC4", "RC3"],
                        help="scanner contract to consume (default RC4)")
    replay.add_argument("--max-bars", type=int, help="pause cleanly after N bars")

    for name in ("resume", "restart", "_recover"):
        p = sub.add_parser(name, help=argparse.SUPPRESS if name.startswith("_") else None)
        p.add_argument("--state-dir", required=True)
        p.add_argument("--max-bars", type=int)
    for name in ("status", "health"):
        p = sub.add_parser(name)
        p.add_argument("--state-dir", required=True)
    export = sub.add_parser("export")
    export.add_argument("--state-dir", required=True)
    export.add_argument("--out")

    args = parser.parse_args(argv)
    state_dir = Path(args.state_dir)
    try:
        if args.command == "replay":
            config = _build_config(args)
            return _run(BotEngine(state_dir, config, command="replay"), args.max_bars, allow_unclean=False)
        if args.command == "resume":
            return _run(BotEngine(state_dir, command="resume"), args.max_bars, allow_unclean=False)
        if args.command == "_recover":
            return _run(BotEngine(state_dir, command="restart"), args.max_bars, allow_unclean=True)
        if args.command == "restart":
            child = [sys.executable, "-m", "botdryrun", "_recover", "--state-dir", str(state_dir)]
            if args.max_bars is not None:
                child += ["--max-bars", str(args.max_bars)]
            return subprocess.call(child)
        if args.command == "status":
            _print(status_report(state_dir))
            return 0
        if args.command == "health":
            report = health_report(state_dir)
            _print(report)
            return 0 if report["healthy"] else 1
        if args.command == "export":
            from botdryrun.journals import export_journals
            from botdryrun.store import StateStore

            store = StateStore(state_dir)
            try:
                _print(export_journals(store, Path(args.out) if args.out else state_dir / "journals"))
            finally:
                store.close()
            return 0
    except LiveTradingForbiddenError as exc:
        print(f"REFUSED (live trading): {exc}", file=sys.stderr)
        return 6
    except SealedRangeRefusedError as exc:
        print(f"REFUSED (sealed range): {exc}", file=sys.stderr)
        return 5
    except (RebuildDigestMismatchError, FeedRevisionError) as exc:
        print(f"RECOVERY FAILED: {exc}", file=sys.stderr)
        return 4
    except FeedIntegrityError as exc:
        print(f"FEED INTEGRITY ERROR: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 3
    except (ConfigError, EngineStateError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    except AssertionError as exc:
        # rc3_daily_authority.SealedRangeViolationError is an AssertionError.
        if "sealed" in str(exc):
            print(f"REFUSED (sealed range): {exc}", file=sys.stderr)
            return 5
        raise
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
