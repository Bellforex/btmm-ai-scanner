"""Correlation-V1 (T0) — the BellForex web top-down correlation layer.

An ADDITIONAL supervisory layer over the validated scanner + BTRC, exactly
as BTRC itself sits over POI/BTMM without overriding their validity: this
package never re-detects a swing, POI, BOS, CHOCH, FVG or BTRC decision, and
never invalidates a POI/BTMM setup. It only classifies which supplied
timeframes matter for a requested ``TradingMode``, resolves a mode-aware
authority direction, applies a deterministic countertrend-protection policy,
and selects/ranks the highest-confluence eligible execution-timeframe
candidate — or reports ``NO_VALID_SETUP``/``INSUFFICIENT_DATA`` when none
qualifies, which is a normal, successful analysis outcome.

See ``docs/WEB_TOP_DOWN_CORRELATION.md`` for the full product/architecture
rationale. This package does not call the website, does not deploy
anything, and adds no network, LLM, or broker dependency.
"""

from btmm_ai_scanner.correlation.candidate import RankedCandidate
from btmm_ai_scanner.correlation.configuration import CorrelationConfiguration
from btmm_ai_scanner.correlation.contract import (
    AnnotationBox,
    AnnotationContract,
    TopDownWebContract,
    WebAuthorityContract,
    WebAuthorityTimeframeContract,
    WebCorrelationContract,
    WebPresentationContract,
    WebProvenanceContract,
    WebSetupCandidateContract,
    WebSetupContract,
    WebTechnicalContextContract,
    WebTradePlanContract,
    build_annotation_contract,
    build_web_contract,
)
from btmm_ai_scanner.correlation.engine import (
    InsufficientTopDownDataError,
    TopDownCorrelationDecision,
    evaluate_top_down_setup,
)
from btmm_ai_scanner.correlation.enums import (
    SetupVerdict,
    TopDownCorrelationState,
    TradingMode,
)
from btmm_ai_scanner.correlation.mode_trend import (
    ModeAuthorityAssessment,
    ModeTimeframeDirection,
    assess_mode_authority,
)
from btmm_ai_scanner.correlation.policy import (
    CandidatePolicyResult,
    evaluate_candidate_policy,
)
from btmm_ai_scanner.correlation.profiles import (
    DAY_TRADE_PROFILE,
    SCALP_PROFILE,
    SWING_PROFILE,
    InvalidTradingModeProfileError,
    TradingModeProfile,
    profile_for,
)

__all__ = [
    "DAY_TRADE_PROFILE",
    "SCALP_PROFILE",
    "SWING_PROFILE",
    "AnnotationBox",
    "AnnotationContract",
    "CandidatePolicyResult",
    "CorrelationConfiguration",
    "InsufficientTopDownDataError",
    "InvalidTradingModeProfileError",
    "ModeAuthorityAssessment",
    "ModeTimeframeDirection",
    "RankedCandidate",
    "SetupVerdict",
    "TopDownCorrelationDecision",
    "TopDownCorrelationState",
    "TopDownWebContract",
    "TradingMode",
    "TradingModeProfile",
    "WebAuthorityContract",
    "WebAuthorityTimeframeContract",
    "WebCorrelationContract",
    "WebPresentationContract",
    "WebProvenanceContract",
    "WebSetupCandidateContract",
    "WebSetupContract",
    "WebTechnicalContextContract",
    "WebTradePlanContract",
    "assess_mode_authority",
    "build_annotation_contract",
    "build_web_contract",
    "evaluate_candidate_policy",
    "evaluate_top_down_setup",
    "profile_for",
]
