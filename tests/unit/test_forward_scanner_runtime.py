"""Permanent tests for the A7A forward scanner runtime foundation.

Synthetic candles only (no genuine market data). The keystone test proves the
forward runner is byte-identical to the authoritative batch ``scan_market``
oracle over the same accepted candles — the forward path adds ingestion,
grouping, journaling and alerts around the UNCHANGED scanner engine.
"""

import random
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

import pytest

from btmm_ai_scanner.btmm.configuration import BtmmConfiguration
from btmm_ai_scanner.config.enums import Timeframe
from btmm_ai_scanner.contracts.normalized_candle import NormalizedCandle
from btmm_ai_scanner.domain.configuration import MarketMeasurementConfiguration
from btmm_ai_scanner.forward import (
    AcceptedCandleJournal,
    CollectingAlertSink,
    ForwardIngestOutcome,
    ForwardScannerRunner,
    ProviderCandle,
    ScannerEventType,
    SyntheticTransport,
    build_forward_closed_candle,
)
from btmm_ai_scanner.historical_backtest.direct_batch_worker import _snapshot_checksum
from btmm_ai_scanner.historical_backtest.identity import (
    ContentAddressedIdentityProvider,
)
from btmm_ai_scanner.poi.configuration import PoiConfiguration
from btmm_ai_scanner.scanner.analysis import ScannerAnalysis
from btmm_ai_scanner.scanner.analyzer import scan_market
from btmm_ai_scanner.scanner.configuration import ScannerConfiguration
from btmm_ai_scanner.scanner.timeframe_input import ScannerTimeframeInput
from btmm_ai_scanner.structure.configuration import StructureConfiguration

_BASE = datetime(2026, 1, 1, tzinfo=UTC)
# Ingestion (processing) happens after a candle closes; a far-future constant is
# safely >= every synthetic candle's availability. processing_time_utc is
# operational metadata only — it is not part of candle identity/fingerprint nor
# any scanner semantic output, so a shared constant does not affect equivalence.
_INGEST = _BASE + timedelta(days=365)
_MINUTES = {Timeframe.M1: 1, Timeframe.M5: 5, Timeframe.M15: 15}


def _config(required: frozenset[Timeframe]) -> ScannerConfiguration:
    tick = Decimal("0.01")
    return ScannerConfiguration(
        measurement_configuration=MarketMeasurementConfiguration(
            minimum_price_tick=tick
        ),
        structure_configuration=StructureConfiguration(),
        poi_configuration=PoiConfiguration(minimum_price_tick=tick),
        btmm_configuration=BtmmConfiguration(minimum_price_tick=tick),
        required_timeframes=required,
        optional_timeframes=frozenset(),
    )


def _walk(n: int, seed: int) -> list[tuple[float, float, float, float]]:
    rng = random.Random(seed)
    price = 100.0
    out: list[tuple[float, float, float, float]] = []
    for _ in range(n):
        o = price
        c = o + rng.uniform(-1.5, 1.5)
        h = max(o, c) + rng.uniform(0, 0.8)
        low = min(o, c) - rng.uniform(0, 0.8)
        out.append((o, h, low, c))
        price = c
    return out


def _row(
    index: int,
    ohlc: tuple[float, float, float, float],
    timeframe: Timeframe,
    *,
    is_closed: bool = True,
) -> ProviderCandle:
    o, h, low, c = ohlc
    return ProviderCandle(
        provider="FXCM",
        source_symbol="XAUUSD",
        source_timeframe=timeframe.value,
        open_time_utc=_BASE + timedelta(minutes=_MINUTES[timeframe] * index),
        open=Decimal(str(o)),
        high=Decimal(str(h)),
        low=Decimal(str(low)),
        close=Decimal(str(c)),
        volume=Decimal("10"),
        is_closed=is_closed,
    )


def _rows(n: int, seed: int, timeframe: Timeframe) -> list[ProviderCandle]:
    return [_row(i, p, timeframe) for i, p in enumerate(_walk(n, seed))]


def _ingest_all(runner: ForwardScannerRunner, rows: list[ProviderCandle]) -> None:
    ingest_time = _INGEST
    for row in rows:
        runner.ingest(row, ingestion_time_utc=ingest_time)
    runner.flush()


def _batch_snapshot(
    rows: list[ProviderCandle], config: ScannerConfiguration
) -> ScannerAnalysis:
    candles_by_tf: dict[Timeframe, list[NormalizedCandle]] = {}
    for row in rows:
        candle = build_forward_closed_candle(row, ingestion_time_utc=_INGEST)
        candles_by_tf.setdefault(candle.timeframe, []).append(candle)
    bundles = tuple(
        ScannerTimeframeInput(timeframe=tf, candles=tuple(candles))
        for tf, candles in candles_by_tf.items()
    )
    return scan_market(bundles, (), config, ContentAddressedIdentityProvider())


# --------------------------------------------------------------------------
def test_provider_closed_candle_accepted() -> None:
    config = _config(frozenset({Timeframe.M15}))
    runner = ForwardScannerRunner(
        (Timeframe.M15,), config, alert_sink=CollectingAlertSink()
    )
    result = runner.ingest(_rows(1, 1, Timeframe.M15)[0], ingestion_time_utc=_INGEST)
    assert result.outcome is ForwardIngestOutcome.ACCEPTED
    assert result.record_id is not None


def test_forming_candle_rejected_and_never_fed() -> None:
    config = _config(frozenset({Timeframe.M15}))
    sink = CollectingAlertSink()
    runner = ForwardScannerRunner((Timeframe.M15,), config, alert_sink=sink)
    forming = _row(0, (100, 101, 99, 100), Timeframe.M15, is_closed=False)
    result = runner.ingest(forming, ingestion_time_utc=_INGEST)
    assert result.outcome is ForwardIngestOutcome.FORMING_REJECTED
    runner.flush()
    # nothing reached the scanner
    assert runner.finalize().poi_analysis.poi_observations == ()


def test_duplicate_candle_is_idempotent() -> None:
    config = _config(frozenset({Timeframe.M15}))
    runner = ForwardScannerRunner(
        (Timeframe.M15,), config, alert_sink=CollectingAlertSink()
    )
    row = _rows(1, 1, Timeframe.M15)[0]
    first = runner.ingest(row, ingestion_time_utc=_INGEST)
    second = runner.ingest(row, ingestion_time_utc=_INGEST)
    assert first.outcome is ForwardIngestOutcome.ACCEPTED
    assert second.outcome is ForwardIngestOutcome.EXACT_DUPLICATE


def test_conflicting_revision_quarantined_not_fed() -> None:
    config = _config(frozenset({Timeframe.M15}))
    sink = CollectingAlertSink()
    runner = ForwardScannerRunner((Timeframe.M15,), config, alert_sink=sink)
    original = _row(0, (100, 101, 99, 100), Timeframe.M15)
    revised = _row(0, (100, 102, 98, 101), Timeframe.M15)  # same identity, new OHLC
    runner.ingest(original, ingestion_time_utc=_INGEST)
    result = runner.ingest(revised, ingestion_time_utc=_INGEST)
    assert result.outcome is ForwardIngestOutcome.CONFLICTING_REVISION
    assert any(
        a.event_type is ScannerEventType.DATA_QUALITY_WARNING for a in sink.alerts
    )


def test_out_of_order_candle_rejected() -> None:
    config = _config(frozenset({Timeframe.M15}))
    runner = ForwardScannerRunner(
        (Timeframe.M15,), config, alert_sink=CollectingAlertSink()
    )
    rows = _rows(3, 5, Timeframe.M15)
    runner.ingest(rows[0], ingestion_time_utc=_INGEST)
    runner.ingest(rows[2], ingestion_time_utc=_INGEST)  # advances the group boundary
    late = runner.ingest(rows[1], ingestion_time_utc=_INGEST)  # now out of order
    assert late.outcome is ForwardIngestOutcome.OUT_OF_ORDER


def test_missing_candle_recorded_as_warning() -> None:
    config = _config(frozenset({Timeframe.M15}))
    sink = CollectingAlertSink()
    runner = ForwardScannerRunner((Timeframe.M15,), config, alert_sink=sink)
    rows = _rows(5, 7, Timeframe.M15)
    runner.ingest(rows[0], ingestion_time_utc=_INGEST)
    runner.ingest(rows[3], ingestion_time_utc=_INGEST)  # skips indices 1,2 -> gap
    assert any(
        a.event_type is ScannerEventType.DATA_QUALITY_WARNING
        and "POTENTIAL_GAP" in a.detail
        for a in sink.alerts
    )


def test_forward_runner_matches_batch_oracle_single_tf() -> None:
    config = _config(frozenset({Timeframe.M15}))
    rows = _rows(150, 42, Timeframe.M15)
    runner = ForwardScannerRunner(
        (Timeframe.M15,), config, alert_sink=CollectingAlertSink()
    )
    _ingest_all(runner, rows)
    incremental = runner.finalize()
    batch = _batch_snapshot(rows, config)
    assert incremental == batch
    # fixture must actually exercise POIs and BTMM
    assert len(incremental.poi_analysis.poi_observations) > 0
    assert len(incremental.btmm_analysis.btmm_observations) > 0


def _availability(row: ProviderCandle) -> datetime:
    return row.open_time_utc + timedelta(
        minutes=_MINUTES[Timeframe(row.source_timeframe)]
    )


def test_availability_grouping_causal_multi_tf_matches_batch() -> None:
    config = _config(frozenset({Timeframe.M5, Timeframe.M15}))
    rows = _rows(120, 11, Timeframe.M5) + _rows(60, 12, Timeframe.M15)
    # a real live feed delivers closed candles in availability (close) order; the
    # runner groups causally by availability and must match the batch flat-sort.
    rows = sorted(rows, key=_availability)
    runner = ForwardScannerRunner(
        (Timeframe.M5, Timeframe.M15), config, alert_sink=CollectingAlertSink()
    )
    _ingest_all(runner, rows)
    incremental = runner.finalize()
    batch = _batch_snapshot(rows, config)
    assert _snapshot_checksum(
        incremental.model_dump(mode="json")
    ) == _snapshot_checksum(batch.model_dump(mode="json"))


def test_no_lookahead_every_prefix_matches_batch() -> None:
    config = _config(frozenset({Timeframe.M15}))
    rows = _rows(40, 34, Timeframe.M15)
    runner = ForwardScannerRunner(
        (Timeframe.M15,), config, alert_sink=CollectingAlertSink()
    )
    for k, row in enumerate(rows, start=1):
        runner.ingest(row, ingestion_time_utc=_INGEST)
        runner.flush()
        incremental = runner.finalize()
        batch = _batch_snapshot(rows[:k], config)
        assert incremental == batch, f"prefix {k} diverged (lookahead?)"


def test_restart_from_journal_is_deterministic(tmp_path: Path) -> None:
    config = _config(frozenset({Timeframe.M15}))
    journal = AcceptedCandleJournal(tmp_path / "journal.jsonl")
    runner = ForwardScannerRunner(
        (Timeframe.M15,), config, alert_sink=CollectingAlertSink(), journal=journal
    )
    _ingest_all(runner, _rows(120, 42, Timeframe.M15))
    original_checksum = runner.snapshot_checksum()

    recovered = ForwardScannerRunner.recover_from_journal(
        AcceptedCandleJournal(tmp_path / "journal.jsonl"),
        (Timeframe.M15,),
        config,
        alert_sink=CollectingAlertSink(),
    )
    assert recovered.snapshot_checksum() == original_checksum


def test_partially_written_journal_last_line_is_recovered(tmp_path: Path) -> None:
    config = _config(frozenset({Timeframe.M15}))
    path = tmp_path / "journal.jsonl"
    journal = AcceptedCandleJournal(path)
    runner = ForwardScannerRunner(
        (Timeframe.M15,), config, alert_sink=CollectingAlertSink(), journal=journal
    )
    _ingest_all(runner, _rows(30, 3, Timeframe.M15))
    intact_checksum = runner.snapshot_checksum()

    # simulate a crash mid-append: a garbage partial line with no newline
    with open(path, "a", encoding="utf-8") as handle:
        handle.write('{"sequence": 999, "candle": {partial')

    recovered = ForwardScannerRunner.recover_from_journal(
        AcceptedCandleJournal(path),
        (Timeframe.M15,),
        config,
        alert_sink=CollectingAlertSink(),
    )
    assert recovered.snapshot_checksum() == intact_checksum


def test_provider_reconnect_duplicate_and_backfill_handled() -> None:
    config = _config(frozenset({Timeframe.M15}))
    rows = _rows(10, 9, Timeframe.M15)
    transport = SyntheticTransport(rows, batch_size=3)
    runner = ForwardScannerRunner(
        (Timeframe.M15,), config, alert_sink=CollectingAlertSink()
    )
    delivered: list[ProviderCandle] = []
    while not transport.empty():
        delivered.extend(transport.poll_closed_candles())
    # a reconnect re-delivers the whole batch (duplicates + backfill)
    outcomes = [
        runner.ingest(row, ingestion_time_utc=_INGEST).outcome for row in delivered
    ]
    redelivered = [
        runner.ingest(row, ingestion_time_utc=_INGEST).outcome for row in delivered
    ]
    assert all(o is ForwardIngestOutcome.ACCEPTED for o in outcomes)
    assert all(o is ForwardIngestOutcome.EXACT_DUPLICATE for o in redelivered)


def test_new_poi_alert_emitted_exactly_once_per_poi() -> None:
    config = _config(frozenset({Timeframe.M15}))
    sink = CollectingAlertSink()
    runner = ForwardScannerRunner((Timeframe.M15,), config, alert_sink=sink)
    _ingest_all(runner, _rows(150, 42, Timeframe.M15))
    new_poi_ids = [
        a.record_id for a in sink.alerts if a.event_type is ScannerEventType.NEW_POI
    ]
    final_poi_ids = {
        str(o.record_id) for o in runner.finalize().poi_analysis.poi_observations
    }
    assert len(new_poi_ids) == len(set(new_poi_ids))  # each POI announced once
    # every POI present in the final snapshot was announced exactly once; some
    # announced POIs may have later been superseded/merged away, so the announced
    # set is a superset of the final set (never a re-announcement).
    assert final_poi_ids.issubset(set(new_poi_ids))
    assert len(new_poi_ids) > 0


def test_no_order_or_trade_execution_path_exists() -> None:
    import btmm_ai_scanner.forward as forward_pkg

    banned = ("buy", "sell", "order", "execute", "trade", "position")
    for event in ScannerEventType:
        lowered = event.value.lower()
        assert not any(term in lowered for term in ("buy", "sell", "order")), event
    exported = {name.lower() for name in forward_pkg.__all__}
    assert not any(term in name for name in exported for term in banned), (
        "forward package must expose no order/trade-execution symbol"
    )


def test_synthetic_transport_is_credential_free_and_offline() -> None:
    # The live FXCM transport is intentionally absent; the synthetic transport
    # needs no network/credentials and simply replays queued rows.
    transport = SyntheticTransport(_rows(2, 1, Timeframe.M15), batch_size=1)
    assert len(transport.poll_closed_candles()) == 1
    assert len(transport.poll_closed_candles()) == 1
    assert transport.empty()


@pytest.mark.parametrize("timeframe", [Timeframe.M1, Timeframe.M5, Timeframe.M15])
def test_availability_is_open_plus_native_duration(timeframe: Timeframe) -> None:
    row = _row(3, (100, 101, 99, 100), timeframe)
    candle = build_forward_closed_candle(row, ingestion_time_utc=_INGEST)
    assert candle.availability_time_utc == candle.event_time_utc + timedelta(
        minutes=_MINUTES[timeframe]
    )
    assert candle.completeness.value == "CONFIRMED_COMPLETE"
