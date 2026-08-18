"""Forward (live) scanning runtime foundation (A7A).

Provider-neutral, credential-free core that drives the validated
``IncrementalReplayKernel`` from arriving CLOSED candles. The live FXCM
ForexConnect transport is an injected implementation behind
``ForwardCandleTransport`` and is deliberately NOT included here (it requires an
FXCM account + credentials); every component in this package is exercised by a
synthetic transport and never places orders. Scanner semantics are unchanged.
"""

from btmm_ai_scanner.forward.alerts import (
    AlertSink,
    CollectingAlertSink,
    JsonlAlertSink,
)
from btmm_ai_scanner.forward.candle_factory import (
    ForwardCandleRejection,
    build_forward_closed_candle,
)
from btmm_ai_scanner.forward.events import ScannerAlert, ScannerEventType
from btmm_ai_scanner.forward.journal import AcceptedCandleJournal
from btmm_ai_scanner.forward.runner import (
    ForwardIngestOutcome,
    ForwardIngestResult,
    ForwardScannerRunner,
)
from btmm_ai_scanner.forward.transport import (
    ForwardCandleTransport,
    ProviderCandle,
    SyntheticTransport,
)

__all__ = [
    "AcceptedCandleJournal",
    "AlertSink",
    "CollectingAlertSink",
    "ForwardCandleRejection",
    "ForwardCandleTransport",
    "ForwardIngestOutcome",
    "ForwardIngestResult",
    "ForwardScannerRunner",
    "JsonlAlertSink",
    "ProviderCandle",
    "ScannerAlert",
    "ScannerEventType",
    "SyntheticTransport",
    "build_forward_closed_candle",
]
