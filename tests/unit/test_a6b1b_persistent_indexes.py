"""A6-B1-B3 permanent tests: the transaction-safe (persistent) wake indexes.

The persistent interval-touch and breach indexes must (1) answer exactly as the
accepted mutable primitives and the brute-force oracles ``_touches_zone`` /
``_is_breach``, and (2) be genuinely persistent — an older index snapshot keeps
returning its original answers after later branches diverge, and a failed advance
(simulated by simply not publishing the new index) leaves the prior index
unchanged by object identity. These are the properties the transactional
scheduler relies on for rollback.
"""

import random
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

from btmm_ai_scanner.config.enums import InternalSymbol, Timeframe
from btmm_ai_scanner.contracts.normalized_candle import NormalizedCandle
from btmm_ai_scanner.contracts.raw_candle import CandleCompleteness, CandleVolumeKind
from btmm_ai_scanner.contracts.types import SemVer
from btmm_ai_scanner.poi.breach_index import (
    breach_wake_set,
    create_breach_index,
    register,
    unregister,
)
from btmm_ai_scanner.poi.configuration import PoiConfiguration
from btmm_ai_scanner.poi.enums import PoiDirection
from btmm_ai_scanner.poi.interval_index import IntervalTouchIndex
from btmm_ai_scanner.poi.lifecycle import _is_breach, _touches_zone, _zone_reference_atr
from btmm_ai_scanner.poi.persistent_breach_index import create_persistent_breach_index
from btmm_ai_scanner.poi.persistent_interval_index import (
    create_persistent_interval_index,
)

_CFG = PoiConfiguration(minimum_price_tick=Decimal("0.01"))
_AM = _CFG.zone_overshoot_tolerance_atr_multiplier
_HM = _CFG.zone_overshoot_tolerance_zone_height_multiplier
_MT = _CFG.minimum_price_tick


def _candle(o: str, h: str, low: str, c: str) -> NormalizedCandle:
    et = datetime(2026, 1, 1, tzinfo=UTC)
    av = et + timedelta(minutes=1)
    return NormalizedCandle.model_validate(
        {
            "record_id": UUID("0193f4b0-1234-7abc-8def-000000000001"),
            "content_fingerprint": "a" * 64,
            "raw_candle_id": UUID("0193f4b0-1234-7abc-8def-abcdefabcdaa"),
            "provider": "FXCM",
            "source_reference": "r",
            "source_symbol": InternalSymbol.XAUUSD.value,
            "source_timeframe": Timeframe.M1.value,
            "symbol": InternalSymbol.XAUUSD,
            "timeframe": Timeframe.M1,
            "event_time_utc": et,
            "availability_time_utc": av,
            "processing_time_utc": av,
            "original_event_time": et,
            "original_availability_time": av,
            "original_timezone": "UTC",
            "open": Decimal(o),
            "high": Decimal(h),
            "low": Decimal(low),
            "close": Decimal(c),
            "volume": Decimal("10"),
            "volume_kind": CandleVolumeKind.TICK,
            "completeness": CandleCompleteness.CONFIRMED_COMPLETE,
            "rule_version": SemVer.parse("0.1.0"),
            "contract_version": SemVer.parse("0.1.0"),
            "schema_version": SemVer.parse("0.1.0"),
            "provenance_id": UUID("0193f4b0-1234-7abc-8def-abcdefabcdff"),
        }
    )


def _rid(rng: random.Random) -> UUID:
    return UUID(int=rng.getrandbits(122) | (7 << 76))


# ---------------------------------------------------------------------------
# Persistent interval index vs brute force / accepted, plus persistence.
# ---------------------------------------------------------------------------


def test_persistent_touch_index_matches_bruteforce_and_accepted() -> None:
    fails = 0
    cases = 0
    for trial in range(400):
        rng = random.Random(trial)
        pidx = create_persistent_interval_index()
        acc = IntervalTouchIndex()
        zones: dict[UUID, tuple[Decimal, Decimal]] = {}
        for _ in range(rng.randint(1, 50)):
            r = rng.random()
            if r < 0.55 or not zones:
                rid = _rid(rng)
                style = rng.choice(["norm", "wide", "point", "dupband"])
                if style == "point":
                    v = Decimal(rng.randint(90, 110))
                    zb, zt = v, v
                elif style == "wide":
                    zb = Decimal(rng.randint(50, 90))
                    zt = Decimal(rng.randint(110, 150))
                elif style == "dupband":
                    zb, zt = Decimal("100"), Decimal("100.5")
                else:
                    cc = Decimal(f"{rng.uniform(95, 105):.2f}")
                    zb = cc
                    zt = cc + Decimal(f"{rng.uniform(0.01, 3):.2f}")
                if rid in zones:
                    continue
                pidx = pidx.insert(rid, zb, zt)
                acc.insert(rid, zb, zt)
                zones[rid] = (zb, zt)
            elif r < 0.75 and zones:
                rid = rng.choice(list(zones))
                zb, _zt = zones[rid]
                pidx = pidx.remove(rid, zb)
                acc.remove(rid)
                del zones[rid]
            else:
                qlo = Decimal(f"{rng.uniform(85, 115):.2f}")
                qhi = qlo + Decimal(f"{rng.uniform(0, 20):.2f}")
                candle = _candle(str(qlo), str(qhi), str(qlo), str(qhi))
                got = pidx.overlaps(qlo, qhi)
                exp = {
                    rid
                    for rid, (zb, zt) in zones.items()
                    if _touches_zone(candle, zt, zb)
                }
                cases += 1
                if got != exp or got != acc.overlaps(qlo, qhi):
                    fails += 1
            assert len(pidx) == len(zones)
    assert cases > 0
    assert fails == 0


def test_persistent_touch_index_is_persistent_under_branching() -> None:
    rng = random.Random(99)
    base = create_persistent_interval_index()
    zones: dict[UUID, tuple[Decimal, Decimal]] = {}
    for _ in range(40):
        rid = _rid(rng)
        zb = Decimal(rng.randint(90, 100))
        zt = zb + Decimal(rng.randint(1, 10))
        base = base.insert(rid, zb, zt)
        zones[rid] = (zb, zt)
    q = (Decimal("95"), Decimal("101"))
    base_answer = base.overlaps(*q)
    base_root = base._root
    # Branch A and branch B diverge from the same base.
    branch_a = base
    branch_b = base
    for rid, (zb, _zt) in list(zones.items())[:10]:
        branch_a = branch_a.remove(rid, zb)
    for _ in range(10):
        rid = _rid(rng)
        zb = Decimal(rng.randint(90, 100))
        branch_b = branch_b.insert(rid, zb, zb + Decimal("2"))
    # The original snapshot still answers exactly as before; its root object is
    # untouched.
    assert base.overlaps(*q) == base_answer
    assert base._root is base_root
    # And the branches genuinely differ from base and each other.
    assert branch_a.overlaps(*q) != base_answer or len(branch_a) != len(base)
    assert len(branch_b) == len(base) + 10


def test_persistent_touch_index_rollback_leaves_prior_unchanged() -> None:
    # A "failed advance" simply discards the new index; the prior one is the same
    # object with the same answers.
    idx = create_persistent_interval_index()
    r1 = UUID(int=1 | (7 << 76))
    idx = idx.insert(r1, Decimal("100"), Decimal("102"))
    before_root = idx._root
    before_answer = idx.overlaps(Decimal("101"), Decimal("101"))
    # Build a speculative next index, then "roll back" by not keeping it.
    r2 = UUID(int=2 | (7 << 76))
    _speculative = idx.insert(r2, Decimal("100"), Decimal("101"))
    assert idx._root is before_root
    assert idx.overlaps(Decimal("101"), Decimal("101")) == before_answer
    assert len(idx) == 1


# ---------------------------------------------------------------------------
# Persistent breach index vs brute force / accepted, plus persistence.
# ---------------------------------------------------------------------------


def _brute_breach(
    pois: list[tuple[UUID, PoiDirection, Decimal, Decimal]],
    candle: NormalizedCandle,
    atr: Decimal | None,
) -> set[UUID]:
    fallback = candle.high - candle.low
    ref = _zone_reference_atr([atr], 0, fallback)
    out: set[UUID] = set()
    for rid, direction, zt, zb in pois:
        zone_height = zt - zb
        bound_a = _AM * ref
        bound_b = _HM * zone_height if zone_height > 0 else bound_a
        overshoot = max(Decimal("2") * _MT, min(bound_a, bound_b))
        if _is_breach(candle, direction, zt, zb, overshoot):
            out.add(rid)
    return out


def test_persistent_breach_index_matches_bruteforce_and_accepted() -> None:
    fails = 0
    cases = 0
    for trial in range(300):
        rng = random.Random(7000 + trial)
        pindex = create_persistent_breach_index(_CFG)
        acc = create_breach_index(_CFG)
        pois: list[tuple[UUID, PoiDirection, Decimal, Decimal]] = []
        for _ in range(rng.randint(1, 40)):
            zc = rng.uniform(90, 110)
            zh = rng.uniform(0.01, 3.0)
            zt = Decimal(f"{zc + zh / 2:.2f}")
            zb = Decimal(f"{zc - zh / 2:.2f}")
            d = rng.choice([PoiDirection.BULLISH, PoiDirection.BEARISH])
            rid = _rid(rng)
            pindex = pindex.register(rid, d, zt, zb)
            register(acc, rid, d, zt, zb)
            pois.append((rid, d, zt, zb))
        # Randomly unregister a few.
        for rid, d, zt, zb in list(pois):
            if rng.random() < 0.2:
                pindex = pindex.unregister(rid, d, zt, zb)
                unregister(acc, rid)
                pois.remove((rid, d, zt, zb))
        for _ in range(8):
            c = rng.uniform(88, 112)
            o = c + rng.uniform(-2, 2)
            h = max(o, c) + rng.uniform(0, 1.5)
            low = min(o, c) - rng.uniform(0, 1.5)
            candle = _candle(f"{o:.2f}", f"{h:.2f}", f"{low:.2f}", f"{c:.2f}")
            atr = (
                Decimal(f"{rng.uniform(0.01, 4.0):.4f}")
                if rng.random() > 0.15
                else None
            )
            got = pindex.breach_wake_set(candle, atr)
            exp = _brute_breach(pois, candle, atr)
            cases += 1
            if got != exp or got != breach_wake_set(acc, candle, atr):
                fails += 1
    assert cases > 0
    assert fails == 0


def test_persistent_breach_index_is_persistent_under_branching() -> None:
    rng = random.Random(123)
    base = create_persistent_breach_index(_CFG)
    pois: list[tuple[UUID, PoiDirection, Decimal, Decimal]] = []
    for _ in range(30):
        zc = rng.uniform(95, 105)
        zt = Decimal(f"{zc + 0.5:.2f}")
        zb = Decimal(f"{zc - 0.5:.2f}")
        d = rng.choice([PoiDirection.BULLISH, PoiDirection.BEARISH])
        rid = _rid(rng)
        base = base.register(rid, d, zt, zb)
        pois.append((rid, d, zt, zb))
    candle = _candle("100.0", "100.3", "100.0", "100.0")
    atr = Decimal("1.0")
    base_answer = base.breach_wake_set(candle, atr)
    base_size = len(base)
    # Branch: unregister several, verify base still answers identically.
    branch = base
    for rid, d, zt, zb in pois[:8]:
        branch = branch.unregister(rid, d, zt, zb)
    assert base.breach_wake_set(candle, atr) == base_answer
    assert len(base) == base_size
    assert len(branch) == base_size - 8
