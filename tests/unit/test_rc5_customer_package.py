"""The customer package must not leak other customers' data, or source.

This file exists because zipping `release/event/` wholesale produced a
"customer" archive containing `Licensing/access_registry.csv` — the file that
holds every other customer's name, email and licence ID — together with the
internal admin runbook.

Nobody would have noticed at an event. The buyer would simply have received it.
"""

from __future__ import annotations

import zipfile
from pathlib import Path

import pytest

from tools.rc5_customer_package import (
    CUSTOMER_FILES,
    FORBIDDEN_IN_CUSTOMER_PACKAGE,
    build_customer_package,
    stage_customer_package,
)

_REPO = Path(__file__).resolve().parents[2]
_EVENT = _REPO / "release" / "event"


def test_the_event_folder_still_has_every_customer_file() -> None:
    """If a file is renamed, this fails here rather than at the desk."""
    missing = [rel for rel in CUSTOMER_FILES if not (_EVENT / rel).is_file()]
    assert not missing, missing


def test_the_customer_package_contains_exactly_the_allow_list(
    tmp_path: Path,
) -> None:
    root = stage_customer_package(_EVENT, tmp_path)
    got = {p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file()}
    expected = set(CUSTOMER_FILES.values()) | {"README.txt", "CHECKSUMS.txt"}
    assert got == expected


def test_THE_REGISTRY_AND_RUNBOOK_CANNOT_REACH_A_CUSTOMER(
    tmp_path: Path,
) -> None:
    """THE invariant this module exists for."""
    archive = build_customer_package(_EVENT, tmp_path / "customer.zip")
    with zipfile.ZipFile(archive) as zf:
        names = zf.namelist()

    joined = " ".join(names).lower()
    for forbidden in FORBIDDEN_IN_CUSTOMER_PACKAGE:
        assert forbidden.lower() not in joined, forbidden

    # named explicitly, so the intent survives a refactor of the tuple
    assert not any("registry" in n.lower() for n in names)
    assert not any("admin" in n.lower() for n in names)
    assert not any(n.endswith(".mq5") for n in names)


def test_the_builder_refuses_rather_than_silently_dropping(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A forbidden file that somehow gets staged must STOP the build."""
    import tools.rc5_customer_package as mod

    real_stage = mod.stage_customer_package

    def staging_then_poison(source: Path, destination: Path) -> Path:
        root = real_stage(source, destination)
        (root / "access_registry.csv").write_text("leak", encoding="utf-8")
        return root

    monkeypatch.setattr(mod, "stage_customer_package", staging_then_poison)
    with pytest.raises(ValueError, match="customer-forbidden"):
        mod.build_customer_package(_EVENT, tmp_path / "bad.zip")
    assert not (tmp_path / "bad.zip").exists(), "a refused build wrote an archive"


def test_the_checksums_file_covers_every_shipped_file(tmp_path: Path) -> None:
    root = stage_customer_package(_EVENT, tmp_path)
    listed = {
        line.split(" *", 1)[1]
        for line in (root / "CHECKSUMS.txt").read_text().splitlines()
        if " *" in line
    }
    shipped = {
        p.relative_to(root).as_posix()
        for p in root.rglob("*")
        if p.is_file() and p.name != "CHECKSUMS.txt"
    }
    assert shipped <= listed


def test_the_shipped_ex5_is_the_repository_build(tmp_path: Path) -> None:
    """The customer's binary must be the one that passed acceptance."""
    import hashlib

    def digest(path: Path) -> str:
        return hashlib.sha256(path.read_bytes()).hexdigest()

    assert digest(_EVENT / "EA" / "RC5_EA.ex5") == digest(
        _REPO / "mt5" / "Experts" / "RC5_EA.ex5"
    )
