"""BTRC-T3 momentum / breakout / pullback configuration.

All values ENGINEERING-PROVISIONAL, centralized, configurable, documented — never
production-approved. Momentum/breakout consume existing displacement + structure
evidence; pullback consumes swings + POI lifecycle. No RSI/MACD/ADX, no volume
dependency.
"""

from __future__ import annotations

from decimal import Decimal

from pydantic import Field

from btmm_ai_scanner.contracts.types import ContractModel


class MomentumBreakoutPullbackConfiguration(ContractModel):
    # --- momentum ---
    # Most-recent displacement observations forming the momentum window.
    momentum_window: int = Field(default=3, ge=1)
    # Same-direction displacement count that (alone) justifies STRONG momentum.
    momentum_strong_count: int = Field(default=2, ge=1)
    # Relative change in mean range_speed_ratio (recent half vs earlier half)
    # beyond which momentum is ACCELERATING / DECELERATING (else STEADY).
    momentum_acceleration_margin: Decimal = Field(
        default=Decimal("0.15"), ge=Decimal("0")
    )
    # range_speed_ratio scale used for the provisional 0-100 momentum score.
    momentum_score_reference_ratio: Decimal = Field(
        default=Decimal("2.00"), gt=Decimal("0")
    )

    # --- breakout ---
    # A recent equal-level sweep strictly later than the last structural break is
    # classified LIQUIDITY_SWEEP (liquidity taken without a new confirmed break).
    # (no numeric threshold — purely a causal ordering rule)

    # --- pullback ---
    # Retracement depth bands (fraction of the impulse leg). Structure remains
    # authoritative: exceeding the impulse origin OR a POI genuine invalidation is
    # STRUCTURAL_FAILURE regardless of these bands.
    pullback_shallow_max: Decimal = Field(default=Decimal("0.382"), gt=Decimal("0"))
    pullback_deep_min: Decimal = Field(default=Decimal("0.618"), gt=Decimal("0"))
