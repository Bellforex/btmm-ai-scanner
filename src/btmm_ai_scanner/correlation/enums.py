"""Correlation-V1 (T0) — new domain enums for the BellForex web top-down
correlation layer.

This module defines NEW concepts that sit ABOVE the existing, frozen BTRC
enums (``btmm_ai_scanner.btrc.enums``) — it does not redefine, rename, or
alias ``TrendAlignment``, ``AnalyticalPermission``, ``Direction``, or any
other BTRC dimension. Those keep their existing meaning unchanged; this
package only adds a mode-aware supervisory layer on top of them, exactly as
BTRC itself sits on top of POI/BTMM without overriding their validity.

Like the BTRC-V1 T0 freeze, these enums carry their NAMES and MEANING only —
the deterministic policy that produces them lives in
``btmm_ai_scanner.correlation.policy``.
"""

from enum import StrEnum


class TradingMode(StrEnum):
    """A BellForex top-down analysis style — determines which timeframes are
    in play and which are authority/context vs execution vs presentation.
    This is a domain concept only; no UI copy belongs here (see
    ``btmm_ai_scanner.correlation.profiles`` for the human-facing profile
    data, and any web-layer localization for display strings)."""

    SCALP = "SCALP"
    DAY_TRADE = "DAY_TRADE"
    SWING = "SWING"


class TopDownCorrelationState(StrEnum):
    """How the supplied timeframes for a mode agree with each other —
    distinct from ``TrendAlignment`` (which is a per-POI, per-BTRC-decision
    concept). This is a whole-mode-context observation, computed from the
    mode's own per-timeframe direction assessments.

    ALIGNED               — every context/authority timeframe agrees on side.
    PARTIALLY_ALIGNED     — the anchor timeframe has a clear side and the
                             majority of context timeframes agree, but at
                             least one context timeframe disagrees or is
                             neutral.
    MIXED                 — no clear majority; context timeframes are split
                             roughly evenly between sides, or the anchor
                             itself is ambiguous relative to the rest.
    COUNTER_TREND         — a context/authority timeframe clearly opposes the
                             anchor's own direction (material conflict, not
                             just a lower-timeframe pullback).
    INSUFFICIENT_CONTEXT  — too few authority/context timeframes were
                             supplied (or resolved to a direction) to say
                             anything meaningful.
    """

    ALIGNED = "ALIGNED"
    PARTIALLY_ALIGNED = "PARTIALLY_ALIGNED"
    MIXED = "MIXED"
    COUNTER_TREND = "COUNTER_TREND"
    INSUFFICIENT_CONTEXT = "INSUFFICIENT_CONTEXT"


class SetupVerdict(StrEnum):
    """The NEW verdict this layer adds above ``AnalyticalPermission``.
    ``AnalyticalPermission`` (BTRC-T5) keeps its own existing meaning
    unchanged and is not renamed or replaced — ``SetupVerdict`` is a
    strictly-additive, mode-aware wrapper around it plus this layer's own
    top-down/countertrend policy.

    VALID_SETUP            — the candidate survives mode-authority alignment,
                              analytical-permission suitability, lifecycle
                              readiness and the countertrend policy. The
                              single highest-confluence eligible candidate.
    WATCH_FOR_ALIGNMENT     — a candidate exists and is not disqualified, but
                              either authority context is ambiguous/mixed, or
                              confluence/lifecycle is not yet strong enough
                              to call it the primary setup.
    NO_VALID_SETUP          — no candidate is eligible to be presented as the
                              primary setup right now (e.g. a countertrend
                              candidate against a clear authority, no fresh
                              execution-timeframe POI, or all candidates
                              rejected). This is a SUCCESSFUL analysis
                              outcome, not an engine error.
    INSUFFICIENT_DATA       — the supplied timeframes/candles do not meet the
                              mode profile's minimum requirements to reason
                              about a setup at all.
    """

    VALID_SETUP = "VALID_SETUP"
    WATCH_FOR_ALIGNMENT = "WATCH_FOR_ALIGNMENT"
    NO_VALID_SETUP = "NO_VALID_SETUP"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"
