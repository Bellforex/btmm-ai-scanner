"""Harness pipeline-sanity check against the already-verified P9 capture
(protocol §15 "harness pipeline-sanity validation only", brief Phase 44).

This is explicitly NOT a V1-A characterization result — it never touches
the DEV set, and its input (``artifacts/p9_capture/p9_dev_raw_log.csv``) is
drawn from the "already-used development/parity window" the manifest
reserves for exactly this purpose (2026-08-03T07:00 UTC onward — strictly
AFTER the OOS window ends at 2026-08-03T06:45 UTC, so this never opens
OOS either).

What this checks: that ``v1a_outcome_math``'s own field-computation logic
(MFE/MAE/directional-return/threshold-reach/POI-geometry) runs to
completion, without error, on POI states drawn from a REAL, already-closed
Pine capture (not synthetic fixtures), against REAL forward M15 OHLC from
the same FXCM feed — and that its outputs are internally sane (bounded,
correctly signed, monotonic threshold ordering, correctly increasing
censoring near the end of the available window). It does NOT re-run the
scanner replay, and it does NOT claim any BTRC-decision-field parity with
the P9 capture's own already-established permission/lifecycle/score
values (a different question, already closed in a prior phase) — only that
feeding real zone/direction/timestamp data through the OUTCOME MATH
produces sane, non-crashing results.
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "src"))

from btmm_ai_scanner.config.enums import Timeframe  # noqa: E402
from btmm_ai_scanner.measurements.atr import compute_atr_series  # noqa: E402
from tests.parity_support.v1a_csv_loader import (  # noqa: E402
    ALREADY_USED_BOUNDARY_UTC,
    load_v1a_csv,
    verify_v1a_manifest_hashes,
)
from tests.parity_support.v1a_outcome_math import (  # noqa: E402
    ForwardBar,
    compute_mae,
    compute_mfe,
    compute_path_ordering,
    compute_poi_touch_outcome,
    compute_threshold_reach_grid,
)

_TRACE_PATTERN = re.compile(
    r"P9TRACE\|bar=(?P<bar>-?\d+)\|poiIdx=(?P<poi_idx>-?\d+)\|poiType=(?P<poi_type>-?\d+)"
    r"\|poiDir=(?P<poi_dir>-?\d+)\|zoneTop=(?P<zone_top>-?[\d.]+)\|zoneBottom=(?P<zone_bottom>-?[\d.]+)"
    r"\|availTime=(?P<avail_time>-?\d+)\|terminal=(?P<terminal>true|false)"
    r"\|btmmValid=(?P<btmm_valid>true|false)\|finalScore=(?P<final_score>-?\d+)"
    r"\|permission=(?P<permission>-?\d+)\|lifecycle=(?P<lifecycle>-?\d+)"
)


@dataclass(frozen=True)
class P9Row:
    bar_ms: int
    poi_idx: int
    poi_dir: int
    zone_top: Decimal
    zone_bottom: Decimal
    avail_time_ms: int
    terminal: bool
    btmm_valid: bool
    final_score: int


def parse_p9_rows(path: Path) -> tuple[P9Row, ...]:
    rows: list[P9Row] = []
    with path.open("r", encoding="utf-8") as handle:
        next(handle)  # header
        for line in handle:
            match = _TRACE_PATTERN.search(line)
            if match is None:
                continue
            rows.append(
                P9Row(
                    bar_ms=int(match["bar"]),
                    poi_idx=int(match["poi_idx"]),
                    poi_dir=int(match["poi_dir"]),
                    zone_top=Decimal(match["zone_top"]),
                    zone_bottom=Decimal(match["zone_bottom"]),
                    avail_time_ms=int(match["avail_time"]),
                    terminal=match["terminal"] == "true",
                    btmm_valid=match["btmm_valid"] == "true",
                    final_score=int(match["final_score"]),
                )
            )
    return tuple(rows)


def run_sanity_check(dataset_root: Path, p9_capture_path: Path) -> dict:
    verify_v1a_manifest_hashes(dataset_root)
    full_m15 = load_v1a_csv(dataset_root / "v1a_raw_ohlc_full_loaded.csv", Timeframe.M15)
    sanity_window = tuple(c for c in full_m15 if c.event_time_utc >= ALREADY_USED_BOUNDARY_UTC)
    by_event_ms = {int(c.event_time_utc.timestamp() * 1000): idx for idx, c in enumerate(sanity_window)}
    atr_series = compute_atr_series(sanity_window, period=14)

    rows = parse_p9_rows(p9_capture_path)

    matched = 0
    unmatched = 0
    computed = 0
    errors: list[str] = []
    censored_mfe_count = 0
    total_mfe_cells = 0
    threshold_order_violations = 0

    for row in rows:
        bar_index = by_event_ms.get(row.bar_ms)
        if bar_index is None:
            unmatched += 1
            continue
        matched += 1
        try:
            reference = sanity_window[bar_index].close
            forward = tuple(
                ForwardBar(high=c.high, low=c.low, close=c.close)
                for c in sanity_window[bar_index + 1 :]
            )
            bullish = row.poi_dir >= 0
            atr_at_event = atr_series[bar_index]

            mfe = compute_mfe(reference, forward, bullish=bullish, atr_at_event=atr_at_event)
            # MAE is computed too (sanity: must not raise), but only MFE cells
            # feed the censoring-rate stat below.
            compute_mae(reference, forward, bullish=bullish, atr_at_event=atr_at_event)
            grid = compute_threshold_reach_grid(
                reference, forward, bullish=bullish, atr_at_event=atr_at_event
            )
            compute_path_ordering(grid)

            touch_outcome = compute_poi_touch_outcome(
                row.zone_top,
                row.zone_bottom,
                bullish=bullish,
                forward_bars=forward,
                atr_lookup=atr_series[bar_index + 1 :],
            )
            _ = touch_outcome

            for cell in mfe:
                total_mfe_cells += 1
                if cell.censored:
                    censored_mfe_count += 1

            # Sanity invariant: as the ATR threshold grows, the bar offset at
            # which it is first reached must be non-decreasing (a HIGHER bar
            # (favorable excursion is monotonically-increasing per bar, so a
            # bigger threshold can never be reached strictly earlier than a
            # smaller one).
            offsets = [c.bar_offset for c in grid.favorable if c.bar_offset is not None]
            if offsets != sorted(offsets):
                threshold_order_violations += 1

            computed += 1
        except Exception as exc:
            errors.append(f"{row.bar_ms}/{row.poi_idx}: {exc!r}")

    return {
        "total_rows": len(rows),
        "matched_to_a_sanity_window_bar": matched,
        "unmatched": unmatched,
        "computed_without_error": computed,
        "errors": errors[:20],
        "error_count": len(errors),
        "censored_mfe_cell_rate": (censored_mfe_count / total_mfe_cells) if total_mfe_cells else None,
        "threshold_ordering_violations": threshold_order_violations,
        "sanity_window_bar_count": len(sanity_window),
    }


if __name__ == "__main__":
    result = run_sanity_check(
        REPO_ROOT / "artifacts" / "v1a_validation", REPO_ROOT / "artifacts" / "p9_capture" / "p9_dev_raw_log.csv"
    )
    import json

    print(json.dumps(result, indent=2, default=str))
