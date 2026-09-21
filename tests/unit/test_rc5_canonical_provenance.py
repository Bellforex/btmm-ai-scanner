"""RC5 provenance is event history, produced by one canonical path.

Author decision, 2026-09-21 (option A). Three separate defects came from
deriving provenance from the final structural context -- a role that could
lapse, a role upgrade moving ``since`` later, and defended levels dated from
swing confirmation moving it earlier. Each was silent: nothing raised, the POI
simply appeared on the wrong bar, and only a batch-vs-incremental comparison on
real data exposed it.

These tests exist so that class of bug cannot come back quietly.
"""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pytest

from btmm_ai_scanner.config.enums import Timeframe
from btmm_ai_scanner.historical_backtest.identity import (
    ContentAddressedIdentityProvider,
)
from btmm_ai_scanner.poi.authority import FVG_TYPES, REVERSAL_TYPES
from btmm_ai_scanner.poi.configuration import PoiConfiguration
from btmm_ai_scanner.poi.rc5_semantics import (
    Rc5MissingProvenanceError,
    Rc5SemanticLedger,
    assign_origin_authority,
    join_semantic_records,
    replay_rc5_semantic_provenance,
    stable_poi_key,
)
from btmm_ai_scanner.scanner.analyzer import scan_market
from btmm_ai_scanner.scanner.replay import IncrementalReplayKernel
from btmm_ai_scanner.scanner.timeframe_input import ScannerTimeframeInput
from tests.parity_support.level_a_replay import build_scanner_configuration
from tests.parity_support.ob_origin_series import mirror, rows_to_candles
from tests.unit.test_rc3_order_block_leg_origin import _continuation, _reversal

_TICK = Decimal("0.01")
_POI = PoiConfiguration(minimum_price_tick=_TICK, rc5_structural_origin=True)

#: Every field that must be identical wherever provenance is produced.
_PROVENANCE_FIELDS = (
    "poi_type",
    "source_time_utc",
    "availability_time_utc",
    "structural_role",
    "origin_swing_id",
    "broken_swing_id",
    "break_candle_id",
    "structural_since_utc",
)

_SERIES = {
    "continuation": _continuation,
    "continuation_sell": lambda: mirror(_continuation()),
    "reversal": _reversal,
    "reversal_sell": lambda: mirror(_reversal()),
}


def _configuration():
    base = build_scanner_configuration(
        required_timeframes=frozenset({Timeframe.M15}),
        optional_timeframes=frozenset(),
        minimum_price_tick=_TICK,
    )
    return base.model_copy(update={"poi_configuration": _POI})


@pytest.fixture(params=sorted(_SERIES), ids=sorted(_SERIES))
def candles(request: pytest.FixtureRequest, tmp_path: Path):
    return rows_to_candles(_SERIES[request.param](), tmp_path, request.param)


def _batch(candles):
    ledger = Rc5SemanticLedger()
    analysis = scan_market(
        (ScannerTimeframeInput(Timeframe.M15, candles),),
        (),
        _configuration(),
        ContentAddressedIdentityProvider(),
        ledger,
    ).poi_analysis
    return analysis, ledger


def _incremental(candles):
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
    return kernel.finalize().poi_analysis, ledger


# ---------------------------------------------------------------------------
# one canonical producer
# ---------------------------------------------------------------------------


def test_batch_and_incremental_provenance_is_identical(candles) -> None:
    """The property option A exists to guarantee. Batch keeps its optimized
    observation path, but its sidecar comes from the same causal replay."""
    _b, batch = _batch(candles)
    _i, incremental = _incremental(candles)
    assert set(batch.records) == set(incremental.records)
    for key in batch.records:
        for field in _PROVENANCE_FIELDS:
            assert getattr(batch.records[key], field) == getattr(
                incremental.records[key], field
            ), (key[0], field)


def test_frozen_records_stay_identical_across_paths(candles) -> None:
    batch, _bl = _batch(candles)
    incremental, _il = _incremental(candles)
    assert batch.poi_observations == incremental.poi_observations
    assert batch.current_poi_states == incremental.current_poi_states


def test_the_ledger_is_purely_additive(candles) -> None:
    with_ledger, _ = _batch(candles)
    without = scan_market(
        (ScannerTimeframeInput(Timeframe.M15, candles),),
        (),
        _configuration(),
        ContentAddressedIdentityProvider(),
    ).poi_analysis
    assert with_ledger.poi_observations == without.poi_observations


# ---------------------------------------------------------------------------
# provenance is history: it never moves once emitted
# ---------------------------------------------------------------------------


def test_provenance_never_moves_as_later_bars_arrive(candles) -> None:
    """The generic regression for all three defects. A role may not lapse, may
    not be upgraded, and ``since`` may move neither earlier nor later."""
    full = replay_rc5_semantic_provenance(
        candles, _POI, ContentAddressedIdentityProvider()
    )
    for fraction in (2, 3, 4):
        upto = len(candles) * (fraction - 1) // fraction
        if upto < 30:
            continue
        earlier = replay_rc5_semantic_provenance(
            candles[:upto], _POI, ContentAddressedIdentityProvider()
        )
        for key in set(earlier.records) & set(full.records):
            for field in _PROVENANCE_FIELDS:
                assert getattr(earlier.records[key], field) == getattr(
                    full.records[key], field
                ), (key[0], field, upto)


def test_since_is_never_later_than_availability(candles) -> None:
    """``since`` is when the qualifying fact became true; a POI cannot be
    published before its own evidence exists."""
    ledger = replay_rc5_semantic_provenance(
        candles, _POI, ContentAddressedIdentityProvider()
    )
    for record in ledger.records.values():
        if record.structural_since_utc is None:
            continue
        assert record.structural_since_utc <= record.availability_time_utc
        assert record.source_time_utc <= record.availability_time_utc


# ---------------------------------------------------------------------------
# the join, and its refusal to paper over a gap
# ---------------------------------------------------------------------------


def test_every_authority_relevant_poi_joins_to_a_record(candles) -> None:
    analysis, ledger = _batch(candles)
    joined = join_semantic_records(
        analysis.poi_observations, ledger, required_types=REVERSAL_TYPES | FVG_TYPES
    )
    relevant = [
        o
        for o in analysis.poi_observations
        if o.poi_type in (REVERSAL_TYPES | FVG_TYPES)
    ]
    assert len(joined) == len(relevant)


def test_a_missing_record_raises_instead_of_falling_back(candles) -> None:
    """No silent fallback. A gap must stop RC5 analysis, because the
    alternative is path-dependent authority."""
    analysis, _ledger = _batch(candles)
    relevant = [
        o
        for o in analysis.poi_observations
        if o.poi_type in (REVERSAL_TYPES | FVG_TYPES)
    ]
    if not relevant:
        pytest.skip("series produces no authority-relevant POIs")
    with pytest.raises(Rc5MissingProvenanceError):
        join_semantic_records(
            analysis.poi_observations,
            Rc5SemanticLedger(),
            required_types=REVERSAL_TYPES | FVG_TYPES,
        )


# ---------------------------------------------------------------------------
# authority inherits the guarantee
# ---------------------------------------------------------------------------


def test_authority_is_path_independent(candles) -> None:
    batch, batch_ledger = _batch(candles)
    incremental, incremental_ledger = _incremental(candles)
    assign_origin_authority(batch.poi_observations, batch_ledger)
    assign_origin_authority(incremental.poi_observations, incremental_ledger)
    assert batch_ledger.suppressed_keys() == incremental_ledger.suppressed_keys()
    assert batch_ledger.authoritative_keys() == incremental_ledger.authoritative_keys()


def test_a_suppressed_poi_names_its_winner(candles) -> None:
    analysis, ledger = _batch(candles)
    assign_origin_authority(analysis.poi_observations, ledger)
    keys = {stable_poi_key(o) for o in analysis.poi_observations}
    for key in ledger.suppressed_keys():
        record = ledger.get(key)
        assert record is not None
        assert record.authority_winner_key is not None
        assert record.authority_winner_key in keys
        assert record.authority_winner_key != key
