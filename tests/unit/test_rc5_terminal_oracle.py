"""P8's terminal events, proven against an independent expectation.

The oracle reads ONLY lifecycle state -- the first prefix on which a POI turns
``GENUINE_INVALIDATION_CONFIRMED`` -- and never looks at an event. P8 derives
its stream through the eligibility algebra and the alert engine. Agreement
between the two is the claim under test.

NON-VACUITY MATTERS MORE THAN CLEANLINESS HERE. A series that produces no
invalidations at all would pass every assertion below while proving nothing, so
``collapse`` and its mirror are constructed to drive price decisively through
the far side of real POIs, and the test asserts that they actually did.

The ``collapse`` series also carries the case that caught a defect in the
oracle itself: a BULLISH_ENGULFING that shares an origin with a BUY_ORDER_BLOCK
and is therefore suppressed before the opportunity loop. Rebuilding authority
from a fresh ledger (which has no provenance) made it look like a POI owed an
event, so the suppressed set must come from the replay.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from btmm_ai_scanner.config.enums import Timeframe
from tests.parity_support.ob_origin_series import mirror, rows_to_candles, trend
from tests.parity_support.rc5_terminal_oracle import UnobservableReason
from tests.parity_support.rc5_terminal_probe import probe_terminals
from tests.unit.test_rc3_order_block_leg_origin import _continuation, _reversal


def _collapse() -> list:
    """A real continuation structure, then a sustained decline that breaks
    every bullish zone it built."""
    return _continuation() + trend(139.8, -1.2, 40)


def _recovery() -> list:
    return _reversal() + trend(189.3, 1.2, 40)


_SERIES = {
    "continuation": _continuation,
    "reversal": _reversal,
    "collapse": _collapse,
    "collapse_mirror": lambda: mirror(_collapse()),
    "recovery": _recovery,
}

#: series that must actually invalidate something, or the suite is vacuous
_MUST_INVALIDATE = ("collapse", "collapse_mirror")


def _probe(name: str, tmp_path: Path):
    candles = rows_to_candles(_SERIES[name](), tmp_path, name)
    return probe_terminals(Timeframe.M15, candles)


@pytest.mark.parametrize("name", sorted(_SERIES))
def test_p8_terminals_agree_with_the_lifecycle_oracle(
    name: str, tmp_path: Path
) -> None:
    comparison = _probe(name, tmp_path)
    assert not comparison.missing, [
        (m.poi_type, m.terminal_bar, m.ever_evaluated) for m in comparison.missing
    ]
    assert not comparison.extra_poi_idx
    assert not comparison.duplicated_poi_idx
    assert not comparison.post_terminal_violations
    assert comparison.is_clean


@pytest.mark.parametrize("name", _MUST_INVALIDATE)
def test_the_proof_is_not_vacuous(name: str, tmp_path: Path) -> None:
    """Without this the suite above would pass on a series where nothing ever
    dies, which is exactly the failure mode a terminal proof must not have."""
    comparison = _probe(name, tmp_path)
    assert comparison.expected_total > 0
    assert comparison.observable > 0
    assert comparison.matched == comparison.observable


@pytest.mark.parametrize("name", sorted(_SERIES))
def test_every_unmatched_expectation_is_classified(name: str, tmp_path: Path) -> None:
    """No expectation may be quietly dropped: expected == observable plus the
    classified exceptions, and each exception names a reason."""
    comparison = _probe(name, tmp_path)
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
    comparison = _probe("collapse", tmp_path)
    assert comparison.unobservable.get(UnobservableReason.AUTHORITY_SUPPRESSED) == 1
    assert comparison.is_clean
