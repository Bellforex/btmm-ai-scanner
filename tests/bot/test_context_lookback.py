"""The bot must not starve the RC4 scanner of higher-timeframe context.

Finding (2026-09-19): with the old bot default of 40 pre-window context bars
the D1 / W1 trend context never formed and a real-data replay produced zero
actionable permissions; with the scanner authority's own requirement (250) the
same day produced actionable events, intents and paper orders. The default is
therefore inherited from the scanner, not restated in the bot.
"""

from __future__ import annotations

import argparse
from datetime import UTC, datetime

from botdryrun.__main__ import _build_config
from botdryrun.config import BotConfig
from tests.parity_support.rc3_daily_authority import DEFAULT_CONTEXT_LOOKBACK_BARS


def test_default_context_lookback_is_the_scanner_requirement() -> None:
    config = BotConfig(
        window_start_utc=datetime(2026, 8, 9, 22, tzinfo=UTC),
        window_end_utc=datetime(2026, 8, 10, 20, 45, tzinfo=UTC),
        dataset_root="unused",
    )
    assert config.context_lookback_bars == DEFAULT_CONTEXT_LOOKBACK_BARS == 250
    assert config.context_lookback_bars != 40


def test_cli_without_the_flag_uses_the_scanner_requirement() -> None:
    args = argparse.Namespace(
        trading_day="2026-08-10",
        days=1,
        start=None,
        end=None,
        dataset_root="unused",
        data_source=None,
        context_lookback_bars=None,
        gap_policy=None,
        entry_mode=None,
        scanner_profile=None,
        context_timeframes=None,
        config=None,
    )
    assert _build_config(args).context_lookback_bars == DEFAULT_CONTEXT_LOOKBACK_BARS
