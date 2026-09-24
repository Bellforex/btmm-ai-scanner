# DEPLOYING THE SCANNER FOR THE EVENT

Read `RC5_SCANNER_DEPLOYMENT_STATUS.md` first: the chart is running a build from
23 September and is missing all of P4.

Three things below will each, on their own, make a correct deployment look like
"nothing changed". They are the whole reason this runbook exists.

---

## ORDER MATTERS: TWO SCRIPTS, NOT ONE

**`[RC5 VIEW]` does not exist on the account.** The saved list has `[RC5 USER]`
and `[RC5 PANEL]` and nothing else.

The chart currently shows BOS/CHOCH because the **stale** CORE still draws
them. The current CORE does not -- structure moved to VIEW in `4e65243`.

> **Upgrading CORE alone REMOVES the structure overlay from the chart.**

So:

1. create `[RC5 VIEW]` from `tradingview/btmm_poi_btrc_scanner_rc5_view.pine`;
2. save `tradingview/btmm_poi_btrc_scanner_rc5_user.pine` over `[RC5 USER]`;
3. add **both** to the chart (production pair is CORE + VIEW).

## TRAP 1 -- STRUCTURE IS OFF BY DEFAULT

`dspMs` = "Show Market Structure (BOS / CHOCH / swings)" defaults to **false**,
and in VIEW it is the gate on the only structure drawing there is
(`rc5_view.pine:1399`).

Add VIEW to a chart and you get **no structure at all** until this is ticked.
On a fresh study instance it will be off.

## TRAP 2 -- THE TRENDLINE IS OFF BY DEFAULT

`dspTl` = "Show Trendlines" also defaults to **false**, and gates the
structural trendline in CORE (`rc5_user.pine:6628`).

The author sees a trendline today only because it is saved ON in that study's
settings. A freshly added CORE will not show one.

## TRAP 3 -- "SHOW MARKET STRUCTURE" IN *CORE* NOW DOES NOTHING

`dspMs` is still declared in CORE (line 64) but is **not referenced anywhere
else in CORE**. It became vestigial when structure moved to VIEW.

Toggling it in CORE's settings changes nothing on screen. That is confusing to
demonstrate live, so know which script's copy to touch: **VIEW's**.

It is left alone deliberately -- CORE has 73 tokens of headroom and a dead
input is not a correctness defect. Removing it is a post-event change.

---

## THE DISPLAY CONTROLS ALREADY EXIST

No new code is needed to clean up the projector view. CORE already has:

| input | default | what it does |
| --- | --- | --- |
| `p7zMaxVisibleZones` | 8 (1--30) | zone groups drawn, **selected nearest current price** |
| `p7zShowZones` | true | draw POI zone boxes at all |
| `p7zShowLabels` | true | draw POI text -- **turn OFF to kill the overlapping label walls** |
| `p7zProjectBars` | 12 | how far a fresh zone projects right |
| `maxDrawPerFamily` | 20 (1--200) | objects per layer |
| `p7MaxVisiblePois` | 8 (1--20) | rows in the POI table |
| `p7ShowUi` / `p7ShowActivePois` | true | dashboard and POI table |
| 18 type toggles | all true | `BUY ORDER BLOCK` ... `DOJI`, individually suppressible |

The nearest-first selection is real and was verified in source: the renderer
calls `bahui.nearestFirst` and the old position-vs-index bug (which drew the
*oldest* records, off the left edge) is fixed and commented at
`rc5_user.pine:7058`.

### Suggested projector settings

Start from defaults and change only these:

* `p7zShowLabels` **off** if the stacked text is unreadable from the back of
  the room -- the boxes still carry the information;
* `p7zMaxVisibleZones` **4--6** to cut distant clutter;
* `dspMs` **on** (in VIEW) and `dspTl` **on** (in CORE);
* leave the type toggles alone unless a specific family is noise on the day.

---

## STILL UNKNOWN -- NEEDS THE CHART

**Why distant historical zones are on screen.** The obvious explanation is ruled
out: the nearest-first fix landed `d5db718` at 05:45 UTC on 23 September and the
deployed build was saved at 08:41 UTC, so the stale build *does* contain it.

That leaves three candidates, and they are distinguishable only by looking:

1. `p7zMaxVisibleZones` is simply set high in the saved study settings;
2. those zones genuinely *are* the nearest active ones, because price has
   travelled and older zones remain lifecycle-valid -- in which case nothing is
   wrong and the fix is a display setting, not code;
3. a real defect where terminated POIs keep drawing.

Only (3) is a bug. **Do not "fix" this before knowing which it is**, and do not
invent POI age invalidation to tidy the picture -- semantic validity and visual
clutter are different problems.
