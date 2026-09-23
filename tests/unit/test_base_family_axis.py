"""The Base family axis: arrival leg + base + departure leg.

`PoiType` only ever carried the DEPARTURE direction, so `BASE_RALLY` collapsed
Rally-Base-Rally together with Drop-Base-Rally, and `BASE_DROP` collapsed
Rally-Base-Drop with Drop-Base-Drop. The arrival leg was not modelled at all.

`BaseFamily` restores it as RC5 semantic metadata, and the frozen transport
codes are deliberately untouched.

This module owns the TRANSPORT half and the population half: the detector sees
only the base and the departure, it must emit every candidate it used to, and
the family must never change the code a candidate travels as. The arrival leg
itself is structural and is proved in `test_base_arrival_structural`.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

from btmm_ai_scanner.config.enums import InternalSymbol, Timeframe
from btmm_ai_scanner.contracts.normalized_candle import NormalizedCandle
from btmm_ai_scanner.contracts.raw_candle import CandleCompleteness, CandleVolumeKind
from btmm_ai_scanner.poi.base_arrival import assign_base_arrival
from btmm_ai_scanner.poi.bases import detect_bases
from btmm_ai_scanner.poi.configuration import PoiConfiguration
from btmm_ai_scanner.poi.enums import BASE_FAMILY_TRANSPORT, BaseFamily, PoiType
from btmm_ai_scanner.structure.enums import StructureDirection

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
# the detector emits geometry, and only geometry
# --------------------------------------------------------------------------


def test_the_departure_still_decides_the_transport_code() -> None:
    """The half of the formation the detector CAN see, unchanged."""
    for arrival_up in (True, False):
        assert _only_base(arrival_up, departure_up=True).poi_type is PoiType.BASE_RALLY
        assert _only_base(arrival_up, departure_up=False).poi_type is PoiType.BASE_DROP


def test_the_detector_emits_no_family_whatever_the_preceding_candle_does() -> None:
    """The collapse that lost the arrival leg is NOT repaired by looking at one
    candle. These four series differ only in the candle before the base, and
    the detector must be blind to it -- that candle is not the arrival leg."""
    families = {
        _only_base(arrival_up, departure_up).base_family
        for arrival_up in (True, False)
        for departure_up in (True, False)
    }
    assert families == {None}


def test_a_series_with_no_structure_yields_no_family() -> None:
    """Four candles establish no leg, so the arrival is UNDETERMINED and the
    family stays unknown. Assigning one here would be the fallback the author
    refused."""
    series = _series(arrival_up=True, departure_up=False)
    assigned, facts = assign_base_arrival(detect_bases(series, _CONFIG), ([], []), None)
    assert len(assigned) == 1
    assert assigned[0].base_family is None
    fact = next(iter(facts.values()))
    assert fact.arrival_direction is StructureDirection.UNDETERMINED
    assert fact.arrival_known_from_utc is None
    assert fact.arrival_leg_id is None
    # the reference instant is still recorded, so the gap is explicit
    assert fact.arrival_reference_utc == assigned[0].candidate_event_time_utc


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
