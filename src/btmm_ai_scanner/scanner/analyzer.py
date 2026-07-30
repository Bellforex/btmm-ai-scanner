from collections.abc import Sequence
from datetime import UTC, datetime

from btmm_ai_scanner.btmm.analyzer import BtmmAnalysis, BtmmTimeframeInput, analyze_btmm
from btmm_ai_scanner.btmm.reviewed_evidence import BtmmReviewedEvidence
from btmm_ai_scanner.config.enums import InternalSymbol, Timeframe
from btmm_ai_scanner.contracts.provenance_record import EvidenceClassification
from btmm_ai_scanner.contracts.types import UUIDv7
from btmm_ai_scanner.domain.analyzer import (
    DerivedOutputIdentityProvider,
    MarketMeasurementAnalysis,
    MixedSymbolAnalysisError,
    analyze_market_measurements,
)
from btmm_ai_scanner.poi.analyzer import PoiAnalysis, PoiTimeframeInput, analyze_pois
from btmm_ai_scanner.poi.enums import PoiLifecycleStatus
from btmm_ai_scanner.scanner.analysis import ScannerAnalysis, ScannerSetupSummary
from btmm_ai_scanner.scanner.configuration import (
    ScannerConfiguration,
    validate_configuration,
)
from btmm_ai_scanner.scanner.timeframe_input import ScannerTimeframeInput
from btmm_ai_scanner.structure.analyzer import (
    StructureAnalysis,
    analyze_structure_state,
)

_EPOCH = datetime(1970, 1, 1, tzinfo=UTC)

_TIMEFRAME_RANK: dict[Timeframe, int] = {
    Timeframe.M1: 1,
    Timeframe.M5: 2,
    Timeframe.M15: 3,
    Timeframe.H1: 4,
    Timeframe.H3: 5,
    Timeframe.H4: 6,
    Timeframe.D1: 7,
    Timeframe.W1: 8,
}


class MissingRequiredTimeframeError(ValueError):
    pass


class InvalidScannerCandleInputError(ValueError):
    pass


def _validate_bundle_candles(
    bundle: ScannerTimeframeInput, enabled_symbols: frozenset[InternalSymbol]
) -> None:
    for candle in bundle.candles:
        if candle.timeframe != bundle.timeframe:
            raise InvalidScannerCandleInputError(
                f"candle {candle.record_id} carries timeframe {candle.timeframe}, "
                f"which disagrees with its declared bundle timeframe {bundle.timeframe}."
            )
        if candle.symbol not in enabled_symbols:
            raise InvalidScannerCandleInputError(
                f"candle {candle.record_id} carries symbol {candle.symbol}, "
                "which is not among the configured enabled_symbols."
            )


def _validate_scanner_timeframe_inputs(
    timeframe_inputs: tuple[ScannerTimeframeInput, ...],
    configuration: ScannerConfiguration,
) -> None:
    seen_timeframes: set[Timeframe] = set()
    accepted_timeframes = (
        configuration.required_timeframes | configuration.optional_timeframes
    )

    for bundle in timeframe_inputs:
        if bundle.timeframe in seen_timeframes:
            raise InvalidScannerCandleInputError(
                f"timeframe {bundle.timeframe} appears in more than one"
                " ScannerTimeframeInput bundle."
            )
        seen_timeframes.add(bundle.timeframe)

        if bundle.timeframe not in accepted_timeframes:
            raise InvalidScannerCandleInputError(
                f"timeframe {bundle.timeframe} is not among the configured"
                " required_timeframes or optional_timeframes."
            )

        _validate_bundle_candles(bundle, configuration.enabled_symbols)

    missing_required = configuration.required_timeframes - seen_timeframes
    if len(missing_required) > 0:
        raise MissingRequiredTimeframeError(
            "Missing required timeframe(s): "
            f"{sorted(missing_required, key=lambda t: _TIMEFRAME_RANK[t])}."
        )


def _all_symbol(
    timeframe_inputs: tuple[ScannerTimeframeInput, ...],
) -> InternalSymbol | None:
    symbols = {
        candle.symbol for bundle in timeframe_inputs for candle in bundle.candles
    }
    if len(symbols) == 0:
        return None
    if len(symbols) > 1:
        raise MixedSymbolAnalysisError(
            f"Mixed symbols supplied in one scan_market call: {sorted(symbols)}."
        )
    return next(iter(symbols))


def _empty_scanner_analysis(
    configuration: ScannerConfiguration,
    identity_provider: DerivedOutputIdentityProvider,
) -> ScannerAnalysis:
    poi_analysis = analyze_pois((), configuration.poi_configuration, identity_provider)
    btmm_analysis = analyze_btmm(
        (), poi_analysis, (), configuration.btmm_configuration, identity_provider
    )
    return ScannerAnalysis(
        symbol=None,
        processed_timeframes=(),
        measurement_analyses=(),
        structure_analyses=(),
        poi_analysis=poi_analysis,
        btmm_analysis=btmm_analysis,
        setup_summaries=(),
        availability_time_utc=_EPOCH,
        evidence_classification=EvidenceClassification.ENGINEERING_PROVISIONAL,
        rule_version=configuration.rule_version,
        contract_version=configuration.contract_version,
        schema_version=configuration.schema_version,
    )


def _current_poi_lifecycle_status(
    poi_analysis: PoiAnalysis, source_poi_record_id: UUIDv7
) -> PoiLifecycleStatus | None:
    for state in poi_analysis.current_poi_states:
        if state.poi_record_id == source_poi_record_id:
            return state.poi_lifecycle_status
    return None


def _build_setup_summaries(
    poi_analysis: PoiAnalysis, btmm_analysis: BtmmAnalysis
) -> tuple[ScannerSetupSummary, ...]:
    observations_by_id = {
        observation.record_id: observation
        for observation in btmm_analysis.btmm_observations
    }

    summaries: list[ScannerSetupSummary] = []
    for state in btmm_analysis.current_btmm_states:
        observation = observations_by_id[state.btmm_setup_record_id]
        summaries.append(
            ScannerSetupSummary(
                source_btmm_observation_record_id=observation.record_id,
                source_poi_record_id=observation.source_poi_record_id,
                symbol=state.symbol,
                btmm_direction=state.btmm_direction,
                source_poi_type=state.source_poi_type,
                timeframe=state.timeframe,
                poi_lifecycle_status=_current_poi_lifecycle_status(
                    poi_analysis, observation.source_poi_record_id
                ),
                btmm_primary_state=state.primary_state,
                interaction_class=state.interaction_class,
                reaction_classification=state.reaction_classification,
                liquidity_evidence_status=state.liquidity_evidence_status,
                market_direction_status=state.market_direction_status,
                analytical_framework_status=state.analytical_framework_status,
                volume_pillar_status=state.volume_pillar_status,
                availability_time_utc=state.availability_time_utc,
                evidence_classification=state.evidence_classification,
                rule_version=state.rule_version,
                contract_version=state.contract_version,
                schema_version=state.schema_version,
            )
        )

    summaries.sort(
        key=lambda s: (
            _TIMEFRAME_RANK[s.timeframe],
            str(s.source_btmm_observation_record_id),
        )
    )
    return tuple(summaries)


def scan_market(
    timeframe_inputs: tuple[ScannerTimeframeInput, ...],
    reviewed_evidence: tuple[BtmmReviewedEvidence, ...],
    configuration: ScannerConfiguration,
    identity_provider: DerivedOutputIdentityProvider,
) -> ScannerAnalysis:
    validate_configuration(configuration)

    if len(timeframe_inputs) == 0:
        if len(configuration.required_timeframes) == 0:
            return _empty_scanner_analysis(configuration, identity_provider)
        raise MissingRequiredTimeframeError(
            "timeframe_inputs is empty but configuration.required_timeframes is"
            " non-empty."
        )

    _validate_scanner_timeframe_inputs(timeframe_inputs, configuration)
    symbol = _all_symbol(timeframe_inputs)

    ordered_inputs = tuple(
        sorted(timeframe_inputs, key=lambda bundle: _TIMEFRAME_RANK[bundle.timeframe])
    )

    measurement_analyses: list[MarketMeasurementAnalysis] = []
    structure_analyses: list[StructureAnalysis] = []
    poi_timeframe_inputs: list[PoiTimeframeInput] = []
    measurement_by_timeframe: dict[Timeframe, MarketMeasurementAnalysis] = {}

    for bundle in ordered_inputs:
        measurement_analysis = analyze_market_measurements(
            bundle.candles,
            configuration.measurement_configuration,
            identity_provider,
        )
        measurement_analyses.append(measurement_analysis)
        measurement_by_timeframe[bundle.timeframe] = measurement_analysis

        structure_analysis = analyze_structure_state(
            bundle.candles,
            measurement_analysis.confirmed_swings,
            configuration.structure_configuration,
            identity_provider,
        )
        structure_analyses.append(structure_analysis)

        poi_timeframe_inputs.append(
            PoiTimeframeInput(
                timeframe=bundle.timeframe,
                candles=bundle.candles,
                measurement_analysis=measurement_analysis,
            )
        )

    poi_analysis = analyze_pois(
        tuple(poi_timeframe_inputs),
        configuration.poi_configuration,
        identity_provider,
    )

    btmm_eligible_timeframes = (
        configuration.btmm_configuration.formation_timeframes
        | configuration.btmm_configuration.supporting_only_timeframes
    )
    btmm_timeframe_inputs = tuple(
        BtmmTimeframeInput(
            timeframe=bundle.timeframe,
            candles=bundle.candles,
            measurement_analysis=measurement_by_timeframe[bundle.timeframe],
        )
        for bundle in ordered_inputs
        if bundle.timeframe in btmm_eligible_timeframes
    )

    max_candle_availability = _max_candle_availability(ordered_inputs)
    gated_evidence = tuple(
        evidence
        for evidence in reviewed_evidence
        if evidence.availability_time_utc <= max_candle_availability
    )

    btmm_analysis = analyze_btmm(
        btmm_timeframe_inputs,
        poi_analysis,
        gated_evidence,
        configuration.btmm_configuration,
        identity_provider,
    )

    setup_summaries = _build_setup_summaries(poi_analysis, btmm_analysis)

    return ScannerAnalysis(
        symbol=symbol,
        processed_timeframes=tuple(bundle.timeframe for bundle in ordered_inputs),
        measurement_analyses=tuple(measurement_analyses),
        structure_analyses=tuple(structure_analyses),
        poi_analysis=poi_analysis,
        btmm_analysis=btmm_analysis,
        setup_summaries=setup_summaries,
        availability_time_utc=max_candle_availability,
        evidence_classification=EvidenceClassification.ENGINEERING_PROVISIONAL,
        rule_version=configuration.rule_version,
        contract_version=configuration.contract_version,
        schema_version=configuration.schema_version,
    )


def _max_candle_availability(
    ordered_inputs: Sequence[ScannerTimeframeInput],
) -> datetime:
    return max(
        candle.availability_time_utc
        for bundle in ordered_inputs
        for candle in bundle.candles
    )
