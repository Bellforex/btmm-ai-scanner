"""RC3 author decision (2026-09-17): P5 POI-specific scoring uses source_timeframe.

A cross-timeframe overlap that raised a POI's ``effective_timeframe`` is kept as
explicit derived context (``BtrcDecision.higher_tf_context``). It must never
re-time the POI: T3 momentum / breakout / pullback and T4 volatility are read on
the detection timeframe, and no score or permission changes because of it.
"""

from __future__ import annotations

from btmm_ai_scanner.btrc import assess_confluence, latest_poi
from btmm_ai_scanner.btrc.t3_engine import assess_momentum
from btmm_ai_scanner.config.enums import Timeframe
from btmm_ai_scanner.historical_backtest.identity import (
    ContentAddressedIdentityProvider,
)
from btmm_ai_scanner.scanner.analyzer import scan_market
from btmm_ai_scanner.scanner.timeframe_input import ScannerTimeframeInput
from tests.unit.test_t5_component_scores_sufficiency import _config, _m15


def _analysis_and_poi():
    for seed in range(40):
        analysis = scan_market(
            (ScannerTimeframeInput(Timeframe.M15, _m15(180, seed)),),
            (),
            _config(),
            ContentAddressedIdentityProvider(),
        )
        poi = latest_poi(analysis)
        momentum = {m.timeframe for m in assess_momentum(analysis)}
        if poi is not None and Timeframe.M15 in momentum:
            return analysis, poi
    raise AssertionError("no seed produced a POI with M15 momentum")


def test_raised_effective_timeframe_is_context_not_the_scoring_timeframe() -> None:
    analysis, poi = _analysis_and_poi()
    assert poi.source_timeframe == poi.effective_timeframe == Timeframe.M15
    raised = poi.model_copy(update={"effective_timeframe": Timeframe.H4})

    native = assess_confluence(analysis, poi)
    merged = assess_confluence(analysis, raised)

    assert merged.poi_timeframe == Timeframe.M15
    assert merged.higher_tf_context == Timeframe.H4
    assert native.higher_tf_context is None
    # Identical POI-specific inputs, scores and permission: the H4 overlap is
    # context only (under the old effective-timeframe keying the M15 POI read
    # the absent H4 T3 assessments and scored differently).
    assert merged.momentum_direction == native.momentum_direction is not None
    assert merged.breakout_state == native.breakout_state
    assert merged.pullback_state == native.pullback_state
    assert merged.component_scores == native.component_scores
    assert merged.final_confluence_score == native.final_confluence_score
    assert merged.analytical_permission == native.analytical_permission
    assert merged.missing_components == native.missing_components
