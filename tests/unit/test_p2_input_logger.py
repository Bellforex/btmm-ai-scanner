"""Contract tests for the TradingView common-input logger and its parser.

Two halves:

1. **Parser integrity.** The 600 logged rows become the common input for a
   Python-vs-Pine comparison, so a single transposed digit would later surface as
   a fake Structure mismatch. Every corruption mode is asserted to be *rejected*,
   not repaired: bad digit, missing row, duplicate row, wrong order, bad chunk,
   wrong first/last, wrong window hash.

2. **Pine source guards.** The logger must stay a standalone read-only extraction
   tool — no P1/P2 logic, no drawings, no realtime emission — and its digest
   helpers must be byte-equivalent to the frozen parity probe.

`_emit()` below is a Python mirror of the Pine emission format. It exists so the
corruption cases are testable without a browser; the Pine source guards keep the
two formats pinned to each other.
"""

from __future__ import annotations

import importlib.util
import re
import sys
from decimal import Decimal
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
LOGGER = REPO / "tradingview" / "p2_m15_common_input_logger.pine"
PROBE = REPO / "tradingview" / "btmm_poi_btrc_scanner_p2_parity_probe.pine"
PRODUCTION = REPO / "tradingview" / "btmm_poi_btrc_scanner_v1.pine"


def _load(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(
        name, REPO / "tests" / "parity_support" / filename
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


D = _load("_p2ilog_digest", "p2_digest.py")
P = _load("_p2ilog_parser", "p2_input_log.py")

MINTICK = Decimal("0.01")
COUNT = P.EXPECTED_COUNT
CHUNK = P.CHUNK_SIZE


# ---------------------------------------------------------------------------
# A Python mirror of the Pine emission, used to build test fixtures
# ---------------------------------------------------------------------------

def _bars(n: int = COUNT) -> list[dict[str, int]]:
    """A synthetic window that starts and ends on the real snapshot anchors and
    contains a deliberate gap, so gap preservation is exercised."""
    step = 900_000                                   # 15 minutes in ms
    times: list[int] = []
    t = P.EXPECTED_FIRST_MS
    while len(times) < n - 1:
        times.append(t)
        t += step
        if len(times) == 300:                        # simulate a weekend gap
            t += 48 * 3600 * 1000
    times.append(P.EXPECTED_LAST_MS)
    assert len(times) == n

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


def _emit(rows: list[dict[str, int]], *, status: str = "OK") -> str:
    """Render rows exactly as the Pine logger does."""
    records = [_encoded(r) for r in rows]
    h1, h2 = D.input_hashes(records)
    lines = [
        f"P2META|schema=1|count={len(rows)}|first={rows[0]['t']}|last={rows[-1]['t']}"
        f"|mintick=0.01|h1={h1}|h2={h2}|status={status}"
    ]
    chunk: list[tuple[int, ...]] = []
    for row in rows:
        enc = _encoded(row)
        r1 = D.hash_record(enc, D.BASE1, D.MOD1)
        r2 = D.hash_record(enc, D.BASE2, D.MOD2)
        lines.append(
            f"P2RAW|i={row['i']:03d}|t={row['t']}|o={row['o']}|h={row['h']}"
            f"|l={row['l']}|c={row['c']}|tc={row['tc']}|r1={r1}|r2={r2}"
        )
        chunk.append(enc)
        if len(chunk) == CHUNK:
            start = row["i"] - CHUNK + 1
            lines.append(
                f"P2CHUNK|start={start:03d}|end={row['i']:03d}"
                f"|h1={D.hash_sequence(chunk, D.BASE1, D.MOD1)}"
                f"|h2={D.hash_sequence(chunk, D.BASE2, D.MOD2)}"
            )
            chunk = []
    return "\n".join(lines)


def _good() -> tuple[str, list[dict[str, int]], int, int]:
    rows = _bars()
    text = _emit(rows)
    h1, h2 = D.input_hashes([_encoded(r) for r in rows])
    return text, rows, h1, h2


def _verify(text: str, rows: list[dict[str, int]]) -> None:
    """Verify against the hashes this fixture actually produces."""
    h1, h2 = D.input_hashes([_encoded(r) for r in rows])
    P.verify(P.parse(text), expected_hash_1=h1, expected_hash_2=h2)


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------

def test_a_clean_export_parses_and_verifies() -> None:
    text, rows, h1, h2 = _good()
    parsed = P.parse(text)
    assert parsed.count == COUNT
    assert len(parsed.bars) == COUNT
    assert len(parsed.chunks) == COUNT // CHUNK == 12
    assert parsed.first_ms == P.EXPECTED_FIRST_MS
    assert parsed.last_ms == P.EXPECTED_LAST_MS
    assert parsed.mintick == MINTICK
    P.verify(parsed, expected_hash_1=h1, expected_hash_2=h2)
    del rows


def test_indices_are_exactly_zero_to_five_ninety_nine() -> None:
    text, rows, _h1, _h2 = _good()
    parsed = P.parse(text)
    assert [b.index for b in parsed.bars] == list(range(COUNT))
    del rows


def test_session_gaps_are_preserved_not_filled() -> None:
    """The fixture contains a 48h gap; the parser must accept it and must not
    require a uniform 15-minute spacing."""
    text, rows, _h1, _h2 = _good()
    parsed = P.parse(text)
    deltas = {
        b.time_ms - a.time_ms
        for a, b in zip(parsed.bars, parsed.bars[1:], strict=False)
    }
    assert len(deltas) > 1, "fixture must actually contain a gap"
    assert max(deltas) > 900_000
    _verify(text, rows)


def test_ohlc_reconstruction_from_ticks_is_exact() -> None:
    text, rows, _h1, _h2 = _good()
    parsed = P.parse(text)
    canonical = P.to_canonical_rows(parsed)
    assert len(canonical) == COUNT
    first = canonical[0]
    assert first["open"] == Decimal(rows[0]["o"]) * MINTICK
    assert first["high"] == Decimal(rows[0]["h"]) * MINTICK
    assert isinstance(first["open"], Decimal), "must stay Decimal, never float"
    assert first["time_ms"] == P.EXPECTED_FIRST_MS


# ---------------------------------------------------------------------------
# Corruption must be REJECTED, never repaired
# ---------------------------------------------------------------------------

def test_a_single_corrupted_digit_is_rejected() -> None:
    text, rows, _h1, _h2 = _good()
    broken = text.replace(f"|c={rows[7]['c']}|", f"|c={rows[7]['c'] + 1}|", 1)
    assert broken != text
    with pytest.raises(P.InputLogRejected, match="checksum mismatch"):
        _verify(broken, rows)


def test_a_corrupted_timestamp_digit_is_rejected() -> None:
    text, rows, _h1, _h2 = _good()
    victim = rows[123]
    broken = text.replace(f"|t={victim['t']}|", f"|t={victim['t'] + 1000}|", 1)
    with pytest.raises(P.InputLogRejected):
        _verify(broken, rows)


def test_a_missing_row_is_rejected() -> None:
    text, rows, _h1, _h2 = _good()
    lines = [ln for ln in text.splitlines() if "|i=250|" not in ln]
    with pytest.raises(P.InputLogRejected, match="expected 600 P2RAW rows"):
        _verify("\n".join(lines), rows)


def test_a_duplicated_row_is_rejected() -> None:
    text, rows, _h1, _h2 = _good()
    lines = text.splitlines()
    victim = next(ln for ln in lines if "|i=100|" in ln)
    lines.insert(lines.index(victim) + 1, victim)
    with pytest.raises(P.InputLogRejected):
        _verify("\n".join(lines), rows)


def test_out_of_order_rows_are_rejected() -> None:
    text, rows, _h1, _h2 = _good()
    lines = text.splitlines()
    a = next(i for i, ln in enumerate(lines) if "|i=010|" in ln)
    b = next(i for i, ln in enumerate(lines) if "|i=011|" in ln)
    lines[a], lines[b] = lines[b], lines[a]
    with pytest.raises(P.InputLogRejected, match="not exactly 0"):
        _verify("\n".join(lines), rows)


def test_a_bad_chunk_checksum_is_rejected() -> None:
    text, rows, _h1, _h2 = _good()
    parsed = P.parse(text)
    start, end, c1, c2 = parsed.chunks[3]
    broken = text.replace(
        f"P2CHUNK|start={start:03d}|end={end:03d}|h1={c1}|h2={c2}",
        f"P2CHUNK|start={start:03d}|end={end:03d}|h1={c1 + 1}|h2={c2}",
        1,
    )
    with pytest.raises(P.InputLogRejected, match="chunk .* hash 1 mismatch"):
        _verify(broken, rows)


def test_a_missing_chunk_line_is_rejected() -> None:
    text, rows, _h1, _h2 = _good()
    lines = [ln for ln in text.splitlines() if not ln.startswith("P2CHUNK|start=000")]
    with pytest.raises(P.InputLogRejected, match="expected 12 P2CHUNK"):
        _verify("\n".join(lines), rows)


def test_a_wrong_first_timestamp_is_rejected() -> None:
    rows = _bars()
    rows[0]["t"] = P.EXPECTED_FIRST_MS - 900_000
    text = _emit(rows)
    with pytest.raises(P.InputLogRejected, match="first timestamp"):
        _verify(text, rows)


def test_a_wrong_last_timestamp_is_rejected() -> None:
    rows = _bars()
    rows[-1]["t"] = P.EXPECTED_LAST_MS + 900_000
    rows[-1]["tc"] = rows[-1]["t"] + 900_000
    text = _emit(rows)
    with pytest.raises(P.InputLogRejected, match="last timestamp"):
        _verify(text, rows)


def test_a_window_hash_that_misses_the_probe_is_rejected() -> None:
    """The decisive gate: internally consistent data whose hashes do not equal
    the parity probe's is NOT a proven common input."""
    text, rows, _h1, _h2 = _good()
    parsed = P.parse(text)
    with pytest.raises(P.InputLogRejected, match="common input NOT proven"):
        P.verify(parsed, expected_hash_1=999, expected_hash_2=888)
    del rows


def test_a_mismatch_status_is_rejected_before_anything_else() -> None:
    rows = _bars()
    text = _emit(rows, status="MISMATCH")
    with pytest.raises(P.InputLogRejected, match="status=MISMATCH"):
        _verify(text, rows)


def test_missing_or_duplicated_metadata_is_rejected() -> None:
    text, rows, _h1, _h2 = _good()
    without = "\n".join(ln for ln in text.splitlines() if not ln.startswith("P2META"))
    with pytest.raises(P.InputLogRejected, match="exactly one P2META"):
        P.parse(without)
    doubled = text + "\n" + text.splitlines()[0]
    with pytest.raises(P.InputLogRejected, match="exactly one P2META"):
        P.parse(doubled)
    del rows


def test_metadata_disagreeing_with_rows_is_rejected() -> None:
    text, rows, _h1, _h2 = _good()
    broken = text.replace("|count=600|", "|count=599|", 1)
    with pytest.raises(P.InputLogRejected, match="disagrees"):
        _verify(broken, rows)


# ---------------------------------------------------------------------------
# Pine source guards
# ---------------------------------------------------------------------------

def test_logger_is_standalone_and_read_only() -> None:
    text = LOGGER.read_text(encoding="utf-8")
    code = "\n".join(
        ln for ln in text.splitlines() if not ln.strip().startswith("//")
    )
    for forbidden in (
        "strategy.", "request.", "alert(", "order", "f_p2StructureWalk",
        "f_detectSwings", "label.new", "box.new", "line.new", "table.new",
    ):
        assert forbidden not in code, f"logger must not contain {forbidden}"


def test_logger_digest_helpers_match_the_frozen_probe() -> None:
    text = LOGGER.read_text(encoding="utf-8")
    assert "na(v) ? 0 : (v >= 0 ? 2 * v + 2 : -2 * v + 1)" in text
    assert "(acc * base + (v % mod)) % mod" in text
    for constant, value in (
        ("MOD1", D.MOD1), ("MOD2", D.MOD2), ("BASE1", D.BASE1), ("BASE2", D.BASE2)
    ):
        assert re.search(rf"int {constant}\s*=\s*{value}\b", text), constant


def test_logger_collects_closed_bars_only_with_a_duplicate_guard() -> None:
    text = LOGGER.read_text(encoding="utf-8")
    assert (
        "if barstate.isconfirmed and time <= TARGET_LAST_MS "
        "and (na(p2lLastSeen) or time > p2lLastSeen)" in text
    )


def test_logger_emits_once_and_never_on_a_realtime_tick() -> None:
    text = LOGGER.read_text(encoding="utf-8")
    assert "if barstate.islastconfirmedhistory" in text
    code = "\n".join(
        ln for ln in text.splitlines() if not ln.strip().startswith("//")
    )
    assert "barstate.isrealtime" not in code
    assert "barstate.islast\n" not in code, "must be islastconfirmedhistory, not islast"


def test_logger_refuses_to_emit_rows_on_mismatch() -> None:
    """Phase 5: an apparently-valid dataset must never be produced from a window
    that does not reproduce the probe hashes."""
    text = LOGGER.read_text(encoding="utf-8")
    body = text.split("if not allOk")[1]
    fail_branch = body.split("else")[0]
    assert "P2FAIL" in fail_branch
    # Target the EMISSION CALL, not the word: the diagnostic message legitimately
    # contains the string "P2RAW".
    assert 'log.info("P2RAW' not in fail_branch, (
        "rows must not be emitted on the failure path"
    )
    assert "no P2RAW rows emitted" in fail_branch


def test_logger_prices_are_logged_as_integer_ticks() -> None:
    text = LOGGER.read_text(encoding="utf-8")
    for series in ("open", "high", "low", "close"):
        assert f"int(math.round({series}" in text.replace("  ", " "), series
    assert "syminfo.mintick" in text


def test_logger_field_order_matches_the_frozen_contract() -> None:
    """Row hashing must fold time, open, high, low, close, time_close in that
    order — a different order would hash differently while every value matched."""
    text = LOGGER.read_text(encoding="utf-8")
    block = text.split("// ---- pass 2")[1]
    order = re.findall(r"f_p2lEnc\((v[A-Z]+)\)", block)
    unique = list(dict.fromkeys(order))
    assert unique == ["vT", "vO", "vH", "vL", "vC", "vTC"], unique
    assert list(D.INPUT_FIELD_ORDER) == [
        "time", "open", "high", "low", "close", "time_close"
    ]


def test_production_and_probe_pine_are_untouched() -> None:
    import hashlib
    assert (
        hashlib.sha256(PRODUCTION.read_bytes()).hexdigest()
        == "3d6d10df27e4150e6b693cb55bd32bb269478235eabfdf2fecd9aa23d96fa05b"
    )
    assert (
        hashlib.sha256(PROBE.read_bytes()).hexdigest()
        == "17e6d56b5b31c5a8fa4fff4cd4f2f1caff22cbdfdd20917313e2c60c0608b749"
    )
