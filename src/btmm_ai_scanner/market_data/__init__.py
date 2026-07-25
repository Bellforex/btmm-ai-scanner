"""Market-data pipeline foundation: SourceCandleInput through NormalizedCandle."""

from btmm_ai_scanner.market_data.gap_observation import (
    GapClassification,
    GapObservation,
    observe_potential_gap,
)
from btmm_ai_scanner.market_data.idempotency import evaluate_idempotency
from btmm_ai_scanner.market_data.normalization import normalize_raw_candle
from btmm_ai_scanner.market_data.ports import (
    CandleReadRepository,
    HistoricalReplaySource,
    NormalizedCandleSink,
    RawCandleSink,
)
from btmm_ai_scanner.market_data.raw_candle_builder import (
    build_historical_raw_candle,
    build_live_raw_candle,
)
from btmm_ai_scanner.market_data.results import IngestionOutcome, IngestionResult
from btmm_ai_scanner.market_data.source_input import SourceCandleInput
from btmm_ai_scanner.market_data.source_mapping import (
    FXCM_PROVIDER,
    UnsupportedProviderError,
    UnsupportedProviderSymbolError,
    UnsupportedProviderTimeframeError,
    resolve_internal_symbol,
    resolve_timeframe,
)

__all__ = [  # noqa: RUF022 -- order is an approved contract, not alphabetical
    "SourceCandleInput",
    "IngestionOutcome",
    "IngestionResult",
    "FXCM_PROVIDER",
    "UnsupportedProviderError",
    "UnsupportedProviderSymbolError",
    "UnsupportedProviderTimeframeError",
    "resolve_internal_symbol",
    "resolve_timeframe",
    "build_historical_raw_candle",
    "build_live_raw_candle",
    "normalize_raw_candle",
    "evaluate_idempotency",
    "GapClassification",
    "GapObservation",
    "observe_potential_gap",
    "RawCandleSink",
    "NormalizedCandleSink",
    "CandleReadRepository",
    "HistoricalReplaySource",
]
