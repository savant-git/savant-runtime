#!/usr/bin/env python3
"""
Build a deterministic, authority-bounded Opus work packet from Masterplan.

This tool extends the existing authoritative Masterplan implementation.

It does not:

- create or modify authority
- modify the authoritative task graph
- change task priority
- complete tasks
- admit evidence
- accept decisions
- call external AI providers directly
- bypass Opus provider governance

It projects the currently selected Masterplan task into nine distinct analytical
assignments suitable for orchestration by the Opus exile.

Opus may use multiple providers to perform the assignments. Provider output
remains advisory evidence until admitted through Masterplan's existing evidence,
decision, transition, verification, and attestation mechanisms.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Final


ROOT: Final[Path] = Path(
    "/root/savant-runtime"
)

MASTERPLAN_GRAPH: Final[Path] = (
    ROOT
    / "authority"
    / "task-graph"
    / "masterplan.json"
)

AGENT_CONTEXT: Final[Path] = (
    ROOT
    / "reports"
    / "niche"
    / "masterplan"
    / "agent_context"
    / "latest.json"
)

REPORT_ROOT: Final[Path] = (
    ROOT
    / "reports"
    / "niche"
    / "masterplan"
    / "opus-packets"
)

PACKET_SCHEMA: Final[str] = (
    "savant://niche/masterplan/"
    "opus-work-packet/1.0.0"
)

GENERATOR_ID: Final[str] = (
    "prodigal.niche.masterplan."
    "build_masterplan_opus_packet"
)

GENERATOR_VERSION: Final[str] = (
    "1.0.0"
)

ANALYSIS_ASSIGNMENTS: Final[
    tuple[
        tuple[str, str, str],
        ...,
    ]
] = (
    (
        "authority",
        "Authority analysis",
        (
            "Identify every authority source, authority boundary, unresolved "
            "authority question, forbidden inference, and required accepted "
            "decision affecting the selected task."
        ),
    ),
    (
        "dependencies",
        "Dependency analysis",
        (
            "Identify direct and transitive dependencies, affected dependents, "
            "execution ordering, cycles, unreachable requirements, and missing "
            "dependency evidence."
        ),
    ),
    (
        "implementation",
        "Implementation analysis",
        (
            "Inspect the verified implementation baseline and propose the "
            "smallest compatible extension that satisfies the task without "
            "duplicating existing primitives."
        ),
    ),
    (
        "validation",
        "Validation analysis",
        (
            "Design syntax, schema, unit, property, integration, determinism, "
            "security, recovery, replay, and regression verification."
        ),
    ),
    (
        "risk",
        "Risk analysis",
        (
            "Identify regression, authority, compatibility, data-loss, "
            "dependency, nondeterminism, concurrency, security, and migration "
            "risks with evidence-backed mitigations."
        ),
    ),
    (
        "recovery",
        "Recovery analysis",
        (
            "Design complete reversible migration, rollback, replay, restoration, "
            "receipt, and post-recovery verification requirements."
        ),
    ),
    (
        "automation",
        "Automation analysis",
        (
            "Identify work that can be automated deterministically without "
            "manufacturing authority, accepting proposals, waiving evidence, "
            "or performing uncontrolled mutation."
        ),
    ),
    (
        "libraries",
        "Library analysis",
        (
            "Identify contemporary maintained libraries that materially improve "
            "correctness, determinism, validation, orchestration, observability, "
            "security, concurrency, or maintenance. Reject decorative dependencies."
        ),
    ),
    (
        "integration",
        "Integration analysis",
        (
            "Determine how the completed task composes with Masterplan, Opus, "
            "Palaver, Notary, projections, evidence admission, decisions, replay, "
            "attestations, and downstream Savant architecture."
        ),
    ),
)

REQUIRED_RESPONSE_SECTIONS: Final[
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

FORBIDDEN_AI_ACTIONS: Final[
    tuple[str, ...]
] = (
    "manufacture_authority",
    "accept_own_proposal",
    "accept_constitutional_amendment",
    "invent_project_owner_decision",
    "waive_required_evidence",
    "delete_authoritative_history",
    "rewrite_accepted_decision",
    "resolve_semantic_conflict_without_authority",
    "promote_inference_directly_to_authority",
)

ALLOWED_AI_ACTIONS: Final[
    tuple[str, ...]
] = (
    "analyze",
    "compare",
    "classify",
    "decompose",
    "detect_conflicts",
    "generate_proposal",
    "generate_impact_report",
    "generate_validation_plan",
    "generate_recovery_plan",
)


class PacketError(RuntimeError):
    """Raised when an Opus packet cannot be produced reliably."""


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


def load_json(
    path: Path,
) -> dict[str, Any]:
    if not path.is_file():
        raise PacketError(
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
        raise PacketError(
            f"cannot read JSON {path}: {error}"
        ) from error

    if not isinstance(
        value,
        dict,
    ):
        raise PacketError(
            f"JSON root must be an object: {path}"
        )

    return value


def atomic_write(
    path: Path,
    value: bytes,
    mode: int = 0o644,
) -> None:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    descriptor, temporary_name = (
        tempfile.mkstemp(
            prefix=f".{path.name}.",
            suffix=".tmp",
            dir=str(
                path.parent
            ),
        )
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


def extract_projection_payload(
    context: dict[str, Any],
) -> dict[str, Any]:
    projection = context.get(
        "projection"
    )

    if not isinstance(
        projection,
        dict,
    ):
        raise PacketError(
            "agent context lacks projection"
        )

    payload = projection.get(
        "payload"
    )

    if not isinstance(
        payload,
        dict,
    ):
        raise PacketError(
            "agent context projection lacks payload"
        )

    return payload


def extract_selected_task(
    payload: dict[str, Any],
) -> dict[str, Any]:
    selected_task = payload.get(
        "selected_task"
    )

    if not isinstance(
        selected_task,
        dict,
    ):
        raise PacketError(
            "agent context lacks selected task"
        )

    task_id = selected_task.get(
        "id"
    )

    if not isinstance(
        task_id,
        str,
    ) or not task_id:
        raise PacketError(
            "selected task lacks stable id"
        )

    return selected_task


def extract_selection(
    payload: dict[str, Any],
) -> dict[str, Any]:
    selection = payload.get(
        "selection"
    )

    if not isinstance(
        selection,
        dict,
    ):
        raise PacketError(
            "agent context lacks task selection"
        )

    return selection


def extract_audit(
    payload: dict[str, Any],
) -> dict[str, Any]:
    audit = payload.get(
        "audit"
    )

    if not isinstance(
        audit,
        dict,
    ):
        raise PacketError(
            "agent context lacks audit"
        )

    return audit


def task_dependency_ids(
    task: dict[str, Any],
) -> tuple[str, ...]:
    scope = task.get(
        "scope"
    )

    if not isinstance(
        scope,
        dict,
    ):
        return ()

    dependencies = scope.get(
        "depends_on"
    )

    if not isinstance(
        dependencies,
        list,
    ):
        return ()

    normalized = tuple(
        sorted(
            {
                str(
                    dependency
                )
                for dependency in dependencies
                if str(
                    dependency
                ).strip()
            }
        )
    )

    return normalized


def graph_task_index(
    graph: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    records = graph.get(
        "records"
    )

    if not isinstance(
        records,
        list,
    ):
        raise PacketError(
            "Masterplan graph records must be an array"
        )

    index: dict[
        str,
        dict[str, Any],
    ] = {}

    for record in records:
        if not isinstance(
            record,
            dict,
        ):
            continue

        if record.get(
            "kind"
        ) != "task":
            continue

        task_id = record.get(
            "id"
        )

        if not isinstance(
            task_id,
            str,
        ) or not task_id:
            continue

        if task_id in index:
            raise PacketError(
                f"duplicate task id: {task_id}"
            )

        index[
            task_id
        ] = record

    return index


def dependency_closure(
    selected_task: dict[str, Any],
    task_index: dict[
        str,
        dict[str, Any],
    ],
) -> tuple[dict[str, Any], ...]:
    selected_id = str(
        selected_task["id"]
    )

    visiting: set[str] = set()
    visited: set[str] = set()
    ordered: list[
        dict[str, Any]
    ] = []

    def visit(
        task_id: str,
    ) -> None:
        if task_id in visited:
            return

        if task_id in visiting:
            raise PacketError(
                "dependency cycle encountered while "
                f"resolving {task_id}"
            )

        task = task_index.get(
            task_id
        )

        if task is None:
            raise PacketError(
                f"dependency task missing from graph: {task_id}"
            )

        visiting.add(
            task_id
        )

        for dependency_id in task_dependency_ids(
            task
        ):
            visit(
                dependency_id
            )

        visiting.remove(
            task_id
        )

        visited.add(
            task_id
        )

        if task_id != selected_id:
            ordered.append(
                task
            )

    visit(
        selected_id
    )

    return tuple(
        ordered
    )


def build_assignment(
    *,
    ordinal: int,
    key: str,
    title: str,
    purpose: str,
    task: dict[str, Any],
    dependency_ids: tuple[str, ...],
    graph_digest: str,
) -> dict[str, Any]:
    task_id = str(
        task["id"]
    )

    assignment = {
        "id": (
            f"opus-assignment:"
            f"{task_id}:"
            f"{ordinal:02d}:"
            f"{key}"
        ),
        "ordinal": ordinal,
        "key": key,
        "title": title,
        "purpose": purpose,
        "task_id": task_id,
        "dependency_ids": list(
            dependency_ids
        ),
        "graph_digest": graph_digest,
        "authority_effect": "none",
        "output_class": (
            "advisory-evidence-candidate"
        ),
        "required_response_sections": list(
            REQUIRED_RESPONSE_SECTIONS
        ),
        "requirements": {
            "cite_source_paths": True,
            "distinguish_fact_from_inference": True,
            "preserve_unresolved_conflicts": True,
            "prefer_extension_over_replacement": True,
            "prefer_composition_over_duplication": True,
            "prefer_projection_over_duplicate_storage": True,
            "identify_dependencies_and_dependents": True,
            "provide_complete_validation": True,
            "provide_complete_recovery": True,
        },
    }

    assignment[
        "assignment_digest"
    ] = sha256_value(
        assignment
    )

    return assignment


def build_packet(
    graph: dict[str, Any],
    context: dict[str, Any],
) -> dict[str, Any]:
    payload = extract_projection_payload(
        context
    )

    selected_task = extract_selected_task(
        payload
    )

    selection = extract_selection(
        payload
    )

    audit = extract_audit(
        payload
    )

    task_index = graph_task_index(
        graph
    )

    selected_task_id = str(
        selected_task["id"]
    )

    authoritative_task = task_index.get(
        selected_task_id
    )

    if authoritative_task is None:
        raise PacketError(
            "selected task is absent from authoritative graph: "
            f"{selected_task_id}"
        )

    graph_digest = sha256_value(
        graph
    )

    recorded_graph_digest = context.get(
        "graph_digest"
    )

    if (
        isinstance(
            recorded_graph_digest,
            str,
        )
        and recorded_graph_digest
        and recorded_graph_digest
        != graph_digest
    ):
        raise PacketError(
            "agent context graph digest does not match "
            "the current authoritative graph"
        )

    dependencies = dependency_closure(
        authoritative_task,
        task_index,
    )

    dependency_ids = tuple(
        str(
            dependency["id"]
        )
        for dependency in dependencies
    )

    assignments = [
        build_assignment(
            ordinal=ordinal,
            key=key,
            title=title,
            purpose=purpose,
            task=authoritative_task,
            dependency_ids=dependency_ids,
            graph_digest=graph_digest,
        )
        for ordinal, (
            key,
            title,
            purpose,
        ) in enumerate(
            ANALYSIS_ASSIGNMENTS,
            start=1,
        )
    ]

    packet_body: dict[str, Any] = {
        "$schema": PACKET_SCHEMA,
        "packet_id": None,
        "generator": {
            "id": GENERATOR_ID,
            "version": GENERATOR_VERSION,
        },
        "authority": {
            "state": "projection",
            "source": str(
                MASTERPLAN_GRAPH
            ),
            "source_digest": graph_digest,
            "authority_effect": "none",
            "may_modify_authority": False,
            "may_modify_priority": False,
            "may_complete_task": False,
        },
        "opus_policy": {
            "orchestration_owner": "exile.opus",
            "provider_calls_owned_by_opus": True,
            "provider_outputs_are_authority": False,
            "provider_outputs_require_evidence_admission": True,
            "parallel_analysis_allowed": True,
            "cross_provider_comparison_allowed": True,
            "deterministic_packet_required": True,
            "allowed_actions": list(
                ALLOWED_AI_ACTIONS
            ),
            "forbidden_actions": list(
                FORBIDDEN_AI_ACTIONS
            ),
        },
        "selected_task": authoritative_task,
        "dependency_closure": list(
            dependencies
        ),
        "governing_rule": payload.get(
            "governing_rule"
        ),
        "selection": selection,
        "audit": audit,
        "assignments": assignments,
        "response_contract": {
            "assignment_count": 9,
            "required_sections_per_assignment": list(
                REQUIRED_RESPONSE_SECTIONS
            ),
            "final_synthesis_required": True,
            "final_synthesis_authority_effect": "none",
            "admission_route": [
                "masterplan-evidence",
                "masterplan-decision",
                "masterplan-transition",
                "masterplan-replay",
                "masterplan-verify",
                "masterplan-attest",
            ],
        },
        "provenance": {
            "sources": [
                {
                    "path": str(
                        MASTERPLAN_GRAPH
                    ),
                    "sha256": graph_digest,
                    "authority_state": "authoritative",
                },
                {
                    "path": str(
                        AGENT_CONTEXT
                    ),
                    "sha256": sha256_bytes(
                        pretty_json_bytes(
                            context
                        )
                    ),
                    "authority_state": "projection",
                },
            ],
            "transformations": [
                "load_authoritative_task_graph",
                "validate_agent_context",
                "resolve_selected_task",
                "resolve_dependency_closure",
                "project_nine_opus_assignments",
                "bind_advisory_evidence_policy",
            ],
            "generated_by": (
                f"{GENERATOR_ID}@"
                f"{GENERATOR_VERSION}"
            ),
        },
    }

    packet_id = (
        "masterplan-opus-packet:"
        + sha256_value(
            {
                key: value
                for key, value
                in packet_body.items()
                if key != "packet_id"
            }
        )[:24]
    )

    packet_body[
        "packet_id"
    ] = packet_id

    packet_body[
        "packet_digest"
    ] = sha256_value(
        {
            key: value
            for key, value
            in packet_body.items()
            if key != "packet_digest"
        }
    )

    return packet_body


def verify_packet(
    packet: dict[str, Any],
) -> None:
    if packet.get(
        "$schema"
    ) != PACKET_SCHEMA:
        raise PacketError(
            "packet schema mismatch"
        )

    packet_id = packet.get(
        "packet_id"
    )

    if not isinstance(
        packet_id,
        str,
    ) or not packet_id:
        raise PacketError(
            "packet lacks stable id"
        )

    assignments = packet.get(
        "assignments"
    )

    if not isinstance(
        assignments,
        list,
    ):
        raise PacketError(
            "packet assignments must be an array"
        )

    if len(
        assignments
    ) != 9:
        raise PacketError(
            "packet must contain exactly nine assignments"
        )

    ordinals = [
        assignment.get(
            "ordinal"
        )
        for assignment in assignments
        if isinstance(
            assignment,
            dict,
        )
    ]

    if ordinals != list(
        range(
            1,
            10,
        )
    ):
        raise PacketError(
            "assignment ordinals must be contiguous"
        )

    keys = [
        assignment.get(
            "key"
        )
        for assignment in assignments
        if isinstance(
            assignment,
            dict,
        )
    ]

    expected_keys = [
        key
        for key, _, _
        in ANALYSIS_ASSIGNMENTS
    ]

    if keys != expected_keys:
        raise PacketError(
            "assignment ordering differs from authority"
        )

    if len(
        keys
    ) != len(
        set(
            keys
        )
    ):
        raise PacketError(
            "assignment keys are duplicated"
        )

    policy = packet.get(
        "opus_policy"
    )

    if not isinstance(
        policy,
        dict,
    ):
        raise PacketError(
            "packet lacks Opus policy"
        )

    if policy.get(
        "provider_outputs_are_authority"
    ) is not False:
        raise PacketError(
            "provider output cannot be authority"
        )

    authority = packet.get(
        "authority"
    )

    if not isinstance(
        authority,
        dict,
    ):
        raise PacketError(
            "packet lacks authority boundary"
        )

    if authority.get(
        "authority_effect"
    ) != "none":
        raise PacketError(
            "packet may not alter authority"
        )

    recorded_digest = packet.get(
        "packet_digest"
    )

    if not isinstance(
        recorded_digest,
        str,
    ):
        raise PacketError(
            "packet lacks digest"
        )

    calculated_digest = sha256_value(
        {
            key: value
            for key, value
            in packet.items()
            if key != "packet_digest"
        }
    )

    if recorded_digest != calculated_digest:
        raise PacketError(
            "packet digest mismatch"
        )


def write_packet(
    packet: dict[str, Any],
) -> dict[str, Any]:
    timestamp = utc_timestamp()

    run_root = (
        REPORT_ROOT
        / timestamp
    )

    packet_path = (
        run_root
        / "packet.json"
    )

    manifest_path = (
        run_root
        / "manifest.json"
    )

    latest_path = (
        REPORT_ROOT
        / "latest.json"
    )

    packet_bytes = pretty_json_bytes(
        packet
    )

    atomic_write(
        packet_path,
        packet_bytes,
    )

    manifest = {
        "$schema": (
            "savant://niche/masterplan/"
            "opus-work-packet-manifest/1.0.0"
        ),
        "packet_id": packet[
            "packet_id"
        ],
        "entries": [
            {
                "path": str(
                    packet_path
                ),
                "sha256": sha256_bytes(
                    packet_path.read_bytes()
                ),
                "size": packet_path.stat().st_size,
            }
        ],
    }

    atomic_write(
        manifest_path,
        pretty_json_bytes(
            manifest
        ),
    )

    latest = {
        "packet_id": packet[
            "packet_id"
        ],
        "packet_digest": packet[
            "packet_digest"
        ],
        "selected_task_id": packet[
            "selected_task"
        ][
            "id"
        ],
        "assignment_count": len(
            packet[
                "assignments"
            ]
        ),
        "packet": str(
            packet_path
        ),
        "manifest": str(
            manifest_path
        ),
        "authority_effect": "none",
        "provider_calls_performed": False,
        "generated_at": timestamp,
    }

    atomic_write(
        latest_path,
        pretty_json_bytes(
            latest
        ),
    )

    return latest


def run_build() -> dict[str, Any]:
    graph = load_json(
        MASTERPLAN_GRAPH
    )

    context = load_json(
        AGENT_CONTEXT
    )

    packet = build_packet(
        graph,
        context,
    )

    verify_packet(
        packet
    )

    latest = write_packet(
        packet
    )

    return {
        "operation": (
            "build_masterplan_opus_packet"
        ),
        "passed": True,
        "packet_id": latest[
            "packet_id"
        ],
        "selected_task_id": latest[
            "selected_task_id"
        ],
        "assignment_count": latest[
            "assignment_count"
        ],
        "authority_effect": "none",
        "provider_calls_performed": False,
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

    raw_packet_path = latest.get(
        "packet"
    )

    raw_manifest_path = latest.get(
        "manifest"
    )

    if not isinstance(
        raw_packet_path,
        str,
    ):
        raise PacketError(
            "latest pointer lacks packet path"
        )

    if not isinstance(
        raw_manifest_path,
        str,
    ):
        raise PacketError(
            "latest pointer lacks manifest path"
        )

    packet_path = Path(
        raw_packet_path
    )

    manifest_path = Path(
        raw_manifest_path
    )

    packet = load_json(
        packet_path
    )

    manifest = load_json(
        manifest_path
    )

    verify_packet(
        packet
    )

    entries = manifest.get(
        "entries"
    )

    if not isinstance(
        entries,
        list,
    ):
        raise PacketError(
            "manifest entries must be an array"
        )

    if len(
        entries
    ) != 1:
        raise PacketError(
            "manifest must contain one packet entry"
        )

    entry = entries[0]

    if not isinstance(
        entry,
        dict,
    ):
        raise PacketError(
            "manifest entry must be an object"
        )

    expected_path = entry.get(
        "path"
    )

    expected_digest = entry.get(
        "sha256"
    )

    expected_size = entry.get(
        "size"
    )

    if expected_path != str(
        packet_path
    ):
        raise PacketError(
            "manifest packet path mismatch"
        )

    packet_bytes = packet_path.read_bytes()

    if expected_digest != sha256_bytes(
        packet_bytes
    ):
        raise PacketError(
            "manifest packet digest mismatch"
        )

    if expected_size != len(
        packet_bytes
    ):
        raise PacketError(
            "manifest packet size mismatch"
        )

    return {
        "operation": (
            "verify_masterplan_opus_packet"
        ),
        "passed": True,
        "packet_id": packet[
            "packet_id"
        ],
        "selected_task_id": packet[
            "selected_task"
        ][
            "id"
        ],
        "assignment_count": len(
            packet[
                "assignments"
            ]
        ),
        "authority_effect": "none",
        "provider_calls_performed": False,
        "manifest_entry_count": len(
            entries
        ),
    }


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Build or verify an authority-bounded "
            "Masterplan work packet for Opus."
        )
    )

    parser.add_argument(
        "operation",
        choices=(
            "build",
            "verify",
        ),
    )

    return parser.parse_args()


def main() -> int:
    arguments = parse_arguments()

    try:
        if arguments.operation == "build":
            result = run_build()
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

    except PacketError as error:
        print(
            json.dumps(
                {
                    "operation": (
                        arguments.operation
                    ),
                    "passed": False,
                    "authority_effect": "none",
                    "provider_calls_performed": False,
                    "error": str(
                        error
                    ),
                },
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            ),
            file=sys.stderr,
        )

        return 1


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
