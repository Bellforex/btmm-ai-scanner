"""Make the shared test-support package importable.

``tests/performance_support`` is a package but ``tests`` itself deliberately is
not, so pytest never puts this directory on ``sys.path`` and the helpers are
unimportable from ``tests/unit``. Adding it here keeps exactly one module name
for those helpers — ``performance_support.x`` — which is also the name mypy
resolves them to. Making ``tests`` a package instead would rename every module
in the tree and break the bare cross-imports already in use here.
"""

from __future__ import annotations

import sys
from pathlib import Path

_TESTS_ROOT = str(Path(__file__).resolve().parent)
if _TESTS_ROOT not in sys.path:
    sys.path.insert(0, _TESTS_ROOT)
