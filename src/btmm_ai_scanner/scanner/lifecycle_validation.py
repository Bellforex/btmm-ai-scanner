from datetime import datetime
from typing import Any

from btmm_ai_scanner.contracts.types import ContractModel, UUIDv7


class LifecycleMismatch(ContractModel):
    source_record_id: UUIDv7
    expected_event_type: str | None
    actual_event_type: str | None
    expected_prior_state: str | None
    actual_prior_state: str | None
    expected_resulting_state: str | None
    actual_resulting_state: str | None
    expected_event_time_utc: datetime | None
    actual_event_time_utc: datetime | None
    expected_availability_time_utc: datetime | None
    actual_availability_time_utc: datetime | None


class LifecycleValidationReport(ContractModel):
    matched_event_count: int
    missing_events: tuple[LifecycleMismatch, ...]
    extra_events: tuple[LifecycleMismatch, ...]
    duplicated_events: tuple[LifecycleMismatch, ...]
    reordered_events: tuple[LifecycleMismatch, ...]


def _to_mismatch(expected: Any, actual: Any) -> LifecycleMismatch:
    source_record_id = expected.record_id if expected is not None else actual.record_id
    return LifecycleMismatch(
        source_record_id=source_record_id,
        expected_event_type=str(expected.transition_type)
        if expected is not None
        else None,
        actual_event_type=str(actual.transition_type) if actual is not None else None,
        expected_prior_state=None,
        actual_prior_state=None,
        expected_resulting_state=None,
        actual_resulting_state=None,
        expected_event_time_utc=expected.event_time_utc
        if expected is not None
        else None,
        actual_event_time_utc=actual.event_time_utc if actual is not None else None,
        expected_availability_time_utc=(
            expected.availability_time_utc if expected is not None else None
        ),
        actual_availability_time_utc=(
            actual.availability_time_utc if actual is not None else None
        ),
    )


def build_lifecycle_validation_report(
    expected_transitions: tuple[Any, ...],
    actual_transitions: tuple[Any, ...],
) -> LifecycleValidationReport:
    expected_by_id = {t.record_id: t for t in expected_transitions}
    actual_by_id = {t.record_id: t for t in actual_transitions}

    expected_ids_in_order = [t.record_id for t in expected_transitions]
    actual_ids_in_order = [t.record_id for t in actual_transitions]

    expected_id_set = set(expected_ids_in_order)
    actual_id_set = set(actual_ids_in_order)
    common_ids = expected_id_set & actual_id_set

    missing_events = tuple(
        _to_mismatch(expected_by_id[rid], None)
        for rid in expected_ids_in_order
        if rid not in actual_id_set
    )
    extra_events = tuple(
        _to_mismatch(None, actual_by_id[rid])
        for rid in actual_ids_in_order
        if rid not in expected_id_set
    )

    duplicated_events = []
    seen_actual: set[UUIDv7] = set()
    for rid in actual_ids_in_order:
        if rid in seen_actual and rid in common_ids:
            duplicated_events.append(
                _to_mismatch(expected_by_id.get(rid), actual_by_id.get(rid))
            )
        seen_actual.add(rid)

    expected_common_order = [rid for rid in expected_ids_in_order if rid in common_ids]
    actual_common_order = [rid for rid in actual_ids_in_order if rid in common_ids]
    reordered_events = tuple(
        _to_mismatch(expected_by_id[rid], actual_by_id[rid])
        for rid in common_ids
        if expected_common_order.index(rid) != actual_common_order.index(rid)
    )

    matched_event_count = len(common_ids) - len(reordered_events)

    return LifecycleValidationReport(
        matched_event_count=matched_event_count,
        missing_events=missing_events,
        extra_events=extra_events,
        duplicated_events=tuple(duplicated_events),
        reordered_events=reordered_events,
    )
