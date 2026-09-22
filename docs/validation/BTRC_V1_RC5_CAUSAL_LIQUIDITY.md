# BTRC-V1 RC5 — Causal liquidity: why final-state reconstruction is not authority

Status: **PHASE 18 CLOSED.** Canonical causal replay equals independent online
execution, exactly, on all five hosts.

This note exists to stop a future reader "simplifying" the sweep producer back
into either of two designs that were tried and proven wrong.

## Three generations

**GEN 1 — final-state reconstruction.** Build liquidity levels from the FINAL
swing / cluster / trendline collections, then sweep them. **Transient history
is erased.** A level that existed, qualified and was genuinely swept vanishes
because the final collections no longer contain it.

> Evidence: M45 equal-level cluster `4a0ffb5e` appeared at prefix 462, was
> swept at bar 487, and is absent from the final cluster set in both batch and
> incremental runs. Raw framework sweeps: 102 batch vs 123 incremental. H3: 51
> vs 57. Incremental is always a strict SUPERSET, never missing.

**GEN 2 — accumulate every prefix, qualify and deduplicate at the end.** Fixes
the erasure and **invents history instead**, three separate ways:

* a sweep qualified by a structural role the swing earned LATER — H3 fell from
  11 structural-swing events to 3 once this was fixed; eight were hindsight;
* a POI far edge judged by FINAL lifecycle state, so a POI invalidated at bar
  400 counted as dead at bar 100 and its real sweeps there disappeared;
* deduplication over the whole series, letting a link that appeared later merge
  historical events or move a primary owner.

**GEN 3 — per bar, but liveness read from accumulated records.** Rolling
references never die.

> Evidence: previous-day / previous-week levels are replaced daily. Only two
> are live at any prefix on H3 while **88 distinct ones exist** across the
> walk. Resolving liveness through the accumulated map left yesterday's
> previous-day high sweepable forever — 13 stale events on H3, each also
> stealing dedup ownership from the structural swing that really owned the
> level.

**GEN 4 — accepted.** Per bar, liveness from the CURRENT prefix, accumulated
records for RESOLUTION ONLY.

## The rule

> **Historical record preservation is not current active level registration.**
> Preserve history. Do not resurrect liquidity.

Accumulated records exist so a transient reference stays *resolvable* after it
disappears. They must never answer "is this reference active now?".

## Phase 18 closure matrix

Canonical causal replay vs an independently bookkept online engine — raw sweeps
tracked by IDENTITY rather than an index watermark, POI live-set rebuilt from
the current prefix each bar, events emitted per bar.

| host | | bars | canonical | online | missing | extra | field | order | exact |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| M5 | 5m | 2000 | 280 | 280 | 0 | 0 | 0 | yes | **yes** |
| M15 | 15m | 2000 | 272 | 272 | 0 | 0 | 0 | yes | **yes** |
| H3 | 180m | 300 | 57 | 57 | 0 | 0 | 0 | yes | **yes** |
| H4 | 240m | 2000 | 442 | 442 | 0 | 0 | 0 | yes | **yes** |
| M45 | **45m** | 529 | 68 | 68 | 0 | 0 | 0 | yes | **yes** |

1,119 events reproduced event for event, including ordering and corroboration.
M45 reports its semantic host as 45 minutes throughout, never the M15 carrier
enum it is driven on.

## What RC4 keeps

RC4 is untouched. The old final-state route still exists and still serves RC4;
RC5 simply stops treating it as semantic authority. `framework/engine.py` gains
only additive surface — a `LiquidityLevel` alias, an `advance_levels` seam over
the same `_sweep_step` RC4 uses, and one defaulted `rc5_qualified_sweeps`
field. The 37 RC4 framework tests pass unchanged.

## Cost

The canonical producer walks the kernel one candle at a time: ~64 minutes for a
2000-bar host, versus seconds for the lossy route. RC5 batch already pays that
for provenance. Correctness of causal history is not negotiable against speed,
and any future optimisation must preserve exact causal event output rather than
returning to final-state semantics.
