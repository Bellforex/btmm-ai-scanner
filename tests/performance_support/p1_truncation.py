"""P1-PERF-4 — full-history vs truncated-history execution equivalence.

``calc_bars_count = N`` makes TradingView execute the script on only the last
``N`` accessible bars. Every persistent Pine variable therefore starts empty at
bar ``T - N`` instead of bar ``0``. This module replays the P1 engine twice over
the same candles — once from the beginning, once from a truncation point — and
compares the nine published parity outputs bar by bar.

WHY AN ATR INJECTION EXISTS HERE
--------------------------------
The Pine engine keeps ONE incremental Wilder ATR over its whole accessible
history and stores each bar's value in ``wAtr``; the detectors then read that
array. Production Python's detectors instead recompute ``compute_atr_series``
over the exact slice they are handed. Those two agree only when the slice starts
where the ATR did.

Replaying the Pine engine faithfully therefore requires handing the detectors
the ATR that Pine would have had. ``injected_atr`` does exactly that and nothing
else: production ``src/`` is untouched, the detector bodies still run verbatim,
and :func:`assert_injection_is_transparent` proves that injecting the slice the
detector would have computed for itself reproduces production output exactly.

WHAT MAKES TRUNCATION SAFE
--------------------------
Because the window arrays are pruned to ``lookbackWindow`` candles, a protected
bar reads only (a) the last ``lookbackWindow`` candles and (b) their ATR values.
The candles are identical in both runs as soon as the truncated run starts early
enough for the window to be full. The ATR values are identical as soon as the
Wilder recurrence has forgotten its seed. So truncation has exactly one channel
into the result, and closing it closes all of them.
"""

from __future__ import annotations

import contextlib
from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from btmm_ai_scanner.contracts.normalized_candle import NormalizedCandle
from btmm_ai_scanner.domain import support_resistance as _sr_module
from btmm_ai_scanner.domain import swings as _swings_module
from btmm_ai_scanner.domain import trendlines as _tl_module
from btmm_ai_scanner.domain.configuration import MarketMeasurementConfiguration
from btmm_ai_scanner.domain.displacement import detect_displacement_observations
from btmm_ai_scanner.domain.enums import EqualLevelType, SwingType
from btmm_ai_scanner.domain.equal_levels import detect_equal_level_clusters
from btmm_ai_scanner.domain.support_resistance import detect_support_resistance_zones
from btmm_ai_scanner.domain.swings import detect_confirmed_swings
from btmm_ai_scanner.domain.trendlines import detect_trendlines
from btmm_ai_scanner.measurements.atr import compute_atr_series

# The Pine rolling-history contract. `lookbackWindow` in the indicator inputs.
LOOKBACK = 300

# Modules whose detector bodies call ``compute_atr_series`` on the slice handed
# to them. These are the only three; equal levels and displacement derive their
# tolerances from swing records and raw ranges respectively.
_ATR_CONSUMERS: tuple[Any, ...] = (_swings_module, _sr_module, _tl_module)

AtrSeries = tuple[Decimal | None, ...]


@contextlib.contextmanager
def injected_atr(values: AtrSeries) -> Iterator[None]:
    """Make the detectors read ``values`` instead of recomputing the ATR.

    The replacement asserts the length it was called with, so a slice/window
    mismatch fails loudly rather than silently measuring the wrong thing.
    """

    def _fake(candles: Sequence[NormalizedCandle], period: int = 14) -> AtrSeries:
        if len(candles) != len(values):
            raise AssertionError(
                f"injected ATR length {len(values)} does not match the "
                f"{len(candles)} candles the detector was given"
            )
        return values

    originals = [module.compute_atr_series for module in _ATR_CONSUMERS]
    try:
        for module in _ATR_CONSUMERS:
            module.compute_atr_series = _fake
        yield
    finally:
        for module, original in zip(_ATR_CONSUMERS, originals, strict=True):
            module.compute_atr_series = original


@dataclass(frozen=True)
class Published:
    """The nine machine-readable P1 parity outputs, exactly as Pine plots them."""

    swing_high_price: Decimal | None
    swing_low_price: Decimal | None
    disp_code: int | None
    disp_ratio: Decimal | None
    equal_high: Decimal | None
    equal_low: Decimal | None
    sr_top: Decimal | None
    sr_bottom: Decimal | None
    tl_norm_slope: Decimal | None

    def differences(self, other: Published) -> tuple[str, ...]:
        return tuple(
            name
            for name in (
                "swing_high_price",
                "swing_low_price",
                "disp_code",
                "disp_ratio",
                "equal_high",
                "equal_low",
                "sr_top",
                "sr_bottom",
                "tl_norm_slope",
            )
            if getattr(self, name) != getattr(other, name)
        )


def _swing_fingerprint(swings: Sequence[Any]) -> tuple[Any, ...]:
    """Order-sensitive image of the swing set.

    Pine uses a rolling integer accumulator for this; the tuple below carries the
    same information without the modular arithmetic, and only ever drives the
    same recompute gate.
    """
    return tuple(
        (swing.swing_type, swing.meaningful_confirmation_time_utc) for swing in swings
    )


def replay(
    candles: Sequence[NormalizedCandle],
    *,
    start: int,
    configuration: MarketMeasurementConfiguration,
    swings_fn: Any,
    first_protected: int,
    lookback: int = LOOKBACK,
) -> dict[int, Published]:
    """Replay the Pine engine over ``candles[start:]``.

    Returns the published outputs keyed by ABSOLUTE candle index, for every bar
    at or after ``first_protected``. ``swings_fn`` builds confirmed-swing
    records from a window using production detection plus Pine's semantic
    identity (the pivot-end anchor); injecting it keeps exactly one such builder
    in the tree. The state machine below mirrors the Pine
    main block: sticky publication variables stay sticky, the swing-change gate
    still guards equal levels and trendlines, and S/R is recomputed every bar.
    """
    accessible = tuple(candles[start:])
    atr_accessible = compute_atr_series(accessible, configuration.atr_period)

    swing_high_price: Decimal | None = None
    swing_low_price: Decimal | None = None
    disp_code: int | None = None
    disp_ratio: Decimal | None = None
    equal_high: Decimal | None = None
    equal_low: Decimal | None = None
    tl_norm_slope: Decimal | None = None
    last_fingerprint: tuple[Any, ...] | None = None

    out: dict[int, Published] = {}

    for end in range(1, len(accessible) + 1):
        absolute = start + end - 1
        window_first = max(0, end - lookback)
        window = accessible[window_first:end]
        window_atr = atr_accessible[window_first:end]

        with injected_atr(window_atr):
            swings = swings_fn(window, configuration)

            # DISPLACEMENT — recomputed and republished every confirmed bar.
            # Only the CURRENT bar's observation is ever published, and the
            # detector's loop reads just the preceding ``range_context_window``
            # candles, so handing it that tail computes the identical record for
            # a fraction of the work. assert_displacement_tail_is_equivalent
            # proves the two forms agree.
            tail = window[-(configuration.range_context_window + 1) :]
            observations = detect_displacement_observations(tail, configuration)
            if observations:
                latest = observations[-1]
                if latest.event_time_utc == window[-1].event_time_utc:
                    magnitude = {
                        "NORMAL": 0,
                        "FAST": 1,
                        "VERY_FAST": 2,
                    }[latest.classification.value.upper()]
                    sign = 1 if latest.direction.value.upper() == "BULLISH" else -1
                    disp_code = sign * magnitude
                    disp_ratio = latest.range_speed_ratio

            # SWING SCALARS — sticky: an empty direction keeps the prior value.
            newest_high = next(
                (s for s in reversed(swings) if s.swing_type == SwingType.SWING_HIGH),
                None,
            )
            newest_low = next(
                (s for s in reversed(swings) if s.swing_type == SwingType.SWING_LOW),
                None,
            )
            if newest_high is not None:
                swing_high_price = newest_high.pivot_price
            if newest_low is not None:
                swing_low_price = newest_low.pivot_price

            # SUPPORT / RESISTANCE — every bar, never behind the swing gate, and
            # republished as na when the set is empty.
            zones = detect_support_resistance_zones(window, swings, configuration)
            ordered = sorted(zones, key=lambda z: z.confirmation_time_utc)
            sr_top = ordered[-1].zone_top if ordered else None
            sr_bottom = ordered[-1].zone_bottom if ordered else None

            # EQUAL LEVELS + TRENDLINES — behind the swing-change gate, sticky.
            fingerprint = _swing_fingerprint(swings)
            if fingerprint != last_fingerprint:
                last_fingerprint = fingerprint
                clusters = detect_equal_level_clusters(swings, configuration)
                equal_high = None
                equal_low = None
                for cluster in clusters:
                    if cluster.cluster_type == EqualLevelType.EQUAL_HIGH:
                        equal_high = cluster.representative_price
                    else:
                        equal_low = cluster.representative_price
                lines = detect_trendlines(window, swings, configuration)
                tl_norm_slope = lines[-1].normalized_slope if lines else None

        if absolute >= first_protected:
            out[absolute] = Published(
                swing_high_price=swing_high_price,
                swing_low_price=swing_low_price,
                disp_code=disp_code,
                disp_ratio=disp_ratio,
                equal_high=equal_high,
                equal_low=equal_low,
                sr_top=sr_top,
                sr_bottom=sr_bottom,
                tl_norm_slope=tl_norm_slope,
            )

    return out


def assert_injection_is_transparent(
    candles: Sequence[NormalizedCandle],
    configuration: MarketMeasurementConfiguration,
) -> None:
    """Prove the injection changes nothing when it supplies the natural ATR.

    This is what keeps production Python the oracle: if handing a detector the
    series it would have computed for itself ever produced a different answer,
    every truncation measurement taken through this module would be worthless.
    """
    window = tuple(candles)
    natural = compute_atr_series(window, configuration.atr_period)

    unpatched_swings = detect_confirmed_swings(window, configuration)
    with injected_atr(natural):
        patched_swings = detect_confirmed_swings(window, configuration)
    if unpatched_swings != patched_swings:
        raise AssertionError("ATR injection altered detect_confirmed_swings")

    unpatched_tl = detect_trendlines(window, (), configuration)
    with injected_atr(natural):
        patched_tl = detect_trendlines(window, (), configuration)
    if unpatched_tl != patched_tl:
        raise AssertionError("ATR injection altered detect_trendlines")

    unpatched_sr = detect_support_resistance_zones(window, (), configuration)
    with injected_atr(natural):
        patched_sr = detect_support_resistance_zones(window, (), configuration)
    if unpatched_sr != patched_sr:
        raise AssertionError("ATR injection altered detect_support_resistance_zones")


def assert_displacement_tail_is_equivalent(
    candles: Sequence[NormalizedCandle],
    configuration: MarketMeasurementConfiguration,
) -> None:
    """Prove the tail-sliced displacement call matches the whole-window call.

    ``replay`` publishes only the current bar's displacement, so it hands the
    detector the shortest slice that can produce it. If that ever diverged from
    the full-window call, every displacement column in the campaign would be
    measuring a different quantity than Pine publishes.
    """
    span = configuration.range_context_window
    for end in range(span + 1, len(candles) + 1):
        window = tuple(candles[max(0, end - LOOKBACK) : end])
        full = detect_displacement_observations(window, configuration)
        tail = detect_displacement_observations(window[-(span + 1) :], configuration)
        if not full:
            if tail:
                raise AssertionError(f"tail produced an observation at {end}")
            continue
        if not tail or full[-1] != tail[-1]:
            raise AssertionError(f"displacement tail slice diverged at bar {end}")


def atr_convergence_bars(
    candles: Sequence[NormalizedCandle],
    start: int,
    period: int = 14,
) -> int | None:
    """Bars after ``start`` before the truncated ATR equals the full-history ATR.

    ``None`` means it never converged inside the available tail, which makes any
    horizon based on this dataset unsafe.
    """
    full = compute_atr_series(tuple(candles), period)
    truncated = compute_atr_series(tuple(candles[start:]), period)
    for offset in range(len(truncated) - 1, -1, -1):
        if truncated[offset] != full[start + offset]:
            return offset + 1 if offset + 1 < len(truncated) else None
    return 0
