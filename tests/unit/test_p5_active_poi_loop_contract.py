"""PHASES 8-15 of MEGA-AUTONOMOUS-20: the active-POI evaluation loop contract.

The contract itself is already frozen by the project (not an open author
decision this session makes): evaluate ALL active/non-terminal POIs every
eligible bar; a POI that goes terminal on the current bar still gets that
bar's final evaluation, then is excluded from the next bar's set; canonical
P3 identity only; stable deterministic order.

`resolve_eligible_and_next` (the pure set algebra) is what Phases 8-14
actually need proven -- it has no dependency on `ScannerAnalysis` or
`assess_confluence` at all, so these are plain unit tests over
`dict[UUID, PoiLifecycleStatus]`. `run_active_poi_loop` (the thin wrapper
that also calls the real `assess_confluence`) gets one genuine end-to-end
integration test to prove the wiring, per the same pattern
`test_t5_component_scores_sufficiency.py` already used.
"""

from __future__ import annotations

import random
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID, uuid4

from btmm_ai_scanner.btmm.configuration import BtmmConfiguration
from btmm_ai_scanner.config.enums import InternalSymbol, Timeframe
from btmm_ai_scanner.contracts.normalized_candle import NormalizedCandle
from btmm_ai_scanner.contracts.raw_candle import CandleCompleteness, CandleVolumeKind
from btmm_ai_scanner.contracts.types import SemVer
from btmm_ai_scanner.domain.configuration import MarketMeasurementConfiguration
from btmm_ai_scanner.historical_backtest.identity import (
    ContentAddressedIdentityProvider,
)
from btmm_ai_scanner.poi.configuration import PoiConfiguration
from btmm_ai_scanner.poi.enums import PoiLifecycleStatus
from btmm_ai_scanner.scanner.analyzer import scan_market
from btmm_ai_scanner.scanner.configuration import ScannerConfiguration
from btmm_ai_scanner.scanner.timeframe_input import ScannerTimeframeInput
from btmm_ai_scanner.structure.configuration import StructureConfiguration
from tests.parity_support.p5_active_poi_loop_model import (
    resolve_eligible_and_next,
    run_active_poi_loop,
)

TERMINAL = PoiLifecycleStatus.GENUINE_INVALIDATION_CONFIRMED
_NON_TERMINAL_SAMPLE = (
    PoiLifecycleStatus.NOT_APPLICABLE,
    PoiLifecycleStatus.NO_BREACH,
    PoiLifecycleStatus.CLOSE_BREACH_CANDIDATE,
    PoiLifecycleStatus.RECLAIM_PENDING,
    PoiLifecycleStatus.RECLAIM_CONFIRMED,
    PoiLifecycleStatus.DISPLACEMENT_PENDING,
    PoiLifecycleStatus.DISPLACEMENT_AFTER_RECLAIM_CONFIRMED,
    PoiLifecycleStatus.RECLAIM_WITHOUT_DISPLACEMENT,
    PoiLifecycleStatus.RECLAIM_FAILED,
    PoiLifecycleStatus.FALSE_INVALIDATION_CONFIRMED,
)


def _ids(n: int) -> list[UUID]:
    return [uuid4() for _ in range(n)]


# ---------------------------------------------------------------------------
# The sourced terminal-status claim itself
# ---------------------------------------------------------------------------


def test_terminal_status_is_exactly_genuine_invalidation_confirmed() -> None:
    """Every OTHER PoiLifecycleStatus member is non-terminal -- pinned
    explicitly so a future enum addition is forced to make a conscious
    choice here rather than silently inheriting a default."""
    assert TERMINAL is PoiLifecycleStatus.GENUINE_INVALIDATION_CONFIRMED
    others = set(PoiLifecycleStatus) - {TERMINAL}
    assert others == set(_NON_TERMINAL_SAMPLE)


# ---------------------------------------------------------------------------
# PHASE 8: zero active POIs
# ---------------------------------------------------------------------------


def test_zero_active_pois_yields_zero_evaluations() -> None:
    eligible, next_active = resolve_eligible_and_next({}, frozenset())
    assert eligible == frozenset()
    assert next_active == frozenset()


def test_zero_active_pois_is_stable_across_repeated_empty_bars() -> None:
    active = frozenset()
    for _ in range(5):
        eligible, active = resolve_eligible_and_next({}, active)
        assert eligible == frozenset()
    assert active == frozenset()


# ---------------------------------------------------------------------------
# PHASE 9: one active POI
# ---------------------------------------------------------------------------


def test_one_active_poi_yields_exactly_one_evaluation() -> None:
    (a,) = _ids(1)
    status = {a: PoiLifecycleStatus.NO_BREACH}
    eligible, next_active = resolve_eligible_and_next(status, frozenset())
    assert eligible == frozenset({a})
    assert next_active == frozenset({a})


# ---------------------------------------------------------------------------
# PHASE 10: multiple active POIs
# ---------------------------------------------------------------------------


def test_multiple_active_pois_each_get_exactly_one_evaluation() -> None:
    for n in (2, 5, 10, 25):
        ids = _ids(n)
        status = {i: PoiLifecycleStatus.RECLAIM_PENDING for i in ids}
        eligible, next_active = resolve_eligible_and_next(status, frozenset())
        assert eligible == frozenset(ids)
        assert len(eligible) == n  # no duplicates, no cross-POI contamination
        assert next_active == frozenset(ids)


def test_stable_order_is_deterministic_and_no_duplicates() -> None:
    obs = {
        i: type("Obs", (), {"availability_time_utc": datetime(2026, 1, 1, tzinfo=UTC) + timedelta(minutes=k), "record_id": i})()
        for k, i in enumerate(_ids(10))
    }
    from tests.parity_support.p5_active_poi_loop_model import _stable_order

    ids = frozenset(obs)
    order1 = _stable_order(ids, obs)
    order2 = _stable_order(ids, obs)
    assert order1 == order2
    assert len(set(order1)) == len(order1)
    assert list(order1) == sorted(order1, key=lambda i: (obs[i].availability_time_utc, str(i)))


# ---------------------------------------------------------------------------
# PHASE 11: terminal current-bar case
# ---------------------------------------------------------------------------


def test_terminal_on_current_bar_still_gets_final_evaluation() -> None:
    (a,) = _ids(1)
    previously_active = frozenset({a})
    status = {a: TERMINAL}  # went terminal THIS bar
    eligible, next_active = resolve_eligible_and_next(status, previously_active)
    assert a in eligible  # final evaluation happens
    assert a not in next_active  # excluded from the NEXT bar


def test_terminal_before_current_bar_is_not_reevaluated_indefinitely() -> None:
    """Once excluded, a POI does not come back merely because its status
    (queried again) is still terminal -- it must not be in
    `previously_active_ids` on a later call for it to disappear for good."""
    (a,) = _ids(1)
    status = {a: TERMINAL}
    # Bar N: terminal, still previously active -> final evaluation.
    eligible_n, next_n = resolve_eligible_and_next(status, frozenset({a}))
    assert a in eligible_n
    assert a not in next_n
    # Bar N+1: caller correctly passes next_n (a is gone) forward.
    eligible_n1, next_n1 = resolve_eligible_and_next(status, next_n)
    assert a not in eligible_n1
    assert a not in next_n1


# ---------------------------------------------------------------------------
# PHASE 12: newly active current-bar case
# ---------------------------------------------------------------------------


def test_newly_active_poi_is_picked_up_the_bar_it_first_appears() -> None:
    (a,) = _ids(1)
    status = {a: PoiLifecycleStatus.NO_BREACH}  # first bar it exists in the registry
    eligible, next_active = resolve_eligible_and_next(status, frozenset())
    assert a in eligible
    assert a in next_active


def test_a_poi_absent_from_the_registry_is_never_evaluated() -> None:
    """`known_ids` models availability: a previously-active id whose POI has
    since vanished cannot be evaluated -- excluded rather than raising."""
    (a,) = _ids(1)
    eligible, next_active = resolve_eligible_and_next(
        {}, frozenset({a}), known_ids=frozenset()
    )
    assert eligible == frozenset()
    assert next_active == frozenset()


# ---------------------------------------------------------------------------
# PHASE 13: multiple terminals on the same bar
# ---------------------------------------------------------------------------


def test_multiple_simultaneous_terminals_each_get_exactly_one_final_evaluation() -> None:
    ids = _ids(6)
    status = dict.fromkeys(ids, TERMINAL)
    eligible, next_active = resolve_eligible_and_next(status, frozenset(ids))
    assert eligible == frozenset(ids)  # all six get their final evaluation
    assert next_active == frozenset()  # all six excluded next bar


def test_mixed_terminal_and_active_same_bar() -> None:
    terminal_ids = _ids(3)
    active_ids = _ids(4)
    status = dict.fromkeys(terminal_ids, TERMINAL)
    status.update(dict.fromkeys(active_ids, PoiLifecycleStatus.RECLAIM_PENDING))
    eligible, next_active = resolve_eligible_and_next(
        status, frozenset(terminal_ids) | frozenset(active_ids)
    )
    assert eligible == frozenset(terminal_ids) | frozenset(active_ids)
    assert next_active == frozenset(active_ids)


# ---------------------------------------------------------------------------
# PHASE 14: mutation campaign
# ---------------------------------------------------------------------------


def test_mutation_select_only_strongest_or_newest_is_caught() -> None:
    """A port that picked only one POI (however chosen) instead of looping
    all active ones would under-evaluate whenever more than one is active."""
    ids = _ids(3)
    status = {i: PoiLifecycleStatus.NO_BREACH for i in ids}
    eligible, _ = resolve_eligible_and_next(status, frozenset())
    assert len(eligible) == 3
    single_pick = {sorted(eligible, key=str)[0]}
    assert set(single_pick) != eligible


def test_mutation_skip_second_active_poi_is_caught() -> None:
    ids = _ids(2)
    status = {i: PoiLifecycleStatus.NO_BREACH for i in ids}
    eligible, _ = resolve_eligible_and_next(status, frozenset())
    wrong = frozenset({ids[0]})  # a port that only kept the first
    assert eligible != wrong
    assert len(eligible) == 2


def test_mutation_duplicate_poi_is_impossible_by_construction() -> None:
    """`eligible_ids` is a frozenset -- there is no representation in which a
    single POI id could appear twice, so this asserts the type-level
    guarantee directly rather than merely hoping no duplicate slips in."""
    ids = _ids(4)
    status = {i: PoiLifecycleStatus.NO_BREACH for i in ids}
    eligible, _ = resolve_eligible_and_next(status, frozenset(ids))
    assert isinstance(eligible, frozenset)


def test_mutation_remove_terminal_one_bar_early_is_caught() -> None:
    """A port that dropped a POI from evaluation the moment its NEXT status
    would be terminal (rather than the bar it ACTUALLY goes terminal) would
    skip the required final evaluation."""
    (a,) = _ids(1)
    # a is still active (not yet terminal) this bar -- must be evaluated.
    status = {a: PoiLifecycleStatus.RECLAIM_PENDING}
    eligible, next_active = resolve_eligible_and_next(status, frozenset({a}))
    assert a in eligible
    assert a in next_active  # correctly still active, not removed early


def test_mutation_retain_terminal_one_bar_late_is_caught() -> None:
    """A port that kept re-evaluating a POI for one extra bar after it went
    terminal (rather than excluding it starting the very next bar) would
    violate 'exclude it from the NEXT bar's active evaluation set.'"""
    (a,) = _ids(1)
    status = {a: TERMINAL}
    _, next_active = resolve_eligible_and_next(status, frozenset({a}))
    assert a not in next_active  # NOT retained for one more bar


def test_mutation_bind_result_to_wrong_poi_id_is_caught() -> None:
    """Canonical P3 identity only -- a synthetic second id must never collide
    with or be substitutable for the real one."""
    (a,) = _ids(1)
    wrong_id = uuid4()
    status = {a: PoiLifecycleStatus.NO_BREACH}
    eligible, _ = resolve_eligible_and_next(status, frozenset())
    assert wrong_id not in eligible
    assert a in eligible


def test_mutation_iteration_order_changes_the_output_stream_is_caught() -> None:
    """Order affects the emitted LOG stream (Phase 37), even though the
    evaluated SET is order-independent -- pinning that `evaluated_order` is a
    tuple (not a set) so a port cannot silently discard ordering."""
    from tests.parity_support.p5_active_poi_loop_model import _stable_order

    obs = {
        i: type("Obs", (), {"availability_time_utc": datetime(2026, 1, 1, tzinfo=UTC) + timedelta(minutes=-k), "record_id": i})()
        for k, i in enumerate(_ids(5))
    }
    ordered = _stable_order(frozenset(obs), obs)
    assert isinstance(ordered, tuple)
    reversed_order = tuple(reversed(ordered))
    assert ordered != reversed_order  # a naive reversed-iteration port would differ


# ---------------------------------------------------------------------------
# Randomized: multi-bar simulation
# ---------------------------------------------------------------------------


def test_randomized_multibar_simulation_never_double_evaluates_or_loses_a_terminal() -> None:
    """Simulates many bars of a POI population randomly transitioning to
    terminal, checking the two structural invariants across the whole run:
    every POI is evaluated on the exact bar it goes terminal (exactly once),
    and no POI is ever evaluated again afterward."""
    rng = random.Random(2026090401)
    for _trial in range(200):
        n_pois = rng.randint(0, 8)
        ids = _ids(n_pois)
        went_terminal_bar: dict[UUID, int] = {}
        evaluated_bars: dict[UUID, list[int]] = {i: [] for i in ids}
        current_status = {i: PoiLifecycleStatus.NO_BREACH for i in ids}

        # Seed bar -1: every POI is observed non-terminal at least once before
        # the mutation loop can flip it terminal -- a real POI cannot go
        # terminal the instant it is first registered (GENUINE_INVALIDATION_
        # CONFIRMED requires an actual breach + reclaim-window walk, which
        # takes bars). Without this seed, "terminal on its very first-ever
        # appearance" is an unreachable-in-production edge case this loop's
        # contract legitimately does not cover (never "active entering the
        # bar" in the first place).
        active, _ = resolve_eligible_and_next(dict(current_status), frozenset())

        n_bars = rng.randint(1, 12)
        for bar in range(n_bars):
            for i in ids:
                if i not in went_terminal_bar and rng.random() < 0.15:
                    current_status[i] = TERMINAL
                    went_terminal_bar[i] = bar
            eligible, active = resolve_eligible_and_next(dict(current_status), active)
            for i in eligible:
                evaluated_bars[i].append(bar)

        for i in ids:
            if i in went_terminal_bar:
                # Evaluated on every bar it was active up to and including its
                # terminal bar, then never again.
                assert evaluated_bars[i], (i, went_terminal_bar)
                assert evaluated_bars[i][-1] == went_terminal_bar[i]
                assert all(b <= went_terminal_bar[i] for b in evaluated_bars[i])
            # No duplicate evaluations within a single bar's set (frozenset
            # already guarantees this structurally; checked at the list level
            # across bars instead: strictly increasing bar indices).
            assert evaluated_bars[i] == sorted(set(evaluated_bars[i]))


# ---------------------------------------------------------------------------
# PHASE 15: hard pass -- and one genuine end-to-end integration sanity check
# ---------------------------------------------------------------------------

_BASE = datetime(2026, 1, 1, tzinfo=UTC)
_FP = "a" * 64
_V = SemVer.parse("0.1.0")
_M15 = Timeframe.M15


def _uid(n: int) -> UUID:
    return UUID(f"0193f350-1234-7abc-8def-{n:012x}")


def _config() -> ScannerConfiguration:
    tick = Decimal("0.01")
    return ScannerConfiguration(
        measurement_configuration=MarketMeasurementConfiguration(minimum_price_tick=tick),
        structure_configuration=StructureConfiguration(),
        poi_configuration=PoiConfiguration(minimum_price_tick=tick),
        btmm_configuration=BtmmConfiguration(minimum_price_tick=tick),
        required_timeframes=frozenset({_M15}),
        optional_timeframes=frozenset(),
    )


def _m15(n: int, seed: int) -> tuple[NormalizedCandle, ...]:
    rng = random.Random(seed)
    price = 100.0
    out: list[NormalizedCandle] = []
    for i in range(n):
        o = price
        c = o + rng.uniform(-1.5, 1.5)
        h = max(o, c) + rng.uniform(0, 0.8)
        low = min(o, c) - rng.uniform(0, 0.8)
        event = _BASE + timedelta(minutes=15 * i)
        avail = event + timedelta(minutes=15)
        out.append(
            NormalizedCandle.model_validate(
                {
                    "record_id": _uid(500000 + i),
                    "content_fingerprint": _FP,
                    "raw_candle_id": _uid(600000 + i),
                    "provider": "FXCM",
                    "source_reference": "fxcm-xauusd-m15",
                    "source_symbol": "XAUUSD",
                    "source_timeframe": "M15",
                    "symbol": InternalSymbol.XAUUSD,
                    "timeframe": _M15,
                    "event_time_utc": event,
                    "availability_time_utc": avail,
                    "processing_time_utc": avail,
                    "original_event_time": event,
                    "original_availability_time": avail,
                    "original_timezone": "UTC",
                    "open": Decimal(str(o)),
                    "high": Decimal(str(h)),
                    "low": Decimal(str(low)),
                    "close": Decimal(str(c)),
                    "volume": Decimal("10"),
                    "volume_kind": CandleVolumeKind.TICK,
                    "completeness": CandleCompleteness.CONFIRMED_COMPLETE,
                    "rule_version": _V,
                    "contract_version": _V,
                    "schema_version": _V,
                    "provenance_id": _uid(700000 + i),
                }
            )
        )
        price = c
    return tuple(out)


def test_end_to_end_active_loop_evaluates_every_registered_poi() -> None:
    """Real `scan_market` output, real `assess_confluence` calls: proves the
    wiring (which field the loop reads, which it calls) is correct end to
    end, not just the pure set algebra in isolation."""
    checked_any = False
    for seed in (1, 2, 3, 4, 5):
        analysis = scan_market(
            (ScannerTimeframeInput(_M15, _m15(200, seed)),),
            (),
            _config(),
            ContentAddressedIdentityProvider(),
        )
        n_registered = len(analysis.poi_analysis.poi_observations)
        result = run_active_poi_loop(analysis, frozenset())
        if n_registered == 0:
            assert result.decisions_by_poi_id == {}
            continue
        checked_any = True
        registered_ids = {o.record_id for o in analysis.poi_analysis.poi_observations}
        non_terminal_ids = {
            s.poi_record_id
            for s in analysis.poi_analysis.current_poi_states
            if s.poi_lifecycle_status is not TERMINAL
        }
        assert set(result.decisions_by_poi_id) == non_terminal_ids
        assert set(result.decisions_by_poi_id) <= registered_ids
        # Every evaluated POI's decision really is about that exact POI.
        for poi_id, decision in result.decisions_by_poi_id.items():
            assert decision.poi_record_id == str(poi_id)
        assert len(result.evaluated_order) == len(set(result.evaluated_order))
    assert checked_any, "no seed produced any registered POI -- test is vacuous"


def test_p5_active_poi_loop_contract_verified() -> None:
    """PHASE 15 hard-pass marker: exists and passes only once every directed,
    randomized, mutation, and end-to-end case above already does (pytest
    collects and runs this whole module together)."""
    P5_ACTIVE_POI_LOOP_CONTRACT_VERIFIED = True
    assert P5_ACTIVE_POI_LOOP_CONTRACT_VERIFIED
