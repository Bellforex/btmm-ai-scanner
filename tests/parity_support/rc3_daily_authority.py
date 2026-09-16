"""RC3 continuous daily LEVEL-A authority.

Test/validation tooling only — nothing in ``src/`` imports this, and it
changes no production semantics.

WHAT THIS IS
-------------
An independent, six-timeframe, strictly chronological Python replay of a
real FXCM XAUUSD window, producing — per confirmed host bar, per eligible
POI — the full P3 registry state, the BTMM state, the full P5 assessment
and the derived P8 events, plus a per-trading-day manifest and reproducible
period digests.

It is LEVEL A: every value is derived from raw OHLC through the frozen
engines in ``src/``. It never reads a Pine log (``P3LIFE`` / ``P5EVAL`` /
``P8EVENT``) or the ``P5WIRE`` diagnostic transport. A later LEVEL A ==
LEVEL B comparison is therefore a genuine parity claim.

CONTINUITY IS THE POINT
------------------------
The replay is ONE uninterrupted walk (``level_a_replay.iter_level_a_bars``).
Nothing resets at a day, week or weekend boundary: the kernel, the visible
-candle accumulator, the POI registry, the P5 active set, the ``poi_idx``
assignment and the P8 alert engine are all carried straight across. A POI
can appear on Monday, stay fresh through Tuesday, be evaluated on Wednesday
and terminate on Thursday, and every one of those bars is produced by the
same live state. Days are a REPORTING partition applied after the fact, not
an execution partition — ``tests/unit/test_rc3_daily_authority.py`` proves
this by construction.

THE FOUR FROZEN AUTHOR DECISIONS THIS IMPLEMENTS
--------------------------------------------------
1. **P5 terminal-bar policy.** A POI stays eligible for P5 on the bar it
   goes terminal, and is excluded starting from the FOLLOWING bar. Owned by
   ``p5_active_poi_loop_model._resolve_from_terminal_flags``; this module
   only selects the RC3 (``fresh_active``) notion of terminality.
2. **Same-bar terminal precedence.** If mitigation and invalidation become
   eligible on the same bar, MITIGATED wins. Owned by
   ``btmm_ai_scanner.poi.lifecycle.resolve_terminal`` (invalidation only
   wins when it is STRICTLY earlier); this module reports
   ``terminal_reason`` as the engine produced it and never re-ranks.
3. **P8 native contract.** Activation fires when a ``poi_idx`` first enters
   the alert engine's known set; native identity is
   ``(event_type, poi_idx, bar_ms)``; same-bar ordering is ``poi_idx`` then
   event priority; ``terminal_reason`` is payload, never identity. Owned by
   ``p8_alert_oracle``. This module writes events in the exact order the
   engine returned them and NEVER re-sorts by a semantic key.
4. **Trading-day partition.** A day is the FXCM session day, not the UTC
   calendar day: the session runs 22:00 UTC to 20:45 UTC, so the trading
   day of a bar is ``(event_time_utc + 2h).date()``. Verified against the
   window's own observed session gaps.

THE DIGEST FOLD (reproducible by hand)
---------------------------------------
Each record is rendered to one canonical line: the declared field order for
its stream, joined with ``|``, rendered by ``_fmt`` (None -> empty, bool ->
``1``/``0``, Decimal/datetime -> their exact textual form). A day's digest
for a stream is ``sha256`` of that day's lines in emission order, each
terminated by ``\\n``. The period digest is an explicit left fold over the
ordered daily digests::

    acc = sha256(f"{VERSION}|{stream}")
    for day in chronological_days:
        acc = sha256(f"{acc}|{day}|{day_digest}")

so the period digest changes if any day's content changes, if a day is
added or removed, or if the days are reordered.

WARM-UP AND THE M5 DEPTH LIMIT (disclosed)
--------------------------------------------
W1/D1/H4/H1 carry a bounded pre-window warm-up (``context_lookback_bars``,
default 250 bars each) — background context only, exactly as the V1-A
harness already does, and well above every warm-up floor this codebase
declares. The cap applies to PRE-WINDOW history only; an in-window context
bar is never dropped. M5's source file begins at the window's own first
instant, so M5 has ZERO pre-window history. That is the real depth limit of
the acquired feed, not a choice, and it is recorded in the run provenance
(``pre_window_bars`` / ``pre_window_bars_available`` per series).

The host M15 series is sliced strictly to the requested window and is
asserted to be disjoint from the sealed out-of-sample range, so no
out-of-sample bar is ever replayed, recorded, digested or reported.
"""

from __future__ import annotations

import csv
import gzip
import hashlib
import io
import json
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from enum import Enum
from pathlib import Path
from typing import Any
from uuid import UUID

from btmm_ai_scanner.config.enums import Timeframe
from btmm_ai_scanner.contracts.normalized_candle import NormalizedCandle
from btmm_ai_scanner.scanner.configuration import ScannerConfiguration
from tests.parity_support.level_a_replay import (
    DEFAULT_MINIMUM_PRICE_TICK,
    LevelABar,
    WarmupFeedPolicy,
    build_scanner_configuration,
    iter_level_a_bars,
)
from tests.parity_support.p5_wire_normalized_replay import PERMISSION_CODE
from tests.parity_support.p8_alert_oracle import ACTIONABLE_PERMISSIONS, P8EventType
from tests.parity_support.v1a_csv_loader import (
    MANIFEST_FILES,
    ManifestHashMismatchError,
    load_v1a_csv,
)

__all__ = [
    "AUTHORITY_VERSION",
    "CONTEXT_TIMEFRAMES",
    "DEFAULT_CONTEXT_LOOKBACK_BARS",
    "HOST_TIMEFRAME",
    "P3_FIELDS",
    "P5_FIELDS",
    "P8_FIELDS",
    "SESSION_DAY_OFFSET",
    "WINDOW_END_EVENT_UTC",
    "WINDOW_START_EVENT_UTC",
    "AuthorityResult",
    "DayManifest",
    "LevelAWindow",
    "build_authority_configuration",
    "fold_period_digest",
    "load_level_a_window",
    "run_daily_authority",
    "trading_day_of",
    "write_artifacts",
]

AUTHORITY_VERSION = "RC3-AUTHORITY-V1"

HOST_TIMEFRAME = Timeframe.M15
CONTEXT_TIMEFRAMES: tuple[Timeframe, ...] = (
    Timeframe.W1,
    Timeframe.D1,
    Timeframe.H4,
    Timeframe.H1,
    Timeframe.M5,
)

#: The replay period: the only window where all six timeframes genuinely
#: exist in the acquired feed. Both bounds are M15 bar OPEN instants.
WINDOW_START_EVENT_UTC = datetime(2026, 8, 9, 22, 0, tzinfo=UTC)
WINDOW_END_EVENT_UTC = datetime(2026, 9, 4, 20, 30, tzinfo=UTC)

#: The sealed out-of-sample range (bar OPEN instants, inclusive). No host
#: bar may ever fall inside it. See ``_assert_outside_sealed_range``.
SEALED_FIRST_EVENT_UTC = datetime(2026, 7, 14, 17, 15, tzinfo=UTC)
SEALED_LAST_EVENT_UTC = datetime(2026, 8, 3, 6, 45, tzinfo=UTC)

#: FXCM session day offset — see "THE FOUR FROZEN AUTHOR DECISIONS", item 4.
SESSION_DAY_OFFSET = timedelta(hours=2)

DEFAULT_CONTEXT_LOOKBACK_BARS = 250

#: M5 is not in the V1-A provenance manifest (it was acquired later, for the
#: six-timeframe work), so its SHA-256 is pinned here instead. The pin exists
#: for the same reason the manifest's do: this project has already been bitten
#: once by a broker silently revising an already-frozen window.
M5_FILENAME = "v1a_raw_ohlc_M5.csv"
M5_SHA256 = "55f86db9ffb161ab0099f100b16a0505deba05087164ecf5665e6bb5d419d6c2"
M5_ROW_COUNT = 5508

_FILENAME_BY_TIMEFRAME: dict[Timeframe, str] = {
    Timeframe.M15: "v1a_raw_ohlc_full_loaded.csv",
    Timeframe.W1: "v1a_raw_ohlc_W1.csv",
    Timeframe.D1: "v1a_raw_ohlc_D1.csv",
    Timeframe.H4: "v1a_raw_ohlc_H4.csv",
    Timeframe.H1: "v1a_raw_ohlc_H1.csv",
    Timeframe.M5: M5_FILENAME,
}


class SealedRangeViolationError(AssertionError):
    """A host bar was about to be replayed from the sealed out-of-sample range."""


# ---------------------------------------------------------------------------
# Canonical record shapes. The field ORDER below is load-bearing: it is the
# digest's definition. Appending a field changes every digest, which is
# intended — a digest names a contract version, not just a data set.
# ---------------------------------------------------------------------------

P3_FIELDS: tuple[str, ...] = (
    "bar_ms",
    "trading_day",
    "poi_idx",
    "poi_record_id",
    "poi_type",
    "direction",
    "family",
    "source_timeframe",
    "effective_timeframe",
    "zone_top",
    "zone_bottom",
    "representative_price",
    "strength_tier",
    "source_time_utc",
    "confirmation_time_utc",
    "availability_time_utc",
    "lifecycle_status",
    "freshness_status",
    "fresh_active",
    "terminal",
    "terminal_reason",
    "terminal_time_utc",
    "mitigation_time_utc",
    "tap_count",
    "tap_classification",
    "age_in_confirmed_bars",
)

P5_FIELDS: tuple[str, ...] = (
    "bar_ms",
    "trading_day",
    "poi_idx",
    "poi_record_id",
    "poi_timeframe",
    "poi_valid",
    "poi_lifecycle_status",
    "btmm_valid",
    "btmm_direction",
    "btmm_primary_state",
    "btmm_interaction_class",
    "btmm_reaction_classification",
    "btmm_liquidity_evidence_status",
    "btmm_market_direction_status",
    "btmm_analytical_framework_status",
    "btmm_volume_pillar_status",
    "global_direction",
    "trend_alignment",
    "regime",
    "momentum_direction",
    "momentum_acceleration",
    "breakout_state",
    "pullback_state",
    "session_context",
    "volatility_state",
    "score_btmm",
    "score_poi",
    "score_trend",
    "score_regime",
    "score_momentum",
    "score_breakout",
    "score_liquidity",
    "score_volatility",
    "final_confluence_score",
    "analytical_permission",
    "signal_lifecycle_state",
)

P8_FIELDS: tuple[str, ...] = (
    "bar_ms",
    "trading_day",
    "sequence_in_bar",
    "event_type",
    "poi_idx",
    "poi_record_id",
    "poi_bullish",
    "tier",
    "btmm_valid",
    "permission",
    "lifecycle",
    "terminal_reason",
)

def _fmt(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "1" if value else "0"
    if isinstance(value, Enum):
        return str(value.value)
    if isinstance(value, Decimal | UUID | int | str):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    raise TypeError(f"no canonical rendering for {type(value)!r}")


def _canonical_line(fields: Sequence[str], row: Mapping[str, object]) -> str:
    return "|".join(f"{name}={_fmt(row[name])}" for name in fields)


def trading_day_of(candle_event_time_utc: datetime) -> str:
    """The FXCM session day a host bar belongs to (frozen decision 4)."""
    return (candle_event_time_utc + SESSION_DAY_OFFSET).date().isoformat()


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class LevelAWindow:
    host_timeframe: Timeframe
    host_series: tuple[NormalizedCandle, ...]
    context_series: dict[Timeframe, tuple[NormalizedCandle, ...]]
    provenance: dict[str, Any]


def _verify_sha256(path: Path, expected: str) -> str:
    if not path.is_file():
        raise ManifestHashMismatchError(f"series file missing on disk: {path}")
    actual = hashlib.sha256(path.read_bytes()).hexdigest()
    if actual != expected:
        raise ManifestHashMismatchError(
            f"{path.name}: SHA-256 mismatch — expected {expected}, disk has "
            f"{actual}. Refusing to replay unverified data."
        )
    return actual


def _expected_sha_and_rows(timeframe: Timeframe) -> tuple[str, int]:
    filename = _FILENAME_BY_TIMEFRAME[timeframe]
    if filename in MANIFEST_FILES:
        _, sha, rows = MANIFEST_FILES[filename]
        return sha, rows
    return M5_SHA256, M5_ROW_COUNT


def _assert_outside_sealed_range(candles: Iterable[NormalizedCandle]) -> None:
    for candle in candles:
        if SEALED_FIRST_EVENT_UTC <= candle.event_time_utc <= SEALED_LAST_EVENT_UTC:
            raise SealedRangeViolationError(
                "refusing to replay a host bar inside the sealed out-of-sample "
                f"range: {candle.event_time_utc.isoformat()}"
            )


def load_level_a_window(
    dataset_root: Path,
    *,
    window_start_event_utc: datetime = WINDOW_START_EVENT_UTC,
    window_end_event_utc: datetime = WINDOW_END_EVENT_UTC,
    host_timeframe: Timeframe = HOST_TIMEFRAME,
    context_timeframes: Sequence[Timeframe] = CONTEXT_TIMEFRAMES,
    context_lookback_bars: int = DEFAULT_CONTEXT_LOOKBACK_BARS,
    max_bars: int | None = None,
) -> LevelAWindow:
    """Load an arbitrary window of the verified FXCM series, six timeframes.

    The host series is sliced to ``[window_start, window_end]`` on bar OPEN
    and asserted disjoint from the sealed range. Context series carry a
    bounded pre-window warm-up and are truncated at the host window's own
    final availability instant, so nothing after the window is ever visible.
    """
    host_sha, host_rows = _expected_sha_and_rows(host_timeframe)
    host_path = dataset_root / _FILENAME_BY_TIMEFRAME[host_timeframe]
    _verify_sha256(host_path, host_sha)
    all_host = load_v1a_csv(host_path, host_timeframe)
    if len(all_host) != host_rows:
        raise ManifestHashMismatchError(
            f"{host_path.name}: expected {host_rows} rows, loaded {len(all_host)}."
        )
    host = tuple(
        c
        for c in all_host
        if window_start_event_utc <= c.event_time_utc <= window_end_event_utc
    )
    if len(host) == 0:
        raise ValueError("the requested window contains no host bars.")
    if max_bars is not None:
        host = host[:max_bars]
    _assert_outside_sealed_range(host)

    last_availability = host[-1].availability_time_utc
    first_availability = host[0].availability_time_utc

    context: dict[Timeframe, tuple[NormalizedCandle, ...]] = {}
    provenance_series: list[dict[str, Any]] = [
        {
            "timeframe": host_timeframe.value,
            "role": "host",
            "file": host_path.name,
            "sha256": host_sha,
            "file_rows": host_rows,
            "window_bars": len(host),
            "pre_window_bars": 0,
            "pre_window_bars_available": 0,
            "warmup_fed_before_first_host_bar": 0,
            "first_event_utc": host[0].event_time_utc.isoformat(),
            "last_event_utc": host[-1].event_time_utc.isoformat(),
        }
    ]
    for timeframe in context_timeframes:
        sha, rows = _expected_sha_and_rows(timeframe)
        path = dataset_root / _FILENAME_BY_TIMEFRAME[timeframe]
        _verify_sha256(path, sha)
        loaded = load_v1a_csv(path, timeframe)
        if len(loaded) != rows:
            raise ManifestHashMismatchError(
                f"{path.name}: expected {rows} rows, loaded {len(loaded)}."
            )
        bounded = [c for c in loaded if c.availability_time_utc <= last_availability]
        # The cap applies to genuine PRE-WINDOW history only. A context bar
        # that opens inside the window is in-window data and is never capped,
        # even when it closes before the first host bar does (M5 opens two
        # bars before the first M15 bar closes).
        pre_window = [c for c in bounded if c.event_time_utc < window_start_event_utc]
        in_window = [c for c in bounded if c.event_time_utc >= window_start_event_utc]
        capped = pre_window[-context_lookback_bars:] if context_lookback_bars > 0 else []
        series = tuple(capped) + tuple(in_window)
        context[timeframe] = series
        provenance_series.append(
            {
                "timeframe": timeframe.value,
                "role": "context",
                "file": path.name,
                "sha256": sha,
                "file_rows": rows,
                "window_bars": len(in_window),
                "pre_window_bars": len(capped),
                "pre_window_bars_available": len(pre_window),
                "warmup_fed_before_first_host_bar": sum(
                    1 for c in series if c.availability_time_utc < first_availability
                ),
                "first_event_utc": (
                    series[0].event_time_utc.isoformat() if series else None
                ),
                "last_event_utc": (
                    series[-1].event_time_utc.isoformat() if series else None
                ),
            }
        )

    provenance = {
        "authority_version": AUTHORITY_VERSION,
        "evidence_level": "A",
        "evidence_level_note": (
            "Independent Python derived from raw FXCM OHLC. No Pine log, "
            "P5WIRE, P5EVAL or P8EVENT input of any kind."
        ),
        "window_start_event_utc": host[0].event_time_utc.isoformat(),
        "window_end_event_utc": host[-1].event_time_utc.isoformat(),
        "context_lookback_bars": context_lookback_bars,
        "warmup_feed_policy": WarmupFeedPolicy.AVAILABILITY.value,
        "session_day_offset_hours": SESSION_DAY_OFFSET.total_seconds() / 3600.0,
        "series": provenance_series,
    }
    return LevelAWindow(
        host_timeframe=host_timeframe,
        host_series=host,
        context_series=context,
        provenance=provenance,
    )


def build_authority_configuration(
    *,
    host_timeframe: Timeframe = HOST_TIMEFRAME,
    context_timeframes: Sequence[Timeframe] = CONTEXT_TIMEFRAMES,
) -> ScannerConfiguration:
    return build_scanner_configuration(
        required_timeframes=frozenset({host_timeframe}),
        optional_timeframes=frozenset(context_timeframes),
        minimum_price_tick=DEFAULT_MINIMUM_PRICE_TICK,
    )


# ---------------------------------------------------------------------------
# Daily manifest + digests
# ---------------------------------------------------------------------------


@dataclass
class DayManifest:
    trading_day: str
    first_bar_ms: int
    last_bar_ms: int
    first_bar_utc: str
    last_bar_utc: str
    bars_processed: int = 0
    new_p3_pois: int = 0
    total_registry_pois: int = 0
    pois_fresh_at_close: int = 0
    pois_mitigated_at_close: int = 0
    pois_invalidated_at_close: int = 0
    p5_rows: int = 0
    p5_actionable: int = 0
    p8_events: int = 0
    p8_terminal_events: int = 0
    p3_digest: str = ""
    p5_digest: str = ""
    p8_digest: str = ""

    def as_row(self) -> dict[str, Any]:
        return {
            "trading_day": self.trading_day,
            "first_bar_ms": self.first_bar_ms,
            "last_bar_ms": self.last_bar_ms,
            "first_bar_utc": self.first_bar_utc,
            "last_bar_utc": self.last_bar_utc,
            "bars_processed": self.bars_processed,
            "new_p3_pois": self.new_p3_pois,
            "total_registry_pois": self.total_registry_pois,
            "pois_fresh_at_close": self.pois_fresh_at_close,
            "pois_mitigated_at_close": self.pois_mitigated_at_close,
            "pois_invalidated_at_close": self.pois_invalidated_at_close,
            "p5_rows": self.p5_rows,
            "p5_actionable": self.p5_actionable,
            "p8_events": self.p8_events,
            "p8_terminal_events": self.p8_terminal_events,
            "p3_digest": self.p3_digest,
            "p5_digest": self.p5_digest,
            "p8_digest": self.p8_digest,
        }


DAY_MANIFEST_COLUMNS: tuple[str, ...] = tuple(
    DayManifest(
        trading_day="", first_bar_ms=0, last_bar_ms=0, first_bar_utc="", last_bar_utc=""
    ).as_row()
)


@dataclass
class AuthorityResult:
    provenance: dict[str, Any]
    days: list[DayManifest]
    period_p3_digest: str
    period_p5_digest: str
    period_p8_digest: str
    bars_processed: int
    distinct_pois: int
    p3_rows: int
    p5_rows_total: int
    p8_events_total: int
    p8_events_by_type: dict[str, int]
    terminal_reason_counts: dict[str, int]
    primed_poi_count: int
    #: Only populated when ``retain_rows=True`` (tests); the full canonical
    #: lines, in emission order.
    retained_p3: list[str] = field(default_factory=list)
    retained_p5: list[str] = field(default_factory=list)
    retained_p8: list[str] = field(default_factory=list)

    def summary(self) -> dict[str, Any]:
        return {
            "authority_version": AUTHORITY_VERSION,
            "trading_days": len(self.days),
            "first_trading_day": self.days[0].trading_day if self.days else None,
            "last_trading_day": self.days[-1].trading_day if self.days else None,
            "bars_processed": self.bars_processed,
            "distinct_pois": self.distinct_pois,
            "p3_rows": self.p3_rows,
            "p5_rows": self.p5_rows_total,
            "p8_events": self.p8_events_total,
            "p8_events_by_type": self.p8_events_by_type,
            "terminal_reason_counts": self.terminal_reason_counts,
            "pois_primed_at_attach": self.primed_poi_count,
            "period_p3_digest": self.period_p3_digest,
            "period_p5_digest": self.period_p5_digest,
            "period_p8_digest": self.period_p8_digest,
        }


def fold_period_digest(stream: str, days: Sequence[tuple[str, str]]) -> str:
    """Left-fold ordered ``(trading_day, daily_digest)`` pairs into one digest.

    Documented in the module docstring, "THE DIGEST FOLD"; reproducible with
    nothing but ``sha256`` and the manifest CSV.
    """
    acc = hashlib.sha256(f"{AUTHORITY_VERSION}|{stream}".encode()).hexdigest()
    for day, digest in days:
        acc = hashlib.sha256(f"{acc}|{day}|{digest}".encode()).hexdigest()
    return acc


def _p3_row(bar: LevelABar, poi_id: UUID, trading_day: str) -> dict[str, object]:
    poi = bar.observation_by_id[poi_id]
    state = bar.state_by_id.get(poi_id)
    return {
        "bar_ms": bar.bar_ms,
        "trading_day": trading_day,
        "poi_idx": bar.poi_idx_by_id[poi_id],
        "poi_record_id": poi.record_id,
        "poi_type": poi.poi_type,
        "direction": poi.direction,
        "family": poi.family,
        "source_timeframe": poi.source_timeframe,
        "effective_timeframe": poi.effective_timeframe,
        "zone_top": poi.zone_top,
        "zone_bottom": poi.zone_bottom,
        "representative_price": poi.representative_price,
        "strength_tier": poi.strength_tier,
        "source_time_utc": poi.candidate_event_time_utc,
        "confirmation_time_utc": poi.confirmation_time_utc,
        "availability_time_utc": poi.availability_time_utc,
        "lifecycle_status": state.poi_lifecycle_status if state else None,
        "freshness_status": state.freshness_status if state else None,
        "fresh_active": state.fresh_active if state else None,
        "terminal": (not state.fresh_active) if state else None,
        "terminal_reason": state.terminal_reason if state else None,
        "terminal_time_utc": state.terminal_time_utc if state else None,
        "mitigation_time_utc": state.mitigation_time_utc if state else None,
        "tap_count": state.tap_count if state else None,
        "tap_classification": state.tap_classification if state else None,
        "age_in_confirmed_bars": state.age_in_confirmed_bars if state else None,
    }


def _p5_row(bar: LevelABar, poi_id: UUID, trading_day: str) -> dict[str, object]:
    decision = bar.decision_by_id[poi_id]
    scores = decision.component_scores
    setup = bar.setup_by_poi_id.get(poi_id)
    return {
        "bar_ms": bar.bar_ms,
        "trading_day": trading_day,
        "poi_idx": bar.poi_idx_by_id[poi_id],
        "poi_record_id": decision.poi_record_id,
        "poi_timeframe": decision.poi_timeframe,
        "poi_valid": decision.poi_valid,
        "poi_lifecycle_status": decision.poi_lifecycle_status,
        "btmm_valid": decision.btmm_valid,
        "btmm_direction": setup.btmm_direction if setup else None,
        "btmm_primary_state": setup.btmm_primary_state if setup else None,
        "btmm_interaction_class": setup.interaction_class if setup else None,
        "btmm_reaction_classification": (
            setup.reaction_classification if setup else None
        ),
        "btmm_liquidity_evidence_status": (
            setup.liquidity_evidence_status if setup else None
        ),
        "btmm_market_direction_status": setup.market_direction_status if setup else None,
        "btmm_analytical_framework_status": (
            setup.analytical_framework_status if setup else None
        ),
        "btmm_volume_pillar_status": setup.volume_pillar_status if setup else None,
        "global_direction": decision.global_direction,
        "trend_alignment": decision.trend_alignment,
        "regime": decision.regime,
        "momentum_direction": decision.momentum_direction,
        "momentum_acceleration": decision.momentum_acceleration,
        "breakout_state": decision.breakout_state,
        "pullback_state": decision.pullback_state,
        "session_context": decision.session_context,
        "volatility_state": decision.volatility_state,
        "score_btmm": scores.btmm_score,
        "score_poi": scores.poi_score,
        "score_trend": scores.trend_score,
        "score_regime": scores.regime_score,
        "score_momentum": scores.momentum_score,
        "score_breakout": scores.breakout_score,
        "score_liquidity": scores.liquidity_score,
        "score_volatility": scores.volatility_score,
        "final_confluence_score": decision.final_confluence_score,
        "analytical_permission": decision.analytical_permission,
        "signal_lifecycle_state": decision.lifecycle_state,
    }


class _StreamWriter:
    """Writes canonical lines to an optional gzipped NDJSON sink while
    maintaining the per-day digest. Digesting happens on the canonical LINE,
    never on the JSON, so the artifact format can change without moving a
    digest."""

    def __init__(self, fields: Sequence[str], path: Path | None) -> None:
        self._fields = tuple(fields)
        self._handle: gzip.GzipFile | None = None
        if path is not None:
            path.parent.mkdir(parents=True, exist_ok=True)
            # mtime=0 so a re-run produces a byte-identical archive.
            self._handle = gzip.GzipFile(filename=str(path), mode="wb", mtime=0)
        self._day_hash = hashlib.sha256()
        self.count = 0

    def write(self, row: Mapping[str, object]) -> str:
        line = _canonical_line(self._fields, row)
        self._day_hash.update(line.encode("utf-8"))
        self._day_hash.update(b"\n")
        self.count += 1
        if self._handle is not None:
            payload = {name: _fmt(row[name]) for name in self._fields}
            self._handle.write(
                (json.dumps(payload, separators=(",", ":")) + "\n").encode("utf-8")
            )
        return line

    def close_day(self) -> str:
        digest = self._day_hash.hexdigest()
        self._day_hash = hashlib.sha256()
        return digest

    def close(self) -> None:
        if self._handle is not None:
            self._handle.close()
            self._handle = None


def run_daily_authority(
    *,
    host_timeframe: Timeframe,
    host_series: Sequence[NormalizedCandle],
    context_series: Mapping[Timeframe, Sequence[NormalizedCandle]],
    configuration: ScannerConfiguration,
    provenance: Mapping[str, Any] | None = None,
    output_dir: Path | None = None,
    retain_rows: bool = False,
    progress_every: int = 0,
    progress_path: Path | None = None,
) -> AuthorityResult:
    """One continuous chronological replay, partitioned into trading days
    only for REPORTING. See the module docstring."""
    p3 = _StreamWriter(
        P3_FIELDS, (output_dir / "p3_registry_rows.ndjson.gz") if output_dir else None
    )
    p5 = _StreamWriter(
        P5_FIELDS, (output_dir / "p5_assessment_rows.ndjson.gz") if output_dir else None
    )
    p8 = _StreamWriter(
        P8_FIELDS, (output_dir / "p8_event_rows.ndjson.gz") if output_dir else None
    )

    days: list[DayManifest] = []
    current: DayManifest | None = None
    seen_registry_ids: set[UUID] = set()
    distinct_evaluated: set[int] = set()
    events_by_type: dict[str, int] = {t.value: 0 for t in P8EventType}
    terminal_reasons: dict[str, int] = {}
    retained_p3: list[str] = []
    retained_p5: list[str] = []
    retained_p8: list[str] = []
    primed_poi_count = 0
    bars_processed = 0
    started = datetime.now(tz=UTC)

    def _close_day(day: DayManifest, bar: LevelABar) -> None:
        # Registry counts at the day's CLOSE are taken over the WHOLE registry,
        # not just the bars evaluated that day: a POI that went terminal on
        # Tuesday is still counted as mitigated/invalidated on Friday.
        fresh = mitigated = invalidated = 0
        for state in bar.analysis.poi_analysis.current_poi_states:
            if state.fresh_active:
                fresh += 1
            elif state.terminal_reason is not None:
                if state.terminal_reason.value == "MITIGATED":
                    mitigated += 1
                else:
                    invalidated += 1
        day.total_registry_pois = len(bar.analysis.poi_analysis.poi_observations)
        day.pois_fresh_at_close = fresh
        day.pois_mitigated_at_close = mitigated
        day.pois_invalidated_at_close = invalidated
        day.p3_digest = p3.close_day()
        day.p5_digest = p5.close_day()
        day.p8_digest = p8.close_day()

    previous_bar: LevelABar | None = None
    try:
        for bar in iter_level_a_bars(
            host_timeframe=host_timeframe,
            host_series=host_series,
            context_series=context_series,
            configuration=configuration,
            rc3_freshness=True,
            warmup_feed_policy=WarmupFeedPolicy.AVAILABILITY,
        ):
            day_key = trading_day_of(bar.candle.event_time_utc)
            if current is None or current.trading_day != day_key:
                if current is not None and previous_bar is not None:
                    _close_day(current, previous_bar)
                    days.append(current)
                current = DayManifest(
                    trading_day=day_key,
                    first_bar_ms=bar.bar_ms,
                    last_bar_ms=bar.bar_ms,
                    first_bar_utc=bar.availability_time_utc.isoformat(),
                    last_bar_utc=bar.availability_time_utc.isoformat(),
                )
            current.last_bar_ms = bar.bar_ms
            current.last_bar_utc = bar.availability_time_utc.isoformat()
            current.bars_processed += 1
            bars_processed += 1

            for record_id in bar.observation_by_id:
                if record_id not in seen_registry_ids:
                    seen_registry_ids.add(record_id)
                    current.new_p3_pois += 1

            if bar.primed_this_bar:
                primed_poi_count = len(bar.evaluated_order)

            for poi_id in bar.evaluated_order:
                distinct_evaluated.add(bar.poi_idx_by_id[poi_id])
                line = p3.write(_p3_row(bar, poi_id, day_key))
                if retain_rows:
                    retained_p3.append(line)
                row5 = _p5_row(bar, poi_id, day_key)
                line5 = p5.write(row5)
                if retain_rows:
                    retained_p5.append(line5)
                current.p5_rows += 1
                decision = bar.decision_by_id[poi_id]
                # "Actionable" is the alert oracle's own frozen definition
                # (BUY_BIAS / SELL_BIAS), never re-derived from score bands.
                if PERMISSION_CODE[decision.analytical_permission] in (
                    ACTIONABLE_PERMISSIONS
                ):
                    current.p5_actionable += 1

            poi_id_by_idx = {bar.poi_idx_by_id[pid]: pid for pid in bar.evaluated_order}
            # Events are written in the ENGINE's own order. No re-sorting by
            # any semantic key — frozen author decision 3.
            for sequence, event in enumerate(bar.events):
                poi_id = poi_id_by_idx[event.poi_idx]
                row8 = {
                    "bar_ms": event.bar_ms,
                    "trading_day": day_key,
                    "sequence_in_bar": sequence,
                    "event_type": event.event_type,
                    "poi_idx": event.poi_idx,
                    "poi_record_id": poi_id,
                    "poi_bullish": event.poi_bullish,
                    "tier": event.tier,
                    "btmm_valid": event.btmm_valid,
                    "permission": event.permission,
                    "lifecycle": event.lifecycle,
                    "terminal_reason": event.terminal_reason,
                }
                line8 = p8.write(row8)
                if retain_rows:
                    retained_p8.append(line8)
                current.p8_events += 1
                events_by_type[event.event_type.value] += 1
                if event.event_type is P8EventType.POI_TERMINAL:
                    current.p8_terminal_events += 1
                    reason = (
                        event.terminal_reason.value
                        if event.terminal_reason is not None
                        else "UNSPECIFIED"
                    )
                    terminal_reasons[reason] = terminal_reasons.get(reason, 0) + 1

            previous_bar = bar
            if (
                progress_every
                and progress_path is not None
                and bars_processed % progress_every == 0
            ):
                elapsed = (datetime.now(tz=UTC) - started).total_seconds()
                with progress_path.open("a", encoding="utf-8") as handle:
                    handle.write(
                        f"{bars_processed}/{len(host_series)} day={day_key} "
                        f"pois={len(distinct_evaluated)} p5={p5.count} "
                        f"p8={p8.count} elapsed={elapsed:.1f}s\n"
                    )

        if current is not None and previous_bar is not None:
            _close_day(current, previous_bar)
            days.append(current)
    finally:
        p3.close()
        p5.close()
        p8.close()

    pairs_p3 = [(d.trading_day, d.p3_digest) for d in days]
    pairs_p5 = [(d.trading_day, d.p5_digest) for d in days]
    pairs_p8 = [(d.trading_day, d.p8_digest) for d in days]

    return AuthorityResult(
        provenance=dict(provenance) if provenance else {},
        days=days,
        period_p3_digest=fold_period_digest("P3", pairs_p3),
        period_p5_digest=fold_period_digest("P5", pairs_p5),
        period_p8_digest=fold_period_digest("P8", pairs_p8),
        bars_processed=bars_processed,
        distinct_pois=len(distinct_evaluated),
        p3_rows=p3.count,
        p5_rows_total=p5.count,
        p8_events_total=p8.count,
        p8_events_by_type=events_by_type,
        terminal_reason_counts=terminal_reasons,
        primed_poi_count=primed_poi_count,
        retained_p3=retained_p3,
        retained_p5=retained_p5,
        retained_p8=retained_p8,
    )


def write_artifacts(result: AuthorityResult, output_dir: Path) -> dict[str, Path]:
    """Write ``daily_authority_manifest.{csv,json}`` plus the run summary."""
    output_dir.mkdir(parents=True, exist_ok=True)
    csv_path = output_dir / "daily_authority_manifest.csv"
    json_path = output_dir / "daily_authority_manifest.json"
    summary_path = output_dir / "run_summary.json"

    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=list(DAY_MANIFEST_COLUMNS))
    writer.writeheader()
    for day in result.days:
        writer.writerow(day.as_row())
    csv_path.write_text(buffer.getvalue(), encoding="utf-8", newline="")

    json_path.write_text(
        json.dumps(
            {
                "authority_version": AUTHORITY_VERSION,
                "provenance": result.provenance,
                "period_digests": {
                    "p3": result.period_p3_digest,
                    "p5": result.period_p5_digest,
                    "p8": result.period_p8_digest,
                },
                "digest_fold": (
                    "acc = sha256(f'{AUTHORITY_VERSION}|{stream}'); "
                    "for each chronological day: "
                    "acc = sha256(f'{acc}|{trading_day}|{daily_digest}')"
                ),
                "days": [day.as_row() for day in result.days],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    summary_path.write_text(
        json.dumps(result.summary(), indent=2) + "\n", encoding="utf-8"
    )
    return {"csv": csv_path, "json": json_path, "summary": summary_path}


def main(argv: Sequence[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Run the RC3 Level-A daily authority.")
    repo_root = Path(__file__).resolve().parents[2]
    parser.add_argument(
        "--dataset-root", type=Path, default=repo_root / "artifacts" / "v1a_validation"
    )
    parser.add_argument(
        "--output-dir", type=Path, default=repo_root / "artifacts" / "rc3_authority"
    )
    parser.add_argument("--max-bars", type=int, default=None)
    parser.add_argument(
        "--context-lookback-bars", type=int, default=DEFAULT_CONTEXT_LOOKBACK_BARS
    )
    parser.add_argument("--progress-every", type=int, default=25)
    args = parser.parse_args(argv)

    window = load_level_a_window(
        args.dataset_root,
        context_lookback_bars=args.context_lookback_bars,
        max_bars=args.max_bars,
    )
    args.output_dir.mkdir(parents=True, exist_ok=True)
    progress_path = args.output_dir / "replay_progress.log"
    progress_path.write_text("", encoding="utf-8")
    result = run_daily_authority(
        host_timeframe=window.host_timeframe,
        host_series=window.host_series,
        context_series=window.context_series,
        configuration=build_authority_configuration(),
        provenance=window.provenance,
        output_dir=args.output_dir,
        progress_every=args.progress_every,
        progress_path=progress_path,
    )
    paths = write_artifacts(result, args.output_dir)
    print(json.dumps(result.summary(), indent=2))
    for label, path in paths.items():
        print(f"{label}: {path}")
    return 0


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    raise SystemExit(main())
