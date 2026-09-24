"""Build the CUSTOMER deliverable — and refuse to include anything else.

Written after a packaging mistake that would have mattered. Zipping
`release/event/` wholesale produced a "customer" archive containing
`Licensing/ADMIN_RUNBOOK.md` and `Licensing/access_registry.csv` — the second
of which holds OTHER CUSTOMERS' names, emails and licence IDs.

So the customer package is no longer "the event folder". It is an explicit
allow-list, and everything not on it is excluded by construction. A test
asserts the forbidden material cannot appear.
"""

from __future__ import annotations

import hashlib
import shutil
import zipfile
from pathlib import Path

__all__ = [
    "CUSTOMER_FILES",
    "FORBIDDEN_IN_CUSTOMER_PACKAGE",
    "build_customer_package",
    "stage_customer_package",
]

#: Exactly what a paying customer receives. Nothing is added implicitly.
CUSTOMER_FILES: dict[str, str] = {
    "EA/RC5_EA.ex5": "EA/RC5_EA.ex5",
    "EA/INSTALL.md": "EA/INSTALL.md",
    "Scanner/CUSTOMER_GUIDE.md": "Scanner/CUSTOMER_GUIDE.md",
    "Docs/RELEASE_NOTES.md": "RELEASE_NOTES.md",
}

#: Substrings that must never appear in a customer package path. These are not
#: style preferences — each one is either another customer's data, an internal
#: procedure, or source code.
FORBIDDEN_IN_CUSTOMER_PACKAGE: tuple[str, ...] = (
    "access_registry",
    "ADMIN_RUNBOOK",
    "OPERATIONS_CHEATSHEET",
    "rc5-license",
    "EVENT_CHECKLIST",
    "WALKTHROUGH",
    ".mq5",
    ".pine",
    ".db",
    ".env",
)

README = """RC5 SCANNER + EA -- v1.0

  EA/RC5_EA.ex5        the Expert Advisor. Install per EA/INSTALL.md.
  EA/INSTALL.md        installation, and the WebRequest setting you must enable
  Scanner/             how to use the TradingView scanner you were granted
  RELEASE_NOTES.md     what this version does, and what it does not claim
  CHECKSUMS.txt        SHA-256 of every file above

You received an EX5, not source. That is deliberate and is not a limitation of
your licence.

Your licence key was given to you separately. Keep it: it is shown once and
cannot be recovered -- it can only be reissued.

Your licence binds to ONE MT5 account number on ONE broker server. Changing
computers is fine; changing accounts needs support.

If your licence expires, is revoked, or cannot reach the licence server, the EA
stops opening NEW positions. Any position already open keeps its stop, its
target and its exits.
"""


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 16), b""):
            digest.update(block)
    return digest.hexdigest()


def stage_customer_package(source: Path, destination: Path) -> Path:
    """Copy the allow-listed files into `destination`. Returns the root."""
    root = destination / "RC5_Scanner_EA_v1.0"
    if root.exists():
        shutil.rmtree(root)
    for relative, target in CUSTOMER_FILES.items():
        origin = source / relative
        if not origin.is_file():
            raise FileNotFoundError(f"customer package is missing {relative}")
        landing = root / target
        landing.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(origin, landing)

    (root / "README.txt").write_text(README, encoding="utf-8", newline="\n")

    lines = [
        f"{_sha256(p)} *{p.relative_to(root).as_posix()}"
        for p in sorted(root.rglob("*"))
        if p.is_file()
    ]
    (root / "CHECKSUMS.txt").write_text(
        "\n".join(lines) + "\n", encoding="utf-8", newline="\n"
    )
    return root


def build_customer_package(source: Path, archive: Path) -> Path:
    """Stage and zip. Refuses to write an archive containing forbidden paths."""
    staged = stage_customer_package(source, archive.parent / "_stage")
    members = sorted(p for p in staged.rglob("*") if p.is_file())

    for member in members:
        name = member.relative_to(staged).as_posix()
        for forbidden in FORBIDDEN_IN_CUSTOMER_PACKAGE:
            if forbidden in name:
                raise ValueError(
                    f"refusing to package customer-forbidden path: {name}"
                )

    archive.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as zf:
        for member in members:
            zf.write(member, f"{staged.name}/{member.relative_to(staged)}")
    shutil.rmtree(staged.parent)
    return archive
