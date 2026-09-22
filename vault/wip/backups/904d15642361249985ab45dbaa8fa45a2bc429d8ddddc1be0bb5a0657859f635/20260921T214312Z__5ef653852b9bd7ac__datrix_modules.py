#!/usr/bin/env python3

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
import hashlib
import json
import re
from typing import Any, Iterable, Mapping


schema = "savant.carbon.straub.datrix-modules.v1"
owner = "carbon"
module = "straub"
authority_effect = "none"

_identifier_pattern = re.compile(
    r"^[a-z0-9][a-z0-9._:-]*$"
)

_version_pattern = re.compile(
    r"^(0|[1-9][0-9]*)\."
    r"(0|[1-9][0-9]*)\."
    r"(0|[1-9][0-9]*)$"
)


class DatrixModuleError(
    ValueError
):
    pass


class DatrixModuleConflictError(
    DatrixModuleError
):
    pass


class DatrixModuleDependencyError(
    DatrixModuleError
):
    pass


def _canonical_json(
    value: Any,
) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(
            ",",
            ":",
        ),
    )


def _digest(
    value: Any,
) -> str:
    return hashlib.sha256(
        _canonical_json(
            value
        ).encode(
            "utf-8"
        )
    ).hexdigest()


def _identifier(
    value: Any,
    *,
    field: str,
) -> str:
    normalized = str(
        value
        or ""
    ).strip().casefold()

    if not normalized:
        raise DatrixModuleError(
            f"{field} is required"
        )

    if (
        _identifier_pattern.fullmatch(
            normalized
        )
        is None
    ):
        raise DatrixModuleError(
            f"{field} contains invalid characters: "
            f"{normalized!r}"
        )

    return normalized


def _version(
    value: Any,
) -> str:
    normalized = str(
        value
        or ""
    ).strip()

    if (
        _version_pattern.fullmatch(
            normalized
        )
        is None
    ):
        raise DatrixModuleError(
            "version must use major.minor.patch"
        )

    return normalized


def _version_tuple(
    value: str,
) -> tuple[int, int, int]:
    match = _version_pattern.fullmatch(
        value
    )

    if match is None:
        raise DatrixModuleError(
            f"invalid semantic version: {value!r}"
        )

    return tuple(
        int(
            item
        )
        for item
        in match.groups()
    )


def _string_set(
    values: Iterable[Any] | None,
    *,
    field: str,
) -> tuple[str, ...]:
    normalized = {
        _identifier(
            value,
            field=field,
        )
        for value
        in (
            values
            or ()
        )
    }

    return tuple(
        sorted(
            normalized
        )
    )


def _mapping(
    value: Mapping[str, Any] | None,
) -> dict[str, Any]:
    if value is None:
        return {}

    if not isinstance(
        value,
        Mapping,
    ):
        raise DatrixModuleError(
            "mapping value required"
        )

    return deepcopy(
        dict(
            value
        )
    )


@dataclass(
    frozen=True,
    slots=True,
)
class DatrixModule:
    module_id: str
    version: str
    owner: str
    capabilities: tuple[str, ...]
    provides: tuple[str, ...]
    requires: tuple[str, ...]
    conflicts: tuple[str, ...]
    extension_points: tuple[str, ...]
    configuration_schema: dict[str, Any]
    provenance: dict[str, Any]
    lineage: dict[str, Any]
    status: str = "active"

    @classmethod
    def create(
        cls,
        *,
        module_id: str,
        version: str,
        owner: str = "carbon.straub",
        capabilities: Iterable[str] | None = None,
        provides: Iterable[str] | None = None,
        requires: Iterable[str] | None = None,
        conflicts: Iterable[str] | None = None,
        extension_points: Iterable[str] | None = None,
        configuration_schema: Mapping[
            str,
            Any,
        ] | None = None,
        provenance: Mapping[
            str,
            Any,
        ] | None = None,
        lineage: Mapping[
            str,
            Any,
        ] | None = None,
        status: str = "active",
    ) -> "DatrixModule":
        normalized_id = _identifier(
            module_id,
            field="module_id",
        )

        normalized_owner = _identifier(
            owner,
            field="owner",
        )

        normalized_status = _identifier(
            status,
            field="status",
        )

        normalized_requires = _string_set(
            requires,
            field="requires",
        )

        normalized_conflicts = _string_set(
            conflicts,
            field="conflicts",
        )

        if normalized_id in normalized_requires:
            raise DatrixModuleDependencyError(
                "module cannot require itself"
            )

        if normalized_id in normalized_conflicts:
            raise DatrixModuleConflictError(
                "module cannot conflict with itself"
            )

        return cls(
            module_id=normalized_id,
            version=_version(
                version
            ),
            owner=normalized_owner,
            capabilities=_string_set(
                capabilities,
                field="capabilities",
            ),
            provides=_string_set(
                provides,
                field="provides",
            ),
            requires=normalized_requires,
            conflicts=normalized_conflicts,
            extension_points=_string_set(
                extension_points,
                field="extension_points",
            ),
            configuration_schema=_mapping(
                configuration_schema
            ),
            provenance=_mapping(
                provenance
            ),
            lineage=_mapping(
                lineage
            ),
            status=normalized_status,
        )

    def manifest(
        self,
    ) -> dict[str, Any]:
        substance = {
            "schema":
                "savant.carbon.straub."
                "datrix-module.v1",
            "kind":
                "datrix.module",
            "id":
                self.module_id,
            "version":
                self.version,
            "owner":
                self.owner,
            "status":
                self.status,
            "capabilities":
                list(
                    self.capabilities
                ),
            "provides":
                list(
                    self.provides
                ),
            "requires":
                list(
                    self.requires
                ),
            "conflicts":
                list(
                    self.conflicts
                ),
            "extension_points":
                list(
                    self.extension_points
                ),
            "configuration_schema":
                deepcopy(
                    self.configuration_schema
                ),
            "provenance":
                deepcopy(
                    self.provenance
                ),
            "lineage":
                deepcopy(
                    self.lineage
                ),
            "authority_effect":
                "none",
        }

        substance[
            "digest"
        ] = _digest(
            substance
        )

        return substance


class DatrixModuleSet:
    """
    Deterministic capability composition for a Datrix.

    Modules describe optional capability composition.
    They do not own canonical Datrix substance and do
    not become semantic authority.

    The module set is derived configuration. It is safe
    to rebuild from the same descriptors.
    """

    def __init__(
        self,
        modules: Iterable[
            DatrixModule
        ] = (),
    ) -> None:
        self._modules: dict[
            str,
            DatrixModule,
        ] = {}

        for item in modules:
            self.register(
                item
            )

    def register(
        self,
        descriptor: DatrixModule,
    ) -> DatrixModule:
        if not isinstance(
            descriptor,
            DatrixModule,
        ):
            raise DatrixModuleError(
                "descriptor must be DatrixModule"
            )

        existing = self._modules.get(
            descriptor.module_id
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
                raise DatrixModuleConflictError(
                    "module identity already contains "
                    "different substance: "
                    f"{descriptor.module_id}"
                )

            return existing

        self._modules[
            descriptor.module_id
        ] = descriptor

        return descriptor

    def module(
        self,
        module_id: str,
    ) -> DatrixModule | None:
        return self._modules.get(
            _identifier(
                module_id,
                field="module_id",
            )
        )

    def modules(
        self,
    ) -> tuple[DatrixModule, ...]:
        return tuple(
            self._modules[
                module_id
            ]
            for module_id
            in sorted(
                self._modules
            )
        )

    def capabilities(
        self,
    ) -> tuple[str, ...]:
        return tuple(
            sorted(
                {
                    capability
                    for descriptor
                    in self._modules.values()
                    for capability
                    in descriptor.capabilities
                }
            )
        )

    def interfaces(
        self,
    ) -> tuple[str, ...]:
        return tuple(
            sorted(
                {
                    interface
                    for descriptor
                    in self._modules.values()
                    for interface
                    in descriptor.provides
                }
            )
        )

    def providers(
        self,
        interface: str,
    ) -> tuple[str, ...]:
        normalized = _identifier(
            interface,
            field="interface",
        )

        return tuple(
            sorted(
                descriptor.module_id
                for descriptor
                in self._modules.values()
                if normalized
                in descriptor.provides
            )
        )

    def dependents(
        self,
        module_id: str,
    ) -> tuple[str, ...]:
        normalized = _identifier(
            module_id,
            field="module_id",
        )

        return tuple(
            sorted(
                descriptor.module_id
                for descriptor
                in self._modules.values()
                if normalized
                in descriptor.requires
            )
        )

    def dependency_closure(
        self,
        module_id: str,
    ) -> tuple[str, ...]:
        normalized = _identifier(
            module_id,
            field="module_id",
        )

        if normalized not in self._modules:
            raise DatrixModuleDependencyError(
                "unknown module: "
                f"{normalized}"
            )

        result: set[str] = set()
        pending = [
            normalized
        ]

        while pending:
            current = pending.pop()

            for dependency in (
                self._modules[
                    current
                ].requires
            ):
                if dependency in result:
                    continue

                result.add(
                    dependency
                )

                if dependency in self._modules:
                    pending.append(
                        dependency
                    )

        result.discard(
            normalized
        )

        return tuple(
            sorted(
                result
            )
        )

    def missing_dependencies(
        self,
    ) -> dict[str, tuple[str, ...]]:
        result: dict[
            str,
            tuple[str, ...],
        ] = {}

        known = set(
            self._modules
        )

        for descriptor in self.modules():
            missing = tuple(
                dependency
                for dependency
                in descriptor.requires
                if dependency
                not in known
            )

            if missing:
                result[
                    descriptor.module_id
                ] = missing

        return result

    def conflicts(
        self,
    ) -> tuple[
        tuple[str, str],
        ...,
    ]:
        result: set[
            tuple[str, str]
        ] = set()

        known = set(
            self._modules
        )

        for descriptor in self.modules():
            for conflict in (
                descriptor.conflicts
            ):
                if conflict not in known:
                    continue

                result.add(
                    tuple(
                        sorted(
                            (
                                descriptor.module_id,
                                conflict,
                            )
                        )
                    )
                )

        return tuple(
            sorted(
                result
            )
        )

    def cycles(
        self,
    ) -> tuple[
        tuple[str, ...],
        ...,
    ]:
        visiting: set[str] = set()
        visited: set[str] = set()
        stack: list[str] = []
        found: set[
            tuple[str, ...]
        ] = set()

        def visit(
            module_id: str,
        ) -> None:
            if module_id in visited:
                return

            if module_id in visiting:
                try:
                    start = stack.index(
                        module_id
                    )
                except ValueError:
                    return

                cycle = tuple(
                    stack[
                        start:
                    ]
                    + [
                        module_id
                    ]
                )

                found.add(
                    cycle
                )

                return

            visiting.add(
                module_id
            )

            stack.append(
                module_id
            )

            for dependency in (
                self._modules[
                    module_id
                ].requires
            ):
                if dependency in self._modules:
                    visit(
                        dependency
                    )

            stack.pop()

            visiting.remove(
                module_id
            )

            visited.add(
                module_id
            )

        for module_id in sorted(
            self._modules
        ):
            visit(
                module_id
            )

        return tuple(
            sorted(
                found
            )
        )

    def activation_order(
        self,
    ) -> tuple[str, ...]:
        missing = (
            self.missing_dependencies()
        )

        if missing:
            raise DatrixModuleDependencyError(
                "missing module dependencies: "
                + _canonical_json(
                    missing
                )
            )

        conflicts = self.conflicts()

        if conflicts:
            raise DatrixModuleConflictError(
                "module conflicts: "
                + _canonical_json(
                    conflicts
                )
            )

        cycles = self.cycles()

        if cycles:
            raise DatrixModuleDependencyError(
                "module dependency cycle: "
                + _canonical_json(
                    cycles
                )
            )

        indegree = {
            module_id: 0
            for module_id
            in self._modules
        }

        outgoing = {
            module_id: set()
            for module_id
            in self._modules
        }

        for descriptor in self.modules():
            for dependency in (
                descriptor.requires
            ):
                outgoing[
                    dependency
                ].add(
                    descriptor.module_id
                )

                indegree[
                    descriptor.module_id
                ] += 1

        ready = sorted(
            module_id
            for (
                module_id,
                degree,
            )
            in indegree.items()
            if degree == 0
        )

        order: list[str] = []

        while ready:
            current = ready.pop(
                0
            )

            order.append(
                current
            )

            for dependent in sorted(
                outgoing[
                    current
                ]
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

        if len(
            order
        ) != len(
            self._modules
        ):
            raise DatrixModuleDependencyError(
                "module graph could not be "
                "deterministically ordered"
            )

        return tuple(
            order
        )

    def compatible(
        self,
    ) -> bool:
        return (
            not self.missing_dependencies()
            and not self.conflicts()
            and not self.cycles()
        )

    def manifest(
        self,
    ) -> dict[str, Any]:
        descriptors = [
            descriptor.manifest()
            for descriptor
            in self.modules()
        ]

        substance = {
            "schema":
                schema,
            "kind":
                "datrix.module-set",
            "modules":
                descriptors,
            "module_count":
                len(
                    descriptors
                ),
            "capabilities":
                list(
                    self.capabilities()
                ),
            "interfaces":
                list(
                    self.interfaces()
                ),
            "missing_dependencies":
                {
                    key:
                        list(
                            value
                        )
                    for (
                        key,
                        value,
                    )
                    in self
                    .missing_dependencies()
                    .items()
                },
            "conflicts": [
                list(
                    pair
                )
                for pair
                in self.conflicts()
            ],
            "cycles": [
                list(
                    cycle
                )
                for cycle
                in self.cycles()
            ],
            "compatible":
                self.compatible(),
            "authority_effect":
                "none",
        }

        if substance[
            "compatible"
        ]:
            substance[
                "activation_order"
            ] = list(
                self.activation_order()
            )
        else:
            substance[
                "activation_order"
            ] = []

        substance[
            "digest"
        ] = _digest(
            substance
        )

        return substance

    def fingerprint(
        self,
    ) -> str:
        return self.manifest()[
            "digest"
        ]

    def health(
        self,
    ) -> dict[str, Any]:
        manifest = self.manifest()

        return {
            "schema":
                "savant.carbon.straub."
                "datrix-modules-health.v1",
            "status":
                (
                    "ok"
                    if manifest[
                        "compatible"
                    ]
                    else "degraded"
                ),
            "module_count":
                manifest[
                    "module_count"
                ],
            "capability_count":
                len(
                    manifest[
                        "capabilities"
                    ]
                ),
            "interface_count":
                len(
                    manifest[
                        "interfaces"
                    ]
                ),
            "missing_dependencies":
                manifest[
                    "missing_dependencies"
                ],
            "conflicts":
                manifest[
                    "conflicts"
                ],
            "cycles":
                manifest[
                    "cycles"
                ],
            "activation_order":
                manifest[
                    "activation_order"
                ],
            "fingerprint":
                manifest[
                    "digest"
                ],
            "semantic_authority":
                False,
            "rebuildable":
                True,
            "deterministic":
                True,
            "authority_effect":
                "none",
        }


def core_datrix_modules() -> DatrixModuleSet:
    return DatrixModuleSet(
        (
            DatrixModule.create(
                module_id=(
                    "carbon.straub.datrix.dyad"
                ),
                version="1.0.0",
                capabilities=(
                    "composition.dyad",
                    "semantic.pairing",
                ),
                provides=(
                    "datrix.dyad",
                ),
                provenance={
                    "source":
                        "straub.datrix",
                },
            ),
            DatrixModule.create(
                module_id=(
                    "carbon.straub.datrix.umbra"
                ),
                version="1.0.0",
                capabilities=(
                    "metadata.definition",
                    "metadata.instance",
                    "metadata.validation",
                    "metadata.validity",
                    "metadata.composition",
                ),
                provides=(
                    "datrix.umbra",
                    "datrix.metadata",
                ),
                provenance={
                    "source":
                        "straub.registry",
                },
            ),
            DatrixModule.create(
                module_id=(
                    "carbon.straub.datrix.membrane"
                ),
                version="1.0.0",
                capabilities=(
                    "relationship.typed",
                    "relationship.directed",
                    "metadata.attachment",
                ),
                provides=(
                    "datrix.membrane",
                ),
                requires=(
                    "carbon.straub.datrix.umbra",
                ),
                provenance={
                    "source":
                        "straub.registry",
                },
            ),
            DatrixModule.create(
                module_id=(
                    "carbon.straub.datrix.isotope"
                ),
                version="1.0.0",
                capabilities=(
                    "projection.deterministic",
                    "projection.rebuildable",
                    "projection.content-addressed",
                ),
                provides=(
                    "datrix.isotope",
                    "datrix.projection",
                ),
                provenance={
                    "source":
                        "straub.isotope",
                },
            ),
            DatrixModule.create(
                module_id=(
                    "carbon.straub.datrix.query"
                ),
                version="1.0.0",
                capabilities=(
                    "query.deterministic",
                    "query.explicit-time",
                ),
                provides=(
                    "datrix.query",
                ),
                provenance={
                    "source":
                        "straub.query",
                },
            ),
            DatrixModule.create(
                module_id=(
                    "carbon.straub.datrix.dependencies"
                ),
                version="1.0.0",
                capabilities=(
                    "dependency.index",
                    "dependency.reverse-index",
                ),
                provides=(
                    "datrix.dependencies",
                ),
                provenance={
                    "source":
                        "straub.dependency",
                },
            ),
            DatrixModule.create(
                module_id=(
                    "carbon.straub.datrix.custody"
                ),
                version="1.0.0",
                capabilities=(
                    "custody.atomic",
                    "custody.redundant",
                    "custody.compare-and-swap",
                    "custody.recovery",
                    "custody.interprocess-locking",
                ),
                provides=(
                    "datrix.custody",
                ),
                provenance={
                    "source":
                        "straub.resilience",
                },
            ),
        )
    )
