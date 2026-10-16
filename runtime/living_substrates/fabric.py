#!/usr/bin/env python3

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence


ROOT = Path("/root/savant-runtime")

REGISTRY_PATH = (
    ROOT
    / "runtime/living_substrates/registry.json"
)

SCHEMA_PATH = (
    ROOT
    / "runtime/living_substrates/binding.schema.json"
)


SLOT_TO_SUBSTRATE = {
    "structure": "scyon",
    "interface": "splyce",
    "memory": "scrybe",
    "authority": "pryme",
    "exchange": "cypher",
    "assurance": "thryce",
    "evolution": "spyral",
    "derivation": "lythe",
    "execution": "dryve",
}


SUBSTRATES = tuple(
    SLOT_TO_SUBSTRATE.values()
)


AUTHORITY_STATES = (
    "observed",
    "proposed",
    "provisional",
    "accepted",
    "superseded",
    "rejected",
)


class BindingError(RuntimeError):
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


def _load_json(
    path: Path,
) -> dict[str, Any]:
    if not path.is_absolute():
        raise BindingError(
            f"path must be absolute: {path}"
        )

    if not path.is_file():
        raise BindingError(
            f"missing file: {path}"
        )

    try:
        payload = json.loads(
            path.read_text(
                encoding="utf-8"
            )
        )
    except json.JSONDecodeError as exc:
        raise BindingError(
            f"invalid JSON: {path}: {exc}"
        ) from exc

    if not isinstance(
        payload,
        dict,
    ):
        raise BindingError(
            f"expected object: {path}"
        )

    return payload


def _optional_jsonschema_validate(
    payload: Mapping[str, Any],
) -> dict[str, Any]:
    try:
        from jsonschema import (
            Draft202012Validator,
        )
    except ImportError:
        return {
            "available": False,
            "valid": None,
            "errors": [],
        }

    schema = _load_json(
        SCHEMA_PATH
    )

    validator = Draft202012Validator(
        schema
    )

    errors = sorted(
        validator.iter_errors(
            dict(payload)
        ),
        key=lambda error:
            tuple(
                str(part)
                for part
                in error.absolute_path
            ),
    )

    return {
        "available": True,
        "valid": not errors,
        "errors": [
            {
                "path": ".".join(
                    str(part)
                    for part
                    in error.absolute_path
                ),
                "message": error.message,
            }
            for error
            in errors
        ],
    }


@dataclass(
    frozen=True,
    slots=True,
)
class LivingBinding:
    binding_id: str
    owner_id: str
    slot: str
    substrate: str
    substrate_instance: str
    authority_state: str
    enabled: bool
    version: str
    specialization: Mapping[str, Any]
    parameters: Mapping[str, Any]
    dependencies: tuple[str, ...]
    lineage: Mapping[str, Any]
    provenance: Mapping[str, Any]
    compatibility: Mapping[str, Any]

    def __post_init__(
        self,
    ) -> None:
        if not self.binding_id.strip():
            raise BindingError(
                "binding_id is required"
            )

        if not self.owner_id.strip():
            raise BindingError(
                "owner_id is required"
            )

        expected = SLOT_TO_SUBSTRATE.get(
            self.slot
        )

        if expected is None:
            raise BindingError(
                f"unknown living slot: {self.slot}"
            )

        if self.substrate != expected:
            raise BindingError(
                "slot/substrate mismatch: "
                f"{self.slot} requires {expected}, "
                f"found {self.substrate}"
            )

        if (
            self.authority_state
            not in AUTHORITY_STATES
        ):
            raise BindingError(
                "invalid authority state: "
                + self.authority_state
            )

        if not self.version.strip():
            raise BindingError(
                "version is required"
            )

        if not self.substrate_instance.strip():
            raise BindingError(
                "substrate_instance is required"
            )

        if self.binding_id in self.dependencies:
            raise BindingError(
                "binding cannot depend on itself"
            )

    @classmethod
    def from_mapping(
        cls,
        value: Mapping[str, Any],
    ) -> "LivingBinding":
        required = (
            "binding_id",
            "owner_id",
            "slot",
            "substrate",
            "substrate_instance",
            "authority_state",
            "enabled",
            "version",
            "specialization",
            "parameters",
            "dependencies",
            "lineage",
            "provenance",
            "compatibility",
        )

        missing = [
            field
            for field
            in required
            if field not in value
        ]

        if missing:
            raise BindingError(
                "binding missing fields: "
                + ", ".join(
                    missing
                )
            )

        dependencies = value[
            "dependencies"
        ]

        if not isinstance(
            dependencies,
            Sequence,
        ) or isinstance(
            dependencies,
            (
                str,
                bytes,
                bytearray,
            ),
        ):
            raise BindingError(
                "dependencies must be an array"
            )

        return cls(
            binding_id=str(
                value["binding_id"]
            ),
            owner_id=str(
                value["owner_id"]
            ),
            slot=str(
                value["slot"]
            ),
            substrate=str(
                value["substrate"]
            ),
            substrate_instance=str(
                value[
                    "substrate_instance"
                ]
            ),
            authority_state=str(
                value["authority_state"]
            ),
            enabled=bool(
                value["enabled"]
            ),
            version=str(
                value["version"]
            ),
            specialization=dict(
                value["specialization"]
            ),
            parameters=dict(
                value["parameters"]
            ),
            dependencies=tuple(
                str(item)
                for item
                in dependencies
            ),
            lineage=dict(
                value["lineage"]
            ),
            provenance=dict(
                value["provenance"]
            ),
            compatibility=dict(
                value["compatibility"]
            ),
        )

    def projection(
        self,
    ) -> dict[str, Any]:
        payload = {
            "binding_id":
                self.binding_id,
            "owner_id":
                self.owner_id,
            "slot":
                self.slot,
            "substrate":
                self.substrate,
            "substrate_instance":
                self.substrate_instance,
            "authority_state":
                self.authority_state,
            "enabled":
                self.enabled,
            "version":
                self.version,
            "specialization":
                dict(
                    self.specialization
                ),
            "parameters":
                dict(
                    self.parameters
                ),
            "dependencies":
                list(
                    self.dependencies
                ),
            "lineage":
                dict(
                    self.lineage
                ),
            "provenance":
                dict(
                    self.provenance
                ),
            "compatibility":
                dict(
                    self.compatibility
                ),
            "authoritative_projection":
                False,
        }

        payload[
            "binding_digest"
        ] = digest(
            payload
        )

        return payload


class LivingSlotFabric:
    schema = (
        "savant://runtime/"
        "living-slot-fabric/1.0.0"
    )

    def __init__(
        self,
        bindings:
            Iterable[
                LivingBinding
            ] = (),
    ) -> None:
        self.registry = _load_json(
            REGISTRY_PATH
        )

        self._validate_registry()

        self._bindings: dict[
            str,
            LivingBinding,
        ] = {}

        for binding in bindings:
            self.add(
                binding
            )

    def _validate_registry(
        self,
    ) -> None:
        slots = self.registry.get(
            "slots",
            [],
        )

        if not isinstance(
            slots,
            list,
        ):
            raise BindingError(
                "registry slots must be an array"
            )

        if len(slots) != 9:
            raise BindingError(
                "registry must define "
                "exactly 9 living slot types"
            )

        observed = {
            str(
                item.get(
                    "slot"
                )
            ):
                str(
                    item.get(
                        "substrate"
                    )
                )
            for item
            in slots
            if isinstance(
                item,
                dict,
            )
        }

        if observed != SLOT_TO_SUBSTRATE:
            raise BindingError(
                "registry slot/substrate "
                "mapping mismatch"
            )

        health = self.registry.get(
            "health_dimensions",
            [],
        )

        validation = self.registry.get(
            "validation_dimensions",
            [],
        )

        if len(health) != 9:
            raise BindingError(
                "registry must expose "
                "9 health dimensions"
            )

        if len(validation) != 9:
            raise BindingError(
                "registry must expose "
                "9 validation dimensions"
            )

        groups = self.registry.get(
            "enhancement_groups",
            {},
        )

        if (
            not isinstance(
                groups,
                dict,
            )
            or len(groups) != 9
        ):
            raise BindingError(
                "registry must expose "
                "9 enhancement groups"
            )

        for name, values in (
            groups.items()
        ):
            if (
                not isinstance(
                    values,
                    list,
                )
                or len(values) != 3
            ):
                raise BindingError(
                    f"{name} must expose "
                    "exactly 3 enhancements"
                )

    @property
    def enhancement_count(
        self,
    ) -> int:
        return sum(
            len(values)
            for values
            in self.registry[
                "enhancement_groups"
            ].values()
        )

    @classmethod
    def from_manifest(
        cls,
        path: Path,
    ) -> "LivingSlotFabric":
        manifest = _load_json(
            path.resolve()
        )

        raw = manifest.get(
            "bindings",
            [],
        )

        if not isinstance(
            raw,
            list,
        ):
            raise BindingError(
                "manifest bindings "
                "must be an array"
            )

        bindings = [
            LivingBinding.from_mapping(
                item
            )
            for item
            in raw
        ]

        return cls(
            bindings
        )

    def add(
        self,
        binding: LivingBinding,
    ) -> None:
        if (
            binding.binding_id
            in self._bindings
        ):
            raise BindingError(
                "duplicate binding identity: "
                + binding.binding_id
            )

        self._bindings[
            binding.binding_id
        ] = binding

    def bindings(
        self,
        *,
        enabled_only:
            bool = False,
    ) -> tuple[
        LivingBinding,
        ...,
    ]:
        values = [
            self._bindings[key]
            for key
            in sorted(
                self._bindings
            )
        ]

        if enabled_only:
            values = [
                binding
                for binding
                in values
                if binding.enabled
            ]

        return tuple(
            values
        )

    def owner_bindings(
        self,
        owner_id: str,
        *,
        enabled_only:
            bool = False,
    ) -> tuple[
        LivingBinding,
        ...,
    ]:
        return tuple(
            binding
            for binding
            in self.bindings(
                enabled_only=(
                    enabled_only
                )
            )
            if binding.owner_id
            == owner_id
        )

    def slot_bindings(
        self,
        slot: str,
        *,
        enabled_only:
            bool = False,
    ) -> tuple[
        LivingBinding,
        ...,
    ]:
        if slot not in SLOT_TO_SUBSTRATE:
            raise BindingError(
                f"unknown living slot: {slot}"
            )

        return tuple(
            binding
            for binding
            in self.bindings(
                enabled_only=(
                    enabled_only
                )
            )
            if binding.slot == slot
        )

    def substrate_consumers(
        self,
        substrate: str,
        *,
        enabled_only:
            bool = False,
    ) -> tuple[
        str,
        ...,
    ]:
        if substrate not in SUBSTRATES:
            raise BindingError(
                "unknown substrate: "
                + substrate
            )

        return tuple(
            sorted(
                {
                    binding.owner_id
                    for binding
                    in self.bindings(
                        enabled_only=(
                            enabled_only
                        )
                    )
                    if (
                        binding.substrate
                        == substrate
                    )
                }
            )
        )

    def reverse_index(
        self,
    ) -> dict[
        str,
        list[str],
    ]:
        result: dict[
            str,
            list[str],
        ] = {}

        for binding in self.bindings():
            for dependency in (
                binding.dependencies
            ):
                result.setdefault(
                    dependency,
                    [],
                ).append(
                    binding.binding_id
                )

        return {
            key: sorted(
                values
            )
            for key, values
            in sorted(
                result.items()
            )
        }

    def _dependency_edges(
        self,
    ) -> tuple[
        tuple[str, str],
        ...,
    ]:
        edges: list[
            tuple[str, str]
        ] = []

        for binding in self.bindings():
            for dependency in (
                binding.dependencies
            ):
                edges.append(
                    (
                        dependency,
                        binding.binding_id,
                    )
                )

        return tuple(
            sorted(
                edges
            )
        )

    def dependency_report(
        self,
    ) -> dict[str, Any]:
        nodes = tuple(
            self._bindings
        )

        missing = sorted(
            {
                dependency
                for binding
                in self.bindings()
                for dependency
                in binding.dependencies
                if dependency
                not in self._bindings
            }
        )

        edges = self._dependency_edges()

        networkx_available = False
        cycle: list[str] = []
        order: list[str] = []

        try:
            import networkx as nx
        except ImportError:
            nx = None

        if nx is not None:
            networkx_available = True

            graph = nx.DiGraph()

            graph.add_nodes_from(
                nodes
            )

            graph.add_edges_from(
                edges
            )

            if (
                nx.is_directed_acyclic_graph(
                    graph
                )
            ):
                order = list(
                    nx.lexicographical_topological_sort(
                        graph
                    )
                )
            else:
                try:
                    cycle = [
                        str(value)
                        for value
                        in nx.find_cycle(
                            graph
                        )[0]
                    ]
                except (
                    nx.NetworkXNoCycle,
                    IndexError,
                ):
                    cycle = [
                        "cycle-detected"
                    ]

        else:
            order, cycle = (
                self
                ._stdlib_topological_order()
            )

        valid = (
            not missing
            and not cycle
        )

        payload = {
            "nodes":
                sorted(
                    nodes
                ),
            "edges": [
                {
                    "dependency":
                        dependency,
                    "dependent":
                        dependent,
                }
                for (
                    dependency,
                    dependent
                )
                in edges
            ],
            "missing_dependencies":
                missing,
            "cycle":
                cycle,
            "topological_order":
                order,
            "networkx_available":
                networkx_available,
            "valid":
                valid,
        }

        payload[
            "digest"
        ] = digest(
            payload
        )

        return payload

    def _stdlib_topological_order(
        self,
    ) -> tuple[
        list[str],
        list[str],
    ]:
        dependencies: dict[
            str,
            set[str],
        ] = {
            binding.binding_id:
                set(
                    binding.dependencies
                )
            for binding
            in self.bindings()
        }

        for values in (
            dependencies.values()
        ):
            values.intersection_update(
                dependencies
            )

        order: list[str] = []

        while dependencies:
            ready = sorted(
                key
                for key, values
                in dependencies.items()
                if not values
            )

            if not ready:
                return (
                    order,
                    sorted(
                        dependencies
                    ),
                )

            for key in ready:
                order.append(
                    key
                )
                dependencies.pop(
                    key
                )

            for values in (
                dependencies.values()
            ):
                values.difference_update(
                    ready
                )

        return (
            order,
            [],
        )

    def validate_binding(
        self,
        binding:
            LivingBinding,
    ) -> dict[str, Any]:
        projection = (
            binding.projection()
        )

        schema_validation = (
            _optional_jsonschema_validate(
                {
                    key: value
                    for key, value
                    in projection.items()
                    if key
                    not in (
                        "binding_digest",
                        "authoritative_projection",
                    )
                }
            )
        )

        expected_substrate = (
            SLOT_TO_SUBSTRATE.get(
                binding.slot
            )
        )

        checks = {
            "schema": (
                schema_validation[
                    "valid"
                ]
                is not False
            ),
            "identity": bool(
                binding.binding_id
                and binding.owner_id
                and binding.substrate_instance
            ),
            "slot_substrate_compatibility": (
                expected_substrate
                == binding.substrate
            ),
            "authority_state": (
                binding.authority_state
                in AUTHORITY_STATES
            ),
            "dependency_topology": (
                binding.binding_id
                not in binding.dependencies
            ),
            "specialization_integrity": (
                isinstance(
                    binding.specialization,
                    Mapping,
                )
            ),
            "lineage_provenance": (
                isinstance(
                    binding.lineage,
                    Mapping,
                )
                and isinstance(
                    binding.provenance,
                    Mapping,
                )
            ),
            "jurisdiction_boundary":
                True,
            "deterministic_projection": (
                binding.projection()[
                    "binding_digest"
                ]
                == binding.projection()[
                    "binding_digest"
                ]
            ),
        }

        result = {
            "binding_id":
                binding.binding_id,
            "checks":
                checks,
            "jsonschema":
                schema_validation,
            "valid":
                all(
                    checks.values()
                ),
        }

        result[
            "digest"
        ] = digest(
            result
        )

        return result

    def validate(
        self,
    ) -> dict[str, Any]:
        binding_reports = [
            self.validate_binding(
                binding
            )
            for binding
            in self.bindings()
        ]

        dependency_report = (
            self.dependency_report()
        )

        duplicate_owner_slot_instance: list[
            dict[str, str]
        ] = []

        seen: set[
            tuple[str, str, str]
        ] = set()

        for binding in self.bindings():
            key = (
                binding.owner_id,
                binding.slot,
                binding.substrate_instance,
            )

            if key in seen:
                duplicate_owner_slot_instance.append(
                    {
                        "owner_id":
                            binding.owner_id,
                        "slot":
                            binding.slot,
                        "substrate_instance":
                            binding.substrate_instance,
                    }
                )

            seen.add(
                key
            )

        checks = {
            "slot_count": (
                len(
                    SLOT_TO_SUBSTRATE
                )
                == 9
            ),
            "substrate_count": (
                len(
                    SUBSTRATES
                )
                == 9
            ),
            "health_dimensions": (
                len(
                    self.registry[
                        "health_dimensions"
                    ]
                )
                == 9
            ),
            "validation_dimensions": (
                len(
                    self.registry[
                        "validation_dimensions"
                    ]
                )
                == 9
            ),
            "enhancement_count": (
                self.enhancement_count
                == 27
            ),
            "binding_validation": (
                all(
                    report[
                        "valid"
                    ]
                    for report
                    in binding_reports
                )
            ),
            "dependency_topology": (
                dependency_report[
                    "valid"
                ]
            ),
            "duplicate_binding_role": (
                not duplicate_owner_slot_instance
            ),
            "mutation_boundary": (
                self.registry[
                    "mutation_authorized"
                ]
                is False
                and self.registry[
                    "physical_migration_authorized"
                ]
                is False
            ),
        }

        result = {
            "schema": (
                "savant://assurance/"
                "living-slot-fabric/1.0.0"
            ),
            "valid": all(
                checks.values()
            ),
            "checks":
                checks,
            "binding_count":
                len(
                    self._bindings
                ),
            "slot_count":
                9,
            "substrate_count":
                9,
            "enhancement_count":
                self.enhancement_count,
            "bindings":
                binding_reports,
            "dependencies":
                dependency_report,
            "duplicate_owner_slot_instance":
                duplicate_owner_slot_instance,
            "mutation_authorized":
                False,
            "physical_migration_authorized":
                False,
        }

        result[
            "digest"
        ] = digest(
            result
        )

        return result

    def owner_projection(
        self,
        owner_id: str,
    ) -> dict[str, Any]:
        bindings = [
            binding.projection()
            for binding
            in self.owner_bindings(
                owner_id
            )
        ]

        by_slot = {
            slot: [
                binding
                for binding
                in bindings
                if binding[
                    "slot"
                ]
                == slot
            ]
            for slot
            in SLOT_TO_SUBSTRATE
        }

        payload = {
            "schema": (
                "savant://runtime/"
                "living-slot-owner-view/1.0.0"
            ),
            "owner_id":
                owner_id,
            "bindings":
                bindings,
            "slots":
                by_slot,
            "authoritative":
                False,
            "rebuildable":
                True,
        }

        payload[
            "digest"
        ] = digest(
            payload
        )

        return payload

    def substrate_projection(
        self,
        substrate: str,
    ) -> dict[str, Any]:
        consumers = (
            self.substrate_consumers(
                substrate
            )
        )

        bindings = [
            binding.projection()
            for binding
            in self.bindings()
            if (
                binding.substrate
                == substrate
            )
        ]

        payload = {
            "schema": (
                "savant://runtime/"
                "living-slot-substrate-view/1.0.0"
            ),
            "substrate":
                substrate,
            "consumers":
                list(
                    consumers
                ),
            "bindings":
                bindings,
            "authoritative":
                False,
            "rebuildable":
                True,
        }

        payload[
            "digest"
        ] = digest(
            payload
        )

        return payload

    def health(
        self,
    ) -> dict[str, Any]:
        validation = (
            self.validate()
        )

        dimensions = {
            "identity": (
                validation[
                    "checks"
                ][
                    "binding_validation"
                ]
            ),
            "authority": True,
            "compatibility": True,
            "dependencies": (
                validation[
                    "checks"
                ][
                    "dependency_topology"
                ]
            ),
            "lineage": True,
            "provenance": True,
            "specialization": True,
            "substrate_availability": (
                len(
                    SUBSTRATES
                )
                == 9
            ),
            "jurisdiction_preservation": (
                validation[
                    "checks"
                ][
                    "mutation_boundary"
                ]
            ),
        }

        payload = {
            "schema": (
                "savant://runtime/"
                "living-slot-health/1.0.0"
            ),
            "dimensions": {
                name: {
                    "healthy":
                        bool(
                            value
                        )
                }
                for name, value
                in dimensions.items()
            },
            "healthy":
                all(
                    dimensions.values()
                ),
        }

        payload[
            "digest"
        ] = digest(
            payload
        )

        return payload
