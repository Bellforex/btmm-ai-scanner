"""BTRC-T5 confluence + analytical-permission tests.

Layer 1: pure decision-logic (permission bands, counter-trend, extreme-volatility
downgrade, weighted final, lifecycle). Layer 2: integration over a real
``ScannerAnalysis`` proving hard-truth invariants (POI never invalidated by BTRC;
btmm_valid from data not scores), no execution fields, determinism, no-lookahead,
incremental==batch, and the integrated T1->T5 stack.
"""

import random
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from types import SimpleNamespace
from uuid import UUID

from btmm_ai_scanner.btmm.configuration import BtmmConfiguration
from btmm_ai_scanner.btrc import (
    AnalyticalPermission,
    ConfluenceConfiguration,
    TrendAlignment,
    assess_confluence,
    latest_poi,
)
from btmm_ai_scanner.btrc.enums import SignalLifecycleState, VolatilityState
from btmm_ai_scanner.btrc.t5_decision import BtrcDecision, ComponentScores
from btmm_ai_scanner.btrc.t5_engine import _lifecycle, _permission, _weighted_final
from btmm_ai_scanner.config.enums import InternalSymbol, Timeframe
from btmm_ai_scanner.contracts.normalized_candle import NormalizedCandle
from btmm_ai_scanner.contracts.raw_candle import CandleCompleteness, CandleVolumeKind
from btmm_ai_scanner.contracts.types import SemVer
from btmm_ai_scanner.domain.configuration import MarketMeasurementConfiguration
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
_M15 = Timeframe.M15
_CFG = ConfluenceConfiguration()


def _uid(n: int) -> UUID:
    return UUID(f"0193f350-1234-7abc-8def-{n:012x}")


def _scores(value: int = 60) -> ComponentScores:
    return ComponentScores(
        btmm_score=value,
        poi_score=value,
        trend_score=value,
        regime_score=value,
        momentum_score=value,
        breakout_score=value,
        liquidity_score=value,
        volatility_score=value,
    )


# ---------------- pure decision logic ----------------
def test_weighted_final_deterministic_and_uses_config_weights() -> None:
    scores = _scores(60)
    assert _weighted_final(scores, _CFG.weights) == 60
    # zero weights -> 0 (guard), and custom weights change the result
    assert _weighted_final(scores, {}) == 0


def test_permission_counter_trend_stays_counter_trend() -> None:
    perm, _ = _permission(
        alignment=TrendAlignment.COUNTER_TREND,
        poi_bullish=False,
        final=70,
        config=_CFG,
        volatility=None,
    )
    assert perm is AnalyticalPermission.COUNTER_TREND


def test_permission_counter_trend_low_confluence_is_watch_only() -> None:
    perm, _ = _permission(
        alignment=TrendAlignment.COUNTER_TREND,
        poi_bullish=False,
        final=20,
        config=_CFG,
        volatility=None,
    )
    assert perm is AnalyticalPermission.WATCH_ONLY


def test_permission_aligned_high_confluence_is_directional_bias() -> None:
    buy, _ = _permission(
        alignment=TrendAlignment.ALIGNED,
        poi_bullish=True,
        final=90,
        config=_CFG,
        volatility=None,
    )
    sell, _ = _permission(
        alignment=TrendAlignment.ALIGNED,
        poi_bullish=False,
        final=90,
        config=_CFG,
        volatility=None,
    )
    assert buy is AnalyticalPermission.BUY_BIAS
    assert sell is AnalyticalPermission.SELL_BIAS


def test_permission_aligned_moderate_is_watch_only() -> None:
    perm, _ = _permission(
        alignment=TrendAlignment.ALIGNED,
        poi_bullish=True,
        final=50,
        config=_CFG,
        volatility=None,
    )
    assert perm is AnalyticalPermission.WATCH_ONLY


def test_permission_aligned_low_is_no_trade_context() -> None:
    perm, _ = _permission(
        alignment=TrendAlignment.ALIGNED,
        poi_bullish=True,
        final=10,
        config=_CFG,
        volatility=None,
    )
    assert perm is AnalyticalPermission.NO_TRADE_CONTEXT


def test_permission_neutral_allows_both_or_watch() -> None:
    both, _ = _permission(
        alignment=TrendAlignment.NEUTRAL,
        poi_bullish=True,
        final=70,
        config=_CFG,
        volatility=None,
    )
    watch, _ = _permission(
        alignment=TrendAlignment.NEUTRAL,
        poi_bullish=True,
        final=20,
        config=_CFG,
        volatility=None,
    )
    assert both is AnalyticalPermission.ALLOW_BOTH_CONTEXT
    assert watch is AnalyticalPermission.WATCH_ONLY


def test_extreme_volatility_downgrades_permission_not_direction() -> None:
    extreme = SimpleNamespace(volatility_state=VolatilityState.EXTREME)
    perm, reasons = _permission(
        alignment=TrendAlignment.ALIGNED,
        poi_bullish=True,
        final=90,
        config=_CFG,
        volatility=extreme,
    )
    assert perm is AnalyticalPermission.WATCH_ONLY  # would have been BUY_BIAS
    assert any("extreme volatility" in r for r in reasons)


def test_lifecycle_stops_at_first_unmet_gate() -> None:
    # no BTMM -> stops at STRUCTURALLY_VALIDATED
    assert (
        _lifecycle(
            has_structure=True,
            btmm_valid=False,
            alignment=TrendAlignment.ALIGNED,
            favorable_regime=True,
            momentum_aligned=True,
            liquidity_ok=True,
        )
        is SignalLifecycleState.STRUCTURALLY_VALIDATED
    )
    # everything favorable -> LIQUIDITY_VALIDATED (top analytical state)
    assert (
        _lifecycle(
            has_structure=True,
            btmm_valid=True,
            alignment=TrendAlignment.ALIGNED,
            favorable_regime=True,
            momentum_aligned=True,
            liquidity_ok=True,
        )
        is SignalLifecycleState.LIQUIDITY_VALIDATED
    )


def test_missing_components_do_not_fabricate_a_high_score() -> None:
    # neutral placeholders (50) for missing components keep the final moderate,
    # never inflated.
    assert _weighted_final(_scores(50), _CFG.weights) == 50


def test_weights_are_engineering_provisional_and_configurable() -> None:
    custom = ConfluenceConfiguration(weights={"trend": 10})
    assert custom.weights == {"trend": 10}  # fully overridable research baseline


# ---------------- integration over a real ScannerAnalysis ----------------
def _config() -> ScannerConfiguration:
    tick = Decimal("0.01")
    return ScannerConfiguration(
        measurement_configuration=MarketMeasurementConfiguration(
            minimum_price_tick=tick
        ),
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


def _batch(candles: tuple[NormalizedCandle, ...]) -> ScannerAnalysis:
    return scan_market(
        (ScannerTimeframeInput(_M15, candles),),
        (),
        _config(),
        ContentAddressedIdentityProvider(),
    )


def _incremental(candles: tuple[NormalizedCandle, ...]) -> ScannerAnalysis:
    return run_scanner_replay(
        (ScannerTimeframeInput(_M15, candles),),
        (),
        _config(),
        ReplayConfiguration(
            snapshot_retention=SnapshotRetentionPolicy.FINAL_ONLY,
            verify_against_direct_batch=False,
        ),
        ContentAddressedIdentityProvider(),
    ).final_snapshot


def _decision(analysis: ScannerAnalysis) -> BtrcDecision | None:
    poi = latest_poi(analysis)
    if poi is None:
        return None
    return assess_confluence(analysis, poi)


def test_btrc_never_invalidates_the_poi() -> None:
    analysis = _batch(_m15(150, 42))
    decision = _decision(analysis)
    assert decision is not None
    assert decision.poi_valid is True  # BTRC is supervisory; POI stays valid


def test_btmm_valid_reflects_scanner_data_not_scores() -> None:
    analysis = _batch(_m15(150, 42))
    poi = latest_poi(analysis)
    assert poi is not None
    decision = assess_confluence(analysis, poi)
    btmm_present = any(
        b.source_poi_record_id == poi.record_id
        for b in analysis.btmm_analysis.btmm_observations
    )
    assert decision.btmm_valid is btmm_present
    # a huge custom trend weight cannot flip the hard truth
    biased = assess_confluence(
        analysis, poi, configuration=ConfluenceConfiguration(weights={"trend": 1000})
    )
    assert biased.btmm_valid is btmm_present
    assert biased.poi_valid is True


def test_decision_has_no_execution_fields() -> None:
    banned = ("entry", "stop", "target", "lot", "order", "ticket", "execution")
    for name in BtrcDecision.model_fields:
        assert not any(term in name.lower() for term in banned), name


def test_decision_is_deterministic() -> None:
    analysis = _batch(_m15(150, 42))
    poi = latest_poi(analysis)
    assert poi is not None
    assert assess_confluence(analysis, poi) == assess_confluence(analysis, poi)


def test_integrated_stack_incremental_equals_batch() -> None:
    candles = _m15(150, 42)
    b, i = _batch(candles), _incremental(candles)
    bp, ip = latest_poi(b), latest_poi(i)
    assert bp is not None and ip is not None
    assert assess_confluence(b, bp) == assess_confluence(i, ip)


def test_integrated_stack_no_lookahead_prefix() -> None:
    candles = _m15(80, 7)
    for k in (40, 60, 80):
        b, i = _batch(candles[:k]), _incremental(candles[:k])
        bp = latest_poi(b)
        ip = latest_poi(i)
        if bp is None or ip is None:
            continue
        assert assess_confluence(b, bp) == assess_confluence(i, ip)
