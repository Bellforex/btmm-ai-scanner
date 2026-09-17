"""Build the real-data fixture for confirmed S/R zone immutability.

Test tooling only. The first 480 FXCM XAUUSD M15 bars of the aligned RC3 capture
(``artifacts/rc3_lock_aligned``, host window from 2026-08-20 19:15 UTC, all after
the sealed range) with their broker close times. On this series the frozen
measurement confirms a SUPPORT zone at 4600.75 (bar 468, 2026-08-27 22:30 UTC),
replaces it with a same-geometry record (bar 469) and drops it at bar 470 -- the
retroactive disappearance the immutability decision forbids.

    python -m tests.parity_support.rc3_confirmed_zone_fixture
"""

from __future__ import annotations

import json
from pathlib import Path


def main() -> int:  # pragma: no cover - manual rebuild
    from tests.parity_support.rc3_aligned_capture import load_aligned_window

    repo = Path(__file__).resolve().parents[2]
    base = repo / "artifacts" / "rc3_lock_aligned"
    window = load_aligned_window(base / "pine_m15_run2.csv", base)
    rows = [
        {
            "time": int(c.event_time_utc.timestamp() * 1000),
            "open": str(c.open),
            "high": str(c.high),
            "low": str(c.low),
            "close": str(c.close),
            "close_time": int(c.availability_time_utc.timestamp() * 1000),
        }
        for c in window.host_series[:480]
    ]
    doc = {
        "source": (
            "FXCM XAUUSD M15, aligned RC3 capture pine_m15_run2 host window "
            "(RUNMETA + OHLC checksum verified), first 480 bars, all after the "
            "sealed range"
        ),
        "rows": rows,
    }
    out = repo / "tests" / "fixtures" / "rc3_confirmed_zone_m15.json"
    out.write_bytes((json.dumps(doc, indent=0) + "\n").encode("utf-8"))
    print(out, len(rows))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
