"""The RC3 P8 terminal contract, checked against a real live Pine capture.

The fixture is a Pine Logs export from `BTMM + POI + BTRC Scanner
[RC3 PARITY DEV]` running on FX:XAUUSD H4, account bellcare1994, over the full
1800-bar window. That build's semantic code is byte-identical to the release
DEV apart from its title.

Scope, stated honestly: these are invariants of the emitted stream, not a
Python-to-Pine row comparison. The Pine registry spans 1800 H4 bars and the
Python replay fixture spans 299, so registry indices do not align and a
field-by-field differential is not possible from this capture. What the file
does prove is that the live build obeys the terminal contract RC3 froze.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.parity_support.rc3_p8_capture import (
    TERMINAL_REASONS,
    capture_invariants,
    parse_p8_capture,
)

_CAPTURE = (
    Path(__file__).resolve().parents[2]
    / "artifacts"
    / "rc3_parity"
    / "rc3_parity_logs_h4.csv"
)

pytestmark = pytest.mark.skipif(
    not _CAPTURE.exists(),
    reason="live Pine capture is gitignored under artifacts/; run the capture first",
)


@pytest.fixture(scope="module")
def events():
    return parse_p8_capture(_CAPTURE)


@pytest.fixture(scope="module")
def invariants(events):
    return capture_invariants(events)


def test_the_capture_carries_a_substantial_event_stream(invariants) -> None:
    assert invariants["events"] == 2200
    assert invariants["terminal_events"] == 945


def test_every_poi_goes_terminal_at_most_once(invariants) -> None:
    """The campaign's `no repeated terminal event` requirement, on real data."""
    assert invariants["duplicate_terminal_pois"] == {}
    assert invariants["distinct_terminal_pois"] == invariants["terminal_events"]


def test_every_terminal_event_states_its_cause(invariants) -> None:
    assert invariants["terminals_missing_a_reason"] == 0
    assert set(invariants["reason_distribution"]) <= TERMINAL_REASONS


def test_no_poi_goes_terminal_before_it_is_activated(invariants) -> None:
    assert invariants["terminal_before_activation"] == []


def test_activations_exceed_terminals_because_some_pois_are_still_fresh(
    invariants,
) -> None:
    assert invariants["activated_pois"] > invariants["terminal_events"]


def test_the_live_reason_distribution_matches_the_python_finding(invariants) -> None:
    """Mitigation dominates because a zone is almost always touched before it
    breaks down, which is exactly what the 299-bar Python replay reported."""
    dist = invariants["reason_distribution"]
    assert dist.get("MITIGATED", 0) == 945
    assert dist.get("INVALIDATED", 0) == 0


def test_the_event_vocabulary_is_the_frozen_one(invariants) -> None:
    assert set(invariants["by_type"]) == {
        "POI_ACTIVATED",
        "POI_TERMINAL",
        "PERMISSION_ENTERED_ACTIONABLE",
        "PERMISSION_LOST_ACTIONABLE",
    }


def test_no_event_other_than_a_terminal_carries_a_reason(events) -> None:
    for event in events:
        if event.event_type != "POI_TERMINAL":
            assert event.terminal_reason is None, event
