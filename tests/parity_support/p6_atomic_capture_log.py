"""Strict parser for the P6 atomic snapshot and its digest-locked raw captures.

Test/parity tooling only — nothing in `src/` imports this, and it changes no
production semantics.

WHAT IT REFUSES, AND WHY THAT IS THE POINT
-------------------------------------------
The capture is deliberately split: one execution produces the semantic snapshot
(five surface digests plus an INPUT digest per timeframe), and six later
executions each export one timeframe's raw candles. Splitting it is what keeps
each run inside the log volume the feasibility probe actually demonstrated, but
it opens a failure mode that looks exactly like success — the 1250-bar window
slides forward as new bars confirm, so a raw export taken minutes after the
snapshot can cover a DIFFERENT window while being perfectly well-formed.

So this module refuses rather than repairs. A malformed, incomplete, misordered
or mis-provendered capture raises; it is never silently patched, defaulted or
truncated to fit. Anything that parses is then still subject to the five-
dimension identity lock before it may reach the oracle.

THE FIVE-DIMENSION LOCK
-----------------------
A raw capture is accepted only when row count, first timestamp, last timestamp
and BOTH digests match the snapshot. Each dimension earns its place:

* digests alone would not say WHERE a capture diverged, so a mismatch would cost
  a re-derivation rather than a glance;
* row count alone is famously insufficient — a window shifted forward by one bar
  has exactly the same count;
* first and last timestamps localise a shift immediately, and are what turn
  "these differ" into "the window moved forward one bar".

Output equality is never consulted. A prefix can converge closely enough to
produce identical discrete output while being the wrong data, which is precisely
what the M15 truncation experiment measured.

CAPTURE IDENTITY
----------------
There is no serial "capture id" shared between the snapshot and the raw runs,
because they are separate executions and any id minted in one could only be
copied into the other by hand. The binding is cryptographic instead: a raw
capture belongs to a snapshot exactly when its INPUT digest matches. The derived
`capture_id` below names a snapshot for the record; it is not the lock.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from typing import Any

#: Timeframes the snapshot must carry, in authority order.
REQUIRED_TIMEFRAMES: tuple[str, ...] = ("W1", "D1", "H4", "H1", "M15", "M5")

#: Pine `syminfo.prefix` for FX:XAUUSD. Any other feed is rejected outright:
#: this campaign has already had one silent switch to OANDA.
REQUIRED_PROVIDER = "FX"
REQUIRED_TICKER = "XAUUSD"

#: Surfaces and the log key prefix each pair of hashes uses.
SURFACE_KEYS: dict[str, str] = {
    "SWINGS": "SW",
    "EQUAL": "EQ",
    "DISP": "DS",
    "P2_TRANS": "TR",
    "P2_STATE": "ST",
}

_LOG_PREFIX = re.compile(r"^.*?(?=P6META\||P6SNAP\||P6SNAP_END\||P6RAW\||P6RAW_SUMMARY\|)")


class CaptureError(ValueError):
    """A capture is malformed, incomplete, or from the wrong feed."""


def _strip(line: str) -> str:
    """Remove TradingView's `[timestamp]: ` prefix, leaving the record."""
    return _LOG_PREFIX.sub("", line.strip(), count=1)


def _decode(value: int) -> int:
    """Inverse of the canonical encoding: `2v+2` for v>=0, `-2v+1` for v<0."""
    if value == 0:
        raise ValueError("0 encodes `na`, which is not a valid price")
    return (value - 2) // 2 if value % 2 == 0 else -((value - 1) // 2)


def _fields(body: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for part in body.split("|"):
        if "=" in part:
            key, _, value = part.partition("=")
            if key in out:
                raise CaptureError(f"duplicate field {key!r}")
            out[key] = value
    return out


def _require_int(values: dict[str, str], key: str, *, record: str) -> int:
    if key not in values:
        raise CaptureError(f"{record}: missing field {key!r}")
    raw = values[key]
    try:
        return int(raw)
    except ValueError as exc:
        raise CaptureError(f"{record}: field {key!r} is not an integer: {raw!r}") from exc


@dataclass(frozen=True)
class SnapshotMeta:
    schema: int
    provider: str
    ticker: str
    host_timeframe: str
    anchor_time: int
    anchor_close: int
    host_dataset: int
    host_confirmed: int
    semantic_minimum: int
    request_envelope: int
    host_envelope: int
    capture_timeframe: str
    alias_hits: int

    @property
    def feed(self) -> str:
        return f"{self.provider}:{self.ticker}"


@dataclass(frozen=True)
class TimeframeSnapshot:
    timeframe: str
    tf_code: int
    semantic_rows: int
    semantic_first_time: int
    semantic_last_time: int
    semantic_input_h1: int
    semantic_input_h2: int
    swing_count: int
    equal_count: int
    disp_code: int
    transition_count: int
    direction: int
    surfaces: dict[str, tuple[int, int]]
    combined: tuple[int, int]

    def identity(self) -> dict[str, int]:
        """The five dimensions a raw capture must reproduce."""
        return {
            "semantic_rows": self.semantic_rows,
            "semantic_first_time": self.semantic_first_time,
            "semantic_last_time": self.semantic_last_time,
            "semantic_input_h1": self.semantic_input_h1,
            "semantic_input_h2": self.semantic_input_h2,
        }


@dataclass(frozen=True)
class Snapshot:
    meta: SnapshotMeta
    timeframes: dict[str, TimeframeSnapshot]

    @property
    def capture_id(self) -> str:
        """Derived name for this snapshot. NOT the lock -- see module docstring."""
        parts = [
            self.meta.provider,
            self.meta.ticker,
            self.meta.host_timeframe,
            str(self.meta.anchor_time),
        ]
        for timeframe in REQUIRED_TIMEFRAMES:
            snap = self.timeframes[timeframe]
            parts += [timeframe, str(snap.semantic_input_h1), str(snap.semantic_input_h2)]
        return hashlib.sha256("|".join(parts).encode()).hexdigest()[:32]


@dataclass(frozen=True)
class RawCapture:
    timeframe: str
    bars: tuple[dict[str, Any], ...]
    rows: int
    first_time: int
    last_time: int
    h1: int
    h2: int
    provider: str
    ticker: str

    @property
    def identity(self) -> dict[str, int]:
        return {
            "semantic_rows": self.rows,
            "semantic_first_time": self.first_time,
            "semantic_last_time": self.last_time,
            "semantic_input_h1": self.h1,
            "semantic_input_h2": self.h2,
        }


# ---------------------------------------------------------------------------
# Snapshot
# ---------------------------------------------------------------------------


def parse_snapshot(text: str, *, require_feed: bool = True) -> Snapshot:
    meta: SnapshotMeta | None = None
    meta_line: str | None = None
    timeframes: dict[str, TimeframeSnapshot] = {}
    tf_lines: dict[str, str] = {}
    saw_end = False

    for raw_line in text.splitlines():
        line = _strip(raw_line)
        if line.startswith("P6META|"):
            if meta is not None:
                # Pine re-executes the realtime bar on every tick and rolls back
                # `var` state, so a once-guard cannot stop a repeat emission. An
                # IDENTICAL repeat is the same observation; a DIFFERING one means
                # two runs were mixed, which is the thing worth refusing.
                if line == meta_line:
                    continue
                raise CaptureError(
                    "two DIFFERENT P6META records: captures from separate runs "
                    "were mixed"
                )
            meta_line = line
            values = _fields(line)
            meta = SnapshotMeta(
                schema=_require_int(values, "schema", record="P6META"),
                provider=values.get("provider", ""),
                ticker=values.get("ticker", ""),
                host_timeframe=values.get("hostTf", ""),
                anchor_time=_require_int(values, "anchorTime", record="P6META"),
                anchor_close=_require_int(values, "anchorClose", record="P6META"),
                host_dataset=_require_int(values, "hostDataset", record="P6META"),
                host_confirmed=_require_int(values, "hostConfirmed", record="P6META"),
                semantic_minimum=_require_int(values, "semanticMin", record="P6META"),
                request_envelope=_require_int(
                    values, "requestEnvelope", record="P6META"
                ),
                host_envelope=_require_int(values, "hostEnvelope", record="P6META"),
                capture_timeframe=values.get("captureTf", ""),
                alias_hits=_require_int(values, "aliasHits", record="P6META"),
            )
        elif line.startswith("P6SNAP|"):
            if meta is None:
                raise CaptureError("P6SNAP before P6META")
            body = line.split("|", 2)
            if len(body) < 3:
                raise CaptureError(f"malformed P6SNAP: {line[:80]!r}")
            timeframe = body[1]
            if timeframe not in REQUIRED_TIMEFRAMES:
                raise CaptureError(f"unknown timeframe in snapshot: {timeframe!r}")
            if timeframe in timeframes:
                if line == tf_lines[timeframe]:
                    continue  # identical repeat -- see the P6META note above
                raise CaptureError(
                    f"two DIFFERENT {timeframe} records: captures from separate "
                    f"runs were mixed"
                )
            tf_lines[timeframe] = line
            values = _fields(line)
            surfaces = {}
            for surface, key in SURFACE_KEYS.items():
                surfaces[surface] = (
                    _require_int(values, f"{key}1", record=f"P6SNAP {timeframe}"),
                    _require_int(values, f"{key}2", record=f"P6SNAP {timeframe}"),
                )
            timeframes[timeframe] = TimeframeSnapshot(
                timeframe=timeframe,
                tf_code=_require_int(values, "code", record=f"P6SNAP {timeframe}"),
                semantic_rows=_require_int(values, "rows", record=f"P6SNAP {timeframe}"),
                semantic_first_time=_require_int(
                    values, "first", record=f"P6SNAP {timeframe}"
                ),
                semantic_last_time=_require_int(
                    values, "last", record=f"P6SNAP {timeframe}"
                ),
                semantic_input_h1=_require_int(
                    values, "ih1", record=f"P6SNAP {timeframe}"
                ),
                semantic_input_h2=_require_int(
                    values, "ih2", record=f"P6SNAP {timeframe}"
                ),
                swing_count=_require_int(values, "swings", record=f"P6SNAP {timeframe}"),
                equal_count=_require_int(values, "equal", record=f"P6SNAP {timeframe}"),
                disp_code=_require_int(values, "disp", record=f"P6SNAP {timeframe}"),
                transition_count=_require_int(
                    values, "trans", record=f"P6SNAP {timeframe}"
                ),
                direction=_require_int(values, "dir", record=f"P6SNAP {timeframe}"),
                surfaces=surfaces,
                combined=(
                    _require_int(values, "C1", record=f"P6SNAP {timeframe}"),
                    _require_int(values, "C2", record=f"P6SNAP {timeframe}"),
                ),
            )
        elif line.startswith("P6SNAP_END|"):
            values = _fields(line)
            declared = _require_int(values, "tfCount", record="P6SNAP_END")
            if declared != len(REQUIRED_TIMEFRAMES):
                raise CaptureError(
                    f"P6SNAP_END declares {declared} timeframes, expected "
                    f"{len(REQUIRED_TIMEFRAMES)}"
                )
            saw_end = True

    if meta is None:
        raise CaptureError("no P6META record: this is not a snapshot capture")
    if not saw_end:
        raise CaptureError("no P6SNAP_END record: the capture is truncated")

    missing = [tf for tf in REQUIRED_TIMEFRAMES if tf not in timeframes]
    if missing:
        raise CaptureError(f"snapshot is missing timeframes: {missing}")

    if require_feed:
        _check_feed(meta.provider, meta.ticker, record="P6META")

    if meta.host_confirmed <= 0 or meta.host_dataset <= 0:
        raise CaptureError("P6META: non-positive host bar counts")
    for snap in timeframes.values():
        _check_timeframe(snap, meta)

    return Snapshot(meta=meta, timeframes=timeframes)


def _check_feed(provider: str, ticker: str, *, record: str) -> None:
    if provider != REQUIRED_PROVIDER or ticker != REQUIRED_TICKER:
        raise CaptureError(
            f"{record}: wrong feed {provider}:{ticker}, required "
            f"{REQUIRED_PROVIDER}:{REQUIRED_TICKER}"
        )


def _check_timeframe(snap: TimeframeSnapshot, meta: SnapshotMeta) -> None:
    where = f"P6SNAP {snap.timeframe}"
    if snap.semantic_rows <= 0:
        raise CaptureError(f"{where}: non-positive semantic row count")
    if snap.semantic_rows < meta.semantic_minimum:
        raise CaptureError(
            f"{where}: {snap.semantic_rows} confirmed rows is below the semantic "
            f"minimum {meta.semantic_minimum}"
        )
    if snap.semantic_first_time > snap.semantic_last_time:
        raise CaptureError(f"{where}: first time is after last time")
    if snap.semantic_last_time > meta.anchor_close:
        raise CaptureError(
            f"{where}: last confirmed source time {snap.semantic_last_time} is after "
            f"the host anchor close {meta.anchor_close} -- a forming bar leaked in"
        )
    if snap.swing_count < 0 or snap.equal_count < 0 or snap.transition_count < 0:
        raise CaptureError(f"{where}: negative collection count")
    if snap.direction not in (0, 1, -1):
        raise CaptureError(f"{where}: unknown direction code {snap.direction}")


# ---------------------------------------------------------------------------
# Raw capture
# ---------------------------------------------------------------------------


def parse_raw(text: str, *, require_feed: bool = True) -> RawCapture:
    rows: list[dict[str, Any]] = []
    timeframe: str | None = None
    summary: dict[str, str] | None = None
    seen_ordinals: set[int] = set()

    for raw_line in text.splitlines():
        line = _strip(raw_line)
        if line.startswith("P6RAW|"):
            if summary is not None:
                raise CaptureError("raw row after RAW_SUMMARY: capture is not ordered")
            parts = line.split("|")
            if len(parts) != 9:
                raise CaptureError(f"malformed P6RAW ({len(parts)} fields): {line[:80]!r}")
            _, tf, ordinal, open_time, close_time, o, h, low, c = parts
            if timeframe is None:
                timeframe = tf
            elif tf != timeframe:
                raise CaptureError(f"raw capture mixes timeframes: {timeframe} and {tf}")
            try:
                index = int(ordinal)
                # The Pine logs prices through its canonical encoder, so the row
                # carries the ENCODED integer. Both forms are kept: the encoded
                # one is what the digest folds, the decoded one is what rebuilds
                # a price. Conflating them silently doubles every price.
                encoded = (int(o), int(h), int(low), int(c))
                bar = {
                    "ordinal": index,
                    "time_ms": int(open_time),
                    "time_close_ms": int(close_time),
                    "open_enc": encoded[0],
                    "high_enc": encoded[1],
                    "low_enc": encoded[2],
                    "close_enc": encoded[3],
                    "open_ticks": _decode(encoded[0]),
                    "high_ticks": _decode(encoded[1]),
                    "low_ticks": _decode(encoded[2]),
                    "close_ticks": _decode(encoded[3]),
                }
            except ValueError as exc:
                raise CaptureError(f"non-integer field in P6RAW: {line[:80]!r}") from exc
            if index in seen_ordinals:
                raise CaptureError(f"duplicate ordinal {index} in {tf} raw capture")
            seen_ordinals.add(index)
            rows.append(bar)
        elif line.startswith("P6RAW_SUMMARY|"):
            if summary is not None:
                raise CaptureError("more than one RAW_SUMMARY: captures were mixed")
            parts = line.split("|")
            tf = parts[1] if len(parts) > 1 else ""
            if timeframe is not None and tf != timeframe:
                raise CaptureError(
                    f"RAW_SUMMARY timeframe {tf} does not match rows {timeframe}"
                )
            timeframe = tf
            summary = _fields(line)

    if timeframe is None or summary is None:
        raise CaptureError("no RAW_SUMMARY record: the raw capture is truncated")

    provider = summary.get("provider", "")
    ticker = summary.get("ticker", "")
    if require_feed:
        _check_feed(provider, ticker, record=f"P6RAW_SUMMARY {timeframe}")

    declared_rows = _require_int(summary, "rows", record="P6RAW_SUMMARY")
    if declared_rows != len(rows):
        raise CaptureError(
            f"{timeframe}: RAW_SUMMARY declares {declared_rows} rows, {len(rows)} present"
        )
    if not rows:
        raise CaptureError(f"{timeframe}: raw capture has no rows")

    rows.sort(key=lambda bar: bar["ordinal"])
    expected = list(range(len(rows)))
    if [bar["ordinal"] for bar in rows] != expected:
        raise CaptureError(f"{timeframe}: ordinals are not a complete 0..n-1 run")

    previous = None
    for bar in rows:
        if previous is not None and bar["time_ms"] <= previous:
            raise CaptureError(
                f"{timeframe}: timestamps are not strictly increasing at ordinal "
                f"{bar['ordinal']}"
            )
        previous = bar["time_ms"]
        if bar["time_close_ms"] <= bar["time_ms"]:
            raise CaptureError(
                f"{timeframe}: close time is not after open time at ordinal "
                f"{bar['ordinal']}"
            )
        high, low = bar["high_ticks"], bar["low_ticks"]
        if high < low:
            raise CaptureError(f"{timeframe}: high below low at ordinal {bar['ordinal']}")
        for name in ("open_ticks", "close_ticks"):
            if not low <= bar[name] <= high:
                raise CaptureError(
                    f"{timeframe}: {name} outside [low, high] at ordinal "
                    f"{bar['ordinal']}"
                )

    first_time = _require_int(summary, "first", record="P6RAW_SUMMARY")
    last_time = _require_int(summary, "last", record="P6RAW_SUMMARY")
    if rows[0]["time_ms"] != first_time:
        raise CaptureError(
            f"{timeframe}: RAW_SUMMARY first {first_time} does not match row 0 "
            f"{rows[0]['time_ms']}"
        )
    if rows[-1]["time_ms"] != last_time:
        raise CaptureError(
            f"{timeframe}: RAW_SUMMARY last {last_time} does not match final row "
            f"{rows[-1]['time_ms']}"
        )

    return RawCapture(
        timeframe=timeframe,
        bars=tuple(rows),
        rows=declared_rows,
        first_time=first_time,
        last_time=last_time,
        h1=_require_int(summary, "h1", record="P6RAW_SUMMARY"),
        h2=_require_int(summary, "h2", record="P6RAW_SUMMARY"),
        provider=provider,
        ticker=ticker,
    )


# ---------------------------------------------------------------------------
# The five-dimension lock
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class IdentityResult:
    timeframe: str
    matched: bool
    mismatches: tuple[tuple[str, int, int], ...]

    def describe(self) -> str:
        if self.matched:
            return f"{self.timeframe}: identity 5/5"
        parts = [
            f"{dim}: snapshot={want} raw={got}" for dim, want, got in self.mismatches
        ]
        return f"{self.timeframe}: identity FAILED -- " + "; ".join(parts)


def raw_identity_matches(
    snapshot: TimeframeSnapshot, raw: RawCapture
) -> IdentityResult:
    """Structured, never a bare boolean: a failure must say which dimension."""
    if snapshot.timeframe != raw.timeframe:
        raise CaptureError(
            f"cannot lock {raw.timeframe} raw capture against {snapshot.timeframe} "
            f"snapshot"
        )
    want, got = snapshot.identity(), raw.identity
    mismatches = tuple(
        (dim, want[dim], got[dim]) for dim in want if want[dim] != got[dim]
    )
    return IdentityResult(
        timeframe=snapshot.timeframe,
        matched=not mismatches,
        mismatches=mismatches,
    )


# ---------------------------------------------------------------------------
# Selecting one coherent emission out of a whole log buffer
# ---------------------------------------------------------------------------

#: TradingView stamps every log line with the emission time, in two shapes: the
#: on-screen panel renders `[timestamp]: record`, while the downloaded CSV is
#: `timestamp,record`. Both are accepted so a capture can be taken either way.
_TIMESTAMPED = re.compile(r"^(?:\[([\d\-T:.+]+)\]:\s*|([\d\-T:.+]+),)(P6\w*\|.*)$")


def group_by_emission(text: str) -> list[tuple[str, list[str]]]:
    """Split a log buffer into (timestamp, records) groups, in file order.

    A downloaded buffer holds every emission the study made, and the snapshot
    advances as bars confirm -- so the buffer legitimately contains conflicting
    records for the same timeframe. Grouping by emission timestamp is what turns
    that into a series of individually coherent captures, rather than one
    contradictory pile the parser would rightly refuse.
    """
    groups: list[tuple[str, list[str]]] = []
    for raw in text.splitlines():
        match = _TIMESTAMPED.match(raw.strip())
        if not match:
            continue
        stamp = match.group(1) or match.group(2)
        record = match.group(3)
        if groups and groups[-1][0] == stamp:
            groups[-1][1].append(record)
        else:
            groups.append((stamp, [record]))
    return groups


def latest_complete_snapshot(text: str, *, require_feed: bool = True) -> Snapshot:
    """Parse the most recent emission carrying a COMPLETE snapshot.

    Deliberately the LATEST rather than the first: the newest emission is the one
    whose raw captures can still be reproduced, because the sliding window has
    moved on from the older ones. If no emission is complete the underlying
    CaptureError is raised, so a truncated buffer is never silently accepted.
    """
    last_error: CaptureError | None = None
    for _stamp, records in reversed(group_by_emission(text)):
        block = "\n".join(records)
        if "P6META|" not in block or "P6SNAP_END|" not in block:
            continue
        try:
            return parse_snapshot(block, require_feed=require_feed)
        except CaptureError as exc:  # keep looking at older emissions
            last_error = exc
    if last_error is not None:
        raise last_error
    raise CaptureError("no complete snapshot emission in this log buffer")


def latest_raw_capture(text: str, *, require_feed: bool = True) -> RawCapture:
    """Parse the most recent emission carrying a COMPLETE raw capture."""
    last_error: CaptureError | None = None
    for _stamp, records in reversed(group_by_emission(text)):
        block = "\n".join(records)
        if "P6RAW_SUMMARY|" not in block:
            continue
        try:
            return parse_raw(block, require_feed=require_feed)
        except CaptureError as exc:
            last_error = exc
    if last_error is not None:
        raise last_error
    raise CaptureError("no complete raw capture in this log buffer")
