"""TRACK A — Python -> EA analytical transport, on real broker OHLC.

WHAT IS CLAIMED HERE. The frozen engines, fed genuine FXCM candles, produce the
twelve Layer-A fields the MQL5 EA consumes, and every emitted line parses back —
under the EA's own splitting rule — to exactly those twelve values. That is
TRANSPORT parity, and it is provable offline.

WHAT IS NOT CLAIMED. That the EA agrees. The Strategy Tester cannot be launched
in this environment, so no EA-side value exists to compare against. Those rows
are BLOCKED in the release checklist and are not quietly counted as passes.

`artifacts/` is gitignored, so a fresh clone has no capture and these tests
skip rather than fail.
"""

from __future__ import annotations

from collections import Counter
from decimal import Decimal
from pathlib import Path

import pytest

from btmm_ai_scanner.config.enums import Timeframe
from tests.parity_support.rc5_ea_layer_a import (
    LIFECYCLE_CODE,
    VALIDITY_CODE,
    LayerAProjection,
    project_layer_a,
)
from tools.rc5_ea_fixtures import (  # type: ignore[import-not-found]
    FIXTURE_FIELDS,
    fixture_line,
)

_REPO = Path(__file__).resolve().parents[2]

#: `POI_VALIDATED` -- the ceiling this capture actually reaches.
LIFECYCLE_CODE_POI_VALIDATED = 3
_M15 = _REPO / "artifacts" / "rc5_m15_screenshot_capture" / "rc5_ohlc_m15_eurusd.csv"

pytestmark = pytest.mark.skipif(
    not _M15.exists(), reason="real capture absent (artifacts/ is gitignored)"
)


@pytest.fixture(scope="module")
def projection() -> LayerAProjection:
    from tests.unit._arrival_fixtures import m15_eurusd

    return project_layer_a(
        host_timeframe=Timeframe.M15,
        host_series=m15_eurusd(),
        logical_symbol="EURUSD",
        timeframe_minutes=15,
        minimum_price_tick=Decimal("0.00001"),
    )


# ---------------------------------------------------------------------------
# the projection is real
# ---------------------------------------------------------------------------


def test_the_projection_is_not_vacuous(projection: LayerAProjection) -> None:
    assert projection.bars > 0
    assert len(projection.fixtures) > 0


def test_every_emitted_lifecycle_is_an_ANALYTICAL_state(
    projection: LayerAProjection,
) -> None:
    """The engine must never hand Layer B a state it declares it never assigns.

    `RISK_VALIDATED`..`CLOSED` belong to the execution layer; seeing one here
    would mean the analytical/execution boundary had been crossed upstream.
    """
    allowed = set(LIFECYCLE_CODE.values())
    assert allowed == set(range(8))
    for fixture in projection.fixtures:
        assert fixture.lifecycle in allowed


def test_every_emitted_code_is_in_range(projection: LayerAProjection) -> None:
    validity_codes = set(VALIDITY_CODE.values())
    for fixture in projection.fixtures:
        assert fixture.direction in (1, -1)
        assert fixture.validity in validity_codes
        assert fixture.zone_top >= fixture.zone_bottom


# ---------------------------------------------------------------------------
# transport: what Python writes is what the EA reads
# ---------------------------------------------------------------------------


def test_every_line_round_trips_under_the_EAs_own_split_rule(
    projection: LayerAProjection,
) -> None:
    """`ParseFixtureLine` does `StringSplit(line, '|', f)` and requires 12.

    Reproducing that split here is the whole check: if any field could contain
    a pipe, or any value could render as something MQL5 reads differently, it
    shows up as a field-count or value mismatch on this line.
    """
    for fixture in projection.fixtures:
        line = fixture_line(fixture)
        parts = line.split("|")
        assert len(parts) == len(FIXTURE_FIELDS), line
        assert parts[0] == fixture.symbol
        assert int(parts[1]) == fixture.timeframe_minutes
        assert int(parts[2]) == fixture.bar_time_epoch
        assert parts[3] == fixture.poi_id
        assert int(parts[4]) == fixture.poi_type
        assert int(parts[5]) == fixture.direction
        assert Decimal(parts[6]) == fixture.zone_top
        assert Decimal(parts[7]) == fixture.zone_bottom
        assert bool(int(parts[8])) is fixture.authoritative
        assert int(parts[9]) == fixture.validity
        assert bool(int(parts[10])) is fixture.p5_permission
        assert int(parts[11]) == fixture.lifecycle


def test_no_poi_id_contains_the_delimiter(projection: LayerAProjection) -> None:
    """The id is the only free-form field, so it is the only real hazard."""
    for fixture in projection.fixtures:
        assert "|" not in fixture.poi_id


def test_zone_prices_render_without_scientific_notation(
    projection: LayerAProjection,
) -> None:
    """`StringToDouble` would not read `1E-5`. Decimal can produce it."""
    for fixture in projection.fixtures:
        for value in (str(fixture.zone_top), str(fixture.zone_bottom)):
            assert "E" not in value.upper(), value


# ---------------------------------------------------------------------------
# the finding this run produced, pinned so it cannot be forgotten
# ---------------------------------------------------------------------------


def test_this_capture_never_reaches_the_V1_trigger(
    projection: LayerAProjection,
) -> None:
    """MEASURED, and it is a release fact rather than a defect.

    On the author's 300-bar M15 EURUSD capture, run single-timeframe, no POI
    ever reaches `LIQUIDITY_VALIDATED`: the lifecycle ladder tops out at
    `POI_VALIDATED`, because `TREND_VALIDATED` needs a trend alignment that a
    single timeframe with no higher-timeframe context does not produce.

    The consequence for the release is concrete: **this capture cannot
    demonstrate a V1 execution**, so a Strategy Tester run against it would
    correctly place zero trades, and that must not later be read as the EA
    failing. A multi-timeframe capture is required to exercise the trigger.

    If this test ever fails because `confirmed > 0`, that is good news and the
    assertion should be replaced by the real parity expectation.
    """
    assert projection.confirmed == 0
    assert projection.actionable == 0
    reached = Counter(f.lifecycle for f in projection.fixtures)
    assert max(reached) == LIFECYCLE_CODE_POI_VALIDATED

