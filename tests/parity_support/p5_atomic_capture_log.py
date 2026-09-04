"""Strict parser for the P5 ATOMIC PARITY capture: `P5WIRE` (per-bar wire) and
`P5EVAL` (per-bar-per-POI decision) log lines.

Test/parity tooling only — nothing in `src/` imports this, and it changes no
production semantics.

WHY A SEPARATE PARSER FROM `p5x_capture_log`
------------------------------------------------
`p5x_capture_log` parses P5X/P5X_META: a single 26-field-times-6-timeframe
snapshot emitted ONCE per script (re)start (`barstate.islast`). It cannot be
joined to a specific bar's decision. `P5WIRE` is a DIFFERENT emitter (see
`f_p5WireExt`/the `if debugMode` block right before the active-POI loop in
`btmm_poi_btrc_scanner_p5_atomic_parity.pine`): the SAME 26-field UDT for
exactly the four contexts T1/T5-global/T3/T4 actually read (D1, W1, H4, M15),
plus the raw p2Dir/swingCount scalars, emitted ONCE PER CONFIRMED BAR and
joinable to that bar's `P5EVAL` rows by `bar=`. This module parses both tags
from one capture file and groups them by that shared `bar=` key.

THE ONE THING THAT NEEDS TRANSLATION: PINE "NaN" -> PYTHON None
------------------------------------------------------------------
Identical to `p5x_capture_log`'s own note: `str.tostring(na)` on a float
renders `"NaN"`; the three pullback price fields are the only floats that can
carry it, and are translated to `None` here, matching the frozen
`P5TransportRecord` contract.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from .p5x_capture_log import ALL_FIELDS, P5XRecord, _parse_value

REQUIRED_WIRE_TIMEFRAMES: tuple[str, ...] = ("D1", "W1", "H4", "M15")

_LOG_PREFIX = re.compile(r"^.*?(?=P5WIRE\||P5EVAL\|)")

#: The 7 top-level scalar fields on a P5WIRE line, before the first `tf=` block.
_WIRE_SCALAR_FIELDS: tuple[str, ...] = (
    "d1P2d",
    "d1Sw",
    "w1P2d",
    "w1Sw",
    "h4P2d",
    "h4Sw",
    "m15P2d",
)

#: Every field on a P5EVAL line, in wire order, with its Pine type.
_EVAL_INT_FIELDS: tuple[str, ...] = (
    "poiIdx",
    "poiTier",
    "poiStatus",
    "d1Trend",
    "w1Trend",
    "h4Trend",
    "globalDir",
    "operCtx",
    "regime",
    "momDir",
    "momAccel",
    "momRaw",
    "brk",
    "brkScoreRaw",
    "pb",
    "session",
    "vol",
    "volSuitability",
    "align",
    "sBtmm",
    "sPoi",
    "sTrend",
    "sRegime",
    "sMomentum",
    "sBreakout",
    "sLiquidity",
    "sVolatility",
    "wBtmm",
    "wPoi",
    "wTrend",
    "wRegime",
    "wMomentum",
    "wBreakout",
    "wLiquidity",
    "wVolatility",
    "final",
    "permission",
    "lifecycle",
)
_EVAL_BOOL_FIELDS: tuple[str, ...] = ("poiTerminal", "volAbnormal", "btmmValid", "btmmBullish")
_EVAL_ENUM_FIELDS: tuple[str, ...] = ("poiDir",)  # "BULL" | "BEAR"

ALL_EVAL_FIELDS: tuple[str, ...] = (
    "poiIdx",
    "poiDir",
    "poiTier",
    "poiStatus",
    "poiTerminal",
    "d1Trend",
    "w1Trend",
    "h4Trend",
    "globalDir",
    "operCtx",
    "regime",
    "momDir",
    "momAccel",
    "momRaw",
    "brk",
    "brkScoreRaw",
    "pb",
    "session",
    "vol",
    "volAbnormal",
    "volSuitability",
    "btmmValid",
    "btmmBullish",
    "align",
    "sBtmm",
    "sPoi",
    "sTrend",
    "sRegime",
    "sMomentum",
    "sBreakout",
    "sLiquidity",
    "sVolatility",
    "wBtmm",
    "wPoi",
    "wTrend",
    "wRegime",
    "wMomentum",
    "wBreakout",
    "wLiquidity",
    "wVolatility",
    "final",
    "permission",
    "lifecycle",
)


class P5AtomicCaptureError(ValueError):
    """A P5 ATOMIC capture is malformed, incomplete, or from the wrong feed."""


def _strip(line: str) -> str:
    return _LOG_PREFIX.sub("", line.strip(), count=1)


@dataclass(frozen=True)
class P5WireBar:
    bar: int
    d1_p2_dir: int
    d1_swing_count: int
    w1_p2_dir: int
    w1_swing_count: int
    h4_p2_dir: int
    h4_swing_count: int
    m15_p2_dir: int
    timeframes: dict[str, P5XRecord]


@dataclass(frozen=True)
class P5EvalRow:
    bar: int
    poi_idx: int
    poi_bullish: bool
    values: dict[str, object]

    def field(self, name: str) -> object:
        return self.values[name]


@dataclass(frozen=True)
class P5AtomicCapture:
    #: bar timestamp (ms) -> parsed wire; only bars whose P5WIRE line survived
    #: the log ring buffer are present here.
    wire_by_bar: dict[int, P5WireBar]
    #: bar timestamp (ms) -> every P5EVAL row logged for that bar (one per
    #: eligible POI, in emission order).
    eval_by_bar: dict[int, list[P5EvalRow]]


def _parse_wire_line(line: str) -> P5WireBar:
    body = line[len("P5WIRE|") :]
    scalars: dict[str, str] = {}
    timeframes: dict[str, dict[str, str]] = {}
    current_tf: str | None = None
    bar: int | None = None

    for part in body.split("|"):
        if "=" not in part:
            raise P5AtomicCaptureError(f"malformed P5WIRE field {part!r}")
        key, _, value = part.partition("=")
        if key == "bar":
            bar = int(value)
        elif key == "tf":
            if value not in REQUIRED_WIRE_TIMEFRAMES:
                raise P5AtomicCaptureError(f"unknown P5WIRE timeframe: {value!r}")
            if value in timeframes:
                raise P5AtomicCaptureError(f"duplicate P5WIRE timeframe block: {value!r}")
            current_tf = value
            timeframes[current_tf] = {}
        elif key in _WIRE_SCALAR_FIELDS:
            if current_tf is not None:
                raise P5AtomicCaptureError(
                    f"scalar field {key!r} appeared after a tf= block started"
                )
            if key in scalars:
                raise P5AtomicCaptureError(f"duplicate P5WIRE scalar field {key!r}")
            scalars[key] = value
        else:
            if current_tf is None:
                raise P5AtomicCaptureError(f"field {key!r} appeared before any tf= block")
            if key in timeframes[current_tf]:
                raise P5AtomicCaptureError(f"duplicate field {key!r} in tf={current_tf} block")
            timeframes[current_tf][key] = value

    if bar is None:
        raise P5AtomicCaptureError("P5WIRE line has no bar= field")
    missing_scalars = [f for f in _WIRE_SCALAR_FIELDS if f not in scalars]
    if missing_scalars:
        raise P5AtomicCaptureError(f"P5WIRE bar={bar} missing scalar fields: {missing_scalars}")
    missing_tfs = [tf for tf in REQUIRED_WIRE_TIMEFRAMES if tf not in timeframes]
    if missing_tfs:
        raise P5AtomicCaptureError(f"P5WIRE bar={bar} missing timeframe blocks: {missing_tfs}")

    records: dict[str, P5XRecord] = {}
    for tf, raw_values in timeframes.items():
        missing_fields = [f for f in ALL_FIELDS if f not in raw_values]
        if missing_fields:
            raise P5AtomicCaptureError(
                f"P5WIRE bar={bar} tf={tf} missing fields: {missing_fields}"
            )
        parsed: dict[str, object] = {
            name: _parse_value(name, raw_values[name], record=f"P5WIRE bar={bar} tf={tf}")
            for name in ALL_FIELDS
        }
        records[tf] = P5XRecord(timeframe=tf, values=parsed)

    return P5WireBar(
        bar=bar,
        d1_p2_dir=int(scalars["d1P2d"]),
        d1_swing_count=int(scalars["d1Sw"]),
        w1_p2_dir=int(scalars["w1P2d"]),
        w1_swing_count=int(scalars["w1Sw"]),
        h4_p2_dir=int(scalars["h4P2d"]),
        h4_swing_count=int(scalars["h4Sw"]),
        m15_p2_dir=int(scalars["m15P2d"]),
        timeframes=records,
    )


def _parse_eval_line(line: str) -> P5EvalRow:
    body = line[len("P5EVAL|") :]
    raw: dict[str, str] = {}
    for part in body.split("|"):
        if "=" not in part:
            raise P5AtomicCaptureError(f"malformed P5EVAL field {part!r}")
        key, _, value = part.partition("=")
        if key in raw:
            raise P5AtomicCaptureError(f"duplicate P5EVAL field {key!r}")
        raw[key] = value

    missing = [f for f in ALL_EVAL_FIELDS if f not in raw] + (["bar"] if "bar" not in raw else [])
    if missing:
        raise P5AtomicCaptureError(f"P5EVAL line missing fields: {missing}")

    values: dict[str, object] = {}
    for name in _EVAL_INT_FIELDS:
        try:
            values[name] = int(raw[name])
        except ValueError as exc:
            raise P5AtomicCaptureError(
                f"P5EVAL field {name!r} is not an integer: {raw[name]!r}"
            ) from exc
    for name in _EVAL_BOOL_FIELDS:
        if raw[name] not in ("true", "false"):
            raise P5AtomicCaptureError(f"P5EVAL field {name!r} is not true/false: {raw[name]!r}")
        values[name] = raw[name] == "true"
    if raw["poiDir"] not in ("BULL", "BEAR"):
        raise P5AtomicCaptureError(f"P5EVAL field 'poiDir' is not BULL/BEAR: {raw['poiDir']!r}")
    poi_bullish = raw["poiDir"] == "BULL"
    values["poiDir"] = raw["poiDir"]

    return P5EvalRow(
        bar=int(raw["bar"]),
        poi_idx=values["poiIdx"],  # type: ignore[arg-type]
        poi_bullish=poi_bullish,
        values=values,
    )


def parse_p5_atomic_capture(text: str) -> P5AtomicCapture:
    wire_by_bar: dict[int, P5WireBar] = {}
    wire_line_by_bar: dict[int, str] = {}
    eval_by_bar: dict[int, list[P5EvalRow]] = {}
    eval_lines_seen: set[str] = set()

    for raw_line in text.splitlines():
        line = _strip(raw_line)
        if line.startswith("P5WIRE|"):
            wire = _parse_wire_line(line)
            if wire.bar in wire_by_bar:
                # Pine occasionally re-emits the identical log line for the
                # same bar (a redundant recalculation on reload/tick, not a
                # second real observation) -- byte-identical duplicates are
                # collapsed, exactly like `p5x_capture_log`'s own P5X_META
                # dedup. A DIFFERING second line for the same bar is a real
                # capture corruption and still raises.
                if line == wire_line_by_bar[wire.bar]:
                    continue
                raise P5AtomicCaptureError(
                    f"two DIFFERENT P5WIRE lines for bar={wire.bar}: captures "
                    f"from separate runs were mixed"
                )
            wire_by_bar[wire.bar] = wire
            wire_line_by_bar[wire.bar] = line
        elif line.startswith("P5EVAL|"):
            if line in eval_lines_seen:
                # Byte-identical duplicate emission (same reload/tick
                # phenomenon as P5WIRE above) -- not a second real
                # observation of this POI on this bar.
                continue
            eval_lines_seen.add(line)
            row = _parse_eval_line(line)
            eval_by_bar.setdefault(row.bar, []).append(row)

    if not wire_by_bar:
        raise P5AtomicCaptureError("no P5WIRE lines found: this is not a P5 ATOMIC capture")
    if not eval_by_bar:
        raise P5AtomicCaptureError("no P5EVAL lines found: this is not a P5 ATOMIC capture")

    return P5AtomicCapture(wire_by_bar=wire_by_bar, eval_by_bar=eval_by_bar)


__all__ = [
    "REQUIRED_WIRE_TIMEFRAMES",
    "P5AtomicCapture",
    "P5AtomicCaptureError",
    "P5EvalRow",
    "P5WireBar",
    "parse_p5_atomic_capture",
]
