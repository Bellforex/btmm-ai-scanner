"""P8's terminal events, proven against an independent expectation.

The oracle reads ONLY lifecycle state -- the first prefix on which a POI turns
``GENUINE_INVALIDATION_CONFIRMED`` -- and never reads a P8 event to build its
expectation. P8 derives its stream through the eligibility algebra and the
alert engine. Agreement between the two is the claim under test, and the
independence is the whole point: ``rc5_is_terminal`` can fire for a FAILED
interaction episode as well as for a lifecycle invalidation, so if those two
failure detectors ever disagree it surfaces here as an EXTRA rather than being
quietly absorbed.

NON-VACUITY MATTERS MORE THAN CLEANLINESS. A series that never mitigates,
re-mitigates, suppresses or invalidates anything passes every assertion below
while proving nothing, so ``episodes_then_collapse`` is built to exercise each
situation and a test asserts that it did.

``collapse`` also carries the case that caught a defect in the oracle itself:
a BULLISH_ENGULFING sharing an origin with a BUY_ORDER_BLOCK, suppressed before
the opportunity loop. Rebuilding authority from a fresh ledger (which has no
provenance) made it look like a POI owed an event, so the suppressed set must
come from the replay.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from btmm_ai_scanner.config.enums import Timeframe
from tests.parity_support.ob_origin_series import mirror, rows_to_candles, trend
from tests.parity_support.rc5_terminal_oracle import UnobservableReason
from tests.parity_support.rc5_terminal_probe import REQUIRED_COVERAGE, probe_terminals
from tests.unit.test_rc3_order_block_leg_origin import _continuation, _reversal

#: Repeated interactions with the zone built at the end of ``_continuation``:
#: a deep dip that reacts, a deeper dip that reacts again, then a wick through
#: that closes back inside. Only after all of that does price break down.
_EPISODES = [
    (139.8, 140.1, 131.0, 131.6),
    (131.6, 137.0, 131.4, 136.5),
    (136.5, 137.0, 130.2, 130.8),
    (130.8, 136.0, 130.6, 135.6),
    (135.6, 136.0, 127.0, 130.4),
    (130.4, 135.0, 130.2, 134.6),
]


def _collapse() -> list:
    """A real continuation structure, then a sustained decline that breaks
    every bullish zone it built."""
    return _continuation() + trend(139.8, -1.2, 40)


def _episodes_then_collapse() -> list:
    return _continuation() + _EPISODES + trend(134.6, -1.2, 40)


def _recovery() -> list:
    return _reversal() + trend(189.3, 1.2, 40)


_SERIES = {
    "continuation": _continuation,
    "reversal": _reversal,
    "collapse": _collapse,
    "collapse_mirror": lambda: mirror(_collapse()),
    "episodes_then_collapse": _episodes_then_collapse,
    "recovery": _recovery,
}

#: series that must actually invalidate something, or the suite is vacuous
_MUST_INVALIDATE = ("collapse", "collapse_mirror", "episodes_then_collapse")


def _probe(name: str, tmp_path: Path):
    candles = rows_to_candles(_SERIES[name](), tmp_path, name)
    return probe_terminals(Timeframe.M15, candles)


# ---------------------------------------------------------------------------
# agreement
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("name", sorted(_SERIES))
def test_p8_terminals_agree_with_the_lifecycle_oracle(
    name: str, tmp_path: Path
) -> None:
    comparison = _probe(name, tmp_path).comparison
    assert not comparison.missing, [
        (m.poi_type, m.terminal_bar, m.ever_evaluated) for m in comparison.missing
    ]
    assert not comparison.extra_poi_idx
    assert not comparison.duplicated_poi_idx
    assert comparison.is_clean


# ---------------------------------------------------------------------------
# exactness -- the same bar, not merely the same POI
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("name", _MUST_INVALIDATE)
def test_each_terminal_fires_on_the_transition_bar(name: str, tmp_path: Path) -> None:
    comparison = _probe(name, tmp_path).comparison
    assert not comparison.time_mismatches, comparison.time_mismatches
    assert comparison.matched == comparison.observable


@pytest.mark.parametrize("name", _MUST_INVALIDATE)
def test_a_terminal_is_only_ever_an_invalidation(name: str, tmp_path: Path) -> None:
    """No terminal on first touch, ordinary mitigation, reaction, a reclaimed
    false break, or authority suppression."""
    comparison = _probe(name, tmp_path).comparison
    assert not comparison.non_invalidation_reasons, comparison.non_invalidation_reasons


# ---------------------------------------------------------------------------
# post-terminal silence, read from the ACTUAL event stream
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("name", sorted(_SERIES))
def test_nothing_is_emitted_after_a_terminal(name: str, tmp_path: Path) -> None:
    """Checked against the events P8 really produced, not inferred from
    lifecycle state: no POI_ACTIVATED, BTMM_VALIDATED, PERMISSION_*, or a
    second POI_TERMINAL may follow a POI's terminal event."""
    comparison = _probe(name, tmp_path).comparison
    assert not comparison.post_terminal_violations, comparison.post_terminal_violations
    assert not comparison.duplicated_poi_idx


# ---------------------------------------------------------------------------
# non-vacuity
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("name", _MUST_INVALIDATE)
def test_the_proof_is_not_vacuous(name: str, tmp_path: Path) -> None:
    probe = _probe(name, tmp_path)
    assert probe.comparison.expected_total > 0
    assert probe.comparison.observable > 0
    assert probe.comparison.matched == probe.comparison.observable
    assert probe.emitted_terminals > 0


def test_one_series_exercises_every_required_situation(tmp_path: Path) -> None:
    """The guard against this suite decaying into a green tautology. A future
    change that stops POIs being mitigated, re-mitigated or suppressed would
    otherwise leave every assertion above passing on an empty set."""
    probe = _probe("episodes_then_collapse", tmp_path)
    assert probe.missing_coverage == frozenset(), probe.missing_coverage
    assert REQUIRED_COVERAGE <= probe.exercised
    assert probe.mitigated_and_alive > 0
    assert probe.re_mitigated > 0
    assert probe.genuinely_invalidated > 0
    assert probe.authority_suppressed > 0


def test_a_reclaimed_false_break_is_exercised_somewhere() -> None:
    """``false_break_reclaim`` is the one situation the synthetic series do not
    reliably produce (the author's "where practical"). It is proven instead by
    the lifecycle suite, against the real breach walk, and on the real M45
    capture -- so this records WHERE rather than pretending it is covered here.
    """
    from tests.unit import test_rc5_multi_interaction_lifecycle as lifecycle

    assert hasattr(
        lifecycle, "test_a_reclaimed_close_through_is_recorded_as_a_false_invalidation"
    )


# ---------------------------------------------------------------------------
# the classified exceptions
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("name", sorted(_SERIES))
def test_every_unmatched_expectation_is_classified(name: str, tmp_path: Path) -> None:
    """No expectation may be quietly dropped: expected == observable plus the
    classified exceptions, and each exception names a reason."""
    comparison = _probe(name, tmp_path).comparison
    assert comparison.observable + sum(comparison.unobservable.values()) == (
        comparison.expected_total
    )
    known = {reason.value for reason in UnobservableReason}
    assert set(comparison.unobservable) <= known


def test_a_same_origin_subordinate_is_not_owed_a_terminal_event(
    tmp_path: Path,
) -> None:
    """The defect this file was written around. The collapse series contains a
    BULLISH_ENGULFING sharing an origin with a BUY_ORDER_BLOCK; authority
    suppresses it before the opportunity loop, so P8 never sees it and owes it
    no event -- and the oracle must say so BY NAME rather than by silence."""
    comparison = _probe("collapse", tmp_path).comparison
    assert comparison.unobservable.get(UnobservableReason.AUTHORITY_SUPPRESSED) == 1
    assert comparison.is_clean
