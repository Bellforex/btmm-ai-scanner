"""The Base family axis: arrival leg + base + departure leg.

`PoiType` only ever carried the DEPARTURE direction, so `BASE_RALLY` collapsed
Rally-Base-Rally together with Drop-Base-Rally, and `BASE_DROP` collapsed
Rally-Base-Drop with Drop-Base-Drop. The arrival leg was not modelled at all.

`BaseFamily` restores it as RC5 semantic metadata. The frozen transport codes
are deliberately untouched, so these tests assert BOTH halves: the family is
correct, AND the `PoiType` it transports as has not moved.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

from btmm_ai_scanner.config.enums import InternalSymbol, Timeframe
from btmm_ai_scanner.contracts.normalized_candle import NormalizedCandle
from btmm_ai_scanner.contracts.raw_candle import CandleCompleteness, CandleVolumeKind
from btmm_ai_scanner.poi.bases import classify_base_family, detect_bases
from btmm_ai_scanner.poi.configuration import PoiConfiguration
from btmm_ai_scanner.poi.enums import BASE_FAMILY_TRANSPORT, BaseFamily, PoiType

_RAW_CANDLE_ID = UUID("0193f450-1234-7abc-8def-abcdefabcdaa")
_PROVENANCE_ID = UUID("0193f450-1234-7abc-8def-abcdefabcdff")
_FINGERPRINT = "a" * 64
_BASE_TIME = datetime(2026, 1, 1, tzinfo=UTC)
_CONFIG = PoiConfiguration(minimum_price_tick=Decimal("0.01"))


def _candle(
    index: int, open_: str, high: str, low: str, close: str
) -> NormalizedCandle:
    event_time = _BASE_TIME + timedelta(minutes=index)
    availability = event_time + timedelta(minutes=1)
    return NormalizedCandle.model_validate(
        {
            "record_id": UUID(f"0193f450-1234-7abc-8def-{index:012x}"),
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
            "volume": Decimal("100"),
            "volume_kind": CandleVolumeKind.TICK,
            "completeness": CandleCompleteness.CONFIRMED_COMPLETE,
            "rule_version": "1.0.0",
            "contract_version": "1.0.0",
            "schema_version": "1.0.0",
            "provenance_id": _PROVENANCE_ID,
        }
    )


def _series(arrival_up: bool, departure_up: bool) -> tuple[NormalizedCandle, ...]:
    """Arrival candle, two compact base candles, then a decisive departure.

    The base sits at 100.00-100.10 and every approved Base constraint is met by
    construction: two base bars, each far smaller than the departure, tightly
    overlapped, flat midpoints and a departure that closes beyond the base.
    """
    arrival = (
        _candle(0, "99.00", "100.10", "99.00", "100.05")
        if arrival_up
        else _candle(0, "101.00", "101.00", "100.00", "100.05")
    )
    base = (
        _candle(1, "100.02", "100.10", "100.00", "100.06"),
        _candle(2, "100.06", "100.10", "100.00", "100.03"),
    )
    departure = (
        _candle(3, "100.05", "101.20", "100.05", "101.10")
        if departure_up
        else _candle(3, "100.05", "100.05", "98.90", "99.00")
    )
    return (arrival, *base, departure)


def _only_base(arrival_up: bool, departure_up: bool):
    bases = detect_bases(_series(arrival_up, departure_up), _CONFIG)
    assert len(bases) == 1, f"expected exactly one base, got {len(bases)}"
    return bases[0]


# --------------------------------------------------------------------------
# 1-4: the four families, and the transport code each must still carry
# --------------------------------------------------------------------------


def test_rally_base_rally() -> None:
    base = _only_base(arrival_up=True, departure_up=True)
    assert base.base_family is BaseFamily.RALLY_BASE_RALLY
    assert base.poi_type is PoiType.BASE_RALLY


def test_drop_base_rally() -> None:
    base = _only_base(arrival_up=False, departure_up=True)
    assert base.base_family is BaseFamily.DROP_BASE_RALLY
    assert base.poi_type is PoiType.BASE_RALLY


def test_rally_base_drop() -> None:
    base = _only_base(arrival_up=True, departure_up=False)
    assert base.base_family is BaseFamily.RALLY_BASE_DROP
    assert base.poi_type is PoiType.BASE_DROP


def test_drop_base_drop() -> None:
    base = _only_base(arrival_up=False, departure_up=False)
    assert base.base_family is BaseFamily.DROP_BASE_DROP
    assert base.poi_type is PoiType.BASE_DROP


def test_the_two_rally_families_are_distinguishable_but_transport_identically() -> None:
    """The exact collapse that lost the arrival leg, now visible and still safe."""
    rbr = _only_base(arrival_up=True, departure_up=True)
    dbr = _only_base(arrival_up=False, departure_up=True)
    assert rbr.base_family is not dbr.base_family
    assert rbr.poi_type is dbr.poi_type is PoiType.BASE_RALLY


def test_the_two_drop_families_are_distinguishable_but_transport_identically() -> None:
    rbd = _only_base(arrival_up=True, departure_up=False)
    dbd = _only_base(arrival_up=False, departure_up=False)
    assert rbd.base_family is not dbd.base_family
    assert rbd.poi_type is dbd.poi_type is PoiType.BASE_DROP


def test_transport_mapping_is_total_and_matches_the_frozen_codes() -> None:
    assert set(BASE_FAMILY_TRANSPORT) == set(BaseFamily)
    assert set(BASE_FAMILY_TRANSPORT.values()) == {
        PoiType.BASE_RALLY,
        PoiType.BASE_DROP,
    }
    for family, poi_type in BASE_FAMILY_TRANSPORT.items():
        assert (
            "RALLY" if poi_type is PoiType.BASE_RALLY else "DROP"
        ) == family.value.rsplit("_", 1)[-1]


# --------------------------------------------------------------------------
# the axis must not reject anything
# --------------------------------------------------------------------------


def test_the_family_axis_does_not_change_the_base_population() -> None:
    """No arrival STRENGTH gate exists, deliberately: nothing in the codebase
    supplies an impulse qualification for a POI-level arrival, and inventing a
    constant was refused. The axis therefore adds meaning without rejecting a
    single candidate."""
    for arrival_up in (True, False):
        for departure_up in (True, False):
            series = _series(arrival_up, departure_up)
            assert len(detect_bases(series, _CONFIG)) == 1


def test_family_is_none_when_no_arrival_candle_exists() -> None:
    """Unknown, not assumed. A base starting at the first candle of the series
    has no arrival leg to read."""
    assert classify_base_family(None, PoiType.BASE_RALLY) is None
    assert classify_base_family(None, PoiType.BASE_DROP) is None


def test_arrival_direction_reuses_the_displacement_engine_definition() -> None:
    """`detect_displacement_observations` calls a candle BULLISH when
    ``close >= open``. The same test decides the arrival leg, so no new
    threshold enters the Base rule -- including the doji-ish boundary case,
    which that engine also treats as bullish."""
    flat = _candle(0, "100.00", "100.50", "99.50", "100.00")
    assert flat.close == flat.open
    assert classify_base_family(flat, PoiType.BASE_RALLY) is BaseFamily.RALLY_BASE_RALLY
