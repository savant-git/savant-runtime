#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
from typing import Any, Iterator


schema = "savant://runtime/sieve/source-custody/2.0.1"
owner = "sieve"
authority_effect = "none"

chunk_size = 1024 * 1024


class source_custody_error(RuntimeError):
    pass


def canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )


def digest(value: Any) -> str:
    return hashlib.sha256(
        canonical_json(value).encode("utf-8")
    ).hexdigest()


def file_digest(path: Path) -> str:
    hasher = hashlib.sha256()

    with path.open("rb") as handle:
        while True:
            block = handle.read(chunk_size)

            if not block:
                break

            hasher.update(block)

    return hasher.hexdigest()


def iter_files(root: Path) -> Iterator[Path]:
    if root.is_file():
        yield root
        return

    for directory, names, files in os.walk(root):
        names.sort()
        files.sort()

        base = Path(directory)

        for name in files:
            path = base / name

            if path.is_file():
                yield path


def relative_path(
    path: Path,
    root: Path,
) -> str:
    if root.is_file():
        return root.name

    return path.relative_to(root).as_posix()


def file_identity(
    path: Path,
    root: Path,
) -> dict[str, Any]:
    stat = path.stat()

    return {
        "path": relative_path(
            path,
            root,
        ),
        "size": stat.st_size,
        "sha256": file_digest(path),
    }


def census(root: Path) -> dict[str, Any]:
    root = root.resolve()

    if not root.exists():
        raise source_custody_error(
            f"source does not exist: {root}"
        )

    files: list[dict[str, Any]] = []
    total_bytes = 0

    for path in iter_files(root):
        identity = file_identity(
            path,
            root,
        )

        files.append(identity)
        total_bytes += int(
            identity["size"]
        )

    files.sort(
        key=lambda item: item["path"]
    )

    identity_projection = {
        "source_kind": (
            "file"
            if root.is_file()
            else "directory"
        ),
        "file_count": len(files),
        "total_bytes": total_bytes,
        "files": files,
    }

    result = {
        "schema": schema,
        "owner": owner,
        "authority_effect": authority_effect,
        "authoritative": False,
        "destructive": False,
        "source": str(root),
        "source_kind": (
            identity_projection[
                "source_kind"
            ]
        ),
        "file_count": len(files),
        "total_bytes": total_bytes,
        "files": files,
        "boundaries": {
            "creates_authority": False,
            "changes_canon": False,
            "changes_source": False,
            "normalizes_source": False,
            "deletes_source": False,
            "source_bytes_are_immutable": True,
            "derived_projection_only": True,
        },
    }

    result["source_identity_digest"] = digest(
        identity_projection
    )

    digest_projection = dict(result)
    digest_projection.pop(
        "source",
        None,
    )

    result["projection_digest"] = digest(
        digest_projection
    )

    return result


def selftest() -> dict[str, Any]:
    checks = {
        "authority_none": (
            authority_effect == "none"
        ),
        "owner_sieve": (
            owner == "sieve"
        ),
        "sha256_length": (
            len(
                digest(
                    {
                        "a": 1,
                    }
                )
            )
            == 64
        ),
        "canonical_stability": (
            digest(
                {
                    "a": 1,
                    "b": 2,
                }
            )
            == digest(
                {
                    "b": 2,
                    "a": 1,
                }
            )
        ),
    }

    return {
        "schema": (
            "savant://runtime/sieve/"
            "source-custody-selftest/2.0.1"
        ),
        "ok": all(
            checks.values()
        ),
        "checks": checks,
    }


def render_result(
    result: dict[str, Any],
) -> str:
    return json.dumps(
        result,
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
    )


def write_result(
    output: Path,
    rendered: str,
) -> None:
    output = output.resolve()

    output.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    output.write_text(
        rendered + "\n",
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--selftest",
        action="store_true",
    )

    parser.add_argument(
        "--source",
    )

    parser.add_argument(
        "--output",
    )

    arguments = parser.parse_args()

    if arguments.selftest:
        result = selftest()

    else:
        if not arguments.source:
            parser.error(
                "--source is required unless "
                "--selftest is used"
            )

        result = census(
            Path(
                arguments.source
            )
        )

    rendered = render_result(
        result
    )

    if arguments.output:
        write_result(
            Path(
                arguments.output
            ),
            rendered,
        )

    # stdout is part of the executable contract.
    # recovery_pipeline.py consumes this JSON directly.
    print(
        rendered,
        flush=True,
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
