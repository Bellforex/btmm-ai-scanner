import re
from typing import Annotated
from uuid import RFC_4122, UUID

from pydantic import (
    BaseModel,
    BeforeValidator,
    ConfigDict,
    PlainSerializer,
    RootModel,
    StringConstraints,
    field_validator,
)


class ContractModel(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        strict=True,
        validate_default=True,
        revalidate_instances="always",
        allow_inf_nan=False,
        str_strip_whitespace=False,
        use_enum_values=False,
    )


def _validate_uuidv7(value: object) -> UUID:
    if isinstance(value, UUID):
        candidate = value
    elif isinstance(value, str):
        try:
            candidate = UUID(value)
        except ValueError as exc:
            raise ValueError("Invalid UUID text.") from exc
        if str(candidate) != value:
            raise ValueError(
                "UUID text must be in canonical lowercase, hyphenated form."
            )
    else:
        raise TypeError("UUIDv7 must be a UUID instance or a canonical UUID string.")

    if candidate.int == 0:
        raise ValueError("Nil UUID is not a valid UUIDv7.")
    if candidate.version != 7:
        raise ValueError("UUID must be version 7.")
    if candidate.variant != RFC_4122:
        raise ValueError("UUID must use the RFC 4122 variant.")
    return candidate


UUIDv7 = Annotated[
    UUID,
    BeforeValidator(_validate_uuidv7),
    PlainSerializer(str, return_type=str, when_used="json"),
]

SHA256Fingerprint = Annotated[
    str,
    StringConstraints(
        strict=True,
        min_length=64,
        max_length=64,
        pattern=r"^[0-9a-f]{64}$",
    ),
]

_SEMVER_PATTERN = re.compile(
    r"(?P<major>0|[1-9]\d*)"
    r"\.(?P<minor>0|[1-9]\d*)"
    r"\.(?P<patch>0|[1-9]\d*)"
    r"(?:-(?P<prerelease>(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*)"
    r"(?:\.(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*))*))?"
    r"(?:\+(?P<build>[0-9a-zA-Z-]+(?:\.[0-9a-zA-Z-]+)*))?"
)


def _identifier_is_numeric(identifier: str) -> bool:
    return identifier.isdigit()


def _compare_prerelease(
    left: tuple[str, ...] | None, right: tuple[str, ...] | None
) -> int:
    if left is None and right is None:
        return 0
    if left is None:
        return 1
    if right is None:
        return -1
    for left_identifier, right_identifier in zip(left, right, strict=False):
        if left_identifier == right_identifier:
            continue
        left_numeric = _identifier_is_numeric(left_identifier)
        right_numeric = _identifier_is_numeric(right_identifier)
        if left_numeric and right_numeric:
            return -1 if int(left_identifier) < int(right_identifier) else 1
        if left_numeric != right_numeric:
            return -1 if left_numeric else 1
        return -1 if left_identifier < right_identifier else 1
    if len(left) == len(right):
        return 0
    return -1 if len(left) < len(right) else 1


class SemVer(RootModel[str]):
    model_config = ConfigDict(
        frozen=True,
        strict=True,
        str_strip_whitespace=False,
    )

    root: str

    @field_validator("root")
    @classmethod
    def _validate_semver_text(cls, value: str) -> str:
        if _SEMVER_PATTERN.fullmatch(value) is None:
            raise ValueError(f"{value!r} is not a valid SemVer 2.0.0 version string.")
        return value

    @classmethod
    def parse(cls, value: str) -> "SemVer":
        return cls(value)

    def __str__(self) -> str:
        return self.root

    def _match(self) -> re.Match[str]:
        match = _SEMVER_PATTERN.fullmatch(self.root)
        if match is None:  # pragma: no cover - guaranteed valid by field validation
            raise ValueError("SemVer root text failed re-validation.")
        return match

    @property
    def major(self) -> int:
        return int(self._match().group("major"))

    @property
    def minor(self) -> int:
        return int(self._match().group("minor"))

    @property
    def patch(self) -> int:
        return int(self._match().group("patch"))

    @property
    def prerelease(self) -> tuple[str, ...] | None:
        prerelease = self._match().group("prerelease")
        if prerelease is None:
            return None
        return tuple(prerelease.split("."))

    @property
    def build_metadata(self) -> tuple[str, ...] | None:
        build = self._match().group("build")
        if build is None:
            return None
        return tuple(build.split("."))

    def compare_precedence(self, other: "SemVer") -> int:
        self_core = (self.major, self.minor, self.patch)
        other_core = (other.major, other.minor, other.patch)
        if self_core != other_core:
            return -1 if self_core < other_core else 1
        return _compare_prerelease(self.prerelease, other.prerelease)

    def same_precedence_as(self, other: "SemVer") -> bool:
        return self.compare_precedence(other) == 0
