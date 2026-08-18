"""BTRC-T1 trend engine configuration.

All values are ENGINEERING-PROVISIONAL persistence/agreement counts — NOT
production-approved. They are centralized here (never scattered) so T9 can sweep
neighbouring values for stability. No thresholds are derived from oscillators;
market structure is primary.
"""

from __future__ import annotations

from pydantic import Field

from btmm_ai_scanner.contracts.types import ContractModel


class TrendEngineConfiguration(ContractModel):
    # Minimum confirmed swings on a timeframe before any directional assessment
    # is attempted (below this the timeframe reports UNKNOWN).
    min_swings_for_assessment: int = Field(default=2, ge=1)
    # Same-direction continuation-BOS streak required to call a timeframe
    # TRENDING (>=1 confirmed continuation beyond the initiating CHOCH).
    trend_min_streak: int = Field(default=1, ge=1)
    # Same-direction continuation-BOS streak required for STRONG_* (per timeframe)
    # and, combined with higher-timeframe agreement, for a STRONG global result.
    strong_streak: int = Field(default=3, ge=1)
    # Window (most-recent transitions) inspected for whipsaw/range detection.
    range_window: int = Field(default=4, ge=2)
    # Number of change-of-character (CHOCH) events within ``range_window`` that
    # classifies structural behaviour as RANGE (alternating, non-persistent).
    range_choch_count: int = Field(default=3, ge=2)
