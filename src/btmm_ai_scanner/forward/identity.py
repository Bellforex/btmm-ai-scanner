"""Deterministic content-addressed identity for forward candles (A7A).

Mirrors the historical loader's content-addressing property: identifiers derive
purely from candle content (never wall-clock), so replaying the same accepted
candle sequence rebuilds byte-identical scanner state after a restart.
"""

from __future__ import annotations

import hashlib
from uuid import UUID


def _pseudo_v7_uuid(payload: bytes) -> UUID:
    """Deterministic UUID with the v7 version nibble and RFC-4122 variant bits
    set, derived from ``payload`` (never from a timestamp)."""
    digest = hashlib.sha256(payload).digest()[:16]
    as_int = int.from_bytes(digest, "big")
    as_int &= ~(0xF << 76)
    as_int |= 7 << 76
    as_int &= ~(0x3 << 62)
    as_int |= 0x2 << 62
    return UUID(int=as_int)


def derive_forward_uuid(kind: str, parts: tuple[str, ...]) -> UUID:
    return _pseudo_v7_uuid(("forward|" + kind + "|" + "|".join(parts)).encode("utf-8"))


def derive_forward_fingerprint(parts: tuple[str, ...]) -> str:
    return hashlib.sha256(("|".join(parts)).encode("utf-8")).hexdigest()
