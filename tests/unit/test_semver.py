from itertools import pairwise

import pytest
from pydantic import ValidationError

from btmm_ai_scanner.contracts.types import ContractModel, SemVer

_VALID_VERSIONS = [
    "0.1.0",
    "1.0.0",
    "1.0.0-alpha",
    "1.0.0-alpha.1",
    "1.0.0-0.3.7",
    "1.0.0-x.7.z.92",
    "1.0.0+20130313144700",
    "1.0.0-beta+exp.sha.5114f85",
]

_INVALID_VERSIONS = [
    "1",
    "1.2",
    "v1.2.3",
    "01.2.3",
    "1.02.3",
    "1.2.03",
    "1.0.0-01",
    "1.0.0-",
    "1.0.0+",
    "1.0.0-alpha..1",
    "1.0.0 alpha",
    " 1.0.0",
]

_PRECEDENCE_CHAIN = [
    "1.0.0-alpha",
    "1.0.0-alpha.1",
    "1.0.0-alpha.beta",
    "1.0.0-beta",
    "1.0.0-beta.2",
    "1.0.0-beta.11",
    "1.0.0-rc.1",
    "1.0.0",
]


class _VersionHolder(ContractModel):
    version: SemVer


@pytest.mark.parametrize("value", _VALID_VERSIONS)
def test_semver_accepts_valid_semver_2_0_0_values(value: str) -> None:
    assert SemVer.parse(value).root == value


@pytest.mark.parametrize("value", _INVALID_VERSIONS)
def test_semver_rejects_invalid_values(value: str) -> None:
    with pytest.raises(ValidationError):
        SemVer.parse(value)


@pytest.mark.parametrize("value", ["01.2.3", "1.02.3", "1.2.03", "1.0.0-01"])
def test_semver_rejects_leading_zeroes(value: str) -> None:
    with pytest.raises(ValidationError):
        SemVer.parse(value)


def test_semver_preserves_exact_text() -> None:
    text = "1.0.0-beta+exp.sha.5114f85"
    assert str(SemVer.parse(text)) == text


def test_semver_parse_returns_semver() -> None:
    assert isinstance(SemVer.parse("1.2.3"), SemVer)


def test_semver_is_frozen() -> None:
    version = SemVer.parse("1.0.0")
    with pytest.raises(ValidationError):
        version.root = "2.0.0"


def test_semver_serializes_as_json_string() -> None:
    holder = _VersionHolder(version=SemVer.parse("1.2.3-alpha+build"))
    assert holder.model_dump_json() == '{"version":"1.2.3-alpha+build"}'


def test_semver_compares_core_versions() -> None:
    assert SemVer.parse("1.0.0").compare_precedence(SemVer.parse("2.0.0")) == -1
    assert SemVer.parse("2.1.0").compare_precedence(SemVer.parse("2.0.0")) == 1
    assert SemVer.parse("1.2.3").compare_precedence(SemVer.parse("1.2.3")) == 0


def test_semver_orders_prerelease_before_release() -> None:
    assert SemVer.parse("1.0.0-alpha").compare_precedence(SemVer.parse("1.0.0")) == -1
    assert SemVer.parse("1.0.0").compare_precedence(SemVer.parse("1.0.0-alpha")) == 1


def test_semver_compares_prerelease_identifiers() -> None:
    for lower_text, higher_text in pairwise(_PRECEDENCE_CHAIN):
        lower = SemVer.parse(lower_text)
        higher = SemVer.parse(higher_text)
        assert lower.compare_precedence(higher) == -1
        assert higher.compare_precedence(lower) == 1


def test_semver_ignores_build_metadata_for_precedence() -> None:
    left = SemVer.parse("1.0.0+build.1")
    right = SemVer.parse("1.0.0+build.2")
    assert left.compare_precedence(right) == 0


def test_semver_exact_equality_includes_build_metadata() -> None:
    left = SemVer.parse("1.0.0+build.1")
    right = SemVer.parse("1.0.0+build.2")
    assert left != right


def test_semver_same_precedence_ignores_build_metadata() -> None:
    assert SemVer.parse("1.0.0").same_precedence_as(SemVer.parse("1.0.0+build"))
    assert SemVer.parse("1.0.0+build.1").same_precedence_as(
        SemVer.parse("1.0.0+build.2")
    )


def test_semver_does_not_define_rich_ordering() -> None:
    left = SemVer.parse("1.0.0")
    right = SemVer.parse("2.0.0")
    with pytest.raises(TypeError):
        _ = left < right  # type: ignore[operator]


def test_semver_round_trips_through_json() -> None:
    holder = _VersionHolder(version=SemVer.parse("1.2.3-rc.1+build.7"))
    restored = _VersionHolder.model_validate_json(holder.model_dump_json())
    assert restored == holder
