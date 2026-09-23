from uuid import UUID

from btmm_ai_scanner.service.identity import (
    canonical_json_bytes,
    content_fingerprint,
    deterministic_uuid,
)


def test_canonical_json_bytes_is_key_order_independent() -> None:
    a = canonical_json_bytes({"b": 1, "a": 2})
    b = canonical_json_bytes({"a": 2, "b": 1})
    assert a == b


def test_canonical_json_bytes_distinguishes_different_content() -> None:
    assert canonical_json_bytes({"a": 1}) != canonical_json_bytes({"a": 2})


def test_deterministic_uuid_is_pure_and_repeatable() -> None:
    seed = canonical_json_bytes({"x": "y"})
    first = deterministic_uuid(seed)
    second = deterministic_uuid(seed)
    assert first == second


def test_deterministic_uuid_differs_for_different_seeds() -> None:
    first = deterministic_uuid(canonical_json_bytes({"x": "y"}))
    second = deterministic_uuid(canonical_json_bytes({"x": "z"}))
    assert first != second


def test_deterministic_uuid_is_structurally_valid_uuidv7() -> None:
    result = deterministic_uuid(canonical_json_bytes({"seed": "value"}))
    assert isinstance(result, UUID)
    assert result.version == 7
    assert str(result.variant) == "specified in RFC 4122"
    assert result.int != 0


def test_content_fingerprint_is_deterministic_sha256_hex() -> None:
    seed = canonical_json_bytes({"a": 1})
    first = content_fingerprint(seed)
    second = content_fingerprint(seed)
    assert first == second
    assert len(first) == 64
    assert all(c in "0123456789abcdef" for c in first)


def test_content_fingerprint_differs_for_different_seeds() -> None:
    first = content_fingerprint(canonical_json_bytes({"a": 1}))
    second = content_fingerprint(canonical_json_bytes({"a": 2}))
    assert first != second
