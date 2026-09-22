from __future__ import annotations

from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3
import subprocess
import time
from typing import Any, Iterable, Mapping

from .model import Projection


schema = "savant.sdump.palaver-context.v5.1"


runtime_root = Path(
    "/root/savant-runtime"
).resolve(
    strict=False
)


living_state_root = (
    runtime_root
    / "runtime"
    / "living-state"
)


systemd_roots = (
    Path(
        "/etc/systemd/system"
    ),
    Path(
        "/lib/systemd/system"
    ),
)


nginx_roots = (
    Path(
        "/etc/nginx"
    ),
)


external_entrypoints = (
    Path(
        "/usr/local/bin/sdump"
    ),
    Path(
        "/usr/local/bin/savant-state"
    ),
)


sqlite_suffixes = frozenset(
    {
        ".db",
        ".sqlite",
        ".sqlite3",
    }
)


safe_head_columns = frozenset(
    {
        "id",
        "record_id",
        "decision_id",
        "revision_id",
        "version",
        "revision",
        "sequence",
        "generation",
        "epoch",
        "status",
        "state",
        "authority",
        "tier",
        "accepted",
        "active",
        "created_at",
        "updated_at",
        "modified_at",
        "timestamp",
        "created_ns",
        "updated_ns",
        "mtime_ns",
    }
)


sensitive_key_pattern = re.compile(
    (
        r"(?:"
        r"secret|password|passwd|token|"
        r"credential|private[_-]?key|"
        r"api[_-]?key|access[_-]?key"
        r")"
    ),
    re.IGNORECASE,
)


env_assignment_pattern = re.compile(
    r"^(\s*(?:export\s+)?)([A-Za-z_][A-Za-z0-9_]*)(\s*=\s*)(.*)$"
)


systemd_environment_pattern = re.compile(
    r"^(\s*Environment\s*=\s*)(.*)$",
    re.IGNORECASE,
)


generic_secret_pattern = re.compile(
    (
        r"(?i)"
        r"("
        r"(?:password|passwd|secret|token|"
        r"api[_-]?key|access[_-]?key|"
        r"private[_-]?key|credential)"
        r"\s*[:=]\s*"
        r")"
        r"([^\s,;\"']+)"
    )
)


bearer_pattern = re.compile(
    r"(?i)(authorization\s*:\s*bearer\s+)([^\s]+)"
)


aws_access_pattern = re.compile(
    r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b"
)


private_key_pattern = re.compile(
    (
        r"-----BEGIN [^-]*PRIVATE KEY-----"
        r".*?"
        r"-----END [^-]*PRIVATE KEY-----"
    ),
    re.DOTALL,
)


def compact_json(
    value: Any,
) -> str:
    try:
        import orjson

        return orjson.dumps(
            value,
            option=orjson.OPT_SORT_KEYS,
        ).decode(
            "utf-8"
        )

    except ImportError:
        return json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(
                ",",
                ":",
            ),
        )


def stable_hash(
    value: Any,
) -> str:
    return hashlib.sha256(
        compact_json(
            value
        ).encode(
            "utf-8"
        )
    ).hexdigest()


def sha256_file(
    path: Path,
) -> str | None:
    digest = hashlib.sha256()

    try:
        with path.open(
            "rb"
        ) as handle:
            while True:
                chunk = handle.read(
                    1024 * 1024
                )

                if not chunk:
                    break

                digest.update(
                    chunk
                )

    except OSError:
        return None

    return digest.hexdigest()


def run(
    command: list[str],
    timeout: float = 8.0,
) -> dict[str, Any]:
    try:
        result = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
            timeout=timeout,
            env={
                **os.environ,
                "LC_ALL": "C",
            },
        )

        return {
            "ok":
                result.returncode == 0,
            "returncode":
                result.returncode,
            "stdout":
                result.stdout,
            "stderr":
                result.stderr,
        }

    except Exception as error:
        return {
            "ok": False,
            "error":
                type(
                    error
                ).__name__,
            "message":
                str(
                    error
                ),
        }


def redact_text(
    text: str,
) -> tuple[
    str,
    int,
]:
    redactions = 0

    output = private_key_pattern.sub(
        "[redacted-private-key]",
        text,
    )

    if output != text:
        redactions += 1

    lines = []

    for line in output.splitlines(
        keepends=True
    ):
        match = env_assignment_pattern.match(
            line.rstrip(
                "\r\n"
            )
        )

        if match:
            key = match.group(
                2
            )

            if sensitive_key_pattern.search(
                key
            ):
                newline = (
                    "\n"
                    if line.endswith(
                        "\n"
                    )
                    else ""
                )

                line = (
                    match.group(
                        1
                    )
                    + key
                    + match.group(
                        3
                    )
                    + "[redacted]"
                    + newline
                )

                redactions += 1

        environment = (
            systemd_environment_pattern.match(
                line.rstrip(
                    "\r\n"
                )
            )
        )

        if environment:
            payload = environment.group(
                2
            )

            tokens = re.findall(
                (
                    r"(?:\"[^\"]*\"|'[^']*'|\S+)"
                ),
                payload,
            )

            rewritten = []

            for token in tokens:
                raw = token.strip(
                    "\"'"
                )

                key, separator, value = (
                    raw.partition(
                        "="
                    )
                )

                if (
                    separator
                    and sensitive_key_pattern.search(
                        key
                    )
                ):
                    quote = (
                        token[
                            0
                        ]
                        if token[
                            :1
                        ]
                        in {
                            "\"",
                            "'",
                        }
                        else ""
                    )

                    token = (
                        quote
                        + key
                        + "=[redacted]"
                        + quote
                    )

                    redactions += 1

                rewritten.append(
                    token
                )

            newline = (
                "\n"
                if line.endswith(
                    "\n"
                )
                else ""
            )

            line = (
                environment.group(
                    1
                )
                + " ".join(
                    rewritten
                )
                + newline
            )

        line, count = (
            generic_secret_pattern.subn(
                r"\1[redacted]",
                line,
            )
        )

        redactions += count

        line, count = (
            bearer_pattern.subn(
                r"\1[redacted]",
                line,
            )
        )

        redactions += count

        line, count = (
            aws_access_pattern.subn(
                "[redacted-aws-access-key]",
                line,
            )
        )

        redactions += count

        lines.append(
            line
        )

    return (
        "".join(
            lines
        ),
        redactions,
    )


def stable_read_text(
    path: Path,
    attempts: int = 3,
    max_bytes: int = (
        4
        * 1024
        * 1024
    ),
) -> dict[str, Any]:
    result: dict[
        str,
        Any,
    ] = {
        "path":
            str(
                path
            ),
        "exists":
            path.is_file(),
        "authority_effect":
            "none",
    }

    if not path.is_file():
        return result

    for _ in range(
        max(
            1,
            attempts,
        )
    ):
        try:
            before = path.stat()

            if (
                before.st_size
                > max_bytes
            ):
                result.update(
                    {
                        "included":
                            False,
                        "reason":
                            "safe_text_limit_exceeded",
                        "size":
                            before.st_size,
                        "sha256":
                            sha256_file(
                                path
                            ),
                    }
                )

                return result

            text = path.read_text(
                encoding="utf-8",
                errors="replace",
            )

            after = path.stat()

        except OSError as error:
            result.update(
                {
                    "included":
                        False,
                    "reason":
                        type(
                            error
                        ).__name__,
                }
            )

            return result

        if (
            before.st_ino
            == after.st_ino
            and before.st_size
            == after.st_size
            and before.st_mtime_ns
            == after.st_mtime_ns
        ):
            redacted, count = (
                redact_text(
                    text
                )
            )

            result.update(
                {
                    "included":
                        True,
                    "size":
                        before.st_size,
                    "mtime_ns":
                        before.st_mtime_ns,
                    "sha256":
                        hashlib.sha256(
                            text.encode(
                                "utf-8"
                            )
                        ).hexdigest(),
                    "rendered_sha256":
                        hashlib.sha256(
                            redacted.encode(
                                "utf-8"
                            )
                        ).hexdigest(),
                    "redactions":
                        count,
                    "content":
                        redacted,
                }
            )

            return result

        time.sleep(
            0.02
        )

    result.update(
        {
            "included":
                False,
            "reason":
                "changed_during_context_read",
            "sha256":
                sha256_file(
                    path
                ),
        }
    )

    return result


def relevant_systemd_units() -> list[
    Path
]:
    names: set[str] = {
        "nginx.service",
        "cloudflared.service",
        "palaver.service",
        "palaver-attachment.service",
        "palaver-frontend.service",
        "palaver-tunnel.service",
        "palaver-voice-backend.service",
        "palaver-doctor.service",
        "savant-living-state.service",
    }

    result = run(
        [
            "systemctl",
            "list-unit-files",
            "--type=service",
            "--no-legend",
            "--no-pager",
        ]
    )

    if result.get(
        "ok"
    ):
        for line in str(
            result.get(
                "stdout",
                ""
            )
        ).splitlines():
            columns = line.split()

            if not columns:
                continue

            name = columns[
                0
            ]

            lowered = (
                name.casefold()
            )

            if any(
                token
                in lowered
                for token
                in (
                    "savant",
                    "palaver",
                    "nginx",
                    "cloudflared",
                )
            ):
                names.add(
                    name
                )

    paths: set[Path] = set()

    for name in names:
        show = run(
            [
                "systemctl",
                "show",
                name,
                "--property=FragmentPath",
                "--value",
                "--no-pager",
            ]
        )

        fragment = str(
            show.get(
                "stdout",
                ""
            )
        ).strip()

        if fragment:
            path = Path(
                fragment
            )

            if path.is_file():
                paths.add(
                    path
                )

                continue

        for root in systemd_roots:
            candidate = (
                root
                / name
            )

            if candidate.is_file():
                paths.add(
                    candidate
                )

                break

    return sorted(
        paths,
        key=lambda path:
            str(
                path
            ).casefold(),
    )


def deployment_configuration() -> dict[str, Any]:
    systemd = [
        stable_read_text(
            path,
            max_bytes=(
                1024
                * 1024
            ),
        )
        for path
        in relevant_systemd_units()
    ]

    nginx_paths: set[
        Path
    ] = set()

    primary = Path(
        "/etc/nginx/nginx.conf"
    )

    if primary.is_file():
        nginx_paths.add(
            primary
        )

    for root in (
        Path(
            "/etc/nginx/sites-enabled"
        ),
        Path(
            "/etc/nginx/conf.d"
        ),
    ):
        if not root.is_dir():
            continue

        for path in root.iterdir():
            if (
                path.is_file()
                or path.is_symlink()
            ):
                try:
                    resolved = path.resolve(
                        strict=True
                    )

                except OSError:
                    continue

                if resolved.is_file():
                    nginx_paths.add(
                        resolved
                    )

    nginx = [
        stable_read_text(
            path,
            max_bytes=(
                2
                * 1024
                * 1024
            ),
        )
        for path
        in sorted(
            nginx_paths,
            key=lambda item:
                str(
                    item
                ).casefold(),
        )
    ]

    entrypoints = [
        stable_read_text(
            path,
            max_bytes=(
                2
                * 1024
                * 1024
            ),
        )
        for path
        in external_entrypoints
    ]

    return {
        "schema":
            "savant.sdump.deployment-evidence.v1",
        "projection_only":
            True,
        "authority_effect":
            "none",
        "secret_values_serialized":
            False,
        "systemd":
            systemd,
        "nginx":
            nginx,
        "entrypoints":
            entrypoints,
    }


def relevant_service_names() -> list[
    str
]:
    result = run(
        [
            "systemctl",
            "list-unit-files",
            "--type=service",
            "--no-legend",
            "--no-pager",
        ]
    )

    names: set[str] = {
        "nginx.service",
        "cloudflared.service",
        "palaver.service",
        "palaver-attachment.service",
        "palaver-frontend.service",
        "palaver-tunnel.service",
        "palaver-voice-backend.service",
        "palaver-doctor.service",
        "savant-living-state.service",
    }

    if result.get(
        "ok"
    ):
        for line in str(
            result.get(
                "stdout",
                ""
            )
        ).splitlines():
            columns = line.split()

            if not columns:
                continue

            name = columns[
                0
            ]

            lowered = (
                name.casefold()
            )

            if any(
                token
                in lowered
                for token
                in (
                    "savant",
                    "palaver",
                    "nginx",
                    "cloudflared",
                )
            ):
                names.add(
                    name
                )

    return sorted(
        names,
        key=str.casefold,
    )


def service_diagnostics() -> dict[str, Any]:
    records = []

    for name in relevant_service_names():
        show = run(
            [
                "systemctl",
                "show",
                name,
                "--no-pager",
                "--property=LoadState",
                "--property=ActiveState",
                "--property=SubState",
                "--property=Result",
                "--property=ExecMainCode",
                "--property=ExecMainStatus",
                "--property=NRestarts",
                "--property=MainPID",
                "--property=ActiveEnterTimestamp",
                "--property=InactiveEnterTimestamp",
            ]
        )

        fields = {}

        for line in str(
            show.get(
                "stdout",
                ""
            )
        ).splitlines():
            key, separator, value = (
                line.partition(
                    "="
                )
            )

            if separator:
                fields[
                    key
                ] = value

        state = fields.get(
            "ActiveState"
        )

        result = fields.get(
            "Result"
        )

        include_journal = (
            state
            in {
                "failed",
                "activating",
                "deactivating",
            }
            or (
                result
                and result
                not in {
                    "success",
                    "done",
                }
            )
        )

        journal_lines = []

        if include_journal:
            journal = run(
                [
                    "journalctl",
                    "-u",
                    name,
                    "--no-pager",
                    "-n",
                    "30",
                    "-o",
                    "short-iso",
                ],
                timeout=10.0,
            )

            text = str(
                journal.get(
                    "stdout",
                    ""
                )
            )

            redacted, _ = (
                redact_text(
                    text
                )
            )

            journal_lines = (
                redacted.splitlines()[
                    -30:
                ]
            )

        records.append(
            {
                "name":
                    name,
                "load_state":
                    fields.get(
                        "LoadState"
                    ),
                "active_state":
                    state,
                "sub_state":
                    fields.get(
                        "SubState"
                    ),
                "result":
                    result,
                "exec_main_code":
                    fields.get(
                        "ExecMainCode"
                    ),
                "exec_main_status":
                    fields.get(
                        "ExecMainStatus"
                    ),
                "restart_count":
                    fields.get(
                        "NRestarts"
                    ),
                "main_pid":
                    fields.get(
                        "MainPID"
                    ),
                "active_enter":
                    fields.get(
                        "ActiveEnterTimestamp"
                    ),
                "inactive_enter":
                    fields.get(
                        "InactiveEnterTimestamp"
                    ),
                "journal_tail":
                    journal_lines,
                "journal_serialized":
                    bool(
                        journal_lines
                    ),
                "secret_values_serialized":
                    False,
            }
        )

    return {
        "schema":
            "savant.sdump.service-diagnostics.v1",
        "projection_only":
            True,
        "authority_effect":
            "none",
        "services":
            records,
    }


def full_large_file_hashes(
    projection: Projection,
    targets: Iterable[Path],
) -> dict[str, Any]:
    target_list = list(
        targets
    )

    records = []

    for skipped in projection.skipped:
        if (
            skipped.reason
            != "max_file_bytes_exceeded"
        ):
            continue

        resolved: Path | None = None

        if len(
            target_list
        ) == 1:
            base = target_list[
                0
            ]

            if base.is_dir():
                candidate = (
                    base
                    / skipped.path
                )

                if candidate.is_file():
                    resolved = candidate

        else:
            first, separator, rest = (
                skipped.path.partition(
                    "/"
                )
            )

            if separator:
                for base in target_list:
                    if (
                        base.name
                        != first
                    ):
                        continue

                    candidate = (
                        base
                        / rest
                    )

                    if candidate.is_file():
                        resolved = candidate
                        break

        record: dict[
            str,
            Any,
        ] = {
            "path":
                skipped.path,
            "size":
                skipped.size,
            "reason":
                skipped.reason,
            "content_included":
                False,
            "authority_effect":
                "none",
        }

        if resolved is not None:
            try:
                info = resolved.stat()

                record[
                    "mtime_ns"
                ] = info.st_mtime_ns

                record[
                    "sha256"
                ] = sha256_file(
                    resolved
                )

            except OSError:
                record[
                    "sha256"
                ] = None

        records.append(
            record
        )

    return {
        "schema":
            "savant.sdump.large-object-evidence.v1",
        "hash_algorithm":
            "sha256",
        "streaming":
            True,
        "size_ceiling":
            None,
        "content_included":
            False,
        "objects":
            records,
    }


def iter_sqlite_files() -> Iterable[
    Path
]:
    for root, directories, filenames in os.walk(
        runtime_root
    ):
        directories[:] = [
            name
            for name
            in directories
            if name
            not in {
                ".git",
                "__pycache__",
                "node_modules",
                ".venv",
                ".venv_voice",
                ".venv_extract",
            }
        ]

        base = Path(
            root
        )

        for name in filenames:
            path = (
                base
                / name
            )

            if (
                path.suffix.casefold()
                in sqlite_suffixes
            ):
                yield path


def sql_identifier(
    value: str,
) -> str:
    return (
        "\""
        + value.replace(
            "\"",
            "\"\"",
        )
        + "\""
    )


def sqlite_semantic_heads() -> dict[str, Any]:
    databases = []

    for path in sorted(
        iter_sqlite_files(),
        key=lambda item:
            str(
                item
            ).casefold(),
    ):
        try:
            relative = str(
                path.relative_to(
                    runtime_root
                )
            )

        except ValueError:
            continue

        database: dict[
            str,
            Any,
        ] = {
            "path":
                relative,
            "sha256":
                sha256_file(
                    path
                ),
            "content_serialized":
                False,
            "authority_effect":
                "none",
            "tables":
                [],
        }

        try:
            connection = sqlite3.connect(
                f"file:{path}?mode=ro",
                uri=True,
                timeout=2.0,
            )

        except sqlite3.Error as error:
            database[
                "error"
            ] = type(
                error
            ).__name__

            databases.append(
                database
            )

            continue

        try:
            table_names = [
                str(
                    row[
                        0
                    ]
                )
                for row
                in connection.execute(
                    (
                        "SELECT name "
                        "FROM sqlite_master "
                        "WHERE type='table' "
                        "AND name NOT LIKE 'sqlite_%' "
                        "ORDER BY name"
                    )
                )
            ]

            for table in table_names[
                :200
            ]:
                table_id = sql_identifier(
                    table
                )

                try:
                    column_rows = (
                        connection.execute(
                            (
                                "PRAGMA table_info("
                                + table_id
                                + ")"
                            )
                        ).fetchall()
                    )

                except sqlite3.Error:
                    continue

                columns = [
                    str(
                        row[
                            1
                        ]
                    )
                    for row
                    in column_rows
                ]

                safe_columns = [
                    column
                    for column
                    in columns
                    if (
                        column.casefold()
                        in safe_head_columns
                    )
                ]

                try:
                    row_count_row = (
                        connection.execute(
                            (
                                "SELECT COUNT(*) "
                                "FROM "
                                + table_id
                            )
                        ).fetchone()
                    )

                    row_count = (
                        int(
                            row_count_row[
                                0
                            ]
                        )
                        if row_count_row
                        else 0
                    )

                except sqlite3.Error:
                    row_count = None

                summary: dict[
                    str,
                    Any,
                ] = {
                    "name":
                        table,
                    "row_count":
                        row_count,
                    "columns":
                        columns,
                    "safe_head_columns":
                        safe_columns,
                }

                grouped = {}

                for column in safe_columns:
                    lowered = (
                        column.casefold()
                    )

                    if lowered not in {
                        "status",
                        "state",
                        "authority",
                        "tier",
                        "accepted",
                        "active",
                    }:
                        continue

                    column_id = (
                        sql_identifier(
                            column
                        )
                    )

                    try:
                        rows = (
                            connection.execute(
                                (
                                    "SELECT "
                                    + column_id
                                    + ", COUNT(*) "
                                    + "FROM "
                                    + table_id
                                    + " GROUP BY "
                                    + column_id
                                    + " ORDER BY "
                                    + column_id
                                    + " LIMIT 50"
                                )
                            ).fetchall()
                        )

                        grouped[
                            column
                        ] = [
                            {
                                "value":
                                    row[
                                        0
                                    ],
                                "count":
                                    int(
                                        row[
                                            1
                                        ]
                                    ),
                            }
                            for row
                            in rows
                        ]

                    except sqlite3.Error:
                        continue

                if grouped:
                    summary[
                        "group_counts"
                    ] = grouped

                maxima = {}

                for column in safe_columns:
                    lowered = (
                        column.casefold()
                    )

                    if lowered not in {
                        "id",
                        "record_id",
                        "decision_id",
                        "revision_id",
                        "version",
                        "revision",
                        "sequence",
                        "generation",
                        "epoch",
                        "created_at",
                        "updated_at",
                        "modified_at",
                        "timestamp",
                        "created_ns",
                        "updated_ns",
                        "mtime_ns",
                    }:
                        continue

                    column_id = (
                        sql_identifier(
                            column
                        )
                    )

                    try:
                        row = (
                            connection.execute(
                                (
                                    "SELECT MAX("
                                    + column_id
                                    + ") FROM "
                                    + table_id
                                )
                            ).fetchone()
                        )

                        if (
                            row
                            and row[
                                0
                            ]
                            is not None
                        ):
                            value = row[
                                0
                            ]

                            if isinstance(
                                value,
                                (
                                    str,
                                    int,
                                    float,
                                    bool,
                                ),
                            ):
                                maxima[
                                    column
                                ] = value

                    except sqlite3.Error:
                        continue

                if maxima:
                    summary[
                        "semantic_heads"
                    ] = maxima

                database[
                    "tables"
                ].append(
                    summary
                )

        finally:
            connection.close()

        databases.append(
            database
        )

    return {
        "schema":
            "savant.sdump.sqlite-semantic-state.v1",
        "projection_only":
            True,
        "authority_effect":
            "none",
        "raw_rows_serialized":
            False,
        "databases":
            databases,
    }


def living_state_projection() -> dict[str, Any]:
    current = (
        living_state_root
        / "current.json"
    )

    health = (
        living_state_root
        / "health.json"
    )

    journal = (
        living_state_root
        / "journal.jsonl"
    )

    result: dict[
        str,
        Any,
    ] = {
        "schema":
            "savant.sdump.living-state-portable.v1",
        "projection_only":
            True,
        "authority_effect":
            "none",
        "current":
            None,
        "health":
            None,
        "journal_tail":
            [],
    }

    for key, path in (
        (
            "current",
            current,
        ),
        (
            "health",
            health,
        ),
    ):
        if not path.is_file():
            continue

        try:
            raw = path.read_bytes()

            payload = json.loads(
                raw.decode(
                    "utf-8"
                )
            )

            result[
                key
            ] = payload

            result[
                key
                + "_sha256"
            ] = hashlib.sha256(
                raw
            ).hexdigest()

        except (
            OSError,
            UnicodeDecodeError,
            json.JSONDecodeError,
        ):
            result[
                key
                + "_readable"
            ] = False

    if journal.is_file():
        try:
            with journal.open(
                "rb"
            ) as handle:
                handle.seek(
                    0,
                    os.SEEK_END,
                )

                position = handle.tell()

                block = (
                    64
                    * 1024
                )

                data = b""

                while (
                    position > 0
                    and data.count(
                        b"\n"
                    )
                    <= 100
                    and len(
                        data
                    )
                    < (
                        4
                        * 1024
                        * 1024
                    )
                ):
                    amount = min(
                        block,
                        position,
                    )

                    position -= (
                        amount
                    )

                    handle.seek(
                        position
                    )

                    data = (
                        handle.read(
                            amount
                        )
                        + data
                    )

                lines = (
                    data.decode(
                        "utf-8",
                        errors="replace",
                    ).splitlines()[
                        -100:
                    ]
                )

            events = []

            for line in lines:
                try:
                    value = json.loads(
                        line
                    )

                except json.JSONDecodeError:
                    continue

                if isinstance(
                    value,
                    dict,
                ):
                    events.append(
                        value
                    )

            result[
                "journal_tail"
            ] = events

            result[
                "journal_tail_count"
            ] = len(
                events
            )

        except OSError:
            result[
                "journal_readable"
            ] = False

    return result


def health_synthesis(
    projection: Projection,
    services: Mapping[
        str,
        Any,
    ],
    living: Mapping[
        str,
        Any,
    ],
) -> dict[str, Any]:
    service_records = list(
        services.get(
            "services",
            [],
        )
    )

    failed = [
        record.get(
            "name"
        )
        for record
        in service_records
        if (
            record.get(
                "active_state"
            )
            == "failed"
            or (
                record.get(
                    "result"
                )
                not in {
                    None,
                    "",
                    "success",
                    "done",
                }
                and record.get(
                    "active_state"
                )
                != "active"
            )
        )
    ]

    activating = [
        record.get(
            "name"
        )
        for record
        in service_records
        if record.get(
            "active_state"
        )
        == "activating"
    ]

    active = [
        record.get(
            "name"
        )
        for record
        in service_records
        if record.get(
            "active_state"
        )
        == "active"
    ]

    current = living.get(
        "current"
    )

    living_sequence = (
        current.get(
            "sequence"
        )
        if isinstance(
            current,
            dict,
        )
        else None
    )

    living_hash = (
        current.get(
            "snapshot_hash"
        )
        if isinstance(
            current,
            dict,
        )
        else None
    )

    return {
        "schema":
            "savant.sdump.health-synthesis.v1",
        "projection_only":
            True,
        "authority_effect":
            "none",
        "source_projection":
            (
                "complete"
                if not projection.failures
                else "failed"
            ),
        "source_failures":
            len(
                projection.failures
            ),
        "source_skips":
            len(
                projection.skipped
            ),
        "snapshot_hash":
            projection.snapshot_hash,
        "active_relevant_services":
            active,
        "failed_relevant_services":
            failed,
        "activating_relevant_services":
            activating,
        "living_state_available":
            isinstance(
                current,
                dict,
            ),
        "living_state_sequence":
            living_sequence,
        "living_state_snapshot_hash":
            living_hash,
        "healthy_evidence_summary":
            (
                not projection.failures
                and not failed
            ),
        "healthy_evidence_summary_is_authority":
            False,
    }


def delta_projection(
    living: Mapping[
        str,
        Any,
    ],
) -> dict[str, Any]:
    current = living.get(
        "current"
    )

    if not isinstance(
        current,
        dict,
    ):
        return {
            "available":
                False,
            "authority_effect":
                "none",
        }

    delta = current.get(
        "delta"
    )

    return {
        "available":
            isinstance(
                delta,
                dict,
            ),
        "sequence":
            current.get(
                "sequence"
            ),
        "snapshot_hash":
            current.get(
                "snapshot_hash"
            ),
        "previous_snapshot_hash":
            current.get(
                "previous_snapshot_hash"
            ),
        "delta":
            (
                delta
                if isinstance(
                    delta,
                    dict,
                )
                else None
            ),
        "authority_effect":
            "none",
    }


def build_palaver_context(
    manifest: Mapping[
        str,
        Any,
    ],
    projection: Projection,
) -> dict[str, Any]:
    targets = [
        Path(
            str(
                value
            )
        ).resolve(
            strict=False
        )
        for value
        in manifest.get(
            "targets",
            [],
        )
    ]

    started = time.monotonic()

    deployment = (
        deployment_configuration()
    )

    services = (
        service_diagnostics()
    )

    living = (
        living_state_projection()
    )

    large_objects = (
        full_large_file_hashes(
            projection,
            targets,
        )
    )

    sqlite_state = (
        sqlite_semantic_heads()
    )

    delta = delta_projection(
        living
    )

    health = health_synthesis(
        projection,
        services,
        living,
    )

    context: dict[
        str,
        Any,
    ] = {
        "schema":
            schema,
        "generated_at_unix_ns":
            time.time_ns(),
        "projection_only":
            True,
        "authority_effect":
            "none",
        "filesystem_presence_establishes_authority":
            False,
        "secret_values_serialized":
            False,
        "deployment_configuration":
            deployment,
        "service_diagnostics":
            services,
        "living_state":
            living,
        "large_objects":
            large_objects,
        "sqlite_semantic_state":
            sqlite_state,
        "delta":
            delta,
        "health":
            health,
        "palaver_ingestion_contract":
            {
                "treat_as_evidence":
                    True,
                "promote_to_authority":
                    False,
                "current_source_precedes_historical_evidence":
                    True,
                "accepted_authority_precedes_current_source":
                    True,
                "omitted_content_is_unknown":
                    True,
                "secret_values_are_absent":
                    True,
                "deployment_configuration_is_sanitized":
                    True,
                "service_journal_is_bounded":
                    True,
                "sqlite_rows_are_not_serialized":
                    True,
                "large_file_hashes_are_streaming_sha256":
                    True,
                "living_state_delta_is_portable":
                    True,
            },
    }

    hash_material = dict(
        context
    )

    context[
        "context_sha256"
    ] = stable_hash(
        hash_material
    )

    context[
        "build_duration_seconds"
    ] = round(
        (
            time.monotonic()
            - started
        ),
        6,
    )

    return context
