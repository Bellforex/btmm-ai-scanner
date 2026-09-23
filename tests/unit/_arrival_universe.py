"""The POI universe the ownership layer reasons over, built once."""

from __future__ import annotations

from btmm_ai_scanner.domain.swings import detect_confirmed_swings
from btmm_ai_scanner.poi.bases import detect_bases
from btmm_ai_scanner.poi.doji import detect_dojis
from btmm_ai_scanner.poi.engulfing import detect_engulfing
from btmm_ai_scanner.poi.pressure_wicks import detect_pressure_wicks
from btmm_ai_scanner.poi.single_candle_reversals import detect_single_candle_reversals
from btmm_ai_scanner.poi.three_candle_stars import detect_three_candle_stars


def poi_universe(candles, poi_config, measurement):
    """Bases plus every candle-pattern family the ownership layer can own.

    Doji detection receives the host's REAL confirmed swings; handing it an
    empty tuple silently produces no dojis and makes ownership assertions
    vacuous.
    """
    swings = tuple(detect_confirmed_swings(candles, measurement))
    return [
        *detect_bases(candles, poi_config),
        *detect_single_candle_reversals(candles, poi_config),
        *detect_pressure_wicks(candles, poi_config),
        *detect_engulfing(candles, poi_config),
        *detect_three_candle_stars(candles, poi_config),
        *detect_dojis(candles, poi_config, confirmed_swings=swings),
    ]
