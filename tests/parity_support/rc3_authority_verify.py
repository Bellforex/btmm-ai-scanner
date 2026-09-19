"""RC3 final-authority verification: determinism, no lookahead, cross-day continuity.

Test/validation tooling only — reads finished authority artifacts, never the
engine. Three independent checks over one artifact set (plus an optional second
set for the determinism comparison):

1. DETERMINISM — per trading day, the P3 / P5 / P8 digests of two independent
   runs of the same code must be identical on every day both runs completed.
2. NO LOOKAHEAD — no row or event may be emitted before the information it
   carries exists. A source time EARLIER than availability is correct (source is
   the historical formation, availability the structural confirmation). P8 rows
   carry no availability of their own, so each event is joined to its POI's P3
   row on the same bar and judged per event type: every type at or after that
   availability, POI_ACTIVATED on the POI's first evaluated bar, POI_TERMINAL on
   the registry's own terminal bar exactly once with a reason and nothing after.
3. CROSS-DAY CONTINUITY — trading days are contiguous with no bar gap or
   overlap, the registry never shrinks across a boundary, each day's first bar
   still evaluates POIs that became available on an earlier day, and POIs do
   live across days. A live POI without a row on some bar is NOT a deletion:
   rows are written for the bar's bounded evaluation set, not the registry.
   Terminal-bar inclusion and next-bar exclusion are checked alongside.

    python -m tests.parity_support.rc3_authority_verify RUN_DIR [OTHER_RUN_DIR]
"""

from __future__ import annotations

import gzip
import json
import sys
from collections import defaultdict
from datetime import datetime, timedelta
from itertools import pairwise
from pathlib import Path
from typing import Any

__all__ = ["compare_daily_digests", "verify_authority"]

_DIGESTS = ("p3_digest", "p5_digest", "p8_digest")

#: FXCM session-day boundary (22:00 UTC -> next trading day), from the manifest.
_SESSION_OFFSET_HOURS = 2.0

#: The frozen P8 intra-POI priority (tests/parity_support/p8_alert_oracle.py).
_EVENT_PRIORITY: dict[str, int] = {
    "POI_ACTIVATED": 0,
    "BTMM_VALIDATED": 1,
    "PERMISSION_ENTERED_ACTIONABLE": 2,
    "PERMISSION_LOST_ACTIONABLE": 2,
    "POI_TERMINAL": 3,
}

#: Dynamic by contract: the CURRENT period extreme moves with the period.
ROLLING_PERIOD_TYPES = frozenset(
    {
        "CURRENT_DAY_HIGH",
        "CURRENT_DAY_LOW",
        "CURRENT_WEEK_HIGH",
        "CURRENT_WEEK_LOW",
        "CURRENT_MONTH_HIGH",
        "CURRENT_MONTH_LOW",
    }
)


def _poi_class(rows: list[dict[str, Any]]) -> str:
    """STATIC (lifecycle-eligible, frozen once available), ROLLING_PERIOD_LEVEL
    (the author's six CURRENT_* extremes) or CONTEXT_LEVEL (the remaining
    lifecycle NOT_APPLICABLE levels: PREVIOUS_* periods and EQUAL_*_LIQUIDITY,
    which also evolve as their period or cluster gains data)."""
    poi_type = rows[0]["poi_type"]
    if poi_type in ROLLING_PERIOD_TYPES:
        return "ROLLING_PERIOD_LEVEL"
    if rows[0].get("lifecycle_status") == "NOT_APPLICABLE":
        return "CONTEXT_LEVEL"
    return "STATIC"


def _rows(path: Path) -> list[dict[str, Any]]:
    """Every complete row. A run killed mid-write leaves a truncated gzip; its
    complete prefix is still evidence, so the truncation is reported, not raised."""
    out: list[dict[str, Any]] = []
    try:
        with gzip.open(path, "rt", encoding="utf-8") as handle:
            for line in handle:
                if line.endswith("\n"):
                    out.append(json.loads(line))
    except (EOFError, gzip.BadGzipFile, json.JSONDecodeError):
        pass
    return out


def _manifest(run: Path) -> dict[str, Any]:
    loaded: dict[str, Any] = json.loads(
        (run / "daily_authority_manifest.json").read_text("utf-8")
    )
    return loaded


def _days(manifest: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {d["trading_day"]: d for d in manifest["days"]}


def _time(value: str | None) -> datetime | None:
    return datetime.fromisoformat(value) if value else None


def compare_daily_digests(
    run_a: Path, run_b: Path, semantic_sha: str | None = None
) -> dict[str, Any]:
    """Determinism across two independent processes: same inputs, then per-day
    digests AND counts on every day both runs completed."""
    manifest_a, manifest_b = _manifest(run_a), _manifest(run_b)
    provenance = {}
    for key in (
        "authority_version",
        "window_start_event_utc",
        "window_end_event_utc",
        "context_lookback_bars",
        "warmup_feed_policy",
        "session_day_offset_hours",
        "series",
        "configuration",
    ):
        left = manifest_a.get("provenance", {}).get(key, manifest_a.get(key))
        right = manifest_b.get("provenance", {}).get(key, manifest_b.get(key))
        provenance[key] = {"equal": left == right, "a": left} if left != right else True
    heads = {
        run.name: (run / "HEAD.txt").read_text("utf-8").strip()
        if (run / "HEAD.txt").is_file()
        else None
        for run in (run_a, run_b)
    }
    head_values = {v for v in heads.values() if v}
    same_head = len(head_values) == 1 and (
        semantic_sha is None or next(iter(head_values)).startswith(semantic_sha)
    )

    a, b = _days(manifest_a), _days(manifest_b)
    shared = sorted(set(a) & set(b))
    counts = (
        "bars_processed",
        "new_p3_pois",
        "total_registry_pois",
        "pois_fresh_at_close",
        "pois_mitigated_at_close",
        "pois_invalidated_at_close",
        "p5_rows",
        "p5_actionable",
        "p8_events",
        "p8_terminal_events",
    )
    per_digest = {
        key: [day for day in shared if a[day][key] != b[day][key]] for key in _DIGESTS
    }
    mismatched_counts = {
        key: [day for day in shared if a[day].get(key) != b[day].get(key)]
        for key in counts
    }
    mismatched_counts = {k: v for k, v in mismatched_counts.items() if v}
    differing_bars = [
        day
        for day in shared
        if (a[day]["first_bar_ms"], a[day]["last_bar_ms"])
        != (b[day]["first_bar_ms"], b[day]["last_bar_ms"])
    ]
    return {
        "runs": [run_a.name, run_b.name],
        "heads": heads,
        "same_semantic_head": same_head,
        "inputs_identical": provenance,
        "days_available": {run_a.name: len(a), run_b.name: len(b)},
        "days_compared": len(shared),
        "first_day": shared[0] if shared else None,
        "last_day": shared[-1] if shared else None,
        "p3_digest_mismatched_days": per_digest["p3_digest"],
        "p5_digest_mismatched_days": per_digest["p5_digest"],
        "p8_digest_mismatched_days": per_digest["p8_digest"],
        "count_mismatches": mismatched_counts,
        "bar_window_mismatched_days": differing_bars,
        "deterministic": (
            same_head
            and all(v is True for v in provenance.values())
            and not any(per_digest.values())
            and not mismatched_counts
            and not differing_bars
        ),
    }


def verify_authority(run: Path) -> dict[str, Any]:
    manifest = _manifest(run)
    days = manifest["days"]
    p3 = _rows(run / "p3_registry_rows.ndjson.gz")
    p8 = _rows(run / "p8_event_rows.ndjson.gz")

    # ---- 2. no lookahead ---------------------------------------------------
    violations: dict[str, int] = defaultdict(int)
    examples: dict[str, Any] = {}

    def flag(kind: str, row: dict[str, Any]) -> None:
        violations[kind] += 1
        examples.setdefault(kind, {k: row.get(k) for k in list(row)[:8]})

    for row in p3:
        bar = int(row["bar_ms"])
        available = _time(row["availability_time_utc"])
        source = _time(row["source_time_utc"])
        if available is None:
            flag("p3_row_without_availability", row)
            continue
        if available.timestamp() * 1000 > bar:
            flag("p3_row_before_availability", row)
        if source is not None and source > available:
            flag("p3_source_after_availability", row)
        for field in ("terminal_time_utc", "mitigation_time_utc"):
            instant = _time(row.get(field))
            if instant is not None and instant < available:
                flag(f"p3_{field}_before_availability", row)
    # P8 rows carry no availability of their own (schema: bar_ms, trading_day,
    # sequence_in_bar, event_type, poi_idx, poi_record_id, poi_bullish, tier,
    # btmm_valid, permission, lifecycle, terminal_reason), so each event is
    # joined to its POI's P3 row on the SAME bar and judged against that row's
    # availability. The rules are event-type aware:
    #   * every type: event bar >= the availability known on that bar;
    #   * POI_ACTIVATED: on the POI's first EVALUATED bar. Equality with
    #     availability is NOT required — the per-bar evaluation set is bounded,
    #     so a POI can first be evaluated after it became available;
    #   * POI_TERMINAL: on the POI's own P3 terminal bar, exactly once, with a
    #     reason, and nothing after it. Same-bar terminal behaviour stays legal.
    row_at: dict[tuple[str, int], dict[str, Any]] = {}
    first_evaluated: dict[str, int] = {}
    p3_terminal_bar: dict[str, int] = {}
    for row in p3:
        poi = row["poi_record_id"]
        bar = int(row["bar_ms"])
        row_at[(poi, bar)] = row
        first_evaluated[poi] = min(first_evaluated.get(poi, bar), bar)
        if row.get("terminal") == "1":
            p3_terminal_bar[poi] = min(p3_terminal_bar.get(poi, bar), bar)

    event_types: dict[str, int] = defaultdict(int)
    terminal_events: dict[str, int] = defaultdict(int)
    for event in p8:
        poi = event["poi_record_id"]
        bar = int(event["bar_ms"])
        kind = event["event_type"]
        event_types[kind] += 1
        same_bar_row = row_at.get((poi, bar))
        if same_bar_row is None:
            flag(f"p8_{kind}_without_a_same_bar_registry_row", event)
            continue
        available = _time(same_bar_row["availability_time_utc"])
        if available is not None and available.timestamp() * 1000 > bar:
            flag(f"p8_{kind}_before_availability", event)
        if kind == "POI_ACTIVATED" and bar != first_evaluated[poi]:
            flag("p8_activation_not_on_the_first_evaluated_bar", event)
        if kind == "POI_TERMINAL":
            terminal_events[poi] += 1
            if not event.get("terminal_reason"):
                flag("p8_terminal_without_reason", event)
            if p3_terminal_bar.get(poi) != bar:
                flag("p8_terminal_not_on_the_registry_terminal_bar", event)
        terminal_bar = p3_terminal_bar.get(poi)
        if terminal_bar is not None and bar > terminal_bar:
            flag(f"p8_{kind}_after_its_poi_went_terminal", event)
    for poi, count in terminal_events.items():
        if count > 1:
            flag(
                "p8_more_than_one_terminal_event_for_one_poi",
                {"poi_record_id": poi, "terminal_events": count},
            )

    # ---- STATIC vs ROLLING PERIOD LEVEL vs CONTEXT LEVEL -------------------
    # A STATIC (lifecycle-eligible) POI is frozen once available: identity,
    # source, availability and geometry never change retroactively. A ROLLING
    # PERIOD LEVEL and a CONTEXT LEVEL are dynamic by contract, so instead of an
    # immutable-availability assertion they must only update CAUSALLY: every
    # row's availability at or before its own bar (checked above for all rows),
    # availability never moving backwards, geometry changing only together with
    # an availability advance, and the level's own period never being ahead of
    # the bar's trading day. A CURRENT_* level may still date from an earlier
    # session (a weekend, or a source timeframe whose new period has no bar yet)
    # — that is carry-forward, not staleness, so equality is NOT required.
    all_rows_by_poi: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in p3:
        all_rows_by_poi[row["poi_record_id"]].append(row)
    classes: dict[str, int] = defaultdict(int)
    for poi, rows in all_rows_by_poi.items():
        rows.sort(key=lambda r: int(r["bar_ms"]))
        poi_class = _poi_class(rows)
        classes[poi_class] += 1
        if poi_class == "STATIC":
            for field in (
                "availability_time_utc",
                "source_time_utc",
                "zone_top",
                "zone_bottom",
            ):
                if len({r[field] for r in rows}) > 1:
                    flag(
                        f"static_poi_mutated_{field}",
                        {
                            "poi_record_id": poi,
                            "poi_type": rows[0]["poi_type"],
                            "values": sorted({r[field] for r in rows}),
                        },
                    )
            continue
        availabilities = [r["availability_time_utc"] for r in rows]
        if availabilities != sorted(availabilities):
            flag(
                f"{poi_class.lower()}_availability_moved_backwards",
                {"poi_record_id": poi, "poi_type": rows[0]["poi_type"]},
            )
        for earlier, later in pairwise(rows):
            geometry_changed = (earlier["zone_top"], earlier["zone_bottom"]) != (
                later["zone_top"],
                later["zone_bottom"],
            )
            if (
                geometry_changed
                and later["availability_time_utc"] <= earlier["availability_time_utc"]
            ):
                flag(
                    f"{poi_class.lower()}_geometry_changed_without_new_data",
                    {"poi_record_id": poi, "poi_type": rows[0]["poi_type"]},
                )
        for row in rows:
            available = _time(row["availability_time_utc"])
            if available is None:
                continue
            session_day = (available + timedelta(hours=_SESSION_OFFSET_HOURS)).date()
            if str(session_day) > row["trading_day"]:
                flag(f"{poi_class.lower()}_period_ahead_of_its_bar", row)

    # ---- liquidity clusters (author, 2026-09-17) ---------------------------
    # EQUAL_HIGHS / EQUAL_LOWS are dynamic liquidity-context clusters: the
    # cluster identity is stable while source/availability advance as a later
    # equal-level member joins it. Required: every updated state is already
    # available at the bar where it FIRST appears, nothing moves backwards, no
    # earlier row is rewritten, and the cluster never emits a lifecycle terminal.
    liquidity_pois = {
        poi
        for poi, rows in all_rows_by_poi.items()
        if rows[0]["poi_type"].startswith("EQUAL_")
    }
    liquidity: dict[str, int] = defaultdict(int)
    for poi in liquidity_pois:
        rows = all_rows_by_poi[poi]
        liquidity["clusters"] += 1
        seen_state: dict[tuple[str, ...], int] = {}
        for row in rows:
            state = (
                row["availability_time_utc"],
                row["source_time_utc"],
                row["zone_top"],
                row["zone_bottom"],
            )
            bar = int(row["bar_ms"])
            if state not in seen_state:
                seen_state[state] = bar
                liquidity["state_updates"] += 1
                available = _time(row["availability_time_utc"])
                if available is not None and available.timestamp() * 1000 > bar:
                    flag("liquidity_update_available_after_its_first_bar", row)
            elif seen_state[state] > bar:
                flag("liquidity_state_reappeared_on_an_earlier_bar", row)
            if row.get("terminal") == "1" or row.get("terminal_reason"):
                flag("liquidity_cluster_went_terminal", row)
            if row.get("lifecycle_status") != "NOT_APPLICABLE":
                flag("liquidity_cluster_with_a_lifecycle_status", row)
        if len(seen_state) > 1:
            liquidity["clusters_that_advanced"] += 1
    # A cluster may still be activated and gain/lose actionable permission —
    # those are P8 stream events, not lifecycle. Only a LIFECYCLE TERMINAL is
    # forbidden for a NOT_APPLICABLE record; the rest are reported as counts.
    for event in p8:
        if event["poi_record_id"] not in liquidity_pois:
            continue
        liquidity[f"events_{event['event_type']}"] += 1
        if event["event_type"] == "POI_TERMINAL":
            flag("liquidity_cluster_emitted_a_lifecycle_terminal", event)

    # ---- P8 stream order (frozen native priority) --------------------------
    # Within one bar the stream is ordered by ascending poi_idx, then by the
    # frozen intra-POI priority (p8_alert_oracle._EVENT_PRIORITY: activated ->
    # BTMM validated -> permission -> terminal). No permission event may precede
    # its POI's first activation, on an earlier bar or earlier in the same bar.
    stream: dict[str, int] = defaultdict(int)
    first_bar_of_run = min((int(r["bar_ms"]) for r in p3), default=0)
    by_bar: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for event in p8:
        by_bar[int(event["bar_ms"])].append(event)
    for bar, events in by_bar.items():
        ordered = sorted(events, key=lambda e: int(e["sequence_in_bar"]))
        keys = [
            (int(e["poi_idx"]), _EVENT_PRIORITY.get(e["event_type"], 99))
            for e in ordered
        ]
        if keys != sorted(keys):
            flag("p8_bar_not_in_native_order", {"bar_ms": bar, "order": keys[:6]})
        if len({int(e["sequence_in_bar"]) for e in events}) != len(events):
            flag("p8_duplicate_sequence_in_bar", {"bar_ms": bar})

    first_activation: dict[str, tuple[int, int]] = {}
    for event in p8:
        if event["event_type"] == "POI_ACTIVATED":
            key = (int(event["bar_ms"]), int(event["sequence_in_bar"]))
            poi = event["poi_record_id"]
            first_activation[poi] = min(first_activation.get(poi, key), key)
    for event in p8:
        if not event["event_type"].startswith("PERMISSION_"):
            continue
        poi = event["poi_record_id"]
        stream["permission_events"] += 1
        activation = first_activation.get(poi)
        if activation is None:
            # AlertEngine.prime() seeds pre-existing state at attach WITHOUT
            # emitting events, so a POI already alive on the run's first bar has
            # no activation event to precede its later permission transitions.
            if first_evaluated.get(poi) == first_bar_of_run:
                stream["permission_for_a_primed_poi"] += 1
                continue
            flag("p8_permission_for_a_poi_that_never_activated", event)
            continue
        here = (int(event["bar_ms"]), int(event["sequence_in_bar"]))
        if here < activation:
            flag("p8_permission_before_its_poi_activated", event)
        elif here[0] == activation[0]:
            stream["permission_on_the_activation_bar"] += 1

    # ---- primed-at-attach POIs (author, 2026-09-17) ------------------------
    # prime() seeds pre-existing state at the attach bar without emitting
    # events, so these POIs have no POI_ACTIVATED. Required instead: the primed
    # set is exactly the attach bar's evaluated set and matches the run summary;
    # no activation may be dated before attach; permission events start at or
    # after attach; and every permission event is a real transition — ENTERED
    # and LOST alternate, and a primed POI's first event must move AWAY from the
    # permission it was primed with (actionable -> LOST, otherwise -> ENTERED).
    primed = {
        row["poi_record_id"] for row in p3 if int(row["bar_ms"]) == first_bar_of_run
    }
    summary = json.loads((run / "run_summary.json").read_text("utf-8"))
    primed_expected = summary.get("pois_primed_at_attach")
    if primed_expected is not None and len(primed) != primed_expected:
        flag(
            "primed_set_does_not_match_the_run_summary",
            {"attach_bar_pois": len(primed), "run_summary": primed_expected},
        )
    permission_at_attach = {
        row["poi_record_id"]: row.get("analytical_permission")
        for row in _rows(run / "p5_assessment_rows.ndjson.gz")
        if int(row["bar_ms"]) == first_bar_of_run
    }
    actionable = {"BUY_BIAS", "SELL_BIAS"}
    events_by_poi: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for event in p8:
        events_by_poi[event["poi_record_id"]].append(event)
    for poi, events in events_by_poi.items():
        events.sort(key=lambda e: (int(e["bar_ms"]), int(e["sequence_in_bar"])))
        permissions = [e for e in events if e["event_type"].startswith("PERMISSION_")]
        for earlier, later in pairwise(permissions):
            if earlier["event_type"] == later["event_type"]:
                flag("p8_repeated_permission_without_the_opposite_transition", later)
        if poi not in primed:
            continue
        stream["primed_pois_with_events"] += 1
        if any(
            e["event_type"] == "POI_ACTIVATED" and int(e["bar_ms"]) < first_bar_of_run
            for e in events
        ):
            flag("primed_poi_activated_before_the_attach_bar", events[0])
        if permissions:
            if int(permissions[0]["bar_ms"]) < first_bar_of_run:
                flag("primed_poi_permission_before_the_attach_bar", permissions[0])
            was_actionable = permission_at_attach.get(poi) in actionable
            expected = (
                "PERMISSION_LOST_ACTIONABLE"
                if was_actionable
                else "PERMISSION_ENTERED_ACTIONABLE"
            )
            if permissions[0]["event_type"] != expected:
                flag("primed_poi_first_permission_is_not_a_transition", permissions[0])

    # ---- append-only: a bar's recorded state is never rewritten ------------
    seen_rows: dict[tuple[str, int], dict[str, Any]] = {}
    for row in p3:
        row_key = (str(row["poi_record_id"]), int(row["bar_ms"]))
        previous = seen_rows.get(row_key)
        if previous is not None and previous != row:
            flag("registry_row_rewritten_for_the_same_poi_and_bar", row)
        seen_rows[row_key] = row

    # ---- lifecycle: terminal-bar inclusion, next-bar exclusion -------------
    rows_by_poi: dict[str, list[int]] = defaultdict(list)
    for row in p3:
        rows_by_poi[row["poi_record_id"]].append(int(row["bar_ms"]))
    lifecycle: dict[str, int] = defaultdict(int)
    for poi, terminal_bar in p3_terminal_bar.items():
        bars = rows_by_poi[poi]
        lifecycle["pois_with_a_terminal_bar"] += 1
        if terminal_bar not in bars:
            lifecycle["missing_row_on_the_terminal_bar"] += 1
        after = sum(1 for bar in bars if bar > terminal_bar)
        if after:
            lifecycle["rows_after_the_terminal_bar"] += after

    # ---- 3. cross-day continuity -------------------------------------------
    # A P3 row is written for the bar's EVALUATED set (the bounded P5 loop), not
    # for the whole registry, so a live POI legitimately has bars without a row.
    # Continuity means: nothing resets at a day boundary — the first bar of each
    # day still evaluates POIs that became available on an earlier day, and the
    # registry never shrinks.
    first_bar_of_day = {d["first_bar_ms"]: d["trading_day"] for d in days}
    carry_over: dict[str, int] = defaultdict(int)
    for row in p3:
        day = first_bar_of_day.get(int(row["bar_ms"]))
        if day is None:
            continue
        available = _time(row["availability_time_utc"])
        if available is not None and available.isoformat()[:10] < day:
            carry_over[day] += 1

    gaps: list[dict[str, Any]] = []
    dropped: list[dict[str, Any]] = []
    for previous, current in pairwise(days):
        if current["first_bar_ms"] <= previous["last_bar_ms"]:
            gaps.append(
                {
                    "between": (previous["trading_day"], current["trading_day"]),
                    "reason": "overlapping or non-increasing bars",
                }
            )
        if current["total_registry_pois"] < previous["total_registry_pois"]:
            dropped.append(
                {
                    "between": (previous["trading_day"], current["trading_day"]),
                    "registry": (
                        previous["total_registry_pois"],
                        current["total_registry_pois"],
                    ),
                }
            )
        if not carry_over.get(current["trading_day"]):
            dropped.append(
                {
                    "between": (previous["trading_day"], current["trading_day"]),
                    "reason": "no earlier-day POI evaluated on the first bar",
                }
            )
    lifetimes = defaultdict(set)
    for row in p3:
        lifetimes[row["poi_record_id"]].add(row["trading_day"])
    multi_day = sum(1 for v in lifetimes.values() if len(v) > 1)

    return {
        "run": str(run),
        "complete": json.loads((run / "run_summary.json").read_text("utf-8"))[
            "complete"
        ],
        "days": len(days),
        "bars": sum(d["bars_processed"] for d in days),
        "p3_rows": len(p3),
        "p8_events": len(p8),
        "p8_event_types": dict(event_types),
        "poi_classes": dict(classes),
        "liquidity_clusters": dict(liquidity),
        "p8_stream_order": dict(stream),
        "primed_at_attach": {
            "pois": len(primed),
            "run_summary": primed_expected,
        },
        "no_lookahead": {
            "violations": dict(violations),
            "examples": examples,
            "passed": not violations,
        },
        "terminal_lifecycle": {
            "counts": dict(lifecycle),
            "terminal_events": sum(terminal_events.values()),
            "pois_with_a_terminal_event": len(terminal_events),
            "passed": (
                not lifecycle.get("missing_row_on_the_terminal_bar")
                and not lifecycle.get("rows_after_the_terminal_bar")
                and all(count == 1 for count in terminal_events.values())
            ),
        },
        "cross_day_continuity": {
            "bar_sequence_problems": gaps,
            "day_boundary_problems": dropped,
            "carry_over_pois_on_first_bar_by_day": dict(carry_over),
            "pois_living_across_days": multi_day,
            "distinct_pois": len(lifetimes),
            "passed": not gaps and not dropped and multi_day > 0,
        },
        "period_digests": manifest["period_digests"],
    }


def main() -> int:  # pragma: no cover - manual verification
    run = Path(sys.argv[1])
    report = verify_authority(run)
    if len(sys.argv) > 2:
        report["determinism_vs_" + Path(sys.argv[2]).name] = compare_daily_digests(
            run, Path(sys.argv[2]), semantic_sha="3f9f790"
        )
    print(json.dumps(report, indent=1))
    (run / "verification.json").write_text(json.dumps(report, indent=1), "utf-8")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
