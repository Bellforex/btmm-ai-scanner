"""Scanner source pin.

The bot consumes the scanner; it must never silently run against a scanner
it was not built for. ``PINNED_SCANNER_COMMIT`` names the scanner commit this
bot integrates, and ``PINNED_SOURCE_DIGEST`` is a content fingerprint of the
scanner sources at that commit. At startup the engine recomputes the
fingerprint over the source files the Python process ACTUALLY imports and
refuses to run when it differs (``ScannerPinMismatchError``), unless the
caller passes an explicit override, which is recorded in the journals.

Fingerprint (``SCANNER_FINGERPRINT_VERSION``):

* files: every ``*.py`` under the imported ``btmm_ai_scanner`` package
  (``__pycache__`` excluded), plus the replay modules in ``REPLAY_MODULES``
  (the orchestration the adapter calls and everything it pulls in from
  ``tests/parity_support``);
* each file is named by its repo-relative path (``src/btmm_ai_scanner/...``,
  ``tests/parity_support/...``) and hashed as a git blob of its content with
  ``CRLF`` normalized to ``LF`` — i.e. exactly the blob id git stores for it,
  independent of ``core.autocrlf`` and of where the checkout lives;
* digest = sha256 over ``"<version>\\n"`` then ``"<path> <blob_sha1>\\n"`` per
  file in path order.

Because the blob ids are git's own, the pinned digest can be re-derived from
``git ls-tree -r <commit>`` with no checkout at all (``tests/bot`` does so).
The check works in any worktree and does not need git at runtime.
"""

from __future__ import annotations

import hashlib
import importlib.util
from collections.abc import Iterable, Sequence
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

__all__ = [
    "PINNED_SCANNER_COMMIT",
    "PINNED_SOURCE_DIGEST",
    "REPLAY_MODULES",
    "SCANNER_FINGERPRINT_VERSION",
    "ScannerPin",
    "ScannerPinCheck",
    "ScannerPinMismatchError",
    "check_scanner_pin",
    "compute_source_digest",
    "evaluate_scanner_pin",
    "git_blob_sha1",
    "installed_source_blobs",
    "pinned",
    "refusal_message",
]

SCANNER_FINGERPRINT_VERSION = "BOT-SCANNER-PIN-V1"

#: rc4-market-framework head the bot integrates.
PINNED_SCANNER_COMMIT = "a15c199dc3d1b9436fa18f707aed3c51b95fa03d"
#: ``compute_source_digest`` of the fingerprinted files at that commit.
PINNED_SOURCE_DIGEST = "6d6e89c58f89d43bf1117965c90a2112c98ed6dd357d6738d6c18ad0b1718d30"

SCANNER_PACKAGE = "btmm_ai_scanner"
SCANNER_PACKAGE_REPO_PATH = "src/btmm_ai_scanner"

#: The replay orchestration the adapter drives (``tests.parity_support``).
REPLAY_MODULES: tuple[str, ...] = (
    "level_a_replay",
    "p5_active_poi_loop_model",
    "p5_atomic_capture_log",
    "p5_transport_contract",
    "p5_wire_normalized_replay",
    "p5x_capture_log",
    "p8_alert_oracle",
    "rc3_daily_authority",
    "t1_trend_pine_model",
    "t2_regime_pine_model",
    "t3_pine_model",
    "t4_pine_model",
    "t5_aggregator_pine_model",
    "t5_component_scores_pine_model",
    "t5_trend_pine_model",
    "v1a_csv_loader",
)
REPLAY_PACKAGE = "tests.parity_support"
REPLAY_REPO_DIR = "tests/parity_support"


class ScannerPinMismatchError(RuntimeError):
    """The running scanner source is not the pinned scanner source."""


@dataclass(frozen=True)
class ScannerPin:
    commit: str
    source_digest: str
    fingerprint_version: str = SCANNER_FINGERPRINT_VERSION


def pinned() -> ScannerPin:
    return ScannerPin(PINNED_SCANNER_COMMIT, PINNED_SOURCE_DIGEST)


@dataclass(frozen=True)
class ScannerPinCheck:
    pinned_commit: str
    pinned_digest: str
    observed_digest: str
    file_count: int
    #: Pin recorded when the session was created (None for a new session).
    session_pinned_digest: str | None
    matched: bool
    overridden: bool

    @property
    def status(self) -> str:
        if self.matched:
            return "MATCH"
        return "MISMATCH_OVERRIDDEN" if self.overridden else "MISMATCH_REFUSED"

    def as_dict(self) -> dict[str, Any]:
        return {**asdict(self), "status": self.status}


def git_blob_sha1(data: bytes) -> str:
    """git's blob id of ``data`` after CRLF -> LF normalization."""
    data = data.replace(b"\r\n", b"\n")
    return hashlib.sha1(b"blob %d\x00" % len(data) + data, usedforsecurity=False).hexdigest()


def compute_source_digest(blobs: Iterable[tuple[str, str]]) -> str:
    """Fold ``(repo_path, blob_sha1)`` pairs into the fingerprint digest."""
    h = hashlib.sha256(f"{SCANNER_FINGERPRINT_VERSION}\n".encode())
    for path, blob in sorted(blobs):
        h.update(f"{path} {blob}\n".encode())
    return h.hexdigest()


def _origin(module: str) -> Path:
    spec = importlib.util.find_spec(module)
    if spec is None or spec.origin is None:
        raise ScannerPinMismatchError(f"cannot locate scanner module {module!r}")
    return Path(spec.origin)


def installed_source_blobs() -> list[tuple[str, str]]:
    """``(repo_path, blob_sha1)`` for every fingerprinted file this Python
    process would import (not necessarily the files next to ``botdryrun``)."""
    package_dir = _origin(SCANNER_PACKAGE).parent
    out: list[tuple[str, str]] = []
    for path in sorted(package_dir.rglob("*.py")):
        if "__pycache__" in path.parts:
            continue
        rel = path.relative_to(package_dir).as_posix()
        out.append((f"{SCANNER_PACKAGE_REPO_PATH}/{rel}", git_blob_sha1(path.read_bytes())))
    for name in REPLAY_MODULES:
        path = _origin(f"{REPLAY_PACKAGE}.{name}")
        out.append((f"{REPLAY_REPO_DIR}/{name}.py", git_blob_sha1(path.read_bytes())))
    return out


def evaluate_scanner_pin(
    pin: ScannerPin | None = None,
    *,
    session_pinned_digest: str | None = None,
    allow_mismatch: bool = False,
    observed_blobs: Sequence[tuple[str, str]] | None = None,
) -> ScannerPinCheck:
    """Compare the running scanner source with ``pin`` (and with the pin the
    session was created under). Never raises on a mismatch; see
    ``check_scanner_pin``."""
    pin = pin or pinned()
    blobs = list(observed_blobs) if observed_blobs is not None else installed_source_blobs()
    observed = compute_source_digest(blobs)
    matched = observed == pin.source_digest and (
        session_pinned_digest is None or session_pinned_digest == pin.source_digest
    )
    return ScannerPinCheck(
        pinned_commit=pin.commit,
        pinned_digest=pin.source_digest,
        observed_digest=observed,
        file_count=len(blobs),
        session_pinned_digest=session_pinned_digest,
        matched=matched,
        overridden=(not matched) and allow_mismatch,
    )


def refusal_message(check: ScannerPinCheck) -> str:
    reasons = []
    if check.observed_digest != check.pinned_digest:
        reasons.append(
            f"running scanner source digest {check.observed_digest[:16]}... != pinned "
            f"{check.pinned_digest[:16]}... (commit {check.pinned_commit})"
        )
    if (
        check.session_pinned_digest is not None
        and check.session_pinned_digest != check.pinned_digest
    ):
        reasons.append(
            f"session was created under scanner digest {check.session_pinned_digest[:16]}..., "
            f"this bot pins {check.pinned_digest[:16]}..."
        )
    return (
        "scanner pin mismatch: "
        + "; ".join(reasons)
        + ". Refusing to run. Check out the pinned scanner commit, or pass "
        "--allow-scanner-mismatch (recorded in the journals) to override."
    )


def check_scanner_pin(
    pin: ScannerPin | None = None,
    *,
    session_pinned_digest: str | None = None,
    allow_mismatch: bool = False,
    observed_blobs: Sequence[tuple[str, str]] | None = None,
) -> ScannerPinCheck:
    """``evaluate_scanner_pin`` that raises ``ScannerPinMismatchError`` on a
    mismatch unless ``allow_mismatch``."""
    check = evaluate_scanner_pin(
        pin,
        session_pinned_digest=session_pinned_digest,
        allow_mismatch=allow_mismatch,
        observed_blobs=observed_blobs,
    )
    if check.status == "MISMATCH_REFUSED":
        raise ScannerPinMismatchError(refusal_message(check))
    return check
