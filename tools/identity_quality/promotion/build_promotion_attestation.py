#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any


ROOT = Path("/root/savant-runtime")

PARENT_VERIFICATION_ROOT = (
    ROOT
    / "reports"
    / "identity_quality"
    / "promotion"
    / "parent-verifications"
)

ATTESTATION_ROOT = (
    ROOT
    / "reports"
    / "identity_quality"
    / "promotion"
    / "attestations"
)

IDENTITY_QUALITY = (
    ROOT
    / "bin"
    / "identityqualityctl"
)

PROMOTION_QUEUE = (
    ROOT
    / "bin"
    / "identity-promotionctl"
)

VOLATILE_FIELDS = {
    "generated_at",
    "started_at",
    "finished_at",
    "duration_seconds",
    "elapsed_seconds",
    "wall_clock_seconds",
    "timestamp",
}

REQUIRED_BOUNDARY_VALUES = {
    "authority_transfer": False,
    "subject_inherits_parent_authority": False,
    "parent_inherits_subject_authority": False,
    "contract_governed": True,
    "reversible": True,
}


def utc_now() -> str:
    return (
        dt.datetime.now(dt.timezone.utc)
        .replace(microsecond=0)
        .isoformat()
    )


def timestamp() -> str:
    return dt.datetime.now(
        dt.timezone.utc
    ).strftime("%Y%m%dT%H%M%SZ")


def canonical_bytes(
    value: Any,
) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def digest(
    value: Any,
) -> str:
    return hashlib.sha256(
        canonical_bytes(value)
    ).hexdigest()


def sha256_path(
    path: Path,
) -> str:
    hasher = hashlib.sha256()

    with path.open("rb") as handle:
        for chunk in iter(
            lambda: handle.read(
                1024 * 1024
            ),
            b"",
        ):
            hasher.update(chunk)

    return hasher.hexdigest()


def deterministic_projection(
    value: Any,
) -> Any:
    if isinstance(value, dict):
        return {
            key: deterministic_projection(child)
            for key, child in sorted(
                value.items(),
                key=lambda item: item[0],
            )
            if key not in VOLATILE_FIELDS
        }

    if isinstance(value, list):
        return [
            deterministic_projection(child)
            for child in value
        ]

    if isinstance(value, tuple):
        return tuple(
            deterministic_projection(child)
            for child in value
        )

    return value


def load_json(
    path: Path,
) -> dict[str, Any]:
    value = json.loads(
        path.read_text(
            encoding="utf-8",
        )
    )

    if not isinstance(value, dict):
        raise ValueError(
            f"Expected JSON object: {path}"
        )

    return value


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
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )


def write_text(
    path: Path,
    value: str,
) -> None:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    path.write_text(
        value,
        encoding="utf-8",
    )


def relative_path(
    path: Path,
) -> str:
    try:
        return path.relative_to(
            ROOT
        ).as_posix()

    except ValueError:
        return str(path)


def safe_key(
    value: str,
) -> str:
    return "".join(
        character
        if (
            character.isalnum()
            or character in {
                ".",
                "_",
                "-",
            }
        )
        else "_"
        for character in value
    ).strip("_")


def latest_verification_paths() -> list[Path]:
    if not PARENT_VERIFICATION_ROOT.is_dir():
        return []

    return sorted(
        (
            path
            for path in PARENT_VERIFICATION_ROOT.glob(
                "*/latest.json"
            )
            if path.is_file()
        ),
        key=lambda path: (
            path.stat().st_mtime_ns,
            path.as_posix(),
        ),
        reverse=True,
    )


def latest_verification_path() -> Path:
    paths = latest_verification_paths()

    if not paths:
        raise FileNotFoundError(
            "No parent verification exists."
        )

    return paths[0]


def resolve_verification_path(
    declared: Path | None,
) -> Path:
    if declared is None:
        return latest_verification_path()

    path = declared.expanduser()

    if not path.is_absolute():
        path = ROOT / path

    path = path.resolve()

    if not path.is_file():
        raise FileNotFoundError(path)

    return path


def run_command(
    command: list[str],
) -> dict[str, Any]:
    completed = subprocess.run(
        command,
        cwd=str(ROOT),
        check=False,
        capture_output=True,
        text=True,
    )

    return {
        "command": command,
        "returncode": completed.returncode,
        "passed": (
            completed.returncode == 0
        ),
        "stdout": completed.stdout,
        "stderr": completed.stderr,
        "stdout_sha256": hashlib.sha256(
            completed.stdout.encode(
                "utf-8"
            )
        ).hexdigest(),
        "stderr_sha256": hashlib.sha256(
            completed.stderr.encode(
                "utf-8"
            )
        ).hexdigest(),
    }


def validate_verification(
    verification: dict[str, Any],
) -> None:
    if verification.get("passed") is not True:
        raise ValueError(
            "Parent verification did not pass."
        )

    subject = verification.get(
        "subject"
    )

    parent = verification.get(
        "parent"
    )

    if not isinstance(subject, dict):
        raise ValueError(
            "Parent verification has no subject."
        )

    if not isinstance(parent, dict):
        raise ValueError(
            "Parent verification has no parent."
        )

    for record_name, record in (
        ("subject", subject),
        ("parent", parent),
    ):
        identifier = record.get("id")

        if (
            not isinstance(identifier, str)
            or not identifier.strip()
        ):
            raise ValueError(
                f"{record_name} identifier is missing."
            )

        definition = record.get(
            "definition"
        )

        if not isinstance(definition, dict):
            raise ValueError(
                f"{record_name} definition is missing."
            )

        if definition.get("passed") is not True:
            raise ValueError(
                f"{record_name} definition did not pass."
            )

    relationships = verification.get(
        "relationships"
    )

    if (
        not isinstance(relationships, dict)
        or relationships.get("passed")
        is not True
    ):
        raise ValueError(
            "Parent relationships did not pass."
        )

    boundary = verification.get(
        "boundary"
    )

    if (
        not isinstance(boundary, dict)
        or boundary.get("passed")
        is not True
    ):
        raise ValueError(
            "Parent authority boundary did not pass."
        )


def inspect_definition(
    record: dict[str, Any],
) -> dict[str, Any]:
    definition = record.get(
        "definition"
    )

    if not isinstance(definition, dict):
        raise ValueError(
            "Definition record is invalid."
        )

    declared = definition.get(
        "path"
    )

    if not isinstance(declared, str):
        raise ValueError(
            "Definition path is missing."
        )

    path = (
        ROOT
        / declared
    ).resolve()

    try:
        path.relative_to(ROOT)

    except ValueError as exc:
        raise ValueError(
            f"Definition escapes root: {path}"
        ) from exc

    if not path.is_file():
        raise FileNotFoundError(path)

    document = load_json(path)

    return {
        "id": record.get("id"),
        "path": relative_path(path),
        "sha256": sha256_path(path),
        "deterministic_digest": digest(
            deterministic_projection(
                document
            )
        ),
        "document": document,
    }


def relationship_evidence(
    subject: dict[str, Any],
    parent: dict[str, Any],
) -> dict[str, Any]:
    subject_id = subject["id"]
    parent_id = parent["id"]

    subject_relationships = (
        subject["document"].get(
            "relationships"
        )
    )

    parent_relationships = (
        parent["document"].get(
            "relationships"
        )
    )

    subject_match = None
    parent_match = None

    if isinstance(
        subject_relationships,
        list,
    ):
        for relationship in subject_relationships:
            if not isinstance(
                relationship,
                dict,
            ):
                continue

            if (
                relationship.get("type")
                == "attaches_to"
                and relationship.get("target")
                == parent_id
            ):
                subject_match = relationship
                break

    if isinstance(
        parent_relationships,
        list,
    ):
        for relationship in parent_relationships:
            if not isinstance(
                relationship,
                dict,
            ):
                continue

            if (
                relationship.get("type")
                == "composes"
                and relationship.get("target")
                == subject_id
            ):
                parent_match = relationship
                break

    return {
        "passed": (
            subject_match is not None
            and parent_match is not None
        ),
        "subject_relationship": (
            subject_match
        ),
        "parent_relationship": (
            parent_match
        ),
    }


def authority_evidence(
    subject: dict[str, Any],
    relationships: dict[str, Any],
) -> dict[str, Any]:
    authority = subject[
        "document"
    ].get(
        "authority"
    )

    if not isinstance(authority, dict):
        return {
            "passed": False,
            "reason": (
                "Subject authority mapping missing."
            ),
        }

    subject_relationship = relationships.get(
        "subject_relationship"
    )

    parent_relationship = relationships.get(
        "parent_relationship"
    )

    checks = {
        "subject_authority_inherited_false": (
            authority.get(
                "inherited",
                False,
            )
            is False
        ),
        "subject_parent_transfer_false": (
            authority.get(
                "parent_authority_transfer"
            )
            is False
        ),
        "subject_attachment_reversible_true": (
            authority.get(
                "attachment_reversible"
            )
            is True
        ),
        "subject_relationship_transfer_false": (
            isinstance(
                subject_relationship,
                dict,
            )
            and subject_relationship.get(
                "authority_transfer"
            )
            is False
        ),
        "subject_relationship_reversible_true": (
            isinstance(
                subject_relationship,
                dict,
            )
            and subject_relationship.get(
                "reversible"
            )
            is True
        ),
        "parent_relationship_transfer_false": (
            isinstance(
                parent_relationship,
                dict,
            )
            and parent_relationship.get(
                "authority_transfer"
            )
            is False
        ),
        "parent_relationship_reversible_true": (
            isinstance(
                parent_relationship,
                dict,
            )
            and parent_relationship.get(
                "reversible"
            )
            is True
        ),
    }

    return {
        "passed": all(
            checks.values()
        ),
        "checks": checks,
    }


def implementation_evidence(
    subject: dict[str, Any],
) -> dict[str, Any]:
    document = subject[
        "document"
    ]

    evidence = document.get(
        "implementation_evidence"
    )

    runtime = document.get(
        "runtime"
    )

    validation = document.get(
        "validation"
    )

    contracts = document.get(
        "contracts"
    )

    checks = {
        "implementation_evidence_mapping": (
            isinstance(
                evidence,
                dict,
            )
        ),
        "runtime_complete": (
            isinstance(runtime, dict)
            and runtime.get(
                "implementation"
            )
            == "complete"
        ),
        "runtime_deterministic": (
            isinstance(runtime, dict)
            and runtime.get(
                "deterministic"
            )
            is True
        ),
        "runtime_entrypoints_present": (
            isinstance(runtime, dict)
            and isinstance(
                runtime.get(
                    "entrypoints"
                ),
                list,
            )
            and bool(
                runtime.get(
                    "entrypoints"
                )
            )
        ),
        "validation_present": (
            isinstance(
                validation,
                dict,
            )
        ),
        "contracts_present": (
            isinstance(
                contracts,
                dict,
            )
        ),
    }

    file_records: dict[str, Any] = {}

    if isinstance(evidence, dict):
        for role, record in sorted(
            evidence.items()
        ):
            if not isinstance(record, dict):
                file_records[role] = {
                    "passed": False,
                    "reason": (
                        "Evidence record is invalid."
                    ),
                }
                continue

            declared = record.get("path")
            expected = record.get("sha256")

            if not isinstance(
                declared,
                str,
            ):
                file_records[role] = {
                    "passed": False,
                    "reason": (
                        "Evidence path is missing."
                    ),
                }
                continue

            path = (
                ROOT
                / declared
            ).resolve()

            exists = path.is_file()

            actual = (
                sha256_path(path)
                if exists
                else None
            )

            file_records[role] = {
                "path": declared,
                "exists": exists,
                "expected_sha256": expected,
                "actual_sha256": actual,
                "passed": (
                    exists
                    and expected == actual
                ),
            }

    files_passed = (
        bool(file_records)
        and all(
            record.get(
                "passed",
                False,
            )
            for record in file_records.values()
        )
    )

    return {
        "passed": (
            all(
                checks.values()
            )
            and files_passed
        ),
        "checks": checks,
        "files": file_records,
    }


def global_verification() -> dict[str, Any]:
    operations = [
        {
            "id": "identity.audit",
            "command": [
                str(IDENTITY_QUALITY),
                "audit",
            ],
        },
        {
            "id": "identity.validation",
            "command": [
                str(IDENTITY_QUALITY),
                "validate",
            ],
        },
        {
            "id": "promotion.queue",
            "command": [
                str(PROMOTION_QUEUE),
                "strict",
            ],
        },
    ]

    results: list[
        dict[str, Any]
    ] = []

    for operation in operations:
        result = run_command(
            operation["command"]
        )

        result["id"] = operation["id"]

        results.append(result)

        if not result["passed"]:
            break

    return {
        "passed": (
            len(results)
            == len(operations)
            and all(
                result["passed"]
                for result in results
            )
        ),
        "results": results,
    }


def queue_evidence(
    subject_id: str,
) -> dict[str, Any]:
    queue_path = (
        ROOT
        / "reports"
        / "identity_quality"
        / "promotion"
        / "latest.json"
    )

    if not queue_path.is_file():
        return {
            "passed": False,
            "reason": (
                "Promotion queue report is missing."
            ),
            "path": relative_path(
                queue_path
            ),
        }

    queue = load_json(queue_path)

    records = queue.get("records")
    items = queue.get("queue")

    subject_record = None
    queue_item = None

    if isinstance(records, list):
        for record in records:
            if (
                isinstance(record, dict)
                and record.get("id")
                == subject_id
            ):
                subject_record = record
                break

    if isinstance(items, list):
        for item in items:
            if (
                isinstance(item, dict)
                and item.get("id")
                == subject_id
            ):
                queue_item = item
                break

    passed = (
        isinstance(subject_record, dict)
        and subject_record.get("passed")
        is True
        and queue_item is None
    )

    return {
        "passed": passed,
        "path": relative_path(
            queue_path
        ),
        "sha256": sha256_path(
            queue_path
        ),
        "queue_digest": queue.get(
            "digest"
        ),
        "subject_record": subject_record,
        "queue_item": queue_item,
    }


def build_attestation(
    verification_path: Path,
) -> dict[str, Any]:
    verification = load_json(
        verification_path
    )

    validate_verification(
        verification
    )

    subject = inspect_definition(
        verification["subject"]
    )

    parent = inspect_definition(
        verification["parent"]
    )

    relationships = relationship_evidence(
        subject,
        parent,
    )

    authority = authority_evidence(
        subject,
        relationships,
    )

    implementation = implementation_evidence(
        subject
    )

    global_checks = global_verification()

    queue = queue_evidence(
        subject["id"]
    )

    passed = all(
        (
            relationships["passed"],
            authority["passed"],
            implementation["passed"],
            global_checks["passed"],
            queue["passed"],
        )
    )

    attestation: dict[str, Any] = {
        "schema": (
            "savant://identity-quality/"
            "promotion-attestation/1.0.0"
        ),
        "operation": (
            "build_promotion_attestation"
        ),
        "generated_at": utc_now(),
        "verification": {
            "path": relative_path(
                verification_path
            ),
            "sha256": sha256_path(
                verification_path
            ),
            "digest": verification.get(
                "digest"
            ),
        },
        "subject": {
            key: value
            for key, value in subject.items()
            if key != "document"
        },
        "parent": {
            key: value
            for key, value in parent.items()
            if key != "document"
        },
        "relationships": relationships,
        "authority": authority,
        "implementation": implementation,
        "global_verification": (
            global_checks
        ),
        "promotion_queue": queue,
        "boundary": {
            **REQUIRED_BOUNDARY_VALUES,
        },
        "passed": passed,
        "statistics": {
            "relationship_count": 2,
            "relationship_passed_count": sum(
                (
                    relationships.get(
                        "subject_relationship"
                    )
                    is not None,
                    relationships.get(
                        "parent_relationship"
                    )
                    is not None,
                )
            ),
            "implementation_file_count": len(
                implementation.get(
                    "files",
                    {}
                )
            ),
            "implementation_file_passed_count": sum(
                record.get(
                    "passed",
                    False,
                )
                for record in implementation.get(
                    "files",
                    {}
                ).values()
            ),
            "global_command_count": len(
                global_checks[
                    "results"
                ]
            ),
            "global_command_passed_count": sum(
                result[
                    "passed"
                ]
                for result in global_checks[
                    "results"
                ]
            ),
        },
    }

    attestation["digest"] = digest(
        deterministic_projection(
            attestation
        )
    )

    return attestation


def markdown(
    result: dict[str, Any],
) -> str:
    return "\n".join(
        [
            "# Identity Promotion Attestation",
            "",
            (
                f"- Generated: "
                f"`{result['generated_at']}`"
            ),
            (
                f"- Subject: "
                f"`{result['subject']['id']}`"
            ),
            (
                f"- Parent: "
                f"`{result['parent']['id']}`"
            ),
            (
                f"- Relationships: "
                f"**{result['relationships']['passed']}**"
            ),
            (
                f"- Authority boundary: "
                f"**{result['authority']['passed']}**"
            ),
            (
                f"- Implementation: "
                f"**{result['implementation']['passed']}**"
            ),
            (
                f"- Global verification: "
                f"**{result['global_verification']['passed']}**"
            ),
            (
                f"- Removed from queue: "
                f"**{result['promotion_queue']['passed']}**"
            ),
            (
                f"- Passed: "
                f"**{result['passed']}**"
            ),
            (
                f"- Digest: "
                f"`{result['digest']}`"
            ),
            "",
        ]
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Build the final deterministic attestation "
            "for a completed identity promotion."
        )
    )

    parser.add_argument(
        "--verification",
        type=Path,
    )

    parser.add_argument(
        "--strict",
        action="store_true",
    )

    parser.add_argument(
        "--output-root",
        type=Path,
        default=ATTESTATION_ROOT,
    )

    arguments = parser.parse_args()

    try:
        verification_path = (
            resolve_verification_path(
                arguments.verification
            )
        )

        result = build_attestation(
            verification_path
        )

    except Exception as exc:
        print(
            json.dumps(
                {
                    "operation": (
                        "build_promotion_attestation"
                    ),
                    "passed": False,
                    "error": {
                        "type": type(
                            exc
                        ).__name__,
                        "message": str(
                            exc
                        ),
                    },
                },
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )
        )

        return 1

    subject_key = safe_key(
        result["subject"]["id"]
    )

    output_root = (
        arguments.output_root
        .expanduser()
        .resolve()
        / subject_key
    )

    output_root.mkdir(
        parents=True,
        exist_ok=True,
    )

    run_id = timestamp()

    json_path = (
        output_root
        / f"{run_id}__promotion-attestation.json"
    )

    markdown_path = (
        output_root
        / f"{run_id}__promotion-attestation.md"
    )

    latest_json = (
        output_root
        / "latest.json"
    )

    latest_markdown = (
        output_root
        / "latest.md"
    )

    write_json(
        json_path,
        result,
    )

    write_json(
        latest_json,
        result,
    )

    rendered = markdown(result)

    write_text(
        markdown_path,
        rendered,
    )

    write_text(
        latest_markdown,
        rendered,
    )

    manifest = {
        "generated_at": result[
            "generated_at"
        ],
        "subject": result[
            "subject"
        ][
            "id"
        ],
        "parent": result[
            "parent"
        ][
            "id"
        ],
        "passed": result[
            "passed"
        ],
        "attestation_digest": result[
            "digest"
        ],
        "files": {
            json_path.name: sha256_path(
                json_path
            ),
            markdown_path.name: sha256_path(
                markdown_path
            ),
            latest_json.name: sha256_path(
                latest_json
            ),
            latest_markdown.name: sha256_path(
                latest_markdown
            ),
        },
    }

    manifest_path = (
        output_root
        / f"{run_id}__manifest.json"
    )

    write_json(
        manifest_path,
        manifest,
    )

    print(
        json.dumps(
            {
                "operation": (
                    "build_promotion_attestation"
                ),
                "passed": result[
                    "passed"
                ],
                "subject": result[
                    "subject"
                ],
                "parent": result[
                    "parent"
                ],
                "relationships": result[
                    "relationships"
                ],
                "authority": result[
                    "authority"
                ],
                "implementation": result[
                    "implementation"
                ],
                "global_verification": result[
                    "global_verification"
                ],
                "promotion_queue": result[
                    "promotion_queue"
                ],
                "digest": result[
                    "digest"
                ],
                "reports": {
                    "json": str(
                        json_path
                    ),
                    "markdown": str(
                        markdown_path
                    ),
                    "latest_json": str(
                        latest_json
                    ),
                    "latest_markdown": str(
                        latest_markdown
                    ),
                    "manifest": str(
                        manifest_path
                    ),
                },
            },
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )

    if (
        arguments.strict
        and not result["passed"]
    ):
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
