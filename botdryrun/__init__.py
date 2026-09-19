"""botdryrun — a PAPER / DRY-RUN trading bot on top of the frozen BTMM scanner.

Simulation only: no live broker, no network order API, no credentials. The
signal policy is a PRACTICE policy, not a validated strategy. See
``botdryrun/README.md``.
"""

from botdryrun.safety import EXECUTION_MODE

__all__ = ["EXECUTION_MODE"]
