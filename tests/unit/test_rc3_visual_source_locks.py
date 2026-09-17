"""Phase 30 visual mutation locks on the real RC3 USER Pine source.

The Python P7-Z model tests prove the presentation algorithm; these prove the
deployed Pine build still implements the RC3 visual contract, so a regression
cannot reappear silently in the script itself.
"""

from __future__ import annotations

import re
from pathlib import Path

_USER = (
    Path(__file__).resolve().parents[2]
    / "tradingview"
    / "btmm_poi_btrc_scanner_rc3_poi_semantics_dev.pine"
)
_SOURCE = _USER.read_text(encoding="utf-8")


def _code_only(text: str) -> str:
    return "\n".join(line.split("//")[0] for line in text.splitlines())


def _p7z_block() -> str:
    start = _SOURCE.index("P7-Z — POI zone visualization")
    end = _SOURCE.index("P9 — full-system integration trace")
    return _code_only(_SOURCE[start:end])


def test_no_independent_poi_label_object_exists_in_the_zone_block() -> None:
    block = _p7z_block()
    assert "label.new" not in block
    assert "label.set_" not in block
    assert "array<label>" not in block


def test_poi_name_is_box_native_and_centred_on_both_axes() -> None:
    block = _p7z_block()
    creates = re.findall(r"box\.new\((.*?)\)\n", block, flags=re.S)
    assert len(creates) == 1
    call = creates[0]
    assert "text = p7zBoxTxt" in call
    assert "text_halign = text.align_center" in call
    assert "text_valign = text.align_center" in call
    assert "xloc = xloc.bar_time" in call
    # Text must scale with the box so it cannot overflow the zone when the
    # chart is compressed (a fixed size overflowed in the live zoom test).
    assert "text_size = size.auto" in call
    # The extend path re-asserts the same text on the same box object.
    assert "box.set_text(array.get(p7zBoxes, slot), p7zBoxTxt)" in block


def test_every_displayed_box_carries_its_own_name() -> None:
    # Text is empty only when POI Text is switched off; no overlap/collision
    # rule may blank a displayed box (annotation integrity).
    block = _p7z_block()
    assert (
        'string p7zBoxTxt = p7zShowLabels ? p7zTfl + " • " + '
        'array.get(p7zGNames, p7zG) : ""'
    ) in block


def test_direction_colour_cannot_invert() -> None:
    block = _p7z_block()
    assert "color p7zHue = p7zBullish ? color.green : color.red" in block
    assert "bool p7zBullish = array.get(p7zGBull, p7zG)" in block
    for tint in ("p7zFillColor", "p7zBorderColor", "p7zTextColor"):
        assert re.search(rf"color {tint} = color\.new\(p7zHue, \d+\)", block), tint
    # Group direction comes from the POI direction code, never from type text.
    assert "array.push(p7zGBull, dr == C_POI_DIR_BULLISH)" in block
    assert "array.push(p7zGBull, wantDir == C_POI_DIR_BULLISH)" in block


def test_no_text_owner_collision_rule_remains() -> None:
    block = _p7z_block()
    assert "p7zOwner" not in block
    assert "p7zTextOwner" not in block
    assert "p7zComp" not in block


def test_objects_are_bounded_and_evicted() -> None:
    block = _p7z_block()
    assert "box.delete(array.get(p7zBoxes, k))" in block
    assert "array.indexof(p7zSelected, existingPoi) == -1" in block
    cap = re.search(
        r'p7zMaxVisibleZones\s*=\s*input\.int\(\d+, "[^"]*", minval = 1, maxval = (\d+)',
        _SOURCE,
    )
    boxes = re.search(r"max_boxes_count = (\d+)", _SOURCE)
    assert cap and boxes and int(cap.group(1)) <= int(boxes.group(1))


def test_tf_marker_is_only_the_formatter_fallback() -> None:
    code = _code_only(_SOURCE)
    formatter = code[code.index("f_p7zTfLabel(string p) =>") :]
    formatter = formatter[: formatter.index("f_p7PermColor")]
    assert code.count('"TF?"') == formatter.count('"TF?"')
    # Daily/weekly/monthly counted tokens are handled (the RC3 "1D" defect).
    assert 'sfx == "D" ? "D"' in formatter and 'sfx == "W" ? "W"' in formatter


def test_zone_build_is_live_last_bars_or_frozen_review_time_only() -> None:
    assert (
        "if p7zShowZones and (p7zAsOf == 0 ? bar_index >= p1DatasetBars - 2 : "
        "time_close <= p7zAsOf)"
    ) in _SOURCE
    assert (
        'p7zAsOf             = input.time(0, "Review zones as of (0 = live)"' in _SOURCE
    )
    # Review mode reads the same fresh-only eligible set; it cannot revive a
    # terminal zone because freshness is read at that bar, not recomputed.
    block = _p7z_block()
    assert "if array.get(poiFreshActive, pI)" in block


def test_fvg_sweep_state_is_array_held_not_loop_scalars() -> None:
    # Live M15 probe: scalar `:=` updates inside the FVG `for k` sweep read
    # back as their initial value on the next pass, so no FVG cluster was ever
    # flushed and no FVG was ever drawn. The cluster state must live in arrays.
    block = _p7z_block()
    sweep = block[
        block.index("for dirPass = 0 to 1") : block.index("map<string, int> p7zSlot")
    ]
    assert "array<float> cF = array.new<float>(2, na)" in sweep
    assert "array<int>   cI = array.new<int>(4, 0)" in sweep
    assert "int cN = array.get(cI, 2)" in sweep
    assert "array.set(cI, 2, cN + 1)" in sweep
    assert "if cN > 0 and (k == fn or bt > array.get(cF, 0))" in sweep
    for scalar in (
        "float cTop",
        "float cBot",
        "int cLeft",
        "int cKey",
        "bool cTerm",
        "int cType",
    ):
        assert scalar not in sweep, scalar
