#!/usr/bin/env python3

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Any


ROOT = Path(
    os.environ.get(
        "SAVANT_ROOT",
        "/root/savant-runtime",
    )
).resolve()

FOCAL_ROOT = (
    ROOT
    / "runtime/scyon/focals"
)

KERNEL = (
    ROOT
    / "runtime/scyon/scyon_kernel.py"
)

FOCAL_VALIDATOR = (
    ROOT
    / "assurance/validators/"
    "validate_scyon_focal_definition.py"
)

DEFAULT_OUTPUT = (
    FOCAL_ROOT
    / "registry.json"
)

FOCAL_SCHEMA_PREFIX = (
    "savant://runtime/scyon/focal/"
)

REGISTRY_SCHEMA = (
    "savant://runtime/scyon/"
    "focal-registry/1.4.0"
)


class RegistryError(RuntimeError):
    pass


def require(
    condition: bool,
    message: str,
) -> None:
    if not condition:
        raise RegistryError(message)


def canonical_json(
    value: Any,
) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def digest_value(
    value: Any,
) -> str:
    return hashlib.sha256(
        canonical_json(value).encode(
            "utf-8"
        )
    ).hexdigest()


def sha256_file(
    path: Path,
) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as handle:
        for chunk in iter(
            lambda: handle.read(
                1024 * 1024
            ),
            b"",
        ):
            digest.update(chunk)

    return digest.hexdigest()


def load_json(
    path: Path,
) -> Any:
    try:
        return json.loads(
            path.read_text(
                encoding="utf-8"
            )
        )

    except json.JSONDecodeError as exc:
        raise RegistryError(
            f"invalid JSON {path}: {exc}"
        ) from exc


def atomic_json(
    path: Path,
    value: Any,
) -> None:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    payload = (
        json.dumps(
            value,
            indent=2,
            sort_keys=True,
            ensure_ascii=False,
        )
        + "\n"
    )

    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        dir=path.parent,
        prefix=f".{path.name}.",
        delete=False,
    ) as handle:
        handle.write(payload)
        handle.flush()
        os.fsync(
            handle.fileno()
        )

        temporary = Path(
            handle.name
        )

    os.replace(
        temporary,
        path,
    )


def load_validator() -> Any:
    require(
        FOCAL_VALIDATOR.is_file(),
        (
            "Focal validator unavailable: "
            f"{FOCAL_VALIDATOR}"
        ),
    )

    specification = (
        importlib.util.spec_from_file_location(
            "savant_scyon_focal_definition_validator",
            FOCAL_VALIDATOR,
        )
    )

    require(
        specification is not None
        and specification.loader is not None,
        "cannot load Focal validator",
    )

    module = (
        importlib.util.module_from_spec(
            specification
        )
    )

    sys.modules[
        specification.name
    ] = module

    specification.loader.exec_module(
        module
    )

    return module


def inside_root(
    raw: Any,
    label: str,
    *,
    must_exist: bool,
    require_file: bool,
) -> str:
    require(
        isinstance(raw, str)
        and bool(raw.strip()),
        f"{label} path missing",
    )

    path = Path(
        raw
    ).resolve()

    try:
        path.relative_to(ROOT)

    except ValueError as exc:
        raise RegistryError(
            (
                f"{label} escapes "
                f"Savant root: {path}"
            )
        ) from exc

    if must_exist:
        require(
            path.exists(),
            f"{label} unavailable: {path}",
        )

    if (
        must_exist
        and require_file
    ):
        require(
            path.is_file(),
            f"{label} must be file: {path}",
        )

    return str(path)


def normalize_string_list(
    value: Any,
    label: str,
) -> list[str]:
    require(
        isinstance(value, list),
        f"{label} must be array",
    )

    normalized: list[str] = []

    for item in value:
        require(
            isinstance(item, str)
            and bool(item.strip()),
            f"{label} contains invalid string",
        )

        item = item.strip()

        require(
            item not in normalized,
            f"{label} contains duplicate: {item}",
        )

        normalized.append(item)

    return sorted(normalized)


def discover_focal_sources(
) -> tuple[
    list[Path],
    list[dict[str, str]],
]:
    sources: list[Path] = []
    ignored: list[
        dict[str, str]
    ] = []

    require(
        FOCAL_ROOT.is_dir(),
        (
            "Focal root unavailable: "
            f"{FOCAL_ROOT}"
        ),
    )

    for path in sorted(
        FOCAL_ROOT.glob("*.json")
    ):
        resolved = path.resolve()

        if resolved == DEFAULT_OUTPUT:
            ignored.append(
                {
                    "path": str(resolved),
                    "reason": "generated-registry",
                }
            )
            continue

        value = load_json(
            resolved
        )

        if not isinstance(
            value,
            dict,
        ):
            ignored.append(
                {
                    "path": str(resolved),
                    "reason": "non-object-json",
                }
            )
            continue

        schema = value.get(
            "schema"
        )

        if not (
            isinstance(schema, str)
            and schema.startswith(
                FOCAL_SCHEMA_PREFIX
            )
        ):
            ignored.append(
                {
                    "path": str(resolved),
                    "reason": "not-focal-schema",
                }
            )
            continue

        sources.append(
            resolved
        )

    require(
        bool(sources),
        "no typed Scyon Focal definitions discovered",
    )

    return (
        sources,
        ignored,
    )


def validate_definition(
    path: Path,
) -> dict[str, Any]:
    validator = load_validator()

    focal = validator.load_json(
        path,
        "Focal definition",
    )

    try:
        result = validator.validate(
            focal
        )

    except Exception as exc:
        raise RegistryError(
            (
                "Focal definition validation "
                f"failed for {path}: "
                f"{type(exc).__name__}: {exc}"
            )
        ) from exc

    require(
        isinstance(result, dict)
        and result.get("valid")
        is True,
        (
            "Focal validator did not return "
            f"valid=true: {path}"
        ),
    )

    return result


def normalize_command_surface(
    focal_id: str,
    registration: dict[str, Any],
) -> dict[str, Any]:
    surface = registration.get(
        "command_surface"
    )

    require(
        isinstance(surface, dict),
        (
            f"{focal_id}: "
            "command_surface missing"
        ),
    )

    default_runtime = inside_root(
        surface.get(
            "default_runtime"
        ),
        (
            f"{focal_id} "
            "default_runtime"
        ),
        must_exist=True,
        require_file=True,
    )

    passthrough = (
        normalize_string_list(
            surface.get(
                "passthrough_commands",
                [],
            ),
            (
                f"{focal_id} "
                "passthrough_commands"
            ),
        )
    )

    routes = surface.get(
        "routes",
        {},
    )

    require(
        isinstance(routes, dict),
        f"{focal_id}: routes must be object",
    )

    normalized_routes: dict[
        str,
        dict[str, str],
    ] = {}

    for route_name in sorted(routes):
        require(
            isinstance(route_name, str)
            and bool(route_name.strip()),
            f"{focal_id}: invalid route name",
        )

        require(
            route_name not in passthrough,
            (
                f"{focal_id}: command "
                f"{route_name} declared twice"
            ),
        )

        route = routes[
            route_name
        ]

        require(
            isinstance(route, dict),
            (
                f"{focal_id}: route "
                f"{route_name} must be object"
            ),
        )

        runtime = inside_root(
            route.get("runtime"),
            (
                f"{focal_id} route "
                f"{route_name}"
            ),
            must_exist=True,
            require_file=True,
        )

        command = route.get(
            "command"
        )

        require(
            isinstance(command, str)
            and bool(command.strip()),
            (
                f"{focal_id}: route "
                f"{route_name} command missing"
            ),
        )

        normalized_routes[
            route_name
        ] = {
            "runtime": runtime,
            "command": command.strip(),
        }

    return {
        "default_runtime": default_runtime,
        "passthrough_commands": passthrough,
        "routes": normalized_routes,
    }


def normalize_composition(
    focal_id: str,
    registration: dict[str, Any],
) -> dict[str, str]:
    composition = registration.get(
        "composes",
        {},
    )

    require(
        isinstance(composition, dict),
        f"{focal_id}: composes must be object",
    )

    result: dict[
        str,
        str,
    ] = {}

    for name in sorted(composition):
        result[
            str(name)
        ] = inside_root(
            composition[name],
            (
                f"{focal_id} "
                f"composition {name}"
            ),
            must_exist=True,
            require_file=True,
        )

    require(
        result.get(
            "scyon_kernel"
        )
        == str(
            KERNEL.resolve()
        ),
        (
            f"{focal_id}: Focal must "
            "compose canonical Scyon kernel"
        ),
    )

    return result


def normalize_mutation(
    focal_id: str,
    registration: dict[str, Any],
) -> dict[str, Any]:
    mutation = registration.get(
        "mutation"
    )

    require(
        isinstance(mutation, dict),
        (
            f"{focal_id}: mutation "
            "contract missing"
        ),
    )

    for name in (
        "filesystem_move",
        "filesystem_delete",
        "authority_rewrite",
        "historical_rewrite",
    ):
        require(
            mutation.get(name)
            is False,
            (
                f"{focal_id}: forbidden "
                f"mutation enabled: {name}"
            ),
        )

    return {
        str(key): value
        for key, value
        in sorted(
            mutation.items()
        )
    }


def compile_instance(
    path: Path,
) -> dict[str, Any]:
    validation = validate_definition(
        path
    )

    focal = load_json(
        path
    )

    require(
        isinstance(focal, dict),
        f"Focal root must be object: {path}",
    )

    focal_id = str(
        focal["focal_id"]
    )

    focal_kind = str(
        focal["focal_kind"]
    )

    registration = focal[
        "registration"
    ]

    aliases = normalize_string_list(
        registration.get(
            "aliases",
            [],
        ),
        f"{focal_id} aliases",
    )

    command_surface = (
        normalize_command_surface(
            focal_id,
            registration,
        )
    )

    composition = (
        normalize_composition(
            focal_id,
            registration,
        )
    )

    mutation = normalize_mutation(
        focal_id,
        registration,
    )

    runtime = inside_root(
        registration.get(
            "runtime"
        ),
        f"{focal_id} runtime",
        must_exist=True,
        require_file=True,
    )

    state = inside_root(
        registration.get(
            "state"
        ),
        f"{focal_id} state",
        must_exist=False,
        require_file=False,
    )

    projection = inside_root(
        registration.get(
            "projection"
        ),
        f"{focal_id} projection",
        must_exist=False,
        require_file=False,
    )

    service_binding = validation.get(
        "registration",
        {},
    ).get(
        "service_binding"
    )

    instance: dict[
        str,
        Any,
    ] = {
        "aliases": aliases,
        "archetype": str(
            focal["archetype"]
        ),
        "authority_state": str(
            focal[
                "authority_state"
            ]
        ),
        "command_surface": (
            command_surface
        ),
        "composes": composition,
        "definition": str(path),
        "definition_sha256": (
            sha256_file(path)
        ),
        "engine_id": str(
            focal["engine_id"]
        ),
        "focal_id": focal_id,
        "focal_kind": focal_kind,
        "mutation": mutation,
        "owner_id": str(
            focal["owner_id"]
        ),
        "owner_tier": str(
            focal["owner_tier"]
        ),
        "projection": projection,
        "runtime": runtime,
        "schema": str(
            focal["schema"]
        ),
        "scyon_id": str(
            focal["scyon_id"]
        ),
        "service_backed": (
            service_binding
            is not None
        ),
        "service_binding": (
            service_binding
        ),
        "state": state,
        "status": str(
            registration.get(
                "status",
                "registered",
            )
        ),
        "validation": {
            "valid": True,
            "validator": str(
                FOCAL_VALIDATOR
            ),
            "validator_sha256": (
                sha256_file(
                    FOCAL_VALIDATOR
                )
            ),
        },
    }

    instance[
        "registration_digest"
    ] = digest_value(
        instance
    )

    return instance


def validate_registry_uniqueness(
    instances: list[
        dict[str, Any]
    ],
) -> None:
    focal_ids: set[str] = set()
    scyon_ids: set[str] = set()
    engine_ids: set[str] = set()
    aliases: dict[
        str,
        str,
    ] = {}

    for instance in instances:
        focal_id = str(
            instance["focal_id"]
        )

        scyon_id = str(
            instance["scyon_id"]
        )

        engine_id = str(
            instance["engine_id"]
        )

        require(
            focal_id not in focal_ids,
            f"duplicate focal_id: {focal_id}",
        )

        require(
            scyon_id not in scyon_ids,
            f"duplicate scyon_id: {scyon_id}",
        )

        require(
            engine_id not in engine_ids,
            f"duplicate engine_id: {engine_id}",
        )

        focal_ids.add(focal_id)
        scyon_ids.add(scyon_id)
        engine_ids.add(engine_id)

        public_names = [
            str(
                instance[
                    "focal_kind"
                ]
            ),
            *[
                str(alias)
                for alias
                in instance[
                    "aliases"
                ]
            ],
        ]

        for alias in public_names:
            previous = aliases.get(
                alias
            )

            require(
                previous is None
                or previous == focal_id,
                (
                    "Focal alias collision: "
                    f"{alias}: "
                    f"{previous} vs {focal_id}"
                ),
            )

            aliases[
                alias
            ] = focal_id


def compile_registry(
) -> dict[str, Any]:
    require(
        KERNEL.is_file(),
        (
            "Scyon kernel unavailable: "
            f"{KERNEL}"
        ),
    )

    (
        sources,
        ignored,
    ) = discover_focal_sources()

    instances = [
        compile_instance(path)
        for path in sources
    ]

    instances.sort(
        key=lambda item: str(
            item["focal_id"]
        )
    )

    validate_registry_uniqueness(
        instances
    )

    source_records = [
        {
            "path": str(path),
            "sha256": sha256_file(
                path
            ),
        }
        for path in sources
    ]

    registry: dict[
        str,
        Any,
    ] = {
        "schema": REGISTRY_SCHEMA,
        "authority_state": "projection",
        "registry_id": (
            "registry:scyon:focals"
        ),
        "generated": True,
        "rebuildable": True,
        "generator": str(
            Path(__file__).resolve()
        ),
        "generator_sha256": (
            sha256_file(
                Path(__file__).resolve()
            )
        ),
        "definition_validator": {
            "path": str(
                FOCAL_VALIDATOR
            ),
            "sha256": sha256_file(
                FOCAL_VALIDATOR
            ),
            "required_for_every_focal": True,
            "service_binding_fail_closed": True,
        },
        "discovery": {
            "root": str(
                FOCAL_ROOT
            ),
            "schema_prefix": (
                FOCAL_SCHEMA_PREFIX
            ),
            "candidate_json_count": len(
                list(
                    FOCAL_ROOT.glob(
                        "*.json"
                    )
                )
            ),
            "focal_definition_count": len(
                sources
            ),
            "ignored": ignored,
        },
        "kernel": {
            "id": "scyon:kernel",
            "path": str(
                KERNEL.resolve()
            ),
            "sha256": sha256_file(
                KERNEL
            ),
            "shared": True,
            "substantiated_once": True,
        },
        "laws": {
            "canonical_substance_may_not_be_duplicated": True,
            "destructive_mutation_authorized": False,
            "focal_is_specialization_not_replacement": True,
            "focal_may_not_reimplement_kernel": True,
            "history_must_be_preserved": True,
            "lineage_must_be_preserved": True,
            "metadata_is_not_automatically_authority": True,
            "physical_migration_authorized": False,
            "projection_is_not_authority": True,
            "provenance_must_be_preserved": True,
            "service_owner_requires_explicit_implemented_through": True,
            "simulation_is_non_authoritative_by_default": True
        },
        "source_set_digest": (
            digest_value(
                source_records
            )
        ),
        "sources": source_records,
        "instances": instances,
    }

    registry[
        "projection_digest"
    ] = digest_value(
        registry
    )

    return registry


def determinism_check(
) -> dict[str, Any]:
    first = compile_registry()
    second = compile_registry()

    require(
        first == second,
        (
            "Focal registry compilation "
            "is not deterministic"
        ),
    )

    return {
        "deterministic": True,
        "schema": first["schema"],
        "focal_count": len(
            first["instances"]
        ),
        "source_set_digest": (
            first[
                "source_set_digest"
            ]
        ),
        "projection_digest": (
            first[
                "projection_digest"
            ]
        ),
        "service_binding_fail_closed": True,
        "physical_migration_authorized": False,
        "destructive_mutation_authorized": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Compile the deterministic "
            "Scyon Focal registry."
        )
    )

    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
    )

    parser.add_argument(
        "command",
        choices=(
            "check",
            "compile",
            "print",
        ),
    )

    arguments = (
        parser.parse_args()
    )

    if arguments.command == "check":
        print(
            json.dumps(
                determinism_check(),
                indent=2,
                sort_keys=True,
            )
        )

        return 0

    first = compile_registry()
    second = compile_registry()

    require(
        first == second,
        (
            "refusing registry write: "
            "second compilation differs"
        ),
    )

    if arguments.command == "print":
        print(
            json.dumps(
                first,
                indent=2,
                sort_keys=True,
            )
        )

        return 0

    output = (
        arguments.output.resolve()
    )

    try:
        output.relative_to(ROOT)

    except ValueError as exc:
        raise RegistryError(
            (
                "registry output escapes "
                f"Savant root: {output}"
            )
        ) from exc

    atomic_json(
        output,
        first,
    )

    written = load_json(
        output
    )

    require(
        written == first,
        (
            "written registry differs "
            "from compiled projection"
        ),
    )

    print(
        json.dumps(
            {
                "compiled": True,
                "schema": first[
                    "schema"
                ],
                "output": str(
                    output
                ),
                "focal_count": len(
                    first[
                        "instances"
                    ]
                ),
                "source_set_digest": (
                    first[
                        "source_set_digest"
                    ]
                ),
                "projection_digest": (
                    first[
                        "projection_digest"
                    ]
                ),
                "service_binding_fail_closed": True,
                "physical_migration_authorized": False,
                "destructive_mutation_authorized": False,
            },
            indent=2,
            sort_keys=True,
        )
    )

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
        json.JSONDecodeError,
        RegistryError,
    ) as exc:
        print(
            (
                "ERROR: "
                f"{type(exc).__name__}: "
                f"{exc}"
            ),
            file=sys.stderr,
        )

        raise SystemExit(1)
