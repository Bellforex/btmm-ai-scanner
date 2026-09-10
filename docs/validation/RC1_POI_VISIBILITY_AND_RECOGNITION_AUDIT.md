# RC1 POI VISIBILITY + RECOGNITION AUDIT REPORT

**Status:** Question A ANSWERED AND CONFIRMED. Question B BLOCKED on evidence not
available to this session.
**V1-A validation:** PAUSED. **OOS:** unopened.
**RC1 source:** unmodified, SHA256 still
`143c0f8817c78bf45e6842e16112cedf67ca36dc694c288808b7748096664c54`.

---

## HEADLINE

The visibility defect is **CONFIRMED**, and it is not a tuning problem or a
data-dependent one. It is a single static line of selection policy.

Frozen RC1 selects the zones to draw as
`p7PoiIdx[0 .. p7zMaxVisibleZones-1]` — ascending POI-registry index. The
registry is append-only in creation order and **P3 has no expiry**, so the first
12 entries are the **12 oldest POIs that have never been invalidated**. After
~1800 bars of price drift they are, necessarily, nowhere near current price.

This is the exact rule the brief's Phase 8 requires the test suite to reject as a
mutant. The shipped build *is* that mutant.

---

## PHASE 0 — BASELINE

| Item | Value |
| --- | --- |
| Branch | `validation-v1a-outcomes` |
| HEAD at audit start | `297be74aa017b8e019afe2d3c2c2ca7085c05a2e` |
| RC1 SHA256 | `143c0f88…64c54` (matches frozen value) |
| Tests collected (baseline) | 3976 |
| V1-A harness | intact, untouched |

---

## A — SCREENSHOT REPRODUCTION

The user's screenshots are **not attached to this conversation**, and no live
TradingView session was driven for this audit. Rather than guess at the live
chart, the defect was reproduced against a **frozen real FXCM XAU/USD M15
capture** already in the repo — 1799 bars, anchor `1788267600000` — replayed
through the real P3 detection + persistent-lifecycle engine.

This substitution is sound because the defect is price-independent: "first N by
registry index" returns the oldest POIs on *any* data.

| Measure | Value |
| --- | --- |
| Bars replayed | 1799 real FXCM M15 |
| Final close | 4329.33 |
| ATR(14) at final bar | 11.78 |
| Registry total | 968 |
| **Active POIs** | **157** |
| Terminal | 811 |
| P7-Z capacity | 12 |
| P7 table capacity | 8 |

157 active is the same order of magnitude as the 101–136 the user reported, so
the reproduction is representative.

### Currently selected 12 (frozen RC1 rule)

Every one is bullish, and every one is ~17–22 ATR away.

| # | registry idx | type | top | bottom | distance | age (bars) |
| --- | --- | --- | --- | --- | --- | --- |
| 0 | 0 | 3 | 4070.27 | 4070.09 | 259.06 | 1795 |
| 1 | 1 | 3 | 4078.01 | 4074.12 | 251.32 | 1793 |
| 2 | 3 | 9 | 4082.41 | 4077.59 | 246.92 | 1791 |
| 3 | 4 | 1 | 4088.62 | 4082.51 | 240.71 | 1789 |
| 4 | 5 | 11 | 4088.62 | 4082.51 | 240.71 | 1789 |
| 5 | 6 | 3 | 4092.68 | 4088.62 | 236.65 | 1788 |
| 6 | 7 | 3 | 4096.25 | 4092.96 | 233.08 | 1787 |
| 7 | 8 | 7 | 4108.14 | 4095.59 | 221.19 | 1785 |
| 8 | 9 | 7 | 4108.14 | 4092.68 | 221.19 | 1785 |
| 9 | 10 | 3 | 4124.62 | 4108.14 | 204.71 | 1784 |
| 10 | 11 | 1 | 4130.32 | 4127.45 | 199.01 | 1779 |
| 11 | 12 | 11 | 4130.32 | 4127.45 | 199.01 | 1779 |

The age column is the finding in miniature: the displayed set is bars 1779–1795
of a 1799-bar window. RC1 is drawing the **first twelve POIs the scanner ever
created** and nothing since.

### Nearest 12 active POIs (same distance definition)

| # | registry idx | type | top | bottom | distance |
| --- | --- | --- | --- | --- | --- |
| 0 | 136 | 3 | 4355.49 | 4317.27 | **0 (contains price)** |
| 1 | 381 | 3 | 4329.45 | 4324.84 | **0 (contains price)** |
| 2 | 487 | 9 | 4332.24 | 4328.61 | **0 (contains price)** |
| 3 | 494 | 9 | 4337.88 | 4324.41 | **0 (contains price)** |
| 4 | 380 | 6 | 4326.96 | 4319.36 | 2.37 |
| 5 | 373 | 15 | 4326.47 | 4323.30 | 2.86 |
| 6 | 374 | 9 | 4325.23 | 4323.73 | 4.10 |
| 7 | 371 | 3 | 4324.92 | 4323.74 | 4.41 |
| 8 | 379 | 15 | 4324.84 | 4310.72 | 4.49 |
| 9 | 491 | 3 | 4339.09 | 4334.20 | 4.87 |
| 10 | 156 | 9 | 4322.30 | 4318.58 | 7.03 |
| 11 | 503 | 9 | 4342.20 | 4336.67 | 7.34 |

---

## B — VISIBILITY

**6. Offscreen-selection defect: TRUE.**

| | current 12 | nearest 12 |
| --- | --- | --- |
| min distance | 199.01 | 0 |
| median distance | 236.65 | 4.10 |
| max distance | 259.06 | 7.34 |
| **overlap** | **0 of 12** | |

Median displayed distance is **58x** the median nearest distance. **Four active
POIs contain current price and none of them is drawn.**

**7. Old rule.** `sorted(eligible)[:capacity]` — ascending registry index.
`btmm_poi_btrc_scanner_rc1.pine:6187-6190`. The source comment states it plainly:
*"ascending registry-index order, first `p7zMaxVisibleZones` entries"*. The
offline model `p7z_zone_model.py:188-189` mirrors it, and its `advance_bar`
**takes no price argument at all** — proximity was never a consideration anywhere
in the layer.

**8. New rule.** Nearest-to-current-close, ascending, capacity-bounded. Distance
is 0 inside the zone, else the gap to the nearest boundary. Ties fall back to
ascending registry index — the existing canonical stable ordering. No tier, BTRC,
BTMM or timeframe weighting introduced.

**9. Engine count unchanged: TRUE.** The correction touches only the bounded set
handed to `box.new`. `p7PoiIdx` still holds every active POI; P5 still evaluates
all of them; P8 still monitors all of them. A parametrized test asserts the active
universe is neither shrunk nor mutated at capacities 1/5/12/30.

---

## C — MANUAL M15 POI CHALLENGE (Phases 9–13)

> **SUPERSEDED — Question B is now ANSWERED.** The author supplied locator values
> and I captured the real FXCM M15 bars. Result: **CASE A, detection correct,
> visibility defect confirmed.** The zone is registry index 172,
> `BUY_ORDER_BLOCK`, top 4388.55, bottom 4383.21, candidate bar 2026-09-09 06:15
> Europe/London, still ACTIVE. Full verdicts for all 18 detectors and the
> account correction are in
> [RC1_POI_QUESTION_B_REPORT.md](RC1_POI_QUESTION_B_REPORT.md). The section below
> is kept as the record of what was and was not knowable at the time.

**BLOCKED — cannot be answered honestly in this session.**

Phases 9–13 require locating "the grey rectangle shown in the screenshot". The
screenshots are described in the brief but are **not attached to this
conversation**, and there is no live chart session here. I cannot see the marked
zone, so I cannot identify its candles, and I will not guess at coordinates and
then present detector verdicts derived from a guess.

Items 10–19 are therefore **UNANSWERED**, not answered negatively. Nothing in
this report should be read as evidence that P3 detection is correct or incorrect
for the user's zone.

**What unblocks it — any one of these is enough:**

1. The M15 zone's **top and bottom price**, plus the **timestamp** (or bar time)
   of the candle(s) it covers; or
2. The screenshot itself, attached to the conversation; or
3. The approximate time window plus "base of the strong upside displacement", and
   I will enumerate every displacement in that window and test each candidate
   base against all 18 detectors.

Once supplied, Phases 10–13 run mechanically against the frozen detectors and
return PASS or FAIL-with-exact-reason per type.

**One relevant prior, offered as context and not as an answer:** P3 is
demonstrably detecting contemporary structure — **54 POIs were created in the
final 100 bars** of the replay, spanning order blocks, FVGs, engulfings and
pressure wicks. Detection is alive and current. Combined with the confirmed
visibility defect, the Phase 11 outcome (correct detection, defective display) is
the more likely one, but it remains **unproven** until the zone is identified.

---

## D — REGISTRY AUDIT

**20. Active count:** 157 of 968.

**21. Age distribution** (bars since availability, n=156 with resolvable bar times):

| Age bucket | Count |
| --- | --- |
| 0–24 | 13 |
| 25–48 | 11 |
| 49–100 | 1 |
| 101–300 | 29 |
| 301–600 | 26 |
| 600+ | **76** |

**22. Oldest active:** 1795 bars — effectively the first bar of the window.
**23. Median age:** 503 bars. 90th percentile: 1772 bars.

Half the active registry is older than ~21 days of M15 bars. This is a direct
consequence of there being no expiry: a POI stays active until genuine
invalidation, and many never get invalidated. **No expiry was added** — per the
brief this is reported, not fixed.

**24. Distance distribution** (all 157 active, ATR = 11.78):

| Band | Count |
| --- | --- |
| inside a zone (0) | 4 |
| ≤ 0.25 ATR | 6 |
| ≤ 0.5 ATR | 10 |
| ≤ 1 ATR | 14 |
| ≤ 2 ATR | 22 |
| ≤ 5 ATR | 46 |
| > 5 ATR | 111 |

46 active POIs sit within 5 ATR — comfortably more than the 12 slots. The
scanner has plenty of relevant material; it is simply drawing none of it.

---

## E — P7 TABLE (Phase 17)

**25. Same ordering issue: TRUE.**

The table reads `p7PoiIdx[rowIdx]` for rows `0..p7Shown-1` — the identical
first-N-registry-order rule, at capacity 8
(`btmm_poi_btrc_scanner_rc1.pine:6357-6363`).

| | table's 8 rows | nearest 8 |
| --- | --- | --- |
| distance range | 221.19 – 259.06 | 0 – 4.41 |
| overlap | **0 of 8** | |

**Recommendation (not applied):** share one proximity projection between the P7
table and the P7-Z boxes so the table lists the same zones the trader can see.
This is presentation-only and carries no engine implication, but it is a separate
surface from the one the brief authorized, so it is left for the author's
decision.

---

## F — CORRECTION APPLIED

**26. Display change.** New file
`tradingview/btmm_poi_btrc_scanner_rc1_poi_fix_dev.pine`, title
`BTMM + POI + BTRC Scanner [RC1-POI-FIX DEV]`.

**27. P3 source changed: FALSE.** **28. Affected detector: none.**

RC1 is byte-identical and its SHA256 is unchanged. The DEV diff is **four hunks,
all in the P7-Z presentation block**:

| Hunk | Content |
| --- | --- |
| line 44 | indicator title only |
| 6172–6175 | header comment corrected (it documented the old rule) |
| 6188–6203 | new explanatory comment |
| 6206–6236 | the selection loop |

No P3, P4, P5, P6 or P8 code is touched. Pine has no stable key-sort, so the port
uses a repeated-minimum scan; a differential test simulates that Pine loop
exactly and proves it agrees with the Python model across 40 randomized
universes plus a heavy-tie case.

### Phase 6 — bull/bear coverage: AUTHOR DECISION REQUIRED

Pure nearest-distance selection **can** return an entirely one-sided set, and on
this capture it **did**: the nearest 12 are **12 bullish, 0 bearish** (6 above
price, 2 below, 4 containing it). A permanent test documents this behavior
rather than hiding it.

**No 6-buy/6-sell quota was introduced**, per the brief. Whether one-sided
selection is acceptable is the author's call. My recommendation is to ship pure
proximity first and see it live — a quota would force distant zones onto the
chart to fill a side, which reintroduces the very problem being fixed.

---

## G — LIVE ACCEPTANCE (Phases 19–23)

**29–35. NOT PERFORMED.** No live TradingView session was driven, and the
corrective DEV has not been deployed to a chart. M5/M15/H1 acceptance, geometry
and label verification against the registry, price-movement re-selection, pan/zoom
behavior and runtime-error checks (RE10041 / RE10045) all remain **outstanding**.

The DEV script is written and its selection logic is proven offline, but it is
**unverified on TradingView** and must not be treated as accepted.

**Phase 23 note, stated honestly:** selection is computed against **current
close**, not viewport center. Panning away from the current bar will therefore
*not* re-select zones for the region being viewed; the drawn set stays anchored
to live price. This is deliberate and matches the brief, but it is a real
usability property the author should confirm is what they want.

---

## H — ENGINE NON-REGRESSION

**Full suite: 4043 passed, 0 failed** (baseline 3976 + the 67 new tests).

**36–39.** The P5/P6/P8/P9 parity suites are part of that run and all pass. Stated
precisely, so the claim is not stronger than the evidence: the frozen digest
values below live in the closure documents, not as literals in test code, so what
this run proves is that **every parity test still passes** and that **no engine
source was modified** — not that the digest integers were re-derived and compared
in this session.

| Phase | Frozen evidence (from closure docs) |
| --- | --- |
| P5 | 240850 / 240850; H1 351473241, H2 335238294 |
| P6 | 30 / 30 |
| P8 | 456 / 456; H1 294719549, H2 35571918 |
| P9 | H1 224768619, H2 772693120 |

The stronger structural guarantee is the change scope. `git diff` against HEAD
shows **zero modifications under `src/`** and **zero modifications to any existing
file in `tradingview/`**. The only edited file in the entire tree is
`tests/parity_support/p7z_zone_model.py`, and that diff is **101 insertions, 0
deletions** — every pre-existing function is byte-identical. Everything else is a
new file. No semantic change is possible from this shape of diff.

`test_rc1_semantic_equivalence.py` — which pins RC1 against P9 DEV and asserts the
only difference is the indicator title — passed unchanged; the new DEV script is a
separate path and does not participate in it.

---

## I — VALIDATION STATUS

| # | Item | Value |
| --- | --- | --- |
| 40 | V1-A remains paused | **TRUE** |
| 41 | OOS unopened | **TRUE** |
| 42 | RC1 still valid validation baseline | **TRUE** |

Item 42 was provisional when first written, pending Question B. Question B has
since resolved as **CASE A** (detection correct, display defective), so P3
semantics do not change, the validation subject does not move, and item 42 is now
unconditional.

---

## J — SAFETY

| # | Action | Status |
| --- | --- | --- |
| 43 | push | **FALSE** |
| 44 | merge | **FALSE** |
| 45 | publish | **FALSE** |
| 46 | live trading | **FALSE** |

---

## WHAT I RECOMMEND NEXT

1. **Supply the M15 zone coordinates** so Question B can be closed. This is the
   only genuinely blocked item and the only one that could invalidate the
   validation baseline.
2. **Decide the Phase 6 question** — pure proximity, or a bull/bear quota.
3. **Decide whether the P7 table shares the projection** (Phase 17 recommendation).
4. Then deploy the DEV to TradingView for the Phase 19–23 live acceptance.

V1-A stays paused until at least items 1 and 4 are done.
