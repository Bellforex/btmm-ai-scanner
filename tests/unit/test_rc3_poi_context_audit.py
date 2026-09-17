"""RC3 market-context audit: context is causal and direction-symmetric.

The audit (``tests/parity_support/rc3_poi_context_audit.py``) is diagnostic
evidence for future context gates; these tests lock that it never uses a
structure break later than the POI and that a price mirror swaps bullish and
bearish exactly (trend direction never inverted).
"""

from __future__ import annotations

from collections import Counter
from pathlib import Path

from btmm_ai_scanner.config.enums import Timeframe
from tests.parity_support.ob_origin_series import mirror, rows_to_candles
from tests.parity_support.rc3_poi_context_audit import context_rows
from tests.unit.test_rc3_order_block_leg_origin import _continuation, _reversal


def _rows(tmp_path: Path, name: str, rows):
    return context_rows(rows_to_candles(rows, tmp_path, name), Timeframe.M15)


def test_leg_used_for_context_is_never_after_the_poi(tmp_path: Path) -> None:
    for name, series in (("c", _continuation()), ("r", _reversal())):
        for row in _rows(tmp_path, name, series):
            if row["leg_id"] is not None:
                assert row["leg_id"] <= row["availability"], row


def test_context_mirrors_exactly_for_sell_series(tmp_path: Path) -> None:
    def summary(rows):
        flip = {"BULLISH": "BEARISH", "BEARISH": "BULLISH"}
        return Counter(
            (
                r["availability"],
                r["role"],
                r["retracement_bucket"],
                flip.get(r["direction"], r["direction"]),
            )
            for r in rows
        )

    buy = _rows(tmp_path, "buy", _continuation())
    sell = _rows(tmp_path, "sell", mirror(_continuation()))
    assert buy
    assert Counter(
        (r["availability"], r["role"], r["retracement_bucket"], r["direction"])
        for r in buy
    ) == summary(sell)


def test_the_continuation_leg_origin_order_block_is_trend_aligned(
    tmp_path: Path,
) -> None:
    rows = _rows(tmp_path, "ob", _continuation())
    obs = [r for r in rows if r["type"] == "BUY_ORDER_BLOCK"]
    assert obs and all(r["role"] == "TREND_ALIGNED" for r in obs)
    assert all(r["leg_type"] == "BULLISH_BOS" for r in obs)
