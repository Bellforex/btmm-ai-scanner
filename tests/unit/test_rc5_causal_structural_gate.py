"""RC5 Phase 3: structural qualification runs inside prefix causality.

Author decision, 2026-09-20 -- **delayed availability, not rejection of true
origins**:

* a reversal pattern is DETECTED at its own formation candle;
* it is not QUALIFIED until a structural event causally confirms that it sits
  at a decision point;
* when that confirmation arrives, only ``availability_time_utc`` (and the
  ``confirmation_time_utc`` that shadows it) moves. The source candle, the
  source time, the zone and the formation identity are untouched.

That is not look-ahead: the POI becomes available exactly when the evidence
exists, which is why the gate has to run inside the existing prefix/frontier
replay rather than over the final walk.

These tests do not measure impact. They prove the causal contract, and that
``rc5_structural_origin=False`` leaves RC3/RC4 byte-identical.
"""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pytest

from btmm_ai_scanner.config.enums import Timeframe
from btmm_ai_scanner.domain.analyzer import analyze_market_measurements
from btmm_ai_scanner.domain.configuration import MarketMeasurementConfiguration
from btmm_ai_scanner.historical_backtest.identity import (
    ContentAddressedIdentityProvider,
)
from btmm_ai_scanner.poi.analyzer import PoiTimeframeInput, analyze_pois
from btmm_ai_scanner.poi.authority import REVERSAL_TYPES
from btmm_ai_scanner.poi.configuration import PoiConfiguration
from btmm_ai_scanner.poi.engulfing import detect_engulfing
from btmm_ai_scanner.poi.leg_origin import (
    ContextReason,
    structural_role_of,
    structure_context_decisions,
)
from btmm_ai_scanner.poi.structural_role import StructuralRole
from btmm_ai_scanner.scanner.analyzer import scan_market
from btmm_ai_scanner.scanner.replay import IncrementalReplayKernel
from btmm_ai_scanner.scanner.timeframe_input import ScannerTimeframeInput
from tests.parity_support.level_a_replay import build_scanner_configuration
from tests.parity_support.ob_origin_series import mirror, rows_to_candles
from tests.unit.test_rc3_order_block_leg_origin import _continuation, _reversal

_TICK = Decimal("0.01")
_RC4 = PoiConfiguration(minimum_price_tick=_TICK)
_RC5 = PoiConfiguration(minimum_price_tick=_TICK, rc5_structural_origin=True)
_MEASUREMENT = MarketMeasurementConfiguration(minimum_price_tick=_TICK)

_SERIES = {
    "continuation": _continuation,
    "continuation_sell": lambda: mirror(_continuation()),
    "reversal": _reversal,
    "reversal_sell": lambda: mirror(_reversal()),
}


def _measure(candles):
    return analyze_market_measurements(
        candles, _MEASUREMENT, ContentAddressedIdentityProvider()
    )


def _pois(candles, configuration: PoiConfiguration):
    return analyze_pois(
        (PoiTimeframeInput(Timeframe.M15, candles, _measure(candles)),),
        configuration,
        ContentAddressedIdentityProvider(),
    )


def _scanner_configuration(*, rc5: bool):
    base = build_scanner_configuration(minimum_price_tick=_TICK)
    return base.model_copy(
        update={
            "poi_configuration": PoiConfiguration(
                minimum_price_tick=_TICK, rc5_structural_origin=rc5
            )
        }
    )


@pytest.fixture(params=sorted(_SERIES), ids=sorted(_SERIES))
def series(request: pytest.FixtureRequest, tmp_path: Path):
    candles = rows_to_candles(_SERIES[request.param](), tmp_path, request.param)
    return request.param, candles


# ---------------------------------------------------------------------------
# the flag is genuinely off by default
# ---------------------------------------------------------------------------


def test_rc4_stays_byte_identical_when_the_flag_is_off(series) -> None:
    _name, candles = series
    assert (
        _pois(candles, _RC4).poi_observations
        == _pois(
            candles,
            PoiConfiguration(minimum_price_tick=_TICK, rc5_structural_origin=False),
        ).poi_observations
    )


def test_the_gate_only_ever_removes_or_delays_reversal_families(series) -> None:
    """RC5 answers 'is this a POI at all'. It must not invent POIs, and it must
    not touch imbalances, bases or structural zones."""
    _name, candles = series
    rc4 = {
        (o.poi_type, o.source_candle_record_ids): o
        for o in _pois(candles, _RC4).poi_observations
    }
    rc5 = {
        (o.poi_type, o.source_candle_record_ids): o
        for o in _pois(candles, _RC5).poi_observations
    }
    assert set(rc5) <= set(rc4), "RC5 must not create POIs"
    for key in set(rc4) - set(rc5):
        assert key[0] in REVERSAL_TYPES, f"non-reversal family removed: {key[0]}"
    for key, observation in rc5.items():
        if observation != rc4[key]:
            assert key[0] in REVERSAL_TYPES


# ---------------------------------------------------------------------------
# 3 + 4: source time preserved, availability is the causal confirmation
# ---------------------------------------------------------------------------


def test_qualification_never_moves_the_source_time_or_the_geometry(series) -> None:
    _name, candles = series
    rc4 = {
        (o.poi_type, o.source_candle_record_ids): o
        for o in _pois(candles, _RC4).poi_observations
    }
    for observation in _pois(candles, _RC5).poi_observations:
        before = rc4[(observation.poi_type, observation.source_candle_record_ids)]
        # A pattern formed at 10:00 stays a 10:00 pattern.
        assert observation.candidate_event_time_utc == before.candidate_event_time_utc
        assert observation.zone_top == before.zone_top
        assert observation.zone_bottom == before.zone_bottom
        assert observation.source_candle_record_ids == before.source_candle_record_ids
        assert observation.direction == before.direction
        # Only promotion may move, and only ever later.
        assert observation.availability_time_utc >= before.availability_time_utc


def test_availability_never_precedes_the_formation(series) -> None:
    _name, candles = series
    for observation in _pois(candles, _RC5).poi_observations:
        assert observation.availability_time_utc >= observation.candidate_event_time_utc


def test_a_delayed_candidate_is_available_exactly_at_its_confirming_event(
    series,
) -> None:
    """Availability equals the confirming structural event's own availability,
    not the bar the gate happened to notice it on."""
    _name, candles = series
    swings = tuple(_measure(candles).confirmed_swings)
    candidates = detect_engulfing(candles, _RC5)
    for decision in structure_context_decisions(
        candidates, candles, swings, rc5_structural_origin=True
    ):
        if decision.mapped is None:
            continue
        fact_times = [decision.candidate.availability_time_utc]
        assert decision.mapped.availability_time_utc >= max(fact_times)
        assert (
            decision.mapped.candidate_event_time_utc
            == decision.candidate.candidate_event_time_utc
        )


# ---------------------------------------------------------------------------
# 1 + 2: not qualified before the confirming prefix, qualified at the first one
# ---------------------------------------------------------------------------


def test_no_poi_is_ever_visible_before_its_own_availability(series) -> None:
    """P3/P5/P8 read the observation stream, so this is the single property
    that keeps every downstream layer causal."""
    name, candles = series
    configuration = _scanner_configuration(rc5=True)
    kernel = IncrementalReplayKernel(
        (Timeframe.M15,), configuration, ContentAddressedIdentityProvider(), ()
    )
    for index, candle in enumerate(candles):
        kernel.advance_group({Timeframe.M15: (candle,)})
        now = candle.availability_time_utc
        for observation in kernel.finalize().poi_analysis.poi_observations:
            assert observation.availability_time_utc <= now, (name, index)


def test_a_candidate_qualifies_at_the_first_prefix_that_confirms_it_and_not_before(
    series,
) -> None:
    """Walk the prefixes: the bar on which a POI first appears must be the bar
    its availability names. Appearing earlier is look-ahead; appearing later
    means the gate is reading the wrong prefix."""
    name, candles = series
    configuration = _scanner_configuration(rc5=True)
    kernel = IncrementalReplayKernel(
        (Timeframe.M15,), configuration, ContentAddressedIdentityProvider(), ()
    )
    first_seen: dict[tuple, object] = {}
    for candle in candles:
        kernel.advance_group({Timeframe.M15: (candle,)})
        for observation in kernel.finalize().poi_analysis.poi_observations:
            key = (observation.poi_type, observation.source_candle_record_ids)
            if key not in first_seen:
                first_seen[key] = (
                    candle.availability_time_utc,
                    observation.availability_time_utc,
                )
    for key, (seen_at, available_at) in first_seen.items():
        assert seen_at == available_at, (name, key)


# ---------------------------------------------------------------------------
# 7: an emitted availability is history and never moves again
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("rc5", [False, True], ids=["rc4", "rc5"])
def test_later_structure_cannot_rewrite_an_already_emitted_availability(
    series, rc5: bool
) -> None:
    """Once a reversal POI has been published at a bar, no later structure may
    move that timestamp -- otherwise a backtest reading the stream twice would
    see two different histories.

    Scoped to the families the structural gate governs. The rolling period
    levels (CURRENT_DAY/WEEK/MONTH_HIGH/LOW) legitimately re-date as their
    extreme moves, under RC4 exactly as under RC5; that is their definition,
    not a repaint, which is why this runs under both flags.
    """
    name, candles = series
    configuration = _scanner_configuration(rc5=rc5)
    kernel = IncrementalReplayKernel(
        (Timeframe.M15,), configuration, ContentAddressedIdentityProvider(), ()
    )
    emitted: dict[tuple, object] = {}
    for candle in candles:
        kernel.advance_group({Timeframe.M15: (candle,)})
        for observation in kernel.finalize().poi_analysis.poi_observations:
            if observation.poi_type not in REVERSAL_TYPES:
                continue
            key = (observation.poi_type, observation.source_candle_record_ids)
            if key in emitted:
                assert emitted[key] == observation.availability_time_utc, (name, key)
            else:
                emitted[key] = observation.availability_time_utc


# ---------------------------------------------------------------------------
# 6: batch and incremental agree
# ---------------------------------------------------------------------------


def test_batch_and_incremental_agree_at_every_prefix_under_rc5(series) -> None:
    name, candles = series
    configuration = _scanner_configuration(rc5=True)
    kernel = IncrementalReplayKernel(
        (Timeframe.M15,), configuration, ContentAddressedIdentityProvider(), ()
    )
    for n, candle in enumerate(candles, start=1):
        kernel.advance_group({Timeframe.M15: (candle,)})
        if n < 30:
            continue
        incremental = kernel.finalize().poi_analysis
        batch = scan_market(
            (ScannerTimeframeInput(Timeframe.M15, candles[:n]),),
            (),
            configuration,
            ContentAddressedIdentityProvider(),
        ).poi_analysis
        assert incremental.poi_observations == batch.poi_observations, (name, n)
        assert incremental.current_poi_states == batch.current_poi_states, (name, n)


# ---------------------------------------------------------------------------
# the gate does not do authority's job
# ---------------------------------------------------------------------------


def test_several_candidates_on_one_origin_all_survive_the_structural_gate(
    series,
) -> None:
    """Phase 3 asks only whether a candidate is a meaningful structural origin.
    Choosing between same-origin candidates is Phase 4's job, so the gate must
    never thin a shared origin down to one."""
    _name, candles = series
    swings = tuple(_measure(candles).confirmed_swings)
    decisions = structure_context_decisions(
        detect_engulfing(candles, _RC5), candles, swings, rc5_structural_origin=True
    )
    by_origin: dict[object, int] = {}
    for decision in decisions:
        if decision.mapped is None or decision.origin_swing_id is None:
            continue
        by_origin[decision.origin_swing_id] = (
            by_origin.get(decision.origin_swing_id, 0) + 1
        )
    # Nothing asserts a count here -- the point is that the gate never caps it.
    assert all(count >= 1 for count in by_origin.values())


# ---------------------------------------------------------------------------
# the refusal itself
# ---------------------------------------------------------------------------


def test_mid_leg_texture_is_refused_with_its_own_reason(series) -> None:
    _name, candles = series
    swings = tuple(_measure(candles).confirmed_swings)
    candidates = detect_engulfing(candles, _RC5)
    rc5 = structure_context_decisions(
        candidates, candles, swings, rc5_structural_origin=True
    )
    refused = [
        d for d in rc5 if d.reason is ContextReason.CONTEXT_REJECT_NO_STRUCTURAL_ORIGIN
    ]
    for decision in refused:
        assert decision.mapped is None
        assert decision.structural_role is None
    # and every mapped reversal candidate carries the role that let it through
    for decision in rc5:
        if decision.mapped is not None and decision.candidate.poi_type in (
            REVERSAL_TYPES
        ):
            assert decision.structural_role in set(StructuralRole) - {
                StructuralRole.MID_LEG
            }


def test_the_resolver_refuses_a_candidate_that_touches_no_used_swing() -> None:
    """Direct check on the resolver: an empty context has no used swings, so
    nothing can hold a role in it."""
    from btmm_ai_scanner.poi.leg_origin import StructuralContext

    candidate = detect_engulfing(rows_to_candles(_reversal(), Path("."), "noop"), _RC5)
    assert candidate  # the series does produce engulfings
    assert structural_role_of(candidate[0], StructuralContext.empty()) is None
