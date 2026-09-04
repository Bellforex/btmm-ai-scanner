"""Blind Python replay of the P5 transport extension over a real capture.

Test/parity tooling only — nothing in `src/` imports this, and it changes no
production semantics. Nothing in the CLOSED P6 evidence chain
(`p6_projection_oracle.py`, `p6_digest.py`, `p6_real_data_replay.py`) is
modified by this module.

WHY THIS IS A SEPARATE MODULE RATHER THAN AN EXTENSION OF THE CLOSED ORACLE
------------------------------------------------------------------------------
`p6_projection_oracle.project_terminal` computes exactly the closed P6
surface — swing count, last swing, equal-level count, latest displacement,
last transition — and REDUCES away everything else before returning. The
26-field extension needs the full window's swings, ALL displacement
observations (not just the latest), the full transition list, and the current
structure state as objects, so a new function is needed rather than a
parameter added to the closed one.

That new function is written here to CALL the exact same production
components the closed oracle calls (`_DIAG._confirmed_swings`,
`detect_displacement_observations`, `analyze_structure_state`), over the exact
same window (`terminal + 1 - lookback .. terminal + 1`) with the exact same
`injected_atr` bridge — so it is not a second, divergent windowing
implementation. `test_windowing_matches_the_closed_oracle` in the accompanying
test module proves this directly: the closed oracle's reduced counts
(`swing_count`, `p2_transition_count`, `equal_level_count`) are recomputed
independently here and required to match, on the SAME real captured data this
module replays.

WHAT THIS PRODUCES
-------------------
For each timeframe, the 26-field `P5TransportRecord` from
`p5_transport_oracle.reduce_authoritative`, fed the REAL production domain
objects (`ConfirmedSwing`, `StructureTransition`, `DisplacementObservation`,
`CurrentStructureState`) rather than the lightweight test records —
`reduce_authoritative` accepts them directly by duck typing, proven identical
in `test_the_reduced_records_answer_exactly_as_the_real_contract_models`.

BLIND, LIKE THE CLOSED REPLAY
-------------------------------
Nothing here reads a Pine value of any kind. The comparison against the P5X
capture is a separate step the caller performs, on values this module never
saw.
"""

from __future__ import annotations

import hashlib
import importlib.util
import sys
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any
from uuid import UUID

_REPO = Path(__file__).resolve().parents[2]


def _load(name: str, relpath: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, _REPO / relpath)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


ORACLE = _load("_p6x_projection_oracle", "tests/parity_support/p6_projection_oracle.py")
_DIAG = ORACLE._DIAG
_TRUNC = ORACLE._TRUNC

from btmm_ai_scanner.contracts.normalized_candle import NormalizedCandle  # noqa: E402
from btmm_ai_scanner.contracts.provenance_record import (  # noqa: E402
    EvidenceClassification,
)
from btmm_ai_scanner.contracts.types import SemVer  # noqa: E402
from btmm_ai_scanner.domain.configuration import (  # noqa: E402
    MarketMeasurementConfiguration,
)
from btmm_ai_scanner.domain.displacement import (  # noqa: E402
    DisplacementObservation,
    detect_displacement_observations,
)
from btmm_ai_scanner.domain.equal_levels import (  # noqa: E402
    detect_equal_level_clusters,
)
from btmm_ai_scanner.historical_backtest.identity import (  # noqa: E402
    ContentAddressedIdentityProvider,
)
from btmm_ai_scanner.measurements.atr import compute_atr_series  # noqa: E402
from btmm_ai_scanner.structure.analyzer import analyze_structure_state  # noqa: E402
from btmm_ai_scanner.structure.configuration import StructureConfiguration  # noqa: E402

from .p5_transport_contract import P5TransportRecord  # noqa: E402
from .p5_transport_oracle import reduce_authoritative  # noqa: E402

LOOKBACK = ORACLE.LOOKBACK
MINTICK = ORACLE.MINTICK

_FP = "d" * 64
_PROV = UUID("0193f6c2-0000-7abc-8def-abcdefabcd70")
_V = SemVer.parse("0.1.0")
_EC = EvidenceClassification.ENGINEERING_PROVISIONAL


def _uuid7_like(key: str) -> UUID:
    """Deterministic id in the v7 shape the contracts require.

    Same construction as `p1_sr_diagnostics._uuid7_like`: derived from a
    semantic key, never random, so a replay is reproducible. Duplicated rather
    than imported because that module is test-only diagnostics tooling with no
    stable export surface, not because the two should ever intentionally
    diverge -- `test_windowing_matches_the_closed_oracle` is what would notice
    if they did.
    """
    digest = hashlib.sha256(key.encode("utf-8")).digest()[:16]
    value = int.from_bytes(digest, "big")
    value &= ~(0xF << 76)
    value |= 7 << 76  # version 7
    value &= ~(0x3 << 62)
    value |= 0x2 << 62  # RFC 4122 variant
    return UUID(int=value)


def _promote_displacements(
    candidates: Any, timeframe_label: str
) -> tuple[DisplacementObservation, ...]:
    """`detect_displacement_observations` returns candidates with no
    `record_id` (Pine has none either); `reduce_authoritative`'s ordering only
    needs one as a tie-break when two observations share both timestamps, so a
    deterministic id derived from the observation's own event time is
    sufficient and reproducible -- the same principle `_confirmed_swings`
    already applies to swings."""
    out: list[DisplacementObservation] = []
    for candidate in candidates:
        key = f"disp|{timeframe_label}|{candidate.event_time_utc.isoformat()}"
        out.append(
            DisplacementObservation(
                record_id=_uuid7_like(key),
                content_fingerprint=_FP,
                symbol=candidate.symbol,
                timeframe=candidate.timeframe,
                candle_record_id=candidate.candle_record_id,
                event_time_utc=candidate.event_time_utc,
                availability_time_utc=candidate.availability_time_utc,
                total_range=candidate.total_range,
                range_speed_ratio=candidate.range_speed_ratio,
                direction=candidate.direction,
                classification=candidate.classification,
                rule_version=_V,
                contract_version=_V,
                schema_version=_V,
                evidence_classification=_EC,
                provenance_id=_PROV,
            )
        )
    return tuple(out)


@dataclass(frozen=True)
class TransportWindow:
    """The full-object window this module computed, alongside the reduced
    counts needed to cross-check against the closed oracle's own output."""

    timeframe: str
    swing_count: int
    equal_level_count: int
    transition_count: int
    displacement_count: int
    record: P5TransportRecord


def replay_transport_terminal(
    candles: tuple[NormalizedCandle, ...],
    atr_all: Any,
    terminal: int,
    *,
    timeframe: str = "",
    lookback: int = LOOKBACK,
    measurement_configuration: MarketMeasurementConfiguration | None = None,
    structure_configuration: StructureConfiguration | None = None,
) -> TransportWindow:
    """The 26-field extension as of confirmed bar `terminal`.

    Mirrors `p6_projection_oracle.project_terminal`'s windowing exactly: same
    window slice, same `window_atr` bridge, same production calls. Returns the
    full objects instead of the closed oracle's reduced scalars.
    """
    mcfg = measurement_configuration or MarketMeasurementConfiguration(
        minimum_price_tick=MINTICK
    )
    scfg = structure_configuration or StructureConfiguration()

    window_first = max(0, terminal + 1 - lookback)
    window = candles[window_first : terminal + 1]
    watr = ORACLE._REPLAY.window_atr(atr_all, terminal, lookback)

    with _TRUNC.injected_atr(watr):
        swings = tuple(_DIAG._confirmed_swings(window, mcfg))
        equal_levels = detect_equal_level_clusters(swings, mcfg)
        displacement_candidates = detect_displacement_observations(window, mcfg)
        analysis = analyze_structure_state(
            window, swings, scfg, ContentAddressedIdentityProvider()
        )

    displacements = _promote_displacements(displacement_candidates, timeframe_label=timeframe)

    record = reduce_authoritative(
        swings, analysis.structure_transitions, displacements, analysis.current_state
    )

    return TransportWindow(
        timeframe=timeframe,
        swing_count=len(swings),
        equal_level_count=len(equal_levels),
        transition_count=len(analysis.structure_transitions),
        displacement_count=len(displacements),
        record=record,
    )


def replay_transport_series(
    candles: tuple[NormalizedCandle, ...],
    *,
    timeframe: str = "",
    terminals: int = 1,
    lookback: int = LOOKBACK,
    mintick: Decimal = MINTICK,
) -> tuple[TransportWindow, ...]:
    """Replay the last `terminals` confirmed bars of one timeframe's stream."""
    if not candles:
        raise ValueError("no candles to project")
    mcfg = MarketMeasurementConfiguration(minimum_price_tick=mintick)
    scfg = StructureConfiguration()
    atr_all = compute_atr_series(candles, mcfg.atr_period)
    first = max(0, len(candles) - terminals)
    return tuple(
        replay_transport_terminal(
            candles,
            atr_all,
            terminal,
            timeframe=timeframe,
            lookback=lookback,
            measurement_configuration=mcfg,
            structure_configuration=scfg,
        )
        for terminal in range(first, len(candles))
    )
