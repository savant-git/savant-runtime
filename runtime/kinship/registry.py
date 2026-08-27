#!/usr/bin/env python3
from __future__ import annotations

from copy import deepcopy
import json
import os
from pathlib import Path
from typing import Any, Mapping

from .model import (
    KinshipValidationError,
)


ROOT = Path(
    os.environ.get(
        "SAVANT_ROOT",
        "/root/savant-runtime",
    )
).expanduser().resolve()

DEFAULT_KINSHIP_REGISTRY = (
    ROOT
    / "authority_graph"
    / "kinship"
    / "kinship_registry.json"
)


def _deep_merge(
    base: Mapping[str, Any],
    overlay: Mapping[str, Any],
) -> dict[str, Any]:
    result = deepcopy(
        dict(base)
    )

    for key, value in overlay.items():
        if (
            key in result
            and isinstance(
                result[key],
                Mapping,
            )
            and isinstance(
                value,
                Mapping,
            )
        ):
            result[key] = _deep_merge(
                result[key],
                value,
            )
        else:
            result[key] = deepcopy(
                value
            )

    return result


def _load_payload(
    path: Path,
    *,
    stack: tuple[Path, ...] = (),
) -> tuple[
    dict[str, Any],
    tuple[Path, ...],
]:
    source = path.expanduser().resolve()

    if source in stack:
        chain = " -> ".join(
            str(item)
            for item in (
                *stack,
                source,
            )
        )

        raise KinshipValidationError(
            "kinship registry import "
            f"cycle: {chain}"
        )

    if not source.is_file():
        raise KinshipValidationError(
            "kinship registry missing: "
            f"{source}"
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
        raise KinshipValidationError(
            "cannot read kinship registry "
            f"{source}: {exc}"
        ) from exc

    if not isinstance(
        payload,
        Mapping,
    ):
        raise KinshipValidationError(
            "kinship registry must be "
            f"an object: {source}"
        )

    merged: dict[str, Any] = {}
    sources: list[Path] = []

    imports = payload.get(
        "imports",
        [],
    )

    if imports is None:
        imports = []

    if not isinstance(
        imports,
        list,
    ):
        raise KinshipValidationError(
            "kinship registry imports "
            "must be an array"
        )

    for raw_import in imports:
        if (
            not isinstance(
                raw_import,
                str,
            )
            or not raw_import.strip()
        ):
            raise KinshipValidationError(
                "invalid kinship registry "
                "import"
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
            _load_payload(
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

        for imported_source in (
            imported_sources
        ):
            if imported_source not in sources:
                sources.append(
                    imported_source
                )

    merged = _deep_merge(
        merged,
        {
            key: value
            for key, value
            in payload.items()
            if key != "imports"
        },
    )

    if source not in sources:
        sources.append(
            source
        )

    return (
        merged,
        tuple(
            sources
        ),
    )


class KinshipRegistry:
    def __init__(
        self,
        payload: Mapping[str, Any],
        *,
        source_path: Path,
        source_paths: tuple[Path, ...],
    ) -> None:
        self.payload = deepcopy(
            dict(payload)
        )

        self.source_path = (
            source_path
        )

        self.source_paths = (
            source_paths
        )

        self.registry_id = str(
            payload.get(
                "id",
                "",
            )
        )

        self.version = str(
            payload.get(
                "version",
                "",
            )
        )

        self._planes = self._section(
            "relationship_planes"
        )

        self._parent_profiles = (
            self._section(
                "parent_profiles"
            )
        )

        self._child_profiles = (
            self._section(
                "child_profiles"
            )
        )

        self._alliance_profiles = (
            self._section(
                "alliance_profiles"
            )
        )

        self._derived_profiles = (
            self._section(
                "derived_profiles"
            )
        )

        legacy = payload.get(
            "legacy_defaults",
            {},
        )

        if not isinstance(
            legacy,
            Mapping,
        ):
            raise KinshipValidationError(
                "legacy_defaults must "
                "be an object"
            )

        self._legacy_parent = {
            str(key): str(value)
            for key, value
            in dict(
                legacy.get(
                    "parent_profile_by_role",
                    {},
                )
            ).items()
        }

        self._legacy_child = {
            str(key): str(value)
            for key, value
            in dict(
                legacy.get(
                    "child_profile_by_continuation",
                    {},
                )
            ).items()
        }

        states = payload.get(
            "relationship_states",
            [],
        )

        if not isinstance(
            states,
            list,
        ):
            raise KinshipValidationError(
                "relationship_states "
                "must be an array"
            )

        self.relationship_states = tuple(
            str(state)
            for state in states
        )

        self._validate_defaults()

    @classmethod
    def load(
        cls,
        path: Path | str = (
            DEFAULT_KINSHIP_REGISTRY
        ),
    ) -> "KinshipRegistry":
        source = Path(
            path
        ).expanduser().resolve()

        payload, sources = (
            _load_payload(
                source
            )
        )

        return cls(
            payload,
            source_path=source,
            source_paths=sources,
        )

    def _section(
        self,
        name: str,
    ) -> dict[
        str,
        dict[str, Any],
    ]:
        section = self.payload.get(
            name,
            {},
        )

        if not isinstance(
            section,
            Mapping,
        ):
            raise KinshipValidationError(
                f"{name} must be an object"
            )

        result: dict[
            str,
            dict[str, Any],
        ] = {}

        for key, value in section.items():
            normalized = str(
                key
            ).strip()

            if (
                not normalized
                or not isinstance(
                    value,
                    Mapping,
                )
            ):
                raise KinshipValidationError(
                    f"invalid {name} entry"
                )

            result[
                normalized
            ] = deepcopy(
                dict(value)
            )

        return result

    def _validate_defaults(
        self,
    ) -> None:
        for role, profile in (
            self._legacy_parent.items()
        ):
            if (
                profile
                not in self._parent_profiles
            ):
                raise KinshipValidationError(
                    "legacy role default "
                    f"{role} references "
                    f"unknown parent profile "
                    f"{profile}"
                )

        for continuation, profile in (
            self._legacy_child.items()
        ):
            if (
                profile
                not in self._child_profiles
            ):
                raise KinshipValidationError(
                    "legacy continuation "
                    f"default {continuation} "
                    "references unknown child "
                    f"profile {profile}"
                )

    def parent_profile(
        self,
        name: str,
    ) -> dict[str, Any]:
        try:
            return deepcopy(
                self._parent_profiles[
                    name
                ]
            )
        except KeyError as exc:
            raise KinshipValidationError(
                "unknown parent profile: "
                f"{name}"
            ) from exc

    def child_profile(
        self,
        name: str,
    ) -> dict[str, Any]:
        try:
            return deepcopy(
                self._child_profiles[
                    name
                ]
            )
        except KeyError as exc:
            raise KinshipValidationError(
                "unknown child profile: "
                f"{name}"
            ) from exc

    def alliance_profile(
        self,
        name: str,
    ) -> dict[str, Any]:
        try:
            return deepcopy(
                self._alliance_profiles[
                    name
                ]
            )
        except KeyError as exc:
            raise KinshipValidationError(
                "unknown alliance profile: "
                f"{name}"
            ) from exc

    def derived_profile(
        self,
        name: str,
    ) -> dict[str, Any]:
        return deepcopy(
            self._derived_profiles.get(
                name,
                {
                    "meaning": (
                        "Derived functional "
                        "kinship relationship."
                    )
                },
            )
        )

    def default_parent_profile(
        self,
        role: str,
    ) -> str:
        return self._legacy_parent.get(
            str(
                role
            ),
            "parent",
        )

    def default_child_profile(
        self,
        continuation: str,
    ) -> str:
        return self._legacy_child.get(
            str(
                continuation
            ),
            "child",
        )

    def meaning(
        self,
        relationship: str,
    ) -> str:
        for section in (
            self._parent_profiles,
            self._child_profiles,
            self._alliance_profiles,
            self._derived_profiles,
        ):
            definition = section.get(
                relationship
            )

            if definition is not None:
                return str(
                    definition.get(
                        "meaning",
                        "",
                    )
                )

        return ""

    def to_dict(
        self,
    ) -> dict[str, Any]:
        return deepcopy(
            self.payload
        )


__all__ = [
    "DEFAULT_KINSHIP_REGISTRY",
    "KinshipRegistry",
]
