# BTRC-V1 RC5 — STRUCTURAL ROLE FORENSIC

Verdict up front: **B — the role set needs one narrow addition.** The H3
negative control passes perfectly, but the author's own M45 B2S positive
fixture is refused, and the reason is structural rather than marginal.

## 0. Capture provenance

`artifacts/` is gitignored, so the new host captures are recorded here rather
than committed. Captured 2026-09-20 from TradingView, account `bellcare1994`
(verified via `window.user.username` immediately before each read), scratch
layout `BAH-RC5-LAB` (chart `fn3ash9L`). The protected `bellforex` layout was
not used.

| | M45 | H3 |
|---|---|---|
| symbol / provider | FX:XAUUSD / FXCM | FX:XAUUSD / FXCM |
| resolution | 45 | 180 |
| bars | 529 | 300 |
| first bar UTC | 2026-08-26 19:45 | 2026-07-29 10:00 |
| last bar UTC | 2026-09-18 20:30 | 2026-09-18 19:00 |
| sha256 | `12dcd9361ae7b871cc1c02bc146fdeeec83eb681445bfa1f4c1fe920f602e4c6` | `4fcbe5f50d97ed18215e0281a5be0d341390618e635d11d1eb86e832041d3729` |

These are TradingView's own host bars, read from the chart series plot list.
**Nothing is resampled from M5.** The H3 inter-bar gap histogram is 180 min
×291 plus 3060 min ×7 (weekend closes), which is what a genuine 3h FXCM series
looks like.

Depth is plan-capped: `exportData` is refused ("Data export is not supported")
and neither `scrollChartByBar` nor `setVisibleRange` loads more — M45 stops at
529 bars, H3 at 300. Both windows still contain their fixtures.

Transport: M45 came through a Blob download; Chrome then blocked further
automatic downloads from the site, so H3 was copied to the clipboard from the
page and written out with PowerShell. Both files are the page's own CSV text.

## 1. Negative control: the H3 pressure-wick staircase — PASS

Replayed from real H3 host bars (`artifacts/rc5_host_capture/rc5_ohlc_h3.csv`),
not inferred from M15/H4. All six descending BEARISH PRESSURE WICKs released at
the shared availability 2026-08-31 04:00 are refused:

| bar | source | zone | outcome |
|---|---|---|---|
| 156 | 08-25 22:00 | 4657.56–4673.71 | refused — SWING_NEVER_USED_BY_THE_WALK |
| 160 | 08-26 10:00 | 4622.96–4632.94 | refused — NOT_A_PIVOT_ON_ITS_OWN_SIDE |
| 164 | 08-26 22:00 | 4605.02–4627.06 | refused — NOT_A_PIVOT_ON_ITS_OWN_SIDE |
| 171 | 08-27 19:00 | 4610.27–4618.07 | refused — SWING_NEVER_USED_BY_THE_WALK |
| 172 | 08-27 22:00 | 4600.49–4611.42 | refused — NOT_A_PIVOT_ON_ITS_OWN_SIDE |
| 173 | 08-28 01:00 | 4588.67–4601.37 | refused — NOT_A_PIVOT_ON_ITS_OWN_SIDE |

Raw pattern detection TRUE, ordinary swing confirmation TRUE for two of them,
meaningful movement-origin role FALSE, qualified reversal POI FALSE. Exactly
the required outcome.

The three H3 survivors are all genuine: two BULLISH PRESSURE WICKs at
LEG_ORIGIN (bars 71, 94) and one BEARISH PRESSURE WICK at SWING_HIGH_ORIGIN
(bar 184).

## 2. Positive control: the M45 B2S — FAIL

The fixture is found exactly as specified: bar 200, source **2026-09-04
07:00**, zone **4461.42–4486.42**. Under the current role set it is **refused**
with `NOT_A_PIVOT_ON_ITS_OWN_SIDE` — its source candle is not a pivot candle of
any confirmed swing, on either side.

The bars explain why:

```
199  09-04 06:15  o=4468.84 h=4471.78 l=4460.01 c=4462.86
200  09-04 07:00  o=4462.86 h=4486.42 l=4461.42 c=4485.61   <- the B2S
201  09-04 07:45  o=4485.61 h=4490.85 l=4478.87 c=4481.16   <- SWING_HIGH 4490.85
...
207  09-04 12:15  o=4464.70 h=4476.04 l=4379.18 c=4393.83   <- the leg
208  09-04 13:00  o=4393.83 h=4424.02 l=4365.18 c=4423.77
```

Two separate faults, both real:

**(a) Adjacency.** A BUY-TO-SELL candle *is* the last up-candle before the
turn, so the swing high forms on the **next** bar by construction. Matching a
pattern to structure by candle identity therefore systematically misses this
family. This is not a tolerance question — bar 201's pivot 4490.85 is not even
inside the B2S zone.

**(b) The true top holds no role.** Swing high 4490.85 at bar 201 is a confirmed
swing from which a ~125-point bearish leg departs within six bars, and it still
scores `role=NONE`: the walk never broke it and is not protecting it, and the
frozen leg-origin rule could not name it because its origin pool is constrained
to swings *after* the broken swing. The engine instead named bar 211's lower
high (4448.92) LEG_ORIGIN.

So the gate is not merely strict here; it is blind to the specific structure
this fixture is made of.

## 3. The two questionable M15 B2S rejections — both CORRECT

| bar | source | displacement at candle | next 40 bars | verdict |
|---|---|---|---|---|
| 1174 | 2026-09-07 22:00 | VERY_FAST BULLISH (4.59) | drop 26.20, then **exceeds the pivot** (4442.9 > 4414.04) | correct reject |
| 1819 | 2026-09-16 22:30 | NORMAL BULLISH (1.31) | drop 17.31, then **exceeds the pivot** (4335.32 > 4276.09) | correct reject |

Neither is a movement origin: price traded straight back through both highs,
and neither swing was ever broken or protected. No B2S appears anywhere in the
"departure held" population on any host. The current role set is right about
these two.

## 4. Does existing impulse machinery recognise them?

Yes, and that is the warning. Using the frozen `DisplacementObservation`
primitive (`FAST` / `VERY_FAST`), of the M15 `SWING_NEVER_USED_BY_THE_WALK`
rejects **84 of 85** had a FAST-or-better displacement in their own direction
within 40 bars. H4: 79 of 81. M5: 80 of 82.

**"An impulse started here" is not a discriminator at all** — on gold it is true
almost everywhere. A role defined as "confirmed swing + subsequent FAST
displacement" would re-admit essentially the entire rejected population,
including the H3 staircase. That confirms the author's instinct and rules out
the obvious definition.

Adding the requirement that the departure *held* (price did not trade back
through the pivot within 40 bars) cuts it to **17 of 85** on M15, 17 of 81 on
H4, 15 of 82 on M5 — and notably admits **no B2S on any host**. But "within 40
bars" is a new numerical threshold, which is prohibited.

## 5. Reject-reason breakdown

M15, 2000 bars:

| family | refused | NOT_A_PIVOT_ON_ITS_OWN_SIDE | SWING_NEVER_USED_BY_THE_WALK |
|---|---|---|---|
| B2S/S2B | 5 | 3 | 2 |
| STARS | 39 | 21 | 18 |
| ENGULFING | 46 | 32 | 14 |
| HAMMER/SHOOTING | 62 | 40 | 22 |
| PRESSURE WICK | 130 | 101 | 29 |

70% of all refusals are `NOT_A_PIVOT_ON_ITS_OWN_SIDE` — the pattern is not at a
local extreme on the side it claims to defend. Those are the clutter class and
are not in dispute. But the M45 fixture shows this bucket also contains true
origins lost to adjacency, so the headline 88% cannot be taken at face value.

## 6. Five-host impact

| host | bars | source | POI total | reversal | refused | delayed | med/max delay (bars) |
|---|---|---|---|---|---|---|---|
| M5 | 2000 | frozen aligned | 498 → 183 | 349 → 34 | 315 | 19 | 11 / 179 |
| M15 | 2000 | frozen aligned | 455 → 173 | 319 → 37 | 282 | 24 | 18 / 201 |
| M45 | 529 | new capture | 100 → 44 | 63 → 7 | 56 | 5 | 21 / 76 |
| H3 | 300 | new capture | 82 → 42 | 43 → 3 | 40 | 2 | 14.5 / 20 |
| H4 | 2000 | frozen aligned | 483 → 193 | 317 → 27 | 290 | 17 | 9 / 87 |

`families_invented` = [] and `non_reversal_families_removed` = [] on all five.
ORDER BLOCKS unchanged wherever any exist (M5 4→4, M15 4→4, H4 3→3; the M45 and
H3 windows contain none).

**The M45 and H3 windows are short** (plan-capped at 529 and 300 bars), so their
counts are not comparable with the 2000-bar hosts — fewer bars means fewer
confirmed breaks, hence fewer roles. Read them as fixture evidence, not as rates.

P3 / P5 / P8 counts are not reported for M45: the Python `Timeframe` enum has no
M45 member, so that capture was replayed under a carrier label with a 45-minute
duration. The structural-origin gate contains no timeframe-dependent logic, so
the gate result is unaffected — but the downstream layers are timeframe-aware
and their numbers would be meaningless under a carrier label. Adding M45 to the
enum is a contract change (`_TIMEFRAME_STRENGTH_RANK`, the P5 authority set,
BTMM eligibility) and is an author decision, not a forensic side effect.

## 7. Proposed narrow role — NOT IMPLEMENTED, awaiting decision

Two changes are needed, and only the first is a new role.

**(a) Adjacency, which is a bug fix rather than a role.** Resolve a pattern's
structural role from the swing its *formation* terminates at, not only from its
own source candles: a confirmed swing whose pivot bar is the bar immediately
following the pattern's last source candle. This is bounded by the pattern's own
extent, introduces no threshold and no window, and does not widen which swings
count. Without it the B2S family can essentially never qualify.

**(b) `IMPULSE_ORIGIN`.** A confirmed swing extreme that the walk did not name
a leg origin, did not break, and is not protecting, but which is the extreme the
frozen structure walk's **next confirmed break in that direction** departed
from. The causal anchor is that break's `availability_time_utc`, exactly as for
the existing roles. It reuses the walk and the existing transition record; it
adds no threshold and no forward window.

Whether (b) is even required is undecided: it must first be shown that (a) alone
does not rescue the M45 fixture. It probably does not — bar 201's swing high
holds no role at all — but that has to be measured, not assumed.

**Mandatory gate on any such role:** re-run the H3 staircase. If any of the six
wicks qualifies, the definition is rejected. Both of the staircase's
`SWING_NEVER_USED_BY_THE_WALK` members (bars 156, 171) sit in a descending run
where no break departed from them, so the proposed definition should still
refuse them — but that is a prediction, and it will be proven before the role
ships.

## 8. Status

Authority arbitration **not started** and correctly gated: the structural role
set has not passed this forensic review. Qualified-sweep work not started. Pine
untouched (base 95,796 / headroom 4,460).
