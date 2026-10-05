#!/usr/bin/env python3

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from pathlib import Path
from typing import Any

import yaml


ROOT = Path(
    "/root/savant-runtime"
)

EXILE_RUNTIME_ROOT = (
    ROOT
    / "ontology/obelisks/_template/segue/gates/"
      "_template/segue/innates/_template/segue/"
      "exiles/segue/exile_runtime"
)

EXILE_SERVICES = (
    EXILE_RUNTIME_ROOT
    / "runtime/services"
)

if str(EXILE_SERVICES) not in sys.path:
    sys.path.insert(
        0,
        str(EXILE_SERVICES),
    )


from EXILE_REGISTRY import (  # noqa: E402
    EXPECTED_EXILE_COUNT,
    ExileRegistryError,
    load_exile_registry,
)


UI_ROOT = (
    EXILE_RUNTIME_ROOT
    / "ui"
)

AUTHORITY_ROOT = (
    ROOT
    / "canon-system/authority/exiles"
)

EXILES_ROOT = (
    EXILE_RUNTIME_ROOT
    .parent
    .parent
)

PUBLIC_ROOT = (
    UI_ROOT
    / "public"
)

INSTANCE_ROOT = (
    PUBLIC_ROOT
    / "instances"
)

ACTIVE_INSTANCE = (
    PUBLIC_ROOT
    / "exile-ui.instance.json"
)

MANIFEST_PATH = (
    PUBLIC_ROOT
    / "exile-ui.instances.json"
)


PANELS = (
    "overview",
    "capabilities",
    "pipeline",
    "graph",
    "health",
    "validation",
    "activity",
    "provenance",
    "settings",
)


PIPELINE = (
    "admission",
    "identity_resolution",
    "authority_resolution",
    "policy_resolution",
    "schema_validation",
    "provenance_resolution",
    "dependency_resolution",
    "temporal_resolution",
    "evidence_resolution",
    "conflict_analysis",
    "supersession_analysis",
    "execution_planning",
    "domain_execution",
    "state_derivation",
    "change_detection",
    "projection",
    "observability",
    "attestation",
)


PRIORITY_MODES = (
    {
        "id": "mandatory",
        "label": "Mandatory",
        "description": (
            "Minimum dependency-closed requirement."
        ),
    },
    {
        "id": "salient",
        "label": "Salient",
        "description": (
            "Mandatory plus materially important work."
        ),
    },
    {
        "id": "arbitrary",
        "label": "Arbitrary",
        "description": (
            "Complete admissible expansion."
        ),
    },
)


HEALTH_DIMENSIONS = (
    "definition",
    "authority",
    "dependencies",
    "runtime",
    "domain_integrity",
    "replay",
    "projection_freshness",
    "peer_integration",
    "scyon_integration",
)


VALIDATION_DIMENSIONS = (
    "identity",
    "dependency",
    "relationship",
    "authority",
    "history",
    "temporal",
    "evidence",
    "provenance",
    "integration",
)


ENHANCEMENTS = (
    "instance overlay architecture",
    "authority-derived identity projection",
    "Graffiti-owned brand substrate",
    "procedural GPU atmosphere",
    "instanced shard field",
    "adaptive rendering quality",
    "reduced-motion compliance",
    "keyboard-first navigation",
    "command palette",
    "contextual command routing",
    "nine-panel control surface",
    "eighteen-stage pipeline visualization",
    "pipeline stage inspection",
    "three-mode priority control",
    "capability matrix",
    "capability group filtering",
    "nine-dimensional health",
    "nine-dimensional validation",
    "dependency topology surface",
    "activity event stream",
    "provenance inspector",
    "authority visibility",
    "live telemetry HUD",
    "responsive dock system",
    "focus-mode panels",
    "semantic status signals",
    "deterministic instance compilation",
)


class InstanceError(
    RuntimeError
):
    pass


def canonical_json(
    value: Any,
) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def digest(
    value: Any,
) -> str:
    return hashlib.sha256(
        canonical_json(
            value
        ).encode(
            "utf-8"
        )
    ).hexdigest()


def atomic_json(
    path: Path,
    payload: Any,
) -> None:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    temporary = (
        path.parent
        / (
            path.name
            + ".tmp"
        )
    )

    temporary.write_text(
        json.dumps(
            payload,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    temporary.replace(
        path
    )


def registry(
):
    result = (
        load_exile_registry()
    )

    if (
        result.count
        != EXPECTED_EXILE_COUNT
    ):
        raise InstanceError(
            "Exile registry cardinality "
            f"must be {EXPECTED_EXILE_COUNT}; "
            f"found {result.count}"
        )

    return result


def exile_names(
) -> tuple[str, ...]:
    return (
        registry().names
    )


def require_triadic(
    name: str,
    count: int,
    *,
    allow_zero: bool = False,
) -> None:
    if (
        allow_zero
        and count == 0
    ):
        return

    if (
        count == 3
        or (
            count > 0
            and count % 9 == 0
        )
    ):
        return

    raise InstanceError(
        f"{name} cardinality "
        "must be 3 or a positive "
        f"multiple of 9; got {count}"
    )


def authority_path(
    exile: str,
) -> Path:
    return (
        AUTHORITY_ROOT
        / f"{exile}.yaml"
    )


def load_authority(
    exile: str,
) -> dict[str, Any]:
    if exile not in exile_names():
        raise InstanceError(
            "unknown Exile: "
            + exile
        )

    path = authority_path(
        exile
    )

    if not path.is_file():
        raise InstanceError(
            "missing Exile authority: "
            + str(path)
        )

    try:
        payload = yaml.safe_load(
            path.read_text(
                encoding="utf-8"
            )
        )

    except yaml.YAMLError as exc:
        raise InstanceError(
            "invalid Exile authority YAML: "
            f"{path}: {exc}"
        ) from exc

    if not isinstance(
        payload,
        dict,
    ):
        raise InstanceError(
            "invalid Exile authority "
            f"document: {path}"
        )

    expected_id = (
        f"exile:{exile}"
    )

    if (
        payload.get(
            "id"
        )
        != expected_id
    ):
        raise InstanceError(
            "Exile authority identity "
            f"mismatch for {exile}"
        )

    purposes = (
        payload
        .get(
            "purpose",
            {},
        )
        .get(
            "current",
            [],
        )
    )

    if not isinstance(
        purposes,
        list,
    ):
        raise InstanceError(
            f"{exile}: purpose.current "
            "must be a list"
        )

    require_triadic(
        f"{exile}: purposes",
        len(
            purposes
        ),
    )

    return payload


def capability_manifest_path(
    exile: str,
) -> Path:
    return (
        EXILES_ROOT
        / exile
        / "interface/capabilities/"
          "capabilities.json"
    )


def load_real_capabilities(
    exile: str,
) -> list[dict[str, str]]:
    path = (
        capability_manifest_path(
            exile
        )
    )

    if not path.is_file():
        return []

    try:
        payload = json.loads(
            path.read_text(
                encoding="utf-8"
            )
        )

    except json.JSONDecodeError:
        return []

    if not isinstance(
        payload,
        dict,
    ):
        return []

    candidates = payload.get(
        "capabilities",
        [],
    )

    if not isinstance(
        candidates,
        list,
    ):
        return []

    capabilities: list[
        dict[str, str]
    ] = []

    for candidate in candidates:
        if not isinstance(
            candidate,
            dict,
        ):
            continue

        capability_id = str(
            candidate.get(
                "id",
                candidate.get(
                    "name",
                    "",
                ),
            )
        ).strip()

        if not capability_id:
            continue

        capabilities.append(
            {
                "id":
                    capability_id,
                "group":
                    str(
                        candidate.get(
                            "group",
                            "domain",
                        )
                    ),
                "status":
                    str(
                        candidate.get(
                            "status",
                            "ready",
                        )
                    ),
            }
        )

    if capabilities:
        require_triadic(
            f"{exile}: real capabilities",
            len(
                capabilities
            ),
        )

    return capabilities


def projected_capability_slots(
    authority: dict[str, Any],
) -> list[dict[str, str]]:
    purposes = list(
        authority[
            "purpose"
        ][
            "current"
        ]
    )

    authority_state = str(
        authority
        .get(
            "authority",
            {},
        )
        .get(
            "state",
            authority.get(
                "status",
                "unknown",
            ),
        )
    )

    capabilities: list[
        dict[str, str]
    ] = []

    for purpose in purposes:
        capability_id = (
            str(
                purpose
            )
            .lower()
            .replace(
                " ",
                "-",
            )
            .replace(
                "/",
                "-",
            )
        )

        capabilities.append(
            {
                "id": (
                    "purpose:"
                    + capability_id
                ),
                "group":
                    "authority-purpose",
                "status":
                    authority_state,
            }
        )

    for index in range(
        len(
            capabilities
        )
        + 1,
        19,
    ):
        capabilities.append(
            {
                "id":
                    f"reserved:{index:02d}",
                "group":
                    "extension-slot",
                "status":
                    "unresolved",
            }
        )

    if (
        len(
            capabilities
        )
        != 18
    ):
        raise InstanceError(
            "projected capability surface "
            "must contain 18 slots"
        )

    return capabilities


def health_projection(
    authority: dict[str, Any],
) -> list[dict[str, str]]:
    authority_state = str(
        authority
        .get(
            "authority",
            {},
        )
        .get(
            "state",
            "unknown",
        )
    )

    result: list[
        dict[str, str]
    ] = []

    for dimension in (
        HEALTH_DIMENSIONS
    ):
        if (
            dimension
            == "definition"
        ):
            status = "healthy"

        elif (
            dimension
            == "authority"
        ):
            status = (
                authority_state
            )

        else:
            status = "unknown"

        result.append(
            {
                "id":
                    dimension,
                "status":
                    status,
            }
        )

    return result


def validation_projection(
) -> list[dict[str, str]]:
    return [
        {
            "id":
                dimension,
            "status":
                "unknown",
        }
        for dimension
        in VALIDATION_DIMENSIONS
    ]


def compile_instance(
    exile: str,
) -> dict[str, Any]:
    authority = (
        load_authority(
            exile
        )
    )

    real_capabilities = (
        load_real_capabilities(
            exile
        )
    )

    capabilities = (
        real_capabilities
        if real_capabilities
        else projected_capability_slots(
            authority
        )
    )

    title = str(
        authority.get(
            "title",
            exile,
        )
    )

    purposes = [
        str(
            value
        )
        for value
        in authority[
            "purpose"
        ][
            "current"
        ]
    ]

    authority_data = (
        authority.get(
            "authority",
            {},
        )
    )

    authority_state = str(
        authority_data.get(
            "state",
            authority.get(
                "status",
                "unknown",
            ),
        )
    )

    confidence = float(
        authority_data.get(
            "confidence",
            0.0,
        )
    )

    source_path = (
        authority_path(
            exile
        )
    )

    capability_path = (
        capability_manifest_path(
            exile
        )
    )

    payload: dict[
        str,
        Any,
    ] = {
        "schema": (
            "savant://ui/"
            "exile-instance/1.0.0"
        ),
        "instance_id":
            f"ui:exile:{exile}",
        "exile_id":
            f"exile:{exile}",
        "name":
            title.title(),
        "designation": (
            " / ".join(
                purposes
            )
        ),
        "sigil": (
            title[:2]
            .upper()
        ),
        "status": str(
            authority.get(
                "status",
                authority_state,
            )
        ),
        "authority": {
            "state":
                authority_state,
            "confidence":
                confidence,
            "source": str(
                source_path.relative_to(
                    ROOT
                )
            ),
        },
        "accent": {
            "primary":
                "#E6C03B",
            "secondary":
                "#4A90E2",
            "signal":
                "#FF4068",
        },
        "purposes":
            purposes,
        "priority_modes": [
            dict(
                mode
            )
            for mode
            in PRIORITY_MODES
        ],
        "pipeline":
            list(
                PIPELINE
            ),
        "panels":
            list(
                PANELS
            ),
        "capabilities":
            capabilities,
        "health":
            health_projection(
                authority
            ),
        "validation":
            validation_projection(),
        "enhancements":
            list(
                ENHANCEMENTS
            ),
        "projection": {
            "authoritative":
                False,
            "rebuildable":
                True,
            "authority_source": str(
                source_path.relative_to(
                    ROOT
                )
            ),
            "capability_source": (
                str(
                    capability_path.relative_to(
                        ROOT
                    )
                )
                if capability_path.is_file()
                else None
            ),
            "reserved_capability_slots": (
                not bool(
                    real_capabilities
                )
            ),
        },
    }

    payload[
        "projection_digest"
    ] = digest(
        payload
    )

    return payload


def compile_all(
) -> dict[str, Any]:
    exile_registry = (
        registry()
    )

    INSTANCE_ROOT.mkdir(
        parents=True,
        exist_ok=True,
    )

    compiled: list[
        dict[str, Any]
    ] = []

    for exile in (
        exile_registry.names
    ):
        payload = (
            compile_instance(
                exile
            )
        )

        destination = (
            INSTANCE_ROOT
            / f"{exile}.json"
        )

        atomic_json(
            destination,
            payload,
        )

        compiled.append(
            {
                "exile":
                    exile,
                "instance_id":
                    payload[
                        "instance_id"
                    ],
                "authority_state":
                    payload[
                        "authority"
                    ][
                        "state"
                    ],
                "capability_count":
                    len(
                        payload[
                            "capabilities"
                        ]
                    ),
                "reserved_capability_slots":
                    payload[
                        "projection"
                    ][
                        "reserved_capability_slots"
                    ],
                "path":
                    str(
                        destination
                    ),
                "sha256":
                    digest(
                        payload
                    ),
            }
        )

    if (
        len(
            compiled
        )
        != EXPECTED_EXILE_COUNT
    ):
        raise InstanceError(
            "Exile instance population "
            f"must be "
            f"{EXPECTED_EXILE_COUNT}"
        )

    manifest = {
        "schema": (
            "savant://ui/"
            "exile-instance-registry/1.1.0"
        ),
        "count":
            exile_registry.count,
        "registry_source":
            str(
                exile_registry.source
            ),
        "registry_digest":
            exile_registry.source_digest,
        "hardcoded_exile_list":
            False,
        "instances":
            compiled,
        "authority_effect":
            "none",
        "rebuildable":
            True,
    }

    manifest[
        "digest"
    ] = digest(
        manifest
    )

    atomic_json(
        MANIFEST_PATH,
        manifest,
    )

    return manifest


def select_instance(
    exile: str,
) -> dict[str, Any]:
    exile_registry = (
        registry()
    )

    if not exile_registry.contains(
        exile
    ):
        raise InstanceError(
            "unknown Exile: "
            + exile
        )

    source = (
        INSTANCE_ROOT
        / f"{exile}.json"
    )

    if not source.is_file():
        compile_all()

    if not source.is_file():
        raise InstanceError(
            "compiled UI instance "
            "is unavailable: "
            + str(source)
        )

    shutil.copyfile(
        source,
        ACTIVE_INSTANCE,
    )

    payload = json.loads(
        ACTIVE_INSTANCE.read_text(
            encoding="utf-8"
        )
    )

    return {
        "selected":
            exile,
        "instance_id":
            payload[
                "instance_id"
            ],
        "source":
            str(
                source
            ),
        "active":
            str(
                ACTIVE_INSTANCE
            ),
        "registry_source":
            str(
                exile_registry.source
            ),
        "registry_digest":
            exile_registry.source_digest,
        "sha256":
            digest(
                payload
            ),
    }


def valid_capability_count(
    count: int,
) -> bool:
    return (
        count == 3
        or (
            count > 0
            and count % 9 == 0
        )
    )


def validate_instances(
) -> dict[str, Any]:
    exile_registry = (
        registry()
    )

    errors: list[
        str
    ] = []

    for exile in (
        exile_registry.names
    ):
        path = (
            INSTANCE_ROOT
            / f"{exile}.json"
        )

        if not path.is_file():
            errors.append(
                f"{exile}: missing instance"
            )

            continue

        try:
            payload = json.loads(
                path.read_text(
                    encoding="utf-8"
                )
            )

        except json.JSONDecodeError as exc:
            errors.append(
                f"{exile}: "
                f"invalid JSON: {exc}"
            )

            continue

        if (
            payload.get(
                "exile_id"
            )
            != f"exile:{exile}"
        ):
            errors.append(
                f"{exile}: "
                "identity mismatch"
            )

        if (
            len(
                payload.get(
                    "purposes",
                    [],
                )
            )
            != 3
        ):
            errors.append(
                f"{exile}: "
                "purpose count != 3"
            )

        if (
            len(
                payload.get(
                    "pipeline",
                    [],
                )
            )
            != 18
        ):
            errors.append(
                f"{exile}: "
                "pipeline count != 18"
            )

        if (
            len(
                payload.get(
                    "panels",
                    [],
                )
            )
            != 9
        ):
            errors.append(
                f"{exile}: "
                "panel count != 9"
            )

        capability_count = len(
            payload.get(
                "capabilities",
                [],
            )
        )

        if not valid_capability_count(
            capability_count
        ):
            errors.append(
                f"{exile}: "
                "invalid capability "
                f"cardinality "
                f"{capability_count}"
            )

        if (
            len(
                payload.get(
                    "health",
                    [],
                )
            )
            != 9
        ):
            errors.append(
                f"{exile}: "
                "health count != 9"
            )

        if (
            len(
                payload.get(
                    "validation",
                    [],
                )
            )
            != 9
        ):
            errors.append(
                f"{exile}: "
                "validation count != 9"
            )

        if (
            len(
                payload.get(
                    "enhancements",
                    [],
                )
            )
            != 27
        ):
            errors.append(
                f"{exile}: "
                "enhancement count != 27"
            )

    manifest_error: (
        str
        | None
    ) = None

    if MANIFEST_PATH.is_file():
        try:
            manifest = json.loads(
                MANIFEST_PATH.read_text(
                    encoding="utf-8"
                )
            )

            if (
                manifest.get(
                    "registry_digest"
                )
                != exile_registry
                .source_digest
            ):
                manifest_error = (
                    "compiled instance registry "
                    "was generated from a "
                    "different Exile registry "
                    "revision"
                )

        except json.JSONDecodeError as exc:
            manifest_error = (
                "instance registry manifest "
                f"is invalid JSON: {exc}"
            )

    else:
        manifest_error = (
            "instance registry manifest "
            "is missing"
        )

    if manifest_error:
        errors.append(
            manifest_error
        )

    return {
        "schema": (
            "savant://assurance/"
            "splyce-exile-instances/1.1.0"
        ),
        "valid":
            not errors,
        "instance_count":
            exile_registry.count,
        "expected_instance_count":
            EXPECTED_EXILE_COUNT,
        "registry_source":
            str(
                exile_registry.source
            ),
        "registry_digest":
            exile_registry.source_digest,
        "hardcoded_exile_list":
            False,
        "errors":
            errors,
    }


def build_parser(
) -> argparse.ArgumentParser:
    exile_registry = (
        registry()
    )

    parser = argparse.ArgumentParser(
        description=(
            "Compile deterministic "
            "Savant Exile UI instances"
        )
    )

    commands = (
        parser.add_subparsers(
            dest="command",
            required=True,
        )
    )

    commands.add_parser(
        "compile"
    )

    select = (
        commands.add_parser(
            "select"
        )
    )

    select.add_argument(
        "exile",
        choices=(
            exile_registry.names
        ),
    )

    commands.add_parser(
        "validate"
    )

    commands.add_parser(
        "list"
    )

    return parser


def main(
) -> int:
    arguments = (
        build_parser()
        .parse_args()
    )

    exile_registry = (
        registry()
    )

    if (
        arguments.command
        == "compile"
    ):
        result = (
            compile_all()
        )

    elif (
        arguments.command
        == "select"
    ):
        result = (
            select_instance(
                arguments.exile
            )
        )

    elif (
        arguments.command
        == "validate"
    ):
        result = (
            validate_instances()
        )

    elif (
        arguments.command
        == "list"
    ):
        result = {
            "count":
                exile_registry.count,
            "registry_source":
                str(
                    exile_registry.source
                ),
            "registry_digest":
                exile_registry.source_digest,
            "hardcoded_exile_list":
                False,
            "exiles":
                list(
                    exile_registry.names
                ),
        }

    else:
        raise InstanceError(
            "unsupported command"
        )

    print(
        json.dumps(
            result,
            indent=2,
            sort_keys=True,
        )
    )

    if (
        arguments.command
        == "validate"
        and not result[
            "valid"
        ]
    ):
        return 1

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(
            main()
        )

    except (
        OSError,
        ValueError,
        KeyError,
        InstanceError,
        ExileRegistryError,
        yaml.YAMLError,
    ) as exc:
        print(
            "ERROR: "
            f"{type(exc).__name__}: "
            f"{exc}",
            file=sys.stderr,
        )

        raise SystemExit(1)
