from collections.abc import Sequence
from datetime import datetime

from btmm_ai_scanner.contracts.normalized_candle import NormalizedCandle
from btmm_ai_scanner.contracts.raw_candle import RawCandle
from btmm_ai_scanner.market_data.results import IngestionOutcome, IngestionResult

SourceCandleIdentity = tuple[str, str, str, str, datetime]


def _identity_of(raw_candle: RawCandle) -> SourceCandleIdentity:
    return (
        raw_candle.provider,
        raw_candle.source_reference,
        raw_candle.source_symbol,
        raw_candle.source_timeframe,
        raw_candle.event_time_utc,
    )


def evaluate_idempotency(
    candidate_raw_candle: RawCandle,
    candidate_normalized_candle: NormalizedCandle,
    existing_raw_candles: Sequence[RawCandle],
) -> IngestionResult:
    candidate_identity = _identity_of(candidate_raw_candle)

    exact_match: RawCandle | None = None
    conflicting_match: RawCandle | None = None

    for existing in existing_raw_candles:
        if _identity_of(existing) != candidate_identity:
            continue
        if existing.content_fingerprint == candidate_raw_candle.content_fingerprint:
            if exact_match is None:
                exact_match = existing
        elif conflicting_match is None:
            conflicting_match = existing

    if conflicting_match is not None:
        return IngestionResult(
            outcome=IngestionOutcome.CONFLICTING_REVISION,
            reason_codes=("CONFLICTING_REVISION_DETECTED",),
            candidate_raw_candle=candidate_raw_candle,
            candidate_normalized_candle=None,
            existing_record_id=conflicting_match.record_id,
        )

    if exact_match is not None:
        return IngestionResult(
            outcome=IngestionOutcome.EXACT_DUPLICATE,
            reason_codes=(),
            candidate_raw_candle=candidate_raw_candle,
            candidate_normalized_candle=None,
            existing_record_id=exact_match.record_id,
        )

    return IngestionResult(
        outcome=IngestionOutcome.ACCEPTED,
        reason_codes=(),
        candidate_raw_candle=candidate_raw_candle,
        candidate_normalized_candle=candidate_normalized_candle,
        existing_record_id=None,
    )
