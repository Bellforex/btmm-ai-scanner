"""Row-level diff of two RC3 daily-authority artifact sets over the same bars.

Test/validation tooling only. Used to report the downstream impact of an
intentional semantic revision (P3 rows, P5 rows and component scores,
permissions, P8 events). Rows are matched by semantic identity -- POI type,
direction, timeframe, source time, zone -- plus the bar, never by record id,
because a type change legitimately changes record identity.
"""

from __future__ import annotations

import gzip
import json
from collections import Counter
from pathlib import Path
from typing import Any

__all__ = ["diff_authorities"]

#: Incidental numbering: registry position shifts when a type changes.
_INCIDENTAL = frozenset({"poi_record_id", "poi_idx", "sequence_in_bar"})

_SCORES = (
    "score_btmm",
    "score_poi",
    "score_trend",
    "score_regime",
    "score_momentum",
    "score_breakout",
    "score_liquidity",
    "score_volatility",
    "final_confluence_score",
)


def _rows(path: Path) -> list[dict[str, Any]]:
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle]


def _identity_by_record(p3: list[dict[str, Any]]) -> dict[str, tuple[str, ...]]:
    ident: dict[str, tuple[str, ...]] = {}
    for r in p3:
        ident.setdefault(
            r["poi_record_id"],
            (
                r["poi_type"],
                r["direction"],
                r["source_timeframe"],
                r["source_time_utc"],
                r["zone_top"],
                r["zone_bottom"],
            ),
        )
    return ident


def diff_authorities(before: Path, after: Path) -> dict[str, Any]:
    out: dict[str, Any] = {}
    p3b = _rows(before / "p3_registry_rows.ndjson.gz")
    p3a = _rows(after / "p3_registry_rows.ndjson.gz")
    ib, ia = _identity_by_record(p3b), _identity_by_record(p3a)

    def keyed_p3(rows, ident):
        return {
            (r["bar_ms"], ident[r["poi_record_id"]]): {
                k: v for k, v in r.items() if k not in _INCIDENTAL
            }
            for r in rows
        }

    kb, ka = keyed_p3(p3b, ib), keyed_p3(p3a, ia)
    only_b = set(kb) - set(ka)
    only_a = set(ka) - set(kb)
    changed = {k for k in set(kb) & set(ka) if kb[k] != ka[k]}
    out["p3"] = {
        "rows_before": len(kb),
        "rows_after": len(ka),
        "removed_rows": len(only_b),
        "added_rows": len(only_a),
        "changed_rows": len(changed),
        "removed_by_type": dict(Counter(k[1][0] for k in only_b)),
        "added_by_type": dict(Counter(k[1][0] for k in only_a)),
        "changed_by_type": dict(Counter(k[1][0] for k in changed)),
        "distinct_pois_before": len(set(ib.values())),
        "distinct_pois_after": len(set(ia.values())),
    }

    p5b = _rows(before / "p5_assessment_rows.ndjson.gz")
    p5a = _rows(after / "p5_assessment_rows.ndjson.gz")

    def keyed_p5(rows, ident):
        return {
            (r["bar_ms"], ident[r["poi_record_id"]]): {
                k: v for k, v in r.items() if k not in _INCIDENTAL
            }
            for r in rows
        }

    qb, qa = keyed_p5(p5b, ib), keyed_p5(p5a, ia)
    common = set(qb) & set(qa)
    changed5 = [k for k in common if qb[k] != qa[k]]
    score_changes = Counter(
        s for k in changed5 for s in _SCORES if qb[k].get(s) != qa[k].get(s)
    )
    permission_changes = sum(
        1
        for k in common
        if qb[k].get("analytical_permission") != qa[k].get("analytical_permission")
    )
    out["p5"] = {
        "rows_before": len(qb),
        "rows_after": len(qa),
        "removed_rows": len(set(qb) - set(qa)),
        "added_rows": len(set(qa) - set(qb)),
        "changed_rows": len(changed5),
        "component_changes": dict(score_changes),
        "permission_changes_on_common_rows": permission_changes,
    }

    p8b = _rows(before / "p8_event_rows.ndjson.gz")
    p8a = _rows(after / "p8_event_rows.ndjson.gz")

    def keyed_p8(rows, ident):
        return Counter(
            (
                r["bar_ms"],
                r["event_type"],
                ident.get(r["poi_record_id"], ("?",)),
                r.get("permission"),
                r.get("terminal_reason"),
            )
            for r in rows
        )

    eb, ea = keyed_p8(p8b, ib), keyed_p8(p8a, ia)
    out["p8"] = {
        "events_before": sum(eb.values()),
        "events_after": sum(ea.values()),
        "removed_events": sum((eb - ea).values()),
        "added_events": sum((ea - eb).values()),
        "removed_by_type": dict(Counter(k[1] for k in (eb - ea).elements())),
        "added_by_type": dict(Counter(k[1] for k in (ea - eb).elements())),
        "terminal_reasons_after": dict(
            Counter(
                r.get("terminal_reason")
                for r in p8a
                if r["event_type"] == "POI_TERMINAL"
            )
        ),
    }
    return out


def main(argv: list[str] | None = None) -> int:  # pragma: no cover - manual
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("before", type=Path)
    parser.add_argument("after", type=Path)
    args = parser.parse_args(argv)
    print(json.dumps(diff_authorities(args.before, args.after), indent=1))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
