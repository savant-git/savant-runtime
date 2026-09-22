#!/usr/bin/env python3

from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

from .model import (
    StraubValidationError,
    content_digest,
)


schema = "savant.straub.dependency.v1"
owner = "savant"
authority_effect = "none"


class StraubDependencyIndex:
    def __init__(
        self,
        capsule: Mapping[str, Any],
    ) -> None:
        if not isinstance(
            capsule,
            Mapping,
        ):
            raise StraubValidationError(
                "dependency index requires "
                "straub capsule"
            )

        if (
            capsule.get(
                "schema"
            )
            != "savant.straub.capsule.v2"
        ):
            raise StraubValidationError(
                "dependency index requires "
                "capsule v2"
            )

        instances = capsule.get(
            "instances"
        )

        membranes = capsule.get(
            "membranes"
        )

        if not isinstance(
            instances,
            list,
        ):
            raise StraubValidationError(
                "capsule instances invalid"
            )

        if not isinstance(
            membranes,
            list,
        ):
            raise StraubValidationError(
                "capsule membranes invalid"
            )

        self._dependencies: dict[
            str,
            set[str],
        ] = {}

        self._kinds: dict[
            str,
            str,
        ] = {}

        for raw in instances:
            if not isinstance(
                raw,
                Mapping,
            ):
                raise StraubValidationError(
                    "capsule instance invalid"
                )

            record_id = str(
                raw.get(
                    "id"
                )
                or ""
            ).strip()

            if not record_id:
                raise StraubValidationError(
                    "instance id missing"
                )

            self._kinds[
                record_id
            ] = str(
                raw.get(
                    "kind"
                )
                or "instance"
            )

            self._dependencies[
                record_id
            ] = {
                str(
                    value
                ).strip()
                for value
                in (
                    raw.get(
                        "dependencies"
                    )
                    or []
                )
                if str(
                    value
                ).strip()
            }

        for raw in membranes:
            if not isinstance(
                raw,
                Mapping,
            ):
                raise StraubValidationError(
                    "capsule membrane invalid"
                )

            membrane_id = str(
                raw.get(
                    "id"
                )
                or ""
            ).strip()

            if not membrane_id:
                raise StraubValidationError(
                    "membrane id missing"
                )

            dependencies = {
                str(
                    value
                ).strip()
                for value
                in (
                    raw.get(
                        "dependencies"
                    )
                    or []
                )
                if str(
                    value
                ).strip()
            }

            source = str(
                raw.get(
                    "from"
                )
                or ""
            ).strip()

            target = str(
                raw.get(
                    "to"
                )
                or ""
            ).strip()

            if source:
                dependencies.add(
                    source
                )

            if target:
                dependencies.add(
                    target
                )

            self._kinds[
                membrane_id
            ] = "membrane"

            self._dependencies[
                membrane_id
            ] = dependencies

        self._dependents: dict[
            str,
            set[str],
        ] = {}

        for (
            record_id,
            dependencies,
        ) in self._dependencies.items():
            for dependency_id in dependencies:
                self._dependents.setdefault(
                    dependency_id,
                    set(),
                ).add(
                    record_id
                )

    def graph(
        self,
    ) -> dict[str, Any]:
        all_known_ids = set(
            self._dependencies
        )

        unresolved: set[str] = set()

        nodes: list[
            dict[str, Any]
        ] = []

        for record_id in sorted(
            self._dependencies
        ):
            dependencies = sorted(
                self._dependencies[
                    record_id
                ]
            )

            dependents = sorted(
                self._dependents.get(
                    record_id,
                    set(),
                )
            )

            for dependency_id in dependencies:
                if (
                    dependency_id
                    not in all_known_ids
                ):
                    unresolved.add(
                        dependency_id
                    )

            nodes.append(
                {
                    "id":
                        record_id,
                    "kind":
                        self._kinds.get(
                            record_id,
                            "unknown",
                        ),
                    "dependencies":
                        dependencies,
                    "dependents":
                        dependents,
                }
            )

        projection = {
            "schema":
                "savant.straub."
                "dependency-isotope.v1",
            "kind":
                "isotope",
            "node_count":
                len(
                    nodes
                ),
            "nodes":
                nodes,
            "unresolved_dependencies":
                sorted(
                    unresolved
                ),
            "projection_only":
                True,
            "authority_effect":
                "none",
        }

        projection[
            "digest"
        ] = content_digest(
            projection
        )

        return projection

    def invalidation(
        self,
        changed_ids: list[str],
    ) -> dict[str, Any]:
        roots = sorted(
            {
                str(
                    value
                ).strip()
                for value
                in changed_ids
                if str(
                    value
                ).strip()
            }
        )

        if not roots:
            raise StraubValidationError(
                "invalidation requires "
                "at least one changed id"
            )

        affected: set[str] = set()
        frontier = list(
            roots
        )

        traversed: set[str] = set(
            roots
        )

        while frontier:
            current = frontier.pop(
                0
            )

            for dependent in sorted(
                self._dependents.get(
                    current,
                    set(),
                )
            ):
                affected.add(
                    dependent
                )

                if dependent not in traversed:
                    traversed.add(
                        dependent
                    )

                    frontier.append(
                        dependent
                    )

        affected.difference_update(
            roots
        )

        projection = {
            "schema":
                "savant.straub."
                "invalidation-isotope.v1",
            "kind":
                "isotope",
            "changed":
                roots,
            "affected":
                sorted(
                    affected
                ),
            "affected_count":
                len(
                    affected
                ),
            "mutation_performed":
                False,
            "projection_only":
                True,
            "authority_effect":
                "none",
        }

        projection[
            "digest"
        ] = content_digest(
            projection
        )

        return projection

    def dependencies_of(
        self,
        record_id: str,
    ) -> dict[str, Any]:
        dependencies = sorted(
            self._dependencies.get(
                record_id,
                set(),
            )
        )

        dependents = sorted(
            self._dependents.get(
                record_id,
                set(),
            )
        )

        projection = {
            "schema":
                "savant.straub."
                "dependency-node-isotope.v1",
            "kind":
                "isotope",
            "id":
                record_id,
            "record_kind":
                self._kinds.get(
                    record_id
                ),
            "dependencies":
                deepcopy(
                    dependencies
                ),
            "dependents":
                deepcopy(
                    dependents
                ),
            "projection_only":
                True,
            "authority_effect":
                "none",
        }

        projection[
            "digest"
        ] = content_digest(
            projection
        )

        return projection

