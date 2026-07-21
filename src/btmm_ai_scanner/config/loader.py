import os
import re
from collections.abc import Mapping

ENV_PREFIX = "BTMM_CONFIG_"

_KEY_PATTERN = re.compile(r"^[a-z][a-z0-9_]*$")
_SECRET_INDICATORS = (
    "password",
    "secret",
    "token",
    "credential",
    "api_key",
    "private_key",
)

_INVALID_KEY_MESSAGE = "Configuration keys must use lowercase snake_case."
_SECRET_KEY_MESSAGE = "Secret-like keys are not permitted in non-secret configuration."


class ConfigurationError(ValueError):
    """Base error for invalid non-secret configuration."""


class InvalidConfigurationKeyError(ConfigurationError):
    """Raised when a configuration key has an invalid form."""


class SecretConfigurationKeyError(ConfigurationError):
    """Raised when a secret-like key enters non-secret configuration."""


def _validate_key(key: object) -> str:
    if not isinstance(key, str) or not key or _KEY_PATTERN.match(key) is None:
        raise InvalidConfigurationKeyError(_INVALID_KEY_MESSAGE)
    return key


def _reject_if_secret(key: str) -> None:
    lowered = key.lower()
    for indicator in _SECRET_INDICATORS:
        if indicator in lowered:
            raise SecretConfigurationKeyError(_SECRET_KEY_MESSAGE)


def _validate_layer(layer: Mapping[str, object] | None) -> dict[str, object]:
    if layer is None:
        return {}
    result: dict[str, object] = {}
    for raw_key, value in layer.items():
        key = _validate_key(raw_key)
        _reject_if_secret(key)
        result[key] = value
    return result


def _extract_runtime_overrides(environ: Mapping[str, str]) -> dict[str, object]:
    result: dict[str, object] = {}
    seen_normalized: set[str] = set()
    for raw_key, value in environ.items():
        if not raw_key.startswith(ENV_PREFIX):
            continue
        suffix = raw_key[len(ENV_PREFIX) :]
        normalized = suffix.lower()
        if not normalized or _KEY_PATTERN.match(normalized) is None:
            raise InvalidConfigurationKeyError(_INVALID_KEY_MESSAGE)
        if normalized in seen_normalized:
            raise InvalidConfigurationKeyError(_INVALID_KEY_MESSAGE)
        seen_normalized.add(normalized)
        _reject_if_secret(normalized)
        result[normalized] = value
    return result


def _shallow_merge(*layers: Mapping[str, object]) -> dict[str, object]:
    merged: dict[str, object] = {}
    for layer in layers:
        merged.update(layer)
    return merged


def load_configuration(
    project_defaults: Mapping[str, object] | None = None,
    environment_overrides: Mapping[str, object] | None = None,
    *,
    environ: Mapping[str, str] | None = None,
) -> dict[str, object]:
    """Resolve non-secret configuration via a deterministic three-layer precedence."""
    defaults_layer = _validate_layer(project_defaults)
    environment_layer = _validate_layer(environment_overrides)

    active_environ: Mapping[str, str] = os.environ if environ is None else environ
    runtime_layer = _extract_runtime_overrides(active_environ)

    return _shallow_merge(defaults_layer, environment_layer, runtime_layer)
