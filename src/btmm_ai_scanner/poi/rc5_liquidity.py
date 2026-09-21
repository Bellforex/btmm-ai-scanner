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
