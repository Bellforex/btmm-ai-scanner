"""RC5 DOJI: geometry, structural direction, and prefix immutability.

The subtle part is not the detector. It is that "this candle is a pivot of a
confirmed swing" is **not monotone** -- swing supersession can withdraw it --
so a Doji valid at an earlier causal prefix can vanish from the final swing
set. The append-only frontier remembers it; a batch run reading only the final
swings does not. That asymmetry is exactly what ORDER BLOCKS already solve by
prefix replay, and these tests pin the same behaviour for DOJI.
"""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pytest

from btmm_ai_scanner.config.enums import Timeframe
from btmm_ai_scanner.domain.analyzer import analyze_market_measurements
from btmm_ai_scanner.domain.configuration import MarketMeasurementConfiguration
from btmm_ai_scanner.historical_backtest.identity import (
    ContentAddressedIdentityProvider,
)
from btmm_ai_scanner.measurements.candle_metrics import body_efficiency
from btmm_ai_scanner.poi.authority import REVERSAL_LADDER, arbitrate_cluster
from btmm_ai_scanner.poi.configuration import PoiConfiguration
from btmm_ai_scanner.poi.detector_frontier import DOJI_RING_SIZE
from btmm_ai_scanner.poi.doji import detect_dojis, prefix_pivot_sides
from btmm_ai_scanner.poi.enums import PoiDirection, PoiStrengthTier, PoiType
from btmm_ai_scanner.scanner.analyzer import scan_market
from btmm_ai_scanner.scanner.replay import IncrementalReplayKernel
from btmm_ai_scanner.scanner.timeframe_input import ScannerTimeframeInput
from tests.parity_support.level_a_replay import build_scanner_configuration
from tests.parity_support.ob_origin_series import mirror, rows_to_candles
from tests.unit.test_rc3_order_block_leg_origin import _continuation, _reversal

_TICK = Decimal("0.01")
_RC4 = PoiConfiguration(minimum_price_tick=_TICK)
_RC5 = PoiConfiguration(minimum_price_tick=_TICK, rc5_structural_origin=True)
_MEASUREMENT = MarketMeasurementConfiguration(minimum_price_tick=_TICK)

_SERIES = {
    "continuation": _continuation,
    "continuation_sell": lambda: mirror(_continuation()),
    "reversal": _reversal,
    "reversal_sell": lambda: mirror(_reversal()),
}


@pytest.fixture(params=sorted(_SERIES), ids=sorted(_SERIES))
def candles(request: pytest.FixtureRequest, tmp_path: Path):
    return rows_to_candles(_SERIES[request.param](), tmp_path, request.param)


def _sides(candles):
    return prefix_pivot_sides(candles, _MEASUREMENT, ring_size=DOJI_RING_SIZE)


def _configuration(*, rc5: bool):
    base = build_scanner_configuration(
        required_timeframes=frozenset({Timeframe.M15}),
        optional_timeframes=frozenset(),
        minimum_price_tick=_TICK,
    )
    return base.model_copy(
        update={
            "poi_configuration": PoiConfiguration(
                minimum_price_tick=_TICK, rc5_structural_origin=rc5
            )
        }
    )


# ---------------------------------------------------------------------------
# geometry and thresholds
# ---------------------------------------------------------------------------


def test_every_doji_respects_the_frozen_thresholds(candles) -> None:
    by_id = {c.record_id: c for c in candles}
    for doji in detect_dojis(candles, _RC5, pivot_sides=_sides(candles)):
        candle = by_id[doji.source_candle_record_ids[0]]
        efficiency = body_efficiency(candle)
        assert efficiency <= _RC5.doji_body_efficiency_standard
        if doji.strength_tier is PoiStrengthTier.STRONG:
            assert efficiency <= _RC5.doji_body_efficiency_strong


def test_the_zone_is_the_defended_wick(candles) -> None:
    """Same convention as HAMMER / SHOOTING_STAR / the pressure wicks -- no
    padding, no buffer, no Doji-only geometry."""
    by_id = {c.record_id: c for c in candles}
    for doji in detect_dojis(candles, _RC5, pivot_sides=_sides(candles)):
        candle = by_id[doji.source_candle_record_ids[0]]
        if doji.direction is PoiDirection.BULLISH:
            assert doji.zone_top == min(candle.open, candle.close)
            assert doji.zone_bottom == candle.low
        else:
            assert doji.zone_top == candle.high
            assert doji.zone_bottom == max(candle.open, candle.close)
        assert doji.zone_top > doji.zone_bottom


def test_source_time_is_the_doji_candle_itself(candles) -> None:
    by_id = {c.record_id: c for c in candles}
    for doji in detect_dojis(candles, _RC5, pivot_sides=_sides(candles)):
        candle = by_id[doji.source_candle_record_ids[0]]
        assert doji.candidate_event_time_utc == candle.event_time_utc
        assert doji.availability_time_utc == candle.availability_time_utc


# ---------------------------------------------------------------------------
# identity: exactly one Doji per candle
# ---------------------------------------------------------------------------


def test_one_doji_per_candle_so_formation_keys_stay_unique(candles) -> None:
    """``_formation_key`` is ``(poi_type, source_candle_record_ids)``. Emitting
    both directions for one candle would give two candidates the SAME identity
    and the second would silently overwrite the first."""
    dojis = detect_dojis(candles, _RC5, pivot_sides=_sides(candles))
    keys = [(d.poi_type, d.source_candle_record_ids) for d in dojis]
    assert len(keys) == len(set(keys))


def test_direction_is_never_taken_from_candle_colour(candles) -> None:
    """A doji has almost no body, so open-vs-close carries no information about
    which side was defended. Direction must track the structural side."""
    sides = _sides(candles)
    for doji in detect_dojis(candles, _RC5, pivot_sides=sides):
        assert doji.direction is sides[doji.source_candle_record_ids[0]]


def test_a_candle_that_is_never_a_pivot_is_not_promoted(candles) -> None:
    dojis = detect_dojis(candles, _RC5, pivot_sides={})
    assert dojis == ()


# ---------------------------------------------------------------------------
# prefix immutability -- the supersession case
# ---------------------------------------------------------------------------


def test_pivot_sides_are_decided_once_and_never_revised(candles) -> None:
    """The map answers "WAS this a valid pivot when it qualified?", so growing
    the series may add entries but must never change one."""
    full = _sides(candles)
    for fraction in (2, 3, 4):
        upto = len(candles) * (fraction - 1) // fraction
        if upto < 30:
            continue
        earlier = prefix_pivot_sides(
            candles[:upto], _MEASUREMENT, ring_size=DOJI_RING_SIZE
        )
        for candle_id, side in earlier.items():
            assert full.get(candle_id) is side, candle_id


def test_a_doji_valid_at_an_earlier_prefix_survives_into_the_full_series(
    candles,
) -> None:
    """Supersession must not delete history. Anything the prefix produced has
    to still be produced by the full-series run."""
    full = {
        (d.poi_type, d.source_candle_record_ids)
        for d in detect_dojis(candles, _RC5, pivot_sides=_sides(candles))
    }
    for fraction in (2, 3):
        upto = len(candles) * (fraction - 1) // fraction
        if upto < 30:
            continue
        earlier = detect_dojis(
            candles[:upto],
            _RC5,
            pivot_sides=prefix_pivot_sides(
                candles[:upto], _MEASUREMENT, ring_size=DOJI_RING_SIZE
            ),
        )
        for doji in earlier:
            assert (doji.poi_type, doji.source_candle_record_ids) in full


def test_batch_and_incremental_agree_with_doji_enabled(candles) -> None:
    configuration = _configuration(rc5=True)
    batch = scan_market(
        (ScannerTimeframeInput(Timeframe.M15, candles),),
        (),
        configuration,
        ContentAddressedIdentityProvider(),
    ).poi_analysis
    kernel = IncrementalReplayKernel(
        (Timeframe.M15,), configuration, ContentAddressedIdentityProvider(), ()
    )
    for candle in candles:
        kernel.advance_group({Timeframe.M15: (candle,)})
    incremental = kernel.finalize().poi_analysis
    assert batch.poi_observations == incremental.poi_observations
    assert batch.current_poi_states == incremental.current_poi_states


# ---------------------------------------------------------------------------
# RC4 is untouched
# ---------------------------------------------------------------------------


def test_rc4_never_sees_a_doji(candles) -> None:
    analysis = scan_market(
        (ScannerTimeframeInput(Timeframe.M15, candles),),
        (),
        _configuration(rc5=False),
        ContentAddressedIdentityProvider(),
    ).poi_analysis
    assert not [o for o in analysis.poi_observations if o.poi_type is PoiType.DOJI]


def test_the_doji_detector_alone_produces_nothing_without_structure(
    candles,
) -> None:
    identity = ContentAddressedIdentityProvider()
    measurement = analyze_market_measurements(candles, _MEASUREMENT, identity)
    # the RC4 signature path -- raw swings, no prefix map
    assert isinstance(detect_dojis(candles, _RC4, measurement.confirmed_swings), tuple)


# ---------------------------------------------------------------------------
# authority ladder
# ---------------------------------------------------------------------------


def test_doji_sits_at_rank_six() -> None:
    assert REVERSAL_LADDER[PoiType.DOJI] == 6


@pytest.mark.parametrize(
    ("other", "winner"),
    [
        (PoiType.BEARISH_PRESSURE_WICK, PoiType.DOJI),
        (PoiType.SHOOTING_STAR, PoiType.SHOOTING_STAR),
        (PoiType.BEARISH_ENGULFING, PoiType.BEARISH_ENGULFING),
        (PoiType.EVENING_STAR, PoiType.EVENING_STAR),
        (PoiType.BUY_TO_SELL_CANDLE, PoiType.BUY_TO_SELL_CANDLE),
    ],
)
def test_doji_authority_pairings(other: PoiType, winner: PoiType) -> None:
    from tests.unit.test_rc5_poi_authority import CLUSTER, _by_type, _c

    doji = _c(PoiType.DOJI, "4470.00", "4480.00")
    rival = _c(other, "4465.00", "4485.00", minutes=45)
    got = _by_type(arbitrate_cluster([doji, rival], CLUSTER))
    from btmm_ai_scanner.poi.authority import AuthorityReason

    assert got[winner] is AuthorityReason.PRIMARY


def test_a_doji_and_an_independent_fvg_both_survive() -> None:
    from btmm_ai_scanner.poi.authority import AuthorityReason
    from tests.unit.test_rc5_poi_authority import CLUSTER, _by_type, _c

    doji = _c(PoiType.DOJI, "4470.00", "4480.00")
    fvg = _c(PoiType.SELL_FAIR_VALUE_GAP, "4400.00", "4450.00", minutes=45)
    got = _by_type(arbitrate_cluster([doji, fvg], CLUSTER))
    assert got[PoiType.DOJI] is AuthorityReason.PRIMARY
    assert got[PoiType.SELL_FAIR_VALUE_GAP] is AuthorityReason.INDEPENDENT
