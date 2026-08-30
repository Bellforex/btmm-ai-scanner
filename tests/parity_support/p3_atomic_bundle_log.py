"""Parser for the TradingView Pine-Logs P3 ATOMIC parity bundle export.

Test/tooling only — nothing in `src/` imports this, and it changes no
production semantics. It consumes the Pine Logs output of
`tradingview/btmm_poi_btrc_scanner_p3_atomic_parity_bundle.pine` and yields a
verified bundle **only if every integrity check passes**.

THE ATOMIC IDEA
---------------
P2-PARITY-CONTEXT-1 proved the FXCM feed revises history, so raw context and
semantic digests captured in different sessions can never be safely combined.
The bundle therefore carries, from ONE script execution:

* ``P3BRAW``   — every confirmed historical bar the engine processed, indexed
  in the engine's own confirmed-bar frame (idx = confirmedBarCount - 1);
* ``P3BCHUNK`` — 50-row integrity checksums (the final chunk may be shorter);
* ``P3BMETA``  — one record with the context fingerprint, the registry counts,
  the nine family hashes, the seven lifecycle-field hashes and the overall
  dual hashes.

There is deliberately NO hard-coded anchor: the bundle DEFINES the new anchor.
The context count is whatever the execution actually processed and must simply
agree with the row data and with ``confirmedBarCount``.

REJECT, NEVER REPAIR. Every inconsistency raises; nothing is patched, inferred
or filled in. A silently repaired bundle would turn a real divergence into a
false pass.

The digest contract is NOT reimplemented: it is imported from `p3_digest.py`
(which itself reuses `p2_digest.py`), the frozen reference.
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
    "_p3_digest_for_atomic_bundle", Path(__file__).with_name("p3_digest.py")
)
assert _SPEC is not None and _SPEC.loader is not None
_D3 = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = _D3
_SPEC.loader.exec_module(_D3)

MOD1, MOD2 = _D3.MOD1, _D3.MOD2
BASE1, BASE2 = _D3.BASE1, _D3.BASE2
FAMILIES = _D3.FAMILIES
LIFECYCLE_FIELDS = _D3.LIFECYCLE_FIELDS
SCHEMA_VERSION = _D3.SCHEMA_VERSION

CHUNK_SIZE = 50

_P2 = _D3._D  # the frozen dual-hash primitives


class BundleLogRejected(ValueError):
    """The bundle is not internally consistent. It is never repaired."""


_RAW_RE = re.compile(
    r"P3BRAW\|idx=(?P<idx>\d+)\|t=(?P<t>-?\d+)\|o=(?P<o>-?\d+)\|h=(?P<h>-?\d+)"
    r"\|l=(?P<l>-?\d+)\|c=(?P<c>-?\d+)\|tc=(?P<tc>-?\d+)"
    r"\|r1=(?P<r1>\d+)\|r2=(?P<r2>\d+)"
)

_CHUNK_RE = re.compile(
    r"P3BCHUNK\|start=(?P<start>\d+)\|end=(?P<end>\d+)"
    r"\|h1=(?P<h1>\d+)\|h2=(?P<h2>\d+)"
)

_META_RE = re.compile(
    r"P3BMETA\|schema=(?P<schema>\d+)\|anchor=(?P<anchor>\d+|NA)"
    r"\|cbc=(?P<cbc>\d+)\|win=(?P<win>\d+)"
    r"\|ctxn=(?P<ctxn>\d+)\|ctxfirst=(?P<ctxfirst>\d+|NA)"
    r"\|ctxlast=(?P<ctxlast>\d+|NA)\|mintick=(?P<mintick>[0-9.eE+-]+)"
    r"\|ctxh1=(?P<ctxh1>\d+)\|ctxh2=(?P<ctxh2>\d+)"
    r"\|nregistry=(?P<nregistry>\d+)\|nactive=(?P<nactive>\d+)"
    r"\|nterminal=(?P<nterminal>\d+)"
    r"\|ovh1=(?P<ovh1>\d+)\|ovh2=(?P<ovh2>\d+)"
)


@dataclass(frozen=True)
class BundleBar:
    """One confirmed historical bar, in integer ticks and epoch milliseconds."""

    index: int
    time_ms: int
    open_ticks: int
    high_ticks: int
    low_ticks: int
    close_ticks: int
    time_close_ms: int
    row_hash_1: int
    row_hash_2: int


@dataclass(frozen=True)
class ParsedBundle:
    """A bundle that has passed every integrity check."""

    schema: int
    anchor: int
    cbc: int
    window: int
    ctx_count: int
    ctx_first: int
    ctx_last: int
    mintick: Decimal
    ctx_hash_1: int
    ctx_hash_2: int
    registry_count: int
    active_count: int
    terminal_count: int
    overall_hash_1: int
    overall_hash_2: int
    family_hashes: dict[str, int]
    lifecycle_hashes: dict[str, int]
    bars: tuple[BundleBar, ...]
    chunks: tuple[tuple[int, int, int, int], ...]


def _row_checksums(bar: BundleBar) -> tuple[int, int]:
    """Recompute a row's dual checksum from its own fields."""
    fields = (
        bar.time_ms,
        bar.open_ticks,
        bar.high_ticks,
        bar.low_ticks,
        bar.close_ticks,
        bar.time_close_ms,
    )
    encoded = [_P2.encode_int(value) for value in fields]
    return (
        _P2.hash_record(encoded, BASE1, MOD1),
        _P2.hash_record(encoded, BASE2, MOD2),
    )


def parse(text: str) -> ParsedBundle:
    """Parse the export. Structure only — `verify` does the arithmetic."""
    meta_all = _META_RE.findall(text)
    if len(meta_all) != 1:
        raise BundleLogRejected(
            f"expected exactly one P3BMETA line, found {len(meta_all)}"
        )
    meta = _META_RE.search(text)
    assert meta is not None

    for group in ("anchor", "ctxfirst", "ctxlast"):
        if meta.group(group) == "NA":
            raise BundleLogRejected(f"P3BMETA reports {group}=NA (no context)")

    family_hashes: dict[str, int] = {}
    for family in FAMILIES:
        found = re.search(rf"\|fam_{family}=(\d+)", text)
        if found is None:
            raise BundleLogRejected(f"P3BMETA is missing fam_{family}")
        family_hashes[family] = int(found.group(1))

    lifecycle_hashes: dict[str, int] = {}
    for field in LIFECYCLE_FIELDS:
        found = re.search(rf"\|lc_{field}=(\d+)", text)
        if found is None:
            raise BundleLogRejected(f"P3BMETA is missing lc_{field}")
        lifecycle_hashes[field] = int(found.group(1))

    bars = tuple(
        BundleBar(
            index=int(m.group("idx")),
            time_ms=int(m.group("t")),
            open_ticks=int(m.group("o")),
            high_ticks=int(m.group("h")),
            low_ticks=int(m.group("l")),
            close_ticks=int(m.group("c")),
            time_close_ms=int(m.group("tc")),
            row_hash_1=int(m.group("r1")),
            row_hash_2=int(m.group("r2")),
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

    if not bars:
        raise BundleLogRejected("no P3BRAW rows in the export")

    return ParsedBundle(
        schema=int(meta.group("schema")),
        anchor=int(meta.group("anchor")),
        cbc=int(meta.group("cbc")),
        window=int(meta.group("win")),
        ctx_count=int(meta.group("ctxn")),
        ctx_first=int(meta.group("ctxfirst")),
        ctx_last=int(meta.group("ctxlast")),
        mintick=Decimal(meta.group("mintick")),
        ctx_hash_1=int(meta.group("ctxh1")),
        ctx_hash_2=int(meta.group("ctxh2")),
        registry_count=int(meta.group("nregistry")),
        active_count=int(meta.group("nactive")),
        terminal_count=int(meta.group("nterminal")),
        overall_hash_1=int(meta.group("ovh1")),
        overall_hash_2=int(meta.group("ovh2")),
        family_hashes=family_hashes,
        lifecycle_hashes=lifecycle_hashes,
        bars=bars,
        chunks=chunks,
    )


def verify(parsed: ParsedBundle) -> None:
    """Every check that can be made from the bundle alone. Raises on any doubt."""
    if parsed.schema != SCHEMA_VERSION:
        raise BundleLogRejected(f"schema {parsed.schema} != contract {SCHEMA_VERSION}")
    if parsed.mintick <= 0:
        raise BundleLogRejected(f"mintick {parsed.mintick} is not positive")

    bars = parsed.bars
    count = len(bars)

    # -- structure: contiguous 0..n-1, no duplicates, strictly chronological --
    if parsed.ctx_count != count:
        raise BundleLogRejected(
            f"P3BMETA ctxn={parsed.ctx_count} disagrees with {count} P3BRAW rows"
        )
    if parsed.cbc != count:
        raise BundleLogRejected(
            f"P3BMETA cbc={parsed.cbc} disagrees with {count} P3BRAW rows"
        )
    indices = [bar.index for bar in bars]
    if len(set(indices)) != count:
        duplicates = sorted({i for i in indices if indices.count(i) > 1})
        raise BundleLogRejected(f"duplicate P3BRAW indices: {duplicates[:10]}")
    if indices != list(range(count)):
        raise BundleLogRejected(
            "P3BRAW indices are not the contiguous range "
            f"0..{count - 1} in emission order"
        )
    times = [bar.time_ms for bar in bars]
    if len(set(times)) != count:
        raise BundleLogRejected("duplicate bar timestamps in P3BRAW")
    if any(times[i] >= times[i + 1] for i in range(count - 1)):
        raise BundleLogRejected("P3BRAW timestamps are not strictly increasing")
    if times[0] != parsed.ctx_first or times[-1] != parsed.ctx_last:
        raise BundleLogRejected("P3BMETA ctxfirst/ctxlast disagree with the row data")
    if parsed.anchor != parsed.ctx_last:
        raise BundleLogRejected("P3BMETA anchor is not the last context bar")

    # -- OHLC sanity: a bar whose high is below its low is corruption ---------
    for bar in bars:
        if bar.high_ticks < bar.low_ticks:
            raise BundleLogRejected(f"bar {bar.index}: high < low")
        if not (bar.low_ticks <= bar.open_ticks <= bar.high_ticks):
            raise BundleLogRejected(f"bar {bar.index}: open outside [low, high]")
        if not (bar.low_ticks <= bar.close_ticks <= bar.high_ticks):
            raise BundleLogRejected(f"bar {bar.index}: close outside [low, high]")
        if bar.time_close_ms <= bar.time_ms:
            raise BundleLogRejected(f"bar {bar.index}: time_close <= time")

    # -- per-row checksums ----------------------------------------------------
    for bar in bars:
        expected = _row_checksums(bar)
        if (bar.row_hash_1, bar.row_hash_2) != expected:
            raise BundleLogRejected(
                f"bar {bar.index}: row checksum {(bar.row_hash_1, bar.row_hash_2)} "
                f"!= recomputed {expected}"
            )

    # -- chunk partition and checksums ---------------------------------------
    expected_starts = list(range(0, count, CHUNK_SIZE))
    if [chunk[0] for chunk in parsed.chunks] != expected_starts:
        raise BundleLogRejected(
            f"P3BCHUNK starts {[c[0] for c in parsed.chunks][:6]}... do not "
            f"partition 0..{count - 1} in {CHUNK_SIZE}-row blocks"
        )
    for start, end, h1, h2 in parsed.chunks:
        last = min(start + CHUNK_SIZE, count) - 1
        if end != last:
            raise BundleLogRejected(f"P3BCHUNK {start}..{end} should end at {last}")
        acc1 = 0
        acc2 = 0
        for bar in bars[start : end + 1]:
            acc1 = _P2.step(acc1, bar.row_hash_1, BASE1, MOD1)
            acc2 = _P2.step(acc2, bar.row_hash_2, BASE2, MOD2)
        if (acc1, acc2) != (h1, h2):
            raise BundleLogRejected(
                f"P3BCHUNK {start}..{end} checksum {(h1, h2)} != recomputed "
                f"{(acc1, acc2)}"
            )

    # -- whole-context digest -------------------------------------------------
    acc1 = 0
    acc2 = 0
    for bar in bars:
        acc1 = _P2.step(acc1, bar.row_hash_1, BASE1, MOD1)
        acc2 = _P2.step(acc2, bar.row_hash_2, BASE2, MOD2)
    if (acc1, acc2) != (parsed.ctx_hash_1, parsed.ctx_hash_2):
        raise BundleLogRejected(
            f"context digest recomputed {(acc1, acc2)} != P3BMETA "
            f"({parsed.ctx_hash_1}, {parsed.ctx_hash_2})"
        )

    # -- registry counts ------------------------------------------------------
    if parsed.active_count + parsed.terminal_count != parsed.registry_count:
        raise BundleLogRejected(
            f"nactive {parsed.active_count} + nterminal {parsed.terminal_count} "
            f"!= nregistry {parsed.registry_count}"
        )
    if parsed.registry_count == 0:
        raise BundleLogRejected("registry is empty; nothing to compare")


def load_verified(text: str) -> ParsedBundle:
    """Parse and verify. The only entry point callers should use."""
    parsed = parse(text)
    verify(parsed)
    return parsed


def to_canonical_rows(parsed: ParsedBundle) -> list[dict[str, object]]:
    """The frozen context as decimal prices, for the offline replay."""
    tick = parsed.mintick
    return [
        {
            "time": bar.time_ms,
            "open": str(Decimal(bar.open_ticks) * tick),
            "high": str(Decimal(bar.high_ticks) * tick),
            "low": str(Decimal(bar.low_ticks) * tick),
            "close": str(Decimal(bar.close_ticks) * tick),
            "time_close": bar.time_close_ms,
        }
        for bar in parsed.bars
    ]


def write_canonical_csv(parsed: ParsedBundle, path: Path) -> None:
    rows = to_canonical_rows(parsed)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle, fieldnames=["time", "open", "high", "low", "close", "time_close"]
        )
        writer.writeheader()
        writer.writerows(rows)


def context_hashes_from_rows(
    rows: list[dict[str, object]], mintick: Decimal
) -> tuple[int, int]:
    """Recompute the context digest from a CSV read back independently.

    Used to prove the canonical CSV is a faithful carrier of the bundle: it
    goes through prices and back to ticks, so a rounding mistake cannot hide.
    """
    acc1 = 0
    acc2 = 0
    for row in rows:
        encoded = [
            _P2.encode_int(int(row["time"])),
            _P2.encode_price(Decimal(str(row["open"])), mintick),
            _P2.encode_price(Decimal(str(row["high"])), mintick),
            _P2.encode_price(Decimal(str(row["low"])), mintick),
            _P2.encode_price(Decimal(str(row["close"])), mintick),
            _P2.encode_int(int(row["time_close"])),
        ]
        acc1 = _P2.step(acc1, _P2.hash_record(encoded, BASE1, MOD1), BASE1, MOD1)
        acc2 = _P2.step(acc2, _P2.hash_record(encoded, BASE2, MOD2), BASE2, MOD2)
    return (acc1, acc2)
