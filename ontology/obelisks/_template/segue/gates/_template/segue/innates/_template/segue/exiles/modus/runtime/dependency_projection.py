
from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from typing import Any


schema = "savant://modus/dependency-projection/1.1.0"


class projection_error(ValueError):
    pass


def canonical(value: Any) -> bytes:
    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise projection_error(
            "value is not canonically serializable"
        ) from exc


def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()


def _identifier(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise projection_error(
            f"{label} must be a nonempty string"
        )
    return value


def _records(
    values: Sequence[Mapping[str, Any]],
    label: str,
) -> list[dict[str, Any]]:
    if isinstance(values, (str, bytes)) or not isinstance(
        values, Sequence
    ):
        raise projection_error(
            f"{label} must be a sequence"
        )

    records = []

    for index, value in enumerate(values):
        if not isinstance(value, Mapping):
            raise projection_error(
                f"{label}[{index}] must be a mapping"
            )

        record = dict(value)
        canonical(record)

        records.append({
            "position": index,
            "record": record,
            "digest": digest(record),
        })

    return records


def project(
    *,
    modu: str,
    imports: Sequence[Mapping[str, Any]],
    exports: Sequence[Mapping[str, Any]],
    source: str,
    source_digest: str,
) -> dict[str, Any]:
    """
    Project existing composition records without taking ownership.

    The caller must obtain imports and exports from the
    authoritative Savant composition mechanism. This function
    does not resolve imports, interpret masks, read filesystem
    conventions, or create authoritative dependency records.
    """
    modu = _identifier(modu, "modu")
    source = _identifier(source, "source")
    source_digest = _identifier(
        source_digest,
        "source_digest",
    )

    projected_imports = _records(imports, "imports")
    projected_exports = _records(exports, "exports")

    result = {
        "schema": schema,
        "modu": modu,
        "source": {
            "identity": source,
            "digest": source_digest,
        },
        "imports": projected_imports,
        "exports": projected_exports,
        "counts": {
            "imports": len(projected_imports),
            "exports": len(projected_exports),
        },
    }

    result["digest"] = digest(result)
    return result


def verify(
    value: Mapping[str, Any],
) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise projection_error(
            "projection must be a mapping"
        )

    result = dict(value)
    signature = result.pop("digest", None)

    if result.get("schema") != schema:
        raise projection_error(
            "unsupported projection schema"
        )

    if not isinstance(signature, str):
        raise projection_error(
            "projection digest is missing"
        )

    if digest(result) != signature:
        raise projection_error(
            "projection digest mismatch"
        )

    source = result.get("source")

    if not isinstance(source, Mapping):
        raise projection_error(
            "projection source is invalid"
        )

    _identifier(result.get("modu"), "modu")
    _identifier(source.get("identity"), "source identity")
    _identifier(source.get("digest"), "source digest")

    for label in ("imports", "exports"):
        entries = result.get(label)

        if not isinstance(entries, list):
            raise projection_error(
                f"{label} must be a list"
            )

        for index, entry in enumerate(entries):
            if not isinstance(entry, Mapping):
                raise projection_error(
                    "invalid projected entry"
                )

            if entry.get("position") != index:
                raise projection_error(
                    "projected entry order mismatch"
                )

            record = entry.get("record")

            if not isinstance(record, Mapping):
                raise projection_error(
                    "invalid source record"
                )

            if entry.get("digest") != digest(record):
                raise projection_error(
                    "source record digest mismatch"
                )

        if result.get("counts", {}).get(label) != len(entries):
            raise projection_error(
                "projected record count mismatch"
            )

    return dict(value)


def imports_of(
    value: Mapping[str, Any],
) -> list[dict[str, Any]]:
    current = verify(value)

    return [
        dict(entry["record"])
        for entry in current["imports"]
    ]


def exports_of(
    value: Mapping[str, Any],
) -> list[dict[str, Any]]:
    current = verify(value)

    return [
        dict(entry["record"])
        for entry in current["exports"]
    ]
