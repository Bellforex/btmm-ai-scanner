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


def test_p5_never_evaluates_a_same_origin_subordinate(bars) -> None:
    """Authority runs BEFORE the opportunity loop, so a subordinate is never an
    independent opportunity on any bar."""
    checked = 0
    for bar in bars:
        by_id = {o.record_id: o for o in bar.analysis.poi_analysis.poi_observations}
        for poi_id in bar.evaluated_order:
            if by_id.get(poi_id) is None:
                continue
            assert poi_id not in bar.suppressed_poi_ids
            checked += 1
    assert checked, "replay evaluated nothing"


def test_p5_evaluates_only_valid_pois_or_the_bar_one_dies_on(bars) -> None:
    """The ACTUAL relationship, which the tidy nesting gets wrong.

    "P5 actionable => display eligible => valid" is false as stated, because a
    POI's terminal is REPORTED by evaluating it on the bar it became invalid.
    So an evaluated POI is either still valid, or is being evaluated exactly
    once on its own terminal bar. Pinning the real rule is the point: asserting
    the tidy version would fail, and weakening it to "evaluated => not
    suppressed" would stop constraining validity at all.
    """
    terminal_bar_by_id: dict = {}
    dying = 0
    for bar in bars:
        by_id = {o.record_id: o for o in bar.analysis.poi_analysis.poi_observations}
        for poi_id in bar.evaluated_order:
            if by_id.get(poi_id) is None:
                continue
            state = bar.state_by_id.get(poi_id)
            if rc5_poi_is_valid(state):
                continue
            # not valid: this must be the FIRST bar on which that is true
            assert poi_id not in terminal_bar_by_id, (
                f"{poi_id} evaluated again after its terminal bar "
                f"{terminal_bar_by_id.get(poi_id)}"
            )
            terminal_bar_by_id[poi_id] = bar.bar_index
            dying += 1
    assert dying, "no POI was evaluated on a terminal bar -- proof is vacuous"


def test_not_every_valid_poi_is_displayable(bars) -> None:
    """Authority and supersession legitimately hide valid formations, so the
    nesting must NOT be asserted in this direction."""
    hidden_but_not_invalid = 0
    for bar in bars:
        by_id = {o.record_id: o for o in bar.analysis.poi_analysis.poi_observations}
        for poi_id in bar.suppressed_poi_ids:
            if by_id.get(poi_id) is None:
                continue
            if rc5_validity(bar.state_by_id.get(poi_id)) is not Rc5Validity.INVALIDATED:
                hidden_but_not_invalid += 1
    assert hidden_but_not_invalid, (
        "series never hid a non-invalidated POI, so this asymmetry is untested"
    )


def test_display_and_p5_evaluation_coincide_but_actionability_does_not(
    bars,
) -> None:
    """Measured, not assumed. On this series EVERY visible POI is also
    EVALUATED by P5 -- membership of the loop does not separate the layers.
    What separates them is the DECISION: a visible, evaluated, perfectly valid
    zone is routinely not actionable, because permission is a supervisory
    verdict and not a property of the zone.

    So validity must not collapse into P5, and the reason is actionability,
    not loop membership. Both halves are asserted so a future change to either
    one is caught.
    """
    ledger = Rc5SemanticLedger()
    visible_but_unevaluated = 0
    visible_and_evaluated = 0
    visible_but_not_actionable = 0
    for bar in bars:
        evaluated = set(bar.evaluated_order)
        for observation in bar.analysis.poi_analysis.poi_observations:
            state = bar.state_by_id.get(observation.record_id)
            if not is_rc5_active_for_display(observation, state, ledger):
                continue
            if observation.record_id not in evaluated:
                visible_but_unevaluated += 1
                continue
            visible_and_evaluated += 1
            decision = bar.decision_by_id.get(observation.record_id)
            permission = getattr(decision, "analytical_permission", None)
            if getattr(permission, "value", permission) not in {
                "BUY_BIAS",
                "SELL_BIAS",
            }:
                visible_but_not_actionable += 1

    assert visible_and_evaluated, "series produced no visible evaluated POI"
    assert visible_but_unevaluated == 0, (
        "a visible POI escaped the P5 loop -- if this ever fires, the "
        "relationship between display and evaluation has changed and this "
        "test's premise must be re-derived, not relaxed"
    )
    assert visible_but_not_actionable, (
        "every visible POI was actionable, so validity and P5 actionability "
        "are indistinguishable here"
    )


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


# ---------------------------------------------------------------------------
# valid and terminal are mutually exclusive
# ---------------------------------------------------------------------------


def test_a_valid_poi_is_never_terminal(bars) -> None:
    """The invariant a real defect violated.

    P8 used to emit POI_TERMINAL on a bar where the lifecycle still said
    RECLAIM_FAILED -- a status rc5_validity reports as VALID, because the
    breach walk has NOT confirmed failure there and keeps watching. The POI was
    simultaneously valid and terminal.

    It was self-concealing too: the POI left the active set, so when GENUINE
    arrived a few bars later it was no longer evaluated and the correct
    terminal could never fire.

    This asserts the two can never disagree again, on every POI on every bar.
    """
    from tests.parity_support.p5_active_poi_loop_model import rc5_is_terminal

    checked = 0
    for bar in bars:
        for poi_id, state in bar.state_by_id.items():
            decision = bar.decision_by_id.get(poi_id)
            if decision is None:
                continue
            terminal = rc5_is_terminal(state, decision)
            assert terminal is not rc5_poi_is_valid(state), (
                f"{poi_id} valid={rc5_poi_is_valid(state)} terminal={terminal} "
                f"status={state.poi_lifecycle_status}"
            )
            checked += 1
    assert checked, "replay produced no decisions to check"


def test_reclaim_failed_is_valid_and_not_terminal() -> None:
    """The exact state the defect fired on, pinned directly.

    RECLAIM_FAILED means a breach window closed without a reclaim but did NOT
    meet the confirmation test (>=2 of 3 bars closing beyond the far edge, and
    the last bar beyond). The walk keeps watching; the zone may still survive.
    """
    from tests.parity_support.p5_active_poi_loop_model import rc5_is_terminal

    state = _State(
        terminal_reason=PoiTerminalReason.MITIGATED,
        status=PoiLifecycleStatus.RECLAIM_FAILED,
    )
    assert rc5_validity(state) is Rc5Validity.VALID
    for episode in ("ACTIVE", "FAILED", "ENDED", "NOT_TOUCHED", None):
        assert not rc5_is_terminal(state, _Decision(episode)), episode


def test_a_failed_interaction_episode_alone_does_not_kill_a_poi() -> None:
    """The removed branch, asserted absent. The RC4 framework's episode rule
    has no reclaim-confirmation test, so it must not be able to terminate a
    zone the frozen breach walk still considers alive."""
    from tests.parity_support.p5_active_poi_loop_model import rc5_is_terminal

    for status in (
        PoiLifecycleStatus.NO_BREACH,
        PoiLifecycleStatus.CLOSE_BREACH_CANDIDATE,
        PoiLifecycleStatus.RECLAIM_FAILED,
        PoiLifecycleStatus.RECLAIM_PENDING,
        PoiLifecycleStatus.FALSE_INVALIDATION_CONFIRMED,
    ):
        assert not rc5_is_terminal(_State(status=status), _Decision("FAILED")), status
    assert rc5_is_terminal(
        _State(status=PoiLifecycleStatus.GENUINE_INVALIDATION_CONFIRMED),
        _Decision("ACTIVE"),
    )


class _Decision:
    def __init__(self, episode) -> None:
        self.interaction_episode = episode
