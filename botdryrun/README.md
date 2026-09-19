# botdryrun — paper / dry-run bot

**DRY-RUN ONLY.** This package simulates trading on historical candles. There
is no live broker, no network order API, no credential handling and no
live-order code path. `LiveBrokerDisabled` raises on construction, the config
has no `live_broker_enabled` field (setting one is refused), and
`tests/bot/test_safety_and_boundaries.py` asserts all of this.

**PRACTICE POLICY, NOT A VALIDATED STRATEGY.** The signal rules in
`policy.py` exist to exercise the plumbing. No profitability, edge or
production-readiness claim is made. Paper results are not evidence of
anything beyond "the bot did what its rules say".

## What it does

```
CSV candles -> market_data (validate stream) -> scanner_adapter (level_a_replay,
RC4 market-framework profile) -> events (P8 dedup) -> policy (practice)
-> trade intents (explanatory) -> broker (paper)
-> store (sqlite, one transaction per bar) -> journals
```

* The bot implements **no** scanner semantics. POI detection, freshness,
  the RC4 market framework, P5 scoring/permission and P8 events all come
  from `tests/parity_support/level_a_replay.iter_level_a_bars`
  (`rc3_freshness=True`, `WarmupFeedPolicy.AVAILABILITY`,
  `rc4_framework=True`), called only from `scanner_adapter.py`. Its daily
  P3/P5/P8 digests equal `run_daily_authority(..., rc4_framework=True)`'s
  digests for the same series (asserted in `tests/bot`).
* Scanner profile: `RC4` is the default (`scanner_profile` in the config,
  `--scanner-profile` on `replay`). `RC3` stays selectable: the same call
  with `rc4_framework=False`, whose digests equal the RC3 authority's.
* Signals originate only from consumed P8 `PERMISSION_ENTERED_ACTIONABLE`
  events; `PERMISSION_LOST_ACTIONABLE` / `POI_TERMINAL` cancel pending orders.
  The RC4 fields are carried and journaled, but the practice policy does not
  read them (nor scores, nor P5 permission bands).
* Every consumed `PERMISSION_ENTERED_ACTIONABLE` event also produces one
  **paper trade intent** (`trade_intent_journal.csv`): direction, POI zone
  and type, P5 permission and score, BTMM pre-trade reason, RC4 location
  (framework, range position, fib bucket, retracement, sweep, interaction
  episode) and the linked practice-policy signal (ACCEPTED or SKIPPED with a
  reason). An intent is a record, not an order; it places nothing.
* Fill model (see `broker.py`): orders are never evaluated on the bar that
  created them; limit fills at the limit (or the open if gapped through);
  stop before target when both are inside one bar; target never credited on a
  limit fill bar. Slippage and commission default to **0**.

## RC4 fields in the journals

`DecisionView` carries the optional RC4 `BtrcDecision` fields verbatim:
`framework, fib_bucket, retracement_pct, range_position, sweep_before_poi,
btmm_pretrade_reason, btmm_distraction, btmm_delay, btmm_wipeout,
btmm_true_failure, poi_dwell_bars, poi_touch_count, poi_zone_return_count,
interaction_episode`. `p5_decision_journal.csv` has one row per P5-evaluated
POI per bar with all of them. They are also inside the per-bar digest
(`BOT-DRYRUN-BAR-V2`), so a restart whose rebuild changed any of them fails
with `RebuildDigestMismatchError`. With the RC3 profile they hold the
scanner's defaults (empty / 0).

## Scanner pin

`botdryrun/scanner_pin.py` pins the scanner commit this bot integrates
(`PINNED_SCANNER_COMMIT = a15c199dc3d1b9436fa18f707aed3c51b95fa03d`, the
`rc4-market-framework` head) and a content fingerprint of its sources
(`PINNED_SOURCE_DIGEST`): every `*.py` of the imported `btmm_ai_scanner`
package plus the replay modules the adapter uses from `tests/parity_support`,
each hashed as its git blob id with CRLF normalized to LF. The fingerprint
is therefore independent of the checkout location, of worktrees and of
`core.autocrlf`, needs no git at runtime, and can be re-derived from
`git ls-tree -r <commit>` (a test does exactly that).

Every run (replay / resume / restart) fingerprints the scanner source the
process actually imports and compares it with the pin and with the pin
recorded when the session was created. On any difference it refuses to run
(`ScannerPinMismatchError`, CLI exit code **8**) and records the refused
attempt. `--allow-scanner-mismatch` overrides; the override is recorded per
run in `scanner_pin_journal.csv`, in `manifest.json` (`scanner_pin` block,
`override_ever_used: true`) and makes `health` report the session unhealthy.
Moving the bot to a new scanner commit means updating both constants
(re-derive the digest from `git ls-tree` as the test does).

## Restart recovery

Kernel objects are not serializable, so recovery is event-sourced: the store
keeps every processed host bar and every context candle (with the host bar it
was released with), plus per-bar and chained scanner digests. Every run
re-runs the scanner over the persisted inputs, requires each rebuilt digest
to match (else `RebuildDigestMismatchError`), restores processed event and
signal ids, orders, positions and ledger from the store, and continues. A
crash before a bar's COMMIT leaves no trace of that bar, so it is processed
exactly once on restart.

## CLI (run from the repo root, with the project virtualenv)

```
python -m botdryrun replay --state-dir artifacts/bot_dryrun_rc4/day1 \
    --trading-day 2026-08-10 --dataset-root <path>/artifacts/v1a_validation \
    --context-lookback-bars 40 [--max-bars 46] [--scanner-profile RC4|RC3]
python -m botdryrun resume  --state-dir artifacts/bot_dryrun_rc4/day1 [--max-bars N]
python -m botdryrun restart --state-dir artifacts/bot_dryrun_rc4/day1   # new process
python -m botdryrun status  --state-dir artifacts/bot_dryrun_rc4/day1
python -m botdryrun health  --state-dir artifacts/bot_dryrun_rc4/day1
python -m botdryrun export  --state-dir artifacts/bot_dryrun_rc4/day1
```

`--start/--end` (host bar OPEN instants, inclusive) select any period;
`--trading-day D --days N` selects whole FXCM trading days (22:00Z the day
before through 20:45Z). A window intersecting the sealed out-of-sample range
is refused. Journals are written to `<state-dir>/journals/` with a
`manifest.json` of sha256 digests (plus the scanner profile and the
`scanner_pin` block); `perf_bar_timing.csv`, `runs.csv` and
`scanner_pin_journal.csv` hold per-run operational data and are excluded
from the digests. `replay`/`resume`/`restart` accept
`--allow-scanner-mismatch` (see "Scanner pin").

Paper results of any run — including an RC4 replay — say only that the bot
did what its practice rules say on that data. They are not evidence of edge
or profitability, and none is claimed.

Known limitations: the scanner iterator needs the whole host window up front,
so this is a replay bot over a known window (not a streaming live feed);
restart cost grows with bars already processed because the kernel is rebuilt
by re-running it; exchange holidays are reported as `MISSING_BARS` incidents.
