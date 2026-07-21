# Previous Day Low

## Alternative book name

NOT DEFINED IN BOOK.

## Family

Structural POI

## Direction

Bullish (liquidity below)

## Source pages

"4. High and low of the following: Previous Day High, Previous Day Low, Previous Week High, Previous Week Low, Previous Month High, Previous Month Low, High of the Day, Low of the Day, High of the Week, Low of the Week, High of the Month, Low of the Month" (paragraphs 627-687).

## Book definition

The lowest price reached during the previous trading day; a support/breakdown/liquidity level.

## Required market location

Not applicable - this is a calendar-derived level, not a chart-pattern location.

## Formation conditions

The level IS simply the highest/lowest traded price within the defined calendar window.

## Confirmation conditions

Not numerically defined - the book describes two possible outcomes on approach (liquidity sweep-then-reverse, or break-and-continue) but gives no rule for predicting which will occur; explicitly left contextual ('depending on market structure and trend').

## Origin candle or level

The single most extreme (highest or lowest) candle within that calendar window.

## Upper boundary

Not applicable (see Lower boundary).

## Lower boundary

The exact low price of the calendar window (a level, not a zone).

## Wick treatment

The extreme wick of the period defines the level - highs/lows are, by definition, wick-inclusive prices.

## Body treatment

Not applicable.

## Candle-size requirement

Not applicable.

## Volume or momentum proxy

Not applicable.

## Trend requirement

Not defined as a precondition for the level's existence; relevant only to interpreting sweep-vs-break behavior.

## Market-structure requirement

Not defined as a precondition; relevant only to interpreting sweep-vs-break behavior.

## Liquidity requirement

Central to the concept - liquidity (stop-losses, breakout orders, take-profits) is assumed to rest beyond the level.

## Timeframe requirement

Explicit ranking given in the book's "Key Lesson": month > week > day (higher calendar period = stronger, more liquidity).

## Strength classification

Ranked only by calendar period (month > week > day); no further standard/strong split.

## Freshness

NOT DEFINED IN BOOK.

## Partial mitigation

NOT DEFINED IN BOOK.

## Full mitigation

NOT DEFINED IN BOOK.

## Invalidation

Not defined in the book.

## Expiration

NOT DEFINED IN BOOK.

## Phase 0G Rejection-Criterion Applicability

**Resolves `P0G-B013A` (rejection-criterion applicability clarification, Author-Approved) — `rejection_criterion_status = NOT_APPLICABLE` for this POI.** See `knowledge/FINAL_PHASE_0G_KNOWLEDGE_GAP_AUDIT.md`, "Post-Decision Clarifications — P0G-B006 Interaction Timing and P0G-B013A Rejection Applicability."

- This structure is a deterministic calendar-period extremum, not a candidate candlestick or pattern formation that either passes or fails a confirmation threshold.
- Every valid completed or active period necessarily has a high and a low — there is no candidate to reject.
- The absence of a candidate-rejection rule is intentional and not a missing trading rule.
- Existing period validity requirements still apply. Invalid timestamps, wrong period assignment, missing data, or malformed source data are data-quality failures, not trading-pattern rejection criteria, and are out of scope for this clarification.
- Existing boundary definitions (above) remain unchanged.
- Existing confirmation/availability wording (above) remains unchanged.
- Existing rollover uncertainty remains unresolved where already documented (see Unresolved questions below) — this clarification does not resolve rollover or expiration timing.
- Existing period-identity rules remain unchanged.
- No lifecycle, interaction, entry, or risk rule is created by this clarification.

Overall status remains **PARTIAL**.

## Overlap with other POIs

One of twelve variants of the same underlying 'period extreme' family; also conceptually overlaps with Swing Highs/Lows and Equal Highs/Lows (all are prior-extreme liquidity levels).

## Positive example

Yes - one consolidated chart image for this whole section (paragraph 686). Not visually reviewed pixel-by-pixel.

## Negative example

No confirmed negative-example image caption.

## Machine-testable criteria

Partial - the level itself (the price extreme) is fully mechanically testable now (a pure data query over a calendar window); the sweep-vs-break behavioral prediction is not testable (no rule given; the book treats this as contextual judgment, not a formula).

## Unresolved questions

Sweep-vs-break prediction logic (the book leaves this to context, not a numeric ambiguity so much as an acknowledged interpretive gap); rollover/expiration timing for when a 'current' period level becomes a 'previous' period level is never stated.

## Author decision

Pending only for the sweep-vs-break interpretation and the rollover/expiration timing; the level-detection formula itself needs no author decision.

## Approval status

PARTIAL
