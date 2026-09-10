# BTRC V1 — RC2 RELEASE MANIFEST

**Release name:** BTMM + POI + BTRC Scanner [RC2]

RC2 is a **presentation-only promotion** of the live-accepted POI V2 build. No
scanner semantics changed. RC1 is preserved and byte-identical.

---

## ARTIFACT

| Field | Value |
| --- | --- |
| RC2 source | `tradingview/btmm_poi_btrc_scanner_rc2.pine` |
| RC2 SHA256 | `381f2fc2463c4eaa9dc2eb88943f5bc16a83b55a6d4307c390cce5f87f36cc3f` |
| RC2 lines | 6661 |
| RC2 bytes | 358630 |
| Accepted V2 source | `tradingview/btmm_poi_btrc_scanner_rc1_poi_fix_dev.pine` |
| Accepted V2 SHA256 | `bef64353d6e0babb6310683bacd26f026d5fcdc08244e967e5260c4d5e298f34` |
| RC1 source (preserved) | `tradingview/btmm_poi_btrc_scanner_rc1.pine` |
| RC1 SHA256 (unchanged) | `143c0f8817c78bf45e6842e16112cedf67ca36dc694c288808b7748096664c54` |

**Diff from the accepted V2 source: exactly one line — the `indicator()` title.**
Zero non-title differences. Verified mechanically.

---

## PROMOTION COMMITS

| SHA | Subject |
| --- | --- |
| `d7576dd521e5206c8558e4134888c02b67d324ca` | five-cycle cold reconstruction gate, RE10110 resolved |
| `1f0fb10f2566e735db0367bda06b6fccfb544bdf` | Pine sort-and-sweep replacing quadratic grouping |
| `37b59d6e1efd9d901be1492b0404888c9d39d489` | optimized projection model, proven equal to the V2 oracle |
| `7b20457b582c7ed1cde0da03bde9ffa92792bb42` | label anchor fix (stop dragging labels to the right edge) |

---

## SUPPORTED SCOPE

| Item | Value |
| --- | --- |
| Provider | FXCM |
| Symbol | XAUUSD (`FX:XAUUSD`) |
| Host timeframes | **M1, M5, M15, H1** |
| Calculation horizon | `calc_bars_count = 1800` |
| Visual capacity default | 8 visual groups |
| P7 table capacity | 8 semantic POIs |

M1 is newly supported in RC2. RC1's acceptance covered M5, M15 and H1 only.

Scope is what was actually tested. Other providers, symbols and timeframes are
**not** covered by this manifest.

---

## DEFERRED / EXCLUDED (carried forward from RC1)

- **P3 Context** — EQH/EQL plus the 12 calendar/period context types. Deferred,
  not reopened.
- **P4 Reviewed-Evidence Transport** — deferred, not reopened.
- **TradingView technical Alert object creation** — platform/plan-blocked. The
  P8 `alert()` calls are active and closed; creating the Alert object itself is
  a platform limitation, not a scanner defect. Disclosure retained from RC1.
- **Historical terminal POI-zone retention** — remains deferred.
- **Profitability claims of any kind** — excluded.

---

## KNOWN, DOCUMENTED LIMITATIONS

**1. Golden BASE_RALLY live re-trace — N/A, not a defect.**
Registry index 170, M1 BASE_RALLY, top 4349.17, bottom 4347.78, origin 01:41
Europe/London. Its **mechanical geometry is VERIFIED** against source candles.
Its **live visual re-trace is N/A**: the source sits roughly 2114 M1 bars back
while the release calculation horizon is 1800 bars, so the POI is outside the
window and cannot appear. No active in-window BASE_RALLY was available for an
equivalent live check — the five in the latest 500-bar window are all terminal.
This is a documented **evidence limitation**, not a release blocker, not a
detector defect and not a visual defect. `calc_bars_count` and lifecycle
semantics were deliberately NOT altered to manufacture this test.

**2. Fewer labels than boxes on some hosts — expected, not a desync.**
A box's `left` is a bar index. When a zone's origin lies outside the chart's
*loaded* bar window it cannot resolve, so the box reports `left = null` and no
label is placed. Label count always equals the number of boxes with resolvable
origins. Loading more history restores parity: on M5, 300 bars gave 8 boxes / 3
labels / 5 nulls, and 902 bars gave 8 / 8 / 0 with anchors matching exactly.
Independent of `calc_bars_count`, which governs what the study computes rather
than what the chart has fetched.

**3. Two pre-existing Pine warnings**, unchanged from RC1 and from the accepted
V2 build: shadowed `p2TransCount` and `p2LastBrokenLvl` at lines 4631 and 4633.
No errors.

---

## APPROVAL STATUS

| Item | Value |
| --- | --- |
| Technical release candidate | **TRUE** |
| Production trading approval | **FALSE** |
| Profitability established | **FALSE** |
| Autotrading approved | **FALSE** |
| Broker connection approved | **FALSE** |

RC2 is a **technical** release candidate for user-facing presentation. It makes
no claim about trading outcomes.
