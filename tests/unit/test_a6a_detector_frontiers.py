"""A6-A permanent tests: exact incremental Wilder ATR-14 and exact incremental
POI detector frontiers.

Every test compares the incremental frontier against the UNCHANGED batch
detectors / ``compute_atr_series`` at every prefix. The batch functions remain
the differential oracle and are never modified.
"""

import hashlib
import random
from collections.abc import Iterable
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

import pytest

from btmm_ai_scanner.config.enums import InternalSymbol, Timeframe
from btmm_ai_scanner.contracts.normalized_candle import NormalizedCandle
from btmm_ai_scanner.contracts.raw_candle import CandleCompleteness, CandleVolumeKind
from btmm_ai_scanner.contracts.types import SemVer
from btmm_ai_scanner.domain.analyzer import (
    UnsortedCandleSequenceError,
    analyze_market_measurements,
)
from btmm_ai_scanner.domain.configuration import MarketMeasurementConfiguration
from btmm_ai_scanner.domain.enums import DerivedOutputType
from btmm_ai_scanner.measurements.atr import (
    advance_incremental_atr,
    compute_atr_series,
    initial_incremental_atr_state,
)
from btmm_ai_scanner.poi.analyzer import (
    PoiTimeframeInput,
    _advance_poi_replay_state,
    _create_initial_poi_replay_state,
    _detect_bundle_candidates,
    _poi_replay_state_to_analysis,
    analyze_pois,
)
from btmm_ai_scanner.poi.bases import detect_bases
from btmm_ai_scanner.poi.configuration import PoiConfiguration
from btmm_ai_scanner.poi.detector_frontier import (
    _evaluate_new_bases,
    advance_detector_frontier,
    create_initial_detector_frontier_state,
)
from btmm_ai_scanner.poi.reference_zones import detect_reference_zones

_RAW_CANDLE_ID = UUID("0193f460-1234-7abc-8def-abcdefabcdaa")
_PROVENANCE_ID = UUID("0193f460-1234-7abc-8def-abcdefabcdff")
_FINGERPRINT = "a" * 64
_BASE_TIME = datetime(2026, 1, 1, tzinfo=UTC)
_MCONFIG = MarketMeasurementConfiguration(minimum_price_tick=Decimal("0.01"))
_PCONFIG = PoiConfiguration(minimum_price_tick=Decimal("0.01"))


class _HashIdentityProvider:
    def identify(
        self, *, output_type: DerivedOutputType, semantic_key: tuple[str, ...]
    ) -> UUID:
        payload = output_type.value + "|" + "|".join(semantic_key)
        digest = hashlib.sha256(payload.encode("utf-8")).digest()[:16]
        as_int = int.from_bytes(digest, "big")
        as_int &= ~(0xF << 76)
        as_int |= 7 << 76
        as_int &= ~(0x3 << 62)
        as_int |= 0x2 << 62
        return UUID(int=as_int)


def _candle(
    index: int,
    open_: str,
    high: str,
    low: str,
    close: str,
    *,
    event_time: datetime | None = None,
    timeframe: Timeframe = Timeframe.M1,
) -> NormalizedCandle:
    et = event_time if event_time is not None else _BASE_TIME + timedelta(minutes=index)
    av = et + timedelta(minutes=1)
    return NormalizedCandle.model_validate(
        {
            "record_id": UUID(f"0193f460-1234-7abc-8def-{index:012x}"),
            "content_fingerprint": _FINGERPRINT,
            "raw_candle_id": _RAW_CANDLE_ID,
            "provider": "FXCM",
            "source_reference": "fxcm-xauusd",
            "source_symbol": InternalSymbol.XAUUSD.value,
            "source_timeframe": timeframe.value,
            "symbol": InternalSymbol.XAUUSD,
            "timeframe": timeframe,
            "event_time_utc": et,
            "availability_time_utc": av,
            "processing_time_utc": av,
            "original_event_time": et,
            "original_availability_time": av,
            "original_timezone": "UTC",
            "open": Decimal(open_),
            "high": Decimal(high),
            "low": Decimal(low),
            "close": Decimal(close),
            "volume": Decimal("10"),
            "volume_kind": CandleVolumeKind.TICK,
            "completeness": CandleCompleteness.CONFIRMED_COMPLETE,
            "rule_version": SemVer.parse("0.1.0"),
            "contract_version": SemVer.parse("0.1.0"),
            "schema_version": SemVer.parse("0.1.0"),
            "provenance_id": _PROVENANCE_ID,
        }
    )


def _random_walk(
    n: int,
    seed: int,
    *,
    timeframe: Timeframe = Timeframe.M1,
    start: datetime | None = None,
) -> list[NormalizedCandle]:
    rng = random.Random(seed)
    step = {
        Timeframe.M1: timedelta(minutes=1),
        Timeframe.D1: timedelta(days=1),
    }[timeframe]
    base = start if start is not None else _BASE_TIME
    price = 100.0
    candles: list[NormalizedCandle] = []
    for i in range(n):
        price += rng.uniform(-1.5, 1.5)
        o = price
        c = price + rng.uniform(-1.2, 1.2)
        h = max(o, c) + rng.uniform(0.0, 0.9)
        low = min(o, c) - rng.uniform(0.0, 0.9)
        candles.append(
            _candle(
                i,
                f"{o:.2f}",
                f"{h:.2f}",
                f"{low:.2f}",
                f"{c:.2f}",
                event_time=base + step * i,
                timeframe=timeframe,
            )
        )
    return candles


def _sorted_repr(items: Iterable[object]) -> list[str]:
    return sorted(repr(item) for item in items)


# ---------------------------------------------------------------------------
# Incremental Wilder ATR-14.
# ---------------------------------------------------------------------------


def _incremental_atr_series(candles: list[NormalizedCandle]) -> list[Decimal | None]:
    state = initial_incremental_atr_state(14)
    series: list[Decimal | None] = []
    for candle in candles:
        state, value = advance_incremental_atr(state, candle)
        series.append(value)
    return series


def test_incremental_atr14_matches_full_prefix_every_prefix() -> None:
    candles = _random_walk(80, seed=11)
    state = initial_incremental_atr_state(14)
    series: list[Decimal | None] = []
    for k, candle in enumerate(candles, start=1):
        state, value = advance_incremental_atr(state, candle)
        series.append(value)
        assert tuple(series) == compute_atr_series(tuple(candles[:k]), 14)


def test_incremental_atr14_warmup_seed_equal_tr_and_gaps() -> None:
    # Fewer than 14 candles => all None (warm-up).
    short = [_candle(i, "100", "100.5", "99.5", "100.1") for i in range(13)]
    assert _incremental_atr_series(short) == [None] * 13

    # Exactly 14 candles => the seed (mean of the first 14 true ranges) appears
    # only at the final index; the seed transition is exact.
    fourteen = [_candle(i, "100", "100.5", "99.5", "100.1") for i in range(14)]
    assert _incremental_atr_series(fourteen) == list(
        compute_atr_series(tuple(fourteen), 14)
    )

    # Equal true ranges, a large-range gap candle, then a flat run: exercises the
    # seed, the recurrence, and true-range-with-previous-close.
    mixed = [_candle(i, "100", "101", "99", "100") for i in range(14)]
    mixed.append(_candle(14, "100", "140", "60", "130"))  # huge range + gap
    mixed.extend(_candle(15 + j, "130", "130.2", "129.9", "130.1") for j in range(10))
    assert _incremental_atr_series(mixed) == list(compute_atr_series(tuple(mixed), 14))


# ---------------------------------------------------------------------------
# Full detector universe == batch _detect_bundle_candidates at every prefix.
# ---------------------------------------------------------------------------


def _assert_universe_matches_every_prefix(
    candles: list[NormalizedCandle], timeframe: Timeframe
) -> None:
    idp = _HashIdentityProvider()
    frontier = create_initial_detector_frontier_state()
    for k in range(1, len(candles) + 1):
        prefix = tuple(candles[:k])
        measurement = analyze_market_measurements(prefix, _MCONFIG, idp)
        frontier, universe, atr_series = advance_detector_frontier(
            frontier, candles[k - 1], measurement, _PCONFIG
        )
        # ATR handed to the lifecycle is the exact full-prefix series.
        assert tuple(atr_series) == compute_atr_series(prefix, 14)
        bundle = PoiTimeframeInput(
            timeframe=timeframe, candles=prefix, measurement_analysis=measurement
        )
        batch = _detect_bundle_candidates(bundle, _PCONFIG)
        assert _sorted_repr(universe) == _sorted_repr(batch)


def test_detector_universe_matches_batch_every_prefix_m1() -> None:
    _assert_universe_matches_every_prefix(_random_walk(130, seed=7), Timeframe.M1)


def test_detector_universe_matches_batch_across_calendar_boundaries() -> None:
    # D1 candles from mid-Dec 2025 to early Feb 2026 cross UTC day, ISO-week,
    # month and Dec->Jan year boundaries (period-level ADD/REPLACE/REMOVE).
    candles = _random_walk(
        45, seed=3, timeframe=Timeframe.D1, start=datetime(2025, 12, 20, tzinfo=UTC)
    )
    _assert_universe_matches_every_prefix(candles, Timeframe.D1)


# ---------------------------------------------------------------------------
# Bases: full-prefix ATR (A4 regression) + greedy multiplicity.
# ---------------------------------------------------------------------------


def test_base_frontier_matches_full_prefix_bases_every_prefix() -> None:
    # A long warm series so ATR-14 is finalized well before bases form; a sliced
    # (suffix) ATR would diverge from detect_bases(full_prefix) and fail here.
    candles = _random_walk(90, seed=21)
    frontier = create_initial_detector_frontier_state()
    idp = _HashIdentityProvider()
    for k in range(1, len(candles) + 1):
        prefix = tuple(candles[:k])
        measurement = analyze_market_measurements(prefix, _MCONFIG, idp)
        frontier, universe, _ = advance_detector_frontier(
            frontier, candles[k - 1], measurement, _PCONFIG
        )
        frontier_bases = [c for c in universe if type(c).__name__ == "BaseCandidate"]
        assert _sorted_repr(frontier_bases) == _sorted_repr(
            detect_bases(prefix, _PCONFIG)
        )


def test_base_evaluator_consumes_injected_full_prefix_atr_not_a_slice() -> None:
    # A base window whose base_height gate flips with the reference ATR. This is
    # exactly the A4 failure mode: a suffix-reseeded ATR (None during a <14-candle
    # slice => departure_range fallback) would ACCEPT the base, while the true
    # full-prefix ATR (0.3) REJECTS it. The evaluator must honour the injected
    # full-prefix value.
    window = (
        _candle(0, "100", "100.4", "100.0", "100.2"),
        _candle(1, "100", "100.4", "100.0", "100.2"),
        _candle(2, "100.2", "101.5", "100.2", "101.4"),  # departure (rally)
    )
    with_fallback = _evaluate_new_bases(window, None, _PCONFIG)
    with_real_atr = _evaluate_new_bases(window, Decimal("0.3"), _PCONFIG)
    assert len(with_fallback) == 1  # base_height 0.4 <= 0.75 * departure_range 1.3
    assert len(with_real_atr) == 0  # base_height 0.4 > 0.75 * 0.3 => rejected
    assert with_fallback != with_real_atr


# ---------------------------------------------------------------------------
# Reversal candles: delayed confirmation timing.
# ---------------------------------------------------------------------------


def test_reversal_delayed_confirmation_matches_batch_and_respects_no_lookahead() -> (
    None
):
    # A strong bullish reversal candle (index 3) confirmed by a later close above
    # its midpoint. The candidate must appear ONLY once the confirming candle
    # exists (no-lookahead), at exactly the batch's confirmation prefix.
    candles = [
        _candle(0, "100.0", "100.2", "99.8", "100.0"),
        _candle(1, "100.0", "100.2", "99.8", "100.0"),
        _candle(2, "100.0", "100.2", "99.8", "100.0"),
        _candle(3, "100.0", "100.1", "97.0", "99.9"),  # large-range bullish reversal
        _candle(4, "99.9", "100.0", "99.5", "99.6"),  # below midpoint (no confirm)
        _candle(
            5, "99.6", "100.9", "99.5", "100.8"
        ),  # closes above midpoint -> confirm
        _candle(6, "100.8", "101.0", "100.6", "100.9"),
    ]
    frontier = create_initial_detector_frontier_state()
    idp = _HashIdentityProvider()
    for k in range(1, len(candles) + 1):
        prefix = tuple(candles[:k])
        measurement = analyze_market_measurements(prefix, _MCONFIG, idp)
        frontier, universe, _ = advance_detector_frontier(
            frontier, candles[k - 1], measurement, _PCONFIG
        )
        bundle = PoiTimeframeInput(
            timeframe=Timeframe.M1, candles=prefix, measurement_analysis=measurement
        )
        assert _sorted_repr(universe) == _sorted_repr(
            _detect_bundle_candidates(bundle, _PCONFIG)
        )
    # And the per-prefix novelty (delayed confirmation) is exercised on a random
    # series: newly emitted reversals per prefix are exactly the batch delta.
    _assert_universe_matches_every_prefix(_random_walk(60, seed=99), Timeframe.M1)


# ---------------------------------------------------------------------------
# Period levels ADD / REPLACE / REMOVE.
# ---------------------------------------------------------------------------


def test_period_levels_add_replace_remove_current_and_previous() -> None:
    # D1 candles across two ISO days-of-month with distinct extremes so the
    # current-period candidate REPLACES each candle and, on rollover, the closed
    # window becomes the (fixed) previous-period candidate.
    candles = _random_walk(
        20, seed=5, timeframe=Timeframe.D1, start=datetime(2026, 1, 28, tzinfo=UTC)
    )
    frontier = create_initial_detector_frontier_state()
    idp = _HashIdentityProvider()
    for k in range(1, len(candles) + 1):
        prefix = tuple(candles[:k])
        measurement = analyze_market_measurements(prefix, _MCONFIG, idp)
        frontier, universe, _ = advance_detector_frontier(
            frontier, candles[k - 1], measurement, _PCONFIG
        )
        period = [c for c in universe if type(c).__name__ == "PeriodLevelCandidate"]
        bundle = PoiTimeframeInput(
            timeframe=Timeframe.D1, candles=prefix, measurement_analysis=measurement
        )
        batch_period = [
            c
            for c in _detect_bundle_candidates(bundle, _PCONFIG)
            if type(c).__name__ == "PeriodLevelCandidate"
        ]
        assert _sorted_repr(period) == _sorted_repr(batch_period)


# ---------------------------------------------------------------------------
# Reference zones ADD / REPLACE / REMOVE + identity reuse.
# ---------------------------------------------------------------------------


def test_reference_zones_track_measurement_and_reuse_when_unchanged() -> None:
    candles = _random_walk(120, seed=44)
    frontier = create_initial_detector_frontier_state()
    idp = _HashIdentityProvider()
    saw_reference = False
    reused_unchanged = False
    prior_sig = None
    prior_refs = None
    for k in range(1, len(candles) + 1):
        prefix = tuple(candles[:k])
        measurement = analyze_market_measurements(prefix, _MCONFIG, idp)
        frontier, universe, _ = advance_detector_frontier(
            frontier, candles[k - 1], measurement, _PCONFIG
        )
        refs = [c for c in universe if type(c).__name__ == "ReferenceZoneCandidate"]
        expected = detect_reference_zones(
            measurement.support_resistance_zones,
            measurement.equal_level_clusters,
        )
        assert _sorted_repr(refs) == _sorted_repr(expected)
        if refs:
            saw_reference = True
        sig = frontier.reference_signature
        if prior_sig is not None and sig == prior_sig and prior_refs is not None:
            # Unchanged upstream => the identical cached tuple is reused verbatim.
            assert frontier.reference_candidates is prior_refs
            reused_unchanged = True
        prior_sig = sig
        prior_refs = frontier.reference_candidates
    assert saw_reference
    assert reused_unchanged


# ---------------------------------------------------------------------------
# No-lookahead + integrated PoiAnalysis + transaction rollback + hot-path.
# ---------------------------------------------------------------------------


def test_integrated_poi_analysis_matches_batch_every_prefix() -> None:
    candles = _random_walk(70, seed=13)
    idp = _HashIdentityProvider()
    state = _create_initial_poi_replay_state(idp, _PCONFIG)
    for k in range(1, len(candles) + 1):
        prefix = tuple(candles[:k])
        measurement = analyze_market_measurements(prefix, _MCONFIG, idp)
        state = _advance_poi_replay_state(state, candles[k - 1], measurement, _PCONFIG)
        bundle = PoiTimeframeInput(
            timeframe=Timeframe.M1, candles=prefix, measurement_analysis=measurement
        )
        # Fresh identity provider for the batch so record_ids are content-addressed
        # identically to the incremental resolver's.
        batch = analyze_pois((bundle,), _PCONFIG, _HashIdentityProvider())
        incremental = _poi_replay_state_to_analysis(state)
        assert incremental.poi_observations == batch.poi_observations
        assert incremental.poi_lifecycle_transitions == batch.poi_lifecycle_transitions
        assert incremental.current_poi_states == batch.current_poi_states


def test_frontier_advance_is_transactional_on_out_of_order_candle() -> None:
    candles = _random_walk(30, seed=8)
    idp = _HashIdentityProvider()
    state = _create_initial_poi_replay_state(idp, _PCONFIG)
    for k in range(1, 21):
        prefix = tuple(candles[:k])
        measurement = analyze_market_measurements(prefix, _MCONFIG, idp)
        state = _advance_poi_replay_state(state, candles[k - 1], measurement, _PCONFIG)

    frontier_before = state.detector_frontier
    atr_before = frontier_before.atr_series
    appended_before = frontier_before.append_only_candidates

    # An out-of-order candle raises before any frontier work; prior state intact.
    stale_measurement = analyze_market_measurements(tuple(candles[:20]), _MCONFIG, idp)
    with pytest.raises(UnsortedCandleSequenceError):
        _advance_poi_replay_state(state, candles[5], stale_measurement, _PCONFIG)

    assert state.detector_frontier is frontier_before
    assert state.detector_frontier.atr_series == atr_before
    assert state.detector_frontier.append_only_candidates == appended_before


def test_incremental_hot_path_never_calls_full_prefix_detection_or_atr(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from btmm_ai_scanner.poi import analyzer as analyzer_module

    def _boom_bundle(*args: object, **kwargs: object) -> object:
        raise AssertionError(
            "_detect_bundle_candidates(full_prefix) must not run in the "
            "incremental hot path"
        )

    def _boom_atr(*args: object, **kwargs: object) -> object:
        raise AssertionError(
            "compute_atr_series(full_prefix, 14) must not run in the "
            "incremental hot path"
        )

    monkeypatch.setattr(analyzer_module, "_detect_bundle_candidates", _boom_bundle)
    monkeypatch.setattr(analyzer_module, "compute_atr_series", _boom_atr)

    candles = _random_walk(40, seed=2)
    idp = _HashIdentityProvider()
    state = _create_initial_poi_replay_state(idp, _PCONFIG)
    for k in range(1, len(candles) + 1):
        prefix = tuple(candles[:k])
        measurement = analyze_market_measurements(prefix, _MCONFIG, idp)
        # Would raise via the monkeypatched stubs if the hot path called either.
        state = _advance_poi_replay_state(state, candles[k - 1], measurement, _PCONFIG)
    assert state.poi_observations_so_far is not None


def test_incremental_advance_defers_all_lifecycle_output_assembly(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # A6-B1-B7 operation-count gate: the per-candle advance must perform NO
    # lifecycle-output assembly — no historical POI lifecycle discovery loop, no
    # CurrentPoiState materialization, no run_poi_lifecycle, no cursor->walk
    # reconstruction. All of that is deferred to _poi_replay_state_to_analysis
    # (the snapshot boundary). Under FINAL_ONLY retention that is materialized
    # once, not per candle.
    from btmm_ai_scanner.poi import analyzer as analyzer_module

    def _boom(*args: object, **kwargs: object) -> object:
        raise AssertionError(
            "lifecycle-output assembly must be deferred out of the per-candle "
            "advance hot path"
        )

    monkeypatch.setattr(analyzer_module, "_build_lifecycle_outputs", _boom)
    monkeypatch.setattr(analyzer_module, "cursor_walk_result", _boom)
    monkeypatch.setattr(analyzer_module, "_materialize_current_poi_states", _boom)
    monkeypatch.setattr(analyzer_module, "run_poi_lifecycle", _boom)

    candles = _random_walk(40, seed=6)
    idp = _HashIdentityProvider()
    state = _create_initial_poi_replay_state(idp, _PCONFIG)
    for k in range(1, len(candles) + 1):
        prefix = tuple(candles[:k])
        measurement = analyze_market_measurements(prefix, _MCONFIG, idp)
        # Advancing must NOT trigger any deferred lifecycle assembly.
        state = _advance_poi_replay_state(state, candles[k - 1], measurement, _PCONFIG)

    # ...and the deferred assembly genuinely happens at materialization.
    with pytest.raises(AssertionError):
        _poi_replay_state_to_analysis(state)
