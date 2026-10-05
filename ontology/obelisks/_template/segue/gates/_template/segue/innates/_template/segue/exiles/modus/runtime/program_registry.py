#!/usr/bin/env python3

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from pathlib import Path
from typing import Any

try:
    from .program_composition import (
        ProgramCompositionGraph,
        SourceDecomposition,
        digest,
    )
    from .program_store import (
        ProgramCompositionStore,
        ProgramStoreError,
    )
except ImportError:
    from program_composition import (
        ProgramCompositionGraph,
        SourceDecomposition,
        digest,
    )
    from program_store import (
        ProgramCompositionStore,
        ProgramStoreError,
    )


ROOT = Path(
    "/root/savant-runtime"
).resolve()

DEFAULT_REGISTRY = (
    ROOT
    / "runtime"
    / "program-composition"
    / "registry.json"
)


class ProgramRegistryError(
    RuntimeError
):
    pass


def sha256_bytes(
    payload: bytes,
) -> str:
    return hashlib.sha256(
        payload
    ).hexdigest()


def atomic_write_json(
    path: Path,
    payload: dict[str, Any],
) -> None:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    descriptor, temporary_name = (
        tempfile.mkstemp(
            prefix=f".{path.name}.",
            suffix=".tmp",
            dir=str(path.parent),
        )
    )

    temporary = Path(
        temporary_name
    )

    try:
        with os.fdopen(
            descriptor,
            "w",
            encoding="utf-8",
        ) as handle:
            json.dump(
                payload,
                handle,
                indent=2,
                sort_keys=True,
                ensure_ascii=False,
            )

            handle.write(
                "\n"
            )

            handle.flush()

            os.fsync(
                handle.fileno()
            )

        os.replace(
            temporary,
            path,
        )

    except Exception:
        temporary.unlink(
            missing_ok=True
        )
        raise


class ProgramProjectionRegistry:
    schema = (
        "savant://program/"
        "projection-registry/1.0.0"
    )

    owner = "exile:modus"

    def __init__(
        self,
        path: Path = DEFAULT_REGISTRY,
    ) -> None:
        self.path = path.resolve()

        if not self.path.is_absolute():
            raise ProgramRegistryError(
                "registry path must be absolute"
            )

        if not (
            self.path == ROOT
            or ROOT in self.path.parents
        ):
            raise ProgramRegistryError(
                "registry must remain inside Savant root"
            )

    def _empty(
        self,
    ) -> dict[str, Any]:
        payload = {
            "schema": self.schema,
            "owner": self.owner,
            "authoritative": False,
            "authority_effect": "none",
            "entries": {},
        }

        payload["digest"] = digest(
            payload
        )

        return payload

    def load(
        self,
    ) -> dict[str, Any]:
        if not self.path.exists():
            return self._empty()

        try:
            payload = json.loads(
                self.path.read_text(
                    encoding="utf-8"
                )
            )
        except json.JSONDecodeError as exc:
            raise ProgramRegistryError(
                f"invalid registry JSON: {exc}"
            ) from exc

        if not isinstance(
            payload,
            dict,
        ):
            raise ProgramRegistryError(
                "registry root must be object"
            )

        if (
            payload.get("schema")
            != self.schema
        ):
            raise ProgramRegistryError(
                "unsupported registry schema"
            )

        if (
            payload.get("authoritative")
            is not False
        ):
            raise ProgramRegistryError(
                "registry must remain non-authoritative"
            )

        stored_digest = (
            payload.get(
                "digest"
            )
        )

        material = dict(
            payload
        )

        material.pop(
            "digest",
            None,
        )

        if digest(material) != stored_digest:
            raise ProgramRegistryError(
                "registry digest mismatch"
            )

        entries = payload.get(
            "entries"
        )

        if not isinstance(
            entries,
            dict,
        ):
            raise ProgramRegistryError(
                "registry entries must be object"
            )

        return payload

    def save(
        self,
        payload: dict[str, Any],
    ) -> None:
        material = dict(
            payload
        )

        material.pop(
            "digest",
            None,
        )

        material["digest"] = digest(
            material
        )

        atomic_write_json(
            self.path,
            material,
        )

    def register(
        self,
        *,
        source_path: Path,
        store_path: Path,
        decomposition: SourceDecomposition,
    ) -> dict[str, Any]:
        source_path = (
            source_path.resolve()
        )

        store_path = (
            store_path.resolve()
        )

        if not source_path.is_file():
            raise ProgramRegistryError(
                f"missing source: {source_path}"
            )

        if not store_path.is_file():
            raise ProgramRegistryError(
                f"missing store: {store_path}"
            )

        source_bytes = (
            source_path.read_bytes()
        )

        source_digest = sha256_bytes(
            source_bytes
        )

        if (
            source_digest
            != decomposition.source_digest
        ):
            raise ProgramRegistryError(
                "source digest differs from "
                "decomposition digest"
            )

        payload = self.load()

        entries = dict(
            payload["entries"]
        )

        key = str(
            source_path.relative_to(
                ROOT
            )
        )

        entry = {
            "source_path": key,
            "source_digest": (
                source_digest
            ),
            "script_instance_id": (
                decomposition
                .script_instance_id
            ),
            "store_path": str(
                store_path.relative_to(
                    ROOT
                )
            ),
            "projection_owner": (
                self.owner
            ),
            "source_remains_live": True,
            "projection_authoritative": (
                False
            ),
            "mutation_authorized": False,
            "drift_policy": "fail-closed",
        }

        entry["digest"] = digest(
            entry
        )

        entries[key] = entry

        payload["entries"] = entries

        self.save(
            payload
        )

        return entry

    def verify_entry(
        self,
        source_path: Path,
    ) -> dict[str, Any]:
        source_path = (
            source_path.resolve()
        )

        payload = self.load()

        key = str(
            source_path.relative_to(
                ROOT
            )
        )

        entry = payload[
            "entries"
        ].get(
            key
        )

        if not isinstance(
            entry,
            dict,
        ):
            raise ProgramRegistryError(
                f"unregistered source: {key}"
            )

        current_source_digest = (
            sha256_bytes(
                source_path.read_bytes()
            )
        )

        source_matches = (
            current_source_digest
            == entry[
                "source_digest"
            ]
        )

        store_path = (
            ROOT
            / entry[
                "store_path"
            ]
        ).resolve()

        store = (
            ProgramCompositionStore()
        )

        try:
            graph, decomposition = (
                store.load(
                    store_path
                )
            )
        except ProgramStoreError as exc:
            raise ProgramRegistryError(
                str(exc)
            ) from exc

        regenerated = (
            graph.project_text(
                decomposition
                .script_instance_id
            )
            .encode(
                "utf-8"
            )
        )

        regenerated_digest = (
            sha256_bytes(
                regenerated
            )
        )

        projection_matches = (
            regenerated_digest
            == entry[
                "source_digest"
            ]
        )

        passed = (
            source_matches
            and projection_matches
        )

        return {
            "source_path": key,
            "registered_digest": (
                entry[
                    "source_digest"
                ]
            ),
            "current_source_digest": (
                current_source_digest
            ),
            "regenerated_digest": (
                regenerated_digest
            ),
            "source_matches": (
                source_matches
            ),
            "projection_matches": (
                projection_matches
            ),
            "drift_detected": (
                not source_matches
            ),
            "projection_authoritative": (
                False
            ),
            "source_remains_live": True,
            "mutation_authorized": False,
            "authority_effect": "none",
            "passed": passed,
        }

    def status(
        self,
    ) -> dict[str, Any]:
        payload = self.load()

        result = {
            "schema": self.schema,
            "owner": self.owner,
            "registry": str(
                self.path
            ),
            "entry_count": len(
                payload[
                    "entries"
                ]
            ),
            "authoritative": False,
            "authority_effect": "none",
            "drift_policy": "fail-closed",
        }

        result["digest"] = digest(
            result
        )

        return result


def main() -> int:
    registry = (
        ProgramProjectionRegistry()
    )

    print(
        json.dumps(
            registry.status(),
            indent=2,
            sort_keys=True,
        )
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
