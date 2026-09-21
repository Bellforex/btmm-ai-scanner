"""RC5 per-swing structural sidecar.

Liquidity needs to know which LEVELS the structure walk actually used. That
fact already exists — ``leg_origin.StructuralContext.role_by_swing`` — so the
sidecar exposes it rather than computing it again. There is deliberately no
second structural classifier.

WHY THIS IS PATH-INDEPENDENT BY CONSTRUCTION. The batch gate records no RC5
provenance at all (``leg_origin.batch_leg_origin_gate``); batch fills its
ledger by running ``replay_rc5_semantic_provenance``, the same causal frontier
the incremental kernel runs. Both paths therefore execute the *same* code to
produce these records. The equality tests below still measure it, because
"should be identical by construction" is what was believed the last three times
a path-dependence defect shipped.
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
from btmm_ai_scanner.poi.rc5_semantics import (
    MEANINGFUL_STRUCTURAL_ROLES,
    Rc5SemanticLedger,
    Rc5SwingSemanticRecord,
)
from btmm_ai_scanner.poi.structural_role import StructuralRole
from btmm_ai_scanner.scanner.analyzer import scan_market
from btmm_ai_scanner.scanner.replay import IncrementalReplayKernel
from btmm_ai_scanner.scanner.timeframe_input import ScannerTimeframeInput
from tests.parity_support.level_a_replay import build_scanner_configuration
from tests.parity_support.ob_origin_series import mirror, rows_to_candles, trend
from tests.unit.test_rc3_order_block_leg_origin import _continuation, _reversal

_TICK = Decimal("0.01")

_SERIES = {
    "continuation": _continuation,
    "reversal": _reversal,
    "collapse": lambda: _continuation() + trend(139.8, -1.2, 40),
    "collapse_mirror": lambda: mirror(_continuation() + trend(139.8, -1.2, 40)),
}


def _configuration():
    base = build_scanner_configuration(
        required_timeframes=frozenset({Timeframe.M15}),
        optional_timeframes=frozenset(),
        minimum_price_tick=_TICK,
    )
    return base.model_copy(
        update={
            "poi_configuration": PoiConfiguration(
                minimum_price_tick=_TICK, rc5_structural_origin=True
            )
        }
    )


def _batch(candles) -> Rc5SemanticLedger:
    ledger = Rc5SemanticLedger()
    scan_market(
        (ScannerTimeframeInput(Timeframe.M15, candles),),
        (),
        _configuration(),
        ContentAddressedIdentityProvider(),
        ledger,
    )
    return ledger


def _incremental(candles) -> Rc5SemanticLedger:
    ledger = Rc5SemanticLedger()
    kernel = IncrementalReplayKernel(
        (Timeframe.M15,),
        _configuration(),
        ContentAddressedIdentityProvider(),
        (),
        ledger,
    )
    for candle in candles:
        kernel.advance_group({Timeframe.M15: (candle,)})
    kernel.finalize()
    return ledger


@pytest.fixture(params=sorted(_SERIES), ids=sorted(_SERIES))
def candles(request: pytest.FixtureRequest, tmp_path: Path):
    return rows_to_candles(_SERIES[request.param](), tmp_path, request.param)


# ---------------------------------------------------------------------------
# path independence
# ---------------------------------------------------------------------------


def test_the_swing_sidecar_is_batch_incremental_exact(candles) -> None:
    batch, incremental = _batch(candles), _incremental(candles)
    assert set(batch.swing_roles) == set(incremental.swing_roles)
    for swing_id, entry in batch.swing_roles.items():
        assert entry == incremental.swing_roles[swing_id], swing_id
    assert batch.meaningful_swing_ids() == incremental.meaningful_swing_ids()


def test_batch_populates_the_sidecar_at_all(candles) -> None:
    """The defect found while wiring this: the batch path copies the canonical
    replay's records into its ledger, and copying only the POI records left
    batch with an EMPTY swing sidecar while incremental had a full one. Nothing
    downstream distinguishes "no meaningful swings" from "never populated", so
    it would have failed silently as "no qualified liquidity"."""
    batch = _batch(candles)
    assert batch.swing_roles, "batch produced no swing roles"
    assert batch.meaningful_swing_ids()


# ---------------------------------------------------------------------------
# write-once
# ---------------------------------------------------------------------------


def test_a_swing_role_is_never_overwritten() -> None:
    from datetime import UTC, datetime

    ledger = Rc5SemanticLedger()
    first = datetime(2026, 1, 1, tzinfo=UTC)
    later = datetime(2026, 1, 2, tzinfo=UTC)
    ledger.record_swing_role(
        Rc5SwingSemanticRecord("s1", StructuralRole.PULLBACK_LOW, first)
    )
    ledger.record_swing_role(
        Rc5SwingSemanticRecord("s1", StructuralRole.LEG_ORIGIN, later)
    )
    entry = ledger.swing_role("s1")
    assert entry is not None
    assert entry.role is StructuralRole.PULLBACK_LOW
    assert entry.first_qualified_since == first


def test_a_prefix_role_survives_into_the_full_series(candles) -> None:
    """Growing the series may ADD swings but must never revise one, or
    ``first_qualified_since`` moves and causality is lost."""
    full = _incremental(candles).swing_roles
    for fraction in (2, 3):
        upto = len(candles) * (fraction - 1) // fraction
        if upto < 30:
            continue
        earlier = _incremental(candles[:upto]).swing_roles
        for swing_id, entry in earlier.items():
            assert full.get(swing_id) == entry, swing_id


# ---------------------------------------------------------------------------
# the frozen role doctrine
# ---------------------------------------------------------------------------


def test_the_meaningful_role_set_is_exactly_the_frozen_five() -> None:
    assert MEANINGFUL_STRUCTURAL_ROLES == {
        StructuralRole.LEG_ORIGIN,
        StructuralRole.SWING_HIGH_ORIGIN,
        StructuralRole.SWING_LOW_ORIGIN,
        StructuralRole.PULLBACK_HIGH,
        StructuralRole.PULLBACK_LOW,
    }


def test_there_is_no_impulse_origin_role() -> None:
    """Measured at 84 of 85 on M15 -- it discriminates nothing."""
    assert not hasattr(StructuralRole, "IMPULSE_ORIGIN")


def test_texture_roles_are_not_meaningful() -> None:
    for role in (
        StructuralRole.RANGE_HIGH,
        StructuralRole.RANGE_LOW,
        StructuralRole.LIQUIDITY_EXTREME,
        StructuralRole.TRENDLINE_EXTREME,
        StructuralRole.MID_LEG,
    ):
        assert role not in MEANINGFUL_STRUCTURAL_ROLES
        assert not Rc5SwingSemanticRecord("s", role, _EPOCH).is_meaningful


def test_recorded_roles_are_all_meaningful_in_practice(candles) -> None:
    """An honest record of what the filter actually does today.

    ``role_by_swing`` only ever contains swings the walk USED, and every role it
    claims is one of the meaningful five, so ``is_meaningful`` currently admits
    everything in the sidecar. The filter still earns its place -- the sidecar
    holds far fewer swings than the series confirms -- but it is not what does
    the narrowing, and a reader should not believe otherwise.

    It is kept as a guard: the role set is frozen, the claim sites are not.
    """
    for entry in _incremental(candles).swing_roles.values():
        assert entry.is_meaningful, entry.role


def test_the_sidecar_is_a_strict_subset_of_confirmed_swings(candles) -> None:
    """Where the narrowing actually comes from: most confirmed swings are
    texture the walk never used, and they never enter the sidecar."""
    from btmm_ai_scanner.domain.analyzer import analyze_market_measurements
    from btmm_ai_scanner.domain.configuration import MarketMeasurementConfiguration

    measurement = analyze_market_measurements(
        candles,
        MarketMeasurementConfiguration(minimum_price_tick=_TICK),
        ContentAddressedIdentityProvider(),
    )
    confirmed = {s.record_id for s in measurement.confirmed_swings}
    recorded = set(_incremental(candles).swing_roles)
    assert recorded <= confirmed
    assert len(recorded) < len(confirmed), "sidecar narrowed nothing"


_EPOCH = __import__("datetime").datetime(2026, 1, 1, tzinfo=__import__("datetime").UTC)
