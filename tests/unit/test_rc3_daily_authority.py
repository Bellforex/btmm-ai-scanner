"""Tests for the RC3 continuous daily LEVEL-A authority
(``tests/parity_support/rc3_daily_authority.py`` on top of
``tests/parity_support/level_a_replay.py``).

Four things are under test, and they are the whole reason the authority
exists:

* **Determinism** — the same period replayed twice yields byte-identical
  records and identical digests.
* **No lookahead (Phase 13)** — for a bar N the authority may use only
  information available through N. Proved by truncate-and-extend: replay to
  a cutoff, freeze every P3/P5/P8 record, then append future bars, replay
  again, and require the frozen prefix to come back unchanged. Several
  cutoffs, all three streams.
* **Cross-day continuity (Phase 14)** — state survives day boundaries: a POI
  created on one trading day and still fresh on the next, another created on
  one day and mitigated three days later, exactly one terminal event per
  POI, and the frozen P5 terminal-bar policy.
* **The frozen author decisions** — terminal-bar eligibility, same-bar
  MITIGATED precedence, and the native P8 event contract, each asserted
  explicitly against the code that owns it.

FIXTURE STRATEGY
-----------------
Invariants that are properties of the ARCHITECTURE (continuity across days,
one-terminal-per-POI, terminal-bar eligibility, P8 ordering) are proved on a
synthetic, session-calendar-shaped series: it is cheap, it is fully
controlled, and it can be made to contain the exact multi-day lifecycles the
invariant is about. Invariants that are about the REAL period (determinism
and no-lookahead on genuine FXCM prices through the full six-timeframe
stack) are additionally anchored on a short real slice.

The synthetic series is a real CSV parsed by the real loader
(``load_v1a_csv``) — never hand-built ``NormalizedCandle`` objects — so it
exercises the same ingestion path the authority itself uses.
"""

from __future__ import annotations

import csv
import gzip
import hashlib
import json
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from itertools import pairwise
from pathlib import Path

import pytest

from btmm_ai_scanner.config.enums import Timeframe
from btmm_ai_scanner.contracts.normalized_candle import NormalizedCandle
from btmm_ai_scanner.poi.enums import PoiTerminalReason
from btmm_ai_scanner.poi.lifecycle import resolve_terminal
from btmm_ai_scanner.scanner.configuration import ScannerConfiguration
from tests.parity_support.level_a_replay import build_scanner_configuration
from tests.parity_support.p5_active_poi_loop_model import resolve_eligible_and_next_rc3
from tests.parity_support.p8_alert_oracle import (
    AlertEngine,
    AlertEvent,
    BarSnapshot,
    P8EventType,
    PoiSnapshot,
)
from tests.parity_support.rc3_daily_authority import (
    AUTHORITY_VERSION,
    DAY_MANIFEST_COLUMNS,
    SEALED_FIRST_EVENT_UTC,
    SEALED_LAST_EVENT_UTC,
    WINDOW_END_EVENT_UTC,
    WINDOW_START_EVENT_UTC,
    AuthorityResult,
    SealedRangeViolationError,
    build_authority_configuration,
    fold_period_digest,
    load_level_a_window,
    run_daily_authority,
    trading_day_of,
    write_artifacts,
)
from tests.parity_support.v1a_csv_loader import load_v1a_csv

_DATA_ROOT = Path(__file__).resolve().parents[2] / "artifacts" / "v1a_validation"

#: Real-data slices are deliberately tiny: the full-period run is a separate,
#: long-running characterization, not something the unit suite pays for.
_REAL_LOOKBACK = 40
_REAL_CUTOFF_BARS = 18
_REAL_FULL_BARS = 26


def _skip_if_no_data() -> None:
    if not (_DATA_ROOT / "v1a_raw_ohlc_full_loaded.csv").is_file():
        pytest.skip("V1-A raw OHLC artifacts are not present on disk.")
    if not (_DATA_ROOT / "v1a_raw_ohlc_M5.csv").is_file():
        pytest.skip("M5 series is not present on disk.")


# ---------------------------------------------------------------------------
# Synthetic session-calendar fixture
# ---------------------------------------------------------------------------

#: Compressed sessions: each synthetic trading day contributes this many M15
#: bars starting at 22:00 UTC of the previous calendar day, which is exactly
#: the FXCM session boundary the authority's trading-day rule keys off. The
#: count is compressed (a real session is 92-96 bars) because the invariants
#: under test are about CROSSING a boundary, not about session length.
_SYNTH_BARS_PER_DAY = 24
_SYNTH_DAYS = 5
_SYNTH_FIRST_SESSION_OPEN = datetime(2026, 8, 9, 22, 0, tzinfo=UTC)
_SYNTH_DAY0_STEPS = (0.5,) * 8 + (-0.5,) * 3 + (0.5,) * 6 + (-0.5,) * 3 + (0.5,) * 4


def _synthetic_rows() -> list[tuple[datetime, float, float, float, float, int]]:
    """A price path engineered to contain multi-day POI lifecycles.

    Day 0 warms the measurement/structure engines up. Day 1 prints a three
    bar bullish displacement, which the real detectors turn into order
    blocks / fair value gaps. Day 2 drifts away from those zones so they must
    survive a whole day untouched. Days 3-4 walk price back down through
    them, which mitigates some of them several days after they were created.
    """
    rows: list[tuple[datetime, float, float, float, float, int]] = []
    price = 100.0
    for day in range(_SYNTH_DAYS):
        start = _SYNTH_FIRST_SESSION_OPEN + timedelta(days=day)
        for index in range(_SYNTH_BARS_PER_DAY):
            event_time = start + timedelta(minutes=15 * index)
            if day == 0:
                # RC3 context gate: a bullish structure (higher high + higher
                # low) so day 1's bullish displacement maps trend-aligned
                step = _SYNTH_DAY0_STEPS[index]
                open_price = price
                close = price + step
                high = max(open_price, close) + 0.2
                low = min(open_price, close) - 0.2
            elif day == 1 and index in (8, 9, 10):
                open_price = price
                close = price + 6.0
                high = close + 0.3
                low = open_price - 0.1
            elif day == 1:
                open_price = price
                close = price + (0.3 if index % 2 == 0 else -0.3)
                high = max(open_price, close) + 0.2
                low = min(open_price, close) - 0.2
            elif day == 2:
                open_price = price
                close = price + 0.5
                high = close + 0.3
                low = open_price - 0.2
            elif day == 3:
                open_price = price
                close = price - 1.2
                high = open_price + 0.2
                low = close - 0.3
            else:
                open_price = price
                close = price - 0.6
                high = open_price + 0.2
                low = close - 0.3
            rows.append((event_time, open_price, high, low, close, 1000 + index))
            price = close
    return rows


@pytest.fixture(scope="module")
def synthetic_series(tmp_path_factory: pytest.TempPathFactory) -> tuple[NormalizedCandle, ...]:
    path = tmp_path_factory.mktemp("rc3_authority") / "synthetic_m15.csv"
    lines = ["time,open,high,low,close,volume"]
    for event_time, open_price, high, low, close, volume in _synthetic_rows():
        epoch_ms = int(event_time.timestamp() * 1000)
        lines.append(
            f"{epoch_ms},{open_price:.2f},{high:.2f},{low:.2f},{close:.2f},{volume}"
        )
    path.write_text("\n".join(lines), encoding="utf-8")
    return load_v1a_csv(path, Timeframe.M15)


def _synthetic_configuration() -> ScannerConfiguration:
    return build_scanner_configuration(
        required_timeframes=frozenset({Timeframe.M15}),
        optional_timeframes=frozenset(),
        minimum_price_tick=Decimal("0.01"),
    )


def _run_synthetic(
    series: tuple[NormalizedCandle, ...], *, bars: int | None = None
) -> AuthorityResult:
    return run_daily_authority(
        host_timeframe=Timeframe.M15,
        host_series=series if bars is None else series[:bars],
        context_series={},
        configuration=_synthetic_configuration(),
        retain_rows=True,
    )


@pytest.fixture(scope="module")
def synthetic_result(
    synthetic_series: tuple[NormalizedCandle, ...],
) -> AuthorityResult:
    return _run_synthetic(synthetic_series)


@dataclass(frozen=True)
class _Row:
    fields: dict[str, str]

    def __getitem__(self, key: str) -> str:
        return self.fields[key]


def _parse(lines: list[str]) -> list[_Row]:
    return [_Row(dict(part.split("=", 1) for part in line.split("|"))) for line in lines]


# ---------------------------------------------------------------------------
# Determinism
# ---------------------------------------------------------------------------


def test_synthetic_period_is_deterministic(
    synthetic_series: tuple[NormalizedCandle, ...],
) -> None:
    first = _run_synthetic(synthetic_series)
    second = _run_synthetic(synthetic_series)
    assert first.retained_p3 == second.retained_p3
    assert first.retained_p5 == second.retained_p5
    assert first.retained_p8 == second.retained_p8
    assert [day.as_row() for day in first.days] == [day.as_row() for day in second.days]
    assert first.period_p3_digest == second.period_p3_digest
    assert first.period_p5_digest == second.period_p5_digest
    assert first.period_p8_digest == second.period_p8_digest


def _run_real(bars: int) -> AuthorityResult:
    window = load_level_a_window(
        _DATA_ROOT, context_lookback_bars=_REAL_LOOKBACK, max_bars=bars
    )
    return run_daily_authority(
        host_timeframe=window.host_timeframe,
        host_series=window.host_series,
        context_series=window.context_series,
        configuration=build_authority_configuration(),
        provenance=window.provenance,
        retain_rows=True,
    )


@pytest.fixture(scope="module")
def real_cutoff_result() -> AuthorityResult:
    _skip_if_no_data()
    return _run_real(_REAL_CUTOFF_BARS)


@pytest.fixture(scope="module")
def real_full_result() -> AuthorityResult:
    _skip_if_no_data()
    return _run_real(_REAL_FULL_BARS)


def test_real_period_is_deterministic(real_cutoff_result: AuthorityResult) -> None:
    _skip_if_no_data()
    again = _run_real(_REAL_CUTOFF_BARS)
    assert again.retained_p3 == real_cutoff_result.retained_p3
    assert again.retained_p5 == real_cutoff_result.retained_p5
    assert again.retained_p8 == real_cutoff_result.retained_p8
    assert again.period_p3_digest == real_cutoff_result.period_p3_digest
    assert again.period_p5_digest == real_cutoff_result.period_p5_digest
    assert again.period_p8_digest == real_cutoff_result.period_p8_digest


# ---------------------------------------------------------------------------
# Phase 13 — no lookahead
# ---------------------------------------------------------------------------


def _prefix_up_to(rows: list[str], cutoff_bar_ms: int) -> list[str]:
    parsed = _parse(rows)
    return [
        line
        for line, row in zip(rows, parsed, strict=True)
        if int(row["bar_ms"]) <= cutoff_bar_ms
    ]


@pytest.mark.parametrize("cutoff", [30, 60, 96])
def test_no_lookahead_on_synthetic_across_cutoffs(
    synthetic_series: tuple[NormalizedCandle, ...],
    synthetic_result: AuthorityResult,
    cutoff: int,
) -> None:
    """Replay to ``cutoff``, freeze, then replay the longer series and
    require every frozen P3/P5/P8 record to come back byte-identical.

    If ANY value at bar N were derived from a bar after N, extending the
    series would change it — so an unchanged prefix is a direct proof of the
    no-lookahead property for all three streams at once.
    """
    truncated = _run_synthetic(synthetic_series, bars=cutoff)
    cutoff_bar_ms = int(_parse(truncated.retained_p3)[-1]["bar_ms"])

    assert truncated.retained_p3 == _prefix_up_to(
        synthetic_result.retained_p3, cutoff_bar_ms
    )
    assert truncated.retained_p5 == _prefix_up_to(
        synthetic_result.retained_p5, cutoff_bar_ms
    )
    assert truncated.retained_p8 == _prefix_up_to(
        synthetic_result.retained_p8, cutoff_bar_ms
    )


def test_no_lookahead_preserves_completed_daily_digests(
    synthetic_series: tuple[NormalizedCandle, ...], synthetic_result: AuthorityResult
) -> None:
    """A trading day that had already CLOSED before the cutoff must keep its
    exact daily digests once later days are appended."""
    cutoff = _SYNTH_BARS_PER_DAY * 3
    truncated = _run_synthetic(synthetic_series, bars=cutoff)
    completed = {day.trading_day: day for day in truncated.days[:-1]}
    assert completed, "the cutoff must close at least one full trading day"
    full_by_day = {day.trading_day: day for day in synthetic_result.days}
    for name, day in completed.items():
        assert full_by_day[name].p3_digest == day.p3_digest
        assert full_by_day[name].p5_digest == day.p5_digest
        assert full_by_day[name].p8_digest == day.p8_digest
        assert full_by_day[name].as_row() == day.as_row()


def test_no_lookahead_on_real_data(
    real_cutoff_result: AuthorityResult, real_full_result: AuthorityResult
) -> None:
    """The same truncate-and-extend proof, on genuine FXCM prices through the
    full six-timeframe stack."""
    _skip_if_no_data()
    cutoff_bar_ms = int(_parse(real_cutoff_result.retained_p3)[-1]["bar_ms"])
    assert real_full_result.bars_processed > real_cutoff_result.bars_processed
    assert real_cutoff_result.retained_p3 == _prefix_up_to(
        real_full_result.retained_p3, cutoff_bar_ms
    )
    assert real_cutoff_result.retained_p5 == _prefix_up_to(
        real_full_result.retained_p5, cutoff_bar_ms
    )
    assert real_cutoff_result.retained_p8 == _prefix_up_to(
        real_full_result.retained_p8, cutoff_bar_ms
    )


# ---------------------------------------------------------------------------
# Phase 14 — cross-day continuity
# ---------------------------------------------------------------------------


def _days_by_poi(rows: list[_Row]) -> dict[str, list[str]]:
    seen: dict[str, list[str]] = defaultdict(list)
    for row in rows:
        day = row["trading_day"]
        if not seen[row["poi_idx"]] or seen[row["poi_idx"]][-1] != day:
            seen[row["poi_idx"]].append(day)
    return seen


def test_state_is_not_reset_at_a_day_boundary(
    synthetic_result: AuthorityResult,
) -> None:
    """The replay is one walk: POIs must be evaluated on several distinct
    trading days, which is impossible if days were processed independently
    and concatenated."""
    spans = _days_by_poi(_parse(synthetic_result.retained_p5))
    multi_day = {poi: days for poi, days in spans.items() if len(days) > 1}
    assert len(multi_day) >= 10
    assert max(len(days) for days in multi_day.values()) >= 3
    # Trading days must be contiguous and strictly increasing per POI — a
    # reset-and-restart would re-open a day that had already closed.
    for days in multi_day.values():
        assert days == sorted(days)
        assert len(set(days)) == len(days)


def test_poi_created_day_one_is_still_fresh_the_next_day(
    synthetic_result: AuthorityResult,
) -> None:
    p3 = _parse(synthetic_result.retained_p3)
    by_poi: dict[str, list[_Row]] = defaultdict(list)
    for row in p3:
        by_poi[row["poi_idx"]].append(row)

    carried = [
        rows
        for rows in by_poi.values()
        if rows[0]["fresh_active"] == "1"
        and rows[-1]["fresh_active"] == "1"
        and rows[-1]["trading_day"] > rows[0]["trading_day"]
    ]
    assert carried, "no POI stayed fresh into a later trading day"
    # Identity — not geometry — is what must survive the boundary. A period
    # level (CURRENT_DAY_HIGH and friends) keeps one identity while its level
    # legitimately moves, so asserting zone equality here would be asserting
    # the wrong thing.
    for sample in carried:
        for key in (
            "poi_record_id",
            "poi_type",
            "direction",
            "source_timeframe",
            "effective_timeframe",
        ):
            assert sample[0][key] == sample[-1][key], key
    static = [
        rows
        for rows in carried
        if rows[0]["zone_top"] == rows[-1]["zone_top"]
        and rows[0]["source_time_utc"] == rows[-1]["source_time_utc"]
    ]
    assert static, "no fixed-geometry POI carried its zone across a day boundary"


def test_poi_created_one_day_is_mitigated_several_days_later(
    synthetic_result: AuthorityResult,
) -> None:
    p3 = _parse(synthetic_result.retained_p3)
    by_poi: dict[str, list[_Row]] = defaultdict(list)
    for row in p3:
        by_poi[row["poi_idx"]].append(row)

    late_terminals = []
    for poi_idx, rows in by_poi.items():
        terminal = [row for row in rows if row["terminal"] == "1"]
        if not terminal:
            continue
        span = len({row["trading_day"] for row in rows})
        if terminal[0]["trading_day"] > rows[0]["trading_day"] and span >= 3:
            late_terminals.append((poi_idx, rows[0], terminal[0], span))

    assert late_terminals, (
        "no POI was created on one trading day and terminated three or more "
        "days later — the cross-day lifecycle this fixture exists to prove"
    )
    _, first, terminal, _ = late_terminals[0]
    assert terminal["terminal_reason"] == PoiTerminalReason.MITIGATED.value
    assert terminal["mitigation_time_utc"] != ""
    assert first["poi_record_id"] == terminal["poi_record_id"]


def test_exactly_one_terminal_event_per_poi(
    synthetic_result: AuthorityResult,
) -> None:
    counts = Counter(
        row["poi_idx"]
        for row in _parse(synthetic_result.retained_p8)
        if row["event_type"] == P8EventType.POI_TERMINAL.value
    )
    assert counts, "the fixture must produce at least one terminal event"
    assert all(count == 1 for count in counts.values()), dict(counts)
    assert sum(counts.values()) == synthetic_result.p8_events_by_type[
        P8EventType.POI_TERMINAL.value
    ]


def test_terminal_events_carry_a_reason(synthetic_result: AuthorityResult) -> None:
    reasons = {
        row["terminal_reason"]
        for row in _parse(synthetic_result.retained_p8)
        if row["event_type"] == P8EventType.POI_TERMINAL.value
    }
    assert reasons
    assert reasons <= {
        PoiTerminalReason.MITIGATED.value,
        PoiTerminalReason.INVALIDATED.value,
    }


# ---------------------------------------------------------------------------
# Frozen author decision 1 — the P5 terminal-bar policy
# ---------------------------------------------------------------------------


def test_poi_is_evaluated_on_its_terminal_bar_and_never_after(
    synthetic_result: AuthorityResult,
) -> None:
    """FROZEN AUTHOR DECISION: a POI remains eligible for P5 on the bar it
    goes terminal and is excluded starting from the FOLLOWING bar."""
    p3 = _parse(synthetic_result.retained_p3)
    p5 = _parse(synthetic_result.retained_p5)

    terminal_bar: dict[str, int] = {}
    for row in p3:
        if row["terminal"] == "1" and row["poi_idx"] not in terminal_bar:
            terminal_bar[row["poi_idx"]] = int(row["bar_ms"])
    assert terminal_bar

    p5_bars: dict[str, set[int]] = defaultdict(set)
    for row in p5:
        p5_bars[row["poi_idx"]].add(int(row["bar_ms"]))

    for poi_idx, bar_ms in terminal_bar.items():
        assert bar_ms in p5_bars[poi_idx], (
            f"POI {poi_idx} lost its P5 evaluation on its own terminal bar"
        )
        later = {bar for bar in p5_bars[poi_idx] if bar > bar_ms}
        assert not later, (
            f"POI {poi_idx} was still evaluated after its terminal bar: {sorted(later)}"
        )


def test_terminal_bar_policy_in_the_set_algebra() -> None:
    """The same decision, asserted directly on the function that owns it, so
    the policy is pinned even when no fixture happens to exercise it."""
    poi = "11111111-1111-1111-1111-111111111111"
    other = "22222222-2222-2222-2222-222222222222"

    # Bar N: the POI goes terminal (fresh_active flips False) while it was
    # active entering the bar -> still eligible, dropped from the next set.
    eligible, next_active = resolve_eligible_and_next_rc3(
        {poi: False, other: True}, frozenset({poi, other})
    )
    assert poi in eligible
    assert poi not in next_active
    assert other in next_active

    # Bar N+1: it is no longer carried in, and is terminal, so it is gone.
    eligible_next, _ = resolve_eligible_and_next_rc3(
        {poi: False, other: True}, next_active
    )
    assert poi not in eligible_next


# ---------------------------------------------------------------------------
# Frozen author decision 2 — same-bar terminal precedence
# ---------------------------------------------------------------------------


def test_same_bar_mitigation_beats_invalidation() -> None:
    """FROZEN AUTHOR DECISION: when mitigation and invalidation become
    eligible on the SAME bar, MITIGATED wins."""
    same_bar = datetime(2026, 8, 12, 9, 30, tzinfo=UTC)
    reason, terminal_time, mitigation_time = resolve_terminal(same_bar, same_bar)
    assert reason is PoiTerminalReason.MITIGATED
    assert terminal_time == same_bar
    assert mitigation_time == same_bar


def test_strictly_earlier_invalidation_still_wins() -> None:
    """The complement of the decision above: precedence is same-BAR only, it
    is not a blanket preference for mitigation."""
    earlier = datetime(2026, 8, 12, 9, 15, tzinfo=UTC)
    later = datetime(2026, 8, 12, 9, 30, tzinfo=UTC)
    reason, terminal_time, mitigation_time = resolve_terminal(later, earlier)
    assert reason is PoiTerminalReason.INVALIDATED
    assert terminal_time == earlier
    assert mitigation_time is None


# ---------------------------------------------------------------------------
# Frozen author decision 3 — the native P8 contract
# ---------------------------------------------------------------------------


def _priority(event_type: str) -> int:
    return {
        P8EventType.POI_ACTIVATED.value: 0,
        P8EventType.BTMM_VALIDATED.value: 1,
        P8EventType.PERMISSION_ENTERED_ACTIONABLE.value: 2,
        P8EventType.PERMISSION_LOST_ACTIONABLE.value: 2,
        P8EventType.POI_TERMINAL.value: 3,
    }[event_type]


def test_p8_native_identity_is_type_poi_and_bar() -> None:
    """FROZEN AUTHOR DECISION: native identity is
    ``(event_type, poi_idx, bar_ms)``; ``terminal_reason`` is PAYLOAD."""
    base = {
        "event_type": P8EventType.POI_TERMINAL,
        "bar_ms": 1786312800000,
        "poi_idx": 7,
        "poi_bullish": True,
        "tier": 1,
        "btmm_valid": True,
        "permission": 0,
        "lifecycle": 3,
    }
    mitigated = AlertEvent(**base, terminal_reason=PoiTerminalReason.MITIGATED)
    invalidated = AlertEvent(**base, terminal_reason=PoiTerminalReason.INVALIDATED)
    assert mitigated.event_key == invalidated.event_key
    assert mitigated.event_key == (P8EventType.POI_TERMINAL, 7, 1786312800000)
    assert mitigated != invalidated


def test_p8_events_are_written_in_the_native_engine_order(
    synthetic_result: AuthorityResult,
) -> None:
    """FROZEN AUTHOR DECISION: same-bar ordering is ``poi_idx`` then event
    priority, and the authority must NOT re-sort by any semantic key."""
    rows = _parse(synthetic_result.retained_p8)
    assert rows
    by_bar: dict[int, list[_Row]] = defaultdict(list)
    for row in rows:
        by_bar[int(row["bar_ms"])].append(row)

    multi_event_bars = 0
    for bar_rows in by_bar.values():
        keys = [
            (int(row["poi_idx"]), _priority(row["event_type"])) for row in bar_rows
        ]
        assert keys == sorted(keys), keys
        assert [int(row["sequence_in_bar"]) for row in bar_rows] == list(
            range(len(bar_rows))
        )
        if len(bar_rows) > 1:
            multi_event_bars += 1
    assert multi_event_bars, "fixture must contain a bar with several events"

    # Bars themselves are strictly increasing in emission order — a stream
    # that had been re-sorted by event type would not be.
    emitted_bars = [int(row["bar_ms"]) for row in rows]
    assert emitted_bars == sorted(emitted_bars)
    types_in_order = [row["event_type"] for row in rows]
    assert types_in_order != sorted(types_in_order), (
        "the stream is grouped by event type, which means it was re-sorted"
    )


def test_p8_event_identity_is_unique_across_the_whole_period(
    synthetic_result: AuthorityResult,
) -> None:
    keys = [
        (row["event_type"], row["poi_idx"], row["bar_ms"])
        for row in _parse(synthetic_result.retained_p8)
    ]
    assert len(keys) == len(set(keys))


def test_p8_ordering_is_deterministic_across_a_day_boundary(
    synthetic_series: tuple[NormalizedCandle, ...], synthetic_result: AuthorityResult
) -> None:
    """The boundary is where an implementation that re-primed, re-sorted or
    re-keyed per day would diverge; two independent runs must agree bar for
    bar, including on the first bar of each new trading day."""
    again = _run_synthetic(synthetic_series)
    assert again.retained_p8 == synthetic_result.retained_p8

    rows = _parse(synthetic_result.retained_p8)
    first_bar_of_day: dict[str, int] = {}
    for row in rows:
        first_bar_of_day.setdefault(row["trading_day"], int(row["bar_ms"]))
    assert len(first_bar_of_day) >= 3, "need several trading days with events"


def test_activation_fires_when_a_poi_idx_first_enters_the_known_set(
    synthetic_result: AuthorityResult,
) -> None:
    """FROZEN AUTHOR DECISION: activation is "first entry into the engine's
    known set", not "the POI was created". POIs already present when the
    engine is PRIMED are learned silently (the fresh-attach contract), so
    they are excluded here."""
    p5 = _parse(synthetic_result.retained_p5)
    p8 = _parse(synthetic_result.retained_p8)

    first_p5_bar: dict[str, int] = {}
    for row in p5:
        first_p5_bar.setdefault(row["poi_idx"], int(row["bar_ms"]))
    prime_bar = min(first_p5_bar.values())

    activations: dict[str, list[int]] = defaultdict(list)
    for row in p8:
        if row["event_type"] == P8EventType.POI_ACTIVATED.value:
            activations[row["poi_idx"]].append(int(row["bar_ms"]))

    primed = {poi for poi, bar in first_p5_bar.items() if bar == prime_bar}
    assert len(primed) == synthetic_result.primed_poi_count
    for poi in primed:
        assert poi not in activations, (
            f"POI {poi} was present at prime and must not be announced as new"
        )
    for poi, bar in first_p5_bar.items():
        if poi in primed:
            continue
        assert activations[poi] == [bar], (
            f"POI {poi} must be activated exactly once, on its first evaluated bar"
        )


def test_priming_emits_nothing_and_process_requires_it() -> None:
    """The two halves of the fresh-attach contract the authority relies on."""
    engine = AlertEngine()
    snapshot = BarSnapshot(
        bar_ms=1,
        pois=(
            PoiSnapshot(
                poi_idx=0,
                poi_bullish=True,
                tier=1,
                terminal=False,
                btmm_valid=True,
                permission=0,
                lifecycle=3,
            ),
        ),
    )
    with pytest.raises(RuntimeError):
        AlertEngine().process(snapshot)
    engine.prime(snapshot)
    assert engine.process(BarSnapshot(bar_ms=2, pois=snapshot.pois)) == []


# ---------------------------------------------------------------------------
# Frozen author decision 4 — the trading-day partition, and the manifest
# ---------------------------------------------------------------------------


def test_trading_day_follows_the_fxcm_session_not_the_calendar_day() -> None:
    assert trading_day_of(datetime(2026, 8, 9, 22, 0, tzinfo=UTC)) == "2026-08-10"
    assert trading_day_of(datetime(2026, 8, 10, 0, 0, tzinfo=UTC)) == "2026-08-10"
    assert trading_day_of(datetime(2026, 8, 10, 20, 45, tzinfo=UTC)) == "2026-08-10"
    assert trading_day_of(datetime(2026, 8, 10, 22, 0, tzinfo=UTC)) == "2026-08-11"


def test_manifest_days_are_contiguous_and_cover_every_bar(
    synthetic_result: AuthorityResult,
) -> None:
    days = synthetic_result.days
    assert [day.trading_day for day in days] == sorted(
        day.trading_day for day in days
    )
    assert len({day.trading_day for day in days}) == len(days)
    assert sum(day.bars_processed for day in days) == synthetic_result.bars_processed
    assert sum(day.p5_rows for day in days) == synthetic_result.p5_rows_total
    assert sum(day.p8_events for day in days) == synthetic_result.p8_events_total
    for day in days:
        assert day.first_bar_ms <= day.last_bar_ms
    for earlier, later in pairwise(days):
        assert earlier.last_bar_ms < later.first_bar_ms


def test_period_digest_is_a_reproducible_fold_of_the_daily_digests(
    synthetic_result: AuthorityResult, tmp_path: Path
) -> None:
    """Re-derive the period digests from nothing but the written manifest CSV
    and ``sha256`` — the fold must be reproducible by a third party."""
    paths = write_artifacts(synthetic_result, tmp_path)
    with paths["csv"].open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert [row["trading_day"] for row in rows] == [
        day.trading_day for day in synthetic_result.days
    ]
    assert tuple(rows[0]) == DAY_MANIFEST_COLUMNS

    for stream, expected in (
        ("P3", synthetic_result.period_p3_digest),
        ("P5", synthetic_result.period_p5_digest),
        ("P8", synthetic_result.period_p8_digest),
    ):
        column = f"{stream.lower()}_digest"
        acc = hashlib.sha256(f"{AUTHORITY_VERSION}|{stream}".encode()).hexdigest()
        for row in rows:
            acc = hashlib.sha256(
                f"{acc}|{row['trading_day']}|{row[column]}".encode()
            ).hexdigest()
        assert acc == expected


def test_written_artifacts_match_the_streams_and_the_in_memory_result(
    synthetic_series: tuple[NormalizedCandle, ...], tmp_path: Path
) -> None:
    """End-to-end check of the artifact writer, including the per-trading-day
    flush: the NDJSON streams, the manifest and the summary must agree."""
    result = run_daily_authority(
        host_timeframe=Timeframe.M15,
        host_series=synthetic_series,
        context_series={},
        configuration=_synthetic_configuration(),
        output_dir=tmp_path,
        retain_rows=True,
    )
    assert result.complete is True

    counts = {}
    for name, expected in (
        ("p3_registry_rows.ndjson.gz", result.p3_rows),
        ("p5_assessment_rows.ndjson.gz", result.p5_rows_total),
        ("p8_event_rows.ndjson.gz", result.p8_events_total),
    ):
        with gzip.open(tmp_path / name, "rt", encoding="utf-8") as handle:
            counts[name] = sum(1 for _ in handle)
        assert counts[name] == expected, name

    summary = json.loads((tmp_path / "run_summary.json").read_text(encoding="utf-8"))
    assert summary["complete"] is True
    assert summary["bars_processed"] == len(synthetic_series)
    assert summary["p5_rows"] == len(result.retained_p5)
    assert summary["p8_events"] == len(result.retained_p8)

    manifest = json.loads(
        (tmp_path / "daily_authority_manifest.json").read_text(encoding="utf-8")
    )
    assert manifest["days"] == [day.as_row() for day in result.days]
    assert manifest["period_digests"]["p3"] == result.period_p3_digest


def test_a_partial_flush_only_reports_closed_trading_days(
    synthetic_series: tuple[NormalizedCandle, ...],
    synthetic_result: AuthorityResult,
    tmp_path: Path,
) -> None:
    """A mid-replay flush must describe whole trading days that will never
    change again, not a half-processed one — otherwise a long run that is
    stopped early leaves evidence that silently disagrees with a full run."""
    class _StopsPartWayThrough(list[NormalizedCandle]):
        """Behaves exactly like the real host series until the replay is
        part-way into the third trading day, then dies — the crash / kill /
        session-timeout case the flush exists for."""

        def __iter__(self):  # type: ignore[no-untyped-def]
            for index, candle in enumerate(list.__iter__(self)):
                if index == _SYNTH_BARS_PER_DAY * 2 + 5:
                    raise KeyboardInterrupt("simulated interruption")
                yield candle

    output_dir = tmp_path / "interrupted"
    with pytest.raises(KeyboardInterrupt):
        run_daily_authority(
            host_timeframe=Timeframe.M15,
            host_series=_StopsPartWayThrough(synthetic_series),
            context_series={},
            configuration=_synthetic_configuration(),
            output_dir=output_dir,
        )

    manifest = json.loads(
        (output_dir / "daily_authority_manifest.json").read_text(encoding="utf-8")
    )
    summary = json.loads((output_dir / "run_summary.json").read_text(encoding="utf-8"))
    assert summary["complete"] is False
    assert len(manifest["days"]) == 2, "only the two CLOSED days may be reported"

    # Every reported day must be byte-identical to the same day in the full
    # run, digests included — a partial artifact is a prefix, never a
    # different answer.
    full_by_day = {day.trading_day: day.as_row() for day in synthetic_result.days}
    for row in manifest["days"]:
        assert full_by_day[row["trading_day"]] == row
    assert summary["bars_processed"] == sum(
        row["bars_processed"] for row in manifest["days"]
    )
    assert summary["p5_rows"] == sum(row["p5_rows"] for row in manifest["days"])


def test_period_digest_reacts_to_day_order_and_content() -> None:
    days = [("2026-08-10", "aa"), ("2026-08-11", "bb")]
    base = fold_period_digest("P3", days)
    assert base != fold_period_digest("P3", list(reversed(days)))
    assert base != fold_period_digest("P3", [("2026-08-10", "aa")])
    assert base != fold_period_digest("P5", days)
    assert base == fold_period_digest("P3", days)


# ---------------------------------------------------------------------------
# Window integrity
# ---------------------------------------------------------------------------


def test_window_is_six_timeframes_and_clear_of_the_sealed_range() -> None:
    _skip_if_no_data()
    window = load_level_a_window(_DATA_ROOT, context_lookback_bars=8, max_bars=4)
    assert window.host_timeframe is Timeframe.M15
    assert set(window.context_series) == {
        Timeframe.W1,
        Timeframe.D1,
        Timeframe.H4,
        Timeframe.H1,
        Timeframe.M5,
    }
    assert window.host_series[0].event_time_utc == WINDOW_START_EVENT_UTC
    for candle in window.host_series:
        assert not (
            SEALED_FIRST_EVENT_UTC
            <= candle.event_time_utc
            <= SEALED_LAST_EVENT_UTC
        )
    assert window.provenance["evidence_level"] == "A"
    # M5 has no pre-window history at all: its source file begins at the
    # window's own first instant. Disclosed, not silently trimmed.
    m5 = next(s for s in window.provenance["series"] if s["timeframe"] == "M5")
    assert m5["pre_window_bars"] == 0
    assert m5["pre_window_bars_available"] == 0
    # Every other context timeframe does carry pre-window background.
    for series in window.provenance["series"]:
        if series["timeframe"] in {"W1", "D1", "H4", "H1"}:
            assert series["pre_window_bars"] > 0


def test_full_window_bounds_are_the_declared_six_timeframe_period() -> None:
    _skip_if_no_data()
    window = load_level_a_window(_DATA_ROOT, context_lookback_bars=0)
    assert window.host_series[0].event_time_utc == WINDOW_START_EVENT_UTC
    assert window.host_series[-1].event_time_utc == WINDOW_END_EVENT_UTC
    days = {trading_day_of(c.event_time_utc) for c in window.host_series}
    assert min(days) == "2026-08-10"
    assert max(days) == "2026-09-04"


def test_a_window_inside_the_sealed_range_is_refused() -> None:
    _skip_if_no_data()
    with pytest.raises(SealedRangeViolationError):
        load_level_a_window(
            _DATA_ROOT,
            window_start_event_utc=SEALED_FIRST_EVENT_UTC,
            window_end_event_utc=SEALED_FIRST_EVENT_UTC + timedelta(hours=1),
            context_lookback_bars=0,
        )
