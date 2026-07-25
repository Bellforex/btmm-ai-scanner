from collections.abc import Mapping
from types import MappingProxyType

from btmm_ai_scanner.config.enums import InternalSymbol, Timeframe

FXCM_PROVIDER = "FXCM"

_FXCM_SYMBOL_REGISTRY: Mapping[str, InternalSymbol] = MappingProxyType(
    {
        "XAUUSD": InternalSymbol.XAUUSD,
        "EURUSD": InternalSymbol.EURUSD,
        "GBPUSD": InternalSymbol.GBPUSD,
    }
)

_FXCM_TIMEFRAME_REGISTRY: Mapping[str, Timeframe] = MappingProxyType(
    {
        "M1": Timeframe.M1,
        "M5": Timeframe.M5,
        "M15": Timeframe.M15,
        "H1": Timeframe.H1,
        "H3": Timeframe.H3,
        "H4": Timeframe.H4,
        "D1": Timeframe.D1,
        "W1": Timeframe.W1,
    }
)


class UnsupportedProviderError(ValueError):
    pass


class UnsupportedProviderSymbolError(ValueError):
    pass


class UnsupportedProviderTimeframeError(ValueError):
    pass


def resolve_internal_symbol(provider: str, provider_symbol: str) -> InternalSymbol:
    if provider != FXCM_PROVIDER:
        raise UnsupportedProviderError(f"Unsupported provider: {provider!r}.")
    try:
        return _FXCM_SYMBOL_REGISTRY[provider_symbol]
    except KeyError as exc:
        raise UnsupportedProviderSymbolError(
            f"Unsupported provider symbol: {provider_symbol!r}."
        ) from exc


def resolve_timeframe(provider: str, provider_timeframe: str) -> Timeframe:
    if provider != FXCM_PROVIDER:
        raise UnsupportedProviderError(f"Unsupported provider: {provider!r}.")
    try:
        return _FXCM_TIMEFRAME_REGISTRY[provider_timeframe]
    except KeyError as exc:
        raise UnsupportedProviderTimeframeError(
            f"Unsupported provider timeframe: {provider_timeframe!r}."
        ) from exc
