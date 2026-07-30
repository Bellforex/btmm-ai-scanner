from decimal import Decimal

from btmm_ai_scanner.btmm.observation import BtmmObservation
from btmm_ai_scanner.config.enums import InternalSymbol
from btmm_ai_scanner.contracts.types import ContractModel, UUIDv7
from btmm_ai_scanner.poi.observation import PoiObservation
from btmm_ai_scanner.scanner.enums import LabelMatchStatus
from btmm_ai_scanner.scanner.labels import ExpectedBtmmLabel, ExpectedPoiLabel

_NEG_INFINITY = Decimal("-Infinity")
_POS_INFINITY = Decimal("Infinity")


class LabelMatch(ContractModel):
    expected_label_id: str | None
    detected_record_id: UUIDv7 | None
    status: LabelMatchStatus
    overlap_ratio: Decimal | None
    availability_delay: Decimal | None
    boundary_error_ticks: Decimal | None


def zone_overlap_ratio(
    a_top: Decimal, a_bottom: Decimal, b_top: Decimal, b_bottom: Decimal
) -> Decimal:
    intersection = max(Decimal("0"), min(a_top, b_top) - max(a_bottom, b_bottom))
    union = (a_top - a_bottom) + (b_top - b_bottom) - intersection
    if union > 0:
        return intersection / union
    if a_top == a_bottom and b_top == b_bottom and a_top == b_top:
        return Decimal("1")
    return Decimal("0")


def _sort_key(
    overlap_ratio: Decimal | None,
    availability_delay: Decimal | None,
    boundary_error_ticks: Decimal | None,
    expected_label_id: str,
    detected_record_id: UUIDv7,
) -> tuple[Decimal, Decimal, Decimal, str, str]:
    return (
        -(overlap_ratio if overlap_ratio is not None else _NEG_INFINITY),
        abs(availability_delay) if availability_delay is not None else _POS_INFINITY,
        boundary_error_ticks if boundary_error_ticks is not None else _POS_INFINITY,
        expected_label_id,
        str(detected_record_id),
    )


def match_poi_detections(
    symbol: InternalSymbol,
    expected_labels: tuple[ExpectedPoiLabel, ...],
    detections: tuple[PoiObservation, ...],
    case_complete: bool,
) -> tuple[LabelMatch, ...]:
    candidates: list[
        tuple[
            tuple[Decimal, Decimal, Decimal, str, str],
            ExpectedPoiLabel,
            PoiObservation,
            Decimal,
            Decimal,
            Decimal,
        ]
    ] = []

    for label in expected_labels:
        for detection in detections:
            if detection.symbol != symbol:
                continue
            if detection.source_timeframe != label.expected_timeframe:
                continue
            if detection.direction != label.expected_direction:
                continue
            if detection.poi_type != label.expected_poi_type:
                continue
            if not (
                label.earliest_valid_availability_time_utc
                <= detection.availability_time_utc
                <= label.latest_acceptable_availability_time_utc
            ):
                continue

            overlap_ratio = zone_overlap_ratio(
                label.expected_zone_top,
                label.expected_zone_bottom,
                detection.zone_top,
                detection.zone_bottom,
            )
            availability_delay = Decimal(
                (
                    detection.availability_time_utc
                    - label.earliest_valid_availability_time_utc
                ).total_seconds()
            )
            boundary_error_ticks = max(
                abs(label.expected_zone_top - detection.zone_top),
                abs(label.expected_zone_bottom - detection.zone_bottom),
            )

            key = _sort_key(
                overlap_ratio,
                availability_delay,
                boundary_error_ticks,
                label.label_id,
                detection.record_id,
            )
            candidates.append(
                (
                    key,
                    label,
                    detection,
                    overlap_ratio,
                    availability_delay,
                    boundary_error_ticks,
                )
            )

    candidates.sort(key=lambda c: c[0])

    matched_label_ids: set[str] = set()
    matched_detection_ids: set[UUIDv7] = set()
    matches: list[LabelMatch] = []

    for (
        _key,
        label,
        detection,
        overlap_ratio,
        availability_delay,
        boundary_error_ticks,
    ) in candidates:
        if label.label_id in matched_label_ids:
            continue
        if detection.record_id in matched_detection_ids:
            continue
        matched_label_ids.add(label.label_id)
        matched_detection_ids.add(detection.record_id)
        matches.append(
            LabelMatch(
                expected_label_id=label.label_id,
                detected_record_id=detection.record_id,
                status=LabelMatchStatus.MATCHED,
                overlap_ratio=overlap_ratio,
                availability_delay=availability_delay,
                boundary_error_ticks=boundary_error_ticks,
            )
        )

    for label in expected_labels:
        if label.label_id not in matched_label_ids:
            matches.append(
                LabelMatch(
                    expected_label_id=label.label_id,
                    detected_record_id=None,
                    status=LabelMatchStatus.MISSED,
                    overlap_ratio=None,
                    availability_delay=None,
                    boundary_error_ticks=None,
                )
            )

    unexpected_status = (
        LabelMatchStatus.UNEXPECTED if case_complete else LabelMatchStatus.UNREVIEWED
    )
    for detection in detections:
        if detection.symbol != symbol:
            continue
        if detection.record_id not in matched_detection_ids:
            matches.append(
                LabelMatch(
                    expected_label_id=None,
                    detected_record_id=detection.record_id,
                    status=unexpected_status,
                    overlap_ratio=None,
                    availability_delay=None,
                    boundary_error_ticks=None,
                )
            )

    matches.sort(
        key=lambda m: (
            m.expected_label_id if m.expected_label_id is not None else "",
            str(m.detected_record_id) if m.detected_record_id is not None else "",
        )
    )
    return tuple(matches)


def _btmm_reference_time(label: ExpectedBtmmLabel):  # type: ignore[no-untyped-def]
    candidates = [
        value
        for value in (
            label.expected_candidate_availability_time_utc,
            label.expected_forming_availability_time_utc,
            label.expected_confirmation_or_cancellation_time_utc,
        )
        if value is not None
    ]
    return min(candidates) if len(candidates) > 0 else None


def match_btmm_detections(
    symbol: InternalSymbol,
    expected_labels: tuple[ExpectedBtmmLabel, ...],
    detections: tuple[BtmmObservation, ...],
    case_complete: bool,
) -> tuple[LabelMatch, ...]:
    candidates: list[
        tuple[
            tuple[Decimal, Decimal, Decimal, str, str],
            ExpectedBtmmLabel,
            BtmmObservation,
            Decimal | None,
        ]
    ] = []

    for label in expected_labels:
        reference_time = _btmm_reference_time(label)
        for detection in detections:
            if detection.symbol != symbol:
                continue
            if detection.source_timeframe != label.expected_timeframe:
                continue
            if detection.btmm_direction != label.expected_direction:
                continue

            availability_delay = (
                Decimal(
                    (detection.availability_time_utc - reference_time).total_seconds()
                )
                if reference_time is not None
                else None
            )

            key = _sort_key(
                None,
                availability_delay,
                None,
                label.label_id,
                detection.record_id,
            )
            candidates.append((key, label, detection, availability_delay))

    candidates.sort(key=lambda c: c[0])

    matched_label_ids: set[str] = set()
    matched_detection_ids: set[UUIDv7] = set()
    matches: list[LabelMatch] = []

    for _key, label, detection, availability_delay in candidates:
        if label.label_id in matched_label_ids:
            continue
        if detection.record_id in matched_detection_ids:
            continue
        matched_label_ids.add(label.label_id)
        matched_detection_ids.add(detection.record_id)
        matches.append(
            LabelMatch(
                expected_label_id=label.label_id,
                detected_record_id=detection.record_id,
                status=LabelMatchStatus.MATCHED,
                overlap_ratio=None,
                availability_delay=availability_delay,
                boundary_error_ticks=None,
            )
        )

    for label in expected_labels:
        if label.label_id not in matched_label_ids:
            matches.append(
                LabelMatch(
                    expected_label_id=label.label_id,
                    detected_record_id=None,
                    status=LabelMatchStatus.MISSED,
                    overlap_ratio=None,
                    availability_delay=None,
                    boundary_error_ticks=None,
                )
            )

    unexpected_status = (
        LabelMatchStatus.UNEXPECTED if case_complete else LabelMatchStatus.UNREVIEWED
    )
    for detection in detections:
        if detection.symbol != symbol:
            continue
        if detection.record_id not in matched_detection_ids:
            matches.append(
                LabelMatch(
                    expected_label_id=None,
                    detected_record_id=detection.record_id,
                    status=unexpected_status,
                    overlap_ratio=None,
                    availability_delay=None,
                    boundary_error_ticks=None,
                )
            )

    matches.sort(
        key=lambda m: (
            m.expected_label_id if m.expected_label_id is not None else "",
            str(m.detected_record_id) if m.detected_record_id is not None else "",
        )
    )
    return tuple(matches)
