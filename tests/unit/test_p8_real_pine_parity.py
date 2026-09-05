"""Real Pine-vs-Python event parity for P8 (MEGA-AUTONOMOUS-26 Phases 60-62).

Two real, live-captured FXCM logs from `BTMM + POI + BTRC Scanner [P8 DEV]`
are used together:

- `p8_dev_raw_log.csv`: a plain (non-debug-isolated) capture carrying BOTH
  `P5EVAL` (per-bar-per-POI scanner state) and `P8EVENT` (Pine's own
  derived alert events) for the same ~103-bar window -- the only capture
  where state and Pine's real events co-exist, since the noise-isolated
  `p8DebugLog`-only captures never log `P5EVAL`.
- `p8_dev_clean_capture.csv`: an earlier, wider (P8EVENT-only) capture
  whose history reaches back to 2026-08-18, well before `p8_dev_raw_log`'s
  first bar (2026-09-03). Since `p8_dev_raw_log` starts mid-stream (Pine's
  real `p8Known`/`p8PrevBtmmValid`/`p8PrevPermission` caches already carry
  weeks of true history at that point), a naive Python replay that treats
  `p8_dev_raw_log`'s first bar as a priming bar would spuriously emit
  POI_ACTIVATED/BTMM_VALIDATED for POIs that were already known to Pine
  long before the window -- this second capture supplies exactly the
  "known before the window" facts needed to seed the oracle correctly.

Both files are produced by TradingView's Pine Logs -> Download logs; they
are gitignored real captures, so every test here is skipped when absent.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.parity_support.p8_alert_oracle import AlertEngine, AlertEvent, BarSnapshot
from tests.parity_support.p8_capture_log import P8Event, parse_p8_capture
from tests.parity_support.p8_digest import capture_digest
from tests.parity_support.p8_real_state_log import parse_p5eval_snapshots

_REPO = Path(__file__).resolve().parents[2]
_RAW_CAPTURE = _REPO / "artifacts" / "p8_capture" / "p8_dev_raw_log.csv"
_WIDE_CAPTURE = _REPO / "artifacts" / "p8_capture" / "p8_dev_clean_capture.csv"

pytestmark = pytest.mark.skipif(
    not (_RAW_CAPTURE.exists() and _WIDE_CAPTURE.exists()),
    reason=f"real P8 captures not present: {_RAW_CAPTURE.name}, {_WIDE_CAPTURE.name}",
)


def _replay_and_compare() -> tuple[list[AlertEvent], list[P8Event], dict[str, int]]:
    """Returns (python_events, pine_events_excl_first_bar, stats)."""
    raw_text = _RAW_CAPTURE.read_text(encoding="utf-8")
    wide_text = _WIDE_CAPTURE.read_text(encoding="utf-8")

    eval_by_bar = parse_p5eval_snapshots(raw_text)
    bars_sorted = sorted(eval_by_bar.keys())
    first_bar = bars_sorted[0]

    real_events = parse_p8_capture(raw_text).events
    wide_events = parse_p8_capture(wide_text).events

    # Facts about POIs already known to Pine BEFORE this window, mined from
    # the earlier, wider capture's own real event stream.
    known_before_window = {
        e.poi_idx
        for e in wide_events
        if e.event_type == "POI_ACTIVATED" and e.bar_ms < first_bar
    }
    btmm_valid_before = {
        e.poi_idx
        for e in wide_events
        if e.event_type == "BTMM_VALIDATED" and e.bar_ms < first_bar
    }
    latest_actionable_event: dict[int, tuple[int, str]] = {}
    for e in wide_events:
        if e.bar_ms >= first_bar:
            continue
        if e.event_type not in (
            "PERMISSION_ENTERED_ACTIONABLE",
            "PERMISSION_LOST_ACTIONABLE",
        ):
            continue
        prev = latest_actionable_event.get(e.poi_idx)
        if prev is None or e.bar_ms > prev[0]:
            latest_actionable_event[e.poi_idx] = (e.bar_ms, e.event_type)
    actionable_before = {
        idx
        for idx, (_, t) in latest_actionable_event.items()
        if t == "PERMISSION_ENTERED_ACTIONABLE"
    }

    engine = AlertEngine()
    python_events: list[AlertEvent] = []
    for i, bar_ms in enumerate(bars_sorted):
        snapshot = BarSnapshot(bar_ms=bar_ms, pois=tuple(eval_by_bar[bar_ms]))
        if i == 0:
            engine.prime(snapshot)
            # Seed prior knowledge the truncated window cannot itself supply
            # -- `prime()` only knows what is active AT the first bar.
            engine._known |= known_before_window
            for idx in btmm_valid_before:
                engine._prev_btmm_valid.setdefault(idx, True)
            for idx in actionable_before:
                engine._prev_permission.setdefault(idx, 0)  # any ACTIONABLE code
            continue
        python_events.extend(engine.process(snapshot))

    pine_events_excl_first_bar = [e for e in real_events if e.bar_ms != first_bar]
    stats = {
        "bars": len(bars_sorted),
        "first_bar": first_bar,
        "last_bar": bars_sorted[-1],
        "known_before_window": len(known_before_window),
    }
    return python_events, pine_events_excl_first_bar, stats


def test_real_pine_and_python_event_streams_match_exactly() -> None:
    python_events, pine_events, stats = _replay_and_compare()

    assert stats["bars"] >= 100, "expected a substantial real capture"
    assert len(pine_events) > 0, (
        "expected real Pine events beyond the first (unverifiable) bar"
    )

    python_keys = [(e.event_type.value, e.poi_idx, e.bar_ms) for e in python_events]
    pine_keys = [(e.event_type, e.poi_idx, e.bar_ms) for e in pine_events]

    assert len(python_keys) == len(pine_keys), (
        f"event count mismatch: python={len(python_keys)} pine={len(pine_keys)}"
    )
    assert python_keys == pine_keys, (
        "Pine's real event stream and the Python oracle's replay must match exactly, in order"
    )


def test_real_pine_and_python_digests_match() -> None:
    python_events, pine_events, _stats = _replay_and_compare()
    assert capture_digest(python_events) == capture_digest(pine_events)
