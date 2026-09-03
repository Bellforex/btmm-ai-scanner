"""What counts as a timeframe's SEMANTIC input, as opposed to its dataset.

THE DISTINCTION, AND WHY IT DECIDES THE CAPTURE
-----------------------------------------------
`calc_bars_count = 1251` is an EXECUTION ENVELOPE: it says how many bars
TradingView hands the context. It does not say what the semantic engine consumed.
Measured live, a requested context receives 1251 bars and confirms 1250 — the
1251st is the current, still-forming bar, and it exists so that 1250 CONFIRMED
bars are available.

Conflating the two would corrupt the capture in a way no later test could catch:
the input digest would cover a bar that never entered the ATR recurrence, the
window, P1 or P2, and it would change on every tick of the forming candle while
the semantics stood still. A raw capture taken a second later would then fail to
lock against the snapshot for a reason that has nothing to do with correctness.

So this module establishes, from the source rather than from assumption:

    SEMANTIC INPUT = the CONFIRMED bars that context processed
                     1250 for the five requested contexts
                     the host's own confirmed count for M15 (measured, ~1799)

M15 IS NOT SPECIAL-CASED, IT IS MEASURED
-----------------------------------------
The row count for M15 is deliberately NOT hard-coded to 1799 anywhere the
capture depends on. 1799 is what one anchor produced; the rule is "the host's
actual confirmed count at the anchor", which the atomic snapshot must publish and
the raw capture must match.

THE LESSON FROM THE FAILED TRUNCATION TEST
-------------------------------------------
An earlier draft asserted that truncating M15 history always changes the
projection. It does not: dropping 120 warm-up bars changed every ATR value and
left the discrete projection identical, because the Wilder recurrence had
converged past the tolerance that flips a swing.

The correct conclusion is not "shorter input is fine". It is that **output
equality is not input identity**. A prefix can converge closely enough to agree
by accident, and would keep agreeing until a borderline tolerance case. Closure
therefore requires exact input replay, and acceptance is decided on the five
identity dimensions below — never on whether the outputs happened to match.
"""

from __future__ import annotations

import importlib.util
import re
import sys
from decimal import Decimal
from pathlib import Path
from typing import Any

_REPO = Path(__file__).resolve().parents[2]
P6_DEV = _REPO / "tradingview" / "btmm_poi_btrc_scanner_p6_dev.pine"


def _load(name: str, relpath: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, _REPO / relpath)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


DIG = _load("_p6_digest_sem", "tests/parity_support/p6_digest.py")

#: The identity dimensions a raw capture must match, all five, before it may be
#: fed to the oracle. Digest alone is not enough: it would not distinguish a
#: capture that hashed the right bars in the right order from one that also
#: happened to collide, and the counts/times make a mismatch diagnosable.
IDENTITY_DIMENSIONS = (
    "semantic_rows",
    "semantic_first_time",
    "semantic_last_time",
    "semantic_input_h1",
    "semantic_input_h2",
)

REQUEST_ENVELOPE = 1251
SEMANTIC_MINIMUM = 1250
HOST_ENVELOPE = 1800


def _projection_body() -> list[str]:
    source = P6_DEV.read_text(encoding="utf-8")
    start = source.index("f_p6TfProjection() =>")
    end = source.index("] = request.security")
    return source[start:end].split("\n")


# ---------------------------------------------------------------------------
# Phase 1 -- the forming bar contributes nothing, proven from source
# ---------------------------------------------------------------------------


def test_every_semantic_assignment_is_gated_on_confirmation() -> None:
    """The whole basis for excluding the forming bar.

    If a single `:=` sat outside `if barstate.isconfirmed`, the forming bar would
    reach persistent state and the semantic input would have to include it.
    """
    lines = _projection_body()
    gate = next(
        i for i, line in enumerate(lines)
        if line.strip() == "if barstate.isconfirmed"
    )
    gate_indent = len(lines[gate]) - len(lines[gate].lstrip())

    outside = []
    for index, line in enumerate(lines):
        if ":=" not in line or line.strip().startswith("//"):
            continue
        indent = len(line) - len(line.lstrip())
        if not (index > gate and indent > gate_indent):
            outside.append(line.strip())
    assert outside == [], f"state mutated outside the confirmed gate: {outside}"


def test_nothing_semantic_is_computed_before_the_gate() -> None:
    """`qDataset` is the sole pre-gate statement and is a diagnostic: it reads
    the dataset size and feeds no array, no ATR and no detector."""
    lines = _projection_body()
    gate = next(
        i for i, line in enumerate(lines)
        if line.strip() == "if barstate.isconfirmed"
    )
    pre = [
        line.strip()
        for line in lines[1:gate]
        if line.strip()
        and not line.strip().startswith("//")
        and not line.strip().startswith("var ")
    ]
    assert pre == ["int qDataset = last_bar_index + 1"], pre


def test_the_dataset_diagnostic_feeds_nothing_semantic() -> None:
    """`qDataset` may only be returned, never consumed."""
    body = "\n".join(_projection_body())
    uses = [
        line.strip()
        for line in body.split("\n")
        if "qDataset" in line and not line.strip().startswith("//")
    ]
    assert len(uses) == 2, uses  # its declaration and the returned tuple
    assert uses[0] == "int qDataset = last_bar_index + 1"
    assert uses[1].startswith("[qBars,") and uses[1].rstrip().endswith("]")


# ---------------------------------------------------------------------------
# Phase 2 -- execution dataset is not semantic input
# ---------------------------------------------------------------------------


def _bar(time_ms: int, close: str) -> dict[str, Any]:
    return {
        "time_ms": time_ms,
        "open": Decimal("4000.00"),
        "high": Decimal("4010.00"),
        "low": Decimal("3990.00"),
        "close": Decimal(close),
        "time_close_ms": time_ms + 900_000,
    }


def test_appending_a_forming_bar_changes_the_input_digest() -> None:
    """Which is exactly why it must be excluded.

    If the capture included the forming bar, the digest would move on every tick
    while the semantics stood still, and the raw/atomic lock would fail for
    reasons unrelated to correctness.
    """
    confirmed = [_bar(1_000_000_000_000 + i * 900_000, "4005.00") for i in range(5)]
    with_forming = [*confirmed, _bar(1_000_000_000_000 + 5 * 900_000, "4007.25")]
    assert DIG.input_digest(with_forming) != DIG.input_digest(confirmed)


def test_a_ticking_forming_bar_would_move_the_digest_every_tick() -> None:
    """The same point, made against the thing that actually varies."""
    confirmed = [_bar(1_000_000_000_000 + i * 900_000, "4005.00") for i in range(5)]
    tick_a = [*confirmed, _bar(1_000_004_500_000, "4007.25")]
    tick_b = [*confirmed, _bar(1_000_004_500_000, "4007.26")]
    assert DIG.input_digest(tick_a) != DIG.input_digest(tick_b)
    # ...while the confirmed history, which is what the engine consumed, is stable
    assert DIG.input_digest(confirmed) == DIG.input_digest(list(confirmed))


def test_the_envelope_exceeds_the_semantic_input_by_exactly_the_forming_bar() -> None:
    assert REQUEST_ENVELOPE - SEMANTIC_MINIMUM == 1


# ---------------------------------------------------------------------------
# Phase 3 -- identity is decided on five dimensions, not on output equality
# ---------------------------------------------------------------------------


def test_identity_is_five_dimensional() -> None:
    assert IDENTITY_DIMENSIONS == (
        "semantic_rows",
        "semantic_first_time",
        "semantic_last_time",
        "semantic_input_h1",
        "semantic_input_h2",
    )


def accepts(atomic: dict[str, Any], raw: dict[str, Any]) -> bool:
    """A raw capture is acceptable only when ALL five dimensions match."""
    return all(atomic[dim] == raw[dim] for dim in IDENTITY_DIMENSIONS)


def _snapshot(rows: int = 1250) -> dict[str, Any]:
    """A snapshot ending at a FIXED terminal, so fewer rows means an earlier
    start was dropped -- which is what truncating a history actually does."""
    last = 1_000_000_000_000 + 1249 * 900_000
    bars = [_bar(last - (rows - 1 - i) * 900_000, "4005.00") for i in range(rows)]
    h1, h2 = DIG.input_digest(bars)
    return {
        "semantic_rows": rows,
        "semantic_first_time": bars[0]["time_ms"],
        "semantic_last_time": bars[-1]["time_ms"],
        "semantic_input_h1": h1,
        "semantic_input_h2": h2,
    }


def test_a_matching_capture_is_accepted() -> None:
    assert accepts(_snapshot(), _snapshot()) is True


def test_a_truncated_capture_is_rejected_even_if_outputs_would_agree() -> None:
    """The corrected lesson. Acceptance never consults the projection, so a
    prefix that converged closely enough to produce identical output is still
    rejected -- on row count, first time and digest."""
    atomic = _snapshot(1250)
    truncated = _snapshot(1130)
    assert accepts(atomic, truncated) is False
    differing = [d for d in IDENTITY_DIMENSIONS if atomic[d] != truncated[d]]
    assert set(differing) == {
        "semantic_rows",
        "semantic_first_time",
        "semantic_input_h1",
        "semantic_input_h2",
    }, differing
    # the terminal bar is shared, which is precisely why output can agree
    assert atomic["semantic_last_time"] == truncated["semantic_last_time"]


def test_a_window_shifted_by_one_bar_is_rejected() -> None:
    """The failure mode sequential capture actually risks: a new bar confirms
    between the snapshot and the raw export, sliding the window forward."""
    bars = [_bar(1_000_000_000_000 + i * 900_000, "4005.00") for i in range(1251)]
    older, newer = bars[:1250], bars[1:]
    h1o, h2o = DIG.input_digest(older)
    h1n, h2n = DIG.input_digest(newer)
    atomic = {
        "semantic_rows": 1250,
        "semantic_first_time": older[0]["time_ms"],
        "semantic_last_time": older[-1]["time_ms"],
        "semantic_input_h1": h1o,
        "semantic_input_h2": h2o,
    }
    shifted = {
        "semantic_rows": 1250,
        "semantic_first_time": newer[0]["time_ms"],
        "semantic_last_time": newer[-1]["time_ms"],
        "semantic_input_h1": h1n,
        "semantic_input_h2": h2n,
    }
    assert accepts(atomic, shifted) is False
    # row count alone would NOT have caught it -- this is why five dimensions
    assert atomic["semantic_rows"] == shifted["semantic_rows"]


def test_each_dimension_alone_can_reject() -> None:
    """No dimension is decorative."""
    atomic = _snapshot()
    for dimension in IDENTITY_DIMENSIONS:
        raw = dict(atomic)
        raw[dimension] = atomic[dimension] + 1
        assert accepts(atomic, raw) is False, dimension


# ---------------------------------------------------------------------------
# The capture rule as data the tooling reads
# ---------------------------------------------------------------------------


def semantic_rows_for(timeframe: str, *, host_confirmed: int) -> int:
    """Confirmed rows the capture must export.

    M15 is resolved from the host's MEASURED confirmed count rather than a
    constant, because the host envelope is what determines it and that is an
    execution property, not a contract number.
    """
    return host_confirmed if timeframe == "M15" else SEMANTIC_MINIMUM


def test_m15_follows_the_measured_host_count_not_a_constant() -> None:
    assert semantic_rows_for("M15", host_confirmed=1799) == 1799
    assert semantic_rows_for("M15", host_confirmed=1800) == 1800
    assert semantic_rows_for("W1", host_confirmed=1799) == SEMANTIC_MINIMUM


def test_the_requested_contexts_do_not_follow_the_host() -> None:
    for timeframe in ("W1", "D1", "H4", "H1", "M5"):
        assert semantic_rows_for(timeframe, host_confirmed=1799) == 1250


def test_no_source_constant_hardcodes_the_m15_row_count() -> None:
    """1799 is an observation, not a contract; it must not be frozen in Pine."""
    source = P6_DEV.read_text(encoding="utf-8")
    code = "\n".join(
        line for line in source.split("\n") if not line.strip().startswith("//")
    )
    assert not re.search(r"\b1799\b", code)
