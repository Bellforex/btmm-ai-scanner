"""The capture parser must refuse, not repair.

WHY THE NEGATIVE CASES ARE THE MODULE
--------------------------------------
The P6 capture is split across executions: one run emits the semantic snapshot,
six later runs each export one timeframe's raw candles. That split is what keeps
every run inside the log volume the feasibility probe demonstrated, and it opens
a failure mode that looks exactly like success — the 1250-bar window slides
forward as bars confirm, so a raw export taken minutes after the snapshot can
cover a DIFFERENT window and still be perfectly well-formed.

A parser that quietly tolerated a missing row, a duplicate ordinal, a mixed feed
or a short capture would let that through and the whole real-data proof would
rest on the wrong candles. So almost every test here asserts a REFUSAL.

The happy-path tests exist mainly to prove the refusals are not vacuous: a
parser that rejected everything would also pass a suite of rejection tests.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Any

import pytest

_REPO = Path(__file__).resolve().parents[2]


def _load(name: str, relpath: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, _REPO / relpath)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


LOG = _load("_p6_capture_log", "tests/parity_support/p6_atomic_capture_log.py")
DIG = _load("_p6_digest_parser", "tests/parity_support/p6_digest.py")

ANCHOR = 1_788_399_000_000
ANCHOR_CLOSE = ANCHOR + 900_000

_TF_ROWS = {
    "W1": (10080, 1250),
    "D1": (1440, 1250),
    "H4": (240, 1250),
    "H1": (60, 1250),
    "M15": (15, 1799),
    "M5": (5, 1250),
}


def _snap_line(timeframe: str, **overrides: Any) -> str:
    code, rows = _TF_ROWS[timeframe]
    values: dict[str, Any] = {
        "code": code,
        "rows": rows,
        "first": ANCHOR - rows * 900_000,
        "last": ANCHOR - 900_000,
        "ih1": 111_000 + code,
        "ih2": 222_000 + code,
        "swings": 60,
        "equal": 2,
        "disp": 1,
        "trans": 3,
        "dir": 1,
        "SW1": 1, "SW2": 2, "EQ1": 3, "EQ2": 4, "DS1": 5,
        "DS2": 6, "TR1": 7, "TR2": 8, "ST1": 9, "ST2": 10,
        "C1": 11, "C2": 12,
    }
    values.update(overrides)
    body = "|".join(f"{k}={v}" for k, v in values.items())
    return f"[2026-09-03T02:30:00.000+01:00]: P6SNAP|{timeframe}|{body}"


def _meta_line(**overrides: Any) -> str:
    values: dict[str, Any] = {
        "schema": 1,
        "provider": "FX",
        "ticker": "XAUUSD",
        "mintick": "0.01",
        "hostTf": "15",
        "anchorTime": ANCHOR,
        "anchorClose": ANCHOR_CLOSE,
        "hostDataset": 1800,
        "hostConfirmed": 1799,
        "semanticMin": 1250,
        "requestEnvelope": 1251,
        "hostEnvelope": 1800,
        "captureTf": "NONE",
        "aliasHits": 0,
    }
    values.update(overrides)
    body = "|".join(f"{k}={v}" for k, v in values.items())
    return f"[2026-09-03T02:30:00.000+01:00]: P6META|{body}"


def snapshot_text(*, drop: str | None = None, extra: list[str] | None = None) -> str:
    lines = [_meta_line()]
    for timeframe in LOG.REQUIRED_TIMEFRAMES:
        if timeframe == drop:
            continue
        lines.append(_snap_line(timeframe))
    lines += extra or []
    lines.append("[2026-09-03T02:30:00.000+01:00]: P6SNAP_END|schema=1|tfCount=6|provider=FX")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Snapshot: happy path, then every way it can be wrong
# ---------------------------------------------------------------------------


def test_a_well_formed_snapshot_parses() -> None:
    snap = LOG.parse_snapshot(snapshot_text())
    assert set(snap.timeframes) == set(LOG.REQUIRED_TIMEFRAMES)
    assert snap.meta.feed == "FX:XAUUSD"
    assert snap.meta.host_confirmed == 1799
    assert snap.timeframes["W1"].surfaces["SWINGS"] == (1, 2)
    assert snap.timeframes["M15"].semantic_rows == 1799
    assert len(snap.capture_id) == 32


def test_the_capture_id_depends_on_every_input_digest() -> None:
    """It names the snapshot for the record; two different captures must not
    share a name."""
    base = LOG.parse_snapshot(snapshot_text()).capture_id
    lines = snapshot_text().replace("ih1=121080", "ih1=999999")
    assert LOG.parse_snapshot(lines).capture_id != base


@pytest.mark.parametrize("timeframe", list(LOG.REQUIRED_TIMEFRAMES))
def test_a_missing_timeframe_is_refused(timeframe: str) -> None:
    with pytest.raises(LOG.CaptureError, match="missing timeframes"):
        LOG.parse_snapshot(snapshot_text(drop=timeframe))


def test_an_identical_repeat_is_tolerated() -> None:
    """Pine re-executes the realtime bar on every tick and rolls back `var`
    state, so a once-guard cannot prevent a repeat emission. An identical repeat
    is the same observation and must not fail the capture."""
    snap = LOG.parse_snapshot(snapshot_text(extra=[_snap_line("W1")]))
    assert snap.timeframes["W1"].semantic_rows == 1250


def test_a_CONFLICTING_repeat_is_refused() -> None:
    """Two runs mixed in one buffer is the failure that matters."""
    with pytest.raises(LOG.CaptureError, match="two DIFFERENT W1 records"):
        LOG.parse_snapshot(snapshot_text(extra=[_snap_line("W1", swings=999)]))


def test_an_identical_repeated_meta_is_tolerated() -> None:
    snap = LOG.parse_snapshot(snapshot_text() + "\n" + _meta_line())
    assert snap.meta.host_confirmed == 1799


def test_a_conflicting_meta_is_refused_as_mixed_captures() -> None:
    text = snapshot_text() + "\n" + _meta_line(anchorTime=ANCHOR + 900_000)
    with pytest.raises(LOG.CaptureError, match="two DIFFERENT P6META"):
        LOG.parse_snapshot(text)


def test_a_truncated_snapshot_is_refused() -> None:
    text = "\n".join(snapshot_text().split("\n")[:-1])
    with pytest.raises(LOG.CaptureError, match="truncated"):
        LOG.parse_snapshot(text)


def test_a_snapshot_without_meta_is_refused() -> None:
    text = "\n".join(snapshot_text().split("\n")[1:])
    with pytest.raises(LOG.CaptureError, match="P6SNAP before P6META"):
        LOG.parse_snapshot(text)


@pytest.mark.parametrize(
    ("provider", "ticker"),
    [("OANDA", "XAUUSD"), ("FOREXCOM", "XAUUSD"), ("TVC", "GOLD"), ("FX", "EURUSD")],
)
def test_a_foreign_feed_is_refused(provider: str, ticker: str) -> None:
    """This campaign already lost a runtime matrix to a silent OANDA switch."""
    text = snapshot_text().replace(
        "provider=FX|ticker=XAUUSD", f"provider={provider}|ticker={ticker}"
    )
    with pytest.raises(LOG.CaptureError, match="wrong feed"):
        LOG.parse_snapshot(text)


def test_a_missing_surface_hash_is_refused() -> None:
    text = snapshot_text().replace("|TR2=8", "")
    with pytest.raises(LOG.CaptureError, match="missing field 'TR2'"):
        LOG.parse_snapshot(text)


def test_a_non_integer_hash_is_refused() -> None:
    text = snapshot_text().replace("C1=11", "C1=NaN")
    with pytest.raises(LOG.CaptureError, match="not an integer"):
        LOG.parse_snapshot(text)


def test_rows_below_the_semantic_minimum_are_refused() -> None:
    text = snapshot_text().replace(_snap_line("W1"), _snap_line("W1", rows=1249))
    with pytest.raises(LOG.CaptureError, match="below the semantic minimum"):
        LOG.parse_snapshot(text)


def test_a_forming_bar_leaking_past_the_anchor_is_refused() -> None:
    """The last confirmed source time cannot be after the host anchor close."""
    text = snapshot_text().replace(
        _snap_line("D1"), _snap_line("D1", last=ANCHOR_CLOSE + 1)
    )
    with pytest.raises(LOG.CaptureError, match="forming bar leaked"):
        LOG.parse_snapshot(text)


def test_reversed_first_and_last_are_refused() -> None:
    text = snapshot_text().replace(
        _snap_line("H4"), _snap_line("H4", first=ANCHOR, last=ANCHOR - 900_000)
    )
    with pytest.raises(LOG.CaptureError, match="first time is after last time"):
        LOG.parse_snapshot(text)


def test_an_unknown_direction_code_is_refused() -> None:
    text = snapshot_text().replace(_snap_line("M5"), _snap_line("M5", dir=7))
    with pytest.raises(LOG.CaptureError, match="unknown direction code"):
        LOG.parse_snapshot(text)


def test_a_negative_collection_count_is_refused() -> None:
    text = snapshot_text().replace(_snap_line("H1"), _snap_line("H1", swings=-1))
    with pytest.raises(LOG.CaptureError, match="negative collection count"):
        LOG.parse_snapshot(text)


def test_an_unknown_timeframe_is_refused() -> None:
    text = snapshot_text() + "\n" + _snap_line("W1").replace("P6SNAP|W1|", "P6SNAP|M30|")
    with pytest.raises(LOG.CaptureError, match="unknown timeframe"):
        LOG.parse_snapshot(text)


# ---------------------------------------------------------------------------
# Raw capture
# ---------------------------------------------------------------------------


def raw_bars(count: int = 5, *, start: int = 1_000_000_000_000) -> list[dict[str, int]]:
    return [
        {
            "ordinal": i,
            "time_ms": start + i * 900_000,
            "time_close_ms": start + (i + 1) * 900_000,
            "open_ticks": 400_000 + i,
            "high_ticks": 400_100 + i,
            "low_ticks": 399_900 + i,
            "close_ticks": 400_050 + i,
        }
        for i in range(count)
    ]


def raw_text(
    bars: list[dict[str, int]],
    *,
    timeframe: str = "W1",
    h1: int = 4242,
    h2: int = 8484,
    rows: int | None = None,
    provider: str = "FX",
    first: int | None = None,
    last: int | None = None,
    trailing: list[str] | None = None,
) -> str:
    lines = [
        "[t]: P6RAW|{tf}|{o}|{t0}|{t1}|{op}|{hi}|{lo}|{cl}".format(
            tf=timeframe,
            o=b["ordinal"],
            t0=b["time_ms"],
            t1=b["time_close_ms"],
            op=b["open_ticks"],
            hi=b["high_ticks"],
            lo=b["low_ticks"],
            cl=b["close_ticks"],
        )
        for b in bars
    ]
    lines += trailing or []
    lines.append(
        "[t]: P6RAW_SUMMARY|{tf}|rows={r}|kRows={r}|first={f}|last={l}|h1={h1}|h2={h2}"
        "|provider={p}|ticker=XAUUSD".format(
            tf=timeframe,
            r=len(bars) if rows is None else rows,
            f=bars[0]["time_ms"] if first is None else first,
            l=bars[-1]["time_ms"] if last is None else last,
            h1=h1,
            h2=h2,
            p=provider,
        )
    )
    return "\n".join(lines)


def test_a_well_formed_raw_capture_parses() -> None:
    raw = LOG.parse_raw(raw_text(raw_bars()))
    assert raw.timeframe == "W1"
    assert raw.rows == 5
    assert raw.bars[0]["ordinal"] == 0
    assert raw.provider == "FX"


def test_a_missing_ordinal_is_refused() -> None:
    bars = raw_bars(6)
    del bars[3]
    with pytest.raises(LOG.CaptureError, match=r"complete 0\.\.n-1 run"):
        LOG.parse_raw(raw_text(bars))


def test_a_duplicate_ordinal_is_refused() -> None:
    bars = raw_bars(5)
    bars.append(dict(bars[2]))
    with pytest.raises(LOG.CaptureError, match="duplicate ordinal"):
        LOG.parse_raw(raw_text(bars))


def test_a_wrong_declared_row_count_is_refused() -> None:
    with pytest.raises(LOG.CaptureError, match="declares 9 rows"):
        LOG.parse_raw(raw_text(raw_bars(), rows=9))


def test_non_monotonic_timestamps_are_refused() -> None:
    bars = raw_bars(5)
    bars[3]["time_ms"] = bars[2]["time_ms"]
    with pytest.raises(LOG.CaptureError, match="not strictly increasing"):
        LOG.parse_raw(raw_text(bars))


def test_a_close_time_before_open_is_refused() -> None:
    bars = raw_bars(5)
    bars[1]["time_close_ms"] = bars[1]["time_ms"] - 1
    with pytest.raises(LOG.CaptureError, match="close time is not after open"):
        LOG.parse_raw(raw_text(bars))


def test_high_below_low_is_refused() -> None:
    bars = raw_bars(5)
    bars[2]["high_ticks"] = bars[2]["low_ticks"] - 10
    with pytest.raises(LOG.CaptureError, match="high below low"):
        LOG.parse_raw(raw_text(bars))


@pytest.mark.parametrize("field", ["open_ticks", "close_ticks"])
def test_an_ohlc_value_outside_the_range_is_refused(field: str) -> None:
    bars = raw_bars(5)
    bars[2][field] = bars[2]["high_ticks"] + 5
    with pytest.raises(LOG.CaptureError, match=r"outside \[low, high\]"):
        LOG.parse_raw(raw_text(bars))


def test_mixed_timeframes_are_refused() -> None:
    bars = raw_bars(4)
    text = raw_text(bars)
    text = text.replace("P6RAW|W1|2|", "P6RAW|D1|2|", 1)
    with pytest.raises(LOG.CaptureError, match="mixes timeframes"):
        LOG.parse_raw(text)


def test_a_row_after_the_summary_is_refused() -> None:
    """Two concatenated captures would otherwise merge into one."""
    text = raw_text(raw_bars(4)) + "\n[t]: P6RAW|W1|9|1|2|3|4|5|6"
    with pytest.raises(LOG.CaptureError, match="not ordered"):
        LOG.parse_raw(text)


def test_a_capture_without_a_summary_is_refused() -> None:
    text = "\n".join(raw_text(raw_bars()).split("\n")[:-1])
    with pytest.raises(LOG.CaptureError, match="truncated"):
        LOG.parse_raw(text)


def test_a_foreign_feed_raw_capture_is_refused() -> None:
    with pytest.raises(LOG.CaptureError, match="wrong feed"):
        LOG.parse_raw(raw_text(raw_bars(), provider="OANDA"))


def test_a_summary_first_that_disagrees_with_row_zero_is_refused() -> None:
    with pytest.raises(LOG.CaptureError, match="does not match row 0"):
        LOG.parse_raw(raw_text(raw_bars(), first=12345))


def test_a_summary_last_that_disagrees_with_the_final_row_is_refused() -> None:
    with pytest.raises(LOG.CaptureError, match="does not match final row"):
        LOG.parse_raw(raw_text(raw_bars(), last=12345))


# ---------------------------------------------------------------------------
# The five-dimension lock
# ---------------------------------------------------------------------------


def _snapshot_tf(timeframe: str = "W1", **overrides: Any) -> Any:
    snap = LOG.parse_snapshot(snapshot_text()).timeframes[timeframe]
    if not overrides:
        return snap
    from dataclasses import replace

    return replace(snap, **overrides)


def _raw_for(snap: Any, bars: list[dict[str, int]]) -> Any:
    return LOG.parse_raw(
        raw_text(
            bars,
            timeframe=snap.timeframe,
            h1=snap.semantic_input_h1,
            h2=snap.semantic_input_h2,
        )
    )


def test_a_matching_capture_locks() -> None:
    bars = raw_bars(5)
    snap = _snapshot_tf(
        "W1",
        semantic_rows=5,
        semantic_first_time=bars[0]["time_ms"],
        semantic_last_time=bars[-1]["time_ms"],
    )
    result = LOG.raw_identity_matches(snap, _raw_for(snap, bars))
    assert result.matched is True
    assert result.describe().endswith("identity 5/5")


def test_a_window_shifted_forward_by_one_bar_fails_the_lock() -> None:
    """The failure mode sequential capture actually risks -- and note the row
    count is IDENTICAL, which is why row count alone is not the gate."""
    bars = raw_bars(6)
    snap = _snapshot_tf(
        "W1",
        semantic_rows=5,
        semantic_first_time=bars[0]["time_ms"],
        semantic_last_time=bars[4]["time_ms"],
    )
    shifted = [dict(b, ordinal=i) for i, b in enumerate(bars[1:])]
    result = LOG.raw_identity_matches(snap, _raw_for(snap, shifted))
    assert result.matched is False
    dims = {dim for dim, _, _ in result.mismatches}
    assert dims == {"semantic_first_time", "semantic_last_time"}
    assert snap.semantic_rows == len(shifted)  # counts agree; identity still fails


@pytest.mark.parametrize(
    "dimension",
    [
        "semantic_rows",
        "semantic_first_time",
        "semantic_last_time",
        "semantic_input_h1",
        "semantic_input_h2",
    ],
)
def test_each_dimension_alone_can_fail_the_lock(dimension: str) -> None:
    bars = raw_bars(5)
    snap = _snapshot_tf(
        "W1",
        semantic_rows=5,
        semantic_first_time=bars[0]["time_ms"],
        semantic_last_time=bars[-1]["time_ms"],
    )
    from dataclasses import replace

    broken = replace(snap, **{dimension: getattr(snap, dimension) + 1})
    result = LOG.raw_identity_matches(broken, _raw_for(snap, bars))
    assert result.matched is False
    assert [dim for dim, _, _ in result.mismatches] == [dimension]


def test_the_lock_refuses_to_compare_different_timeframes() -> None:
    bars = raw_bars(5)
    snap = _snapshot_tf("W1")
    raw = LOG.parse_raw(raw_text(bars, timeframe="D1"))
    with pytest.raises(LOG.CaptureError, match="cannot lock"):
        LOG.raw_identity_matches(snap, raw)


def test_a_failed_lock_names_the_dimensions() -> None:
    """Never a bare boolean: a mismatch must be diagnosable from the message."""
    bars = raw_bars(5)
    snap = _snapshot_tf("W1", semantic_rows=99)
    result = LOG.raw_identity_matches(snap, _raw_for(snap, bars))
    assert "semantic_rows" in result.describe()
    assert "snapshot=99" in result.describe()


# ---------------------------------------------------------------------------
# The raw rows must reproduce the digest the snapshot published
# ---------------------------------------------------------------------------


def test_parsed_raw_rows_feed_the_python_input_digest() -> None:
    """End to end: parsed tick integers -> the same canonical digest Pine folds.

    The parser stores ticks, so the digest is taken over the tick integers
    directly rather than re-deriving prices, which is what keeps the two sides
    free of a float round-trip.
    """
    bars = raw_bars(5)
    raw = LOG.parse_raw(raw_text(bars))
    records = [
        (
            DIG.encode_int(b["time_ms"]),
            DIG.encode_int(b["open_ticks"]),
            DIG.encode_int(b["high_ticks"]),
            DIG.encode_int(b["low_ticks"]),
            DIG.encode_int(b["close_ticks"]),
            DIG.encode_int(b["time_close_ms"]),
        )
        for b in raw.bars
    ]
    h1 = DIG.hash_sequence(records, DIG.BASE1, DIG.MOD1)
    h2 = DIG.hash_sequence(records, DIG.BASE2, DIG.MOD2)
    assert 0 <= h1 < DIG.MOD1
    assert 0 <= h2 < DIG.MOD2
    # dropping the first row must move it -- the sliding-window case
    assert DIG.hash_sequence(records[1:], DIG.BASE1, DIG.MOD1) != h1


@pytest.mark.parametrize("host_confirmed", [1250, 1400, 1799, 1800, 2400])
def test_m15_row_count_is_whatever_the_host_confirmed(host_confirmed: int) -> None:
    """Phase 10. The M15 dependency follows the measured host count; the parser
    must not have 1799 -- or any other observed value -- baked into it."""
    text = snapshot_text().replace(
        _snap_line("M15"),
        _snap_line("M15", rows=host_confirmed),
    ).replace("hostConfirmed=1799", f"hostConfirmed={host_confirmed}")
    snap = LOG.parse_snapshot(text)
    assert snap.timeframes["M15"].semantic_rows == host_confirmed
    assert snap.meta.host_confirmed == host_confirmed


def test_the_parser_hardcodes_no_observed_row_count() -> None:
    """Checked against executable code: the module docstring legitimately
    discusses the 1250-bar window when explaining why the lock exists."""
    import ast

    source = (_REPO / "tests/parity_support/p6_atomic_capture_log.py").read_text(
        encoding="utf-8"
    )
    tree = ast.parse(source)
    literals = {
        node.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant) and isinstance(node.value, int)
    }
    assert literals & {1799, 1800, 1250, 1251} == set(), sorted(literals)
