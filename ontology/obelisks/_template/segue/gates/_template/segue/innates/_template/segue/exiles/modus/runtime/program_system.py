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
    from .program_parent import (
        PARENT_LEVELS,
        ParentComposition,
        ProgramParentComposer,
        ProgramParentError,
    )
    from .program_subsystem import (
        SubsystemComposition,
    )
except ImportError:
    from program_composition import (
        ProgramCompositionError,
        ProgramCompositionGraph,
        digest,
    )
    from program_parent import (
        PARENT_LEVELS,
        ParentComposition,
        ProgramParentComposer,
        ProgramParentError,
    )
    from program_subsystem import (
        SubsystemComposition,
    )


SYSTEM_LEVEL = "system"

SYSTEM_CHILD_LEVEL = (
    PARENT_LEVELS[
        SYSTEM_LEVEL
    ]
)


class ProgramSystemError(
    ProgramCompositionError
):
    pass


@dataclass(
    frozen=True,
    slots=True,
)
class SystemComposition:
    system_instance_id: str
    subsystem_instance_ids: tuple[str, ...]
    segue_ids: tuple[str, ...]

    def projection(
        self,
    ) -> dict[str, Any]:
        payload = {
            "schema": (
                "savant://program/"
                "system-composition/1.1.0"
            ),
            "system_instance_id": (
                self.system_instance_id
            ),
            "subsystem_instance_ids": list(
                self.subsystem_instance_ids
            ),
            "segue_ids": list(
                self.segue_ids
            ),
            "level": (
                SYSTEM_LEVEL
            ),
            "child_level": (
                SYSTEM_CHILD_LEVEL
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


class ProgramSystemComposer:
    schema = (
        "savant://program/"
        "system-composer/1.1.0"
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
        subsystems: Iterable[
            SubsystemComposition
        ],
        *,
        system_name: str,
        lineage: Iterable[str] = (),
        provenance: Iterable[str] = (),
        dependencies: Iterable[str] = (),
    ) -> SystemComposition:
        values = tuple(
            subsystems
        )

        subsystem_ids = tuple(
            value.subsystem_instance_id
            for value
            in values
        )

        try:
            parent = self.parent.compose(
                level=SYSTEM_LEVEL,
                name=system_name,
                child_instance_ids=(
                    subsystem_ids
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
            raise ProgramSystemError(
                str(
                    exc
                )
            ) from exc

        return SystemComposition(
            system_instance_id=(
                parent.instance_id
            ),
            subsystem_instance_ids=(
                parent.child_instance_ids
            ),
            segue_ids=(
                parent.segue_ids
            ),
        )

    def _parent(
        self,
        composition: SystemComposition,
    ) -> ParentComposition:
        return ParentComposition(
            instance_id=(
                composition
                .system_instance_id
            ),
            level=(
                SYSTEM_LEVEL
            ),
            child_level=(
                SYSTEM_CHILD_LEVEL
            ),
            child_instance_ids=(
                composition
                .subsystem_instance_ids
            ),
            segue_ids=(
                composition
                .segue_ids
            ),
        )

    def manifest(
        self,
        composition: SystemComposition,
    ) -> dict[str, Any]:
        generic = self.parent.manifest(
            self._parent(
                composition
            )
        )

        payload = {
            "schema": (
                "savant://program/"
                "system-manifest/1.1.0"
            ),
            "system": (
                generic[
                    "parent"
                ]
            ),
            "composition": (
                composition.projection()
            ),
            "subsystems": (
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
                SYSTEM_CHILD_LEVEL
            ),
            "target_level": (
                SYSTEM_LEVEL
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
            ProgramSystemComposer(
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
