"""RC3 semantic-correction locks: the T3 evaluation timeframe and the
support/resistance source instant.

Both corrections were made against frozen authority, and both are the kind
of defect that is invisible on the one chart the earlier evidence happened
to be gathered on. These tests exist so neither can silently come back.
"""

from __future__ import annotations

import re
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
_USER_DEV = _REPO / "tradingview" / "btmm_poi_btrc_scanner_rc3_poi_semantics_dev.pine"
_PARITY_DEV = _REPO / "tradingview" / "btmm_poi_btrc_scanner_rc3_parity_dev.pine"
_BUILDS = (_USER_DEV, _PARITY_DEV)

#: The six timeframes production treats as the P5 authority set
#: (btrc/trend_engine.py) and therefore the only hosts for which a genuine
#: per-POI-timeframe T3 assessment exists.
_AUTHORITY_TF_CONSTANTS = (
    "C_P6_TF_W1",
    "C_P6_TF_D1",
    "C_P6_TF_H4",
    "C_P6_TF_H1",
    "C_P6_TF_M15",
    "C_P6_TF_M5",
)


# --------------------------------------------------------------------------
# T3 evaluation timeframe
# --------------------------------------------------------------------------


def test_t3_is_never_hardcoded_to_the_m15_context() -> None:
    """The defect: `f_p5T3Mom(m15Ext)` evaluated every host against M15.

    Exact on an M15 chart, wrong on M5/H1/H4 — which is precisely why no
    earlier parity evidence caught it: all of it was gathered on M15.
    """
    for build in _BUILDS:
        source = build.read_text(encoding="utf-8")
        assert "f_p5T3Mom(m15Ext)" not in source, build.name
        assert "f_p5T3Brk(m15Ext)" not in source, build.name
        assert "f_p5T3Pb(m15P2d, m15Ext)" not in source, build.name


def test_t3_dispatches_across_every_authority_timeframe() -> None:
    for build in _BUILDS:
        source = build.read_text(encoding="utf-8")
        dispatch = source[source.index("P5TransportExt p5T3Ext") :]
        dispatch = dispatch[: dispatch.index("f_p5T3Mom(p5T3Ext)")]
        for constant in _AUTHORITY_TF_CONSTANTS:
            assert f"timeframe.period == {constant}" in dispatch, (
                f"{build.name}: T3 dispatch does not handle {constant}"
            )


def test_t3_uses_the_selected_context_not_a_fixed_one() -> None:
    for build in _BUILDS:
        source = build.read_text(encoding="utf-8")
        assert "f_p5T3Mom(p5T3Ext)" in source, build.name
        assert "f_p5T3Brk(p5T3Ext)" in source, build.name
        assert "f_p5T3Pb(p5T3P2d, p5T3Ext)" in source, build.name


def test_out_of_authority_hosts_get_productions_missing_component_scores() -> None:
    """`t5_engine.py` scores a missing momentum component 50 and a missing
    breakout component 40. A host outside the authority set must reproduce
    those exactly rather than borrowing a foreign timeframe's numbers."""
    for build in _BUILDS:
        source = build.read_text(encoding="utf-8")
        assert "p5T3TfPresent ? f_p5MomentumScoreConfluence" in source, build.name
        assert re.search(r"poiBullish\)\s*:\s*50", source), build.name
        assert re.search(r"p5T3TfPresent\s*\?\s*p5BrkScore\s*:\s*40", source), build.name


def test_python_selects_t3_assessments_by_the_pois_own_timeframe() -> None:
    """Guard the other direction too: the Python authority keys T3 on the
    POI's own detection timeframe (`poi.source_timeframe`, RC3 author decision
    2026-09-17), which is what the host-only Pine dispatch above matches.
    Higher-timeframe overlap stays explicit derived context."""
    engine = (_REPO / "src" / "btmm_ai_scanner" / "btrc" / "t5_engine.py").read_text(
        encoding="utf-8"
    )
    assert "poi_tf = poi.source_timeframe" in engine
    assert "higher_tf_context=higher_tf_context" in engine
    # Computed once per bar in ConfluenceBarContext, selected per POI timeframe.
    for component, table in (
        ("assess_momentum", "momentum_by_timeframe"),
        ("assess_breakout", "breakout_by_timeframe"),
        ("assess_pullback", "pullback_by_timeframe"),
    ):
        assert f"{component}(self.analysis)" in engine
        assert f"bar_context.{table}.get(poi_tf)" in engine


# --------------------------------------------------------------------------
# Support / resistance source instant
# --------------------------------------------------------------------------


def test_support_resistance_carries_its_origin_swing_pivot_end() -> None:
    for build in _BUILDS:
        source = build.read_text(encoding="utf-8")
        assert "int   originPivotEndTime" in source, build.name
        assert "SRRec.new(cached.originType" in source and "cached.originKey)" in source, (
            build.name
        )
        assert "origin.key)" in source, build.name


def test_reference_zone_emit_uses_source_not_confirmation_for_the_candidate() -> None:
    """The defect: all five time arguments were `z.confirmationTime`, which
    collapsed source into availability and drew the zone's left edge at the
    moment it confirmed rather than the moment the level came into being."""
    for build in _BUILDS:
        source = build.read_text(encoding="utf-8")
        assert (
            "C_POI_TIER_NA, z.confirmationTime, 1, z.confirmationTime, "
            "z.confirmationTime, z.confirmationTime)" not in source
        ), build.name
        assert (
            "C_POI_TIER_NA, z.confirmationTime, 1, z.confirmationTime, "
            "z.originPivotEndTime, z.confirmationTime)" in source
        ), build.name


def test_the_identity_triple_still_uses_confirmation_time() -> None:
    """POI identity must NOT move with this change. The documented collision
    fix on `ModelPoi.identity` depends on the (first, count, last) triple
    staying exactly what it was."""
    for build in _BUILDS:
        source = build.read_text(encoding="utf-8")
        assert (
            "z.confirmationTime, 1, z.confirmationTime, z.originPivotEndTime" in source
        ), build.name


def test_both_rc3_builds_agree_on_every_corrected_line() -> None:
    """The USER build and the PARITY build must never drift on semantics —
    the whole point of the parity build is that it is the same engine."""
    user = _USER_DEV.read_text(encoding="utf-8").splitlines()
    parity = _PARITY_DEV.read_text(encoding="utf-8").splitlines()
    markers = ("p5T3Ext", "p5T3P2d", "p5T3TfPresent", "originPivotEndTime", "SRRec.new(")
    user_lines = [ln.strip() for ln in user if any(m in ln for m in markers)]
    parity_lines = [ln.strip() for ln in parity if any(m in ln for m in markers)]
    assert user_lines == parity_lines
    assert len(user_lines) > 0
