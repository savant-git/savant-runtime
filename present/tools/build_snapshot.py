#!/usr/bin/env python3

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SAVANT = Path("/root/savant-runtime")
PRESENT = Path("/root/savant-runtime/present")
OUTPUT = PRESENT / "data" / "savant.snapshot.json"

EXILES = (
    SAVANT
    / "canon-system"
    / "authority"
    / "exiles"
)

CONSTITUTION = (
    SAVANT
    / "canon-system"
    / "authority"
    / "constitution"
)

KINDRED = (
    SAVANT
    / "lexicon"
    / "kindred"
)

IDENTITY_edifice = [
    "obelisk",
    "gate",
    "innate",
    "exile",
    "prodigal",
    "quirk",
    "facet",
    "nuance",
    "trait",
]

LIVING_SUBSTRATES = [
    {
        "id": "scyon",
        "purpose": "living structural implementation",
    },
    {
        "id": "splyce",
        "purpose": "living interface and interaction",
    },
    {
        "id": "scrybe",
        "purpose": "context and memory projection",
    },
    {
        "id": "pryme",
        "purpose": "authority and precedence interpretation",
    },
    {
        "id": "cypher",
        "purpose": "translation and normalization",
    },
    {
        "id": "thryce",
        "purpose": "validation and assurance",
    },
    {
        "id": "spyral",
        "purpose": "evolution and migration compatibility",
    },
    {
        "id": "lythe",
        "purpose": "deterministic derivation specification",
    },
    {
        "id": "dryve",
        "purpose": "execution lifecycle mechanics",
    },
]

OWNERS = {
    "palaver": "conversation and development workstation",
    "envoy": "persona and outward communication",
    "orobouros": "canonical default persona",
    "opus": "AI and provider orchestration",
    "niche": "planning and task governance",
    "coda": "durable mutation orchestration",
    "notary": "evidence and verification",
    "modus": "modularity and composition",
    "coalesce": "application composition",
    "carbon": "simulation",
    "lore": "fluid canon",
    "scrybe": "context and recall projection",
    "filament": "projection execution",
}


def stable_json(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def digest(value: Any) -> str:
    return hashlib.sha256(
        stable_json(value).encode("utf-8")
    ).hexdigest()


def read_yaml(path: Path) -> dict[str, Any] | None:
    try:
        import yaml
    except ImportError:
        return None

    try:
        with path.open("r", encoding="utf-8") as handle:
            value = yaml.safe_load(handle)
    except (OSError, UnicodeError, ValueError):
        return None

    return value if isinstance(value, dict) else None


def read_json(path: Path) -> Any:
    try:
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)
    except (OSError, UnicodeError, ValueError):
        return None


def count_files(root: Path) -> int:
    if not root.exists():
        return 0

    return sum(
        1
        for path in root.rglob("*")
        if path.is_file()
    )


def count_dirs(root: Path) -> int:
    if not root.exists():
        return 0

    return sum(
        1
        for path in root.rglob("*")
        if path.is_dir()
    )


def extension_counts(root: Path) -> dict[str, int]:
    counter: Counter[str] = Counter()

    if not root.exists():
        return {}

    for path in root.rglob("*"):
        if not path.is_file():
            continue

        suffix = path.suffix.lower() or "[none]"
        counter[suffix] += 1

    return dict(
        sorted(
            counter.items(),
            key=lambda item: (
                -item[1],
                item[0],
            ),
        )
    )


def authority_records() -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []

    authority_root = (
        SAVANT
        / "canon-system"
        / "authority"
    )

    if not authority_root.exists():
        return records

    for path in sorted(
        authority_root.rglob("*.yaml")
    ):
        value = read_yaml(path)

        if not value:
            continue

        records.append(
            {
                "path": str(
                    path.relative_to(SAVANT)
                ),
                "id": value.get("id"),
                "kind": value.get("kind"),
                "status": value.get("status"),
                "title": value.get("title"),
                "authority": value.get(
                    "authority",
                    {},
                ),
                "dependencies": value.get(
                    "dependencies",
                    [],
                ),
                "relationships": value.get(
                    "relationships",
                    [],
                ),
                "lineage": value.get(
                    "lineage",
                    {},
                ),
                "provenance": value.get(
                    "provenance",
                    {},
                ),
            }
        )

    return records


def exile_records() -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []

    if not EXILES.exists():
        return records

    for path in sorted(
        EXILES.glob("*.yaml")
    ):
        value = read_yaml(path)

        if not value:
            continue

        purpose = value.get(
            "purpose",
            {},
        )

        if isinstance(purpose, dict):
            current_purpose = purpose.get(
                "current",
                [],
            )
        else:
            current_purpose = purpose

        orchestration = value.get(
            "orchestration",
            {},
        )

        if not isinstance(
            orchestration,
            dict,
        ):
            orchestration = {}

        authority = value.get(
            "authority",
            {},
        )

        if not isinstance(
            authority,
            dict,
        ):
            authority = {}

        records.append(
            {
                "id": value.get(
                    "id",
                    f"exile:{path.stem}",
                ),
                "name": path.stem,
                "title": value.get(
                    "title",
                    path.stem,
                ),
                "status": value.get(
                    "status",
                    "unknown",
                ),
                "purpose": current_purpose,
                "authority_state": authority.get(
                    "state",
                    "unknown",
                ),
                "confidence": authority.get(
                    "confidence"
                ),
                "opus_ready": bool(
                    orchestration.get(
                        "opus_ready"
                    )
                ),
                "chain_alias": orchestration.get(
                    "chain_alias"
                ),
                "dependencies": value.get(
                    "dependencies",
                    [],
                ),
                "relationships": value.get(
                    "relationships",
                    [],
                ),
                "lineage": value.get(
                    "lineage",
                    {},
                ),
                "provenance": value.get(
                    "provenance",
                    {},
                ),
            }
        )

    return records


def constitutional_relationships() -> list[dict[str, Any]]:
    path = (
        CONSTITUTION
        / "relationships.json"
    )

    payload = read_json(path)

    if not isinstance(
        payload,
        dict,
    ):
        return []

    relationships = payload.get(
        "relationships",
        [],
    )

    if not isinstance(
        relationships,
        list,
    ):
        return []

    return [
        dict(item)
        for item in relationships
        if isinstance(item, dict)
    ]


def kindred_disciplines() -> list[dict[str, Any]]:
    path = (
        KINDRED
        / "discipline_registry.yaml"
    )

    value = read_yaml(path)

    if not value:
        return []

    disciplines = value.get(
        "disciplines",
        [],
    )

    if not isinstance(
        disciplines,
        list,
    ):
        return []

    return [
        dict(item)
        for item in disciplines
        if isinstance(item, dict)
    ]


def run_json_command(
    command: list[str],
) -> dict[str, Any] | None:
    try:
        result = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
            timeout=15,
            env=os.environ.copy(),
        )
    except (
        OSError,
        subprocess.TimeoutExpired,
    ):
        return None

    if result.returncode != 0:
        return None

    try:
        value = json.loads(
            result.stdout
        )
    except json.JSONDecodeError:
        return None

    return (
        value
        if isinstance(value, dict)
        else None
    )


def ai_status() -> dict[str, Any]:
    command = (
        SAVANT
        / "commands"
        / "savant-ai"
    )

    if not command.exists():
        return {
            "available": False,
            "mode": "unknown",
        }

    value = run_json_command(
        [
            str(command),
            "status",
        ]
    )

    if value is None:
        return {
            "available": False,
            "mode": "unknown",
        }

    providers = value.get(
        "providers",
        {},
    )

    safe_providers: dict[str, Any] = {}

    if isinstance(
        providers,
        dict,
    ):
        for name, provider in providers.items():
            if not isinstance(
                provider,
                dict,
            ):
                continue

            safe_providers[name] = {
                "configured": bool(
                    provider.get(
                        "configured"
                    )
                ),
                "usable": bool(
                    provider.get(
                        "usable"
                    )
                ),
                "capabilities": provider.get(
                    "capabilities",
                    [],
                ),
                "reason": provider.get(
                    "reason",
                ),
            }

    return {
        "available": True,
        "mode": value.get(
            "mode",
            "unknown",
        ),
        "usable_providers": value.get(
            "usable_providers",
            [],
        ),
        "capabilities": value.get(
            "capabilities",
            [],
        ),
        "providers": safe_providers,
    }


def test_inventory() -> dict[str, int]:
    tests_root = SAVANT / "tests"

    if not tests_root.exists():
        return {
            "files": 0,
            "test_functions": 0,
        }

    files = 0
    functions = 0

    for path in tests_root.rglob(
        "test*.py"
    ):
        files += 1

        try:
            text = path.read_text(
                encoding="utf-8",
                errors="replace",
            )
        except OSError:
            continue

        functions += sum(
            1
            for line in text.splitlines()
            if line.lstrip().startswith(
                "def test"
            )
        )

    return {
        "files": files,
        "test_functions": functions,
    }


def build() -> dict[str, Any]:
    if not SAVANT.exists():
        raise RuntimeError(
            f"Savant runtime missing: {SAVANT}"
        )

    authorities = authority_records()
    exiles = exile_records()
    relationships = (
        constitutional_relationships()
    )
    disciplines = kindred_disciplines()
    tests = test_inventory()

    status_counter = Counter(
        str(
            record.get(
                "status",
                "unknown",
            )
        )
        for record in authorities
    )

    kind_counter = Counter(
        str(
            record.get(
                "kind",
                "unknown",
            )
        )
        for record in authorities
    )

    snapshot: dict[str, Any] = {
        "schema": (
            "savant.observatory.snapshot.v1"
        ),
        "generated_at": datetime.now(
            timezone.utc
        ).isoformat(),
        "source_root": str(SAVANT),
        "presentation_root": str(
            PRESENT
        ),
        "read_only": True,
        "identity_edifice": (
            IDENTITY_edifice
        ),
        "living_substrates": (
            LIVING_SUBSTRATES
        ),
        "ownership": OWNERS,
        "metrics": {
            "files": count_files(
                SAVANT
            ),
            "directories": count_dirs(
                SAVANT
            ),
            "authority_records": len(
                authorities
            ),
            "exiles": len(
                exiles
            ),
            "constitutional_relationships": len(
                relationships
            ),
            "kindred_disciplines": len(
                disciplines
            ),
            "test_files": tests[
                "files"
            ],
            "test_functions": tests[
                "test_functions"
            ],
        },
        "extensions": extension_counts(
            SAVANT
        ),
        "authority_statuses": dict(
            sorted(
                status_counter.items()
            )
        ),
        "authority_kinds": dict(
            sorted(
                kind_counter.items()
            )
        ),
        "exiles": exiles,
        "authority_records": authorities,
        "constitutional_relationships": (
            relationships
        ),
        "kindred_disciplines": (
            disciplines
        ),
        "ai": ai_status(),
        "presentation": {
            "title": "SAVANT",
            "subtitle": (
                "A recursively composable "
                "intelligence architecture"
            ),
            "edition": (
                "Founder's Demonstration"
            ),
            "date": "August 2026",
            "dedication": "For Mom.",
            "why": [
                (
                    "To build complex intelligent "
                    "software that can preserve "
                    "where its knowledge came from."
                ),
                (
                    "To let a system evolve without "
                    "destroying its history."
                ),
                (
                    "To make relationships, "
                    "dependencies, authority, "
                    "lineage and provenance visible."
                ),
                (
                    "To remain useful without an "
                    "external AI provider while "
                    "becoming more capable when "
                    "providers are available."
                ),
                (
                    "To make an ambitious system "
                    "composable instead of brittle."
                ),
            ],
        },
    }

    snapshot[
        "snapshot_sha256"
    ] = digest(snapshot)

    return snapshot


def main() -> int:
    try:
        snapshot = build()

        OUTPUT.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        OUTPUT.write_text(
            json.dumps(
                snapshot,
                indent=2,
                ensure_ascii=False,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )

        print(
            json.dumps(
                {
                    "valid": True,
                    "output": str(
                        OUTPUT
                    ),
                    "sha256": snapshot[
                        "snapshot_sha256"
                    ],
                    "metrics": snapshot[
                        "metrics"
                    ],
                },
                indent=2,
                sort_keys=True,
            )
        )

        return 0

    except Exception as exc:
        print(
            json.dumps(
                {
                    "valid": False,
                    "error": str(exc),
                },
                indent=2,
                sort_keys=True,
            ),
            file=sys.stderr,
        )

        return 1


if __name__ == "__main__":
    raise SystemExit(main())
