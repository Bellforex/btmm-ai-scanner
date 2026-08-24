"""Repository safety guards for the P1 Pine measurements source.

These are static invariants over ``tradingview/btmm_poi_btrc_scanner_v1.pine`` —
NOT a substitute for TradingView compilation (see the P1 doc for the manual
compile gate). They exist to catch regressions that would silently turn the
analytical scanner into an execution strategy, add repainting lookahead, or drop
the non-repaint gate. Comment lines are stripped before the forbidden-token
checks so that the file's own documentation (which names the forbidden tokens to
say it avoids them) does not trip the guards.
"""

import re
from pathlib import Path

_PINE_PATH = (
    Path(__file__).resolve().parents[2]
    / "tradingview"
    / "btmm_poi_btrc_scanner_v1.pine"
)

# ``for <v> = <start> to array.size(<x>) - 1`` — the counted form that fires
# ``array.get(<x>, <start>)`` on an empty array (see the loop-direction guards).
_COUNTED_ARRAY_LOOP = re.compile(
    r"^\s*for\s+\w+\s*=\s*(?P<start>.+?)\s+to\s+array\.size\(\s*(?P<arr>\w+)\s*\)\s*-\s*1\s*$"
)
# ``int x = na`` / ``var float y = na`` — scalars whose initial state is na.
_NA_DECLARATION = re.compile(
    r"^\s*(?:var\s+)?(?:int|float|bool|string)\s+(?P<name>\w+)\s*=\s*na\s*$"
)


def _source() -> str:
    return _PINE_PATH.read_text(encoding="utf-8")


def _code_lines() -> list[str]:
    """Code-only lines (comment tails stripped), indices aligned to the file."""
    return _code_only(_source()).splitlines()


def _code_only(source: str) -> str:
    """Return the source with ``//`` comment tails removed (line by line).

    A naive split on ``//`` is safe here because the Pine source contains no
    string literal that embeds ``//`` — the guards below would need revisiting
    only if that ever changes.
    """
    lines: list[str] = []
    for line in source.splitlines():
        head = line.split("//", 1)[0]
        lines.append(head)
    return "\n".join(lines)


def test_pine_source_exists() -> None:
    assert _PINE_PATH.is_file(), f"missing Pine source at {_PINE_PATH}"


def test_pine_declares_version_6() -> None:
    assert _source().lstrip().startswith("//@version=6")


def test_pine_is_indicator_not_strategy() -> None:
    code = _code_only(_source())
    assert "indicator(" in code
    assert "strategy(" not in code


def test_pine_has_no_execution_calls() -> None:
    code = _code_only(_source())
    forbidden = (
        "strategy.entry",
        "strategy.order",
        "strategy.exit",
        "strategy.close",
        "strategy.cancel",
    )
    present = [token for token in forbidden if token in code]
    assert not present, f"execution calls present in Pine source: {present}"


def test_pine_has_no_lookahead_or_multitimeframe() -> None:
    code = _code_only(_source())
    # P1 is single-chart, non-repaint: no security requests, no lookahead.
    assert "request.security" not in code
    assert "lookahead" not in code
    assert "barmerge.lookahead_on" not in code


def test_pine_gates_confirmed_state_on_closed_bars() -> None:
    # The non-repaint contract: confirmed analytical state advances only under a
    # barstate.isconfirmed gate.
    assert "barstate.isconfirmed" in _code_only(_source())


def test_pine_exposes_parity_plots() -> None:
    code = _code_only(_source())
    for key in (
        "P1_swing_high_price",
        "P1_swing_low_price",
        "P1_disp_code",
        "P1_equal_high",
        "P1_equal_low",
    ):
        assert key in code, f"missing parity output {key}"


# ---------------------------------------------------------------------------
# Swing confirmation: absent prior confirmed type (swings.py:221/228).
#
# Python seeds ``last_confirmed_type = None`` and skips a pivot only when
# ``pivot.swing_type == last_confirmed_type``; against None that is False, so the
# FIRST eligible pivot always proceeds. Pine seeds the analogue to ``na``, and a
# bare ``!=`` against an na int evaluates to na (falsy) — which permanently
# blocked the first confirmation, yielding zero swings on every timeframe and
# emptying every downstream detector. The alternation rule itself is unchanged;
# only the initial-state comparison is made explicit.
# ---------------------------------------------------------------------------


def test_pine_seeds_last_confirmed_type_as_na() -> None:
    code = _code_only(_source())
    assert "int lastConfirmedType = na" in code, (
        "the swing confirmation alternation state must still be seeded absent"
    )


def test_pine_first_confirmation_not_blocked_by_absent_prior_type() -> None:
    """Every comparison against ``lastConfirmedType`` must be na-guarded."""
    offenders: list[tuple[int, str]] = []
    for number, line in enumerate(_code_lines(), start=1):
        if "lastConfirmedType" not in line:
            continue
        if "!=" not in line and "==" not in line:
            continue  # declaration / assignment, not a gate
        if "na(lastConfirmedType)" not in line:
            offenders.append((number, line.strip()))
    assert not offenders, (
        "swing confirmation compares lastConfirmedType without an explicit "
        "na() guard, so the first pivot can never confirm (swings.py:228): "
        f"{offenders}"
    )


def test_pine_na_seeded_scalars_are_na_guarded_where_compared() -> None:
    """Comparisons against na-seeded scalars need a nearby explicit ``na()``.

    Bounded heuristic, not a Pine parser: the guard may name a partner scalar
    rather than the compared one, because this source seeds and assigns some
    state in pairs (e.g. lastSwingCount / lastSwingConfTime), where guarding the
    partner is sufficient. That still catches the failure class above, where no
    ``na()`` call appears anywhere near the comparison.
    """
    lines = _code_lines()
    na_names = {
        match.group("name")
        for match in (_NA_DECLARATION.match(line) for line in lines)
        if match is not None
    }
    assert "lastConfirmedType" in na_names, "expected na-seeded scalars to be found"

    offenders: list[tuple[int, str]] = []
    for index, line in enumerate(lines):
        if "!=" not in line and "==" not in line:
            continue
        if _NA_DECLARATION.match(line):
            continue
        # The name must be an OPERAND of the comparison — not merely present as
        # a call argument (``array.get(x, bestRel)``), an assignment target
        # (``ratio := ...``), or a UDT field access (``sr.zoneTop``).
        compared = [
            name
            for name in na_names
            if re.search(
                rf"(?<![\w.]){re.escape(name)}\s*(?:==|!=)"
                rf"|(?:==|!=)\s*{re.escape(name)}(?![\w.(])",
                line,
            )
        ]
        if not compared:
            continue
        window = lines[max(0, index - 5) : index + 1]
        if not any("na(" in candidate for candidate in window):
            offenders.append((index + 1, line.strip()))
    assert not offenders, (
        f"na-seeded scalar compared without any nearby na() guard: {offenders}"
    )


# ---------------------------------------------------------------------------
# Pine loop direction (RE10045).
#
# Pine's ``for i = a to b`` counts DOWN when a > b instead of yielding zero
# iterations like Python's ``for x in list`` / ``range(len(x))``. So
# ``for i = 0 to array.size(x) - 1`` executes ``array.get(x, 0)`` on an empty
# array; ``for a = 1 to size - 1`` breaks at size 0 AND 1; and
# ``for j = i + 1 to size - 1`` runs in reverse when i is the last element. The
# safe form is ``for [i, elem] in x``, which yields zero iterations when empty.
# ---------------------------------------------------------------------------


def test_pine_counted_array_loops_are_nonempty_guarded() -> None:
    """Counted ``to array.size(x) - 1`` loops need an explicit nonempty guard."""
    lines = _code_lines()
    offenders: list[tuple[int, str]] = []
    for index, line in enumerate(lines):
        match = _COUNTED_ARRAY_LOOP.match(line)
        if match is None:
            continue
        array_name = match.group("arr")
        window = lines[max(0, index - 3) : index]
        guarded = any(
            re.search(
                rf"array\.size\(\s*{re.escape(array_name)}\s*\)\s*(?:>\s*0|>=\s*1)",
                candidate,
            )
            for candidate in window
        )
        if not guarded:
            offenders.append((index + 1, line.strip()))
    assert not offenders, (
        "counted loop over an array with no preceding nonempty guard — Pine "
        "runs it in reverse when the array is empty (RE10045); use "
        f"`for [i, elem] in <array>` instead: {offenders}"
    )


def test_pine_has_no_offset_start_counted_array_loops() -> None:
    """Offset-start counted array loops must use the ``for ... in`` form.

    ``for a = 1 to size - 1`` (insertion sorts) and ``for j = i + 1 to size - 1``
    (nested pair scans) stay broken even under a ``size > 0`` guard, so they are
    rejected outright rather than guarded.
    """
    offenders: list[tuple[int, str]] = []
    for number, line in enumerate(_code_lines(), start=1):
        match = _COUNTED_ARRAY_LOOP.match(line)
        if match is None:
            continue
        start = match.group("start").strip()
        if start != "0":
            offenders.append((number, line.strip()))
    assert not offenders, (
        "offset-start counted array loop; use `for [i, elem] in <array>` with a "
        f"`continue` guard for the skipped prefix: {offenders}"
    )


# ---------------------------------------------------------------------------
# P1-PERF-1 — architectural performance invariants.
#
# The port originally re-derived the entire measurement pipeline over the whole
# rolling window on every confirmed historical bar, which exhausted TradingView's
# per-script time budget (RE10110) on M1/H1/D1. The guards below pin the shape of
# the optimisation so a later edit cannot quietly reintroduce the quadratic work.
# They are structural, not stylistic: each one matches on a token or an
# assignment, never on indentation or spacing.
# ---------------------------------------------------------------------------


def _next_code_line(lines: list[str], index: int) -> str:
    """First non-blank code line strictly after ``index`` (or '' at the end)."""
    for candidate in lines[index + 1 :]:
        if candidate.strip():
            return candidate.strip()
    return ""


def test_pine_pivot_detection_is_incremental() -> None:
    """Single-candle pivots must be maintained by a frontier, not rescanned.

    A pivot's verdict is final once it has C_WINDOW_RADIUS closed bars to its
    right, so re-deriving every window index on every bar recomputed an identical
    answer O(window) times over.
    """
    code = _code_only(_source())
    assert "f_advancePivotFrontier" in code, (
        "the incremental single-candle pivot frontier is missing"
    )
    assert "for idx = C_WINDOW_RADIUS to n - C_WINDOW_RADIUS - 1" not in code, (
        "the full-window single-candle pivot rescan has been reintroduced"
    )


def test_pine_pivot_frontier_state_is_persistent() -> None:
    """The frontier only works if its state survives across bars."""
    code = _code_only(_source())
    for declaration in (
        "var int confirmedBarCount",
        "var array<int>   pvAbs",
        "var array<int>   pvType",
        "var array<float> pvPrice",
        "var array<float> pvAtr",
        "var array<float> pvTie",
    ):
        assert declaration in code, f"missing persistent frontier state: {declaration}"


def test_pine_reversal_search_starts_at_its_lower_bound() -> None:
    """The meaningful-reversal scan must not walk the window from index 0.

    ``for [j, _] in lows`` + ``if j < searchStart: continue`` visited ~W/2 dead
    indices per candidate pivot before reaching the first usable one. Python's
    ``range(search_start, n)`` starts where it means to.
    """
    offenders = [
        (number, line.strip())
        for number, line in enumerate(_code_lines(), start=1)
        if "j < searchStart" in line
    ]
    assert not offenders, (
        "reversal-confirmation search re-walks the window from index 0 instead of "
        f"starting at searchStart: {offenders}"
    )


def test_pine_existence_scans_short_circuit() -> None:
    """First-match / existence scans must stop once the answer is fixed.

    Each of these assignments settles its scan's result; continuing to iterate
    afterwards cannot change the outcome and was a large share of the S/R and
    trendline cost.
    """
    settling_assignments = (
        "reactionStart := i",
        "integrityOk := false",
        "confTime := touch.meaningfulConfTime",
        "confIdx := j",
    )
    lines = _code_lines()
    offenders: list[tuple[int, str]] = []
    for index, line in enumerate(lines):
        stripped = line.strip()
        if not any(stripped == assignment for assignment in settling_assignments):
            continue
        window = [
            candidate.strip()
            for candidate in lines[index + 1 : index + 4]
            if candidate.strip()
        ]
        if "break" not in window[:3]:
            offenders.append((index + 1, stripped))
    assert not offenders, (
        "scan result is settled but the loop keeps iterating — add a `break`: "
        f"{offenders}"
    )


def _swing_change_gate_index(lines: list[str]) -> int:
    """Index of the gate that actually guards the SWING-DERIVED detectors.

    Anchored to the equal-levels call and searched backwards, not to the first
    textual ``if changed``: P1-SR-PERF-3 added a separate swing-keyed gate for
    candidate/fold reconciliation which legitimately runs before S/R publishes,
    and a first-match heuristic would mistake it for this one.
    """
    call = next(
        index
        for index, line in enumerate(lines)
        if "f_detectEqualLevels(" in line and not line.strip().startswith("f_")
    )
    for index in range(call, -1, -1):
        if lines[index].strip() == "if changed":
            return index
    raise AssertionError("the swing-derived detector gate is missing")


def _call_sites(lines: list[str], call: str) -> list[int]:
    """Invocation lines for a Pine function, excluding its own definition."""
    sites = [
        index
        for index, line in enumerate(lines)
        if call in line and not line.strip().startswith("f_")
    ]
    assert sites, f"missing call site for {call}"
    return sites


def test_pine_swing_derived_detectors_stay_behind_the_change_gate() -> None:
    """Equal levels and trendlines must not run unconditionally per bar.

    Both are pure functions of the confirmed-swing set — a trendline's
    confirmation comes from a touch SWING, not from a bar — so the swing-set
    fingerprint is a sound gate for them. S/R is deliberately excluded; see
    ``test_pine_support_resistance_is_not_gated_on_swing_change``.
    """
    lines = _code_lines()
    gate = _swing_change_gate_index(lines)
    for call in ("f_detectEqualLevels(", "f_detectTrendlines("):
        assert all(index > gate for index in _call_sites(lines, call)), (
            f"{call} is invoked outside the swing-set change gate"
        )


def test_pine_change_gate_covers_the_whole_swing_set() -> None:
    """A same-length reshuffle must invalidate the cached derived state.

    The window's left edge re-seeds the alternation chain every bar, so a change
    can land in the MIDDLE of the swing list with the count and the last
    confirmation time both unchanged.
    """
    code = _code_only(_source())
    assert "lastSwingFingerprint" in code, (
        "the change gate no longer fingerprints the whole swing set"
    )
    assert "newFingerprint != lastSwingFingerprint" in code, (
        "the fingerprint is computed but not compared"
    )


def test_pine_median_does_not_copy_per_call() -> None:
    """Medians run inside the hot path; they must not allocate a copy each time."""
    code = _code_only(_source())
    assert "array.copy(" not in code, (
        "array.copy in the Pine source — the median helpers consume a "
        "caller-owned array instead of copying"
    )
    assert "f_medianConsume(" in code, "the consuming median helper is missing"


def test_pine_debug_table_is_built_only_in_debug_mode() -> None:
    """Instrumentation must not allocate in normal client-style mode."""
    lines = _code_lines()
    offenders: list[tuple[int, str]] = []
    for index, line in enumerate(lines):
        if "table.new(" not in line:
            continue
        window = lines[max(0, index - 3) : index]
        if not any("debugMode" in candidate for candidate in window):
            offenders.append((index + 1, line.strip()))
    assert not offenders, (
        f"table.new reached without a debugMode guard above it: {offenders}"
    )


def test_pine_analytical_window_default_is_unchanged() -> None:
    """B17: performance must come from algorithmic work, not a shorter window.

    Shrinking `lookbackWindow` changes which records the port can reproduce, so it
    is a semantic change and needs its own equivalence analysis — not a perf knob.
    """
    code = _code_only(_source())
    assert 'input.int(300, "Analytical window' in code, (
        "the provisional 300-bar analytical window default was changed; that is a "
        "semantic change, not a performance optimisation"
    )


# ---------------------------------------------------------------------------
# P1-CLOSEOUT (C1) — support/resistance must advance on candle growth alone.
#
# domain/support_resistance.py:80 searches `range(search_start_index, n)` for the
# reaction start, and `n` grows with every candle, so a reaction can first
# satisfy its gate on a candle that introduces no new swing. The Python
# incremental analyzer says so outright at analyzer.py:923 — "Must run every
# candle (not only when confirmed_swings changes): a reaction's bounded window
# can newly resolve purely from candle growth with no new swing involved."
#
# Gating the Pine S/R detector on the swing-set fingerprint therefore delayed a
# real state transition until the next swing mutation. These guards pin the
# corrected wiring. The behavioural proof against the production Python
# implementation lives in test_pine_p1_sr_candle_growth_semantics.py.
# ---------------------------------------------------------------------------


def test_pine_support_resistance_advances_outside_the_swing_change_gate() -> None:
    """C1.6-A/C: unresolved reactions must advance on every confirmed bar.

    An unresolved reaction has to be able to advance — and an already-resolved
    one has to be able to publish — without waiting for the swing set to mutate.
    P1-SR-PERF-2 does that by advancing trackers unconditionally; only the walk
    over the resolved set is event-gated.
    """
    lines = _code_lines()
    gate = _swing_change_gate_index(lines)
    main_sites = [
        index
        for index in _call_sites(lines, "f_advanceSRTracker(")
        if "f_srTrackerIndex" not in lines[index]
        and not lines[index].lstrip().startswith("SRTracker advanced")
    ]
    assert main_sites, "the per-bar tracker advance is missing"
    assert all(index < gate for index in main_sites), (
        "tracker advancement sits behind the swing-set change gate, which "
        "delays reaction confirmations Python publishes on the same bar"
    )


def test_pine_support_resistance_publication_is_not_gated_on_swing_change() -> None:
    """The published S/R state must move with the detector, not with the gate."""
    lines = _code_lines()
    gate = _swing_change_gate_index(lines)
    offenders: list[tuple[int, str]] = []
    for index, line in enumerate(lines):
        stripped = line.strip()
        if not stripped.startswith(
            ("latestSRTop :=", "latestSRBottom :=", "latestSRType :=")
        ):
            continue
        if index > gate:
            offenders.append((index + 1, stripped))
    assert not offenders, (
        f"S/R publication sits inside the swing-set change gate: {offenders}"
    )


def test_pine_sr_tracker_state_is_persistent() -> None:
    """§18: the frontier only works if its state survives across bars."""
    code = _code_only(_source())
    for declaration in (
        "type SRTracker",
        "var array<int>       srKeys",
        "var array<SRTracker> srTrk",
        "var array<SRRec>     srCached",
        "var bool             srSeeded",
    ):
        assert declaration in code, f"missing persistent frontier state: {declaration}"


def test_pine_sr_walk_is_event_gated_not_per_bar() -> None:
    """§18/§19: no unconditional full S/R reconstruction on every bar.

    The brute-force detector must be gone, and the walk that replaced it must
    sit behind a condition that includes both triggers — a tracker resolution
    moving, and the swing set changing.
    """
    lines = _code_lines()
    code = "\n".join(lines)
    assert "f_detectSR" not in code, "the brute-force per-bar S/R detector is back"
    assert "f_evaluateReaction" not in code, "the rescanning reaction evaluator is back"
    sites = _call_sites(lines, "f_walkSR(")
    assert len(sites) == 1, f"expected exactly one walk call site, got {sites}"
    guard = next(
        line.strip()
        for line in reversed(lines[: sites[0]])
        if line.strip().startswith("if ")
    )
    assert "srTrackerChanged" in guard and "changed" in guard, (
        f"the walk gate must react to BOTH triggers: {guard!r}"
    )


def test_pine_sr_tracker_state_is_retired_at_the_window_edge() -> None:
    """§21: tracker arrays must not grow without bound."""
    code = _code_only(_source())
    assert "int srMinKey = absFirst * C_SR_KEY_STRIDE" in code, (
        "the window-edge retirement bound is missing"
    )
    assert "array.shift(srKeys)" in code and "array.shift(srTrk)" in code, (
        "retired trackers are never removed from the frontier arrays"
    )


def test_pine_sr_tracker_mutation_stays_inside_the_closed_bar_gate() -> None:
    """§24: no unresolved tracker may advance on a forming bar."""
    lines = _code_lines()
    confirmed_gate = next(
        index
        for index, line in enumerate(lines)
        if line.strip() == "if barstate.isconfirmed"
    )
    for token in ("array.set(srTrk", "array.shift(srTrk)", "array.clear(srCached)"):
        sites = [index for index, line in enumerate(lines) if token in line]
        assert sites, f"missing frontier mutation site for {token}"
        for index in sites:
            assert index > confirmed_gate, (
                f"{token} mutates frontier state before the closed-bar gate"
            )
            assert lines[index].startswith(" "), (
                f"{token} is at top level — it must stay inside the "
                "barstate.isconfirmed block"
            )


def test_pine_sr_fingerprint_only_gates_debug_drawing() -> None:
    """C1.6-C: the S/R fingerprint is a drawing gate, never an analytical one.

    It exists so that per-bar recomputation does not become a per-bar
    clear-and-redraw. If it ever guards the detector or the published state, the
    delayed-confirmation defect is back in a new disguise.
    """
    lines = _code_lines()
    for index, line in enumerate(lines):
        stripped = line.strip()
        if "srChanged" not in stripped:
            continue
        if stripped.startswith(("bool srChanged", "srChanged :=")):
            continue  # declaration / assignment
        assert "debugMode" in stripped, (
            f"line {index + 1}: srChanged is used outside a debugMode drawing "
            f"guard — it must never gate analytical state: {stripped}"
        )


def test_pine_support_resistance_stays_inside_the_closed_bar_gate() -> None:
    """C1.6-D: running every bar must not mean running on the forming bar."""
    lines = _code_lines()
    confirmed_gate = next(
        index
        for index, line in enumerate(lines)
        if line.strip() == "if barstate.isconfirmed"
    )
    for index in _call_sites(lines, "f_walkSR("):
        assert index > confirmed_gate, "the S/R walk runs before the closed-bar gate"
        assert lines[index].startswith(" "), (
            "the S/R walk is at top level — it must stay inside the "
            "barstate.isconfirmed block"
        )


def test_pine_reaction_scan_is_bounded_by_available_candles() -> None:
    """C1.6-D: the reaction search may not read beyond the confirmed window."""
    code = _code_only(_source())
    assert "while i < nAbs" in code, (
        "the reaction-start scan no longer carries its upper bound"
    )
    assert "int nAbs = absFirst + array.size(highs)" in code, (
        "the reaction scan's bound is no longer derived from the available candles"
    )


# ---------------------------------------------------------------------------
# P1-SR-ORDERING — the resolved S/R set must carry Python's canonical order.
#
# support_resistance.py:303 ends the detector with a STABLE ascending sort on
# confirmation_time_utc. The Pine walk had no final sort, so its last element —
# which is what the P1_sr_* parity scalars publish — could be an older zone than
# Python's latest whenever both directions qualified.
# ---------------------------------------------------------------------------


def _pine_block_bounds(lines: list[str], definition: str) -> tuple[int, int]:
    """(definition line, first line at top level after it) for a Pine function."""
    start = next(
        index for index, line in enumerate(lines) if line.startswith(definition)
    )
    end = next(
        index
        for index, line in enumerate(lines[start + 1 :], start=start + 1)
        if line and not line.startswith(" ")
    )
    return start, end


def test_pine_sr_walk_applies_the_canonical_final_order() -> None:
    """The walk must end in Python's order, ties included."""
    code = _code_only(_source())
    assert (
        "probeTime > keyTime or (probeTime == keyTime and probeIdx > keyIdx)" in code
    ), (
        "the canonical (confirmationTime, insertionIndex) ordering key is gone — "
        "without it Pine can publish an older zone than Python's latest"
    )
    lines = _code_lines()
    walk_def, next_top_level = _pine_block_bounds(lines, "f_walkSR(")
    body = [
        line.strip()
        for line in lines[walk_def + 1 : next_top_level]
        if line.strip() and not line.strip().startswith("//")
    ]
    assert body[-1] == "ordered", (
        f"f_walkSR must return the canonically ordered set, not {body[-1]!r}"
    )


def test_pine_publishes_the_canonically_latest_zone() -> None:
    """The parity scalars read the LAST element of the ordered set."""
    code = _code_only(_source())
    assert "SRRec srLast = array.get(srs, array.size(srs) - 1)" in code, (
        "the published S/R scalar no longer reads the canonically latest zone"
    )


def test_pine_sr_ordering_runs_only_when_the_set_is_rebuilt() -> None:
    """The sort must live inside the walk, not on the per-bar path."""
    lines = _code_lines()
    sort_line = next(
        index
        for index, line in enumerate(lines)
        if "probeTime == keyTime and probeIdx > keyIdx" in line
    )
    walk_def, next_top_level = _pine_block_bounds(lines, "f_walkSR(")
    assert walk_def < sort_line < next_top_level, (
        "the canonical sort escaped f_walkSR and may now run every bar"
    )


# ---------------------------------------------------------------------------
# P1-SR-PERF-3 — semantic pair/fold frontier.
#
# Measurement on canonical FXCM controls showed ~650-680 origin x touch visits
# per genuinely new semantic pair. The fold cache removes that redundancy; these
# guards stop it being removed, weakened, or turned back into a full rebuild.
# ---------------------------------------------------------------------------


def test_pine_declares_the_fold_and_candidate_types() -> None:
    code = _code_only(_source())
    assert "type SRCand" in code, "the semantic candidate type is missing"
    assert "type SRFold" in code, "the persistent fold type is missing"


def test_pine_fold_and_candidate_state_is_persistent() -> None:
    code = _code_only(_source())
    for declaration in (
        "var array<SRCand> srCandSupport",
        "var array<SRCand> srCandResist",
        "var array<int>    srOppSupport",
        "var array<int>    srOppResist",
        "var array<SRCand> srSnap",
        "var array<SRFold> srFold",
        "var array<SRFold> srFoldKeep",
        "var array<int>    srDirty",
    ):
        assert declaration in code, f"missing persistent frontier state: {declaration}"


def test_pine_fold_cache_is_consulted_before_recomputing() -> None:
    """A cached fold must be reusable; otherwise the frontier does nothing."""
    code = _code_only(_source())
    assert "f_srFoldFind(" in code, "no fold lookup exists"
    assert "cached.hasZone" in code, "the cached fold result is never republished"


def test_pine_fold_invalidation_and_retirement_exist() -> None:
    code = _code_only(_source())
    assert "f_srApplyDelta(" in code, "swing-delta invalidation is missing"
    assert "f_srSwingHasKey(" in code, "fold retirement by origin survival is missing"
    assert "srFoldKeep" in code, "retirement must rebuild from survivors"


def test_pine_swing_delta_is_a_linear_merge() -> None:
    """The delta must not scan the old snapshot once per new swing.

    Both lists are ascending by pivot-end time, so reconciliation is a two-cursor
    merge. A nested membership search here would just move the quadratic cost.
    """
    lines = _code_lines()
    start = next(
        index for index, line in enumerate(lines) if line.startswith("f_srApplyDelta(")
    )
    end = next(
        index
        for index, line in enumerate(lines)
        if index > start and line and not line.startswith((" ", "\t"))
    )
    body = lines[start:end]
    merge = [line for line in body if "while i < oldN or j < newN" in line]
    assert merge, "f_srApplyDelta no longer uses the two-cursor merge"


def test_pine_reference_atr_is_stored_not_reconstructed() -> None:
    """referenceAtr must be carried, never recovered by dividing zoneDepth."""
    code = _code_only(_source())
    assert "float referenceAtr" in code, "SRFold/SRCand must carry referenceAtr"
    offenders = [
        (number, line.strip())
        for number, line in enumerate(_code_lines(), start=1)
        if "zoneDepth /" in line or "zoneDepth/" in line
    ]
    assert not offenders, (
        "referenceAtr is being reconstructed by dividing zoneDepth, which "
        f"introduces avoidable float error: {offenders}"
    )


def test_pine_fold_retirement_never_removes_while_iterating() -> None:
    """Index-based removal mid-loop is how the earlier Pine defects happened."""
    code = _code_only(_source())
    assert "array.remove(" not in code, (
        "array.remove reintroduced — retirement must rebuild from survivors so "
        "no index can be invalidated mid-loop"
    )


def test_pine_candidate_lists_carry_absolute_indices() -> None:
    """Cached candidates must not hold window-relative indices.

    pivotEndIdx shifts every bar as the 300-bar window slides; a cached
    candidate holding one would silently address the wrong candle.
    """
    code = _code_only(_source())
    assert "int   pivotEndAbs" in code, "SRCand must carry an ABSOLUTE pivot index"
    lines = _code_lines()
    start = next(
        index for index, line in enumerate(lines) if line.startswith("f_walkSR(")
    )
    end = next(
        index
        for index, line in enumerate(lines)
        if index > start and line and not line.startswith((" ", "\t"))
    )
    offenders = [
        (start + offset + 1, line.strip())
        for offset, line in enumerate(lines[start:end])
        if "pivotEndIdx" in line
    ]
    assert not offenders, f"f_walkSR reads a window-relative pivot index: {offenders}"


def test_pine_dirty_set_drives_fold_recomputation() -> None:
    """Only origins whose own reaction moved may lose their cached fold."""
    code = _code_only(_source())
    assert "array.clear(srDirty)" in code, "the dirty set is never reset per bar"
    assert "array.push(srDirty, dirtyOrigin)" in code, (
        "reaction changes no longer record which origin they affect"
    )
    assert "if foldIdx >= 0 and not isDirty" in code, (
        "the walk no longer reuses folds for clean origins"
    )


# ---------------------------------------------------------------------------
# P1-PERF-4 — bounded historical execution.
#
# TradingView's Basic plan gives the whole script 20 seconds to execute its
# accessible history, and PERF-3 still tripped it on D1. `calc_bars_count` caps
# how many trailing bars are executed at all. That is only sound because every
# value a bar reads is pruned to `lookbackWindow` except the Wilder ATR, which
# is an IIR recurrence — so the horizon has to cover the window PLUS the bars
# the ATR needs to forget its seed. These guards pin that arithmetic into the
# source, and pin the properties that make the horizon safe at all.
# ---------------------------------------------------------------------------

_P1_CALC_BARS = 1800
_P1_MIN_CALC_BARS = 1250
_P1_LOOKBACK = 300
_P1_PROTECTED = 300
_P1_WARMUP_CEILING = 950


def test_pine_declares_the_validated_calc_bars_count() -> None:
    code = _code_only(_source())
    assert f"calc_bars_count = {_P1_CALC_BARS}" in code, (
        "the indicator declaration no longer carries the validated historical "
        "execution horizon"
    )
    assert "indicator(" in code


def test_pine_calc_bars_count_is_not_reduced_below_the_approved_value() -> None:
    """A smaller horizon is a semantic change, not a performance knob.

    Below the approved value the oldest protected bars read an ATR that still
    remembers the truncation seed, and the published outputs stop matching
    full-history execution.
    """
    import re

    match = re.search(r"calc_bars_count\s*=\s*(\d+)", _code_only(_source()))
    assert match is not None, "calc_bars_count is missing from the declaration"
    declared = int(match.group(1))
    assert declared >= _P1_CALC_BARS, (
        f"calc_bars_count was lowered to {declared}; {_P1_CALC_BARS} is the "
        "validated horizon"
    )


def test_pine_mirrors_the_horizon_in_named_constants() -> None:
    """The declaration takes a literal, so the constants must be kept in step."""
    code = _code_only(_source())
    assert f"int C_P1_CALC_BARS     = {_P1_CALC_BARS}" in code
    assert f"int C_P1_MIN_CALC_BARS = {_P1_MIN_CALC_BARS}" in code


def test_pine_validity_floor_covers_window_plus_atr_warmup() -> None:
    assert _P1_MIN_CALC_BARS >= _P1_LOOKBACK + _P1_WARMUP_CEILING, (
        "the insufficient-history floor no longer covers a full analytical "
        "window plus the measured ATR warm-up"
    )


def test_pine_horizon_keeps_every_protected_bar_valid() -> None:
    processed_at_earliest = _P1_CALC_BARS - (_P1_PROTECTED - 1)
    assert processed_at_earliest >= _P1_MIN_CALC_BARS, (
        "the earliest protected bar would be published while still inside the "
        "ATR warm-up"
    )


def test_pine_uses_bar_index_only_as_dataset_capacity_metadata() -> None:
    """The one property that makes calc_bars_count safe to add at all.

    TradingView renumbers bars when calc_bars_count is set: the first executed
    bar becomes bar_index 0. Any ANALYTICAL value derived from bar_index would
    silently shift with the horizon, so the engine derives its absolute
    positions from its own confirmedBarCount instead.

    P1-PERF-4A admits exactly one exception: ``last_bar_index`` as dataset-size
    metadata for the capacity gate. That reads how much history exists, never
    where a bar sits, so the horizon cannot move it into an identity, a key, an
    ordering or a geometry.
    """
    code = _code_only(_source())
    # `last_bar_index` contains the substring, so remove it before looking for
    # bare uses — otherwise the capacity gate would mask a real regression.
    bare = code.replace("last_bar_index", "")
    assert "bar_index" not in bare, (
        "bar_index is referenced outside the capacity gate; under "
        "calc_bars_count its origin moves with the horizon, so it cannot be "
        "used for analytical state"
    )
    uses = [line.strip() for line in _code_lines() if "last_bar_index" in line]
    assert uses == ["int  p1DatasetBars = last_bar_index + 1"], (
        f"last_bar_index may only feed the capacity gate; found {uses}"
    )


def test_pine_capacity_metadata_stays_out_of_the_analytical_engine() -> None:
    """Capacity is a product gate, not an input to any measurement."""
    lines = _code_lines()
    gate = next(
        index
        for index, line in enumerate(lines)
        if line.strip() == "if barstate.isconfirmed"
    )
    gate_indent = len(lines[gate]) - len(lines[gate].lstrip())
    end = len(lines)
    for index in range(gate + 1, len(lines)):
        stripped = lines[index].strip()
        if stripped and (len(lines[index]) - len(lines[index].lstrip())) <= gate_indent:
            end = index
            break
    offenders = [
        index + 1
        for index in range(gate, end)
        if "last_bar_index" in lines[index]
        or "p1DatasetBars" in lines[index]
        or "p1CapacityOk" in lines[index]
    ]
    assert not offenders, (
        f"capacity metadata reached the confirmed analytical block at lines "
        f"{offenders}; it must only gate publication"
    )


def test_pine_separates_capacity_from_warmup() -> None:
    """The two history questions must stay distinguishable in the source.

    Collapsing them back into one comparison is how PERF-4 came to answer only
    the warm-up question while appearing to answer both.
    """
    code = _code_only(_source())
    assert "bool p1CapacityOk  = p1DatasetBars >= C_P1_CALC_BARS" in code, (
        "the dataset-capacity gate is missing or no longer checks the selected horizon"
    )
    assert "bool p1WarmupOk    = confirmedBarCount >= C_P1_MIN_CALC_BARS" in code, (
        "the per-bar warm-up gate is missing"
    )
    assert "bool p1HistoryOk   = p1CapacityOk and p1WarmupOk" in code, (
        "publication must require BOTH capacity and warm-up"
    )


def test_pine_capacity_requirement_is_the_selected_horizon_not_the_floor() -> None:
    """1250 is a per-bar warm-up floor, never the dataset-capacity requirement.

    A 1300-bar run contains a few warm bars and is still outside the validated
    contract, so capacity has to be measured against 1800.
    """
    code = _code_only(_source())
    assert "p1DatasetBars >= C_P1_MIN_CALC_BARS" not in code, (
        "capacity is being checked against the warm-up floor; that would admit "
        "runs far shorter than the validated horizon"
    )


def test_pine_status_message_does_not_guess_the_cause() -> None:
    """Short symbol history and a lowered setting are indistinguishable here."""
    code = _code_only(_source())
    assert "INSUFFICIENT CALCULATED HISTORY" in code, (
        "the bounded insufficient-history status indication is missing"
    )
    assert "restore Calculated bars" not in code, (
        "the status claims the user lowered the setting, but a short symbol "
        "history produces the same state and the script cannot tell them apart"
    )


def test_pine_withholds_outputs_when_history_is_insufficient() -> None:
    """Wrong-but-plausible output is worse than no output."""
    code = _code_only(_source())
    assert "bool p1HistoryOk   = p1CapacityOk and p1WarmupOk" in code, (
        "the insufficient-history guard is missing"
    )
    lines = _code_lines()
    plots = [line for line in lines if line.startswith("plot(") and "P1_" in line]
    assert len(plots) == 9, f"expected nine parity plots, found {len(plots)}"
    ungated = [line for line in plots if "p1HistoryOk ?" not in line]
    assert not ungated, (
        f"these parity outputs publish without the history guard: {ungated}"
    )


def test_pine_history_guard_is_publication_only() -> None:
    """The guard must not become an analytical rule.

    It may suppress publication; it may not change what the engine computes or
    stores, or the confirmed-bar boundary would start depending on chart length.
    """
    lines = _code_lines()
    gate = next(
        index
        for index, line in enumerate(lines)
        if line.strip() == "if barstate.isconfirmed"
    )
    gate_indent = len(lines[gate]) - len(lines[gate].lstrip())
    end = len(lines)
    for index in range(gate + 1, len(lines)):
        stripped = lines[index].strip()
        if stripped and (len(lines[index]) - len(lines[index].lstrip())) <= gate_indent:
            end = index
            break
    inside = [index + 1 for index in range(gate, end) if "p1HistoryOk" in lines[index]]
    assert not inside, (
        f"the history guard is referenced inside the confirmed-bar block at "
        f"lines {inside}; it must only gate publication"
    )
