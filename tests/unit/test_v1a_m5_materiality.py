"""Permanent unit tests for the V1-A M5-materiality gate
(``tests/parity_support/v1a_m5_materiality.py``).

These tests deliberately never run the real replay (that is a long-running
empirical operation performed once to produce
``docs/validation/BTRC_V1_V1A_M5_MATERIALITY_ADDENDUM.md`` -- see that
document). What they DO prove, permanently and cheaply:

1. the FULL6/NO_M5 run specs (and the ``ScannerConfiguration`` each
   produces) differ ONLY in the M5 timeframe -- a test that would fail if a
   future edit accidentally changed the date window, warm-up, or another
   timeframe between the two configs/specs;
2. the score-differential / 45- and 65-boundary-crossing counting logic is
   correct on a constructed synthetic example with a known expected delta
   and known expected crossing count;
3. the permission-transition-matrix construction is correct on a synthetic
   example;
4. the P8 event-differential logic (exact match / timing mismatch /
   event-type mismatch / POI-identity mismatch) is correct on a synthetic
   example;
5. the classification logic (Class A vs Class B) is correct given
   constructed mismatch inputs -- including the brief's explicit
   "do not round to equivalence" requirement: a single one-point score
   difference on ONE (POI, bar) pair must force Class B, never Class A.
"""

from __future__ import annotations

from pathlib import Path

from btmm_ai_scanner.config.enums import Timeframe
from tests.parity_support.v1a_m5_materiality import (
    TIMEFRAMES_FULL6,
    TIMEFRAMES_NO_M5,
    EventRecordLite,
    MaterialityDiffReport,
    PoiBarRecord,
    ScoreDiff,
    UniverseDiff,
    build_configuration_for,
    classify_materiality,
    diff_events,
    diff_records,
    full6_spec,
    no_m5_spec,
)

_ROOT = Path(__file__).resolve().parents[2] / "artifacts" / "v1a_validation"


# --------------------------------------------------------------------------
# 1. FULL6/NO_M5 configs differ ONLY in M5
# --------------------------------------------------------------------------


def test_full6_and_no_m5_specs_differ_only_in_timeframes() -> None:
    full6 = full6_spec(_ROOT, max_bars=17)
    no_m5 = no_m5_spec(_ROOT, max_bars=17)

    # Every field except `label` and `timeframes` must be byte-identical --
    # this is exactly the invariant that would break if a future edit
    # changed the window, warm-up, or another timeframe between the two.
    assert full6.dataset_root == no_m5.dataset_root
    assert full6.window_start == no_m5.window_start
    assert full6.window_end == no_m5.window_end
    assert full6.pre_window_lookback_bars == no_m5.pre_window_lookback_bars
    assert full6.max_bars == no_m5.max_bars

    assert set(full6.timeframes) - set(no_m5.timeframes) == {Timeframe.M5}
    assert set(no_m5.timeframes) - set(full6.timeframes) == set()
    assert full6.label != no_m5.label


def test_full6_and_no_m5_configurations_differ_only_in_optional_timeframes() -> None:
    full6_cfg = build_configuration_for(TIMEFRAMES_FULL6)
    no_m5_cfg = build_configuration_for(TIMEFRAMES_NO_M5)

    assert set(full6_cfg.optional_timeframes) - set(no_m5_cfg.optional_timeframes) == {Timeframe.M5}
    assert set(no_m5_cfg.optional_timeframes) - set(full6_cfg.optional_timeframes) == set()

    full6_dump = full6_cfg.model_dump()
    no_m5_dump = no_m5_cfg.model_dump()
    for key in full6_dump:
        if key == "optional_timeframes":
            continue
        assert full6_dump[key] == no_m5_dump[key], f"unexpected config divergence in {key!r}"


def test_full6_config_required_timeframes_unaffected() -> None:
    full6_cfg = build_configuration_for(TIMEFRAMES_FULL6)
    no_m5_cfg = build_configuration_for(TIMEFRAMES_NO_M5)
    assert full6_cfg.required_timeframes == no_m5_cfg.required_timeframes == frozenset({Timeframe.M15})


# --------------------------------------------------------------------------
# helpers to build synthetic PoiBarRecord/EventRecordLite rows without a
# real replay
# --------------------------------------------------------------------------


def _record(
    poi_id: str,
    bar: str,
    *,
    final_confluence_score: int = 50,
    permission: str = "WATCH_ONLY",
    poi_type: str = "ORDER_BLOCK",
    **overrides: object,
) -> PoiBarRecord:
    base = dict(
        poi_record_id=poi_id,
        bar_availability_utc=bar,
        bar_index=0,
        poi_type=poi_type,
        poi_direction="BULLISH",
        poi_timeframe="M15",
        lifecycle_state="STRUCTURALLY_VALIDATED",
        poi_lifecycle_status=None,
        btmm_valid=False,
        trend_alignment="NEUTRAL",
        regime="RANGE",
        momentum_direction=None,
        momentum_acceleration=None,
        breakout_state=None,
        pullback_state=None,
        session_context=None,
        volatility_state=None,
        global_direction="NEUTRAL",
        btmm_score=25,
        poi_score=50,
        trend_score=50,
        regime_score=35,
        momentum_score=50,
        breakout_score=40,
        liquidity_score=40,
        volatility_score=50,
        final_confluence_score=final_confluence_score,
        permission=permission,
    )
    base.update(overrides)
    return PoiBarRecord(**base)  # type: ignore[arg-type]


# --------------------------------------------------------------------------
# 2. score-differential / boundary-crossing counting
# --------------------------------------------------------------------------


def test_score_diff_delta_and_crossing_counts() -> None:
    full6_records = {
        ("poiA", "b0"): _record("poiA", "b0", final_confluence_score=40),  # < 45 both sides -> no cross
        ("poiB", "b0"): _record("poiB", "b0", final_confluence_score=40),  # crosses 45 up (40 -> 46)
        ("poiC", "b0"): _record("poiC", "b0", final_confluence_score=70),  # crosses 65 down (70 -> 60)
        ("poiD", "b0"): _record("poiD", "b0", final_confluence_score=50),  # identical both sides
    }
    no_m5_records = {
        ("poiA", "b0"): _record("poiA", "b0", final_confluence_score=42),
        ("poiB", "b0"): _record("poiB", "b0", final_confluence_score=46),
        ("poiC", "b0"): _record("poiC", "b0", final_confluence_score=60),
        ("poiD", "b0"): _record("poiD", "b0", final_confluence_score=50),
    }

    universe, _field_mm, _comp_mm, _comp_max, score, _perm_mm, _perm_matrix = diff_records(
        full6_records, no_m5_records
    )

    assert universe.shared_record_count == 4
    assert score.compared_count == 4
    assert score.identical_count == 1  # poiD only
    assert score.different_count == 3
    # deltas: |40-42|=2, |40-46|=6, |70-60|=10, |50-50|=0 -> max=10, mean=4.5, median=4.0 (sorted [0,2,6,10])
    assert score.max_abs_delta == 10
    assert score.mean_abs_delta == 4.5
    assert score.median_abs_delta == 4.0
    assert score.cross_45_up == 1  # poiB: 40 -> 46
    assert score.cross_45_down == 0
    assert score.cross_65_up == 0
    assert score.cross_65_down == 1  # poiC: 70 -> 60


def test_score_diff_single_point_delta_is_not_dropped() -> None:
    """A ONE-point delta on a single record must show up as a difference --
    the exact 'do not round to equivalence' contract the brief requires."""
    full6_records = {("poi1", "b0"): _record("poi1", "b0", final_confluence_score=64)}
    no_m5_records = {("poi1", "b0"): _record("poi1", "b0", final_confluence_score=65)}

    _, _, _, _, score, _, _ = diff_records(full6_records, no_m5_records)

    assert score.different_count == 1
    assert score.identical_count == 0
    assert score.max_abs_delta == 1
    assert score.cross_65_up == 1


# --------------------------------------------------------------------------
# 3. permission-transition-matrix construction
# --------------------------------------------------------------------------


def test_permission_transition_matrix() -> None:
    full6_records = {
        ("p1", "b0"): _record("p1", "b0", permission="BUY_BIAS"),
        ("p2", "b0"): _record("p2", "b0", permission="BUY_BIAS"),
        ("p3", "b0"): _record("p3", "b0", permission="WATCH_ONLY"),
        ("p4", "b0"): _record("p4", "b0", permission="SELL_BIAS"),
    }
    no_m5_records = {
        ("p1", "b0"): _record("p1", "b0", permission="BUY_BIAS"),  # BUY -> BUY
        ("p2", "b0"): _record("p2", "b0", permission="WATCH_ONLY"),  # BUY -> WATCH
        ("p3", "b0"): _record("p3", "b0", permission="WATCH_ONLY"),  # WATCH -> WATCH
        ("p4", "b0"): _record("p4", "b0", permission="BUY_BIAS"),  # SELL -> BUY
    }

    _, _, _, _, _, perm_mismatch, matrix = diff_records(full6_records, no_m5_records)

    assert perm_mismatch == 2  # p2 and p4 changed
    assert matrix[("BUY_BIAS", "BUY_BIAS")] == 1
    assert matrix[("BUY_BIAS", "WATCH_ONLY")] == 1
    assert matrix[("WATCH_ONLY", "WATCH_ONLY")] == 1
    assert matrix[("SELL_BIAS", "BUY_BIAS")] == 1
    assert sum(matrix.values()) == 4


# --------------------------------------------------------------------------
# 4. event-differential logic
# --------------------------------------------------------------------------


def test_event_diff_exact_match() -> None:
    ev = EventRecordLite(event_type="POI_ACTIVATED", poi_record_id="p1", bar_availability_utc="b0", bar_index=0)
    diff = diff_events([ev], [ev], full6_poi_universe=frozenset({"p1"}), no_m5_poi_universe=frozenset({"p1"}))
    assert diff.exact_matches == 1
    assert diff.missing_from_no_m5 == 0
    assert diff.extra_in_no_m5 == 0
    assert diff.timing_mismatches == 0
    assert diff.event_type_mismatches == 0


def test_event_diff_timing_mismatch() -> None:
    full6_ev = EventRecordLite("BTMM_VALIDATED", "p1", "b0", 0)
    no_m5_ev = EventRecordLite("BTMM_VALIDATED", "p1", "b3", 3)  # same type+poi, different bar
    diff = diff_events(
        [full6_ev], [no_m5_ev], full6_poi_universe=frozenset({"p1"}), no_m5_poi_universe=frozenset({"p1"})
    )
    assert diff.exact_matches == 0
    assert diff.timing_mismatches == 1
    assert diff.event_type_mismatches == 0
    assert diff.missing_from_no_m5 == 0
    assert diff.extra_in_no_m5 == 0


def test_event_diff_event_type_mismatch() -> None:
    full6_ev = EventRecordLite("PERMISSION_ENTERED_ACTIONABLE", "p1", "b0", 0)
    no_m5_ev = EventRecordLite("PERMISSION_LOST_ACTIONABLE", "p1", "b0", 0)  # same poi+bar, different type
    diff = diff_events(
        [full6_ev], [no_m5_ev], full6_poi_universe=frozenset({"p1"}), no_m5_poi_universe=frozenset({"p1"})
    )
    assert diff.exact_matches == 0
    assert diff.timing_mismatches == 0
    assert diff.event_type_mismatches == 1
    assert diff.missing_from_no_m5 == 0
    assert diff.extra_in_no_m5 == 0


def test_event_diff_poi_identity_mismatch() -> None:
    # p_m5_only exists only in FULL6's own POI universe (an M5-origin POI);
    # the event has no plausible counterpart in NO_M5 at all.
    full6_ev = EventRecordLite("POI_ACTIVATED", "p_m5_only", "b0", 0)
    diff = diff_events(
        [full6_ev], [], full6_poi_universe=frozenset({"p_m5_only"}), no_m5_poi_universe=frozenset()
    )
    assert diff.missing_from_no_m5 == 1
    assert diff.poi_identity_mismatches_full6_only == 1
    assert diff.poi_identity_mismatches_no_m5_only == 0
    assert diff.timing_mismatches == 0
    assert diff.event_type_mismatches == 0


def test_event_diff_by_event_type_breakdown() -> None:
    full6_events = [
        EventRecordLite("POI_ACTIVATED", "p1", "b0", 0),
        EventRecordLite("BTMM_VALIDATED", "p1", "b1", 1),
    ]
    no_m5_events = [EventRecordLite("POI_ACTIVATED", "p1", "b0", 0)]
    diff = diff_events(
        full6_events, no_m5_events, full6_poi_universe=frozenset({"p1"}), no_m5_poi_universe=frozenset({"p1"})
    )
    assert diff.by_event_type["POI_ACTIVATED"] == {"full6_count": 1, "no_m5_count": 1, "exact_matches": 1}
    assert diff.by_event_type["BTMM_VALIDATED"] == {"full6_count": 1, "no_m5_count": 0, "exact_matches": 0}


# --------------------------------------------------------------------------
# 5. classification logic
# --------------------------------------------------------------------------


def _clean_report() -> MaterialityDiffReport:
    universe = UniverseDiff(
        full6_poi_count=2,
        no_m5_poi_count=2,
        shared_poi_count=2,
        only_full6_poi_count=0,
        only_no_m5_poi_count=0,
        full6_record_count=2,
        no_m5_record_count=2,
        shared_record_count=2,
        only_full6_record_count=0,
        only_no_m5_record_count=0,
    )
    score = ScoreDiff(
        compared_count=2,
        identical_count=2,
        different_count=0,
        max_abs_delta=0,
        mean_abs_delta=0.0,
        median_abs_delta=0.0,
        cross_45_up=0,
        cross_45_down=0,
        cross_65_up=0,
        cross_65_down=0,
    )
    events = diff_events([], [], full6_poi_universe=frozenset(), no_m5_poi_universe=frozenset())
    return MaterialityDiffReport(
        universe=universe,
        field_mismatch_counts={"poi_type": 0, "trend_alignment": 0},
        component_mismatch_counts={"btmm_score": 0},
        component_max_abs_delta={"btmm_score": 0},
        score=score,
        permission_mismatch_count=0,
        permission_transition_matrix={},
        events=events,
    )


def test_classify_clean_report_is_class_a() -> None:
    letter, reasoning = classify_materiality(_clean_report())
    assert letter == "A"
    assert "Class A" in reasoning


def test_classify_universe_divergence_is_class_b() -> None:
    report = _clean_report()
    dirty_universe = UniverseDiff(
        **{**report.universe.__dict__, "only_full6_poi_count": 3, "full6_poi_count": 5}
    )
    report = MaterialityDiffReport(**{**report.__dict__, "universe": dirty_universe})
    letter, reasoning = classify_materiality(report)
    assert letter == "B"
    assert "POI universe differs" in reasoning


def test_classify_single_one_point_score_delta_forces_class_b() -> None:
    """The brief's explicit, non-negotiable requirement: a single one-point
    score difference on ONE POI/bar disqualifies Class A -- no rounding, no
    partial credit."""
    report = _clean_report()
    dirty_score = ScoreDiff(
        compared_count=2,
        identical_count=1,
        different_count=1,
        max_abs_delta=1,
        mean_abs_delta=0.5,
        median_abs_delta=0.5,
        cross_45_up=0,
        cross_45_down=0,
        cross_65_up=0,
        cross_65_down=0,
    )
    report = MaterialityDiffReport(**{**report.__dict__, "score": dirty_score})
    letter, reasoning = classify_materiality(report)
    assert letter == "B"
    assert "final_confluence_score differs on 1 shared record" in reasoning


def test_classify_single_field_mismatch_forces_class_b() -> None:
    report = _clean_report()
    dirty_fields = dict(report.field_mismatch_counts)
    dirty_fields["trend_alignment"] = 1
    report = MaterialityDiffReport(**{**report.__dict__, "field_mismatch_counts": dirty_fields})
    letter, _reasoning = classify_materiality(report)
    assert letter == "B"


def test_classify_single_permission_mismatch_forces_class_b() -> None:
    report = _clean_report()
    report = MaterialityDiffReport(**{**report.__dict__, "permission_mismatch_count": 1})
    letter, _reasoning = classify_materiality(report)
    assert letter == "B"


def test_classify_single_event_timing_mismatch_forces_class_b() -> None:
    report = _clean_report()
    full6_ev = EventRecordLite("BTMM_VALIDATED", "p1", "b0", 0)
    no_m5_ev = EventRecordLite("BTMM_VALIDATED", "p1", "b1", 1)
    dirty_events = diff_events(
        [full6_ev], [no_m5_ev], full6_poi_universe=frozenset({"p1"}), no_m5_poi_universe=frozenset({"p1"})
    )
    report = MaterialityDiffReport(**{**report.__dict__, "events": dirty_events})
    letter, reasoning = classify_materiality(report)
    assert letter == "B"
    assert "P8 event stream differs" in reasoning
