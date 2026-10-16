#!/usr/bin/env python3
"""
Compile a complete, read-only implementation workspace for Masterplan-to-Opus.

The workspace is derived from the latest verified binding plan. It gathers the
actual current Opus source artifacts referenced by discovery, preserves their
digests and provenance, maps them to the nine binding capabilities, and emits a
deterministic implementation packet.

This stage does not:

- modify Masterplan
- modify Opus
- call providers
- admit evidence
- accept decisions
- transition tasks
- create replacement implementation
- infer missing source content
- authorize implementation
- conceal binding-plan blockers

A blocked plan still produces a diagnostic workspace. An implementation-ready
workspace is produced only when the plan is planned and every referenced source
artifact remains present and digestible.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import tempfile
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Final


ROOT: Final[Path] = Path(
    "/root/savant-runtime"
).resolve()

PLAN_ROOT: Final[Path] = (
    ROOT
    / "reports"
    / "niche"
    / "masterplan"
    / "opus-binding-plan"
)

LATEST_PLAN: Final[Path] = (
    PLAN_ROOT
    / "latest.json"
)

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

WORKSPACE_ROOT: Final[Path] = (
    ROOT
    / "runtime"
    / "masterplan"
    / "opus"
    / "binding-workspaces"
)

REPORT_ROOT: Final[Path] = (
    ROOT
    / "reports"
    / "niche"
    / "masterplan"
    / "opus-binding-workspace"
)

WORKSPACE_SCHEMA: Final[str] = (
    "savant://niche/masterplan/"
    "opus-binding-workspace/1.0.0"
)

COMPILER_ID: Final[str] = (
    "prodigal.niche.masterplan."
    "compile_masterplan_opus_binding_workspace"
)

COMPILER_VERSION: Final[str] = "1.0.0"

WORKSPACE_STATES: Final[
    tuple[str, ...]
] = (
    "blocked",
    "diagnostic",
    "ready",
)

SOURCE_CLASSES: Final[
    tuple[str, ...]
] = (
    "authority",
    "protocol",
    "provider",
    "registry",
    "router",
    "worker",
    "event",
    "lineage",
    "evidence",
)

CAPABILITIES: Final[
    tuple[str, ...]
] = (
    "request_creation",
    "request_validation",
    "provider_discovery",
    "provider_routing",
    "provider_execution",
    "response_validation",
    "event_publication",
    "lineage_capture",
    "evidence_handoff",
)

IMPLEMENTATION_PHASES: Final[
    tuple[str, ...]
] = (
    "baseline",
    "contract",
    "adapter",
    "routing",
    "execution",
    "normalization",
    "lineage",
    "evidence",
    "integration",
)

VALIDATION_PHASES: Final[
    tuple[str, ...]
] = (
    "syntax",
    "schema",
    "unit",
    "property",
    "integration",
    "determinism",
    "concurrency",
    "recovery",
    "regression",
)


class WorkspaceError(RuntimeError):
    """Raised when a binding workspace cannot be compiled reliably."""


@dataclass(frozen=True, slots=True)
class SourceArtifact:
    path: str
    relative_path: str
    suffix: str
    size: int
    sha256: str
    artifact_class: str
    capabilities: tuple[str, ...]
    authority_score: int
    historical_score: int
    symbols: tuple[str, ...]
    imports: tuple[str, ...]
    source_present: bool
    source_current: bool
    blockers: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class CapabilityWorkspace:
    ordinal: int
    capability: str
    layer: str
    action: str
    requirement: str
    source_paths: tuple[str, ...]
    source_artifact_ids: tuple[str, ...]
    implementation_required: bool
    ready: bool
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
        raise WorkspaceError(
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
        raise WorkspaceError(
            f"cannot read JSON {path}: {error}"
        ) from error

    if not isinstance(
        value,
        dict,
    ):
        raise WorkspaceError(
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
        raise WorkspaceError(
            f"{field} must be a string path"
        )

    path = Path(
        raw_path
    )

    if not path.is_absolute():
        raise WorkspaceError(
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
        raise WorkspaceError(
            f"{field} escapes runtime root: {resolved}"
        ) from error

    return resolved


def resolve_plan() -> tuple[
    Path,
    dict[str, Any],
]:
    latest = load_json(
        LATEST_PLAN
    )

    plan_path = confined_path(
        latest.get(
            "plan"
        ),
        "binding plan",
    )

    return (
        plan_path,
        load_json(
            plan_path
        ),
    )


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
        "binding discovery report",
    )

    return (
        report_path,
        load_json(
            report_path
        ),
    )


def artifact_identity(
    path: str,
    digest: str,
) -> str:
    return (
        "opus-source-artifact:"
        + semantic_digest(
            {
                "path": path,
                "sha256": digest,
            }
        )[:24]
    )


def normalize_string_tuple(
    value: object,
) -> tuple[str, ...]:
    if not isinstance(
        value,
        list,
    ):
        return ()

    return tuple(
        sorted(
            {
                str(
                    item
                )
                for item in value
                if str(
                    item
                ).strip()
            }
        )
    )


def compile_source_artifact(
    selected_runtime: Path,
    raw_artifact: dict[str, Any],
) -> tuple[
    str,
    SourceArtifact,
]:
    raw_path = raw_artifact.get(
        "path"
    )

    path = confined_path(
        raw_path,
        "discovered source artifact",
    )

    blockers: list[str] = []

    source_present = path.is_file()

    expected_digest = raw_artifact.get(
        "sha256"
    )

    if not isinstance(
        expected_digest,
        str,
    ):
        expected_digest = ""
        blockers.append(
            "discovery artifact lacks source digest"
        )

    current_digest = ""

    if source_present:
        current_digest = sha256_bytes(
            path.read_bytes()
        )

        if (
            expected_digest
            and current_digest
            != expected_digest
        ):
            blockers.append(
                "source artifact changed after discovery"
            )
    else:
        blockers.append(
            "source artifact is missing"
        )

    try:
        relative_path = path.relative_to(
            selected_runtime
        ).as_posix()
    except ValueError:
        relative_path = path.relative_to(
            ROOT
        ).as_posix()

        blockers.append(
            "source artifact is outside selected runtime root"
        )

    artifact_class = str(
        raw_artifact.get(
            "artifact_class",
            "",
        )
    )

    if artifact_class not in SOURCE_CLASSES:
        blockers.append(
            "source artifact class is invalid"
        )

    capabilities = normalize_string_tuple(
        raw_artifact.get(
            "capabilities"
        )
    )

    unknown_capabilities = set(
        capabilities
    ) - set(
        CAPABILITIES
    )

    if unknown_capabilities:
        blockers.append(
            "source artifact contains unknown capabilities: "
            + ", ".join(
                sorted(
                    unknown_capabilities
                )
            )
        )

    source_current = (
        source_present
        and bool(
            expected_digest
        )
        and current_digest
        == expected_digest
    )

    digest_for_identity = (
        current_digest
        or expected_digest
        or semantic_digest(
            {
                "path": str(
                    path
                ),
                "missing": True,
            }
        )
    )

    artifact_id = artifact_identity(
        str(
            path
        ),
        digest_for_identity,
    )

    artifact = SourceArtifact(
        path=str(
            path
        ),
        relative_path=relative_path,
        suffix=str(
            raw_artifact.get(
                "suffix",
                path.suffix.casefold(),
            )
        ),
        size=(
            path.stat().st_size
            if source_present
            else int(
                raw_artifact.get(
                    "size",
                    0,
                )
                or 0
            )
        ),
        sha256=(
            current_digest
            or expected_digest
        ),
        artifact_class=artifact_class,
        capabilities=capabilities,
        authority_score=int(
            raw_artifact.get(
                "authority_score",
                0,
            )
            or 0
        ),
        historical_score=int(
            raw_artifact.get(
                "historical_score",
                0,
            )
            or 0
        ),
        symbols=normalize_string_tuple(
            raw_artifact.get(
                "symbols"
            )
        ),
        imports=normalize_string_tuple(
            raw_artifact.get(
                "imports"
            )
        ),
        source_present=source_present,
        source_current=source_current,
        blockers=tuple(
            dict.fromkeys(
                blockers
            )
        ),
    )

    return artifact_id, artifact


def compile_sources(
    discovery: dict[str, Any],
) -> tuple[
    Path,
    dict[str, SourceArtifact],
]:
    selected = discovery.get(
        "selected_candidate"
    )

    if not isinstance(
        selected,
        dict,
    ):
        raise WorkspaceError(
            "binding discovery lacks selected runtime"
        )

    selected_runtime = confined_path(
        selected.get(
            "path"
        ),
        "selected Opus runtime",
    )

    raw_artifacts = discovery.get(
        "selected_artifacts"
    )

    if not isinstance(
        raw_artifacts,
        list,
    ):
        raise WorkspaceError(
            "binding discovery artifacts must be an array"
        )

    artifacts: dict[
        str,
        SourceArtifact,
    ] = {}

    for raw_artifact in raw_artifacts:
        if not isinstance(
            raw_artifact,
            dict,
        ):
            raise WorkspaceError(
                "binding discovery artifact must be an object"
            )

        artifact_id, artifact = (
            compile_source_artifact(
                selected_runtime,
                raw_artifact,
            )
        )

        if artifact_id in artifacts:
            raise WorkspaceError(
                f"duplicate source artifact identity: {artifact_id}"
            )

        artifacts[
            artifact_id
        ] = artifact

    return selected_runtime, artifacts


def capability_artifact_ids(
    capability: str,
    artifacts: dict[
        str,
        SourceArtifact,
    ],
) -> tuple[str, ...]:
    return tuple(
        sorted(
            artifact_id
            for artifact_id, artifact
            in artifacts.items()
            if capability
            in artifact.capabilities
        )
    )


def compile_capability_workspaces(
    plan: dict[str, Any],
    artifacts: dict[
        str,
        SourceArtifact,
    ],
) -> tuple[
    CapabilityWorkspace,
    ...,
]:
    raw_plans = plan.get(
        "capability_plans"
    )

    if not isinstance(
        raw_plans,
        list,
    ):
        raise WorkspaceError(
            "binding plan capability plans must be an array"
        )

    if len(
        raw_plans
    ) != 9:
        raise WorkspaceError(
            "binding plan must contain nine capability plans"
        )

    workspaces: list[
        CapabilityWorkspace
    ] = []

    for raw_plan in raw_plans:
        if not isinstance(
            raw_plan,
            dict,
        ):
            raise WorkspaceError(
                "binding capability plan must be an object"
            )

        capability = str(
            raw_plan.get(
                "capability",
                "",
            )
        )

        if capability not in CAPABILITIES:
            raise WorkspaceError(
                f"unknown binding capability: {capability}"
            )

        source_artifact_ids = (
            capability_artifact_ids(
                capability,
                artifacts,
            )
        )

        blockers = [
            str(
                blocker
            )
            for blocker in raw_plan.get(
                "blockers",
                [],
            )
            if str(
                blocker
            ).strip()
        ]

        if not source_artifact_ids:
            blockers.append(
                "no current source artifact implements capability"
            )

        for artifact_id in source_artifact_ids:
            artifact = artifacts[
                artifact_id
            ]

            blockers.extend(
                artifact.blockers
            )

        ready = (
            not blockers
            and bool(
                source_artifact_ids
            )
        )

        workspaces.append(
            CapabilityWorkspace(
                ordinal=int(
                    raw_plan.get(
                        "ordinal",
                        0,
                    )
                    or 0
                ),
                capability=capability,
                layer=str(
                    raw_plan.get(
                        "layer",
                        "",
                    )
                ),
                action=str(
                    raw_plan.get(
                        "action",
                        "",
                    )
                ),
                requirement=str(
                    raw_plan.get(
                        "requirement",
                        "",
                    )
                ),
                source_paths=tuple(
                    str(
                        path
                    )
                    for path in raw_plan.get(
                        "source_paths",
                        [],
                    )
                ),
                source_artifact_ids=(
                    source_artifact_ids
                ),
                implementation_required=bool(
                    raw_plan.get(
                        "implementation_required",
                        True,
                    )
                ),
                ready=ready,
                blockers=tuple(
                    dict.fromkeys(
                        blockers
                    )
                ),
            )
        )

    ordinals = [
        workspace.ordinal
        for workspace in workspaces
    ]

    if ordinals != list(
        range(
            1,
            10,
        )
    ):
        raise WorkspaceError(
            "capability workspace ordinals are invalid"
        )

    return tuple(
        workspaces
    )


def build_workspace(
    *,
    plan_path: Path,
    plan: dict[str, Any],
    discovery_path: Path,
    discovery: dict[str, Any],
) -> dict[str, Any]:
    selected_runtime, artifacts = (
        compile_sources(
            discovery
        )
    )

    capability_workspaces = (
        compile_capability_workspaces(
            plan,
            artifacts,
        )
    )

    blockers: list[str] = []

    plan_state = plan.get(
        "state"
    )

    if plan_state != "planned":
        blockers.append(
            f"binding plan is not implementation-ready: {plan_state}"
        )

    blockers.extend(
        str(
            blocker
        )
        for blocker in plan.get(
            "blockers",
            [],
        )
        if str(
            blocker
        ).strip()
    )

    for artifact in artifacts.values():
        blockers.extend(
            artifact.blockers
        )

    for capability_workspace in capability_workspaces:
        blockers.extend(
            capability_workspace.blockers
        )

    blockers = list(
        dict.fromkeys(
            blockers
        )
    )

    if blockers:
        workspace_state = "blocked"
    elif capability_workspaces:
        workspace_state = "ready"
    else:
        workspace_state = "diagnostic"

    class_counts = Counter(
        artifact.artifact_class
        for artifact in artifacts.values()
    )

    capability_counts = Counter(
        capability
        for artifact in artifacts.values()
        for capability in artifact.capabilities
    )

    workspace: dict[str, Any] = {
        "$schema": WORKSPACE_SCHEMA,
        "workspace_id": None,
        "compiler": {
            "id": COMPILER_ID,
            "version": COMPILER_VERSION,
        },
        "state": workspace_state,
        "task": plan.get(
            "task"
        ),
        "selected_runtime": str(
            selected_runtime
        ),
        "plan": {
            "id": plan.get(
                "plan_id"
            ),
            "path": str(
                plan_path
            ),
            "semantic_digest": plan.get(
                "semantic_digest"
            ),
            "state": plan_state,
        },
        "discovery": {
            "path": str(
                discovery_path
            ),
            "semantic_digest": discovery.get(
                "semantic_digest"
            ),
        },
        "source_classes": list(
            SOURCE_CLASSES
        ),
        "capabilities": list(
            CAPABILITIES
        ),
        "implementation_phases": list(
            IMPLEMENTATION_PHASES
        ),
        "validation_phases": list(
            VALIDATION_PHASES
        ),
        "source_artifact_count": len(
            artifacts
        ),
        "source_artifact_class_counts": {
            source_class: class_counts[
                source_class
            ]
            for source_class in SOURCE_CLASSES
        },
        "capability_source_counts": {
            capability: capability_counts[
                capability
            ]
            for capability in CAPABILITIES
        },
        "source_artifacts": {
            artifact_id: asdict(
                artifact
            )
            for artifact_id, artifact
            in sorted(
                artifacts.items()
            )
        },
        "capability_workspaces": [
            asdict(
                workspace
            )
            for workspace
            in capability_workspaces
        ],
        "implementation_contract": {
            "baseline_is_mandatory": True,
            "extend_selected_runtime_only": True,
            "parallel_runtime_forbidden": True,
            "reuse_existing_primitives_first": True,
            "complete_files_required": True,
            "atomic_writes_required": True,
            "rollback_required": True,
            "integrated_validation_required": True,
            "implementation_authority_required": True,
        },
        "blockers": blockers,
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
                        plan_path
                    ),
                    "sha256": sha256_bytes(
                        plan_path.read_bytes()
                    ),
                },
                {
                    "path": str(
                        discovery_path
                    ),
                    "sha256": sha256_bytes(
                        discovery_path.read_bytes()
                    ),
                },
            ],
            "generated_by": (
                f"{COMPILER_ID}@"
                f"{COMPILER_VERSION}"
            ),
            "transformations": [
                "load_verified_binding_plan",
                "load_verified_binding_discovery",
                "resolve_selected_runtime",
                "verify_current_source_digests",
                "map_sources_to_capabilities",
                "compile_nine_capability_workspaces",
                "compile_nine_implementation_phases",
                "compile_nine_validation_phases",
                "withhold_implementation_authority",
            ],
        },
    }

    workspace_id = (
        "masterplan-opus-binding-workspace:"
        + semantic_digest(
            {
                key: value
                for key, value
                in workspace.items()
                if key != "workspace_id"
            }
        )[:24]
    )

    workspace[
        "workspace_id"
    ] = workspace_id

    workspace[
        "semantic_digest"
    ] = semantic_digest(
        {
            key: value
            for key, value
            in workspace.items()
            if key != "semantic_digest"
        }
    )

    return workspace


def verify_workspace(
    workspace: dict[str, Any],
) -> None:
    if workspace.get(
        "$schema"
    ) != WORKSPACE_SCHEMA:
        raise WorkspaceError(
            "workspace schema mismatch"
        )

    if workspace.get(
        "state"
    ) not in WORKSPACE_STATES:
        raise WorkspaceError(
            "workspace state is invalid"
        )

    for collection, name in (
        (
            SOURCE_CLASSES,
            "source classes",
        ),
        (
            CAPABILITIES,
            "capabilities",
        ),
        (
            IMPLEMENTATION_PHASES,
            "implementation phases",
        ),
        (
            VALIDATION_PHASES,
            "validation phases",
        ),
    ):
        if len(
            collection
        ) != 9:
            raise WorkspaceError(
                f"{name} cardinality must equal nine"
            )

        if len(
            set(
                collection
            )
        ) != 9:
            raise WorkspaceError(
                f"{name} must be unique"
            )

    capability_workspaces = workspace.get(
        "capability_workspaces"
    )

    if not isinstance(
        capability_workspaces,
        list,
    ) or len(
        capability_workspaces
    ) != 9:
        raise WorkspaceError(
            "workspace must contain nine capability workspaces"
        )

    authority = workspace.get(
        "authority"
    )

    if not isinstance(
        authority,
        dict,
    ):
        raise WorkspaceError(
            "workspace lacks authority boundary"
        )

    if authority.get(
        "effect"
    ) != "none":
        raise WorkspaceError(
            "workspace may not alter authority"
        )

    if authority.get(
        "implementation_authorized"
    ) is not False:
        raise WorkspaceError(
            "workspace prematurely authorizes implementation"
        )

    recorded_digest = workspace.get(
        "semantic_digest"
    )

    if not isinstance(
        recorded_digest,
        str,
    ):
        raise WorkspaceError(
            "workspace lacks semantic digest"
        )

    calculated_digest = semantic_digest(
        {
            key: value
            for key, value
            in workspace.items()
            if key != "semantic_digest"
        }
    )

    if calculated_digest != recorded_digest:
        raise WorkspaceError(
            "workspace semantic digest mismatch"
        )


def write_workspace(
    workspace: dict[str, Any],
) -> dict[str, Any]:
    timestamp = utc_timestamp()

    runtime_root = (
        WORKSPACE_ROOT
        / timestamp
    )

    report_run_root = (
        REPORT_ROOT
        / timestamp
    )

    workspace_path = (
        runtime_root
        / "workspace.json"
    )

    manifest_path = (
        runtime_root
        / "manifest.json"
    )

    report_path = (
        report_run_root
        / "report.json"
    )

    report_manifest_path = (
        report_run_root
        / "manifest.json"
    )

    latest_path = (
        REPORT_ROOT
        / "latest.json"
    )

    atomic_write(
        workspace_path,
        pretty_json_bytes(
            workspace
        ),
    )

    manifest = {
        "$schema": (
            "savant://niche/masterplan/"
            "opus-binding-workspace-manifest/1.0.0"
        ),
        "workspace_id": workspace[
            "workspace_id"
        ],
        "entries": [
            {
                "path": str(
                    workspace_path
                ),
                "sha256": sha256_bytes(
                    workspace_path.read_bytes()
                ),
                "size": (
                    workspace_path.stat().st_size
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

    report = {
        "$schema": (
            "savant://niche/masterplan/"
            "opus-binding-workspace-report/1.0.0"
        ),
        "operation": (
            "compile_masterplan_opus_binding_workspace"
        ),
        "passed": (
            workspace[
                "state"
            ]
            == "ready"
        ),
        "workspace_id": workspace[
            "workspace_id"
        ],
        "state": workspace[
            "state"
        ],
        "task_id": (
            workspace.get(
                "task",
                {}
            ).get(
                "id"
            )
            if isinstance(
                workspace.get(
                    "task"
                ),
                dict,
            )
            else None
        ),
        "selected_runtime": workspace[
            "selected_runtime"
        ],
        "source_artifact_count": workspace[
            "source_artifact_count"
        ],
        "blocker_count": len(
            workspace[
                "blockers"
            ]
        ),
        "workspace": str(
            workspace_path
        ),
        "workspace_manifest": str(
            manifest_path
        ),
        "authority_effect": "none",
        "implementation_authorized": False,
        "provider_execution_authorized": False,
        "implementation_mutation_performed": False,
        "generated_at": timestamp,
    }

    atomic_write(
        report_path,
        pretty_json_bytes(
            report
        ),
    )

    report_manifest = {
        "$schema": (
            "savant://niche/masterplan/"
            "opus-binding-workspace-report-manifest/1.0.0"
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
        "workspace_id": workspace[
            "workspace_id"
        ],
        "semantic_digest": workspace[
            "semantic_digest"
        ],
        "state": workspace[
            "state"
        ],
        "task_id": report[
            "task_id"
        ],
        "selected_runtime": workspace[
            "selected_runtime"
        ],
        "source_artifact_count": workspace[
            "source_artifact_count"
        ],
        "blocker_count": report[
            "blocker_count"
        ],
        "workspace": str(
            workspace_path
        ),
        "workspace_manifest": str(
            manifest_path
        ),
        "report": str(
            report_path
        ),
        "report_manifest": str(
            report_manifest_path
        ),
        "authority_effect": "none",
        "implementation_authorized": False,
        "provider_execution_authorized": False,
        "implementation_mutation_performed": False,
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
        raise WorkspaceError(
            "manifest entries must be an array"
        )

    for entry in entries:
        if not isinstance(
            entry,
            dict,
        ):
            raise WorkspaceError(
                "manifest entry must be an object"
            )

        artifact_path = confined_path(
            entry.get(
                "path"
            ),
            "manifest artifact",
        )

        if not artifact_path.is_file():
            raise WorkspaceError(
                f"manifest file missing: {artifact_path}"
            )

        content = artifact_path.read_bytes()

        if entry.get(
            "sha256"
        ) != sha256_bytes(
            content
        ):
            raise WorkspaceError(
                f"manifest digest mismatch: {artifact_path}"
            )

        if entry.get(
            "size"
        ) != len(
            content
        ):
            raise WorkspaceError(
                f"manifest size mismatch: {artifact_path}"
            )

    return len(
        entries
    )


def run_compile() -> dict[str, Any]:
    plan_path, plan = resolve_plan()

    discovery_path, discovery = (
        resolve_discovery()
    )

    workspace = build_workspace(
        plan_path=plan_path,
        plan=plan,
        discovery_path=discovery_path,
        discovery=discovery,
    )

    verify_workspace(
        workspace
    )

    latest = write_workspace(
        workspace
    )

    return {
        "operation": (
            "compile_masterplan_opus_binding_workspace"
        ),
        "passed": (
            workspace[
                "state"
            ]
            == "ready"
        ),
        "state": workspace[
            "state"
        ],
        "workspace_id": workspace[
            "workspace_id"
        ],
        "task_id": latest[
            "task_id"
        ],
        "selected_runtime": latest[
            "selected_runtime"
        ],
        "source_artifact_count": latest[
            "source_artifact_count"
        ],
        "blocker_count": latest[
            "blocker_count"
        ],
        "authority_effect": "none",
        "implementation_authorized": False,
        "provider_execution_authorized": False,
        "implementation_mutation_performed": False,
        "latest": str(
            REPORT_ROOT
            / "latest.json"
        ),
    }


def run_verify() -> dict[str, Any]:
    latest = load_json(
        REPORT_ROOT
        / "latest.json"
    )

    workspace_path = confined_path(
        latest.get(
            "workspace"
        ),
        "binding workspace",
    )

    workspace_manifest_path = confined_path(
        latest.get(
            "workspace_manifest"
        ),
        "binding workspace manifest",
    )

    report_manifest_path = confined_path(
        latest.get(
            "report_manifest"
        ),
        "binding workspace report manifest",
    )

    workspace = load_json(
        workspace_path
    )

    verify_workspace(
        workspace
    )

    workspace_manifest_count = (
        verify_manifest(
            workspace_manifest_path
        )
    )

    report_manifest_count = (
        verify_manifest(
            report_manifest_path
        )
    )

    return {
        "operation": (
            "verify_masterplan_opus_binding_workspace"
        ),
        "passed": True,
        "workspace_state": workspace[
            "state"
        ],
        "workspace_id": workspace[
            "workspace_id"
        ],
        "task_id": (
            workspace.get(
                "task",
                {}
            ).get(
                "id"
            )
            if isinstance(
                workspace.get(
                    "task"
                ),
                dict,
            )
            else None
        ),
        "selected_runtime": workspace[
            "selected_runtime"
        ],
        "source_artifact_count": workspace[
            "source_artifact_count"
        ],
        "blocker_count": len(
            workspace[
                "blockers"
            ]
        ),
        "workspace_manifest_entry_count": (
            workspace_manifest_count
        ),
        "report_manifest_entry_count": (
            report_manifest_count
        ),
        "authority_effect": "none",
        "implementation_authorized": False,
        "provider_execution_authorized": False,
        "implementation_mutation_performed": False,
    }


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Compile or verify the Masterplan-to-Opus "
            "binding implementation workspace."
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
        WorkspaceError,
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
                    "implementation_mutation_performed": False,
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
