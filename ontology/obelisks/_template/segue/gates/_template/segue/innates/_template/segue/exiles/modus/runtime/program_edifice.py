#!/usr/bin/env python3

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Iterator


class ProgramedificeError(
    ValueError
):
    pass


def canonical_json(
    value: Any,
) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )


def digest(
    value: Any,
) -> str:
    return hashlib.sha256(
        canonical_json(
            value
        ).encode(
            "utf-8"
        )
    ).hexdigest()


@dataclass(
    frozen=True,
    slots=True,
)
class ProgramedificeSegue:
    segue_id: str
    parent_instance: str
    child_instance: str
    ordinal: int
    functional_role: str = "composition"
    semantic_axis: str = "program-edifice"
    inheritance_policy: str = "none"
    propagation_policy: str = "composition-only"
    authority_state: str = "accepted"
    authority_source: str = (
        "current-user-directive:"
        "program-composition-edifice"
    )
    provenance: tuple[str, ...] = (
        "current-user-directive:"
        "program-composition-edifice",
        "canon:FOUNDATION-008",
    )
    valid: bool = True
    extensions: tuple[
        tuple[str, str],
        ...,
    ] = ()
    owner: str = "exile:modus"

    def __post_init__(
        self,
    ) -> None:
        if not self.segue_id.strip():
            raise ProgramedificeError(
                "segue_id is required"
            )

        if not self.parent_instance.strip():
            raise ProgramedificeError(
                "parent_instance is required"
            )

        if not self.child_instance.strip():
            raise ProgramedificeError(
                "child_instance is required"
            )

        if (
            self.parent_instance
            == self.child_instance
        ):
            raise ProgramedificeError(
                "lineage segue cannot "
                "self-reference"
            )

        if self.ordinal < 1:
            raise ProgramedificeError(
                "lineage segue ordinal "
                "must be positive"
            )

        if (
            self.functional_role
            != "composition"
        ):
            raise ProgramedificeError(
                "program edifice lineage "
                "must use composition role"
            )

        if (
            self.semantic_axis
            != "program-edifice"
        ):
            raise ProgramedificeError(
                "program edifice semantic "
                "axis mismatch"
            )

        if (
            self.authority_state
            != "accepted"
        ):
            raise ProgramedificeError(
                "program edifice segue "
                "must be accepted"
            )

        if self.valid is not True:
            raise ProgramedificeError(
                "program edifice segue "
                "must be valid"
            )

        if not self.provenance:
            raise ProgramedificeError(
                "program edifice segue "
                "requires provenance"
            )

    @property
    def parent_level(
        self,
    ) -> str:
        return self.parent_instance

    @property
    def child_level(
        self,
    ) -> str:
        return self.child_instance

    @property
    def source_level(
        self,
    ) -> str:
        """
        Compatibility projection.

        Existing composition callers traverse
        upward from child to parent.
        """
        return self.child_instance

    @property
    def target_level(
        self,
    ) -> str:
        """
        Compatibility projection.

        Existing composition callers traverse
        upward from child to parent.
        """
        return self.parent_instance

    @property
    def segue_type(
        self,
    ) -> str:
        return self.functional_role

    def projection(
        self,
    ) -> dict[str, Any]:
        payload = {
            "schema": (
                "savant://program/"
                "edifice-segue/1.2.0"
            ),
            "segue_id": (
                self.segue_id
            ),
            "parent_instance": (
                self.parent_instance
            ),
            "child_instance": (
                self.child_instance
            ),
            "functional_role": (
                self.functional_role
            ),
            "semantic_axis": (
                self.semantic_axis
            ),
            "inheritance_policy": (
                self.inheritance_policy
            ),
            "propagation_policy": (
                self.propagation_policy
            ),
            "authority": {
                "state": (
                    self.authority_state
                ),
                "source": (
                    self.authority_source
                ),
            },
            "provenance": list(
                self.provenance
            ),
            "valid": self.valid,
            "extensions": {
                key: value
                for key, value
                in self.extensions
            },
            "ordinal": (
                self.ordinal
            ),
            "owner": self.owner,
            "authoritative": True,
            "authority_effect": (
                "edifice-definition"
            ),
            "mutation_authorized": False,
            "source_level": (
                self.source_level
            ),
            "target_level": (
                self.target_level
            ),
            "type": (
                self.segue_type
            ),
            "compatibility_projection": {
                "source_level": (
                    "child_instance"
                ),
                "target_level": (
                    "parent_instance"
                ),
            },
        }

        payload["digest"] = digest(
            payload
        )

        return payload


def make_program_edifice_segue(
    *,
    parent_instance: str,
    child_instance: str,
    ordinal: int,
) -> ProgramedificeSegue:
    material = {
        "parent_instance": (
            parent_instance
        ),
        "child_instance": (
            child_instance
        ),
        "functional_role": (
            "composition"
        ),
        "semantic_axis": (
            "program-edifice"
        ),
        "inheritance_policy": (
            "none"
        ),
        "propagation_policy": (
            "composition-only"
        ),
    }

    return ProgramedificeSegue(
        segue_id=(
            "program-edifice-segue:"
            + digest(
                material
            )[:24]
        ),
        parent_instance=(
            parent_instance
        ),
        child_instance=(
            child_instance
        ),
        ordinal=ordinal,
    )


PROGRAM_edifice_SEGUES = (
    make_program_edifice_segue(
        parent_instance="line",
        child_instance="character",
        ordinal=1,
    ),
    make_program_edifice_segue(
        parent_instance="segment",
        child_instance="line",
        ordinal=2,
    ),
    make_program_edifice_segue(
        parent_instance="snippet",
        child_instance="segment",
        ordinal=3,
    ),
    make_program_edifice_segue(
        parent_instance="script",
        child_instance="snippet",
        ordinal=4,
    ),
    make_program_edifice_segue(
        parent_instance="engine",
        child_instance="script",
        ordinal=5,
    ),
    make_program_edifice_segue(
        parent_instance="subsystem",
        child_instance="engine",
        ordinal=6,
    ),
    make_program_edifice_segue(
        parent_instance="system",
        child_instance="subsystem",
        ordinal=7,
    ),
    make_program_edifice_segue(
        parent_instance="application",
        child_instance="system",
        ordinal=8,
    ),
)


def project_program_lineage(
    segues: tuple[
        ProgramedificeSegue,
        ...,
    ],
) -> tuple[
    tuple[str, str],
    ...,
]:
    return tuple(
        (
            segue.parent_instance,
            segue.child_instance,
        )
        for segue
        in segues
    )


PROGRAM_edifice_LINEAGE = (
    project_program_lineage(
        PROGRAM_edifice_SEGUES
    )
)


def project_program_levels(
    segues: tuple[
        ProgramedificeSegue,
        ...,
    ],
) -> tuple[str, ...]:
    if not segues:
        raise ProgramedificeError(
            "program edifice segues "
            "cannot be empty"
        )

    parents = {
        segue.parent_instance
        for segue
        in segues
    }

    children = {
        segue.child_instance
        for segue
        in segues
    }

    atomic_roots = (
        children - parents
    )

    aggregate_terminals = (
        parents - children
    )

    if len(
        atomic_roots
    ) != 1:
        raise ProgramedificeError(
            "program edifice must "
            "have exactly one "
            "atomic root"
        )

    if len(
        aggregate_terminals
    ) != 1:
        raise ProgramedificeError(
            "program edifice must "
            "have exactly one "
            "aggregate terminal"
        )

    parent_by_child: dict[
        str,
        str,
    ] = {}

    for segue in segues:
        child = (
            segue.child_instance
        )

        parent = (
            segue.parent_instance
        )

        if child in parent_by_child:
            raise ProgramedificeError(
                "program edifice child "
                "has multiple composition "
                "parents: "
                + child
            )

        parent_by_child[
            child
        ] = parent

    current = next(
        iter(
            atomic_roots
        )
    )

    result = [
        current
    ]

    visited = {
        current
    }

    while (
        current
        in parent_by_child
    ):
        current = (
            parent_by_child[
                current
            ]
        )

        if current in visited:
            raise ProgramedificeError(
                "program edifice cycle "
                "detected"
            )

        result.append(
            current
        )

        visited.add(
            current
        )

    expected_nodes = (
        parents | children
    )

    if visited != expected_nodes:
        raise ProgramedificeError(
            "program edifice is "
            "disconnected"
        )

    return tuple(
        result
    )


PROGRAM_LEVELS = (
    project_program_levels(
        PROGRAM_edifice_SEGUES
    )
)

PROGRAM_LEVEL_INDEX = {
    level: index
    for index, level
    in enumerate(
        PROGRAM_LEVELS
    )
}

PROGRAM_CHILD_LEVEL = {
    segue.parent_instance: (
        segue.child_instance
    )
    for segue
    in PROGRAM_edifice_SEGUES
}

PROGRAM_PARENT_LEVEL = {
    segue.child_instance: (
        segue.parent_instance
    )
    for segue
    in PROGRAM_edifice_SEGUES
}


@dataclass(
    frozen=True,
    slots=True,
)
class ProgramLevel:
    name: str
    ordinal: int
    child: str | None
    parent: str | None

    def projection(
        self,
    ) -> dict[str, Any]:
        return {
            "name": self.name,
            "ordinal": (
                self.ordinal
            ),
            "child": self.child,
            "parent": self.parent,
            "authoritative": False,
            "authority_effect": "none",
            "derived_from": (
                "PROGRAM_edifice_SEGUES"
            ),
        }


class Programedifice:
    schema = (
        "savant://program/"
        "edifice/1.3.0"
    )

    owner = "exile:modus"

    def __iter__(
        self,
    ) -> Iterator[
        ProgramLevel
    ]:
        for name in PROGRAM_LEVELS:
            yield self.level(
                name
            )

    @staticmethod
    def normalize(
        level: str,
    ) -> str:
        value = str(
            level
        ).strip().lower()

        if (
            value
            not in PROGRAM_LEVEL_INDEX
        ):
            raise ProgramedificeError(
                "unknown program level: "
                + value
            )

        return value

    def level(
        self,
        level: str,
    ) -> ProgramLevel:
        name = self.normalize(
            level
        )

        return ProgramLevel(
            name=name,
            ordinal=(
                PROGRAM_LEVEL_INDEX[
                    name
                ]
            ),
            child=(
                PROGRAM_CHILD_LEVEL
                .get(
                    name
                )
            ),
            parent=(
                PROGRAM_PARENT_LEVEL
                .get(
                    name
                )
            ),
        )

    def child_of(
        self,
        parent: str,
    ) -> str | None:
        name = self.normalize(
            parent
        )

        return (
            PROGRAM_CHILD_LEVEL
            .get(
                name
            )
        )

    def parent_of(
        self,
        child: str,
    ) -> str | None:
        name = self.normalize(
            child
        )

        return (
            PROGRAM_PARENT_LEVEL
            .get(
                name
            )
        )

    def adjacent(
        self,
        child: str,
        parent: str,
    ) -> bool:
        child_name = (
            self.normalize(
                child
            )
        )

        parent_name = (
            self.normalize(
                parent
            )
        )

        return (
            PROGRAM_PARENT_LEVEL
            .get(
                child_name
            )
            == parent_name
        )

    def distance(
        self,
        source: str,
        target: str,
    ) -> int:
        source_name = (
            self.normalize(
                source
            )
        )

        target_name = (
            self.normalize(
                target
            )
        )

        return (
            PROGRAM_LEVEL_INDEX[
                target_name
            ]
            - PROGRAM_LEVEL_INDEX[
                source_name
            ]
        )

    def path(
        self,
        source: str,
        target: str,
    ) -> tuple[str, ...]:
        source_name = (
            self.normalize(
                source
            )
        )

        target_name = (
            self.normalize(
                target
            )
        )

        start = (
            PROGRAM_LEVEL_INDEX[
                source_name
            ]
        )

        end = (
            PROGRAM_LEVEL_INDEX[
                target_name
            ]
        )

        step = (
            1
            if end >= start
            else -1
        )

        return tuple(
            PROGRAM_LEVELS[
                index
            ]
            for index in range(
                start,
                end + step,
                step,
            )
        )

    def segue(
        self,
        source_level: str,
        target_level: str,
    ) -> ProgramedificeSegue:
        source = (
            self.normalize(
                source_level
            )
        )

        target = (
            self.normalize(
                target_level
            )
        )

        if not self.adjacent(
            source,
            target,
        ):
            raise ProgramedificeError(
                "program edifice segue "
                "requires adjacent levels: "
                f"{source} -> {target}"
            )

        for segue in (
            PROGRAM_edifice_SEGUES
        ):
            if (
                segue.child_instance
                == source
                and segue.parent_instance
                == target
            ):
                return segue

        raise ProgramedificeError(
            "authoritative edifice "
            "segue missing: "
            f"{source} -> {target}"
        )

    def segues(
        self,
    ) -> tuple[
        ProgramedificeSegue,
        ...,
    ]:
        return (
            PROGRAM_edifice_SEGUES
        )

    def segue_path(
        self,
        source: str,
        target: str,
    ) -> tuple[
        ProgramedificeSegue,
        ...,
    ]:
        levels = self.path(
            source,
            target,
        )

        if len(levels) <= 1:
            return ()

        if (
            self.distance(
                source,
                target,
            )
            < 0
        ):
            raise ProgramedificeError(
                "edifice segue path "
                "projects upward only"
            )

        return tuple(
            self.segue(
                child,
                parent,
            )
            for child, parent
            in zip(
                levels,
                levels[1:],
            )
        )

    def validate(
        self,
    ) -> dict[str, Any]:
        errors: list[str] = []

        expected_levels = (
            "character",
            "line",
            "segment",
            "snippet",
            "script",
            "engine",
            "subsystem",
            "system",
            "application",
        )

        if (
            len(
                PROGRAM_edifice_SEGUES
            )
            != 8
        ):
            errors.append(
                "program edifice must "
                "contain 8 authoritative "
                "lineage segues"
            )

        if (
            PROGRAM_LEVELS
            != expected_levels
        ):
            errors.append(
                "program edifice level "
                "projection mismatch"
            )

        if (
            len(
                PROGRAM_LEVELS
            )
            != 9
        ):
            errors.append(
                "program edifice must "
                "project 9 levels"
            )

        if (
            PROGRAM_edifice_LINEAGE
            != project_program_lineage(
                PROGRAM_edifice_SEGUES
            )
        ):
            errors.append(
                "lineage compatibility "
                "projection mismatch"
            )

        if (
            PROGRAM_LEVELS
            != project_program_levels(
                PROGRAM_edifice_SEGUES
            )
        ):
            errors.append(
                "level projection is not "
                "deterministic"
            )

        segue_ids = {
            segue.segue_id
            for segue
            in PROGRAM_edifice_SEGUES
        }

        if len(
            segue_ids
        ) != 8:
            errors.append(
                "program edifice segue "
                "identities must be unique"
            )

        for index, segue in (
            enumerate(
                PROGRAM_edifice_SEGUES,
                start=1,
            )
        ):
            if (
                segue.ordinal
                != index
            ):
                errors.append(
                    "program edifice "
                    "segue ordinal mismatch: "
                    + segue.segue_id
                )

            if (
                segue.valid
                is not True
            ):
                errors.append(
                    "invalid program "
                    "edifice segue: "
                    + segue.segue_id
                )

            if (
                segue.authority_state
                != "accepted"
            ):
                errors.append(
                    "non-accepted program "
                    "edifice segue: "
                    + segue.segue_id
                )

            if (
                segue.functional_role
                != "composition"
            ):
                errors.append(
                    "program edifice "
                    "functional role "
                    "mismatch: "
                    + segue.segue_id
                )

            if (
                segue.semantic_axis
                != "program-edifice"
            ):
                errors.append(
                    "program edifice "
                    "semantic axis mismatch: "
                    + segue.segue_id
                )

            if not segue.provenance:
                errors.append(
                    "program edifice "
                    "segue provenance "
                    "missing: "
                    + segue.segue_id
                )

        return {
            "valid": (
                not errors
            ),
            "errors": errors,
            "level_count": len(
                PROGRAM_LEVELS
            ),
            "transition_count": len(
                PROGRAM_edifice_SEGUES
            ),
            "segue_count": len(
                PROGRAM_edifice_SEGUES
            ),
            "authority_primitive": (
                "PROGRAM_edifice_SEGUES"
            ),
            "authoritative_segue_count": (
                len(
                    PROGRAM_edifice_SEGUES
                )
            ),
            "lineage_tuple_is_projection": (
                True
            ),
            "levels_are_projection": (
                True
            ),
            "indexes_are_projection": (
                True
            ),
            "parent_child_maps_are_projection": (
                True
            ),
        }

    def projection(
        self,
    ) -> dict[str, Any]:
        validation = (
            self.validate()
        )

        payload = {
            "schema": self.schema,
            "owner": self.owner,
            "authoritative": False,
            "authority_effect": "none",
            "mutation_authorized": False,
            "rebuildable": True,
            "authority_primitive": (
                validation[
                    "authority_primitive"
                ]
            ),
            "levels": [
                level.projection()
                for level in self
            ],
            "segues": [
                segue.projection()
                for segue
                in self.segues()
            ],
            "level_count": (
                validation[
                    "level_count"
                ]
            ),
            "transition_count": (
                validation[
                    "transition_count"
                ]
            ),
            "segue_count": (
                validation[
                    "segue_count"
                ]
            ),
            "lineage_tuple_is_projection": (
                True
            ),
            "levels_are_projection": (
                True
            ),
            "indexes_are_projection": (
                True
            ),
            "parent_child_maps_are_projection": (
                True
            ),
            "valid": (
                validation[
                    "valid"
                ]
            ),
            "errors": (
                validation[
                    "errors"
                ]
            ),
        }

        payload["digest"] = digest(
            payload
        )

        return payload


def main() -> int:
    edifice = (
        Programedifice()
    )

    projection = (
        edifice.projection()
    )

    print(
        json.dumps(
            projection,
            indent=2,
            sort_keys=True,
        )
    )

    return (
        0
        if projection["valid"]
        else 1
    )


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
