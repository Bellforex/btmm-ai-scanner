"""Offline blind replay of P3 CORE over the frozen atomic context.

Test/parity tooling only — nothing in `src/` imports this, and it changes no
production semantics.

BLIND means the replay never sees a target. It takes only the frozen context
CSV, drives the authoritative P3 pipeline, and reports the digests it computed.
Comparison happens afterwards, in the caller. No expected hash is an input to
any computation here, so a "match" cannot be manufactured.

NOTHING IS REIMPLEMENTED. Every layer is the already-verified one:

* candles come from `p2_atomic_state_replay.load_context_candles`, the same
  loader the P2 campaign used, so the CSV is interpreted identically;
* ATR is production's `compute_atr_series` over the WHOLE context, because the
  Wilder ATR is an IIR filter and a truncated seed would drift;
* detection is `p3_pine_model.run_frontier` — the Pine frontier transcription;
* lifecycle is `p3_lifecycle_model.PoiLifecycleCursor` — the committed-boundary
  cursor;
* digests are `p3_digest`, the frozen contract the Pine probe also reuses.

The pipeline is the one asserted by tests/unit/test_p3_core_parity.py, so this
module adds an input source and a trace, not semantics.
"""

from __future__ import annotations

import csv
import importlib.util
import sys
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from types import ModuleType
from typing import Any

from btmm_ai_scanner.contracts.normalized_candle import NormalizedCandle
from btmm_ai_scanner.measurements.atr import compute_atr_series
from btmm_ai_scanner.poi.configuration import PoiConfiguration
from btmm_ai_scanner.poi.enums import PoiDirection

_HERE = Path(__file__).parent


def _load(name: str, filename: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, _HERE / filename)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


M = _load("_p3replay_detectors", "p3_pine_model.py")
L = _load("_p3replay_lifecycle", "p3_lifecycle_model.py")
G = _load("_p3replay_digest", "p3_digest.py")
P2R = _load("_p3replay_context", "p2_atomic_state_replay.py")

load_context_candles = P2R.load_context_candles


@dataclass(frozen=True)
class ReplayResult:
    """Everything the comparison needs, and nothing it could be biased by."""

    registry_count: int
    active_count: int
    terminal_count: int
    overall_hash_1: int
    overall_hash_2: int
    family_hashes: dict[str, int]
    lifecycle_hashes: dict[str, int]
    states: list[Any]

    def trace_rows(self, mintick: Decimal) -> list[list[str]]:
        """One canonical row per POI, in AD-1 order — the byte-level artifact.

        Determinism is asserted on THIS, not just on the hashes: two runs must
        produce identical bytes, so a coincidental hash agreement cannot hide a
        difference in the underlying records.
        """
        ordered = G.order_states(self.states, mintick)
        rows: list[list[str]] = []
        for state in ordered:
            rows.append([str(value) for value in state.encoded(mintick)])
        return rows


def reference_zone_pois(
    candles: tuple[NormalizedCandle, ...],
    atr_all: Any,
    mintick: Decimal,
    lookback: int = 300,
) -> list[Any]:
    """Every reference-zone POI the frontier emits, deduplicated by identity.

    Pine calls `f_poiDetectReferenceZones()` on EVERY confirmed bar, projecting
    whatever P1 has published in `srCached` for the CURRENT rolling window, with
    `f_poiEmit` collapsing repeats by identity. Reproducing that means running
    the windowed S/R detection per bar rather than once at the end: a zone that
    exists only mid-run still enters the registry and never leaves it.

    The window, the injected continuous ATR and the swing detector are the same
    ones the P2 campaign validated, so this adds no new P1 semantics.
    """
    from btmm_ai_scanner.domain.configuration import MarketMeasurementConfiguration
    from btmm_ai_scanner.domain.support_resistance import (
        detect_support_resistance_zones,
    )

    measurement = MarketMeasurementConfiguration(minimum_price_tick=mintick)
    emitted: list[Any] = []
    seen: set[tuple[int, int, int, int]] = set()
    for terminal in range(len(candles)):
        window_first = max(0, terminal + 1 - lookback)
        window = candles[window_first : terminal + 1]
        watr = P2R.window_atr(atr_all, terminal, lookback)
        with P2R._TRUNC.injected_atr(watr):
            swings = P2R._DIAG._confirmed_swings(window, measurement)
            if not swings:
                continue
            # The S/R detector recomputes the ATR from whatever candles it is
            # handed. Production hands it the WHOLE history, so it measures the
            # continuous Wilder ATR; handing it a bare 300-bar window would make
            # it measure a cold-started one instead, and its reaction gate reads
            # those values directly. It therefore has to stay INSIDE the
            # injection with the swing detector, not outside it.
            zones = detect_support_resistance_zones(
                tuple(window), tuple(swings), measurement
            )
        for poi in M.project_reference_zones(zones):
            if poi.identity not in seen:
                seen.add(poi.identity)
                emitted.append(poi)
    return emitted


def replay(
    candles: tuple[NormalizedCandle, ...],
    mintick: Decimal,
    *,
    include_reference_zones: bool = True,
) -> ReplayResult:
    """Detection -> persistent identity -> persistent lifecycle -> projection."""
    configuration = PoiConfiguration(minimum_price_tick=mintick)
    atr_all = compute_atr_series(candles, 14)
    registry = M.run_frontier(list(candles), configuration)
    if include_reference_zones:
        registry = [*registry, *reference_zone_pois(candles, atr_all, mintick)]

    states: list[Any] = []
    for poi in registry:
        direction = PoiDirection.BULLISH if poi.direction == 1 else PoiDirection.BEARISH
        cursor = L.PoiLifecycleCursor(
            zone_top=poi.zone_top,
            zone_bottom=poi.zone_bottom,
            direction=direction,
            availability_ms=poi.confirm_time,
            configuration=configuration,
        )
        for index in range(len(candles)):
            cursor.advance(candles, atr_all, index)
        code, count, relevant, last = cursor.downstream_projection()
        states.append(
            G.P3PoiState(
                poi_type=poi.poi_type,
                direction=poi.direction,
                zone_bottom=poi.zone_bottom,
                zone_top=poi.zone_top,
                candidate_time=poi.candidate_time,
                confirm_time=poi.confirm_time,
                avail_time=poi.confirm_time,
                tier=poi.tier,
                src_first_time=poi.src_first_time,
                src_count=poi.src_count,
                src_last_time=poi.src_last_time,
                status=code,
                transition_count=count,
                relevant_count=relevant,
                last_transition_code=last[0],
                last_transition_event=last[1],
                last_transition_avail=last[2],
                tap_count=cursor.tap_count,
            )
        )

    total, active, terminal = G.counts(states)
    hash_1, hash_2 = G.overall_hashes(states, mintick)
    return ReplayResult(
        registry_count=total,
        active_count=active,
        terminal_count=terminal,
        overall_hash_1=hash_1,
        overall_hash_2=hash_2,
        family_hashes=G.family_hashes(states, mintick),
        lifecycle_hashes=G.lifecycle_hashes(states, mintick),
        states=states,
    )


def replay_csv(csv_path: Path, mintick: Decimal) -> ReplayResult:
    """Load the frozen context and replay it. The only entry point callers need."""
    return replay(load_context_candles(csv_path), mintick)


def write_trace(result: ReplayResult, mintick: Decimal, path: Path) -> None:
    header = [name for name, _kind in G.POI_FIELD_ORDER]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(header)
        writer.writerows(result.trace_rows(mintick))
