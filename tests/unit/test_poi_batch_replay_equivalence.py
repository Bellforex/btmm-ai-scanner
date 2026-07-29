import hashlib
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

from btmm_ai_scanner.config.enums import InternalSymbol, Timeframe
from btmm_ai_scanner.contracts.normalized_candle import NormalizedCandle
from btmm_ai_scanner.contracts.raw_candle import CandleCompleteness, CandleVolumeKind
from btmm_ai_scanner.contracts.types import SemVer
from btmm_ai_scanner.domain import MarketMeasurementAnalysis
from btmm_ai_scanner.domain.analyzer import _canonicalize as domain_canonicalize
from btmm_ai_scanner.domain.analyzer import (
    _compute_content_fingerprint as domain_fingerprint,
)
from btmm_ai_scanner.poi.analyzer import PoiTimeframeInput, analyze_pois
from btmm_ai_scanner.poi.analyzer import _canonicalize as poi_canonicalize
from btmm_ai_scanner.poi.analyzer import _compute_content_fingerprint as poi_fingerprint
from btmm_ai_scanner.poi.configuration import PoiConfiguration
from btmm_ai_scanner.poi.enums import PoiType
from btmm_ai_scanner.structure.analyzer import _canonicalize as structure_canonicalize
from btmm_ai_scanner.structure.analyzer import (
    _compute_content_fingerprint as structure_fingerprint,
)

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
            "source_symbol": InternalSymbol.XAUUSD.value,
            "source_timeframe": timeframe.value,
            "symbol": InternalSymbol.XAUUSD,
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
    candle_count: int, timeframe: Timeframe = Timeframe.M1
) -> MarketMeasurementAnalysis:
    return MarketMeasurementAnalysis(
        symbol=InternalSymbol.XAUUSD,
        timeframe=timeframe,
        analyzed_candle_count=candle_count,
        confirmed_swings=(),
        displacement_observations=(),
        equal_level_clusters=(),
        support_resistance_zones=(),
        trendlines=(),
    )


def test_batch_and_replay_produce_identical_poi_observations_for_the_same_prefix() -> (
    None
):
    provider = _HashIdentityProvider()
    origin = _candle(0, "100", "100", "99", "99")
    displacement = _candle(1, "99", "101", "99", "101")
    candles = (origin, displacement)
    bundle = PoiTimeframeInput(
        timeframe=Timeframe.M1,
        candles=candles,
        measurement_analysis=_measurement_analysis(2),
    )

    direct_call = analyze_pois((bundle,), _CONFIG, provider)
    replayed_call = analyze_pois((bundle,), _CONFIG, provider)

    assert direct_call.poi_observations == replayed_call.poi_observations


def test_batch_and_replay_produce_identical_lifecycle_transitions_for_the_same_prefix() -> (
    None
):
    provider = _HashIdentityProvider()
    candles = (
        _candle(0, "100", "100", "99", "99"),
        _candle(1, "99", "101", "99", "101"),
        _candle(2, "101", "101.2", "99.85", "99.9"),
        _candle(3, "99.9", "102", "99.8", "101.9"),
    )
    bundle = PoiTimeframeInput(
        timeframe=Timeframe.M1,
        candles=candles,
        measurement_analysis=_measurement_analysis(len(candles)),
    )

    first = analyze_pois((bundle,), _CONFIG, provider)
    second = analyze_pois((bundle,), _CONFIG, provider)

    assert first.poi_lifecycle_transitions == second.poi_lifecycle_transitions


def test_unchanged_poi_observations_retain_the_same_record_id_across_growing_prefixes() -> (
    None
):
    provider = _HashIdentityProvider()
    origin = _candle(0, "100", "100", "99", "99")
    displacement = _candle(1, "99", "101", "99", "101")
    extra = _candle(2, "101", "101.5", "100.8", "101.2")

    short_bundle = PoiTimeframeInput(
        timeframe=Timeframe.M1,
        candles=(origin, displacement),
        measurement_analysis=_measurement_analysis(2),
    )
    grown_bundle = PoiTimeframeInput(
        timeframe=Timeframe.M1,
        candles=(origin, displacement, extra),
        measurement_analysis=_measurement_analysis(3),
    )

    short_result = analyze_pois((short_bundle,), _CONFIG, provider)
    grown_result = analyze_pois((grown_bundle,), _CONFIG, provider)

    short_ob = next(
        o
        for o in short_result.poi_observations
        if o.poi_type == PoiType.BUY_ORDER_BLOCK
    )
    grown_ob = next(
        o
        for o in grown_result.poi_observations
        if o.poi_type == PoiType.BUY_ORDER_BLOCK
    )

    assert short_ob.record_id == grown_ob.record_id
    assert short_ob.content_fingerprint == grown_ob.content_fingerprint


def test_current_poi_state_fingerprint_changes_only_when_public_content_changes() -> (
    None
):
    provider = _HashIdentityProvider()
    origin = _candle(0, "100", "100", "99", "99")
    displacement = _candle(1, "99", "101", "99", "101")
    untouched_tail = _candle(2, "102", "102.5", "101.8", "102")
    touching_tail = _candle(2, "99.6", "99.8", "99.3", "99.6")

    bundle_untouched = PoiTimeframeInput(
        timeframe=Timeframe.M1,
        candles=(origin, displacement, untouched_tail),
        measurement_analysis=_measurement_analysis(3),
    )
    bundle_touched = PoiTimeframeInput(
        timeframe=Timeframe.M1,
        candles=(origin, displacement, touching_tail),
        measurement_analysis=_measurement_analysis(3),
    )

    result_untouched = analyze_pois((bundle_untouched,), _CONFIG, provider)
    result_touched = analyze_pois((bundle_touched,), _CONFIG, provider)

    state_untouched = next(
        s
        for s in result_untouched.current_poi_states
        if s.poi_type == PoiType.BUY_ORDER_BLOCK
    )
    state_touched = next(
        s
        for s in result_touched.current_poi_states
        if s.poi_type == PoiType.BUY_ORDER_BLOCK
    )

    assert state_untouched.record_id == state_touched.record_id
    assert state_untouched.content_fingerprint != state_touched.content_fingerprint


def test_merge_decisions_are_stable_across_growing_prefixes() -> None:
    provider = _HashIdentityProvider()
    m1_origin = _candle(0, "100", "100", "99", "99", timeframe=Timeframe.M1)
    m1_displacement = _candle(1, "99", "101", "99", "101", timeframe=Timeframe.M1)
    h4_origin = _candle(0, "100", "100", "99", "99", timeframe=Timeframe.H4)
    h4_displacement = _candle(1, "99", "102", "99", "102", timeframe=Timeframe.H4)
    m1_extra = _candle(2, "101", "101.5", "100.8", "101.2", timeframe=Timeframe.M1)

    m1_bundle_short = PoiTimeframeInput(
        timeframe=Timeframe.M1,
        candles=(m1_origin, m1_displacement),
        measurement_analysis=_measurement_analysis(2),
    )
    m1_bundle_grown = PoiTimeframeInput(
        timeframe=Timeframe.M1,
        candles=(m1_origin, m1_displacement, m1_extra),
        measurement_analysis=_measurement_analysis(3),
    )
    h4_bundle = PoiTimeframeInput(
        timeframe=Timeframe.H4,
        candles=(h4_origin, h4_displacement),
        measurement_analysis=_measurement_analysis(2, timeframe=Timeframe.H4),
    )

    short_result = analyze_pois((m1_bundle_short, h4_bundle), _CONFIG, provider)
    grown_result = analyze_pois((m1_bundle_grown, h4_bundle), _CONFIG, provider)

    short_parent = next(
        o
        for o in short_result.poi_observations
        if o.poi_type == PoiType.BUY_ORDER_BLOCK and o.source_timeframe == Timeframe.H4
    )
    grown_parent = next(
        o
        for o in grown_result.poi_observations
        if o.poi_type == PoiType.BUY_ORDER_BLOCK and o.source_timeframe == Timeframe.H4
    )

    assert (
        short_parent.merged_source_poi_record_ids
        == grown_parent.merged_source_poi_record_ids
    )


def test_poi_fingerprint_serializer_matches_domain_and_structure_serializers() -> None:
    sample_fields: dict[str, object] = {
        "decimal_field": Decimal("1.2345"),
        "zero_decimal": Decimal("0"),
        "enum_field": InternalSymbol.XAUUSD,
        "uuid_field": _record_id(1),
        "datetime_field": _BASE_TIME,
        "semver_field": SemVer.parse("1.2.3"),
        "tuple_field": (Decimal("1"), "text", None),
        "none_field": None,
        "bool_field": True,
        "int_field": 42,
        "string_field": "hello",
        "nested_contract_field": {
            "inner_decimal": Decimal("9.99"),
            "inner_uuid": _record_id(2),
            "inner_tuple": (1, 2, 3),
        },
    }

    domain_result = domain_canonicalize(sample_fields)
    structure_result = structure_canonicalize(sample_fields)
    poi_result = poi_canonicalize(sample_fields)

    assert domain_result == structure_result == poi_result

    domain_hash = domain_fingerprint(sample_fields)
    structure_hash = structure_fingerprint(sample_fields)
    poi_hash = poi_fingerprint(sample_fields)

    assert domain_hash == structure_hash == poi_hash
