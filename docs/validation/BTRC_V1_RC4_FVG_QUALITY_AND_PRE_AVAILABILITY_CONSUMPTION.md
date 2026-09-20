# BTRC-V1 RC4 — FVG QUALITY + PRE-AVAILABILITY CONSUMPTION

Author decision, 2026-09-19/20, following the `M15 • BUY FVG ×3` forensic audit
(`tests/unit/test_rc4_fvg_x3_forensic.py`). RC4 profile only. RC3 is frozen and
untouched: the same bars still produce the same three FVGs under RC3.

## 1. What the forensic audit established

The displayed group was **not** a Pine defect, a grouping defect, a stale count
or a lookahead defect. Python and Pine produced bit-identical output. The group
was three genuinely detected three-candle imbalances:

| member | 1st candle (UTC) | zone | gap / ATR14 | departure `range_speed_ratio` |
|--------|------------------|------|-------------|-------------------------------|
| 392 | 2026-09-17 06:45 | 4311.88 – 4319.27 | 0.771 | 1.738 (FAST) |
| 393 | 2026-09-17 07:00 | 4323.42 – 4329.23 | 0.602 | 1.301 (normal) |
| 395 | 2026-09-17 10:30 | 4318.43 – 4323.90 | 0.649 | 1.093 (normal) |

All three became available only at 12:30 (`MAPPED_REVERSAL_CONTEXT`), and 392
and 393 had already been **100 % re-filled before that availability** (392's
imbalance was traded through to 4305.01).

Root cause: qualification was too permissive. The frozen gap rule measures the
**gap**, never the departure candle's expansion (Register §35J's expansion rule
was measured and *not* adopted in RC3), and nothing refused an imbalance that no
longer existed at the moment it was released.

## 2. The correction (RC4 only, `PoiConfiguration.rc4_fvg_quality`)

Two additional necessary conditions, both built from numbers that already exist.
**No new multiplier was invented; the grouping algorithm was not changed; FVG
geometry was not shrunk.**

1. **Departure must be a real expansion.** The frozen displacement primitive
   (`range_speed_ratio` = total range / median total range of the previous
   `range_context_window` = 20 bars, `domain/displacement.py`) must class the
   departure candle at least **FAST** (`displacement_fast_ratio` = 1.50) —
   rejection reason `NO_DISPLACEMENT` — **and** its full range must strictly
   exceed the immediately preceding candle's full range — rejection reason
   `PREDECESSOR_NOT_EXPANSIVE`.
2. **Qualification at availability.** An FVG whose imbalance was already
   **fully** consumed between the bar that completed it and the (possibly much
   later, reversal-context) bar that made it available is refused —
   `PRE_AVAILABILITY_CONSUMED`. A *partial* pre-availability fill does **not**
   reject and still does **not** mitigate: the frozen lifecycle rule
   ("a pre-availability touch never mitigates") is unchanged.

The consumption window is derived from the **third source candle's own
availability**, not from `confirmation_time_utc` — the structural-context gate
rewrites that field to the delayed release time, so reading it would have made
the check vacuous (this was a real bug found and fixed during implementation).
The check reads only bars closed at or before the release bar: **no lookahead**.

## 3. Verdict on the three members

| member | RC3 | RC4 |
|--------|-----|-----|
| 392 | MAPPED | `PRE_AVAILABILITY_CONSUMED` |
| 393 | MAPPED | `NO_DISPLACEMENT` |
| 395 | MAPPED | `NO_DISPLACEMENT` |

Qualified FVG count in that region under RC4: **0**, as the author predicted —
in Python **and** in the live Pine registry (all three absent from `P3LIFE`).

## 4. Pine port

`tools/rc4_pine_build/rc4_fvg.py`, applied by `build_rc4_pine.py` to both
builds:

* emit-site guard `fvgDepOk` using the existing `f_medianRange`,
  `C_RANGE_CONTEXT_WINDOW` and `C_DISP_FAST_RATIO`;
* release-site guard `cpOk` in the context-pending release loop.

USER token budget was made to fit **without removing semantic functionality**:
the inert `P9 integrated trace log` input (the trace lives in the PARITY build)
and three purely informational dashboard rows (momentum acceleration, pullback,
session) were removed.

## 5. Evidence

* **Aligned bounded parity**, fresh same-session capture
  (`artifacts/rc4_aligned_v2/`, RUNMETA host checksum `31903896.42999992`,
  500 Level-A bars / 300 compared bars):
  * P3 93 matched, 0 python-only, 0 pine-only, **0 field mismatches**
  * P5 1 634 rows compared, **0 mismatches**
  * P8 394 Pine / 394 Python, **0 payload, 0 ordering, 0 terminal anomalies**
  * `first_divergence: null`
* **Live chart** FX:XAUUSD M15 with USER v16: the `×3` zone is gone
  (`artifacts/rc4_fvg_forensic/live_m15_rc4_after.png`); M1/M5/M15/H1/H4/D1/W1
  all run without runtime error.
* **Regression fixtures**: `tests/unit/test_rc4_fvg_x3_forensic.py` (real bars),
  `tests/unit/test_rc4_fvg_quality_rules.py` (synthetic rule matrix).

## 6. Impact (pre-gate FVG qualification, RC3 → RC4)

| window | raw | RC3 qualified | RC4 qualified | `NO_DISPLACEMENT` | `PREDECESSOR_NOT_EXPANSIVE` | `QUALITY_REJECT` |
|--------|-----|---------------|---------------|-------------------|------------------------------|------------------|
| M15 120 | 24 | 9 | 6 | 3 | 0 | 15 (unchanged) |
| M15 300 | 69 | 24 | 12 | 12 | 0 | 45 (unchanged) |
| M15 500 | 117 | 39 | 22 | 16 | 1 | 78 (unchanged) |
| H1 120 | 27 | 5 | 2 | 3 | 0 | 22 (unchanged) |
| H1 300 | 62 | 18 | 8 | 9 | 1 | 44 (unchanged) |
| H4 120 | 29 | 9 | 6 | 3 | 0 | 20 (unchanged) |

Downstream, over the bounded backtest windows:

| window | POIs evaluated | P5 rows | P8 events |
|--------|----------------|---------|-----------|
| M15 120 | 269 → 244 | 17 558 → 15 680 | 560 → 497 |
| M15 300 | 503 → 454 | 49 068 → 43 920 | 1 992 → 1 784 |
| H1 120 | 600 → 538 | 21 242 → 18 927 | 1 659 → 1 434 |
| H4 120 | 1 405 → 1 306 | 27 746 → 25 453 | 4 129 → 3 661 |

No permission band, weight or BTMM threshold changed; the reduction is entirely
fewer qualified FVGs and their downstream rows.
