from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path


OUT = Path("/root/savant-runtime/ontology/runtime_reports/observatory_events.jsonl")
OUT.parent.mkdir(parents=True, exist_ok=True)


class ObservatoryKernel:

    def emit(self, event: str, payload=None):
        row = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event": event,
            "payload": payload or {},
        }

        with OUT.open("a", encoding="utf-8") as f:
            f.write(json.dumps(row) + "\n")

        return row


observatory_kernel = ObservatoryKernel()
