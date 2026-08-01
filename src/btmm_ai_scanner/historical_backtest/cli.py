import argparse
from collections.abc import Sequence
from decimal import Decimal
from pathlib import Path

from btmm_ai_scanner.btmm.configuration import BtmmConfiguration
from btmm_ai_scanner.domain.configuration import MarketMeasurementConfiguration
from btmm_ai_scanner.historical_backtest.configuration import (
    HistoricalDatasetConfiguration,
)
from btmm_ai_scanner.historical_backtest.data_quality import ChecksumMismatchError
from btmm_ai_scanner.historical_backtest.execution import execute_scanner_backtest
from btmm_ai_scanner.historical_backtest.identity import (
    ContentAddressedIdentityProvider,
)
from btmm_ai_scanner.historical_backtest.loader import (
    DatasetManifestNotFoundError,
    load_historical_dataset,
)
from btmm_ai_scanner.historical_backtest.manifest import InvalidDatasetManifestError
from btmm_ai_scanner.historical_backtest.reporting import (
    HistoricalReportWriteError,
    write_backtest_report,
)
from btmm_ai_scanner.poi.configuration import PoiConfiguration
from btmm_ai_scanner.scanner.configuration import (
    ReplayConfiguration,
    ScannerConfiguration,
)
from btmm_ai_scanner.scanner.labels import InvalidReviewedLabelError
from btmm_ai_scanner.structure.configuration import StructureConfiguration

EXIT_SUCCESS = 0
EXIT_UNEXPECTED_FAILURE = 1
EXIT_USAGE_ERROR = 2
EXIT_DATASET_REJECTION = 3
EXIT_REPLAY_FAILURE = 4
EXIT_REVIEWED_CASE_FAILURE = 5
EXIT_REPORT_WRITE_FAILURE = 6

_MINIMUM_PRICE_TICK = Decimal("0.01")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="btmm_ai_scanner.historical_backtest")
    parser.add_argument("--dataset", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    return parser


def _default_scanner_configuration() -> ScannerConfiguration:
    return ScannerConfiguration(
        measurement_configuration=MarketMeasurementConfiguration(
            minimum_price_tick=_MINIMUM_PRICE_TICK
        ),
        structure_configuration=StructureConfiguration(),
        poi_configuration=PoiConfiguration(minimum_price_tick=_MINIMUM_PRICE_TICK),
        btmm_configuration=BtmmConfiguration(minimum_price_tick=_MINIMUM_PRICE_TICK),
    )


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)  # argparse itself exits 2 on a usage/parse error

    scanner_configuration = _default_scanner_configuration()
    replay_configuration = ReplayConfiguration()
    identity_provider = ContentAddressedIdentityProvider()

    try:
        dataset = load_historical_dataset(
            args.dataset, HistoricalDatasetConfiguration()
        )
    except (
        DatasetManifestNotFoundError,
        InvalidDatasetManifestError,
        ChecksumMismatchError,
    ):
        return EXIT_DATASET_REJECTION
    except Exception:
        return EXIT_UNEXPECTED_FAILURE

    try:
        result = execute_scanner_backtest(
            dataset, scanner_configuration, replay_configuration, identity_provider
        )
    except InvalidReviewedLabelError:
        return EXIT_REVIEWED_CASE_FAILURE
    except Exception:
        return EXIT_UNEXPECTED_FAILURE

    for replay_result in result.per_symbol_replay_results:
        if (
            not replay_result.direct_batch_verified
            or len(replay_result.detection_mismatches) > 0
        ):
            return EXIT_REPLAY_FAILURE

    try:
        write_backtest_report(result, args.output)
    except HistoricalReportWriteError:
        return EXIT_REPORT_WRITE_FAILURE
    except Exception:
        return EXIT_UNEXPECTED_FAILURE

    return EXIT_SUCCESS
