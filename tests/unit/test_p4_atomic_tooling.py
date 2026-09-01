"""P4 atomic probe: DEV equivalence, and a parser that refuses bad captures.

Two things have to hold before a real-data parity result means anything.

First, the probe must be the SAME ENGINE as the scanner. If the atomic build
could drift from P4 DEV, a parity pass would prove something about a program
nobody runs. The equivalence test asserts the probe is P4 DEV byte-for-byte
with only the title changed, plus an appended logging block that declares no
engine state and mutates no engine array.

Second, the parser must reject rather than repair. A harness that quietly
patched a missing row or a bad checksum could turn a broken capture into a
"match", which is the one failure mode a parity harness must not have. Each
corruption below is injected into a synthetic-but-valid bundle and must be
refused.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from tests.parity_support import p4_atomic_bundle_log as B
from tests.parity_support import p4_digest as G

REPO = Path(__file__).resolve().parents[2]
P4_DEV = REPO / "tradingview" / "btmm_poi_btrc_scanner_p4_dev.pine"
P4_ATOMIC = REPO / "tradingview" / "btmm_poi_btrc_scanner_p4_atomic_parity_bundle.pine"

DEV_TITLE = "BTMM + POI + BTRC Scanner [P4 DEV]"
ATOMIC_TITLE = "BTMM + POI + BTRC Scanner [P4 ATOMIC PARITY]"
PROBE_BANNER = "// P4 ATOMIC PARITY PROBE"


def _dev() -> str:
    return P4_DEV.read_text(encoding="utf-8")


def _atomic() -> str:
    return P4_ATOMIC.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# DEV <-> ATOMIC equivalence
# ---------------------------------------------------------------------------


def test_atomic_is_dev_plus_title_plus_probe_appendix() -> None:
    dev = _dev()
    atomic = _atomic()
    expected_prefix = dev.replace(
        f'indicator("{DEV_TITLE}"', f'indicator("{ATOMIC_TITLE}"', 1
    )
    assert atomic.startswith(expected_prefix), (
        "the atomic probe is NOT the DEV engine plus an appendix: the engine "
        "region differs, so a parity pass would not be about the scanner"
    )
    appendix = atomic[len(expected_prefix) :]
    assert PROBE_BANNER in appendix
    assert appendix.index(PROBE_BANNER) < 200, "appendix must open with its banner"


def _probe_appendix() -> str:
    dev = _dev()
    atomic = _atomic()
    prefix = dev.replace(f'indicator("{DEV_TITLE}"', f'indicator("{ATOMIC_TITLE}"', 1)
    return atomic[len(prefix) :]


def _code(text: str) -> str:
    return "\n".join(
        line for line in text.splitlines() if not line.strip().startswith("//")
    )


def test_probe_declares_no_engine_state() -> None:
    """Every variable the appendix declares is probe-local (p4b* / P4B* / P4P*).

    A probe that introduced engine state could change what it is measuring.
    """
    code = _code(_probe_appendix())
    declared = re.findall(
        r"^(?:var\s+)?(?:array<\w+>|int|float|bool|string)\s+(\w+)\s*=", code, re.M
    )
    for name in declared:
        assert name.startswith(("p4b", "P4B", "P4P")), name


def test_probe_mutates_no_engine_array() -> None:
    """Instrumentation reads; it never writes. Any array.set/push/remove on a
    non-probe array would make the measurement part of the thing measured."""
    code = _code(_probe_appendix())
    writes = re.findall(
        r"array\.(?:set|push|insert|remove|clear|shift|pop)\((\w+)", code
    )
    assert writes == [], writes


def test_probe_emits_the_frozen_field_count() -> None:
    """The Pine row and the Python contract must agree on how many fields a
    setup record has, or the parser would silently misalign columns."""
    code = _code(_probe_appendix())
    assigned = re.findall(r"^\s+int f(\d\d) = ", code, re.M)
    assert len(assigned) == len(G.BTMM_FIELD_ORDER) == B.STATE_FIELDS
    assert assigned == [f"{i:02d}" for i in range(len(G.BTMM_FIELD_ORDER))]


def test_probe_reads_the_evidence_channel_rather_than_asserting_it() -> None:
    """evidence_present is measured from btmmEvHas, so a build that had somehow
    acquired reviewed evidence cannot be replayed against the no-evidence
    oracle by accident."""
    code = _code(_probe_appendix())
    assert "array.get(btmmEvHas" in code
    assert "evidence_present=" in code


def test_atomic_has_no_security_or_strategy_calls() -> None:
    code = _code(_atomic())
    assert "request.security" not in code
    assert "strategy." not in code


# ---------------------------------------------------------------------------
# The parser refuses, and never repairs
# ---------------------------------------------------------------------------


def _enc(v: int) -> int:
    return 2 * v + 2 if v >= 0 else -2 * v + 1


def _step(acc: int, v: int, base: int, mod: int) -> int:
    return (acc * base + (v % mod)) % mod


def _bar_line(idx: int, t: int) -> tuple[str, int, int]:
    o, h, low, c, tc = 100 + idx, 105 + idx, 95 + idx, 102 + idx, t + 900000
    r1 = r2 = 0
    for v in (t, o, h, low, c, tc):
        r1 = _step(r1, _enc(v), B.BASE1, B.MOD1)
        r2 = _step(r2, _enc(v), B.BASE2, B.MOD2)
    line = (
        f"P4BRAW|idx={idx:04d}|t={t}|o={o}|h={h}|l={low}|c={c}|tc={tc}|r1={r1}|r2={r2}"
    )
    return line, r1, r2


def _state_line(i: int, primary: int, stage: int) -> tuple[str, int, int]:
    fields = [0] * B.STATE_FIELDS
    fields[0] = 1
    fields[1] = 1
    fields[2] = 10000 + i
    fields[3] = 10100 + i
    fields[4] = 1788000000000
    fields[5] = 1
    fields[6] = primary
    fields[7] = stage
    r1 = r2 = 0
    for v in fields:
        r1 = _step(r1, _enc(v), B.BASE1, B.MOD1)
        r2 = _step(r2, _enc(v), B.BASE2, B.MOD2)
    line = f"P4BSTATE|i={i:04d}|f={','.join(str(v) for v in fields)}|r1={r1}|r2={r2}"
    return line, r1, r2


def _bundle(n_bars: int = 120, n_setups: int = 3) -> str:
    lines: list[str] = []
    ctx1 = ctx2 = 0
    chunk1 = chunk2 = 0
    chunk_start = 0
    first_t = last_t = 0
    rows: list[tuple[int, int]] = []
    for idx in range(n_bars):
        t = 1788000000000 + idx * 900000
        line, r1, r2 = _bar_line(idx, t)
        lines.append(line)
        rows.append((r1, r2))
        if idx == 0:
            first_t = t
        last_t = t
        ctx1 = _step(ctx1, r1, B.BASE1, B.MOD1)
        ctx2 = _step(ctx2, r2, B.BASE2, B.MOD2)
        chunk1 = _step(chunk1, r1, B.BASE1, B.MOD1)
        chunk2 = _step(chunk2, r2, B.BASE2, B.MOD2)
        if idx % B.CHUNK_SIZE == B.CHUNK_SIZE - 1:
            lines.append(
                f"P4BCHUNK|start={idx - B.CHUNK_SIZE + 1:04d}|end={idx:04d}"
                f"|h1={chunk1}|h2={chunk2}"
            )
            chunk1 = chunk2 = 0
            chunk_start = idx + 1
    if chunk_start <= n_bars - 1:
        lines.append(
            f"P4BCHUNK|start={chunk_start:04d}|end={n_bars - 1:04d}"
            f"|h1={chunk1}|h2={chunk2}"
        )

    st1 = st2 = 0
    primaries = [5, 2, 5]
    stages = [6, 4, 6]
    for i in range(n_setups):
        line, r1, r2 = _state_line(i, primaries[i % 3], stages[i % 3])
        lines.append(line)
        st1 = _step(st1, r1, B.BASE1, B.MOD1)
        st2 = _step(st2, r2, B.BASE2, B.MOD2)

    counts = {5: 0, 2: 0}
    for i in range(n_setups):
        counts[primaries[i % 3]] = counts.get(primaries[i % 3], 0) + 1
    n_final = sum(1 for i in range(n_setups) if stages[i % 3] == 6)

    lines.append(
        "P4BMETA|schema=1|tf=15|sym=FX:XAUUSD"
        f"|anchor={last_t}|cbc={n_bars}|win=300|ctxn={n_bars}"
        f"|ctxfirst={first_t}|ctxlast={last_t}|mintick=0.01"
        f"|ctxh1={ctx1}|ctxh2={ctx2}|nsetup={n_setups}"
        f"|ncandidate=0|nforming={counts.get(2, 0)}|nblocked=0|nconfirmed=0"
        f"|ncancelled={counts.get(5, 0)}|nfinalgate={n_final}"
        f"|evidence_present=0|sth1={st1}|sth2={st2}"
        "|formationtf=1|supportedtf=1"
    )
    return "\n".join(lines)


def test_a_well_formed_bundle_verifies() -> None:
    parsed = B.load_verified(_bundle())
    assert len(parsed.bars) == 120
    assert len(parsed.states) == 3
    assert parsed.timeframe_period == "15"
    assert parsed.mintick == B.Decimal("0.01")


def test_missing_row_is_rejected() -> None:
    text = "\n".join(
        line for line in _bundle().splitlines() if "|idx=0007|" not in line
    )
    with pytest.raises(B.BundleLogRejected):
        B.load_verified(text)


def test_duplicate_row_is_rejected() -> None:
    lines = _bundle().splitlines()
    dup = next(x for x in lines if "|idx=0007|" in x)
    lines.insert(10, dup)
    with pytest.raises(B.BundleLogRejected):
        B.load_verified("\n".join(lines))


def test_out_of_order_rows_are_rejected() -> None:
    lines = _bundle().splitlines()
    raws = [i for i, x in enumerate(lines) if x.startswith("P4BRAW")]
    lines[raws[3]], lines[raws[9]] = lines[raws[9]], lines[raws[3]]
    with pytest.raises(B.BundleLogRejected):
        B.load_verified("\n".join(lines))


def test_bad_row_checksum_is_rejected() -> None:
    text = _bundle().replace("|c=102|", "|c=103|", 1)
    with pytest.raises(B.BundleLogRejected):
        B.load_verified(text)


def test_bad_chunk_checksum_is_rejected() -> None:
    text = re.sub(
        r"(P4BCHUNK\|start=0000\|end=0049\|h1=)(\d+)", r"\g<1>12345", _bundle()
    )
    with pytest.raises(B.BundleLogRejected):
        B.load_verified(text)


def test_bad_context_hash_is_rejected() -> None:
    text = re.sub(r"\|ctxh1=\d+", "|ctxh1=999", _bundle())
    with pytest.raises(B.BundleLogRejected):
        B.load_verified(text)


def test_missing_state_row_is_rejected() -> None:
    text = "\n".join(
        line for line in _bundle().splitlines() if "P4BSTATE|i=0001" not in line
    )
    with pytest.raises(B.BundleLogRejected):
        B.load_verified(text)


def test_bad_state_checksum_is_rejected() -> None:
    lines = _bundle().splitlines()
    for i, line in enumerate(lines):
        if line.startswith("P4BSTATE|i=0000"):
            lines[i] = line.replace("|f=1,1,", "|f=1,-1,", 1)
            break
    with pytest.raises(B.BundleLogRejected):
        B.load_verified("\n".join(lines))


def test_state_transport_hash_mismatch_is_rejected() -> None:
    text = re.sub(r"\|sth1=\d+", "|sth1=42", _bundle())
    with pytest.raises(B.BundleLogRejected):
        B.load_verified(text)


def test_declared_counts_must_agree_with_the_rows() -> None:
    text = re.sub(r"\|ncancelled=\d+", "|ncancelled=99", _bundle())
    with pytest.raises(B.BundleLogRejected):
        B.load_verified(text)


def test_a_capture_with_reviewed_evidence_is_refused() -> None:
    """The strongest gate: a bundle taken from a run that had reviewed evidence
    must never be replayed against the `reviewed_evidence=()` oracle."""
    text = _bundle().replace("|evidence_present=0", "|evidence_present=3")
    with pytest.raises(B.BundleLogRejected, match="no-evidence"):
        B.load_verified(text)


def test_two_meta_records_are_rejected() -> None:
    text = _bundle()
    text = text + "\n" + text.splitlines()[-1]
    with pytest.raises(B.BundleLogRejected):
        B.load_verified(text)


def test_missing_meta_is_rejected() -> None:
    text = "\n".join(x for x in _bundle().splitlines() if not x.startswith("P4BMETA"))
    with pytest.raises(B.BundleLogRejected):
        B.load_verified(text)


def test_forming_bundle_without_states_is_rejected() -> None:
    text = "\n".join(x for x in _bundle().splitlines() if not x.startswith("P4BSTATE"))
    with pytest.raises(B.BundleLogRejected):
        B.load_verified(text)


# ---------------------------------------------------------------------------
# The digest contract itself
# ---------------------------------------------------------------------------


def test_canonical_field_order_matches_the_probe_and_the_parser() -> None:
    assert len(G.BTMM_FIELD_ORDER) == B.STATE_FIELDS
    assert len(G.FIELD_NAMES) == len(set(G.FIELD_NAMES))


def test_every_field_belongs_to_exactly_one_group() -> None:
    """A field missing from every group would be hashed overall but never
    localised; a field in two groups would double-count."""
    seen: list[str] = []
    for names in G.GROUPS.values():
        seen.extend(names)
    assert sorted(seen) == sorted(G.FIELD_NAMES)


def test_the_evidence_surface_is_hashed_not_omitted() -> None:
    """These stay at their defaults in the no-evidence runtime. They are hashed
    anyway, so a change that started moving them has to change the digest."""
    for name in (
        "market_direction",
        "analytical_framework",
        "session",
        "volume",
        "liquidity_status",
        "reviewed_evidence_time",
    ):
        assert name in G.FIELD_NAMES
        assert name in G.GROUPS["evidence"]
