"""Does `t5_component_scores_pine_model.py` reproduce `assess_confluence`'s
component-score / trend-alignment formulas?

Two kinds of evidence, per the module docstring in
`t5_component_scores_pine_model.py`:

1. Source-text verification -- the exact characteristic lines of each formula
   are asserted present in `t5_engine.py`, so a source edit that changes the
   formula fails this file loudly instead of leaving a stale, silently-wrong
   model behind.
2. A differential against a literal Python transcription of that
   source-verified text, run over many combinations -- plus a few genuine
   end-to-end `assess_confluence` integration checks that exercise the actual,
   unmodified production code (catching a wiring mistake neither
   transcription alone would catch).
"""

from __future__ import annotations

import random
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from itertools import product
from pathlib import Path
from uuid import UUID

from btmm_ai_scanner.btmm.configuration import BtmmConfiguration
from btmm_ai_scanner.btrc import assess_confluence, latest_poi
from btmm_ai_scanner.btrc.enums import (
    Direction,
    MomentumDirection,
    Regime,
    TrendAlignment,
)
from btmm_ai_scanner.config.enums import InternalSymbol, Timeframe
from btmm_ai_scanner.contracts.normalized_candle import NormalizedCandle
from btmm_ai_scanner.contracts.raw_candle import CandleCompleteness, CandleVolumeKind
from btmm_ai_scanner.contracts.types import SemVer
from btmm_ai_scanner.domain.configuration import MarketMeasurementConfiguration
from btmm_ai_scanner.historical_backtest.identity import (
    ContentAddressedIdentityProvider,
)
from btmm_ai_scanner.poi.configuration import PoiConfiguration
from btmm_ai_scanner.poi.enums import PoiStrengthTier
from btmm_ai_scanner.scanner.analyzer import scan_market
from btmm_ai_scanner.scanner.configuration import ScannerConfiguration
from btmm_ai_scanner.scanner.timeframe_input import ScannerTimeframeInput
from btmm_ai_scanner.structure.configuration import StructureConfiguration
from tests.parity_support.t5_component_scores_pine_model import (
    REGIME_SCORE,
    btmm_score,
    liquidity_score,
    momentum_score,
    poi_score,
    regime_score,
    trend_alignment,
    trend_score,
    volatility_score,
)

_REPO = Path(__file__).resolve().parents[2]
_T5 = _REPO / "src" / "btmm_ai_scanner" / "btrc" / "t5_engine.py"
_SOURCE = _T5.read_text(encoding="utf-8")

_BASE = datetime(2026, 1, 1, tzinfo=UTC)
_FP = "a" * 64
_V = SemVer.parse("0.1.0")
_M15 = Timeframe.M15
_BULL_DIRS = (Direction.STRONG_BULLISH, Direction.BULLISH)
_BEAR_DIRS = (Direction.STRONG_BEARISH, Direction.BEARISH)
_ALL_DIRS = (*Direction,)


# ---------------------------------------------------------------------------
# Source-text verification (mirrors test_p5_aggregator_arithmetic.py's method)
# ---------------------------------------------------------------------------


def test_trend_alignment_formula_matches_source_text() -> None:
    assert "poi_side = _BULLISH_SIDE if poi_bullish else _BEARISH_SIDE" in _SOURCE
    assert "opposite_side = _BEARISH_SIDE if poi_bullish else _BULLISH_SIDE" in _SOURCE
    assert "if global_direction in poi_side:" in _SOURCE
    assert "if operational in opposite_side" in _SOURCE
    assert "elif global_direction in opposite_side:" in _SOURCE
    assert "alignment = TrendAlignment.COUNTER_TREND" in _SOURCE
    assert "alignment = TrendAlignment.NEUTRAL" in _SOURCE


def test_trend_score_formula_matches_source_text() -> None:
    assert "TrendAlignment.PARTIAL: 60," in _SOURCE
    assert "TrendAlignment.NEUTRAL: 50," in _SOURCE
    assert "TrendAlignment.COUNTER_TREND: 20," in _SOURCE
    assert "Direction.STRONG_BULLISH," in _SOURCE
    assert "Direction.STRONG_BEARISH," in _SOURCE
    assert "else 80," in _SOURCE


def test_regime_score_table_matches_source_text() -> None:
    assert "Regime.TREND: 90," in _SOURCE
    assert "Regime.EXPANSION: 80," in _SOURCE
    assert "Regime.BREAKOUT_PENDING: 65," in _SOURCE
    assert "Regime.DECELERATION: 50," in _SOURCE
    assert "Regime.COMPRESSION: 45," in _SOURCE
    assert "Regime.TRANSITION: 40," in _SOURCE
    assert "Regime.RANGE: 35," in _SOURCE
    assert "Regime.UNCERTAIN: 30," in _SOURCE


def test_momentum_score_formula_matches_source_text() -> None:
    assert "momentum_score = 50" in _SOURCE
    assert (
        'elif (momentum.direction.value.endswith("BULLISH")) == poi_bullish and ('
        in _SOURCE
    )
    assert '"NEUTRAL" not in momentum.direction.value' in _SOURCE
    assert "momentum_score = min(100, 50 + momentum.momentum_score // 2)" in _SOURCE
    assert 'elif "NEUTRAL" in momentum.direction.value:' in _SOURCE
    assert "momentum_score = max(0, 50 - momentum.momentum_score // 2)" in _SOURCE


def test_breakout_score_formula_matches_source_text() -> None:
    assert "breakout_score = breakout.breakout_score if breakout is not None else 40" in _SOURCE


def test_poi_score_formula_matches_source_text() -> None:
    assert "PoiStrengthTier.STRONG: 85," in _SOURCE
    assert "PoiStrengthTier.STANDARD: 60," in _SOURCE
    assert "}.get(poi.strength_tier, 50)" in _SOURCE
    assert "if poi.strength_tier" in _SOURCE


def test_btmm_score_formula_matches_source_text() -> None:
    assert 'btmm_bullish = btmm.btmm_direction.value.startswith("BULLISH")' in _SOURCE
    assert "btmm_score = 85 if btmm_bullish == poi_bullish else 70" in _SOURCE
    assert "btmm_score = 25" in _SOURCE


def test_liquidity_score_formula_matches_source_text() -> None:
    assert "liquidity_score = 60 if btmm_valid else 40" in _SOURCE


def test_volatility_score_formula_matches_source_text() -> None:
    assert "volatility_score = volatility.suitability_score" in _SOURCE
    assert "volatility_score = 50" in _SOURCE


# ---------------------------------------------------------------------------
# Literal transcription of the source-verified text (the "oracle" for this file)
# ---------------------------------------------------------------------------


def _oracle_alignment(
    global_direction: Direction, operational_context: Direction, poi_bullish: bool
) -> TrendAlignment:
    poi_side = frozenset(_BULL_DIRS) if poi_bullish else frozenset(_BEAR_DIRS)
    opposite_side = frozenset(_BEAR_DIRS) if poi_bullish else frozenset(_BULL_DIRS)
    if global_direction in poi_side:
        operational = operational_context
        return (
            TrendAlignment.PARTIAL
            if operational in opposite_side
            else TrendAlignment.ALIGNED
        )
    if global_direction in opposite_side:
        return TrendAlignment.COUNTER_TREND
    return TrendAlignment.NEUTRAL


def _oracle_trend_score(alignment: TrendAlignment, global_direction: Direction) -> int:
    return {
        TrendAlignment.ALIGNED: 100
        if global_direction in {Direction.STRONG_BULLISH, Direction.STRONG_BEARISH}
        else 80,
        TrendAlignment.PARTIAL: 60,
        TrendAlignment.NEUTRAL: 50,
        TrendAlignment.COUNTER_TREND: 20,
    }[alignment]


def _oracle_momentum_score(
    direction: MomentumDirection | None, mscore: int, poi_bullish: bool
) -> int:
    if direction is None:
        return 50
    if (direction.value.endswith("BULLISH")) == poi_bullish and (
        "NEUTRAL" not in direction.value
    ):
        return min(100, 50 + mscore // 2)
    if "NEUTRAL" in direction.value:
        return 50
    return max(0, 50 - mscore // 2)


def _oracle_poi_score(tier: PoiStrengthTier | None) -> int:
    return (
        {PoiStrengthTier.STRONG: 85, PoiStrengthTier.STANDARD: 60}.get(tier, 50)
        if tier
        else 50
    )


def _oracle_btmm_score(btmm_valid: bool, btmm_bullish: bool, poi_bullish: bool) -> int:
    if btmm_valid:
        return 85 if btmm_bullish == poi_bullish else 70
    return 25


# ---------------------------------------------------------------------------
# Differential: exhaustive over the enum-sized domains
# ---------------------------------------------------------------------------


def test_exhaustive_trend_alignment_and_score() -> None:
    for gd, oc, poi_bullish in product(_ALL_DIRS, _ALL_DIRS, (True, False)):
        oracle_a = _oracle_alignment(gd, oc, poi_bullish)
        wire_a = trend_alignment(gd, oc, poi_bullish)
        assert oracle_a == wire_a, (gd, oc, poi_bullish, oracle_a, wire_a)
        assert _oracle_trend_score(oracle_a, gd) == trend_score(wire_a, gd)


def test_exhaustive_regime_score() -> None:
    for regime in Regime:
        assert REGIME_SCORE[regime] == regime_score(regime)


def test_exhaustive_momentum_score() -> None:
    rng = random.Random(1122)
    directions: tuple[MomentumDirection | None, ...] = (None, *MomentumDirection)
    for direction, poi_bullish in product(directions, (True, False)):
        for mscore in (0, 1, 25, 50, 51, 99, 100):
            oracle = _oracle_momentum_score(direction, mscore, poi_bullish)
            wire = momentum_score(direction, mscore, poi_bullish)
            assert oracle == wire, (direction, mscore, poi_bullish, oracle, wire)
    for _ in range(500):
        direction = rng.choice(directions)
        mscore = rng.randint(0, 100)
        poi_bullish = rng.choice((True, False))
        assert _oracle_momentum_score(direction, mscore, poi_bullish) == momentum_score(
            direction, mscore, poi_bullish
        )


def test_exhaustive_poi_score() -> None:
    for tier in (None, *PoiStrengthTier):
        assert _oracle_poi_score(tier) == poi_score(tier)


def test_exhaustive_btmm_and_liquidity_score() -> None:
    for btmm_valid, btmm_bullish, poi_bullish in product((True, False), repeat=3):
        assert _oracle_btmm_score(btmm_valid, btmm_bullish, poi_bullish) == btmm_score(
            btmm_valid, btmm_bullish, poi_bullish
        )
    assert liquidity_score(True) == 60
    assert liquidity_score(False) == 40


def test_breakout_and_volatility_score_passthrough_or_default() -> None:
    from tests.parity_support.t5_component_scores_pine_model import breakout_score

    assert breakout_score(None) == 40
    for s in (0, 10, 50, 90, 100):
        assert breakout_score(s) == s
    assert volatility_score(None) == 50
    for s in (0, 20, 60, 100):
        assert volatility_score(s) == s


# ---------------------------------------------------------------------------
# Mutations
# ---------------------------------------------------------------------------


def test_mutation_missing_component_default_differs_from_scoring_zero() -> None:
    """Same shape as the aggregator's own Finding 1: a MISSING component uses
    a specific non-zero default (50 for momentum/volatility, 40 for breakout,
    25 for btmm-invalid), never a bare 0 -- guessing 0 anywhere here is wrong."""
    assert momentum_score(None, 0, True) == 50
    assert momentum_score(None, 0, True) != 0
    from tests.parity_support.t5_component_scores_pine_model import breakout_score

    assert breakout_score(None) == 40
    assert breakout_score(None) != 0
    assert volatility_score(None) == 50
    assert volatility_score(None) != 0
    assert btmm_score(False, True, True) == 25
    assert btmm_score(False, True, True) != 0


def test_mutation_partial_vs_aligned_requires_operational_context() -> None:
    """A port that ignored `operational_context` entirely (always ALIGNED when
    global agrees with POI direction) would miss PARTIAL."""
    assert (
        trend_alignment(Direction.BULLISH, Direction.BULLISH, True) == TrendAlignment.ALIGNED
    )
    assert (
        trend_alignment(Direction.BULLISH, Direction.BEARISH, True) == TrendAlignment.PARTIAL
    )


# ---------------------------------------------------------------------------
# End-to-end sanity: the actual, unmodified assess_confluence
# ---------------------------------------------------------------------------


def _uid(n: int) -> UUID:
    return UUID(f"0193f350-1234-7abc-8def-{n:012x}")


def _config() -> ScannerConfiguration:
    tick = Decimal("0.01")
    return ScannerConfiguration(
        measurement_configuration=MarketMeasurementConfiguration(minimum_price_tick=tick),
        structure_configuration=StructureConfiguration(),
        poi_configuration=PoiConfiguration(minimum_price_tick=tick),
        btmm_configuration=BtmmConfiguration(minimum_price_tick=tick),
        required_timeframes=frozenset({_M15}),
        optional_timeframes=frozenset(),
    )


def _m15(n: int, seed: int) -> tuple[NormalizedCandle, ...]:
    rng = random.Random(seed)
    price = 100.0
    out: list[NormalizedCandle] = []
    for i in range(n):
        o = price
        c = o + rng.uniform(-1.5, 1.5)
        h = max(o, c) + rng.uniform(0, 0.8)
        low = min(o, c) - rng.uniform(0, 0.8)
        event = _BASE + timedelta(minutes=15 * i)
        avail = event + timedelta(minutes=15)
        out.append(
            NormalizedCandle.model_validate(
                {
                    "record_id": _uid(500000 + i),
                    "content_fingerprint": _FP,
                    "raw_candle_id": _uid(600000 + i),
                    "provider": "FXCM",
                    "source_reference": "fxcm-xauusd-m15",
                    "source_symbol": "XAUUSD",
                    "source_timeframe": "M15",
                    "symbol": InternalSymbol.XAUUSD,
                    "timeframe": _M15,
                    "event_time_utc": event,
                    "availability_time_utc": avail,
                    "processing_time_utc": avail,
                    "original_event_time": event,
                    "original_availability_time": avail,
                    "original_timezone": "UTC",
                    "open": Decimal(str(o)),
                    "high": Decimal(str(h)),
                    "low": Decimal(str(low)),
                    "close": Decimal(str(c)),
                    "volume": Decimal("10"),
                    "volume_kind": CandleVolumeKind.TICK,
                    "completeness": CandleCompleteness.CONFIRMED_COMPLETE,
                    "rule_version": _V,
                    "contract_version": _V,
                    "schema_version": _V,
                    "provenance_id": _uid(700000 + i),
                }
            )
        )
        price = c
    return tuple(out)


def test_end_to_end_component_scores_match_the_model_on_real_scanner_output() -> None:
    """Only D1/W1/H4 are absent in this single-M15 harness, so global_direction
    is always NEUTRAL and trend_score is always 50 -- that degenerate case is
    exactly what this checks: not richness (the exhaustive tests above already
    cover the full domain), but that the model's WIRING (which field, which
    default) matches the real, unmodified `assess_confluence` end to end,
    reading momentum's raw score and BTMM's raw direction the same way
    `assess_confluence` itself does (they are not exposed on `BtrcDecision`)."""
    from btmm_ai_scanner.btrc.t3_engine import assess_momentum

    checked = 0
    for seed in (1, 2, 3, 4, 5, 6, 7, 8):
        analysis = scan_market(
            (ScannerTimeframeInput(_M15, _m15(180, seed)),),
            (),
            _config(),
            ContentAddressedIdentityProvider(),
        )
        poi = latest_poi(analysis)
        if poi is None:
            continue
        decision = assess_confluence(analysis, poi)
        poi_bullish = poi.direction.value == "BULLISH"

        assert decision.component_scores.trend_score == trend_score(
            TrendAlignment.NEUTRAL, Direction.NEUTRAL
        )
        assert decision.component_scores.regime_score == regime_score(decision.regime)

        momentum = {m.timeframe: m for m in assess_momentum(analysis)}.get(
            poi.effective_timeframe
        )
        raw_momentum_score = momentum.momentum_score if momentum is not None else 0
        assert decision.component_scores.momentum_score == momentum_score(
            decision.momentum_direction, raw_momentum_score, poi_bullish
        )

        btmm = next(
            (
                b
                for b in analysis.btmm_analysis.btmm_observations
                if b.source_poi_record_id == poi.record_id
            ),
            None,
        )
        btmm_bullish = (
            btmm.btmm_direction.value.startswith("BULLISH") if btmm is not None else False
        )
        assert decision.component_scores.btmm_score == btmm_score(
            decision.btmm_valid, btmm_bullish, poi_bullish
        )
        assert decision.component_scores.liquidity_score == liquidity_score(decision.btmm_valid)
        checked += 1
    assert checked > 0
