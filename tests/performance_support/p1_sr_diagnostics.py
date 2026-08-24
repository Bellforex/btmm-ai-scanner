"""P1 support/resistance work diagnostic — developer tooling, not production.

Answers one question with numbers instead of intuition: **where does the P1 S/R
cost actually go on a real candle stream?** It replays the Pine-equivalent
frontier prefix-by-prefix over an exported CSV and reports the work counters the
frontier records, so a hot-path hypothesis can be confirmed or refuted before any
Pine source is changed.

Usage::

    uv run python -m tests.performance_support.p1_sr_diagnostics \\
        --csv <path> --provider FXCM --symbol XAUUSD --timeframe D1 \\
        --lookback 300 --window-bars 300 --json out.json

The canonical D1 measurement needs a genuine FXCM TradingView D1 export. Running
this against another provider, another timeframe, or synthetic data produces a
CONTROL measurement, and the report labels it as such — it is never a substitute
for the D1 number.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
import statistics
import sys
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any
from uuid import UUID

from btmm_ai_scanner.config.enums import InternalSymbol, Timeframe
from btmm_ai_scanner.contracts.normalized_candle import NormalizedCandle
from btmm_ai_scanner.contracts.provenance_record import EvidenceClassification
from btmm_ai_scanner.contracts.raw_candle import CandleCompleteness, CandleVolumeKind
from btmm_ai_scanner.contracts.types import SemVer
from btmm_ai_scanner.domain.configuration import MarketMeasurementConfiguration
from btmm_ai_scanner.domain.swings import ConfirmedSwing, detect_confirmed_swings
from btmm_ai_scanner.measurements.atr import compute_atr_series

_MODEL_PATH = (
    Path(__file__).resolve().parents[1] / "unit" / "test_pine_p1_sr_frontier_model.py"
)
_NAMESPACE = UUID("0193f320-1234-7abc-8def-abcdefabcd00")
_FINGERPRINT = "a" * 64
_RAW_CANDLE_ID = UUID("0193f320-1234-7abc-8def-abcdefabcdaa")
_PROVENANCE_ID = UUID("0193f320-1234-7abc-8def-abcdefabcdff")

# Availability is the CLOSE of the bar (contracts/normalized_candle.py), so the
# bar duration is part of the input contract rather than something to guess.
_BAR_DURATION = {
    Timeframe.M1: timedelta(minutes=1),
    Timeframe.M5: timedelta(minutes=5),
    Timeframe.M15: timedelta(minutes=15),
    Timeframe.H1: timedelta(hours=1),
    Timeframe.H3: timedelta(hours=3),
    Timeframe.H4: timedelta(hours=4),
    Timeframe.D1: timedelta(days=1),
    Timeframe.W1: timedelta(weeks=1),
}


def _uuid7_like(key: str) -> UUID:
    """Deterministic id in the v7 shape the contracts require.

    Derived from a semantic key, never random, so a replay is reproducible.
    """
    digest = hashlib.sha256(key.encode("utf-8")).digest()[:16]
    value = int.from_bytes(digest, "big")
    value &= ~(0xF << 76)
    value |= 7 << 76  # version 7
    value &= ~(0x3 << 62)
    value |= 0x2 << 62  # RFC 4122 variant
    return UUID(int=value)


def _load_model() -> Any:
    """Load the validated frontier model by path.

    The model lives with its oracle tests so there is exactly one implementation
    and one place where its equality against production Python is proven. Loading
    it by path keeps that arrangement without turning the test tree into a
    package.
    """
    spec = importlib.util.spec_from_file_location("_p1_sr_model", _MODEL_PATH)
    if spec is None or spec.loader is None:  # pragma: no cover - defensive
        raise RuntimeError(f"cannot load frontier model from {_MODEL_PATH}")
    module = importlib.util.module_from_spec(spec)
    # dataclasses resolves annotations through sys.modules, so the module has to
    # be registered before it executes.
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


# ---------------------------------------------------------------------------
# CSV input
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Row:
    timestamp: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal


_TIME_KEYS = ("time", "timestamp", "date", "datetime", "open_time")
_FIELD_KEYS = {
    "open": ("open", "o"),
    "high": ("high", "h"),
    "low": ("low", "l"),
    "close": ("close", "c"),
}


def _pick(header: Sequence[str], candidates: Sequence[str]) -> str:
    lowered = {name.strip().lower(): name for name in header}
    for candidate in candidates:
        if candidate in lowered:
            return lowered[candidate]
    raise ValueError(f"none of {candidates} present in CSV header {list(header)}")


def _parse_timestamp(raw: str) -> datetime:
    text = raw.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        # TradingView also exports epoch seconds
        parsed = datetime.fromtimestamp(int(float(text)), tz=UTC)
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)


def load_rows(path: Path) -> list[Row]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise ValueError(f"{path} has no header row")
        header = reader.fieldnames
        time_key = _pick(header, _TIME_KEYS)
        keys = {name: _pick(header, opts) for name, opts in _FIELD_KEYS.items()}
        rows = [
            Row(
                timestamp=_parse_timestamp(record[time_key]),
                open=Decimal(str(record[keys["open"]]).strip()),
                high=Decimal(str(record[keys["high"]]).strip()),
                low=Decimal(str(record[keys["low"]]).strip()),
                close=Decimal(str(record[keys["close"]]).strip()),
            )
            for record in reader
        ]
    rows.sort(key=lambda r: r.timestamp)
    return rows


@dataclass
class QualityReport:
    rows: int = 0
    duplicate_timestamps: int = 0
    out_of_order_before_sort: int = 0
    zero_or_negative_prices: int = 0
    high_below_body: int = 0
    low_above_body: int = 0
    high_below_low: int = 0

    @property
    def clean(self) -> bool:
        return (
            self.duplicate_timestamps == 0
            and self.zero_or_negative_prices == 0
            and self.high_below_body == 0
            and self.low_above_body == 0
            and self.high_below_low == 0
        )


def assess_quality(rows: Sequence[Row]) -> QualityReport:
    report = QualityReport(rows=len(rows))
    seen: set[datetime] = set()
    previous: datetime | None = None
    for row in rows:
        if row.timestamp in seen:
            report.duplicate_timestamps += 1
        seen.add(row.timestamp)
        if previous is not None and row.timestamp < previous:
            report.out_of_order_before_sort += 1
        previous = row.timestamp
        if min(row.open, row.high, row.low, row.close) <= 0:
            report.zero_or_negative_prices += 1
        if row.high < max(row.open, row.close):
            report.high_below_body += 1
        if row.low > min(row.open, row.close):
            report.low_above_body += 1
        if row.high < row.low:
            report.high_below_low += 1
    return report


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def window_fingerprint(rows: Sequence[Row]) -> str:
    """Deterministic hash of the exact analysed window, values untouched."""
    digest = hashlib.sha256()
    for row in rows:
        digest.update(
            f"{row.timestamp.isoformat()}|{row.open}|{row.high}|{row.low}|{row.close}\n".encode()
        )
    return digest.hexdigest()


# ---------------------------------------------------------------------------
# Domain construction
# ---------------------------------------------------------------------------


def _candle(
    index: int, row: Row, symbol: InternalSymbol, timeframe: Timeframe, provider: str
) -> NormalizedCandle:
    availability = row.timestamp + _BAR_DURATION[timeframe]
    return NormalizedCandle.model_validate(
        {
            "record_id": _uuid7_like(f"candle|{index}|{row.timestamp.isoformat()}"),
            "content_fingerprint": _FINGERPRINT,
            "raw_candle_id": _RAW_CANDLE_ID,
            "provider": provider,
            "source_reference": f"{provider.lower()}-{symbol.value.lower()}",
            "source_symbol": symbol.value,
            "source_timeframe": timeframe.value,
            "symbol": symbol,
            "timeframe": timeframe,
            "event_time_utc": row.timestamp,
            "availability_time_utc": availability,
            "processing_time_utc": availability,
            "original_event_time": row.timestamp,
            "original_availability_time": availability,
            "original_timezone": "UTC",
            "open": row.open,
            "high": row.high,
            "low": row.low,
            "close": row.close,
            "volume": Decimal("1"),
            "volume_kind": CandleVolumeKind.TICK,
            "completeness": CandleCompleteness.CONFIRMED_COMPLETE,
            "rule_version": SemVer.parse("0.1.0"),
            "contract_version": SemVer.parse("0.1.0"),
            "schema_version": SemVer.parse("0.1.0"),
            "provenance_id": _PROVENANCE_ID,
        }
    )


def build_candles(
    rows: Sequence[Row], symbol: InternalSymbol, timeframe: Timeframe, provider: str
) -> tuple[NormalizedCandle, ...]:
    return tuple(
        _candle(index, row, symbol, timeframe, provider)
        for index, row in enumerate(rows)
    )


def _confirmed_swings(
    window: Sequence[NormalizedCandle], configuration: MarketMeasurementConfiguration
) -> tuple[ConfirmedSwing, ...]:
    """Production swing detection, given the deterministic identity Pine uses.

    Pine has no UUIDs; its swing identity is the pivot-end anchor. Deriving the
    record_id from exactly that anchor keeps the two in step.
    """
    candidates = detect_confirmed_swings(tuple(window), configuration)
    swings: list[ConfirmedSwing] = []
    for candidate in candidates:
        key = f"swing|{candidate.swing_type.value}|{candidate.pivot_end_time_utc.isoformat()}"
        swings.append(
            ConfirmedSwing(
                record_id=_uuid7_like(key),
                content_fingerprint=_FINGERPRINT,
                symbol=candidate.symbol,
                timeframe=candidate.timeframe,
                swing_type=candidate.swing_type,
                pivot_price=candidate.pivot_price,
                pivot_bar_index=candidate.pivot_bar_index,
                pivot_candle_record_ids=candidate.pivot_candle_record_ids,
                pivot_start_time_utc=candidate.pivot_start_time_utc,
                pivot_end_time_utc=candidate.pivot_end_time_utc,
                local_confirmation_time_utc=candidate.local_confirmation_time_utc,
                meaningful_confirmation_time_utc=(
                    candidate.meaningful_confirmation_time_utc
                ),
                confirmation_candle_id=candidate.confirmation_candle_id,
                pivot_reference_atr=candidate.pivot_reference_atr,
                pivot_tie_tolerance=candidate.pivot_tie_tolerance,
                reversal_threshold=candidate.reversal_threshold,
                reversal_excursion=candidate.reversal_excursion,
                availability_time_utc=candidate.meaningful_confirmation_time_utc,
                rule_version=SemVer.parse("1.0.0"),
                contract_version=SemVer.parse("0.1.0"),
                schema_version=SemVer.parse("0.1.0"),
                evidence_classification=(
                    EvidenceClassification.ENGINEERING_PROVISIONAL
                ),
                provenance_id=_PROVENANCE_ID,
            )
        )
    return tuple(swings)


# ---------------------------------------------------------------------------
# Replay
# ---------------------------------------------------------------------------


@dataclass
class Replay:
    counters: dict[str, int] = field(default_factory=dict)
    per_bar: list[dict[str, int]] = field(default_factory=list)
    a_support: list[int] = field(default_factory=list)
    a_resistance: list[int] = field(default_factory=list)
    a_total: list[int] = field(default_factory=list)
    published: list[int] = field(default_factory=list)


def replay(
    candles: tuple[NormalizedCandle, ...],
    *,
    lookback: int,
    first_prefix: int,
    configuration: MarketMeasurementConfiguration,
) -> Replay:
    model = _load_model()
    frontier = model.SRFrontier(configuration, lookback=lookback)
    atr_full = list(compute_atr_series(candles, configuration.atr_period))
    out = Replay()

    for end in range(first_prefix, len(candles) + 1):
        window_first = max(0, end - lookback)
        window = candles[window_first:end]
        swings = _confirmed_swings(window, configuration)
        zones = frontier.advance(
            list(candles[:end]), atr_full[:end], swings, window_first
        )
        supports = sum(1 for s in swings if s.swing_type.value == "SWING_LOW")
        out.a_support.append(supports)
        out.a_resistance.append(len(swings) - supports)
        out.a_total.append(len(swings))
        out.published.append(len(zones))

    out.counters = frontier.counters.snapshot()
    out.per_bar = list(frontier.per_bar)
    return out


def _stats(values: Sequence[int]) -> dict[str, float | int]:
    if not values:
        return {"max": 0, "median": 0, "p95": 0, "mean": 0, "latest": 0}
    ordered = sorted(values)
    p95_index = min(len(ordered) - 1, round(0.95 * (len(ordered) - 1)))
    return {
        "max": max(values),
        "median": statistics.median(values),
        "p95": ordered[p95_index],
        "mean": round(statistics.fmean(values), 3),
        "latest": values[-1],
    }


def _ratio(numerator: float, denominator: float) -> float | None:
    return None if denominator == 0 else round(numerator / denominator, 4)


def summarise(replayed: Replay) -> dict[str, Any]:
    counters = replayed.counters
    bars = counters.get("bars_processed", 0)
    per_bar_pairs = [bar["actual_pair_visits"] for bar in replayed.per_bar]
    per_bar_advances = [bar["tracker_advances"] for bar in replayed.per_bar]
    per_bar_walks = [bar["walks"] for bar in replayed.per_bar]
    return {
        "counters": counters,
        "A_total": _stats(replayed.a_total),
        "A_support": _stats(replayed.a_support),
        "A_resistance": _stats(replayed.a_resistance),
        "published_zones": _stats(replayed.published),
        "per_bar_pair_visits": _stats(per_bar_pairs),
        "per_bar_tracker_advances": _stats(per_bar_advances),
        "bars_with_a_walk": sum(per_bar_walks),
        "ratios": {
            "actual_pair_visits_per_new_pair": _ratio(
                counters.get("actual_pair_visits", 0),
                counters.get("new_semantic_pairs", 0),
            ),
            "dedup_hits_over_pair_visits": _ratio(
                counters.get("pair_dedup_hits", 0),
                counters.get("actual_pair_visits", 0),
            ),
            "pair_visits_per_bar": _ratio(counters.get("actual_pair_visits", 0), bars),
            "tracker_advances_per_bar": _ratio(
                counters.get("tracker_advances", 0), bars
            ),
            "walks_per_swing_change": _ratio(
                counters.get("walks", 0), counters.get("swing_frontier_changes", 0)
            ),
            "walks_per_bar": _ratio(counters.get("walks", 0), bars),
            "actual_over_potential_pairs": _ratio(
                counters.get("actual_pair_visits", 0),
                counters.get("potential_pairs", 0),
            ),
        },
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _canonical_note(provider: str, timeframe: str) -> str:
    if provider.upper() == "FXCM" and timeframe.upper() == "D1":
        return "CANONICAL D1 MEASUREMENT"
    return (
        f"CONTROL MEASUREMENT ONLY ({provider.upper()} {timeframe.upper()}) — "
        "not a substitute for the canonical FXCM D1 measurement"
    )


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--csv", required=True, type=Path)
    parser.add_argument("--provider", required=True)
    parser.add_argument("--symbol", default="XAUUSD")
    parser.add_argument("--timeframe", required=True)
    parser.add_argument("--lookback", type=int, default=300)
    parser.add_argument(
        "--window-bars",
        type=int,
        default=300,
        help="analyse only the newest N closed candles (0 = all rows)",
    )
    parser.add_argument(
        "--drop-last",
        type=int,
        default=0,
        help="drop N trailing rows, e.g. a still-forming final candle",
    )
    parser.add_argument("--json", type=Path)
    args = parser.parse_args(argv)

    rows = load_rows(args.csv)
    if args.drop_last:
        rows = rows[: -args.drop_last]
    quality = assess_quality(rows)
    selected = rows[-args.window_bars :] if args.window_bars else rows

    symbol = InternalSymbol(args.symbol.upper())
    timeframe = Timeframe(args.timeframe.upper())
    configuration = MarketMeasurementConfiguration(minimum_price_tick=Decimal("0.01"))
    candles = build_candles(selected, symbol, timeframe, args.provider.upper())

    replayed = replay(
        candles,
        lookback=args.lookback,
        first_prefix=1,
        configuration=configuration,
    )
    summary = summarise(replayed)

    payload: dict[str, Any] = {
        "classification": _canonical_note(args.provider, args.timeframe),
        "source": {
            "path": str(args.csv),
            "sha256": sha256_of(args.csv),
            "provider": args.provider.upper(),
            "symbol": symbol.value,
            "timeframe": timeframe.value,
            "total_rows": quality.rows,
            "dropped_trailing_rows": args.drop_last,
        },
        "window": {
            "bars": len(selected),
            "start": selected[0].timestamp.isoformat() if selected else None,
            "end": selected[-1].timestamp.isoformat() if selected else None,
            "sha256": window_fingerprint(selected),
        },
        "quality": {
            "clean": quality.clean,
            **{k: v for k, v in quality.__dict__.items()},
        },
        "lookback": args.lookback,
        "summary": summary,
    }

    if args.json:
        args.json.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    print(f"== {payload['classification']}")
    print(
        f"   {payload['source']['provider']} {payload['source']['symbol']} "
        f"{payload['source']['timeframe']}  rows={payload['source']['total_rows']} "
        f"analysed={payload['window']['bars']} lookback={args.lookback}"
    )
    print(f"   window {payload['window']['start']} .. {payload['window']['end']}")
    print(f"   window sha256 {payload['window']['sha256']}")
    print(f"   quality clean = {quality.clean}  {quality.__dict__}")
    print("-- swing counts (A)")
    for name in ("A_total", "A_support", "A_resistance"):
        print(f"   {name:<14} {summary[name]}")
    print("-- work counters")
    for key, value in sorted(summary["counters"].items()):
        print(f"   {key:<26} {value}")
    print("-- per-bar")
    print(f"   pair visits      {summary['per_bar_pair_visits']}")
    print(f"   tracker advances {summary['per_bar_tracker_advances']}")
    print(f"   bars with a walk {summary['bars_with_a_walk']}")
    print("-- ratios")
    for key, value in summary["ratios"].items():
        print(f"   {key:<34} {value}")
    return 0


if __name__ == "__main__":  # pragma: no cover - CLI
    sys.exit(main())
