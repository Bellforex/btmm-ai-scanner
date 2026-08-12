"""A6-B1-B: exact no-op fast-forward for a dormant POI lifecycle cursor.

The accepted ``advance_poi_cursor`` must be fed every candle sequentially (its tap
loop and committed-floor bookkeeping assume no gaps). The event scheduler wakes a
cursor only on candles that touch, breach, fall in an open window, or start its
lifecycle; between wakes a cursor is *dormant* and the skipped candles are
provably no-ops for it. This module closes that gap in O(1) instead of replaying
the skipped candles one by one, producing a cursor byte-identical to the one N
sequential ``advance_poi_cursor`` calls over those no-op candles would produce.

A dormant advance over a candle that (post-start) neither touches nor breaches the
zone, with the cursor committed (empty suffix buffer, ``resume_i == total_count``)
and not mid-tap-run (``in_tap`` False), changes only three counters:
``total_count``, ``resume_i`` and ``tap_next_index`` each advance by one; every
other field is invariant (verified by reading ``advance_poi_cursor``). A pre-start
candle (``start_index is None`` — no candle after the POI's availability yet)
advances ``total_count``, ``start_search_next`` and ``resume_i`` only. So a jump
of K such candles is exactly a bump of those counters by K.

The strict preconditions are asserted, and the equivalence is proven by the
permanent differential test (fast-forward + one real advance == sequential advance
over the same candles). ``lifecycle_cursor`` is not modified; this only reads its
public frozen dataclass and rebuilds a new instance.
"""

from btmm_ai_scanner.poi.lifecycle_cursor import PoiLifecycleCursor


def fast_forward_poi_cursor(
    cursor: PoiLifecycleCursor, target_total_count: int
) -> PoiLifecycleCursor:
    """Advance ``cursor.total_count`` up to ``target_total_count`` treating every
    intervening candle as a no-op (the caller — the scheduler — guarantees, via
    the touch/breach index registrations, that none of them touch or breach this
    POI). Exact equivalent of that many ``advance_poi_cursor`` no-op calls."""
    if target_total_count == cursor.total_count:
        return cursor
    if target_total_count < cursor.total_count:
        raise ValueError("fast-forward target precedes the cursor's position")
    if cursor.terminal:
        # A terminal cursor's breach walk is frozen, but its tap accounting still
        # reacts to touching candles — so a terminal cursor is only ever
        # fast-forwarded over NON-touching candles. That is still a pure
        # total_count bump (the terminal branch of advance_poi_cursor leaves
        # resume_i/tap state untouched and only in_tap may flip to False, which it
        # already is for a dormant cursor). Guard the same in_tap precondition.
        assert not cursor.in_tap, "terminal fast-forward requires a closed tap run"
        # The terminal branch of advance_poi_cursor still runs the tap loop, so
        # tap_next_index advances to the head each candle (only over non-touching
        # candles here, so tap_count/in_tap are unchanged). start_index is set for
        # any terminal cursor (it breached), so the tap loop is always entered.
        return PoiLifecycleCursor(
            symbol=cursor.symbol,
            timeframe=cursor.timeframe,
            poi_record_id=cursor.poi_record_id,
            direction=cursor.direction,
            zone_top=cursor.zone_top,
            zone_bottom=cursor.zone_bottom,
            zone_height=cursor.zone_height,
            availability_time_utc=cursor.availability_time_utc,
            total_count=target_total_count,
            start_index=cursor.start_index,
            start_search_next=cursor.start_search_next,
            tap_count=cursor.tap_count,
            in_tap=cursor.in_tap,
            tap_next_index=target_total_count,
            resume_i=cursor.resume_i,
            resume_status=cursor.resume_status,
            committed_transitions=cursor.committed_transitions,
            terminal=True,
            terminal_last_seen=cursor.terminal_last_seen,
            candle_buffer=(),
            atr_buffer=(),
        )

    if cursor.start_index is None:
        # Pre-start: no candle after the POI's availability yet. Skipped candles
        # only advance the position counters; start_index stays None (the caller
        # must NOT fast-forward across the first eligible candle — that one is
        # woken so advance_poi_cursor can resolve start_index).
        return PoiLifecycleCursor(
            symbol=cursor.symbol,
            timeframe=cursor.timeframe,
            poi_record_id=cursor.poi_record_id,
            direction=cursor.direction,
            zone_top=cursor.zone_top,
            zone_bottom=cursor.zone_bottom,
            zone_height=cursor.zone_height,
            availability_time_utc=cursor.availability_time_utc,
            total_count=target_total_count,
            start_index=None,
            start_search_next=target_total_count,
            tap_count=cursor.tap_count,
            in_tap=cursor.in_tap,
            tap_next_index=cursor.tap_next_index,
            resume_i=target_total_count,
            resume_status=cursor.resume_status,
            committed_transitions=cursor.committed_transitions,
            terminal=False,
            terminal_last_seen=None,
            candle_buffer=(),
            atr_buffer=(),
        )

    # Post-start dormant: committed (empty suffix buffer, resume_i caught up to
    # the head) and not mid-tap-run. Under these preconditions each skipped candle
    # is a pure no-op advance that bumps total_count, resume_i and tap_next_index.
    assert not cursor.in_tap, "dormant fast-forward requires a closed tap run"
    assert len(cursor.candle_buffer) == 0, (
        "dormant fast-forward requires a fully committed cursor (empty buffer)"
    )
    assert cursor.resume_i == cursor.total_count, (
        "dormant fast-forward requires resume_i caught up to the head"
    )
    return PoiLifecycleCursor(
        symbol=cursor.symbol,
        timeframe=cursor.timeframe,
        poi_record_id=cursor.poi_record_id,
        direction=cursor.direction,
        zone_top=cursor.zone_top,
        zone_bottom=cursor.zone_bottom,
        zone_height=cursor.zone_height,
        availability_time_utc=cursor.availability_time_utc,
        total_count=target_total_count,
        start_index=cursor.start_index,
        start_search_next=cursor.start_search_next,
        tap_count=cursor.tap_count,
        in_tap=False,
        tap_next_index=target_total_count,
        resume_i=target_total_count,
        resume_status=cursor.resume_status,
        committed_transitions=cursor.committed_transitions,
        terminal=False,
        terminal_last_seen=None,
        candle_buffer=(),
        atr_buffer=(),
    )
