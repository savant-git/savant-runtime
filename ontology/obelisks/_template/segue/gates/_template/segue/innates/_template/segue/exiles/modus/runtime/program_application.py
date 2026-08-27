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
    from .program_system import (
        SystemComposition,
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
    from program_system import (
        SystemComposition,
    )


APPLICATION_LEVEL = "application"

APPLICATION_CHILD_LEVEL = (
    PARENT_LEVELS[
        APPLICATION_LEVEL
    ]
)


class ProgramApplicationError(
    ProgramCompositionError
):
    pass


@dataclass(
    frozen=True,
    slots=True,
)
class ApplicationComposition:
    application_instance_id: str
    system_instance_ids: tuple[str, ...]
    segue_ids: tuple[str, ...]

    def projection(
        self,
    ) -> dict[str, Any]:
        payload = {
            "schema": (
                "savant://program/"
                "application-composition/1.1.0"
            ),
            "application_instance_id": (
                self.application_instance_id
            ),
            "system_instance_ids": list(
                self.system_instance_ids
            ),
            "segue_ids": list(
                self.segue_ids
            ),
            "level": (
                APPLICATION_LEVEL
            ),
            "child_level": (
                APPLICATION_CHILD_LEVEL
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


class ProgramApplicationComposer:
    schema = (
        "savant://program/"
        "application-composer/1.1.0"
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
        systems: Iterable[
            SystemComposition
        ],
        *,
        application_name: str,
        lineage: Iterable[str] = (),
        provenance: Iterable[str] = (),
        dependencies: Iterable[str] = (),
    ) -> ApplicationComposition:
        values = tuple(
            systems
        )

        system_ids = tuple(
            value.system_instance_id
            for value
            in values
        )

        try:
            parent = self.parent.compose(
                level=APPLICATION_LEVEL,
                name=application_name,
                child_instance_ids=(
                    system_ids
                ),
                lineage=lineage,
                provenance=provenance,
                dependencies=dependencies,
                metadata={
                    "hierarchy_source": (
                        "PROGRAM_HIERARCHY_SEGUES"
                    ),
                },
            )
        except ProgramParentError as exc:
            raise ProgramApplicationError(
                str(
                    exc
                )
            ) from exc

        return ApplicationComposition(
            application_instance_id=(
                parent.instance_id
            ),
            system_instance_ids=(
                parent.child_instance_ids
            ),
            segue_ids=(
                parent.segue_ids
            ),
        )

    def _parent(
        self,
        composition: ApplicationComposition,
    ) -> ParentComposition:
        return ParentComposition(
            instance_id=(
                composition
                .application_instance_id
            ),
            level=(
                APPLICATION_LEVEL
            ),
            child_level=(
                APPLICATION_CHILD_LEVEL
            ),
            child_instance_ids=(
                composition
                .system_instance_ids
            ),
            segue_ids=(
                composition
                .segue_ids
            ),
        )

    def manifest(
        self,
        composition: ApplicationComposition,
    ) -> dict[str, Any]:
        generic = self.parent.manifest(
            self._parent(
                composition
            )
        )

        payload = {
            "schema": (
                "savant://program/"
                "application-manifest/1.1.0"
            ),
            "application": (
                generic[
                    "parent"
                ]
            ),
            "composition": (
                composition.projection()
            ),
            "systems": (
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
                APPLICATION_CHILD_LEVEL
            ),
            "target_level": (
                APPLICATION_LEVEL
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
            ProgramApplicationComposer(
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
