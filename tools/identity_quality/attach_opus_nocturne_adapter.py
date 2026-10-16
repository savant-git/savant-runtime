#!/usr/bin/env python3
from __future__ import annotations

import datetime as dt
import hashlib
import json
import shutil
from pathlib import Path
from typing import Any


ROOT = Path(
    "/root/savant-runtime"
)

NOCTURNE_ROOT = (
    ROOT
    / "edifices"
    / "identity"
    / "exiles"
    / "opus"
    / "prodigals"
    / "nocturne"
)

NOCTURNE_DEFINITION = (
    NOCTURNE_ROOT
    / "definition.json"
)

OPUS_DEFINITION_CANDIDATES = (
    ROOT
    / "edifices"
    / "identity"
    / "exiles"
    / "opus"
    / "definition.json",
    ROOT
    / "ontology"
    / "exiles"
    / "opus"
    / "authority"
    / "identity.json",
)

ADAPTER = (
    NOCTURNE_ROOT
    / "adapters"
    / "opus"
    / "opus_nocturne_adapter.py"
)

TEST = (
    NOCTURNE_ROOT
    / "adapters"
    / "opus"
    / "tests"
    / "test_opus_nocturne_adapter.py"
)

CONTRACTS = (
    NOCTURNE_ROOT
    / "contracts"
    / "opus_attachment_contracts.py"
)

BACKUP_ROOT = (
    ROOT
    / "backups"
    / "identity-quality"
    / "opus-nocturne-adapter-attachment"
)


def timestamp() -> str:
    return dt.datetime.now(
        dt.timezone.utc
    ).strftime(
        "%Y%m%dT%H%M%SZ"
    )


def sha256_path(
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


def load_json(
    path: Path,
) -> dict[str, Any]:
    value = json.loads(
        path.read_text(
            encoding="utf-8"
        )
    )

    if not isinstance(
        value,
        dict,
    ):
        raise ValueError(
            f"Expected JSON object: {path}"
        )

    return value


def write_json(
    path: Path,
    value: Any,
) -> None:
    path.write_text(
        json.dumps(
            value,
            ensure_ascii=False,
            indent=2,
            sort_keys=False,
        )
        + "\n",
        encoding="utf-8",
    )


def append_unique(
    collection: list[Any],
    candidate: Any,
) -> None:
    if candidate not in collection:
        collection.append(
            candidate
        )


def backup_file(
    path: Path,
    run_id: str,
) -> Path:
    backup = (
        BACKUP_ROOT
        / run_id
        / path.relative_to(
            ROOT
        )
    )

    backup.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    shutil.copy2(
        path,
        backup,
    )

    return backup


def locate_opus_definition() -> Path | None:
    for candidate in (
        OPUS_DEFINITION_CANDIDATES
    ):
        if candidate.is_file():
            return candidate

    return None


def attach_to_nocturne(
    document: dict[str, Any],
) -> dict[str, Any]:
    runtime = document.setdefault(
        "runtime",
        {},
    )

    adapters = runtime.setdefault(
        "adapters",
        [],
    )

    append_unique(
        adapters,
        ADAPTER.relative_to(
            ROOT
        ).as_posix(),
    )

    relationships = document.setdefault(
        "relationships",
        [],
    )

    append_unique(
        relationships,
        {
            "type": (
                "attaches_to"
            ),
            "target": (
                "exile.opus"
            ),
            "direction": (
                "outbound"
            ),
            "adapter": (
                ADAPTER.relative_to(
                    ROOT
                ).as_posix()
            ),
            "authority_transfer": False,
            "reversible": True,
        },
    )

    dependencies = document.setdefault(
        "dependencies",
        {},
    )

    for field in (
        "required",
        "optional",
        "runtime",
        "external",
    ):
        dependencies.setdefault(
            field,
            [],
        )

    append_unique(
        dependencies[
            "runtime"
        ],
        {
            "id": (
                "opus.nocturne.adapter"
            ),
            "kind": (
                "attachment_adapter"
            ),
            "required": False,
        },
    )

    validation = document.setdefault(
        "validation",
        {},
    )

    integration_tests = (
        validation.setdefault(
            "integration_tests",
            [],
        )
    )

    append_unique(
        integration_tests,
        TEST.relative_to(
            ROOT
        ).as_posix(),
    )

    security_tests = (
        validation.setdefault(
            "security_tests",
            [],
        )
    )

    for test_name in (
        (
            "nocturne_cannot_select_"
            "external_providers"
        ),
        (
            "nocturne_cannot_read_"
            "opus_secrets"
        ),
        (
            "unresolved_provider_"
            "request_is_rejected"
        ),
        (
            "forbidden_policy_flag_"
            "is_rejected"
        ),
        (
            "attachment_is_reversible"
        ),
    ):
        append_unique(
            security_tests,
            test_name,
        )

    provenance = document.setdefault(
        "provenance",
        {},
    )

    created_from = (
        provenance.setdefault(
            "created_from",
            [],
        )
    )

    source_hashes = (
        provenance.setdefault(
            "source_hashes",
            {},
        )
    )

    for path in (
        ADAPTER,
        TEST,
        CONTRACTS,
    ):
        relative = path.relative_to(
            ROOT
        ).as_posix()

        append_unique(
            created_from,
            relative,
        )

        source_hashes[
            relative
        ] = sha256_path(
            path
        )

    return document


def attach_to_opus(
    document: dict[str, Any],
) -> dict[str, Any]:
    relationships = document.setdefault(
        "relationships",
        [],
    )

    append_unique(
        relationships,
        {
            "type": (
                "delegates_local_analysis_to"
            ),
            "target": (
                "prodigal.nocturne"
            ),
            "direction": (
                "outbound"
            ),
            "adapter": (
                ADAPTER.relative_to(
                    ROOT
                ).as_posix()
            ),
            "provider_orchestration_owner": (
                "exile.opus"
            ),
            "authority_transfer": False,
            "reversible": True,
        },
    )

    runtime = document.setdefault(
        "runtime",
        {},
    )

    adapters = runtime.setdefault(
        "adapters",
        [],
    )

    append_unique(
        adapters,
        ADAPTER.relative_to(
            ROOT
        ).as_posix(),
    )

    return document


def main() -> int:
    required = (
        NOCTURNE_DEFINITION,
        ADAPTER,
        TEST,
        CONTRACTS,
    )

    missing = [
        str(
            path
        )
        for path in required
        if not path.is_file()
    ]

    if missing:
        print(
            json.dumps(
                {
                    "operation": (
                        "attach_opus_"
                        "nocturne_adapter"
                    ),
                    "passed": False,
                    "missing": missing,
                },
                indent=2,
                sort_keys=True,
            )
        )

        return 2

    run_id = timestamp()

    nocturne_backup = (
        backup_file(
            NOCTURNE_DEFINITION,
            run_id,
        )
    )

    nocturne = load_json(
        NOCTURNE_DEFINITION
    )

    nocturne = attach_to_nocturne(
        nocturne
    )

    write_json(
        NOCTURNE_DEFINITION,
        nocturne,
    )

    opus_path = (
        locate_opus_definition()
    )

    opus_backup: Path | None = None

    if opus_path is not None:
        opus_backup = (
            backup_file(
                opus_path,
                run_id,
            )
        )

        opus = load_json(
            opus_path
        )

        opus = attach_to_opus(
            opus
        )

        write_json(
            opus_path,
            opus,
        )

    print(
        json.dumps(
            {
                "operation": (
                    "attach_opus_"
                    "nocturne_adapter"
                ),
                "passed": True,
                "nocturne_definition": (
                    str(
                        NOCTURNE_DEFINITION
                    )
                ),
                "nocturne_sha256": (
                    sha256_path(
                        NOCTURNE_DEFINITION
                    )
                ),
                "nocturne_backup": (
                    str(
                        nocturne_backup
                    )
                ),
                "opus_definition": (
                    str(
                        opus_path
                    )
                    if opus_path
                    else None
                ),
                "opus_sha256": (
                    sha256_path(
                        opus_path
                    )
                    if opus_path
                    else None
                ),
                "opus_backup": (
                    str(
                        opus_backup
                    )
                    if opus_backup
                    else None
                ),
                "adapter": str(
                    ADAPTER
                ),
                "test": str(
                    TEST
                ),
                "contracts": str(
                    CONTRACTS
                ),
            },
            indent=2,
            sort_keys=True,
        )
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
