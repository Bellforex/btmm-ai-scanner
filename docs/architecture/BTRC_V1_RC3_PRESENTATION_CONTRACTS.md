# BTRC V1 — RC3 PRESENTATION CONTRACTS

Source-time geometry, timeframe naming, host visibility, and annotation
collision. Everything here decides what is **drawn**. None of it changes what
exists: detection, geometry, lifecycle and scoring are untouched by every rule
below.

---

## 1. SOURCE TIME VERSUS AVAILABILITY TIME

Two different fields, never interchangeable.

| Field | Meaning | Used for |
| --- | --- | --- |
| `candidate_event_time_utc` / `poiCandTime` | opening time of the candle or block that created the price area | the **visual left edge** |
| `availability_time_utc` / `poiAvailTime` | the close at which the full validating pattern became knowable | the **freshness clock**, and the exact-geometry dedup key |

The reaction clock starts strictly **after** availability, so a POI can never
consume itself. The box is drawn **from** the source candle but only comes into
existence at availability, which is why anchoring the left edge to the source
introduces no lookahead.

This supersedes `BTRC_V1_P7Z_POI_VISUALIZATION_CLOSURE.md`, which anchored the
left edge to availability specifically to avoid drawing "as if the scanner knew
about the zone before it confirmed". That concern is answered by the second
sentence above: existence is still gated on availability.

### The origin defect this fixed

One shared assignment in the visual layer read availability where the registry
already carried the source time, so **every** POI family started late by exactly
its own pattern span. Measured across a 173-POI H4 registry:

| Pattern span | POI types | Bars late |
| --- | --- | --- |
| 1 candle | pressure wicks, hammer, shooting star | 1 |
| 2 candles | both engulfings, both order blocks | 2 |
| 3 candles | both fair value gaps, both stars, base drop | 3 |
| 4 candles | buy-to-sell candle | 4 |

Confirmed live after the fix: the order-block-plus-engulfing zones moved two
bars left, the stars three, the pressure wick one.

---

## 2. TIMEFRAME TOKENS

`f_p7zTfLabel` mirrors `timeframe_label` in `p7z_zone_model.py`. Numeric first,
calendar suffix second.

| `timeframe.period` | Token |
| --- | --- |
| `1`, `5`, `15`, `45` | M1, M5, M15, M45 |
| `60`, `240`, `360`, `480`, `720` | H1, H4, H6, H8, H12 |
| `1D`, `D`, `1440` | D1 |
| `1W`, `W` | W1 |
| `1M`, `M` | MN1 |
| `30S` | S30 |

### The defect this fixed

The previous formatter exact-matched `"D"`, `"W"` and `"M"` and then tried to
parse the token as a number. TradingView hands a **daily** chart `"1D"`, which
matches neither, so every annotation on a daily host rendered **`TF?`** — the
release blocker in the author's D1 screenshot, reproduced at 8 of 8 boxes and
now 0 of 8.

The differential test that should have caught it existed but its token list
omitted the calendar spellings TradingView actually emits. Those are now in it.

**Release rule:** a POI whose timeframe cannot be named is not drawn. `TF?` must
never reach a user.

---

## 3. HOST VISIBILITY

A POI may be drawn when its origin timeframe is the host timeframe **or higher**.

```
M1 host   M1 M5 M15 H1 H4 D1 W1
M15 host        M15 H1 H4 D1 W1
H4 host                H4 D1 W1
D1 host                   D1 W1
W1 host                      W1
```

Higher-timeframe structure may project down onto a lower host. Lower-timeframe
detail must never climb onto a higher one. Ranks are ordinal, in `TF_RANK`, and
carry no duration meaning. An unranked token is ineligible on both sides.

This is **presentation eligibility only** — the canonical registry keeps every
POI, and P5 and P8 are unaffected.

### Honest scope note

P3 is single-timeframe by construction: the registry carries no per-POI origin
timeframe, so today every POI on a chart originates on that chart and the filter
is a **no-op**. It is implemented and tested anyway, because it is the contract
and because it is the only thing that would stand between a daily chart and a
pile of one-minute boxes the day P3 gains multi-timeframe POIs. What the author
saw as lower-timeframe boxes hanging on the daily chart was not lower-timeframe
contamination — it was the origin defect in §1 plus the annotation pile in §4.

---

## 4. ANNOTATION COLLISION

Zones may overlap. Their **text** may not.

After capacity selection, two zones are in the same collision group when their
price intervals intersect, inclusively. Groups are transitive connected
components. Exactly one zone per group prints its name.

Owner priority, in order:

1. higher origin timeframe
2. smaller distance to current price
3. newer source time
4. lowest canonical registry index

This is a **readability** ordering. It decides whose text survives a pile-up,
never whose setup is better, and it is not a BTRC or BTMM ranking.

A suppressed zone keeps its rectangle, its geometry and its registry identity.
It only stops drawing text, and the P7 active-POI table still lists it, so no
information is lost. Nothing is merged and nothing is deleted.

The Pine port omits the timeframe term because it is constant on a
single-timeframe registry; `p7z_mtf_presentation.py` holds the full ordering.
The Pine loop is O(k³) with k bounded by the visual capacity of 8, so at most
~512 comparisons per confirmed bar — about fifty times smaller than the active
set scan that once caused RE10110, and bounded by an input rather than by market
history.

### Measured on the author's daily chart

| | Before | After |
| --- | --- | --- |
| Boxes drawn | 8 | 8 |
| Annotations printed | 8 | 5 |
| Overlapping annotations | 3 pairs | **0** |
| `TF?` annotations | 8 | **0** |

Three co-located support zones collapsed to one annotation, and a base drop
overlapping a sell order block kept the nearer of the two.

---

## 5. THE RELEASE PIPELINE

```
canonical registry
  -> fresh filter
  -> host-timeframe eligibility
  -> valid source-timeframe integrity
  -> exact-geometry dedup
  -> FVG clustering
  -> proximity order
  -> capacity (8 visual groups)
  -> annotation collision resolution
  -> draw
```

Capacity is presentation only and never caps the registry, P5 or P8.

---

## 6. STYLE

Fresh bullish zones draw a green border with a green fill at 90% transparency;
bearish the same in red. The annotation sits inside the box, centred on both
axes, carrying the full POI name and never the tier, the registry id or any
debug field. Fresh zones project to the right, both through `extend.right` and
through a bounded projected right edge that gives the centred text a real span
to sit in.

Mitigated and invalidated zones are not drawn at all in release mode.

---

## 7. WHAT IS NOT IN THE RELEASE DEV BUILD

The in-box identity annotation compiled but was removed. Together with the
collision resolver it exceeded TradingView's 100256-token limit by 253. The
collision resolver is release-blocking; the identity annotation is a
convenience, and suppressed and selected identities are both already visible in
the P7 active-POI table. A parity build with reduced presentation can carry it
back.

`P5EVAL`, `P9TRACE` and `P7DIAG` were removed from this build for the same
budget reason. `P8EVENT` and `P8PRIME` are kept, because RC3's terminal-cause
evidence depends on them.
