"""RC3 ORDER BLOCK leg-origin port in the USER and PARITY Pine builds.

Source locks mirroring ``poi/leg_origin.py`` and
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
def test_gate_is_the_leg_origin_of_each_structure_break(build: str) -> None:
    code = _code(build)
    assert "    p3Events := p2bEvents" in code  # this bar's frozen P2 breaks
    gate = code[code.index("f_poiGateOrderBlocks() =>") :]
    gate = gate[: gate.index("\nf_poiApplyPromotions() =>")]
    assert "for [_ek, ev] in p3Events" in gate
    # a break is gated on the bar it becomes available (never re-derived later
    # at the edge of the sliding analytical window)
    assert "if ev.availabilityTime == nowT" in gate
    assert "int want = bull ? SWING_LOW : SWING_HIGH" in gate
    # origin: extreme confirmed opposite swing between the broken swing and the
    # break candle, confirmed by the break; exact ties -> latest pivot
    assert (
        "s.swingType == want and sStart > ev.brokenSwingKey and "
        "s.pivotEndTime < ev.breakTime and "
        "s.meaningfulConfTime <= ev.availabilityTime and "
        "(na(best) or (bull ? s.price <= best : s.price >= best))"
    ) in gate
    # earliest pending raw formation on the origin swing, complete by the break
    assert (
        "r.srcFirstTime <= oEnd and r.srcLastTime >= oStart and "
        "r.availTime <= ev.availabilityTime and "
        "(pick < 0 or r.srcFirstTime < array.get(obPending, pick).srcFirstTime)"
    ) in gate
    assert "map.contains(obSwingUsed, oEnd + want)" in gate  # one OB per leg origin
    assert (
        "int avail = math.max(math.max(ob.availTime, oConf), "
        "math.max(ev.availabilityTime, nowT))"
    ) in gate  # never before this bar (immutable first appearance)
    assert (
        "f_poiEmit(ob.poiType, ob.direction, ob.zoneTop, ob.zoneBottom, "
        "ob.strengthTier, ob.srcFirstTime, 2, ob.srcLastTime, ob.candidateTime, avail)"
    ) in gate
    assert "f_poiFind(ob.poiType + 10," in gate  # the same formation's engulfing


@pytest.mark.parametrize("build", sorted(_BUILDS))
def test_no_emitted_poi_is_ever_removed(build: str) -> None:
    code = _code(build)
    gate = code[code.index("f_poiGateOrderBlocks() =>") :]
    gate = gate[: gate.index("\nf_poiApplyPromotions() =>")]
    # only pending raw formations are dropped; the registry is append-only
    assert "array.remove(obPending, pick)" in gate
    assert "array.shift(obPending)" in gate
    assert "array.remove(poi" not in code and "array.shift(poi" not in code


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
