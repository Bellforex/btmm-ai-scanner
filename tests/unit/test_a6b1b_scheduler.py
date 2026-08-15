"""A6-B1-B4/B5/B6 permanent tests: the event-driven POI lifecycle scheduler.

The scheduler drives cursors from indexed wake events instead of advancing every
cursor every candle. Correctness is proven by an every-prefix differential against
a brute-force reference that rebuilds each present POI's cursor from its own
history (``feed_from_0``): the scheduler's lazily-materialized cursor must be
byte-identical for every POI at every prefix. A separate check proves zero wake
false-negatives (any POI whose semantic cursor state changes on a candle is in the
scheduler's woken set), plus dedicated no-interaction, huge-candle, reference
mutation, persistence and rollback cases.
"""

import random
from dataclasses import asdict
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

from btmm_ai_scanner.config.enums import InternalSymbol, Timeframe
from btmm_ai_scanner.contracts.normalized_candle import NormalizedCandle
from btmm_ai_scanner.contracts.raw_candle import CandleCompleteness, CandleVolumeKind
from btmm_ai_scanner.contracts.types import SemVer
from btmm_ai_scanner.poi.configuration import PoiConfiguration
from btmm_ai_scanner.poi.enums import PoiDirection
from btmm_ai_scanner.poi.lifecycle_cursor import (
    PoiLifecycleCursor,
    advance_poi_cursor,
    create_poi_lifecycle_cursor,
)
from btmm_ai_scanner.poi.lifecycle_scheduler import (
    PoiEventScheduler,
    PoiSpec,
    advance_scheduler,
    create_scheduler,
)

_CFG = PoiConfiguration(minimum_price_tick=Decimal("0.01"))
_BASE = datetime(2026, 1, 1, tzinfo=UTC)


def _u7(a: int, b: int) -> UUID:
    return UUID(int=(7 << 76) | (0b10 << 62) | ((a & 0xFFFFFFF) << 80) | (b & 0xFFF))


def _candle(index: int, o: float, h: float, low: float, c: float) -> NormalizedCandle:
    et = _BASE + timedelta(minutes=index)
    av = et + timedelta(minutes=1)
    return NormalizedCandle.model_validate(
        {
            "record_id": _u7(index + 1, 1),
            "content_fingerprint": "a" * 64,
            "raw_candle_id": _u7(index + 1, 2),
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
            "open": Decimal(f"{o:.2f}"),
            "high": Decimal(f"{h:.2f}"),
            "low": Decimal(f"{low:.2f}"),
            "close": Decimal(f"{c:.2f}"),
            "volume": Decimal("10"),
            "volume_kind": CandleVolumeKind.TICK,
            "completeness": CandleCompleteness.CONFIRMED_COMPLETE,
            "rule_version": SemVer.parse("0.1.0"),
            "contract_version": SemVer.parse("0.1.0"),
            "schema_version": SemVer.parse("0.1.0"),
            "provenance_id": _u7(index + 1, 3),
        }
    )


def _random_candle(rng: random.Random, index: int) -> NormalizedCandle:
    c = rng.uniform(90, 110)
    o = c + rng.uniform(-3, 3)
    h = max(o, c) + rng.uniform(0, 2)
    low = min(o, c) - rng.uniform(0, 2)
    return _candle(index, o, h, low, c)


def _feed_from_0(
    spec: PoiSpec, candles: list[NormalizedCandle], atrs: list[Decimal | None]
) -> PoiLifecycleCursor:
    cursor = create_poi_lifecycle_cursor(
        spec.symbol,
        spec.timeframe,
        spec.record_id,
        spec.direction,
        spec.zone_top,
        spec.zone_bottom,
        spec.availability_time_utc,
    )
    for i in range(len(candles)):
        cursor, _ = advance_poi_cursor(cursor, candles[i], atrs[i], _CFG)
    return cursor


def _spec(
    rng: random.Random, seed: int, appear_index: int, candles: list[NormalizedCandle]
) -> PoiSpec:
    center = rng.uniform(92, 108)
    height = rng.uniform(0.2, 2.5)
    zt = Decimal(f"{center + height / 2:.2f}")
    zb = Decimal(f"{center - height / 2:.2f}")
    direction = rng.choice([PoiDirection.BULLISH, PoiDirection.BEARISH])
    return PoiSpec(
        record_id=_u7(100000 + seed, 9),
        symbol=InternalSymbol.XAUUSD,
        timeframe=Timeframe.M1,
        direction=direction,
        zone_top=zt,
        zone_bottom=zb,
        availability_time_utc=candles[appear_index].availability_time_utc,
    )


_SEMANTIC = (
    "start_index",
    "tap_count",
    "in_tap",
    "resume_status",
    "committed_transitions",
    "terminal",
)


def _semantic(cursor: PoiLifecycleCursor) -> tuple[object, ...]:
    d = asdict(cursor)
    return tuple(d[k] for k in _SEMANTIC)


def _materialized_dict(
    scheduler: PoiEventScheduler, record_id: UUID
) -> dict[str, object]:
    cursor = scheduler.materialize_cursor(record_id)
    assert cursor is not None
    return asdict(cursor)


def test_scheduler_matches_bruteforce_every_prefix() -> None:
    total_prefix_checks = 0
    for trial in range(12):
        rng = random.Random(4000 + trial)
        n = rng.randint(30, 70)
        candles = [_random_candle(rng, i) for i in range(n)]
        atrs: list[Decimal | None] = [
            (Decimal(f"{rng.uniform(0.2, 3.0):.4f}") if rng.random() > 0.1 else None)
            for _ in range(n)
        ]

        # Plan a POI universe: appearance, optional change, optional removal.
        pcount = rng.randint(1, 12)
        plans = []
        for s in range(pcount):
            appear = rng.randint(0, n - 2)
            base_spec = _spec(rng, s, appear, candles)
            change_at = None
            changed_spec = None
            if rng.random() < 0.35:
                change_at = rng.randint(appear + 1, n - 1)
                changed_spec = _spec(rng, 1000 + s, appear, candles)
                changed_spec = PoiSpec(
                    record_id=base_spec.record_id,
                    symbol=base_spec.symbol,
                    timeframe=base_spec.timeframe,
                    direction=changed_spec.direction,
                    zone_top=changed_spec.zone_top,
                    zone_bottom=changed_spec.zone_bottom,
                    availability_time_utc=base_spec.availability_time_utc,
                )
            remove_at = None
            if rng.random() < 0.2:
                lo = (change_at or appear) + 1
                if lo <= n - 1:
                    remove_at = rng.randint(lo, n - 1)
            plans.append((base_spec, appear, change_at, changed_spec, remove_at))

        scheduler = create_scheduler(_CFG)
        # current spec per still-present POI
        present: dict[UUID, PoiSpec] = {}
        reference_prev: dict[UUID, PoiLifecycleCursor] = {}

        for m in range(n):
            new_pois: list[PoiSpec] = []
            changed_pois: list[PoiSpec] = []
            removed_ids: list[UUID] = []
            for base_spec, appear, change_at, changed_spec, remove_at in plans:
                rid = base_spec.record_id
                if remove_at == m and rid in present:
                    removed_ids.append(rid)
                    continue
                if appear == m:
                    new_pois.append(base_spec)
                elif change_at == m and rid in present:
                    assert changed_spec is not None
                    changed_pois.append(changed_spec)

            scheduler = advance_scheduler(
                scheduler,
                candles[: m + 1],
                atrs[: m + 1],
                new_pois=new_pois,
                changed_pois=changed_pois,
                removed_ids=removed_ids,
            )

            # Update the present map.
            for rid in removed_ids:
                present.pop(rid, None)
                reference_prev.pop(rid, None)
            for spec in new_pois:
                present[spec.record_id] = spec
            for spec in changed_pois:
                present[spec.record_id] = spec

            # Differential: every present POI's materialized cursor matches the
            # brute-force feed-from-0 reference exactly.
            for rid, spec in present.items():
                reference = _feed_from_0(spec, candles[: m + 1], atrs[: m + 1])
                materialized = scheduler.materialize_cursor(rid)
                assert materialized is not None
                assert asdict(materialized) == asdict(reference), (
                    f"trial={trial} m={m} rid mismatch"
                )
                # Zero false negatives: if the POI's semantic state changed vs the
                # previous prefix, it must have been woken (advanced) this candle.
                prev = reference_prev.get(rid)
                if prev is not None and _semantic(prev) != _semantic(reference):
                    # A change means the scheduler must have advanced it: its stored
                    # (non-materialized) cursor is now at the head.
                    stored = scheduler.cursors.get(rid.int)
                    assert stored is not None
                    assert stored.total_count == m + 1, (
                        f"false negative: rid changed but not woken at m={m}"
                    )
                reference_prev[rid] = reference
                total_prefix_checks += 1

            # Removed POIs are gone.
            for rid in removed_ids:
                assert scheduler.materialize_cursor(rid) is None

    assert total_prefix_checks > 0


def test_scheduler_no_interaction_advances_nothing() -> None:
    # Many scanning POIs whose zones sit far below a stream of high candles that
    # never touch or breach them: after each POI has started, subsequent
    # non-interacting candles must wake and advance nobody.
    n = 61
    # Candles far ABOVE all zones (zones live near 100; candles near 500).
    candles = [_candle(i, 500.0, 501.0, 499.5, 500.0) for i in range(n)]
    atrs: list[Decimal | None] = [Decimal("1.0")] * n

    scheduler = create_scheduler(_CFG)
    specs = []
    for s in range(15):
        center = 100 + s
        specs.append(
            PoiSpec(
                record_id=_u7(200000 + s, 9),
                symbol=InternalSymbol.XAUUSD,
                timeframe=Timeframe.M1,
                direction=PoiDirection.BULLISH,
                zone_top=Decimal(f"{center + 0.5:.2f}"),
                zone_bottom=Decimal(f"{center - 0.5:.2f}"),
                availability_time_utc=candles[0].availability_time_utc,
            )
        )

    # Advance through all but the last candle to let every POI start; then verify
    # the final (still non-interacting) advance wakes and rebuilds nobody.
    for m in range(n - 1):
        new_pois = specs if m == 0 else []
        scheduler = advance_scheduler(
            scheduler, candles[: m + 1], atrs[: m + 1], new_pois=new_pois
        )
    scheduler_last = advance_scheduler(scheduler, candles, atrs)
    assert scheduler_last.woken_ids == frozenset()
    assert scheduler_last.rebuilt == 0
    # And every POI is still exact vs brute force.
    for spec in specs:
        reference = _feed_from_0(spec, candles, atrs)
        assert _materialized_dict(scheduler_last, spec.record_id) == asdict(reference)


def test_scheduler_huge_candle_wakes_all_touched() -> None:
    # Many scanning POIs; then one huge candle spanning all their zones must wake
    # (and exactly reproduce) every one of them. W == P is legitimate here.
    n = 8
    scheduler = create_scheduler(_CFG)
    specs = []
    for s in range(20):
        center = 95 + s * 0.5
        specs.append(
            PoiSpec(
                record_id=_u7(300000 + s, 9),
                symbol=InternalSymbol.XAUUSD,
                timeframe=Timeframe.M1,
                direction=PoiDirection.BULLISH,
                zone_top=Decimal(f"{center + 0.3:.2f}"),
                zone_bottom=Decimal(f"{center - 0.3:.2f}"),
                availability_time_utc=_BASE,
            )
        )
    # Warmup candles above the zones (start the cursors without touching).
    candles = [_candle(i, 200.0, 201.0, 199.5, 200.0) for i in range(n)]
    atrs: list[Decimal | None] = [Decimal("1.0")] * n
    # Huge final candle spanning everything.
    candles.append(_candle(n, 90.0, 130.0, 80.0, 100.0))
    atrs.append(Decimal("1.0"))

    for m in range(n + 1):
        new_pois = specs if m == 0 else []
        scheduler = advance_scheduler(
            scheduler, candles[: m + 1], atrs[: m + 1], new_pois=new_pois
        )

    # The huge candle touched every zone => every POI woken and exact.
    assert scheduler.woken_ids == {s.record_id for s in specs}
    for spec in specs:
        reference = _feed_from_0(spec, candles, atrs)
        assert _materialized_dict(scheduler, spec.record_id) == asdict(reference)


def test_scheduler_terminal_poi_still_taps_via_touch_index() -> None:
    # A POI that has gone terminal (GENUINE_INVALIDATION) must stay registered in
    # the TOUCH index: the batch oracle keeps counting taps after terminal. So a
    # candle that touches the zone after invalidation must still wake the POI and
    # increment its tap_count — proving §7's "terminal register nowhere" would be
    # wrong. Pinned here permanently.
    spec = PoiSpec(
        record_id=_u7(600000, 9),
        symbol=InternalSymbol.XAUUSD,
        timeframe=Timeframe.M1,
        direction=PoiDirection.BULLISH,
        zone_top=Decimal("101.0"),
        zone_bottom=Decimal("99.0"),
        availability_time_utc=_BASE,
    )
    # 0: far-above (starts the cursor, no touch/breach). 1..4: strong bullish
    # breaches (close 90, high 91 < 99 so they do NOT touch) => terminal at 4.
    # 5: a candle straddling the zone => touches (first tap), AFTER terminal.
    candles = [_candle(0, 200.0, 201.0, 199.5, 200.0)]
    candles += [_candle(i, 90.0, 91.0, 89.0, 90.0) for i in range(1, 5)]
    candles.append(_candle(5, 99.5, 100.5, 98.5, 99.5))
    atrs: list[Decimal | None] = [Decimal("1.0")] * len(candles)

    scheduler = create_scheduler(_CFG)
    for m in range(len(candles)):
        scheduler = advance_scheduler(
            scheduler,
            candles[: m + 1],
            atrs[: m + 1],
            new_pois=[spec] if m == 0 else [],
        )
        if m == 4:
            mid = scheduler.materialize_cursor(spec.record_id)
            assert mid is not None and mid.terminal is True
            assert mid.tap_count == 0  # breaches did not touch the zone
        if m == 5:
            # The post-terminal touching candle must have woken the POI...
            assert spec.record_id in scheduler.woken_ids
            after = scheduler.materialize_cursor(spec.record_id)
            assert after is not None and after.terminal is True
            # ...and incremented its tap, exactly as the batch oracle does.
            assert after.tap_count == 1

    reference = _feed_from_0(spec, candles, atrs)
    assert _materialized_dict(scheduler, spec.record_id) == asdict(reference)
    assert reference.terminal is True
    assert reference.tap_count == 1


def test_scheduler_persistence_and_rollback() -> None:
    n = 6
    rng = random.Random(777)
    candles = [_random_candle(rng, i) for i in range(n + 1)]
    atrs: list[Decimal | None] = [Decimal("1.0")] * (n + 1)
    spec = PoiSpec(
        record_id=_u7(400000, 9),
        symbol=InternalSymbol.XAUUSD,
        timeframe=Timeframe.M1,
        direction=PoiDirection.BULLISH,
        zone_top=Decimal("101.0"),
        zone_bottom=Decimal("99.0"),
        availability_time_utc=candles[0].availability_time_utc,
    )
    scheduler = create_scheduler(_CFG)
    for m in range(n):
        scheduler = advance_scheduler(
            scheduler,
            candles[: m + 1],
            atrs[: m + 1],
            new_pois=[spec] if m == 0 else [],
        )
    published = scheduler
    published_total = published.total_count
    published_cursor = _materialized_dict(published, spec.record_id)

    # A "failed advance": wrong candles length (too short) raises; the published
    # scheduler is untouched and identical by object identity.
    try:
        advance_scheduler(published, candles[:n], atrs[:n])
    except ValueError:
        pass
    else:
        raise AssertionError("expected the mismatched advance to raise")
    # Its own fields are unchanged (persistent structures were never mutated).
    assert scheduler is published
    assert published.total_count == published_total
    assert _materialized_dict(published, spec.record_id) == published_cursor
    # A real next advance branches from the SAME published scheduler without
    # disturbing it.
    nxt = advance_scheduler(published, candles[: n + 1], atrs[: n + 1])
    assert nxt.total_count == published_total + 1
    assert published.total_count == published_total
    assert _materialized_dict(published, spec.record_id) == published_cursor
