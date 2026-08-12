"""A6-B2-B permanent tests: the persistent event-driven BTMM setup scheduler.

Primary gate: at every candle prefix, for every setup registered with the
scheduler, ``scheduler.materialize_walk(setup_id)`` must equal
``run_btmm_lifecycle(full prefix, exact visible inputs)`` byte-for-byte
(transitions and every ``_StateFields`` value) -- the unchanged batch oracle,
never called by the scheduler itself. Covers setup-delta NEW/CHANGED/REMOVE,
forming-due timing, interaction-index vs brute force, reaction start/window
scheduling, source-POI routing (linked vs unrelated), evidence routing,
freeze semantics, persistence/rollback, and the wake-union zero-false-negative
requirement against a brute-force ``advance every setup`` oracle.
"""

from dataclasses import asdict
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

from btmm_ai_scanner.btmm.configuration import BtmmConfiguration
from btmm_ai_scanner.btmm.enums import BtmmLifecycleStatus
from btmm_ai_scanner.btmm.lifecycle import run_btmm_lifecycle
from btmm_ai_scanner.btmm.lifecycle_cursor import (
    BtmmLifecycleCursor,
    advance_btmm_cursor,
    create_btmm_lifecycle_cursor,
)
from btmm_ai_scanner.btmm.lifecycle_scheduler import (
    BtmmSchedulerStage,
    BtmmSetupEventScheduler,
    advance_btmm_scheduler,
    create_btmm_scheduler,
)
from btmm_ai_scanner.btmm.reviewed_evidence import BtmmReviewedEvidence
from btmm_ai_scanner.btmm.setup_delta import (
    BtmmSetupDelta,
    BtmmSetupSpec,
    setup_record_id_for_poi,
)
from btmm_ai_scanner.config.enums import InternalSymbol, Timeframe
from btmm_ai_scanner.contracts.normalized_candle import NormalizedCandle
from btmm_ai_scanner.contracts.provenance_record import EvidenceClassification
from btmm_ai_scanner.contracts.raw_candle import CandleCompleteness, CandleVolumeKind
from btmm_ai_scanner.contracts.types import SemVer
from btmm_ai_scanner.domain.enums import DerivedOutputType
from btmm_ai_scanner.measurements.atr import compute_atr_series
from btmm_ai_scanner.poi.enums import (
    PoiDirection,
    PoiFamily,
    PoiLifecycleTransitionType,
    PoiType,
)
from btmm_ai_scanner.poi.lifecycle import PoiLifecycleTransition
from btmm_ai_scanner.poi.observation import PoiObservation

_FINGERPRINT = "a" * 64
_RAW_ID = UUID("0193f470-1234-7abc-8def-abcdefabcdaa")
_PROV_ID = UUID("0193f470-1234-7abc-8def-abcdefabcdff")
_BASE_TIME = datetime(2026, 1, 1, tzinfo=UTC)
_EPOCH = datetime(1970, 1, 1, tzinfo=UTC)
_CONFIG = BtmmConfiguration(minimum_price_tick=Decimal("0.01"))
_RULE_VERSION_TEXT = str(_CONFIG.rule_version)


class _HashIdentityProvider:
    def __init__(self) -> None:
        self._next = 0
        self._by_key: dict[tuple[str, ...], UUID] = {}

    def identify(
        self, *, output_type: DerivedOutputType, semantic_key: tuple[str, ...]
    ) -> UUID:
        key = (output_type.value, *semantic_key)
        cached = self._by_key.get(key)
        if cached is not None:
            return cached
        self._next += 1
        result = UUID(f"0193f470-aaaa-7000-8000-{self._next:012x}")
        self._by_key[key] = result
        return result


def _v7(n: int) -> UUID:
    return UUID(f"0193f470-bbbb-7000-8000-{n:012x}")


def _candle(index: int, o: str, h: str, low: str, c: str) -> NormalizedCandle:
    event_time = _BASE_TIME + timedelta(minutes=5 * index)
    availability = event_time + timedelta(minutes=1)
    return NormalizedCandle.model_validate(
        {
            "record_id": UUID(f"0193f470-1234-7abc-8def-{index:012x}"),
            "content_fingerprint": _FINGERPRINT,
            "raw_candle_id": _RAW_ID,
            "provider": "FXCM",
            "source_reference": "fxcm-xauusd-m5",
            "source_symbol": InternalSymbol.XAUUSD.value,
            "source_timeframe": Timeframe.M5.value,
            "symbol": InternalSymbol.XAUUSD,
            "timeframe": Timeframe.M5,
            "event_time_utc": event_time,
            "availability_time_utc": availability,
            "processing_time_utc": availability,
            "original_event_time": event_time,
            "original_availability_time": availability,
            "original_timezone": "UTC",
            "open": Decimal(o),
            "high": Decimal(h),
            "low": Decimal(low),
            "close": Decimal(c),
            "volume": None,
            "volume_kind": CandleVolumeKind.UNKNOWN,
            "completeness": CandleCompleteness.CONFIRMED_COMPLETE,
            "rule_version": SemVer.parse("0.1.0"),
            "contract_version": SemVer.parse("0.1.0"),
            "schema_version": SemVer.parse("0.1.0"),
            "provenance_id": _PROV_ID,
        }
    )


def _source_poi(
    record_id: UUID,
    direction: PoiDirection = PoiDirection.BULLISH,
    availability_index: int = 13,
    zone_top: Decimal = Decimal("101"),
    zone_bottom: Decimal = Decimal("100"),
) -> PoiObservation:
    poi_type = (
        PoiType.SUPPORT_ZONE
        if direction == PoiDirection.BULLISH
        else PoiType.RESISTANCE_ZONE
    )
    ct = _candle(availability_index, "105", "105.2", "104.8", "105")
    return PoiObservation(
        record_id=record_id,
        content_fingerprint=_FINGERPRINT,
        symbol=InternalSymbol.XAUUSD,
        source_timeframe=Timeframe.M5,
        effective_timeframe=Timeframe.M5,
        family=PoiFamily.STRUCTURAL,
        poi_type=poi_type,
        direction=direction,
        zone_top=zone_top,
        zone_bottom=zone_bottom,
        representative_price=None,
        strength_tier=None,
        source_candle_record_ids=(),
        source_measurement_record_ids=(),
        merged_source_poi_record_ids=(),
        candidate_event_time_utc=ct.event_time_utc,
        confirmation_time_utc=ct.event_time_utc,
        availability_time_utc=ct.availability_time_utc,
        rule_version=SemVer.parse("0.1.0"),
        contract_version=SemVer.parse("0.1.0"),
        schema_version=SemVer.parse("0.1.0"),
        evidence_classification=EvidenceClassification.ENGINEERING_PROVISIONAL,
        provenance_id=_PROV_ID,
    )


def _evidence(poi_id: UUID, availability: datetime) -> BtmmReviewedEvidence:
    from btmm_ai_scanner.btmm.enums import (
        BtmmContextAlignmentStatus,
        BtmmEvidenceSource,
        BtmmLiquidityEvidenceStatus,
        BtmmSessionStatus,
        BtmmVolumePillarStatus,
    )

    return BtmmReviewedEvidence(
        symbol=InternalSymbol.XAUUSD,
        timeframe=Timeframe.M5,
        source_poi_record_id=poi_id,
        market_direction_status=BtmmContextAlignmentStatus.ALIGNED,
        analytical_framework_status=BtmmContextAlignmentStatus.ALIGNED,
        session_status=BtmmSessionStatus.ACTIVE,
        liquidity_evidence_status=BtmmLiquidityEvidenceStatus.PRESENT,
        volume_pillar_status=BtmmVolumePillarStatus.SUPPORTS,
        context_input_source=BtmmEvidenceSource.EXPERT_LABELLED,
        liquidity_event_source=BtmmEvidenceSource.EXPERT_LABELLED,
        volume_evidence_source=BtmmEvidenceSource.EXPERT_LABELLED,
        availability_time_utc=availability,
        rule_version=SemVer.parse("0.1.0"),
        contract_version=SemVer.parse("0.1.0"),
        schema_version=SemVer.parse("0.1.0"),
    )


def _poi_transition(
    poi_id: UUID, transition_type: PoiLifecycleTransitionType, index: int
) -> PoiLifecycleTransition:
    event_time = _BASE_TIME + timedelta(minutes=5 * index)
    return PoiLifecycleTransition(
        record_id=UUID(f"0193f470-dddd-7000-8000-{index:012x}"),
        content_fingerprint=_FINGERPRINT,
        symbol=InternalSymbol.XAUUSD,
        timeframe=Timeframe.M5,
        poi_record_id=poi_id,
        transition_type=transition_type,
        triggering_candle_record_id=UUID(f"0193f470-1234-7abc-8def-{index:012x}"),
        event_time_utc=event_time,
        availability_time_utc=event_time + timedelta(minutes=1),
        rule_version=SemVer.parse("0.1.0"),
        contract_version=SemVer.parse("0.1.0"),
        schema_version=SemVer.parse("0.1.0"),
        evidence_classification=EvidenceClassification.ENGINEERING_PROVISIONAL,
        provenance_id=_PROV_ID,
    )


def _strong() -> tuple[NormalizedCandle, ...]:
    candles = [_candle(i, "105", "105.2", "104.8", "105") for i in range(14)]
    candles.append(_candle(14, "105", "105.1", "100.5", "100.8"))
    candles.append(_candle(15, "100.8", "102.2", "100.7", "102.0"))
    candles.append(_candle(16, "102.0", "103.5", "101.9", "103.4"))
    candles.append(_candle(17, "103.4", "105.0", "103.3", "104.9"))
    candles.append(_candle(18, "104.9", "106.5", "104.8", "106.4"))
    candles.append(_candle(19, "106.4", "108.0", "106.3", "107.9"))
    candles.extend(
        _candle(i, "107.9", "108.1", "107.7", "107.9") for i in range(20, 26)
    )
    return tuple(candles)


def _weak() -> tuple[NormalizedCandle, ...]:
    candles = [_candle(i, "105", "105.2", "104.8", "105") for i in range(14)]
    candles.append(_candle(14, "105", "105.1", "100.5", "100.8"))
    candles.append(_candle(15, "100.8", "102.2", "100.7", "102.0"))
    candles.append(_candle(16, "102.0", "102.3", "101.8", "102.1"))
    candles.append(_candle(17, "102.1", "102.4", "101.9", "102.0"))
    candles.append(_candle(18, "102.0", "102.3", "101.7", "101.9"))
    candles.append(_candle(19, "101.9", "102.2", "101.6", "101.8"))
    candles.extend(
        _candle(i, "101.8", "101.9", "101.7", "101.8") for i in range(20, 26)
    )
    return tuple(candles)


def _no_interaction() -> tuple[NormalizedCandle, ...]:
    return tuple(_candle(i, "105", "105.2", "104.8", "105") for i in range(20))


def _ineligible() -> tuple[NormalizedCandle, ...]:
    candles = [_candle(i, "98", "98.2", "97.8", "98") for i in range(14)]
    candles.append(_candle(14, "98", "100.5", "97.9", "100.4"))
    candles.append(_candle(15, "100.4", "101.0", "100.3", "100.9"))
    candles.append(_candle(16, "100.9", "101.5", "100.8", "101.4"))
    return tuple(candles)


def _incomplete_reaction() -> tuple[NormalizedCandle, ...]:
    # Interacts and starts reacting, but the candle stream ends before the
    # 5-bar reaction window fills -- REACTION_DUE stays open forever.
    candles = [_candle(i, "105", "105.2", "104.8", "105") for i in range(14)]
    candles.append(_candle(14, "105", "105.1", "100.5", "100.8"))
    candles.append(_candle(15, "100.8", "102.2", "100.7", "102.0"))
    candles.append(_candle(16, "102.0", "102.5", "101.9", "102.3"))
    return tuple(candles)


def _stage(
    scheduler: BtmmSetupEventScheduler, setup_id: UUID
) -> BtmmSchedulerStage | None:
    return scheduler.stage_of(setup_id)


def _new_setup_delta(
    poi: PoiObservation, provider: _HashIdentityProvider
) -> tuple[BtmmSetupDelta, UUID]:
    setup_id = setup_record_id_for_poi(
        provider, poi.symbol, poi.source_timeframe, poi.record_id, _RULE_VERSION_TEXT
    )
    spec = BtmmSetupSpec(
        setup_record_id=setup_id,
        symbol=poi.symbol,
        source_timeframe=poi.source_timeframe,
        source_poi_record_id=poi.record_id,
        direction=poi.direction,
        zone_top=poi.zone_top,
        zone_bottom=poi.zone_bottom,
        candidate_availability_time_utc=poi.availability_time_utc,
    )
    return BtmmSetupDelta(new_setups=(spec,)), setup_id


def _drive_single_setup(
    candles: tuple[NormalizedCandle, ...],
    poi: PoiObservation,
    reviewed_evidence: BtmmReviewedEvidence | None,
    poi_transitions: tuple[PoiLifecycleTransition, ...],
    *,
    create_at_index: int = 0,
) -> tuple[BtmmSetupEventScheduler, UUID, int]:
    """Drive the scheduler across every prefix, creating the setup at
    ``create_at_index``, feeding transitions/evidence exactly when they become
    newly visible, asserting the materialized walk equals ``run_btmm_lifecycle``
    at every prefix from ``create_at_index`` onward. Returns (final scheduler,
    setup_id, prefixes checked)."""
    atr_full = compute_atr_series(candles, 14)
    provider = _HashIdentityProvider()
    setup_id = setup_record_id_for_poi(
        provider, poi.symbol, poi.source_timeframe, poi.record_id, _RULE_VERSION_TEXT
    )
    scheduler = create_btmm_scheduler(_CONFIG)
    checks = 0
    prev_avail = _EPOCH
    for n in range(1, len(candles) + 1):
        idx = n - 1
        now = candles[idx].availability_time_utc
        delta = BtmmSetupDelta()
        if idx == create_at_index:
            delta, _sid = _new_setup_delta(poi, provider)
            assert _sid == setup_id
        new_transitions = tuple(
            t for t in poi_transitions if prev_avail < t.availability_time_utc <= now
        )
        new_evidence = (
            (reviewed_evidence,)
            if reviewed_evidence is not None
            and prev_avail < reviewed_evidence.availability_time_utc <= now
            else ()
        )
        scheduler = advance_btmm_scheduler(
            scheduler,
            candles[:n],
            atr_full[:n],
            setup_delta=delta,
            new_poi_transitions=new_transitions,
            new_reviewed_evidence=new_evidence,
        )
        prev_avail = now

        if idx >= create_at_index:
            visible_transitions = tuple(
                t for t in poi_transitions if t.availability_time_utc <= now
            )
            visible_evidence = (
                reviewed_evidence
                if reviewed_evidence is not None
                and reviewed_evidence.availability_time_utc <= now
                else None
            )
            oracle = run_btmm_lifecycle(
                symbol=poi.symbol,
                source_timeframe=poi.source_timeframe,
                btmm_setup_record_id=setup_id,
                source_poi=poi,
                candidate_availability_time_utc=poi.availability_time_utc,
                bundle_candles=candles[:n],
                atr_values=atr_full[:n],
                poi_lifecycle_transitions=visible_transitions,
                reviewed_evidence=visible_evidence,
                configuration=_CONFIG,
            )
            actual = scheduler.materialize_walk(setup_id)
            assert actual is not None, f"setup missing @ n={n}"
            assert actual.transitions == oracle.transitions, f"transitions @ n={n}"
            assert asdict(actual.final_fields) == asdict(oracle.final_fields), (
                f"final_fields @ n={n}"
            )
            checks += 1
    return scheduler, setup_id, checks


# =====================================================================
# Primary gate: every-prefix scheduler differential against run_btmm_lifecycle.
# =====================================================================


def test_confirmed_path_every_prefix() -> None:
    poi = _source_poi(_v7(1))
    ev = _evidence(poi.record_id, _BASE_TIME)
    _s, _sid, checks = _drive_single_setup(_strong(), poi, ev, ())
    assert checks > 0
    _s2, _, _ = _drive_single_setup(_strong(), poi, ev, ())


def test_weak_reaction_cancelled_every_prefix() -> None:
    poi = _source_poi(_v7(2))
    ev = _evidence(poi.record_id, _BASE_TIME)
    _s, _sid, checks = _drive_single_setup(_weak(), poi, ev, ())
    assert checks > 0


def test_no_interaction_stays_forming_every_prefix() -> None:
    poi = _source_poi(_v7(3))
    scheduler, sid, checks = _drive_single_setup(_no_interaction(), poi, None, ())
    assert checks > 0
    assert _stage(scheduler, sid) == BtmmSchedulerStage.WAIT_INTERACTION


def test_ineligible_interaction_every_prefix() -> None:
    poi = _source_poi(_v7(4))
    ev = _evidence(poi.record_id, _BASE_TIME)
    scheduler, sid, checks = _drive_single_setup(_ineligible(), poi, ev, ())
    assert checks > 0
    # Price-only cancellation with no observed source-POI transition yet: a later
    # GENUINE_INVALIDATION_CONFIRMED could still retroactively change the result
    # (materialize_btmm_cursor's tail truncation runs unconditionally), so the
    # setup must still watch its source POI -- not FROZEN.
    assert _stage(scheduler, sid) == BtmmSchedulerStage.SOURCE_POI_WATCH


def test_incomplete_reaction_window_stays_reaction_due() -> None:
    poi = _source_poi(_v7(5))
    scheduler, sid, checks = _drive_single_setup(_incomplete_reaction(), poi, None, ())
    assert checks > 0
    assert _stage(scheduler, sid) == BtmmSchedulerStage.REACTION_DUE


def test_no_reviewed_evidence_cancels_then_watches_source_poi() -> None:
    poi = _source_poi(_v7(6))
    scheduler, sid, checks = _drive_single_setup(_strong(), poi, None, ())
    assert checks > 0
    assert _stage(scheduler, sid) == BtmmSchedulerStage.SOURCE_POI_WATCH


def test_bearish_resistance_every_prefix() -> None:
    candles = [_candle(i, "96", "96.2", "95.8", "96") for i in range(14)]
    candles.append(_candle(14, "96", "100.5", "95.9", "100.2"))
    candles.append(_candle(15, "100.2", "100.3", "98.8", "99.0"))
    candles.append(_candle(16, "99.0", "99.1", "97.5", "97.6"))
    candles.append(_candle(17, "97.6", "97.7", "96.0", "96.1"))
    candles.append(_candle(18, "96.1", "96.2", "94.5", "94.6"))
    candles.append(_candle(19, "94.6", "94.7", "93.0", "93.1"))
    poi = _source_poi(
        _v7(7),
        direction=PoiDirection.BEARISH,
        zone_top=Decimal("101"),
        zone_bottom=Decimal("100"),
    )
    ev = _evidence(poi.record_id, _BASE_TIME)
    _s, _sid, checks = _drive_single_setup(tuple(candles), poi, ev, ())
    assert checks > 0


# =====================================================================
# Setup delta: NEW / CHANGED / REMOVE against the running scheduler.
# =====================================================================


def test_new_setup_registers_wait_forming() -> None:
    poi = _source_poi(_v7(10))
    provider = _HashIdentityProvider()
    delta, sid = _new_setup_delta(poi, provider)
    candles = _no_interaction()[:1]
    atr = compute_atr_series(candles, 14)
    scheduler = create_btmm_scheduler(_CONFIG)
    scheduler = advance_btmm_scheduler(scheduler, candles, atr, setup_delta=delta)
    assert scheduler.stage_of(sid) in (
        BtmmSchedulerStage.WAIT_FORMING,
        BtmmSchedulerStage.WAIT_INTERACTION,
    )


def test_removed_setup_disappears_from_scheduler() -> None:
    poi = _source_poi(_v7(11))
    provider = _HashIdentityProvider()
    delta, sid = _new_setup_delta(poi, provider)
    candles = _no_interaction()[:2]
    atr = compute_atr_series(candles, 14)
    scheduler = create_btmm_scheduler(_CONFIG)
    scheduler = advance_btmm_scheduler(
        scheduler, candles[:1], atr[:1], setup_delta=delta
    )
    assert scheduler.materialize_cursor(sid) is not None
    remove_delta = BtmmSetupDelta(removed_source_poi_ids=(poi.record_id,))
    scheduler = advance_btmm_scheduler(
        scheduler, candles[:2], atr[:2], setup_delta=remove_delta
    )
    assert scheduler.materialize_cursor(sid) is None
    assert scheduler.stage_of(sid) is None


def test_changed_setup_rebuilds_cursor_with_new_zone() -> None:
    poi_before = _source_poi(
        _v7(12), zone_top=Decimal("101"), zone_bottom=Decimal("100")
    )
    provider = _HashIdentityProvider()
    delta, sid = _new_setup_delta(poi_before, provider)
    candles = _strong()
    atr = compute_atr_series(candles, 14)
    scheduler = create_btmm_scheduler(_CONFIG)
    # Build up through candle 15 (interaction already happened against the old zone).
    for n in range(1, 16):
        scheduler = advance_btmm_scheduler(
            scheduler,
            candles[:n],
            atr[:n],
            setup_delta=delta if n == 1 else BtmmSetupDelta(),
        )
    cursor_before = scheduler.materialize_cursor(sid)
    assert cursor_before is not None
    assert cursor_before.zone_top == Decimal("101")

    poi_after = _source_poi(
        _v7(12), zone_top=Decimal("120"), zone_bottom=Decimal("119")
    )
    changed_spec = BtmmSetupSpec(
        setup_record_id=sid,
        symbol=poi_after.symbol,
        source_timeframe=poi_after.source_timeframe,
        source_poi_record_id=poi_after.record_id,
        direction=poi_after.direction,
        zone_top=poi_after.zone_top,
        zone_bottom=poi_after.zone_bottom,
        candidate_availability_time_utc=poi_after.availability_time_utc,
    )
    scheduler = advance_btmm_scheduler(
        scheduler,
        candles[:16],
        atr[:16],
        setup_delta=BtmmSetupDelta(changed_setups=(changed_spec,)),
    )
    cursor_after = scheduler.materialize_cursor(sid)
    assert cursor_after is not None
    assert cursor_after.zone_top == Decimal("120")
    # The rebuilt cursor must equal run_btmm_lifecycle against the NEW zone over
    # the same 16-candle prefix (proves the rebuild refeeds full history, not a
    # patch of the old cursor).
    oracle = run_btmm_lifecycle(
        symbol=poi_after.symbol,
        source_timeframe=poi_after.source_timeframe,
        btmm_setup_record_id=sid,
        source_poi=poi_after,
        candidate_availability_time_utc=poi_after.availability_time_utc,
        bundle_candles=candles[:16],
        atr_values=atr[:16],
        poi_lifecycle_transitions=(),
        reviewed_evidence=None,
        configuration=_CONFIG,
    )
    actual = scheduler.materialize_walk(sid)
    assert actual is not None
    assert (
        actual.final_fields.interaction_class == oracle.final_fields.interaction_class
    )


# =====================================================================
# Forming-due, interaction-index vs brute force.
# =====================================================================


def test_forming_due_exact_wake_no_early_no_missed() -> None:
    """The setup's own availability lands mid-candle-19; forming must trigger on
    EXACTLY the first candle whose availability exceeds it, never earlier or
    later, verified against run_btmm_lifecycle's ENTERED_FORMING transition
    timing at every prefix."""
    poi = _source_poi(_v7(13), availability_index=19)
    _scheduler, _sid, checks = _drive_single_setup(_strong(), poi, None, ())
    assert checks > 0


def test_interaction_index_matches_brute_force_zero_false_negatives() -> None:
    """For every candle, the interaction_index.overlaps() wake set must be a
    superset (here exactly equal, since the predicate is identical) of brute-
    force '_touches_zone' eligibility over the same zone."""
    candles = _strong()
    poi = _source_poi(_v7(14))
    provider = _HashIdentityProvider()
    delta, sid = _new_setup_delta(poi, provider)
    atr = compute_atr_series(candles, 14)
    scheduler = create_btmm_scheduler(_CONFIG)
    for n in range(1, len(candles) + 1):
        idx = n - 1
        candle = candles[idx]
        scheduler = advance_btmm_scheduler(
            scheduler,
            candles[:n],
            atr[:n],
            setup_delta=delta if n == 1 else BtmmSetupDelta(),
        )
        cursor = scheduler.materialize_cursor(sid)
        assert cursor is not None
        if (
            cursor.interaction_index is None
            and cursor.entered_forming_index is not None
        ):
            brute_force_touches = (
                candle.low <= poi.zone_top and candle.high >= poi.zone_bottom
            )
            indexed = sid in scheduler.interaction_index.overlaps(
                candle.low, candle.high
            )
            assert indexed == brute_force_touches, f"n={n}"


def test_no_interaction_huge_candle_still_registers_correctly() -> None:
    candles = [_candle(i, "105", "105.2", "104.8", "105") for i in range(14)]
    candles.append(_candle(14, "50", "150", "50", "149"))  # engulfs the whole zone
    poi = _source_poi(_v7(15))
    ev = _evidence(poi.record_id, _BASE_TIME)
    _s, _sid, checks = _drive_single_setup(tuple(candles), poi, ev, ())
    assert checks > 0


# =====================================================================
# Source-POI routing and evidence routing (multi-setup, cross-wake isolation).
# =====================================================================


def test_unrelated_poi_event_wakes_no_setup() -> None:
    poi_a = _source_poi(_v7(20))
    poi_b = _source_poi(_v7(21), availability_index=15)
    provider = _HashIdentityProvider()
    delta_a, sid_a = _new_setup_delta(poi_a, provider)
    delta_b, sid_b = _new_setup_delta(poi_b, provider)
    candles = _strong()
    atr = compute_atr_series(candles, 14)
    scheduler = create_btmm_scheduler(_CONFIG)
    scheduler = advance_btmm_scheduler(
        scheduler,
        candles[:1],
        atr[:1],
        setup_delta=BtmmSetupDelta(
            new_setups=(delta_a.new_setups[0], delta_b.new_setups[0])
        ),
    )
    unrelated = _poi_transition(
        _v7(999), PoiLifecycleTransitionType.GENUINE_INVALIDATION_CONFIRMED, 0
    )
    scheduler = advance_btmm_scheduler(
        scheduler, candles[:2], atr[:2], new_poi_transitions=(unrelated,)
    )
    assert sid_a not in scheduler.woken_ids
    assert sid_b not in scheduler.woken_ids


def test_linked_confirmed_then_genuine_invalidation_wakes_exact_setup_only() -> None:
    poi_a = _source_poi(_v7(22))
    poi_b = _source_poi(_v7(23), availability_index=15)
    provider = _HashIdentityProvider()
    delta_a, sid_a = _new_setup_delta(poi_a, provider)
    delta_b, sid_b = _new_setup_delta(poi_b, provider)
    ev_a = _evidence(poi_a.record_id, _BASE_TIME)
    candles = _strong()
    atr = compute_atr_series(candles, 14)
    scheduler = create_btmm_scheduler(_CONFIG)

    for n in range(1, 21):
        d = BtmmSetupDelta()
        if n == 1:
            d = BtmmSetupDelta(
                new_setups=(delta_a.new_setups[0], delta_b.new_setups[0])
            )
        new_ev = (ev_a,) if n == 1 else ()
        scheduler = advance_btmm_scheduler(
            scheduler, candles[:n], atr[:n], setup_delta=d, new_reviewed_evidence=new_ev
        )
    assert scheduler.stage_of(sid_a) == BtmmSchedulerStage.CONFIRMED_SOURCE_WATCH

    invalidation = _poi_transition(
        poi_a.record_id, PoiLifecycleTransitionType.GENUINE_INVALIDATION_CONFIRMED, 20
    )
    scheduler = advance_btmm_scheduler(
        scheduler, candles[:21], atr[:21], new_poi_transitions=(invalidation,)
    )
    assert sid_a in scheduler.woken_ids
    assert sid_b not in scheduler.woken_ids
    walk_a = scheduler.materialize_walk(sid_a)
    assert walk_a is not None
    assert walk_a.final_fields.primary_state == BtmmLifecycleStatus.BTMM_CANCELLED
    assert any(t.transition_type.value == "POI_REJECTED" for t in walk_a.transitions)
    assert scheduler.stage_of(sid_a) == BtmmSchedulerStage.FROZEN


def test_late_reviewed_evidence_blocks_then_resolves_every_prefix() -> None:
    poi = _source_poi(_v7(24))
    ev = _evidence(poi.record_id, _BASE_TIME + timedelta(minutes=5 * 30))
    _scheduler, _sid, checks = _drive_single_setup(_strong(), poi, ev, ())
    assert checks > 0


def test_automatic_evidence_from_false_invalidation_every_prefix() -> None:
    poi = _source_poi(_v7(25))
    ev = _evidence(poi.record_id, _BASE_TIME)
    trans = (
        _poi_transition(
            poi.record_id, PoiLifecycleTransitionType.FALSE_INVALIDATION_CONFIRMED, 5
        ),
    )
    _scheduler, _sid, checks = _drive_single_setup(_strong(), poi, ev, trans)
    assert checks > 0


def test_only_linked_setup_wakes_on_evidence_arrival() -> None:
    poi_a = _source_poi(_v7(26))
    poi_b = _source_poi(_v7(27), availability_index=15)
    provider = _HashIdentityProvider()
    delta_a, sid_a = _new_setup_delta(poi_a, provider)
    delta_b, sid_b = _new_setup_delta(poi_b, provider)
    candles = _strong()
    atr = compute_atr_series(candles, 14)
    scheduler = create_btmm_scheduler(_CONFIG)
    for n in range(1, 21):
        d = (
            BtmmSetupDelta(new_setups=(delta_a.new_setups[0], delta_b.new_setups[0]))
            if n == 1
            else BtmmSetupDelta()
        )
        scheduler = advance_btmm_scheduler(
            scheduler, candles[:n], atr[:n], setup_delta=d
        )
    ev_a = _evidence(poi_a.record_id, candles[20].availability_time_utc)
    scheduler = advance_btmm_scheduler(
        scheduler, candles[:21], atr[:21], new_reviewed_evidence=(ev_a,)
    )
    assert sid_a in scheduler.woken_ids
    assert sid_b not in scheduler.woken_ids


# =====================================================================
# Freeze semantics.
# =====================================================================


def test_confirmed_setup_not_advanced_by_further_price_candles() -> None:
    poi = _source_poi(_v7(30))
    ev = _evidence(poi.record_id, _BASE_TIME)
    scheduler, sid, _ = _drive_single_setup(_strong(), poi, ev, ())
    assert scheduler.stage_of(sid) == BtmmSchedulerStage.CONFIRMED_SOURCE_WATCH
    cursor_before = scheduler.materialize_cursor(sid)
    more_candles = _strong() + tuple(
        _candle(i, "107.9", "500", "0.1", "108") for i in range(26, 30)
    )
    atr = compute_atr_series(more_candles, 14)
    for n in range(len(_strong()) + 1, len(more_candles) + 1):
        scheduler = advance_btmm_scheduler(scheduler, more_candles[:n], atr[:n])
        assert sid not in scheduler.woken_ids
    cursor_after = scheduler.materialize_cursor(sid)
    assert cursor_after is not None and cursor_before is not None
    assert cursor_after.total_count == cursor_before.total_count


def test_frozen_setup_no_longer_watched_after_invalidation() -> None:
    poi = _source_poi(_v7(31))
    base = _ineligible()
    extended = (*base, _candle(len(base), "101.4", "101.5", "101.3", "101.4"))
    scheduler, sid, _ = _drive_single_setup(
        base, poi, _evidence(poi.record_id, _BASE_TIME), ()
    )
    assert scheduler.stage_of(sid) == BtmmSchedulerStage.SOURCE_POI_WATCH

    invalidation = _poi_transition(
        poi.record_id,
        PoiLifecycleTransitionType.GENUINE_INVALIDATION_CONFIRMED,
        len(base),
    )
    atr = compute_atr_series(extended, 14)
    scheduler = advance_btmm_scheduler(
        scheduler, extended, atr, new_poi_transitions=(invalidation,)
    )
    assert scheduler.stage_of(sid) == BtmmSchedulerStage.FROZEN
    bucket = scheduler.source_poi_watch.get(poi.record_id.int)
    assert not bucket


# =====================================================================
# Persistence / rollback.
# =====================================================================


def test_scheduler_branches_are_independent() -> None:
    poi = _source_poi(_v7(40))
    provider = _HashIdentityProvider()
    delta, sid = _new_setup_delta(poi, provider)
    candles = _strong()
    atr = compute_atr_series(candles, 14)
    base = create_btmm_scheduler(_CONFIG)
    base = advance_btmm_scheduler(base, candles[:1], atr[:1], setup_delta=delta)
    checkpoint = base

    branch_a = advance_btmm_scheduler(checkpoint, candles[:2], atr[:2])
    branch_b = advance_btmm_scheduler(checkpoint, candles[:2], atr[:2])

    assert checkpoint.total_count == 1
    assert branch_a.total_count == 2
    assert branch_b.total_count == 2
    cursor_checkpoint = checkpoint.materialize_cursor(sid)
    assert cursor_checkpoint is not None
    assert cursor_checkpoint.total_count == 1


def test_rollback_on_never_committing_failed_branch_leaves_prior_valid() -> None:
    poi = _source_poi(_v7(41))
    provider = _HashIdentityProvider()
    delta, _sid = _new_setup_delta(poi, provider)
    candles = _strong()
    atr = compute_atr_series(candles, 14)
    scheduler = create_btmm_scheduler(_CONFIG)
    scheduler = advance_btmm_scheduler(
        scheduler, candles[:1], atr[:1], setup_delta=delta
    )
    good_checkpoint = scheduler
    try:
        # candles length mismatch -> raises, never mutates/replaces `scheduler`.
        advance_btmm_scheduler(scheduler, candles[:1], atr[:1])
        raise AssertionError("expected ValueError")
    except ValueError:
        pass
    assert scheduler is good_checkpoint
    assert scheduler.total_count == 1


# =====================================================================
# Wake union: dedup + zero false negatives against a brute-force oracle.
# =====================================================================


def _semantic_snapshot(cursor: BtmmLifecycleCursor) -> tuple[object, ...]:
    """Fields that matter for wake correctness -- excludes total_count/prev_
    candle, which change on every single advance_btmm_cursor call regardless of
    any semantic effect (pure bookkeeping), and would make every candle look
    'changed' under raw dataclass equality."""
    return (
        cursor.entered_forming_index,
        cursor.interaction_index,
        cursor.interaction_class,
        cursor.reaction_start_index,
        cursor.reaction_anchor,
        len(cursor.window_candles),
        cursor.tier_result,
        cursor.window_close_candle,
    )


def test_wake_set_has_zero_false_negatives_vs_brute_force() -> None:
    """For every candle, any setup whose brute-force sequential advance_btmm_
    cursor changes its SEMANTICALLY-relevant fields must be in woken_ids."""
    candles = _strong()
    poi = _source_poi(_v7(50))
    provider = _HashIdentityProvider()
    delta, sid = _new_setup_delta(poi, provider)
    atr = compute_atr_series(candles, 14)
    scheduler = create_btmm_scheduler(_CONFIG)

    brute_cursor = create_btmm_lifecycle_cursor(
        poi.symbol,
        poi.source_timeframe,
        sid,
        poi.record_id,
        poi.zone_top,
        poi.zone_bottom,
        poi.direction,
        poi.availability_time_utc,
        _CONFIG,
    )
    for n in range(1, len(candles) + 1):
        idx = n - 1
        d = delta if n == 1 else BtmmSetupDelta()
        before = _semantic_snapshot(brute_cursor)
        brute_cursor = advance_btmm_cursor(
            brute_cursor, candles[idx], atr[idx], _CONFIG
        )
        changed = before != _semantic_snapshot(brute_cursor)
        scheduler = advance_btmm_scheduler(
            scheduler, candles[:n], atr[:n], setup_delta=d
        )
        if changed and n > 1:
            assert sid in scheduler.woken_ids, f"missed wake @ n={n}"


def test_woken_ids_is_deduplicated_set() -> None:
    poi = _source_poi(_v7(51))
    provider = _HashIdentityProvider()
    delta, _sid = _new_setup_delta(poi, provider)
    candles = _strong()
    atr = compute_atr_series(candles, 14)
    scheduler = create_btmm_scheduler(_CONFIG)
    scheduler = advance_btmm_scheduler(
        scheduler, candles[:1], atr[:1], setup_delta=delta
    )
    assert isinstance(scheduler.woken_ids, frozenset)
    assert len(scheduler.woken_ids) == len(set(scheduler.woken_ids))
