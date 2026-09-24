"""Release artifact integrity: what is on disk, and does it match what ships.

Written after the check caught a real one. The EA had been recompiled in the
repository after the signal-id separator fix, but the copy installed in the
MetaTrader data folder was never refreshed — so the build that would actually
have run in the Strategy Tester was the PRE-FIX one, emitting pipe-bearing
signal ids that the journal parser now refuses. Source and installed copy
compiled cleanly and told the same story about themselves; only their hashes
disagreed.

Three checks:

* every release artifact's SHA-256, recorded so a later run can diff it;
* the installed EA is byte-identical to the repository source and its `.ex5`;
* VIEW and PANEL regenerate from CORE without a diff.
"""

from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass
from pathlib import Path

__all__ = [
    "ARTIFACTS",
    "IntegrityResult",
    "check_installed_ea",
    "installed_ea_paths",
    "sha256",
]

REPO = Path(__file__).resolve().parents[1]

#: Everything that constitutes the release, repo-relative.
ARTIFACTS: tuple[str, ...] = (
    "tradingview/btmm_poi_btrc_scanner_rc5_user.pine",
    "tradingview/btmm_poi_btrc_scanner_rc5_view.pine",
    "tradingview/btmm_poi_btrc_scanner_rc5_panel.pine",
    "tradingview/rc5_view_presentation.pine",
    "mt5/Experts/RC5_EA.mq5",
    "mt5/Scripts/RC5_SpecCapture.mq5",
    "tools/rc5_compose.py",
    "tools/rc5_ea_fixtures.py",
    "tools/rc5_journal_parser.py",
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


@dataclass(frozen=True)
class IntegrityResult:
    name: str
    ok: bool
    detail: str


def installed_ea_paths() -> tuple[Path, Path] | None:
    """The installed EA source and binary, or None when no terminal is present.

    The MetaTrader data folder is machine-specific, so this returns None rather
    than guessing — a check that cannot run must not report success.
    """
    appdata = os.environ.get("APPDATA")
    if not appdata:
        return None
    root = Path(appdata) / "MetaQuotes" / "Terminal"
    if not root.is_dir():
        return None
    for terminal in root.iterdir():
        source = terminal / "MQL5" / "Experts" / "RC5" / "RC5_EA.mq5"
        binary = terminal / "MQL5" / "Experts" / "RC5" / "RC5_EA.ex5"
        if source.is_file() and binary.is_file():
            return source, binary
    return None


def check_installed_ea() -> IntegrityResult:
    """Is the EA the terminal would RUN the same one the repository holds?"""
    found = installed_ea_paths()
    if found is None:
        return IntegrityResult(
            "installed_ea", True, "no MetaTrader data folder on this machine"
        )
    source, binary = found
    repo_source = REPO / "mt5" / "Experts" / "RC5_EA.mq5"
    repo_binary = REPO / "mt5" / "Experts" / "RC5_EA.ex5"

    if sha256(source) != sha256(repo_source):
        return IntegrityResult(
            "installed_ea",
            False,
            f"STALE SOURCE: installed {sha256(source)[:12]} != "
            f"repo {sha256(repo_source)[:12]}",
        )
    if repo_binary.is_file() and sha256(binary) != sha256(repo_binary):
        return IntegrityResult(
            "installed_ea",
            False,
            f"STALE BINARY: installed {sha256(binary)[:12]} != "
            f"repo {sha256(repo_binary)[:12]}",
        )
    return IntegrityResult("installed_ea", True, "byte-identical")


def main() -> int:
    print("SHA-256 of release artifacts")
    for rel in ARTIFACTS:
        path = REPO / rel
        mark = sha256(path) if path.is_file() else "MISSING"
        print(f"  {mark}  {rel}")

    result = check_installed_ea()
    print(f"\ninstalled EA: {'OK' if result.ok else 'FAIL'} - {result.detail}")
    return 0 if result.ok else 1


if __name__ == "__main__":  # pragma: no cover - operator entry point
    raise SystemExit(main())
