import hashlib
import random
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from itertools import pairwise
from uuid import UUID

import pytest

from btmm_ai_scanner.config.enums import InternalSymbol, Timeframe
from btmm_ai_scanner.contracts.normalized_candle import NormalizedCandle
from btmm_ai_scanner.contracts.raw_candle import CandleCompleteness, CandleVolumeKind
from btmm_ai_scanner.contracts.types import SemVer
from btmm_ai_scanner.domain.analyzer import (
    AmbiguousEventTimeAnalysisError,
    UnsortedCandleSequenceError,
    _advance_measurement_replay_state,
    _atr_incremental_step,
    _AtrIncrementalState,
    _create_initial_measurement_replay_state,
    _measurement_replay_state_to_analysis,
    analyze_market_measurements,
)
from btmm_ai_scanner.domain.configuration import MarketMeasurementConfiguration
from btmm_ai_scanner.domain.enums import DerivedOutputType
from btmm_ai_scanner.domain.swings import (
    _merge_adjacent_plateaus,
    _supersede_same_direction_runs,
)
from btmm_ai_scanner.measurements.atr import compute_atr_series

_RAW_CANDLE_ID = UUID("0193f350-1234-7abc-8def-abcdefabcdaa")
_PROVENANCE_ID = UUID("0193f350-1234-7abc-8def-abcdefabcdff")
_FINGERPRINT = "a" * 64
_BASE_TIME = datetime(2026, 1, 1, tzinfo=UTC)
_CONFIG = MarketMeasurementConfiguration(minimum_price_tick=Decimal("0.01"))


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


def _record_id(index: int) -> UUID:
    return UUID(f"0193f350-1234-7abc-8def-{index:012x}")


def _candle(
    index: int,
    o: float,
    h: float,
    low: float,
    c: float,
    *,
    event_time: datetime | None = None,
    availability_time: datetime | None = None,
) -> NormalizedCandle:
    if event_time is None:
        event_time = _BASE_TIME + timedelta(minutes=index)
    if availability_time is None:
        availability_time = event_time + timedelta(minutes=1)
    return NormalizedCandle.model_validate(
        {
            "record_id": _record_id(index),
            "content_fingerprint": _FINGERPRINT,
            "raw_candle_id": _RAW_CANDLE_ID,
            "provider": "FXCM",
            "source_reference": "fxcm-xauusd-m1",
            "source_symbol": "XAUUSD",
            "source_timeframe": "M1",
            "symbol": InternalSymbol.XAUUSD,
            "timeframe": Timeframe.M1,
            "event_time_utc": event_time,
            "availability_time_utc": availability_time,
            "processing_time_utc": availability_time,
            "original_event_time": event_time,
            "original_availability_time": availability_time,
            "original_timezone": "UTC",
            "open": Decimal(str(o)),
            "high": Decimal(str(h)),
            "low": Decimal(str(low)),
            "close": Decimal(str(c)),
            "volume": Decimal("10"),
            "volume_kind": CandleVolumeKind.TICK,
            "completeness": CandleCompleteness.CONFIRMED_COMPLETE,
            "rule_version": SemVer.parse("0.1.0"),
            "contract_version": SemVer.parse("0.1.0"),
            "schema_version": SemVer.parse("0.1.0"),
            "provenance_id": _PROVENANCE_ID,
        }
    )


def _build(
    prices: list[tuple[float, float, float, float]],
) -> tuple[NormalizedCandle, ...]:
    return tuple(_candle(i, *p) for i, p in enumerate(prices))


def _random_walk_prices(
    n: int, seed: int, *, low_vol: bool = False
) -> list[tuple[float, float, float, float]]:
    rng = random.Random(seed)
    price = 100.0
    spread = 0.6 if low_vol else 1.5
    wick = 0.3 if low_vol else 0.8
    prices: list[tuple[float, float, float, float]] = []
    for _ in range(n):
        o = price
        move = rng.uniform(-spread, spread)
        c = o + move
        h = max(o, c) + rng.uniform(0, wick)
        low = min(o, c) - rng.uniform(0, wick)
        prices.append((o, h, low, c))
        price = c
    return prices


_ZIGZAG_PRICES = [
    (100 + 0.1 * i, 100.5 + 0.1 * i, 99.6 + 0.1 * i, 100.2 + 0.1 * i) for i in range(16)
] + [
    (100, 101, 99, 100),
    (100, 102, 99.5, 101.5),
    (101.5, 105, 101, 104),
    (104, 104.5, 100, 100.5),
    (100.5, 101, 96, 96.5),
    (96.5, 97, 93, 93.5),
    (93.5, 96, 93, 95.5),
    (95.5, 99, 95, 98.5),
    (98.5, 103, 98, 102.5),
    (102.5, 104, 101, 103.5),
    (103.5, 104, 100, 100.5),
    (100.5, 101, 97, 97.5),
    (97.5, 98, 94, 94.5),
    (94.5, 95, 91, 91.5),
    (91.5, 95, 91, 94.5),
    (94.5, 98, 94, 97.5),
    (97.5, 101, 97, 100.5),
]

_ZIGZAG_CANDLES = _build(_ZIGZAG_PRICES)
_RANDOM_WALK_CANDLES = _build(_random_walk_prices(140, seed=42))
_RICH_SWING_CANDLES = _build(_random_walk_prices(200, seed=34))


def _replay_all_prefixes_match_oracle(
    candles: tuple[NormalizedCandle, ...],
) -> tuple[bool, list[int]]:
    state = _create_initial_measurement_replay_state(_HashIdentityProvider(), _CONFIG)
    mismatched: list[int] = []
    for k, candle in enumerate(candles, start=1):
        state = _advance_measurement_replay_state(state, candle, _CONFIG)
        incremental = _measurement_replay_state_to_analysis(state)
        batch = analyze_market_measurements(
            candles[:k], _CONFIG, _HashIdentityProvider()
        )
        if incremental != batch:
            mismatched.append(k)
    return len(mismatched) == 0, mismatched


def test_wilder_atr_incremental_state_before_initialization_reports_no_value() -> None:
    state = _AtrIncrementalState()
    for candle in _RANDOM_WALK_CANDLES[: _CONFIG.atr_period - 1]:
        state, value = _atr_incremental_step(state, candle, _CONFIG.atr_period)
        assert value is None


def test_wilder_atr_incremental_state_at_the_seed_boundary_matches_the_simple_average_seed() -> (
    None
):
    boundary_candles = _RANDOM_WALK_CANDLES[: _CONFIG.atr_period]
    batch_atr = compute_atr_series(boundary_candles, _CONFIG.atr_period)

    state = _AtrIncrementalState()
    value = None
    for candle in boundary_candles:
        state, value = _atr_incremental_step(state, candle, _CONFIG.atr_period)

    assert value is not None
    assert value == batch_atr[_CONFIG.atr_period - 1]


def test_wilder_atr_incremental_state_matches_full_history_after_initialization() -> (
    None
):
    batch_atr = compute_atr_series(_RANDOM_WALK_CANDLES, _CONFIG.atr_period)

    state = _AtrIncrementalState()
    incremental_atr: list[Decimal | None] = []
    for candle in _RANDOM_WALK_CANDLES:
        state, value = _atr_incremental_step(state, candle, _CONFIG.atr_period)
        incremental_atr.append(value)

    assert tuple(incremental_atr) == batch_atr


def test_wilder_atr_incremental_state_matches_full_history_across_an_event_time_gap() -> (
    None
):
    gapped_candles = list(_RANDOM_WALK_CANDLES[:20])
    last = gapped_candles[-1]
    gap_start = last.event_time_utc + timedelta(days=1)
    for offset, price_tuple in enumerate(_random_walk_prices(20, seed=99)):
        gapped_candles.append(
            _candle(
                100 + offset,
                *price_tuple,
                event_time=gap_start + timedelta(minutes=offset),
            )
        )
    gapped = tuple(gapped_candles)

    batch_atr = compute_atr_series(gapped, _CONFIG.atr_period)
    state = _AtrIncrementalState()
    incremental_atr: list[Decimal | None] = []
    for candle in gapped:
        state, value = _atr_incremental_step(state, candle, _CONFIG.atr_period)
        incremental_atr.append(value)

    assert tuple(incremental_atr) == batch_atr


def test_pending_swing_remains_unconfirmed_beyond_a_short_fixed_duration() -> None:
    state = _create_initial_measurement_replay_state(_HashIdentityProvider(), _CONFIG)
    unresolved_seen = False
    for candle in _RICH_SWING_CANDLES[:60]:
        state = _advance_measurement_replay_state(state, candle, _CONFIG)
        if any(
            tracker.confirmed_at_index is None
            for tracker in state.confirmation_trackers.values()
        ):
            unresolved_seen = True
            break

    assert unresolved_seen, "fixture never produced a pending, unconfirmed pivot"

    matched, mismatched = _replay_all_prefixes_match_oracle(_RICH_SWING_CANDLES[:60])
    assert matched, f"mismatched prefixes: {mismatched}"


def test_pivot_plateau_merge_matches_the_batch_oracle() -> None:
    state = _create_initial_measurement_replay_state(_HashIdentityProvider(), _CONFIG)
    for candle in _RICH_SWING_CANDLES:
        state = _advance_measurement_replay_state(state, candle, _CONFIG)

    merged = _merge_adjacent_plateaus(list(state.raw_pivots_so_far))
    assert len(merged) < len(state.raw_pivots_so_far), (
        "fixture never produced an adjacent-plateau merge"
    )

    matched, mismatched = _replay_all_prefixes_match_oracle(_RICH_SWING_CANDLES)
    assert matched, f"mismatched prefixes: {mismatched}"


def test_same_direction_swing_supersession_matches_the_batch_oracle() -> None:
    state = _create_initial_measurement_replay_state(_HashIdentityProvider(), _CONFIG)
    for candle in _RICH_SWING_CANDLES:
        state = _advance_measurement_replay_state(state, candle, _CONFIG)

    merged = _merge_adjacent_plateaus(list(state.raw_pivots_so_far))
    superseded = _supersede_same_direction_runs(merged)
    assert len(superseded) < len(merged), (
        "fixture never produced a same-direction supersession"
    )

    matched, mismatched = _replay_all_prefixes_match_oracle(_RICH_SWING_CANDLES)
    assert matched, f"mismatched prefixes: {mismatched}"


def test_confirmed_swing_status_can_change_as_history_grows_and_still_match_the_batch_oracle() -> (
    None
):
    """A pivot's confirmation status is pending (not yet in
    confirmed_swing_candidates_so_far) for a stretch of candles and only
    later becomes confirmed once its reversal threshold is reached — the
    candidate count must plateau (unresolved trackers present) and then
    grow, not increase in lockstep with every new pivot. Exact list-position
    reordering (a resolved-out-of-pivot-order insertion) is additionally
    possible per the algorithm's traced non-monotonic semantics, but is not
    reliably reproducible with bounded synthetic fixtures, so it is not
    asserted here as a required occurrence; full prefix equivalence (which
    would catch either form of drift) is still checked below."""
    state = _create_initial_measurement_replay_state(_HashIdentityProvider(), _CONFIG)
    candidate_counts: list[int] = []
    unresolved_seen = False
    for candle in _RICH_SWING_CANDLES:
        state = _advance_measurement_replay_state(state, candle, _CONFIG)
        candidate_counts.append(len(state.confirmed_swing_candidates_so_far))
        if any(
            tracker.confirmed_at_index is None
            for tracker in state.confirmation_trackers.values()
        ):
            unresolved_seen = True

    assert unresolved_seen, "fixture never left a pivot pending confirmation"
    plateaus = sum(
        1 for earlier, later in pairwise(candidate_counts) if earlier == later
    )
    assert plateaus > 0, "confirmed-swing count grew every single candle"
    assert candidate_counts[-1] > candidate_counts[0], (
        "confirmed-swing count never grew across the fixture"
    )

    matched, mismatched = _replay_all_prefixes_match_oracle(_RICH_SWING_CANDLES)
    assert matched, f"mismatched prefixes: {mismatched}"


def test_older_confirmed_swings_remain_relevant_to_later_equal_level_and_trendline_output() -> (
    None
):
    early_prefix = 60
    state = _create_initial_measurement_replay_state(_HashIdentityProvider(), _CONFIG)
    early_swing_ids: set[UUID] = set()
    for k, candle in enumerate(_RICH_SWING_CANDLES, start=1):
        state = _advance_measurement_replay_state(state, candle, _CONFIG)
        if k == early_prefix:
            early_swing_ids = {s.record_id for s in state.confirmed_swings_so_far}

    late_referenced_ids: set[UUID] = set()
    for cluster in state.equal_level_clusters_so_far:
        late_referenced_ids.update(cluster.component_swing_record_ids)
    for trendline in state.trendlines_so_far:
        late_referenced_ids.add(trendline.anchor_1_swing_record_id)
        late_referenced_ids.add(trendline.anchor_2_swing_record_id)

    assert early_swing_ids & late_referenced_ids, (
        "no early-confirmed swing was referenced by later equal-level/trendline output"
    )

    matched, mismatched = _replay_all_prefixes_match_oracle(_RICH_SWING_CANDLES)
    assert matched, f"mismatched prefixes: {mismatched}"


def test_incremental_support_reaction_window_completion_matches_the_batch_oracle() -> (
    None
):
    state = _create_initial_measurement_replay_state(_HashIdentityProvider(), _CONFIG)
    for candle in _RICH_SWING_CANDLES:
        state = _advance_measurement_replay_state(state, candle, _CONFIG)

    batch = analyze_market_measurements(
        _RICH_SWING_CANDLES, _CONFIG, _HashIdentityProvider()
    )
    support_zones = [
        z for z in batch.support_resistance_zones if z.zone_type.value == "SUPPORT"
    ]
    assert support_zones, "fixture never produced a confirmed support zone"

    incremental = _measurement_replay_state_to_analysis(state)
    assert incremental.support_resistance_zones == batch.support_resistance_zones


def test_incremental_resistance_reaction_window_completion_matches_the_batch_oracle() -> (
    None
):
    state = _create_initial_measurement_replay_state(_HashIdentityProvider(), _CONFIG)
    for candle in _RICH_SWING_CANDLES:
        state = _advance_measurement_replay_state(state, candle, _CONFIG)

    batch = analyze_market_measurements(
        _RICH_SWING_CANDLES, _CONFIG, _HashIdentityProvider()
    )
    resistance_zones = [
        z for z in batch.support_resistance_zones if z.zone_type.value == "RESISTANCE"
    ]
    assert resistance_zones, "fixture never produced a confirmed resistance zone"

    incremental = _measurement_replay_state_to_analysis(state)
    assert incremental.support_resistance_zones == batch.support_resistance_zones


def test_delayed_support_resistance_candidate_catch_up_matches_the_batch_oracle() -> (
    None
):
    state = _create_initial_measurement_replay_state(_HashIdentityProvider(), _CONFIG)
    saw_delayed_creation = False
    for candle in _RICH_SWING_CANDLES:
        before_origins = set(state.sr_origin_trackers)
        state = _advance_measurement_replay_state(state, candle, _CONFIG)
        new_origin_keys = set(state.sr_origin_trackers) - before_origins
        if any(
            state.sr_origin_trackers[key].reaction_start_index is not None
            for key in new_origin_keys
        ):
            saw_delayed_creation = True

    assert saw_delayed_creation, (
        "fixture never exercised a tracker created after its search already had "
        "unscanned candles pending"
    )

    matched, mismatched = _replay_all_prefixes_match_oracle(_RICH_SWING_CANDLES)
    assert matched, f"mismatched prefixes: {mismatched}"


def test_incremental_equal_high_clusters_match_the_batch_oracle() -> None:
    state = _create_initial_measurement_replay_state(_HashIdentityProvider(), _CONFIG)
    for candle in _RICH_SWING_CANDLES:
        state = _advance_measurement_replay_state(state, candle, _CONFIG)

    batch = analyze_market_measurements(
        _RICH_SWING_CANDLES, _CONFIG, _HashIdentityProvider()
    )
    equal_highs = [
        c for c in batch.equal_level_clusters if c.cluster_type.value == "EQUAL_HIGH"
    ]
    assert equal_highs, "fixture never produced an equal-high cluster"

    incremental = _measurement_replay_state_to_analysis(state)
    assert incremental.equal_level_clusters == batch.equal_level_clusters


def test_incremental_equal_low_clusters_match_the_batch_oracle() -> None:
    state = _create_initial_measurement_replay_state(_HashIdentityProvider(), _CONFIG)
    for candle in _RICH_SWING_CANDLES:
        state = _advance_measurement_replay_state(state, candle, _CONFIG)

    batch = analyze_market_measurements(
        _RICH_SWING_CANDLES, _CONFIG, _HashIdentityProvider()
    )
    equal_lows = [
        c for c in batch.equal_level_clusters if c.cluster_type.value == "EQUAL_LOW"
    ]
    assert equal_lows, "fixture never produced an equal-low cluster"

    incremental = _measurement_replay_state_to_analysis(state)
    assert incremental.equal_level_clusters == batch.equal_level_clusters


def test_incremental_trendlines_match_the_batch_oracle_as_confirmed_swings_arrive() -> (
    None
):
    matched, mismatched = _replay_all_prefixes_match_oracle(_RICH_SWING_CANDLES)
    assert matched, f"mismatched prefixes: {mismatched}"

    batch = analyze_market_measurements(
        _RICH_SWING_CANDLES, _CONFIG, _HashIdentityProvider()
    )
    assert len(batch.trendlines) > 0, "fixture never produced a confirmed trendline"


def test_incremental_displacement_observations_are_not_duplicated_or_dropped() -> None:
    state = _create_initial_measurement_replay_state(_HashIdentityProvider(), _CONFIG)
    for candle in _RANDOM_WALK_CANDLES:
        state = _advance_measurement_replay_state(state, candle, _CONFIG)

    incremental = _measurement_replay_state_to_analysis(state)
    batch = analyze_market_measurements(
        _RANDOM_WALK_CANDLES, _CONFIG, _HashIdentityProvider()
    )

    candle_ids = [obs.candle_record_id for obs in incremental.displacement_observations]
    assert len(candle_ids) == len(set(candle_ids)), (
        "duplicate displacement observation for the same candle"
    )
    assert incremental.displacement_observations == batch.displacement_observations
    assert len(incremental.displacement_observations) == (
        len(_RANDOM_WALK_CANDLES) - _CONFIG.range_context_window
    )


def test_measurement_state_equivalence_beyond_the_range_context_window() -> None:
    window = _CONFIG.range_context_window
    state = _create_initial_measurement_replay_state(_HashIdentityProvider(), _CONFIG)
    for k, candle in enumerate(_RANDOM_WALK_CANDLES, start=1):
        state = _advance_measurement_replay_state(state, candle, _CONFIG)
        if k <= window:
            continue
        incremental = _measurement_replay_state_to_analysis(state)
        batch = analyze_market_measurements(
            _RANDOM_WALK_CANDLES[:k], _CONFIG, _HashIdentityProvider()
        )
        assert incremental == batch, f"mismatch beyond range_context_window at k={k}"


def test_incremental_measurement_output_preserves_deterministic_ordering_against_the_batch_oracle() -> (
    None
):
    state = _create_initial_measurement_replay_state(_HashIdentityProvider(), _CONFIG)
    for candle in _RICH_SWING_CANDLES:
        state = _advance_measurement_replay_state(state, candle, _CONFIG)

    incremental = _measurement_replay_state_to_analysis(state)
    batch = analyze_market_measurements(
        _RICH_SWING_CANDLES, _CONFIG, _HashIdentityProvider()
    )

    assert [s.record_id for s in incremental.confirmed_swings] == [
        s.record_id for s in batch.confirmed_swings
    ]
    assert [z.record_id for z in incremental.support_resistance_zones] == [
        z.record_id for z in batch.support_resistance_zones
    ]
    assert [t.record_id for t in incremental.trendlines] == [
        t.record_id for t in batch.trendlines
    ]
    assert [c.record_id for c in incremental.equal_level_clusters] == [
        c.record_id for c in batch.equal_level_clusters
    ]
    assert [d.record_id for d in incremental.displacement_observations] == [
        d.record_id for d in batch.displacement_observations
    ]


def test_incremental_engine_preserves_identity_equality_against_one_shot_batch_oracle() -> (
    None
):
    state = _create_initial_measurement_replay_state(_HashIdentityProvider(), _CONFIG)
    for candle in _RICH_SWING_CANDLES:
        state = _advance_measurement_replay_state(state, candle, _CONFIG)

    incremental = _measurement_replay_state_to_analysis(state)
    batch = analyze_market_measurements(
        _RICH_SWING_CANDLES, _CONFIG, _HashIdentityProvider()
    )

    assert {s.record_id for s in incremental.confirmed_swings} == {
        s.record_id for s in batch.confirmed_swings
    }
    assert len(incremental.confirmed_swings) > 0


def test_incremental_engine_preserves_content_fingerprint_equality_against_one_shot_batch_oracle() -> (
    None
):
    state = _create_initial_measurement_replay_state(_HashIdentityProvider(), _CONFIG)
    for candle in _RICH_SWING_CANDLES:
        state = _advance_measurement_replay_state(state, candle, _CONFIG)

    incremental = _measurement_replay_state_to_analysis(state)
    batch = analyze_market_measurements(
        _RICH_SWING_CANDLES, _CONFIG, _HashIdentityProvider()
    )

    incremental_fingerprints_by_id = {
        s.record_id: s.content_fingerprint for s in incremental.confirmed_swings
    }
    batch_fingerprints_by_id = {
        s.record_id: s.content_fingerprint for s in batch.confirmed_swings
    }
    assert incremental_fingerprints_by_id == batch_fingerprints_by_id
    assert len(incremental_fingerprints_by_id) > 0


def test_incremental_measurement_state_rejects_a_chronologically_unordered_candle() -> (
    None
):
    state = _create_initial_measurement_replay_state(_HashIdentityProvider(), _CONFIG)
    for candle in _RICH_SWING_CANDLES[:10]:
        state = _advance_measurement_replay_state(state, candle, _CONFIG)

    out_of_order = _candle(
        9999,
        100.0,
        101.0,
        99.0,
        100.0,
        event_time=_RICH_SWING_CANDLES[5].event_time_utc,
    )
    with pytest.raises(UnsortedCandleSequenceError):
        _advance_measurement_replay_state(state, out_of_order, _CONFIG)

    ambiguous = _candle(
        9998,
        100.0,
        101.0,
        99.0,
        100.0,
        event_time=_RICH_SWING_CANDLES[9].event_time_utc,
    )
    with pytest.raises(AmbiguousEventTimeAnalysisError):
        _advance_measurement_replay_state(state, ambiguous, _CONFIG)


def test_incremental_engine_rolls_back_cleanly_on_a_domain_update_failure() -> None:
    state = _create_initial_measurement_replay_state(_HashIdentityProvider(), _CONFIG)
    for candle in _RICH_SWING_CANDLES[:10]:
        state = _advance_measurement_replay_state(state, candle, _CONFIG)

    candles_before = list(state.candles_so_far)
    swings_before = state.confirmed_swings_so_far

    out_of_order = _candle(
        9999,
        100.0,
        101.0,
        99.0,
        100.0,
        event_time=_RICH_SWING_CANDLES[5].event_time_utc,
    )
    with pytest.raises(UnsortedCandleSequenceError):
        _advance_measurement_replay_state(state, out_of_order, _CONFIG)

    assert state.candles_so_far == candles_before
    assert state.confirmed_swings_so_far == swings_before

    resumed = _advance_measurement_replay_state(state, _RICH_SWING_CANDLES[10], _CONFIG)
    assert len(resumed.candles_so_far) == len(candles_before) + 1
