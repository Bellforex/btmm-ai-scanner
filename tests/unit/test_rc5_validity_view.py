"""RC5 validity: the zone itself, kept separate from who may trade it.

Three layers, each a subset of the one before:

    VALIDITY  >=  DISPLAY ELIGIBILITY  >=  P5 ACTIONABILITY

Keeping them apart is the author's requirement to SEPARATE OPPORTUNITY
EVALUATION FROM TERMINAL MONITORING. Terminal monitoring watches VALIDITY, so
it keeps watching a POI that authority has suppressed or that P5 is not
currently allowed to act on -- which is precisely how a zone can die correctly
while nobody was permitted to trade it.

The nesting is asserted on real replayed state, not on hand-built objects, so
it cannot be satisfied by a convenient fixture.
"""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pytest

from btmm_ai_scanner.config.enums import Timeframe
from btmm_ai_scanner.poi.configuration import PoiConfiguration
from btmm_ai_scanner.poi.enums import (
    LIFECYCLE_ELIGIBLE_POI_TYPES,
    PoiLifecycleStatus,
    PoiTerminalReason,
)
from btmm_ai_scanner.poi.rc5_semantics import (
    DisplayHiddenReason,
    Rc5SemanticLedger,
    Rc5Validity,
    display_hidden_reason,
    is_rc5_active_for_display,
    rc5_poi_is_valid,
    rc5_validity,
    stable_poi_key,
)
from tests.parity_support.level_a_replay import (
    build_scanner_configuration,
    iter_level_a_bars,
)
from tests.parity_support.ob_origin_series import mirror, rows_to_candles, trend
from tests.unit.test_rc3_order_block_leg_origin import _continuation

_TICK = Decimal("0.01")


class _State:
    def __init__(self, *, terminal_reason=None, status=PoiLifecycleStatus.NO_BREACH):
        self.terminal_reason = terminal_reason
        self.poi_lifecycle_status = status


# ---------------------------------------------------------------------------
# validity reads the lifecycle and nothing else
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("state", "expected"),
    [
        (None, Rc5Validity.VALID),
        (_State(), Rc5Validity.VALID),
        (_State(status=PoiLifecycleStatus.CLOSE_BREACH_CANDIDATE), Rc5Validity.VALID),
        (_State(status=PoiLifecycleStatus.RECLAIM_PENDING), Rc5Validity.VALID),
        (_State(terminal_reason=PoiTerminalReason.MITIGATED), Rc5Validity.VALID),
        (
            _State(
                terminal_reason=PoiTerminalReason.MITIGATED,
                status=PoiLifecycleStatus.FALSE_INVALIDATION_CONFIRMED,
            ),
            Rc5Validity.VALID,
        ),
        (
            _State(status=PoiLifecycleStatus.GENUINE_INVALIDATION_CONFIRMED),
            Rc5Validity.INVALIDATED,
        ),
        (
            _State(terminal_reason=PoiTerminalReason.INVALIDATED),
            Rc5Validity.INVALIDATED,
        ),
        (
            _State(terminal_reason=PoiTerminalReason.PROMOTED_TO_ORDER_BLOCK),
            Rc5Validity.SUPERSEDED,
        ),
    ],
    ids=[
        "unknown",
        "fresh",
        "breach-candidate",
        "reclaim-pending",
        "mitigated",
        "false-break-reclaimed",
        "genuine-invalidation",
        "invalidated",
        "promoted-to-order-block",
    ],
)
def test_validity_is_decided_by_the_frozen_lifecycle(state, expected) -> None:
    assert rc5_validity(state) is expected
    assert rc5_poi_is_valid(state) is (expected is Rc5Validity.VALID)


def test_validity_takes_no_ledger_so_it_cannot_depend_on_authority() -> None:
    """A suppressed subordinate is still a real zone. If validity consulted
    authority, terminal monitoring would stop watching it and the zone could
    fail unobserved."""
    import inspect

    parameters = inspect.signature(rc5_validity).parameters
    assert list(parameters) == ["state"]


# ---------------------------------------------------------------------------
# the nesting, on replayed state
# ---------------------------------------------------------------------------


def _replay(tmp_path: Path):
    rows = _continuation() + trend(139.8, -1.2, 40)
    candles = rows_to_candles(rows, tmp_path, "collapse")
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
    return list(
        iter_level_a_bars(
            host_timeframe=Timeframe.M15,
            host_series=candles,
            context_series={},
            configuration=configuration,
            rc3_freshness=True,
            rc4_framework=True,
            rc5_authority=True,
        )
    )


@pytest.fixture(scope="module")
def bars(tmp_path_factory):
    return _replay(tmp_path_factory.mktemp("validity"))


def test_display_is_a_subset_of_validity_on_every_bar(bars) -> None:
    ledger = Rc5SemanticLedger()
    checked = 0
    for bar in bars:
        for observation in bar.analysis.poi_analysis.poi_observations:
            state = bar.state_by_id.get(observation.record_id)
            if is_rc5_active_for_display(observation, state, ledger):
                assert rc5_poi_is_valid(state)
                checked += 1
    assert checked, "replay produced nothing to check"


def test_the_p5_evaluated_set_is_a_subset_of_display(bars) -> None:
    """P5 may only evaluate what a student can see."""
    checked = 0
    for bar in bars:
        by_id = {o.record_id: o for o in bar.analysis.poi_analysis.poi_observations}
        for poi_id in bar.evaluated_order:
            observation = by_id.get(poi_id)
            if observation is None:
                continue
            assert poi_id not in bar.suppressed_poi_ids
            checked += 1
    assert checked, "replay evaluated nothing"


def test_suppression_hides_a_poi_without_killing_it() -> None:
    """The distinction the whole layering exists for: authority answers "draw
    this?", validity answers "does this zone still stand?". A subordinate that
    price has merely mitigated is hidden AND alive, so terminal monitoring must
    keep watching it -- if suppression implied death, a suppressed zone could
    fail unobserved."""

    class _Observation:
        poi_type = "X"
        source_candle_record_ids = ()
        record_id = object()

    observation = _Observation()
    ledger = Rc5SemanticLedger()
    key = stable_poi_key(observation)
    ledger.get = lambda k: _Suppressed() if k == key else None  # type: ignore[method-assign]

    state = _State(terminal_reason=PoiTerminalReason.MITIGATED)
    assert rc5_poi_is_valid(state)
    assert (
        display_hidden_reason(observation, state, ledger)
        is DisplayHiddenReason.AUTHORITY_SUPPRESSED
    )
    assert not is_rc5_active_for_display(observation, state, ledger)


def test_in_the_collapse_series_suppression_and_supersession_agree(bars) -> None:
    """A finding worth pinning rather than assuming. Every POI the collapse
    series suppresses is a BULLISH_ENGULFING that the lifecycle independently
    marked PROMOTED_TO_ORDER_BLOCK -- it did not lose an arbitration, it BECAME
    the order block. The two mechanisms reaching the same verdict by different
    routes is a consistency check, so it is asserted, not glossed."""
    seen = 0
    for bar in bars:
        by_id = {o.record_id: o for o in bar.analysis.poi_analysis.poi_observations}
        for poi_id in bar.suppressed_poi_ids:
            observation = by_id.get(poi_id)
            if observation is None:
                continue
            state = bar.state_by_id.get(poi_id)
            assert rc5_validity(state) in {
                Rc5Validity.SUPERSEDED,
                Rc5Validity.INVALIDATED,
            }
            assert not is_rc5_active_for_display(observation, state, _ledger(bar))
            seen += 1
    assert seen, "series produced no suppression"


def _ledger(bar) -> Rc5SemanticLedger:
    """A ledger that reports exactly this bar's suppression decision, so the
    display predicate is asked the same question the replay answered."""
    ledger = Rc5SemanticLedger()
    suppressed = {
        stable_poi_key(o)
        for o in bar.analysis.poi_analysis.poi_observations
        if o.record_id in bar.suppressed_poi_ids
    }
    ledger.suppressed_keys = lambda: suppressed  # type: ignore[method-assign]
    ledger.get = lambda key: _Suppressed() if key in suppressed else None  # type: ignore[method-assign]
    return ledger


class _Suppressed:
    is_suppressed = True


# ---------------------------------------------------------------------------
# display still answers WHY, and still agrees with validity
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("rows_name", ["collapse", "collapse_mirror"])
def test_every_hidden_reason_matches_the_validity_beneath_it(
    rows_name: str, tmp_path: Path
) -> None:
    rows = _continuation() + trend(139.8, -1.2, 40)
    if rows_name == "collapse_mirror":
        rows = mirror(rows)
    candles = rows_to_candles(rows, tmp_path, rows_name)
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
    checked = 0
    for bar in iter_level_a_bars(
        host_timeframe=Timeframe.M15,
        host_series=candles,
        context_series={},
        configuration=configuration,
        rc3_freshness=True,
        rc4_framework=True,
        rc5_authority=True,
    ):
        for observation in bar.analysis.poi_analysis.poi_observations:
            if observation.poi_type not in LIFECYCLE_ELIGIBLE_POI_TYPES:
                continue
            state = bar.state_by_id.get(observation.record_id)
            reason = display_hidden_reason(observation, state, ledger)
            validity = rc5_validity(state)
            if reason is DisplayHiddenReason.INVALIDATED:
                assert validity is Rc5Validity.INVALIDATED
            elif reason is DisplayHiddenReason.SUPERSEDED:
                assert validity is Rc5Validity.SUPERSEDED
            elif reason is None:
                assert validity is Rc5Validity.VALID
            checked += 1
    assert checked, "replay produced no lifecycle-eligible POIs"
