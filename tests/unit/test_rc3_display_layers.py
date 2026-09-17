"""RC3 display layers on the real USER Pine source (presentation only).

Locks: the new toggles and their defaults, that they are read only by drawing
code, the independent dashboard / POI-table gates, the same-formation
dominance filter, the structure and BTMM overlays reading the frozen engines,
and the P8 debug log living only in the PARITY build.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from tests.parity_support.pine_semantic_core import semantic_core_sha256

_TV = Path(__file__).resolve().parents[2] / "tradingview"
_USER = (_TV / "btmm_poi_btrc_scanner_rc3_poi_semantics_dev.pine").read_text(
    encoding="utf-8"
)
_PARITY = (_TV / "btmm_poi_btrc_scanner_rc3_parity_dev.pine").read_text(
    encoding="utf-8"
)


def _code(text: str) -> list[str]:
    return [ln for ln in text.splitlines() if not ln.strip().startswith("//")]


def _p7z_block() -> str:
    start = _USER.index("P7-Z — POI zone visualization")
    end = _USER.index("P9 — full-system integration trace")
    return "\n".join(_code(_USER[start:end]))


# ---- the semantic-core extractor really separates semantics from drawing ----


@pytest.mark.parametrize(
    ("old", "new"),
    [
        (
            "float C_POI_OB_RATIO_STANDARD        = 2.0",
            "float C_POI_OB_RATIO_STANDARD        = 2.5",
        ),
        (
            'p5WBtmm       = input.int(3, "Weight: BTMM"',
            'p5WBtmm       = input.int(4, "Weight: BTMM"',
        ),
        ("        f_poiDetectFvg(p3Wn)\n", ""),
    ],
)
def test_semantic_core_detects_a_semantic_edit(old: str, new: str) -> None:
    assert old in _USER
    edited = _USER.replace(old, new, 1)
    assert semantic_core_sha256(edited) != semantic_core_sha256(_USER)


def test_semantic_core_ignores_a_drawing_edit() -> None:
    edited = _USER.replace("color.new(p7zHue, 90)", "color.new(p7zHue, 80)", 1)
    assert edited != _USER
    assert semantic_core_sha256(edited) == semantic_core_sha256(_USER)


# ---- toggles ----------------------------------------------------------------


@pytest.mark.parametrize(
    ("var", "default", "title"),
    [
        ("dspFvg", "true", "Show FVG"),
        ("dspSR", "true", "Show Support / Resistance"),
        ("dspMs", "false", "Show Market Structure (BOS / CHOCH / swings)"),
        ("dspBtmm", "false", "Show BTMM Lifecycle"),
        ("p7ShowUi", "true", "Show Dashboard"),
        ("p7ShowActivePois", "true", "Show POI Table"),
        ("p7zShowZones", "true", "Show POI Zones"),
        ("p7zShowLabels", "true", "Show POI Text"),
    ],
)
def test_display_toggle_exists_with_its_default(
    var: str, default: str, title: str
) -> None:
    assert re.search(
        rf'^{var}\s*=\s*input\.bool\({default},\s*"{re.escape(title)}', _USER, re.M
    ), var


@pytest.mark.parametrize("var", ["dspFvg", "dspSR", "dspMs", "dspBtmm"])
def test_new_toggles_are_read_only_by_drawing_code(var: str) -> None:
    uses = [
        ln
        for ln in _code(_USER)
        if re.search(rf"\b{var}\b", ln) and not re.match(rf"^{var}\s*=", ln)
    ]
    assert uses
    block = _p7z_block()
    for ln in uses:
        assert (
            ln in block
            or ln.strip().startswith("if dspMs and bar_index >= last_bar_index - 1")
            or ln.startswith("plotshape(dspBtmm")
        ), ln


def test_dashboard_and_poi_table_are_independent_gates() -> None:
    lines = _code(_USER)
    head = lines.index("if barstate.islast")
    body = lines[head + 1 :]
    assert "    if p7ShowUi" in body
    assert "    if p7ShowActivePois" in body
    assert "if barstate.islast and p7ShowUi" not in _USER
    table_new = [ln for ln in body if "table.new(" in ln]
    assert len(table_new) == 2 and all(ln.startswith("        ") for ln in table_new)


# ---- same-formation dominance -----------------------------------------------


def test_dominance_key_is_candle_identity_not_overlap() -> None:
    block = _p7z_block()
    key = "array.get(poiCandTime, pI) * array.get(poiDirection, pI)"
    assert f"map.put(p7zDom, {key}, true)" in block
    assert f"map.contains(p7zDom, {key})" in block
    assert "not (isFvg and (not dspFvg or map.contains(p7zDom," in block
    assert block.index("map<int, bool> p7zDom") < block.index("for dirPass = 0 to 1")


def test_support_resistance_filter_and_dashed_border() -> None:
    block = _p7z_block()
    assert "(dspSR or ty < C_POI_SUPPORT_ZONE)" in block
    assert (
        'border_style = str.contains(array.get(p7zGNames, p7zG), "ZONE") ? '
        "line.style_dashed : line.style_solid"
    ) in block


# ---- overlays read the frozen engines ---------------------------------------


def test_market_structure_overlay_draws_the_frozen_p2_events_and_p1_swings() -> None:
    code = "\n".join(_code(_USER))
    start = code.index("    if dspMs and bar_index >= last_bar_index - 1")
    overlay = code[start : code.index("\n    int sc = array.size(swings)", start)]
    assert "for [k, ev] in p2bEvents" in overlay
    assert "for [k, sw] in swings" in overlay
    assert 'math.abs(ev.transitionCode) == 2 ? "CHOCH" : "BOS"' in overlay
    assert "ev.transitionCode > 0 ? color.green : color.red" in overlay
    assert "f_p2" not in overlay and "=>" not in overlay


def test_btmm_overlay_is_a_small_marker_not_a_background() -> None:
    code = _code(_USER)
    assert not any(ln.startswith("bgcolor(") for ln in code)
    marks = [ln for ln in code if ln.startswith("plotshape(dspBtmm")]
    assert len(marks) == 1
    assert "location.bottom" in marks[0] and "size.tiny" in marks[0]
    assert "ta.change(array.get(p4Counts, C_P4_N_FINAL_GATE))" in _USER


def test_plot_budget_is_within_tradingviews_64() -> None:
    plots = sum(
        1
        for ln in _code(_USER)
        if re.match(r"^\s*(plot|plotshape|plotchar|bgcolor|barcolor|fill)\(", ln)
    )
    assert plots <= 64


# ---- P8 debug log moved to the capture build --------------------------------


def test_p8_debug_log_lives_only_in_the_parity_build() -> None:
    user_code = "\n".join(_code(_USER))
    assert "P8EVENT|" not in user_code and "P8PRIME|" not in user_code
    assert "p8DebugLog" not in user_code
    parity_code = "\n".join(_code(_PARITY))
    assert 'log.info("P8EVENT|type=POI_TERMINAL"' in parity_code
    assert 'log.info("P8PRIME|bar="' in parity_code
    assert 'alert("P8 POI_TERMINAL|"' in user_code
