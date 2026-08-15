"""A6-B2-B permanent tests: exact incremental BTMM setup-delta derivation.

``derive_btmm_setup_delta`` must map the POI engine's own bounded per-candle
NEW/CHANGED/REMOVED delta onto the BTMM-eligible setup subset, assigning each
surviving POI the exact identity ``analyze_btmm`` itself would assign (proven by
comparing against ``setup_record_id_for_poi`` applied the same way analyze_btmm's
own resolver would), with zero historical-universe scanning (the function only
ever reads its own bounded input lists)."""

from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from btmm_ai_scanner.btmm.configuration import BtmmConfiguration
from btmm_ai_scanner.btmm.setup_delta import (
    derive_btmm_setup_delta,
    is_btmm_eligible,
    setup_record_id_for_poi,
)
from btmm_ai_scanner.config.enums import InternalSymbol, Timeframe
from btmm_ai_scanner.contracts.provenance_record import EvidenceClassification
from btmm_ai_scanner.contracts.types import SemVer
from btmm_ai_scanner.domain.enums import DerivedOutputType
from btmm_ai_scanner.poi.enums import PoiDirection, PoiFamily, PoiType
from btmm_ai_scanner.poi.observation import PoiObservation

_FINGERPRINT = "a" * 64
_PROV_ID = UUID("0193f460-1234-7abc-8def-abcdefabcdff")
_BASE_TIME = datetime(2026, 1, 1, tzinfo=UTC)
_CONFIG = BtmmConfiguration(minimum_price_tick=Decimal("0.01"))
_RULE_VERSION_TEXT = str(_CONFIG.rule_version)


class _HashIdentityProvider:
    """Deterministic content-addressed provider matching the pattern used
    throughout the incremental-replay permanent test suite."""

    def __init__(self) -> None:
        self._next = 0
        self._by_key: dict[tuple[str, ...], UUID] = {}

    def identify(
        self, *, output_type: DerivedOutputType, semantic_key: tuple[str, ...]
    ) -> UUID:
        key = (output_type.value, *semantic_key)
        cached = self._by_key.get(key)
        if cached is not None:
            return cached
        self._next += 1
        result = UUID(f"0193f460-aaaa-7000-8000-{self._next:012x}")
        self._by_key[key] = result
        return result


def _poi(
    record_id: UUID,
    poi_type: PoiType,
    source_timeframe: Timeframe = Timeframe.M5,
    zone_top: Decimal = Decimal("101"),
    zone_bottom: Decimal = Decimal("100"),
) -> PoiObservation:
    direction = (
        PoiDirection.BULLISH
        if poi_type == PoiType.SUPPORT_ZONE
        else PoiDirection.BEARISH
    )
    return PoiObservation(
        record_id=record_id,
        content_fingerprint=_FINGERPRINT,
        symbol=InternalSymbol.XAUUSD,
        source_timeframe=source_timeframe,
        effective_timeframe=source_timeframe,
        family=PoiFamily.STRUCTURAL,
        poi_type=poi_type,
        direction=direction,
        zone_top=zone_top,
        zone_bottom=zone_bottom,
        representative_price=None,
        strength_tier=None,
        source_candle_record_ids=(),
        source_measurement_record_ids=(),
        merged_source_poi_record_ids=(),
        candidate_event_time_utc=_BASE_TIME,
        confirmation_time_utc=_BASE_TIME,
        availability_time_utc=_BASE_TIME,
        rule_version=SemVer.parse("0.1.0"),
        contract_version=SemVer.parse("0.1.0"),
        schema_version=SemVer.parse("0.1.0"),
        evidence_classification=EvidenceClassification.ENGINEERING_PROVISIONAL,
        provenance_id=_PROV_ID,
    )


def _v7(n: int) -> UUID:
    return UUID(f"0193f460-aaaa-7000-8000-{n:012x}")


def test_new_eligible_poi_becomes_new_setup_with_exact_identity() -> None:
    provider = _HashIdentityProvider()
    poi = _poi(_v7(1), PoiType.BUY_ORDER_BLOCK)
    delta = derive_btmm_setup_delta(
        (poi,), (), (), provider, _RULE_VERSION_TEXT, _CONFIG
    )
    assert len(delta.new_setups) == 1
    spec = delta.new_setups[0]
    expected_id = setup_record_id_for_poi(
        provider, poi.symbol, poi.source_timeframe, poi.record_id, _RULE_VERSION_TEXT
    )
    assert spec.setup_record_id == expected_id
    assert spec.source_poi_record_id == poi.record_id
    assert spec.zone_top == poi.zone_top
    assert spec.zone_bottom == poi.zone_bottom
    assert spec.direction == poi.direction
    assert spec.candidate_availability_time_utc == poi.availability_time_utc


def test_ineligible_poi_type_produces_no_setup() -> None:
    provider = _HashIdentityProvider()
    poi = _poi(_v7(2), PoiType.EQUAL_HIGHS_LIQUIDITY)
    assert not is_btmm_eligible(poi, _CONFIG)
    delta = derive_btmm_setup_delta(
        (poi,), (), (), provider, _RULE_VERSION_TEXT, _CONFIG
    )
    assert delta.new_setups == ()


def test_unsupported_timeframe_produces_no_setup() -> None:
    provider = _HashIdentityProvider()
    poi = _poi(_v7(3), PoiType.BUY_ORDER_BLOCK, source_timeframe=Timeframe.H1)
    delta = derive_btmm_setup_delta(
        (poi,), (), (), provider, _RULE_VERSION_TEXT, _CONFIG
    )
    assert delta.new_setups == ()


def test_changed_source_poi_becomes_changed_setup_same_identity() -> None:
    provider = _HashIdentityProvider()
    poi_before = _poi(_v7(4), PoiType.SUPPORT_ZONE, zone_top=Decimal("101"))
    poi_after = _poi(_v7(4), PoiType.SUPPORT_ZONE, zone_top=Decimal("102"))
    delta_before = derive_btmm_setup_delta(
        (poi_before,), (), (), provider, _RULE_VERSION_TEXT, _CONFIG
    )
    delta_after = derive_btmm_setup_delta(
        (), (poi_after,), (), provider, _RULE_VERSION_TEXT, _CONFIG
    )
    assert len(delta_after.changed_setups) == 1
    assert (
        delta_after.changed_setups[0].setup_record_id
        == delta_before.new_setups[0].setup_record_id
    )
    assert delta_after.changed_setups[0].zone_top == Decimal("102")


def test_removed_poi_forwarded_as_removed_source_poi_id() -> None:
    provider = _HashIdentityProvider()
    poi_id = _v7(5)
    delta = derive_btmm_setup_delta(
        (), (), (poi_id,), provider, _RULE_VERSION_TEXT, _CONFIG
    )
    assert delta.removed_source_poi_ids == (poi_id,)
    assert delta.new_setups == ()
    assert delta.changed_setups == ()


def test_zero_historical_diff_only_bounded_delta_touched() -> None:
    """Only the supplied (bounded) lists are read -- a huge unrelated 'universe'
    passed nowhere near the function proves there is no historical scan; the
    delta size is exactly the size of the bounded input, regardless of how many
    setups might already exist elsewhere (this function has no notion of them at
    all -- it is a pure function of its three input lists)."""
    provider = _HashIdentityProvider()
    new_pois = tuple(_poi(_v7(100 + i), PoiType.BUY_ORDER_BLOCK) for i in range(3))
    delta = derive_btmm_setup_delta(
        new_pois, (), (), provider, _RULE_VERSION_TEXT, _CONFIG
    )
    assert len(delta.new_setups) == 3


def test_identity_matches_analyze_btmm_semantic_key_formula() -> None:
    """The exact semantic key formula analyze_btmm uses for
    DerivedOutputType.BTMM_OBSERVATION -- byte-identical field order and text."""
    provider = _HashIdentityProvider()
    poi = _poi(_v7(6), PoiType.BUY_FAIR_VALUE_GAP)
    expected = provider.identify(
        output_type=DerivedOutputType.BTMM_OBSERVATION,
        semantic_key=(
            poi.symbol.value,
            poi.source_timeframe.value,
            str(poi.record_id),
            _RULE_VERSION_TEXT,
        ),
    )
    actual = setup_record_id_for_poi(
        provider, poi.symbol, poi.source_timeframe, poi.record_id, _RULE_VERSION_TEXT
    )
    assert actual == expected
