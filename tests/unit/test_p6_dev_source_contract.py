"""The P6 source must inherit P4 and keep the architecture the lab measured.

Two things this file is really guarding.

**Inheritance.** P6 DEV is P4 DEV verbatim plus an appended section, so the
requested contexts CALL the closed P1 functions rather than re-implementing
them. `f_advancePivotFrontier`, `f_detectSwings` and `f_detectEqualLevels` were
verified to reference zero of the file's 174 global `var`s -- they are pure
functions of their array arguments -- which is exactly what makes handing them a
requested context's own arrays sound. A second, divergent definition of P1 would
be the easiest and worst mistake available here, and would not fail loudly
anywhere.

**The history architecture.** Host at 1800, each request at 1250. Those look
contradictory and are not: the host runs over max(indicator, largest request),
and 1250 sits below 1800. Drop the per-request argument and each context clamps
to the host's TIME span -- two weekly bars on an M15 host, against the 1250
required -- silently.

Assertions are scoped to the appended P6 section wherever P4's own code could
otherwise satisfy them.
"""

from __future__ import annotations

import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
P4_DEV = REPO / "tradingview" / "btmm_poi_btrc_scanner_p4_dev.pine"
P6_DEV = REPO / "tradingview" / "btmm_poi_btrc_scanner_p6_dev.pine"

BANNER = "// P6 — CROSS-TIMEFRAME SUBSTRATE"


def _text() -> str:
    return P6_DEV.read_text(encoding="utf-8")


def _section() -> str:
    text = _text()
    assert BANNER in text, "P6 section banner missing"
    return text[text.index(BANNER) :]


def _strip_comments(source: str) -> str:
    return "\n".join(
        line for line in source.splitlines() if not line.strip().startswith("//")
    )


def _section_code() -> str:
    return _strip_comments(_section())


# ---------------------------------------------------------------------------
# Inheritance, not a fork
# ---------------------------------------------------------------------------


def test_p6_is_p4_verbatim_plus_an_appended_section() -> None:
    p4 = P4_DEV.read_text(encoding="utf-8")
    expected_prefix = p4.replace("[P4 DEV]", "[P6 DEV]", 1)
    assert _text().startswith(expected_prefix), (
        "P6 DEV no longer contains P4 DEV verbatim; the P1/P2 semantics it "
        "calls may have forked"
    )


def test_the_projection_calls_the_closed_p1_functions() -> None:
    code = _section_code()
    for call in ("f_advancePivotFrontier(", "f_detectSwings(", "f_detectEqualLevels("):
        assert call in code, call


def test_the_section_defines_no_rival_p1_implementation() -> None:
    """Calling is fine; redefining is the failure this guards."""
    section = _section()
    for definition in (
        "\nf_advancePivotFrontier(array",
        "\nf_detectSwings(array",
        "\nf_detectEqualLevels(array",
    ):
        assert definition not in section, definition


def test_the_context_uses_its_own_arrays_not_the_hosts() -> None:
    """Handing a requested context the HOST's window arrays would project host
    data onto every timeframe while looking perfectly reasonable."""
    code = _section_code()
    call = re.search(r"f_detectSwings\(([^)]*)\)", code)
    assert call, "expected a f_detectSwings call in the P6 section"
    args = [a.strip() for a in call.group(1).split(",")]
    assert all(a.startswith("q") for a in args if a[:1].isalpha()), args
    for host_array in ("wHigh", "wLow", "wAtr", "pvAbs", "pvPrice"):
        assert host_array not in args, host_array


# ---------------------------------------------------------------------------
# The measured history architecture
# ---------------------------------------------------------------------------


def test_host_envelope_is_1800() -> None:
    assert "int C_P6_HOST_CALC_BARS    = 1800" in _section_code()
    assert re.search(
        r"indicator\([^)]*calc_bars_count = 1800", _strip_comments(_text()), re.S
    )


def test_every_request_uses_the_derived_envelope() -> None:
    code = _section_code()
    assert "int C_P6_REQUEST_CALC_BARS = C_P1_MIN_CALC_BARS + 1" in code
    calls = re.findall(r"request\.security\([^\n]*", code)
    assert len(calls) == 6, f"expected six requested contexts, found {len(calls)}"
    for call in calls:
        assert "calc_bars_count = C_P6_REQUEST_CALC_BARS" in call, call


def test_request_count_is_below_the_host_envelope() -> None:
    """If this ever inverts, the host follows the request and P1-P4 quietly
    leave the horizon they were validated on."""
    text = _strip_comments(_text())
    host = int(re.search(r"C_P6_HOST_CALC_BARS\s+=\s+(\d+)", text).group(1))
    minimum = int(re.search(r"C_P1_MIN_CALC_BARS = (\d+)", text).group(1))
    assert minimum + 1 < host, (minimum, host)


def test_exactly_the_six_authority_timeframes_are_requested() -> None:
    code = _section_code()
    requested = re.findall(r"request\.security\(syminfo\.tickerid, (\w+),", code)
    assert set(requested) == {
        "C_P6_TF_W1",
        "C_P6_TF_D1",
        "C_P6_TF_H4",
        "C_P6_TF_H1",
        "C_P6_TF_M15",
        "C_P6_TF_M5",
    }
    assert len(requested) == 6


def test_no_m1_context_exists() -> None:
    """P4's set is {M1, M5, M15}; P5's authority set contains no M1 at all."""
    code = _section_code()
    assert "C_P6_TF_M1 " not in code
    assert not re.search(r'C_P6_TF_\w+\s*=\s*"1"', code)


# ---------------------------------------------------------------------------
# The transport exclusions
# ---------------------------------------------------------------------------


def test_the_excluded_surfaces_are_absent_from_the_section() -> None:
    """S/R and trendlines are leaves (test_p6_dependency_closure), so omitting
    them cannot change a required value -- and it skips the machinery that
    dominated P3."""
    for excluded in ("support_resistance", "trendline", "swing_relationship"):
        offending = [
            line
            for line in _section().splitlines()
            if excluded in line.lower() and not line.strip().startswith("//")
        ]
        assert offending == [], offending


# ---------------------------------------------------------------------------
# Guards and hygiene
# ---------------------------------------------------------------------------


def test_isolation_is_asserted_continuously() -> None:
    code = _section_code()
    assert "f_p6Aliased" in code
    assert "p6AliasHits" in code
    assert "P6_ALIAS_HITS" in code


def test_the_host_envelope_is_watched_at_runtime() -> None:
    code = _section_code()
    assert "p6HostBarsMax" in code
    assert "P6_host_bars_max" in code


def test_mutations_are_confirmed_bar_only() -> None:
    assert "barstate.isconfirmed" in _section_code()


def test_no_strategy_or_orders() -> None:
    code = _section_code()
    for forbidden in ("strategy.", "alert("):
        assert forbidden not in code


def test_the_section_draws_nothing_on_the_price_scale() -> None:
    """P7 was just closed on a price-scale issue; the P6 section must not
    compete with the scanner's own rendering."""
    code = _section_code()
    plots = re.findall(r"^plot\(.*$", code, re.M)
    assert plots, "expected diagnostic plots"
    for plot in plots:
        assert "display = display.data_window" in plot, plot
    for drawing in ("label.new", "line.new", "box.new", "plotshape("):
        assert drawing not in code


def test_the_slice_states_its_own_scope() -> None:
    flat = " ".join(_section().replace("//", " ").split())
    assert "SLICE 2" in flat
    assert "minimal P1 projection" in flat


# ---------------------------------------------------------------------------
# Defects found by the first live run on TradingView
# ---------------------------------------------------------------------------


def test_the_pine_sources_are_lf_only() -> None:
    """A CRLF rewrite is invisible to every other test in this file, because
    Python reads text with universal newlines -- the content compares equal
    while the bytes, and therefore the deployment hash, do not."""
    for path in (P4_DEV, P6_DEV):
        assert b"\r\n" not in path.read_bytes(), f"{path.name} has CRLF endings"


def test_projection_outputs_survive_a_forming_bar() -> None:
    """The first live run returned 0 swings on every timeframe. The outputs were
    plain locals, so on any host bar where the requested context's own bar was
    still forming they reset to 0 -- which is most bars, for a weekly context.
    Persisting them is also the staleness rule BTRC needs: hold last confirmed."""
    body = _section_code()
    body = body[body.index("f_p6TfProjection()") :]
    body = body[: body.index("] = request.security")]
    for declaration in (
        "var int   swingCount",
        "var int   lastType",
        "var float lastPrice",
        "var int   lastConfT",
        "var int   eqCount",
    ):
        assert declaration in body, declaration


def test_the_history_envelope_is_measured_not_inferred() -> None:
    """`bars` counts CONFIRMED bars, so it can never reach the requested count
    while one bar is forming. Capacity has to be read from the context's own
    dataset, exactly as the host reads p1DatasetBars."""
    code = _section_code()
    assert "int qDataset = last_bar_index + 1" in code
    assert "f_p6Capacity(int dataset)" in code
    assert "dataset >= C_P6_REQUEST_CALC_BARS" in code
    # warm-up is P1's validated minimum, not the request size
    assert "bars >= C_P1_MIN_CALC_BARS" in code
    for tf in ("W1", "D1", "H4", "H1", "M15", "M5"):
        assert f'"P6_{tf}_dataset"' in code, tf
