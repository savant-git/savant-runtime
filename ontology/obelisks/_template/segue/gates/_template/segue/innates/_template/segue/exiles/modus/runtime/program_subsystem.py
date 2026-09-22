#!/usr/bin/env python3

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Iterable

try:
    from .program_composition import (
        ProgramCompositionError,
        ProgramCompositionGraph,
        digest,
    )
    from .program_engine import (
        EngineComposition,
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
        digest,
    )
    from program_engine import (
        EngineComposition,
    )
    from program_parent import (
        PARENT_LEVELS,
        ParentComposition,
        ProgramParentComposer,
        ProgramParentError,
    )


SUBSYSTEM_LEVEL = "subsystem"

SUBSYSTEM_CHILD_LEVEL = (
    PARENT_LEVELS[
        SUBSYSTEM_LEVEL
    ]
)


class ProgramSubsystemError(
    ProgramCompositionError
):
    pass


@dataclass(
    frozen=True,
    slots=True,
)
class SubsystemComposition:
    subsystem_instance_id: str
    engine_instance_ids: tuple[str, ...]
    segue_ids: tuple[str, ...]

    def projection(
        self,
    ) -> dict[str, Any]:
        payload = {
            "schema": (
                "savant://program/"
                "subsystem-composition/1.1.0"
            ),
            "subsystem_instance_id": (
                self.subsystem_instance_id
            ),
            "engine_instance_ids": list(
                self.engine_instance_ids
            ),
            "segue_ids": list(
                self.segue_ids
            ),
            "level": (
                SUBSYSTEM_LEVEL
            ),
            "child_level": (
                SUBSYSTEM_CHILD_LEVEL
            ),
            "edifice_source": (
                "PROGRAM_edifice_SEGUES"
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


class ProgramSubsystemComposer:
    schema = (
        "savant://program/"
        "subsystem-composer/1.1.0"
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
        engines: Iterable[
            EngineComposition
        ],
        *,
        subsystem_name: str,
        lineage: Iterable[str] = (),
        provenance: Iterable[str] = (),
        dependencies: Iterable[str] = (),
    ) -> SubsystemComposition:
        values = tuple(
            engines
        )

        engine_ids = tuple(
            value.engine_instance_id
            for value
            in values
        )

        try:
            parent = self.parent.compose(
                level=SUBSYSTEM_LEVEL,
                name=subsystem_name,
                child_instance_ids=(
                    engine_ids
                ),
                lineage=lineage,
                provenance=provenance,
                dependencies=dependencies,
                metadata={
                    "edifice_source": (
                        "PROGRAM_edifice_SEGUES"
                    ),
                },
            )
        except ProgramParentError as exc:
            raise ProgramSubsystemError(
                str(
                    exc
                )
            ) from exc

        return SubsystemComposition(
            subsystem_instance_id=(
                parent.instance_id
            ),
            engine_instance_ids=(
                parent.child_instance_ids
            ),
            segue_ids=(
                parent.segue_ids
            ),
        )

    def _parent(
        self,
        composition: SubsystemComposition,
    ) -> ParentComposition:
        return ParentComposition(
            instance_id=(
                composition
                .subsystem_instance_id
            ),
            level=(
                SUBSYSTEM_LEVEL
            ),
            child_level=(
                SUBSYSTEM_CHILD_LEVEL
            ),
            child_instance_ids=(
                composition
                .engine_instance_ids
            ),
            segue_ids=(
                composition
                .segue_ids
            ),
        )

    def manifest(
        self,
        composition: SubsystemComposition,
    ) -> dict[str, Any]:
        generic = self.parent.manifest(
            self._parent(
                composition
            )
        )

        payload = {
            "schema": (
                "savant://program/"
                "subsystem-manifest/1.1.0"
            ),
            "subsystem": (
                generic[
                    "parent"
                ]
            ),
            "composition": (
                composition.projection()
            ),
            "engines": (
                generic[
                    "children"
                ]
            ),
            "segues": (
                generic[
                    "segues"
                ]
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
            "edifice_source": (
                "PROGRAM_edifice_SEGUES"
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
                SUBSYSTEM_CHILD_LEVEL
            ),
            "target_level": (
                SUBSYSTEM_LEVEL
            ),
            "edifice_source": (
                "PROGRAM_edifice_SEGUES"
            ),
            "edifice_projection": True,
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
            ProgramSubsystemComposer(
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
