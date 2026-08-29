"""Contract tests for the P2 atomic parity bundle script and its parser.

Three halves:

1. **Static source equivalence (the decisive guard).** The atomic script MUST
   be the frozen P2 parity probe byte-for-byte — title excepted — plus an
   appended read-only P2B instrumentation block. This is proven by direct
   byte comparison against the committed probe, not by human review: any edit
   to P1/P2 logic, the 27-digest contract, field order, or hash constants
   makes the prefix comparison fail.

2. **Parser integrity.** The bundle becomes the canonical NEW parity anchor,
   so every corruption mode must be *rejected*, never repaired.

3. **Emission-format lockstep.** `_emit()` mirrors the Pine appendix so the
   corruption cases are testable without a browser; the source guards pin the
   two formats to each other.
"""

from __future__ import annotations

import hashlib
import importlib.util
import re
import sys
from decimal import Decimal
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
ATOMIC = REPO / "tradingview" / "btmm_poi_btrc_scanner_p2_atomic_parity_bundle.pine"
PROBE = REPO / "tradingview" / "btmm_poi_btrc_scanner_p2_parity_probe.pine"
PRODUCTION = REPO / "tradingview" / "btmm_poi_btrc_scanner_v1.pine"
LOGGER_600 = REPO / "tradingview" / "p2_m15_common_input_logger.pine"

OLD_TITLE = "BTMM + POI + BTRC Scanner [P2 PARITY PROBE]"
NEW_TITLE = "BTMM + POI + BTRC Scanner [P2 ATOMIC PARITY]"
BANNER = "// P2 ATOMIC PARITY BUNDLE  ---  APPENDED INSTRUMENTATION ONLY (P2B*)"


def _load(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(
        name, REPO / "tests" / "parity_support" / filename
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


D = _load("_p2b_digest", "p2_digest.py")
B = _load("_p2b_parser", "p2_atomic_bundle_log.py")

MINTICK = Decimal("0.01")
CHUNK = B.CHUNK_SIZE
IN_N = B.INPUT_COUNT
ST_N = B.STATE_COUNT


def _atomic_appendix() -> str:
    """The appended block, extracted by proving the probe-prefix property."""
    probe = PROBE.read_text(encoding="utf-8")
    atomic = ATOMIC.read_text(encoding="utf-8")
    expected_prefix = probe.replace(
        f'indicator("{OLD_TITLE}"', f'indicator("{NEW_TITLE}"', 1
    )
    assert atomic.startswith(expected_prefix), (
        "atomic script is NOT probe+title-change+appendix — the frozen "
        "P1/P2/digest region differs"
    )
    return atomic[len(expected_prefix) :]


# ---------------------------------------------------------------------------
# Static source equivalence (Phase 10)
# ---------------------------------------------------------------------------

def test_atomic_is_probe_plus_title_change_plus_appendix_only() -> None:
    appendix = _atomic_appendix()
    assert BANNER in appendix
    assert appendix.index(BANNER) < 200, "appendix must begin with its banner"


def test_frozen_source_files_are_untouched() -> None:
    assert (
        hashlib.sha256(PRODUCTION.read_bytes()).hexdigest()
        == "3d6d10df27e4150e6b693cb55bd32bb269478235eabfdf2fecd9aa23d96fa05b"
    )
    assert (
        hashlib.sha256(PROBE.read_bytes()).hexdigest()
        == "17e6d56b5b31c5a8fa4fff4cd4f2f1caff22cbdfdd20917313e2c60c0608b749"
    )
    assert (
        hashlib.sha256(LOGGER_600.read_bytes()).hexdigest()
        == "73029f425e3655f7923be3d3db936c249a8641a372dd7f99235092279fe823a7"
    )


def test_appendix_is_read_only_instrumentation() -> None:
    """The appendix may never assign to production/probe state, add plots, or
    introduce new digest constants — it reuses the frozen P2P_* contract."""
    appendix = _atomic_appendix()
    code = "\n".join(
        ln for ln in appendix.splitlines() if not ln.strip().startswith("//")
    )
    for forbidden in (
        "confirmedBarCount :=", "wHigh", "array.push(p2p", "array.shift(p2p",
        "plot(", "strategy.", "request.", "alert(", "label.new", "box.new",
        "line.new", "table.new", "input.int(", "input.bool(",
    ):
        if forbidden == "wHigh":
            # read-only use is allowed; assignment/mutation is not
            assert "wHigh :=" not in code
            assert not re.search(r"array\.(push|shift|set|clear|pop)\(wHigh", code)
            continue
        assert forbidden not in code, f"appendix must not contain {forbidden}"
    # no NEW digest constants — the frozen probe constants are reused
    assert not re.search(r"int\s+(P2P_)?(MOD|BASE)\d\s*=", code)
    assert "P2P_BASE1" in code and "P2P_MOD2" in code


def test_appendix_finalizes_on_last_confirmed_history_only() -> None:
    appendix = _atomic_appendix()
    code = "\n".join(
        ln for ln in appendix.splitlines() if not ln.strip().startswith("//")
    )
    assert "if barstate.islastconfirmedhistory and not p2bMetaDone" in code
    assert "if barstate.isconfirmed and barstate.ishistory" in code
    assert "barstate.isrealtime" not in code
    assert not re.search(r"if barstate\.islast\b(?!confirmedhistory)", code)


def test_appendix_raw_field_order_matches_the_frozen_contract() -> None:
    appendix = _atomic_appendix()
    raw_block = appendix.split("log.info(\"P2BRAW")[0]
    order = re.findall(r"f_p2pEnc\((b[A-Z]+)\)", raw_block)
    unique = list(dict.fromkeys(order))
    assert unique == ["bT", "bO", "bH", "bL", "bC", "bTC"], unique
    assert list(D.INPUT_FIELD_ORDER) == [
        "time", "open", "high", "low", "close", "time_close"
    ]


def test_appendix_meta_covers_all_15_field_hashes_and_index_frame() -> None:
    appendix = _atomic_appendix()
    meta_call = appendix[appendix.index('log.info("P2BMETA') :]
    for key in [k for k, _n in B.FIELD_HASH_KEYS]:
        assert f"|{key}=" in meta_call, key
    for key in ("|cbc=", "|win=", "|absfirst=", "|ctxh1=", "|ctxh2=",
                "|inh1=", "|inh2=", "|sth1=", "|sth2=", "|status="):
        assert key in meta_call, key
    # the state fold order inside the appendix must be the frozen field order
    fold = appendix.split("// ---- final-300 state digests")[1].split("// ---- execution-index origin")[0]
    arrays = re.findall(r"array\.get\((p2pS_\w+),", fold)
    unique_arrays = list(dict.fromkeys(arrays))
    assert unique_arrays == [
        "p2pS_" + name for _k, name in B.FIELD_HASH_KEYS
    ], unique_arrays


def test_atomic_keeps_probe_calc_bars_count_1800() -> None:
    """The atomic bundle IS the engine run: it must keep the production
    execution horizon (1800), unlike the standalone context logger which
    needed a surplus budget for a stale target. Here the anchor is CURRENT,
    so the newest 1800 bars are exactly the engine's own context."""
    atomic = ATOMIC.read_text(encoding="utf-8")
    first_line = next(
        ln for ln in atomic.splitlines() if ln.startswith("indicator(")
    )
    assert "calc_bars_count = 1800" in first_line
    assert NEW_TITLE in first_line


# ---------------------------------------------------------------------------
# A Python mirror of the Pine appendix emission, for fixtures
# ---------------------------------------------------------------------------

def _bars(n: int = 1799) -> list[dict[str, int]]:
    """Synthetic execution context (default 1799 = forming-realtime-bar case,
    which also exercises the short trailing chunk) with a weekend gap."""
    step = 900_000
    t0 = 1_790_000_100_000
    times: list[int] = []
    t = t0
    while len(times) < n:
        times.append(t)
        t += step
        if len(times) == 700:
            t += 48 * 3600 * 1000
    rows = []
    for i, tm in enumerate(times):
        base = 465000 + (i * 7) % 500
        rows.append(
            {
                "i": i,
                "t": tm,
                "o": base,
                "h": base + 12,
                "l": base - 9,
                "c": base + 3,
                "tc": tm + step,
            }
        )
    return rows


def _encoded(row: dict[str, int]) -> tuple[int, ...]:
    return (
        D.encode_int(row["t"]),
        D.encode_int(row["o"]),
        D.encode_int(row["h"]),
        D.encode_int(row["l"]),
        D.encode_int(row["c"]),
        D.encode_int(row["tc"]),
    )


def _fake_state_hashes() -> dict[str, int]:
    return {key: 1000 + i for i, (key, _name) in enumerate(B.FIELD_HASH_KEYS)}


def _emit(rows: list[dict[str, int]], *, status: str | None = None) -> str:
    """Render a bundle exactly as the Pine appendix does."""
    n = len(rows)
    records = [_encoded(r) for r in rows]
    ctx1, ctx2 = D.input_hashes(records)
    nested = records[n - IN_N :]
    in1, in2 = D.input_hashes(list(nested))
    lines: list[str] = []
    chunk: list[tuple[int, ...]] = []
    chunk_start = 0
    for row in rows:
        enc = _encoded(row)
        r1 = D.hash_record(enc, D.BASE1, D.MOD1)
        r2 = D.hash_record(enc, D.BASE2, D.MOD2)
        lines.append(
            f"P2BRAW|idx={row['i']:04d}|t={row['t']}|o={row['o']}|h={row['h']}"
            f"|l={row['l']}|c={row['c']}|tc={row['tc']}|r1={r1}|r2={r2}"
        )
        chunk.append(enc)
        if len(chunk) == CHUNK:
            lines.append(
                f"P2BCHUNK|start={chunk_start:04d}|end={row['i']:04d}"
                f"|h1={D.hash_sequence(chunk, D.BASE1, D.MOD1)}"
                f"|h2={D.hash_sequence(chunk, D.BASE2, D.MOD2)}"
            )
            chunk = []
            chunk_start = row["i"] + 1
    if chunk:
        lines.append(
            f"P2BCHUNK|start={chunk_start:04d}|end={rows[-1]['i']:04d}"
            f"|h1={D.hash_sequence(chunk, D.BASE1, D.MOD1)}"
            f"|h2={D.hash_sequence(chunk, D.BASE2, D.MOD2)}"
        )
    fh = _fake_state_hashes()
    field_part = "".join(f"|{k}={v}" for k, v in fh.items())
    win = min(n, B.WINDOW_SIZE)
    lines.append(
        f"P2BMETA|schema=1|anchor={rows[-1]['t']}|cbc={n}|win={win}"
        f"|absfirst={n - win}|ctxn={n}|ctxfirst={rows[0]['t']}"
        f"|ctxlast={rows[-1]['t']}|mintick=0.01|ctxh1={ctx1}|ctxh2={ctx2}"
        f"|inn={IN_N}|infirst={rows[n - IN_N]['t']}|inlast={rows[-1]['t']}"
        f"|inh1={in1}|inh2={in2}"
        f"|stn={ST_N}|stfirst={rows[n - ST_N]['t']}|stlast={rows[-1]['t']}"
        f"|sth1=123456789|sth2=987654321{field_part}"
        f"|status={status or 'OK'}"
    )
    return "\n".join(lines)


def _good(n: int = 1799) -> tuple[str, list[dict[str, int]]]:
    rows = _bars(n)
    return _emit(rows), rows


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------

def test_a_clean_1799_bundle_parses_and_verifies() -> None:
    text, rows = _good(1799)
    parsed = B.load_verified(text)
    assert parsed.ctx_count == 1799
    assert parsed.cbc == 1799
    assert parsed.win == 300
    assert parsed.absfirst == 1499
    assert parsed.anchor_ms == rows[-1]["t"]
    assert len(parsed.chunks) == 36            # 35 full + 1 short trailing
    assert parsed.chunks[-1][1] - parsed.chunks[-1][0] + 1 == 49
    assert parsed.mintick == MINTICK
    assert len(parsed.field_hashes) == 15


def test_a_clean_1800_bundle_parses_and_verifies() -> None:
    text, rows = _good(1800)
    parsed = B.load_verified(text)
    assert parsed.ctx_count == 1800
    assert len(parsed.chunks) == 36            # exact 50-row partition
    assert all(e - s + 1 == CHUNK for s, e, _1, _2 in parsed.chunks)
    del rows


def test_canonical_csv_roundtrip_reproduces_all_hashes(tmp_path: Path) -> None:
    text, rows = _good(1799)
    parsed = B.load_verified(text)
    out = tmp_path / "ctx.csv"
    B.write_canonical_csv(parsed, out)
    import csv as _csv
    with out.open(encoding="utf-8") as handle:
        read_rows = list(_csv.DictReader(handle))
    assert len(read_rows) == 1799
    records = [
        D.encode_input_bar(
            time_ms=int(r["time"]),
            open_=Decimal(r["open"]),
            high=Decimal(r["high"]),
            low=Decimal(r["low"]),
            close=Decimal(r["close"]),
            time_close_ms=int(r["time_close"]),
            mintick=MINTICK,
        )
        for r in read_rows
    ]
    assert D.input_hashes(records) == (parsed.ctx_hash_1, parsed.ctx_hash_2)
    assert D.input_hashes(records[-IN_N:]) == (
        parsed.input_hash_1,
        parsed.input_hash_2,
    )
    del rows


def test_gap_preservation_and_decimal_prices() -> None:
    text, rows = _good()
    parsed = B.load_verified(text)
    deltas = {
        b.time_ms - a.time_ms
        for a, b in zip(parsed.bars, parsed.bars[1:], strict=False)
    }
    assert max(deltas) > 900_000, "fixture gap must survive"
    canonical = B.to_canonical_rows(parsed)
    assert canonical[0]["open"] == Decimal(rows[0]["o"]) * MINTICK
    assert isinstance(canonical[0]["open"], Decimal)


# ---------------------------------------------------------------------------
# Corruption must be REJECTED, never repaired
# ---------------------------------------------------------------------------

def test_missing_context_row_is_rejected() -> None:
    text, _rows = _good()
    lines = [ln for ln in text.splitlines() if "|idx=0250|" not in ln]
    with pytest.raises(B.BundleLogRejected, match="disagrees with"):
        B.load_verified("\n".join(lines))


def test_duplicate_row_is_rejected() -> None:
    text, _rows = _good()
    lines = text.splitlines()
    victim = next(ln for ln in lines if "|idx=0100|" in ln)
    lines.insert(lines.index(victim) + 1, victim)
    with pytest.raises(B.BundleLogRejected):
        B.load_verified("\n".join(lines))


def test_out_of_order_rows_are_rejected() -> None:
    text, _rows = _good()
    lines = text.splitlines()
    a = next(i for i, ln in enumerate(lines) if "|idx=0010|" in ln)
    b = next(i for i, ln in enumerate(lines) if "|idx=0011|" in ln)
    lines[a], lines[b] = lines[b], lines[a]
    with pytest.raises(B.BundleLogRejected, match="not exactly 0"):
        B.load_verified("\n".join(lines))


def test_row_corruption_is_rejected() -> None:
    text, rows = _good()
    broken = text.replace(f"|c={rows[7]['c']}|", f"|c={rows[7]['c'] + 1}|", 1)
    assert broken != text
    with pytest.raises(B.BundleLogRejected, match="checksum mismatch"):
        B.load_verified(broken)


def test_chunk_corruption_is_rejected() -> None:
    text, _rows = _good()
    parsed = B.parse(text)
    start, end, c1, c2 = parsed.chunks[3]
    broken = text.replace(
        f"P2BCHUNK|start={start:04d}|end={end:04d}|h1={c1}|h2={c2}",
        f"P2BCHUNK|start={start:04d}|end={end:04d}|h1={c1 + 1}|h2={c2}",
        1,
    )
    with pytest.raises(B.BundleLogRejected, match="chunk .* hash 1 mismatch"):
        B.load_verified(broken)


def test_context_hash_corruption_is_rejected() -> None:
    text, _rows = _good()
    parsed = B.parse(text)
    broken = text.replace(
        f"|ctxh1={parsed.ctx_hash_1}|", f"|ctxh1={parsed.ctx_hash_1 + 1}|", 1
    )
    with pytest.raises(B.BundleLogRejected, match="context hashes"):
        B.load_verified(broken)


def test_incorrect_final_600_hash_is_rejected() -> None:
    text, _rows = _good()
    parsed = B.parse(text)
    broken = text.replace(
        f"|inh1={parsed.input_hash_1}|", f"|inh1={parsed.input_hash_1 + 1}|", 1
    )
    with pytest.raises(B.BundleLogRejected, match="not nested in the captured"):
        B.load_verified(broken)


def test_missing_state_field_hash_is_rejected() -> None:
    text, _rows = _good()
    broken = re.sub(r"\|h07=\d+", "", text, count=1)
    with pytest.raises(B.BundleLogRejected, match="exactly one P2BMETA"):
        B.load_verified(broken)


def test_forming_or_incomplete_bundle_is_rejected() -> None:
    rows = _bars()
    text = _emit(rows, status="MISMATCH")
    with pytest.raises(B.BundleLogRejected, match="status=MISMATCH"):
        B.load_verified(text)
    # missing META entirely
    no_meta = "\n".join(
        ln for ln in _emit(rows).splitlines() if not ln.startswith("P2BMETA")
    )
    with pytest.raises(B.BundleLogRejected, match="exactly one P2BMETA"):
        B.load_verified(no_meta)


def test_unexpected_seed_record_is_rejected() -> None:
    """Phase 1 proved no pre-origin seed exists; a P2BSEED record therefore
    signals a contract drift and must be rejected, not silently accepted."""
    text, _rows = _good()
    with pytest.raises(B.BundleLogRejected, match="P2BSEED"):
        B.load_verified("P2BSEED|atrPrevClose=123\n" + text)


def test_wrong_index_frame_is_rejected() -> None:
    text, _rows = _good(1799)
    broken = text.replace("|absfirst=1499|", "|absfirst=1500|", 1)
    with pytest.raises(B.BundleLogRejected, match="absfirst"):
        B.load_verified(broken)
    broken2 = text.replace("|cbc=1799|", "|cbc=1800|", 1)
    with pytest.raises(B.BundleLogRejected, match="confirmedBarCount"):
        B.load_verified(broken2)


def test_anchor_must_equal_last_context_bar() -> None:
    text, rows = _good()
    broken = text.replace(
        f"|anchor={rows[-1]['t']}|", f"|anchor={rows[-1]['t'] + 900000}|", 1
    )
    with pytest.raises(B.BundleLogRejected, match="anchor"):
        B.load_verified(broken)
