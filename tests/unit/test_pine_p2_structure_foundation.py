"""Source guards for the P2-I1 declarations and the P2-I2 swing adapter.

Pine cannot be executed locally, so these inspect the production source. They
assert two different kinds of thing:

1. **What must be present** — the structure codes, the record declarations, and
   an adapter that derives every field from canonical P1 state.
2. **What must NOT be present yet** — relationship classification, bootstrap,
   BOS, CHOCH, protected/weak mutation. I1/I2 are declarations plus adapter
   only; anything else would be unreviewed behaviour.

The second group matters more. It is easy to "just add" the label comparison
while the codes are fresh, and that is exactly what the phase gate forbids.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from btmm_ai_scanner.structure.enums import (
    StructureDirection,
    StructureTransitionType,
    SwingRelationshipLabel,
)

REPO = Path(__file__).resolve().parents[2]
PINE = REPO / "tradingview" / "btmm_poi_btrc_scanner_v1.pine"


def _src() -> str:
    return PINE.read_text(encoding="utf-8")


def _int_consts(text: str) -> dict[str, int]:
    return {
        m.group(1): int(m.group(2))
        for m in re.finditer(r"^int\s+(C_ST_[A-Z_]+)\s*=\s*(-?\d+)\s*$", text, re.M)
    }


# ---------------------------------------------------------------------------
# P2-I1 — structure codes
# ---------------------------------------------------------------------------

def test_every_python_enum_member_has_exactly_one_pine_code() -> None:
    """1:1 mapping, both directions — no missing member, no invented one."""
    consts = _int_consts(_src())
    expected = (
        {f"C_ST_DIR_{m.name}" for m in StructureDirection}
        | {f"C_ST_REL_{m.name}" for m in SwingRelationshipLabel}
        | {f"C_ST_TR_{m.name}" for m in StructureTransitionType}
    )
    declared = set(consts) - {"C_ST_NA"}
    assert declared == expected, (
        f"missing: {sorted(expected - declared)}  invented: {sorted(declared - expected)}"
    )


def test_code_counts_match_the_closed_python_enums() -> None:
    consts = _int_consts(_src())
    assert len([k for k in consts if k.startswith("C_ST_DIR_")]) == len(StructureDirection) == 3
    assert len([k for k in consts if k.startswith("C_ST_REL_")]) == len(SwingRelationshipLabel) == 6
    assert len([k for k in consts if k.startswith("C_ST_TR_")]) == len(StructureTransitionType) == 4


def test_codes_are_distinct_within_each_family() -> None:
    consts = _int_consts(_src())
    for prefix in ("C_ST_DIR_", "C_ST_REL_", "C_ST_TR_"):
        values = [v for k, v in consts.items() if k.startswith(prefix)]
        assert len(values) == len(set(values)), f"duplicate code value in {prefix}"


def test_unset_sentinel_is_neither_zero_nor_na() -> None:
    """0 is a live direction code (UNDETERMINED), and `int x = na` degrades to
    `const int` in Pine v6 — the defect that broke the first forensic probe."""
    consts = _int_consts(_src())
    assert "C_ST_NA" in consts
    assert consts["C_ST_NA"] != 0
    assert consts["C_ST_NA"] not in {
        v for k, v in consts.items() if k != "C_ST_NA"
    }, "the sentinel must not collide with any live code"
    assert not re.search(r"^int\s+C_ST_NA\s*=\s*na", _src(), re.M)


@pytest.mark.parametrize(
    "forbidden", ["RANGE", "NEUTRAL", "MSS", "INTERNAL", "EXTERNAL", "MAJOR", "MINOR"]
)
def test_no_structure_state_absent_from_python_is_invented(forbidden: str) -> None:
    """structure/enums.py is a closed set; a Pine code for anything else would
    fabricate a state the Python contract cannot emit."""
    consts = _int_consts(_src())
    assert not [k for k in consts if forbidden in k], (
        f"C_ST_* code containing {forbidden!r} has no Python counterpart"
    )


# ---------------------------------------------------------------------------
# P2-I1 — record declarations
# ---------------------------------------------------------------------------

def _type_body(text: str, name: str) -> str:
    m = re.search(rf"^type {name}\n((?:[ \t]+.*\n|\n)*)", text, re.M)
    assert m, f"type {name} not declared"
    return m.group(1)


@pytest.mark.parametrize(
    ("type_name", "fields"),
    [
        (
            "StructSwingView",
            ["stableKey", "swingType", "pivotPrice", "referenceAtr",
             "meaningfulConfTime", "pivotStartTime", "pivotStartAbs"],
        ),
        (
            "StructRelRec",
            ["swingKey", "previousSameTypeKey", "relationshipCode", "availabilityTime"],
        ),
        (
            "StructEventRec",
            ["transitionCode", "brokenSwingKey", "brokenLevel", "breakClose",
             "breakTime", "availabilityTime"],
        ),
    ],
)
def test_structure_records_declare_exactly_the_planned_fields(type_name, fields) -> None:
    body = _type_body(_src(), type_name)
    declared = re.findall(r"^\s+(?:int|float|bool|string)\s+(\w+)", body, re.M)
    assert declared == fields, f"{type_name} fields drifted: {declared}"


def test_future_records_are_declared_but_never_constructed() -> None:
    """I1 authorises declarations only. A constructor call would mean behaviour."""
    text = _src()
    assert "type StructRelRec" in text
    assert "type StructEventRec" in text
    assert "StructRelRec.new(" not in text
    assert "StructEventRec.new(" not in text


def test_swing_view_does_not_duplicate_all_of_swingrec() -> None:
    """Redundant carriage would create a second source of truth. Fields P2 does
    not consume (localConfTime, tieTolerance, reversalThreshold/Excursion) stay
    on SwingRec only."""
    body = _type_body(_src(), "StructSwingView")
    for redundant in ("localConfTime", "tieTolerance", "reversalThreshold",
                      "reversalExcursion", "pivotEndIdx"):
        assert redundant not in body, f"StructSwingView must not carry {redundant}"


# ---------------------------------------------------------------------------
# P2-I2 — adapter
# ---------------------------------------------------------------------------

def _adapter_body(text: str) -> str:
    start = text.index("f_p2BuildSwingView(")
    end = text.index("\n// ====", start)
    return text[start:end]


def test_adapter_exists_and_is_the_only_p2_swing_source() -> None:
    text = _src()
    assert text.count("f_p2BuildSwingView(") == 2, (
        "expected exactly one definition and one call site"
    )


def test_adapter_maps_stable_key_to_pine_own_swing_identity() -> None:
    """P1 documents pivotEndTime as 'the stable semantic swing identity' and
    binary-searches on it (f_srSwingHasKey), so reusing it needs no new field."""
    body = _adapter_body(_src())
    assert "StructSwingView.new(s.pivotEndTime," in body.replace(" ", " ")
    assert "the stable semantic swing identity" in _src()


def test_adapter_derives_absolute_index_from_absfirst() -> None:
    body = _adapter_body(_src())
    assert "absFirst + s.pivotStartIdx" in body


def test_adapter_uses_meaningful_confirmation_time_only() -> None:
    """Python availability is meaningful_confirmation_time_utc. Substituting a
    pivot time or the current bar time would break the non-repaint gate."""
    body = _adapter_body(_src())
    assert "s.meaningfulConfTime" in body
    assert "s.localConfTime" not in body
    assert "time_close" not in body
    assert "timenow" not in body


def test_adapter_never_reorders_canonical_p1_swings() -> None:
    """A sort here would silently redefine canonical order — a semantic bug."""
    body = _adapter_body(_src())
    for token in ("array.sort", "insertion sort", "array.reverse"):
        assert token not in body, f"adapter must not {token}"


def test_adapter_performs_no_swing_detection() -> None:
    """No second detector: the adapter may not look at raw highs/lows or apply
    any pivot/tolerance predicate."""
    body = _adapter_body(_src())
    for token in ("wHigh", "wLow", "C_PIVOT_TIE_TOL_ATR", "C_WINDOW_RADIUS",
                  "qHigh", "qLow"):
        assert token not in body, f"adapter must not reference {token}"


def test_adapter_runs_only_inside_the_confirmed_bar_block() -> None:
    """Closed-bar inheritance: the call must sit under `if barstate.isconfirmed`
    so a forming bar cannot move the adapted view."""
    text = _src()
    lines = text.splitlines()
    call = next(
        i for i, line in enumerate(lines) if "p2Swings = f_p2BuildSwingView" in line
    )
    guards = [
        i for i, line in enumerate(lines[:call]) if line.startswith("if barstate.isconfirmed")
    ]
    assert guards, "no `if barstate.isconfirmed` precedes the adapter call"
    # nothing at column 0 may intervene between the guard and the call
    between = [
        line
        for line in lines[guards[-1] + 1 : call]
        if line and not line[0].isspace() and not line.startswith("//")
    ]
    assert not between, f"adapter escaped the confirmed-bar block: {between[:3]}"


# ---------------------------------------------------------------------------
# Forbidden behaviour — the phase gate
# ---------------------------------------------------------------------------

def test_no_relationship_classification_yet() -> None:
    text = _src()
    for code in ("C_ST_REL_HIGHER_HIGH", "C_ST_REL_LOWER_HIGH", "C_ST_REL_EQUAL_HIGH",
                 "C_ST_REL_HIGHER_LOW", "C_ST_REL_LOWER_LOW", "C_ST_REL_EQUAL_LOW"):
        assert text.count(code) == 1, (
            f"{code} appears {text.count(code)} times; I1 permits the declaration only"
        )


def test_no_transition_emission_yet() -> None:
    text = _src()
    for code in ("C_ST_TR_BULLISH_BOS", "C_ST_TR_BEARISH_BOS",
                 "C_ST_TR_BULLISH_CHOCH", "C_ST_TR_BEARISH_CHOCH"):
        assert text.count(code) == 1, f"{code} used beyond its declaration"


def test_no_direction_state_machine_yet() -> None:
    text = _src()
    for code in ("C_ST_DIR_UNDETERMINED", "C_ST_DIR_BULLISH", "C_ST_DIR_BEARISH"):
        assert text.count(code) == 1, f"{code} used beyond its declaration"


def test_no_protected_or_weak_level_state_yet() -> None:
    text = _src()
    for token in ("protectedHigh", "protectedLow", "weakHigh", "weakLow",
                  "brokenKeys", "structDirection"):
        assert token not in text, f"{token} is P2-I5/I6 state, not I1/I2"


def test_no_structure_tolerance_arithmetic_yet() -> None:
    """The 0.10 relationship tolerance must not be computed anywhere yet."""
    text = _src()
    assert "C_ST_REL_TOL" not in text
    assert not re.search(r"0\.10\s*\*\s*\w*[Ss]wing", text)


# ---------------------------------------------------------------------------
# P1 integrity and budget
# ---------------------------------------------------------------------------

def test_p1_swingrec_is_unchanged() -> None:
    """The adapter must not have required a P1 record change."""
    body = _type_body(_src(), "SwingRec")
    declared = re.findall(r"^\s+(?:int|float)\s+(\w+)", body, re.M)
    assert declared == [
        "swingType", "price", "pivotStartIdx", "pivotEndIdx", "pivotEndTime",
        "localConfTime", "meaningfulConfTime", "referenceAtr", "tieTolerance",
        "reversalThreshold", "reversalExcursion",
    ], f"SwingRec drifted: {declared}"


def test_p1_capacity_and_defaults_unchanged() -> None:
    text = _src()
    assert "calc_bars_count = 1800)" in text
    assert "int C_P1_CALC_BARS     = 1800" in text
    assert "int C_P1_MIN_CALC_BARS = 1250" in text
    assert 'input.int(300, "Analytical window' in text
    assert "debugMode        = input.bool(false" in text


def test_p1_nine_outputs_still_present_and_ungated_by_debug() -> None:
    text = _src()
    for name in ("P1_swing_high_price", "P1_swing_low_price", "P1_disp_code",
                 "P1_disp_ratio", "P1_equal_high", "P1_equal_low", "P1_sr_top",
                 "P1_sr_bottom", "P1_tl_norm_slope"):
        line = next(ln for ln in text.splitlines() if f'"{name}"' in ln)
        assert "debugMode" not in line, f"{name} must not become debug-gated"


def test_p2_diagnostics_are_debug_gated() -> None:
    text = _src()
    p2_plots = [ln for ln in text.splitlines() if re.match(r'^\s*plot\(.*"P2_', ln)]
    assert p2_plots, "expected P2 adapter diagnostics"
    for line in p2_plots:
        assert "debugMode" in line, f"P2 diagnostic not debug-gated: {line[:70]}"
        assert "display.data_window" in line


def test_plot_budget_stays_well_under_the_tradingview_limit() -> None:
    """RE10140 fires at 64. P1 shipped 11; I1/I2 add debug diagnostics only."""
    text = _src()
    total = sum(
        len(re.findall(rf"^\s*{fn}\(", text, re.M))
        for fn in ("plot", "plotshape", "plotchar", "plotarrow", "plotcandle",
                   "plotbar", "bgcolor", "barcolor", "fill", "hline")
    )
    assert total <= 32, f"{total} plot-budget consumers; keep well clear of 64"


def _code_only(text: str) -> str:
    """Strip full-line and trailing `//` comments.

    Naive substring matching finds these APIs inside prose — the source
    documents "no request.security" in a design comment — so the check must look
    at code, not at the file.
    """
    out = []
    for line in text.splitlines():
        stripped = line.lstrip()
        if stripped.startswith("//"):
            continue
        out.append(line.split("//", 1)[0])
    return chr(10).join(out)


def test_no_order_or_strategy_or_mtf_apis() -> None:
    code = _code_only(_src())
    for api in ("strategy.entry", "strategy.exit", "strategy.order",
                "strategy.close", "strategy(", "request.security", "alert("):
        assert api not in code, f"forbidden API present in code: {api}"


def test_the_api_guard_actually_inspects_code_not_comments() -> None:
    """Guards the guard: the phrase exists in a comment, so a prose-matching
    implementation would pass vacuously and hide a real call."""
    assert "request.security" in _src(), "expected the phrase in a comment"
    assert "request.security" not in _code_only(_src())


def test_source_is_pine_v6() -> None:
    assert _src().splitlines()[0].strip() == "//@version=6"


def test_no_bare_bool_declared_as_na() -> None:
    bad = [
        f"{n}: {ln.strip()}"
        for n, ln in enumerate(_src().splitlines(), 1)
        if re.search(r"\bbool\s+\w+\s*=\s*na\s*(//.*)?$", ln)
    ]
    assert not bad, "Pine v6 cannot assign to a const bool:\n" + "\n".join(bad)
