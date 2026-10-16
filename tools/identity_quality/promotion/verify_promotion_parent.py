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

PARENT_ATTACHMENT_ROOT = (
    ROOT
    / "reports"
    / "identity_quality"
    / "promotion"
    / "parent-attachments"
)

VERIFICATION_ROOT = (
    ROOT
    / "reports"
    / "identity_quality"
    / "promotion"
    / "parent-verifications"
)

PYTHON = (
    ROOT
    / "bin"
    / "identity-quality-python"
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


def latest_attachment_paths() -> list[Path]:
    if not PARENT_ATTACHMENT_ROOT.is_dir():
        return []

    return sorted(
        (
            path
            for path in PARENT_ATTACHMENT_ROOT.glob(
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


def latest_attachment_path() -> Path:
    paths = latest_attachment_paths()

    if not paths:
        raise FileNotFoundError(
            "No parent attachment exists."
        )

    return paths[0]


def resolve_attachment_path(
    declared: Path | None,
) -> Path:
    if declared is None:
        return latest_attachment_path()

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


def validate_attachment(
    attachment: dict[str, Any],
) -> None:
    if attachment.get("mode") != "apply":
        raise ValueError(
            "Parent attachment was not applied."
        )

    if attachment.get("applied") is not True:
        raise ValueError(
            "Parent attachment is not marked applied."
        )

    if attachment.get("passed") is not True:
        raise ValueError(
            "Parent attachment did not pass."
        )

    boundary = attachment.get(
        "boundary"
    )

    if not isinstance(boundary, dict):
        raise ValueError(
            "Parent attachment has no boundary."
        )

    required_false = (
        "authority_transfer",
        "subject_inherits_parent_authority",
        "parent_inherits_subject_authority",
    )

    for field in required_false:
        if boundary.get(field) is not False:
            raise ValueError(
                f"Boundary violation: {field}"
            )

    if boundary.get(
        "contract_governed"
    ) is not True:
        raise ValueError(
            "Attachment is not contract-governed."
        )

    if boundary.get(
        "reversible"
    ) is not True:
        raise ValueError(
            "Attachment is not reversible."
        )


def inspect_definition(
    declared: str,
    expected_sha256: str | None,
) -> dict[str, Any]:
    path = (
        ROOT
        / declared
    ).resolve()

    exists = path.is_file()

    actual_sha256 = (
        sha256_path(path)
        if exists
        else None
    )

    passed = (
        exists
        and (
            expected_sha256 is None
            or expected_sha256
            == actual_sha256
        )
    )

    document: dict[str, Any] | None = None

    if exists:
        document = load_json(path)

    return {
        "path": declared,
        "exists": exists,
        "expected_sha256": (
            expected_sha256
        ),
        "actual_sha256": (
            actual_sha256
        ),
        "passed": passed,
        "document": document,
    }


def has_relationship(
    document: dict[str, Any],
    *,
    relationship_type: str,
    target: str,
    authority_transfer: bool,
    reversible: bool,
) -> bool:
    relationships = document.get(
        "relationships"
    )

    if not isinstance(
        relationships,
        list,
    ):
        return False

    for relationship in relationships:
        if not isinstance(
            relationship,
            dict,
        ):
            continue

        if (
            relationship.get("type")
            == relationship_type
            and relationship.get("target")
            == target
            and relationship.get(
                "authority_transfer"
            )
            is authority_transfer
            and relationship.get(
                "reversible"
            )
            is reversible
        ):
            return True

    return False


def verify_relationships(
    attachment: dict[str, Any],
    subject_record: dict[str, Any],
    parent_record: dict[str, Any],
) -> dict[str, Any]:
    subject_id = attachment[
        "subject"
    ][
        "id"
    ]

    parent_id = attachment[
        "parent"
    ][
        "id"
    ]

    subject_document = subject_record.get(
        "document"
    )

    parent_document = parent_record.get(
        "document"
    )

    subject_passed = (
        isinstance(
            subject_document,
            dict,
        )
        and has_relationship(
            subject_document,
            relationship_type=(
                "attaches_to"
            ),
            target=parent_id,
            authority_transfer=False,
            reversible=True,
        )
    )

    parent_passed = (
        isinstance(
            parent_document,
            dict,
        )
        and has_relationship(
            parent_document,
            relationship_type=(
                "composes"
            ),
            target=subject_id,
            authority_transfer=False,
            reversible=True,
        )
    )

    return {
        "passed": (
            subject_passed
            and parent_passed
        ),
        "subject_relationship": (
            subject_passed
        ),
        "parent_relationship": (
            parent_passed
        ),
    }


def verify_authority_boundary(
    attachment: dict[str, Any],
    subject_record: dict[str, Any],
) -> dict[str, Any]:
    document = subject_record.get(
        "document"
    )

    if not isinstance(
        document,
        dict,
    ):
        return {
            "passed": False,
            "reason": (
                "Subject definition unavailable."
            ),
        }

    authority = document.get(
        "authority"
    )

    if not isinstance(
        authority,
        dict,
    ):
        return {
            "passed": False,
            "reason": (
                "Subject authority mapping missing."
            ),
        }

    checks = {
        "inherited_false": (
            authority.get(
                "inherited",
                False,
            )
            is False
        ),
        "parent_authority_transfer_false": (
            authority.get(
                "parent_authority_transfer"
            )
            is False
        ),
        "attachment_reversible_true": (
            authority.get(
                "attachment_reversible"
            )
            is True
        ),
        "reported_boundary_matches": (
            attachment[
                "boundary"
            ][
                "authority_transfer"
            ]
            is False
        ),
    }

    return {
        "passed": all(
            checks.values()
        ),
        "checks": checks,
    }


def verification_commands() -> list[dict[str, Any]]:
    return [
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


def verify_attachment(
    attachment_path: Path,
) -> dict[str, Any]:
    attachment = load_json(
        attachment_path
    )

    validate_attachment(
        attachment
    )

    subject = attachment[
        "subject"
    ]

    parent = attachment[
        "parent"
    ]

    subject_record = inspect_definition(
        subject[
            "definition"
        ],
        subject.get(
            "after_sha256"
        ),
    )

    parent_record = inspect_definition(
        parent[
            "definition"
        ],
        parent.get(
            "after_sha256"
        ),
    )

    relationships = verify_relationships(
        attachment,
        subject_record,
        parent_record,
    )

    boundary = verify_authority_boundary(
        attachment,
        subject_record,
    )

    commands: list[
        dict[str, Any]
    ] = []

    precommand_passed = all(
        (
            subject_record[
                "passed"
            ],
            parent_record[
                "passed"
            ],
            relationships[
                "passed"
            ],
            boundary[
                "passed"
            ],
        )
    )

    if precommand_passed:
        for operation in verification_commands():
            result = run_command(
                operation[
                    "command"
                ]
            )

            result[
                "id"
            ] = operation[
                "id"
            ]

            commands.append(
                result
            )

            if not result[
                "passed"
            ]:
                break

    commands_passed = (
        bool(commands)
        and all(
            result[
                "passed"
            ]
            for result in commands
        )
    )

    passed = (
        precommand_passed
        and commands_passed
    )

    result: dict[str, Any] = {
        "schema": (
            "savant://identity-quality/"
            "promotion-parent-verification/1.0.0"
        ),
        "operation": (
            "verify_promotion_parent"
        ),
        "generated_at": utc_now(),
        "attachment": {
            "path": relative_path(
                attachment_path
            ),
            "sha256": sha256_path(
                attachment_path
            ),
            "digest": attachment.get(
                "digest"
            ),
        },
        "subject": {
            "id": subject[
                "id"
            ],
            "definition": {
                key: value
                for key, value
                in subject_record.items()
                if key != "document"
            },
        },
        "parent": {
            "id": parent[
                "id"
            ],
            "definition": {
                key: value
                for key, value
                in parent_record.items()
                if key != "document"
            },
        },
        "relationships": relationships,
        "boundary": boundary,
        "commands": {
            "passed": commands_passed,
            "results": commands,
        },
        "passed": passed,
        "statistics": {
            "definition_count": 2,
            "definition_passed_count": sum(
                (
                    subject_record[
                        "passed"
                    ],
                    parent_record[
                        "passed"
                    ],
                )
            ),
            "relationship_passed_count": sum(
                (
                    relationships[
                        "subject_relationship"
                    ],
                    relationships[
                        "parent_relationship"
                    ],
                )
            ),
            "command_count": len(
                commands
            ),
            "command_passed_count": sum(
                command[
                    "passed"
                ]
                for command in commands
            ),
        },
    }

    result[
        "digest"
    ] = digest(
        deterministic_projection(
            result
        )
    )

    return result


def markdown(
    result: dict[str, Any],
) -> str:
    return "\n".join(
        [
            "# Promotion Parent Verification",
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
                f"- Relationships passed: "
                f"**{result['relationships']['passed']}**"
            ),
            (
                f"- Boundary passed: "
                f"**{result['boundary']['passed']}**"
            ),
            (
                f"- Commands passed: "
                f"**{result['commands']['passed']}**"
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
            "Verify an applied parent attachment, "
            "its authority boundary, and its graph links."
        )
    )

    parser.add_argument(
        "--attachment",
        type=Path,
    )

    parser.add_argument(
        "--strict",
        action="store_true",
    )

    parser.add_argument(
        "--output-root",
        type=Path,
        default=VERIFICATION_ROOT,
    )

    arguments = parser.parse_args()

    try:
        attachment_path = (
            resolve_attachment_path(
                arguments.attachment
            )
        )

        result = verify_attachment(
            attachment_path
        )

    except Exception as exc:
        print(
            json.dumps(
                {
                    "operation": (
                        "verify_promotion_parent"
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
        result[
            "subject"
        ][
            "id"
        ]
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
        / (
            f"{run_id}__"
            "parent-verification.json"
        )
    )

    markdown_path = (
        output_root
        / (
            f"{run_id}__"
            "parent-verification.md"
        )
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

    rendered = markdown(
        result
    )

    write_text(
        markdown_path,
        rendered,
    )

    write_text(
        latest_markdown,
        rendered,
    )

    manifest = {
        "generated_at": (
            result[
                "generated_at"
            ]
        ),
        "subject": (
            result[
                "subject"
            ][
                "id"
            ]
        ),
        "parent": (
            result[
                "parent"
            ][
                "id"
            ]
        ),
        "passed": (
            result[
                "passed"
            ]
        ),
        "verification_digest": (
            result[
                "digest"
            ]
        ),
        "files": {
            json_path.name: (
                sha256_path(
                    json_path
                )
            ),
            markdown_path.name: (
                sha256_path(
                    markdown_path
                )
            ),
            latest_json.name: (
                sha256_path(
                    latest_json
                )
            ),
            latest_markdown.name: (
                sha256_path(
                    latest_markdown
                )
            ),
        },
    }

    manifest_path = (
        output_root
        / (
            f"{run_id}__manifest.json"
        )
    )

    write_json(
        manifest_path,
        manifest,
    )

    print(
        json.dumps(
            {
                "operation": (
                    "verify_promotion_parent"
                ),
                "passed": (
                    result[
                        "passed"
                    ]
                ),
                "subject": (
                    result[
                        "subject"
                    ]
                ),
                "parent": (
                    result[
                        "parent"
                    ]
                ),
                "relationships": (
                    result[
                        "relationships"
                    ]
                ),
                "boundary": (
                    result[
                        "boundary"
                    ]
                ),
                "commands": (
                    result[
                        "commands"
                    ]
                ),
                "digest": (
                    result[
                        "digest"
                    ]
                ),
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
        and not result[
            "passed"
        ]
    ):
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
