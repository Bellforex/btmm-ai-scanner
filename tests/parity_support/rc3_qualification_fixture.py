"""Build the real-data fixtures for RC3 POI qualification (author cases).

Test tooling only. Same-session FXCM XAUUSD exports of the aligned RC3 capture
(``artifacts/rc3_lock_aligned``, 2026-09-17), all bars after the sealed range:

* ``m15``: 160 M15 bars ending 2026-09-17 06:30 UTC. The author marked the BUY
  FVG sourced 05:15 (4294.06-4295.89) weak and the BUY FVG sourced 05:30
  (4298.06-4304.27) valid.
* ``h1``: 160 H1 bars ending 2026-09-17 11:00 UTC (the bullish CHOCH candle). The BUY FVG sourced 04:00
  (4298.89-4304.27) departs from the 05:00 candle, which is a BULLISH PRESSURE
  WICK: one originating formation, the pressure wick is primary.

    python -m tests.parity_support.rc3_qualification_fixture
"""

from __future__ import annotations

import json
from pathlib import Path


def main() -> int:  # pragma: no cover - manual rebuild
    from btmm_ai_scanner.config.enums import Timeframe
    from tests.parity_support.rc3_aligned_capture import _load_export

    repo = Path(__file__).resolve().parents[2]
    base = repo / "artifacts" / "rc3_qual_aligned_v12"
    doc: dict[str, object] = {
        "source": "FXCM XAUUSD same-session exports, aligned RC3 capture 2026-09-17",
    }
    for stem, tf, end in (
        ("m15", Timeframe.M15, "2026-09-17T06:30"),
        ("h1", Timeframe.H1, "2026-09-17T11:00"),
    ):
        candles = _load_export(
            base / f"ohlc_{stem}.csv", tf, base / "_normalized" / f"{stem}.csv"
        )
        last = next(
            i
            for i, c in enumerate(candles)
            if c.event_time_utc.isoformat().startswith(end)
        )
        doc[stem] = [
            {
                "time": int(c.event_time_utc.timestamp() * 1000),
                "open": str(c.open),
                "high": str(c.high),
                "low": str(c.low),
                "close": str(c.close),
                "close_time": int(c.availability_time_utc.timestamp() * 1000),
            }
            for c in candles[last - 159 : last + 1]
        ]
    out = repo / "tests" / "fixtures" / "rc3_qualification_fxcm.json"
    out.write_bytes((json.dumps(doc, indent=0) + "\n").encode("utf-8"))
    print(out)
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
