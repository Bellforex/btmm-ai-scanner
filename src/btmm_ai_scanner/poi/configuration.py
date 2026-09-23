from decimal import Decimal

from btmm_ai_scanner.config.enums import InternalSymbol
from btmm_ai_scanner.contracts.provenance_record import EvidenceClassification
from btmm_ai_scanner.contracts.types import ContractModel, SemVer
from btmm_ai_scanner.poi.enums import PoiType

_ALL_IMPLEMENTABLE_POI_TYPES: frozenset[PoiType] = frozenset(PoiType)


class InvalidPoiConfigurationError(ValueError):
    pass


class PoiConfiguration(ContractModel):
    minimum_price_tick: Decimal

    enabled_poi_types: frozenset[PoiType] = _ALL_IMPLEMENTABLE_POI_TYPES
    supported_symbols: frozenset[InternalSymbol] = frozenset(
        {InternalSymbol.XAUUSD, InternalSymbol.EURUSD, InternalSymbol.GBPUSD}
    )

    #: ORDER BLOCK / ENGULFING displacement ratios. Shared by `order_blocks.py`
    #: and `engulfing.py`; NOT a Base rule and deliberately untouched by the
    #: Arm E calibration below.
    order_block_size_ratio_standard: Decimal = Decimal("2.0")
    order_block_size_ratio_strong: Decimal = Decimal("3.0")

    #: FROZEN P3-ERA CONSTANTS. Nothing in the Base path reads these any more --
    #: `test_base_candle_size_doctrine` asserts that. They are retained solely
    #: because the closed P3 Pine appendix carries
    #: `C_POI_SMALL_CANDLE_STANDARD = 0.50` and its parity test pins the two
    #: together. Changing them would silently break a closed phase's parity, and
    #: they are NOT the RC5 Base rule.
    small_candle_ratio_standard: Decimal = Decimal("0.50")
    small_candle_ratio_strong: Decimal = Decimal("0.3333")

    base_min_candles: int = 2
    base_max_candles: int = 6
    base_height_atr_multiplier: Decimal = Decimal("0.75")
    base_height_departure_multiplier: Decimal = Decimal("0.60")
    base_midpoint_drift_ratio: Decimal = Decimal("0.25")
    base_overlap_ratio_minimum: Decimal = Decimal("0.50")

    #: THE ONE canonical Base-candle size rule (author decision, Arm E).
    #:
    #:     max base candle Total Range <= base_candle_size_ratio_standard x
    #:                                    departure Total Range
    #:
    #: Basis: Candle Total Range, wicks included -- the basis the source
    #: material specifies ("Base = 2+ candles, short, small RANGE";
    #: `knowledge/POI_MASTER_CATALOG.md` SS1.4, which also records that those
    #: words carry "no numeric thresholds"). Body is deliberately NOT used: the
    #: source reserves body language for Pressure Wick.
    #:
    #: The value is 0.60, calibrated from the provisional 0.50. It is not a new
    #: number -- `base_height_departure_multiplier` is already 0.60 in the same
    #: approved standard, and because Base Height >= every base candle's Total
    #: Range, that gate ALREADY implied this bound. Arm E makes the implication
    #: explicit instead of enforcing a stricter, unsourced 0.50 on top of it.
    #:
    #: There is deliberately no second, separately-configured reciprocal form.
    #: `max_base <= k x departure` and `departure / max_base >= 1 / k` are the
    #: same statement, and configuring both is how 0.60 and 2.0 drift apart.
    #: Read the reciprocal from `base_departure_ratio_standard` instead.
    base_candle_size_ratio_standard: Decimal = Decimal("0.60")
    #: Strong Base. Unchanged in value from the approved standard.
    base_candle_size_ratio_strong: Decimal = Decimal("0.3333")

    @property
    def base_departure_ratio_standard(self) -> Decimal:
        """The same rule written the other way up, DERIVED not configured.

        Documentation and the Pine port both want the `departure / base >= N`
        form. Computing it here means there is no second constant to fall out of
        step with `base_candle_size_ratio_standard`.
        """
        return Decimal(1) / self.base_candle_size_ratio_standard

    @property
    def base_departure_ratio_strong(self) -> Decimal:
        return Decimal(1) / self.base_candle_size_ratio_strong

    pressure_wick_share_standard: Decimal = Decimal("0.40")
    pressure_wick_body_efficiency_standard: Decimal = Decimal("0.25")
    pressure_wick_dominance_standard: Decimal = Decimal("2.0")
    pressure_wick_close_position_standard: Decimal = Decimal("0.60")
    pressure_wick_share_strong: Decimal = Decimal("0.50")
    pressure_wick_body_efficiency_strong: Decimal = Decimal("0.30")
    pressure_wick_dominance_strong: Decimal = Decimal("3.0")
    pressure_wick_close_position_strong: Decimal = Decimal("0.70")
    pressure_wick_range_context_strong: Decimal = Decimal("1.25")

    hammer_shooting_star_wick_share_standard: Decimal = Decimal("0.60")
    hammer_shooting_star_body_efficiency_standard: Decimal = Decimal("0.30")
    hammer_shooting_star_opposite_wick_standard: Decimal = Decimal("0.10")
    hammer_shooting_star_wick_share_strong: Decimal = Decimal("0.70")
    hammer_shooting_star_body_efficiency_strong: Decimal = Decimal("0.20")
    hammer_shooting_star_opposite_wick_strong: Decimal = Decimal("0.05")

    doji_body_efficiency_standard: Decimal = Decimal("0.10")
    doji_body_efficiency_strong: Decimal = Decimal("0.05")

    # RC3 qualification (author decision 2026-09-17): an FVG is mapped only when
    # gap width >= this x ATR-14 of its departure candle.
    fvg_min_gap_atr_ratio: Decimal = Decimal("0.35")

    #: RC4 profile only (author decision 2026-09-19). Adds to the RC3 gap rule:
    #: the departure candle must be a real expansion -- the frozen displacement
    #: primitive must class it at least FAST (range >= 1.50 x the median range
    #: of the previous 20 bars) AND its range must exceed the immediately
    #: preceding candle's range -- and an FVG whose imbalance was already fully
    #: consumed before its (possibly delayed) availability is not admitted.
    #: False keeps the frozen RC3 contract exactly.
    rc4_fvg_quality: bool = False

    #: RC5 profile only (author decision 2026-09-20). A reversal-family
    #: candidate is promoted only where the market actually made a structural
    #: decision: its formation must touch a leg origin, a confirmed swing
    #: extreme on its own side, a pullback terminal, a range boundary,
    #: tracked liquidity or a trendline. Geometrically perfect candles in
    #: mid-leg texture stay raw patterns. Answers "is this a POI at all?";
    #: same-origin arbitration is a separate filter (``poi/authority.py``).
    #: False keeps the frozen RC3/RC4 contract exactly.
    rc5_structural_origin: bool = False

    reversal_candidate_size_ratio_standard: Decimal = Decimal("2.0")
    reversal_candidate_size_ratio_strong: Decimal = Decimal("3.0")
    reversal_body_efficiency_standard: Decimal = Decimal("0.60")
    reversal_body_efficiency_strong: Decimal = Decimal("0.70")
    reversal_close_position_standard: Decimal = Decimal("0.70")
    reversal_close_position_strong: Decimal = Decimal("0.80")

    zone_contact_tolerance_atr_multiplier: Decimal = Decimal("0.05")
    zone_contact_tolerance_zone_height_multiplier: Decimal = Decimal("0.10")
    zone_overshoot_tolerance_atr_multiplier: Decimal = Decimal("0.10")
    zone_overshoot_tolerance_zone_height_multiplier: Decimal = Decimal("0.25")

    reclaim_window_bars: int = 3
    displacement_window_bars: int = 3

    rule_version: SemVer = SemVer.parse("1.0.0")
    contract_version: SemVer = SemVer.parse("0.1.0")
    schema_version: SemVer = SemVer.parse("0.1.0")
    evidence_classification: EvidenceClassification = (
        EvidenceClassification.ENGINEERING_PROVISIONAL
    )


_POSITIVE_DECIMAL_FIELDS: tuple[str, ...] = (
    "minimum_price_tick",
    "order_block_size_ratio_standard",
    "order_block_size_ratio_strong",
    "small_candle_ratio_standard",
    "small_candle_ratio_strong",
    "base_candle_size_ratio_standard",
    "base_candle_size_ratio_strong",
    "base_height_atr_multiplier",
    "base_height_departure_multiplier",
    "base_midpoint_drift_ratio",
    "base_overlap_ratio_minimum",
    "pressure_wick_share_standard",
    "pressure_wick_body_efficiency_standard",
    "pressure_wick_dominance_standard",
    "pressure_wick_close_position_standard",
    "pressure_wick_share_strong",
    "pressure_wick_body_efficiency_strong",
    "pressure_wick_dominance_strong",
    "pressure_wick_close_position_strong",
    "pressure_wick_range_context_strong",
    "hammer_shooting_star_wick_share_standard",
    "hammer_shooting_star_body_efficiency_standard",
    "hammer_shooting_star_opposite_wick_standard",
    "hammer_shooting_star_wick_share_strong",
    "hammer_shooting_star_body_efficiency_strong",
    "hammer_shooting_star_opposite_wick_strong",
    "doji_body_efficiency_standard",
    "doji_body_efficiency_strong",
    "fvg_min_gap_atr_ratio",
    "reversal_candidate_size_ratio_standard",
    "reversal_candidate_size_ratio_strong",
    "reversal_body_efficiency_standard",
    "reversal_body_efficiency_strong",
    "reversal_close_position_standard",
    "reversal_close_position_strong",
    "zone_contact_tolerance_atr_multiplier",
    "zone_contact_tolerance_zone_height_multiplier",
    "zone_overshoot_tolerance_atr_multiplier",
    "zone_overshoot_tolerance_zone_height_multiplier",
)

_POSITIVE_INT_FIELDS: tuple[str, ...] = (
    "base_min_candles",
    "base_max_candles",
    "reclaim_window_bars",
    "displacement_window_bars",
)


def validate_configuration(configuration: PoiConfiguration) -> None:
    """Explicit, reachable validation raising the exact approved typed error.

    Pydantic field validators would wrap a raised error in ValidationError,
    losing the InvalidPoiConfigurationError identity the register requires
    callers to be able to catch directly.
    """
    for field_name in _POSITIVE_DECIMAL_FIELDS:
        value: Decimal = getattr(configuration, field_name)
        if value <= 0:
            raise InvalidPoiConfigurationError(
                f"{field_name} must be strictly greater than zero, got {value!r}."
            )

    for int_field_name in _POSITIVE_INT_FIELDS:
        int_value: int = getattr(configuration, int_field_name)
        if int_value <= 0:
            raise InvalidPoiConfigurationError(
                f"{int_field_name} must be strictly greater than zero, got"
                f" {int_value!r}."
            )

    if configuration.base_max_candles < configuration.base_min_candles:
        raise InvalidPoiConfigurationError(
            "base_max_candles must be greater than or equal to base_min_candles."
        )

    if not configuration.enabled_poi_types.issubset(_ALL_IMPLEMENTABLE_POI_TYPES):
        raise InvalidPoiConfigurationError(
            "enabled_poi_types may only contain approved implementable PoiType members."
        )

    if len(configuration.supported_symbols) == 0:
        raise InvalidPoiConfigurationError(
            "supported_symbols must contain at least one InternalSymbol."
        )
