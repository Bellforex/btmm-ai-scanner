"""A run that claims to be production must actually use production defaults.

This exists because of a real mistake. A XAUUSD H4 reconciliation was run with
`rc5_structural_origin=True` while the production default is `False`, and the
non-default output was then read as ground truth. It produced a confident and
completely wrong conclusion -- that the live chart was drawing invalidated
zones -- which survived until the same capture was re-run with the default and
every one of those zones came back `NO_BREACH`.

The failure mode was not the flag. It was that nothing recorded which
configuration a comparison had used, so the mismatch was invisible.

These tests pin the defaults that a "production-equivalent" claim depends on,
so that changing one is a deliberate, visible act rather than a silent drift.
"""

from __future__ import annotations

from decimal import Decimal

from btmm_ai_scanner.poi.configuration import PoiConfiguration


def test_the_structural_origin_gate_is_OFF_by_default() -> None:
    """THE flag that caused the wrong conclusion.

    Pine's Stage D gate is deliberately more permissive than this strict
    option -- it also accepts a range boundary, a liquidity pool or a
    trendline. So `True` here is NOT the Pine-equivalent setting, and a
    comparison that sets it is not comparing like with like.
    """
    assert PoiConfiguration(minimum_price_tick=Decimal("0.001")).rc5_structural_origin is False


def test_a_default_configuration_needs_nothing_but_the_tick() -> None:
    """If this ever requires more arguments, every 'production default' claim
    in the repository has to be re-examined."""
    configuration = PoiConfiguration(minimum_price_tick=Decimal("0.001"))
    assert configuration.minimum_price_tick == Decimal("0.001")


def test_the_invalidation_tolerances_are_the_frozen_ones() -> None:
    """The breach rule's constants. A silent change here would move every
    lifecycle result without any test naming it."""
    configuration = PoiConfiguration(minimum_price_tick=Decimal("0.001"))
    assert configuration.zone_overshoot_tolerance_atr_multiplier == Decimal("0.10")
    assert configuration.zone_overshoot_tolerance_zone_height_multiplier == Decimal(
        "0.25"
    )
    assert configuration.reclaim_window_bars == 3


def test_a_non_default_gate_is_visible_when_set() -> None:
    """The guard only helps if the override is observable, not swallowed."""
    overridden = PoiConfiguration(
        minimum_price_tick=Decimal("0.001"), rc5_structural_origin=True
    )
    assert overridden.rc5_structural_origin is True
    assert (
        overridden.rc5_structural_origin
        != PoiConfiguration(minimum_price_tick=Decimal("0.001")).rc5_structural_origin
    ), "an override must differ from the default or the guard is meaningless"
