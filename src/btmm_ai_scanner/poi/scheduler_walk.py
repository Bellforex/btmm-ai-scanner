"""A6-B1-B7: exact cursor -> LifecycleWalkResult adapter.

Reconstructs the ``LifecycleWalkResult`` that ``advance_poi_cursor`` would return
for a cursor already advanced to the current candle, WITHOUT re-feeding history and
WITHOUT calling ``run_poi_lifecycle``. This lets the event-driven analyzer read a
scheduler-held cursor (woken or dormant, materialized to the head) and obtain its
exact public lifecycle state.

Equivalence to ``advance_poi_cursor``'s returned walk (verified by reading that
function and by the every-prefix production differential):

* terminal      -> committed transitions, GENUINE_INVALIDATION, taps still live,
                   ``terminal_last_seen``.
* pre-start     -> empty walk (NO_BREACH, tap 0), no ``last_seen``.
* committed     -> committed transitions, ``resume_status`` (== the walk's final
  (empty buffer)    status when fully committed), ``last_seen`` = the current
                   candle (the last candle the committed floor advanced past).
* open window   -> re-run the bounded ``_walk_inner`` over the cursor's suffix
  (buffer)         buffer (O(window)); its transitions/final_status/last_seen are
                   exactly what the last advance produced.
"""

from btmm_ai_scanner.contracts.normalized_candle import NormalizedCandle
from btmm_ai_scanner.poi.configuration import PoiConfiguration
from btmm_ai_scanner.poi.enums import PoiFreshnessStatus, PoiLifecycleStatus
from btmm_ai_scanner.poi.lifecycle import LifecycleWalkResult, _classify_tap_count
from btmm_ai_scanner.poi.lifecycle_cursor import PoiLifecycleCursor, _walk_inner


def cursor_walk_result(
    cursor: PoiLifecycleCursor,
    current_candle: NormalizedCandle,
    configuration: PoiConfiguration,
) -> LifecycleWalkResult:
    """The exact ``LifecycleWalkResult`` for ``cursor`` at the current prefix.
    ``cursor`` must already be advanced/materialized to the head (``total_count``
    == the current candle count); ``current_candle`` is that head candle."""
    freshness = (
        PoiFreshnessStatus.INTERACTED
        if cursor.tap_count > 0
        else PoiFreshnessStatus.FRESH
    )
    tap_classification = _classify_tap_count(cursor.tap_count)
    n = cursor.total_count
    age = max(0, n - cursor.start_index) if cursor.start_index is not None else 0

    if cursor.terminal:
        return LifecycleWalkResult(
            transitions=cursor.committed_transitions,
            final_status=PoiLifecycleStatus.GENUINE_INVALIDATION_CONFIRMED,
            freshness_status=freshness,
            tap_count=cursor.tap_count,
            tap_classification=tap_classification,
            age_in_confirmed_bars=age,
            last_seen_candle=cursor.terminal_last_seen,
        )

    if cursor.start_index is None:
        return LifecycleWalkResult(
            transitions=(),
            final_status=PoiLifecycleStatus.NO_BREACH,
            freshness_status=PoiFreshnessStatus.FRESH,
            tap_count=0,
            tap_classification=None,
            age_in_confirmed_bars=0,
            last_seen_candle=None,
        )

    if not cursor.candle_buffer:
        # Fully committed (dormant): the committed floor advanced past the head, so
        # the walk saw the current candle last as a non-breaching commit.
        return LifecycleWalkResult(
            transitions=cursor.committed_transitions,
            final_status=cursor.resume_status,
            freshness_status=freshness,
            tap_count=cursor.tap_count,
            tap_classification=tap_classification,
            age_in_confirmed_bars=age,
            last_seen_candle=current_candle,
        )

    walk = _walk_inner(
        cursor.candle_buffer,
        cursor.atr_buffer,
        cursor.symbol,
        cursor.timeframe,
        cursor.poi_record_id,
        cursor.direction,
        cursor.zone_top,
        cursor.zone_bottom,
        cursor.zone_height,
        configuration.minimum_price_tick,
        cursor.resume_status,
        configuration,
    )
    return LifecycleWalkResult(
        transitions=cursor.committed_transitions + walk.transitions,
        final_status=walk.final_status,
        freshness_status=freshness,
        tap_count=cursor.tap_count,
        tap_classification=tap_classification,
        age_in_confirmed_bars=age,
        last_seen_candle=walk.last_seen_candle,
    )
