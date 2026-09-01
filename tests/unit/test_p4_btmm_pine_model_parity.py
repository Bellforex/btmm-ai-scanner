"""Differential parity: the Pine-shaped BTMM model against `analyze_btmm`.

`tests/parity_support/p4_btmm_model.py` is the transcription the Pine port is
written from, so it has to agree with production before a line of Pine is
written -- otherwise a later Pine divergence is ambiguous between a bad port and
a bad model.

The comparison runs at EVERY PREFIX, not just at the end. Pine reports on every
confirmed bar, so agreeing only on the final bar would leave the whole reported
history unproven. At prefix T the model has been advanced bar by bar with no
history rescan, while production re-runs its batch walk over `candles[:T+1]`;
the two must produce the same setups, the same states and the same transitions
in the same emission order.

Both evidence modes are proven against the same oracle:

* Layer A -- reviewed evidence supplied, so `BTMM_CONFIRMED` is reachable;
* Layer B -- `reviewed_evidence = ()`, the TradingView runtime contract, which
  cancels with `NO_LIQUIDITY_EVIDENCE`.

Neither mode is allowed to imitate the other, and the Layer B run is checked to
be genuinely evidence-free rather than merely unconfirmed.
"""

from __future__ import annotations

import random
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any
from uuid import UUID

import pytest

from btmm_ai_scanner.btmm.analyzer import BtmmTimeframeInput, analyze_btmm
from btmm_ai_scanner.btmm.configuration import BtmmConfiguration
from btmm_ai_scanner.btmm.enums import BtmmLifecycleStatus
from btmm_ai_scanner.btmm.reviewed_evidence import BtmmReviewedEvidence
from btmm_ai_scanner.config.enums import InternalSymbol, Timeframe
from btmm_ai_scanner.contracts.normalized_candle import NormalizedCandle
from btmm_ai_scanner.contracts.provenance_record import EvidenceClassification
from btmm_ai_scanner.contracts.raw_candle import CandleCompleteness, CandleVolumeKind
from btmm_ai_scanner.contracts.types import SemVer
from btmm_ai_scanner.domain import MarketMeasurementAnalysis
from btmm_ai_scanner.domain.enums import DerivedOutputType
from btmm_ai_scanner.measurements.atr import compute_atr_series
from btmm_ai_scanner.poi.analyzer import PoiAnalysis
from btmm_ai_scanner.poi.enums import (
    PoiDirection,
    PoiFamily,
    PoiLifecycleTransitionType,
    PoiType,
)
from btmm_ai_scanner.poi.lifecycle import PoiLifecycleTransition
from btmm_ai_scanner.poi.observation import PoiObservation
from tests.parity_support import p4_btmm_model as M

_FP = "a" * 64
_PROV = UUID("0193f450-1234-7abc-8def-abcdefabcdff")
_RAW = UUID("0193f450-1234-7abc-8def-abcdefabcdaa")
_T0 = datetime(2026, 1, 1, tzinfo=UTC)
_STEP = timedelta(minutes=15)
_CONFIG = BtmmConfiguration(minimum_price_tick=Decimal("0.01"))


class _Identity:
    def __init__(self) -> None:
        self._seen: dict[Any, UUID] = {}

    def identify(
        self, *, output_type: DerivedOutputType, semantic_key: tuple[str, ...]
    ) -> UUID:
        key = (output_type, semantic_key)
        if key not in self._seen:
            n = len(self._seen) + 1
            self._seen[key] = UUID(f"0193f450-0000-7000-8000-{n:012x}")
        return self._seen[key]


def _candle(index: int, o: str, h: str, low: str, c: str) -> NormalizedCandle:
    event = _T0 + _STEP * index
    return NormalizedCandle.model_validate(
        {
            "record_id": UUID(f"0193f415-1234-7abc-8def-{index:012x}"),
            "content_fingerprint": _FP,
            "raw_candle_id": _RAW,
            "provider": "FXCM",
            "source_reference": "fxcm",
            "source_symbol": "XAUUSD",
            "source_timeframe": "M15",
            "symbol": InternalSymbol.XAUUSD,
            "timeframe": Timeframe.M15,
            "event_time_utc": event,
            "availability_time_utc": event + _STEP,
            "processing_time_utc": event + _STEP,
            "original_event_time": event,
            "original_availability_time": event + _STEP,
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
            "provenance_id": _PROV,
        }
    )


def _stream(seed: int, count: int) -> tuple[NormalizedCandle, ...]:
    """A random walk that repeatedly crosses the zone band the POIs sit in, so
    interactions, reactions and failures all actually occur."""
    rng = random.Random(seed)
    out: list[NormalizedCandle] = []
    price = 102.0
    for index in range(count):
        drift = rng.uniform(-2.2, 2.2)
        open_ = price
        close = max(95.0, min(112.0, price + drift))
        high = max(open_, close) + rng.uniform(0.0, 1.1)
        low = min(open_, close) - rng.uniform(0.0, 1.1)
        out.append(
            _candle(index, f"{open_:.2f}", f"{high:.2f}", f"{low:.2f}", f"{close:.2f}")
        )
        price = close
    return tuple(out)


def _poi(
    n: int, direction: PoiDirection, top: str, bottom: str, at: int
) -> PoiObservation:
    moment = _T0 + _STEP * at
    return PoiObservation(
        record_id=UUID(f"0193f4aa-0000-7000-8000-{n:012x}"),
        content_fingerprint=_FP,
        symbol=InternalSymbol.XAUUSD,
        source_timeframe=Timeframe.M15,
        effective_timeframe=Timeframe.M15,
        family=PoiFamily.STRUCTURAL,
        poi_type=(
            PoiType.SUPPORT_ZONE
            if direction == PoiDirection.BULLISH
            else PoiType.RESISTANCE_ZONE
        ),
        direction=direction,
        zone_top=Decimal(top),
        zone_bottom=Decimal(bottom),
        representative_price=None,
        strength_tier=None,
        source_candle_record_ids=(),
        source_measurement_record_ids=(),
        merged_source_poi_record_ids=(),
        candidate_event_time_utc=moment,
        confirmation_time_utc=moment,
        availability_time_utc=moment + _STEP,
        rule_version=SemVer.parse("0.1.0"),
        contract_version=SemVer.parse("0.1.0"),
        schema_version=SemVer.parse("0.1.0"),
        evidence_classification=EvidenceClassification.ENGINEERING_PROVISIONAL,
        provenance_id=_PROV,
    )


def _pois() -> tuple[PoiObservation, ...]:
    return (
        _poi(1, PoiDirection.BULLISH, "101.0", "100.0", 2),
        _poi(2, PoiDirection.BEARISH, "107.0", "106.0", 3),
        _poi(3, PoiDirection.BULLISH, "104.5", "103.5", 5),
    )


def _evidence_for(
    poi: PoiObservation, at_index: int, *, liquidity_present: bool = True
) -> BtmmReviewedEvidence:
    from btmm_ai_scanner.btmm.enums import (
        BtmmContextAlignmentStatus,
        BtmmEvidenceSource,
        BtmmLiquidityEvidenceStatus,
        BtmmSessionStatus,
        BtmmVolumePillarStatus,
    )

    return BtmmReviewedEvidence(
        symbol=InternalSymbol.XAUUSD,
        timeframe=Timeframe.M15,
        source_poi_record_id=poi.record_id,
        market_direction_status=BtmmContextAlignmentStatus.ALIGNED,
        analytical_framework_status=BtmmContextAlignmentStatus.ALIGNED,
        session_status=BtmmSessionStatus.ACTIVE,
        liquidity_evidence_status=(
            BtmmLiquidityEvidenceStatus.PRESENT
            if liquidity_present
            else BtmmLiquidityEvidenceStatus.PENDING
        ),
        volume_pillar_status=BtmmVolumePillarStatus.SUPPORTS,
        context_input_source=BtmmEvidenceSource.EXPERT_LABELLED,
        liquidity_event_source=BtmmEvidenceSource.EXPERT_LABELLED,
        volume_evidence_source=BtmmEvidenceSource.EXPERT_LABELLED,
        availability_time_utc=_T0 + _STEP * at_index,
        rule_version=SemVer.parse("0.1.0"),
        contract_version=SemVer.parse("0.1.0"),
        schema_version=SemVer.parse("0.1.0"),
    )


# --------------------------------------------------------------------------
# Oracle -> Pine-code projection
# --------------------------------------------------------------------------

_STATUS_CODE = {v: k for k, v in M.STATUS_BY_CODE.items()}
_STAGE_CODE = {v: k for k, v in M.STAGE_BY_CODE.items()}
_GATE_CODE = {v: k for k, v in M.GATE_BY_CODE.items()}
_IC_CODE = {v: k for k, v in M.INTERACTION_BY_CODE.items()}
_RC_CODE = {v: k for k, v in M.REACTION_BY_CODE.items()}
_LQL_CODE = {v: k for k, v in M.LIQUIDITY_LOCATION_BY_CODE.items()}
_CANCEL_CODE = {v: k for k, v in M.CANCEL_BY_CODE.items()}
_BLOCK_CODE = {v: k for k, v in M.BLOCK_BY_CODE.items()}
_TR_CODE = {v: k for k, v in M.TRANSITION_BY_CODE.items()}


def _ts(moment: datetime | None) -> int:
    return -1 if moment is None else int(moment.timestamp() * 1000)


def _project_state(state: Any, poi_key: str) -> M.PineState:
    return M.PineState(
        poi_key=poi_key,
        direction=(
            M.DIR_BULLISH
            if state.btmm_direction.value == "BULLISH_BTMM"
            else M.DIR_BEARISH
        ),
        primary_state=_STATUS_CODE[state.primary_state],
        formation_stage=_STAGE_CODE[state.formation_stage],
        market_direction=M.CONTEXT_CODE[state.market_direction_status],
        analytical_framework=M.CONTEXT_CODE[state.analytical_framework_status],
        session=M.SESSION_CODE[state.session_status],
        accuracy_gate=_GATE_CODE[state.accuracy_gate_status],
        interaction_class=_IC_CODE[state.interaction_class],
        reaction_gate=_GATE_CODE[state.reaction_gate_status],
        reaction_class=_RC_CODE[state.reaction_classification],
        reaction_speed_gate=_GATE_CODE[state.reaction_speed_gate_status],
        reaction_speed_class=(
            0
            if state.reaction_speed_classification is None
            else M.SPEED_CODE[state.reaction_speed_classification]
        ),
        formation_tf_gate=_GATE_CODE[state.formation_timeframe_gate_status],
        volume=M.VOLUME_CODE[state.volume_pillar_status],
        liquidity_status=M.LIQUIDITY_STATUS_CODE[state.liquidity_evidence_status],
        liquidity_location=_LQL_CODE[state.liquidity_location],
        liquidity_source=(
            M.SRC_NA
            if state.liquidity_evidence_source is None
            else M.EVIDENCE_SOURCE_CODE[state.liquidity_evidence_source]
        ),
        reviewed_evidence_time=_ts(state.reviewed_evidence_availability_time_utc),
        cancellation_reason=_CANCEL_CODE[state.cancellation_reason],
        blocked_reason=_BLOCK_CODE[state.blocked_reason],
        availability_time=_ts(state.availability_time_utc),
    )


# --------------------------------------------------------------------------
# Runners
# --------------------------------------------------------------------------


def _run_oracle(
    candles: tuple[NormalizedCandle, ...],
    pois: tuple[PoiObservation, ...],
    evidence: tuple[BtmmReviewedEvidence, ...],
    poi_transitions: tuple[PoiLifecycleTransition, ...],
    configuration: BtmmConfiguration = _CONFIG,
) -> Any:
    return analyze_btmm(
        (
            BtmmTimeframeInput(
                timeframe=Timeframe.M15,
                candles=candles,
                measurement_analysis=MarketMeasurementAnalysis(
                    symbol=InternalSymbol.XAUUSD,
                    timeframe=Timeframe.M15,
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
            analyzed_timeframes=(Timeframe.M15,),
            analyzed_candle_count_by_timeframe=(len(candles),),
            poi_observations=pois,
            poi_lifecycle_transitions=poi_transitions,
            poi_overlap_relationships=(),
            current_poi_states=(),
        ),
        evidence,
        configuration,
        _Identity(),
    )


def _run_model(
    candles: tuple[NormalizedCandle, ...],
    pois: tuple[PoiObservation, ...],
    evidence: tuple[BtmmReviewedEvidence, ...],
    poi_transitions: tuple[PoiLifecycleTransition, ...],
    configuration: BtmmConfiguration = _CONFIG,
) -> tuple[list[M.PineTransition], list[M.PineState]]:
    engine = M.PineBtmmEngine(configuration=configuration)
    for poi in pois:
        engine.add_setup(
            M.PineSetupSpec(
                poi_key=str(poi.record_id),
                direction=(
                    M.DIR_BULLISH
                    if poi.direction == PoiDirection.BULLISH
                    else M.DIR_BEARISH
                ),
                zone_top=poi.zone_top,
                zone_bottom=poi.zone_bottom,
                candidate_availability_time=_ts(poi.availability_time_utc),
                is_formation_timeframe=(
                    poi.source_timeframe in configuration.formation_timeframes
                ),
            )
        )

    atrs = compute_atr_series(candles, 14)
    for index, candle in enumerate(candles):
        engine.advance(
            M.PineCandle(
                open=candle.open,
                high=candle.high,
                low=candle.low,
                close=candle.close,
                event_time=_ts(candle.event_time_utc),
                availability_time=_ts(candle.availability_time_utc),
            ),
            atrs[index],
        )

    false_inv = {
        str(t.poi_record_id): True
        for t in poi_transitions
        if t.transition_type == PoiLifecycleTransitionType.FALSE_INVALIDATION_CONFIRMED
    }
    genuine: dict[str, tuple[int, int]] = {}
    for t in poi_transitions:
        if (
            t.transition_type
            != PoiLifecycleTransitionType.GENUINE_INVALIDATION_CONFIRMED
        ):
            continue
        key = str(t.poi_record_id)
        stamp = (_ts(t.event_time_utc), _ts(t.availability_time_utc))
        if key not in genuine or stamp[1] < genuine[key][1]:
            genuine[key] = stamp

    return M.report(
        engine,
        false_inv,
        genuine,
        {str(e.source_poi_record_id): _project_evidence(e) for e in evidence},
    )


def _project_evidence(evidence: BtmmReviewedEvidence) -> M.PineEvidence:
    return M.PineEvidence(
        poi_key=str(evidence.source_poi_record_id),
        availability_time=_ts(evidence.availability_time_utc),
        market_direction=M.CONTEXT_CODE[evidence.market_direction_status],
        analytical_framework=M.CONTEXT_CODE[evidence.analytical_framework_status],
        session=M.SESSION_CODE[evidence.session_status],
        liquidity_status=M.LIQUIDITY_STATUS_CODE[evidence.liquidity_evidence_status],
        volume=M.VOLUME_CODE[evidence.volume_pillar_status],
        liquidity_source=M.EVIDENCE_SOURCE_CODE[evidence.liquidity_event_source],
    )


def _compare(
    candles: tuple[NormalizedCandle, ...],
    pois: tuple[PoiObservation, ...],
    evidence: tuple[BtmmReviewedEvidence, ...] = (),
    poi_transitions: tuple[PoiLifecycleTransition, ...] = (),
    configuration: BtmmConfiguration = _CONFIG,
) -> Any:
    oracle = _run_oracle(candles, pois, evidence, poi_transitions, configuration)
    model_transitions, model_states = _run_model(
        candles, pois, evidence, poi_transitions, configuration
    )

    setup_to_key = {
        observation.record_id: str(observation.source_poi_record_id)
        for observation in oracle.btmm_observations
    }

    expected_states = sorted(
        (
            _project_state(state, setup_to_key[state.btmm_setup_record_id])
            for state in oracle.current_btmm_states
        ),
        key=lambda s: s.poi_key,
    )
    actual_states = sorted(model_states, key=lambda s: s.poi_key)
    assert actual_states == expected_states

    expected_transitions = sorted(
        (
            setup_to_key[t.btmm_setup_record_id],
            _TR_CODE[t.transition_type],
            _BLOCK_CODE[t.blocked_reason],
            _ts(t.event_time_utc),
            _ts(t.availability_time_utc),
        )
        for t in oracle.btmm_lifecycle_transitions
    )
    actual = sorted(
        (t.poi_key, t.code, t.blocked_reason, t.event_time, t.availability_time)
        for t in model_transitions
    )
    assert actual == expected_transitions
    return oracle


# --------------------------------------------------------------------------
# Prefix campaigns
# --------------------------------------------------------------------------


@pytest.mark.parametrize("seed", range(6))
def test_no_evidence_every_prefix(seed: int) -> None:
    """Layer B: the TradingView runtime contract, at every reported bar."""
    candles = _stream(seed, 46)
    pois = _pois()
    for cut in range(1, len(candles) + 1):
        _compare(candles[:cut], pois)


@pytest.mark.parametrize("seed", range(6))
def test_full_evidence_every_prefix(seed: int) -> None:
    """Layer A: the complete engine, with confirmation reachable."""
    candles = _stream(seed, 46)
    pois = _pois()
    evidence = tuple(_evidence_for(poi, 8) for poi in pois)
    for cut in range(1, len(candles) + 1):
        _compare(candles[:cut], pois, evidence)


@pytest.mark.parametrize("seed", range(4))
def test_late_evidence_every_prefix(seed: int) -> None:
    """Evidence arriving after the reaction window closes takes the BLOCKED-then-
    resolve path, which is a different branch from same-bar evidence."""
    candles = _stream(seed, 46)
    pois = _pois()
    evidence = tuple(_evidence_for(poi, 44) for poi in pois)
    for cut in range(1, len(candles) + 1):
        _compare(candles[:cut], pois, evidence)


def _poi_transition(
    poi: PoiObservation, kind: PoiLifecycleTransitionType, at: int, n: int
) -> PoiLifecycleTransition:
    moment = _T0 + _STEP * at
    return PoiLifecycleTransition(
        record_id=UUID(f"0193f4bb-0000-7000-8000-{n:012x}"),
        content_fingerprint=_FP,
        symbol=InternalSymbol.XAUUSD,
        timeframe=Timeframe.M15,
        poi_record_id=poi.record_id,
        transition_type=kind,
        triggering_candle_record_id=UUID(f"0193f415-1234-7abc-8def-{at:012x}"),
        event_time_utc=moment,
        availability_time_utc=moment + _STEP,
        rule_version=SemVer.parse("0.1.0"),
        contract_version=SemVer.parse("0.1.0"),
        schema_version=SemVer.parse("0.1.0"),
        evidence_classification=EvidenceClassification.ENGINEERING_PROVISIONAL,
        provenance_id=_PROV,
    )


@pytest.mark.parametrize("seed", range(4))
def test_derived_liquidity_every_prefix(seed: int) -> None:
    """A P3 false invalidation feeds derived liquidity into the walk."""
    candles = _stream(seed, 46)
    pois = _pois()
    transitions = tuple(
        _poi_transition(
            poi, PoiLifecycleTransitionType.FALSE_INVALIDATION_CONFIRMED, 12, n
        )
        for n, poi in enumerate(pois)
    )
    for cut in range(1, len(candles) + 1):
        _compare(candles[:cut], pois, (), transitions)


@pytest.mark.parametrize("seed", range(4))
def test_genuine_invalidation_truncates_every_prefix(seed: int) -> None:
    """A genuine invalidation truncates the walk at its own availability,
    whatever price stage the setup had reached."""
    candles = _stream(seed, 46)
    pois = _pois()
    evidence = tuple(_evidence_for(poi, 8) for poi in pois)
    transitions = tuple(
        _poi_transition(
            poi, PoiLifecycleTransitionType.GENUINE_INVALIDATION_CONFIRMED, 20, n
        )
        for n, poi in enumerate(pois)
    )
    for cut in range(1, len(candles) + 1):
        _compare(candles[:cut], pois, evidence, transitions)


@pytest.mark.parametrize("seed", range(4))
def test_pending_liquidity_evidence_every_prefix(seed: int) -> None:
    """Evidence that exists but reports liquidity PENDING still cancels -- the
    presence of a reviewed record is not itself the gate."""
    candles = _stream(seed, 46)
    pois = _pois()
    evidence = tuple(_evidence_for(poi, 8, liquidity_present=False) for poi in pois)
    for cut in range(1, len(candles) + 1):
        _compare(candles[:cut], pois, evidence)


# --------------------------------------------------------------------------
# A scripted stream that actually confirms
# --------------------------------------------------------------------------
#
# The random walk above exercises interaction, weak reaction, speed failure and
# invalidation, but its drift never clears the zone by the full height the
# STANDARD tier demands, so it cannot reach BTMM_CONFIRMED. Rather than loosen
# the thresholds -- which would be tuning the test until the product looks good
# -- this adds a deliberately shaped stream: a quiet approach, a sweep into the
# zone, then a sustained rally away from it.


def _confirming_stream() -> tuple[NormalizedCandle, ...]:
    rows = [("105", "105.2", "104.8", "105")] * 14
    rows.append(("105", "105.1", "100.5", "100.8"))
    rows.append(("100.8", "102.2", "100.7", "102.0"))
    rows.append(("102.0", "103.5", "101.9", "103.4"))
    rows.append(("103.4", "105.0", "103.3", "104.9"))
    rows.append(("104.9", "106.5", "104.8", "106.4"))
    rows.append(("106.4", "108.0", "106.3", "107.9"))
    return tuple(_candle(i, *row) for i, row in enumerate(rows))


def _confirming_poi() -> PoiObservation:
    return _poi(7, PoiDirection.BULLISH, "101", "100", 12)


def test_confirming_stream_every_prefix() -> None:
    """Layer A end to end, at every reported bar, on a stream that confirms."""
    candles = _confirming_stream()
    pois = (_confirming_poi(),)
    evidence = (_evidence_for(pois[0], 2),)
    for cut in range(1, len(candles) + 1):
        _compare(candles[:cut], pois, evidence)


def test_confirming_stream_confirms_under_evidence_and_cancels_without() -> None:
    """The two layers on identical price action: the only difference is whether
    reviewed evidence was supplied."""
    candles = _confirming_stream()
    pois = (_confirming_poi(),)

    with_evidence = _compare(candles, pois, (_evidence_for(pois[0], 2),))
    assert [s.primary_state for s in with_evidence.current_btmm_states] == [
        BtmmLifecycleStatus.BTMM_CONFIRMED
    ]

    without = _compare(candles, pois)
    assert [s.primary_state for s in without.current_btmm_states] == [
        BtmmLifecycleStatus.BTMM_CANCELLED
    ]


def test_derived_liquidity_on_the_confirming_stream_every_prefix() -> None:
    """Derived liquidity present AND review present: the reviewed source must
    supersede RULE_BASED, and the model must reproduce that."""
    candles = _confirming_stream()
    pois = (_confirming_poi(),)
    transitions = (
        _poi_transition(
            pois[0], PoiLifecycleTransitionType.FALSE_INVALIDATION_CONFIRMED, 15, 40
        ),
    )
    evidence = (_evidence_for(pois[0], 2),)
    for cut in range(1, len(candles) + 1):
        _compare(candles[:cut], pois, evidence, transitions)
    for cut in range(1, len(candles) + 1):
        _compare(candles[:cut], pois, (), transitions)


# --------------------------------------------------------------------------
# Vacuity guards: the streams must actually reach the interesting states
# --------------------------------------------------------------------------


def test_the_campaign_reaches_confirmation_and_cancellation() -> None:
    """Guard the guards. Every prefix comparison above would pass vacuously on a
    stream where no setup ever interacts with its zone."""
    seen: set[BtmmLifecycleStatus] = set()
    for seed in range(6):
        candles = _stream(seed, 46)
        pois = _pois()
        oracle = _compare(candles, pois, tuple(_evidence_for(p, 8) for p in pois))
        seen.update(s.primary_state for s in oracle.current_btmm_states)

    scripted = _confirming_stream()
    scripted_pois = (_confirming_poi(),)
    oracle = _compare(scripted, scripted_pois, (_evidence_for(scripted_pois[0], 2),))
    seen.update(s.primary_state for s in oracle.current_btmm_states)
    assert BtmmLifecycleStatus.BTMM_CONFIRMED in seen
    assert BtmmLifecycleStatus.BTMM_CANCELLED in seen


def test_layer_b_is_genuinely_evidence_free() -> None:
    """The no-evidence run must not merely fail to confirm -- every evidence
    field must remain at its PENDING default, so nothing in the runtime path can
    be quietly supplying review."""
    from btmm_ai_scanner.btmm.enums import (
        BtmmContextAlignmentStatus,
        BtmmLiquidityEvidenceStatus,
        BtmmSessionStatus,
        BtmmVolumePillarStatus,
    )

    oracle = _compare(_stream(0, 46), _pois())
    assert oracle.current_btmm_states
    for state in oracle.current_btmm_states:
        assert state.primary_state is not BtmmLifecycleStatus.BTMM_CONFIRMED
        assert state.market_direction_status is BtmmContextAlignmentStatus.PENDING
        assert state.analytical_framework_status is BtmmContextAlignmentStatus.PENDING
        assert state.session_status is BtmmSessionStatus.PENDING
        assert state.volume_pillar_status is BtmmVolumePillarStatus.PENDING
        assert state.liquidity_evidence_status is BtmmLiquidityEvidenceStatus.PENDING
        assert state.reviewed_evidence_availability_time_utc is None


# --------------------------------------------------------------------------
# Directed scenarios: one per final-gate outcome
# --------------------------------------------------------------------------
#
# The prefix campaigns above prove the model agrees with the oracle wherever the
# streams happen to go. A coverage measurement of those runs showed they never
# reach BTMM_BLOCKED, never exercise three of the eight cancellation reasons,
# and never get far enough for derived liquidity to be written. Rather than
# report that as covered, these scenarios drive each outcome deliberately: the
# confirming stream held fixed, with only the reviewed evidence varied, so the
# gate under test is the only thing that differs.


def _shaped_evidence(
    poi: PoiObservation,
    at_index: int,
    *,
    market_direction: Any = None,
    framework: Any = None,
    session: Any = None,
    volume: Any = None,
    liquidity: Any = None,
) -> BtmmReviewedEvidence:
    from btmm_ai_scanner.btmm.enums import (
        BtmmContextAlignmentStatus,
        BtmmEvidenceSource,
        BtmmLiquidityEvidenceStatus,
        BtmmSessionStatus,
        BtmmVolumePillarStatus,
    )

    return BtmmReviewedEvidence(
        symbol=InternalSymbol.XAUUSD,
        timeframe=Timeframe.M15,
        source_poi_record_id=poi.record_id,
        market_direction_status=market_direction or BtmmContextAlignmentStatus.ALIGNED,
        analytical_framework_status=framework or BtmmContextAlignmentStatus.ALIGNED,
        session_status=session or BtmmSessionStatus.ACTIVE,
        liquidity_evidence_status=liquidity or BtmmLiquidityEvidenceStatus.PRESENT,
        volume_pillar_status=volume or BtmmVolumePillarStatus.SUPPORTS,
        context_input_source=BtmmEvidenceSource.EXPERT_LABELLED,
        liquidity_event_source=BtmmEvidenceSource.EXPERT_LABELLED,
        volume_evidence_source=BtmmEvidenceSource.EXPERT_LABELLED,
        availability_time_utc=_T0 + _STEP * at_index,
        rule_version=SemVer.parse("0.1.0"),
        contract_version=SemVer.parse("0.1.0"),
        schema_version=SemVer.parse("0.1.0"),
    )


def _directed(**evidence_kwargs: Any) -> Any:
    """Run the confirming stream at every prefix with one evidence variation."""

    configuration = evidence_kwargs.pop("configuration", _CONFIG)
    at_index = evidence_kwargs.pop("at_index", 2)
    candles = _confirming_stream()
    pois = (_confirming_poi(),)
    evidence = (_shaped_evidence(pois[0], at_index, **evidence_kwargs),)
    for cut in range(1, len(candles) + 1):
        _compare(candles[:cut], pois, evidence, (), configuration)
    return _compare(candles, pois, evidence, (), configuration)


def test_directed_context_rejected() -> None:
    from btmm_ai_scanner.btmm.enums import (
        BtmmCancellationReason,
        BtmmContextAlignmentStatus,
    )

    state = _directed(market_direction=BtmmContextAlignmentStatus.MISALIGNED)
    only = state.current_btmm_states[0]
    assert only.primary_state is BtmmLifecycleStatus.BTMM_CANCELLED
    assert only.cancellation_reason is BtmmCancellationReason.CONTEXT_REJECTED


def test_directed_session_inactive() -> None:
    from btmm_ai_scanner.btmm.enums import BtmmCancellationReason, BtmmSessionStatus

    state = _directed(session=BtmmSessionStatus.INACTIVE)
    only = state.current_btmm_states[0]
    assert only.primary_state is BtmmLifecycleStatus.BTMM_CANCELLED
    assert only.cancellation_reason is BtmmCancellationReason.SESSION_INACTIVE


def test_directed_volume_pillar_failed() -> None:
    from btmm_ai_scanner.btmm.enums import (
        BtmmCancellationReason,
        BtmmVolumePillarStatus,
    )

    state = _directed(volume=BtmmVolumePillarStatus.FAILS)
    only = state.current_btmm_states[0]
    assert only.primary_state is BtmmLifecycleStatus.BTMM_CANCELLED
    assert only.cancellation_reason is BtmmCancellationReason.VOLUME_PILLAR_FAILED


def test_directed_blocked_context_unknown() -> None:
    from btmm_ai_scanner.btmm.enums import BtmmBlockedReason, BtmmContextAlignmentStatus

    state = _directed(market_direction=BtmmContextAlignmentStatus.UNKNOWN)
    only = state.current_btmm_states[0]
    assert only.primary_state is BtmmLifecycleStatus.BTMM_BLOCKED
    assert only.blocked_reason is BtmmBlockedReason.CONTEXT_UNKNOWN


def test_directed_blocked_volume_review_pending() -> None:
    from btmm_ai_scanner.btmm.enums import BtmmBlockedReason, BtmmVolumePillarStatus

    state = _directed(volume=BtmmVolumePillarStatus.MISSING_DATA)
    only = state.current_btmm_states[0]
    assert only.primary_state is BtmmLifecycleStatus.BTMM_BLOCKED
    assert only.blocked_reason is BtmmBlockedReason.VOLUME_REVIEW_PENDING


def test_directed_blocked_unresolved_volume() -> None:
    from btmm_ai_scanner.btmm.enums import BtmmBlockedReason, BtmmVolumePillarStatus

    state = _directed(volume=BtmmVolumePillarStatus.UNRESOLVED)
    assert (
        state.current_btmm_states[0].blocked_reason
        is BtmmBlockedReason.VOLUME_REVIEW_PENDING
    )


def test_directed_blocked_formation_timeframe_not_confirmed() -> None:
    """M15 moved out of the formation set, so the same evidence that would
    confirm now blocks. This exercises the supporting-only branch without
    rebuilding the stream on another timeframe."""
    from btmm_ai_scanner.btmm.configuration import BtmmConfiguration
    from btmm_ai_scanner.btmm.enums import BtmmBlockedReason

    configuration = BtmmConfiguration(
        minimum_price_tick=Decimal("0.01"),
        formation_timeframes=frozenset({Timeframe.M5}),
        supporting_only_timeframes=frozenset({Timeframe.M1, Timeframe.M15}),
    )
    state = _directed(configuration=configuration)
    only = state.current_btmm_states[0]
    assert only.primary_state is BtmmLifecycleStatus.BTMM_BLOCKED
    assert only.blocked_reason is BtmmBlockedReason.FORMATION_TIMEFRAME_NOT_CONFIRMED


def test_directed_late_evidence_blocks_then_confirms() -> None:
    """Evidence arriving after the reaction window closes emits BLOCKED with
    LIQUIDITY_REVIEW_PENDING first, then resolves on the evidence bar."""
    from btmm_ai_scanner.btmm.enums import BtmmLifecycleTransitionType

    state = _directed(at_index=22)
    only = state.current_btmm_states[0]
    assert only.primary_state is BtmmLifecycleStatus.BTMM_CONFIRMED
    kinds = [t.transition_type for t in state.btmm_lifecycle_transitions]
    assert BtmmLifecycleTransitionType.BLOCKED in kinds
    assert BtmmLifecycleTransitionType.CONFIRMED in kinds


def test_directed_late_evidence_resumes_forming() -> None:
    """Late evidence that neither confirms nor cancels emits RESUMED_FORMING --
    the one transition reachable only through the late-evidence branch."""
    from btmm_ai_scanner.btmm.enums import (
        BtmmContextAlignmentStatus,
        BtmmLifecycleTransitionType,
    )

    state = _directed(at_index=22, market_direction=BtmmContextAlignmentStatus.UNKNOWN)
    kinds = [t.transition_type for t in state.btmm_lifecycle_transitions]
    assert BtmmLifecycleTransitionType.BLOCKED in kinds
    assert BtmmLifecycleTransitionType.RESUMED_FORMING in kinds
    assert state.current_btmm_states[0].primary_state is (
        BtmmLifecycleStatus.BTMM_FORMING
    )


def test_directed_derived_liquidity_reaches_the_final_gate() -> None:
    """On a stream that gets all the way to the final gate, derived liquidity is
    actually written -- location AFTER_POI, source RULE_BASED -- and the setup
    still cancels for want of review."""
    from btmm_ai_scanner.btmm.enums import (
        BtmmCancellationReason,
        BtmmEvidenceSource,
        BtmmLiquidityEvidenceStatus,
        BtmmLiquidityLocation,
    )

    candles = _confirming_stream()
    pois = (_confirming_poi(),)
    transitions = (
        _poi_transition(
            pois[0], PoiLifecycleTransitionType.FALSE_INVALIDATION_CONFIRMED, 15, 40
        ),
    )
    state = _compare(candles, pois, (), transitions)
    only = state.current_btmm_states[0]
    assert only.liquidity_location is BtmmLiquidityLocation.LIQUIDITY_AFTER_POI
    assert only.liquidity_evidence_source is BtmmEvidenceSource.RULE_BASED
    assert only.liquidity_evidence_status is BtmmLiquidityEvidenceStatus.PENDING
    assert only.primary_state is BtmmLifecycleStatus.BTMM_CANCELLED
    assert only.cancellation_reason is BtmmCancellationReason.NO_LIQUIDITY_EVIDENCE


def test_directed_candidate_state_before_availability() -> None:
    """A setup whose POI only becomes available after the last bar stays
    BTMM_CANDIDATE with no formation stage at all."""
    candles = _confirming_stream()
    pois = (_poi(9, PoiDirection.BULLISH, "101", "100", 40),)
    state = _compare(candles, pois)
    only = state.current_btmm_states[0]
    assert only.primary_state is BtmmLifecycleStatus.BTMM_CANDIDATE
    assert only.formation_stage is None


# --------------------------------------------------------------------------
# Shaped streams: the interaction, reaction and speed classes the walks miss
# --------------------------------------------------------------------------
#
# The dip depth selects the interaction class (how far into the zone the sweep
# reaches) and the rally step selects the reaction tier and leg speed. Both were
# found by sweeping the parameters and recording which class each produced, not
# by reasoning backwards from the thresholds -- so these are observations of
# production behaviour rather than restatements of the configuration.


def _shaped_stream(
    dip: float, rally_step: float, quiet: int = 14
) -> tuple[NormalizedCandle, ...]:
    rows = [("105", "105.2", "104.8", "105")] * quiet
    rows.append(("105", "105.1", f"{dip:.2f}", f"{dip + 0.3:.2f}"))
    price = dip + 0.3
    for _ in range(6):
        nxt = price + rally_step
        rows.append(
            (f"{price:.2f}", f"{nxt + 0.1:.2f}", f"{price - 0.1:.2f}", f"{nxt:.2f}")
        )
        price = nxt
    return tuple(_candle(i, *row) for i, row in enumerate(rows))


_SHAPES = [
    # (dip, rally step, expected interaction, expected reaction, expected speed)
    (100.5, 0.3, "PARTIAL_ENTRY", "STANDARD_REACTION", "SLOW_OR_UNCLEAR"),
    (100.5, 0.5, "PARTIAL_ENTRY", "STRONG_REACTION", "FAST"),
    (100.5, 0.7, "PARTIAL_ENTRY", "STRONG_REACTION", "STRONG_FAST"),
    (100.0, 0.5, "FAR_BOUNDARY_TOUCH", "STRONG_REACTION", "FAST"),
    (99.97, 0.7, "CONTROLLED_OVERSHOOT", "STRONG_REACTION", "STRONG_FAST"),
    (99.90, 0.3, "EXCESSIVE_OVERSHOOT", None, None),
]


@pytest.mark.parametrize(
    ("dip", "step", "interaction", "reaction", "speed"),
    _SHAPES,
    ids=[s[2] + "-" + str(s[3]) for s in _SHAPES],
)
def test_shaped_streams_every_prefix(
    dip: float, step: float, interaction: str, reaction: str | None, speed: str | None
) -> None:
    candles = _shaped_stream(dip, step)
    pois = (_poi(7, PoiDirection.BULLISH, "101", "100", 12),)
    evidence = (_evidence_for(pois[0], 2),)
    for cut in range(1, len(candles) + 1):
        _compare(candles[:cut], pois, evidence)

    state = _compare(candles, pois, evidence).current_btmm_states[0]
    assert state.interaction_class.value == interaction
    assert (
        state.reaction_classification.value if state.reaction_classification else None
    ) == reaction
    assert (
        state.reaction_speed_classification.value
        if state.reaction_speed_classification
        else None
    ) == speed


@pytest.mark.parametrize("source", ["HYBRID_REVIEWED", "RULE_BASED_REVIEWED"])
def test_every_approved_liquidity_source_every_prefix(source: str) -> None:
    """All three approved reviewed sources must round-trip onto the state, so a
    confirmed record always names the review it actually rested on."""
    from btmm_ai_scanner.btmm.enums import BtmmEvidenceSource

    candles = _confirming_stream()
    pois = (_confirming_poi(),)
    base = _evidence_for(pois[0], 2)
    evidence = (
        base.model_copy(update={"liquidity_event_source": BtmmEvidenceSource(source)}),
    )
    for cut in range(1, len(candles) + 1):
        _compare(candles[:cut], pois, evidence)
    state = _compare(candles, pois, evidence).current_btmm_states[0]
    assert state.liquidity_evidence_source.value == source
    assert state.primary_state is BtmmLifecycleStatus.BTMM_CONFIRMED


def test_liquidity_review_pending_is_reachable_on_a_transition() -> None:
    """LIQUIDITY_REVIEW_PENDING is transient: it is carried on the BLOCKED
    transition emitted at the reaction close and cleared when the evidence bar
    resolves, so it never appears on a final state. Asserting it only at state
    level would have reported it as unreachable."""
    from btmm_ai_scanner.btmm.enums import BtmmBlockedReason

    candles = _confirming_stream()
    pois = (_confirming_poi(),)
    result = _compare(candles, pois, (_shaped_evidence(pois[0], 22),))
    reasons = {
        t.blocked_reason
        for t in result.btmm_lifecycle_transitions
        if t.blocked_reason is not None
    }
    assert BtmmBlockedReason.LIQUIDITY_REVIEW_PENDING in reasons


# --------------------------------------------------------------------------
# The two coverage figures, asserted rather than described
# --------------------------------------------------------------------------
#
# ENGINE_REACHABLE_COVERAGE and NO_EVIDENCE_RUNTIME_REACHABLE_COVERAGE are
# reported separately in the P4 closure and are never summed. Layer B is
# EXPECTED to be the smaller set: confirmation, the four evidence-driven
# cancellations and every blocked reason are unreachable without reviewed
# evidence, and that absence is the contract working, not a shortfall.
#
# Both are pinned here so the numbers in the report are produced by running the
# engine rather than by counting enum members.


def _evidence_scenarios() -> list[Any]:
    from btmm_ai_scanner.btmm.configuration import BtmmConfiguration
    from btmm_ai_scanner.btmm.enums import (
        BtmmContextAlignmentStatus,
        BtmmSessionStatus,
        BtmmVolumePillarStatus,
    )

    out: list[Any] = []
    for seed in range(6):
        candles = _stream(seed, 46)
        pois = _pois()
        out.append(
            _run_oracle(candles, pois, tuple(_evidence_for(p, 8) for p in pois), ())
        )
        out.append(
            _run_oracle(candles, pois, tuple(_evidence_for(p, 44) for p in pois), ())
        )
        out.append(
            _run_oracle(
                candles,
                pois,
                tuple(_evidence_for(p, 8, liquidity_present=False) for p in pois),
                (),
            )
        )
        genuine = tuple(
            _poi_transition(
                p, PoiLifecycleTransitionType.GENUINE_INVALIDATION_CONFIRMED, 20, n
            )
            for n, p in enumerate(pois)
        )
        out.append(
            _run_oracle(
                candles, pois, tuple(_evidence_for(p, 8) for p in pois), genuine
            )
        )

    candles = _confirming_stream()
    pois = (_confirming_poi(),)
    variants: list[dict[str, Any]] = [
        {},
        {"market_direction": BtmmContextAlignmentStatus.MISALIGNED},
        {"session": BtmmSessionStatus.INACTIVE},
        {"volume": BtmmVolumePillarStatus.FAILS},
        {"market_direction": BtmmContextAlignmentStatus.UNKNOWN},
        {"volume": BtmmVolumePillarStatus.MISSING_DATA},
        {"volume": BtmmVolumePillarStatus.UNRESOLVED},
    ]
    for variant in variants:
        out.append(
            _run_oracle(candles, pois, (_shaped_evidence(pois[0], 2, **variant),), ())
        )
    out.append(_run_oracle(candles, pois, (_shaped_evidence(pois[0], 22),), ()))
    out.append(
        _run_oracle(
            candles,
            pois,
            (
                _shaped_evidence(
                    pois[0], 22, market_direction=BtmmContextAlignmentStatus.UNKNOWN
                ),
            ),
            (),
        )
    )
    out.append(
        _run_oracle(
            candles,
            pois,
            (_shaped_evidence(pois[0], 2),),
            (),
            BtmmConfiguration(
                minimum_price_tick=Decimal("0.01"),
                formation_timeframes=frozenset({Timeframe.M5}),
                supporting_only_timeframes=frozenset({Timeframe.M1, Timeframe.M15}),
            ),
        )
    )
    for dip, step, _ic, _rc, _sp in _SHAPES:
        shaped = _shaped_stream(dip, step)
        shaped_pois = (_poi(7, PoiDirection.BULLISH, "101", "100", 12),)
        out.append(
            _run_oracle(shaped, shaped_pois, (_evidence_for(shaped_pois[0], 2),), ())
        )
    return out


def _no_evidence_scenarios() -> list[Any]:
    out: list[Any] = []
    for seed in range(6):
        candles = _stream(seed, 46)
        pois = _pois()
        out.append(_run_oracle(candles, pois, (), ()))
        false_inv = tuple(
            _poi_transition(
                p, PoiLifecycleTransitionType.FALSE_INVALIDATION_CONFIRMED, 12, n
            )
            for n, p in enumerate(pois)
        )
        out.append(_run_oracle(candles, pois, (), false_inv))
    candles = _confirming_stream()
    pois = (_confirming_poi(),)
    out.append(_run_oracle(candles, pois, (), ()))
    out.append(
        _run_oracle(
            candles,
            pois,
            (),
            (
                _poi_transition(
                    pois[0],
                    PoiLifecycleTransitionType.FALSE_INVALIDATION_CONFIRMED,
                    15,
                    40,
                ),
            ),
        )
    )
    out.append(
        _run_oracle(candles, (_poi(9, PoiDirection.BULLISH, "101", "100", 40),), (), ())
    )
    for dip, step, _ic, _rc, _sp in _SHAPES:
        shaped_pois = (_poi(7, PoiDirection.BULLISH, "101", "100", 12),)
        out.append(_run_oracle(_shaped_stream(dip, step), shaped_pois, (), ()))
    return out


def _reached(results: list[Any]) -> dict[str, set[str]]:
    out: dict[str, set[str]] = {
        name: set()
        for name in (
            "status",
            "transition",
            "interaction",
            "reaction",
            "speed",
            "cancel",
            "blocked",
            "stage",
            "liquidity_location",
        )
    }
    for result in results:
        for state in result.current_btmm_states:
            out["status"].add(state.primary_state.value)
            if state.formation_stage:
                out["stage"].add(state.formation_stage.value)
            if state.interaction_class:
                out["interaction"].add(state.interaction_class.value)
            if state.reaction_classification:
                out["reaction"].add(state.reaction_classification.value)
            if state.reaction_speed_classification:
                out["speed"].add(state.reaction_speed_classification.value)
            if state.cancellation_reason:
                out["cancel"].add(state.cancellation_reason.value)
            if state.liquidity_location:
                out["liquidity_location"].add(state.liquidity_location.value)
        for transition in result.btmm_lifecycle_transitions:
            out["transition"].add(transition.transition_type.value)
            if transition.blocked_reason:
                out["blocked"].add(transition.blocked_reason.value)
    return out


def test_engine_reachable_coverage_is_complete() -> None:
    """Layer A reaches every PRODUCED member of every vocabulary.

    Denominators come from the produced subset recorded in
    `test_btmm_vocabulary_reachability.py`, not from `len(Enum)`.
    """
    reached = _reached(_evidence_scenarios() + _no_evidence_scenarios())
    assert reached["status"] == {
        "BTMM_CANDIDATE",
        "BTMM_FORMING",
        "BTMM_BLOCKED",
        "BTMM_CONFIRMED",
        "BTMM_CANCELLED",
    }
    assert len(reached["transition"]) == 15
    assert len(reached["cancel"]) == 8
    assert len(reached["blocked"]) == 4
    assert len(reached["stage"]) == 3
    assert len(reached["interaction"]) == 7
    assert len(reached["reaction"]) == 3
    assert len(reached["speed"]) == 3
    assert reached["liquidity_location"] == {"LIQUIDITY_AFTER_POI"}


def test_no_evidence_runtime_coverage_is_the_expected_subset() -> None:
    """Layer B: exactly what the TradingView runtime can reach.

    The absences are the point. Confirmation, every blocked reason and the four
    evidence-driven cancellations are unreachable without reviewed evidence, and
    this test fails if any of them ever becomes reachable -- which is what a
    change that quietly satisfies a reviewed gate would look like.
    """
    reached = _reached(_no_evidence_scenarios())

    assert reached["status"] == {"BTMM_CANDIDATE", "BTMM_FORMING", "BTMM_CANCELLED"}
    assert "BTMM_CONFIRMED" not in reached["status"]
    assert "BTMM_BLOCKED" not in reached["status"]
    assert reached["blocked"] == set()

    assert reached["cancel"] == {
        "INTERACTION_INELIGIBLE",
        "WEAK_REACTION",
        "REACTION_SPEED_FAILED",
        "NO_LIQUIDITY_EVIDENCE",
    }
    assert reached["transition"] == {
        "ENTERED_FORMING",
        "ACCURACY_GATE_CONFIRMED",
        "INTERACTION_INELIGIBLE",
        "REACTION_GATE_CONFIRMED",
        "WEAK_REACTION",
        "REACTION_SPEED_GATE_CONFIRMED",
        "REACTION_SPEED_FAILED",
        "NO_LIQUIDITY_EVIDENCE",
    }

    # The price-derived half of the engine is fully exercised without evidence:
    # every interaction class, reaction tier, speed class and stage is reachable.
    assert len(reached["interaction"]) == 7
    assert len(reached["reaction"]) == 3
    assert len(reached["speed"]) == 3
    assert len(reached["stage"]) == 3
    # Derived liquidity works in the runtime; it just never confirms anything.
    assert reached["liquidity_location"] == {"LIQUIDITY_AFTER_POI"}


# --------------------------------------------------------------------------
# Late discovery: semantic availability is not engine discovery
# --------------------------------------------------------------------------
#
# `analyze_btmm` walks a setup from its source POI's availability, whatever bar
# the POI was found on. Pine only learns a POI exists when P3 emits it, and the
# reference-zone family comes from a rolling S/R projection that can surface a
# zone many bars after its own confirmation. A setup created at discovery would
# skip every bar in between.
#
# This was not hypothetical. The first M15 atomic capture disagreed with
# production on exactly one of 956 setups: a resistance zone whose POI became
# available at bar 739 was not discovered until bar 892 -- 153 bars later -- and
# its POI was genuinely invalidated at bar 753, before the setup existed at all.
# Pine reported POI_REJECTED with no formation stage; production had already
# cancelled it INTERACTION_INELIGIBLE on an excessive overshoot at bar ~745.
#
# The engine therefore backfills a late-created setup over the bars it missed.
# These tests hold that equivalence, because the defect is invisible in any
# scenario where every setup exists from bar zero -- which is every synthetic
# scenario above.


def _model_run(
    candles: tuple[NormalizedCandle, ...],
    poi: PoiObservation,
    discover_at: int | None,
) -> list[M.PineState]:
    """Run the model, optionally creating the setup late and backfilling it."""
    engine = M.PineBtmmEngine(configuration=_CONFIG)
    atrs = compute_atr_series(candles, 14)
    pine_candles = [
        M.PineCandle(
            open=c.open,
            high=c.high,
            low=c.low,
            close=c.close,
            event_time=_ts(c.event_time_utc),
            availability_time=_ts(c.availability_time_utc),
        )
        for c in candles
    ]
    spec = M.PineSetupSpec(
        poi_key=str(poi.record_id),
        direction=(
            M.DIR_BULLISH if poi.direction == PoiDirection.BULLISH else M.DIR_BEARISH
        ),
        zone_top=poi.zone_top,
        zone_bottom=poi.zone_bottom,
        candidate_availability_time=_ts(poi.availability_time_utc),
        is_formation_timeframe=True,
    )

    created = discover_at is None
    if created:
        engine.add_setup(spec)
    for index, pc in enumerate(pine_candles):
        if not created and index == discover_at:
            slot = engine.add_setup(spec)
            M.backfill(engine, slot, pine_candles, atrs, index)
            created = True
        if created:
            engine.advance(pc, atrs[index])
        else:
            # No setups yet: the registry is empty, so only the bar cursor moves.
            engine.total_count += 1
            engine.prev_close = pc.close
    _t, states = M.report(engine, {}, {}, {})
    return states


@pytest.mark.parametrize("discover_at", [1, 5, 14, 15, 16, 17, 18, 19])
def test_a_late_created_setup_backfills_to_the_same_state(discover_at: int) -> None:
    """Discovering the POI on bar N and backfilling must equal having had it all
    along -- for every N, including bars after the interaction and after the
    reaction window has closed."""
    candles = _confirming_stream()
    poi = _confirming_poi()
    assert _model_run(candles, poi, None) == _model_run(candles, poi, discover_at)


@pytest.mark.parametrize("seed", range(4))
@pytest.mark.parametrize("discover_at", [7, 23, 41])
def test_late_creation_equivalence_on_random_streams(
    seed: int, discover_at: int
) -> None:
    candles = _stream(seed, 46)
    poi = _poi(1, PoiDirection.BULLISH, "101.0", "100.0", 2)
    assert _model_run(candles, poi, None) == _model_run(candles, poi, discover_at)


def test_backfill_is_needed_at_all() -> None:
    """Guard the guard: if a late-created setup with NO backfill already matched,
    the tests above would be proving nothing."""
    candles = _confirming_stream()
    poi = _confirming_poi()

    engine = M.PineBtmmEngine(configuration=_CONFIG)
    atrs = compute_atr_series(candles, 14)
    pine_candles = [
        M.PineCandle(
            open=c.open,
            high=c.high,
            low=c.low,
            close=c.close,
            event_time=_ts(c.event_time_utc),
            availability_time=_ts(c.availability_time_utc),
        )
        for c in candles
    ]
    spec = M.PineSetupSpec(
        poi_key=str(poi.record_id),
        direction=M.DIR_BULLISH,
        zone_top=poi.zone_top,
        zone_bottom=poi.zone_bottom,
        candidate_availability_time=_ts(poi.availability_time_utc),
        is_formation_timeframe=True,
    )
    created = False
    for index, pc in enumerate(pine_candles):
        if not created and index == 17:  # after the interaction, no backfill
            engine.add_setup(spec)
            created = True
        if created:
            engine.advance(pc, atrs[index])
        else:
            engine.total_count += 1
            engine.prev_close = pc.close
    _t, without = M.report(engine, {}, {}, {})

    assert without != _model_run(candles, poi, None), (
        "a late-created setup without backfill must NOT already agree, or these "
        "tests would pass for the wrong reason"
    )


def test_backfill_skips_bars_at_or_before_the_candidate_availability() -> None:
    """The replay starts at the POI's own availability, not at bar zero: a bar
    whose availability does not exceed it cannot make the setup form."""
    candles = _confirming_stream()
    poi = _confirming_poi()  # becomes available at index 12
    states = _model_run(candles, poi, 19)
    assert len(states) == 1
    # Formation is driven by the first bar strictly after availability, which is
    # well after bar 0; if the backfill had replayed from bar 0 the setup would
    # have interacted with the quiet approach instead of the sweep.
    assert states[0].interaction_class != 0
