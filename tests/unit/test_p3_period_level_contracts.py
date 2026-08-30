"""P3-I0 — B-6: period-level calendar boundary and tie contracts.

THIS FILE ASSERTS THE AUTHORITATIVE PRODUCTION CONTRACT.

The 12 period-level types are P3-CONTEXT (deferred from the P3 CORE parity
gate by AD-6), but their semantics are still pinned here so the deferral is a
scheduling decision rather than an unexamined gap.

Two behaviours had no coverage and are easy to get wrong in a port:

* the December -> January month rollover (`_month_window`, period_levels.py:43-49
  is the only place a year increment happens);
* the equal-extreme tie rule (`_extreme_candidates`, :86-93 uses STRICT `>` and
  `<`, so the FIRST candle achieving the extreme wins and later equals never
  displace it).
"""

from __future__ import annotations

import importlib.util
import sys
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from types import ModuleType
from uuid import UUID

from btmm_ai_scanner.config.enums import InternalSymbol, Timeframe
from btmm_ai_scanner.contracts.normalized_candle import NormalizedCandle
from btmm_ai_scanner.contracts.raw_candle import CandleCompleteness, CandleVolumeKind
from btmm_ai_scanner.contracts.types import SemVer
from btmm_ai_scanner.poi.enums import PoiType
from btmm_ai_scanner.poi.period_levels import (
    PeriodLevelCandidate,
    detect_period_levels,
)


def _load(name: str, filename: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        name, Path(__file__).with_name(filename)
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


_C = _load("_p3pl_contracts", "test_p3_core_contracts.py")
_CONFIG = _C._CONFIG
_RAW_CANDLE_ID = _C._RAW_CANDLE_ID
_PROVENANCE_ID = _C._PROVENANCE_ID
_FINGERPRINT = _C._FINGERPRINT


def _at(
    index: int, moment: datetime, open_: str, high: str, low: str, close: str
) -> NormalizedCandle:
    availability = moment + timedelta(minutes=15)
    return NormalizedCandle.model_validate(
        {
            "record_id": UUID(f"0193f470-1234-7abc-8def-{index:012x}"),
            "content_fingerprint": _FINGERPRINT,
            "raw_candle_id": _RAW_CANDLE_ID,
            "provider": "FXCM",
            "source_reference": "fxcm-xauusd-m15",
            "source_symbol": InternalSymbol.XAUUSD.value,
            "source_timeframe": Timeframe.M15.value,
            "symbol": InternalSymbol.XAUUSD,
            "timeframe": Timeframe.M15,
            "event_time_utc": moment,
            "availability_time_utc": availability,
            "processing_time_utc": availability,
            "original_event_time": moment,
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


def _by_type(
    candidates: tuple[PeriodLevelCandidate, ...], poi_type: PoiType
) -> list[PeriodLevelCandidate]:
    return [c for c in candidates if c.poi_type == poi_type]


def test_december_to_january_rollover_increments_the_year() -> None:
    """`_month_window` is the only year-incrementing branch in the detector."""
    december = _at(
        0, datetime(2025, 12, 31, 22, 0, tzinfo=UTC), "100", "105", "95", "100"
    )
    january = _at(1, datetime(2026, 1, 1, 0, 0, tzinfo=UTC), "100", "110", "90", "100")
    got = detect_period_levels((december, january), _CONFIG)

    current_high = _by_type(got, PoiType.CURRENT_MONTH_HIGH)
    previous_high = _by_type(got, PoiType.PREVIOUS_MONTH_HIGH)
    assert len(current_high) == 1
    assert len(previous_high) == 1
    # January is the CURRENT month window; December became PREVIOUS.
    assert current_high[0].representative_price == Decimal("110")
    assert previous_high[0].representative_price == Decimal("105")
    assert current_high[0].period_start_time_utc == datetime(2026, 1, 1, tzinfo=UTC)
    assert current_high[0].period_end_time_utc == datetime(2026, 2, 1, tzinfo=UTC)
    assert previous_high[0].period_start_time_utc == datetime(2025, 12, 1, tzinfo=UTC)
    # The December window's end rolls the YEAR, not just the month.
    assert previous_high[0].period_end_time_utc == datetime(2026, 1, 1, tzinfo=UTC)


def test_previous_period_availability_is_the_first_candle_of_the_new_window() -> None:
    """A previous-period level becomes available at the rollover, not later."""
    december = _at(
        0, datetime(2025, 12, 31, 22, 0, tzinfo=UTC), "100", "105", "95", "100"
    )
    january_first = _at(
        1, datetime(2026, 1, 1, 0, 0, tzinfo=UTC), "100", "110", "90", "100"
    )
    january_later = _at(
        2, datetime(2026, 1, 2, 0, 0, tzinfo=UTC), "100", "108", "92", "100"
    )
    got = detect_period_levels((december, january_first, january_later), _CONFIG)
    previous_high = _by_type(got, PoiType.PREVIOUS_MONTH_HIGH)[0]
    assert previous_high.availability_time_utc == (january_first.availability_time_utc)


def test_equal_extremes_keep_the_first_candle_that_reached_them() -> None:
    """STRICT `>` / `<` means a later EQUAL extreme never displaces the first."""
    first = _at(0, datetime(2026, 3, 2, 0, 0, tzinfo=UTC), "100", "110", "90", "100")
    equal_later = _at(
        1, datetime(2026, 3, 2, 1, 0, tzinfo=UTC), "100", "110", "90", "100"
    )
    got = detect_period_levels((first, equal_later), _CONFIG)

    day_high = _by_type(got, PoiType.CURRENT_DAY_HIGH)[0]
    day_low = _by_type(got, PoiType.CURRENT_DAY_LOW)[0]
    assert day_high.source_candle_record_ids == (first.record_id,)
    assert day_low.source_candle_record_ids == (first.record_id,)
    assert day_high.candidate_event_time_utc == first.event_time_utc


def test_a_strictly_greater_extreme_does_displace_the_earlier_candle() -> None:
    """The mirror of the tie rule: strictly better extremes DO win."""
    first = _at(0, datetime(2026, 3, 2, 0, 0, tzinfo=UTC), "100", "110", "90", "100")
    higher = _at(
        1, datetime(2026, 3, 2, 1, 0, tzinfo=UTC), "100", "110.01", "89.99", "100"
    )
    got = detect_period_levels((first, higher), _CONFIG)
    assert _by_type(got, PoiType.CURRENT_DAY_HIGH)[0].source_candle_record_ids == (
        higher.record_id,
    )
    assert _by_type(got, PoiType.CURRENT_DAY_LOW)[0].source_candle_record_ids == (
        higher.record_id,
    )


def test_period_levels_are_point_zones_with_a_representative_price() -> None:
    """Period levels are the only POI family carrying representative_price."""
    candle = _at(0, datetime(2026, 3, 2, 0, 0, tzinfo=UTC), "100", "110", "90", "100")
    got = detect_period_levels((candle,), _CONFIG)
    assert len(got) > 0
    for candidate in got:
        assert candidate.representative_price in (Decimal("110"), Decimal("90"))


def test_a_gap_week_is_skipped_so_previous_means_previous_with_candles() -> None:
    """`_group_by_window` groups CONSECUTIVE runs: empty calendar weeks vanish.

    Two candles three weeks apart yield exactly two week windows, so the
    'previous week' is the one that actually had candles, not the empty one
    immediately before.
    """
    early = _at(0, datetime(2026, 3, 2, 0, 0, tzinfo=UTC), "100", "105", "95", "100")
    much_later = _at(
        1, datetime(2026, 3, 23, 0, 0, tzinfo=UTC), "100", "115", "85", "100"
    )
    got = detect_period_levels((early, much_later), _CONFIG)
    previous_week_high = _by_type(got, PoiType.PREVIOUS_WEEK_HIGH)
    assert len(previous_week_high) == 1
    assert previous_week_high[0].representative_price == Decimal("105")
    assert previous_week_high[0].period_start_time_utc == (
        datetime(2026, 3, 2, tzinfo=UTC)
    )
