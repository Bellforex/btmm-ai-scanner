# BTRC V1 — POI VISUAL NAMING CONTRACT

Frozen user-facing vocabulary for every drawn POI zone and every P7 table row.
This is UI text only. It carries no semantic meaning and no P3, P4, P5, P6 or P8
behaviour depends on it.

Implemented by `type_label`, `timeframe_label` and `zone_label_v2` in
`tests/parity_support/p7z_zone_model.py`, and ported to `f_p7zTypeLabel` /
`f_p7zTfLabel` / `f_p7zZoneLabel` in
`tradingview/btmm_poi_btrc_scanner_rc1_poi_fix_dev.pine`. Both sides are pinned
by `tests/unit/test_p7z_v2_naming_and_dedup.py`, which transcribes the table
below independently so a silent edit to either side fails.

---

## LABEL SHAPE

```
{TIMEFRAME} • {TYPE}
{TIMEFRAME} • {TYPE} • STRONG
{TIMEFRAME} • {TYPE} + {TYPE}
```

The third form appears only when several POIs share exactly identical geometry
and are therefore drawn as one box. See the deduplication section.

The separator is the bullet `•` with a single space either side.

---

## TIMEFRAME TOKEN

Pine's `timeframe.period` is a **raw token**: `1`, `5`, `15`, `60`, `D`, `W`. It
must never be rendered directly. Doing so produced labels reading `1 • BUY FVG`
on M1 charts, where the leading `1` reads as a quantity rather than a timeframe.

| Pine period | Rendered |
| --- | --- |
| `1` | `M1` |
| `5` | `M5` |
| `15` | `M15` |
| `30` | `M30` |
| `60` | `H1` |
| `120` | `H2` |
| `240` | `H4` |
| `720` | `H12` |
| `1440` or `D` | `D1` |
| `W` | `W1` |
| `M` | `MN1` |
| unparseable | `TF?` |

Rules: minutes below 60 render `M<n>`. Whole hours below a day render `H<n>`.
Calendar tokens map to `D1`, `W1`, `MN1`. Anything unparseable renders `TF?`,
never a bare number and never a fabricated timeframe.

**A rendered timeframe never begins with a digit.** A test asserts this across
every token TradingView can supply.

The timeframe shown is always the **host chart timeframe**. The P3 registry
carries no per-POI origin-timeframe field, because P3 is single-timeframe by
construction, so a POI's origin timeframe is the chart that detected it.

---

## THE EIGHTEEN TYPE NAMES

| # | P3 type | Rendered |
| --- | --- | --- |
| 1 | BUY_ORDER_BLOCK | `BUY OB` |
| 2 | SELL_ORDER_BLOCK | `SELL OB` |
| 3 | BUY_FAIR_VALUE_GAP | `BUY FVG` |
| 4 | SELL_FAIR_VALUE_GAP | `SELL FVG` |
| 5 | BUY_TO_SELL_CANDLE | `B2S` |
| 6 | SELL_TO_BUY_CANDLE | `S2B` |
| 7 | BASE_RALLY | `BASE RALLY` |
| 8 | BASE_DROP | `BASE DROP` |
| 9 | BULLISH_PRESSURE_WICK | `BULL PRESSURE` |
| 10 | BEARISH_PRESSURE_WICK | `BEAR PRESSURE` |
| 11 | BULLISH_ENGULFING | `BULL ENGULF` |
| 12 | BEARISH_ENGULFING | `BEAR ENGULF` |
| 13 | HAMMER | `HAMMER` |
| 14 | SHOOTING_STAR | `SHOOTING STAR` |
| 15 | MORNING_STAR | `MORNING STAR` |
| 16 | EVENING_STAR | `EVENING STAR` |
| 17 | SUPPORT_ZONE | `SUPPORT` |
| 18 | RESISTANCE_ZONE | `RESISTANCE` |

Any type code outside this closed set renders `UNKNOWN`. That deliberately
includes the liquidity and period-level types 19 to 32, which the zone layer
does not draw.

**No name repeats a word.** A test enforces this, so a label can never read
`RALLY BASE RALLY`.

---

## STRONG TIER

`• STRONG` is appended only for tier `STRONG`. Standard and not-applicable tiers
add nothing. On a merged box the suffix appears when **any** contributing POI is
strong, because the box stands for all of them.

---

## EXACT-GEOMETRY DEDUPLICATION

Two POIs are drawn as one box only when **all four** of these match exactly:

- zone top
- zone bottom
- availability time
- direction

Type and tier are deliberately excluded from the key. Differing types is the
whole point: an order block and an engulfing routinely anchor on the same origin
candle and produce identical rectangles.

The merged label names every contributing type once, in the group's own order:

```
M15 • BUY OB + BULL ENGULF
M1 • HAMMER + BULL PRESSURE
```

**Overlap alone never merges anything.** Two zones that merely intersect, even
one wholly inside another, remain separate boxes. No percentage-overlap
clustering rule exists, and none may be added without an explicit author
decision.

**Registry identity is never merged.** P3, P5 and P8 continue to see every POI
as its own entity. Only the count of drawn objects collapses, and no POI is
hidden, because every contributing type is named in the label.

Measured on the live FX:XAUUSD M1 capture of 2026-09-09, 258 registry entries
contained 28 exact-geometry groups covering 56 POIs, which collapse to 28 boxes.
The recurring pairs are:

| Pair | Why they coincide |
| --- | --- |
| `BUY OB + BULL ENGULF` | both anchor on the same bearish origin candle |
| `SELL OB + BEAR ENGULF` | mirror case |
| `HAMMER + BULL PRESSURE` | same single candle satisfies both wick tests |
| `SHOOTING STAR + BEAR PRESSURE` | mirror case |

---

## LABEL PLACEMENT

The label anchors at the zone's **origin**, its left edge, not at `time_close`.

Every visible zone extends to the right edge of the chart, so anchoring labels
there stacked all of them on one x coordinate, where they overlapped into an
unreadable pile and ran off-screen entirely once the boxes extended past the
viewport. The origin is unique per zone and is where a trader looks to see what
created the zone.

Bullish zones label below the zone bottom, bearish zones above the zone top, so
the text does not sit on the candles inside the zone.
