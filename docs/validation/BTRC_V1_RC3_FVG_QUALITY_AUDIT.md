# BTRC V1 — RC3 FVG quality audit

Real FXCM XAUUSD, unsealed segments only, no future price reaction used.
Tools: `tests/parity_support/rc3_fvg_quality_audit.py` (distributions),
`tests/parity_support/rc3_qualification_coverage.py` (pipeline counts).

## 1. Author cases (M15, 2026-09-17)

| FVG | zone | gap | gap / ATR14 (departure) | departure range / median prev 20 (frozen displacement) | §35J expansion (departure / max prev 3) | 3-candle net move / ATR | author |
|---|---|---|---|---|---|---|---|
| source 05:15 | 4294.06–4295.89 | 1.83 | **0.19** | 1.23 (NORMAL) | 1.36 | 1.08 | weak (X) |
| source 05:30 | 4298.06–4304.27 | 6.21 | **0.64** | 0.99 (NORMAL) | 0.80 | 2.66 | valid (tick) |

Findings:

* The frozen displacement classification (`domain/displacement.py`, FAST ≥ 1.50,
  VERY_FAST ≥ 2.00) calls both NORMAL and ranks the weak one faster.
* Register §35J's documented-but-unimplemented displacement requirement
  (middle candle ≥ 2.0 × largest of the 3 preceding candles, Small Candle
  Standard) rejects BOTH — including the approved one — and ranks them in the
  opposite order.
* Gap width relative to ATR and the net three-candle move separate the pair.

## 2. Distributions (raw FVGs)

| TF | raw | gap/ATR p10 / p50 / p90 | departure speed p50 | pass §35J ≥ 2.0 | pass gap ≥ 0.35 ATR | pass gap ≥ 0.50 ATR |
|---|---|---|---|---|---|---|
| M5 | 456 | 0.042 / 0.253 / 0.832 | 1.33 | 7 % | 38 % | 25 % |
| M15 | 430 | 0.048 / 0.256 / 0.783 | 1.34 | 7 % | 39 % | 24 % |
| H1 | 349 | 0.044 / 0.263 / 1.069 | 1.34 | 13 % | 38 % | 26 % |
| H4 | 409 | 0.051 / 0.325 / 1.015 | 1.49 | 16 % | 47 % | 33 % |

## 3. Decision and rule

Author decision (2026-09-17, after the evidence above): **an FVG is mapped only
when gap ≥ 0.35 × Wilder ATR-14 of its departure (middle) candle.**
`PoiConfiguration.fvg_min_gap_atr_ratio = 0.35`; Pine `C_POI_FVG_MIN_GAP_ATR`.
The ATR is final at the departure close, before availability (third close): no
lookahead. During ATR warm-up an FVG cannot qualify. §35J's expansion rule stays
documented-not-implemented; this replaces it for mapping.

## 4. Tests (`tests/unit/test_rc3_poi_qualification.py`)

Author pair (raw TRUE both; mapped FALSE / TRUE, gap ratios < 0.25 / > 0.60);
tiny gap rejected; exact 0.35 boundary mapped, 0.349 rejected; no ATR ⇒ reject;
threshold must be positive; mapping decided at availability never changes when
bars are appended; kernel == batch; Pine USER/PARITY constant and gate locked.

## 5. Pipeline counts (all unsealed segments)

RAW → QUALITY → ARBITRATION → MAPPED (BUY / SELL):

| TF | BUY FVG | SELL FVG |
|---|---|---|
| W1 | 289 → 175 → 113 → 113 | 234 → 121 → 66 → 66 |
| D1 | 281 → 162 → 114 → 114 | 169 → 97 → 52 → 52 |
| H4 | 228 → 142 → 86 → 86 | 181 → 101 → 60 → 60 |
| H1 | 173 → 87 → 51 → 51 | 176 → 82 → 42 → 42 |
| M15 | 208 → 107 → 69 → 69 | 222 → 97 → 61 → 61 |
| M5 | 218 → 106 → 64 → 64 | 238 → 126 → 73 → 73 |

Live FX:XAUUSD M15 (USER DEV v29): the 05:15 FVG is no longer drawn; the 05:30
FVG is.
