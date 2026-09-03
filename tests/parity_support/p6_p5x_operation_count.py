"""Deterministic operation-count model for the P5 transport extension's scans.

Test/parity tooling only. Nothing in ``src/`` imports this.

WHY THIS EXISTS
----------------
TradingView exposes no reliable internal wall-clock API, and the live A/B
resource investigation (MEGA-AUTONOMOUS-17) found the "heavy script" warning
did not reproduce across seven consecutive attach/reload/timeframe-switch
operations on the extended P6 DEV, in isolation or combined with the control.
That result does not license silence about cost, though: it only says the
observed warning was not a reliable, reproducible signal. This module answers
the question in the one way that IS reliable on this platform -- by counting
element visits mechanically, independent of TradingView's own timing.

WHAT IS COUNTED
----------------
Every backward/forward scan the extension's Pine source (``f_p6TfProjection``)
performs once per confirmed bar, per requested context:

* ``contStreak`` / ``priorOppStreak`` -- backward walks over the transition
  event array, each stopping at the first non-matching element (so their COST
  is bounded by the length of a matching run, not by the array length).
* ``exhaustFlag`` -- backward walk over the swing array, stopping once two
  same-type swings are found.
* ``pullback impulse search`` -- backward walk over the swing array, stopping
  at the first swing of the impulse type.
* ``pullback role scan`` -- FORWARD walk over the ENTIRE swing array with NO
  early exit (it must see every swing to find the LAST origin and the LAST
  pullback candidate).
* ``dispClsAtTrans`` -- FORWARD walk over the ENTIRE per-candle displacement
  array with NO early exit, bounded only by ``lookbackWindow`` (300), because
  ``xDspAvail`` is pruned to exactly that length every confirmed bar.

THE FINDING THIS MODEL MAKES VISIBLE
--------------------------------------
The pullback role scan and the displacement-at scan are the only two that
cannot exit early, and of those, ``dispClsAtTrans`` is unconditionally the
largest: it scans a fixed-length 300-element array on every confirmed bar of
every one of the six requested contexts, for as long as any transition exists
-- which in practice is almost the entire warm-up. The pullback role scan is
bounded by SWING count instead, which in the observed live capture ran in the
50-90 range per context, an order of magnitude below 300.

So if a future capture DOES show a reproducible, material slowdown, this is
where to look first -- not because this file proves the extension is too slow
today (it does not; see the resource report), but because it is the biggest
fixed per-bar cost that is possible to reduce (rolling max/min over a bounded
window) without touching any of the twenty-two other reductions this campaign
already proved correct.
"""

from __future__ import annotations

from dataclasses import dataclass

#: The context's own analytical window (P6 DEV `lookbackWindow` default).
LOOKBACK_WINDOW = 300

#: `_displacement_at`'s scan target: exactly `lookbackWindow`, always, because
#: `xDspAvail` is pruned to this length on every confirmed bar.
DISPLACEMENT_AT_SCAN_LENGTH = LOOKBACK_WINDOW


@dataclass(frozen=True)
class ScanCost:
    """One reducer's per-bar cost, as element visits -- not wall-clock time."""

    name: str
    bounded: bool
    early_exit: bool
    worst_case_bound: str
    observed_typical: int


#: The seven scans f_p6TfProjection performs once per confirmed bar, per
#: context. `observed_typical` is read from the live FXCM capture in the
#: resource report (swing/event counts around 50-90; the two bounded windows
#: are literally always at their cap once warm).
SCANS: tuple[ScanCost, ...] = (
    ScanCost("transWindowCount extraction", True, True, "min(4, count)", 4),
    ScanCost("dispWindowCount extraction", True, True, "min(3, count)", 3),
    ScanCost("contStreak", False, True, "len(transitions)", 4),
    ScanCost("priorOppStreak", False, True, "len(transitions)", 0),
    ScanCost("exhaustFlag", False, True, "len(swings)", 2),
    ScanCost("pullback impulse search", False, True, "len(swings)", 3),
    ScanCost(
        "pullback role scan (origin+pullback)", False, False, "len(swings)", 66
    ),
    ScanCost(
        "dispClsAtTrans", True, False, "lookbackWindow", DISPLACEMENT_AT_SCAN_LENGTH
    ),
)


def per_bar_visits(
    swing_count: int, transition_count: int, displacement_window: int = LOOKBACK_WINDOW
) -> dict[str, int]:
    """Element-visit count for one confirmed bar, one context.

    Bounded/early-exit scans are counted at their WORST case (the array
    length), which overstates their true cost on any run where they exit
    early -- deliberately, since the point is an upper bound, not a measured
    average.
    """
    return {
        "transWindowCount extraction": min(4, transition_count),
        "dispWindowCount extraction": min(3, displacement_window),
        "contStreak": transition_count,
        "priorOppStreak": transition_count,
        "exhaustFlag": swing_count,
        "pullback impulse search": swing_count,
        "pullback role scan (origin+pullback)": swing_count,
        "dispClsAtTrans": displacement_window,
    }


def total_visits_over_warmup(
    confirmed_bars: int,
    *,
    swing_count: int,
    transition_count: int,
    contexts: int = 6,
    displacement_window: int = LOOKBACK_WINDOW,
) -> int:
    """Worst-case total element visits across the whole warm-up, all contexts.

    `confirmed_bars` here is the number of bars over which the projection
    RUNS the extension block (i.e. `if barstate.isconfirmed`), which is the
    warm-up length, not the raw calc_bars_count envelope.
    """
    per_bar = per_bar_visits(swing_count, transition_count, displacement_window)
    return sum(per_bar.values()) * confirmed_bars * contexts


def total_visits_by_reducer(
    confirmed_bars: int,
    *,
    swing_count: int,
    transition_count: int,
    contexts: int = 6,
    displacement_window: int = LOOKBACK_WINDOW,
) -> dict[str, int]:
    """Same total, broken out per reducer -- shows where the cost concentrates."""
    per_bar = per_bar_visits(swing_count, transition_count, displacement_window)
    return {
        name: visits * confirmed_bars * contexts for name, visits in per_bar.items()
    }
