"""Parser for the TradingView Pine-Logs common-input export.

Test/tooling only — nothing in `src/` imports this, and it changes no production
semantics. It consumes lines copied out of the Pine Logs pane, produced by
`tradingview/p2_m15_common_input_logger.pine`, and turns them into a canonical
local input artifact **only if every integrity check passes**.

The digest contract is NOT reimplemented here: it is imported from
`p2_digest.py`, the frozen reference already pinned by 51 tests. If the two ever
drift, the row checksums stop matching and this parser refuses the data.

WHY CHECKSUMS AT ALL
--------------------
These 600 rows become the common input for a Python-vs-Pine comparison. A single
transposed digit would surface later as a fake Structure mismatch, which is the
most expensive kind of wrong answer available here. So the export carries three
independent layers, and this parser rejects rather than repairs:

* **per-row** `r1`/`r2` — catches a corrupted digit inside one row;
* **per-chunk** hashes every 50 rows — catches a missing, duplicated or
  reordered row within a block;
* **whole-window** `h1`/`h2` — must equal the hashes the parity probe itself
  reported, which is what proves both engines are looking at the same bars.

Nothing is inferred. A bar that was not logged is never reconstructed.
"""

from __future__ import annotations

import importlib.util
import re
import sys
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "_p2_digest_for_input_log", Path(__file__).with_name("p2_digest.py")
)
assert _SPEC is not None and _SPEC.loader is not None
_D = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = _D
_SPEC.loader.exec_module(_D)

MOD1, MOD2 = _D.MOD1, _D.MOD2
BASE1, BASE2 = _D.BASE1, _D.BASE2

EXPECTED_COUNT = 600
CHUNK_SIZE = 50

#: The parity snapshot this export must reproduce.
EXPECTED_FIRST_MS = 1786984200000
EXPECTED_LAST_MS = 1787722200000
EXPECTED_HASH_1 = 192040354
EXPECTED_HASH_2 = 862722483

_META_RE = re.compile(
    r"P2META\|schema=(?P<schema>\d+)\|count=(?P<count>\d+)\|first=(?P<first>\d+|NA)"
    r"\|last=(?P<last>\d+|NA)\|mintick=(?P<mintick>[0-9.eE+-]+)"
    r"\|h1=(?P<h1>\d+)\|h2=(?P<h2>\d+)\|status=(?P<status>\w+)"
)
_RAW_RE = re.compile(
    r"P2RAW\|i=(?P<i>\d+)\|t=(?P<t>-?\d+)\|o=(?P<o>-?\d+)\|h=(?P<h>-?\d+)"
    r"\|l=(?P<l>-?\d+)\|c=(?P<c>-?\d+)\|tc=(?P<tc>-?\d+)"
    r"\|r1=(?P<r1>\d+)\|r2=(?P<r2>\d+)"
)
_CHUNK_RE = re.compile(
    r"P2CHUNK\|start=(?P<start>\d+)\|end=(?P<end>\d+)\|h1=(?P<h1>\d+)\|h2=(?P<h2>\d+)"
)


class InputLogRejected(ValueError):
    """The export failed an integrity check. The data is not usable."""


@dataclass(frozen=True)
class LoggedBar:
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
        """Ticks -> price. Exact, because ticks are integers and mintick is a
        Decimal — no binary floating point is involved."""
        return {
            "open": self.open_ticks * mintick,
            "high": self.high_ticks * mintick,
            "low": self.low_ticks * mintick,
            "close": self.close_ticks * mintick,
        }


@dataclass(frozen=True)
class ParsedInputLog:
    schema: int
    count: int
    first_ms: int
    last_ms: int
    mintick: Decimal
    hash_1: int
    hash_2: int
    status: str
    bars: tuple[LoggedBar, ...]
    chunks: tuple[tuple[int, int, int, int], ...]


def _row_checksums(bar: LoggedBar) -> tuple[int, int]:
    encoded = bar.encoded()
    return (
        _D.hash_record(encoded, BASE1, MOD1),
        _D.hash_record(encoded, BASE2, MOD2),
    )


def parse(text: str) -> ParsedInputLog:
    """Parse raw Pine Logs text. Structural parse only — no verification."""
    meta_matches = _META_RE.findall(text)
    if len(meta_matches) != 1:
        raise InputLogRejected(
            f"expected exactly one P2META line, found {len(meta_matches)}"
        )
    meta = _META_RE.search(text)
    assert meta is not None
    if meta.group("first") == "NA" or meta.group("last") == "NA":
        raise InputLogRejected("P2META reports no window (first/last = NA)")

    bars = tuple(
        LoggedBar(
            index=int(m.group("i")),
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
        (int(m.group("start")), int(m.group("end")), int(m.group("h1")), int(m.group("h2")))
        for m in _CHUNK_RE.finditer(text)
    )

    return ParsedInputLog(
        schema=int(meta.group("schema")),
        count=int(meta.group("count")),
        first_ms=int(meta.group("first")),
        last_ms=int(meta.group("last")),
        mintick=Decimal(meta.group("mintick")),
        hash_1=int(meta.group("h1")),
        hash_2=int(meta.group("h2")),
        status=meta.group("status"),
        bars=bars,
        chunks=chunks,
    )


def verify(
    parsed: ParsedInputLog,
    *,
    expected_first_ms: int = EXPECTED_FIRST_MS,
    expected_last_ms: int = EXPECTED_LAST_MS,
    expected_hash_1: int = EXPECTED_HASH_1,
    expected_hash_2: int = EXPECTED_HASH_2,
    expected_count: int = EXPECTED_COUNT,
) -> None:
    """Raise `InputLogRejected` on the first failed check. Never repairs."""
    if parsed.status != "OK":
        raise InputLogRejected(f"logger reported status={parsed.status}")

    # -- structure ---------------------------------------------------------
    if len(parsed.bars) != expected_count:
        raise InputLogRejected(
            f"expected {expected_count} P2RAW rows, found {len(parsed.bars)}"
        )
    if parsed.count != len(parsed.bars):
        raise InputLogRejected(
            f"P2META count={parsed.count} disagrees with {len(parsed.bars)} rows"
        )

    indices = [b.index for b in parsed.bars]
    if len(set(indices)) != len(indices):
        duplicates = sorted({i for i in indices if indices.count(i) > 1})
        raise InputLogRejected(f"duplicate row indices: {duplicates[:10]}")
    if indices != list(range(expected_count)):
        raise InputLogRejected("row indices are not exactly 0..%d in order" % (expected_count - 1))

    # -- timestamps --------------------------------------------------------
    times = [b.time_ms for b in parsed.bars]
    if any(b <= a for a, b in zip(times, times[1:], strict=False)):
        raise InputLogRejected("timestamps are not strictly increasing")
    if times[0] != expected_first_ms:
        raise InputLogRejected(
            f"first timestamp {times[0]} != expected {expected_first_ms}"
        )
    if times[-1] != expected_last_ms:
        raise InputLogRejected(
            f"last timestamp {times[-1]} != expected {expected_last_ms}"
        )
    if parsed.first_ms != times[0] or parsed.last_ms != times[-1]:
        raise InputLogRejected("P2META first/last disagree with the row data")

    # -- per-row checksums -------------------------------------------------
    for bar in parsed.bars:
        r1, r2 = _row_checksums(bar)
        if (r1, r2) != (bar.r1, bar.r2):
            raise InputLogRejected(
                f"row {bar.index} checksum mismatch: "
                f"logged ({bar.r1}, {bar.r2}) computed ({r1}, {r2})"
            )

    # -- per-chunk checksums ----------------------------------------------
    expected_chunks = expected_count // CHUNK_SIZE
    if len(parsed.chunks) != expected_chunks:
        raise InputLogRejected(
            f"expected {expected_chunks} P2CHUNK lines, found {len(parsed.chunks)}"
        )
    for start, end, c1, c2 in parsed.chunks:
        if end - start + 1 != CHUNK_SIZE:
            raise InputLogRejected(f"chunk {start}..{end} is not {CHUNK_SIZE} rows")
        block = [b.encoded() for b in parsed.bars[start : end + 1]]
        if _D.hash_sequence(block, BASE1, MOD1) != c1:
            raise InputLogRejected(f"chunk {start}..{end} hash 1 mismatch")
        if _D.hash_sequence(block, BASE2, MOD2) != c2:
            raise InputLogRejected(f"chunk {start}..{end} hash 2 mismatch")

    # -- whole-window hashes ----------------------------------------------
    records = [b.encoded() for b in parsed.bars]
    h1, h2 = _D.input_hashes(records)
    if h1 != parsed.hash_1 or h2 != parsed.hash_2:
        raise InputLogRejected(
            f"recomputed window hashes ({h1}, {h2}) disagree with P2META "
            f"({parsed.hash_1}, {parsed.hash_2})"
        )
    if (h1, h2) != (expected_hash_1, expected_hash_2):
        raise InputLogRejected(
            f"window hashes ({h1}, {h2}) do not match the parity probe "
            f"({expected_hash_1}, {expected_hash_2}) — common input NOT proven"
        )


def load_verified(text: str, **kwargs: int) -> ParsedInputLog:
    """Parse and verify in one step. Only a fully verified export is returned."""
    parsed = parse(text)
    verify(parsed, **kwargs)
    return parsed


def to_canonical_rows(parsed: ParsedInputLog) -> list[dict[str, object]]:
    """Canonical rows for the parity campaign. Call only on a verified export."""
    return [
        {
            "index": bar.index,
            "time_ms": bar.time_ms,
            "time_close_ms": bar.time_close_ms,
            **bar.prices(parsed.mintick),
        }
        for bar in parsed.bars
    ]
