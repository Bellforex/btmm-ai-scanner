# BTRC-V1 — P6 transport closure (superseding)

Status: **P6 MTF CORE = CLOSED · P6 ORIGINAL SEMANTICS = UNCHANGED ·
P6→P5 TRANSPORT = COMPLETE · P6→P5 REAL PARITY = VERIFIED**
Branch: `pine-p4-btmm`
Closed: 2026-09-04

---

## 1. What this document is

`BTRC_V1_P6_MTF_CLOSURE.md` closed P6's original cross-timeframe substrate —
the fourteen-scalar projection, five transported surfaces, six requested
contexts. That closure is **not amended**: its evidence (30/30, H1 74231825 /
H2 124714621) is reconfirmed unmodified in §3 below, not replaced.

This document closes the ADDITIVE work that followed: exporting twenty-six
further bounded values P5 needs, appended as one object per context, without
touching a single one of the original fourteen positions, the request
architecture, or P1–P4.

## 2. Lineage

```
ORIGINAL P6 CLOSURE                a42c1545a58c0039a275a7859829f3ddf6110012
P5 TRANSPORT AUDIT (no category D)  cc8d268 .. 116dbec
26-FIELD ORACLE + MUTATIONS         116dbec
ADDITIVE PINE EXTENSION             478d89e
SENTINEL BOUNDARY FIX               5e0601a
UDT LITERAL-DEFAULT FIX (live)      a6842a2
RESOURCE ATTRIBUTION (GO)           a1f50b7
REAL TRANSPORT PARITY               (this commit's parent)
SUPERSEDING CLOSURE                 (this commit)
```

History is not rewritten. `a42c1545` remains reachable and its evidence file
untouched.

## 3. Old core: reconfirmed, not re-proven from scratch

| claim | evidence | result |
|---|---|---|
| old 14 scalar positions unchanged, in order | `test_p6_transport_extension_source.py::test_every_request_preserves_its_fourteen_original_names_in_order` | PASS |
| extension is position 15, nothing reordered | same file, `test_the_extension_is_appended_at_position_fifteen` | PASS |
| request count unchanged (6) | same file, `test_the_request_count_is_unchanged` | PASS |
| no second detector/walk/ATR engine | same file, `test_no_analytical_engine_gained_a_call_site` | PASS |
| plot count unchanged (63/64) | same file, `test_the_plot_count_is_unchanged_at_sixty_three` | PASS |
| execution envelope unchanged (1250/1251/1800) | same file, `test_the_execution_envelope_is_untouched` | PASS |
| confirmed-only (no forming-bar leak in new code) | same file, `test_every_extension_assignment_is_inside_the_confirmed_guard` | PASS |
| **historical** frozen artifact, 30/30 | `test_p6_real_data_parity.py` (unmodified) | **61/61 passed** |
| **new-anchor** old surfaces, 30/30 | `test_p6x_transport_real_parity.py::test_old_30_of_30_at_new_anchor` | **30/30 exact** |

P1, P2, P3, P4 are untouched: no file under those closures' evidence chains
was modified by this campaign.

## 4. New transport: proven on real FXCM data

Full detail in `BTRC_V1_P6X_TRANSPORT_REAL_PARITY.md`. Summary:

```
6/6 real input identity           (rows, first, last, H1, H2 — all 5 dims)
156/156 field-level real parity   (26 fields x 6 timeframes, 0 mismatches)
Transport digest                  Python-derived regression fingerprint
                                   (not an independent Pine fold — see
                                   BTRC_V1_P6_P5X_RESOURCE_ATTRIBUTION.md §ownership)
```

Preceded by the synthetic proof that established the reduction itself is
correct, independent of any live capture:

```
26-field oracle: directed / randomized (3000 cases) / prefix / mutation (22)
```

## 5. Resource status

`BTRC_V1_P6_P5X_RESOURCE_ATTRIBUTION.md`: classification D (not reliably
attributable), zero runtime failures across eight controlled operations plus
the full live capture campaign in this document — the heaviest configuration
tested (both extended scripts attached, capture mode `ALL`, live for several
minutes) completed and produced 100% correct, deterministic output.
**RESOURCE GO**, no reducer rewritten.

## 6. Formal status

```
P6 MTF CORE                        CLOSED
P6 ORIGINAL SEMANTICS              UNCHANGED
P6→P5 TRANSPORT                    COMPLETE
P6→P5 REAL PINE<->PYTHON PARITY    VERIFIED
```

**Still not claimed**: anything about P5's own arithmetic, weights, bands, or
calibration. This closes the boundary P6 hands data across; P5's own closure
is a separate, later document.
