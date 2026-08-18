"""BTRC-T2 deterministic regime-engine tests.

Layer 1: precise, direct tests of the per-timeframe regime mapping + precedence
using hand-built T1 assessments and displacement records. Layer 2: integration
over a real ``ScannerAnalysis`` for determinism, no-lookahead, and
incremental-vs-batch equivalence. Regime never carries bullish/bearish polarity.
"""

import random
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

from btmm_ai_scanner.btmm.configuration import BtmmConfiguration
from btmm_ai_scanner.btrc import Direction, Regime, TrendState, assess_regime
from btmm_ai_scanner.btrc.regime_configuration import RegimeEngineConfiguration
from btmm_ai_scanner.btrc.regime_engine import _regime_for_timeframe
from btmm_ai_scanner.btrc.trend_assessment import TimeframeTrendAssessment
from btmm_ai_scanner.config.enums import InternalSymbol, Timeframe
from btmm_ai_scanner.contracts.normalized_candle import NormalizedCandle
from btmm_ai_scanner.contracts.provenance_record import EvidenceClassification
from btmm_ai_scanner.contracts.raw_candle import CandleCompleteness, CandleVolumeKind
from btmm_ai_scanner.contracts.types import SemVer
from btmm_ai_scanner.domain.configuration import MarketMeasurementConfiguration
from btmm_ai_scanner.domain.displacement import DisplacementObservation
from btmm_ai_scanner.domain.enums import (
    DisplacementClassification,
    DisplacementDirection,
)
from btmm_ai_scanner.historical_backtest.identity import (
    ContentAddressedIdentityProvider,
)
from btmm_ai_scanner.poi.configuration import PoiConfiguration
from btmm_ai_scanner.scanner.analysis import ScannerAnalysis
from btmm_ai_scanner.scanner.analyzer import scan_market
from btmm_ai_scanner.scanner.configuration import (
    ReplayConfiguration,
    ScannerConfiguration,
)
from btmm_ai_scanner.scanner.enums import SnapshotRetentionPolicy
from btmm_ai_scanner.scanner.replay import run_scanner_replay
from btmm_ai_scanner.scanner.timeframe_input import ScannerTimeframeInput
from btmm_ai_scanner.structure.configuration import StructureConfiguration

_BASE = datetime(2026, 1, 1, tzinfo=UTC)
_FP = "a" * 64
_V = SemVer.parse("0.1.0")
_EC = EvidenceClassification.ENGINEERING_PROVISIONAL
_RCFG = RegimeEngineConfiguration()


def _uid(n: int) -> UUID:
    return UUID(f"0193f350-1234-7abc-8def-{n:012x}")


def _trend(
    trend_state: TrendState,
    *,
    direction: Direction = Direction.NEUTRAL,
    streak: int = 0,
    timeframe: Timeframe = Timeframe.M15,
) -> TimeframeTrendAssessment:
    return TimeframeTrendAssessment(
        timeframe=timeframe,
        direction=direction,
        trend_state=trend_state,
        evaluation_time_utc=_BASE,
        analyzed_swing_count=5,
        continuation_streak=streak,
        supporting_evidence=(),
        opposing_evidence=(),
        structure_reference_ids=(),
    )


def _disp(n: int, ratio: str) -> DisplacementObservation:
    t = _BASE + timedelta(minutes=n)
    return DisplacementObservation(
        record_id=_uid(n),
        content_fingerprint=_FP,
        symbol=InternalSymbol.XAUUSD,
        timeframe=Timeframe.M15,
        candle_record_id=_uid(10000 + n),
        event_time_utc=t,
        availability_time_utc=t,
        total_range=Decimal("2.0"),
        range_speed_ratio=Decimal(ratio),
        direction=DisplacementDirection.BULLISH,
        classification=DisplacementClassification.NORMAL,
        rule_version=_V,
        contract_version=_V,
        schema_version=_V,
        evidence_classification=_EC,
        provenance_id=_uid(20000 + n),
    )


# ----- layer 1: per-timeframe regime mapping -----
def test_unknown_trend_is_uncertain_regime() -> None:
    assert (
        _regime_for_timeframe(_trend(TrendState.UNKNOWN), (), _RCFG).regime
        is Regime.UNCERTAIN
    )


def test_transition_trend_is_transition_regime() -> None:
    assert (
        _regime_for_timeframe(_trend(TrendState.TRANSITION), (), _RCFG).regime
        is Regime.TRANSITION
    )


def test_trending_is_trend_regime() -> None:
    r = _regime_for_timeframe(_trend(TrendState.TRENDING, streak=2), (), _RCFG)
    assert r.regime is Regime.TREND


def test_exhausting_is_deceleration_regime() -> None:
    assert (
        _regime_for_timeframe(_trend(TrendState.EXHAUSTING), (), _RCFG).regime
        is Regime.DECELERATION
    )


def test_range_trend_is_range_regime() -> None:
    assert (
        _regime_for_timeframe(_trend(TrendState.RANGE), (), _RCFG).regime
        is Regime.RANGE
    )


def test_forming_without_displacement_is_compression() -> None:
    assert (
        _regime_for_timeframe(_trend(TrendState.FORMING), (), _RCFG).regime
        is Regime.COMPRESSION
    )


def test_forming_with_building_displacement_is_breakout_pending() -> None:
    r = _regime_for_timeframe(_trend(TrendState.FORMING), (_disp(1, "1.10"),), _RCFG)
    assert r.regime is Regime.BREAKOUT_PENDING


def test_forming_with_fast_displacement_is_expansion() -> None:
    r = _regime_for_timeframe(_trend(TrendState.FORMING), (_disp(1, "1.80"),), _RCFG)
    assert r.regime is Regime.EXPANSION


def test_direction_and_regime_are_independent() -> None:
    # bullish direction + COMPRESSION regime
    bull_compress = _regime_for_timeframe(
        _trend(TrendState.FORMING, direction=Direction.BULLISH), (), _RCFG
    )
    assert bull_compress.regime is Regime.COMPRESSION
    # bearish direction + EXPANSION regime
    bear_expand = _regime_for_timeframe(
        _trend(TrendState.FORMING, direction=Direction.BEARISH),
        (_disp(1, "1.80"),),
        _RCFG,
    )
    assert bear_expand.regime is Regime.EXPANSION
    # regime tokens never carry polarity
    assert not any("BULL" in r.value or "BEAR" in r.value for r in Regime)


def test_regime_precedence_transition_over_forming_evidence() -> None:
    # even with fast recent displacement, a confirmed TRANSITION dominates.
    r = _regime_for_timeframe(_trend(TrendState.TRANSITION), (_disp(1, "3.0"),), _RCFG)
    assert r.regime is Regime.TRANSITION


# ----- layer 2: integration over a real ScannerAnalysis -----
def _config() -> ScannerConfiguration:
    tick = Decimal("0.01")
    return ScannerConfiguration(
        measurement_configuration=MarketMeasurementConfiguration(
            minimum_price_tick=tick
        ),
        structure_configuration=StructureConfiguration(),
        poi_configuration=PoiConfiguration(minimum_price_tick=tick),
        btmm_configuration=BtmmConfiguration(minimum_price_tick=tick),
        required_timeframes=frozenset({Timeframe.M15}),
        optional_timeframes=frozenset(),
    )


def _m15_candles(n: int, seed: int) -> tuple[NormalizedCandle, ...]:
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
                    "timeframe": Timeframe.M15,
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


def _batch(candles: tuple[NormalizedCandle, ...]) -> ScannerAnalysis:
    bundles = (ScannerTimeframeInput(Timeframe.M15, candles),)
    return scan_market(bundles, (), _config(), ContentAddressedIdentityProvider())


def _incremental(candles: tuple[NormalizedCandle, ...]) -> ScannerAnalysis:
    bundles = (ScannerTimeframeInput(Timeframe.M15, candles),)
    return run_scanner_replay(
        bundles,
        (),
        _config(),
        ReplayConfiguration(
            snapshot_retention=SnapshotRetentionPolicy.FINAL_ONLY,
            verify_against_direct_batch=False,
        ),
        ContentAddressedIdentityProvider(),
    ).final_snapshot


def test_assess_regime_is_deterministic() -> None:
    analysis = _batch(_m15_candles(120, 42))
    assert assess_regime(analysis) == assess_regime(analysis)


def test_regime_incremental_and_batch_equivalent() -> None:
    candles = _m15_candles(120, 42)
    assert assess_regime(_incremental(candles)) == assess_regime(_batch(candles))


def test_regime_no_lookahead_prefix_matches_incremental() -> None:
    candles = _m15_candles(60, 7)
    for k in (20, 40, 60):
        prefix = candles[:k]
        assert assess_regime(_batch(prefix)) == assess_regime(_incremental(prefix))


def test_evidence_ordering_deterministic() -> None:
    analysis = _batch(_m15_candles(80, 3))
    a = assess_regime(analysis)
    b = assess_regime(analysis)
    assert [r.supporting_evidence for r in a.timeframe_regimes] == [
        r.supporting_evidence for r in b.timeframe_regimes
    ]
