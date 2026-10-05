from __future__ import annotations

import sys
from pathlib import Path

SERVICES = Path(__file__).resolve().parents[1] / "services"

if str(SERVICES) not in sys.path:
    sys.path.insert(0, str(SERVICES))

from ENTITY_AUDIT import audit


if __name__ == "__main__":
    out = audit()
    print(f"[OK] entity audit written: {out}")
