"""The P6 transport source must keep the architecture the lab measured.

Phase-22 settled two numbers that look contradictory and are not: the host runs
at 1800 and each requested context asks for 1250. Because 1250 sits below 1800,
the host envelope is untouched while every timeframe gets its full warm-up. Drop
the per-request argument and the contexts silently clamp to the host's TIME span
-- two weekly bars on an M15 host, against the 1250 required -- which would not
fail loudly anywhere.

These tests read the Pine as source and pin that, along with the transport
exclusions the per-component audit established.
"""

from __future__ import annotations

import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
P6_DEV = REPO / "tradingview" / "btmm_poi_btrc_scanner_p6_dev.pine"


def _text() -> str:
    return P6_DEV.read_text(encoding="utf-8")


def _code() -> str:
    return "\n".join(
        line for line in _text().splitlines() if not line.strip().startswith("//")
    )


def test_host_envelope_is_1800() -> None:
    code = _code()
    assert "int C_P6_HOST_CALC_BARS    = 1800" in code
    assert re.search(r"indicator\([^)]*calc_bars_count = 1800", code, re.S)


def test_each_request_asks_for_1250() -> None:
    """The load-bearing detail. Without it the contexts clamp to the host span."""
    code = _code()
    assert "int C_P6_REQUEST_CALC_BARS = 1250" in code
    calls = re.findall(r"request\.security\([^\n]*", code)
    assert len(calls) == 6, f"expected six requested contexts, found {len(calls)}"
    for call in calls:
        assert "calc_bars_count = C_P6_REQUEST_CALC_BARS" in call, call


def test_request_count_is_below_the_host_envelope() -> None:
    """The whole reason the two frozen numbers coexist. If a later change raised
    the request above 1800 the host would follow it, moving P1-P4 off their
    validated horizon."""
    code = _code()
    host = int(re.search(r"C_P6_HOST_CALC_BARS\s+=\s+(\d+)", code).group(1))
    req = int(re.search(r"C_P6_REQUEST_CALC_BARS = (\d+)", code).group(1))
    assert req < host, (req, host)


def test_exactly_the_six_authority_timeframes_are_requested() -> None:
    code = _code()
    requested = set(re.findall(r'C_P6_TF_(\w+)\s*=\s*"([^"]+)"', code))
    assert requested == {
        ("W1", "W"),
        ("D1", "D"),
        ("H4", "240"),
        ("H1", "60"),
        ("M15", "15"),
        ("M5", "5"),
    }


def test_no_m1_is_transported() -> None:
    """P4's set is {M1, M5, M15}; P5's authority set has no M1 at all."""
    code = _code()
    assert '"1"' not in re.sub(r'"(15|60|240|5|W|D)"', "", code)


def test_the_excluded_surfaces_are_absent() -> None:
    """BTRC reads three of P1's five collections and two of P2's three. The two
    it ignores carry the most expensive machinery, so their absence here is the
    point rather than an oversight."""
    text = _text()
    for excluded in (
        "support_resistance_zones",
        "trendlines",
        "swing_relationships",
    ):
        code_uses = [
            line
            for line in text.splitlines()
            if excluded in line and not line.strip().startswith("//")
        ]
        assert code_uses == [], code_uses


def test_isolation_is_asserted_continuously_not_once() -> None:
    """Aliasing between requested contexts would silently invalidate every later
    parity claim, so the source carries a running guard."""
    code = _code()
    assert "f_p6Aliased" in code
    assert "p6AliasHits" in code
    assert "ALIAS_HITS" in code


def test_the_host_envelope_is_watched_at_runtime() -> None:
    code = _code()
    assert "p6HostBarsMax" in code
    assert "host_bars_max" in code


def test_mutations_are_confirmed_bar_only() -> None:
    """Same non-repaint contract as P1-P4."""
    code = _code()
    assert "barstate.isconfirmed" in code
    # every assignment to the running guards sits under a confirmed-bar gate
    assert code.count("barstate.isconfirmed") >= 2


def test_no_strategy_or_orders() -> None:
    code = _code()
    for forbidden in ("strategy.", "order.", "alert("):
        assert forbidden not in code


def test_nothing_is_drawn_on_the_price_scale() -> None:
    """This slice is transport; it must not compete with the scanner's own
    rendering, and P7 has just been closed on a price-scale issue."""
    code = _code()
    plots = re.findall(r"^plot\(.*$", code, re.M)
    assert plots, "expected diagnostic plots"
    for plot in plots:
        assert "display = display.data_window" in plot, plot
    for drawing in ("label.new", "line.new", "box.new", "plotshape("):
        assert drawing not in code


def test_the_slice_states_its_own_scope() -> None:
    """It carries transport, not yet the P1/P2 projection. The header must say
    so, so the file cannot be mistaken for a finished P6."""
    # the header wraps across comment lines, so normalise before matching
    flat = " ".join(_text().replace("//", " ").split())
    assert "SLICE 1" in flat
    assert "does NOT yet carry the P1/P2 semantic projection" in flat
