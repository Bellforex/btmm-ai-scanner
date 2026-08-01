import csv
import io
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal, InvalidOperation
from uuid import UUID
from zoneinfo import ZoneInfo

from btmm_ai_scanner.config.enums import InternalSymbol, Timeframe
from btmm_ai_scanner.contracts.raw_candle import CandleCompleteness
from btmm_ai_scanner.historical_backtest.data_quality import DataQualityIssue
from btmm_ai_scanner.historical_backtest.enums import (
    CanonicalCandleField,
    DataQualityClassification,
)
from btmm_ai_scanner.historical_backtest.identity import (
    CandleIdentityCollisionTracker,
    derive_content_fingerprint,
    derive_provenance_id,
    derive_record_id,
    derive_source_record_id,
)
from btmm_ai_scanner.historical_backtest.manifest import (
    DatasetManifest,
    HistoricalFileEntry,
    _load_bundled_zone,
)

_INTRADAY_DURATION: dict[Timeframe, timedelta] = {
    Timeframe.M1: timedelta(minutes=1),
    Timeframe.M5: timedelta(minutes=5),
    Timeframe.M15: timedelta(minutes=15),
    Timeframe.H1: timedelta(hours=1),
    Timeframe.H3: timedelta(hours=3),
    Timeframe.H4: timedelta(hours=4),
}

_TRUE_VALUES = frozenset({"true"})
_FALSE_VALUES = frozenset({"false"})


class _RowRejected(Exception):
    def __init__(self, reason_code: str) -> None:
        super().__init__(reason_code)
        self.reason_code = reason_code


class FileRejected(Exception):
    def __init__(self, reason_code: str) -> None:
        super().__init__(reason_code)
        self.reason_code = reason_code


@dataclass(frozen=True)
class ParsedCandleRecord:
    symbol: InternalSymbol
    timeframe: Timeframe
    event_time_utc: datetime
    original_event_time: datetime
    availability_time_utc: datetime
    original_availability_time: datetime
    open_price: Decimal
    high_price: Decimal
    low_price: Decimal
    close_price: Decimal
    volume: Decimal | None
    completeness: CandleCompleteness
    source_record_id: str
    provenance_id: UUID
    record_id: UUID
    content_fingerprint: str
    row_number: int


@dataclass(frozen=True)
class _PendingRecord:
    row_number: int
    event_time_utc: datetime
    original_event_time: datetime
    availability_time_utc: datetime
    open_price: Decimal
    high_price: Decimal
    low_price: Decimal
    close_price: Decimal
    volume: Decimal | None
    explicit_completeness: CandleCompleteness | None
    source_record_id: str


@dataclass(frozen=True)
class ParsedFileResult:
    records: tuple[ParsedCandleRecord, ...]
    issues: tuple[DataQualityIssue, ...]
    blank_rows_skipped: int
    duplicate_rows_rejected: int
    unsorted_rows_resorted: int
    total_nonblank_data_rows: int


def resolve_local_instants(
    naive_local_datetime: datetime, zone: ZoneInfo
) -> tuple[datetime, ...]:
    valid: list[datetime] = []
    for fold in (0, 1):
        candidate = naive_local_datetime.replace(tzinfo=zone, fold=fold)
        candidate_utc = candidate.astimezone(UTC)
        round_trip = candidate_utc.astimezone(zone)
        if (
            round_trip.replace(tzinfo=None) == naive_local_datetime
            and round_trip.fold == fold
        ):
            valid.append(candidate_utc)

    deduped: list[datetime] = []
    for instant in valid:
        if instant not in deduped:
            deduped.append(instant)
    return tuple(deduped)


def _parse_open_timestamp(
    raw_value: str, timestamp_format: str, zone: ZoneInfo
) -> tuple[datetime, datetime]:
    stripped = raw_value.strip()
    if stripped == "":
        raise _RowRejected("EMPTY_TIMESTAMP")
    try:
        naive_local = datetime.strptime(stripped, timestamp_format)
    except ValueError as exc:
        raise _RowRejected("INVALID_TIMESTAMP_FORMAT") from exc
    if naive_local.tzinfo is not None:
        raise _RowRejected("UNEXPECTED_TIMEZONE_AWARE_TIMESTAMP")

    instants = resolve_local_instants(naive_local, zone)
    if len(instants) == 0:
        raise _RowRejected("NONEXISTENT_LOCAL_TIME")
    if len(instants) > 1:
        raise _RowRejected("AMBIGUOUS_LOCAL_TIME")
    return naive_local, instants[0]


def _derive_event_and_availability(
    naive_local_open: datetime,
    event_time_utc: datetime,
    zone: ZoneInfo,
    entry: HistoricalFileEntry,
) -> datetime:
    if entry.timeframe in _INTRADAY_DURATION:
        return event_time_utc + _INTRADAY_DURATION[entry.timeframe]

    assert entry.calendar_close_day_offset is not None
    assert entry.calendar_close_time_local is not None
    close_date: date = naive_local_open.date() + timedelta(
        days=entry.calendar_close_day_offset
    )
    close_naive = datetime.combine(close_date, entry.calendar_close_time_local)

    instants = resolve_local_instants(close_naive, zone)
    if len(instants) == 0:
        raise _RowRejected("NONEXISTENT_LOCAL_CLOSE")
    if len(instants) > 1:
        raise _RowRejected("AMBIGUOUS_LOCAL_CLOSE")
    return instants[0]


def _parse_decimal(raw_value: str) -> Decimal:
    try:
        value = Decimal(raw_value)
    except InvalidOperation as exc:
        raise _RowRejected("INVALID_DECIMAL") from exc
    if not value.is_finite():
        raise _RowRejected("NON_FINITE_DECIMAL")
    return value


def _parse_completeness_column(raw_value: str) -> CandleCompleteness:
    lowered = raw_value.strip().lower()
    if lowered in _TRUE_VALUES:
        return CandleCompleteness.CONFIRMED_COMPLETE
    if lowered in _FALSE_VALUES:
        return CandleCompleteness.INCOMPLETE
    raise _RowRejected("INVALID_COMPLETENESS_VALUE")


def parse_candle_rows(
    *,
    decoded_text: str,
    entry: HistoricalFileEntry,
    manifest: DatasetManifest,
    identity_tracker: CandleIdentityCollisionTracker,
) -> ParsedFileResult:
    reader = csv.reader(io.StringIO(decoded_text))
    try:
        header_row = next(reader)
    except StopIteration:
        raise FileRejected("EMPTY_FILE") from None

    stripped_headers = [name.strip() for name in header_row]
    if len(stripped_headers) != len(set(stripped_headers)):
        raise FileRejected("DUPLICATE_HEADER_COLUMN")

    header_index = {name: idx for idx, name in enumerate(stripped_headers)}
    field_index = {
        hm.canonical_field: header_index[hm.source_column]
        for hm in entry.header_mapping
        if hm.source_column in header_index
    }

    zone = _load_bundled_zone(entry.timezone)

    issues: list[DataQualityIssue] = []
    blank_rows_skipped = 0
    duplicate_rows_rejected = 0
    total_nonblank_data_rows = 0
    seen_by_event_time: dict[
        datetime, tuple[Decimal, Decimal, Decimal, Decimal, Decimal | None]
    ] = {}
    pending: list[_PendingRecord] = []
    provenance_id, provenance_bytes = derive_provenance_id(
        dataset_id=manifest.dataset_id,
        dataset_version=manifest.dataset_version,
        provider=manifest.provider,
        relative_path=entry.relative_path,
        expected_sha256=entry.sha256,
    )
    identity_tracker.check_provenance_id(
        provenance_id, provenance_bytes, source=entry.relative_path
    )
    seen_source_record_ids: set[str] = set()

    for row in reader:
        row_number = reader.line_num
        if all(cell.strip() == "" for cell in row):
            blank_rows_skipped += 1
            continue

        total_nonblank_data_rows += 1

        try:
            if CanonicalCandleField.TIMESTAMP not in field_index:
                raise _RowRejected("EMPTY_MANDATORY_FIELD")

            expected_columns = max(field_index.values()) + 1 if field_index else 0
            if len(row) < expected_columns:
                raise _RowRejected("SHORT_ROW")
            if len(row) > len(stripped_headers):
                raise _RowRejected("SURPLUS_COLUMN")

            def field(
                canonical: "CanonicalCandleField",
                *,
                required: bool,
                row: list[str] = row,
            ) -> str | None:
                idx = field_index.get(canonical)
                if idx is None:
                    return None
                value = row[idx].strip()
                if required and value == "":
                    raise _RowRejected("EMPTY_MANDATORY_FIELD")
                return value

            timestamp_raw = field(CanonicalCandleField.TIMESTAMP, required=True)
            assert timestamp_raw is not None
            naive_local_open, event_time_utc = _parse_open_timestamp(
                timestamp_raw, entry.timestamp_format, zone
            )
            availability_time_utc = _derive_event_and_availability(
                naive_local_open, event_time_utc, zone, entry
            )
            if not availability_time_utc > event_time_utc:
                raise _RowRejected("NON_POSITIVE_AVAILABILITY_DURATION")

            open_raw = field(CanonicalCandleField.OPEN, required=True)
            high_raw = field(CanonicalCandleField.HIGH, required=True)
            low_raw = field(CanonicalCandleField.LOW, required=True)
            close_raw = field(CanonicalCandleField.CLOSE, required=True)
            assert open_raw is not None
            assert high_raw is not None
            assert low_raw is not None
            assert close_raw is not None
            open_price = _parse_decimal(open_raw)
            high_price = _parse_decimal(high_raw)
            low_price = _parse_decimal(low_raw)
            close_price = _parse_decimal(close_raw)
            for price in (open_price, high_price, low_price, close_price):
                if price <= 0:
                    raise _RowRejected("NON_POSITIVE_PRICE")
            if high_price < max(open_price, close_price, low_price):
                raise _RowRejected("INVALID_OHLC_GEOMETRY")
            if low_price > min(open_price, close_price):
                raise _RowRejected("INVALID_OHLC_GEOMETRY")

            volume_raw = field(CanonicalCandleField.VOLUME, required=False)
            volume: Decimal | None = None
            if volume_raw is not None and volume_raw != "":
                volume = _parse_decimal(volume_raw)
                if volume < 0:
                    raise _RowRejected("NEGATIVE_VOLUME")

            complete_raw = field(CanonicalCandleField.COMPLETE, required=False)
            explicit_completeness: CandleCompleteness | None = None
            if complete_raw is not None and complete_raw != "":
                explicit_completeness = _parse_completeness_column(complete_raw)

            if entry.expected_start <= event_time_utc <= entry.expected_end:
                pass
            else:
                raise _RowRejected("TIMESTAMP_OUTSIDE_EXPECTED_RANGE")

            source_record_id_raw = field(
                CanonicalCandleField.SOURCE_RECORD_ID, required=False
            )
            source_record_id = derive_source_record_id(
                literal_value=source_record_id_raw,
                dataset_id=manifest.dataset_id,
                dataset_version=manifest.dataset_version,
                relative_path=entry.relative_path,
                physical_record_number=row_number,
                symbol=entry.symbol,
                timeframe=entry.timeframe,
                event_time_utc=event_time_utc,
            )
            if source_record_id_raw is not None and source_record_id_raw.strip() != "":
                if source_record_id in seen_source_record_ids:
                    raise _RowRejected("DUPLICATE_SOURCE_RECORD_ID")
            seen_source_record_ids.add(source_record_id)

            ohlcv_key = (open_price, high_price, low_price, close_price, volume)
            if event_time_utc in seen_by_event_time:
                if seen_by_event_time[event_time_utc] == ohlcv_key:
                    duplicate_rows_rejected += 1
                    continue
                raise FileRejected("DUPLICATE_TIMESTAMP_DIFFERING_OHLCV")
            seen_by_event_time[event_time_utc] = ohlcv_key

            pending.append(
                _PendingRecord(
                    row_number=row_number,
                    event_time_utc=event_time_utc,
                    original_event_time=naive_local_open.replace(tzinfo=zone),
                    availability_time_utc=availability_time_utc,
                    open_price=open_price,
                    high_price=high_price,
                    low_price=low_price,
                    close_price=close_price,
                    volume=volume,
                    explicit_completeness=explicit_completeness,
                    source_record_id=source_record_id,
                )
            )
        except _RowRejected as rejected:
            issues.append(
                DataQualityIssue(
                    relative_path=entry.relative_path,
                    row_number=row_number,
                    symbol=entry.symbol,
                    timeframe=entry.timeframe,
                    reason_code=rejected.reason_code,
                    classification=DataQualityClassification.REJECT_ROW,
                )
            )
            continue

    pending.sort(key=lambda item: item.event_time_utc)
    unsorted_rows_resorted = 0
    previous_time: datetime | None = None
    for item in pending:
        current_time = item.event_time_utc
        if previous_time is not None and current_time < previous_time:
            unsorted_rows_resorted += 1
        previous_time = current_time

    records: list[ParsedCandleRecord] = []
    last_index = len(pending) - 1
    for index, item in enumerate(pending):
        if item.explicit_completeness is not None:
            completeness = item.explicit_completeness
        elif entry.complete_candles_only:
            if (
                index == last_index
                and item.availability_time_utc > manifest.created_at_utc
            ):
                completeness = CandleCompleteness.INCOMPLETE
            else:
                completeness = CandleCompleteness.CONFIRMED_COMPLETE
        else:
            completeness = CandleCompleteness.UNKNOWN

        content_fingerprint, content_bytes = derive_content_fingerprint(
            provider=manifest.provider,
            symbol=entry.symbol,
            timeframe=entry.timeframe,
            event_time_utc=item.event_time_utc,
            availability_time_utc=item.availability_time_utc,
            open_price=item.open_price,
            high_price=item.high_price,
            low_price=item.low_price,
            close_price=item.close_price,
            volume=item.volume,
            completeness=completeness,
            source_record_id=item.source_record_id,
        )
        identity_tracker.check_content_fingerprint(
            content_fingerprint, content_bytes, source=entry.relative_path
        )

        record_id, record_bytes = derive_record_id(
            provenance_id=provenance_id,
            source_record_id=item.source_record_id,
            provider=manifest.provider,
            symbol=entry.symbol,
            timeframe=entry.timeframe,
            event_time_utc=item.event_time_utc,
        )
        identity_tracker.check_record_id(
            record_id, record_bytes, source=entry.relative_path
        )

        records.append(
            ParsedCandleRecord(
                symbol=entry.symbol,
                timeframe=entry.timeframe,
                event_time_utc=item.event_time_utc,
                original_event_time=item.original_event_time,
                availability_time_utc=item.availability_time_utc,
                original_availability_time=item.availability_time_utc,
                open_price=item.open_price,
                high_price=item.high_price,
                low_price=item.low_price,
                close_price=item.close_price,
                volume=item.volume,
                completeness=completeness,
                source_record_id=item.source_record_id,
                provenance_id=provenance_id,
                record_id=record_id,
                content_fingerprint=content_fingerprint,
                row_number=item.row_number,
            )
        )

    return ParsedFileResult(
        records=tuple(records),
        issues=tuple(issues),
        blank_rows_skipped=blank_rows_skipped,
        duplicate_rows_rejected=duplicate_rows_rejected,
        unsorted_rows_resorted=unsorted_rows_resorted,
        total_nonblank_data_rows=total_nonblank_data_rows,
    )
