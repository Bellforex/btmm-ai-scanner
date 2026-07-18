# POI Coverage Matrix

Phase 0B coverage audit. One row per verified POI (36 total, covering all directional/
period variants named in the audit brief). Cross-referenced against the individual rule
files in `knowledge/poi_rules/` and the ambiguity register in
`AMBIGUITIES_REQUIRING_AUTHOR_DECISION.md`.

Legend: **Yes** = fully defined by the book; **Partial** = described qualitatively/narratively
but not quantified, or defined for only part of the concept; **No** = not defined in the book
at all; **N/A** = does not apply to this POI type.

Status values: NOT STARTED / PARTIAL / NEEDS AUTHOR DECISION / READY FOR SPECIFICATION / APPROVED.
No POI is marked APPROVED - no POI yet has all mandatory rules complete and author-approved
(every POI is missing at least Freshness, Partial mitigation, Full mitigation, and Expiration,
none of which the book defines for any POI).

---

| POI name | POI family | Direction | Book page/section | Definition available | Required location defined | Formation rule defined | Confirmation rule defined | Exact drawing boundary defined | Candle-size rule defined | Wick/body rule defined | Trend requirement defined | Market-structure requirement defined | Liquidity requirement defined | Timeframe rule defined | Strength classification defined | Freshness rule defined | Partial mitigation defined | Full mitigation defined | Invalidation defined | Expiration defined | Positive example available | Negative example available | Machine-testable now | Author clarification required | Status |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Buy Order Block | Volume-Based | Bullish | Ch.1 "Order blocks (OB)" P199-237; appendix P829-871 | Yes | Yes | Yes | Partial | Yes | Yes | Yes | Partial | No | No | Yes | Yes | No | No | No | No | No | Yes | No | Partial | Yes | PARTIAL |
| Sell Order Block | Volume-Based | Bearish | Ch.1 "Order blocks (OB)" P199-237; appendix P872-908 | Yes | Yes | Yes | Partial | Yes | Yes | Yes | Partial | No | No | Yes | Yes | No | No | No | No | No | Yes | No | Partial | Yes | PARTIAL |
| Buy Fair Value Gap | Volume-Based | Bullish | Ch.1 "Fair Value Gap" P238-287; appendix P688-704 | Yes | Yes | Yes | Partial | Yes | Partial | Partial | Partial | No | No | No | Yes | No | No | No | Partial | No | Yes | No | Partial | Yes | PARTIAL |
| Sell Fair Value Gap | Volume-Based | Bearish | Ch.1 "Fair Value Gap" P238-287; appendix P705-720 | Yes | Yes | Yes | Partial | Yes | Partial | Partial | Partial | No | No | No | Yes | No | No | No | Partial | No | Yes | No | Partial | Yes | PARTIAL |
| Buy-to-Sell Candle | Volume-Based | Bearish | P288-341; appendix P1057-1090, 1125-1159 | Yes | Yes | Yes | Partial | Yes | Yes | Yes | Yes | No | No | Yes | Yes | No | No | No | No | No | Yes | No | Partial | Yes | NEEDS AUTHOR DECISION |
| Sell-to-Buy Candle | Volume-Based | Bullish | P288-341; appendix P1091-1159 | Yes | Yes | Yes | Partial | Yes | Yes | Yes | Yes | No | No | Yes | Yes | No | No | No | No | No | Yes | No | Partial | Yes | NEEDS AUTHOR DECISION |
| Base Rally (Rally-Base-Rally) | Volume-Based | Bullish | P342-358; appendix P942-1049 | Yes | Yes | Yes | Yes | Yes | Yes | Yes | Yes | No | No | Yes | Yes | No | No | No | No | No | Yes | No | Partial | Yes | PARTIAL |
| Base Drop (Drop-Base-Drop) | Volume-Based | Bearish | P342-358; appendix P942-1049 | Yes | Yes | Yes | Yes | Yes | Yes | Yes | Yes | No | No | Yes | Yes | No | No | No | No | No | Yes | No | Partial | Yes | PARTIAL |
| Bullish Pressure Wick (Liquidity Wick) | Volume-Based | Bullish | P359-373 | Yes | Partial | Partial | Yes | No | N/A | No | No | No | Partial | Yes | No | No | No | No | No | No | Yes | No | No | Yes | NEEDS AUTHOR DECISION |
| Bearish Pressure Wick (Liquidity Wick) | Volume-Based | Bearish | P359-373 | Yes | Partial | Partial | Yes | No | N/A | No | No | No | Partial | Yes | No | No | No | No | No | No | Yes | No | No | Yes | NEEDS AUTHOR DECISION |
| Bullish Engulfing Candle | Price Action | Bullish | P413-474; appendix P731-764, 799-828 | Yes | Yes | Yes | Yes | No | Yes | Yes | Partial | Partial | Partial | Yes | Yes | No | No | No | No | No | Yes | No | Partial | Yes | PARTIAL |
| Bearish Engulfing Candle | Price Action | Bearish | P413-474; appendix P765-828 | Yes | Yes | Yes | Yes | No | Yes | Yes | Partial | Partial | Partial | Yes | Yes | No | No | No | No | No | Yes | No | Partial | Yes | PARTIAL |
| Hammer (a.k.a. Pin Bar) | Price Action | Bullish | P475-496 | Yes | Yes | Partial | Yes | No | N/A | No | No | No | No | No | Partial | No | No | No | No | No | Yes | No | No | Yes | NEEDS AUTHOR DECISION |
| Shooting Star | Price Action | Bearish | P475-496 | Yes | Yes | Partial | Yes | No | N/A | No | No | No | No | No | Partial | No | No | No | No | No | Yes | No | No | Yes | NEEDS AUTHOR DECISION |
| Morning Star | Price Action | Bullish | P497-523 | Yes | Yes | Partial | Yes | No | Yes | No | No | No | No | Yes | Partial | No | No | No | No | No | Yes | No | Partial | Yes | PARTIAL |
| Evening Star | Price Action | Bearish | P497-523 | Yes | Yes | Partial | Yes | No | Yes | No | No | No | No | Yes | Partial | No | No | No | No | No | Yes | No | Partial | Yes | PARTIAL |
| Bullish Trendline | Structural | Bullish | P576-589 | Yes | Partial | Partial | Partial | No | N/A | No | Yes | No | Partial | Yes | No | No | No | No | No | No | Yes | No | No | Yes | NEEDS AUTHOR DECISION |
| Bearish Trendline | Structural | Bearish | P576-589 | Yes | Partial | Partial | Partial | No | N/A | No | Yes | No | Partial | Yes | No | No | No | No | No | No | Yes | No | No | Yes | NEEDS AUTHOR DECISION |
| Support | Structural | Bullish | P590-602 | Yes | Yes | No | Partial | No | N/A | No | No | No | Partial | No | No | No | No | No | No | No | Yes | No | No | Yes | NEEDS AUTHOR DECISION |
| Resistance | Structural | Bearish | P590-602 | Yes | Yes | No | Partial | No | N/A | No | No | No | Partial | No | No | No | No | No | No | No | Yes | No | No | Yes | NEEDS AUTHOR DECISION |
| Equal Highs | Structural | Bearish | P603-617 | Yes | Yes | Yes | Partial | Yes | N/A | Yes | No | No | Yes | Partial | Yes | No | No | No | No | No | Yes | No | Partial | Yes | PARTIAL |
| Equal Lows | Structural | Bullish | P603-617 | Yes | Yes | Yes | Partial | Yes | N/A | Yes | No | No | Yes | Partial | Yes | No | No | No | No | No | Yes | No | Partial | Yes | PARTIAL |
| Swing High | Structural | Bearish | P618-626 | Yes | No | No | No | No | N/A | No | No | No | Yes | No | No | No | No | No | No | No | Yes | No | No | Yes | NEEDS AUTHOR DECISION |
| Swing Low | Structural | Bullish | P618-626 | Yes | No | No | No | No | N/A | No | No | No | Yes | No | No | No | No | No | No | No | Yes | No | No | Yes | NEEDS AUTHOR DECISION |
| Previous Day High | Structural | Bearish | Ch.1 "High and low of the following..." P627-687 | Yes | N/A | Yes | No | Yes | N/A | Yes | No | No | Yes | Yes | Partial | No | No | No | No | No | Yes | No | Partial | Yes | PARTIAL |
| Previous Day Low | Structural | Bullish | Ch.1 "High and low of the following..." P627-687 | Yes | N/A | Yes | No | Yes | N/A | Yes | No | No | Yes | Yes | Partial | No | No | No | No | No | Yes | No | Partial | Yes | PARTIAL |
| Previous Week High | Structural | Bearish | Ch.1 "High and low of the following..." P627-687 | Yes | N/A | Yes | No | Yes | N/A | Yes | No | No | Yes | Yes | Partial | No | No | No | No | No | Yes | No | Partial | Yes | PARTIAL |
| Previous Week Low | Structural | Bullish | Ch.1 "High and low of the following..." P627-687 | Yes | N/A | Yes | No | Yes | N/A | Yes | No | No | Yes | Yes | Partial | No | No | No | No | No | Yes | No | Partial | Yes | PARTIAL |
| Previous Month High | Structural | Bearish | Ch.1 "High and low of the following..." P627-687 | Yes | N/A | Yes | No | Yes | N/A | Yes | No | No | Yes | Yes | Partial | No | No | No | No | No | Yes | No | Partial | Yes | PARTIAL |
| Previous Month Low | Structural | Bullish | Ch.1 "High and low of the following..." P627-687 | Yes | N/A | Yes | No | Yes | N/A | Yes | No | No | Yes | Yes | Partial | No | No | No | No | No | Yes | No | Partial | Yes | PARTIAL |
| Current Day High (book: "High of the Day") | Structural | Bearish | Ch.1 "High and low of the following..." P627-687 | Yes | N/A | Yes | No | Yes | N/A | Yes | No | No | Yes | Yes | Partial | No | No | No | No | No | Yes | No | Partial | Yes | PARTIAL |
| Current Day Low (book: "Low of the Day") | Structural | Bullish | Ch.1 "High and low of the following..." P627-687 | Yes | N/A | Yes | No | Yes | N/A | Yes | No | No | Yes | Yes | Partial | No | No | No | No | No | Yes | No | Partial | Yes | PARTIAL |
| Current Week High (book: "High of the Week") | Structural | Bearish | Ch.1 "High and low of the following..." P627-687 | Yes | N/A | Yes | No | Yes | N/A | Yes | No | No | Yes | Yes | Partial | No | No | No | No | No | Yes | No | Partial | Yes | PARTIAL |
| Current Week Low (book: "Low of the Week") | Structural | Bullish | Ch.1 "High and low of the following..." P627-687 | Yes | N/A | Yes | No | Yes | N/A | Yes | No | No | Yes | Yes | Partial | No | No | No | No | No | Yes | No | Partial | Yes | PARTIAL |
| Current Month High (book: "High of the Month") | Structural | Bearish | Ch.1 "High and low of the following..." P627-687 | Yes | N/A | Yes | No | Yes | N/A | Yes | No | No | Yes | Yes | Partial | No | No | No | No | No | Yes | No | Partial | Yes | PARTIAL |
| Current Month Low (book: "Low of the Month") | Structural | Bullish | Ch.1 "High and low of the following..." P627-687 | Yes | N/A | Yes | No | Yes | N/A | Yes | No | No | Yes | Yes | Partial | No | No | No | No | No | Yes | No | Partial | Yes | PARTIAL |

## Summary Counts

- Total POIs verified: **36**
- PARTIAL: **24** (Base Rally and Base Drop moved from NEEDS AUTHOR DECISION to PARTIAL after Base Formation Standard V1 — Provisional resolved Ambiguity 4; Equal Highs and Equal Lows moved from NEEDS AUTHOR DECISION to PARTIAL after Equal Highs and Equal Lows Standard V1 — Provisional resolved Ambiguity 5)
- NEEDS AUTHOR DECISION: **12**

Machine-testable-now breakdown: Partial=26, No=10

Note: Base Rally and Base Drop's "Formation rule defined" and "Confirmation rule defined" columns were updated to Yes following the Phase 0D approval of Base Formation Standard V1 — Provisional (base candle count, compactness, and departure confirmation are now defined, subject to future calibration). Neither POI is marked APPROVED — freshness, mitigation, invalidation, and expiration remain undefined for both, and the standard itself is explicitly provisional.

Note: Equal Highs and Equal Lows' "Formation rule defined," "Exact drawing boundary defined," "Wick/body rule defined," and "Strength classification defined" columns were updated to Yes, and "Confirmation rule defined" and "Machine-testable now" to Partial, following approval of Equal Highs and Equal Lows Standard V1 — Provisional (minimum qualifying-point count, same-timeframe rule, equality tolerance, drawing boundaries, and strength classification are now defined, all provisional pending calibration). Neither POI is marked APPROVED — the automatic swing-detection method (Ambiguity 10), SWEPT/BROKEN states, and freshness/mitigation/invalidation/expiration all remain unresolved for both.
