"""RC5 user-facing structure: HH / HL / LH / LL.

No second swing engine. The population is the canonical meaningful swing
sidecar -- the swings the structure walk actually used, which is the same
population BOS / CHOCH is built from. Internal SH / SL are untouched.
"""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pytest

from btmm_ai_scanner.config.enums import Timeframe
from btmm_ai_scanner.domain.enums import SwingType
from btmm_ai_scanner.historical_backtest.identity import (
    ContentAddressedIdentityProvider,
)
from btmm_ai_scanner.poi.configuration import PoiConfiguration
from btmm_ai_scanner.poi.rc5_semantics import Rc5SemanticLedger
from btmm_ai_scanner.poi.rc5_structure import StructureLabel, label_market_structure
from btmm_ai_scanner.scanner.analyzer import scan_market
from btmm_ai_scanner.scanner.timeframe_input import ScannerTimeframeInput
from tests.parity_support.level_a_replay import build_scanner_configuration
from tests.parity_support.ob_origin_series import mirror, rows_to_candles, trend
from tests.unit.test_rc3_order_block_leg_origin import _continuation, _reversal

_TICK = Decimal("0.01")

_SERIES = {
    "bull_continuation": _continuation,
    "bear_continuation": lambda: mirror(_continuation()),
    "reversal": _reversal,
    "reversal_mirror": lambda: mirror(_reversal()),
    "bull_then_bear": lambda: _continuation() + trend(139.8, -1.2, 45),
    "bear_then_bull": lambda: mirror(_continuation()) + trend(60.2, 1.2, 45),
}


def _analyse(candles):
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
    analysis = scan_market(
        (ScannerTimeframeInput(Timeframe.M15, candles),),
        (),
        configuration,
        ContentAddressedIdentityProvider(),
        ledger,
    )
    measurement = next(
        m for m in analysis.measurement_analyses if m.timeframe is Timeframe.M15
    )
    structure = next(
        (s for s in analysis.structure_analyses if s.timeframe is Timeframe.M15), None
    )
    labels = label_market_structure(measurement.confirmed_swings, ledger)
    return measurement, structure, ledger, labels


@pytest.fixture(params=sorted(_SERIES), ids=sorted(_SERIES))
def analysed(request: pytest.FixtureRequest, tmp_path: Path):
    candles = rows_to_candles(_SERIES[request.param](), tmp_path, request.param)
    return _analyse(candles)


def test_labels_come_only_from_meaningful_swings(analysed) -> None:
    """Texture the walk never used keeps its internal SH/SL and gets no
    user-facing label -- that is what stops the chart being covered in them."""
    measurement, _structure, ledger, labels = analysed
    assert labels, "series produced no structure labels"
    for entry in labels:
        assert ledger.swing_role(entry.swing_record_id) is not None
    assert len(labels) < len(measurement.confirmed_swings)


def test_a_high_is_compared_with_the_previous_high(analysed) -> None:
    """Highs and lows sequence independently: HH compares a high with the
    previous HIGH, not with whatever confirmed in between."""
    measurement, _structure, _ledger, labels = analysed
    by_id = {s.record_id: s for s in measurement.confirmed_swings}
    for entry in labels:
        swing = by_id[entry.swing_record_id]
        earlier = by_id[entry.previous_swing_record_id]
        assert swing.swing_type is earlier.swing_type
        if entry.label in (StructureLabel.HIGHER_HIGH, StructureLabel.LOWER_HIGH):
            assert swing.swing_type is SwingType.SWING_HIGH
        else:
            assert swing.swing_type is SwingType.SWING_LOW


def test_the_direction_of_every_label_matches_the_prices(analysed) -> None:
    measurement, _structure, _ledger, labels = analysed
    by_id = {s.record_id: s for s in measurement.confirmed_swings}
    for entry in labels:
        swing = by_id[entry.swing_record_id]
        earlier = by_id[entry.previous_swing_record_id]
        higher = swing.pivot_price > earlier.pivot_price
        if entry.label in (StructureLabel.HIGHER_HIGH, StructureLabel.HIGHER_LOW):
            assert higher
        else:
            assert not higher


def test_a_label_is_never_knowable_before_confirmation(analysed) -> None:
    """The causality rule. Pine may DRAW the text back at the pivot candle; the
    semantic fact belongs to the confirmation bar."""
    measurement, _structure, _ledger, labels = analysed
    by_id = {s.record_id: s for s in measurement.confirmed_swings}
    for entry in labels:
        swing = by_id[entry.swing_record_id]
        assert entry.available_from_utc == swing.meaningful_confirmation_time_utc
        assert entry.available_from_utc >= swing.pivot_end_time_utc


def test_equal_pivots_are_not_forced_into_a_label(tmp_path: Path) -> None:
    """Ambiguity under the swing's own frozen pivot_tie_tolerance gets NO
    label rather than an invented HH or LH. No structural epsilon is
    introduced -- that tolerance already governs pivot ties."""
    from btmm_ai_scanner.poi.rc5_structure import label_market_structure as run

    class _Swing:
        def __init__(self, price, when, side) -> None:
            self.record_id = f"s{when}"
            self.pivot_price = Decimal(price)
            self.pivot_tie_tolerance = Decimal("0.50")
            self.swing_type = side
            self.meaningful_confirmation_time_utc = when
            self.pivot_end_time_utc = when

    class _Ledger:
        def swing_role(self, _):
            return object()

    equal = [
        _Swing("100.00", 1, SwingType.SWING_HIGH),
        _Swing("100.30", 2, SwingType.SWING_HIGH),  # inside tolerance
        _Swing("103.00", 3, SwingType.SWING_HIGH),  # clearly higher
    ]
    labels = run(equal, _Ledger())
    assert len(labels) == 1
    assert labels[0].label is StructureLabel.HIGHER_HIGH


def test_labels_do_not_contradict_the_bos_choch_stream(analysed) -> None:
    """The visible sequence and the transition stream must tell one story.

    Stated carefully, because the obvious version is WRONG: "a bearish
    transition implies an LL label somewhere" fails on a sharp monotonic
    decline. A BOS breaks an EXISTING low, while a label needs a NEWLY
    CONFIRMED meaningful low -- and a straight-line drop confirms none until
    price turns. The transition is real and there is simply nothing yet to
    label.

    What must hold is the direction of travel AFTER a transition: once a
    bearish break has happened and new meaningful lows do confirm, they cannot
    all be higher lows.
    """
    _measurement, structure, _ledger, labels = analysed
    if structure is None or not structure.structure_transitions:
        pytest.skip("series produced no structure transitions")

    for prefix, downward in (("BULLISH", False), ("BEARISH", True)):
        breaks = [
            t
            for t in structure.structure_transitions
            if t.transition_type.value.startswith(prefix)
        ]
        if not breaks:
            continue
        first = min(t.availability_time_utc for t in breaks)
        after = [entry for entry in labels if entry.available_from_utc >= first]
        if len(after) < 2:
            continue
        downside = {StructureLabel.LOWER_LOW, StructureLabel.LOWER_HIGH}
        found = {entry.label for entry in after}
        if downward:
            assert found & downside, f"no downside label after a {prefix} break"
        else:
            assert found - downside, f"no upside label after a {prefix} break"


def test_labels_are_stable_as_the_series_grows(tmp_path: Path) -> None:
    """A later bar must not rewrite a historical label."""
    rows = _continuation() + trend(139.8, -1.2, 45)
    candles = rows_to_candles(rows, tmp_path, "stability")
    _m, _s, _l, full = _analyse(candles)
    assert full
    for fraction in (3, 2):
        upto = len(candles) * (fraction - 1) // fraction
        _m2, _s2, _l2, earlier = _analyse(candles[:upto])
        cutoff = candles[upto - 1].availability_time_utc
        expected = {
            e.swing_record_id: e.label for e in full if e.available_from_utc <= cutoff
        }
        for entry in earlier:
            if entry.swing_record_id in expected:
                assert expected[entry.swing_record_id] is entry.label
