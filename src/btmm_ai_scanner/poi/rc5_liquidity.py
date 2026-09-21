"""RC5 qualified liquidity: which references deserve sweep authority.

WHAT THIS CHANGES AND WHAT IT DOES NOT. Raw liquidity detection is untouched.
Every confirmed swing, equal-level cluster, range boundary and trendline the
engine already finds is still found, still tracked, and still available to
internal machinery. This layer adds a SEMANTIC SUBSET on top: the references a
student should be shown, and the only ones allowed to produce a user-facing
sweep or feed RC5 DISTRACTION.

Nothing here alters the frozen ``SweepEvent``. It follows the pattern already
established by ``rc5_semantics.Rc5SemanticLedger``: a frozen contract left
alone, and a keyed sidecar carrying the RC5 verdict beside it. The bridge back
to a raw event is ``SweepEvent.level_id``, whose prefixes the framework already
assigns -- "S" swing, "E" equal-level cluster, "T" trendline, and
"<range_id>:<RANGE_HIGH|RANGE_LOW>" for a range boundary.

BSL / SSL. ``LiquiditySide`` already answers this for every level the framework
builds: BUY_SIDE is resting liquidity above price (highs, i.e. buy-side
liquidity) and SELL_SIDE is below (lows). RC5 re-uses that verdict rather than
re-deriving it, so the two can never disagree.

NO NEW TOLERANCES. Nothing in this module compares prices. Qualification is
decided by identity and by the structural role a reference already earned, and
deduplication is by stable source identity. That is deliberate: the moment a
price constant appears here, two references that ARE the same level start
depending on how close they happen to be rather than on what they are.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Any

from btmm_ai_scanner.framework.model import LiquidityKind, LiquiditySide
from btmm_ai_scanner.poi.rc5_host_identity import Rc5HostIdentity

__all__ = [
    "KIND_TO_REFERENCE",
    "PoiBoundary",
    "QualifiedLiquidityReference",
    "SweepReferenceKind",
    "poi_boundary_liquidity",
    "reference_kind_of_level_id",
    "side_of_reference",
]


class SweepReferenceKind(StrEnum):
    """What KIND of thing was swept, in student-facing terms.

    Deliberately not a copy of ``LiquidityKind``: that enum splits by side
    (SWING_HIGH vs SWING_LOW, RANGE_HIGH vs RANGE_LOW) because it names a
    level. This names a REFERENCE, and the side is carried separately as
    BSL/SSL, so one sweep never has to encode its side twice and cannot
    encode it inconsistently.

    POI_BOUNDARY and SUPPORT_RESISTANCE have no ``LiquidityKind`` at all --
    they are references RC5 adds.
    """

    STRUCTURAL_SWING = "STRUCTURAL_SWING"
    EQUAL_HIGH_LOW = "EQUAL_HIGH_LOW"
    RANGE_BOUNDARY = "RANGE_BOUNDARY"
    TRENDLINE = "TRENDLINE"
    POI_BOUNDARY = "POI_BOUNDARY"
    SUPPORT_RESISTANCE = "SUPPORT_RESISTANCE"


#: Every ``LiquidityKind`` the framework can emit, mapped to its RC5 reference
#: kind. Exhaustive by construction -- a new LiquidityKind that is not listed
#: raises rather than being silently dropped from qualification.
KIND_TO_REFERENCE: dict[LiquidityKind, SweepReferenceKind] = {
    LiquidityKind.SWING_HIGH: SweepReferenceKind.STRUCTURAL_SWING,
    LiquidityKind.SWING_LOW: SweepReferenceKind.STRUCTURAL_SWING,
    LiquidityKind.EQUAL_HIGHS: SweepReferenceKind.EQUAL_HIGH_LOW,
    LiquidityKind.EQUAL_LOWS: SweepReferenceKind.EQUAL_HIGH_LOW,
    LiquidityKind.RANGE_HIGH: SweepReferenceKind.RANGE_BOUNDARY,
    LiquidityKind.RANGE_LOW: SweepReferenceKind.RANGE_BOUNDARY,
    LiquidityKind.TRENDLINE: SweepReferenceKind.TRENDLINE,
}


@dataclass(frozen=True)
class QualifiedLiquidityReference:
    """One reference that has earned sweep authority.

    ``source_identity`` is the STABLE identity of whatever produced the level:
    a swing record id, an equal-level cluster record id, a trendline record id,
    a range id, or a POI ``_formation_key`` plus boundary side. It is what
    deduplication keys on, so one real level that several detectors describe
    collapses to one reference without any price comparison.
    """

    kind: SweepReferenceKind
    side: LiquiditySide
    price: Decimal
    #: Stable identity of the producing record. Never a runtime index.
    source_identity: tuple[Any, ...]
    #: The level id the framework uses, when this reference maps to one.
    #: ``None`` for references RC5 adds (POI boundaries).
    level_id: str | None
    host: Rc5HostIdentity
    #: When this reference became causally usable.
    known_from_utc: datetime
    #: Why it qualified -- forensic, so a surviving sweep can answer "why was
    #: this reference meaningful?" without re-deriving anything.
    reason: str

    @property
    def is_buy_side(self) -> bool:
        """BSL: resting liquidity above price."""
        return self.side is LiquiditySide.BUY_SIDE

    @property
    def label(self) -> str:
        """``BSL`` or ``SSL`` -- the student-facing name."""
        return "BSL" if self.is_buy_side else "SSL"

    @property
    def key(self) -> tuple[Any, ...]:
        """Host-local identity. Includes the SEMANTIC host, so an M45
        reference can never collide with an M15 one despite sharing a
        carrier enum."""
        return (*self.host.key, self.kind.value, *self.source_identity)


def reference_kind_of_level_id(level_id: str) -> SweepReferenceKind:
    """Map a framework ``level_id`` back to its RC5 reference kind.

    The framework's own prefixes are the contract here (framework/engine.py):
    ``S<uuid>`` swing, ``E<uuid>`` equal-level cluster, ``T<uuid>`` trendline,
    and ``<range_id>:<RANGE_HIGH|RANGE_LOW>`` for a range boundary, where
    ``range_id`` is itself ``R<isoformat>``.

    A range id also starts with "R", so the ``":"`` test must come FIRST --
    checking the prefix first would classify every range boundary as a swing.
    """
    if level_id.startswith("P"):
        return SweepReferenceKind.POI_BOUNDARY
    if ":" in level_id:
        return SweepReferenceKind.RANGE_BOUNDARY
    if level_id.startswith("S"):
        return SweepReferenceKind.STRUCTURAL_SWING
    if level_id.startswith("E"):
        return SweepReferenceKind.EQUAL_HIGH_LOW
    if level_id.startswith("T"):
        return SweepReferenceKind.TRENDLINE
    raise ValueError(f"unrecognised framework level_id: {level_id!r}")


def side_of_reference(kind: LiquidityKind) -> LiquiditySide:
    """The side a ``LiquidityKind`` rests on.

    TRENDLINE is deliberately absent: a trendline's side depends on its slope,
    not its kind, and the framework already decides it per level. Asking here
    would invite a second, disagreeing answer.
    """
    highs = {
        LiquidityKind.SWING_HIGH,
        LiquidityKind.EQUAL_HIGHS,
        LiquidityKind.RANGE_HIGH,
    }
    lows = {
        LiquidityKind.SWING_LOW,
        LiquidityKind.EQUAL_LOWS,
        LiquidityKind.RANGE_LOW,
    }
    if kind in highs:
        return LiquiditySide.BUY_SIDE
    if kind in lows:
        return LiquiditySide.SELL_SIDE
    raise ValueError(
        f"{kind.value} has no side that follows from its kind alone; read it "
        "from the level the framework built"
    )


@dataclass(frozen=True)
class PoiBoundary:
    """The one edge of a POI that is a liquidity reference, and its side."""

    price: Decimal
    side: LiquiditySide
    #: "zone_top" or "zone_bottom" -- which edge this was, for forensics.
    edge: str

    @property
    def label(self) -> str:
        return "BSL" if self.side is LiquiditySide.BUY_SIDE else "SSL"


def poi_boundary_liquidity(
    direction: Any,
    zone_top: Decimal,
    zone_bottom: Decimal,
) -> PoiBoundary:
    """The FAR edge of a POI, which is the edge that holds liquidity.

    NOT "top is BSL, bottom is SSL". That mapping is true of a level, and a POI
    is not a level -- it is a directional zone with a proximal edge price
    enters through and a distal edge beyond which the idea is wrong. Only the
    far edge is a liquidity reference, and which edge that is depends on the
    POI's direction.

    Derived from the frozen lifecycle rather than asserted. ``poi/lifecycle.py``
    breaches a BULLISH zone on ``close < zone_bottom`` and a BEARISH zone on
    ``close > zone_top``, so the far edge IS the invalidation boundary. That is
    also why it is the meaningful liquidity: protective orders for anyone
    working the zone rest beyond it, and a sweep of that level is precisely the
    event that would invalidate the POI if it were not reclaimed.

    So:

    * BULLISH POI -- far edge is the BOTTOM. Liquidity rests BELOW price, which
      is SELL_SIDE, shown as SSL.
    * BEARISH POI -- far edge is the TOP. Liquidity rests ABOVE price, which is
      BUY_SIDE, shown as BSL.

    The proximal edge is deliberately not a reference. Price trading through it
    is mitigation -- the zone being used -- and mitigation is not a sweep.
    """
    name = getattr(direction, "value", direction)
    if name == "BULLISH":
        return PoiBoundary(
            price=zone_bottom, side=LiquiditySide.SELL_SIDE, edge="zone_bottom"
        )
    if name == "BEARISH":
        return PoiBoundary(price=zone_top, side=LiquiditySide.BUY_SIDE, edge="zone_top")
    raise ValueError(f"POI direction {name!r} has no far edge")


# ---------------------------------------------------------------------------
# qualification
# ---------------------------------------------------------------------------
#
# WHY THERE IS NO SEPARATE "ACTIVE" VIEW FOR THESE FAMILIES.
#
# The author's concern is that a write-once qualification could let dead
# references keep producing sweeps forever. For every family that flows through
# ``framework/engine.py::_levels()`` that cannot happen, and the framework
# already prevents it rather than RC5 needing to:
#
# * ``_sweep_step`` drops a level that was closed through and not reclaimed
#   within ``sweep_reclaim_bars`` -- consumed, no event;
# * a level that DOES fire a sweep is likewise not appended to the survivors,
#   so every level fires at most one sweep in its life and then retires;
# * both range registration sites guard on a seen-key set, so a consumed range
#   boundary is never re-registered.
#
# So a raw ``SweepEvent`` existing at all is proof its level was live at that
# bar. Qualification therefore only has to answer the HISTORICAL question --
# was this reference ever meaningful? -- and adding a second activity test here
# would duplicate the framework's lifecycle and risk disagreeing with it.
#
# POI far edges are different: they are an RC5 addition with no level lifecycle
# of their own, so their activity IS evaluated, from rc5_validity plus
# authority standing. That is handled where they are produced, not here.


class RejectionReason(StrEnum):
    """Why a raw sweep produced no user-facing event. Never "noise"."""

    TEXTURE_SWING = "TEXTURE_SWING"
    TRENDLINE_ANCHORS_NOT_MEANINGFUL = "TRENDLINE_ANCHORS_NOT_MEANINGFUL"
    UNKNOWN_LEVEL = "UNKNOWN_LEVEL"


@dataclass(frozen=True)
class Qualification:
    """The verdict on one raw sweep: a reference, or a named refusal."""

    reference: QualifiedLiquidityReference | None
    rejected_because: RejectionReason | None = None

    @property
    def is_qualified(self) -> bool:
        return self.reference is not None


def qualify_sweep_reference(
    event: Any,
    ledger: Any,
    host: Rc5HostIdentity,
    *,
    swings_by_id: Any = None,
    trendlines_by_id: Any = None,
) -> Qualification:
    """Decide whether one raw ``SweepEvent`` swept a meaningful reference.

    Per-family doctrine, all of it from facts that already exist:

    * STRUCTURAL_SWING -- the swing must appear in the canonical swing sidecar,
      i.e. the structure walk actually used it. Texture pivots are internal.
    * EQUAL_HIGH_LOW -- always qualifies. A pool of equal highs or lows IS
      liquidity; it does not have to also be a structural origin.
    * RANGE_BOUNDARY -- always qualifies, on the range's own confirmation.
    * TRENDLINE -- BOTH defining anchors must be meaningful swings. Touch count
      is unusable: ``qualifying_touch_swing_record_ids`` is length 1 for all
      437 trendlines measured on M15 and H4, so it carries no information.

    ``side`` is taken from the event, which the framework already decided. It
    is never re-derived here, so the two layers cannot disagree about BSL/SSL.
    """
    level_id = event.level_id
    kind = reference_kind_of_level_id(level_id)
    side = event.side

    def _reference(source_identity: tuple[Any, ...], reason: str) -> Qualification:
        return Qualification(
            QualifiedLiquidityReference(
                kind=kind,
                side=side,
                price=event.level_price,
                source_identity=source_identity,
                level_id=level_id,
                host=host,
                known_from_utc=event.availability_time_utc,
                reason=reason,
            )
        )

    if kind is SweepReferenceKind.RANGE_BOUNDARY:
        range_id, _, boundary = level_id.rpartition(":")
        return _reference((range_id, boundary), "CONFIRMED_RANGE_BOUNDARY")

    identity = level_id[1:]

    if kind is SweepReferenceKind.EQUAL_HIGH_LOW:
        return _reference((identity,), "EQUAL_LEVEL_POOL")

    if kind is SweepReferenceKind.STRUCTURAL_SWING:
        swing = (swings_by_id or {}).get(identity)
        entry = ledger.swing_role(swing.record_id) if swing is not None else None
        if entry is None or not entry.is_meaningful:
            return Qualification(None, RejectionReason.TEXTURE_SWING)
        return _reference((identity,), str(entry.role))

    if kind is SweepReferenceKind.TRENDLINE:
        line = (trendlines_by_id or {}).get(identity)
        if line is None:
            return Qualification(None, RejectionReason.UNKNOWN_LEVEL)
        anchors = (line.anchor_1_swing_record_id, line.anchor_2_swing_record_id)
        facts = [ledger.swing_role(a) for a in anchors]
        if not all(f is not None and f.is_meaningful for f in facts):
            return Qualification(None, RejectionReason.TRENDLINE_ANCHORS_NOT_MEANINGFUL)
        return _reference(tuple(str(a) for a in anchors), "BOTH_ANCHORS_MEANINGFUL")

    return Qualification(None, RejectionReason.UNKNOWN_LEVEL)


# ---------------------------------------------------------------------------
# POI far edges -- the one family with no framework lifecycle of its own
# ---------------------------------------------------------------------------

#: POI far edges are an RC5 family, and ``LiquidityKind`` is frozen with no
#: member for them. Adding one would change a published contract surface, so a
#: POI level CARRIES the side-appropriate existing kind purely so the shared
#: stepper can build its internal event.
#:
#: NOTHING MAY READ ``kind`` FOR A POI LEVEL. The authority is the "P" prefix on
#: ``level_id``, which ``reference_kind_of_level_id`` resolves first. These raw
#: events never leave RC5 -- they become qualified references whose kind is
#: POI_BOUNDARY.
_POI_CARRIER_KIND = {
    LiquiditySide.BUY_SIDE: LiquidityKind.SWING_HIGH,
    LiquiditySide.SELL_SIDE: LiquidityKind.SWING_LOW,
}


def poi_boundary_level_id(observation: Any) -> str:
    """Stable, host-independent identity for a POI far-edge level.

    Built from stable provenance, never from a runtime index. The "P" prefix
    keeps it outside the framework's own S / E / T / range namespaces.

    NOT the formation key alone. Reference-zone POIs -- support/resistance
    zones and equal-level pools -- have an EMPTY
    ``source_candle_record_ids``: their provenance is the zone or cluster they
    came from, which lives in ``source_measurement_record_ids``. Keying on
    formation alone gave every equal-low pool the same id,
    ``PEQUAL_LOWS_LIQUIDITY:``, so they all collapsed onto one level and only
    the first ever registered. Measured on M5, where two distinct pools
    surfaced as an unexplained same-price collision.

    ``poi_reference_source_identity`` already picks the right provenance per
    family, so this reuses it rather than repeating the choice.
    """
    poi_type = getattr(getattr(observation, "poi_type", None), "value", "POI")
    identity = "+".join(str(p) for p in poi_reference_source_identity(observation))
    return f"P{poi_type}:{identity}"


def poi_reference_is_active(
    observation: Any,
    state: Any | None,
    ledger: Any,
) -> bool:
    """Whether a POI's far edge may CURRENTLY hold liquidity.

    This is the one place an activity rule is genuinely needed. Every other
    reference family flows through the framework's own level lifecycle, which
    already retires a level once it is swept or accepted through. POI far edges
    are an RC5 addition with no such lifecycle, so their activity is evaluated
    from the layers that do own it:

    * ``rc5_validity`` -- the zone still stands, and
    * authority -- it is an independent opportunity, not a same-origin
      subordinate hiding behind a better POI from the same origin.

    ACTIVE through fresh, interaction, mitigation, RE-mitigation and a
    false break that was reclaimed. INACTIVE only after genuine invalidation,
    standalone lifecycle supersession, or authority suppression.

    Deliberately does NOT read ``terminal_reason == MITIGATED`` or
    ``fresh_active``: the frozen lifecycle sets both on the FIRST TOUCH, so
    either would retire a perfectly good zone the moment price used it.
    """
    from btmm_ai_scanner.poi.rc5_semantics import rc5_poi_is_valid, stable_poi_key

    record = ledger.get(stable_poi_key(observation))
    if record is not None and record.is_suppressed:
        return False
    return rc5_poi_is_valid(state)


def poi_boundary_sweeps(
    candles: Any,
    observations: Any,
    states_by_poi_id: Any,
    ledger: Any,
    configuration: Any,
) -> tuple[Any, ...]:
    """Sweeps of POI far edges, using the framework's OWN sweep mechanics.

    ``framework.engine.advance_levels`` is literally the function RC4 uses, so
    the wick test, the close-through test, the reclaim window and the
    "accepted beyond consumes the level" rule are shared, not re-implemented.
    Nothing about RC4's own level set is touched: this is a separate pass over
    levels RC4 never builds.

    TWO WAYS A POI LEVEL LEAVES THE BOOK, and they are different:

    * the framework consumes it -- swept, or accepted through. Same as any
      other level; ``advance_levels`` handles it.
    * the POI dies. A zone that is genuinely invalidated, superseded or
      authority-suppressed stops holding liquidity, so its level is withdrawn
      BEFORE the step rather than left to be swept. This is the check the
      other families do not need.

    A level is registered once, at the POI's own availability, and never
    re-registered -- the same discipline the framework applies to range
    boundaries, so a consumed far edge cannot come back.
    """
    from btmm_ai_scanner.framework.engine import LiquidityLevel, advance_levels

    ordered = sorted(
        observations, key=lambda o: (o.availability_time_utc, str(o.record_id))
    )
    pending = list(ordered)
    active: list[Any] = []
    level_owner: dict[str, Any] = {}
    registered: set[str] = set()
    events: list[Any] = []

    for index, candle in enumerate(candles):
        opened = candle.event_time_utc
        while pending and pending[0].availability_time_utc <= opened:
            observation = pending.pop(0)
            level_id = poi_boundary_level_id(observation)
            if level_id in registered:
                continue
            state = states_by_poi_id.get(observation.record_id)
            if not poi_reference_is_active(observation, state, ledger):
                continue
            boundary = poi_boundary_liquidity(
                observation.direction, observation.zone_top, observation.zone_bottom
            )
            registered.add(level_id)
            level_owner[level_id] = observation
            active.append(
                LiquidityLevel(
                    level_id,
                    _POI_CARRIER_KIND[boundary.side],
                    boundary.side,
                    boundary.price,
                    observation.availability_time_utc,
                )
            )

        # withdraw levels whose POI is no longer a live, independent zone
        still_live: list[Any] = []
        for level in active:
            observation = level_owner.get(level.level_id)
            if observation is None:
                continue
            state = states_by_poi_id.get(observation.record_id)
            if poi_reference_is_active(observation, state, ledger):
                still_live.append(level)
        active = advance_levels(still_live, index, candle, None, configuration, events)

    return tuple(events)


#: Reference-zone POI types carry a level that ALREADY has a reference kind of
#: its own. ``poi/reference_zones.py`` turns support/resistance zones and
#: equal-level clusters into POIs, keeping the producing record in
#: ``source_measurement_record_ids``, so those far edges are not generic POI
#: boundaries -- they ARE the S/R zone and the equal pool.
#:
#: Naming them correctly matters for two reasons: SUPPORT_RESISTANCE would
#: otherwise never appear at all, and an equal pool would be counted once as a
#: framework "E" level and again as an unrelated-looking POI boundary instead
#: of being visible as the same liquidity described twice.
_REFERENCE_ZONE_KINDS: dict[str, SweepReferenceKind] = {
    "SUPPORT_ZONE": SweepReferenceKind.SUPPORT_RESISTANCE,
    "RESISTANCE_ZONE": SweepReferenceKind.SUPPORT_RESISTANCE,
    "EQUAL_HIGHS_LIQUIDITY": SweepReferenceKind.EQUAL_HIGH_LOW,
    "EQUAL_LOWS_LIQUIDITY": SweepReferenceKind.EQUAL_HIGH_LOW,
}


def reference_kind_of_poi(observation: Any) -> SweepReferenceKind:
    """The reference kind a POI's far edge represents."""
    name = getattr(getattr(observation, "poi_type", None), "value", None)
    return _REFERENCE_ZONE_KINDS.get(str(name), SweepReferenceKind.POI_BOUNDARY)


def poi_reference_source_identity(observation: Any) -> tuple[Any, ...]:
    """Stable identity for a POI far-edge reference.

    A reference-zone POI is identified by the record it came FROM -- the S/R
    zone or the equal-level cluster -- because that is the identity the
    framework's own level for the same liquidity uses. Sharing it is what lets
    deduplication link the two without comparing prices.

    Every other POI is identified by its formation key.
    """
    from btmm_ai_scanner.poi.rc5_semantics import stable_poi_key

    sources = getattr(observation, "source_measurement_record_ids", ())
    if reference_kind_of_poi(observation) is not SweepReferenceKind.POI_BOUNDARY:
        if sources:
            return (str(sources[0]),)
    key = stable_poi_key(observation)
    poi_type = getattr(key[0], "value", key[0])
    return (str(poi_type), *(str(c) for c in key[1]))
