#!/usr/bin/env python3
from __future__ import annotations

from typing import Any, Mapping

from guise import (
    OWNER,
    SCHEMA,
    SPECIALIZATION,
    CharacterGraph,
    Guise,
    GuiseError,
    digest,
)


class GuiseInterrogationError(
    GuiseError
):
    pass


class GuiseInterrogator:
    def __init__(
        self,
        guise: Guise,
    ) -> None:
        self.guise = guise

    def _base(
        self,
        graph: CharacterGraph,
        operation: str,
    ) -> dict[str, Any]:
        return {
            "schema": SCHEMA,
            "owner": OWNER,
            "specialization": SPECIALIZATION,
            "operation": operation,
            "character_id": (
                graph.character_id
            ),
            "authority_effect": "none",
        }

    def current(
        self,
        graph: CharacterGraph,
    ) -> dict[str, Any]:
        states = sorted(
            graph.states.values(),
            key=lambda item: (
                item.at or "",
                item.id,
            ),
        )

        result = self._base(
            graph,
            "current",
        )

        result["state"] = (
            states[-1].projection()
            if states
            else None
        )
        result["known"] = bool(states)

        return self._finish(result)

    def knows(
        self,
        graph: CharacterGraph,
    ) -> dict[str, Any]:
        result = self._base(
            graph,
            "knows",
        )

        result["knowledge"] = [
            item.projection()
            for item in sorted(
                graph.knowledge.values(),
                key=lambda value: (
                    value.id
                ),
            )
        ]

        return self._finish(result)

    def pressure(
        self,
        graph: CharacterGraph,
    ) -> dict[str, Any]:
        states = sorted(
            graph.states.values(),
            key=lambda item: (
                item.at or "",
                item.id,
            ),
        )

        result = self._base(
            graph,
            "pressure",
        )

        result["states"] = [
            {
                "state_id": item.id,
                "at": item.at,
                "pressures": list(
                    item.pressures
                ),
            }
            for item in states
            if item.pressures
        ]

        return self._finish(result)

    def relationships(
        self,
        graph: CharacterGraph,
    ) -> dict[str, Any]:
        result = self._base(
            graph,
            "relationships",
        )

        result["relationships"] = [
            item.projection()
            for item in sorted(
                graph.relationships.values(),
                key=lambda value: (
                    value.id
                ),
            )
        ]

        return self._finish(result)

    def contradictions(
        self,
        graph: CharacterGraph,
    ) -> dict[str, Any]:
        result = self._base(
            graph,
            "contradictions",
        )

        result["contradictions"] = [
            item.projection()
            for item in sorted(
                graph.contradictions.values(),
                key=lambda value: (
                    value.id
                ),
            )
        ]

        return self._finish(result)

    def unresolved(
        self,
        graph: CharacterGraph,
    ) -> dict[str, Any]:
        result = self._base(
            graph,
            "unresolved",
        )

        result["questions"] = list(
            graph.unresolved
        )

        return self._finish(result)

    def why(
        self,
        graph: CharacterGraph,
        *,
        category_id: str,
    ) -> dict[str, Any]:
        category = graph.categories.get(
            category_id
        )

        if category is None:
            raise GuiseInterrogationError(
                f"unknown category: "
                f"{category_id}"
            )

        result = self._base(
            graph,
            "why",
        )

        result["category"] = (
            category.projection()
        )
        result["evidence"] = (
            graph.evidence_for(
                category
            )
        )
        result[
            "alternative_explanations"
        ] = list(
            category.alternative_explanations
        )

        return self._finish(result)

    def domain(
        self,
        graph: CharacterGraph,
        *,
        domain: str,
    ) -> dict[str, Any]:
        return graph.domain_projection(
            domain,
            self.guise.manifest,
        )

    def profile(
        self,
        graph: CharacterGraph,
    ) -> dict[str, Any]:
        return graph.projection(
            self.guise.manifest
        )

    def execute(
        self,
        graph: CharacterGraph,
        operation: str,
        arguments: Mapping[
            str,
            Any,
        ] | None = None,
    ) -> dict[str, Any]:
        arguments = dict(
            arguments or {}
        )

        operations = {
            "current": self.current,
            "knows": self.knows,
            "pressure": self.pressure,
            "relationships": (
                self.relationships
            ),
            "contradictions": (
                self.contradictions
            ),
            "unresolved": self.unresolved,
            "profile": self.profile,
        }

        if operation == "why":
            return self.why(
                graph,
                category_id=str(
                    arguments.get(
                        "category_id",
                        "",
                    )
                ),
            )

        if operation == "domain":
            return self.domain(
                graph,
                domain=str(
                    arguments.get(
                        "domain",
                        "",
                    )
                ),
            )

        handler = operations.get(
            operation
        )

        if handler is None:
            raise GuiseInterrogationError(
                f"unsupported guise operation: "
                f"{operation}"
            )

        return handler(graph)

    @staticmethod
    def _finish(
        result: dict[str, Any],
    ) -> dict[str, Any]:
        result["projection_digest"] = (
            digest(result)
        )
        return result
