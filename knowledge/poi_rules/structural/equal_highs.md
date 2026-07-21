# Equal Highs

## Alternative book name

NOT DEFINED IN BOOK.

## Family

Structural POI

## Direction

Bearish (buy-side liquidity rests above; used as a bearish liquidity-grab trigger leading toward a bearish POI).

## Source pages

"3. Equal highs - Equal lows" (paragraphs 603-617).

## Book definition

Price levels where the market has reached "the same high area" more than once; buy-side liquidity is assumed to rest above.

## Required market location

Two or more highs reached at a similar level.

## Formation conditions

Resolved under Equal Highs and Equal Lows Standard V1 — Provisional (Ambiguity 5): at least 2 confirmed swing points, using confirmed swing-high wick prices, all from the same timeframe (never combined across timeframes). **Swing-source dependency resolved under Meaningful Swing High and Swing Low Detection Standard V1 — Provisional (Ambiguity 10):** the qualifying swing points must be two distinct **CONFIRMED_MEANINGFUL_SWING_HIGH** events (an adjacent plateau counts as one event); **LOCAL_SWING_CANDIDATE** and **SUPERSEDED** records do not qualify; at least one opposite confirmed meaningful swing (a CONFIRMED_MEANINGFUL_SWING_LOW) must exist between two same-type Equal-High swing events. See knowledge/MEASUREMENT_STANDARDS.md, "Meaningful Swing High and Swing Low Detection Standard." Equal Highs Cluster Spread (highest qualifying swing-high wick price minus lowest qualifying swing-high wick price) must be <= Equality Tolerance, where Equality Tolerance = MAX(2 x minimum price ticks for the instrument, 0.10 x Reference ATR), and Reference ATR = median ATR(14) across all qualifying swing-touch candles (same symbol/timeframe, confirmed candles only) - **this Equality Tolerance/Reference ATR formula and the 0.05x/0.10x strength thresholds are unchanged by the swing-source update.** See knowledge/MEASUREMENT_STANDARDS.md, "Equal Highs and Equal Lows Tolerance and Drawing Standard" (provisional, pending calibration).

## Confirmation conditions

Resolved under Equal Highs and Equal Lows Standard V1 — Provisional: the pattern is **CONFIRMED** only when at least 2 qualifying swing points exist, all are from the same timeframe, the latest swing point has itself been confirmed, and the cluster spread remains within Equality Tolerance. Before the latest swing confirms, the pattern is only **FORMING**. The book's own recommendation still applies on top of this: treat Equal Highs as an entry TRIGGER leading to another POI, not a direct entry zone - wait for the liquidity grab (a sweep beyond the level) first, then look for confirmation at the main POI the sweep leads toward. SWEPT and BROKEN states are reserved for later but not defined now.

## Origin candle or level

The repeated confirmed swing-high wick points (at least 2, same timeframe).

## Upper boundary

Resolved under Equal Highs and Equal Lows Standard V1 — Provisional: Zone Top = highest qualifying swing-high wick price. An optional Reference Level (median of all qualifying swing-high wick prices) may also be drawn but must not replace the Zone Top/Zone Bottom boundaries.

## Lower boundary

Resolved under Equal Highs and Equal Lows Standard V1 — Provisional: Zone Bottom = lowest qualifying swing-high wick price (this now gives Equal Highs a real two-sided zone rather than "not applicable," since the standard defines both a Zone Top and Zone Bottom from the cluster's wick-price spread).

## Wick treatment

Resolved under Equal Highs and Equal Lows Standard V1 — Provisional: confirmed swing-high **wick** prices are explicitly used (not close prices) for both the equality comparison and the Zone Top/Zone Bottom boundaries.

## Body treatment

Not defined in the book.

## Candle-size requirement

Not applicable / not defined.

## Volume or momentum proxy

Not defined in the book.

## Trend requirement

Not defined beyond the general POI framework note.

## Market-structure requirement

Not defined beyond the general POI framework note.

## Liquidity requirement

Central to the concept (buy-side liquidity above). Liquidity expectation is now formalized under Equal Highs and Equal Lows Standard V1 — Provisional: liquidity is expected **above Zone Top**. No numeric sizing rule (how much liquidity) is defined - only the expected location.

## Timeframe requirement

More reliable on higher timeframes (stronger liquidity) - stated generally, no explicit ranking list like Order Block's.

## Strength classification

Resolved under Equal Highs and Equal Lows Standard V1 — Provisional: **STRONG** (Cluster Spread <= 0.05x Reference ATR), **STANDARD** (> 0.05x and <= 0.10x Reference ATR), **NOT EQUAL** (Cluster Spread > Equality Tolerance). The minimum-tick floor from the Equality Tolerance formula still applies throughout. No additional tiers are defined. Still provisional pending calibration.

## Freshness

`freshness_status = NOT_AUTOMATICALLY_EVALUATED` (resolved under `knowledge/poi_lifecycle/POI_FRESHNESS_AND_AGE_STANDARD.md`, `P0G-B006`) — see "Phase 0G Specialized Lifecycle Deferral" below. Not defined in the book.

## Partial mitigation

NOT DEFINED IN BOOK.

## Full mitigation

NOT DEFINED IN BOOK.

## Invalidation

Not defined in the book.

## Expiration

`expiration_status = NOT_AUTOMATICALLY_EVALUATED` (resolved under `knowledge/poi_lifecycle/POI_FRESHNESS_AND_AGE_STANDARD.md`, `P0G-B007`) — see "Phase 0G Specialized Lifecycle Deferral" below. Not defined in the book.

## Phase 0G Specialized Lifecycle Deferral

**Resolves `P0G-B004` (Equal High/Equal Low sweep lifecycle) — Option B approved: the specialized lifecycle is formally deferred outside Phase 0G.** See `knowledge/FINAL_PHASE_0G_KNOWLEDGE_GAP_AUDIT.md`, "Post-Audit Author Decisions — P0G-B002 through P0G-B007 and P0G-B013," for the full decision record.

- **Liquidity-reference role:** Equal Highs remains a confirmed liquidity-reference structure (buy-side liquidity expected above Zone Top), not a directional entry zone.
- **Generic bounded lifecycle prohibited:** the shared POI Boundary Breach, Reclaim, Repeated Tap, and Invalidation Standard (`knowledge/poi_lifecycle/POI_BOUNDARY_BREACH_RECLAIM_INVALIDATION.md`) is explicitly excluded from Equal Highs and must never be silently applied.
- **Automated specialized lifecycle deferred:** SWEPT, BROKEN, reclaim, and false-sweep detection remain undefined and are not implemented by this decision.
- **Manual expert label permitted:** a reviewed manual expert liquidity-event label may be used as liquidity-location evidence. Required source tag: `liquidity_event_source = MANUAL_EXPERT_LABEL`.
- **Permitted operations:** detect and confirm the Equal Highs structure (per the existing formation/confirmation rules above); record its zone (Zone Top/Zone Bottom, per the existing drawing boundaries above); record its strength (STRONG/STANDARD/NOT EQUAL, per the existing strength classification above); use it as reviewed liquidity-location evidence; use reviewed manual expert liquidity-event labels.
- **Prohibited operations:** automatically declaring SWEPT; automatically declaring BROKEN; automatically declaring reclaim or false sweep; automatically invalidating or reactivating the structure; applying the generic bounded lifecycle; treating the structure as a bullish or bearish entry zone; silently inferring an event from a wick or close; allowing the structure alone (without a reviewed manual expert label) to satisfy a BTMM liquidity-event gate.
- **Freshness and expiration:** `NOT_AUTOMATICALLY_EVALUATED` (see Freshness/Expiration sections above and `knowledge/poi_lifecycle/POI_FRESHNESS_AND_AGE_STANDARD.md`).
- **Existing geometry, tolerance, confirmation, and strength rules (Ambiguity 5) are unchanged** by this decision.
- **No entry role is created** by this decision.

Overall status remains **PARTIAL**. This POI is not marked APPROVED.

## Overlap with other POIs

Conceptually related to Swing High and to the Previous/Current Period High-Low family (all are 'prior highs' that attract liquidity) - the book does not give a formal hierarchy distinguishing them.

## Positive example

Yes (paragraphs 608-612). Not visually reviewed pixel-by-pixel.

## Negative example

No confirmed negative-example image caption.

## Machine-testable criteria

Partial - equality tolerance, Reference ATR, Cluster Spread, strength classification, Zone Top/Bottom drawing, the FORMING/CONFIRMED states, and now (Ambiguity 10, provisional) the swing-source detection itself (local pivot window, meaningful-reversal confirmation, plateau/SUPERSEDED handling) are all testable under the combined Equal Highs and Equal Lows Standard V1 — Provisional and Meaningful Swing High and Swing Low Detection Standard V1 — Provisional. Not testable end-to-end: STRONG_SWING's material-breach condition (undefined, affects swing strength but not Equal-Highs eligibility itself), SWEPT/BROKEN states, and all lifecycle behavior (freshness, mitigation, invalidation, expiration).

## Unresolved questions

The swing-source detection method is now resolved (provisionally) via Meaningful Swing High and Swing Low Detection Standard V1 (Ambiguity 10), but that standard's own material-breach sub-rule for STRONG_SWING remains undefined; SWEPT and BROKEN state definitions; reclaim, invalidation, expiration, freshness, and mitigation rules; both standards are explicitly provisional and require future calibration against expert-approved/rejected examples across XAUUSD/EURUSD/GBPUSD, relevant project timeframes, different volatility regimes, and different market sessions before they can be considered final.

## Author decision

Equality tolerance, Reference ATR, Cluster Spread formulas, strength classification, drawing boundaries, and FORMING/CONFIRMED states are approved (provisionally) - see Equal Highs and Equal Lows Standard V1 — Provisional. The swing-source dependency is now also approved (provisionally) - see Meaningful Swing High and Swing Low Detection Standard V1 — Provisional (Ambiguity 10). SWEPT/BROKEN states, the material-breach sub-rule, and freshness/mitigation/invalidation/expiration remain pending.

## Approval status

PARTIAL
