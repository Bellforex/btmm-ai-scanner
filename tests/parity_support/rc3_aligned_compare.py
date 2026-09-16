"""RC3 aligned LEVEL A vs LEVEL B comparator with automatic first-divergence.

Test/validation tooling only.

LEVEL A: the per-bar P3 / P5 / P8 rows written by ``rc3_aligned_capture``
(the unchanged ``run_daily_authority`` over the exact bars one Pine run used).
LEVEL B: that Pine run's own ``P3LIFE`` / ``P5C`` / ``P8EVENT`` log lines.

SCOPE, STATED EXPLICITLY
-------------------------
* The Pine PARITY build's registry is single-timeframe (host) and P3 CORE
  (type codes 1-18) by construction. Level A evaluates POIs from every
  tracked timeframe and also the liquidity / period-level families. The
  comparison is therefore over Level-A POIs whose ``source_timeframe`` AND
  ``effective_timeframe`` are the host and whose type is one of the 18 core
  types. Level-A POIs outside that scope are COUNTED and reported, never
  silently dropped.
* CANONICAL IDENTITY KEEPS THE SOURCE TIMEFRAME (author decision 3). A host
  POI whose ``effective_timeframe`` was raised by the cross-timeframe merge
  (``poi/overlap.py resolve_merges``) is still a host POI: it is matched on
  ``source_timeframe`` and the raised timeframe is reported as DERIVED
  higher-timeframe context (``higher_tf_context``), never as a P3 identity or
  field divergence. Its downstream P5/P8 rows are still compared field by
  field and classed ``higher_tf_context`` so their divergence stays visible.
* P8 ORDER (author decision 4). Pine's native order -- registry index, then
  event priority ACTIVATED < BTMM_VALIDATED < ENTERED/LOST_ACTIONABLE <
  TERMINAL -- is authoritative. Python events are associated to Pine POIs by
  canonical identity and checked against that order; Level A's own record
  numbering is incidental and is never compared to Pine's.
* POIs are matched by identity ``(type, direction, source_ms, availability_ms,
  top, bottom)`` — never by index, because Level A numbers every timeframe's
  POIs in one sequence while Pine numbers only the host's.
* Only bars Level A has actually completed (whole trading days flushed by the
  authority) are compared. Nothing about bars beyond that point is claimed.
* P5 is compared only on bars the Pine run emitted ``P5C`` for.

No tolerance is invented. Integer scores, codes and permissions must be
equal. Geometry is compared on the printed decimal value; Pine prints floats
with ``str.tostring`` so a value is compared after rounding both sides to the
same 8 decimals, and any difference is reported with both raw values.
"""

from __future__ import annotations

import gzip
import json
import re
from collections import Counter, defaultdict
from collections.abc import Iterator
from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from btmm_ai_scanner.btrc.enums import (
    AnalyticalPermission,
    SignalLifecycleState,
    TrendAlignment,
)
from btmm_ai_scanner.poi.enums import PoiLifecycleStatus
from tests.parity_support.p3_lifecycle_model import LC_CODE
from tests.parity_support.p4_atomic_state_replay import CODE_BY_POI_TYPE
from tests.parity_support.p5_wire_normalized_replay import (
    ALIGNMENT_CODE,
    LIFECYCLE_CODE,
    PERMISSION_CODE,
)

__all__ = ["ComparisonReport", "compare"]

_EVENT = re.compile(r"P8EVENT\|type=([A-Z_]+)\|([^\"\n]*)")
_P3 = re.compile(r"P3LIFE\|([^\"\n]*)")
_P5C = re.compile(r"P5C\|([^\"\n]*)")
_TIER_CODE = {"": 0, "STANDARD": 1, "STRONG": 2}
_TERM_CODE = {"": 0, "MITIGATED": 1, "INVALIDATED": 2}
_STAGE_ORDER = {"P3": 0, "P5": 1, "P8": 2}


def _kv(blob: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for part in blob.split("|"):
        if "=" in part:
            k, _, v = part.partition("=")
            out[k] = v
    return out


def _iso_ms(value: str) -> int:
    return int(datetime.fromisoformat(value).timestamp() * 1000)


def _geom(value: str) -> str:
    return f"{Decimal(value):.8f}"


Identity = tuple[int, int, int, int, str, str]


@dataclass
class Mismatch:
    stage: str
    bar_ms: int
    poi: str
    field: str
    python: Any
    pine: Any

    def as_dict(self) -> dict[str, Any]:
        return {
            "stage": self.stage,
            "bar_ms": self.bar_ms,
            "bar_utc": datetime.fromtimestamp(self.bar_ms / 1000, tz=UTC).isoformat()
            if self.bar_ms
            else None,
            "poi": self.poi,
            "field": self.field,
            "python": self.python,
            "pine": self.pine,
        }


@dataclass
class ComparisonReport:
    compared_through_bar_ms: int
    level_a_bars: int
    scope: dict[str, Any] = field(default_factory=dict)
    p3: dict[str, Any] = field(default_factory=dict)
    p5: dict[str, Any] = field(default_factory=dict)
    p8: dict[str, Any] = field(default_factory=dict)
    daily: dict[str, dict[str, int]] = field(default_factory=dict)
    first_divergence: dict[str, Any] | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "compared_through_bar_ms": self.compared_through_bar_ms,
            "level_a_bars": self.level_a_bars,
            "scope": self.scope,
            "p3": self.p3,
            "p5": self.p5,
            "p8": self.p8,
            "daily": self.daily,
            "first_divergence": self.first_divergence,
        }


def _rows(path: Path, through_bar_ms: int) -> Iterator[dict[str, str]]:
    """Rows up to and including ``through_bar_ms``.

    The authority may still be appending to the file, so a truncated gzip
    member or a half-written last line at the tail ends the read instead of
    failing it; rows past the last completed trading day are never yielded.
    """
    try:
        with gzip.open(path, "rt", encoding="utf-8") as handle:
            for line in handle:
                if not line.strip():
                    continue
                try:
                    row = json.loads(line)
                except json.JSONDecodeError:
                    return
                if int(row["bar_ms"]) > through_bar_ms:
                    return
                yield row
    except (EOFError, gzip.BadGzipFile):
        return


def _day_of(bar_ms: int) -> str:
    from datetime import UTC, timedelta

    return (
        (
            datetime.fromtimestamp(bar_ms / 1000, tz=UTC)
            - timedelta(minutes=15)
            + timedelta(hours=2)
        )
        .date()
        .isoformat()
    )


def compare(
    capture: Path, authority_dir: Path, host_timeframe: str = "M15"
) -> ComparisonReport:
    text = capture.read_text(encoding="utf-8", errors="replace")

    # ---------------- LEVEL B (Pine) ----------------
    pine_identity: dict[int, Identity] = {}
    pine_p3: dict[int, dict[str, str]] = {}
    for blob in _P3.findall(text):
        f = _kv(blob)
        idx = int(f["poiIdx"])
        pine_identity[idx] = (
            int(f["type"]),
            1 if int(f["dir"]) > 0 else -1,
            int(f["srcTime"]),
            int(f["availTime"]),
            _geom(f["top"]),
            _geom(f["bottom"]),
        )
        pine_p3[idx] = f
    pine_idx_by_identity = {v: k for k, v in pine_identity.items()}
    if len(pine_idx_by_identity) != len(pine_identity):
        raise AssertionError("Pine P3LIFE identities are not unique")

    pine_events: list[dict[str, Any]] = []
    for etype, blob in _EVENT.findall(text):
        f = _kv(blob)
        pine_events.append({"type": etype, **f})

    pine_p5: dict[int, dict[int, list[str]]] = defaultdict(dict)
    pine_p5_bars: set[int] = set()
    for blob in _P5C.findall(text):
        head, _, rows = blob.partition("|rows=")
        f = _kv(head)
        bar = int(f["bar"])
        pine_p5_bars.add(bar)
        for row in filter(None, rows.split(";")):
            cols = row.split(",")
            pine_p5[bar][int(cols[0])] = cols

    # ---------------- LEVEL A (Python) ----------------
    manifest = json.loads(
        (authority_dir / "daily_authority_manifest.json").read_text(encoding="utf-8")
    )
    days = (
        manifest["days"]
        if isinstance(manifest, dict) and "days" in manifest
        else manifest
    )
    if not days:
        raise AssertionError("Level A has not completed a trading day yet")
    through = max(int(d["last_bar_ms"]) for d in days)
    level_a_bars = sum(int(d["bars_processed"]) for d in days)

    py_identity: dict[str, Identity] = {}
    py_last_p3: dict[str, dict[str, str]] = {}
    out_of_scope: Counter[str] = Counter()
    promoted: dict[str, str] = {}
    for row in _rows(authority_dir / "p3_registry_rows.ndjson.gz", through):
        rid = row["poi_record_id"]
        if row["source_timeframe"] != host_timeframe:
            out_of_scope[f"timeframe:{row['source_timeframe']}"] += (
                0 if rid in py_identity else 1
            )
            continue
        if row["effective_timeframe"] != host_timeframe:
            # Cross-timeframe merge (poi/overlap.py resolve_merges) raised
            # this host POI's effective timeframe. That is derived
            # higher-timeframe context; identity stays on source_timeframe.
            promoted[rid] = row["effective_timeframe"]
        type_code = CODE_BY_POI_TYPE.get(_poi_type(row["poi_type"]))
        if type_code is None or type_code > 18:
            out_of_scope[f"type:{row['poi_type']}"] += 0 if rid in py_identity else 1
            continue
        py_identity.setdefault(
            rid,
            (
                type_code,
                1 if row["direction"] == "BULLISH" else -1,
                _iso_ms(row["source_time_utc"]),
                _iso_ms(row["availability_time_utc"]),
                _geom(row["zone_top"]),
                _geom(row["zone_bottom"]),
            ),
        )
        py_last_p3[rid] = row

    mismatches: list[Mismatch] = []
    daily: dict[str, Counter[str]] = defaultdict(Counter)

    # ---------------- P3 ----------------
    py_by_identity = {v: k for k, v in py_identity.items()}
    pine_evaluated = {
        int(e["poiIdx"])
        for e in pine_events
        if e["type"] == "POI_ACTIVATED" and int(e["bar"]) <= through
    }
    python_only = [
        rid for rid, ident in py_identity.items() if ident not in pine_idx_by_identity
    ]
    pine_only = [
        idx
        for idx in sorted(pine_evaluated)
        if pine_identity[idx] not in py_by_identity
    ]
    for rid in python_only:
        ident = py_identity[rid]
        mismatches.append(
            Mismatch("P3", ident[3], f"py:{rid}", "python_only", ident, None)
        )
    for idx in pine_only:
        ident = pine_identity[idx]
        mismatches.append(
            Mismatch("P3", ident[3], f"pine:{idx}", "pine_only", None, ident)
        )
    p3_field_mismatches = 0
    for rid, ident in py_identity.items():
        idx = pine_idx_by_identity.get(ident)
        if idx is None:
            continue
        py = py_last_p3[rid]
        pine = pine_p3[idx]
        checks = {
            "tier": (_TIER_CODE[py["strength_tier"]], int(pine["tier"])),
        }
        py_term_ms = _iso_ms(py["terminal_time_utc"]) if py["terminal_time_utc"] else 0
        if py["terminal"] == "1":
            checks["termReason"] = (
                _TERM_CODE[py["terminal_reason"]],
                int(pine["termReason"]),
            )
            checks["termTime"] = (py_term_ms, int(pine["termTime"]))
        elif int(pine["termTime"] or 0) and int(pine["termTime"]) <= int(py["bar_ms"]):
            checks["terminal_by_last_python_bar"] = (0, int(pine["termTime"]))
        for name, (a, b) in checks.items():
            if a != b:
                p3_field_mismatches += 1
                mismatches.append(
                    Mismatch("P3", int(py["bar_ms"]), f"pine:{idx}", name, a, b)
                )

    # ---------------- P8 ----------------
    py_events = [
        e
        for e in _rows(authority_dir / "p8_event_rows.ndjson.gz", through)
        if e["poi_record_id"] in py_identity
    ]
    py_events_mapped: list[dict[str, Any]] = []
    unmatched_py_event_pois = 0
    for e in py_events:
        idx = pine_idx_by_identity.get(py_identity[e["poi_record_id"]])
        if idx is None:
            unmatched_py_event_pois += 1
            continue
        py_events_mapped.append({**e, "pine_idx": idx})
    py_key = {
        (e["event_type"], e["pine_idx"], int(e["bar_ms"])): e for e in py_events_mapped
    }
    pine_key = {
        (e["type"], int(e["poiIdx"]), int(e["bar"])): e
        for e in pine_events
        if int(e["bar"]) <= through
    }
    missing = sorted(set(pine_key) - set(py_key), key=lambda k: (k[2], k[1]))
    extra = sorted(set(py_key) - set(pine_key), key=lambda k: (k[2], k[1]))
    for k in missing:
        mismatches.append(
            Mismatch("P8", k[2], f"pine:{k[1]}", f"missing_in_python:{k[0]}", None, k)
        )
    for k in extra:
        mismatches.append(
            Mismatch("P8", k[2], f"pine:{k[1]}", f"extra_in_python:{k[0]}", k, None)
        )
    payload_mismatches = 0
    for k in set(py_key) & set(pine_key):
        a, b = py_key[k], pine_key[k]
        pairs = {
            "permission": (int(a["permission"]), int(b["permission"])),
            "lifecycle": (int(a["lifecycle"]), int(b["lifecycle"])),
            "btmmValid": (a["btmm_valid"] == "1", b["btmmValid"] == "true"),
            "poiDir": (a["poi_bullish"] == "1", b["poiDir"] == "BULL"),
        }
        if k[0] == "POI_TERMINAL":
            pairs["terminalReason"] = (
                a["terminal_reason"],
                b.get("terminalReason", ""),
            )
        for name, (x, y) in pairs.items():
            if x != y:
                payload_mismatches += 1
                mismatches.append(Mismatch("P8", k[2], f"pine:{k[1]}", name, x, y))
    # native ordering within a bar (author decision 4): Pine's own log order
    # must be its native (poiIdx, event priority) order, and Python's events,
    # associated to Pine POIs by canonical identity, must realise that same
    # order. Level A's own record numbering is incidental and never compared.
    ordering_mismatches = 0
    pine_native_order_violations = 0
    pine_order: dict[int, list[tuple[str, int]]] = defaultdict(list)
    for e in pine_events:
        if int(e["bar"]) <= through:
            pine_order[int(e["bar"])].append((e["type"], int(e["poiIdx"])))
    for bar, seq in pine_order.items():
        if seq != sorted(seq, key=_native_key):
            pine_native_order_violations += 1
            mismatches.append(
                Mismatch("P8", bar, "-", "pine_native_order", seq[:6], None)
            )
    py_order: dict[int, list[tuple[str, int]]] = defaultdict(list)
    for e in sorted(
        py_events_mapped, key=lambda e: (int(e["bar_ms"]), int(e["sequence_in_bar"]))
    ):
        py_order[int(e["bar_ms"])].append((e["event_type"], e["pine_idx"]))
    # Within one POI Python must emit in the same priority order Pine does;
    # that part of the order is semantic, not incidental numbering.
    python_priority_violations = 0
    for bar, seq in py_order.items():
        by_poi: dict[int, list[int]] = defaultdict(list)
        for etype, idx in seq:
            by_poi[idx].append(P8_EVENT_PRIORITY[etype])
        if any(v != sorted(v) for v in by_poi.values()):
            python_priority_violations += 1
            mismatches.append(
                Mismatch("P8", bar, "-", "python_event_priority", seq[:6], None)
            )
    for bar in sorted(set(py_order) & set(pine_order)):
        common = set(py_order[bar]) & set(pine_order[bar])
        a = sorted((x for x in py_order[bar] if x in common), key=_native_key)
        b = [x for x in pine_order[bar] if x in common]
        if a != b:
            ordering_mismatches += 1
            mismatches.append(Mismatch("P8", bar, "-", "ordering", a[:6], b[:6]))
    term_counts = Counter(
        e["pine_idx"] for e in py_events_mapped if e["event_type"] == "POI_TERMINAL"
    )
    dup_terminal = sum(1 for c in term_counts.values() if c > 1)
    missing_reason = sum(
        1
        for e in py_events_mapped
        if e["event_type"] == "POI_TERMINAL" and not e["terminal_reason"]
    )
    activated_bar = {
        e["pine_idx"]: int(e["bar_ms"])
        for e in py_events_mapped
        if e["event_type"] == "POI_ACTIVATED"
    }
    term_before_act = sum(
        1
        for e in py_events_mapped
        if e["event_type"] == "POI_TERMINAL"
        and (
            e["pine_idx"] not in activated_bar
            or int(e["bar_ms"]) < activated_bar[e["pine_idx"]]
        )
    )

    # ---------------- P5 ----------------
    p5_rows_compared = 0
    p5_rows_by_class: Counter[str] = Counter()
    p5_field_mismatches = 0
    p5_python_only = 0
    p5_pine_only = 0
    p5_bars_compared = 0
    py_p5: dict[int, dict[int, dict[str, str]]] = defaultdict(dict)
    for row in _rows(authority_dir / "p5_assessment_rows.ndjson.gz", through):
        rid = row["poi_record_id"]
        bar = int(row["bar_ms"])
        if rid not in py_identity or bar not in pine_p5_bars:
            continue
        idx = pine_idx_by_identity.get(py_identity[rid])
        if idx is None:
            continue
        py_p5[bar][idx] = row
    for bar in sorted(b for b in pine_p5_bars if b <= through):
        p5_bars_compared += 1
        pine_rows = pine_p5.get(bar, {})
        py_rows = py_p5.get(bar, {})
        for idx in sorted(set(py_rows) - set(pine_rows)):
            p5_python_only += 1
            mismatches.append(
                Mismatch("P5", bar, f"pine:{idx}", "python_only_row", True, None)
            )
        for idx in sorted(set(pine_rows) - set(py_rows)):
            p5_pine_only += 1
            mismatches.append(
                Mismatch("P5", bar, f"pine:{idx}", "pine_only_row", None, True)
            )
        for idx in sorted(set(py_rows) & set(pine_rows)):
            p5_rows_compared += 1
            p5_rows_by_class[
                "higher_tf_context"
                if py_rows[idx]["poi_record_id"] in promoted
                else "host_only"
            ] += 1
            a = py_rows[idx]
            c = pine_rows[idx]
            pairs = {
                "btmmValid": (a["btmm_valid"] == "1", c[5] == "1"),
                "align": (
                    ALIGNMENT_CODE[TrendAlignment(a["trend_alignment"])],
                    int(c[7]),
                ),
                "sBtmm": (int(a["score_btmm"]), int(c[8])),
                "sPoi": (int(a["score_poi"]), int(c[9])),
                "sTrend": (int(a["score_trend"]), int(c[10])),
                "sRegime": (int(a["score_regime"]), int(c[11])),
                "sMomentum": (int(a["score_momentum"]), int(c[12])),
                "sBreakout": (int(a["score_breakout"]), int(c[13])),
                "sLiquidity": (int(a["score_liquidity"]), int(c[14])),
                "sVolatility": (int(a["score_volatility"]), int(c[15])),
                "final": (int(a["final_confluence_score"]), int(c[16])),
                "permission": (
                    PERMISSION_CODE[AnalyticalPermission(a["analytical_permission"])],
                    int(c[17]),
                ),
                "lifecycle": (
                    LIFECYCLE_CODE[SignalLifecycleState(a["signal_lifecycle_state"])],
                    int(c[18]),
                ),
            }
            if a["poi_lifecycle_status"]:
                pairs["poiStatus"] = (
                    LC_CODE[PoiLifecycleStatus(a["poi_lifecycle_status"])],
                    int(c[3]),
                )
            for name, (x, y) in pairs.items():
                if x != y:
                    p5_field_mismatches += 1
                    mismatches.append(Mismatch("P5", bar, f"pine:{idx}", name, x, y))

    for m in mismatches:
        daily[_day_of(m.bar_ms) if m.bar_ms else "-"][m.stage] += 1

    mismatches.sort(key=lambda m: (m.bar_ms, _STAGE_ORDER[m.stage]))
    report = ComparisonReport(
        compared_through_bar_ms=through, level_a_bars=level_a_bars
    )
    report.scope = {
        "host_timeframe": host_timeframe,
        "level_a_in_scope_pois": len(py_identity),
        "level_a_out_of_scope_pois": dict(out_of_scope),
        "canonical_identity_timeframe": "source_timeframe",
        "level_a_host_pois_with_higher_tf_context": dict(Counter(promoted.values())),
        "pine_registry_pois": len(pine_identity),
        "pine_evaluated_pois_through": len(pine_evaluated),
    }
    report.p3 = {
        "python_only": len(python_only),
        "pine_only": len(pine_only),
        "field_mismatches": p3_field_mismatches,
        "matched": len(py_identity) - len(python_only),
    }
    promoted_pine_idx = {
        pine_idx_by_identity[py_identity[rid]]
        for rid in promoted
        if py_identity.get(rid) in pine_idx_by_identity
    }
    report.p8 = {
        "pine_events_by_poi_class": dict(
            Counter(
                "higher_tf_context" if k[1] in promoted_pine_idx else "host_only"
                for k in pine_key
            )
        ),
        "pine_events": len(pine_key),
        "python_events": len(py_key),
        "missing_in_python": len(missing),
        "extra_in_python": len(extra),
        "payload_mismatches": payload_mismatches,
        "ordering_mismatch_bars": ordering_mismatches,
        "pine_native_order_violation_bars": pine_native_order_violations,
        "python_event_priority_violation_bars": python_priority_violations,
        "duplicate_terminal": dup_terminal,
        "missing_terminal_reason": missing_reason,
        "terminal_before_activation": term_before_act,
        "python_events_on_unmatched_pois": unmatched_py_event_pois,
    }
    promoted_idx = {
        pine_idx_by_identity[py_identity[rid]]
        for rid in promoted
        if py_identity.get(rid) in pine_idx_by_identity
    }
    by_class: Counter[str] = Counter()
    for m in mismatches:
        idx_s = m.poi.split(":")[1] if m.poi.startswith("pine:") else ""
        cls = (
            "higher_tf_context"
            if idx_s.isdigit() and int(idx_s) in promoted_idx
            else "host_only"
        )
        by_class[f"{m.stage}:{cls}"] += 1
    report.scope["mismatches_by_poi_class"] = dict(by_class)
    first_by_class: dict[str, dict[str, Any]] = {}
    for m in mismatches:
        idx_s = m.poi.split(":")[1] if m.poi.startswith("pine:") else ""
        cls = (
            "higher_tf_context"
            if idx_s.isdigit() and int(idx_s) in promoted_idx
            else "host_only"
        )
        key = f"{m.stage}:{cls}"
        first_by_class.setdefault(key, m.as_dict())
    report.scope["first_divergence_by_class"] = first_by_class
    report.scope["all_mismatches"] = [m.as_dict() for m in mismatches]
    report.p5 = {
        "bars_compared": p5_bars_compared,
        "rows_compared": p5_rows_compared,
        "rows_compared_by_poi_class": dict(p5_rows_by_class),
        "python_only_rows": p5_python_only,
        "pine_only_rows": p5_pine_only,
        "field_mismatches": p5_field_mismatches,
    }
    report.daily = {k: dict(v) for k, v in sorted(daily.items())}
    report.first_divergence = mismatches[0].as_dict() if mismatches else None
    report.scope["first_mismatches"] = [m.as_dict() for m in mismatches[:15]]
    return report


#: Pine P8 emission order within one POI on one bar (see the P8EVENT block).
P8_EVENT_PRIORITY = {
    "POI_ACTIVATED": 0,
    "BTMM_VALIDATED": 1,
    "PERMISSION_ENTERED_ACTIONABLE": 2,
    "PERMISSION_LOST_ACTIONABLE": 2,
    "POI_TERMINAL": 3,
}


def _native_key(event: tuple[str, int]) -> tuple[int, int]:
    return (event[1], P8_EVENT_PRIORITY[event[0]])


def _poi_type(name: str) -> Any:
    from btmm_ai_scanner.poi.enums import PoiType

    return PoiType(name)


def main() -> int:
    import argparse

    repo = Path(__file__).resolve().parents[2]
    base = repo / "artifacts" / "rc3_aligned"
    parser = argparse.ArgumentParser()
    parser.add_argument("--capture", type=Path, default=base / "pine_m15_run1.csv")
    parser.add_argument("--authority-dir", type=Path, default=base / "authority")
    parser.add_argument("--out", type=Path, default=base / "parity_report.json")
    args = parser.parse_args()
    report = compare(args.capture, args.authority_dir)
    args.out.write_text(
        json.dumps(report.as_dict(), indent=2, default=str), encoding="utf-8"
    )
    print(json.dumps(report.as_dict(), indent=2, default=str)[:6000])
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
