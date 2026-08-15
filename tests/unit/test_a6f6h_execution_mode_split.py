"""A6-F6H: the batch HISTORICAL_FINAL_ONLY + incremental streaming execution-mode
split.

Proves the routing table, that FINAL_ONLY historical execution drives the
isolated batch worker under the 120-minute EMPIRICALLY-CALIBRATED ceiling (6 GB
worker / 4 GB host floor unchanged), that ALL / CHANGED_ONLY remain the
incremental kernel, and -- the semantic crux -- that the batch-derived event
ledger equals the incremental kernel's ``event_ledger()`` on bounded prefixes
(so batch may own the historical job without weakening any lifecycle/ledger
guarantee).
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

import pytest

from btmm_ai_scanner.btmm.configuration import BtmmConfiguration
from btmm_ai_scanner.config.enums import InternalSymbol, Timeframe
from btmm_ai_scanner.contracts.normalized_candle import NormalizedCandle
from btmm_ai_scanner.contracts.raw_candle import CandleCompleteness, CandleVolumeKind
from btmm_ai_scanner.contracts.types import SemVer
from btmm_ai_scanner.domain.configuration import MarketMeasurementConfiguration
from btmm_ai_scanner.domain.enums import DerivedOutputType
from btmm_ai_scanner.historical_backtest import execution as execution_module
from btmm_ai_scanner.historical_backtest.direct_batch_worker import (
    DirectBatchVerificationStatus,
    _DirectBatchVerificationOutcome,
)
from btmm_ai_scanner.historical_backtest.execution import (
    _HISTORICAL_FINAL_ONLY_TIMEOUT_SECONDS,
    _HISTORICAL_WORKER_MEMORY_CEILING_BYTES,
    HistoricalExecutionMode,
    resolve_historical_execution_mode,
)
from btmm_ai_scanner.poi.configuration import PoiConfiguration
from btmm_ai_scanner.scanner.analyzer import scan_market
from btmm_ai_scanner.scanner.configuration import ScannerConfiguration
from btmm_ai_scanner.scanner.enums import SnapshotRetentionPolicy
from btmm_ai_scanner.scanner.replay import IncrementalReplayKernel
from btmm_ai_scanner.scanner.timeframe_input import ScannerTimeframeInput
from btmm_ai_scanner.structure.configuration import StructureConfiguration

_BASE = datetime(2024, 1, 1, tzinfo=UTC)
_RAW = UUID("0193f450-1234-7abc-8def-abcdefabcdaa")
_PROV = UUID("0193f450-1234-7abc-8def-abcdefabcdff")


class _Ident:
    def identify(
        self, *, output_type: DerivedOutputType, semantic_key: tuple[str, ...]
    ) -> UUID:
        import hashlib

        d = hashlib.sha256(
            (output_type.value + "|" + "|".join(semantic_key)).encode()
        ).digest()[:16]
        v = int.from_bytes(d, "big")
        v &= ~(0xF << 76)
        v |= 7 << 76
        v &= ~(0x3 << 62)
        v |= 0x2 << 62
        return UUID(int=v)


def _config() -> ScannerConfiguration:
    return ScannerConfiguration(
        measurement_configuration=MarketMeasurementConfiguration(
            minimum_price_tick=Decimal("0.01")
        ),
        structure_configuration=StructureConfiguration(),
        poi_configuration=PoiConfiguration(minimum_price_tick=Decimal("0.01")),
        btmm_configuration=BtmmConfiguration(minimum_price_tick=Decimal("0.01")),
    )


def _single_m15_config() -> ScannerConfiguration:
    # scan_market defaults to requiring M1/M5/M15; the ledger-equality comparison
    # is single-timeframe, so require only M15 (mirrors the kernel construction).
    return ScannerConfiguration(
        measurement_configuration=MarketMeasurementConfiguration(
            minimum_price_tick=Decimal("0.01")
        ),
        structure_configuration=StructureConfiguration(),
        poi_configuration=PoiConfiguration(minimum_price_tick=Decimal("0.01")),
        btmm_configuration=BtmmConfiguration(minimum_price_tick=Decimal("0.01")),
        required_timeframes=frozenset({Timeframe.M15}),
        optional_timeframes=frozenset(),
    )


def _gold_m15(n: int) -> list[NormalizedCandle]:
    import random

    rng = random.Random(20260813)
    price = 2000.0
    out: list[NormalizedCandle] = []
    for i in range(n):
        o = price
        c = o + rng.uniform(-2.5, 2.5)
        h = max(o, c) + rng.uniform(0, 1.5)
        low = min(o, c) - rng.uniform(0, 1.5)
        event = _BASE + timedelta(minutes=15 * i)
        avail = event + timedelta(seconds=1)
        out.append(
            NormalizedCandle.model_validate(
                {
                    "record_id": UUID(f"0193f450-1234-7abc-8def-{i:012x}"),
                    "content_fingerprint": "a" * 64,
                    "raw_candle_id": _RAW,
                    "provider": "FXCM",
                    "source_reference": "fxcm-xauusd-m15",
                    "source_symbol": "XAUUSD",
                    "source_timeframe": Timeframe.M15.value,
                    "symbol": InternalSymbol.XAUUSD,
                    "timeframe": Timeframe.M15,
                    "event_time_utc": event,
                    "availability_time_utc": avail,
                    "processing_time_utc": avail,
                    "original_event_time": event,
                    "original_availability_time": avail,
                    "original_timezone": "UTC",
                    "open": Decimal(str(round(o, 2))),
                    "high": Decimal(str(round(h, 2))),
                    "low": Decimal(str(round(low, 2))),
                    "close": Decimal(str(round(c, 2))),
                    "volume": Decimal("10"),
                    "volume_kind": CandleVolumeKind.TICK,
                    "completeness": CandleCompleteness.CONFIRMED_COMPLETE,
                    "rule_version": SemVer.parse("0.1.0"),
                    "contract_version": SemVer.parse("0.1.0"),
                    "schema_version": SemVer.parse("0.1.0"),
                    "provenance_id": _PROV,
                }
            )
        )
        price = c
    return out


def test_resolve_historical_execution_mode_routing_table() -> None:
    assert (
        resolve_historical_execution_mode(SnapshotRetentionPolicy.FINAL_ONLY)
        is HistoricalExecutionMode.BATCH_HISTORICAL_FINAL_ONLY
    )
    assert (
        resolve_historical_execution_mode(SnapshotRetentionPolicy.ALL)
        is HistoricalExecutionMode.INCREMENTAL_STREAMING
    )
    assert (
        resolve_historical_execution_mode(SnapshotRetentionPolicy.CHANGED_ONLY)
        is HistoricalExecutionMode.INCREMENTAL_STREAMING
    )


def test_final_only_batch_execution_uses_120_minute_worker_gate(
    monkeypatch: pytest.MonkeyPatch, tmp_path: object
) -> None:
    """The authoritative FINAL_ONLY batch path must call the isolated worker with
    the 120-minute (7200 s) EMPIRICALLY-CALIBRATED timeout and the 6 GB working-
    set ceiling -- not the streaming path's 90-minute gate."""
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path("tests/unit").resolve()))
    import test_historical_cli as cli_fixtures

    dataset_root = Path(str(tmp_path)) / "dataset"
    dataset_root.mkdir()
    cli_fixtures._build_valid_dataset(dataset_root)
    from btmm_ai_scanner.historical_backtest.configuration import (
        HistoricalDatasetConfiguration,
    )
    from btmm_ai_scanner.historical_backtest.execution import (
        execute_scanner_backtest_batch_historical,
    )
    from btmm_ai_scanner.historical_backtest.loader import load_historical_dataset

    dataset = load_historical_dataset(dataset_root, HistoricalDatasetConfiguration())

    captured: dict[str, object] = {}
    real = execution_module._run_isolated_direct_batch_verification  # type: ignore[attr-defined]

    def _recording(
        inputs: tuple[ScannerTimeframeInput, ...],
        evidence: tuple[object, ...],
        config: ScannerConfiguration,
        timeout_seconds: float,
        memory_ceiling_bytes: int,
        *args: object,
        **kwargs: object,
    ) -> _DirectBatchVerificationOutcome:
        captured["timeout_seconds"] = timeout_seconds
        captured["memory_ceiling_bytes"] = memory_ceiling_bytes
        return real(inputs, evidence, config, timeout_seconds, memory_ceiling_bytes)  # type: ignore[arg-type]

    monkeypatch.setattr(
        execution_module, "_run_isolated_direct_batch_verification", _recording
    )
    result = execute_scanner_backtest_batch_historical(dataset, _config())

    assert captured["timeout_seconds"] == _HISTORICAL_FINAL_ONLY_TIMEOUT_SECONDS
    assert captured["timeout_seconds"] == 7200.0
    assert captured["memory_ceiling_bytes"] == _HISTORICAL_WORKER_MEMORY_CEILING_BYTES
    assert captured["memory_ceiling_bytes"] == 6 * 1024**3
    # The batch result is authoritative: verified, no cross-engine mismatch step.
    assert result.per_symbol_replay_results[0].direct_batch_verified is True
    assert result.per_symbol_replay_results[0].detection_mismatches == ()


def test_batch_execution_denies_result_when_worker_not_success(
    monkeypatch: pytest.MonkeyPatch, tmp_path: object
) -> None:
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path("tests/unit").resolve()))
    import test_historical_cli as cli_fixtures

    dataset_root = Path(str(tmp_path)) / "dataset"
    dataset_root.mkdir()
    cli_fixtures._build_valid_dataset(dataset_root)
    from btmm_ai_scanner.historical_backtest.configuration import (
        HistoricalDatasetConfiguration,
    )
    from btmm_ai_scanner.historical_backtest.execution import (
        HistoricalBatchExecutionError,
        execute_scanner_backtest_batch_historical,
    )
    from btmm_ai_scanner.historical_backtest.loader import load_historical_dataset

    dataset = load_historical_dataset(dataset_root, HistoricalDatasetConfiguration())

    def _timeout(*args: object, **kwargs: object) -> _DirectBatchVerificationOutcome:
        return _DirectBatchVerificationOutcome(
            status=DirectBatchVerificationStatus.TIMEOUT,
            final_snapshot_json=None,
            checksum=None,
            elapsed_seconds=0.0,
            peak_working_set_bytes=None,
            preserved_log_path=None,
        )

    monkeypatch.setattr(
        execution_module, "_run_isolated_direct_batch_verification", _timeout
    )
    with pytest.raises(HistoricalBatchExecutionError):
        execute_scanner_backtest_batch_historical(dataset, _config())


def _batch_ledger_families(analysis: object) -> dict[str, tuple[object, ...]]:
    """Flatten the batch ScannerAnalysis into the same classification-A record
    families the incremental event ledger accumulates (single-timeframe here)."""
    m = analysis.measurement_analyses[0]  # type: ignore[attr-defined]
    s = analysis.structure_analyses[0]  # type: ignore[attr-defined]
    poi = analysis.poi_analysis  # type: ignore[attr-defined]
    btmm = analysis.btmm_analysis  # type: ignore[attr-defined]
    return {
        "confirmed_swings": m.confirmed_swings,
        "displacement_observations": m.displacement_observations,
        "equal_level_clusters": m.equal_level_clusters,
        "support_resistance_zones": m.support_resistance_zones,
        "trendlines": m.trendlines,
        "structure_transitions": s.structure_transitions,
        "poi_observations": poi.poi_observations,
        "poi_lifecycle_transitions": poi.poi_lifecycle_transitions,
        "btmm_observations": btmm.btmm_observations,
        "btmm_lifecycle_transitions": btmm.btmm_lifecycle_transitions,
    }


@pytest.mark.parametrize("prefix", [80, 160, 240])
def test_batch_derived_ledger_equals_incremental_ledger_on_bounded_prefixes(
    prefix: int,
) -> None:
    """The semantic crux of A6-F6H: the event ledger the incremental kernel
    exposes at a bounded prefix is byte-identical to the ledger derivable from
    the batch ``scan_market`` over the same prefix -- so the batch engine may own
    the historical job without losing any lifecycle/ledger record."""
    candles = _gold_m15(prefix)
    inputs = (ScannerTimeframeInput(timeframe=Timeframe.M15, candles=tuple(candles)),)
    config = _single_m15_config()

    # Incremental kernel ledger.
    kernel = IncrementalReplayKernel((Timeframe.M15,), config, _Ident(), ())
    for candle in candles:
        kernel.advance_group({Timeframe.M15: (candle,)})
    kernel.finalize()
    ledger = kernel.event_ledger()

    # Batch scan_market over the same prefix.
    batch = scan_market(inputs, (), config, _Ident())
    batch_families = _batch_ledger_families(batch)

    for name, batch_records in batch_families.items():
        incremental_records = getattr(ledger, name)
        assert incremental_records == batch_records, name
