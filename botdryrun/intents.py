"""Paper trade intents.

A trade intent is an explanatory record, written once for every consumed P8
``PERMISSION_ENTERED_ACTIONABLE`` event: which POI, which direction, what the
scanner said about it at that bar (P5 permission and score, BTMM pre-trade
reason, RC4 location: framework / range position / fib bucket /
retracement, sweep, interaction episode) and what the practice policy did
with it (the linked signal id, ACCEPTED or SKIPPED + reason).

It is NOT an order and places nothing. It carries no rule logic: every field
is copied from the consumed event, the POI view and the P5 decision view of
the SAME snapshot, all produced by the scanner. The trigger is the consumed
P8 event only — a P5 decision without an event never yields an intent.

Intent ids are ``INT-`` + sha256(native event id)[:20]; one event can only
ever produce one intent, so a restart never duplicates one.
"""

from __future__ import annotations

import hashlib
from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal

from botdryrun.domain import EventView, P8EventName, ScannerBarSnapshot
from botdryrun.policy import SignalDecision, signal_id_for
from botdryrun.safety import EXECUTION_MODE

__all__ = ["TRADE_INTENT_COLUMNS", "TradeIntent", "build_trade_intents", "intent_id_for"]

TRADE_INTENT_COLUMNS: tuple[str, ...] = (
    "intent_id",
    "source_event_id",
    "bar_index",
    "bar_ms",
    "trading_day",
    "poi_idx",
    "poi_record_id",
    "direction",
    "poi_type",
    "source_timeframe",
    "effective_timeframe",
    "zone_bottom",
    "zone_top",
    "event_permission_code",
    "permission",
    "final_score",
    "btmm_valid",
    "btmm_pretrade_reason",
    "framework",
    "range_position",
    "fib_bucket",
    "retracement_pct",
    "sweep_before_poi",
    "interaction_episode",
    "signal_id",
    "signal_status",
    "signal_reason",
    "execution_mode",
)


def intent_id_for(event_id: str) -> str:
    return "INT-" + hashlib.sha256(event_id.encode("utf-8")).hexdigest()[:20]


@dataclass(frozen=True)
class TradeIntent:
    intent_id: str
    source_event_id: str
    bar_index: int
    bar_ms: int
    trading_day: str
    poi_idx: int
    poi_record_id: str
    direction: str  # "LONG" | "SHORT"
    poi_type: str | None
    source_timeframe: str | None
    effective_timeframe: str | None
    zone_bottom: Decimal | None
    zone_top: Decimal | None
    event_permission_code: int
    permission: str | None
    final_score: int | None
    btmm_valid: bool
    btmm_pretrade_reason: str | None
    framework: str | None
    range_position: str | None
    fib_bucket: str | None
    retracement_pct: str | None
    sweep_before_poi: bool | None
    interaction_episode: str | None
    signal_id: str | None
    signal_status: str | None
    signal_reason: str | None
    execution_mode: str = EXECUTION_MODE

    def as_row(self) -> tuple[object, ...]:
        out: list[object] = []
        for name in TRADE_INTENT_COLUMNS:
            value = getattr(self, name)
            if isinstance(value, bool):
                value = int(value)
            elif isinstance(value, Decimal):
                value = str(value)
            out.append(value)
        return tuple(out)


def build_trade_intents(
    events: Sequence[EventView],
    snapshot: ScannerBarSnapshot,
    signals: Sequence[SignalDecision],
) -> tuple[TradeIntent, ...]:
    """One intent per consumed ``PERMISSION_ENTERED_ACTIONABLE`` event."""
    pois = snapshot.poi_by_idx()
    decisions = snapshot.decision_by_idx()
    signal_by_id = {s.signal_id: s for s in signals}
    intents: list[TradeIntent] = []
    for event in events:
        if event.event_type != P8EventName.PERMISSION_ENTERED_ACTIONABLE.value:
            continue
        poi = pois.get(event.poi_idx)
        decision = decisions.get(event.poi_idx)
        signal = signal_by_id.get(signal_id_for(event.event_id))
        intents.append(
            TradeIntent(
                intent_id=intent_id_for(event.event_id),
                source_event_id=event.event_id,
                bar_index=snapshot.bar_index,
                bar_ms=snapshot.bar_ms,
                trading_day=snapshot.trading_day,
                poi_idx=event.poi_idx,
                poi_record_id=event.poi_record_id,
                direction="LONG" if event.poi_bullish else "SHORT",
                poi_type=poi.poi_type if poi else None,
                source_timeframe=poi.source_timeframe if poi else None,
                effective_timeframe=poi.effective_timeframe if poi else None,
                zone_bottom=poi.zone_bottom if poi else None,
                zone_top=poi.zone_top if poi else None,
                event_permission_code=event.permission,
                permission=decision.permission if decision else None,
                final_score=decision.final_score if decision else None,
                btmm_valid=event.btmm_valid,
                btmm_pretrade_reason=decision.btmm_pretrade_reason if decision else None,
                framework=decision.framework if decision else None,
                range_position=decision.range_position if decision else None,
                fib_bucket=decision.fib_bucket if decision else None,
                retracement_pct=decision.retracement_pct if decision else None,
                sweep_before_poi=decision.sweep_before_poi if decision else None,
                interaction_episode=decision.interaction_episode if decision else None,
                signal_id=signal.signal_id if signal else None,
                signal_status=signal.status if signal else None,
                signal_reason=signal.reason if signal else None,
            )
        )
    return tuple(intents)
