#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any


ROOT = Path("/root/savant-runtime")

SCAFFOLD_ROOT = (
    ROOT
    / "reports"
    / "identity_quality"
    / "promotion"
    / "scaffolds"
)

EXECUTION_ROOT = (
    ROOT
    / "reports"
    / "identity_quality"
    / "promotion"
    / "execution"
)

VOLATILE_FIELDS = {
    "generated_at",
    "timestamp",
    "started_at",
    "finished_at",
    "duration_seconds",
    "elapsed_seconds",
    "wall_clock_seconds",
}

FILE_ROLES = {
    "contracts",
    "runtime",
    "tests",
    "controller",
    "quality_verifier",
    "attestation_builder",
}

DIRECTORY_ROLES = {
    "reports",
}

SUPPORTED_OPERATIONS = {
    "create",
    "extend",
    "create_or_extend",
}

FORBIDDEN_REPLACEMENT_ROLES = {
    "definition",
    "definition_attachment",
    "parent_attachment",
}

REQUIRED_EXECUTION_STAGES = (
    "preflight",
    "backup",
    "contracts",
    "runtime",
    "controller",
    "tests",
    "definition_attachment",
    "parent_attachment",
    "verification",
    "attestation",
    "promotion_queue_refresh",
)


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
    return re.sub(
        r"[^A-Za-z0-9._-]+",
        "_",
        value,
    ).strip("_")


def latest_scaffold_paths() -> list[Path]:
    if not SCAFFOLD_ROOT.is_dir():
        return []

    return sorted(
        (
            path
            for path in SCAFFOLD_ROOT.glob(
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


def latest_scaffold_path() -> Path:
    paths = latest_scaffold_paths()

    if not paths:
        raise FileNotFoundError(
            "No promotion scaffold exists."
        )

    return paths[0]


def resolve_scaffold_path(
    declared: Path | None,
) -> Path:
    if declared is None:
        return latest_scaffold_path()

    path = declared.expanduser()

    if not path.is_absolute():
        path = ROOT / path

    path = path.resolve()

    if not path.is_file():
        raise FileNotFoundError(path)

    return path


def inspect_path(
    declared: str,
    *,
    directory: bool = False,
) -> dict[str, Any]:
    path = (
        ROOT
        / declared
    ).resolve()

    exists = (
        path.is_dir()
        if directory
        else path.is_file()
    )

    record: dict[str, Any] = {
        "path": declared,
        "absolute_path": str(path),
        "exists": exists,
        "kind": (
            "directory"
            if directory
            else "file"
        ),
    }

    if path.is_file():
        stat = path.stat()

        record.update(
            {
                "size": stat.st_size,
                "mode": oct(
                    stat.st_mode & 0o777
                ),
                "sha256": sha256_path(path),
            }
        )

    return record


def validate_scaffold(
    scaffold: dict[str, Any],
) -> None:
    subject = scaffold.get(
        "subject"
    )

    if not isinstance(subject, dict):
        raise ValueError(
            "Scaffold has no subject."
        )

    identifier = subject.get(
        "id"
    )

    if (
        not isinstance(identifier, str)
        or not identifier.strip()
    ):
        raise ValueError(
            "Scaffold subject has no identifier."
        )

    actions = scaffold.get(
        "actions"
    )

    if (
        not isinstance(actions, list)
        or not actions
    ):
        raise ValueError(
            "Scaffold has no actions."
        )

    for action in actions:
        if not isinstance(action, dict):
            raise ValueError(
                "Scaffold contains invalid action."
            )

        operation = action.get(
            "operation"
        )

        if operation not in SUPPORTED_OPERATIONS:
            raise ValueError(
                f"Unsupported action operation: {operation}"
            )

        role = action.get(
            "role"
        )

        if (
            role in FORBIDDEN_REPLACEMENT_ROLES
            and action.get(
                "replacement_forbidden"
            )
            is not True
        ):
            raise ValueError(
                f"Replacement protection missing for role: {role}"
            )


def normalize_actions(
    scaffold: dict[str, Any],
) -> list[dict[str, Any]]:
    actions = scaffold[
        "actions"
    ]

    normalized: list[
        dict[str, Any]
    ] = []

    for action in sorted(
        actions,
        key=lambda item: (
            int(
                item.get(
                    "position",
                    0,
                )
            ),
            str(
                item.get(
                    "role",
                    "",
                )
            ),
        ),
    ):
        role = str(
            action.get(
                "role",
                ""
            )
        )

        declared_path = action.get(
            "path"
        )

        path_record: dict[str, Any] | None = None

        if isinstance(
            declared_path,
            str,
        ):
            path_record = inspect_path(
                declared_path,
                directory=(
                    role
                    in DIRECTORY_ROLES
                ),
            )

        normalized.append(
            {
                "position": int(
                    action.get(
                        "position",
                        0,
                    )
                ),
                "role": role,
                "operation": action.get(
                    "operation"
                ),
                "path": declared_path,
                "path_state": path_record,
                "replacement_forbidden": bool(
                    action.get(
                        "replacement_forbidden",
                        False,
                    )
                ),
                "requires_backup": bool(
                    path_record
                    and path_record.get(
                        "exists"
                    )
                ),
                "authority_effect": (
                    "none"
                    if role
                    not in {
                        "definition_attachment",
                        "parent_attachment",
                    }
                    else (
                        "extend_declared_authority_metadata"
                    )
                ),
            }
        )

    return normalized


def build_backup_operations(
    scaffold: dict[str, Any],
    actions: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    subject_id = scaffold[
        "subject"
    ][
        "id"
    ]

    backup_root = (
        ROOT
        / "backups"
        / "identity-quality"
        / "promotion"
        / safe_key(
            subject_id
        )
    )

    operations: list[
        dict[str, Any]
    ] = []

    for action in actions:
        path_state = action.get(
            "path_state"
        )

        if (
            not isinstance(path_state, dict)
            or not path_state.get(
                "exists"
            )
            or path_state.get(
                "kind"
            )
            != "file"
        ):
            continue

        source = Path(
            path_state[
                "absolute_path"
            ]
        )

        destination = (
            backup_root
            / timestamp()
            / source.relative_to(
                ROOT
            )
        )

        operations.append(
            {
                "role": action[
                    "role"
                ],
                "source": relative_path(
                    source
                ),
                "source_sha256": path_state.get(
                    "sha256"
                ),
                "destination": relative_path(
                    destination
                ),
                "required": True,
            }
        )

    return operations


def build_preflight_checks(
    scaffold: dict[str, Any],
    actions: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    checks: list[
        dict[str, Any]
    ] = [
        {
            "id": "root.exists",
            "passed": ROOT.is_dir(),
            "value": str(ROOT),
        },
        {
            "id": "subject.identifier",
            "passed": bool(
                scaffold[
                    "subject"
                ][
                    "id"
                ]
            ),
            "value": scaffold[
                "subject"
            ][
                "id"
            ],
        },
        {
            "id": "subject.definition",
            "passed": (
                ROOT
                / scaffold[
                    "subject"
                ][
                    "definition"
                ]
            ).is_file(),
            "value": scaffold[
                "subject"
            ][
                "definition"
            ],
        },
        {
            "id": "scaffold.digest",
            "passed": bool(
                scaffold.get(
                    "digest"
                )
            ),
            "value": scaffold.get(
                "digest"
            ),
        },
    ]

    for action in actions:
        role = action[
            "role"
        ]

        if role in DIRECTORY_ROLES:
            continue

        if (
            action[
                "operation"
            ]
            == "extend"
        ):
            state = action.get(
                "path_state"
            )

            checks.append(
                {
                    "id": (
                        f"action.{role}."
                        "extend_target_exists"
                    ),
                    "passed": bool(
                        isinstance(
                            state,
                            dict,
                        )
                        and state.get(
                            "exists"
                        )
                    ),
                    "value": action.get(
                        "path"
                    ),
                }
            )

    return checks


def build_stage(
    position: int,
    stage_id: str,
    *,
    depends_on: list[str],
    operations: list[dict[str, Any]],
    acceptance: list[str],
    rollback: list[str],
) -> dict[str, Any]:
    return {
        "position": position,
        "id": stage_id,
        "depends_on": depends_on,
        "operations": operations,
        "acceptance": acceptance,
        "rollback": rollback,
        "state": "planned",
    }


def actions_for_roles(
    actions: list[dict[str, Any]],
    roles: set[str],
) -> list[dict[str, Any]]:
    return [
        action
        for action in actions
        if action[
            "role"
        ]
        in roles
    ]


def build_stages(
    scaffold: dict[str, Any],
    actions: list[dict[str, Any]],
    preflight: list[dict[str, Any]],
    backups: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    subject = scaffold[
        "subject"
    ]

    controller = scaffold[
        "target_layout"
    ][
        "controller"
    ]

    stages = [
        build_stage(
            1,
            "preflight",
            depends_on=[],
            operations=preflight,
            acceptance=[
                (
                    "All required roots, definitions, "
                    "digests, and extension targets exist."
                ),
                (
                    "No unsupported operation is admitted."
                ),
            ],
            rollback=[],
        ),
        build_stage(
            2,
            "backup",
            depends_on=[
                "preflight",
            ],
            operations=backups,
            acceptance=[
                (
                    "Every existing file scheduled for "
                    "modification has a content-addressed backup."
                ),
                (
                    "Backup hashes equal source hashes."
                ),
            ],
            rollback=[
                (
                    "Restore every modified file from its "
                    "recorded backup."
                ),
            ],
        ),
        build_stage(
            3,
            "contracts",
            depends_on=[
                "backup",
            ],
            operations=actions_for_roles(
                actions,
                {
                    "contracts",
                },
            ),
            acceptance=[
                (
                    "Versioned strict request, policy, "
                    "result, failure, source, and provenance "
                    "contracts exist."
                ),
                (
                    "Contracts perform no side effects."
                ),
            ],
            rollback=[
                (
                    "Restore prior contract file or remove "
                    "new unreferenced contract file."
                ),
            ],
        ),
        build_stage(
            4,
            "runtime",
            depends_on=[
                "contracts",
            ],
            operations=actions_for_roles(
                actions,
                {
                    "runtime",
                },
            ),
            acceptance=[
                (
                    "Runtime implements bounded capability "
                    "derived from authoritative primitives."
                ),
                (
                    "Runtime excludes volatile telemetry "
                    "from deterministic identity."
                ),
                (
                    "Runtime fails closed when authority "
                    "or evidence is absent."
                ),
            ],
            rollback=[
                (
                    "Restore prior runtime or remove new "
                    "unattached runtime."
                ),
            ],
        ),
        build_stage(
            5,
            "controller",
            depends_on=[
                "runtime",
            ],
            operations=actions_for_roles(
                actions,
                {
                    "controller",
                },
            ),
            acceptance=[
                (
                    "One executable canonical controller exists."
                ),
                (
                    "Controller delegates behavior to runtime."
                ),
                (
                    "Controller exposes example, run, schema, "
                    "test, verify, and status."
                ),
            ],
            rollback=[
                (
                    "Restore prior controller or remove new "
                    "unattached controller."
                ),
            ],
        ),
        build_stage(
            6,
            "tests",
            depends_on=[
                "controller",
            ],
            operations=actions_for_roles(
                actions,
                {
                    "tests",
                },
            ),
            acceptance=[
                (
                    "Unit, property, security, integration, "
                    "recovery, and determinism tests pass."
                ),
                (
                    "Equal requests produce equal authoritative "
                    "result digests."
                ),
                (
                    "Parent authority is never inherited."
                ),
            ],
            rollback=[
                (
                    "Restore prior tests or remove invalid "
                    "new test projection."
                ),
            ],
        ),
        build_stage(
            7,
            "definition_attachment",
            depends_on=[
                "tests",
            ],
            operations=actions_for_roles(
                actions,
                {
                    "definition",
                    "definition_attachment",
                },
            ),
            acceptance=[
                (
                    "Authoritative definition is extended, "
                    "not replaced."
                ),
                (
                    "Runtime evidence, contracts, tests, "
                    "dependencies, relationships, lineage, "
                    "provenance, observability, security, "
                    "lifecycle, and apertures are exposed."
                ),
                (
                    "Source hashes match attached files."
                ),
            ],
            rollback=[
                (
                    "Restore authoritative definition from backup."
                ),
            ],
        ),
        build_stage(
            8,
            "parent_attachment",
            depends_on=[
                "definition_attachment",
            ],
            operations=actions_for_roles(
                actions,
                {
                    "parent_attachment",
                },
            ),
            acceptance=[
                (
                    "Attachment is reversible and contract-governed."
                ),
                (
                    "Authority transfer is false."
                ),
                (
                    "Parent and subject retain separate authority."
                ),
            ],
            rollback=[
                (
                    "Remove attachment relationship and restore "
                    "parent definition from backup."
                ),
            ],
        ),
        build_stage(
            9,
            "verification",
            depends_on=[
                "parent_attachment",
            ],
            operations=[
                {
                    "role": (
                        "subject_controller_verify"
                    ),
                    "command": [
                        str(
                            ROOT
                            / controller
                        ),
                        "verify",
                    ],
                },
                {
                    "role": (
                        "identity_audit"
                    ),
                    "command": [
                        str(
                            ROOT
                            / "bin"
                            / "identityqualityctl"
                        ),
                        "audit",
                    ],
                },
                {
                    "role": (
                        "identity_validation"
                    ),
                    "command": [
                        str(
                            ROOT
                            / "bin"
                            / "identityqualityctl"
                        ),
                        "validate",
                    ],
                },
            ],
            acceptance=[
                (
                    "Subject controller verification passes."
                ),
                (
                    "Identity audit passes."
                ),
                (
                    "Identity validation passes."
                ),
            ],
            rollback=[
                (
                    "Rollback all modified stages when required "
                    "verification fails."
                ),
            ],
        ),
        build_stage(
            10,
            "attestation",
            depends_on=[
                "verification",
            ],
            operations=actions_for_roles(
                actions,
                {
                    "quality_verifier",
                    "attestation_builder",
                    "reports",
                },
            ),
            acceptance=[
                (
                    "Deterministic attestation records subject, "
                    "files, hashes, contracts, tests, authority "
                    "boundaries, and verification results."
                ),
                (
                    "Attestation digest excludes volatile fields."
                ),
            ],
            rollback=[
                (
                    "Discard failed generated attestation "
                    "projections."
                ),
            ],
        ),
        build_stage(
            11,
            "promotion_queue_refresh",
            depends_on=[
                "attestation",
            ],
            operations=[
                {
                    "role": (
                        "promotion_queue_refresh"
                    ),
                    "command": [
                        str(
                            ROOT
                            / "bin"
                            / "identity-promotionctl"
                        ),
                        "strict",
                    ],
                },
            ],
            acceptance=[
                (
                    f"`{subject['id']}` is removed from the "
                    "promotion queue or retains only verified "
                    "unresolved issues."
                ),
                (
                    "The next promotion subject is selected "
                    "deterministically."
                ),
            ],
            rollback=[],
        ),
    ]

    stage_ids = tuple(
        stage[
            "id"
        ]
        for stage in stages
    )

    if stage_ids != REQUIRED_EXECUTION_STAGES:
        raise RuntimeError(
            "Execution stage order is invalid."
        )

    return stages


def build_execution_packet(
    scaffold_path: Path,
) -> dict[str, Any]:
    scaffold = load_json(
        scaffold_path
    )

    validate_scaffold(
        scaffold
    )

    actions = normalize_actions(
        scaffold
    )

    preflight = build_preflight_checks(
        scaffold,
        actions,
    )

    backups = build_backup_operations(
        scaffold,
        actions,
    )

    stages = build_stages(
        scaffold,
        actions,
        preflight,
        backups,
    )

    packet: dict[str, Any] = {
        "schema": (
            "savant://identity-quality/"
            "promotion-execution-packet/1.0.0"
        ),
        "operation": (
            "build_promotion_execution_packet"
        ),
        "generated_at": utc_now(),
        "scaffold": {
            "path": relative_path(
                scaffold_path
            ),
            "sha256": sha256_path(
                scaffold_path
            ),
            "digest": scaffold.get(
                "digest"
            ),
        },
        "subject": scaffold[
            "subject"
        ],
        "authority": scaffold.get(
            "authority",
            {}
        ),
        "constraints": scaffold.get(
            "constraints",
            []
        ),
        "actions": actions,
        "preflight": {
            "checks": preflight,
            "passed": all(
                check[
                    "passed"
                ]
                for check in preflight
            ),
        },
        "backups": {
            "operations": backups,
            "required_count": len(
                backups
            ),
        },
        "stages": stages,
        "execution_policy": {
            "stop_on_failure": True,
            "rollback_on_failure": True,
            "replace_existing_authority": False,
            "authority_transfer": False,
            "preserve_intermediate_results": True,
            "require_attestation": True,
            "require_queue_refresh": True,
        },
        "statistics": {
            "action_count": len(
                actions
            ),
            "preflight_check_count": len(
                preflight
            ),
            "backup_count": len(
                backups
            ),
            "stage_count": len(
                stages
            ),
        },
    }

    packet[
        "digest"
    ] = digest(
        deterministic_projection(
            packet
        )
    )

    return packet


def markdown(
    packet: dict[str, Any],
) -> str:
    subject = packet[
        "subject"
    ]

    lines = [
        "# Identity Promotion Execution Packet",
        "",
        (
            f"- Generated: "
            f"`{packet['generated_at']}`"
        ),
        (
            f"- Digest: "
            f"`{packet['digest']}`"
        ),
        (
            f"- Subject: "
            f"`{subject['id']}`"
        ),
        (
            f"- Kind: "
            f"`{subject['kind']}`"
        ),
        (
            f"- Parent: "
            f"`{subject['parent']}`"
        ),
        (
            f"- Preflight passed: "
            f"**{packet['preflight']['passed']}**"
        ),
        (
            f"- Backup count: "
            f"**{packet['backups']['required_count']}**"
        ),
        "",
        "## Stages",
        "",
    ]

    for stage in packet[
        "stages"
    ]:
        lines.extend(
            [
                (
                    f"### {stage['position']}. "
                    f"`{stage['id']}`"
                ),
                "",
                (
                    f"- Depends on: "
                    f"`{', '.join(stage['depends_on'])}`"
                ),
                (
                    f"- Operations: "
                    f"**{len(stage['operations'])}**"
                ),
                "",
                "Acceptance:",
                "",
            ]
        )

        for item in stage[
            "acceptance"
        ]:
            lines.append(
                f"- {item}"
            )

        if stage[
            "rollback"
        ]:
            lines.extend(
                [
                    "",
                    "Rollback:",
                    "",
                ]
            )

            for item in stage[
                "rollback"
            ]:
                lines.append(
                    f"- {item}"
                )

        lines.append("")

    return "\n".join(
        lines
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Build a deterministic execution packet "
            "for the current identity promotion scaffold."
        )
    )

    parser.add_argument(
        "--scaffold",
        type=Path,
    )

    parser.add_argument(
        "--output-root",
        type=Path,
        default=EXECUTION_ROOT,
    )

    parser.add_argument(
        "--strict",
        action="store_true",
    )

    arguments = parser.parse_args()

    try:
        scaffold_path = resolve_scaffold_path(
            arguments.scaffold
        )

        packet = build_execution_packet(
            scaffold_path
        )

    except Exception as exc:
        print(
            json.dumps(
                {
                    "operation": (
                        "build_promotion_execution_packet"
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
        packet[
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
            "promotion-execution-packet.json"
        )
    )

    markdown_path = (
        output_root
        / (
            f"{run_id}__"
            "promotion-execution-packet.md"
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
        packet,
    )

    write_json(
        latest_json,
        packet,
    )

    rendered = markdown(
        packet
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
            packet[
                "generated_at"
            ]
        ),
        "subject": (
            packet[
                "subject"
            ][
                "id"
            ]
        ),
        "execution_digest": (
            packet[
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

    passed = bool(
        packet[
            "preflight"
        ][
            "passed"
        ]
        and packet[
            "statistics"
        ][
            "stage_count"
        ]
        == len(
            REQUIRED_EXECUTION_STAGES
        )
    )

    print(
        json.dumps(
            {
                "operation": (
                    "build_promotion_execution_packet"
                ),
                "passed": passed,
                "subject": packet[
                    "subject"
                ],
                "digest": packet[
                    "digest"
                ],
                "statistics": packet[
                    "statistics"
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
        and not passed
    ):
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
