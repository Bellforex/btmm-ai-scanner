from enum import StrEnum


class DatasetPartition(StrEnum):
    DEVELOPMENT = "DEVELOPMENT"
    REVIEWED_VALIDATION = "REVIEWED_VALIDATION"
    OUT_OF_SAMPLE = "OUT_OF_SAMPLE"


class CandleTimestampConvention(StrEnum):
    CANDLE_OPEN_TIME = "CANDLE_OPEN_TIME"


class CandleCompletenessConvention(StrEnum):
    ALL_ROWS_CONFIRMED_COMPLETE = "ALL_ROWS_CONFIRMED_COMPLETE"
    FINAL_ROW_MAY_BE_INCOMPLETE = "FINAL_ROW_MAY_BE_INCOMPLETE"


class HistoricalFileFormat(StrEnum):
    CSV_CANONICAL_V1 = "CSV_CANONICAL_V1"


class CanonicalCandleField(StrEnum):
    TIMESTAMP = "TIMESTAMP"
    OPEN = "OPEN"
    HIGH = "HIGH"
    LOW = "LOW"
    CLOSE = "CLOSE"
    VOLUME = "VOLUME"
    COMPLETE = "COMPLETE"
    SOURCE_RECORD_ID = "SOURCE_RECORD_ID"


class DataQualityClassification(StrEnum):
    REJECT_DATASET = "REJECT_DATASET"
    REJECT_FILE = "REJECT_FILE"
    REJECT_ROW = "REJECT_ROW"
    RETAIN_WITH_GAP_RECORD = "RETAIN_WITH_GAP_RECORD"
    RETAIN = "RETAIN"
    WARNING = "WARNING"


class BacktestQualityGateStatus(StrEnum):
    PASSED = "PASSED"
    FAILED = "FAILED"
