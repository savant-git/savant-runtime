from __future__ import annotations

import json
from pathlib import Path

from CAPABILITY_REGISTRY import capabilities
from CONTRACT_REGISTRY import contracts
from EVENT_REGISTRY import events
from SERVICE_REGISTRY import services


OUT = Path("/root/savant-runtime/ontology/runtime_index.json")


OUT.write_text(
    json.dumps(
        {
            "capabilities": capabilities(),
            "contracts": contracts(),
            "events": events(),
            "services": services(),
        },
        indent=2,
    ),
    encoding="utf-8",
)

print(f"[OK] {OUT}")
