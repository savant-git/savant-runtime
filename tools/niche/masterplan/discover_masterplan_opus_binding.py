#!/usr/bin/env python3
"""
Discover the current authoritative Opus runtime before binding Masterplan to it.

This tool performs read-only implementation discovery.

It searches the current Savant runtime for existing Opus primitives relevant to
Masterplan work execution:

- runtime request protocols
- provider adapters
- provider registries
- route registries
- orchestration policies
- routers
- workers
- event buses
- queue consumers
- response contracts
- lineage and provenance facilities
- evidence-admission integration points

It does not:

- create a parallel Opus implementation
- choose historical implementation over current implementation
- call providers
- modify authority
- modify Masterplan
- modify Opus
- mutate implementation
- infer that filesystem presence establishes authority

The resulting binding report is evidence for the next implementation stage.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
import tempfile
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Final, Iterator


ROOT: Final[Path] = Path(
    "/root/savant-runtime"
).resolve()

REPORT_ROOT: Final[Path] = (
    ROOT
    / "reports"
    / "niche"
    / "masterplan"
    / "opus-binding-discovery"
)

DISCOVERY_SCHEMA: Final[str] = (
    "savant://niche/masterplan/"
    "opus-binding-discovery/1.0.0"
)

DISCOVERY_ROOTS: Final[
    tuple[Path, ...]
] = (
    ROOT
    / "hierarchies"
    / "identity"
    / "exiles"
    / "opus",
    ROOT
    / "ontology"
    / "obelisks"
    / "_template"
    / "segue"
    / "gates"
    / "_template"
    / "segue"
    / "innates"
    / "_template"
    / "segue"
    / "exiles"
    / "opus",
    ROOT
    / "ontology"
    / "obelisks"
    / "segue"
    / "gates"
    / "segue"
    / "innates"
    / "segue"
    / "exiles"
    / "opus",
    ROOT
    / "exiles"
    / "opus",
)

TEXT_SUFFIXES: Final[
    frozenset[str]
] = frozenset(
    {
        ".json",
        ".jsonl",
        ".md",
        ".py",
        ".sh",
        ".toml",
        ".txt",
        ".yaml",
        ".yml",
    }
)

EXCLUDED_DIRECTORIES: Final[
    frozenset[str]
] = frozenset(
    {
        ".git",
        ".hg",
        ".mypy_cache",
        ".pytest_cache",
        ".ruff_cache",
        ".svn",
        ".tox",
        ".venv",
        "__pycache__",
        "node_modules",
        "site-packages",
        "venv",
    }
)

ARTIFACT_CLASSES: Final[
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

BINDING_CAPABILITIES: Final[
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

AUTHORITY_MARKERS: Final[
    tuple[str, ...]
] = (
    "accepted",
    "authoritative",
    "authority",
    "canon",
    "constitutional",
    "current_user_directive",
    "project-owner",
    "project_owner",
    "source_of_truth",
)

HISTORICAL_MARKERS: Final[
    tuple[str, ...]
] = (
    "_template",
    "archive",
    "backup",
    "deprecated",
    "history",
    "historical",
    "legacy",
    "retired",
    "superseded",
)

MAX_TEXT_BYTES: Final[int] = (
    4_000_000
)


class DiscoveryError(RuntimeError):
    """Raised when current Opus discovery cannot complete reliably."""


@dataclass(frozen=True, slots=True)
class CandidateRoot:
    path: str
    exists: bool
    file_count: int
    authority_score: int
    historical_score: int
    implementation_score: int
    ranking_score: int
    classification: str
    evidence: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class Artifact:
    path: str
    relative_path: str
    suffix: str
    size: int
    sha256: str
    artifact_class: str
    authority_score: int
    historical_score: int
    symbols: tuple[str, ...]
    imports: tuple[str, ...]
    capabilities: tuple[str, ...]
    evidence: tuple[str, ...]


def utc_timestamp() -> str:
    return datetime.now(
        timezone.utc
    ).strftime(
        "%Y%m%dT%H%M%SZ"
    )


def sha256_bytes(
    value: bytes,
) -> str:
    return hashlib.sha256(
        value
    ).hexdigest()


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


def confined_path(
    path: Path,
) -> Path:
    resolved = path.resolve(
        strict=False
    )

    try:
        resolved.relative_to(
            ROOT
        )
    except ValueError as error:
        raise DiscoveryError(
            f"path escapes runtime root: {resolved}"
        ) from error

    return resolved


def iter_files(
    root: Path,
) -> Iterator[Path]:
    if not root.is_dir():
        return

    for raw_root, directories, files in os.walk(
        root,
        topdown=True,
        followlinks=False,
    ):
        directories[:] = sorted(
            directory
            for directory in directories
            if directory
            not in EXCLUDED_DIRECTORIES
        )

        current_root = Path(
            raw_root
        )

        for file_name in sorted(
            files
        ):
            path = current_root / file_name

            if (
                path.suffix.casefold()
                not in TEXT_SUFFIXES
            ):
                continue

            try:
                size = path.stat().st_size
            except OSError:
                continue

            if size > MAX_TEXT_BYTES:
                continue

            yield path


def read_text(
    path: Path,
) -> str | None:
    try:
        raw = path.read_bytes()
    except OSError:
        return None

    if len(
        raw
    ) > MAX_TEXT_BYTES:
        return None

    if b"\x00" in raw:
        return None

    try:
        return raw.decode(
            "utf-8"
        )
    except UnicodeDecodeError:
        return None


def marker_score(
    value: str,
    markers: tuple[str, ...],
) -> int:
    normalized = value.casefold()

    return sum(
        1
        for marker in markers
        if marker.casefold()
        in normalized
    )


def classify_artifact(
    path: Path,
    text: str,
) -> str:
    normalized_path = (
        path.as_posix().casefold()
    )

    normalized_text = text.casefold()

    if any(
        marker in normalized_path
        for marker in (
            "/authority/",
            "/canon/",
            "constitution",
        )
    ):
        return "authority"

    if any(
        marker in normalized_path
        for marker in (
            "/protocol/",
            "contract",
            "schema",
        )
    ):
        return "protocol"

    if any(
        marker in normalized_path
        for marker in (
            "/providers/",
            "/provider/",
            "provider_",
        )
    ):
        return "provider"

    if any(
        marker in normalized_path
        for marker in (
            "/registry/",
            "/registries/",
        )
    ):
        return "registry"

    if any(
        marker in normalized_path
        for marker in (
            "router",
            "/routes/",
            "/routing/",
        )
    ):
        return "router"

    if any(
        marker in normalized_path
        for marker in (
            "/workers/",
            "worker",
            "executor",
            "consumer",
        )
    ):
        return "worker"

    if any(
        marker in normalized_path
        for marker in (
            "/events/",
            "event_bus",
            "eventbus",
        )
    ):
        return "event"

    if any(
        marker in normalized_path
        for marker in (
            "/lineage/",
            "provenance",
            "receipt",
        )
    ):
        return "lineage"

    if any(
        marker in normalized_path
        for marker in (
            "evidence",
            "admission",
            "attestation",
        )
    ):
        return "evidence"

    if "provider" in normalized_text:
        return "provider"

    return "registry"


def python_symbols(
    path: Path,
    text: str,
) -> tuple[
    tuple[str, ...],
    tuple[str, ...],
]:
    if path.suffix.casefold() != ".py":
        return (), ()

    try:
        tree = ast.parse(
            text,
            filename=str(
                path
            ),
        )
    except SyntaxError:
        return (), ()

    symbols: set[str] = set()
    imports: set[str] = set()

    for node in ast.walk(
        tree
    ):
        if isinstance(
            node,
            (
                ast.AsyncFunctionDef,
                ast.ClassDef,
                ast.FunctionDef,
            ),
        ):
            symbols.add(
                node.name
            )

        elif isinstance(
            node,
            ast.Import,
        ):
            for alias in node.names:
                imports.add(
                    alias.name
                )

        elif isinstance(
            node,
            ast.ImportFrom,
        ):
            if node.module:
                imports.add(
                    node.module
                )

    return (
        tuple(
            sorted(
                symbols
            )
        ),
        tuple(
            sorted(
                imports
            )
        ),
    )


def detect_capabilities(
    path: Path,
    text: str,
    symbols: tuple[str, ...],
) -> tuple[
    tuple[str, ...],
    tuple[str, ...],
]:
    normalized = (
        path.as_posix()
        + "\n"
        + text
        + "\n"
        + "\n".join(
            symbols
        )
    ).casefold()

    capabilities: set[str] = set()
    evidence: list[str] = []

    patterns: dict[
        str,
        tuple[str, ...],
    ] = {
        "request_creation": (
            "make_request",
            "create_request",
            "build_request",
            "runtime_request",
            "request_id",
        ),
        "request_validation": (
            "validate_request",
            "request_schema",
            "request contract",
            "request_contract",
        ),
        "provider_discovery": (
            "select_provider",
            "provider registry",
            "provider_registry",
            "available()",
            "fallback_order",
        ),
        "provider_routing": (
            "route(",
            "router",
            "routing_policy",
            "route_id",
        ),
        "provider_execution": (
            "execute_provider",
            "providers.call",
            "provider.call",
            "synthesize(",
            "asyncio.gather",
        ),
        "response_validation": (
            "validate_response",
            "response_schema",
            "response contract",
            "response_contract",
        ),
        "event_publication": (
            "publish(",
            "event_bus",
            "eventbus",
            "emit(",
        ),
        "lineage_capture": (
            "lineage",
            "provenance",
            "source_hash",
            "semantic_digest",
        ),
        "evidence_handoff": (
            "evidence",
            "admit_",
            "attestation",
            "masterplan-evidence",
        ),
    }

    for capability, markers in patterns.items():
        matched = [
            marker
            for marker in markers
            if marker.casefold()
            in normalized
        ]

        if matched:
            capabilities.add(
                capability
            )

            evidence.append(
                f"{capability}: "
                + ", ".join(
                    sorted(
                        matched
                    )
                )
            )

    return (
        tuple(
            sorted(
                capabilities
            )
        ),
        tuple(
            evidence
        ),
    )


def inspect_artifact(
    root: Path,
    path: Path,
) -> Artifact | None:
    text = read_text(
        path
    )

    if text is None:
        return None

    raw = path.read_bytes()

    relative_path = (
        path.relative_to(
            root
        ).as_posix()
    )

    symbols, imports = python_symbols(
        path,
        text,
    )

    capabilities, capability_evidence = (
        detect_capabilities(
            path,
            text,
            symbols,
        )
    )

    authority_score = marker_score(
        path.as_posix()
        + "\n"
        + text,
        AUTHORITY_MARKERS,
    )

    historical_score = marker_score(
        path.as_posix()
        + "\n"
        + text,
        HISTORICAL_MARKERS,
    )

    evidence = [
        *capability_evidence,
    ]

    if authority_score:
        evidence.append(
            "authority markers: "
            f"{authority_score}"
        )

    if historical_score:
        evidence.append(
            "historical markers: "
            f"{historical_score}"
        )

    return Artifact(
        path=str(
            path
        ),
        relative_path=relative_path,
        suffix=path.suffix.casefold(),
        size=len(
            raw
        ),
        sha256=sha256_bytes(
            raw
        ),
        artifact_class=classify_artifact(
            path,
            text,
        ),
        authority_score=authority_score,
        historical_score=historical_score,
        symbols=symbols,
        imports=imports,
        capabilities=capabilities,
        evidence=tuple(
            evidence
        ),
    )


def inspect_root(
    root: Path,
) -> tuple[
    CandidateRoot,
    tuple[Artifact, ...],
]:
    root = confined_path(
        root
    )

    artifacts = tuple(
        artifact
        for artifact in (
            inspect_artifact(
                root,
                path,
            )
            for path in iter_files(
                root
            )
        )
        if artifact is not None
    )

    authority_score = sum(
        artifact.authority_score
        for artifact in artifacts
    )

    historical_score = sum(
        artifact.historical_score
        for artifact in artifacts
    )

    capabilities = {
        capability
        for artifact in artifacts
        for capability
        in artifact.capabilities
    }

    implementation_score = (
        len(
            artifacts
        )
        + (
            5
            * len(
                capabilities
            )
        )
    )

    ranking_score = (
        implementation_score
        + (
            3
            * authority_score
        )
        - (
            4
            * historical_score
        )
    )

    evidence: list[str] = []

    if root.is_dir():
        evidence.append(
            f"text artifacts: {len(artifacts)}"
        )

        evidence.append(
            "capabilities: "
            + (
                ", ".join(
                    sorted(
                        capabilities
                    )
                )
                if capabilities
                else "none"
            )
        )

    if authority_score:
        evidence.append(
            f"authority score: {authority_score}"
        )

    if historical_score:
        evidence.append(
            f"historical score: {historical_score}"
        )

    if not root.exists():
        classification = "missing"

    elif historical_score > (
        authority_score
        + implementation_score
    ):
        classification = "historical"

    elif (
        len(
            capabilities
        )
        == len(
            BINDING_CAPABILITIES
        )
    ):
        classification = "complete_candidate"

    elif capabilities:
        classification = "partial_candidate"

    else:
        classification = "unresolved"

    candidate = CandidateRoot(
        path=str(
            root
        ),
        exists=root.is_dir(),
        file_count=len(
            artifacts
        ),
        authority_score=authority_score,
        historical_score=historical_score,
        implementation_score=(
            implementation_score
        ),
        ranking_score=ranking_score,
        classification=classification,
        evidence=tuple(
            evidence
        ),
    )

    return candidate, artifacts


def select_candidate(
    candidates: tuple[
        CandidateRoot,
        ...,
    ],
) -> CandidateRoot | None:
    eligible = [
        candidate
        for candidate in candidates
        if candidate.exists
        and candidate.classification
        not in {
            "historical",
            "missing",
        }
    ]

    if not eligible:
        return None

    ranked = sorted(
        eligible,
        key=lambda candidate: (
            candidate.ranking_score,
            candidate.authority_score,
            candidate.implementation_score,
            candidate.path,
        ),
        reverse=True,
    )

    if (
        len(
            ranked
        )
        > 1
        and ranked[0].ranking_score
        == ranked[1].ranking_score
    ):
        return None

    return ranked[0]


def capability_matrix(
    artifacts: tuple[
        Artifact,
        ...,
    ],
) -> dict[str, list[str]]:
    matrix = {
        capability: []
        for capability
        in BINDING_CAPABILITIES
    }

    for artifact in artifacts:
        for capability in artifact.capabilities:
            matrix[
                capability
            ].append(
                artifact.path
            )

    return {
        capability: sorted(
            set(
                paths
            )
        )
        for capability, paths
        in matrix.items()
    }


def build_discovery() -> dict[str, Any]:
    candidate_results = tuple(
        inspect_root(
            root
        )
        for root in DISCOVERY_ROOTS
    )

    candidates = tuple(
        candidate
        for candidate, _
        in candidate_results
    )

    selected = select_candidate(
        candidates
    )

    selected_artifacts: tuple[
        Artifact,
        ...,
    ] = ()

    if selected is not None:
        selected_artifacts = next(
            artifacts
            for candidate, artifacts
            in candidate_results
            if candidate.path
            == selected.path
        )

    matrix = capability_matrix(
        selected_artifacts
    )

    missing_capabilities = [
        capability
        for capability, paths
        in matrix.items()
        if not paths
    ]

    class_counts = Counter(
        artifact.artifact_class
        for artifact
        in selected_artifacts
    )

    discovery: dict[str, Any] = {
        "$schema": DISCOVERY_SCHEMA,
        "operation": (
            "discover_masterplan_opus_binding"
        ),
        "passed": (
            selected is not None
        ),
        "authority_effect": "none",
        "provider_calls_performed": False,
        "implementation_mutation_performed": False,
        "candidate_count": len(
            candidates
        ),
        "candidates": [
            asdict(
                candidate
            )
            for candidate
            in candidates
        ],
        "selected_candidate": (
            asdict(
                selected
            )
            if selected is not None
            else None
        ),
        "selection_state": (
            "selected"
            if selected is not None
            else "authority_required"
        ),
        "selection_rule": (
            "Choose the highest-ranked nonhistorical current "
            "implementation candidate only when the ranking is unique."
        ),
        "artifact_classes": list(
            ARTIFACT_CLASSES
        ),
        "binding_capabilities": list(
            BINDING_CAPABILITIES
        ),
        "capability_matrix": matrix,
        "missing_capabilities": (
            missing_capabilities
        ),
        "selected_artifact_count": len(
            selected_artifacts
        ),
        "selected_artifact_class_counts": {
            artifact_class: class_counts[
                artifact_class
            ]
            for artifact_class
            in ARTIFACT_CLASSES
        },
        "selected_artifacts": [
            asdict(
                artifact
            )
            for artifact
            in selected_artifacts
        ],
        "binding_readiness": {
            "current_runtime_uniquely_selected": (
                selected is not None
            ),
            "all_capabilities_present": (
                not missing_capabilities
            ),
            "direct_binding_authorized": False,
            "next_stage": (
                "compile_binding_plan"
                if (
                    selected is not None
                    and not missing_capabilities
                )
                else "resolve_missing_capabilities"
            ),
        },
        "unknowns": [
            (
                "Filesystem presence does not independently "
                "establish accepted authority."
            ),
            (
                "No provider API call contract is assumed "
                "until selected artifacts are inspected."
            ),
            (
                "No Masterplan-to-Opus adapter is authorized "
                "by this discovery report."
            ),
        ],
    }

    discovery[
        "semantic_digest"
    ] = semantic_digest(
        {
            key: value
            for key, value
            in discovery.items()
            if key != "semantic_digest"
        }
    )

    return discovery


def verify_discovery(
    discovery: dict[str, Any],
) -> None:
    if discovery.get(
        "$schema"
    ) != DISCOVERY_SCHEMA:
        raise DiscoveryError(
            "discovery schema mismatch"
        )

    artifact_classes = discovery.get(
        "artifact_classes"
    )

    if tuple(
        artifact_classes
        if isinstance(
            artifact_classes,
            list,
        )
        else ()
    ) != ARTIFACT_CLASSES:
        raise DiscoveryError(
            "artifact classes differ from authority"
        )

    capabilities = discovery.get(
        "binding_capabilities"
    )

    if tuple(
        capabilities
        if isinstance(
            capabilities,
            list,
        )
        else ()
    ) != BINDING_CAPABILITIES:
        raise DiscoveryError(
            "binding capabilities differ from authority"
        )

    if len(
        ARTIFACT_CLASSES
    ) != 9:
        raise DiscoveryError(
            "artifact class cardinality must equal nine"
        )

    if len(
        BINDING_CAPABILITIES
    ) != 9:
        raise DiscoveryError(
            "binding capability cardinality must equal nine"
        )

    if discovery.get(
        "authority_effect"
    ) != "none":
        raise DiscoveryError(
            "discovery may not alter authority"
        )

    recorded_digest = discovery.get(
        "semantic_digest"
    )

    if not isinstance(
        recorded_digest,
        str,
    ):
        raise DiscoveryError(
            "discovery lacks semantic digest"
        )

    calculated_digest = semantic_digest(
        {
            key: value
            for key, value
            in discovery.items()
            if key != "semantic_digest"
        }
    )

    if calculated_digest != recorded_digest:
        raise DiscoveryError(
            "discovery semantic digest mismatch"
        )


def write_discovery(
    discovery: dict[str, Any],
) -> dict[str, Any]:
    timestamp = utc_timestamp()

    run_root = (
        REPORT_ROOT
        / timestamp
    )

    report_path = (
        run_root
        / "report.json"
    )

    manifest_path = (
        run_root
        / "manifest.json"
    )

    latest_path = (
        REPORT_ROOT
        / "latest.json"
    )

    atomic_write(
        report_path,
        pretty_json_bytes(
            discovery
        ),
    )

    manifest = {
        "$schema": (
            "savant://niche/masterplan/"
            "opus-binding-discovery-manifest/1.0.0"
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
        manifest_path,
        pretty_json_bytes(
            manifest
        ),
    )

    latest = {
        "operation": (
            "discover_masterplan_opus_binding"
        ),
        "passed": discovery[
            "passed"
        ],
        "report": str(
            report_path
        ),
        "manifest": str(
            manifest_path
        ),
        "selection_state": discovery[
            "selection_state"
        ],
        "selected_candidate": (
            discovery[
                "selected_candidate"
            ][
                "path"
            ]
            if discovery[
                "selected_candidate"
            ]
            is not None
            else None
        ),
        "missing_capability_count": len(
            discovery[
                "missing_capabilities"
            ]
        ),
        "semantic_digest": discovery[
            "semantic_digest"
        ],
        "authority_effect": "none",
        "provider_calls_performed": False,
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
    path: Path,
) -> int:
    manifest = json.loads(
        path.read_text(
            encoding="utf-8"
        )
    )

    entries = manifest.get(
        "entries"
    )

    if not isinstance(
        entries,
        list,
    ):
        raise DiscoveryError(
            "manifest entries must be an array"
        )

    for entry in entries:
        if not isinstance(
            entry,
            dict,
        ):
            raise DiscoveryError(
                "manifest entry must be an object"
            )

        raw_path = entry.get(
            "path"
        )

        expected_digest = entry.get(
            "sha256"
        )

        expected_size = entry.get(
            "size"
        )

        if not isinstance(
            raw_path,
            str,
        ):
            raise DiscoveryError(
                "manifest entry lacks path"
            )

        artifact_path = confined_path(
            Path(
                raw_path
            )
        )

        if not artifact_path.is_file():
            raise DiscoveryError(
                f"manifest file missing: {artifact_path}"
            )

        content = artifact_path.read_bytes()

        if expected_digest != sha256_bytes(
            content
        ):
            raise DiscoveryError(
                f"manifest digest mismatch: {artifact_path}"
            )

        if expected_size != len(
            content
        ):
            raise DiscoveryError(
                f"manifest size mismatch: {artifact_path}"
            )

    return len(
        entries
    )


def run_discover() -> dict[str, Any]:
    discovery = build_discovery()

    verify_discovery(
        discovery
    )

    latest = write_discovery(
        discovery
    )

    return {
        "operation": (
            "discover_masterplan_opus_binding"
        ),
        "passed": discovery[
            "passed"
        ],
        "selection_state": discovery[
            "selection_state"
        ],
        "selected_candidate": latest[
            "selected_candidate"
        ],
        "missing_capability_count": latest[
            "missing_capability_count"
        ],
        "authority_effect": "none",
        "provider_calls_performed": False,
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

    latest = json.loads(
        latest_path.read_text(
            encoding="utf-8"
        )
    )

    report_path = confined_path(
        Path(
            str(
                latest[
                    "report"
                ]
            )
        )
    )

    manifest_path = confined_path(
        Path(
            str(
                latest[
                    "manifest"
                ]
            )
        )
    )

    discovery = json.loads(
        report_path.read_text(
            encoding="utf-8"
        )
    )

    verify_discovery(
        discovery
    )

    manifest_entry_count = verify_manifest(
        manifest_path
    )

    return {
        "operation": (
            "verify_masterplan_opus_binding_discovery"
        ),
        "passed": True,
        "discovery_passed": discovery[
            "passed"
        ],
        "selection_state": discovery[
            "selection_state"
        ],
        "selected_candidate": (
            discovery[
                "selected_candidate"
            ][
                "path"
            ]
            if discovery[
                "selected_candidate"
            ]
            is not None
            else None
        ),
        "missing_capability_count": len(
            discovery[
                "missing_capabilities"
            ]
        ),
        "manifest_entry_count": (
            manifest_entry_count
        ),
        "authority_effect": "none",
        "provider_calls_performed": False,
        "implementation_mutation_performed": False,
    }


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Discover or verify the current Opus "
            "implementation for Masterplan binding."
        )
    )

    parser.add_argument(
        "operation",
        choices=(
            "discover",
            "verify",
        ),
    )

    return parser.parse_args()


def main() -> int:
    arguments = parse_arguments()

    try:
        if arguments.operation == "discover":
            result = run_discover()
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
        DiscoveryError,
        KeyError,
        OSError,
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
                    "provider_calls_performed": False,
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
