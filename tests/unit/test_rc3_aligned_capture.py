"""Locks for the RC3 aligned Level-A tooling: window alignment is proven, not
assumed; the sealed range is refused; the comparator finds the first
divergence instead of passing silently."""

from __future__ import annotations

import gzip
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from tests.parity_support.rc3_aligned_capture import (
    AlignmentError,
    load_aligned_window,
    parse_runmeta,
)
from tests.parity_support.rc3_aligned_compare import compare
from tests.parity_support.rc3_daily_authority import SealedRangeViolationError

_STEPS = {
    "w1": timedelta(days=7),
    "d1": timedelta(days=1),
    "h4": timedelta(hours=4),
    "h1": timedelta(hours=1),
    "m15": timedelta(minutes=15),
    "m5": timedelta(minutes=5),
}
_PERIOD = {"w1": "1W", "d1": "1D", "h4": "240", "h1": "60", "m15": "15", "m5": "5"}


def _ms(dt: datetime) -> int:
    return int(dt.timestamp() * 1000)


def _write_exports(
    tmp: Path, host_start: datetime, n: int = 6
) -> dict[str, tuple[int, int, int, float]]:
    meta: dict[str, tuple[int, int, int, float]] = {}
    for stem, step in _STEPS.items():
        start = host_start - step * n if stem != "m15" else host_start
        lines = []
        checksum = 0.0
        for i in range(n):
            t = start + step * i
            o, h, lo, c = 100.0 + i, 101.5 + i, 99.25 + i, 100.75 + i
            checksum += o + h + lo + c
            lines.append(
                f'2026-01-01,"OHLC|tf={_PERIOD[stem]}|t={_ms(t)}|tc={_ms(t + step)}'
                f'|o={o}|h={h}|l={lo}|c={c}|v=10"'
            )
        (tmp / f"ohlc_{stem}.csv").write_text(
            "Date,Message\n" + "\n".join(lines), encoding="utf-8"
        )
        meta[stem] = (_ms(start), _ms(start + step * (n - 1)), n, checksum)
    return meta


def _write_capture(
    tmp: Path,
    meta: dict[str, tuple[int, int, int, float]],
    *,
    count_override: int | None = None,
) -> Path:
    def _fmt(key: str) -> str:
        first, last, n, ck = meta[key]
        if count_override is not None and key == "h4":
            n = count_override
        return f"{first},{last},{n},{ck:.8f}"

    line = (
        "RUNMETA|feed=FX:XAUUSD|tf=15|host="
        + _fmt("m15")
        + "".join(
            f"|{k.upper()}={_fmt(k)}" for k in ("w1", "d1", "h4", "h1", "m15", "m5")
        )
    )
    path = tmp / "capture.csv"
    path.write_text(f'Date,Message\n2026-01-01,"{line}"\n', encoding="utf-8")
    return path


def test_runmeta_parses_every_window(tmp_path: Path) -> None:
    meta = _write_exports(tmp_path, datetime(2026, 8, 20, 10, tzinfo=UTC))
    run = parse_runmeta(_write_capture(tmp_path, meta))
    assert run.feed == "FX:XAUUSD"
    assert run.host_period == "15"
    assert set(run.contexts) == {"W1", "D1", "H4", "H1", "M15", "M5"}
    assert run.contexts["H4"].count == 6


def test_aligned_window_selects_exactly_the_run_bars(tmp_path: Path) -> None:
    meta = _write_exports(tmp_path, datetime(2026, 8, 20, 10, tzinfo=UTC))
    window = load_aligned_window(_write_capture(tmp_path, meta), tmp_path)
    assert len(window.host_series) == 6
    # The same-timeframe request is the host itself, never a second context.
    assert {tf.value for tf in window.context_series} == {"W1", "D1", "H4", "H1", "M5"}


def test_a_count_disagreement_is_refused(tmp_path: Path) -> None:
    meta = _write_exports(tmp_path, datetime(2026, 8, 20, 10, tzinfo=UTC))
    with pytest.raises(AlignmentError):
        load_aligned_window(_write_capture(tmp_path, meta, count_override=5), tmp_path)


def test_a_checksum_disagreement_is_refused(tmp_path: Path) -> None:
    meta = _write_exports(tmp_path, datetime(2026, 8, 20, 10, tzinfo=UTC))
    first, last, n, ck = meta["h1"]
    meta["h1"] = (first, last, n, ck + 0.01)
    with pytest.raises(AlignmentError):
        load_aligned_window(_write_capture(tmp_path, meta), tmp_path)


def test_a_host_window_inside_the_sealed_range_is_refused(tmp_path: Path) -> None:
    meta = _write_exports(tmp_path, datetime(2026, 7, 20, 10, tzinfo=UTC))
    with pytest.raises(SealedRangeViolationError):
        load_aligned_window(_write_capture(tmp_path, meta), tmp_path)


# --------------------------------------------------------------------------
# comparator
# --------------------------------------------------------------------------

_BAR = 1787200000000
_SRC = "2026-08-19T20:00:00+00:00"
_AVAIL = "2026-08-19T20:30:00+00:00"


def _authority(
    tmp: Path, *, permission: str = "WATCH_ONLY", perm_code: int = 4
) -> Path:
    d = tmp / "authority"
    d.mkdir()
    rid = "00000000-0000-7000-8000-000000000001"
    p3 = {
        "bar_ms": str(_BAR),
        "poi_record_id": rid,
        "poi_type": "BUY_ORDER_BLOCK",
        "direction": "BULLISH",
        "source_timeframe": "M15",
        "effective_timeframe": "M15",
        "zone_top": "101.5",
        "zone_bottom": "99.25",
        "strength_tier": "STANDARD",
        "source_time_utc": _SRC,
        "availability_time_utc": _AVAIL,
        "terminal": "0",
        "terminal_reason": "",
        "terminal_time_utc": "",
    }
    p5 = {
        "bar_ms": str(_BAR),
        "poi_record_id": rid,
        "poi_lifecycle_status": "NO_BREACH",
        "btmm_valid": "0",
        "trend_alignment": "PARTIAL",
        "score_btmm": "25",
        "score_poi": "50",
        "score_trend": "20",
        "score_regime": "50",
        "score_momentum": "26",
        "score_breakout": "50",
        "score_liquidity": "40",
        "score_volatility": "20",
        "final_confluence_score": "35",
        "analytical_permission": permission,
        "signal_lifecycle_state": "STRUCTURALLY_VALIDATED",
    }
    p8 = {
        "bar_ms": str(_BAR),
        "sequence_in_bar": "0",
        "event_type": "POI_ACTIVATED",
        "poi_record_id": rid,
        "poi_bullish": "1",
        "btmm_valid": "0",
        "permission": str(perm_code),
        "lifecycle": "1",
        "terminal_reason": "",
    }
    for name, row in (
        ("p3_registry_rows", p3),
        ("p5_assessment_rows", p5),
        ("p8_event_rows", p8),
    ):
        with gzip.open(d / f"{name}.ndjson.gz", "wt", encoding="utf-8") as h:
            h.write(json.dumps(row) + "\n")
    (d / "daily_authority_manifest.json").write_text(
        json.dumps({"days": [{"last_bar_ms": _BAR, "bars_processed": 1}]}),
        encoding="utf-8",
    )
    return d


def _pine_capture(tmp: Path) -> Path:
    src = int(datetime.fromisoformat(_SRC).timestamp() * 1000)
    avail = int(datetime.fromisoformat(_AVAIL).timestamp() * 1000)
    lines = [
        f'"P3LIFE|poiIdx=0|type=1|dir=1|tier=1|top=101.5|bottom=99.25|srcTime={src}|availTime={avail}'
        '|status=1|walkTerminal=false|taps=0|firstTouch=0|invalTime=0|termReason=0|termTime=0|freshActive=true"',
        f'"P8EVENT|type=POI_ACTIVATED|bar={_BAR}|poiIdx=0|poiDir=BULL|poiTier=1|btmmValid=false|permission=4|lifecycle=1"',
        f'"P5C|bar={_BAR}|k=0|n=1|hdr=0|end=1|rows=0,1,1,1,0,0,0,1,25,50,20,50,26,50,40,20,35,4,1"',
    ]
    path = tmp / "pine.csv"
    path.write_text(
        "Date,Message\n" + "\n".join(f"2026-01-01,{x}" for x in lines), encoding="utf-8"
    )
    return path


def test_identical_level_a_and_level_b_report_zero_mismatches(tmp_path: Path) -> None:
    report = compare(_pine_capture(tmp_path), _authority(tmp_path))
    assert report.first_divergence is None
    assert report.p3 == {
        "python_only": 0,
        "pine_only": 0,
        "field_mismatches": 0,
        "matched": 1,
    }
    assert report.p5["rows_compared"] == 1 and report.p5["field_mismatches"] == 0
    assert report.p8["missing_in_python"] == 0 and report.p8["extra_in_python"] == 0


def test_a_single_field_difference_is_reported_as_the_first_divergence(
    tmp_path: Path,
) -> None:
    report = compare(
        _pine_capture(tmp_path),
        _authority(tmp_path, permission="NO_TRADE_CONTEXT", perm_code=5),
    )
    first = report.first_divergence
    assert first is not None
    assert first["bar_ms"] == _BAR
    assert first["stage"] == "P5"
    assert first["field"] == "permission"
    assert (first["python"], first["pine"]) == (5, 4)


def test_capture_instrumentation_is_parity_only_and_defaults_off() -> None:
    repo = Path(__file__).resolve().parents[2]
    parity = (
        repo / "tradingview" / "btmm_poi_btrc_scanner_rc3_parity_dev.pine"
    ).read_text(encoding="utf-8")
    user = (
        repo / "tradingview" / "btmm_poi_btrc_scanner_rc3_poi_semantics_dev.pine"
    ).read_text(encoding="utf-8")
    assert 'capRunMeta   = input.bool(false, "RUNMETA' in parity
    assert 'capP5Compact = input.bool(false, "P5C' in parity
    # Log-only: every P5C / RUNMETA emission is a log.info call.
    for marker in ('"P5C|', '"RUNMETA|'):
        for line in parity.splitlines():
            if marker in line:
                assert "log.info(" in line, line
    assert "capRunMeta" not in user and "capP5Compact" not in user
