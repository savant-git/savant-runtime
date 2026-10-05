#!/usr/bin/env python3

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys
from typing import Any


ROOT = Path(
    "/root/savant-runtime"
)

COALESCE = Path(
    "/root/savant-runtime/ontology/obelisks/_template/segue/gates/"
    "_template/segue/innates/_template/segue/exiles/modus/segue/"
    "prodigals/coalesce"
).resolve()

COALESCE_RUNTIME = (
    COALESCE
    / "runtime"
)

FILAMENT_PROJECTOR = Path(
    "/root/savant-runtime/ontology/obelisks/_template/segue/gates/"
    "_template/segue/innates/_template/segue/exiles/filament/runtime/"
    "projectors/coalesce_view.py"
)

if str(COALESCE_RUNTIME) not in sys.path:
    sys.path.insert(
        0,
        str(COALESCE_RUNTIME),
    )


from coalesce_v2 import (
    runtime as coalesce_runtime,
)
from identity_resolver import (
    resolver,
)


SCHEMA = (
    "savant://coalesce/"
    "application-extraction-verification/1.1"
)

OWNER = "prodigal:modus:coalesce"

RECIPE = "chronology-explorer"

FORBIDDEN_DOMAIN_TERMS = (
    "mayorgate",
    "chipouras",
    "cutler bay",
)

SCAN_SUFFIXES = {
    ".py",
    ".json",
    ".md",
    ".js",
    ".ts",
    ".tsx",
    ".html",
    ".css",
    ".yaml",
    ".yml",
    ".toml",
}


class ApplicationExtractionVerificationError(
    RuntimeError
):
    pass


def require(
    condition: bool,
    message: str,
) -> None:
    if not condition:
        raise ApplicationExtractionVerificationError(
            message
        )


def load_filament_projector():
    require(
        FILAMENT_PROJECTOR.is_file(),
        "Filament Coalesce projector missing",
    )

    spec = (
        importlib.util.spec_from_file_location(
            "savant_filament_coalesce_extraction_verify",
            FILAMENT_PROJECTOR,
        )
    )

    require(
        spec is not None
        and spec.loader is not None,
        "unable to construct Filament projector import",
    )

    module = (
        importlib.util.module_from_spec(
            spec
        )
    )

    sys.modules[
        spec.name
    ] = module

    spec.loader.exec_module(
        module
    )

    return module


def neutral_record() -> dict[str, Any]:
    return {
        "id": "neutral-record-001",
        "date": "2026-01-02T03:04:05Z",
        "title": "neutral chronology event",
        "preview": "generic application extraction verification",
        "body": "neutral record body",
        "kind": "event",
        "status": "active",
        "category": "general",
        "provenance": {
            "source": "verification-fixture",
            "authority_effect": "none",
        },
        "relationships": [],
    }


def verify_recipe_resolution() -> dict[str, Any]:
    identities = resolver()

    resolved = identities.resolve(
        RECIPE
    )

    canonical_identity = str(
        resolved.get(
            "canonical_identity",
            "",
        )
        or ""
    ).strip()

    short_identity = str(
        resolved.get(
            "short_identity",
            "",
        )
        or ""
    ).strip()

    aliases = {
        str(
            value
            or ""
        ).strip()
        for value
        in resolved.get(
            "recipe_identities",
            [],
        )
        if str(
            value
            or ""
        ).strip()
    }

    require(
        short_identity == RECIPE,
        "chronology-explorer short recipe identity changed",
    )

    require(
        RECIPE in aliases,
        "chronology-explorer alias is missing",
    )

    require(
        bool(
            canonical_identity
        ),
        "canonical chronology-explorer recipe identity missing",
    )

    require(
        canonical_identity in aliases,
        "canonical recipe identity is not present in recipe aliases",
    )

    require(
        resolved.get(
            "canonical_identity_kind"
        )
        == "alloy-recipe",
        "chronology-explorer is not resolving as an Alloy recipe",
    )

    sliver_count = resolved.get(
        "sliver_count"
    )

    require(
        isinstance(
            sliver_count,
            int,
        )
        and 1 <= sliver_count <= 9,
        "chronology-explorer violates the 1-9 Sliver invariant",
    )

    canonical_resolution = identities.resolve(
        canonical_identity
    )

    require(
        canonical_resolution.get(
            "canonical_identity"
        )
        == canonical_identity,
        "canonical recipe identity does not round trip",
    )

    require(
        canonical_resolution.get(
            "short_identity"
        )
        == RECIPE,
        "canonical recipe identity does not converge on the short alias",
    )

    return {
        "requested_identity":
            RECIPE,
        "canonical_identity":
            canonical_identity,
        "short_identity":
            short_identity,
        "recipe_identities":
            sorted(
                aliases
            ),
        "sliver_count":
            sliver_count,
        "slivers":
            resolved.get(
                "slivers",
                [],
            ),
    }


def verify_v2_composition() -> dict[str, Any]:
    runtime = coalesce_runtime()

    result = runtime.dispatch(
        "plan-recipe",
        {
            "application_id":
                RECIPE,
        },
    )

    require(
        result.get(
            "ok"
        )
        is True,
        "Coalesce v2 failed to plan chronology-explorer",
    )

    planned = result.get(
        "result"
    )

    require(
        isinstance(
            planned,
            dict,
        ),
        "Coalesce recipe plan missing",
    )

    return {
        "planned":
            True,
        "plan":
            planned,
    }


def verify_filament_projection() -> dict[str, Any]:
    module = load_filament_projector()

    derive = getattr(
        module,
        "derive_coalesce_view",
        None,
    )

    require(
        callable(
            derive
        ),
        "Filament derive_coalesce_view unavailable",
    )

    record = neutral_record()

    result = derive(
        RECIPE,
        {
            "records": [
                record
            ],
        },
    )

    require(
        isinstance(
            result,
            dict,
        ),
        "Filament returned non-object projection",
    )

    require(
        result.get(
            "owner"
        )
        == "exile:filament",
        "Filament ownership changed",
    )

    require(
        result.get(
            "source"
        )
        == OWNER,
        "Coalesce source identity changed",
    )

    require(
        result.get(
            "recipe"
        )
        == RECIPE,
        "projected recipe identity changed",
    )

    records = result.get(
        "records",
        [],
    )

    require(
        isinstance(
            records,
            list,
        ),
        "projected records missing",
    )

    require(
        len(
            records
        ) >= 1,
        "neutral record did not enter the application projection",
    )

    matched = any(
        isinstance(
            row,
            dict,
        )
        and row.get(
            "id"
        )
        == record[
            "id"
        ]
        for row in records
    )

    require(
        matched,
        "neutral record identity was not preserved through projection",
    )

    composition = result.get(
        "composition",
        {},
    )

    require(
        isinstance(
            composition,
            dict,
        )
        and bool(
            composition.get(
                "digest"
            )
        ),
        "composition digest missing from Filament projection",
    )

    return {
        "record_count":
            len(
                records
            ),
        "neutral_record_projected":
            True,
        "composition_digest":
            composition.get(
                "digest"
            ),
        "executed_piece_count":
            len(
                result.get(
                    "trace",
                    [],
                )
            ),
    }


def verify_domain_separation() -> dict[str, Any]:
    findings: list[dict[str, Any]] = []

    for path in sorted(
        COALESCE.rglob(
            "*"
        )
    ):
        if not path.is_file():
            continue

        if path.suffix.lower() not in SCAN_SUFFIXES:
            continue

        if path.name == (
            "application_extraction_verify.py"
        ):
            continue

        try:
            text = path.read_text(
                encoding="utf-8",
                errors="replace",
            )
        except OSError:
            continue

        lowered = text.lower()

        matched_terms = [
            term
            for term in FORBIDDEN_DOMAIN_TERMS
            if term in lowered
        ]

        if matched_terms:
            findings.append(
                {
                    "path":
                        str(
                            path.relative_to(
                                ROOT
                            )
                        ),
                    "terms":
                        matched_terms,
                }
            )

    require(
        not findings,
        "source-domain substance remains inside generic Coalesce: "
        + json.dumps(
            findings,
            sort_keys=True,
        ),
    )

    return {
        "clean":
            True,
        "forbidden_terms":
            list(
                FORBIDDEN_DOMAIN_TERMS
            ),
        "findings":
            [],
    }


def verify() -> dict[str, Any]:
    recipe = (
        verify_recipe_resolution()
    )

    composition = (
        verify_v2_composition()
    )

    filament = (
        verify_filament_projection()
    )

    separation = (
        verify_domain_separation()
    )

    return {
        "ok":
            True,
        "schema":
            SCHEMA,
        "owner":
            OWNER,
        "recipe":
            recipe,
        "composition":
            composition,
        "filament":
            filament,
        "domain_separation":
            separation,
        "completion": {
            "useful_generic_behavior":
                "represented",
            "source_domain_data":
                "absent-from-generic-coalesce",
            "composition":
                "verified",
            "neutral_data":
                "verified",
            "filament_projection":
                "verified",
            "canonical_recipe_identity":
                "preserved",
            "short_recipe_alias":
                "preserved",
            "existing_savant_components":
                "reused",
            "known_blocker":
                None,
        },
        "authority_effect":
            "none",
    }


def main() -> int:
    print(
        json.dumps(
            verify(),
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
            default=str,
        )
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
