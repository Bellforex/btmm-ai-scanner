"""RC4 Pine builds: source-level contract (USER + PARITY).

The RC4 builds are generated from the frozen RC3 builds, which stay byte-for-byte
untouched. These checks pin what the RC4 port must carry: the author-decided
framework constants, the unchanged P6 transport (no new request.security), the
capture streams the aligned parity comparison reads, and LF line endings.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2] / "tradingview"
USER = ROOT / "btmm_poi_btrc_scanner_rc4_user.pine"
PARITY = ROOT / "btmm_poi_btrc_scanner_rc4_parity.pine"


def _live(path: Path) -> str:
    return "\n".join(
        line
        for line in path.read_text(encoding="utf-8").splitlines()
        if not line.lstrip().startswith("//")
    )


@pytest.mark.parametrize("path", [USER, PARITY])
def test_lf_only(path: Path) -> None:
    assert b"\r\n" not in path.read_bytes()


@pytest.mark.parametrize("path", [USER, PARITY])
def test_framework_constants(path: Path) -> None:
    src = _live(path)
    # BTMM = score, not gate: 85 action / 55 setup only / 25 none
    assert "btmmScore := fwPre ? 85 : btmmValid ? 55 : 25" in src
    assert "btmmValid := fwPre" in src
    assert "liquidityScore := fwLoc" in src
    # location: Fibonacci bands of the origin impulse, range thirds, sweep bonus
    assert "loc := ret < 50 ? 40 : ret < 61.8 ? 65 : ret <= 79 ? 80 : 55" in src
    assert "loc := pos == 0 ? 35 : pos == -dir ? 75 : 20" in src
    assert "loc := math.min(100, loc + 15)" in src
    # interaction episode = BTMM reaction window (5 bars); reclaim window 3 bars
    assert "int eI = sI + 4" in src
    assert "j - pen >= 3" in src
    assert "fwNow - l.x >= 3" in src
    # DELAY: >= 2 inside closes or >= 1 re-entry
    assert "run >= 2" in src and "reent >= 1" in src
    # RANGE rule: >= 3 CHOCH in the last 4 transitions
    assert "for q = k - 3 to k" in src and "ch >= 3" in src
    # framework applies to the 18 canonical types only
    assert "array.get(poiType, i) <= C_POI_CORE_TYPE_MAX" in src
    # episode-aware terminal predicate and INVALIDATED on true failure
    assert "C_POI_TERM_MITIGATED and fwEp == 1" in src
    assert "fwEp == 3 ? C_POI_TERM_INVALIDATED" in src


@pytest.mark.parametrize(
    ("path", "rc3"),
    [
        (USER, ROOT / "btmm_poi_btrc_scanner_rc3_poi_semantics_dev.pine"),
        (PARITY, ROOT / "btmm_poi_btrc_scanner_rc3_parity_dev.pine"),
    ],
)
def test_p6_transport_unchanged(path: Path, rc3: Path) -> None:
    """No new request.security: the framework runs on the host timeframe only."""

    def count(p: Path) -> int:
        return len(re.findall(r"request\.security\(", _live(p)))

    assert count(path) == count(rc3)


def test_parity_keeps_capture_streams() -> None:
    src = _live(PARITY)
    for stream in ('"RUNMETA|', '"P5C|', '"P8EVENT|type=', '"P8PRIME|', '"P3LIFE|'):
        assert stream in src, stream


def test_user_has_visibility_controls() -> None:
    src = _live(USER)
    for title in (
        "Show Market Structure",
        "Show Trendlines",
        "Show Consolidation / Range",
        "Show Liquidity",
        "Show BTMM Cycle",
        "Show Dashboard",
        "Show POI Table",
    ):
        assert title in src, title
    # all 18 POI types keep an individual display switch
    assert len(re.findall(r"(?m)^t\w+ = input\.bool\(true, ", src)) == 18
