#!/usr/bin/env python3
"""CLI shim: python scripts/beadtrain.py … without pip install."""
from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from beadtrains.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
