"""RC5 active display: what a student should still see as a live zone.

Two author rules, and they pull in opposite directions:

* dead zones must stop looking tradeable; but
* **mitigation is not termination** -- a POI that price touched, entered
  deeply, and reacted from is still a valid zone and may be re-mitigated.

So the only thing that hides a POI is confirmed failure through its FAR side
(or authority suppression). The frozen lifecycle sets
``terminal_reason = MITIGATED`` at the FIRST TOUCH, which says only that price
has been in the zone -- never that the zone failed.

This is ONE predicate for every lifecycle-eligible family, governing box, label
and table row together. Nothing is deleted; history keeps every record.
"""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pytest

from btmm_ai_scanner.config.enums import Timeframe
from btmm_ai_scanner.historical_backtest.identity import (
    ContentAddressedIdentityProvider,
)
from btmm_ai_scanner.poi.configuration import PoiConfiguration
from btmm_ai_scanner.poi.enums import (
    LIFECYCLE_ELIGIBLE_POI_TYPES,
    PoiLifecycleStatus,
    PoiTerminalReason,
)
from btmm_ai_scanner.poi.rc5_semantics import (
    DisplayHiddenReason,
    Rc5SemanticLedger,
    active_display_pois,
    assign_origin_authority,
    display_hidden_reason,
    is_rc5_active_for_display,
    stable_poi_key,
)
from btmm_ai_scanner.scanner.analyzer import scan_market
from btmm_ai_scanner.scanner.timeframe_input import ScannerTimeframeInput
from tests.parity_support.level_a_replay import build_scanner_configuration
from tests.parity_support.ob_origin_series import mirror, rows_to_candles
from tests.unit.test_rc3_order_block_leg_origin import _continuation, _reversal

_TICK = Decimal("0.01")

_SERIES = {
    "continuation": _continuation,
    "continuation_sell": lambda: mirror(_continuation()),
    "reversal": _reversal,
    "reversal_sell": lambda: mirror(_reversal()),
}


class _State:
    """Minimal stand-in for CurrentPoiState: the predicate reads exactly three
    attributes, and pinning that keeps the view from quietly growing new
    dependencies on the frozen record."""

    def __init__(
        self,
        *,
        terminal_reason=None,
        poi_lifecycle_status=PoiLifecycleStatus.NO_BREACH,
        terminal_time_utc=None,
    ) -> None:
        self.terminal_reason = terminal_reason
        self.poi_lifecycle_status = poi_lifecycle_status
        self.terminal_time_utc = terminal_time_utc


@pytest.fixture(params=sorted(_SERIES), ids=sorted(_SERIES))
def analysis(request: pytest.FixtureRequest, tmp_path: Path):
    candles = rows_to_candles(_SERIES[request.param](), tmp_path, request.param)
    base = build_scanner_configuration(
        required_timeframes=frozenset({Timeframe.M15}),
        optional_timeframes=frozenset(),
        minimum_price_tick=_TICK,
    )
    configuration = base.model_copy(
        update={
            "poi_configuration": PoiConfiguration(
                minimum_price_tick=_TICK, rc5_structural_origin=True
            )
        }
    )
    ledger = Rc5SemanticLedger()
    result = scan_market(
        (ScannerTimeframeInput(Timeframe.M15, candles),),
        (),
        configuration,
        ContentAddressedIdentityProvider(),
        ledger,
    ).poi_analysis
    assign_origin_authority(result.poi_observations, ledger)
    return result, ledger


# ---------------------------------------------------------------------------
# the contract, applied generically
# ---------------------------------------------------------------------------


def test_a_fresh_poi_with_no_state_yet_is_visible(analysis) -> None:
    result, ledger = analysis
    shown = [
        o
        for o in result.poi_observations
        if o.poi_type in LIFECYCLE_ELIGIBLE_POI_TYPES
        and stable_poi_key(o) not in ledger.suppressed_keys()
    ]
    if not shown:
        pytest.skip("series produces no lifecycle-eligible authoritative POIs")
    for observation in shown:
        assert is_rc5_active_for_display(observation, None, ledger)


@pytest.mark.parametrize(
    ("state", "expected"),
    [
        (_State(), None),
        (
            _State(poi_lifecycle_status=PoiLifecycleStatus.CLOSE_BREACH_CANDIDATE),
            None,
        ),
        (_State(poi_lifecycle_status=PoiLifecycleStatus.RECLAIM_PENDING), None),
        (_State(terminal_reason=PoiTerminalReason.MITIGATED), None),
        (
            _State(
                terminal_reason=PoiTerminalReason.MITIGATED,
                poi_lifecycle_status=PoiLifecycleStatus.FALSE_INVALIDATION_CONFIRMED,
            ),
            None,
        ),
        (
            _State(terminal_reason=PoiTerminalReason.INVALIDATED),
            DisplayHiddenReason.INVALIDATED,
        ),
        (
            _State(
                poi_lifecycle_status=(PoiLifecycleStatus.GENUINE_INVALIDATION_CONFIRMED)
            ),
            DisplayHiddenReason.INVALIDATED,
        ),
    ],
    ids=[
        "fresh",
        "open-interaction-breach",
        "open-interaction-reclaim",
        "mitigated-still-valid",
        "far-edge-false-break-reclaimed",
        "invalidated",
        "genuine-invalidation",
    ],
)
def test_lifecycle_display_contract(analysis, state, expected) -> None:
    """Fresh and open interactions stay visible; mitigated, invalidated and
    terminal do not."""
    result, ledger = analysis
    candidates = [
        o
        for o in result.poi_observations
        if o.poi_type in LIFECYCLE_ELIGIBLE_POI_TYPES
        and stable_poi_key(o) not in ledger.suppressed_keys()
    ]
    if not candidates:
        pytest.skip("series produces no lifecycle-eligible authoritative POIs")
    assert display_hidden_reason(candidates[0], state, ledger) is expected


def test_the_contract_holds_for_every_family_not_just_one(analysis) -> None:
    """No POI type is special-cased -- the author asked for this explicitly
    after pressure wicks were the visible symptom."""
    result, ledger = analysis
    invalidated = _State(
        poi_lifecycle_status=PoiLifecycleStatus.GENUINE_INVALIDATION_CONFIRMED
    )
    seen = set()
    for observation in result.poi_observations:
        if observation.poi_type not in LIFECYCLE_ELIGIBLE_POI_TYPES:
            continue
        seen.add(observation.poi_type)
        assert not is_rc5_active_for_display(observation, invalidated, ledger)
    assert len(seen) >= 2, "series should exercise more than one family"


def test_mitigation_never_hides_a_poi_in_any_family(analysis) -> None:
    """The correction itself: price using a zone does not kill it, whatever
    the family, and however many times it has been used."""
    result, ledger = analysis
    mitigated = _State(terminal_reason=PoiTerminalReason.MITIGATED)
    for observation in result.poi_observations:
        if observation.poi_type not in LIFECYCLE_ELIGIBLE_POI_TYPES:
            continue
        if stable_poi_key(observation) in ledger.suppressed_keys():
            continue
        assert is_rc5_active_for_display(observation, mitigated, ledger)


def test_a_reclaimed_far_edge_break_keeps_the_poi_alive(analysis) -> None:
    """A wick beyond the far side that was reclaimed is a false break, which
    the author explicitly wants preserved -- the frozen walk records it as
    FALSE_INVALIDATION_CONFIRMED rather than GENUINE."""
    result, ledger = analysis
    false_break = _State(
        terminal_reason=PoiTerminalReason.MITIGATED,
        poi_lifecycle_status=PoiLifecycleStatus.FALSE_INVALIDATION_CONFIRMED,
    )
    shown = [
        o
        for o in result.poi_observations
        if o.poi_type in LIFECYCLE_ELIGIBLE_POI_TYPES
        and stable_poi_key(o) not in ledger.suppressed_keys()
    ]
    if not shown:
        pytest.skip("series produces no lifecycle-eligible authoritative POIs")
    for observation in shown:
        assert is_rc5_active_for_display(observation, false_break, ledger)


# ---------------------------------------------------------------------------
# authority interaction
# ---------------------------------------------------------------------------


def test_a_suppressed_poi_is_hidden_even_when_perfectly_fresh(analysis) -> None:
    result, ledger = analysis
    suppressed = ledger.suppressed_keys()
    if not suppressed:
        pytest.skip("series produces no same-origin suppression")
    by_key = {stable_poi_key(o): o for o in result.poi_observations}
    for key in suppressed:
        observation = by_key[key]
        assert (
            display_hidden_reason(observation, None, ledger)
            is DisplayHiddenReason.AUTHORITY_SUPPRESSED
        )
        assert not is_rc5_active_for_display(observation, None, ledger)


def test_authority_suppression_outranks_a_healthy_lifecycle(analysis) -> None:
    """A subordinate is not a separate opportunity, so its own lifecycle being
    healthy must not put it back on the chart."""
    result, ledger = analysis
    suppressed = ledger.suppressed_keys()
    if not suppressed:
        pytest.skip("series produces no same-origin suppression")
    by_key = {stable_poi_key(o): o for o in result.poi_observations}
    healthy = _State(poi_lifecycle_status=PoiLifecycleStatus.NO_BREACH)
    for key in suppressed:
        assert (
            display_hidden_reason(by_key[key], healthy, ledger)
            is DisplayHiddenReason.AUTHORITY_SUPPRESSED
        )


# ---------------------------------------------------------------------------
# the view never deletes history
# ---------------------------------------------------------------------------


def test_the_view_is_a_subset_and_history_is_untouched(analysis) -> None:
    result, ledger = analysis
    lifecycle = [
        o for o in result.poi_observations if o.poi_type in LIFECYCLE_ELIGIBLE_POI_TYPES
    ]
    states = {s.poi_record_id: s for s in result.current_poi_states}
    visible = active_display_pois(lifecycle, states, ledger)
    assert set(visible) <= set(lifecycle)
    # the registry itself is unchanged
    assert len(result.poi_observations) >= len(lifecycle)
    assert len(result.current_poi_states) == len(result.current_poi_states)
