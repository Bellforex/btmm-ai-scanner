"""BTRC-T4 volatility + session configuration.

ENGINEERING-PROVISIONAL, centralized, documented — never production-approved.
Volatility reuses the existing ATR / candle-range implementation. Session windows
are expressed in EXCHANGE-LOCAL time and resolved through ``zoneinfo`` so DST is
handled correctly for every date (never a hardcoded year-round UTC offset).
"""

from __future__ import annotations

from decimal import Decimal

from pydantic import Field

from btmm_ai_scanner.contracts.types import ContractModel

_HourMinute = tuple[int, int]


class VolatilitySessionConfiguration(ContractModel):
    # --- volatility ---
    atr_period: int = Field(default=14, ge=2)
    # Trailing candle-range window used for the percentile distribution.
    volatility_window: int = Field(default=50, ge=5)
    # Percentile band edges (fraction 0-1) mapping to VolatilityState.
    percentile_very_low_max: Decimal = Field(default=Decimal("0.10"))
    percentile_low_max: Decimal = Field(default=Decimal("0.30"))
    percentile_normal_max: Decimal = Field(default=Decimal("0.70"))
    percentile_high_max: Decimal = Field(default=Decimal("0.90"))
    # current range >= this multiple of the rolling median -> ABNORMAL_VOLATILITY_SPIKE
    abnormal_spike_multiplier: Decimal = Field(default=Decimal("2.5"), gt=Decimal("0"))

    # --- session (exchange-local windows; DST resolved via zoneinfo) ---
    london_timezone: str = "Europe/London"
    new_york_timezone: str = "America/New_York"
    london_preopen_start: _HourMinute = (7, 0)
    london_open: _HourMinute = (8, 0)
    london_close: _HourMinute = (16, 30)
    new_york_preopen_start: _HourMinute = (7, 0)
    new_york_open: _HourMinute = (8, 0)
    new_york_close: _HourMinute = (17, 0)
    # Asian session as a UTC window (Tokyo does not observe DST).
    asian_start_hour_utc: int = Field(default=22, ge=0, le=23)
    asian_end_hour_utc: int = Field(default=6, ge=0, le=23)
