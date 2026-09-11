# BTRC V1 — RC3 PARITY STATUS

Where the three new parity authorities actually stand, after building the
parity DEV the campaign authorises. Written so the gap is legible rather than
buried.

| Authority | Status |
| --- | --- |
| P6 transport | **PROVEN UNCHANGED** |
| P8 events | **LIVE CONTRACT EVIDENCE** — not a row-for-row differential |
| P3 lifecycle | **NOT CAPTURED** |
| P5 observations | **NOT CAPTURED** |

---

## P6 — proven unchanged

Three independent checks, all mechanical, all pinned by tests:

1. The P6 transport block is **byte-identical** between RC2 and the RC3 DEV —
   292 lines each, sha256 `52ceb8eed5a679b49b4e507cdb377301cb43204972fbc5431366792ba0ed21a3`.
2. **Zero** of the fourteen symbols RC3 introduced or repurposed appears
   anywhere inside that block.
3. **Zero** P3 registry arrays appear inside it either. P6 projects P1
   measurements; there is no data path from the POI registry into it, so the
   RC3 lifecycle work cannot reach it even indirectly.

No `src/` file outside `poi/` changed. This upgrades P6 from "argued unchanged"
to "measured unchanged", and `test_rc3_pine_block_immutability.py` fails if any
of it drifts.

---

## The parity DEV build

`tradingview/btmm_poi_btrc_scanner_rc3_parity_dev.pine`, saved on TradingView as
**BTMM + POI + BTRC Scanner [RC3 PARITY DEV]**. Compiles clean: 0 errors, the
same two pre-existing shadowing warnings as every other build, no token
overflow.

Presentation gives way, semantics do not. The entire P7-Z drawing block is
absent — 402 lines — which buys the budget for the debug transports. Verified
by hashing each semantic span against the release DEV:

| Span | Identical |
| --- | --- |
| P1 measurements | yes, apart from the `indicator()` title line |
| P3 POI foundation | **yes** |
| P4 BTMM | **yes** |
| P6 transport | **yes** |

Restored in it: `P5EVAL`. Added: `P3LIFE`, a new stream carrying every field RC3
added to P3 — source time, availability, geometry, taps, first touch,
invalidation time, terminal reason and fresh-active.

---

## P8 — live contract evidence

One real capture from that build on FX:XAUUSD H4, account bellcare1994, over the
full 1800-bar window. Persisted at `artifacts/rc3_parity/rc3_parity_logs_h4.csv`,
sha256 `72b83d331cfd9ccf1c4ce6d4344bff51bdb6999370db93327c8c45e2cb3b020a`.

| Measure | Value |
| --- | --- |
| Events | 2200 |
| `POI_ACTIVATED` | 986 |
| `POI_TERMINAL` | 945 |
| `PERMISSION_ENTERED_ACTIONABLE` | 136 |
| `PERMISSION_LOST_ACTIONABLE` | 133 |
| Distinct POIs going terminal | **945** |
| Duplicate terminal events | **0** |
| Terminals missing a reason | **0** |
| `terminalReason = MITIGATED` | 945 |
| `terminalReason = INVALIDATED` | 0 |
| Terminal before activation | **0** |

Every clause of the RC3 terminal contract holds on real data: exactly one
terminal per POI, never repeated, always labelled, never before activation. The
all-mitigation distribution matches what the 299-bar Python replay reported at
much smaller scale, for the same reason — a zone is almost always touched before
it breaks down.

**What this is not.** It is not a Python-to-Pine row comparison. The captured
Pine registry spans 1800 H4 bars and the Python replay fixture spans 299, so
registry indices do not align and a field-by-field differential is not possible
from this capture. Calling it a parity authority would overstate it.

---

## P3 and P5 — not captured

**P3LIFE did not emit.** The first build guarded it on `barstate.islast`, which
is unreachable there: the whole section sits inside `if barstate.isconfirmed`,
and the last bar is not confirmed while it is still forming. The guard was
corrected to `barstate.islastconfirmedhistory` and the build recompiled clean,
but the Pine Logs panel would not re-bind to the parity study after the
remove-and-re-add cycle — it stayed pinned to the P6 DEV stream — so no second
capture was taken. The fix is in the source and untested live.

**P5EVAL was not captured.** It is per-POI per-bar. The P8 stream alone filled
TradingView's log buffer before the run reached the last bar, which is also why
the first P3LIFE attempt would have been truncated even with a correct guard.
A P5 capture needs either a shorter window or a build that emits only P5EVAL.

Neither is blocked by anything architectural. Both need another capture session.

---

## CONSEQUENCE

RC3 is **not promotion-ready**. Two of the three new authorities the campaign
names as closure conditions do not exist, and the third is contract evidence
rather than a differential.

RC2's digests remain historical comparison only and are not claimed as RC3
evidence. V1-A0 must rerun against RC3 semantics after RC3 freezes. The
characterization summary and OOS remain sealed and unopened.
