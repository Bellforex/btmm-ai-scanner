"""Every number spoken on stage must match the captured journal.

Written during the demo rehearsal, which caught a claim that was simply false:
the walkthrough said predicted risk and realized loss were both 92.30. They are
91.85 and 92.30. The 0.45 difference is stop slippage — a better story than the
one being told, and one that survives being checked by someone in the audience.

The demo script is not prose here. It is an assertion about a captured
artifact, so it cannot drift away from the evidence.
"""

from __future__ import annotations

import re
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
_JOURNAL = _REPO / "tests" / "fixtures" / "rc5_tester" / "golden_journal.txt"
_WALKTHROUGH = _REPO / "release" / "event" / "Demo" / "WALKTHROUGH.md"

#: XAUUSDm: tick 0.001 with tick value 0.1 -> one whole price unit is 100 USD
#: per 1.00 lot. Taken from the broker specification logged at OnInit, not
#: guessed.
USD_PER_PRICE_UNIT_PER_LOT = 100.0


def _journal() -> str:
    return _JOURNAL.read_text(encoding="utf-8")


def _walkthrough() -> str:
    return _WALKTHROUGH.read_text(encoding="utf-8")


def _executed() -> list[dict[str, str]]:
    plans = []
    for line in _journal().splitlines():
        if not line.startswith("RC5PLAN EXECUTED"):
            continue
        fields = dict(
            part.split("=", 1)
            for part in line.split("|")
            if "=" in part and not part.startswith("RC5PLAN")
        )
        plans.append(fields)
    return plans


def _deals() -> list[tuple[str, float, float]]:
    pattern = re.compile(
        r"deal #\d+ (buy|sell) ([0-9.]+) \w+ at ([0-9.]+) done"
    )
    return [
        (m.group(1), float(m.group(2)), float(m.group(3)))
        for m in pattern.finditer(_journal())
    ]


def test_the_journal_records_exactly_two_executions() -> None:
    assert len(_executed()) == 2
    assert len(_deals()) == 4, "two entries and two exits"


def test_the_demo_table_matches_the_journal() -> None:
    """Section 5 of the walkthrough, number by number."""
    golden_1, golden_2 = _executed()
    text = _walkthrough()

    for plan, expected in (
        (golden_1, {"entry": "4461.849", "sl": "4450.539", "tp": "4484.469"}),
        (golden_2, {"entry": "4398.837", "sl": "4391.069", "tp": "4414.373"}),
    ):
        for field, value in expected.items():
            assert plan[field] == value, (field, plan[field], value)
            assert value in text, f"{value} is not in the walkthrough"

    for field, values in (
        ("R", ("11.310", "7.768")),
        ("spreadToR", ("0.0230", "0.0335")),
        ("vol", ("0.04", "0.06")),
        ("margin", ("35.69", "52.79")),
    ):
        assert (golden_1[field], golden_2[field]) == values, field
        for value in values:
            assert value in text, f"{field} {value} missing from the walkthrough"


def test_THE_RISK_CLAIM_IS_THE_ONE_THE_EVIDENCE_SUPPORTS() -> None:
    """The rehearsal finding, locked.

    Predicted risk at the traded volumes is the sum of the `realized` field.
    The account's loss is the balance change. They are NOT equal, and the
    walkthrough must not say they are.
    """
    predicted = sum(float(p["realized"]) for p in _executed())
    assert round(predicted, 2) == 91.85

    balance = float(
        re.search(r"final balance ([0-9.]+)", _journal(), re.I).group(1)
    )
    loss = round(10_000.00 - balance, 2)
    assert loss == 92.30

    text = _walkthrough()
    assert "91.85" in text and "92.30" in text
    assert "predicted aggregate risk across the two trades was **92.30**" not in text


def test_the_slippage_gap_is_fully_explained() -> None:
    """The 0.45 must be arithmetic, not a shrug."""
    plans = _executed()
    deals = _deals()
    exits = [d for d in deals if d[0] == "sell"]

    slipped = 0.0
    for plan, (_, volume, fill) in zip(plans, exits, strict=True):
        stop = float(plan["sl"])
        assert fill < stop, "a BUY stop must fill at or below its level"
        slipped += (stop - fill) * USD_PER_PRICE_UNIT_PER_LOT * volume

    predicted = sum(float(p["realized"]) for p in plans)
    balance = float(
        re.search(r"final balance ([0-9.]+)", _journal(), re.I).group(1)
    )
    loss = 10_000.00 - balance

    assert round(slipped, 2) == 0.46
    assert "0.46" in _walkthrough(), "the demo must quote the slippage it proves"

    # predicted + slippage reconstructs the account's loss. The residual is
    # sub-cent: the journal prints risk to two decimals, so the reconstruction
    # cannot be exact and must not be asserted as if it were.
    residual = abs((predicted + slipped) - loss)
    assert residual < 0.02, residual


def test_the_refusal_numbers_are_real() -> None:
    """Section 6 — the strongest part of the talk, so the least room to be wrong."""
    journal = _journal()
    text = _walkthrough()
    for fragment in (
        "CONFIRMATION_PROXIMITY_INVALID",
        "distance=4145.936",
        "tolerance=0.260",
        "SPREAD_TO_RISK_INVALID",
        "spread=0.260",
        "R=0.240",
        "ratio=1.0833",
        "max=0.2500",
    ):
        assert fragment in journal, f"{fragment} is not in the journal"
        assert fragment in text, f"{fragment} is claimed nowhere in the demo"


def test_the_demo_never_promises_a_licence_state_it_cannot_produce() -> None:
    """No endpoint is deployed, so LICENSE_VALID cannot be shown live."""
    text = _walkthrough()
    assert "LICENSE_SERVER_UNREACHABLE" in text
    assert "REHEARSAL FINDING" in text


def test_the_forbidden_claims_stay_forbidden() -> None:
    lowered = _walkthrough().lower()
    for phrase in ("guaranteed", "risk-free", "uncrackable", "win rate"):
        section = lowered.split("## do not say", 1)
        assert phrase in section[-1], f"{phrase} must remain in the DO NOT list"
    # and must not be claimed anywhere before that section
    for phrase in ("guaranteed", "risk-free", "uncrackable"):
        assert phrase not in section[0], f"{phrase} is claimed in the talk itself"
