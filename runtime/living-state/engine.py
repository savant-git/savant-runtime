#!/usr/bin/env python3

from __future__ import annotations

from collections import Counter
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import socket
import sqlite3
import stat
import subprocess
import sys
import tempfile
import threading
import time
from typing import Any, Iterable


schema = "savant.living-state.v1"

runtime_root = Path(
    "/root/savant-runtime"
).resolve()

state_root = (
    runtime_root
    / "runtime"
    / "living-state"
).resolve()

current_path = (
    state_root
    / "current.json"
)

journal_path = (
    state_root
    / "journal.jsonl"
)

cache_path = (
    state_root
    / "cache.json"
)

health_path = (
    state_root
    / "health.json"
)

lock_path = (
    state_root
    / "engine.lock"
)

vendor_root = (
    runtime_root
    / "tools"
    / "sdump-enterprise"
    / "vendor"
)

if vendor_root.is_dir():
    sys.path.insert(
        0,
        str(vendor_root),
    )


stop_event = threading.Event()


source_suffixes = frozenset(
    {
        ".py",
        ".pyi",
        ".js",
        ".jsx",
        ".ts",
        ".tsx",
        ".mjs",
        ".cjs",
        ".json",
        ".jsonl",
        ".yaml",
        ".yml",
        ".toml",
        ".ini",
        ".cfg",
        ".conf",
        ".md",
        ".txt",
        ".html",
        ".css",
        ".scss",
        ".sql",
        ".sh",
        ".bash",
        ".service",
        ".socket",
        ".timer",
        ".target",
        ".path",
        ".env.example",
        ".xml",
        ".csv",
        ".graphql",
        ".proto",
        ".lock",
    }
)


package_manifest_names = frozenset(
    {
        "package.json",
        "package-lock.json",
        "pnpm-lock.yaml",
        "yarn.lock",
        "pyproject.toml",
        "poetry.lock",
        "requirements.txt",
        "requirements-dev.txt",
        "pipfile",
        "pipfile.lock",
        "cargo.toml",
        "cargo.lock",
        "go.mod",
        "go.sum",
        "composer.json",
        "composer.lock",
        "gemfile",
        "gemfile.lock",
    }
)


ignored_directory_names = frozenset(
    {
        "__pycache__",
        ".git",
        ".pytest_cache",
        ".mypy_cache",
        ".ruff_cache",
        ".cache",
        "node_modules",
    }
)


self_generated_names = frozenset(
    {
        current_path.name,
        journal_path.name,
        cache_path.name,
        health_path.name,
        lock_path.name,
    }
)


known_services = (
    "palaver.service",
    "palaver-attachment.service",
    "palaver-frontend.service",
    "palaver-tunnel.service",
    "savant-living-state.service",
)


sqlite_suffixes = frozenset(
    {
        ".sqlite",
        ".sqlite3",
        ".db",
    }
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


def pretty_json(
    value: Any,
) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        indent=2,
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
) -> str:
    digest = hashlib.sha256()

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

    return digest.hexdigest()


def optional_blake3_file(
    path: Path,
) -> str | None:
    try:
        import blake3

    except ImportError:
        return None

    digest = blake3.blake3()

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

    return digest.hexdigest()


def atomic_write_json(
    path: Path,
    value: Any,
) -> None:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.",
        suffix=".partial",
        dir=str(path.parent),
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
                pretty_json(
                    value
                )
            )

            handle.write(
                "\n"
            )

            handle.flush()
            os.fsync(
                handle.fileno()
            )

        os.chmod(
            temporary,
            0o600,
        )

        os.replace(
            temporary,
            path,
        )

    finally:
        if temporary.exists():
            temporary.unlink()


def append_journal(
    record: dict[str, Any],
) -> None:
    state_root.mkdir(
        parents=True,
        exist_ok=True,
    )

    with journal_path.open(
        "a",
        encoding="utf-8",
        newline="",
    ) as handle:
        handle.write(
            compact_json(
                record
            )
        )

        handle.write(
            "\n"
        )

        handle.flush()
        os.fsync(
            handle.fileno()
        )


def run(
    command: list[str],
    timeout: float = 5.0,
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
            "ok": (
                result.returncode == 0
            ),
            "returncode":
                result.returncode,
            "stdout":
                result.stdout.strip(),
            "stderr":
                result.stderr.strip(),
        }

    except Exception as error:
        return {
            "ok": False,
            "error":
                type(error).__name__,
            "message":
                str(error),
        }


def env_names_from_file(
    path: Path,
) -> list[str]:
    if not path.is_file():
        return []

    names: set[str] = set()

    try:
        for raw in path.read_text(
            encoding="utf-8",
            errors="replace",
        ).splitlines():
            line = raw.strip()

            if (
                not line
                or line.startswith("#")
                or "=" not in line
            ):
                continue

            key = line.split(
                "=",
                1,
            )[0].strip()

            if key.startswith(
                "export "
            ):
                key = key[
                    7:
                ].strip()

            if (
                key
                and key.replace(
                    "_",
                    ""
                ).isalnum()
            ):
                names.add(
                    key
                )

    except OSError:
        return []

    return sorted(
        names
    )


def environment_state() -> dict[str, Any]:
    files = [
        Path("/root/.env"),
        runtime_root / ".env",
    ]

    records = []

    all_names: set[str] = set()

    for path in files:
        names = env_names_from_file(
            path
        )

        if names:
            all_names.update(
                names
            )

        records.append(
            {
                "path": str(path),
                "exists": path.is_file(),
                "variable_names": names,
                "values_included": False,
            }
        )

    required = (
        "AWS_S3_BUCKET",
        "AWS_ACCESS_KEY_ID",
        "AWS_SECRET_ACCESS_KEY",
    )

    return {
        "values_included": False,
        "sources": records,
        "known_names": sorted(
            all_names
        ),
        "required_presence": {
            name: (
                name in all_names
                or bool(
                    os.environ.get(
                        name
                    )
                )
            )
            for name
            in required
        },
    }


def classify_path(
    relative: str,
) -> str:
    normalized = (
        "/"
        + relative.casefold().strip("/")
        + "/"
    )

    if (
        "/runtime/living-state/"
        in normalized
    ):
        return "live_state_projection"

    if (
        "/backups/"
        in normalized
        or "/backup/"
        in normalized
    ):
        return "backup_evidence"

    if (
        "/evolution/"
        in normalized
        or "migration"
        in normalized
    ):
        return "migration_evidence"

    if (
        "/imports/"
        in normalized
        or "/relics/"
        in normalized
    ):
        return "imported_or_historical_evidence"

    if (
        "/vault/"
        in normalized
    ):
        return "vault_evidence"

    if (
        "/authority/"
        in normalized
        or "/canon/"
        in normalized
        or "/canon-system/"
        in normalized
    ):
        return "authority_candidate"

    if (
        "/runtime/"
        in normalized
    ):
        return "runtime_projection_or_state"

    return "implementation_evidence"


def executable_shebang(
    path: Path,
    mode: int,
) -> str | None:
    if not stat.S_ISREG(
        mode
    ):
        return None

    if not (
        mode & 0o111
    ):
        return None

    try:
        with path.open(
            "rb"
        ) as handle:
            first = handle.readline(
                512
            )

    except OSError:
        return None

    if not first.startswith(
        b"#!"
    ):
        return None

    return first.decode(
        "utf-8",
        errors="replace",
    ).strip()


def source_candidate(
    path: Path,
    mode: int,
) -> bool:
    name = path.name.casefold()
    suffix = path.suffix.casefold()

    if name in package_manifest_names:
        return True

    if suffix in source_suffixes:
        return True

    if executable_shebang(
        path,
        mode,
    ):
        return True

    return False


def filesystem_inventory(
    previous_cache: dict[str, Any],
) -> tuple[
    dict[str, Any],
    dict[str, Any],
]:
    files: dict[
        str,
        dict[str, Any],
    ] = {}

    symlinks = []
    failures = []

    extension_counts: Counter[
        str
    ] = Counter()

    class_counts: Counter[
        str
    ] = Counter()

    source_count = 0
    total_bytes = 0

    previous_files = previous_cache.get(
        "files",
        {}
    )

    for root, directories, filenames in os.walk(
        runtime_root,
        followlinks=False,
    ):
        root_path = Path(
            root
        )

        directories[:] = [
            name
            for name
            in sorted(
                directories,
                key=str.casefold,
            )
            if (
                name.casefold()
                not in ignored_directory_names
            )
        ]

        for name in sorted(
            filenames,
            key=str.casefold,
        ):
            path = (
                root_path
                / name
            )

            try:
                relative = str(
                    path.relative_to(
                        runtime_root
                    )
                )

            except ValueError:
                continue

            if (
                path.parent == state_root
                and name in self_generated_names
            ):
                continue

            try:
                info = path.lstat()

            except OSError as error:
                failures.append(
                    {
                        "path": relative,
                        "error":
                            type(error).__name__,
                    }
                )
                continue

            if stat.S_ISLNK(
                info.st_mode
            ):
                try:
                    target = os.readlink(
                        path
                    )

                except OSError:
                    target = None

                symlinks.append(
                    {
                        "path": relative,
                        "target": target,
                    }
                )

                continue

            if not stat.S_ISREG(
                info.st_mode
            ):
                continue

            total_bytes += (
                info.st_size
            )

            suffix = (
                path.suffix.casefold()
                or "[none]"
            )

            extension_counts[
                suffix
            ] += 1

            evidence_class = (
                classify_path(
                    relative
                )
            )

            class_counts[
                evidence_class
            ] += 1

            shebang = (
                executable_shebang(
                    path,
                    info.st_mode,
                )
            )

            is_source = (
                source_candidate(
                    path,
                    info.st_mode,
                )
            )

            if is_source:
                source_count += 1

            signature = (
                f"{info.st_size}:"
                f"{info.st_mtime_ns}:"
                f"{info.st_mode}"
            )

            previous = previous_files.get(
                relative
            )

            sha256 = None

            if (
                isinstance(
                    previous,
                    dict,
                )
                and previous.get(
                    "signature"
                )
                == signature
            ):
                sha256 = previous.get(
                    "sha256"
                )

            if (
                sha256 is None
                and is_source
                and info.st_size
                <= 32 * 1024 * 1024
            ):
                try:
                    sha256 = (
                        sha256_file(
                            path
                        )
                    )

                except OSError:
                    sha256 = None

            files[
                relative
            ] = {
                "signature":
                    signature,
                "size":
                    info.st_size,
                "mtime_ns":
                    info.st_mtime_ns,
                "mode":
                    oct(
                        stat.S_IMODE(
                            info.st_mode
                        )
                    ),
                "source_candidate":
                    is_source,
                "sha256":
                    sha256,
                "shebang":
                    shebang,
                "evidence_class":
                    evidence_class,
                "authority_effect":
                    "none",
            }

    cache = {
        "schema":
            "savant.living-state.cache.v1",
        "files":
            files,
    }

    summary = {
        "files":
            len(files),
        "source_candidates":
            source_count,
        "bytes":
            total_bytes,
        "symlink_count":
            len(symlinks),
        "symlinks":
            symlinks,
        "failures":
            failures,
        "extensions":
            dict(
                sorted(
                    extension_counts.items()
                )
            ),
        "evidence_classes":
            dict(
                sorted(
                    class_counts.items()
                )
            ),
    }

    return (
        cache,
        summary,
    )


def file_delta(
    old_cache: dict[str, Any],
    new_cache: dict[str, Any],
) -> dict[str, Any]:
    old_files = old_cache.get(
        "files",
        {}
    )

    new_files = new_cache.get(
        "files",
        {}
    )

    old_paths = set(
        old_files
    )

    new_paths = set(
        new_files
    )

    added = sorted(
        new_paths
        - old_paths,
        key=str.casefold,
    )

    deleted = sorted(
        old_paths
        - new_paths,
        key=str.casefold,
    )

    changed = sorted(
        (
            path
            for path
            in old_paths
            & new_paths
            if (
                old_files[
                    path
                ].get(
                    "signature"
                )
                != new_files[
                    path
                ].get(
                    "signature"
                )
                or old_files[
                    path
                ].get(
                    "sha256"
                )
                != new_files[
                    path
                ].get(
                    "sha256"
                )
            )
        ),
        key=str.casefold,
    )

    return {
        "added":
            added,
        "changed":
            changed,
        "deleted":
            deleted,
        "added_count":
            len(added),
        "changed_count":
            len(changed),
        "deleted_count":
            len(deleted),
    }


def read_json(
    path: Path,
) -> dict[str, Any]:
    try:
        value = json.loads(
            path.read_text(
                encoding="utf-8"
            )
        )

        if isinstance(
            value,
            dict,
        ):
            return value

    except (
        OSError,
        json.JSONDecodeError,
    ):
        pass

    return {}


def service_state(
    name: str,
) -> dict[str, Any]:
    result = run(
        [
            "systemctl",
            "show",
            name,
            "--no-pager",
            "--property=LoadState",
            "--property=ActiveState",
            "--property=SubState",
            "--property=FragmentPath",
            "--property=WorkingDirectory",
            "--property=ExecStart",
            "--property=MainPID",
            "--property=ActiveEnterTimestamp",
        ]
    )

    fields: dict[
        str,
        str,
    ] = {}

    for line in str(
        result.get(
            "stdout",
            ""
        )
    ).splitlines():
        key, separator, value = line.partition(
            "="
        )

        if separator:
            fields[
                key
            ] = value

    return {
        "name":
            name,
        "query_ok":
            result.get(
                "ok",
                False,
            ),
        "load_state":
            fields.get(
                "LoadState"
            ),
        "active_state":
            fields.get(
                "ActiveState"
            ),
        "sub_state":
            fields.get(
                "SubState"
            ),
        "fragment_path":
            fields.get(
                "FragmentPath"
            ),
        "working_directory":
            fields.get(
                "WorkingDirectory"
            ),
        "exec_start":
            fields.get(
                "ExecStart"
            ),
        "main_pid":
            fields.get(
                "MainPID"
            ),
        "active_since":
            fields.get(
                "ActiveEnterTimestamp"
            ),
    }


def services_state() -> list[
    dict[str, Any]
]:
    return [
        service_state(
            name
        )
        for name
        in known_services
    ]


def listening_ports() -> list[
    dict[str, Any]
]:
    result = run(
        [
            "ss",
            "-H",
            "-ltnp",
        ]
    )

    if not result.get(
        "ok"
    ):
        return []

    records = []

    for line in str(
        result.get(
            "stdout",
            ""
        )
    ).splitlines():
        columns = line.split(
            None,
            5,
        )

        if len(
            columns
        ) < 4:
            continue

        records.append(
            {
                "state":
                    columns[0],
                "recv_q":
                    columns[1],
                "send_q":
                    columns[2],
                "local":
                    columns[3],
                "peer":
                    (
                        columns[4]
                        if len(
                            columns
                        ) > 4
                        else None
                    ),
                "process":
                    (
                        columns[5]
                        if len(
                            columns
                        ) > 5
                        else None
                    ),
            }
        )

    return records


def process_state() -> list[
    dict[str, Any]
]:
    records = []

    proc = Path(
        "/proc"
    )

    for candidate in proc.iterdir():
        if not candidate.name.isdigit():
            continue

        pid = candidate.name

        try:
            cwd = os.readlink(
                candidate / "cwd"
            )

        except OSError:
            cwd = ""

        try:
            command = (
                candidate
                / "cmdline"
            ).read_bytes().replace(
                b"\x00",
                b" ",
            ).decode(
                "utf-8",
                errors="replace",
            ).strip()

        except OSError:
            command = ""

        relevant = (
            str(runtime_root)
            in cwd
            or str(runtime_root)
            in command
            or "palaver"
            in command.casefold()
            or "savant"
            in command.casefold()
        )

        if not relevant:
            continue

        records.append(
            {
                "pid":
                    int(pid),
                "cwd":
                    cwd or None,
                "command":
                    command[:4096],
            }
        )

    return sorted(
        records,
        key=lambda item:
            item["pid"],
    )


def nginx_state() -> dict[str, Any]:
    roots = (
        Path(
            "/etc/nginx/sites-enabled"
        ),
        Path(
            "/etc/nginx/conf.d"
        ),
    )

    files = []

    for root in roots:
        if not root.is_dir():
            continue

        for path in sorted(
            root.iterdir(),
            key=lambda item:
                item.name.casefold(),
        ):
            if not (
                path.is_file()
                or path.is_symlink()
            ):
                continue

            record: dict[
                str,
                Any,
            ] = {
                "path":
                    str(path),
                "is_symlink":
                    path.is_symlink(),
            }

            try:
                resolved = path.resolve(
                    strict=True
                )

                record[
                    "resolved"
                ] = str(
                    resolved
                )

                record[
                    "sha256"
                ] = sha256_file(
                    resolved
                )

            except OSError:
                record[
                    "resolved"
                ] = None

                record[
                    "sha256"
                ] = None

            files.append(
                record
            )

    test = run(
        [
            "nginx",
            "-t",
        ]
    )

    return {
        "configuration_test_ok":
            test.get(
                "ok",
                False,
            ),
        "files":
            files,
    }


def cloudflared_state() -> dict[str, Any]:
    binary = shutil.which(
        "cloudflared"
    )

    service_candidates = (
        "cloudflared.service",
        "palaver-tunnel.service",
    )

    return {
        "binary":
            binary,
        "services": [
            service_state(
                name
            )
            for name
            in service_candidates
        ],
    }


def system_resources() -> dict[str, Any]:
    result: dict[
        str,
        Any,
    ] = {}

    try:
        load1, load5, load15 = os.getloadavg()

        result[
            "load_average"
        ] = {
            "1m": load1,
            "5m": load5,
            "15m": load15,
        }

    except OSError:
        pass

    try:
        usage = shutil.disk_usage(
            runtime_root
        )

        result[
            "disk"
        ] = {
            "total":
                usage.total,
            "used":
                usage.used,
            "free":
                usage.free,
        }

    except OSError:
        pass

    try:
        uptime = Path(
            "/proc/uptime"
        ).read_text(
            encoding="utf-8"
        ).split()[0]

        result[
            "uptime_seconds"
        ] = float(
            uptime
        )

    except (
        OSError,
        ValueError,
        IndexError,
    ):
        pass

    try:
        memory: dict[
            str,
            int,
        ] = {}

        for line in Path(
            "/proc/meminfo"
        ).read_text(
            encoding="utf-8"
        ).splitlines():
            key, separator, value = line.partition(
                ":"
            )

            if not separator:
                continue

            token = value.strip().split()[0]

            if token.isdigit():
                memory[
                    key
                ] = int(
                    token
                ) * 1024

        result[
            "memory"
        ] = memory

    except OSError:
        pass

    return result


def git_state() -> dict[str, Any] | None:
    root_result = run(
        [
            "git",
            "-C",
            str(runtime_root),
            "rev-parse",
            "--show-toplevel",
        ]
    )

    if not root_result.get(
        "ok"
    ):
        return None

    branch = run(
        [
            "git",
            "-C",
            str(runtime_root),
            "branch",
            "--show-current",
        ]
    )

    commit = run(
        [
            "git",
            "-C",
            str(runtime_root),
            "rev-parse",
            "HEAD",
        ]
    )

    status = run(
        [
            "git",
            "-C",
            str(runtime_root),
            "status",
            "--porcelain=v1",
        ]
    )

    return {
        "root":
            root_result.get(
                "stdout"
            ),
        "branch":
            branch.get(
                "stdout"
            ),
        "commit":
            commit.get(
                "stdout"
            ),
        "dirty":
            bool(
                status.get(
                    "stdout"
                )
            ),
        "status_entries":
            len(
                str(
                    status.get(
                        "stdout",
                        ""
                    )
                ).splitlines()
            ),
    }


def package_state(
    cache: dict[str, Any],
) -> list[
    dict[str, Any]
]:
    records = []

    for relative, item in cache.get(
        "files",
        {}
    ).items():
        name = Path(
            relative
        ).name.casefold()

        if name not in package_manifest_names:
            continue

        records.append(
            {
                "path":
                    relative,
                "size":
                    item.get(
                        "size"
                    ),
                "sha256":
                    item.get(
                        "sha256"
                    ),
            }
        )

    return sorted(
        records,
        key=lambda item:
            item["path"].casefold(),
    )


def sqlite_state() -> list[
    dict[str, Any]
]:
    records = []

    for path in runtime_root.rglob(
        "*"
    ):
        if (
            not path.is_file()
            or path.suffix.casefold()
            not in sqlite_suffixes
        ):
            continue

        try:
            relative = str(
                path.relative_to(
                    runtime_root
                )
            )

        except ValueError:
            continue

        record: dict[
            str,
            Any,
        ] = {
            "path":
                relative,
            "size":
                path.stat().st_size,
            "authority_effect":
                "none",
            "contents_included":
                False,
        }

        try:
            uri = (
                "file:"
                + str(path)
                + "?mode=ro"
            )

            connection = sqlite3.connect(
                uri,
                uri=True,
                timeout=1.0,
            )

            try:
                tables = [
                    row[0]
                    for row
                    in connection.execute(
                        """
                        SELECT name
                        FROM sqlite_master
                        WHERE type = 'table'
                          AND name NOT LIKE 'sqlite_%'
                        ORDER BY name
                        """
                    )
                ]

                counts: dict[
                    str,
                    int | None,
                ] = {}

                for table in tables[
                    :100
                ]:
                    escaped = table.replace(
                        '"',
                        '""',
                    )

                    try:
                        count = connection.execute(
                            f'SELECT COUNT(*) FROM "{escaped}"'
                        ).fetchone()

                        counts[
                            table
                        ] = (
                            int(
                                count[0]
                            )
                            if count
                            else 0
                        )

                    except sqlite3.Error:
                        counts[
                            table
                        ] = None

                record[
                    "tables"
                ] = tables

                record[
                    "row_counts"
                ] = counts

                version = connection.execute(
                    "PRAGMA user_version"
                ).fetchone()

                record[
                    "user_version"
                ] = (
                    int(
                        version[0]
                    )
                    if version
                    else None
                )

            finally:
                connection.close()

        except sqlite3.Error as error:
            record[
                "inspection_error"
            ] = str(
                error
            )

        records.append(
            record
        )

    return sorted(
        records,
        key=lambda item:
            item["path"].casefold(),
    )


def latest_sdump_state() -> dict[str, Any] | None:
    source_root = (
        runtime_root
        / "source"
    )

    if not source_root.is_dir():
        return None

    candidates = [
        path
        for path
        in source_root.rglob(
            "sdump_*.txt"
        )
        if path.is_file()
    ]

    if not candidates:
        return None

    latest = max(
        candidates,
        key=lambda path:
            path.stat().st_mtime_ns,
    )

    return {
        "path":
            str(latest),
        "size":
            latest.stat().st_size,
        "mtime_ns":
            latest.stat().st_mtime_ns,
        "sha256":
            sha256_file(
                latest
            ),
    }


def previous_snapshot_state() -> dict[str, Any]:
    return read_json(
        current_path
    )


def next_sequence(
    previous: dict[str, Any],
) -> int:
    try:
        return int(
            previous.get(
                "sequence",
                0,
            )
        ) + 1

    except (
        TypeError,
        ValueError,
    ):
        return 1


def build_snapshot() -> tuple[
    dict[str, Any],
    dict[str, Any],
]:
    previous = (
        previous_snapshot_state()
    )

    old_cache = read_json(
        cache_path
    )

    new_cache, filesystem = (
        filesystem_inventory(
            old_cache
        )
    )

    delta = file_delta(
        old_cache,
        new_cache,
    )

    sequence = next_sequence(
        previous
    )

    previous_snapshot_hash = (
        previous.get(
            "snapshot_hash"
        )
        if previous
        else None
    )

    generated_at_ns = (
        time.time_ns()
    )

    snapshot = {
        "schema":
            schema,
        "projection_only":
            True,
        "authority_effect":
            "none",
        "filesystem_presence_establishes_authority":
            False,
        "sequence":
            sequence,
        "generated_at_unix_ns":
            generated_at_ns,
        "previous_snapshot_hash":
            previous_snapshot_hash,
        "runtime_root":
            str(
                runtime_root
            ),
        "filesystem":
            filesystem,
        "delta":
            delta,
        "environment":
            environment_state(),
        "services":
            services_state(),
        "processes":
            process_state(),
        "listening_tcp":
            listening_ports(),
        "nginx":
            nginx_state(),
        "cloudflared":
            cloudflared_state(),
        "system":
            system_resources(),
        "git":
            git_state(),
        "packages":
            package_state(
                new_cache
            ),
        "sqlite":
            sqlite_state(),
        "latest_sdump":
            latest_sdump_state(),
        "capabilities": {
            "event_driven_watch":
                watchfiles_available(),
            "orjson":
                module_available(
                    "orjson"
                ),
            "blake3":
                module_available(
                    "blake3"
                ),
            "psutil":
                module_available(
                    "psutil"
                ),
            "secret_values_serialized":
                False,
            "sqlite_open_mode":
                "read_only",
            "hash_chain":
                True,
            "atomic_snapshots":
                True,
        },
    }

    hash_material = dict(
        snapshot
    )

    snapshot_hash = stable_hash(
        hash_material
    )

    snapshot[
        "snapshot_hash"
    ] = snapshot_hash

    journal_record = {
        "schema":
            "savant.living-state.event.v1",
        "sequence":
            sequence,
        "generated_at_unix_ns":
            generated_at_ns,
        "snapshot_hash":
            snapshot_hash,
        "previous_snapshot_hash":
            previous_snapshot_hash,
        "delta":
            delta,
    }

    journal_record[
        "event_hash"
    ] = stable_hash(
        journal_record
    )

    return (
        snapshot,
        {
            "cache":
                new_cache,
            "journal":
                journal_record,
        },
    )


def persist_snapshot() -> dict[str, Any]:
    started = time.monotonic()

    try:
        snapshot, support = (
            build_snapshot()
        )

        atomic_write_json(
            cache_path,
            support[
                "cache"
            ],
        )

        atomic_write_json(
            current_path,
            snapshot,
        )

        append_journal(
            support[
                "journal"
            ]
        )

        health = {
            "schema":
                "savant.living-state.health.v1",
            "healthy":
                True,
            "sequence":
                snapshot[
                    "sequence"
                ],
            "snapshot_hash":
                snapshot[
                    "snapshot_hash"
                ],
            "duration_seconds":
                (
                    time.monotonic()
                    - started
                ),
            "updated_at_unix_ns":
                time.time_ns(),
        }

        atomic_write_json(
            health_path,
            health,
        )

        sd_notify(
            "WATCHDOG=1"
        )

        return snapshot

    except Exception as error:
        atomic_write_json(
            health_path,
            {
                "schema":
                    "savant.living-state.health.v1",
                "healthy":
                    False,
                "error":
                    type(error).__name__,
                "message":
                    str(error),
                "updated_at_unix_ns":
                    time.time_ns(),
            },
        )

        raise


def module_available(
    name: str,
) -> bool:
    try:
        __import__(
            name
        )

        return True

    except ImportError:
        return False


def watchfiles_available() -> bool:
    return module_available(
        "watchfiles"
    )


def sd_notify(
    message: str,
) -> None:
    address = os.environ.get(
        "NOTIFY_SOCKET"
    )

    if not address:
        return

    if address.startswith(
        "@"
    ):
        address = (
            "\0"
            + address[1:]
        )

    try:
        notifier = socket.socket(
            socket.AF_UNIX,
            socket.SOCK_DGRAM,
        )

        try:
            notifier.connect(
                address
            )

            notifier.sendall(
                message.encode(
                    "utf-8"
                )
            )

        finally:
            notifier.close()

    except OSError:
        return


def acquire_lock() -> int:
    state_root.mkdir(
        parents=True,
        exist_ok=True,
    )

    descriptor = os.open(
        lock_path,
        os.O_CREAT
        | os.O_RDWR,
        0o600,
    )

    try:
        import fcntl

        fcntl.flock(
            descriptor,
            fcntl.LOCK_EX
            | fcntl.LOCK_NB,
        )

    except BlockingIOError as error:
        os.close(
            descriptor
        )

        raise RuntimeError(
            "living state engine is already running"
        ) from error

    os.ftruncate(
        descriptor,
        0,
    )

    os.write(
        descriptor,
        str(
            os.getpid()
        ).encode(
            "ascii"
        ),
    )

    return descriptor


def signal_handler(
    signum: int,
    frame: Any,
) -> None:
    del signum
    del frame

    stop_event.set()


def event_loop(
    interval: float,
    reconcile_interval: float,
) -> None:
    persist_snapshot()

    sd_notify(
        "READY=1"
    )

    if watchfiles_available():
        from watchfiles import watch

        last_full = time.monotonic()

        for changes in watch(
            runtime_root,
            stop_event=stop_event,
            debounce=1000,
            step=500,
            recursive=True,
            yield_on_timeout=True,
            rust_timeout=int(
                max(
                    1000,
                    interval
                    * 1000,
                )
            ),
        ):
            if stop_event.is_set():
                break

            meaningful = False

            for _, raw_path in changes:
                path = Path(
                    raw_path
                )

                try:
                    if (
                        path.parent.resolve(
                            strict=False
                        )
                        == state_root
                    ):
                        continue

                except OSError:
                    pass

                meaningful = True
                break

            now = time.monotonic()

            if (
                meaningful
                or (
                    now
                    - last_full
                    >= reconcile_interval
                )
            ):
                persist_snapshot()

                last_full = now

            else:
                sd_notify(
                    "WATCHDOG=1"
                )

        return

    while not stop_event.wait(
        interval
    ):
        persist_snapshot()


def one_shot() -> int:
    snapshot = persist_snapshot()

    print(
        compact_json(
            {
                "sequence":
                    snapshot[
                        "sequence"
                    ],
                "snapshot_hash":
                    snapshot[
                        "snapshot_hash"
                    ],
                "current":
                    str(
                        current_path
                    ),
            }
        )
    )

    return 0


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser(
        prog="savant-living-state",
    )

    value.add_argument(
        "--once",
        action="store_true",
    )

    value.add_argument(
        "--interval",
        type=float,
        default=15.0,
    )

    value.add_argument(
        "--reconcile-interval",
        type=float,
        default=300.0,
    )

    return value


def main() -> int:
    arguments = parser().parse_args()

    state_root.mkdir(
        parents=True,
        exist_ok=True,
    )

    lock_descriptor = acquire_lock()

    signal.signal(
        signal.SIGTERM,
        signal_handler,
    )

    signal.signal(
        signal.SIGINT,
        signal_handler,
    )

    try:
        if arguments.once:
            return one_shot()

        event_loop(
            interval=max(
                2.0,
                arguments.interval,
            ),
            reconcile_interval=max(
                30.0,
                arguments.reconcile_interval,
            ),
        )

        sd_notify(
            "STOPPING=1"
        )

        return 0

    finally:
        os.close(
            lock_descriptor
        )


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
