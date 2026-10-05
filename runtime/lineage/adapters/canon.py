#!/usr/bin/env python3
from __future__ import annotations

from collections.abc import (
    Mapping,
)
from pathlib import Path
from typing import (
    Any,
    Iterable,
)

from ..engine import LineageGraph
from .authority import (
    ingest_authority_document,
)


DEFAULT_IGNORE_NAMES = {
    ".git",
    ".venv",
    ".venv_voice",
    "node_modules",
    "__pycache__",
    "site-packages",
    "exports",
    "repair_backups",
    "source",
    "projections",
    "history",
    "proposals",
}


def iter_yaml_documents(
    roots: Iterable[
        Path | str
    ],
    *,
    ignored_names: Iterable[
        str
    ] = DEFAULT_IGNORE_NAMES,
):
    try:
        import yaml
    except ImportError as exc:
        raise RuntimeError(
            "PyYAML is required to "
            "ingest canon-system "
            "authority YAML"
        ) from exc

    ignored = set(
        ignored_names
    )

    seen: set[Path] = set()

    for raw_root in roots:
        root = Path(
            raw_root
        ).expanduser().resolve()

        if not root.exists():
            continue

        candidates = (
            [root]
            if root.is_file()
            else sorted(
                [
                    *root.rglob(
                        "*.yaml"
                    ),
                    *root.rglob(
                        "*.yml"
                    ),
                ]
            )
        )

        for path in candidates:
            resolved = path.resolve()

            if (
                resolved in seen
                or any(
                    part in ignored
                    for part in path.parts
                )
            ):
                continue

            seen.add(
                resolved
            )

            try:
                payload = yaml.safe_load(
                    path.read_text(
                        encoding="utf-8"
                    )
                )
            except (
                OSError,
                UnicodeError,
                yaml.YAMLError,
            ):
                continue

            if isinstance(
                payload,
                Mapping,
            ):
                yield (
                    path,
                    payload,
                )

            elif isinstance(
                payload,
                list,
            ):
                for item in payload:
                    if isinstance(
                        item,
                        Mapping,
                    ):
                        yield (
                            path,
                            item,
                        )


def ingest_canon_system(
    graph: LineageGraph,
    roots: Iterable[
        Path | str
    ],
) -> dict[str, int]:
    documents = 0
    emitted = 0

    for (
        path,
        document,
    ) in iter_yaml_documents(
        roots
    ):
        emitted += (
            ingest_authority_document(
                graph,
                document,
                source_path=path,
            )
        )

        documents += 1

    return {
        "documents": documents,
        "emitted": emitted,
    }
