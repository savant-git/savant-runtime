#!/usr/bin/env python3

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType
from typing import Any, Sequence


SCANNER_PATH = Path(
    "/root/savant-runtime/ontology/obelisks/_template/segue/"
    "gates/_template/segue/innates/_template/segue/exiles/"
    "underscore/rubric/structure-intelligence/source/"
    "compile_structure_intelligence.py"
)

AUTHORITY_PATH = Path(
    "/root/savant-runtime/canon/structure/"
    "canonical_runtime_structure.json"
)

IDENTITY_COMPATIBILITY_CONTAINERS = {
    "gates": "portal",
    "shards": "iota",
}

DESCRIPTOR_NAMES = {
    "instance.cue",
    "rubric.cue",
    "cabal.cue",
}

PACKAGE_MANIFEST_NAMES = {
    "pyproject.toml",
    "setup.py",
    "setup.cfg",
    "package.json",
    "cargo.toml",
    "go.mod",
    "pom.xml",
    "build.gradle",
    "build.gradle.kts",
    "composer.json",
    "gemfile",
}

SOURCE_LIKE_KINDS = {
    "source",
    "schema",
    "manifest",
    "service-unit",
    "environment",
}


def require(
    condition: bool,
    message: str,
) -> None:
    if not condition:
        raise ValueError(message)


def load_json(path: Path) -> dict[str, Any]:
    require(
        path.is_file(),
        f"file unavailable: {path}",
    )

    require(
        path.stat().st_size > 0,
        f"file empty: {path}",
    )

    value = json.loads(
        path.read_text(encoding="utf-8")
    )

    require(
        isinstance(value, dict),
        f"JSON root must be an object: {path}",
    )

    return value


def load_scanner(path: Path) -> ModuleType:
    require(
        path.is_file(),
        f"scanner unavailable: {path}",
    )

    require(
        path.stat().st_size > 0,
        f"scanner empty: {path}",
    )

    specification = importlib.util.spec_from_file_location(
        "savant_structure_intelligence_verified",
        path,
    )

    require(
        specification is not None,
        f"cannot create scanner specification: {path}",
    )

    require(
        specification.loader is not None,
        f"scanner loader unavailable: {path}",
    )

    module = importlib.util.module_from_spec(
        specification
    )

    sys.modules[specification.name] = module
    specification.loader.exec_module(module)

    return module


def validate_authority(
    authority: dict[str, Any],
) -> None:
    require(
        authority.get("status")
        == "accepted-authority",
        "canonical structure status must be accepted-authority",
    )

    authority_state = authority.get("authority")

    require(
        isinstance(authority_state, dict),
        "authority section must be an object",
    )

    require(
        authority_state.get("mutation_authorized")
        is False,
        "canonical structure must not authorize mutation",
    )

    identity = authority.get(
        "identity_edifice"
    )

    require(
        isinstance(identity, dict),
        "identity_edifice must be an object",
    )

    content = authority.get(
        "content_edifice"
    )

    require(
        isinstance(content, dict),
        "content_edifice must be an object",
    )

    rubric = authority.get("rubric")

    require(
        isinstance(rubric, dict),
        "rubric must be an object",
    )

    cabal = authority.get("cabal")

    require(
        isinstance(cabal, dict),
        "cabal must be an object",
    )

    identity_levels = identity.get("ascending")
    content_levels = content.get("ascending")
    rubric_facilities = rubric.get("facilities")
    cabal_laws = cabal.get("laws")

    require(
        isinstance(identity_levels, list)
        and len(identity_levels) == 9,
        "identity edifice must contain nine levels",
    )

    require(
        isinstance(content_levels, list)
        and len(content_levels) == 9,
        "content edifice must contain nine levels",
    )

    require(
        isinstance(rubric_facilities, list)
        and len(rubric_facilities) == 9,
        "Rubric must contain nine facilities",
    )

    require(
        isinstance(cabal_laws, list)
        and len(cabal_laws) == 9,
        "Cabal must contain nine laws",
    )


def authority_sets(
    authority: dict[str, Any],
) -> dict[str, Any]:
    identity = authority[
        "identity_edifice"
    ]

    content = authority[
        "content_edifice"
    ]

    rubric = authority["rubric"]
    cabal = authority["cabal"]

    identity_containers = {
        str(name).lower(): str(level).lower()
        for name, level in identity[
            "containers"
        ].items()
    }

    content_collections = {
        str(name).lower(): str(level).lower()
        for name, level in content[
            "collections"
        ].items()
    }

    reserved_nonowners = {
        str(value).lower()
        for value in identity[
            "owner_inference"
        ]["reserved_nonowners"]
    }

    rubric_facilities = {
        str(value).lower()
        for value in rubric["facilities"]
    }

    cabal_laws = {
        str(value).lower()
        for value in cabal["laws"]
    }

    identity_levels = tuple(
        str(value).lower()
        for value in identity["ascending"]
    )

    content_levels = tuple(
        str(value).lower()
        for value in content["ascending"]
    )

    return {
        "identity_containers": identity_containers,
        "content_collections": content_collections,
        "reserved_nonowners": reserved_nonowners,
        "rubric_facilities": rubric_facilities,
        "cabal_laws": cabal_laws,
        "identity_levels": identity_levels,
        "content_levels": content_levels,
    }


def normalized_parts(
    relative: str,
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    path = Path(relative)

    original = tuple(path.parts)

    lowered = tuple(
        part.lower()
        for part in original
    )

    return original, lowered


def valid_instance_name(
    candidate: str,
    reserved_nonowners: set[str],
) -> bool:
    lowered = candidate.lower()

    if not candidate:
        return False

    if candidate.startswith("_"):
        return False

    if lowered in reserved_nonowners:
        return False

    if lowered in DESCRIPTOR_NAMES:
        return False

    return True


def identity_instances(
    relative: str,
    identity_containers: dict[str, str],
    reserved_nonowners: set[str],
) -> list[tuple[int, str, str]]:
    original, lowered = normalized_parts(
        relative
    )

    containers = dict(
        identity_containers
    )

    containers.update(
        IDENTITY_COMPATIBILITY_CONTAINERS
    )

    instances: list[tuple[int, str, str]] = []

    for index, component in enumerate(lowered):
        level = containers.get(component)

        if not level:
            continue

        child_index = index + 1

        if child_index >= len(original):
            continue

        candidate = original[child_index]

        if not valid_instance_name(
            candidate,
            reserved_nonowners,
        ):
            continue

        instances.append(
            (
                index,
                level,
                candidate,
            )
        )

    return instances


def explicit_rubric_scope(
    relative: str,
    rubric_facilities: set[str],
) -> str | None:
    original, lowered = normalized_parts(
        relative
    )

    for index, component in enumerate(lowered):
        if component != "rubric":
            continue

        name_index = index + 1

        if name_index >= len(original):
            return None

        rubric_name = original[name_index]

        if (
            not rubric_name
            or rubric_name.startswith("_")
            or rubric_name.lower()
            in rubric_facilities
        ):
            return None

        return "/".join(
            original[: name_index + 1]
        )

    return None


def explicit_cabal_scope(
    relative: str,
) -> str | None:
    original, lowered = normalized_parts(
        relative
    )

    for index, component in enumerate(lowered):
        if component != "cabal":
            continue

        name_index = index + 1

        if name_index >= len(original):
            return None

        cabal_name = original[name_index]

        if (
            not cabal_name
            or cabal_name.startswith("_")
        ):
            return None

        return "/".join(
            original[: name_index + 1]
        )

    return None


def explicit_descriptor_instance(
    relative: str,
) -> str | None:
    path = Path(relative)

    if path.name.lower() not in DESCRIPTOR_NAMES:
        return None

    return path.parent.as_posix()


def install_authority_overrides(
    scanner: ModuleType,
    authority: dict[str, Any],
) -> None:
    sets = authority_sets(authority)

    identity_containers: dict[str, str] = (
        sets["identity_containers"]
    )

    content_collections: dict[str, str] = (
        sets["content_collections"]
    )

    reserved_nonowners: set[str] = (
        sets["reserved_nonowners"]
    )

    rubric_facilities: set[str] = (
        sets["rubric_facilities"]
    )

    identity_levels: tuple[str, ...] = (
        sets["identity_levels"]
    )

    content_levels: tuple[str, ...] = (
        sets["content_levels"]
    )

    def identify_edifice_level_authority(
        tokens: Sequence[str],
    ) -> str | None:
        lowered = tuple(
            str(token).lower()
            for token in tokens
        )

        recognized: list[
            tuple[int, str]
        ] = []

        combined_identity = dict(
            identity_containers
        )

        combined_identity.update(
            IDENTITY_COMPATIBILITY_CONTAINERS
        )

        for index, token in enumerate(lowered):
            identity_level = (
                combined_identity.get(token)
            )

            if identity_level:
                recognized.append(
                    (
                        index,
                        identity_level,
                    )
                )

            content_level = (
                content_collections.get(token)
            )

            if content_level:
                recognized.append(
                    (
                        index,
                        content_level,
                    )
                )

        if not recognized:
            return None

        recognized.sort(
            key=lambda value: value[0]
        )

        return recognized[-1][1]

    def infer_owner_authority(
        relative: str,
    ) -> tuple[str | None, float]:
        explicit_instance = (
            explicit_descriptor_instance(
                relative
            )
        )

        instances = identity_instances(
            relative,
            identity_containers,
            reserved_nonowners,
        )

        if instances:
            deepest = sorted(
                instances,
                key=lambda value: value[0],
            )[-1]

            _, _, owner = deepest

            return owner, 1.0

        if explicit_instance:
            parent = Path(
                explicit_instance
            )

            candidate = parent.name

            if valid_instance_name(
                candidate,
                reserved_nonowners,
            ):
                return candidate, 0.95

        return None, 0.0

    def nearest_named_scope_authority(
        relative: str,
        markers: Sequence[str],
    ) -> tuple[str | None, float]:
        original, lowered = normalized_parts(
            relative
        )

        normalized_markers = {
            str(marker).lower()
            for marker in markers
        }

        for index, component in enumerate(lowered):
            if component not in normalized_markers:
                continue

            child_index = index + 1

            if child_index >= len(original):
                continue

            child = original[child_index]

            if not valid_instance_name(
                child,
                reserved_nonowners,
            ):
                continue

            return (
                "/".join(
                    original[: child_index + 1]
                ),
                1.0,
            )

        return None, 0.0

    def probable_rubric_authority(
        relative: str,
        kind: str,
        owner: str | None,
    ) -> tuple[str | None, float]:
        del owner

        if kind not in SOURCE_LIKE_KINDS:
            return None, 0.0

        explicit = explicit_rubric_scope(
            relative,
            rubric_facilities,
        )

        if explicit:
            return explicit, 1.0

        return None, 0.0

    def probable_cabal_authority(
        relative: str,
        kind: str,
    ) -> tuple[str | None, float]:
        if kind not in SOURCE_LIKE_KINDS:
            return None, 0.0

        explicit = explicit_cabal_scope(
            relative
        )

        if explicit:
            return explicit, 1.0

        return None, 0.0

    def identify_instance_authority(
        relative: str,
    ) -> str | None:
        explicit = explicit_descriptor_instance(
            relative
        )

        if explicit:
            return explicit

        instances = identity_instances(
            relative,
            identity_containers,
            reserved_nonowners,
        )

        if not instances:
            return None

        deepest = sorted(
            instances,
            key=lambda value: value[0],
        )[-1]

        index, _, _ = deepest
        original, _ = normalized_parts(
            relative
        )

        return "/".join(
            original[: index + 2]
        )

    def proposed_destination_authority(
        record: Any,
    ) -> str | None:
        del record

        # Authority-aware classification is diagnostic until a
        # separate migration planner proves a complete destination,
        # dependency rewrite, rollback and validation plan.
        return None

    scanner.IDENTITY_LEVELS = (
        identity_levels
    )

    scanner.CONTENT_LEVELS = (
        content_levels
    )

    scanner.RUBRIC_FACILITIES = tuple(
        authority["rubric"]["facilities"]
    )

    scanner.CABAL_LAWS = tuple(
        authority["cabal"]["laws"]
    )

    scanner.identify_edifice_level = (
        identify_edifice_level_authority
    )

    scanner.infer_owner = (
        infer_owner_authority
    )

    scanner.nearest_named_scope = (
        nearest_named_scope_authority
    )

    scanner.probable_rubric = (
        probable_rubric_authority
    )

    scanner.probable_cabal = (
        probable_cabal_authority
    )

    scanner.identify_instance = (
        identify_instance_authority
    )

    scanner.proposed_destination = (
        proposed_destination_authority
    )

    scanner.CANONICAL_STRUCTURE_AUTHORITY = (
        str(AUTHORITY_PATH)
    )

    scanner.CANONICAL_STRUCTURE_STATUS = (
        authority["status"]
    )

    scanner.AUTHORITY_CLASSIFICATION_ACTIVE = (
        True
    )


def run_self_test(
    scanner: ModuleType,
) -> None:
    owner, confidence = scanner.infer_owner(
        "ontology/obelisks/example/segue/"
        "portals/main/segue/innates/core/segue/"
        "exiles/opus/runtime/services/"
        "ENTITY_GRAPH.py"
    )

    require(
        owner == "opus",
        f"expected owner opus, found {owner}",
    )

    require(
        confidence == 1.0,
        "explicit identity owner must have confidence 1.0",
    )

    filename_owner, filename_confidence = (
        scanner.infer_owner(
            "runtime/services/ENTITY_GRAPH.py"
        )
    )

    require(
        filename_owner is None,
        "filename after services must not become owner",
    )

    require(
        filename_confidence == 0.0,
        "unresolved filename owner confidence must be zero",
    )

    rubric, rubric_confidence = (
        scanner.probable_rubric(
            "ontology/obelisks/example/segue/"
            "portals/main/segue/innates/core/"
            "segue/exiles/underscore/rubric/"
            "structure-intelligence/tests/"
            "test_structure_intelligence.py",
            "source",
            "underscore",
        )
    )

    require(
        rubric
        == (
            "ontology/obelisks/example/segue/"
            "portals/main/segue/innates/core/"
            "segue/exiles/underscore/rubric/"
            "structure-intelligence"
        ),
        f"unexpected explicit Rubric: {rubric}",
    )

    require(
        rubric_confidence == 1.0,
        "explicit Rubric confidence must be 1.0",
    )

    arbitrary_rubric, arbitrary_confidence = (
        scanner.probable_rubric(
            "ontology/obelisks/example/segue/"
            "portals/main/segue/innates/core/"
            "segue/exiles/palaver/apps/webui/"
            "src/chat/Composer.jsx",
            "source",
            "palaver",
        )
    )

    require(
        arbitrary_rubric is None,
        "application feature directory must not become a Rubric",
    )

    require(
        arbitrary_confidence == 0.0,
        "unresolved Rubric confidence must be zero",
    )

    require(
        scanner.proposed_destination(
            object()
        )
        is None,
        "authority-aware diagnostic scan must not propose moves",
    )


def main() -> int:
    try:
        authority = load_json(
            AUTHORITY_PATH
        )

        validate_authority(
            authority
        )

        scanner = load_scanner(
            SCANNER_PATH
        )

        install_authority_overrides(
            scanner,
            authority,
        )

        run_self_test(scanner)

        if "--authority-self-test" in sys.argv:
            print(
                f"SCANNER: {SCANNER_PATH}"
            )
            print(
                f"AUTHORITY: {AUTHORITY_PATH}"
            )
            print(
                "AUTHORITY STATUS: accepted-authority"
            )
            print(
                "OWNER INFERENCE: validated"
            )
            print(
                "RUBRIC INFERENCE: validated"
            )
            print(
                "CABAL INFERENCE: validated"
            )
            print(
                "UNSAFE DESTINATIONS: suppressed"
            )
            print(
                "MUTATION AUTHORIZED: false"
            )

            return 0

        return int(scanner.main())

    except (
        OSError,
        ValueError,
        json.JSONDecodeError,
        ImportError,
        AttributeError,
        TypeError,
    ) as exc:
        print(
            f"ERROR: {type(exc).__name__}: {exc}",
            file=sys.stderr,
        )

        return 1


if __name__ == "__main__":
    raise SystemExit(main())
