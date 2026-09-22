"""RC5 user-facing market structure: HH / HL / LH / LL.

There is NO second swing detector here. The population is the canonical
meaningful swing sidecar -- the swings the structure walk actually used, which
is the same population BOS / CHOCH are built from. Internal SH / SL remain
untouched and available; this only decides what a student is shown.

CAUSALITY. A label becomes knowable when the swing is CONFIRMED, not when its
pivot printed. Pine may later draw the text back at the pivot candle; the
semantic fact still belongs to the confirmation bar, and nothing in backtest or
event logic may know it earlier.

EQUALITY IS NOT A NEW TOLERANCE. Two pivots that are equal within the swing's
own frozen ``pivot_tie_tolerance`` are ambiguous, and an ambiguous pair gets NO
label rather than being forced into HH or LH. That tolerance already governs
pivot ties in the measurement layer; this reuses it rather than inventing a
structural epsilon.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Any

from btmm_ai_scanner.domain.enums import SwingType

__all__ = [
    "Rc5StructureLabel",
    "StructureLabel",
    "label_market_structure",
]


class StructureLabel(StrEnum):
    HIGHER_HIGH = "HH"
    LOWER_HIGH = "LH"
    HIGHER_LOW = "HL"
    LOWER_LOW = "LL"


@dataclass(frozen=True)
class Rc5StructureLabel:
    swing_record_id: Any
    label: StructureLabel
    price: Decimal
    #: when the label became KNOWABLE -- the swing's confirmation, never the
    #: pivot time it may later be drawn at
    available_from_utc: datetime
    previous_swing_record_id: Any


def label_market_structure(
    swings: Any,
    ledger: Any,
) -> tuple[Rc5StructureLabel, ...]:
    """Label consecutive meaningful highs and lows.

    Highs and lows are sequenced independently, because "higher high" compares
    a high with the previous HIGH, not with whatever swing happened to confirm
    in between.

    A swing with no sidecar record is texture the walk never used: it keeps its
    internal SH / SL identity and gets no user-facing label.
    """
    meaningful = [s for s in swings if ledger.swing_role(s.record_id) is not None]
    meaningful.sort(
        key=lambda s: (s.meaningful_confirmation_time_utc, str(s.record_id))
    )

    previous: dict[Any, Any] = {}
    out: list[Rc5StructureLabel] = []
    for swing in meaningful:
        side = swing.swing_type
        earlier = previous.get(side)
        previous[side] = swing
        if earlier is None:
            continue
        difference = swing.pivot_price - earlier.pivot_price
        tolerance = swing.pivot_tie_tolerance
        if abs(difference) <= tolerance:
            # equal within the frozen pivot-tie tolerance: genuinely ambiguous,
            # so no label is forced.
            continue
        if side is SwingType.SWING_HIGH:
            label = (
                StructureLabel.HIGHER_HIGH
                if difference > 0
                else StructureLabel.LOWER_HIGH
            )
        else:
            label = (
                StructureLabel.HIGHER_LOW
                if difference > 0
                else StructureLabel.LOWER_LOW
            )
        out.append(
            Rc5StructureLabel(
                swing_record_id=swing.record_id,
                label=label,
                price=swing.pivot_price,
                available_from_utc=swing.meaningful_confirmation_time_utc,
                previous_swing_record_id=earlier.record_id,
            )
        )
    return tuple(out)
