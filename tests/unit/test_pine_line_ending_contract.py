"""Every Pine file's line endings must be declared, not left to the checkout.

WHY THIS MATTERS MORE THAN IT LOOKS
-----------------------------------
Pine sources are compared byte-for-byte: against the script saved on
TradingView, and against sha256 values recorded in closure evidence. Line
endings are invisible in every editor and every text-mode diff, and
`core.autocrlf` decides them per machine -- so a file can change its hash
without changing a single visible character, and no text-based test will see it.

Two live examples in this repository:

* Editing `btmm_poi_btrc_scanner_p6_dev.pine` with Python's `write_text` on
  Windows silently rewrote it to CRLF. Every existing test still passed, because
  `read_text` uses universal newlines -- but the deployment hash had moved.
* `btmm_poi_btrc_scanner_v1.pine` and `..._p2_parity_probe.pine` are stored in
  git as LF, yet their recorded P2 closure hashes (`3d6d10df...`, `17e6d56b...`)
  were computed over CRLF bytes. Those hashes therefore only matched on a
  machine with `autocrlf=true`; on a fresh Linux clone the P2 tests would have
  failed for a reason no one would have looked for.

So `.gitattributes` now states the ending for every Pine file, and this module
requires the bytes on disk to agree with what was stated. It deliberately does
NOT prefer LF everywhere: the two legacy files are pinned to CRLF because that
is what their closure evidence was derived from, and re-deriving closed evidence
to satisfy a tidiness preference would be the worse trade.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
PINE = REPO / "tradingview"

#: Files whose recorded closure hashes were computed over CRLF bytes.
CRLF_PINNED = {
    "btmm_poi_btrc_scanner_v1.pine",
    "btmm_poi_btrc_scanner_p2_parity_probe.pine",
}


def _declared_eol(path: Path) -> str:
    """What .gitattributes says this file's working-tree ending must be."""
    result = subprocess.run(
        ["git", "check-attr", "eol", "--", str(path.relative_to(REPO))],
        capture_output=True,
        text=True,
        cwd=REPO,
        check=True,
    )
    return result.stdout.strip().rsplit(":", 1)[-1].strip()


def _pine_files() -> list[Path]:
    files = sorted(PINE.glob("*.pine"))
    assert files, "no Pine sources found"
    return files


def test_every_pine_file_declares_its_line_ending() -> None:
    """`unspecified` means the checkout decides, which is the whole problem."""
    undeclared = [p.name for p in _pine_files() if _declared_eol(p) == "unspecified"]
    assert undeclared == [], f"line endings left to the checkout: {undeclared}"


def test_the_bytes_on_disk_match_what_was_declared() -> None:
    mismatched = []
    for path in _pine_files():
        raw = path.read_bytes()
        actual = "crlf" if b"\r\n" in raw else "lf"
        declared = _declared_eol(path)
        if actual != declared:
            mismatched.append(f"{path.name}: declared {declared}, on disk {actual}")
    assert mismatched == [], mismatched


def test_the_active_scanner_sources_are_lf() -> None:
    """The files this campaign deploys. Stated separately from the generic rule
    so that a future edit to .gitattributes cannot quietly flip them."""
    for name in (
        "btmm_poi_btrc_scanner_p4_dev.pine",
        "btmm_poi_btrc_scanner_p6_dev.pine",
    ):
        assert b"\r\n" not in (PINE / name).read_bytes(), name
        assert _declared_eol(PINE / name) == "lf", name


def test_the_crlf_pinned_files_are_exactly_the_known_legacy_ones() -> None:
    """A new file arriving as CRLF is a mistake, not a convention. Only the two
    files carrying CRLF-derived P2 closure hashes may be pinned that way."""
    pinned = {p.name for p in _pine_files() if _declared_eol(p) == "crlf"}
    assert pinned == CRLF_PINNED, pinned


def test_the_recorded_p2_hashes_still_match_their_files() -> None:
    """The reason the pin exists. If this fails, either the pin was removed or
    the files were normalised -- and the P2 closure evidence no longer holds."""
    import hashlib

    for name, recorded in (
        (
            "btmm_poi_btrc_scanner_v1.pine",
            "3d6d10df27e4150e6b693cb55bd32bb269478235eabfdf2fecd9aa23d96fa05b",
        ),
        (
            "btmm_poi_btrc_scanner_p2_parity_probe.pine",
            "17e6d56b5b31c5a8fa4fff4cd4f2f1caff22cbdfdd20917313e2c60c0608b749",
        ),
    ):
        actual = hashlib.sha256((PINE / name).read_bytes()).hexdigest()
        assert actual == recorded, f"{name}: {actual} != recorded {recorded}"
