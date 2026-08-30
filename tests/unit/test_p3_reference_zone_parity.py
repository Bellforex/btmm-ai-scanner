"""P3-I5 — parity for the reference-zone projection.

THIS FILE ASSERTS THE AUTHORITATIVE PRODUCTION CONTRACT.

Reference zones are not detected from candles: production projects existing P1
records 1:1 (`reference_zones.py:26`). So the test drives the real P1 engine to
produce support/resistance zones, feeds those same zones to production's
projection and to the Pine transcription, and requires the two to agree on
type, direction, bounds and all three timestamps.

Two contracts get pinned here because they are easy to lose in a port:

* every reference POI timestamp collapses to the zone's confirmation time,
  since the P1 finalizer sets a zone's availability to its confirmation time
  (`domain/analyzer.py:377`);
* EQH/EQL clusters are the other half of production's projection but are
  lifecycle-ineligible, so P3 CORE deliberately does not emit them (AD-6).
"""

from __future__ import annotations

import importlib.util
import sys
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from types import ModuleType
from typing import Any
from uuid import UUID

from btmm_ai_scanner.config.enums import InternalSymbol, Timeframe
from btmm_ai_scanner.contracts.normalized_candle import NormalizedCandle
from btmm_ai_scanner.contracts.raw_candle import CandleCompleteness, CandleVolumeKind
from btmm_ai_scanner.contracts.types import SemVer
from btmm_ai_scanner.domain.analyzer import analyze_market_measurements
from btmm_ai_scanner.domain.configuration import MarketMeasurementConfiguration
from btmm_ai_scanner.domain.enums import SupportResistanceType
from btmm_ai_scanner.historical_backtest.identity import (
    ContentAddressedIdentityProvider,
)
from btmm_ai_scanner.poi.enums import PoiDirection, PoiType
from btmm_ai_scanner.poi.reference_zones import detect_reference_zones

REPO = Path(__file__).resolve().parents[2]
P3_DEV = REPO / "tradingview" / "btmm_poi_btrc_scanner_p3_dev.pine"


def _load(name: str, relpath: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, REPO / relpath)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


M = _load("_p3_refzone_model", "tests/parity_support/p3_pine_model.py")

_TICK = Decimal("0.01")
_BASE_TIME = datetime(2026, 1, 1, tzinfo=UTC)
_RAW_CANDLE_ID = UUID("0193f490-1234-7abc-8def-abcdefabcdaa")
_PROVENANCE_ID = UUID("0193f490-1234-7abc-8def-abcdefabcdff")
_FINGERPRINT = "d" * 64


def _candle(
    index: int, open_: str, high: str, low: str, close: str
) -> NormalizedCandle:
    event_time = _BASE_TIME + timedelta(minutes=index)
    availability = event_time + timedelta(minutes=1)
    return NormalizedCandle.model_validate(
        {
            "record_id": UUID(f"0193f490-1234-7abc-8def-{index:012x}"),
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


def _oscillating_stream(length: int = 160) -> tuple[NormalizedCandle, ...]:
    """A repeatedly-tested band, which is what makes the P1 engine emit zones."""
    candles = []
    for index in range(length):
        phase = index % 20
        if phase < 10:
            base = Decimal("100") + Decimal(phase) * Decimal("0.4")
        else:
            base = Decimal("100") + Decimal(20 - phase) * Decimal("0.4")
        open_ = base
        close = base + Decimal("0.1")
        candles.append(
            _candle(
                index,
                str(open_),
                str(close + Decimal("0.25")),
                str(open_ - Decimal("0.25")),
                str(close),
            )
        )
    return tuple(candles)


def _p1_zones(candles: tuple[NormalizedCandle, ...]) -> tuple[Any, ...]:
    analysis = analyze_market_measurements(
        candles,
        MarketMeasurementConfiguration(minimum_price_tick=_TICK),
        ContentAddressedIdentityProvider(),
    )
    return analysis.support_resistance_zones


def _ms(moment: datetime) -> int:
    return int(moment.timestamp() * 1000)


def _production_projection(zones: tuple[Any, ...]) -> set[tuple[Any, ...]]:
    projected: set[tuple[Any, ...]] = set()
    for candidate in detect_reference_zones(zones, ()):
        projected.add(
            (
                M.TYPE_SUPPORT_ZONE
                if candidate.poi_type == PoiType.SUPPORT_ZONE
                else M.TYPE_RESISTANCE_ZONE,
                M.DIR_BULLISH
                if candidate.direction == PoiDirection.BULLISH
                else M.DIR_BEARISH,
                candidate.zone_top,
                candidate.zone_bottom,
                _ms(candidate.candidate_event_time_utc),
                _ms(candidate.confirmation_time_utc),
                _ms(candidate.availability_time_utc),
            )
        )
    return projected


def _model_projection(zones: tuple[Any, ...]) -> set[tuple[Any, ...]]:
    projected: set[tuple[Any, ...]] = set()
    for poi in M.project_reference_zones(zones):
        projected.add(
            (
                poi.poi_type,
                poi.direction,
                poi.zone_top,
                poi.zone_bottom,
                poi.candidate_time,
                poi.confirm_time,
                poi.confirm_time,
            )
        )
    return projected


def test_reference_zone_projection_matches_production() -> None:
    zones = _p1_zones(_oscillating_stream())
    assert len(zones) > 0, "fixture must actually produce P1 zones"
    assert _model_projection(zones) == _production_projection(zones)


def test_projection_covers_both_support_and_resistance() -> None:
    zones = _p1_zones(_oscillating_stream())
    kinds = {z.zone_type for z in zones}
    assert SupportResistanceType.SUPPORT in kinds or (
        SupportResistanceType.RESISTANCE in kinds
    )
    types = {t[0] for t in _model_projection(zones)}
    assert types.issubset({M.TYPE_SUPPORT_ZONE, M.TYPE_RESISTANCE_ZONE})
    for zone in zones:
        expected = (
            M.TYPE_SUPPORT_ZONE
            if zone.zone_type == SupportResistanceType.SUPPORT
            else M.TYPE_RESISTANCE_ZONE
        )
        assert expected in types


def test_all_three_timestamps_collapse_to_the_confirmation_time() -> None:
    """P1 sets a zone's availability to its confirmation time."""
    zones = _p1_zones(_oscillating_stream())
    assert len(zones) > 0
    for zone in zones:
        assert zone.availability_time_utc == zone.confirmation_time_utc
    for projected in _model_projection(zones):
        assert projected[4] == projected[5] == projected[6]


def test_reference_zones_carry_no_strength_tier() -> None:
    zones = _p1_zones(_oscillating_stream())
    for poi in M.project_reference_zones(zones):
        assert poi.tier == M.TIER_NA


def test_equal_level_clusters_are_not_emitted_by_p3_core() -> None:
    """AD-6: EQH/EQL are lifecycle-ineligible P3 CONTEXT."""
    code = "\n".join(
        line
        for line in P3_DEV.read_text(encoding="utf-8").splitlines()
        if not line.strip().startswith("//")
    )
    assert (
        "C_POI_EQUAL_HIGHS_LIQUIDITY" not in code.split("f_poiDetectReferenceZones")[-1]
    )
    assert (
        "C_POI_EQUAL_LOWS_LIQUIDITY" not in code.split("f_poiDetectReferenceZones")[-1]
    )


# ---------------------------------------------------------------------------
# Pine source guards
# ---------------------------------------------------------------------------


def _pine_code() -> str:
    return "\n".join(
        line
        for line in P3_DEV.read_text(encoding="utf-8").splitlines()
        if not line.strip().startswith("//")
    )


def test_pine_projects_the_existing_p1_zones_without_recomputing() -> None:
    code = _pine_code()
    assert "f_poiDetectReferenceZones() =>" in code
    assert "array.size(srCached)" in code
    # the S/R engine itself must not be re-entered by P3
    detector = code.split("f_poiDetectReferenceZones")[1]
    assert "f_walkSR" not in detector
    assert "f_srTrackerIndex" not in detector


def test_pine_reference_zone_direction_mapping_follows_the_origin_swing() -> None:
    code = _pine_code()
    assert "bool isSupport = z.zoneType == SWING_LOW" in code
    assert "isSupport ? C_POI_SUPPORT_ZONE : C_POI_RESISTANCE_ZONE" in code
    assert "isSupport ? C_POI_DIR_BULLISH : C_POI_DIR_BEARISH" in code


def test_registry_identity_includes_zone_bounds() -> None:
    """Reference zones have no source candles, so bounds complete the identity."""
    code = _pine_code()
    assert "f_poiTicks(array.get(poiZoneBottom, i)) == lowTicks" in code
    assert "f_poiTicks(array.get(poiZoneTop, i)) == highTicks" in code
    assert (
        "f_poiFind(typeCode, srcFirstT, srcCount, srcLastT, "
        "f_poiTicks(zoneBottom), f_poiTicks(zoneTop))" in code
    )
