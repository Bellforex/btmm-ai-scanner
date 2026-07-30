from decimal import Decimal

import btmm_ai_scanner.btmm as btmm_package
from btmm_ai_scanner.btmm.analyzer import _DIRECTION_MAP
from btmm_ai_scanner.btmm.enums import BtmmDirection
from btmm_ai_scanner.poi.enums import PoiDirection, PoiType


def test_pressure_wick_sourced_setup_inherits_context_without_bypassing_gates() -> None:
    config = btmm_package.BtmmConfiguration(minimum_price_tick=Decimal("0.01"))
    assert PoiType.BULLISH_PRESSURE_WICK in config.eligible_poi_types
    assert PoiType.BEARISH_PRESSURE_WICK in config.eligible_poi_types
    assert "pressure_strength_tier" not in btmm_package.BtmmObservation.model_fields
    assert "interaction_class" in btmm_package.CurrentBtmmState.model_fields


def test_buy_to_sell_candle_produces_bearish_btmm() -> None:
    assert _DIRECTION_MAP[PoiDirection.BEARISH] == BtmmDirection.BEARISH_BTMM


def test_sell_to_buy_candle_produces_bullish_btmm() -> None:
    assert _DIRECTION_MAP[PoiDirection.BULLISH] == BtmmDirection.BULLISH_BTMM


def test_no_separate_btmm_pattern_type_enum_exists() -> None:
    assert not hasattr(btmm_package, "BtmmPatternType")
    assert set(BtmmDirection) == {
        BtmmDirection.BULLISH_BTMM,
        BtmmDirection.BEARISH_BTMM,
    }


def test_direction_derived_purely_from_source_poi_direction_for_other_types() -> None:
    assert len(_DIRECTION_MAP) == 2
    for poi_direction, btmm_direction in _DIRECTION_MAP.items():
        assert isinstance(poi_direction, PoiDirection)
        assert isinstance(btmm_direction, BtmmDirection)
