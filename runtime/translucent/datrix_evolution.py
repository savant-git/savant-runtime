#!/usr/bin/env python3

from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from typing import Any, Iterable, Mapping, Sequence


schema = "savant.translucent.datrix-evolution.v1"
authority_effect = "none"
MAX_CURRENT_RECORDS = 100_000
MAX_EVOLUTION_DEPTH = 256


class DatrixEvolutionError(ValueError):
    pass


def _canonical(value: Any) -> str:
    try:
        return json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
    except (TypeError, ValueError) as exc:
        raise DatrixEvolutionError(f"value is not canonical-json compatible: {exc}") from exc


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _path_get(value: Any, path: str) -> Any:
    current = value
    for part in str(path).split("."):
        if not part:
            continue
        if isinstance(current, Mapping):
            current = current.get(part)
        elif isinstance(current, Sequence) and not isinstance(current, (str, bytes, bytearray)):
            try:
                current = current[int(part)]
            except (ValueError, IndexError):
                return None
        else:
            return None
    return current


def _path_set(target: dict[str, Any], path: str, value: Any) -> None:
    parts = [part for part in str(path).split(".") if part]
    if len(parts) < 2 or parts[0] not in {"payload", "metadata"}:
        raise DatrixEvolutionError(
            "update paths must address payload.* or metadata.*"
        )
    current: dict[str, Any] = target
    for part in parts[:-1]:
        existing = current.get(part)
        if existing is None:
            current[part] = {}
            existing = current[part]
        if not isinstance(existing, dict):
            raise DatrixEvolutionError(f"update path crosses non-object at {part!r}")
        current = existing
    current[parts[-1]] = deepcopy(value)


def _path_unset(target: dict[str, Any], path: str) -> None:
    parts = [part for part in str(path).split(".") if part]
    if len(parts) < 2 or parts[0] not in {"payload", "metadata"}:
        raise DatrixEvolutionError(
            "unset paths must address payload.* or metadata.*"
        )
    current: Any = target
    for part in parts[:-1]:
        if not isinstance(current, Mapping) or part not in current:
            return
        current = current[part]
    if isinstance(current, dict):
        current.pop(parts[-1], None)


def build_revision_record(
    base: Mapping[str, Any],
    *,
    successor_id: str,
    set_values: Mapping[str, Any],
    unset_paths: Iterable[str],
    status: str | None,
    truth: Mapping[str, Any],
    source_node: str,
    semantic_terms: Mapping[str, str],
) -> dict[str, Any]:
    base_id = str(base.get("id") or "").strip()
    successor = str(successor_id or "").strip()
    if not base_id or not successor or successor == base_id:
        raise DatrixEvolutionError("revision requires distinct base and successor identities")
    patch = {
        "set": {str(key): deepcopy(value) for key, value in sorted(set_values.items())},
        "unset": sorted({str(path) for path in unset_paths if str(path)}),
        "status": None if status is None else str(status),
    }
    record = {
        "id": successor,
        "kind": str(base.get("kind") or "").strip(),
        "status": str(status if status is not None else base.get("status") or "active"),
        "payload": {},
        "metadata": {},
        "dependencies": sorted(
            set(str(item) for item in base.get("dependencies", []) if str(item)) | {base_id}
        ),
        "relationships": [],
        "provenance": {
            "source": schema,
            "source_node": source_node,
            "base": base_id,
            "base_digest": base.get("digest"),
        },
        "lineage": {
            "derived_from": [base_id],
            "supersedes": [base_id],
            "superseded_by": None,
            "history": [
                {
                    "event": "supersedes",
                    "predecessor": base_id,
                    "successor": successor,
                }
            ],
        },
        "extensions": {
            "datrix_evolution": {
                "schema": schema,
                "type": "revision",
                "base": base_id,
                "base_digest": base.get("digest"),
                "patch": patch,
                "semantic_terms": dict(semantic_terms),
            },
            "truth": deepcopy(dict(truth)),
        },
    }
    return record


def build_retirement_record(
    base: Mapping[str, Any],
    *,
    tombstone_id: str,
    reason: str,
    truth: Mapping[str, Any],
    source_node: str,
    semantic_terms: Mapping[str, str],
) -> dict[str, Any]:
    base_id = str(base.get("id") or "").strip()
    tombstone = str(tombstone_id or "").strip()
    if not base_id or not tombstone or tombstone == base_id:
        raise DatrixEvolutionError("retirement requires distinct subject and tombstone identities")
    return {
        "id": tombstone,
        "kind": str(base.get("kind") or "").strip(),
        "status": "retired",
        "payload": {},
        "metadata": {},
        "dependencies": sorted(
            set(str(item) for item in base.get("dependencies", []) if str(item)) | {base_id}
        ),
        "relationships": [],
        "provenance": {
            "source": schema,
            "source_node": source_node,
            "subject": base_id,
            "subject_digest": base.get("digest"),
        },
        "lineage": {
            "derived_from": [base_id],
            "supersedes": [],
            "superseded_by": None,
            "history": [
                {
                    "event": "retires",
                    "predecessor": base_id,
                    "successor": tombstone,
                }
            ],
        },
        "extensions": {
            "datrix_evolution": {
                "schema": schema,
                "type": "retirement",
                "base": base_id,
                "base_digest": base.get("digest"),
                "reason": str(reason or ""),
                "semantic_terms": dict(semantic_terms),
            },
            "truth": deepcopy(dict(truth)),
        },
    }


def evolution_info(record: Mapping[str, Any]) -> Mapping[str, Any] | None:
    extensions = record.get("extensions")
    if not isinstance(extensions, Mapping):
        return None
    value = extensions.get("datrix_evolution")
    return value if isinstance(value, Mapping) else None


def materialize_current(records: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    if len(records) > MAX_CURRENT_RECORDS:
        raise DatrixEvolutionError(
            f"current-view source exceeds {MAX_CURRENT_RECORDS} records"
        )
    by_id = {
        str(record.get("id")): deepcopy(dict(record))
        for record in records
        if str(record.get("id") or "") and str(record.get("kind") or "") != "segue"
    }
    transitions = [
        record
        for record in records
        if str(record.get("kind") or "") == "segue"
        and isinstance(record.get("payload"), Mapping)
        and str(record["payload"].get("relation") or "") in {"supersedes", "retires"}
    ]
    superseded = {
        str(record["payload"].get("to") or "")
        for record in transitions
        if str(record["payload"].get("to") or "")
    }
    resolving: set[str] = set()
    cache: dict[str, dict[str, Any] | None] = {}

    def resolve(identity: str, depth: int = 0) -> dict[str, Any] | None:
        if depth > MAX_EVOLUTION_DEPTH:
            raise DatrixEvolutionError(
                f"evolution chain exceeds depth {MAX_EVOLUTION_DEPTH}"
            )
        if identity in cache:
            value = cache[identity]
            return None if value is None else deepcopy(value)
        if identity in resolving:
            raise DatrixEvolutionError(f"evolution cycle detected at {identity}")
        record = by_id.get(identity)
        if record is None:
            raise DatrixEvolutionError(f"evolution base is missing: {identity}")
        resolving.add(identity)
        info = evolution_info(record)
        if info is None:
            effective = deepcopy(record)
        else:
            kind = str(info.get("type") or "")
            base_id = str(info.get("base") or "")
            if kind == "retirement":
                effective = None
            elif kind == "revision":
                base = resolve(base_id, depth + 1)
                if base is None:
                    raise DatrixEvolutionError(
                        f"revision {identity} derives from retired base {base_id}"
                    )
                effective = deepcopy(base)
                effective["id"] = identity
                effective["kind"] = str(record.get("kind") or base.get("kind") or "")
                effective["status"] = str(record.get("status") or base.get("status") or "active")
                patch = info.get("patch") if isinstance(info.get("patch"), Mapping) else {}
                set_values = patch.get("set") if isinstance(patch.get("set"), Mapping) else {}
                for path, value in sorted(set_values.items()):
                    _path_set(effective, str(path), value)
                unset_paths = patch.get("unset") if isinstance(patch.get("unset"), list) else []
                for path in unset_paths:
                    _path_unset(effective, str(path))
                base_extensions = (
                    deepcopy(dict(effective.get("extensions") or {}))
                    if isinstance(effective.get("extensions"), Mapping)
                    else {}
                )
                revision_extensions = (
                    deepcopy(dict(record.get("extensions") or {}))
                    if isinstance(record.get("extensions"), Mapping)
                    else {}
                )
                base_extensions.update(revision_extensions)
                effective["extensions"] = base_extensions
                effective["provenance"] = deepcopy(record.get("provenance") or {})
                effective["lineage"] = deepcopy(record.get("lineage") or {})
                effective["dependencies"] = deepcopy(record.get("dependencies") or [])
                effective["canonical_digest"] = record.get("digest")
                effective["canonical_revision"] = identity
                effective["projection_only"] = True
                effective["authority_effect"] = authority_effect
                effective["digest"] = _digest(
                    {key: value for key, value in effective.items() if key != "digest"}
                )
            else:
                raise DatrixEvolutionError(f"unknown datrix evolution type: {kind!r}")
        resolving.remove(identity)
        cache[identity] = None if effective is None else deepcopy(effective)
        return None if effective is None else deepcopy(effective)

    heads = [identity for identity in sorted(by_id) if identity not in superseded]
    output: list[dict[str, Any]] = []
    for identity in heads:
        value = resolve(identity)
        if value is not None:
            output.append(value)
    return output


def _matches(record: Mapping[str, Any], clause: Mapping[str, Any]) -> bool:
    op = str(clause.get("op") or "eq").casefold()
    actual = _path_get(record, str(clause.get("path") or ""))
    expected = clause.get("value")
    if op == "eq":
        return actual == expected
    if op == "ne":
        return actual != expected
    if op == "exists":
        return (actual is not None) == bool(expected)
    if op == "contains":
        try:
            return expected in actual
        except TypeError:
            return False
    if op == "in":
        return actual in expected if isinstance(expected, Sequence) else False
    if op == "prefix":
        return isinstance(actual, str) and actual.startswith(str(expected))
    raise DatrixEvolutionError(f"unsupported where operator: {op}")



def _sort_token(value: Any) -> tuple[int, Any]:
    if value is None:
        return (4, "")
    if isinstance(value, bool):
        return (0, int(value))
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return (1, float(value))
    if isinstance(value, str):
        return (2, value)
    return (3, _canonical(value))


def select_current(
    interface: Any,
    *,
    kinds: Sequence[str],
    where: Sequence[Mapping[str, Any]],
    order_by: str,
    direction: str,
    limit: int | None,
    fields: Sequence[str],
) -> dict[str, Any]:
    raw = interface.select(
        kinds=(),
        where=(),
        order_by="id",
        direction="asc",
        limit=None,
        fields=(),
    )
    records = materialize_current(raw.get("records", []))
    kind_set = {str(item) for item in kinds}
    if kind_set:
        records = [item for item in records if str(item.get("kind") or "") in kind_set]
    for clause in where:
        records = [item for item in records if _matches(item, clause)]
    reverse = str(direction or "asc").casefold() == "desc"
    records.sort(
        key=lambda item: _sort_token(_path_get(item, order_by)),
        reverse=reverse,
    )
    if limit is not None:
        records = records[:limit]
    if fields:
        records = [
            {str(field): deepcopy(_path_get(item, str(field))) for field in fields}
            for item in records
        ]
    result = {
        "schema": "savant.translucent.datrix-current-view.v1",
        "kind": "isotope",
        "view": "current",
        "count": len(records),
        "records": records,
        "projection_only": True,
        "authority_effect": authority_effect,
    }
    result["digest"] = _digest(result)
    return result


__all__ = [
    "DatrixEvolutionError",
    "MAX_CURRENT_RECORDS",
    "MAX_EVOLUTION_DEPTH",
    "authority_effect",
    "build_retirement_record",
    "build_revision_record",
    "evolution_info",
    "materialize_current",
    "schema",
    "select_current",
]
