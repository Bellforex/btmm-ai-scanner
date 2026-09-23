"""Formation ownership must GOVERN the final authoritative view, not annotate it.

The sidecar already decided that a Base owns the candle patterns it contains.
Until this layer existed that decision changed nothing: the contained pattern
kept full standing, entered the opportunity loop on its own, and emitted its own
lifecycle events -- so a Base containing a Pressure Wick still lost the chart to
the Pressure Wick.

Two ranking systems are kept deliberately apart and are NOT merged:

* `REVERSAL_LADDER` ranks reversal SYNONYMS describing one structural event.
  Base is absent from it and stays absent.
* Formation ownership answers CONTAINMENT.

Ownership runs FIRST, so a subordinate never reaches same-origin arbitration.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from btmm_ai_scanner.config.enums import Timeframe
from btmm_ai_scanner.historical_backtest.identity import (
    ContentAddressedIdentityProvider,
)
from btmm_ai_scanner.poi.authority import REVERSAL_LADDER, AuthorityReason
from btmm_ai_scanner.poi.configuration import PoiConfiguration
from btmm_ai_scanner.poi.enums import BaseFamily, PoiType
from btmm_ai_scanner.poi.formation_ownership import BASE_TYPES, OWNABLE_PATTERN_TYPES
from btmm_ai_scanner.poi.rc5_semantics import (
    Rc5SemanticLedger,
    assign_formation_ownership_authority,
    assign_origin_authority,
    authoritative_rc5_pois,
    stable_poi_key,
    suppressed_record_ids,
)
from btmm_ai_scanner.scanner.analyzer import scan_market
from btmm_ai_scanner.scanner.timeframe_input import ScannerTimeframeInput
from tests.parity_support.level_a_replay import build_scanner_configuration
from tests.unit._arrival_fixtures import M15_CSV, m15_eurusd

pytestmark = pytest.mark.skipif(
    not M15_CSV.exists(), reason="RC5 M15 forensic capture not present"
)

_TICK = Decimal("0.00001")

#: The Base at 2026-09-21 19:15 occupies bars 134-135 with its departure at 136.
_GOLDEN = "2026-09-21 19:15"


def _scan(*, structural_origin: bool):
    """Full pipeline on the real capture, body basis on.

    `structural_origin=False` is the configuration in which the contained
    patterns actually reach the observation layer, which is where ownership has
    something to govern. With the RC5 structural-origin gate on, those same
    patterns are already rejected upstream as mid-leg texture -- a DIFFERENT
    mechanism, proved separately below.
    """
    candles = m15_eurusd()
    base = build_scanner_configuration(
        required_timeframes=frozenset({Timeframe.M15}),
        optional_timeframes=frozenset(),
        minimum_price_tick=_TICK,
    )
    configuration = base.model_copy(
        update={
            "poi_configuration": PoiConfiguration(
                minimum_price_tick=_TICK,
                rc5_structural_origin=structural_origin,
                base_size_uses_body=True,
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
    ).poi_analysis
    return analysis, ledger


def _at(observations, stamp, poi_type):
    hit = [
        o
        for o in observations
        if o.poi_type is poi_type
        and f"{o.candidate_event_time_utc:%Y-%m-%d %H:%M}" == stamp
    ]
    assert len(hit) == 1, f"expected one {poi_type.value} at {stamp}, got {len(hit)}"
    return hit[0]


# ---------------------------------------------------------------------------
# 1. the doctrine boundary that must not move
# ---------------------------------------------------------------------------


def test_base_is_not_in_the_reversal_ladder_and_must_not_be() -> None:
    """A Base is not a synonym for a Shooting Star, so it does not belong in a
    ladder that ranks synonyms. Containment is answered by a different layer."""
    for base_type in BASE_TYPES:
        assert base_type not in REVERSAL_LADDER


# ---------------------------------------------------------------------------
# 2. the golden formation reaches FINAL authority
# ---------------------------------------------------------------------------


def test_golden_base_owns_the_pressure_wick_in_the_final_authoritative_view() -> None:
    analysis, ledger = _scan(structural_origin=False)
    observations = analysis.poi_observations

    applied = assign_formation_ownership_authority(observations, ledger)
    assign_origin_authority(observations, ledger)

    base = _at(observations, _GOLDEN, PoiType.BASE_DROP)
    wick = _at(observations, _GOLDEN, PoiType.BEARISH_PRESSURE_WICK)

    # the owner is the structurally-resolved DBD Base
    assert ledger.get(stable_poi_key(base)).base_family is BaseFamily.DROP_BASE_DROP

    subordinate = ledger.get(stable_poi_key(wick))
    assert subordinate.authority_status is AuthorityReason.FORMATION_SUBORDINATE
    assert subordinate.formation_owner_key == stable_poi_key(base)
    assert subordinate.formation_subordinate_since_utc is not None

    authoritative = {
        stable_poi_key(o) for o in authoritative_rc5_pois(observations, ledger)
    }
    assert stable_poi_key(base) in authoritative
    assert stable_poi_key(wick) not in authoritative

    # and it reaches the downstream bridge P5/P8 actually consume
    assert wick.record_id in suppressed_record_ids(observations, ledger)
    assert base.record_id not in suppressed_record_ids(observations, ledger)

    assert any(r.member_key == stable_poi_key(wick) for r in applied)


def test_the_subordinate_keeps_its_own_type_and_record() -> None:
    """Subordinate does NOT mean deleted. It stays in the ledger with its own
    PoiType, for forensics, parity and historical evidence."""
    analysis, ledger = _scan(structural_origin=False)
    observations = analysis.poi_observations
    assign_formation_ownership_authority(observations, ledger)

    wick = _at(observations, _GOLDEN, PoiType.BEARISH_PRESSURE_WICK)
    record = ledger.get(stable_poi_key(wick))
    assert record is not None
    assert record.poi_type is PoiType.BEARISH_PRESSURE_WICK
    assert wick in observations  # the frozen observation is untouched


# ---------------------------------------------------------------------------
# 3. causality -- no retroactive erasure
# ---------------------------------------------------------------------------


def test_the_subordinate_was_legitimately_actionable_before_its_owner_existed() -> None:
    """The Pressure Wick confirms at 19:30; the Base only exists once its
    departure closes at 20:00. Between those instants the wick was a real,
    independent POI and history must say so."""
    analysis, ledger = _scan(structural_origin=False)
    observations = analysis.poi_observations
    assign_formation_ownership_authority(observations, ledger)

    wick = _at(observations, _GOLDEN, PoiType.BEARISH_PRESSURE_WICK)
    record = ledger.get(stable_poi_key(wick))
    since = record.formation_subordinate_since_utc

    assert record.availability_time_utc < since
    assert record.is_actionable_at(record.availability_time_utc) is True
    assert record.is_actionable_at(since) is False

    # ownership activates when BOTH exist, never earlier
    base = _at(observations, _GOLDEN, PoiType.BASE_DROP)
    assert since == max(
        ledger.get(stable_poi_key(base)).availability_time_utc,
        record.availability_time_utc,
    )


# ---------------------------------------------------------------------------
# 4. ordering -- ownership precedes reversal authority
# ---------------------------------------------------------------------------


def test_same_origin_arbitration_can_never_hand_standing_back() -> None:
    """The ordering guarantee, asserted directly rather than inferred from a
    run in which no cluster happened to contain the subordinate."""
    analysis, ledger = _scan(structural_origin=False)
    observations = analysis.poi_observations
    assign_formation_ownership_authority(observations, ledger)

    wick_key = stable_poi_key(_at(observations, _GOLDEN, PoiType.BEARISH_PRESSURE_WICK))
    assert (
        ledger.get(wick_key).authority_status is AuthorityReason.FORMATION_SUBORDINATE
    )

    # an arbitration result arriving afterwards must be refused
    ledger.assign_authority(wick_key, reason=AuthorityReason.PRIMARY)
    assert (
        ledger.get(wick_key).authority_status is AuthorityReason.FORMATION_SUBORDINATE
    )

    assign_origin_authority(observations, ledger)
    assert (
        ledger.get(wick_key).authority_status is AuthorityReason.FORMATION_SUBORDINATE
    )


# ---------------------------------------------------------------------------
# 5. sidecar and final authority must agree
# ---------------------------------------------------------------------------


def test_sidecar_subordinations_equal_final_authority_suppressions() -> None:
    """Counted over the SAME candidate set, the two must not disagree -- that
    is the whole point of making the sidecar govern."""
    analysis, ledger = _scan(structural_origin=False)
    observations = analysis.poi_observations
    applied = assign_formation_ownership_authority(observations, ledger)

    sidecar_members = {r.member_key for r in applied}
    final = ledger.formation_subordinate_keys()
    assert sidecar_members == final
    assert final <= ledger.suppressed_keys()


# ---------------------------------------------------------------------------
# 6. the boundary case, pinned rather than decided
# ---------------------------------------------------------------------------


def test_a_pattern_spanning_the_departure_candle_is_not_contained() -> None:
    """OPEN AUTHOR DECISION, recorded as measured fact.

    The EVENING_STAR on the same bars spans 134-136. `_base_candle_ids`
    deliberately excludes the departure (136) because the departure is the
    impulse that confirms the base, not part of the pause -- so containment
    fails by exactly one bar and the Evening Star keeps full standing.

    Whether a Base should also own a pattern that ENDS on its departure is a
    doctrine question. This test pins today's behaviour so a change is
    deliberate, and asserts nothing about which answer is right.
    """
    analysis, ledger = _scan(structural_origin=False)
    observations = analysis.poi_observations
    assign_formation_ownership_authority(observations, ledger)

    base = _at(observations, _GOLDEN, PoiType.BASE_DROP)
    star = _at(observations, _GOLDEN, PoiType.EVENING_STAR)

    assert len(star.source_candle_record_ids) == 3
    assert star.source_candle_record_ids == base.source_candle_record_ids
    # identical source candles, yet not contained: the last one is the departure
    assert ledger.get(stable_poi_key(star)).authority_status is not (
        AuthorityReason.FORMATION_SUBORDINATE
    )
    authoritative = {
        stable_poi_key(o) for o in authoritative_rc5_pois(observations, ledger)
    }
    assert stable_poi_key(star) in authoritative


# ---------------------------------------------------------------------------
# 7. the other mechanism, so the two are never confused
# ---------------------------------------------------------------------------


def test_the_structural_origin_gate_removes_these_patterns_earlier_and_separately() -> (
    None
):
    """With `rc5_structural_origin` ON, the contained patterns never reach the
    observation layer at all -- they are rejected upstream as mid-leg texture.

    That is a different mechanism from ownership and must not be mistaken for
    it: it is why the golden formation shows only a Base in RC5's own
    configuration, and why ownership applies nothing there.
    """
    gated, _ = _scan(structural_origin=True)
    ungated, _ = _scan(structural_origin=False)

    def near(analysis):
        return {
            o.poi_type
            for o in analysis.poi_observations
            if f"{o.candidate_event_time_utc:%Y-%m-%d %H:%M}" == _GOLDEN
        }

    assert near(gated) == {PoiType.BASE_DROP}
    assert {PoiType.BEARISH_PRESSURE_WICK, PoiType.EVENING_STAR} <= near(ungated)

    gated_ownable = sum(
        1 for o in gated.poi_observations if o.poi_type in OWNABLE_PATTERN_TYPES
    )
    ungated_ownable = sum(
        1 for o in ungated.poi_observations if o.poi_type in OWNABLE_PATTERN_TYPES
    )
    assert gated_ownable < ungated_ownable


# ---------------------------------------------------------------------------
# 8. RC4 comparison -- does the corrected Base reproduce the remembered box?
# ---------------------------------------------------------------------------


def test_the_corrected_base_reproduces_rc4s_zone_exactly() -> None:
    """The placement question, answered on the frozen capture.

    On these bars RC4 drew an EVENING_STAR over candles 134-136 with the zone
    1.14672-1.14693. The corrected RC5 Base covers the SAME candles with the
    SAME zone and is labelled BASE_DROP / DROP_BASE_DROP.

    So the author was seeing the right rectangle under the wrong name. That is
    also why ownership cannot subordinate this Evening Star: it is not a
    pattern CONTAINED in the Base, it is co-extensive with it -- identical
    source candles, identical geometry. Containment is the wrong tool for a
    duplicate, and inventing a containment rule that swallowed it would have
    hidden that.
    """
    analysis, ledger = _scan(structural_origin=False)
    observations = analysis.poi_observations

    base = _at(observations, _GOLDEN, PoiType.BASE_DROP)
    star = _at(observations, _GOLDEN, PoiType.EVENING_STAR)

    assert base.zone_top == star.zone_top == Decimal("1.14693")
    assert base.zone_bottom == star.zone_bottom == Decimal("1.14672")
    assert base.source_candle_record_ids == star.source_candle_record_ids
    assert ledger.get(stable_poi_key(base)).base_family is BaseFamily.DROP_BASE_DROP


# ---------------------------------------------------------------------------
# 9. P5 / P8 consequence, through the real per-bar replay
# ---------------------------------------------------------------------------


def test_a_formation_subordinate_stops_emitting_but_keeps_its_history() -> None:
    """The consequence the author asked to see, measured bar by bar.

    On the frozen M15 capture the Pressure Wick is first evaluated by the P5
    opportunity loop at 19:30 and first suppressed at 20:00, when its owning
    Base confirms. So:

    * it was independently actionable for exactly 30 minutes (2 bars), and that
      history is NOT erased;
    * from 20:00 it is evaluated zero times by P5;
    * from 20:00 it emits zero P8 events.

    The replay applies ownership per bar against the kernel's own ledger, which
    is what makes the first half of that true rather than an accident.
    """
    from tests.parity_support.level_a_replay import iter_level_a_bars

    candles = m15_eurusd()
    base = build_scanner_configuration(
        required_timeframes=frozenset({Timeframe.M15}),
        optional_timeframes=frozenset(),
        minimum_price_tick=_TICK,
    )
    configuration = base.model_copy(
        update={
            "poi_configuration": PoiConfiguration(
                minimum_price_tick=_TICK,
                rc5_structural_origin=False,
                base_size_uses_body=True,
            )
        }
    )

    first_evaluated: dict[object, object] = {}
    first_suppressed: dict[object, object] = {}
    evaluated_while_suppressed: dict[object, int] = {}
    events_after_suppression: dict[object, int] = {}
    poi_type_of: dict[object, PoiType] = {}

    for bar in iter_level_a_bars(
        host_timeframe=Timeframe.M15,
        host_series=candles,
        context_series={},
        configuration=configuration,
        rc3_freshness=True,
        rc5_authority=True,
    ):
        moment = bar.availability_time_utc
        for poi_id, observation in bar.observation_by_id.items():
            poi_type_of[poi_id] = observation.poi_type
        for poi_id in bar.evaluated_order:
            first_evaluated.setdefault(poi_id, moment)
            if poi_id in bar.suppressed_poi_ids:
                evaluated_while_suppressed[poi_id] = (
                    evaluated_while_suppressed.get(poi_id, 0) + 1
                )
        for poi_id in bar.suppressed_poi_ids:
            first_suppressed.setdefault(poi_id, moment)
        for event in bar.events:
            poi_id = getattr(event, "poi_record_id", None)
            if poi_id is not None and poi_id in first_suppressed:
                events_after_suppression[poi_id] = (
                    events_after_suppression.get(poi_id, 0) + 1
                )

    assert first_suppressed, "nothing was suppressed; the assertions were vacuous"

    wicks = [
        poi_id
        for poi_id in first_suppressed
        if poi_type_of.get(poi_id) is PoiType.BEARISH_PRESSURE_WICK
    ]
    assert len(wicks) == 1
    wick = wicks[0]

    # it stood alone first -- history preserved
    assert first_evaluated[wick] < first_suppressed[wick]
    assert f"{first_evaluated[wick]:%Y-%m-%d %H:%M}" == "2026-09-21 19:30"
    assert f"{first_suppressed[wick]:%Y-%m-%d %H:%M}" == "2026-09-21 20:00"

    # and nothing independent afterwards
    for poi_id in first_suppressed:
        assert evaluated_while_suppressed.get(poi_id, 0) == 0
        assert events_after_suppression.get(poi_id, 0) == 0
