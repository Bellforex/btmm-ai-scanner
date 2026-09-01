"""Strict parser for the P4 atomic parity bundle log.

Test/parity tooling only -- nothing in `src/` imports this, and it changes no
production semantics.

The parser REJECTS; it never repairs. A bundle that is missing a row, has a
duplicate index, is out of order, fails a row checksum, fails a chunk checksum,
fails the whole-context hash, disagrees with its own declared counts, or was
captured with reviewed evidence present is refused outright. Silently patching
any of those would let a broken capture masquerade as a parity result, which is
the one failure mode a parity harness must not have.

The raw-context half is byte-identical in shape to P3BRAW, so the already-verified
context loader reads it unchanged; only the P4BSTATE and P4BMETA records are new.
"""

from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

MOD1 = 1000000007
MOD2 = 1000000009
BASE1 = 1000003
BASE2 = 1000033
CHUNK_SIZE = 50
SCHEMA = 1

#: Number of canonical fields per P4BSTATE record; must equal
#: len(p4_digest.BTMM_FIELD_ORDER).
STATE_FIELDS = 30


class BundleLogRejected(ValueError):
    """The bundle is not a usable atomic capture. Never repaired."""


_RAW_RE = re.compile(
    r"P4BRAW\|idx=(\d+)\|t=(-?\d+)\|o=(-?\d+)\|h=(-?\d+)\|l=(-?\d+)\|c=(-?\d+)"
    r"\|tc=(-?\d+)\|r1=(\d+)\|r2=(\d+)"
)
_CHUNK_RE = re.compile(r"P4BCHUNK\|start=(\d+)\|end=(\d+)\|h1=(\d+)\|h2=(\d+)")
_STATE_RE = re.compile(r"P4BSTATE\|i=(\d+)\|f=([-\d,]+)\|r1=(\d+)\|r2=(\d+)")
_META_RE = re.compile(r"P4BMETA\|([^\n\r]+)")


def _enc(value: int) -> int:
    return 2 * value + 2 if value >= 0 else -2 * value + 1


def _step(acc: int, value: int, base: int, mod: int) -> int:
    return (acc * base + (value % mod)) % mod


@dataclass(frozen=True)
class BundleBar:
    index: int
    time: int
    open_ticks: int
    high_ticks: int
    low_ticks: int
    close_ticks: int
    time_close: int
    r1: int
    r2: int


@dataclass(frozen=True)
class BundleState:
    index: int
    fields: tuple[int, ...]
    r1: int
    r2: int


@dataclass(frozen=True)
class ParsedP4Bundle:
    meta: dict[str, str]
    bars: tuple[BundleBar, ...]
    chunks: tuple[tuple[int, int, int, int], ...]
    states: tuple[BundleState, ...]

    @property
    def anchor(self) -> int:
        return int(self.meta["anchor"])

    @property
    def mintick(self) -> Decimal:
        return Decimal(self.meta["mintick"])

    @property
    def timeframe_period(self) -> str:
        return self.meta["tf"]


def _row_checksums(bar: BundleBar) -> tuple[int, int]:
    r1 = r2 = 0
    for value in (
        bar.time,
        bar.open_ticks,
        bar.high_ticks,
        bar.low_ticks,
        bar.close_ticks,
        bar.time_close,
    ):
        r1 = _step(r1, _enc(value), BASE1, MOD1)
        r2 = _step(r2, _enc(value), BASE2, MOD2)
    return r1, r2


def _state_checksums(state: BundleState) -> tuple[int, int]:
    r1 = r2 = 0
    for value in state.fields:
        r1 = _step(r1, _enc(value), BASE1, MOD1)
        r2 = _step(r2, _enc(value), BASE2, MOD2)
    return r1, r2


def parse(text: str) -> ParsedP4Bundle:
    metas = _META_RE.findall(text)
    if not metas:
        raise BundleLogRejected("no P4BMETA record")
    if len(metas) > 1:
        raise BundleLogRejected(f"{len(metas)} P4BMETA records; expected exactly 1")

    meta: dict[str, str] = {}
    for part in metas[0].split("|"):
        if "=" not in part:
            raise BundleLogRejected(f"malformed meta field {part!r}")
        key, value = part.split("=", 1)
        meta[key] = value

    if meta.get("schema") != str(SCHEMA):
        raise BundleLogRejected(f"schema {meta.get('schema')!r}, expected {SCHEMA}")

    bars = tuple(
        BundleBar(
            index=int(m.group(1)),
            time=int(m.group(2)),
            open_ticks=int(m.group(3)),
            high_ticks=int(m.group(4)),
            low_ticks=int(m.group(5)),
            close_ticks=int(m.group(6)),
            time_close=int(m.group(7)),
            r1=int(m.group(8)),
            r2=int(m.group(9)),
        )
        for m in _RAW_RE.finditer(text)
    )
    chunks = tuple(
        (int(m.group(1)), int(m.group(2)), int(m.group(3)), int(m.group(4)))
        for m in _CHUNK_RE.finditer(text)
    )
    states = tuple(
        BundleState(
            index=int(m.group(1)),
            fields=tuple(int(v) for v in m.group(2).split(",")),
            r1=int(m.group(3)),
            r2=int(m.group(4)),
        )
        for m in _STATE_RE.finditer(text)
    )
    return ParsedP4Bundle(meta=meta, bars=bars, chunks=chunks, states=states)


def verify(parsed: ParsedP4Bundle) -> None:
    """Every integrity gate. Raises on the first failure; repairs nothing."""
    meta = parsed.meta

    # --- context completeness and ordering ---------------------------------
    declared = int(meta["ctxn"])
    if len(parsed.bars) != declared:
        raise BundleLogRejected(
            f"{len(parsed.bars)} P4BRAW rows, meta declares ctxn={declared}"
        )
    if declared == 0:
        raise BundleLogRejected("empty context")

    indices = [b.index for b in parsed.bars]
    if len(set(indices)) != len(indices):
        raise BundleLogRejected("duplicate P4BRAW index")
    if indices != sorted(indices):
        raise BundleLogRejected("P4BRAW rows out of order")
    if indices != list(range(indices[0], indices[0] + len(indices))):
        raise BundleLogRejected("P4BRAW indices are not contiguous")

    times = [b.time for b in parsed.bars]
    if times != sorted(times) or len(set(times)) != len(times):
        raise BundleLogRejected("P4BRAW bar times are not strictly increasing")

    if parsed.bars[0].time != int(meta["ctxfirst"]):
        raise BundleLogRejected("first bar time disagrees with meta ctxfirst")
    if parsed.bars[-1].time != int(meta["ctxlast"]):
        raise BundleLogRejected("last bar time disagrees with meta ctxlast")

    # --- row checksums ------------------------------------------------------
    for bar in parsed.bars:
        r1, r2 = _row_checksums(bar)
        if (r1, r2) != (bar.r1, bar.r2):
            raise BundleLogRejected(f"row checksum mismatch at idx={bar.index}")

    # --- chunk checksums ----------------------------------------------------
    by_index = {b.index: b for b in parsed.bars}
    covered: set[int] = set()
    for start, end, h1, h2 in parsed.chunks:
        acc1 = acc2 = 0
        for i in range(start, end + 1):
            bar = by_index.get(i)
            if bar is None:
                raise BundleLogRejected(f"chunk {start}-{end} covers missing idx={i}")
            acc1 = _step(acc1, bar.r1, BASE1, MOD1)
            acc2 = _step(acc2, bar.r2, BASE2, MOD2)
            covered.add(i)
        if (acc1, acc2) != (h1, h2):
            raise BundleLogRejected(f"chunk checksum mismatch {start}-{end}")
    if covered != set(indices):
        raise BundleLogRejected("chunks do not cover the context exactly once")

    # --- whole-context hash -------------------------------------------------
    ctx1 = ctx2 = 0
    for bar in parsed.bars:
        ctx1 = _step(ctx1, bar.r1, BASE1, MOD1)
        ctx2 = _step(ctx2, bar.r2, BASE2, MOD2)
    if ctx1 != int(meta["ctxh1"]) or ctx2 != int(meta["ctxh2"]):
        raise BundleLogRejected("context hash mismatch")

    # --- setup records ------------------------------------------------------
    n_setup = int(meta["nsetup"])
    if len(parsed.states) != n_setup:
        raise BundleLogRejected(
            f"{len(parsed.states)} P4BSTATE rows, meta declares nsetup={n_setup}"
        )
    state_indices = [s.index for s in parsed.states]
    if state_indices != list(range(n_setup)):
        raise BundleLogRejected("P4BSTATE indices are not 0..nsetup-1 in order")
    for state in parsed.states:
        if len(state.fields) != STATE_FIELDS:
            raise BundleLogRejected(
                f"setup {state.index} has {len(state.fields)} fields,"
                f" expected {STATE_FIELDS}"
            )
        r1, r2 = _state_checksums(state)
        if (r1, r2) != (state.r1, state.r2):
            raise BundleLogRejected(f"state checksum mismatch at i={state.index}")

    st1 = st2 = 0
    for state in parsed.states:
        st1 = _step(st1, state.r1, BASE1, MOD1)
        st2 = _step(st2, state.r2, BASE2, MOD2)
    if st1 != int(meta["sth1"]) or st2 != int(meta["sth2"]):
        raise BundleLogRejected("state transport hash mismatch")

    # --- declared counts must agree with the rows ---------------------------
    from collections import Counter

    by_state = Counter(s.fields[6] for s in parsed.states)
    by_stage = Counter(s.fields[7] for s in parsed.states)
    expected = {
        "ncandidate": by_state.get(1, 0),
        "nforming": by_state.get(2, 0),
        "nblocked": by_state.get(3, 0),
        "nconfirmed": by_state.get(4, 0),
        "ncancelled": by_state.get(5, 0),
        "nfinalgate": by_stage.get(6, 0),
    }
    for key, value in expected.items():
        if int(meta[key]) != value:
            raise BundleLogRejected(
                f"meta {key}={meta[key]} disagrees with rows ({value})"
            )

    # --- the evidence declaration -------------------------------------------
    # A bundle captured with reviewed evidence present must never be replayed
    # against the no-evidence oracle.
    if meta.get("evidence_present") != "0":
        raise BundleLogRejected(
            f"evidence_present={meta.get('evidence_present')!r};"
            " this bundle is not a no-evidence capture"
        )


def load_verified(text: str) -> ParsedP4Bundle:
    parsed = parse(text)
    verify(parsed)
    return parsed


def to_canonical_rows(parsed: ParsedP4Bundle) -> list[dict[str, object]]:
    """Context rows in the shape the shared context loader expects."""
    mintick = parsed.mintick
    rows: list[dict[str, object]] = []
    for bar in parsed.bars:
        rows.append(
            {
                "index": bar.index,
                "time": bar.time,
                "time_close": bar.time_close,
                "open": str(Decimal(bar.open_ticks) * mintick),
                "high": str(Decimal(bar.high_ticks) * mintick),
                "low": str(Decimal(bar.low_ticks) * mintick),
                "close": str(Decimal(bar.close_ticks) * mintick),
            }
        )
    return rows


def write_canonical_csv(parsed: ParsedP4Bundle, path: Path) -> None:
    rows = to_canonical_rows(parsed)
    header = ["index", "time", "time_close", "open", "high", "low", "close"]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=header)
        writer.writeheader()
        writer.writerows(rows)


def pine_states(parsed: ParsedP4Bundle) -> list[tuple[int, ...]]:
    """The emitted setup records, as raw canonical field tuples."""
    return [s.fields for s in parsed.states]
