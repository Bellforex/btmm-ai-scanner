"""P1 and P2 on the six timeframes BTRC's authority hierarchy requires.

P1 and P2 were closed against real-data parity on M15 alone, and P3 was later
extended to M5. BTRC needs `(W1, D1, H4, H1, M15, M5)`, so four of those
timeframes have never been verified at any layer. This module establishes the
Python-oracle half of that extension, which is the half that can be settled
without TradingView.

WHAT IS ACTUALLY BEING CLAIMED
------------------------------
Reading the source first: `analyze_market_measurements` and
`analyze_structure_state` both take `(candles, configuration,
identity_provider)` and derive the timeframe FROM the candles. Grepping the
whole of `measurements/`, `domain/` and `structure/` for `Timeframe.` returns
only error strings asserting single-timeframe input -- there is no branch
anywhere on WHICH timeframe. So the expectation is that both layers are pure
functions of the bar sequence, and that the timeframe is carried as metadata.

That expectation is worth very little as an observation and quite a lot as a
proof, because if it holds then P1/P2 correctness established on M15 transfers
to W1/D1/H4/H1/M5 as a property of the algorithm rather than as six separate
empirical claims. These tests prove it on REAL bars: the frozen 1799-bar M15
atomic context from the P3 closure capture, re-timed onto each timeframe's
natural spacing with the prices left untouched.

Re-timing rather than relabelling is deliberate. Stamping M15 bars as W1 while
leaving fifteen-minute timestamps would be an inconsistent input, and the
validator would not catch it -- it checks identity and uniqueness, not spacing.
Each variant here is a well-formed bar series for its timeframe.

WHAT THIS DOES NOT CLAIM
------------------------
It does not claim that real W1 or D1 gold behaves like re-timed M15 gold. It
claims that the ENGINE does not care which timeframe it is given, so feeding it
genuine W1 bars is a data problem, not a correctness problem. The remaining
half -- whether TradingView can deliver 1250 W1 bars to the Pine port, and
whether the Pine engine can run in another timeframe's context at all -- is the
Phase 22 feasibility question and is not addressed here.

The 1250-bar warm-up contract is preserved unchanged; nothing here alters P1 or
P2 semantics.
"""

from __future__ import annotations

import csv
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any
from uuid import UUID

import pytest

from btmm_ai_scanner.config.enums import InternalSymbol, Timeframe
from btmm_ai_scanner.contracts.normalized_candle import NormalizedCandle
from btmm_ai_scanner.contracts.raw_candle import CandleCompleteness, CandleVolumeKind
from btmm_ai_scanner.contracts.types import SemVer
from btmm_ai_scanner.domain.analyzer import analyze_market_measurements
from btmm_ai_scanner.domain.configuration import MarketMeasurementConfiguration
from btmm_ai_scanner.domain.enums import DerivedOutputType
from btmm_ai_scanner.structure.analyzer import analyze_structure_state
from btmm_ai_scanner.structure.configuration import StructureConfiguration

REPO = Path(__file__).resolve().parents[2]
CONTEXT = (
    REPO
    / "artifacts"
    / "p3_parity"
    / "P3_M15_FINAL_ATOMIC_CONTEXT_1799_1788214500000.csv"
)

#: The BTRC authority hierarchy, with each timeframe's bar length.
AUTHORITY_MINUTES: dict[Timeframe, int] = {
    Timeframe.W1: 7 * 24 * 60,
    Timeframe.D1: 24 * 60,
    Timeframe.H4: 4 * 60,
    Timeframe.H1: 60,
    Timeframe.M15: 15,
    Timeframe.M5: 5,
}
AUTHORITY_TIMEFRAMES = tuple(AUTHORITY_MINUTES)

_T0 = datetime(2000, 1, 3, tzinfo=UTC)  # a Monday, so W1 bars start cleanly
_FP = "b" * 64
_PROV = UUID("0193f450-6666-7abc-8def-abcdefabcd66")
_RAW = UUID("0193f450-6666-7abc-8def-abcdefabcd67")


class _ContentIdentity:
    """Content-addressed ids, so a comparison cannot be disturbed by call order."""

    def identify(
        self, *, output_type: DerivedOutputType, semantic_key: tuple[str, ...]
    ) -> UUID:
        import hashlib

        raw = f"{output_type}|{'|'.join(str(p) for p in semantic_key)}"
        d = hashlib.sha256(raw.encode()).hexdigest()
        return UUID(f"{d[:8]}-{d[8:12]}-7{d[13:16]}-8{d[17:20]}-{d[20:32]}")


def _prices() -> list[tuple[Decimal, Decimal, Decimal, Decimal]]:
    """The real OHLC sequence from the frozen P3 closure context."""
    if not CONTEXT.exists():  # pragma: no cover - artifacts are gitignored
        pytest.skip(f"frozen context not present: {CONTEXT.name}")
    rows: list[tuple[Decimal, Decimal, Decimal, Decimal]] = []
    with CONTEXT.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            rows.append(
                (
                    Decimal(row["open"]),
                    Decimal(row["high"]),
                    Decimal(row["low"]),
                    Decimal(row["close"]),
                )
            )
    return rows


def _series(
    timeframe: Timeframe, count: int | None = None
) -> tuple[NormalizedCandle, ...]:
    """The same real prices, re-timed onto `timeframe`'s natural spacing."""
    step = timedelta(minutes=AUTHORITY_MINUTES[timeframe])
    rows = _prices()
    if count is not None:
        rows = rows[:count]
    out: list[NormalizedCandle] = []
    for index, (open_, high, low, close) in enumerate(rows):
        event = _T0 + step * index
        out.append(
            NormalizedCandle.model_validate(
                {
                    "record_id": UUID(f"0193{index:04x}-0000-7abc-8def-000000000001"),
                    "content_fingerprint": _FP,
                    "raw_candle_id": _RAW,
                    "provider": "FXCM",
                    "source_reference": "fxcm",
                    "source_symbol": "XAUUSD",
                    "source_timeframe": timeframe.value,
                    "symbol": InternalSymbol.XAUUSD,
                    "timeframe": timeframe,
                    "event_time_utc": event,
                    "availability_time_utc": event + step,
                    "processing_time_utc": event + step,
                    "original_event_time": event,
                    "original_availability_time": event + step,
                    "original_timezone": "UTC",
                    "open": open_,
                    "high": high,
                    "low": low,
                    "close": close,
                    "volume": None,
                    "volume_kind": CandleVolumeKind.UNKNOWN,
                    "completeness": CandleCompleteness.CONFIRMED_COMPLETE,
                    "rule_version": SemVer.parse("0.1.0"),
                    "contract_version": SemVer.parse("0.1.0"),
                    "schema_version": SemVer.parse("0.1.0"),
                    "provenance_id": _PROV,
                }
            )
        )
    return tuple(out)


def _run(timeframe: Timeframe, count: int | None = None) -> tuple[Any, Any]:
    candles = _series(timeframe, count)
    measurement = analyze_market_measurements(
        candles,
        MarketMeasurementConfiguration(minimum_price_tick=Decimal("0.01")),
        _ContentIdentity(),
    )
    structure = analyze_structure_state(
        candles,
        measurement.confirmed_swings,
        StructureConfiguration(),
        _ContentIdentity(),
    )
    return measurement, structure


# --------------------------------------------------------------------------
# Timeframe-independent projections
# --------------------------------------------------------------------------
#
# Absolute times MUST differ between variants -- that is the whole point of
# re-timing -- so they are excluded. Everything that is a function of the price
# sequence is compared, including the ordering.


def _swing_shape(measurement: Any) -> list[tuple[str, str]]:
    return [
        (s.swing_type.value, str(s.pivot_price)) for s in measurement.confirmed_swings
    ]


def _displacement_shape(measurement: Any) -> list[tuple[str, str]]:
    return [
        (d.direction.value, d.classification.value, str(d.range_speed_ratio))
        for d in measurement.displacement_observations
    ]


def _equal_level_shape(measurement: Any) -> list[tuple[str, str, int]]:
    return [
        (
            c.cluster_type.value,
            str(c.representative_price),
            len(c.component_swing_record_ids),
        )
        for c in measurement.equal_level_clusters
    ]


def _zone_shape(measurement: Any) -> list[tuple[str, str, str]]:
    return [
        (z.zone_type.value, str(z.zone_top), str(z.zone_bottom))
        for z in measurement.support_resistance_zones
    ]


def _transition_shape(structure: Any) -> list[str]:
    return [t.transition_type.value for t in structure.structure_transitions]


def _state_shape(structure: Any) -> tuple[Any, ...]:
    state = structure.current_state
    if state is None:
        return ("NONE",)
    return (state.direction.value, state.analyzed_swing_count)


# --------------------------------------------------------------------------
# The proof
# --------------------------------------------------------------------------

#: 400 bars keeps six full P1+P2 runs inside a sane test budget while staying
#: well above the 21-bar maximum dependency window, so every detector family and
#: the structure walk are genuinely exercised.
_BARS = 400


@pytest.fixture(scope="module")
def by_timeframe() -> dict[Timeframe, tuple[Any, Any]]:
    return {tf: _run(tf, _BARS) for tf in AUTHORITY_TIMEFRAMES}


@pytest.mark.parametrize("timeframe", AUTHORITY_TIMEFRAMES)
def test_every_authority_timeframe_runs_without_error(
    timeframe: Timeframe, by_timeframe: dict[Timeframe, tuple[Any, Any]]
) -> None:
    """The four never-verified timeframes (W1, D1, H4, H1) included."""
    measurement, structure = by_timeframe[timeframe]
    assert measurement.timeframe is timeframe
    assert structure.timeframe is timeframe
    assert measurement.analyzed_candle_count == _BARS
    assert structure.analyzed_candle_count == _BARS


@pytest.mark.parametrize(
    "projection",
    [
        _swing_shape,
        _displacement_shape,
        _equal_level_shape,
        _zone_shape,
    ],
    ids=["swings", "displacement", "equal_levels", "sr_zones"],
)
def test_p1_output_is_identical_across_all_six_timeframes(
    projection: Any, by_timeframe: dict[Timeframe, tuple[Any, Any]]
) -> None:
    """P1 is a function of the bar sequence, not of the timeframe label."""
    baseline = projection(by_timeframe[Timeframe.M15][0])
    for timeframe in AUTHORITY_TIMEFRAMES:
        assert projection(by_timeframe[timeframe][0]) == baseline, timeframe


@pytest.mark.parametrize(
    "projection", [_transition_shape, _state_shape], ids=["transitions", "state"]
)
def test_p2_output_is_identical_across_all_six_timeframes(
    projection: Any, by_timeframe: dict[Timeframe, tuple[Any, Any]]
) -> None:
    """P2 likewise -- including the transition ORDER, not just the set."""
    baseline = projection(by_timeframe[Timeframe.M15][1])
    for timeframe in AUTHORITY_TIMEFRAMES:
        assert projection(by_timeframe[timeframe][1]) == baseline, timeframe


def test_the_comparison_is_not_vacuous(
    by_timeframe: dict[Timeframe, tuple[Any, Any]],
) -> None:
    """Guard the guard. Six empty analyses would agree perfectly and prove
    nothing, so require that this window genuinely exercises both layers."""
    measurement, structure = by_timeframe[Timeframe.M15]
    assert len(measurement.confirmed_swings) > 5
    assert len(structure.structure_transitions) > 0
    assert structure.current_state is not None
    # and the higher timeframes must be producing the same real content
    for timeframe in (Timeframe.W1, Timeframe.D1, Timeframe.H4, Timeframe.H1):
        other, other_structure = by_timeframe[timeframe]
        assert len(other.confirmed_swings) == len(measurement.confirmed_swings)
        assert len(other_structure.structure_transitions) == len(
            structure.structure_transitions
        )


def test_timestamps_do_differ_between_timeframes(
    by_timeframe: dict[Timeframe, tuple[Any, Any]],
) -> None:
    """The variants must really be different inputs. If the re-timing silently
    collapsed, the agreement above would be trivial."""
    times = {
        tf: by_timeframe[tf][0].confirmed_swings[0].meaningful_confirmation_time_utc
        for tf in AUTHORITY_TIMEFRAMES
    }
    assert len(set(times.values())) == len(AUTHORITY_TIMEFRAMES)


def test_source_contains_no_timeframe_branching_in_p1_or_p2() -> None:
    """The structural reason the agreement above holds, asserted directly so a
    future `if timeframe is Timeframe.W1:` cannot slip in unnoticed."""
    import re

    roots = [
        REPO / "src" / "btmm_ai_scanner" / "measurements",
        REPO / "src" / "btmm_ai_scanner" / "domain",
        REPO / "src" / "btmm_ai_scanner" / "structure",
    ]
    offenders: list[str] = []
    for root in roots:
        for path in sorted(root.rglob("*.py")):
            for number, line in enumerate(
                path.read_text(encoding="utf-8").splitlines(), 1
            ):
                if re.search(
                    r"\bTimeframe\.[A-Z]", line
                ) and not line.lstrip().startswith(('"', "#", "'")):
                    offenders.append(f"{path.name}:{number}: {line.strip()}")
    assert offenders == [], (
        "P1/P2 gained a timeframe-specific branch; the higher-timeframe "
        "extension proof above no longer holds:\n" + "\n".join(offenders)
    )


def test_the_warm_up_contract_is_unchanged() -> None:
    """The 1250-bar contract is preserved verbatim, as authorized. This pins the
    Pine constants so the higher-timeframe work cannot quietly relax them to make
    W1 look affordable."""
    pine = (REPO / "tradingview" / "btmm_poi_btrc_scanner_p4_dev.pine").read_text(
        encoding="utf-8"
    )
    assert "int C_P1_CALC_BARS     = 1800" in pine
    assert "C_P1_MIN_CALC_BARS = lookbackWindow + warm-up = 300 + 950 = 1250" in pine
