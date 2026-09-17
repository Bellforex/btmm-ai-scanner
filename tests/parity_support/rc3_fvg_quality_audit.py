"""RC3 FVG quality audit: candidate metrics for every raw FVG on real FXCM data.

Test/validation tooling only; never reads future price reaction. For each raw
three-candle FVG (first, departure, third) it records, using only candles up to
and including the third candle:

* gap width, gap / ATR-14 at the departure candle, gap / departure range;
* departure range speed ratio = range / median(previous 20 ranges) -- the frozen
  ``domain/displacement.py`` measurement -- and its frozen classification
  (NORMAL / FAST >= 1.50 / VERY_FAST >= 2.00);
* the strongest speed ratio / classification of the three candles;
* departure range / previous candle range; departure body efficiency;
* departure direction agreement with the gap.

    python -m tests.parity_support.rc3_fvg_quality_audit
"""

from __future__ import annotations

import json
import statistics
from collections import Counter
from dataclasses import asdict, dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any

from btmm_ai_scanner.config.enums import Timeframe
from btmm_ai_scanner.contracts.normalized_candle import NormalizedCandle
from btmm_ai_scanner.domain.configuration import MarketMeasurementConfiguration
from btmm_ai_scanner.domain.displacement import _classify
from btmm_ai_scanner.measurements.atr import compute_atr_series
from btmm_ai_scanner.measurements.candle_metrics import (
    body_efficiency,
    range_speed_ratio,
    total_range,
)
from btmm_ai_scanner.poi.configuration import PoiConfiguration
from btmm_ai_scanner.poi.enums import PoiDirection
from btmm_ai_scanner.poi.fair_value_gaps import detect_fair_value_gaps

__all__ = ["FvgMetrics", "fvg_metrics"]

_MCONFIG = MarketMeasurementConfiguration(minimum_price_tick=Decimal("0.01"))
_PCONFIG = PoiConfiguration(minimum_price_tick=Decimal("0.01"))


@dataclass(frozen=True)
class FvgMetrics:
    timeframe: str
    direction: str
    source_utc: str
    bottom: str
    top: str
    gap: float
    gap_atr: float | None
    gap_departure: float
    departure_speed: float | None
    departure_class: str | None
    max_speed: float | None
    max_class: str | None
    departure_prev_range: float | None
    departure_body_eff: float
    departure_aligned: bool


def _speed(candles: tuple[NormalizedCandle, ...], i: int) -> Decimal | None:
    window = _MCONFIG.range_context_window
    if i < window or total_range(candles[i]) == 0:
        return None
    return range_speed_ratio(candles[i], candles[i - window : i])


def fvg_metrics(candles: tuple[NormalizedCandle, ...]) -> list[FvgMetrics]:
    atr = compute_atr_series(candles, _MCONFIG.atr_period)
    index = {c.record_id: i for i, c in enumerate(candles)}
    out: list[FvgMetrics] = []
    for f in detect_fair_value_gaps(candles, _PCONFIG):
        i0, i1, i2 = (index[r] for r in f.source_candle_record_ids)
        dep = candles[i1]
        gap = f.zone_top - f.zone_bottom
        speeds = [_speed(candles, i) for i in (i0, i1, i2)]
        known = [s for s in speeds if s is not None]
        prev = total_range(candles[i0])
        bull = f.direction is PoiDirection.BULLISH
        out.append(
            FvgMetrics(
                timeframe=dep.timeframe.value,
                direction="BUY" if bull else "SELL",
                source_utc=candles[i0].event_time_utc.isoformat(),
                bottom=str(f.zone_bottom),
                top=str(f.zone_top),
                gap=float(gap),
                gap_atr=float(gap / atr[i1]) if atr[i1] else None,
                gap_departure=float(gap / total_range(dep))
                if total_range(dep)
                else 0.0,
                departure_speed=float(speeds[1]) if speeds[1] is not None else None,
                departure_class=_classify(speeds[1], _MCONFIG).value
                if speeds[1] is not None
                else None,
                max_speed=float(max(known)) if known else None,
                max_class=_classify(max(known), _MCONFIG).value if known else None,
                departure_prev_range=float(total_range(dep) / prev) if prev else None,
                departure_body_eff=float(body_efficiency(dep)),
                departure_aligned=(dep.close > dep.open) == bull,
            )
        )
    return out


def _quantiles(values: list[float]) -> dict[str, float]:
    if len(values) < 5:
        return {}
    q = statistics.quantiles(values, n=10)
    return {"p10": round(q[0], 3), "p50": round(q[4], 3), "p90": round(q[8], 3)}


def main() -> int:  # pragma: no cover - manual measurement
    from tests.parity_support.rc3_poi_overlap_audit import load_unsealed_segments

    repo = Path(__file__).resolve().parents[2]
    base = repo / "artifacts" / "rc3_aligned"
    out = repo / "artifacts" / "rc3_fvg_quality"
    out.mkdir(parents=True, exist_ok=True)
    report: dict[str, Any] = {}
    rows: list[dict[str, Any]] = []
    for stem, tf in (
        ("m5", Timeframe.M5),
        ("m15", Timeframe.M15),
        ("h1", Timeframe.H1),
        ("h4", Timeframe.H4),
    ):
        metrics: list[FvgMetrics] = []
        for seg in load_unsealed_segments(
            base / f"ohlc_{stem}.csv", tf, out / "_n" / f"{stem}.csv"
        ):
            metrics.extend(fvg_metrics(seg))
        rows.extend(asdict(m) for m in metrics)
        report[tf.value] = {
            "raw": len(metrics),
            "departure_class": dict(Counter(m.departure_class for m in metrics)),
            "max_class": dict(Counter(m.max_class for m in metrics)),
            "gap_atr": _quantiles(
                [m.gap_atr for m in metrics if m.gap_atr is not None]
            ),
            "departure_speed": _quantiles(
                [m.departure_speed for m in metrics if m.departure_speed is not None]
            ),
            "departure_prev_range": _quantiles(
                [m.departure_prev_range for m in metrics if m.departure_prev_range]
            ),
            "departure_aligned": sum(m.departure_aligned for m in metrics),
        }
        print(tf.value, json.dumps(report[tf.value]), flush=True)
    (out / "fvg_distribution.json").write_text(json.dumps(report, indent=1), "utf-8")
    (out / "fvg_rows.json").write_text(json.dumps(rows), "utf-8")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
