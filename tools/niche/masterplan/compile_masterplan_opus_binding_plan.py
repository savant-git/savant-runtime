#!/usr/bin/env python3
"""
Compile a deterministic Masterplan-to-Opus binding plan.

This tool consumes the latest verified Opus binding-discovery report and
projects the exact adapter work required to connect the Masterplan living task
queue to the current Opus implementation.

It does not:

- create an Opus replacement
- duplicate provider logic
- call any provider
- mutate Masterplan
- mutate Opus
- modify authority
- invent missing capabilities
- silently choose between tied implementations
- perform implementation writes outside its report directory

The plan remains blocked unless discovery uniquely selected a current runtime.
Missing capabilities are preserved as explicit implementation requirements.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import tempfile
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Final


ROOT: Final[Path] = Path(
    "/root/savant-runtime"
).resolve()

DISCOVERY_ROOT: Final[Path] = (
    ROOT
    / "reports"
    / "niche"
    / "masterplan"
    / "opus-binding-discovery"
)

LATEST_DISCOVERY: Final[Path] = (
    DISCOVERY_ROOT
    / "latest.json"
)

QUEUE_LATEST: Final[Path] = (
    ROOT
    / "reports"
    / "niche"
    / "masterplan"
    / "opus-queue"
    / "latest.json"
)

PLAN_ROOT: Final[Path] = (
    ROOT
    / "reports"
    / "niche"
    / "masterplan"
    / "opus-binding-plan"
)

PLAN_SCHEMA: Final[str] = (
    "savant://niche/masterplan/"
    "opus-binding-plan/1.0.0"
)

PLANNER_ID: Final[str] = (
    "prodigal.niche.masterplan."
    "compile_masterplan_opus_binding_plan"
)

PLANNER_VERSION: Final[str] = "1.0.0"

BINDING_LAYERS: Final[
    tuple[str, ...]
] = (
    "authority",
    "request",
    "validation",
    "routing",
    "execution",
    "response",
    "events",
    "lineage",
    "evidence",
)

BINDING_ACTIONS: Final[
    tuple[str, ...]
] = (
    "reuse",
    "adapt",
    "extend",
    "validate",
    "register",
    "mediate",
    "observe",
    "project",
    "defer",
)

PLAN_STATES: Final[
    tuple[str, ...]
] = (
    "blocked",
    "discovered",
    "planned",
)

CAPABILITY_TO_LAYER: Final[
    dict[str, str]
] = {
    "request_creation": "request",
    "request_validation": "validation",
    "provider_discovery": "routing",
    "provider_routing": "routing",
    "provider_execution": "execution",
    "response_validation": "response",
    "event_publication": "events",
    "lineage_capture": "lineage",
    "evidence_handoff": "evidence",
}

CAPABILITY_REQUIREMENTS: Final[
    dict[str, str]
] = {
    "request_creation": (
        "Translate each Masterplan Opus queue request into the current "
        "Opus request primitive without duplicating request substance."
    ),
    "request_validation": (
        "Validate every translated request against the current Opus "
        "request contract before provider routing."
    ),
    "provider_discovery": (
        "Resolve eligible providers through the current Opus provider "
        "registry and capability model."
    ),
    "provider_routing": (
        "Route each assignment through current Opus policy, fallback, "
        "budget, and provider-selection primitives."
    ),
    "provider_execution": (
        "Execute provider calls exclusively through current Opus execution "
        "primitives with bounded retries and preserved failures."
    ),
    "response_validation": (
        "Validate normalized provider outputs before synthesis or queue "
        "state transition."
    ),
    "event_publication": (
        "Publish request, routing, execution, response, failure, and "
        "completion events through the current event system."
    ),
    "lineage_capture": (
        "Preserve task, packet, assignment, request, provider, response, "
        "synthesis, and evidence lineage."
    ),
    "evidence_handoff": (
        "Project successful synthesized outputs into Masterplan evidence "
        "candidates without admitting them automatically."
    ),
}

LIFECYCLE_TRANSITIONS: Final[
    tuple[tuple[str, str], ...]
] = (
    (
        "queued",
        "leased",
    ),
    (
        "leased",
        "running",
    ),
    (
        "running",
        "succeeded",
    ),
    (
        "running",
        "failed",
    ),
    (
        "failed",
        "queued",
    ),
    (
        "queued",
        "deferred",
    ),
    (
        "deferred",
        "queued",
    ),
    (
        "succeeded",
        "admitted",
    ),
    (
        "queued",
        "cancelled",
    ),
)

VALIDATION_GATES: Final[
    tuple[str, ...]
] = (
    "authority_preserved",
    "selected_runtime_verified",
    "queue_contract_verified",
    "request_adapter_verified",
    "routing_adapter_verified",
    "response_adapter_verified",
    "lineage_verified",
    "replay_verified",
    "evidence_boundary_verified",
)


class PlanError(RuntimeError):
    """Raised when a binding plan cannot be compiled reliably."""


@dataclass(frozen=True, slots=True)
class CapabilityPlan:
    ordinal: int
    capability: str
    layer: str
    action: str
    requirement: str
    source_paths: tuple[str, ...]
    source_present: bool
    implementation_required: bool
    blockers: tuple[str, ...]


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


def semantic_digest(
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
        raise PlanError(
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
        raise PlanError(
            f"cannot read JSON {path}: {error}"
        ) from error

    if not isinstance(
        value,
        dict,
    ):
        raise PlanError(
            f"JSON root must be an object: {path}"
        )

    return value


def confined_path(
    raw_path: object,
    field: str,
) -> Path:
    if not isinstance(
        raw_path,
        str,
    ):
        raise PlanError(
            f"{field} must be a string path"
        )

    path = Path(
        raw_path
    )

    if not path.is_absolute():
        raise PlanError(
            f"{field} must be absolute: {path}"
        )

    resolved = path.resolve(
        strict=False
    )

    try:
        resolved.relative_to(
            ROOT
        )
    except ValueError as error:
        raise PlanError(
            f"{field} escapes runtime root: {resolved}"
        ) from error

    return resolved


def resolve_discovery() -> tuple[
    Path,
    dict[str, Any],
]:
    latest = load_json(
        LATEST_DISCOVERY
    )

    report_path = confined_path(
        latest.get(
            "report"
        ),
        "discovery report",
    )

    discovery = load_json(
        report_path
    )

    return report_path, discovery


def resolve_queue() -> tuple[
    Path,
    dict[str, Any],
]:
    latest = load_json(
        QUEUE_LATEST
    )

    queue_path = confined_path(
        latest.get(
            "queue"
        ),
        "Masterplan Opus queue",
    )

    queue = load_json(
        queue_path
    )

    return queue_path, queue


def selected_candidate_path(
    discovery: dict[str, Any],
) -> str | None:
    selected = discovery.get(
        "selected_candidate"
    )

    if not isinstance(
        selected,
        dict,
    ):
        return None

    path = selected.get(
        "path"
    )

    if not isinstance(
        path,
        str,
    ):
        return None

    return path


def compile_capability_plans(
    discovery: dict[str, Any],
) -> tuple[
    CapabilityPlan,
    ...,
]:
    matrix = discovery.get(
        "capability_matrix"
    )

    if not isinstance(
        matrix,
        dict,
    ):
        raise PlanError(
            "discovery lacks capability matrix"
        )

    plans: list[
        CapabilityPlan
    ] = []

    for ordinal, capability in enumerate(
        CAPABILITY_TO_LAYER,
        start=1,
    ):
        raw_paths = matrix.get(
            capability
        )

        source_paths = tuple(
            sorted(
                {
                    str(
                        path
                    )
                    for path in (
                        raw_paths
                        if isinstance(
                            raw_paths,
                            list,
                        )
                        else []
                    )
                    if str(
                        path
                    ).strip()
                }
            )
        )

        source_present = bool(
            source_paths
        )

        blockers: list[str] = []

        if source_present:
            action = "adapt"
            implementation_required = True
        else:
            action = "extend"
            implementation_required = True
            blockers.append(
                "current selected Opus runtime lacks "
                f"discovered capability: {capability}"
            )

        plans.append(
            CapabilityPlan(
                ordinal=ordinal,
                capability=capability,
                layer=CAPABILITY_TO_LAYER[
                    capability
                ],
                action=action,
                requirement=(
                    CAPABILITY_REQUIREMENTS[
                        capability
                    ]
                ),
                source_paths=source_paths,
                source_present=source_present,
                implementation_required=(
                    implementation_required
                ),
                blockers=tuple(
                    blockers
                ),
            )
        )

    return tuple(
        plans
    )


def build_plan(
    *,
    discovery_path: Path,
    discovery: dict[str, Any],
    queue_path: Path,
    queue: dict[str, Any],
) -> dict[str, Any]:
    selected_path = selected_candidate_path(
        discovery
    )

    selection_state = discovery.get(
        "selection_state"
    )

    capability_plans = (
        compile_capability_plans(
            discovery
        )
    )

    blockers: list[str] = []

    if selection_state != "selected":
        blockers.append(
            "current Opus runtime is not uniquely selected"
        )

    if selected_path is None:
        blockers.append(
            "selected Opus runtime path is unavailable"
        )

    queue_record_count = queue.get(
        "record_count"
    )

    if queue_record_count != 9:
        blockers.append(
            "Masterplan Opus queue does not contain "
            "exactly nine work records"
        )

    for capability_plan in capability_plans:
        blockers.extend(
            capability_plan.blockers
        )

    plan_state = (
        "planned"
        if not blockers
        else "blocked"
    )

    task = queue.get(
        "task"
    )

    if not isinstance(
        task,
        dict,
    ):
        raise PlanError(
            "queue lacks selected task"
        )

    queue_id = queue.get(
        "queue_id"
    )

    if not isinstance(
        queue_id,
        str,
    ):
        raise PlanError(
            "queue lacks stable id"
        )

    plan: dict[str, Any] = {
        "$schema": PLAN_SCHEMA,
        "plan_id": None,
        "planner": {
            "id": PLANNER_ID,
            "version": PLANNER_VERSION,
        },
        "state": plan_state,
        "task": task,
        "queue": {
            "id": queue_id,
            "path": str(
                queue_path
            ),
            "digest": queue.get(
                "queue_digest"
            ),
        },
        "discovery": {
            "path": str(
                discovery_path
            ),
            "digest": discovery.get(
                "semantic_digest"
            ),
            "selection_state": (
                selection_state
            ),
            "selected_runtime": (
                selected_path
            ),
        },
        "binding_layers": list(
            BINDING_LAYERS
        ),
        "binding_actions": list(
            BINDING_ACTIONS
        ),
        "lifecycle_transitions": [
            {
                "ordinal": ordinal,
                "from": source,
                "to": target,
            }
            for ordinal, (
                source,
                target,
            ) in enumerate(
                LIFECYCLE_TRANSITIONS,
                start=1,
            )
        ],
        "validation_gates": list(
            VALIDATION_GATES
        ),
        "capability_plans": [
            asdict(
                capability_plan
            )
            for capability_plan
            in capability_plans
        ],
        "implementation_contract": {
            "extend_current_runtime": True,
            "parallel_opus_runtime_forbidden": True,
            "reuse_existing_provider_adapters": True,
            "reuse_existing_routing": True,
            "reuse_existing_event_system": True,
            "reuse_existing_lineage": True,
            "provider_calls_owned_by_opus": True,
            "masterplan_authority_preserved": True,
            "automatic_evidence_admission_forbidden": True,
        },
        "automation_contract": {
            "lease_ready_records": True,
            "respect_record_dependencies": True,
            "execute_independent_records_concurrently": True,
            "retry_transient_failures": True,
            "preserve_terminal_failures": True,
            "normalize_provider_outputs": True,
            "synthesize_multi_provider_results": True,
            "write_content_addressed_receipts": True,
            "return_evidence_candidates_to_masterplan": True,
        },
        "blockers": list(
            dict.fromkeys(
                blockers
            )
        ),
        "authority": {
            "state": "projection",
            "effect": "none",
            "implementation_authorized": False,
            "provider_execution_authorized": False,
            "task_transition_authorized": False,
            "evidence_admission_authorized": False,
        },
        "provenance": {
            "sources": [
                {
                    "path": str(
                        discovery_path
                    ),
                    "sha256": sha256_bytes(
                        discovery_path.read_bytes()
                    ),
                },
                {
                    "path": str(
                        queue_path
                    ),
                    "sha256": sha256_bytes(
                        queue_path.read_bytes()
                    ),
                },
            ],
            "generated_by": (
                f"{PLANNER_ID}@"
                f"{PLANNER_VERSION}"
            ),
            "transformations": [
                "load_binding_discovery",
                "load_living_queue",
                "resolve_selected_runtime",
                "map_capabilities_to_layers",
                "derive_adapter_requirements",
                "preserve_missing_capabilities",
                "compile_validation_gates",
                "compile_reversible_plan",
                "withhold_implementation_authority",
            ],
        },
    }

    plan_id = (
        "masterplan-opus-binding-plan:"
        + semantic_digest(
            {
                key: value
                for key, value
                in plan.items()
                if key != "plan_id"
            }
        )[:24]
    )

    plan[
        "plan_id"
    ] = plan_id

    plan[
        "semantic_digest"
    ] = semantic_digest(
        {
            key: value
            for key, value
            in plan.items()
            if key != "semantic_digest"
        }
    )

    return plan


def verify_plan(
    plan: dict[str, Any],
) -> None:
    if plan.get(
        "$schema"
    ) != PLAN_SCHEMA:
        raise PlanError(
            "binding plan schema mismatch"
        )

    if plan.get(
        "state"
    ) not in PLAN_STATES:
        raise PlanError(
            "binding plan state is invalid"
        )

    if len(
        BINDING_LAYERS
    ) != 9:
        raise PlanError(
            "binding layer cardinality must equal nine"
        )

    if len(
        BINDING_ACTIONS
    ) != 9:
        raise PlanError(
            "binding action cardinality must equal nine"
        )

    if len(
        CAPABILITY_TO_LAYER
    ) != 9:
        raise PlanError(
            "capability plan cardinality must equal nine"
        )

    if len(
        LIFECYCLE_TRANSITIONS
    ) != 9:
        raise PlanError(
            "lifecycle transition cardinality must equal nine"
        )

    if len(
        VALIDATION_GATES
    ) != 9:
        raise PlanError(
            "validation gate cardinality must equal nine"
        )

    capability_plans = plan.get(
        "capability_plans"
    )

    if not isinstance(
        capability_plans,
        list,
    ) or len(
        capability_plans
    ) != 9:
        raise PlanError(
            "binding plan must contain nine capability plans"
        )

    ordinals = [
        item.get(
            "ordinal"
        )
        for item in capability_plans
        if isinstance(
            item,
            dict,
        )
    ]

    if ordinals != list(
        range(
            1,
            10,
        )
    ):
        raise PlanError(
            "capability plan ordinals are invalid"
        )

    authority = plan.get(
        "authority"
    )

    if not isinstance(
        authority,
        dict,
    ):
        raise PlanError(
            "binding plan lacks authority boundary"
        )

    if authority.get(
        "effect"
    ) != "none":
        raise PlanError(
            "binding plan may not alter authority"
        )

    if authority.get(
        "implementation_authorized"
    ) is not False:
        raise PlanError(
            "binding plan prematurely authorizes implementation"
        )

    recorded_digest = plan.get(
        "semantic_digest"
    )

    if not isinstance(
        recorded_digest,
        str,
    ):
        raise PlanError(
            "binding plan lacks semantic digest"
        )

    calculated_digest = semantic_digest(
        {
            key: value
            for key, value
            in plan.items()
            if key != "semantic_digest"
        }
    )

    if calculated_digest != recorded_digest:
        raise PlanError(
            "binding plan semantic digest mismatch"
        )


def write_plan(
    plan: dict[str, Any],
) -> dict[str, Any]:
    timestamp = utc_timestamp()

    run_root = (
        PLAN_ROOT
        / timestamp
    )

    plan_path = (
        run_root
        / "plan.json"
    )

    manifest_path = (
        run_root
        / "manifest.json"
    )

    latest_path = (
        PLAN_ROOT
        / "latest.json"
    )

    atomic_write(
        plan_path,
        pretty_json_bytes(
            plan
        ),
    )

    manifest = {
        "$schema": (
            "savant://niche/masterplan/"
            "opus-binding-plan-manifest/1.0.0"
        ),
        "plan_id": plan[
            "plan_id"
        ],
        "entries": [
            {
                "path": str(
                    plan_path
                ),
                "sha256": sha256_bytes(
                    plan_path.read_bytes()
                ),
                "size": (
                    plan_path.stat().st_size
                ),
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
        "plan_id": plan[
            "plan_id"
        ],
        "semantic_digest": plan[
            "semantic_digest"
        ],
        "state": plan[
            "state"
        ],
        "task_id": plan[
            "task"
        ][
            "id"
        ],
        "queue_id": plan[
            "queue"
        ][
            "id"
        ],
        "selected_runtime": plan[
            "discovery"
        ][
            "selected_runtime"
        ],
        "blocker_count": len(
            plan[
                "blockers"
            ]
        ),
        "plan": str(
            plan_path
        ),
        "manifest": str(
            manifest_path
        ),
        "authority_effect": "none",
        "implementation_authorized": False,
        "provider_execution_authorized": False,
        "generated_at": timestamp,
    }

    atomic_write(
        latest_path,
        pretty_json_bytes(
            latest
        ),
    )

    return latest


def verify_manifest(
    manifest_path: Path,
) -> int:
    manifest = load_json(
        manifest_path
    )

    entries = manifest.get(
        "entries"
    )

    if not isinstance(
        entries,
        list,
    ):
        raise PlanError(
            "manifest entries must be an array"
        )

    for entry in entries:
        if not isinstance(
            entry,
            dict,
        ):
            raise PlanError(
                "manifest entry must be an object"
            )

        artifact_path = confined_path(
            entry.get(
                "path"
            ),
            "manifest entry path",
        )

        if not artifact_path.is_file():
            raise PlanError(
                f"manifest file missing: {artifact_path}"
            )

        content = artifact_path.read_bytes()

        if entry.get(
            "sha256"
        ) != sha256_bytes(
            content
        ):
            raise PlanError(
                f"manifest digest mismatch: {artifact_path}"
            )

        if entry.get(
            "size"
        ) != len(
            content
        ):
            raise PlanError(
                f"manifest size mismatch: {artifact_path}"
            )

    return len(
        entries
    )


def run_compile() -> dict[str, Any]:
    discovery_path, discovery = (
        resolve_discovery()
    )

    queue_path, queue = (
        resolve_queue()
    )

    plan = build_plan(
        discovery_path=discovery_path,
        discovery=discovery,
        queue_path=queue_path,
        queue=queue,
    )

    verify_plan(
        plan
    )

    latest = write_plan(
        plan
    )

    return {
        "operation": (
            "compile_masterplan_opus_binding_plan"
        ),
        "passed": (
            plan[
                "state"
            ]
            == "planned"
        ),
        "state": plan[
            "state"
        ],
        "plan_id": plan[
            "plan_id"
        ],
        "task_id": latest[
            "task_id"
        ],
        "selected_runtime": latest[
            "selected_runtime"
        ],
        "blocker_count": latest[
            "blocker_count"
        ],
        "authority_effect": "none",
        "implementation_authorized": False,
        "provider_execution_authorized": False,
        "latest": str(
            PLAN_ROOT
            / "latest.json"
        ),
    }


def run_verify() -> dict[str, Any]:
    latest_path = (
        PLAN_ROOT
        / "latest.json"
    )

    latest = load_json(
        latest_path
    )

    plan_path = confined_path(
        latest.get(
            "plan"
        ),
        "binding plan",
    )

    manifest_path = confined_path(
        latest.get(
            "manifest"
        ),
        "binding plan manifest",
    )

    plan = load_json(
        plan_path
    )

    verify_plan(
        plan
    )

    manifest_entry_count = (
        verify_manifest(
            manifest_path
        )
    )

    return {
        "operation": (
            "verify_masterplan_opus_binding_plan"
        ),
        "passed": True,
        "plan_state": plan[
            "state"
        ],
        "plan_id": plan[
            "plan_id"
        ],
        "task_id": plan[
            "task"
        ][
            "id"
        ],
        "selected_runtime": plan[
            "discovery"
        ][
            "selected_runtime"
        ],
        "blocker_count": len(
            plan[
                "blockers"
            ]
        ),
        "manifest_entry_count": (
            manifest_entry_count
        ),
        "authority_effect": "none",
        "implementation_authorized": False,
        "provider_execution_authorized": False,
    }


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Compile or verify the deterministic "
            "Masterplan-to-Opus binding plan."
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
                indent=2,
                sort_keys=True,
            )
        )

        if arguments.operation == "verify":
            return 0

        return (
            0
            if result[
                "passed"
            ]
            else 2
        )

    except (
        KeyError,
        OSError,
        PlanError,
        json.JSONDecodeError,
    ) as error:
        print(
            json.dumps(
                {
                    "operation": (
                        arguments.operation
                    ),
                    "passed": False,
                    "authority_effect": "none",
                    "implementation_authorized": False,
                    "provider_execution_authorized": False,
                    "error": str(
                        error
                    ),
                },
                indent=2,
                sort_keys=True,
            )
        )

        return 1


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
