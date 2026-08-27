#!/usr/bin/env python3

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Mapping

try:
    from .program_hierarchy import (
        PROGRAM_CHILD_LEVEL,
        PROGRAM_LEVEL_INDEX,
        PROGRAM_LEVELS,
        ProgramHierarchy,
        ProgramHierarchyError,
    )
except ImportError:
    from program_hierarchy import (
        PROGRAM_CHILD_LEVEL,
        PROGRAM_LEVEL_INDEX,
        PROGRAM_LEVELS,
        ProgramHierarchy,
        ProgramHierarchyError,
    )


CODE_SEGUE_TYPES = (
    "composition",
    "control-flow",
    "data-flow",
    "state",
    "contract",
    "lifecycle",
    "exception",
    "adaptation",
    "integration",
)

LINE_TERMINATORS = (
    "",
    "\n",
    "\r\n",
    "\r",
)


class ProgramCompositionError(RuntimeError):
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
        canonical_json(value).encode(
            "utf-8"
        )
    ).hexdigest()


def digest_bytes(
    value: bytes,
) -> str:
    return hashlib.sha256(
        value
    ).hexdigest()


def normalize_identifier(
    value: Any,
    *,
    field_name: str,
) -> str:
    text = str(
        value
        if value is not None
        else ""
    ).strip()

    if not text:
        raise ProgramCompositionError(
            f"{field_name} is required"
        )

    return text


def normalize_unique_string_tuple(
    values: Iterable[Any] | None,
) -> tuple[str, ...]:
    if values is None:
        return ()

    result: list[str] = []

    for value in values:
        text = str(
            value
        ).strip()

        if not text:
            continue

        if text not in result:
            result.append(
                text
            )

    return tuple(
        result
    )


def normalize_ordered_string_tuple(
    values: Iterable[Any] | None,
) -> tuple[str, ...]:
    if values is None:
        return ()

    result: list[str] = []

    for value in values:
        text = str(
            value
        ).strip()

        if not text:
            raise ProgramCompositionError(
                "ordered composition contains "
                "empty identity"
            )

        result.append(
            text
        )

    return tuple(
        result
    )


def content_id(
    kind: str,
    material: Any,
) -> str:
    prefix = normalize_identifier(
        kind,
        field_name="kind",
    ).lower()

    return (
        f"{prefix}:"
        + digest(
            material
        )[:24]
    )


def split_line_terminator(
    physical_line: str,
) -> tuple[str, str]:
    if physical_line.endswith(
        "\r\n"
    ):
        return (
            physical_line[:-2],
            "\r\n",
        )

    if physical_line.endswith(
        "\n"
    ):
        return (
            physical_line[:-1],
            "\n",
        )

    if physical_line.endswith(
        "\r"
    ):
        return (
            physical_line[:-1],
            "\r",
        )

    return (
        physical_line,
        "",
    )


@dataclass(
    frozen=True,
    slots=True,
)
class ProgramInstance:
    instance_id: str
    level: str
    children: tuple[str, ...] = ()
    value: str | None = None
    terminator: str = ""
    owner: str = "exile:modus"
    authority_state: str = "provisional"
    authoritative: bool = False
    lineage: tuple[str, ...] = ()
    provenance: tuple[str, ...] = ()
    dependencies: tuple[str, ...] = ()
    future_extensions: tuple[str, ...] = ()
    metadata: Mapping[str, Any] = field(
        default_factory=dict
    )

    def __post_init__(
        self,
    ) -> None:
        object.__setattr__(
            self,
            "instance_id",
            normalize_identifier(
                self.instance_id,
                field_name="instance_id",
            ),
        )

        hierarchy = ProgramHierarchy()

        try:
            level = hierarchy.normalize(
                self.level
            )
        except ProgramHierarchyError as exc:
            raise ProgramCompositionError(
                str(exc)
            ) from exc

        object.__setattr__(
            self,
            "level",
            level,
        )

        object.__setattr__(
            self,
            "children",
            normalize_ordered_string_tuple(
                self.children
            ),
        )

        object.__setattr__(
            self,
            "lineage",
            normalize_unique_string_tuple(
                self.lineage
            ),
        )

        object.__setattr__(
            self,
            "provenance",
            normalize_unique_string_tuple(
                self.provenance
            ),
        )

        object.__setattr__(
            self,
            "dependencies",
            normalize_unique_string_tuple(
                self.dependencies
            ),
        )

        object.__setattr__(
            self,
            "future_extensions",
            normalize_unique_string_tuple(
                self.future_extensions
            ),
        )

        object.__setattr__(
            self,
            "metadata",
            dict(
                self.metadata
            ),
        )

        if self.authoritative is not False:
            raise ProgramCompositionError(
                "runtime program instances "
                "must remain non-authoritative"
            )

        if level == "character":
            if self.children:
                raise ProgramCompositionError(
                    "character instances cannot "
                    "contain children"
                )

            if self.value is None:
                raise ProgramCompositionError(
                    "character instance requires "
                    "value"
                )

            if len(
                self.value
            ) != 1:
                raise ProgramCompositionError(
                    "character value must contain "
                    "exactly one Unicode character"
                )

            if self.terminator:
                raise ProgramCompositionError(
                    "character instance cannot own "
                    "line terminator"
                )

            return

        if self.value is not None:
            raise ProgramCompositionError(
                f"{level} instances cannot "
                "store direct source value"
            )

        if level == "line":
            if (
                self.terminator
                not in LINE_TERMINATORS
            ):
                raise ProgramCompositionError(
                    "invalid line terminator"
                )

            return

        if self.terminator:
            raise ProgramCompositionError(
                f"{level} instances cannot own "
                "line terminator"
            )

        if not self.children:
            raise ProgramCompositionError(
                f"{level} instance requires "
                "child instances"
            )

    @property
    def ordinal(
        self,
    ) -> int:
        return PROGRAM_LEVEL_INDEX[
            self.level
        ]

    @property
    def child_level(
        self,
    ) -> str | None:
        return PROGRAM_CHILD_LEVEL.get(
            self.level
        )

    def projection(
        self,
    ) -> dict[str, Any]:
        payload = {
            "schema": (
                "savant://program/"
                "instance/1.1.0"
            ),
            "instance_id": (
                self.instance_id
            ),
            "level": self.level,
            "ordinal": self.ordinal,
            "child_level": (
                self.child_level
            ),
            "children": list(
                self.children
            ),
            "value": self.value,
            "terminator": (
                self.terminator
            ),
            "owner": self.owner,
            "authority_state": (
                self.authority_state
            ),
            "authoritative": False,
            "lineage": list(
                self.lineage
            ),
            "provenance": list(
                self.provenance
            ),
            "dependencies": list(
                self.dependencies
            ),
            "future_extensions": list(
                self.future_extensions
            ),
            "metadata": dict(
                self.metadata
            ),
        }

        payload["digest"] = digest(
            payload
        )

        return payload


@dataclass(
    frozen=True,
    slots=True,
)
class CodeSegue:
    segue_id: str
    source: str
    target: str
    segue_type: str
    owner: str = "exile:modus"
    authority_state: str = "provisional"
    authoritative: bool = False
    contract: str | None = None
    dependencies: tuple[str, ...] = ()
    lineage: tuple[str, ...] = ()
    provenance: tuple[str, ...] = ()
    metadata: Mapping[str, Any] = field(
        default_factory=dict
    )

    def __post_init__(
        self,
    ) -> None:
        object.__setattr__(
            self,
            "segue_id",
            normalize_identifier(
                self.segue_id,
                field_name="segue_id",
            ),
        )

        object.__setattr__(
            self,
            "source",
            normalize_identifier(
                self.source,
                field_name="source",
            ),
        )

        object.__setattr__(
            self,
            "target",
            normalize_identifier(
                self.target,
                field_name="target",
            ),
        )

        segue_type = normalize_identifier(
            self.segue_type,
            field_name="segue_type",
        ).lower()

        if (
            segue_type
            not in CODE_SEGUE_TYPES
        ):
            raise ProgramCompositionError(
                "invalid code segue type: "
                + segue_type
            )

        object.__setattr__(
            self,
            "segue_type",
            segue_type,
        )

        object.__setattr__(
            self,
            "dependencies",
            normalize_unique_string_tuple(
                self.dependencies
            ),
        )

        object.__setattr__(
            self,
            "lineage",
            normalize_unique_string_tuple(
                self.lineage
            ),
        )

        object.__setattr__(
            self,
            "provenance",
            normalize_unique_string_tuple(
                self.provenance
            ),
        )

        object.__setattr__(
            self,
            "metadata",
            dict(
                self.metadata
            ),
        )

        if self.authoritative is not False:
            raise ProgramCompositionError(
                "runtime code segues must "
                "remain non-authoritative"
            )

    def projection(
        self,
    ) -> dict[str, Any]:
        payload = {
            "schema": (
                "savant://program/"
                "segue/1.0.0"
            ),
            "segue_id": (
                self.segue_id
            ),
            "source": self.source,
            "target": self.target,
            "type": self.segue_type,
            "owner": self.owner,
            "authority_state": (
                self.authority_state
            ),
            "authoritative": False,
            "contract": self.contract,
            "dependencies": list(
                self.dependencies
            ),
            "lineage": list(
                self.lineage
            ),
            "provenance": list(
                self.provenance
            ),
            "metadata": dict(
                self.metadata
            ),
        }

        payload["digest"] = digest(
            payload
        )

        return payload


@dataclass(
    frozen=True,
    slots=True,
)
class SourceDecomposition:
    source_path: str
    source_digest: str
    script_instance_id: str
    line_ids: tuple[str, ...]
    segment_ids: tuple[str, ...]
    snippet_ids: tuple[str, ...]
    segue_ids: tuple[str, ...]

    def projection(
        self,
    ) -> dict[str, Any]:
        payload = {
            "schema": (
                "savant://program/"
                "source-decomposition/1.0.0"
            ),
            "source_path": (
                self.source_path
            ),
            "source_digest": (
                self.source_digest
            ),
            "script_instance_id": (
                self.script_instance_id
            ),
            "line_ids": list(
                self.line_ids
            ),
            "segment_ids": list(
                self.segment_ids
            ),
            "snippet_ids": list(
                self.snippet_ids
            ),
            "segue_ids": list(
                self.segue_ids
            ),
            "authoritative": False,
            "authority_effect": "none",
        }

        payload["digest"] = digest(
            payload
        )

        return payload


class ProgramCompositionGraph:
    schema = (
        "savant://program/"
        "composition-graph/1.1.0"
    )

    owner = "exile:modus"

    def __init__(
        self,
    ) -> None:
        self.hierarchy = (
            ProgramHierarchy()
        )

        self._instances: dict[
            str,
            ProgramInstance,
        ] = {}

        self._segues: dict[
            str,
            CodeSegue,
        ] = {}

    @property
    def instances(
        self,
    ) -> tuple[
        ProgramInstance,
        ...,
    ]:
        return tuple(
            self._instances[
                key
            ]
            for key in sorted(
                self._instances
            )
        )

    @property
    def segues(
        self,
    ) -> tuple[
        CodeSegue,
        ...,
    ]:
        return tuple(
            self._segues[
                key
            ]
            for key in sorted(
                self._segues
            )
        )

    def add_instance(
        self,
        instance: ProgramInstance,
    ) -> ProgramInstance:
        existing = (
            self._instances.get(
                instance.instance_id
            )
        )

        if existing is not None:
            if existing == instance:
                return existing

            raise ProgramCompositionError(
                "instance identity conflict: "
                + instance.instance_id
            )

        self._instances[
            instance.instance_id
        ] = instance

        return instance

    def add_segue(
        self,
        segue: CodeSegue,
    ) -> CodeSegue:
        existing = (
            self._segues.get(
                segue.segue_id
            )
        )

        if existing is not None:
            if existing == segue:
                return existing

            raise ProgramCompositionError(
                "segue identity conflict: "
                + segue.segue_id
            )

        self._segues[
            segue.segue_id
        ] = segue

        return segue

    def instance(
        self,
        instance_id: str,
    ) -> ProgramInstance:
        try:
            return self._instances[
                instance_id
            ]
        except KeyError as exc:
            raise ProgramCompositionError(
                "unknown program instance: "
                + instance_id
            ) from exc

    def segue(
        self,
        segue_id: str,
    ) -> CodeSegue:
        try:
            return self._segues[
                segue_id
            ]
        except KeyError as exc:
            raise ProgramCompositionError(
                "unknown code segue: "
                + segue_id
            ) from exc

    def _validate_children(
        self,
        instance: ProgramInstance,
    ) -> None:
        if (
            instance.level
            == "character"
        ):
            return

        expected = (
            self.hierarchy.child_of(
                instance.level
            )
        )

        if expected is None:
            raise ProgramCompositionError(
                "program hierarchy defines "
                "no child level for "
                + instance.level
            )

        for child_id in (
            instance.children
        ):
            child = self.instance(
                child_id
            )

            if (
                child.level
                != expected
            ):
                raise ProgramCompositionError(
                    f"{instance.instance_id} "
                    f"expects {expected} "
                    "children; "
                    f"{child_id} is "
                    f"{child.level}"
                )

    def _validate_segues(
        self,
    ) -> None:
        for segue in self.segues:
            self.instance(
                segue.source
            )

            self.instance(
                segue.target
            )

            if (
                segue.source
                == segue.target
            ):
                raise ProgramCompositionError(
                    "code segue cannot target "
                    "itself: "
                    + segue.segue_id
                )

    def _validate_cycle(
        self,
        instance_id: str,
        *,
        visiting: set[str],
        visited: set[str],
    ) -> None:
        if instance_id in visited:
            return

        if instance_id in visiting:
            raise ProgramCompositionError(
                "program composition cycle "
                "detected at "
                + instance_id
            )

        visiting.add(
            instance_id
        )

        instance = self.instance(
            instance_id
        )

        for child_id in (
            instance.children
        ):
            self._validate_cycle(
                child_id,
                visiting=visiting,
                visited=visited,
            )

        visiting.remove(
            instance_id
        )

        visited.add(
            instance_id
        )

    def validate(
        self,
    ) -> dict[str, Any]:
        hierarchy_validation = (
            self.hierarchy.validate()
        )

        for instance in (
            self.instances
        ):
            self._validate_children(
                instance
            )

        self._validate_segues()

        visited: set[str] = set()

        for instance in (
            self.instances
        ):
            self._validate_cycle(
                instance.instance_id,
                visiting=set(),
                visited=visited,
            )

        checks = {
            "program_levels": (
                hierarchy_validation[
                    "valid"
                ]
                and hierarchy_validation[
                    "level_count"
                ]
                == 9
            ),
            "segment_present": (
                PROGRAM_LEVEL_INDEX.get(
                    "segment"
                )
                == 2
            ),
            "application_terminal": (
                PROGRAM_LEVELS[-1]
                == "application"
            ),
            "hierarchy_derived": True,
            "hierarchy_transition_count": (
                hierarchy_validation[
                    "transition_count"
                ]
                == 8
            ),
            "segue_types": (
                len(
                    CODE_SEGUE_TYPES
                )
                == 9
            ),
            "ordered_composition": (
                True
            ),
            "blank_lines_supported": (
                True
            ),
            "line_terminators_supported": (
                True
            ),
            "instances_valid": True,
            "segues_valid": True,
            "acyclic": True,
            "non_authoritative": (
                all(
                    instance.authoritative
                    is False
                    for instance
                    in self.instances
                )
                and all(
                    segue.authoritative
                    is False
                    for segue
                    in self.segues
                )
            ),
        }

        payload = {
            "schema": (
                "savant://assurance/"
                "program-composition/1.1.0"
            ),
            "valid": all(
                checks.values()
            ),
            "checks": checks,
            "program_levels": list(
                PROGRAM_LEVELS
            ),
            "hierarchy_schema": (
                self.hierarchy.schema
            ),
            "instance_count": len(
                self._instances
            ),
            "segue_count": len(
                self._segues
            ),
            "owner": self.owner,
            "authority_effect": "none",
        }

        payload["digest"] = digest(
            payload
        )

        return payload

    def descendants(
        self,
        instance_id: str,
    ) -> tuple[str, ...]:
        self.instance(
            instance_id
        )

        result: list[str] = []
        seen: set[str] = set()

        def walk(
            current_id: str,
        ) -> None:
            current = self.instance(
                current_id
            )

            for child_id in (
                current.children
            ):
                if (
                    child_id
                    not in seen
                ):
                    seen.add(
                        child_id
                    )

                    result.append(
                        child_id
                    )

                    walk(
                        child_id
                    )

        walk(
            instance_id
        )

        return tuple(
            result
        )

    def relevant_segues(
        self,
        instance_id: str,
    ) -> tuple[
        CodeSegue,
        ...,
    ]:
        members = {
            instance_id,
            *self.descendants(
                instance_id
            ),
        }

        return tuple(
            segue
            for segue
            in self.segues
            if (
                segue.source
                in members
                and segue.target
                in members
            )
        )

    def project_manifest(
        self,
        instance_id: str,
    ) -> dict[str, Any]:
        instance = self.instance(
            instance_id
        )

        relevant_ids = (
            instance_id,
            *self.descendants(
                instance_id
            ),
        )

        payload = {
            "schema": (
                "savant://program/"
                "projection-manifest/1.1.0"
            ),
            "source_instance_id": (
                instance_id
            ),
            "source_level": (
                instance.level
            ),
            "source_instances": [
                self.instance(
                    item
                ).projection()
                for item
                in relevant_ids
            ],
            "source_segues": [
                segue.projection()
                for segue
                in self.relevant_segues(
                    instance_id
                )
            ],
            "owner": self.owner,
            "authoritative": False,
            "authority_effect": "none",
            "rebuildable": True,
        }

        payload["digest"] = digest(
            payload
        )

        return payload

    def project_text(
        self,
        instance_id: str,
    ) -> str:
        instance = self.instance(
            instance_id
        )

        if (
            instance.ordinal
            > PROGRAM_LEVEL_INDEX[
                "script"
            ]
        ):
            raise ProgramCompositionError(
                "text projection is defined "
                "only through script level"
            )

        return self._render(
            instance
        )

    def _render(
        self,
        instance: ProgramInstance,
    ) -> str:
        if (
            instance.level
            == "character"
        ):
            if (
                instance.value
                is None
            ):
                raise ProgramCompositionError(
                    "character value missing"
                )

            return instance.value

        rendered = "".join(
            self._render(
                self.instance(
                    child_id
                )
            )
            for child_id
            in instance.children
        )

        if instance.level == "line":
            return (
                rendered
                + instance.terminator
            )

        return rendered

    def _intern_character(
        self,
        value: str,
    ) -> str:
        instance_id = content_id(
            "character",
            {
                "value": value,
            },
        )

        self.add_instance(
            ProgramInstance(
                instance_id=(
                    instance_id
                ),
                level="character",
                value=value,
                provenance=(
                    "deterministic-source-decomposition",
                ),
            )
        )

        return instance_id

    def _intern_line(
        self,
        content: str,
        terminator: str,
    ) -> str:
        child_ids = tuple(
            self._intern_character(
                character
            )
            for character
            in content
        )

        instance_id = content_id(
            "line",
            {
                "children": (
                    child_ids
                ),
                "terminator": (
                    terminator
                ),
            },
        )

        self.add_instance(
            ProgramInstance(
                instance_id=(
                    instance_id
                ),
                level="line",
                children=child_ids,
                terminator=(
                    terminator
                ),
                provenance=(
                    "deterministic-source-decomposition",
                ),
            )
        )

        return instance_id

    def _intern_composition(
        self,
        *,
        level: str,
        children: tuple[str, ...],
        metadata: (
            Mapping[str, Any]
            | None
        ) = None,
    ) -> str:
        try:
            normalized_level = (
                self.hierarchy.normalize(
                    level
                )
            )
        except ProgramHierarchyError as exc:
            raise ProgramCompositionError(
                str(exc)
            ) from exc

        instance_id = content_id(
            normalized_level,
            {
                "children": children,
                "metadata": dict(
                    metadata or {}
                ),
            },
        )

        self.add_instance(
            ProgramInstance(
                instance_id=(
                    instance_id
                ),
                level=(
                    normalized_level
                ),
                children=children,
                provenance=(
                    "deterministic-source-decomposition",
                ),
                metadata=dict(
                    metadata or {}
                ),
            )
        )

        return instance_id

    def decompose_text(
        self,
        text: str,
        *,
        source_path: str,
    ) -> SourceDecomposition:
        source_path = (
            normalize_identifier(
                source_path,
                field_name=(
                    "source_path"
                ),
            )
        )

        physical_lines = (
            text.splitlines(
                keepends=True
            )
        )

        if not physical_lines:
            physical_lines = [
                "",
            ]

        line_ids: list[str] = []

        for physical_line in (
            physical_lines
        ):
            content, terminator = (
                split_line_terminator(
                    physical_line
                )
            )

            line_ids.append(
                self._intern_line(
                    content,
                    terminator,
                )
            )

        segment_line_groups: list[
            tuple[str, ...]
        ] = []

        current: list[str] = []

        for line_id in line_ids:
            current.append(
                line_id
            )

            line = self.instance(
                line_id
            )

            if (
                not line.children
                and line.terminator
            ):
                segment_line_groups.append(
                    tuple(
                        current
                    )
                )

                current = []

        if current:
            segment_line_groups.append(
                tuple(
                    current
                )
            )

        if not segment_line_groups:
            segment_line_groups.append(
                tuple(
                    line_ids
                )
            )

        segment_ids: list[str] = []

        for ordinal, group in enumerate(
            segment_line_groups,
            start=1,
        ):
            segment_ids.append(
                self._intern_composition(
                    level="segment",
                    children=group,
                    metadata={
                        "decomposition_ordinal": (
                            ordinal
                        ),
                    },
                )
            )

        snippet_ids: list[str] = []

        for (
            ordinal,
            segment_id,
        ) in enumerate(
            segment_ids,
            start=1,
        ):
            snippet_ids.append(
                self._intern_composition(
                    level="snippet",
                    children=(
                        segment_id,
                    ),
                    metadata={
                        "decomposition_ordinal": (
                            ordinal
                        ),
                        "bootstrap_classification": (
                            "structural"
                        ),
                    },
                )
            )

        source_digest = (
            digest_bytes(
                text.encode(
                    "utf-8"
                )
            )
        )

        script_id = (
            self._intern_composition(
                level="script",
                children=tuple(
                    snippet_ids
                ),
                metadata={
                    "source_path": (
                        source_path
                    ),
                    "source_digest": (
                        source_digest
                    ),
                    "decomposition": (
                        "blank-line-bounded-v1"
                    ),
                },
            )
        )

        segue_ids: list[str] = []

        for ordinal in range(
            len(
                snippet_ids
            ) - 1
        ):
            source = snippet_ids[
                ordinal
            ]

            target = snippet_ids[
                ordinal + 1
            ]

            segue_id = content_id(
                "segue",
                {
                    "source": source,
                    "target": target,
                    "type": (
                        "composition"
                    ),
                    "ordinal": (
                        ordinal + 1
                    ),
                },
            )

            self.add_segue(
                CodeSegue(
                    segue_id=segue_id,
                    source=source,
                    target=target,
                    segue_type=(
                        "composition"
                    ),
                    provenance=(
                        "deterministic-source-decomposition",
                    ),
                    metadata={
                        "ordinal": (
                            ordinal + 1
                        ),
                    },
                )
            )

            segue_ids.append(
                segue_id
            )

        decomposition = (
            SourceDecomposition(
                source_path=(
                    source_path
                ),
                source_digest=(
                    source_digest
                ),
                script_instance_id=(
                    script_id
                ),
                line_ids=tuple(
                    line_ids
                ),
                segment_ids=tuple(
                    segment_ids
                ),
                snippet_ids=tuple(
                    snippet_ids
                ),
                segue_ids=tuple(
                    segue_ids
                ),
            )
        )

        projected = (
            self.project_text(
                script_id
            )
        )

        if projected != text:
            raise ProgramCompositionError(
                "source decomposition failed "
                "byte-equivalent text "
                "projection"
            )

        return decomposition

    def decompose_file(
        self,
        path: Path,
    ) -> SourceDecomposition:
        path = path.resolve()

        if not path.is_absolute():
            raise ProgramCompositionError(
                "source path must be absolute"
            )

        if not path.is_file():
            raise ProgramCompositionError(
                f"missing source file: "
                f"{path}"
            )

        raw = path.read_bytes()

        try:
            text = raw.decode(
                "utf-8"
            )
        except UnicodeDecodeError as exc:
            raise ProgramCompositionError(
                f"source is not UTF-8: "
                f"{path}"
            ) from exc

        decomposition = (
            self.decompose_text(
                text,
                source_path=str(
                    path
                ),
            )
        )

        projected = (
            self.project_text(
                decomposition
                .script_instance_id
            ).encode(
                "utf-8"
            )
        )

        if projected != raw:
            raise ProgramCompositionError(
                "source decomposition failed "
                "byte-for-byte projection"
            )

        return decomposition

    def profile(
        self,
    ) -> dict[str, Any]:
        hierarchy_validation = (
            self.hierarchy.validate()
        )

        payload = {
            "schema": self.schema,
            "owner": self.owner,
            "role": (
                "canonical program "
                "composition runtime "
                "primitive"
            ),
            "program_levels": list(
                PROGRAM_LEVELS
            ),
            "hierarchy_schema": (
                self.hierarchy.schema
            ),
            "hierarchy_valid": (
                hierarchy_validation[
                    "valid"
                ]
            ),
            "hierarchy_level_count": (
                hierarchy_validation[
                    "level_count"
                ]
            ),
            "hierarchy_transition_count": (
                hierarchy_validation[
                    "transition_count"
                ]
            ),
            "levels_are_projection": (
                True
            ),
            "segue_types": list(
                CODE_SEGUE_TYPES
            ),
            "line_terminators": list(
                LINE_TERMINATORS
            ),
            "instance_count": len(
                self._instances
            ),
            "segue_count": len(
                self._segues
            ),
            "source_decomposition": (
                "blank-line-bounded-v1"
            ),
            "authoritative": False,
            "mutation_authorized": False,
            "authority_effect": "none",
        }

        payload["digest"] = digest(
            payload
        )

        return payload


def main() -> int:
    graph = (
        ProgramCompositionGraph()
    )

    print(
        json.dumps(
            graph.profile(),
            indent=2,
            sort_keys=True,
        )
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
