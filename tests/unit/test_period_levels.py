import hashlib
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

from btmm_ai_scanner.config.enums import InternalSymbol, Timeframe
from btmm_ai_scanner.contracts.normalized_candle import NormalizedCandle
from btmm_ai_scanner.contracts.raw_candle import CandleCompleteness, CandleVolumeKind
from btmm_ai_scanner.contracts.types import SemVer
from btmm_ai_scanner.domain import MarketMeasurementAnalysis
from btmm_ai_scanner.poi.analyzer import PoiTimeframeInput, analyze_pois
from btmm_ai_scanner.poi.configuration import PoiConfiguration
from btmm_ai_scanner.poi.enums import (
    NOT_APPLICABLE_LIFECYCLE_POI_TYPES,
    PERIOD_LEVEL_POI_TYPES,
    PoiDirection,
    PoiLifecycleStatus,
    PoiType,
)
from btmm_ai_scanner.poi.period_levels import detect_period_levels

_RAW_CANDLE_ID = UUID("0193f450-1234-7abc-8def-abcdefabcdaa")
_PROVENANCE_ID = UUID("0193f450-1234-7abc-8def-abcdefabcdff")
_FINGERPRINT = "a" * 64
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


def _candle_at(
    index: int, event_time: datetime, high: str, low: str
) -> NormalizedCandle:
    availability = event_time + timedelta(minutes=1)
    return NormalizedCandle.model_validate(
        {
            "record_id": _record_id(index),
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
            "open": Decimal("100"),
            "high": Decimal(high),
            "low": Decimal(low),
            "close": Decimal("100"),
            "volume": Decimal("10"),
            "volume_kind": CandleVolumeKind.TICK,
            "completeness": CandleCompleteness.CONFIRMED_COMPLETE,
            "rule_version": SemVer.parse("0.1.0"),
            "contract_version": SemVer.parse("0.1.0"),
            "schema_version": SemVer.parse("0.1.0"),
            "provenance_id": _PROVENANCE_ID,
        }
    )


def _empty_measurement_analysis(candle_count: int) -> MarketMeasurementAnalysis:
    return MarketMeasurementAnalysis(
        symbol=InternalSymbol.XAUUSD,
        timeframe=Timeframe.M1,
        analyzed_candle_count=candle_count,
        confirmed_swings=(),
        displacement_observations=(),
        equal_level_clusters=(),
        support_resistance_zones=(),
        trendlines=(),
    )


def test_period_level_windows_use_exact_utc_calendar_day_week_and_month_boundaries() -> (
    None
):
    thursday_noon = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
    candle = _candle_at(0, thursday_noon, "101", "99")

    candidates = detect_period_levels((candle,), _CONFIG)
    by_type = {c.poi_type: c for c in candidates}

    day_high = by_type[PoiType.CURRENT_DAY_HIGH]
    assert day_high.period_start_time_utc == datetime(2026, 1, 1, tzinfo=UTC)
    assert day_high.period_end_time_utc == datetime(2026, 1, 2, tzinfo=UTC)

    week_high = by_type[PoiType.CURRENT_WEEK_HIGH]
    assert week_high.period_start_time_utc == datetime(2025, 12, 29, tzinfo=UTC)
    assert week_high.period_end_time_utc == datetime(2026, 1, 5, tzinfo=UTC)

    month_high = by_type[PoiType.CURRENT_MONTH_HIGH]
    assert month_high.period_start_time_utc == datetime(2026, 1, 1, tzinfo=UTC)
    assert month_high.period_end_time_utc == datetime(2026, 2, 1, tzinfo=UTC)


def test_previous_period_skips_empty_weekend_and_holiday_windows() -> None:
    thursday = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
    monday = datetime(2026, 1, 5, 12, 0, tzinfo=UTC)
    candles = (
        _candle_at(0, thursday, "101", "99"),
        _candle_at(1, monday, "103", "98"),
    )

    candidates = detect_period_levels(candles, _CONFIG)
    previous_day_high = next(
        c for c in candidates if c.poi_type == PoiType.PREVIOUS_DAY_HIGH
    )

    assert previous_day_high.period_start_time_utc == datetime(2026, 1, 1, tzinfo=UTC)
    assert previous_day_high.representative_price == Decimal("101")


def test_previous_period_level_content_is_fixed_after_period_closes() -> None:
    day1 = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
    day2_first = datetime(2026, 1, 2, 1, 0, tzinfo=UTC)
    day2_second = datetime(2026, 1, 2, 5, 0, tzinfo=UTC)

    candles_short = (
        _candle_at(0, day1, "101", "99"),
        _candle_at(1, day2_first, "102", "98.5"),
    )
    candles_long = (
        *candles_short,
        _candle_at(2, day2_second, "105", "97"),
    )

    short_result = next(
        c
        for c in detect_period_levels(candles_short, _CONFIG)
        if c.poi_type == PoiType.PREVIOUS_DAY_HIGH
    )
    long_result = next(
        c
        for c in detect_period_levels(candles_long, _CONFIG)
        if c.poi_type == PoiType.PREVIOUS_DAY_HIGH
    )

    assert short_result.representative_price == long_result.representative_price
    assert short_result.availability_time_utc == long_result.availability_time_utc


def test_current_period_level_fingerprint_changes_as_new_extreme_appears() -> None:
    provider = _HashIdentityProvider()
    day1 = datetime(2026, 1, 1, 1, 0, tzinfo=UTC)
    day1_later = datetime(2026, 1, 1, 5, 0, tzinfo=UTC)

    prefix = (_candle_at(0, day1, "101", "99"),)
    grown = (*prefix, _candle_at(1, day1_later, "110", "99"))

    bundle_prefix = PoiTimeframeInput(
        timeframe=Timeframe.M1,
        candles=prefix,
        measurement_analysis=_empty_measurement_analysis(len(prefix)),
    )
    bundle_grown = PoiTimeframeInput(
        timeframe=Timeframe.M1,
        candles=grown,
        measurement_analysis=_empty_measurement_analysis(len(grown)),
    )

    result_prefix = analyze_pois((bundle_prefix,), _CONFIG, provider)
    result_grown = analyze_pois((bundle_grown,), _CONFIG, provider)

    prefix_high = next(
        o
        for o in result_prefix.poi_observations
        if o.poi_type == PoiType.CURRENT_DAY_HIGH
    )
    grown_high = next(
        o
        for o in result_grown.poi_observations
        if o.poi_type == PoiType.CURRENT_DAY_HIGH
    )

    assert prefix_high.record_id == grown_high.record_id
    assert prefix_high.content_fingerprint != grown_high.content_fingerprint
    assert grown_high.zone_top == Decimal("110")


def test_current_day_high_and_low_track_running_extreme_within_the_window() -> None:
    day1 = datetime(2026, 1, 1, 1, 0, tzinfo=UTC)
    day1_mid = datetime(2026, 1, 1, 5, 0, tzinfo=UTC)
    day1_late = datetime(2026, 1, 1, 10, 0, tzinfo=UTC)

    candles = (
        _candle_at(0, day1, "101", "99"),
        _candle_at(1, day1_mid, "105", "97"),
        _candle_at(2, day1_late, "103", "98"),
    )

    candidates = detect_period_levels(candles, _CONFIG)
    day_high = next(c for c in candidates if c.poi_type == PoiType.CURRENT_DAY_HIGH)
    day_low = next(c for c in candidates if c.poi_type == PoiType.CURRENT_DAY_LOW)

    assert day_high.representative_price == Decimal("105")
    assert day_low.representative_price == Decimal("97")
    assert day_high.direction == PoiDirection.BEARISH
    assert day_low.direction == PoiDirection.BULLISH


def test_period_level_lifecycle_status_is_fixed_at_not_applicable() -> None:
    provider = _HashIdentityProvider()
    day1 = datetime(2026, 1, 1, 1, 0, tzinfo=UTC)
    candles = (_candle_at(0, day1, "101", "99"),)
    bundle = PoiTimeframeInput(
        timeframe=Timeframe.M1,
        candles=candles,
        measurement_analysis=_empty_measurement_analysis(len(candles)),
    )

    result = analyze_pois((bundle,), _CONFIG, provider)

    period_states = [
        state
        for state in result.current_poi_states
        if state.poi_type in PERIOD_LEVEL_POI_TYPES
    ]
    assert len(period_states) > 0
    for state in period_states:
        assert state.poi_lifecycle_status == PoiLifecycleStatus.NOT_APPLICABLE
        assert state.poi_type in NOT_APPLICABLE_LIFECYCLE_POI_TYPES


def test_period_level_identity_is_stable_across_a_growing_window_and_rollover_creates_a_new_record() -> (
    None
):
    provider = _HashIdentityProvider()
    day1 = datetime(2026, 1, 1, 1, 0, tzinfo=UTC)
    day1_later = datetime(2026, 1, 1, 10, 0, tzinfo=UTC)
    day2 = datetime(2026, 1, 2, 1, 0, tzinfo=UTC)

    within_day = (
        _candle_at(0, day1, "101", "99"),
        _candle_at(1, day1_later, "102", "98"),
    )
    rolled_over = (*within_day, _candle_at(2, day2, "103", "97"))

    bundle_within = PoiTimeframeInput(
        timeframe=Timeframe.M1,
        candles=within_day,
        measurement_analysis=_empty_measurement_analysis(len(within_day)),
    )
    bundle_rolled = PoiTimeframeInput(
        timeframe=Timeframe.M1,
        candles=rolled_over,
        measurement_analysis=_empty_measurement_analysis(len(rolled_over)),
    )

    result_within = analyze_pois((bundle_within,), _CONFIG, provider)
    result_rolled = analyze_pois((bundle_rolled,), _CONFIG, provider)

    current_high_within = next(
        o
        for o in result_within.poi_observations
        if o.poi_type == PoiType.CURRENT_DAY_HIGH
    )
    previous_high_after_rollover = next(
        o
        for o in result_rolled.poi_observations
        if o.poi_type == PoiType.PREVIOUS_DAY_HIGH
    )
    current_high_after_rollover = next(
        o
        for o in result_rolled.poi_observations
        if o.poi_type == PoiType.CURRENT_DAY_HIGH
    )

    assert previous_high_after_rollover.record_id != current_high_within.record_id
    assert current_high_after_rollover.record_id != current_high_within.record_id
    assert previous_high_after_rollover.representative_price == Decimal("102")


def test_all_twelve_period_level_types_are_covered() -> None:
    assert len(PERIOD_LEVEL_POI_TYPES) == 12
    for poi_type in PERIOD_LEVEL_POI_TYPES:
        assert poi_type.name.startswith(("PREVIOUS_", "CURRENT_"))
