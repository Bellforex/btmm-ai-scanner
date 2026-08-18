"""BTRC-T2 regime engine configuration.

ENGINEERING-PROVISIONAL, centralized, configurable, documented — never
production-approved. No polarity (bullish/bearish) lives here; regime is a
direction-independent behaviour dimension.
"""

from __future__ import annotations

from decimal import Decimal

from pydantic import Field

from btmm_ai_scanner.contracts.types import ContractModel


class RegimeEngineConfiguration(ContractModel):
    # Number of most-recent displacement observations considered "recent" when
    # deciding compression / breakout-pending / expansion during a forming state.
    recent_displacement_window: int = Field(default=3, ge=1)
    # range_speed_ratio at/above which a recent displacement counts as genuine
    # range EXPANSION (below it, displacement is "building" -> BREAKOUT_PENDING).
    expansion_speed_ratio: Decimal = Field(default=Decimal("1.50"), gt=Decimal("0"))
