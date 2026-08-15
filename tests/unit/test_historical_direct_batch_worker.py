"""Permanent tests for the isolated direct-batch verification worker (§44AN).

Exactly the seven register-approved top-level tests (§44AR), in the approved
order. All fixtures are tiny synthetic candles — never genuine XAUUSD — and the
termination / crash / corruption paths are driven by the module's own
spawn-safe synthetic workers so no real full-dataset oracle call is required.
"""

import tempfile
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from uuid import UUID

from btmm_ai_scanner.btmm.configuration import BtmmConfiguration
from btmm_ai_scanner.config.enums import InternalSymbol, Timeframe
from btmm_ai_scanner.contracts.normalized_candle import NormalizedCandle
from btmm_ai_scanner.contracts.raw_candle import CandleCompleteness, CandleVolumeKind
from btmm_ai_scanner.contracts.types import SemVer
from btmm_ai_scanner.domain.configuration import MarketMeasurementConfiguration
from btmm_ai_scanner.historical_backtest import direct_batch_worker as worker
from btmm_ai_scanner.historical_backtest.direct_batch_worker import (
    _SYNTHETIC_LOG_MARKER,
    DirectBatchVerificationStatus,
    _report_publication_permitted,
    _run_isolated_direct_batch_verification,
    _snapshot_checksum,
)
from btmm_ai_scanner.historical_backtest.identity import _uuid_from_canonical_bytes
from btmm_ai_scanner.poi.configuration import PoiConfiguration
from btmm_ai_scanner.scanner.configuration import ScannerConfiguration
from btmm_ai_scanner.scanner.timeframe_input import ScannerTimeframeInput
from btmm_ai_scanner.structure.configuration import StructureConfiguration


def _uid(seed: str) -> UUID:
    return _uuid_from_canonical_bytes(seed.encode("utf-8"))


def _candle(minute_offset: int) -> NormalizedCandle:
    event_time = datetime(2024, 1, 15, 9, 30, tzinfo=UTC) + timedelta(
        minutes=minute_offset
    )
    return NormalizedCandle(
        record_id=_uid(f"record-{minute_offset}"),
        content_fingerprint="a" * 64,
        raw_candle_id=_uid(f"raw-{minute_offset}"),
        provider="FXCM",
        source_reference=f"ref-{minute_offset}",
        source_symbol="XAUUSD",
        source_timeframe="M1",
        symbol=InternalSymbol.XAUUSD,
        timeframe=Timeframe.M1,
        event_time_utc=event_time,
        availability_time_utc=event_time + timedelta(minutes=1),
        processing_time_utc=event_time + timedelta(minutes=1),
        original_event_time=event_time,
        original_availability_time=event_time + timedelta(minutes=1),
        original_timezone="UTC",
        open=Decimal("2000.00"),
        high=Decimal("2000.50"),
        low=Decimal("1999.50"),
        close=Decimal("2000.10"),
        volume=None,
        volume_kind=CandleVolumeKind.UNKNOWN,
        completeness=CandleCompleteness.CONFIRMED_COMPLETE,
        rule_version=SemVer.parse("0.1.0"),
        contract_version=SemVer.parse("0.1.0"),
        schema_version=SemVer.parse("0.1.0"),
        provenance_id=_uid("provenance"),
    )


def _configuration() -> ScannerConfiguration:
    return ScannerConfiguration(
        measurement_configuration=MarketMeasurementConfiguration(
            minimum_price_tick=Decimal("0.01")
        ),
        structure_configuration=StructureConfiguration(),
        poi_configuration=PoiConfiguration(minimum_price_tick=Decimal("0.01")),
        btmm_configuration=BtmmConfiguration(minimum_price_tick=Decimal("0.01")),
        required_timeframes=frozenset({Timeframe.M1}),
        optional_timeframes=frozenset(),
    )


def _inputs() -> tuple[ScannerTimeframeInput, ...]:
    return (
        ScannerTimeframeInput(
            timeframe=Timeframe.M1,
            candles=tuple(_candle(i) for i in range(6)),
        ),
    )


def test_direct_batch_worker_succeeds_and_returns_a_validated_checksum() -> None:
    outcome = _run_isolated_direct_batch_verification(_inputs(), (), _configuration())

    assert outcome.status is DirectBatchVerificationStatus.SUCCESS
    assert outcome.final_snapshot_json is not None
    assert outcome.checksum is not None
    # The parent's independent checksum of the returned snapshot must match the
    # worker's claimed checksum — the trust boundary of the whole verification.
    assert _snapshot_checksum(outcome.final_snapshot_json) == outcome.checksum
    assert _report_publication_permitted(outcome) is True
    assert outcome.preserved_log_path is None


def test_direct_batch_worker_times_out_and_is_terminated() -> None:
    outcome = _run_isolated_direct_batch_verification(
        _inputs(),
        (),
        _configuration(),
        timeout_seconds=1.0,
        monitor_interval_seconds=0.05,
        worker_entrypoint=worker._synthetic_sleep_worker,
    )

    assert outcome.status is DirectBatchVerificationStatus.TIMEOUT
    assert outcome.final_snapshot_json is None
    assert outcome.checksum is None
    assert _report_publication_permitted(outcome) is False


def test_direct_batch_worker_exceeding_the_memory_ceiling_is_terminated() -> None:
    outcome = _run_isolated_direct_batch_verification(
        _inputs(),
        (),
        _configuration(),
        memory_ceiling_bytes=150_000_000,
        monitor_interval_seconds=0.05,
        worker_entrypoint=worker._synthetic_memory_growth_worker,
    )

    assert outcome.status is DirectBatchVerificationStatus.MEMORY_CEILING_EXCEEDED
    assert outcome.final_snapshot_json is None
    assert _report_publication_permitted(outcome) is False


def test_direct_batch_worker_corrupted_response_is_rejected() -> None:
    outcome = _run_isolated_direct_batch_verification(
        _inputs(),
        (),
        _configuration(),
        worker_entrypoint=worker._synthetic_corrupt_response_worker,
    )

    # A claimed SUCCESS whose checksum does not match its payload is never
    # trusted — it is classified CORRUPTED and carries no publishable snapshot.
    assert outcome.status is DirectBatchVerificationStatus.CORRUPTED
    assert outcome.final_snapshot_json is None
    assert outcome.checksum is None
    assert _report_publication_permitted(outcome) is False


def test_no_report_is_published_after_incomplete_direct_batch_verification() -> None:
    outcome = _run_isolated_direct_batch_verification(
        _inputs(),
        (),
        _configuration(),
        worker_entrypoint=worker._synthetic_crash_worker,
    )

    assert outcome.status is DirectBatchVerificationStatus.CRASHED
    # The publication gate denies a report for any non-SUCCESS verification, and
    # no snapshot/checksum exists to publish even if a caller ignored the gate.
    assert _report_publication_permitted(outcome) is False
    assert outcome.final_snapshot_json is None
    assert outcome.checksum is None


def test_direct_batch_worker_temporary_files_are_cleaned_up_after_success() -> None:
    temp_root = Path(tempfile.gettempdir())
    before = set(temp_root.glob(f"{worker._TEMP_DIR_PREFIX}*"))
    outcome = _run_isolated_direct_batch_verification(_inputs(), (), _configuration())
    after = set(temp_root.glob(f"{worker._TEMP_DIR_PREFIX}*"))

    assert outcome.status is DirectBatchVerificationStatus.SUCCESS
    # The dedicated per-invocation temp directory is deleted on success, leaving
    # no request/response/log residue behind, and no log is preserved.
    assert after == before
    assert outcome.preserved_log_path is None


def test_direct_batch_worker_preserves_logs_on_failure_before_cleanup() -> None:
    outcome = _run_isolated_direct_batch_verification(
        _inputs(),
        (),
        _configuration(),
        worker_entrypoint=worker._synthetic_logging_crash_worker,
    )

    assert outcome.status is DirectBatchVerificationStatus.CRASHED
    # The temp directory is gone, but the worker's log was copied out first and
    # still contains the worker's diagnostic output.
    assert outcome.preserved_log_path is not None
    preserved = Path(outcome.preserved_log_path)
    assert preserved.exists()
    assert _SYNTHETIC_LOG_MARKER in preserved.read_text(encoding="utf-8")
    preserved.unlink()
