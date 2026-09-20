# BTRC V1 — V1-A DEV-Set Signal-Outcome Characterization — Summary

**Status: draft placeholder — being populated as the DEV-set replay run completes.**

This document will summarize, in prose and tables, the headline results of
`docs/validation/BTRC_V1_VALIDATION_PROTOCOL.md`'s V1-A characterization,
computed by the harness under `tests/parity_support/v1a_*.py` and
`tests/unit/test_v1a_*.py`, run once over the frozen DEV set (2903 M15
bars, 2026-05-31T22:00 to 2026-07-14T17:00 UTC) per
`docs/validation/BTRC_V1_V1A_DATA_PROVENANCE_MANIFEST.md`.

**The OOS set remains locked — not opened — throughout.**

This placeholder will be replaced with the actual headline numbers once
the full-DEV run (`tests/parity_support/v1a_run_dev.py`) completes and
`tests/parity_support/v1a_generate_report.py` produces the full report
under `artifacts/v1a_validation/` (gitignored). No metric prohibited by
protocol §12 (win rate, profit factor, expectancy, R-multiple, drawdown,
Sharpe, equity curve, "return on risk") appears anywhere in this document
or in the underlying report.
