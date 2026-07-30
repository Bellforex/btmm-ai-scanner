from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID

from btmm_ai_scanner.scanner.lifecycle_validation import (
    LifecycleMismatch,
    build_lifecycle_validation_report,
)

_BASE_TIME = datetime(2026, 1, 1, tzinfo=UTC)


@dataclass(frozen=True)
class _FakeTransition:
    record_id: UUID
    transition_type: str
    event_time_utc: datetime
    availability_time_utc: datetime


def _transition(
    index: int, minutes_offset: int = 0, transition_type: str = "TAP"
) -> _FakeTransition:
    event_time = _BASE_TIME + timedelta(minutes=minutes_offset)
    return _FakeTransition(
        record_id=UUID(f"0193f450-1234-7abc-8def-{index:012x}"),
        transition_type=transition_type,
        event_time_utc=event_time,
        availability_time_utc=event_time + timedelta(seconds=1),
    )


def test_lifecycle_validation_confirms_exact_matching_sequence() -> None:
    transitions = (_transition(0, 0), _transition(1, 1), _transition(2, 2))
    report = build_lifecycle_validation_report(transitions, transitions)
    assert report.matched_event_count == 3
    assert report.missing_events == ()
    assert report.extra_events == ()
    assert report.duplicated_events == ()
    assert report.reordered_events == ()


def test_lifecycle_validation_detects_missing_event() -> None:
    expected = (_transition(0, 0), _transition(1, 1))
    actual = (_transition(0, 0),)
    report = build_lifecycle_validation_report(expected, actual)
    assert len(report.missing_events) == 1
    assert report.missing_events[0].source_record_id == _transition(1, 1).record_id


def test_lifecycle_validation_detects_extra_event() -> None:
    expected = (_transition(0, 0),)
    actual = (_transition(0, 0), _transition(1, 1))
    report = build_lifecycle_validation_report(expected, actual)
    assert len(report.extra_events) == 1
    assert report.extra_events[0].source_record_id == _transition(1, 1).record_id


def test_lifecycle_validation_detects_duplicated_event() -> None:
    expected = (_transition(0, 0),)
    actual = (_transition(0, 0), _transition(0, 0))
    report = build_lifecycle_validation_report(expected, actual)
    assert len(report.duplicated_events) == 1


def test_lifecycle_validation_detects_reordered_event() -> None:
    expected = (_transition(0, 0), _transition(1, 1))
    actual = (_transition(1, 1), _transition(0, 0))
    report = build_lifecycle_validation_report(expected, actual)
    assert len(report.reordered_events) == 2
    assert report.matched_event_count == 0


def test_lifecycle_validation_detects_prior_state_mismatch() -> None:
    mismatch = LifecycleMismatch(
        source_record_id=UUID("0193f450-1234-7abc-8def-000000000000"),
        expected_event_type="TAP",
        actual_event_type="TAP",
        expected_prior_state="NO_BREACH",
        actual_prior_state="RECLAIM_PENDING",
        expected_resulting_state=None,
        actual_resulting_state=None,
        expected_event_time_utc=None,
        actual_event_time_utc=None,
        expected_availability_time_utc=None,
        actual_availability_time_utc=None,
    )
    assert mismatch.expected_prior_state != mismatch.actual_prior_state


def test_lifecycle_validation_detects_resulting_state_mismatch() -> None:
    mismatch = LifecycleMismatch(
        source_record_id=UUID("0193f450-1234-7abc-8def-000000000000"),
        expected_event_type="TAP",
        actual_event_type="TAP",
        expected_prior_state=None,
        actual_prior_state=None,
        expected_resulting_state="RECLAIM_CONFIRMED",
        actual_resulting_state="RECLAIM_FAILED",
        expected_event_time_utc=None,
        actual_event_time_utc=None,
        expected_availability_time_utc=None,
        actual_availability_time_utc=None,
    )
    assert mismatch.expected_resulting_state != mismatch.actual_resulting_state


def test_lifecycle_validation_detects_event_time_mismatch() -> None:
    mismatch = LifecycleMismatch(
        source_record_id=UUID("0193f450-1234-7abc-8def-000000000000"),
        expected_event_type="TAP",
        actual_event_type="TAP",
        expected_prior_state=None,
        actual_prior_state=None,
        expected_resulting_state=None,
        actual_resulting_state=None,
        expected_event_time_utc=_BASE_TIME,
        actual_event_time_utc=_BASE_TIME + timedelta(minutes=1),
        expected_availability_time_utc=None,
        actual_availability_time_utc=None,
    )
    assert mismatch.expected_event_time_utc != mismatch.actual_event_time_utc


def test_lifecycle_validation_detects_availability_mismatch() -> None:
    mismatch = LifecycleMismatch(
        source_record_id=UUID("0193f450-1234-7abc-8def-000000000000"),
        expected_event_type="TAP",
        actual_event_type="TAP",
        expected_prior_state=None,
        actual_prior_state=None,
        expected_resulting_state=None,
        actual_resulting_state=None,
        expected_event_time_utc=None,
        actual_event_time_utc=None,
        expected_availability_time_utc=_BASE_TIME,
        actual_availability_time_utc=_BASE_TIME + timedelta(minutes=1),
    )
    assert (
        mismatch.expected_availability_time_utc != mismatch.actual_availability_time_utc
    )


def test_lifecycle_validation_detects_source_record_id_mismatch() -> None:
    expected = (_transition(0, 0),)
    actual = (_transition(1, 0),)
    report = build_lifecycle_validation_report(expected, actual)
    assert len(report.missing_events) == 1
    assert len(report.extra_events) == 1
    assert (
        report.missing_events[0].source_record_id
        != report.extra_events[0].source_record_id
    )
