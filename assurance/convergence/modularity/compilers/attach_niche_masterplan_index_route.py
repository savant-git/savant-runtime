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
    "attach-niche-masterplan-index-route.v1"
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
    / "masterplan_index_projection.py"
)

import_statement = (
    "from masterplan_index_projection "
    "import index_projection"
)

route_anchor = '''        if path == "/api/masterplan/summary":
            self.send_json(
                summary_projection()
            )
            return

'''

route_source = '''        if path == "/api/masterplan/index":
            self.send_json(
                index_projection()
            )
            return

'''


class MigrationError(
    RuntimeError
):
    pass


def parse_python(
    text: str,
    path: Path,
) -> ast.Module:
    try:
        return ast.parse(
            text,
            filename=str(path),
        )

    except SyntaxError as exc:
        raise MigrationError(
            f"unable to parse {path}: {exc}"
        ) from exc


def compile_python(
    text: str,
    path: Path,
) -> None:
    compile(
        text,
        str(path),
        "exec",
    )


def import_signature(
    statement: str,
) -> str:
    module = ast.parse(
        statement
    )

    if len(
        module.body
    ) != 1:
        raise MigrationError(
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

    module = parse_python(
        text,
        server_path,
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
    module = parse_python(
        text,
        server_path,
    )

    line = 0

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
            line = int(
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
            line = int(
                node.end_lineno
                or node.lineno
            )
            continue

        break

    return line


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

    compile_python(
        migrated,
        server_path,
    )

    return (
        migrated,
        "added",
    )


def add_route(
    text: str,
) -> tuple[
    str,
    str,
]:
    if (
        'if path == "/api/masterplan/index":'
        in text
    ):
        return (
            text,
            "already_present",
        )

    count = text.count(
        route_anchor
    )

    if count != 1:
        raise MigrationError(
            "expected one masterplan "
            "summary route anchor, "
            f"found {count}"
        )

    migrated = text.replace(
        route_anchor,
        route_anchor
        + route_source,
        1,
    )

    compile_python(
        migrated,
        server_path,
    )

    return (
        migrated,
        "added",
    )


def validate_projection() -> None:
    if not projection_path.is_file():
        raise MigrationError(
            "masterplan index projection "
            "module unavailable"
        )

    text = projection_path.read_text(
        encoding="utf-8"
    )

    compile_python(
        text,
        projection_path,
    )

    required = (
        "def index_projection(",
        "def self_check(",
        '"mutation_authority":',
    )

    missing = [
        fragment
        for fragment
        in required
        if fragment not in text
    ]

    if missing:
        raise MigrationError(
            "index projection module "
            "incomplete: "
            + ", ".join(
                missing
            )
        )


def validate_server(
    text: str,
) -> None:
    compile_python(
        text,
        server_path,
    )

    required = (
        "class TaskboardHandler",
        "def _get(",
        'if path == "/api/masterplan":',
        'if path == "/api/masterplan/summary":',
        "summary_projection()",
        "self.send_json(",
    )

    missing = [
        fragment
        for fragment
        in required
        if fragment not in text
    ]

    if missing:
        raise MigrationError(
            "taskboard server shape "
            "mismatch: "
            + ", ".join(
                missing
            )
        )


def validate_result(
    text: str,
) -> None:
    compile_python(
        text,
        server_path,
    )

    required = (
        import_statement,
        'if path == "/api/masterplan/index":',
        "index_projection()",
    )

    missing = [
        fragment
        for fragment
        in required
        if fragment not in text
    ]

    if missing:
        raise MigrationError(
            "index route integration "
            "incomplete: "
            + ", ".join(
                missing
            )
        )

    if text.count(
        'if path == "/api/masterplan/index":'
    ) != 1:
        raise MigrationError(
            "masterplan index route "
            "must occur once"
        )

    if text.count(
        "index_projection()"
    ) != 1:
        raise MigrationError(
            "index projection call "
            "must occur once"
        )


def transform(
    original: str,
) -> tuple[
    str,
    dict[str, str],
]:
    validate_server(
        original
    )

    migrated = original

    (
        migrated,
        import_disposition,
    ) = add_import(
        migrated
    )

    (
        migrated,
        route_disposition,
    ) = add_route(
        migrated
    )

    validate_result(
        migrated
    )

    return (
        migrated,
        {
            "import":
                import_disposition,
            "index_route":
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
    validate_projection()

    if not server_path.is_file():
        raise MigrationError(
            "taskboard server unavailable"
        )

    original = server_path.read_text(
        encoding="utf-8"
    )

    (
        migrated,
        dispositions,
    ) = transform(
        original
    )

    changed = (
        migrated != original
    )

    if apply and changed:
        atomic_write(
            server_path,
            migrated,
        )

        try:
            current = server_path.read_text(
                encoding="utf-8"
            )

            validate_result(
                current
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
        "owner":
            "exile:niche",
        "mutation_authority_added":
            False,
        "server":
            str(
                server_path
            ),
        "projection_module":
            str(
                projection_path
            ),
        "endpoint":
            "/api/masterplan/index",
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
                        str(
                            exc
                        ),
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
