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

PROMOTION_ROOT = (
    ROOT
    / "reports"
    / "identity_quality"
    / "promotion"
)

SUBJECT_REPORT_ROOT = (
    PROMOTION_ROOT
    / "subjects"
)

SCAFFOLD_REPORT_ROOT = (
    PROMOTION_ROOT
    / "scaffolds"
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

SUPPORTED_KINDS = {
    "exile",
    "prodigal",
    "quirk",
}


def utc_now() -> str:
    return (
        dt.datetime.now(
            dt.timezone.utc
        )
        .replace(
            microsecond=0
        )
        .isoformat()
    )


def timestamp() -> str:
    return dt.datetime.now(
        dt.timezone.utc
    ).strftime(
        "%Y%m%dT%H%M%SZ"
    )


def canonical_bytes(
    value: Any,
) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(
            ",",
            ":",
        ),
    ).encode(
        "utf-8"
    )


def digest(
    value: Any,
) -> str:
    return hashlib.sha256(
        canonical_bytes(
            value
        )
    ).hexdigest()


def sha256_path(
    path: Path,
) -> str:
    hasher = hashlib.sha256()

    with path.open(
        "rb"
    ) as handle:
        for chunk in iter(
            lambda: handle.read(
                1024
                * 1024
            ),
            b"",
        ):
            hasher.update(
                chunk
            )

    return hasher.hexdigest()


def deterministic_projection(
    value: Any,
) -> Any:
    if isinstance(
        value,
        dict,
    ):
        return {
            key: deterministic_projection(
                child
            )
            for key, child in sorted(
                value.items(),
                key=lambda item: item[
                    0
                ],
            )
            if key
            not in VOLATILE_FIELDS
        }

    if isinstance(
        value,
        list,
    ):
        return [
            deterministic_projection(
                child
            )
            for child in value
        ]

    if isinstance(
        value,
        tuple,
    ):
        return tuple(
            deterministic_projection(
                child
            )
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

    if not isinstance(
        value,
        dict,
    ):
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
        return str(
            path
        )


def safe_subject_key(
    value: str,
) -> str:
    normalized = re.sub(
        r"[^A-Za-z0-9._-]+",
        "_",
        value,
    )

    return normalized.strip(
        "_"
    )


def safe_python_name(
    value: str,
) -> str:
    normalized = re.sub(
        r"[^A-Za-z0-9_]+",
        "_",
        value,
    ).lower()

    normalized = re.sub(
        r"_+",
        "_",
        normalized,
    ).strip(
        "_"
    )

    if not normalized:
        raise ValueError(
            "Cannot derive Python name."
        )

    if normalized[
        0
    ].isdigit():
        normalized = (
            "_"
            + normalized
        )

    return normalized


def latest_packet_paths() -> list[Path]:
    if not SUBJECT_REPORT_ROOT.is_dir():
        return []

    return sorted(
        (
            path
            for path in SUBJECT_REPORT_ROOT.glob(
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


def latest_packet_path() -> Path:
    paths = latest_packet_paths()

    if not paths:
        raise FileNotFoundError(
            "No promotion packet exists."
        )

    return paths[
        0
    ]


def resolve_packet_path(
    declared: Path | None,
) -> Path:
    if declared is None:
        return latest_packet_path()

    path = declared.expanduser()

    if not path.is_absolute():
        path = (
            ROOT
            / path
        )

    path = path.resolve()

    if not path.is_file():
        raise FileNotFoundError(
            path
        )

    return path


def inspect_target(
    declared: str,
    *,
    directory: bool = False,
) -> dict[str, Any]:
    path = (
        ROOT
        / declared
    ).resolve()

    record: dict[
        str,
        Any,
    ] = {
        "path": declared,
        "absolute_path": str(
            path
        ),
        "expected_kind": (
            "directory"
            if directory
            else "file"
        ),
        "exists": (
            path.is_dir()
            if directory
            else path.is_file()
        ),
    }

    if path.is_file():
        stat = path.stat()

        record.update(
            {
                "size": stat.st_size,
                "mode": oct(
                    stat.st_mode
                    & 0o777
                ),
                "sha256": sha256_path(
                    path
                ),
            }
        )

    return record


def validate_packet(
    packet: dict[str, Any],
) -> None:
    subject = packet.get(
        "subject"
    )

    if not isinstance(
        subject,
        dict,
    ):
        raise ValueError(
            "Promotion packet has no subject."
        )

    identifier = subject.get(
        "id"
    )

    if (
        not isinstance(
            identifier,
            str,
        )
        or not identifier.strip()
    ):
        raise ValueError(
            "Promotion subject has no identifier."
        )

    kind = subject.get(
        "kind"
    )

    if kind not in SUPPORTED_KINDS:
        raise ValueError(
            f"Unsupported subject kind: {kind}"
        )

    layout = packet.get(
        "target_layout"
    )

    if not isinstance(
        layout,
        dict,
    ):
        raise ValueError(
            "Promotion packet has no target layout."
        )

    for required in (
        "definition",
        "contracts",
        "runtime",
        "tests",
        "controller",
        "reports",
    ):
        value = layout.get(
            required
        )

        if (
            not isinstance(
                value,
                str,
            )
            or not value.strip()
        ):
            raise ValueError(
                f"Target layout is missing: {required}"
            )


def subject_name(
    packet: dict[str, Any],
) -> str:
    subject = packet[
        "subject"
    ]

    for field in (
        "name",
        "id",
    ):
        value = subject.get(
            field
        )

        if (
            isinstance(
                value,
                str,
            )
            and value.strip()
        ):
            if field == "id":
                return value.rsplit(
                    ".",
                    1,
                )[
                    -1
                ]

            return value.strip()

    raise ValueError(
        "Cannot resolve subject name."
    )


def parent_id(
    packet: dict[str, Any],
) -> str | None:
    subject = packet[
        "subject"
    ]

    value = subject.get(
        "parent"
    )

    if (
        isinstance(
            value,
            str,
        )
        and value.strip()
    ):
        return value.strip()

    return None


def build_contract_model_plan(
    kind: str,
    python_name: str,
) -> dict[str, Any]:
    title = "".join(
        segment.capitalize()
        for segment in python_name.split(
            "_"
        )
    )

    return {
        "module": (
            f"{python_name}_contracts"
        ),
        "contract_version": "1.0.0",
        "strict_base_model": (
            "StrictModel"
        ),
        "request_model": (
            f"{title}Request"
        ),
        "policy_model": (
            f"{title}Policy"
        ),
        "result_model": (
            f"{title}Result"
        ),
        "failure_model": (
            "FailureRecord"
        ),
        "source_model": (
            "SourceReference"
        ),
        "provenance_model": (
            "ProvenanceEnvelope"
        ),
        "authority_enum": (
            "AuthorityState"
        ),
        "kind": kind,
        "requirements": [
            (
                "All models forbid undeclared fields."
            ),
            (
                "All models are immutable after validation."
            ),
            (
                "Requests expose purpose, policy, "
                "authority, and provenance."
            ),
            (
                "Results expose passed state, failure, "
                "metrics, and provenance."
            ),
            (
                "Contracts contain no runtime side effects."
            ),
            (
                "Contract versions are explicit."
            ),
        ],
    }


def build_runtime_plan(
    kind: str,
    python_name: str,
) -> dict[str, Any]:
    return {
        "runtime_id": (
            f"{kind}.{python_name}.runtime"
        ),
        "runtime_version": "1.0.0",
        "module": (
            f"{python_name}_runtime"
        ),
        "functions": [
            "canonical_bytes",
            "digest",
            "deterministic_projection",
            "build_provenance",
            "validate_request",
            "execute",
            "example_request",
            "load_request",
            "write_result",
            "main",
        ],
        "deterministic_exclusions": sorted(
            VOLATILE_FIELDS
        ),
        "requirements": [
            (
                "Runtime behavior must derive from "
                "the authoritative definition."
            ),
            (
                "Runtime must remain independently useful."
            ),
            (
                "Runtime must fail closed when authority "
                "or implementation evidence is absent."
            ),
            (
                "Equal requests must produce equal "
                "authoritative result digests."
            ),
            (
                "Volatile telemetry must remain outside "
                "deterministic identity."
            ),
            (
                "No undeclared network, subprocess, "
                "filesystem, provider, or secret authority."
            ),
            (
                "Every result must preserve lineage "
                "and provenance."
            ),
        ],
    }


def build_test_plan(
    python_name: str,
) -> dict[str, Any]:
    return {
        "module": (
            f"test_{python_name}_runtime"
        ),
        "required_tests": [
            "test_example_request_succeeds",
            (
                "test_equal_requests_produce_"
                "equal_result_digests"
            ),
            (
                "test_canonical_serialization_"
                "is_stable"
            ),
            (
                "test_result_preserves_"
                "provenance"
            ),
            (
                "test_runtime_fails_closed_"
                "without_authority"
            ),
            (
                "test_runtime_rejects_"
                "undeclared_capability"
            ),
            (
                "test_volatile_telemetry_"
                "does_not_change_identity"
            ),
            (
                "test_parent_authority_"
                "is_not_inherited"
            ),
        ],
        "test_classes": [
            "unit",
            "property",
            "security",
            "integration",
            "recovery",
            "determinism",
        ],
    }


def build_controller_plan(
    python_name: str,
) -> dict[str, Any]:
    return {
        "name": (
            f"{python_name}ctl"
        ),
        "commands": [
            "example",
            "run",
            "schema",
            "test",
            "verify",
            "status",
        ],
        "python": (
            "bin/identity-quality-python"
        ),
        "requirements": [
            (
                "One canonical executable controller."
            ),
            (
                "Controller delegates logic to runtime."
            ),
            (
                "Verify runs compile, tests, example, "
                "runtime execution, and result validation."
            ),
            (
                "Controller returns nonzero status "
                "on any failed verification stage."
            ),
        ],
    }


def build_definition_patch_plan(
    packet: dict[str, Any],
    python_name: str,
) -> dict[str, Any]:
    subject = packet[
        "subject"
    ]

    layout = packet[
        "target_layout"
    ]

    parent = parent_id(
        packet
    )

    return {
        "definition": layout[
            "definition"
        ],
        "subject_id": subject[
            "id"
        ],
        "parent_id": parent,
        "runtime": {
            "implementation": (
                "complete"
            ),
            "entrypoints": [
                layout[
                    "runtime"
                ],
            ],
            "commands": [
                layout[
                    "controller"
                ],
            ],
            "deterministic": True,
            "side_effects": [],
        },
        "validation": {
            "unit_tests": [
                layout[
                    "tests"
                ],
            ],
            "integration_tests": [],
            "property_tests": [
                (
                    "equal_requests_produce_"
                    "equal_result_digests"
                ),
                (
                    "canonical_serialization_"
                    "is_stable"
                ),
                (
                    "volatile_telemetry_does_"
                    "not_change_identity"
                ),
            ],
            "security_tests": [
                (
                    "runtime_fails_closed_"
                    "without_authority"
                ),
                (
                    "runtime_rejects_"
                    "undeclared_capability"
                ),
                (
                    "parent_authority_is_"
                    "not_inherited"
                ),
            ],
        },
        "relationships": (
            [
                {
                    "type": (
                        "attaches_to"
                    ),
                    "target": parent,
                    "direction": (
                        "outbound"
                    ),
                    "authority_transfer": (
                        False
                    ),
                    "reversible": True,
                }
            ]
            if parent
            else []
        ),
        "dependencies": {
            "required": [
                {
                    "id": (
                        "python.pydantic"
                    ),
                    "kind": (
                        "library"
                    ),
                    "required": True,
                },
            ],
            "runtime": [
                {
                    "id": (
                        f"{python_name}.contracts"
                    ),
                    "kind": (
                        "contract_module"
                    ),
                    "required": True,
                },
            ],
            "optional": [],
            "external": [],
        },
        "apertures": [
            {
                "id": (
                    f"{subject['id']}.attachment"
                ),
                "purpose": (
                    "Admit compatible future attachments "
                    "without replacing the promoted identity."
                ),
                "admission": (
                    "Requires explicit authority, versioned "
                    "contracts, provenance, security review, "
                    "deterministic fallback, and passing tests."
                ),
            },
        ],
    }


def build_attachment_plan(
    packet: dict[str, Any],
) -> dict[str, Any]:
    subject = packet[
        "subject"
    ]

    parent = parent_id(
        packet
    )

    return {
        "required": (
            parent is not None
        ),
        "subject": subject[
            "id"
        ],
        "parent": parent,
        "authority_transfer": False,
        "reversible": True,
        "requirements": [
            (
                "Parent retains its declared authority."
            ),
            (
                "Subject retains its internal authority."
            ),
            (
                "No secrets, provider selection, registry "
                "mutation, or policy bypass is inherited."
            ),
            (
                "Attachment is contract-governed."
            ),
            (
                "Attachment failures preserve reasons "
                "and provenance."
            ),
        ],
    }


def build_backup_plan(
    layout: dict[str, str],
    subject_key: str,
) -> dict[str, Any]:
    backup_root = (
        ROOT
        / "backups"
        / "identity-quality"
        / "promotion"
        / subject_key
    )

    sources: list[
        dict[str, Any]
    ] = []

    for key in (
        "definition",
        "contracts",
        "runtime",
        "tests",
        "controller",
    ):
        declared = layout[
            key
        ]

        path = (
            ROOT
            / declared
        ).resolve()

        sources.append(
            {
                "role": key,
                "path": declared,
                "exists": path.is_file(),
                "sha256": (
                    sha256_path(
                        path
                    )
                    if path.is_file()
                    else None
                ),
            }
        )

    return {
        "root": relative_path(
            backup_root
        ),
        "sources": sources,
        "policy": (
            "Back up every existing authoritative or "
            "runtime file before modification."
        ),
    }


def build_actions(
    packet: dict[str, Any],
) -> list[dict[str, Any]]:
    layout = packet[
        "target_layout"
    ]

    existing = packet.get(
        "existing",
        {}
    )

    existing_layout = (
        existing.get(
            "layout",
            {}
        )
        if isinstance(
            existing,
            dict,
        )
        else {}
    )

    actions: list[
        dict[str, Any]
    ] = []

    order = (
        "definition",
        "contracts",
        "runtime",
        "tests",
        "controller",
        "reports",
    )

    for position, role in enumerate(
        order,
        start=1,
    ):
        declared = layout[
            role
        ]

        record = existing_layout.get(
            role,
            {}
        )

        exists = (
            bool(
                record.get(
                    "exists"
                )
            )
            if isinstance(
                record,
                dict,
            )
            else False
        )

        actions.append(
            {
                "position": position,
                "role": role,
                "path": declared,
                "exists": exists,
                "operation": (
                    "extend"
                    if exists
                    else "create"
                ),
                "replacement_forbidden": (
                    exists
                ),
            }
        )

    actions.extend(
        [
            {
                "position": 7,
                "role": (
                    "definition_attachment"
                ),
                "path": layout[
                    "definition"
                ],
                "operation": (
                    "extend"
                ),
                "replacement_forbidden": (
                    True
                ),
            },
            {
                "position": 8,
                "role": (
                    "parent_attachment"
                ),
                "path": None,
                "operation": (
                    "create_or_extend"
                ),
                "replacement_forbidden": (
                    True
                ),
            },
            {
                "position": 9,
                "role": (
                    "quality_verifier"
                ),
                "path": (
                    f"bin/{safe_python_name(subject_name(packet))}"
                    "-quality-verify"
                ),
                "operation": (
                    "create_or_extend"
                ),
                "replacement_forbidden": (
                    True
                ),
            },
            {
                "position": 10,
                "role": (
                    "attestation_builder"
                ),
                "path": (
                    "tools/identity_quality/"
                    "promotion/attestations/"
                    f"{safe_python_name(subject_name(packet))}/"
                    "build_reference_attestation.py"
                ),
                "operation": (
                    "create_or_extend"
                ),
                "replacement_forbidden": (
                    True
                ),
            },
        ]
    )

    return actions


def markdown(
    scaffold: dict[str, Any],
) -> str:
    subject = scaffold[
        "subject"
    ]

    lines = [
        "# Identity Promotion Scaffold",
        "",
        (
            f"- Generated: "
            f"`{scaffold['generated_at']}`"
        ),
        (
            f"- Digest: "
            f"`{scaffold['digest']}`"
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
        "",
        "## Actions",
        "",
    ]

    for action in scaffold[
        "actions"
    ]:
        lines.append(
            (
                f"{action['position']}. "
                f"`{action['operation']}` "
                f"`{action['role']}` "
                f"at `{action['path']}`"
            )
        )

    lines.extend(
        [
            "",
            "## Contracts",
            "",
        ]
    )

    contracts = scaffold[
        "contracts"
    ]

    lines.extend(
        [
            (
                f"- Request: "
                f"`{contracts['request_model']}`"
            ),
            (
                f"- Policy: "
                f"`{contracts['policy_model']}`"
            ),
            (
                f"- Result: "
                f"`{contracts['result_model']}`"
            ),
            "",
            "## Runtime",
            "",
        ]
    )

    for requirement in scaffold[
        "runtime"
    ][
        "requirements"
    ]:
        lines.append(
            f"- {requirement}"
        )

    lines.extend(
        [
            "",
            "## Tests",
            "",
        ]
    )

    for test in scaffold[
        "tests"
    ][
        "required_tests"
    ]:
        lines.append(
            f"- `{test}`"
        )

    lines.extend(
        [
            "",
            "## Authority Boundary",
            "",
        ]
    )

    for requirement in scaffold[
        "attachment"
    ][
        "requirements"
    ]:
        lines.append(
            f"- {requirement}"
        )

    lines.append(
        ""
    )

    return "\n".join(
        lines
    )


def build_scaffold(
    packet_path: Path,
) -> dict[str, Any]:
    packet = load_json(
        packet_path
    )

    validate_packet(
        packet
    )

    subject = packet[
        "subject"
    ]

    layout = packet[
        "target_layout"
    ]

    name = subject_name(
        packet
    )

    python_name = safe_python_name(
        name
    )

    subject_key = safe_subject_key(
        subject[
            "id"
        ]
    )

    kind = subject[
        "kind"
    ]

    scaffold: dict[
        str,
        Any,
    ] = {
        "schema": (
            "savant://identity-quality/"
            "promotion-scaffold/1.0.0"
        ),
        "operation": (
            "build_promotion_scaffold"
        ),
        "generated_at": utc_now(),
        "packet": {
            "path": relative_path(
                packet_path
            ),
            "sha256": sha256_path(
                packet_path
            ),
            "digest": packet.get(
                "digest"
            ),
        },
        "subject": {
            "id": subject[
                "id"
            ],
            "name": name,
            "python_name": (
                python_name
            ),
            "kind": kind,
            "parent": parent_id(
                packet
            ),
            "definition": layout[
                "definition"
            ],
            "reference_subject": (
                subject.get(
                    "reference_subject",
                    False,
                )
            ),
        },
        "authority": packet.get(
            "authority",
            {}
        ),
        "target_layout": layout,
        "backup": build_backup_plan(
            layout,
            subject_key,
        ),
        "actions": build_actions(
            packet
        ),
        "contracts": (
            build_contract_model_plan(
                kind,
                python_name,
            )
        ),
        "runtime": (
            build_runtime_plan(
                kind,
                python_name,
            )
        ),
        "tests": (
            build_test_plan(
                python_name
            )
        ),
        "controller": (
            build_controller_plan(
                python_name
            )
        ),
        "definition_patch": (
            build_definition_patch_plan(
                packet,
                python_name,
            )
        ),
        "attachment": (
            build_attachment_plan(
                packet
            )
        ),
        "verification": {
            "stages": [
                "compile_contracts",
                "compile_runtime",
                "compile_tests",
                "run_unit_tests",
                "run_property_tests",
                "run_security_tests",
                "run_integration_tests",
                "run_recovery_tests",
                "run_example",
                "validate_result",
                "verify_determinism",
                "verify_definition",
                "verify_parent_attachment",
                "run_identity_audit",
                "run_identity_validation",
                "build_attestation",
                "rebuild_promotion_queue",
            ],
            "stop_on_failure": True,
            "attestation_required": (
                True
            ),
        },
        "constraints": packet.get(
            "promotion_constraints",
            []
        ),
        "source_tasks": subject.get(
            "tasks",
            []
        ),
    }

    scaffold[
        "digest"
    ] = digest(
        deterministic_projection(
            scaffold
        )
    )

    return scaffold


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Build a deterministic implementation scaffold "
            "for the current identity promotion packet."
        )
    )

    parser.add_argument(
        "--packet",
        type=Path,
    )

    parser.add_argument(
        "--output-root",
        type=Path,
        default=(
            SCAFFOLD_REPORT_ROOT
        ),
    )

    parser.add_argument(
        "--strict",
        action="store_true",
    )

    arguments = parser.parse_args()

    try:
        packet_path = resolve_packet_path(
            arguments.packet
        )

        scaffold = build_scaffold(
            packet_path
        )

    except Exception as exc:
        print(
            json.dumps(
                {
                    "operation": (
                        "build_promotion_scaffold"
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

    subject_key = safe_subject_key(
        scaffold[
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
            "promotion-scaffold.json"
        )
    )

    markdown_path = (
        output_root
        / (
            f"{run_id}__"
            "promotion-scaffold.md"
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
        scaffold,
    )

    write_json(
        latest_json,
        scaffold,
    )

    rendered = markdown(
        scaffold
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
            scaffold[
                "generated_at"
            ]
        ),
        "subject": (
            scaffold[
                "subject"
            ][
                "id"
            ]
        ),
        "scaffold_digest": (
            scaffold[
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
            f"{run_id}__"
            "manifest.json"
        )
    )

    write_json(
        manifest_path,
        manifest,
    )

    passed = all(
        (
            scaffold[
                "packet"
            ][
                "sha256"
            ],
            scaffold[
                "subject"
            ][
                "id"
            ],
            scaffold[
                "target_layout"
            ],
            scaffold[
                "actions"
            ],
        )
    )

    print(
        json.dumps(
            {
                "operation": (
                    "build_promotion_scaffold"
                ),
                "passed": passed,
                "subject": (
                    scaffold[
                        "subject"
                    ]
                ),
                "digest": (
                    scaffold[
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
        and not passed
    ):
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
