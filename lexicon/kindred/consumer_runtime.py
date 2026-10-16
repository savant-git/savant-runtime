#!/usr/bin/env python3

from __future__ import annotations

import json
from types import MappingProxyType
from typing import Any, Mapping

from lexicon.kindred.kindred_engine import KindredEngine
from lexicon.kindred.relationship_resolver import (
    KindredRelationshipResolver,
)
from lexicon.kindred.runtime_contract import (
    contract as runtime_contract,
)
from lexicon.kindred.semantic_runtime import (
    KindredSemanticRuntime,
)


schema = "savant.kindred.consumer-runtime.v1"
authority_effect = "none"
owner = "kindred"

forbidden_consumer_modules = (
    "discipline_engine",
    "discipline_registry",
)


class KindredConsumerRuntimeError(
    RuntimeError
):
    pass


class KindredConsumerRuntime:
    """
    Canonical read boundary for downstream Kindred consumers.

    Consumers receive resolved relationship semantics, Kindred
    registry projections, and canonical calculus capabilities through
    this surface rather than independently deciding relationship
    authority.

    This runtime owns no mutation authority.
    """

    def __init__(
        self,
    ) -> None:
        self._resolver = (
            KindredRelationshipResolver()
        )

        self._engine = (
            KindredEngine()
        )

        self._semantic = (
            KindredSemanticRuntime()
        )

        self._contract = (
            runtime_contract()
        )

        self._assert_contract()

    def _assert_contract(
        self,
    ) -> None:
        if (
            self._contract.get(
                "mutation_authority"
            )
            is not False
        ):
            raise KindredConsumerRuntimeError(
                "Kindred runtime contract acquired "
                "mutation authority"
            )

        if (
            self._contract.get(
                "relationship_authority_created"
            )
            is not False
        ):
            raise KindredConsumerRuntimeError(
                "Kindred runtime contract manufactured "
                "relationship authority"
            )

        relationship_authority = (
            self._contract.get(
                "relationship_authority"
            )
        )

        if not isinstance(
            relationship_authority,
            Mapping,
        ):
            raise KindredConsumerRuntimeError(
                "Kindred relationship authority "
                "contract is missing"
            )

        if (
            relationship_authority.get(
                "owner"
            )
            != "constitutional-relationships"
        ):
            raise KindredConsumerRuntimeError(
                "Kindred relationship authority "
                "owner changed"
            )

        registry = (
            self._contract.get(
                "kindred_registry"
            )
        )

        if not isinstance(
            registry,
            Mapping,
        ):
            raise KindredConsumerRuntimeError(
                "Kindred registry contract is missing"
            )

        if (
            registry.get(
                "lineage_primitive"
            )
            != "lineage_segue"
        ):
            raise KindredConsumerRuntimeError(
                "Kindred lineage primitive changed"
            )

        if (
            registry.get(
                "inverse_lineage_views"
            )
            != "projection"
        ):
            raise KindredConsumerRuntimeError(
                "Kindred inverse lineage views "
                "became authoritative"
            )

    @property
    def contract(
        self,
    ) -> Mapping[str, Any]:
        return MappingProxyType(
            self._contract
        )

    def resolve_relationship(
        self,
        relationship_id: str,
    ) -> Mapping[str, Any]:
        relationship_id = str(
            relationship_id
        ).strip()

        if not relationship_id:
            raise KindredConsumerRuntimeError(
                "relationship_id is required"
            )

        resolved = (
            self._resolver.resolve(
                relationship_id
            )
        )

        if not isinstance(
            resolved,
            Mapping,
        ):
            raise KindredConsumerRuntimeError(
                "relationship resolver returned "
                "a non-object"
            )

        authoritative = (
            resolved.get(
                "authoritative"
            )
        )

        if authoritative not in (
            True,
            False,
        ):
            raise KindredConsumerRuntimeError(
                "resolved relationship lacks "
                "explicit authority state"
            )

        return MappingProxyType(
            dict(
                resolved
            )
        )

    def kindred(
        self,
        kindred_id: str,
    ) -> Any:
        kindred_id = str(
            kindred_id
        ).strip()

        if not kindred_id:
            raise KindredConsumerRuntimeError(
                "kindred_id is required"
            )

        return self._engine.get(
            kindred_id
        )

    def lineage(
        self,
        kindred_id: str,
    ) -> Any:
        return self._engine.lineage(
            str(
                kindred_id
            ).strip()
        )

    def parents(
        self,
        kindred_id: str,
    ) -> Any:
        return self._engine.parents(
            str(
                kindred_id
            ).strip()
        )

    def children(
        self,
        kindred_id: str,
    ) -> Any:
        return self._engine.children(
            str(
                kindred_id
            ).strip()
        )

    def ancestors(
        self,
        kindred_id: str,
    ) -> Any:
        return self._engine.ancestors(
            str(
                kindred_id
            ).strip()
        )

    def descendants(
        self,
        kindred_id: str,
    ) -> Any:
        return self._engine.descendants(
            str(
                kindred_id
            ).strip()
        )

    def dependencies(
        self,
        kindred_id: str,
    ) -> Any:
        return self._engine.dependencies(
            str(
                kindred_id
            ).strip()
        )

    def memberships(
        self,
        kindred_id: str,
    ) -> Any:
        return self._engine.memberships(
            str(
                kindred_id
            ).strip()
        )

    def relationship_edges(
        self,
        kindred_id: str,
    ) -> Any:
        return self._engine.relationship_edges(
            str(
                kindred_id
            ).strip()
        )

    def graph(
        self,
    ) -> Mapping[str, Any]:
        graph = self._engine.graph()

        if not isinstance(
            graph,
            Mapping,
        ):
            raise KindredConsumerRuntimeError(
                "Kindred graph projection "
                "is not an object"
            )

        lineage_authority = (
            graph.get(
                "lineage_authority",
                {}
            )
        )

        if (
            lineage_authority.get(
                "primitive"
            )
            != "lineage_segue"
        ):
            raise KindredConsumerRuntimeError(
                "Kindred graph changed lineage "
                "primitive authority"
            )

        if (
            lineage_authority.get(
                "inverse_views"
            )
            != "projection"
        ):
            raise KindredConsumerRuntimeError(
                "Kindred graph promoted inverse "
                "views to authority"
            )

        return MappingProxyType(
            dict(
                graph
            )
        )

    def semantic(
        self,
        module_name: str,
        capability_name: str,
        /,
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        if (
            module_name
            in forbidden_consumer_modules
        ):
            raise KindredConsumerRuntimeError(
                f"{module_name!r} is quarantined "
                "from the canonical consumer surface"
            )

        return self._semantic.invoke(
            module_name,
            capability_name,
            *args,
            **kwargs,
        )

    def manifest(
        self,
    ) -> dict[str, Any]:
        relationship_authority = (
            self._contract[
                "relationship_authority"
            ]
        )

        registry = (
            self._contract[
                "kindred_registry"
            ]
        )

        return {
            "schema":
                schema,
            "authority_effect":
                authority_effect,
            "owner":
                owner,
            "mutation_authority":
                False,
            "relationship_authority_created":
                False,
            "relationship_authority_owner":
                relationship_authority[
                    "owner"
                ],
            "relationship_authority_source":
                relationship_authority[
                    "source"
                ],
            "kindred_registry_source":
                registry[
                    "source"
                ],
            "lineage_primitive":
                registry[
                    "lineage_primitive"
                ],
            "inverse_lineage_views":
                registry[
                    "inverse_lineage_views"
                ],
            "consumer_authority_interpretation":
                False,
            "forbidden_consumer_modules":
                list(
                    forbidden_consumer_modules
                ),
            "surfaces": [
                "resolve_relationship",
                "kindred",
                "lineage",
                "parents",
                "children",
                "ancestors",
                "descendants",
                "dependencies",
                "memberships",
                "relationship_edges",
                "graph",
                "semantic",
            ],
        }


def self_check() -> dict[str, Any]:
    runtime = KindredConsumerRuntime()

    first = runtime.manifest()
    second = runtime.manifest()

    if (
        json.dumps(
            first,
            sort_keys=True,
            separators=(",", ":"),
        )
        != json.dumps(
            second,
            sort_keys=True,
            separators=(",", ":"),
        )
    ):
        raise KindredConsumerRuntimeError(
            "Kindred consumer manifest "
            "is not deterministic"
        )

    if (
        first[
            "mutation_authority"
        ]
        is not False
    ):
        raise KindredConsumerRuntimeError(
            "consumer runtime acquired "
            "mutation authority"
        )

    if (
        first[
            "relationship_authority_created"
        ]
        is not False
    ):
        raise KindredConsumerRuntimeError(
            "consumer runtime created "
            "relationship authority"
        )

    if (
        first[
            "consumer_authority_interpretation"
        ]
        is not False
    ):
        raise KindredConsumerRuntimeError(
            "consumer runtime independently "
            "interprets relationship authority"
        )

    for forbidden in (
        forbidden_consumer_modules
    ):
        if (
            forbidden
            not in first[
                "forbidden_consumer_modules"
            ]
        ):
            raise KindredConsumerRuntimeError(
                "quarantined module escaped "
                "consumer exclusion"
            )

    graph = runtime.graph()

    if (
        graph.get(
            "lineage_authority",
            {}
        ).get(
            "primitive"
        )
        != "lineage_segue"
    ):
        raise KindredConsumerRuntimeError(
            "consumer graph lineage primitive "
            "check failed"
        )

    return {
        **first,
        "status":
            "passed",
    }


def main() -> int:
    try:
        print(
            json.dumps(
                self_check(),
                indent=2,
                sort_keys=True,
            )
        )

        return 0

    except Exception as exc:
        print(
            json.dumps(
                {
                    "schema":
                        schema,
                    "authority_effect":
                        authority_effect,
                    "owner":
                        owner,
                    "status":
                        "failed",
                    "error":
                        str(
                            exc
                        ),
                },
                indent=2,
                sort_keys=True,
            )
        )

        return 1


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
