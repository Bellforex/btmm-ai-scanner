import pytest

from btmm_ai_scanner.config.enums import InternalSymbol, Timeframe
from btmm_ai_scanner.market_data import source_mapping
from btmm_ai_scanner.market_data.source_mapping import (
    FXCM_PROVIDER,
    UnsupportedProviderError,
    UnsupportedProviderSymbolError,
    UnsupportedProviderTimeframeError,
    resolve_internal_symbol,
    resolve_timeframe,
)


def test_resolve_internal_symbol_maps_approved_fxcm_symbols() -> None:
    assert resolve_internal_symbol(FXCM_PROVIDER, "XAUUSD") == InternalSymbol.XAUUSD
    assert resolve_internal_symbol(FXCM_PROVIDER, "EURUSD") == InternalSymbol.EURUSD
    assert resolve_internal_symbol(FXCM_PROVIDER, "GBPUSD") == InternalSymbol.GBPUSD


def test_resolve_timeframe_maps_approved_fxcm_timeframes() -> None:
    expected = {
        "M1": Timeframe.M1,
        "M5": Timeframe.M5,
        "M15": Timeframe.M15,
        "H1": Timeframe.H1,
        "H3": Timeframe.H3,
        "H4": Timeframe.H4,
        "D1": Timeframe.D1,
        "W1": Timeframe.W1,
    }
    for provider_timeframe, timeframe in expected.items():
        assert resolve_timeframe(FXCM_PROVIDER, provider_timeframe) == timeframe


def test_resolve_internal_symbol_rejects_unsupported_provider() -> None:
    with pytest.raises(UnsupportedProviderError):
        resolve_internal_symbol("OANDA", "XAUUSD")
    with pytest.raises(UnsupportedProviderError):
        resolve_timeframe("OANDA", "M1")


def test_resolve_internal_symbol_rejects_unsupported_symbol() -> None:
    with pytest.raises(UnsupportedProviderSymbolError):
        resolve_internal_symbol(FXCM_PROVIDER, "USDJPY")


def test_resolve_timeframe_rejects_unsupported_timeframe() -> None:
    with pytest.raises(UnsupportedProviderTimeframeError):
        resolve_timeframe(FXCM_PROVIDER, "M30")


def test_source_mapping_is_case_sensitive() -> None:
    with pytest.raises(UnsupportedProviderSymbolError):
        resolve_internal_symbol(FXCM_PROVIDER, "xauusd")
    with pytest.raises(UnsupportedProviderTimeframeError):
        resolve_timeframe(FXCM_PROVIDER, "m1")
    with pytest.raises(UnsupportedProviderSymbolError):
        resolve_internal_symbol(FXCM_PROVIDER, " XAUUSD")
    with pytest.raises(UnsupportedProviderTimeframeError):
        resolve_timeframe(FXCM_PROVIDER, "M1 ")


def test_source_mapping_does_not_expose_tradingview_lookup() -> None:
    public_names = {name for name in vars(source_mapping) if not name.startswith("_")}
    assert not any("tradingview" in name.lower() for name in public_names)
    assert "FXCM:XAUUSD" not in source_mapping._FXCM_SYMBOL_REGISTRY

    # Both private registries are structurally read-only (MappingProxyType-backed):
    # mutation attempts must raise TypeError, not silently succeed.
    with pytest.raises(TypeError):
        source_mapping._FXCM_SYMBOL_REGISTRY["USDJPY"] = InternalSymbol.XAUUSD  # type: ignore[index]
    with pytest.raises(TypeError):
        source_mapping._FXCM_TIMEFRAME_REGISTRY["M30"] = Timeframe.M1  # type: ignore[index]
    with pytest.raises(TypeError):
        source_mapping._FXCM_TIMEFRAME_REGISTRY["M1"] = Timeframe.M5  # type: ignore[index]

    # Resolver behavior is unaffected by the failed mutation attempts.
    assert resolve_internal_symbol(FXCM_PROVIDER, "XAUUSD") == InternalSymbol.XAUUSD
    assert resolve_timeframe(FXCM_PROVIDER, "M1") == Timeframe.M1
    with pytest.raises(UnsupportedProviderSymbolError):
        resolve_internal_symbol(FXCM_PROVIDER, "USDJPY")
    with pytest.raises(UnsupportedProviderTimeframeError):
        resolve_timeframe(FXCM_PROVIDER, "M30")
