#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence

from simulation import (
    OWNER,
    SimulationRuntime,
    Transition,
    clone,
    digest,
    runtime,
)


SCHEMA = "savant://carbon/simulation-world/1"


class WorldError(RuntimeError):
    pass


def canonical(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )


def stable_id(
    prefix: str,
    material: Any,
) -> str:
    return (
        prefix
        + ":"
        + hashlib.sha256(
            canonical(material).encode("utf-8")
        ).hexdigest()[:24]
    )


@dataclass(frozen=True, slots=True)
class WorldEntity:
    id: str
    kind: str
    state: Mapping[str, Any]
    traits: Mapping[str, Any]
    tags: tuple[str, ...] = ()

    def projection(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "kind": self.kind,
            "state": clone(self.state),
            "traits": clone(self.traits),
            "tags": list(self.tags),
        }


@dataclass(frozen=True, slots=True)
class WorldRelation:
    id: str
    source: str
    target: str
    relation: str
    attributes: Mapping[str, Any]

    def projection(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "source": self.source,
            "target": self.target,
            "relation": self.relation,
            "attributes": clone(
                self.attributes
            ),
        }


@dataclass(slots=True)
class World:
    id: str
    name: str
    entities: dict[
        str,
        WorldEntity,
    ] = field(default_factory=dict)
    relations: dict[
        str,
        WorldRelation,
    ] = field(default_factory=dict)
    environment: dict[
        str,
        Any,
    ] = field(default_factory=dict)
    laws: dict[
        str,
        Any,
    ] = field(default_factory=dict)
    metadata: dict[
        str,
        Any,
    ] = field(default_factory=dict)

    def projection(self) -> dict[str, Any]:
        payload = {
            "schema": SCHEMA,
            "kind": "simulation_world",
            "id": self.id,
            "owner": OWNER,
            "name": self.name,
            "entities": {
                key: value.projection()
                for key, value in sorted(
                    self.entities.items()
                )
            },
            "relations": {
                key: value.projection()
                for key, value in sorted(
                    self.relations.items()
                )
            },
            "environment": clone(
                self.environment
            ),
            "laws": clone(self.laws),
            "metadata": clone(
                self.metadata
            ),
            "derived": True,
            "authoritative": False,
            "authority_effect": "none",
        }

        payload["digest"] = digest(payload)
        return payload


class WorldEngine:
    def __init__(
        self,
        simulation_runtime: SimulationRuntime = runtime,
    ) -> None:
        self.runtime = simulation_runtime
        self.worlds: dict[str, World] = {}

    def create(
        self,
        name: str,
        *,
        environment: Mapping[
            str,
            Any,
        ] | None = None,
        laws: Mapping[
            str,
            Any,
        ] | None = None,
        metadata: Mapping[
            str,
            Any,
        ] | None = None,
    ) -> World:
        normalized = str(
            name or ""
        ).strip()

        if not normalized:
            raise WorldError(
                "world name is required"
            )

        material = {
            "name": normalized,
            "environment": clone(
                dict(environment or {})
            ),
            "laws": clone(
                dict(laws or {})
            ),
            "metadata": clone(
                dict(metadata or {})
            ),
        }

        world = World(
            id=stable_id(
                "carbon-world",
                material,
            ),
            name=normalized,
            environment=material[
                "environment"
            ],
            laws=material["laws"],
            metadata=material[
                "metadata"
            ],
        )

        existing = self.worlds.get(
            world.id
        )

        if existing is not None:
            return existing

        self.worlds[world.id] = world
        return world

    def entity(
        self,
        world_id: str,
        *,
        kind: str,
        state: Mapping[
            str,
            Any,
        ] | None = None,
        traits: Mapping[
            str,
            Any,
        ] | None = None,
        tags: Sequence[str] = (),
        identity: str | None = None,
    ) -> WorldEntity:
        world = self._world(world_id)

        normalized_kind = str(
            kind or ""
        ).strip()

        if not normalized_kind:
            raise WorldError(
                "entity kind is required"
            )

        normalized_tags = tuple(
            sorted(
                {
                    str(tag).strip()
                    for tag in tags
                    if str(tag).strip()
                }
            )
        )

        material = {
            "world_id": world.id,
            "kind": normalized_kind,
            "state": clone(
                dict(state or {})
            ),
            "traits": clone(
                dict(traits or {})
            ),
            "tags": list(
                normalized_tags
            ),
            "identity": (
                str(identity).strip()
                if identity is not None
                else None
            ),
        }

        entity_id = (
            str(identity).strip()
            if identity is not None
            and str(identity).strip()
            else stable_id(
                "carbon-world-entity",
                material,
            )
        )

        if entity_id in world.entities:
            raise WorldError(
                f"world entity already exists: "
                f"{entity_id}"
            )

        entity = WorldEntity(
            id=entity_id,
            kind=normalized_kind,
            state=material["state"],
            traits=material["traits"],
            tags=normalized_tags,
        )

        world.entities[
            entity.id
        ] = entity

        return entity

    def relate(
        self,
        world_id: str,
        *,
        source: str,
        target: str,
        relation: str,
        attributes: Mapping[
            str,
            Any,
        ] | None = None,
    ) -> WorldRelation:
        world = self._world(world_id)

        if source not in world.entities:
            raise WorldError(
                f"source entity not found: "
                f"{source}"
            )

        if target not in world.entities:
            raise WorldError(
                f"target entity not found: "
                f"{target}"
            )

        normalized_relation = str(
            relation or ""
        ).strip()

        if not normalized_relation:
            raise WorldError(
                "relation is required"
            )

        material = {
            "world_id": world.id,
            "source": source,
            "target": target,
            "relation": normalized_relation,
            "attributes": clone(
                dict(attributes or {})
            ),
        }

        relation_id = stable_id(
            "carbon-world-relation",
            material,
        )

        relation_value = WorldRelation(
            id=relation_id,
            source=source,
            target=target,
            relation=normalized_relation,
            attributes=material[
                "attributes"
            ],
        )

        world.relations[
            relation_id
        ] = relation_value

        return relation_value

    def update_entity(
        self,
        world_id: str,
        entity_id: str,
        *,
        state: Mapping[
            str,
            Any,
        ] | None = None,
        traits: Mapping[
            str,
            Any,
        ] | None = None,
    ) -> WorldEntity:
        world = self._world(world_id)

        try:
            current = world.entities[
                entity_id
            ]
        except KeyError as exc:
            raise WorldError(
                f"world entity not found: "
                f"{entity_id}"
            ) from exc

        next_state = clone(
            dict(current.state)
        )
        next_traits = clone(
            dict(current.traits)
        )

        if state is not None:
            next_state.update(
                clone(dict(state))
            )

        if traits is not None:
            next_traits.update(
                clone(dict(traits))
            )

        updated = WorldEntity(
            id=current.id,
            kind=current.kind,
            state=next_state,
            traits=next_traits,
            tags=current.tags,
        )

        world.entities[
            entity_id
        ] = updated

        return updated

    def neighborhood(
        self,
        world_id: str,
        entity_id: str,
        *,
        relation: str | None = None,
        direction: str = "both",
    ) -> dict[str, Any]:
        world = self._world(world_id)

        if entity_id not in world.entities:
            raise WorldError(
                f"world entity not found: "
                f"{entity_id}"
            )

        if direction not in {
            "inbound",
            "outbound",
            "both",
        }:
            raise WorldError(
                "direction must be inbound, "
                "outbound, or both"
            )

        relation_filter = (
            str(relation).strip()
            if relation is not None
            else None
        )

        edges = []
        neighbors = set()

        for edge in world.relations.values():
            if (
                relation_filter
                and edge.relation
                != relation_filter
            ):
                continue

            outbound = (
                edge.source == entity_id
            )
            inbound = (
                edge.target == entity_id
            )

            include = (
                (
                    direction == "both"
                    and (
                        inbound
                        or outbound
                    )
                )
                or (
                    direction
                    == "outbound"
                    and outbound
                )
                or (
                    direction
                    == "inbound"
                    and inbound
                )
            )

            if not include:
                continue

            edges.append(
                edge.projection()
            )

            if outbound:
                neighbors.add(
                    edge.target
                )

            if inbound:
                neighbors.add(
                    edge.source
                )

        return {
            "schema": SCHEMA,
            "kind": "world_neighborhood",
            "owner": OWNER,
            "world_id": world.id,
            "entity_id": entity_id,
            "direction": direction,
            "relation": relation_filter,
            "neighbors": [
                world.entities[
                    neighbor
                ].projection()
                for neighbor in sorted(
                    neighbors
                )
            ],
            "relations": sorted(
                edges,
                key=lambda item: item[
                    "id"
                ],
            ),
            "derived": True,
            "authority_effect": "none",
        }

    def simulation_state(
        self,
        world_id: str,
    ) -> dict[str, Any]:
        world = self._world(world_id)

        return {
            "world_id": world.id,
            "world_name": world.name,
            "environment": clone(
                world.environment
            ),
            "laws": clone(
                world.laws
            ),
            "entities": {
                key: {
                    "kind": entity.kind,
                    "state": clone(
                        entity.state
                    ),
                    "traits": clone(
                        entity.traits
                    ),
                    "tags": list(
                        entity.tags
                    ),
                }
                for key, entity in sorted(
                    world.entities.items()
                )
            },
            "relations": [
                relation.projection()
                for _, relation in sorted(
                    world.relations.items()
                )
            ],
        }

    def instantiate(
        self,
        world_id: str,
        definition_id: str,
        *,
        seed: int | None = None,
    ):
        state = self.simulation_state(
            world_id
        )

        return self.runtime.instantiate(
            definition_id,
            initial_state=state,
            seed=seed,
        )

    def simulate(
        self,
        world_id: str,
        definition_id: str,
        transition: Transition,
        *,
        steps: int = 1,
        delta_time: float = 1.0,
        events: Sequence[Any] = (),
        parameters: Mapping[
            str,
            Any,
        ] | None = None,
        seed: int | None = None,
    ) -> dict[str, Any]:
        world = self._world(world_id)

        instance = self.instantiate(
            world.id,
            definition_id,
            seed=seed,
        )

        produced = self.runtime.execute(
            instance.id,
            transition=transition,
            events=events,
            steps=steps,
            delta_time=delta_time,
            parameters=parameters,
        )

        final_state = produced[-1]

        result = {
            "schema": SCHEMA,
            "kind": "world_simulation",
            "owner": OWNER,
            "world_id": world.id,
            "world_digest": (
                world.projection()[
                    "digest"
                ]
            ),
            "definition_id": (
                definition_id
            ),
            "instance_id": instance.id,
            "branch_id": (
                final_state.branch_id
            ),
            "states": [
                state.projection()
                for state in produced
            ],
            "final_state": (
                final_state.projection()
            ),
            "replay": (
                self.runtime
                .replay_projection(
                    instance.id
                )
            ),
            "derived": True,
            "authoritative": False,
            "authority_effect": "none",
        }

        result["id"] = stable_id(
            "carbon-world-simulation",
            {
                "world_id": world.id,
                "definition_id": (
                    definition_id
                ),
                "final_state_digest": (
                    final_state.digest
                ),
            },
        )

        result["digest"] = digest(
            result
        )

        return result

    def fork_world(
        self,
        world_id: str,
        *,
        name: str,
    ) -> World:
        source = self._world(
            world_id
        )

        material = {
            "source_world_id": source.id,
            "source_digest": (
                source.projection()[
                    "digest"
                ]
            ),
            "name": str(name).strip(),
        }

        if not material["name"]:
            raise WorldError(
                "fork world name is required"
            )

        fork = World(
            id=stable_id(
                "carbon-world",
                material,
            ),
            name=material["name"],
            entities={
                key: WorldEntity(
                    id=value.id,
                    kind=value.kind,
                    state=clone(
                        value.state
                    ),
                    traits=clone(
                        value.traits
                    ),
                    tags=tuple(
                        value.tags
                    ),
                )
                for key, value in (
                    source.entities.items()
                )
            },
            relations={
                key: WorldRelation(
                    id=value.id,
                    source=value.source,
                    target=value.target,
                    relation=value.relation,
                    attributes=clone(
                        value.attributes
                    ),
                )
                for key, value in (
                    source.relations.items()
                )
            },
            environment=clone(
                source.environment
            ),
            laws=clone(
                source.laws
            ),
            metadata={
                **clone(
                    source.metadata
                ),
                "forked_from": (
                    source.id
                ),
                "forked_from_digest": (
                    source.projection()[
                        "digest"
                    ]
                ),
            },
        )

        self.worlds[fork.id] = fork

        return fork

    def compare_worlds(
        self,
        left_world_id: str,
        right_world_id: str,
    ) -> dict[str, Any]:
        left = self._world(
            left_world_id
        )
        right = self._world(
            right_world_id
        )

        left_projection = (
            left.projection()
        )
        right_projection = (
            right.projection()
        )

        sections = (
            "entities",
            "relations",
            "environment",
            "laws",
            "metadata",
        )

        differences = {}

        for section in sections:
            left_value = (
                left_projection[section]
            )
            right_value = (
                right_projection[section]
            )

            if canonical(
                left_value
            ) != canonical(
                right_value
            ):
                differences[
                    section
                ] = {
                    "left": clone(
                        left_value
                    ),
                    "right": clone(
                        right_value
                    ),
                }

        return {
            "schema": SCHEMA,
            "kind": "world_comparison",
            "owner": OWNER,
            "left_world_id": left.id,
            "right_world_id": right.id,
            "left_digest": (
                left_projection["digest"]
            ),
            "right_digest": (
                right_projection["digest"]
            ),
            "same": not differences,
            "differences": differences,
            "derived": True,
            "non_mutating": True,
            "authority_effect": "none",
        }

    def _world(
        self,
        world_id: str,
    ) -> World:
        try:
            return self.worlds[
                world_id
            ]
        except KeyError as exc:
            raise WorldError(
                f"world not found: "
                f"{world_id}"
            ) from exc


engine = WorldEngine()


def status() -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "owner": OWNER,
        "purpose": (
            "compose simulation worlds from "
            "reusable entities, relations, "
            "environment, and governing laws"
        ),
        "capabilities": [
            "world_composition",
            "entity_instantiation",
            "typed_relationships",
            "environment_projection",
            "law_projection",
            "graph_neighborhoods",
            "world_to_simulation_projection",
            "world_simulation",
            "world_forking",
            "counterfactual_worlds",
            "world_comparison",
        ],
        "authority_effect": "none",
    }


if __name__ == "__main__":
    print(
        json.dumps(
            status(),
            indent=2,
            sort_keys=True,
        )
    )
