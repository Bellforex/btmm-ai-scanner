"""Bot configuration.

One frozen dataclass, loadable from a JSON file and/or CLI overrides. Unknown
keys are refused, and live-trading keys are refused with
``LiveTradingForbiddenError`` (see ``botdryrun.safety``). There is no
``live_broker_enabled`` field: it cannot be set to anything.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import asdict, dataclass, fields, replace
from datetime import UTC, datetime
from decimal import Decimal
from enum import StrEnum
from pathlib import Path
from typing import Any

from botdryrun.safety import (
    EXECUTION_MODE,
    FORBIDDEN_CONFIG_KEYS,
    LiveTradingForbiddenError,
    assert_paper_mode,
)

__all__ = [
    "BotConfig",
    "ConfigError",
    "DataSourceKind",
    "EntryMode",
    "GapPolicy",
    "ScannerProfile",
    "parse_utc",
]


class ConfigError(ValueError):
    pass


class DataSourceKind(StrEnum):
    #: The verified FXCM V1-A / RC3 files (SHA-256 pinned by the repo loaders).
    FXCM_V1A = "FXCM_V1A"
    #: A directory of ``<TF>.csv`` files in the same format. UNVERIFIED; for
    #: synthetic fixtures and experiments only.
    CSV_DIR = "CSV_DIR"


class ScannerProfile(StrEnum):
    #: RC4 market-framework profile (``iter_level_a_bars(rc4_framework=True)``)
    #: on top of the RC3 freshness contract. The default.
    RC4 = "RC4"
    #: The plain RC3 freshness contract (``rc4_framework=False``).
    RC3 = "RC3"


class GapPolicy(StrEnum):
    CONTINUE = "CONTINUE"
    HALT = "HALT"


class EntryMode(StrEnum):
    #: Resting limit at the POI's proximal edge (practice policy default).
    LIMIT_AT_ZONE = "LIMIT_AT_ZONE"
    #: Market entry at the next host bar's open.
    NEXT_OPEN = "NEXT_OPEN"


def parse_utc(text: str) -> datetime:
    value = datetime.fromisoformat(text.replace("Z", "+00:00"))
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


@dataclass(frozen=True)
class BotConfig:
    # --- window / data ---------------------------------------------------
    window_start_utc: datetime
    window_end_utc: datetime
    dataset_root: str
    data_source: DataSourceKind = DataSourceKind.FXCM_V1A
    host_timeframe: str = "M15"
    context_timeframes: tuple[str, ...] = ("W1", "D1", "H4", "H1", "M5")
    context_lookback_bars: int = 40
    gap_policy: GapPolicy = GapPolicy.CONTINUE
    scanner_profile: ScannerProfile = ScannerProfile.RC4
    # --- paper account / practice policy ----------------------------------
    initial_balance: Decimal = Decimal("10000")
    risk_fraction: Decimal = Decimal("0.01")
    max_concurrent_positions: int = 2
    reward_risk: Decimal = Decimal("2")
    entry_mode: EntryMode = EntryMode.LIMIT_AT_ZONE
    pending_expiry_bars: int = 16
    stop_buffer: Decimal = Decimal("0")
    #: Adverse price offset applied to every simulated fill/exit. Default 0.
    slippage: Decimal = Decimal("0")
    #: Commission per unit per side. Default 0.
    commission_per_unit: Decimal = Decimal("0")
    #: Always "PAPER". Present so a persisted config states it explicitly.
    execution_mode: str = EXECUTION_MODE

    def __post_init__(self) -> None:
        assert_paper_mode(self.execution_mode)
        if self.window_end_utc < self.window_start_utc:
            raise ConfigError("window_end_utc precedes window_start_utc")
        if self.context_lookback_bars < 0:
            raise ConfigError("context_lookback_bars must be >= 0")
        if not (Decimal("0") < self.risk_fraction <= Decimal("0.05")):
            raise ConfigError("risk_fraction must be in (0, 0.05]")
        if self.max_concurrent_positions < 1:
            raise ConfigError("max_concurrent_positions must be >= 1")
        if self.reward_risk <= 0:
            raise ConfigError("reward_risk must be > 0")
        if self.pending_expiry_bars < 1:
            raise ConfigError("pending_expiry_bars must be >= 1")
        if self.initial_balance <= 0:
            raise ConfigError("initial_balance must be > 0")
        for name in ("stop_buffer", "slippage", "commission_per_unit"):
            if getattr(self, name) < 0:
                raise ConfigError(f"{name} must be >= 0")
        if self.host_timeframe in self.context_timeframes:
            raise ConfigError("host timeframe must not be a context timeframe")

    # ------------------------------------------------------------------
    def to_json(self) -> str:
        payload: dict[str, Any] = {}
        for key, value in asdict(self).items():
            if isinstance(value, datetime):
                payload[key] = value.isoformat()
            elif isinstance(value, Decimal):
                payload[key] = str(value)
            elif isinstance(value, tuple):
                payload[key] = list(value)
            elif isinstance(value, StrEnum):
                payload[key] = value.value
            else:
                payload[key] = value
        return json.dumps(payload, sort_keys=True, separators=(",", ":"))

    @classmethod
    def from_mapping(cls, raw: Mapping[str, Any]) -> BotConfig:
        forbidden = sorted(set(raw) & FORBIDDEN_CONFIG_KEYS)
        if forbidden:
            raise LiveTradingForbiddenError(
                f"config keys {forbidden} are refused: botdryrun has no live "
                "execution path and no credential handling"
            )
        known = {f.name for f in fields(cls)}
        unknown = sorted(set(raw) - known)
        if unknown:
            raise ConfigError(f"unknown config keys: {unknown}")
        kwargs: dict[str, Any] = {}
        for key, value in raw.items():
            if value is None:
                continue
            if key in ("window_start_utc", "window_end_utc"):
                kwargs[key] = value if isinstance(value, datetime) else parse_utc(str(value))
            elif key in (
                "initial_balance",
                "risk_fraction",
                "reward_risk",
                "stop_buffer",
                "slippage",
                "commission_per_unit",
            ):
                kwargs[key] = Decimal(str(value))
            elif key == "context_timeframes":
                kwargs[key] = tuple(str(v) for v in value)
            elif key == "data_source":
                kwargs[key] = DataSourceKind(str(value))
            elif key == "gap_policy":
                kwargs[key] = GapPolicy(str(value))
            elif key == "scanner_profile":
                kwargs[key] = ScannerProfile(str(value))
            elif key == "entry_mode":
                kwargs[key] = EntryMode(str(value))
            elif key in ("context_lookback_bars", "max_concurrent_positions", "pending_expiry_bars"):
                kwargs[key] = int(value)
            else:
                kwargs[key] = str(value)
        try:
            return cls(**kwargs)
        except TypeError as exc:
            raise ConfigError(str(exc)) from exc

    @classmethod
    def from_json(cls, text: str) -> BotConfig:
        return cls.from_mapping(json.loads(text))

    @classmethod
    def load(cls, path: Path, overrides: Mapping[str, Any] | None = None) -> BotConfig:
        raw: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
        if overrides:
            raw.update({k: v for k, v in overrides.items() if v is not None})
        return cls.from_mapping(raw)

    def with_overrides(self, **changes: Any) -> BotConfig:
        forbidden = sorted(set(changes) & FORBIDDEN_CONFIG_KEYS)
        if forbidden:
            raise LiveTradingForbiddenError(f"config keys {forbidden} are refused")
        return replace(self, **changes)
