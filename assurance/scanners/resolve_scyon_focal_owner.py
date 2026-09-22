#!/usr/bin/env python3

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(
    os.environ.get(
        "SAVANT_ROOT",
        "/root/savant-runtime",
    )
).resolve()

SCYON_TIERS = (
    "trait",
    "quirk",
    "prodigal",
    "exile",
    "innate",
    "gate",
    "portal",
    "obelisk",
)

AUTHORITY_ROOTS = (
    ROOT / "authority",
    ROOT / "canon",
    ROOT / "canon-system",
    ROOT / "edifices",
    ROOT / "ontology",
    ROOT / "runtime",
)

OUTPUT_ROOT = (
    ROOT
    / "runtime/reports/scyon-owner-resolution"
)

JSON_SUFFIXES = {
    ".json",
    ".jsonl",
}

TEXT_SUFFIXES = {
    ".md",
    ".txt",
    ".yaml",
    ".yml",
    ".cue",
    ".py",
}

IMPLEMENTATION_RELATIONS = {
    "implemented_through",
    "implemented_by",
    "executed_through",
    "provided_through",
}

GOVERNANCE_RELATIONS = {
    "owned_by",
    "governed_by",
    "responsible_to",
}

DIRECT_OWNER_FIELDS = {
    "scyon_owner",
    "scyon_owner_id",
    "implementation_owner",
    "implementation_owner_id",
}


class ResolutionError(RuntimeError):
    pass


@dataclass(
    frozen=True,
    slots=True,
)
class Evidence:
    path: str
    sha256: str
    authority_class: str
    evidence_kind: str
    relation: str | None
    candidate_id: str | None
    candidate_tier: str | None
    candidate_role: str
    target: str

    def as_dict(
        self,
    ) -> dict[str, Any]:
        return {
            "path": self.path,
            "sha256": self.sha256,
            "authority_class": self.authority_class,
            "evidence_kind": self.evidence_kind,
            "relation": self.relation,
            "candidate_id": self.candidate_id,
            "candidate_tier": self.candidate_tier,
            "candidate_role": self.candidate_role,
            "target": self.target,
        }


def require(
    condition: bool,
    message: str,
) -> None:
    if not condition:
        raise ResolutionError(
            message
        )


def sha256_file(
    path: Path,
) -> str:
    digest = hashlib.sha256()

    with path.open(
        "rb"
    ) as handle:
        for chunk in iter(
            lambda: handle.read(
                1024 * 1024
            ),
            b"",
        ):
            digest.update(
                chunk
            )

    return digest.hexdigest()


def scyon_identity(
    value: Any,
) -> tuple[
    str,
    str,
] | None:
    if not isinstance(
        value,
        str,
    ):
        return None

    if ":" not in value:
        return None

    tier, name = value.split(
        ":",
        1,
    )

    tier = tier.strip().lower()
    name = name.strip()

    if (
        tier not in SCYON_TIERS
        or not name
    ):
        return None

    return (
        tier,
        f"{tier}:{name}",
    )


def authority_class(
    path: Path,
) -> str:
    relative = str(
        path.relative_to(
            ROOT
        )
    )

    if relative.startswith(
        "authority/accepted-decisions/"
    ):
        return "accepted-decision"

    if relative.startswith(
        "authority/"
    ):
        return "authority"

    if "/authority/" in relative:
        return "authority"

    if relative.startswith(
        "canon/"
    ):
        return "canon"

    if relative.startswith(
        "canon-system/"
    ):
        return "canon-system"

    if relative.endswith(
        "/definition.json"
    ):
        return "identity-definition"

    if relative.startswith(
        "runtime/"
    ):
        return "verified-implementation"

    return "source-evidence"


def authority_weight(
    classification: str,
) -> int:
    return {
        "accepted-decision": 600,
        "authority": 500,
        "canon": 400,
        "canon-system": 400,
        "identity-definition": 350,
        "verified-implementation": 300,
        "source-evidence": 100,
    }.get(
        classification,
        0,
    )


def iter_candidate_files(
) -> Iterable[Path]:
    seen: set[Path] = set()

    for root in AUTHORITY_ROOTS:
        if not root.exists():
            continue

        for path in root.rglob(
            "*"
        ):
            if (
                not path.is_file()
                or path in seen
            ):
                continue

            if (
                path.suffix.lower()
                not in (
                    JSON_SUFFIXES
                    | TEXT_SUFFIXES
                )
            ):
                continue

            seen.add(
                path
            )

            yield path.resolve()


def contains_target(
    value: Any,
    target: str,
) -> bool:
    if isinstance(
        value,
        str,
    ):
        return value == target

    if isinstance(
        value,
        list,
    ):
        return any(
            contains_target(
                item,
                target,
            )
            for item in value
        )

    if isinstance(
        value,
        dict,
    ):
        return any(
            contains_target(
                item,
                target,
            )
            for item in value.values()
        )

    return False


def direct_owner_candidates(
    value: Any,
    target: str,
) -> set[str]:
    result: set[str] = set()

    if isinstance(
        value,
        list,
    ):
        for item in value:
            result.update(
                direct_owner_candidates(
                    item,
                    target,
                )
            )

        return result

    if not isinstance(
        value,
        dict,
    ):
        return result

    if contains_target(
        value,
        target,
    ):
        for key in (
            DIRECT_OWNER_FIELDS
        ):
            identity = scyon_identity(
                value.get(
                    key
                )
            )

            if identity:
                result.add(
                    identity[1]
                )

    for item in value.values():
        result.update(
            direct_owner_candidates(
                item,
                target,
            )
        )

    return result


def relationship_evidence(
    value: Any,
    target: str,
) -> list[
    tuple[
        str,
        str,
        str,
    ]
]:
    """
    Returns tuples:

        candidate_role,
        relation_type,
        candidate_identity
    """

    result: list[
        tuple[
            str,
            str,
            str,
        ]
    ] = []

    if isinstance(
        value,
        list,
    ):
        for item in value:
            result.extend(
                relationship_evidence(
                    item,
                    target,
                )
            )

        return result

    if not isinstance(
        value,
        dict,
    ):
        return result

    object_id = value.get(
        "id"
    )

    if object_id == target:
        relationships = value.get(
            "relationships",
            [],
        )

        if isinstance(
            relationships,
            list,
        ):
            for relationship in relationships:
                if not isinstance(
                    relationship,
                    dict,
                ):
                    continue

                relation = str(
                    relationship.get(
                        "type",
                        "",
                    )
                ).strip()

                relation_target = (
                    relationship.get(
                        "target"
                    )
                )

                identity = (
                    scyon_identity(
                        relation_target
                    )
                )

                if identity:
                    if (
                        relation
                        in IMPLEMENTATION_RELATIONS
                    ):
                        result.append(
                            (
                                "implementation-owner",
                                relation,
                                identity[1],
                            )
                        )

                    elif (
                        relation
                        in GOVERNANCE_RELATIONS
                    ):
                        result.append(
                            (
                                "governance-owner",
                                relation,
                                identity[1],
                            )
                        )

    for item in value.values():
        result.extend(
            relationship_evidence(
                item,
                target,
            )
        )

    return result


def scan_json(
    path: Path,
    target: str,
) -> list[Evidence]:
    try:
        if (
            path.suffix.lower()
            == ".jsonl"
        ):
            value: Any = [
                json.loads(line)
                for line
                in path.read_text(
                    encoding="utf-8",
                    errors="replace",
                ).splitlines()
                if line.strip()
            ]

        else:
            value = json.loads(
                path.read_text(
                    encoding="utf-8",
                    errors="replace",
                )
            )

    except (
        json.JSONDecodeError,
        UnicodeDecodeError,
    ):
        return []

    if not contains_target(
        value,
        target,
    ):
        return []

    classification = (
        authority_class(
            path
        )
    )

    source_digest = (
        sha256_file(
            path
        )
    )

    result: list[
        Evidence
    ] = []

    for candidate in sorted(
        direct_owner_candidates(
            value,
            target,
        )
    ):
        result.append(
            Evidence(
                path=str(path),
                sha256=source_digest,
                authority_class=(
                    classification
                ),
                evidence_kind=(
                    "explicit-scyon-owner-field"
                ),
                relation=None,
                candidate_id=(
                    candidate
                ),
                candidate_tier=(
                    candidate.split(
                        ":",
                        1,
                    )[0]
                ),
                candidate_role=(
                    "implementation-owner"
                ),
                target=target,
            )
        )

    for (
        role,
        relation,
        candidate,
    ) in relationship_evidence(
        value,
        target,
    ):
        result.append(
            Evidence(
                path=str(path),
                sha256=source_digest,
                authority_class=(
                    classification
                ),
                evidence_kind=(
                    "explicit-relationship"
                ),
                relation=relation,
                candidate_id=(
                    candidate
                ),
                candidate_tier=(
                    candidate.split(
                        ":",
                        1,
                    )[0]
                ),
                candidate_role=role,
                target=target,
            )
        )

    if not result:
        result.append(
            Evidence(
                path=str(path),
                sha256=source_digest,
                authority_class=(
                    classification
                ),
                evidence_kind=(
                    "target-reference-only"
                ),
                relation=None,
                candidate_id=None,
                candidate_tier=None,
                candidate_role=(
                    "non-owner-reference"
                ),
                target=target,
            )
        )

    return result


def scan_text(
    path: Path,
    target: str,
) -> list[Evidence]:
    text = path.read_text(
        encoding="utf-8",
        errors="replace",
    )

    if target not in text:
        return []

    classification = (
        authority_class(
            path
        )
    )

    source_digest = (
        sha256_file(
            path
        )
    )

    tier_pattern = (
        "|".join(
            SCYON_TIERS
        )
    )

    patterns = (
        (
            "implementation-owner",
            "implemented_through",
            (
                rf"{re.escape(target)}"
                rf".{{0,300}}?"
                rf"implemented[_ -]through"
                rf".{{0,80}}?"
                rf"(({tier_pattern}):"
                rf"[A-Za-z0-9_.-]+)"
            ),
        ),
        (
            "implementation-owner",
            "implemented_by",
            (
                rf"{re.escape(target)}"
                rf".{{0,300}}?"
                rf"implemented[_ -]by"
                rf".{{0,80}}?"
                rf"(({tier_pattern}):"
                rf"[A-Za-z0-9_.-]+)"
            ),
        ),
        (
            "implementation-owner",
            "explicit-scyon-owner",
            (
                rf"{re.escape(target)}"
                rf".{{0,300}}?"
                rf"(?:scyon[_ -]owner|"
                rf"implementation[_ -]owner)"
                rf".{{0,80}}?"
                rf"(({tier_pattern}):"
                rf"[A-Za-z0-9_.-]+)"
            ),
        ),
    )

    result: list[
        Evidence
    ] = []

    for (
        role,
        relation,
        pattern,
    ) in patterns:
        for match in re.finditer(
            pattern,
            text,
            flags=(
                re.IGNORECASE
                | re.DOTALL
            ),
        ):
            identity = (
                scyon_identity(
                    match.group(1)
                )
            )

            if not identity:
                continue

            result.append(
                Evidence(
                    path=str(path),
                    sha256=source_digest,
                    authority_class=(
                        classification
                    ),
                    evidence_kind=(
                        "explicit-textual-relationship"
                    ),
                    relation=relation,
                    candidate_id=(
                        identity[1]
                    ),
                    candidate_tier=(
                        identity[0]
                    ),
                    candidate_role=role,
                    target=target,
                )
            )

    if result:
        return result

    return [
        Evidence(
            path=str(path),
            sha256=source_digest,
            authority_class=(
                classification
            ),
            evidence_kind=(
                "target-reference-only"
            ),
            relation=None,
            candidate_id=None,
            candidate_tier=None,
            candidate_role=(
                "non-owner-reference"
            ),
            target=target,
        )
    ]


def rank_candidates(
    evidence: list[Evidence],
    role: str,
) -> list[
    dict[str, Any]
]:
    grouped: dict[
        str,
        list[Evidence],
    ] = {}

    for item in evidence:
        if (
            item.candidate_role
            != role
            or item.candidate_id
            is None
        ):
            continue

        grouped.setdefault(
            item.candidate_id,
            [],
        ).append(
            item
        )

    result: list[
        dict[str, Any]
    ] = []

    for (
        candidate_id,
        records,
    ) in grouped.items():
        highest_weight = max(
            authority_weight(
                item.authority_class
            )
            for item in records
        )

        result.append(
            {
                "candidate_id": (
                    candidate_id
                ),
                "candidate_tier": (
                    candidate_id.split(
                        ":",
                        1,
                    )[0]
                ),
                "highest_authority_weight": (
                    highest_weight
                ),
                "evidence_count": len(
                    records
                ),
                "authority_classes": sorted(
                    {
                        item.authority_class
                        for item in records
                    }
                ),
                "relations": sorted(
                    {
                        item.relation
                        for item in records
                        if item.relation
                    }
                ),
            }
        )

    result.sort(
        key=lambda item: (
            -int(
                item[
                    "highest_authority_weight"
                ]
            ),
            -int(
                item[
                    "evidence_count"
                ]
            ),
            str(
                item[
                    "candidate_id"
                ]
            ),
        )
    )

    return result


def choose_candidate(
    ranked: list[
        dict[str, Any]
    ],
) -> tuple[
    str,
    str | None,
    str | None,
]:
    if not ranked:
        return (
            "unresolved",
            None,
            None,
        )

    highest_weight = ranked[
        0
    ][
        "highest_authority_weight"
    ]

    strongest = [
        item
        for item in ranked
        if item[
            "highest_authority_weight"
        ]
        == highest_weight
    ]

    if len(
        strongest
    ) != 1:
        return (
            "authority-conflict",
            None,
            None,
        )

    selected = strongest[
        0
    ]

    return (
        "explicit-owner-found",
        str(
            selected[
                "candidate_id"
            ]
        ),
        str(
            selected[
                "candidate_tier"
            ]
        ),
    )


def resolve(
    target: str,
) -> dict[str, Any]:
    evidence: list[
        Evidence
    ] = []

    files_scanned = 0

    for path in (
        iter_candidate_files()
    ):
        files_scanned += 1

        if (
            path.suffix.lower()
            in JSON_SUFFIXES
        ):
            evidence.extend(
                scan_json(
                    path,
                    target,
                )
            )

        else:
            evidence.extend(
                scan_text(
                    path,
                    target,
                )
            )

    implementation_candidates = (
        rank_candidates(
            evidence,
            "implementation-owner",
        )
    )

    governance_candidates = (
        rank_candidates(
            evidence,
            "governance-owner",
        )
    )

    (
        resolution,
        owner_id,
        owner_tier,
    ) = choose_candidate(
        implementation_candidates
    )

    return {
        "schema": (
            "savant://assurance/"
            "scyon-owner-resolution/1.1.0"
        ),
        "target": target,
        "resolution": resolution,
        "scyon_owner_id": (
            owner_id
        ),
        "scyon_owner_tier": (
            owner_tier
        ),
        "owner_basis": (
            "explicit implementation identity"
            if owner_id
            else None
        ),
        "governance_owner_is_distinct": True,
        "implementation_owner_candidates": (
            implementation_candidates
        ),
        "governance_owner_candidates": (
            governance_candidates
        ),
        "files_scanned": (
            files_scanned
        ),
        "reference_count": len(
            evidence
        ),
        "explicit_implementation_evidence_count": sum(
            1
            for item in evidence
            if item.candidate_role
            == "implementation-owner"
        ),
        "explicit_governance_evidence_count": sum(
            1
            for item in evidence
            if item.candidate_role
            == "governance-owner"
        ),
        "inference_used": False,
        "semantic_similarity_used": False,
        "authority_mutation_performed": False,
        "physical_mutation_performed": False,
        "evidence": [
            item.as_dict()
            for item in evidence
        ],
    }


def write_json(
    path: Path,
    value: Any,
) -> None:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    path.write_text(
        json.dumps(
            value,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Resolve the explicit "
            "Scyon-bearing implementation "
            "identity for a service without "
            "conflating service governance."
        )
    )

    parser.add_argument(
        "target",
    )

    parser.add_argument(
        "--output",
        type=Path,
        default=None,
    )

    arguments = (
        parser.parse_args()
    )

    try:
        report = resolve(
            arguments.target
        )

        output = arguments.output

        if output is None:
            safe_target = re.sub(
                r"[^A-Za-z0-9_.-]+",
                "-",
                arguments.target,
            ).strip(
                "-"
            )

            output = (
                OUTPUT_ROOT
                / f"{safe_target}.json"
            )

        output = (
            output.resolve()
        )

        try:
            output.relative_to(
                ROOT
            )

        except ValueError as exc:
            raise ResolutionError(
                (
                    "output escapes "
                    "Savant root: "
                    f"{output}"
                )
            ) from exc

        write_json(
            output,
            report,
        )

        print(
            json.dumps(
                {
                    "target": (
                        report[
                            "target"
                        ]
                    ),
                    "resolution": (
                        report[
                            "resolution"
                        ]
                    ),
                    "scyon_owner_id": (
                        report[
                            "scyon_owner_id"
                        ]
                    ),
                    "scyon_owner_tier": (
                        report[
                            "scyon_owner_tier"
                        ]
                    ),
                    "explicit_implementation_evidence_count": (
                        report[
                            "explicit_implementation_evidence_count"
                        ]
                    ),
                    "governance_owner_is_distinct": True,
                    "inference_used": False,
                    "output": str(
                        output
                    ),
                },
                indent=2,
                sort_keys=True,
            )
        )

        if (
            report[
                "resolution"
            ]
            == "authority-conflict"
        ):
            return 2

        return 0

    except (
        OSError,
        ValueError,
        KeyError,
        ResolutionError,
    ) as exc:
        print(
            (
                "ERROR: "
                f"{type(exc).__name__}: "
                f"{exc}"
            ),
            file=sys.stderr,
        )

        return 1


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
