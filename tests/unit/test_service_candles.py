from datetime import UTC, datetime
from decimal import Decimal

from btmm_ai_scanner.config.enums import InternalSymbol, Timeframe
from btmm_ai_scanner.contracts.raw_candle import CandleCompleteness, CandleVolumeKind
from btmm_ai_scanner.service.candles import (
    DEFAULT_MINIMUM_PRICE_TICK,
    build_normalized_candle,
)
from btmm_ai_scanner.service.schemas import RawBar

_PROVIDER = "BELLFOREX_WEB"


def _bar(**overrides: object) -> RawBar:
    defaults: dict[str, object] = {
        "time": datetime(2026, 1, 1, 12, 0, tzinfo=UTC),
        "open": Decimal("2000.00"),
        "high": Decimal("2001.00"),
        "low": Decimal("1999.00"),
        "close": Decimal("2000.50"),
        "volume": Decimal("125"),
    }
    defaults.update(overrides)
    return RawBar.model_validate(defaults)


def test_build_normalized_candle_maps_fields_faithfully() -> None:
    bar = _bar()
    candle = build_normalized_candle(
        symbol=InternalSymbol.XAUUSD,
        timeframe=Timeframe.H1,
        bar=bar,
        provider=_PROVIDER,
    )
    assert candle.symbol is InternalSymbol.XAUUSD
    assert candle.timeframe is Timeframe.H1
    assert candle.provider == _PROVIDER
    assert candle.open == bar.open
    assert candle.high == bar.high
    assert candle.low == bar.low
    assert candle.close == bar.close
    assert candle.volume == bar.volume
    assert candle.event_time_utc == bar.time.astimezone(UTC)
    assert candle.completeness == CandleCompleteness.CONFIRMED_COMPLETE
    assert candle.volume_kind == CandleVolumeKind.TICK


def test_build_normalized_candle_without_volume_is_unknown_volume_kind() -> None:
    candle = build_normalized_candle(
        symbol=InternalSymbol.EURUSD,
        timeframe=Timeframe.M15,
        bar=_bar(volume=None),
        provider=_PROVIDER,
    )
    assert candle.volume is None
    assert candle.volume_kind == CandleVolumeKind.UNKNOWN


def test_build_normalized_candle_record_id_differs_from_raw_candle_id() -> None:
    candle = build_normalized_candle(
        symbol=InternalSymbol.GBPUSD,
        timeframe=Timeframe.H4,
        bar=_bar(),
        provider=_PROVIDER,
    )
    assert candle.record_id != candle.raw_candle_id
    assert candle.record_id != candle.provenance_id
    assert candle.raw_candle_id != candle.provenance_id


def test_build_normalized_candle_is_deterministic_for_identical_input() -> None:
    bar = _bar()
    first = build_normalized_candle(
        symbol=InternalSymbol.XAUUSD, timeframe=Timeframe.M5, bar=bar, provider=_PROVIDER
    )
    second = build_normalized_candle(
        symbol=InternalSymbol.XAUUSD, timeframe=Timeframe.M5, bar=bar, provider=_PROVIDER
    )
    assert first.record_id == second.record_id
    assert first.raw_candle_id == second.raw_candle_id
    assert first.provenance_id == second.provenance_id
    assert first.content_fingerprint == second.content_fingerprint


def test_build_normalized_candle_differs_for_different_bar_content() -> None:
    first = build_normalized_candle(
        symbol=InternalSymbol.XAUUSD,
        timeframe=Timeframe.M5,
        bar=_bar(),
        provider=_PROVIDER,
    )
    second = build_normalized_candle(
        symbol=InternalSymbol.XAUUSD,
        timeframe=Timeframe.M5,
        bar=_bar(close=Decimal("2005.00"), high=Decimal("2006.00")),
        provider=_PROVIDER,
    )
    assert first.record_id != second.record_id
    assert first.content_fingerprint != second.content_fingerprint


def test_build_normalized_candle_differs_across_timeframes_for_same_bar() -> None:
    bar = _bar()
    m5 = build_normalized_candle(
        symbol=InternalSymbol.XAUUSD, timeframe=Timeframe.M5, bar=bar, provider=_PROVIDER
    )
    h1 = build_normalized_candle(
        symbol=InternalSymbol.XAUUSD, timeframe=Timeframe.H1, bar=bar, provider=_PROVIDER
    )
    assert m5.record_id != h1.record_id


def test_default_minimum_price_tick_covers_every_internal_symbol() -> None:
    assert set(DEFAULT_MINIMUM_PRICE_TICK) == set(InternalSymbol)
    for tick in DEFAULT_MINIMUM_PRICE_TICK.values():
        assert tick > 0
