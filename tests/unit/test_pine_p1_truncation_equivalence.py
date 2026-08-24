"""P1-PERF-4 — bounded historical execution (``calc_bars_count``).

``calc_bars_count = N`` makes TradingView execute the script on only the last
``N`` bars, so every persistent Pine variable starts empty part-way through the
dataset. These tests pin the reason that is safe.

The argument has one load-bearing step. Every value a protected bar reads comes
from arrays pruned to ``lookbackWindow`` candles — except the Wilder ATR, which
is an IIR recurrence carried across the whole accessible history. So a truncated
run differs from a full-history run *only* while its ATR still remembers its own
seed, and once the two ATR series are identical over everything the protected
region reads, the detectors receive byte-identical inputs and must agree.

That makes the cheap ATR test below a proof rather than a sample, and the
expensive end-to-end replay a confirmation of it. The wider sweep across all
three canonical datasets, twenty adversarial fixtures and the randomized
campaign lives in ``tests/performance_support`` because of its runtime; its
recorded results are in the performance document.
"""

from __future__ import annotations

from datetime import UTC
from decimal import Decimal
from pathlib import Path

import pytest
from performance_support import p1_sr_diagnostics as diagnostics
from performance_support import p1_truncation as truncation
from performance_support import p1_truncation_fixtures as fixtures

from btmm_ai_scanner.config.enums import InternalSymbol, Timeframe
from btmm_ai_scanner.contracts.normalized_candle import NormalizedCandle
from btmm_ai_scanner.domain.configuration import MarketMeasurementConfiguration
from btmm_ai_scanner.measurements.atr import compute_atr_series

# The values the Pine source declares. Kept here so a change to either side has
# to be a deliberate, reviewed change to both.
CALC_BARS_COUNT = 1800
MIN_CALC_BARS = 1250
LOOKBACK = 300

# P1-PERF-4A: the region that must be exact is not "the last 300 bars", it is
# every bar the publication gate admits — processed counts 1250..1800 inside a
# full-size run. Proving only the last 300 would leave 251 publishable bars
# unverified.
PUBLISHED_BARS = CALC_BARS_COUNT - MIN_CALC_BARS + 1  # 551

# Largest warm-up observed before the truncated ATR became IDENTICAL to the
# full-history ATR: 920 bars over 549 start positions on canonical FXCM data,
# 945 bars on fixtures that deliberately distort the seed by 5000x.
MEASURED_WARMUP_CEILING = 950

_DATA_ROOT = Path(
    r"C:\Users\user\Desktop\BTMM_REAL_DATA\DATASETS\xauusd_2026_07_pilot\candles"
)
_DATASETS = {
    "M1": (Timeframe.M1, _DATA_ROOT / "xauusd_m1.csv"),
    "M5": (Timeframe.M5, _DATA_ROOT / "xauusd_m5.csv"),
    "M15": (Timeframe.M15, _DATA_ROOT / "xauusd_m15.csv"),
}


def _configuration() -> MarketMeasurementConfiguration:
    return MarketMeasurementConfiguration(minimum_price_tick=Decimal("0.01"))


_CANDLE_CACHE: dict[str, tuple[NormalizedCandle, ...]] = {}


def _load(name: str) -> tuple[NormalizedCandle, ...]:
    timeframe, path = _DATASETS[name]
    if not path.exists():  # pragma: no cover - depends on the local data drive
        pytest.skip(f"canonical FXCM {name} dataset is not present at {path}")
    if name not in _CANDLE_CACHE:
        rows = diagnostics.load_rows(path)
        _CANDLE_CACHE[name] = diagnostics.build_candles(
            rows, InternalSymbol.XAUUSD, timeframe, "FXCM"
        )
    return _CANDLE_CACHE[name]


# ---------------------------------------------------------------------------
# The horizon arithmetic. Pure reasoning, no data — these are the claims the
# measurements below are allowed to support.
# ---------------------------------------------------------------------------


def test_validity_floor_is_window_plus_measured_warmup() -> None:
    """A bar is valid once its window's LEFT EDGE has an exact ATR."""
    assert MIN_CALC_BARS >= LOOKBACK + MEASURED_WARMUP_CEILING, (
        "the per-bar validity floor must cover the whole analytical window plus "
        "the ATR warm-up, or the oldest bar in the window carries a seed-tainted "
        "ATR into the detectors"
    )


def test_selected_horizon_makes_every_published_bar_valid() -> None:
    """The EARLIEST published bar is the binding one, not the last bar."""
    bars_processed_at_earliest_published = CALC_BARS_COUNT - (PUBLISHED_BARS - 1)
    assert bars_processed_at_earliest_published >= MIN_CALC_BARS, (
        f"calc_bars_count={CALC_BARS_COUNT} leaves the earliest of the last "
        f"{PUBLISHED_BARS} bars with only "
        f"{bars_processed_at_earliest_published} processed bars, below the "
        f"{MIN_CALC_BARS} floor"
    )


def test_selected_horizon_is_not_overfitted_to_the_minimum() -> None:
    """PERF-4 chose a documented margin, not the smallest passing number.

    The first exactly-matching horizon measured on real data was 1200. Sitting
    on that would make the script correct only for the datasets that happened to
    be tested.
    """
    assert PUBLISHED_BARS >= 300 + 200, (
        "the horizon should keep a real margin above the 300-bar analytical "
        f"window; only {PUBLISHED_BARS} publishable bars"
    )


def test_pine_declares_the_validated_horizon() -> None:
    source = Path("tradingview/btmm_poi_btrc_scanner_v1.pine").read_text(
        encoding="utf-8"
    )
    assert f"calc_bars_count = {CALC_BARS_COUNT}" in source
    assert f"int C_P1_CALC_BARS     = {CALC_BARS_COUNT}" in source
    assert f"int C_P1_MIN_CALC_BARS = {MIN_CALC_BARS}" in source


# ---------------------------------------------------------------------------
# Harness fidelity. If these fail, every measurement taken through the harness
# is meaningless, so they come before the measurements.
# ---------------------------------------------------------------------------


def test_atr_injection_is_transparent() -> None:
    """Production Python stays the oracle.

    The harness hands detectors the ATR Pine would have had. Handing them the
    series they would have computed for themselves must change nothing.
    """
    candles = _load("M15")
    truncation.assert_injection_is_transparent(candles[:400], _configuration())


def test_displacement_tail_slice_matches_the_whole_window() -> None:
    candles = _load("M15")
    truncation.assert_displacement_tail_is_equivalent(candles[:400], _configuration())


# ---------------------------------------------------------------------------
# The measurement the horizon rests on.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("dataset", sorted(_DATASETS))
def test_measured_atr_warmup_stays_under_the_ceiling(dataset: str) -> None:
    """The Wilder recurrence must actually forget its seed, and do it in time."""
    candles = _load(dataset)
    configuration = _configuration()
    total = len(candles)
    observed: list[int] = []
    for start in range(500, total - CALC_BARS_COUNT, 700):
        warmup = truncation.atr_convergence_bars(
            candles, start, configuration.atr_period
        )
        assert warmup is not None, (
            f"{dataset}: a truncated ATR started at {start} never became "
            "identical to the full-history ATR; no horizon can be safe"
        )
        observed.append(warmup)
    assert observed, f"{dataset}: no start positions were exercised"
    assert max(observed) <= MEASURED_WARMUP_CEILING, (
        f"{dataset}: ATR warm-up reached {max(observed)} bars, above the "
        f"{MEASURED_WARMUP_CEILING} ceiling the validity floor was built on"
    )


@pytest.mark.parametrize("dataset", sorted(_DATASETS))
def test_truncated_atr_is_exact_everywhere_the_protected_region_reads(
    dataset: str,
) -> None:
    """The sufficient condition, checked directly.

    The published region reads ATR values from the left edge of the oldest
    publishable bar's window onward. If the truncated series matches the
    full-history series across all of that, the detectors cannot tell the two
    runs apart.
    """
    candles = _load(dataset)
    configuration = _configuration()
    total = len(candles)
    start = total - CALC_BARS_COUNT
    earliest_read = total - PUBLISHED_BARS - (LOOKBACK - 1)

    full = compute_atr_series(tuple(candles), configuration.atr_period)
    truncated = compute_atr_series(tuple(candles[start:]), configuration.atr_period)

    mismatched = [
        index
        for index in range(earliest_read, total)
        if truncated[index - start] != full[index]
    ]
    assert not mismatched, (
        f"{dataset}: {len(mismatched)} ATR values differ inside the region the "
        f"protected bars read (first at absolute index {mismatched[0]})"
    )


# ---------------------------------------------------------------------------
# End-to-end confirmation of the proof, on real data, at the selected horizon.
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def m15_full_history_baseline() -> dict[int, truncation.Published]:
    """Full-history outputs over the protected region, built once for this file.

    Both replay tests below compare against the same baseline; recomputing it
    per test doubled this file's runtime without adding any coverage.
    """
    candles = _load("M15")
    total = len(candles)
    return truncation.replay(
        candles,
        start=0,
        configuration=_configuration(),
        swings_fn=diagnostics._confirmed_swings,
        first_protected=total - PUBLISHED_BARS,
    )


def test_truncated_execution_matches_full_history_on_fxcm_m15(
    m15_full_history_baseline: dict[int, truncation.Published],
) -> None:
    """Replay the engine twice and compare all nine outputs, bar by bar.

    M15 is the representative case kept in the normal suite; the same comparison
    across M1, M5, the twenty adversarial fixtures and the randomized streams is
    recorded in the performance document and reproducible from
    ``tests/performance_support``.
    """
    candles = _load("M15")
    configuration = _configuration()
    total = len(candles)
    first_protected = total - PUBLISHED_BARS

    baseline = m15_full_history_baseline
    bounded = truncation.replay(
        candles,
        start=total - CALC_BARS_COUNT,
        configuration=configuration,
        swings_fn=diagnostics._confirmed_swings,
        first_protected=first_protected,
    )

    assert len(baseline) == PUBLISHED_BARS
    divergent = {
        index: baseline[index].differences(bounded[index])
        for index in sorted(baseline)
        if baseline[index].differences(bounded[index])
    }
    assert not divergent, (
        f"bounded execution diverged on {len(divergent)} of {PUBLISHED_BARS} "
        f"publishable bars: {dict(list(divergent.items())[:5])}"
    )


def test_a_too_short_horizon_is_actually_detected(
    m15_full_history_baseline: dict[int, truncation.Published],
) -> None:
    """Guard against a vacuous test.

    If the comparison could not see a truncation defect, every other result here
    would be worthless. A horizon well below the validated floor must fail.
    """
    candles = _load("M15")
    configuration = _configuration()
    total = len(candles)
    first_protected = total - PUBLISHED_BARS

    baseline = m15_full_history_baseline
    # 900 rather than something tiny: the horizon still has to cover the whole
    # published region, or the two runs would not have the same bars to compare
    # and the test would pass on a KeyError-free technicality instead of on
    # detected divergence.
    starved_horizon = 900
    assert starved_horizon >= PUBLISHED_BARS
    starved = truncation.replay(
        candles,
        start=total - starved_horizon,
        configuration=configuration,
        swings_fn=diagnostics._confirmed_swings,
        first_protected=first_protected,
    )
    assert set(starved) == set(baseline), "the two runs must cover the same bars"
    divergent = [
        index
        for index in sorted(baseline)
        if baseline[index].differences(starved[index])
    ]
    assert divergent, (
        f"a {starved_horizon}-bar horizon produced identical output to full "
        "history, which means this comparison cannot detect truncation damage "
        "at all"
    )


def test_adversarial_fixtures_carry_real_structure() -> None:
    """The fixtures must contain swings, or they would prove nothing.

    A stream with no confirmed swings compares na against na on most columns and
    passes for the wrong reason.
    """
    configuration = _configuration()
    from datetime import datetime, timedelta

    epoch = datetime(2026, 1, 1, tzinfo=UTC)
    for name, build in sorted(fixtures.SCENARIOS.items()):
        bars = build(340, 640)
        rows = [
            diagnostics.Row(
                epoch + timedelta(minutes=15 * index),
                bar.open,
                bar.high,
                bar.low,
                bar.close,
            )
            for index, bar in enumerate(bars)
        ]
        candles = diagnostics.build_candles(
            rows, InternalSymbol.XAUUSD, Timeframe.M15, "SYNTH"
        )
        swings = diagnostics._confirmed_swings(candles[-LOOKBACK:], configuration)
        assert swings, f"fixture {name} produced no confirmed swings"
