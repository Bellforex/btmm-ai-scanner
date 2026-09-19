"""RC3 ALIGNED Level-A replay: run the frozen Level-A authority over EXACTLY
the bars one live Pine PARITY run executed on.

Test/validation tooling only — nothing in ``src/`` imports this.

WHY THIS EXISTS
---------------
``rc3_daily_authority`` replays a fixed, previously acquired window. A live
Pine run instead executes the last ``calc_bars_count`` host bars of the
session's feed, with each ``request.security`` context bounded to its own
1251-bar window. Comparing the two directly compares different runtime
contexts. This module removes every one of those differences mechanically:

* the Pine run logs ``RUNMETA`` (PARITY build, log-only instrumentation):
  host first/last confirmed bar, bar count and an OHLC checksum, and the same
  four values for every context window;
* the same TradingView session exports every timeframe's OHLC
  (``tradingview/btmm_ohlc_exporter.pine``);
* this module selects, per timeframe, exactly the bars RUNMETA names, proves
  the selection by count AND checksum, refuses a host window that touches the
  sealed out-of-sample range, and hands the result to the unchanged
  ``run_daily_authority`` — one interpretation of the scanner rules.

It never reads P3LIFE / P5C / P8EVENT: RUNMETA and the OHLC export are the
only Pine-session inputs, and both are raw market data plus window bounds.
The Level-A side therefore stays independent of the Pine semantics it is
later compared against.
"""

from __future__ import annotations

import csv
import json
import re
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from btmm_ai_scanner.config.enums import Timeframe
from btmm_ai_scanner.contracts.normalized_candle import NormalizedCandle
from tests.parity_support.rc3_daily_authority import (
    SEALED_FIRST_EVENT_UTC,
    SEALED_LAST_EVENT_UTC,
    SealedRangeViolationError,
    build_authority_configuration,
    run_daily_authority,
)
from tests.parity_support.v1a_csv_loader import load_v1a_csv

__all__ = [
    "AlignedWindow",
    "RunMeta",
    "WindowMeta",
    "load_aligned_window",
    "parse_runmeta",
]

#: RUNMETA key -> (Timeframe, export file stem).
_TIMEFRAMES: dict[str, tuple[Timeframe, str]] = {
    "W1": (Timeframe.W1, "w1"),
    "D1": (Timeframe.D1, "d1"),
    "H4": (Timeframe.H4, "h4"),
    "H1": (Timeframe.H1, "h1"),
    "M15": (Timeframe.M15, "m15"),
    "M5": (Timeframe.M5, "m5"),
}
_HOST_TF_BY_PERIOD: dict[str, str] = {"15": "M15", "60": "H1", "240": "H4", "5": "M5"}

#: The checksum is a running float64 sum of o+h+l+c; the export prints prices
#: to 5 decimals, so re-summing parsed prices can differ from Pine's own sum by
#: accumulated binary rounding only. Prices are 2-decimal, so any genuinely
#: different bar moves the sum by >= 0.01.
CHECKSUM_TOLERANCE = 1e-5

_OHLC = re.compile(
    r"OHLC\|tf=[^|]*\|t=(\d+)\|tc=(\d+)\|o=([\d.]+)\|h=([\d.]+)\|l=([\d.]+)"
    r"\|c=([\d.]+)\|v=([\d.]+)"
)


@dataclass(frozen=True)
class WindowMeta:
    first_ms: int
    last_ms: int
    count: int
    checksum: float


@dataclass(frozen=True)
class RunMeta:
    feed: str
    host_period: str
    host: WindowMeta
    contexts: dict[str, WindowMeta]


class AlignmentError(AssertionError):
    """The export does not reproduce the window the Pine run executed."""


def parse_runmeta(capture_path: Path) -> RunMeta:
    text = capture_path.read_text(encoding="utf-8", errors="replace")
    lines = re.findall(r"RUNMETA\|[^\"\n]*", text)
    if len(lines) != 1:
        raise AlignmentError(f"expected exactly one RUNMETA line, found {len(lines)}")
    fields = dict(part.split("=", 1) for part in lines[0].split("|")[1:])

    def _window(raw: str) -> WindowMeta:
        first, last, count, checksum = raw.split(",")
        return WindowMeta(int(first), int(last), int(count), float(checksum))

    return RunMeta(
        feed=fields["feed"],
        host_period=fields["tf"],
        host=_window(fields["host"]),
        contexts={key: _window(fields[key]) for key in _TIMEFRAMES},
    )


def _load_export(
    path: Path, timeframe: Timeframe, scratch: Path
) -> tuple[NormalizedCandle, ...]:
    rows: dict[int, tuple[str, ...]] = {}
    close_ms: dict[int, int] = {}
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        match = _OHLC.search(line)
        if match is None:
            continue
        open_ms = int(match[1])
        row = (str(open_ms), match[3], match[4], match[5], match[6], match[7])
        if open_ms in rows and rows[open_ms] != row:
            raise AlignmentError(f"{path.name}: conflicting duplicate bar {open_ms}")
        rows[open_ms] = row
        close_ms[open_ms] = int(match[2])
    scratch.parent.mkdir(parents=True, exist_ok=True)
    with scratch.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(("time", "open", "high", "low", "close", "volume"))
        for open_ms in sorted(rows):
            writer.writerow(rows[open_ms])
    # Availability is the broker's REAL bar close (TradingView `time_close`),
    # not open + a fixed duration: FXCM session-end bars are shorter, and a
    # fixed duration makes them visible to the engine late.
    return load_v1a_csv(scratch, timeframe, close_time_ms_by_open_ms=close_ms)


def _select(
    candles: Sequence[NormalizedCandle], meta: WindowMeta, label: str
) -> tuple[NormalizedCandle, ...]:
    def _ms(candle: NormalizedCandle) -> int:
        return int(candle.event_time_utc.timestamp() * 1000)

    selected = tuple(c for c in candles if meta.first_ms <= _ms(c) <= meta.last_ms)
    if (
        not selected
        or _ms(selected[0]) != meta.first_ms
        or _ms(selected[-1]) != meta.last_ms
    ):
        raise AlignmentError(
            f"{label}: export does not contain the run's first/last bar"
        )
    if len(selected) != meta.count:
        raise AlignmentError(
            f"{label}: {len(selected)} bars exported, run executed {meta.count}"
        )
    checksum = 0.0
    for c in selected:
        checksum += float(c.open) + float(c.high) + float(c.low) + float(c.close)
    if abs(checksum - meta.checksum) > CHECKSUM_TOLERANCE:
        raise AlignmentError(
            f"{label}: OHLC checksum {checksum!r} != run checksum {meta.checksum!r}"
        )
    return selected


@dataclass(frozen=True)
class AlignedWindow:
    runmeta: RunMeta
    host_timeframe: Timeframe
    host_series: tuple[NormalizedCandle, ...]
    context_series: dict[Timeframe, tuple[NormalizedCandle, ...]]
    provenance: dict[str, object]


def load_aligned_window(capture_path: Path, export_dir: Path) -> AlignedWindow:
    runmeta = parse_runmeta(capture_path)
    if runmeta.feed != "FX:XAUUSD":
        raise AlignmentError(
            f"feed must be FXCM XAUUSD (FX:XAUUSD), got {runmeta.feed}"
        )
    host_key = _HOST_TF_BY_PERIOD[runmeta.host_period]
    host_tf = _TIMEFRAMES[host_key][0]
    scratch = export_dir / "_normalized"

    loaded = {
        key: _load_export(export_dir / f"ohlc_{stem}.csv", tf, scratch / f"{stem}.csv")
        for key, (tf, stem) in _TIMEFRAMES.items()
    }
    host = _select(loaded[host_key], runmeta.host, "host")
    for candle in host:
        if SEALED_FIRST_EVENT_UTC <= candle.event_time_utc <= SEALED_LAST_EVENT_UTC:
            raise SealedRangeViolationError(
                f"host bar {candle.event_time_utc.isoformat()} is inside the sealed range"
            )

    contexts: dict[Timeframe, tuple[NormalizedCandle, ...]] = {}
    for key, (tf, _stem) in _TIMEFRAMES.items():
        selected = _select(loaded[key], runmeta.contexts[key], key)
        if tf is host_tf:
            # TradingView serves a same-timeframe request from the host series
            # itself (RUNMETA shows an identical first bar, count and checksum),
            # so it is the host, not a second context.
            if selected != host:
                raise AlignmentError(f"{key} context differs from the host series")
            continue
        contexts[tf] = selected

    provenance: dict[str, object] = {
        "capture": capture_path.name,
        "feed": runmeta.feed,
        "host_timeframe": host_tf.value,
        "host_first_event_utc": host[0].event_time_utc.isoformat(),
        "host_last_event_utc": host[-1].event_time_utc.isoformat(),
        "host_bars": len(host),
        "context_bars": {tf.value: len(v) for tf, v in contexts.items()},
        "context_first_event_utc": {
            tf.value: v[0].event_time_utc.isoformat() for tf, v in contexts.items()
        },
        "alignment": "RUNMETA first/last/count + OHLC checksum verified per window",
        "availability": "broker bar close (TradingView time_close) per bar",
    }
    return AlignedWindow(runmeta, host_tf, host, contexts, provenance)


def main(argv: Sequence[str] | None = None) -> int:
    import argparse

    repo_root = Path(__file__).resolve().parents[2]
    base = repo_root / "artifacts" / "rc3_aligned"
    parser = argparse.ArgumentParser(description="Aligned RC3 Level-A replay.")
    parser.add_argument("--capture", type=Path, default=base / "pine_m15_run1.csv")
    parser.add_argument("--export-dir", type=Path, default=base)
    parser.add_argument("--output-dir", type=Path, default=base / "authority")
    parser.add_argument("--max-bars", type=int, default=None)
    parser.add_argument("--rc4", action="store_true", help="RC4 market-framework profile")
    parser.add_argument("--progress-every", type=int, default=10)
    args = parser.parse_args(argv)

    window = load_aligned_window(args.capture, args.export_dir)
    host = window.host_series[: args.max_bars] if args.max_bars else window.host_series
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "alignment.json").write_text(
        json.dumps(window.provenance, indent=2), encoding="utf-8"
    )
    progress_path = args.output_dir / "replay_progress.log"
    progress_path.write_text(
        f"started {datetime.now(tz=UTC).isoformat()}\n", encoding="utf-8"
    )
    result = run_daily_authority(
        host_timeframe=window.host_timeframe,
        host_series=host,
        context_series=window.context_series,
        configuration=build_authority_configuration(
            host_timeframe=window.host_timeframe,
            context_timeframes=tuple(window.context_series),
        ),
        provenance=window.provenance,
        output_dir=args.output_dir,
        progress_every=args.progress_every,
        progress_path=progress_path,
        rc4_framework=args.rc4,
    )
    print(json.dumps(result.summary(), indent=2))
    return 0


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    raise SystemExit(main())
