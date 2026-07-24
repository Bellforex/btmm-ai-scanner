from uuid import UUID

import pytest
from pydantic import ValidationError

from btmm_ai_scanner.contracts.types import ContractModel, SHA256Fingerprint, UUIDv7

_UUIDV7_TEXT = "0193f2c0-1234-7abc-8def-abcdefabcdef"
_UUIDV7_UUID = UUID(_UUIDV7_TEXT)
_FINGERPRINT = "a" * 64


class _IdentityModel(ContractModel):
    record_id: UUIDv7
    content_fingerprint: SHA256Fingerprint


class _FloatModel(ContractModel):
    value: float


class _StrictIntModel(ContractModel):
    value: int


class _NestedInner(ContractModel):
    value: int


class _NestedOuter(ContractModel):
    inner: _NestedInner


class _DefaultFingerprintModel(ContractModel):
    fingerprint: SHA256Fingerprint = "too-short"


class _FingerprintOnlyModel(ContractModel):
    value: SHA256Fingerprint


class _UUIDv7OnlyModel(ContractModel):
    value: UUIDv7


def test_contract_model_is_frozen() -> None:
    model = _IdentityModel(record_id=_UUIDV7_UUID, content_fingerprint=_FINGERPRINT)
    with pytest.raises(ValidationError):
        model.content_fingerprint = "b" * 64


def test_contract_model_forbids_extra_fields() -> None:
    with pytest.raises(ValidationError):
        _IdentityModel(
            record_id=_UUIDV7_UUID,
            content_fingerprint=_FINGERPRINT,
            unexpected_field=1,  # type: ignore[call-arg]
        )


def test_contract_model_rejects_type_coercion() -> None:
    with pytest.raises(ValidationError):
        _StrictIntModel(value="5")  # type: ignore[arg-type]


def test_contract_model_validates_default_values() -> None:
    with pytest.raises(ValidationError):
        _DefaultFingerprintModel()


def test_contract_model_revalidates_nested_instances() -> None:
    inner = _NestedInner(value=1)
    object.__setattr__(inner, "value", "not-an-int")
    with pytest.raises(ValidationError):
        _NestedOuter(inner=inner)


@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf")])
def test_contract_model_rejects_nan_and_infinity(value: float) -> None:
    with pytest.raises(ValidationError):
        _FloatModel(value=value)


def test_uuidv7_accepts_canonical_string_and_uuid_instance() -> None:
    from_string = _UUIDv7OnlyModel(value=_UUIDV7_TEXT)  # type: ignore[arg-type]
    from_uuid = _UUIDv7OnlyModel(value=_UUIDV7_UUID)
    assert from_string.value == _UUIDV7_UUID
    assert from_uuid.value == _UUIDV7_UUID


def test_uuidv7_rejects_invalid_text() -> None:
    with pytest.raises(ValidationError):
        _UUIDv7OnlyModel(value="not-a-uuid")  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "value",
    [
        "00000000-0000-0000-0000-000000000000",
        "12345678-1234-4234-8234-123456789abc",
    ],
)
def test_uuidv7_rejects_nil_and_non_version_seven_values(value: str) -> None:
    with pytest.raises(ValidationError):
        _UUIDv7OnlyModel(value=value)  # type: ignore[arg-type]


def test_uuidv7_rejects_non_rfc_variant() -> None:
    non_rfc_variant_text = "0193f2c0-1234-7abc-0def-abcdefabcdef"
    assert UUID(non_rfc_variant_text).variant != UUID(_UUIDV7_TEXT).variant
    with pytest.raises(ValidationError):
        _UUIDv7OnlyModel(value=non_rfc_variant_text)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "value",
    [
        _UUIDV7_TEXT.upper(),
        _UUIDV7_TEXT.replace("-", ""),
        "{" + _UUIDV7_TEXT + "}",
    ],
)
def test_uuidv7_rejects_noncanonical_text(value: str) -> None:
    with pytest.raises(ValidationError):
        _UUIDv7OnlyModel(value=value)  # type: ignore[arg-type]


def test_uuidv7_serialization_modes() -> None:
    model = _UUIDv7OnlyModel(value=_UUIDV7_TEXT)  # type: ignore[arg-type]
    assert model.model_dump()["value"] == _UUIDV7_UUID
    assert model.model_dump_json() == f'{{"value":"{_UUIDV7_TEXT}"}}'


def test_sha256_fingerprint_accepts_exact_lowercase_hex() -> None:
    model = _FingerprintOnlyModel(value=_FINGERPRINT)
    assert model.value == _FINGERPRINT


@pytest.mark.parametrize(
    "value",
    [
        "A" * 64,
        "a" * 63,
        "a" * 65,
        "g" * 64,
    ],
)
def test_sha256_fingerprint_rejects_invalid_values(value: str) -> None:
    with pytest.raises(ValidationError):
        _FingerprintOnlyModel(value=value)


def test_sha256_fingerprint_serializes_without_normalization() -> None:
    model = _FingerprintOnlyModel(value=_FINGERPRINT)
    assert model.model_dump()["value"] == _FINGERPRINT
    assert model.model_dump_json() == f'{{"value":"{_FINGERPRINT}"}}'


def test_identity_and_fingerprint_are_not_interchangeable() -> None:
    with pytest.raises(ValidationError):
        _FingerprintOnlyModel(value=_UUIDV7_TEXT)
    with pytest.raises(ValidationError):
        _UUIDv7OnlyModel(value=_FINGERPRINT)  # type: ignore[arg-type]


def test_core_value_types_round_trip_through_json() -> None:
    model = _IdentityModel(record_id=_UUIDV7_UUID, content_fingerprint=_FINGERPRINT)
    restored = _IdentityModel.model_validate_json(model.model_dump_json())
    assert restored == model
