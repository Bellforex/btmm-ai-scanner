"""A6-B2-B: exact no-op fast-forward for a dormant BTMM lifecycle cursor.

``advance_btmm_cursor`` (B2-A, unmodified) must be fed every candle sequentially
for two of its four stages — WAIT_REACTION_START (``running_anchor`` accumulates
``min``/``max`` over every candle since interaction, whether or not the reaction
actually starts that candle) and the reaction window buffer (every candle in the
bounded window must be appended) are NOT skippable; a setup in either stage is
always scheduled every candle via the due-bar registry, never fast-forwarded.

The other two stages ARE true no-ops on a non-triggering candle, verified by
reading ``advance_btmm_cursor``:

* Pre-forming (``entered_forming_index is None``): a candle whose availability
  does not yet exceed the candidate's changes nothing but ``total_count`` and
  ``prev_candle``.
* Open interaction scan, non-touching candle (``entered_forming_index is not
  None and interaction_index is None``): ``find_first_interaction`` over a
  single-candle window returns ``None`` for a candle that fails
  ``_touches_zone`` — the scheduler's ``interaction_index`` query is byte-
  identical to that predicate, so a candle absent from the query result is
  proven to be a no-op here.
* Fully price-resolved (``tier_result is not None``, or the interaction was
  determined ineligible): nothing downstream of price re-reads candles at all
  (``materialize_btmm_cursor`` is a fixed-cost function over the cached stage
  results plus the current evidence/transition inputs) — permanently dormant.

In every skippable case ``prev_candle`` must still advance to the immediately
preceding candle (the open-interaction scan's ``m > 0`` branch reads
``candles[index - 1].close``), so a fast-forward of K candles sets
``prev_candle`` to the candle at ``target_total_count - 1``, not the cursor's
own prior value.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import replace

from btmm_ai_scanner.btmm.lifecycle_cursor import BtmmLifecycleCursor
from btmm_ai_scanner.contracts.normalized_candle import NormalizedCandle


def btmm_cursor_is_fast_forwardable(cursor: BtmmLifecycleCursor) -> bool:
    """True iff the cursor's currently-open stage (if any) is one where every
    non-triggering candle is a proven no-op. False for WAIT_REACTION_START
    (``interaction_index is not None and reaction_start_index is None``, in the
    eligible-interaction branch) and the reaction window buffer (``reaction_
    start_index is not None and tier_result is None``) — those must be advanced
    one candle at a time via the due-bar registry."""
    if cursor.interaction_index is None:
        return True  # pre-forming or open (non-touching) interaction scan.
    from btmm_ai_scanner.btmm.interaction import ELIGIBLE_INTERACTION_CLASSES

    if cursor.interaction_class not in ELIGIBLE_INTERACTION_CLASSES:
        return True  # ineligible interaction: fully price-resolved, terminal.
    return cursor.tier_result is not None


def fast_forward_btmm_cursor(
    cursor: BtmmLifecycleCursor,
    candles: Sequence[NormalizedCandle],
    target_total_count: int,
) -> BtmmLifecycleCursor:
    """Advance ``cursor.total_count`` up to ``target_total_count`` treating every
    intervening candle as a no-op. The caller (the scheduler) guarantees, via the
    forming/interaction index registrations, that none of the skipped candles
    trigger a stage transition, and via ``btmm_cursor_is_fast_forwardable`` that
    the cursor is not mid-reaction-start or mid-window (those are always
    due-scheduled every candle, never skipped). ``candles`` is the full visible
    prefix; only ``candles[target_total_count - 1]`` (the new ``prev_candle``) is
    read."""
    if target_total_count == cursor.total_count:
        return cursor
    if target_total_count < cursor.total_count:
        raise ValueError("fast-forward target precedes the cursor's position")
    assert btmm_cursor_is_fast_forwardable(cursor), (
        "fast-forward requires a dormant-safe stage"
        " (pre-forming, open interaction scan, or fully price-resolved)"
    )
    return replace(
        cursor,
        total_count=target_total_count,
        prev_candle=candles[target_total_count - 1],
    )
