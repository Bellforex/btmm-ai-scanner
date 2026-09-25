# RC5 SCANNER EVENT BUILD -- FROZEN

Frozen 2026-09-25 after live acceptance and verified persistence.

---

## 1. FREEZE RECORD

| | |
| --- | --- |
| repo SHA | `ca4323f` (+ this documentation commit) |
| CORE | `[RC5 USER]` **v21.0** |
| CORE source hash (LF) | `e08051c2e3908ba6...` |
| CORE tokens | **100,211** / 100,256 -- headroom **45** |
| VIEW | `[RC5 VIEW]` **v1.0** |
| PANEL | v2.0 in the script store, **not attached** |
| account | `bellcare1994` |
| layout | `BAH-RC5-LAB` (`/chart/fn3ash9L/`) |
| symbol / timeframe | `OANDA:XAUUSD` H4 |
| publication | **FALSE** |

### Enabled settings

```
CORE   dspMs = true   dspBtmm = true   dspTl = true
       POI zones = ON   POI labels = ON
       all 19 POI type toggles = ON
       p7zMaxVisibleZones = 8   p7zProjectBars = 12   maxDrawPerFamily = 20
VIEW   dspMs = true
```

## 2. HOW PERSISTENCE WAS ACTUALLY PROVEN

This is the gate that failed twice before, so the method matters.

The `navigate` reload is blocked by TradingView's `beforeunload`, which the
chart page **always** registers -- `window.onbeforeunload` is a function
regardless of dirty state, so the guard is not evidence of unsaved work, and
`force: true` is prohibited. The header's "Save" label is likewise always
present and is **not** a dirty indicator.

So persistence was proven by opening a **fresh tab** on the same layout URL,
which loads the server's saved copy without touching the working tab:

| attempt | fresh-tab CORE | verdict |
| --- | --- | --- |
| after first UI save | **v20.0** | save did not land |
| after `POST /api/v1/charts/save/` returned **200** | **v21.0** | **persisted** |

The network read is what settled it. An earlier save reported success through
its callback while `POST /api/v1/charts/save/` had actually failed with
`TypeError: Failed to fetch` -- **the callback is not proof; the request is.**

## 3. FREEZE GATE

| check | status |
| --- | --- |
| CORE v21 persisted after reload | **PASS** -- fresh tab, server copy |
| VIEW v1 persisted | **PASS** |
| exactly one CORE instance | **PASS** |
| all 19 type toggles ON | **PASS** (19/19) |
| zones + labels ON | **PASS** |
| `dspMs` / `dspBtmm` / `dspTl` | **PASS** (all true) |
| VIEW `dspMs` | **PASS** |
| zero invalidated zones visible | **PASS** -- 0 of 8, 142 excluded upstream |
| no stale / duplicate boxes | **PASS** -- 8 drawn against a quota of 8 |
| BOS / CHOCH render | **PASS** |
| exactly one structural trendline | **PASS** |
| BTMM markers | **PASS** |
| scanner console errors | **PASS** -- 0 |
| manual drawings preserved | **PASS** -- 0 before and after |
| final save succeeded | **PASS** -- HTTP 200 |

**All fifteen pass. RC5 SCANNER EVENT BUILD IS FROZEN.**

## 4. THE VISIBLE EIGHT

Verified in `RC5_VISIBLE_ZONE_VERIFICATION.md`: 5 fresh, 1 mitigated-holding,
2 reclaim/false-break. Zero invalidated, zero superseded, zero stale.

Two of them carry 7 and 5 taps and remain correctly visible -- the
mitigated-but-holding and false-break cases the doctrine keeps.

## 5. WHAT FREEZE MEANS

No further ranking experiments, detector tuning, threshold changes, token
hunting or architecture changes before the event. The scanner is stable.

Known, deliberately unchanged:

* the global quota stage is nearest-first; overlap clusters are tier-first via
  `f_rc5DisplayBetter`. Both accepted, both documented;
* order blocks and Doji are detected (121 raw candidates across four captures)
  but gated downstream in these windows;
* the S1/S2 swing-label anchor question is open and is VIEW-only, zero CORE
  cost, if it is ever decided.

## 6. STILL OPEN, EXPLICITLY OUT OF SCOPE FOR THE FREEZE

* the 3x3 manifestation matrix across XAUUSD / EURUSD / GBPUSD;
* the residual study of whether a non-overlapping STRONG zone is ever
  harmfully displaced by the nearest-first quota;
* per-POI pixel geometry on the live chart, deliberately never claimed from
  screenshots.

Next work is EA Strategy Tester acceptance, not the scanner.
