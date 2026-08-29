"""P2-PARITY-STATE-2 — offline Pine-execution replay over the atomic context.

Test/parity tooling only — nothing in `src/` imports this, and it changes no
production semantics. It replays the frozen 1800-bar atomic execution context
through the AUTHORITATIVE Python engine, modeling Pine's execution chronology,
and captures the 15 canonical P2 Structure state fields for the final
`state_count` closed bars.

THIS MODULE IS DELIBERATELY BLIND: it contains no expected Pine hash values.
Comparison against the Pine targets is a separate step performed by the
caller, after the replay output exists (P2-PARITY-STATE-2 Phase 17).

EXECUTION MODEL (mirrors the audited Pine main block)
-----------------------------------------------------
* Context row r IS Pine confirmed-bar (confirmedBarCount = r + 1) — the atomic
  bundle proved cbc == ctxn == 1800 and absfirst == 1500.
* P1 ATR is ONE continuous Wilder recurrence over the whole context
  (production `compute_atr_series` over all 1800 candles — the batch form of
  the same recurrence Pine advances incrementally), NOT a per-window restart.
* At each terminal bar T the analytical view is the bounded window of the
  last `lookback` (300) candles, exactly like Pine's pruned `w*` arrays.
* Window swing detection is PRODUCTION `detect_confirmed_swings`, handed the
  continuous ATR slice through the validated `injected_atr` bridge from
  `tests/performance_support/p1_truncation.py` (production detector bodies run
  verbatim; `assert_injection_is_transparent` is its standing proof).
* Swing records use the established Pine identity (pivot-end anchor) via
  `tests/performance_support/p1_sr_diagnostics._confirmed_swings` — the single
  canonical builder already used by the P1 truncation campaign.
* Relationships come from PRODUCTION
  `structure.relationships.detect_swing_relationships` and structure state
  from PRODUCTION `structure.analyzer.analyze_structure_state` — the reference
  side of every P2 parity test. Each terminal is evaluated independently on
  its bounded view; no P2 walk state is carried across terminals (Pine
  recomputes the walk from the window every confirmed bar).

NOTHING here reimplements ATR, pivot, swing, relationship, bootstrap, BOS,
weak re-arm, CHOCH or digest math. This module only loads rows, selects
windows, invokes production components, projects their outputs into the
frozen Pine diagnostic field vocabulary, and folds hashes with the frozen
`p2_digest` reference.

Field projection (Pine diagnostic <- production output), pinned by the
existing parity suites:

  adapted_swing_count      len(window swings)                    absent: n/a
  last_pivot_start_abs     absFirst + window index of the last swing's
                           pivot_start_time_utc candle           absent: na
  last_conf_time           last swing meaningful_confirmation ms absent: na
  relationship_count       len(relationships)
  last_high_relationship   last code in {1,-1,10}                absent: na
  last_low_relationship    last code in {2,-2,20}                absent: na
  direction                UNDETERMINED->0 BULLISH->1 BEARISH->-1
  protected_high/low,      swing pivot_end ms of the active id,
  weak_high/low            C_ST_NA (-99) when unset
  transition_count         len(structure_transitions)
  last_transition_code     BOS +/-1, CHOCH +/-2                  absent: C_ST_NA
  last_broken_key          broken swing pivot_end ms             absent: C_ST_NA
  last_broken_level        broken_level_price (Decimal)          absent: na
"""

from __future__ import annotations

import csv
import importlib.util
import sys
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]


def _load(name: str, relpath: str):
    spec = importlib.util.spec_from_file_location(name, _REPO / relpath)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


_DIAG = _load("_p2rep_diagnostics", "tests/performance_support/p1_sr_diagnostics.py")
_TRUNC = _load("_p2rep_truncation", "tests/performance_support/p1_truncation.py")
_DIGEST = _load("_p2rep_digest", "tests/parity_support/p2_digest.py")

from btmm_ai_scanner.config.enums import InternalSymbol, Timeframe  # noqa: E402
from btmm_ai_scanner.contracts.normalized_candle import NormalizedCandle  # noqa: E402
from btmm_ai_scanner.contracts.raw_candle import (  # noqa: E402
    CandleCompleteness,
    CandleVolumeKind,
)
from btmm_ai_scanner.contracts.types import SemVer  # noqa: E402
from btmm_ai_scanner.domain.configuration import (  # noqa: E402
    MarketMeasurementConfiguration,
)
from btmm_ai_scanner.historical_backtest.identity import (  # noqa: E402
    ContentAddressedIdentityProvider,
)
from btmm_ai_scanner.measurements.atr import compute_atr_series  # noqa: E402
from btmm_ai_scanner.structure.analyzer import analyze_structure_state  # noqa: E402
from btmm_ai_scanner.structure.configuration import StructureConfiguration  # noqa: E402
from btmm_ai_scanner.structure.enums import (  # noqa: E402
    StructureDirection,
    StructureTransitionType,
    SwingRelationshipLabel,
)
from btmm_ai_scanner.structure.relationships import (  # noqa: E402
    detect_swing_relationships,
)

_EPOCH = datetime(1970, 1, 1, tzinfo=UTC)
_ONE_MS = timedelta(milliseconds=1)

C_ST_NA = -99
LOOKBACK = 300
MINTICK = Decimal("0.01")

#: Pine int codes, mirrored from test_p2_relationship_parity.C_ST_REL.
REL_CODE = {
    SwingRelationshipLabel.HIGHER_HIGH: 1,
    SwingRelationshipLabel.LOWER_HIGH: -1,
    SwingRelationshipLabel.EQUAL_HIGH: 10,
    SwingRelationshipLabel.HIGHER_LOW: 2,
    SwingRelationshipLabel.LOWER_LOW: -2,
    SwingRelationshipLabel.EQUAL_LOW: 20,
}
_HIGH_REL_CODES = frozenset({1, -1, 10})

#: Pine direction ints, mirrored from test_p2_bos_parity._DIR_FROM_PYTHON.
DIR_CODE = {
    StructureDirection.UNDETERMINED: 0,
    StructureDirection.BULLISH: 1,
    StructureDirection.BEARISH: -1,
}

#: Pine transition ints, mirrored from test_p2_bos_parity._TR_FROM_PYTHON.
TR_CODE = {
    StructureTransitionType.BULLISH_BOS: 1,
    StructureTransitionType.BEARISH_BOS: -1,
    StructureTransitionType.BULLISH_CHOCH: 2,
    StructureTransitionType.BEARISH_CHOCH: -2,
}


class ReplayInputError(ValueError):
    """The context CSV is unusable. Reject, never repair."""


def _ms(moment: datetime) -> int:
    """datetime -> exact epoch milliseconds (integer arithmetic, no floats)."""
    return (moment - _EPOCH) // _ONE_MS


def _from_ms(ms: int) -> datetime:
    return _EPOCH + ms * _ONE_MS


def load_context_candles(csv_path: Path) -> tuple[NormalizedCandle, ...]:
    """Context CSV rows -> production NormalizedCandle objects.

    Times come straight from the CSV's exact millisecond columns (event =
    ``time``, availability/processing = ``time_close``); prices stay Decimal
    end to end. Candle identity follows the established deterministic scheme
    from `p1_sr_diagnostics` so record ids are stable across runs.
    """
    with csv_path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != ["time", "open", "high", "low", "close", "time_close"]:
            raise ReplayInputError(
                f"unexpected context CSV columns: {reader.fieldnames}"
            )
        rows = list(reader)
    if not rows:
        raise ReplayInputError("context CSV has no rows")

    candles: list[NormalizedCandle] = []
    previous_time = None
    for index, row in enumerate(rows):
        event_ms = int(row["time"])
        close_ms = int(row["time_close"])
        if previous_time is not None and event_ms <= previous_time:
            raise ReplayInputError(
                f"context row {index} time {event_ms} is not strictly increasing"
            )
        previous_time = event_ms
        event_time = _from_ms(event_ms)
        availability = _from_ms(close_ms)
        candles.append(
            NormalizedCandle.model_validate(
                {
                    "record_id": _DIAG._uuid7_like(
                        f"candle|{index}|{event_time.isoformat()}"
                    ),
                    "content_fingerprint": _DIAG._FINGERPRINT,
                    "raw_candle_id": _DIAG._RAW_CANDLE_ID,
                    "provider": "FXCM",
                    "source_reference": "fxcm-xauusd-atomic-context",
                    "source_symbol": InternalSymbol.XAUUSD.value,
                    "source_timeframe": Timeframe.M15.value,
                    "symbol": InternalSymbol.XAUUSD,
                    "timeframe": Timeframe.M15,
                    "event_time_utc": event_time,
                    "availability_time_utc": availability,
                    "processing_time_utc": availability,
                    "original_event_time": event_time,
                    "original_availability_time": availability,
                    "original_timezone": "UTC",
                    "open": Decimal(row["open"]),
                    "high": Decimal(row["high"]),
                    "low": Decimal(row["low"]),
                    "close": Decimal(row["close"]),
                    "volume": Decimal("1"),
                    "volume_kind": CandleVolumeKind.TICK,
                    "completeness": CandleCompleteness.CONFIRMED_COMPLETE,
                    "rule_version": SemVer.parse("0.1.0"),
                    "contract_version": SemVer.parse("0.1.0"),
                    "schema_version": SemVer.parse("0.1.0"),
                    "provenance_id": _DIAG._PROVENANCE_ID,
                }
            )
        )
    return tuple(candles)


def window_atr(atr_all, terminal: int, lookback: int = LOOKBACK):
    """The bounded window's ATR values from the CONTINUOUS series.

    This is the load-bearing difference from a naive per-window replay: the
    slice comes from the full-history recurrence (Pine's `wAtr`), never from a
    recomputation over the window alone.
    """
    first = max(0, terminal + 1 - lookback)
    return tuple(atr_all[first : terminal + 1])


@dataclass(frozen=True)
class TerminalState:
    evaluation_index: int
    time_ms: int
    confirmed_bar_count: int
    abs_first: int
    adapted_swing_count: int
    last_pivot_start_abs: int | None
    last_conf_time: int | None
    relationship_count: int
    last_high_relationship: int | None
    last_low_relationship: int | None
    direction: int
    protected_high: int
    protected_low: int
    weak_high: int
    weak_low: int
    transition_count: int
    last_transition_code: int
    last_broken_key: int
    last_broken_level: Decimal | None

    def digest_values(self) -> dict[str, object]:
        """The 15 fields keyed exactly as the frozen STATE_FIELD_ORDER."""
        return {
            "adapted_swing_count": self.adapted_swing_count,
            "last_pivot_start_abs": self.last_pivot_start_abs,
            "last_conf_time": self.last_conf_time,
            "relationship_count": self.relationship_count,
            "last_high_relationship": self.last_high_relationship,
            "last_low_relationship": self.last_low_relationship,
            "direction": self.direction,
            "protected_high": self.protected_high,
            "protected_low": self.protected_low,
            "weak_high": self.weak_high,
            "weak_low": self.weak_low,
            "transition_count": self.transition_count,
            "last_transition_code": self.last_transition_code,
            "last_broken_key": self.last_broken_key,
            "last_broken_level": self.last_broken_level,
        }


@dataclass(frozen=True)
class ReplayResult:
    states: tuple[TerminalState, ...]
    field_hashes: dict[str, int]
    state_hash_1: int
    state_hash_2: int


def _evaluate_terminal(
    candles: tuple[NormalizedCandle, ...],
    atr_all,
    terminal: int,
    lookback: int,
    measurement_configuration: MarketMeasurementConfiguration,
    structure_configuration: StructureConfiguration,
) -> TerminalState:
    window_first = max(0, terminal + 1 - lookback)
    window = candles[window_first : terminal + 1]
    watr = window_atr(atr_all, terminal, lookback)

    confirmed_bar_count = terminal + 1
    abs_first = confirmed_bar_count - len(window)

    with _TRUNC.injected_atr(watr):
        swings = _DIAG._confirmed_swings(window, measurement_configuration)

    relationships = detect_swing_relationships(
        tuple(swings), structure_configuration
    )
    analysis = analyze_structure_state(
        tuple(window),
        tuple(swings),
        structure_configuration,
        ContentAddressedIdentityProvider(),
    )
    state = analysis.current_state

    # -- swing view diagnostics (Pine f_p2BuildSwingView last element) ----
    if swings:
        last_swing = swings[-1]
        window_index_by_time = {
            candle.event_time_utc: idx for idx, candle in enumerate(window)
        }
        start_idx = window_index_by_time.get(last_swing.pivot_start_time_utc)
        if start_idx is None:
            raise ReplayInputError(
                f"terminal {terminal}: last swing pivot start "
                f"{last_swing.pivot_start_time_utc} not found in its own window"
            )
        last_pivot_start_abs: int | None = abs_first + start_idx
        last_conf_time: int | None = _ms(last_swing.meaningful_confirmation_time_utc)
    else:
        last_pivot_start_abs = None
        last_conf_time = None

    # -- relationship diagnostics (highs-then-lows production order) ------
    codes = [REL_CODE[record.label] for record in relationships]
    last_high_relationship = next(
        (code for code in reversed(codes) if code in _HIGH_REL_CODES), None
    )
    last_low_relationship = next(
        (code for code in reversed(codes) if code not in _HIGH_REL_CODES), None
    )

    # -- walk diagnostics --------------------------------------------------
    key_by_id = {swing.record_id: _ms(swing.pivot_end_time_utc) for swing in swings}

    def _key_or_sentinel(record_id) -> int:
        if record_id is None:
            return C_ST_NA
        return key_by_id[record_id]

    transitions = analysis.structure_transitions
    if transitions:
        last_transition = transitions[-1]
        last_transition_code = TR_CODE[last_transition.transition_type]
        last_broken_key = key_by_id[last_transition.broken_swing_id]
        last_broken_level: Decimal | None = last_transition.broken_level_price
    else:
        last_transition_code = C_ST_NA
        last_broken_key = C_ST_NA
        last_broken_level = None

    return TerminalState(
        evaluation_index=terminal,
        time_ms=_ms(window[-1].event_time_utc),
        confirmed_bar_count=confirmed_bar_count,
        abs_first=abs_first,
        adapted_swing_count=len(swings),
        last_pivot_start_abs=last_pivot_start_abs,
        last_conf_time=last_conf_time,
        relationship_count=len(relationships),
        last_high_relationship=last_high_relationship,
        last_low_relationship=last_low_relationship,
        direction=DIR_CODE[state.direction],
        protected_high=_key_or_sentinel(state.active_protected_high_swing_id),
        protected_low=_key_or_sentinel(state.active_protected_low_swing_id),
        weak_high=_key_or_sentinel(state.active_weak_high_swing_id),
        weak_low=_key_or_sentinel(state.active_weak_low_swing_id),
        transition_count=len(transitions),
        last_transition_code=last_transition_code,
        last_broken_key=last_broken_key,
        last_broken_level=last_broken_level,
    )


def replay(
    csv_path: Path,
    *,
    state_count: int = 300,
    lookback: int = LOOKBACK,
    mintick: Decimal = MINTICK,
) -> ReplayResult:
    """Full blind replay: context CSV in, states + frozen-contract hashes out."""
    candles = load_context_candles(csv_path)
    if len(candles) < state_count:
        raise ReplayInputError(
            f"context has {len(candles)} rows, fewer than state_count {state_count}"
        )

    measurement_configuration = MarketMeasurementConfiguration(
        minimum_price_tick=mintick
    )
    structure_configuration = StructureConfiguration()

    atr_all = compute_atr_series(candles, measurement_configuration.atr_period)

    first_terminal = len(candles) - state_count
    states = tuple(
        _evaluate_terminal(
            candles,
            atr_all,
            terminal,
            lookback,
            measurement_configuration,
            structure_configuration,
        )
        for terminal in range(first_terminal, len(candles))
    )

    records = [
        _DIGEST.encode_state_bar(state.digest_values(), mintick) for state in states
    ]
    return ReplayResult(
        states=states,
        field_hashes=_DIGEST.per_field_hashes(records),
        state_hash_1=_DIGEST.state_hashes(records)[0],
        state_hash_2=_DIGEST.state_hashes(records)[1],
    )


_TRACE_COLUMNS = [
    "evaluation_index",
    "time",
    "confirmed_bar_count",
    "abs_first",
    "adapted_swing_count",
    "last_pivot_start_abs",
    "last_conf_time",
    "relationship_count",
    "last_high_relationship",
    "last_low_relationship",
    "direction",
    "protected_high",
    "protected_low",
    "weak_high",
    "weak_low",
    "transition_count",
    "last_transition_code",
    "last_broken_key",
    "last_broken_level",
]


def write_trace(result: ReplayResult, path: Path) -> None:
    """Deterministic diagnostic trace of the Python trajectory (raw values)."""
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(_TRACE_COLUMNS)
        for state in result.states:
            writer.writerow(
                [
                    state.evaluation_index,
                    state.time_ms,
                    state.confirmed_bar_count,
                    state.abs_first,
                    state.adapted_swing_count,
                    "" if state.last_pivot_start_abs is None else state.last_pivot_start_abs,
                    "" if state.last_conf_time is None else state.last_conf_time,
                    state.relationship_count,
                    "" if state.last_high_relationship is None else state.last_high_relationship,
                    "" if state.last_low_relationship is None else state.last_low_relationship,
                    state.direction,
                    state.protected_high,
                    state.protected_low,
                    state.weak_high,
                    state.weak_low,
                    state.transition_count,
                    state.last_transition_code,
                    state.last_broken_key,
                    "" if state.last_broken_level is None else str(state.last_broken_level),
                ]
            )
