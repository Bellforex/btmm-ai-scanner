"""Data contracts for the BTMM and POI AI scanner."""

from btmm_ai_scanner.contracts.normalized_candle import NormalizedCandle
from btmm_ai_scanner.contracts.provenance_record import (
    EvidenceClassification,
    ProvenanceRecord,
    ProvenanceSourceReference,
)
from btmm_ai_scanner.contracts.raw_candle import (
    CandleCompleteness,
    CandleVolumeKind,
    RawCandle,
)
from btmm_ai_scanner.contracts.rule_version_manifest import (
    CompatibilityClass,
    RuleVersionManifest,
)
from btmm_ai_scanner.contracts.schema_version_manifest import SchemaVersionManifest
from btmm_ai_scanner.contracts.types import (
    ContractModel,
    SemVer,
    SHA256Fingerprint,
    UUIDv7,
)
from btmm_ai_scanner.contracts.validation_result import (
    AnalyticalEligibility,
    ValidationResult,
    ValidationStatus,
)

__all__ = [  # noqa: RUF022 -- order is an approved contract, not alphabetical
    "ContractModel",
    "SHA256Fingerprint",
    "SemVer",
    "UUIDv7",
    "CandleCompleteness",
    "CandleVolumeKind",
    "RawCandle",
    "NormalizedCandle",
    "AnalyticalEligibility",
    "ValidationResult",
    "ValidationStatus",
    "EvidenceClassification",
    "ProvenanceRecord",
    "ProvenanceSourceReference",
    "CompatibilityClass",
    "RuleVersionManifest",
    "SchemaVersionManifest",
]
