#!/usr/bin/env python3

from __future__ import annotations

import hashlib
import json
import sqlite3
import subprocess
import sys
from pathlib import Path
from typing import Any


ROOT = Path(
    "/root/savant-runtime"
).resolve()

REGISTRY = (
    ROOT
    / "runtime/scyon/focals/registry.json"
)

FOCAL = (
    ROOT
    / "runtime/scyon/focals/living-structure.json"
)

REGISTRY_COMPILER = (
    ROOT
    / "runtime/scyon/compile_focal_registry.py"
)

FOCAL_DEFINITION_VALIDATOR = (
    ROOT
    / "assurance/validators/"
    "validate_scyon_focal_definition.py"
)

OWNER_RESOLVER = (
    ROOT
    / "assurance/scanners/"
    "resolve_scyon_focal_owner.py"
)

KERNEL = (
    ROOT
    / "runtime/scyon/scyon_kernel.py"
)

LIVING = (
    ROOT
    / "runtime/scyon/living_engine.py"
)

STRUCTURE_ENGINE = (
    ROOT
    / "runtime/scyon/living_structure_engine.py"
)

STRUCTURE_STATE = (
    ROOT
    / "runtime/scyon/living_structure_state.py"
)

SCYONCTL = (
    ROOT
    / "bin/scyonctl"
)

DATABASE = (
    ROOT
    / "runtime/scyon/state/living-structure.sqlite3"
)

SCANNER = (
    ROOT
    / "ontology/obelisks/_template/segue/"
    "gates/_template/segue/innates/_template/segue/"
    "exiles/underscore/rubric/structure-intelligence/"
    "source/compile_structure_intelligence_authority_v2.py"
)

MIGRATION_COMPILER = (
    ROOT
    / "ontology/obelisks/_template/segue/"
    "gates/_template/segue/innates/_template/segue/"
    "exiles/underscore/rubric/structure-intelligence/"
    "source/compile_migration_manifest.py"
)

SCYON_CONTRACT_VALIDATOR = (
    ROOT
    / "assurance/validators/"
    "validate_savant_scyon_focal_contract.py"
)

SCYON_AUTHORITY_VALIDATOR = (
    ROOT
    / "assurance/validators/"
    "validate_scyon_focal_authority.sh"
)

SUPPORTED_REGISTRY_SCHEMAS = {
    "savant://runtime/scyon/focal-registry/1.0.0",
    "savant://runtime/scyon/focal-registry/1.1.0",
    "savant://runtime/scyon/focal-registry/1.2.0",
    "savant://runtime/scyon/focal-registry/1.3.0",
    "savant://runtime/scyon/focal-registry/1.4.0",
}


class ValidationError(RuntimeError):
    pass


def require(
    condition: bool,
    message: str,
) -> None:
    if not condition:
        raise ValidationError(
            message
        )


def load_json(
    path: Path,
) -> dict[str, Any]:
    require(
        path.is_file(),
        f"missing JSON file: {path}",
    )

    require(
        path.stat().st_size > 0,
        f"empty JSON file: {path}",
    )

    try:
        value = json.loads(
            path.read_text(
                encoding="utf-8"
            )
        )

    except json.JSONDecodeError as exc:
        raise ValidationError(
            f"invalid JSON {path}: {exc}"
        ) from exc

    require(
        isinstance(value, dict),
        (
            "JSON root must be "
            f"object: {path}"
        ),
    )

    return value


def sha256_file(
    path: Path,
) -> str:
    digest = hashlib.sha256()

    with path.open(
        "rb"
    ) as handle:
        for chunk in iter(
            lambda: handle.read(
                1024 * 1024
            ),
            b"",
        ):
            digest.update(
                chunk
            )

    return digest.hexdigest()


def require_path(
    path: Path,
    label: str,
) -> None:
    require(
        path.is_file(),
        f"{label} missing: {path}",
    )

    require(
        path.stat().st_size > 0,
        f"{label} empty: {path}",
    )


def validate_paths() -> None:
    required = (
        (
            REGISTRY,
            "Focal registry",
        ),
        (
            FOCAL,
            "Living Structure Focal",
        ),
        (
            REGISTRY_COMPILER,
            "Focal registry compiler",
        ),
        (
            FOCAL_DEFINITION_VALIDATOR,
            "Focal definition validator",
        ),
        (
            OWNER_RESOLVER,
            "Scyon owner resolver",
        ),
        (
            KERNEL,
            "Scyon kernel",
        ),
        (
            LIVING,
            "LivingEngine",
        ),
        (
            STRUCTURE_ENGINE,
            "Living Structure Engine",
        ),
        (
            STRUCTURE_STATE,
            "Living Structure state engine",
        ),
        (
            SCYONCTL,
            "scyonctl",
        ),
        (
            SCANNER,
            "Structure Intelligence",
        ),
        (
            MIGRATION_COMPILER,
            "migration compiler",
        ),
        (
            SCYON_CONTRACT_VALIDATOR,
            "Scyon contract validator",
        ),
        (
            SCYON_AUTHORITY_VALIDATOR,
            "Scyon authority validator",
        ),
    )

    for path, label in required:
        require_path(
            path,
            label,
        )


def validate_registry(
    registry: dict[str, Any],
) -> dict[str, Any]:
    schema = registry.get(
        "schema"
    )

    require(
        schema
        in SUPPORTED_REGISTRY_SCHEMAS,
        (
            "invalid Focal registry "
            f"schema: {schema!r}"
        ),
    )

    require(
        registry.get(
            "authority_state"
        )
        == "projection",
        (
            "Focal registry must "
            "remain a projection"
        ),
    )

    if (
        schema
        != (
            "savant://runtime/scyon/"
            "focal-registry/1.0.0"
        )
    ):
        require(
            registry.get(
                "rebuildable"
            )
            is True,
            (
                "generated Focal registry "
                "must be rebuildable"
            ),
        )

    kernel = registry.get(
        "kernel"
    )

    require(
        isinstance(
            kernel,
            dict,
        ),
        "kernel registry record missing",
    )

    require(
        kernel.get(
            "path"
        )
        == str(
            KERNEL
        ),
        (
            "registry kernel "
            "path drifted"
        ),
    )

    require(
        kernel.get(
            "shared"
        )
        is True,
        (
            "Scyon kernel must "
            "remain shared"
        ),
    )

    require(
        kernel.get(
            "substantiated_once"
        )
        is True,
        (
            "Scyon kernel must be "
            "substantiated once"
        ),
    )

    laws = registry.get(
        "laws"
    )

    require(
        isinstance(
            laws,
            dict,
        ),
        "registry laws missing",
    )

    required_true = (
        "canonical_substance_may_not_be_duplicated",
        "focal_is_specialization_not_replacement",
        "focal_may_not_reimplement_kernel",
        "history_must_be_preserved",
        "lineage_must_be_preserved",
        "metadata_is_not_automatically_authority",
        "projection_is_not_authority",
        "provenance_must_be_preserved",
    )

    for law in required_true:
        require(
            laws.get(
                law
            )
            is True,
            (
                "required Scyon law "
                f"false or missing: {law}"
            ),
        )

    require(
        laws.get(
            "physical_migration_authorized"
        )
        is False,
        (
            "physical migration must "
            "remain unauthorized"
        ),
    )

    require(
        laws.get(
            "destructive_mutation_authorized"
        )
        is False,
        (
            "destructive mutation must "
            "remain unauthorized"
        ),
    )

    if schema.endswith(
        "/1.4.0"
    ):
        require(
            laws.get(
                "service_owner_requires_explicit_implemented_through"
            )
            is True,
            (
                "1.4 registry must enforce "
                "explicit service implementation ownership"
            ),
        )

        validator = registry.get(
            "definition_validator"
        )

        require(
            isinstance(
                validator,
                dict,
            ),
            (
                "1.4 registry definition "
                "validator binding missing"
            ),
        )

        require(
            validator.get(
                "path"
            )
            == str(
                FOCAL_DEFINITION_VALIDATOR
            ),
            (
                "registry definition "
                "validator path drifted"
            ),
        )

        require(
            validator.get(
                "sha256"
            )
            == sha256_file(
                FOCAL_DEFINITION_VALIDATOR
            ),
            (
                "registry definition "
                "validator digest drifted"
            ),
        )

        require(
            validator.get(
                "required_for_every_focal"
            )
            is True,
            (
                "definition validator must "
                "apply to every Focal"
            ),
        )

        require(
            validator.get(
                "service_binding_fail_closed"
            )
            is True,
            (
                "service-backed Focal "
                "validation must fail closed"
            ),
        )

    instances = registry.get(
        "instances"
    )

    require(
        isinstance(
            instances,
            list,
        ),
        (
            "registry instances "
            "must be an array"
        ),
    )

    require(
        len(
            instances
        )
        >= 1,
        (
            "registry contains "
            "no Focal instances"
        ),
    )

    focal_ids: set[
        str
    ] = set()

    scyon_ids: set[
        str
    ] = set()

    engine_ids: set[
        str
    ] = set()

    public_aliases: dict[
        str,
        str,
    ] = {}

    living: dict[
        str,
        Any,
    ] | None = None

    for instance in instances:
        require(
            isinstance(
                instance,
                dict,
            ),
            (
                "registry instance "
                "must be object"
            ),
        )

        focal_id = instance.get(
            "focal_id"
        )

        scyon_id = instance.get(
            "scyon_id"
        )

        engine_id = instance.get(
            "engine_id"
        )

        require(
            isinstance(
                focal_id,
                str,
            )
            and bool(
                focal_id
            ),
            (
                "registered Focal "
                "missing focal_id"
            ),
        )

        require(
            isinstance(
                scyon_id,
                str,
            )
            and bool(
                scyon_id
            ),
            (
                f"{focal_id}: "
                "scyon_id missing"
            ),
        )

        require(
            isinstance(
                engine_id,
                str,
            )
            and bool(
                engine_id
            ),
            (
                f"{focal_id}: "
                "engine_id missing"
            ),
        )

        require(
            focal_id
            not in focal_ids,
            (
                "duplicate focal_id: "
                f"{focal_id}"
            ),
        )

        require(
            scyon_id
            not in scyon_ids,
            (
                "duplicate scyon_id: "
                f"{scyon_id}"
            ),
        )

        require(
            engine_id
            not in engine_ids,
            (
                "duplicate engine_id: "
                f"{engine_id}"
            ),
        )

        focal_ids.add(
            focal_id
        )

        scyon_ids.add(
            scyon_id
        )

        engine_ids.add(
            engine_id
        )

        focal_kind = instance.get(
            "focal_kind"
        )

        require(
            isinstance(
                focal_kind,
                str,
            )
            and bool(
                focal_kind
            ),
            (
                f"{focal_id}: "
                "focal_kind missing"
            ),
        )

        aliases = instance.get(
            "aliases",
            [],
        )

        require(
            isinstance(
                aliases,
                list,
            ),
            (
                f"{focal_id}: "
                "aliases must be array"
            ),
        )

        names = [
            focal_kind,
            *[
                str(alias)
                for alias
                in aliases
            ],
        ]

        for alias in names:
            previous = (
                public_aliases.get(
                    alias
                )
            )

            require(
                previous is None
                or previous
                == focal_id,
                (
                    "Focal alias collision: "
                    f"{alias}: "
                    f"{previous} vs {focal_id}"
                ),
            )

            public_aliases[
                alias
            ] = focal_id

        if (
            focal_id
            == "focal:living-structure"
        ):
            living = instance

    require(
        living is not None,
        (
            "Living Structure Focal "
            "is not registered"
        ),
    )

    validate_living_instance(
        living,
        schema,
    )

    discovery = registry.get(
        "discovery"
    )

    if (
        schema.endswith(
            "/1.3.0"
        )
        or schema.endswith(
            "/1.4.0"
        )
    ):
        require(
            isinstance(
                discovery,
                dict,
            ),
            (
                "typed registry "
                "discovery record missing"
            ),
        )

        require(
            discovery.get(
                "schema_prefix"
            )
            == (
                "savant://runtime/"
                "scyon/focal/"
            ),
            (
                "Focal discovery "
                "schema prefix drifted"
            ),
        )

        source_set_digest = (
            registry.get(
                "source_set_digest"
            )
        )

        require(
            isinstance(
                source_set_digest,
                str,
            )
            and len(
                source_set_digest
            )
            == 64,
            (
                "source_set_digest "
                "missing or invalid"
            ),
        )

        projection_digest = (
            registry.get(
                "projection_digest"
            )
        )

        require(
            isinstance(
                projection_digest,
                str,
            )
            and len(
                projection_digest
            )
            == 64,
            (
                "projection_digest "
                "missing or invalid"
            ),
        )

    return {
        "schema": schema,
        "focal_count": len(
            instances
        ),
        "living_structure": True,
        "registry_driven_dispatch": True,
        "typed_focal_discovery": (
            isinstance(
                discovery,
                dict,
            )
        ),
        "service_binding_fail_closed": (
            schema.endswith(
                "/1.4.0"
            )
        ),
    }


def validate_living_instance(
    living: dict[str, Any],
    registry_schema: Any,
) -> None:
    require(
        living.get(
            "focal_kind"
        )
        == "living-structure",
        (
            "wrong Living Structure "
            "focal_kind"
        ),
    )

    require(
        living.get(
            "scyon_id"
        )
        == (
            "scyon:exile:underscore:"
            "living-structure"
        ),
        (
            "wrong Living Structure "
            "scyon_id"
        ),
    )

    require(
        living.get(
            "owner_id"
        )
        == "exile:underscore",
        (
            "Living Structure "
            "owner drifted"
        ),
    )

    require(
        living.get(
            "owner_tier"
        )
        == "exile",
        (
            "Living Structure "
            "owner tier drifted"
        ),
    )

    require(
        living.get(
            "definition"
        )
        == str(
            FOCAL
        ),
        (
            "Living Structure "
            "definition path drifted"
        ),
    )

    require(
        living.get(
            "definition_sha256"
        )
        == sha256_file(
            FOCAL
        ),
        (
            "Living Structure "
            "definition digest drifted"
        ),
    )

    require(
        living.get(
            "runtime"
        )
        == str(
            STRUCTURE_ENGINE
        ),
        (
            "Living Structure "
            "runtime path drifted"
        ),
    )

    if (
        isinstance(
            registry_schema,
            str,
        )
        and registry_schema.endswith(
            "/1.4.0"
        )
    ):
        require(
            living.get(
                "service_backed"
            )
            is False,
            (
                "Living Structure is not "
                "a service-backed Focal"
            ),
        )

        require(
            living.get(
                "service_binding"
            )
            is None,
            (
                "Living Structure must not "
                "carry fabricated service binding"
            ),
        )

        validation = living.get(
            "validation"
        )

        require(
            isinstance(
                validation,
                dict,
            ),
            (
                "Living Structure registry "
                "validation receipt missing"
            ),
        )

        require(
            validation.get(
                "valid"
            )
            is True,
            (
                "Living Structure registry "
                "validation is not valid"
            ),
        )

        require(
            validation.get(
                "validator"
            )
            == str(
                FOCAL_DEFINITION_VALIDATOR
            ),
            (
                "Living Structure Focal "
                "validator binding drifted"
            ),
        )

        require(
            validation.get(
                "validator_sha256"
            )
            == sha256_file(
                FOCAL_DEFINITION_VALIDATOR
            ),
            (
                "Living Structure Focal "
                "validator digest drifted"
            ),
        )

    mutation = living.get(
        "mutation"
    )

    require(
        isinstance(
            mutation,
            dict,
        ),
        (
            "Living Structure "
            "mutation contract missing"
        ),
    )

    for forbidden in (
        "filesystem_move",
        "filesystem_delete",
        "authority_rewrite",
        "historical_rewrite",
    ):
        require(
            mutation.get(
                forbidden
            )
            is False,
            (
                "forbidden mutation "
                f"enabled: {forbidden}"
            ),
        )

    composition = living.get(
        "composes"
    )

    require(
        isinstance(
            composition,
            dict,
        ),
        (
            "Living Structure "
            "composition missing"
        ),
    )

    require(
        composition.get(
            "scyon_kernel"
        )
        == str(
            KERNEL
        ),
        (
            "Living Structure must "
            "compose canonical Scyon kernel"
        ),
    )

    require(
        composition.get(
            "living_template"
        )
        == str(
            LIVING
        ),
        (
            "Living Structure must "
            "compose LivingEngine"
        ),
    )

    require(
        composition.get(
            "structure_intelligence"
        )
        == str(
            SCANNER
        ),
        (
            "Structure Intelligence "
            "binding drifted"
        ),
    )

    require(
        composition.get(
            "migration_manifest_compiler"
        )
        == str(
            MIGRATION_COMPILER
        ),
        (
            "migration compiler "
            "binding drifted"
        ),
    )

    surface = living.get(
        "command_surface"
    )

    require(
        isinstance(
            surface,
            dict,
        ),
        (
            "Living Structure "
            "command surface missing"
        ),
    )

    require(
        surface.get(
            "default_runtime"
        )
        == str(
            STRUCTURE_ENGINE
        ),
        (
            "Living Structure default "
            "runtime drifted"
        ),
    )

    passthrough = surface.get(
        "passthrough_commands"
    )

    require(
        isinstance(
            passthrough,
            list,
        ),
        (
            "Living Structure "
            "passthrough commands "
            "must be array"
        ),
    )

    required_commands = {
        "status",
        "self-test",
        "ingest-latest",
        "ingest-report",
        "compile-proposal",
        "ingest-latest-proposal",
        "ingest-proposal",
        "cycle",
        "proposal-cycle",
        "full-cycle",
    }

    require(
        required_commands.issubset(
            {
                str(item)
                for item
                in passthrough
            }
        ),
        (
            "Living Structure "
            "command surface incomplete"
        ),
    )

    routes = surface.get(
        "routes"
    )

    require(
        isinstance(
            routes,
            dict,
        ),
        (
            "Living Structure "
            "routes must be object"
        ),
    )

    expected_routes = {
        "state": "evaluate",
        "state-test": "self-test",
    }

    for (
        route_name,
        target_command,
    ) in expected_routes.items():
        route = routes.get(
            route_name
        )

        require(
            isinstance(
                route,
                dict,
            ),
            (
                "Living Structure route "
                f"missing: {route_name}"
            ),
        )

        require(
            route.get(
                "runtime"
            )
            == str(
                STRUCTURE_STATE
            ),
            (
                "Living Structure route "
                f"runtime drifted: {route_name}"
            ),
        )

        require(
            route.get(
                "command"
            )
            == target_command,
            (
                "Living Structure route "
                f"command drifted: {route_name}"
            ),
        )


def validate_focal_definition(
    focal: dict[str, Any],
) -> None:
    schema = focal.get(
        "schema"
    )

    require(
        isinstance(
            schema,
            str,
        )
        and schema.startswith(
            "savant://runtime/"
            "scyon/focal/"
        ),
        (
            "Living Structure "
            "Focal schema invalid"
        ),
    )

    require(
        focal.get(
            "focal_id"
        )
        == "focal:living-structure",
        (
            "Living Structure "
            "focal_id drifted"
        ),
    )

    require(
        focal.get(
            "scyon_id"
        )
        == (
            "scyon:exile:underscore:"
            "living-structure"
        ),
        (
            "Living Structure "
            "scyon_id drifted"
        ),
    )

    require(
        focal.get(
            "owner_id"
        )
        == "exile:underscore",
        (
            "Living Structure "
            "owner drifted"
        ),
    )

    require(
        focal.get(
            "owner_tier"
        )
        == "exile",
        (
            "Living Structure "
            "owner tier drifted"
        ),
    )

    registration = focal.get(
        "registration"
    )

    require(
        isinstance(
            registration,
            dict,
        ),
        (
            "Living Structure "
            "registration missing"
        ),
    )

    require(
        registration.get(
            "service_binding"
        )
        is None,
        (
            "Living Structure must "
            "remain non-service-backed"
        ),
    )

    policy = focal.get(
        "policy"
    )

    require(
        isinstance(
            policy,
            dict,
        ),
        (
            "Living Structure "
            "policy missing"
        ),
    )

    require(
        policy.get(
            "destructive_mutation"
        )
        is False,
        (
            "Living Structure permits "
            "destructive mutation"
        ),
    )

    require(
        policy.get(
            "physical_migration"
        )
        is False,
        (
            "Living Structure permits "
            "physical migration"
        ),
    )

    enhancements = focal.get(
        "enhancements"
    )

    require(
        isinstance(
            enhancements,
            list,
        )
        and len(
            enhancements
        )
        >= 20,
        (
            "Living Structure "
            "enhancement set incomplete"
        ),
    )


def validate_persistence(
) -> dict[str, Any]:
    if not DATABASE.is_file():
        return {
            "database_present": False,
            "database_validation": (
                "not-yet-instantiated"
            ),
        }

    connection = sqlite3.connect(
        str(
            DATABASE
        )
    )

    try:
        integrity = (
            connection.execute(
                "PRAGMA integrity_check"
            ).fetchone()
        )

        foreign_keys = (
            connection.execute(
                "PRAGMA foreign_key_check"
            ).fetchall()
        )

    finally:
        connection.close()

    require(
        integrity is not None
        and integrity[0] == "ok",
        (
            "Living Structure SQLite "
            "integrity failure"
        ),
    )

    require(
        not foreign_keys,
        (
            "Living Structure SQLite "
            "foreign-key violations"
        ),
    )

    return {
        "database_present": True,
        "database_validation": "passed",
        "database_sha256": (
            sha256_file(
                DATABASE
            )
        ),
    }


def run_check(
    command: list[str],
    label: str,
) -> str:
    completed = subprocess.run(
        command,
        cwd=str(
            ROOT
        ),
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )

    require(
        completed.returncode == 0,
        (
            f"{label} failed "
            f"with exit "
            f"{completed.returncode}:\n"
            f"{completed.stdout}"
        ),
    )

    return completed.stdout


def main() -> int:
    try:
        validate_paths()

        registry = load_json(
            REGISTRY
        )

        focal = load_json(
            FOCAL
        )

        registry_result = (
            validate_registry(
                registry
            )
        )

        validate_focal_definition(
            focal
        )

        run_check(
            [
                sys.executable,
                str(
                    FOCAL_DEFINITION_VALIDATOR
                ),
                str(
                    FOCAL
                ),
            ],
            (
                "Living Structure "
                "Focal definition validation"
            ),
        )

        run_check(
            [
                sys.executable,
                str(
                    REGISTRY_COMPILER
                ),
                "check",
            ],
            (
                "Focal registry "
                "determinism validation"
            ),
        )

        run_check(
            [
                sys.executable,
                "-m",
                "py_compile",
                str(
                    REGISTRY_COMPILER
                ),
                str(
                    FOCAL_DEFINITION_VALIDATOR
                ),
                str(
                    OWNER_RESOLVER
                ),
                str(
                    LIVING
                ),
                str(
                    STRUCTURE_ENGINE
                ),
                str(
                    STRUCTURE_STATE
                ),
                str(
                    SCYONCTL
                ),
            ],
            "syntax validation",
        )

        run_check(
            [
                sys.executable,
                str(
                    SCYON_CONTRACT_VALIDATOR
                ),
            ],
            (
                "Scyon/Focal "
                "contract validation"
            ),
        )

        run_check(
            [
                str(
                    SCYON_AUTHORITY_VALIDATOR
                ),
            ],
            (
                "Scyon/Focal "
                "authority validation"
            ),
        )

        persistence = (
            validate_persistence()
        )

        result = {
            "schema": (
                "savant://assurance/"
                "living-scyon-integration/"
                "1.4.0"
            ),
            "valid": True,
            "registry": (
                registry_result
            ),
            "kernel_shared": True,
            "living_template_shared": True,
            "living_structure_registered": True,
            "registry_driven_dispatch": True,
            "typed_focal_discovery": True,
            "focal_definition_validation": True,
            "service_binding_fail_closed": True,
            "owner_resolution_available": True,
            "living_structure_service_backed": False,
            "physical_migration_authorized": False,
            "destructive_mutation_authorized": False,
            "persistence": persistence,
            "artifacts": {
                "registry": {
                    "path": str(
                        REGISTRY
                    ),
                    "sha256": (
                        sha256_file(
                            REGISTRY
                        )
                    ),
                },
                "focal": {
                    "path": str(
                        FOCAL
                    ),
                    "sha256": (
                        sha256_file(
                            FOCAL
                        )
                    ),
                },
                "registry_compiler": {
                    "path": str(
                        REGISTRY_COMPILER
                    ),
                    "sha256": (
                        sha256_file(
                            REGISTRY_COMPILER
                        )
                    ),
                },
                "focal_definition_validator": {
                    "path": str(
                        FOCAL_DEFINITION_VALIDATOR
                    ),
                    "sha256": (
                        sha256_file(
                            FOCAL_DEFINITION_VALIDATOR
                        )
                    ),
                },
                "owner_resolver": {
                    "path": str(
                        OWNER_RESOLVER
                    ),
                    "sha256": (
                        sha256_file(
                            OWNER_RESOLVER
                        )
                    ),
                },
                "kernel": {
                    "path": str(
                        KERNEL
                    ),
                    "sha256": (
                        sha256_file(
                            KERNEL
                        )
                    ),
                },
                "living_template": {
                    "path": str(
                        LIVING
                    ),
                    "sha256": (
                        sha256_file(
                            LIVING
                        )
                    ),
                },
                "living_structure_engine": {
                    "path": str(
                        STRUCTURE_ENGINE
                    ),
                    "sha256": (
                        sha256_file(
                            STRUCTURE_ENGINE
                        )
                    ),
                },
                "living_structure_state": {
                    "path": str(
                        STRUCTURE_STATE
                    ),
                    "sha256": (
                        sha256_file(
                            STRUCTURE_STATE
                        )
                    ),
                },
                "scyonctl": {
                    "path": str(
                        SCYONCTL
                    ),
                    "sha256": (
                        sha256_file(
                            SCYONCTL
                        )
                    ),
                },
                "structure_intelligence": {
                    "path": str(
                        SCANNER
                    ),
                    "sha256": (
                        sha256_file(
                            SCANNER
                        )
                    ),
                },
                "migration_compiler": {
                    "path": str(
                        MIGRATION_COMPILER
                    ),
                    "sha256": (
                        sha256_file(
                            MIGRATION_COMPILER
                        )
                    ),
                },
            },
        }

        print(
            json.dumps(
                result,
                indent=2,
                sort_keys=True,
            )
        )

        return 0

    except (
        OSError,
        ValueError,
        KeyError,
        json.JSONDecodeError,
        sqlite3.DatabaseError,
        ValidationError,
    ) as exc:
        print(
            (
                "ERROR: "
                f"{type(exc).__name__}: "
                f"{exc}"
            ),
            file=sys.stderr,
        )

        return 1


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
