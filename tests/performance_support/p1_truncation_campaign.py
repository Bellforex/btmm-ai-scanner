"""P1-PERF-4 — developer campaign for the bounded-execution horizon.

Reproduces the evidence recorded in
``docs/architecture/BTRC_V1_P1_PERFORMANCE_OPTIMIZATION.md`` §18. It is a
developer/stress tool, not part of the unit suite: a full sweep replays several
thousand bars per horizon per dataset and takes tens of minutes. The unit suite
keeps the cheap structural proof plus one end-to-end case.

    # horizon sweep over the canonical FXCM datasets
    uv run python -m tests.performance_support.p1_truncation_campaign real \\
        --horizons 300,600,900,1200,1350,1500,1800 --json real.json

    # the twenty adversarial boundary fixtures
    uv run python -m tests.performance_support.p1_truncation_campaign adversarial \\
        --horizons 900,1200,1800 --json adv.json

    # randomized structured streams at the selected horizon
    uv run python -m tests.performance_support.p1_truncation_campaign random \\
        --horizons 1800 --streams 200 --json rand.json

Every mode compares FULL-history execution against TRUNCATED execution over the
final ``--protected`` bars, on all nine published parity outputs.
"""

from __future__ import annotations

import argparse
import json
from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from multiprocessing import Pool
from pathlib import Path
from typing import Any

from btmm_ai_scanner.config.enums import InternalSymbol, Timeframe
from btmm_ai_scanner.contracts.normalized_candle import NormalizedCandle
from btmm_ai_scanner.domain.configuration import MarketMeasurementConfiguration

from . import p1_sr_diagnostics as diagnostics
from . import p1_truncation as truncation
from . import p1_truncation_fixtures as fixtures

_DATA_ROOT = Path(
    r"C:\Users\user\Desktop\BTMM_REAL_DATA\DATASETS\xauusd_2026_07_pilot\candles"
)
_REAL = {
    "M1": (Timeframe.M1, _DATA_ROOT / "xauusd_m1.csv"),
    "M5": (Timeframe.M5, _DATA_ROOT / "xauusd_m5.csv"),
    "M15": (Timeframe.M15, _DATA_ROOT / "xauusd_m15.csv"),
}
_EPOCH = datetime(2026, 1, 1, tzinfo=UTC)


def _configuration() -> MarketMeasurementConfiguration:
    return MarketMeasurementConfiguration(minimum_price_tick=Decimal("0.01"))


def _synthetic_candles(bars: Sequence[Any]) -> tuple[NormalizedCandle, ...]:
    rows = [
        diagnostics.Row(
            _EPOCH + timedelta(minutes=15 * index),
            bar.open,
            bar.high,
            bar.low,
            bar.close,
        )
        for index, bar in enumerate(bars)
    ]
    return diagnostics.build_candles(
        rows, InternalSymbol.XAUUSD, Timeframe.M15, "SYNTH"
    )


def compare(
    candles: Sequence[NormalizedCandle], horizon: int, protected: int
) -> dict[str, Any]:
    """Full-history vs truncated execution over the final ``protected`` bars."""
    configuration = _configuration()
    total = len(candles)
    first_protected = total - protected
    baseline = truncation.replay(
        candles,
        start=0,
        configuration=configuration,
        swings_fn=diagnostics._confirmed_swings,
        first_protected=first_protected,
    )
    bounded = truncation.replay(
        candles,
        start=total - horizon,
        configuration=configuration,
        swings_fn=diagnostics._confirmed_swings,
        first_protected=first_protected,
    )
    fields: dict[str, int] = {}
    bad = 0
    for index in sorted(baseline):
        differences = baseline[index].differences(bounded[index])
        if differences:
            bad += 1
            for name in differences:
                fields[name] = fields.get(name, 0) + 1
    return {
        "compared": len(baseline),
        "mismatched_bars": bad,
        "fields": fields,
        "atr_warmup": truncation.atr_convergence_bars(
            candles, total - horizon, configuration.atr_period
        ),
    }


def _job(task: tuple[str, str, int, int, int]) -> dict[str, Any]:
    mode, name, horizon, protected, seed = task
    if mode == "real":
        timeframe, path = _REAL[name]
        rows = diagnostics.load_rows(path)
        candles = diagnostics.build_candles(
            rows, InternalSymbol.XAUUSD, timeframe, "FXCM"
        )
    elif mode == "adversarial":
        total = horizon + 800
        candles = _synthetic_candles(fixtures.SCENARIOS[name](total - horizon, total))
    else:
        total = horizon + 700
        candles = _synthetic_candles(fixtures.structured_stream(seed, total))
    result = compare(candles, horizon, protected)
    result.update({"mode": mode, "name": name, "horizon": horizon})
    return result


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("real", "adversarial", "random"))
    parser.add_argument("--horizons", default="1800")
    parser.add_argument("--protected", type=int, default=300)
    parser.add_argument("--streams", type=int, default=200)
    parser.add_argument("--workers", type=int, default=3)
    parser.add_argument("--json", type=Path)
    args = parser.parse_args(argv)

    horizons = [int(value) for value in args.horizons.split(",")]
    tasks: list[tuple[str, str, int, int, int]] = []
    for horizon in horizons:
        if args.mode == "real":
            tasks += [
                ("real", name, horizon, args.protected, 0) for name in sorted(_REAL)
            ]
        elif args.mode == "adversarial":
            tasks += [
                ("adversarial", name, horizon, args.protected, 0)
                for name in sorted(fixtures.SCENARIOS)
            ]
        else:
            tasks += [
                ("random", f"seed{1000 + index}", horizon, args.protected, 1000 + index)
                for index in range(args.streams)
            ]

    results: list[dict[str, Any]] = []
    with Pool(args.workers) as pool:
        for result in pool.imap_unordered(_job, tasks):
            results.append(result)
            status = "OK" if result["mismatched_bars"] == 0 else "MISMATCH"
            print(
                f"[{result['mode']}] {result['name']:<32} N={result['horizon']:<5} "
                f"{status:<8} bad={result['mismatched_bars']:<4} "
                f"compared={result['compared']} {result['fields'] or ''}",
                flush=True,
            )

    compared = sum(result["compared"] for result in results)
    mismatched = sum(result["mismatched_bars"] for result in results)
    print(
        f"\n{args.mode.upper()}: runs={len(results)} "
        f"protected_bar_comparisons={compared} MISMATCHES={mismatched}"
    )
    if args.json:
        args.json.write_text(json.dumps(results, indent=1), encoding="utf-8")
        print("wrote", args.json)
    return 0 if mismatched == 0 else 1


if __name__ == "__main__":  # pragma: no cover - developer entry point
    raise SystemExit(main())
