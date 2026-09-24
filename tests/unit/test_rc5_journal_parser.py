"""The tester-journal parser, checked against the EA's OWN format strings.

The fixtures below are not hand-written guesses at what MT5 prints: the field
list is read out of `mt5/Experts/RC5_EA.mq5` and compared with what the parser
expects, so a change to the log breaks this file rather than a tester run.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from tools.rc5_journal_parser import (  # type: ignore[import-not-found]
    _PLAN_NAMED,
    JournalParseError,
    parse_journal,
    parse_plan_line,
)

_REPO = Path(__file__).resolve().parents[2]
_EA = _REPO / "mt5" / "Experts" / "RC5_EA.mq5"


def _ea() -> str:
    return _EA.read_text(encoding="utf-8-sig")


#: A realistic DENIED line, in the EA's exact field order.
DENIED_LINE = (
    "2026.08.30 22:45:00   RC5PLAN DENIED|XAUUSD~15~HAMMER~38983f2ef82a~0~1~1788127200"
    "|XAUUSDm|15|BUY|conf=1788127200|dec=1788127260|entry=4400.00|sl=308.74"
    "|tp=12582.52|R=4091.26|riskPct=0.50|riskMoney=50.00|realized=40.91|vol=0.01"
    "|spread=0.20|spreadToR=0.0000|margin=0.00|marginFrac=0.0000|confDist=4087.15"
    "|entryDist=4087.15|tol=0.20|Rticks=409126.0|R/entry=0.929832|TPdist=8182.52"
    "|TP/entry=1.859664|lc=7|xb=0|CONFIRMATION_PROXIMITY_INVALID"
)

WOULD_EXECUTE_LINE = DENIED_LINE.replace("DENIED|", "WOULD_EXECUTE|").replace(
    "CONFIRMATION_PROXIMITY_INVALID", "-"
)


# ---------------------------------------------------------------------------
# the parser matches the EA, not my memory of it
# ---------------------------------------------------------------------------


def test_the_parsers_field_list_matches_the_EAs_format_string() -> None:
    """The anti-drift check. Every `name=` in the EA's RC5PLAN format must be
    a field the parser knows, and vice versa."""
    src = _ea()
    start = src.index('PrintFormat("RC5PLAN ')
    raw = src[start : src.index(");", start)]
    # MQL5 splits the format across adjacent string literals, so the `|` before
    # a field can sit at the end of one chunk and the name at the start of the
    # next. Concatenate the literals before matching, or fields vanish.
    fmt = "".join(raw.split('"')[1::2])
    in_format = re.findall(r"\|(\w[\w/]*)=%", fmt)
    assert list(_PLAN_NAMED) == in_format, (list(_PLAN_NAMED), in_format)


def test_a_denied_plan_parses_every_field() -> None:
    row = parse_plan_line(DENIED_LINE)
    assert row.verdict == "DENIED"
    assert row.denied and not row.executed
    assert row.symbol == "XAUUSDm"
    assert row.side == "BUY"
    assert row.reason == "CONFIRMATION_PROXIMITY_INVALID"
    assert row.get("confDist") == "4087.15"
    assert row.get("tol") == "0.20"
    assert row.get("R") == "4091.26"
    assert set(_PLAN_NAMED) <= set(row.fields)


def test_the_signal_id_survives_intact() -> None:
    """The whole reason the id separator was changed to `~`."""
    row = parse_plan_line(DENIED_LINE)
    assert row.signal_id == "XAUUSD~15~HAMMER~38983f2ef82a~0~1~1788127200"
    assert "|" not in row.signal_id


def test_a_pipe_bearing_signal_id_is_refused_rather_than_misparsed() -> None:
    """The regression for the defect this parser exposed.

    With `|` inside the id every later field shifted by five positions and the
    line parsed into confident nonsense. It must now fail loudly.
    """
    broken = DENIED_LINE.replace(
        "XAUUSD~15~HAMMER~38983f2ef82a~0~1~1788127200",
        "XAUUSD|15|HAMMER~38983f2ef82a|0|1|1788127200",
    )
    with pytest.raises(JournalParseError):
        parse_plan_line(broken)


def test_a_missing_field_fails_loudly() -> None:
    truncated = DENIED_LINE.replace("|tol=0.20", "")
    with pytest.raises(JournalParseError, match="missing fields"):
        parse_plan_line(truncated)


# ---------------------------------------------------------------------------
# whole-journal parsing
# ---------------------------------------------------------------------------


JOURNAL = "\n".join(
    [
        "2026.08.30 22:45:00   RC5 EA v1.00 EA1: 3/3 symbols usable",
        "2026.08.30 22:45:00   RC5SETUP XAUUSDm|15|1788129900|HAMMER~82c481350728"
        "|0|1|4467.06|4450.54|1|0|1|7|ELIGIBLE|-",
        "2026.08.30 22:45:01   RC5DENY CONFIRMATION_PROXIMITY_INVALID "
        "XAUUSD~15~HAMMER~38983f2ef82a~0~1~1788127200|price=4400.00"
        "|zone=308.75..312.85|distance=4087.15|spread=0.20|tick=0.01|tolerance=0.20",
        DENIED_LINE,
        WOULD_EXECUTE_LINE,
        "2026.08.30 22:46:00   RC5TERM XAUUSDm poi=HAMMER~82c481350728 "
        "event=MITIGATED NO_CLOSE (non-terminal for V1)",
        "2026.08.30 22:47:00   RC5CLOSE XAUUSDm ticket=12345 "
        "why=GENUINE_INVALIDATION_CONFIRMED ok=1 retcode=10009",
        "2026.08.30 22:48:00   some unrelated terminal chatter",
    ]
)


def test_a_journal_separates_every_line_kind() -> None:
    parsed = parse_journal(JOURNAL)
    assert len(parsed.plans) == 2
    assert len(parsed.denies) == 1
    assert len(parsed.setups) == 1
    assert len(parsed.terminals) == 1
    assert len(parsed.closes) == 1
    assert parsed.unparsed == []


def test_the_deny_line_carries_the_proximity_evidence() -> None:
    reason, fields = parse_journal(JOURNAL).denies[0]
    assert reason == "CONFIRMATION_PROXIMITY_INVALID"
    assert fields["distance"] == "4087.15"
    assert fields["tolerance"] == "0.20"
    assert fields["zone"] == "308.75..312.85"


def test_nothing_executed_in_this_journal() -> None:
    parsed = parse_journal(JOURNAL)
    assert parsed.executed() == []
    assert parsed.deny_reasons() == ["CONFIRMATION_PROXIMITY_INVALID"]


def test_a_malformed_rc5_line_is_collected_not_silently_dropped() -> None:
    """A skipped line is how a tester run comes back looking cleaner than it
    was, so the parser keeps them."""
    parsed = parse_journal(JOURNAL + "\n2026.08.30 22:49:00   RC5PLAN garbage")
    assert len(parsed.unparsed) == 1
    assert "garbage" in parsed.unparsed[0]


def test_rows_can_be_looked_up_by_signal_identity() -> None:
    parsed = parse_journal(JOURNAL)
    rows = parsed.by_signal("XAUUSD~15~HAMMER~38983f2ef82a~0~1~1788127200")
    assert len(rows) == 2
