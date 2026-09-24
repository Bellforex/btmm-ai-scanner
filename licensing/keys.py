"""License key generation, masking and hashing.

THE SECURITY TARGET IS COMMERCIAL-GRADE CONTROLLED ACCESS, NOT UNCRACKABILITY.
An EX5 runs on the customer's machine and can be inspected; nothing here
pretends otherwise. What this layer does buy is real: keys cannot be guessed,
the server never stores a usable key, and a leaked log never contains one.

Three rules the rest of the system depends on:

* keys are RANDOM, never sequential — a customer cannot derive the next one;
* the server stores only a hash, so a database copy does not yield usable keys;
* only the MASKED form is ever logged or printed.
"""

from __future__ import annotations

import hashlib
import hmac
import re
import secrets

__all__ = [
    "KEY_PATTERN",
    "hash_key",
    "mask_key",
    "new_license_key",
    "normalise_key",
    "verify_key",
]

#: `RC5-XXXXX-XXXXX-XXXXX-XXXXX`. Crockford-style alphabet: no I, L, O, U, so a
#: key read aloud at an event cannot be mistranscribed into a different valid
#: one.
_ALPHABET = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"
_GROUPS = 4
_GROUP_LEN = 5

KEY_PATTERN = re.compile(r"^RC5(?:-[0-9A-HJKMNP-TV-Z]{5}){4}$")

#: 20 random characters from a 32-symbol alphabet = 100 bits of entropy.
KEY_ENTROPY_BITS = _GROUPS * _GROUP_LEN * 5


def new_license_key() -> str:
    """A fresh, unguessable key. `secrets`, never `random`."""
    groups = [
        "".join(secrets.choice(_ALPHABET) for _ in range(_GROUP_LEN))
        for _ in range(_GROUPS)
    ]
    return "RC5-" + "-".join(groups)


def normalise_key(key: str) -> str:
    """Upper-case and strip, so a customer's transcription still validates."""
    return key.strip().upper().replace(" ", "")


def hash_key(key: str, *, pepper: bytes) -> str:
    """What the server stores. The plaintext key is never persisted.

    `pepper` is a server-side secret that lives in the service environment and
    NEVER in the EX5 — a distributed binary is an untrusted client and must not
    carry anything that would let a holder mint or verify keys offline.
    """
    return hmac.new(
        pepper, normalise_key(key).encode("ascii"), hashlib.sha256
    ).hexdigest()


def verify_key(key: str, key_hash: str, *, pepper: bytes) -> bool:
    """Constant-time comparison, so timing cannot be used to walk a key."""
    return hmac.compare_digest(hash_key(key, pepper=pepper), key_hash)


def mask_key(key: str) -> str:
    """The ONLY form that may be logged, printed or put in a support ticket.

    `RC5-ABCDE-FGHIJ-KLMNO-PQRST` -> `RC5-ABCDE-***-PQRST`
    """
    key = normalise_key(key)
    parts = key.split("-")
    if len(parts) < 3:
        return "RC5-****"
    return f"{parts[0]}-{parts[1]}-***-{parts[-1]}"
