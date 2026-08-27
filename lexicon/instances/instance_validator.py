#!/usr/bin/env python3

from __future__ import annotations

import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Any

import yaml


ROOT = Path(__file__).resolve().parent
LEXICON_ROOT = ROOT.parent

INSTANCE_REGISTRY = ROOT / "instance_registry.yaml"
SEGUE_REGISTRY = ROOT / "segue_registry.yaml"

KINDRED_REGISTRY = (
    LEXICON_ROOT
    / "kindred"
    / "kindred_registry.yaml"
)

ONTOLOGY_REGISTRY = (
    LEXICON_ROOT
    / "ontology"
    / "ontology_registry.yaml"
)

INSTANCE_PATTERN = re.compile(
    r"^instance:[a-z][a-z0-9_-]*"
    r"(?::[a-z][a-z0-9_-]*)*$"
)

SEGUE_PATTERN = re.compile(
    r"^segue:[a-z][a-z0-9_-]*"
    r"(?::[a-z][a-z0-9_-]*)*$"
)

CONFIDENCE_VALUES = {
    "confirmed",
    "inferred",
    "projected",
}

DIRECTION_VALUES = {
    "directed",
    "bidirectional",
}

STATUS_VALUES = {
    "active",
    "dormant",
    "deprecated",
    "superseded",
    "reserved",
}


def load_yaml(
    path: Path,
) -> dict[str, Any]:

    if not path.exists():

        raise FileNotFoundError(
            str(path)
        )

    with path.open(
        "r",
        encoding="utf-8",
    ) as handle:

        data = yaml.safe_load(
            handle
        )

    if not isinstance(
        data,
        dict,
    ):

        raise ValueError(
            f"Invalid YAML root: {path}"
        )

    return data


def text(
    value: Any,
) -> str:

    if value is None:

        return ""

    return str(value).strip()


def string_list(
    value: Any,
) -> list[str]:

    if value is None:

        return []

    if isinstance(
        value,
        str,
    ):

        result = value.strip()

        return (
            [result]
            if result
            else []
        )

    if isinstance(
        value,
        list,
    ):

        return [
            text(item)
            for item in value
            if text(item)
        ]

    result = text(value)

    return (
        [result]
        if result
        else []
    )


def add_issue(
    issues: list[dict[str, Any]],
    code: str,
    message: str,
    severity: str = "error",
    reference: str | None = None,
    field: str | None = None,
    value: Any = None,
) -> None:

    record: dict[str, Any] = {
        "code": code,
        "message": message,
        "severity": severity,
    }

    if reference:

        record["reference"] = reference

    if field:

        record["field"] = field

    if value is not None:

        record["value"] = value

    issues.append(
        record
    )


def duplicate_values(
    values: list[str],
) -> list[str]:

    seen: set[str] = set()
    duplicates: set[str] = set()

    for value in values:

        if value in seen:

            duplicates.add(
                value
            )

        seen.add(
            value
        )

    return sorted(
        duplicates
    )


def find_cycle(
    graph: dict[str, set[str]],
) -> list[str] | None:

    state: dict[str, int] = {}
    stack: list[str] = []
    positions: dict[str, int] = {}

    def visit(
        node: str,
    ) -> list[str] | None:

        state[node] = 1

        positions[node] = len(
            stack
        )

        stack.append(
            node
        )

        for target in sorted(
            graph.get(
                node,
                set(),
            )
        ):

            target_state = state.get(
                target,
                0,
            )

            if target_state == 0:

                cycle = visit(
                    target
                )

                if cycle:

                    return cycle

            elif target_state == 1:

                start = positions[
                    target
                ]

                return [
                    *stack[start:],
                    target,
                ]

        stack.pop()

        positions.pop(
            node,
            None,
        )

        state[node] = 2

        return None

    for node in sorted(
        graph
    ):

        if state.get(
            node,
            0,
        ) != 0:

            continue

        cycle = visit(
            node
        )

        if cycle:

            return cycle

    return None


def extract_ontology_ids(
    ontology_data: dict[str, Any],
) -> set[str]:

    candidates = []

    for field in (
        "classes",
        "ontologies",
        "ontology",
        "terms",
        "nodes",
    ):

        value = ontology_data.get(
            field
        )

        if isinstance(
            value,
            list,
        ):

            candidates.extend(
                value
            )

    identifiers: set[str] = set()

    for record in candidates:

        if isinstance(
            record,
            dict,
        ):

            identifier = text(
                record.get("id")
            )

            if identifier:

                identifiers.add(
                    identifier
                )

            canonical = text(
                record.get(
                    "canonical"
                )
            )

            if canonical:

                identifiers.add(
                    canonical
                )

        elif text(record):

            identifiers.add(
                text(record)
            )

    return identifiers


def validate_source(
    issues: list[dict[str, Any]],
    instance_id: str,
    source: Any,
) -> None:

    if not isinstance(
        source,
        dict,
    ):

        add_issue(
            issues,
            "instance.source.invalid",
            "Source must be an object",
            reference=instance_id,
            field="source",
        )

        return

    source_type = text(
        source.get("type")
    )

    source_reference = text(
        source.get(
            "reference"
        )
    )

    if not source_type:

        add_issue(
            issues,
            "instance.source.type_missing",
            "Source type is missing",
            reference=instance_id,
            field="source.type",
        )

    if not source_reference:

        add_issue(
            issues,
            "instance.source.reference_missing",
            "Source reference is missing",
            reference=instance_id,
            field="source.reference",
        )

        return

    if source_type != "file":

        return

    source_path = (
        LEXICON_ROOT
        / source_reference
    ).resolve()

    lexicon_root = (
        LEXICON_ROOT.resolve()
    )

    try:

        source_path.relative_to(
            lexicon_root
        )

    except ValueError:

        add_issue(
            issues,
            "instance.source.path_escape",
            "Source escapes lexicon root",
            reference=instance_id,
            field="source.reference",
            value=source_reference,
        )

        return

    if not source_path.exists():

        add_issue(
            issues,
            "instance.source.missing",
            "Source file does not exist",
            reference=instance_id,
            field="source.reference",
            value=source_reference,
        )


def validate_provenance(
    issues: list[dict[str, Any]],
    reference: str,
    provenance: Any,
    prefix: str,
) -> None:

    if not isinstance(
        provenance,
        dict,
    ):

        add_issue(
            issues,
            f"{prefix}.provenance.invalid",
            "Provenance must be an object",
            reference=reference,
            field="provenance",
        )

        return

    source = text(
        provenance.get("source")
    )

    if not source:

        add_issue(
            issues,
            f"{prefix}.provenance.source_missing",
            "Provenance source is missing",
            reference=reference,
            field="provenance.source",
        )

    confidence = text(
        provenance.get(
            "confidence"
        )
    )

    if confidence not in CONFIDENCE_VALUES:

        add_issue(
            issues,
            f"{prefix}.provenance.confidence_invalid",
            "Invalid provenance confidence",
            reference=reference,
            field="provenance.confidence",
            value=confidence,
        )

    evidence = provenance.get(
        "evidence",
        [],
    )

    if not isinstance(
        evidence,
        list,
    ):

        add_issue(
            issues,
            f"{prefix}.provenance.evidence_invalid",
            "Provenance evidence must be a list",
            reference=reference,
            field="provenance.evidence",
        )


def validate_lineage(
    issues: list[dict[str, Any]],
    reference: str,
    lineage: Any,
    prefix: str,
) -> None:

    if not isinstance(
        lineage,
        dict,
    ):

        add_issue(
            issues,
            f"{prefix}.lineage.invalid",
            "Lineage must be an object",
            reference=reference,
            field="lineage",
        )

        return

    derived_from = lineage.get(
        "derived_from"
    )

    history = lineage.get(
        "history"
    )

    supersedes = lineage.get(
        "supersedes",
        [],
    )

    if not isinstance(
        derived_from,
        list,
    ):

        add_issue(
            issues,
            f"{prefix}.lineage.derived_from_invalid",
            "lineage.derived_from must be a list",
            reference=reference,
            field="lineage.derived_from",
        )

    if not isinstance(
        history,
        list,
    ):

        add_issue(
            issues,
            f"{prefix}.lineage.history_invalid",
            "lineage.history must be a list",
            reference=reference,
            field="lineage.history",
        )

    if not isinstance(
        supersedes,
        list,
    ):

        add_issue(
            issues,
            f"{prefix}.lineage.supersedes_invalid",
            "lineage.supersedes must be a list",
            reference=reference,
            field="lineage.supersedes",
        )


def validate_relationships(
    issues: list[dict[str, Any]],
    instance_id: str,
    relationships: Any,
) -> None:

    if relationships is None:

        return

    if not isinstance(
        relationships,
        list,
    ):

        add_issue(
            issues,
            "instance.relationships.invalid",
            "Relationships must be a list",
            reference=instance_id,
            field="relationships",
        )

        return

    for position, relationship in enumerate(
        relationships
    ):

        if isinstance(
            relationship,
            str,
        ):

            if not text(
                relationship
            ):

                add_issue(
                    issues,
                    "instance.relationship.empty",
                    "Relationship reference is empty",
                    reference=instance_id,
                    field=f"relationships[{position}]",
                )

            continue

        if not isinstance(
            relationship,
            dict,
        ):

            add_issue(
                issues,
                "instance.relationship.invalid",
                "Relationship must be a string or object",
                reference=instance_id,
                field=f"relationships[{position}]",
            )

            continue

        relationship_type = text(
            relationship.get("type")
        )

        target = text(
            relationship.get("target")
        )

        if not relationship_type:

            add_issue(
                issues,
                "instance.relationship.type_missing",
                "Relationship type is missing",
                reference=instance_id,
                field=f"relationships[{position}].type",
            )

        if not target:

            add_issue(
                issues,
                "instance.relationship.target_missing",
                "Relationship target is missing",
                reference=instance_id,
                field=f"relationships[{position}].target",
            )


def validate() -> list[dict[str, Any]]:

    issues: list[
        dict[str, Any]
    ] = []

    instance_data = load_yaml(
        INSTANCE_REGISTRY
    )

    segue_data = load_yaml(
        SEGUE_REGISTRY
    )

    kindred_data = load_yaml(
        KINDRED_REGISTRY
    )

    ontology_data = load_yaml(
        ONTOLOGY_REGISTRY
    )

    raw_instances = instance_data.get(
        "instances",
        [],
    )

    raw_segues = segue_data.get(
        "segues",
        [],
    )

    raw_kindreds = kindred_data.get(
        "kindreds",
        [],
    )

    if not isinstance(
        raw_instances,
        list,
    ):

        add_issue(
            issues,
            "instance.registry.invalid",
            "instances must be a list",
        )

        raw_instances = []

    if not isinstance(
        raw_segues,
        list,
    ):

        add_issue(
            issues,
            "segue.registry.invalid",
            "segues must be a list",
        )

        raw_segues = []

    if not isinstance(
        raw_kindreds,
        list,
    ):

        add_issue(
            issues,
            "kindred.registry.invalid",
            "kindreds must be a list",
        )

        raw_kindreds = []

    kindred_ids = {
        text(
            record.get("id")
        )
        for record in raw_kindreds
        if isinstance(
            record,
            dict,
        )
        and text(
            record.get("id")
        )
    }

    ontology_ids = extract_ontology_ids(
        ontology_data
    )

    instances: dict[
        str,
        dict[str, Any],
    ] = {}

    segues: dict[
        str,
        dict[str, Any],
    ] = {}

    canonical_index: dict[
        str,
        list[str],
    ] = defaultdict(
        list
    )

    for position, record in enumerate(
        raw_instances
    ):

        if not isinstance(
            record,
            dict,
        ):

            add_issue(
                issues,
                "instance.record.invalid",
                "Instance record must be an object",
                value=position,
            )

            continue

        instance_id = text(
            record.get("id")
        )

        if not instance_id:

            add_issue(
                issues,
                "instance.id.missing",
                "Instance id is missing",
                value=position,
            )

            continue

        if not INSTANCE_PATTERN.fullmatch(
            instance_id
        ):

            add_issue(
                issues,
                "instance.id.invalid",
                "Instance id format is invalid",
                reference=instance_id,
                field="id",
            )

        if instance_id in instances:

            add_issue(
                issues,
                "instance.id.duplicate",
                "Instance id is duplicated",
                reference=instance_id,
            )

        instances[
            instance_id
        ] = record

        canonical = text(
            record.get(
                "canonical"
            )
        )

        if not canonical:

            add_issue(
                issues,
                "instance.canonical.missing",
                "Canonical name is missing",
                reference=instance_id,
                field="canonical",
            )

        else:

            canonical_index[
                canonical.casefold()
            ].append(
                instance_id
            )

        status = text(
            record.get(
                "status",
                "active",
            )
        )

        if status not in STATUS_VALUES:

            add_issue(
                issues,
                "instance.status.invalid",
                "Instance status is invalid",
                reference=instance_id,
                field="status",
                value=status,
            )

        for field in (
            "kindreds",
            "source",
            "state",
            "provenance",
            "lineage",
        ):

            if field not in record:

                add_issue(
                    issues,
                    "instance.required.missing",
                    "Required field is missing",
                    reference=instance_id,
                    field=field,
                )

        kindreds = string_list(
            record.get(
                "kindreds"
            )
        )

        for duplicate in duplicate_values(
            kindreds
        ):

            add_issue(
                issues,
                "instance.kindred.duplicate",
                "Kindred reference is duplicated",
                reference=instance_id,
                field="kindreds",
                value=duplicate,
            )

        for kindred_id in kindreds:

            if kindred_id not in kindred_ids:

                add_issue(
                    issues,
                    "instance.kindred.unresolved",
                    "Kindred does not resolve",
                    reference=instance_id,
                    field="kindreds",
                    value=kindred_id,
                )

        ontologies = string_list(
            record.get(
                "ontology"
            )
        )

        for duplicate in duplicate_values(
            ontologies
        ):

            add_issue(
                issues,
                "instance.ontology.duplicate",
                "Ontology reference is duplicated",
                reference=instance_id,
                field="ontology",
                value=duplicate,
            )

        for ontology_id in ontologies:

            if (
                ontology_ids
                and ontology_id not in ontology_ids
            ):

                add_issue(
                    issues,
                    "instance.ontology.unresolved",
                    "Ontology class does not resolve",
                    reference=instance_id,
                    field="ontology",
                    value=ontology_id,
                )

        validate_source(
            issues,
            instance_id,
            record.get("source"),
        )

        state = record.get(
            "state"
        )

        if not isinstance(
            state,
            dict,
        ):

            add_issue(
                issues,
                "instance.state.invalid",
                "State must be an object",
                reference=instance_id,
                field="state",
            )

        dependencies = string_list(
            record.get(
                "dependencies"
            )
        )

        for duplicate in duplicate_values(
            dependencies
        ):

            add_issue(
                issues,
                "instance.dependency.duplicate",
                "Dependency is duplicated",
                reference=instance_id,
                field="dependencies",
                value=duplicate,
            )

        validate_relationships(
            issues,
            instance_id,
            record.get(
                "relationships"
            ),
        )

        projections = record.get(
            "projections",
            [],
        )

        if not isinstance(
            projections,
            list,
        ):

            add_issue(
                issues,
                "instance.projections.invalid",
                "Projections must be a list",
                reference=instance_id,
                field="projections",
            )

        validate_provenance(
            issues,
            instance_id,
            record.get(
                "provenance"
            ),
            "instance",
        )

        validate_lineage(
            issues,
            instance_id,
            record.get(
                "lineage"
            ),
            "instance",
        )

    for position, record in enumerate(
        raw_segues
    ):

        if not isinstance(
            record,
            dict,
        ):

            add_issue(
                issues,
                "segue.record.invalid",
                "Segue record must be an object",
                value=position,
            )

            continue

        segue_id = text(
            record.get("id")
        )

        if not segue_id:

            add_issue(
                issues,
                "segue.id.missing",
                "Segue id is missing",
                value=position,
            )

            continue

        if not SEGUE_PATTERN.fullmatch(
            segue_id
        ):

            add_issue(
                issues,
                "segue.id.invalid",
                "Segue id format is invalid",
                reference=segue_id,
                field="id",
            )

        if segue_id in segues:

            add_issue(
                issues,
                "segue.id.duplicate",
                "Segue id is duplicated",
                reference=segue_id,
            )

        segues[
            segue_id
        ] = record

        canonical = text(
            record.get(
                "canonical"
            )
        )

        if not canonical:

            add_issue(
                issues,
                "segue.canonical.missing",
                "Canonical name is missing",
                reference=segue_id,
                field="canonical",
            )

        else:

            canonical_index[
                canonical.casefold()
            ].append(
                segue_id
            )

        status = text(
            record.get(
                "status",
                "active",
            )
        )

        if status not in STATUS_VALUES:

            add_issue(
                issues,
                "segue.status.invalid",
                "Segue status is invalid",
                reference=segue_id,
                field="status",
                value=status,
            )

        source = text(
            record.get("from")
        )

        target = text(
            record.get("to")
        )

        relation = text(
            record.get(
                "relation"
            )
        )

        direction = text(
            record.get(
                "direction",
                "directed",
            )
        )

        if not source:

            add_issue(
                issues,
                "segue.from.missing",
                "Segue source is missing",
                reference=segue_id,
                field="from",
            )

        if not target:

            add_issue(
                issues,
                "segue.to.missing",
                "Segue target is missing",
                reference=segue_id,
                field="to",
            )

        if source and target and source == target:

            add_issue(
                issues,
                "segue.self_loop",
                "Segue connects an instance to itself",
                severity="warning",
                reference=segue_id,
            )

        if not relation:

            add_issue(
                issues,
                "segue.relation.missing",
                "Segue relation is missing",
                reference=segue_id,
                field="relation",
            )

        if direction not in DIRECTION_VALUES:

            add_issue(
                issues,
                "segue.direction.invalid",
                "Segue direction is invalid",
                reference=segue_id,
                field="direction",
                value=direction,
            )

        conditions = record.get(
            "conditions",
            [],
        )

        if not isinstance(
            conditions,
            list,
        ):

            add_issue(
                issues,
                "segue.conditions.invalid",
                "Segue conditions must be a list",
                reference=segue_id,
                field="conditions",
            )

        effects = record.get(
            "effects",
            [],
        )

        if not isinstance(
            effects,
            list,
        ):

            add_issue(
                issues,
                "segue.effects.invalid",
                "Segue effects must be a list",
                reference=segue_id,
                field="effects",
            )

        dependencies = string_list(
            record.get(
                "dependencies"
            )
        )

        for duplicate in duplicate_values(
            dependencies
        ):

            add_issue(
                issues,
                "segue.dependency.duplicate",
                "Dependency is duplicated",
                reference=segue_id,
                field="dependencies",
                value=duplicate,
            )

        validate_provenance(
            issues,
            segue_id,
            record.get(
                "provenance"
            ),
            "segue",
        )

        validate_lineage(
            issues,
            segue_id,
            record.get(
                "lineage"
            ),
            "segue",
        )

    all_nodes = {
        *instances,
        *segues,
    }

    for segue_id, record in segues.items():

        source = text(
            record.get("from")
        )

        target = text(
            record.get("to")
        )

        if source not in instances:

            add_issue(
                issues,
                "segue.from.unresolved",
                "Segue source instance does not resolve",
                reference=segue_id,
                field="from",
                value=source,
            )

        if target not in instances:

            add_issue(
                issues,
                "segue.to.unresolved",
                "Segue target instance does not resolve",
                reference=segue_id,
                field="to",
                value=target,
            )

    dependency_graph: dict[
        str,
        set[str],
    ] = {
        node: set()
        for node in all_nodes
    }

    for instance_id, record in instances.items():

        dependencies = string_list(
            record.get(
                "dependencies"
            )
        )

        for dependency in dependencies:

            if dependency == instance_id:

                add_issue(
                    issues,
                    "instance.dependency.self_reference",
                    "Instance depends on itself",
                    reference=instance_id,
                    field="dependencies",
                    value=dependency,
                )

            if dependency not in all_nodes:

                add_issue(
                    issues,
                    "instance.dependency.unresolved",
                    "Instance dependency does not resolve",
                    reference=instance_id,
                    field="dependencies",
                    value=dependency,
                )

            else:

                dependency_graph[
                    instance_id
                ].add(
                    dependency
                )

    for segue_id, record in segues.items():

        dependencies = string_list(
            record.get(
                "dependencies"
            )
        )

        for dependency in dependencies:

            if dependency == segue_id:

                add_issue(
                    issues,
                    "segue.dependency.self_reference",
                    "Segue depends on itself",
                    reference=segue_id,
                    field="dependencies",
                    value=dependency,
                )

            if dependency not in all_nodes:

                add_issue(
                    issues,
                    "segue.dependency.unresolved",
                    "Segue dependency does not resolve",
                    reference=segue_id,
                    field="dependencies",
                    value=dependency,
                )

            else:

                dependency_graph[
                    segue_id
                ].add(
                    dependency
                )

    cycle = find_cycle(
        dependency_graph
    )

    if cycle:

        add_issue(
            issues,
            "dependency.cycle",
            "Dependency graph contains a cycle",
            value=cycle,
        )

    for canonical, owners in sorted(
        canonical_index.items()
    ):

        if len(
            owners
        ) > 1:

            add_issue(
                issues,
                "canonical.duplicate",
                "Canonical name is duplicated",
                value={
                    "canonical": canonical,
                    "owners": sorted(
                        owners
                    ),
                },
            )

    return issues


def main() -> int:

    try:

        issues = validate()

    except Exception as error:

        print(
            json.dumps(
                {
                    "valid": False,
                    "error_count": 1,
                    "warning_count": 0,
                    "issues": [
                        {
                            "code": (
                                "validator."
                                "runtime_failure"
                            ),
                            "severity": "error",
                            "message": str(
                                error
                            ),
                            "exception": type(
                                error
                            ).__name__,
                        }
                    ],
                },
                indent=2,
                sort_keys=True,
            )
        )

        return 1

    errors = [
        record
        for record in issues
        if record.get(
            "severity"
        ) == "error"
    ]

    warnings = [
        record
        for record in issues
        if record.get(
            "severity"
        ) == "warning"
    ]

    print(
        json.dumps(
            {
                "valid": not errors,
                "error_count": len(
                    errors
                ),
                "warning_count": len(
                    warnings
                ),
                "issues": issues,
            },
            indent=2,
            sort_keys=True,
        )
    )

    return (
        1
        if errors
        else 0
    )


if __name__ == "__main__":

    raise SystemExit(
        main()
    )
