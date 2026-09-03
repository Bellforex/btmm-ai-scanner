"""The P6 digest contract: golden values, and proof every field is covered.

WHY THIS IS WORTH ITS LENGTH
----------------------------
Two digests carry the whole P6 real-data proof, and each fails silently if it is
wrong in the wrong direction.

The **input digest** locks the raw candles handed to Python to the exact candles
the Pine semantic execution consumed. The six raw exports happen in separate
executions, so without that lock the M5/M15 windows could shift by a bar between
runs and the comparison would be against the wrong data while still "passing".
"Historical bars are immutable" does not cover this: the 1251-bar window slides
forward as new bars confirm.

The **output digests** are the comparison. A digest that ignored a field would
pass on a port that got that field wrong.

So every test below is a mutation test. Each one changes exactly one thing and
requires the digest to move. A digest that survived any of them would be
worthless in precisely the situation it exists for.

Golden values are pinned so the contract cannot drift silently: if a refactor
changes an encoding, these fail rather than quietly re-basing both sides of a
future comparison onto new numbers.
"""

from __future__ import annotations

import importlib.util
import sys
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest

_REPO = Path(__file__).resolve().parents[2]


def _load(name: str, relpath: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, _REPO / relpath)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


DIG = _load("_p6_digest_uut", "tests/parity_support/p6_digest.py")


def _bars() -> list[dict[str, Any]]:
    """Three ordered candles, oldest -> newest."""
    return [
        {
            "time_ms": 1_031_522_400_000,
            "open": Decimal("320.15"),
            "high": Decimal("324.25"),
            "low": Decimal("314.75"),
            "close": Decimal("316.85"),
            "time_close_ms": 1_032_127_200_000,
        },
        {
            "time_ms": 1_032_127_200_000,
            "open": Decimal("316.85"),
            "high": Decimal("330.00"),
            "low": Decimal("316.00"),
            "close": Decimal("329.40"),
            "time_close_ms": 1_032_732_000_000,
        },
        {
            "time_ms": 1_032_732_000_000,
            "open": Decimal("329.40"),
            "high": Decimal("331.10"),
            "low": Decimal("321.05"),
            "close": Decimal("322.60"),
            "time_close_ms": 1_033_336_800_000,
        },
    ]


def _values() -> dict[str, Any]:
    """One timeframe's transported surface values."""
    return {
        "swing_count": 66,
        "last_swing_type": 1,
        "last_swing_price": Decimal("3941.75"),
        "last_conf_time": 1_787_522_400_000,
        "equal_level_count": 3,
        "disp_code": 1,
        "disp_ratio": Decimal("1.077562"),
        "p2_direction": -1,
        "p2_transition_count": 4,
        "p2_last_transition_code": -2,
        "p2_last_broken_level": Decimal("4696.87"),
    }


# ---------------------------------------------------------------------------
# Golden values -- the contract must not drift silently
# ---------------------------------------------------------------------------


def test_input_digest_golden() -> None:
    assert DIG.input_digest(_bars()) == (503069320, 129072572)


def test_timeframe_digest_golden() -> None:
    assert DIG.timeframe_digest("W1", _values()) == (539278324, 51004007)


def test_surface_digests_golden() -> None:
    assert DIG.surface_digests(_values()) == {
        "SWINGS": (32674709, 350173177),
        "EQUAL": (8, 8),
        "DISP": (6155138, 6155258),
        "P2_TRANS": (65869481, 665860431),
        "P2_STATE": (3, 3),
    }


# ---------------------------------------------------------------------------
# INPUT digest -- every way the raw capture could be wrong
# ---------------------------------------------------------------------------


def test_input_digest_is_stable() -> None:
    assert DIG.input_digest(_bars()) == DIG.input_digest(_bars())


def test_one_tick_changes_the_input_digest() -> None:
    """The whole point of the lock: a single tick of drift must be visible."""
    mutated = _bars()
    mutated[1]["close"] = Decimal("329.41")
    assert DIG.input_digest(mutated) != DIG.input_digest(_bars())


def test_a_timestamp_change_changes_the_input_digest() -> None:
    mutated = _bars()
    mutated[0]["time_ms"] += 1
    assert DIG.input_digest(mutated) != DIG.input_digest(_bars())


def test_close_time_is_covered() -> None:
    mutated = _bars()
    mutated[2]["time_close_ms"] += 1
    assert DIG.input_digest(mutated) != DIG.input_digest(_bars())


def test_reordering_rows_changes_the_input_digest() -> None:
    """The accumulation is order-sensitive by construction; this proves it."""
    mutated = _bars()
    mutated[0], mutated[1] = mutated[1], mutated[0]
    assert DIG.input_digest(mutated) != DIG.input_digest(_bars())


def test_dropping_the_first_row_changes_the_input_digest() -> None:
    """A window that slid by one bar is exactly this mutation."""
    assert DIG.input_digest(_bars()[1:]) != DIG.input_digest(_bars())


def test_dropping_the_last_row_changes_the_input_digest() -> None:
    assert DIG.input_digest(_bars()[:-1]) != DIG.input_digest(_bars())


@pytest.mark.parametrize("field", ["open", "high", "low", "close"])
def test_every_ohlc_component_is_covered(field: str) -> None:
    mutated = _bars()
    mutated[1][field] = Decimal(str(mutated[1][field])) + Decimal("0.01")
    assert DIG.input_digest(mutated) != DIG.input_digest(_bars())


# ---------------------------------------------------------------------------
# OUTPUT digests -- every transported field must be covered
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("field", list(_values()))
def test_every_transported_field_moves_the_timeframe_digest(field: str) -> None:
    """A field the digest ignored would let a wrong port pass."""
    mutated = _values()
    current = mutated[field]
    mutated[field] = (
        current + (Decimal("0.01") if isinstance(current, Decimal) else 1)
        if current is not None
        else 1
    )
    assert DIG.timeframe_digest("W1", mutated) != DIG.timeframe_digest("W1", _values())


def test_the_surface_digests_localise_a_mismatch() -> None:
    """The reason surfaces are hashed separately: a combined mismatch must say
    WHICH surface moved, not merely that something did."""
    mutated = _values()
    mutated["p2_direction"] = 1
    before, after = DIG.surface_digests(_values()), DIG.surface_digests(mutated)
    moved = [s for s in DIG.SURFACE_ORDER if before[s] != after[s]]
    assert moved == ["P2_STATE"], moved


def test_the_timeframe_code_is_part_of_the_digest() -> None:
    """Two timeframes with identical values must still differ, or a projection
    that ignored its timeframe entirely could pass."""
    assert DIG.timeframe_digest("W1", _values()) != DIG.timeframe_digest(
        "D1", _values()
    )


def test_absent_price_and_absent_code_are_distinguishable() -> None:
    """Pine keeps `na` and the -99 sentinel distinct; conflating them here would
    hide a port that conflated them there."""
    na_price = _values() | {"p2_last_broken_level": None}
    sentinel = _values() | {"p2_last_transition_code": DIG.C_ST_NA}
    base = DIG.timeframe_digest("W1", _values())
    assert DIG.timeframe_digest("W1", na_price) != base
    assert DIG.timeframe_digest("W1", sentinel) != base
    assert DIG.timeframe_digest("W1", na_price) != DIG.timeframe_digest(
        "W1", sentinel
    )


def test_the_capture_digest_covers_every_timeframe() -> None:
    per_tf = {tf: _values() for tf in ("W1", "D1", "H4", "H1", "M15", "M5")}
    base = DIG.capture_digest(per_tf)
    for timeframe in per_tf:
        mutated = {k: (v | {"swing_count": 99} if k == timeframe else v)
                   for k, v in per_tf.items()}
        assert DIG.capture_digest(mutated) != base, timeframe


def test_the_capture_digest_requires_all_six_timeframes() -> None:
    per_tf = {tf: _values() for tf in ("W1", "D1", "H4", "H1", "M15")}
    with pytest.raises(KeyError):
        DIG.capture_digest(per_tf)


def test_capture_digest_order_is_fixed_not_caller_supplied() -> None:
    """Iteration order must not be able to change the global digest."""
    forward = {tf: _values() for tf in ("W1", "D1", "H4", "H1", "M15", "M5")}
    reversed_ = dict(reversed(list(forward.items())))
    assert DIG.capture_digest(forward) == DIG.capture_digest(reversed_)


# ---------------------------------------------------------------------------
# The contract's own shape
# ---------------------------------------------------------------------------


def test_the_surface_set_is_exactly_the_five_transported_ones() -> None:
    assert set(DIG.SURFACE_FIELDS) == {
        "SWINGS",
        "EQUAL",
        "DISP",
        "P2_TRANS",
        "P2_STATE",
    }
    assert set(DIG.SURFACE_ORDER) == set(DIG.SURFACE_FIELDS)


def test_the_surfaces_cover_the_oracle_compare_set_exactly() -> None:
    """If the oracle grows a field the digests do not hash, the parity
    comparison would silently stop covering it."""
    oracle = _load("_p6_oracle_for_digest", "tests/parity_support/p6_projection_oracle.py")
    covered = {name for fields in DIG.SURFACE_FIELDS.values() for name, _ in fields}
    projection = oracle.P6Projection(
        confirmed_bar_count=1, swing_count=0, last_swing_type=DIG.C_ST_NA,
        last_swing_price=None, last_conf_time=None, equal_level_count=0,
        disp_code=0, disp_ratio=None, p2_direction=0, p2_transition_count=0,
        p2_last_transition_code=DIG.C_ST_NA, p2_last_broken_level=None,
    )
    assert covered == set(projection.compare_values())


def test_hashes_stay_inside_the_frozen_moduli() -> None:
    values = _values()
    h1, h2 = DIG.timeframe_digest("W1", values)
    assert 0 <= h1 < DIG.MOD1
    assert 0 <= h2 < DIG.MOD2
    assert (DIG.MOD1, DIG.BASE1, DIG.MOD2, DIG.BASE2) == (
        1000000007,
        1000003,
        1000000009,
        1000033,
    )
