"""V1-A characterization report generator (test/validation tooling only).

Consumes a ``v1a_harness.DevReplayResult`` (or the JSON a
``v1a_run_dev.py`` run wrote to disk) and produces the protocol §18 report:
event/POI counts, MFE/MAE distributions, fixed-horizon directional
returns, ATR-normalized threshold-reach + path ordering, POI zone-touch/
invalidation rates, reaction characterization, frequency tables, the
exclusion table (§13), and the §16 segmentation tables.

Every excursion/return/threshold number here comes from
``v1a_outcome_math`` — this module only aggregates already-computed cells
into distribution statistics and segment buckets, per protocol §16/§18.
It contains NO win-rate/profit-factor/expectancy/R-multiple/drawdown/
Sharpe/equity-curve computation anywhere (protocol §12 hard prohibition),
and it never invents a metric name that implies trade profitability.
"""

from __future__ import annotations

import statistics
from dataclasses import dataclass
from decimal import Decimal

from btmm_ai_scanner.poi.enums import LIFECYCLE_ELIGIBLE_POI_TYPES
from tests.parity_support.v1a_outcome_math import (
    ATR_THRESHOLDS,
    HORIZONS,
    ForwardBar,
    compute_directional_returns,
    compute_mae,
    compute_mfe,
    compute_path_ordering,
    compute_poi_touch_outcome,
    compute_threshold_reach_grid,
)

_REACTION_HORIZON_BARS = 48  # bounded by the same frozen horizon grid's own max


@dataclass
class ExclusionCounts:
    horizon_censored: int = 0
    atr_warmup: int = 0
    incomplete_terminal_lifecycle: int = 0
    missing_context: int = 0


def _forward_bars(dev_m15_ohlc: list[dict], start_index: int) -> tuple[ForwardBar, ...]:
    return tuple(
        ForwardBar(high=Decimal(row["high"]), low=Decimal(row["low"]), close=Decimal(row["close"]))
        for row in dev_m15_ohlc[start_index:]
    )


def compute_event_outcomes(
    events: list[dict],
    dev_m15_ohlc: list[dict],
    atr_series: list[Decimal | None],
    displacement_by_bar_index: dict[int, tuple[str, str]],
) -> tuple[list[dict], ExclusionCounts]:
    exclusions = ExclusionCounts()
    outcomes: list[dict] = []
    n_bars = len(dev_m15_ohlc)

    for event in events:
        bar_index = event["bar_index"]
        bullish = event["poi_direction"] == "BULLISH"
        reference = Decimal(dev_m15_ohlc[bar_index]["close"])
        forward = _forward_bars(dev_m15_ohlc, bar_index + 1)
        atr_at_event = atr_series[bar_index] if bar_index < len(atr_series) else None
        if atr_at_event is None:
            exclusions.atr_warmup += 1

        returns = compute_directional_returns(reference, forward, bullish=bullish)
        mfe = compute_mfe(reference, forward, bullish=bullish, atr_at_event=atr_at_event)
        mae = compute_mae(reference, forward, bullish=bullish, atr_at_event=atr_at_event)
        for r in returns:
            if r.censored:
                exclusions.horizon_censored += 1
        grid = compute_threshold_reach_grid(reference, forward, bullish=bullish, atr_at_event=atr_at_event)
        ordering = compute_path_ordering(grid)

        # Reaction characterization (protocol §11): first FAST/VERY_FAST
        # displacement observation within the horizon grid's own max window,
        # in the frozen reused primitive's own labels.
        reaction_delay: int | None = None
        reaction_direction: str | None = None
        reaction_classification: str | None = None
        for offset in range(1, min(_REACTION_HORIZON_BARS, n_bars - bar_index - 1) + 1):
            candidate = displacement_by_bar_index.get(bar_index + offset)
            if candidate is not None and candidate[1] in ("FAST", "VERY_FAST"):
                reaction_delay = offset
                reaction_direction, reaction_classification = candidate
                break

        outcomes.append(
            {
                "event": event,
                "event_close_reference": str(reference),
                "atr_at_event": str(atr_at_event) if atr_at_event is not None else None,
                "directional_returns": [
                    {
                        "horizon": r.horizon,
                        "value": str(r.directional_return),
                        "pct": str(r.directional_return_pct),
                        "censored": r.censored,
                    }
                    for r in returns
                ],
                "mfe": [
                    {
                        "horizon": r.horizon,
                        "value": str(r.value),
                        "pct": str(r.pct),
                        "atr_units": str(r.atr_units) if r.atr_units is not None else None,
                        "censored": r.censored,
                    }
                    for r in mfe
                ],
                "mae": [
                    {
                        "horizon": r.horizon,
                        "value": str(r.value),
                        "pct": str(r.pct),
                        "atr_units": str(r.atr_units) if r.atr_units is not None else None,
                        "censored": r.censored,
                    }
                    for r in mae
                ],
                "threshold_reach_favorable": [
                    {"threshold_atr": str(c.threshold_atr), "bar_offset": c.bar_offset}
                    for c in grid.favorable
                ],
                "threshold_reach_adverse": [
                    {"threshold_atr": str(c.threshold_atr), "bar_offset": c.bar_offset}
                    for c in grid.adverse
                ],
                "path_ordering": {str(k): v for k, v in ordering.items()},
                "reaction_delay_bars": reaction_delay,
                "reaction_direction": reaction_direction,
                "reaction_classification": reaction_classification,
            }
        )

    return outcomes, exclusions


def compute_poi_outcomes(
    poi_registry: list[dict],
    dev_m15_ohlc: list[dict],
    atr_series: list[Decimal | None],
    availability_ms_to_bar_index: dict[int, int],
) -> tuple[list[dict], ExclusionCounts]:
    exclusions = ExclusionCounts()
    outcomes: list[dict] = []
    for poi in poi_registry:
        start_index = poi["first_seen_bar_index"] + 1
        forward = _forward_bars(dev_m15_ohlc, start_index)
        atr_lookup = tuple(atr_series[i] for i in range(start_index, len(dev_m15_ohlc)))
        if len(forward) == 0:
            exclusions.missing_context += 1
        outcome = compute_poi_touch_outcome(
            Decimal(poi["zone_top"]),
            Decimal(poi["zone_bottom"]),
            bullish=poi["poi_direction"] == "BULLISH",
            forward_bars=forward,
            atr_lookup=atr_lookup,
        )
        outcomes.append(
            {
                "poi": poi,
                "touched": outcome.touched,
                "first_touch_offset": outcome.first_touch_offset,
                "max_penetration_price": (
                    str(outcome.max_penetration_price)
                    if outcome.max_penetration_price is not None
                    else None
                ),
                "max_penetration_atr": (
                    str(outcome.max_penetration_atr)
                    if outcome.max_penetration_atr is not None
                    else None
                ),
                "far_boundary_crossed": outcome.far_boundary_crossed,
                "censored_no_forward_data": outcome.censored_no_forward_data,
            }
        )
    return outcomes, exclusions


def _distribution(values: list[Decimal]) -> dict:
    if not values:
        return {"n": 0, "mean": None, "median": None, "p25": None, "p75": None, "p90": None}
    floats = [float(v) for v in values]
    floats_sorted = sorted(floats)

    def pct(p: float) -> float:
        if len(floats_sorted) == 1:
            return floats_sorted[0]
        k = (len(floats_sorted) - 1) * p
        f = int(k)
        c = min(f + 1, len(floats_sorted) - 1)
        if f == c:
            return floats_sorted[f]
        return floats_sorted[f] + (floats_sorted[c] - floats_sorted[f]) * (k - f)

    return {
        "n": len(floats),
        "mean": statistics.fmean(floats),
        "median": statistics.median(floats),
        "p25": pct(0.25),
        "p75": pct(0.75),
        "p90": pct(0.90),
    }


def _segment_key(outcome: dict, dimension: str) -> str:
    event = outcome["event"]
    if dimension == "event_type":
        return event["event_type"]
    if dimension == "poi_type":
        return event["poi_type"]
    if dimension == "origin_timeframe":
        return event["origin_timeframe"]
    if dimension == "direction":
        return event["poi_direction"]
    if dimension == "permission":
        return event["btrc_permission"]
    if dimension == "score_band":
        return event["btrc_score_band"]
    if dimension == "btmm_valid":
        return str(event["btmm_valid"])
    if dimension == "trend_alignment":
        return event["trend_alignment"]
    if dimension == "regime":
        return event["regime"]
    if dimension == "session":
        return event["session"] or "UNKNOWN"
    if dimension == "volatility_state":
        return event["volatility_state"] or "UNKNOWN"
    raise ValueError(f"unknown segmentation dimension: {dimension}")


_SEGMENT_DIMENSIONS = (
    "event_type",
    "poi_type",
    "origin_timeframe",
    "direction",
    "permission",
    "score_band",
    "btmm_valid",
    "trend_alignment",
    "regime",
    "session",
    "volatility_state",
)


def build_mfe_mae_segment_tables(event_outcomes: list[dict], horizon: int) -> dict:
    """Protocol §16: MFE/MAE distribution (mean/median/p25/p75/p90/n) per
    segment, for one representative horizon at a time."""
    tables: dict[str, dict[str, dict]] = {}
    for dimension in _SEGMENT_DIMENSIONS:
        buckets: dict[str, list[Decimal]] = {}
        mae_buckets: dict[str, list[Decimal]] = {}
        for outcome in event_outcomes:
            cell = next(c for c in outcome["mfe"] if c["horizon"] == horizon)
            mae_cell = next(c for c in outcome["mae"] if c["horizon"] == horizon)
            if cell["censored"]:
                continue
            key = _segment_key(outcome, dimension)
            buckets.setdefault(key, []).append(Decimal(cell["value"]))
            mae_buckets.setdefault(key, []).append(Decimal(mae_cell["value"]))
        tables[dimension] = {
            "mfe": {k: _distribution(v) for k, v in buckets.items()},
            "mae": {k: _distribution(v) for k, v in mae_buckets.items()},
        }
    return tables


def build_directional_return_table(event_outcomes: list[dict]) -> dict:
    """Fixed-horizon directional returns per segment (event_type only, to
    keep the primary report tractable — every other dimension is available
    identically via ``build_mfe_mae_segment_tables``'s own pattern and is
    left to the full artifact, not the committed summary)."""
    table: dict[int, dict[str, dict]] = {}
    for horizon in HORIZONS:
        buckets: dict[str, list[Decimal]] = {}
        for outcome in event_outcomes:
            cell = next(c for c in outcome["directional_returns"] if c["horizon"] == horizon)
            if cell["censored"]:
                continue
            key = _segment_key(outcome, "event_type")
            buckets.setdefault(key, []).append(Decimal(cell["value"]))
        table[horizon] = {k: _distribution(v) for k, v in buckets.items()}
    return table


def build_threshold_reach_rates(event_outcomes: list[dict]) -> dict:
    favorable_rates: dict[str, dict] = {}
    adverse_rates: dict[str, dict] = {}
    for threshold in ATR_THRESHOLDS:
        threshold_str = str(threshold)
        fav_hits = 0
        fav_total = 0
        adv_hits = 0
        adv_total = 0
        for outcome in event_outcomes:
            fav_cell = next(
                c for c in outcome["threshold_reach_favorable"] if c["threshold_atr"] == threshold_str
            )
            adv_cell = next(
                c for c in outcome["threshold_reach_adverse"] if c["threshold_atr"] == threshold_str
            )
            if outcome["atr_at_event"] is not None:
                fav_total += 1
                adv_total += 1
                if fav_cell["bar_offset"] is not None:
                    fav_hits += 1
                if adv_cell["bar_offset"] is not None:
                    adv_hits += 1
        favorable_rates[threshold_str] = {
            "reached": fav_hits,
            "total": fav_total,
            "rate": (fav_hits / fav_total) if fav_total else None,
        }
        adverse_rates[threshold_str] = {
            "reached": adv_hits,
            "total": adv_total,
            "rate": (adv_hits / adv_total) if adv_total else None,
        }
    return {"favorable": favorable_rates, "adverse": adverse_rates}


def build_path_ordering_summary(event_outcomes: list[dict]) -> dict:
    summary: dict[str, dict[str, int]] = {}
    for threshold in ATR_THRESHOLDS:
        threshold_str = str(threshold)
        counts: dict[str, int] = {}
        for outcome in event_outcomes:
            ordering = outcome["path_ordering"].get(threshold_str)
            if ordering is None:
                continue
            counts[ordering] = counts.get(ordering, 0) + 1
        summary[threshold_str] = counts
    return summary


def build_poi_geometry_summary(poi_outcomes: list[dict]) -> dict:
    total = len(poi_outcomes)
    touched = sum(1 for o in poi_outcomes if o["touched"])
    far_crossed = sum(1 for o in poi_outcomes if o["far_boundary_crossed"])
    censored = sum(1 for o in poi_outcomes if o["censored_no_forward_data"])
    by_type: dict[str, dict] = {}
    for outcome in poi_outcomes:
        poi_type = outcome["poi"]["poi_type"]
        bucket = by_type.setdefault(poi_type, {"total": 0, "touched": 0, "far_crossed": 0})
        bucket["total"] += 1
        if outcome["touched"]:
            bucket["touched"] += 1
        if outcome["far_boundary_crossed"]:
            bucket["far_crossed"] += 1
    return {
        "total_pois": total,
        "touched": touched,
        "touch_rate": (touched / total) if total else None,
        "far_boundary_crossed": far_crossed,
        "censored_no_forward_data": censored,
        "by_poi_type": by_type,
    }


def build_reaction_summary(event_outcomes: list[dict]) -> dict:
    total = len(event_outcomes)
    with_reaction = sum(1 for o in event_outcomes if o["reaction_delay_bars"] is not None)
    delays = [o["reaction_delay_bars"] for o in event_outcomes if o["reaction_delay_bars"] is not None]
    return {
        "total_events": total,
        "events_with_reaction": with_reaction,
        "reaction_occurrence_rate": (with_reaction / total) if total else None,
        "delay_distribution": _distribution([Decimal(d) for d in delays]),
    }


def build_frequency_tables(events: list[dict], poi_registry: list[dict]) -> dict:
    events_by_day: dict[str, int] = {}
    events_by_week: dict[str, int] = {}
    for event in events:
        events_by_day[event["calendar_day"]] = events_by_day.get(event["calendar_day"], 0) + 1
        events_by_week[event["iso_week"]] = events_by_week.get(event["iso_week"], 0) + 1
    pois_by_day: dict[str, int] = {}
    for poi in poi_registry:
        day = poi["availability_time_utc"][:10]
        pois_by_day[day] = pois_by_day.get(day, 0) + 1
    return {
        "events_per_day": events_by_day,
        "events_per_week": events_by_week,
        "pois_per_day": pois_by_day,
        "distinct_days_with_events": len(events_by_day),
        "distinct_weeks_with_events": len(events_by_week),
    }


def build_permission_churn(events: list[dict]) -> dict:
    entered = sum(1 for e in events if e["event_type"] == "PERMISSION_ENTERED_ACTIONABLE")
    lost = sum(1 for e in events if e["event_type"] == "PERMISSION_LOST_ACTIONABLE")
    return {"permission_entered_actionable": entered, "permission_lost_actionable": lost}


def compute_incomplete_terminal_lifecycle_count(
    poi_registry: list[dict], events: list[dict]
) -> int:
    """Protocol §13 ``incomplete_terminal_lifecycle``: a lifecycle-eligible
    POI (per the closed P3 registry, ``poi.enums.LIFECYCLE_ELIGIBLE_POI_TYPES``
    -- the same eligibility set the reused engines themselves use) that never
    reached ``POI_TERMINAL`` before the DEV window ends. Derived from the
    already-collected event stream (never a new invalidation rule)."""
    terminal_poi_ids = {e["poi_record_id"] for e in events if e["event_type"] == "POI_TERMINAL"}
    eligible_type_values = {t.value for t in LIFECYCLE_ELIGIBLE_POI_TYPES}
    return sum(
        1
        for poi in poi_registry
        if poi["poi_type"] in eligible_type_values and poi["record_id"] not in terminal_poi_ids
    )


def build_report(
    events: list[dict],
    poi_registry: list[dict],
    event_outcomes: list[dict],
    poi_outcomes: list[dict],
    event_exclusions: ExclusionCounts,
    poi_exclusions: ExclusionCounts,
) -> dict:
    event_type_counts: dict[str, int] = {}
    for event in events:
        event_type_counts[event["event_type"]] = event_type_counts.get(event["event_type"], 0) + 1

    incomplete_terminal = compute_incomplete_terminal_lifecycle_count(poi_registry, events)
    event_exclusions.incomplete_terminal_lifecycle = incomplete_terminal
    poi_exclusions.incomplete_terminal_lifecycle = incomplete_terminal

    return {
        "counts": {
            "total_events": len(events),
            "events_by_type": event_type_counts,
            "total_pois": len(poi_registry),
        },
        "mfe_mae_by_segment_horizon_1": build_mfe_mae_segment_tables(event_outcomes, horizon=1),
        "mfe_mae_by_segment_horizon_8": build_mfe_mae_segment_tables(event_outcomes, horizon=8),
        "mfe_mae_by_segment_horizon_48": build_mfe_mae_segment_tables(event_outcomes, horizon=48),
        "directional_returns_by_event_type": build_directional_return_table(event_outcomes),
        "threshold_reach_rates": build_threshold_reach_rates(event_outcomes),
        "path_ordering": build_path_ordering_summary(event_outcomes),
        "poi_geometry": build_poi_geometry_summary(poi_outcomes),
        "reaction": build_reaction_summary(event_outcomes),
        "frequency": build_frequency_tables(events, poi_registry),
        "permission_churn": build_permission_churn(events),
        "exclusions": {
            "events": {
                "horizon_censored": event_exclusions.horizon_censored,
                "atr_warmup": event_exclusions.atr_warmup,
                "incomplete_terminal_lifecycle": event_exclusions.incomplete_terminal_lifecycle,
                "missing_context": event_exclusions.missing_context,
            },
            "pois": {
                "horizon_censored": poi_exclusions.horizon_censored,
                "atr_warmup": poi_exclusions.atr_warmup,
                "incomplete_terminal_lifecycle": poi_exclusions.incomplete_terminal_lifecycle,
                "missing_context": poi_exclusions.missing_context,
            },
        },
    }
