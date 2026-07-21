from enum import StrEnum


class InternalSymbol(StrEnum):
    XAUUSD = "XAUUSD"
    EURUSD = "EURUSD"
    GBPUSD = "GBPUSD"


class Timeframe(StrEnum):
    M1 = "M1"
    M5 = "M5"
    M15 = "M15"
    H1 = "H1"
    H3 = "H3"
    H4 = "H4"
    D1 = "D1"
    W1 = "W1"
