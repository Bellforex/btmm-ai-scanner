import hashlib
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

from btmm_ai_scanner.config.enums import InternalSymbol, Timeframe
from btmm_ai_scanner.contracts.provenance_record import EvidenceClassification
from btmm_ai_scanner.contracts.types import SemVer
from btmm_ai_scanner.domain.configuration import MarketMeasurementConfiguration
from btmm_ai_scanner.domain.enums import DerivedOutputType, EqualLevelType, SwingType
from btmm_ai_scanner.domain.equal_levels import detect_equal_level_clusters
from btmm_ai_scanner.domain.swings import ConfirmedSwing

_PROVENANCE_ID = UUID("0193f300-1234-7abc-8def-abcdefabcdff")
_BASE_TIME = datetime(2026, 1, 1, tzinfo=UTC)
_CONFIG = MarketMeasurementConfiguration(minimum_price_tick=Decimal("0.01"))


class _HashIdentityProvider:
    def identify(
        self, *, output_type: DerivedOutputType, semantic_key: tuple[str, ...]
    ) -> UUID:
        payload = output_type.value + "|" + "|".join(semantic_key)
        digest = hashlib.sha256(payload.encode("utf-8")).digest()[:16]
        as_int = int.from_bytes(digest, "big")
        as_int &= ~(0xF << 76)
        as_int |= 7 << 76
        as_int &= ~(0x3 << 62)
        as_int |= 0x2 << 62
        return UUID(int=as_int)


def _record_id(index: int) -> UUID:
    digest = hashlib.sha256(f"swing-{index}".encode()).digest()[:16]
    as_int = int.from_bytes(digest, "big")
    as_int &= ~(0xF << 76)
    as_int |= 7 << 76
    as_int &= ~(0x3 << 62)
    as_int |= 0x2 << 62
    return UUID(int=as_int)


def _swing(
    index: int,
    swing_type: SwingType,
    price: str,
    minutes_offset: int,
    reference_atr: str = "1.0",
) -> ConfirmedSwing:
    pivot_time = _BASE_TIME + timedelta(minutes=minutes_offset)
    confirmation_time = pivot_time + timedelta(minutes=5)
    return ConfirmedSwing(
        record_id=_record_id(index),
        content_fingerprint="a" * 64,
        symbol=InternalSymbol.XAUUSD,
        timeframe=Timeframe.M1,
        swing_type=swing_type,
        pivot_price=Decimal(price),
        pivot_bar_index=minutes_offset,
        pivot_candle_record_ids=(_record_id(index),),
        pivot_start_time_utc=pivot_time,
        pivot_end_time_utc=pivot_time,
        local_confirmation_time_utc=pivot_time + timedelta(minutes=2),
        meaningful_confirmation_time_utc=confirmation_time,
        confirmation_candle_id=_record_id(index + 1000),
        pivot_reference_atr=Decimal(reference_atr),
        pivot_tie_tolerance=Decimal("0.02"),
        reversal_threshold=Decimal("0.5"),
        reversal_excursion=Decimal("1"),
        availability_time_utc=confirmation_time,
        rule_version=SemVer.parse("1.0.0"),
        contract_version=SemVer.parse("0.1.0"),
        schema_version=SemVer.parse("0.1.0"),
        evidence_classification=EvidenceClassification.ENGINEERING_PROVISIONAL,
        provenance_id=_PROVENANCE_ID,
    )


def test_equal_level_cluster_confirms_equal_highs_within_tolerance() -> None:
    swings = (
        _swing(1, SwingType.SWING_HIGH, "100.00", 0),
        _swing(2, SwingType.SWING_LOW, "95.00", 10),
        _swing(3, SwingType.SWING_HIGH, "100.02", 20),
    )
    clusters = detect_equal_level_clusters(swings, _CONFIG)

    assert len(clusters) == 1
    assert clusters[0].cluster_type == EqualLevelType.EQUAL_HIGH
    assert len(clusters[0].component_swing_record_ids) == 2


def test_equal_level_cluster_confirms_equal_lows_within_tolerance() -> None:
    swings = (
        _swing(1, SwingType.SWING_LOW, "100.00", 0),
        _swing(2, SwingType.SWING_HIGH, "105.00", 10),
        _swing(3, SwingType.SWING_LOW, "100.02", 20),
    )
    clusters = detect_equal_level_clusters(swings, _CONFIG)

    assert len(clusters) == 1
    assert clusters[0].cluster_type == EqualLevelType.EQUAL_LOW


def test_equal_level_cluster_rejects_spread_beyond_tolerance() -> None:
    swings = (
        _swing(1, SwingType.SWING_HIGH, "100.00", 0),
        _swing(2, SwingType.SWING_LOW, "95.00", 10),
        _swing(3, SwingType.SWING_HIGH, "110.00", 20),
    )
    clusters = detect_equal_level_clusters(swings, _CONFIG)

    assert clusters == ()


def test_equal_level_cluster_resolves_transitive_chain_without_forming_an_invalid_cluster() -> (
    None
):
    # A within tolerance of B, B within tolerance of C, A not within tolerance of C.
    swings = (
        _swing(1, SwingType.SWING_HIGH, "100.00", 0),  # A
        _swing(2, SwingType.SWING_LOW, "90.00", 10),
        _swing(3, SwingType.SWING_HIGH, "100.05", 20),  # B
        _swing(4, SwingType.SWING_LOW, "80.00", 30),
        _swing(5, SwingType.SWING_HIGH, "100.13", 40),  # C
    )
    clusters = detect_equal_level_clusters(swings, _CONFIG)

    assert len(clusters) == 1
    only_cluster = clusters[0]
    assert len(only_cluster.component_swing_record_ids) == 2
    assert _record_id(1) in only_cluster.component_swing_record_ids
    assert _record_id(3) in only_cluster.component_swing_record_ids
    assert _record_id(5) not in only_cluster.component_swing_record_ids


def test_equal_level_cluster_prevents_swing_reuse_across_clusters() -> None:
    swings = (
        _swing(1, SwingType.SWING_HIGH, "100.00", 0),
        _swing(2, SwingType.SWING_LOW, "90.00", 10),
        _swing(3, SwingType.SWING_HIGH, "100.03", 20),
        _swing(4, SwingType.SWING_LOW, "90.00", 30),
        _swing(5, SwingType.SWING_HIGH, "100.06", 40),
        _swing(6, SwingType.SWING_LOW, "90.00", 50),
        _swing(7, SwingType.SWING_HIGH, "100.09", 60),
    )
    clusters = detect_equal_level_clusters(swings, _CONFIG)

    seen: set[UUID] = set()
    for cluster in clusters:
        for swing_id in cluster.component_swing_record_ids:
            assert swing_id not in seen
            seen.add(swing_id)


def test_equal_level_cluster_requires_distinct_confirmed_meaningful_swings() -> None:
    swings = (_swing(1, SwingType.SWING_HIGH, "100.00", 0),)
    clusters = detect_equal_level_clusters(swings, _CONFIG)
    assert clusters == ()


def test_equal_level_cluster_growth_retains_record_id_and_changes_content_fingerprint() -> (
    None
):
    from btmm_ai_scanner.domain.analyzer import _finalize, _IdentityResolver

    two_members = (
        _swing(1, SwingType.SWING_HIGH, "100.00", 0),
        _swing(2, SwingType.SWING_LOW, "90.00", 10),
        _swing(3, SwingType.SWING_HIGH, "100.02", 20),
    )
    three_members = (
        *two_members,
        _swing(4, SwingType.SWING_LOW, "80.00", 30),
        _swing(5, SwingType.SWING_HIGH, "100.03", 40),
    )

    provider = _HashIdentityProvider()
    small_candidates = list(detect_equal_level_clusters(two_members, _CONFIG))
    large_candidates = list(detect_equal_level_clusters(three_members, _CONFIG))

    from btmm_ai_scanner.domain.equal_levels import EqualLevelCluster

    small_result = _finalize(
        small_candidates,
        DerivedOutputType.EQUAL_LEVEL_CLUSTER,
        EqualLevelCluster,
        lambda c: (
            c.symbol.value,
            c.timeframe.value,
            c.cluster_type.value,
            str(c.first_seed_swing_id),
            str(c.second_seed_swing_id),
            str(_CONFIG.rule_version),
        ),
        lambda c: {"availability_time_utc": c.confirmation_time_utc},
        frozenset({"first_seed_swing_id", "second_seed_swing_id"}),
        _CONFIG,
        _IdentityResolver(provider),
    )
    large_result = _finalize(
        large_candidates,
        DerivedOutputType.EQUAL_LEVEL_CLUSTER,
        EqualLevelCluster,
        lambda c: (
            c.symbol.value,
            c.timeframe.value,
            c.cluster_type.value,
            str(c.first_seed_swing_id),
            str(c.second_seed_swing_id),
            str(_CONFIG.rule_version),
        ),
        lambda c: {"availability_time_utc": c.confirmation_time_utc},
        frozenset({"first_seed_swing_id", "second_seed_swing_id"}),
        _CONFIG,
        _IdentityResolver(provider),
    )

    assert len(small_result) == 1
    assert len(large_result) == 1
    assert small_result[0].record_id == large_result[0].record_id
    assert small_result[0].content_fingerprint != large_result[0].content_fingerprint


def test_equal_level_cluster_liquidity_side_is_a_computed_property_not_a_separate_object() -> (
    None
):
    high_swings = (
        _swing(1, SwingType.SWING_HIGH, "100.00", 0),
        _swing(2, SwingType.SWING_LOW, "90.00", 10),
        _swing(3, SwingType.SWING_HIGH, "100.02", 20),
    )
    low_swings = (
        _swing(1, SwingType.SWING_LOW, "100.00", 0),
        _swing(2, SwingType.SWING_HIGH, "110.00", 10),
        _swing(3, SwingType.SWING_LOW, "100.02", 20),
    )

    high_clusters = detect_equal_level_clusters(high_swings, _CONFIG)
    low_clusters = detect_equal_level_clusters(low_swings, _CONFIG)

    # Candidates carry no `liquidity_side`/`reference_price` field — those are
    # computed properties added only on the final EqualLevelCluster contract.
    assert not hasattr(high_clusters[0], "liquidity_side")
    assert not hasattr(low_clusters[0], "liquidity_side")


def test_equal_level_cluster_representative_price_is_the_zone_midpoint() -> None:
    swings = (
        _swing(1, SwingType.SWING_HIGH, "100.00", 0),
        _swing(2, SwingType.SWING_LOW, "90.00", 10),
        _swing(3, SwingType.SWING_HIGH, "100.04", 20),
    )
    clusters = detect_equal_level_clusters(swings, _CONFIG)

    assert len(clusters) == 1
    cluster = clusters[0]
    assert cluster.representative_price == (
        cluster.zone_bottom + cluster.zone_top
    ) / Decimal(2)
