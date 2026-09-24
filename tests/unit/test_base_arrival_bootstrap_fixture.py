"""The bootstrap fixture the real captures cannot provide.

Structural direction has TWO sources: the walk's initial bootstrap (the first
HH+HL or LH+LL relationship pair) and, after that, each transition's
`direction_after`. A Pine port that implemented only the second half would be
wrong, and — this is the point — it would pass every real-data parity check
available, because all three FXCM captures contain a bootstrap-only window with
**zero Bases inside it**:

    M15 EURUSD  bootstrap 2026-09-18 18:30, first transition 19:15   0 Bases
    M45 XAUUSD  bootstrap 2026-08-27 21:15, first transition 00:15   0 Bases
    H3  XAUUSD  bootstrap 2026-08-05 04:00, first transition 07:00   0 Bases

So the divergence would be real, silent and invisible. These synthetic series
exist solely to make it visible.

Built from the existing structural primitives in
`tests/parity_support/ob_origin_series.py` — `trend`, `mirror`,
`rows_to_candles` — and detected with the PRODUCTION `PoiConfiguration`. No
constant is relaxed to make the Base qualify.
"""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path

from btmm_ai_scanner.domain.configuration import MarketMeasurementConfiguration
from btmm_ai_scanner.poi.base_arrival import resolve_base_arrival
from btmm_ai_scanner.poi.bases import detect_bases
from btmm_ai_scanner.poi.configuration import PoiConfiguration
from btmm_ai_scanner.poi.enums import BaseFamily, PoiType, is_standard_base_family
from btmm_ai_scanner.structure.enums import StructureDirection
from tests.parity_support.ob_origin_series import Row, mirror, rows_to_candles, trend
from tests.unit._arrival_fixtures import structure_of

_TICK = Decimal("0.01")
_MEASUREMENT = MarketMeasurementConfiguration(minimum_price_tick=_TICK)
_POI = PoiConfiguration(minimum_price_tick=_TICK)


def _bullish_rows() -> list[Row]:
    """L0 -> H1 -> L1 -> H2 -> L2, then a Base, and never a transition.

    Two highs and two lows are the minimum that yields BOTH a HIGHER_HIGH and a
    HIGHER_LOW, which is what the walk bootstraps on. The departure closes above
    the base but stays below H2, so it cannot break structure and no transition
    is ever produced.
    """
    rows = trend(110, -1.0, 8)  # L0 = 102
    rows += trend(102, 1.0, 8)  # H1 = 110
    rows += trend(110, -1.0, 5)  # L1 = 105, higher than L0
    rows += trend(105, 1.0, 10)  # H2 = 115, higher than H1  -> HIGHER_HIGH
    rows += trend(115, -1.0, 5)  # L2 = 110, higher than L1  -> HIGHER_LOW
    rows += trend(110, 0.2, 5)  # drift, still far below H2
    base = 111.0
    rows += [(base, base + 0.10, base - 0.10, base + 0.02)]
    rows += [(base + 0.02, base + 0.10, base - 0.10, base - 0.01)]
    rows += [(base - 0.01, base + 1.9, base - 0.10, base + 1.8)]
    rows += trend(112.8, 0.1, 6)
    return rows


def _candles(rows: list[Row], tmp_path: Path, name: str):
    return rows_to_candles(rows, tmp_path, name)


def _resolve(rows: list[Row], tmp_path: Path, name: str):
    candles = _candles(rows, tmp_path, name)
    timeline, walk = structure_of(candles, _MEASUREMENT)
    bases = detect_bases(candles, _POI)
    return candles, timeline, walk, bases, resolve_base_arrival(bases, timeline, walk)


# ---------------------------------------------------------------------------
# the fixture really is bootstrap-only
# ---------------------------------------------------------------------------


def test_the_bullish_fixture_bootstraps_and_never_transitions(tmp_path: Path) -> None:
    _, timeline, walk, bases, facts = _resolve(_bullish_rows(), tmp_path, "bull")
    times, dirs = timeline

    assert walk.transitions == (), "a transition would destroy the discriminator"
    assert len(times) == 1, "exactly one timeline entry: the bootstrap"
    assert dirs[0] is StructureDirection.BULLISH
    assert bases, "fixture produced no Base"

    for base in bases:
        fact = facts[(base.poi_type, base.source_candle_record_ids)]
        # strictly inside [bootstrap, first transition) -- there is no first
        # transition, so every Base after the bootstrap qualifies
        assert fact.arrival_reference_utc >= times[0]
        assert fact.arrival_known_from_utc == times[0]


def test_the_bearish_mirror_bootstraps_and_never_transitions(tmp_path: Path) -> None:
    _, timeline, walk, bases, facts = _resolve(
        mirror(_bullish_rows()), tmp_path, "bear"
    )
    times, dirs = timeline
    assert walk.transitions == ()
    assert len(times) == 1
    assert dirs[0] is StructureDirection.BEARISH
    assert bases
    for base in bases:
        assert (
            facts[(base.poi_type, base.source_candle_record_ids)].arrival_known_from_utc
            == times[0]
        )


# ---------------------------------------------------------------------------
# the families Pine must reproduce
# ---------------------------------------------------------------------------


def test_bullish_bootstrap_yields_rally_base_rally(tmp_path: Path) -> None:
    _, _, _, bases, facts = _resolve(_bullish_rows(), tmp_path, "bull")
    for base in bases:
        fact = facts[(base.poi_type, base.source_candle_record_ids)]
        assert base.poi_type is PoiType.BASE_RALLY
        assert fact.arrival_direction is StructureDirection.BULLISH
        assert fact.family is BaseFamily.RALLY_BASE_RALLY
        assert is_standard_base_family(fact.family)


def test_bearish_bootstrap_yields_drop_base_drop(tmp_path: Path) -> None:
    _, _, _, bases, facts = _resolve(mirror(_bullish_rows()), tmp_path, "bear")
    for base in bases:
        fact = facts[(base.poi_type, base.source_candle_record_ids)]
        assert base.poi_type is PoiType.BASE_DROP
        assert fact.arrival_direction is StructureDirection.BEARISH
        assert fact.family is BaseFamily.DROP_BASE_DROP
        assert is_standard_base_family(fact.family)


# ---------------------------------------------------------------------------
# the discriminator itself
# ---------------------------------------------------------------------------


def test_a_transitions_only_implementation_would_answer_unknown(
    tmp_path: Path,
) -> None:
    """THE reason this fixture exists.

    Rebuild the direction timeline from transitions ALONE — which is what a
    Pine port that skipped the bootstrap would effectively have — and every
    Base here becomes UNKNOWN and loses authority. Against the real captures
    that same implementation is indistinguishable from a correct one.
    """
    for rows, name in ((_bullish_rows(), "bull"), (mirror(_bullish_rows()), "bear")):
        _, _timeline, walk, bases, facts = _resolve(rows, tmp_path, name)

        transitions_only: tuple[list, list] = (
            [t.availability_time_utc for t in walk.transitions],
            [t.direction_after for t in walk.transitions],
        )
        degraded = resolve_base_arrival(bases, transitions_only, walk)

        assert bases
        for base in bases:
            key = (base.poi_type, base.source_candle_record_ids)
            assert facts[key].family is not None, "the faithful answer is a family"
            assert is_standard_base_family(facts[key].family)

            assert degraded[key].arrival_direction is StructureDirection.UNDETERMINED
            assert degraded[key].family is None
            assert not is_standard_base_family(degraded[key].family)
