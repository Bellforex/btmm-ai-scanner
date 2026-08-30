"""P3-I6 — differential parity for the persistent POI lifecycle.

THIS FILE ASSERTS THE AUTHORITATIVE PRODUCTION CONTRACT.

`tests/parity_support/p3_lifecycle_model.py` is a transcription of the Pine
persistent cursor. Production `run_poi_lifecycle` is always the reference side.

THE DECISIVE PROPERTY
---------------------
Production looks ahead up to seven bars; Pine cannot. The port therefore keeps
a committed boundary and re-derives only the unresolved tail each bar. That is
only correct if, for EVERY prefix of a stream, the incremental cursor reports
exactly what a fresh batch walk over that same prefix reports — including the
deliberately provisional tail production produces on a truncated window.

So the campaign feeds each stream bar by bar and, at every single bar, compares
the cursor's status, its full transition sequence (codes and both timestamps),
and its tap count against `run_poi_lifecycle(candles[:t+1])`. A cursor that
committed too early would diverge the moment a later bar changed an outcome; a
cursor that never committed would still pass, so a separate test asserts the
committed boundary actually advances and stays bounded.
"""

from __future__ import annotations

import importlib.util
import random
import sys
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from types import ModuleType
from typing import Any
from uuid import UUID

import pytest

from btmm_ai_scanner.config.enums import InternalSymbol, Timeframe
from btmm_ai_scanner.contracts.normalized_candle import NormalizedCandle
from btmm_ai_scanner.contracts.raw_candle import CandleCompleteness, CandleVolumeKind
from btmm_ai_scanner.contracts.types import SemVer
from btmm_ai_scanner.poi.configuration import PoiConfiguration
from btmm_ai_scanner.poi.enums import PoiDirection, PoiLifecycleStatus
from btmm_ai_scanner.poi.lifecycle import run_poi_lifecycle

REPO = Path(__file__).resolve().parents[2]


def _load(name: str, relpath: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, REPO / relpath)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


L = _load("_p3_lifecycle_model", "tests/parity_support/p3_lifecycle_model.py")

_CONFIG = PoiConfiguration(minimum_price_tick=Decimal("0.01"))
_BASE_TIME = datetime(2026, 1, 1, tzinfo=UTC)
_RAW_CANDLE_ID = UUID("0193f4a0-1234-7abc-8def-abcdefabcdaa")
_PROVENANCE_ID = UUID("0193f4a0-1234-7abc-8def-abcdefabcdff")
_POI_RECORD_ID = UUID("0193f4a0-1234-7abc-8def-999999999999")
_FINGERPRINT = "e" * 64

_TOP = Decimal("100.4")
_BOTTOM = Decimal("99.6")


def _candle(
    index: int,
    open_: str,
    high: str,
    low: str,
    close: str,
    *,
    gap_minutes: int = 0,
) -> NormalizedCandle:
    event_time = _BASE_TIME + timedelta(minutes=index + gap_minutes)
    availability = event_time + timedelta(minutes=1)
    return NormalizedCandle.model_validate(
        {
            "record_id": UUID(f"0193f4a0-1234-7abc-8def-{index:012x}"),
            "content_fingerprint": _FINGERPRINT,
            "raw_candle_id": _RAW_CANDLE_ID,
            "provider": "FXCM",
            "source_reference": "fxcm-xauusd-m1",
            "source_symbol": InternalSymbol.XAUUSD.value,
            "source_timeframe": Timeframe.M1.value,
            "symbol": InternalSymbol.XAUUSD,
            "timeframe": Timeframe.M1,
            "event_time_utc": event_time,
            "availability_time_utc": availability,
            "processing_time_utc": availability,
            "original_event_time": event_time,
            "original_availability_time": availability,
            "original_timezone": "UTC",
            "open": Decimal(open_),
            "high": Decimal(high),
            "low": Decimal(low),
            "close": Decimal(close),
            "volume": Decimal("10"),
            "volume_kind": CandleVolumeKind.TICK,
            "completeness": CandleCompleteness.CONFIRMED_COMPLETE,
            "rule_version": SemVer.parse("0.1.0"),
            "contract_version": SemVer.parse("0.1.0"),
            "schema_version": SemVer.parse("0.1.0"),
            "provenance_id": _PROVENANCE_ID,
        }
    )


def _atr(
    candles: tuple[NormalizedCandle, ...], value: str = "1.00"
) -> tuple[Decimal | None, ...]:
    return tuple(Decimal(value) for _ in candles)


def _ms(moment: datetime) -> int:
    return int(moment.timestamp() * 1000)


def _oracle(
    candles: tuple[NormalizedCandle, ...],
    atr_values: tuple[Decimal | None, ...],
    direction: PoiDirection,
    zone_top: Decimal = _TOP,
    zone_bottom: Decimal = _BOTTOM,
) -> Any:
    """Production is always the reference side."""
    return run_poi_lifecycle(
        candles,
        atr_values,
        InternalSymbol.XAUUSD,
        Timeframe.M1,
        _POI_RECORD_ID,
        direction,
        zone_top,
        zone_bottom,
        candles[0].event_time_utc,
        _CONFIG,
    )


def _oracle_projection(result: Any) -> tuple[int, tuple[Any, ...], int]:
    transitions = tuple(
        (
            L.TR_CODE[t.transition_type],
            _ms(t.event_time_utc),
            _ms(t.availability_time_utc),
        )
        for t in result.transitions
    )
    return L.LC_CODE[result.final_status], transitions, result.tap_count


def _model_projection(cursor: Any) -> tuple[int, tuple[Any, ...], int]:
    transitions = tuple(
        (t.code, t.event_ms, t.availability_ms) for t in cursor.transitions()
    )
    return cursor.state_code(), transitions, cursor.tap_count


def _assert_prefix_parity(
    candles: tuple[NormalizedCandle, ...],
    direction: PoiDirection,
    zone_top: Decimal = _TOP,
    zone_bottom: Decimal = _BOTTOM,
    atr_value: str = "1.00",
) -> Any:
    """Compare the incremental cursor with a fresh batch walk at EVERY prefix."""
    atr_values = _atr(candles, atr_value)
    cursor = L.PoiLifecycleCursor(
        zone_top=zone_top,
        zone_bottom=zone_bottom,
        direction=direction,
        availability_ms=_ms(candles[0].event_time_utc),
        configuration=_CONFIG,
    )
    for t in range(len(candles)):
        cursor.advance(candles, atr_values, t)
        prefix = candles[: t + 1]
        expected = _oracle_projection(
            _oracle(prefix, atr_values[: t + 1], direction, zone_top, zone_bottom)
        )
        actual = _model_projection(cursor)
        assert actual == expected, f"prefix {t}: model={actual} oracle={expected}"
    return cursor


# ---------------------------------------------------------------------------
# Directed fixtures — one per reachable transition, both directions
# ---------------------------------------------------------------------------

_INSIDE = ("100", "100.4", "99.6", "100")
_ABOVE = ("101", "101.5", "100.8", "101.2")
_BELOW = ("99", "99.4", "98.5", "99")
_BREACH_B = ("99.6", "99.7", "99.4", "99.49")  # bullish zone breach
_SUSTAIN_B = ("99.4", "99.5", "99.2", "99.30")
_LOW_B = ("99.4", "99.5", "99.3", "99.45")
_RECLAIM_B = ("99.5", "99.8", "99.4", "99.70")
_FAST_B = ("99.7", "103", "99.6", "102.9")


def _stream(specs: list[tuple[str, str, str, str]]) -> tuple[NormalizedCandle, ...]:
    return tuple(_candle(i, *spec) for i, spec in enumerate(specs))


def test_untouched_poi_stays_no_breach() -> None:
    cursor = _assert_prefix_parity(
        _stream([_INSIDE] + [_ABOVE] * 12), PoiDirection.BULLISH
    )
    assert cursor.reported_status == PoiLifecycleStatus.NO_BREACH


def test_breach_then_reclaim_then_fast_leg_is_false_invalidation() -> None:
    cursor = _assert_prefix_parity(
        _stream([_INSIDE, _BREACH_B, _RECLAIM_B, _FAST_B, _ABOVE, _ABOVE]),
        PoiDirection.BULLISH,
    )
    assert cursor.reported_status == (PoiLifecycleStatus.FALSE_INVALIDATION_CONFIRMED)


def test_reclaim_without_displacement() -> None:
    drift = ("99.7", "99.9", "99.65", "99.8")
    cursor = _assert_prefix_parity(
        _stream([_INSIDE, _BREACH_B, _RECLAIM_B, drift, drift, drift, _ABOVE]),
        PoiDirection.BULLISH,
    )
    assert cursor.reported_status == (PoiLifecycleStatus.RECLAIM_WITHOUT_DISPLACEMENT)


def test_genuine_invalidation_is_terminal() -> None:
    cursor = _assert_prefix_parity(
        _stream([_INSIDE, _BREACH_B, _SUSTAIN_B, _SUSTAIN_B, _SUSTAIN_B, _BELOW]),
        PoiDirection.BULLISH,
    )
    assert cursor.reported_status == (PoiLifecycleStatus.GENUINE_INVALIDATION_CONFIRMED)
    assert cursor.terminal is True


def test_reclaim_failed_path() -> None:
    """Window bars that neither reclaim (>= 99.65) nor breach (< 99.50).

    A bar closing at 99.45 would breach at its own tolerance and, sustained
    three times, produce a GENUINE invalidation instead — so the neutral band
    is what isolates the RECLAIM_FAILED outcome.
    """
    neutral = ("99.5", "99.6", "99.45", "99.55")
    cursor = _assert_prefix_parity(
        _stream([_INSIDE, _BREACH_B, neutral, neutral, neutral, _ABOVE, _ABOVE]),
        PoiDirection.BULLISH,
    )
    codes = [t.code for t in cursor.transitions()]
    assert 8 in codes, "RECLAIM_FAILED must be emitted"
    assert 10 not in codes, "a neutral window must not invalidate"


def test_breach_on_the_final_bar_stays_a_candidate() -> None:
    """No window bars yet, so production reports the un-resolved candidate."""
    cursor = _assert_prefix_parity(_stream([_INSIDE, _BREACH_B]), PoiDirection.BULLISH)
    assert cursor.reported_status == PoiLifecycleStatus.CLOSE_BREACH_CANDIDATE


def test_bearish_mirror_of_every_transition() -> None:
    breach = ("100.4", "100.6", "100.3", "100.51")
    reclaim = ("100.5", "100.6", "100.2", "100.30")
    fast = ("100.3", "100.4", "97", "97.1")
    sustain = ("100.5", "100.8", "100.4", "100.70")
    _assert_prefix_parity(
        _stream([_INSIDE, breach, reclaim, fast, _BELOW, _BELOW]),
        PoiDirection.BEARISH,
    )
    _assert_prefix_parity(
        _stream([_INSIDE, breach, sustain, sustain, sustain, _ABOVE]),
        PoiDirection.BEARISH,
    )


def test_multiple_episodes_in_one_stream() -> None:
    cursor = _assert_prefix_parity(
        _stream(
            [
                _INSIDE,
                _BREACH_B,
                _RECLAIM_B,
                _FAST_B,
                _INSIDE,
                _BREACH_B,
                _RECLAIM_B,
                _FAST_B,
                _ABOVE,
            ]
        ),
        PoiDirection.BULLISH,
    )
    breaches = [t for t in cursor.transitions() if t.code == 2]
    assert len(breaches) == 2, "false invalidation is not terminal"


# ---------------------------------------------------------------------------
# Long streams, left-edge persistence, and gaps
# ---------------------------------------------------------------------------


def test_poi_origin_far_outside_the_analytical_window_stays_live() -> None:
    """A POI created 500 bars ago is still tracked: there is no expiry."""
    specs = [_INSIDE] + [_ABOVE] * 500 + [_BREACH_B, _RECLAIM_B, _FAST_B, _ABOVE]
    cursor = _assert_prefix_parity(_stream(specs), PoiDirection.BULLISH)
    assert cursor.reported_status == (PoiLifecycleStatus.FALSE_INVALIDATION_CONFIRMED)


def test_terminal_state_survives_hundreds_of_later_bars() -> None:
    specs = [_INSIDE, _BREACH_B, _SUSTAIN_B, _SUSTAIN_B, _SUSTAIN_B] + [
        _FAST_B,
        _ABOVE,
        _INSIDE,
    ] * 100
    cursor = _assert_prefix_parity(_stream(specs), PoiDirection.BULLISH)
    assert cursor.reported_status == (PoiLifecycleStatus.GENUINE_INVALIDATION_CONFIRMED)
    genuine = [t for t in cursor.transitions() if t.code == 10]
    assert len(genuine) == 1, "a terminal POI must never resurrect"


def test_breach_before_the_left_edge_with_reclaim_after_it() -> None:
    """The episode spans the 300-bar boundary; persistence must carry it."""
    specs = (
        [_INSIDE] + [_ABOVE] * 298 + [_BREACH_B, _RECLAIM_B, _FAST_B] + [_ABOVE] * 300
    )
    _assert_prefix_parity(_stream(specs), PoiDirection.BULLISH)


def test_session_and_weekend_gaps_do_not_disturb_the_cursor() -> None:
    candles = []
    gap = 0
    for index, spec in enumerate(
        [_INSIDE, _BREACH_B, _RECLAIM_B, _FAST_B, _ABOVE, _ABOVE, _INSIDE]
    ):
        if index == 3:
            gap += 60 * 24 * 2  # a weekend-sized gap
        candles.append(_candle(index, *spec, gap_minutes=gap))
    _assert_prefix_parity(tuple(candles), PoiDirection.BULLISH)


# ---------------------------------------------------------------------------
# Randomized prefix campaign
# ---------------------------------------------------------------------------


def _random_stream(seed: int, length: int) -> tuple[NormalizedCandle, ...]:
    """Deterministic stream that actually crosses the zone repeatedly."""
    rng = random.Random(seed)
    specs: list[tuple[str, str, str, str]] = []
    price = Decimal("100")
    for _ in range(length):
        drift = Decimal(rng.randint(-90, 90)) / Decimal(100)
        open_ = price
        close = price + drift
        up = Decimal(rng.randint(0, 40)) / Decimal(100)
        dn = Decimal(rng.randint(0, 40)) / Decimal(100)
        high = max(open_, close) + up
        low = min(open_, close) - dn
        specs.append((str(open_), str(high), str(low), str(close)))
        price = close
        if price > Decimal("103") or price < Decimal("97"):
            price = Decimal("100")
    return _stream(specs)


@pytest.mark.parametrize("seed", range(14))
@pytest.mark.parametrize("direction", [PoiDirection.BULLISH, PoiDirection.BEARISH])
def test_random_prefix_campaign(seed: int, direction: PoiDirection) -> None:
    _assert_prefix_parity(_random_stream(seed, 90), direction)


@pytest.mark.parametrize("length", [20, 50, 100, 300])
def test_prefix_campaign_at_declared_lengths(length: int) -> None:
    _assert_prefix_parity(_random_stream(777, length), PoiDirection.BULLISH)


def test_randomized_campaign_reaches_every_reachable_state() -> None:
    """A campaign that never triggered a transition would prove nothing."""
    seen: set[int] = set()
    for seed in range(14):
        for direction in (PoiDirection.BULLISH, PoiDirection.BEARISH):
            candles = _random_stream(seed, 90)
            atr_values = _atr(candles)
            result = _oracle(candles, atr_values, direction)
            seen.add(L.LC_CODE[result.final_status])
            for transition in result.transitions:
                seen.add(L.TR_CODE[transition.transition_type])
    for required in (2, 4, 6, 7, 9, 10):
        assert required in seen, f"campaign never produced transition {required}"


# ---------------------------------------------------------------------------
# Cursor boundedness and the reserved states
# ---------------------------------------------------------------------------


def test_committed_boundary_advances_and_stays_bounded() -> None:
    """A cursor that never committed would pass parity but not be bounded."""
    candles = _random_stream(3, 200)
    atr_values = _atr(candles)
    cursor = L.PoiLifecycleCursor(
        zone_top=_TOP,
        zone_bottom=_BOTTOM,
        direction=PoiDirection.BULLISH,
        availability_ms=_ms(candles[0].event_time_utc),
        configuration=_CONFIG,
    )
    worst_lag = 0
    for t in range(len(candles)):
        cursor.advance(candles, atr_values, t)
        if not cursor.terminal and cursor.resume_index is not None:
            worst_lag = max(worst_lag, t + 1 - cursor.resume_index)
    assert worst_lag <= 8, f"unresolved span grew to {worst_lag} bars"
    assert worst_lag > 0


def test_reserved_states_are_never_reported_or_emitted() -> None:
    for seed in range(14):
        for direction in (PoiDirection.BULLISH, PoiDirection.BEARISH):
            cursor = _assert_prefix_parity(_random_stream(seed, 60), direction)
            assert cursor.reported_status not in L.RESERVED_UNREACHABLE
            assert all(t.code not in (3, 5) for t in cursor.transitions())


def test_no_expiry_is_ever_applied() -> None:
    specs = [_INSIDE] + [_ABOVE] * 900
    cursor = _assert_prefix_parity(_stream(specs), PoiDirection.BULLISH)
    assert cursor.reported_status == PoiLifecycleStatus.NO_BREACH
    assert cursor.terminal is False


# ---------------------------------------------------------------------------
# Pine source guards — keep the transcription pinned to the real Pine block
# ---------------------------------------------------------------------------

_P3_DEV = REPO / "tradingview/btmm_poi_btrc_scanner_p3_dev.pine"


def _pine_code() -> str:
    return "\n".join(
        line
        for line in _P3_DEV.read_text(encoding="utf-8").splitlines()
        if not line.strip().startswith("//")
    )


def test_pine_declares_the_persistent_lifecycle_functions() -> None:
    code = _pine_code()
    assert "f_poiAdvanceLifecycle(int i, int absFirst, int cbc) =>" in code
    assert "f_poiAdvanceAllLifecycles(int absFirst, int cbc) =>" in code
    assert "f_poiLegQualifies(int fromAbs, int toAbs, int absFirst, int dir) =>" in code


def test_pine_commits_only_final_outcomes() -> None:
    """The committed boundary is what makes a look-ahead walk portable."""
    code = _pine_code()
    assert "bool windowComplete = (idx + 1 + C_POI_RECLAIM_WINDOW_BARS) <= n" in code
    assert (
        "bool dispComplete = (reclaimIdx + 1 + C_POI_DISPLACEMENT_WINDOW_BARS) <= n"
        in code
    )
    assert "episodeFinal := dispComplete" in code
    assert "if windowComplete" in code


def test_pine_lifecycle_keeps_a_separate_reported_status() -> None:
    """Provisional status must not overwrite the committed one."""
    code = _pine_code()
    assert "array.set(poiStatus, i, commitStatus)" in code
    assert "array.set(poiReported, i, status)" in code


def test_pine_terminal_pois_skip_the_walk_but_keep_counting_taps() -> None:
    code = _pine_code()
    tap_block = code.split("f_poiAdvanceLifecycle")[1].split(
        "if not array.get(poiTerminal"
    )[0]
    assert "poiTapCount" in tap_block, "taps must update before the terminal gate"
    assert "if not array.get(poiTerminal, i)" in code


def test_pine_lifecycle_never_assigns_a_reserved_state() -> None:
    code = _pine_code()
    for dead in ("C_POI_LC_RECLAIM_PENDING", "C_POI_LC_DISPLACEMENT_PENDING"):
        assert f"status := {dead}" not in code
        assert f"commitStatus := {dead}" not in code


def test_pine_lifecycle_has_no_expiry_or_eviction() -> None:
    code = _pine_code()
    for banned in ("array.remove(poi", "array.shift(poi", "array.pop(poi"):
        assert banned not in code


def test_pine_leg_thresholds_match_the_hard_coded_production_values() -> None:
    code = _pine_code()
    assert "speed >= C_POI_LEG_STRONG_SPEED" in code
    assert "efficiency >= C_POI_LEG_STRONG_EFFICIENCY" in code
    assert "share >= C_POI_LEG_STRONG_SHARE" in code
    assert "speed >= C_POI_LEG_FAST_SPEED" in code


def test_pine_leg_medians_only_known_atr_values() -> None:
    """Production filters None before taking the median; zero then means SLOW."""
    code = _pine_code()
    assert "if not na(atrW)" in code
    assert "referenceAtr != 0 and pathDistance != 0" in code


def test_pine_poi_becomes_live_on_strictly_later_availability() -> None:
    code = _pine_code()
    assert "> array.get(poiAvailTime, i)" in code
