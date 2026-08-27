#!/usr/bin/env python3

from __future__ import annotations

import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

import yaml


LEXICON_ROOT = Path("/root/savant-runtime/lexicon")

REGISTRY_PATH = LEXICON_ROOT / "registry.yaml"

VALIDATOR_PATH = (
    LEXICON_ROOT
    / "validators"
    / "lexicon_validator.py"
)

CONSTITUTION_PATH = (
    LEXICON_ROOT
    / "docs"
    / "LEXICON_CONSTITUTION.md"
)

KINDRED_ID = "lex:core:kindred"
KINSHIP_ID = "lex:service:kinship"

CURRENT_KINSHIP_CONCEPT = (
    "Functional relationship-plane service"
)

CURRENT_KINDRED_CONCEPT = (
    "Canonical relationship methodology and typed relationship system"
)


def utc_stamp() -> str:
    return (
        datetime.now(timezone.utc)
        .strftime("%Y%m%dT%H%M%SZ")
    )


def load_yaml(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(
        path.read_text(
            encoding="utf-8"
        )
    )

    if not isinstance(data, dict):
        raise TypeError(
            f"{path}: expected YAML object"
        )

    return data


def write_yaml(
    path: Path,
    payload: Mapping[str, Any],
) -> None:
    path.write_text(
        yaml.safe_dump(
            dict(payload),
            sort_keys=False,
            allow_unicode=True,
            width=100,
        ),
        encoding="utf-8",
    )


def backup_file(
    source: Path,
    backup_root: Path,
) -> Path:
    relative = source.relative_to(
        LEXICON_ROOT
    )

    destination = (
        backup_root
        / relative
    )

    destination.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    shutil.copy2(
        source,
        destination,
    )

    return destination


def ensure_lineage(
    lexeme: dict[str, Any],
) -> dict[str, Any]:
    lineage = lexeme.get("lineage")

    if lineage is None:
        lineage = {}

    if not isinstance(
        lineage,
        dict,
    ):
        raise TypeError(
            f"{lexeme.get('id')}: "
            "lineage must be an object"
        )

    supersedes = lineage.get(
        "supersedes"
    )

    if supersedes is None:
        supersedes = []

    if not isinstance(
        supersedes,
        list,
    ):
        raise TypeError(
            f"{lexeme.get('id')}: "
            "lineage.supersedes must be a list"
        )

    history = lineage.get(
        "history"
    )

    if history is None:
        history = []

    if not isinstance(
        history,
        list,
    ):
        raise TypeError(
            f"{lexeme.get('id')}: "
            "lineage.history must be a list"
        )

    lineage["supersedes"] = supersedes
    lineage["history"] = history

    lineage.setdefault(
        "superseded_by",
        None,
    )

    lexeme["lineage"] = lineage

    return lineage


def ensure_provenance(
    lexeme: dict[str, Any],
) -> None:
    provenance = lexeme.get(
        "provenance"
    )

    if isinstance(
        provenance,
        dict,
    ):
        return

    if isinstance(
        provenance,
        list,
    ):
        lexeme["provenance"] = {
            "sources": [
                str(value)
                for value in provenance
            ],
            "authority": "user",
            "confidence": "confirmed",
        }

        return

    if isinstance(
        provenance,
        str,
    ):
        lexeme["provenance"] = {
            "sources": [
                provenance
            ],
            "authority": "user",
            "confidence": "confirmed",
        }

        return

    lexeme["provenance"] = {
        "sources": [
            "lexical-migration-20260809"
        ],
        "authority": "user",
        "confidence": "confirmed",
    }


def active_by_canonical(
    lexemes: list[dict[str, Any]],
    canonical: str,
) -> list[dict[str, Any]]:
    target = canonical.casefold()

    return [
        lexeme
        for lexeme in lexemes
        if (
            str(
                lexeme.get(
                    "canonical",
                    "",
                )
            ).casefold()
            == target
            and lexeme.get(
                "status"
            )
            == "active"
        )
    ]


def restore_kindred_and_kinship(
    registry: dict[str, Any],
) -> None:
    lexemes = registry["lexemes"]

    if not isinstance(
        lexemes,
        list,
    ):
        raise TypeError(
            "registry.lexemes must be a list"
        )

    by_id = {
        str(lexeme.get("id")): lexeme
        for lexeme in lexemes
        if isinstance(
            lexeme,
            dict,
        )
        and lexeme.get("id")
    }

    kindred = by_id.get(
        KINDRED_ID
    )

    if kindred is None:
        matches = active_by_canonical(
            lexemes,
            "Kindred",
        )

        if len(matches) != 1:
            raise RuntimeError(
                "Unable to resolve one "
                "active Kindred lexeme"
            )

        kindred = matches[0]

    kindred["id"] = KINDRED_ID
    kindred["canonical"] = "Kindred"
    kindred["concept"] = (
        CURRENT_KINDRED_CONCEPT
    )
    kindred["status"] = "active"

    ensure_provenance(kindred)

    kindred_lineage = ensure_lineage(
        kindred
    )

    historical_kinship_ids = {
        "lex:history:kinship",
        KINSHIP_ID,
    }

    kindred_lineage["supersedes"] = [
        predecessor
        for predecessor
        in kindred_lineage[
            "supersedes"
        ]
        if str(predecessor)
        not in historical_kinship_ids
    ]

    kindred_lineage["history"] = [
        event
        for event
        in kindred_lineage[
            "history"
        ]
        if not (
            isinstance(
                event,
                Mapping,
            )
            and (
                str(
                    event.get(
                        "predecessor",
                        "",
                    )
                )
                in historical_kinship_ids
                or str(
                    event.get(
                        "historical_term",
                        "",
                    )
                ).casefold()
                == "kinship"
            )
        )
    ]

    kindred_lineage[
        "superseded_by"
    ] = None

    historical_kinship = by_id.get(
        "lex:history:kinship"
    )

    if historical_kinship is not None:
        lexemes.remove(
            historical_kinship
        )

    existing_service = by_id.get(
        KINSHIP_ID
    )

    if existing_service is None:
        kinship = {
            "id": KINSHIP_ID,
            "canonical": "Kinship",
            "concept": (
                CURRENT_KINSHIP_CONCEPT
            ),
            "description": (
                "Active Savant service that "
                "compiles functional relationship "
                "planes from Kindred relationship "
                "authority."
            ),
            "layer": "shard00",
            "status": "active",
            "dependencies": [
                KINDRED_ID
            ],
            "relationships": [
                {
                    "type": "depends_on",
                    "target": KINDRED_ID,
                }
            ],
            "lineage": {
                "supersedes": [],
                "superseded_by": None,
                "history": [],
            },
            "provenance": {
                "sources": [
                    "service:kinship",
                    "runtime/kinship/",
                    "constitutional-bootstrap",
                ],
                "authority": "accepted",
                "confidence": "confirmed",
            },
            "metadata": {
                "system_dependency": (
                    "system:kindred"
                ),
                "service_identity": (
                    "service:kinship"
                ),
                "implementation": (
                    "runtime/kinship"
                ),
                "implemented_through": (
                    "exile:modus"
                ),
            },
        }

        lexemes.append(
            kinship
        )

    else:
        existing_service[
            "canonical"
        ] = "Kinship"

        existing_service[
            "concept"
        ] = CURRENT_KINSHIP_CONCEPT

        existing_service[
            "status"
        ] = "active"

        ensure_provenance(
            existing_service
        )

        lineage = ensure_lineage(
            existing_service
        )

        lineage["supersedes"] = []
        lineage["superseded_by"] = None

        dependencies = (
            existing_service.get(
                "dependencies"
            )
        )

        if not isinstance(
            dependencies,
            list,
        ):
            dependencies = []

        if (
            KINDRED_ID
            not in dependencies
        ):
            dependencies.append(
                KINDRED_ID
            )

        existing_service[
            "dependencies"
        ] = dependencies

        metadata = (
            existing_service.get(
                "metadata"
            )
        )

        if not isinstance(
            metadata,
            dict,
        ):
            metadata = {}

        metadata.update(
            {
                "system_dependency": (
                    "system:kindred"
                ),
                "service_identity": (
                    "service:kinship"
                ),
                "implementation": (
                    "runtime/kinship"
                ),
                "implemented_through": (
                    "exile:modus"
                ),
            }
        )

        existing_service[
            "metadata"
        ] = metadata

    reserved = registry.get(
        "reserved"
    )

    if isinstance(
        reserved,
        list,
    ):
        registry["reserved"] = [
            value
            for value in reserved
            if str(value).casefold()
            != "kinship"
        ]


def repair_historical_concepts(
    registry: dict[str, Any],
) -> int:
    lexemes = registry["lexemes"]

    by_id = {
        str(item["id"]): item
        for item in lexemes
        if isinstance(
            item,
            Mapping,
        )
        and item.get("id")
    }

    changed = 0

    for lexeme in lexemes:
        if not isinstance(
            lexeme,
            dict,
        ):
            continue

        lexeme_id = str(
            lexeme.get(
                "id",
                "",
            )
        )

        if not lexeme_id.startswith(
            "lex:history:"
        ):
            continue

        if (
            lexeme.get("status")
            != "superseded"
        ):
            continue

        lineage = lexeme.get(
            "lineage"
        )

        if not isinstance(
            lineage,
            Mapping,
        ):
            continue

        successor_id = lineage.get(
            "superseded_by"
        )

        successor = by_id.get(
            str(successor_id)
        )

        successor_name = (
            str(
                successor.get(
                    "canonical",
                    successor_id,
                )
            )
            if successor
            else str(
                successor_id
            )
        )

        historical_name = str(
            lexeme.get(
                "canonical",
                "",
            )
        ).strip()

        concept = (
            "Historical lexical predecessor "
            f"{historical_name} of "
            f"{successor_name}"
        )

        if (
            lexeme.get("concept")
            != concept
        ):
            lexeme["concept"] = (
                concept
            )

            changed += 1

    return changed


def repair_constitution_path(
    registry: dict[str, Any],
) -> None:
    if not CONSTITUTION_PATH.is_file():
        raise FileNotFoundError(
            CONSTITUTION_PATH
        )

    registry["constitution"] = (
        "docs/LEXICON_CONSTITUTION.md"
    )


def method_bounds(
    source: str,
    method_name: str,
    next_method_name: str,
) -> tuple[int, int]:
    start_marker = (
        f"    def {method_name}("
    )

    next_marker = (
        f"    def {next_method_name}("
    )

    start = source.find(
        start_marker
    )

    if start < 0:
        raise RuntimeError(
            f"method not found: "
            f"{method_name}"
        )

    end = source.find(
        next_marker,
        start + len(
            start_marker
        ),
    )

    if end < 0:
        raise RuntimeError(
            "following method not found: "
            f"{next_method_name}"
        )

    return start, end


def replace_method(
    source: str,
    method_name: str,
    next_method_name: str,
    replacement: str,
) -> str:
    start, end = method_bounds(
        source,
        method_name,
        next_method_name,
    )

    return (
        source[:start]
        + replacement.rstrip()
        + "\n\n"
        + source[end:]
    )


VALIDATE_TERMINOLOGY = r'''
    def validate_terminology(self) -> None:
        context = require_context(
            self.context
        )

        active_kindred = []
        active_kinship = []

        for lexeme in context.lexemes:
            canonical = optional_string(
                lexeme.get(
                    "canonical"
                )
            )

            status = optional_string(
                lexeme.get(
                    "status"
                )
            )

            normalized = (
                normalize_term(
                    canonical
                )
                if canonical
                else ""
            )

            if (
                status == "active"
                and normalized
                == "kindred"
            ):
                active_kindred.append(
                    lexeme
                )

            if (
                status == "active"
                and normalized
                == "kinship"
            ):
                active_kinship.append(
                    lexeme
                )

        if len(active_kindred) != 1:
            self.report.add(
                code=(
                    "terminology."
                    "kindred_cardinality"
                ),
                severity="error",
                validator="terminology",
                message=(
                    "Exactly one active "
                    "Kindred lexeme is "
                    "required."
                ),
                metadata={
                    "count": len(
                        active_kindred
                    )
                },
            )

        if len(active_kinship) != 1:
            self.report.add(
                code=(
                    "terminology."
                    "kinship_cardinality"
                ),
                severity="error",
                validator="terminology",
                message=(
                    "Exactly one active "
                    "Kinship service lexeme "
                    "is required."
                ),
                metadata={
                    "count": len(
                        active_kinship
                    )
                },
            )

        if (
            len(active_kindred) == 1
            and len(active_kinship) == 1
        ):
            kindred_id = (
                context.lexeme_identity(
                    active_kindred[0]
                )
            )

            kinship = (
                active_kinship[0]
            )

            kinship_id = (
                context.lexeme_identity(
                    kinship
                )
            )

            dependencies = (
                kinship.get(
                    "dependencies"
                )
            )

            if not isinstance(
                dependencies,
                list,
            ):
                dependencies = []

            if (
                kindred_id
                not in dependencies
            ):
                self.report.add(
                    code=(
                        "terminology."
                        "kinship_kindred_"
                        "dependency_missing"
                    ),
                    severity="error",
                    validator=(
                        "terminology"
                    ),
                    message=(
                        "Kinship must depend "
                        "on Kindred."
                    ),
                    lexeme_id=kinship_id,
                    field="dependencies",
                    value=kindred_id,
                )

        for lexeme in context.lexemes:
            status = optional_string(
                lexeme.get(
                    "status"
                )
            )

            if status in {
                "superseded",
                "reserved",
                "deprecated",
            }:
                continue

            lexeme_id = (
                context.lexeme_identity(
                    lexeme
                )
            )

            self._scan_value_for_forbidden_terms(
                value=lexeme,
                validator="terminology",
                lexeme_id=lexeme_id,
                field_path="lexeme",
            )

        self._scan_repository_terminology()
'''


SCAN_VALUE = r'''
    def _scan_value_for_forbidden_terms(
        self,
        value: Any,
        validator: str,
        lexeme_id: str | None,
        field_path: str,
    ) -> None:
        historical_fields = (
            "lexeme.lineage",
            "lexeme.aliases",
            "lexeme.reserved_spellings",
            "lexeme.provenance",
        )

        if any(
            field_path.startswith(
                prefix
            )
            for prefix
            in historical_fields
        ):
            return

        if isinstance(
            value,
            str,
        ):
            normalized_value = (
                normalize_term(
                    value
                )
            )

            if (
                lexeme_id
                == "lex:service:kinship"
                and contains_term(
                    value,
                    "kinship",
                )
            ):
                return

            for forbidden in (
                FORBIDDEN_TERMS
            ):
                if (
                    forbidden
                    == "kinship"
                ):
                    continue

                if contains_term(
                    value,
                    forbidden,
                ):
                    self.report.add(
                        code=(
                            "terminology."
                            "forbidden_term"
                        ),
                        severity="error",
                        validator=validator,
                        message=(
                            "Forbidden "
                            "terminology detected."
                        ),
                        lexeme_id=lexeme_id,
                        field=field_path,
                        value=forbidden,
                    )

            return

        if isinstance(
            value,
            Mapping,
        ):
            for key, item in (
                value.items()
            ):
                self._scan_value_for_forbidden_terms(
                    value=item,
                    validator=validator,
                    lexeme_id=lexeme_id,
                    field_path=(
                        f"{field_path}.{key}"
                    ),
                )

            return

        if isinstance(
            value,
            list,
        ):
            for index, item in (
                enumerate(value)
            ):
                self._scan_value_for_forbidden_terms(
                    value=item,
                    validator=validator,
                    lexeme_id=lexeme_id,
                    field_path=(
                        f"{field_path}"
                        f"[{index}]"
                    ),
                )
'''


SCAN_REPOSITORY = r'''
    def _scan_repository_terminology(
        self,
    ) -> None:
        if self.scan_root is None:
            return

        historical_or_authority_files = {
            "registry.yaml",
            "TERMINOLOGY_EVOLUTION.yaml",
            "registry.schema.yaml",
            "lexeme.schema.yaml",
            "constitution_registry.yaml",
            "LEXICON_CONSTITUTION.md",
        }

        for path in iter_text_files(
            self.scan_root
        ):
            if path.name in (
                SCAN_EXCLUDED_FILENAMES
            ):
                continue

            try:
                relative = (
                    path.resolve()
                    .relative_to(
                        self.scan_root.resolve()
                    )
                )
            except ValueError:
                continue

            if "backups" in (
                relative.parts
            ):
                continue

            if path.name in (
                historical_or_authority_files
            ):
                continue

            try:
                text = path.read_text(
                    encoding="utf-8",
                    errors="replace",
                )
            except OSError as exc:
                self.report.add(
                    code=(
                        "terminology."
                        "scan_read_failed"
                    ),
                    severity="warning",
                    validator="terminology",
                    message=(
                        "Unable to scan "
                        "repository file."
                    ),
                    path=str(path),
                    metadata={
                        "error": str(exc)
                    },
                )

                continue

            for line_number, line in (
                enumerate(
                    text.splitlines(),
                    start=1,
                )
            ):
                for forbidden in (
                    FORBIDDEN_TERMS
                ):
                    if (
                        forbidden
                        == "kinship"
                    ):
                        continue

                    if not contains_term(
                        line,
                        forbidden,
                    ):
                        continue

                    self.report.add(
                        code=(
                            "terminology."
                            "forbidden_term_in_file"
                        ),
                        severity="error",
                        validator="terminology",
                        message=(
                            "Forbidden terminology "
                            "detected in current "
                            "repository content."
                        ),
                        value=forbidden,
                        path=str(path),
                        line=line_number,
                    )
'''


def repair_validator() -> None:
    source = VALIDATOR_PATH.read_text(
        encoding="utf-8"
    )

    source = replace_method(
        source,
        "validate_terminology",
        "_scan_value_for_forbidden_terms",
        VALIDATE_TERMINOLOGY,
    )

    source = replace_method(
        source,
        "_scan_value_for_forbidden_terms",
        "_scan_repository_terminology",
        SCAN_VALUE,
    )

    source = replace_method(
        source,
        "_scan_repository_terminology",
        "_validate_reference_field",
        SCAN_REPOSITORY,
    )

    VALIDATOR_PATH.write_text(
        source,
        encoding="utf-8",
    )


def validate_local(
    registry: dict[str, Any],
) -> None:
    lexemes = registry[
        "lexemes"
    ]

    active_kindred = (
        active_by_canonical(
            lexemes,
            "Kindred",
        )
    )

    active_kinship = (
        active_by_canonical(
            lexemes,
            "Kinship",
        )
    )

    if len(
        active_kindred
    ) != 1:
        raise RuntimeError(
            "Expected exactly one "
            "active Kindred"
        )

    if len(
        active_kinship
    ) != 1:
        raise RuntimeError(
            "Expected exactly one "
            "active Kinship"
        )

    if (
        active_kindred[0]["id"]
        == active_kinship[0]["id"]
    ):
        raise RuntimeError(
            "Kindred and Kinship "
            "must have distinct identities"
        )

    if (
        active_kindred[0]["id"]
        not in active_kinship[0].get(
            "dependencies",
            [],
        )
    ):
        raise RuntimeError(
            "Kinship must depend "
            "on Kindred"
        )

    kindred_lineage = (
        ensure_lineage(
            active_kindred[0]
        )
    )

    if any(
        str(value).casefold()
        == "lex:history:kinship"
        for value in kindred_lineage[
            "supersedes"
        ]
    ):
        raise RuntimeError(
            "Kindred must not "
            "supersede Kinship"
        )

    if (
        registry.get(
            "constitution"
        )
        != "docs/LEXICON_CONSTITUTION.md"
    ):
        raise RuntimeError(
            "Incorrect constitution path"
        )

    concepts: dict[
        str,
        list[str],
    ] = {}

    for lexeme in lexemes:
        concept = " ".join(
            str(
                lexeme.get(
                    "concept",
                    "",
                )
            )
            .casefold()
            .split()
        )

        if not concept:
            continue

        concepts.setdefault(
            concept,
            [],
        ).append(
            str(
                lexeme.get(
                    "id"
                )
            )
        )

    duplicates = {
        concept: owners
        for concept, owners
        in concepts.items()
        if len(owners) > 1
    }

    if duplicates:
        raise RuntimeError(
            "Duplicate concepts remain: "
            f"{duplicates}"
        )


def main() -> int:
    stamp = utc_stamp()

    backup_root = (
        LEXICON_ROOT
        / "backups"
        / "lexical-finalization-20260809"
        / stamp
    )

    backup_file(
        REGISTRY_PATH,
        backup_root,
    )

    backup_file(
        VALIDATOR_PATH,
        backup_root,
    )

    registry = load_yaml(
        REGISTRY_PATH
    )

    repair_constitution_path(
        registry
    )

    repair_historical_concepts(
        registry
    )

    restore_kindred_and_kinship(
        registry
    )

    for lexeme in registry[
        "lexemes"
    ]:
        if not isinstance(
            lexeme,
            dict,
        ):
            raise TypeError(
                "Lexeme must be object"
            )

        ensure_lineage(
            lexeme
        )

        ensure_provenance(
            lexeme
        )

    registry["lexemes"] = sorted(
        registry["lexemes"],
        key=lambda item: (
            0
            if item.get(
                "status"
            )
            == "active"
            else 1,
            str(
                item.get(
                    "id",
                    "",
                )
            ),
        ),
    )

    write_yaml(
        REGISTRY_PATH,
        registry,
    )

    repair_validator()

    validate_local(
        load_yaml(
            REGISTRY_PATH
        )
    )

    print(
        "LEXICON FINALIZATION: complete"
    )

    print(
        "KINDRED: active methodology/system"
    )

    print(
        "KINSHIP: active dependent service"
    )

    print(
        f"BACKUP: {backup_root}"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
