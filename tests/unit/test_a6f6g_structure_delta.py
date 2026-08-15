"""A6-F6G: structure event identity-reuse operation gates.

On the full re-diff path (a candle that changes the confirmed-swing set), the
structure replay must NOT re-derive the identity string of every historical
event: candles and unchanged confirmed swings are the same objects across
candles, so their identity is reused by object identity. Byte-identical
structure output stays covered by the every-prefix batch/incremental
equivalence cascade; this file asserts the operation-count reduction (which the
equivalence tests do not measure): the vast majority of events on a full-path
candle are reused, not re-derived.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

from btmm_ai_scanner.config.enums import InternalSymbol, Timeframe
from btmm_ai_scanner.contracts.normalized_candle import NormalizedCandle
from btmm_ai_scanner.contracts.raw_candle import CandleCompleteness, CandleVolumeKind
from btmm_ai_scanner.contracts.types import SemVer
from btmm_ai_scanner.domain.analyzer import (
    _advance_measurement_replay_state,
    _create_initial_measurement_replay_state,
)
from btmm_ai_scanner.domain.configuration import MarketMeasurementConfiguration
from btmm_ai_scanner.domain.enums import DerivedOutputType
from btmm_ai_scanner.structure.analyzer import (
    _advance_structure_replay_state,
    _create_initial_structure_replay_state,
)
from btmm_ai_scanner.structure.configuration import StructureConfiguration

_MCONFIG = MarketMeasurementConfiguration(minimum_price_tick=Decimal("0.01"))
_SCONFIG = StructureConfiguration()
_BASE = datetime(2026, 1, 1, tzinfo=UTC)
_FP = "a" * 64
_RAW = UUID("0193f350-1234-7abc-8def-abcdefabcdaa")
_PROV = UUID("0193f350-1234-7abc-8def-abcdefabcdff")


class _Ident:
    def identify(
        self, *, output_type: DerivedOutputType, semantic_key: tuple[str, ...]
    ) -> UUID:
        import hashlib

        d = hashlib.sha256(
            (output_type.value + "|" + "|".join(semantic_key)).encode()
        ).digest()[:16]
        v = int.from_bytes(d, "big")
        v &= ~(0xF << 76)
        v |= 7 << 76
        v &= ~(0x3 << 62)
        v |= 0x2 << 62
        return UUID(int=v)


def _candle(i: int, o: float, h: float, low: float, c: float) -> NormalizedCandle:
    et = _BASE + timedelta(minutes=15 * i)
    av = et + timedelta(minutes=15)
    return NormalizedCandle.model_validate(
        {
            "record_id": UUID(f"0193f350-1234-7abc-8def-{i:012x}"),
            "content_fingerprint": _FP,
            "raw_candle_id": _RAW,
            "provider": "FXCM",
            "source_reference": "r",
            "source_symbol": "XAUUSD",
            "source_timeframe": Timeframe.M15.value,
            "symbol": InternalSymbol.XAUUSD,
            "timeframe": Timeframe.M15,
            "event_time_utc": et,
            "availability_time_utc": av,
            "processing_time_utc": av,
            "original_event_time": et,
            "original_availability_time": av,
            "original_timezone": "UTC",
            "open": Decimal(f"{o:.2f}"),
            "high": Decimal(f"{h:.2f}"),
            "low": Decimal(f"{low:.2f}"),
            "close": Decimal(f"{c:.2f}"),
            "volume": Decimal("10"),
            "volume_kind": CandleVolumeKind.TICK,
            "completeness": CandleCompleteness.CONFIRMED_COMPLETE,
            "rule_version": SemVer.parse("0.1.0"),
            "contract_version": SemVer.parse("0.1.0"),
            "schema_version": SemVer.parse("0.1.0"),
            "provenance_id": _PROV,
        }
    )


def _zigzag(n: int, amp: float, period: int) -> list[NormalizedCandle]:
    out = []
    price = 100.0
    for i in range(n):
        direction = 1 if (i // period) % 2 == 0 else -1
        o = price
        c = o + direction * amp
        out.append(_candle(i, o, max(o, c) + amp * 0.2, min(o, c) - amp * 0.2, c))
        price = c
    return out


def test_full_path_reuses_the_bulk_of_event_identities() -> None:
    candles = _zigzag(200, 4.0, 5)
    measurement = _create_initial_measurement_replay_state(_Ident(), _MCONFIG)
    structure = _create_initial_structure_replay_state(_Ident(), _SCONFIG)
    total_reused = 0
    total_derived = 0
    full_paths = 0
    for candle in candles:
        measurement = _advance_measurement_replay_state(measurement, candle, _MCONFIG)
        structure = _advance_structure_replay_state(
            structure, candle, measurement.confirmed_swings_so_far, _SCONFIG
        )
        if structure.full_sort_path:
            full_paths += 1
            total_reused += structure.identity_reused
            total_derived += structure.identity_derived
    # There must have been genuine full-path (swing-changing) candles, and across
    # them the reused identities must dominate -- candles (the bulk of every
    # event stream) are always reused, never re-derived.
    assert full_paths > 5, full_paths
    assert total_reused > total_derived, (total_reused, total_derived)
    # Reuse fraction is high: only new/changed swings + rebuilt relationships are
    # re-derived, everything else (all candle events + unchanged swings) is reused.
    assert total_reused > 3 * total_derived, (total_reused, total_derived)


def test_fast_path_reuses_all_but_the_new_candle() -> None:
    # A candle that does not change the confirmed-swing set reuses every prior
    # identity and derives exactly one (the new candle event).
    candles = _zigzag(60, 4.0, 5)
    measurement = _create_initial_measurement_replay_state(_Ident(), _MCONFIG)
    structure = _create_initial_structure_replay_state(_Ident(), _SCONFIG)
    saw_fast = False
    for candle in candles:
        measurement = _advance_measurement_replay_state(measurement, candle, _MCONFIG)
        structure = _advance_structure_replay_state(
            structure, candle, measurement.confirmed_swings_so_far, _SCONFIG
        )
        if not structure.full_sort_path and len(structure.event_identities) > 3:
            saw_fast = True
            assert structure.identity_derived == 1, structure.identity_derived
            assert structure.identity_reused == len(structure.event_identities) - 1
    assert saw_fast
