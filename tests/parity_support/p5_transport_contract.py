"""The canonical P6 -> P5 transport contract: 26 fields, one definition.

Test/parity tooling only. Nothing in ``src/`` imports this and it changes no
production semantics.

This module is the single source of truth for what crosses the boundary. The
Pine UDT, the authoritative oracle, the Pine-equivalent model, the digest and
the capture parser all read their field list from here, so a field cannot be
added in one place and forgotten in another.

WHY DIRECTION AND CLASSIFICATION ARE SEPARATE FIELDS
-----------------------------------------------------
P6 already transports a displacement as ONE signed code, built in Pine as
``code = isBull ? cls : -cls`` with ``cls`` in {0, 1, 2}. That encoding is
lossy in a way that does not matter for the closed P6 surface and matters a
great deal here: a bullish NORMAL displacement encodes to ``0`` and a bearish
NORMAL encodes to ``-0``, which is the same ``0``. Direction is destroyed
exactly on the classification that occurs most often.

`assess_momentum` counts bullish against bearish displacements in its window
regardless of classification, so reusing the signed code would have silently
mis-scored every window containing a NORMAL bar. The window therefore carries
``dispNDir`` and ``dispNCls`` separately. The existing signed ``dispCode``
scalar stays exactly as it is, untouched, in its old tuple position.

SLOT ORDERING -- STATED, NEVER IMPLIED
---------------------------------------
Both windows are LEFT-ALIGNED and run OLDEST -> NEWEST:

* ``trans1Type`` is the oldest retained transition, ``trans{transWindowCount}Type``
  the newest; slots above the count hold the absent sentinel;
* likewise ``disp1*`` .. ``disp{dispWindowCount}*``.

So with two retained transitions, ``trans1Type`` is the older and
``trans2Type`` the newest, while ``trans3Type`` and ``trans4Type`` are absent.
Breakout's ``ordered_transitions[-2]`` is ``trans{count-1}Type``, NOT a fixed
slot. That is deliberately awkward to write down, because the alternative --
leaving it to be inferred -- is how a window gets read backwards.

TWO SPELLINGS OF ABSENT -- AND WHERE THE LINE ACTUALLY FALLS
---------------------------------------------------------------
Inherited unchanged from the P2/P3/P4/P6 digest contracts, because they encode
differently and a port that confused them would move the digest rather than
pass quietly:

* ``C_ST_NA`` (-99) for every integer field -- CODES and integer TIMES alike,
  because 0 is a live value for both, and the closed P6 surface already spells
  an absent integer time this way (``lastConfT``, at position 5 of the original
  fourteen). ``stateAvailT``, ``lastTransAvailT`` and ``dispAvailT`` are epoch
  milliseconds, i.e. integers, so they follow the same rule -- NOT the ``na``
  rule a first draft of this contract mistakenly gave them.
* ``None`` / Pine ``na`` for prices and ratios only (the fields typed ``float``
  in ``FIELDS`` below).

THIS IS A TRANSPORT-BOUNDARY DECISION, NOT A CHANGE TO PYTHON SEMANTICS
--------------------------------------------------------------------------
The authoritative domain models -- ``CurrentStructureState.availability_time_utc``,
``StructureTransition.availability_time_utc`` -- are untouched and keep using
``datetime | None`` exactly as their contracts define them. What changed is only
``p5_transport_records.epoch_ms``, the WIRE encoder both the oracle and the
Pine-equivalent model call to turn a ``datetime | None`` into what actually
crosses ``request.security``: it now maps ``None -> C_ST_NA`` instead of
``None -> None``, because Pine has no ``None`` to receive. ``P5TransportRecord``
below therefore models the WIRE record, and its three time fields are plain
``int``, never ``int | None`` -- matching what the Pine UDT itself declares
(``int stateAvailT = C_ST_NA``, and likewise for the other two). A semantic
comparison that needs ``None`` back uses ``decode_epoch_ms`` to invert it; digest
folding and the oracle/model differential both operate on the encoded ``int``
directly and never need to.

Counts are ordinary integers: zero means an empty window, not an absent one.
"""

from __future__ import annotations

from dataclasses import dataclass
from dataclasses import fields as dataclass_fields
from typing import Final

#: Pine's integer "absent" sentinel, identical to every earlier phase contract.
C_ST_NA: Final = -99

#: How many most-recent structure transitions the wire carries.
TRANSITION_WINDOW_CAPACITY: Final = 4

#: How many most-recent displacement observations the wire carries.
DISPLACEMENT_WINDOW_CAPACITY: Final = 3

# --- code vocabularies, matching the Pine constants already in P6 DEV --------
TR_BULLISH_BOS: Final = 1
TR_BEARISH_BOS: Final = -1
TR_BULLISH_CHOCH: Final = 2
TR_BEARISH_CHOCH: Final = -2

DIR_UNDETERMINED: Final = 0
DIR_BULLISH: Final = 1
DIR_BEARISH: Final = -1

DISP_DIR_BULLISH: Final = 1
DISP_DIR_BEARISH: Final = -1

DISP_CLS_NORMAL: Final = 0
DISP_CLS_FAST: Final = 1
DISP_CLS_VERY_FAST: Final = 2


@dataclass(frozen=True)
class TransportField:
    """One field on the wire, with everything a port needs to implement it."""

    position: int
    name: str
    pine_type: str
    consumer: str
    meaning: str
    absent: str
    availability: str


FIELDS: Final[tuple[TransportField, ...]] = (
    TransportField(
        1,
        "stateAvailT",
        "int",
        "trend",
        "current_state.availability_time_utc, in epoch milliseconds",
        "C_ST_NA when there is no current structure state",
        "the structure walk's own availability time; confirmed bars only",
    ),
    TransportField(
        2,
        "contStreak",
        "int",
        "trend",
        "_continuation_streak: consecutive most-recent continuation BOS for the "
        "current direction, scanning backwards until anything else",
        "0 when there are no transitions or the newest is not a continuation BOS",
        "derived from the full ordered transition history",
    ),
    TransportField(
        3,
        "priorOppStreak",
        "int",
        "trend",
        "_prior_opposite_streak: consecutive opposing BOS immediately before the "
        "LAST transition, which is itself excluded",
        "0 when fewer than two transitions",
        "derived from the full ordered transition history",
    ),
    TransportField(
        4,
        "exhaustFlag",
        "int",
        "trend",
        "_exhaustion as 0/1: bullish and last SWING_HIGH below the previous "
        "SWING_HIGH, or bearish and last SWING_LOW above the previous SWING_LOW",
        "0 when undetermined, or fewer than two same-type swings",
        "derived from the full ordered swing history",
    ),
    TransportField(
        5,
        "transWindowCount",
        "int",
        "trend+breakout",
        "min(TRANSITION_WINDOW_CAPACITY, number of ordered transitions)",
        "0 for an empty history; never absent",
        "confirmed transitions only",
    ),
    *[
        TransportField(
            5 + i,
            f"trans{i}Type",
            "int",
            "trend+breakout",
            f"transition_type code of retained slot {i}, oldest -> newest",
            "C_ST_NA above transWindowCount",
            "confirmed transitions only",
        )
        for i in range(1, TRANSITION_WINDOW_CAPACITY + 1)
    ],
    TransportField(
        10,
        "lastTransAvailT",
        "int",
        "breakout",
        "availability_time_utc of the newest transition, epoch milliseconds",
        "C_ST_NA when there are no transitions",
        "confirmed transitions only",
    ),
    TransportField(
        11,
        "dispWindowCount",
        "int",
        "regime+momentum",
        "min(DISPLACEMENT_WINDOW_CAPACITY, number of ordered displacements)",
        "0 for an empty history; never absent",
        "confirmed displacements only",
    ),
    *[
        field
        for i in range(1, DISPLACEMENT_WINDOW_CAPACITY + 1)
        for field in (
            TransportField(
                11 + (i - 1) * 3 + 1,
                f"disp{i}Dir",
                "int",
                "regime+momentum",
                f"DisplacementDirection of retained slot {i}, oldest -> newest, as "
                "+1 bullish / -1 bearish. Separate from the class because the "
                "legacy signed code loses direction when the class is NORMAL",
                "C_ST_NA above dispWindowCount",
                "confirmed displacements only",
            ),
            TransportField(
                11 + (i - 1) * 3 + 2,
                f"disp{i}Cls",
                "int",
                "regime+momentum",
                f"DisplacementClassification of retained slot {i} as 0 NORMAL / "
                "1 FAST / 2 VERY_FAST",
                "C_ST_NA above dispWindowCount",
                "confirmed displacements only",
            ),
            TransportField(
                11 + (i - 1) * 3 + 3,
                f"disp{i}Ratio",
                "float",
                "regime+momentum",
                f"range_speed_ratio of retained slot {i}, RAW -- P5 owns the 1.50 "
                "expansion and 2.00 momentum-reference comparisons",
                "None above dispWindowCount",
                "confirmed displacements only",
            ),
        )
    ],
    TransportField(
        21,
        "dispAvailT",
        "int",
        "regime+momentum",
        "availability_time_utc of the NEWEST retained displacement",
        "C_ST_NA when the window is empty",
        "confirmed displacements only",
    ),
    TransportField(
        22,
        "dispClsAtTrans",
        "int",
        "breakout",
        "_displacement_at: the MAXIMUM classification among every displacement "
        "whose availability_time_utc equals the newest transition's -- not the "
        "first match, not the latest displacement overall",
        "C_ST_NA when no transition, or no displacement shares its availability",
        "confirmed only; matched on availability time",
    ),
    TransportField(
        23,
        "pbImpulsePrice",
        "float",
        "pullback",
        "pivot_price of the impulse swing _retracement_depth selected: the last "
        "SWING_HIGH when bullish, the last SWING_LOW when bearish",
        "None when the source returns no depth",
        "confirmed swings only",
    ),
    TransportField(
        24,
        "pbOriginPrice",
        "float",
        "pullback",
        "pivot_price of the last opposite-type swing at or before the impulse "
        "swing's pivot_start_time_utc (the <= branch)",
        "None when the source returns no depth",
        "confirmed swings only",
    ),
    TransportField(
        25,
        "pbPullbackPrice",
        "float",
        "pullback",
        "pivot_price of the last opposite-type swing strictly after the impulse "
        "swing's pivot_start_time_utc (the > branch)",
        "None when the source returns no depth",
        "confirmed swings only",
    ),
    TransportField(
        26,
        "pbValid",
        "bool",
        "pullback",
        "True when _retracement_depth returns a depth: all three swings exist "
        "and the impulse leg is strictly positive",
        "False; the three prices are then all None",
        "confirmed swings only",
    ),
)

FIELD_COUNT: Final = 26
FIELD_NAMES: Final[tuple[str, ...]] = tuple(f.name for f in FIELDS)
FIELDS_BY_NAME: Final[dict[str, TransportField]] = {f.name: f for f in FIELDS}


@dataclass(frozen=True)
class P5TransportRecord:
    """One timeframe's extension payload: exactly the 26 contract fields."""

    stateAvailT: int
    contStreak: int
    priorOppStreak: int
    exhaustFlag: int
    transWindowCount: int
    trans1Type: int
    trans2Type: int
    trans3Type: int
    trans4Type: int
    lastTransAvailT: int
    dispWindowCount: int
    disp1Dir: int
    disp1Cls: int
    disp1Ratio: float | None
    disp2Dir: int
    disp2Cls: int
    disp2Ratio: float | None
    disp3Dir: int
    disp3Cls: int
    disp3Ratio: float | None
    dispAvailT: int
    dispClsAtTrans: int
    pbImpulsePrice: float | None
    pbOriginPrice: float | None
    pbPullbackPrice: float | None
    pbValid: bool

    def as_dict(self) -> dict[str, object]:
        return {f.name: getattr(self, f.name) for f in dataclass_fields(self)}

    def differing_fields(self, other: P5TransportRecord) -> tuple[str, ...]:
        """Field-level diff. Digest equality is never accepted as a substitute
        for this, so the comparison that matters is the one reported."""
        mine, theirs = self.as_dict(), other.as_dict()
        return tuple(name for name in FIELD_NAMES if mine[name] != theirs[name])


def record_field_names() -> tuple[str, ...]:
    """The dataclass's own field order, for cross-checking against FIELDS."""
    return tuple(f.name for f in dataclass_fields(P5TransportRecord))
