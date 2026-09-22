from enum import StrEnum


class InternalSymbol(StrEnum):
    XAUUSD = "XAUUSD"
    EURUSD = "EURUSD"
    GBPUSD = "GBPUSD"


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
