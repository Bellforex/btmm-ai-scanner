"""BTRC-T5 confluence + analytical-permission configuration.

Component weights and permission bands are ENGINEERING-PROVISIONAL research
baselines — NOT production-approved, never optimized against historical results
in this campaign, and centralized here (no scattered magic numbers). BTMM + POI
carry the largest weight (they are the strategy/context core; BTRC is supervisory
confluence).
"""

from __future__ import annotations

from collections.abc import Mapping
from types import MappingProxyType

from pydantic import Field

from btmm_ai_scanner.contracts.types import ContractModel

_DEFAULT_WEIGHTS: Mapping[str, int] = MappingProxyType(
    {
        "btmm": 3,
        "poi": 3,
        "trend": 2,
        "regime": 1,
        "momentum": 1,
        "breakout": 1,
        "liquidity": 1,
        "volatility": 1,
    }
)


class ConfluenceConfiguration(ContractModel):
    # Relative weights for the FINAL_CONFLUENCE_SCORE (research baseline).
    weights: dict[str, int] = Field(default_factory=lambda: dict(_DEFAULT_WEIGHTS))
    # FINAL_CONFLUENCE_SCORE at/above which an aligned context yields a bias.
    high_confluence_min: int = Field(default=65, ge=0, le=100)
    # Below this an aligned context is only WATCH_ONLY; far below -> NO_TRADE_CONTEXT.
    watch_only_min: int = Field(default=45, ge=0, le=100)
    # Volatility state that downgrades permission (never changes direction).
    downgrade_on_extreme_volatility: bool = True
