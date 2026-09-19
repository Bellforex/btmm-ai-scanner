"""RC4 bounded backtest / replay report (seminar evidence, NOT an authority).

Test/validation tooling only. Walks the unchanged Level-A replay with the RC4
market-framework profile over a bounded window and aggregates, per POI, its
LAST evaluated RC4 decision plus every P8 event. No profitability claim: the
report counts analytical states, it does not score trades.

    python -m tests.parity_support.rc4_bounded_backtest --bars 300 \\
        --host M15 --out artifacts/rc4_backtest/m15_300
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from btmm_ai_scanner.config.enums import Timeframe
from tests.parity_support.level_a_replay import WarmupFeedPolicy, iter_level_a_bars
from tests.parity_support.rc3_daily_authority import (
    WINDOW_START_EVENT_UTC,
    build_authority_configuration,
    load_level_a_window,
)

_ALL = (
    Timeframe.M5,
    Timeframe.M15,
    Timeframe.H1,
    Timeframe.H4,
    Timeframe.D1,
    Timeframe.W1,
)
_ROOT = Path(__file__).resolve().parents[2] / "artifacts" / "v1a_validation"

__all__ = ["run_bounded_backtest"]


def run_bounded_backtest(
    *,
    bars: int,
    host: Timeframe = Timeframe.M15,
    start: datetime = WINDOW_START_EVENT_UTC,
    rc4: bool = True,
) -> dict[str, Any]:
    contexts = tuple(tf for tf in _ALL if tf is not host)
    window = load_level_a_window(
        _ROOT,
        window_start_event_utc=start,
        host_timeframe=host,
        context_timeframes=contexts,
        max_bars=bars,
    )
    host_series = window.host_series
    last_decision: dict[str, Any] = {}
    last_meta: dict[str, dict[str, Any]] = {}
    events: Counter[str] = Counter()
    permission_rows: Counter[str] = Counter()
    evaluated_rows = 0
    for bar in iter_level_a_bars(
        host_timeframe=window.host_timeframe,
        host_series=host_series,
        context_series=window.context_series,
        configuration=build_authority_configuration(
            host_timeframe=host, context_timeframes=contexts
        ),
        rc3_freshness=True,
        warmup_feed_policy=WarmupFeedPolicy.AVAILABILITY,
        rc4_framework=rc4,
    ):
        for event in bar.events:
            events[event.event_type.value] += 1
        for poi_id in bar.evaluated_order:
            decision = bar.decision_by_id[poi_id]
            evaluated_rows += 1
            permission_rows[decision.analytical_permission.value] += 1
            key = str(poi_id)
            last_decision[key] = decision
            poi = bar.observation_by_id[poi_id]
            last_meta[key] = {
                "poi_type": poi.poi_type.value,
                "direction": poi.direction.value,
                "source_timeframe": poi.source_timeframe.value,
                "last_bar": bar.candle.event_time_utc.isoformat(),
            }

    per_poi = []
    for key, d in last_decision.items():
        per_poi.append(
            {
                **last_meta[key],
                "poi_record_id": key,
                "framework": d.framework,
                "fib_bucket": d.fib_bucket,
                "retracement_pct": d.retracement_pct,
                "range_position": d.range_position,
                "sweep_before_poi": d.sweep_before_poi,
                "btmm_pretrade_reason": d.btmm_pretrade_reason,
                "distraction": d.btmm_distraction,
                "delay": d.btmm_delay,
                "wipeout": d.btmm_wipeout,
                "true_failure": d.btmm_true_failure,
                "dwell": d.poi_dwell_bars,
                "touches": d.poi_touch_count,
                "zone_returns": d.poi_zone_return_count,
                "episode": d.interaction_episode,
                "permission": d.analytical_permission.value,
                "final_score": d.final_confluence_score,
                "score_btmm": d.component_scores.btmm_score,
                "score_liquidity": d.component_scores.liquidity_score,
                "evidence": list(d.framework_evidence),
            }
        )

    def count(field: str) -> dict[str, int]:
        return dict(Counter(str(p[field]) for p in per_poi))

    return {
        "host": window.host_timeframe.value,
        "bars": len(host_series),
        "first_bar": host_series[0].event_time_utc.isoformat(),
        "last_bar": host_series[-1].event_time_utc.isoformat(),
        "profile": "RC4" if rc4 else "RC3",
        "pois_evaluated": len(per_poi),
        "p5_rows": evaluated_rows,
        "p5_permission_rows": dict(permission_rows),
        "p8_events": dict(events),
        "btmm_reason": count("btmm_pretrade_reason"),
        "btmm_distraction": sum(p["distraction"] for p in per_poi),
        "btmm_delay": sum(p["delay"] for p in per_poi),
        "btmm_wipeout": sum(p["wipeout"] for p in per_poi),
        "btmm_true_failure": sum(p["true_failure"] for p in per_poi),
        "framework": count("framework"),
        "fib_bucket": count("fib_bucket"),
        "range_position": count("range_position"),
        "episode": count("episode"),
        "final_permission": count("permission"),
        "per_poi": per_poi,
    }


def main() -> int:  # pragma: no cover - manual measurement
    parser = argparse.ArgumentParser()
    parser.add_argument("--bars", type=int, default=300)
    parser.add_argument("--host", default="M15")
    parser.add_argument("--start", default=None, help="window start, ISO UTC")
    parser.add_argument(
        "--rc3", action="store_true", help="RC3 baseline instead of RC4"
    )
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    start = (
        datetime.fromisoformat(args.start).replace(tzinfo=UTC)
        if args.start
        else WINDOW_START_EVENT_UTC
    )
    report = run_bounded_backtest(
        bars=args.bars, host=Timeframe(args.host), start=start, rc4=not args.rc3
    )
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "report.json").write_text(json.dumps(report, indent=1), "utf-8")
    summary = {k: v for k, v in report.items() if k != "per_poi"}
    print(json.dumps(summary, indent=1))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
