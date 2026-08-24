"""P1 S/R overnight stress campaign — developer tooling, not production.

Runs the validated frontier model against the production Python oracle over many
deterministic seeded streams, comparing **every prefix**, and reports the totals
plus peak state. Publication timing is part of S/R semantics, so a final-state
comparison would prove very little; this compares the whole trajectory.

Usage::

    uv run python -m tests.performance_support.p1_sr_stress \\
        --seeds 100 --length 420 --swings 26 --lookback 300 --json out.json

Deterministic by construction: seeds are fixed integers, never random.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
import time
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

_MODEL_PATH = (
    Path(__file__).resolve().parents[1] / "unit" / "test_pine_p1_sr_frontier_model.py"
)


def _load_model() -> Any:
    spec = importlib.util.spec_from_file_location("_p1_sr_model_stress", _MODEL_PATH)
    if spec is None or spec.loader is None:  # pragma: no cover - defensive
        raise RuntimeError(f"cannot load frontier model from {_MODEL_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@dataclass
class Mismatch:
    seed: int
    prefix: int
    expected: str
    actual: str


@dataclass
class Campaign:
    seeds: int = 0
    prefixes: int = 0
    comparisons: int = 0
    mismatches: list[Mismatch] = field(default_factory=list)
    total_pair_visits: int = 0
    total_new_pairs: int = 0
    total_tracker_advances: int = 0
    total_tracker_resolutions: int = 0
    total_retirements: int = 0
    total_walks: int = 0
    total_published: int = 0
    peak_active_trackers: int = 0
    peak_a_total: int = 0
    duration_seconds: float = 0.0

    def as_dict(self) -> dict[str, Any]:
        return {
            "seeds": self.seeds,
            "prefixes": self.prefixes,
            "oracle_comparisons": self.comparisons,
            "oracle_mismatches": len(self.mismatches),
            "first_mismatches": [
                {
                    "seed": m.seed,
                    "prefix": m.prefix,
                    "expected": m.expected,
                    "actual": m.actual,
                }
                for m in self.mismatches[:5]
            ],
            "total_pair_visits": self.total_pair_visits,
            "total_new_pairs": self.total_new_pairs,
            "total_tracker_advances": self.total_tracker_advances,
            "total_tracker_resolutions": self.total_tracker_resolutions,
            "total_pair_retirements": self.total_retirements,
            "total_walks": self.total_walks,
            "total_published_zones": self.total_published,
            "peak_active_trackers": self.peak_active_trackers,
            "peak_swings_in_window": self.peak_a_total,
            "duration_seconds": round(self.duration_seconds, 2),
        }


def run(
    *,
    seeds: int,
    length: int,
    swings: int,
    lookback: int,
    start_seed: int = 1,
    mode: str = "both",
    blocks: int = 12,
) -> Campaign:
    model = _load_model()
    campaign = Campaign()
    started = time.perf_counter()

    plan: list[tuple[str, int]] = []
    for offset in range(seeds):
        seed = start_seed + offset
        if mode in ("random", "both"):
            plan.append(("random", seed))
        if mode in ("structured", "both"):
            plan.append(("structured", seed))

    for kind, seed in plan:
        if kind == "random":
            candles, swing_set = model._random_stream(
                seed, length=length, swing_count=swings
            )
        else:
            candles, swing_set = model._structured_stream(seed, blocks=blocks)
        frontier, rows = model.run_prefixes(candles, swing_set, lookback=lookback)
        campaign.seeds += 1
        for end, oracle, actual in rows:
            campaign.comparisons += 1
            campaign.prefixes += 1
            if actual != oracle:
                campaign.mismatches.append(
                    Mismatch(
                        seed=seed,
                        prefix=end,
                        expected=repr(oracle),
                        actual=repr(actual),
                    )
                )
        counters = frontier.counters
        campaign.total_pair_visits += counters.actual_pair_visits
        campaign.total_new_pairs += counters.new_semantic_pairs
        campaign.total_tracker_advances += counters.tracker_advances
        campaign.total_tracker_resolutions += counters.trackers_resolved
        campaign.total_retirements += counters.pair_retirements
        campaign.total_walks += counters.walks
        campaign.total_published += counters.published_zones
        campaign.peak_active_trackers = max(
            campaign.peak_active_trackers, counters.max_active_trackers
        )
        campaign.peak_a_total = max(campaign.peak_a_total, len(swing_set))

    campaign.duration_seconds = time.perf_counter() - started
    return campaign


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seeds", type=int, default=50)
    parser.add_argument("--length", type=int, default=420)
    parser.add_argument("--swings", type=int, default=26)
    parser.add_argument("--lookback", type=int, default=300)
    parser.add_argument("--start-seed", type=int, default=1)
    parser.add_argument(
        "--mode", choices=("random", "structured", "both"), default="both"
    )
    parser.add_argument("--blocks", type=int, default=12)
    parser.add_argument("--json", type=Path)
    args = parser.parse_args(argv)

    campaign = run(
        seeds=args.seeds,
        length=args.length,
        swings=args.swings,
        lookback=args.lookback,
        start_seed=args.start_seed,
        mode=args.mode,
        blocks=args.blocks,
    )
    payload = campaign.as_dict()
    if args.json:
        args.json.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    for key, value in payload.items():
        if key == "first_mismatches":
            continue
        print(f"{key:<28} {value}")
    if campaign.mismatches:
        print("\nFIRST MISMATCHES")
        for entry in payload["first_mismatches"]:
            print(f"  seed={entry['seed']} prefix={entry['prefix']}")
            print(f"    expected {entry['expected']}")
            print(f"    actual   {entry['actual']}")
        return 1
    return 0


if __name__ == "__main__":  # pragma: no cover - CLI
    sys.exit(main())
