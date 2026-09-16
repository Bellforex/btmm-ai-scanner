"""Author decisions 3 and 4 in the aligned Python <-> Pine comparator.

3. Canonical P3 identity keeps the SOURCE timeframe. A raised
   ``effective_timeframe`` is derived higher-timeframe context, never a P3
   identity or field divergence.
4. Pine's native P8 order (registry index, then event priority) is
   authoritative. Level A's own record numbering is incidental.
"""

from __future__ import annotations

import gzip
import json
from pathlib import Path

from tests.parity_support.rc3_aligned_compare import compare
from tests.unit.test_rc3_aligned_capture import _BAR, _authority, _pine_capture


def _rewrite(path: Path, rows: list[dict]) -> None:
    with gzip.open(path, "wt", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row) + "\n")


def _read(path: Path) -> list[dict]:
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle]


def _append_capture(path: Path, lines: list[str]) -> None:
    text = path.read_text(encoding="utf-8")
    path.write_text(
        text + "".join(f'\n2026-01-01,"{x}"' for x in lines), encoding="utf-8"
    )


def test_higher_tf_context_is_not_a_p3_identity_divergence(tmp_path: Path) -> None:
    authority = _authority(tmp_path)
    p3 = authority / "p3_registry_rows.ndjson.gz"
    rows = _read(p3)
    rows[0]["effective_timeframe"] = "H4"  # raised by the cross-TF merge
    _rewrite(p3, rows)
    report = compare(_pine_capture(tmp_path), authority)
    assert report.p3 == {
        "python_only": 0,
        "pine_only": 0,
        "field_mismatches": 0,
        "matched": 1,
    }
    assert report.scope["canonical_identity_timeframe"] == "source_timeframe"
    assert report.scope["level_a_host_pois_with_higher_tf_context"] == {"H4": 1}
    assert report.p5["rows_compared_by_poi_class"] == {"higher_tf_context": 1}
    assert report.first_divergence is None


def test_a_non_host_source_timeframe_is_still_out_of_scope(tmp_path: Path) -> None:
    authority = _authority(tmp_path)
    p3 = authority / "p3_registry_rows.ndjson.gz"
    rows = _read(p3)
    rows[0]["source_timeframe"] = "H4"
    _rewrite(p3, rows)
    report = compare(_pine_capture(tmp_path), authority)
    assert report.scope["level_a_out_of_scope_pois"] == {"timeframe:H4": 1}
    assert report.p3["matched"] == 0


def _two_poi_case(tmp_path: Path, pine_order: list[tuple[str, int]]) -> Path:
    """Level A numbers the second Pine POI FIRST (incidental numbering)."""
    authority = _authority(tmp_path)
    p3 = authority / "p3_registry_rows.ndjson.gz"
    first = _read(p3)[0]
    second = {
        **first,
        "poi_record_id": "00000000-0000-7000-8000-000000000002",
        "zone_top": "105.5",
        "zone_bottom": "104.25",
    }
    _rewrite(p3, [second, first])
    p8 = authority / "p8_event_rows.ndjson.gz"
    event = _read(p8)[0]
    _rewrite(
        p8,
        [
            {**event, "poi_record_id": second["poi_record_id"], "sequence_in_bar": "0"},
            {**event, "poi_record_id": first["poi_record_id"], "sequence_in_bar": "1"},
        ],
    )
    capture = _pine_capture(tmp_path)
    text = capture.read_text(encoding="utf-8")
    src_line = next(x for x in text.splitlines() if "P3LIFE" in x)
    p3life = src_line.split(",", 1)[1].strip('"')
    second_p3 = p3life.replace("poiIdx=0", "poiIdx=1").replace(
        "top=101.5|bottom=99.25", "top=105.5|bottom=104.25"
    )
    lines = [x for x in text.splitlines() if "P8EVENT" not in x]
    capture.write_text("\n".join(lines), encoding="utf-8")
    events = [
        f"P8EVENT|type={etype}|bar={_BAR}|poiIdx={idx}|poiDir=BULL|poiTier=1"
        "|btmmValid=false|permission=4|lifecycle=1"
        for etype, idx in pine_order
    ]
    _append_capture(capture, [second_p3, *events])
    return capture


def test_incidental_level_a_numbering_is_not_an_ordering_divergence(
    tmp_path: Path,
) -> None:
    capture = _two_poi_case(tmp_path, [("POI_ACTIVATED", 0), ("POI_ACTIVATED", 1)])
    report = compare(capture, tmp_path / "authority")
    assert report.p3["matched"] == 2
    assert report.p8["missing_in_python"] == 0 and report.p8["extra_in_python"] == 0
    assert report.p8["ordering_mismatch_bars"] == 0
    assert report.p8["pine_native_order_violation_bars"] == 0


def test_pine_log_out_of_native_order_is_reported(tmp_path: Path) -> None:
    capture = _two_poi_case(tmp_path, [("POI_ACTIVATED", 1), ("POI_ACTIVATED", 0)])
    report = compare(capture, tmp_path / "authority")
    assert report.p8["pine_native_order_violation_bars"] == 1


def test_python_priority_inversion_within_one_poi_is_reported(tmp_path: Path) -> None:
    authority = _authority(tmp_path)
    p8 = authority / "p8_event_rows.ndjson.gz"
    activated = _read(p8)[0]
    terminal = {
        **activated,
        "event_type": "POI_TERMINAL",
        "terminal_reason": "MITIGATED",
        "sequence_in_bar": "0",
    }
    _rewrite(p8, [terminal, {**activated, "sequence_in_bar": "1"}])
    report = compare(_pine_capture(tmp_path), authority)
    assert report.p8["python_event_priority_violation_bars"] == 1
