"""Paper broker — simulated execution only.

DETERMINISTIC FILL MODEL (documented here, asserted in tests/bot)
-----------------------------------------------------------------
Everything is evaluated on CONFIRMED host bars, in this order per bar N:

1. Positions opened on an EARLIER bar are checked against bar N:
   * LONG: open <= stop -> exit at open (``STOP_GAP``); otherwise
     low <= stop -> exit at stop (``STOP``); otherwise open >= target -> exit
     at target (``TARGET_GAP``, never credited better than target);
     otherwise high >= target -> exit at target (``TARGET``). If the stop and
     the target are both inside bar N's range, the STOP is assumed to have
     traded first (conservative). SHORT is the mirror image.
2. Pending orders created on bar N-1 or earlier (never the bar that created
   them) are evaluated against bar N, oldest first:
   * ``NEXT_OPEN``: fills at bar N's open; target is derived from that fill.
   * ``LIMIT_AT_ZONE``: a LONG fills if low <= limit, at the limit, or at the
     open if the bar opened through the limit (SHORT mirrored).
   * a fill at or beyond the stop is REJECTED (``ENTRY_BEYOND_STOP``);
     quantity comes from the ``RiskPolicy`` using the balance at fill time
     (``SIZE_ZERO`` -> rejected); the concurrency cap is re-checked.
   * On the fill bar only the STOP is evaluated (low <= stop for a long) —
     for a limit fill we cannot know whether the target traded before the
     fill, so it is never credited on the fill bar. For ``NEXT_OPEN`` the
     whole bar is after the fill, so stop and target are both evaluated
     (stop first).
3. After the bar's P8 events: cancels (``PERMISSION_LOST_ACTIONABLE`` /
   ``POI_TERMINAL``), new orders, then expiry of pending orders that have had
   ``pending_expiry_bars`` bars to fill.

Costs: ``slippage`` (price units, applied adversely to every fill and exit)
and ``commission_per_unit`` (per side) both DEFAULT TO 0 and are disclosed in
every journal header. PnL = price difference x quantity (1 unit = 1 price
point), rounded to 0.01 (ROUND_HALF_EVEN).
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from decimal import ROUND_HALF_EVEN, Decimal

from botdryrun.config import BotConfig, EntryMode
from botdryrun.policy import RiskPolicy, Side, SignalDecision
from btmm_ai_scanner.contracts.normalized_candle import NormalizedCandle

__all__ = ["BarExecution", "LedgerEntry", "Order", "PaperBroker", "Position"]

_CENT = Decimal("0.01")


def _money(value: Decimal) -> Decimal:
    return value.quantize(_CENT, rounding=ROUND_HALF_EVEN)


@dataclass
class Order:
    order_id: str
    signal_id: str
    poi_record_id: str
    poi_idx: int
    side: Side
    entry_mode: EntryMode
    limit_price: Decimal | None
    stop_price: Decimal
    target_price: Decimal | None
    created_bar_index: int
    status: str  # PENDING FILLED CANCELLED EXPIRED REJECTED
    status_bar_index: int
    reason: str


@dataclass
class Position:
    position_id: str
    order_id: str
    poi_record_id: str
    side: Side
    quantity: Decimal
    entry_price: Decimal
    entry_bar_index: int
    stop_price: Decimal
    target_price: Decimal
    status: str  # OPEN CLOSED
    exit_price: Decimal | None = None
    exit_bar_index: int | None = None
    exit_reason: str | None = None
    realized_pnl: Decimal | None = None


@dataclass(frozen=True)
class LedgerEntry:
    seq: int
    bar_index: int
    kind: str
    ref_id: str
    amount: Decimal
    balance_after: Decimal


@dataclass
class BarExecution:
    fills: int = 0
    exits: int = 0
    rejects: int = 0
    cancels: int = 0
    expired: int = 0


class PaperBroker:
    def __init__(
        self,
        config: BotConfig,
        risk: RiskPolicy,
        *,
        orders: Iterable[Order] = (),
        positions: Iterable[Position] = (),
        ledger: Iterable[LedgerEntry] = (),
    ) -> None:
        self._config = config
        self._risk = risk
        self.orders: dict[str, Order] = {o.order_id: o for o in orders}
        self.positions: dict[str, Position] = {p.position_id: p for p in positions}
        self.ledger: list[LedgerEntry] = sorted(ledger, key=lambda e: e.seq)
        self.balance: Decimal = (
            self.ledger[-1].balance_after if self.ledger else config.initial_balance
        )
        self.dirty_orders: set[str] = set()
        self.dirty_positions: set[str] = set()
        self.new_ledger: list[LedgerEntry] = []

    # ---------------------------------------------------------------- views
    def active_count(self) -> int:
        return sum(1 for o in self.orders.values() if o.status == "PENDING") + sum(
            1 for p in self.positions.values() if p.status == "OPEN"
        )

    def has_activity_for_poi(self, poi_record_id: str) -> bool:
        return any(
            o.poi_record_id == poi_record_id and o.status == "PENDING"
            for o in self.orders.values()
        ) or any(
            p.poi_record_id == poi_record_id and p.status == "OPEN"
            for p in self.positions.values()
        )

    def open_positions(self) -> list[Position]:
        return sorted(
            (p for p in self.positions.values() if p.status == "OPEN"),
            key=lambda p: (p.entry_bar_index, p.position_id),
        )

    def pending_orders(self) -> list[Order]:
        return sorted(
            (o for o in self.orders.values() if o.status == "PENDING"),
            key=lambda o: (o.created_bar_index, o.order_id),
        )

    def equity(self, mark: Decimal) -> Decimal:
        unrealized = Decimal("0")
        for p in self.open_positions():
            diff = mark - p.entry_price if p.side is Side.LONG else p.entry_price - mark
            unrealized += diff * p.quantity
        return _money(self.balance + unrealized)

    def begin_bar(self) -> None:
        self.dirty_orders.clear()
        self.dirty_positions.clear()
        self.new_ledger = []

    # ------------------------------------------------------------ internals
    def _post(self, bar_index: int, kind: str, ref_id: str, amount: Decimal) -> None:
        amount = _money(amount)
        self.balance = _money(self.balance + amount)
        seq = (self.ledger[-1].seq + 1) if self.ledger else 1
        entry = LedgerEntry(seq, bar_index, kind, ref_id, amount, self.balance)
        self.ledger.append(entry)
        self.new_ledger.append(entry)

    def _adverse(self, price: Decimal, side: Side, entering: bool) -> Decimal:
        slip = self._config.slippage
        buying = (side is Side.LONG) == entering
        return price + slip if buying else price - slip

    def _close(self, p: Position, bar_index: int, price: Decimal, reason: str) -> None:
        exit_price = self._adverse(price, p.side, entering=False)
        diff = exit_price - p.entry_price if p.side is Side.LONG else p.entry_price - exit_price
        pnl = _money(diff * p.quantity)
        p.status = "CLOSED"
        p.exit_price = exit_price
        p.exit_bar_index = bar_index
        p.exit_reason = reason
        p.realized_pnl = pnl
        self.dirty_positions.add(p.position_id)
        self._post(bar_index, "REALIZED_PNL", p.position_id, pnl)
        commission = self._config.commission_per_unit * p.quantity
        if commission > 0:
            self._post(bar_index, "COMMISSION_EXIT", p.position_id, -commission)

    def _check_exit(self, p: Position, bar: NormalizedCandle, bar_index: int, *, fill_bar_limit: bool) -> bool:
        long = p.side is Side.LONG
        if not fill_bar_limit and p.entry_bar_index != bar_index:
            if (long and bar.open <= p.stop_price) or (not long and bar.open >= p.stop_price):
                self._close(p, bar_index, bar.open, "STOP_GAP")
                return True
        stop_hit = bar.low <= p.stop_price if long else bar.high >= p.stop_price
        if stop_hit:
            self._close(p, bar_index, p.stop_price, "STOP")
            return True
        if fill_bar_limit:
            return False
        if p.entry_bar_index != bar_index:
            gap_target = bar.open >= p.target_price if long else bar.open <= p.target_price
            if gap_target:
                self._close(p, bar_index, p.target_price, "TARGET_GAP")
                return True
        target_hit = bar.high >= p.target_price if long else bar.low <= p.target_price
        if target_hit:
            self._close(p, bar_index, p.target_price, "TARGET")
            return True
        return False

    # -------------------------------------------------------------- per bar
    def process_bar(self, bar_index: int, bar: NormalizedCandle) -> BarExecution:
        result = BarExecution()
        for p in self.open_positions():
            if p.entry_bar_index < bar_index and self._check_exit(
                p, bar, bar_index, fill_bar_limit=False
            ):
                result.exits += 1

        for order in self.pending_orders():
            if order.created_bar_index >= bar_index:
                continue
            filled = self._try_fill(order, bar, bar_index, result)
            if filled is not None:
                limit_fill = order.entry_mode is EntryMode.LIMIT_AT_ZONE
                if self._check_exit(filled, bar, bar_index, fill_bar_limit=limit_fill):
                    result.exits += 1
        return result

    def _try_fill(
        self, order: Order, bar: NormalizedCandle, bar_index: int, result: BarExecution
    ) -> Position | None:
        long = order.side is Side.LONG
        if order.entry_mode is EntryMode.NEXT_OPEN:
            raw = bar.open
        else:
            assert order.limit_price is not None
            limit = order.limit_price
            touched = bar.low <= limit if long else bar.high >= limit
            if not touched:
                return None
            if long:
                raw = bar.open if bar.open <= limit else limit
            else:
                raw = bar.open if bar.open >= limit else limit
        price = self._adverse(raw, order.side, entering=True)

        def reject(reason: str) -> None:
            order.status = "REJECTED"
            order.status_bar_index = bar_index
            order.reason = reason
            self.dirty_orders.add(order.order_id)
            result.rejects += 1

        if (long and price <= order.stop_price) or (not long and price >= order.stop_price):
            reject("ENTRY_BEYOND_STOP")
            return None
        open_now = sum(1 for p in self.positions.values() if p.status == "OPEN")
        if open_now >= self._risk.max_concurrent_positions:
            reject("MAX_CONCURRENT_AT_FILL")
            return None
        quantity = self._risk.position_size(self.balance, price, order.stop_price)
        if quantity <= 0:
            reject("SIZE_ZERO")
            return None
        risk = abs(price - order.stop_price)
        if order.target_price is not None:
            target = order.target_price
        else:
            target = price + self._config.reward_risk * risk if long else price - self._config.reward_risk * risk
        order.status = "FILLED"
        order.status_bar_index = bar_index
        order.reason = "FILLED"
        self.dirty_orders.add(order.order_id)
        position = Position(
            position_id=order.order_id,
            order_id=order.order_id,
            poi_record_id=order.poi_record_id,
            side=order.side,
            quantity=quantity,
            entry_price=price,
            entry_bar_index=bar_index,
            stop_price=order.stop_price,
            target_price=target,
            status="OPEN",
        )
        self.positions[position.position_id] = position
        self.dirty_positions.add(position.position_id)
        commission = self._config.commission_per_unit * quantity
        if commission > 0:
            self._post(bar_index, "COMMISSION_ENTRY", position.position_id, -commission)
        result.fills += 1
        return position

    # ------------------------------------------------------ policy actions
    def place(self, signal: SignalDecision) -> None:
        if signal.status != "ACCEPTED" or signal.side is None or signal.stop_price is None:
            return
        if signal.signal_id in self.orders:
            # Deterministic ids: the same signal can never become two orders.
            return
        self.orders[signal.signal_id] = Order(
            order_id=signal.signal_id,
            signal_id=signal.signal_id,
            poi_record_id=signal.poi_record_id,
            poi_idx=signal.poi_idx,
            side=signal.side,
            entry_mode=signal.entry_mode,
            limit_price=signal.entry_price,
            stop_price=signal.stop_price,
            target_price=signal.target_price,
            created_bar_index=signal.bar_index,
            status="PENDING",
            status_bar_index=signal.bar_index,
            reason="PLACED",
        )
        self.dirty_orders.add(signal.signal_id)

    def cancel_for_poi(self, poi_record_id: str, reason: str, bar_index: int) -> int:
        count = 0
        for order in self.pending_orders():
            if order.poi_record_id == poi_record_id:
                order.status = "CANCELLED"
                order.status_bar_index = bar_index
                order.reason = reason
                self.dirty_orders.add(order.order_id)
                count += 1
        return count

    def expire(self, bar_index: int) -> int:
        count = 0
        for order in self.pending_orders():
            if bar_index - order.created_bar_index >= self._config.pending_expiry_bars:
                order.status = "EXPIRED"
                order.status_bar_index = bar_index
                order.reason = "EXPIRED"
                self.dirty_orders.add(order.order_id)
                count += 1
        return count
