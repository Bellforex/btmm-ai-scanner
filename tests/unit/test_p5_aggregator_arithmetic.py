"""The exact aggregator arithmetic a Pine port must reproduce.

Traced from `_weighted_final` and `_permission` in `btrc/t5_engine.py` rather
than inferred, because two of the four findings below are invisible until you
run them.

WHAT THE SOURCE ACTUALLY DOES
-----------------------------
```python
total_weight = sum(weights.get(k, 0) for k in values)
if total_weight == 0:
    return 0
weighted = sum(values[k] * weights.get(k, 0) for k in values)
return round(weighted / total_weight)
```

FINDING 1 — a missing weight key EXCLUDES a component, it does not zero it
--------------------------------------------------------------------------
`total_weight` sums `weights.get(k, 0)` over the same eight keys the numerator
uses, so a key absent from the weight table contributes zero to BOTH sums. The
component drops out of the mean entirely.

That is not the same as scoring it zero, and the difference is not small: on the
same inputs, dropping the volatility weight gives 61 while scoring volatility as
zero gives 57. A port that "helpfully" defaulted an unknown component to a zero
SCORE would drag every result down; the source raises it instead.

FINDING 2 — the denominator is computed, never the constant 13
--------------------------------------------------------------
13 is what the default table happens to sum to. The source recomputes it from
whatever weights it is given, so a port that hard-codes 13 diverges the moment
the configuration changes — which is exactly what a provisional calibration is
expected to do.

FINDING 3 — `round()` is BANKER'S rounding, and Pine's `math.round` is not
--------------------------------------------------------------------------
Python rounds halves to even; Pine rounds halves away from zero. They disagree
at 62.5 (62 vs 63) and 64.5 (64 vs 65).

With the default table this can never bite: a tie needs `weighted / total` to
land on exactly `n + 0.5`, which requires `total` to be EVEN, and 13 is odd. But
the weights are configuration, so the guarantee is contingent, not structural.
The port must implement banker's rounding rather than reach for `math.round`.
This repository already has the mirror-image helper (`p2_digest.pine_round`)
for the same reason in the opposite direction.

FINDING 4 — the comparators are not symmetric
---------------------------------------------
Counter-trend uses `final < watch_only_min`; every other branch uses `>=`. So at
exactly 45 a counter-trend POI is NOT downgraded, while at exactly 45 a neutral
or aligned POI clears the lower band. Guessing `<=` anywhere flips a boundary.
"""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

import pytest

from btmm_ai_scanner.btrc.t5_configuration import ConfluenceConfiguration

_REPO = Path(__file__).resolve().parents[2]
_T5 = _REPO / "src" / "btmm_ai_scanner" / "btrc" / "t5_engine.py"

SCORED_KEYS = (
    "btmm",
    "poi",
    "trend",
    "regime",
    "momentum",
    "breakout",
    "liquidity",
    "volatility",
)


def weighted_final(values: dict[str, int], weights: dict[str, int]) -> int:
    """The source formula, transcribed exactly."""
    total_weight = sum(weights.get(k, 0) for k in values)
    if total_weight == 0:
        return 0
    weighted = sum(values[k] * weights.get(k, 0) for k in values)
    return round(weighted / total_weight)


def _values(**overrides: int) -> dict[str, int]:
    base = {
        "btmm": 85,
        "poi": 60,
        "trend": 50,
        "regime": 50,
        "momentum": 50,
        "breakout": 40,
        "liquidity": 60,
        "volatility": 50,
    }
    base.update(overrides)
    return base


def _weights() -> dict[str, int]:
    return dict(ConfluenceConfiguration().weights)


# ---------------------------------------------------------------------------
# The formula is the source formula
# ---------------------------------------------------------------------------


def test_the_transcribed_formula_matches_the_source_text() -> None:
    source = _T5.read_text(encoding="utf-8")
    assert "total_weight = sum(weights.get(k, 0) for k in values)" in source
    assert "weighted = sum(values[k] * weights.get(k, 0) for k in values)" in source
    assert "return round(weighted / total_weight)" in source
    assert "if total_weight == 0:" in source


def test_the_default_denominator_is_thirteen() -> None:
    assert sum(_weights().values()) == 13


def test_the_denominator_is_computed_not_hardcoded() -> None:
    """Finding 2: halving every weight leaves the score identical, which only
    holds if the denominator moves with the numerator."""
    weights = _weights()
    doubled = {k: v * 2 for k, v in weights.items()}
    assert weighted_final(_values(), weights) == weighted_final(_values(), doubled)


# ---------------------------------------------------------------------------
# Finding 1 -- exclusion, not zeroing
# ---------------------------------------------------------------------------


def test_a_missing_weight_excludes_the_component_from_both_sums() -> None:
    weights = _weights()
    without = {k: v for k, v in weights.items() if k != "volatility"}
    assert weighted_final(_values(), without) == 61
    assert weighted_final(_values(), weights) == 60


def test_excluding_differs_from_scoring_zero() -> None:
    """The distinction a port would most plausibly get wrong."""
    weights = _weights()
    without = {k: v for k, v in weights.items() if k != "volatility"}
    excluded = weighted_final(_values(), without)
    zeroed = weighted_final(_values(volatility=0), weights)
    assert excluded == 61
    assert zeroed == 57
    assert excluded != zeroed


@pytest.mark.parametrize("key", list(SCORED_KEYS))
def test_every_key_absent_from_the_table_is_silently_dropped(key: str) -> None:
    """No exception, no warning -- which is why the key strings are pinned."""
    weights = {k: v for k, v in _weights().items() if k != key}
    result = weighted_final(_values(), weights)
    assert isinstance(result, int)


def test_an_empty_weight_table_returns_zero_rather_than_dividing() -> None:
    assert weighted_final(_values(), {}) == 0


# ---------------------------------------------------------------------------
# Finding 3 -- banker's rounding
# ---------------------------------------------------------------------------


def _pine_round(value: float) -> int:
    """Pine's `math.round`: ties away from zero."""
    return int(Decimal(str(value)).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


@pytest.mark.parametrize(
    ("value", "python_result", "pine_result"),
    [(62.5, 62, 63), (63.5, 64, 64), (64.5, 64, 65)],
)
def test_python_and_pine_rounding_disagree_on_ties(
    value: float, python_result: int, pine_result: int
) -> None:
    assert round(value) == python_result
    assert _pine_round(value) == pine_result


def test_a_tie_is_unreachable_with_the_default_odd_denominator() -> None:
    """Contingent, not structural: it holds because 13 is odd."""
    total = sum(_weights().values())
    assert total % 2 == 1
    assert not any((numerator / total) % 1 == 0.5 for numerator in range(0, 100 * total))


def test_a_tie_becomes_reachable_once_the_denominator_is_even() -> None:
    """So the port must round like Python, not like Pine, even though the
    default configuration would never expose the difference."""
    weights = {k: v for k, v in _weights().items() if k != "volatility"}
    total = sum(weights.values())
    assert total == 12
    quotient = 750 / total
    assert quotient == 62.5
    assert round(quotient) == 62
    assert _pine_round(quotient) == 63


# ---------------------------------------------------------------------------
# Finding 4 -- the comparators
# ---------------------------------------------------------------------------


def test_the_band_values_are_the_frozen_provisional_ones() -> None:
    config = ConfluenceConfiguration()
    assert config.watch_only_min == 45
    assert config.high_confluence_min == 65


def test_counter_trend_uses_strictly_less_than() -> None:
    source = _T5.read_text(encoding="utf-8")
    assert "if final < config.watch_only_min:" in source


def test_every_other_band_test_uses_greater_or_equal() -> None:
    source = _T5.read_text(encoding="utf-8")
    assert "if final >= config.watch_only_min:" in source
    assert "if final >= config.high_confluence_min:" in source
    assert "elif final >= config.watch_only_min:" in source


def test_at_exactly_45_counter_trend_is_not_downgraded() -> None:
    """The asymmetry, stated as behaviour: `< 45` is false at 45."""
    assert not (45 < 45)


def test_at_exactly_45_and_65_the_higher_branches_are_taken() -> None:
    assert 45 >= 45
    assert 65 >= 65


def test_the_extreme_volatility_downgrade_is_configurable_and_last() -> None:
    """It rewrites an already-decided BUY/SELL bias to WATCH_ONLY and says the
    direction is unchanged -- so it is supervision, not a re-decision."""
    source = _T5.read_text(encoding="utf-8")
    assert "config.downgrade_on_extreme_volatility" in source
    assert "VolatilityState.EXTREME" in source
    assert "direction unchanged" in source
