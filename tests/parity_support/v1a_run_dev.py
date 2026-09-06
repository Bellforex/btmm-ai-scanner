"""CLI runner for the V1-A DEV-set replay (test/validation tooling only).

Runs ``v1a_harness.run_dev_replay`` over the full (or, via ``--max-bars``, a
truncated) DEV set, checkpointing progress to disk every ``--progress-every``
bars so a long run's partial results survive an interruption, and writing
the final events/POI-registry/ATR-series/displacement-index to
``artifacts/v1a_validation/v1a_dev_replay_result.json`` on completion.

Usage (from the repo root, with the project venv):
    .venv/Scripts/python.exe tests/parity_support/v1a_run_dev.py \\
        --lookback 250 --progress-every 50
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "src"))

from tests.parity_support.v1a_harness import (  # noqa: E402
    DevReplayResult,
    run_dev_replay,
)


def _event_to_json(event: object) -> dict:
    return dataclasses.asdict(event)  # type: ignore[call-overload]


def _poi_entry_to_json(entry: object) -> dict:
    d = dataclasses.asdict(entry)  # type: ignore[call-overload]
    d["record_id"] = str(d["record_id"])
    d["zone_top"] = str(d["zone_top"])
    d["zone_bottom"] = str(d["zone_bottom"])
    d["availability_time_utc"] = d["availability_time_utc"].isoformat()
    return d


def _write_checkpoint(path: Path, bars_done: int, total: int, events: list, poi_registry: dict) -> None:
    payload = {
        "bars_done": bars_done,
        "total_bars": total,
        "event_count": len(events),
        "poi_count": len(poi_registry),
        "events": [_event_to_json(e) for e in events],
        "poi_registry": [_poi_entry_to_json(v) for v in poi_registry.values()],
    }
    tmp_path = path.with_suffix(".tmp")
    tmp_path.write_text(json.dumps(payload), encoding="utf-8")
    tmp_path.replace(path)


def _write_final(path: Path, result: DevReplayResult) -> None:
    payload = {
        "dev_bar_count": len(result.dev_m15),
        "events": [_event_to_json(e) for e in result.events],
        "poi_registry": [_poi_entry_to_json(v) for v in result.poi_registry.values()],
        "atr_series": [str(v) if v is not None else None for v in result.atr_series],
        "displacement_by_bar_index": {
            str(k): list(v) for k, v in result.displacement_by_bar_index.items()
        },
        "dev_m15_ohlc": [
            {
                "event_time_utc": c.event_time_utc.isoformat(),
                "availability_time_utc": c.availability_time_utc.isoformat(),
                "open": str(c.open),
                "high": str(c.high),
                "low": str(c.low),
                "close": str(c.close),
            }
            for c in result.dev_m15
        ],
    }
    path.write_text(json.dumps(payload), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset-root", default=str(REPO_ROOT / "artifacts" / "v1a_validation"))
    parser.add_argument("--lookback", type=int, default=250)
    parser.add_argument("--max-bars", type=int, default=None)
    parser.add_argument("--progress-every", type=int, default=50)
    parser.add_argument(
        "--out-dir", default=str(REPO_ROOT / "artifacts" / "v1a_validation")
    )
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    checkpoint_path = out_dir / "v1a_dev_replay_checkpoint.json"
    final_path = out_dir / "v1a_dev_replay_result.json"
    log_path = out_dir / "v1a_dev_replay_progress.log"

    t_start = time.time()

    def progress_callback(bars_done: int, total: int, events: list, poi_registry: dict) -> None:
        elapsed = time.time() - t_start
        line = (
            f"{bars_done}/{total} events={len(events)} pois={len(poi_registry)} "
            f"elapsed={elapsed:.1f}s"
        )
        print(line, flush=True)
        with log_path.open("a", encoding="utf-8") as handle:
            handle.write(line + "\n")
        _write_checkpoint(checkpoint_path, bars_done, total, events, poi_registry)

    result = run_dev_replay(
        dataset_root=Path(args.dataset_root),
        pre_dev_lookback_bars=args.lookback,
        max_bars=args.max_bars,
        progress_every=args.progress_every,
        progress_callback=progress_callback,
    )

    _write_final(final_path, result)
    total_elapsed = time.time() - t_start
    print(f"DONE total_elapsed={total_elapsed:.1f}s events={len(result.events)} pois={len(result.poi_registry)}")
    with log_path.open("a", encoding="utf-8") as handle:
        handle.write(
            f"DONE total_elapsed={total_elapsed:.1f}s events={len(result.events)} "
            f"pois={len(result.poi_registry)}\n"
        )


if __name__ == "__main__":
    main()
