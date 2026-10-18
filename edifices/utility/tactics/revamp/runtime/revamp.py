#!/usr/bin/env python3
"""revamp: deterministic, read-only source diagnostics."""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
import sys
import tokenize
from pathlib import Path

ROOT = Path("/root/savant-runtime")
SCHEMA = "savant.revamp.diagnostic.v1"
VERSION = "0.1.0"

EXCLUDED_DIRECTORIES = frozenset({
    ".git",
    ".venv",
    "venv",
    "__pycache__",
    ".mypy_cache",
    ".pytest_cache",
})


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical_json(value: object) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def finding(
    code: str,
    message: str,
    *,
    line: int | None = None,
    column: int | None = None,
) -> dict:
    return {
        "code": code,
        "message": message,
        "line": line,
        "column": column,
    }


def inspect_source(path: Path, root: Path) -> dict:
    relative = path.relative_to(root).as_posix()

    record = {
        "path": relative,
        "status": "unknown",
        "size_bytes": None,
        "sha256": None,
        "imports": [],
        "definitions": [],
        "findings": [],
    }

    try:
        if path.is_symlink():
            raise ValueError("symbolic links are not inspected")

        with path.open("rb") as stream:
            source = stream.read()

        record["size_bytes"] = len(source)
        record["sha256"] = sha256(source)

    except (OSError, ValueError) as exc:
        record["status"] = "error"
        record["findings"].append(
            finding(
                "read_failure",
                type(exc).__name__,
            )
        )
        return record

    try:
        readline = iter(
            source.splitlines(keepends=True)
        ).__next__

        encoding, _ = tokenize.detect_encoding(readline)
        text = source.decode(encoding)
        tree = ast.parse(text, filename=relative)

    except (SyntaxError, UnicodeError, LookupError) as exc:
        record["status"] = "error"
        record["findings"].append(
            finding(
                "parse_failure",
                str(exc),
                line=getattr(exc, "lineno", None),
                column=getattr(exc, "offset", None),
            )
        )
        return record

    imports = set()
    definitions = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.add(alias.name)

        elif isinstance(node, ast.ImportFrom):
            imports.add(
                "." * node.level + (node.module or "")
            )

        elif isinstance(
            node,
            (
                ast.FunctionDef,
                ast.AsyncFunctionDef,
                ast.ClassDef,
            ),
        ):
            definitions.append({
                "name": node.name,
                "kind": type(node).__name__,
                "line": node.lineno,
            })

    record["imports"] = sorted(imports)

    record["definitions"] = sorted(
        definitions,
        key=lambda item: (
            item["line"],
            item["name"],
            item["kind"],
        ),
    )

    record["status"] = "parsed"
    return record


def discover(target: Path) -> list[Path]:
    if target.is_symlink():
        raise ValueError("symbolic-link target rejected")

    if target.is_file():
        if target.suffix != ".py":
            raise ValueError("target must be a python file")
        return [target]

    if not target.is_dir():
        raise ValueError("target must be a file or directory")

    discovered = []

    for directory, dirs, files in os.walk(
        target,
        topdown=True,
        followlinks=False,
    ):
        base = Path(directory)

        dirs[:] = sorted(
            name
            for name in dirs
            if name not in EXCLUDED_DIRECTORIES
            and not (base / name).is_symlink()
        )

        for name in sorted(files):
            path = base / name

            if (
                path.suffix == ".py"
                and not path.is_symlink()
            ):
                discovered.append(path)

    return sorted(
        discovered,
        key=lambda path: path.as_posix(),
    )


def inspect(target: Path, root: Path) -> dict:
    records = [
        inspect_source(path, root)
        for path in discover(target)
    ]

    report = {
        "schema": SCHEMA,
        "version": VERSION,
        "mode": "read_only",
        "edifice": "utility",
        "proposed_level": "tactic",
        "classification_status": "unverified",
        "scope": target.relative_to(root).as_posix(),
        "summary": {
            "files": len(records),
            "parsed": sum(
                item["status"] == "parsed"
                for item in records
            ),
            "errors": sum(
                item["status"] == "error"
                for item in records
            ),
            "source_bytes": sum(
                item["size_bytes"] or 0
                for item in records
            ),
        },
        "files": records,
    }

    report["report_sha256"] = sha256(
        canonical_json(report)
    )

    return report


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "revamp: deterministic, read-only "
            "python source diagnostics"
        )
    )

    parser.add_argument(
        "target",
        help="python file or directory inside savant",
    )

    parser.add_argument(
        "--compact",
        action="store_true",
        help="emit compact json",
    )

    args = parser.parse_args()

    try:
        root = ROOT.resolve(strict=True)

        if not root.is_dir():
            raise ValueError("runtime root is not a directory")

        requested = Path(args.target)

        if requested.is_absolute():
            target = requested.resolve(strict=True)
        else:
            target = (root / requested).resolve(strict=True)

        if not target.is_relative_to(root):
            raise ValueError("target escapes runtime root")

        report = inspect(target, root)

    except (OSError, ValueError) as exc:
        print(
            json.dumps(
                {
                    "status": "error",
                    "message": str(exc),
                },
                sort_keys=True,
            ),
            file=sys.stderr,
        )
        return 2

    print(
        json.dumps(
            report,
            ensure_ascii=False,
            sort_keys=True,
            indent=None if args.compact else 2,
            separators=(",", ":") if args.compact else None,
        )
    )

    return 1 if report["summary"]["errors"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
