
from __future__ import annotations

import hashlib
import json
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any


class composition_error(ValueError):
    pass


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _load(
    path: Path,
    *,
    owner: str,
    direction: str,
) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise composition_error(
            f"invalid {direction} composition source"
        )

    try:
        record = json.loads(
            path.read_text(encoding="utf-8")
        )
    except (OSError, UnicodeError, ValueError) as exc:
        raise composition_error(
            f"cannot read {direction} composition"
        ) from exc

    if not isinstance(record, dict):
        raise composition_error(
            "composition record must be an object"
        )

    if record.get("owner") != owner:
        raise composition_error(
            "composition ownership mismatch"
        )

    if record.get("id") != f"{owner}.{direction}":
        raise composition_error(
            "composition identity mismatch"
        )

    entries = record.get(direction)

    if not isinstance(entries, list):
        raise composition_error(
            "composition entries must be a list"
        )

    if not all(
        isinstance(entry, Mapping)
        for entry in entries
    ):
        raise composition_error(
            "composition entries must be objects"
        )

    return record


def project_composition(
    *,
    modu_directory: str | Path,
    modu: str,
    projector: Callable[..., dict[str, Any]],
) -> dict[str, Any]:
    """
    Adapt established composition records to a projection.

    The projector is supplied by the existing composition
    integration. This adapter neither resolves imports nor
    interprets shades or modus masks.
    """
    if not isinstance(modu, str) or not modu.strip():
        raise composition_error(
            "invalid modu identity"
        )

    if not callable(projector):
        raise composition_error(
            "projector must be callable"
        )

    directory = Path(modu_directory).resolve(
        strict=True
    )

    if not directory.is_dir():
        raise composition_error(
            "modu directory is unavailable"
        )

    composition = directory / "composition"

    imports = _load(
        composition / "imports.json",
        owner=modu,
        direction="imports",
    )

    exports = _load(
        composition / "exports.json",
        owner=modu,
        direction="exports",
    )

    sources = {
        "imports": {
            "identity": imports["id"],
            "digest": _digest(imports),
        },
        "exports": {
            "identity": exports["id"],
            "digest": _digest(exports),
        },
    }

    source_digest = _digest(sources)

    result = projector(
        modu=modu,
        imports=imports["imports"],
        exports=exports["exports"],
        source=f"{modu}.composition",
        source_digest=source_digest,
    )

    if not isinstance(result, dict):
        raise composition_error(
            "projector returned an invalid result"
        )

    if result.get("modu") != modu:
        raise composition_error(
            "projected modu identity mismatch"
        )

    projected_source = result.get("source")

    if not isinstance(projected_source, Mapping):
        raise composition_error(
            "projected source is missing"
        )

    if projected_source.get("digest") != source_digest:
        raise composition_error(
            "projected source digest mismatch"
        )

    return result
