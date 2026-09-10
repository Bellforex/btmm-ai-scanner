# BTRC V1 — RC2 RELEASE CHECKLIST

Artifact: `tradingview/btmm_poi_btrc_scanner_rc2.pine`
SHA256: `381f2fc2463c4eaa9dc2eb88943f5bc16a83b55a6d4307c390cce5f87f36cc3f`

Live environment: account **bellcare1994**, provider **FXCM**, symbol
**FX:XAUUSD**, chart `6cu1b2O7`, studies **RC2 + P6 DEV**.

---

## SOURCE INTEGRITY

| Gate | Result |
| --- | --- |
| RC2 diff vs accepted V2 source | **1 line** — the `indicator()` title |
| Non-title semantic differences | **0** |
| RC1 SHA256 | `143c0f88…64c54`, **unchanged** |
| Accepted V2 saved script overwritten | **NO** — RC2 saved separately |
| `git diff --check` | clean |

Feature verification on the RC2 source: proximity selection, capacity 8 default
(zones and table), M1…W1 timeframe naming, origin-anchored labels, exact-geometry
dedup via map key, FVG overlap-or-touch sweep, sentinel flush, neutral gray fill
— all present. Old quadratic loop (`p7zGrpOf`) and old per-bar
`label.set_x` reposition — both **0 occurrences**.

---

## LIVE COMPILE

| Gate | Result |
| --- | --- |
| Pine version | v6 |
| Compile errors | **0** |
| Token limit | within limit |
| Warnings | 2, pre-existing and unchanged (shadowed `p2TransCount`, `p2LastBrokenLvl`) |
| Saved as | `BTMM + POI + BTRC Scanner [RC2]` (separate script) |

---

## LIVE HOST SMOKE (RC2 attached)

| Host | Failed | Code | Boxes | Labels | Tables | Studies | Capacity | Anchors match | RE10110 | RE10041 | RE10045 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| M1 | false | none | 8 | 8 | 2 | 2 | 8 | yes | 0 | 0 | 0 |
| M5 | false | none | 8 | 8 | 2 | 2 | 8 | yes | 0 | 0 | 0 |
| M15 | false | none | 8 | 7 | 2 | 2 | 8 | yes | 0 | 0 | 0 |
| H1 | false | none | 8 | 7 | 2 | 2 | 8 | yes | 0 | 0 | 0 |

Label counts below 8 are the documented loaded-window artifact; anchors match
the resolvable box lefts in every case.

---

## M5 FRESH-TAB COLD BOOT (packaging confirmation)

A genuinely fresh browser tab opening the saved layout directly on M5. Read only
after `isFailed() || isCompleted()`, then re-read after a further 34 s.

| Gate | Result |
| --- | --- |
| Studies reconstructed | RC2 + P6 DEV (exactly 2) |
| Settled | 2797 ms |
| Failed | **false** |
| Error code | none |
| Boxes / labels / tables | 8 / 6 / 2 |
| RE10110 / RE10041 / RE10045 | 0 / 0 / 0 |
| Held on re-read (+34 s) | **yes**, `isCompleted: true` |

This is a packaging confirmation. It does **not** replace the V2 five-cycle
cold-boot evidence, which remains the acceptance authority.

---

## VISUAL AND LIFECYCLE

| Gate | Result |
| --- | --- |
| RE10110 | **RESOLVED** |
| Label anchoring (`label x == box left`) | **TRUE** on every host |
| Labels migrated to `time_close` | **0** |
| LABEL_MIGRATION | **FALSE** |
| Object counts | bounded at 8 boxes / ≤8 labels / 2 tables |
| Duplicate study instances | **0** |
| OBJECT_LEAK | **FALSE** |

---

## OFFLINE GATES

| Gate | Result |
| --- | --- |
| Full pytest | **4469 passed, 0 failed** |
| Targeted P7 / P7-Z / V2 / grouping / label / lifecycle | 581 passed |
| RC1 semantic-equivalence suite | 7 passed |
| ruff (changed files) | clean |
| mypy `src` | clean, 138 files |
| `git diff --check` | clean |

---

## FROZEN ENGINE AUTHORITIES

Unchanged, by construction — RC2 differs from the accepted V2 source only in the
indicator title, and no `src/` file was touched across the promotion commits.

| Phase | Authority |
| --- | --- |
| P5 | 240850 / 240850; H1 351473241, H2 335238294 |
| P6 | 30 / 30 |
| P8 | 456 / 456; H1 294719549, H2 35571918 |
| P9 | H1 224768619, H2 772693120 |

Stated precisely: these digest values live in the closure documents rather than
as literals in test code. What the run proves is that every parity test passes
and no engine source changed.

---

## APPROVAL

| Item | Value |
| --- | --- |
| Technical release candidate | TRUE |
| Production trading approval | **FALSE** |
| Profitability established | **FALSE** |
| Autotrading approved | **FALSE** |
