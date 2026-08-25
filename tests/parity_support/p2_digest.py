"""Python reference implementation of the P2 parity digest contract.

Test/tooling only — nothing in `src/` imports this, and it changes no production
semantics. It exists so the digests printed by
`tradingview/btmm_poi_btrc_scanner_p2_parity_probe.pine` can be reproduced
exactly from the Python oracle, turning a ~17,400-cell comparison into a handful
of integers.

THE CONTRACT (must stay byte-for-byte equivalent to the Pine appendix)
----------------------------------------------------------------------

Canonical encoding, applied to every field before it is hashed::

    na / None -> 0
    x >= 0    -> 2x + 2
    x <  0    -> -2x + 1

so NA, 0, -1, +1 map to 0, 2, 3, 4 — all distinct. `C_ST_NA` is simply the
integer -99 and encodes to 199; it is **not** collapsed into NA, because the two
mean different things and the Pine side keeps them apart.

Prices are converted to integer ticks first::

    round(price / mintick)      # ties away from zero, as Pine's math.round

which keeps binary floating point out of the parity contract entirely.

Times use raw epoch **milliseconds** through the integer encoding — never
stringified, never divided. (The probe's metadata plots divide by 1000 purely so
the Data Window stays readable; the hashes do not.)

Accumulation, shared by record and sequence hashing::

    step(acc, v) = (acc * BASE + (v % MOD)) % MOD

    record  : r = 0; for each field v in FIXED ORDER: r = step(r, v)
    sequence: h = 0; for each record r OLDEST -> NEWEST: h = step(h, r)

The sequence hash is order-sensitive by construction: swapping two records
changes `h` unless they are identical.

Overflow: the largest intermediate is `(MOD-1)*BASE + (MOD-1)` = 1.000034e15
against an int64 ceiling of 9.223372e18 — 9,223x of headroom. Python has
arbitrary-precision ints, so this bound exists to prove the *Pine* side is safe;
`test_mod_arithmetic_stays_within_int64` asserts it.
"""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal

MOD1 = 1000000007
BASE1 = 1000003
MOD2 = 1000000009
BASE2 = 1000033

INT64_MAX = 2**63 - 1

SCHEMA_VERSION = 1

INPUT_CAP = 600
STATE_CAP = 300

#: Raw-input record field order. Fixed, and mirrored exactly in the Pine
#: appendix. `open` does not reach P2 (it feeds displacement, a P1 output) but is
#: included so a feed difference in `open` cannot pass silently.
INPUT_FIELD_ORDER = ("time", "open", "high", "low", "close", "time_close")

#: P2 state record field order, and each field's canonical type. `PRICE` fields
#: go through tick normalisation; everything else is a plain integer/code/key.
#: `absent` records how that field spells "no value" on the Pine side, which is
#: what the caller must pass through as the encoder's input.
STATE_FIELD_ORDER: tuple[tuple[str, str, str], ...] = (
    ("adapted_swing_count",    "INTEGER",     "na"),
    ("last_pivot_start_abs",   "INTEGER",     "na"),
    ("last_conf_time",         "TIME_OR_KEY", "na"),
    ("relationship_count",     "INTEGER",     "na"),
    ("last_high_relationship", "CODE",        "na"),
    ("last_low_relationship",  "CODE",        "na"),
    ("direction",              "CODE",        "C_ST_NA"),
    ("protected_high",         "TIME_OR_KEY", "C_ST_NA"),
    ("protected_low",          "TIME_OR_KEY", "C_ST_NA"),
    ("weak_high",              "TIME_OR_KEY", "C_ST_NA"),
    ("weak_low",               "TIME_OR_KEY", "C_ST_NA"),
    ("transition_count",       "INTEGER",     "C_ST_NA"),
    ("last_transition_code",   "CODE",        "C_ST_NA"),
    ("last_broken_key",        "TIME_OR_KEY", "C_ST_NA"),
    ("last_broken_level",      "PRICE",       "na"),
)

C_ST_NA = -99


def pine_round(value: Decimal | float | int) -> int:
    """Pine's `math.round`: nearest integer, ties away from zero.

    Python's built-in `round` is banker's rounding and would disagree at exact
    `.5` tick boundaries, so it is deliberately not used.
    """
    quantised = Decimal(str(value)).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    return int(quantised)


def encode_int(value: int | None) -> int:
    """Canonical signed-integer encoding. `None` is Pine's `na`."""
    if value is None:
        return 0
    return 2 * value + 2 if value >= 0 else -2 * value + 1


def encode_price(price: Decimal | float | None, mintick: Decimal | float) -> int:
    """Price -> integer ticks -> canonical encoding."""
    if price is None:
        return 0
    ticks = pine_round(Decimal(str(price)) / Decimal(str(mintick)))
    return encode_int(ticks)


def step(acc: int, value: int, base: int, mod: int) -> int:
    """One accumulation step. `value` is always >= 0 thanks to the canonical
    encoding, so `%` never has to disagree between Pine and Python on sign."""
    return (acc * base + (value % mod)) % mod


def hash_record(fields: list[int] | tuple[int, ...], base: int, mod: int) -> int:
    """Hash one already-encoded record, in the caller's field order."""
    acc = 0
    for value in fields:
        acc = step(acc, value, base, mod)
    return acc


def hash_sequence(
    records: list[list[int]] | list[tuple[int, ...]], base: int, mod: int
) -> int:
    """Hash a sequence of encoded records, OLDEST -> NEWEST."""
    acc = 0
    for record in records:
        acc = step(acc, hash_record(record, base, mod), base, mod)
    return acc


def encode_input_bar(
    *,
    time_ms: int,
    open_: Decimal | float,
    high: Decimal | float,
    low: Decimal | float,
    close: Decimal | float,
    time_close_ms: int,
    mintick: Decimal | float,
) -> tuple[int, ...]:
    """One raw-input record, in `INPUT_FIELD_ORDER`."""
    return (
        encode_int(time_ms),
        encode_price(open_, mintick),
        encode_price(high, mintick),
        encode_price(low, mintick),
        encode_price(close, mintick),
        encode_int(time_close_ms),
    )


def encode_state_bar(
    values: dict[str, int | Decimal | float | None], mintick: Decimal | float
) -> tuple[int, ...]:
    """One P2 state record, in `STATE_FIELD_ORDER`.

    `values` is keyed by the short field names in `STATE_FIELD_ORDER`. Callers
    must pass the field's own "absent" spelling — `None` for the `na` fields and
    `C_ST_NA` for the sentinel ones — because the Pine side keeps them distinct.
    """
    encoded: list[int] = []
    for name, kind, _absent in STATE_FIELD_ORDER:
        raw = values[name]
        if kind == "PRICE":
            encoded.append(encode_price(raw, mintick))  # type: ignore[arg-type]
        else:
            encoded.append(encode_int(raw))  # type: ignore[arg-type]
    return tuple(encoded)


def input_hashes(records: list[tuple[int, ...]]) -> tuple[int, int]:
    """(P2P_INPUT_HASH_1, P2P_INPUT_HASH_2)."""
    return (
        hash_sequence(list(records), BASE1, MOD1),
        hash_sequence(list(records), BASE2, MOD2),
    )


def state_hashes(records: list[tuple[int, ...]]) -> tuple[int, int]:
    """(P2P_STATE_HASH_1, P2P_STATE_HASH_2)."""
    return (
        hash_sequence(list(records), BASE1, MOD1),
        hash_sequence(list(records), BASE2, MOD2),
    )


def per_field_hashes(records: list[tuple[int, ...]]) -> dict[str, int]:
    """The 15 localisation hashes, one per state field, all under MOD1.

    Mirrors the Pine loop: each field accumulates independently across bars, so a
    single mismatching field names the divergent semantic directly.
    """
    result: dict[str, int] = {}
    for index, (name, _kind, _absent) in enumerate(STATE_FIELD_ORDER):
        acc = 0
        for record in records:
            acc = step(acc, record[index], BASE1, MOD1)
        result[name] = acc
    return result
