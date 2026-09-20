"""P3-I1 — static contract tests for the Pine POI semantic foundation.

Pine cannot run locally, so these tests read
`tradingview/btmm_poi_btrc_scanner_p3_dev.pine` as source and assert the
structural guarantees the later slices depend on:

* P3 DEV is the frozen P2 DEV production scanner, byte-for-byte, with ONLY the
  indicator title changed, plus an appended P3 block — so no P1 or P2 semantic
  region can drift while P3 is built on top of it;
* the POI vocabulary matches the production Python enums exactly (all 32 types,
  the CORE/CONTEXT split, directions, tiers, all 11 lifecycle statuses);
* every ported configuration constant equals its `PoiConfiguration` default,
  including the displacement-leg thresholds that production hard-codes;
* the two dead lifecycle states are reserved but never assigned;
* the closed-bar gate is present, no `request.security` is introduced, and the
  semantic layer has no drawing-object dependency.
"""

from __future__ import annotations

import hashlib
import re
from decimal import Decimal
from pathlib import Path

from btmm_ai_scanner.poi.configuration import PoiConfiguration
from btmm_ai_scanner.poi.enums import (
    LIFECYCLE_ELIGIBLE_POI_TYPES,
    NOT_APPLICABLE_LIFECYCLE_POI_TYPES,
    PoiLifecycleStatus,
)
from btmm_ai_scanner.poi.transport_codes import (
    FROZEN_TRANSPORT_CODES,
    RC5_ONLY_TRANSPORT_CODES,
)

REPO = Path(__file__).resolve().parents[2]
P2_DEV = REPO / "tradingview" / "btmm_poi_btrc_scanner_v1.pine"
P3_DEV = REPO / "tradingview" / "btmm_poi_btrc_scanner_p3_dev.pine"

P2_DEV_SHA = "3d6d10df27e4150e6b693cb55bd32bb269478235eabfdf2fecd9aa23d96fa05b"
OLD_TITLE = "BTMM + POI + BTRC Scanner [P2 DEV]"
NEW_TITLE = "BTMM + POI + BTRC Scanner [P3 DEV]"
BANNER = "// P3 — POI SEMANTIC FOUNDATION  (P3-I1)"

_CONFIG = PoiConfiguration(minimum_price_tick=Decimal("0.01"))


def _p3_text() -> str:
    return P3_DEV.read_text(encoding="utf-8")


def _p3_appendix() -> str:
    """The appended block, extracted by proving the P2-prefix property."""
    p2 = P2_DEV.read_text(encoding="utf-8")
    p3 = _p3_text()
    expected_prefix = p2.replace(
        f'indicator("{OLD_TITLE}"', f'indicator("{NEW_TITLE}"', 1
    ).rstrip("\n")
    assert p3.startswith(expected_prefix), (
        "P3 DEV is NOT P2 DEV + title change + appendix: the frozen P1/P2 "
        "region differs"
    )
    return p3[len(expected_prefix) :]


def _code(text: str) -> str:
    """Source with comment-only lines removed."""
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
# P2 immutability
# ---------------------------------------------------------------------------


def test_p2_dev_source_is_untouched() -> None:
    assert hashlib.sha256(P2_DEV.read_bytes()).hexdigest() == P2_DEV_SHA


def test_p3_dev_is_p2_dev_plus_title_change_plus_appendix_only() -> None:
    appendix = _p3_appendix()
    assert BANNER in appendix
    assert appendix.index(BANNER) < 200, "appendix must open with its banner"


def test_p3_dev_declares_the_p3_title_and_keeps_the_p2_execution_horizon() -> None:
    first_line = next(
        line for line in _p3_text().splitlines() if line.startswith("indicator(")
    )
    assert NEW_TITLE in first_line
    assert OLD_TITLE not in first_line
    # The atomic P3 parity campaign reuses the proven 1800-bar horizon (AD-6).
    assert "calc_bars_count = 1800" in first_line


# ---------------------------------------------------------------------------
# Vocabulary: all 32 types, the CORE/CONTEXT split, directions, tiers
# ---------------------------------------------------------------------------


def _poi_type_codes(appendix: str) -> dict[str, int]:
    """The Pine code declared for each FROZEN PoiType, by exact name.

    Deliberately iterates ``FROZEN_TRANSPORT_CODES``, never the live ``PoiType``
    enum: this file pins a frozen artifact, so adding an RC5 type to the enum
    must not change what this test demands of it.
    """
    codes: dict[str, int] = {}
    for poi_type in FROZEN_TRANSPORT_CODES:
        matches = re.findall(
            rf"^int\s+C_POI_{poi_type.value}\s*=\s*(\d+)\s*$",
            appendix,
            re.MULTILINE,
        )
        assert len(matches) == 1, (
            f"expected exactly one Pine code for {poi_type.value}, found {len(matches)}"
        )
        codes[poi_type.value] = int(matches[0])
    return codes


def test_every_frozen_poi_type_has_exactly_one_pine_code() -> None:
    codes = _poi_type_codes(_p3_appendix())
    assert set(codes) == {t.value for t in FROZEN_TRANSPORT_CODES}
    assert len(set(codes.values())) == 32, "POI type codes must be distinct"
    assert sorted(codes.values()) == list(range(1, 33))


def test_frozen_pine_codes_match_the_frozen_python_transport_map() -> None:
    """The frozen Pine artifact and FROZEN_TRANSPORT_CODES are the same wire
    vocabulary. This is the regression that proves RC5 renumbered nothing."""
    codes = _poi_type_codes(_p3_appendix())
    assert codes == {t.value: c for t, c in FROZEN_TRANSPORT_CODES.items()}


def test_the_frozen_artifact_declares_no_rc5_type_code() -> None:
    """RC5 types have no transport-code declaration in the frozen Pine.

    Matches a code DECLARATION specifically: the frozen build legitimately
    contains ``C_POI_DOJI_BODY_EFF_STANDARD`` / ``_STRONG`` (the doji
    suppression thresholds that RC3 already used), which is not a type code.
    """
    appendix = _p3_appendix()
    for poi_type in RC5_ONLY_TRANSPORT_CODES:
        assert not re.search(
            rf"^int\s+C_POI_{poi_type.value}\s*=\s*\d+\s*$", appendix, re.MULTILINE
        )


def test_core_codes_are_exactly_the_lifecycle_eligible_types() -> None:
    appendix = _p3_appendix()
    core_min = _int_const("C_POI_CORE_TYPE_MIN", appendix)
    core_max = _int_const("C_POI_CORE_TYPE_MAX", appendix)
    assert (core_min, core_max) == (1, 18)
    frozen_eligible = LIFECYCLE_ELIGIBLE_POI_TYPES - set(RC5_ONLY_TRANSPORT_CODES)
    assert len(frozen_eligible) == 18
    assert len(NOT_APPLICABLE_LIFECYCLE_POI_TYPES) == 14

    codes = _poi_type_codes(appendix)
    core_names = {
        name for name, value in codes.items() if core_min <= value <= core_max
    }
    assert core_names == {t.value for t in frozen_eligible}
    context_names = set(codes) - core_names
    assert context_names == {t.value for t in NOT_APPLICABLE_LIFECYCLE_POI_TYPES}


def test_direction_codes_match_the_structure_vocabulary() -> None:
    appendix = _p3_appendix()
    assert _int_const("C_POI_DIR_BULLISH", appendix) == 1
    assert _int_const("C_POI_DIR_BEARISH", appendix) == -1


def test_strength_tier_codes_reserve_a_distinct_absent_value() -> None:
    """FVG and reference zones carry NO tier in production, so NA is real."""
    appendix = _p3_appendix()
    assert _int_const("C_POI_TIER_NA", appendix) == 0
    assert _int_const("C_POI_TIER_STANDARD", appendix) == 1
    assert _int_const("C_POI_TIER_STRONG", appendix) == 2


def test_every_production_lifecycle_status_has_a_pine_code() -> None:
    appendix = _p3_appendix()
    statuses = {
        m.group(1)
        for m in re.finditer(
            r"^int\s+C_POI_LC_([A-Z_]+)\s*=\s*\d+", appendix, re.MULTILINE
        )
    }
    assert statuses == {s.value for s in PoiLifecycleStatus}


# ---------------------------------------------------------------------------
# AD-2 — dead states reserved but never assigned
# ---------------------------------------------------------------------------


def test_dead_lifecycle_states_are_reserved_but_never_assigned() -> None:
    appendix = _p3_appendix()
    code = _code(appendix)
    for dead in ("C_POI_LC_RECLAIM_PENDING", "C_POI_LC_DISPLACEMENT_PENDING"):
        assert re.search(rf"^int\s+{dead}\s*=\s*\d+", appendix, re.MULTILINE), dead
        # the code defines the constant and never assigns it to anything
        assignments = re.findall(rf":=\s*{dead}\b", code)
        assert assignments == [], f"{dead} must never be assigned (AD-2)"
        pushes = re.findall(rf"array\.push\([^)]*{dead}", code)
        assert pushes == [], f"{dead} must never enter the registry (AD-2)"


def test_no_transition_code_exists_for_either_dead_state() -> None:
    appendix = _p3_appendix()
    assert not re.search(r"^int\s+C_POI_TR_RECLAIM_PENDING", appendix, re.MULTILINE)
    assert not re.search(
        r"^int\s+C_POI_TR_DISPLACEMENT_PENDING", appendix, re.MULTILINE
    )


# ---------------------------------------------------------------------------
# Configuration constants must equal the production defaults
# ---------------------------------------------------------------------------


def test_ported_configuration_constants_match_production_defaults() -> None:
    appendix = _p3_appendix()
    pairs: tuple[tuple[str, Decimal], ...] = (
        ("C_POI_OB_RATIO_STANDARD", _CONFIG.order_block_size_ratio_standard),
        ("C_POI_OB_RATIO_STRONG", _CONFIG.order_block_size_ratio_strong),
        ("C_POI_SMALL_CANDLE_STANDARD", _CONFIG.small_candle_ratio_standard),
        ("C_POI_SMALL_CANDLE_STRONG", _CONFIG.small_candle_ratio_strong),
        ("C_POI_BASE_HEIGHT_ATR_MULT", _CONFIG.base_height_atr_multiplier),
        ("C_POI_BASE_HEIGHT_DEP_MULT", _CONFIG.base_height_departure_multiplier),
        ("C_POI_BASE_MIDPOINT_DRIFT", _CONFIG.base_midpoint_drift_ratio),
        ("C_POI_BASE_OVERLAP_MIN", _CONFIG.base_overlap_ratio_minimum),
        ("C_POI_PW_SHARE_STANDARD", _CONFIG.pressure_wick_share_standard),
        ("C_POI_PW_BODY_EFF_STANDARD", _CONFIG.pressure_wick_body_efficiency_standard),
        ("C_POI_PW_DOMINANCE_STANDARD", _CONFIG.pressure_wick_dominance_standard),
        ("C_POI_PW_CLOSE_POS_STANDARD", _CONFIG.pressure_wick_close_position_standard),
        ("C_POI_PW_SHARE_STRONG", _CONFIG.pressure_wick_share_strong),
        ("C_POI_PW_BODY_EFF_STRONG", _CONFIG.pressure_wick_body_efficiency_strong),
        ("C_POI_PW_DOMINANCE_STRONG", _CONFIG.pressure_wick_dominance_strong),
        ("C_POI_PW_CLOSE_POS_STRONG", _CONFIG.pressure_wick_close_position_strong),
        ("C_POI_PW_RANGE_CONTEXT_STRONG", _CONFIG.pressure_wick_range_context_strong),
        (
            "C_POI_HSS_WICK_SHARE_STANDARD",
            _CONFIG.hammer_shooting_star_wick_share_standard,
        ),
        (
            "C_POI_HSS_BODY_EFF_STANDARD",
            _CONFIG.hammer_shooting_star_body_efficiency_standard,
        ),
        (
            "C_POI_HSS_OPP_WICK_STANDARD",
            _CONFIG.hammer_shooting_star_opposite_wick_standard,
        ),
        (
            "C_POI_HSS_WICK_SHARE_STRONG",
            _CONFIG.hammer_shooting_star_wick_share_strong,
        ),
        (
            "C_POI_HSS_BODY_EFF_STRONG",
            _CONFIG.hammer_shooting_star_body_efficiency_strong,
        ),
        (
            "C_POI_HSS_OPP_WICK_STRONG",
            _CONFIG.hammer_shooting_star_opposite_wick_strong,
        ),
        ("C_POI_DOJI_BODY_EFF_STANDARD", _CONFIG.doji_body_efficiency_standard),
        ("C_POI_DOJI_BODY_EFF_STRONG", _CONFIG.doji_body_efficiency_strong),
        ("C_POI_REV_RATIO_STANDARD", _CONFIG.reversal_candidate_size_ratio_standard),
        ("C_POI_REV_RATIO_STRONG", _CONFIG.reversal_candidate_size_ratio_strong),
        ("C_POI_REV_BODY_EFF_STANDARD", _CONFIG.reversal_body_efficiency_standard),
        ("C_POI_REV_BODY_EFF_STRONG", _CONFIG.reversal_body_efficiency_strong),
        ("C_POI_REV_CLOSE_POS_STANDARD", _CONFIG.reversal_close_position_standard),
        ("C_POI_REV_CLOSE_POS_STRONG", _CONFIG.reversal_close_position_strong),
        (
            "C_POI_CONTACT_TOL_ATR_MULT",
            _CONFIG.zone_contact_tolerance_atr_multiplier,
        ),
        (
            "C_POI_CONTACT_TOL_HEIGHT_MULT",
            _CONFIG.zone_contact_tolerance_zone_height_multiplier,
        ),
        (
            "C_POI_OVERSHOOT_TOL_ATR_MULT",
            _CONFIG.zone_overshoot_tolerance_atr_multiplier,
        ),
        (
            "C_POI_OVERSHOOT_TOL_HEIGHT_MULT",
            _CONFIG.zone_overshoot_tolerance_zone_height_multiplier,
        ),
    )
    for name, expected in pairs:
        assert _float_const(name, appendix) == expected, name

    assert _int_const("C_POI_BASE_MIN_CANDLES", appendix) == _CONFIG.base_min_candles
    assert _int_const("C_POI_BASE_MAX_CANDLES", appendix) == _CONFIG.base_max_candles
    assert (
        _int_const("C_POI_RECLAIM_WINDOW_BARS", appendix) == _CONFIG.reclaim_window_bars
    )
    assert (
        _int_const("C_POI_DISPLACEMENT_WINDOW_BARS", appendix)
        == _CONFIG.displacement_window_bars
    )


def test_displacement_leg_thresholds_match_the_hard_coded_production_values() -> None:
    """These live in lifecycle.py:262-267, NOT in PoiConfiguration."""
    appendix = _p3_appendix()
    assert _float_const("C_POI_LEG_FAST_SPEED", appendix) == Decimal("0.50")
    assert _float_const("C_POI_LEG_FAST_EFFICIENCY", appendix) == Decimal("0.60")
    assert _float_const("C_POI_LEG_FAST_SHARE", appendix) == Decimal("0.67")
    assert _float_const("C_POI_LEG_STRONG_SPEED", appendix) == Decimal("0.75")
    assert _float_const("C_POI_LEG_STRONG_EFFICIENCY", appendix) == Decimal("0.75")
    assert _float_const("C_POI_LEG_STRONG_SHARE", appendix) == Decimal("0.80")


def test_detector_dependency_window_is_the_pressure_wick_baseline_plus_one() -> None:
    """The widest detector need is the candle plus its 20-bar baseline."""
    appendix = _p3_appendix()
    assert _int_const("C_POI_PW_BASELINE_WINDOW", appendix) == 20
    assert _int_const("C_POI_MAX_DEPENDENCY_BARS", appendix) == 21
    assert _int_const("C_POI_REV_LOOKBACK", appendix) == 3
    assert _int_const("C_POI_REV_CONFIRM_WINDOW", appendix) == 3


# ---------------------------------------------------------------------------
# Records, registry and primitives
# ---------------------------------------------------------------------------


def test_geometry_and_lifecycle_are_separate_records() -> None:
    appendix = _p3_appendix()
    assert re.search(r"^type PoiRec$", appendix, re.MULTILINE)
    assert re.search(r"^type PoiLife$", appendix, re.MULTILINE)
    rec_block = appendix.split("type PoiRec")[1].split("type PoiLife")[0]
    life_block = appendix.split("type PoiLife")[1].split("// ---")[0]
    # geometry must not carry mutable lifecycle state
    for mutable in ("status", "terminal", "resumeIdx", "tapCount"):
        assert mutable not in rec_block, f"PoiRec must not hold {mutable}"
    # lifecycle must not duplicate immutable geometry
    for immutable in ("zoneTop", "zoneBottom", "poiType", "direction"):
        assert immutable not in life_block, f"PoiLife must not duplicate {immutable}"


def test_registry_is_append_only_and_never_deletes_semantic_records() -> None:
    """AD-5: no expiry, no truncation of semantic records."""
    code = _code(_p3_appendix())
    for banned in (
        "array.remove(poi",
        "array.shift(poi",
        "array.pop(poi",
        "array.clear(poi",
    ):
        assert banned not in code, f"registry must not use {banned} (AD-5)"
    assert "array.push(poiType" in code


def test_identity_uses_the_contiguous_source_run_and_no_uuid() -> None:
    """AD-1: identity is (type, first source time, count, last source time)."""
    appendix = _p3_appendix()
    code = _code(appendix)
    assert "f_poiSameIdentity" in code
    for field in ("srcFirstTime", "srcCount", "srcLastTime"):
        assert field in appendix, field
    assert "uuid" not in code.lower()


def test_price_normalisation_is_the_single_tick_conversion_point() -> None:
    code = _code(_p3_appendix())
    assert "f_poiTicks" in code
    assert "math.round(price / syminfo.mintick)" in code


def test_lifecycle_primitives_mirror_the_production_inequalities() -> None:
    """Strict breach, non-strict reclaim/displacement, inclusive touch."""
    code = _code(_p3_appendix())
    assert "(zoneBottom - closePrice) > overshootTol" in code
    assert "(closePrice - zoneTop) > overshootTol" in code
    assert "closePrice >= zoneBottom + contactTol" in code
    assert "closePrice <= zoneTop - contactTol" in code
    assert "closePrice >= zoneTop + contactTol" in code
    assert "closePrice <= zoneBottom - contactTol" in code
    assert (
        "candleLow <= array.get(poiZoneTop, i) and candleHigh >= "
        "array.get(poiZoneBottom, i)" in code
    )


def test_tolerance_reproduces_the_zero_height_fallback_and_tick_floor() -> None:
    code = _code(_p3_appendix())
    assert "zoneHeight > 0 ? heightMult * zoneHeight : boundA" in code
    assert "math.max(2 * syminfo.mintick, math.min(boundA, boundB))" in code


# ---------------------------------------------------------------------------
# Safety gates
# ---------------------------------------------------------------------------


def test_closed_bar_gate_is_present_and_realtime_state_is_never_mutated() -> None:
    code = _code(_p3_appendix())
    assert "if barstate.isconfirmed" in code
    assert "barstate.isrealtime" not in code


def test_p3_introduces_no_request_security_call() -> None:
    code = _code(_p3_text())
    assert "request." not in code


def test_semantic_layer_has_no_drawing_object_dependency() -> None:
    code = _code(_p3_appendix())
    for drawing in ("box.new", "line.new", "label.new", "table.new", "plot("):
        assert drawing not in code, f"P3 semantics must not depend on {drawing}"


def test_p3_contains_no_trading_or_execution_surface() -> None:
    """No strategy/order/alert surface.

    `order.ascending` is a Pine SORT enum used by the frozen P1 median helper,
    so the check targets real execution calls rather than the bare token.
    """
    code = _code(_p3_text())
    for banned in (
        "strategy.",
        "alertcondition(",
        "order.new",
        "order.cancel",
        "request.security",
    ):
        assert banned not in code, f"P3 DEV must not contain {banned}"


# ---------------------------------------------------------------------------
# Declaration order — Pine resolves identifiers in source order
# ---------------------------------------------------------------------------


def test_every_registry_array_is_declared_before_it_is_used() -> None:
    """TradingView rejected an earlier build with

        Error at 2575:16  Undeclared identifier "poiReported"

    because `f_poiAppend` sits in the foundation but pushed to arrays that were
    introduced further down the file. Pine has no forward declarations, so this
    guard fails locally instead of at the compile gate.
    """
    lines = _p3_text().splitlines()
    declarations: dict[str, int] = {}
    for index, line in enumerate(lines):
        match = re.match(r"^var array<[^>]+>\s+(\w+)\s*=", line)
        if match:
            declarations.setdefault(match.group(1), index)

    poi_arrays = {name for name in declarations if name.startswith("poi")}
    assert len(poi_arrays) >= 30, f"expected the full registry, saw {len(poi_arrays)}"

    problems: list[str] = []
    for index, line in enumerate(lines):
        if line.strip().startswith("//"):
            continue
        for used in re.findall(r"array\.\w+\(\s*(\w+)", line):
            if used in declarations and index < declarations[used]:
                problems.append(
                    f"{used} used on line {index + 1} but declared on "
                    f"line {declarations[used] + 1}"
                )
    assert not problems, "; ".join(problems)


def test_the_downstream_relevance_helper_follows_its_constants() -> None:
    """It reads two C_POI_TR_* codes, so it must come after them."""
    text = _p3_text()
    helper = text.index("f_poiIsDownstreamRelevant(int code) =>")
    for constant in (
        "int C_POI_TR_FALSE_INVALIDATION_CONFIRMED",
        "int C_POI_TR_GENUINE_INVALIDATION_CONFIRMED",
    ):
        assert text.index(constant) < helper, constant


#: Every P3 entry point that MUST be reachable from the bar loop. Detection and
#: the lifecycle walk are pure functions, so defining them proves nothing about
#: runtime: the whole engine can be present, correct and never execute.
_MUST_BE_CALLED = (
    "f_poiDetectOrderBlocks",
    "f_poiDetectFvg",
    "f_poiDetectEngulfing",
    "f_poiDetectStars",
    "f_poiDetectSingleCandleReversals",
    "f_poiDetectPressureWicks",
    "f_poiDetectReversalCandles",
    "f_poiDetectBases",
    "f_poiDetectReferenceZones",
    "f_poiAdvanceAllLifecycles",
)


def _call_sites(text: str, name: str) -> list[int]:
    """Line numbers where `name` is CALLED rather than defined."""
    sites: list[int] = []
    for number, line in enumerate(text.splitlines(), 1):
        code = line.split("//", 1)[0]
        if name not in code:
            continue
        if re.match(rf"\s*{name}\s*\(.*\)\s*=>", code):
            continue  # the definition
        if re.search(rf"(?<![A-Za-z0-9_]){name}\s*\(", code):
            sites.append(number)
    return sites


def test_every_p3_entry_point_is_actually_called() -> None:
    """A defined-but-never-called engine is an empty registry at runtime.

    This is the regression guard for the P3-ACCEL-3 finding: the detectors and
    the lifecycle walk were fully implemented and parity-verified, but nothing
    invoked them, so every real execution produced nregistry=0 while the whole
    synthetic suite stayed green. Synthetic tests drive the Python
    transcription directly and can never catch that; only a call-site check on
    the Pine source can.
    """
    text = _p3_text()
    uncalled = [name for name in _MUST_BE_CALLED if not _call_sites(text, name)]
    assert not uncalled, (
        "P3 functions are defined but never called, so the registry can only "
        f"ever be empty at runtime: {uncalled}"
    )


def test_the_driver_runs_only_on_confirmed_bars() -> None:
    """A forming bar must never mutate P3 state."""
    text = _p3_text()
    marker = "// P3-I8 — PER-BAR DRIVER"
    assert marker in text, "the P3 per-bar driver block is missing"
    driver = text[text.index(marker) :]
    assert "if barstate.isconfirmed" in driver
    for name in _MUST_BE_CALLED:
        assert _call_sites(driver, name), f"{name} is not called from the driver"


def test_no_for_loop_can_iterate_backwards_off_a_clamped_window() -> None:
    """Pine's `for` counts DOWN when `to` < `from`; Python's range() is empty.

    Every P3 window bound is built with `math.min(start + k, n)`, so whenever the
    window is incomplete the bound collapses to `start` and `to` becomes
    `start - 1`. Python does nothing; Pine walks BACKWARDS off the end of the
    window and reads index `n`, which is exactly the RE10045 array-bounds fault
    the first driver build hit on bar 9. Any such loop must clamp its bound with
    `math.max(<from>, ...)` and gate its body.
    """
    lines = _p3_text().splitlines()
    clamped_vars: set[str] = set()
    for line in lines:
        code = line.split("//", 1)[0]
        assigned = re.match(r"\s*(?:int\s+)?(\w+)\s*:?=\s*math\.min\(", code)
        if assigned:
            clamped_vars.add(assigned.group(1))

    offenders: list[str] = []
    for number, line in enumerate(lines, 1):
        code = line.split("//", 1)[0]
        loop = re.search(r"\bfor\s+\w+\s*=\s*(.+?)\s+to\s+(.+?)\s*$", code)
        if not loop:
            continue
        upper = loop.group(2).strip()
        bound = re.match(r"(\w+)\s*-\s*1$", upper)
        if bound and bound.group(1) in clamped_vars:
            offenders.append(f"line {number}: {code.strip()}")

    assert not offenders, (
        "these loops use an unclamped `math.min` bound and will iterate "
        "BACKWARDS when the window is incomplete:\n" + "\n".join(offenders)
    )


def test_the_driver_detects_before_advancing_lifecycles() -> None:
    """The model's per-bar order: run_frontier, then cursor.advance."""
    text = _p3_text()
    driver = text[text.index("// P3-I8 — PER-BAR DRIVER") :]
    advance = _call_sites(driver, "f_poiAdvanceAllLifecycles")[0]
    for name in _MUST_BE_CALLED:
        if name == "f_poiAdvanceAllLifecycles":
            continue
        assert _call_sites(driver, name)[0] < advance, (
            f"{name} must run before the lifecycle advance"
        )
