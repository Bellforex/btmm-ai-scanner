"""BTMM partitions by the source POI's timeframe.

`analyze_btmm` takes `tuple[BtmmTimeframeInput, ...]`, which reads like a
multi-timeframe algorithm. It is not. Each BTMM setup observes only the data
belonging to its own POI's `source_timeframe`; the tuple is a batch container.
Production states the property itself, in `_combine_btmm_replay_states`:

    "Setups partition by their source POI's timeframe, so concatenating the
     per-timeframe states and re-sorting on analyze_btmm's own keys yields the
     identical combined result."

and relies on it for the incremental replay path.

This matters architecturally: it is what lets a Pine port run ONE current-chart
timeframe partition with no `request.security` and no cross-timeframe transport.
An earlier audit concluded the opposite, which would have had us build a
multi-timeframe substrate the source does not require. These tests exist so the
invariant fails loudly if production ever starts coupling timeframes.

The comparison is deliberately whole-record: every field of every observation,
transition and current state, not a hand-picked subset.
"""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any
from uuid import UUID

import pytest

from btmm_ai_scanner.btmm.analyzer import BtmmTimeframeInput, analyze_btmm
from btmm_ai_scanner.btmm.configuration import BtmmConfiguration
from btmm_ai_scanner.config.enums import InternalSymbol, Timeframe
from btmm_ai_scanner.contracts.normalized_candle import NormalizedCandle
from btmm_ai_scanner.contracts.provenance_record import EvidenceClassification
from btmm_ai_scanner.contracts.raw_candle import CandleCompleteness, CandleVolumeKind
from btmm_ai_scanner.contracts.types import SemVer
from btmm_ai_scanner.domain import MarketMeasurementAnalysis
from btmm_ai_scanner.domain.enums import DerivedOutputType
from btmm_ai_scanner.poi.analyzer import PoiAnalysis
from btmm_ai_scanner.poi.enums import PoiDirection, PoiFamily, PoiType
from btmm_ai_scanner.poi.observation import PoiObservation

_FP = "a" * 64
_PROV = UUID("0193f450-1234-7abc-8def-abcdefabcdff")
_RAW = UUID("0193f450-1234-7abc-8def-abcdefabcdaa")
_T0 = datetime(2026, 1, 1, tzinfo=UTC)
_MINUTES = {Timeframe.M1: 1, Timeframe.M5: 5, Timeframe.M15: 15}
_TFS = (Timeframe.M1, Timeframe.M5, Timeframe.M15)


class _ContentIdentity:
    """Content-addressed identity.

    The sequential provider used elsewhere numbers records in call order, so a
    combined run and three separate runs would disagree for a reason that has
    nothing to do with partitioning. Hashing the semantic key removes that
    confound and lets the test compare record_id like any other field.
    """

    def identify(
        self, *, output_type: DerivedOutputType, semantic_key: tuple[str, ...]
    ) -> UUID:
        raw = f"{output_type}|{'|'.join(str(part) for part in semantic_key)}"
        digest = hashlib.sha256(raw.encode()).hexdigest()
        return UUID(
            f"{digest[:8]}-{digest[8:12]}-7{digest[13:16]}"
            f"-8{digest[17:20]}-{digest[20:32]}"
        )


def _candle(timeframe: Timeframe, index: int, prices: tuple[str, str, str, str]) -> Any:
    step = timedelta(minutes=_MINUTES[timeframe])
    event = _T0 + step * index
    available = event + step
    open_, high, low, close = prices
    return NormalizedCandle.model_validate(
        {
            "record_id": UUID(
                f"0193f4{_MINUTES[timeframe]:02d}-1234-7abc-8def-{index:012x}"
            ),
            "content_fingerprint": _FP,
            "raw_candle_id": _RAW,
            "provider": "FXCM",
            "source_reference": f"fxcm-{timeframe.value}",
            "source_symbol": "XAUUSD",
            "source_timeframe": timeframe.value,
            "symbol": InternalSymbol.XAUUSD,
            "timeframe": timeframe,
            "event_time_utc": event,
            "availability_time_utc": available,
            "processing_time_utc": available,
            "original_event_time": event,
            "original_availability_time": available,
            "original_timezone": "UTC",
            "open": Decimal(open_),
            "high": Decimal(high),
            "low": Decimal(low),
            "close": Decimal(close),
            "volume": None,
            "volume_kind": CandleVolumeKind.UNKNOWN,
            "completeness": CandleCompleteness.CONFIRMED_COMPLETE,
            "rule_version": SemVer.parse("0.1.0"),
            "contract_version": SemVer.parse("0.1.0"),
            "schema_version": SemVer.parse("0.1.0"),
            "provenance_id": _PROV,
        }
    )


def _series(timeframe: Timeframe, count: int, seed: int) -> tuple[Any, ...]:
    out: list[Any] = []
    price = 100.0 + seed
    for index in range(count):
        price += 1.4 if (index + seed) % 3 == 0 else -0.9
        out.append(
            _candle(
                timeframe,
                index,
                (
                    f"{price:.2f}",
                    f"{price + 0.8:.2f}",
                    f"{price - 0.8:.2f}",
                    f"{price + 0.2:.2f}",
                ),
            )
        )
    return tuple(out)


def _measurement(timeframe: Timeframe, count: int) -> MarketMeasurementAnalysis:
    return MarketMeasurementAnalysis(
        symbol=InternalSymbol.XAUUSD,
        timeframe=timeframe,
        analyzed_candle_count=count,
        confirmed_swings=(),
        displacement_observations=(),
        equal_level_clusters=(),
        support_resistance_zones=(),
        trendlines=(),
    )


def _poi(timeframe: Timeframe, index: int, direction: PoiDirection) -> PoiObservation:
    moment = _T0 + timedelta(minutes=_MINUTES[timeframe]) * 5
    return PoiObservation(
        record_id=UUID(f"0193f4aa-{_MINUTES[timeframe]:04d}-7000-8000-{index:012x}"),
        content_fingerprint=_FP,
        symbol=InternalSymbol.XAUUSD,
        source_timeframe=timeframe,
        effective_timeframe=timeframe,
        family=PoiFamily.STRUCTURAL,
        poi_type=PoiType.SUPPORT_ZONE,
        direction=direction,
        zone_top=Decimal("101"),
        zone_bottom=Decimal("100"),
        representative_price=None,
        strength_tier=None,
        source_candle_record_ids=(),
        source_measurement_record_ids=(),
        merged_source_poi_record_ids=(),
        candidate_event_time_utc=moment,
        confirmation_time_utc=moment,
        availability_time_utc=moment,
        rule_version=SemVer.parse("0.1.0"),
        contract_version=SemVer.parse("0.1.0"),
        schema_version=SemVer.parse("0.1.0"),
        evidence_classification=EvidenceClassification.ENGINEERING_PROVISIONAL,
        provenance_id=_PROV,
    )


def _poi_analysis(
    pois: tuple[PoiObservation, ...], candles: dict[Timeframe, tuple[Any, ...]]
) -> PoiAnalysis:
    timeframes = tuple(
        sorted({p.source_timeframe for p in pois}, key=lambda tf: _MINUTES[tf])
    )
    return PoiAnalysis(
        symbol=InternalSymbol.XAUUSD,
        analyzed_timeframes=timeframes,
        analyzed_candle_count_by_timeframe=tuple(len(candles[tf]) for tf in timeframes),
        poi_observations=pois,
        poi_lifecycle_transitions=(),
        poi_overlap_relationships=(),
        current_poi_states=(),
    )


def _dump(records: Any) -> list[tuple[tuple[str, str], ...]]:
    """Whole-record comparison: every field, stringified, order-insensitive."""
    return sorted(
        tuple(sorted((k, str(v)) for k, v in r.model_dump(mode="json").items()))
        for r in records
    )


def _scenario(
    seed: int, pois_per_tf: int = 2
) -> tuple[Any, list[Any], list[Any], list[Any]]:
    candles = {tf: _series(tf, 40, seed) for tf in _TFS}
    pois = {
        tf: tuple(
            _poi(
                tf,
                k,
                PoiDirection.BULLISH if (k + seed) % 2 == 0 else PoiDirection.BEARISH,
            )
            for k in range(pois_per_tf)
        )
        for tf in _TFS
    }
    config = BtmmConfiguration(minimum_price_tick=Decimal("0.01"))

    def bundle(tf: Timeframe) -> BtmmTimeframeInput:
        return BtmmTimeframeInput(
            timeframe=tf,
            candles=candles[tf],
            measurement_analysis=_measurement(tf, len(candles[tf])),
        )

    every_poi = tuple(p for tf in _TFS for p in pois[tf])
    combined = analyze_btmm(
        tuple(bundle(tf) for tf in _TFS),
        _poi_analysis(every_poi, candles),
        (),
        config,
        _ContentIdentity(),
    )

    observations: list[Any] = []
    transitions: list[Any] = []
    states: list[Any] = []
    for tf in _TFS:
        part = analyze_btmm(
            (bundle(tf),),
            _poi_analysis(pois[tf], candles),
            (),
            config,
            _ContentIdentity(),
        )
        observations += list(part.btmm_observations)
        transitions += list(part.btmm_lifecycle_transitions)
        states += list(part.current_btmm_states)
    return combined, observations, transitions, states


@pytest.mark.parametrize("seed", range(6))
def test_combined_equals_union_of_independent_partitions(seed: int) -> None:
    combined, observations, transitions, states = _scenario(seed)

    assert _dump(combined.btmm_observations) == _dump(observations)
    assert _dump(combined.btmm_lifecycle_transitions) == _dump(transitions)
    assert _dump(combined.current_btmm_states) == _dump(states)


def test_the_scenario_actually_produces_state_to_compare() -> None:
    """Guard the guard: an empty comparison would pass vacuously."""
    combined, _observations, _transitions, _states = _scenario(0)
    assert len(combined.btmm_observations) == 6
    assert len(combined.btmm_lifecycle_transitions) > 0
    assert len(combined.current_btmm_states) == 6


def test_every_setup_carries_its_own_source_timeframe() -> None:
    combined, _observations, _transitions, _states = _scenario(1)
    by_timeframe = {tf: 0 for tf in _TFS}
    for observation in combined.btmm_observations:
        by_timeframe[observation.source_timeframe] += 1
    assert by_timeframe == {Timeframe.M1: 2, Timeframe.M5: 2, Timeframe.M15: 2}


@pytest.mark.parametrize("timeframe", _TFS)
def test_a_single_bundle_is_a_valid_call(timeframe: Timeframe) -> None:
    """A one-timeframe call is a supported production configuration: it is what
    the scanner issues when the caller supplies only that timeframe, and it is
    the oracle a single-chart Pine port must reproduce."""
    candles = {tf: _series(tf, 40, 0) for tf in _TFS}
    pois = (_poi(timeframe, 0, PoiDirection.BULLISH),)
    result = analyze_btmm(
        (
            BtmmTimeframeInput(
                timeframe=timeframe,
                candles=candles[timeframe],
                measurement_analysis=_measurement(timeframe, len(candles[timeframe])),
            ),
        ),
        _poi_analysis(pois, candles),
        (),
        BtmmConfiguration(minimum_price_tick=Decimal("0.01")),
        _ContentIdentity(),
    )
    assert len(result.btmm_observations) == 1
    assert result.btmm_observations[0].source_timeframe is timeframe


def test_formation_role_is_a_local_property_of_the_bundle() -> None:
    """M5 and M15 are formation timeframes and M1 is supporting-only, and that is
    decided per POI from its own timeframe -- not by whether a sibling timeframe
    was supplied alongside it."""
    config = BtmmConfiguration(minimum_price_tick=Decimal("0.01"))
    assert Timeframe.M5 in config.formation_timeframes
    assert Timeframe.M15 in config.formation_timeframes
    assert Timeframe.M1 in config.supporting_only_timeframes
    assert config.formation_timeframes.isdisjoint(config.supporting_only_timeframes)
