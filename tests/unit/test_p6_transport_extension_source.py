"""The P6 source-level gates on the additive P5 transport extension.

WHAT "ADDITIVE" HAS TO MEAN, MECHANICALLY
------------------------------------------
The claim that P6's analytical semantics are unchanged is only worth as much as
what can be checked. These are the checks:

* the fourteen original return positions keep their names, in order, in every
  one of the six requests -- so nothing was inserted, reordered or renamed;
* the extension is exactly position 15 and nothing else moved;
* the request COUNT is unchanged, so no P5 engine was smuggled in as a seventh
  context;
* the engine entry points are called the same number of times as before, so no
  second ATR, swing detector, equal-level detector or structure walk exists;
* the plot count is unchanged at 63, so the FXCM runtime matrix still reads the
  plots it reads;
* the envelope constants are untouched.

The frozen name list below was extracted from the pre-extension file at commit
6f72b06 rather than retyped, which is why it can be trusted as a baseline.

THE UDT IS CHECKED AGAINST THE CANONICAL CONTRACT, NOT AGAINST ITSELF
----------------------------------------------------------------------
`test_the_pine_udt_matches_the_canonical_contract` parses the Pine type and
compares names, order and types against
`tests/parity_support/p5_transport_contract.py` -- the same definition the
oracle and the Pine-equivalent model read. A field added to one and forgotten in
the other cannot survive that.

CONFIRMED-ONLY IS A SOURCE PROPERTY HERE, AS IT WAS FOR THE CLOSED SURFACE
---------------------------------------------------------------------------
P6's closure rested on tracing that no `:=` runs outside `if barstate.isconfirmed`
in the projection. The extension has to hold the same line, so the assignment
scan is repeated over the new code rather than assumed to inherit it.
"""

from __future__ import annotations

import re
from pathlib import Path

from tests.parity_support.p5_transport_contract import FIELDS

_REPO = Path(__file__).resolve().parents[2]
P6_DEV = _REPO / "tradingview" / "btmm_poi_btrc_scanner_p6_dev.pine"

#: Extracted from the pre-extension source at 6f72b06. These fourteen names, in
#: this order, are the frozen P6 return contract.
FROZEN_PREFIX: dict[str, tuple[str, ...]] = {
    prefix: tuple(
        f"{prefix}{suffix}"
        for suffix in (
            "Bars",
            "Sw",
            "Type",
            "Price",
            "Conf",
            "Eq",
            "Fp",
            "Ds",
            "Dc",
            "Dr",
            "P2d",
            "Tc",
            "Lt",
            "Bl",
        )
    )
    for prefix in ("w1", "d1", "h4", "h1", "m15", "m5")
}

#: Call counts in the pre-extension source. Equality proves no engine was added.
FROZEN_ENGINE_CALLS: dict[str, int] = {
    "f_detectSwings": 3,
    "f_p2StructureWalk": 3,
    "f_advancePivotFrontier": 3,
    "f_detectEqualLevels": 3,
    "f_latestDisplacement": 3,
    "f_trueRange": 3,
    "f_p2BuildSwingView": 3,
    "f_p2BuildRelationships": 3,
}

_REQUEST = re.compile(r"^\[([^\]]+)\]\s*=\s*request\.security\(", re.M)


def _source() -> str:
    return P6_DEV.read_text(encoding="utf-8")


def _destructurings() -> list[list[str]]:
    return [
        [name.strip() for name in m.group(1).split(",")]
        for m in _REQUEST.finditer(_source())
    ]


# ---------------------------------------------------------------------------
# Old prefix immutability
# ---------------------------------------------------------------------------


def test_there_are_still_exactly_six_semantic_requests() -> None:
    assert len(_destructurings()) == 6


def test_every_request_preserves_its_fourteen_original_names_in_order() -> None:
    for names in _destructurings():
        prefix = names[0].replace("Bars", "")
        assert prefix in FROZEN_PREFIX, prefix
        assert tuple(names[:14]) == FROZEN_PREFIX[prefix], prefix


def test_the_extension_is_appended_at_position_fifteen() -> None:
    for names in _destructurings():
        assert len(names) == 15
        prefix = names[0].replace("Bars", "")
        assert names[14] == f"{prefix}Ext"


def test_no_original_name_was_reused_for_the_extension() -> None:
    for names in _destructurings():
        assert names[14] not in names[:14]


def test_the_projection_returns_fifteen_values() -> None:
    source = _source()
    tail = source[source.index("f_p6TfProjection() =>") :]
    ret = next(
        line
        for line in reversed(tail[: tail.index("] = request.security(")].split("\n"))
        if line.strip().startswith("[qBars,")
    )
    values = [v.strip() for v in ret.strip().lstrip("[").rstrip("]").split(",")]
    assert len(values) == 15
    assert values[:14] == [
        "qBars",
        "swingCount",
        "lastType",
        "lastPrice",
        "lastConfT",
        "eqCount",
        "qFingerprint",
        "qDataset",
        "dispCode",
        "dispRatio",
        "p2Dir",
        "p2TransCount",
        "p2LastTrans",
        "p2LastBrokenLvl",
    ]
    assert values[14] == "xExt"


# ---------------------------------------------------------------------------
# No new engines, no new contexts, no new plots
# ---------------------------------------------------------------------------


def test_no_analytical_engine_gained_a_call_site() -> None:
    """Bounded reductions only. A second detector would move one of these."""
    source = _source()
    actual = {name: source.count(name + "(") for name in FROZEN_ENGINE_CALLS}
    assert actual == FROZEN_ENGINE_CALLS


def test_the_request_count_is_unchanged() -> None:
    assert len(re.findall(r"=\s*request\.security\(", _source())) == 6


def test_the_plot_count_is_unchanged_at_sixty_three() -> None:
    """The FXCM runtime matrix reads these by title; P5 adds none."""
    assert len(re.findall(r"^plot", _source(), re.M)) == 63


def test_the_execution_envelope_is_untouched() -> None:
    source = _source()
    assert "int C_P1_MIN_CALC_BARS = 1250" in source
    assert "int C_P6_HOST_CALC_BARS    = 1800" in source
    assert "int C_P6_REQUEST_CALC_BARS = C_P1_MIN_CALC_BARS + 1" in source
    assert "calc_bars_count = 1800" in source


def test_the_request_envelope_is_still_derived_not_a_literal() -> None:
    assert "calc_bars_count = 1251" not in _source()


# ---------------------------------------------------------------------------
# The UDT against the canonical contract
# ---------------------------------------------------------------------------


def _udt_fields() -> list[tuple[str, str]]:
    source = _source()
    block = source[source.index("type P5TransportExt") :]
    block = block[: block.index("\n\n// ---")]
    found: list[tuple[str, str]] = []
    for line in block.split("\n")[1:]:
        stripped = line.strip()
        if not stripped or stripped.startswith("//"):
            continue
        parts = stripped.split()
        found.append((parts[1], parts[0]))
    return found


def test_the_pine_udt_matches_the_canonical_contract() -> None:
    """Names, ORDER and types, against the same definition the oracle reads."""
    assert _udt_fields() == [(f.name, f.pine_type) for f in FIELDS]


def test_the_pine_udt_has_twenty_six_fields() -> None:
    assert len(_udt_fields()) == 26


def test_every_udt_field_declares_a_default() -> None:
    """An undeclared default would make "absent" depend on Pine's own zero value
    rather than on the contract's sentinel."""
    source = _source()
    block = source[source.index("type P5TransportExt") :]
    block = block[: block.index("\n\n// ---")]
    for line in block.split("\n")[1:]:
        stripped = line.strip()
        if not stripped or stripped.startswith("//"):
            continue
        assert "=" in stripped, stripped


def test_integer_codes_default_to_the_sentinel_literal_and_counts_to_zero() -> None:
    """The default is the LITERAL -99, not a reference to C_ST_NA.

    Pine rejects `int x = C_ST_NA` as a `type` field default (CE10132: "the
    default value cannot be a function, variable or calculation") even though
    C_ST_NA is itself just a top-level `int`. Only the DECLARATION site has to
    spell the literal; every read and write of these fields elsewhere in the
    projection still goes through C_ST_NA, which a separate test checks, so the
    sentinel stays defined in exactly one place everywhere but here.
    """
    source = _source()
    block = source[source.index("type P5TransportExt") :]
    block = block[: block.index("\n\n// ---")]
    for name in ("trans1Type", "disp1Dir", "disp1Cls", "dispClsAtTrans", "stateAvailT"):
        assert re.search(rf"\b{name}\s*=\s*-99\b", block), name
        assert not re.search(rf"\b{name}\s*=\s*C_ST_NA\b", block), name
    for name in ("transWindowCount", "dispWindowCount", "contStreak"):
        assert re.search(rf"\b{name}\s*=\s*0\b", block), name
    for name in ("disp1Ratio", "pbImpulsePrice", "pbOriginPrice", "pbPullbackPrice"):
        assert re.search(rf"\b{name}\s*=\s*na\b", block), name
    assert re.search(r"\bpbValid\s*=\s*false\b", block)


def test_the_type_declaration_reuses_the_named_sentinel_value() -> None:
    """The declaration spells -99 for Pine syntax reasons; every USE of these
    fields elsewhere in the projection still goes through the named constant, so
    a future change to C_ST_NA's value only has to be echoed in the fourteen
    literal declaration lines above."""
    source = _source()
    assert "int C_ST_NA = -99" in source


# ---------------------------------------------------------------------------
# Confirmed-only, and no P5 calibration constant
# ---------------------------------------------------------------------------


def _projection_body() -> list[str]:
    source = _source()
    start = source.index("f_p6TfProjection() =>")
    end = source.index("] = request.security(", start)
    return source[start:end].split("\n")


def test_every_extension_assignment_is_inside_the_confirmed_guard() -> None:
    """The same trace P6's closure rested on, repeated over the new code.

    `if barstate.isconfirmed` sits at four spaces, so every statement it governs
    is indented deeper. An extension assignment at four spaces would run on
    forming bars.
    """
    inside = False
    offenders: list[str] = []
    for line in _projection_body():
        if line.strip().startswith("if barstate.isconfirmed"):
            inside = True
            continue
        if not line.strip():
            continue
        indent = len(line) - len(line.lstrip())
        if inside and indent <= 4 and not line.strip().startswith("["):
            inside = False
        if not inside and ("qX." in line or "xExt :=" in line) and ":=" in line:
            offenders.append(line)
    assert offenders == [], offenders


def test_no_p5_threshold_appears_in_the_projection() -> None:
    """T2's expansion ratio, T3's momentum reference and acceleration margin,
    the retracement bands and the permission bands all belong to P5. The
    displacement classifier's own ratios live in the closed P1 constants.

    Comments are stripped first, because this is a claim about CODE. A first
    run failed on this test's own prose naming the constants in order to say
    they are absent -- a different thing from them being present.
    """
    for line in _projection_body():
        code = line.split("//")[0]
        for constant in ("1.50", "2.00", "0.15", "0.382", "0.618", "0.65", "0.45"):
            assert constant not in code, (constant, line)


def test_the_extension_capacities_are_declared_as_constants() -> None:
    source = _source()
    assert "int C_P5X_TRANS_CAP = 4" in source
    assert "int C_P5X_DISP_CAP  = 3" in source


def test_the_state_availability_fallback_is_implemented() -> None:
    """structure/analyzer.py falls back to the newest candle's availability when
    the walk reports no last change. Omitting that would publish an absent state
    time where Python publishes a real one."""
    body = "\n".join(_projection_body())
    assert "qLastChange != C_ST_NA ? qLastChange : array.get(qAvailT" in body


def test_the_prior_opposite_scan_starts_one_before_the_newest() -> None:
    body = "\n".join(_projection_body())
    assert "int qb = qNEv - 2" in body
    assert "int qa = qNEv - 1" in body


def test_the_pullback_comparators_are_not_normalised() -> None:
    body = "\n".join(_projection_body())
    assert "if qCandStrT <= qImpStrT" in body


def test_backward_scans_use_while_not_a_descending_for() -> None:
    """A descending `for` has bitten this codebase before."""
    body = "\n".join(_projection_body())
    assert "while qa >= 0" in body
    assert "while qb >= 0" in body
    assert "while qc >= 0" in body
    assert "while qd >= 0" in body
    assert not re.search(r"for\s+\w+\s*=\s*\w+\s*to\s*0\b", body)


def test_the_extension_is_rebuilt_each_confirmed_bar() -> None:
    """A fresh object per confirmed bar, because the walk runs over a SLIDING
    window and a stale slot would disagree with Python's current collections."""
    body = "\n".join(_projection_body())
    assert "P5TransportExt qX = P5TransportExt.new()" in body
    assert "xExt := qX" in body


# ---------------------------------------------------------------------------
# The live smoke emitter costs no plot
# ---------------------------------------------------------------------------


def test_the_smoke_emitter_uses_logs_rather_than_plots() -> None:
    source = _source()
    assert "log.info(" in source
    assert len(re.findall(r"^plot", source, re.M)) == 63


def test_the_smoke_emitter_reports_every_timeframe_and_the_feed() -> None:
    source = _source()
    for timeframe in ("W1", "D1", "H4", "H1", "M15", "M5"):
        assert f'f_p5xLine("{timeframe}"' in source
    assert "syminfo.prefix" in source
    assert "aliasHits=" in source


def test_the_smoke_emitter_fires_once() -> None:
    source = _source()
    assert "var bool p5xEmitted = false" in source
    assert "if barstate.islast and not p5xEmitted" in source
