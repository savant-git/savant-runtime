#!/usr/bin/env python3

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Iterable

try:
    from .program_composition import (
        CodeSegue,
        ProgramCompositionError,
        ProgramCompositionGraph,
        ProgramInstance,
        content_id,
        digest,
    )
    from .program_hierarchy import (
        PROGRAM_CHILD_LEVEL,
        PROGRAM_LEVEL_INDEX,
        PROGRAM_LEVELS,
    )
except ImportError:
    from program_composition import (
        CodeSegue,
        ProgramCompositionError,
        ProgramCompositionGraph,
        ProgramInstance,
        content_id,
        digest,
    )
    from program_hierarchy import (
        PROGRAM_CHILD_LEVEL,
        PROGRAM_LEVEL_INDEX,
        PROGRAM_LEVELS,
    )


PARENT_LEVELS = {
    parent: PROGRAM_CHILD_LEVEL[
        parent
    ]
    for parent in PROGRAM_LEVELS[
        PROGRAM_LEVEL_INDEX[
            "engine"
        ]:
    ]
}


class ProgramParentError(
    ProgramCompositionError
):
    pass


@dataclass(
    frozen=True,
    slots=True,
)
class ParentComposition:
    instance_id: str
    level: str
    child_level: str
    child_instance_ids: tuple[str, ...]
    segue_ids: tuple[str, ...]

    def projection(
        self,
    ) -> dict[str, Any]:
        payload = {
            "schema": (
                "savant://program/"
                "parent-composition/1.1.0"
            ),
            "instance_id": (
                self.instance_id
            ),
            "level": self.level,
            "child_level": (
                self.child_level
            ),
            "child_instance_ids": list(
                self.child_instance_ids
            ),
            "segue_ids": list(
                self.segue_ids
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


class ProgramParentComposer:
    schema = (
        "savant://program/"
        "parent-composer/1.1.0"
    )

    owner = "exile:modus"

    def __init__(
        self,
        graph: ProgramCompositionGraph,
    ) -> None:
        self.graph = graph

    @staticmethod
    def child_level_for(
        level: str,
    ) -> str:
        normalized = str(
            level
        ).strip().lower()

        try:
            return PARENT_LEVELS[
                normalized
            ]
        except KeyError as exc:
            raise ProgramParentError(
                "unsupported parent level: "
                + normalized
            ) from exc

    def compose(
        self,
        *,
        level: str,
        name: str,
        child_instance_ids: Iterable[str],
        lineage: Iterable[str] = (),
        provenance: Iterable[str] = (),
        dependencies: Iterable[str] = (),
        metadata: dict[str, Any] | None = None,
    ) -> ParentComposition:
        parent_level = str(
            level
        ).strip().lower()

        child_level = (
            self.child_level_for(
                parent_level
            )
        )

        parent_name = str(
            name
        ).strip()

        if not parent_name:
            raise ProgramParentError(
                f"{parent_level}_name "
                "is required"
            )

        child_ids = tuple(
            str(value).strip()
            for value
            in child_instance_ids
            if str(value).strip()
        )

        if not child_ids:
            raise ProgramParentError(
                f"{parent_level} requires "
                f"at least one {child_level}"
            )

        if len(
            set(
                child_ids
            )
        ) != len(
            child_ids
        ):
            raise ProgramParentError(
                "duplicate child instance"
            )

        for child_id in child_ids:
            child = (
                self.graph.instance(
                    child_id
                )
            )

            if (
                child.level
                != child_level
            ):
                raise ProgramParentError(
                    f"{parent_level} children "
                    f"must be {child_level} "
                    "instances"
                )

        parent_id = content_id(
            parent_level,
            {
                "name": (
                    parent_name
                ),
                "children": (
                    child_ids
                ),
                "child_level": (
                    child_level
                ),
            },
        )

        parent_metadata = {
            "name": parent_name,
            "composition": (
                f"{child_level}-to-"
                f"{parent_level}"
            ),
            "hierarchy_source": (
                "PROGRAM_HIERARCHY_SEGUES"
            ),
        }

        if metadata:
            parent_metadata.update(
                metadata
            )

        parent = ProgramInstance(
            instance_id=parent_id,
            level=parent_level,
            children=child_ids,
            lineage=tuple(
                lineage
            ),
            provenance=(
                tuple(
                    provenance
                )
                + (
                    "deterministic-parent-composition",
                    "program-hierarchy-segue-projection",
                )
            ),
            dependencies=tuple(
                dependencies
            ),
            metadata=(
                parent_metadata
            ),
        )

        self.graph.add_instance(
            parent
        )

        segue_ids: list[str] = []

        for ordinal in range(
            len(
                child_ids
            ) - 1
        ):
            source = (
                child_ids[
                    ordinal
                ]
            )

            target = (
                child_ids[
                    ordinal + 1
                ]
            )

            segue_id = content_id(
                "segue",
                {
                    "source": source,
                    "target": target,
                    "type": (
                        "composition"
                    ),
                    "scope": parent_id,
                    "ordinal": (
                        ordinal + 1
                    ),
                },
            )

            segue = CodeSegue(
                segue_id=segue_id,
                source=source,
                target=target,
                segue_type=(
                    "composition"
                ),
                provenance=(
                    "deterministic-parent-composition",
                    "program-hierarchy-segue-projection",
                ),
                metadata={
                    "parent_instance_id": (
                        parent_id
                    ),
                    "parent_level": (
                        parent_level
                    ),
                    "child_level": (
                        child_level
                    ),
                    "ordinal": (
                        ordinal + 1
                    ),
                    "hierarchy_source": (
                        "PROGRAM_HIERARCHY_SEGUES"
                    ),
                },
            )

            self.graph.add_segue(
                segue
            )

            segue_ids.append(
                segue_id
            )

        validation = (
            self.graph.validate()
        )

        if (
            validation[
                "valid"
            ]
            is not True
        ):
            raise ProgramParentError(
                f"{parent_level} composition "
                "produced invalid graph"
            )

        return ParentComposition(
            instance_id=parent_id,
            level=parent_level,
            child_level=child_level,
            child_instance_ids=(
                child_ids
            ),
            segue_ids=tuple(
                segue_ids
            ),
        )

    def manifest(
        self,
        composition: ParentComposition,
    ) -> dict[str, Any]:
        parent = (
            self.graph.instance(
                composition.instance_id
            )
        )

        if (
            parent.level
            != composition.level
        ):
            raise ProgramParentError(
                "composition root "
                "level mismatch"
            )

        expected_child_level = (
            self.child_level_for(
                composition.level
            )
        )

        if (
            composition.child_level
            != expected_child_level
        ):
            raise ProgramParentError(
                "composition child level "
                "does not match hierarchy "
                "projection"
            )

        descendants = (
            self.graph.descendants(
                parent.instance_id
            )
        )

        payload = {
            "schema": (
                "savant://program/"
                "parent-manifest/1.1.0"
            ),
            "parent": (
                parent.projection()
            ),
            "composition": (
                composition.projection()
            ),
            "children": [
                self.graph.instance(
                    child_id
                ).projection()
                for child_id
                in composition
                .child_instance_ids
            ],
            "segues": [
                self.graph.segue(
                    segue_id
                ).projection()
                for segue_id
                in composition
                .segue_ids
            ],
            "descendant_count": len(
                descendants
            ),
            "descendants": list(
                descendants
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
            "levels": dict(
                PARENT_LEVELS
            ),
            "hierarchy_source": (
                "PROGRAM_HIERARCHY_SEGUES"
            ),
            "hierarchy_projection": True,
            "composition_only": True,
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
            ProgramParentComposer(
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
