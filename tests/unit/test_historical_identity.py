from datetime import UTC, datetime
from decimal import Decimal
from uuid import RFC_4122, UUID

import pytest

from btmm_ai_scanner.config.enums import InternalSymbol, Timeframe
from btmm_ai_scanner.contracts.raw_candle import CandleCompleteness
from btmm_ai_scanner.contracts.types import _validate_uuidv7
from btmm_ai_scanner.domain.enums import DerivedOutputType
from btmm_ai_scanner.historical_backtest.identity import (
    CandleIdentityCollisionTracker,
    ContentAddressedIdentityProvider,
    derive_content_fingerprint,
    derive_normalized_record_id,
    derive_provenance_id,
    derive_record_id,
)
from btmm_ai_scanner.historical_backtest.manifest import InvalidDatasetManifestError


def test_content_addressed_identity_provider_ignores_call_order() -> None:
    provider = ContentAddressedIdentityProvider()
    key_a = ("alpha",)
    key_b = ("beta",)

    first_order_a = provider.identify(
        output_type=DerivedOutputType.CONFIRMED_SWING, semantic_key=key_a
    )
    first_order_b = provider.identify(
        output_type=DerivedOutputType.CONFIRMED_SWING, semantic_key=key_b
    )

    second_order_b = provider.identify(
        output_type=DerivedOutputType.CONFIRMED_SWING, semantic_key=key_b
    )
    second_order_a = provider.identify(
        output_type=DerivedOutputType.CONFIRMED_SWING, semantic_key=key_a
    )

    assert first_order_a == second_order_a
    assert first_order_b == second_order_b


def test_content_addressed_identity_provider_produces_valid_uuidv7_version_and_variant_bits() -> (
    None
):
    provider = ContentAddressedIdentityProvider()
    identifier = provider.identify(
        output_type=DerivedOutputType.CONFIRMED_SWING, semantic_key=("gamma",)
    )
    assert isinstance(identifier, UUID)
    assert identifier.version == 7
    assert identifier.variant == RFC_4122
    validated = _validate_uuidv7(identifier)
    assert validated == identifier


def test_content_addressed_identity_provider_is_deterministic_across_process_instances() -> (
    None
):
    first_provider = ContentAddressedIdentityProvider()
    second_provider = ContentAddressedIdentityProvider()
    key = ("delta",)
    first_id = first_provider.identify(
        output_type=DerivedOutputType.CONFIRMED_SWING, semantic_key=key
    )
    second_id = second_provider.identify(
        output_type=DerivedOutputType.CONFIRMED_SWING, semantic_key=key
    )
    assert first_id == second_id


def test_candle_provenance_id_is_deterministic() -> None:
    first_id, first_bytes = derive_provenance_id(
        dataset_id="dataset-1",
        dataset_version="1.0.0",
        provider="FXCM",
        relative_path="data.csv",
        expected_sha256="a" * 64,
    )
    second_id, second_bytes = derive_provenance_id(
        dataset_id="dataset-1",
        dataset_version="1.0.0",
        provider="FXCM",
        relative_path="data.csv",
        expected_sha256="a" * 64,
    )
    assert first_id == second_id
    assert first_bytes == second_bytes

    different_id, _ = derive_provenance_id(
        dataset_id="dataset-1",
        dataset_version="1.0.0",
        provider="FXCM",
        relative_path="other.csv",
        expected_sha256="a" * 64,
    )
    assert different_id != first_id


def test_candle_record_id_is_deterministic() -> None:
    provenance_id = UUID("018f0000-0000-7000-8000-000000000000")
    event_time_utc = datetime(2024, 1, 1, tzinfo=UTC)

    first_id, first_bytes = derive_record_id(
        provenance_id=provenance_id,
        source_record_id="derived:abc",
        provider="FXCM",
        symbol=InternalSymbol.XAUUSD,
        timeframe=Timeframe.M1,
        event_time_utc=event_time_utc,
    )
    second_id, second_bytes = derive_record_id(
        provenance_id=provenance_id,
        source_record_id="derived:abc",
        provider="FXCM",
        symbol=InternalSymbol.XAUUSD,
        timeframe=Timeframe.M1,
        event_time_utc=event_time_utc,
    )
    assert first_id == second_id
    assert first_bytes == second_bytes

    different_id, _ = derive_record_id(
        provenance_id=provenance_id,
        source_record_id="derived:xyz",
        provider="FXCM",
        symbol=InternalSymbol.XAUUSD,
        timeframe=Timeframe.M1,
        event_time_utc=event_time_utc,
    )
    assert different_id != first_id

    # Strengthened: the normalized-record identity derived from a candle's own
    # record_id must itself be deterministic and distinct from its input, and
    # the collision tracker must accept idempotent re-derivation of any
    # tracked identity category (including the normalized-record category)
    # while rejecting a genuine collision (same identifier, differing
    # canonical content) for every tracked category.
    normalized_first_id, normalized_first_bytes = derive_normalized_record_id(first_id)
    normalized_second_id, normalized_second_bytes = derive_normalized_record_id(
        first_id
    )
    assert normalized_first_id == normalized_second_id
    assert normalized_first_bytes == normalized_second_bytes
    assert normalized_first_id != first_id

    tracker = CandleIdentityCollisionTracker()
    tracker.check_record_id(first_id, first_bytes, source="file-a.csv")
    tracker.check_record_id(second_id, second_bytes, source="file-b.csv")
    tracker.check_normalized_record_id(
        normalized_first_id, normalized_first_bytes, source="file-a.csv"
    )
    tracker.check_normalized_record_id(
        normalized_second_id, normalized_second_bytes, source="file-b.csv"
    )

    with pytest.raises(InvalidDatasetManifestError):
        tracker.check_record_id(
            first_id, b"different-canonical-bytes", source="file-c.csv"
        )
    with pytest.raises(InvalidDatasetManifestError):
        tracker.check_normalized_record_id(
            normalized_first_id, b"different-canonical-bytes", source="file-c.csv"
        )


def test_candle_content_fingerprint_is_canonical() -> None:
    event_time_utc = datetime(2024, 1, 1, tzinfo=UTC)
    availability_time_utc = datetime(2024, 1, 1, 0, 1, tzinfo=UTC)

    fingerprint_a, bytes_a = derive_content_fingerprint(
        provider="FXCM",
        symbol=InternalSymbol.XAUUSD,
        timeframe=Timeframe.M1,
        event_time_utc=event_time_utc,
        availability_time_utc=availability_time_utc,
        open_price=Decimal("2000.00"),
        high_price=Decimal("2000.50"),
        low_price=Decimal("1999.50"),
        close_price=Decimal("2000.10"),
        volume=None,
        completeness=CandleCompleteness.CONFIRMED_COMPLETE,
        source_record_id="derived:abc",
    )
    fingerprint_b, bytes_b = derive_content_fingerprint(
        provider="FXCM",
        symbol=InternalSymbol.XAUUSD,
        timeframe=Timeframe.M1,
        event_time_utc=event_time_utc,
        availability_time_utc=availability_time_utc,
        open_price=Decimal("2000.00"),
        high_price=Decimal("2000.50"),
        low_price=Decimal("1999.50"),
        close_price=Decimal("2000.10"),
        volume=None,
        completeness=CandleCompleteness.CONFIRMED_COMPLETE,
        source_record_id="derived:abc",
    )
    assert fingerprint_a == fingerprint_b
    assert bytes_a == bytes_b
    assert len(fingerprint_a) == 64

    different_price_fingerprint, _ = derive_content_fingerprint(
        provider="FXCM",
        symbol=InternalSymbol.XAUUSD,
        timeframe=Timeframe.M1,
        event_time_utc=event_time_utc,
        availability_time_utc=availability_time_utc,
        open_price=Decimal("2000.00"),
        high_price=Decimal("2000.50"),
        low_price=Decimal("1999.50"),
        close_price=Decimal("2001.10"),
        volume=None,
        completeness=CandleCompleteness.CONFIRMED_COMPLETE,
        source_record_id="derived:abc",
    )
    assert different_price_fingerprint != fingerprint_a
