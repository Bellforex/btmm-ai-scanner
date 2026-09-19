"""Signal generation and risk policy.

PRACTICE POLICY — NOT A VALIDATED STRATEGY. It exists to exercise the
dry-run plumbing (event consumption, restart safety, paper execution). No
profitability claim of any kind is made for it.

The policy never looks at scores, trend, momentum or permission bands
itself. Its ONLY trigger is a consumed P8 event:

* ``PERMISSION_ENTERED_ACTIONABLE`` -> propose ONE entry in the POI's
  direction, provided the POI is still fresh in the same snapshot, the P8
  permission code agrees with the POI direction (BUY_BIAS for a bullish POI,
  SELL_BIAS for a bearish one), no order/position already exists for that
  POI, and the concurrency cap is not reached. Otherwise the signal is
  recorded as SKIPPED with a reason (so it is still "processed" and a restart
  never re-evaluates it).
* ``PERMISSION_LOST_ACTIONABLE`` / ``POI_TERMINAL`` -> cancel pending orders
  for that POI. Open positions are managed only by stop/target.

Levels: LONG stop = zone_bottom - stop_buffer; SHORT stop = zone_top +
stop_buffer. ``LIMIT_AT_ZONE`` enters at the proximal edge (zone_top for a
long, zone_bottom for a short); ``NEXT_OPEN`` enters at the next host bar's
open. Target = entry +/- reward_risk * risk.

Signal ids are ``SIG-`` + sha256(native event id)[:20], so the same event
can only ever produce the same signal id.
"""

from __future__ import annotations

import hashlib
from collections.abc import Sequence
from dataclasses import dataclass
from decimal import ROUND_DOWN, Decimal
from enum import StrEnum
from typing import Protocol

from botdryrun.config import BotConfig, EntryMode
from botdryrun.domain import EventView, P8EventName, ScannerBarSnapshot

__all__ = [
    "PRACTICE_POLICY_LABEL",
    "BrokerView",
    "CancelRequest",
    "FixedFractionalRiskPolicy",
    "PolicyActions",
    "PracticePolicy",
    "RiskPolicy",
    "Side",
    "SignalDecision",
    "signal_id_for",
]

PRACTICE_POLICY_LABEL = "PRACTICE POLICY - not a validated strategy; no profitability claim"

#: Native P8 permission codes (``p5_wire_normalized_replay.PERMISSION_CODE``).
_BUY_BIAS = 0
_SELL_BIAS = 1


class Side(StrEnum):
    LONG = "LONG"
    SHORT = "SHORT"


def signal_id_for(event_id: str) -> str:
    return "SIG-" + hashlib.sha256(event_id.encode("utf-8")).hexdigest()[:20]


@dataclass(frozen=True)
class SignalDecision:
    signal_id: str
    source_event_id: str
    bar_index: int
    bar_ms: int
    poi_idx: int
    poi_record_id: str
    side: Side | None
    status: str  # "ACCEPTED" | "SKIPPED"
    reason: str
    entry_mode: EntryMode
    entry_price: Decimal | None
    stop_price: Decimal | None
    target_price: Decimal | None


@dataclass(frozen=True)
class CancelRequest:
    poi_record_id: str
    reason: str


@dataclass(frozen=True)
class PolicyActions:
    signals: tuple[SignalDecision, ...]
    cancels: tuple[CancelRequest, ...]


class BrokerView(Protocol):
    def active_count(self) -> int: ...

    def has_activity_for_poi(self, poi_record_id: str) -> bool: ...


class RiskPolicy(Protocol):
    @property
    def max_concurrent_positions(self) -> int: ...

    def position_size(self, balance: Decimal, entry: Decimal, stop: Decimal) -> Decimal: ...


@dataclass(frozen=True)
class FixedFractionalRiskPolicy:
    risk_fraction: Decimal
    max_positions: int
    quantity_step: Decimal = Decimal("0.001")

    @property
    def max_concurrent_positions(self) -> int:
        return self.max_positions

    def position_size(self, balance: Decimal, entry: Decimal, stop: Decimal) -> Decimal:
        risk_per_unit = abs(entry - stop)
        if risk_per_unit <= 0 or balance <= 0:
            return Decimal("0")
        raw = (balance * self.risk_fraction) / risk_per_unit
        return raw.quantize(self.quantity_step, rounding=ROUND_DOWN)


class PracticePolicy:
    label = PRACTICE_POLICY_LABEL

    def __init__(self, config: BotConfig, risk: RiskPolicy) -> None:
        self._config = config
        self._risk = risk

    def on_events(
        self,
        events: Sequence[EventView],
        snapshot: ScannerBarSnapshot,
        broker: BrokerView,
    ) -> PolicyActions:
        signals: list[SignalDecision] = []
        cancels: list[CancelRequest] = []
        accepted_this_bar: set[str] = set()
        for event in events:
            if event.event_type in (
                P8EventName.PERMISSION_LOST_ACTIONABLE.value,
                P8EventName.POI_TERMINAL.value,
            ):
                cancels.append(CancelRequest(event.poi_record_id, event.event_type))
                continue
            if event.event_type != P8EventName.PERMISSION_ENTERED_ACTIONABLE.value:
                continue
            signals.append(
                self._entry(event, snapshot, broker, accepted_this_bar)
            )
        return PolicyActions(tuple(signals), tuple(cancels))

    def _entry(
        self,
        event: EventView,
        snapshot: ScannerBarSnapshot,
        broker: BrokerView,
        accepted_this_bar: set[str],
    ) -> SignalDecision:
        cfg = self._config

        def skipped(reason: str, side: Side | None = None) -> SignalDecision:
            return SignalDecision(
                signal_id=signal_id_for(event.event_id),
                source_event_id=event.event_id,
                bar_index=snapshot.bar_index,
                bar_ms=snapshot.bar_ms,
                poi_idx=event.poi_idx,
                poi_record_id=event.poi_record_id,
                side=side,
                status="SKIPPED",
                reason=reason,
                entry_mode=cfg.entry_mode,
                entry_price=None,
                stop_price=None,
                target_price=None,
            )

        poi = snapshot.poi_by_idx().get(event.poi_idx)
        if poi is None:
            return skipped("POI_NOT_IN_SNAPSHOT")
        side = Side.LONG if poi.direction == "BULLISH" else Side.SHORT
        if poi.fresh_active is not True:
            return skipped("POI_NOT_FRESH", side)
        expected_code = _BUY_BIAS if side is Side.LONG else _SELL_BIAS
        if event.permission != expected_code:
            return skipped("PERMISSION_DIRECTION_MISMATCH", side)
        if poi.record_id in accepted_this_bar or broker.has_activity_for_poi(poi.record_id):
            return skipped("ALREADY_ACTIVE_FOR_POI", side)
        if broker.active_count() + len(accepted_this_bar) >= self._risk.max_concurrent_positions:
            return skipped("MAX_CONCURRENT_POSITIONS", side)

        if side is Side.LONG:
            stop = poi.zone_bottom - cfg.stop_buffer
            limit = poi.zone_top
        else:
            stop = poi.zone_top + cfg.stop_buffer
            limit = poi.zone_bottom
        entry: Decimal | None
        target: Decimal | None
        if cfg.entry_mode is EntryMode.LIMIT_AT_ZONE:
            risk = abs(limit - stop)
            if risk <= 0:
                return skipped("ZERO_RISK_ZONE", side)
            entry = limit
            target = limit + cfg.reward_risk * risk if side is Side.LONG else limit - cfg.reward_risk * risk
        else:
            entry = None
            target = None
        accepted_this_bar.add(poi.record_id)
        return SignalDecision(
            signal_id=signal_id_for(event.event_id),
            source_event_id=event.event_id,
            bar_index=snapshot.bar_index,
            bar_ms=snapshot.bar_ms,
            poi_idx=event.poi_idx,
            poi_record_id=poi.record_id,
            side=side,
            status="ACCEPTED",
            reason="PERMISSION_ENTERED_ACTIONABLE",
            entry_mode=cfg.entry_mode,
            entry_price=entry,
            stop_price=stop,
            target_price=target,
        )
