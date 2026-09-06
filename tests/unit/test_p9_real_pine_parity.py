"""Real Pine-vs-Python full-system parity for P9 (integration/parity work
only -- see `BTRC_V1_P9_FULL_SYSTEM_PARITY_CLOSURE.md` for the campaign
context; this test changes no semantics anywhere).

One real, live-captured FXCM (FX:XAUUSD, M15) log is used:
`artifacts/p9_capture/p9_dev_raw_log.csv`, a `BTMM + POI + BTRC Scanner
[P9 DEV]` capture with BOTH `p9DebugLog` and `p8DebugLog` enabled, carrying
`P9TRACE` (one row per POI per bar, for every POI in the P5 active-POI set
that bar) and `P8EVENT` (Pine's own real fired alert events) interleaved.
TradingView's Pine Logs -> Download logs caps the download at ~10000 rows,
so this is a REAL but TRUNCATED window (103 bars, 9537 P9TRACE rows, 456
P8EVENT rows) -- not the full 1800-bar calc window. The file is gitignored
(`artifacts/`); every test here is skipped when it is absent.

SEEDING / FIRST-BAR-EXCLUSION DECISION
------------------------------------------------------------------------
`P9IntegratedState.advance_bar`'s FIRST call silently primes its internal
`AlertEngine` (`p9_integrated_model.py:184-187`) -- exactly the P8
precedent's `prime()` contract: no events possible on that call. This
replay therefore treats this capture's first bar as that priming call and
excludes it from every comparison below, mirroring
`test_p8_real_pine_parity.py`'s own `pine_events_excl_first_bar`.

Beyond events, P9 also delegates ELIGIBILITY (and therefore
`p7_visible`/`p7z_visible`) to `p5_active_poi_loop_model.resolve_eligible_
and_next` via `P7DisplayState`/`P7ZDisplayState` (both instantiated fresh,
with `self._previously_active = frozenset()`, inside `P9IntegratedState.
__init__`). That function's contract
(`p5_active_poi_loop_model.py:106-114`):

    available      = known_ids or frozenset(status_by_id)
    non_terminal_now = {id: status is not TERMINAL}
    eligible_ids   = (previously_active_ids | non_terminal_now) & available

On a FRESH state's first `advance_bar` call, `previously_active_ids` is
`frozenset()`, so `eligible_ids_bar1 = non_terminal_now & available`. Since
`available` is built from the SAME bar's `inputs_by_idx` keys (i.e. exactly
the POIs this capture's `P9TRACE` already logged as bar 1's real
`p7PoiIdx` active set -- P9TRACE only ever logs POIs Pine itself considers
active), the two sides differ ONLY if some bar-1 row has `terminal=true`:
such a POI is excluded from `non_terminal_now`, and -- with no real
`previously_active_ids` carried in from before this truncated window --
Python's fresh replay would compute it as NOT eligible even though Pine's
real (non-fresh) engine plainly DID include it (it is right there in the
capture). This is a genuine, evidence-based divergence *class*, not a
theoretical one: it is exactly the mechanism the P7-Z terminal-grace-bar
docstring describes (`p7z_zone_model.py:23-35`), and a fresh Python replay
cannot reconstruct a "previous bar" it never observed.

Empirically, THIS particular capture's bar 1 (bar_ms=1788459300000, 64
rows) has zero rows with `terminal=true` (verified directly against the
raw capture before this test was written), so the divergence class above
happens not to fire in practice here. The exclusion is kept anyway,
un-conditionally, for the same reason `test_p8_real_pine_parity.py` excludes
its own first bar outright rather than special-casing "only if it would
have mattered": bar 1's true eligibility set can never be independently
verified against Pine's real (pre-window) state from this capture alone,
so it is not a fair comparison point regardless of whether this specific
window happens to dodge the edge case. Both EVENTS and the full `P9Record`
field comparison exclude bar 1 for this reason.

WHY NO "KNOWN BEFORE THE WINDOW" EXTRA SEEDING (UNLIKE P8's TEST) --
CONFIRMED, NOT JUST THEORETICAL
------------------------------------------------------------------------
`test_p8_real_pine_parity.py` seeds `AlertEngine._known` /
`_prev_btmm_valid` / `_prev_permission` from a SECOND, wider capture
reaching back weeks before its raw capture's own first bar, because a POI
absent from bar 1 but re-entering later in the window would otherwise look
"new" to a Python replay that only primed from bar 1, even though Pine's
real, non-fresh `AlertEngine` already knew it. P9 has no second, wider
capture available -- inventing "known before window" facts is explicitly
disallowed by this campaign's own rules. This replay therefore seeds
`P9IntegratedState`'s internal `AlertEngine` ONLY from what this ONE
capture's first bar itself shows (via `advance_bar`'s own silent first-call
priming).

This is not a hypothetical gap: running the naive strict replay against
this real capture surfaces it directly. Of the 81 (bar, poiIdx) pairs where
a POI appears for the first time within the window at some bar OTHER than
the priming bar, exactly 24 disagree with Pine's real event stream -- in
EVERY case the Python replay spuriously emits `POI_ACTIVATED` (+
`BTMM_VALIDATED`, sometimes also `PERMISSION_ENTERED_ACTIONABLE`, all on
that same first-seen bar) for a POI Pine's real engine fires nothing for.
Registry-index inspection confirms the root cause exactly: the 24
mismatching indices (513-620) are scattered, non-sequential, low values --
genuinely pre-existing POIs that were simply outside the active/eligible
set at bar 1 and re-entered it later. The other 57 first-appearance keys
(indices 904-960, strictly sequential and contiguous, i.e. freshly
registered live during the capture window itself) agree exactly on both
sides -- Python correctly identifies these as genuinely new. No mismatch
of any OTHER kind was found: every scalar field (`zone_top`, `zone_bottom`,
`terminal`, `btmm_valid`, `final_score`, `permission`, `lifecycle`,
`p7_visible`, `p7z_visible`, ...) matches exactly for all 9536
non-priming-bar records, including all 81 ambiguous ones -- the ambiguity
is structurally confined to `event_types` at a POI's first observed bar,
exactly as `resolve_eligible_and_next`'s algebra predicts (a fresh
`previously_active_ids` cannot distinguish "genuinely new" from
"pre-existing, briefly inactive" -- and neither can `AlertEngine._known`,
seeded the same way).

Per this campaign's own instruction, the honest resolution is NOT to
invent seed data to erase this (there is nothing to seed it from), and NOT
to silently drop the comparison broadly -- it is to define, MECHANICALLY
and BEFORE looking at any comparison result, exactly which (bar, poiIdx)
keys are structurally unverifiable (`_first_appearance_keys` below: a
POI's first bar in the window, at a bar other than the priming bar, for a
POI absent from the priming bar's own snapshot) and exclude ONLY
`event_types` on ONLY those keys from the strict-equality assertions,
while still requiring every other field, and every other key's
`event_types`, to match exactly with zero tolerance. The excluded set's
size (81) and its exact mismatch count within it (24) are asserted
directly below specifically so a future capture, or a future change to any
of the three delegated sub-models, that shifts this count is caught and
re-investigated rather than silently re-absorbed into "the known
limitation."

TIER/ALIGN PLACEHOLDER
------------------------------------------------------------------------
`P9TRACE` does not log `poiTier`/`poiAlign` (by design). Verified before
writing this test, by direct inspection of all three closed sub-models P9
delegates to:

* `p7_ui_display_model.py` -- `tier`/`align` are fields on `PoiDecision`
  (lines 60/62) but `render_bar`/`P7DisplayState.advance_bar` never branch
  on either; only `resolve_eligible_and_next`'s terminal/active-set algebra
  and `sorted(eligible_ids)[:max_visible]` decide visibility.
* `p7z_zone_model.py` -- has no `align` field anywhere; `tier` (line 121)
  is read only inside `zone_label()` (lines 97-106) to append the
  `"• STRONG"` display suffix -- never in `advance_bar`'s eligibility,
  creation, extension, or eviction logic.
* `p8_alert_oracle.py` -- has no `align` field anywhere; `tier` (lines
  112/136) is a pure pass-through on `PoiSnapshot`/`AlertEvent`, forwarded
  into the emitted event for display only -- `AlertEngine.process` never
  reads it in any branch (only `btmm_valid`/`permission`/`terminal`/
  `poi_idx` drive transitions).

And `P9Record` itself (`p9_integrated_model.py:78-98`) carries neither
`tier` nor `align` as an output field. The placeholder value `0` passed for
both in `P9BarInput` below is therefore inert for every comparison this
test performs -- it cannot influence `p7_visible`, `p7z_visible`,
`event_types`, or any other compared field.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.parity_support.p9_capture_log import P9Capture, P9TraceRow, parse_p9_capture
from tests.parity_support.p9_digest import integrated_digest
from tests.parity_support.p9_integrated_model import (
    P9BarInput,
    P9IntegratedState,
    P9Record,
)

_REPO = Path(__file__).resolve().parents[2]
_CAPTURE = _REPO / "artifacts" / "p9_capture" / "p9_dev_raw_log.csv"

pytestmark = pytest.mark.skipif(
    not _CAPTURE.exists(), reason=f"real P9 capture not present: {_CAPTURE.name}"
)

#: The real capture's host chart timeframe (`BTMM + POI + BTRC Scanner
#: [P9 DEV]` on FX:XAUUSD, M15 -- see module docstring). `P9Record.
#: origin_tf` is the fixed host timeframe (never per-POI), so it is a
#: replay/reconstruction constant, not something either side "computes".
_TIMEFRAME = "M15"

#: The real P9 DEV script's own `input.int` defaults
#: (`tradingview/btmm_poi_btrc_scanner_p9_dev.pine:5690,5717`) -- must match
#: what actually produced this capture's `p7Visible`/`p7zVisible` flags, or
#: a cap mismatch alone (nothing to do with real parity) would show up as a
#: spurious visibility divergence.
_P7_MAX_VISIBLE = 8
_P7Z_MAX_VISIBLE = 12


def _to_bar_input(row: P9TraceRow) -> P9BarInput:
    return P9BarInput(
        idx=row.poi_idx,
        poi_type=row.poi_type,
        direction=row.direction,
        zone_top=row.zone_top,
        zone_bottom=row.zone_bottom,
        avail_time_ms=row.avail_time_ms,
        tier=0,  # placeholder -- see module docstring "TIER/ALIGN PLACEHOLDER"
        terminal=row.terminal,
        btmm_valid=row.btmm_valid,
        align=0,  # placeholder -- see module docstring "TIER/ALIGN PLACEHOLDER"
        final_score=row.final_score,
        permission=row.permission,
        lifecycle=row.lifecycle,
    )


def _events_by_key(capture: P9Capture) -> dict[tuple[int, int], frozenset[str]]:
    out: dict[tuple[int, int], frozenset[str]] = {}
    for e in capture.events:
        key = (e.bar_ms, e.poi_idx)
        out[key] = out.get(key, frozenset()) | {e.event_type}
    return out


def _python_replay(capture: P9Capture, bars_sorted: list[int]) -> dict[tuple[int, int], P9Record]:
    state = P9IntegratedState(
        p7_max_visible=_P7_MAX_VISIBLE,
        p7z_max_visible=_P7Z_MAX_VISIBLE,
        timeframe=_TIMEFRAME,
    )
    by_key: dict[tuple[int, int], P9Record] = {}
    for i, bar_ms in enumerate(bars_sorted):
        inputs_by_idx = {row.poi_idx: _to_bar_input(row) for row in capture.trace_by_bar[bar_ms]}
        records = state.advance_bar(bar_ms, inputs_by_idx)
        if i == 0:
            continue  # priming bar -- see module docstring
        for r in records:
            by_key[(r.bar_ms, r.idx)] = r
    return by_key


def _pine_reconstructed(
    capture: P9Capture, bars_sorted: list[int]
) -> dict[tuple[int, int], P9Record]:
    """`P9Record`s built directly from the capture's own `P9TRACE` rows,
    with `event_types` independently cross-checked against grouped
    `P8EVENT` rows for the same (bar, poiIdx) -- never derived from the
    Python replay."""
    events_by_key = _events_by_key(capture)
    by_key: dict[tuple[int, int], P9Record] = {}
    for i, bar_ms in enumerate(bars_sorted):
        if i == 0:
            continue  # priming bar -- see module docstring
        for row in capture.trace_by_bar[bar_ms]:
            key = (bar_ms, row.poi_idx)
            event_types = tuple(sorted(events_by_key.get(key, frozenset())))
            by_key[key] = P9Record(
                bar_ms=row.bar_ms,
                idx=row.poi_idx,
                poi_type=row.poi_type,
                direction=row.direction,
                origin_tf=_TIMEFRAME,
                zone_top=row.zone_top,
                zone_bottom=row.zone_bottom,
                avail_time_ms=row.avail_time_ms,
                terminal=row.terminal,
                btmm_valid=row.btmm_valid,
                final_score=row.final_score,
                permission=row.permission,
                lifecycle=row.lifecycle,
                p7_visible=row.p7_visible,
                p7z_visible=row.p7z_visible,
                event_types=event_types,
            )
    return by_key


def _first_appearance_keys(
    capture: P9Capture, bars_sorted: list[int], first_bar: int
) -> frozenset[tuple[int, int]]:
    """(bar_ms, poiIdx) for every POI's first appearance in the window at a
    bar OTHER than the priming bar, for a POI that was NOT present in the
    priming bar's own snapshot -- computed purely mechanically from the
    capture's own POI-index membership per bar, before looking at any
    comparison result. See module docstring "WHY NO 'KNOWN BEFORE THE
    WINDOW' EXTRA SEEDING" for why `event_types` cannot be verified for
    exactly these keys."""
    seen = {row.poi_idx for row in capture.trace_by_bar[first_bar]}
    keys: set[tuple[int, int]] = set()
    for bar_ms in bars_sorted:
        if bar_ms == first_bar:
            continue
        ids_this_bar = {row.poi_idx for row in capture.trace_by_bar[bar_ms]}
        for idx in ids_this_bar - seen:
            keys.add((bar_ms, idx))
        seen |= ids_this_bar
    return frozenset(keys)


def _load() -> tuple[P9Capture, list[int], int]:
    text = _CAPTURE.read_text(encoding="utf-8")
    capture = parse_p9_capture(text)
    bars_sorted = sorted(capture.trace_by_bar.keys())
    return capture, bars_sorted, bars_sorted[0]


def test_capture_is_a_substantial_real_window() -> None:
    capture, bars_sorted, first_bar = _load()
    assert len(bars_sorted) >= 100, "expected a substantial real capture"
    pine_events_excl_first_bar = [e for e in capture.events if e.bar_ms != first_bar]
    assert len(pine_events_excl_first_bar) > 0, (
        "expected real Pine events beyond the first (unverifiable) bar"
    )


_SCALAR_FIELDS = (
    "bar_ms",
    "idx",
    "poi_type",
    "direction",
    "origin_tf",
    "zone_top",
    "zone_bottom",
    "avail_time_ms",
    "terminal",
    "btmm_valid",
    "final_score",
    "permission",
    "lifecycle",
    "p7_visible",
    "p7z_visible",
)

#: Real, capture-derived counts (see module docstring "WHY NO 'KNOWN
#: BEFORE THE WINDOW' EXTRA SEEDING"), asserted directly so any future
#: change to the capture file or any of the three delegated sub-models
#: that shifts either count is caught and re-investigated rather than
#: silently re-absorbed into "the known limitation".
_EXPECTED_UNVERIFIABLE_KEY_COUNT = 81
_EXPECTED_UNVERIFIABLE_EVENT_MISMATCH_COUNT = 24


def test_first_appearance_ambiguity_is_confined_exactly_to_event_types() -> None:
    """Direct evidence for the module docstring's claim: within the 81
    structurally-unverifiable (bar, poiIdx) keys, the Python replay and
    Pine's real capture disagree on `event_types` for exactly 24 of them
    (all traced to registry indices 513-620 -- pre-existing POIs re-
    entering the active set -- never the 57 sequentially-registered
    904-960 indices genuinely born during the window), and disagree on NO
    scalar field for ANY of the 81."""
    capture, bars_sorted, first_bar = _load()
    unverifiable = _first_appearance_keys(capture, bars_sorted, first_bar)
    assert len(unverifiable) == _EXPECTED_UNVERIFIABLE_KEY_COUNT

    python_by_key = _python_replay(capture, bars_sorted)
    pine_by_key = _pine_reconstructed(capture, bars_sorted)

    scalar_mismatches: list[str] = []
    event_mismatch_keys: list[tuple[int, int]] = []
    for key in sorted(unverifiable):
        py_rec = python_by_key[key]
        pine_rec = pine_by_key[key]
        for field in _SCALAR_FIELDS:
            py_val = getattr(py_rec, field)
            pine_val = getattr(pine_rec, field)
            if py_val != pine_val:
                scalar_mismatches.append(f"{key} field={field!r} python={py_val!r} pine={pine_val!r}")
        if frozenset(py_rec.event_types) != frozenset(pine_rec.event_types):
            event_mismatch_keys.append(key)

    assert scalar_mismatches == [], scalar_mismatches
    assert len(event_mismatch_keys) == _EXPECTED_UNVERIFIABLE_EVENT_MISMATCH_COUNT, (
        event_mismatch_keys
    )
    for bar_ms, idx in event_mismatch_keys:
        assert 513 <= idx <= 620, (bar_ms, idx)


def test_real_pine_and_python_records_match_exactly() -> None:
    """Every field of every (bar_ms, poiIdx) record beyond the priming bar
    must match exactly, EXCEPT `event_types` on the mechanically-defined,
    structurally-unverifiable first-appearance keys (see module docstring
    and `test_first_appearance_ambiguity_is_confined_exactly_to_event_
    types`, which independently proves that carve-out is real and narrow,
    not a blanket weakening)."""
    capture, bars_sorted, first_bar = _load()

    python_by_key = _python_replay(capture, bars_sorted)
    pine_by_key = _pine_reconstructed(capture, bars_sorted)
    unverifiable = _first_appearance_keys(capture, bars_sorted, first_bar)

    assert set(python_by_key) == set(pine_by_key), (
        "the set of (bar_ms, poiIdx) records compared must match exactly "
        f"-- python only: {set(python_by_key) - set(pine_by_key)!r}, "
        f"pine only: {set(pine_by_key) - set(python_by_key)!r}"
    )
    assert len(python_by_key) > 0

    mismatches: list[str] = []
    for key in sorted(python_by_key):
        py_rec = python_by_key[key]
        pine_rec = pine_by_key[key]
        for field in _SCALAR_FIELDS:
            py_val = getattr(py_rec, field)
            pine_val = getattr(pine_rec, field)
            if py_val != pine_val:
                mismatches.append(
                    f"(bar_ms={key[0]}, idx={key[1]}) field={field!r} "
                    f"python={py_val!r} pine={pine_val!r}"
                )
        if key in unverifiable:
            continue  # see module docstring -- event_types unverifiable for these keys only
        py_events = frozenset(py_rec.event_types)
        pine_events = frozenset(pine_rec.event_types)
        if py_events != pine_events:
            mismatches.append(
                f"(bar_ms={key[0]}, idx={key[1]}) field='event_types' "
                f"python={sorted(py_events)!r} pine={sorted(pine_events)!r}"
            )

    assert mismatches == [], (
        f"{len(mismatches)} field mismatch(es); first: {mismatches[0]}\n"
        + "\n".join(mismatches[:20])
    )


def test_real_pine_and_python_digests_match() -> None:
    """Digest over the fully-verifiable record subset: every (bar_ms,
    poiIdx) key beyond the priming bar, EXCLUDING the mechanically-defined
    unverifiable first-appearance keys entirely from BOTH sequences (same
    reasoning, one level narrower, as excluding the priming bar itself --
    see module docstring)."""
    capture, bars_sorted, first_bar = _load()

    python_by_key = _python_replay(capture, bars_sorted)
    pine_by_key = _pine_reconstructed(capture, bars_sorted)
    unverifiable = _first_appearance_keys(capture, bars_sorted, first_bar)

    verifiable_keys = sorted(set(python_by_key) - unverifiable)
    assert len(verifiable_keys) > 0

    python_records = [python_by_key[k] for k in verifiable_keys]
    pine_records = [pine_by_key[k] for k in verifiable_keys]

    python_digest = integrated_digest(python_records)
    pine_digest = integrated_digest(pine_records)
    assert python_digest == pine_digest, (
        f"python digest {python_digest} != pine digest {pine_digest}"
    )
