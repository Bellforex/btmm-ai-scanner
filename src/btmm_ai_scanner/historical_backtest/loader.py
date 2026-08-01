import hashlib
from decimal import Decimal
from itertools import pairwise
from pathlib import Path, PurePosixPath

from btmm_ai_scanner.btmm.configuration import BtmmConfiguration
from btmm_ai_scanner.config.enums import InternalSymbol, Timeframe
from btmm_ai_scanner.contracts.normalized_candle import NormalizedCandle
from btmm_ai_scanner.contracts.raw_candle import CandleCompleteness, CandleVolumeKind
from btmm_ai_scanner.contracts.types import ContractModel, SemVer, SHA256Fingerprint
from btmm_ai_scanner.domain.configuration import MarketMeasurementConfiguration
from btmm_ai_scanner.historical_backtest.configuration import (
    HistoricalDatasetConfiguration,
)
from btmm_ai_scanner.historical_backtest.csv_parser import (
    FileRejected,
    ParsedCandleRecord,
    parse_candle_rows,
)
from btmm_ai_scanner.historical_backtest.data_quality import (
    ChecksumMismatchError,
    DataQualityIssue,
    GapRecord,
    HistoricalDataQualityReport,
    TimeframeCoverage,
    detect_gap,
    warm_up_floor_bars,
)
from btmm_ai_scanner.historical_backtest.enums import DataQualityClassification
from btmm_ai_scanner.historical_backtest.identity import (
    CandleIdentityCollisionTracker,
    derive_normalized_record_id,
)
from btmm_ai_scanner.historical_backtest.manifest import (
    DatasetManifest,
    HistoricalFileEntry,
    InvalidDatasetManifestError,
    validate_dataset_manifest,
    validate_relative_path_syntax,
)
from btmm_ai_scanner.market_data.normalization import normalize_raw_candle
from btmm_ai_scanner.market_data.raw_candle_builder import build_historical_raw_candle
from btmm_ai_scanner.market_data.results import IngestionOutcome
from btmm_ai_scanner.market_data.source_input import SourceCandleInput
from btmm_ai_scanner.poi.configuration import PoiConfiguration
from btmm_ai_scanner.scanner.labels import (
    ReviewedScannerCase,
    validate_reviewed_scanner_case,
)
from btmm_ai_scanner.scanner.timeframe_input import ScannerTimeframeInput

_TIMEFRAME_RANK: dict[Timeframe, int] = {
    Timeframe.M1: 1,
    Timeframe.M5: 2,
    Timeframe.M15: 3,
    Timeframe.H1: 4,
    Timeframe.H3: 5,
    Timeframe.H4: 6,
    Timeframe.D1: 7,
    Timeframe.W1: 8,
}

_SYMBOL_ORDER: dict[InternalSymbol, int] = {
    InternalSymbol.XAUUSD: 1,
    InternalSymbol.EURUSD: 2,
    InternalSymbol.GBPUSD: 3,
}


class DatasetManifestNotFoundError(ValueError):
    pass


class ReviewedCaseDocument(ContractModel):
    schema_version: SemVer
    dataset_id: str
    cases: tuple[ReviewedScannerCase, ...]


class LoadedHistoricalDataset(ContractModel):
    manifest: DatasetManifest
    timeframe_inputs_by_symbol: tuple[
        tuple[InternalSymbol, tuple[ScannerTimeframeInput, ...]], ...
    ]
    reviewed_cases: tuple[ReviewedScannerCase, ...]
    data_quality_report: HistoricalDataQualityReport
    file_checksums: tuple[tuple[str, SHA256Fingerprint], ...]


def _resolve_and_validate_path(dataset_root_resolved: Path, relative_path: str) -> Path:
    candidate = dataset_root_resolved
    for part in PurePosixPath(relative_path).parts:
        candidate = candidate / part
        if candidate.is_symlink():
            raise InvalidDatasetManifestError(
                f"symlink descendant is not permitted: {relative_path!r}."
            )
    if not candidate.exists():
        raise InvalidDatasetManifestError(
            f"declared file does not exist on disk: {relative_path!r}."
        )
    resolved = candidate.resolve(strict=True)
    if not resolved.is_relative_to(dataset_root_resolved):
        raise InvalidDatasetManifestError(
            f"resolved path escapes the dataset root: {relative_path!r}."
        )
    if not resolved.is_file():
        raise InvalidDatasetManifestError(
            f"declared path is not a regular file: {relative_path!r}."
        )
    return resolved


def _verify_checksum(
    resolved_path: Path, expected_sha256: str, *, relative_path: str
) -> bytes:
    raw_bytes = resolved_path.read_bytes()
    actual = hashlib.sha256(raw_bytes).hexdigest()
    if actual != expected_sha256:
        raise ChecksumMismatchError(
            f"checksum mismatch for {relative_path!r}: expected {expected_sha256},"
            f" got {actual}."
        )
    return raw_bytes


def _record_to_normalized_candle(
    record: ParsedCandleRecord, *, entry: HistoricalFileEntry, manifest: DatasetManifest
) -> NormalizedCandle:
    volume_kind = (
        manifest.volume_convention
        if record.volume is not None
        else CandleVolumeKind.UNKNOWN
    )

    source_input = SourceCandleInput(
        record_id=record.record_id,
        content_fingerprint=record.content_fingerprint,
        provider=manifest.provider,
        source_reference=record.source_record_id,
        source_symbol=record.symbol.value,
        source_timeframe=record.timeframe.value,
        event_time_utc=record.event_time_utc,
        availability_time_utc=record.availability_time_utc,
        processing_time_utc=record.availability_time_utc,
        original_event_time=record.original_event_time,
        original_availability_time=record.original_availability_time,
        original_timezone=entry.timezone,
        open=record.open_price,
        high=record.high_price,
        low=record.low_price,
        close=record.close_price,
        volume=record.volume,
        volume_kind=volume_kind,
        completeness=record.completeness,
        rule_version=manifest.schema_version,
        contract_version=manifest.schema_version,
        schema_version=manifest.schema_version,
        provenance_id=record.provenance_id,
    )

    raw_result = build_historical_raw_candle(source_input)
    if raw_result.outcome != IngestionOutcome.ACCEPTED:
        raise InvalidDatasetManifestError(
            f"historical raw-candle construction rejected a record for"
            f" {entry.relative_path!r}: {raw_result.reason_codes}."
        )
    assert raw_result.candidate_raw_candle is not None

    normalized_record_id, _ = derive_normalized_record_id(record.record_id)
    normalize_result = normalize_raw_candle(
        raw_result.candidate_raw_candle,
        normalized_record_id=normalized_record_id,
        normalized_content_fingerprint=record.content_fingerprint,
        normalized_rule_version=manifest.schema_version,
        normalized_contract_version=manifest.schema_version,
        normalized_schema_version=manifest.schema_version,
        normalized_provenance_id=record.provenance_id,
    )
    if normalize_result.outcome != IngestionOutcome.ACCEPTED:
        raise InvalidDatasetManifestError(
            f"normalization rejected a record for {entry.relative_path!r}:"
            f" {normalize_result.reason_codes}."
        )
    assert normalize_result.candidate_normalized_candle is not None
    return normalize_result.candidate_normalized_candle


def load_historical_dataset(
    dataset_path: Path,
    configuration: HistoricalDatasetConfiguration,
) -> LoadedHistoricalDataset:
    dataset_root_resolved = dataset_path.resolve(strict=True)
    manifest_path = dataset_root_resolved / "manifest.json"
    if not manifest_path.is_file():
        raise DatasetManifestNotFoundError(
            f"no manifest.json found at {dataset_root_resolved}."
        )

    manifest = DatasetManifest.model_validate_json(manifest_path.read_bytes())
    validate_dataset_manifest(manifest)

    issues: list[DataQualityIssue] = []
    gaps: list[GapRecord] = []
    blank_rows_skipped = 0
    unsorted_rows_resorted = 0
    duplicate_rows_rejected = 0
    checksum_mismatched_files: list[str] = []
    file_checksums: list[tuple[str, str]] = []
    checksum_verified = True

    identity_tracker = CandleIdentityCollisionTracker()
    candles_by_symbol_timeframe: dict[
        tuple[InternalSymbol, Timeframe], list[NormalizedCandle]
    ] = {}
    seen_resolved_targets: set[Path] = set()

    for entry in manifest.file_entries:
        resolved_path = _resolve_and_validate_path(
            dataset_root_resolved, entry.relative_path
        )
        if resolved_path in seen_resolved_targets:
            raise InvalidDatasetManifestError(
                f"duplicate resolved file target: {entry.relative_path!r}."
            )
        seen_resolved_targets.add(resolved_path)

        try:
            raw_bytes = _verify_checksum(
                resolved_path, entry.sha256, relative_path=entry.relative_path
            )
        except ChecksumMismatchError:
            checksum_verified = False
            checksum_mismatched_files.append(entry.relative_path)
            raise

        file_checksums.append((entry.relative_path, entry.sha256))

        try:
            decoded_text = raw_bytes.decode("utf-8-sig")
        except UnicodeDecodeError:
            issues.append(
                DataQualityIssue(
                    relative_path=entry.relative_path,
                    row_number=None,
                    symbol=entry.symbol,
                    timeframe=entry.timeframe,
                    reason_code="UNSUPPORTED_ENCODING",
                    classification=DataQualityClassification.REJECT_FILE,
                )
            )
            continue

        try:
            parsed = parse_candle_rows(
                decoded_text=decoded_text,
                entry=entry,
                manifest=manifest,
                identity_tracker=identity_tracker,
            )
        except FileRejected as rejected:
            issues.append(
                DataQualityIssue(
                    relative_path=entry.relative_path,
                    row_number=None,
                    symbol=entry.symbol,
                    timeframe=entry.timeframe,
                    reason_code=rejected.reason_code,
                    classification=DataQualityClassification.REJECT_FILE,
                )
            )
            continue

        issues.extend(parsed.issues)
        blank_rows_skipped += parsed.blank_rows_skipped
        unsorted_rows_resorted += parsed.unsorted_rows_resorted
        duplicate_rows_rejected += parsed.duplicate_rows_rejected

        if (
            configuration.reject_unexpected_row_count_drift
            and parsed.total_nonblank_data_rows != entry.expected_row_count
        ):
            issues.append(
                DataQualityIssue(
                    relative_path=entry.relative_path,
                    row_number=None,
                    symbol=entry.symbol,
                    timeframe=entry.timeframe,
                    reason_code="UNEXPECTED_ROW_COUNT",
                    classification=DataQualityClassification.REJECT_DATASET,
                )
            )
            raise InvalidDatasetManifestError(
                f"unexpected row count for {entry.relative_path!r}: expected"
                f" {entry.expected_row_count}, got {parsed.total_nonblank_data_rows}."
            )
        elif parsed.total_nonblank_data_rows != entry.expected_row_count:
            issues.append(
                DataQualityIssue(
                    relative_path=entry.relative_path,
                    row_number=None,
                    symbol=entry.symbol,
                    timeframe=entry.timeframe,
                    reason_code="UNEXPECTED_ROW_COUNT",
                    classification=DataQualityClassification.WARNING,
                )
            )

        key = (entry.symbol, entry.timeframe)
        normalized_candles = candles_by_symbol_timeframe.setdefault(key, [])
        confirmed_only: list[NormalizedCandle] = []
        for record in parsed.records:
            candle = _record_to_normalized_candle(
                record, entry=entry, manifest=manifest
            )
            if record.completeness == CandleCompleteness.INCOMPLETE:
                issues.append(
                    DataQualityIssue(
                        relative_path=entry.relative_path,
                        row_number=record.row_number,
                        symbol=entry.symbol,
                        timeframe=entry.timeframe,
                        reason_code="INCOMPLETE_CANDLE_EXCLUDED",
                        classification=DataQualityClassification.RETAIN,
                    )
                )
                continue
            confirmed_only.append(candle)

        confirmed_only.sort(key=lambda c: c.event_time_utc)
        for previous_candle, current_candle in pairwise(confirmed_only):
            gap = detect_gap(
                entry.symbol,
                entry.timeframe,
                previous_candle.event_time_utc,
                current_candle.event_time_utc,
            )
            if gap is not None:
                gaps.append(gap)

        normalized_candles.extend(confirmed_only)

    measurement_configuration = MarketMeasurementConfiguration(
        minimum_price_tick=Decimal("0.01")
    )
    btmm_configuration = BtmmConfiguration(minimum_price_tick=Decimal("0.01"))
    poi_configuration = PoiConfiguration(minimum_price_tick=Decimal("0.01"))
    floor_bars = warm_up_floor_bars(
        measurement_configuration, btmm_configuration, poi_configuration
    )

    timeframe_coverage: list[TimeframeCoverage] = []
    for (symbol, timeframe), candles in candles_by_symbol_timeframe.items():
        candles.sort(key=lambda c: c.event_time_utc)
        complete_calendar_period_count = (
            len(candles) if timeframe in (Timeframe.D1, Timeframe.W1) else None
        )
        timeframe_coverage.append(
            TimeframeCoverage(
                symbol=symbol,
                timeframe=timeframe,
                candle_count=len(candles),
                warm_up_floor_bars=floor_bars,
                meets_warm_up_floor=len(candles) >= floor_bars,
                complete_calendar_period_count=complete_calendar_period_count,
            )
        )
    timeframe_coverage.sort(
        key=lambda c: (_SYMBOL_ORDER[c.symbol], _TIMEFRAME_RANK[c.timeframe])
    )

    data_quality_report = HistoricalDataQualityReport(
        blank_rows_skipped=blank_rows_skipped,
        unsorted_rows_resorted=unsorted_rows_resorted,
        duplicate_rows_rejected=duplicate_rows_rejected,
        issues=tuple(issues),
        gaps=tuple(gaps),
        checksum_verified=checksum_verified,
        checksum_mismatched_files=tuple(checksum_mismatched_files),
        timeframe_coverage=tuple(timeframe_coverage),
    )

    timeframe_inputs_by_symbol: list[
        tuple[InternalSymbol, tuple[ScannerTimeframeInput, ...]]
    ] = []
    symbols_present = sorted(
        {symbol for symbol, _ in candles_by_symbol_timeframe},
        key=lambda s: _SYMBOL_ORDER[s],
    )
    for symbol in symbols_present:
        timeframes_for_symbol = sorted(
            (tf for (sym, tf) in candles_by_symbol_timeframe if sym == symbol),
            key=lambda t: _TIMEFRAME_RANK[t],
        )
        bundles = tuple(
            ScannerTimeframeInput(
                timeframe=timeframe,
                candles=tuple(candles_by_symbol_timeframe[(symbol, timeframe)]),
            )
            for timeframe in timeframes_for_symbol
        )
        timeframe_inputs_by_symbol.append((symbol, bundles))

    reviewed_cases: tuple[ReviewedScannerCase, ...] = ()
    if manifest.reviewed_case_file is not None:
        validate_relative_path_syntax(
            manifest.reviewed_case_file, field_name="reviewed_case_file"
        )
        reviewed_case_path = _resolve_and_validate_path(
            dataset_root_resolved, manifest.reviewed_case_file
        )
        if reviewed_case_path in seen_resolved_targets:
            raise InvalidDatasetManifestError(
                f"duplicate resolved file target: {manifest.reviewed_case_file!r}."
            )
        seen_resolved_targets.add(reviewed_case_path)
        assert manifest.reviewed_case_sha256 is not None
        _verify_checksum(
            reviewed_case_path,
            manifest.reviewed_case_sha256,
            relative_path=manifest.reviewed_case_file,
        )
        file_checksums.append(
            (manifest.reviewed_case_file, manifest.reviewed_case_sha256)
        )

        document = ReviewedCaseDocument.model_validate_json(
            reviewed_case_path.read_bytes()
        )
        if document.dataset_id != manifest.dataset_id:
            raise InvalidDatasetManifestError(
                "reviewed_cases.json dataset_id does not match the manifest's own"
                " dataset_id."
            )
        seen_case_ids: set[str] = set()
        for case in document.cases:
            if case.case_id in seen_case_ids:
                raise InvalidDatasetManifestError(
                    f"duplicate case_id in reviewed_cases.json: {case.case_id!r}."
                )
            seen_case_ids.add(case.case_id)
            validate_reviewed_scanner_case(case)
        reviewed_cases = document.cases

    return LoadedHistoricalDataset(
        manifest=manifest,
        timeframe_inputs_by_symbol=tuple(timeframe_inputs_by_symbol),
        reviewed_cases=reviewed_cases,
        data_quality_report=data_quality_report,
        file_checksums=tuple(file_checksums),
    )
