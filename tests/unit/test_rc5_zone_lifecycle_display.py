"""A zone that the market destroyed must not read as a live opportunity.

The author's contract for the active chart is: show fresh zones, keep a
mitigated zone that is STILL HOLDING, and drop a zone once the market genuinely
broke it.

The trap these tests exist to lock is subtle and was measured on real data:

    `terminal_reason` CANNOT express "destroyed".

`resolve_terminal` resolves the earliest cause and its own docstring says "POI
that was touched and only later broke down stays MITIGATED". Since a zone is
almost always touched before it breaks, genuinely-invalidated zones record
MITIGATED. On the XAUUSD H4 capture that is 53 destroyed zones sitting inside
59 MITIGATED records, with ZERO records reading INVALIDATED.

So anything that gates display on `terminal_reason == INVALIDATED` shows every
failed zone as live. The field that actually separates them is
`poi_lifecycle_status`.
"""

from __future__ import annotations

import collections
from decimal import Decimal

import pytest

from btmm_ai_scanner.config.enums import InternalSymbol, Timeframe
from btmm_ai_scanner.historical_backtest.identity import (
    ContentAddressedIdentityProvider,
)
from btmm_ai_scanner.poi.configuration import PoiConfiguration
from btmm_ai_scanner.poi.enums import PoiTerminalReason
from btmm_ai_scanner.poi.rc5_semantics import Rc5SemanticLedger
from btmm_ai_scanner.scanner.analyzer import scan_market
from btmm_ai_scanner.scanner.timeframe_input import ScannerTimeframeInput
from tests.parity_support.level_a_replay import build_scanner_configuration
from tests.unit._arrival_fixtures import H4_XAU_CSV, load_capture

_TICK = Decimal("0.001")

pytestmark = pytest.mark.skipif(
    not H4_XAU_CSV.is_file(),
    reason=f"XAUUSD H4 capture not present at {H4_XAU_CSV}",
)


@pytest.fixture(scope="module")
def analysis():
    candles = load_capture(
        H4_XAU_CSV, Timeframe.H4, 240, InternalSymbol.XAUUSD, "0.001"
    )
    base = build_scanner_configuration(
        required_timeframes=frozenset({Timeframe.H4}),
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
    return scan_market(
        (ScannerTimeframeInput(Timeframe.H4, candles),),
        (),
        configuration,
        ContentAddressedIdentityProvider(),
        Rc5SemanticLedger(),
    ).poi_analysis


def _status(state) -> str:
    return getattr(state.poi_lifecycle_status, "name", str(state.poi_lifecycle_status))


def test_the_capture_really_does_contain_destroyed_zones(analysis) -> None:
    """Without this the rest of the file would pass vacuously."""
    statuses = collections.Counter(_status(s) for s in analysis.current_poi_states)
    assert statuses["GENUINE_INVALIDATION_CONFIRMED"] > 0
    # invalidation is the COMMON case here, which is what makes this capture
    # worth keeping: a majority of zones die.
    assert statuses["GENUINE_INVALIDATION_CONFIRMED"] > len(
        analysis.current_poi_states
    ) // 2


def test_TERMINAL_REASON_CANNOT_BE_USED_AS_A_DISPLAY_GATE(analysis) -> None:
    """THE trap. Destroyed zones do not record INVALIDATED.

    If this test ever fails because INVALIDATED appears, the resolution rule
    changed and the Pine display gate must be re-examined -- not "fixed" to
    match.
    """
    states = analysis.current_poi_states
    destroyed = [s for s in states if _status(s) == "GENUINE_INVALIDATION_CONFIRMED"]
    assert destroyed

    reasons = {getattr(s.terminal_reason, "name", None) for s in destroyed}
    assert "INVALIDATED" not in reasons, (
        "a destroyed zone now reports INVALIDATED; the earliest-cause rule "
        "changed and the display gate must be revisited"
    )
    assert reasons <= {"MITIGATED", None}


def test_the_lifecycle_status_is_the_field_that_separates_them(analysis) -> None:
    """Holding and destroyed must be distinguishable by SOMETHING."""
    states = analysis.current_poi_states
    interacted = [
        s for s in states if s.terminal_reason is PoiTerminalReason.MITIGATED
    ]
    assert interacted, "no mitigated records to separate"

    destroyed = {
        s.poi_record_id
        for s in interacted
        if _status(s) == "GENUINE_INVALIDATION_CONFIRMED"
    }
    holding = {s.poi_record_id for s in interacted} - destroyed
    assert destroyed, "expected destroyed zones inside the mitigated population"
    assert holding, "expected surviving zones inside the mitigated population"


def test_every_ledger_invalidation_reaches_the_state(analysis) -> None:
    """The transition ledger and the current state must not disagree."""
    invalidated = {
        t.poi_record_id
        for t in analysis.poi_lifecycle_transitions
        if t.transition_type.name == "GENUINE_INVALIDATION_CONFIRMED"
    }
    reported = {
        s.poi_record_id
        for s in analysis.current_poi_states
        if _status(s) == "GENUINE_INVALIDATION_CONFIRMED"
    }
    assert invalidated == reported, (
        "a zone was invalidated in the ledger but its current state does not "
        "say so, which is exactly how a dead zone stays on the chart"
    )


def test_a_surviving_zone_is_not_marked_destroyed(analysis) -> None:
    """The converse: reclaims and untouched zones must stay alive."""
    for state in analysis.current_poi_states:
        if _status(state) in {"NO_BREACH", "NOT_APPLICABLE"}:
            assert state.terminal_reason is not PoiTerminalReason.INVALIDATED
