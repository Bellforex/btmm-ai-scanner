"""The atomic twin must be P6 DEV plus instrumentation, and must hash like Python.

TWO THINGS GUARDED HERE
-----------------------
**1. Semantic equivalence.** A parity capture is only evidence about P6 DEV if the
script that produced it computes what P6 DEV computes. The atomic file is
therefore required to be DEV verbatim -- title aside -- with an appended section,
and the appended section is required not to touch the projection. The design that
makes this cheap to guarantee is that the surface digests are folded from the
values the projection ALREADY returns, so `f_p6TfProjection` needs no change at
all.

**2. Hash correspondence.** The comparison is Pine digests against Python digests.
If the two folded their fields in different orders, or encoded a price where the
other encoded a plain integer, every timeframe would mismatch and the ownership
hunt would start in the wrong place. So the Pine fold order is parsed out of the
source and compared against the Python contract field by field, rather than both
being trusted to have been written correctly.

WHAT THE ATOMIC SECTION IS ALLOWED TO ADD
------------------------------------------
Log emission, its own confirmed-bar accumulation for the input digest, hash
helpers, and the raw-capture selector. It may not touch the projection, may not
add a plot (DEV already sits at 63 of Pine's 64), and may not introduce a second
definition of anything semantic.
"""

from __future__ import annotations

import importlib.util
import re
import sys
from pathlib import Path
from typing import Any

_REPO = Path(__file__).resolve().parents[2]
P6_DEV = _REPO / "tradingview" / "btmm_poi_btrc_scanner_p6_dev.pine"
P6_ATOMIC = _REPO / "tradingview" / "btmm_poi_btrc_scanner_p6_atomic_parity.pine"

BANNER = "// P6 ATOMIC PARITY — capture instrumentation"


def _load(name: str, relpath: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, _REPO / relpath)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


DIG = _load("_p6_digest_atomic", "tests/parity_support/p6_digest.py")


def _atomic() -> str:
    return P6_ATOMIC.read_text(encoding="utf-8")


def _section() -> str:
    text = _atomic()
    assert BANNER in text, "atomic instrumentation banner missing"
    return text[text.index(BANNER) :]


# ---------------------------------------------------------------------------
# Semantic equivalence with DEV
# ---------------------------------------------------------------------------


def test_the_atomic_file_is_dev_verbatim_plus_a_section() -> None:
    dev = P6_DEV.read_text(encoding="utf-8")
    expected = dev.replace("[P6 DEV]", "[P6 ATOMIC PARITY]", 1)
    assert _atomic().startswith(expected), (
        "the atomic twin no longer contains P6 DEV verbatim; a capture taken "
        "with it would not be evidence about DEV"
    )


def test_only_the_title_differs_in_the_shared_region() -> None:
    dev = P6_DEV.read_text(encoding="utf-8").split("\n")
    atomic = _atomic().split("\n")[: len(dev)]
    differing = [(i + 1, a, b) for i, (a, b) in enumerate(zip(dev, atomic, strict=False)) if a != b]
    assert len(differing) == 1, differing
    assert "indicator(" in differing[0][1]


def test_the_section_does_not_redefine_the_projection() -> None:
    section = _section()
    assert "f_p6TfProjection() =>" not in section
    for closed in ("f_detectSwings(array", "f_p2StructureWalk(array", "f_advancePivotFrontier(array"):
        assert closed not in section, closed


def test_the_section_adds_no_plot() -> None:
    """P6 DEV already sits at 63 of Pine's 64 plot calls."""
    section = _section()
    assert not re.search(r"^plot\(", section, re.M)
    total = len(re.findall(r"^plot\(", _atomic(), re.M)) + len(
        re.findall(r"^plotshape\(", _atomic(), re.M)
    )
    assert total <= 64, total


def test_the_request_count_stays_within_pines_limit() -> None:
    """Six projection contexts plus six capture contexts."""
    calls = re.findall(r"request\.security\(", _atomic())
    assert len(calls) == 12, len(calls)


def test_the_capture_contexts_use_the_same_envelope() -> None:
    """A capture that ran over a different envelope would hash a different set
    of bars from the one the projection consumed."""
    sites = [
        line
        for line in _atomic().split("\n")
        if "f_p6AtomicCapture(" in line and "request.security(" in line
    ]
    assert len(sites) == 6, len(sites)
    for call in sites:
        assert "calc_bars_count = C_P6_REQUEST_CALC_BARS" in call, call


def test_the_capture_hashes_confirmed_bars_only() -> None:
    """Mirrors the projection's own gate. Hashing the forming bar would make the
    digest move on every tick while the semantics stood still."""
    section = _section()
    body = section[section.index("f_p6AtomicCapture(") : section.index("string P6A_CAPTURE_TF")]
    lines = body.split("\n")
    gate = next(
        i for i, line in enumerate(lines) if line.strip() == "if barstate.isconfirmed"
    )
    gate_indent = len(lines[gate]) - len(lines[gate].lstrip())
    # The emission block starts here; assignments after it are NOT confirmed-gated
    # and only the once-guard is permitted among them.
    emit = next(i for i, line in enumerate(lines) if "if emitRaw and barstate.islast" in line)
    for index, line in enumerate(lines):
        if ":=" not in line or line.strip().startswith("//"):
            continue
        indent = len(line) - len(line.lstrip())
        if index > emit:
            assert line.strip() == "kEmitted := true", (
                f"only the emission once-guard may be assigned outside the "
                f"confirmed gate, found: {line.strip()}"
            )
            continue
        assert index > gate and indent > gate_indent, line.strip()


def test_no_strategy_or_order_calls_were_introduced() -> None:
    """Checked against code only: the word "order" appears legitimately in the
    section's prose about field ordering."""
    code = "\n".join(
        line
        for line in _section().split("\n")
        if not line.strip().startswith("//")
    )
    for forbidden in (
        "strategy.",
        "alert(",
        "order.",
        "label.new",
        "line.new",
        "box.new",
    ):
        assert forbidden not in code, forbidden


# ---------------------------------------------------------------------------
# Hash correspondence with the Python contract
# ---------------------------------------------------------------------------


def test_the_moduli_and_bases_match_the_python_contract() -> None:
    section = _section()
    for name, value in (
        ("P6A_MOD1", DIG.MOD1),
        ("P6A_MOD2", DIG.MOD2),
        ("P6A_BASE1", DIG.BASE1),
        ("P6A_BASE2", DIG.BASE2),
    ):
        assert re.search(rf"int {name}\s+= {value}\b", section), name


def test_the_canonical_encoding_matches() -> None:
    """`na -> 0`, otherwise `2v+2` / `-2v+1`, exactly as `encode_int`."""
    section = _section()
    assert "na(v) ? 0 : (v >= 0 ? 2 * v + 2 : -2 * v + 1)" in section
    assert DIG.encode_int(None) == 0
    assert DIG.encode_int(3) == 8
    assert DIG.encode_int(-3) == 7


def test_the_accumulation_step_matches() -> None:
    section = _section()
    assert "(acc * base + (v % mod)) % mod" in section


def test_the_ratio_scale_matches() -> None:
    """The displacement ratio has no tick to normalise against, so both sides
    must agree on the fixed scale instead."""
    section = _section()
    assert "int(math.round(r * 1000000))" in section
    assert DIG.RATIO_SCALE == 1000000


#: Pine fold-order, parsed from the source; compared against the Python contract.
_PINE_SURFACE_FN = {
    "SWINGS": "f_p6aSwings",
    "EQUAL": "f_p6aEqual",
    "DISP": "f_p6aDisp",
    "P2_TRANS": "f_p6aTrans",
    "P2_STATE": "f_p6aState",
}

_ENCODER_FOR_KIND = {
    "INTEGER": "f_p6aEnc",
    "PRICE": "f_p6aEncPrice",
    "RATIO": "f_p6aEncRatio",
}


def _pine_fold_encoders(function: str) -> list[str]:
    """The encoder used at each fold step of a Pine surface function."""
    section = _section()
    start = section.index(f"{function}(")
    body = section[start : section.index("\n\n", start)]
    return re.findall(r"f_p6aStep\([^,]+,\s*(f_p6aEnc\w*)\(", body)


def test_every_surface_folds_its_fields_in_the_python_order() -> None:
    """The comparison is Pine digests against Python digests. A different fold
    order or a price encoded as a plain integer would mismatch every timeframe
    and send the ownership hunt to the wrong place."""
    for surface, function in _PINE_SURFACE_FN.items():
        expected = [
            _ENCODER_FOR_KIND[kind] for _name, kind in DIG.SURFACE_FIELDS[surface]
        ]
        assert _pine_fold_encoders(function) == expected, (surface, function)


def test_the_combined_digest_leads_with_the_timeframe_code() -> None:
    """Python's `timeframe_digest` hashes the TF code as the first record."""
    section = _section()
    combined = section[section.index("f_p6aTfCombined(") :]
    combined = combined[: combined.index("\n\n")]
    first_step = re.search(r"f_p6aStep\(a, (\w+)\(tfCode\)", combined)
    assert first_step and first_step.group(1) == "f_p6aEnc"


def test_the_combined_digest_folds_the_five_surfaces_in_order() -> None:
    section = _section()
    combined = section[section.index("f_p6aTfCombined(") :]
    combined = combined[: combined.index("\n\n")]
    folded = re.findall(r"f_p6aStep\(a, (f_p6a(?:Swings|Equal|Disp|Trans|State))\(", combined)
    assert folded == [_PINE_SURFACE_FN[s] for s in DIG.SURFACE_ORDER], folded


def test_the_input_record_folds_the_frozen_six_fields() -> None:
    """`encode_input_bar` order: time, open, high, low, close, time_close."""
    section = _section()
    body = section[section.index("f_p6AtomicCapture(") : section.index("string P6A_CAPTURE_TF")]
    fields = re.findall(r"f_p6aStep\(r1, f_p6aEnc\w*\((\w+)\)", body)
    assert fields == ["time", "open", "high", "low", "close", "time_close"], fields


# ---------------------------------------------------------------------------
# The capture protocol itself
# ---------------------------------------------------------------------------


def test_raw_capture_is_one_timeframe_per_run() -> None:
    """Six timeframes at once would be ~7500 log rows, well past the 2501 the
    feasibility probe actually demonstrated."""
    section = _section()
    assert 'input.string("NONE", "Atomic raw capture timeframe"' in section
    for timeframe in ("W1", "D1", "H4", "H1", "M15", "M5"):
        assert f'P6A_CAPTURE_TF == "{timeframe}"' in section, timeframe


def test_the_snapshot_publishes_all_five_identity_dimensions() -> None:
    """Rows, first, last and both digests -- the raw capture is accepted on all
    five, never on the digest alone."""
    section = _section()
    for token in ("rows=", "first=", "last=", "ih1=", "ih2="):
        assert token in section, token


def test_the_snapshot_covers_all_six_timeframes_in_one_execution() -> None:
    section = _section()
    emitted = re.findall(r'f_p6aTfRow\("(\w+)"', section)
    assert emitted == ["W1", "D1", "H4", "H1", "M15", "M5"], emitted
    # Anchored at the live edge with a once-guard, not at the last historical
    # bar: measured, the M5 context had confirmed only 1248 of 1250 there.
    assert "if barstate.islast and not p6aSnapshotDone" in section
    assert "var bool p6aSnapshotDone = false" in section


def test_the_snapshot_records_the_provider() -> None:
    """Every capture must be attributable to FXCM; a silent feed switch is a
    failure mode this campaign has already hit once."""
    section = _section()
    assert "provider=" in section
    assert "syminfo.prefix" in section


def test_the_raw_summary_carries_its_own_identity() -> None:
    section = _section()
    summary = section[section.index("P6RAW_SUMMARY") :]
    summary = summary[: summary.index("\n")]
    for token in ("rows=", "first=", "last=", "h1=", "h2=", "provider="):
        assert token in summary, token


def test_the_sources_are_lf_only() -> None:
    for path in (P6_DEV, P6_ATOMIC):
        assert b"\r\n" not in path.read_bytes(), path.name
