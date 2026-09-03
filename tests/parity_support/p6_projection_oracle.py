"""Authoritative Python side of the P6 requested-context projection.

Test/parity tooling only — nothing in `src/` imports this, and it changes no
production semantics.

WHAT THIS IS FOR
----------------
The P6 Pine section reduces each requested timeframe to exactly five transported
surfaces (`BTRC_V1_P6_MTF_ARCHITECTURE.md` §3a):

    P1: confirmed_swings, equal_level_clusters, displacement_observations
    P2: structure_transitions, current_state

This module produces those same five surfaces from PRODUCTION Python, in the
Pine's own integer vocabulary, so the two can be compared field for field.

WHY IT REUSES THE P2 REPLAY'S EXECUTION MODEL RATHER THAN INVENTING ONE
-----------------------------------------------------------------------
`p2_atomic_state_replay` already established, and P2 closure already proved, the
correspondence between Pine's incremental bounded execution and the batch
production engine:

* ATR is ONE continuous Wilder recurrence over the whole context — the batch
  form of the recurrence Pine advances incrementally — never a per-window
  restart;
* at each terminal bar the analytical view is the last `lookback` (300) candles,
  exactly Pine's pruned `w*`/`q*` arrays;
* window swing detection is the PRODUCTION detector, handed the continuous ATR
  slice through the validated `injected_atr` bridge, whose transparency has its
  own standing proof;
* the P2 walk is recomputed from the window every confirmed bar, carrying no
  state across terminals, exactly as Pine does.

Reproducing that model here rather than importing it would be a second,
divergent copy of the very thing P2 closure pinned — the same mistake the P6
Pine section deliberately avoids by calling the closed Pine functions instead of
re-implementing them. So the helpers are imported.

NOTHING here reimplements ATR, pivot, swing, equal-level, displacement,
relationship, bootstrap, BOS or CHOCH math. It selects windows, invokes
production components, and projects their outputs into the Pine field
vocabulary.

WHAT IT DELIBERATELY DOES NOT DO
--------------------------------
It contains no expected Pine values. Comparison against captured Pine output is
always a separate step performed by the caller, so a mismatch cannot be
massaged away inside the oracle.
"""

from __future__ import annotations

import importlib.util
import sys
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any

_REPO = Path(__file__).resolve().parents[2]


def _load(name: str, relpath: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, _REPO / relpath)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


_REPLAY = _load("_p6_replay", "tests/parity_support/p2_atomic_state_replay.py")
_DIAG = _load("_p6_diagnostics", "tests/performance_support/p1_sr_diagnostics.py")
_TRUNC = _load("_p6_truncation", "tests/performance_support/p1_truncation.py")

from btmm_ai_scanner.contracts.normalized_candle import NormalizedCandle  # noqa: E402
from btmm_ai_scanner.domain.configuration import (  # noqa: E402
    MarketMeasurementConfiguration,
)
from btmm_ai_scanner.domain.displacement import (  # noqa: E402
    detect_displacement_observations,
)
from btmm_ai_scanner.domain.enums import (  # noqa: E402
    DisplacementClassification,
    DisplacementDirection,
    SwingType,
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

#: Pine sentinels and window bound, mirrored from the Pine source.
C_ST_NA = _REPLAY.C_ST_NA
LOOKBACK = _REPLAY.LOOKBACK
MINTICK = _REPLAY.MINTICK

#: Pine `SWING_HIGH = 1`, `SWING_LOW = -1`.
SWING_CODE = {SwingType.SWING_HIGH: 1, SwingType.SWING_LOW: -1}

#: Pine `cls` in f_latestDisplacement: 0 normal, 1 fast, 2 very fast.
DISP_LEVEL = {
    DisplacementClassification.NORMAL: 0,
    DisplacementClassification.FAST: 1,
    DisplacementClassification.VERY_FAST: 2,
}

DIR_CODE = _REPLAY.DIR_CODE
TR_CODE = _REPLAY.TR_CODE


@dataclass(frozen=True)
class P6Projection:
    """Exactly what one requested context transports, in Pine's vocabulary."""

    confirmed_bar_count: int

    # P1 -- confirmed_swings
    swing_count: int
    last_swing_type: int
    last_swing_price: Decimal | None
    last_conf_time: int | None

    # P1 -- equal_level_clusters
    equal_level_count: int

    # P1 -- displacement_observations (latest confirmed candle)
    disp_code: int
    disp_ratio: Decimal | None

    # P2 -- current_state and structure_transitions
    p2_direction: int
    p2_transition_count: int
    p2_last_transition_code: int
    p2_last_broken_level: Decimal | None

    def compare_values(self) -> dict[str, object]:
        """The canonical compare set: exactly the fields Pine transports.

        Restricted to what P5 consumes plus the two counts needed to prove the
        projection itself, per the Phase-2 rule.
        """
        return {
            "swing_count": self.swing_count,
            "last_swing_type": self.last_swing_type,
            "last_swing_price": self.last_swing_price,
            "last_conf_time": self.last_conf_time,
            "equal_level_count": self.equal_level_count,
            "disp_code": self.disp_code,
            "disp_ratio": self.disp_ratio,
            "p2_direction": self.p2_direction,
            "p2_transition_count": self.p2_transition_count,
            "p2_last_transition_code": self.p2_last_transition_code,
            "p2_last_broken_level": self.p2_last_broken_level,
        }


def _latest_displacement(
    window: tuple[NormalizedCandle, ...],
    configuration: MarketMeasurementConfiguration,
) -> tuple[int, Decimal | None]:
    """Pine's `f_latestDisplacement`, taken from the production detector.

    Pine classifies only the LAST candle of the window and encodes it as
    `isBull ? cls : -cls`. Production emits an observation per candle carrying
    the same classification, so the projection is a lookup of the observation
    whose candle is the window's last, not a recomputation of the rule.
    """
    if not window:
        return 0, None
    observations = detect_displacement_observations(window, configuration)
    last_time = window[-1].event_time_utc
    latest = next(
        (o for o in reversed(observations) if o.event_time_utc == last_time), None
    )
    if latest is None:
        # Pine leaves `code` na when the context window is shorter than the
        # range-context baseline; the sentinel keeps that distinguishable.
        return C_ST_NA, None
    level = DISP_LEVEL[latest.classification]
    signed = level if latest.direction is DisplacementDirection.BULLISH else -level
    return signed, latest.range_speed_ratio


def project_terminal(
    candles: tuple[NormalizedCandle, ...],
    atr_all: Any,
    terminal: int,
    *,
    lookback: int = LOOKBACK,
    measurement_configuration: MarketMeasurementConfiguration | None = None,
    structure_configuration: StructureConfiguration | None = None,
) -> P6Projection:
    """The five transported surfaces as of confirmed bar `terminal`."""
    mcfg = measurement_configuration or MarketMeasurementConfiguration(
        minimum_price_tick=MINTICK
    )
    scfg = structure_configuration or StructureConfiguration()

    window_first = max(0, terminal + 1 - lookback)
    window = candles[window_first : terminal + 1]
    watr = _REPLAY.window_atr(atr_all, terminal, lookback)

    # Production detector over the bounded window, with the continuous ATR the
    # host advances incrementally -- the validated bridge, not a re-derivation.
    with _TRUNC.injected_atr(watr):
        swings = _DIAG._confirmed_swings(window, mcfg)
        equal_levels = detect_equal_level_clusters(tuple(swings), mcfg)

    if swings:
        last = swings[-1]
        last_swing_type = SWING_CODE[last.swing_type]
        last_swing_price: Decimal | None = last.pivot_price
        last_conf_time: int | None = _REPLAY._ms(last.meaningful_confirmation_time_utc)
    else:
        last_swing_type = C_ST_NA
        last_swing_price = None
        last_conf_time = None

    disp_code, disp_ratio = _latest_displacement(tuple(window), mcfg)

    analysis = analyze_structure_state(
        tuple(window), tuple(swings), scfg, ContentAddressedIdentityProvider()
    )
    transitions = analysis.structure_transitions
    if transitions:
        last_transition_code = TR_CODE[transitions[-1].transition_type]
        last_broken_level: Decimal | None = transitions[-1].broken_level_price
    else:
        last_transition_code = C_ST_NA
        last_broken_level = None

    return P6Projection(
        confirmed_bar_count=terminal + 1,
        swing_count=len(swings),
        last_swing_type=last_swing_type,
        last_swing_price=last_swing_price,
        last_conf_time=last_conf_time,
        equal_level_count=len(equal_levels),
        disp_code=disp_code,
        disp_ratio=disp_ratio,
        p2_direction=DIR_CODE[analysis.current_state.direction],
        p2_transition_count=len(transitions),
        p2_last_transition_code=last_transition_code,
        p2_last_broken_level=last_broken_level,
    )


def project_series(
    candles: tuple[NormalizedCandle, ...],
    *,
    terminals: int = 1,
    lookback: int = LOOKBACK,
    mintick: Decimal = MINTICK,
) -> tuple[P6Projection, ...]:
    """Project the last `terminals` confirmed bars of one timeframe's stream."""
    if not candles:
        raise ValueError("no candles to project")
    mcfg = MarketMeasurementConfiguration(minimum_price_tick=mintick)
    scfg = StructureConfiguration()
    atr_all = compute_atr_series(candles, mcfg.atr_period)
    first = max(0, len(candles) - terminals)
    return tuple(
        project_terminal(
            candles,
            atr_all,
            terminal,
            lookback=lookback,
            measurement_configuration=mcfg,
            structure_configuration=scfg,
        )
        for terminal in range(first, len(candles))
    )
