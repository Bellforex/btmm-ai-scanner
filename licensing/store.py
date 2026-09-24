"""The licence record store. SQLite, stdlib only — no new dependencies.

Deliberately small. An event needs a store that is correct and inspectable,
not one that is impressive: two tables, explicit statuses, and every write
through a method that can be tested.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path

from licensing.keys import hash_key, mask_key, new_license_key, normalise_key

__all__ = [
    "LicenseRecord",
    "LicenseStatus",
    "LicenseStore",
]


class LicenseStatus(StrEnum):
    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"
    REVOKED = "REVOKED"
    EXPIRED = "EXPIRED"


@dataclass(frozen=True)
class LicenseRecord:
    license_id: str
    key_hash: str
    customer: str
    email: str
    status: LicenseStatus
    created_at: datetime
    expires_at: datetime
    max_activations: int
    product_id: str
    minimum_version: str
    notes: str = ""

    def is_expired(self, now: datetime) -> bool:
        return now >= self.expires_at


_SCHEMA = """
CREATE TABLE IF NOT EXISTS licenses (
    license_id      TEXT PRIMARY KEY,
    key_hash        TEXT NOT NULL UNIQUE,
    customer        TEXT NOT NULL,
    email           TEXT NOT NULL,
    status          TEXT NOT NULL,
    created_at      TEXT NOT NULL,
    expires_at      TEXT NOT NULL,
    max_activations INTEGER NOT NULL,
    product_id      TEXT NOT NULL,
    minimum_version TEXT NOT NULL,
    notes           TEXT NOT NULL DEFAULT ''
);
CREATE TABLE IF NOT EXISTS activations (
    license_id     TEXT NOT NULL,
    account_login  TEXT NOT NULL,
    account_server TEXT NOT NULL,
    first_seen     TEXT NOT NULL,
    last_seen      TEXT NOT NULL,
    ea_version     TEXT NOT NULL DEFAULT '',
    PRIMARY KEY (license_id, account_login, account_server)
);
"""


def _iso(when: datetime) -> str:
    return when.astimezone(UTC).isoformat()


def _parse(text: str) -> datetime:
    return datetime.fromisoformat(text)


class LicenseStore:
    """Every licence operation, in one auditable place."""

    def __init__(self, path: Path, *, pepper: bytes) -> None:
        self._path = path
        self._pepper = pepper
        path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            conn.executescript(_SCHEMA)

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self._path)
        try:
            conn.row_factory = sqlite3.Row
            yield conn
            conn.commit()
        finally:
            conn.close()

    # -- creation ----------------------------------------------------------

    def create(
        self,
        *,
        customer: str,
        email: str,
        expires_at: datetime,
        product_id: str = "RC5-EA",
        minimum_version: str = "1.00",
        max_activations: int = 1,
        notes: str = "",
        now: datetime | None = None,
    ) -> tuple[str, LicenseRecord]:
        """Mint a licence. Returns `(plaintext_key, record)`.

        The plaintext is returned ONCE and never stored. If it is lost the
        licence must be reissued — which is the point: a store breach yields
        no usable keys.
        """
        now = now or datetime.now(UTC)
        key = new_license_key()
        license_id = f"LIC-{now:%Y%m%d}-{key.split('-')[-1]}"
        record = LicenseRecord(
            license_id=license_id,
            key_hash=hash_key(key, pepper=self._pepper),
            customer=customer,
            email=email,
            status=LicenseStatus.ACTIVE,
            created_at=now,
            expires_at=expires_at,
            max_activations=max_activations,
            product_id=product_id,
            minimum_version=minimum_version,
            notes=notes,
        )
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO licenses VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                (
                    record.license_id,
                    record.key_hash,
                    record.customer,
                    record.email,
                    record.status.value,
                    _iso(record.created_at),
                    _iso(record.expires_at),
                    record.max_activations,
                    record.product_id,
                    record.minimum_version,
                    record.notes,
                ),
            )
        return key, record

    # -- lookup ------------------------------------------------------------

    def _row_to_record(self, row: sqlite3.Row) -> LicenseRecord:
        return LicenseRecord(
            license_id=row["license_id"],
            key_hash=row["key_hash"],
            customer=row["customer"],
            email=row["email"],
            status=LicenseStatus(row["status"]),
            created_at=_parse(row["created_at"]),
            expires_at=_parse(row["expires_at"]),
            max_activations=row["max_activations"],
            product_id=row["product_id"],
            minimum_version=row["minimum_version"],
            notes=row["notes"],
        )

    def by_key(self, key: str) -> LicenseRecord | None:
        """Look up by HASH. The plaintext never touches a WHERE clause."""
        digest = hash_key(normalise_key(key), pepper=self._pepper)
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM licenses WHERE key_hash = ?", (digest,)
            ).fetchone()
        return self._row_to_record(row) if row else None

    def by_id(self, license_id: str) -> LicenseRecord | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM licenses WHERE license_id = ?", (license_id,)
            ).fetchone()
        return self._row_to_record(row) if row else None

    def all_licenses(self) -> tuple[LicenseRecord, ...]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM licenses ORDER BY created_at"
            ).fetchall()
        return tuple(self._row_to_record(r) for r in rows)

    # -- administration ----------------------------------------------------

    def set_status(self, license_id: str, status: LicenseStatus) -> bool:
        with self._connect() as conn:
            changed = conn.execute(
                "UPDATE licenses SET status = ? WHERE license_id = ?",
                (status.value, license_id),
            ).rowcount
        return changed == 1

    def set_expiry(self, license_id: str, expires_at: datetime) -> bool:
        with self._connect() as conn:
            changed = conn.execute(
                "UPDATE licenses SET expires_at = ? WHERE license_id = ?",
                (_iso(expires_at), license_id),
            ).rowcount
        return changed == 1

    # -- activations -------------------------------------------------------

    def activations(self, license_id: str) -> tuple[dict[str, str], ...]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM activations WHERE license_id = ? "
                "ORDER BY first_seen",
                (license_id,),
            ).fetchall()
        return tuple(dict(r) for r in rows)

    def activation_count(self, license_id: str) -> int:
        return len(self.activations(license_id))

    def has_activation(
        self, license_id: str, account_login: str, account_server: str
    ) -> bool:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT 1 FROM activations WHERE license_id = ? "
                "AND account_login = ? AND account_server = ?",
                (license_id, account_login, account_server),
            ).fetchone()
        return row is not None

    def record_activation(
        self,
        license_id: str,
        account_login: str,
        account_server: str,
        *,
        ea_version: str = "",
        now: datetime | None = None,
    ) -> None:
        """Bind an account to a licence, or refresh an existing binding.

        The pair is (LOGIN, SERVER) — not a machine id. A customer may move
        machines; they may not move brokers or accounts.
        """
        now = now or datetime.now(UTC)
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO activations VALUES (?,?,?,?,?,?) "
                "ON CONFLICT(license_id, account_login, account_server) "
                "DO UPDATE SET last_seen = excluded.last_seen, "
                "ea_version = excluded.ea_version",
                (
                    license_id,
                    account_login,
                    account_server,
                    _iso(now),
                    _iso(now),
                    ea_version,
                ),
            )

    def describe(self, record: LicenseRecord) -> str:
        """Admin-facing summary. Carries no key material of any kind."""
        return (
            f"{record.license_id}  {record.status.value:<9} "
            f"{record.customer} <{record.email}>  "
            f"expires {record.expires_at:%Y-%m-%d %H:%M}Z  "
            f"activations {self.activation_count(record.license_id)}"
            f"/{record.max_activations}  product {record.product_id}"
        )


def masked(key: str) -> str:
    """Re-exported so callers never reach for the raw key by habit."""
    return mask_key(key)
