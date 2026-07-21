import importlib
import os
import socket
import sys
import tempfile

import pytest


def test_package_imports() -> None:
    import btmm_ai_scanner

    assert btmm_ai_scanner is not None


def test_config_public_exports_import() -> None:
    from btmm_ai_scanner import config

    expected = {
        "ENV_PREFIX",
        "ConfigurationError",
        "InternalSymbol",
        "InvalidConfigurationKeyError",
        "SecretConfigurationKeyError",
        "Timeframe",
        "load_configuration",
    }
    assert set(config.__all__) == expected
    for name in expected:
        assert hasattr(config, name)


def test_import_has_no_filesystem_or_network_side_effect(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    package_module_names = [
        name
        for name in list(sys.modules)
        if name == "btmm_ai_scanner" or name.startswith("btmm_ai_scanner.")
    ]
    for name in package_module_names:
        monkeypatch.delitem(sys.modules, name, raising=False)

    def _blocked_socket(*args: object, **kwargs: object) -> None:
        raise AssertionError("Network access is not permitted during import.")

    monkeypatch.setattr(socket, "socket", _blocked_socket)
    monkeypatch.setattr(sys, "dont_write_bytecode", True)

    original_cwd = os.getcwd()
    with tempfile.TemporaryDirectory() as temp_dir:
        before = sorted(os.listdir(temp_dir))
        os.chdir(temp_dir)
        try:
            package = importlib.import_module("btmm_ai_scanner")
            config_package = importlib.import_module("btmm_ai_scanner.config")
        finally:
            os.chdir(original_cwd)

        after = sorted(os.listdir(temp_dir))
        assert before == after
        assert package is not None
        assert config_package is not None
