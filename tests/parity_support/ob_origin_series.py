"""Synthetic candle series for the RC3 ORDER BLOCK movement-origin tests.

Test tooling only. Each series is built from explicit OHLC rows so the swing
structure is readable, then run through the REAL engine
(`analyze_market_measurements` -> `analyze_pois`) -- no model of the rule.
SELL cases are exact price mirrors of the BUY cases (p -> MIRROR - p with
high/low and open/close swapped), so both directions exercise identical
structure.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

from btmm_ai_scanner.config.enums import Timeframe
from btmm_ai_scanner.contracts.normalized_candle import NormalizedCandle
from btmm_ai_scanner.domain.analyzer import analyze_market_measurements
from btmm_ai_scanner.domain.configuration import MarketMeasurementConfiguration
from btmm_ai_scanner.historical_backtest.identity import (
    ContentAddressedIdentityProvider,
)
from btmm_ai_scanner.poi.analyzer import PoiAnalysis, PoiTimeframeInput, analyze_pois
from btmm_ai_scanner.poi.configuration import PoiConfiguration
from tests.parity_support.v1a_csv_loader import load_v1a_csv

__all__ = ["Row", "analyze_rows", "mirror", "rows_to_candles", "trend"]

Row = tuple[float, float, float, float]  # open, high, low, close
START = datetime(2026, 8, 10, 0, 0, tzinfo=UTC)
MIRROR = 400.0


def trend(start: float, step: float, count: int, wick: float = 0.3) -> list[Row]:
    """`count` candles each closing `step` from the previous close."""
    rows: list[Row] = []
    price = start
    for _ in range(count):
        o, c = price, price + step
        rows.append((o, max(o, c) + wick, min(o, c) - wick, c))
        price = c
    return rows


def mirror(rows: list[Row]) -> list[Row]:
    return [(MIRROR - o, MIRROR - lo, MIRROR - h, MIRROR - c) for o, h, lo, c in rows]


def rows_to_candles(
    rows: list[Row], tmp: Path, name: str
) -> tuple[NormalizedCandle, ...]:
    path = tmp / f"{name}.csv"
    lines = ["time,open,high,low,close,volume"]
    for i, (o, h, lo, c) in enumerate(rows):
        t = int((START + timedelta(minutes=15 * i)).timestamp() * 1000)
        lines.append(f"{t},{o:.2f},{h:.2f},{lo:.2f},{c:.2f},100")
    path.write_bytes("\n".join(lines).encode("utf-8"))
    return load_v1a_csv(path, Timeframe.M15)


def analyze_rows(
    rows: list[Row], tmp: Path, name: str
) -> tuple[PoiAnalysis, tuple[NormalizedCandle, ...], object]:
    candles = rows_to_candles(rows, tmp, name)
    identity = ContentAddressedIdentityProvider()
    measurement = analyze_market_measurements(
        candles,
        MarketMeasurementConfiguration(minimum_price_tick=Decimal("0.01")),
        identity,
    )
    pois = analyze_pois(
        (PoiTimeframeInput(Timeframe.M15, candles, measurement),),
        PoiConfiguration(minimum_price_tick=Decimal("0.01")),
        identity,
    )
    return pois, candles, measurement
