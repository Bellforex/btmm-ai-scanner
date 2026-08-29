"""Harness tests for the P2 atomic state-replay orchestrator.

These verify the ORCHESTRATION — row loading, execution-origin indexing,
confirmedBarCount/absFirst mapping, bounded-window selection, warm-history
ATR preservation, field extraction, digest normalization, determinism, and
input rejection. They deliberately do NOT hard-code any Pine hash target:
the engine under the orchestrator is production code already covered by its
own suites, and overfitting the harness to expected outputs would prove
nothing.
"""

from __future__ import annotations

import importlib.util
import sys
from decimal import Decimal
from pathlib import Path

import pytest

from btmm_ai_scanner.measurements.atr import compute_atr_series

REPO = Path(__file__).resolve().parents[2]


def _load(name: str, relpath: str):
    spec = importlib.util.spec_from_file_location(name, REPO / relpath)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


R = _load("_p2rep_under_test", "tests/parity_support/p2_atomic_state_replay.py")
D = _load("_p2rep_digest_ref", "tests/parity_support/p2_digest.py")

STEP = 900_000


def _write_context(path: Path, rows: list[tuple[int, str, str, str, str]]) -> Path:
    lines = ["time,open,high,low,close,time_close"]
    for time_ms, open_, high, low, close in rows:
        lines.append(f"{time_ms},{open_},{high},{low},{close},{time_ms + STEP}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def _zigzag_rows(n: int, start_ms: int = 1_790_000_100_000) -> list[tuple[int, str, str, str, str]]:
    """A deterministic zig-zag with real swings, plus one weekend gap."""
    rows = []
    t = start_ms
    for i in range(n):
        base = Decimal("4000") + Decimal((i * 17) % 40 - 20)
        open_ = base
        close = base + (Decimal((i * 23) % 30 - 15) / 2)
        high = max(open_, close) + 4
        low = min(open_, close) - 4
        rows.append((t, str(open_), str(high), str(low), str(close)))
        t += STEP
        if i == n // 2:
            t += 48 * 3600 * 1000
    return rows


def _monotone_rows(n: int, start_ms: int = 1_790_000_100_000) -> list[tuple[int, str, str, str, str]]:
    """Strictly rising bars: no local extremum, hence zero swings."""
    rows = []
    t = start_ms
    for i in range(n):
        base = Decimal("4000") + 10 * i
        rows.append((t, str(base), str(base + 3), str(base - 3), str(base + 2)))
        t += STEP
    return rows


# ---------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------

def test_loader_builds_exact_decimal_candles(tmp_path: Path) -> None:
    path = _write_context(tmp_path / "ctx.csv", _zigzag_rows(10))
    candles = R.load_context_candles(path)
    assert len(candles) == 10
    assert isinstance(candles[0].open, Decimal)
    assert R._ms(candles[0].event_time_utc) == 1_790_000_100_000
    assert R._ms(candles[0].availability_time_utc) == 1_790_000_100_000 + STEP
    # availability comes from the CSV's time_close column, exactly
    for candle in candles:
        assert candle.availability_time_utc == candle.processing_time_utc


def test_loader_rejects_wrong_columns(tmp_path: Path) -> None:
    bad = tmp_path / "bad.csv"
    bad.write_text("time,open,high,low,close\n1,2,3,1,2\n", encoding="utf-8")
    with pytest.raises(R.ReplayInputError, match="columns"):
        R.load_context_candles(bad)


def test_loader_rejects_non_monotonic_times(tmp_path: Path) -> None:
    rows = _zigzag_rows(5)
    rows[3] = (rows[1][0], *rows[3][1:])  # duplicate an earlier timestamp
    path = _write_context(tmp_path / "ctx.csv", rows)
    with pytest.raises(R.ReplayInputError, match="strictly increasing"):
        R.load_context_candles(path)


def test_replay_rejects_too_few_rows(tmp_path: Path) -> None:
    path = _write_context(tmp_path / "ctx.csv", _zigzag_rows(10))
    with pytest.raises(R.ReplayInputError, match="fewer than state_count"):
        R.replay(path, state_count=11)


# ---------------------------------------------------------------------------
# Index frame and window selection
# ---------------------------------------------------------------------------

def test_confirmed_bar_count_and_abs_first_mapping(tmp_path: Path) -> None:
    path = _write_context(tmp_path / "ctx.csv", _zigzag_rows(40))
    result = R.replay(path, state_count=5, lookback=20)
    assert [s.evaluation_index for s in result.states] == [35, 36, 37, 38, 39]
    assert [s.confirmed_bar_count for s in result.states] == [36, 37, 38, 39, 40]
    assert [s.abs_first for s in result.states] == [16, 17, 18, 19, 20]
    candles = R.load_context_candles(path)
    assert [s.time_ms for s in result.states] == [
        R._ms(c.event_time_utc) for c in candles[35:]
    ]


def test_partial_window_before_lookback_is_full_history(tmp_path: Path) -> None:
    path = _write_context(tmp_path / "ctx.csv", _zigzag_rows(12))
    result = R.replay(path, state_count=12, lookback=20)
    assert result.states[0].abs_first == 0
    assert result.states[-1].abs_first == 0  # 12 < lookback: window never slides


# ---------------------------------------------------------------------------
# Warm-history ATR preservation (the load-bearing replay property)
# ---------------------------------------------------------------------------

def test_window_atr_is_the_continuous_series_not_a_restart(tmp_path: Path) -> None:
    path = _write_context(tmp_path / "ctx.csv", _zigzag_rows(40))
    candles = R.load_context_candles(path)
    atr_all = compute_atr_series(candles, 14)
    terminal, lookback = 39, 20
    continuous = R.window_atr(atr_all, terminal, lookback)
    window = candles[terminal + 1 - lookback : terminal + 1]
    restarted = compute_atr_series(window, 14)
    assert len(continuous) == len(window)
    # a restart has NO ATR during its warm-up; the continuous slice is warm
    assert restarted[0] is None
    assert continuous[0] is not None
    assert continuous == tuple(atr_all[20:40])


# ---------------------------------------------------------------------------
# Field extraction and digest normalization
# ---------------------------------------------------------------------------

def test_zero_swing_context_uses_frozen_absent_semantics(tmp_path: Path) -> None:
    path = _write_context(tmp_path / "ctx.csv", _monotone_rows(30))
    result = R.replay(path, state_count=3, lookback=30)
    for state in result.states:
        assert state.adapted_swing_count == 0
        assert state.last_pivot_start_abs is None      # na family
        assert state.last_conf_time is None
        assert state.relationship_count == 0
        assert state.last_high_relationship is None
        assert state.last_low_relationship is None
        assert state.direction == 0                     # UNDETERMINED, not NA
        assert state.protected_high == R.C_ST_NA        # sentinel family
        assert state.protected_low == R.C_ST_NA
        assert state.weak_high == R.C_ST_NA
        assert state.weak_low == R.C_ST_NA
        assert state.transition_count == 0
        assert state.last_transition_code == R.C_ST_NA
        assert state.last_broken_key == R.C_ST_NA
        assert state.last_broken_level is None


def test_hashes_recompute_from_states_via_frozen_digest(tmp_path: Path) -> None:
    path = _write_context(tmp_path / "ctx.csv", _zigzag_rows(60))
    result = R.replay(path, state_count=10, lookback=30)
    records = [
        D.encode_state_bar(s.digest_values(), Decimal("0.01")) for s in result.states
    ]
    assert D.per_field_hashes(records) == result.field_hashes
    assert D.state_hashes(records) == (result.state_hash_1, result.state_hash_2)
    assert set(result.field_hashes) == {name for name, _k, _a in D.STATE_FIELD_ORDER}


def test_swingful_context_produces_consistent_swing_fields(tmp_path: Path) -> None:
    path = _write_context(tmp_path / "ctx.csv", _zigzag_rows(60))
    result = R.replay(path, state_count=5, lookback=30)
    final = result.states[-1]
    assert final.adapted_swing_count > 0, "zig-zag fixture must produce swings"
    assert final.last_conf_time is not None
    assert final.last_pivot_start_abs is not None
    # the pivot-start abs index must sit inside the final bounded window
    assert final.abs_first <= final.last_pivot_start_abs <= final.evaluation_index


# ---------------------------------------------------------------------------
# Determinism and trace
# ---------------------------------------------------------------------------

def test_replay_and_trace_are_deterministic(tmp_path: Path) -> None:
    path = _write_context(tmp_path / "ctx.csv", _zigzag_rows(60))
    first = R.replay(path, state_count=10, lookback=30)
    second = R.replay(path, state_count=10, lookback=30)
    assert first.states == second.states
    assert first.field_hashes == second.field_hashes
    assert (first.state_hash_1, first.state_hash_2) == (
        second.state_hash_1,
        second.state_hash_2,
    )
    trace_a = tmp_path / "a.csv"
    trace_b = tmp_path / "b.csv"
    R.write_trace(first, trace_a)
    R.write_trace(second, trace_b)
    assert trace_a.read_bytes() == trace_b.read_bytes()
