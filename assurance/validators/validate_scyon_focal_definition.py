#!/usr/bin/env python3

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Any


ROOT = Path(
    os.environ.get(
        "SAVANT_ROOT",
        "/root/savant-runtime",
    )
).resolve()

KERNEL = (
    ROOT
    / "runtime/scyon/scyon_kernel.py"
).resolve()

FOCAL_SCHEMA_PREFIX = (
    "savant://runtime/scyon/focal/"
)

OWNER_RECEIPT_SCHEMA_PREFIX = (
    "savant://assurance/scyon-owner-resolution/"
)

SCYON_TIERS = (
    "trait",
    "quirk",
    "prodigal",
    "exile",
    "innate",
    "gate",
    "portal",
    "obelisk",
)

ATOMIC_EXCLUSIONS = {
    "iota",
    "mote",
}

FORBIDDEN_OWNER_PREFIXES = {
    "service",
    "program",
    "rubric",
    "cabal",
    "runtime",
    "projection",
    "report",
}

FORBIDDEN_MUTATIONS = (
    "filesystem_move",
    "filesystem_delete",
    "authority_rewrite",
    "historical_rewrite",
)


class ValidationError(RuntimeError):
    pass


def require(
    condition: bool,
    message: str,
) -> None:
    if not condition:
        raise ValidationError(message)


def sha256_file(
    path: Path,
) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as handle:
        for chunk in iter(
            lambda: handle.read(1024 * 1024),
            b"",
        ):
            digest.update(chunk)

    return digest.hexdigest()


def load_json(
    path: Path,
    label: str,
) -> dict[str, Any]:
    require(
        path.is_absolute(),
        f"{label} path must be absolute: {path}",
    )

    require(
        path.is_file(),
        f"{label} unavailable: {path}",
    )

    require(
        path.stat().st_size > 0,
        f"{label} empty: {path}",
    )

    try:
        value = json.loads(
            path.read_text(
                encoding="utf-8"
            )
        )

    except json.JSONDecodeError as exc:
        raise ValidationError(
            f"invalid {label} JSON: {exc}"
        ) from exc

    require(
        isinstance(value, dict),
        f"{label} root must be object",
    )

    return value


def root_path(
    raw: Any,
    label: str,
    *,
    must_exist: bool,
) -> Path:
    require(
        isinstance(raw, str)
        and bool(raw.strip()),
        f"{label} path missing",
    )

    path = Path(raw).resolve()

    try:
        path.relative_to(ROOT)

    except ValueError as exc:
        raise ValidationError(
            f"{label} escapes Savant root: {path}"
        ) from exc

    if must_exist:
        require(
            path.is_file(),
            f"{label} unavailable: {path}",
        )

    return path


def unique_strings(
    value: Any,
    label: str,
) -> list[str]:
    require(
        isinstance(value, list),
        f"{label} must be array",
    )

    result: list[str] = []

    for item in value:
        require(
            isinstance(item, str)
            and bool(item.strip()),
            f"{label} contains invalid value",
        )

        normalized = item.strip()

        require(
            normalized not in result,
            f"{label} contains duplicate: {normalized}",
        )

        result.append(normalized)

    return result


def validate_owner(
    focal: dict[str, Any],
) -> dict[str, str]:
    owner_id = focal.get("owner_id")
    owner_tier = focal.get("owner_tier")

    require(
        isinstance(owner_id, str)
        and bool(owner_id.strip()),
        "owner_id must be non-empty string",
    )

    require(
        isinstance(owner_tier, str)
        and owner_tier in SCYON_TIERS,
        (
            "owner_tier must be one of: "
            + ", ".join(SCYON_TIERS)
        ),
    )

    parts = owner_id.split(
        ":",
        1,
    )

    require(
        len(parts) == 2,
        (
            "owner_id must use typed identity form "
            "<tier>:<identity>"
        ),
    )

    owner_prefix = parts[0].strip()
    owner_name = parts[1].strip()

    require(
        bool(owner_name),
        "owner identity name is empty",
    )

    require(
        owner_prefix not in ATOMIC_EXCLUSIONS,
        (
            f"{owner_prefix} is atomic and "
            "cannot own a Scyon"
        ),
    )

    require(
        owner_prefix not in FORBIDDEN_OWNER_PREFIXES,
        (
            f"{owner_prefix} is not a "
            "Scyon-bearing identity tier"
        ),
    )

    require(
        owner_prefix in SCYON_TIERS,
        (
            "owner_id prefix is not a "
            "Scyon-bearing tier: "
            f"{owner_prefix}"
        ),
    )

    require(
        owner_prefix == owner_tier,
        (
            "owner_id / owner_tier mismatch: "
            f"{owner_id} declares {owner_tier}"
        ),
    )

    return {
        "owner_id": owner_id,
        "owner_tier": owner_tier,
    }


def validate_service_binding(
    focal: dict[str, Any],
    registration: dict[str, Any],
) -> dict[str, Any] | None:
    binding = registration.get(
        "service_binding"
    )

    if binding is None:
        return None

    require(
        isinstance(binding, dict),
        "registration.service_binding must be object",
    )

    service_id = binding.get(
        "service_id"
    )

    require(
        isinstance(service_id, str)
        and service_id.startswith("service:")
        and len(service_id) > len("service:"),
        (
            "service_binding.service_id must use "
            "service:<identity>"
        ),
    )

    relation = binding.get(
        "owner_relation"
    )

    require(
        relation == "implemented_through",
        (
            "service-backed Scyon ownership must "
            "use implemented_through"
        ),
    )

    receipt_path = root_path(
        binding.get(
            "owner_resolution_receipt"
        ),
        "service_binding.owner_resolution_receipt",
        must_exist=True,
    )

    receipt = load_json(
        receipt_path,
        "owner-resolution receipt",
    )

    schema = receipt.get(
        "schema"
    )

    require(
        isinstance(schema, str)
        and schema.startswith(
            OWNER_RECEIPT_SCHEMA_PREFIX
        ),
        (
            "unsupported owner-resolution "
            f"receipt schema: {schema!r}"
        ),
    )

    require(
        receipt.get("target")
        == service_id,
        (
            "owner-resolution receipt target "
            "does not match service_binding"
        ),
    )

    require(
        receipt.get("resolution")
        == "explicit-owner-found",
        (
            "service-backed Focal requires "
            "resolution=explicit-owner-found"
        ),
    )

    require(
        receipt.get(
            "inference_used"
        )
        is False,
        (
            "service-backed Focal ownership "
            "cannot rely on inference"
        ),
    )

    require(
        receipt.get(
            "semantic_similarity_used"
        )
        is False,
        (
            "service-backed Focal ownership "
            "cannot rely on semantic similarity"
        ),
    )

    require(
        receipt.get(
            "authority_mutation_performed"
        )
        is False,
        (
            "owner-resolution receipt records "
            "authority mutation"
        ),
    )

    require(
        receipt.get(
            "physical_mutation_performed"
        )
        is False,
        (
            "owner-resolution receipt records "
            "physical mutation"
        ),
    )

    resolved_owner = receipt.get(
        "scyon_owner_id"
    )

    resolved_tier = receipt.get(
        "scyon_owner_tier"
    )

    require(
        resolved_owner
        == focal["owner_id"],
        (
            "declared Focal owner does not match "
            "resolved service implementation owner: "
            f"{focal['owner_id']} != {resolved_owner}"
        ),
    )

    require(
        resolved_tier
        == focal["owner_tier"],
        (
            "declared Focal owner tier does not "
            "match resolver receipt: "
            f"{focal['owner_tier']} != {resolved_tier}"
        ),
    )

    candidates = receipt.get(
        "implementation_owner_candidates"
    )

    require(
        isinstance(candidates, list),
        (
            "owner-resolution receipt lacks "
            "implementation_owner_candidates"
        ),
    )

    matching = [
        item
        for item in candidates
        if isinstance(item, dict)
        and item.get("candidate_id")
        == resolved_owner
    ]

    require(
        len(matching) == 1,
        (
            "resolved implementation owner must "
            "have exactly one candidate record"
        ),
    )

    relations = matching[0].get(
        "relations",
        [],
    )

    require(
        isinstance(relations, list)
        and "implemented_through"
        in relations,
        (
            "resolver receipt does not prove "
            "implemented_through relationship"
        ),
    )

    return {
        "service_id": service_id,
        "owner_relation": relation,
        "resolved_owner_id": resolved_owner,
        "resolved_owner_tier": resolved_tier,
        "receipt": str(receipt_path),
        "receipt_sha256": sha256_file(
            receipt_path
        ),
        "verified": True,
    }


def validate_identity(
    focal: dict[str, Any],
) -> dict[str, str]:
    schema = focal.get("schema")

    require(
        isinstance(schema, str)
        and schema.startswith(
            FOCAL_SCHEMA_PREFIX
        ),
        "invalid Focal schema",
    )

    for name in (
        "focal_id",
        "focal_kind",
        "scyon_id",
        "engine_id",
        "archetype",
        "authority_state",
    ):
        require(
            isinstance(
                focal.get(name),
                str,
            )
            and bool(
                focal[name].strip()
            ),
            f"{name} must be non-empty string",
        )

    require(
        focal["focal_id"].startswith(
            "focal:"
        ),
        "focal_id must begin focal:",
    )

    require(
        focal["scyon_id"].startswith(
            "scyon:"
        ),
        "scyon_id must begin scyon:",
    )

    require(
        focal["authority_state"]
        != "projection",
        (
            "projection cannot substantiate "
            "a Focal definition"
        ),
    )

    require(
        focal.get(
            "generated",
            False,
        )
        is not True,
        (
            "generated artifact cannot "
            "substantiate a Focal definition"
        ),
    )

    return validate_owner(
        focal
    )


def validate_abilities(
    focal: dict[str, Any],
) -> None:
    abilities = focal.get(
        "abilities"
    )

    require(
        isinstance(abilities, list),
        "abilities must be array",
    )

    names: set[str] = set()

    for ability in abilities:
        require(
            isinstance(ability, dict),
            "ability must be object",
        )

        name = ability.get("name")

        require(
            isinstance(name, str)
            and bool(name.strip()),
            "ability name missing",
        )

        require(
            name not in names,
            f"duplicate ability: {name}",
        )

        names.add(name)

        minimum_tier = ability.get(
            "minimum_tier"
        )

        require(
            minimum_tier in SCYON_TIERS,
            (
                f"ability {name} has invalid "
                f"minimum_tier: {minimum_tier}"
            ),
        )

        contract = ability.get(
            "contract"
        )

        require(
            isinstance(contract, dict),
            (
                f"ability {name} "
                "contract must be object"
            ),
        )


def validate_equalizer(
    focal: dict[str, Any],
) -> None:
    equalizer = focal.get(
        "equalizer"
    )

    require(
        isinstance(equalizer, dict),
        "equalizer must be object",
    )

    for channel, value in equalizer.items():
        require(
            isinstance(channel, str)
            and bool(channel),
            "equalizer channel invalid",
        )

        require(
            isinstance(value, (int, float))
            and not isinstance(value, bool),
            (
                f"equalizer {channel} "
                "must be numeric"
            ),
        )

        require(
            0.0 <= float(value) <= 1.0,
            (
                f"equalizer {channel} "
                "must be between 0.0 and 1.0"
            ),
        )


def validate_metadata_and_policy(
    focal: dict[str, Any],
) -> None:
    for name in (
        "metadata",
        "policy",
        "integrations",
    ):
        require(
            isinstance(
                focal.get(name),
                dict,
            ),
            f"{name} must be object",
        )

    policy = focal[
        "policy"
    ]

    if (
        "destructive_mutation"
        in policy
    ):
        require(
            policy[
                "destructive_mutation"
            ]
            is False,
            (
                "Focal policy cannot authorize "
                "destructive mutation"
            ),
        )

    if (
        "physical_migration"
        in policy
    ):
        require(
            policy[
                "physical_migration"
            ]
            is False,
            (
                "Focal policy cannot authorize "
                "physical migration"
            ),
        )


def validate_registration(
    focal: dict[str, Any],
) -> dict[str, Any]:
    registration = focal.get(
        "registration"
    )

    require(
        isinstance(registration, dict),
        "registration must be object",
    )

    aliases = unique_strings(
        registration.get(
            "aliases",
            [],
        ),
        "registration.aliases",
    )

    require(
        focal["focal_id"]
        not in aliases,
        (
            "focal_id must not be "
            "duplicated as alias"
        ),
    )

    require(
        focal["focal_kind"]
        not in aliases,
        (
            "focal_kind already supplies "
            "the canonical public alias"
        ),
    )

    runtime = root_path(
        registration.get(
            "runtime"
        ),
        "registration.runtime",
        must_exist=True,
    )

    state = root_path(
        registration.get(
            "state"
        ),
        "registration.state",
        must_exist=False,
    )

    projection = root_path(
        registration.get(
            "projection"
        ),
        "registration.projection",
        must_exist=False,
    )

    surface = registration.get(
        "command_surface"
    )

    require(
        isinstance(surface, dict),
        "command_surface must be object",
    )

    default_runtime = root_path(
        surface.get(
            "default_runtime"
        ),
        "command_surface.default_runtime",
        must_exist=True,
    )

    require(
        runtime == default_runtime,
        (
            "registration.runtime must equal "
            "command_surface.default_runtime"
        ),
    )

    passthrough = unique_strings(
        surface.get(
            "passthrough_commands",
            [],
        ),
        "passthrough_commands",
    )

    routes = surface.get(
        "routes",
        {},
    )

    require(
        isinstance(routes, dict),
        "routes must be object",
    )

    route_targets: set[
        tuple[str, str]
    ] = set()

    for name, route in routes.items():
        require(
            isinstance(name, str)
            and bool(name.strip()),
            "route name invalid",
        )

        require(
            name not in passthrough,
            (
                f"command {name} cannot be both "
                "passthrough and explicit route"
            ),
        )

        require(
            isinstance(route, dict),
            f"route {name} must be object",
        )

        route_runtime = root_path(
            route.get("runtime"),
            f"route {name}.runtime",
            must_exist=True,
        )

        command = route.get(
            "command"
        )

        require(
            isinstance(command, str)
            and bool(command.strip()),
            f"route {name}.command missing",
        )

        target = (
            str(route_runtime),
            command.strip(),
        )

        require(
            target not in route_targets,
            (
                "duplicate route target: "
                f"{target[0]}:{target[1]}"
            ),
        )

        route_targets.add(target)

    composition = registration.get(
        "composes"
    )

    require(
        isinstance(composition, dict),
        "registration.composes must be object",
    )

    normalized_composition: dict[
        str,
        Path,
    ] = {}

    for name, value in composition.items():
        require(
            isinstance(name, str)
            and bool(name.strip()),
            "composition name invalid",
        )

        normalized_composition[
            name
        ] = root_path(
            value,
            f"composition {name}",
            must_exist=True,
        )

    require(
        normalized_composition.get(
            "scyon_kernel"
        )
        == KERNEL,
        (
            "every Focal must compose the "
            "canonical shared Scyon kernel"
        ),
    )

    mutation = registration.get(
        "mutation"
    )

    require(
        isinstance(mutation, dict),
        "registration.mutation must be object",
    )

    for name in FORBIDDEN_MUTATIONS:
        require(
            name in mutation,
            (
                "registration.mutation must "
                f"declare {name}"
            ),
        )

        require(
            mutation[name] is False,
            (
                "forbidden Focal mutation "
                f"enabled: {name}"
            ),
        )

    service_binding = (
        validate_service_binding(
            focal,
            registration,
        )
    )

    return {
        "alias_count": len(
            aliases
        ),
        "passthrough_command_count": len(
            passthrough
        ),
        "route_count": len(
            routes
        ),
        "composition_count": len(
            composition
        ),
        "runtime": str(
            runtime
        ),
        "state": str(
            state
        ),
        "projection": str(
            projection
        ),
        "service_binding": (
            service_binding
        ),
    }


def validate(
    focal: dict[str, Any],
) -> dict[str, Any]:
    owner = validate_identity(
        focal
    )

    validate_abilities(
        focal
    )

    validate_equalizer(
        focal
    )

    validate_metadata_and_policy(
        focal
    )

    registration = (
        validate_registration(
            focal
        )
    )

    enhancements = focal.get(
        "enhancements",
        [],
    )

    require(
        isinstance(enhancements, list),
        "enhancements must be array",
    )

    return {
        "valid": True,
        "focal_id": focal[
            "focal_id"
        ],
        "focal_kind": focal[
            "focal_kind"
        ],
        "scyon_id": focal[
            "scyon_id"
        ],
        "owner": owner,
        "ability_count": len(
            focal["abilities"]
        ),
        "equalizer_channel_count": len(
            focal["equalizer"]
        ),
        "enhancement_count": len(
            enhancements
        ),
        "service_backed": (
            registration[
                "service_binding"
            ]
            is not None
        ),
        "registration": (
            registration
        ),
        "physical_migration_authorized": False,
        "destructive_mutation_authorized": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Validate one Scyon Focal "
            "specialization definition."
        )
    )

    parser.add_argument(
        "definition",
        type=Path,
    )

    arguments = (
        parser.parse_args()
    )

    try:
        path = (
            arguments.definition.resolve()
        )

        focal = load_json(
            path,
            "Focal definition",
        )

        result = validate(
            focal
        )

    except (
        OSError,
        ValueError,
        KeyError,
        json.JSONDecodeError,
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

    print(
        json.dumps(
            result,
            indent=2,
            sort_keys=True,
        )
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
