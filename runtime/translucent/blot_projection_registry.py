#!/usr/bin/env python3

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Iterable, Mapping

from runtime.translucent.blot_projection_lock import (
    ProjectionLock,
)


name = "blot."
schema = "savant.translucent.blot.projection-registry.v1"
authority_effect = "none"
mutation_effect = "none"
projection_only = True

max_entries = 4096


class BlotProjectionRegistryError(ValueError):
    pass


def _canonical(value: Any) -> str:
    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        )
    except (TypeError, ValueError) as exc:
        raise BlotProjectionRegistryError(
            "value is not canonical-json compatible"
        ) from exc


def _digest(value: Any) -> str:
    if isinstance(value, bytes):
        raw = value
    elif isinstance(value, str):
        raw = value.encode("utf-8")
    else:
        raw = _canonical(value).encode("utf-8")

    return hashlib.sha256(raw).hexdigest()


def _text(value: Any, field_name: str) -> str:
    result = str(value or "").strip()

    if not result:
        raise BlotProjectionRegistryError(
            f"{field_name} is required"
        )

    return result


def _unique(
    values: Iterable[Any],
) -> tuple[str, ...]:
    result: list[str] = []
    seen: set[str] = set()

    for value in values:
        token = str(value or "").strip()

        if not token or token in seen:
            continue

        seen.add(token)
        result.append(token)

    return tuple(result)


def _lock_data(
    value: ProjectionLock | Mapping[str, Any],
) -> dict[str, Any]:
    if isinstance(value, ProjectionLock):
        result = value.normalized()
    elif isinstance(value, Mapping):
        result = dict(value)
    else:
        raise BlotProjectionRegistryError(
            "projection lock must be ProjectionLock or mapping"
        )

    if not result.get("locked"):
        raise BlotProjectionRegistryError(
            "registry accepts locked projections only"
        )

    return result


@dataclass(frozen=True)
class ProjectionEntry:
    projection_id: str
    source_digest: str
    construction_digest: str
    execution_digest: str
    projection_digest: str
    profile_id: str
    lock_digest: str
    lineage: tuple[str, ...] = ()
    provenance: tuple[str, ...] = ()

    def normalized(self) -> dict[str, Any]:
        body = {
            "projection_id": _text(
                self.projection_id,
                "projection_id",
            ),
            "source_digest": _text(
                self.source_digest,
                "source_digest",
            ),
            "construction_digest": _text(
                self.construction_digest,
                "construction_digest",
            ),
            "execution_digest": _text(
                self.execution_digest,
                "execution_digest",
            ),
            "projection_digest": _text(
                self.projection_digest,
                "projection_digest",
            ),
            "profile_id": _text(
                self.profile_id,
                "profile_id",
            ),
            "lock_digest": _text(
                self.lock_digest,
                "lock_digest",
            ),
            "lineage": list(
                _unique(self.lineage)
            ),
            "provenance": list(
                _unique(self.provenance)
            ),
        }

        return {
            **body,
            "digest": _digest(body),
        }


class ProjectionRegistry:
    def __init__(self) -> None:
        self._entries: dict[
            str,
            ProjectionEntry,
        ] = {}

    def register(
        self,
        lock: ProjectionLock | Mapping[str, Any],
        *,
        projection_id: str | None = None,
        lineage: Iterable[str] = (),
        provenance: Iterable[str] = (),
    ) -> ProjectionEntry:
        if len(self._entries) >= max_entries:
            raise BlotProjectionRegistryError(
                "projection registry limit exceeded"
            )

        data = _lock_data(lock)

        lock_digest = str(
            data.get("digest")
            or _digest(data)
        )

        if projection_id is None:
            projection_id = (
                "blot-projection-"
                + _digest(
                    {
                        "projection_digest":
                            data["projection_digest"],
                        "profile_id":
                            data["profile_id"],
                        "lock_digest":
                            lock_digest,
                    }
                )[:24]
            )

        entry = ProjectionEntry(
            projection_id=projection_id,
            source_digest=data["source_digest"],
            construction_digest=data["construction_digest"],
            execution_digest=data["execution_digest"],
            projection_digest=data["projection_digest"],
            profile_id=data["profile_id"],
            lock_digest=lock_digest,
            lineage=tuple(lineage),
            provenance=tuple(provenance),
        )

        normalized = entry.normalized()

        existing = self._entries.get(
            normalized["projection_id"]
        )

        if existing is not None:
            if (
                existing.normalized()["digest"]
                != normalized["digest"]
            ):
                raise BlotProjectionRegistryError(
                    "projection identity conflict"
                )

            return existing

        for current in self._entries.values():
            current_data = current.normalized()

            same_projection = (
                current_data["projection_digest"]
                == normalized["projection_digest"]
                and current_data["profile_id"]
                == normalized["profile_id"]
            )

            if same_projection:
                if (
                    current_data["construction_digest"]
                    != normalized["construction_digest"]
                    or current_data["execution_digest"]
                    != normalized["execution_digest"]
                ):
                    raise BlotProjectionRegistryError(
                        "projection digest lineage conflict"
                    )

        self._entries[
            normalized["projection_id"]
        ] = entry

        return entry

    def get(
        self,
        projection_id: str,
    ) -> ProjectionEntry:
        projection_id = _text(
            projection_id,
            "projection_id",
        )

        try:
            return self._entries[
                projection_id
            ]
        except KeyError as exc:
            raise BlotProjectionRegistryError(
                f"unknown projection: {projection_id}"
            ) from exc

    def entries(
        self,
    ) -> tuple[ProjectionEntry, ...]:
        return tuple(
            self._entries[key]
            for key in sorted(
                self._entries
            )
        )

    def for_construction(
        self,
        construction_digest: str,
    ) -> tuple[ProjectionEntry, ...]:
        construction_digest = _text(
            construction_digest,
            "construction_digest",
        )

        return tuple(
            entry
            for entry in self.entries()
            if (
                entry.construction_digest
                == construction_digest
            )
        )

    def for_profile(
        self,
        profile_id: str,
    ) -> tuple[ProjectionEntry, ...]:
        profile_id = _text(
            profile_id,
            "profile_id",
        )

        return tuple(
            entry
            for entry in self.entries()
            if entry.profile_id
            == profile_id
        )

    def manifest(
        self,
    ) -> dict[str, Any]:
        entries = [
            entry.normalized()
            for entry in self.entries()
        ]

        body = {
            "schema": schema,
            "name": name,
            "authority_effect": authority_effect,
            "mutation_effect": mutation_effect,
            "projection_only": projection_only,
            "entry_count": len(entries),
            "entries": entries,
            "projection_is_authority": False,
            "registry_is_authority": False,
            "canonical_source": "construction-graph",
            "delete_projection_deletes_source": False,
        }

        return {
            **body,
            "digest": _digest(body),
        }


def manifest() -> dict[str, Any]:
    body = {
        "schema": schema,
        "name": name,
        "authority_effect": authority_effect,
        "mutation_effect": mutation_effect,
        "projection_only": projection_only,
        "registry_is_authority": False,
        "projection_is_authority": False,
        "canonical_source": "construction-graph",
        "identity": "content-and-lineage-bound",
        "max_entries": max_entries,
    }

    return {
        **body,
        "digest": _digest(body),
    }


__all__ = [
    "BlotProjectionRegistryError",
    "ProjectionEntry",
    "ProjectionRegistry",
    "authority_effect",
    "manifest",
    "max_entries",
    "mutation_effect",
    "name",
    "projection_only",
    "schema",
]


if __name__ == "__main__":
    print(
        json.dumps(
            manifest(),
            indent=2,
            sort_keys=True,
        )
    )
