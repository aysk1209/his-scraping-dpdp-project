"""Developer tools and test fixtures that sit beside ``src`` rather than in it.

Importing this package makes ``src`` importable, so ``python -m tools.<thing>``
works from a plain checkout without installing the project.
"""

from __future__ import annotations

import sys
from pathlib import Path

_SRC = Path(__file__).resolve().parents[1] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))
