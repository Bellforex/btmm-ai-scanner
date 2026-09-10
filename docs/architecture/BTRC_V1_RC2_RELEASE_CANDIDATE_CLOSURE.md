# BTRC V1 — RC2 RELEASE CANDIDATE CLOSURE

| Item | Value |
| --- | --- |
| **TECHNICAL RC2 READY** | **TRUE** |
| **LIVE VISUAL ACCEPTANCE** | **VERIFIED** |
| M1 | **VERIFIED** |
| M5 | **VERIFIED** |
| M15 | **VERIFIED** |
| H1 | **VERIFIED** |
| RE10110 | **RESOLVED** |
| PRODUCTION APPROVED | **FALSE** |
| PROFITABILITY ESTABLISHED | **FALSE** |
| AUTOTRADING APPROVED | **FALSE** |

RC2 SHA256 `381f2fc2463c4eaa9dc2eb88943f5bc16a83b55a6d4307c390cce5f87f36cc3f`.
RC1 preserved, byte-identical at `143c0f88…64c54`.

---

## RC1 → RC2 USER-FACING CHANGELOG

**No scanner semantic engine change.** Every item below is presentation.

**1. Nearby POIs are shown instead of the oldest surviving registry entries.**
RC1 selected `p7PoiIdx[0 … capacity-1]`, ascending registry index. The registry
is append-only and P3 has no expiry, so those were the oldest never-invalidated
POIs. Measured on a frozen FXCM M15 capture (close 4329.33, ATR14 11.78, 157
active): the 12 drawn zones sat 199.01–259.06 from price, roughly 17–22 ATR,
while **four active POIs contained price**, and overlap with the nearest 12 was
**zero**. RC2 selects by distance to current close.

**2. Professional timeframe names.** `timeframe.period` is a raw token, so M1
rendered as `1 • BUY FVG`. RC2 renders M1, M5, M15, H1, H4, D1, W1. A test
asserts no label ever begins with a digit.

**3. Origin-anchored labels.** RC1 dragged every label to `time_close` on every
bar, piling them on one x coordinate and pushing them off-screen. RC2 anchors
each label at its zone's origin and never moves it; only the box's right edge
tracks time.

**4. Cleaner visual styling.** Neutral gray fill at 92% transparency with thin
directional borders, replacing the directional 85% fill that stacked into a
solid green wall.

**5. Capacity counts 8 visual groups**, not 12 raw zones. Grouping runs over the
whole active set *before* the cut, so a cluster can never be split by it.

**6. Exact-geometry presentation dedup.** Co-located POIs sharing top, bottom,
origin and direction draw as one box with a combined label, e.g.
`M15 • BUY OB + BULL ENGULF`. Registry identity is never merged.

**7. FVG overlap-or-touch clustering.** Same-direction FVGs whose intervals
overlap or touch draw as one box labelled `×N`, membership transitive, geometry
the envelope. Overlap alone never merges anything outside the FVG family.

**8. Optimized clustering eliminating the M5 RE10110 failure.** See below.

**9. M1 is formally supported.** RC1 acceptance covered M5, M15 and H1 only.

---

## THE RE10110 FAILURE AND ITS RESOLUTION

The P7-Z block sits inside `if barstate.isconfirmed`, so grouping runs on **every
confirmed bar** — about 1800 times per full recalculation. The first V2 build
used envelope-growth closure, O(n²) in the active-POI count. On M5, whose 1800
bars span roughly 6.25 days of structure against M1's 30 hours, that exceeded
TradingView's 20-second budget and raised **RE10110**, leaving the study drawing
nothing while P6 DEV stayed healthy. TradingView's own editor banner corroborated
it: *"Heavy script. This script is close to your plan's runtime limit (20s)."*

Replaced with **partition → sort → sweep**: partition by direction, sort by lower
edge, sweep with a running maximum upper edge. That is the classic interval merge
and produces identical connected components in O(n log n). Non-FVG exact-geometry
twins group through a hash key rather than a pairwise scan.

**The active set was deliberately not bounded before grouping.** A far interval
can be reachable only through a connector, so truncating first changes both
membership and geometry — a test demonstrates that concretely.

Equivalence against the frozen oracle: zero mismatches across 17 adversarial
shapes, randomized sizes 1 to 1000, the full 1800-bar budget, four real captures,
and a Pine-port simulation over 40 seeds to size 900.

**Five fresh-tab M5 cold reconstructions: 5/5 PASS, total RE10110 = 0.**

---

## DEFECTS FOUND AND FIXED DURING ACCEPTANCE

Recorded because each was caught by a check rather than by luck.

1. `str.tonumber(p) == na` — invalid in Pine v6. Caught by the compiler, not by
   offline tests, which exercise the Python model rather than Pine syntax.
2. `• STRONG` appended to FVG cluster labels — FVGs are TIER_NA. Caught by the
   randomized Pine-port differential.
3. P7 table parallel-array desync on three of nine fields — rows would have shown
   one POI's identity with another's data.
4. UTF-16 BOM pasted as U+FFFD, silently breaking `//@version=6` so the script
   compiled as Pine v1.
5. Per-bar `label.set_x` label migration — the half-fixed Phase 8 anchor.
6. RE10110 execution timeout — the subject of this closure.
7. Compile token-limit overflow (100534 against 100256) on the first sweep build.

---

## LIMITATIONS CARRIED INTO RC2

- **Golden BASE_RALLY (registry 170) live re-trace: N/A.** Mechanical geometry is
  VERIFIED; the POI sits ~2114 M1 bars back against an 1800-bar horizon, so it
  cannot appear. The five in-window BASE_RALLY candidates are all terminal.
  Documented **evidence limitation** — not a blocker, not a detector defect, not
  a visual defect. `calc_bars_count` and lifecycle semantics were not altered to
  manufacture the test.
- **Fewer labels than boxes** where a zone's origin lies outside the chart's
  loaded window. Expected, explained, and resolves as history loads.
- **P3 Context** and **P4 Reviewed-Evidence Transport** remain deferred.
- **TradingView Alert object creation** remains platform-blocked.

---

## WHAT RC2 IS NOT

RC2 is a technical release candidate for user-facing presentation. It is not
production-approved, makes no profitability claim, and is not autotrading
approved. Nothing in this closure supports placing trades.
