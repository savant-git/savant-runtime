#!/usr/bin/env python3
"""
Compile the latest Masterplan Opus packet into a deterministic living-work queue.

The authoritative task graph remains the source of task identity, priority,
dependencies, acceptance conditions, and authority boundaries.

This compiler:

- reads the latest verified Masterplan Opus packet
- creates exactly one queue record for each Opus assignment
- preserves assignment identity, lineage, provenance, and source digests
- creates a deterministic dependency-aware execution order
- records explicit lifecycle state
- creates provider-neutral Opus request envelopes
- supports safe replay and verification
- performs no provider calls
- performs no authority mutation
- performs no task transition
- performs no evidence admission
- performs no accepted decision
- performs no implementation mutation

Provider execution remains owned by Opus.
Masterplan remains the governing living-task engine.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import tempfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Final


ROOT: Final[Path] = Path(
    "/root/savant-runtime"
)

OPUS_PACKET_ROOT: Final[Path] = (
    ROOT
    / "reports"
    / "niche"
    / "masterplan"
    / "opus-packets"
)

LATEST_OPUS_PACKET: Final[Path] = (
    OPUS_PACKET_ROOT
    / "latest.json"
)

QUEUE_ROOT: Final[Path] = (
    ROOT
    / "runtime"
    / "masterplan"
    / "opus"
    / "queue"
)

REPORT_ROOT: Final[Path] = (
    ROOT
    / "reports"
    / "niche"
    / "masterplan"
    / "opus-queue"
)

QUEUE_SCHEMA: Final[str] = (
    "savant://niche/masterplan/"
    "opus-living-queue/1.0.0"
)

REQUEST_SCHEMA: Final[str] = (
    "savant://exile/opus/"
    "masterplan-analysis-request/1.0.0"
)

MANIFEST_SCHEMA: Final[str] = (
    "savant://niche/masterplan/"
    "opus-living-queue-manifest/1.0.0"
)

COMPILER_ID: Final[str] = (
    "prodigal.niche.masterplan."
    "compile_masterplan_opus_queue"
)

COMPILER_VERSION: Final[str] = (
    "1.0.0"
)

QUEUE_STATES: Final[
    tuple[str, ...]
] = (
    "queued",
    "leased",
    "running",
    "succeeded",
    "failed",
    "deferred",
    "cancelled",
    "superseded",
    "admitted",
)

EXECUTION_POLICIES: Final[
    tuple[str, ...]
] = (
    "dependency_ordered",
    "parallel_when_independent",
    "fail_isolated",
    "retry_bounded",
    "provider_neutral",
    "authority_preserving",
    "provenance_required",
    "evidence_candidate_only",
    "replayable",
)

RESPONSE_SECTIONS: Final[
    tuple[str, ...]
] = (
    "confirmed_facts",
    "source_derived_findings",
    "inferences",
    "unknowns",
    "conflicts",
    "recommended_actions",
    "validation",
    "risks",
    "evidence",
)

ASSIGNMENT_ORDER: Final[
    tuple[str, ...]
] = (
    "authority",
    "dependencies",
    "implementation",
    "validation",
    "risk",
    "recovery",
    "automation",
    "libraries",
    "integration",
)

ASSIGNMENT_DEPENDENCIES: Final[
    dict[str, tuple[str, ...]]
] = {
    "authority": (),
    "dependencies": (
        "authority",
    ),
    "implementation": (
        "authority",
        "dependencies",
    ),
    "validation": (
        "authority",
        "dependencies",
        "implementation",
    ),
    "risk": (
        "authority",
        "dependencies",
        "implementation",
    ),
    "recovery": (
        "authority",
        "dependencies",
        "implementation",
        "risk",
    ),
    "automation": (
        "authority",
        "dependencies",
        "implementation",
        "risk",
    ),
    "libraries": (
        "authority",
        "dependencies",
        "implementation",
        "risk",
    ),
    "integration": (
        "authority",
        "dependencies",
        "implementation",
        "validation",
        "risk",
        "recovery",
        "automation",
        "libraries",
    ),
}

PROVIDER_CAPABILITIES: Final[
    tuple[str, ...]
] = (
    "reasoning",
    "source_analysis",
    "code_analysis",
    "dependency_analysis",
    "risk_analysis",
    "validation_design",
    "recovery_design",
    "library_analysis",
    "synthesis",
)

FORBIDDEN_EFFECTS: Final[
    tuple[str, ...]
] = (
    "authority_mutation",
    "priority_override",
    "task_completion",
    "decision_acceptance",
    "evidence_admission",
    "implementation_mutation",
    "history_deletion",
    "conflict_reconciliation",
    "requirement_waiver",
)


class QueueError(RuntimeError):
    """Raised when the living Opus queue cannot be compiled safely."""


def utc_timestamp() -> str:
    return datetime.now(
        timezone.utc
    ).strftime(
        "%Y%m%dT%H%M%SZ"
    )


def canonical_json_bytes(
    value: object,
) -> bytes:
    return (
        json.dumps(
            value,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        )
        + "\n"
    ).encode(
        "utf-8"
    )


def pretty_json_bytes(
    value: object,
) -> bytes:
    return (
        json.dumps(
            value,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n"
    ).encode(
        "utf-8"
    )


def sha256_bytes(
    value: bytes,
) -> str:
    return hashlib.sha256(
        value
    ).hexdigest()


def sha256_value(
    value: object,
) -> str:
    return sha256_bytes(
        canonical_json_bytes(
            value
        )
    )


def atomic_write(
    path: Path,
    value: bytes,
    mode: int = 0o644,
) -> None:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.",
        suffix=".tmp",
        dir=str(
            path.parent
        ),
    )

    temporary = Path(
        temporary_name
    )

    try:
        with os.fdopen(
            descriptor,
            "wb",
        ) as handle:
            handle.write(
                value
            )

            handle.flush()

            os.fsync(
                handle.fileno()
            )

        temporary.chmod(
            mode
        )

        temporary.replace(
            path
        )

        directory_descriptor = os.open(
            path.parent,
            os.O_DIRECTORY,
        )

        try:
            os.fsync(
                directory_descriptor
            )
        finally:
            os.close(
                directory_descriptor
            )

    except BaseException:
        temporary.unlink(
            missing_ok=True
        )

        raise


def load_json(
    path: Path,
) -> dict[str, Any]:
    if not path.is_file():
        raise QueueError(
            f"required JSON file missing: {path}"
        )

    try:
        value = json.loads(
            path.read_text(
                encoding="utf-8"
            )
        )
    except (
        OSError,
        UnicodeDecodeError,
        json.JSONDecodeError,
    ) as error:
        raise QueueError(
            f"cannot load JSON {path}: {error}"
        ) from error

    if not isinstance(
        value,
        dict,
    ):
        raise QueueError(
            f"JSON root must be an object: {path}"
        )

    return value


def confined_path(
    value: object,
    field: str,
) -> Path:
    if not isinstance(
        value,
        str,
    ):
        raise QueueError(
            f"{field} must be a string path"
        )

    path = Path(
        value
    )

    if not path.is_absolute():
        raise QueueError(
            f"{field} must be absolute: {path}"
        )

    resolved = path.resolve(
        strict=False
    )

    try:
        resolved.relative_to(
            ROOT.resolve()
        )
    except ValueError as error:
        raise QueueError(
            f"{field} escapes runtime root: {resolved}"
        ) from error

    return resolved


def resolve_packet_path() -> Path:
    latest = load_json(
        LATEST_OPUS_PACKET
    )

    raw_packet_path = latest.get(
        "packet"
    )

    packet_path = confined_path(
        raw_packet_path,
        "latest Opus packet",
    )

    if not packet_path.is_file():
        raise QueueError(
            f"Opus packet is missing: {packet_path}"
        )

    return packet_path


def assignment_index(
    packet: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    assignments = packet.get(
        "assignments"
    )

    if not isinstance(
        assignments,
        list,
    ):
        raise QueueError(
            "Opus packet assignments must be an array"
        )

    if len(
        assignments
    ) != 9:
        raise QueueError(
            "Opus packet must contain exactly nine assignments"
        )

    index: dict[
        str,
        dict[str, Any],
    ] = {}

    for assignment in assignments:
        if not isinstance(
            assignment,
            dict,
        ):
            raise QueueError(
                "Opus assignment must be an object"
            )

        key = assignment.get(
            "key"
        )

        if not isinstance(
            key,
            str,
        ) or not key:
            raise QueueError(
                "Opus assignment lacks stable key"
            )

        if key in index:
            raise QueueError(
                f"duplicate Opus assignment key: {key}"
            )

        index[
            key
        ] = assignment

    if tuple(
        index
    ) != ASSIGNMENT_ORDER:
        raise QueueError(
            "Opus assignment order differs from authority"
        )

    return index


def validate_assignment_graph() -> None:
    if tuple(
        ASSIGNMENT_DEPENDENCIES
    ) != ASSIGNMENT_ORDER:
        raise QueueError(
            "assignment dependency map order differs "
            "from assignment authority"
        )

    known = set(
        ASSIGNMENT_ORDER
    )

    for key, dependencies in (
        ASSIGNMENT_DEPENDENCIES.items()
    ):
        if key in dependencies:
            raise QueueError(
                f"assignment depends on itself: {key}"
            )

        unknown = set(
            dependencies
        ) - known

        if unknown:
            raise QueueError(
                f"assignment {key} has unknown dependencies: "
                f"{sorted(unknown)}"
            )

        key_index = ASSIGNMENT_ORDER.index(
            key
        )

        for dependency in dependencies:
            dependency_index = (
                ASSIGNMENT_ORDER.index(
                    dependency
                )
            )

            if dependency_index >= key_index:
                raise QueueError(
                    "assignment dependency violates "
                    f"execution order: {dependency} -> {key}"
                )


def task_identity(
    packet: dict[str, Any],
) -> tuple[str, str]:
    selected_task = packet.get(
        "selected_task"
    )

    if not isinstance(
        selected_task,
        dict,
    ):
        raise QueueError(
            "Opus packet lacks selected task"
        )

    task_id = selected_task.get(
        "id"
    )

    title = selected_task.get(
        "title"
    )

    if not isinstance(
        task_id,
        str,
    ) or not task_id:
        raise QueueError(
            "selected task lacks stable id"
        )

    if not isinstance(
        title,
        str,
    ):
        title = ""

    return task_id, title


def prompt_for_assignment(
    *,
    packet: dict[str, Any],
    assignment: dict[str, Any],
    dependency_keys: tuple[str, ...],
) -> str:
    selected_task = packet[
        "selected_task"
    ]

    authority = packet.get(
        "authority",
        {},
    )

    opus_policy = packet.get(
        "opus_policy",
        {},
    )

    request_payload = {
        "directive": (
            "Perform the assigned analysis for the selected "
            "Savant Masterplan task. Produce explicit auditable "
            "reasoning artifacts, not private chain-of-thought."
        ),
        "selected_task": selected_task,
        "assignment": {
            "id": assignment.get(
                "id"
            ),
            "key": assignment.get(
                "key"
            ),
            "title": assignment.get(
                "title"
            ),
            "purpose": assignment.get(
                "purpose"
            ),
            "requirements": assignment.get(
                "requirements",
                {},
            ),
        },
        "assignment_dependencies": list(
            dependency_keys
        ),
        "authority": authority,
        "opus_policy": opus_policy,
        "response_contract": {
            "format": "json_object",
            "required_sections": list(
                RESPONSE_SECTIONS
            ),
            "authority_effect": "none",
            "output_class": (
                "advisory-evidence-candidate"
            ),
        },
    }

    return (
        "SAVANT MASTERPLAN LIVING TASK ANALYSIS\n"
        + json.dumps(
            request_payload,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )


def queue_record_identity(
    *,
    packet_id: str,
    task_id: str,
    assignment_key: str,
    request_digest: str,
) -> str:
    return (
        "masterplan-opus-work:"
        + sha256_value(
            {
                "packet_id": packet_id,
                "task_id": task_id,
                "assignment_key": (
                    assignment_key
                ),
                "request_digest": (
                    request_digest
                ),
            }
        )[:24]
    )


def build_request(
    *,
    packet: dict[str, Any],
    assignment: dict[str, Any],
    dependency_keys: tuple[str, ...],
) -> dict[str, Any]:
    task_id, task_title = task_identity(
        packet
    )

    packet_id = packet.get(
        "packet_id"
    )

    if not isinstance(
        packet_id,
        str,
    ) or not packet_id:
        raise QueueError(
            "Opus packet lacks stable packet id"
        )

    assignment_key = assignment.get(
        "key"
    )

    assignment_id = assignment.get(
        "id"
    )

    if not isinstance(
        assignment_key,
        str,
    ):
        raise QueueError(
            "assignment lacks key"
        )

    if not isinstance(
        assignment_id,
        str,
    ):
        raise QueueError(
            "assignment lacks id"
        )

    prompt = prompt_for_assignment(
        packet=packet,
        assignment=assignment,
        dependency_keys=dependency_keys,
    )

    request_body: dict[str, Any] = {
        "$schema": REQUEST_SCHEMA,
        "request_id": None,
        "kind": (
            "masterplan_task_analysis"
        ),
        "owner": "exile.opus",
        "caller": (
            "prodigal.niche.masterplan"
        ),
        "task": {
            "id": task_id,
            "title": task_title,
        },
        "assignment": {
            "id": assignment_id,
            "key": assignment_key,
            "ordinal": assignment.get(
                "ordinal"
            ),
            "title": assignment.get(
                "title"
            ),
            "purpose": assignment.get(
                "purpose"
            ),
        },
        "dependencies": {
            "assignment_keys": list(
                dependency_keys
            ),
            "task_ids": assignment.get(
                "dependency_ids",
                [],
            ),
        },
        "routing": {
            "mode": "parallel_capability_fanout",
            "minimum_provider_count": 1,
            "preferred_provider_count": 3,
            "maximum_provider_count": 9,
            "required_capabilities": list(
                PROVIDER_CAPABILITIES
            ),
            "allow_provider_fallback": True,
            "allow_partial_success": True,
            "require_cross_provider_comparison": True,
            "require_final_synthesis": True,
        },
        "policy": {
            "provider_output_authority": False,
            "evidence_admission_required": True,
            "authority_effect": "none",
            "forbidden_effects": list(
                FORBIDDEN_EFFECTS
            ),
            "retry_limit": 3,
            "timeout_seconds": 300,
            "cache_policy": (
                "content_addressed"
            ),
            "deduplicate_equal_outputs": True,
            "preserve_rejected_branches": True,
            "preserve_provider_failures": True,
        },
        "input": {
            "format": "text",
            "prompt": prompt,
            "prompt_sha256": sha256_bytes(
                prompt.encode(
                    "utf-8"
                )
            ),
        },
        "output": {
            "format": "json_object",
            "required_sections": list(
                RESPONSE_SECTIONS
            ),
            "class": (
                "advisory-evidence-candidate"
            ),
        },
        "lineage": {
            "packet_id": packet_id,
            "assignment_id": assignment_id,
            "task_id": task_id,
            "source_packet_digest": (
                packet.get(
                    "packet_digest"
                )
            ),
        },
    }

    request_digest = sha256_value(
        {
            key: value
            for key, value
            in request_body.items()
            if key != "request_id"
        }
    )

    request_id = (
        "opus-request:"
        + request_digest[:24]
    )

    request_body[
        "request_id"
    ] = request_id

    request_body[
        "request_digest"
    ] = sha256_value(
        {
            key: value
            for key, value
            in request_body.items()
            if key != "request_digest"
        }
    )

    return request_body


def build_queue_record(
    *,
    packet: dict[str, Any],
    assignment: dict[str, Any],
    request: dict[str, Any],
    request_path: Path,
    dependency_record_ids: tuple[
        str,
        ...,
    ],
) -> dict[str, Any]:
    task_id, task_title = task_identity(
        packet
    )

    packet_id = str(
        packet[
            "packet_id"
        ]
    )

    assignment_key = str(
        assignment[
            "key"
        ]
    )

    request_digest = str(
        request[
            "request_digest"
        ]
    )

    record_id = queue_record_identity(
        packet_id=packet_id,
        task_id=task_id,
        assignment_key=assignment_key,
        request_digest=request_digest,
    )

    record: dict[str, Any] = {
        "id": record_id,
        "kind": "opus_work_record",
        "state": "queued",
        "task": {
            "id": task_id,
            "title": task_title,
        },
        "assignment": {
            "id": assignment.get(
                "id"
            ),
            "key": assignment_key,
            "ordinal": assignment.get(
                "ordinal"
            ),
            "title": assignment.get(
                "title"
            ),
        },
        "request": {
            "id": request.get(
                "request_id"
            ),
            "path": str(
                request_path
            ),
            "sha256": sha256_bytes(
                request_path.read_bytes()
            ),
            "semantic_digest": (
                request_digest
            ),
        },
        "dependencies": {
            "record_ids": list(
                dependency_record_ids
            ),
            "assignment_keys": list(
                ASSIGNMENT_DEPENDENCIES[
                    assignment_key
                ]
            ),
        },
        "execution": {
            "attempt_count": 0,
            "retry_limit": 3,
            "lease_id": None,
            "lease_owner": None,
            "leased_at": None,
            "lease_expires_at": None,
            "started_at": None,
            "finished_at": None,
            "provider_ids": [],
            "result_path": None,
            "error_path": None,
        },
        "authority": {
            "state": "projection",
            "effect": "none",
            "may_modify_authority": False,
            "may_modify_priority": False,
            "may_complete_task": False,
            "may_accept_decision": False,
            "may_admit_evidence": False,
        },
        "lineage": {
            "packet_id": packet_id,
            "task_id": task_id,
            "assignment_id": assignment.get(
                "id"
            ),
            "request_id": request.get(
                "request_id"
            ),
        },
        "provenance": {
            "generated_by": (
                f"{COMPILER_ID}@"
                f"{COMPILER_VERSION}"
            ),
            "source_packet_digest": (
                packet.get(
                    "packet_digest"
                )
            ),
            "transformations": [
                "validate_packet",
                "resolve_assignment_dependencies",
                "compile_provider_neutral_request",
                "compile_queue_record",
            ],
        },
    }

    record[
        "digest"
    ] = sha256_value(
        {
            key: value
            for key, value
            in record.items()
            if key != "digest"
        }
    )

    return record


def validate_request(
    request: dict[str, Any],
) -> None:
    if request.get(
        "$schema"
    ) != REQUEST_SCHEMA:
        raise QueueError(
            "request schema mismatch"
        )

    request_id = request.get(
        "request_id"
    )

    if not isinstance(
        request_id,
        str,
    ) or not request_id:
        raise QueueError(
            "request lacks stable id"
        )

    routing = request.get(
        "routing"
    )

    if not isinstance(
        routing,
        dict,
    ):
        raise QueueError(
            "request lacks routing policy"
        )

    minimum = routing.get(
        "minimum_provider_count"
    )

    preferred = routing.get(
        "preferred_provider_count"
    )

    maximum = routing.get(
        "maximum_provider_count"
    )

    if not all(
        isinstance(
            value,
            int,
        )
        for value in (
            minimum,
            preferred,
            maximum,
        )
    ):
        raise QueueError(
            "provider counts must be integers"
        )

    if not (
        1
        <= minimum
        <= preferred
        <= maximum
        <= 9
    ):
        raise QueueError(
            "provider count policy is invalid"
        )

    policy = request.get(
        "policy"
    )

    if not isinstance(
        policy,
        dict,
    ):
        raise QueueError(
            "request lacks execution policy"
        )

    if policy.get(
        "provider_output_authority"
    ) is not False:
        raise QueueError(
            "provider output cannot be authority"
        )

    if policy.get(
        "authority_effect"
    ) != "none":
        raise QueueError(
            "request may not alter authority"
        )

    recorded_digest = request.get(
        "request_digest"
    )

    if not isinstance(
        recorded_digest,
        str,
    ):
        raise QueueError(
            "request lacks semantic digest"
        )

    calculated_digest = sha256_value(
        {
            key: value
            for key, value
            in request.items()
            if key != "request_digest"
        }
    )

    if recorded_digest != calculated_digest:
        raise QueueError(
            "request semantic digest mismatch"
        )


def validate_record(
    record: dict[str, Any],
) -> None:
    state = record.get(
        "state"
    )

    if state not in QUEUE_STATES:
        raise QueueError(
            f"invalid queue state: {state}"
        )

    authority = record.get(
        "authority"
    )

    if not isinstance(
        authority,
        dict,
    ):
        raise QueueError(
            "queue record lacks authority boundary"
        )

    if authority.get(
        "effect"
    ) != "none":
        raise QueueError(
            "queue record may not alter authority"
        )

    digest = record.get(
        "digest"
    )

    if not isinstance(
        digest,
        str,
    ):
        raise QueueError(
            "queue record lacks digest"
        )

    calculated = sha256_value(
        {
            key: value
            for key, value
            in record.items()
            if key != "digest"
        }
    )

    if calculated != digest:
        raise QueueError(
            "queue record digest mismatch"
        )


def compile_queue(
    packet: dict[str, Any],
    run_root: Path,
) -> tuple[
    dict[str, Any],
    tuple[Path, ...],
]:
    validate_assignment_graph()

    assignments = assignment_index(
        packet
    )

    task_id, task_title = task_identity(
        packet
    )

    request_root = (
        run_root
        / "requests"
    )

    record_root = (
        run_root
        / "records"
    )

    records: list[
        dict[str, Any]
    ] = []

    request_paths: list[
        Path
    ] = []

    record_paths: list[
        Path
    ] = []

    record_id_by_key: dict[
        str,
        str,
    ] = {}

    for assignment_key in ASSIGNMENT_ORDER:
        assignment = assignments[
            assignment_key
        ]

        dependency_keys = (
            ASSIGNMENT_DEPENDENCIES[
                assignment_key
            ]
        )

        request = build_request(
            packet=packet,
            assignment=assignment,
            dependency_keys=dependency_keys,
        )

        validate_request(
            request
        )

        ordinal = int(
            assignment[
                "ordinal"
            ]
        )

        request_path = (
            request_root
            / (
                f"{ordinal:02d}__"
                f"{assignment_key}.json"
            )
        )

        atomic_write(
            request_path,
            pretty_json_bytes(
                request
            ),
        )

        dependency_record_ids = tuple(
            record_id_by_key[
                dependency_key
            ]
            for dependency_key
            in dependency_keys
        )

        record = build_queue_record(
            packet=packet,
            assignment=assignment,
            request=request,
            request_path=request_path,
            dependency_record_ids=(
                dependency_record_ids
            ),
        )

        validate_record(
            record
        )

        record_path = (
            record_root
            / (
                f"{ordinal:02d}__"
                f"{assignment_key}.json"
            )
        )

        atomic_write(
            record_path,
            pretty_json_bytes(
                record
            ),
        )

        record_id_by_key[
            assignment_key
        ] = str(
            record[
                "id"
            ]
        )

        request_paths.append(
            request_path
        )

        record_paths.append(
            record_path
        )

        records.append(
            record
        )

    queue_id = (
        "masterplan-opus-queue:"
        + sha256_value(
            {
                "packet_id": packet[
                    "packet_id"
                ],
                "task_id": task_id,
                "record_digests": [
                    record[
                        "digest"
                    ]
                    for record in records
                ],
            }
        )[:24]
    )

    queue: dict[str, Any] = {
        "$schema": QUEUE_SCHEMA,
        "queue_id": queue_id,
        "compiler": {
            "id": COMPILER_ID,
            "version": (
                COMPILER_VERSION
            ),
        },
        "task": {
            "id": task_id,
            "title": task_title,
        },
        "packet": {
            "id": packet[
                "packet_id"
            ],
            "digest": packet.get(
                "packet_digest"
            ),
        },
        "state": "queued",
        "record_count": len(
            records
        ),
        "execution_order": list(
            ASSIGNMENT_ORDER
        ),
        "execution_policies": list(
            EXECUTION_POLICIES
        ),
        "state_counts": {
            state: (
                len(records)
                if state == "queued"
                else 0
            )
            for state in QUEUE_STATES
        },
        "records": records,
        "authority": {
            "state": "projection",
            "effect": "none",
            "source": (
                "authoritative Masterplan task graph"
            ),
            "provider_output_authority": False,
            "evidence_admission_required": True,
        },
        "provenance": {
            "source_packet_path": str(
                resolve_packet_path()
            ),
            "source_packet_digest": (
                packet.get(
                    "packet_digest"
                )
            ),
            "generated_by": (
                f"{COMPILER_ID}@"
                f"{COMPILER_VERSION}"
            ),
            "transformations": [
                "load_verified_opus_packet",
                "validate_assignment_graph",
                "compile_nine_requests",
                "compile_nine_queue_records",
                "derive_dependency_order",
                "project_living_queue",
            ],
        },
    }

    queue[
        "queue_digest"
    ] = sha256_value(
        {
            key: value
            for key, value
            in queue.items()
            if key != "queue_digest"
        }
    )

    return (
        queue,
        tuple(
            request_paths
            + record_paths
        ),
    )


def verify_queue(
    queue: dict[str, Any],
) -> None:
    if queue.get(
        "$schema"
    ) != QUEUE_SCHEMA:
        raise QueueError(
            "queue schema mismatch"
        )

    if queue.get(
        "record_count"
    ) != 9:
        raise QueueError(
            "queue must contain exactly nine records"
        )

    execution_order = queue.get(
        "execution_order"
    )

    if tuple(
        execution_order
        if isinstance(
            execution_order,
            list,
        )
        else ()
    ) != ASSIGNMENT_ORDER:
        raise QueueError(
            "queue execution order differs from authority"
        )

    policies = queue.get(
        "execution_policies"
    )

    if tuple(
        policies
        if isinstance(
            policies,
            list,
        )
        else ()
    ) != EXECUTION_POLICIES:
        raise QueueError(
            "queue execution policies differ from authority"
        )

    records = queue.get(
        "records"
    )

    if not isinstance(
        records,
        list,
    ):
        raise QueueError(
            "queue records must be an array"
        )

    keys: list[str] = []

    identifiers: list[str] = []

    for record in records:
        if not isinstance(
            record,
            dict,
        ):
            raise QueueError(
                "queue record must be an object"
            )

        validate_record(
            record
        )

        identifiers.append(
            str(
                record[
                    "id"
                ]
            )
        )

        assignment = record.get(
            "assignment"
        )

        if not isinstance(
            assignment,
            dict,
        ):
            raise QueueError(
                "queue record lacks assignment"
            )

        keys.append(
            str(
                assignment[
                    "key"
                ]
            )
        )

    if tuple(
        keys
    ) != ASSIGNMENT_ORDER:
        raise QueueError(
            "queue record order differs from authority"
        )

    if len(
        identifiers
    ) != len(
        set(
            identifiers
        )
    ):
        raise QueueError(
            "queue record identifiers are duplicated"
        )

    recorded_digest = queue.get(
        "queue_digest"
    )

    if not isinstance(
        recorded_digest,
        str,
    ):
        raise QueueError(
            "queue lacks digest"
        )

    calculated_digest = sha256_value(
        {
            key: value
            for key, value
            in queue.items()
            if key != "queue_digest"
        }
    )

    if recorded_digest != calculated_digest:
        raise QueueError(
            "queue digest mismatch"
        )


def write_queue(
    *,
    packet_path: Path,
    packet: dict[str, Any],
) -> dict[str, Any]:
    timestamp = utc_timestamp()

    cycle_root = (
        QUEUE_ROOT
        / timestamp
    )

    report_run_root = (
        REPORT_ROOT
        / timestamp
    )

    queue_path = (
        cycle_root
        / "queue.json"
    )

    queue, generated_paths = (
        compile_queue(
            packet,
            cycle_root,
        )
    )

    verify_queue(
        queue
    )

    atomic_write(
        queue_path,
        pretty_json_bytes(
            queue
        ),
    )

    manifest_entries = []

    for path in (
        queue_path,
        *generated_paths,
    ):
        manifest_entries.append(
            {
                "path": str(
                    path
                ),
                "sha256": sha256_bytes(
                    path.read_bytes()
                ),
                "size": path.stat().st_size,
            }
        )

    manifest = {
        "$schema": MANIFEST_SCHEMA,
        "queue_id": queue[
            "queue_id"
        ],
        "entries": manifest_entries,
    }

    manifest_path = (
        cycle_root
        / "manifest.json"
    )

    atomic_write(
        manifest_path,
        pretty_json_bytes(
            manifest
        ),
    )

    report = {
        "$schema": (
            "savant://niche/masterplan/"
            "opus-living-queue-report/1.0.0"
        ),
        "operation": (
            "compile_masterplan_opus_queue"
        ),
        "passed": True,
        "queue_id": queue[
            "queue_id"
        ],
        "queue_digest": queue[
            "queue_digest"
        ],
        "task_id": queue[
            "task"
        ][
            "id"
        ],
        "packet_id": packet[
            "packet_id"
        ],
        "packet_path": str(
            packet_path
        ),
        "queue_path": str(
            queue_path
        ),
        "manifest_path": str(
            manifest_path
        ),
        "record_count": queue[
            "record_count"
        ],
        "state_counts": queue[
            "state_counts"
        ],
        "authority_effect": "none",
        "provider_calls_performed": False,
        "task_transition_performed": False,
        "evidence_admitted": False,
        "implementation_mutation_performed": False,
        "generated_at": timestamp,
    }

    report_path = (
        report_run_root
        / "report.json"
    )

    atomic_write(
        report_path,
        pretty_json_bytes(
            report
        ),
    )

    report_manifest_path = (
        report_run_root
        / "manifest.json"
    )

    report_manifest = {
        "$schema": (
            "savant://niche/masterplan/"
            "opus-living-queue-report-manifest/1.0.0"
        ),
        "entries": [
            {
                "path": str(
                    report_path
                ),
                "sha256": sha256_bytes(
                    report_path.read_bytes()
                ),
                "size": (
                    report_path.stat().st_size
                ),
            }
        ],
    }

    atomic_write(
        report_manifest_path,
        pretty_json_bytes(
            report_manifest
        ),
    )

    latest = {
        "queue_id": queue[
            "queue_id"
        ],
        "queue_digest": queue[
            "queue_digest"
        ],
        "task_id": queue[
            "task"
        ][
            "id"
        ],
        "packet_id": packet[
            "packet_id"
        ],
        "queue": str(
            queue_path
        ),
        "queue_manifest": str(
            manifest_path
        ),
        "report": str(
            report_path
        ),
        "report_manifest": str(
            report_manifest_path
        ),
        "record_count": 9,
        "state": "queued",
        "authority_effect": "none",
        "provider_calls_performed": False,
        "task_transition_performed": False,
        "evidence_admitted": False,
        "implementation_mutation_performed": False,
        "generated_at": timestamp,
    }

    latest_path = (
        REPORT_ROOT
        / "latest.json"
    )

    atomic_write(
        latest_path,
        pretty_json_bytes(
            latest
        ),
    )

    return latest


def verify_manifest(
    path: Path,
) -> int:
    manifest = load_json(
        path
    )

    entries = manifest.get(
        "entries"
    )

    if not isinstance(
        entries,
        list,
    ):
        raise QueueError(
            f"manifest entries must be an array: {path}"
        )

    for entry in entries:
        if not isinstance(
            entry,
            dict,
        ):
            raise QueueError(
                f"manifest entry must be an object: {path}"
            )

        entry_path = confined_path(
            entry.get(
                "path"
            ),
            "manifest entry path",
        )

        expected_digest = entry.get(
            "sha256"
        )

        expected_size = entry.get(
            "size"
        )

        if not entry_path.is_file():
            raise QueueError(
                f"manifest file missing: {entry_path}"
            )

        content = entry_path.read_bytes()

        if expected_digest != sha256_bytes(
            content
        ):
            raise QueueError(
                f"manifest digest mismatch: {entry_path}"
            )

        if expected_size != len(
            content
        ):
            raise QueueError(
                f"manifest size mismatch: {entry_path}"
            )

    return len(
        entries
    )


def run_compile() -> dict[str, Any]:
    packet_path = resolve_packet_path()

    packet = load_json(
        packet_path
    )

    latest = write_queue(
        packet_path=packet_path,
        packet=packet,
    )

    return {
        "operation": (
            "compile_masterplan_opus_queue"
        ),
        "passed": True,
        "queue_id": latest[
            "queue_id"
        ],
        "task_id": latest[
            "task_id"
        ],
        "packet_id": latest[
            "packet_id"
        ],
        "record_count": latest[
            "record_count"
        ],
        "state": latest[
            "state"
        ],
        "authority_effect": "none",
        "provider_calls_performed": False,
        "task_transition_performed": False,
        "evidence_admitted": False,
        "implementation_mutation_performed": False,
        "latest": str(
            REPORT_ROOT
            / "latest.json"
        ),
    }


def run_verify() -> dict[str, Any]:
    latest_path = (
        REPORT_ROOT
        / "latest.json"
    )

    latest = load_json(
        latest_path
    )

    queue_path = confined_path(
        latest.get(
            "queue"
        ),
        "queue path",
    )

    queue_manifest_path = confined_path(
        latest.get(
            "queue_manifest"
        ),
        "queue manifest path",
    )

    report_manifest_path = confined_path(
        latest.get(
            "report_manifest"
        ),
        "report manifest path",
    )

    queue = load_json(
        queue_path
    )

    verify_queue(
        queue
    )

    queue_manifest_count = verify_manifest(
        queue_manifest_path
    )

    report_manifest_count = verify_manifest(
        report_manifest_path
    )

    records = queue[
        "records"
    ]

    state_counts = Counter(
        record[
            "state"
        ]
        for record in records
    )

    if state_counts[
        "queued"
    ] != 9:
        raise QueueError(
            "new queue must contain exactly nine queued records"
        )

    for record in records:
        request = record.get(
            "request"
        )

        if not isinstance(
            request,
            dict,
        ):
            raise QueueError(
                "queue record lacks request"
            )

        request_path = confined_path(
            request.get(
                "path"
            ),
            "request path",
        )

        request_document = load_json(
            request_path
        )

        validate_request(
            request_document
        )

    return {
        "operation": (
            "verify_masterplan_opus_queue"
        ),
        "passed": True,
        "queue_id": queue[
            "queue_id"
        ],
        "task_id": queue[
            "task"
        ][
            "id"
        ],
        "record_count": queue[
            "record_count"
        ],
        "queued_count": state_counts[
            "queued"
        ],
        "queue_manifest_entry_count": (
            queue_manifest_count
        ),
        "report_manifest_entry_count": (
            report_manifest_count
        ),
        "authority_effect": "none",
        "provider_calls_performed": False,
        "task_transition_performed": False,
        "evidence_admitted": False,
        "implementation_mutation_performed": False,
    }


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Compile or verify the Masterplan "
            "living Opus work queue."
        )
    )

    parser.add_argument(
        "operation",
        choices=(
            "compile",
            "verify",
        ),
    )

    return parser.parse_args()


def main() -> int:
    arguments = parse_arguments()

    try:
        if arguments.operation == "compile":
            result = run_compile()
        else:
            result = run_verify()

        print(
            json.dumps(
                result,
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )
        )

        return 0

    except QueueError as error:
        print(
            json.dumps(
                {
                    "operation": (
                        arguments.operation
                    ),
                    "passed": False,
                    "authority_effect": "none",
                    "provider_calls_performed": False,
                    "task_transition_performed": False,
                    "evidence_admitted": False,
                    "implementation_mutation_performed": False,
                    "error": str(
                        error
                    ),
                },
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )
        )

        return 1


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
