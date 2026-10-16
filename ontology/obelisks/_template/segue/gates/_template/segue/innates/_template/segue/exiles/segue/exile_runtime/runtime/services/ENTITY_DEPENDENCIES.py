#!/usr/bin/env python3
"""
SAVANT ENTITY DEPENDENCIES SERVICE

Authority:
- Runtime may inspect authority.
- Runtime may not become authority.
- Dependencies are projected from entity files when available.

Purpose:
- Collect dependency declarations for exile runtime entities.
- Remain safe when dependency files are missing or invalid.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


ROOT = Path("/root/savant-runtime")
EXILES_ROOT = (
    ROOT
    / "ontology/obelisks/_template/segue/gates/_template/segue/innates/_template/segue/exiles"
)


def _read_json(path: Path, fallback: Any) -> Any:
    try:
        if not path.is_file():
            return fallback
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return {
            "error": "invalid_json",
            "path": str(path),
            "detail": str(exc),
        }


def _entity_roots() -> list[Path]:
    if not EXILES_ROOT.is_dir():
        return []

    roots: list[Path] = []

    for child in sorted(EXILES_ROOT.iterdir(), key=lambda p: p.name):
        if not child.is_dir():
            continue
        if child.name.startswith("_"):
            continue
        if child.name == "segue":
            continue
        roots.append(child)

    return roots


def collect_dependencies() -> dict[str, Any]:
    rows: dict[str, Any] = {}

    for entity_root in _entity_roots():
        entity_id = entity_root.name

        candidates = [
            entity_root / "registry/dependencies.json",
            entity_root / "authority/dependencies.json",
            entity_root / "lineage/dependencies.json",
            entity_root / "runtime/dependencies.json",
            entity_root / "module.json",
        ]

        found: list[dict[str, Any]] = []

        for dep_file in candidates:
            payload = _read_json(dep_file, None)
            if payload is None:
                continue

            found.append(
                {
                    "source": str(dep_file),
                    "data": payload,
                }
            )

        rows[entity_id] = {
            "entity": entity_id,
            "root": str(entity_root),
            "dependencies": found,
        }

    return rows


def entity_dependencies() -> dict[str, Any]:
    return collect_dependencies()


def main() -> int:
    print(json.dumps(collect_dependencies(), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
