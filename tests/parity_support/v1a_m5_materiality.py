"""V1-A M5-materiality gate (test/validation tooling only).

Nothing in ``src/`` imports this, and it changes no production semantics.
Every detection/scoring decision this module observes comes from the same
already-closed engines ``v1a_harness.py`` drives (``IncrementalReplayKernel``,
``assess_confluence``, the P8 alert oracle) -- this module only decides WHICH
timeframe set and WHICH (non-DEV) window they get driven over, and folds
their output into a structural per-bar/per-POI record two runs can be
diffed on. No POI/BTMM/BTRC/P8 scoring or detection logic is changed
anywhere.

WHY THIS GATE EXISTS
---------------------
The just-finished V1-A DEV characterization harness runs on five timeframes
(W1/D1/H4/H1/M15), omitting M5, because real M5 history on this project's
feed only reaches back to 2026-08-09 -- after the frozen V1-A DEV/OOS window
(2026-05-31 to 2026-08-03). ``trend_engine.py``/``regime_engine.py`` gracefully
skip any missing timeframe, and M5 is not in the trend "authority" set
(``trend_engine.py`` ``_AUTHORITY_TIMEFRAMES`` iteration vs. the 3-timeframe
``_resolve_global`` authority read) -- but "the code looks like it degrades
gracefully" is not evidence. In particular, ``t3_engine.assess_pullback``
passes the SAME ``analysis.poi_analysis.poi_lifecycle_transitions`` (the full,
cross-timeframe transition list, not filtered to one timeframe) into every
per-timeframe pullback assessment, and ``btmm.configuration.BtmmConfiguration
.formation_timeframes`` defaults to ``{M5, M15}`` -- meaning M5 IS a genuine
BTMM/POI formation timeframe when tracked, so adding M5 can (a) create a
whole new class of M5-origin POIs, and (b) change a SHARED, non-M5 POI's own
pullback/BTMM-adjacent reads through that shared cross-timeframe list. That
mechanism is exactly why this module runs the real engine twice (FULL6 vs
NO_M5) over the same real window and diffs every field, rather than
reasoning about it from the source alone.

WHY A NEW MODULE, NOT AN EDIT TO ``v1a_harness.py``/``v1a_csv_loader.py``
--------------------------------------------------------------------------
Those two files are a separate, already-finished piece of work (staged,
uncommitted, not this task's to commit). Editing them in place would mix
this task's diff into their staged diff and make "leave them staged as-is"
impossible to honor cleanly. This module is purely additive: it reuses their
public functions (``build_scanner_configuration``, ``verify_v1a_manifest_hashes``,
``load_v1a_csv``, ``VerifiedFile``, ``ManifestHashMismatchError``,
``DEFAULT_PRE_DEV_LOOKBACK_BARS``, ``ALREADY_USED_BOUNDARY_UTC``) but never
imports or touches their DEV-window-specific functions
(``load_dev_only_m15``, ``load_dev_bounded_context_capped``) and defines its
own window-parametrized loaders instead.

WHY THE MAIN LOOP IS GROUPED BY EXACT AVAILABILITY TIMESTAMP, NOT "PER M15 BAR
WITH CONTEXT BUNDLED IN" LIKE ``v1a_harness.run_dev_replay``
--------------------------------------------------------------------------------
``run_dev_replay`` bundles any context (W1/D1/H4/H1) candle whose own
availability is <= the current M15 bar's availability into that M15 step's
single ``advance_group`` call. That is safe there because every context
timeframe in that harness is coarser than M15 (H1 is the finest), so at most
one context candle per timeframe can land inside any 15-minute window, and
it always lands exactly on an M15 boundary (this dataset's own timeframes
are all M15-grid-aligned, confirmed by the data-provenance manifest).

M5 breaks that assumption: it is FINER than M15 (three M5 candles complete
per M15 window, only the last of which shares the M15 candle's own
availability instant). Bundling all three into one M15-driven
``advance_group`` call would collapse three genuinely distinct availability
groups into one, which is not "the same observable contract" the kernel's
own docstring promises (byte-identical to ``scan_market`` over the true
per-availability-group prefix). So this module's main loop instead flattens
every tracked timeframe's in-window candles into one list, groups it by
EXACT ``availability_time_utc`` (never by a "<=" catch-up bound), and calls
``kernel.advance_group`` once per distinct group in ascending order --
finalizing a ``ScannerAnalysis`` / running ``assess_confluence`` / running
the P8 alert engine ONLY at the groups that include an M15 candle (M15
remains "the primary observation series", per the task brief). This is
strictly finer-grained than ``run_dev_replay``'s own bundling, so it
subsumes it correctly for the NO_M5 config (every context candle in this
dataset lands on an M15 boundary, so NO_M5's observation cadence and
groups are identical either way) while being unambiguously correct for the
FULL6 config's extra M5 groups.

NO LOOKAHEAD, BY CONSTRUCTION
--------------------------------
Every candle handed to the kernel or to ``assess_confluence`` is bounded to
its own ``availability_time_utc``, in strict ascending order, exactly as in
``v1a_harness.run_dev_replay`` -- see that module's docstring for the same
argument, which applies unchanged here.

OOS / DEV ISOLATION
---------------------
Every window-parametrized loader in this module refuses (raises
``WindowIntegrityError``) if asked to load a window whose ``window_start``
precedes ``v1a_csv_loader.ALREADY_USED_BOUNDARY_UTC`` (2026-08-03T07:00 UTC)
-- the frozen boundary after which no prior P2-P9 capture nor the DEV/OOS
split extends. This is a structural guard, not just a choice of constants:
even a future caller who mis-typed a window cannot make this module read a
DEV or OOS row.
"""

from __future__ import annotations

import csv
import hashlib
import statistics
from collections import defaultdict
from collections.abc import Iterator
from dataclasses import astuple, dataclass, field
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from uuid import UUID

from btmm_ai_scanner.btrc.t5_engine import assess_confluence
from btmm_ai_scanner.config.enums import InternalSymbol, Timeframe
from btmm_ai_scanner.contracts.normalized_candle import NormalizedCandle
from btmm_ai_scanner.contracts.raw_candle import CandleCompleteness, CandleVolumeKind
from btmm_ai_scanner.contracts.types import SemVer
from btmm_ai_scanner.historical_backtest.identity import (
    ContentAddressedIdentityProvider,
    derive_content_fingerprint,
    derive_provenance_id,
    derive_record_id,
)
from btmm_ai_scanner.poi.enums import PoiLifecycleStatus, PoiStrengthTier
from btmm_ai_scanner.scanner.configuration import ScannerConfiguration
from btmm_ai_scanner.scanner.replay import IncrementalReplayKernel
from tests.parity_support.p5_active_poi_loop_model import resolve_eligible_and_next
from tests.parity_support.p5_wire_normalized_replay import (
    LIFECYCLE_CODE,
    PERMISSION_CODE,
    POI_TIER_BY_CODE,
)
from tests.parity_support.p8_alert_oracle import AlertEngine, BarSnapshot, PoiSnapshot
from tests.parity_support.v1a_csv_loader import (
    ALREADY_USED_BOUNDARY_UTC,
    DEFAULT_PRE_DEV_LOOKBACK_BARS,
    ManifestHashMismatchError,
    VerifiedFile,
    load_v1a_csv,
    verify_v1a_manifest_hashes,
)
from tests.parity_support.v1a_harness import build_scanner_configuration

_TERMINAL_STATUS = PoiLifecycleStatus.GENUINE_INVALIDATION_CONFIRMED
#: Duplicated (not imported) from ``v1a_harness``/``p5_wire_normalized_replay``
#: deliberately -- a 3-line constant, not worth coupling to another module's
#: private name for.
_TIER_CODE_BY_VALUE: dict[PoiStrengthTier | None, int] = {
    v: k for k, v in POI_TIER_BY_CODE.items() if v is not None
}
_TIER_CODE_BY_VALUE[None] = 0

# --------------------------------------------------------------------------
# Window + M5 file constants
# --------------------------------------------------------------------------

#: The full available M5 span on this feed, M15-bar-aligned at the end (the
#: last M15 bar in ``v1a_raw_ohlc_full_loaded.csv`` is 2026-09-04T20:30:00Z;
#: M5 itself has two further rows, 20:35/20:40, deliberately excluded so the
#: M15 series -- "the primary observation series" -- remains the bounding
#: series). Both ends are strictly inside the already-used window's own
#: superset (2026-08-03T07:00 onward) and strictly outside the DEV/OOS
#: windows, which both end by 2026-08-03.
OVERLAP_WINDOW_START: datetime = datetime(2026, 8, 9, 22, 0, tzinfo=UTC)
OVERLAP_WINDOW_END: datetime = datetime(2026, 9, 4, 20, 30, tzinfo=UTC)

M5_FILENAME = "v1a_raw_ohlc_M5.csv"
#: Verified directly against the artifact on disk at the start of this task
#: (task brief's own hash, independently re-verified with certutil before
#: this module was written). Not present in
#: ``docs/validation/BTRC_V1_V1A_DATA_PROVENANCE_MANIFEST.md``'s file TABLE
#: (that document's own M5 section records row count/date range prose only,
#: no hash row) -- transcribed here instead, verified on every load.
M5_SHA256 = "55f86db9ffb161ab0099f100b16a0505deba05087164ecf5665e6bb5d419d6c2"
M5_ROW_COUNT = 5508

_BASE_CONTEXT_TIMEFRAMES: tuple[Timeframe, ...] = (
    Timeframe.W1,
    Timeframe.D1,
    Timeframe.H4,
    Timeframe.H1,
)
#: The five-timeframe set the DEV harness already uses (no M5).
TIMEFRAMES_NO_M5: tuple[Timeframe, ...] = (*_BASE_CONTEXT_TIMEFRAMES, Timeframe.M15)
#: The full six-timeframe set this gate tests against NO_M5.
TIMEFRAMES_FULL6: tuple[Timeframe, ...] = (*TIMEFRAMES_NO_M5, Timeframe.M5)


class WindowIntegrityError(ValueError):
    """A requested window/row count violates a structural safety invariant
    of this module (e.g. would risk touching DEV/OOS rows, or a loaded file
    does not match its expected row count)."""


#: M5's own fixed-cadence duration, per the same "availability_time_utc =
#: event_time_utc + duration" rule ``v1a_csv_loader.load_v1a_csv`` applies to
#: the other five files. NOT read from ``v1a_csv_loader._DURATION`` (that
#: table has no M5 entry -- the DEV harness never needed one -- and that
#: file is not this task's to edit, see module docstring), so this module
#: carries its own single-entry duration constant and a near-duplicate of
#: ``load_v1a_csv``'s row-parsing loop, parametrized for M5 instead of
#: reaching into another module's private table.
_M5_DURATION = timedelta(minutes=5)
_M5_SCHEMA_VERSION = SemVer.parse("0.1.0")
_M5_PROVIDER = "FXCM"
_M5_DATASET_ID = "v1a-validation"
_M5_DATASET_VERSION = "1"


def _epoch_ms_to_utc(time_ms: int) -> datetime:
    seconds, millis = divmod(time_ms, 1000)
    return datetime(1970, 1, 1, tzinfo=UTC) + timedelta(seconds=seconds, milliseconds=millis)


def _load_m5_csv(path: Path, *, symbol: InternalSymbol = InternalSymbol.XAUUSD) -> tuple[NormalizedCandle, ...]:
    """M5-only counterpart of ``v1a_csv_loader.load_v1a_csv`` (same row
    format, same identity-derivation primitives, same strictly-increasing
    ordering check, same ``event_time_utc + duration`` availability rule) --
    duplicated rather than parametrizing the shared loader because that
    would require editing ``v1a_csv_loader.py`` (see module docstring)."""
    relative_path = path.name
    raw_bytes = path.read_bytes()
    expected_sha256 = hashlib.sha256(raw_bytes).hexdigest()

    provenance_id, _ = derive_provenance_id(
        dataset_id=_M5_DATASET_ID,
        dataset_version=_M5_DATASET_VERSION,
        provider=_M5_PROVIDER,
        relative_path=relative_path,
        expected_sha256=expected_sha256,
    )

    candles: list[NormalizedCandle] = []
    previous_event_time: datetime | None = None
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise ValueError(f"{relative_path}: empty file, no header row.")
        expected_header = ["time", "open", "high", "low", "close", "volume"]
        if list(reader.fieldnames) != expected_header:
            raise ValueError(
                f"{relative_path}: unexpected header {list(reader.fieldnames)!r}, "
                f"expected {expected_header!r}."
            )
        for row_number, row in enumerate(reader, start=2):
            time_ms = int(row["time"])
            event_time_utc = _epoch_ms_to_utc(time_ms)
            if previous_event_time is not None and event_time_utc <= previous_event_time:
                raise ValueError(
                    f"{relative_path} row {row_number}: time is not strictly increasing "
                    f"({event_time_utc.isoformat()} follows {previous_event_time.isoformat()})."
                )
            previous_event_time = event_time_utc

            availability_time_utc = event_time_utc + _M5_DURATION
            open_price = Decimal(row["open"])
            high_price = Decimal(row["high"])
            low_price = Decimal(row["low"])
            close_price = Decimal(row["close"])
            volume_text = row["volume"].strip() if row["volume"] is not None else ""
            volume = Decimal(volume_text) if volume_text != "" else None

            source_record_id = str(time_ms)
            content_fingerprint, _ = derive_content_fingerprint(
                provider=_M5_PROVIDER,
                symbol=symbol,
                timeframe=Timeframe.M5,
                event_time_utc=event_time_utc,
                availability_time_utc=availability_time_utc,
                open_price=open_price,
                high_price=high_price,
                low_price=low_price,
                close_price=close_price,
                volume=volume,
                completeness=CandleCompleteness.CONFIRMED_COMPLETE,
                source_record_id=source_record_id,
            )
            record_id, _ = derive_record_id(
                provenance_id=provenance_id,
                source_record_id=source_record_id,
                provider=_M5_PROVIDER,
                symbol=symbol,
                timeframe=Timeframe.M5,
                event_time_utc=event_time_utc,
            )
            raw_candle_id, _ = derive_record_id(
                provenance_id=provenance_id,
                source_record_id=source_record_id + "#raw",
                provider=_M5_PROVIDER,
                symbol=symbol,
                timeframe=Timeframe.M5,
                event_time_utc=event_time_utc,
            )

            candle = NormalizedCandle.model_validate(
                {
                    "record_id": record_id,
                    "content_fingerprint": content_fingerprint,
                    "raw_candle_id": raw_candle_id,
                    "provider": _M5_PROVIDER,
                    "source_reference": f"v1a:{relative_path}:{row_number}",
                    "source_symbol": symbol.value,
                    "source_timeframe": Timeframe.M5.value,
                    "symbol": symbol,
                    "timeframe": Timeframe.M5,
                    "event_time_utc": event_time_utc,
                    "availability_time_utc": availability_time_utc,
                    "processing_time_utc": availability_time_utc,
                    "original_event_time": event_time_utc,
                    "original_availability_time": availability_time_utc,
                    "original_timezone": "UTC",
                    "open": open_price,
                    "high": high_price,
                    "low": low_price,
                    "close": close_price,
                    "volume": volume,
                    "volume_kind": CandleVolumeKind.UNKNOWN,
                    "completeness": CandleCompleteness.CONFIRMED_COMPLETE,
                    "rule_version": _M5_SCHEMA_VERSION,
                    "contract_version": _M5_SCHEMA_VERSION,
                    "schema_version": _M5_SCHEMA_VERSION,
                    "provenance_id": provenance_id,
                }
            )
            candles.append(candle)

    return tuple(candles)


def verify_m5_hash(root: Path) -> VerifiedFile:
    """Verify ``v1a_raw_ohlc_M5.csv`` against ``M5_SHA256``. Raises
    ``ManifestHashMismatchError`` (the same exception ``v1a_csv_loader`` uses
    for its own five files) on any mismatch or missing file."""
    path = root / M5_FILENAME
    if not path.is_file():
        raise ManifestHashMismatchError(f"M5 file missing on disk: {path}")
    raw_bytes = path.read_bytes()
    actual = hashlib.sha256(raw_bytes).hexdigest()
    if actual != M5_SHA256:
        raise ManifestHashMismatchError(
            f"{M5_FILENAME}: SHA-256 mismatch -- expected {M5_SHA256}, disk has "
            f"{actual}. Refusing to proceed on unverified data."
        )
    return VerifiedFile(
        filename=M5_FILENAME, path=path, timeframe=Timeframe.M5, sha256=actual, row_count=M5_ROW_COUNT
    )


def _guard_window_start(window_start: datetime) -> None:
    if window_start < ALREADY_USED_BOUNDARY_UTC:
        raise WindowIntegrityError(
            f"window_start {window_start.isoformat()} precedes the frozen "
            f"already-used-window boundary {ALREADY_USED_BOUNDARY_UTC.isoformat()}; "
            "loading it would risk touching DEV or OOS rows. Refusing."
        )


def load_window_m15(root: Path, window_start: datetime, window_end: datetime) -> tuple[NormalizedCandle, ...]:
    """Load the M15 series, bounded to ``[window_start, window_end]`` by
    ``event_time_utc`` (inclusive both ends). Structurally cannot return a
    DEV/OOS row: refuses any window starting before the already-used
    boundary (see module docstring)."""
    _guard_window_start(window_start)
    verified = verify_v1a_manifest_hashes(root)
    full_entry = next(v for v in verified if v.filename == "v1a_raw_ohlc_full_loaded.csv")
    all_m15 = load_v1a_csv(full_entry.path, Timeframe.M15)
    if len(all_m15) != full_entry.row_count:
        raise WindowIntegrityError(f"expected {full_entry.row_count} M15 rows, loaded {len(all_m15)}.")
    windowed = tuple(c for c in all_m15 if window_start <= c.event_time_utc <= window_end)
    if not windowed:
        raise WindowIntegrityError("no M15 rows fall inside the requested window.")
    return windowed


def load_window_m5(root: Path, window_start: datetime, window_end: datetime) -> tuple[NormalizedCandle, ...]:
    """Load the M5 series, bounded to ``[window_start, window_end]`` by
    ``event_time_utc`` (inclusive both ends). Same OOS/DEV guard as
    ``load_window_m15``."""
    _guard_window_start(window_start)
    entry = verify_m5_hash(root)
    all_m5 = _load_m5_csv(entry.path)
    if len(all_m5) != entry.row_count:
        raise WindowIntegrityError(f"expected {entry.row_count} M5 rows, loaded {len(all_m5)}.")
    return tuple(c for c in all_m5 if window_start <= c.event_time_utc <= window_end)


def load_window_context(
    root: Path,
    window_start: datetime,
    window_end: datetime,
    timeframes: tuple[Timeframe, ...],
    *,
    bound_availability_utc: datetime,
    pre_window_lookback_bars: int = DEFAULT_PRE_DEV_LOOKBACK_BARS,
) -> dict[Timeframe, tuple[NormalizedCandle, ...]]:
    """Load an arbitrary subset of {W1, D1, H4, H1, M5} (never M15, which
    ``load_window_m15`` owns), each timeframe capped EXACTLY like
    ``v1a_csv_loader.load_dev_bounded_context_capped``: every candle whose
    ``event_time_utc`` falls inside ``[window_start, window_end]`` is
    included in full, in strict availability order, with zero lookahead;
    only the portion strictly BEFORE ``window_start`` is capped to the most
    recent ``pre_window_lookback_bars`` candles. Every returned candle is
    additionally bounded by ``availability_time_utc <= bound_availability_utc``
    (mirroring ``load_dev_bounded_context``'s own bound), so a W1/D1 bar
    whose OWN availability lands after the window's own last M15
    availability instant is excluded even if its ``event_time_utc`` is
    inside the window.

    M5 naturally receives ZERO pre-window lookback here when ``window_start``
    is ``OVERLAP_WINDOW_START`` -- that is this dataset's own M5 history
    boundary, not a value chosen by this function.
    """
    _guard_window_start(window_start)
    result: dict[Timeframe, tuple[NormalizedCandle, ...]] = {}
    for timeframe in timeframes:
        if timeframe is Timeframe.M15:
            raise WindowIntegrityError("M15 must be loaded via load_window_m15, not load_window_context.")
        if timeframe is Timeframe.M5:
            entry = verify_m5_hash(root)
            all_candles = _load_m5_csv(entry.path)
        else:
            verified = verify_v1a_manifest_hashes(root)
            entry = next(
                v
                for v in verified
                if v.timeframe is timeframe
                and "raw_ohlc_" in v.filename
                and v.filename != "v1a_raw_ohlc_full_loaded.csv"
            )
            all_candles = load_v1a_csv(entry.path, timeframe)
        if len(all_candles) != entry.row_count:
            raise WindowIntegrityError(
                f"{entry.filename}: expected {entry.row_count} rows, loaded {len(all_candles)}."
            )
        pre = [c for c in all_candles if c.event_time_utc < window_start]
        during = [c for c in all_candles if window_start <= c.event_time_utc <= window_end]
        capped_pre = pre[-pre_window_lookback_bars:] if pre_window_lookback_bars > 0 else []
        bounded = tuple(
            c for c in (*capped_pre, *during) if c.availability_time_utc <= bound_availability_utc
        )
        result[timeframe] = bounded
    return result


def build_configuration_for(timeframes: tuple[Timeframe, ...]) -> ScannerConfiguration:
    """The DEV harness's own ``build_scanner_configuration()``, with
    ``Timeframe.M5`` added to ``optional_timeframes`` iff ``M5`` is in
    ``timeframes`` -- guarantees the FULL6/NO_M5 configurations differ in
    EXACTLY that one field, never independently re-derived."""
    base = build_scanner_configuration()
    if Timeframe.M5 in timeframes:
        return base.model_copy(update={"optional_timeframes": base.optional_timeframes | frozenset({Timeframe.M5})})
    return base


# --------------------------------------------------------------------------
# Run spec + replay driver
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class MaterialityRunSpec:
    label: str
    dataset_root: Path
    timeframes: tuple[Timeframe, ...]
    window_start: datetime
    window_end: datetime
    pre_window_lookback_bars: int = DEFAULT_PRE_DEV_LOOKBACK_BARS
    max_bars: int | None = None


def full6_spec(dataset_root: Path, *, max_bars: int | None = None) -> MaterialityRunSpec:
    return MaterialityRunSpec(
        label="FULL6",
        dataset_root=dataset_root,
        timeframes=TIMEFRAMES_FULL6,
        window_start=OVERLAP_WINDOW_START,
        window_end=OVERLAP_WINDOW_END,
        max_bars=max_bars,
    )


def no_m5_spec(dataset_root: Path, *, max_bars: int | None = None) -> MaterialityRunSpec:
    return MaterialityRunSpec(
        label="NO_M5",
        dataset_root=dataset_root,
        timeframes=TIMEFRAMES_NO_M5,
        window_start=OVERLAP_WINDOW_START,
        window_end=OVERLAP_WINDOW_END,
        max_bars=max_bars,
    )


@dataclass(frozen=True)
class PoiBarRecord:
    """One (POI, M15-observation-bar) pair's full BTRC decision, as a flat,
    hash/diff-friendly record. Field selection follows the task brief's own
    diff list verbatim."""

    poi_record_id: str
    bar_availability_utc: str  # isoformat
    bar_index: int
    poi_type: str
    poi_direction: str
    poi_timeframe: str
    lifecycle_state: str
    poi_lifecycle_status: str | None
    btmm_valid: bool
    trend_alignment: str
    regime: str
    momentum_direction: str | None
    momentum_acceleration: str | None
    breakout_state: str | None
    pullback_state: str | None
    session_context: str | None
    volatility_state: str | None
    global_direction: str
    btmm_score: int
    poi_score: int
    trend_score: int
    regime_score: int
    momentum_score: int
    breakout_score: int
    liquidity_score: int
    volatility_score: int
    final_confluence_score: int
    permission: str


@dataclass(frozen=True)
class EventRecordLite:
    event_type: str
    poi_record_id: str
    bar_availability_utc: str  # isoformat
    bar_index: int


@dataclass
class MaterialityReplayResult:
    label: str
    timeframes: tuple[Timeframe, ...]
    bar_availabilities: tuple[str, ...]
    records: dict[tuple[str, str], PoiBarRecord] = field(default_factory=dict)
    events: list[EventRecordLite] = field(default_factory=list)
    poi_universe: frozenset[str] = frozenset()


def _iter_groups(
    flat: list[tuple[datetime, Timeframe, NormalizedCandle]],
) -> Iterator[dict[Timeframe, tuple[NormalizedCandle, ...]]]:
    """Group a chronologically-sorted flat candle list by EXACT
    ``availability_time_utc`` -- never a "<=" catch-up bound. See module
    docstring for why this matters once M5 is in the mix."""
    index = 0
    n = len(flat)
    while index < n:
        group_time = flat[index][0]
        group: dict[Timeframe, list[NormalizedCandle]] = {}
        while index < n and flat[index][0] == group_time:
            _, timeframe, candle = flat[index]
            group.setdefault(timeframe, []).append(candle)
            index += 1
        yield {tf: tuple(v) for tf, v in group.items()}


def run_materiality_replay(spec: MaterialityRunSpec) -> MaterialityReplayResult:
    """Run one FULL6 or NO_M5 replay: one ``ScannerAnalysis`` snapshot per
    M15-aligned availability group (see module docstring for why the group
    boundary is exact-timestamp, not M15-bundled), the active-POI loop,
    ``assess_confluence`` per eligible POI, and P8 event derivation --
    exactly the same code paths ``v1a_harness.run_dev_replay`` uses, just
    driven over an arbitrary window/timeframe-set instead of the frozen DEV
    window.
    """
    m15 = load_window_m15(spec.dataset_root, spec.window_start, spec.window_end)
    if spec.max_bars is not None:
        m15 = m15[: spec.max_bars]
    if not m15:
        raise WindowIntegrityError("empty M15 window after max_bars truncation.")
    window_end_availability = m15[-1].availability_time_utc

    context_timeframes = tuple(tf for tf in spec.timeframes if tf is not Timeframe.M15)
    context_full = load_window_context(
        spec.dataset_root,
        spec.window_start,
        spec.window_end,
        context_timeframes,
        bound_availability_utc=window_end_availability,
        pre_window_lookback_bars=spec.pre_window_lookback_bars,
    )
    context_candles: dict[Timeframe, list[NormalizedCandle]] = {
        tf: sorted(candles, key=lambda c: c.availability_time_utc) for tf, candles in context_full.items()
    }

    config = build_configuration_for(spec.timeframes)
    kernel = IncrementalReplayKernel(spec.timeframes, config, ContentAddressedIdentityProvider(), ())

    # --- warm-up: pre-window context candles only (never M15, never M5 --
    # M5's own history starts exactly at OVERLAP_WINDOW_START, so it
    # naturally contributes zero pre-window candles) ---
    pre_window_flat: list[tuple[datetime, Timeframe, NormalizedCandle]] = []
    for timeframe, candles in context_candles.items():
        for candle in candles:
            if candle.event_time_utc < spec.window_start:
                pre_window_flat.append((candle.availability_time_utc, timeframe, candle))
    pre_window_flat.sort(key=lambda row: row[0])
    for group in _iter_groups(pre_window_flat):
        kernel.advance_group(group)

    visible: dict[Timeframe, list[NormalizedCandle]] = {tf: [] for tf in spec.timeframes}
    for timeframe, candles in context_candles.items():
        pre = [c for c in candles if c.event_time_utc < spec.window_start]
        visible[timeframe].extend(pre)

    # --- main loop: every tracked timeframe's in-window candles, grouped by
    # exact availability timestamp ---
    in_window_flat: list[tuple[datetime, Timeframe, NormalizedCandle]] = [
        (candle.availability_time_utc, Timeframe.M15, candle) for candle in m15
    ]
    for timeframe, candles in context_candles.items():
        for candle in candles:
            if candle.event_time_utc >= spec.window_start:
                in_window_flat.append((candle.availability_time_utc, timeframe, candle))
    in_window_flat.sort(key=lambda row: row[0])

    poi_idx_by_id: dict[UUID, int] = {}
    next_poi_idx = 0
    previously_active_ids: frozenset[UUID] = frozenset()
    alert_engine = AlertEngine()
    records: dict[tuple[str, str], PoiBarRecord] = {}
    events: list[EventRecordLite] = []
    bar_availabilities: list[str] = []
    poi_universe: set[str] = set()
    bar_index = -1

    for group in _iter_groups(in_window_flat):
        kernel.advance_group(group)
        for timeframe, new_candles in group.items():
            visible[timeframe].extend(new_candles)

        if Timeframe.M15 not in group:
            continue  # not an observation point -- keep advancing

        bar_index += 1
        snapshot = kernel.finalize()
        bar_iso = snapshot.availability_time_utc.isoformat()
        bar_availabilities.append(bar_iso)

        status_by_id = {
            s.poi_record_id: s.poi_lifecycle_status for s in snapshot.poi_analysis.current_poi_states
        }
        obs_by_id = {o.record_id: o for o in snapshot.poi_analysis.poi_observations}
        eligible_ids, next_active = resolve_eligible_and_next(
            status_by_id, previously_active_ids, known_ids=frozenset(obs_by_id)
        )
        ordered = tuple(
            sorted(eligible_ids, key=lambda pid: (obs_by_id[pid].availability_time_utc, str(pid)))
        )

        poi_snapshots: list[PoiSnapshot] = []
        for poi_id in ordered:
            poi = obs_by_id[poi_id]
            if poi_id not in poi_idx_by_id:
                poi_idx_by_id[poi_id] = next_poi_idx
                next_poi_idx += 1

            decision = assess_confluence(
                snapshot,
                poi,
                candles_by_timeframe=visible,
                evaluation_time_utc=snapshot.availability_time_utc,
            )
            status = status_by_id.get(poi_id)
            poi_snapshots.append(
                PoiSnapshot(
                    poi_idx=poi_idx_by_id[poi_id],
                    poi_bullish=poi.direction.value == "BULLISH",
                    tier=_TIER_CODE_BY_VALUE[poi.strength_tier],
                    terminal=status is _TERMINAL_STATUS,
                    btmm_valid=decision.btmm_valid,
                    permission=PERMISSION_CODE[decision.analytical_permission],
                    lifecycle=LIFECYCLE_CODE[decision.lifecycle_state],
                )
            )

            poi_id_str = str(poi_id)
            poi_universe.add(poi_id_str)
            records[(poi_id_str, bar_iso)] = PoiBarRecord(
                poi_record_id=poi_id_str,
                bar_availability_utc=bar_iso,
                bar_index=bar_index,
                poi_type=decision.poi_type.value,
                poi_direction=decision.poi_direction.value,
                poi_timeframe=decision.poi_timeframe.value,
                lifecycle_state=decision.lifecycle_state.value,
                poi_lifecycle_status=(
                    decision.poi_lifecycle_status.value if decision.poi_lifecycle_status else None
                ),
                btmm_valid=decision.btmm_valid,
                trend_alignment=decision.trend_alignment.value,
                regime=decision.regime.value,
                momentum_direction=(decision.momentum_direction.value if decision.momentum_direction else None),
                momentum_acceleration=(
                    decision.momentum_acceleration.value if decision.momentum_acceleration else None
                ),
                breakout_state=(decision.breakout_state.value if decision.breakout_state else None),
                pullback_state=(decision.pullback_state.value if decision.pullback_state else None),
                session_context=(decision.session_context.value if decision.session_context else None),
                volatility_state=(decision.volatility_state.value if decision.volatility_state else None),
                global_direction=decision.global_direction.value,
                btmm_score=decision.component_scores.btmm_score,
                poi_score=decision.component_scores.poi_score,
                trend_score=decision.component_scores.trend_score,
                regime_score=decision.component_scores.regime_score,
                momentum_score=decision.component_scores.momentum_score,
                breakout_score=decision.component_scores.breakout_score,
                liquidity_score=decision.component_scores.liquidity_score,
                volatility_score=decision.component_scores.volatility_score,
                final_confluence_score=decision.final_confluence_score,
                permission=decision.analytical_permission.value,
            )

        bar_ms = int(snapshot.availability_time_utc.timestamp() * 1000)
        bar_snapshot = BarSnapshot(bar_ms=bar_ms, pois=tuple(poi_snapshots))
        if not alert_engine.primed:
            alert_engine.prime(bar_snapshot)
            fired = []
        else:
            fired = alert_engine.process(bar_snapshot)

        poi_id_by_idx_this_bar = {poi_idx_by_id[pid]: pid for pid in ordered}
        for alert_event in fired:
            poi_id = poi_id_by_idx_this_bar[alert_event.poi_idx]
            events.append(
                EventRecordLite(
                    event_type=alert_event.event_type.value,
                    poi_record_id=str(poi_id),
                    bar_availability_utc=bar_iso,
                    bar_index=bar_index,
                )
            )

        previously_active_ids = next_active

    return MaterialityReplayResult(
        label=spec.label,
        timeframes=spec.timeframes,
        bar_availabilities=tuple(bar_availabilities),
        records=records,
        events=events,
        poi_universe=frozenset(poi_universe),
    )


def compute_result_digest(result: MaterialityReplayResult) -> str:
    """A canonical, order-independent SHA-256 over one replay result's full
    observable output -- used to prove same-config determinism (run twice,
    same digest) before any FULL6-vs-NO_M5 comparison is trusted."""
    parts: list[str] = [result.label, ",".join(tf.value for tf in result.timeframes)]
    for key in sorted(result.records):
        parts.append("R|" + "|".join(str(x) for x in astuple(result.records[key])))
    for event in sorted(result.events, key=lambda e: (e.bar_availability_utc, e.event_type, e.poi_record_id)):
        parts.append("E|" + "|".join(str(x) for x in astuple(event)))
    blob = "\n".join(parts).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()


# --------------------------------------------------------------------------
# Diff + classification
# --------------------------------------------------------------------------

SEMANTIC_FIELDS: tuple[str, ...] = (
    "poi_type",
    "poi_direction",
    "poi_timeframe",
    "lifecycle_state",
    "poi_lifecycle_status",
    "btmm_valid",
    "trend_alignment",
    "regime",
    "momentum_direction",
    "momentum_acceleration",
    "breakout_state",
    "pullback_state",
    "session_context",
    "volatility_state",
    "global_direction",
)
COMPONENT_FIELDS: tuple[str, ...] = (
    "btmm_score",
    "poi_score",
    "trend_score",
    "regime_score",
    "momentum_score",
    "breakout_score",
    "liquidity_score",
    "volatility_score",
)


@dataclass(frozen=True)
class UniverseDiff:
    full6_poi_count: int
    no_m5_poi_count: int
    shared_poi_count: int
    only_full6_poi_count: int
    only_no_m5_poi_count: int
    full6_record_count: int
    no_m5_record_count: int
    shared_record_count: int
    only_full6_record_count: int
    only_no_m5_record_count: int


@dataclass(frozen=True)
class ScoreDiff:
    compared_count: int
    identical_count: int
    different_count: int
    max_abs_delta: int
    mean_abs_delta: float
    median_abs_delta: float
    cross_45_up: int  # FULL6 < 45  -> NO_M5 >= 45
    cross_45_down: int  # FULL6 >= 45 -> NO_M5 < 45
    cross_65_up: int  # FULL6 < 65  -> NO_M5 >= 65
    cross_65_down: int  # FULL6 >= 65 -> NO_M5 < 65


@dataclass(frozen=True)
class EventDiff:
    full6_event_count: int
    no_m5_event_count: int
    exact_matches: int
    missing_from_no_m5: int
    extra_in_no_m5: int
    timing_mismatches: int
    event_type_mismatches: int
    poi_identity_mismatches_full6_only: int
    poi_identity_mismatches_no_m5_only: int
    by_event_type: dict[str, dict[str, int]]


@dataclass(frozen=True)
class MaterialityDiffReport:
    universe: UniverseDiff
    field_mismatch_counts: dict[str, int]
    component_mismatch_counts: dict[str, int]
    component_max_abs_delta: dict[str, int]
    score: ScoreDiff
    permission_mismatch_count: int
    permission_transition_matrix: dict[tuple[str, str], int]
    events: EventDiff


def _median(values: list[int]) -> float:
    return float(statistics.median(values)) if values else 0.0


def diff_records(
    full6_records: dict[tuple[str, str], PoiBarRecord],
    no_m5_records: dict[tuple[str, str], PoiBarRecord],
) -> tuple[
    UniverseDiff,
    dict[str, int],
    dict[str, int],
    dict[str, int],
    ScoreDiff,
    int,
    dict[tuple[str, str], int],
]:
    full6_keys = set(full6_records)
    no_m5_keys = set(no_m5_records)
    shared_keys = full6_keys & no_m5_keys

    full6_poi_ids = {k[0] for k in full6_keys}
    no_m5_poi_ids = {k[0] for k in no_m5_keys}

    universe = UniverseDiff(
        full6_poi_count=len(full6_poi_ids),
        no_m5_poi_count=len(no_m5_poi_ids),
        shared_poi_count=len(full6_poi_ids & no_m5_poi_ids),
        only_full6_poi_count=len(full6_poi_ids - no_m5_poi_ids),
        only_no_m5_poi_count=len(no_m5_poi_ids - full6_poi_ids),
        full6_record_count=len(full6_keys),
        no_m5_record_count=len(no_m5_keys),
        shared_record_count=len(shared_keys),
        only_full6_record_count=len(full6_keys - no_m5_keys),
        only_no_m5_record_count=len(no_m5_keys - full6_keys),
    )

    field_mismatch_counts = {f: 0 for f in SEMANTIC_FIELDS}
    component_mismatch_counts = {f: 0 for f in COMPONENT_FIELDS}
    component_max_abs_delta = {f: 0 for f in COMPONENT_FIELDS}
    deltas: list[int] = []
    identical_scores = 0
    cross_45_up = cross_45_down = cross_65_up = cross_65_down = 0
    permission_matrix: dict[tuple[str, str], int] = defaultdict(int)
    permission_mismatch = 0

    for key in shared_keys:
        a = full6_records[key]
        b = no_m5_records[key]
        for f in SEMANTIC_FIELDS:
            if getattr(a, f) != getattr(b, f):
                field_mismatch_counts[f] += 1
        for f in COMPONENT_FIELDS:
            da, db = getattr(a, f), getattr(b, f)
            if da != db:
                component_mismatch_counts[f] += 1
                component_max_abs_delta[f] = max(component_max_abs_delta[f], abs(da - db))

        delta = abs(a.final_confluence_score - b.final_confluence_score)
        deltas.append(delta)
        if delta == 0:
            identical_scores += 1
        if a.final_confluence_score < 45 <= b.final_confluence_score:
            cross_45_up += 1
        if b.final_confluence_score < 45 <= a.final_confluence_score:
            cross_45_down += 1
        if a.final_confluence_score < 65 <= b.final_confluence_score:
            cross_65_up += 1
        if b.final_confluence_score < 65 <= a.final_confluence_score:
            cross_65_down += 1

        permission_matrix[(a.permission, b.permission)] += 1
        if a.permission != b.permission:
            permission_mismatch += 1

    n = len(deltas)
    score = ScoreDiff(
        compared_count=n,
        identical_count=identical_scores,
        different_count=n - identical_scores,
        max_abs_delta=max(deltas) if deltas else 0,
        mean_abs_delta=(sum(deltas) / n) if n else 0.0,
        median_abs_delta=_median(deltas),
        cross_45_up=cross_45_up,
        cross_45_down=cross_45_down,
        cross_65_up=cross_65_up,
        cross_65_down=cross_65_down,
    )

    return (
        universe,
        field_mismatch_counts,
        component_mismatch_counts,
        component_max_abs_delta,
        score,
        permission_mismatch,
        dict(permission_matrix),
    )


def diff_events(
    full6_events: list[EventRecordLite],
    no_m5_events: list[EventRecordLite],
    *,
    full6_poi_universe: frozenset[str],
    no_m5_poi_universe: frozenset[str],
) -> EventDiff:
    """Diff two P8 event streams.

    Matching algorithm (documented so the classification is reproducible,
    not incidental):
      1. Exact key match on ``(event_type, poi_record_id, bar_availability_utc)``.
      2. Of what's left, greedily pair remaining FULL6/NO_M5 entries sharing
         ``(event_type, poi_record_id)`` but a DIFFERENT bar -- a "timing
         mismatch" (the same transition fired, just on a different bar).
      3. Of what's STILL left, greedily pair remaining entries sharing
         ``(poi_record_id, bar_availability_utc)`` but a different
         ``event_type`` -- an "event-type mismatch" (a different transition
         fired for the same POI on the same bar).
      4. Whatever remains unpaired is reported as missing-from-NO_M5 /
         extra-in-NO_M5; the subset of those whose POI id does not exist AT
         ALL in the other run's POI universe is additionally broken out as
         a POI-identity mismatch (informational, not double-counted).
    """
    full6_keys = {(e.event_type, e.poi_record_id, e.bar_availability_utc) for e in full6_events}
    no_m5_keys = {(e.event_type, e.poi_record_id, e.bar_availability_utc) for e in no_m5_events}

    exact = full6_keys & no_m5_keys
    only_full6 = full6_keys - no_m5_keys
    only_no_m5 = no_m5_keys - full6_keys

    full6_by_type_poi: dict[tuple[str, str], list[tuple[str, str, str]]] = defaultdict(list)
    for k in only_full6:
        full6_by_type_poi[(k[0], k[1])].append(k)
    no_m5_by_type_poi: dict[tuple[str, str], list[tuple[str, str, str]]] = defaultdict(list)
    for k in only_no_m5:
        no_m5_by_type_poi[(k[0], k[1])].append(k)

    timing_mismatches = 0
    consumed_full6: set[tuple[str, str, str]] = set()
    consumed_no_m5: set[tuple[str, str, str]] = set()
    for tp, f6_list in full6_by_type_poi.items():
        nm_list = no_m5_by_type_poi.get(tp, [])
        pair_count = min(len(f6_list), len(nm_list))
        timing_mismatches += pair_count
        for i in range(pair_count):
            consumed_full6.add(f6_list[i])
            consumed_no_m5.add(nm_list[i])

    remaining_full6 = only_full6 - consumed_full6
    remaining_no_m5 = only_no_m5 - consumed_no_m5

    full6_by_poi_bar: dict[tuple[str, str], list[tuple[str, str, str]]] = defaultdict(list)
    for k in remaining_full6:
        full6_by_poi_bar[(k[1], k[2])].append(k)
    no_m5_by_poi_bar: dict[tuple[str, str], list[tuple[str, str, str]]] = defaultdict(list)
    for k in remaining_no_m5:
        no_m5_by_poi_bar[(k[1], k[2])].append(k)

    event_type_mismatches = 0
    consumed2_full6: set[tuple[str, str, str]] = set()
    consumed2_no_m5: set[tuple[str, str, str]] = set()
    for pb, f6_list in full6_by_poi_bar.items():
        nm_list = no_m5_by_poi_bar.get(pb, [])
        pair_count = min(len(f6_list), len(nm_list))
        event_type_mismatches += pair_count
        for i in range(pair_count):
            consumed2_full6.add(f6_list[i])
            consumed2_no_m5.add(nm_list[i])

    final_remaining_full6 = remaining_full6 - consumed2_full6
    final_remaining_no_m5 = remaining_no_m5 - consumed2_no_m5

    poi_identity_full6_only = sum(1 for k in final_remaining_full6 if k[1] not in no_m5_poi_universe)
    poi_identity_no_m5_only = sum(1 for k in final_remaining_no_m5 if k[1] not in full6_poi_universe)

    by_event_type: dict[str, dict[str, int]] = {}
    event_types = {e.event_type for e in full6_events} | {e.event_type for e in no_m5_events}
    for et in sorted(event_types):
        f6_type_keys = {k for k in full6_keys if k[0] == et}
        nm_type_keys = {k for k in no_m5_keys if k[0] == et}
        by_event_type[et] = {
            "full6_count": len(f6_type_keys),
            "no_m5_count": len(nm_type_keys),
            "exact_matches": len(f6_type_keys & nm_type_keys),
        }

    return EventDiff(
        full6_event_count=len(full6_events),
        no_m5_event_count=len(no_m5_events),
        exact_matches=len(exact),
        missing_from_no_m5=len(final_remaining_full6),
        extra_in_no_m5=len(final_remaining_no_m5),
        timing_mismatches=timing_mismatches,
        event_type_mismatches=event_type_mismatches,
        poi_identity_mismatches_full6_only=poi_identity_full6_only,
        poi_identity_mismatches_no_m5_only=poi_identity_no_m5_only,
        by_event_type=by_event_type,
    )


def diff_materiality(full6: MaterialityReplayResult, no_m5: MaterialityReplayResult) -> MaterialityDiffReport:
    (
        universe,
        field_mismatch_counts,
        component_mismatch_counts,
        component_max_abs_delta,
        score,
        permission_mismatch,
        permission_matrix,
    ) = diff_records(full6.records, no_m5.records)
    events = diff_events(
        full6.events,
        no_m5.events,
        full6_poi_universe=full6.poi_universe,
        no_m5_poi_universe=no_m5.poi_universe,
    )
    return MaterialityDiffReport(
        universe=universe,
        field_mismatch_counts=field_mismatch_counts,
        component_mismatch_counts=component_mismatch_counts,
        component_max_abs_delta=component_max_abs_delta,
        score=score,
        permission_mismatch_count=permission_mismatch,
        permission_transition_matrix=permission_matrix,
        events=events,
    )


def classify_materiality(report: MaterialityDiffReport) -> tuple[str, str]:
    """Class A requires ALL of: identical POI universe (POI-id AND
    per-bar-record level), identical semantic fields, identical component
    scores, identical final scores, identical permissions, identical P8
    event stream. A single one-point score difference on a single POI/bar
    disqualifies Class A -- no rounding, no partial credit. Returns
    ``(class_letter, reasoning)``."""
    reasons: list[str] = []

    u = report.universe
    if u.only_full6_poi_count or u.only_no_m5_poi_count:
        reasons.append(
            f"POI universe differs: {u.only_full6_poi_count} POI(s) only in FULL6, "
            f"{u.only_no_m5_poi_count} only in NO_M5 (shared={u.shared_poi_count})."
        )
    if u.only_full6_record_count or u.only_no_m5_record_count:
        reasons.append(
            f"(POI, bar) record universe differs: {u.only_full6_record_count} record(s) only "
            f"in FULL6, {u.only_no_m5_record_count} only in NO_M5 (shared={u.shared_record_count})."
        )
    for f, c in report.field_mismatch_counts.items():
        if c:
            reasons.append(f"semantic field '{f}' mismatched on {c} shared record(s).")
    for f, c in report.component_mismatch_counts.items():
        if c:
            reasons.append(
                f"component score '{f}' mismatched on {c} shared record(s) "
                f"(max |delta|={report.component_max_abs_delta[f]})."
            )
    if report.score.different_count:
        reasons.append(
            f"final_confluence_score differs on {report.score.different_count} shared record(s) "
            f"(max|delta|={report.score.max_abs_delta}, "
            f"45-crossings up/down={report.score.cross_45_up}/{report.score.cross_45_down}, "
            f"65-crossings up/down={report.score.cross_65_up}/{report.score.cross_65_down})."
        )
    if report.permission_mismatch_count:
        reasons.append(f"analytical_permission differs on {report.permission_mismatch_count} shared record(s).")
    ev = report.events
    if ev.missing_from_no_m5 or ev.extra_in_no_m5 or ev.timing_mismatches or ev.event_type_mismatches:
        reasons.append(
            "P8 event stream differs: "
            f"missing_from_no_m5={ev.missing_from_no_m5}, extra_in_no_m5={ev.extra_in_no_m5}, "
            f"timing_mismatches={ev.timing_mismatches}, event_type_mismatches={ev.event_type_mismatches}."
        )

    if not reasons:
        return (
            "A",
            "Every category matched exactly: identical POI universe, identical semantic "
            "fields, identical component scores, identical final scores, identical "
            "permissions, identical P8 event stream. Class A per the frozen rule (no "
            "rounding, no partial credit).",
        )
    return "B", " ".join(reasons)
