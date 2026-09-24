"""Parse an MT5 tester journal into structured rows.

Tester verification should be a diff, not a reading exercise. This turns the
EA's own log lines into records that can be compared field by field against the
expected-result templates.

It parses four line kinds:

``RC5SETUP``  the analytical state the EA received
``RC5PLAN``   one complete execution decision, every field
``RC5DENY``   the detailed refusal emitted by a quality gate
``RC5TERM``   a terminal/lifecycle event and what V1 did about it
``RC5CLOSE``  an actual position close

WHY THE SIGNAL ID USES ``~``
----------------------------
Writing this parser is what exposed it. The signal id is
``symbol~tf~poiId~type~direction~barTime`` and appears INSIDE pipe-delimited
``RC5PLAN`` lines. With ``|`` as its internal separator every plan line carried
five extra pipes and no positional parse was safe. The id was changed to ``~``
in both the EA and the Python mirror; this parser assumes that and asserts it.

Nothing here interprets or judges. It reads what the EA wrote.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

__all__ = [
    "JournalParseError",
    "ParsedJournal",
    "PlanRow",
    "parse_journal",
    "parse_plan_line",
]

#: `RC5PLAN <verdict>|<signalId>|<symbol>|<tf>|<side>|conf=..|dec=..|...|<reason>`
#: The first five fields are positional; everything after is `name=value`.
_PLAN_POSITIONAL = ("verdict", "signal_id", "symbol", "timeframe", "side")

#: Named fields the EA emits, in its own order. Kept explicit so a field added
#: to the log without updating this list fails loudly instead of vanishing.
_PLAN_NAMED = (
    "conf",
    "dec",
    "entry",
    "sl",
    "tp",
    "R",
    "riskPct",
    "riskMoney",
    "realized",
    "vol",
    "spread",
    "spreadToR",
    "margin",
    "marginFrac",
    "confDist",
    "entryDist",
    "tol",
    "Rticks",
    "R/entry",
    "TPdist",
    "TP/entry",
    "lc",
    "xb",
)


class JournalParseError(ValueError):
    """A line that looks like an EA log line but does not parse."""


@dataclass(frozen=True)
class PlanRow:
    """One `RC5PLAN` decision, exactly as logged."""

    verdict: str
    signal_id: str
    symbol: str
    timeframe: str
    side: str
    reason: str
    fields: dict[str, str]

    @property
    def executed(self) -> bool:
        return self.verdict == "EXECUTED"

    @property
    def denied(self) -> bool:
        return self.verdict == "DENIED"

    def get(self, name: str) -> str | None:
        return self.fields.get(name)


@dataclass
class ParsedJournal:
    plans: list[PlanRow] = field(default_factory=list)
    denies: list[tuple[str, dict[str, str]]] = field(default_factory=list)
    setups: list[list[str]] = field(default_factory=list)
    terminals: list[str] = field(default_factory=list)
    closes: list[str] = field(default_factory=list)
    #: Lines that started with an RC5 marker but could not be parsed. Surfaced
    #: rather than dropped: a silently skipped line is how a tester run comes
    #: back looking cleaner than it was.
    unparsed: list[str] = field(default_factory=list)

    def executed(self) -> list[PlanRow]:
        return [p for p in self.plans if p.executed]

    def by_signal(self, signal_id: str) -> list[PlanRow]:
        return [p for p in self.plans if p.signal_id == signal_id]

    def deny_reasons(self) -> list[str]:
        return [p.reason for p in self.plans if p.denied]


def parse_plan_line(line: str) -> PlanRow:
    """Parse one `RC5PLAN` line. Raises rather than guessing."""
    body = line.split("RC5PLAN ", 1)[1].strip() if "RC5PLAN " in line else ""
    if not body:
        raise JournalParseError(line)

    parts = body.split("|")
    if len(parts) < len(_PLAN_POSITIONAL) + 1:
        raise JournalParseError(line)

    positional = dict(zip(_PLAN_POSITIONAL, parts[: len(_PLAN_POSITIONAL)], strict=True))
    if "~" not in positional["signal_id"] and positional["signal_id"] != "":
        # A `|` inside the id would have shifted every field. Fail loudly.
        raise JournalParseError(f"signal id is not '~'-separated: {line}")

    named: dict[str, str] = {}
    for chunk in parts[len(_PLAN_POSITIONAL) : -1]:
        if "=" not in chunk:
            raise JournalParseError(f"unnamed field {chunk!r} in: {line}")
        key, value = chunk.split("=", 1)
        named[key] = value

    missing = [k for k in _PLAN_NAMED if k not in named]
    if missing:
        raise JournalParseError(f"missing fields {missing} in: {line}")

    return PlanRow(
        verdict=positional["verdict"],
        signal_id=positional["signal_id"],
        symbol=positional["symbol"],
        timeframe=positional["timeframe"],
        side=positional["side"],
        reason=parts[-1],
        fields=named,
    )


_DENY_RE = re.compile(r"RC5DENY (\w+) (.+)")


def _parse_deny(line: str) -> tuple[str, dict[str, str]]:
    match = _DENY_RE.search(line)
    if not match:
        raise JournalParseError(line)
    reason, body = match.group(1), match.group(2)
    fields: dict[str, str] = {}
    chunks = body.split("|")
    fields["signal_id"] = chunks[0]
    for chunk in chunks[1:]:
        if "=" in chunk:
            key, value = chunk.split("=", 1)
            fields[key] = value
    return reason, fields


def parse_journal(text: str) -> ParsedJournal:
    """Parse a whole journal. Unknown RC5 lines are COLLECTED, not dropped."""
    out = ParsedJournal()
    for raw in text.splitlines():
        line = raw.rstrip()
        try:
            if "RC5PLAN " in line:
                out.plans.append(parse_plan_line(line))
            elif "RC5DENY " in line:
                out.denies.append(_parse_deny(line))
            elif "RC5SETUP " in line:
                out.setups.append(line.split("RC5SETUP ", 1)[1].split("|"))
            elif "RC5TERM " in line:
                out.terminals.append(line.split("RC5TERM ", 1)[1])
            elif "RC5CLOSE " in line:
                out.closes.append(line.split("RC5CLOSE ", 1)[1])
        except JournalParseError:
            out.unparsed.append(line)
    return out


def parse_journal_file(path: Path) -> ParsedJournal:
    return parse_journal(path.read_text(encoding="utf-8", errors="replace"))
