#!/usr/bin/env python3

from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import dataclass
from typing import Any, Iterable

from capability_compiler import (
    AlloyPlan,
    CapabilityCompiler,
    CapabilityCompilerError,
    compiler,
)
from sliver_pool import (
    SliverPool,
    build_pool,
)


OWNER = "prodigal:modus:coalesce"

ALLOY_SCHEMA = (
    "savant://coalesce/alloy/1"
)

COMPOSITION_GRAPH_SCHEMA = (
    "savant://coalesce/"
    "composition-graph/1"
)

MAX_SLIVERS = 9


class AlloyAssemblerError(
    RuntimeError
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


def normalized_id(
    value: Any,
) -> str:
    return str(
        value
        or ""
    ).strip()


@dataclass(
    frozen=True,
    slots=True,
)
class SegueBinding:
    source: str
    target: str
    segue_type: str

    def projection(
        self,
    ) -> dict[str, str]:
        return {
            "source": self.source,
            "target": self.target,
            "type": self.segue_type,
        }


class AlloyAssembler:
    def __init__(
        self,
        *,
        pool: SliverPool | None = None,
        capability_compiler: (
            CapabilityCompiler
            | None
        ) = None,
    ) -> None:
        self.pool = (
            pool
            or build_pool()
        )

        self.compiler = (
            capability_compiler
            or compiler()
        )

    def _validate_plan(
        self,
        plan: AlloyPlan,
    ) -> None:
        count = len(
            plan.sliver_ids
        )

        if (
            count < 1
            or count > MAX_SLIVERS
        ):
            raise AlloyAssemblerError(
                "Alloy must contain "
                "between 1 and 9 Slivers"
            )

        if (
            len(
                set(
                    plan.sliver_ids
                )
            )
            != count
        ):
            raise AlloyAssemblerError(
                "duplicate Sliver "
                "instances are not allowed"
            )

        for sliver_id in (
            plan.sliver_ids
        ):
            if sliver_id.startswith(
                "exile:"
            ):
                raise AlloyAssemblerError(
                    "Exiles may not be "
                    "embedded in an Alloy"
                )

            self.pool.get(
                sliver_id
            )

    def _normalize_configuration(
        self,
        plan: AlloyPlan,
        configuration: (
            dict[str, Any]
            | None
        ),
    ) -> dict[str, Any]:
        raw = (
            configuration
            or {}
        )

        if not isinstance(
            raw,
            dict,
        ):
            raise AlloyAssemblerError(
                "configuration must "
                "be an object"
            )

        allowed = set(
            plan.sliver_ids
        )

        unknown = sorted(
            key
            for key
            in raw
            if key not in allowed
        )

        if unknown:
            raise AlloyAssemblerError(
                "configuration references "
                "unselected Slivers: "
                + ", ".join(
                    unknown
                )
            )

        return {
            sliver_id: (
                raw.get(
                    sliver_id,
                    {},
                )
            )
            for sliver_id
            in plan.sliver_ids
        }

    def _normalize_interfaces(
        self,
        plan: AlloyPlan,
        interfaces: (
            dict[str, Iterable[str]]
            | None
        ),
    ) -> dict[
        str,
        tuple[str, ...],
    ]:
        raw = (
            interfaces
            or {}
        )

        if not isinstance(
            raw,
            dict,
        ):
            raise AlloyAssemblerError(
                "authorized_interfaces "
                "must be an object"
            )

        selected = set(
            plan.sliver_ids
        )

        unknown = sorted(
            key
            for key
            in raw
            if key not in selected
        )

        if unknown:
            raise AlloyAssemblerError(
                "interface bindings "
                "reference unselected "
                "Slivers: "
                + ", ".join(
                    unknown
                )
            )

        result: dict[
            str,
            tuple[str, ...],
        ] = {}

        for sliver_id in (
            plan.sliver_ids
        ):
            values = raw.get(
                sliver_id,
                (),
            )

            if isinstance(
                values,
                str,
            ):
                values = (
                    values,
                )

            normalized = tuple(
                sorted(
                    {
                        normalized_id(
                            value
                        )
                        for value
                        in values
                        if normalized_id(
                            value
                        )
                    }
                )
            )

            for value in normalized:
                if not (
                    value.startswith(
                        "interface:"
                    )
                    or value.startswith(
                        "service:"
                    )
                    or value.startswith(
                        "provider:"
                    )
                ):
                    raise AlloyAssemblerError(
                        "external capability "
                        "must be referenced "
                        "through an authorized "
                        "interface/service/"
                        "provider identity: "
                        + value
                    )

            result[
                sliver_id
            ] = normalized

        return result

    def _normalize_segues(
        self,
        plan: AlloyPlan,
        segues: (
            Iterable[
                SegueBinding
                | dict[str, Any]
            ]
            | None
        ),
        interfaces: dict[
            str,
            tuple[str, ...],
        ],
    ) -> tuple[
        SegueBinding,
        ...
    ]:
        selected = set(
            plan.sliver_ids
        )

        external = {
            interface
            for values
            in interfaces.values()
            for interface
            in values
        }

        allowed = (
            selected
            | external
        )

        result: list[
            SegueBinding
        ] = []

        for raw in (
            segues
            or ()
        ):
            if isinstance(
                raw,
                SegueBinding,
            ):
                binding = raw
            elif isinstance(
                raw,
                dict,
            ):
                binding = (
                    SegueBinding(
                        source=normalized_id(
                            raw.get(
                                "source"
                            )
                        ),
                        target=normalized_id(
                            raw.get(
                                "target"
                            )
                        ),
                        segue_type=normalized_id(
                            raw.get(
                                "type"
                            )
                        ),
                    )
                )
            else:
                raise AlloyAssemblerError(
                    "invalid Segue binding"
                )

            if (
                not binding.source
                or not binding.target
                or not binding.segue_type
            ):
                raise AlloyAssemblerError(
                    "Segue bindings require "
                    "source, target, and type"
                )

            if (
                binding.source
                not in allowed
                or binding.target
                not in allowed
            ):
                raise AlloyAssemblerError(
                    "Segue endpoint is not "
                    "part of the composition: "
                    f"{binding.source} -> "
                    f"{binding.target}"
                )

            result.append(
                binding
            )

        unique = {
            (
                item.source,
                item.segue_type,
                item.target,
            ): item
            for item
            in result
        }

        return tuple(
            unique[key]
            for key
            in sorted(
                unique
            )
        )

    def assemble(
        self,
        plan: AlloyPlan,
        *,
        configuration: (
            dict[str, Any]
            | None
        ) = None,
        authorized_interfaces: (
            dict[
                str,
                Iterable[str],
            ]
            | None
        ) = None,
        segues: (
            Iterable[
                SegueBinding
                | dict[str, Any]
            ]
            | None
        ) = None,
    ) -> dict[str, Any]:
        self._validate_plan(
            plan
        )

        config = (
            self._normalize_configuration(
                plan,
                configuration,
            )
        )

        interfaces = (
            self._normalize_interfaces(
                plan,
                authorized_interfaces,
            )
        )

        segue_bindings = (
            self._normalize_segues(
                plan,
                segues,
                interfaces,
            )
        )

        sliver_instances = []

        for ordinal, sliver_id in (
            enumerate(
                plan.sliver_ids,
                start=1,
            )
        ):
            sliver = self.pool.get(
                sliver_id
            )

            projection = (
                sliver.projection()
            )

            instance = {
                "instance_id": (
                    f"{plan.alloy_id}:"
                    f"{sliver_id}"
                ),
                "ordinal": ordinal,
                "sliver": sliver_id,
                "capability": (
                    sliver.capability
                ),
                "sliver_digest": (
                    projection[
                        "digest"
                    ]
                ),
                "configuration": (
                    config[
                        sliver_id
                    ]
                ),
                "authorized_interfaces": (
                    list(
                        interfaces[
                            sliver_id
                        ]
                    )
                ),
                "composition": (
                    "reference"
                ),
            }

            instance[
                "digest"
            ] = digest(
                instance
            )

            sliver_instances.append(
                instance
            )

        graph_nodes = [
            {
                "id": (
                    plan.alloy_id
                ),
                "kind": "alloy",
            }
        ]

        graph_nodes.extend(
            {
                "id": item[
                    "instance_id"
                ],
                "kind": (
                    "sliver-instance"
                ),
                "sliver": item[
                    "sliver"
                ],
            }
            for item
            in sliver_instances
        )

        external_nodes = sorted(
            {
                interface
                for values
                in interfaces.values()
                for interface
                in values
            }
        )

        graph_nodes.extend(
            {
                "id": identity,
                "kind": (
                    "authorized-external-"
                    "interface"
                ),
            }
            for identity
            in external_nodes
        )

        instance_lookup = {
            item[
                "sliver"
            ]: item[
                "instance_id"
            ]
            for item
            in sliver_instances
        }

        graph_edges = [
            {
                "source": (
                    plan.alloy_id
                ),
                "target": item[
                    "instance_id"
                ],
                "type": "composes",
            }
            for item
            in sliver_instances
        ]

        for binding in (
            segue_bindings
        ):
            graph_edges.append(
                {
                    "source": (
                        instance_lookup.get(
                            binding.source,
                            binding.source,
                        )
                    ),
                    "target": (
                        instance_lookup.get(
                            binding.target,
                            binding.target,
                        )
                    ),
                    "type": (
                        binding.segue_type
                    ),
                }
            )

        graph_edges.sort(
            key=lambda edge: (
                edge[
                    "source"
                ],
                edge[
                    "type"
                ],
                edge[
                    "target"
                ],
            )
        )

        graph = {
            "schema": (
                COMPOSITION_GRAPH_SCHEMA
            ),
            "nodes": graph_nodes,
            "edges": graph_edges,
            "authoritative": False,
            "rebuildable": True,
        }

        graph[
            "digest"
        ] = digest(
            graph
        )

        alloy = {
            "schema": ALLOY_SCHEMA,
            "id": plan.alloy_id,
            "kind": "alloy",
            "owner": OWNER,
            "source_plan": (
                plan.projection()
            ),
            "sliver_count": len(
                sliver_instances
            ),
            "sliver_ids": list(
                plan.sliver_ids
            ),
            "sliver_instances": (
                sliver_instances
            ),
            "segues": [
                item.projection()
                for item
                in segue_bindings
            ],
            "composition_graph": (
                graph
            ),
            "composition": (
                "reference"
            ),
            "minimum_sufficient": True,
            "exiles_embedded": False,
            "external_access": (
                "authorized-interface-only"
            ),
            "authoritative": False,
            "rebuildable": True,
            "authority_effect": "none",
        }

        alloy[
            "composition_digest"
        ] = digest(
            alloy
        )

        return alloy

    def assemble_recipe(
        self,
        application_id: str,
        **kwargs: Any,
    ) -> dict[str, Any]:
        try:
            plan = (
                self.compiler
                .compile_recipe(
                    application_id
                )
            )
        except (
            CapabilityCompilerError
        ) as exc:
            raise AlloyAssemblerError(
                str(
                    exc
                )
            ) from exc

        return self.assemble(
            plan,
            **kwargs,
        )

    def status(
        self,
    ) -> dict[str, Any]:
        payload = {
            "schema": (
                "savant://coalesce/"
                "alloy-assembler-status/1"
            ),
            "owner": OWNER,
            "sliver_pool_size": len(
                self.pool.slivers
            ),
            "alloy_min_slivers": 1,
            "alloy_max_slivers": 9,
            "reference_composition": (
                True
            ),
            "typed_segues": True,
            "configuration": True,
            "authorized_interfaces": (
                True
            ),
            "exile_embedding": False,
            "deterministic": True,
            "authoritative": False,
            "authority_effect": "none",
        }

        payload[
            "digest"
        ] = digest(
            payload
        )

        return payload


def assembler() -> AlloyAssembler:
    return AlloyAssembler()


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="alloy_assembler"
    )

    parser.add_argument(
        "operation",
        choices=(
            "status",
            "recipe",
        ),
    )

    parser.add_argument(
        "identity",
        nargs="?",
    )

    args = parser.parse_args()

    engine = assembler()

    if args.operation == "status":
        result = engine.status()

    else:
        if not args.identity:
            parser.error(
                "recipe requires identity"
            )

        result = (
            engine.assemble_recipe(
                args.identity
            )
        )

    print(
        json.dumps(
            result,
            indent=2,
            sort_keys=True,
        )
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
