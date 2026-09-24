# EVERY X-COORDINATE IN THE DRAWING PATHS, CLASSIFIED

Track 18. The question: is any drawn object still anchored to a clock time
rather than to the thing it describes?

Answer: **no, after the two fixes** -- and the audit is small enough to state
exhaustively, which is the point.

---

## CORE -- three x-coordinate call sites, that is all

| line | call | x source | verdict |
| --- | --- | --- | --- |
| 6691 | `line.new(tw.anchor1Time, ..., tw.anchor2Time, ...)` | the trendline's two swing **anchors** | **CORRECT** -- a trendline is defined by its anchors |
| 7101 | `box.new(left = p7zIsSr ? poiCandTime : poiSrcFirst, ...)` | the POI's **source formation** | **CORRECT** (fixed in v20/v21) |
| 7109 | `box.set_right(..., p7zRightEdge)` | right edge only | **CORRECT** -- forward extension is permitted while active |

There is no fourth. No `time_close`, `timenow`, `bar_index` or availability
time appears as an x coordinate anywhere in CORE's drawing paths.

## VIEW -- three call sites

| line | call | x source | verdict |
| --- | --- | --- | --- |
| 1405 | `line.new(ev.brokenSwingKey, ..., ev.breakTime, ...)` | broken swing -> break bar | **CORRECT** -- the connector's whole meaning is "this level, broken here" |
| 1406 | `label.new(ev.breakTime, ...)` BOS / CHOCH | the **breaking** candle | **CORRECT** -- a break happens at the bar that broke it |
| 1413 | `label.new(sw.pivotEndTime, sw.price, "HH"/"LH"/"HL"/"LL")` | the pivot's **END** | **NEEDS A DECISION** -- see below |

## The one open item: swing labels sit at the pivot END

`label.new(sw.pivotEndTime, sw.price, ...)` places HH/HL/LH/LL at the pivot's
last candle. For a single-candle pivot that is the same bar and nothing is
wrong. For a **multi-candle** pivot, start and end differ, and the label sits
at the end while the extreme price was first made earlier.

This is exactly the S1/S2 question:

| target | swing | pivot START | pivot END |
| --- | --- | --- | --- |
| 1 | SWING_HIGH 1.14691 | 2026-09-18 15:15 | 15:30 |
| 2 | SWING_HIGH 1.14649 | 2026-09-22 06:45 | 07:00 |

Two facts make this cheap to fix *if* it is agreed to be wrong:

1. `StructSwingView` **already carries `pivotStartTime`**
   (`// <- wOpenT[pivotStartIdx] (pivot_start_time_utc)`), so no new data has
   to be transported;
2. the label is drawn in `tradingview/rc5_view_presentation.pine:41` and does
   **not** exist in CORE at all -- `grep -c "label.new(sw.pivotEndTime" CORE`
   returns 0. So the change is **VIEW-only and costs zero CORE tokens**, which
   matters with 45 headroom left.

**It was not changed.** The directive is explicit that this is a "no change
unless visibly one bar late" call, and that judgement needs the two named bars
on screen. What is settled is the *diagnosis* and that the fix is free; what is
not settled is whether the end-anchor is actually wrong, which is a question
about what an HH label is supposed to point at -- the bar that made the
extreme, or the bar that completed the pivot.

Both readings are defensible, which is why it is an author call and not a
defect.
