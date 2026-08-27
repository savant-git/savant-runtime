#!/usr/bin/env python3

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Iterable

try:
    from .program_composition import (
        ProgramCompositionError,
        ProgramCompositionGraph,
        SourceDecomposition,
        digest,
    )
    from .program_parent import (
        PARENT_LEVELS,
        ParentComposition,
        ProgramParentComposer,
        ProgramParentError,
    )
except ImportError:
    from program_composition import (
        ProgramCompositionError,
        ProgramCompositionGraph,
        SourceDecomposition,
        digest,
    )
    from program_parent import (
        PARENT_LEVELS,
        ParentComposition,
        ProgramParentComposer,
        ProgramParentError,
    )


ENGINE_LEVEL = "engine"
ENGINE_CHILD_LEVEL = (
    PARENT_LEVELS[
        ENGINE_LEVEL
    ]
)


class ProgramEngineError(
    ProgramCompositionError
):
    pass


@dataclass(
    frozen=True,
    slots=True,
)
class EngineComposition:
    engine_instance_id: str
    script_instance_ids: tuple[str, ...]
    source_paths: tuple[str, ...]
    segue_ids: tuple[str, ...]

    def projection(
        self,
    ) -> dict[str, Any]:
        payload = {
            "schema": (
                "savant://program/"
                "engine-composition/1.1.0"
            ),
            "engine_instance_id": (
                self.engine_instance_id
            ),
            "script_instance_ids": list(
                self.script_instance_ids
            ),
            "source_paths": list(
                self.source_paths
            ),
            "segue_ids": list(
                self.segue_ids
            ),
            "level": (
                ENGINE_LEVEL
            ),
            "child_level": (
                ENGINE_CHILD_LEVEL
            ),
            "hierarchy_source": (
                "PROGRAM_HIERARCHY_SEGUES"
            ),
            "owner": "exile:modus",
            "authoritative": False,
            "authority_effect": "none",
            "mutation_authorized": False,
            "rebuildable": True,
        }

        payload["digest"] = digest(
            payload
        )

        return payload


class ProgramEngineComposer:
    schema = (
        "savant://program/"
        "engine-composer/1.1.0"
    )

    owner = "exile:modus"

    def __init__(
        self,
        graph: ProgramCompositionGraph,
    ) -> None:
        self.graph = graph
        self.parent = (
            ProgramParentComposer(
                graph
            )
        )

    def compose(
        self,
        decompositions: Iterable[
            SourceDecomposition
        ],
        *,
        engine_name: str,
        lineage: Iterable[str] = (),
        provenance: Iterable[str] = (),
        dependencies: Iterable[str] = (),
    ) -> EngineComposition:
        values = tuple(
            decompositions
        )

        if not values:
            raise ProgramEngineError(
                "engine requires at least "
                "one script"
            )

        script_ids: list[str] = []
        source_paths: list[str] = []

        for decomposition in values:
            script = (
                self.graph.instance(
                    decomposition
                    .script_instance_id
                )
            )

            if (
                script.level
                != ENGINE_CHILD_LEVEL
            ):
                raise ProgramEngineError(
                    f"{ENGINE_LEVEL} children "
                    f"must be "
                    f"{ENGINE_CHILD_LEVEL} "
                    "instances"
                )

            projected = (
                self.graph.project_text(
                    script.instance_id
                )
            )

            projected_digest = (
                hashlib.sha256(
                    projected.encode(
                        "utf-8"
                    )
                ).hexdigest()
            )

            if (
                projected_digest
                != decomposition
                .source_digest
            ):
                raise ProgramEngineError(
                    "script projection digest "
                    "does not match "
                    "decomposition"
                )

            script_ids.append(
                script.instance_id
            )

            source_paths.append(
                decomposition
                .source_path
            )

        try:
            parent = (
                self.parent.compose(
                    level=ENGINE_LEVEL,
                    name=engine_name,
                    child_instance_ids=(
                        script_ids
                    ),
                    lineage=lineage,
                    provenance=provenance,
                    dependencies=(
                        dependencies
                    ),
                    metadata={
                        "source_paths": (
                            source_paths
                        ),
                        "hierarchy_source": (
                            "PROGRAM_HIERARCHY_SEGUES"
                        ),
                    },
                )
            )
        except ProgramParentError as exc:
            raise ProgramEngineError(
                str(
                    exc
                )
            ) from exc

        return EngineComposition(
            engine_instance_id=(
                parent.instance_id
            ),
            script_instance_ids=(
                parent
                .child_instance_ids
            ),
            source_paths=tuple(
                source_paths
            ),
            segue_ids=(
                parent.segue_ids
            ),
        )

    def _parent(
        self,
        composition: EngineComposition,
    ) -> ParentComposition:
        return ParentComposition(
            instance_id=(
                composition
                .engine_instance_id
            ),
            level=ENGINE_LEVEL,
            child_level=(
                ENGINE_CHILD_LEVEL
            ),
            child_instance_ids=(
                composition
                .script_instance_ids
            ),
            segue_ids=(
                composition
                .segue_ids
            ),
        )

    def manifest(
        self,
        composition: EngineComposition,
    ) -> dict[str, Any]:
        generic = (
            self.parent.manifest(
                self._parent(
                    composition
                )
            )
        )

        payload = {
            "schema": (
                "savant://program/"
                "engine-manifest/1.1.0"
            ),
            "engine": (
                generic[
                    "parent"
                ]
            ),
            "composition": (
                composition.projection()
            ),
            "descendant_count": (
                generic[
                    "descendant_count"
                ]
            ),
            "descendants": (
                generic[
                    "descendants"
                ]
            ),
            "scripts": (
                generic[
                    "children"
                ]
            ),
            "segues": (
                generic[
                    "segues"
                ]
            ),
            "hierarchy_source": (
                "PROGRAM_HIERARCHY_SEGUES"
            ),
            "owner": self.owner,
            "authoritative": False,
            "authority_effect": "none",
            "mutation_authorized": False,
            "rebuildable": True,
        }

        payload["digest"] = digest(
            payload
        )

        return payload

    def status(
        self,
    ) -> dict[str, Any]:
        payload = {
            "schema": self.schema,
            "owner": self.owner,
            "source_level": (
                ENGINE_CHILD_LEVEL
            ),
            "target_level": (
                ENGINE_LEVEL
            ),
            "hierarchy_source": (
                "PROGRAM_HIERARCHY_SEGUES"
            ),
            "hierarchy_projection": True,
            "composition_only": True,
            "parent_primitive": (
                "ProgramParentComposer"
            ),
            "authoritative": False,
            "authority_effect": "none",
            "mutation_authorized": False,
        }

        payload["digest"] = digest(
            payload
        )

        return payload


def main() -> int:
    print(
        json.dumps(
            ProgramEngineComposer(
                ProgramCompositionGraph()
            ).status(),
            indent=2,
            sort_keys=True,
        )
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
