"""RC4 market framework: range, liquidity / sweep, BTMM pre-trade cycle, location.

Author decisions 2026-09-19 (RC4 only; RC3 at 3f9f790 is untouched). Every
function is causal: it reads only candles, swings, clusters, trendlines and
structure transitions already available at the evaluation bar.
"""

from btmm_ai_scanner.framework.engine import (
    FrameworkBarContext,
    FrameworkTracker,
    build_framework_bar_context,
    evaluate_poi_framework,
    framework_context_for,
)
from btmm_ai_scanner.framework.model import (
    BtmmPretradeReason,
    FibBucket,
    FrameworkConfiguration,
    FrameworkKind,
    InteractionEpisode,
    LiquidityKind,
    LiquidityScope,
    LiquiditySide,
    PoiFrameworkAssessment,
    RangePosition,
    RangeState,
    SweepEvent,
    SweepType,
    TradingRange,
)

__all__ = [
    "BtmmPretradeReason",
    "FibBucket",
    "FrameworkBarContext",
    "FrameworkConfiguration",
    "FrameworkKind",
    "FrameworkTracker",
    "InteractionEpisode",
    "LiquidityKind",
    "LiquidityScope",
    "LiquiditySide",
    "PoiFrameworkAssessment",
    "RangePosition",
    "RangeState",
    "SweepEvent",
    "SweepType",
    "TradingRange",
    "build_framework_bar_context",
    "evaluate_poi_framework",
    "framework_context_for",
]
