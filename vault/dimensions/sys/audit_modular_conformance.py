#!/usr/bin/env python3
"""
Savant modular-conformance auditor.

Bounded, read-only, authority-surface implementation.

Audits:

1. Shade / reusable identity
2. Composition and reference reuse
3. Rut / Sidecar capability attachment
4. Mood and two-Mood fusion conformance
5. Nine-Tidal reusable family conformance

This validator intentionally does NOT crawl the complete Savant filesystem.

That behavior would violate the Primary Architectural Law's minimum runtime,
validation, storage, and cognitive footprint requirements.

Filesystem presence is evidence, not authority.
No mutation is performed.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys

from collections import Counter
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from itertools import combinations
from pathlib import Path
from typing import Any, Final, Iterator, Mapping


ROOT: Final[Path] = Path(
    "/root/savant-runtime"
)

SYS_ROOT: Final[Path] = (
    ROOT
    / "vault"
    / "dimensions"
    / "sys"
)

REPORT_ROOT: Final[Path] = (
    SYS_ROOT
    / "reports"
    / "modular-conformance"
)

PRIMARY_LAW: Final[Path] = (
    ROOT
    / "ontology"
    / "obelisks"
    / "segue"
    / "authority_graph"
    / "canon"
    / "PRIMARY_ARCHITECTURAL_LAW.md"
)

PROJECT_INSTRUCTIONS: Final[Path] = (
    ROOT
    / "vault"
    / "dimensions"
    / "canon"
    / "PROJECT_INSTRUCTIONS.md"
)

MOOD_REGISTRY: Final[Path] = (
    ROOT
    / "authority_graph"
    / "registries"
    / "modular_moods.json"
)

RUT_REGISTRY: Final[Path] = (
    ROOT
    / "authority_graph"
    / "registries"
    / "attachment_slots.json"
)

SHADE_ROOT: Final[Path] = (
    ROOT
    / "authority_graph"
    / "instances"
)

TIDAL_REGISTRY: Final[Path] = (
    ROOT
    / "runtime"
    / "living_substrates"
    / "registry.json"
)

TIDAL_RUNTIME_ROOT: Final[Path] = (
    ROOT
    / "runtime"
    / "living_substrates"
)

CANON_AUTHORITY_ROOT: Final[Path] = (
    ROOT
    / "canon-system"
    / "authority"
)

LEXICON_REGISTRY: Final[Path] = (
    ROOT
    / "lexicon"
    / "registry.yaml"
)

MAX_STRUCTURED_BYTES: Final[int] = (
    2 * 1024 * 1024
)

CANONICAL_MOODS: Final[tuple[str, ...]] = (
    "anima",
    "weld",
    "kiln",
    "graft",
    "aria",
    "mantle",
    "fulcrum",
    "echelon",
    "ascent",
)

CANONICAL_TIDALS: Final[tuple[str, ...]] = (
    "scyon",
    "splyce",
    "scrybe",
    "pryme",
    "cyphor",
    "thryce",
    "spyral",
    "lythe",
    "dryve",
)

TIDAL_ALIASES: Final[dict[str, str]] = {
    "cypher": "cyphor",
}

EXPECTED_FUSIONS: Final[
    frozenset[tuple[str, str]]
] = frozenset(
    tuple(
        sorted(pair)
    )
    for pair in combinations(
        CANONICAL_MOODS,
        2,
    )
)

MOOD_KEYS: Final[frozenset[str]] = frozenset(
    {
        "mood",
        "moods",
        "mood_binding",
        "mood_bindings",
        "construction_moods",
        "active_moods",
        "inherited_moods",
    }
)

RUT_KEYS: Final[frozenset[str]] = frozenset(
    {
        "rut",
        "ruts",
        "slot",
        "slots",
        "future_slots",
    }
)

SIDECAR_KEYS: Final[frozenset[str]] = frozenset(
    {
        "sidecar",
        "sidecars",
        "attachment",
        "attachments",
    }
)

COMPOSITION_KEYS: Final[frozenset[str]] = frozenset(
    {
        "composition",
        "composed",
        "composed_instances",
        "instances",
        "members",
        "components",
    }
)

REFERENCE_PREFIXES: Final[tuple[str, ...]] = (
    "shade:",
    "instance:",
    "iota:",
    "mote:",
    "ink:",
    "quirk:",
    "prodigal:",
    "exile:",
    "innate:",
    "wyrmhole:",
    "obelisk:",
    "tidal:",
    "mood:",
    "system:",
    "service:",
)

STRUCTURED_SUFFIXES: Final[frozenset[str]] = frozenset(
    {
        ".json",
        ".yaml",
        ".yml",
    }
)

SKIP_DIRECTORY_NAMES: Final[frozenset[str]] = frozenset(
    {
        ".git",
        "__pycache__",
        "backups",
        "cache",
        "generated",
        "logs",
        "projections",
        "reports",
        "snapshots",
    }
)


class AuditError(RuntimeError):
    pass


@dataclass(
    frozen=True,
    slots=True,
)
class Finding:
    key: str
    severity: str
    domain: str
    path: str
    evidence: str
    action: str


@dataclass(
    frozen=True,
    slots=True,
)
class Surface:
    path: str
    size: int
    sha256: str


def normalize(
    value: object,
) -> str:
    return (
        str(value)
        .strip()
        .casefold()
    )


def utc_stamp() -> str:
    return datetime.now(
        timezone.utc
    ).strftime(
        "%Y%m%dT%H%M%SZ"
    )


def sha256_file(
    path: Path,
) -> str:
    digest = hashlib.sha256()

    with path.open(
        "rb"
    ) as handle:
        while True:
            block = handle.read(
                1024 * 1024
            )

            if not block:
                break

            digest.update(
                block
            )

    return digest.hexdigest()


def write_json(
    path: Path,
    value: object,
) -> None:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    temporary = path.with_name(
        f".{path.name}.tmp"
    )

    temporary.write_text(
        json.dumps(
            value,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    temporary.chmod(
        0o644
    )

    temporary.replace(
        path
    )


def read_json_object(
    path: Path,
) -> dict[str, Any]:
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
        raise AuditError(
            f"cannot load JSON {path}: {error}"
        ) from error

    if not isinstance(
        value,
        dict,
    ):
        raise AuditError(
            f"JSON root must be object: {path}"
        )

    return value


def read_structured(
    path: Path,
) -> dict[str, Any] | None:
    try:
        size = path.stat().st_size
    except OSError:
        return None

    if size > MAX_STRUCTURED_BYTES:
        return None

    suffix = path.suffix.casefold()

    if suffix not in STRUCTURED_SUFFIXES:
        return None

    try:
        text = path.read_text(
            encoding="utf-8",
            errors="strict",
        )
    except (
        OSError,
        UnicodeDecodeError,
    ):
        return None

    if suffix == ".json":
        try:
            value = json.loads(
                text
            )
        except json.JSONDecodeError:
            return None

    else:
        try:
            import yaml
        except ImportError:
            return None

        try:
            value = yaml.safe_load(
                text
            )
        except yaml.YAMLError:
            return None

    return (
        value
        if isinstance(
            value,
            dict,
        )
        else None
    )


def iter_structured_files(
    root: Path,
) -> Iterator[Path]:
    if not root.is_dir():
        return

    stack = [
        root
    ]

    while stack:
        current = stack.pop()

        try:
            children = sorted(
                current.iterdir(),
                key=lambda path: (
                    path.name
                ),
                reverse=True,
            )
        except OSError:
            continue

        for path in children:
            if path.is_symlink():
                continue

            if path.is_dir():
                if (
                    path.name
                    in SKIP_DIRECTORY_NAMES
                ):
                    continue

                stack.append(
                    path
                )

                continue

            if (
                path.is_file()
                and path.suffix.casefold()
                in STRUCTURED_SUFFIXES
            ):
                yield path


def flatten(
    value: Any,
    prefix: str = "",
) -> Iterator[
    tuple[str, Any]
]:
    if isinstance(
        value,
        Mapping,
    ):
        for key, child in value.items():
            child_path = (
                f"{prefix}.{key}"
                if prefix
                else str(key)
            )

            yield from flatten(
                child,
                child_path,
            )

        return

    if isinstance(
        value,
        list,
    ):
        for index, child in enumerate(
            value
        ):
            yield from flatten(
                child,
                f"{prefix}[{index}]",
            )

        return

    yield (
        prefix,
        value,
    )


def terminal_key(
    path: str,
) -> str:
    return (
        path
        .split(".")[-1]
        .split("[")[0]
        .casefold()
    )


def authority_findings() -> list[Finding]:
    findings: list[
        Finding
    ] = []

    for path in (
        PRIMARY_LAW,
        PROJECT_INSTRUCTIONS,
        MOOD_REGISTRY,
        RUT_REGISTRY,
    ):
        if path.is_file():
            continue

        findings.append(
            Finding(
                key="missing_authority_surface",
                severity="error",
                domain="authority",
                path=str(path),
                evidence=(
                    "required canonical modular "
                    "authority surface is missing"
                ),
                action=(
                    "Restore the accepted authority "
                    "primitive; do not create a "
                    "parallel authority."
                ),
            )
        )

    return findings


def mood_registry_findings() -> list[Finding]:
    if not MOOD_REGISTRY.is_file():
        return []

    value = read_json_object(
        MOOD_REGISTRY
    )

    findings: list[
        Finding
    ] = []

    moods = value.get(
        "moods"
    )

    if not isinstance(
        moods,
        list,
    ):
        return [
            Finding(
                key="invalid_mood_registry",
                severity="error",
                domain="mood",
                path=str(
                    MOOD_REGISTRY
                ),
                evidence=(
                    "moods must be an array"
                ),
                action=(
                    "Restore canonical Mood "
                    "registry structure."
                ),
            )
        ]

    observed = tuple(
        normalize(
            item.get(
                "key",
                "",
            )
        )
        for item in moods
        if isinstance(
            item,
            Mapping,
        )
    )

    if observed != CANONICAL_MOODS:
        findings.append(
            Finding(
                key="canonical_mood_mismatch",
                severity="error",
                domain="mood",
                path=str(
                    MOOD_REGISTRY
                ),
                evidence=(
                    f"expected={CANONICAL_MOODS!r}; "
                    f"observed={observed!r}"
                ),
                action=(
                    "Preserve exactly the nine "
                    "canonical Moods."
                ),
            )
        )

    fusions = value.get(
        "fusions"
    )

    if not isinstance(
        fusions,
        list,
    ):
        findings.append(
            Finding(
                key="missing_mood_fusions",
                severity="error",
                domain="mood",
                path=str(
                    MOOD_REGISTRY
                ),
                evidence=(
                    "fusions must be an array"
                ),
                action=(
                    "Restore the canonical "
                    "two-Mood fusion matrix."
                ),
            )
        )

        return findings

    observed_fusions: set[
        tuple[str, str]
    ] = set()

    for index, fusion in enumerate(
        fusions
    ):
        if not isinstance(
            fusion,
            Mapping,
        ):
            findings.append(
                Finding(
                    key="invalid_mood_fusion",
                    severity="error",
                    domain="mood",
                    path=str(
                        MOOD_REGISTRY
                    ),
                    evidence=(
                        f"fusion[{index}] "
                        "is not an object"
                    ),
                    action=(
                        "Every fusion must contain "
                        "two canonical Moods."
                    ),
                )
            )

            continue

        left = normalize(
            fusion.get(
                "left",
                "",
            )
        ).removeprefix(
            "mood:"
        )

        right = normalize(
            fusion.get(
                "right",
                "",
            )
        ).removeprefix(
            "mood:"
        )

        if (
            left
            not in CANONICAL_MOODS
            or right
            not in CANONICAL_MOODS
            or left == right
        ):
            findings.append(
                Finding(
                    key="invalid_mood_fusion",
                    severity="error",
                    domain="mood",
                    path=str(
                        MOOD_REGISTRY
                    ),
                    evidence=(
                        f"fusion[{index}]="
                        f"{left}+{right}"
                    ),
                    action=(
                        "Use exactly two distinct "
                        "canonical Moods."
                    ),
                )
            )

            continue

        observed_fusions.add(
            tuple(
                sorted(
                    (
                        left,
                        right,
                    )
                )
            )
        )

    missing = (
        EXPECTED_FUSIONS
        - observed_fusions
    )

    extras = (
        observed_fusions
        - EXPECTED_FUSIONS
    )

    if missing:
        findings.append(
            Finding(
                key="missing_mood_fusions",
                severity="error",
                domain="mood",
                path=str(
                    MOOD_REGISTRY
                ),
                evidence=(
                    f"missing_count="
                    f"{len(missing)}"
                ),
                action=(
                    "Complete the canonical "
                    "36-pair Mood matrix."
                ),
            )
        )

    if extras:
        findings.append(
            Finding(
                key="unexpected_mood_fusions",
                severity="error",
                domain="mood",
                path=str(
                    MOOD_REGISTRY
                ),
                evidence=(
                    f"unexpected="
                    f"{sorted(extras)!r}"
                ),
                action=(
                    "Classify the unexpected "
                    "fusion without deleting "
                    "authority automatically."
                ),
            )
        )

    return findings


def rut_findings() -> list[Finding]:
    if not RUT_REGISTRY.is_file():
        return []

    value = read_json_object(
        RUT_REGISTRY
    )

    semantics = value.get(
        "semantics"
    )

    if not isinstance(
        semantics,
        Mapping,
    ):
        return [
            Finding(
                key="invalid_rut_semantics",
                severity="error",
                domain="rut-sidecar",
                path=str(
                    RUT_REGISTRY
                ),
                evidence=(
                    "semantics must be an object"
                ),
                action=(
                    "Restore explicit additive "
                    "Rut semantics."
                ),
            )
        ]

    expected = {
        "additive": True,
        "fusion": False,
        "occupant_identity_preserved": True,
        "occupant_authority_preserved": True,
        "occupant_removability_preserved": True,
        "new_mood_created": False,
        "new_fusion_ability_created": False,
    }

    findings: list[
        Finding
    ] = []

    for key, expected_value in expected.items():
        actual = semantics.get(
            key
        )

        if actual == expected_value:
            continue

        findings.append(
            Finding(
                key=(
                    f"rut_semantic_{key}"
                ),
                severity="error",
                domain="rut-sidecar",
                path=str(
                    RUT_REGISTRY
                ),
                evidence=(
                    f"expected="
                    f"{expected_value!r}; "
                    f"actual={actual!r}"
                ),
                action=(
                    "Preserve independent, "
                    "removable Sidecar capability "
                    "without Mood fusion."
                ),
            )
        )

    return findings


def tidal_findings() -> list[Finding]:
    if not TIDAL_REGISTRY.is_file():
        return [
            Finding(
                key="tidal_registry_missing",
                severity="warning",
                domain="composition",
                path=str(
                    TIDAL_REGISTRY
                ),
                evidence=(
                    "canonical Tidal registry "
                    "was not found"
                ),
                action=(
                    "Resolve the existing accepted "
                    "registry location before "
                    "creating another."
                ),
            )
        ]

    value = read_json_object(
        TIDAL_REGISTRY
    )

    slots = value.get(
        "slots"
    )

    if not isinstance(
        slots,
        list,
    ):
        return [
            Finding(
                key="invalid_tidal_registry",
                severity="error",
                domain="composition",
                path=str(
                    TIDAL_REGISTRY
                ),
                evidence=(
                    "slots must be an array"
                ),
                action=(
                    "Preserve the nine reusable "
                    "Tidal bindings."
                ),
            )
        ]

    observed: list[str] = []

    for item in slots:
        if not isinstance(
            item,
            Mapping,
        ):
            continue

        name = normalize(
            item.get(
                "substrate",
                "",
            )
        )

        name = (
            TIDAL_ALIASES
            .get(
                name,
                name,
            )
        )

        if name:
            observed.append(
                name
            )

    if tuple(
        observed
    ) == CANONICAL_TIDALS:
        return []

    return [
        Finding(
            key="tidal_family_mismatch",
            severity="error",
            domain="composition",
            path=str(
                TIDAL_REGISTRY
            ),
            evidence=(
                f"expected="
                f"{CANONICAL_TIDALS!r}; "
                f"observed="
                f"{tuple(observed)!r}"
            ),
            action=(
                "Preserve one reusable "
                "binding for each of the nine "
                "canonical Tidals."
            ),
        )
    ]


def inspect_record(
    *,
    path: Path,
    value: dict[str, Any],
) -> list[Finding]:
    findings: list[
        Finding
    ] = []

    relative_path = (
        path.relative_to(
            ROOT
        ).as_posix()
    )

    observed_keys: set[str] = set()

    for field_path, child in flatten(
        value
    ):
        key = terminal_key(
            field_path
        )

        observed_keys.add(
            key
        )

        if (
            key in MOOD_KEYS
            and isinstance(
                child,
                str,
            )
        ):
            mood = normalize(
                child
            ).removeprefix(
                "mood:"
            )

            if (
                mood
                and mood
                not in CANONICAL_MOODS
            ):
                findings.append(
                    Finding(
                        key=(
                            "noncanonical_mood_reference"
                        ),
                        severity="error",
                        domain="mood",
                        path=relative_path,
                        evidence=(
                            f"{field_path}="
                            f"{child!r}"
                        ),
                        action=(
                            "Resolve behavioral "
                            "transformation through "
                            "a canonical Mood."
                        ),
                    )
                )

        if (
            key in COMPOSITION_KEYS
            and isinstance(
                child,
                str,
            )
        ):
            reference = (
                child.strip()
            )

            if (
                not reference
                or reference.startswith(
                    REFERENCE_PREFIXES
                )
            ):
                continue

            if "/" in reference:
                findings.append(
                    Finding(
                        key=(
                            "composition_uses_"
                            "physical_path"
                        ),
                        severity="notice",
                        domain="composition",
                        path=relative_path,
                        evidence=(
                            f"{field_path}="
                            f"{reference!r}"
                        ),
                        action=(
                            "Determine whether a "
                            "stable Shade identity "
                            "should replace this "
                            "physical-path coupling."
                        ),
                    )
                )

    if (
        observed_keys
        & SIDECAR_KEYS
        and not (
            observed_keys
            & RUT_KEYS
        )
    ):
        findings.append(
            Finding(
                key="sidecar_without_rut_surface",
                severity="notice",
                domain="rut-sidecar",
                path=relative_path,
                evidence=(
                    "Sidecar/attachment surface "
                    "exists without a local "
                    "Rut surface."
                ),
                action=(
                    "Check whether Rut capacity "
                    "is inherited or projected "
                    "before adding anything."
                ),
            )
        )

    if (
        observed_keys
        & RUT_KEYS
        and observed_keys
        & MOOD_KEYS
    ):
        findings.append(
            Finding(
                key="rut_and_mood_present",
                severity="notice",
                domain="rut-sidecar",
                path=relative_path,
                evidence=(
                    "Record carries both Rut "
                    "and Mood surfaces."
                ),
                action=(
                    "Verify Rut adds capability "
                    "while Mood transforms "
                    "behavior; never conflate "
                    "the mechanisms."
                ),
            )
        )

    if (
        relative_path.startswith(
            "authority_graph/instances/"
        )
    ):
        if not value.get(
            "id"
        ):
            findings.append(
                Finding(
                    key="shade_identity_missing",
                    severity="error",
                    domain="shade",
                    path=relative_path,
                    evidence=(
                        "canonical Shade record "
                        "has no id"
                    ),
                    action=(
                        "Restore stable canonical "
                        "Shade identity."
                    ),
                )
            )

        for required in (
            "lineage",
            "provenance",
        ):
            if required in value:
                continue

            findings.append(
                Finding(
                    key=(
                        "shade_authority_incomplete"
                    ),
                    severity="warning",
                    domain="shade",
                    path=relative_path,
                    evidence=(
                        f"missing={required}"
                    ),
                    action=(
                        "Locate the canonical "
                        "surface or projection "
                        "before adding duplicate "
                        "authority."
                    ),
                )
            )

    return findings


def targeted_surface_findings() -> tuple[
    list[Finding],
    list[Surface],
]:
    findings: list[
        Finding
    ] = []

    surfaces: list[
        Surface
    ] = []

    shade_ids: dict[
        str,
        list[str],
    ] = {}

    roots = (
        SHADE_ROOT,
        CANON_AUTHORITY_ROOT,
        TIDAL_RUNTIME_ROOT,
    )

    visited: set[
        Path
    ] = set()

    for root in roots:
        if not root.is_dir():
            continue

        for path in iter_structured_files(
            root
        ):
            resolved = path.resolve()

            if resolved in visited:
                continue

            visited.add(
                resolved
            )

            try:
                stat = path.stat()
            except OSError:
                continue

            if (
                stat.st_size
                > MAX_STRUCTURED_BYTES
            ):
                continue

            value = read_structured(
                path
            )

            if value is None:
                continue

            surfaces.append(
                Surface(
                    path=(
                        path.relative_to(
                            ROOT
                        ).as_posix()
                    ),
                    size=stat.st_size,
                    sha256=sha256_file(
                        path
                    ),
                )
            )

            findings.extend(
                inspect_record(
                    path=path,
                    value=value,
                )
            )

            relative_path = (
                path.relative_to(
                    ROOT
                ).as_posix()
            )

            if relative_path.startswith(
                "authority_graph/instances/"
            ):
                shade_id = value.get(
                    "id"
                )

                if isinstance(
                    shade_id,
                    str,
                ) and shade_id.strip():
                    shade_ids.setdefault(
                        shade_id,
                        [],
                    ).append(
                        relative_path
                    )

    for shade_id, owners in (
        shade_ids.items()
    ):
        if len(
            owners
        ) < 2:
            continue

        findings.append(
            Finding(
                key="duplicate_shade_identity",
                severity="error",
                domain="shade",
                path=sorted(
                    owners
                )[0],
                evidence=(
                    f"id={shade_id!r}; "
                    f"owners="
                    f"{sorted(owners)!r}"
                ),
                action=(
                    "Resolve duplicate canonical "
                    "Shade ownership through "
                    "authority and lineage."
                ),
            )
        )

    return (
        findings,
        surfaces,
    )


def build_conformance(
    findings: list[Finding],
) -> dict[str, Any]:
    counts = Counter(
        finding.domain
        for finding in findings
    )

    return {
        "shade_identity": {
            "finding_count": (
                counts["shade"]
            ),
            "principle": (
                "Canonical substance is "
                "substantiated once and reused "
                "through stable Shade identity."
            ),
        },
        "composition_reference_reuse": {
            "finding_count": (
                counts[
                    "composition"
                ]
            ),
            "principle": (
                "Higher structures compose "
                "existing substance rather than "
                "duplicating it."
            ),
        },
        "rut_sidecar_attachment": {
            "finding_count": (
                counts[
                    "rut-sidecar"
                ]
            ),
            "principle": (
                "Ruts attach independently "
                "removable Sidecar capability."
            ),
        },
        "mood_transformation": {
            "finding_count": (
                counts[
                    "mood"
                ]
            ),
            "principle": (
                "Behavioral transformation "
                "uses canonical Moods or "
                "two-Mood fusion."
            ),
        },
    }


def run_audit() -> dict[str, Any]:
    stamp = utc_stamp()

    findings = (
        authority_findings()
        + mood_registry_findings()
        + rut_findings()
        + tidal_findings()
    )

    targeted, surfaces = (
        targeted_surface_findings()
    )

    findings.extend(
        targeted
    )

    severity_counts = Counter(
        finding.severity
        for finding in findings
    )

    key_counts = Counter(
        finding.key
        for finding in findings
    )

    domain_counts = Counter(
        finding.domain
        for finding in findings
    )

    conformance = build_conformance(
        findings
    )

    report_directory = (
        REPORT_ROOT
        / stamp
    )

    report_path = (
        report_directory
        / "report.json"
    )

    findings_path = (
        report_directory
        / "findings.json"
    )

    surfaces_path = (
        report_directory
        / "surfaces.json"
    )

    manifest_path = (
        report_directory
        / "manifest.json"
    )

    report = {
        "schema": (
            "savant://vault/dimensions/"
            "modular-conformance/2.2.0"
        ),
        "operation": (
            "audit_modular_conformance"
        ),
        "timestamp": stamp,
        "passed": (
            severity_counts[
                "error"
            ]
            == 0
        ),
        "mutation_performed": False,
        "authority_effect": "none",
        "scan_mode": (
            "targeted-authority-surfaces"
        ),
        "conformance": conformance,
        "summary": {
            "surface_count": len(
                surfaces
            ),
            "finding_count": len(
                findings
            ),
            "error_count": (
                severity_counts[
                    "error"
                ]
            ),
            "warning_count": (
                severity_counts[
                    "warning"
                ]
            ),
            "notice_count": (
                severity_counts[
                    "notice"
                ]
            ),
            "domains": dict(
                sorted(
                    domain_counts.items()
                )
            ),
            "finding_keys": dict(
                sorted(
                    key_counts.items()
                )
            ),
        },
        "scanned_roots": [
            str(
                SHADE_ROOT
            ),
            str(
                CANON_AUTHORITY_ROOT
            ),
            str(
                TIDAL_RUNTIME_ROOT
            ),
        ],
        "direct_authority_files": [
            str(
                PRIMARY_LAW
            ),
            str(
                PROJECT_INSTRUCTIONS
            ),
            str(
                MOOD_REGISTRY
            ),
            str(
                RUT_REGISTRY
            ),
            str(
                TIDAL_REGISTRY
            ),
        ],
        "laws": {
            "instance_first": True,
            "authority_once": True,
            "mood_governed": True,
            "rut_additive": True,
            "sidecar_removable": True,
            "two_mood_fusion_only": True,
            "weld_composition": True,
            "tidals_reusable": True,
        },
        "limitations": [
            (
                "The complete filesystem is "
                "not scanned."
            ),
            (
                "Filesystem presence does not "
                "establish authority."
            ),
            (
                "Mood absence alone is not "
                "an error."
            ),
            (
                "Generated projections and "
                "historical backups are not "
                "canonical audit surfaces."
            ),
            (
                "This audit performs no "
                "mutation."
            ),
        ],
    }

    write_json(
        report_path,
        report,
    )

    write_json(
        findings_path,
        {
            "schema": (
                "savant://vault/dimensions/"
                "modular-conformance/"
                "findings/2.2.0"
            ),
            "findings": [
                asdict(
                    finding
                )
                for finding in findings
            ],
        },
    )

    write_json(
        surfaces_path,
        {
            "schema": (
                "savant://vault/dimensions/"
                "modular-conformance/"
                "surfaces/2.2.0"
            ),
            "surfaces": [
                asdict(
                    surface
                )
                for surface in surfaces
            ],
        },
    )

    manifest_entries = []

    for path in (
        report_path,
        findings_path,
        surfaces_path,
    ):
        manifest_entries.append(
            {
                "path": str(
                    path
                ),
                "size": (
                    path.stat()
                    .st_size
                ),
                "sha256": (
                    sha256_file(
                        path
                    )
                ),
            }
        )

    write_json(
        manifest_path,
        {
            "schema": (
                "savant://vault/dimensions/"
                "modular-conformance/"
                "manifest/2.2.0"
            ),
            "entries": (
                manifest_entries
            ),
        },
    )

    latest_path = (
        REPORT_ROOT
        / "latest.json"
    )

    write_json(
        latest_path,
        {
            "schema": (
                "savant://vault/dimensions/"
                "modular-conformance/"
                "latest/2.2.0"
            ),
            "timestamp": stamp,
            "report": str(
                report_path
            ),
            "findings": str(
                findings_path
            ),
            "surfaces": str(
                surfaces_path
            ),
            "manifest": str(
                manifest_path
            ),
            "passed": report[
                "passed"
            ],
            "failure_count": (
                report[
                    "summary"
                ][
                    "error_count"
                ]
            ),
            "warning_count": (
                report[
                    "summary"
                ][
                    "warning_count"
                ]
            ),
            "finding_count": (
                report[
                    "summary"
                ][
                    "finding_count"
                ]
            ),
            "surface_count": (
                report[
                    "summary"
                ][
                    "surface_count"
                ]
            ),
            "scan_mode": (
                "targeted-authority-surfaces"
            ),
            "conformance": (
                conformance
            ),
        },
    )

    return {
        "operation": (
            "audit_modular_conformance"
        ),
        "passed": report[
            "passed"
        ],
        "mutation_performed": False,
        "authority_effect": "none",
        "scan_mode": (
            "targeted-authority-surfaces"
        ),
        "summary": report[
            "summary"
        ],
        "conformance": (
            conformance
        ),
        "latest": str(
            latest_path
        ),
    }


def verify_latest() -> dict[str, Any]:
    latest_path = (
        REPORT_ROOT
        / "latest.json"
    )

    if not latest_path.is_file():
        raise AuditError(
            "latest report does not exist: "
            f"{latest_path}"
        )

    latest = read_json_object(
        latest_path
    )

    if (
        latest.get(
            "schema"
        )
        != (
            "savant://vault/dimensions/"
            "modular-conformance/"
            "latest/2.2.0"
        )
    ):
        raise AuditError(
            "latest report is stale; "
            "run audit with v2.2.0"
        )

    expected_domains = {
        "shade_identity",
        "composition_reference_reuse",
        "rut_sidecar_attachment",
        "mood_transformation",
    }

    conformance = latest.get(
        "conformance"
    )

    if not isinstance(
        conformance,
        Mapping,
    ):
        raise AuditError(
            "latest audit lacks "
            "conformance domains"
        )

    if set(
        conformance
    ) != expected_domains:
        raise AuditError(
            "conformance domain "
            "contract mismatch"
        )

    manifest_path = Path(
        str(
            latest.get(
                "manifest",
                "",
            )
        )
    )

    manifest = read_json_object(
        manifest_path
    )

    entries = manifest.get(
        "entries"
    )

    if not isinstance(
        entries,
        list,
    ):
        raise AuditError(
            "manifest entries must "
            "be an array"
        )

    for entry in entries:
        if not isinstance(
            entry,
            Mapping,
        ):
            raise AuditError(
                "invalid manifest entry"
            )

        path = Path(
            str(
                entry.get(
                    "path",
                    "",
                )
            )
        )

        if not path.is_file():
            raise AuditError(
                f"manifest artifact "
                f"missing: {path}"
            )

        expected_digest = str(
            entry.get(
                "sha256",
                "",
            )
        )

        actual_digest = sha256_file(
            path
        )

        if (
            actual_digest
            != expected_digest
        ):
            raise AuditError(
                "manifest digest mismatch: "
                f"{path}"
            )

    return {
        "operation": (
            "verify_modular_conformance"
        ),
        "passed": True,
        "audit_passed": bool(
            latest.get(
                "passed"
            )
        ),
        "failure_count": int(
            latest.get(
                "failure_count",
                0,
            )
        ),
        "warning_count": int(
            latest.get(
                "warning_count",
                0,
            )
        ),
        "finding_count": int(
            latest.get(
                "finding_count",
                0,
            )
        ),
        "surface_count": int(
            latest.get(
                "surface_count",
                0,
            )
        ),
        "scan_mode": latest.get(
            "scan_mode"
        ),
        "manifest_entry_count": len(
            entries
        ),
        "conformance_domains": sorted(
            expected_domains
        ),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Audit Savant modular "
            "conformance on canonical "
            "authority surfaces."
        )
    )

    parser.add_argument(
        "operation",
        choices=(
            "audit",
            "verify",
        ),
    )

    return parser.parse_args()


def main() -> int:
    arguments = parse_args()

    try:
        if (
            arguments.operation
            == "audit"
        ):
            result = run_audit()

            print(
                json.dumps(
                    result,
                    indent=2,
                    sort_keys=True,
                )
            )

            return (
                0
                if result[
                    "passed"
                ]
                else 1
            )

        result = verify_latest()

        print(
            json.dumps(
                result,
                indent=2,
                sort_keys=True,
            )
        )

        return 0

    except AuditError as error:
        print(
            json.dumps(
                {
                    "operation": (
                        arguments.operation
                    ),
                    "passed": False,
                    "error": str(
                        error
                    ),
                },
                indent=2,
                sort_keys=True,
            ),
            file=sys.stderr,
        )

        return 2


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
