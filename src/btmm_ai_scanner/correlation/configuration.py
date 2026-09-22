"""Correlation-V1 (T0) configuration — thresholds for the setup-verdict
policy and candidate ranking. Kept as data (this class), never scattered
if-statement literals, following the same *Configuration convention as
``btrc.t5_configuration.ConfluenceConfiguration`` and the rest of the
scanner core.
"""

from __future__ import annotations

from btmm_ai_scanner.contracts.types import ContractModel, SemVer


class CorrelationConfiguration(ContractModel):
    # A candidate whose BTRC final_confluence_score is at or above this,
    # AND whose mode/authority alignment and lifecycle pass the policy, may
    # become VALID_SETUP.
    minimum_confluence_for_valid_setup: int = 60
    # Below this, even an aligned, eligible candidate is only
    # WATCH_FOR_ALIGNMENT rather than VALID_SETUP.
    minimum_confluence_for_watch: int = 40
    # How many of a mode profile's authority timeframes must have resolved
    # (non-missing) before the engine will attempt a verdict at all, on top
    # of the profile's own minimum_timeframe_count. 1 means "at least one
    # authority/context timeframe, whatever the mode."
    minimum_resolved_authority_timeframes: int = 1

    rule_version: SemVer = SemVer.parse("0.1.0")
    contract_version: SemVer = SemVer.parse("0.1.0")
    schema_version: SemVer = SemVer.parse("0.1.0")
