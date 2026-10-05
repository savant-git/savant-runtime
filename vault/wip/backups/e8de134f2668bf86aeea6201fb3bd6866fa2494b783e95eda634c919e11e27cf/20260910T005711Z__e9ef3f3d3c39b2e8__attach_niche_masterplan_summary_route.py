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
    "attach-niche-masterplan-summary-route.v1"
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

old_import = (
    "from masterplan_projection "
    "import masterplan_projection"
)

new_import = (
    "from masterplan_projection import "
    "masterplan_projection, summary_projection"
)

masterplan_route_anchor = '''        if path == "/api/masterplan":
            self.send_json(
                masterplan_projection()
            )
            return

'''

summary_route = '''        if path == "/api/masterplan/summary":
            self.send_json(
                summary_projection()
            )
            return

'''

required_projection_symbols = (
    "def masterplan_projection(",
    "def summary_projection(",
)

required_server_fragments = (
    "class TaskboardHandler",
    "def _get(",
    'if path == "/api/masterplan":',
    "masterplan_projection()",
    "self.send_json(",
)


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


def validate_projection_module() -> None:
    if not projection_path.is_file():
        raise MigrationError(
            "masterplan projection module "
            "unavailable"
        )

    text = projection_path.read_text(
        encoding="utf-8"
    )

    compile_python(
        text,
        projection_path,
    )

    missing = [
        symbol
        for symbol
        in required_projection_symbols
        if symbol not in text
    ]

    if missing:
        raise MigrationError(
            "masterplan projection module "
            "does not expose required symbols: "
            + ", ".join(
                missing
            )
        )


def validate_server_shape(
    text: str,
) -> None:
    compile_python(
        text,
        server_path,
    )

    missing = [
        fragment
        for fragment
        in required_server_fragments
        if fragment not in text
    ]

    if missing:
        raise MigrationError(
            "taskboard server shape mismatch: "
            + ", ".join(
                missing
            )
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


def has_exact_import(
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


def upgrade_import(
    text: str,
) -> tuple[
    str,
    str,
]:
    if has_exact_import(
        text,
        new_import,
    ):
        return (
            text,
            "already_present",
        )

    count = text.count(
        old_import
    )

    if count != 1:
        raise MigrationError(
            "expected one existing "
            "masterplan_projection import, "
            f"found {count}"
        )

    migrated = text.replace(
        old_import,
        new_import,
        1,
    )

    compile_python(
        migrated,
        server_path,
    )

    return (
        migrated,
        "upgraded",
    )


def add_summary_route(
    text: str,
) -> tuple[
    str,
    str,
]:
    if (
        'if path == "/api/masterplan/summary":'
        in text
    ):
        return (
            text,
            "already_present",
        )

    count = text.count(
        masterplan_route_anchor
    )

    if count != 1:
        raise MigrationError(
            "expected one masterplan "
            "route anchor, "
            f"found {count}"
        )

    migrated = text.replace(
        masterplan_route_anchor,
        masterplan_route_anchor
        + summary_route,
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


def validate_result(
    text: str,
) -> None:
    compile_python(
        text,
        server_path,
    )

    required = (
        new_import,
        'if path == "/api/masterplan":',
        'if path == "/api/masterplan/summary":',
        "masterplan_projection()",
        "summary_projection()",
    )

    missing = [
        fragment
        for fragment
        in required
        if fragment not in text
    ]

    if missing:
        raise MigrationError(
            "transformed server incomplete: "
            + ", ".join(
                missing
            )
        )

    if text.count(
        'if path == "/api/masterplan/summary":'
    ) != 1:
        raise MigrationError(
            "masterplan summary route "
            "must occur exactly once"
        )

    if text.count(
        "summary_projection()"
    ) != 1:
        raise MigrationError(
            "summary projection call "
            "must occur exactly once"
        )


def transform(
    original: str,
) -> tuple[
    str,
    dict[str, str],
]:
    validate_server_shape(
        original
    )

    migrated = original

    (
        migrated,
        import_disposition,
    ) = upgrade_import(
        migrated
    )

    (
        migrated,
        route_disposition,
    ) = add_summary_route(
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
            "summary_route":
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

    temporary_path = Path(
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
            temporary_path,
            mode,
        )

        os.replace(
            temporary_path,
            path,
        )

    finally:
        if temporary_path.exists():
            temporary_path.unlink()


def migrate(
    apply: bool,
) -> dict[str, Any]:
    validate_projection_module()

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
            "/api/masterplan/summary",
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
