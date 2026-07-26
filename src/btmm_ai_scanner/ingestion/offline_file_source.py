from collections.abc import Mapping
from types import MappingProxyType

from btmm_ai_scanner.ingestion.port import MarketDataSourcePort
from btmm_ai_scanner.ingestion.requests import SourceAcquisitionRequest
from btmm_ai_scanner.ingestion.results import (
    SourceAcquisitionOutcome,
    SourceAcquisitionResult,
)
from btmm_ai_scanner.market_data.source_input import SourceCandleInput


class OfflineFileSource(MarketDataSourcePort):
    def __init__(
        self,
        fixtures: Mapping[SourceAcquisitionRequest, tuple[SourceCandleInput, ...]],
    ) -> None:
        self._fixtures: Mapping[
            SourceAcquisitionRequest, tuple[SourceCandleInput, ...]
        ] = MappingProxyType(dict(fixtures))

    def acquire(self, request: SourceAcquisitionRequest) -> SourceAcquisitionResult:
        if request not in self._fixtures:
            return SourceAcquisitionResult(
                outcome=SourceAcquisitionOutcome.UNSUPPORTED,
                source_candle_inputs=(),
                reason_codes=("SOURCE_REQUEST_UNSUPPORTED",),
            )
        return SourceAcquisitionResult(
            outcome=SourceAcquisitionOutcome.SUCCEEDED,
            source_candle_inputs=self._fixtures[request],
            reason_codes=(),
        )
