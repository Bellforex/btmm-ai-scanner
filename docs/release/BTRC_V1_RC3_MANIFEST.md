# BTRC V1 — RC3 SEMANTIC FREEZE MANIFEST

**Semantic code SHA: `3f9f79099c5fb2b9102f5c68a484c6381e6e683f`** (`3f9f790`),
branch `rc3-ob-origin-revision`, pushed, **not merged**. RC3 is a *semantics*
freeze, not a promoted release: no RC3 release Pine file is cut, nothing is
merged to main, nothing is published to TradingView, no live broker exists.
RC1 and RC2 remain frozen and byte-identical.

---

## ARTIFACTS

| Field | Value |
| --- | --- |
| USER DEV source | `tradingview/btmm_poi_btrc_scanner_rc3_poi_semantics_dev.pine` |
| USER DEV SHA256 | `a24672606520e561bb8dad9906519c5fd97e7363d4928fdc113702876df7b93a` |
| USER DEV lines / bytes | 6931 / 375 814 |
| USER DEV TradingView version | v30 (saved-source SHA256 equals the file) |
| PARITY DEV source | `tradingview/btmm_poi_btrc_scanner_rc3_parity_dev.pine` |
| PARITY DEV SHA256 | `84d3f7e7874870afdc3899cf8bf0652d6eda4a2f59df1195ba60f093f6dbd190` |
| PARITY DEV lines / bytes | 6627 / 357 810 |
| PARITY DEV TradingView version | v13 (saved-source SHA256 equals the file) |
| RC1 (preserved) | `143c0f8817c78bf45e6842e16112cedf67ca36dc694c288808b7748096664c54` |
| RC2 (preserved) | `381f2fc2463c4eaa9dc2eb88943f5bc16a83b55a6d4307c390cce5f87f36cc3f` |

---

## FREEZE COMMITS

| SHA | Subject |
| --- | --- |
| `6400352a3036f9efcc8a9763200eb7a832dda27b` | structural context gate + hammer/shooting-star precedence (decisions A, B, C) incl. Pine USER v30 / PARITY v13 |
| `c53d3ac7de821697dfb3d9da13a30ad6c1588942` | small fixtures given a confirmed structure (test-only) |
| `68c03db72c63f1b46f264bd1eea2cb4c460d52fc` | docs, non-FVG matrix, audit tooling |
| `3f9f79099c5fb2b9102f5c68a484c6381e6e683f` | BTMM incremental replay: FALSE POI invalidation is not terminal |

Documentation-only commits made after the authority run are recorded as the
FREEZE RECORD SHA and do not rerun the authority.

---

## FROZEN SEMANTICS (RC3)

| area | rule |
|---|---|
| POI mapping | RAW → TYPE QUALITY → SAME-ORIGIN ARBITRATION → STRUCTURAL CONTEXT GATE → QUALIFIED MAPPED POI → LIFECYCLE → P5 → P8 |
| context gate (A) | trend-aligned at availability maps; counter-trend maps only at a break confirming a leg it formed inside; neutral stays raw; ORDER BLOCK and S/R are structural by contract and not re-gated |
| arbitration (B) | HAMMER > same-candle BULLISH PRESSURE WICK; SHOOTING STAR > same-candle BEARISH PRESSURE WICK; every other non-FVG pair kept separately |
| FVG quality (C) | gap ≥ 0.35 × Wilder ATR-14 of the departure candle (0.349999 rejects); §35J not adopted |
| ORDER BLOCK | leg origin of a confirmed P2 break; immutable once available |
| lifecycle | source = formation origin; availability = structural confirmation; freshness strictly after availability; pre-availability touches never mitigate; earliest terminal cause wins; no expiry |
| confluence | Fibonacci, trendline, S/R and liquidity are metadata, never creation gates |
| P5 / P8 | P5 on `source_timeframe`, terminal-bar inclusion, next-bar exclusion; P8 native ordering |
| P6 | CLOSED, untouched |

---

## RELEASE GATE STATUS

| gate | status |
|---|---|
| full suite (sealed test excluded) | PASS — 4 875 passed, 0 failed |
| ruff / mypy / diff-check | PASS |
| fresh P3 / P5 / P8 parity (context-gated engine) | PASS — 0 mismatches |
| P6 | CLOSED (unchanged) |
| live acceptance M1..W1 | PASS — status OK, 0 unlabeled zones |
| bot adapter compatibility (read-only) | PASS — 55/55 against `3f9f790` |
| final full authority | PASS — 1 836 / 1 836 bars, complete, exit 0, Task Scheduler result 0; all seven frozen checks PASS; deterministic vs both witnesses (12 + 19 days, 0 mismatches) |
| SEMANTIC FREEZE READY | **TRUE** (semantic code SHA `3f9f790`) |
| production approved | **FALSE** |
| merged to main | **FALSE** |
| published to TradingView | **FALSE** |
| live broker | **NONE — paper / dry-run only** |

---

## SUPPORTED SCOPE

FX:XAUUSD (FXCM feed) on M1, M5, M15, H1, H4, D1, W1. Analytical output only:
POIs, BTMM setup states, P5 analytical permission, P8 events. No entries, stops,
targets, position sizing, profitability claim or trade recommendation. Evidence
classification stays ENGINEERING_PROVISIONAL.

---

## RELATED DOCUMENTS

* `docs/validation/BTRC_V1_RC3_SEMANTIC_FREEZE.md` — measurements, parity, authority
* `docs/release/BTRC_V1_RC3_EVIDENCE_INDEX.md` — every claim and where it is proven
* `docs/release/BTRC_V1_RC3_ROLLBACK_AND_RECOVERY.md` — restore points, recovery
* `docs/release/BTRC_V1_RC3_POST_FREEZE_PLAN.md` — branches, bot handoff, demo runbook
