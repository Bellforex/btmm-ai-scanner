"""Bot-domain snapshot types.

These are plain, immutable VIEWS of what the scanner already computed. They
carry no rule logic: every field is copied from the scanner's own output by
``botdryrun.scanner_adapter`` (or, in tests, by a scripted source).
"""

from __future__ import annotations

import hashlib
from collections.abc import Iterator, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from decimal import Decimal
from enum import StrEnum
from typing import Protocol

from btmm_ai_scanner.config.enums import Timeframe
from btmm_ai_scanner.contracts.normalized_candle import NormalizedCandle

__all__ = [
    "BAR_DIGEST_VERSION",
    "DECISION_ROW_FIELDS",
    "GENESIS_CHAIN_DIGEST",
    "RC4_DECISION_FIELDS",
    "SESSION_DAY_OFFSET",
    "DecisionView",
    "EventView",
    "P8EventName",
    "PoiView",
    "ScannerBarSnapshot",
    "ScannerSource",
    "compute_bar_digest",
    "event_id_of",
    "fold_chain_digest",
    "trading_day_of",
]

#: V2: the digest also covers every P5 decision row including the RC4
#: market-framework fields (``DecisionView.canonical_line``).
BAR_DIGEST_VERSION = "BOT-DRYRUN-BAR-V2"

#: FXCM session day: 22:00 UTC opens the next trading day. Mirrors the frozen
#: authority decision (``rc3_daily_authority.SESSION_DAY_OFFSET``).
SESSION_DAY_OFFSET = timedelta(hours=2)


def trading_day_of(bar_open_utc: datetime) -> str:
    return (bar_open_utc + SESSION_DAY_OFFSET).date().isoformat()


class P8EventName(StrEnum):
    """String names of the five native P8 event types (payload only)."""

    POI_ACTIVATED = "POI_ACTIVATED"
    BTMM_VALIDATED = "BTMM_VALIDATED"
    PERMISSION_ENTERED_ACTIONABLE = "PERMISSION_ENTERED_ACTIONABLE"
    PERMISSION_LOST_ACTIONABLE = "PERMISSION_LOST_ACTIONABLE"
    POI_TERMINAL = "POI_TERMINAL"


def event_id_of(event_type: str, poi_idx: int, bar_ms: int) -> str:
    """The native P8 identity ``(event_type, poi_idx, bar_ms)`` as a string."""
    return f"{event_type}:{poi_idx}:{bar_ms}"


@dataclass(frozen=True)
class PoiView:
    record_id: str
    poi_idx: int | None
    poi_type: str
    direction: str  # "BULLISH" | "BEARISH"
    family: str
    source_timeframe: str
    effective_timeframe: str
    zone_top: Decimal
    zone_bottom: Decimal
    source_time_utc: str
    availability_time_utc: str
    fresh_active: bool | None
    terminal_reason: str | None
    terminal_time_utc: str | None

    def as_row(self) -> tuple[object, ...]:
        return (
            self.record_id,
            self.poi_idx,
            self.poi_type,
            self.direction,
            self.family,
            self.source_timeframe,
            self.effective_timeframe,
            str(self.zone_top),
            str(self.zone_bottom),
            self.source_time_utc,
            self.availability_time_utc,
            None if self.fresh_active is None else int(self.fresh_active),
            self.terminal_reason,
            self.terminal_time_utc,
        )


#: RC4 market-framework fields copied verbatim from ``BtrcDecision`` (their
#: defaults are what the scanner emits when the RC4 profile is off).
RC4_DECISION_FIELDS: tuple[str, ...] = (
    "framework",
    "fib_bucket",
    "retracement_pct",
    "range_position",
    "sweep_before_poi",
    "btmm_pretrade_reason",
    "btmm_distraction",
    "btmm_delay",
    "btmm_wipeout",
    "btmm_true_failure",
    "poi_dwell_bars",
    "poi_touch_count",
    "poi_zone_return_count",
    "interaction_episode",
)

#: Column order of one decision row (journal + digest line).
DECISION_ROW_FIELDS: tuple[str, ...] = (
    "record_id",
    "poi_idx",
    "permission",
    "permission_code",
    "actionable",
    "final_score",
    "lifecycle",
    "btmm_valid",
    *RC4_DECISION_FIELDS,
)


@dataclass(frozen=True)
class DecisionView:
    record_id: str
    poi_idx: int
    permission: str
    permission_code: int
    actionable: bool
    final_score: int
    lifecycle: str
    btmm_valid: bool
    # --- RC4 market framework (BtrcDecision; defaults when the profile is off)
    framework: str | None = None
    fib_bucket: str | None = None
    retracement_pct: str | None = None
    range_position: str | None = None
    sweep_before_poi: bool = False
    btmm_pretrade_reason: str | None = None
    btmm_distraction: bool = False
    btmm_delay: bool = False
    btmm_wipeout: bool = False
    btmm_true_failure: bool = False
    poi_dwell_bars: int = 0
    poi_touch_count: int = 0
    poi_zone_return_count: int = 0
    interaction_episode: str | None = None

    def as_row(self) -> tuple[object, ...]:
        """Storage/journal row in ``DECISION_ROW_FIELDS`` order (bools as 0/1)."""
        out: list[object] = []
        for name in DECISION_ROW_FIELDS:
            value = getattr(self, name)
            out.append(int(value) if isinstance(value, bool) else value)
        return tuple(out)

    def canonical_line(self) -> str:
        return "|".join("" if v is None else str(v) for v in self.as_row())


@dataclass(frozen=True)
class EventView:
    event_type: str
    poi_idx: int
    bar_ms: int
    sequence_in_bar: int
    poi_record_id: str
    poi_bullish: bool
    tier: int
    btmm_valid: bool
    permission: int
    lifecycle: int
    terminal_reason: str | None

    @property
    def event_id(self) -> str:
        return event_id_of(self.event_type, self.poi_idx, self.bar_ms)


@dataclass(frozen=True)
class ScannerBarSnapshot:
    bar_index: int
    #: The bar's CLOSE (availability) instant in epoch ms — the P8 ``bar_ms``.
    bar_ms: int
    candle: NormalizedCandle
    trading_day: str
    primed: bool
    #: Full registry (every POI observation), in scanner order.
    pois: tuple[PoiView, ...]
    #: The P5-evaluated POIs this bar, in the scanner's evaluation order.
    decisions: tuple[DecisionView, ...]
    #: P8 events, in the native engine order.
    events: tuple[EventView, ...]
    new_registry_pois: int
    fresh_at_close: int
    mitigated_at_close: int
    invalidated_at_close: int
    #: Canonical per-stream lines (authority P3/P5/P8 row formats).
    p3_lines: tuple[str, ...]
    p5_lines: tuple[str, ...]
    p8_lines: tuple[str, ...]
    digest: str = field(default="")

    def poi_by_idx(self) -> dict[int, PoiView]:
        return {p.poi_idx: p for p in self.pois if p.poi_idx is not None}

    def decision_by_idx(self) -> dict[int, DecisionView]:
        return {d.poi_idx: d for d in self.decisions}


def compute_bar_digest(
    *,
    bar_index: int,
    bar_ms: int,
    primed: bool,
    registry_size: int,
    new_registry_pois: int,
    fresh_at_close: int,
    mitigated_at_close: int,
    invalidated_at_close: int,
    p3_lines: Sequence[str],
    p5_lines: Sequence[str],
    p8_lines: Sequence[str],
    decision_lines: Sequence[str] = (),
) -> str:
    h = hashlib.sha256()
    header = (
        f"{BAR_DIGEST_VERSION}|{bar_index}|{bar_ms}|{int(primed)}|{registry_size}|"
        f"{new_registry_pois}|{fresh_at_close}|{mitigated_at_close}|{invalidated_at_close}"
    )
    h.update(header.encode("utf-8") + b"\n")
    for tag, lines in (
        ("P3", p3_lines),
        ("P5", p5_lines),
        ("P8", p8_lines),
        ("DV", decision_lines),
    ):
        h.update(f"#{tag}|{len(lines)}\n".encode())
        for line in lines:
            h.update(line.encode("utf-8") + b"\n")
    return h.hexdigest()


def fold_chain_digest(previous: str, bar_digest: str) -> str:
    return hashlib.sha256(f"{previous}|{bar_digest}".encode()).hexdigest()


#: Chain digest before the first bar.
GENESIS_CHAIN_DIGEST = hashlib.sha256(BAR_DIGEST_VERSION.encode()).hexdigest()


class ScannerSource(Protocol):
    """Anything that turns a host/context series into per-bar snapshots.

    Production uses ``LevelAScannerSource``. Tests may substitute a scripted
    source to exercise the bot's own plumbing (restart, dedup, broker).
    """

    def iterate(
        self,
        host_timeframe: Timeframe,
        host_series: Sequence[NormalizedCandle],
        context_series: Mapping[Timeframe, Sequence[NormalizedCandle]],
    ) -> Iterator[ScannerBarSnapshot]: ...
