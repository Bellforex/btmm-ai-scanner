import hashlib
import json
from collections.abc import Callable
from datetime import UTC
from decimal import Decimal
from enum import Enum
from itertools import pairwise
from typing import Any, Protocol
from uuid import UUID

from btmm_ai_scanner.config.enums import InternalSymbol, Timeframe
from btmm_ai_scanner.contracts.normalized_candle import NormalizedCandle
from btmm_ai_scanner.contracts.types import ContractModel, SemVer, UUIDv7
from btmm_ai_scanner.domain.configuration import MarketMeasurementConfiguration
from btmm_ai_scanner.domain.displacement import (
    DisplacementObservation,
    detect_displacement_observations,
)
from btmm_ai_scanner.domain.enums import DerivedOutputType
from btmm_ai_scanner.domain.equal_levels import (
    EqualLevelCluster,
    detect_equal_level_clusters,
)
from btmm_ai_scanner.domain.support_resistance import (
    SupportResistanceZone,
    detect_support_resistance_zones,
)
from btmm_ai_scanner.domain.swings import ConfirmedSwing, detect_confirmed_swings
from btmm_ai_scanner.domain.trendlines import Trendline, detect_trendlines


class MixedSymbolAnalysisError(ValueError):
    pass


class MixedTimeframeAnalysisError(ValueError):
    pass


class UnsortedCandleSequenceError(ValueError):
    pass


class DuplicateCandleRecordError(ValueError):
    pass


class AmbiguousEventTimeAnalysisError(ValueError):
    pass


class InvalidMarketMeasurementConfigurationError(ValueError):
    pass


class DerivedIdentityCollisionError(ValueError):
    pass


class DerivedOutputIdentityProvider(Protocol):
    def identify(
        self, *, output_type: DerivedOutputType, semantic_key: tuple[str, ...]
    ) -> UUIDv7: ...


class MarketMeasurementAnalysis(ContractModel):
    symbol: InternalSymbol | None
    timeframe: Timeframe | None
    analyzed_candle_count: int
    confirmed_swings: tuple[ConfirmedSwing, ...]
    displacement_observations: tuple[DisplacementObservation, ...]
    equal_level_clusters: tuple[EqualLevelCluster, ...]
    support_resistance_zones: tuple[SupportResistanceZone, ...]
    trendlines: tuple[Trendline, ...]


def _canonicalize(value: object) -> object:
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, Decimal):
        if value == 0:
            return "0"
        return format(value.normalize(), "f")
    if isinstance(value, int):
        return value
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, SemVer):
        return str(value)
    if hasattr(value, "astimezone") and hasattr(value, "isoformat"):
        return value.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%S.%f") + "Z"
    if isinstance(value, str):
        return value
    if isinstance(value, tuple | list):
        return [_canonicalize(item) for item in value]
    if isinstance(value, dict):
        return {key: _canonicalize(item) for key, item in value.items()}
    raise TypeError(f"Cannot canonicalize value of type {type(value)!r}")


def _compute_content_fingerprint(fields: dict[str, object]) -> str:
    canonical = _canonicalize(fields)
    serialized = json.dumps(canonical, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def _validate_candles(candles: tuple[NormalizedCandle, ...]) -> None:
    if len(candles) == 0:
        return

    for candle in candles:
        if candle.symbol is None or candle.timeframe is None:
            raise InvalidMarketMeasurementConfigurationError(
                "Every candle must carry non-null symbol and timeframe instrument "
                "metadata; analyze_market_measurements does not infer missing "
                "instrument identity."
            )

    symbols = {candle.symbol for candle in candles}
    if len(symbols) > 1:
        raise MixedSymbolAnalysisError(
            "analyze_market_measurements requires exactly one InternalSymbol."
        )

    timeframes = {candle.timeframe for candle in candles}
    if len(timeframes) > 1:
        raise MixedTimeframeAnalysisError(
            "analyze_market_measurements requires exactly one Timeframe."
        )

    seen_record_ids: set[UUID] = set()
    for candle in candles:
        if candle.record_id in seen_record_ids:
            raise DuplicateCandleRecordError(
                f"record_id {candle.record_id} appears more than once in the input."
            )
        seen_record_ids.add(candle.record_id)

    for previous, current in pairwise(candles):
        if current.event_time_utc == previous.event_time_utc:
            raise AmbiguousEventTimeAnalysisError(
                "Two distinct candle records share the same event_time_utc; "
                "revision selection is a caller responsibility."
            )
        if current.event_time_utc < previous.event_time_utc:
            raise UnsortedCandleSequenceError(
                "candles must be canonically ordered by (event_time_utc, record_id)."
            )


class _IdentityResolver:
    def __init__(self, provider: DerivedOutputIdentityProvider) -> None:
        self._provider = provider
        self._issued: dict[UUID, tuple[str, ...]] = {}

    def resolve(
        self, output_type: DerivedOutputType, semantic_key: tuple[str, ...]
    ) -> UUID:
        record_id = self._provider.identify(
            output_type=output_type, semantic_key=semantic_key
        )
        existing = self._issued.get(record_id)
        if existing is not None and existing != semantic_key:
            raise DerivedIdentityCollisionError(
                f"identity provider returned {record_id} for two different "
                "semantic keys within one analysis call."
            )
        self._issued[record_id] = semantic_key
        return record_id


def _finalize[ContractT: ContractModel](
    candidates: list[Any],
    output_type: DerivedOutputType,
    contract_class: type[ContractT],
    semantic_key_fn: Callable[[Any], tuple[str, ...]],
    extra_fields_fn: Callable[[Any], dict[str, object]],
    excluded_candidate_fields: frozenset[str],
    configuration: MarketMeasurementConfiguration,
    resolver: _IdentityResolver,
) -> tuple[ContractT, ...]:
    results: list[ContractT] = []
    for candidate in candidates:
        semantic_key = semantic_key_fn(candidate)
        record_id = resolver.resolve(output_type, semantic_key)
        provenance_id = resolver.resolve(output_type, (*semantic_key, "provenance"))

        fields: dict[str, object] = dict(candidate._asdict())
        for excluded in excluded_candidate_fields:
            fields.pop(excluded, None)
        fields.update(extra_fields_fn(candidate))
        fields.update(
            rule_version=configuration.rule_version,
            contract_version=configuration.contract_version,
            schema_version=configuration.schema_version,
            evidence_classification=configuration.evidence_classification,
            provenance_id=provenance_id,
        )

        content_fingerprint = _compute_content_fingerprint(fields)
        # A generic TypeVar call site cannot statically see the concrete
        # subclass's fields; every one of the 5 contract classes passed here
        # genuinely accepts record_id/content_fingerprint plus **fields.
        results.append(
            contract_class(  # type: ignore[call-arg]
                record_id=record_id,
                content_fingerprint=content_fingerprint,
                **fields,
            )
        )
    return tuple(results)


def analyze_market_measurements(
    candles: tuple[NormalizedCandle, ...],
    configuration: MarketMeasurementConfiguration,
    identity_provider: DerivedOutputIdentityProvider,
) -> MarketMeasurementAnalysis:
    _validate_candles(candles)

    if len(candles) == 0:
        return MarketMeasurementAnalysis(
            symbol=None,
            timeframe=None,
            analyzed_candle_count=0,
            confirmed_swings=(),
            displacement_observations=(),
            equal_level_clusters=(),
            support_resistance_zones=(),
            trendlines=(),
        )

    resolver = _IdentityResolver(identity_provider)
    rule_version_text = str(configuration.rule_version)

    swing_candidates = detect_confirmed_swings(candles, configuration)
    confirmed_swings = _finalize(
        list(swing_candidates),
        DerivedOutputType.CONFIRMED_SWING,
        ConfirmedSwing,
        lambda c: (
            c.symbol.value,
            c.timeframe.value,
            c.swing_type.value,
            str(c.pivot_candle_record_ids[0]),
            str(c.confirmation_candle_id),
            rule_version_text,
        ),
        lambda c: {"availability_time_utc": c.meaningful_confirmation_time_utc},
        frozenset(),
        configuration,
        resolver,
    )

    displacement_candidates = detect_displacement_observations(candles, configuration)
    displacement_observations = _finalize(
        list(displacement_candidates),
        DerivedOutputType.DISPLACEMENT_OBSERVATION,
        DisplacementObservation,
        lambda c: (
            c.symbol.value,
            c.timeframe.value,
            str(c.candle_record_id),
            rule_version_text,
        ),
        lambda c: {},
        frozenset(),
        configuration,
        resolver,
    )

    equal_level_candidates = detect_equal_level_clusters(
        tuple(confirmed_swings), configuration
    )
    equal_level_clusters = _finalize(
        list(equal_level_candidates),
        DerivedOutputType.EQUAL_LEVEL_CLUSTER,
        EqualLevelCluster,
        lambda c: (
            c.symbol.value,
            c.timeframe.value,
            c.cluster_type.value,
            str(c.first_seed_swing_id),
            str(c.second_seed_swing_id),
            rule_version_text,
        ),
        lambda c: {"availability_time_utc": c.confirmation_time_utc},
        frozenset({"first_seed_swing_id", "second_seed_swing_id"}),
        configuration,
        resolver,
    )

    support_resistance_candidates = detect_support_resistance_zones(
        candles, tuple(confirmed_swings), configuration
    )
    support_resistance_zones = _finalize(
        list(support_resistance_candidates),
        DerivedOutputType.SUPPORT_RESISTANCE_ZONE,
        SupportResistanceZone,
        lambda c: (
            c.symbol.value,
            c.timeframe.value,
            c.zone_type.value,
            str(c.origin_swing_record_id),
            str(c.confirmation_candle_id),
            rule_version_text,
        ),
        lambda c: {"availability_time_utc": c.confirmation_time_utc},
        frozenset(),
        configuration,
        resolver,
    )

    trendline_candidates = detect_trendlines(
        candles, tuple(confirmed_swings), configuration
    )
    trendlines = _finalize(
        list(trendline_candidates),
        DerivedOutputType.TRENDLINE,
        Trendline,
        lambda c: (
            c.symbol.value,
            c.timeframe.value,
            c.orientation.value,
            str(c.anchor_1_swing_record_id),
            str(c.anchor_2_swing_record_id),
            str(c.confirmation_candle_id),
            rule_version_text,
        ),
        lambda c: {"availability_time_utc": c.confirmation_time_utc},
        frozenset(),
        configuration,
        resolver,
    )

    return MarketMeasurementAnalysis(
        symbol=candles[0].symbol,
        timeframe=candles[0].timeframe,
        analyzed_candle_count=len(candles),
        confirmed_swings=confirmed_swings,
        displacement_observations=displacement_observations,
        equal_level_clusters=equal_level_clusters,
        support_resistance_zones=support_resistance_zones,
        trendlines=trendlines,
    )
