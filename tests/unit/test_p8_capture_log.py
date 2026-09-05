"""P8 capture parser + digest: directed proof, and a synthetic
Pine-source-shaped capture replayed through both the parser and the
Python `AlertEngine` oracle to confirm they agree exactly -- the same
kind of proof `test_p5_atomic_capture_replay_parity.py` already
established for P5, applied here to a synthetic (not yet real-FXCM)
P8EVENT/P8PRIME log, since no live TradingView capture exists yet.
"""

from __future__ import annotations

import pytest

from tests.parity_support.p8_alert_oracle import (
    AlertEngine,
    BarSnapshot,
    PoiSnapshot,
)
from tests.parity_support.p8_capture_log import P8CaptureError, parse_p8_capture
from tests.parity_support.p8_digest import capture_digest


def _line(ts: str, tag_line: str) -> str:
    return f"{ts},{tag_line}"


def test_parses_a_minimal_synthetic_capture():
    text = "\n".join(
        [
            _line("2026-09-06T09:00:00.000+01:00", "P8PRIME|bar=1000|poiIdx=1|btmmValid=false|permission=4|terminal=false"),
            _line(
                "2026-09-06T09:15:00.000+01:00",
                "P8EVENT|type=POI_ACTIVATED|bar=2000|poiIdx=5|poiDir=BULL|poiTier=1|btmmValid=false|permission=4|lifecycle=1",
            ),
            _line(
                "2026-09-06T09:15:00.000+01:00",
                "P8EVENT|type=PERMISSION_ENTERED_ACTIONABLE|bar=2000|poiIdx=5|poiDir=BULL|poiTier=1|btmmValid=false|permission=0|lifecycle=1",
            ),
        ]
    )
    capture = parse_p8_capture(text)
    assert len(capture.events) == 2
    assert capture.events[0].event_type == "POI_ACTIVATED"
    assert capture.events[0].poi_idx == 5
    assert capture.events[1].event_type == "PERMISSION_ENTERED_ACTIONABLE"
    assert capture.events[1].permission == 0
    assert 1000 in capture.prime_by_bar
    assert capture.prime_by_bar[1000][0].poi_idx == 1


def test_duplicate_identical_event_line_is_collapsed():
    line = _line(
        "2026-09-06T09:15:00.000+01:00",
        "P8EVENT|type=POI_ACTIVATED|bar=2000|poiIdx=5|poiDir=BULL|poiTier=1|btmmValid=false|permission=4|lifecycle=1",
    )
    text = "\n".join([line, line])
    capture = parse_p8_capture(text)
    assert len(capture.events) == 1


def test_malformed_line_is_rejected():
    with pytest.raises(P8CaptureError):
        parse_p8_capture("P8EVENT|type=NOT_A_REAL_TYPE|bar=1|poiIdx=1|poiDir=BULL|poiTier=1|btmmValid=false|permission=1|lifecycle=1\n")


def test_missing_field_is_rejected():
    with pytest.raises(P8CaptureError):
        parse_p8_capture("P8EVENT|type=POI_ACTIVATED|bar=1|poiIdx=1\n")


def test_synthetic_capture_replayed_through_oracle_matches_parsed_events_and_digest():
    """Builds a small synthetic 'Pine-shaped' log by running the REAL
    Python oracle, formatting its output exactly as the Pine source would
    log it, then parsing that text back through `parse_p8_capture` --
    proving the parser and the oracle's own output are round-trip
    consistent, and that the digest computed from each side matches."""
    engine = AlertEngine()
    prime_snapshot = BarSnapshot(bar_ms=1000, pois=(PoiSnapshot(1, True, 1, False, False, 4, 1),))
    engine.prime(prime_snapshot)

    bar2 = BarSnapshot(
        bar_ms=2000,
        pois=(
            PoiSnapshot(1, True, 1, False, False, 0, 1),  # permission entered actionable
            PoiSnapshot(2, False, 2, False, True, 4, 1),  # new + btmm valid same bar
        ),
    )
    oracle_events = engine.process(bar2)
    assert len(oracle_events) == 3  # PERMISSION_ENTERED_ACTIONABLE(1), POI_ACTIVATED(2), BTMM_VALIDATED(2)

    # Format exactly as the Pine `P8EVENT|...` line does.
    lines = [
        "2026-09-06T09:00:00.000+01:00,P8PRIME|bar=1000|poiIdx=1|btmmValid=false|permission=4|terminal=false"
    ]
    for e in oracle_events:
        lines.append(
            "2026-09-06T09:15:00.000+01:00,"
            f"P8EVENT|type={e.event_type}|bar={e.bar_ms}|poiIdx={e.poi_idx}|"
            f"poiDir={'BULL' if e.poi_bullish else 'BEAR'}|poiTier={e.tier}|"
            f"btmmValid={'true' if e.btmm_valid else 'false'}|permission={e.permission}|lifecycle={e.lifecycle}"
        )
    capture = parse_p8_capture("\n".join(lines))

    assert len(capture.events) == len(oracle_events)
    parsed_keys = [ev.event_key for ev in capture.events]
    oracle_keys = [ev.event_key for ev in oracle_events]
    assert parsed_keys == [(t, p, b) for (t, p, b) in oracle_keys]  # StrEnum vs str compare equal

    digest_from_capture = capture_digest(list(capture.events))
    digest_from_oracle = capture_digest(oracle_events)
    assert digest_from_capture == digest_from_oracle
    h1, h2 = digest_from_capture
    assert h1 != 0 and h2 != 0
