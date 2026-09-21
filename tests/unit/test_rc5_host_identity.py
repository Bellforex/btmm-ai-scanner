"""RC5 host identity: M45 is M45, never M15.

The frozen ``Timeframe`` enum has no M45 and must not gain one, so M45 replays
through an M15 CARRIER. That is fine for driving the engine and NOT fine for
recording, because a host-local key built from the carrier would put M45 and
M15 in one key space.

These tests pin the distinction using the REAL M45 and H3 captures where they
exist, and synthetic spacing otherwise.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from btmm_ai_scanner.config.enums import Timeframe
from btmm_ai_scanner.poi.rc5_host_identity import (
    Rc5HostIdentity,
    host_identity_from_candles,
    host_identity_of,
)
from tests.parity_support.ob_origin_series import rows_to_candles, trend
from tests.parity_support.v1a_csv_loader import load_v1a_csv

_M45_CSV = Path("artifacts/rc5_host_capture/rc5_ohlc_m45.csv")
_H3_CSV = Path("artifacts/rc5_host_capture/rc5_ohlc_h3.csv")


def test_an_honest_host_records_itself() -> None:
    identity = host_identity_of(Timeframe.M15)
    assert identity.label == "M15"
    assert identity.minutes == 15
    assert identity.carrier is Timeframe.M15
    assert not identity.is_carrier_only
    assert identity.key == ("M15", 15)


def test_hosts_that_share_a_carrier_do_not_share_a_key() -> None:
    """The collision this module exists to prevent."""
    m15 = host_identity_of(Timeframe.M15)
    m45 = Rc5HostIdentity(label="M45", minutes=45, carrier=Timeframe.M15)
    assert m15.carrier is m45.carrier
    assert m15.key != m45.key
    assert m45.is_carrier_only
    assert "M45" in str(m45) and "M15" in str(m45)


@pytest.mark.parametrize(
    ("minutes", "label"),
    [(5, "M5"), (15, "M15"), (30, "M30"), (45, "M45"), (60, "H1")],
)
def test_identity_is_derived_from_bar_spacing_not_from_the_label(
    minutes: int, label: str, tmp_path: Path
) -> None:
    """A caller cannot assert a host into existence -- the series' own spacing
    decides, so a mislabelled series is caught instead of recorded."""
    candles = rows_to_candles(trend(100.0, 0.5, 40), tmp_path, f"spacing{minutes}")
    candles = _respace(candles, minutes)
    identity = host_identity_from_candles(Timeframe.M15, candles)
    assert identity.label == label
    assert identity.minutes == minutes


def test_the_real_m45_capture_is_identified_as_m45() -> None:
    if not _M45_CSV.exists():
        pytest.skip("M45 capture not present")
    candles = load_v1a_csv(_M45_CSV, Timeframe.M15)
    identity = host_identity_from_candles(Timeframe.M15, candles)
    assert identity.label == "M45"
    assert identity.minutes == 45
    assert identity.carrier is Timeframe.M15
    assert identity.is_carrier_only


def test_the_real_h3_capture_needs_no_carrier_fiction() -> None:
    if not _H3_CSV.exists():
        pytest.skip("H3 capture not present")
    candles = load_v1a_csv(_H3_CSV, Timeframe.H3)
    identity = host_identity_from_candles(Timeframe.H3, candles)
    assert identity.label == "H3"
    assert identity.minutes == 180
    assert not identity.is_carrier_only


def test_an_unrecognised_spacing_is_refused_rather_than_mislabelled(
    tmp_path: Path,
) -> None:
    candles = rows_to_candles(trend(100.0, 0.5, 40), tmp_path, "odd")
    candles = _respace(candles, 7)
    with pytest.raises(ValueError, match="refusing to record"):
        host_identity_from_candles(Timeframe.M15, candles)


def _respace(candles, minutes: int):
    """Rebuild the series at a different bar spacing, keeping prices."""
    from datetime import timedelta

    out = []
    start = candles[0].event_time_utc
    for index, candle in enumerate(candles):
        moment = start + timedelta(minutes=minutes * index)
        out.append(
            candle.model_copy(
                update={
                    "event_time_utc": moment,
                    "availability_time_utc": moment + timedelta(minutes=minutes),
                }
            )
        )
    return out
