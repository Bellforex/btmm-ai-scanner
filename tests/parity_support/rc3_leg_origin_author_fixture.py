"""Build the permanent H4 author-regression fixture for the ORDER BLOCK leg origin.

Test tooling only. The author's two H4 examples (08-04 18:00 4074.70-4088.96
and 08-05 06:00 4153.11-4179.50) sit in the first FXCM H4 bars after the
sealed validation range, where the frozen swing ATR has no history of its own.
The fixture therefore holds:

* ``real``: the unmodified FXCM XAUUSD H4 candles from 2026-08-03 10:00 UTC
  (first bar after the sealed range) onward, with their real open/close times;
* ``synthetic_context``: a clearly synthetic, deterministic pre-context (not
  market data, timestamps before the sealed range starts) that only seeds the
  ATR and an established bullish structure whose last weak high (4150) is
  broken by the real 08-05 02:00 close -- the same structural situation the
  author's chart shows (bullish structure, pullback to 4019.03, higher low
  4065.46, bullish BOS). No sealed bar is read, replayed or reproduced.

Run ``python -m tests.parity_support.rc3_leg_origin_author_fixture`` to rebuild
``tests/fixtures/rc3_leg_origin_h4_author.json`` from the local aligned export.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

__all__ = ["synthetic_context"]

_H4 = timedelta(hours=4)
_CONTEXT_END = datetime(2026, 7, 13, 20, 0, tzinfo=UTC)  # well before the seal


def _leg(rows: list[tuple[float, float, float, float]], end: float, bars: int) -> None:
    start = rows[-1][3] if rows else end
    step = (end - start) / bars
    price = start
    for _ in range(bars):
        o, c = price, price + step
        rows.append((o, max(o, c) + 8.0, min(o, c) - 8.0, c))
        price = c


def synthetic_context() -> list[dict[str, object]]:
    rows: list[tuple[float, float, float, float]] = []
    for k in range(16):  # ATR warm-up: gentle zig-zag around 3850
        o = 3850.0 + (4.0 if k % 2 else -4.0)
        c = 3850.0 + (-4.0 if k % 2 else 4.0)
        rows.append((o, max(o, c) + 16.0, min(o, c) - 16.0, c))
    _leg(rows, 3950.0, 4)
    _leg(rows, 3905.0, 3)
    _leg(rows, 4040.0, 5)  # higher high
    _leg(rows, 3985.0, 3)  # higher low -> bullish structure
    _leg(rows, 4150.0, 6)  # breaks 4040 (BOS); 4150 becomes the weak high
    _leg(rows, 4055.17, 4)  # pullback into the first real bar's open
    start = _CONTEXT_END - _H4 * (len(rows) - 1)
    out = []
    for i, (o, h, lo, c) in enumerate(rows):
        t = start + _H4 * i
        out.append(
            {
                "time": int(t.timestamp() * 1000),
                "open": f"{o:.2f}",
                "high": f"{h:.2f}",
                "low": f"{lo:.2f}",
                "close": f"{c:.2f}",
                "close_time": int((t + _H4).timestamp() * 1000),
            }
        )
    return out


def main() -> int:  # pragma: no cover - manual rebuild
    from btmm_ai_scanner.config.enums import Timeframe
    from tests.parity_support.rc3_poi_overlap_audit import load_unsealed_segments

    repo = Path(__file__).resolve().parents[2]
    segment = load_unsealed_segments(
        repo / "artifacts" / "rc3_aligned" / "ohlc_h4.csv",
        Timeframe.H4,
        repo / "artifacts" / "rc3_poi_coverage" / "_n" / "h4.csv",
    )[-1]
    assert segment[0].event_time_utc == datetime(2026, 8, 3, 10, 0, tzinfo=UTC)
    real = [
        {
            "time": int(c.event_time_utc.timestamp() * 1000),
            "open": str(c.open),
            "high": str(c.high),
            "low": str(c.low),
            "close": str(c.close),
            "close_time": int(c.availability_time_utc.timestamp() * 1000),
        }
        for c in segment[:34]
    ]
    doc = {
        "source": (
            "real: FXCM XAUUSD H4 same-session export (artifacts/rc3_aligned/"
            "ohlc_h4.csv), first 34 bars after the sealed range; "
            "synthetic_context: deterministic synthetic pre-context from "
            "tests/parity_support/rc3_leg_origin_author_fixture.py (not market data)"
        ),
        "author_examples": {
            "example_1": {
                "source_utc": "2026-08-04T18:00:00Z",
                "zone": ["4074.7", "4088.96"],
            },
            "example_2": {
                "source_utc": "2026-08-05T06:00:00Z",
                "zone": ["4153.11", "4179.5"],
            },
        },
        "synthetic_context": synthetic_context(),
        "real": real,
    }
    out = repo / "tests" / "fixtures" / "rc3_leg_origin_h4_author.json"
    out.write_text(json.dumps(doc, indent=1) + "\n", encoding="utf-8")
    print(out)
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
