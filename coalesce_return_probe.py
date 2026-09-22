#!/usr/bin/env python3

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess


runtime_root = Path(
    "/root/savant-runtime"
)

coalesce_root = Path(
    "/root/savant-runtime/ontology/obelisks/"
    "_template/segue/gates/_template/segue/"
    "innates/_template/segue/exiles/modus/"
    "segue/prodigals/coalesce"
)

filament_root = Path(
    "/root/savant-runtime/ontology/obelisks/"
    "_template/segue/gates/_template/segue/"
    "innates/_template/segue/exiles/filament"
)

authority_files = [
    runtime_root / "COALESCE_COMPOSITION_CONTRACT.md",
    runtime_root / "COALESCE_ARCHITECTURE_CANON.md",
    runtime_root / "COALESCE_SLIVER_MIGRATION_PLAN.md",
    runtime_root / "COALESCE_27_PRIMITIVE_TARGET.md",
]

interesting_names = {
    "registry",
    "registries",
    "recipe",
    "recipes",
    "sliver",
    "slivers",
    "alloy",
    "alloys",
    "test",
    "tests",
    "contract",
    "contracts",
    "runtime",
    "projection",
    "projections",
    "filament",
}

interesting_suffixes = {
    ".py",
    ".json",
    ".md",
    ".yaml",
    ".yml",
    ".toml",
    ".sh",
}


def digest(
    path: Path,
) -> str:
    h = hashlib.sha256()

    with path.open(
        "rb"
    ) as handle:
        for chunk in iter(
            lambda: handle.read(
                1024 * 1024
            ),
            b"",
        ):
            h.update(
                chunk
            )

    return h.hexdigest()


def relative(
    path: Path,
) -> str:
    try:
        return str(
            path.relative_to(
                runtime_root
            )
        )
    except ValueError:
        return str(
            path
        )


def file_record(
    path: Path,
) -> dict:
    return {
        "path":
            relative(
                path
            ),
        "size":
            path.stat().st_size,
        "sha256":
            digest(
                path
            ),
    }


def selected_files() -> list[dict]:
    if not coalesce_root.is_dir():
        return []

    records: list[dict] = []

    for path in sorted(
        coalesce_root.rglob(
            "*"
        )
    ):
        if not path.is_file():
            continue

        rel = path.relative_to(
            coalesce_root
        )

        lowered_parts = {
            part.lower()
            for part in rel.parts
        }

        name = path.name.lower()

        interesting = (
            path.suffix.lower()
            in interesting_suffixes
            and (
                bool(
                    lowered_parts
                    & interesting_names
                )
                or any(
                    token in name
                    for token
                    in interesting_names
                )
            )
        )

        if interesting:
            records.append(
                file_record(
                    path
                )
            )

    return records


def grep_references(
    root: Path,
    terms: tuple[str, ...],
    limit: int = 80,
) -> list[str]:
    if not root.is_dir():
        return []

    results: list[str] = []

    for path in sorted(
        root.rglob(
            "*"
        )
    ):
        if not path.is_file():
            continue

        if path.suffix.lower() not in (
            interesting_suffixes
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

        if not any(
            term.lower()
            in lowered
            for term in terms
        ):
            continue

        matches = []

        for number, line in enumerate(
            text.splitlines(),
            start=1,
        ):
            line_lower = line.lower()

            if any(
                term.lower()
                in line_lower
                for term in terms
            ):
                matches.append(
                    f"{relative(path)}:"
                    f"{number}:"
                    f"{line.strip()[:220]}"
                )

                if (
                    len(results)
                    + len(matches)
                    >= limit
                ):
                    break

        results.extend(
            matches
        )

        if len(results) >= limit:
            break

    return results[
        :limit
    ]


def git_status() -> dict:
    git_dir = (
        runtime_root
        / ".git"
    )

    if not git_dir.exists():
        return {
            "available":
                False,
        }

    def run(
        *args: str,
    ) -> str:
        result = subprocess.run(
            [
                "git",
                "-C",
                str(
                    runtime_root
                ),
                *args,
            ],
            check=False,
            capture_output=True,
            text=True,
        )

        return result.stdout.strip()

    return {
        "available":
            True,
        "head":
            run(
                "rev-parse",
                "HEAD",
            ),
        "branch":
            run(
                "rev-parse",
                "--abbrev-ref",
                "HEAD",
            ),
        "coalesce_history":
            run(
                "log",
                "-n",
                "12",
                "--format=%H %cI %s",
                "--",
                str(
                    coalesce_root
                ),
            ).splitlines(),
    }


def main() -> int:
    payload = {
        "schema":
            "savant.coalesce.return-probe.v1",
        "authority_effect":
            "none",
        "coalesce_root":
            str(
                coalesce_root
            ),
        "coalesce_root_exists":
            coalesce_root.is_dir(),
        "authority_files": [
            {
                "path":
                    relative(
                        path
                    ),
                "exists":
                    path.is_file(),
                **(
                    {
                        "size":
                            path.stat().st_size,
                        "sha256":
                            digest(
                                path
                            ),
                    }
                    if path.is_file()
                    else {}
                ),
            }
            for path
            in authority_files
        ],
        "current_files":
            selected_files(),
        "coalesce_filament_references":
            grep_references(
                coalesce_root,
                (
                    "filament",
                    "projection",
                    "project",
                ),
            ),
        "filament_coalesce_references":
            grep_references(
                filament_root,
                (
                    "coalesce",
                    "alloy",
                    "sliver",
                ),
            ),
        "identity_references":
            grep_references(
                coalesce_root,
                (
                    "prodigal:modus:coalesce",
                    "exile:modus",
                    "\"coalesce\"",
                    "'coalesce'",
                ),
            ),
        "registry_recipe_references":
            grep_references(
                coalesce_root,
                (
                    "registry",
                    "recipe",
                    "sliver",
                    "alloy",
                ),
            ),
        "test_references":
            grep_references(
                coalesce_root,
                (
                    "pytest",
                    "unittest",
                    "test_",
                    "assert ",
                ),
            ),
        "git":
            git_status(),
    }

    print(
        json.dumps(
            payload,
            indent=2,
            sort_keys=True,
        )
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
