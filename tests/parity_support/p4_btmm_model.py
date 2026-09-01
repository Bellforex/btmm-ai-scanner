"""Pine-shaped transcription of the BTMM setup engine (P4).

Test/parity tooling only -- nothing in `src/` imports this, and it changes no
production semantics. `analyze_btmm` is always the oracle.

WHY A MODEL RATHER THAN A DIRECT PORT
-------------------------------------
`run_btmm_lifecycle` re-runs the whole cascade over `candles[0:]` on every
candle. Pine cannot: it sees one confirmed bar at a time and must not re-scan
history. Production already resolves this in `btmm/lifecycle_cursor.py`, whose
cursor reproduces the batch result one appended candle at a time and is proven
byte-identical at every prefix. That module -- not the batch walk -- is what
Pine ports.

What this file adds is the DATA SHAPE. The production cursor is a frozen
dataclass holding `NormalizedCandle` objects, `Decimal | None`, enum members and
UUIDs. Pine has none of those: it has parallel arrays of `int`/`float`/`bool`,
integer codes, and `na`. Transcribing straight from production to Pine would mix
an algorithmic port with a representation port and make any divergence
ambiguous. So this model holds the algorithm fixed and changes only the
representation:

* one flat parallel array per field, indexed by setup slot, exactly as the Pine
  registry will be;
* `-1` for an absent index and `None` for `na`, never `Optional[Decimal]`;
* integer codes for every enum, mirroring the `C_BTMM_*` Pine constants;
* no per-setup object, no dict keyed by record, no comprehension over history.

Numerics stay `Decimal` because the oracle is `Decimal`; Pine's float behaviour
is absorbed by the tick-normalised digest, exactly as in P2 and P3.

WHAT IS DELIBERATELY NOT MODELLED
---------------------------------
Record identity. Pine cannot compute Python's UUIDs, so the model reports the
setup's source POI identity and lets the digest address records semantically --
the P3 AD-1 rule, unchanged.

EVIDENCE
--------
The model accepts reviewed evidence so that Layer A (the complete engine,
including `BTMM_CONFIRMED`) is exercised and proven. The TradingView runtime
supplies none, which is Layer B and reaches `BTMM_CANCELLED /
NO_LIQUIDITY_EVIDENCE`. Both modes are proven against the same oracle; neither
is allowed to imitate the other.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from decimal import Decimal

from btmm_ai_scanner.btmm.configuration import BtmmConfiguration
from btmm_ai_scanner.btmm.enums import (
    BtmmBlockedReason,
    BtmmCancellationReason,
    BtmmContextAlignmentStatus,
    BtmmDirection,
    BtmmEvidenceSource,
    BtmmFormationStage,
    BtmmGateStatus,
    BtmmInteractionClass,
    BtmmLifecycleStatus,
    BtmmLifecycleTransitionType,
    BtmmLiquidityEvidenceStatus,
    BtmmLiquidityLocation,
    BtmmReactionClassification,
    BtmmSessionStatus,
    BtmmVolumePillarStatus,
)
from btmm_ai_scanner.measurements.legs import LegSpeedClassification

_ZERO = Decimal("0")
_ONE = Decimal("1")
_TWO = Decimal("2")

# ---------------------------------------------------------------------------
# Integer code vocabulary -- mirrors the C_BTMM_* constants in the Pine port.
# Only PRODUCED members are given codes; reserved vocabulary is not modelled
# (see test_btmm_vocabulary_reachability.py for the inventory).
# ---------------------------------------------------------------------------

ST_NA = 0
ST_CANDIDATE = 1
ST_FORMING = 2
ST_BLOCKED = 3
ST_CONFIRMED = 4
ST_CANCELLED = 5

STAGE_NA = 0
STAGE_POI_INTERACTION = 4
STAGE_REACTION_MONITORING = 5
STAGE_FINAL_GATE = 6

GATE_PENDING = 0
GATE_PASS = 1
GATE_FAIL = 2

IC_EDGE_TOUCH = 1
IC_PARTIAL_ENTRY = 2
IC_DEEP_ENTRY = 3
IC_FAR_BOUNDARY_TOUCH = 4
IC_CONTROLLED_OVERSHOOT = 5
IC_EXCESSIVE_OVERSHOOT = 6
IC_NONCANONICAL_SIDE = 9

#: `interaction.ELIGIBLE_INTERACTION_CLASSES`, as codes.
ELIGIBLE_INTERACTION_CODES = frozenset(
    {
        IC_EDGE_TOUCH,
        IC_PARTIAL_ENTRY,
        IC_DEEP_ENTRY,
        IC_FAR_BOUNDARY_TOUCH,
        IC_CONTROLLED_OVERSHOOT,
    }
)

RC_WEAK = 3
RC_STANDARD = 4
RC_STRONG = 5

SPD_SLOW_OR_UNCLEAR = 1
SPD_FAST = 2
SPD_STRONG_FAST = 3

CTX_PENDING = 0
CTX_ALIGNED = 1
CTX_MISALIGNED = 2
CTX_UNKNOWN = 3

SESS_PENDING = 0
SESS_ACTIVE = 1
SESS_INACTIVE = 2
SESS_UNKNOWN = 3

VOL_PENDING = 0
VOL_SUPPORTS = 1
VOL_FAILS = 2
VOL_MISSING_DATA = 3
VOL_UNRESOLVED = 4

LQS_PENDING = 0
LQS_PRESENT = 1

LQL_NA = 0
LQL_AFTER_POI = 3

SRC_NA = 0
SRC_EXPERT_LABELLED = 1
SRC_RULE_BASED = 2
SRC_HYBRID_REVIEWED = 4
SRC_RULE_BASED_REVIEWED = 5

CANCEL_NA = 0
CANCEL_POI_REJECTED = 1
CANCEL_INTERACTION_INELIGIBLE = 2
CANCEL_WEAK_REACTION = 3
CANCEL_REACTION_SPEED_FAILED = 4
CANCEL_CONTEXT_REJECTED = 5
CANCEL_SESSION_INACTIVE = 6
CANCEL_VOLUME_PILLAR_FAILED = 7
CANCEL_NO_LIQUIDITY_EVIDENCE = 8

BLOCK_NA = 0
BLOCK_CONTEXT_UNKNOWN = 1
BLOCK_LIQUIDITY_REVIEW_PENDING = 2
BLOCK_VOLUME_REVIEW_PENDING = 3
BLOCK_FORMATION_TF_NOT_CONFIRMED = 4

TR_ENTERED_FORMING = 1
TR_ACCURACY_GATE_CONFIRMED = 2
TR_INTERACTION_INELIGIBLE = 3
TR_REACTION_GATE_CONFIRMED = 4
TR_WEAK_REACTION = 5
TR_REACTION_SPEED_GATE_CONFIRMED = 6
TR_REACTION_SPEED_FAILED = 7
TR_BLOCKED = 8
TR_RESUMED_FORMING = 9
TR_CONFIRMED = 10
TR_POI_REJECTED = 11
TR_CONTEXT_REJECTED = 12
TR_SESSION_INACTIVE = 13
TR_VOLUME_PILLAR_FAILED = 14
TR_NO_LIQUIDITY_EVIDENCE = 15

DIR_BULLISH = 1
DIR_BEARISH = -1


# --- code <-> enum tables, used only to compare against the oracle ----------

STATUS_BY_CODE: dict[int, BtmmLifecycleStatus] = {
    ST_CANDIDATE: BtmmLifecycleStatus.BTMM_CANDIDATE,
    ST_FORMING: BtmmLifecycleStatus.BTMM_FORMING,
    ST_BLOCKED: BtmmLifecycleStatus.BTMM_BLOCKED,
    ST_CONFIRMED: BtmmLifecycleStatus.BTMM_CONFIRMED,
    ST_CANCELLED: BtmmLifecycleStatus.BTMM_CANCELLED,
}
STAGE_BY_CODE: dict[int, BtmmFormationStage | None] = {
    STAGE_NA: None,
    STAGE_POI_INTERACTION: BtmmFormationStage.POI_INTERACTION,
    STAGE_REACTION_MONITORING: BtmmFormationStage.REACTION_MONITORING,
    STAGE_FINAL_GATE: BtmmFormationStage.FINAL_GATE_EVALUATION,
}
GATE_BY_CODE: dict[int, BtmmGateStatus] = {
    GATE_PENDING: BtmmGateStatus.PENDING,
    GATE_PASS: BtmmGateStatus.PASS,
    GATE_FAIL: BtmmGateStatus.FAIL,
}
INTERACTION_BY_CODE: dict[int, BtmmInteractionClass | None] = {
    0: None,
    IC_EDGE_TOUCH: BtmmInteractionClass.EDGE_TOUCH,
    IC_PARTIAL_ENTRY: BtmmInteractionClass.PARTIAL_ENTRY,
    IC_DEEP_ENTRY: BtmmInteractionClass.DEEP_ENTRY,
    IC_FAR_BOUNDARY_TOUCH: BtmmInteractionClass.FAR_BOUNDARY_TOUCH,
    IC_CONTROLLED_OVERSHOOT: BtmmInteractionClass.CONTROLLED_OVERSHOOT,
    IC_EXCESSIVE_OVERSHOOT: BtmmInteractionClass.EXCESSIVE_OVERSHOOT,
    IC_NONCANONICAL_SIDE: BtmmInteractionClass.NONCANONICAL_SIDE_INTERACTION,
}
REACTION_BY_CODE: dict[int, BtmmReactionClassification | None] = {
    0: None,
    RC_WEAK: BtmmReactionClassification.WEAK_REACTION,
    RC_STANDARD: BtmmReactionClassification.STANDARD_REACTION,
    RC_STRONG: BtmmReactionClassification.STRONG_REACTION,
}
SPEED_BY_CODE: dict[int, LegSpeedClassification | None] = {
    0: None,
    SPD_SLOW_OR_UNCLEAR: LegSpeedClassification.SLOW_OR_UNCLEAR,
    SPD_FAST: LegSpeedClassification.FAST,
    SPD_STRONG_FAST: LegSpeedClassification.STRONG_FAST,
}
SPEED_CODE: dict[LegSpeedClassification, int] = {
    v: k for k, v in SPEED_BY_CODE.items() if v is not None
}
CONTEXT_BY_CODE: dict[int, BtmmContextAlignmentStatus] = {
    CTX_PENDING: BtmmContextAlignmentStatus.PENDING,
    CTX_ALIGNED: BtmmContextAlignmentStatus.ALIGNED,
    CTX_MISALIGNED: BtmmContextAlignmentStatus.MISALIGNED,
    CTX_UNKNOWN: BtmmContextAlignmentStatus.UNKNOWN,
}
CONTEXT_CODE = {v: k for k, v in CONTEXT_BY_CODE.items()}
SESSION_BY_CODE: dict[int, BtmmSessionStatus] = {
    SESS_PENDING: BtmmSessionStatus.PENDING,
    SESS_ACTIVE: BtmmSessionStatus.ACTIVE,
    SESS_INACTIVE: BtmmSessionStatus.INACTIVE,
    SESS_UNKNOWN: BtmmSessionStatus.UNKNOWN,
}
SESSION_CODE = {v: k for k, v in SESSION_BY_CODE.items()}
VOLUME_BY_CODE: dict[int, BtmmVolumePillarStatus] = {
    VOL_PENDING: BtmmVolumePillarStatus.PENDING,
    VOL_SUPPORTS: BtmmVolumePillarStatus.SUPPORTS,
    VOL_FAILS: BtmmVolumePillarStatus.FAILS,
    VOL_MISSING_DATA: BtmmVolumePillarStatus.MISSING_DATA,
    VOL_UNRESOLVED: BtmmVolumePillarStatus.UNRESOLVED,
}
VOLUME_CODE = {v: k for k, v in VOLUME_BY_CODE.items()}
LIQUIDITY_STATUS_BY_CODE: dict[int, BtmmLiquidityEvidenceStatus] = {
    LQS_PENDING: BtmmLiquidityEvidenceStatus.PENDING,
    LQS_PRESENT: BtmmLiquidityEvidenceStatus.PRESENT,
}
LIQUIDITY_STATUS_CODE = {v: k for k, v in LIQUIDITY_STATUS_BY_CODE.items()}
LIQUIDITY_LOCATION_BY_CODE: dict[int, BtmmLiquidityLocation | None] = {
    LQL_NA: None,
    LQL_AFTER_POI: BtmmLiquidityLocation.LIQUIDITY_AFTER_POI,
}
EVIDENCE_SOURCE_BY_CODE: dict[int, BtmmEvidenceSource | None] = {
    SRC_NA: None,
    SRC_EXPERT_LABELLED: BtmmEvidenceSource.EXPERT_LABELLED,
    SRC_RULE_BASED: BtmmEvidenceSource.RULE_BASED,
    SRC_HYBRID_REVIEWED: BtmmEvidenceSource.HYBRID_REVIEWED,
    SRC_RULE_BASED_REVIEWED: BtmmEvidenceSource.RULE_BASED_REVIEWED,
}
EVIDENCE_SOURCE_CODE = {
    v: k for k, v in EVIDENCE_SOURCE_BY_CODE.items() if v is not None
}
CANCEL_BY_CODE: dict[int, BtmmCancellationReason | None] = {
    CANCEL_NA: None,
    CANCEL_POI_REJECTED: BtmmCancellationReason.POI_REJECTED,
    CANCEL_INTERACTION_INELIGIBLE: BtmmCancellationReason.INTERACTION_INELIGIBLE,
    CANCEL_WEAK_REACTION: BtmmCancellationReason.WEAK_REACTION,
    CANCEL_REACTION_SPEED_FAILED: BtmmCancellationReason.REACTION_SPEED_FAILED,
    CANCEL_CONTEXT_REJECTED: BtmmCancellationReason.CONTEXT_REJECTED,
    CANCEL_SESSION_INACTIVE: BtmmCancellationReason.SESSION_INACTIVE,
    CANCEL_VOLUME_PILLAR_FAILED: BtmmCancellationReason.VOLUME_PILLAR_FAILED,
    CANCEL_NO_LIQUIDITY_EVIDENCE: BtmmCancellationReason.NO_LIQUIDITY_EVIDENCE,
}
BLOCK_BY_CODE: dict[int, BtmmBlockedReason | None] = {
    BLOCK_NA: None,
    BLOCK_CONTEXT_UNKNOWN: BtmmBlockedReason.CONTEXT_UNKNOWN,
    BLOCK_LIQUIDITY_REVIEW_PENDING: BtmmBlockedReason.LIQUIDITY_REVIEW_PENDING,
    BLOCK_VOLUME_REVIEW_PENDING: BtmmBlockedReason.VOLUME_REVIEW_PENDING,
    BLOCK_FORMATION_TF_NOT_CONFIRMED: (
        BtmmBlockedReason.FORMATION_TIMEFRAME_NOT_CONFIRMED
    ),
}
TRANSITION_BY_CODE: dict[int, BtmmLifecycleTransitionType] = {
    TR_ENTERED_FORMING: BtmmLifecycleTransitionType.ENTERED_FORMING,
    TR_ACCURACY_GATE_CONFIRMED: BtmmLifecycleTransitionType.ACCURACY_GATE_CONFIRMED,
    TR_INTERACTION_INELIGIBLE: BtmmLifecycleTransitionType.INTERACTION_INELIGIBLE,
    TR_REACTION_GATE_CONFIRMED: BtmmLifecycleTransitionType.REACTION_GATE_CONFIRMED,
    TR_WEAK_REACTION: BtmmLifecycleTransitionType.WEAK_REACTION,
    TR_REACTION_SPEED_GATE_CONFIRMED: (
        BtmmLifecycleTransitionType.REACTION_SPEED_GATE_CONFIRMED
    ),
    TR_REACTION_SPEED_FAILED: BtmmLifecycleTransitionType.REACTION_SPEED_FAILED,
    TR_BLOCKED: BtmmLifecycleTransitionType.BLOCKED,
    TR_RESUMED_FORMING: BtmmLifecycleTransitionType.RESUMED_FORMING,
    TR_CONFIRMED: BtmmLifecycleTransitionType.CONFIRMED,
    TR_POI_REJECTED: BtmmLifecycleTransitionType.POI_REJECTED,
    TR_CONTEXT_REJECTED: BtmmLifecycleTransitionType.CONTEXT_REJECTED,
    TR_SESSION_INACTIVE: BtmmLifecycleTransitionType.SESSION_INACTIVE,
    TR_VOLUME_PILLAR_FAILED: BtmmLifecycleTransitionType.VOLUME_PILLAR_FAILED,
    TR_NO_LIQUIDITY_EVIDENCE: BtmmLifecycleTransitionType.NO_LIQUIDITY_EVIDENCE,
}
DIRECTION_BY_CODE: dict[int, BtmmDirection] = {
    DIR_BULLISH: BtmmDirection.BULLISH_BTMM,
    DIR_BEARISH: BtmmDirection.BEARISH_BTMM,
}


# ---------------------------------------------------------------------------
# Pine-shaped inputs
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PineCandle:
    """One confirmed bar, as Pine sees it: four prices plus the two times."""

    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    event_time: int
    availability_time: int


@dataclass(frozen=True)
class PineSetupSpec:
    """A BTMM-eligible source POI, reduced to what the engine reads.

    `poi_key` stands in for the POI's record identity: Pine addresses POIs by
    the P3 identity triple, never by UUID.
    """

    poi_key: str
    direction: int
    zone_top: Decimal
    zone_bottom: Decimal
    candidate_availability_time: int
    is_formation_timeframe: bool


@dataclass(frozen=True)
class PineEvidence:
    """Reviewed evidence, in codes. Supplied by the caller; never derived."""

    poi_key: str
    availability_time: int
    market_direction: int
    analytical_framework: int
    session: int
    liquidity_status: int
    volume: int
    liquidity_source: int


@dataclass(frozen=True)
class PineTransition:
    """One emitted BTMM lifecycle transition."""

    poi_key: str
    code: int
    blocked_reason: int
    event_time: int
    availability_time: int


@dataclass(frozen=True)
class PineState:
    """The reported state of one setup -- the Pine-visible subset of
    `CurrentBtmmState`, excluding identity and provenance fields Pine cannot
    compute."""

    poi_key: str
    direction: int
    primary_state: int
    formation_stage: int
    market_direction: int
    analytical_framework: int
    session: int
    accuracy_gate: int
    interaction_class: int
    reaction_gate: int
    reaction_class: int
    reaction_speed_gate: int
    reaction_speed_class: int
    formation_tf_gate: int
    volume: int
    liquidity_status: int
    liquidity_location: int
    liquidity_source: int
    reviewed_evidence_time: int
    cancellation_reason: int
    blocked_reason: int
    availability_time: int


# ---------------------------------------------------------------------------
# Mutable per-setup fields (the `_StateFields` analogue, all int-coded)
# ---------------------------------------------------------------------------


@dataclass
class _Fields:
    primary_state: int = ST_CANDIDATE
    formation_stage: int = STAGE_NA
    market_direction: int = CTX_PENDING
    analytical_framework: int = CTX_PENDING
    session: int = SESS_PENDING
    accuracy_gate: int = GATE_PENDING
    interaction_class: int = 0
    reaction_gate: int = GATE_PENDING
    reaction_class: int = 0
    reaction_speed_gate: int = GATE_PENDING
    reaction_speed_class: int = 0
    formation_tf_gate: int = GATE_PENDING
    volume: int = VOL_PENDING
    liquidity_status: int = LQS_PENDING
    liquidity_location: int = LQL_NA
    liquidity_source: int = SRC_NA
    reviewed_evidence_time: int = -1
    cancellation_reason: int = CANCEL_NA
    blocked_reason: int = BLOCK_NA
    availability_time: int = -1

    def copy(self) -> _Fields:
        return _Fields(**vars(self))


@dataclass
class _Step:
    code: int  # 0 = a silent field update, not an emitted transition
    blocked_reason: int
    event_time: int
    availability_time: int
    fields: _Fields


# ---------------------------------------------------------------------------
# Leg measurement, transcribed for the Pine shape
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class _Leg:
    reference_atr: Decimal
    directional_efficiency: Decimal
    directional_candle_share: Decimal
    classification: int


def _median(values: Sequence[Decimal]) -> Decimal:
    if len(values) == 0:
        return _ZERO
    ordered = sorted(values)
    mid = len(ordered) // 2
    if len(ordered) % 2 == 1:
        return ordered[mid]
    return (ordered[mid - 1] + ordered[mid]) / _TWO


def _measure_leg(
    candles: Sequence[PineCandle],
    atrs: Sequence[Decimal | None],
    is_bullish: bool,
    configuration: BtmmConfiguration,
) -> _Leg:
    """Transcription of `measurements.legs.measure_leg`.

    Verified against the source rather than inferred. Four details a plausible
    guess gets wrong, and each of which changes the speed gate:

    * `reference_atr` is the MEDIAN of the known ATRs, not their mean, and only
      `None` is filtered -- a zero ATR still participates;
    * the leg distance is `abs(last.close - first.open)`, not the excursion to
      the favourable extreme;
    * directional efficiency divides that by the summed high-low path;
    * the directional-candle test is inclusive (`>=` / `<=`), so a doji counts.
    """
    bar_count = len(candles)
    if bar_count == 0:
        return _Leg(_ZERO, _ZERO, _ZERO, SPD_SLOW_OR_UNCLEAR)

    net = abs(candles[-1].close - candles[0].open)
    reference_atr = _median([a for a in atrs if a is not None])
    path = sum((c.high - c.low for c in candles), _ZERO)

    directional = 0
    for candle in candles:
        if is_bullish:
            if candle.close >= candle.open:
                directional += 1
        elif candle.close <= candle.open:
            directional += 1
    share = Decimal(directional) / Decimal(bar_count)

    if reference_atr == _ZERO or path == _ZERO:
        return _Leg(reference_atr, _ZERO, share, SPD_SLOW_OR_UNCLEAR)

    speed = net / (Decimal(bar_count) * reference_atr)
    efficiency = net / path

    classification = SPD_SLOW_OR_UNCLEAR
    if (
        speed >= configuration.reaction_speed_strong_fast_normalized_speed_per_bar
        and efficiency
        >= configuration.reaction_speed_strong_fast_directional_efficiency
        and share >= configuration.reaction_speed_strong_fast_directional_candle_share
    ):
        classification = SPD_STRONG_FAST
    elif (
        speed >= configuration.reaction_speed_fast_normalized_speed_per_bar
        and efficiency >= configuration.reaction_speed_fast_directional_efficiency
        and share >= configuration.reaction_speed_fast_directional_candle_share
    ):
        classification = SPD_FAST

    return _Leg(reference_atr, efficiency, share, classification)


# ---------------------------------------------------------------------------
# Interaction classification (one candle at a time)
# ---------------------------------------------------------------------------


def _tolerance(
    reference_atr: Decimal,
    zone_height: Decimal,
    min_tick: Decimal,
    atr_multiplier: Decimal,
    height_multiplier: Decimal,
) -> Decimal:
    return max(
        _TWO * min_tick,
        min(atr_multiplier * reference_atr, height_multiplier * zone_height),
    )


def _classify_interaction(
    prev_close: Decimal | None,
    candle: PineCandle,
    atr_value: Decimal | None,
    zone_top: Decimal,
    zone_bottom: Decimal,
    direction: int,
    configuration: BtmmConfiguration,
) -> int:
    """`find_first_interaction` reduced to the single-candle test Pine performs.

    Production scans forward from a start index; the cursor already narrows that
    to "test this one candle", which is what Pine does natively. `prev_close` is
    None only on the very first bar, where production falls back to the candle's
    own open for the canonical-side test.
    """
    if not (candle.low <= zone_top and candle.high >= zone_bottom):
        return 0

    zone_height = zone_top - zone_bottom
    fallback = candle.high - candle.low
    reference_atr = atr_value if atr_value is not None and atr_value > 0 else fallback

    prior_reference_price = prev_close if prev_close is not None else candle.open
    is_bullish = direction == DIR_BULLISH
    canonical_side = (
        prior_reference_price >= zone_top
        if is_bullish
        else prior_reference_price <= zone_bottom
    )
    if not canonical_side:
        return IC_NONCANONICAL_SIDE

    overshoot_tolerance = _tolerance(
        reference_atr,
        zone_height,
        configuration.minimum_price_tick,
        configuration.interaction_overshoot_tolerance_atr_multiplier,
        configuration.interaction_overshoot_tolerance_zone_height_multiplier,
    )

    raw_penetration = zone_top - candle.low if is_bullish else candle.high - zone_bottom

    if raw_penetration >= zone_height:
        overshoot_distance = raw_penetration - zone_height
        penetration_ratio = _ONE
    else:
        overshoot_distance = _ZERO
        penetration_ratio = raw_penetration / zone_height if zone_height > 0 else _ZERO

    if overshoot_distance > overshoot_tolerance:
        return IC_EXCESSIVE_OVERSHOOT
    if overshoot_distance > 0:
        return IC_CONTROLLED_OVERSHOOT
    if penetration_ratio >= 1:
        return IC_FAR_BOUNDARY_TOUCH
    if (
        penetration_ratio
        > configuration.interaction_partial_entry_max_penetration_ratio
    ):
        return IC_DEEP_ENTRY
    if penetration_ratio > configuration.interaction_edge_touch_max_penetration_ratio:
        return IC_PARTIAL_ENTRY
    return IC_EDGE_TOUCH


# ---------------------------------------------------------------------------
# Reaction window evaluation (over the filled bounded window)
# ---------------------------------------------------------------------------


def _evaluate_reaction_window(
    window: Sequence[PineCandle],
    window_atrs: Sequence[Decimal | None],
    reaction_anchor: Decimal,
    far_boundary: Decimal,
    zone_height: Decimal,
    direction: int,
    configuration: BtmmConfiguration,
) -> tuple[int, int]:
    """Transcription of `evaluate_reaction_window`, returning (tier, speed).

    Two details that a summary of the rule loses: the tier is the HIGHEST reached
    over every prefix k = 1..window_bars, not the tier at the close; and the
    speed leg is measured to the bar of maximum favourable excursion, which is
    generally not the window's last bar.
    """
    is_bullish = direction == DIR_BULLISH
    window_bars = configuration.reaction_window_bars
    highest_tier = 0

    for k in range(1, window_bars + 1):
        sub = window[:k]
        sub_atrs = window_atrs[:k]
        leg = _measure_leg(sub, sub_atrs, is_bullish, configuration)
        favorable = max(c.high for c in sub) if is_bullish else min(c.low for c in sub)
        reaction_mfe = abs(favorable - reaction_anchor)
        atr_reaction_ratio = (
            reaction_mfe / leg.reference_atr if leg.reference_atr > 0 else _ZERO
        )
        clearance = favorable - far_boundary if is_bullish else far_boundary - favorable
        clearance_ratio = clearance / zone_height if zone_height > 0 else _ZERO

        standard = (
            atr_reaction_ratio >= configuration.reaction_standard_atr_ratio
            and clearance_ratio >= configuration.reaction_standard_zone_clearance_ratio
            and leg.directional_efficiency
            >= configuration.reaction_standard_directional_efficiency
            and leg.directional_candle_share
            >= configuration.reaction_standard_directional_candle_share
        )
        strong = (
            atr_reaction_ratio >= configuration.reaction_strong_atr_ratio
            and clearance_ratio >= configuration.reaction_strong_zone_clearance_ratio
            and leg.directional_efficiency
            >= configuration.reaction_strong_directional_efficiency
            and leg.directional_candle_share
            >= configuration.reaction_strong_directional_candle_share
            and leg.classification in (SPD_FAST, SPD_STRONG_FAST)
        )
        if strong:
            highest_tier = max(highest_tier, 2)
        if standard:
            highest_tier = max(highest_tier, 1)

    tier_code = (
        RC_STRONG
        if highest_tier == 2
        else (RC_STANDARD if highest_tier == 1 else RC_WEAK)
    )

    full = window[:window_bars]
    best_offset = 0
    best_extreme: Decimal | None = None
    for offset, candle in enumerate(full):
        candidate = candle.high if is_bullish else candle.low
        better = best_extreme is None or (
            candidate > best_extreme if is_bullish else candidate < best_extreme
        )
        if better:
            best_extreme = candidate
            best_offset = offset

    speed_leg = _measure_leg(
        window[: best_offset + 1],
        window_atrs[: best_offset + 1],
        is_bullish,
        configuration,
    )
    return tier_code, speed_leg.classification


# ---------------------------------------------------------------------------
# The engine: a persistent parallel-array registry advanced one bar at a time
# ---------------------------------------------------------------------------


@dataclass
class PineBtmmEngine:
    """The Pine registry, one flat array per field.

    Slot `i` is one BTMM setup, created when its source POI becomes eligible and
    never removed -- the same append-only discipline P3's POI registry uses. The
    per-bar cost is one stage test per price-open setup; a setup whose price
    stages are all committed does no candle work at all.
    """

    configuration: BtmmConfiguration

    # immutable setup geometry
    key: list[str] = field(default_factory=list)
    direction: list[int] = field(default_factory=list)
    zone_top: list[Decimal] = field(default_factory=list)
    zone_bottom: list[Decimal] = field(default_factory=list)
    zone_height: list[Decimal] = field(default_factory=list)
    entry_boundary: list[Decimal] = field(default_factory=list)
    far_boundary: list[Decimal] = field(default_factory=list)
    candidate_avail: list[int] = field(default_factory=list)
    is_formation_tf: list[bool] = field(default_factory=list)

    # committed price-stage frontier (-1 = not yet reached)
    forming_idx: list[int] = field(default_factory=list)
    forming_event: list[int] = field(default_factory=list)
    forming_avail: list[int] = field(default_factory=list)
    interaction_idx: list[int] = field(default_factory=list)
    interaction_code: list[int] = field(default_factory=list)
    interaction_event: list[int] = field(default_factory=list)
    interaction_avail: list[int] = field(default_factory=list)
    running_anchor: list[Decimal | None] = field(default_factory=list)
    reaction_start_idx: list[int] = field(default_factory=list)
    reaction_anchor: list[Decimal | None] = field(default_factory=list)
    window: list[list[PineCandle]] = field(default_factory=list)
    window_atr: list[list[Decimal | None]] = field(default_factory=list)
    tier_code: list[int] = field(default_factory=list)
    speed_code: list[int] = field(default_factory=list)
    close_event: list[int] = field(default_factory=list)
    close_avail: list[int] = field(default_factory=list)

    total_count: int = 0
    prev_close: Decimal | None = None

    # ---- registry -------------------------------------------------------

    def add_setup(self, spec: PineSetupSpec) -> int:
        is_bullish = spec.direction == DIR_BULLISH
        self.key.append(spec.poi_key)
        self.direction.append(spec.direction)
        self.zone_top.append(spec.zone_top)
        self.zone_bottom.append(spec.zone_bottom)
        self.zone_height.append(spec.zone_top - spec.zone_bottom)
        self.entry_boundary.append(spec.zone_top if is_bullish else spec.zone_bottom)
        self.far_boundary.append(spec.zone_bottom if is_bullish else spec.zone_top)
        self.candidate_avail.append(spec.candidate_availability_time)
        self.is_formation_tf.append(spec.is_formation_timeframe)

        self.forming_idx.append(-1)
        self.forming_event.append(-1)
        self.forming_avail.append(-1)
        self.interaction_idx.append(-1)
        self.interaction_code.append(0)
        self.interaction_event.append(-1)
        self.interaction_avail.append(-1)
        self.running_anchor.append(None)
        self.reaction_start_idx.append(-1)
        self.reaction_anchor.append(None)
        self.window.append([])
        self.window_atr.append([])
        self.tier_code.append(0)
        self.speed_code.append(0)
        self.close_event.append(-1)
        self.close_avail.append(-1)
        return len(self.key) - 1

    # ---- per-bar advance ------------------------------------------------

    def advance(self, candle: PineCandle, atr_value: Decimal | None) -> None:
        """Test this one confirmed bar against every price-open setup.

        Transcribed from `advance_btmm_cursor`. Committed stages are never
        revisited, and no setup ever re-reads history.
        """
        m = self.total_count
        for i in range(len(self.key)):
            self.advance_one(i, candle, atr_value)
        self.total_count = m + 1
        self.prev_close = candle.close

    def advance_one(
        self, i: int, candle: PineCandle, atr_value: Decimal | None
    ) -> None:
        """Advance ONE setup by one bar, so a late-created setup can be
        replayed over the bars it missed without disturbing the others."""
        m = self.total_count
        window_bars = self.configuration.reaction_window_bars
        if True:
            is_bullish = self.direction[i] == DIR_BULLISH

            # 1. forming: first candle strictly after the candidate availability
            if (
                self.forming_idx[i] < 0
                and candle.availability_time > self.candidate_avail[i]
            ):
                self.forming_idx[i] = m
                self.forming_event[i] = candle.event_time
                self.forming_avail[i] = candle.availability_time

            # 2. first interaction
            if (
                self.forming_idx[i] >= 0
                and self.interaction_idx[i] < 0
                and m >= self.forming_idx[i]
            ):
                code = _classify_interaction(
                    None if m == 0 else self.prev_close,
                    candle,
                    atr_value,
                    self.zone_top[i],
                    self.zone_bottom[i],
                    self.direction[i],
                    self.configuration,
                )
                if code != 0:
                    self.interaction_idx[i] = m
                    self.interaction_code[i] = code
                    self.interaction_event[i] = candle.event_time
                    self.interaction_avail[i] = candle.availability_time
                    if code in ELIGIBLE_INTERACTION_CODES:
                        self.running_anchor[i] = (
                            candle.low if is_bullish else candle.high
                        )

            # 3. reaction start
            if (
                self.interaction_idx[i] >= 0
                and self.interaction_code[i] in ELIGIBLE_INTERACTION_CODES
                and self.reaction_start_idx[i] < 0
                and m > self.interaction_idx[i]
            ):
                anchor = self.running_anchor[i]
                assert anchor is not None
                if is_bullish:
                    anchor = min(anchor, candle.low)
                    started = candle.close > self.entry_boundary[i]
                else:
                    anchor = max(anchor, candle.high)
                    started = candle.close < self.entry_boundary[i]
                self.running_anchor[i] = anchor
                if started:
                    self.reaction_start_idx[i] = m
                    self.reaction_anchor[i] = anchor

            # 4. bounded reaction window
            if (
                self.reaction_start_idx[i] >= 0
                and self.tier_code[i] == 0
                and self.reaction_start_idx[i]
                <= m
                < self.reaction_start_idx[i] + window_bars
            ):
                self.window[i].append(candle)
                self.window_atr[i].append(atr_value)
                if len(self.window[i]) == window_bars:
                    anchor = self.reaction_anchor[i]
                    assert anchor is not None
                    tier, speed = _evaluate_reaction_window(
                        self.window[i],
                        self.window_atr[i],
                        anchor,
                        self.far_boundary[i],
                        self.zone_height[i],
                        self.direction[i],
                        self.configuration,
                    )
                    self.tier_code[i] = tier
                    self.speed_code[i] = speed
                    self.close_event[i] = candle.event_time
                    self.close_avail[i] = candle.availability_time


# ---------------------------------------------------------------------------
# Resolution: fixed cost, no candle scan
# ---------------------------------------------------------------------------


def _resolve_final_gates(
    evidence: PineEvidence, is_formation_tf: bool
) -> tuple[str, int, int]:
    """Transcription of `lifecycle._resolve_final_gates`.

    Gate precedence is strict and order-sensitive: liquidity, then context, then
    session, then volume. A setup failing two gates reports the first.
    """
    if evidence.liquidity_status != LQS_PRESENT:
        return ("CANCEL", CANCEL_NO_LIQUIDITY_EVIDENCE, BLOCK_NA)
    if (
        evidence.market_direction == CTX_MISALIGNED
        or evidence.analytical_framework == CTX_MISALIGNED
    ):
        return ("CANCEL", CANCEL_CONTEXT_REJECTED, BLOCK_NA)
    if evidence.session == SESS_INACTIVE:
        return ("CANCEL", CANCEL_SESSION_INACTIVE, BLOCK_NA)
    if evidence.volume == VOL_FAILS:
        return ("CANCEL", CANCEL_VOLUME_PILLAR_FAILED, BLOCK_NA)

    fully_aligned = (
        evidence.market_direction == CTX_ALIGNED
        and evidence.analytical_framework == CTX_ALIGNED
        and evidence.session == SESS_ACTIVE
        and evidence.volume == VOL_SUPPORTS
    )
    if is_formation_tf and fully_aligned:
        return ("CONFIRM", CANCEL_NA, BLOCK_NA)

    if not is_formation_tf:
        reason = BLOCK_FORMATION_TF_NOT_CONFIRMED
    elif (
        evidence.market_direction != CTX_ALIGNED
        or evidence.analytical_framework != CTX_ALIGNED
        or evidence.session != SESS_ACTIVE
    ):
        reason = BLOCK_CONTEXT_UNKNOWN
    else:
        reason = BLOCK_VOLUME_REVIEW_PENDING
    return ("BLOCKED", CANCEL_NA, reason)


def _cancel_transition_code(reason: int) -> int:
    if reason == CANCEL_NO_LIQUIDITY_EVIDENCE:
        return TR_NO_LIQUIDITY_EVIDENCE
    if reason == CANCEL_CONTEXT_REJECTED:
        return TR_CONTEXT_REJECTED
    if reason == CANCEL_SESSION_INACTIVE:
        return TR_SESSION_INACTIVE
    return TR_VOLUME_PILLAR_FAILED


def materialize(
    engine: PineBtmmEngine,
    i: int,
    has_false_invalidation: bool,
    genuine_event: int,
    genuine_avail: int,
    evidence: PineEvidence | None,
) -> tuple[list[PineTransition], _Fields]:
    """Transcription of `materialize_btmm_cursor`.

    Reads only the committed price-stage frontier for slot `i` plus the current
    evidence and POI-invalidation inputs, so an evidence arrival re-resolves a
    setup without touching a single candle. `genuine_avail` is `-1` when the
    source POI was never genuinely invalidated.
    """
    key = engine.key[i]
    steps: list[_Step] = [
        _Step(
            0,
            BLOCK_NA,
            -1,
            engine.candidate_avail[i],
            _Fields(availability_time=engine.candidate_avail[i]),
        )
    ]

    def emit(
        code: int, avail: int, event: int, fields: _Fields, blocked: int = BLOCK_NA
    ) -> None:
        fields.availability_time = avail
        steps.append(_Step(code, blocked, event, avail, fields))

    if engine.forming_idx[i] >= 0:
        fields = steps[-1].fields.copy()
        fields.primary_state = ST_FORMING
        fields.formation_stage = STAGE_POI_INTERACTION
        emit(
            TR_ENTERED_FORMING, engine.forming_avail[i], engine.forming_event[i], fields
        )

        if engine.interaction_idx[i] >= 0:
            code = engine.interaction_code[i]
            i_avail = engine.interaction_avail[i]
            i_event = engine.interaction_event[i]

            if code in ELIGIBLE_INTERACTION_CODES:
                fields = steps[-1].fields.copy()
                fields.accuracy_gate = GATE_PASS
                fields.interaction_class = code
                fields.formation_stage = STAGE_REACTION_MONITORING
                emit(TR_ACCURACY_GATE_CONFIRMED, i_avail, i_event, fields)

                if engine.tier_code[i] != 0:
                    c_avail = engine.close_avail[i]
                    c_event = engine.close_event[i]

                    if engine.tier_code[i] == RC_WEAK:
                        fields = steps[-1].fields.copy()
                        fields.primary_state = ST_CANCELLED
                        fields.reaction_gate = GATE_FAIL
                        fields.reaction_class = RC_WEAK
                        fields.cancellation_reason = CANCEL_WEAK_REACTION
                        emit(TR_WEAK_REACTION, c_avail, c_event, fields)
                    else:
                        fields = steps[-1].fields.copy()
                        fields.reaction_gate = GATE_PASS
                        fields.reaction_class = engine.tier_code[i]
                        emit(TR_REACTION_GATE_CONFIRMED, c_avail, c_event, fields)

                        if engine.speed_code[i] == SPD_SLOW_OR_UNCLEAR:
                            fields = steps[-1].fields.copy()
                            fields.primary_state = ST_CANCELLED
                            fields.reaction_speed_gate = GATE_FAIL
                            fields.reaction_speed_class = engine.speed_code[i]
                            fields.cancellation_reason = CANCEL_REACTION_SPEED_FAILED
                            emit(TR_REACTION_SPEED_FAILED, c_avail, c_event, fields)
                        else:
                            fields = steps[-1].fields.copy()
                            fields.reaction_speed_gate = GATE_PASS
                            fields.reaction_speed_class = engine.speed_code[i]
                            fields.formation_stage = STAGE_FINAL_GATE
                            emit(
                                TR_REACTION_SPEED_GATE_CONFIRMED,
                                c_avail,
                                c_event,
                                fields,
                            )

                            # Derived liquidity: location and source only. It can
                            # never assert that liquidity evidence was REVIEWED,
                            # which is what the gate below actually reads.
                            if has_false_invalidation:
                                fields = steps[-1].fields.copy()
                                fields.liquidity_location = LQL_AFTER_POI
                                fields.liquidity_source = SRC_RULE_BASED
                                steps.append(
                                    _Step(
                                        0,
                                        BLOCK_NA,
                                        c_event,
                                        fields.availability_time,
                                        fields,
                                    )
                                )

                            if evidence is None:
                                fields = steps[-1].fields.copy()
                                fields.primary_state = ST_CANCELLED
                                fields.cancellation_reason = (
                                    CANCEL_NO_LIQUIDITY_EVIDENCE
                                )
                                emit(TR_NO_LIQUIDITY_EVIDENCE, c_avail, c_event, fields)
                            else:
                                t_ev = evidence.availability_time
                                if t_ev > c_avail:
                                    fields = steps[-1].fields.copy()
                                    fields.primary_state = ST_BLOCKED
                                    fields.blocked_reason = (
                                        BLOCK_LIQUIDITY_REVIEW_PENDING
                                    )
                                    emit(
                                        TR_BLOCKED,
                                        c_avail,
                                        c_event,
                                        fields,
                                        BLOCK_LIQUIDITY_REVIEW_PENDING,
                                    )

                                    kind, cancel_reason, block_reason = (
                                        _resolve_final_gates(
                                            evidence, engine.is_formation_tf[i]
                                        )
                                    )
                                    fields = steps[-1].fields.copy()
                                    fields.market_direction = evidence.market_direction
                                    fields.analytical_framework = (
                                        evidence.analytical_framework
                                    )
                                    fields.session = evidence.session
                                    fields.volume = evidence.volume
                                    fields.liquidity_status = evidence.liquidity_status
                                    fields.reviewed_evidence_time = t_ev
                                    if evidence.liquidity_status == LQS_PRESENT:
                                        fields.liquidity_source = (
                                            evidence.liquidity_source
                                        )
                                    if kind == "CANCEL":
                                        fields.primary_state = ST_CANCELLED
                                        fields.cancellation_reason = cancel_reason
                                        fields.blocked_reason = BLOCK_NA
                                        emit(
                                            _cancel_transition_code(cancel_reason),
                                            t_ev,
                                            t_ev,
                                            fields,
                                        )
                                    elif kind == "CONFIRM":
                                        fields.primary_state = ST_CONFIRMED
                                        fields.formation_tf_gate = GATE_PASS
                                        fields.blocked_reason = BLOCK_NA
                                        emit(TR_CONFIRMED, t_ev, t_ev, fields)
                                    else:
                                        fields.primary_state = ST_FORMING
                                        fields.blocked_reason = BLOCK_NA
                                        emit(TR_RESUMED_FORMING, t_ev, t_ev, fields)
                                else:
                                    fields = steps[-1].fields.copy()
                                    fields.market_direction = evidence.market_direction
                                    fields.analytical_framework = (
                                        evidence.analytical_framework
                                    )
                                    fields.session = evidence.session
                                    fields.volume = evidence.volume
                                    fields.liquidity_status = evidence.liquidity_status
                                    fields.reviewed_evidence_time = t_ev
                                    if evidence.liquidity_status == LQS_PRESENT:
                                        fields.liquidity_source = (
                                            evidence.liquidity_source
                                        )

                                    kind, cancel_reason, block_reason = (
                                        _resolve_final_gates(
                                            evidence, engine.is_formation_tf[i]
                                        )
                                    )
                                    if kind == "CANCEL":
                                        fields.primary_state = ST_CANCELLED
                                        fields.cancellation_reason = cancel_reason
                                        emit(
                                            _cancel_transition_code(cancel_reason),
                                            c_avail,
                                            c_event,
                                            fields,
                                        )
                                    elif kind == "CONFIRM":
                                        fields.primary_state = ST_CONFIRMED
                                        fields.formation_tf_gate = GATE_PASS
                                        emit(TR_CONFIRMED, c_avail, c_event, fields)
                                    else:
                                        fields.primary_state = ST_BLOCKED
                                        fields.blocked_reason = block_reason
                                        emit(
                                            TR_BLOCKED,
                                            c_avail,
                                            c_event,
                                            fields,
                                            block_reason,
                                        )
            else:
                fields = steps[-1].fields.copy()
                fields.primary_state = ST_CANCELLED
                fields.accuracy_gate = GATE_FAIL
                fields.interaction_class = code
                fields.cancellation_reason = CANCEL_INTERACTION_INELIGIBLE
                emit(TR_INTERACTION_INELIGIBLE, i_avail, i_event, fields)

    # A genuine invalidation of the source POI truncates the walk at its own
    # availability, whatever price stage the setup had reached.
    if genuine_avail < 0:
        kept = steps
    else:
        kept = [steps[0]]
        for step in steps[1:]:
            if step.availability_time < genuine_avail:
                kept.append(step)
            else:
                break
        if kept[-1].fields.primary_state != ST_CANCELLED:
            fields = kept[-1].fields.copy()
            fields.primary_state = ST_CANCELLED
            fields.cancellation_reason = CANCEL_POI_REJECTED
            fields.blocked_reason = BLOCK_NA
            fields.availability_time = genuine_avail
            kept.append(
                _Step(TR_POI_REJECTED, BLOCK_NA, genuine_event, genuine_avail, fields)
            )

    transitions = [
        PineTransition(key, s.code, s.blocked_reason, s.event_time, s.availability_time)
        for s in kept
        if s.code != 0
    ]
    return transitions, kept[-1].fields


def report(
    engine: PineBtmmEngine,
    false_invalidation: dict[str, bool],
    genuine: dict[str, tuple[int, int]],
    evidence_by_key: dict[str, PineEvidence],
) -> tuple[list[PineTransition], list[PineState]]:
    """Materialize every setup and return the Pine-visible outputs.

    Transitions come back in walk-emission order, per setup, exactly as the
    engine produced them -- the canonical public sort is a separate, later step
    (`analyzer.py:568-591`), and `latest_lifecycle_transition_id` is reduced
    BEFORE it. Sorting here would silently change which transition is reported
    as latest on any bar carrying more than one.
    """
    all_transitions: list[PineTransition] = []
    states: list[PineState] = []
    for i in range(len(engine.key)):
        key = engine.key[i]
        g_event, g_avail = genuine.get(key, (-1, -1))
        transitions, fields = materialize(
            engine,
            i,
            false_invalidation.get(key, False),
            g_event,
            g_avail,
            evidence_by_key.get(key),
        )
        all_transitions.extend(transitions)
        states.append(
            PineState(
                poi_key=key,
                direction=engine.direction[i],
                primary_state=fields.primary_state,
                formation_stage=fields.formation_stage,
                market_direction=fields.market_direction,
                analytical_framework=fields.analytical_framework,
                session=fields.session,
                accuracy_gate=fields.accuracy_gate,
                interaction_class=fields.interaction_class,
                reaction_gate=fields.reaction_gate,
                reaction_class=fields.reaction_class,
                reaction_speed_gate=fields.reaction_speed_gate,
                reaction_speed_class=fields.reaction_speed_class,
                formation_tf_gate=fields.formation_tf_gate,
                volume=fields.volume,
                liquidity_status=fields.liquidity_status,
                liquidity_location=fields.liquidity_location,
                liquidity_source=fields.liquidity_source,
                reviewed_evidence_time=fields.reviewed_evidence_time,
                cancellation_reason=fields.cancellation_reason,
                blocked_reason=fields.blocked_reason,
                availability_time=fields.availability_time,
            )
        )
    return all_transitions, states


def backfill(
    engine: PineBtmmEngine,
    slot: int,
    candles: Sequence[PineCandle],
    atrs: Sequence[Decimal | None],
    upto: int,
) -> None:
    """Replay a LATE-CREATED setup over the bars it missed.

    Semantic availability is not engine discovery. `analyze_btmm` walks a setup
    from its source POI's availability whatever bar the POI was found on, but
    Pine only learns a POI exists when P3 emits it -- and the reference-zone
    family comes from a rolling projection that can surface a zone many bars
    after its own confirmation. Without this the setup silently skips every bar
    in between.

    `upto` is exclusive: the newest bar is advanced by the normal per-bar path
    immediately afterwards and must not be applied twice.
    """
    for j in range(upto):
        if candles[j].availability_time <= engine.candidate_avail[slot]:
            continue
        saved_total, saved_prev = engine.total_count, engine.prev_close
        engine.total_count = j
        engine.prev_close = candles[j - 1].close if j > 0 else None
        engine.advance_one(slot, candles[j], atrs[j])
        engine.total_count, engine.prev_close = saved_total, saved_prev
