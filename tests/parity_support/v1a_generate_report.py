"""Builds the full V1-A DEV-set characterization report (protocol §18) from
a completed ``v1a_run_dev.py`` result file.

Writes:
  - ``artifacts/v1a_validation/v1a_characterization_report.json`` (full,
    machine-readable, every segmentation table)
  - ``artifacts/v1a_validation/V1A_CHARACTERIZATION_REPORT.md`` (the same
    content, rendered as markdown for human review)

Both are gitignored (``artifacts/``) — the short prose summary that gets
committed lives at
``docs/validation/BTRC_V1_V1A_CHARACTERIZATION_SUMMARY.md``.
"""

from __future__ import annotations

import json
import sys
from decimal import Decimal
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "src"))

from tests.parity_support.v1a_report import (  # noqa: E402
    build_report,
    compute_event_outcomes,
    compute_poi_outcomes,
)


def _availability_ms_index(dev_m15_ohlc: list[dict]) -> dict[int, int]:
    return {
        int(
            __import__("datetime")
            .datetime.fromisoformat(row["availability_time_utc"])
            .timestamp()
            * 1000
        ): idx
        for idx, row in enumerate(dev_m15_ohlc)
    }


def _fmt_pct(value: float | None) -> str:
    if value is None:
        return "n/a"
    return f"{value * 100:.1f}%"


def _fmt_dist(dist: dict) -> str:
    if dist["n"] == 0:
        return "n=0"
    return (
        f"n={dist['n']} mean={dist['mean']:.4f} median={dist['median']:.4f} "
        f"p25={dist['p25']:.4f} p75={dist['p75']:.4f} p90={dist['p90']:.4f}"
    )


def render_markdown(report: dict) -> str:
    lines: list[str] = []
    lines.append("# V1-A DEV-Set Signal-Outcome Characterization Report")
    lines.append("")
    lines.append(
        "**OOS remains locked, not opened.** This report covers the DEV set "
        "(2903 M15 bars, 2026-05-31T22:00 to 2026-07-14T17:00 UTC) only, per "
        "`docs/validation/BTRC_V1_VALIDATION_PROTOCOL.md`. All figures are "
        "descriptive characterizations of historical price behavior "
        "following RC1's own informational events — none is a trade-"
        "profitability metric (protocol §12)."
    )
    lines.append("")

    lines.append("## Counts")
    counts = report["counts"]
    lines.append(f"- Total events: {counts['total_events']}")
    for event_type, n in sorted(counts["events_by_type"].items()):
        lines.append(f"  - {event_type}: {n}")
    lines.append(f"- Total POIs registered: {counts['total_pois']}")
    lines.append("")

    lines.append("## Exclusions (protocol §13)")
    for scope in ("events", "pois"):
        lines.append(f"### {scope}")
        for k, v in report["exclusions"][scope].items():
            lines.append(f"- {k}: {v}")
    lines.append("")

    lines.append("## MFE / MAE by event_type (horizon = 8 bars)")
    seg = report["mfe_mae_by_segment_horizon_8"]["event_type"]
    for key in sorted(seg["mfe"]):
        lines.append(f"- **{key}**")
        lines.append(f"  - MFE: {_fmt_dist(seg['mfe'][key])}")
        lines.append(f"  - MAE: {_fmt_dist(seg['mae'][key])}")
    lines.append("")

    lines.append("## ATR-normalized threshold-reach rates")
    tr = report["threshold_reach_rates"]
    lines.append("| ATR threshold | favorable reach rate | adverse reach rate |")
    lines.append("|---|---|---|")
    for threshold in tr["favorable"]:
        fav = tr["favorable"][threshold]
        adv = tr["adverse"][threshold]
        lines.append(
            f"| {threshold} | {_fmt_pct(fav['rate'])} ({fav['reached']}/{fav['total']}) "
            f"| {_fmt_pct(adv['rate'])} ({adv['reached']}/{adv['total']}) |"
        )
    lines.append("")

    lines.append("## Path ordering (favorable-first vs adverse-first vs neither)")
    for threshold, counts_by_ordering in report["path_ordering"].items():
        lines.append(f"- {threshold} ATR: {counts_by_ordering}")
    lines.append("")

    lines.append("## POI zone-touch / invalidation geometry")
    geo = report["poi_geometry"]
    lines.append(f"- Total POIs: {geo['total_pois']}")
    lines.append(f"- Touched: {geo['touched']} ({_fmt_pct(geo['touch_rate'])})")
    lines.append(f"- Far boundary crossed: {geo['far_boundary_crossed']}")
    lines.append(f"- Censored (no forward data): {geo['censored_no_forward_data']}")
    lines.append("")

    lines.append("## Reaction characterization (displacement FAST/VERY_FAST)")
    reaction = report["reaction"]
    lines.append(f"- Events with a qualifying reaction: {reaction['events_with_reaction']}"
                 f" / {reaction['total_events']} ({_fmt_pct(reaction['reaction_occurrence_rate'])})")
    lines.append(f"- Delay distribution (bars): {_fmt_dist(reaction['delay_distribution'])}")
    lines.append("")

    lines.append("## Frequency")
    freq = report["frequency"]
    lines.append(f"- Distinct days with events: {freq['distinct_days_with_events']}")
    lines.append(f"- Distinct weeks with events: {freq['distinct_weeks_with_events']}")
    lines.append("")

    lines.append("## Permission churn")
    lines.append(str(report["permission_churn"]))
    lines.append("")

    return "\n".join(lines)


def main() -> None:
    out_dir = REPO_ROOT / "artifacts" / "v1a_validation"
    result_path = out_dir / "v1a_dev_replay_result.json"
    data = json.loads(result_path.read_text(encoding="utf-8"))

    dev_m15_ohlc = data["dev_m15_ohlc"]
    events = data["events"]
    poi_registry = data["poi_registry"]
    atr_series: list[Decimal | None] = [
        Decimal(v) if v is not None else None for v in data["atr_series"]
    ]
    displacement_by_bar_index = {
        int(k): tuple(v) for k, v in data["displacement_by_bar_index"].items()
    }

    event_outcomes, event_exclusions = compute_event_outcomes(
        events, dev_m15_ohlc, atr_series, displacement_by_bar_index
    )
    availability_index = _availability_ms_index(dev_m15_ohlc)
    poi_outcomes, poi_exclusions = compute_poi_outcomes(
        poi_registry, dev_m15_ohlc, atr_series, availability_index
    )
    report = build_report(
        events, poi_registry, event_outcomes, poi_outcomes, event_exclusions, poi_exclusions
    )

    (out_dir / "v1a_characterization_report.json").write_text(
        json.dumps(report, indent=2, default=str), encoding="utf-8"
    )
    markdown = render_markdown(report)
    (out_dir / "V1A_CHARACTERIZATION_REPORT.md").write_text(markdown, encoding="utf-8")
    print(markdown)


if __name__ == "__main__":
    main()
