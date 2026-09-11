"""RC3 must not disturb the frozen Pine blocks it does not own.

Phase 31 asked whether P6 transport changed. Arguing "no file under it was
edited" is weaker than measuring, so this hashes the block itself out of both
sources and compares. It also asserts the two frozen release artifacts are
byte-identical to their published hashes, which is the campaign's hard stop.

These are cheap file-level checks by design. They cannot prove runtime
equivalence, and they are not offered as parity evidence.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

_TV = Path(__file__).resolve().parents[2] / "tradingview"
RC1 = _TV / "btmm_poi_btrc_scanner_rc1.pine"
RC2 = _TV / "btmm_poi_btrc_scanner_rc2.pine"
RC3_DEV = _TV / "btmm_poi_btrc_scanner_rc3_poi_semantics_dev.pine"

RC1_SHA = "143c0f8817c78bf45e6842e16112cedf67ca36dc694c288808b7748096664c54"
RC2_SHA = "381f2fc2463c4eaa9dc2eb88943f5bc16a83b55a6d4307c390cce5f87f36cc3f"

_P6_START = "P6 — CROSS-TIMEFRAME SUBSTRATE"
_P6_END = "P5 TRANSPORT EXTENSION"

#: Symbols RC3 introduced or repurposed. None may appear inside the P6 block.
_RC3_SYMBOLS = (
    "poiFirstTouchT",
    "poiInvalT",
    "poiTermReason",
    "poiTermTime",
    "poiFreshActive",
    "C_POI_TERM_",
    "f_p8TermReasonLabel",
    "f_p7zTfLabel",
    "p7zComp",
    "p7zOwner",
    "p7zGLeft",
    "p7zProjectBars",
    "p7zRightEdge",
    "poiCandTime",
)

#: P3 registry arrays. P6 projects P1 measurements, so it should read none of
#: them — which is what makes the data-path argument checkable rather than
#: merely plausible.
_P3_ARRAYS = (
    "poiType",
    "poiZoneTop",
    "poiZoneBottom",
    "poiAvailTime",
    "poiTerminal",
    "poiDirection",
    "poiStatus",
    "poiTier",
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _p6_block(path: Path) -> str:
    lines = path.read_text(encoding="utf-8").split("\n")
    start = next(i for i, line in enumerate(lines) if _P6_START in line)
    end = next(i for i in range(start + 1, len(lines)) if _P6_END in lines[i])
    return "\n".join(lines[start:end])


# ---- the frozen releases ----------------------------------------------------


def test_rc1_is_byte_identical_to_its_published_hash() -> None:
    assert _sha256(RC1) == RC1_SHA


def test_rc2_is_byte_identical_to_its_published_hash() -> None:
    assert _sha256(RC2) == RC2_SHA


# ---- P6 transport -----------------------------------------------------------


def test_the_p6_block_is_byte_identical_between_rc2_and_rc3_dev() -> None:
    rc2_block, rc3_block = _p6_block(RC2), _p6_block(RC3_DEV)
    assert rc2_block.count("\n") == rc3_block.count("\n")
    assert hashlib.sha256(rc2_block.encode()).hexdigest() == (
        hashlib.sha256(rc3_block.encode()).hexdigest()
    )


@pytest.mark.parametrize("symbol", _RC3_SYMBOLS)
def test_no_rc3_symbol_reaches_the_p6_block(symbol: str) -> None:
    assert symbol not in _p6_block(RC3_DEV)


@pytest.mark.parametrize("array_name", _P3_ARRAYS)
def test_p6_reads_no_p3_registry_array(array_name: str) -> None:
    """There is no data path from the POI registry into cross-timeframe transport."""
    assert array_name not in _p6_block(RC3_DEV)


# ---- the release-blocking presentation invariants ---------------------------


def test_the_timeframe_formatter_handles_the_calendar_spellings() -> None:
    """`1D` is what a daily chart actually reports, and it used to render TF?."""
    source = RC3_DEV.read_text(encoding="utf-8")
    start = source.index("f_p7zTfLabel(string p) =>")
    end = source.index("\n\n", start)
    body = source[start:end]
    assert 'str.substring(p, n - 1)' in body, "needs a suffix branch"
    assert '"D" ?' in body or 'sfx == "D"' in body


def test_the_annotation_collision_resolver_is_present() -> None:
    source = RC3_DEV.read_text(encoding="utf-8")
    assert "ANNOTATION COLLISION RESOLUTION" in source
    assert "p7zOwner" in source


def test_the_drawn_origin_uses_the_source_candle_not_availability() -> None:
    source = RC3_DEV.read_text(encoding="utf-8")
    assert "array.push(p7zGLeft, cd)" in source
    assert "array.push(p7zGLeft, lf)" not in source
