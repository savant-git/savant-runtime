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
        CodeSegue,
        ProgramCompositionError,
        ProgramCompositionGraph,
        ProgramInstance,
        SourceDecomposition,
        canonical_json,
        digest,
    )
except ImportError:
    from program_composition import (
        CodeSegue,
        ProgramCompositionError,
        ProgramCompositionGraph,
        ProgramInstance,
        SourceDecomposition,
        canonical_json,
        digest,
    )

ROOT = Path(
    "/root/savant-runtime"
).resolve()

DEFAULT_STORE_ROOT = (
    ROOT
    / "runtime"
    / "program-composition"
    / "instances"
)


class ProgramStoreError(
    ProgramCompositionError
):
    pass


def digest_bytes(
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


def load_json(
    path: Path,
) -> dict[str, Any]:
    if not path.is_file():
        raise ProgramStoreError(
            f"missing program store: {path}"
        )

    try:
        payload = json.loads(
            path.read_text(
                encoding="utf-8"
            )
        )

    except json.JSONDecodeError as exc:
        raise ProgramStoreError(
            f"invalid program store JSON: "
            f"{path}: {exc}"
        ) from exc

    if not isinstance(
        payload,
        dict,
    ):
        raise ProgramStoreError(
            "program store root must be "
            "a JSON object"
        )

    return payload


class ProgramCompositionStore:
    schema = (
        "savant://program/"
        "composition-store/1.0.0"
    )

    owner = "exile:modus"

    def __init__(
        self,
        root: Path = DEFAULT_STORE_ROOT,
    ) -> None:
        root = root.resolve()

        if not root.is_absolute():
            raise ProgramStoreError(
                "program store root "
                "must be absolute"
            )

        if not (
            root == ROOT
            or ROOT in root.parents
        ):
            raise ProgramStoreError(
                "program store must remain "
                "inside Savant root"
            )

        self.root = root

    def snapshot(
        self,
        graph: ProgramCompositionGraph,
        decomposition: SourceDecomposition,
    ) -> dict[str, Any]:
        validation = (
            graph.validate()
        )

        if validation["valid"] is not True:
            raise ProgramStoreError(
                "cannot persist invalid "
                "program composition graph"
            )

        manifest = (
            graph.project_manifest(
                decomposition.script_instance_id
            )
        )

        relevant_ids = {
            item["instance_id"]
            for item
            in manifest[
                "source_instances"
            ]
        }

        instances = [
            instance.projection()
            for instance
            in graph.instances
            if instance.instance_id
            in relevant_ids
        ]

        segue_ids = set(
            decomposition.segue_ids
        )

        segues = [
            segue.projection()
            for segue
            in graph.segues
            if segue.segue_id
            in segue_ids
        ]

        payload = {
            "schema": self.schema,
            "owner": self.owner,
            "authoritative": False,
            "authority_effect": "none",
            "source": (
                decomposition.projection()
            ),
            "instances": instances,
            "segues": segues,
            "graph_validation": (
                validation
            ),
            "rebuildable": True,
        }

        payload["digest"] = digest(
            payload
        )

        return payload

    def destination_for(
        self,
        decomposition: SourceDecomposition,
    ) -> Path:
        source_name = (
            Path(
                decomposition.source_path
            ).name
            or "source"
        )

        identity = (
            decomposition
            .script_instance_id
            .replace(
                ":",
                "_",
            )
        )

        return (
            self.root
            / f"{source_name}__{identity}.json"
        )

    def save(
        self,
        graph: ProgramCompositionGraph,
        decomposition: SourceDecomposition,
    ) -> dict[str, Any]:
        payload = self.snapshot(
            graph,
            decomposition,
        )

        destination = (
            self.destination_for(
                decomposition
            )
        )

        atomic_write_json(
            destination,
            payload,
        )

        confirmed = load_json(
            destination
        )

        if (
            confirmed.get(
                "digest"
            )
            != payload["digest"]
        ):
            raise ProgramStoreError(
                "stored snapshot digest "
                "verification failed"
            )

        return {
            "path": str(
                destination
            ),
            "bytes": (
                destination
                .stat()
                .st_size
            ),
            "digest": (
                payload["digest"]
            ),
            "source_digest": (
                decomposition
                .source_digest
            ),
            "script_instance_id": (
                decomposition
                .script_instance_id
            ),
            "atomic": True,
            "verified": True,
            "authoritative": False,
            "authority_effect": "none",
        }

    def load(
        self,
        path: Path,
    ) -> tuple[
        ProgramCompositionGraph,
        SourceDecomposition,
    ]:
        path = path.resolve()

        if not (
            path == ROOT
            or ROOT in path.parents
        ):
            raise ProgramStoreError(
                "program store path "
                "must remain inside Savant root"
            )

        payload = load_json(
            path
        )

        if (
            payload.get(
                "schema"
            )
            != self.schema
        ):
            raise ProgramStoreError(
                "unsupported program store schema"
            )

        if (
            payload.get(
                "authoritative"
            )
            is not False
        ):
            raise ProgramStoreError(
                "program runtime store "
                "must remain non-authoritative"
            )

        stored_digest = (
            payload.get(
                "digest"
            )
        )

        digest_material = dict(
            payload
        )

        digest_material.pop(
            "digest",
            None,
        )

        if (
            digest(
                digest_material
            )
            != stored_digest
        ):
            raise ProgramStoreError(
                "program store content "
                "digest mismatch"
            )

        graph = (
            ProgramCompositionGraph()
        )

        raw_instances = (
            payload.get(
                "instances",
                [],
            )
        )

        if not isinstance(
            raw_instances,
            list,
        ):
            raise ProgramStoreError(
                "instances must be a list"
            )

        for raw in raw_instances:
            if not isinstance(
                raw,
                dict,
            ):
                raise ProgramStoreError(
                    "instance projection "
                    "must be an object"
                )

            graph.add_instance(
                ProgramInstance(
                    instance_id=raw[
                        "instance_id"
                    ],
                    level=raw[
                        "level"
                    ],
                    children=tuple(
                        raw.get(
                            "children",
                            [],
                        )
                    ),
                    value=raw.get(
                        "value"
                    ),
                    terminator=raw.get(
                        "terminator",
                        "",
                    ),
                    owner=raw.get(
                        "owner",
                        "exile:modus",
                    ),
                    authority_state=(
                        raw.get(
                            "authority_state",
                            "provisional",
                        )
                    ),
                    authoritative=False,
                    lineage=tuple(
                        raw.get(
                            "lineage",
                            [],
                        )
                    ),
                    provenance=tuple(
                        raw.get(
                            "provenance",
                            [],
                        )
                    ),
                    dependencies=tuple(
                        raw.get(
                            "dependencies",
                            [],
                        )
                    ),
                    future_extensions=tuple(
                        raw.get(
                            "future_extensions",
                            [],
                        )
                    ),
                    metadata=dict(
                        raw.get(
                            "metadata",
                            {},
                        )
                    ),
                )
            )

        raw_segues = (
            payload.get(
                "segues",
                [],
            )
        )

        if not isinstance(
            raw_segues,
            list,
        ):
            raise ProgramStoreError(
                "segues must be a list"
            )

        for raw in raw_segues:
            if not isinstance(
                raw,
                dict,
            ):
                raise ProgramStoreError(
                    "segue projection "
                    "must be an object"
                )

            graph.add_segue(
                CodeSegue(
                    segue_id=raw[
                        "segue_id"
                    ],
                    source=raw[
                        "source"
                    ],
                    target=raw[
                        "target"
                    ],
                    segue_type=raw[
                        "type"
                    ],
                    owner=raw.get(
                        "owner",
                        "exile:modus",
                    ),
                    authority_state=(
                        raw.get(
                            "authority_state",
                            "provisional",
                        )
                    ),
                    authoritative=False,
                    contract=raw.get(
                        "contract"
                    ),
                    dependencies=tuple(
                        raw.get(
                            "dependencies",
                            [],
                        )
                    ),
                    lineage=tuple(
                        raw.get(
                            "lineage",
                            [],
                        )
                    ),
                    provenance=tuple(
                        raw.get(
                            "provenance",
                            [],
                        )
                    ),
                    metadata=dict(
                        raw.get(
                            "metadata",
                            {},
                        )
                    ),
                )
            )

        source = payload.get(
            "source"
        )

        if not isinstance(
            source,
            dict,
        ):
            raise ProgramStoreError(
                "source decomposition missing"
            )

        decomposition = (
            SourceDecomposition(
                source_path=source[
                    "source_path"
                ],
                source_digest=source[
                    "source_digest"
                ],
                script_instance_id=source[
                    "script_instance_id"
                ],
                line_ids=tuple(
                    source.get(
                        "line_ids",
                        [],
                    )
                ),
                segment_ids=tuple(
                    source.get(
                        "segment_ids",
                        [],
                    )
                ),
                snippet_ids=tuple(
                    source.get(
                        "snippet_ids",
                        [],
                    )
                ),
                segue_ids=tuple(
                    source.get(
                        "segue_ids",
                        [],
                    )
                ),
            )
        )

        validation = (
            graph.validate()
        )

        if validation["valid"] is not True:
            raise ProgramStoreError(
                "reloaded graph failed validation"
            )

        projected = (
            graph.project_text(
                decomposition
                .script_instance_id
            )
        )

        projected_digest = (
            digest_bytes(
                projected.encode(
                    "utf-8"
                )
            )
        )

        if (
            projected_digest
            != decomposition
            .source_digest
        ):
            raise ProgramStoreError(
                "reloaded projection "
                "does not reproduce "
                "source digest"
            )

        return (
            graph,
            decomposition,
        )

    def status(
        self,
    ) -> dict[str, Any]:
        payload = {
            "schema": self.schema,
            "owner": self.owner,
            "root": str(
                self.root
            ),
            "atomic_write": True,
            "content_digest": True,
            "reload_validation": True,
            "rebuild_validation": True,
            "authoritative": False,
            "authority_effect": "none",
        }

        payload["digest"] = digest(
            payload
        )

        return payload


def main() -> int:
    store = (
        ProgramCompositionStore()
    )

    print(
        json.dumps(
            store.status(),
            indent=2,
            sort_keys=True,
        )
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
