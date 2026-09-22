#!/usr/bin/env python3

from __future__ import annotations

import argparse
import ast
import json
import os
import tempfile
from pathlib import Path
from typing import Any


schema_version = (
    "savant.assurance."
    "attach-niche-masterplan-projection.v1"
)

authority_effect = "none"

runtime_root = Path(
    "/root/savant-runtime"
)

taskboard_root = (
    runtime_root
    / "ontology"
    / "obelisks"
    / "_template"
    / "segue"
    / "gates"
    / "_template"
    / "segue"
    / "innates"
    / "_template"
    / "segue"
    / "exiles"
    / "niche"
    / "apps"
    / "taskboard"
)

server_path = (
    taskboard_root
    / "server.py"
)

projection_path = (
    taskboard_root
    / "masterplan_projection.py"
)

import_statement = (
    "from masterplan_projection "
    "import masterplan_projection"
)

route_marker = (
    'if path == "/api/history":'
)

route_source = '''
        if path == "/api/masterplan":
            self.send_json(
                masterplan_projection()
            )
            return

'''


def compile_text(
    text: str,
    path: Path,
) -> None:
    compile(
        text,
        str(path),
        "exec",
    )


def parse_module(
    text: str,
    path: Path,
) -> ast.Module:
    try:
        return ast.parse(
            text,
            filename=str(path),
        )

    except SyntaxError as exc:
        raise RuntimeError(
            f"unable to parse {path}: {exc}"
        ) from exc


def import_signature(
    statement: str,
) -> str:
    module = ast.parse(
        statement
    )

    if len(
        module.body
    ) != 1:
        raise RuntimeError(
            "invalid import statement"
        )

    return ast.dump(
        module.body[0],
        annotate_fields=True,
        include_attributes=False,
    )


def has_import(
    text: str,
    statement: str,
) -> bool:
    wanted = import_signature(
        statement
    )

    module = ast.parse(
        text
    )

    for node in module.body:
        if not isinstance(
            node,
            (
                ast.Import,
                ast.ImportFrom,
            ),
        ):
            continue

        current = ast.dump(
            node,
            annotate_fields=True,
            include_attributes=False,
        )

        if current == wanted:
            return True

    return False


def import_insertion_line(
    text: str,
) -> int:
    module = parse_module(
        text,
        server_path,
    )

    last_import = 0

    for node in module.body:
        if (
            isinstance(
                node,
                ast.Expr,
            )
            and isinstance(
                node.value,
                ast.Constant,
            )
            and isinstance(
                node.value.value,
                str,
            )
        ):
            last_import = int(
                node.end_lineno
                or node.lineno
            )
            continue

        if isinstance(
            node,
            (
                ast.Import,
                ast.ImportFrom,
            ),
        ):
            last_import = int(
                node.end_lineno
                or node.lineno
            )
            continue

        break

    return last_import


def add_import(
    text: str,
) -> tuple[
    str,
    str,
]:
    if has_import(
        text,
        import_statement,
    ):
        return (
            text,
            "already_present",
        )

    lines = text.splitlines(
        keepends=True
    )

    lines.insert(
        import_insertion_line(
            text
        ),
        import_statement + "\n",
    )

    migrated = "".join(
        lines
    )

    compile_text(
        migrated,
        server_path,
    )

    return (
        migrated,
        "added",
    )


def route_present(
    text: str,
) -> bool:
    return (
        'path == "/api/masterplan"'
        in text
    )


def add_route(
    text: str,
) -> tuple[
    str,
    str,
]:
    if route_present(
        text
    ):
        return (
            text,
            "already_present",
        )

    count = text.count(
        route_marker
    )

    if count != 1:
        raise RuntimeError(
            "expected exactly one "
            "/api/history route anchor, "
            f"found {count}"
        )

    replacement = (
        route_source
        + "        "
        + route_marker
    )

    migrated = text.replace(
        "        " + route_marker,
        replacement,
        1,
    )

    compile_text(
        migrated,
        server_path,
    )

    return (
        migrated,
        "added",
    )


def verify_live_shape(
    text: str,
) -> None:
    required_fragments = (
        "class TaskboardHandler",
        "def _get(",
        'if path == "/api/health":',
        'if path == "/api/dashboard":',
        'if path == "/api/state":',
        'if path == "/api/history":',
        "self.send_json(",
    )

    missing = [
        fragment
        for fragment
        in required_fragments
        if fragment not in text
    ]

    if missing:
        raise RuntimeError(
            "live taskboard server "
            "does not match required "
            "integration shape: "
            + ", ".join(
                missing
            )
        )


def transform() -> tuple[
    str,
    dict[str, str],
]:
    if not server_path.is_file():
        raise RuntimeError(
            "taskboard server unavailable"
        )

    if not projection_path.is_file():
        raise RuntimeError(
            "masterplan projection "
            "module unavailable"
        )

    projection_text = (
        projection_path.read_text(
            encoding="utf-8"
        )
    )

    compile_text(
        projection_text,
        projection_path,
    )

    original = server_path.read_text(
        encoding="utf-8"
    )

    verify_live_shape(
        original
    )

    (
        migrated,
        import_disposition,
    ) = add_import(
        original
    )

    (
        migrated,
        route_disposition,
    ) = add_route(
        migrated
    )

    compile_text(
        migrated,
        server_path,
    )

    return (
        migrated,
        {
            "import":
                import_disposition,
            "route":
                route_disposition,
        },
    )


def atomic_write(
    path: Path,
    text: str,
) -> None:
    mode = path.stat().st_mode

    descriptor, temporary_name = (
        tempfile.mkstemp(
            prefix=path.name + ".",
            suffix=".tmp",
            dir=str(
                path.parent
            ),
        )
    )

    temporary = Path(
        temporary_name
    )

    try:
        with os.fdopen(
            descriptor,
            "w",
            encoding="utf-8",
            newline="",
        ) as handle:
            handle.write(
                text
            )
            handle.flush()

            os.fsync(
                handle.fileno()
            )

        os.chmod(
            temporary,
            mode,
        )

        os.replace(
            temporary,
            path,
        )

    finally:
        if temporary.exists():
            temporary.unlink()


def migrate(
    apply: bool,
) -> dict[str, Any]:
    original = server_path.read_text(
        encoding="utf-8"
    )

    (
        migrated,
        dispositions,
    ) = transform()

    changed = (
        migrated != original
    )

    if apply and changed:
        atomic_write(
            server_path,
            migrated,
        )

        try:
            compile_text(
                server_path.read_text(
                    encoding="utf-8"
                ),
                server_path,
            )

        except Exception:
            atomic_write(
                server_path,
                original,
            )
            raise

    return {
        "schema":
            schema_version,
        "authority_effect":
            authority_effect,
        "status":
            "passed",
        "apply":
            apply,
        "changed":
            changed,
        "server":
            str(
                server_path
            ),
        "projection_module":
            str(
                projection_path
            ),
        "endpoint":
            "/api/masterplan",
        "dispositions":
            dispositions,
    }


def main() -> int:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--apply",
        action="store_true",
    )

    arguments = parser.parse_args()

    try:
        result = migrate(
            arguments.apply
        )

    except Exception as exc:
        print(
            json.dumps(
                {
                    "schema":
                        schema_version,
                    "authority_effect":
                        authority_effect,
                    "apply":
                        arguments.apply,
                    "status":
                        "failed",
                    "error":
                        str(exc),
                },
                indent=2,
                sort_keys=True,
            )
        )

        return 1

    print(
        json.dumps(
            result,
            indent=2,
            sort_keys=True,
        )
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
