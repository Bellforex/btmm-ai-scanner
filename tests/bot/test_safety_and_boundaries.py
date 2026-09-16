"""Hard guarantees: live execution is impossible, and the bot has no forked
scanner semantics (the scanner adapter is its single entry point)."""

from __future__ import annotations

import ast
import dataclasses
import json
from pathlib import Path

import pytest

import botdryrun
from botdryrun.config import BotConfig, ConfigError
from botdryrun.safety import (
    EXECUTION_MODE,
    FORBIDDEN_CONFIG_KEYS,
    LiveBrokerDisabled,
    LiveTradingForbiddenError,
    assert_paper_mode,
)

PACKAGE = Path(botdryrun.__file__).resolve().parent
_BASE = {
    "window_start_utc": "2026-08-17T19:00:00Z",
    "window_end_utc": "2026-08-17T20:00:00Z",
    "dataset_root": ".",
}


def _imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module)
            names.update(f"{node.module}.{alias.name}" for alias in node.names)
    return names


def _modules() -> dict[str, set[str]]:
    return {p.name: _imports(p) for p in sorted(PACKAGE.glob("*.py"))}


# ---------------------------------------------------------------------------
# Live execution is impossible
# ---------------------------------------------------------------------------


def test_live_broker_cannot_be_constructed() -> None:
    with pytest.raises(LiveTradingForbiddenError):
        LiveBrokerDisabled()
    with pytest.raises(LiveTradingForbiddenError):
        LiveBrokerDisabled(api_key="x", account="y")


def test_config_has_no_live_switch_and_refuses_live_keys() -> None:
    field_names = {f.name for f in dataclasses.fields(BotConfig)}
    assert not field_names & FORBIDDEN_CONFIG_KEYS
    assert "live_broker_enabled" not in field_names
    for key in sorted(FORBIDDEN_CONFIG_KEYS):
        for value in (True, False, "true", 0, None):
            with pytest.raises(LiveTradingForbiddenError):
                BotConfig.from_mapping({**_BASE, key: value})
    with pytest.raises(ConfigError):
        BotConfig.from_mapping({**_BASE, "some_unknown_key": 1})
    config = BotConfig.from_mapping(_BASE)
    with pytest.raises(LiveTradingForbiddenError):
        config.with_overrides(live_broker_enabled=True)
    assert config.execution_mode == EXECUTION_MODE == "PAPER"


def test_execution_mode_cannot_be_anything_but_paper() -> None:
    for mode in ("LIVE", "live", "REAL", ""):
        with pytest.raises(LiveTradingForbiddenError):
            BotConfig.from_mapping({**_BASE, "execution_mode": mode})
        with pytest.raises(LiveTradingForbiddenError):
            assert_paper_mode(mode)


def test_cli_refuses_a_live_config_file(tmp_path: Path) -> None:
    from botdryrun.__main__ import main

    config_path = tmp_path / "live.json"
    config_path.write_text(json.dumps({**_BASE, "live_broker_enabled": True}), encoding="utf-8")
    assert main(["replay", "--state-dir", str(tmp_path / "s"), "--config", str(config_path)]) == 6


def test_package_imports_no_network_or_broker_client_library() -> None:
    forbidden_roots = {
        "socket", "ssl", "http", "urllib", "urllib3", "requests", "httpx", "aiohttp",
        "websocket", "websockets", "ftplib", "smtplib", "xmlrpc", "grpc", "ccxt", "MetaTrader5",
        "oandapyV20", "ib_insync", "alpaca_trade_api", "fxcmpy",
    }
    for module, names in _modules().items():
        roots = {name.split(".")[0] for name in names}
        assert not roots & forbidden_roots, (module, roots & forbidden_roots)


def test_the_only_broker_the_engine_builds_is_the_paper_broker() -> None:
    engine_imports = _modules()["engine.py"]
    assert "botdryrun.broker.PaperBroker" in engine_imports
    assert not any("LiveBroker" in name for name in engine_imports)
    for module, names in _modules().items():
        if module != "safety.py":
            assert not any("LiveBrokerDisabled" in n for n in names), module


# ---------------------------------------------------------------------------
# No forked semantics
# ---------------------------------------------------------------------------


def test_scanner_adapter_is_the_only_module_driving_the_scanner() -> None:
    modules = _modules()
    drivers = {
        module
        for module, names in modules.items()
        if any(
            n.startswith(("tests.parity_support.level_a_replay", "tests.parity_support.p8_alert_oracle",
                          "tests.parity_support.p5_active_poi_loop_model"))
            or n.startswith(("btmm_ai_scanner.scanner", "btmm_ai_scanner.poi", "btmm_ai_scanner.btrc",
                             "btmm_ai_scanner.btmm", "btmm_ai_scanner.structure"))
            for n in names
        )
    }
    assert drivers == {"scanner_adapter.py"}
    assert "tests.parity_support.level_a_replay.iter_level_a_bars" in modules["scanner_adapter.py"]


def test_scanner_adapter_pins_the_rc3_contract() -> None:
    tree = ast.parse((PACKAGE / "scanner_adapter.py").read_text(encoding="utf-8"))
    calls = [
        node for node in ast.walk(tree)
        if isinstance(node, ast.Call) and getattr(node.func, "id", None) == "iter_level_a_bars"
    ]
    assert len(calls) == 1
    keywords = {k.arg: k.value for k in calls[0].keywords}
    assert isinstance(keywords["rc3_freshness"], ast.Constant) and keywords["rc3_freshness"].value is True
    assert ast.unparse(keywords["warmup_feed_policy"]) == "WarmupFeedPolicy.AVAILABILITY"


def test_signals_only_originate_from_consumed_p8_events() -> None:
    """Structural: the policy receives ``batch.new_events`` (the consumer's
    output) and nothing else event-like; its decision method never reads
    ``snapshot.decisions`` (P5 rows), so a bare actionable decision cannot
    produce a signal. Behavioural coverage: POI 6 in
    ``test_restart_and_trading`` is actionable on every bar with no event and
    never gets a signal."""
    engine_src = (PACKAGE / "engine.py").read_text(encoding="utf-8")
    assert "self.policy.on_events(batch.new_events, snap, broker)" in engine_src
    assert engine_src.count(".on_events(") == 1
    policy_src = (PACKAGE / "policy.py").read_text(encoding="utf-8")
    assert ".decisions" not in policy_src
    assert "final_score" not in policy_src and "final_confluence_score" not in policy_src
