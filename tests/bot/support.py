"""Shared fixtures for the dry-run bot tests (synthetic data only)."""

from __future__ import annotations

import json
from collections.abc import Callable, Iterator, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

from botdryrun.config import BotConfig, DataSourceKind
from botdryrun.domain import (
    DecisionView,
    EventView,
    PoiView,
    ScannerBarSnapshot,
    compute_bar_digest,
    trading_day_of,
)
from botdryrun.market_data import FeedItem, FeedKind, FxcmSessionCalendar, interleave
from btmm_ai_scanner.config.enums import Timeframe
from btmm_ai_scanner.contracts.normalized_candle import NormalizedCandle
from tests.parity_support.v1a_csv_loader import load_v1a_csv

Bar = tuple[float, float, float, float]

#: Monday; 19:00Z leaves 8 bars before the 21:00->22:00 session break.
SCRIPT_START = datetime(2026, 8, 17, 19, 0, tzinfo=UTC)
#: 14:00Z Monday -> 28 bars before the session break.
SCANNER_START = datetime(2026, 8, 17, 14, 0, tzinfo=UTC)


def session_times(start: datetime, count: int, step: timedelta = timedelta(minutes=15)) -> list[datetime]:
    calendar = FxcmSessionCalendar(step=step)
    assert calendar.is_slot(start)
    times = [start]
    while len(times) < count:
        times.append(calendar.next_slot(times[-1]))
    return times


def write_csv(path: Path, times: Sequence[datetime], bars: Sequence[Bar]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = ["time,open,high,low,close,volume"]
    for index, (t, (o, h, lo, c)) in enumerate(zip(times, bars, strict=True)):
        lines.append(f"{int(t.timestamp() * 1000)},{o:.2f},{h:.2f},{lo:.2f},{c:.2f},{1000 + index}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def load(path: Path, timeframe: Timeframe = Timeframe.M15) -> tuple[NormalizedCandle, ...]:
    return load_v1a_csv(path, timeframe)


def config_for(
    dataset_root: Path,
    times: Sequence[datetime],
    **overrides: object,
) -> BotConfig:
    raw: dict[str, object] = {
        "window_start_utc": times[0].isoformat(),
        "window_end_utc": times[-1].isoformat(),
        "dataset_root": str(dataset_root),
        "data_source": DataSourceKind.CSV_DIR.value,
        "context_timeframes": [],
        "context_lookback_bars": 0,
    }
    raw.update(overrides)
    return BotConfig.from_mapping(raw)


def static_loader(items: Sequence[FeedItem]) -> Callable[[BotConfig], Sequence[FeedItem]]:
    frozen = list(items)
    return lambda _config: frozen


def host_items(candles: Sequence[NormalizedCandle]) -> list[FeedItem]:
    return interleave(candles, {})


def items_of(kind: FeedKind, candles: Sequence[NormalizedCandle]) -> list[FeedItem]:
    return [FeedItem(kind, c) for c in candles]


# ---------------------------------------------------------------------------
# Scripted scanner source (bot plumbing tests only; never used in production)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ScriptedPoi:
    idx: int
    direction: str
    zone_bottom: str
    zone_top: str
    terminal_from_bar: int | None = None
    #: From this bar on the POI reports a different effective timeframe (the
    #: registry legitimately re-labels merged POIs; persistence must follow).
    retimeframe_from_bar: int | None = None


class ScriptedScannerSource:
    """Deterministic stand-in for the scanner: fixed POIs and scripted P8
    events at given bar indices. The digest covers the candle, so a revised
    persisted input is detected exactly like with the real scanner."""

    def __init__(
        self,
        pois: Sequence[ScriptedPoi],
        events: Mapping[int, Sequence[tuple[str, int, int]]],
        standing_permission: Mapping[int, int] | None = None,
    ) -> None:
        self.pois = list(pois)
        self.events = {k: list(v) for k, v in events.items()}
        self.standing = dict(standing_permission or {})
        self.iterations = 0

    def iterate(
        self,
        host_timeframe: Timeframe,
        host_series: Sequence[NormalizedCandle],
        context_series: Mapping[Timeframe, Sequence[NormalizedCandle]],
    ) -> Iterator[ScannerBarSnapshot]:
        self.iterations += 1
        permission = dict(self.standing)
        for index, candle in enumerate(host_series):
            bar_ms = int(candle.availability_time_utc.timestamp() * 1000)
            views = []
            for p in self.pois:
                terminal = p.terminal_from_bar is not None and index >= p.terminal_from_bar
                views.append(
                    PoiView(
                        record_id=f"poi-{p.idx}",
                        poi_idx=p.idx,
                        poi_type="SCRIPTED",
                        direction=p.direction,
                        family="SCRIPTED",
                        source_timeframe="M15",
                        effective_timeframe=(
                            "H1"
                            if p.retimeframe_from_bar is not None and index >= p.retimeframe_from_bar
                            else "M15"
                        ),
                        zone_top=Decimal(p.zone_top),
                        zone_bottom=Decimal(p.zone_bottom),
                        source_time_utc=host_series[0].event_time_utc.isoformat(),
                        availability_time_utc=host_series[0].availability_time_utc.isoformat(),
                        fresh_active=not terminal,
                        terminal_reason="MITIGATED" if terminal else None,
                        terminal_time_utc=None,
                    )
                )
            events: list[EventView] = []
            for event_type, poi_idx, perm in self.events.get(index, []):
                if event_type == "PERMISSION_ENTERED_ACTIONABLE":
                    permission[poi_idx] = perm
                elif event_type == "PERMISSION_LOST_ACTIONABLE":
                    permission[poi_idx] = perm
                events.append(
                    EventView(
                        event_type=event_type,
                        poi_idx=poi_idx,
                        bar_ms=bar_ms,
                        sequence_in_bar=len(events),
                        poi_record_id=f"poi-{poi_idx}",
                        poi_bullish=self.pois[poi_idx].direction == "BULLISH",
                        tier=1,
                        btmm_valid=True,
                        permission=perm,
                        lifecycle=3,
                        terminal_reason="MITIGATED" if event_type == "POI_TERMINAL" else None,
                    )
                )
            decisions = tuple(
                DecisionView(
                    record_id=f"poi-{p.idx}",
                    poi_idx=p.idx,
                    permission="SCRIPTED",
                    permission_code=permission.get(p.idx, 4),
                    actionable=permission.get(p.idx, 4) in (0, 1),
                    final_score=50,
                    lifecycle="POI_VALIDATED",
                    btmm_valid=True,
                )
                for p in self.pois
            )
            p3 = tuple(f"bar={index}|poi={v.poi_idx}|fresh={v.fresh_active}|close={candle.close}" for v in views)
            p5 = tuple(f"bar={index}|poi={d.poi_idx}|perm={d.permission_code}" for d in decisions)
            p8 = tuple(f"{e.event_type}|{e.poi_idx}|{e.bar_ms}" for e in events)
            fresh = sum(1 for v in views if v.fresh_active)
            digest = compute_bar_digest(
                bar_index=index,
                bar_ms=bar_ms,
                primed=index == 0,
                registry_size=len(views),
                new_registry_pois=len(views) if index == 0 else 0,
                fresh_at_close=fresh,
                mitigated_at_close=len(views) - fresh,
                invalidated_at_close=0,
                p3_lines=p3,
                p5_lines=p5,
                p8_lines=p8,
            )
            yield ScannerBarSnapshot(
                bar_index=index,
                bar_ms=bar_ms,
                candle=candle,
                trading_day=trading_day_of(candle.event_time_utc),
                primed=index == 0,
                pois=tuple(views),
                decisions=decisions,
                events=tuple(events),
                new_registry_pois=len(views) if index == 0 else 0,
                fresh_at_close=fresh,
                mitigated_at_close=len(views) - fresh,
                invalidated_at_close=0,
                p3_lines=p3,
                p5_lines=p5,
                p8_lines=p8,
                digest=digest,
            )


# ---------------------------------------------------------------------------
# The scripted trading scenario (30 bars across a session break)
# ---------------------------------------------------------------------------

SCRIPT_BARS = 30
ENTERED = "PERMISSION_ENTERED_ACTIONABLE"
LOST = "PERMISSION_LOST_ACTIONABLE"
TERMINAL = "POI_TERMINAL"

SCRIPT_POIS = (
    ScriptedPoi(0, "BULLISH", "98.00", "99.00"),
    ScriptedPoi(1, "BEARISH", "102.00", "103.00"),
    ScriptedPoi(2, "BULLISH", "97.00", "98.00", terminal_from_bar=9),
    ScriptedPoi(3, "BULLISH", "96.00", "97.00", terminal_from_bar=11),
    ScriptedPoi(4, "BULLISH", "99.00", "99.50"),
    ScriptedPoi(5, "BEARISH", "100.20", "100.80"),
    ScriptedPoi(6, "BULLISH", "95.00", "96.00", retimeframe_from_bar=5),
)

SCRIPT_EVENTS: dict[int, list[tuple[str, int, int]]] = {
    2: [(ENTERED, 0, 0)],
    3: [(ENTERED, 1, 1)],
    6: [(LOST, 1, 4)],
    8: [(ENTERED, 2, 0)],
    9: [(TERMINAL, 2, 0)],
    12: [(ENTERED, 3, 0)],
    14: [(ENTERED, 4, 0), (ENTERED, 4, 0)],  # duplicate delivery in one bar
    20: [(ENTERED, 5, 0)],  # BUY_BIAS on a bearish POI -> direction mismatch
    22: [(ENTERED, 0, 0)],
}

#: POI 6 is actionable in every P5 decision but never gets a P8 event.
SCRIPT_STANDING_PERMISSION = {6: 0}


def script_bars() -> list[Bar]:
    bars: list[Bar] = [(100.0, 100.3, 99.7, 100.0)] * SCRIPT_BARS
    bars = list(bars)
    bars[5] = (100.0, 100.2, 98.8, 99.8)  # fills POI0 limit 99.00
    bars[10] = (100.0, 101.5, 99.7, 101.0)  # POI0 target 101.00
    bars[16] = (100.0, 100.2, 99.4, 99.9)  # fills POI4 limit 99.50
    bars[19] = (99.9, 100.6, 98.9, 100.0)  # POI4 stop 99.00 AND target 100.50 -> stop
    return bars


def scripted_source() -> ScriptedScannerSource:
    return ScriptedScannerSource(SCRIPT_POIS, SCRIPT_EVENTS, SCRIPT_STANDING_PERMISSION)


def scanner_bars(count: int) -> list[Bar]:
    """A price path that makes the real scanner register, carry and mitigate
    POIs (warm-up, bullish displacement, drift, walk back down)."""
    bars: list[Bar] = []
    price = 100.0
    for index in range(count):
        if index < 20:
            o = price
            c = price + (0.4 if index % 2 == 0 else -0.4)
            h, lo = max(o, c) + 0.2, min(o, c) - 0.2
        elif index < 23:
            o, c = price, price + 6.0
            h, lo = c + 0.3, o - 0.1
        elif index < 36:
            o, c = price, price + 0.5
            h, lo = c + 0.3, o - 0.2
        else:
            o, c = price, price - 1.2
            h, lo = o + 0.2, c - 0.3
        bars.append((o, h, lo, c))
        price = c
    return bars


# ---------------------------------------------------------------------------
# Engine helpers
# ---------------------------------------------------------------------------


def deterministic_journals(state_dir: Path) -> dict[str, bytes]:
    """Every deterministic journal file plus the manifest's digests."""
    journals = state_dir / "journals"
    manifest = json.loads((journals / "manifest.json").read_text(encoding="utf-8"))
    out = {name: (journals / name).read_bytes() for name in manifest["journal_sha256"]}
    out["manifest#digests"] = json.dumps(
        {
            "journal_sha256": manifest["journal_sha256"],
            "chain_digest": manifest["chain_digest"],
            "period": manifest["period_digests_authority_fold"],
            "bars": manifest["bars_processed"],
        },
        sort_keys=True,
    ).encode()
    return out
