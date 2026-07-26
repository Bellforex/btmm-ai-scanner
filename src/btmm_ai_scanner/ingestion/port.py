from typing import Protocol

from btmm_ai_scanner.ingestion.requests import SourceAcquisitionRequest
from btmm_ai_scanner.ingestion.results import SourceAcquisitionResult


class MarketDataSourcePort(Protocol):
    def acquire(self, request: SourceAcquisitionRequest) -> SourceAcquisitionResult: ...
