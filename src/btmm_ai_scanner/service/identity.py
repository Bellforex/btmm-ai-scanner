"""Deterministic, content-addressed identity helpers for the HTTP service
boundary — reimplemented locally (not imported from
``historical_backtest.identity``) since that module is a private, frozen
part of the historical-backtest ingestion pipeline and this is a distinct,
separate concern (turning one HTTP request's raw bars into valid
``NormalizedCandle`` records). The algorithm (SHA-256 digest, forced to a
valid UUID version-7 + RFC-4122-variant bit pattern) is the same technique
already used elsewhere in this project for content-addressed identity —
never random, so the exact same input candle always produces the exact same
record id, which matters for idempotent retries of the same analyze request.
"""

from __future__ import annotations

import hashlib
import json
from uuid import UUID


def canonical_json_bytes(value: object) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")


def deterministic_uuid(canonical_bytes: bytes) -> UUID:
    digest = hashlib.sha256(canonical_bytes).digest()[:16]
    as_int = int.from_bytes(digest, "big")
    as_int &= ~(0xF << 76)
    as_int |= 7 << 76
    as_int &= ~(0x3 << 62)
    as_int |= 2 << 62
    return UUID(int=as_int)


def content_fingerprint(canonical_bytes: bytes) -> str:
    return hashlib.sha256(canonical_bytes).hexdigest()
