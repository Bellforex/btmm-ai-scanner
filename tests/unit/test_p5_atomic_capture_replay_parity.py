"""P5 real, wire-normalized parity: the captured FXCM P5 ATOMIC PARITY log,
replayed in Python and compared field-by-field against Pine's own decisions.

WHAT THIS ASSERTS
------------------
The whole P5 wire-normalized parity claim, re-derived from a real capture
rather than trusted:

1. the capture parses strictly (`p5_atomic_capture_log`) and every `P5WIRE`
   bar has at least one matching `P5EVAL` bar (the join key the whole
   replay depends on);
2. for every bar that has a `P5WIRE` line, `p5_wire_normalized_replay.
   compute_bar_level` -- built from ONLY that wire, using the SAME
   already-proven-sufficient T1/T2/T3/T5-global pine-model functions this
   campaign already differential-tested against production -- reproduces
   EVERY `P5EVAL` row logged for that bar's bar-level fields exactly;
3. for every `P5EVAL` row, `compute_poi_level` -- built from ONLY that row's
   own logged fields (POI/BTMM state + weights, no wire needed for this
   layer) -- reproduces that row's own POI-level aggregator fields exactly
   (alignment, all eight component scores, the weighted final, permission,
   lifecycle).

WHY IT SKIPS RATHER THAN FAILS WITHOUT THE CAPTURE
---------------------------------------------------
`artifacts/` is gitignored, so a fresh clone has no capture. Skipping keeps
the suite honest for someone who has not taken one; it does not weaken the
claim, because the closure evidence records the real counts and the (empty)
mismatch list independently.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.parity_support.p5_atomic_capture_log import (
    P5AtomicCaptureError,
    parse_p5_atomic_capture,
)
from tests.parity_support.p5_digest import ROW_FIELDS, capture_digest
from tests.parity_support.p5_wire_normalized_replay import (
    BAR_LEVEL_EVAL_FIELDS,
    POI_LEVEL_EVAL_FIELDS,
    compute_bar_level,
    compute_poi_level,
)

_REPO = Path(__file__).resolve().parents[2]
CAPTURE = _REPO / "artifacts" / "p5_capture" / "p5_atomic_raw_log.csv"

pytestmark = pytest.mark.skipif(
    not CAPTURE.exists(), reason=f"no P5 ATOMIC capture present: {CAPTURE.name}"
)


@pytest.fixture(scope="module")
def capture():
    text = CAPTURE.read_text(encoding="utf-8", errors="strict")
    return parse_p5_atomic_capture(text)


def test_capture_parses_and_is_non_vacuous(capture):
    assert len(capture.wire_by_bar) > 0
    assert len(capture.eval_by_bar) > 0
    total_rows = sum(len(rows) for rows in capture.eval_by_bar.values())
    assert total_rows > 1000, "expected a substantial real capture, not a token sample"


def test_every_wire_bar_has_a_matching_eval_bar(capture):
    missing = [bar for bar in capture.wire_by_bar if bar not in capture.eval_by_bar]
    assert missing == []


def test_malformed_line_is_rejected():
    with pytest.raises(P5AtomicCaptureError):
        parse_p5_atomic_capture("P5EVAL|bar=1|poiIdx=nope\n")


def test_bar_level_replay_matches_every_eval_row(capture):
    """Every P5EVAL row sharing a bar carries an IDENTICAL copy of the
    bar-level fields (computed once per bar in the Pine source before the
    per-POI loop runs) -- so this checks the replay against every row, not
    just one representative, which would silently miss a per-row corruption
    of an otherwise-constant field."""
    mismatches: list[str] = []
    bars_checked = 0
    rows_checked = 0
    for bar, wire in capture.wire_by_bar.items():
        rows = capture.eval_by_bar.get(bar, [])
        if not rows:
            continue
        bars_checked += 1
        replayed = compute_bar_level(wire)
        for row in rows:
            rows_checked += 1
            for eval_field, attr in BAR_LEVEL_EVAL_FIELDS:
                expected = row.field(eval_field)
                actual = getattr(replayed, attr)
                if expected != actual:
                    mismatches.append(
                        f"bar={bar} poiIdx={row.poi_idx} {eval_field}: "
                        f"pine={expected} python={actual}"
                    )

    assert bars_checked >= 100, f"expected 100+ real bars, got {bars_checked}"
    assert rows_checked >= 1000, f"expected 1000+ real rows, got {rows_checked}"
    assert mismatches == []


def test_poi_level_replay_matches_every_eval_row(capture):
    mismatches: list[str] = []
    rows_checked = 0
    for bar, rows in capture.eval_by_bar.items():
        for row in rows:
            rows_checked += 1
            replayed = compute_poi_level(row)
            for eval_field, attr in POI_LEVEL_EVAL_FIELDS:
                expected = row.field(eval_field)
                actual = getattr(replayed, attr)
                if expected != actual:
                    mismatches.append(
                        f"bar={bar} poiIdx={row.poi_idx} {eval_field}: "
                        f"pine={expected} python={actual}"
                    )

    assert rows_checked >= 1000, f"expected 1000+ real rows, got {rows_checked}"
    assert mismatches == []


def test_full_row_replay_matches_end_to_end(capture):
    """Both layers together, on every row: the same claim the closure
    document reports as one number, computed here as two independent passes
    rather than trusted from the two tests above alone."""
    total = 0
    mismatched_rows = 0
    for bar, wire in capture.wire_by_bar.items():
        rows = capture.eval_by_bar.get(bar, [])
        bar_level = compute_bar_level(wire)
        for row in rows:
            total += 1
            poi_level = compute_poi_level(row)
            ok = all(
                row.field(f) == getattr(bar_level, a) for f, a in BAR_LEVEL_EVAL_FIELDS
            ) and all(
                row.field(f) == getattr(poi_level, a) for f, a in POI_LEVEL_EVAL_FIELDS
            )
            if not ok:
                mismatched_rows += 1

    assert total >= 1000
    assert mismatched_rows == 0


def _pine_row_dict(row) -> dict[str, int]:
    return {name: (row.bar if name == "bar" else row.field(name)) for name in ROW_FIELDS}


def _replayed_row_dict(bar, row) -> dict[str, int]:
    bar_level = compute_bar_level(bar)
    poi_level = compute_poi_level(row)
    out: dict[str, int] = {"bar": row.bar, "poiIdx": row.poi_idx}
    for eval_field, attr in BAR_LEVEL_EVAL_FIELDS:
        out[eval_field] = getattr(bar_level, attr)
    for eval_field, attr in POI_LEVEL_EVAL_FIELDS:
        out[eval_field] = getattr(poi_level, attr)
    return out


def compute_both_digests(capture) -> tuple[tuple[int, int], tuple[int, int]]:
    """(pine_digest, python_digest) over every row, ordered by (bar, poiIdx)
    so both sides fold in the identical, deterministic order regardless of
    the capture file's own emission order or any dict iteration order."""
    ordered: list[tuple[int, int, object, object]] = []
    for bar_ms, wire in capture.wire_by_bar.items():
        for row in capture.eval_by_bar.get(bar_ms, []):
            ordered.append((bar_ms, row.poi_idx, wire, row))
    ordered.sort(key=lambda t: (t[0], t[1]))

    pine_rows = [_pine_row_dict(row) for _, _, _wire, row in ordered]
    python_rows = [_replayed_row_dict(wire, row) for _, _, wire, row in ordered]
    return capture_digest(pine_rows), capture_digest(python_rows)


def test_global_digest_matches(capture):
    pine_digest, python_digest = compute_both_digests(capture)
    assert pine_digest == python_digest
    h1, h2 = pine_digest
    assert h1 != 0 and h2 != 0, "a degenerate all-zero digest would hide a real bug"
