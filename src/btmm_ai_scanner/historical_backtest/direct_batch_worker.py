"""Isolated direct-batch verification worker (register §44AN).

Private module, no public export. Runs the **unchanged** direct-batch scanner
oracle (`scan_market`) in a **separate** Python process — never inside the
incremental historical replay's own process — so a full-dataset oracle call can
be bounded by a hard working-set ceiling and a wall-clock timeout, and killed
before it can exhaust the host, exactly the failure mode that forced the
original manual replay termination.

Scope (register §44AS, this phase): this module owns only the worker itself and
its parent-side orchestration (spawn, monitor, terminate, validate, clean up).
It performs **no** report publication and touches **no** CLI/execution wiring;
those consume the returned `_DirectBatchVerificationOutcome` in a later phase.
The parent-enforced 4 GB host-RAM floor (register §44AF) is likewise a
run-level gate belonging to that later execution wiring — this worker enforces
only its own child's 6 GB ceiling and the 90-minute timeout (§44AN).

Worker outcome status is one of exactly five values (§44AN): ``SUCCESS``,
``TIMEOUT``, ``MEMORY_CEILING_EXCEEDED``, ``CRASHED``, ``CORRUPTED``. Semantic /
identity / fingerprint comparison against the incremental engine is the later
execution layer's responsibility, not this worker's — the worker only produces
the deterministic final snapshot plus a content checksum from which that layer
decides whether report publication is permitted.

Environmental measurements recorded here (peak working set, elapsed seconds) are
**operational metadata only** and never participate in any scanner semantic
identity, content fingerprint, or deterministic detection output (§44Z).
"""

from __future__ import annotations

import hashlib
import json
import multiprocessing
import os
import shutil
import sys
import tempfile
import time
import traceback
from collections.abc import Callable
from contextlib import redirect_stderr, redirect_stdout
from dataclasses import dataclass, replace
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING

from btmm_ai_scanner.btmm.reviewed_evidence import BtmmReviewedEvidence
from btmm_ai_scanner.config.enums import Timeframe
from btmm_ai_scanner.contracts.normalized_candle import NormalizedCandle
from btmm_ai_scanner.historical_backtest import process_metrics
from btmm_ai_scanner.historical_backtest.identity import (
    ContentAddressedIdentityProvider,
)
from btmm_ai_scanner.scanner.analyzer import scan_market
from btmm_ai_scanner.scanner.configuration import (
    ScannerConfiguration,
    validate_configuration,
)
from btmm_ai_scanner.scanner.timeframe_input import ScannerTimeframeInput

if TYPE_CHECKING:
    from multiprocessing.process import BaseProcess

# Author-approved gates (§44AF/§44AN, AUTHOR-APPROVED + ENGINEERING-PROVISIONAL).
_DEFAULT_TIMEOUT_SECONDS = 5400.0
_DEFAULT_MEMORY_CEILING_BYTES = 6 * 1024**3
_DEFAULT_MONITOR_INTERVAL_SECONDS = 5.0

# Worker exit codes (§44AN): the child self-reports only these; timeout and
# memory-ceiling events are detected and enforced by the parent instead.
_WORKER_EXIT_SUCCESS = 0
_WORKER_EXIT_CRASH = 1
_WORKER_EXIT_CORRUPTED_REQUEST = 2

_TEMP_DIR_PREFIX = "btmm_direct_batch_"
_REQUEST_FILENAME = "request.json"
_RESPONSE_FILENAME = "response.json"
_LOG_FILENAME = "worker.log"
_PRESERVED_LOG_PREFIX = "btmm_direct_batch_log_"


class DirectBatchVerificationStatus(Enum):
    """The exactly-five worker outcome statuses (register §44AN)."""

    SUCCESS = "SUCCESS"
    TIMEOUT = "TIMEOUT"
    MEMORY_CEILING_EXCEEDED = "MEMORY_CEILING_EXCEEDED"
    CRASHED = "CRASHED"
    CORRUPTED = "CORRUPTED"


@dataclass(frozen=True)
class _DirectBatchVerificationOutcome:
    """Parent-side result of one isolated verification attempt.

    ``final_snapshot_json`` and ``checksum`` are populated **only** on
    ``SUCCESS`` — every other status leaves them ``None`` so a partial or
    untrusted worker result can never masquerade as a verified one.
    ``preserved_log_path`` points at a copied-out worker log on any non-success
    outcome (§44AN cleanup rule); it is ``None`` on success.
    """

    status: DirectBatchVerificationStatus
    final_snapshot_json: dict[str, object] | None
    checksum: str | None
    elapsed_seconds: float
    peak_working_set_bytes: int | None
    preserved_log_path: str | None


def _canonical_json_bytes(value: object) -> bytes:
    """Deterministic, key-sorted, compact JSON encoding — the single canonical
    form used for both the on-disk request and the response checksum (§44AN)."""
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")


def _snapshot_checksum(final_snapshot_json: object) -> str:
    """SHA-256 of the canonical JSON dump of a final snapshot (§44AN)."""
    return hashlib.sha256(_canonical_json_bytes(final_snapshot_json)).hexdigest()


def _serialize_request(
    historical_inputs: tuple[ScannerTimeframeInput, ...],
    reviewed_evidence: tuple[BtmmReviewedEvidence, ...],
    scanner_configuration: ScannerConfiguration,
) -> dict[str, object]:
    """Build the JSON-safe worker request (§44AN). ``identity_provider`` is
    deliberately **not** serialized — the worker constructs a fresh, stateless
    ``ContentAddressedIdentityProvider`` itself, since it is deterministic by
    construction and independent of call order."""
    return {
        "historical_inputs": [
            {
                "timeframe": bundle.timeframe.value,
                "candles": [
                    candle.model_dump(mode="json") for candle in bundle.candles
                ],
            }
            for bundle in historical_inputs
        ],
        "reviewed_evidence": [
            evidence.model_dump(mode="json") for evidence in reviewed_evidence
        ],
        "scanner_configuration": scanner_configuration.model_dump(mode="json"),
    }


def _deserialize_request(
    payload: dict[str, object],
) -> tuple[
    tuple[ScannerTimeframeInput, ...],
    tuple[BtmmReviewedEvidence, ...],
    ScannerConfiguration,
]:
    """Reconstruct the strict contract models from a worker request.

    Reconstruction goes through pydantic's JSON wire mode
    (``model_validate_json``) rather than ``model_validate``: the contract
    models are ``strict=True``, so the JSON-mode dict (string Decimals, ISO
    datetimes, list-encoded frozensets) must be re-parsed as JSON, not fed as
    native Python objects."""
    raw_inputs = payload["historical_inputs"]
    raw_evidence = payload["reviewed_evidence"]
    raw_configuration = payload["scanner_configuration"]
    if not isinstance(raw_inputs, list) or not isinstance(raw_evidence, list):
        raise ValueError("worker request has malformed input collections.")

    historical_inputs = tuple(
        ScannerTimeframeInput(
            timeframe=Timeframe(bundle["timeframe"]),
            candles=tuple(
                NormalizedCandle.model_validate_json(json.dumps(candle))
                for candle in bundle["candles"]
            ),
        )
        for bundle in raw_inputs
    )
    reviewed_evidence = tuple(
        BtmmReviewedEvidence.model_validate_json(json.dumps(evidence))
        for evidence in raw_evidence
    )
    scanner_configuration = ScannerConfiguration.model_validate_json(
        json.dumps(raw_configuration)
    )
    return historical_inputs, reviewed_evidence, scanner_configuration


def _atomic_write_json(path: Path, payload: object) -> None:
    """Write ``payload`` to a sibling ``*.partial`` file, then atomically rename
    it into place — the final path only ever exists as a complete file, so a
    partial worker result can never masquerade as a finished one (§44AN)."""
    partial = path.with_name(path.name + ".partial")
    partial.write_text(
        json.dumps(payload, separators=(",", ":"), ensure_ascii=False),
        encoding="utf-8",
    )
    os.replace(partial, path)


def _direct_batch_worker_entrypoint(request_path: str, response_path: str) -> None:
    """Subprocess entry point (§44AN): read the request, run the unchanged
    direct-batch oracle, write the validated response, exit.

    Exit codes: ``0`` success; ``2`` corrupted/unreadable request; any unhandled
    computation error propagates and multiprocessing records exit ``1`` (crash).
    stdout/stderr are redirected to a sibling ``worker.log`` for the whole run so
    worker output never interleaves with the parent's."""
    temp_dir = Path(response_path).parent
    log_path = temp_dir / _LOG_FILENAME
    with (
        log_path.open("w", encoding="utf-8") as log_file,
        redirect_stdout(log_file),
        redirect_stderr(log_file),
    ):
        try:
            payload = json.loads(Path(request_path).read_text(encoding="utf-8"))
            historical_inputs, reviewed_evidence, scanner_configuration = (
                _deserialize_request(payload)
            )
        except Exception:
            traceback.print_exc()
            log_file.flush()
            sys.exit(_WORKER_EXIT_CORRUPTED_REQUEST)

        start = time.monotonic()
        analysis = scan_market(
            historical_inputs,
            reviewed_evidence,
            scanner_configuration,
            ContentAddressedIdentityProvider(),
        )
        elapsed = time.monotonic() - start

        final_snapshot_json = analysis.model_dump(mode="json")
        response = {
            "status": DirectBatchVerificationStatus.SUCCESS.value,
            "final_snapshot_json": final_snapshot_json,
            "elapsed_seconds": elapsed,
            "peak_working_set_bytes": process_metrics.peak_working_set_bytes(),
            "checksum": _snapshot_checksum(final_snapshot_json),
        }
        _atomic_write_json(Path(response_path), response)
        log_file.flush()


def _terminate_process(process: BaseProcess) -> None:
    """Hard-terminate a worker and wait for it, escalating to ``kill`` if the
    process ignores the first signal — leaving no orphaned worker behind.

    The isolated worker spawns no descendants (register §44AN), so terminating
    the single process terminates its whole tree; ``terminate`` maps to
    ``TerminateProcess`` on Windows and ``SIGTERM`` on POSIX."""
    process.terminate()
    process.join(timeout=5.0)
    if process.is_alive():
        process.kill()
        process.join(timeout=5.0)


def _spawn_and_monitor(
    process: BaseProcess,
    timeout_seconds: float,
    memory_ceiling_bytes: int,
    monitor_interval_seconds: float,
) -> tuple[DirectBatchVerificationStatus | None, float, int | None]:
    """Start ``process`` and monitor its OS-reported working set on a monotonic
    clock until it exits or breaches a gate.

    Returns ``(terminal_status, elapsed_seconds, peak_working_set_bytes)`` where
    ``terminal_status`` is ``TIMEOUT``/``MEMORY_CEILING_EXCEEDED`` if the parent
    terminated the child, or ``None`` if the child exited on its own."""
    process.start()
    start = time.monotonic()
    peak_working_set: int | None = None
    terminal_status: DirectBatchVerificationStatus | None = None

    while process.is_alive():
        working_set = process_metrics.current_working_set_bytes(process.pid)
        if working_set is not None:
            peak_working_set = (
                working_set
                if peak_working_set is None
                else max(peak_working_set, working_set)
            )
            if working_set > memory_ceiling_bytes:
                terminal_status = DirectBatchVerificationStatus.MEMORY_CEILING_EXCEEDED
                break
        if time.monotonic() - start >= timeout_seconds:
            terminal_status = DirectBatchVerificationStatus.TIMEOUT
            break
        # join doubles as the poll sleep: it returns early the instant the child
        # exits, so a fast worker is not held back by the monitor interval.
        process.join(timeout=monitor_interval_seconds)

    if terminal_status is not None:
        _terminate_process(process)
    process.join()
    elapsed = time.monotonic() - start
    return terminal_status, elapsed, peak_working_set


def _read_response(response_path: Path) -> dict[str, object] | None:
    """Read and JSON-parse a worker response, or ``None`` if it is absent or
    unreadable (treated as an untrusted result by the caller)."""
    try:
        parsed = json.loads(response_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return parsed if isinstance(parsed, dict) else None


def _preserve_log(log_path: Path) -> str | None:
    """Copy a worker log out of its soon-to-be-deleted temp directory so it
    survives cleanup for diagnostics (§44AN); ``None`` if there is no log."""
    if not log_path.exists():
        return None
    handle, preserved = tempfile.mkstemp(prefix=_PRESERVED_LOG_PREFIX, suffix=".log")
    os.close(handle)
    shutil.copyfile(log_path, preserved)
    return preserved


def _classify_completed_worker(
    process: BaseProcess,
    response_path: Path,
    elapsed_seconds: float,
    peak_working_set_bytes: int | None,
) -> _DirectBatchVerificationOutcome:
    """Classify a worker that exited on its own (not parent-terminated) into a
    ``SUCCESS``/``CRASHED``/``CORRUPTED`` outcome, validating the response
    checksum before ever trusting a claimed ``SUCCESS`` (§44AN)."""
    if process.exitcode != _WORKER_EXIT_SUCCESS:
        return _DirectBatchVerificationOutcome(
            status=DirectBatchVerificationStatus.CRASHED,
            final_snapshot_json=None,
            checksum=None,
            elapsed_seconds=elapsed_seconds,
            peak_working_set_bytes=peak_working_set_bytes,
            preserved_log_path=None,
        )

    response = _read_response(response_path)
    final_snapshot_json = (
        None if response is None else response.get("final_snapshot_json")
    )
    claimed_checksum = None if response is None else response.get("checksum")
    corrupted = (
        response is None
        or response.get("status") != DirectBatchVerificationStatus.SUCCESS.value
        or not isinstance(final_snapshot_json, dict)
        or not isinstance(claimed_checksum, str)
        or _snapshot_checksum(final_snapshot_json) != claimed_checksum
    )
    if corrupted:
        return _DirectBatchVerificationOutcome(
            status=DirectBatchVerificationStatus.CORRUPTED,
            final_snapshot_json=None,
            checksum=None,
            elapsed_seconds=elapsed_seconds,
            peak_working_set_bytes=peak_working_set_bytes,
            preserved_log_path=None,
        )

    assert isinstance(final_snapshot_json, dict)
    assert isinstance(claimed_checksum, str)
    reported_peak = response.get("peak_working_set_bytes") if response else None
    return _DirectBatchVerificationOutcome(
        status=DirectBatchVerificationStatus.SUCCESS,
        final_snapshot_json=final_snapshot_json,
        checksum=claimed_checksum,
        elapsed_seconds=elapsed_seconds,
        peak_working_set_bytes=(
            reported_peak if isinstance(reported_peak, int) else peak_working_set_bytes
        ),
        preserved_log_path=None,
    )


def _run_isolated_direct_batch_verification(
    historical_inputs: tuple[ScannerTimeframeInput, ...],
    reviewed_evidence: tuple[BtmmReviewedEvidence, ...],
    scanner_configuration: ScannerConfiguration,
    timeout_seconds: float = _DEFAULT_TIMEOUT_SECONDS,
    memory_ceiling_bytes: int = _DEFAULT_MEMORY_CEILING_BYTES,
    monitor_interval_seconds: float = _DEFAULT_MONITOR_INTERVAL_SECONDS,
    *,
    worker_entrypoint: Callable[[str, str], None] = _direct_batch_worker_entrypoint,
) -> _DirectBatchVerificationOutcome:
    """Parent-side orchestration of one isolated direct-batch verification.

    Validates the configuration, spawns the worker (``spawn`` context, for a
    clean cross-platform memory footprint), monitors it against the working-set
    ceiling and timeout, validates the response checksum, preserves the log on
    any non-success outcome, and unconditionally deletes the temp directory.

    ``worker_entrypoint`` is a private test seam so the deterministic synthetic
    workers below can exercise the timeout / memory-ceiling / crash / corrupted
    paths; production always uses the default real entry point."""
    validate_configuration(scanner_configuration)

    temp_dir = Path(tempfile.mkdtemp(prefix=_TEMP_DIR_PREFIX))
    request_path = temp_dir / _REQUEST_FILENAME
    response_path = temp_dir / _RESPONSE_FILENAME
    log_path = temp_dir / _LOG_FILENAME
    try:
        _atomic_write_json(
            request_path,
            _serialize_request(
                historical_inputs, reviewed_evidence, scanner_configuration
            ),
        )
        context = multiprocessing.get_context("spawn")
        process = context.Process(
            target=worker_entrypoint,
            args=(str(request_path), str(response_path)),
        )
        terminal_status, elapsed, peak = _spawn_and_monitor(
            process,
            timeout_seconds,
            memory_ceiling_bytes,
            monitor_interval_seconds,
        )
        if terminal_status is not None:
            outcome = _DirectBatchVerificationOutcome(
                status=terminal_status,
                final_snapshot_json=None,
                checksum=None,
                elapsed_seconds=elapsed,
                peak_working_set_bytes=peak,
                preserved_log_path=None,
            )
        else:
            outcome = _classify_completed_worker(process, response_path, elapsed, peak)

        if outcome.status is not DirectBatchVerificationStatus.SUCCESS:
            outcome = replace(outcome, preserved_log_path=_preserve_log(log_path))
        return outcome
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def _report_publication_permitted(outcome: _DirectBatchVerificationOutcome) -> bool:
    """Publication gate the later execution layer applies (§44AN): a report may
    be written **only** for a ``SUCCESS`` outcome carrying a validated snapshot
    and checksum. Any incomplete verification — crash, timeout, memory-ceiling
    abort, or corrupted response — denies publication."""
    return (
        outcome.status is DirectBatchVerificationStatus.SUCCESS
        and outcome.final_snapshot_json is not None
        and outcome.checksum is not None
    )


# --- Deterministic synthetic workers (spawn-safe test support only) -----------
# These exist solely to exercise the parent monitor/termination/classification
# paths deterministically. `spawn` re-imports the target's module in the child,
# and pytest's importlib mode makes test-module functions unreachable there, so
# these live in this always-importable module. None participates in production
# verification, which always uses `_direct_batch_worker_entrypoint`.


def _synthetic_sleep_worker(request_path: str, response_path: str) -> None:
    """Never writes a response; sleeps until the parent terminates it — drives
    the ``TIMEOUT`` path."""
    time.sleep(3600.0)


def _synthetic_memory_growth_worker(request_path: str, response_path: str) -> None:
    """Grows resident memory without bound until terminated — drives the
    ``MEMORY_CEILING_EXCEEDED`` path."""
    blocks: list[bytearray] = []
    while True:
        blocks.append(bytearray(20_000_000))
        time.sleep(0.02)


def _synthetic_crash_worker(request_path: str, response_path: str) -> None:
    """Exits non-zero without writing a response — drives the ``CRASHED`` path."""
    os._exit(_WORKER_EXIT_CRASH)


_SYNTHETIC_LOG_MARKER = "synthetic-worker-diagnostic-line"


def _synthetic_logging_crash_worker(request_path: str, response_path: str) -> None:
    """Writes a diagnostic line to the worker log (exactly as the real entry
    point does via redirected stderr) and then exits non-zero without a
    response — drives the ``CRASHED`` path *with* a log to preserve."""
    log_path = Path(response_path).parent / _LOG_FILENAME
    with log_path.open("w", encoding="utf-8") as log_file:
        log_file.write(_SYNTHETIC_LOG_MARKER + "\n")
        log_file.flush()
    os._exit(_WORKER_EXIT_CRASH)


def _synthetic_corrupt_response_worker(request_path: str, response_path: str) -> None:
    """Writes a ``SUCCESS`` response whose checksum does not match its payload —
    drives the ``CORRUPTED`` path."""
    _atomic_write_json(
        Path(response_path),
        {
            "status": DirectBatchVerificationStatus.SUCCESS.value,
            "final_snapshot_json": {"tampered": True},
            "elapsed_seconds": 0.0,
            "peak_working_set_bytes": None,
            "checksum": "0" * 64,
        },
    )
