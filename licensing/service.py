"""The validation decision — pure logic, no HTTP, fully testable.

`server.py` is a thin transport over this. Keeping the decision separate is
what makes the thirteen licence cases unit-testable without a socket.

WHAT THE SERVICE WILL NOT DO
----------------------------
It never returns the licence key, never echoes it into a message, and never
logs it. Everything customer-facing carries the MASKED form.

It also never closes a trade. A licence answer can only ever restrict NEW
entries — `MANAGE_ONLY` exists precisely so a lapsed licence cannot orphan an
open position. That rule lives in the EA, and the wire protocol is shaped to
make it easy to honour: the response says what is ALLOWED, not what to do.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from typing import Any

from licensing.keys import mask_key
from licensing.store import LicenseStatus, LicenseStore

__all__ = [
    "DEFAULT_LEASE",
    "LicenseState",
    "ValidationRequest",
    "ValidationResponse",
    "validate",
]

#: How long the EA may run on a cached answer when the server is unreachable.
#: Short by design: long enough to survive a conference wifi drop, short enough
#: that a revoked licence stops trading the same day.
DEFAULT_LEASE = timedelta(hours=12)


class LicenseState(StrEnum):
    """Exactly the states the EA implements. Kept in lockstep with the MQL5
    `RC5_LIC_*` constants; a test asserts both lists agree."""

    VALID = "LICENSE_VALID"
    GRACE = "LICENSE_GRACE"
    INVALID = "LICENSE_INVALID"
    EXPIRED = "LICENSE_EXPIRED"
    REVOKED = "LICENSE_REVOKED"
    ACCOUNT_MISMATCH = "LICENSE_ACCOUNT_MISMATCH"
    ACTIVATION_LIMIT = "LICENSE_ACTIVATION_LIMIT"
    SERVER_UNREACHABLE = "LICENSE_SERVER_UNREACHABLE"
    VERSION_BLOCKED = "LICENSE_VERSION_BLOCKED"
    TESTER_BYPASS = "LICENSE_TESTER_BYPASS"


@dataclass(frozen=True)
class ValidationRequest:
    license_key: str
    product_id: str
    ea_version: str
    account_login: str
    account_server: str
    nonce: str = ""


@dataclass(frozen=True)
class ValidationResponse:
    valid: bool
    state: LicenseState
    license_id: str = ""
    expires_at: str = ""
    lease_until: str = ""
    activation_status: str = ""
    minimum_version: str = ""
    message: str = ""
    extra: dict[str, Any] = field(default_factory=dict)

    def to_json(self) -> dict[str, Any]:
        return {
            "valid": self.valid,
            "state": self.state.value,
            "license_id": self.license_id,
            "expires_at": self.expires_at,
            "lease_until": self.lease_until,
            "activation_status": self.activation_status,
            "minimum_version": self.minimum_version,
            "message": self.message,
            **self.extra,
        }


def _version_tuple(text: str) -> tuple[int, ...]:
    parts: list[int] = []
    for chunk in text.split("."):
        digits = "".join(c for c in chunk if c.isdigit())
        parts.append(int(digits) if digits else 0)
    return tuple(parts)


def _deny(state: LicenseState, message: str, **kw: Any) -> ValidationResponse:
    return ValidationResponse(valid=False, state=state, message=message, **kw)


def validate(
    store: LicenseStore,
    request: ValidationRequest,
    *,
    now: datetime | None = None,
    lease: timedelta = DEFAULT_LEASE,
) -> ValidationResponse:
    """Decide one validation. Order of checks is deliberate.

    Identity first, then status, then expiry, then binding, then version —
    cheapest and most definitive refusals first, and never a message that
    reveals whether a near-miss key exists.
    """
    now = now or datetime.now(UTC)
    record = store.by_key(request.license_key)

    # A wrong key and a non-existent key are answered IDENTICALLY, so the
    # endpoint cannot be used to discover which keys are real.
    if record is None:
        return _deny(LicenseState.INVALID, "License not recognised")

    if record.status is LicenseStatus.REVOKED:
        return _deny(
            LicenseState.REVOKED,
            "License revoked",
            license_id=record.license_id,
        )
    if record.status is LicenseStatus.SUSPENDED:
        return _deny(
            LicenseState.INVALID,
            "License suspended",
            license_id=record.license_id,
        )
    if record.status is LicenseStatus.EXPIRED or record.is_expired(now):
        return _deny(
            LicenseState.EXPIRED,
            "License expired",
            license_id=record.license_id,
            expires_at=record.expires_at.isoformat(),
        )
    if request.product_id and request.product_id != record.product_id:
        return _deny(
            LicenseState.INVALID,
            "Wrong product",
            license_id=record.license_id,
        )
    if _version_tuple(request.ea_version) < _version_tuple(
        record.minimum_version
    ):
        return _deny(
            LicenseState.VERSION_BLOCKED,
            f"EA version below required {record.minimum_version}",
            license_id=record.license_id,
            minimum_version=record.minimum_version,
        )

    known = store.has_activation(
        record.license_id, request.account_login, request.account_server
    )
    if not known:
        if store.activation_count(record.license_id) >= record.max_activations:
            # The binding is (LOGIN, SERVER). A different login OR a different
            # broker server is a different activation, which is what stops one
            # key running on a friend's account.
            return _deny(
                LicenseState.ACTIVATION_LIMIT,
                "Activation limit reached for this license",
                license_id=record.license_id,
                activation_status=(
                    f"{store.activation_count(record.license_id)}"
                    f"/{record.max_activations}"
                ),
            )
        store.record_activation(
            record.license_id,
            request.account_login,
            request.account_server,
            ea_version=request.ea_version,
            now=now,
        )
    else:
        store.record_activation(
            record.license_id,
            request.account_login,
            request.account_server,
            ea_version=request.ea_version,
            now=now,
        )

    return ValidationResponse(
        valid=True,
        state=LicenseState.VALID,
        license_id=record.license_id,
        expires_at=record.expires_at.isoformat(),
        lease_until=(now + lease).isoformat(),
        activation_status=(
            f"{store.activation_count(record.license_id)}"
            f"/{record.max_activations}"
        ),
        minimum_version=record.minimum_version,
        message=f"OK {mask_key(request.license_key)}",
    )
