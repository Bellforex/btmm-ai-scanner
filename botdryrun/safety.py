"""The hard dry-run guarantee.

This package is a PAPER / DRY-RUN / SIMULATION bot. There is no real broker,
no network order API, no credential handling and no live-order code path.

The guarantee is structural, not a flag:

* ``EXECUTION_MODE`` is the constant ``"PAPER"`` and nothing reads any other
  value.
* ``LiveBrokerDisabled`` is the only object in the package whose name refers
  to a live broker, and constructing it raises ``LiveTradingForbiddenError``
  unconditionally. It exists so that "wire up a live broker" fails loudly at
  the first line instead of silently doing something.
* ``botdryrun.config`` has no ``live_broker_enabled`` field; a config file or
  flag that tries to set one (to ANY value) is refused with
  ``LiveTradingForbiddenError``.
* ``tests/bot/test_safety.py`` asserts all of the above and that no module in
  the package imports a networking library.
"""

from __future__ import annotations

from typing import Final, NoReturn

__all__ = [
    "EXECUTION_MODE",
    "FORBIDDEN_CONFIG_KEYS",
    "LiveBrokerDisabled",
    "LiveTradingForbiddenError",
    "assert_paper_mode",
]

EXECUTION_MODE: Final = "PAPER"

#: Config keys that are refused outright, whatever their value. Anything that
#: looks like it would connect to a real account is on this list; every other
#: unknown key is refused by ``botdryrun.config`` as well.
FORBIDDEN_CONFIG_KEYS: Final[frozenset[str]] = frozenset(
    {
        "live_broker_enabled",
        "live_trading",
        "live",
        "broker_url",
        "broker_api_key",
        "api_key",
        "api_secret",
        "account_id",
        "password",
        "credentials",
        "token",
    }
)


class LiveTradingForbiddenError(RuntimeError):
    """Raised on any attempt to reach a live-execution path."""


class LiveBrokerDisabled:
    """Placeholder for a live broker. It can never be constructed."""

    def __init__(self, *args: object, **kwargs: object) -> None:
        raise LiveTradingForbiddenError(
            "botdryrun is a paper/dry-run bot: live execution is disabled and "
            "cannot be enabled by configuration."
        )

    def place_order(self, *args: object, **kwargs: object) -> NoReturn:  # pragma: no cover
        raise LiveTradingForbiddenError("live execution is disabled")


def assert_paper_mode(mode: str) -> None:
    if mode != EXECUTION_MODE:
        raise LiveTradingForbiddenError(
            f"execution mode {mode!r} refused: only {EXECUTION_MODE!r} exists"
        )
