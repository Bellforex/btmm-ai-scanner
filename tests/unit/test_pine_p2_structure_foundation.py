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
            ["swingKey", "previousSameTypeKey", "relationshipCode", "availabilityTime",
             "currentPivotStartAbs"],
        ),
        (
            "StructEventRec",
            ["transitionCode", "brokenSwingKey", "brokenLevel", "breakClose",
             "breakTime", "availabilityTime", "protectedSwingKey"],
        ),
    ],
)
def test_structure_records_declare_exactly_the_planned_fields(type_name, fields) -> None:
    body = _type_body(_src(), type_name)
    declared = re.findall(r"^\s+(?:int|float|bool|string)\s+(\w+)", body, re.M)
    assert declared == fields, f"{type_name} fields drifted: {declared}"


def test_transition_record_is_constructed_for_bos_only() -> None:
    """As of I5 StructEventRec is built — but only with BOS transition codes."""
    text = _src()
    assert "StructRelRec.new(" in text, "I3 must construct relationships"
    assert "StructEventRec.new(" in text, "I5 must construct BOS transitions"
    construction = text.split("StructEventRec.new(")[1].split(")\n")[0]
    assert "C_ST_TR_BULLISH_BOS" in construction
    assert "C_ST_TR_BEARISH_BOS" in construction
    assert "CHOCH" not in construction, "CHOCH emission is a later phase"


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

NL = chr(10)


def _fn_body(text: str, name: str) -> str:
    """Body of a Pine function, up to the next top-level banner or definition."""
    start = text.index(NL + name + "(")
    rest = text[start + 1 :]
    end = len(rest)
    for marker in (NL + "// ====", NL + "f_p2"):
        idx = rest.find(marker, len(name))
        if idx != -1:
            end = min(end, idx)
    return rest[:end]


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

def test_every_relationship_code_is_actually_reachable() -> None:
    """As of I3 each label must be produced by the classifier, not just declared.
    A code that appears only once is a declared-but-unreachable label."""
    text = _src()
    for code in ("C_ST_REL_HIGHER_HIGH", "C_ST_REL_LOWER_HIGH", "C_ST_REL_EQUAL_HIGH",
                 "C_ST_REL_HIGHER_LOW", "C_ST_REL_LOWER_LOW", "C_ST_REL_EQUAL_LOW"):
        assert text.count(code) >= 2, f"{code} is declared but never assigned"


def test_relationship_tolerance_is_a_named_constant() -> None:
    """No anonymous 0.10 literal in the classifier."""
    text = _src()
    assert "float C_ST_REL_EQUAL_TOL_ATR = 0.10" in text
    body = _fn_body(text, "f_p2ClassifyRelationship")
    assert "C_ST_REL_EQUAL_TOL_ATR * cur.referenceAtr" in body
    assert "0.10" not in body, "classifier must not inline the multiplier"


def test_classifier_uses_current_swing_atr_not_predecessor() -> None:
    body = _fn_body(_src(), "f_p2ClassifyRelationship")
    assert "cur.referenceAtr" in body
    assert "prev.referenceAtr" not in body, "tolerance must use the CURRENT swing ATR"


def test_classifier_boundaries_are_strict() -> None:
    body = _fn_body(_src(), "f_p2ClassifyRelationship")
    assert "cur.pivotPrice > prev.pivotPrice + tol" in body
    assert "cur.pivotPrice < prev.pivotPrice - tol" in body
    assert ">=" not in body and "<=" not in body, (
        "non-strict comparison would move the equal-band edges"
    )


def test_classifier_is_pure() -> None:
    """No persistent state, no candle access, no swing detection."""
    body = _fn_body(_src(), "f_p2ClassifyRelationship")
    for token in ("var ", "wHigh", "wLow", "close", "high[", "low[", "timenow",
                  "array.push"):
        assert token not in body, f"classifier must not reference {token}"


def test_relationship_builder_reproduces_python_output_order() -> None:
    """Python filters highs then lows and appends in that order, so the tuple is
    all-highs-then-all-lows, NOT chronologically interleaved."""
    body = _fn_body(_src(), "f_p2BuildRelationships")
    assert "for pass = 0 to 1" in body
    assert "pass == 0 ? SWING_HIGH : SWING_LOW" in body


def test_relationship_builder_walks_per_type_not_two_back() -> None:
    """A hardcoded i-2 would rely on alternation; the per-type walk does not."""
    body = _fn_body(_src(), "f_p2BuildRelationships")
    assert "prevIdx" in body
    assert "i - 2" not in body and "i-2" not in body


def test_relationship_availability_is_the_later_confirmation() -> None:
    body = _fn_body(_src(), "f_p2BuildRelationships")
    assert "math.max(v.meaningfulConfTime, pv.meaningfulConfTime)" in body


def test_relationship_builder_retains_no_state_behind_the_window() -> None:
    """Python classifies exactly the bounded input it receives, so Pine must not
    keep a predecessor that has dropped out of P1's live swing list."""
    body = _fn_body(_src(), "f_p2BuildRelationships")
    assert "var " not in body, "builder must hold no persistent state"


def test_bos_codes_are_reachable_and_choch_codes_are_not() -> None:
    """The I5 phase boundary: BOS is behavioural, CHOCH is still declaration-only."""
    text = _src()
    for code in ("C_ST_TR_BULLISH_BOS", "C_ST_TR_BEARISH_BOS"):
        assert text.count(code) >= 2, f"{code} is declared but never emitted"
    for code in ("C_ST_TR_BULLISH_CHOCH", "C_ST_TR_BEARISH_CHOCH"):
        assert text.count(code) == 1, f"{code} used beyond its declaration"


def test_every_direction_code_is_actually_reachable() -> None:
    """As of I4 direction is behavioural, not merely declared."""
    text = _src()
    for code in ("C_ST_DIR_UNDETERMINED", "C_ST_DIR_BULLISH", "C_ST_DIR_BEARISH"):
        assert text.count(code) >= 2, f"{code} is declared but never assigned"


def test_no_weak_re_arm_state_yet() -> None:
    """I5 owns BOS. Weak RE-ARM after the boundary is P2-I6 / TD-B.

    The boundary index may be written (BOS sets it) but must not yet be READ by
    any swing-visible gate, which is what re-arming would require.
    """
    swing_branch = _walk_branches(_src())["swing"]
    assert "weakHighBoundaryAbs" not in swing_branch
    assert "weakLowBoundaryAbs" not in swing_branch
    assert "weakHighIx :=" not in swing_branch
    assert "weakLowIx :=" not in swing_branch
    assert "array.push(visOrder" in swing_branch, (
        "the swing branch must still register the replacement candidate"
    )


def _walk_branches(text: str) -> dict[str, str]:
    """Split f_p2StructureWalk's event dispatch into its three branches.

    Pine has no `else:` terminator, so the branches are cut on the exact
    indentation-anchored `if pick == N` / `else if pick == N` / trailing `else`
    lines, and the final branch stops before the function's return tuple.
    """
    body = _fn_body(text, "f_p2StructureWalk")
    candle_start = body.index(NL + " " * 12 + "if pick == 0")
    swing_start = body.index(NL + " " * 12 + "else if pick == 1")
    rel_start = body.index(NL + " " * 12 + "else" + NL, swing_start)
    rel_end = body.index(NL + " " * 4 + "int protHighKey")
    return {
        "candle": body[candle_start:swing_start],
        "swing": body[swing_start:rel_start],
        "relationship": body[rel_start:rel_end],
    }


# --- P2-I4 bootstrap gates ------------------------------------------------

def test_bootstrap_uses_merged_availability_order_not_api_order() -> None:
    """The single highest-risk detail: `f_p2BuildRelationships` emits highs then
    lows, which is API order, NOT chronology. The walk must consume an explicitly
    ordered index list keyed on availability then the current swing's pivot index
    (transitions.py:122-135)."""
    text = _src()
    order_body = _fn_body(text, "f_p2OrderRelationships")
    assert "r.availabilityTime < o.availabilityTime" in order_body
    assert "r.currentPivotStartAbs < o.currentPivotStartAbs" in order_body

    walk_body = _fn_body(text, "f_p2StructureWalk")
    assert "array.get(rels, array.get(relOrder, ri))" in walk_body, (
        "walk must iterate the ORDERED index list, not the raw relationship array"
    )
    assert "f_p2BuildRelationships" not in walk_body, (
        "walk must not rebuild relationships in API order"
    )


def test_bootstrap_predicates_match_python() -> None:
    body = _fn_body(_src(), "f_p2StructureWalk")
    assert "hiLabel == C_ST_REL_HIGHER_HIGH and loLabel == C_ST_REL_HIGHER_LOW" in body
    assert "hiLabel == C_ST_REL_LOWER_HIGH and loLabel == C_ST_REL_LOWER_LOW" in body


def test_bootstrap_assigns_only_the_two_python_slots_per_direction() -> None:
    """BULLISH sets protected_low + weak_high; BEARISH sets protected_high +
    weak_low. The opposite two must stay unset (transitions.py:366-381)."""
    body = _fn_body(_src(), "f_p2StructureWalk")
    # Only the assignment lines of each branch — the shared return tuple names
    # every slot and would defeat a naive substring split.
    assigns = [ln.strip() for ln in body.splitlines() if ":=" in ln]
    bull = [ln for ln in assigns[assigns.index("dir        := C_ST_DIR_BULLISH"):]
            if ln.startswith(("protLowIx", "weakHighIx", "protHighIx", "weakLowIx"))][:2]
    bear = [ln for ln in assigns[assigns.index("dir        := C_ST_DIR_BEARISH"):]
            if ln.startswith(("protLowIx", "weakHighIx", "protHighIx", "weakLowIx"))][:2]
    assert [ln.split()[0] for ln in bull] == ["protLowIx", "weakHighIx"], bull
    assert [ln.split()[0] for ln in bear] == ["protHighIx", "weakLowIx"], bear


def test_bootstrap_is_once_only() -> None:
    """Relationship evidence must never flip an established direction; flips are
    CHOCH (P2-I5+)."""
    body = _fn_body(_src(), "f_p2StructureWalk")
    assert "if dir == C_ST_DIR_UNDETERMINED" in body


def test_bootstrap_branch_emits_no_transition() -> None:
    """The RELATIONSHIP branch sets direction and the initial levels only; every
    transition in the walk is emitted from the CANDLE branch."""
    rel_branch = _walk_branches(_src())["relationship"]
    for token in ("C_ST_TR_", "StructEventRec", "array.push", "brokenKeys"):
        assert token not in rel_branch, f"bootstrap must not emit: {token}"
    assert "C_ST_DIR_BULLISH" in rel_branch, "but it must still bootstrap"


def test_structure_walk_reads_no_live_series_values() -> None:
    """I5 consumes the CONFIRMED window arrays passed in as parameters.

    It must never touch the Pine series builtins directly: `close`/`high`/`low`/
    `open` would be the FORMING bar, and a wick would not be a close-only break.
    Word boundaries matter — the parameter `closes` and the local `barClose` are
    legitimate, the bare builtin `close` is not.
    """
    raw = _src()
    for fn in ("f_p2OrderRelationships", "f_p2OrderSwings", "f_p2RelIsHigh",
               "f_p2MostRecentUnbroken", "f_p2ViewIndexByKey", "f_p2StructureWalk"):
        # The body must be located in the RAW source — _code_only strips the
        # banner comments that delimit a function — then comment-stripped.
        body = _code_only(_fn_body(raw, fn))
        found = re.findall(
            r"(?<![\w.])(close|high|low|open|timenow|volume)(?![\w])", body
        )
        assert not found, f"{fn} references live series values: {sorted(set(found))}"
        assert "request." not in body


def test_structure_walk_retains_no_state_behind_the_window() -> None:
    """Batch-equivalent over the bounded window: rebuilt every confirmed bar,
    never accumulated."""
    text = _src()
    for fn in ("f_p2OrderRelationships", "f_p2OrderSwings", "f_p2MostRecentUnbroken",
               "f_p2StructureWalk"):
        assert "var " not in _fn_body(text, fn), f"{fn} must hold no persistent state"


# --- P2-I5 BOS gates ------------------------------------------------------

def test_bos_predicates_are_strict_and_close_only() -> None:
    candle = _code_only(_walk_branches(_src())["candle"])
    assert "barClose > array.get(views, weakHighIx).pivotPrice" in candle
    assert "barClose < array.get(views, weakLowIx).pivotPrice" in candle
    # Every price comparison in the branch must be strict. `>= 0` index guards
    # are not price tests, so the check is anchored on pivotPrice itself.
    price_tests = re.findall(r"[<>]=?\s*array\.get\(views, \w+\)\.pivotPrice", candle)
    assert len(price_tests) == 4, price_tests
    for test in price_tests:
        assert "=" not in test, f"equality must not break: {test}"


def test_choch_guard_is_suppression_only() -> None:
    """The guard must decide BOS eligibility and nothing else: no transition, no
    direction flip, no swing consumption, no state mutation."""
    candle = _walk_branches(_src())["candle"]
    guard = candle.split("bool chochGuard = false")[1].split("if chochGuard")[0]

    # It may READ the direction and the protected level; it may WRITE only its
    # own boolean.
    assignments = re.findall(r"(\w+)\s*:=", guard)
    assert set(assignments) == {"chochGuard"}, assignments
    for token in ("array.push", "StructEventRec", "C_ST_TR_"):
        assert token not in guard, f"CHOCH guard must not {token}"

    taken = candle.split("if chochGuard")[1].split(NL + " " * 16 + "else" + NL, 1)[0]
    assert "suppressed := suppressed + 1" in taken
    taken_assignments = re.findall(r"(\w+)\s*:=", taken)
    assert set(taken_assignments) == {"suppressed"}, (
        f"suppression must mutate nothing else: {taken_assignments}"
    )
    for token in ("array.push", "StructEventRec", "C_ST_TR_"):
        assert token not in taken, f"suppression path must not {token}"


def test_defensive_fallback_is_present_and_not_optimised_away() -> None:
    """Architecture doc 17.5a: the fallback is retained even though it is proven
    unreachable, and no runtime assertion encodes the invariant."""
    body = _fn_body(_src(), "f_p2StructureWalk")
    assert "int newProtIx = replIx >= 0 ? replIx : existing" in body
    assert "runtime.error" not in body
    assert "int existing = bosHigh ? protLowIx : protHighIx" in body


def test_broken_swing_is_consumed_before_the_replacement_search() -> None:
    """Python adds to broken_ids at :260, before searching at :262."""
    body = _fn_body(_src(), "f_p2StructureWalk")
    assert body.index("array.push(brokenKeys, broken.stableKey)") < body.index(
        "int replIx   = f_p2MostRecentUnbroken("
    )


def test_replacement_transcribes_all_three_key_tiers() -> None:
    body = _fn_body(_src(), "f_p2MostRecentUnbroken")
    assert "v.pivotStartAbs > b.pivotStartAbs" in body
    assert "v.pivotStartTime > b.pivotStartTime" in body
    assert "v.stableKey > b.stableKey" in body
    assert "array.indexof(brokenKeys, v.stableKey) < 0" in body


def test_bos_clears_only_its_own_weak_side_in_source() -> None:
    body = _fn_body(_src(), "f_p2StructureWalk")
    bull = body.split("if bosHigh\n")[1].split("else")[0]
    assert "weakHighIx := -1" in bull
    assert "weakLowIx" not in bull
    assert "weakHighBoundaryAbs := barAbs" in bull


def test_transition_availability_keeps_the_max() -> None:
    body = _fn_body(_src(), "f_p2StructureWalk")
    assert (
        "math.max(array.get(availT, ci), broken.meaningfulConfTime)" in body
    ), "the max must be transcribed structurally, not simplified to the candle"


def test_merged_walk_is_a_three_way_cursor_merge() -> None:
    """Not a sort of the combined list: each stream is pre-sorted, and ties are
    resolved by kind because only a STRICTLY earlier time displaces."""
    body = _fn_body(_src(), "f_p2StructureWalk")
    for cursor in ("ci := ci + 1", "si := si + 1", "ri := ri + 1"):
        assert cursor in body
    assert "sv.meaningfulConfTime < bestT" in body
    assert "rr.availabilityTime < bestT" in body
    assert "<=" not in body.split("// ---- pick the next event")[1].split("if pick == 0")[0]


def test_no_break_predicates_yet() -> None:
    """No close-vs-structural-level comparison anywhere in P2 code."""
    code = _code_only(_src())
    assert not re.search(r"close\s*[<>]", code), "break predicate is P2-I5, not I4"


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
    """RE10140 fires at 64. P1 shipped 11; P2 adds debug diagnostics only, and
    I4 retired two superseded adapter echoes to fund the bootstrap slots."""
    text = _src()
    total = sum(
        len(re.findall(rf"^\s*{fn}\(", text, re.M))
        for fn in ("plot", "plotshape", "plotchar", "plotarrow", "plotcandle",
                   "plotbar", "bgcolor", "barcolor", "fill", "hline")
    )
    assert total <= 26, f"{total} plot-budget consumers; P2-I5 target is 26"


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
