"""The P3 atomic bundle parser must reject anything it cannot prove.

A parity campaign is only worth as much as its evidence, so the parser's job is
adversarial: every one of these tests corrupts a valid bundle in exactly one
way and asserts the corruption is caught. Silently repairing any of them would
turn a real divergence into a false pass.

The valid bundle is BUILT here from the frozen digest primitives rather than
pasted from a capture, so these tests do not depend on TradingView and cannot
drift with the feed.
"""

from __future__ import annotations

import importlib.util
import sys
from decimal import Decimal
from pathlib import Path

import pytest

_SUPPORT = Path(__file__).resolve().parents[1] / "parity_support"


def _load(name: str):
    spec = importlib.util.spec_from_file_location(
        f"_test_{name}", _SUPPORT / f"{name}.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


B = _load("p3_atomic_bundle_log")
D3 = _load("p3_digest")
P2 = D3._D

MINTICK = Decimal("0.01")
COUNT = 120  # 2 full 50-row chunks plus a 20-row tail


def _bar_fields(index: int) -> tuple[int, int, int, int, int, int]:
    """A synthetic but structurally valid bar."""
    time_ms = 1_787_949_000_000 + index * 900_000
    base = 445_000 + index
    low = base - 30
    high = base + 30
    open_ticks = base - 10
    close_ticks = base + 10
    return (time_ms, open_ticks, high, low, close_ticks, time_ms + 900_000)


def _row_hashes(fields: tuple[int, ...]) -> tuple[int, int]:
    encoded = [P2.encode_int(v) for v in fields]
    return (
        P2.hash_record(encoded, D3.BASE1, D3.MOD1),
        P2.hash_record(encoded, D3.BASE2, D3.MOD2),
    )


def build_bundle(count: int = COUNT) -> str:
    """A fully self-consistent bundle export."""
    lines: list[str] = []
    ctx1 = ctx2 = 0
    chunk1 = chunk2 = 0
    chunk_start = 0
    rows: list[tuple[int, tuple[int, ...], tuple[int, int]]] = []

    for index in range(count):
        time_ms, o, h, low, c, tc = _bar_fields(index)
        fields = (time_ms, o, h, low, c, tc)
        r1, r2 = _row_hashes(fields)
        rows.append((index, fields, (r1, r2)))
        lines.append(
            f"P3BRAW|idx={index:04d}|t={time_ms}|o={o}|h={h}|l={low}|c={c}"
            f"|tc={tc}|r1={r1}|r2={r2}"
        )
        ctx1 = P2.step(ctx1, r1, D3.BASE1, D3.MOD1)
        ctx2 = P2.step(ctx2, r2, D3.BASE2, D3.MOD2)
        chunk1 = P2.step(chunk1, r1, D3.BASE1, D3.MOD1)
        chunk2 = P2.step(chunk2, r2, D3.BASE2, D3.MOD2)
        if index % B.CHUNK_SIZE == B.CHUNK_SIZE - 1:
            lines.append(
                f"P3BCHUNK|start={index - B.CHUNK_SIZE + 1:04d}|end={index:04d}"
                f"|h1={chunk1}|h2={chunk2}"
            )
            chunk1 = chunk2 = 0
            chunk_start = index + 1

    if chunk_start <= count - 1:
        lines.append(
            f"P3BCHUNK|start={chunk_start:04d}|end={count - 1:04d}"
            f"|h1={chunk1}|h2={chunk2}"
        )

    first_time = rows[0][1][0]
    last_time = rows[-1][1][0]
    meta = (
        f"P3BMETA|schema={D3.SCHEMA_VERSION}|anchor={last_time}|cbc={count}"
        f"|win=300|ctxn={count}|ctxfirst={first_time}|ctxlast={last_time}"
        f"|mintick={MINTICK}|ctxh1={ctx1}|ctxh2={ctx2}"
        f"|nregistry=40|nactive=33|nterminal=7|ovh1=123456|ovh2=654321"
    )
    for i, family in enumerate(D3.FAMILIES):
        meta += f"|fam_{family}={1000 + i}"
    for i, field in enumerate(D3.LIFECYCLE_FIELDS):
        meta += f"|lc_{field}={2000 + i}"
    lines.append(meta)
    return "\n".join(lines) + "\n"


# --------------------------------------------------------------------------
# the happy path
# --------------------------------------------------------------------------


def test_a_consistent_bundle_is_accepted() -> None:
    parsed = B.load_verified(build_bundle())
    assert len(parsed.bars) == COUNT
    assert parsed.ctx_count == COUNT
    assert parsed.registry_count == 40
    assert parsed.active_count == 33
    assert parsed.terminal_count == 7
    assert parsed.mintick == MINTICK
    assert set(parsed.family_hashes) == set(D3.FAMILIES)
    assert set(parsed.lifecycle_hashes) == set(D3.LIFECYCLE_FIELDS)


def test_the_anchor_is_defined_by_the_bundle_not_hard_coded() -> None:
    parsed = B.load_verified(build_bundle())
    assert parsed.anchor == parsed.ctx_last == parsed.bars[-1].time_ms


def test_canonical_csv_round_trips_to_the_same_context_digest(tmp_path) -> None:
    """Prices go out as decimals and come back as ticks; rounding cannot hide."""
    import csv

    parsed = B.load_verified(build_bundle())
    path = tmp_path / "ctx.csv"
    B.write_canonical_csv(parsed, path)
    with path.open(encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == COUNT
    recomputed = B.context_hashes_from_rows(rows, parsed.mintick)
    assert recomputed == (parsed.ctx_hash_1, parsed.ctx_hash_2)


# --------------------------------------------------------------------------
# corruption — one mutation each
# --------------------------------------------------------------------------


def test_missing_row_is_rejected() -> None:
    lines = build_bundle().splitlines()
    del lines[7]
    with pytest.raises(B.BundleLogRejected):
        B.load_verified("\n".join(lines))


def test_duplicate_row_is_rejected() -> None:
    lines = build_bundle().splitlines()
    lines.insert(7, lines[6])
    with pytest.raises(B.BundleLogRejected):
        B.load_verified("\n".join(lines))


def test_rows_out_of_index_order_are_rejected() -> None:
    lines = build_bundle().splitlines()
    lines[3], lines[4] = lines[4], lines[3]
    with pytest.raises(B.BundleLogRejected):
        B.load_verified("\n".join(lines))


def test_non_monotonic_timestamps_are_rejected() -> None:
    text = build_bundle()
    time_ms, o, h, low, c, tc = _bar_fields(5)
    fields = (time_ms, o, h, low, c, tc)
    r1, r2 = _row_hashes(fields)
    bad_time = _bar_fields(1)[0]
    bad_fields = (bad_time, o, h, low, c, tc)
    br1, br2 = _row_hashes(bad_fields)
    text = text.replace(
        f"P3BRAW|idx=0005|t={time_ms}|o={o}|h={h}|l={low}|c={c}|tc={tc}"
        f"|r1={r1}|r2={r2}",
        f"P3BRAW|idx=0005|t={bad_time}|o={o}|h={h}|l={low}|c={c}|tc={tc}"
        f"|r1={br1}|r2={br2}",
    )
    with pytest.raises(B.BundleLogRejected):
        B.load_verified(text)


def test_digit_corruption_in_a_price_is_rejected() -> None:
    """The row checksum no longer matches the row."""
    time_ms, o, h, low, c, tc = _bar_fields(9)
    r1, r2 = _row_hashes((time_ms, o, h, low, c, tc))
    text = build_bundle().replace(
        f"P3BRAW|idx=0009|t={time_ms}|o={o}|h={h}|l={low}|c={c}|tc={tc}"
        f"|r1={r1}|r2={r2}",
        f"P3BRAW|idx=0009|t={time_ms}|o={o}|h={h}|l={low}|c={c + 1}|tc={tc}"
        f"|r1={r1}|r2={r2}",
    )
    with pytest.raises(B.BundleLogRejected, match="row checksum"):
        B.load_verified(text)


def test_bad_row_checksum_is_rejected() -> None:
    time_ms, o, h, low, c, tc = _bar_fields(11)
    r1, r2 = _row_hashes((time_ms, o, h, low, c, tc))
    text = build_bundle().replace(f"|r1={r1}|r2={r2}", f"|r1={r1 + 1}|r2={r2}", 1)
    with pytest.raises(B.BundleLogRejected, match="row checksum"):
        B.load_verified(text)


def test_bad_chunk_checksum_is_rejected() -> None:
    lines = build_bundle().splitlines()
    for i, line in enumerate(lines):
        if line.startswith("P3BCHUNK"):
            head, tail = line.rsplit("|h1=", 1)
            h1, h2 = tail.split("|h2=")
            lines[i] = f"{head}|h1={int(h1) + 1}|h2={h2}"
            break
    with pytest.raises(B.BundleLogRejected, match="P3BCHUNK"):
        B.load_verified("\n".join(lines))


def test_missing_chunk_is_rejected() -> None:
    lines = [
        line
        for i, line in enumerate(build_bundle().splitlines())
        if not (line.startswith("P3BCHUNK") and "start=0000" in line)
    ]
    with pytest.raises(B.BundleLogRejected, match="P3BCHUNK"):
        B.load_verified("\n".join(lines))


def test_bad_context_digest_is_rejected() -> None:
    text = build_bundle()
    meta = next(line for line in text.splitlines() if line.startswith("P3BMETA"))
    ctxh1 = meta.split("|ctxh1=")[1].split("|")[0]
    text = text.replace(f"|ctxh1={ctxh1}|", f"|ctxh1={int(ctxh1) + 1}|")
    with pytest.raises(B.BundleLogRejected, match="context digest"):
        B.load_verified(text)


def test_ctxn_disagreeing_with_the_rows_is_rejected() -> None:
    text = build_bundle().replace(f"|ctxn={COUNT}|", f"|ctxn={COUNT - 1}|")
    with pytest.raises(B.BundleLogRejected, match="ctxn"):
        B.load_verified(text)


def test_cbc_disagreeing_with_the_rows_is_rejected() -> None:
    text = build_bundle().replace(f"|cbc={COUNT}|", f"|cbc={COUNT + 5}|")
    with pytest.raises(B.BundleLogRejected, match="cbc"):
        B.load_verified(text)


@pytest.mark.parametrize("family", list(D3.FAMILIES))
def test_missing_family_hash_is_rejected(family: str) -> None:
    text = build_bundle()
    value = text.split(f"|fam_{family}=")[1].split("|")[0]
    text = text.replace(f"|fam_{family}={value}", "")
    with pytest.raises(B.BundleLogRejected, match=f"fam_{family}"):
        B.load_verified(text)


@pytest.mark.parametrize("field", list(D3.LIFECYCLE_FIELDS))
def test_missing_lifecycle_hash_is_rejected(field: str) -> None:
    text = build_bundle()
    value = text.split(f"|lc_{field}=")[1].split("|")[0]
    text = text.replace(f"|lc_{field}={value}", "")
    with pytest.raises(B.BundleLogRejected, match=f"lc_{field}"):
        B.load_verified(text)


def test_forming_or_incomplete_bundle_without_meta_is_rejected() -> None:
    lines = [
        line for line in build_bundle().splitlines() if not line.startswith("P3BMETA")
    ]
    with pytest.raises(B.BundleLogRejected, match="P3BMETA"):
        B.load_verified("\n".join(lines))


def test_two_meta_records_are_rejected() -> None:
    """Two executions in one export can never be combined."""
    text = build_bundle()
    meta = next(line for line in text.splitlines() if line.startswith("P3BMETA"))
    with pytest.raises(B.BundleLogRejected, match="exactly one"):
        B.load_verified(text + meta + "\n")


def test_export_with_no_rows_is_rejected() -> None:
    lines = [
        line for line in build_bundle().splitlines() if not line.startswith("P3BRAW")
    ]
    with pytest.raises(B.BundleLogRejected, match="no P3BRAW"):
        B.load_verified("\n".join(lines))


def test_anchor_not_matching_the_last_bar_is_rejected() -> None:
    text = build_bundle()
    last = _bar_fields(COUNT - 1)[0]
    text = text.replace(f"|anchor={last}|", f"|anchor={last + 900_000}|")
    with pytest.raises(B.BundleLogRejected, match="anchor"):
        B.load_verified(text)


def test_na_context_is_rejected() -> None:
    text = build_bundle()
    first = _bar_fields(0)[0]
    text = text.replace(f"|ctxfirst={first}|", "|ctxfirst=NA|")
    with pytest.raises(B.BundleLogRejected, match="NA"):
        B.load_verified(text)


def test_wrong_schema_is_rejected() -> None:
    text = build_bundle().replace(
        f"P3BMETA|schema={D3.SCHEMA_VERSION}|", "P3BMETA|schema=99|"
    )
    with pytest.raises(B.BundleLogRejected, match="schema"):
        B.load_verified(text)


def test_inconsistent_registry_counts_are_rejected() -> None:
    text = build_bundle().replace("|nactive=33|", "|nactive=30|")
    with pytest.raises(B.BundleLogRejected, match="nactive"):
        B.load_verified(text)


def test_empty_registry_is_rejected() -> None:
    text = build_bundle().replace(
        "|nregistry=40|nactive=33|nterminal=7|", "|nregistry=0|nactive=0|nterminal=0|"
    )
    with pytest.raises(B.BundleLogRejected, match="registry is empty"):
        B.load_verified(text)


def test_impossible_ohlc_is_rejected() -> None:
    """high < low can only be corruption."""
    time_ms, o, h, low, c, tc = _bar_fields(4)
    fields = (time_ms, o, low, h, c, tc)  # high and low swapped
    r1, r2 = _row_hashes(fields)
    good = _row_hashes((time_ms, o, h, low, c, tc))
    text = build_bundle().replace(
        f"P3BRAW|idx=0004|t={time_ms}|o={o}|h={h}|l={low}|c={c}|tc={tc}"
        f"|r1={good[0]}|r2={good[1]}",
        f"P3BRAW|idx=0004|t={time_ms}|o={o}|h={low}|l={h}|c={c}|tc={tc}"
        f"|r1={r1}|r2={r2}",
    )
    with pytest.raises(B.BundleLogRejected, match="high < low"):
        B.load_verified(text)


def test_parser_never_repairs_a_rejected_bundle() -> None:
    """There is no lenient mode: rejection is the only outcome."""
    text = build_bundle()
    assert not hasattr(B, "repair")
    assert not hasattr(B, "parse_lenient")
    lines = text.splitlines()
    del lines[3]
    with pytest.raises(B.BundleLogRejected):
        B.load_verified("\n".join(lines))
