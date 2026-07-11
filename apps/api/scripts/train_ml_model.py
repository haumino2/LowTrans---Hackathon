"""Train and persist the sklearn KYT model."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from agent.ml_model import train_model  # noqa: E402


def main() -> int:
    meta = train_model(persist=True)
    print(json.dumps(meta, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
