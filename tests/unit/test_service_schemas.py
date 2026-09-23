import pytest
from pydantic import ValidationError

from btmm_ai_scanner.service.schemas import (
    MAX_CANDLES_PER_TIMEFRAME,
    MAX_TIMEFRAMES_PER_REQUEST,
    AnalyzeRequest,
    RawBar,
)

_VALID_BAR = {
    "time": "2026-01-01T00:00:00+00:00",
    "open": "2000.00",
    "high": "2001.00",
    "low": "1999.00",
    "close": "2000.50",
    "volume": "10",
}


def test_raw_bar_accepts_a_well_formed_json_bar() -> None:
    bar = RawBar.model_validate(_VALID_BAR)
    assert bar.close.__class__.__name__ == "Decimal"
    assert bar.time.tzinfo is not None


def test_raw_bar_rejects_naive_datetime() -> None:
    with pytest.raises(ValidationError):
        RawBar.model_validate({**_VALID_BAR, "time": "2026-01-01T00:00:00"})


def test_raw_bar_rejects_non_positive_price() -> None:
    with pytest.raises(ValidationError):
        RawBar.model_validate({**_VALID_BAR, "open": "0"})


def test_raw_bar_rejects_high_below_open() -> None:
    with pytest.raises(ValidationError):
        RawBar.model_validate({**_VALID_BAR, "high": "1000.00"})


def test_raw_bar_rejects_low_above_close() -> None:
    with pytest.raises(ValidationError):
        RawBar.model_validate({**_VALID_BAR, "low": "2500.00"})


def test_raw_bar_rejects_negative_volume() -> None:
    with pytest.raises(ValidationError):
        RawBar.model_validate({**_VALID_BAR, "volume": "-1"})


def test_raw_bar_rejects_unknown_field() -> None:
    with pytest.raises(ValidationError):
        RawBar.model_validate({**_VALID_BAR, "unexpected_field": 1})


def _analyze_request(**overrides: object) -> dict:
    payload = {
        "request_id": "req-1",
        "symbol": "XAUUSD",
        "mode": "SCALP",
        "timeframes": {"M5": [_VALID_BAR]},
    }
    payload.update(overrides)
    return payload


def test_analyze_request_accepts_a_well_formed_bundle() -> None:
    request = AnalyzeRequest.model_validate(_analyze_request())
    assert request.source_provider == "BELLFOREX_WEB"


def test_analyze_request_rejects_unknown_symbol() -> None:
    with pytest.raises(ValidationError):
        AnalyzeRequest.model_validate(_analyze_request(symbol="DOGEUSD"))


def test_analyze_request_rejects_unknown_timeframe_key() -> None:
    with pytest.raises(ValidationError):
        AnalyzeRequest.model_validate(
            _analyze_request(timeframes={"M45": [_VALID_BAR]})
        )


def test_analyze_request_rejects_empty_timeframes() -> None:
    with pytest.raises(ValidationError):
        AnalyzeRequest.model_validate(_analyze_request(timeframes={}))


def test_analyze_request_rejects_empty_bar_list_for_a_timeframe() -> None:
    with pytest.raises(ValidationError):
        AnalyzeRequest.model_validate(_analyze_request(timeframes={"M5": []}))


def test_analyze_request_rejects_too_many_candles_in_one_timeframe() -> None:
    too_many = [_VALID_BAR] * (MAX_CANDLES_PER_TIMEFRAME + 1)
    with pytest.raises(ValidationError):
        AnalyzeRequest.model_validate(_analyze_request(timeframes={"M5": too_many}))


def test_analyze_request_rejects_more_timeframes_than_the_enum_has() -> None:
    all_timeframes = [
        "M1", "M5", "M15", "H1", "H2", "H3", "H4", "H6", "H9", "H12", "D1", "W1", "MN1",
    ]
    assert len(all_timeframes) == MAX_TIMEFRAMES_PER_REQUEST
    # Constructing a 14th distinct Timeframe key is impossible (the enum only
    # has 13 members), so this asserts the guard's bound matches the enum
    # exactly rather than trying to smuggle in an unknown 14th key.
    bundle = {tf: [_VALID_BAR] for tf in all_timeframes}
    request = AnalyzeRequest.model_validate(_analyze_request(timeframes=bundle))
    assert len(request.timeframes) == MAX_TIMEFRAMES_PER_REQUEST


def test_analyze_request_rejects_unknown_mode() -> None:
    with pytest.raises(ValidationError):
        AnalyzeRequest.model_validate(_analyze_request(mode="POSITION_TRADE"))


def test_analyze_request_rejects_unexpected_top_level_field() -> None:
    with pytest.raises(ValidationError):
        AnalyzeRequest.model_validate(_analyze_request(unexpected="x"))
