"""Market-data adapter: loads candles and validates the stream the bot sees.

Responsibilities (and nothing else — no scanner rule lives here):

* load FXCM CSV candles per timeframe as ``NormalizedCandle`` through the
  repository's own loaders (``load_level_a_window`` for the SHA-verified
  FXCM files, ``load_v1a_csv`` for an unverified directory of fixtures);
* present them as an ARRIVAL-ORDERED stream of ``FeedItem`` s and validate it:

  - host bar with the same open time and identical OHLCV as one already
    accepted -> ignored idempotently (counted, INFO incident);
  - same open time, different OHLCV -> ``ConflictingDuplicateBarError``
    (CRITICAL; the run stops at that point);
  - open time earlier than the last accepted host bar ->
    ``OutOfOrderBarError`` (CRITICAL; the run stops at that point);
  - open time later than the next FXCM session slot -> ``MISSING_BARS``
    incident; ``GapPolicy.HALT`` stops the run before that bar,
    ``GapPolicy.CONTINUE`` records it and goes on. The known session breaks
    (Mon-Thu 21:00->22:00 UTC, Friday 20:45 UTC -> Sunday 22:00 UTC) are not
    gaps;
  - a context (higher/lower-TF) candle that ARRIVES after a host bar whose
    availability is at or beyond its own availability is ``LATE``: the host
    bar was already processed without it, so it is rejected (WARNING
    incident) rather than retro-actively changing history;
  - a context candle that arrives EARLY is held back: it is released to the
    bot's input ledger only with the first host bar whose availability
    reaches its own. (The scanner core also enforces availability ordering;
    this adapter never weakens it.)

* refuse any window whose host bars intersect the sealed out-of-sample
  range (constants imported from ``rc3_daily_authority``).
"""

from __future__ import annotations

import bisect
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime, time, timedelta
from enum import StrEnum
from pathlib import Path

from botdryrun.config import BotConfig, DataSourceKind, GapPolicy
from btmm_ai_scanner.config.enums import Timeframe
from btmm_ai_scanner.contracts.normalized_candle import NormalizedCandle
from tests.parity_support.rc3_daily_authority import (
    SEALED_FIRST_EVENT_UTC,
    SEALED_LAST_EVENT_UTC,
    load_level_a_window,
)
from tests.parity_support.v1a_csv_loader import load_v1a_csv

__all__ = [
    "TIMEFRAME_DURATION",
    "ConflictingDuplicateBarError",
    "FeedIntegrityError",
    "FeedItem",
    "FeedKind",
    "FxcmSessionCalendar",
    "Incident",
    "OutOfOrderBarError",
    "SealedRangeRefusedError",
    "Severity",
    "ValidatedFeed",
    "assemble_feed",
    "assert_outside_sealed_range",
    "assert_window_outside_sealed_range",
    "candle_fingerprint",
    "interleave",
    "load_feed_items",
]

TIMEFRAME_DURATION: dict[Timeframe, timedelta] = {
    Timeframe.M1: timedelta(minutes=1),
    Timeframe.M5: timedelta(minutes=5),
    Timeframe.M15: timedelta(minutes=15),
    Timeframe.H1: timedelta(hours=1),
    Timeframe.H3: timedelta(hours=3),
    Timeframe.H4: timedelta(hours=4),
    Timeframe.D1: timedelta(days=1),
    Timeframe.W1: timedelta(days=7),
}

#: Presentation/ordering only (coarse to fine).
_TF_ORDER: dict[Timeframe, int] = {
    Timeframe.W1: 0,
    Timeframe.D1: 1,
    Timeframe.H4: 2,
    Timeframe.H3: 3,
    Timeframe.H1: 4,
    Timeframe.M15: 5,
    Timeframe.M5: 6,
    Timeframe.M1: 7,
}


class FeedIntegrityError(RuntimeError):
    """The input stream is not trustworthy past this point."""


class ConflictingDuplicateBarError(FeedIntegrityError):
    pass


class OutOfOrderBarError(FeedIntegrityError):
    pass


class SealedRangeRefusedError(AssertionError):
    """A host bar would fall inside the sealed out-of-sample range."""


class FeedKind(StrEnum):
    HOST = "HOST"
    CONTEXT = "CONTEXT"


class Severity(StrEnum):
    INFO = "INFO"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"


@dataclass(frozen=True)
class FeedItem:
    kind: FeedKind
    candle: NormalizedCandle

    @property
    def timeframe(self) -> Timeframe:
        return self.candle.timeframe


def _ms(value: datetime) -> int:
    return int(value.timestamp() * 1000)


@dataclass(frozen=True)
class Incident:
    kind: str
    severity: Severity
    timeframe: str
    event_utc: str
    detail: str

    @property
    def incident_id(self) -> str:
        return f"{self.kind}:{self.timeframe}:{self.event_utc}"


def candle_fingerprint(candle: NormalizedCandle) -> str:
    """Market-content identity of a bar (OHLCV + times + timeframe)."""
    return (
        f"{candle.timeframe.value}|{candle.event_time_utc.isoformat()}|"
        f"{candle.availability_time_utc.isoformat()}|{candle.open}|{candle.high}|"
        f"{candle.low}|{candle.close}|{candle.volume}"
    )


# ---------------------------------------------------------------------------
# Sealed range
# ---------------------------------------------------------------------------


def assert_window_outside_sealed_range(start_utc: datetime, end_utc: datetime) -> None:
    if start_utc <= SEALED_LAST_EVENT_UTC and end_utc >= SEALED_FIRST_EVENT_UTC:
        raise SealedRangeRefusedError(
            "refusing a replay window that intersects the sealed out-of-sample range"
        )


def assert_outside_sealed_range(candles: Iterable[NormalizedCandle]) -> None:
    for candle in candles:
        if SEALED_FIRST_EVENT_UTC <= candle.event_time_utc <= SEALED_LAST_EVENT_UTC:
            raise SealedRangeRefusedError(
                "refusing to replay a host bar inside the sealed out-of-sample range"
            )


# ---------------------------------------------------------------------------
# Session calendar
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class FxcmSessionCalendar:
    """FXCM XAUUSD session slots (UTC), as observed in the acquired feed.

    Sessions open 22:00 UTC. Mon-Thu the last bar CLOSES at 21:00 UTC; Friday
    the last bar closes at 20:45 UTC and the market reopens Sunday 22:00 UTC.
    Exchange holidays are NOT modelled: a holiday shows up as a
    ``MISSING_BARS`` incident, which is the honest outcome.
    """

    step: timedelta
    session_open: time = time(22, 0)
    weekday_close: time = time(21, 0)
    friday_close: time = time(20, 45)

    def _at(self, day: datetime, clock: time) -> datetime:
        return datetime(day.year, day.month, day.day, clock.hour, clock.minute, tzinfo=UTC)

    def is_slot(self, t: datetime) -> bool:
        weekday = t.weekday()  # Mon=0 .. Sun=6
        end = t + self.step
        if weekday == 5:
            return False
        if weekday == 6:
            return t >= self._at(t, self.session_open)
        if t >= self._at(t, self.session_open):
            return weekday != 4  # Friday evening is closed
        close = self.friday_close if weekday == 4 else self.weekday_close
        return end <= self._at(t, close)

    def next_slot(self, t: datetime) -> datetime:
        candidate = t + self.step
        for _ in range(10_000):
            if self.is_slot(candidate):
                return candidate
            weekday = candidate.weekday()
            opening = self._at(candidate, self.session_open)
            if weekday in (0, 1, 2, 3) and candidate < opening:
                candidate = opening
            elif weekday == 6 and candidate < opening:
                candidate = opening
            else:
                days_to_sunday = (6 - weekday) % 7 or 7
                candidate = self._at(candidate + timedelta(days=days_to_sunday), self.session_open)
        raise RuntimeError("session calendar did not converge")  # pragma: no cover

    def missing_slots_between(self, previous: datetime, current: datetime) -> int:
        count = 0
        slot = self.next_slot(previous)
        while slot < current:
            count += 1
            slot = self.next_slot(slot)
            if count > 100_000:  # pragma: no cover
                break
        return count


# ---------------------------------------------------------------------------
# Stream validation
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ValidatedFeed:
    host_timeframe: Timeframe
    host: tuple[NormalizedCandle, ...]
    context: dict[Timeframe, tuple[NormalizedCandle, ...]]
    #: (timeframe, event_ms) -> host bar index the candle is released with;
    #: -1 = pre-window warm-up; absent = never released inside this feed.
    release_index: dict[tuple[str, int], int]
    incidents: tuple[Incident, ...]
    fatal: FeedIntegrityError | None
    halted_on_gap: bool
    duplicates_ignored: int = 0
    late_context_rejected: int = 0
    notes: tuple[str, ...] = field(default_factory=tuple)

    def released_context(self, through_bar_index: int) -> dict[Timeframe, tuple[NormalizedCandle, ...]]:
        out: dict[Timeframe, tuple[NormalizedCandle, ...]] = {}
        for timeframe, candles in self.context.items():
            kept = tuple(
                c
                for c in candles
                if self.release_index.get((timeframe.value, _ms(c.event_time_utc)), 1 << 62)
                <= through_bar_index
            )
            out[timeframe] = kept
        return out


class _SeriesValidator:
    def __init__(self, timeframe: Timeframe) -> None:
        self.timeframe = timeframe
        self.accepted: list[NormalizedCandle] = []
        self._by_time: dict[datetime, str] = {}

    def offer(self, candle: NormalizedCandle) -> bool:
        """True = accepted, False = identical duplicate ignored. Raises on
        conflicting duplicates and out-of-order bars."""
        if candle.timeframe is not self.timeframe:
            raise FeedIntegrityError(
                f"candle timeframe {candle.timeframe} offered to the {self.timeframe} series"
            )
        known = self._by_time.get(candle.event_time_utc)
        if known is not None:
            if known == candle_fingerprint(candle):
                return False
            raise ConflictingDuplicateBarError(
                f"{self.timeframe.value} bar {candle.event_time_utc.isoformat()} was "
                "delivered twice with different OHLCV"
            )
        if self.accepted and candle.event_time_utc < self.accepted[-1].event_time_utc:
            raise OutOfOrderBarError(
                f"{self.timeframe.value} bar {candle.event_time_utc.isoformat()} arrived "
                f"after {self.accepted[-1].event_time_utc.isoformat()}"
            )
        self.accepted.append(candle)
        self._by_time[candle.event_time_utc] = candle_fingerprint(candle)
        return True


def assemble_feed(
    items: Iterable[FeedItem],
    *,
    host_timeframe: Timeframe,
    gap_policy: GapPolicy,
    calendar: FxcmSessionCalendar | None = None,
) -> ValidatedFeed:
    calendar = calendar or FxcmSessionCalendar(step=TIMEFRAME_DURATION[host_timeframe])
    host = _SeriesValidator(host_timeframe)
    context: dict[Timeframe, _SeriesValidator] = {}
    incidents: list[Incident] = []
    fatal: FeedIntegrityError | None = None
    halted = False
    duplicates = 0
    late = 0
    watermark: datetime | None = None

    for item in items:
        candle = item.candle
        tf = candle.timeframe.value
        event = candle.event_time_utc.isoformat()
        if item.kind is FeedKind.HOST:
            previous = host.accepted[-1] if host.accepted else None
            try:
                accepted = host.offer(candle)
            except FeedIntegrityError as exc:
                incidents.append(
                    Incident(type(exc).__name__, Severity.CRITICAL, tf, event, str(exc))
                )
                fatal = exc
                break
            if not accepted:
                duplicates += 1
                incidents.append(
                    Incident(
                        "DUPLICATE_BAR_IGNORED",
                        Severity.INFO,
                        tf,
                        event,
                        "identical duplicate host bar ignored",
                    )
                )
                continue
            if previous is not None:
                missing = calendar.missing_slots_between(
                    previous.event_time_utc, candle.event_time_utc
                )
                if missing > 0:
                    incidents.append(
                        Incident(
                            "MISSING_BARS",
                            Severity.WARNING,
                            tf,
                            event,
                            f"{missing} session slot(s) missing after "
                            f"{previous.event_time_utc.isoformat()}; policy={gap_policy.value}",
                        )
                    )
                    if gap_policy is GapPolicy.HALT:
                        host.accepted.pop()
                        halted = True
                        break
            watermark = candle.availability_time_utc
        else:
            validator = context.setdefault(candle.timeframe, _SeriesValidator(candle.timeframe))
            if watermark is not None and candle.availability_time_utc <= watermark:
                late += 1
                incidents.append(
                    Incident(
                        "LATE_CONTEXT_CANDLE",
                        Severity.WARNING,
                        tf,
                        event,
                        "context candle arrived after a host bar at/after its "
                        "availability had been accepted; rejected",
                    )
                )
                continue
            try:
                accepted = validator.offer(candle)
            except FeedIntegrityError as exc:
                incidents.append(
                    Incident(type(exc).__name__, Severity.CRITICAL, tf, event, str(exc))
                )
                fatal = exc
                break
            if not accepted:
                duplicates += 1
                incidents.append(
                    Incident(
                        "DUPLICATE_BAR_IGNORED",
                        Severity.INFO,
                        tf,
                        event,
                        "identical duplicate context candle ignored",
                    )
                )

    host_series = tuple(host.accepted)
    assert_outside_sealed_range(host_series)
    availabilities = [c.availability_time_utc for c in host_series]
    release: dict[tuple[str, int], int] = {}
    context_series: dict[Timeframe, tuple[NormalizedCandle, ...]] = {}
    for timeframe in sorted(context, key=lambda t: _TF_ORDER[t]):
        candles = tuple(sorted(context[timeframe].accepted, key=lambda c: c.availability_time_utc))
        context_series[timeframe] = candles
        for c in candles:
            if availabilities and c.availability_time_utc < availabilities[0]:
                release[(timeframe.value, _ms(c.event_time_utc))] = -1
                continue
            index = bisect.bisect_left(availabilities, c.availability_time_utc)
            if index < len(availabilities):
                release[(timeframe.value, _ms(c.event_time_utc))] = index
    # Deterministic, de-duplicated incident order (arrival order, first wins).
    seen: set[str] = set()
    unique: list[Incident] = []
    for incident in incidents:
        if incident.incident_id not in seen:
            seen.add(incident.incident_id)
            unique.append(incident)
    return ValidatedFeed(
        host_timeframe=host_timeframe,
        host=host_series,
        context=context_series,
        release_index=release,
        incidents=tuple(unique),
        fatal=fatal,
        halted_on_gap=halted,
        duplicates_ignored=duplicates,
        late_context_rejected=late,
    )


# ---------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------


def interleave(
    host: Sequence[NormalizedCandle],
    context: dict[Timeframe, Sequence[NormalizedCandle]],
) -> list[FeedItem]:
    """Arrival order for a historical replay: by availability; at equal
    availability a context candle arrives BEFORE the host bar (it closed at
    the same instant, so it is on time for that bar)."""
    rows: list[tuple[datetime, int, int, datetime, FeedItem]] = []
    for c in host:
        rows.append((c.availability_time_utc, 1, _TF_ORDER[c.timeframe], c.event_time_utc, FeedItem(FeedKind.HOST, c)))
    for candles in context.values():
        for c in candles:
            rows.append((c.availability_time_utc, 0, _TF_ORDER[c.timeframe], c.event_time_utc, FeedItem(FeedKind.CONTEXT, c)))
    rows.sort(key=lambda r: (r[0], r[1], r[2], r[3]))
    return [r[4] for r in rows]


def _load_csv_dir(config: BotConfig) -> list[FeedItem]:
    root = Path(config.dataset_root)
    host_tf = Timeframe(config.host_timeframe)
    all_host = load_v1a_csv(root / f"{host_tf.value}.csv", host_tf)
    host = [
        c for c in all_host if config.window_start_utc <= c.event_time_utc <= config.window_end_utc
    ]
    if not host:
        raise ValueError("the requested window contains no host bars")
    last_availability = host[-1].availability_time_utc
    context: dict[Timeframe, Sequence[NormalizedCandle]] = {}
    for name in config.context_timeframes:
        tf = Timeframe(name)
        path = root / f"{tf.value}.csv"
        if not path.is_file():
            continue
        loaded = [c for c in load_v1a_csv(path, tf) if c.availability_time_utc <= last_availability]
        pre = [c for c in loaded if c.event_time_utc < config.window_start_utc]
        during = [c for c in loaded if c.event_time_utc >= config.window_start_utc]
        capped = pre[-config.context_lookback_bars :] if config.context_lookback_bars > 0 else []
        context[tf] = capped + during
    return interleave(host, context)


def load_feed_items(config: BotConfig) -> list[FeedItem]:
    assert_window_outside_sealed_range(config.window_start_utc, config.window_end_utc)
    if config.data_source is DataSourceKind.CSV_DIR:
        return _load_csv_dir(config)
    window = load_level_a_window(
        Path(config.dataset_root),
        window_start_event_utc=config.window_start_utc,
        window_end_event_utc=config.window_end_utc,
        host_timeframe=Timeframe(config.host_timeframe),
        context_timeframes=tuple(Timeframe(t) for t in config.context_timeframes),
        context_lookback_bars=config.context_lookback_bars,
    )
    assert_outside_sealed_range(window.host_series)
    return interleave(window.host_series, dict(window.context_series))
