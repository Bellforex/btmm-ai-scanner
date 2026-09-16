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
RC3 contract) -> events (P8 dedup) -> policy (practice) -> broker (paper)
-> store (sqlite, one transaction per bar) -> journals
```

* The bot implements **no** scanner semantics. POI detection, freshness,
  P5 scoring/permission and P8 events all come from
  `tests/parity_support/level_a_replay.iter_level_a_bars`
  (`rc3_freshness=True`, `WarmupFeedPolicy.AVAILABILITY`), called only from
  `scanner_adapter.py`. Its daily P3/P5/P8 digests equal the RC3 daily
  authority's digests for the same series.
* Signals originate only from consumed P8 `PERMISSION_ENTERED_ACTIONABLE`
  events; `PERMISSION_LOST_ACTIONABLE` / `POI_TERMINAL` cancel pending orders.
* Fill model (see `broker.py`): orders are never evaluated on the bar that
  created them; limit fills at the limit (or the open if gapped through);
  stop before target when both are inside one bar; target never credited on a
  limit fill bar. Slippage and commission default to **0**.

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
python -m botdryrun replay --state-dir artifacts/bot_dryrun/day1 \
    --trading-day 2026-08-10 --dataset-root <path>/artifacts/v1a_validation \
    --context-lookback-bars 40 [--max-bars 46]
python -m botdryrun resume  --state-dir artifacts/bot_dryrun/day1 [--max-bars N]
python -m botdryrun restart --state-dir artifacts/bot_dryrun/day1   # new process
python -m botdryrun status  --state-dir artifacts/bot_dryrun/day1
python -m botdryrun health  --state-dir artifacts/bot_dryrun/day1
python -m botdryrun export  --state-dir artifacts/bot_dryrun/day1
```

`--start/--end` (host bar OPEN instants, inclusive) select any period;
`--trading-day D --days N` selects whole FXCM trading days (22:00Z the day
before through 20:45Z). A window intersecting the sealed out-of-sample range
is refused. Journals are written to `<state-dir>/journals/` with a
`manifest.json` of sha256 digests; `perf_bar_timing.csv` and `runs.csv` hold
wall-clock data and are excluded from the digests.

Known limitations: the scanner iterator needs the whole host window up front,
so this is a replay bot over a known window (not a streaming live feed);
restart cost grows with bars already processed because the kernel is rebuilt
by re-running it; exchange holidays are reported as `MISSING_BARS` incidents.
