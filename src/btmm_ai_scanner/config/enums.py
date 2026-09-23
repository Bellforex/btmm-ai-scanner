from enum import StrEnum


class InternalSymbol(StrEnum):
    """The scanner's own symbol identity — deliberately provider-agnostic
    (see ``service/candles.py``'s own docstring: a caller resolves whatever
    a real vendor calls an instrument into one of these values before ever
    calling this engine).

    Originally scoped to three forex/metals pairs with no recorded
    rationale beyond "that's what every config default/tick-table/FXCM-
    registry literal happened to enumerate" (Bell Academy Hub Phase 2C's
    own audit of this file found no prior docstring or comment explaining
    the scope). That audit also confirmed the BTMM/POI/BTRC analytical
    core itself carries ZERO currency-pair-specific branching anywhere —
    `symbol` is threaded through purely as an opaque identity/provenance
    tag (equality filters, content-hashing, record-keeping) — so adding a
    new member here is safe for the analytical core by construction.

    `BTCUSD`/`AAPL` were added as the first real cross-asset-class test of
    that claim (Bell Academy Hub Phase 2C's engine-generalization test
    matrix — see `tests/unit/test_service_multi_asset_class.py`), not
    because a real crypto/stock market-data provider now exists (none
    does — see docs/BTMM_SCANNER_WEB_INTEGRATION.md in the Bell Academy
    Hub repo). Two real, NOT-yet-addressed gaps remain outside the live
    HTTP scan path used by that test:

    - `historical_backtest/data_quality.py`'s `is_likely_market_closure()`
      applies a blanket Friday-Sunday "forex weekend" heuristic
      regardless of symbol — correct for XAUUSD/EURUSD/GBPUSD, wrong for
      a 24/7 crypto symbol (real weekend gaps would be misclassified as
      closures) and incomplete for a stock (misses weekday-evening/
      holiday closures). Not reachable from `service/app.py`'s live scan
      path (that path never runs gap/data-quality classification), so
      this does not affect a real-time scan — only historical-backtest
      CLI data-quality reporting, which has no crypto/stock dataset
      support today regardless.
    - Genuine session-aware timeframe aggregation (e.g. building an H9
      candle from a stock's actual regular-session minutes rather than a
      blind 9-hour wall-clock bucket) has not been designed for any
      asset class beyond forex's already-24x5-ish treatment. Nothing in
      this engine currently performs that aggregation at all (Bell
      Academy Hub's own web-integration layer sends already-closed bars
      per timeframe directly), so this is a forward-looking note, not a
      regression.

    Note on `enabled_symbols`/`supported_symbols` config defaults:
    `scanner/configuration.py`, `poi/configuration.py`, and
    `btmm/configuration.py` each default this to the ORIGINAL three-member
    set on purpose — several existing tests assert those exact literal
    default values as "approved standards" (a first attempt at widening all
    three defaults to `frozenset(InternalSymbol)` broke three such tests).
    `service/app.py`'s own `_build_scanner_configuration()` is the ONLY
    place that explicitly widens acceptance to every `InternalSymbol`
    member for the live HTTP scan path — any other caller (e.g. a future
    historical-backtest run) must pass its own explicit `enabled_symbols`
    to accept BTCUSD/AAPL, exactly as it would for any new symbol.
    """

    XAUUSD = "XAUUSD"
    EURUSD = "EURUSD"
    GBPUSD = "GBPUSD"
    BTCUSD = "BTCUSD"
    AAPL = "AAPL"


class Timeframe(StrEnum):
    """Existing members (M1, M5, M15, H1, H3, H4, D1, W1) are unchanged — their
    string values and StrEnum identity are load-bearing for every existing
    scanner/BTMM/BTRC/historical_backtest test and fixture.

    H2, H6, H9, H12 and MN1 are NEW identities added for the BellForex web
    top-down correlation product (see btmm_ai_scanner.correlation and
    docs/WEB_TOP_DOWN_CORRELATION.md). They are valid Timeframe values the
    caller may supply candles for through the existing scan_market() contract
    — the analytical core does NOT resample or invent candle boundaries for
    them. A caller (the eventual web integration layer) must supply already-
    normalized candles whose boundaries match its own provider/session
    semantics. See docs/WEB_TOP_DOWN_CORRELATION.md "OHLC requirement" for the
    full rationale.
    """

    M1 = "M1"
    M5 = "M5"
    M15 = "M15"
    H1 = "H1"
    H2 = "H2"
    H3 = "H3"
    H4 = "H4"
    H6 = "H6"
    H9 = "H9"
    H12 = "H12"
    D1 = "D1"
    W1 = "W1"
    MN1 = "MN1"
