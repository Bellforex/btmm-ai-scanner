"""Offline blind replay of P4 BTMM over the frozen atomic context.

Test/parity tooling only -- nothing in `src/` imports this, and it changes no
production semantics.

BLIND means the replay never sees a target. It takes only the frozen context
CSV, drives the authoritative pipeline, and reports what it computed. Comparison
happens afterwards, in the caller. No expected hash is an input to any
computation here, so a "match" cannot be manufactured.

NOTHING IS REIMPLEMENTED, AND THE ORACLE IS PRODUCTION
-------------------------------------------------------
The upstream half reuses the already-verified P3 replay: candles from the P2
loader, ATR from production's `compute_atr_series`, detection from the Pine
frontier transcription, lifecycle from the committed-boundary cursor. That half
is what P3 closure proved against real data.

The P4 half is not a model at all -- it calls production `analyze_btmm`
directly, with `reviewed_evidence=()`. The Pine-shaped model in
`p4_btmm_model.py` is proven equal to that oracle at every prefix elsewhere; it
is deliberately NOT used here, so the real-data claim is Pine against
production rather than Pine against my transcription of it.

Bridging the two needs `PoiObservation` records, which the P3 replay does not
build (it works in the Pine registry shape). They are constructed here from the
registry, with content-addressed UUIDs derived from the P3 identity triple, so
the mapping is deterministic and carries no information the digest depends on --
`analyze_btmm` reads only the POI's type, timeframe, direction, zone bounds and
times, all of which come straight from the registry record.

Only the two BTMM-consumed transition kinds are forwarded. That is not a
simplification: `find_automatic_liquidity_evidence` and the genuine-invalidation
truncation are the only two things `analyze_btmm` reads from the POI transition
stream (`liquidity.py:16-29`, `lifecycle_cursor.py:630-640`).
"""

from __future__ import annotations

import csv
import hashlib
import importlib.util
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from types import ModuleType
from typing import Any
from uuid import UUID

from btmm_ai_scanner.btmm.analyzer import BtmmTimeframeInput, analyze_btmm
from btmm_ai_scanner.btmm.configuration import BtmmConfiguration
from btmm_ai_scanner.config.enums import InternalSymbol, Timeframe
from btmm_ai_scanner.contracts.normalized_candle import NormalizedCandle
from btmm_ai_scanner.contracts.provenance_record import EvidenceClassification
from btmm_ai_scanner.contracts.types import SemVer
from btmm_ai_scanner.domain import MarketMeasurementAnalysis
from btmm_ai_scanner.domain.enums import DerivedOutputType
from btmm_ai_scanner.measurements.atr import compute_atr_series
from btmm_ai_scanner.poi.analyzer import PoiAnalysis
from btmm_ai_scanner.poi.configuration import PoiConfiguration
from btmm_ai_scanner.poi.enums import (
    PoiDirection,
    PoiFamily,
    PoiLifecycleTransitionType,
    PoiType,
)
from btmm_ai_scanner.poi.lifecycle import PoiLifecycleTransition
from btmm_ai_scanner.poi.observation import PoiObservation

_HERE = Path(__file__).parent


def _load(name: str, filename: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, _HERE / filename)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


M = _load("_p4replay_detectors", "p3_pine_model.py")
L = _load("_p4replay_lifecycle", "p3_lifecycle_model.py")
P3R = _load("_p4replay_p3", "p3_atomic_state_replay.py")
G4 = _load("_p4replay_digest", "p4_digest.py")

load_context_candles = P3R.load_context_candles

_FP = "0" * 64
_PROV = UUID("0193f450-4444-7abc-8def-abcdefabcd44")

#: Pine POI type code -> production PoiType. The P3 vocabulary, unchanged.
POI_TYPE_BY_CODE: dict[int, PoiType] = {
    1: PoiType.BUY_ORDER_BLOCK,
    2: PoiType.SELL_ORDER_BLOCK,
    3: PoiType.BUY_FAIR_VALUE_GAP,
    4: PoiType.SELL_FAIR_VALUE_GAP,
    5: PoiType.BUY_TO_SELL_CANDLE,
    6: PoiType.SELL_TO_BUY_CANDLE,
    7: PoiType.BASE_RALLY,
    8: PoiType.BASE_DROP,
    9: PoiType.BULLISH_PRESSURE_WICK,
    10: PoiType.BEARISH_PRESSURE_WICK,
    11: PoiType.BULLISH_ENGULFING,
    12: PoiType.BEARISH_ENGULFING,
    13: PoiType.HAMMER,
    14: PoiType.SHOOTING_STAR,
    15: PoiType.MORNING_STAR,
    16: PoiType.EVENING_STAR,
    17: PoiType.SUPPORT_ZONE,
    18: PoiType.RESISTANCE_ZONE,
}
CODE_BY_POI_TYPE: dict[PoiType, int] = {v: k for k, v in POI_TYPE_BY_CODE.items()}

_STRUCTURAL = {PoiType.SUPPORT_ZONE, PoiType.RESISTANCE_ZONE}


def _uuid_for(*parts: object) -> UUID:
    """Content-addressed identity from the P3 semantic key.

    Sequential ids would make the mapping depend on iteration order, which the
    digest must not be able to see.
    """
    digest = hashlib.sha256("|".join(str(p) for p in parts).encode()).hexdigest()
    return UUID(
        f"{digest[:8]}-{digest[8:12]}-7{digest[13:16]}-8{digest[17:20]}-{digest[20:32]}"
    )


def _dt(ms: int) -> datetime:
    return datetime.fromtimestamp(ms / 1000, tz=UTC)


class _ContentIdentity:
    def identify(
        self, *, output_type: DerivedOutputType, semantic_key: tuple[str, ...]
    ) -> UUID:
        return _uuid_for(output_type, *semantic_key)


@dataclass(frozen=True)
class P4ReplayResult:
    """Everything the comparison needs, and nothing it could be biased by."""

    timeframe: Timeframe
    poi_count: int
    setup_count: int
    states: list[Any]
    counts: dict[str, int]
    overall_hash_1: int
    overall_hash_2: int
    group_hashes: dict[str, int]
    transition_total: int
    reviewed_evidence_present: bool

    def trace_rows(self, mintick: Decimal) -> list[list[str]]:
        return G4.trace_rows(self.states, mintick)


def _build_pois(
    registry: list[Any], timeframe: Timeframe
) -> tuple[list[PoiObservation], dict[int, UUID]]:
    pois: list[PoiObservation] = []
    by_index: dict[int, UUID] = {}
    for index, poi in enumerate(registry):
        poi_type = POI_TYPE_BY_CODE[poi.poi_type]
        record_id = _uuid_for(
            "poi",
            poi.poi_type,
            poi.src_first_time,
            poi.src_count,
            poi.src_last_time,
            poi.zone_bottom,
            poi.zone_top,
        )
        by_index[index] = record_id
        pois.append(
            PoiObservation(
                record_id=record_id,
                content_fingerprint=_FP,
                symbol=InternalSymbol.XAUUSD,
                source_timeframe=timeframe,
                effective_timeframe=timeframe,
                family=(
                    PoiFamily.STRUCTURAL
                    if poi_type in _STRUCTURAL
                    else PoiFamily.PRICE_ACTION
                ),
                poi_type=poi_type,
                direction=(
                    PoiDirection.BULLISH if poi.direction == 1 else PoiDirection.BEARISH
                ),
                zone_top=poi.zone_top,
                zone_bottom=poi.zone_bottom,
                representative_price=None,
                strength_tier=None,
                source_candle_record_ids=(),
                source_measurement_record_ids=(),
                merged_source_poi_record_ids=(),
                candidate_event_time_utc=_dt(poi.candidate_time),
                confirmation_time_utc=_dt(poi.confirm_time),
                availability_time_utc=_dt(poi.confirm_time),
                rule_version=SemVer.parse("0.1.0"),
                contract_version=SemVer.parse("0.1.0"),
                schema_version=SemVer.parse("0.1.0"),
                evidence_classification=(
                    EvidenceClassification.ENGINEERING_PROVISIONAL
                ),
                provenance_id=_PROV,
            )
        )
    return pois, by_index


def _build_transitions(
    registry: list[Any],
    cursors: list[Any],
    by_index: dict[int, UUID],
    timeframe: Timeframe,
) -> list[PoiLifecycleTransition]:
    """Forward only the two transition kinds `analyze_btmm` reads."""
    wanted = {
        9: PoiLifecycleTransitionType.FALSE_INVALIDATION_CONFIRMED,
        10: PoiLifecycleTransitionType.GENUINE_INVALIDATION_CONFIRMED,
    }
    out: list[PoiLifecycleTransition] = []
    for index, cursor in enumerate(cursors):
        for order, transition in enumerate(cursor.transitions()):
            kind = wanted.get(transition.code)
            if kind is None:
                continue
            out.append(
                PoiLifecycleTransition(
                    record_id=_uuid_for("tr", by_index[index], order, transition.code),
                    content_fingerprint=_FP,
                    symbol=InternalSymbol.XAUUSD,
                    timeframe=timeframe,
                    poi_record_id=by_index[index],
                    transition_type=kind,
                    triggering_candle_record_id=_uuid_for("cand", transition.event_ms),
                    event_time_utc=_dt(transition.event_ms),
                    availability_time_utc=_dt(transition.availability_ms),
                    rule_version=SemVer.parse("0.1.0"),
                    contract_version=SemVer.parse("0.1.0"),
                    schema_version=SemVer.parse("0.1.0"),
                    evidence_classification=(
                        EvidenceClassification.ENGINEERING_PROVISIONAL
                    ),
                    provenance_id=_PROV,
                )
            )
    return out


# --- production enum -> Pine code -------------------------------------------

_ST = {
    "BTMM_CANDIDATE": 1,
    "BTMM_FORMING": 2,
    "BTMM_BLOCKED": 3,
    "BTMM_CONFIRMED": 4,
    "BTMM_CANCELLED": 5,
}
_STAGE = {"POI_INTERACTION": 4, "REACTION_MONITORING": 5, "FINAL_GATE_EVALUATION": 6}
_GATE = {"PENDING": 0, "PASS": 1, "FAIL": 2}
_IC = {
    "EDGE_TOUCH": 1,
    "PARTIAL_ENTRY": 2,
    "DEEP_ENTRY": 3,
    "FAR_BOUNDARY_TOUCH": 4,
    "CONTROLLED_OVERSHOOT": 5,
    "EXCESSIVE_OVERSHOOT": 6,
    "NONCANONICAL_SIDE_INTERACTION": 9,
}
_RC = {"WEAK_REACTION": 3, "STANDARD_REACTION": 4, "STRONG_REACTION": 5}
_SPD = {"SLOW_OR_UNCLEAR": 1, "FAST": 2, "STRONG_FAST": 3}
_CTX = {"PENDING": 0, "ALIGNED": 1, "MISALIGNED": 2, "UNKNOWN": 3}
_SESS = {"PENDING": 0, "ACTIVE": 1, "INACTIVE": 2, "UNKNOWN": 3}
_VOL = {
    "PENDING": 0,
    "SUPPORTS": 1,
    "FAILS": 2,
    "MISSING_DATA": 3,
    "UNRESOLVED": 4,
}
_LQS = {"PENDING": 0, "PRESENT": 1}
_LQL = {"LIQUIDITY_AFTER_POI": 3}
_SRC = {
    "EXPERT_LABELLED": 1,
    "RULE_BASED": 2,
    "HYBRID_REVIEWED": 4,
    "RULE_BASED_REVIEWED": 5,
}
_CANCEL = {
    "POI_REJECTED": 1,
    "INTERACTION_INELIGIBLE": 2,
    "WEAK_REACTION": 3,
    "REACTION_SPEED_FAILED": 4,
    "CONTEXT_REJECTED": 5,
    "SESSION_INACTIVE": 6,
    "VOLUME_PILLAR_FAILED": 7,
    "NO_LIQUIDITY_EVIDENCE": 8,
}
_BLOCK = {
    "CONTEXT_UNKNOWN": 1,
    "LIQUIDITY_REVIEW_PENDING": 2,
    "VOLUME_REVIEW_PENDING": 3,
    "FORMATION_TIMEFRAME_NOT_CONFIRMED": 4,
}
_TR = {
    "ENTERED_FORMING": 1,
    "ACCURACY_GATE_CONFIRMED": 2,
    "INTERACTION_INELIGIBLE": 3,
    "REACTION_GATE_CONFIRMED": 4,
    "WEAK_REACTION": 5,
    "REACTION_SPEED_GATE_CONFIRMED": 6,
    "REACTION_SPEED_FAILED": 7,
    "BLOCKED": 8,
    "RESUMED_FORMING": 9,
    "CONFIRMED": 10,
    "POI_REJECTED": 11,
    "CONTEXT_REJECTED": 12,
    "SESSION_INACTIVE": 13,
    "VOLUME_PILLAR_FAILED": 14,
    "NO_LIQUIDITY_EVIDENCE": 15,
}


def _code(table: dict[str, int], member: Any, absent: int = 0) -> int:
    return absent if member is None else table[member.value]


def _ms(moment: datetime | None) -> int:
    return -1 if moment is None else int(moment.timestamp() * 1000)


def _restamp(
    candles: tuple[NormalizedCandle, ...], timeframe: Timeframe
) -> tuple[NormalizedCandle, ...]:
    """Re-label the loaded candles onto the captured timeframe.

    `load_context_candles` is the P2/P3 loader and stamps M15, which is all
    those campaigns ever captured. `analyze_btmm` validates that every candle's
    timeframe agrees with its bundle's, so an M5 or M1 capture has to be
    re-labelled. Only the two timeframe fields change -- prices, times and
    identity are untouched -- so the loader stays the single interpretation of a
    context CSV rather than being forked.
    """
    if timeframe is Timeframe.M15:
        return candles
    return tuple(
        c.model_copy(
            update={"timeframe": timeframe, "source_timeframe": timeframe.value}
        )
        for c in candles
    )


def replay(
    candles: tuple[NormalizedCandle, ...],
    mintick: Decimal,
    timeframe: Timeframe,
) -> P4ReplayResult:
    """Context -> P3 registry + lifecycle -> production analyze_btmm -> digest."""
    candles = _restamp(candles, timeframe)
    poi_config = PoiConfiguration(minimum_price_tick=mintick)
    atr_all = compute_atr_series(candles, 14)

    registry = M.run_frontier(list(candles), poi_config)
    registry = [
        *registry,
        *P3R.reference_zone_pois(candles, atr_all, mintick),
    ]

    cursors: list[Any] = []
    for poi in registry:
        direction = PoiDirection.BULLISH if poi.direction == 1 else PoiDirection.BEARISH
        cursor = L.PoiLifecycleCursor(
            zone_top=poi.zone_top,
            zone_bottom=poi.zone_bottom,
            direction=direction,
            availability_ms=poi.confirm_time,
            configuration=poi_config,
        )
        for index in range(len(candles)):
            cursor.advance(candles, atr_all, index)
        cursors.append(cursor)

    pois, by_index = _build_pois(registry, timeframe)
    transitions = _build_transitions(registry, cursors, by_index, timeframe)

    analysis = analyze_btmm(
        (
            BtmmTimeframeInput(
                timeframe=timeframe,
                candles=candles,
                measurement_analysis=MarketMeasurementAnalysis(
                    symbol=InternalSymbol.XAUUSD,
                    timeframe=timeframe,
                    analyzed_candle_count=len(candles),
                    confirmed_swings=(),
                    displacement_observations=(),
                    equal_level_clusters=(),
                    support_resistance_zones=(),
                    trendlines=(),
                ),
            ),
        ),
        PoiAnalysis(
            symbol=InternalSymbol.XAUUSD,
            analyzed_timeframes=(timeframe,),
            analyzed_candle_count_by_timeframe=(len(candles),),
            poi_observations=tuple(pois),
            poi_lifecycle_transitions=tuple(transitions),
            poi_overlap_relationships=(),
            current_poi_states=(),
        ),
        (),  # reviewed_evidence: the runtime contract, never fabricated
        BtmmConfiguration(minimum_price_tick=mintick),
        _ContentIdentity(),
    )

    poi_by_id = {p.record_id: p for p in pois}
    source_of_setup = {
        o.record_id: o.source_poi_record_id for o in analysis.btmm_observations
    }

    # latest_lifecycle_transition_id is reduced in walk-emission order upstream;
    # the transition list here is the canonical public one, so the reduction is
    # taken from the state record rather than recomputed by sorting.
    tr_by_setup: dict[UUID, list[Any]] = {}
    for t in analysis.btmm_lifecycle_transitions:
        tr_by_setup.setdefault(t.btmm_setup_record_id, []).append(t)
    latest_by_id = {t.record_id: t for t in analysis.btmm_lifecycle_transitions}

    states: list[Any] = []
    for state in analysis.current_btmm_states:
        poi = poi_by_id[source_of_setup[state.btmm_setup_record_id]]
        emitted = tr_by_setup.get(state.btmm_setup_record_id, [])
        latest = latest_by_id.get(state.latest_lifecycle_transition_id)
        states.append(
            G4.P4SetupState(
                poi_type=CODE_BY_POI_TYPE[poi.poi_type],
                poi_direction=1 if poi.direction == PoiDirection.BULLISH else -1,
                zone_bottom=poi.zone_bottom,
                zone_top=poi.zone_top,
                candidate_avail_time=_ms(poi.availability_time_utc),
                btmm_direction=(
                    1 if state.btmm_direction.value == "BULLISH_BTMM" else -1
                ),
                primary_state=_ST[state.primary_state.value],
                formation_stage=_code(_STAGE, state.formation_stage),
                accuracy_gate=_GATE[state.accuracy_gate_status.value],
                interaction_class=_code(_IC, state.interaction_class),
                reaction_gate=_GATE[state.reaction_gate_status.value],
                reaction_class=_code(_RC, state.reaction_classification),
                reaction_speed_gate=_GATE[state.reaction_speed_gate_status.value],
                reaction_speed_class=_code(_SPD, state.reaction_speed_classification),
                formation_tf_gate=_GATE[state.formation_timeframe_gate_status.value],
                market_direction=_CTX[state.market_direction_status.value],
                analytical_framework=_CTX[state.analytical_framework_status.value],
                session=_SESS[state.session_status.value],
                volume=_VOL[state.volume_pillar_status.value],
                liquidity_status=_LQS[state.liquidity_evidence_status.value],
                liquidity_location=_code(_LQL, state.liquidity_location),
                liquidity_source=_code(_SRC, state.liquidity_evidence_source),
                reviewed_evidence_time=_ms(
                    state.reviewed_evidence_availability_time_utc
                ),
                cancellation_reason=_code(_CANCEL, state.cancellation_reason),
                blocked_reason=_code(_BLOCK, state.blocked_reason),
                availability_time=_ms(state.availability_time_utc),
                transition_count=len(emitted),
                last_transition_code=(
                    0 if latest is None else _TR[latest.transition_type.value]
                ),
                last_transition_event=(
                    -1 if latest is None else _ms(latest.event_time_utc)
                ),
                last_transition_avail=(
                    -1 if latest is None else _ms(latest.availability_time_utc)
                ),
            )
        )

    h1, h2 = G4.overall_hashes(states, mintick)
    return P4ReplayResult(
        timeframe=timeframe,
        poi_count=len(pois),
        setup_count=len(states),
        states=states,
        counts=G4.state_counts(states),
        overall_hash_1=h1,
        overall_hash_2=h2,
        group_hashes=G4.group_hashes(states, mintick),
        transition_total=len(analysis.btmm_lifecycle_transitions),
        reviewed_evidence_present=False,
    )


def replay_csv(
    csv_path: Path, mintick: Decimal, timeframe: Timeframe
) -> P4ReplayResult:
    return replay(load_context_candles(csv_path), mintick, timeframe)


def write_trace(result: P4ReplayResult, mintick: Decimal, path: Path) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(list(G4.FIELD_NAMES))
        writer.writerows(result.trace_rows(mintick))
