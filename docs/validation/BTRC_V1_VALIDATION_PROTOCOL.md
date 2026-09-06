# BTRC V1 — Validation Protocol — V1-A: Frozen RC1 Signal-Outcome Characterization

**This document is committed BEFORE any aggregate outcome is examined.**
Its purpose is to make that fact independently verifiable: the git
history timestamp of this commit is the proof that every definition
below was fixed before any characterization result existed. Nothing in
this document may be edited after implementation begins in a way that
would make a result look better — if a genuine error is found in a
definition, it is corrected in a NEW commit, with the reason stated, and
the original committed protocol is not silently rewritten.

## 0. Scope discipline

RC1 (`tradingview/btmm_poi_btrc_scanner_rc1.pine`, SHA-256
`143c0f8817c78bf45e6842e16112cedf67ca36dc694c288808b7748096664c54`) is
the frozen subject under test. It is not modified anywhere in V1-A. No
P1–P10 semantics, weights, bands, thresholds, or definitions are changed.

**V1-A produces NO trade-profitability metric of any kind.** RC1 defines
no entry price, no stop-loss, no take-profit, no exit rule, no position
size. Win rate, expectancy, R-multiple, profit factor, drawdown, and
equity-curve metrics are explicitly OUT OF SCOPE for this document and
for the harness it specifies — see §12.

## 1. What is being measured

For every one of RC1's five closed V1 informational events
(`POI_ACTIVATED`, `BTMM_VALIDATED`, `PERMISSION_ENTERED_ACTIONABLE`,
`PERMISSION_LOST_ACTIONABLE`, `POI_TERMINAL`), and separately for every
POI's own lifecycle, this protocol measures **what price actually did
afterward** — direction, magnitude, speed, and whether the POI's own
zone was subsequently touched or invalidated — using a neutral reference
price that is explicitly NOT a trade entry (§5).

## 2. Reuse architecture — nothing here is new detection/scoring logic

Every computation in this protocol delegates to already-closed,
already-tested code. This section is the frozen implementation contract;
Phase 47 (harness implementation) must follow it exactly.

- **P1–P4 (measurements, structure, POI, BTMM)**:
  `btmm_ai_scanner.scanner.replay.run_scanner_replay`, called directly
  (NOT via `historical_backtest.execute_scanner_backtest`, whose
  `_UNSAFE_RETENTION_GROUP_CAP = 250` availability-group ceiling is a
  historical-backtest business rule, not a `scanner.replay` constraint,
  and would reject this dataset's ~2900+ groups), with
  `SnapshotRetentionPolicy.ALL` to get one full `ScannerAnalysis` per
  confirmed availability group (bar).
- **P5 (BTRC confluence)**: `btmm_ai_scanner.btrc.assess_confluence`
  (`btrc/t5_engine.py:69-76`), called once per eligible POI per bar,
  given that bar's `ScannerAnalysis`, the target `PoiObservation`,
  `candles_by_timeframe` (five timeframes, §3), and
  `evaluation_time_utc`. This single call internally runs T1–T5; no
  manual per-engine wiring.
- **Active-POI eligibility loop**: modeled on
  `tests/parity_support/p5_active_poi_loop_model.run_active_poi_loop` —
  the same frozen contract every prior Pine phase (P5/P7/P7-Z/P9) reused
  rather than re-derived.
- **P8 (event derivation)**: `tests/parity_support/p8_alert_oracle
  .AlertEngine`, fed one `PoiSnapshot` per eligible POI per bar. Field
  mapping (verified against source, not assumed): `poi_bullish` from
  `PoiObservation.direction`; `terminal` from
  `current_poi_states[...].poi_lifecycle_status ==
  PoiLifecycleStatus.GENUINE_INVALIDATION_CONFIRMED`; `tier`/`permission`
  /`lifecycle` integer codes from the existing
  `tests/parity_support/p5_wire_normalized_replay.py` code tables
  (`POI_TIER_BY_CODE`, `PERMISSION_CODE`, `LIFECYCLE_CODE`) — reused, not
  re-derived — applied to the `BtrcDecision` `assess_confluence` returns.
- **Reaction/displacement**: `domain.displacement
  .detect_displacement_observations` (`domain/displacement.py:66-105`) —
  the existing closed "reaction" primitive (NORMAL/FAST/VERY_FAST
  classification by `range_speed_ratio`, plus direction). V1-A does not
  define a new "successful reaction" concept; where a reaction label is
  reported, it is this function's own output.
- **ATR**: `measurements.atr.compute_atr_series` (Wilder's method,
  period 14, `measurements/atr.py:19-44`) computed on the M15 (host)
  candle series. ATR-normalized figures divide by this series' value at
  the event's own bar; bars during ATR warm-up (`None`) are excluded
  from ATR-normalized tables and counted in the exclusion report (§13).

## 3. Timeframe inputs

Five of the six `_AUTHORITY_TIMEFRAMES` are supplied as genuine FXCM
history (see `BTRC_V1_V1A_DATA_PROVENANCE_MANIFEST.md` for exact
files/hashes): **W1, D1, H4, H1, M15**. **M5 is omitted** — its real
history does not reach back into the characterization window (plateaus
at 2026-08-09, after the window ends). This is not a silent
simplification: `trend_engine.assess_trend`/`regime_engine.assess_regime`
(`trend_engine.py:295-297`, `regime_engine.py:114-136`) skip any
timeframe absent from the supplied `ScannerAnalysis` without error, and
M15/M5/H1 are not in the trend "authority" set (`{W1, D1, H4}`,
`trend_engine.py:345`) used for trend confirmation, so omitting M5
degrades the confluence context only marginally, not materially.

M15 is the host/observation timeframe: POI registration, event
timestamps, and the primary reported bar-count horizons (§6) are all in
M15 bars.

## 4. Non-repaint / no-lookahead contract

A bar's data is available starting at its `availability_time_utc`
(`contracts/normalized_candle.py:108-109` structurally requires
`availability_time_utc > event_time_utc`; for intraday timeframes
`availability_time_utc = event_time_utc + <timeframe duration>` —
i.e., **the bar's close**, per `historical_backtest/csv_parser.py:
148-149`). Every event and every forward observation in V1-A gates on
this field, exactly as `scanner.replay` itself does internally
(`replay.py:879-891`). No field is ever read before its own
`availability_time_utc`. This matches the non-repaint contract already
documented since P1 ("every confirmed analytical record is produced
ONLY on a CONFIRMED/CLOSED bar... availability = close of the bar").

## 5. Event reference price — NOT an entry price

`EVENT_CLOSE_REFERENCE` := the `close` of the confirmed M15 bar on which
the event's `availability_time_utc` falls (i.e., that bar's own close
price — the same bar, since availability = close-of-bar for M15). Every
table and every field in every report carries this exact name, never
"entry."

## 6. Forward horizons (frozen, bar-count based)

`[1, 2, 3, 4, 8, 12, 24, 48]` M15 bars, measured from the event's own
bar (horizon 0). A horizon of `N` bars means "through and including the
`N`-th confirmed bar after the event bar." Horizons are never changed
after any result is examined. If a horizon extends past the end of the
DEV or OOS set, that event/horizon cell is marked `censored` (§13), never
padded or truncated silently.

## 7. Directional return

For horizon `N`: `directional_return = sign(direction) * (close[N] -
EVENT_CLOSE_REFERENCE)`, where `sign(direction) = +1` for a bullish
event, `-1` for bearish. Reported in raw price units, and separately as
a percentage of `EVENT_CLOSE_REFERENCE`. Never called "profit."

## 8. MFE (Maximum Favorable Excursion)

Over bars `1..N` of a horizon: `MFE = max(sign(direction) * (high[i] -
EVENT_CLOSE_REFERENCE))` for a bullish event (using `low[i]` inverted
for bearish — i.e., the best price movement IN the event's favor,
using each bar's favorable-side extreme). Reported absolute, as % of
`EVENT_CLOSE_REFERENCE`, and ATR-normalized (÷ ATR at the event bar).
Never called "realized profit."

## 9. MAE (Maximum Adverse Excursion)

Same construction as MFE, using the unfavorable-side extreme
(`low[i]` for bullish, `high[i]` for bearish). Never interpreted as
stop-loss performance.

## 10. POI geometry outcomes

Independent of the event-close excursion tables, per POI (not per
event): touch (`low[i] <= zone_top AND high[i] >= zone_bottom` for any
bar after `avail_time_ms`), first-touch bar offset, maximum penetration
depth (in price and ATR units) into the zone, whether the zone's far
boundary was crossed, whether genuine P3 invalidation occurred
(`poi_lifecycle_status == GENUINE_INVALIDATION_CONFIRMED` — reusing the
existing lifecycle definition, never a new invalidation rule), and bars
to invalidation. A POI never touched or never invalidated within the
available data is `censored`, not defaulted to a maximum.

## 11. Reaction characterization

Using `domain.displacement.detect_displacement_observations` on the M15
series: for each event, whether a `FAST`/`VERY_FAST` displacement
observation (per that function's own classification) occurs within the
forward horizon grid, in which direction, and how many bars after the
event. This is reported as "reaction occurrence/magnitude/delay" per
Phase 11 of the brief, using the closed primitive's own labels — no new
"successful setup" definition is introduced.

## 12. Prohibited metrics (hard rule, enforced in code review of the harness)

V1-A MUST NOT compute, and no V1-A report may contain: win rate, profit
factor, expectancy (in R or in currency), R-multiple, average R, maximum
drawdown, consecutive-loss count, trade frequency framed as position
turnover, balance/equity curve, Sharpe ratio, or any percentage framed
as "return on risk." These all require a trade-simulation contract this
document deliberately does not define — that is V1-B, a separate,
future, separately-authorized document.

## 13. Exclusion policy

Never silently drop a record. Every excluded observation is counted and
reasoned in a dedicated exclusion table with categories: `horizon
_censored` (horizon extends past DEV/OOS boundary), `atr_warmup`
(ATR undefined at the event bar), `incomplete_terminal_lifecycle` (POI
still non-terminal at the end of the available window), `missing
_context` (a needed higher-timeframe bar was absent for that instant —
should be rare given the five-TF coverage in §3, but tracked, not
assumed zero).

## 14. Statistical independence caveat

Event observations are NOT independent: many originate from overlapping
POIs active on the same market move. Every report adds descriptive
clustering identifiers (calendar day, ISO week, POI identity, event bar)
so a later, more careful statistical treatment is possible. V1-A itself
computes no confidence interval that assumes independence.

## 15. Dataset split

See `BTRC_V1_V1A_DATA_PROVENANCE_MANIFEST.md` for the exact, hash-proven
boundaries: DEV = 2903 M15 bars (2026-05-31T22:00 → 2026-07-14T17:00
UTC), OOS = 1244 M15 bars (2026-07-14T17:15 → 2026-08-03T06:45 UTC),
both chronologically prior to and disjoint from every already-used
P2–P9 development/parity capture. **The OOS set remains locked
(unopened) through the end of V1-A characterization** — only DEV-set
results are reported in the V1-A characterization report (§16). OOS is
reserved for a later, separately-scoped out-of-sample validation pass
(the brief's own V3), not part of V1-A's deliverable.

The already-used window (2026-08-03 onward, all prior P2–P9 captures) is
usable ONLY for harness pipeline-sanity checks against already-verified
evidence (brief Phase 44) — never for a V1-A characterization conclusion.

## 16. Segmentation (predeclared; no post-hoc segment invented for a headline conclusion)

Event type; POI type; POI origin timeframe (distinct from M15 host
timeframe); direction; BTRC permission; BTRC score band (frozen bands:
`<45`, `45–64`, `>=65` — unchanged from RC1); BTMM valid/not valid; trend
alignment (aligned vs. countertrend, from RC1's own closed state); regime;
session; volatility state — all taken directly from the `ScannerAnalysis`
/`BtrcDecision` fields already computed by the reused engines, never
recomputed or reclassified by this harness. Any segment not in this list
that is later explored is labeled `exploratory` in its own table, never
merged into the primary segmentation tables.

## 17. Determinism and integrity requirements for the harness (Phase 47–49)

- Running the full V1-A pipeline twice over the same input must produce
  byte-identical output records and identical digests.
- A deliberate lookahead-injection mutation (event state built from data
  after its own `availability_time_utc`) must fail a dedicated test.
- Deliberate event-timing mutations (one-bar-early/late, wrong
  confirmed-bar reference) must be caught by dedicated tests.
- Deliberate direction mutations (bull/bear sign inversion, MFE/MAE
  swapped) must be caught by dedicated tests.
- Deliberate horizon mutations (off-by-one, event bar included when it
  should not be, partial horizon misreported as complete) must be caught
  by dedicated tests.
- Randomized synthetic-OHLC oracle tests, where the expected MFE/MAE/
  directional return is mathematically known in advance, must match
  exactly.

## 18. Report contents (V1-A characterization report, DEV set only)

Event/POI counts; MFE/MAE distributions (mean, median, p25, p75, p90,
n) per segment; fixed-horizon directional returns per segment; reaction
occurrence/magnitude/delay; ATR-normalized threshold reach rates (grid:
0.25/0.50/1.00/1.50/2.00/3.00 ATR, favorable and adverse tracked
separately) with time-to-threshold (or `censored`); path ordering
(favorable-first vs. adverse-first vs. neither, per paired threshold);
zone-touch/invalidation rates and timing; event-frequency tables
(events/day, events/week, POIs/day, simultaneous active POIs);
permission-churn statistics; the exclusion table (§13); and the
segmentation tables (§16). No metric from §12 appears anywhere in this
report.

Every conclusion is phrased descriptively: *"Historically, events with
property X exhibited Y distribution over the DEV set."* Never
*"this setup is profitable"* or any causal claim.
