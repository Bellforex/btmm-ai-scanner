"""Contract tests for the P2 parity digest, and source guards on the probe.

Two jobs:

1. Pin the digest contract in Python (`tests/parity_support/p2_digest.py`) hard
   enough that it can be trusted as the reference for numbers read off a
   TradingView chart — including hand-calculated fixtures, so the implementation
   is checked against arithmetic rather than against itself.

2. Guard the isolation of `btmm_poi_btrc_scanner_p2_parity_probe.pine`: it must
   be a copy of the frozen production scanner plus an appendix, differing in
   exactly one production line (the title) and touching no P1/P2 analytics.
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
PRODUCTION = REPO / "tradingview" / "btmm_poi_btrc_scanner_v1.pine"
PROBE = REPO / "tradingview" / "btmm_poi_btrc_scanner_p2_parity_probe.pine"

PRODUCTION_SHA256 = "3d6d10df27e4150e6b693cb55bd32bb269478235eabfdf2fecd9aa23d96fa05b"
PRODUCTION_LINES = 2281

_SPEC = importlib.util.spec_from_file_location(
    "_p2_digest_ref", REPO / "tests" / "parity_support" / "p2_digest.py"
)
assert _SPEC is not None and _SPEC.loader is not None
D = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = D
_SPEC.loader.exec_module(D)

MINTICK = Decimal("0.01")


# ---------------------------------------------------------------------------
# Canonical encoding
# ---------------------------------------------------------------------------

def test_na_is_distinguishable_from_every_numeric_value() -> None:
    """The whole point of the encoding: NA must not collide with any real value."""
    assert D.encode_int(None) == 0
    for value in range(-500, 501):
        assert D.encode_int(value) != 0, value


def test_zero_and_minus_one_and_plus_one_stay_distinct() -> None:
    assert D.encode_int(None) == 0
    assert D.encode_int(0) == 2
    assert D.encode_int(-1) == 3
    assert D.encode_int(1) == 4
    assert len({D.encode_int(v) for v in (None, 0, -1, 1)}) == 4


def test_encoding_is_injective_over_a_wide_range() -> None:
    seen = {D.encode_int(None)}
    for value in range(-5000, 5001):
        encoded = D.encode_int(value)
        assert encoded not in seen, f"collision at {value}"
        seen.add(encoded)


def test_encoding_is_always_non_negative() -> None:
    """`v % MOD` must agree between Pine and Python, which it only does for
    non-negative operands."""
    for value in (-10**12, -99, -1, 0, 1, 10**12):
        assert D.encode_int(value) >= 0


def test_c_st_na_encodes_as_the_integer_minus_99_not_as_na() -> None:
    """C_ST_NA is a real sentinel integer on the Pine side, so it must NOT be
    collapsed into NA — otherwise 'never computed' and 'computed as absent'
    would hash identically."""
    assert D.C_ST_NA == -99
    assert D.encode_int(D.C_ST_NA) == 199
    assert D.encode_int(D.C_ST_NA) != D.encode_int(None)


# ---------------------------------------------------------------------------
# Price / time normalisation
# ---------------------------------------------------------------------------

def test_price_normalisation_is_deterministic_in_ticks() -> None:
    assert D.encode_price(Decimal("4650.07"), MINTICK) == D.encode_int(465007)
    assert D.encode_price(Decimal("0"), MINTICK) == D.encode_int(0)
    assert D.encode_price(Decimal("-1.23"), MINTICK) == D.encode_int(-123)
    assert D.encode_price(None, MINTICK) == 0


def test_price_rounding_is_ties_away_from_zero_not_bankers() -> None:
    """Python's built-in round() would give 2 for 2.5 and 2 for 1.5+0.5; Pine's
    math.round goes away from zero. The difference only bites on exact .5 tick
    boundaries, which is precisely where a silent parity bug would hide."""
    assert D.pine_round(Decimal("0.5")) == 1
    assert D.pine_round(Decimal("1.5")) == 2
    assert D.pine_round(Decimal("2.5")) == 3      # round() would say 2
    assert D.pine_round(Decimal("-0.5")) == -1
    assert D.pine_round(Decimal("-2.5")) == -3    # round() would say -2


def test_prices_one_tick_apart_never_collide() -> None:
    base = Decimal("4650.00")
    encoded = {
        D.encode_price(base + Decimal("0.01") * n, MINTICK) for n in range(1000)
    }
    assert len(encoded) == 1000


def test_epoch_milliseconds_are_deterministic_and_not_divided() -> None:
    ms = 1787595821689
    assert D.encode_int(ms) == 2 * ms + 2
    # One millisecond apart must differ — proving no truncation to seconds.
    assert D.encode_int(ms) != D.encode_int(ms + 1)


# ---------------------------------------------------------------------------
# Hand-calculated fixtures — arithmetic, not self-comparison
# ---------------------------------------------------------------------------

def test_single_record_hash_matches_hand_calculation() -> None:
    """records = [[encode(1)]] = [[4]].

    r = step(0, 4) = (0*BASE1 + 4) % MOD1 = 4
    h = step(0, 4) = 4
    """
    assert D.hash_sequence([[D.encode_int(1)]], D.BASE1, D.MOD1) == 4


def test_two_record_hash_matches_hand_calculation() -> None:
    """records = [[encode(1)], [encode(2)]] = [[4], [6]].

    r1 = 4 ; h = 4
    r2 = 6 ; h = (4 * 1000003 + 6) % 1000000007 = 4000018
    """
    expected = (4 * D.BASE1 + 6) % D.MOD1
    assert expected == 4000018
    assert D.hash_sequence(
        [[D.encode_int(1)], [D.encode_int(2)]], D.BASE1, D.MOD1
    ) == 4000018


def test_multi_field_record_matches_hand_calculation() -> None:
    """One record of two fields [encode(0), encode(-1)] = [2, 3].

    r = step(step(0, 2), 3) = ((0*B + 2) * B + 3) % M = (2B + 3) % M
    h = step(0, r) = r
    """
    expected = (2 * D.BASE1 + 3) % D.MOD1
    assert D.hash_sequence([[2, 3]], D.BASE1, D.MOD1) == expected
    assert expected == 2000009


# ---------------------------------------------------------------------------
# Sensitivity — the properties that make the digest worth trusting
# ---------------------------------------------------------------------------

def _records(n: int = 40) -> list[tuple[int, ...]]:
    return [
        D.encode_input_bar(
            time_ms=1_780_000_000_000 + i * 900_000,
            open_=Decimal("4600.00") + i,
            high=Decimal("4601.50") + i,
            low=Decimal("4599.25") + i,
            close=Decimal("4600.75") + i,
            time_close_ms=1_780_000_000_000 + (i + 1) * 900_000,
            mintick=MINTICK,
        )
        for i in range(n)
    ]


def test_reordering_records_changes_the_hash() -> None:
    records = _records()
    swapped = list(records)
    swapped[3], swapped[17] = swapped[17], swapped[3]
    assert D.input_hashes(records) != D.input_hashes(swapped)


def test_reversing_the_sequence_changes_the_hash() -> None:
    records = _records()
    assert D.input_hashes(records) != D.input_hashes(list(reversed(records)))


def test_mutating_a_single_value_changes_the_hash() -> None:
    records = _records()
    mutated = list(records)
    row = list(mutated[10])
    row[4] += 2                                   # one tick on close
    mutated[10] = tuple(row)
    assert D.input_hashes(records) != D.input_hashes(mutated)


def test_a_one_tick_price_change_changes_the_hash() -> None:
    a = [D.encode_input_bar(time_ms=1, open_=Decimal("4600.00"),
                            high=Decimal("4600.00"), low=Decimal("4600.00"),
                            close=Decimal("4600.00"), time_close_ms=2,
                            mintick=MINTICK)]
    b = [D.encode_input_bar(time_ms=1, open_=Decimal("4600.00"),
                            high=Decimal("4600.00"), low=Decimal("4600.00"),
                            close=Decimal("4600.01"), time_close_ms=2,
                            mintick=MINTICK)]
    assert D.input_hashes(a) != D.input_hashes(b)


def test_deleting_a_row_changes_the_hash() -> None:
    records = _records()
    assert D.input_hashes(records) != D.input_hashes(records[:-1])
    assert D.input_hashes(records) != D.input_hashes(records[1:])


def test_inserting_a_row_changes_the_hash() -> None:
    records = _records()
    inserted = list(records)
    inserted.insert(20, inserted[20])
    assert D.input_hashes(records) != D.input_hashes(inserted)


def test_the_two_moduli_are_independent() -> None:
    """A second (MOD, BASE) pair only adds confidence if it does not track the
    first."""
    records = _records()
    h1, h2 = D.input_hashes(records)
    assert h1 != h2
    mutated = list(records)
    row = list(mutated[5])
    row[3] += 2
    mutated[5] = tuple(row)
    m1, m2 = D.input_hashes(mutated)
    assert h1 != m1 and h2 != m2


def test_hashes_stay_inside_the_modulus() -> None:
    records = _records(200)
    for value in (*D.input_hashes(records), *D.state_hashes(records)):
        assert 0 <= value < max(D.MOD1, D.MOD2)


def test_mod_arithmetic_stays_within_int64() -> None:
    """Python has bignums; Pine does not. This proves the PINE side cannot
    overflow, which is why the moduli and bases were chosen as they are."""
    for mod, base in ((D.MOD1, D.BASE1), (D.MOD2, D.BASE2)):
        worst = (mod - 1) * base + (mod - 1)
        assert worst < D.INT64_MAX
        assert D.INT64_MAX / worst > 1000, "want a wide margin, not a squeak"
    # The largest real encoded operand is an epoch millisecond value.
    worst_operand = D.encode_int(4_102_444_800_000)       # year 2100
    assert (D.MOD1 - 1) * D.BASE1 + worst_operand < D.INT64_MAX


# ---------------------------------------------------------------------------
# State-record contract
# ---------------------------------------------------------------------------

def test_state_field_order_matches_the_fifteen_p2_outputs() -> None:
    names = [name for name, _kind, _absent in D.STATE_FIELD_ORDER]
    assert len(names) == 15
    assert names == [
        "adapted_swing_count", "last_pivot_start_abs", "last_conf_time",
        "relationship_count", "last_high_relationship", "last_low_relationship",
        "direction", "protected_high", "protected_low", "weak_high", "weak_low",
        "transition_count", "last_transition_code", "last_broken_key",
        "last_broken_level",
    ]


def test_exactly_one_state_field_is_a_price() -> None:
    prices = [n for n, kind, _a in D.STATE_FIELD_ORDER if kind == "PRICE"]
    assert prices == ["last_broken_level"], prices


def test_state_absence_conventions_match_the_pine_declarations() -> None:
    """Seven fields are `na`-seeded and eight use the C_ST_NA sentinel; the split is
    read off the production source, not guessed from names."""
    source = PRODUCTION.read_text(encoding="utf-8")
    na_seeded = {n for n, _k, absent in D.STATE_FIELD_ORDER if absent == "na"}
    sentinel = {n for n, _k, absent in D.STATE_FIELD_ORDER if absent == "C_ST_NA"}
    assert len(na_seeded) == 7 and len(sentinel) == 8
    # Spot-check both conventions against the real declarations.
    assert re.search(r"var int   p2SwingCount    = na", source)
    assert re.search(r"var int   p2Direction     = C_ST_NA", source)
    assert re.search(r"var float p2LastBrokenLvl = na", source)


def test_per_field_hashes_localise_a_single_field_mutation() -> None:
    """The reason the 15 hashes exist: one wrong field names itself."""
    base_values = {name: 1 for name, _k, _a in D.STATE_FIELD_ORDER}
    records = [D.encode_state_bar(base_values, MINTICK) for _ in range(20)]

    mutated_values = dict(base_values)
    mutated_values["weak_low"] = 7
    mutated = list(records)
    mutated[9] = D.encode_state_bar(mutated_values, MINTICK)

    before = D.per_field_hashes(records)
    after = D.per_field_hashes(mutated)
    differing = [k for k in before if before[k] != after[k]]
    assert differing == ["weak_low"], differing
    assert D.state_hashes(records) != D.state_hashes(mutated)


def test_absent_state_values_hash_differently_from_real_ones() -> None:
    present = {name: 0 for name, _k, _a in D.STATE_FIELD_ORDER}
    absent = {
        name: (None if a == "na" else D.C_ST_NA)
        for name, _k, a in D.STATE_FIELD_ORDER
    }
    assert D.encode_state_bar(present, MINTICK) != D.encode_state_bar(absent, MINTICK)


# ---------------------------------------------------------------------------
# Probe source guards
# ---------------------------------------------------------------------------

def test_production_pine_is_still_the_frozen_baseline() -> None:
    digest = hashlib.sha256(PRODUCTION.read_bytes()).hexdigest()
    assert digest == PRODUCTION_SHA256, "production Pine must not be edited"


def test_probe_is_production_plus_an_appendix() -> None:
    """The probe's first 2281 lines must equal production except the title."""
    prod = PRODUCTION.read_text(encoding="utf-8").splitlines()
    probe = PROBE.read_text(encoding="utf-8").splitlines()
    assert len(prod) == PRODUCTION_LINES
    assert len(probe) > PRODUCTION_LINES, "the probe must append instrumentation"

    head = probe[:PRODUCTION_LINES]
    differing = [i for i in range(PRODUCTION_LINES) if head[i] != prod[i]]
    assert len(differing) == 1, f"expected only the title to differ: {differing}"
    line = differing[0]
    assert prod[line].startswith("indicator(")
    assert '"BTMM + POI + BTRC Scanner [P2 DEV]"' in prod[line]
    assert '"BTMM + POI + BTRC Scanner [P2 PARITY PROBE]"' in head[line]


def test_probe_preserves_history_and_window_settings() -> None:
    text = PROBE.read_text(encoding="utf-8")
    assert "calc_bars_count = 1800" in text
    assert 'input.int(300, "Analytical window' in text
    assert "int C_P1_CALC_BARS     = 1800" in text


def test_probe_appendix_never_assigns_a_production_variable() -> None:
    """The appendix may READ p2* state; it must not write it, or the probe would
    stop being an observer."""
    text = PROBE.read_text(encoding="utf-8")
    appendix = text.split("P2 PARITY PROBE  ---  APPENDED INSTRUMENTATION ONLY")[1]
    code = "\n".join(
        ln for ln in appendix.splitlines() if not ln.strip().startswith("//")
    )
    forbidden = re.findall(r"\b(p2[A-Z]\w*)\s*:=", code)
    assert not forbidden, f"probe assigns production state: {forbidden}"
    for token in ("f_p2StructureWalk", "f_p2BuildRelationships", "f_detectSwings"):
        assert token not in code, f"probe must not re-run {token}"


def test_probe_outputs_are_data_window_only() -> None:
    text = PROBE.read_text(encoding="utf-8")
    probe_plots = [ln for ln in text.splitlines() if '"P2P_' in ln]
    assert len(probe_plots) == 27, len(probe_plots)
    for line in probe_plots:
        assert "display = display.data_window" in line, line
    appendix = text.split("P2 PARITY PROBE  ---  APPENDED INSTRUMENTATION ONLY")[1]
    for drawing in ("label.new", "box.new", "line.new", "table.new"):
        assert drawing not in appendix, f"probe must not draw: {drawing}"


def test_probe_plot_budget_is_under_the_tradingview_limit() -> None:
    text = PROBE.read_text(encoding="utf-8")
    total = sum(
        len(re.findall(rf"^\s*{fn}\(", text, re.M))
        for fn in ("plot", "plotshape", "plotchar", "plotarrow", "plotcandle",
                   "plotbar", "bgcolor", "barcolor", "fill", "hline")
    )
    assert total == 53, total
    assert total < 64, "RE10140 fires at 64"


def test_probe_collects_confirmed_bars_only_with_a_duplicate_guard() -> None:
    text = PROBE.read_text(encoding="utf-8")
    assert (
        "if barstate.isconfirmed and (na(p2pLastSeenTime) or time > p2pLastSeenTime)"
        in text
    )


def test_probe_constants_match_the_python_reference() -> None:
    text = PROBE.read_text(encoding="utf-8")
    assert f"int   P2P_MOD1  = {D.MOD1}" in text
    assert f"int   P2P_MOD2  = {D.MOD2}" in text
    assert f"int   P2P_BASE1 = {D.BASE1}" in text
    assert f"int   P2P_BASE2 = {D.BASE2}" in text
    assert f"int   P2P_SCHEMA_VERSION = {D.SCHEMA_VERSION}" in text
    assert f"int   P2P_INPUT_CAP = {D.INPUT_CAP}" in text
    assert f"int   P2P_STATE_CAP = {D.STATE_CAP}" in text


def test_probe_encoder_matches_the_python_reference_expression() -> None:
    text = PROBE.read_text(encoding="utf-8")
    assert "na(v) ? 0 : (v >= 0 ? 2 * v + 2 : -2 * v + 1)" in text
    assert "(acc * base + (v % mod)) % mod" in text
    assert "f_p2pEnc(int(math.round(p / syminfo.mintick)))" in text


@pytest.mark.parametrize(
    "name", [n for n, _k, _a in D.STATE_FIELD_ORDER]
)
def test_every_state_field_has_a_probe_hash_output(name: str) -> None:
    text = PROBE.read_text(encoding="utf-8")
    assert f'"P2P_H_{name}"' in text


def test_probe_state_record_uses_the_reference_field_order() -> None:
    """The order the appendix pushes fields in must equal STATE_FIELD_ORDER, or
    the two record hashes would disagree while every value matched."""
    text = PROBE.read_text(encoding="utf-8")
    pushed = re.findall(r"array\.push\(p2pS_(\w+),", text)
    assert pushed == [n for n, _k, _a in D.STATE_FIELD_ORDER], pushed
