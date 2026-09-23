"""Batch == incremental for everything the final-authority layer decides.

The two producers are genuinely different code: `scan_market` runs the batch
detectors and the batch gate, while `replay_rc5_semantic_provenance` drives the
canonical causal frontier one candle at a time -- the same primitives live
execution runs. They must agree on the Base arrival, on which formation owns
which pattern, on when that ownership began, and on the resulting authoritative
key set.

Walked over prefixes of the real M15 capture, because a structural arrival and
a formation ownership both need real structure to exist at all.
"""

from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

import pytest

from btmm_ai_scanner.config.enums import Timeframe
from btmm_ai_scanner.historical_backtest.identity import (
    ContentAddressedIdentityProvider,
)
from btmm_ai_scanner.poi.authority import AuthorityReason
from btmm_ai_scanner.poi.configuration import PoiConfiguration
from btmm_ai_scanner.poi.rc5_semantics import (
    Rc5SemanticLedger,
    assign_formation_ownership_authority,
    assign_origin_authority,
    authoritative_rc5_pois,
    replay_rc5_semantic_provenance,
    stable_poi_key,
)
from btmm_ai_scanner.scanner.analyzer import scan_market
from btmm_ai_scanner.scanner.timeframe_input import ScannerTimeframeInput
from tests.parity_support.level_a_replay import build_scanner_configuration
from tests.unit._arrival_fixtures import M15_CSV, m15_eurusd

pytestmark = pytest.mark.skipif(
    not M15_CSV.exists(), reason="RC5 M15 forensic capture not present"
)

_TICK = Decimal("0.00001")
_POI = PoiConfiguration(minimum_price_tick=_TICK, rc5_structural_origin=False)

#: Prefixes are expensive here (both producers run the whole pipeline), so they
#: are sampled rather than exhaustive. The first Base lands well before 140.
_PREFIXES = range(140, 301, 40)


def _batch(candles):
    base = build_scanner_configuration(
        required_timeframes=frozenset({Timeframe.M15}),
        optional_timeframes=frozenset(),
        minimum_price_tick=_TICK,
    )
    configuration = base.model_copy(update={"poi_configuration": _POI})
    ledger = Rc5SemanticLedger()
    analysis = scan_market(
        (ScannerTimeframeInput(Timeframe.M15, candles),),
        (),
        configuration,
        ContentAddressedIdentityProvider(),
        ledger,
    ).poi_analysis
    return analysis, ledger


def _arrival_signature(ledger: Rc5SemanticLedger) -> list[tuple]:
    return sorted(
        (
            (key, record.poi_type, record.base_family)
            for key, record in ledger.records.items()
            if record.base_family is not None
        ),
        key=repr,
    )


def _ownership_signature(ledger: Rc5SemanticLedger) -> list[tuple]:
    return sorted(
        (
            (
                key,
                record.formation_owner_key,
                record.formation_subordinate_since_utc,
                record.authority_status,
            )
            for key, record in ledger.records.items()
            if record.authority_status is AuthorityReason.FORMATION_SUBORDINATE
        ),
        key=repr,
    )


def test_batch_and_incremental_agree_on_arrival_and_ownership() -> None:
    candles = m15_eurusd()
    saw_family = False
    saw_ownership = False

    for end in _PREFIXES:
        prefix = candles[:end]

        analysis, batch_ledger = _batch(prefix)
        observations = analysis.poi_observations
        assign_formation_ownership_authority(observations, batch_ledger)
        assign_origin_authority(observations, batch_ledger)

        incremental_ledger = replay_rc5_semantic_provenance(
            prefix, _POI, ContentAddressedIdentityProvider()
        )
        assign_formation_ownership_authority(observations, incremental_ledger)
        assign_origin_authority(observations, incremental_ledger)

        assert _arrival_signature(batch_ledger) == _arrival_signature(
            incremental_ledger
        ), f"Base arrival diverged at prefix {end}"
        assert _ownership_signature(batch_ledger) == _ownership_signature(
            incremental_ledger
        ), f"formation ownership diverged at prefix {end}"

        batch_view = {
            stable_poi_key(o)
            for o in authoritative_rc5_pois(observations, batch_ledger)
        }
        incremental_view = {
            stable_poi_key(o)
            for o in authoritative_rc5_pois(observations, incremental_ledger)
        }
        assert batch_view == incremental_view, (
            f"final authoritative set diverged at prefix {end}"
        )

        saw_family = saw_family or bool(_arrival_signature(batch_ledger))
        saw_ownership = saw_ownership or bool(_ownership_signature(batch_ledger))

    assert saw_family, "no Base arrival was ever resolved; the assertions were vacuous"
    assert saw_ownership, "no ownership ever applied; the assertions were vacuous"


def test_ownership_activation_is_never_earlier_than_either_member() -> None:
    """The causality guarantee, on whatever the real capture produces.

    The invariant is about the WINDOW BEFORE activation, not about the member's
    own availability instant. A co-extensive member confirms at the same moment
    as its owner, so it has no such window and is subordinate immediately -- a
    contained member that confirmed earlier does have one. Both follow from the
    same rule; asserting "actionable at its own availability" would only be
    true of the second kind.
    """
    candles = m15_eurusd()
    analysis, ledger = _batch(candles)
    observations = analysis.poi_observations
    applied = assign_formation_ownership_authority(observations, ledger)
    assert applied, "no ownership applied; the assertion would be vacuous"

    for relationship in applied:
        owner = ledger.get(relationship.owner_key)
        member = ledger.get(relationship.member_key)
        assert relationship.active_from_utc >= owner.availability_time_utc
        assert relationship.active_from_utc >= member.availability_time_utc
        since = relationship.active_from_utc
        assert member.is_actionable_at(since) is False
        # everything strictly before activation is still independent
        assert member.is_actionable_at(since - timedelta(microseconds=1)) is True
        if member.availability_time_utc < since:
            assert member.is_actionable_at(member.availability_time_utc) is True
