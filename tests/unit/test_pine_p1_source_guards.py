"""Repository safety guards for the P1 Pine measurements source.

These are static invariants over ``tradingview/btmm_poi_btrc_scanner_v1.pine`` —
NOT a substitute for TradingView compilation (see the P1 doc for the manual
compile gate). They exist to catch regressions that would silently turn the
analytical scanner into an execution strategy, add repainting lookahead, or drop
the non-repaint gate. Comment lines are stripped before the forbidden-token
checks so that the file's own documentation (which names the forbidden tokens to
say it avoids them) does not trip the guards.
"""

import re
from pathlib import Path

_PINE_PATH = (
    Path(__file__).resolve().parents[2]
    / "tradingview"
    / "btmm_poi_btrc_scanner_v1.pine"
)

# ``for <v> = <start> to array.size(<x>) - 1`` — the counted form that fires
# ``array.get(<x>, <start>)`` on an empty array (see the loop-direction guards).
_COUNTED_ARRAY_LOOP = re.compile(
    r"^\s*for\s+\w+\s*=\s*(?P<start>.+?)\s+to\s+array\.size\(\s*(?P<arr>\w+)\s*\)\s*-\s*1\s*$"
)
# ``int x = na`` / ``var float y = na`` — scalars whose initial state is na.
_NA_DECLARATION = re.compile(
    r"^\s*(?:var\s+)?(?:int|float|bool|string)\s+(?P<name>\w+)\s*=\s*na\s*$"
)


def _source() -> str:
    return _PINE_PATH.read_text(encoding="utf-8")


def _code_lines() -> list[str]:
    """Code-only lines (comment tails stripped), indices aligned to the file."""
    return _code_only(_source()).splitlines()


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


# ---------------------------------------------------------------------------
# Swing confirmation: absent prior confirmed type (swings.py:221/228).
#
# Python seeds ``last_confirmed_type = None`` and skips a pivot only when
# ``pivot.swing_type == last_confirmed_type``; against None that is False, so the
# FIRST eligible pivot always proceeds. Pine seeds the analogue to ``na``, and a
# bare ``!=`` against an na int evaluates to na (falsy) — which permanently
# blocked the first confirmation, yielding zero swings on every timeframe and
# emptying every downstream detector. The alternation rule itself is unchanged;
# only the initial-state comparison is made explicit.
# ---------------------------------------------------------------------------


def test_pine_seeds_last_confirmed_type_as_na() -> None:
    code = _code_only(_source())
    assert "int lastConfirmedType = na" in code, (
        "the swing confirmation alternation state must still be seeded absent"
    )


def test_pine_first_confirmation_not_blocked_by_absent_prior_type() -> None:
    """Every comparison against ``lastConfirmedType`` must be na-guarded."""
    offenders: list[tuple[int, str]] = []
    for number, line in enumerate(_code_lines(), start=1):
        if "lastConfirmedType" not in line:
            continue
        if "!=" not in line and "==" not in line:
            continue  # declaration / assignment, not a gate
        if "na(lastConfirmedType)" not in line:
            offenders.append((number, line.strip()))
    assert not offenders, (
        "swing confirmation compares lastConfirmedType without an explicit "
        "na() guard, so the first pivot can never confirm (swings.py:228): "
        f"{offenders}"
    )


def test_pine_na_seeded_scalars_are_na_guarded_where_compared() -> None:
    """Comparisons against na-seeded scalars need a nearby explicit ``na()``.

    Bounded heuristic, not a Pine parser: the guard may name a partner scalar
    rather than the compared one, because this source seeds and assigns some
    state in pairs (e.g. lastSwingCount / lastSwingConfTime), where guarding the
    partner is sufficient. That still catches the failure class above, where no
    ``na()`` call appears anywhere near the comparison.
    """
    lines = _code_lines()
    na_names = {
        match.group("name")
        for match in (_NA_DECLARATION.match(line) for line in lines)
        if match is not None
    }
    assert "lastConfirmedType" in na_names, "expected na-seeded scalars to be found"

    offenders: list[tuple[int, str]] = []
    for index, line in enumerate(lines):
        if "!=" not in line and "==" not in line:
            continue
        if _NA_DECLARATION.match(line):
            continue
        # The name must be an OPERAND of the comparison — not merely present as
        # a call argument (``array.get(x, bestRel)``), an assignment target
        # (``ratio := ...``), or a UDT field access (``sr.zoneTop``).
        compared = [
            name
            for name in na_names
            if re.search(
                rf"(?<![\w.]){re.escape(name)}\s*(?:==|!=)"
                rf"|(?:==|!=)\s*{re.escape(name)}(?![\w.(])",
                line,
            )
        ]
        if not compared:
            continue
        window = lines[max(0, index - 5) : index + 1]
        if not any("na(" in candidate for candidate in window):
            offenders.append((index + 1, line.strip()))
    assert not offenders, (
        f"na-seeded scalar compared without any nearby na() guard: {offenders}"
    )


# ---------------------------------------------------------------------------
# Pine loop direction (RE10045).
#
# Pine's ``for i = a to b`` counts DOWN when a > b instead of yielding zero
# iterations like Python's ``for x in list`` / ``range(len(x))``. So
# ``for i = 0 to array.size(x) - 1`` executes ``array.get(x, 0)`` on an empty
# array; ``for a = 1 to size - 1`` breaks at size 0 AND 1; and
# ``for j = i + 1 to size - 1`` runs in reverse when i is the last element. The
# safe form is ``for [i, elem] in x``, which yields zero iterations when empty.
# ---------------------------------------------------------------------------


def test_pine_counted_array_loops_are_nonempty_guarded() -> None:
    """Counted ``to array.size(x) - 1`` loops need an explicit nonempty guard."""
    lines = _code_lines()
    offenders: list[tuple[int, str]] = []
    for index, line in enumerate(lines):
        match = _COUNTED_ARRAY_LOOP.match(line)
        if match is None:
            continue
        array_name = match.group("arr")
        window = lines[max(0, index - 3) : index]
        guarded = any(
            re.search(
                rf"array\.size\(\s*{re.escape(array_name)}\s*\)\s*(?:>\s*0|>=\s*1)",
                candidate,
            )
            for candidate in window
        )
        if not guarded:
            offenders.append((index + 1, line.strip()))
    assert not offenders, (
        "counted loop over an array with no preceding nonempty guard — Pine "
        "runs it in reverse when the array is empty (RE10045); use "
        f"`for [i, elem] in <array>` instead: {offenders}"
    )


def test_pine_has_no_offset_start_counted_array_loops() -> None:
    """Offset-start counted array loops must use the ``for ... in`` form.

    ``for a = 1 to size - 1`` (insertion sorts) and ``for j = i + 1 to size - 1``
    (nested pair scans) stay broken even under a ``size > 0`` guard, so they are
    rejected outright rather than guarded.
    """
    offenders: list[tuple[int, str]] = []
    for number, line in enumerate(_code_lines(), start=1):
        match = _COUNTED_ARRAY_LOOP.match(line)
        if match is None:
            continue
        start = match.group("start").strip()
        if start != "0":
            offenders.append((number, line.strip()))
    assert not offenders, (
        "offset-start counted array loop; use `for [i, elem] in <array>` with a "
        f"`continue` guard for the skipped prefix: {offenders}"
    )
