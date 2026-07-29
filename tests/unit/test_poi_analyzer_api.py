import hashlib
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

import pytest

from btmm_ai_scanner.config.enums import InternalSymbol, Timeframe
from btmm_ai_scanner.contracts.normalized_candle import NormalizedCandle
from btmm_ai_scanner.contracts.provenance_record import EvidenceClassification
from btmm_ai_scanner.contracts.raw_candle import CandleCompleteness, CandleVolumeKind
from btmm_ai_scanner.contracts.types import SemVer
from btmm_ai_scanner.domain import MarketMeasurementAnalysis, MixedSymbolAnalysisError
from btmm_ai_scanner.domain.enums import SupportResistanceType
from btmm_ai_scanner.domain.support_resistance import SupportResistanceZone
from btmm_ai_scanner.poi.analyzer import (
    DuplicatePoiTimeframeInputError,
    InputPrefixMismatchError,
    MissingSourceRecordError,
    PoiTimeframeInput,
    UnsortedPoiTimeframeInputError,
    analyze_pois,
)
from btmm_ai_scanner.poi.configuration import PoiConfiguration
from btmm_ai_scanner.poi.enums import PoiType

_RAW_CANDLE_ID = UUID("0193f450-1234-7abc-8def-abcdefabcdaa")
_PROVENANCE_ID = UUID("0193f450-1234-7abc-8def-abcdefabcdff")
_FINGERPRINT = "a" * 64
_BASE_TIME = datetime(2026, 1, 1, tzinfo=UTC)
_CONFIG = PoiConfiguration(minimum_price_tick=Decimal("0.01"))


class _HashIdentityProvider:
    def identify(self, *, output_type: object, semantic_key: tuple[str, ...]) -> UUID:
        payload = output_type.value + "|" + "|".join(semantic_key)  # type: ignore[attr-defined]
        digest = hashlib.sha256(payload.encode("utf-8")).digest()[:16]
        as_int = int.from_bytes(digest, "big")
        as_int &= ~(0xF << 76)
        as_int |= 7 << 76
        as_int &= ~(0x3 << 62)
        as_int |= 0x2 << 62
        return UUID(int=as_int)


def _record_id(index: int) -> UUID:
    return UUID(f"0193f450-1234-7abc-8def-{index:012x}")


def _candle(
    index: int,
    open_: str,
    high: str,
    low: str,
    close: str,
    symbol: InternalSymbol = InternalSymbol.XAUUSD,
    timeframe: Timeframe = Timeframe.M1,
) -> NormalizedCandle:
    event_time = _BASE_TIME + timedelta(minutes=index)
    availability = event_time + timedelta(minutes=1)
    return NormalizedCandle.model_validate(
        {
            "record_id": _record_id(index),
            "content_fingerprint": _FINGERPRINT,
            "raw_candle_id": _RAW_CANDLE_ID,
            "provider": "FXCM",
            "source_reference": "fxcm-xauusd-m1",
            "source_symbol": symbol.value,
            "source_timeframe": timeframe.value,
            "symbol": symbol,
            "timeframe": timeframe,
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


def _measurement_analysis(
    candle_count: int,
    symbol: InternalSymbol = InternalSymbol.XAUUSD,
    timeframe: Timeframe = Timeframe.M1,
    support_resistance_zones: tuple[SupportResistanceZone, ...] = (),
) -> MarketMeasurementAnalysis:
    return MarketMeasurementAnalysis(
        symbol=symbol,
        timeframe=timeframe,
        analyzed_candle_count=candle_count,
        confirmed_swings=(),
        displacement_observations=(),
        equal_level_clusters=(),
        support_resistance_zones=support_resistance_zones,
        trendlines=(),
    )


def _order_block_pair(
    ratio_ok: bool = True,
) -> tuple[NormalizedCandle, NormalizedCandle]:
    origin = _candle(0, "100", "100", "99", "99")
    if ratio_ok:
        displacement = _candle(1, "99", "101", "99", "101")
    else:
        displacement = _candle(1, "99", "100.4", "99", "100.3")
    return origin, displacement


def test_analyze_pois_returns_empty_aggregate_for_empty_input() -> None:
    result = analyze_pois((), _CONFIG, _HashIdentityProvider())

    assert result.symbol is None
    assert result.analyzed_timeframes == ()
    assert result.poi_observations == ()
    assert result.poi_lifecycle_transitions == ()
    assert result.poi_overlap_relationships == ()
    assert result.current_poi_states == ()


def test_analyze_pois_rejects_mixed_symbol_input() -> None:
    xau = _candle(0, "100", "101", "99", "100", symbol=InternalSymbol.XAUUSD)
    eur = _candle(1, "100", "101", "99", "100", symbol=InternalSymbol.EURUSD)
    bundle = PoiTimeframeInput(
        timeframe=Timeframe.M1,
        candles=(xau, eur),
        measurement_analysis=_measurement_analysis(2),
    )

    with pytest.raises(MixedSymbolAnalysisError):
        analyze_pois((bundle,), _CONFIG, _HashIdentityProvider())


def test_analyze_pois_rejects_duplicate_or_unsorted_timeframe_input() -> None:
    candles = (_candle(0, "100", "101", "99", "100"),)
    m15_candles = (_candle(0, "100", "101", "99", "100", timeframe=Timeframe.M15),)
    m1_bundle = PoiTimeframeInput(
        timeframe=Timeframe.M1,
        candles=candles,
        measurement_analysis=_measurement_analysis(1),
    )
    duplicate_m1_bundle = PoiTimeframeInput(
        timeframe=Timeframe.M1,
        candles=candles,
        measurement_analysis=_measurement_analysis(1),
    )
    m15_bundle = PoiTimeframeInput(
        timeframe=Timeframe.M15,
        candles=m15_candles,
        measurement_analysis=_measurement_analysis(1, timeframe=Timeframe.M15),
    )

    with pytest.raises(DuplicatePoiTimeframeInputError):
        analyze_pois((m1_bundle, duplicate_m1_bundle), _CONFIG, _HashIdentityProvider())

    with pytest.raises(UnsortedPoiTimeframeInputError):
        analyze_pois((m15_bundle, m1_bundle), _CONFIG, _HashIdentityProvider())


def test_analyze_pois_rejects_measurement_candle_count_mismatch() -> None:
    candles = (_candle(0, "100", "101", "99", "100"),)
    bundle = PoiTimeframeInput(
        timeframe=Timeframe.M1,
        candles=candles,
        measurement_analysis=_measurement_analysis(5),
    )

    with pytest.raises(InputPrefixMismatchError):
        analyze_pois((bundle,), _CONFIG, _HashIdentityProvider())


def test_poi_timeframe_input_has_no_structure_analysis_field() -> None:
    assert "structure_analysis" not in PoiTimeframeInput._fields
    assert "candles" in PoiTimeframeInput._fields
    assert "measurement_analysis" in PoiTimeframeInput._fields


def test_analyze_pois_rejects_missing_source_record() -> None:
    candles = (_candle(0, "100", "101", "99", "100"),)
    mismatched_zone = SupportResistanceZone(
        record_id=_record_id(100),
        content_fingerprint="a" * 64,
        symbol=InternalSymbol.EURUSD,
        timeframe=Timeframe.M1,
        zone_type=SupportResistanceType.SUPPORT,
        origin_swing_record_id=_record_id(101),
        creator_reference_atr=Decimal("1.0"),
        zone_depth=Decimal("1"),
        zone_top=Decimal("101"),
        zone_bottom=Decimal("100"),
        qualifying_touch_swing_record_ids=(),
        confirmation_candle_id=_record_id(102),
        confirmation_time_utc=_BASE_TIME,
        availability_time_utc=_BASE_TIME,
        rule_version=SemVer.parse("1.0.0"),
        contract_version=SemVer.parse("0.1.0"),
        schema_version=SemVer.parse("0.1.0"),
        evidence_classification=EvidenceClassification.ENGINEERING_PROVISIONAL,
        provenance_id=_PROVENANCE_ID,
    )
    bundle = PoiTimeframeInput(
        timeframe=Timeframe.M1,
        candles=candles,
        measurement_analysis=_measurement_analysis(
            1, support_resistance_zones=(mismatched_zone,)
        ),
    )

    with pytest.raises(MissingSourceRecordError):
        analyze_pois((bundle,), _CONFIG, _HashIdentityProvider())


def test_unconfirmed_candidate_is_not_exposed_as_poi_observation() -> None:
    origin, weak_displacement = _order_block_pair(ratio_ok=False)
    bundle = PoiTimeframeInput(
        timeframe=Timeframe.M1,
        candles=(origin, weak_displacement),
        measurement_analysis=_measurement_analysis(2),
    )

    result = analyze_pois((bundle,), _CONFIG, _HashIdentityProvider())

    order_block_observations = [
        o for o in result.poi_observations if o.poi_type == PoiType.BUY_ORDER_BLOCK
    ]
    assert order_block_observations == []


def test_public_poi_observation_exists_only_after_confirmation() -> None:
    origin, displacement = _order_block_pair(ratio_ok=True)
    bundle = PoiTimeframeInput(
        timeframe=Timeframe.M1,
        candles=(origin, displacement),
        measurement_analysis=_measurement_analysis(2),
    )

    result = analyze_pois((bundle,), _CONFIG, _HashIdentityProvider())

    order_block_observations = [
        o for o in result.poi_observations if o.poi_type == PoiType.BUY_ORDER_BLOCK
    ]
    assert len(order_block_observations) == 1


def test_poi_outputs_use_engineering_provisional_evidence() -> None:
    origin, displacement = _order_block_pair(ratio_ok=True)
    bundle = PoiTimeframeInput(
        timeframe=Timeframe.M1,
        candles=(origin, displacement),
        measurement_analysis=_measurement_analysis(2),
    )

    result = analyze_pois((bundle,), _CONFIG, _HashIdentityProvider())

    for observation in result.poi_observations:
        assert observation.evidence_classification == (
            EvidenceClassification.ENGINEERING_PROVISIONAL
        )


def test_analyze_pois_disabled_poi_type_is_never_detected() -> None:
    origin, displacement = _order_block_pair(ratio_ok=True)
    bundle = PoiTimeframeInput(
        timeframe=Timeframe.M1,
        candles=(origin, displacement),
        measurement_analysis=_measurement_analysis(2),
    )
    restricted_config = PoiConfiguration(
        minimum_price_tick=Decimal("0.01"),
        enabled_poi_types=frozenset(
            _CONFIG.enabled_poi_types - {PoiType.BUY_ORDER_BLOCK}
        ),
    )

    result = analyze_pois((bundle,), restricted_config, _HashIdentityProvider())

    assert all(o.poi_type != PoiType.BUY_ORDER_BLOCK for o in result.poi_observations)


def test_analyze_pois_is_deterministic_across_repeated_calls() -> None:
    origin, displacement = _order_block_pair(ratio_ok=True)
    bundle = PoiTimeframeInput(
        timeframe=Timeframe.M1,
        candles=(origin, displacement),
        measurement_analysis=_measurement_analysis(2),
    )

    first = analyze_pois((bundle,), _CONFIG, _HashIdentityProvider())
    second = analyze_pois((bundle,), _CONFIG, _HashIdentityProvider())

    assert first == second
