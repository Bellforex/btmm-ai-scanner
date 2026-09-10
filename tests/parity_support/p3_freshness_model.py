"""RC3 candidate semantics: POI validation state and first-reaction mitigation.

Test-side oracle only. Nothing in ``src/`` imports this module and it changes
no frozen P3 behaviour: RC2 has no mitigation concept at all, so this is the
proposed contract expressed as executable semantics, ready to be differentiated
against a Pine port once the author approves it.

THE TWO AXES ARE DELIBERATELY SEPARATE
--------------------------------------
``qualify_engulfing`` answers "is this pattern instance a POI worth trading?"
and ``resolve_lifecycle`` answers "has price already used it up?". They are
kept apart because the H4 reference audit showed the author's two examples are
separated by the second axis, not the first: both satisfy the frozen 2.0
total-range rule, and only their reaction histories differ.

The qualification predicate is therefore parameterised rather than hard-coded.
``qualify_frozen`` reproduces RC2 exactly; ``qualify_with_range_engulfment``
adds the book's already-written "stronger version also engulfs the previous
candle's entire range including wicks" clause. Which one becomes mandatory is
an author decision, not a default this module gets to pick.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum

__all__ = [
    "Bar",
    "LifecycleState",
    "PoiInterval",
    "Resolution",
    "TerminalReason",
    "body_engulfs",
    "intersects",
    "qualify_engulfing",
    "qualify_frozen",
    "qualify_with_range_engulfment",
    "range_engulfs",
    "resolve_lifecycle",
]


@dataclass(frozen=True)
class Bar:
    """One confirmed candle, reduced to what the lifecycle rules actually read."""

    index: int
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal


@dataclass(frozen=True)
class PoiInterval:
    """A bounded POI zone plus the bar index at which it became available.

    ``availability_index`` is the index of the bar whose close made the POI
    knowable. That bar can never consume its own POI, so reaction scanning
    starts at ``availability_index + 1``.
    """

    top: Decimal
    bottom: Decimal
    availability_index: int
    bullish: bool = True

    def __post_init__(self) -> None:
        if self.top < self.bottom:
            raise ValueError(f"top {self.top} is below bottom {self.bottom}")


class LifecycleState(StrEnum):
    CANDIDATE = "CANDIDATE"
    VALIDATED_FRESH = "VALIDATED_FRESH"
    MITIGATED = "MITIGATED"
    INVALIDATED = "INVALIDATED"


class TerminalReason(StrEnum):
    FIRST_REACTION = "FIRST_REACTION"
    FAR_BOUNDARY_BREACH_WITHOUT_CONTACT = "FAR_BOUNDARY_BREACH_WITHOUT_CONTACT"
    FAILED_QUALIFICATION = "FAILED_QUALIFICATION"


@dataclass(frozen=True)
class Resolution:
    """The outcome of running one POI through the whole bar sequence.

    Identity-bearing fields are carried through unchanged even for terminal
    outcomes: a mitigated POI stops being *displayed and eligible*, it is never
    deleted from the registry.
    """

    state: LifecycleState
    terminal_index: int | None
    terminal_reason: TerminalReason | None
    top: Decimal
    bottom: Decimal
    availability_index: int

    @property
    def display_eligible(self) -> bool:
        return self.state is LifecycleState.VALIDATED_FRESH

    @property
    def downstream_eligible(self) -> bool:
        return self.state is LifecycleState.VALIDATED_FRESH


def intersects(bar: Bar, poi: PoiInterval) -> bool:
    """Does this bar's range touch the POI interval? Boundary touch counts.

    Both comparisons are inclusive on purpose. A wick that stops exactly on the
    zone boundary is a reaction: price reached the level and the level did its
    job, whether or not it traded through.
    """
    return bar.high >= poi.bottom and bar.low <= poi.top


def _far_boundary_breached(bar: Bar, poi: PoiInterval) -> bool:
    """Closed clean through the far side without ever touching the zone.

    Only reachable when the bar's whole range sits beyond the far boundary,
    since any bar that overlaps the zone is a reaction first. In practice this
    is the gap case.
    """
    if poi.bullish:
        return bar.high < poi.bottom and bar.close < poi.bottom
    return bar.low > poi.top and bar.close > poi.top


def resolve_lifecycle(bars: Sequence[Bar], poi: PoiInterval) -> Resolution:
    """Walk forward from the first bar that is allowed to consume the POI.

    Scanning starts strictly after ``availability_index``. The availability bar
    is the one that *created* the POI; letting it also consume the POI would
    make every POI dead on arrival, which is the specific mistake this contract
    exists to prevent.
    """
    for bar in bars:
        if bar.index <= poi.availability_index:
            continue
        if intersects(bar, poi):
            return Resolution(
                LifecycleState.MITIGATED,
                bar.index,
                TerminalReason.FIRST_REACTION,
                poi.top,
                poi.bottom,
                poi.availability_index,
            )
        if _far_boundary_breached(bar, poi):
            return Resolution(
                LifecycleState.INVALIDATED,
                bar.index,
                TerminalReason.FAR_BOUNDARY_BREACH_WITHOUT_CONTACT,
                poi.top,
                poi.bottom,
                poi.availability_index,
            )
    return Resolution(
        LifecycleState.VALIDATED_FRESH,
        None,
        None,
        poi.top,
        poi.bottom,
        poi.availability_index,
    )


# ---- qualification predicates ----------------------------------------------


def _range(bar: Bar) -> Decimal:
    return bar.high - bar.low


def body_engulfs(source: Bar, departure: Bar) -> bool:
    """Departure body covers the source body — the book's core engulfing rule.

    Frozen RC2 does not test this at all; it is included here so the audit can
    report on it rather than assume it.
    """
    return min(departure.open, departure.close) <= min(
        source.open, source.close
    ) and max(departure.open, departure.close) >= max(source.open, source.close)


def range_engulfs(source: Bar, departure: Bar) -> bool:
    """Departure range covers the source range including wicks.

    The book calls this "a stronger version" and explicitly does not require it
    for a baseline valid pattern. Promoting it to mandatory is the author
    decision this module refuses to make silently.
    """
    return departure.low <= source.low and departure.high >= source.high


QualifyFn = Callable[[Bar, Bar, Decimal], bool]


def qualify_frozen(source: Bar, departure: Bar, threshold: Decimal) -> bool:
    """Exactly what RC2 does: total-range ratio plus opposite candle colours."""
    source_range = _range(source)
    if source_range == 0:
        return False
    if _range(departure) / source_range < threshold:
        return False
    return source.close < source.open and departure.close > departure.open


def qualify_with_range_engulfment(
    source: Bar, departure: Bar, threshold: Decimal
) -> bool:
    """Frozen rule plus the book's full-range (wick) engulfment clause."""
    return qualify_frozen(source, departure, threshold) and range_engulfs(
        source, departure
    )


def qualify_engulfing(
    source: Bar,
    departure: Bar,
    threshold: Decimal = Decimal("2.0"),
    predicate: QualifyFn = qualify_frozen,
) -> LifecycleState:
    """CANDIDATE when the shape is there, VALIDATED_FRESH when it also qualifies.

    Returning CANDIDATE rather than nothing is the point of Phase 6: pattern
    recognition survives even when the POI validation principle rejects the
    instance, so a rejected engulfing is still explainable instead of invisible.
    """
    shape = source.close < source.open and departure.close > departure.open
    if not shape:
        raise ValueError("not a bullish engulfing shape")
    return (
        LifecycleState.VALIDATED_FRESH
        if predicate(source, departure, threshold)
        else LifecycleState.CANDIDATE
    )
