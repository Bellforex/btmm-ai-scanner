"""P6→P5 transport real-data parity: the captured FXCM capture, replayed.

WHAT THIS ASSERTS
------------------
The full re-closure claim for the additive P5 transport extension, re-derived
from artifacts rather than trusted:

1. every timeframe's raw candles lock to the atomic snapshot on all five
   identity dimensions (Phase 7/8 of the re-closure campaign);
2. the OLD five transported surfaces still match the production oracle at
   this NEW anchor -- 30/30 exact -- proving the additive extension did not
   disturb P6's original semantics;
3. every one of the 26 new transport fields matches the authoritative Python
   oracle, field by field, across all six timeframes -- 156/156 exact, on
   real FXCM data;
4. the transport digest, folded from that same field-exact data.

WHY THE TRANSPORT DIGEST IS LABELLED PYTHON-DERIVED, NOT PINE==PYTHON
-------------------------------------------------------------------------
Unlike the OLD five surfaces, Pine never computes a digest fold over the 26
new fields -- the atomic twin's capture section was deliberately left
untouched (see BTRC_V1_P6_P5X_RESOURCE_ATTRIBUTION.md ownership boundary), so
there is no live Pine-side digest to compare against. The values below are
frozen as a REGRESSION FINGERPRINT of the field-exact real capture: a future
change that altered any of the 26 fields on real data would move this number,
which is what closure evidence needs it for. The field-level 156/156 is the
authoritative parity claim per se (`p6_atomic_capture_log`'s own doctrine:
"field-level comparison is authoritative, never tune to digest"); this digest
is downstream confirmation, not a second independent proof.

WHY IT SKIPS RATHER THAN FAILS WITHOUT THE CAPTURE
-----------------------------------------------------
`artifacts/` is gitignored. Skipping keeps the suite honest for a fresh clone
without weakening the claim -- the closure evidence records the values
independently in BTRC_V1_P6X_TRANSPORT_REAL_PARITY.md.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.parity_support.p5x_capture_log import ALL_FIELDS, find_capture_at
from tests.parity_support.p6_atomic_capture_log import (
    group_by_emission,
    parse_raw,
    parse_snapshot,
    raw_identity_matches,
)
from tests.parity_support.p6_real_data_replay import build_candles, replay_capture
from tests.parity_support.p6x_transport_digest import (
    global_transport_digest,
    timeframe_transport_digest,
)
from tests.parity_support.p6x_transport_replay import replay_transport_series

_REPO = Path(__file__).resolve().parents[2]
CAPTURE = _REPO / "artifacts" / "p6x_capture" / "atomic_all_raw_log.csv"

pytestmark = pytest.mark.skipif(
    not CAPTURE.exists(), reason=f"no P6X capture present: {CAPTURE.name}"
)

TIMEFRAMES: tuple[str, ...] = ("W1", "D1", "H4", "H1", "M15", "M5")

#: Frozen at re-closure. A future capture must re-derive these, never adjust
#: the test to match a new run -- a change here should be a deliberate,
#: reviewed re-closure, not a silent re-basing.
SNAPSHOT_STAMP = "2026-09-04T02:12:42.211+01:00"
CAPTURE_ID = "f2dfa1152ad06d1e05ba2f99c58dcbd0"

RAW_STAMPS: dict[str, str] = {
    "W1": "2026-09-04T02:12:44.416+01:00",
    "D1": "2026-09-04T02:12:44.280+01:00",
    "H4": "2026-09-04T02:12:42.218+01:00",
    "H1": "2026-09-04T02:12:47.013+01:00",
    "M15": "2026-09-04T02:12:42.211+01:00",
    "M5": "2026-09-04T02:12:42.226+01:00",
}

EXPECTED_ROWS: dict[str, int] = {
    "W1": 1250,
    "D1": 1250,
    "H4": 1250,
    "H1": 1250,
    "M15": 1799,
    "M5": 1250,
}

GLOBAL_TRANSPORT_H1 = 587324251
GLOBAL_TRANSPORT_H2 = 795923623

TIMEFRAME_TRANSPORT_DIGESTS: dict[str, tuple[int, int]] = {
    "W1": (992954022, 143829031),
    "D1": (893013043, 346300067),
    "H4": (978144049, 336125251),
    "H1": (918084312, 633265513),
    "M15": (57476645, 768475044),
    "M5": (774659550, 357379521),
}


@pytest.fixture(scope="module")
def raw_text() -> str:
    return CAPTURE.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def snapshot(raw_text: str):
    for stamp, records in group_by_emission(raw_text):
        if stamp != SNAPSHOT_STAMP:
            continue
        block = "\n".join(records)
        if "P6META|" in block and "P6SNAP_END|" in block:
            return parse_snapshot(block)
    raise AssertionError("target snapshot not found in capture")


@pytest.fixture(scope="module")
def p5x_capture(raw_text: str):
    return find_capture_at(raw_text, SNAPSHOT_STAMP)


@pytest.fixture(scope="module")
def raw_captures(raw_text: str) -> dict[str, object]:
    out: dict[str, object] = {}
    for tf, stamp in RAW_STAMPS.items():
        for group_stamp, records in group_by_emission(raw_text):
            if group_stamp != stamp:
                continue
            block = "\n".join(records)
            if "P6RAW_SUMMARY|" in block:
                raw = parse_raw(block)
                if raw.timeframe == tf:
                    out[tf] = raw
    assert set(out) == set(TIMEFRAMES), out.keys()
    return out


def test_capture_id_matches(snapshot) -> None:
    assert snapshot.capture_id == CAPTURE_ID


def test_snapshot_is_fxcm(snapshot) -> None:
    """`parse_snapshot` already rejects a non-FXCM feed by default (this
    fixture would have raised), so this restates the assertion explicitly
    rather than relying on that side effect."""
    assert snapshot.meta.feed == "FX:XAUUSD"


@pytest.mark.parametrize("tf", TIMEFRAMES)
def test_row_counts(snapshot, tf: str) -> None:
    assert snapshot.timeframes[tf].semantic_rows == EXPECTED_ROWS[tf]


@pytest.mark.parametrize("tf", TIMEFRAMES)
def test_6_of_6_raw_input_identity(snapshot, raw_captures, tf: str) -> None:
    result = raw_identity_matches(snapshot.timeframes[tf], raw_captures[tf])
    assert result.matched, result.describe()


@pytest.mark.parametrize("tf", TIMEFRAMES)
def test_old_30_of_30_at_new_anchor(snapshot, raw_captures, tf: str) -> None:
    """The additive extension did not disturb the closed P6 surfaces."""
    replay = replay_capture({tf: raw_captures[tf]})[tf]
    pine = snapshot.timeframes[tf]
    for surface in ("SWINGS", "EQUAL", "DISP", "P2_TRANS", "P2_STATE"):
        assert replay.surfaces[surface] == pine.surfaces[surface], surface


@pytest.mark.parametrize("tf", TIMEFRAMES)
def test_26_field_real_differential(raw_captures, p5x_capture, tf: str) -> None:
    candles = build_candles(tf, raw_captures[tf].bars)
    transport = replay_transport_series(candles, timeframe=tf, terminals=1)[0]
    python_record = transport.record.as_dict()
    pine_record = p5x_capture.timeframes[tf]

    mismatches = []
    for field in ALL_FIELDS:
        pine_value = pine_record.field(field)
        python_value = python_record[field]
        if isinstance(pine_value, float) and isinstance(python_value, float):
            ok = abs(pine_value - python_value) < 1e-6
        else:
            ok = pine_value == python_value
        if not ok:
            mismatches.append((field, pine_value, python_value))
    assert mismatches == [], mismatches


def test_the_26_field_comparison_denominator_is_156(raw_captures, p5x_capture) -> None:
    """26 fields x 6 timeframes, none excluded -- the contract marks no field
    as timeframe-inapplicable."""
    total = 0
    for tf in TIMEFRAMES:
        candles = build_candles(tf, raw_captures[tf].bars)
        transport = replay_transport_series(candles, timeframe=tf, terminals=1)[0]
        total += len(transport.record.as_dict())
    assert total == len(ALL_FIELDS) * len(TIMEFRAMES) == 156


@pytest.mark.parametrize("tf", TIMEFRAMES)
def test_transport_digest_is_a_stable_fingerprint(raw_captures, tf: str) -> None:
    candles = build_candles(tf, raw_captures[tf].bars)
    transport = replay_transport_series(candles, timeframe=tf, terminals=1)[0]
    h1, h2 = timeframe_transport_digest(tf, transport.record.as_dict())
    assert (h1, h2) == TIMEFRAME_TRANSPORT_DIGESTS[tf]


def test_global_transport_digest(raw_captures) -> None:
    per_tf = {}
    for tf in TIMEFRAMES:
        candles = build_candles(tf, raw_captures[tf].bars)
        transport = replay_transport_series(candles, timeframe=tf, terminals=1)[0]
        per_tf[tf] = transport.record.as_dict()
    h1, h2 = global_transport_digest(per_tf)
    assert (h1, h2) == (GLOBAL_TRANSPORT_H1, GLOBAL_TRANSPORT_H2)
