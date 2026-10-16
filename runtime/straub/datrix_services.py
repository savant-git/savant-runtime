#!/usr/bin/env python3

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from typing import Any, Callable, Iterable, Mapping, Protocol

from .datrix_modules import (
    canonical_json,
    normalize_identifier,
    stable_digest,
)


schema = "savant.carbon.straub.datrix-services.v1"
authority_effect = "none"


class DatrixServiceError(ValueError):
    pass


class DatrixAdapterError(DatrixServiceError):
    pass


class DatrixTransactionError(DatrixServiceError):
    pass


class DatrixIndexError(DatrixServiceError):
    pass


class DatrixProjectionError(DatrixServiceError):
    pass


def _copy(
    value: Any,
) -> Any:
    return json.loads(
        canonical_json(
            value
        )
    )


def _normalized_ids(
    values: Iterable[Any] | None,
) -> tuple[str, ...]:
    return tuple(
        sorted(
            {
                str(value).strip()
                for value in (
                    values or ()
                )
                if str(value).strip()
            }
        )
    )


def _capsule_digest(
    capsule: Mapping[str, Any],
) -> str:
    digest = str(
        capsule.get("digest")
        or ""
    ).strip()

    if not digest:
        raise DatrixServiceError(
            "capsule digest is required"
        )

    return digest


def _capsule_instances(
    capsule: Mapping[str, Any],
) -> tuple[dict[str, Any], ...]:
    raw = capsule.get(
        "instances"
    )

    if not isinstance(
        raw,
        list,
    ):
        raise DatrixServiceError(
            "capsule instances invalid"
        )

    result: list[
        dict[str, Any]
    ] = []

    seen: set[str] = set()

    for item in raw:
        if not isinstance(
            item,
            Mapping,
        ):
            raise DatrixServiceError(
                "capsule instance invalid"
            )

        record = _copy(
            dict(item)
        )

        record_id = str(
            record.get("id")
            or ""
        ).strip()

        if not record_id:
            raise DatrixServiceError(
                "capsule instance id missing"
            )

        if record_id in seen:
            raise DatrixServiceError(
                "duplicate capsule instance id: "
                f"{record_id}"
            )

        seen.add(
            record_id
        )

        result.append(
            record
        )

    result.sort(
        key=lambda item: str(
            item["id"]
        )
    )

    return tuple(
        result
    )


def _capsule_membranes(
    capsule: Mapping[str, Any],
) -> tuple[dict[str, Any], ...]:
    raw = capsule.get(
        "membranes"
    )

    if not isinstance(
        raw,
        list,
    ):
        raise DatrixServiceError(
            "capsule membranes invalid"
        )

    result: list[
        dict[str, Any]
    ] = []

    seen: set[str] = set()

    for item in raw:
        if not isinstance(
            item,
            Mapping,
        ):
            raise DatrixServiceError(
                "capsule membrane invalid"
            )

        record = _copy(
            dict(item)
        )

        record_id = str(
            record.get("id")
            or ""
        ).strip()

        if not record_id:
            raise DatrixServiceError(
                "capsule membrane id missing"
            )

        if record_id in seen:
            raise DatrixServiceError(
                "duplicate capsule membrane id: "
                f"{record_id}"
            )

        seen.add(
            record_id
        )

        result.append(
            record
        )

    result.sort(
        key=lambda item: str(
            item["id"]
        )
    )

    return tuple(
        result
    )


class DatrixCustodyAdapter(
    Protocol
):
    adapter_id: str

    def load(
        self,
    ) -> Mapping[str, Any] | None:
        ...

    def compare_and_swap(
        self,
        capsule: Mapping[str, Any],
        expected_digest: str | None,
    ) -> str:
        ...

    def health(
        self,
    ) -> Mapping[str, Any]:
        ...


@dataclass(
    frozen=True,
    slots=True,
)
class DatrixAdapterDescriptor:
    adapter_id: str
    adapter_kind: str
    capabilities: tuple[str, ...]
    deterministic: bool
    durable: bool
    authoritative: bool
    distributed: bool
    provenance: Mapping[str, Any]

    @classmethod
    def create(
        cls,
        *,
        adapter_id: str,
        adapter_kind: str,
        capabilities: Iterable[str] = (),
        deterministic: bool = True,
        durable: bool = False,
        authoritative: bool = False,
        distributed: bool = False,
        provenance: Mapping[
            str,
            Any,
        ] | None = None,
    ) -> "DatrixAdapterDescriptor":
        normalized_id = (
            normalize_identifier(
                adapter_id,
                field="adapter_id",
            )
        )

        normalized_kind = (
            normalize_identifier(
                adapter_kind,
                field="adapter_kind",
            )
        )

        normalized_capabilities = tuple(
            sorted(
                {
                    normalize_identifier(
                        value,
                        field="capability",
                    )
                    for value
                    in capabilities
                }
            )
        )

        return cls(
            adapter_id=normalized_id,
            adapter_kind=normalized_kind,
            capabilities=(
                normalized_capabilities
            ),
            deterministic=bool(
                deterministic
            ),
            durable=bool(
                durable
            ),
            authoritative=bool(
                authoritative
            ),
            distributed=bool(
                distributed
            ),
            provenance=_copy(
                dict(
                    provenance
                    or {}
                )
            ),
        )

    def manifest(
        self,
    ) -> dict[str, Any]:
        substance = {
            "schema":
                "savant.carbon.straub."
                "datrix-adapter.v1",
            "kind":
                "datrix.adapter",
            "id":
                self.adapter_id,
            "adapter_kind":
                self.adapter_kind,
            "capabilities":
                list(
                    self.capabilities
                ),
            "deterministic":
                self.deterministic,
            "durable":
                self.durable,
            "distributed":
                self.distributed,
            "semantic_authority":
                self.authoritative,
            "provenance":
                _copy(
                    self.provenance
                ),
            "authority_effect":
                "none",
        }

        substance["digest"] = (
            stable_digest(
                substance
            )
        )

        return substance


class DatrixAdapterRegistry:
    def __init__(
        self,
    ) -> None:
        self._adapters: dict[
            str,
            DatrixAdapterDescriptor,
        ] = {}

    def register(
        self,
        descriptor: DatrixAdapterDescriptor,
    ) -> DatrixAdapterDescriptor:
        if descriptor.authoritative:
            raise DatrixAdapterError(
                "adapter cannot become "
                "semantic authority"
            )

        existing = self._adapters.get(
            descriptor.adapter_id
        )

        if existing is not None:
            if (
                existing.manifest()[
                    "digest"
                ]
                != descriptor.manifest()[
                    "digest"
                ]
            ):
                raise DatrixAdapterError(
                    "adapter identity collision: "
                    f"{descriptor.adapter_id}"
                )

            return existing

        self._adapters[
            descriptor.adapter_id
        ] = descriptor

        return descriptor

    def adapters(
        self,
    ) -> tuple[
        DatrixAdapterDescriptor,
        ...,
    ]:
        return tuple(
            self._adapters[key]
            for key
            in sorted(
                self._adapters
            )
        )

    def providers(
        self,
        capability: str,
    ) -> tuple[str, ...]:
        normalized = normalize_identifier(
            capability,
            field="capability",
        )

        return tuple(
            descriptor.adapter_id
            for descriptor
            in self.adapters()
            if normalized
            in descriptor.capabilities
        )

    def manifest(
        self,
    ) -> dict[str, Any]:
        adapters = [
            descriptor.manifest()
            for descriptor
            in self.adapters()
        ]

        substance = {
            "schema":
                "savant.carbon.straub."
                "datrix-adapter-registry.v1",
            "kind":
                "datrix.adapter-registry",
            "adapters":
                adapters,
            "adapter_count":
                len(adapters),
            "semantic_authority":
                False,
            "rebuildable":
                True,
            "authority_effect":
                "none",
        }

        substance["digest"] = (
            stable_digest(
                substance
            )
        )

        return substance


class DatrixDeterministicIndex:
    def __init__(
        self,
        capsule: Mapping[str, Any],
    ) -> None:
        if not isinstance(
            capsule,
            Mapping,
        ):
            raise DatrixIndexError(
                "index requires capsule"
            )

        self._capsule_digest = (
            _capsule_digest(
                capsule
            )
        )

        self._instances = (
            _capsule_instances(
                capsule
            )
        )

        self._membranes = (
            _capsule_membranes(
                capsule
            )
        )

        self._by_id: dict[
            str,
            dict[str, Any],
        ] = {}

        self._by_kind: dict[
            str,
            list[str],
        ] = {}

        self._by_dependency: dict[
            str,
            set[str],
        ] = {}

        self._outgoing: dict[
            str,
            set[str],
        ] = {}

        self._incoming: dict[
            str,
            set[str],
        ] = {}

        for record in self._instances:
            record_id = str(
                record["id"]
            )

            self._by_id[
                record_id
            ] = record

            record_kind = str(
                record.get("kind")
                or "instance"
            )

            self._by_kind.setdefault(
                record_kind,
                [],
            ).append(
                record_id
            )

            for dependency in (
                record.get(
                    "dependencies"
                )
                or []
            ):
                dependency_id = str(
                    dependency
                ).strip()

                if dependency_id:
                    self._by_dependency.setdefault(
                        dependency_id,
                        set(),
                    ).add(
                        record_id
                    )

        for membrane in self._membranes:
            membrane_id = str(
                membrane["id"]
            )

            self._by_id[
                membrane_id
            ] = membrane

            self._by_kind.setdefault(
                "membrane",
                [],
            ).append(
                membrane_id
            )

            source = str(
                membrane.get("from")
                or ""
            ).strip()

            target = str(
                membrane.get("to")
                or ""
            ).strip()

            if source and target:
                self._outgoing.setdefault(
                    source,
                    set(),
                ).add(
                    target
                )

                self._incoming.setdefault(
                    target,
                    set(),
                ).add(
                    source
                )

            dependencies = set(
                _normalized_ids(
                    membrane.get(
                        "dependencies"
                    )
                    or ()
                )
            )

            if source:
                dependencies.add(
                    source
                )

            if target:
                dependencies.add(
                    target
                )

            for dependency_id in dependencies:
                self._by_dependency.setdefault(
                    dependency_id,
                    set(),
                ).add(
                    membrane_id
                )

        for values in (
            self._by_kind.values()
        ):
            values.sort()

    def record(
        self,
        record_id: str,
    ) -> dict[str, Any] | None:
        record = self._by_id.get(
            str(record_id).strip()
        )

        if record is None:
            return None

        return _copy(
            record
        )

    def ids_by_kind(
        self,
        kind: str,
    ) -> tuple[str, ...]:
        return tuple(
            self._by_kind.get(
                str(kind),
                (),
            )
        )

    def dependents_of(
        self,
        record_id: str,
    ) -> tuple[str, ...]:
        return tuple(
            sorted(
                self._by_dependency.get(
                    str(record_id).strip(),
                    set(),
                )
            )
        )

    def outgoing(
        self,
        record_id: str,
    ) -> tuple[str, ...]:
        return tuple(
            sorted(
                self._outgoing.get(
                    str(record_id).strip(),
                    set(),
                )
            )
        )

    def incoming(
        self,
        record_id: str,
    ) -> tuple[str, ...]:
        return tuple(
            sorted(
                self._incoming.get(
                    str(record_id).strip(),
                    set(),
                )
            )
        )

    def projection(
        self,
    ) -> dict[str, Any]:
        kinds = {
            key: list(
                self._by_kind[key]
            )
            for key
            in sorted(
                self._by_kind
            )
        }

        dependencies = {
            key: sorted(
                self._by_dependency[key]
            )
            for key
            in sorted(
                self._by_dependency
            )
        }

        outgoing = {
            key: sorted(
                self._outgoing[key]
            )
            for key
            in sorted(
                self._outgoing
            )
        }

        incoming = {
            key: sorted(
                self._incoming[key]
            )
            for key
            in sorted(
                self._incoming
            )
        }

        projection = {
            "schema":
                "savant.carbon.straub."
                "datrix-index-isotope.v1",
            "kind":
                "isotope",
            "source_capsule_digest":
                self._capsule_digest,
            "record_count":
                len(
                    self._by_id
                ),
            "instance_count":
                len(
                    self._instances
                ),
            "membrane_count":
                len(
                    self._membranes
                ),
            "kinds":
                kinds,
            "dependency_dependents":
                dependencies,
            "outgoing":
                outgoing,
            "incoming":
                incoming,
            "projection_only":
                True,
            "rebuildable":
                True,
            "semantic_authority":
                False,
            "authority_effect":
                "none",
        }

        projection["digest"] = (
            stable_digest(
                projection
            )
        )

        return projection


@dataclass(
    frozen=True,
    slots=True,
)
class DatrixOperation:
    operation_id: str
    operation_kind: str
    target_id: str | None
    payload: Mapping[str, Any]
    dependencies: tuple[str, ...]

    @classmethod
    def create(
        cls,
        *,
        operation_id: str,
        operation_kind: str,
        target_id: str | None = None,
        payload: Mapping[
            str,
            Any,
        ] | None = None,
        dependencies: Iterable[
            str
        ] = (),
    ) -> "DatrixOperation":
        normalized_target = (
            str(
                target_id
                or ""
            ).strip()
            or None
        )

        return cls(
            operation_id=(
                normalize_identifier(
                    operation_id,
                    field="operation_id",
                )
            ),
            operation_kind=(
                normalize_identifier(
                    operation_kind,
                    field="operation_kind",
                )
            ),
            target_id=(
                normalized_target
            ),
            payload=_copy(
                dict(
                    payload
                    or {}
                )
            ),
            dependencies=(
                _normalized_ids(
                    dependencies
                )
            ),
        )

    def manifest(
        self,
    ) -> dict[str, Any]:
        substance = {
            "schema":
                "savant.carbon.straub."
                "datrix-operation.v1",
            "kind":
                "datrix.operation",
            "id":
                self.operation_id,
            "operation_kind":
                self.operation_kind,
            "target_id":
                self.target_id,
            "payload":
                _copy(
                    self.payload
                ),
            "dependencies":
                list(
                    self.dependencies
                ),
            "authority_effect":
                "none",
        }

        substance["digest"] = (
            stable_digest(
                substance
            )
        )

        return substance


class DatrixTransactionPlan:
    def __init__(
        self,
        *,
        source_capsule_digest: str,
        transaction_id: str,
        operations: Iterable[
            DatrixOperation
        ] = (),
    ) -> None:
        self._source_digest = str(
            source_capsule_digest
        ).strip()

        if not self._source_digest:
            raise DatrixTransactionError(
                "source capsule digest required"
            )

        self._transaction_id = (
            normalize_identifier(
                transaction_id,
                field="transaction_id",
            )
        )

        self._operations: dict[
            str,
            DatrixOperation,
        ] = {}

        for operation in operations:
            self.add(
                operation
            )

    def add(
        self,
        operation: DatrixOperation,
    ) -> DatrixOperation:
        if not isinstance(
            operation,
            DatrixOperation,
        ):
            raise DatrixTransactionError(
                "operation must be "
                "DatrixOperation"
            )

        existing = self._operations.get(
            operation.operation_id
        )

        if existing is not None:
            if (
                existing.manifest()[
                    "digest"
                ]
                != operation.manifest()[
                    "digest"
                ]
            ):
                raise DatrixTransactionError(
                    "operation identity collision: "
                    f"{operation.operation_id}"
                )

            return existing

        self._operations[
            operation.operation_id
        ] = operation

        return operation

    def _activation_order(
        self,
    ) -> tuple[str, ...]:
        known = set(
            self._operations
        )

        missing: dict[
            str,
            list[str],
        ] = {}

        indegree = {
            operation_id: 0
            for operation_id
            in known
        }

        outgoing = {
            operation_id: set()
            for operation_id
            in known
        }

        for operation in (
            self._operations.values()
        ):
            for dependency in (
                operation.dependencies
            ):
                if dependency not in known:
                    missing.setdefault(
                        operation.operation_id,
                        [],
                    ).append(
                        dependency
                    )

                    continue

                indegree[
                    operation.operation_id
                ] += 1

                outgoing[
                    dependency
                ].add(
                    operation.operation_id
                )

        if missing:
            raise DatrixTransactionError(
                "transaction has missing "
                "operation dependencies: "
                + canonical_json(
                    missing
                )
            )

        ready = sorted(
            operation_id
            for operation_id, degree
            in indegree.items()
            if degree == 0
        )

        order: list[str] = []

        while ready:
            current = ready.pop(0)

            order.append(
                current
            )

            for dependent in sorted(
                outgoing[current]
            ):
                indegree[
                    dependent
                ] -= 1

                if (
                    indegree[
                        dependent
                    ]
                    == 0
                ):
                    ready.append(
                        dependent
                    )

                    ready.sort()

        if len(order) != len(
            self._operations
        ):
            raise DatrixTransactionError(
                "transaction operation "
                "dependency cycle"
            )

        return tuple(
            order
        )

    def manifest(
        self,
    ) -> dict[str, Any]:
        order = (
            self._activation_order()
        )

        operations = [
            self._operations[
                operation_id
            ].manifest()
            for operation_id
            in order
        ]

        substance = {
            "schema":
                "savant.carbon.straub."
                "datrix-transaction-plan.v1",
            "kind":
                "datrix.transaction-plan",
            "id":
                self._transaction_id,
            "source_capsule_digest":
                self._source_digest,
            "operation_count":
                len(operations),
            "activation_order":
                list(order),
            "operations":
                operations,
            "mutation_performed":
                False,
            "semantic_authority":
                False,
            "replayable":
                True,
            "deterministic":
                True,
            "authority_effect":
                "none",
        }

        substance["digest"] = (
            stable_digest(
                substance
            )
        )

        return substance


class DatrixProjectionRegistry:
    def __init__(
        self,
    ) -> None:
        self._projectors: dict[
            str,
            Callable[
                [Mapping[str, Any]],
                Mapping[str, Any],
            ],
        ] = {}

    def register(
        self,
        projection_type: str,
        projector: Callable[
            [Mapping[str, Any]],
            Mapping[str, Any],
        ],
    ) -> None:
        normalized = normalize_identifier(
            projection_type,
            field="projection_type",
        )

        if not callable(
            projector
        ):
            raise DatrixProjectionError(
                "projector must be callable"
            )

        existing = self._projectors.get(
            normalized
        )

        if (
            existing is not None
            and existing is not projector
        ):
            raise DatrixProjectionError(
                "projection type already "
                "registered: "
                f"{normalized}"
            )

        self._projectors[
            normalized
        ] = projector

    def projection_types(
        self,
    ) -> tuple[str, ...]:
        return tuple(
            sorted(
                self._projectors
            )
        )

    def project(
        self,
        projection_type: str,
        capsule: Mapping[str, Any],
    ) -> dict[str, Any]:
        normalized = normalize_identifier(
            projection_type,
            field="projection_type",
        )

        projector = (
            self._projectors.get(
                normalized
            )
        )

        if projector is None:
            raise DatrixProjectionError(
                "unknown projection type: "
                f"{normalized}"
            )

        source_digest = (
            _capsule_digest(
                capsule
            )
        )

        raw = projector(
            capsule
        )

        if not isinstance(
            raw,
            Mapping,
        ):
            raise DatrixProjectionError(
                "projector must return mapping"
            )

        payload = _copy(
            dict(raw)
        )

        projection = {
            "schema":
                "savant.carbon.straub."
                "datrix-service-isotope.v1",
            "kind":
                "isotope",
            "projection_type":
                normalized,
            "source_capsule_digest":
                source_digest,
            "projection":
                payload,
            "projection_only":
                True,
            "semantic_authority":
                False,
            "rebuildable":
                True,
            "authority_effect":
                "none",
        }

        projection["digest"] = (
            stable_digest(
                projection
            )
        )

        return projection


class DatrixServiceSurface:
    def __init__(
        self,
        capsule: Mapping[str, Any],
    ) -> None:
        self._capsule = _copy(
            dict(capsule)
        )

        self._capsule_digest = (
            _capsule_digest(
                self._capsule
            )
        )

        self._index = (
            DatrixDeterministicIndex(
                self._capsule
            )
        )

        self._adapters = (
            DatrixAdapterRegistry()
        )

        self._projections = (
            DatrixProjectionRegistry()
        )

        self._projections.register(
            "index",
            lambda source: (
                DatrixDeterministicIndex(
                    source
                ).projection()
            ),
        )

    @property
    def capsule_digest(
        self,
    ) -> str:
        return self._capsule_digest

    @property
    def index(
        self,
    ) -> DatrixDeterministicIndex:
        return self._index

    @property
    def adapters(
        self,
    ) -> DatrixAdapterRegistry:
        return self._adapters

    @property
    def projections(
        self,
    ) -> DatrixProjectionRegistry:
        return self._projections

    def transaction(
        self,
        transaction_id: str,
        operations: Iterable[
            DatrixOperation
        ] = (),
    ) -> DatrixTransactionPlan:
        return DatrixTransactionPlan(
            source_capsule_digest=(
                self._capsule_digest
            ),
            transaction_id=(
                transaction_id
            ),
            operations=operations,
        )

    def health(
        self,
    ) -> dict[str, Any]:
        index_projection = (
            self._index.projection()
        )

        adapters = (
            self._adapters.manifest()
        )

        result = {
            "schema":
                "savant.carbon.straub."
                "datrix-services-health.v1",
            "status":
                "ok",
            "source_capsule_digest":
                self._capsule_digest,
            "index_digest":
                index_projection[
                    "digest"
                ],
            "record_count":
                index_projection[
                    "record_count"
                ],
            "adapter_registry_digest":
                adapters[
                    "digest"
                ],
            "adapter_count":
                adapters[
                    "adapter_count"
                ],
            "projection_types":
                list(
                    self._projections
                    .projection_types()
                ),
            "deterministic":
                True,
            "rebuildable":
                True,
            "transaction_plans_mutate":
                False,
            "adapter_semantic_authority":
                False,
            "storage_engine_selected":
                False,
            "database_engine":
                None,
            "semantic_authority":
                "canonical datrix substance",
            "authority_effect":
                "none",
        }

        result["digest"] = (
            stable_digest(
                result
            )
        )

        return result
