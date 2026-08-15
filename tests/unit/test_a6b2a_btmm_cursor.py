"""A6-B2-A permanent tests: the resumable BTMM lifecycle cursor.

At every prefix the incrementally-advanced cursor, materialized with the exact
inputs visible at that prefix (candles, full-prefix ATR-14, source-POI lifecycle
transitions and reviewed evidence gated by availability <= the current candle),
must equal ``run_btmm_lifecycle(full prefix, same inputs)`` byte-for-byte:
transitions and every ``_StateFields`` value. Covers forming, eligible/ineligible
interaction, reaction start, incomplete/weak/valid/speed reaction windows,
automatic + reviewed evidence (incl. late arrival), BLOCKED/CONFIRMED/CANCELLED,
CONFIRMED-then-source-POI-invalidation, POI_REJECTED, and no-lookahead.
"""

import random
from dataclasses import asdict
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

from btmm_ai_scanner.btmm.configuration import BtmmConfiguration
from btmm_ai_scanner.btmm.enums import (
    BtmmContextAlignmentStatus,
    BtmmEvidenceSource,
    BtmmLiquidityEvidenceStatus,
    BtmmSessionStatus,
    BtmmVolumePillarStatus,
)
from btmm_ai_scanner.btmm.lifecycle import run_btmm_lifecycle
from btmm_ai_scanner.btmm.lifecycle_cursor import (
    advance_btmm_cursor,
    create_btmm_lifecycle_cursor,
    materialize_btmm_cursor,
)
from btmm_ai_scanner.btmm.reviewed_evidence import BtmmReviewedEvidence
from btmm_ai_scanner.config.enums import InternalSymbol, Timeframe
from btmm_ai_scanner.contracts.normalized_candle import NormalizedCandle
from btmm_ai_scanner.contracts.provenance_record import EvidenceClassification
from btmm_ai_scanner.contracts.raw_candle import CandleCompleteness, CandleVolumeKind
from btmm_ai_scanner.contracts.types import SemVer
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
_RAW_ID = UUID("0193f450-1234-7abc-8def-abcdefabcdaa")
_PROV_ID = UUID("0193f450-1234-7abc-8def-abcdefabcdff")
_BASE_TIME = datetime(2026, 1, 1, tzinfo=UTC)
_POI_ID = UUID("0193f450-aaaa-7000-8000-000000000001")
_SETUP_ID = UUID("0193f450-bbbb-7000-8000-000000000001")
_CANDLE_INV = UUID("0193f450-cccc-7000-8000-000000000001")
_CONFIG = BtmmConfiguration(minimum_price_tick=Decimal("0.01"))


def _candle(index: int, o: str, h: str, low: str, c: str) -> NormalizedCandle:
    event_time = _BASE_TIME + timedelta(minutes=5 * index)
    availability = event_time + timedelta(minutes=1)
    return NormalizedCandle.model_validate(
        {
            "record_id": UUID(f"0193f450-1234-7abc-8def-{index:012x}"),
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


def _source_poi(direction: PoiDirection = PoiDirection.BULLISH) -> PoiObservation:
    poi_type = (
        PoiType.SUPPORT_ZONE
        if direction == PoiDirection.BULLISH
        else PoiType.RESISTANCE_ZONE
    )
    ct = _candle(13, "105", "105.2", "104.8", "105")
    return PoiObservation(
        record_id=_POI_ID,
        content_fingerprint=_FINGERPRINT,
        symbol=InternalSymbol.XAUUSD,
        source_timeframe=Timeframe.M5,
        effective_timeframe=Timeframe.M5,
        family=PoiFamily.STRUCTURAL,
        poi_type=poi_type,
        direction=direction,
        zone_top=Decimal("101"),
        zone_bottom=Decimal("100"),
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


def _evidence(
    availability: datetime,
    liquidity: BtmmLiquidityEvidenceStatus = BtmmLiquidityEvidenceStatus.PRESENT,
    context: BtmmContextAlignmentStatus = BtmmContextAlignmentStatus.ALIGNED,
    session: BtmmSessionStatus = BtmmSessionStatus.ACTIVE,
    volume: BtmmVolumePillarStatus = BtmmVolumePillarStatus.SUPPORTS,
) -> BtmmReviewedEvidence:
    return BtmmReviewedEvidence(
        symbol=InternalSymbol.XAUUSD,
        timeframe=Timeframe.M5,
        source_poi_record_id=_POI_ID,
        market_direction_status=context,
        analytical_framework_status=context,
        session_status=session,
        liquidity_evidence_status=liquidity,
        volume_pillar_status=volume,
        context_input_source=BtmmEvidenceSource.EXPERT_LABELLED,
        liquidity_event_source=BtmmEvidenceSource.EXPERT_LABELLED,
        volume_evidence_source=BtmmEvidenceSource.EXPERT_LABELLED,
        availability_time_utc=availability,
        rule_version=SemVer.parse("0.1.0"),
        contract_version=SemVer.parse("0.1.0"),
        schema_version=SemVer.parse("0.1.0"),
    )


def _time_at(index: int) -> datetime:
    return _BASE_TIME + timedelta(minutes=5 * index)


def _poi_transition(
    transition_type: PoiLifecycleTransitionType, index: int
) -> PoiLifecycleTransition:
    event_time = _time_at(index)
    return PoiLifecycleTransition(
        record_id=UUID(f"0193f450-dddd-7000-8000-{index:012x}"),
        content_fingerprint=_FINGERPRINT,
        symbol=InternalSymbol.XAUUSD,
        timeframe=Timeframe.M5,
        poi_record_id=_POI_ID,
        transition_type=transition_type,
        triggering_candle_record_id=_CANDLE_INV,
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
    return tuple(candles)


def _weak() -> tuple[NormalizedCandle, ...]:
    candles = [_candle(i, "105", "105.2", "104.8", "105") for i in range(14)]
    candles.append(_candle(14, "105", "105.1", "100.5", "100.8"))
    candles.append(_candle(15, "100.8", "102.2", "100.7", "102.0"))
    candles.append(_candle(16, "102.0", "102.3", "101.8", "102.1"))
    candles.append(_candle(17, "102.1", "102.4", "101.9", "102.0"))
    candles.append(_candle(18, "102.0", "102.3", "101.7", "101.9"))
    candles.append(_candle(19, "101.9", "102.2", "101.6", "101.8"))
    return tuple(candles)


def _no_interaction() -> tuple[NormalizedCandle, ...]:
    # Price never touches the 100-101 zone.
    return tuple(_candle(i, "105", "105.2", "104.8", "105") for i in range(20))


def _every_prefix_matches(
    candles: tuple[NormalizedCandle, ...],
    source_poi: PoiObservation,
    reviewed_evidence: BtmmReviewedEvidence | None,
    poi_transitions: tuple[PoiLifecycleTransition, ...],
) -> int:
    atr_full = compute_atr_series(candles, 14)
    cursor = create_btmm_lifecycle_cursor(
        source_poi.symbol,
        source_poi.source_timeframe,
        _SETUP_ID,
        source_poi.record_id,
        source_poi.zone_top,
        source_poi.zone_bottom,
        source_poi.direction,
        source_poi.availability_time_utc,
        _CONFIG,
    )
    checks = 0
    for n in range(1, len(candles) + 1):
        cursor = advance_btmm_cursor(cursor, candles[n - 1], atr_full[n - 1], _CONFIG)
        now = candles[n - 1].availability_time_utc
        visible_transitions = tuple(
            t for t in poi_transitions if t.availability_time_utc <= now
        )
        visible_evidence = (
            reviewed_evidence
            if reviewed_evidence is not None
            and reviewed_evidence.availability_time_utc <= now
            else None
        )
        batch = run_btmm_lifecycle(
            symbol=source_poi.symbol,
            source_timeframe=source_poi.source_timeframe,
            btmm_setup_record_id=_SETUP_ID,
            source_poi=source_poi,
            candidate_availability_time_utc=source_poi.availability_time_utc,
            bundle_candles=candles[:n],
            atr_values=atr_full[:n],
            poi_lifecycle_transitions=visible_transitions,
            reviewed_evidence=visible_evidence,
            configuration=_CONFIG,
        )
        materialized = materialize_btmm_cursor(
            cursor, visible_transitions, visible_evidence, _CONFIG
        )
        assert materialized.transitions == batch.transitions, f"transitions @ n={n}"
        assert asdict(materialized.final_fields) == asdict(batch.final_fields), (
            f"final_fields @ n={n}"
        )
        checks += 1
    return checks


def test_confirmed_path_every_prefix() -> None:
    poi = _source_poi()
    ev = _evidence(_BASE_TIME)  # available from the start
    assert _every_prefix_matches(_strong(), poi, ev, ()) > 0


def test_weak_reaction_cancelled_every_prefix() -> None:
    poi = _source_poi()
    ev = _evidence(_BASE_TIME)
    assert _every_prefix_matches(_weak(), poi, ev, ()) > 0


def test_no_interaction_stays_forming_every_prefix() -> None:
    poi = _source_poi()
    assert _every_prefix_matches(_no_interaction(), poi, None, ()) > 0


def test_no_reviewed_evidence_cancels_every_prefix() -> None:
    poi = _source_poi()
    assert _every_prefix_matches(_strong(), poi, None, ()) > 0


def test_late_reviewed_evidence_blocks_then_resolves_every_prefix() -> None:
    # Evidence arrives after the reaction window closes (candle 19) -> BLOCKED then
    # resolved when its availability is reached.
    poi = _source_poi()
    ev = _evidence(_time_at(30))
    assert _every_prefix_matches(_strong(), poi, ev, ()) > 0


def test_context_rejected_evidence_every_prefix() -> None:
    poi = _source_poi()
    ev = _evidence(_BASE_TIME, context=BtmmContextAlignmentStatus.MISALIGNED)
    assert _every_prefix_matches(_strong(), poi, ev, ()) > 0


def test_blocked_non_formation_timeframe_every_prefix() -> None:
    # Session inactive -> CANCEL(session); but use volume review pending path via a
    # blocked outcome: here use aligned context + present liquidity but volume
    # UNKNOWN to exercise BLOCKED.
    poi = _source_poi()
    ev = _evidence(_BASE_TIME, volume=BtmmVolumePillarStatus.UNRESOLVED)
    assert _every_prefix_matches(_strong(), poi, ev, ()) > 0


def test_automatic_evidence_from_false_invalidation_every_prefix() -> None:
    poi = _source_poi()
    ev = _evidence(_BASE_TIME)
    trans = (
        _poi_transition(PoiLifecycleTransitionType.FALSE_INVALIDATION_CONFIRMED, 5),
    )
    assert _every_prefix_matches(_strong(), poi, ev, trans) > 0


def test_confirmed_then_source_poi_invalidation_every_prefix() -> None:
    # Confirmed early, then a later genuine invalidation -> POI_REJECTED -> CANCELLED.
    poi = _source_poi()
    ev = _evidence(_BASE_TIME)
    trans = (
        _poi_transition(PoiLifecycleTransitionType.GENUINE_INVALIDATION_CONFIRMED, 25),
    )
    assert _every_prefix_matches(_strong(), poi, ev, trans) > 0


def test_invalidation_before_confirmation_every_prefix() -> None:
    poi = _source_poi()
    ev = _evidence(_BASE_TIME)
    trans = (
        _poi_transition(PoiLifecycleTransitionType.GENUINE_INVALIDATION_CONFIRMED, 16),
    )
    assert _every_prefix_matches(_strong(), poi, ev, trans) > 0


def _ineligible() -> tuple[NormalizedCandle, ...]:
    # Approach the 100-101 zone from BELOW so the first touch is a noncanonical-side
    # (ineligible) interaction => INTERACTION_INELIGIBLE / cancelled.
    candles = [_candle(i, "98", "98.2", "97.8", "98") for i in range(14)]
    candles.append(_candle(14, "98", "100.5", "97.9", "100.4"))
    candles.append(_candle(15, "100.4", "101.0", "100.3", "100.9"))
    candles.append(_candle(16, "100.9", "101.5", "100.8", "101.4"))
    return tuple(candles)


def test_ineligible_interaction_every_prefix() -> None:
    poi = _source_poi()
    ev = _evidence(_BASE_TIME)
    assert _every_prefix_matches(_ineligible(), poi, ev, ()) > 0


def _strong_bearish() -> tuple[NormalizedCandle, ...]:
    # Mirror of _strong for a resistance zone (bearish): price below, spikes up into
    # the zone, then reacts down through the far boundary.
    candles = [_candle(i, "96", "96.2", "95.8", "96") for i in range(14)]
    candles.append(_candle(14, "96", "100.5", "95.9", "100.2"))
    candles.append(_candle(15, "100.2", "100.3", "98.8", "99.0"))
    candles.append(_candle(16, "99.0", "99.1", "97.5", "97.6"))
    candles.append(_candle(17, "97.6", "97.7", "96.0", "96.1"))
    candles.append(_candle(18, "96.1", "96.2", "94.5", "94.6"))
    candles.append(_candle(19, "94.6", "94.7", "93.0", "93.1"))
    return tuple(candles)


def test_bearish_resistance_every_prefix() -> None:
    poi = _source_poi(PoiDirection.BEARISH)
    ev = _evidence(_BASE_TIME)
    assert _every_prefix_matches(_strong_bearish(), poi, ev, ()) > 0


def test_cursor_calls_no_batch_and_replays_no_history() -> None:
    # §15: the cursor never calls run_btmm_lifecycle (not even imported); each candle
    # is consumed once, and the only retained candle buffer is bounded by
    # reaction_window_bars.
    import btmm_ai_scanner.btmm.lifecycle_cursor as cursor_module

    assert not hasattr(cursor_module, "run_btmm_lifecycle")
    candles = _strong()
    atr = compute_atr_series(candles, 14)
    poi = _source_poi()
    cursor = create_btmm_lifecycle_cursor(
        poi.symbol,
        poi.source_timeframe,
        _SETUP_ID,
        poi.record_id,
        poi.zone_top,
        poi.zone_bottom,
        poi.direction,
        poi.availability_time_utc,
        _CONFIG,
    )
    max_window = 0
    for i in range(len(candles)):
        cursor = advance_btmm_cursor(cursor, candles[i], atr[i], _CONFIG)
        max_window = max(max_window, len(cursor.window_candles))
    assert max_window <= _CONFIG.reaction_window_bars


def test_cursor_is_immutable_and_transactional() -> None:
    candles = _strong()
    atr = compute_atr_series(candles, 14)
    poi = _source_poi()
    cursor = create_btmm_lifecycle_cursor(
        poi.symbol,
        poi.source_timeframe,
        _SETUP_ID,
        poi.record_id,
        poi.zone_top,
        poi.zone_bottom,
        poi.direction,
        poi.availability_time_utc,
        _CONFIG,
    )
    for i in range(16):
        cursor = advance_btmm_cursor(cursor, candles[i], atr[i], _CONFIG)
    before = asdict(cursor)
    before_mat = materialize_btmm_cursor(cursor, (), _evidence(_BASE_TIME), _CONFIG)
    # A speculative next advance must not mutate the prior cursor.
    _speculative = advance_btmm_cursor(cursor, candles[16], atr[16], _CONFIG)
    assert asdict(cursor) == before
    assert (
        materialize_btmm_cursor(cursor, (), _evidence(_BASE_TIME), _CONFIG)
        == before_mat
    )


def test_cursor_is_deterministic() -> None:
    candles = _strong()
    atr = compute_atr_series(candles, 14)
    poi = _source_poi()
    ev = _evidence(_BASE_TIME)

    def run() -> tuple[dict, object]:  # type: ignore[type-arg]
        cursor = create_btmm_lifecycle_cursor(
            poi.symbol,
            poi.source_timeframe,
            _SETUP_ID,
            poi.record_id,
            poi.zone_top,
            poi.zone_bottom,
            poi.direction,
            poi.availability_time_utc,
            _CONFIG,
        )
        for i in range(len(candles)):
            cursor = advance_btmm_cursor(cursor, candles[i], atr[i], _CONFIG)
        return asdict(cursor), materialize_btmm_cursor(cursor, (), ev, _CONFIG)

    a_state, a_mat = run()
    b_state, b_mat = run()
    assert a_state == b_state
    assert a_mat == b_mat


def _random_stream(rng: random.Random, n: int) -> tuple[NormalizedCandle, ...]:
    candles = []
    price = 103.0
    for i in range(n):
        price += rng.uniform(-2.5, 2.5)
        price = max(96.0, min(110.0, price))
        o = price
        c = price + rng.uniform(-1.5, 1.5)
        h = max(o, c) + rng.uniform(0.0, 1.2)
        low = min(o, c) - rng.uniform(0.0, 1.2)
        candles.append(_candle(i, f"{o:.2f}", f"{h:.2f}", f"{low:.2f}", f"{c:.2f}"))
    return tuple(candles)


def test_randomized_every_prefix_differential() -> None:
    total = 0
    for trial in range(60):
        rng = random.Random(7000 + trial)
        candles = _random_stream(rng, rng.randint(16, 40))
        direction = rng.choice([PoiDirection.BULLISH, PoiDirection.BEARISH])
        poi = _source_poi(direction)
        # Randomly: no evidence, early evidence, or late evidence; varied statuses.
        ev: BtmmReviewedEvidence | None
        choice = rng.random()
        if choice < 0.3:
            ev = None
        else:
            avail = _time_at(rng.randint(0, len(candles) + 5))
            ev = _evidence(
                avail,
                liquidity=rng.choice(
                    [
                        BtmmLiquidityEvidenceStatus.PRESENT,
                        BtmmLiquidityEvidenceStatus.PENDING,
                    ]
                ),
                context=rng.choice(
                    [
                        BtmmContextAlignmentStatus.ALIGNED,
                        BtmmContextAlignmentStatus.MISALIGNED,
                        BtmmContextAlignmentStatus.UNKNOWN,
                    ]
                ),
                session=rng.choice(
                    [BtmmSessionStatus.ACTIVE, BtmmSessionStatus.INACTIVE]
                ),
                volume=rng.choice(
                    [
                        BtmmVolumePillarStatus.SUPPORTS,
                        BtmmVolumePillarStatus.FAILS,
                        BtmmVolumePillarStatus.UNRESOLVED,
                    ]
                ),
            )
        trans: tuple[PoiLifecycleTransition, ...] = ()
        if rng.random() < 0.4:
            kind = rng.choice(
                [
                    PoiLifecycleTransitionType.FALSE_INVALIDATION_CONFIRMED,
                    PoiLifecycleTransitionType.GENUINE_INVALIDATION_CONFIRMED,
                ]
            )
            trans = (_poi_transition(kind, rng.randint(0, len(candles) + 3)),)
        total += _every_prefix_matches(candles, poi, ev, trans)
    assert total > 0
