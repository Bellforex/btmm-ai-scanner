import importlib.resources
import re
from datetime import datetime, time
from zoneinfo import ZoneInfo

from btmm_ai_scanner.config.enums import InternalSymbol, Timeframe
from btmm_ai_scanner.contracts.raw_candle import CandleVolumeKind
from btmm_ai_scanner.contracts.types import ContractModel, SemVer, SHA256Fingerprint
from btmm_ai_scanner.historical_backtest.enums import (
    CandleCompletenessConvention,
    CandleTimestampConvention,
    CanonicalCandleField,
    DatasetPartition,
    HistoricalFileFormat,
)

_FXCM_PROVIDER = "FXCM"

_MANDATORY_CANONICAL_FIELDS: frozenset[CanonicalCandleField] = frozenset(
    {
        CanonicalCandleField.TIMESTAMP,
        CanonicalCandleField.OPEN,
        CanonicalCandleField.HIGH,
        CanonicalCandleField.LOW,
        CanonicalCandleField.CLOSE,
    }
)

_INTRADAY_TIMEFRAMES: frozenset[Timeframe] = frozenset(
    {
        Timeframe.M1,
        Timeframe.M5,
        Timeframe.M15,
        Timeframe.H1,
        Timeframe.H3,
        Timeframe.H4,
    }
)

_SHA256_HEX_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_WINDOWS_DRIVE_PATTERN = re.compile(r"^[A-Za-z]:")


class InvalidDatasetManifestError(ValueError):
    pass


def validate_relative_path_syntax(path: str, *, field_name: str) -> None:
    if path == "":
        raise InvalidDatasetManifestError(f"{field_name} must not be empty.")
    if path == ".":
        raise InvalidDatasetManifestError(f"{field_name} must not be '.'.")
    if path.startswith("/"):
        raise InvalidDatasetManifestError(
            f"{field_name} must not be an absolute POSIX path: {path!r}."
        )
    if _WINDOWS_DRIVE_PATTERN.match(path) is not None:
        raise InvalidDatasetManifestError(
            f"{field_name} must not be a Windows drive path: {path!r}."
        )
    if path.startswith("\\\\") or path.startswith("//"):
        raise InvalidDatasetManifestError(
            f"{field_name} must not be a UNC path: {path!r}."
        )
    if "\\" in path:
        raise InvalidDatasetManifestError(
            f"{field_name} must not contain a backslash: {path!r}."
        )
    if "\x00" in path:
        raise InvalidDatasetManifestError(
            f"{field_name} must not contain a NUL character: {path!r}."
        )
    for segment in path.split("/"):
        if segment == "":
            raise InvalidDatasetManifestError(
                f"{field_name} must not contain an empty path segment: {path!r}."
            )
        if segment == ".":
            raise InvalidDatasetManifestError(
                f"{field_name} must not contain a '.' path segment: {path!r}."
            )
        if segment == "..":
            raise InvalidDatasetManifestError(
                f"{field_name} must not contain a '..' path segment: {path!r}."
            )


def _load_bundled_zone(zone_name: str) -> ZoneInfo:
    validate_relative_path_syntax(zone_name, field_name="timezone")

    resource = importlib.resources.files("tzdata.zoneinfo")
    for segment in zone_name.split("/"):
        resource = resource.joinpath(segment)

    if not resource.is_file():
        raise InvalidDatasetManifestError(
            f"timezone {zone_name!r} has no matching resource in the bundled"
            " tzdata package."
        )

    with resource.open("rb") as resource_file:
        return ZoneInfo.from_file(resource_file, key=zone_name)


class HeaderMappingEntry(ContractModel):
    canonical_field: CanonicalCandleField
    source_column: str


def _validate_header_mapping(header_mapping: tuple[HeaderMappingEntry, ...]) -> None:
    seen_source_columns: set[str] = set()
    seen_canonical_fields: set[CanonicalCandleField] = set()
    for entry in header_mapping:
        if entry.source_column.strip() == "":
            raise InvalidDatasetManifestError(
                "header_mapping source_column must not be blank."
            )
        if entry.source_column in seen_source_columns:
            raise InvalidDatasetManifestError(
                f"header_mapping contains a duplicated source_column: "
                f"{entry.source_column!r}."
            )
        seen_source_columns.add(entry.source_column)
        if entry.canonical_field in seen_canonical_fields:
            raise InvalidDatasetManifestError(
                f"header_mapping contains a duplicated canonical_field: "
                f"{entry.canonical_field!r}."
            )
        seen_canonical_fields.add(entry.canonical_field)

    missing = _MANDATORY_CANONICAL_FIELDS - seen_canonical_fields
    if missing:
        raise InvalidDatasetManifestError(
            "header_mapping is missing mandatory canonical field(s): "
            f"{sorted(missing, key=lambda f: f.value)}."
        )


class HistoricalFileEntry(ContractModel):
    relative_path: str
    symbol: InternalSymbol
    timeframe: Timeframe
    format: HistoricalFileFormat
    header_mapping: tuple[HeaderMappingEntry, ...]
    timestamp_semantics: CandleTimestampConvention
    timestamp_format: str
    calendar_close_day_offset: int | None
    calendar_close_time_local: time | None
    timezone: str
    expected_start: datetime
    expected_end: datetime
    expected_row_count: int
    sha256: SHA256Fingerprint
    volume_available: bool
    complete_candles_only: bool


def validate_historical_file_entry(entry: HistoricalFileEntry) -> None:
    validate_relative_path_syntax(entry.relative_path, field_name="relative_path")
    _validate_header_mapping(entry.header_mapping)
    _load_bundled_zone(entry.timezone)

    if "%z" in entry.timestamp_format or "%Z" in entry.timestamp_format:
        raise InvalidDatasetManifestError(
            "timestamp_format must not contain '%z' or '%Z'; the manifest's own"
            " source_timezone is the sole timezone owner."
        )

    if entry.timeframe in _INTRADAY_TIMEFRAMES:
        if entry.calendar_close_day_offset is not None:
            raise InvalidDatasetManifestError(
                "calendar_close_day_offset must be None for a fixed intraday"
                f" timeframe ({entry.timeframe})."
            )
        if entry.calendar_close_time_local is not None:
            raise InvalidDatasetManifestError(
                "calendar_close_time_local must be None for a fixed intraday"
                f" timeframe ({entry.timeframe})."
            )
    elif entry.timeframe == Timeframe.D1:
        if (
            entry.calendar_close_day_offset is None
            or entry.calendar_close_time_local is None
        ):
            raise InvalidDatasetManifestError(
                "calendar_close_day_offset and calendar_close_time_local are"
                " required for D1."
            )
        if entry.calendar_close_day_offset not in (0, 1):
            raise InvalidDatasetManifestError(
                "calendar_close_day_offset must be 0 or 1 for D1; got"
                f" {entry.calendar_close_day_offset!r}."
            )
    elif entry.timeframe == Timeframe.W1:
        if (
            entry.calendar_close_day_offset is None
            or entry.calendar_close_time_local is None
        ):
            raise InvalidDatasetManifestError(
                "calendar_close_day_offset and calendar_close_time_local are"
                " required for W1."
            )
        if not (0 <= entry.calendar_close_day_offset <= 7):
            raise InvalidDatasetManifestError(
                "calendar_close_day_offset must be between 0 and 7 inclusive for"
                f" W1; got {entry.calendar_close_day_offset!r}."
            )

    if entry.expected_start >= entry.expected_end:
        raise InvalidDatasetManifestError(
            "expected_start must be strictly before expected_end."
        )
    if entry.expected_row_count < 0:
        raise InvalidDatasetManifestError("expected_row_count must be non-negative.")


class DatasetManifest(ContractModel):
    dataset_id: str
    dataset_version: str
    provider: str
    source_description: str
    source_timezone: str
    created_at_utc: datetime
    partition: DatasetPartition
    symbols: tuple[InternalSymbol, ...]
    timeframes: tuple[Timeframe, ...]
    file_entries: tuple[HistoricalFileEntry, ...]
    timestamp_convention: CandleTimestampConvention
    candle_completeness_convention: CandleCompletenessConvention
    volume_convention: CandleVolumeKind
    reviewed_case_file: str | None
    reviewed_case_sha256: str | None
    notes: str
    schema_version: SemVer


def validate_dataset_manifest(manifest: DatasetManifest) -> None:
    if manifest.dataset_id.strip() == "":
        raise InvalidDatasetManifestError("dataset_id must not be blank.")
    if manifest.provider != _FXCM_PROVIDER:
        raise InvalidDatasetManifestError(
            f"provider must be {_FXCM_PROVIDER!r}; got {manifest.provider!r}."
        )
    if len(manifest.file_entries) == 0:
        raise InvalidDatasetManifestError("file_entries must not be empty.")

    for entry in manifest.file_entries:
        validate_historical_file_entry(entry)

    expected_symbols = tuple(
        sorted({entry.symbol for entry in manifest.file_entries}, key=lambda s: s.value)
    )
    if tuple(sorted(manifest.symbols, key=lambda s: s.value)) != expected_symbols:
        raise InvalidDatasetManifestError(
            "symbols must equal the sorted union of file_entries[].symbol."
        )
    expected_timeframes = tuple(
        sorted(
            {entry.timeframe for entry in manifest.file_entries}, key=lambda t: t.value
        )
    )
    if tuple(sorted(manifest.timeframes, key=lambda t: t.value)) != expected_timeframes:
        raise InvalidDatasetManifestError(
            "timeframes must equal the sorted union of file_entries[].timeframe."
        )

    for entry in manifest.file_entries:
        if entry.timezone != manifest.source_timezone:
            raise InvalidDatasetManifestError(
                f"file entry {entry.relative_path!r} timezone {entry.timezone!r} must"
                f" equal the manifest's own source_timezone {manifest.source_timezone!r}."
            )
        if entry.timestamp_semantics != manifest.timestamp_convention:
            raise InvalidDatasetManifestError(
                f"file entry {entry.relative_path!r} timestamp_semantics must equal"
                " the manifest's own timestamp_convention."
            )

    if (manifest.reviewed_case_file is None) != (manifest.reviewed_case_sha256 is None):
        raise InvalidDatasetManifestError(
            "reviewed_case_file and reviewed_case_sha256 must both be None or both be"
            " set."
        )
    if manifest.reviewed_case_sha256 is not None:
        if _SHA256_HEX_PATTERN.fullmatch(manifest.reviewed_case_sha256) is None:
            raise InvalidDatasetManifestError(
                "reviewed_case_sha256 must be lowercase 64-character hexadecimal."
            )
        assert manifest.reviewed_case_file is not None
        validate_relative_path_syntax(
            manifest.reviewed_case_file, field_name="reviewed_case_file"
        )

    all_paths = [entry.relative_path for entry in manifest.file_entries]
    if manifest.reviewed_case_file is not None:
        all_paths.append(manifest.reviewed_case_file)

    seen_exact: set[str] = set()
    seen_casefold: set[str] = set()
    for path in all_paths:
        if path in seen_exact:
            raise InvalidDatasetManifestError(
                f"duplicate normalized path across the manifest: {path!r}."
            )
        seen_exact.add(path)
        casefolded = path.casefold()
        if casefolded in seen_casefold:
            raise InvalidDatasetManifestError(
                f"casefold-colliding paths across the manifest: {path!r}."
            )
        seen_casefold.add(casefolded)
