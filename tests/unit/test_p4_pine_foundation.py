"""P4 — static contract tests for the Pine BTMM engine.

Pine cannot run locally, so these read
`tradingview/btmm_poi_btrc_scanner_p4_dev.pine` as source and assert the
structural guarantees the compile and the real-data parity depend on:

* P4 DEV is the frozen P3 DEV scanner with ONLY the title changed and the
  false-invalidation tracking added, plus an appended P4 block -- so no P1, P2 or
  P3 semantic region can drift while P4 is built on top of it, and the added
  tracking is provably write-only from P3's side;
* every ported BTMM configuration constant equals its `BtmmConfiguration`
  default;
* the integer vocabulary covers exactly the PRODUCED enum members and omits the
  reserved ones, so the port neither invents behaviour nor drops any;
* setup admission reproduces `analyze_btmm`'s two skips -- ineligible POI type
  and unsupported source timeframe -- rather than conflating "unsupported" with
  "supporting-only";
* the reviewed-evidence channel exists, is read by the engine, and is written by
  nothing, which is what makes live confirmation unreachable by construction
  instead of by deleting the confirmation branch;
* derived liquidity writes only the location and source and never the status the
  final gate reads;
* the closed-bar gate is present and no `request.security` or `strategy.*` is
  introduced.
"""

from __future__ import annotations

import re
from decimal import Decimal
from pathlib import Path

from btmm_ai_scanner.btmm.configuration import BtmmConfiguration

REPO = Path(__file__).resolve().parents[2]
P3_DEV = REPO / "tradingview" / "btmm_poi_btrc_scanner_p3_dev.pine"
P4_DEV = REPO / "tradingview" / "btmm_poi_btrc_scanner_p4_dev.pine"

OLD_TITLE = "BTMM + POI + BTRC Scanner [P3 DEV]"
NEW_TITLE = "BTMM + POI + BTRC Scanner [P4 DEV]"
BANNER = "// P4 — BTMM SETUP ENGINE  (P4-I1 .. P4-I8)"

#: The only names P4 may add inside the P3 region. Both carry the one P3 fact
#: BTMM consumes that the existing arrays cannot answer: a genuine invalidation
#: is terminal, so poiRepLastCode identifies and times it, but a false
#: invalidation is not, so "did this POI ever sweep?" needs its own flag.
ALLOWED_P3_ADDITIONS = ("poiCommFalseInv", "poiRepFalseInv", "falseSeen", "cFalseSeen")

_CONFIG = BtmmConfiguration(minimum_price_tick=Decimal("0.01"))


def _p4_text() -> str:
    return P4_DEV.read_text(encoding="utf-8")


def _p4_appendix() -> str:
    text = _p4_text()
    index = text.index(BANNER)
    return text[index:]


def _p3_region() -> str:
    return _p4_text()[: _p4_text().index(BANNER)]


def _code(text: str) -> str:
    return "\n".join(
        line for line in text.splitlines() if not line.strip().startswith("//")
    )


def _int_const(name: str, text: str) -> int:
    match = re.search(rf"^int\s+{name}\s*=\s*(-?\d+)\s*$", text, re.MULTILINE)
    assert match is not None, f"missing int constant {name}"
    return int(match.group(1))


def _float_const(name: str, text: str) -> Decimal:
    match = re.search(rf"^float\s+{name}\s*=\s*(-?[\d.]+)\s*$", text, re.MULTILINE)
    assert match is not None, f"missing float constant {name}"
    return Decimal(match.group(1))


# ---------------------------------------------------------------------------
# The P3 boundary
# ---------------------------------------------------------------------------


def test_p4_is_p3_plus_title_plus_tracking_plus_appendix() -> None:
    """Every line the P3 region gained must be one of the allowed additions.

    A diff rather than a hash, because P4 legitimately adds tracking inside the
    P3 lifecycle walk; the point is that it adds ONLY that.
    """
    import difflib

    p3 = P3_DEV.read_text(encoding="utf-8").splitlines()
    p4 = _p3_region().splitlines()

    added = [
        line[1:]
        for line in difflib.unified_diff(p3, p4, n=0, lineterm="")
        if line.startswith("+") and not line.startswith("+++")
    ]
    removed = [
        line[1:]
        for line in difflib.unified_diff(p3, p4, n=0, lineterm="")
        if line.startswith("-") and not line.startswith("---")
    ]

    # The only removals are the P3 driver block, which moves below the P4
    # section, and the old title line.
    for line in removed:
        assert OLD_TITLE in line or line.strip().startswith(
            ("if barstate.isconfirmed", "int p3Wn", "if p3Wn", "f_poi")
        ), f"P3 region lost a semantic line: {line!r}"

    for line in added:
        stripped = line.strip()
        if not stripped or stripped.startswith("//"):
            continue
        if NEW_TITLE in line:
            continue
        assert any(name in line for name in ALLOWED_P3_ADDITIONS), (
            f"P4 changed P3 semantics: {line!r}"
        )


def test_the_added_p3_tracking_is_write_only_from_p3s_side() -> None:
    """Nothing in the P3 region READS the new flags -- they are written there and
    consumed only by the P4 engine, so no P3 output can depend on them."""
    region = _code(_p3_region())
    readers = [
        line
        for line in region.splitlines()
        if "array.get(poiCommFalseInv" in line or "array.get(poiRepFalseInv" in line
    ]
    # The single permitted read inside the P3 region is the one that computes
    # the reported flag from the committed one.
    assert len(readers) == 1
    assert "array.set(poiRepFalseInv" in readers[0]

    appendix = _code(_p4_appendix())
    assert "array.get(poiRepFalseInv" in appendix


def test_p4_declares_its_title_and_keeps_the_execution_horizon() -> None:
    line = next(x for x in _p4_text().splitlines() if x.startswith("indicator("))
    assert NEW_TITLE in line
    assert "calc_bars_count = 1800" in line


# ---------------------------------------------------------------------------
# Setup admission
# ---------------------------------------------------------------------------


def test_supported_timeframe_is_distinct_from_formation_timeframe() -> None:
    """`analyze_btmm` skips a POI whose source timeframe is outside
    `formation | supporting_only` (analyzer.py:400-416), so on H1/H4/D1 it
    creates NO setups -- not supporting-only ones. Conflating the two would make
    an unsupported chart silently produce a whole BTMM registry."""
    code = _code(_p4_appendix())
    assert "C_BTMM_IS_FORMATION_TF" in code
    assert "C_BTMM_TF_SUPPORTED" in code

    formation = re.search(r"bool C_BTMM_IS_FORMATION_TF\s*=\s*(.+)", code)
    supported = re.search(r"bool C_BTMM_TF_SUPPORTED\s*=\s*(.+)", code)
    assert formation is not None and supported is not None

    # M5 and M15 form; M1 is supported but supporting-only.
    assert '"5"' in formation.group(1) and '"15"' in formation.group(1)
    assert '"1"' in supported.group(1)
    assert "C_BTMM_IS_FORMATION_TF" in supported.group(1)


def test_setup_creation_is_gated_on_supported_timeframe_and_core_type() -> None:
    code = _code(_p4_appendix())
    creation = re.search(
        r"if C_BTMM_TF_SUPPORTED and tc >= C_POI_CORE_TYPE_MIN and tc <= C_POI_CORE_TYPE_MAX",
        code,
    )
    assert creation is not None, "setup creation must reproduce both production skips"


def test_formation_timeframes_match_production_defaults() -> None:
    from btmm_ai_scanner.config.enums import Timeframe

    assert _CONFIG.formation_timeframes == frozenset({Timeframe.M5, Timeframe.M15})
    assert _CONFIG.supporting_only_timeframes == frozenset({Timeframe.M1})


# ---------------------------------------------------------------------------
# Ported configuration
# ---------------------------------------------------------------------------


def test_ported_configuration_constants_match_production_defaults() -> None:
    text = _p4_appendix()
    pairs = {
        "C_BTMM_OVERSHOOT_TOL_ATR_MULT": (
            _CONFIG.interaction_overshoot_tolerance_atr_multiplier
        ),
        "C_BTMM_OVERSHOOT_TOL_HEIGHT_MULT": (
            _CONFIG.interaction_overshoot_tolerance_zone_height_multiplier
        ),
        "C_BTMM_EDGE_TOUCH_MAX_RATIO": (
            _CONFIG.interaction_edge_touch_max_penetration_ratio
        ),
        "C_BTMM_PARTIAL_ENTRY_MAX_RATIO": (
            _CONFIG.interaction_partial_entry_max_penetration_ratio
        ),
        "C_BTMM_STD_ATR_RATIO": _CONFIG.reaction_standard_atr_ratio,
        "C_BTMM_STD_CLEARANCE_RATIO": _CONFIG.reaction_standard_zone_clearance_ratio,
        "C_BTMM_STD_EFFICIENCY": _CONFIG.reaction_standard_directional_efficiency,
        "C_BTMM_STD_CANDLE_SHARE": _CONFIG.reaction_standard_directional_candle_share,
        "C_BTMM_STRONG_ATR_RATIO": _CONFIG.reaction_strong_atr_ratio,
        "C_BTMM_STRONG_CLEARANCE_RATIO": _CONFIG.reaction_strong_zone_clearance_ratio,
        "C_BTMM_STRONG_EFFICIENCY": _CONFIG.reaction_strong_directional_efficiency,
        "C_BTMM_STRONG_CANDLE_SHARE": _CONFIG.reaction_strong_directional_candle_share,
        "C_BTMM_FAST_SPEED": _CONFIG.reaction_speed_fast_normalized_speed_per_bar,
        "C_BTMM_FAST_EFFICIENCY": _CONFIG.reaction_speed_fast_directional_efficiency,
        "C_BTMM_FAST_CANDLE_SHARE": (
            _CONFIG.reaction_speed_fast_directional_candle_share
        ),
        "C_BTMM_SFAST_SPEED": (
            _CONFIG.reaction_speed_strong_fast_normalized_speed_per_bar
        ),
        "C_BTMM_SFAST_EFFICIENCY": (
            _CONFIG.reaction_speed_strong_fast_directional_efficiency
        ),
        "C_BTMM_SFAST_CANDLE_SHARE": (
            _CONFIG.reaction_speed_strong_fast_directional_candle_share
        ),
    }
    for name, expected in pairs.items():
        assert _float_const(name, text) == expected, name

    assert _int_const("C_BTMM_REACTION_WINDOW_BARS", text) == (
        _CONFIG.reaction_window_bars
    )


# ---------------------------------------------------------------------------
# Vocabulary: produced only
# ---------------------------------------------------------------------------


def test_every_produced_lifecycle_status_has_a_code() -> None:
    text = _p4_appendix()
    codes = {
        _int_const(name, text)
        for name in (
            "C_BTMM_ST_CANDIDATE",
            "C_BTMM_ST_FORMING",
            "C_BTMM_ST_BLOCKED",
            "C_BTMM_ST_CONFIRMED",
            "C_BTMM_ST_CANCELLED",
        )
    }
    assert len(codes) == 5, "the five statuses must have distinct codes"
    assert _int_const("C_BTMM_ST_NA", text) not in codes


def test_all_fifteen_transition_codes_exist_and_are_distinct() -> None:
    text = _p4_appendix()
    names = re.findall(r"^int (C_BTMM_TR_\w+)\s*=", text, re.MULTILINE)
    assert len(names) == 15, names
    assert len({_int_const(n, text) for n in names}) == 15


def test_all_eight_cancellation_and_four_blocked_reasons_exist() -> None:
    text = _p4_appendix()
    cancels = [
        n
        for n in re.findall(r"^int (C_BTMM_CANCEL_\w+)\s*=", text, re.MULTILINE)
        if n != "C_BTMM_CANCEL_NA"
    ]
    blocks = [
        n
        for n in re.findall(r"^int (C_BTMM_BLOCK_\w+)\s*=", text, re.MULTILINE)
        if n != "C_BTMM_BLOCK_NA"
    ]
    assert len(cancels) == 8, cancels
    assert len(blocks) == 4, blocks


def test_reserved_vocabulary_is_not_ported() -> None:
    """Production never assigns these, so inventing a Pine code for one would be
    the port claiming behaviour the source does not have."""
    text = _p4_appendix()
    for reserved in (
        "NO_CONTACT",
        "NEAR_MISS",
        "MODEL_PROPOSED",
        "AWAITING_REACTION",
        "REACTION_IN_PROGRESS",
        "CONTEXT_CHECK",
        "LIQUIDITY_MONITORING",
        "APPROACH_MONITORING",
        "LIQUIDITY_BEFORE_POI",
        "LIQUIDITY_WITHIN_POI",
        "MULTIPLE_LOCATIONS",
        "NONE_OBSERVED",
        "NOT_YET_EVALUATED",
    ):
        assert f"C_BTMM_{reserved}" not in text
        assert not re.search(rf"^int \w*{reserved}\w*\s*=", text, re.MULTILINE)


def test_the_seven_produced_interaction_classes_are_ported() -> None:
    text = _p4_appendix()
    names = [
        n
        for n in re.findall(r"^int (C_BTMM_IC_\w+)\s*=", text, re.MULTILINE)
        if n != "C_BTMM_IC_NONE"
    ]
    assert len(names) == 7, names
    eligible = re.search(r"f_btmmInteractionEligible\(int code\) =>\n(.+)", text)
    assert eligible is not None
    body = eligible.group(1)
    for name in (
        "C_BTMM_IC_EDGE_TOUCH",
        "C_BTMM_IC_PARTIAL_ENTRY",
        "C_BTMM_IC_DEEP_ENTRY",
        "C_BTMM_IC_FAR_BOUNDARY",
        "C_BTMM_IC_CONTROLLED_OVER",
    ):
        assert name in body
    # The two ineligible classes must NOT pass the gate.
    assert "C_BTMM_IC_EXCESSIVE_OVER" not in body
    assert "C_BTMM_IC_NONCANONICAL" not in body


# ---------------------------------------------------------------------------
# The reviewed-evidence boundary
# ---------------------------------------------------------------------------


def test_the_evidence_channel_exists_and_nothing_writes_it() -> None:
    """This is the whole two-layer contract in one assertion.

    The engine READS these arrays, so confirmation is implemented. Nothing WRITES
    them beyond the neutral push at setup creation, so confirmation is
    unreachable at runtime by construction rather than by deleting the branch. A
    future change that populates any of them from market data would flip a
    machine calculation into a claim of human review, and would fail here.
    """
    code = _code(_p4_appendix())
    channel = (
        "btmmEvHas",
        "btmmEvTime",
        "btmmEvCtxDir",
        "btmmEvCtxFw",
        "btmmEvSession",
        "btmmEvVolume",
        "btmmEvLqStatus",
        "btmmEvLqSrc",
    )
    for name in channel:
        assert (
            f"var array<{'bool' if name == 'btmmEvHas' else 'int'}>  {name}" in code
            or (re.search(rf"var array<\w+>\s+{name}\s*=", code) is not None)
        ), name
        writes = re.findall(rf"array\.set\({name},", code)
        assert writes == [], f"{name} must never be assigned: {writes}"
        pushes = re.findall(rf"array\.push\({name},\s*([^)]+)\)", code)
        assert len(pushes) == 1, f"{name} should be seeded exactly once"
        assert pushes[0].strip() in {
            "false",
            "-1",
            "C_BTMM_CTX_PENDING",
            "C_BTMM_SESS_PENDING",
            "C_BTMM_VOL_PENDING",
            "C_BTMM_LQS_PENDING",
            "C_BTMM_SRC_NA",
        }, f"{name} seeded with a non-neutral value: {pushes[0]}"

    assert "array.get(btmmEvHas" in code, "the engine must read the channel"


def test_the_confirmation_branch_is_present() -> None:
    """The engine is complete. Removing confirmation to make the runtime tidy
    would be a different, lesser port."""
    code = _code(_p4_appendix())
    assert "C_BTMM_ST_CONFIRMED" in code
    assert "C_BTMM_TR_CONFIRMED" in code
    assert "f_btmmResolveGates" in code
    assert "state := C_BTMM_ST_CONFIRMED" in code


def test_final_gate_precedence_matches_production() -> None:
    """liquidity, then context, then session, then volume -- a setup failing two
    gates reports the first."""
    code = _code(_p4_appendix())
    body = code[code.index("f_btmmResolveGates") :]
    body = body[: body.index("f_btmmCancelTransition")]
    order = [
        body.index("C_BTMM_CANCEL_NO_LIQUIDITY"),
        body.index("C_BTMM_CANCEL_CONTEXT"),
        body.index("C_BTMM_CANCEL_SESSION"),
        body.index("C_BTMM_CANCEL_VOLUME"),
    ]
    assert order == sorted(order)


def test_derived_liquidity_writes_location_and_source_but_never_status() -> None:
    """A P3 false invalidation says WHERE liquidity was taken. Only review says
    THAT it was reviewed, and the gate reads the latter."""
    code = _code(_p4_appendix())
    derived = code[code.index("if hasFalseInv") :]
    derived = derived[: derived.index("if not array.get(btmmEvHas")]
    assert "lqLoc := C_BTMM_LQL_AFTER_POI" in derived
    assert "lqSrc := C_BTMM_SRC_RULE_BASED" in derived
    assert "lqStatus" not in derived

    # The status is only ever taken from the evidence record.
    assignments = re.findall(r"lqStatus := (\w+)", code)
    assert set(assignments) == {"evLiq"}, assignments


def test_only_one_liquidity_location_is_ported() -> None:
    text = _p4_appendix()
    names = [
        n
        for n in re.findall(r"^int (C_BTMM_LQL_\w+)\s*=", text, re.MULTILINE)
        if n != "C_BTMM_LQL_NA"
    ]
    assert names == ["C_BTMM_LQL_AFTER_POI"]


def test_rule_based_is_not_offered_as_a_reviewed_source() -> None:
    """RULE_BASED exists because derived liquidity carries it, but it must never
    appear as an evidence-channel source constant that could satisfy the gate."""
    code = _code(_p4_appendix())
    assert "C_BTMM_SRC_RULE_BASED" in code
    # The only assignment of the derived source is the derived-liquidity one.
    assert len(re.findall(r"lqSrc := C_BTMM_SRC_RULE_BASED", code)) == 1


# ---------------------------------------------------------------------------
# Structure and safety
# ---------------------------------------------------------------------------


def test_closed_bar_gate_is_present() -> None:
    code = _code(_p4_text())
    assert "if barstate.isconfirmed" in code
    driver = code[code.rindex("f_btmmSyncSetups()") :]
    assert "f_btmmAdvance(" in driver
    assert "f_btmmMaterializeAll()" in driver


def test_no_security_or_strategy_calls() -> None:
    code = _code(_p4_text())
    assert "request.security" not in code
    assert "request.security_lower_tf" not in code
    assert "strategy." not in code


def test_latest_transition_is_not_recomputed_by_sorting() -> None:
    """Production reduces the latest transition over walk-EMISSION order and
    sorts the public list only afterwards. A port that sorts and takes the last
    element disagrees on every bar carrying more than one transition -- and
    confirmation shares its bar with both reaction gates."""
    code = _code(_p4_appendix())
    assert "btmmTrLastCode" in code
    assert "array.sort(btmmTrLastCode" not in code
    # The only sort in the P4 section is the median helper.
    sorts = re.findall(r"array\.sort\((\w+)", code)
    assert set(sorts) <= {"ordered"}, sorts


def test_reaction_window_is_a_bounded_ring() -> None:
    code = _code(_p4_appendix())
    for name in ("btmmWinO", "btmmWinH", "btmmWinL", "btmmWinC", "btmmWinAtr"):
        assert f"array.push({name}, na)" in code
    assert "s * C_BTMM_REACTION_WINDOW_BARS" in code


def test_no_function_reassigns_a_global_scalar() -> None:
    """Pine forbids it, and it silently looks like working code until compile."""
    lines = _p4_text().splitlines()
    globals_: dict[str, int] = {}
    for i, line in enumerate(lines):
        match = re.match(r"^(?:var\s+)?(?:int|float|bool|string)\s+(\w+)\s*=", line)
        if match:
            globals_[match.group(1)] = i

    in_function = False
    offenders: list[str] = []
    for i, line in enumerate(lines):
        if re.match(r"^f_\w+\(", line):
            in_function = True
            continue
        if line and not line[0].isspace():
            in_function = False
        if in_function:
            match = re.match(r"\s+(\w+)\s*(?::=|\+=)", line)
            if match and match.group(1) in globals_:
                offenders.append(f"line {i + 1}: {line.strip()}")
    assert offenders == [], offenders
