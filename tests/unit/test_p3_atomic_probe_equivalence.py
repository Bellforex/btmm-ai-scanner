"""The P3 atomic probe must stay semantically identical to P3 DEV.

The probe exists to measure P3 DEV, so any drift between them would silently
invalidate a real-data parity result: the hashes would describe a script that
is not the one under test. These tests fail if the detector, lifecycle or
downstream logic of either file changes without the other.

Two authorised deviations, and only two:

1. the ``indicator()`` title, and
2. an APPENDED instrumentation block that only reads the registry.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

_TV = Path(__file__).resolve().parents[2] / "tradingview"
_DEV = _TV / "btmm_poi_btrc_scanner_p3_dev.pine"
_PROBE = _TV / "btmm_poi_btrc_scanner_p3_atomic_parity_bundle.pine"

_MARKER = "// P3 ATOMIC PARITY INSTRUMENTATION"

#: Registry arrays the ENGINE owns. The probe may read them; writing to one
#: would make the probe a second implementation instead of a measurement.
_REGISTRY_ARRAYS = (
    "poiType",
    "poiDirection",
    "poiZoneTop",
    "poiZoneBottom",
    "poiCandTime",
    "poiConfirmTime",
    "poiAvailTime",
    "poiTier",
    "poiSrcFirst",
    "poiSrcCount",
    "poiSrcLast",
    "poiStatus",
    "poiTerminal",
    "poiResumeIdx",
    "poiBreachIdx",
    "poiReclaimIdx",
    "poiWindowSeen",
    "poiSustained",
    "poiLastWinBreach",
    "poiTapCount",
    "poiInTap",
    "poiReported",
    "poiCommTransCount",
    "poiCommLastCode",
    "poiCommLastEvent",
    "poiCommLastAvail",
    "poiCommRelevant",
    "poiRepTransCount",
    "poiRepLastCode",
    "poiRepLastEvent",
    "poiRepLastAvail",
    "poiRepRelevant",
)


def _dev_text() -> str:
    return _DEV.read_text(encoding="utf-8").replace("\r\n", "\n")


def _probe_text() -> str:
    return _PROBE.read_text(encoding="utf-8").replace("\r\n", "\n")


def _split_probe() -> tuple[str, str]:
    """Return (prefix, instrumentation) around the appendix marker."""
    text = _probe_text()
    index = text.find(_MARKER)
    assert index != -1, "instrumentation marker not found in the probe"
    banner = text.rfind("\n// =", 0, index)
    return text[:banner], text[banner:]


def test_both_pine_files_exist() -> None:
    assert _DEV.is_file()
    assert _PROBE.is_file()


def test_probe_prefix_is_p3_dev_apart_from_the_title() -> None:
    """The measured engine and the deployed engine are the same source."""
    prefix, _ = _split_probe()
    dev_lines = _dev_text().rstrip("\n").splitlines()
    pre_lines = prefix.rstrip("\n").splitlines()

    assert len(pre_lines) == len(dev_lines), (
        f"probe prefix has {len(pre_lines)} lines, P3 DEV has {len(dev_lines)}: "
        "the instrumentation must be APPENDED, never interleaved"
    )
    differing = [i for i in range(len(dev_lines)) if dev_lines[i] != pre_lines[i]]
    assert len(differing) == 1, (
        "exactly one line may differ (the indicator title); differing lines: "
        f"{[(i + 1, dev_lines[i], pre_lines[i]) for i in differing]}"
    )
    line = differing[0]
    assert dev_lines[line].startswith("indicator(")
    assert "[P3 DEV]" in dev_lines[line]
    assert "[P3 ATOMIC PARITY]" in pre_lines[line]
    assert dev_lines[line].replace("[P3 DEV]", "[P3 ATOMIC PARITY]") == pre_lines[line]


def test_titles_are_distinct_so_both_can_be_saved_separately() -> None:
    assert '"BTMM + POI + BTRC Scanner [P3 DEV]"' in _dev_text()
    assert '"BTMM + POI + BTRC Scanner [P3 ATOMIC PARITY]"' in _probe_text()
    assert "[P3 DEV]" not in _probe_text()


def test_instrumentation_never_writes_to_a_registry_array() -> None:
    """The probe measures; it must not mutate what it measures."""
    _, appendix = _split_probe()
    offenders: list[str] = []
    for number, line in enumerate(appendix.splitlines(), 1):
        code = line.split("//", 1)[0]
        for name in _REGISTRY_ARRAYS:
            if re.search(
                rf"array\.(set|push|insert|remove|clear|pop|unshift|fill|sort|reverse)"
                rf"\s*\(\s*{name}\b",
                code,
            ):
                offenders.append(f"line {number}: {line.strip()[:90]}")
    assert not offenders, "instrumentation mutates engine state:\n" + "\n".join(
        offenders
    )


def test_instrumentation_defines_no_detector_or_lifecycle_function() -> None:
    """Every function the appendix defines must be probe-local (`f_p3b`/`f_p3p`)."""
    _, appendix = _split_probe()
    defined = re.findall(r"^(f_\w+)\s*\(", appendix, flags=re.M)
    assert defined, "expected the appendix to define its own helpers"
    stray = [name for name in defined if not name.startswith(("f_p3b", "f_p3p"))]
    assert not stray, f"appendix defines non-probe functions: {stray}"


def test_instrumentation_only_appends_never_reopens_engine_state() -> None:
    """No `var` in the appendix may shadow an engine registry array."""
    _, appendix = _split_probe()
    declared = re.findall(r"^var\s+(?:array<\w+>|\w+)\s+(\w+)", appendix, flags=re.M)
    clashes = sorted(set(declared) & set(_REGISTRY_ARRAYS))
    assert not clashes, f"appendix re-declares engine arrays: {clashes}"
    for name in declared:
        assert name.startswith("p3b"), f"appendix state must be probe-local: {name}"


def test_probe_reuses_the_frozen_dual_hash_constants() -> None:
    """The probe must not invent a second digest contract."""
    import importlib.util
    import sys

    support = Path(__file__).resolve().parents[1] / "parity_support" / "p3_digest.py"
    spec = importlib.util.spec_from_file_location("_p3_digest_probe_check", support)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)

    _, appendix = _split_probe()
    for name, value in (
        ("P3P_MOD1", module.MOD1),
        ("P3P_MOD2", module.MOD2),
        ("P3P_BASE1", module.BASE1),
        ("P3P_BASE2", module.BASE2),
    ):
        match = re.search(rf"^int\s+{name}\s*=\s*(\d+)", appendix, flags=re.M)
        assert match, f"{name} not declared in the appendix"
        assert int(match.group(1)) == value, (
            f"{name} is {match.group(1)} but the frozen contract says {value}"
        )


def test_probe_emits_every_family_and_lifecycle_hash_the_contract_defines() -> None:
    """A missing family hash would hide a detector mismatch behind the total."""
    import importlib.util
    import sys

    support = Path(__file__).resolve().parents[1] / "parity_support" / "p3_digest.py"
    spec = importlib.util.spec_from_file_location("_p3_digest_probe_fields", support)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)

    _, appendix = _split_probe()
    for family in module.FAMILIES:
        assert f"|fam_{family}=" in appendix, f"probe never emits fam_{family}"
    for field in module.LIFECYCLE_FIELDS:
        assert f"|lc_{field}=" in appendix, f"probe never emits lc_{field}"
    for key in ("ovh1", "ovh2", "ctxh1", "ctxh2", "nregistry", "nactive", "nterminal"):
        assert f"|{key}=" in appendix, f"probe never emits {key}"


def test_probe_hashes_the_reported_lifecycle_projection() -> None:
    """Parity is against the oracle's whole-series result, i.e. the REPORTED
    projection, not the committed cursor (which deliberately lags)."""
    _, appendix = _split_probe()
    for name in (
        "poiReported",
        "poiRepTransCount",
        "poiRepRelevant",
        "poiRepLastCode",
        "poiRepLastEvent",
        "poiRepLastAvail",
    ):
        assert f"array.get({name}," in appendix, f"probe never reads {name}"
    for name in ("poiCommTransCount", "poiCommLastCode", "poiCommRelevant"):
        assert f"array.get({name}," not in appendix, (
            f"probe reads the COMMITTED array {name}; the digest is defined on "
            "the reported projection"
        )


@pytest.mark.parametrize(
    "forbidden", ["strategy.", "request.security", "alertcondition("]
)
def test_probe_adds_no_execution_or_multi_timeframe_surface(forbidden: str) -> None:
    for line in _probe_text().splitlines():
        code = line.split("//", 1)[0]
        assert forbidden not in code, f"probe introduces {forbidden}: {line.strip()}"


def test_probe_emits_exactly_one_meta_record() -> None:
    appendix = _split_probe()[1]
    assert appendix.count('log.info("P3BMETA|') == 1
    assert "barstate.islastconfirmedhistory" in appendix
    assert "p3bMetaDone" in appendix


def test_probe_records_only_confirmed_historical_bars() -> None:
    """A forming realtime bar must never enter the bundle."""
    appendix = _split_probe()[1]
    assert "barstate.isconfirmed and barstate.ishistory" in appendix
