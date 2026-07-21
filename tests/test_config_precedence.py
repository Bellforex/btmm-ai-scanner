import pytest

from btmm_ai_scanner.config import (
    InvalidConfigurationKeyError,
    SecretConfigurationKeyError,
    load_configuration,
)

_SECRET_INDICATORS = (
    "password",
    "secret",
    "token",
    "credential",
    "api_key",
    "private_key",
)


def test_defaults_are_preserved() -> None:
    defaults = {"log_level": "info"}
    result = load_configuration(defaults, None, environ={})
    assert result == {"log_level": "info"}


def test_environment_overrides_defaults() -> None:
    defaults = {"log_level": "info"}
    environment_overrides = {"log_level": "debug"}
    result = load_configuration(defaults, environment_overrides, environ={})
    assert result["log_level"] == "debug"


def test_runtime_environment_overrides_all_layers() -> None:
    defaults = {"log_level": "info"}
    environment_overrides = {"log_level": "debug"}
    environ = {"BTMM_CONFIG_LOG_LEVEL": "warning"}
    result = load_configuration(defaults, environment_overrides, environ=environ)
    assert result["log_level"] == "warning"


def test_input_mappings_are_not_mutated() -> None:
    defaults = {"log_level": "info"}
    environment_overrides = {"log_level": "debug"}
    environ = {"BTMM_CONFIG_LOG_LEVEL": "warning"}

    defaults_snapshot = dict(defaults)
    environment_overrides_snapshot = dict(environment_overrides)
    environ_snapshot = dict(environ)

    load_configuration(defaults, environment_overrides, environ=environ)

    assert defaults == defaults_snapshot
    assert environment_overrides == environment_overrides_snapshot
    assert environ == environ_snapshot


def test_runtime_environment_keys_are_normalized() -> None:
    environ = {"BTMM_CONFIG_LOG_LEVEL": "debug"}
    result = load_configuration(environ=environ)
    assert result == {"log_level": "debug"}


def test_shallow_merge_replaces_nested_value() -> None:
    defaults = {"nested": {"x": 1, "y": 2}}
    environment_overrides = {"nested": {"x": 9}}
    result = load_configuration(defaults, environment_overrides, environ={})
    assert result["nested"] == {"x": 9}


@pytest.mark.parametrize("indicator", _SECRET_INDICATORS)
@pytest.mark.parametrize("layer", ["defaults", "environment_overrides", "environ"])
def test_secret_like_keys_are_rejected(indicator: str, layer: str) -> None:
    key = f"my_{indicator}_value"

    with pytest.raises(SecretConfigurationKeyError) as exc_info:
        if layer == "defaults":
            load_configuration({key: "x"}, environ={})
        elif layer == "environment_overrides":
            load_configuration({}, {key: "x"}, environ={})
        else:
            load_configuration(environ={f"BTMM_CONFIG_{key.upper()}": "x"})

    message = str(exc_info.value)
    assert message == "Secret-like keys are not permitted in non-secret configuration."
    assert key not in message


@pytest.mark.parametrize("invalid_key", ["Invalid-Key", "1abc", "UPPERCASE", ""])
def test_invalid_configuration_key_is_rejected(invalid_key: str) -> None:
    with pytest.raises(InvalidConfigurationKeyError) as exc_info:
        load_configuration({invalid_key: "x"}, environ={})

    assert str(exc_info.value) == "Configuration keys must use lowercase snake_case."


def test_empty_runtime_suffix_is_rejected() -> None:
    environ = {"BTMM_CONFIG_": "x"}
    with pytest.raises(InvalidConfigurationKeyError) as exc_info:
        load_configuration(environ=environ)

    assert str(exc_info.value) == "Configuration keys must use lowercase snake_case."


def test_duplicate_normalized_runtime_keys_are_rejected() -> None:
    environ = {
        "BTMM_CONFIG_LOG_LEVEL": "debug",
        "BTMM_CONFIG_Log_Level": "warning",
    }
    with pytest.raises(InvalidConfigurationKeyError):
        load_configuration(environ=environ)


def test_result_is_deterministic() -> None:
    defaults = {"log_level": "info"}
    environment_overrides = {"log_level": "debug"}
    environ = {"BTMM_CONFIG_TIMEFRAME": "M15"}

    first = load_configuration(defaults, environment_overrides, environ=environ)
    second = load_configuration(defaults, environment_overrides, environ=environ)

    assert first == second
