"""P6 real-data parity: the captured FXCM capture, replayed and compared.

WHAT THIS ASSERTS
-----------------
The whole closure claim, re-derived from artifacts rather than trusted:

1. every timeframe's raw candles LOCK to the atomic snapshot on all five
   identity dimensions -- rows, first time, last time, and both digests;
2. Python INDEPENDENTLY reproduces Pine's input digest from those rows, which is
   the non-tautological half of the lock: it proves the exported candles really
   are the data the digest covers, rather than two Pine variables agreeing with
   each other;
3. the production oracle, which never sees a Pine surface hash, produces the
   same five surface digests as Pine on all six timeframes -- thirty exact
   comparisons;
4. the global digest folded from the six per-timeframe digests matches.

WHY IT SKIPS RATHER THAN FAILS WITHOUT THE CAPTURE
---------------------------------------------------
`artifacts/` is gitignored, so a fresh clone has no capture. Skipping keeps the
suite honest for someone who has not taken one; it does not weaken the claim,
because the closure evidence records the digests independently.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Any

import pytest

_REPO = Path(__file__).resolve().parents[2]
CAPTURE = _REPO / "artifacts" / "p6_capture" / "atomic_all_raw_log.csv"


def _load(name: str, relpath: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, _REPO / relpath)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


LOG = _load("_p6_rd_log", "tests/parity_support/p6_atomic_capture_log.py")
DIG = _load("_p6_rd_digest", "tests/parity_support/p6_digest.py")

#: Frozen at closure. Recorded here so a future regression fails loudly rather
#: than silently re-basing onto whatever the code then produces.
GLOBAL_H1 = 74231825
GLOBAL_H2 = 124714621
CAPTURE_ID = "002c391ae9d625599e2f60ff57552b9c"
ANCHOR = 1788407100000

EXPECTED_ROWS = {
    "W1": 1250,
    "D1": 1250,
    "H4": 1250,
    "H1": 1250,
    "M15": 1799,
    "M5": 1250,
}

pytestmark = pytest.mark.skipif(
    not CAPTURE.exists(), reason=f"no P6 capture present: {CAPTURE.name}"
)


def _split_raw(text: str) -> dict[str, list[str]]:
    pending: dict[str, list[str]] = {}
    captures: dict[str, list[str]] = {}
    for _stamp, records in LOG.group_by_emission(text):
        for record in records:
            if record.startswith("P6RAW|"):
                pending.setdefault(record.split("|")[1], []).append(record)
            elif record.startswith("P6RAW_SUMMARY|"):
                timeframe = record.split("|")[1]
                block = "\n".join([*pending.pop(timeframe, []), record])
                captures.setdefault(timeframe, []).append(block)
    return captures


@pytest.fixture(scope="module")
def capture() -> Any:
    text = CAPTURE.read_text(encoding="utf-8")
    snapshot = LOG.latest_complete_snapshot(text)
    blocks = _split_raw(text)
    locked = {}
    for timeframe in LOG.REQUIRED_TIMEFRAMES:
        for block in reversed(blocks[timeframe]):
            raw = LOG.parse_raw(block)
            if LOG.raw_identity_matches(snapshot.timeframes[timeframe], raw).matched:
                locked[timeframe] = raw
                break
    return snapshot, locked


@pytest.fixture(scope="module")
def replayed(capture: Any) -> Any:
    replay = _load("_p6_rd_replay", "tests/parity_support/p6_real_data_replay.py")
    _snapshot, locked = capture
    return replay.replay_capture(locked)


# ---------------------------------------------------------------------------
# The capture itself
# ---------------------------------------------------------------------------


def test_the_capture_is_the_frozen_one(capture: Any) -> None:
    snapshot, _ = capture
    assert snapshot.capture_id == CAPTURE_ID
    assert snapshot.meta.anchor_time == ANCHOR
    assert snapshot.meta.feed == "FX:XAUUSD"
    assert snapshot.meta.alias_hits == 0


def test_the_envelopes_are_the_frozen_contract(capture: Any) -> None:
    snapshot, _ = capture
    assert snapshot.meta.semantic_minimum == 1250
    assert snapshot.meta.request_envelope == 1251
    assert snapshot.meta.host_envelope == 1800


def test_m15_carries_the_hosts_confirmed_history(capture: Any) -> None:
    """The dependency rule: M15 follows the host, not the request envelope."""
    snapshot, _ = capture
    assert snapshot.timeframes["M15"].semantic_rows == snapshot.meta.host_confirmed


@pytest.mark.parametrize("timeframe", list(LOG.REQUIRED_TIMEFRAMES))
def test_every_timeframe_meets_the_semantic_minimum(
    capture: Any, timeframe: str
) -> None:
    snapshot, _ = capture
    assert snapshot.timeframes[timeframe].semantic_rows >= 1250
    assert snapshot.timeframes[timeframe].semantic_rows == EXPECTED_ROWS[timeframe]


# ---------------------------------------------------------------------------
# Input identity, both halves
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("timeframe", list(LOG.REQUIRED_TIMEFRAMES))
def test_the_raw_capture_locks_on_all_five_dimensions(
    capture: Any, timeframe: str
) -> None:
    snapshot, locked = capture
    assert timeframe in locked, f"{timeframe}: no raw capture locked"
    result = LOG.raw_identity_matches(snapshot.timeframes[timeframe], locked[timeframe])
    assert result.matched, result.describe()


@pytest.mark.parametrize("timeframe", list(LOG.REQUIRED_TIMEFRAMES))
def test_python_independently_reproduces_the_input_digest(
    capture: Any, timeframe: str
) -> None:
    """The non-tautological half.

    The lock alone compares two values Pine produced. This recomputes the digest
    in Python from the exported rows, so it proves the candles handed to the
    oracle really are the ones the digest covers.
    """
    snapshot, locked = capture
    raw = locked[timeframe]
    records = [
        (
            DIG.encode_int(bar["time_ms"]),
            bar["open_enc"],
            bar["high_enc"],
            bar["low_enc"],
            bar["close_enc"],
            DIG.encode_int(bar["time_close_ms"]),
        )
        for bar in raw.bars
    ]
    snap = snapshot.timeframes[timeframe]
    assert DIG.hash_sequence(records, DIG.BASE1, DIG.MOD1) == snap.semantic_input_h1
    assert DIG.hash_sequence(records, DIG.BASE2, DIG.MOD2) == snap.semantic_input_h2


def test_the_decoded_prices_are_plausible_gold(capture: Any) -> None:
    """A guard against a silent encoding slip: the decode once doubled every
    price and still produced a self-consistent digest, because the digest folds
    the ENCODED form. Only a value check catches that."""
    _snapshot, locked = capture
    for timeframe, raw in locked.items():
        for bar in (raw.bars[0], raw.bars[-1]):
            price = bar["close_ticks"] * float(DIG.MINTICK)
            assert 100.0 < price < 10000.0, (timeframe, bar["ordinal"], price)


# ---------------------------------------------------------------------------
# The 30 comparisons
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("timeframe", list(LOG.REQUIRED_TIMEFRAMES))
@pytest.mark.parametrize("surface", list(DIG.SURFACE_ORDER))
def test_surface_digest_matches_pine(
    capture: Any, replayed: Any, timeframe: str, surface: str
) -> None:
    snapshot, _ = capture
    pine = snapshot.timeframes[timeframe].surfaces[surface]
    mine = replayed[timeframe].surfaces[surface]
    assert pine == mine, (
        f"{timeframe} {surface}: pine={pine} python={mine} "
        f"values={replayed[timeframe].values}"
    )


@pytest.mark.parametrize("timeframe", list(LOG.REQUIRED_TIMEFRAMES))
def test_combined_digest_matches_pine(
    capture: Any, replayed: Any, timeframe: str
) -> None:
    snapshot, _ = capture
    assert snapshot.timeframes[timeframe].combined == replayed[timeframe].combined


def test_the_global_digest_is_exact(capture: Any, replayed: Any) -> None:
    snapshot, _ = capture

    def fold(values: list[int], base: int, mod: int) -> int:
        return DIG.hash_sequence([(DIG.encode_int(v),) for v in values], base, mod)

    order = LOG.REQUIRED_TIMEFRAMES
    pine_h1 = fold([snapshot.timeframes[t].combined[0] for t in order], DIG.BASE1, DIG.MOD1)
    pine_h2 = fold([snapshot.timeframes[t].combined[1] for t in order], DIG.BASE2, DIG.MOD2)
    py_h1 = fold([replayed[t].combined[0] for t in order], DIG.BASE1, DIG.MOD1)
    py_h2 = fold([replayed[t].combined[1] for t in order], DIG.BASE2, DIG.MOD2)

    assert (pine_h1, pine_h2) == (py_h1, py_h2)
    assert (pine_h1, pine_h2) == (GLOBAL_H1, GLOBAL_H2)


def test_the_projections_are_non_vacuous(replayed: Any) -> None:
    """Thirty matching digests would prove nothing if every value were empty."""
    for timeframe, result in replayed.items():
        assert result.values["swing_count"] > 0, timeframe
        assert result.values["last_swing_price"] is not None, timeframe
        assert result.values["p2_direction"] in (0, 1, -1), timeframe


def test_the_timeframes_are_differentiated(replayed: Any) -> None:
    """And nothing would be proven if all six agreed by construction."""
    prices = {r.values["last_swing_price"] for r in replayed.values()}
    assert len(prices) == len(replayed)
