from decimal import Decimal

from btmm_ai_scanner.btmm.configuration import BtmmConfiguration
from btmm_ai_scanner.config.enums import InternalSymbol, Timeframe
from btmm_ai_scanner.contracts.types import ContractModel, SemVer
from btmm_ai_scanner.domain.configuration import MarketMeasurementConfiguration
from btmm_ai_scanner.poi.configuration import PoiConfiguration
from btmm_ai_scanner.scanner.enums import SnapshotRetentionPolicy
from btmm_ai_scanner.structure.configuration import StructureConfiguration

_DEFAULT_ENABLED_SYMBOLS: frozenset[InternalSymbol] = frozenset(
    {InternalSymbol.XAUUSD, InternalSymbol.EURUSD, InternalSymbol.GBPUSD}
)
_DEFAULT_REQUIRED_TIMEFRAMES: frozenset[Timeframe] = frozenset(
    {Timeframe.M1, Timeframe.M5, Timeframe.M15}
)
_DEFAULT_OPTIONAL_TIMEFRAMES: frozenset[Timeframe] = frozenset(
    {Timeframe.H1, Timeframe.H3, Timeframe.H4, Timeframe.D1, Timeframe.W1}
)


class InvalidScannerConfigurationError(ValueError):
    pass


class ScannerConfiguration(ContractModel):
    measurement_configuration: MarketMeasurementConfiguration
    structure_configuration: StructureConfiguration
    poi_configuration: PoiConfiguration
    btmm_configuration: BtmmConfiguration

    enabled_symbols: frozenset[InternalSymbol] = _DEFAULT_ENABLED_SYMBOLS
    required_timeframes: frozenset[Timeframe] = _DEFAULT_REQUIRED_TIMEFRAMES
    optional_timeframes: frozenset[Timeframe] = _DEFAULT_OPTIONAL_TIMEFRAMES

    rule_version: SemVer = SemVer.parse("0.1.0")
    contract_version: SemVer = SemVer.parse("0.1.0")
    schema_version: SemVer = SemVer.parse("0.1.0")


def validate_configuration(configuration: ScannerConfiguration) -> None:
    if not configuration.required_timeframes.isdisjoint(
        configuration.optional_timeframes
    ):
        raise InvalidScannerConfigurationError(
            "required_timeframes and optional_timeframes must be disjoint."
        )
    if len(configuration.enabled_symbols) == 0:
        raise InvalidScannerConfigurationError("enabled_symbols must be non-empty.")

    # StructureConfiguration owns no minimum_price_tick field and is
    # deliberately excluded from this invariant (1B-L-SCANNER-A1).
    measurement_tick = configuration.measurement_configuration.minimum_price_tick
    poi_tick = configuration.poi_configuration.minimum_price_tick
    btmm_tick = configuration.btmm_configuration.minimum_price_tick
    if not (measurement_tick == poi_tick == btmm_tick):
        raise InvalidScannerConfigurationError(
            "measurement_configuration.minimum_price_tick, "
            "poi_configuration.minimum_price_tick, and "
            "btmm_configuration.minimum_price_tick must all be equal; got "
            f"{measurement_tick}, {poi_tick}, {btmm_tick}."
        )


def canonical_minimum_price_tick(configuration: ScannerConfiguration) -> Decimal:
    """The single validated Decimal tick shared by measurement/POI/BTMM configuration."""
    return configuration.measurement_configuration.minimum_price_tick


class ReplayConfiguration(ContractModel):
    snapshot_retention: SnapshotRetentionPolicy = SnapshotRetentionPolicy.ALL
    verify_against_direct_batch: bool = True

    rule_version: SemVer = SemVer.parse("0.1.0")
    contract_version: SemVer = SemVer.parse("0.1.0")
    schema_version: SemVer = SemVer.parse("0.1.0")
