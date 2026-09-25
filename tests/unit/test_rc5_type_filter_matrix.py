"""The 19 POI-type switches: mapping, all-on, all-off, and each one alone.

The filter works by ONE array lookup:

    array.get(p7zTypeOn, ty - 1)

so the whole matrix reduces to two questions that can be settled from source:

1. does position `code - 1` really hold the switch for that type?
2. is the lookup ANDed with the other gates, rather than able to override them?

If both hold, then "only FVG on" necessarily yields only FVGs, all-off yields
nothing, and all-on restores the current behaviour -- for all 19 switches at
once, without needing the chart. That is why this is a mapping test and not 19
UI screenshots.
"""

from __future__ import annotations

import re
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
_CORE = _REPO / "tradingview" / "btmm_poi_btrc_scanner_rc5_user.pine"

#: (input variable, display label, type code) in p7zTypeOn order.
EXPECTED: tuple[tuple[str, str, int], ...] = (
    ("tBuyOb", "BUY ORDER BLOCK", 1),
    ("tSellOb", "SELL ORDER BLOCK", 2),
    ("tBuyFvg", "BUY FVG", 3),
    ("tSellFvg", "SELL FVG", 4),
    ("tB2S", "BUY TO SELL CANDLE (B2S)", 5),
    ("tS2B", "SELL TO BUY CANDLE (S2B)", 6),
    ("tBaseRally", "BASE RALLY", 7),
    ("tBaseDrop", "BASE DROP", 8),
    ("tBullPw", "BULLISH PRESSURE WICK", 9),
    ("tBearPw", "BEARISH PRESSURE WICK", 10),
    ("tBullEng", "BULLISH ENGULFING", 11),
    ("tBearEng", "BEARISH ENGULFING", 12),
    ("tHammer", "HAMMER", 13),
    ("tShootStar", "SHOOTING STAR", 14),
    ("tMorning", "MORNING STAR", 15),
    ("tEvening", "EVENING STAR", 16),
    ("tSupport", "SUPPORT ZONE", 17),
    ("tResist", "RESISTANCE ZONE", 18),
    ("tDoji", "DOJI", 33),
)

#: Codes 19..32 -- the liquidity / reference family. Hardcoded false in
#: p7zTypeOn because they are NOT POI-zone types; they render through dspLiq.
LIQUIDITY_CODES = tuple(range(19, 33))


def _core() -> str:
    return _CORE.read_text(encoding="utf-8")


def _type_on_arguments() -> list[str]:
    line = next(
        raw for raw in _core().splitlines() if raw.startswith("p7zTypeOn")
    )
    inner = line.split("array.from(", 1)[1].rsplit(")", 1)[0]
    return [part.strip() for part in inner.split(",")]


def test_there_are_exactly_nineteen_switches_all_defaulting_true() -> None:
    core = _core()
    declared = re.findall(
        r"^(t[A-Za-z0-9]+)\s*=\s*input\.bool\((true|false),\s*\"([^\"]+)\"",
        core,
        re.MULTILINE,
    )
    grouped = [d for d in declared if d[0] in {e[0] for e in EXPECTED}]
    assert len(grouped) == 19, [d[0] for d in grouped]
    for name, default, label in grouped:
        assert default == "true", f"{name} does not default true"
        expected_label = next(e[1] for e in EXPECTED if e[0] == name)
        assert label == expected_label, (name, label, expected_label)


def test_EVERY_SWITCH_SITS_AT_ITS_OWN_TYPE_CODE() -> None:
    """THE mapping. Position `code - 1` must hold that type's switch.

    An off-by-one here would silently make one checkbox control a different
    POI family, which is the kind of defect nobody notices until a customer
    filters to one type and gets another.
    """
    args = _type_on_arguments()
    assert len(args) == 33, f"p7zTypeOn must have 33 entries, got {len(args)}"
    for variable, _label, code in EXPECTED:
        assert args[code - 1] == variable, (
            f"code {code} should be controlled by {variable}, "
            f"found {args[code - 1]}"
        )


def test_the_liquidity_family_is_hardcoded_off_in_the_zone_renderer() -> None:
    """Codes 19..32 are not POI-zone types. They belong to dspLiq."""
    args = _type_on_arguments()
    for code in LIQUIDITY_CODES:
        assert args[code - 1] == "false", (
            f"code {code} is a liquidity/reference type and must not be "
            f"switchable in the zone renderer, found {args[code - 1]}"
        )
    assert "dspLiq" in _core()


def test_the_filter_is_a_lookup_at_code_minus_one() -> None:
    assert "array.get(p7zTypeOn, ty - 1)" in _core()


def test_A_SWITCH_CAN_ONLY_PERMIT_NEVER_OVERRIDE() -> None:
    """ALL-ON must not resurrect anything.

    The eligibility test is a conjunction, so an enabled type still has to be
    lifecycle-valid, non-subordinate and not FVG-dominated. If the toggle were
    ever ORed in, a disabled-but-valid record could reappear -- or worse, an
    invalidated one.
    """
    line = next(
        raw
        for raw in _core().splitlines()
        if "array.get(p7zTypeOn, ty - 1)" in raw
        and "rc5Subordinate" in raw
    )
    assert "f_rc5Validity(pI) == C_RC5_VALID and" in line
    assert "not map.contains(rc5Subordinate, pI) and" in line
    assert "array.get(p7zTypeOn, ty - 1) and" in line
    assert " or " not in line.split("if ", 1)[1].split(" and array.get(p7zTypeOn")[0]


def test_all_off_leaves_no_zone_eligible() -> None:
    """With every switch false the lookup is false for every code, so the
    conjunction fails for every POI. Proven structurally: the only path that
    pushes into the visible set is guarded by that lookup."""
    pushes = [
        raw for raw in _core().splitlines() if "array.push(p7zVisibleIdx, pI)" in raw
    ]
    assert len(pushes) == 1, "more than one way into the visible set"
    block = _core().split("array.push(p7zVisibleIdx, pI)", 1)[0]
    guard = block.rsplit("if ", 1)[1]
    assert "array.get(p7zTypeOn, ty - 1)" in guard
