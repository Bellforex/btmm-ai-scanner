"""Type, source candles and zone must come from ONE semantic observation.

The failure this forbids is a renderer or transport that pairs the TYPE of one
candidate with the GEOMETRY of another -- a Doji drawn with an Order Block's
box, an FVG drawn with a Base's. Nothing observed today does that, and this
module exists so that it cannot start.

It is deliberately generic: it walks the real detectors over a real series and
asserts the invariant for every candidate produced, rather than hand-listing
cases that could drift out of date.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

from btmm_ai_scanner.config.enums import InternalSymbol, Timeframe
from btmm_ai_scanner.contracts.normalized_candle import NormalizedCandle
from btmm_ai_scanner.contracts.raw_candle import CandleCompleteness, CandleVolumeKind
from btmm_ai_scanner.poi.bases import detect_bases
from btmm_ai_scanner.poi.configuration import PoiConfiguration
from btmm_ai_scanner.poi.engulfing import detect_engulfing
from btmm_ai_scanner.poi.enums import PoiType
from btmm_ai_scanner.poi.fair_value_gaps import detect_fair_value_gaps
from btmm_ai_scanner.poi.order_blocks import detect_order_blocks
from btmm_ai_scanner.poi.pressure_wicks import detect_pressure_wicks
from btmm_ai_scanner.poi.single_candle_reversals import detect_single_candle_reversals

_RAW_CANDLE_ID = UUID("0193f450-1234-7abc-8def-abcdefabcdaa")
_PROVENANCE_ID = UUID("0193f450-1234-7abc-8def-abcdefabcdff")
_FINGERPRINT = "a" * 64
_T0 = datetime(2026, 1, 1, tzinfo=UTC)
_CONFIG = PoiConfiguration(minimum_price_tick=Decimal("0.01"))


def _candle(index: int, o: str, h: str, low: str, c: str) -> NormalizedCandle:
    event_time = _T0 + timedelta(minutes=index)
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
            "open": Decimal(o),
            "high": Decimal(h),
            "low": Decimal(low),
            "close": Decimal(c),
            "volume": Decimal("100"),
            "volume_kind": CandleVolumeKind.TICK,
            "completeness": CandleCompleteness.CONFIRMED_COMPLETE,
            "rule_version": "1.0.0",
            "contract_version": "1.0.0",
            "schema_version": "1.0.0",
            "provenance_id": _PROVENANCE_ID,
        }
    )


#: A series carrying a compact base, a decisive drop, an imbalance and wicks,
#: so several different families fire over the same bars.
_SERIES = tuple(
    _candle(i, o, h, low, c)
    for i, (o, h, low, c) in enumerate(
        [
            ("99.00", "100.10", "99.00", "100.05"),
            ("100.02", "100.10", "100.00", "100.06"),
            ("100.06", "100.10", "100.00", "100.03"),
            ("100.05", "100.05", "98.90", "99.00"),
            ("98.95", "99.00", "97.50", "97.60"),
            ("97.60", "99.50", "97.55", "97.70"),
            ("97.70", "97.80", "96.00", "96.10"),
            ("96.10", "96.20", "95.00", "95.10"),
            ("95.10", "97.00", "95.05", "96.80"),
            ("96.80", "96.90", "94.00", "94.10"),
        ]
    )
)


def _all_candidates() -> list[object]:
    return [
        *detect_bases(_SERIES, _CONFIG),
        *detect_fair_value_gaps(_SERIES, _CONFIG),
        *detect_order_blocks(_SERIES, _CONFIG),
        *detect_pressure_wicks(_SERIES, _CONFIG),
        *detect_engulfing(_SERIES, _CONFIG),
        *detect_single_candle_reversals(_SERIES, _CONFIG),
    ]


def test_the_series_actually_produces_several_families() -> None:
    """Guards the guard: an empty sweep would make every assertion vacuous."""
    candidates = _all_candidates()
    assert candidates, "fixture produced no candidates"
    assert len({c.poi_type for c in candidates}) >= 2


def test_every_candidate_zone_is_bounded_by_its_own_source_candles() -> None:
    """The invariant. A zone that escapes its own source candles' range proves
    the geometry came from a different observation than the type."""
    by_id = {c.record_id: c for c in _SERIES}
    for candidate in _all_candidates():
        sources = [by_id[rid] for rid in candidate.source_candle_record_ids]
        assert sources, f"{candidate.poi_type} has no source candles"
        highest = max(s.high for s in sources)
        lowest = min(s.low for s in sources)
        assert candidate.zone_top <= highest, candidate.poi_type
        assert candidate.zone_bottom >= lowest, candidate.poi_type
        assert candidate.zone_top > candidate.zone_bottom, candidate.poi_type


def test_every_candidate_source_candle_exists_in_the_series() -> None:
    known = {c.record_id for c in _SERIES}
    for candidate in _all_candidates():
        for record_id in candidate.source_candle_record_ids:
            assert record_id in known, candidate.poi_type


def test_no_two_families_share_a_zone_and_a_source_set() -> None:
    """Different families over identical candles must still differ in geometry
    or in source span; identical on both would mean one borrowed the other."""
    seen: dict[tuple[object, ...], PoiType] = {}
    for candidate in _all_candidates():
        signature = (
            candidate.source_candle_record_ids,
            candidate.zone_top,
            candidate.zone_bottom,
        )
        previous = seen.get(signature)
        assert previous is None or previous is candidate.poi_type, (
            f"{previous} and {candidate.poi_type} share source candles AND zone"
        )
        seen[signature] = candidate.poi_type


def test_a_doji_never_becomes_an_order_block() -> None:
    """The historical misclassification class, pinned shut.

    A small candle immediately before displacement must not acquire the
    ORDER BLOCK type. If the OB detector independently qualifies one from the
    same candle under its own doctrine, both identities stay explicit and
    authority resolves them later -- what may never happen is silent mutation.
    """
    order_blocks = detect_order_blocks(_SERIES, _CONFIG)
    for block in order_blocks:
        assert block.poi_type in {
            PoiType.BUY_ORDER_BLOCK,
            PoiType.SELL_ORDER_BLOCK,
        }
        # OB geometry is its origin candle's full range, never a doji body.
        by_id = {c.record_id: c for c in _SERIES}
        origin = by_id[block.source_candle_record_ids[0]]
        assert block.zone_top == origin.high
        assert block.zone_bottom == origin.low
