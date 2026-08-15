"""A6-B1-B permanent tests: the exact wake-discovery index primitives.

Both indexes are validated against brute-force batch predicates
(``_touches_zone`` / ``_is_breach``) — the unchanged differential oracle — across
randomized insert/delete/query corpora with adversarial geometry and ATR
regimes. Zero false negatives; exact set equality.

These cover the B1-B1 (ZONE_TOUCH) and B1-B2 (BREACH) primitives. The
scheduler-gated-advancement wiring (B1-B5) and lazy CurrentPoiState (B1-B6) are
NOT yet integrated (see the A6-B1-B report).
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
)
from btmm_ai_scanner.poi.configuration import PoiConfiguration
from btmm_ai_scanner.poi.enums import PoiDirection
from btmm_ai_scanner.poi.interval_index import IntervalTouchIndex
from btmm_ai_scanner.poi.lifecycle import _is_breach, _touches_zone, _zone_reference_atr

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


# ---------------------------------------------------------------------------
# ZONE_TOUCH interval index vs brute-force _touches_zone.
# ---------------------------------------------------------------------------


def test_touch_index_matches_touches_zone_over_insert_delete_query() -> None:
    fails = 0
    cases = 0
    for trial in range(400):
        rng = random.Random(trial)
        idx = IntervalTouchIndex()
        zones: dict[UUID, tuple[Decimal, Decimal]] = {}
        for _ in range(rng.randint(1, 50)):
            r = rng.random()
            if r < 0.55 or not zones:
                rid = UUID(int=rng.getrandbits(122) | (7 << 76))
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
                    c = Decimal(f"{rng.uniform(95, 105):.2f}")
                    zb = c
                    zt = c + Decimal(f"{rng.uniform(0.01, 3):.2f}")
                idx.insert(rid, zb, zt)
                zones[rid] = (zb, zt)
            elif r < 0.75 and zones:
                rid = rng.choice(list(zones))
                idx.remove(rid)
                del zones[rid]
            else:
                qlo = Decimal(f"{rng.uniform(85, 115):.2f}")
                qhi = qlo + Decimal(f"{rng.uniform(0, 20):.2f}")
                candle = _candle(str(qlo), str(qhi), str(qlo), str(qhi))
                got = idx.overlaps(qlo, qhi)
                exp = {
                    rid
                    for rid, (zb, zt) in zones.items()
                    if _touches_zone(candle, zt, zb)
                }
                cases += 1
                if got != exp:
                    fails += 1
    assert cases > 0
    assert fails == 0


def test_touch_index_huge_and_empty_span() -> None:
    idx = IntervalTouchIndex()
    zones: dict[UUID, tuple[Decimal, Decimal]] = {}
    for i in range(200):
        rid = UUID(int=(i + 1) | (7 << 76))
        zb = Decimal(i)
        zt = zb + Decimal("0.5")
        idx.insert(rid, zb, zt)
        zones[rid] = (zb, zt)
    # Huge candle spanning all zones: W == P (output-sensitive, allowed).
    assert idx.overlaps(Decimal("-1000"), Decimal("1000")) == set(zones)
    # Gap candle spanning none.
    assert idx.overlaps(Decimal("1e6"), Decimal("2e6")) == set()
    # Point query hitting exactly the zones covering that price.
    got = idx.overlaps(Decimal("50.25"), Decimal("50.25"))
    exp = {rid for rid, (zb, zt) in zones.items() if zb <= Decimal("50.25") <= zt}
    assert got == exp


# ---------------------------------------------------------------------------
# BREACH index vs brute-force _is_breach.
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


def test_breach_index_matches_is_breach_randomized() -> None:
    fails = 0
    cases = 0
    for trial in range(300):
        rng = random.Random(5000 + trial)
        index = create_breach_index(_CFG)
        pois: list[tuple[UUID, PoiDirection, Decimal, Decimal]] = []
        for _ in range(rng.randint(1, 40)):
            zc = rng.uniform(90, 110)
            zh = rng.uniform(0.01, 3.0)
            zt = Decimal(f"{zc + zh / 2:.2f}")
            zb = Decimal(f"{zc - zh / 2:.2f}")
            d = rng.choice([PoiDirection.BULLISH, PoiDirection.BEARISH])
            rid = UUID(int=rng.getrandbits(122) | (7 << 76))
            register(index, rid, d, zt, zb)
            pois.append((rid, d, zt, zb))
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
            got = breach_wake_set(index, candle, atr)
            exp = _brute_breach(pois, candle, atr)
            cases += 1
            if got != exp:
                fails += 1
    assert cases > 0
    assert fails == 0


def test_breach_index_regime_and_min_tick_boundaries() -> None:
    # Construct exact boundary cases: hm*zone_height == am*ATR, am*ATR == 2*mt,
    # and just above/below, for both directions.
    index = create_breach_index(_CFG)
    pois: list[tuple[UUID, PoiDirection, Decimal, Decimal]] = []
    # A zone whose hm*H equals am*ATR at ATR=1.0: hm*H = am*1 => H = am/hm.
    h_eq = _AM / _HM  # zone height where hm*H == am*ATR at ATR=1
    for k, mult in enumerate(
        [
            Decimal("0.5"),
            Decimal("0.999"),
            Decimal("1.0"),
            Decimal("1.001"),
            Decimal("2"),
        ]
    ):
        zh = h_eq * mult
        for d in (PoiDirection.BULLISH, PoiDirection.BEARISH):
            zb = Decimal("100")
            zt = zb + zh
            rid = UUID(
                int=(k * 10 + (0 if d == PoiDirection.BULLISH else 1) + 1) | (7 << 76)
            )
            register(index, rid, d, zt, zb)
            pois.append((rid, d, zt, zb))
    for atr in [None, Decimal("1.0"), _MT, _MT * 2, Decimal("0.001"), Decimal("10")]:
        for close in ["96.0", "99.0", "100.0", "101.0", "104.0", "108.0"]:
            candle = _candle(close, str(Decimal(close) + Decimal("0.3")), close, close)
            assert breach_wake_set(index, candle, atr) == _brute_breach(
                pois, candle, atr
            )
