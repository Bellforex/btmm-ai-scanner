import pytest

from btmm_ai_scanner.historical_backtest.enums import CanonicalCandleField
from btmm_ai_scanner.historical_backtest.manifest import (
    HeaderMappingEntry,
    InvalidDatasetManifestError,
    _validate_header_mapping,
)

_MANDATORY_MAPPING = (
    HeaderMappingEntry(
        canonical_field=CanonicalCandleField.TIMESTAMP, source_column="TIMESTAMP"
    ),
    HeaderMappingEntry(canonical_field=CanonicalCandleField.OPEN, source_column="OPEN"),
    HeaderMappingEntry(canonical_field=CanonicalCandleField.HIGH, source_column="HIGH"),
    HeaderMappingEntry(canonical_field=CanonicalCandleField.LOW, source_column="LOW"),
    HeaderMappingEntry(
        canonical_field=CanonicalCandleField.CLOSE, source_column="CLOSE"
    ),
)


def test_header_mapping_rejects_duplicate_source_column() -> None:
    mapping = (
        *_MANDATORY_MAPPING,
        HeaderMappingEntry(
            canonical_field=CanonicalCandleField.VOLUME, source_column="TIMESTAMP"
        ),
    )
    with pytest.raises(InvalidDatasetManifestError):
        _validate_header_mapping(mapping)


def test_header_mapping_rejects_duplicate_canonical_field() -> None:
    mapping = (
        *_MANDATORY_MAPPING,
        HeaderMappingEntry(
            canonical_field=CanonicalCandleField.CLOSE, source_column="CLOSE_2"
        ),
    )
    with pytest.raises(InvalidDatasetManifestError):
        _validate_header_mapping(mapping)


def test_header_mapping_rejects_blank_source_column() -> None:
    mapping = (
        *_MANDATORY_MAPPING[:-1],
        HeaderMappingEntry(
            canonical_field=CanonicalCandleField.CLOSE, source_column="   "
        ),
    )
    with pytest.raises(InvalidDatasetManifestError):
        _validate_header_mapping(mapping)


def test_header_mapping_rejects_missing_mandatory_canonical_field() -> None:
    mapping = _MANDATORY_MAPPING[:-1]
    with pytest.raises(InvalidDatasetManifestError):
        _validate_header_mapping(mapping)


def test_header_mapping_accepts_arbitrary_literal_column_names_for_tradingview_and_fxcm_style_files() -> (
    None
):
    tradingview_style = (
        HeaderMappingEntry(
            canonical_field=CanonicalCandleField.TIMESTAMP, source_column="time"
        ),
        HeaderMappingEntry(
            canonical_field=CanonicalCandleField.OPEN, source_column="open"
        ),
        HeaderMappingEntry(
            canonical_field=CanonicalCandleField.HIGH, source_column="high"
        ),
        HeaderMappingEntry(
            canonical_field=CanonicalCandleField.LOW, source_column="low"
        ),
        HeaderMappingEntry(
            canonical_field=CanonicalCandleField.CLOSE, source_column="close"
        ),
    )
    fxcm_style = (
        HeaderMappingEntry(
            canonical_field=CanonicalCandleField.TIMESTAMP, source_column="Date Time"
        ),
        HeaderMappingEntry(
            canonical_field=CanonicalCandleField.OPEN, source_column="BidOpen"
        ),
        HeaderMappingEntry(
            canonical_field=CanonicalCandleField.HIGH, source_column="BidHigh"
        ),
        HeaderMappingEntry(
            canonical_field=CanonicalCandleField.LOW, source_column="BidLow"
        ),
        HeaderMappingEntry(
            canonical_field=CanonicalCandleField.CLOSE, source_column="BidClose"
        ),
    )
    _validate_header_mapping(tradingview_style)
    _validate_header_mapping(fxcm_style)
