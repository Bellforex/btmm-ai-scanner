"""RC4 integration: scanner SHA pin, RC4 decision fields in the journals,
paper trade intents, and restart safety under the RC4 profile.

* the pin: the pinned source digest is re-derived from ``git ls-tree`` of
  the pinned commit; the running scanner matches it; a mismatch refuses to
  run (engine and CLI exit 8) and is recorded; the explicit override runs
  and is recorded in the manifest and flagged by ``health``;
* RC4 fields: copied verbatim into ``p5_decision_journal.csv`` and covered
  by the per-bar digest (so a rebuild that changed one is caught);
* trade intents: exactly one per consumed ``PERMISSION_ENTERED_ACTIONABLE``
  event, linked to the practice-policy signal of that event, never from a
  bare actionable P5 decision;
* restart safety: crash mid-run under RC4 (real scanner) -> resume ->
  byte-identical journals and digests.
"""

from __future__ import annotations

import csv
import io
import json
import re
import subprocess
from pathlib import Path

import pytest

import botdryrun
from botdryrun.config import BotConfig, ScannerProfile
from botdryrun.domain import (
    DECISION_ROW_FIELDS,
    RC4_DECISION_FIELDS,
    DecisionView,
    compute_bar_digest,
)
from botdryrun.engine import BotEngine, RunOutcome, ScannerPinMismatchError
from botdryrun.health import health_report
from botdryrun.intents import TRADE_INTENT_COLUMNS, intent_id_for
from botdryrun.scanner_pin import (
    PINNED_SCANNER_COMMIT,
    PINNED_SOURCE_DIGEST,
    REPLAY_MODULES,
    ScannerPin,
    check_scanner_pin,
    compute_source_digest,
    evaluate_scanner_pin,
    git_blob_sha1,
    installed_source_blobs,
)
from botdryrun.store import StateStore
from tests.bot.support import (
    SCANNER_START,
    SCRIPT_BARS,
    SCRIPT_START,
    config_for,
    deterministic_journals,
    host_items,
    load,
    scanner_bars,
    script_bars,
    scripted_source,
    session_times,
    static_loader,
    write_csv,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
PACKAGE = Path(botdryrun.__file__).resolve().parent
FAKE_PIN = ScannerPin(PINNED_SCANNER_COMMIT, "0" * 64)


class SimulatedCrash(RuntimeError):
    pass


def _rows(path: Path) -> list[dict[str, str]]:
    return list(csv.DictReader(io.StringIO(path.read_text(encoding="utf-8"))))


@pytest.fixture(scope="module")
def scenario(tmp_path_factory: pytest.TempPathFactory) -> tuple[BotConfig, list]:  # type: ignore[type-arg]
    root = tmp_path_factory.mktemp("rc4_script")
    times = session_times(SCRIPT_START, SCRIPT_BARS)
    write_csv(root / "M15.csv", times, script_bars())
    return config_for(root, times), host_items(load(root / "M15.csv"))


def _scripted(state: Path, config: BotConfig | None, items: list, **kwargs: object) -> BotEngine:  # type: ignore[type-arg]
    return BotEngine(
        state, config, feed_loader=static_loader(items), scanner_source=scripted_source(), **kwargs  # type: ignore[arg-type]
    )


# ---------------------------------------------------------------------------
# Scanner pin
# ---------------------------------------------------------------------------


def test_pinned_digest_is_the_git_tree_of_the_pinned_commit() -> None:
    assert re.fullmatch(r"[0-9a-f]{40}", PINNED_SCANNER_COMMIT)
    try:
        subprocess.run(
            ["git", "cat-file", "-e", f"{PINNED_SCANNER_COMMIT}^{{commit}}"],
            cwd=REPO_ROOT, check=True, capture_output=True, timeout=60,
        )
        listing = subprocess.run(
            ["git", "ls-tree", "-r", PINNED_SCANNER_COMMIT, "--", "src/btmm_ai_scanner", "tests/parity_support"],
            cwd=REPO_ROOT, check=True, capture_output=True, text=True, timeout=60,
        ).stdout
    except (OSError, subprocess.SubprocessError):
        pytest.skip("git or the pinned commit is not available")
    wanted = {f"tests/parity_support/{m}.py" for m in REPLAY_MODULES}
    blobs = []
    for line in listing.splitlines():
        meta, path = line.split("\t", 1)
        if (path.startswith("src/btmm_ai_scanner/") and path.endswith(".py")) or path in wanted:
            blobs.append((path, meta.split()[2]))
    assert {p for p, _ in blobs} >= wanted
    assert compute_source_digest(blobs) == PINNED_SOURCE_DIGEST


def test_running_scanner_source_matches_the_pin() -> None:
    check = check_scanner_pin()
    assert check.status == "MATCH" and check.matched and not check.overridden
    assert check.observed_digest == PINNED_SOURCE_DIGEST
    assert check.file_count == len(installed_source_blobs()) > len(REPLAY_MODULES)


def test_fingerprint_is_line_ending_neutral_and_detects_a_changed_file() -> None:
    assert git_blob_sha1(b"a = 1\r\nb = 2\r\n") == git_blob_sha1(b"a = 1\nb = 2\n")
    # git's own blob id of "hello\n"
    assert git_blob_sha1(b"hello\n") == "ce013625030ba8dba906f756967f9e9ca394464a"
    blobs = installed_source_blobs()
    path, blob = blobs[0]
    tampered = [(path, git_blob_sha1(b"# edited\n")), *blobs[1:]]
    assert evaluate_scanner_pin(observed_blobs=blobs).matched
    check = evaluate_scanner_pin(observed_blobs=tampered)
    assert check.status == "MISMATCH_REFUSED"
    with pytest.raises(ScannerPinMismatchError, match="Refusing to run"):
        check_scanner_pin(observed_blobs=tampered)
    assert check_scanner_pin(observed_blobs=tampered, allow_mismatch=True).status == "MISMATCH_OVERRIDDEN"
    # an extra file (e.g. an untracked module inside the package) is a mismatch too
    assert not evaluate_scanner_pin(observed_blobs=[*blobs, ("src/btmm_ai_scanner/x.py", blob)]).matched


def test_engine_refuses_a_pin_mismatch_and_records_the_refusal(tmp_path: Path, scenario) -> None:  # type: ignore[no-untyped-def]
    config, items = scenario
    state = tmp_path / "state"
    engine = _scripted(state, config, items, scanner_pin=FAKE_PIN)
    try:
        with pytest.raises(ScannerPinMismatchError):
            engine.run()
    finally:
        engine.close()
    store = StateStore(state)
    try:
        assert store.processed_bar_count() == 0
        assert store.get_meta("status") == "NEW"  # untouched: not left RUNNING
        assert store.query("SELECT outcome FROM runs") == [("REFUSED_SCANNER_PIN",)]
        assert store.query("SELECT status, overridden FROM scanner_pin_checks") == [("MISMATCH_REFUSED", 0)]
    finally:
        store.close()
    assert "last run was refused: scanner source does not match the pin" in health_report(state)["problems"]


def test_override_runs_and_is_recorded_in_manifest_and_health(tmp_path: Path, scenario) -> None:  # type: ignore[no-untyped-def]
    config, items = scenario
    state = tmp_path / "state"
    engine = _scripted(state, config, items, scanner_pin=FAKE_PIN, allow_scanner_mismatch=True)
    try:
        report = engine.run()
    finally:
        engine.close()
    assert report.outcome is RunOutcome.COMPLETED
    assert report.scanner_pin is not None and report.scanner_pin["status"] == "MISMATCH_OVERRIDDEN"
    manifest = json.loads((state / "journals" / "manifest.json").read_text(encoding="utf-8"))
    pin = manifest["scanner_pin"]
    assert pin["override_ever_used"] is True and pin["all_checks_matched"] is False
    assert pin["last_check"]["status"] == "MISMATCH_OVERRIDDEN"
    assert pin["pinned_commit"] == PINNED_SCANNER_COMMIT
    assert pin["session_pin"]["source_digest"] == "0" * 64
    pin_journal = _rows(state / "journals" / "scanner_pin_journal.csv")
    assert [r["status"] for r in pin_journal] == ["MISMATCH_OVERRIDDEN"]
    health = health_report(state)
    assert not health["healthy"]
    assert any("overridden" in p for p in health["problems"])


def test_a_session_created_under_another_pin_is_refused(tmp_path: Path, scenario) -> None:  # type: ignore[no-untyped-def]
    """Even with the running scanner matching the bot's pin, a session whose
    earlier bars were produced under a DIFFERENT pin is not continued."""
    config, items = scenario
    state = tmp_path / "state"
    other = ScannerPin("f" * 40, "f" * 64)
    engine = _scripted(state, config, items, scanner_pin=other, allow_scanner_mismatch=True)
    try:
        engine.run(max_bars=5)
    finally:
        engine.close()
    engine = _scripted(state, None, items)  # the real pin; matches the source
    try:
        with pytest.raises(ScannerPinMismatchError, match="session was created under"):
            engine.run()
    finally:
        engine.close()


def test_a_matching_session_records_the_pin_in_manifest(tmp_path: Path, scenario) -> None:  # type: ignore[no-untyped-def]
    config, items = scenario
    state = tmp_path / "state"
    engine = _scripted(state, config, items)
    try:
        engine.run(max_bars=3)
    finally:
        engine.close()
    engine = _scripted(state, None, items)
    try:
        engine.run()
    finally:
        engine.close()
    pin = json.loads((state / "journals" / "manifest.json").read_text(encoding="utf-8"))["scanner_pin"]
    assert pin["checks"] == 2 and pin["all_checks_matched"] is True and pin["override_ever_used"] is False
    assert pin["session_pin"] == {
        "commit": PINNED_SCANNER_COMMIT,
        "fingerprint_version": "BOT-SCANNER-PIN-V1",
        "source_digest": PINNED_SOURCE_DIGEST,
    }
    assert health_report(state)["healthy"]


def test_cli_exit_8_on_pin_mismatch_and_override_flag(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import botdryrun.engine as engine_module
    from botdryrun.__main__ import main

    times = session_times(SCANNER_START, 6)
    write_csv(tmp_path / "data" / "M15.csv", times, scanner_bars(6))
    monkeypatch.setattr(engine_module, "pinned", lambda: FAKE_PIN)
    window = ["--start", times[0].isoformat(), "--end", times[-1].isoformat(),
              "--dataset-root", str(tmp_path / "data"), "--data-source", "CSV_DIR",
              "--context-timeframes", "", "--context-lookback-bars", "0"]
    assert main(["replay", "--state-dir", str(tmp_path / "a"), *window]) == 8
    assert main(["replay", "--state-dir", str(tmp_path / "b"), *window, "--allow-scanner-mismatch"]) == 0
    manifest = json.loads((tmp_path / "b" / "journals" / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["scanner_pin"]["override_ever_used"] is True


# ---------------------------------------------------------------------------
# RC4 decision fields and trade intents (scripted source)
# ---------------------------------------------------------------------------


def test_rc4_decision_fields_are_journaled_verbatim(tmp_path: Path, scenario) -> None:  # type: ignore[no-untyped-def]
    config, items = scenario
    state = tmp_path / "state"
    engine = _scripted(state, config, items)
    try:
        engine.run()
    finally:
        engine.close()
    journal = state / "journals" / "p5_decision_journal.csv"
    header = journal.read_text(encoding="utf-8").splitlines()[0].split(",")
    assert header == ["bar_index", *DECISION_ROW_FIELDS]
    assert set(RC4_DECISION_FIELDS) <= set(header)
    rows = _rows(journal)
    assert len(rows) == SCRIPT_BARS * 7
    row = next(r for r in rows if r["bar_index"] == "12" and r["poi_idx"] == "1")
    assert row["framework"] == "SCRIPTED_TREND"
    assert row["range_position"] == "UPPER" and row["fib_bucket"] == "PREMIUM"
    assert row["retracement_pct"] == "61.8"
    assert row["btmm_pretrade_reason"] == "SCRIPTED_REASON_1"
    assert row["sweep_before_poi"] == "0" and row["poi_touch_count"] == "1"
    assert row["poi_dwell_bars"] == "12" and row["interaction_episode"] == "EP-1"
    manifest = json.loads((state / "journals" / "manifest.json").read_text(encoding="utf-8"))
    assert "p5_decision_journal.csv" in manifest["journal_sha256"]
    assert "trade_intent_journal.csv" in manifest["journal_sha256"]


def test_bar_digest_covers_the_rc4_decision_fields() -> None:
    base = DecisionView("r", 0, "BUY_BIAS", 0, True, 70, "POI_VALIDATED", True, framework="TREND")
    changed = DecisionView("r", 0, "BUY_BIAS", 0, True, 70, "POI_VALIDATED", True, framework="RANGE")

    def digest(d: DecisionView) -> str:
        return compute_bar_digest(
            bar_index=0, bar_ms=0, primed=False, registry_size=0, new_registry_pois=0,
            fresh_at_close=0, mitigated_at_close=0, invalidated_at_close=0,
            p3_lines=(), p5_lines=(), p8_lines=(), decision_lines=[d.canonical_line()],
        )

    assert digest(base) != digest(changed)


def test_one_trade_intent_per_consumed_entered_event(tmp_path: Path, scenario) -> None:  # type: ignore[no-untyped-def]
    config, items = scenario
    state = tmp_path / "state"
    engine = _scripted(state, config, items)
    try:
        engine.run()
    finally:
        engine.close()
    intents = _rows(state / "journals" / "trade_intent_journal.csv")
    assert list(intents[0]) == list(TRADE_INTENT_COLUMNS)
    store = StateStore(state)
    try:
        entered = [
            r[0] for r in store.query(
                "SELECT event_id FROM events WHERE event_type='PERMISSION_ENTERED_ACTIONABLE' "
                "ORDER BY bar_index, sequence_in_bar"
            )
        ]
        signals = {r[0]: r[1:] for r in store.query("SELECT signal_id, source_event_id, status, reason FROM signals")}
        per_bar = dict(store.query("SELECT bar_index, trade_intents FROM bar_summary"))
    finally:
        store.close()
    assert len(entered) == 7
    # one per consumed ENTERED event, in native order; the duplicate
    # delivery at bar 14 produced one event and therefore one intent
    assert [r["source_event_id"] for r in intents] == entered
    assert [r["intent_id"] for r in intents] == [intent_id_for(e) for e in entered]
    assert sum(per_bar.values()) == 7 and per_bar[14] == 1
    for r in intents:
        source, status, reason = signals[r["signal_id"]]
        assert source == r["source_event_id"]
        assert (r["signal_status"], r["signal_reason"]) == (status, reason)
        assert r["execution_mode"] == "PAPER"
        poi = int(r["poi_idx"])
        assert r["btmm_pretrade_reason"] == f"SCRIPTED_REASON_{poi}"
        assert r["framework"] == "SCRIPTED_TREND"
        assert float(r["zone_bottom"]) < float(r["zone_top"])
    by_poi = {r["poi_idx"]: r for r in intents}
    assert by_poi["1"]["direction"] == "SHORT" and by_poi["1"]["range_position"] == "UPPER"
    assert by_poi["1"]["zone_bottom"] == "102.00" and by_poi["1"]["zone_top"] == "103.00"
    assert by_poi["4"]["direction"] == "LONG" and by_poi["4"]["signal_status"] == "ACCEPTED"
    assert by_poi["5"]["signal_status"] == "SKIPPED"
    assert by_poi["5"]["signal_reason"] == "PERMISSION_DIRECTION_MISMATCH"
    # POI 6 is actionable in every P5 decision but never had an event
    assert "6" not in by_poi


def test_trade_intents_place_nothing_and_are_event_triggered_only() -> None:
    source = (PACKAGE / "intents.py").read_text(encoding="utf-8")
    assert "botdryrun.broker" not in source and ".place(" not in source
    assert "P8EventName.PERMISSION_ENTERED_ACTIONABLE" in source
    engine_src = (PACKAGE / "engine.py").read_text(encoding="utf-8")
    assert engine_src.count("build_trade_intents(") == 1
    assert "build_trade_intents(batch.new_events, snap, actions.signals)" in engine_src


# ---------------------------------------------------------------------------
# Restart safety under RC4 (real scanner)
# ---------------------------------------------------------------------------

BARS = 48


@pytest.fixture(scope="module")
def rc4_data(tmp_path_factory: pytest.TempPathFactory):  # type: ignore[no-untyped-def]
    root = tmp_path_factory.mktemp("rc4_real")
    times = session_times(SCANNER_START, BARS)
    write_csv(root / "M15.csv", times, scanner_bars(BARS))
    state = tmp_path_factory.mktemp("rc4_uninterrupted")
    config = config_for(root, times)
    assert config.scanner_profile is ScannerProfile.RC4
    engine = BotEngine(state, config)
    try:
        assert engine.run().outcome is RunOutcome.COMPLETED
    finally:
        engine.close()
    return config, deterministic_journals(state)


@pytest.mark.parametrize("crash_bar", [11, 29])
def test_rc4_crash_mid_run_then_resume_is_identical(tmp_path: Path, rc4_data, crash_bar: int) -> None:  # type: ignore[no-untyped-def]
    config, expected = rc4_data
    state = tmp_path / "state"

    def fault(stage: str, bar_index: int) -> None:
        if stage == "before_commit" and bar_index == crash_bar:
            raise SimulatedCrash("killed before COMMIT")

    engine = BotEngine(state, config, fault_injector=fault)
    with pytest.raises(SimulatedCrash):
        engine.run()
    engine.close()
    engine = BotEngine(state)
    try:
        report = engine.run()
    finally:
        engine.close()
    assert report.outcome is RunOutcome.COMPLETED and report.rebuilt_bars == crash_bar
    assert report.scanner_pin is not None and report.scanner_pin["status"] == "MATCH"
    assert deterministic_journals(state) == expected


_FXCM_ROOT = Path("C:/Users/user/Desktop/btmm-ai-scanner/artifacts/v1a_validation")


def test_real_fxcm_rc4_crash_and_resume_is_identical_and_carries_rc4_fields(tmp_path: Path) -> None:
    """Genuine FXCM, six timeframes, in-sample (2026-08-10): the RC4 fields
    reach the journal, and a crash mid-run followed by a resume ends
    byte-identical to an uninterrupted run."""
    if not (_FXCM_ROOT / "v1a_raw_ohlc_M5.csv").is_file():
        pytest.skip("FXCM artifacts not present")
    config = BotConfig.from_mapping(
        {
            "window_start_utc": "2026-08-09T22:00:00Z",
            "window_end_utc": "2026-08-10T03:45:00Z",
            "dataset_root": str(_FXCM_ROOT),
            "context_lookback_bars": 40,
        }
    )
    assert config.scanner_profile is ScannerProfile.RC4
    engine = BotEngine(tmp_path / "full", config)
    try:
        assert engine.run().processed_bars == 24
    finally:
        engine.close()
    rows = _rows(tmp_path / "full" / "journals" / "p5_decision_journal.csv")
    assert rows and any(r["framework"] for r in rows)
    assert any(r["fib_bucket"] for r in rows) and any(r["interaction_episode"] for r in rows)

    def fault(stage: str, bar_index: int) -> None:
        if stage == "before_commit" and bar_index == 13:
            raise SimulatedCrash("killed before COMMIT")

    engine = BotEngine(tmp_path / "crashed", config, fault_injector=fault)
    with pytest.raises(SimulatedCrash):
        engine.run()
    engine.close()
    engine = BotEngine(tmp_path / "crashed")
    try:
        report = engine.run()
        assert report.rebuilt_bars == 13 and report.outcome is RunOutcome.COMPLETED
    finally:
        engine.close()
    assert deterministic_journals(tmp_path / "crashed") == deterministic_journals(tmp_path / "full")
