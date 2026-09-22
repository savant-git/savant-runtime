#!/usr/bin/env python3

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Final, Iterator


SAVANT_ROOT: Final[Path] = Path(
    "/root/savant-runtime"
)

LEGACY_CANON_ROOT: Final[Path] = (
    SAVANT_ROOT / "canon"
)

DIMENSIONAL_CANON_ROOT: Final[Path] = (
    SAVANT_ROOT
    / "vault"
    / "dimensions"
    / "canon"
)

REPORT_PATH: Final[Path] = (
    SAVANT_ROOT
    / "vault"
    / "dimensions"
    / "sys"
    / "reports"
    / "canon-tree-conflict.json"
)

EXCLUDED_DIRS: Final[frozenset[str]] = frozenset(
    {
        ".git",
        "__pycache__",
        "backups",
        "cache",
        "reports",
    }
)


@dataclass(frozen=True, slots=True)
class FileInfo:
    relative_path: str
    absolute_path: str
    sha256: str
    size: int


def digest_file(path: Path) -> str:
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


def iter_files(root: Path) -> Iterator[Path]:
    for current, dirs, files in os.walk(
        root,
        topdown=True,
        followlinks=False,
    ):
        dirs[:] = sorted(
            name
            for name in dirs
            if name not in EXCLUDED_DIRS
        )

        current_path = Path(current)

        for name in sorted(files):
            path = current_path / name

            if path.is_symlink():
                continue

            if path.is_file():
                yield path


def inventory(
    root: Path,
) -> dict[str, FileInfo]:
    if not root.is_dir():
        raise RuntimeError(
            f"missing canon root: {root}"
        )

    result: dict[str, FileInfo] = {}

    for path in iter_files(root):
        relative = (
            path.relative_to(root)
            .as_posix()
        )

        result[relative] = FileInfo(
            relative_path=relative,
            absolute_path=str(path),
            sha256=digest_file(path),
            size=path.stat().st_size,
        )

    return result


def tree_digest(
    values: dict[str, FileInfo],
) -> str:
    digest = hashlib.sha256()

    for relative in sorted(values):
        record = values[relative]

        digest.update(
            relative.encode("utf-8")
        )

        digest.update(b"\0")

        digest.update(
            record.sha256.encode("ascii")
        )

        digest.update(b"\0")

    return digest.hexdigest()


def classify(
    legacy: dict[str, FileInfo],
    dimensional: dict[str, FileInfo],
) -> dict[str, object]:
    legacy_paths = set(legacy)
    dimensional_paths = set(dimensional)

    shared = sorted(
        legacy_paths
        & dimensional_paths
    )

    identical_shared = [
        path
        for path in shared
        if legacy[path].sha256
        == dimensional[path].sha256
    ]

    contradictory_shared = [
        path
        for path in shared
        if legacy[path].sha256
        != dimensional[path].sha256
    ]

    legacy_only = sorted(
        legacy_paths
        - dimensional_paths
    )

    dimensional_only = sorted(
        dimensional_paths
        - legacy_paths
    )

    if contradictory_shared:
        classification = (
            "true-content-conflict"
        )

        safe_automatic_action = None

    elif (
        legacy_only
        and not dimensional_only
    ):
        classification = (
            "legacy-strict-superset"
        )

        safe_automatic_action = (
            "copy-missing-legacy-files-"
            "into-dimensional-canon"
        )

    elif (
        dimensional_only
        and not legacy_only
    ):
        classification = (
            "dimensional-strict-superset"
        )

        safe_automatic_action = (
            "no-content-merge-required"
        )

    elif (
        legacy_only
        and dimensional_only
    ):
        classification = (
            "non-conflicting-divergent-"
            "supersets"
        )

        safe_automatic_action = (
            "union-missing-files-"
            "without-overwrite"
        )

    else:
        classification = (
            "identical"
        )

        safe_automatic_action = (
            "retire-legacy-path-"
            "after-backup"
        )

    return {
        "classification": classification,
        "safe_automatic_action": (
            safe_automatic_action
        ),
        "automatic_content_merge_safe": (
            not contradictory_shared
        ),
        "legacy_only": [
            asdict(legacy[path])
            for path in legacy_only
        ],
        "dimensional_only": [
            asdict(dimensional[path])
            for path in dimensional_only
        ],
        "identical_shared": (
            identical_shared
        ),
        "contradictory_shared": [
            {
                "relative_path": path,
                "legacy": asdict(
                    legacy[path]
                ),
                "dimensional": asdict(
                    dimensional[path]
                ),
            }
            for path
            in contradictory_shared
        ],
        "counts": {
            "legacy": len(legacy),
            "dimensional": len(
                dimensional
            ),
            "shared": len(shared),
            "identical_shared": len(
                identical_shared
            ),
            "contradictory_shared": len(
                contradictory_shared
            ),
            "legacy_only": len(
                legacy_only
            ),
            "dimensional_only": len(
                dimensional_only
            ),
        },
    }


def main() -> int:
    legacy = inventory(
        LEGACY_CANON_ROOT
    )

    dimensional = inventory(
        DIMENSIONAL_CANON_ROOT
    )

    decision = classify(
        legacy,
        dimensional,
    )

    report = {
        "schema": (
            "savant://vault/dimensions/"
            "canon-tree-conflict-audit/"
            "2.0.0"
        ),
        "authority": {
            "legacy_path": str(
                LEGACY_CANON_ROOT
            ),
            "dimensional_path": str(
                DIMENSIONAL_CANON_ROOT
            ),
            "dimensional_root_is_"
            "structurally_canonical": True,
            "content_authority_"
            "inferred_from_path": False,
        },
        "mutation_authorized": False,
        "physical_migration_"
        "authorized": False,
        "legacy_tree_digest": (
            tree_digest(legacy)
        ),
        "dimensional_tree_digest": (
            tree_digest(dimensional)
        ),
        **decision,
    }

    REPORT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    REPORT_PATH.write_text(
        json.dumps(
            report,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    summary = {
        "classification": report[
            "classification"
        ],
        "safe_automatic_action": report[
            "safe_automatic_action"
        ],
        "automatic_content_merge_safe": (
            report[
                "automatic_content_merge_safe"
            ]
        ),
        "counts": report["counts"],
        "legacy_tree_digest": report[
            "legacy_tree_digest"
        ],
        "dimensional_tree_digest": (
            report[
                "dimensional_tree_digest"
            ]
        ),
        "report": str(REPORT_PATH),
    }

    print(
        json.dumps(
            summary,
            indent=2,
            sort_keys=True,
        )
    )

    return (
        2
        if report[
            "classification"
        ]
        == "true-content-conflict"
        else 0
    )


if __name__ == "__main__":
    raise SystemExit(main())
