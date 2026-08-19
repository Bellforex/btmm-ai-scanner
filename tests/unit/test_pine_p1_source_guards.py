"""Repository safety guards for the P1 Pine measurements source.

These are static invariants over ``tradingview/btmm_poi_btrc_scanner_v1.pine`` —
NOT a substitute for TradingView compilation (see the P1 doc for the manual
compile gate). They exist to catch regressions that would silently turn the
analytical scanner into an execution strategy, add repainting lookahead, or drop
the non-repaint gate. Comment lines are stripped before the forbidden-token
checks so that the file's own documentation (which names the forbidden tokens to
say it avoids them) does not trip the guards.
"""

from pathlib import Path

_PINE_PATH = (
    Path(__file__).resolve().parents[2]
    / "tradingview"
    / "btmm_poi_btrc_scanner_v1.pine"
)


def _source() -> str:
    return _PINE_PATH.read_text(encoding="utf-8")


def _code_only(source: str) -> str:
    """Return the source with ``//`` comment tails removed (line by line).

    A naive split on ``//`` is safe here because the Pine source contains no
    string literal that embeds ``//`` — the guards below would need revisiting
    only if that ever changes.
    """
    lines: list[str] = []
    for line in source.splitlines():
        head = line.split("//", 1)[0]
        lines.append(head)
    return "\n".join(lines)


def test_pine_source_exists() -> None:
    assert _PINE_PATH.is_file(), f"missing Pine source at {_PINE_PATH}"


def test_pine_declares_version_6() -> None:
    assert _source().lstrip().startswith("//@version=6")


def test_pine_is_indicator_not_strategy() -> None:
    code = _code_only(_source())
    assert "indicator(" in code
    assert "strategy(" not in code


def test_pine_has_no_execution_calls() -> None:
    code = _code_only(_source())
    forbidden = (
        "strategy.entry",
        "strategy.order",
        "strategy.exit",
        "strategy.close",
        "strategy.cancel",
    )
    present = [token for token in forbidden if token in code]
    assert not present, f"execution calls present in Pine source: {present}"


def test_pine_has_no_lookahead_or_multitimeframe() -> None:
    code = _code_only(_source())
    # P1 is single-chart, non-repaint: no security requests, no lookahead.
    assert "request.security" not in code
    assert "lookahead" not in code
    assert "barmerge.lookahead_on" not in code


def test_pine_gates_confirmed_state_on_closed_bars() -> None:
    # The non-repaint contract: confirmed analytical state advances only under a
    # barstate.isconfirmed gate.
    assert "barstate.isconfirmed" in _code_only(_source())


def test_pine_exposes_parity_plots() -> None:
    code = _code_only(_source())
    for key in (
        "P1_swing_high_price",
        "P1_swing_low_price",
        "P1_disp_code",
        "P1_equal_high",
        "P1_equal_low",
    ):
        assert key in code, f"missing parity output {key}"
