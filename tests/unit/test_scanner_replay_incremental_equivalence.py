import hashlib
import random
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from itertools import pairwise
from uuid import UUID

import pytest

from btmm_ai_scanner.config.enums import InternalSymbol, Timeframe
from btmm_ai_scanner.contracts.normalized_candle import NormalizedCandle
from btmm_ai_scanner.contracts.provenance_record import EvidenceClassification
from btmm_ai_scanner.contracts.raw_candle import CandleCompleteness, CandleVolumeKind
from btmm_ai_scanner.contracts.types import SemVer
from btmm_ai_scanner.domain.analyzer import (
    AmbiguousEventTimeAnalysisError,
    MarketMeasurementAnalysis,
    UnsortedCandleSequenceError,
    _advance_measurement_replay_state,
    _atr_incremental_step,
    _AtrIncrementalState,
    _create_initial_measurement_replay_state,
    _measurement_replay_state_to_analysis,
    analyze_market_measurements,
)
from btmm_ai_scanner.domain.configuration import MarketMeasurementConfiguration
from btmm_ai_scanner.domain.enums import DerivedOutputType, SwingType
from btmm_ai_scanner.domain.equal_levels import EqualLevelCluster
from btmm_ai_scanner.domain.swings import (
    ConfirmedSwing,
    _merge_adjacent_plateaus,
    _supersede_same_direction_runs,
)
from btmm_ai_scanner.domain.trendlines import Trendline
from btmm_ai_scanner.measurements.atr import compute_atr_series
from btmm_ai_scanner.poi.analyzer import (
    PoiAnalysis,
    PoiTimeframeInput,
    _advance_poi_replay_state,
    _create_initial_poi_replay_state,
    _poi_replay_state_to_analysis,
    analyze_pois,
)
from btmm_ai_scanner.poi.configuration import PoiConfiguration
from btmm_ai_scanner.poi.enums import (
    PoiLifecycleStatus,
    PoiLifecycleTransitionType,
)
from btmm_ai_scanner.structure.analyzer import (
    StructureAnalysis,
    _advance_structure_replay_state,
    _create_initial_structure_replay_state,
    _structure_replay_state_to_analysis,
    analyze_structure_state,
)
from btmm_ai_scanner.structure.configuration import StructureConfiguration
from btmm_ai_scanner.structure.enums import StructureDirection, StructureTransitionType

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


# =====================================================================
# Subsystem 2b-final: incremental equal-level / trendline frontier.
# Every assertion below uses the one-shot batch analyze_market_measurements
# as the oracle and compares the COMPLETE MarketMeasurementAnalysis at the
# controlled prefixes, never counts alone.
# =====================================================================

_FRONTIER_SEEDS = (42, 7, 99, 123)
_FRONTIER_CANDLES = {
    seed: _build(_random_walk_prices(180, seed=seed)) for seed in _FRONTIER_SEEDS
}


def _batch_analysis(
    candles: tuple[NormalizedCandle, ...], k: int
) -> MarketMeasurementAnalysis:
    return analyze_market_measurements(candles[:k], _CONFIG, _HashIdentityProvider())


def _incremental_series(
    candles: tuple[NormalizedCandle, ...],
) -> list[MarketMeasurementAnalysis]:
    """Full incremental MarketMeasurementAnalysis at every prefix (no oracle
    calls — used to locate the prefixes where a scenario occurs)."""
    state = _create_initial_measurement_replay_state(_HashIdentityProvider(), _CONFIG)
    series: list[MarketMeasurementAnalysis] = []
    for candle in candles:
        state = _advance_measurement_replay_state(state, candle, _CONFIG)
        series.append(_measurement_replay_state_to_analysis(state))
    return series


@pytest.mark.parametrize("seed", _FRONTIER_SEEDS)
def test_incremental_frontier_matches_batch_oracle_at_every_prefix(seed: int) -> None:
    matched, mismatched = _replay_all_prefixes_match_oracle(_FRONTIER_CANDLES[seed])
    assert matched, f"seed={seed} mismatched prefixes: {mismatched}"


def test_frontier_does_not_treat_confirmed_swings_as_append_only() -> None:
    """Out-of-order confirmation inserts a swing at a MIDDLE list position, so
    an existing entry changes (not a pure tail append). The trendline frontier
    must invalidate/re-arm rather than assume append-only; assert the scenario
    occurs and the full analysis still matches the oracle at those prefixes."""
    candles = _FRONTIER_CANDLES[7]
    series = _incremental_series(candles)
    non_append_prefixes: list[int] = []
    previous: tuple[ConfirmedSwing, ...] = ()
    for k, incremental in enumerate(series, start=1):
        swings = incremental.confirmed_swings
        common = 0
        limit = min(len(previous), len(swings))
        while common < limit and previous[common] == swings[common]:
            common += 1
        if common < len(previous):
            non_append_prefixes.append(k)
        previous = swings

    assert non_append_prefixes, (
        "fixture never produced a non-append confirmed-swing change"
    )
    for k in non_append_prefixes:
        assert series[k - 1] == _batch_analysis(candles, k), (
            f"prefix {k} diverged from the batch oracle"
        )


def test_trendline_created_from_a_newly_appended_anchor_matches_the_oracle() -> None:
    candles = _FRONTIER_CANDLES[42]
    series = _incremental_series(candles)
    added_prefixes: list[int] = []
    previous_ids: set[UUID] = set()
    for k, incremental in enumerate(series, start=1):
        ids = {t.record_id for t in incremental.trendlines}
        if ids - previous_ids:
            added_prefixes.append(k)
        previous_ids = ids

    assert added_prefixes, "fixture never created a trendline"
    for k in added_prefixes:
        batch = _batch_analysis(candles, k)
        assert series[k - 1] == batch
        assert [t.record_id for t in series[k - 1].trendlines] == [
            t.record_id for t in batch.trendlines
        ], f"trendline canonical ordering diverged at prefix {k}"


def test_trendline_invalidated_after_a_frontier_change_matches_the_oracle() -> None:
    candles = _FRONTIER_CANDLES[7]
    series = _incremental_series(candles)
    removed_prefixes: list[int] = []
    previous_ids: set[UUID] = set()
    for k, incremental in enumerate(series, start=1):
        ids = {t.record_id for t in incremental.trendlines}
        if previous_ids - ids:
            removed_prefixes.append(k)
        previous_ids = ids

    assert removed_prefixes, "fixture never invalidated a previously emitted trendline"
    for k in removed_prefixes:
        assert series[k - 1] == _batch_analysis(candles, k)
        assert series[k - 2] == _batch_analysis(candles, k - 1)


def test_unaffected_historical_trendline_is_preserved_to_the_final_prefix() -> None:
    candles = _FRONTIER_CANDLES[123]
    series = _incremental_series(candles)
    final = series[-1]
    assert len(final.trendlines) >= 2, "fixture too thin to test preservation"
    final_by_id = {t.record_id: t for t in final.trendlines}

    first_seen: dict[UUID, tuple[int, Trendline]] = {}
    for k, incremental in enumerate(series, start=1):
        for trendline in incremental.trendlines:
            if (
                trendline.record_id in final_by_id
                and trendline.record_id not in first_seen
            ):
                first_seen[trendline.record_id] = (k, trendline)

    preserved = [
        record_id
        for record_id, (k, trendline) in first_seen.items()
        if k < len(series) - 5 and trendline == final_by_id[record_id]
    ]
    assert preserved, "no historical trendline survived unchanged to the final prefix"
    assert final == _batch_analysis(candles, len(candles))


def test_existing_equal_level_cluster_membership_change_matches_the_oracle() -> None:
    candles = _FRONTIER_CANDLES[123]
    series = _incremental_series(candles)
    changed_prefixes: list[int] = []
    previous: dict[UUID, tuple[UUID, ...]] = {}
    for k, incremental in enumerate(series, start=1):
        current = {
            c.record_id: c.component_swing_record_ids
            for c in incremental.equal_level_clusters
        }
        for record_id, members in previous.items():
            if record_id in current and current[record_id] != members:
                changed_prefixes.append(k)
                break
        previous = current

    assert changed_prefixes, (
        "fixture never changed an existing equal-level cluster's membership"
    )
    for k in changed_prefixes:
        assert series[k - 1] == _batch_analysis(candles, k)


def test_unaffected_equal_level_cluster_preserved_when_another_changes() -> None:
    candles = _FRONTIER_CANDLES[99]
    series = _incremental_series(candles)
    saw_preserved_across_change = False
    previous: dict[UUID, EqualLevelCluster] = {}
    for k, incremental in enumerate(series, start=1):
        current: dict[UUID, EqualLevelCluster] = {
            c.record_id: c for c in incremental.equal_level_clusters
        }
        if previous and set(current) != set(previous):
            preserved = [
                record_id
                for record_id in current
                if record_id in previous and current[record_id] == previous[record_id]
            ]
            if preserved:
                saw_preserved_across_change = True
                assert incremental == _batch_analysis(candles, k)
        previous = current

    assert saw_preserved_across_change, (
        "fixture never preserved an equal-level cluster across a set change"
    )


def test_frontier_identity_and_fingerprint_equality_against_the_oracle() -> None:
    candles = _FRONTIER_CANDLES[123]
    state = _create_initial_measurement_replay_state(_HashIdentityProvider(), _CONFIG)
    saw_trendline = False
    saw_cluster = False
    for k, candle in enumerate(candles, start=1):
        state = _advance_measurement_replay_state(state, candle, _CONFIG)
        incremental = _measurement_replay_state_to_analysis(state)
        batch = _batch_analysis(candles, k)

        assert [t.record_id for t in incremental.trendlines] == [
            t.record_id for t in batch.trendlines
        ]
        assert {t.record_id: t.content_fingerprint for t in incremental.trendlines} == {
            t.record_id: t.content_fingerprint for t in batch.trendlines
        }
        assert [c.record_id for c in incremental.equal_level_clusters] == [
            c.record_id for c in batch.equal_level_clusters
        ]
        assert {
            c.record_id: c.content_fingerprint for c in incremental.equal_level_clusters
        } == {c.record_id: c.content_fingerprint for c in batch.equal_level_clusters}
        if incremental.trendlines:
            saw_trendline = True
        if incremental.equal_level_clusters:
            saw_cluster = True

    assert saw_trendline and saw_cluster


def test_frontier_caches_roll_back_cleanly_on_a_domain_update_failure() -> None:
    state = _create_initial_measurement_replay_state(_HashIdentityProvider(), _CONFIG)
    for candle in _RICH_SWING_CANDLES[:90]:
        state = _advance_measurement_replay_state(state, candle, _CONFIG)

    high_before = state.equal_level_cache_high
    low_before = state.equal_level_cache_low
    trendline_caches_before = state.trendline_caches
    clusters_before = state.equal_level_clusters_so_far
    trendlines_before = state.trendlines_so_far

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

    # The prior state object is never mutated: the very same cache objects
    # (identity, not just equality) survive the failed transition.
    assert state.equal_level_cache_high is high_before
    assert state.equal_level_cache_low is low_before
    assert state.trendline_caches is trendline_caches_before
    assert state.equal_level_clusters_so_far == clusters_before
    assert state.trendlines_so_far == trendlines_before


# =====================================================================
# Subsystem 2c: incremental structure state / transition differential tests.
# Every assertion compares the incremental structure engine
# (_create_initial_structure_replay_state / _advance_structure_replay_state /
# _structure_replay_state_to_analysis) against the UNMODIFIED batch oracle
# analyze_structure_state, at every controlled candle prefix — full
# StructureAnalysis equality (identities, fingerprints, ordering, current
# state), never counts alone. Two fixture styles are used: hand-built
# (candles, swings) for deterministic BOS / CHoCH / priority / protected /
# weak scenarios (mirroring test_break_and_transitions), and measurement-driven
# real swings (reusing the subsystem-2b measurement replay) for the non-append
# confirmed-swing frontier, supersession, and same-length content-change cases.
# =====================================================================

_STRUCT_CONFIG = StructureConfiguration()


def _flat_candle(index: int, close: str) -> NormalizedCandle:
    """A neutral candle whose close is `close` and whose wicks reach ±20, matching
    the deterministic fixtures in test_break_and_transitions."""
    value = float(close)
    return _candle(index, value, value + 20, value - 20, value)


def _flat_build(closes: list[str]) -> tuple[NormalizedCandle, ...]:
    return tuple(_flat_candle(i, c) for i, c in enumerate(closes))


def _hand_swing(
    idx: int,
    swing_type: SwingType,
    price: str,
    pivot_bar_index: int,
    confirmation_bar_index: int,
    candles: tuple[NormalizedCandle, ...],
) -> ConfirmedSwing:
    pivot_time = candles[pivot_bar_index].event_time_utc
    confirmation_time = candles[confirmation_bar_index].availability_time_utc
    return ConfirmedSwing(
        record_id=_record_id(1000 + idx),
        content_fingerprint="a" * 64,
        symbol=InternalSymbol.XAUUSD,
        timeframe=Timeframe.M1,
        swing_type=swing_type,
        pivot_price=Decimal(price),
        pivot_bar_index=pivot_bar_index,
        pivot_candle_record_ids=(candles[pivot_bar_index].record_id,),
        pivot_start_time_utc=pivot_time,
        pivot_end_time_utc=pivot_time,
        local_confirmation_time_utc=pivot_time + timedelta(minutes=1),
        meaningful_confirmation_time_utc=confirmation_time,
        confirmation_candle_id=candles[confirmation_bar_index].record_id,
        pivot_reference_atr=Decimal("1.0"),
        pivot_tie_tolerance=Decimal("0.02"),
        reversal_threshold=Decimal("0.5"),
        reversal_excursion=Decimal("1"),
        availability_time_utc=confirmation_time,
        rule_version=SemVer.parse("1.0.0"),
        contract_version=SemVer.parse("0.1.0"),
        schema_version=SemVer.parse("0.1.0"),
        evidence_classification=EvidenceClassification.ENGINEERING_PROVISIONAL,
        provenance_id=_PROVENANCE_ID,
    )


def _bullish_bootstrap_swings(
    candles: tuple[NormalizedCandle, ...],
) -> tuple[ConfirmedSwing, ...]:
    return (
        _hand_swing(1, SwingType.SWING_LOW, "90", 0, 1, candles),
        _hand_swing(2, SwingType.SWING_HIGH, "100", 2, 3, candles),
        _hand_swing(3, SwingType.SWING_LOW, "91", 4, 5, candles),
        _hand_swing(4, SwingType.SWING_HIGH, "101", 6, 7, candles),
    )


def _bearish_bootstrap_swings(
    candles: tuple[NormalizedCandle, ...],
) -> tuple[ConfirmedSwing, ...]:
    return (
        _hand_swing(1, SwingType.SWING_HIGH, "100", 0, 1, candles),
        _hand_swing(2, SwingType.SWING_LOW, "90", 2, 3, candles),
        _hand_swing(3, SwingType.SWING_HIGH, "99", 4, 5, candles),
        _hand_swing(4, SwingType.SWING_LOW, "89", 6, 7, candles),
    )


def _swings_visible_at(
    swings: tuple[ConfirmedSwing, ...], candle: NormalizedCandle
) -> tuple[ConfirmedSwing, ...]:
    """The confirmed swings a measurement engine would already expose at this
    candle's availability instant (no look-ahead)."""
    return tuple(
        s
        for s in swings
        if s.meaningful_confirmation_time_utc <= candle.availability_time_utc
    )


def _hand_replay_matches_oracle(
    candles: tuple[NormalizedCandle, ...],
    swings: tuple[ConfirmedSwing, ...],
) -> tuple[bool, list[int]]:
    """Drive the incremental structure engine one candle at a time, feeding the
    hand-built swings visible at each prefix, comparing the FULL StructureAnalysis
    against the batch oracle at every prefix."""
    state = _create_initial_structure_replay_state(
        _HashIdentityProvider(), _STRUCT_CONFIG
    )
    mismatched: list[int] = []
    for k, candle in enumerate(candles, start=1):
        visible = _swings_visible_at(swings, candle)
        state = _advance_structure_replay_state(state, candle, visible, _STRUCT_CONFIG)
        incremental = _structure_replay_state_to_analysis(state)
        batch = analyze_structure_state(
            candles[:k], visible, _STRUCT_CONFIG, _HashIdentityProvider()
        )
        if incremental != batch:
            mismatched.append(k)
    return len(mismatched) == 0, mismatched


def _final_hand_analysis(
    candles: tuple[NormalizedCandle, ...],
    swings: tuple[ConfirmedSwing, ...],
) -> StructureAnalysis:
    return analyze_structure_state(
        candles, swings, _STRUCT_CONFIG, _HashIdentityProvider()
    )


def _hand_replay_provider_matches_oracle(
    candles: tuple[NormalizedCandle, ...],
    provider: object,
) -> tuple[bool, list[int], list[tuple[ConfirmedSwing, ...]]]:
    """Like _hand_replay_matches_oracle but the confirmed-swing set at each
    prefix is chosen by `provider(k, candles)`, letting a test drive a deliberate
    same-length, existing-position content change (as a measurement supersession
    would) and confirm the frontier reprocesses it to the oracle exactly."""
    state = _create_initial_structure_replay_state(
        _HashIdentityProvider(), _STRUCT_CONFIG
    )
    mismatched: list[int] = []
    swing_series: list[tuple[ConfirmedSwing, ...]] = []
    for k, candle in enumerate(candles, start=1):
        swings = provider(k, candles)  # type: ignore[operator]
        swing_series.append(swings)
        state = _advance_structure_replay_state(state, candle, swings, _STRUCT_CONFIG)
        incremental = _structure_replay_state_to_analysis(state)
        batch = analyze_structure_state(
            candles[:k], swings, _STRUCT_CONFIG, _HashIdentityProvider()
        )
        if incremental != batch:
            mismatched.append(k)
    return len(mismatched) == 0, mismatched, swing_series


class _MeasurementDrivenResult:
    def __init__(
        self,
        all_match: bool,
        mismatched: list[int],
        swing_series: list[tuple[ConfirmedSwing, ...]],
        analysis_series: list[StructureAnalysis],
        final_state: object,
    ) -> None:
        self.all_match = all_match
        self.mismatched = mismatched
        self.swing_series = swing_series
        self.analysis_series = analysis_series
        self.final_state = final_state


def _measurement_driven_structure(
    candles: tuple[NormalizedCandle, ...],
) -> _MeasurementDrivenResult:
    """Advance the subsystem-2b measurement replay and the subsystem-2c
    structure replay in lockstep, feeding real (non-append-changing) confirmed
    swings into structure, and compare against the batch oracle at every
    prefix."""
    m_state = _create_initial_measurement_replay_state(_HashIdentityProvider(), _CONFIG)
    s_state = _create_initial_structure_replay_state(
        _HashIdentityProvider(), _STRUCT_CONFIG
    )
    mismatched: list[int] = []
    swing_series: list[tuple[ConfirmedSwing, ...]] = []
    analysis_series: list[StructureAnalysis] = []
    for k, candle in enumerate(candles, start=1):
        m_state = _advance_measurement_replay_state(m_state, candle, _CONFIG)
        swings = m_state.confirmed_swings_so_far
        swing_series.append(swings)
        s_state = _advance_structure_replay_state(
            s_state, candle, swings, _STRUCT_CONFIG
        )
        incremental = _structure_replay_state_to_analysis(s_state)
        analysis_series.append(incremental)
        batch = analyze_structure_state(
            candles[:k], swings, _STRUCT_CONFIG, _HashIdentityProvider()
        )
        if incremental != batch:
            mismatched.append(k)
    return _MeasurementDrivenResult(
        len(mismatched) == 0, mismatched, swing_series, analysis_series, s_state
    )


_STRUCT_FRONTIER_SEEDS = (42, 7, 99, 123, 34)
_STRUCT_MEASUREMENT_CANDLES = {
    seed: _build(_random_walk_prices(180, seed=seed)) for seed in _STRUCT_FRONTIER_SEEDS
}


def test_structure_empty_state_matches_the_batch_oracle() -> None:
    state = _create_initial_structure_replay_state(
        _HashIdentityProvider(), _STRUCT_CONFIG
    )
    incremental = _structure_replay_state_to_analysis(state)
    batch = analyze_structure_state((), (), _STRUCT_CONFIG, _HashIdentityProvider())
    assert incremental == batch
    assert incremental.current_state is None
    assert incremental.analyzed_candle_count == 0


def test_structure_initial_protected_high_matches_the_batch_oracle() -> None:
    candles = _flat_build(["95"] * 9)
    swings = _bearish_bootstrap_swings(candles)
    matched, mismatched = _hand_replay_matches_oracle(candles, swings)
    assert matched, f"mismatched prefixes: {mismatched}"
    final = _final_hand_analysis(candles, swings)
    assert final.current_state is not None
    assert final.current_state.direction == StructureDirection.BEARISH
    assert final.current_state.active_protected_high_swing_id == swings[2].record_id


def test_structure_initial_protected_low_matches_the_batch_oracle() -> None:
    candles = _flat_build(["95"] * 9)
    swings = _bullish_bootstrap_swings(candles)
    matched, mismatched = _hand_replay_matches_oracle(candles, swings)
    assert matched, f"mismatched prefixes: {mismatched}"
    final = _final_hand_analysis(candles, swings)
    assert final.current_state is not None
    assert final.current_state.direction == StructureDirection.BULLISH
    assert final.current_state.active_protected_low_swing_id == swings[2].record_id


def test_structure_initial_weak_high_matches_the_batch_oracle() -> None:
    candles = _flat_build(["95"] * 9)
    swings = _bullish_bootstrap_swings(candles)
    matched, mismatched = _hand_replay_matches_oracle(candles, swings)
    assert matched, f"mismatched prefixes: {mismatched}"
    final = _final_hand_analysis(candles, swings)
    assert final.current_state is not None
    assert final.current_state.active_weak_high_swing_id == swings[3].record_id


def test_structure_initial_weak_low_matches_the_batch_oracle() -> None:
    candles = _flat_build(["95"] * 9)
    swings = _bearish_bootstrap_swings(candles)
    matched, mismatched = _hand_replay_matches_oracle(candles, swings)
    assert matched, f"mismatched prefixes: {mismatched}"
    final = _final_hand_analysis(candles, swings)
    assert final.current_state is not None
    assert final.current_state.active_weak_low_swing_id == swings[3].record_id


def test_structure_bullish_bos_matches_the_batch_oracle() -> None:
    candles = _flat_build(["95"] * 8 + ["110"])
    swings = _bullish_bootstrap_swings(candles)
    matched, mismatched = _hand_replay_matches_oracle(candles, swings)
    assert matched, f"mismatched prefixes: {mismatched}"
    final = _final_hand_analysis(candles, swings)
    assert len(final.structure_transitions) == 1
    assert final.structure_transitions[0].transition_type == (
        StructureTransitionType.BULLISH_BOS
    )


def test_structure_bearish_bos_matches_the_batch_oracle() -> None:
    candles = _flat_build(["95"] * 8 + ["70"])
    swings = _bearish_bootstrap_swings(candles)
    matched, mismatched = _hand_replay_matches_oracle(candles, swings)
    assert matched, f"mismatched prefixes: {mismatched}"
    final = _final_hand_analysis(candles, swings)
    assert len(final.structure_transitions) == 1
    assert final.structure_transitions[0].transition_type == (
        StructureTransitionType.BEARISH_BOS
    )


def test_structure_bullish_choch_matches_the_batch_oracle() -> None:
    candles = _flat_build(["95"] * 8 + ["150"])
    swings = _bearish_bootstrap_swings(candles)
    matched, mismatched = _hand_replay_matches_oracle(candles, swings)
    assert matched, f"mismatched prefixes: {mismatched}"
    final = _final_hand_analysis(candles, swings)
    assert len(final.structure_transitions) == 1
    transition = final.structure_transitions[0]
    assert transition.transition_type == StructureTransitionType.BULLISH_CHOCH
    assert final.current_state is not None
    assert final.current_state.direction == StructureDirection.BULLISH


def test_structure_bearish_choch_matches_the_batch_oracle() -> None:
    candles = _flat_build(["95"] * 8 + ["30"])
    swings = _bullish_bootstrap_swings(candles)
    matched, mismatched = _hand_replay_matches_oracle(candles, swings)
    assert matched, f"mismatched prefixes: {mismatched}"
    final = _final_hand_analysis(candles, swings)
    assert len(final.structure_transitions) == 1
    transition = final.structure_transitions[0]
    assert transition.transition_type == StructureTransitionType.BEARISH_CHOCH
    assert final.current_state is not None
    assert final.current_state.direction == StructureDirection.BEARISH


def test_structure_bos_versus_choch_priority_matches_the_batch_oracle() -> None:
    # weak_high (75) priced BELOW protected_low (91): a single close (80) breaches
    # both; CHoCH must win, BOS must never also fire for the same candle.
    candles = _flat_build(["95"] * 8 + ["80"])
    swings = (
        _hand_swing(1, SwingType.SWING_LOW, "90", 0, 1, candles),
        _hand_swing(2, SwingType.SWING_HIGH, "70", 2, 3, candles),
        _hand_swing(3, SwingType.SWING_LOW, "91", 4, 5, candles),
        _hand_swing(4, SwingType.SWING_HIGH, "75", 6, 7, candles),
    )
    matched, mismatched = _hand_replay_matches_oracle(candles, swings)
    assert matched, f"mismatched prefixes: {mismatched}"
    final = _final_hand_analysis(candles, swings)
    assert len(final.structure_transitions) == 1
    assert final.structure_transitions[0].transition_type == (
        StructureTransitionType.BEARISH_CHOCH
    )


def test_structure_one_transition_per_candle_matches_the_batch_oracle() -> None:
    # 102 breaks weak_high (101) but does not cross protected_low (91): exactly
    # one BOS, never two transitions, for the breaking candle.
    candles = _flat_build(["95"] * 8 + ["102"])
    swings = _bullish_bootstrap_swings(candles)
    matched, mismatched = _hand_replay_matches_oracle(candles, swings)
    assert matched, f"mismatched prefixes: {mismatched}"
    state = _create_initial_structure_replay_state(
        _HashIdentityProvider(), _STRUCT_CONFIG
    )
    for candle in candles:
        state = _advance_structure_replay_state(
            state, candle, _swings_visible_at(swings, candle), _STRUCT_CONFIG
        )
    assert len(state.structure_transitions_so_far) == 1


def test_structure_protected_level_replacement_matches_the_batch_oracle() -> None:
    # A bullish CHoCH breaks the active protected_high and installs a fresh
    # protected_low; the replacement must match the oracle at every prefix.
    candles = _flat_build(["95"] * 8 + ["150"])
    swings = _bearish_bootstrap_swings(candles)
    matched, mismatched = _hand_replay_matches_oracle(candles, swings)
    assert matched, f"mismatched prefixes: {mismatched}"
    final = _final_hand_analysis(candles, swings)
    assert final.current_state is not None
    assert final.current_state.active_protected_low_swing_id == swings[3].record_id
    assert final.current_state.active_protected_high_swing_id is None


def test_structure_weak_level_replacement_matches_the_batch_oracle() -> None:
    # First BOS retires the initial weak_high; an intervening LOW keeps
    # alternation; a replacement HIGH is later broken by a subsequent candle.
    candles = _flat_build(["95"] * 8 + ["110", "95", "95", "95", "120", "95", "120"])
    bootstrap = _bullish_bootstrap_swings(candles)
    pullback_low = _hand_swing(5, SwingType.SWING_LOW, "93", 9, 10, candles)
    replacement_high = _hand_swing(6, SwingType.SWING_HIGH, "115", 11, 12, candles)
    swings = (*bootstrap, pullback_low, replacement_high)
    matched, mismatched = _hand_replay_matches_oracle(candles, swings)
    assert matched, f"mismatched prefixes: {mismatched}"
    final = _final_hand_analysis(candles, swings)
    assert len(final.structure_transitions) == 2
    assert final.structure_transitions[1].broken_swing_id == replacement_high.record_id


def test_structure_swing_supersession_matches_the_batch_oracle() -> None:
    # Supersession / out-of-order confirmation rewrites an already-emitted
    # confirmed swing's content (a later resolution can insert or replace at a
    # MIDDLE list position, changing an existing entry's value), which the
    # structure frontier must invalidate and replay rather than treat as
    # append-only. Detected as a full-value change at an existing index.
    candles = _STRUCT_MEASUREMENT_CANDLES[34]
    result = _measurement_driven_structure(candles)
    superseded_seen = False
    previous: tuple[ConfirmedSwing, ...] = ()
    for swings in result.swing_series:
        common = 0
        limit = min(len(previous), len(swings))
        while common < limit and previous[common] == swings[common]:
            common += 1
        if common < len(previous):
            superseded_seen = True
        previous = swings
    assert superseded_seen, "fixture never rewrote a prior confirmed-swing entry"
    assert result.all_match, f"mismatched prefixes: {result.mismatched}"


def test_structure_same_length_swing_content_replacement_matches_the_batch_oracle() -> (
    None
):
    # A same-length, same-position content rewrite of an already-confirmed swing
    # is a genuine but (per subsystem 2b) not-reliably-reproducible outcome of
    # bounded synthetic measurement fixtures, so it is driven deterministically
    # here: from candle 10 onward the open HIGH run's representative extends to a
    # higher extreme (price 101 -> 104), rewriting confirmed swing #4 in place
    # (same list length, same index 3). The frontier must reprocess from that
    # event and still match the oracle at every prefix.
    candles = _flat_build(["95"] * 8 + ["96", "97", "98", "97", "96", "97"])
    base = _bullish_bootstrap_swings(candles)
    raised = _hand_swing(7, SwingType.SWING_HIGH, "104", 6, 7, candles)

    def provider(
        k: int, cs: tuple[NormalizedCandle, ...]
    ) -> tuple[ConfirmedSwing, ...]:
        visible = _swings_visible_at(base, cs[k - 1])
        if len(visible) == 4 and k >= 10:
            visible = (*visible[:3], raised)
        return visible

    matched, mismatched, swing_series = _hand_replay_provider_matches_oracle(
        candles, provider
    )
    same_length_change_seen = False
    previous: tuple[ConfirmedSwing, ...] = ()
    for swings in swing_series:
        if len(swings) == len(previous) and swings != previous and previous != ():
            same_length_change_seen = True
        previous = swings
    assert same_length_change_seen, (
        "fixture never produced a same-length confirmed-swing content change"
    )
    assert matched, f"mismatched prefixes: {mismatched}"


def test_structure_non_append_swing_frontier_matches_the_batch_oracle() -> None:
    candles = _STRUCT_MEASUREMENT_CANDLES[7]
    result = _measurement_driven_structure(candles)
    non_append_seen = False
    previous: tuple[ConfirmedSwing, ...] = ()
    for swings in result.swing_series:
        common = 0
        limit = min(len(previous), len(swings))
        while common < limit and previous[common] == swings[common]:
            common += 1
        if common < len(previous):
            non_append_seen = True
        previous = swings
    assert non_append_seen, (
        "fixture never changed an existing confirmed-swing entry (non-append)"
    )
    assert result.all_match, f"mismatched prefixes: {result.mismatched}"


def test_structure_no_event_sequence_matches_the_batch_oracle() -> None:
    candles = _flat_build(["95"] * 12)
    matched, mismatched = _hand_replay_matches_oracle(candles, ())
    assert matched, f"mismatched prefixes: {mismatched}"
    final = _final_hand_analysis(candles, ())
    assert final.structure_transitions == ()
    assert final.current_state is not None
    assert final.current_state.direction == StructureDirection.UNDETERMINED


def test_structure_event_ordering_matches_the_batch_oracle() -> None:
    candles = _STRUCT_MEASUREMENT_CANDLES[99]
    result = _measurement_driven_structure(candles)
    assert result.all_match, f"mismatched prefixes: {result.mismatched}"
    final_incremental = result.analysis_series[-1]
    final_batch = analyze_structure_state(
        candles, result.swing_series[-1], _STRUCT_CONFIG, _HashIdentityProvider()
    )
    assert len(final_batch.structure_transitions) > 0, "fixture produced no transition"
    assert [t.record_id for t in final_incremental.structure_transitions] == [
        t.record_id for t in final_batch.structure_transitions
    ]
    assert [r.record_id for r in final_incremental.swing_relationships] == [
        r.record_id for r in final_batch.swing_relationships
    ]


def test_structure_event_time_equality_against_the_batch_oracle() -> None:
    candles = _STRUCT_MEASUREMENT_CANDLES[123]
    result = _measurement_driven_structure(candles)
    assert result.all_match, f"mismatched prefixes: {result.mismatched}"
    final_incremental = result.analysis_series[-1]
    final_batch = analyze_structure_state(
        candles, result.swing_series[-1], _STRUCT_CONFIG, _HashIdentityProvider()
    )
    assert len(final_batch.structure_transitions) > 0
    assert {
        t.record_id: t.event_time_utc for t in final_incremental.structure_transitions
    } == {t.record_id: t.event_time_utc for t in final_batch.structure_transitions}


def test_structure_availability_time_equality_against_the_batch_oracle() -> None:
    candles = _STRUCT_MEASUREMENT_CANDLES[123]
    result = _measurement_driven_structure(candles)
    assert result.all_match, f"mismatched prefixes: {result.mismatched}"
    final_incremental = result.analysis_series[-1]
    final_batch = analyze_structure_state(
        candles, result.swing_series[-1], _STRUCT_CONFIG, _HashIdentityProvider()
    )
    assert {
        t.record_id: t.availability_time_utc
        for t in final_incremental.structure_transitions
    } == {
        t.record_id: t.availability_time_utc for t in final_batch.structure_transitions
    }
    assert final_incremental.current_state is not None
    assert final_batch.current_state is not None
    assert (
        final_incremental.current_state.availability_time_utc
        == final_batch.current_state.availability_time_utc
    )


def test_structure_identity_equality_against_the_batch_oracle() -> None:
    candles = _STRUCT_MEASUREMENT_CANDLES[42]
    result = _measurement_driven_structure(candles)
    assert result.all_match, f"mismatched prefixes: {result.mismatched}"
    final_incremental = result.analysis_series[-1]
    final_batch = analyze_structure_state(
        candles, result.swing_series[-1], _STRUCT_CONFIG, _HashIdentityProvider()
    )
    assert {t.record_id for t in final_incremental.structure_transitions} == {
        t.record_id for t in final_batch.structure_transitions
    }
    assert final_incremental.current_state is not None
    assert final_batch.current_state is not None
    assert (
        final_incremental.current_state.record_id == final_batch.current_state.record_id
    )


def test_structure_fingerprint_equality_against_the_batch_oracle() -> None:
    candles = _STRUCT_MEASUREMENT_CANDLES[42]
    result = _measurement_driven_structure(candles)
    assert result.all_match, f"mismatched prefixes: {result.mismatched}"
    final_incremental = result.analysis_series[-1]
    final_batch = analyze_structure_state(
        candles, result.swing_series[-1], _STRUCT_CONFIG, _HashIdentityProvider()
    )
    assert {
        t.record_id: t.content_fingerprint
        for t in final_incremental.structure_transitions
    } == {t.record_id: t.content_fingerprint for t in final_batch.structure_transitions}
    assert final_incremental.current_state is not None
    assert final_batch.current_state is not None
    assert (
        final_incremental.current_state.content_fingerprint
        == final_batch.current_state.content_fingerprint
    )


@pytest.mark.parametrize("seed", _STRUCT_FRONTIER_SEEDS)
def test_structure_complete_analysis_equality_at_every_prefix(seed: int) -> None:
    result = _measurement_driven_structure(_STRUCT_MEASUREMENT_CANDLES[seed])
    assert result.all_match, f"seed={seed} mismatched prefixes: {result.mismatched}"


def test_structure_transaction_rollback_leaves_prior_state_untouched() -> None:
    candles = _flat_build(["95"] * 8 + ["110", "95", "95"])
    swings = _bullish_bootstrap_swings(candles)
    state = _create_initial_structure_replay_state(
        _HashIdentityProvider(), _STRUCT_CONFIG
    )
    for candle in candles[:10]:
        state = _advance_structure_replay_state(
            state, candle, _swings_visible_at(swings, candle), _STRUCT_CONFIG
        )

    checkpoints_before = state.checkpoints
    candles_before = state.candles_so_far
    transitions_before = state.structure_transitions_so_far

    replayed = _candle(
        9999,
        95.0,
        115.0,
        75.0,
        95.0,
        event_time=candles[5].event_time_utc,
    )
    with pytest.raises(UnsortedCandleSequenceError):
        _advance_structure_replay_state(
            state, replayed, _swings_visible_at(swings, candles[9]), _STRUCT_CONFIG
        )

    # The prior state object is never mutated: the same checkpoint tuple object
    # (identity, not just equality) survives the failed transition.
    assert state.checkpoints is checkpoints_before
    assert state.candles_so_far == candles_before
    assert state.structure_transitions_so_far == transitions_before

    resumed = _advance_structure_replay_state(
        state, candles[10], _swings_visible_at(swings, candles[10]), _STRUCT_CONFIG
    )
    assert len(resumed.candles_so_far) == len(candles_before) + 1


def test_structure_measurement_to_structure_handoff_matches_the_batch_oracle() -> None:
    candles = _build(_random_walk_prices(200, seed=34))
    result = _measurement_driven_structure(candles)
    assert result.all_match, f"mismatched prefixes: {result.mismatched}"
    # The swings that reached structure are exactly the measurement engine's
    # confirmed swings, and a real transition was produced from them.
    assert result.final_state.confirmed_swings_so_far == result.swing_series[-1]  # type: ignore[attr-defined]
    assert len(result.final_state.structure_transitions_so_far) > 0  # type: ignore[attr-defined]


# =====================================================================
# Subsystem 2d: incremental POI state / lifecycle differential tests.
# Every assertion compares the incremental POI engine
# (_create_initial_poi_replay_state / _advance_poi_replay_state /
# _poi_replay_state_to_analysis) against the UNMODIFIED batch oracle
# analyze_pois((single_bundle,), ...) at every candle prefix — full PoiAnalysis
# equality (observations, lifecycle transitions, overlap relationships, current
# states; identities, fingerprints, ordering), never counts alone. The single
# timeframe is the approved 2d unit (cross-timeframe merge is deferred to the
# 2f kernel). Real measurement output is fed from the subsystem-2b measurement
# replay, so these tests double as the measurement-to-POI handoff proof.
# =====================================================================

_POI_CONFIG = PoiConfiguration(minimum_price_tick=Decimal("0.01"))
_POI_SEEDS = (42, 7, 34, 123)
_POI_CANDLES = {
    seed: _build(_random_walk_prices(120, seed=seed)) for seed in _POI_SEEDS
}


class _PoiDrivenResult:
    def __init__(
        self,
        all_match: bool,
        mismatched: list[int],
        analysis_series: list[PoiAnalysis],
        measurement_series: list[MarketMeasurementAnalysis],
        final_state: object,
    ) -> None:
        self.all_match = all_match
        self.mismatched = mismatched
        self.analysis_series = analysis_series
        self.measurement_series = measurement_series
        self.final_state = final_state

    def statuses_seen(self) -> set[PoiLifecycleStatus]:
        return {
            s.poi_lifecycle_status
            for analysis in self.analysis_series
            for s in analysis.current_poi_states
        }

    def transition_types(self) -> set[PoiLifecycleTransitionType]:
        return {
            t.transition_type
            for t in self.analysis_series[-1].poi_lifecycle_transitions
        }


def _measurement_driven_poi(
    candles: tuple[NormalizedCandle, ...],
) -> _PoiDrivenResult:
    """Advance the subsystem-2b measurement replay and the subsystem-2d POI
    replay in lockstep, feeding real (non-append-changing) measurement output
    into POI, and compare against analyze_pois((bundle,), ...) at every prefix."""
    m_state = _create_initial_measurement_replay_state(_HashIdentityProvider(), _CONFIG)
    p_state = _create_initial_poi_replay_state(_HashIdentityProvider(), _POI_CONFIG)
    mismatched: list[int] = []
    analysis_series: list[PoiAnalysis] = []
    measurement_series: list[MarketMeasurementAnalysis] = []
    for k, candle in enumerate(candles, start=1):
        m_state = _advance_measurement_replay_state(m_state, candle, _CONFIG)
        measurement = _measurement_replay_state_to_analysis(m_state)
        measurement_series.append(measurement)
        p_state = _advance_poi_replay_state(p_state, candle, measurement, _POI_CONFIG)
        incremental = _poi_replay_state_to_analysis(p_state)
        analysis_series.append(incremental)
        batch = analyze_pois(
            (PoiTimeframeInput(candle.timeframe, candles[:k], measurement),),
            _POI_CONFIG,
            _HashIdentityProvider(),
        )
        if incremental != batch:
            mismatched.append(k)
    return _PoiDrivenResult(
        len(mismatched) == 0,
        mismatched,
        analysis_series,
        measurement_series,
        p_state,
    )


_poi_driven_cache: dict[int, _PoiDrivenResult] = {}


def _poi_driven(seed: int) -> _PoiDrivenResult:
    if seed not in _poi_driven_cache:
        _poi_driven_cache[seed] = _measurement_driven_poi(_POI_CANDLES[seed])
    return _poi_driven_cache[seed]


def test_poi_empty_state_matches_the_batch_oracle() -> None:
    state = _create_initial_poi_replay_state(_HashIdentityProvider(), _POI_CONFIG)
    incremental = _poi_replay_state_to_analysis(state)
    batch = analyze_pois((), _POI_CONFIG, _HashIdentityProvider())
    assert incremental == batch
    assert incremental.poi_observations == ()
    assert incremental.current_poi_states == ()


def test_poi_observations_created_match_the_batch_oracle() -> None:
    result = _poi_driven(42)
    assert result.all_match, f"mismatched prefixes: {result.mismatched}"
    assert len(result.analysis_series[-1].poi_observations) > 0


def test_poi_no_breach_lifecycle_matches_the_batch_oracle() -> None:
    result = _poi_driven(123)
    assert PoiLifecycleStatus.NO_BREACH in result.statuses_seen()
    assert result.all_match, f"mismatched prefixes: {result.mismatched}"


def test_poi_close_breach_candidate_matches_the_batch_oracle() -> None:
    result = _poi_driven(123)
    assert PoiLifecycleStatus.CLOSE_BREACH_CANDIDATE in result.statuses_seen()
    assert result.all_match, f"mismatched prefixes: {result.mismatched}"


def test_poi_reclaim_confirmed_transition_matches_the_batch_oracle() -> None:
    result = _poi_driven(42)
    assert PoiLifecycleTransitionType.RECLAIM_CONFIRMED in result.transition_types()
    assert result.all_match, f"mismatched prefixes: {result.mismatched}"


def test_poi_displacement_after_reclaim_transition_matches_the_batch_oracle() -> None:
    result = _poi_driven(42)
    assert (
        PoiLifecycleTransitionType.DISPLACEMENT_AFTER_RECLAIM_CONFIRMED
        in result.transition_types()
    )
    assert result.all_match, f"mismatched prefixes: {result.mismatched}"


def test_poi_false_invalidation_matches_the_batch_oracle() -> None:
    result = _poi_driven(42)
    assert PoiLifecycleStatus.FALSE_INVALIDATION_CONFIRMED in result.statuses_seen()
    assert result.all_match, f"mismatched prefixes: {result.mismatched}"


def test_poi_reclaim_without_displacement_matches_the_batch_oracle() -> None:
    result = _poi_driven(42)
    assert PoiLifecycleStatus.RECLAIM_WITHOUT_DISPLACEMENT in result.statuses_seen()
    assert result.all_match, f"mismatched prefixes: {result.mismatched}"


def test_poi_reclaim_failed_matches_the_batch_oracle() -> None:
    result = _poi_driven(42)
    assert PoiLifecycleStatus.RECLAIM_FAILED in result.statuses_seen()
    assert result.all_match, f"mismatched prefixes: {result.mismatched}"


def test_poi_genuine_invalidation_is_terminal_and_matches_the_batch_oracle() -> None:
    result = _poi_driven(42)
    assert PoiLifecycleStatus.GENUINE_INVALIDATION_CONFIRMED in result.statuses_seen()
    assert result.all_match, f"mismatched prefixes: {result.mismatched}"
    # Every POI whose current status is a genuine invalidation has a terminal,
    # result-cached lifecycle walk in the final incremental state.
    final = result.analysis_series[-1]
    terminal_ids = {
        s.poi_record_id
        for s in final.current_poi_states
        if s.poi_lifecycle_status == PoiLifecycleStatus.GENUINE_INVALIDATION_CONFIRMED
    }
    assert terminal_ids
    for record_id in terminal_ids:
        assert result.final_state.lifecycle_states[record_id].terminal  # type: ignore[attr-defined]


def test_poi_taps_and_freshness_match_the_batch_oracle() -> None:
    result = _poi_driven(42)
    final = result.analysis_series[-1]
    interacted = [
        s for s in final.current_poi_states if s.freshness_status.value == "INTERACTED"
    ]
    assert interacted, "fixture never produced an interacted (tapped) POI"
    assert any(s.tap_count > 0 and s.tap_classification is not None for s in interacted)
    assert result.all_match, f"mismatched prefixes: {result.mismatched}"


def test_poi_overlap_relationships_match_the_batch_oracle() -> None:
    result = _poi_driven(42)
    assert len(result.analysis_series[-1].poi_overlap_relationships) > 0
    assert result.all_match, f"mismatched prefixes: {result.mismatched}"


def test_poi_not_applicable_period_and_liquidity_match_the_batch_oracle() -> None:
    result = _poi_driven(42)
    final = result.analysis_series[-1]
    not_applicable = [
        s
        for s in final.current_poi_states
        if s.poi_lifecycle_status == PoiLifecycleStatus.NOT_APPLICABLE
    ]
    assert not_applicable, "fixture never produced a NOT_APPLICABLE POI"
    period_or_liquidity = [
        o
        for o in final.poi_observations
        if o.poi_type.value.endswith(("_HIGH", "_LOW"))
        or o.poi_type.value.endswith("_LIQUIDITY")
    ]
    assert period_or_liquidity
    assert result.all_match, f"mismatched prefixes: {result.mismatched}"


def test_poi_reference_zone_from_measurement_matches_the_batch_oracle() -> None:
    result = _poi_driven(34)
    reference_zone_types = {
        "SUPPORT_ZONE",
        "RESISTANCE_ZONE",
        "EQUAL_HIGHS_LIQUIDITY",
        "EQUAL_LOWS_LIQUIDITY",
    }
    seen = {
        o.poi_type.value
        for o in result.analysis_series[-1].poi_observations
        if o.poi_type.value in reference_zone_types
    }
    assert seen, "fixture never produced a measurement-sourced reference-zone POI"
    assert result.all_match, f"mismatched prefixes: {result.mismatched}"


def test_poi_non_append_measurement_frontier_matches_the_batch_oracle() -> None:
    # The measurement engine's confirmed swings feed reference-zone POIs and can
    # change non-append; the POI engine must re-derive the affected observations
    # and still match the oracle at every prefix.
    result = _poi_driven(34)
    non_append_seen = False
    previous: tuple[ConfirmedSwing, ...] = ()
    for measurement in result.measurement_series:
        swings = measurement.confirmed_swings
        common = 0
        limit = min(len(previous), len(swings))
        while common < limit and previous[common] == swings[common]:
            common += 1
        if common < len(previous):
            non_append_seen = True
        previous = swings
    assert non_append_seen, "fixture never changed an existing confirmed swing"
    assert result.all_match, f"mismatched prefixes: {result.mismatched}"


def test_poi_live_versus_terminal_ownership() -> None:
    result = _poi_driven(42)
    final = result.analysis_series[-1]
    live_ids = {o.record_id for o in result.final_state.live_pois}  # type: ignore[attr-defined]
    genuinely_invalidated = {
        s.poi_record_id
        for s in final.current_poi_states
        if s.poi_lifecycle_status == PoiLifecycleStatus.GENUINE_INVALIDATION_CONFIRMED
    }
    assert genuinely_invalidated
    # A genuinely-invalidated POI is terminal and never counted as live.
    assert not (live_ids & genuinely_invalidated)


def test_poi_no_lookahead_observations_never_precede_availability() -> None:
    candles = _POI_CANDLES[42]
    result = _poi_driven(42)
    for k, analysis in enumerate(result.analysis_series, start=1):
        visible_cutoff = candles[k - 1].availability_time_utc
        for observation in analysis.poi_observations:
            assert observation.availability_time_utc <= visible_cutoff
    assert result.all_match, f"mismatched prefixes: {result.mismatched}"


def test_poi_ordering_matches_the_batch_oracle() -> None:
    seed = 34
    result = _poi_driven(seed)
    assert result.all_match, f"mismatched prefixes: {result.mismatched}"
    final_incremental = result.analysis_series[-1]
    measurement = result.measurement_series[-1]
    final_batch = analyze_pois(
        (PoiTimeframeInput(Timeframe.M1, _POI_CANDLES[seed], measurement),),
        _POI_CONFIG,
        _HashIdentityProvider(),
    )
    assert [o.record_id for o in final_incremental.poi_observations] == [
        o.record_id for o in final_batch.poi_observations
    ]
    assert [t.record_id for t in final_incremental.poi_lifecycle_transitions] == [
        t.record_id for t in final_batch.poi_lifecycle_transitions
    ]
    assert [
        r.evaluated_at_time_utc for r in final_incremental.poi_overlap_relationships
    ] == [r.evaluated_at_time_utc for r in final_batch.poi_overlap_relationships]


def test_poi_identity_equality_matches_the_batch_oracle() -> None:
    seed = 42
    result = _poi_driven(seed)
    assert result.all_match, f"mismatched prefixes: {result.mismatched}"
    final_incremental = result.analysis_series[-1]
    measurement = result.measurement_series[-1]
    final_batch = analyze_pois(
        (PoiTimeframeInput(Timeframe.M1, _POI_CANDLES[seed], measurement),),
        _POI_CONFIG,
        _HashIdentityProvider(),
    )
    assert {o.record_id for o in final_incremental.poi_observations} == {
        o.record_id for o in final_batch.poi_observations
    }
    assert {s.record_id for s in final_incremental.current_poi_states} == {
        s.record_id for s in final_batch.current_poi_states
    }
    assert len(final_incremental.poi_observations) > 0


def test_poi_fingerprint_equality_matches_the_batch_oracle() -> None:
    seed = 42
    result = _poi_driven(seed)
    assert result.all_match, f"mismatched prefixes: {result.mismatched}"
    final_incremental = result.analysis_series[-1]
    measurement = result.measurement_series[-1]
    final_batch = analyze_pois(
        (PoiTimeframeInput(Timeframe.M1, _POI_CANDLES[seed], measurement),),
        _POI_CONFIG,
        _HashIdentityProvider(),
    )
    assert {
        o.record_id: o.content_fingerprint for o in final_incremental.poi_observations
    } == {o.record_id: o.content_fingerprint for o in final_batch.poi_observations}
    assert {
        s.record_id: s.content_fingerprint for s in final_incremental.current_poi_states
    } == {s.record_id: s.content_fingerprint for s in final_batch.current_poi_states}


@pytest.mark.parametrize("seed", _POI_SEEDS)
def test_poi_complete_analysis_equality_at_every_prefix(seed: int) -> None:
    result = _poi_driven(seed)
    assert result.all_match, f"seed={seed} mismatched prefixes: {result.mismatched}"


def test_poi_transaction_rollback_leaves_prior_state_untouched() -> None:
    candles = _POI_CANDLES[42]
    state = _create_initial_poi_replay_state(_HashIdentityProvider(), _POI_CONFIG)
    for k in range(1, 41):
        measurement = analyze_market_measurements(
            candles[:k], _CONFIG, _HashIdentityProvider()
        )
        state = _advance_poi_replay_state(
            state, candles[k - 1], measurement, _POI_CONFIG
        )

    lifecycle_states_before = state.lifecycle_states
    candles_before = state.candles_so_far
    observations_before = state.poi_observations_so_far

    measurement = analyze_market_measurements(
        candles[:40], _CONFIG, _HashIdentityProvider()
    )
    out_of_order = _candle(
        9999,
        100.0,
        101.0,
        99.0,
        100.0,
        event_time=candles[5].event_time_utc,
    )
    with pytest.raises(UnsortedCandleSequenceError):
        _advance_poi_replay_state(state, out_of_order, measurement, _POI_CONFIG)

    # The prior state object — including the per-POI lifecycle dict (identity,
    # not just equality) — survives the failed transition unchanged.
    assert state.lifecycle_states is lifecycle_states_before
    assert state.candles_so_far == candles_before
    assert state.poi_observations_so_far == observations_before

    resumed = _advance_poi_replay_state(state, candles[40], measurement, _POI_CONFIG)
    assert len(resumed.candles_so_far) == len(candles_before) + 1


def test_poi_measurement_to_poi_handoff_matches_the_batch_oracle() -> None:
    # The measurement analyses that reached POI are exactly the subsystem-2b
    # measurement replay's output, and real lifecycle transitions were produced.
    result = _poi_driven(42)
    assert result.all_match, f"mismatched prefixes: {result.mismatched}"
    assert len(result.analysis_series[-1].poi_lifecycle_transitions) > 0
    assert result.final_state.candles_so_far == _POI_CANDLES[42]  # type: ignore[attr-defined]
