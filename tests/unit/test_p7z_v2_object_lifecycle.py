"""RC1-POI-V2 Gate 4: drawn-object lifecycle under repeated state change.

The Pine build keeps three DENSE parallel arrays -- `p7zBoxPoiIdx`,
`p7zBoxes`, `p7zLabels` -- and each bar it deletes the box and label for any
POI no longer in the selected set, then removes all three entries. A leak here
is not abstract: `box.new` without a matching `box.delete` accumulates real
chart objects against `max_boxes_count`, and the failure mode looks like
counts climbing 8, 16, 24, 32 across recalculations with comparable state.

These tests exercise the V2 GROUP projection specifically, since capacity now
bounds visual groups rather than semantic POIs, and one group may own several
POIs. Model level: this proves the selection/eviction contract the Pine port
implements, not the live TradingView object table.
"""

from __future__ import annotations

import random

import pytest

from tests.parity_support.p7z_zone_model import (
    DIRECTION_BEARISH,
    DIRECTION_BULLISH,
    TIER_STANDARD,
    PoiGeometry,
    build_visual_groups,
)

CAPACITY = 8
BUY_FVG, SELL_FVG = 3, 4
NON_FVG = (1, 7, 9, 11, 13)


class DrawnObjects:
    """Mirrors the Pine box/label registry: identity-keyed, evict-then-create."""

    def __init__(self) -> None:
        self.boxes: dict[int, tuple] = {}
        self.labels: dict[int, str] = {}
        self.created = 0
        self.deleted = 0

    def render(self, groups: list[dict]) -> None:
        keys = {min(g["members"]) for g in groups}
        for stale in list(self.boxes):
            if stale not in keys:
                del self.boxes[stale]
                del self.labels[stale]
                self.deleted += 1
        for g in groups:
            k = min(g["members"])
            if k not in self.boxes:
                self.created += 1
            self.boxes[k] = (g["top"], g["bottom"], g["left_time_ms"])
            self.labels[k] = g["label"]

    @property
    def counts(self) -> tuple[int, int]:
        return (len(self.boxes), len(self.labels))


def _universe(seed: int, n: int) -> dict[int, PoiGeometry]:
    rng = random.Random(seed)
    geo = {}
    for i in range(n):
        if rng.random() < 0.5:
            poi_type = rng.choice([BUY_FVG, SELL_FVG])
            direction = DIRECTION_BULLISH if poi_type == BUY_FVG else DIRECTION_BEARISH
        else:
            poi_type = rng.choice(NON_FVG)
            direction = rng.choice([DIRECTION_BULLISH, DIRECTION_BEARISH])
        bottom = round(rng.uniform(90.0, 110.0), 2)
        geo[i] = PoiGeometry(
            idx=i, poi_type=poi_type, direction=direction,
            zone_top=round(bottom + rng.uniform(0.0, 2.0), 2), zone_bottom=bottom,
            avail_time_ms=1000 + i * 60, tier=TIER_STANDARD,
        )
    return geo


def test_object_counts_stay_bounded_across_many_price_moves():
    """The forbidden pattern is monotonic growth across recalculations."""
    geo = _universe(1, 120)
    active = list(geo)
    objs = DrawnObjects()
    observed = []
    rng = random.Random(99)
    for _ in range(300):
        close = rng.uniform(85.0, 115.0)
        objs.render(build_visual_groups(active, geo, close, CAPACITY, "1"))
        observed.append(objs.counts[0])
    assert max(observed) <= CAPACITY
    # Conservation: every object ever created is either still drawn or was
    # deleted. This is the invariant a real leak breaks -- `box.new` without a
    # matching `box.delete` makes created outrun deleted + live.
    live_boxes, live_labels = objs.counts
    assert objs.created - objs.deleted == live_boxes
    assert live_boxes == live_labels
    # 300 price moves over a 120-POI universe churn the selection heavily, so
    # the run must actually have exercised eviction rather than sitting still.
    assert objs.deleted > 0, "no eviction happened; the stress was vacuous"
    assert objs.created > CAPACITY, "selection never changed; the stress was vacuous"


def test_repeated_identical_state_creates_nothing_new():
    """Re-rendering the same state must not re-create objects."""
    geo = _universe(2, 60)
    active = list(geo)
    objs = DrawnObjects()
    objs.render(build_visual_groups(active, geo, 100.0, CAPACITY, "1"))
    after_first = objs.created
    for _ in range(50):
        objs.render(build_visual_groups(active, geo, 100.0, CAPACITY, "1"))
    assert objs.created == after_first, "identical state re-created objects"
    assert objs.deleted == 0
    assert objs.counts == (CAPACITY, CAPACITY)


def test_every_drawn_object_belongs_to_the_current_selection():
    """No orphan boxes: after each render the key set equals the group keys."""
    geo = _universe(3, 90)
    active = list(geo)
    objs = DrawnObjects()
    rng = random.Random(7)
    for _ in range(120):
        groups = build_visual_groups(active, geo, rng.uniform(88.0, 112.0), CAPACITY, "1")
        objs.render(groups)
        expected = {min(g["members"]) for g in groups}
        assert set(objs.boxes) == expected, "stale graphic survived"
        assert set(objs.labels) == expected


def test_boxes_and_labels_never_desynchronise():
    geo = _universe(4, 75)
    active = list(geo)
    objs = DrawnObjects()
    rng = random.Random(11)
    for _ in range(150):
        objs.render(build_visual_groups(active, geo, rng.uniform(85.0, 115.0), CAPACITY, "1"))
        assert set(objs.boxes) == set(objs.labels)
        boxes, labels = objs.counts
        assert boxes == labels


@pytest.mark.parametrize("n_active", [1, 5, 8, 9, 40, 150])
def test_counts_bounded_for_any_active_population(n_active):
    geo = _universe(5, n_active)
    groups = build_visual_groups(list(geo), geo, 100.0, CAPACITY, "1")
    objs = DrawnObjects()
    objs.render(groups)
    boxes, labels = objs.counts
    assert boxes <= CAPACITY and labels <= CAPACITY
    assert boxes == len(groups)


def test_shrinking_active_set_releases_objects():
    """Host switches shrink the universe; objects must be released, not kept."""
    geo = _universe(6, 100)
    objs = DrawnObjects()
    objs.render(build_visual_groups(list(geo), geo, 100.0, CAPACITY, "1"))
    assert objs.counts == (CAPACITY, CAPACITY)
    objs.render(build_visual_groups([0, 1], geo, 100.0, CAPACITY, "1"))
    assert objs.counts[0] <= 2
    objs.render([])
    assert objs.counts == (0, 0), "objects survived an empty selection"


def test_simulated_host_switch_cycle_does_not_accumulate():
    """M1 -> M5 -> M1 -> M15 -> M1 -> H1 -> M1 with different universes."""
    objs = DrawnObjects()
    seen = []
    for _cycle in range(12):
        for seed, n in ((10, 120), (11, 40), (10, 120), (12, 70), (10, 120), (13, 25), (10, 120)):
            geo = _universe(seed, n)
            objs.render(build_visual_groups(list(geo), geo, 100.0, CAPACITY, "1"))
            seen.append(objs.counts[0])
    assert max(seen) <= CAPACITY
    assert seen[-7:] == seen[:7], "counts drifted across identical cycles"


# ---- label anchoring (the defect found in live Gate 1) -------------------
# Frozen RC1 called `label.set_x(existing, time_close)` on every bar for every
# already-drawn zone. The V2 corrective changed label CREATION to anchor at the
# zone origin but initially left that per-bar reposition in place, so only a
# label created on the current bar ever sat at its origin and every older one
# was dragged to the right edge. Measured live on M5: 6 of 8 labels had been
# pulled to the last bar index while their boxes started at six distinct
# origins. These tests pin the corrected contract.


class DrawnWithLabelAnchors(DrawnObjects):
    """Adds the label x anchor, and a bar clock, to the lifecycle mirror."""

    def __init__(self) -> None:
        super().__init__()
        self.label_x: dict[int, int] = {}

    def render_at(self, groups: list[dict], bar_time: int) -> None:
        keys = {min(g["members"]) for g in groups}
        for stale in list(self.boxes):
            if stale not in keys:
                del self.boxes[stale]
                del self.labels[stale]
                del self.label_x[stale]
                self.deleted += 1
        for g in groups:
            k = min(g["members"])
            if k not in self.boxes:
                self.created += 1
                # label.new(x = group origin) -- set ONCE, never moved
                self.label_x[k] = g["left_time_ms"]
            # box.set_right(bar_time) every bar; the label must NOT follow
            self.boxes[k] = (g["top"], g["bottom"], g["left_time_ms"], bar_time)
            self.labels[k] = g["label"]


def test_label_anchor_is_the_zone_origin_not_the_current_bar():
    geo = _universe(20, 40)
    active = list(geo)
    objs = DrawnWithLabelAnchors()
    groups = build_visual_groups(active, geo, 100.0, CAPACITY, "1")
    objs.render_at(groups, bar_time=999_999)
    for g in groups:
        k = min(g["members"])
        assert objs.label_x[k] == g["left_time_ms"]
        assert objs.label_x[k] != 999_999, "label anchored to the current bar"


def test_label_anchor_never_moves_while_the_box_right_edge_advances():
    """The exact regression: box right tracks time, label x must not."""
    geo = _universe(21, 40)
    active = list(geo)
    objs = DrawnWithLabelAnchors()
    groups = build_visual_groups(active, geo, 100.0, CAPACITY, "1")
    objs.render_at(groups, bar_time=1_000)
    first = dict(objs.label_x)
    rights_first = {k: v[3] for k, v in objs.boxes.items()}

    for t in range(1_060, 1_600, 60):
        objs.render_at(build_visual_groups(active, geo, 100.0, CAPACITY, "1"), bar_time=t)

    assert objs.label_x == first, "a label was dragged as bars advanced"
    rights_last = {k: v[3] for k, v in objs.boxes.items()}
    assert all(rights_last[k] > rights_first[k] for k in rights_first), (
        "box right edge did not advance; the test proved nothing"
    )


def test_labels_do_not_collapse_onto_one_x_coordinate():
    """Distinct origins must yield distinct label anchors -- the pile."""
    geo = {
        i: PoiGeometry(idx=i, poi_type=NON_FVG[i % len(NON_FVG)],
                       direction=DIRECTION_BULLISH,
                       zone_top=100.0 + i, zone_bottom=99.5 + i,
                       avail_time_ms=1000 + i * 60, tier=TIER_STANDARD)
        for i in range(CAPACITY)
    }
    objs = DrawnWithLabelAnchors()
    objs.render_at(build_visual_groups(list(geo), geo, 103.0, CAPACITY, "1"), bar_time=99_999)
    anchors = sorted(objs.label_x.values())
    assert len(set(anchors)) == len(anchors), "labels piled onto shared x"
    assert 99_999 not in anchors
