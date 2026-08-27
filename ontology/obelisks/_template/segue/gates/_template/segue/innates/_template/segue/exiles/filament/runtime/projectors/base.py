from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict


class FilamentProjectionError(RuntimeError):
    pass


def read_text(path: Path) -> str:
    return path.read_text(
        encoding="utf-8",
        errors="replace",
    )


def read_json_safe(
    path: Path,
) -> Dict[str, Any]:
    try:
        return json.loads(
            read_text(path)
        )
    except Exception as exc:
        return {
            "path": str(path),
            "error": "invalid_json",
            "detail": str(exc),
        }


def entity_record(
    path: Path,
) -> Dict[str, Any]:
    return {
        "path": str(path),
        "name": path.name,
        "is_dir": path.is_dir(),
        "is_file": path.is_file(),
    }
