from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict


schema = "savant.opus.runtime-json-io.v1"


def read_json(
    path: Path,
) -> Dict[str, Any]:
    return json.loads(
        path.read_text(
            encoding="utf-8"
        )
    )
