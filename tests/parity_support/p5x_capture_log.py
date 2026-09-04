"""Strict parser for the P5X transport-extension log lines.

Test/parity tooling only — nothing in `src/` imports this, and it changes no
production semantics.

WHY A SEPARATE PARSER FROM `p6_atomic_capture_log`
-----------------------------------------------------
The P5X lines are a DIFFERENT emitter (`f_p5xLine`, the live-smoke emitter
appended to P6 DEV) from the P6SNAP/P6META atomic-capture lines, sharing only
the log buffer they happen to be interleaved in. They carry the 26-field
extension in human-readable form -- unlike P6SNAP's canonically-encoded digest
fields, `str.tostring()` on a raw Pine value -- so parsing them is a matter of
splitting on `|` and typing each field, not decoding anything.

THE ONE THING THAT NEEDS TRANSLATION: PINE "NaN" -> PYTHON None
------------------------------------------------------------------
`str.tostring(na)` on a float renders the literal string `"NaN"`. The frozen
transport contract's WIRE domain (`P5TransportRecord`) already spells absent
INTEGERS as the C_ST_NA literal -99 -- unchanged by this parser, since Pine's
own `-99` parses natively as the same integer -- but it spells absent FLOATS as
`None`, and Pine has no `None` to print. So this parser is the one place that
maps the literal string `"NaN"` back to `None` for the four float fields
(`disp1Ratio`, `disp2Ratio`, `disp3Ratio`, `pbImpulsePrice`, `pbOriginPrice`,
`pbPullbackPrice`). Everywhere else, wire compares to wire directly: Pine's
`-99` against Python's `C_ST_NA` needs no translation because they are the
same integer.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

REQUIRED_TIMEFRAMES: tuple[str, ...] = ("W1", "D1", "H4", "H1", "M15", "M5")

_LOG_PREFIX = re.compile(r"^.*?(?=P5X_META\||P5X\|)")

#: The 26 fields, in wire order, with their Pine type. Mirrors
#: `tests/parity_support/p5_transport_contract.FIELDS` exactly; duplicated here
#: (rather than imported) because this parser has no dependency on the
#: contract module and should fail loudly on its own if the two drift, via the
#: cross-check test that compares the two field-name tuples.
_INT_FIELDS: tuple[str, ...] = (
    "stateAvailT",
    "contStreak",
    "priorOppStreak",
    "exhaustFlag",
    "transWindowCount",
    "trans1Type",
    "trans2Type",
    "trans3Type",
    "trans4Type",
    "lastTransAvailT",
    "dispWindowCount",
    "disp1Dir",
    "disp1Cls",
    "disp2Dir",
    "disp2Cls",
    "disp3Dir",
    "disp3Cls",
    "dispAvailT",
    "dispClsAtTrans",
)
_FLOAT_FIELDS: tuple[str, ...] = (
    "disp1Ratio",
    "disp2Ratio",
    "disp3Ratio",
    "pbImpulsePrice",
    "pbOriginPrice",
    "pbPullbackPrice",
)
_BOOL_FIELDS: tuple[str, ...] = ("pbValid",)

ALL_FIELDS: tuple[str, ...] = (
    "stateAvailT",
    "contStreak",
    "priorOppStreak",
    "exhaustFlag",
    "transWindowCount",
    "trans1Type",
    "trans2Type",
    "trans3Type",
    "trans4Type",
    "lastTransAvailT",
    "dispWindowCount",
    "disp1Dir",
    "disp1Cls",
    "disp1Ratio",
    "disp2Dir",
    "disp2Cls",
    "disp2Ratio",
    "disp3Dir",
    "disp3Cls",
    "disp3Ratio",
    "dispAvailT",
    "dispClsAtTrans",
    "pbImpulsePrice",
    "pbOriginPrice",
    "pbPullbackPrice",
    "pbValid",
)


class P5XCaptureError(ValueError):
    """A P5X capture is malformed, incomplete, or from the wrong feed."""


def _strip(line: str) -> str:
    return _LOG_PREFIX.sub("", line.strip(), count=1)


def _fields(body: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for part in body.split("|"):
        if "=" in part:
            key, _, value = part.partition("=")
            if key in out:
                raise P5XCaptureError(f"duplicate field {key!r}")
            out[key] = value
    return out


def _parse_value(name: str, raw: str, *, record: str) -> object:
    if name in _INT_FIELDS:
        try:
            return int(raw)
        except ValueError as exc:
            raise P5XCaptureError(
                f"{record}: field {name!r} is not an integer: {raw!r}"
            ) from exc
    if name in _FLOAT_FIELDS:
        if raw == "NaN":
            return None
        try:
            return float(raw)
        except ValueError as exc:
            raise P5XCaptureError(
                f"{record}: field {name!r} is not a float or NaN: {raw!r}"
            ) from exc
    if name in _BOOL_FIELDS:
        if raw not in ("true", "false"):
            raise P5XCaptureError(f"{record}: field {name!r} is not true/false: {raw!r}")
        return raw == "true"
    raise P5XCaptureError(f"{record}: unknown field {name!r}")


@dataclass(frozen=True)
class P5XMeta:
    feed: str
    host_tf: str
    semantic_min: int
    request: int
    host: int
    alias_hits: int


@dataclass(frozen=True)
class P5XRecord:
    timeframe: str
    values: dict[str, object]

    def field(self, name: str) -> object:
        return self.values[name]


@dataclass(frozen=True)
class P5XCapture:
    meta: P5XMeta
    timeframes: dict[str, P5XRecord]


def parse_p5x_capture(text: str) -> P5XCapture:
    meta: P5XMeta | None = None
    meta_line: str | None = None
    records: dict[str, P5XRecord] = {}
    tf_lines: dict[str, str] = {}

    for raw_line in text.splitlines():
        line = _strip(raw_line)
        if line.startswith("P5X_META|"):
            if meta is not None:
                if line == meta_line:
                    continue
                raise P5XCaptureError(
                    "two DIFFERENT P5X_META records: captures from separate "
                    "runs were mixed"
                )
            meta_line = line
            values = _fields(line)
            meta = P5XMeta(
                feed=values.get("feed", ""),
                host_tf=values.get("host_tf", ""),
                semantic_min=int(values.get("semanticMin", "-1")),
                request=int(values.get("request", "-1")),
                host=int(values.get("host", "-1")),
                alias_hits=int(values.get("aliasHits", "-1")),
            )
        elif line.startswith("P5X|"):
            parts = line.split("|", 2)
            if len(parts) < 3:
                raise P5XCaptureError(f"malformed P5X line: {line[:80]!r}")
            timeframe = parts[1]
            if timeframe not in REQUIRED_TIMEFRAMES:
                raise P5XCaptureError(f"unknown timeframe in P5X: {timeframe!r}")
            if timeframe in records:
                if line == tf_lines[timeframe]:
                    continue
                raise P5XCaptureError(
                    f"two DIFFERENT P5X {timeframe} records: captures from "
                    f"separate runs were mixed"
                )
            tf_lines[timeframe] = line
            raw_values = _fields(parts[2])
            parsed: dict[str, object] = {}
            for name in ALL_FIELDS:
                if name not in raw_values:
                    raise P5XCaptureError(f"P5X {timeframe}: missing field {name!r}")
                parsed[name] = _parse_value(name, raw_values[name], record=f"P5X {timeframe}")
            records[timeframe] = P5XRecord(timeframe=timeframe, values=parsed)

    if meta is None:
        raise P5XCaptureError("no P5X_META record: this is not a P5X capture")
    missing = [tf for tf in REQUIRED_TIMEFRAMES if tf not in records]
    if missing:
        raise P5XCaptureError(f"P5X capture is missing timeframes: {missing}")

    return P5XCapture(meta=meta, timeframes=records)


_TIMESTAMPED = re.compile(r"^(?:\[([\d\-T:.+]+)\]:\s*|([\d\-T:.+]+),)(P5X\w*\|.*)$")


def group_by_emission(text: str) -> list[tuple[str, list[str]]]:
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


def find_capture_at(text: str, stamp: str) -> P5XCapture:
    """Parse the P5X capture whose emission timestamp is exactly `stamp`."""
    for group_stamp, records in group_by_emission(text):
        if group_stamp != stamp:
            continue
        block = "\n".join(records)
        if "P5X_META|" not in block:
            continue
        return parse_p5x_capture(block)
    raise P5XCaptureError(f"no P5X capture at timestamp {stamp!r}")
