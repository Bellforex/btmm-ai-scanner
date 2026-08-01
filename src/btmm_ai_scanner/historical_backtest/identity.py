import hashlib
import json
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from btmm_ai_scanner.config.enums import InternalSymbol, Timeframe
from btmm_ai_scanner.contracts.raw_candle import CandleCompleteness
from btmm_ai_scanner.domain.enums import DerivedOutputType
from btmm_ai_scanner.historical_backtest.manifest import InvalidDatasetManifestError

_PROVENANCE_DOMAIN_TAG = "btmm-ai-scanner/historical-candle-provenance/v1"
_RECORD_DOMAIN_TAG = "btmm-ai-scanner/historical-candle-record/v1"
_CONTENT_DOMAIN_TAG = "btmm-ai-scanner/historical-candle-content/v1"
_NORMALIZED_RECORD_DOMAIN_TAG = "btmm-ai-scanner/historical-candle-normalized-record/v1"
_DERIVED_OUTPUT_IDENTITY_NAMESPACE = "btmm-ai-scanner/derived-output-identity/v1"


def _canonical_json_bytes(value: object) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")


def _uuid_from_canonical_bytes(canonical_bytes: bytes) -> UUID:
    digest = hashlib.sha256(canonical_bytes).digest()[:16]
    as_int = int.from_bytes(digest, "big")
    as_int &= ~(0xF << 76)
    as_int |= 7 << 76
    as_int &= ~(0x3 << 62)
    as_int |= 2 << 62
    return UUID(int=as_int)


def derive_provenance_id(
    *,
    dataset_id: str,
    dataset_version: str,
    provider: str,
    relative_path: str,
    expected_sha256: str,
) -> tuple[UUID, bytes]:
    canonical_bytes = _canonical_json_bytes(
        {
            "domain_tag": _PROVENANCE_DOMAIN_TAG,
            "dataset_id": dataset_id,
            "dataset_version": dataset_version,
            "provider": provider,
            "relative_path": relative_path,
            "expected_sha256": expected_sha256,
        }
    )
    return _uuid_from_canonical_bytes(canonical_bytes), canonical_bytes


def derive_source_record_id(
    *,
    literal_value: str | None,
    dataset_id: str,
    dataset_version: str,
    relative_path: str,
    physical_record_number: int,
    symbol: InternalSymbol,
    timeframe: Timeframe,
    event_time_utc: datetime,
) -> str:
    if literal_value is not None:
        stripped = literal_value.strip()
        if stripped != "":
            return stripped

    canonical_bytes = _canonical_json_bytes(
        {
            "dataset_id": dataset_id,
            "dataset_version": dataset_version,
            "relative_path": relative_path,
            "physical_record_number": physical_record_number,
            "symbol": symbol.value,
            "timeframe": timeframe.value,
            "event_time_utc": event_time_utc.astimezone(UTC).isoformat(),
        }
    )
    return f"derived:{hashlib.sha256(canonical_bytes).hexdigest()}"


def derive_record_id(
    *,
    provenance_id: UUID,
    source_record_id: str,
    provider: str,
    symbol: InternalSymbol,
    timeframe: Timeframe,
    event_time_utc: datetime,
) -> tuple[UUID, bytes]:
    canonical_bytes = _canonical_json_bytes(
        {
            "domain_tag": _RECORD_DOMAIN_TAG,
            "provenance_id": str(provenance_id),
            "source_record_id": source_record_id,
            "provider": provider,
            "symbol": symbol.value,
            "timeframe": timeframe.value,
            "event_time_utc": event_time_utc.astimezone(UTC).isoformat(),
        }
    )
    return _uuid_from_canonical_bytes(canonical_bytes), canonical_bytes


def derive_normalized_record_id(record_id: UUID) -> tuple[UUID, bytes]:
    canonical_bytes = _canonical_json_bytes(
        {
            "domain_tag": _NORMALIZED_RECORD_DOMAIN_TAG,
            "record_id": str(record_id),
        }
    )
    return _uuid_from_canonical_bytes(canonical_bytes), canonical_bytes


def derive_content_fingerprint(
    *,
    provider: str,
    symbol: InternalSymbol,
    timeframe: Timeframe,
    event_time_utc: datetime,
    availability_time_utc: datetime,
    open_price: Decimal,
    high_price: Decimal,
    low_price: Decimal,
    close_price: Decimal,
    volume: Decimal | None,
    completeness: CandleCompleteness,
    source_record_id: str,
) -> tuple[str, bytes]:
    canonical_bytes = _canonical_json_bytes(
        {
            "domain_tag": _CONTENT_DOMAIN_TAG,
            "provider": provider,
            "symbol": symbol.value,
            "timeframe": timeframe.value,
            "event_time_utc": event_time_utc.astimezone(UTC).isoformat(),
            "availability_time_utc": availability_time_utc.astimezone(UTC).isoformat(),
            "open": str(open_price),
            "high": str(high_price),
            "low": str(low_price),
            "close": str(close_price),
            "volume": str(volume) if volume is not None else None,
            "complete": completeness.value,
            "source_record_id": source_record_id,
        }
    )
    return hashlib.sha256(canonical_bytes).hexdigest(), canonical_bytes


class CandleIdentityCollisionTracker:
    def __init__(self) -> None:
        self._provenance: dict[str, bytes] = {}
        self._record: dict[str, bytes] = {}
        self._content: dict[str, bytes] = {}

    def check_provenance_id(
        self, key: UUID, canonical_bytes: bytes, *, source: str
    ) -> None:
        self._check(
            self._provenance,
            str(key),
            canonical_bytes,
            category="provenance_id",
            source=source,
        )

    def check_record_id(
        self, key: UUID, canonical_bytes: bytes, *, source: str
    ) -> None:
        self._check(
            self._record, str(key), canonical_bytes, category="record_id", source=source
        )

    def check_content_fingerprint(
        self, key: str, canonical_bytes: bytes, *, source: str
    ) -> None:
        self._check(
            self._content,
            key,
            canonical_bytes,
            category="content_fingerprint",
            source=source,
        )

    @staticmethod
    def _check(
        store: dict[str, bytes],
        key: str,
        canonical_bytes: bytes,
        *,
        category: str,
        source: str,
    ) -> None:
        existing = store.get(key)
        if existing is not None and existing != canonical_bytes:
            raise InvalidDatasetManifestError(
                f"{category} collision detected for {key!r} at {source!r}: an"
                " identical identifier maps to differing canonical content."
            )
        store[key] = canonical_bytes


class ContentAddressedIdentityProvider:
    """Concrete, deterministic `DerivedOutputIdentityProvider`.

    Produces a value that satisfies this repository's own `UUIDv7` structural
    validator (version-7 bit, RFC 4122 variant, non-nil by construction) and is
    stable across processes and independent of call order, since it is a pure
    function of `(output_type, semantic_key)` only. It does not embed a genuine
    Unix-millisecond timestamp and carries no chronological-ordering guarantee.
    """

    def identify(
        self, *, output_type: DerivedOutputType, semantic_key: tuple[str, ...]
    ) -> UUID:
        canonical_bytes = _canonical_json_bytes(
            [_DERIVED_OUTPUT_IDENTITY_NAMESPACE, output_type.value, list(semantic_key)]
        )
        return _uuid_from_canonical_bytes(canonical_bytes)
