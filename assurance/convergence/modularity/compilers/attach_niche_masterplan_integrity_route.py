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
    "attach-niche-masterplan-integrity-route.v1"
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
    / "masterplan_projection_self_check.py"
)

import_statement = (
    "from masterplan_projection_self_check "
    "import projection_snapshot"
)

route_anchor = '''        if path == "/api/masterplan/lineage":
            self.send_json(
                lineage_projection()
            )
            return

'''

route_source = '''        if path == "/api/masterplan/integrity":
            self.send_json(
                projection_snapshot()
            )
            return

'''


class MigrationError(
    RuntimeError
):
    pass


def compile_python(
    text: str,
    path: Path,
) -> None:
    compile(
        text,
        str(path),
        "exec",
    )


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
) -> bool:
    wanted = import_signature(
        import_statement
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
        text
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
        'if path == "/api/masterplan/integrity":'
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
            "lineage route anchor, "
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
            "masterplan projection integrity "
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
        "def projection_snapshot(",
        "def self_check(",
        '"mutation_authority":',
        '"cross_projection_consistency":',
    )

    missing = [
        fragment
        for fragment
        in required
        if fragment not in text
    ]

    if missing:
        raise MigrationError(
            "masterplan projection integrity "
            "module incomplete: "
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
        'if path == "/api/masterplan/index":',
        'if path == "/api/masterplan/lineage":',
        "lineage_projection()",
    )

    missing = [
        fragment
        for fragment
        in required
        if fragment not in text
    ]

    if missing:
        raise MigrationError(
            "taskboard server shape mismatch: "
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
        'if path == "/api/masterplan/integrity":',
        "projection_snapshot()",
    )

    missing = [
        fragment
        for fragment
        in required
        if fragment not in text
    ]

    if missing:
        raise MigrationError(
            "integrity route integration "
            "incomplete: "
            + ", ".join(
                missing
            )
        )

    if text.count(
        'if path == "/api/masterplan/integrity":'
    ) != 1:
        raise MigrationError(
            "masterplan integrity route "
            "must occur exactly once"
        )

    if text.count(
        "projection_snapshot()"
    ) != 1:
        raise MigrationError(
            "projection snapshot call "
            "must occur exactly once"
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
            "integrity_route":
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
            "/api/masterplan/integrity",
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
