"""V1-A raw-OHLC CSV -> NormalizedCandle loader (test/validation tooling only).

Nothing in ``src/`` imports this, and it changes no production semantics.

DESIGN CHOICE — hand-rolled loader, not the manifest-driven
``historical_backtest.loader.load_historical_dataset`` path
-------------------------------------------------------------------------
``load_historical_dataset`` is built for a *manifest-declared* dataset: a
``manifest.json`` describing header mappings, ``strptime`` timestamp
formats, an IANA source timezone, per-file expected row counts, and D1/W1
"calendar close" local-time rules resolved through that timezone. The V1-A
raw files are NOT that shape — they are a direct browser export
(``time,open,high,low,close,volume`` with an **epoch-millisecond, UTC**
``time`` column, one row per bar's OPEN instant), acquired straight from
TradingView's own main-series data per
``docs/validation/BTRC_V1_V1A_DATA_PROVENANCE_MANIFEST.md``. Standing up a
synthetic ``manifest.json`` (fake header mapping, fake ``strptime`` format,
fake local timezone) just to satisfy that loader's shape would add a full
extra layer of indirection and local-time/DST resolution machinery that
has nothing to verify here — the source data has no local time at all, it
is already UTC. That extra layer is exactly the kind of "subtle bug risk"
the task brief asked us to weigh against.

So this module reads the five CSVs directly and constructs
``NormalizedCandle`` objects, while still REUSING the project's own
identity-derivation primitives (``historical_backtest.identity
.derive_provenance_id`` / ``derive_record_id`` / ``derive_content_fingerprint``)
rather than inventing a new UUIDv7/fingerprint scheme — the one piece of
that stack genuinely worth not re-deriving.

Availability-time rule (protocol §4)
-------------------------------------
For M15/H1/H4 (the three genuinely intraday files here), the protocol
pins ``availability_time_utc = event_time_utc + <timeframe duration>``
directly. D1 and W1 are not "intraday" in the protocol's own vocabulary,
but the identical rule is the mathematically exact statement of "a fixed
duration bar becomes fully known at its own close": a bar spanning a
fixed 24h (D1) or 7-day (W1) window is completely determined exactly 24h
/ 7 days after it opens, full stop — there is no broker-local-calendar
ambiguity to resolve when the source series is already a fixed-cadence
UTC clock (confirmed by the manifest's own data-quality section: 0
non-monotonic steps, and the W1/D1 first bars land on the same
22:00-UTC boundary the M15 series aligns to). This is why
``historical_backtest.csv_parser`` needs its local-timezone
"calendar_close_day_offset/calendar_close_time_local" machinery at all —
to convert a broker LOCAL close convention into UTC — a conversion this
already-UTC source data does not require. So this loader applies
``event_time_utc + duration`` uniformly across all five files
(duration = 1 day for D1, 7 days for W1), which is both the simplest
faithful implementation and the one with the least surface for a
local-time/DST bug to hide in.

No row is ever dropped, reordered, or fabricated: every physical CSV row
becomes exactly one ``NormalizedCandle``; rows are required to already be
in strictly increasing, non-duplicated ``time`` order (the manifest's own
data-quality section already asserts this for these five files), and a
loader that found otherwise raises rather than silently re-sorting or
de-duplicating.

DEV/OOS enforcement
--------------------
``load_dev_only_m15`` is the ONLY function in this module that can hand
back M15 candles for characterization use, and it deliberately never
returns (or exposes any way to reach) the OOS slice — it slices the
verified 2903-bar DEV prefix out of the loaded M15 series, asserts its
bar count and first/last timestamps against the frozen manifest, and
discards the rest of the in-memory list before returning. There is no
function anywhere in this module, or in the harness that consumes it,
that accepts an OOS row. (The OOS bytes are still read off disk as part
of reading+hashing the whole ``v1a_raw_ohlc_full_loaded.csv`` file — that
is unavoidable to verify the file's own manifest SHA-256 covers the
un-doctored file — but no OOS row is ever converted into a
``NormalizedCandle``, so its OHLC values are never available to any
Decimal/pydantic computation in this codebase.)
"""

from __future__ import annotations

import csv
import hashlib
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

from btmm_ai_scanner.config.enums import InternalSymbol, Timeframe
from btmm_ai_scanner.contracts.normalized_candle import NormalizedCandle
from btmm_ai_scanner.contracts.raw_candle import CandleCompleteness, CandleVolumeKind
from btmm_ai_scanner.contracts.types import SemVer
from btmm_ai_scanner.historical_backtest.identity import (
    derive_content_fingerprint,
    derive_provenance_id,
    derive_record_id,
)

_SCHEMA_VERSION = SemVer.parse("0.1.0")
_PROVIDER = "FXCM"
_DATASET_ID = "v1a-validation"
_DATASET_VERSION = "1"

#: Manifest-declared filenames -> (Timeframe, expected SHA-256, expected row count).
#: Transcribed verbatim from docs/validation/BTRC_V1_V1A_DATA_PROVENANCE_MANIFEST.md.
MANIFEST_FILES: dict[str, tuple[Timeframe, str, int]] = {
    "v1a_raw_ohlc_full_loaded.csv": (
        Timeframe.M15,
        "9f5322c3ba82eaf667f7bfef6a2c111670c4152f33d9c7cc824e0a3fa69c9029",
        6406,
    ),
    "v1a_raw_ohlc_W1.csv": (
        Timeframe.W1,
        "dc8a061392e586b447ff0858000dd35e8b6150a8fa1dcee931c871f08f3d3ae7",
        2754,
    ),
    "v1a_raw_ohlc_D1.csv": (
        Timeframe.D1,
        "e9ed832c6316ca48d823b83bce658cac2b7e41ce1dff79b12d1f57164efe50e0",
        901,
    ),
    "v1a_raw_ohlc_H4.csv": (
        Timeframe.H4,
        "f3789b1020fabca317a2ceb0d2dfa00c065d3db7f8ff177b0b2626c704e84a57",
        5685,
    ),
    "v1a_raw_ohlc_H1.csv": (
        Timeframe.H1,
        "44bf23f8e43c83f937188c9f380e93932e1132231797e5f5bdd2df55a02a84d2",
        9927,
    ),
}

_DURATION: dict[Timeframe, timedelta] = {
    # M5 was acquired after the V1-A manifest was frozen (for the RC3
    # six-timeframe authority), so it has no MANIFEST_FILES entry; the same
    # "a fixed-duration bar is fully known at its own close" rule applies.
    Timeframe.M5: timedelta(minutes=5),
    Timeframe.M15: timedelta(minutes=15),
    Timeframe.H1: timedelta(hours=1),
    Timeframe.H4: timedelta(hours=4),
    Timeframe.D1: timedelta(days=1),
    Timeframe.W1: timedelta(days=7),
}

#: Frozen chronological split, transcribed verbatim from the manifest.
DEV_BAR_COUNT = 2903
OOS_BAR_COUNT = 1244
DEV_FIRST_EVENT_UTC = datetime(2026, 5, 31, 22, 0, tzinfo=UTC)
DEV_LAST_EVENT_UTC = datetime(2026, 7, 14, 17, 0, tzinfo=UTC)
OOS_FIRST_EVENT_UTC = datetime(2026, 7, 14, 17, 15, tzinfo=UTC)
#: The already-used development/parity boundary (manifest: "Already-used
#: development/parity window"). Every M15 row with event_time_utc at or after
#: this instant belongs to prior P2-P9 captures, not the fresh V1-A window.
ALREADY_USED_BOUNDARY_UTC = datetime(2026, 8, 3, 7, 0, tzinfo=UTC)


class ManifestHashMismatchError(ValueError):
    """A file's on-disk SHA-256 does not match the frozen provenance manifest."""


class DevSplitIntegrityError(ValueError):
    """The DEV/OOS split computed from disk does not match the frozen manifest."""


@dataclass(frozen=True)
class VerifiedFile:
    filename: str
    path: Path
    timeframe: Timeframe
    sha256: str
    row_count: int


def verify_v1a_manifest_hashes(root: Path) -> tuple[VerifiedFile, ...]:
    """Verify every file in ``MANIFEST_FILES`` against its frozen SHA-256.

    Raises ``ManifestHashMismatchError`` on the FIRST mismatch — per the task
    instruction, any hash mismatch must stop the whole pipeline rather than
    proceed on unverified data.
    """
    verified: list[VerifiedFile] = []
    for filename, (timeframe, expected_sha256, expected_rows) in MANIFEST_FILES.items():
        path = root / filename
        if not path.is_file():
            raise ManifestHashMismatchError(f"manifest file missing on disk: {path}")
        raw_bytes = path.read_bytes()
        actual = hashlib.sha256(raw_bytes).hexdigest()
        if actual != expected_sha256:
            raise ManifestHashMismatchError(
                f"{filename}: SHA-256 mismatch — manifest declares "
                f"{expected_sha256}, disk has {actual}. Refusing to proceed "
                "on unverified data."
            )
        verified.append(
            VerifiedFile(
                filename=filename,
                path=path,
                timeframe=timeframe,
                sha256=actual,
                row_count=expected_rows,
            )
        )
    return tuple(verified)


def _epoch_ms_to_utc(time_ms: int) -> datetime:
    # Avoid float division (ms / 1000) precision loss: build the datetime
    # from whole seconds + whole milliseconds via integer arithmetic only.
    seconds, millis = divmod(time_ms, 1000)
    return datetime(1970, 1, 1, tzinfo=UTC) + timedelta(seconds=seconds, milliseconds=millis)


def load_v1a_csv(
    path: Path,
    timeframe: Timeframe,
    *,
    symbol: InternalSymbol = InternalSymbol.XAUUSD,
) -> tuple[NormalizedCandle, ...]:
    """Parse one V1-A raw-OHLC CSV into an ordered tuple of ``NormalizedCandle``.

    Every physical data row becomes exactly one candle. Rows must already be
    in strictly increasing, non-duplicated ``time`` order — this loader
    verifies that and raises rather than silently re-sorting or dropping.
    """
    relative_path = path.name
    raw_bytes = path.read_bytes()
    expected_sha256 = hashlib.sha256(raw_bytes).hexdigest()
    duration = _DURATION[timeframe]

    provenance_id, _ = derive_provenance_id(
        dataset_id=_DATASET_ID,
        dataset_version=_DATASET_VERSION,
        provider=_PROVIDER,
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
        for row_number, row in enumerate(reader, start=2):  # header is physical row 1
            time_ms = int(row["time"])
            event_time_utc = _epoch_ms_to_utc(time_ms)
            if previous_event_time is not None:
                if event_time_utc <= previous_event_time:
                    raise ValueError(
                        f"{relative_path} row {row_number}: time is not strictly "
                        f"increasing ({event_time_utc.isoformat()} follows "
                        f"{previous_event_time.isoformat()})."
                    )
            previous_event_time = event_time_utc

            availability_time_utc = event_time_utc + duration
            open_price = Decimal(row["open"])
            high_price = Decimal(row["high"])
            low_price = Decimal(row["low"])
            close_price = Decimal(row["close"])
            volume_text = row["volume"].strip() if row["volume"] is not None else ""
            volume = Decimal(volume_text) if volume_text != "" else None

            source_record_id = str(time_ms)
            content_fingerprint, _ = derive_content_fingerprint(
                provider=_PROVIDER,
                symbol=symbol,
                timeframe=timeframe,
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
                provider=_PROVIDER,
                symbol=symbol,
                timeframe=timeframe,
                event_time_utc=event_time_utc,
            )
            # raw_candle_id must differ from record_id (structural rule) --
            # derive it with a distinguishing suffix on the same, already-
            # public derive_record_id helper, rather than inventing a new
            # id-derivation scheme.
            raw_candle_id, _ = derive_record_id(
                provenance_id=provenance_id,
                source_record_id=source_record_id + "#raw",
                provider=_PROVIDER,
                symbol=symbol,
                timeframe=timeframe,
                event_time_utc=event_time_utc,
            )

            candle = NormalizedCandle.model_validate(
                {
                    "record_id": record_id,
                    "content_fingerprint": content_fingerprint,
                    "raw_candle_id": raw_candle_id,
                    "provider": _PROVIDER,
                    "source_reference": f"v1a:{relative_path}:{row_number}",
                    "source_symbol": symbol.value,
                    "source_timeframe": timeframe.value,
                    "symbol": symbol,
                    "timeframe": timeframe,
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
                    "rule_version": _SCHEMA_VERSION,
                    "contract_version": _SCHEMA_VERSION,
                    "schema_version": _SCHEMA_VERSION,
                    "provenance_id": provenance_id,
                }
            )
            candles.append(candle)

    return tuple(candles)


def load_dev_only_m15(root: Path) -> tuple[NormalizedCandle, ...]:
    """Load the M15 series and return ONLY the frozen 2903-bar DEV prefix.

    This is the sole function in this module capable of returning M15
    candles for use in characterization, and it structurally cannot hand
    back an OOS row: the OOS slice is computed, asserted against the
    manifest's own declared boundaries, and then discarded — never
    returned, never passed to any caller.
    """
    verified = verify_v1a_manifest_hashes(root)
    full_entry = next(v for v in verified if v.filename == "v1a_raw_ohlc_full_loaded.csv")
    all_m15 = load_v1a_csv(full_entry.path, Timeframe.M15)
    if len(all_m15) != full_entry.row_count:
        raise DevSplitIntegrityError(
            f"expected {full_entry.row_count} M15 rows, loaded {len(all_m15)}."
        )

    fresh = tuple(c for c in all_m15 if c.event_time_utc < ALREADY_USED_BOUNDARY_UTC)
    if len(fresh) != DEV_BAR_COUNT + OOS_BAR_COUNT:
        raise DevSplitIntegrityError(
            f"expected {DEV_BAR_COUNT + OOS_BAR_COUNT} fresh (pre-already-used-window) "
            f"M15 bars, found {len(fresh)}."
        )

    dev = fresh[:DEV_BAR_COUNT]
    # oos is intentionally NOT bound to a name that escapes this function scope
    # beyond the assertions below (fresh[DEV_BAR_COUNT:] is read once, for its
    # length and boundary timestamp only, then discarded).
    oos_len = len(fresh) - DEV_BAR_COUNT
    if oos_len != OOS_BAR_COUNT:
        raise DevSplitIntegrityError(f"expected {OOS_BAR_COUNT} OOS bars, computed {oos_len}.")
    oos_first_event = fresh[DEV_BAR_COUNT].event_time_utc

    if len(dev) != DEV_BAR_COUNT:
        raise DevSplitIntegrityError(f"expected {DEV_BAR_COUNT} DEV bars, got {len(dev)}.")
    if dev[0].event_time_utc != DEV_FIRST_EVENT_UTC:
        raise DevSplitIntegrityError(
            f"DEV first bar event_time_utc {dev[0].event_time_utc.isoformat()} != "
            f"manifest {DEV_FIRST_EVENT_UTC.isoformat()}."
        )
    if dev[-1].event_time_utc != DEV_LAST_EVENT_UTC:
        raise DevSplitIntegrityError(
            f"DEV last bar event_time_utc {dev[-1].event_time_utc.isoformat()} != "
            f"manifest {DEV_LAST_EVENT_UTC.isoformat()}."
        )
    if oos_first_event != OOS_FIRST_EVENT_UTC:
        raise DevSplitIntegrityError(
            f"OOS first bar event_time_utc {oos_first_event.isoformat()} != "
            f"manifest {OOS_FIRST_EVENT_UTC.isoformat()}."
        )

    return dev


def load_context_timeframe_bounded(
    root: Path, timeframe: Timeframe, *, bound_availability_utc: datetime
) -> tuple[NormalizedCandle, ...]:
    """Load a W1/D1/H4/H1 context file, bounded to candles whose own
    ``availability_time_utc`` does not exceed ``bound_availability_utc``.

    Bounding every context timeframe to the DEV window's own final
    availability instant (rather than feeding the whole file, which
    extends through and past the OOS window and the already-used window)
    keeps the entire ``run_scanner_replay`` input set strictly inside DEV
    territory — belt-and-suspenders on top of ``load_dev_only_m15`` already
    never exposing an OOS M15 row.
    """
    verified = verify_v1a_manifest_hashes(root)
    entry = next(v for v in verified if v.timeframe is timeframe and "raw_ohlc_" in v.filename and v.filename != "v1a_raw_ohlc_full_loaded.csv")
    all_candles = load_v1a_csv(entry.path, timeframe)
    if len(all_candles) != entry.row_count:
        raise DevSplitIntegrityError(
            f"{entry.filename}: expected {entry.row_count} rows, loaded {len(all_candles)}."
        )
    return tuple(c for c in all_candles if c.availability_time_utc <= bound_availability_utc)


def load_dev_bounded_context(root: Path) -> dict[Timeframe, tuple[NormalizedCandle, ...]]:
    """Load W1/D1/H4/H1, each bounded to the DEV M15 window's own final
    availability instant (the M15 bar at ``DEV_LAST_EVENT_UTC``'s own
    ``availability_time_utc`` = ``DEV_LAST_EVENT_UTC + 15 minutes``)."""
    bound = DEV_LAST_EVENT_UTC + _DURATION[Timeframe.M15]
    return {
        tf: load_context_timeframe_bounded(root, tf, bound_availability_utc=bound)
        for tf in (Timeframe.W1, Timeframe.D1, Timeframe.H4, Timeframe.H1)
    }


#: Default pre-DEV lookback cap applied by ``load_dev_bounded_context_capped``
#: to each context timeframe's history strictly BEFORE the DEV window starts.
#: See that function's docstring for the full rationale. 250 W1 bars is
#: ~4.8 years of weekly history; 250 D1 is ~8 months; 250 H4 is ~42 days;
#: 250 H1 is ~10.4 days -- all comfortably above every warm-up floor this
#: codebase declares (``historical_backtest.data_quality.warm_up_floor_bars``
#: tops out at 2x the swing-confirmation radius, order of a few dozen bars)
#: and in the same spirit as the project's own prior Pine-side precedent of a
#: BOUNDED (not infinite) BTRC context window (register: P6's
#: ``calc_bars_count`` history-gate work, "P5 accepted, P6 gated" /
#: "P6 compile passed, envelope open").
DEFAULT_PRE_DEV_LOOKBACK_BARS = 250


def load_dev_bounded_context_capped(
    root: Path, *, pre_dev_lookback_bars: int = DEFAULT_PRE_DEV_LOOKBACK_BARS
) -> dict[Timeframe, tuple[NormalizedCandle, ...]]:
    """Load W1/D1/H4/H1 exactly as ``load_dev_bounded_context`` does, but cap
    the portion of each series that falls STRICTLY BEFORE the DEV window's
    own first bar to the most recent ``pre_dev_lookback_bars`` candles.

    WHY THIS EXISTS (a disclosed, deliberate engineering trade-off)
    -------------------------------------------------------------------
    ``run_scanner_replay``'s per-availability-group replay (the ALL-retention
    path the frozen protocol names, and the byte-identical incremental kernel
    this harness drives instead for tractable wall-clock -- see
    ``v1a_harness.py``'s own docstring) re-derives structure/POI/BTMM state
    from the FULL accumulated candle history at every step. Feeding the
    entire loaded history (W1 back to 1970, D1/H4 back to 2023, H1 back to
    2025-01) turned a 2903-bar DEV replay into a many-hour run in this
    project's own prior "kernel is quadratic" finding (register:
    "A2 kernel performance is quadratic" -- 18k bars measured at 51-84h)
    -- independently reconfirmed here empirically before committing to a
    run: an M15-only micro-benchmark on this exact dataset scaled from 50
    bars (0.76s) to 400 bars (55.75s), consistent with the same
    super-linear growth, and adding the full unbounded H1/H4/D1/W1 context
    made even a 50-M15-bar slice fail to return within 10 minutes.

    Capping the PRE-DEV lookback (never the in-DEV-window portion, which is
    always included in full, in strict availability order, with zero
    lookahead) keeps every timeframe's warm-up well above this codebase's
    own warm-up floors and above every timeframe's role in the reused BTRC
    engines (D1/H4/W1 are the trend "authority" set; H1/M15 feed T3
    momentum/breakout/pullback, which read only a local window, not deep
    history) while keeping the full DEV replay tractable to actually run
    inside this task. This is called out explicitly, per the task brief's
    own request to flag judgment calls, rather than silently trimmed.
    """
    full = load_dev_bounded_context(root)
    dev_start = DEV_FIRST_EVENT_UTC
    capped: dict[Timeframe, tuple[NormalizedCandle, ...]] = {}
    for timeframe, candles in full.items():
        pre = [c for c in candles if c.event_time_utc < dev_start]
        during = [c for c in candles if c.event_time_utc >= dev_start]
        capped_pre = pre[-pre_dev_lookback_bars:] if pre_dev_lookback_bars > 0 else []
        capped[timeframe] = tuple(capped_pre) + tuple(during)
    return capped
