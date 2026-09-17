"""RC3 ORDER BLOCK movement-origin port in the USER and PARITY Pine builds.

Source locks mirroring ``poi/order_blocks.apply_movement_origin_gate`` and
``poi/lifecycle.apply_order_block_promotion``. Runtime agreement with Python
needs a real capture; these guarantee the port is present, ordered correctly
and identical in both builds.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.parity_support.pine_semantic_core import capture_neutral_core

_TV = Path(__file__).resolve().parents[2] / "tradingview"
_BUILDS = {
    "USER": _TV / "btmm_poi_btrc_scanner_rc3_poi_semantics_dev.pine",
    "PARITY": _TV / "btmm_poi_btrc_scanner_rc3_parity_dev.pine",
}


def _code(name: str) -> str:
    text = _BUILDS[name].read_text(encoding="utf-8")
    return "\n".join(ln for ln in text.splitlines() if not ln.strip().startswith("//"))


def test_user_and_parity_semantic_cores_are_identical() -> None:
    cores = {
        name: capture_neutral_core(path.read_text(encoding="utf-8"))
        for name, path in _BUILDS.items()
    }
    assert cores["USER"] == cores["PARITY"]


@pytest.mark.parametrize("build", sorted(_BUILDS))
def test_formation_is_not_emitted_as_an_order_block_directly(build: str) -> None:
    code = _code(build)
    detector = code[code.index("f_poiDetectOrderBlocks(int wn) =>") :]
    detector = detector[: detector.index("\nf_poiDetectFvg(")]
    assert "f_poiEmit(" not in detector
    assert "array.push(obPending, PoiRec.new(typeCode, direction" in detector


@pytest.mark.parametrize("build", sorted(_BUILDS))
def test_gate_requires_a_confirmed_opposite_swing_on_the_formation(build: str) -> None:
    code = _code(build)
    gate = code[code.index("f_poiGateOrderBlocks() =>") :]
    gate = gate[: gate.index("\nf_poiApplyPromotions() =>")]
    assert (
        "int want = r.direction == C_POI_DIR_BULLISH ? SWING_LOW : SWING_HIGH"
    ) in gate
    assert "for [_gi, s] in p3Swings" in gate
    assert (
        "s.swingType == want and r.srcFirstTime <= s.pivotEndTime and "
        "r.srcLastTime >= array.get(wOpenT, s.pivotStartIdx)"
    ) in gate
    assert "s.meaningfulConfTime < conf" in gate  # earliest confirmation wins
    assert (
        "f_poiEmit(r.poiType, r.direction, r.zoneTop, r.zoneBottom, "
        "r.strengthTier, r.srcFirstTime, 2, r.srcLastTime, r.candidateTime, conf)"
    ) in gate  # source = origin formation, availability = confirmation
    assert "f_poiFind(r.poiType + 10," in gate  # the same formation's engulfing


@pytest.mark.parametrize("build", sorted(_BUILDS))
def test_promotion_keeps_an_earlier_terminal_cause(build: str) -> None:
    code = _code(build)
    promo = code[code.index("f_poiApplyPromotions() =>") :]
    promo = promo[: promo.index("\n\n")]
    assert (
        "if e >= 0 and (array.get(poiTermReason, e) == C_POI_TERM_NONE or "
        "array.get(poiTermTime, e) > t)"
    ) in promo
    assert "array.set(poiTermReason, e, C_POI_TERM_PROMOTED)" in promo
    assert "array.set(poiFreshActive, e, false)" in promo
    assert "int C_POI_TERM_PROMOTED    = 3" in code
    assert 'C_POI_TERM_PROMOTED    => "PROMOTED_TO_ORDER_BLOCK"' in code


@pytest.mark.parametrize("build", sorted(_BUILDS))
def test_gate_runs_before_and_promotion_after_the_lifecycle_advance(
    build: str,
) -> None:
    code = _code(build)
    order = [
        "        f_poiDetectReferenceZones()",
        "        f_poiGateOrderBlocks()",
        "        f_poiAdvanceAllLifecycles(confirmedBarCount - p3Wn, confirmedBarCount)",
        "        f_poiApplyPromotions()",
    ]
    positions = [code.index(line) for line in order]
    assert positions == sorted(positions)
    assert "    p3Swings := swings" in code


def test_terminal_code_matches_the_python_enum() -> None:
    from btmm_ai_scanner.poi.enums import PoiTerminalReason

    assert PoiTerminalReason.PROMOTED_TO_ORDER_BLOCK.value == "PROMOTED_TO_ORDER_BLOCK"
