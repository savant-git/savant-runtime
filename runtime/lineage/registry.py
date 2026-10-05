#!/usr/bin/env python3
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
import json
import os
from pathlib import Path
from typing import Any, Mapping

from .model import LineageValidationError


SAVANT_ROOT = Path(
    os.environ.get(
        "SAVANT_ROOT",
        "/root/savant-runtime",
    )
).resolve()

DEFAULT_ROLE_REGISTRY = (
    SAVANT_ROOT
    / "authority_graph"
    / "roles"
    / "lineage_role_registry.json"
)


@dataclass(frozen=True, slots=True)
class RoleDefinition:
    name: str
    axis: str
    inverse: str
    aliases: tuple[str, ...]
    precedence: int
    acyclic: bool
    cycle_domain: str
    propagates_changes: bool
    default_inheritance: Mapping[str, Any]
    symbolic_parent_alias: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "axis": self.axis,
            "inverse": self.inverse,
            "aliases": list(self.aliases),
            "precedence": self.precedence,
            "acyclic": self.acyclic,
            "cycle_domain": self.cycle_domain,
            "propagates_changes": self.propagates_changes,
            "default_inheritance": deepcopy(
                dict(self.default_inheritance)
            ),
            "symbolic_parent_alias": self.symbolic_parent_alias,
        }


def _deep_merge(
    base: Mapping[str, Any],
    overlay: Mapping[str, Any],
) -> dict[str, Any]:
    result = deepcopy(dict(base))

    for key, value in overlay.items():
        if (
            key in result
            and isinstance(result[key], Mapping)
            and isinstance(value, Mapping)
        ):
            result[key] = _deep_merge(
                result[key],
                value,
            )
        else:
            result[key] = deepcopy(value)

    return result


def _load_registry_payload(
    path: Path,
    *,
    stack: tuple[Path, ...] = (),
) -> tuple[dict[str, Any], tuple[Path, ...]]:
    source = path.expanduser().resolve()

    if source in stack:
        chain = " -> ".join(
            str(item)
            for item in (*stack, source)
        )

        raise LineageValidationError(
            f"lineage role registry import cycle: {chain}"
        )

    if not source.is_file():
        raise LineageValidationError(
            f"lineage role registry missing: {source}"
        )

    try:
        payload = json.loads(
            source.read_text(
                encoding="utf-8"
            )
        )
    except (
        OSError,
        UnicodeError,
        json.JSONDecodeError,
    ) as exc:
        raise LineageValidationError(
            "cannot read lineage role registry "
            f"{source}: {exc}"
        ) from exc

    if not isinstance(payload, Mapping):
        raise LineageValidationError(
            "lineage role registry must be "
            f"an object: {source}"
        )

    merged: dict[str, Any] = {
        "roles": {},
        "continuation_modes": {},
    }

    sources: list[Path] = []

    imports = payload.get(
        "imports",
        [],
    )

    if imports is None:
        imports = []

    if not isinstance(imports, list):
        raise LineageValidationError(
            "lineage role registry imports "
            f"must be an array: {source}"
        )

    for raw_import in imports:
        if (
            not isinstance(raw_import, str)
            or not raw_import.strip()
        ):
            raise LineageValidationError(
                "invalid lineage role registry "
                f"import in {source}"
            )

        imported_path = Path(
            raw_import
        )

        if not imported_path.is_absolute():
            imported_path = (
                source.parent
                / imported_path
            )

        imported, imported_sources = (
            _load_registry_payload(
                imported_path,
                stack=(
                    *stack,
                    source,
                ),
            )
        )

        merged = _deep_merge(
            merged,
            imported,
        )

        for imported_source in imported_sources:
            if imported_source not in sources:
                sources.append(
                    imported_source
                )

    local_payload = {
        key: value
        for key, value in payload.items()
        if key != "imports"
    }

    merged = _deep_merge(
        merged,
        local_payload,
    )

    if source not in sources:
        sources.append(
            source
        )

    return merged, tuple(sources)


class LineageRoleRegistry:
    def __init__(
        self,
        roles: Mapping[
            str,
            RoleDefinition,
        ],
        aliases: Mapping[
            str,
            str,
        ],
        continuation_modes: Mapping[
            str,
            Mapping[str, Any],
        ],
        *,
        source_path: Path | None = None,
        source_paths: tuple[Path, ...] = (),
        version: str = "",
        registry_id: str = "",
    ) -> None:
        self._roles = dict(
            roles
        )

        self._aliases = dict(
            aliases
        )

        self._continuation_modes = {
            key: deepcopy(
                dict(value)
            )
            for key, value
            in continuation_modes.items()
        }

        self.source_path = source_path
        self.source_paths = tuple(
            source_paths
        )
        self.version = version
        self.registry_id = registry_id

    @classmethod
    def load(
        cls,
        path: Path | str = (
            DEFAULT_ROLE_REGISTRY
        ),
    ) -> "LineageRoleRegistry":
        source = Path(
            path
        ).expanduser().resolve()

        payload, source_paths = (
            _load_registry_payload(
                source
            )
        )

        role_payload = payload.get(
            "roles"
        )

        if (
            not isinstance(
                role_payload,
                Mapping,
            )
            or not role_payload
        ):
            raise LineageValidationError(
                "lineage role registry "
                "has no roles"
            )

        roles: dict[
            str,
            RoleDefinition,
        ] = {}

        aliases: dict[
            str,
            str,
        ] = {}

        for (
            raw_name,
            raw_definition,
        ) in role_payload.items():
            name = str(
                raw_name
            ).strip()

            if (
                not name
                or not isinstance(
                    raw_definition,
                    Mapping,
                )
            ):
                raise LineageValidationError(
                    "invalid lineage "
                    "role definition"
                )

            role_aliases = tuple(
                str(alias).strip()
                for alias
                in raw_definition.get(
                    "aliases",
                    [],
                )
                if str(alias).strip()
            )

            precedence = (
                raw_definition.get(
                    "precedence",
                    0,
                )
            )

            if (
                isinstance(
                    precedence,
                    bool,
                )
                or not isinstance(
                    precedence,
                    int,
                )
            ):
                raise LineageValidationError(
                    f"lineage role {name} "
                    "precedence must be integer"
                )

            acyclic = (
                raw_definition.get(
                    "acyclic",
                    True,
                )
            )

            propagates = (
                raw_definition.get(
                    "propagates_changes",
                    True,
                )
            )

            if not isinstance(
                acyclic,
                bool,
            ):
                raise LineageValidationError(
                    f"lineage role {name} "
                    "acyclic must be boolean"
                )

            if not isinstance(
                propagates,
                bool,
            ):
                raise LineageValidationError(
                    f"lineage role {name} "
                    "propagates_changes "
                    "must be boolean"
                )

            default_inheritance = (
                raw_definition.get(
                    "default_inheritance",
                    {},
                )
            )

            if not isinstance(
                default_inheritance,
                Mapping,
            ):
                raise LineageValidationError(
                    f"lineage role {name} "
                    "default_inheritance "
                    "must be an object"
                )

            definition = RoleDefinition(
                name=name,
                axis=str(
                    raw_definition.get(
                        "axis",
                        "unspecified",
                    )
                ),
                inverse=str(
                    raw_definition.get(
                        "inverse",
                        "generic_child",
                    )
                ),
                aliases=role_aliases,
                precedence=precedence,
                acyclic=acyclic,
                cycle_domain=str(
                    raw_definition.get(
                        "cycle_domain",
                        name,
                    )
                ),
                propagates_changes=(
                    propagates
                ),
                default_inheritance=(
                    deepcopy(
                        dict(
                            default_inheritance
                        )
                    )
                ),
                symbolic_parent_alias=(
                    str(
                        raw_definition[
                            "symbolic_parent_alias"
                        ]
                    )
                    if raw_definition.get(
                        "symbolic_parent_alias"
                    )
                    else None
                ),
            )

            roles[name] = definition

            for alias in (
                name,
                *role_aliases,
            ):
                normalized = (
                    alias.casefold()
                )

                existing = aliases.get(
                    normalized
                )

                if (
                    existing is not None
                    and existing != name
                ):
                    raise LineageValidationError(
                        "lineage role alias "
                        f"collision: {alias}"
                    )

                aliases[
                    normalized
                ] = name

        continuation_modes = (
            payload.get(
                "continuation_modes",
                {},
            )
        )

        if not isinstance(
            continuation_modes,
            Mapping,
        ):
            raise LineageValidationError(
                "continuation_modes "
                "must be an object"
            )

        for (
            mode_name,
            mode_definition,
        ) in continuation_modes.items():
            if (
                not isinstance(
                    mode_name,
                    str,
                )
                or not mode_name.strip()
            ):
                raise LineageValidationError(
                    "continuation mode names "
                    "must be non-empty strings"
                )

            if not isinstance(
                mode_definition,
                Mapping,
            ):
                raise LineageValidationError(
                    "continuation mode "
                    f"{mode_name} must be "
                    "an object"
                )

        return cls(
            roles,
            aliases,
            continuation_modes,
            source_path=source,
            source_paths=source_paths,
            version=str(
                payload.get(
                    "version",
                    "",
                )
            ),
            registry_id=str(
                payload.get(
                    "id",
                    "",
                )
            ),
        )

    def canonical_name(
        self,
        role_or_alias: str,
    ) -> str:
        normalized = str(
            role_or_alias
        ).strip().casefold()

        if not normalized:
            normalized = "generic"

        canonical = self._aliases.get(
            normalized
        )

        if canonical is None:
            raise LineageValidationError(
                "unknown lineage role: "
                f"{role_or_alias}"
            )

        return canonical

    def has(
        self,
        role_or_alias: str,
    ) -> bool:
        try:
            self.canonical_name(
                role_or_alias
            )
        except LineageValidationError:
            return False

        return True

    def get(
        self,
        role_or_alias: str,
    ) -> RoleDefinition:
        return self._roles[
            self.canonical_name(
                role_or_alias
            )
        ]

    def symbolic_parent_alias(
        self,
        role_or_alias: str,
    ) -> str:
        definition = self.get(
            role_or_alias
        )

        return (
            definition.symbolic_parent_alias
            or "parent"
        )

    def symbolic_child_alias(
        self,
        continuation: str,
    ) -> str:
        definition = (
            self._continuation_modes.get(
                continuation
            )
        )

        if not definition:
            raise LineageValidationError(
                "unknown lineage "
                "continuation mode: "
                f"{continuation}"
            )

        return str(
            definition.get(
                "symbolic_child_alias",
                "child",
            )
        )

    def roles(
        self,
    ) -> tuple[
        RoleDefinition,
        ...,
    ]:
        return tuple(
            sorted(
                self._roles.values(),
                key=lambda role: (
                    role.precedence,
                    role.name,
                ),
            )
        )

    def to_dict(
        self,
    ) -> dict[str, Any]:
        return {
            "id": self.registry_id,
            "version": self.version,
            "source": (
                str(
                    self.source_path
                )
                if self.source_path
                else None
            ),
            "sources": [
                str(path)
                for path
                in self.source_paths
            ],
            "roles": {
                role.name: (
                    role.to_dict()
                )
                for role in self.roles()
            },
            "continuation_modes": (
                deepcopy(
                    self._continuation_modes
                )
            ),
        }
