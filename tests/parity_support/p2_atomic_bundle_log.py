"""Parser for the TradingView Pine-Logs ATOMIC parity bundle export.

Test/tooling only — nothing in `src/` imports this, and it changes no
production semantics. It consumes the Pine Logs output of
`tradingview/btmm_poi_btrc_scanner_p2_atomic_parity_bundle.pine` and yields a
verified bundle **only if every integrity check passes**.

THE ATOMIC IDEA
---------------
P2-PARITY-CONTEXT-1 proved the FXCM feed revises history, so raw context and
state digests captured in different sessions can never be safely combined. The
atomic bundle carries, from ONE script execution:

* ``P2BRAW``   — every confirmed historical bar the engine processed, indexed
  in the engine's own confirmed-bar frame (idx = confirmedBarCount - 1);
* ``P2BCHUNK`` — 50-row integrity checksums (the final chunk may be shorter);
* ``P2BMETA`` — one record with the context fingerprint, the final-600 input
  digests, the final-300 state digests, all 15 per-field hashes, and the
  execution-index origin (cbc / win / absfirst).

There is deliberately NO hard-coded anchor: the bundle defines the NEW anchor.
Counts are structural (input 600, state 300); the context count is whatever
the execution actually processed (1799 with a forming realtime bar, 1800 with
the market closed) and must simply agree with confirmedBarCount.

The digest contract is NOT reimplemented: it is imported from `p2_digest.py`,
the frozen reference. Reject, never repair.
"""

from __future__ import annotations

import csv
import importlib.util
import re
import sys
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "_p2_digest_for_atomic_bundle", Path(__file__).with_name("p2_digest.py")
)
assert _SPEC is not None and _SPEC.loader is not None
_D = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = _D
_SPEC.loader.exec_module(_D)

MOD1, MOD2 = _D.MOD1, _D.MOD2
BASE1, BASE2 = _D.BASE1, _D.BASE2

INPUT_COUNT = 600
STATE_COUNT = 300
CHUNK_SIZE = 50
WINDOW_SIZE = 300  # production lookbackWindow

#: META h-key -> canonical field name, in the frozen STATE_FIELD_ORDER.
FIELD_HASH_KEYS: tuple[tuple[str, str], ...] = (
    ("h01", "adapted_swing_count"),
    ("h02", "last_pivot_start_abs"),
    ("h03", "last_conf_time"),
    ("h04", "relationship_count"),
    ("h05", "last_high_relationship"),
    ("h06", "last_low_relationship"),
    ("h07", "direction"),
    ("h08", "protected_high"),
    ("h09", "protected_low"),
    ("h10", "weak_high"),
    ("h11", "weak_low"),
    ("h12", "transition_count"),
    ("h13", "last_transition_code"),
    ("h14", "last_broken_key"),
    ("h15", "last_broken_level"),
)

_META_RE = re.compile(
    r"P2BMETA\|schema=(?P<schema>\d+)\|anchor=(?P<anchor>\d+|NA)"
    r"\|cbc=(?P<cbc>\d+)\|win=(?P<win>\d+)\|absfirst=(?P<absfirst>-?\d+)"
    r"\|ctxn=(?P<ctxn>\d+)\|ctxfirst=(?P<ctxfirst>\d+|NA)\|ctxlast=(?P<ctxlast>\d+|NA)"
    r"\|mintick=(?P<mintick>[0-9.eE+-]+)\|ctxh1=(?P<ctxh1>\d+)\|ctxh2=(?P<ctxh2>\d+)"
    r"\|inn=(?P<inn>\d+)\|infirst=(?P<infirst>\d+|NA)\|inlast=(?P<inlast>\d+|NA)"
    r"\|inh1=(?P<inh1>\d+)\|inh2=(?P<inh2>\d+)"
    r"\|stn=(?P<stn>\d+)\|stfirst=(?P<stfirst>\d+|NA)\|stlast=(?P<stlast>\d+|NA)"
    r"\|sth1=(?P<sth1>\d+)\|sth2=(?P<sth2>\d+)"
    r"\|h01=(?P<h01>\d+)\|h02=(?P<h02>\d+)\|h03=(?P<h03>\d+)\|h04=(?P<h04>\d+)"
    r"\|h05=(?P<h05>\d+)\|h06=(?P<h06>\d+)\|h07=(?P<h07>\d+)\|h08=(?P<h08>\d+)"
    r"\|h09=(?P<h09>\d+)\|h10=(?P<h10>\d+)\|h11=(?P<h11>\d+)\|h12=(?P<h12>\d+)"
    r"\|h13=(?P<h13>\d+)\|h14=(?P<h14>\d+)\|h15=(?P<h15>\d+)"
    r"\|status=(?P<status>\w+)"
)
_RAW_RE = re.compile(
    r"P2BRAW\|idx=(?P<idx>\d+)\|t=(?P<t>-?\d+)\|o=(?P<o>-?\d+)\|h=(?P<h>-?\d+)"
    r"\|l=(?P<l>-?\d+)\|c=(?P<c>-?\d+)\|tc=(?P<tc>-?\d+)"
    r"\|r1=(?P<r1>\d+)\|r2=(?P<r2>\d+)"
)
_CHUNK_RE = re.compile(
    r"P2BCHUNK\|start=(?P<start>\d+)\|end=(?P<end>\d+)"
    r"\|h1=(?P<h1>\d+)\|h2=(?P<h2>\d+)"
)
_SEED_RE = re.compile(r"P2BSEED\|(?P<body>[^\r\n]*)")


class BundleLogRejected(ValueError):
    """The export failed an integrity check. The data is not usable."""


@dataclass(frozen=True)
class BundleBar:
    index: int
    time_ms: int
    open_ticks: int
    high_ticks: int
    low_ticks: int
    close_ticks: int
    time_close_ms: int
    r1: int
    r2: int

    def encoded(self) -> tuple[int, ...]:
        """The 6 canonical fields, in the frozen input field order."""
        return (
            _D.encode_int(self.time_ms),
            _D.encode_int(self.open_ticks),
            _D.encode_int(self.high_ticks),
            _D.encode_int(self.low_ticks),
            _D.encode_int(self.close_ticks),
            _D.encode_int(self.time_close_ms),
        )

    def prices(self, mintick: Decimal) -> dict[str, Decimal]:
        """Ticks -> price. Exact: integer ticks times a Decimal mintick."""
        return {
            "open": self.open_ticks * mintick,
            "high": self.high_ticks * mintick,
            "low": self.low_ticks * mintick,
            "close": self.close_ticks * mintick,
        }


@dataclass(frozen=True)
class ParsedBundle:
    schema: int
    anchor_ms: int
    cbc: int
    win: int
    absfirst: int
    ctx_count: int
    ctx_first_ms: int
    ctx_last_ms: int
    mintick: Decimal
    ctx_hash_1: int
    ctx_hash_2: int
    input_count: int
    input_first_ms: int
    input_last_ms: int
    input_hash_1: int
    input_hash_2: int
    state_count: int
    state_first_ms: int
    state_last_ms: int
    state_hash_1: int
    state_hash_2: int
    field_hashes: dict[str, int]
    status: str
    bars: tuple[BundleBar, ...]
    chunks: tuple[tuple[int, int, int, int], ...]
    seeds: tuple[str, ...]


def _row_checksums(bar: BundleBar) -> tuple[int, int]:
    encoded = bar.encoded()
    return (
        _D.hash_record(encoded, BASE1, MOD1),
        _D.hash_record(encoded, BASE2, MOD2),
    )


def parse(text: str) -> ParsedBundle:
    """Parse raw Pine Logs text. Structural parse only — no verification."""
    meta_matches = _META_RE.findall(text)
    if len(meta_matches) != 1:
        raise BundleLogRejected(
            f"expected exactly one P2BMETA line, found {len(meta_matches)}"
        )
    meta = _META_RE.search(text)
    assert meta is not None
    for group in ("anchor", "ctxfirst", "ctxlast", "infirst", "inlast", "stfirst", "stlast"):
        if meta.group(group) == "NA":
            raise BundleLogRejected(f"P2BMETA reports {group}=NA (no window)")

    bars = tuple(
        BundleBar(
            index=int(m.group("idx")),
            time_ms=int(m.group("t")),
            open_ticks=int(m.group("o")),
            high_ticks=int(m.group("h")),
            low_ticks=int(m.group("l")),
            close_ticks=int(m.group("c")),
            time_close_ms=int(m.group("tc")),
            r1=int(m.group("r1")),
            r2=int(m.group("r2")),
        )
        for m in _RAW_RE.finditer(text)
    )
    chunks = tuple(
        (
            int(m.group("start")),
            int(m.group("end")),
            int(m.group("h1")),
            int(m.group("h2")),
        )
        for m in _CHUNK_RE.finditer(text)
    )
    seeds = tuple(m.group("body") for m in _SEED_RE.finditer(text))

    return ParsedBundle(
        schema=int(meta.group("schema")),
        anchor_ms=int(meta.group("anchor")),
        cbc=int(meta.group("cbc")),
        win=int(meta.group("win")),
        absfirst=int(meta.group("absfirst")),
        ctx_count=int(meta.group("ctxn")),
        ctx_first_ms=int(meta.group("ctxfirst")),
        ctx_last_ms=int(meta.group("ctxlast")),
        mintick=Decimal(meta.group("mintick")),
        ctx_hash_1=int(meta.group("ctxh1")),
        ctx_hash_2=int(meta.group("ctxh2")),
        input_count=int(meta.group("inn")),
        input_first_ms=int(meta.group("infirst")),
        input_last_ms=int(meta.group("inlast")),
        input_hash_1=int(meta.group("inh1")),
        input_hash_2=int(meta.group("inh2")),
        state_count=int(meta.group("stn")),
        state_first_ms=int(meta.group("stfirst")),
        state_last_ms=int(meta.group("stlast")),
        state_hash_1=int(meta.group("sth1")),
        state_hash_2=int(meta.group("sth2")),
        field_hashes={name: int(meta.group(key)) for key, name in FIELD_HASH_KEYS},
        status=meta.group("status"),
        bars=bars,
        chunks=chunks,
        seeds=seeds,
    )


def verify(parsed: ParsedBundle) -> None:
    """Raise `BundleLogRejected` on the first failed check. Never repairs.

    No expected anchor/hash values are passed in: the bundle IS the new
    canonical snapshot. What is verified is internal consistency — that every
    layer of the bundle (raw rows, chunks, context hashes, nested input slice,
    state metadata, index frame) agrees with every other layer under the
    frozen digest contract.
    """
    if parsed.status != "OK":
        raise BundleLogRejected(f"bundle reported status={parsed.status}")
    if parsed.seeds:
        raise BundleLogRejected(
            "unexpected P2BSEED record(s): the audited engine needs no "
            f"pre-origin seed, got {len(parsed.seeds)}"
        )

    # -- structure ---------------------------------------------------------
    n = parsed.ctx_count
    if n < INPUT_COUNT:
        raise BundleLogRejected(
            f"context count {n} is smaller than the {INPUT_COUNT}-bar input window"
        )
    if len(parsed.bars) != n:
        raise BundleLogRejected(
            f"P2BMETA ctxn={n} disagrees with {len(parsed.bars)} P2BRAW rows"
        )

    indices = [b.index for b in parsed.bars]
    if len(set(indices)) != len(indices):
        duplicates = sorted({i for i in indices if indices.count(i) > 1})
        raise BundleLogRejected(f"duplicate row indices: {duplicates[:10]}")
    if indices != list(range(n)):
        raise BundleLogRejected("row indices are not exactly 0..%d in order" % (n - 1))

    # -- timestamps --------------------------------------------------------
    times = [b.time_ms for b in parsed.bars]
    if any(b <= a for a, b in zip(times, times[1:], strict=False)):
        raise BundleLogRejected("timestamps are not strictly increasing")
    if parsed.ctx_first_ms != times[0] or parsed.ctx_last_ms != times[-1]:
        raise BundleLogRejected("P2BMETA ctxfirst/ctxlast disagree with the row data")
    if parsed.anchor_ms != parsed.ctx_last_ms:
        raise BundleLogRejected(
            f"anchor {parsed.anchor_ms} != last context bar {parsed.ctx_last_ms}"
        )

    # -- execution-index frame --------------------------------------------
    if parsed.cbc != n:
        raise BundleLogRejected(
            f"confirmedBarCount {parsed.cbc} != context count {n}"
        )
    expected_win = min(n, WINDOW_SIZE)
    if parsed.win != expected_win:
        raise BundleLogRejected(
            f"window size {parsed.win} != expected {expected_win}"
        )
    if parsed.absfirst != parsed.cbc - parsed.win:
        raise BundleLogRejected(
            f"absfirst {parsed.absfirst} != cbc - win = {parsed.cbc - parsed.win}"
        )

    # -- per-row checksums -------------------------------------------------
    for bar in parsed.bars:
        r1, r2 = _row_checksums(bar)
        if (r1, r2) != (bar.r1, bar.r2):
            raise BundleLogRejected(
                f"row {bar.index} checksum mismatch: "
                f"logged ({bar.r1}, {bar.r2}) computed ({r1}, {r2})"
            )

    # -- per-chunk checksums (last chunk may be short) ---------------------
    expected_bounds = []
    start = 0
    while start < n:
        end = min(start + CHUNK_SIZE, n) - 1
        expected_bounds.append((start, end))
        start = end + 1
    if [(c[0], c[1]) for c in parsed.chunks] != expected_bounds:
        raise BundleLogRejected(
            f"chunk boundaries {[(c[0], c[1]) for c in parsed.chunks][:5]}... do not "
            f"partition 0..{n - 1} in {CHUNK_SIZE}-row blocks"
        )
    for chunk_start, chunk_end, c1, c2 in parsed.chunks:
        block = [b.encoded() for b in parsed.bars[chunk_start : chunk_end + 1]]
        if _D.hash_sequence(block, BASE1, MOD1) != c1:
            raise BundleLogRejected(f"chunk {chunk_start}..{chunk_end} hash 1 mismatch")
        if _D.hash_sequence(block, BASE2, MOD2) != c2:
            raise BundleLogRejected(f"chunk {chunk_start}..{chunk_end} hash 2 mismatch")

    # -- full context hashes ----------------------------------------------
    records = [b.encoded() for b in parsed.bars]
    ctx1, ctx2 = _D.input_hashes(records)
    if (ctx1, ctx2) != (parsed.ctx_hash_1, parsed.ctx_hash_2):
        raise BundleLogRejected(
            f"recomputed context hashes ({ctx1}, {ctx2}) disagree with "
            f"P2BMETA ({parsed.ctx_hash_1}, {parsed.ctx_hash_2})"
        )

    # -- final-600 input slice, recomputed FROM THE RAW CONTEXT ------------
    if parsed.input_count != INPUT_COUNT:
        raise BundleLogRejected(
            f"input count {parsed.input_count} != {INPUT_COUNT}"
        )
    nested = parsed.bars[n - INPUT_COUNT :]
    if parsed.input_first_ms != nested[0].time_ms:
        raise BundleLogRejected(
            f"input first {parsed.input_first_ms} != raw row {n - INPUT_COUNT} "
            f"time {nested[0].time_ms}"
        )
    if parsed.input_last_ms != parsed.ctx_last_ms:
        raise BundleLogRejected("input last != context last")
    in1, in2 = _D.input_hashes([b.encoded() for b in nested])
    if (in1, in2) != (parsed.input_hash_1, parsed.input_hash_2):
        raise BundleLogRejected(
            f"final-600 hashes recomputed from raw context ({in1}, {in2}) disagree "
            f"with P2BMETA ({parsed.input_hash_1}, {parsed.input_hash_2}) — the "
            "input slice is not nested in the captured context"
        )

    # -- state metadata ----------------------------------------------------
    if parsed.state_count != STATE_COUNT:
        raise BundleLogRejected(
            f"state count {parsed.state_count} != {STATE_COUNT}"
        )
    if n < STATE_COUNT:
        raise BundleLogRejected("context smaller than the state window")
    if parsed.state_first_ms != parsed.bars[n - STATE_COUNT].time_ms:
        raise BundleLogRejected(
            f"state first {parsed.state_first_ms} != raw row {n - STATE_COUNT} "
            f"time {parsed.bars[n - STATE_COUNT].time_ms}"
        )
    if parsed.state_last_ms != parsed.ctx_last_ms:
        raise BundleLogRejected("state last != context last")
    if len(parsed.field_hashes) != 15:
        raise BundleLogRejected("missing per-field state hashes")


def load_verified(text: str) -> ParsedBundle:
    """Parse and verify in one step. Only a fully verified bundle is returned."""
    parsed = parse(text)
    verify(parsed)
    return parsed


def to_canonical_rows(parsed: ParsedBundle) -> list[dict[str, object]]:
    """Canonical rows for the parity campaign. Call only on a verified bundle."""
    return [
        {
            "index": bar.index,
            "time_ms": bar.time_ms,
            "time_close_ms": bar.time_close_ms,
            **bar.prices(parsed.mintick),
        }
        for bar in parsed.bars
    ]


def write_canonical_csv(parsed: ParsedBundle, path: Path) -> None:
    """Write the canonical raw-context CSV (time,open,high,low,close,time_close).

    Prices are exact Decimal strings (ticks * mintick). Call only on a
    verified bundle.
    """
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["time", "open", "high", "low", "close", "time_close"])
        for bar in parsed.bars:
            prices = bar.prices(parsed.mintick)
            writer.writerow(
                [
                    bar.time_ms,
                    str(prices["open"]),
                    str(prices["high"]),
                    str(prices["low"]),
                    str(prices["close"]),
                    bar.time_close_ms,
                ]
            )
