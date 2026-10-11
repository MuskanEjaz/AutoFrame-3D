"""Run the bounded development-only T-LESS search strategy comparison."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from autoframe3d.tless_search import compare_search_strategies


if __name__ == "__main__":
    print(json.dumps(compare_search_strategies(), indent=2))