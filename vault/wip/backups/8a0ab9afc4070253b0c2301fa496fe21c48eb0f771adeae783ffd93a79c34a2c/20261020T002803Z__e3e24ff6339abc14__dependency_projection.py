
from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any


schema = "savant://modus/dependency-projection/1.0.0"


class projection_error(ValueError):
    pass


def canonical(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()


def _read(path: Path) -> Any:
    if not path.is_file():
        raise projection_error(
            f"composition source unavailable: {path.name}"
        )

    if path.is_symlink():
        raise projection_error(
            "composition source cannot be a symlink"
        )

    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError) as exc:
        raise projection_error(
            "composition source cannot be read"
        ) from exc


def _entries(value: Any, name: str) -> list[Any]:
    if isinstance(value, list):
        return value

    if isinstance(value, Mapping):
        if name not in value:
            return []

        entries = value[name]

        if isinstance(entries, list):
            return entries

    raise projection_error(
        f"unsupported {name} composition representation"
    )


def _identity(value: Any) -> str | None:
    if isinstance(value, str):
        return value if value.strip() else None

    if isinstance(value, Mapping):
        for key in (
            "ref",
            "id",
            "target",
            "module",
            "source",
        ):
            identity = value.get(key)

            if isinstance(identity, str) and identity.strip():
                return identity

    return None


def _project_entries(
    entries: list[Any],
    *,
    direction: str,
) -> list[dict[str, Any]]:
    result = []

    for position, entry in enumerate(entries):
        result.append({
            "position": position,
            "direction": direction,
            "identity": _identity(entry),
            "source": entry,
            "source_digest": digest(entry),
        })

    return result


def project(module_directory: str | Path) -> dict[str, Any]:
    directory = Path(module_directory).resolve()

    if not directory.is_dir():
        raise projection_error(
            "module directory is unavailable"
        )

    composition = directory / "composition"

    imports_source = composition / "imports.json"
    exports_source = composition / "exports.json"

    imports_record = _read(imports_source)
    exports_record = _read(exports_source)

    imports = _project_entries(
        _entries(imports_record, "imports"),
        direction="import",
    )

    exports = _project_entries(
        _entries(exports_record, "exports"),
        direction="export",
    )

    result = {
        "schema": schema,
        "module_directory": str(directory),
        "sources": {
            "imports": {
                "path": str(imports_source),
                "digest": digest(imports_record),
            },
            "exports": {
                "path": str(exports_source),
                "digest": digest(exports_record),
            },
        },
        "imports": imports,
        "exports": exports,
        "counts": {
            "imports": len(imports),
            "exports": len(exports),
        },
        "unresolved_identities": [
            {
                "direction": entry["direction"],
                "position": entry["position"],
            }
            for entry in imports + exports
            if entry["identity"] is None
        ],
    }

    result["digest"] = digest(result)
    return result


def verify(projection: Mapping[str, Any]) -> bool:
    if not isinstance(projection, Mapping):
        raise projection_error(
            "projection must be a mapping"
        )

    value = dict(projection)
    signature = value.pop("digest", None)

    if value.get("schema") != schema:
        raise projection_error(
            "unsupported projection schema"
        )

    if signature != digest(value):
        raise projection_error(
            "projection digest mismatch"
        )

    return True


def dependencies(
    module_directory: str | Path,
) -> list[dict[str, Any]]:
    return project(module_directory)["imports"]


def dependents_contract(
    module_directory: str | Path,
) -> list[dict[str, Any]]:
    return project(module_directory)["exports"]
