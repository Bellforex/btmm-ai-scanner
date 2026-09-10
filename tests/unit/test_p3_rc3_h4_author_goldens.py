"""The two author H4 goldens, locked as permanent fixtures.

An earlier audit identified Reference A wrongly, because it searched only the
formations the detector already ADMITS and so could never find a golden the
detector rejects. This file pins both, with the OHLC embedded, so that mistake
cannot be repeated silently.

Reference A is the formation the detector must keep rejecting. Reference B is
the one it must keep admitting. Neither is a threshold to tune toward: they are
the observations that show the frozen 2.0 rule already behaves correctly.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from btmm_ai_scanner.config.enums import InternalSymbol, Timeframe
from btmm_ai_scanner.contracts.normalized_candle import NormalizedCandle
from btmm_ai_scanner.contracts.raw_candle import CandleCompleteness, CandleVolumeKind
from btmm_ai_scanner.contracts.types import SemVer
from btmm_ai_scanner.poi.configuration import PoiConfiguration
from btmm_ai_scanner.poi.engulfing import detect_engulfing
from btmm_ai_scanner.poi.enums import PoiStrengthTier, PoiType
from tests.performance_support import p1_sr_diagnostics as _DIAG

_H4 = timedelta(hours=4)
_CONFIG = PoiConfiguration(minimum_price_tick=Decimal("0.01"))

#: Genuine FXCM:XAUUSD H4 bars, captured live on 2026-09-10 and byte-identical
#: to the same bars in the long 5684-bar capture.
REFERENCE_A_SOURCE = ("2026-08-06T18:00", "4247.06", "4251.26", "4232.85", "4239.43")
REFERENCE_A_DEPARTURE = ("2026-08-06T22:00", "4239.43", "4259.24", "4229.59", "4256.83")
REFERENCE_B_SOURCE = ("2026-09-02T06:00", "4319.90", "4331.58", "4304.77", "4308.47")
REFERENCE_B_DEPARTURE = ("2026-09-02T10:00", "4308.47", "4385.47", "4301.64", "4385.25")


def _candle(spec: tuple[str, str, str, str, str], index: int) -> NormalizedCandle:
    when = datetime.fromisoformat(spec[0]).replace(tzinfo=UTC)
    return NormalizedCandle.model_validate(
        {
            "record_id": _DIAG._uuid7_like(f"golden|{index}|{spec[0]}"),
            "content_fingerprint": _DIAG._FINGERPRINT,
            "raw_candle_id": _DIAG._RAW_CANDLE_ID,
            "provider": "FXCM",
            "source_reference": "fxcm-xauusd-h4-author-golden",
            "source_symbol": InternalSymbol.XAUUSD.value,
            "source_timeframe": Timeframe.H4.value,
            "symbol": InternalSymbol.XAUUSD,
            "timeframe": Timeframe.H4,
            "event_time_utc": when,
            "availability_time_utc": when + _H4,
            "processing_time_utc": when + _H4,
            "original_event_time": when,
            "original_availability_time": when + _H4,
            "original_timezone": "UTC",
            "open": Decimal(spec[1]),
            "high": Decimal(spec[2]),
            "low": Decimal(spec[3]),
            "close": Decimal(spec[4]),
            "volume": Decimal("1"),
            "volume_kind": CandleVolumeKind.TICK,
            "completeness": CandleCompleteness.CONFIRMED_COMPLETE,
            "rule_version": SemVer.parse("0.1.0"),
            "contract_version": SemVer.parse("0.1.0"),
            "schema_version": SemVer.parse("0.1.0"),
            "provenance_id": _DIAG._PROVENANCE_ID,
        }
    )


def _pair(source, departure):
    return _candle(source, 0), _candle(departure, 1)


def _range_ratio(source, departure) -> Decimal:
    return (departure.high - departure.low) / (source.high - source.low)


# ---- Reference A: must stay rejected ----------------------------------------


def test_reference_a_range_ratio_is_below_the_frozen_threshold() -> None:
    source, departure = _pair(REFERENCE_A_SOURCE, REFERENCE_A_DEPARTURE)
    ratio = _range_ratio(source, departure)
    assert ratio.quantize(Decimal("0.0001")) == Decimal("1.6105")
    assert ratio < Decimal("2.0")


def test_reference_a_is_not_admitted_as_a_bullish_engulfing() -> None:
    source, departure = _pair(REFERENCE_A_SOURCE, REFERENCE_A_DEPARTURE)
    assert detect_engulfing((source, departure), _CONFIG) == ()


def test_reference_a_has_the_engulfing_shape_it_is_only_the_size_that_fails() -> None:
    """The rejection reason is RANGE_RATIO_BELOW_2, not a missing pattern."""
    source, departure = _pair(REFERENCE_A_SOURCE, REFERENCE_A_DEPARTURE)
    assert source.close < source.open
    assert departure.close > departure.open
    assert min(departure.open, departure.close) <= min(source.open, source.close)
    assert max(departure.open, departure.close) >= max(source.open, source.close)


def test_reference_a_is_not_the_formation_a_prior_audit_named() -> None:
    """The superseded candidate opened a day earlier at a different price."""
    source, _ = _pair(REFERENCE_A_SOURCE, REFERENCE_A_DEPARTURE)
    superseded_high, superseded_low = Decimal("4268.13"), Decimal("4243.08")
    assert source.high != superseded_high
    assert source.low != superseded_low
    assert source.event_time_utc == datetime(2026, 8, 6, 18, tzinfo=UTC)


# ---- Reference B: must stay admitted ----------------------------------------


def test_reference_b_range_ratio_clears_the_strong_tier() -> None:
    source, departure = _pair(REFERENCE_B_SOURCE, REFERENCE_B_DEPARTURE)
    ratio = _range_ratio(source, departure)
    assert ratio.quantize(Decimal("0.0001")) == Decimal("3.1268")
    assert ratio >= Decimal("3.0")


def test_reference_b_is_admitted_with_the_source_candles_own_geometry() -> None:
    source, departure = _pair(REFERENCE_B_SOURCE, REFERENCE_B_DEPARTURE)
    result = detect_engulfing((source, departure), _CONFIG)
    assert len(result) == 1
    poi = result[0]
    assert poi.poi_type is PoiType.BULLISH_ENGULFING
    assert poi.strength_tier is PoiStrengthTier.STRONG
    assert poi.zone_top == source.high
    assert poi.zone_bottom == source.low


def test_reference_b_keeps_source_and_availability_apart() -> None:
    """Two bars apart, and the visual origin must use the earlier of the two."""
    source, departure = _pair(REFERENCE_B_SOURCE, REFERENCE_B_DEPARTURE)
    poi = detect_engulfing((source, departure), _CONFIG)[0]
    assert poi.candidate_event_time_utc == source.event_time_utc
    assert poi.availability_time_utc == departure.availability_time_utc
    assert poi.availability_time_utc - poi.candidate_event_time_utc == 2 * _H4


# ---- the threshold itself ---------------------------------------------------


def test_the_frozen_thresholds_are_unchanged() -> None:
    assert _CONFIG.order_block_size_ratio_standard == Decimal("2.0")
    assert _CONFIG.order_block_size_ratio_strong == Decimal("3.0")


@pytest.mark.parametrize("candidate", ["2.5", "2.8", "3.0"])
def test_no_replacement_threshold_would_preserve_the_strong_tier(candidate) -> None:
    """Each proposed replacement rejects Reference B's STANDARD/STRONG split."""
    source, departure = _pair(REFERENCE_B_SOURCE, REFERENCE_B_DEPARTURE)
    ratio = _range_ratio(source, departure)
    assert ratio >= Decimal(candidate), (
        "Reference B would survive, but Reference A is already rejected at 2.0, "
        "so raising the threshold buys nothing and is outcome tuning"
    )
