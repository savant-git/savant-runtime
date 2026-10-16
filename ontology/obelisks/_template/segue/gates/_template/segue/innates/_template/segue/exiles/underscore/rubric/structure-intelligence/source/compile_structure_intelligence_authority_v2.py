#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path
from types import ModuleType
from typing import Any


authority_wrapper = Path(
    "/root/savant-runtime/ontology/obelisks/_template/segue/"
    "gates/_template/segue/innates/_template/segue/exiles/"
    "underscore/rubric/structure-intelligence/source/"
    "compile_structure_intelligence_authority.py"
)

generic_descriptor_stems = {
    "entity",
    "instance",
    "manifest",
    "schema",
    "record",
    "descriptor",
    "template",
    "_template",
}

authority_record_suffixes = {
    ".json",
    ".yaml",
    ".yml",
    ".toml",
    ".cue",
}

root_owner_scopes = {
    "assurance": "savant-runtime",
    "authority": "savant-runtime",
    "authority_graph": "savant-runtime",
    "canon": "savant-runtime",
    "canon-system": "savant-runtime",
    "context": "savant-runtime",
    "docs": "savant-runtime",
    "evolution": "savant-runtime",
    "frontend": "savant-runtime",
    "imports": "savant-runtime",
    "lexicon": "savant-runtime",
    "migrations": "savant-runtime",
    "port": "savant-runtime",
    "present": "savant-runtime",
    "reports": "savant-runtime",
    "runtime": "savant-runtime",
    "scripts": "savant-runtime",
    "tests": "savant-runtime",
    "tools": "savant-runtime",
    "vault": "savant-runtime",
}

non_owner_root_prefixes = (
    ".venv",
)

root_source_suffixes = {
    ".fish",
    ".js",
    ".py",
    ".pyi",
    ".sh",
    ".ts",
    ".tsx",
}


def require(
    condition: bool,
    message: str,
) -> None:
    if not condition:
        raise ValueError(message)


def load_authority_wrapper() -> ModuleType:
    import importlib.util

    require(
        authority_wrapper.is_file(),
        f"authority wrapper unavailable: {authority_wrapper}",
    )

    require(
        authority_wrapper.stat().st_size > 0,
        f"authority wrapper empty: {authority_wrapper}",
    )

    specification = importlib.util.spec_from_file_location(
        "savant_structure_intelligence_authority_v1",
        authority_wrapper,
    )

    require(
        specification is not None,
        "cannot create authority-wrapper specification",
    )

    require(
        specification.loader is not None,
        "authority-wrapper loader unavailable",
    )

    module = importlib.util.module_from_spec(
        specification
    )

    sys.modules[specification.name] = module
    specification.loader.exec_module(module)

    return module


def authority_sets(
    authority: dict[str, Any],
) -> dict[str, Any]:
    identity = authority.get(
        "identity_edifice"
    )

    require(
        isinstance(identity, dict),
        "identity_edifice must be an object",
    )

    containers = identity.get(
        "containers"
    )

    require(
        isinstance(containers, dict),
        "identity containers must be an object",
    )

    owner_inference = identity.get(
        "owner_inference"
    )

    require(
        isinstance(owner_inference, dict),
        "owner_inference must be an object",
    )

    reserved = owner_inference.get(
        "reserved_nonowners"
    )

    require(
        isinstance(reserved, list),
        "reserved_nonowners must be a list",
    )

    return {
        "identity_containers": {
            str(name).lower(): str(level).lower()
            for name, level in containers.items()
        },
        "reserved_nonowners": {
            str(value).lower()
            for value in reserved
        },
    }


def terminal_identity_record(
    relative: str,
    identity_containers: dict[str, str],
    reserved_nonowners: set[str],
) -> tuple[str, str] | None:
    path = Path(relative)
    original = tuple(path.parts)
    lowered = tuple(
        component.lower()
        for component in original
    )

    if not original:
        return None

    suffix = path.suffix.lower()
    stem = path.stem

    if suffix not in authority_record_suffixes:
        return None

    normalized_stem = stem.lower()

    if normalized_stem in generic_descriptor_stems:
        return None

    if stem.startswith("_"):
        return None

    if normalized_stem in reserved_nonowners:
        return None

    combined_containers = dict(
        identity_containers
    )

    combined_containers.update(
        {
            "gates": "portal",
            "shards": "iota",
        }
    )

    terminal_index = len(original) - 1

    for index, component in enumerate(lowered):
        level = combined_containers.get(
            component
        )

        if not level:
            continue

        child_index = index + 1

        if child_index != terminal_index:
            continue

        prefix = {
            component.lower()
            for component in original[:index]
        }

        if (
            "authority" not in prefix
            and "canon-system" not in prefix
        ):
            return None

        return stem, level

    return None


def root_scope_owner(
    relative: str,
) -> tuple[str | None, float]:
    path = Path(relative)
    parts = path.parts

    if not parts:
        return None, 0.0

    root = parts[0].lower()

    if any(
        root.startswith(prefix)
        for prefix in non_owner_root_prefixes
    ):
        return None, 0.0

    owner = root_owner_scopes.get(root)

    if owner:
        return owner, 1.0

    if len(parts) == 1:
        suffix = path.suffix.lower()

        if suffix in root_source_suffixes:
            return "savant-runtime", 1.0

    return None, 0.0


def install_authority_extension(
    scanner: ModuleType,
    authority: dict[str, Any],
) -> None:
    sets = authority_sets(
        authority
    )

    identity_containers: dict[str, str] = (
        sets["identity_containers"]
    )

    reserved_nonowners: set[str] = (
        sets["reserved_nonowners"]
    )

    inherited_infer_owner = scanner.infer_owner
    inherited_identify_instance = (
        scanner.identify_instance
    )

    def extended_infer_owner(
        relative: str,
    ) -> tuple[str | None, float]:
        record = terminal_identity_record(
            relative,
            identity_containers,
            reserved_nonowners,
        )

        if record:
            owner, _ = record
            return owner, 1.0

        owner, confidence = inherited_infer_owner(
            relative
        )

        if owner is not None:
            return owner, confidence

        return root_scope_owner(
            relative
        )

    def extended_identify_instance(
        relative: str,
    ) -> str | None:
        record = terminal_identity_record(
            relative,
            identity_containers,
            reserved_nonowners,
        )

        if record:
            owner, level = record

            return f"authority:{level}:{owner}"

        return inherited_identify_instance(
            relative
        )

    scanner.infer_owner = extended_infer_owner
    scanner.identify_instance = (
        extended_identify_instance
    )


def run_self_test(
    scanner: ModuleType,
) -> None:
    owner, confidence = scanner.infer_owner(
        "canon-system/authority/exiles/opus.yaml"
    )

    require(
        owner == "opus",
        f"expected authority-record owner opus, found {owner}",
    )

    require(
        confidence == 1.0,
        "authority-record owner confidence must be 1.0",
    )

    instance = scanner.identify_instance(
        "canon-system/authority/exiles/opus.yaml"
    )

    require(
        instance == "authority:exile:opus",
        f"unexpected authority-record instance: {instance}",
    )

    root_owner, root_confidence = scanner.infer_owner(
        "tools/sdump-enterprise/commands/sdump.py"
    )

    require(
        root_owner == "savant-runtime",
        f"expected root-scope owner savant-runtime, found {root_owner}",
    )

    require(
        root_confidence == 1.0,
        "explicit root-scope owner confidence must be 1.0",
    )

    loose_owner, loose_confidence = scanner.infer_owner(
        "build_runtime_map_from_clean_parse.sh"
    )

    require(
        loose_owner == "savant-runtime",
        f"expected runtime-root owner savant-runtime, found {loose_owner}",
    )

    require(
        loose_confidence == 1.0,
        "runtime-root source confidence must be 1.0",
    )

    venv_owner, venv_confidence = scanner.infer_owner(
        ".venv_voice/bin/helper.py"
    )

    require(
        venv_owner is None,
        "virtual-environment artifact must remain unresolved",
    )

    require(
        venv_confidence == 0.0,
        "virtual-environment owner confidence must remain zero",
    )

    require(
        scanner.proposed_destination(object())
        is None,
        "authority-aware scan must suppress destinations",
    )


def main() -> int:
    try:
        wrapper = load_authority_wrapper()

        authority = wrapper.load_json(
            wrapper.AUTHORITY_PATH
        )

        wrapper.validate_authority(
            authority
        )

        scanner = wrapper.load_scanner(
            wrapper.SCANNER_PATH
        )

        wrapper.install_authority_overrides(
            scanner,
            authority,
        )

        install_authority_extension(
            scanner,
            authority,
        )

        run_self_test(scanner)

        if "--authority-self-test" in sys.argv:
            print(
                f"scanner: {wrapper.SCANNER_PATH}"
            )
            print(
                f"authority: {wrapper.AUTHORITY_PATH}"
            )
            print(
                "authority status: accepted-authority"
            )
            print(
                "authority record owners: validated"
            )
            print(
                "root scope owners: validated"
            )
            print(
                "inherited ownership inference: preserved"
            )
            print(
                "unsafe destinations: suppressed"
            )
            print(
                "mutation authorized: false"
            )

            return 0

        return int(scanner.main())

    except Exception as exc:
        print(
            f"error: {type(exc).__name__}: {exc}",
            file=sys.stderr,
        )

        return 1


if __name__ == "__main__":
    raise SystemExit(main())
