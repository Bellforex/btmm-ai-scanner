"""RC3 FVG pipeline audit (Phases 9-11): detection -> registration ->
freshness -> termination -> grouping -> selection -> drawing.

Test/validation tooling only. Inputs are one Pine PARITY run's P3LIFE registry
(``artifacts/rc3_aligned/pine_m15_run1.csv``) and the same-session OHLC export
of the executed host window (proven identical by RUNMETA). Stage E uses the
committed P7-Z presentation model (``p7z_zone_model.build_visual_groups_fast``),
whose equivalence to the Pine grouping/selection code is already locked by
tests. Drawing (stage F/G) is checked live separately.
"""

from __future__ import annotations

import json
import re
from collections import Counter
from decimal import Decimal
from pathlib import Path
from typing import Any

from btmm_ai_scanner.config.enums import Timeframe
from btmm_ai_scanner.poi.configuration import PoiConfiguration
from btmm_ai_scanner.poi.fair_value_gaps import detect_fair_value_gaps
from tests.parity_support.p7z_zone_model import (
    FVG_TYPES,
    PoiGeometry,
    build_visual_groups_fast,
)
from tests.parity_support.rc3_aligned_capture import (
    _load_export,
    _select,
    parse_runmeta,
)

_P3 = re.compile(r"P3LIFE\|([^\"\n]*)")
_CODE = {"BUY_FAIR_VALUE_GAP": 3, "SELL_FAIR_VALUE_GAP": 4}


def _kv(blob: str) -> dict[str, str]:
    return dict(p.split("=", 1) for p in blob.split("|") if "=" in p)


def audit(
    capture: Path, export_dir: Path, *, capacity: int = 8, period: str = "15"
) -> dict[str, Any]:
    meta = parse_runmeta(capture)
    host = _select(
        _load_export(
            export_dir / "ohlc_m15.csv",
            Timeframe.M15,
            export_dir / "_normalized" / "m15.csv",
        ),
        meta.host,
        "host",
    )
    last_close = float(host[-1].close)
    last_ms = int(host[-1].availability_time_utc.timestamp() * 1000)

    # A. detection over exactly the executed window
    detected = detect_fair_value_gaps(
        host, PoiConfiguration(minimum_price_tick=Decimal("0.01"))
    )
    det_keys = {
        (
            _CODE[c.poi_type.value],
            int(c.candidate_event_time_utc.timestamp() * 1000),
            int(c.availability_time_utc.timestamp() * 1000),
            f"{c.zone_top:.2f}",
            f"{c.zone_bottom:.2f}",
        )
        for c in detected
    }

    rows = [
        _kv(b)
        for b in _P3.findall(capture.read_text(encoding="utf-8", errors="replace"))
    ]
    geometry: dict[int, PoiGeometry] = {}
    fresh: set[int] = set()
    reg_fvg_keys: set[tuple[Any, ...]] = set()
    term = Counter()
    for r in rows:
        idx, typ = int(r["poiIdx"]), int(r["type"])
        geometry[idx] = PoiGeometry(
            idx,
            typ,
            1 if int(r["dir"]) > 0 else -1,
            float(r["top"]),
            float(r["bottom"]),
            int(r["availTime"]),
            int(r["tier"]),
        )
        if r["freshActive"] == "true":
            fresh.add(idx)
        if typ in FVG_TYPES:
            reg_fvg_keys.add(
                (
                    typ,
                    int(r["srcTime"]),
                    int(r["availTime"]),
                    f"{Decimal(r['top']):.2f}",
                    f"{Decimal(r['bottom']):.2f}",
                )
            )
            if r["freshActive"] != "true":
                term[
                    "MITIGATED"
                    if r["termReason"] == "1"
                    else "INVALIDATED"
                    if r["termReason"] == "2"
                    else "OTHER"
                ] += 1

    fvg_idx = [i for i, g in geometry.items() if g.poi_type in FVG_TYPES]
    fresh_fvg = [i for i in fvg_idx if i in fresh]

    all_groups = build_visual_groups_fast(
        sorted(fresh), geometry, last_close, 10**9, period
    )
    shown = build_visual_groups_fast(
        sorted(fresh), geometry, last_close, capacity, period
    )
    fvg_groups = [
        g for g in all_groups if geometry[g["members"][0]].poi_type in FVG_TYPES
    ]
    shown_ids = {tuple(g["members"]) for g in shown}
    omitted_fvg = [g for g in fvg_groups if tuple(g["members"]) not in shown_ids]
    shown_fvg = [g for g in shown if geometry[g["members"][0]].poi_type in FVG_TYPES]

    def _row(g: dict[str, Any], rank: int) -> dict[str, Any]:
        first = geometry[g["members"][0]]
        return {
            "rank_by_distance": rank,
            "type": "BUY_FVG" if first.poi_type == 3 else "SELL_FVG",
            "members": len(g["members"]),
            "distance": round(g["distance"], 2),
            "age_hours": round(
                (last_ms - min(geometry[m].avail_time_ms for m in g["members"]))
                / 3.6e6,
                1,
            ),
            "why_omitted": "display cap (rank > capacity)",
        }

    rank = {tuple(g["members"]): i + 1 for i, g in enumerate(all_groups)}
    family_share = Counter(
        "FVG" if geometry[g["members"][0]].poi_type in FVG_TYPES else "OTHER"
        for g in shown
    )
    return {
        "window": {
            "host_first_ms": meta.host.first_ms,
            "host_last_ms": meta.host.last_ms,
            "bars": len(host),
            "close": last_close,
        },
        "A_detected_by_python": len(detected),
        "A_detected_buy": sum(
            1 for c in detected if c.poi_type.value == "BUY_FAIR_VALUE_GAP"
        ),
        "A_detected_sell": sum(
            1 for c in detected if c.poi_type.value == "SELL_FAIR_VALUE_GAP"
        ),
        "B_registered_by_pine": len(fvg_idx),
        "detection_identity_python_only": len(det_keys - reg_fvg_keys),
        "detection_identity_pine_only": len(reg_fvg_keys - det_keys),
        "C_terminal": dict(term),
        "C_fresh": len(fresh_fvg),
        "D_fresh_fvg_groups": len(fvg_groups),
        "D_members_folded_into_groups": len(fresh_fvg) - len(fvg_groups),
        "D_fresh_fvg_lost_in_grouping": len(fresh_fvg)
        - sum(len(g["members"]) for g in fvg_groups),
        "all_fresh_groups": len(all_groups),
        "E_fvg_groups_selected": len(shown_fvg),
        "E_fvg_groups_omitted_by_cap": len(omitted_fvg),
        "E_selected_family_share": dict(family_share),
        "E_omitted_fvg_detail": [
            _row(g, rank[tuple(g["members"])]) for g in omitted_fvg
        ],
        "E_nearest_fvg_group_rank": min(
            (rank[tuple(g["members"])] for g in fvg_groups), default=None
        ),
    }


def main() -> int:
    repo = Path(__file__).resolve().parents[2]
    base = repo / "artifacts" / "rc3_aligned"
    report = audit(base / "pine_m15_run1.csv", base)
    out = repo / "artifacts" / "rc3_poi_quality" / "fvg_pipeline_audit_m15.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(
        json.dumps(
            {k: v for k, v in report.items() if k != "E_omitted_fvg_detail"}, indent=1
        )
    )
    print("omitted FVG groups (first 12):")
    for row in report["E_omitted_fvg_detail"][:12]:
        print("  ", row)
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
