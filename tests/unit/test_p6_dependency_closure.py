"""The excluded P1 engines are leaves, so omitting them is safe.

P6 transports three of P1's five collections and two of P2's three, on the
strength of a read-audit: BTRC never references `support_resistance_zones`,
`trendlines` or `swing_relationships`. That audit answers "does anything read
them", which is necessary but not sufficient. The dangerous case it cannot see
is an excluded engine being an UPSTREAM dependency of a required one -- omitting
it would then silently change a required output rather than merely dropping an
unused one.

This module closes that gap from the detector signatures. The dependency graph
is:

    candles                     -> confirmed_swings
    candles                     -> displacement_observations
    confirmed_swings            -> equal_level_clusters
    candles + confirmed_swings  -> support_resistance_zones   (leaf)
    candles + confirmed_swings  -> trendlines                 (leaf)
    candles + confirmed_swings  -> structure analysis (P2)

Both excluded engines CONSUME swings and are consumed by nothing. They are
leaves, so a six-timeframe substrate that never builds them produces byte-
identical values for everything BTRC actually reads -- and it skips the S/R
tracker and fold-cache machinery that dominated P3's difficulty.
"""

from __future__ import annotations

import inspect

from btmm_ai_scanner.domain import (
    displacement,
    equal_levels,
    support_resistance,
    swings,
    trendlines,
)
from btmm_ai_scanner.structure import analyzer as structure_analyzer


def _params(fn) -> list[str]:
    return list(inspect.signature(fn).parameters)


def test_swings_need_only_candles() -> None:
    assert _params(swings.detect_confirmed_swings) == ["candles", "configuration"]


def test_displacement_needs_only_candles() -> None:
    assert _params(displacement.detect_displacement_observations) == [
        "candles",
        "configuration",
    ]


def test_equal_levels_need_only_swings() -> None:
    """Notably NOT candles, and certainly not zones."""
    assert _params(equal_levels.detect_equal_level_clusters) == [
        "confirmed_swings",
        "configuration",
    ]


def test_structure_needs_only_candles_and_swings() -> None:
    assert _params(structure_analyzer.analyze_structure_state) == [
        "candles",
        "confirmed_swings",
        "configuration",
        "identity_provider",
    ]


def test_the_excluded_engines_are_leaves() -> None:
    """The load-bearing assertion. Both take swings as INPUT, so neither can be
    upstream of anything required; and nothing required takes a zone or a
    trendline."""
    for fn in (
        support_resistance.detect_support_resistance_zones,
        trendlines.detect_trendlines,
    ):
        params = _params(fn)
        assert "confirmed_swings" in params, params
        assert "candles" in params, params

    required = (
        swings.detect_confirmed_swings,
        displacement.detect_displacement_observations,
        equal_levels.detect_equal_level_clusters,
        structure_analyzer.analyze_structure_state,
    )
    for fn in required:
        params = _params(fn)
        for forbidden in (
            "support_resistance_zones",
            "zones",
            "trendlines",
            "swing_relationships",
        ):
            assert forbidden not in params, (fn.__name__, params)


def test_no_required_detector_imports_an_excluded_engine() -> None:
    """A module-level import would be the other way an excluded engine could
    sneak into a required computation."""
    for module in (swings, displacement, equal_levels, structure_analyzer):
        source = inspect.getsource(module)
        for forbidden in ("support_resistance", "trendlines"):
            offending = [
                line
                for line in source.splitlines()
                if forbidden in line and ("import" in line)
            ]
            assert offending == [], (module.__name__, offending)


def test_the_excluded_engines_are_the_expensive_ones() -> None:
    """Why this matters beyond tidiness: the two leaves carry substantially more
    machinery than the three required detectors, and S/R is the family that
    produced P3's hardest divergences."""
    required_len = sum(
        len(inspect.getsource(fn).splitlines())
        for fn in (
            swings.detect_confirmed_swings,
            displacement.detect_displacement_observations,
            equal_levels.detect_equal_level_clusters,
        )
    )
    excluded_len = len(inspect.getsource(support_resistance).splitlines()) + len(
        inspect.getsource(trendlines).splitlines()
    )
    assert excluded_len > required_len, (excluded_len, required_len)
