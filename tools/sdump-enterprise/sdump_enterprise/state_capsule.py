from __future__ import annotations

from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import socket
import sqlite3
import stat
import subprocess
import time
from typing import Any, Iterable, Mapping

from .model import Projection


schema = "savant.sdump.state-capsule.v5"

secret_name_patterns = (
    re.compile(
        r"^\.env(?:\..*)?$",
        re.IGNORECASE,
    ),
    re.compile(
        r"secret",
        re.IGNORECASE,
    ),
    re.compile(
        r"credential",
        re.IGNORECASE,
    ),
    re.compile(
        r"(?:^|[-_.])key(?:$|[-_.])",
        re.IGNORECASE,
    ),
    re.compile(
        r"^id_(?:rsa|ed25519)$",
        re.IGNORECASE,
    ),
)

package_names = frozenset(
    {
        "package.json",
        "package-lock.json",
        "pnpm-lock.yaml",
        "yarn.lock",
        "bun.lock",
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

sqlite_suffixes = frozenset(
    {
        ".db",
        ".sqlite",
        ".sqlite3",
    }
)

ignored_walk_names = frozenset(
    {
        ".git",
        "__pycache__",
        "node_modules",
        ".pytest_cache",
        ".mypy_cache",
        ".ruff_cache",
        ".staging",
        "source",
        "exports",
        "audit",
        "_reports",
        "repair_backups",
        "relics",
    }
)


def _json(
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
        _json(
            value
        ).encode(
            "utf-8"
        )
    ).hexdigest()


def sha256_file(
    path: Path,
    max_bytes: int | None = None,
) -> str | None:
    try:
        if (
            max_bytes is not None
            and path.stat().st_size
            > max_bytes
        ):
            return None

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

    except OSError:
        return None


def sample_sha256(
    path: Path,
    sample_bytes: int = 65536,
) -> str | None:
    try:
        size = path.stat().st_size

        digest = hashlib.sha256()

        with path.open(
            "rb"
        ) as handle:
            digest.update(
                handle.read(
                    sample_bytes
                )
            )

            if size > sample_bytes:
                handle.seek(
                    max(
                        0,
                        size
                        - sample_bytes,
                    )
                )

                digest.update(
                    handle.read(
                        sample_bytes
                    )
                )

        digest.update(
            str(
                size
            ).encode(
                "ascii"
            )
        )

        return digest.hexdigest()

    except OSError:
        return None


def _run(
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
            "ok":
                result.returncode == 0,
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
                type(
                    error
                ).__name__,
            "message":
                str(
                    error
                ),
        }


def _is_secret_path(
    path: Path,
) -> bool:
    return any(
        pattern.search(
            path.name
        )
        for pattern
        in secret_name_patterns
    )


def _parse_env_names(
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
                or line.startswith(
                    "#"
                )
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

            if re.fullmatch(
                r"[A-Za-z_][A-Za-z0-9_]*",
                key,
            ):
                names.add(
                    key
                )

    except OSError:
        return []

    return sorted(
        names
    )


def environment_state(
    runtime: Path,
) -> dict[str, Any]:
    sources = [
        Path(
            "/root/.env"
        ),
        runtime / ".env",
    ]

    records = []
    all_names: set[str] = set()

    for path in sources:
        names = _parse_env_names(
            path
        )

        all_names.update(
            names
        )

        records.append(
            {
                "path":
                    str(
                        path
                    ),
                "exists":
                    path.is_file(),
                "variable_names":
                    names,
                "values_serialized":
                    False,
            }
        )

    required = (
        "AWS_S3_BUCKET",
        "AWS_ACCESS_KEY_ID",
        "AWS_SECRET_ACCESS_KEY",
    )

    return {
        "sources":
            records,
        "known_variable_names":
            sorted(
                all_names
            ),
        "required_presence":
            {
                name:
                    (
                        name
                        in all_names
                        or bool(
                            os.environ.get(
                                name
                            )
                        )
                    )
                for name
                in required
            },
        "values_serialized":
            False,
    }


def _unit_names() -> list[str]:
    discovered: set[str] = {
        "nginx.service",
        "cloudflared.service",
        "palaver.service",
        "palaver-attachment.service",
        "palaver-frontend.service",
        "palaver-tunnel.service",
        "savant-living-state.service",
    }

    result = _run(
        [
            "systemctl",
            "list-unit-files",
            "--type=service",
            "--no-legend",
            "--no-pager",
        ],
        timeout=8.0,
    )

    if result.get(
        "ok"
    ):
        for line in str(
            result.get(
                "stdout",
                "",
            )
        ).splitlines():
            fields = line.split()

            if not fields:
                continue

            name = fields[
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
                    "cloudflared",
                    "nginx",
                )
            ):
                discovered.add(
                    name
                )

    return sorted(
        discovered,
        key=str.casefold,
    )


def _service_state(
    name: str,
) -> dict[str, Any]:
    result = _run(
        [
            "systemctl",
            "show",
            name,
            "--no-pager",
            "--property=LoadState",
            "--property=UnitFileState",
            "--property=ActiveState",
            "--property=SubState",
            "--property=FragmentPath",
            "--property=WorkingDirectory",
            "--property=MainPID",
            "--property=ActiveEnterTimestampMonotonic",
        ]
    )

    fields: dict[
        str,
        str,
    ] = {}

    for line in str(
        result.get(
            "stdout",
            "",
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

    fragment = Path(
        fields.get(
            "FragmentPath"
        )
        or ""
    )

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
        "unit_file_state":
            fields.get(
                "UnitFileState"
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
            (
                fields.get(
                    "FragmentPath"
                )
                or None
            ),
        "fragment_sha256":
            (
                sha256_file(
                    fragment,
                    max_bytes=(
                        8
                        * 1024
                        * 1024
                    ),
                )
                if fragment.is_file()
                else None
            ),
        "working_directory":
            (
                fields.get(
                    "WorkingDirectory"
                )
                or None
            ),
        "main_pid":
            (
                fields.get(
                    "MainPID"
                )
                or None
            ),
        "active_enter_monotonic":
            (
                fields.get(
                    "ActiveEnterTimestampMonotonic"
                )
                or None
            ),
        "environment_values_serialized":
            False,
        "exec_arguments_serialized":
            False,
    }


def service_state() -> dict[str, Any]:
    services = [
        _service_state(
            name
        )
        for name
        in _unit_names()
    ]

    return {
        "services":
            services,
        "active_count":
            sum(
                item.get(
                    "active_state"
                )
                == "active"
                for item
                in services
            ),
        "environment_values_serialized":
            False,
    }


def nginx_state() -> dict[str, Any]:
    paths: set[Path] = {
        Path(
            "/etc/nginx/nginx.conf"
        )
    }

    for root in (
        Path(
            "/etc/nginx/sites-enabled"
        ),
        Path(
            "/etc/nginx/conf.d"
        ),
    ):
        if root.is_dir():
            paths.update(
                path
                for path
                in root.iterdir()
                if (
                    path.is_file()
                    or path.is_symlink()
                )
            )

    records = []

    for path in sorted(
        paths,
        key=lambda item:
            str(
                item
            ).casefold(),
    ):
        try:
            resolved = path.resolve(
                strict=True
            )

        except OSError:
            resolved = path.resolve(
                strict=False
            )

        records.append(
            {
                "path":
                    str(
                        path
                    ),
                "resolved":
                    str(
                        resolved
                    ),
                "is_symlink":
                    path.is_symlink(),
                "exists":
                    resolved.is_file(),
                "sha256":
                    (
                        sha256_file(
                            resolved,
                            max_bytes=(
                                16
                                * 1024
                                * 1024
                            ),
                        )
                        if resolved.is_file()
                        else None
                    ),
                "content_serialized":
                    False,
            }
        )

    test = _run(
        [
            "nginx",
            "-t",
        ],
        timeout=8.0,
    )

    return {
        "configuration_test_ok":
            test.get(
                "ok",
                False,
            ),
        "configuration_files":
            records,
        "configuration_content_serialized":
            False,
    }


def process_state(
    runtime: Path,
) -> dict[str, Any]:
    records: list[
        dict[str, Any]
    ] = []

    try:
        import psutil

        for process in psutil.process_iter(
            [
                "pid",
                "name",
                "exe",
                "cwd",
                "create_time",
            ]
        ):
            try:
                info = process.info

                name = str(
                    info.get(
                        "name"
                    )
                    or ""
                )

                executable = str(
                    info.get(
                        "exe"
                    )
                    or ""
                )

                cwd = str(
                    info.get(
                        "cwd"
                    )
                    or ""
                )

                relevant = (
                    str(
                        runtime
                    )
                    in cwd
                    or str(
                        runtime
                    )
                    in executable
                    or "savant"
                    in name.casefold()
                    or "palaver"
                    in name.casefold()
                )

                if not relevant:
                    continue

                records.append(
                    {
                        "pid":
                            int(
                                info[
                                    "pid"
                                ]
                            ),
                        "name":
                            name,
                        "exe":
                            (
                                executable
                                or None
                            ),
                        "cwd":
                            (
                                cwd
                                or None
                            ),
                        "create_time":
                            info.get(
                                "create_time"
                            ),
                    }
                )

            except (
                psutil.Error,
                OSError,
                ValueError,
            ):
                continue

    except ImportError:
        proc = Path(
            "/proc"
        )

        candidates = (
            proc.iterdir()
            if proc.is_dir()
            else []
        )

        for candidate in candidates:
            if not candidate.name.isdigit():
                continue

            try:
                cwd = os.readlink(
                    candidate
                    / "cwd"
                )

            except OSError:
                cwd = ""

            try:
                executable = os.readlink(
                    candidate
                    / "exe"
                )

            except OSError:
                executable = ""

            try:
                name = (
                    candidate
                    / "comm"
                ).read_text(
                    encoding="utf-8",
                    errors="replace",
                ).strip()

            except OSError:
                name = ""

            relevant = (
                str(
                    runtime
                )
                in cwd
                or str(
                    runtime
                )
                in executable
                or "savant"
                in name.casefold()
                or "palaver"
                in name.casefold()
            )

            if relevant:
                records.append(
                    {
                        "pid":
                            int(
                                candidate.name
                            ),
                        "name":
                            name,
                        "exe":
                            (
                                executable
                                or None
                            ),
                        "cwd":
                            (
                                cwd
                                or None
                            ),
                        "create_time":
                            None,
                    }
                )

    records.sort(
        key=lambda item:
            item[
                "pid"
            ]
    )

    return {
        "processes":
            records,
        "arguments_serialized":
            False,
        "environment_values_serialized":
            False,
    }


def network_state() -> dict[str, Any]:
    listeners: list[
        dict[str, Any]
    ] = []

    try:
        import psutil

        for connection in psutil.net_connections(
            kind="inet"
        ):
            if (
                connection.status
                != psutil.CONN_LISTEN
                or not connection.laddr
            ):
                continue

            listeners.append(
                {
                    "host":
                        connection.laddr.ip,
                    "port":
                        connection.laddr.port,
                    "pid":
                        connection.pid,
                }
            )

    except (
        ImportError,
        PermissionError,
    ):
        result = _run(
            [
                "ss",
                "-H",
                "-ltnp",
            ]
        )

        if result.get(
            "ok"
        ):
            for line in str(
                result.get(
                    "stdout",
                    "",
                )
            ).splitlines():
                fields = line.split()

                if len(
                    fields
                ) < 4:
                    continue

                listeners.append(
                    {
                        "local":
                            fields[
                                3
                            ],
                        "process":
                            (
                                fields[
                                    -1
                                ]
                                if "users:("
                                in fields[
                                    -1
                                ]
                                else None
                            ),
                    }
                )

    return {
        "tcp_listeners":
            listeners,
        "remote_connections_serialized":
            False,
    }


def toolchain_state() -> list[
    dict[str, Any]
]:
    commands = (
        (
            "python3",
            [
                "python3",
                "--version",
            ],
        ),
        (
            "node",
            [
                "node",
                "--version",
            ],
        ),
        (
            "npm",
            [
                "npm",
                "--version",
            ],
        ),
        (
            "git",
            [
                "git",
                "--version",
            ],
        ),
        (
            "nginx",
            [
                "nginx",
                "-v",
            ],
        ),
        (
            "cloudflared",
            [
                "cloudflared",
                "--version",
            ],
        ),
        (
            "systemd",
            [
                "systemctl",
                "--version",
            ],
        ),
    )

    records = []

    for name, command in commands:
        executable = shutil.which(
            command[
                0
            ]
        )

        if not executable:
            records.append(
                {
                    "name":
                        name,
                    "available":
                        False,
                }
            )

            continue

        result = _run(
            command
        )

        combined = str(
            result.get(
                "stdout"
            )
            or result.get(
                "stderr"
            )
            or ""
        )

        records.append(
            {
                "name":
                    name,
                "available":
                    True,
                "executable":
                    executable,
                "version_line":
                    (
                        combined.splitlines()[
                            0
                        ]
                        if combined
                        else None
                    ),
            }
        )

    return records


def _iter_target_files(
    targets: Iterable[Path],
) -> Iterable[
    tuple[
        Path,
        Path,
    ]
]:
    for target in targets:
        if target.is_file():
            yield (
                target.parent,
                target,
            )

            continue

        if not target.is_dir():
            continue

        for (
            current,
            directories,
            filenames,
        ) in os.walk(
            target,
            followlinks=False,
        ):
            directories[:] = [
                name
                for name
                in sorted(
                    directories,
                    key=str.casefold,
                )
                if (
                    name.casefold()
                    not in ignored_walk_names
                )
            ]

            root = Path(
                current
            )

            for name in sorted(
                filenames,
                key=str.casefold,
            ):
                yield (
                    target,
                    root
                    / name,
                )


def filesystem_fingerprint(
    targets: list[Path],
) -> dict[str, Any]:
    digest = hashlib.sha256()

    files = 0
    directories: set[str] = set()
    symlinks = 0
    bytes_seen = 0
    failures = 0

    top_levels: Counter[
        str
    ] = Counter()

    extensions: Counter[
        str
    ] = Counter()

    for (
        root,
        path,
    ) in _iter_target_files(
        targets
    ):
        try:
            relative = path.relative_to(
                root
            ).as_posix()

            info = path.lstat()

        except OSError:
            failures += 1
            continue

        parent = Path(
            relative
        ).parent

        while str(
            parent
        ) not in {
            "",
            ".",
        }:
            directories.add(
                parent.as_posix()
            )

            parent = (
                parent.parent
            )

        top = relative.split(
            "/",
            1,
        )[
            0
        ]

        top_levels[
            top
        ] += 1

        if stat.S_ISLNK(
            info.st_mode
        ):
            symlinks += 1

            try:
                target_value = (
                    os.readlink(
                        path
                    )
                )

            except OSError:
                target_value = ""

            material = (
                f"l\0{relative}\0"
                f"{target_value}\0"
                f"{info.st_mtime_ns}\n"
            )

            digest.update(
                material.encode(
                    "utf-8",
                    errors="surrogateescape",
                )
            )

            continue

        if not stat.S_ISREG(
            info.st_mode
        ):
            continue

        files += 1
        bytes_seen += (
            info.st_size
        )

        extensions[
            (
                path.suffix.casefold()
                or "[none]"
            )
        ] += 1

        material = (
            f"f\0{relative}\0"
            f"{info.st_size}\0"
            f"{info.st_mtime_ns}\0"
            f"{stat.S_IMODE(info.st_mode):o}\n"
        )

        digest.update(
            material.encode(
                "utf-8",
                errors="surrogateescape",
            )
        )

    return {
        "algorithm":
            "sha256",
        "metadata_merkle_root":
            digest.hexdigest(),
        "regular_files":
            files,
        "directories":
            len(
                directories
            ),
        "symlinks":
            symlinks,
        "bytes":
            bytes_seen,
        "failures":
            failures,
        "top_level_file_counts":
            dict(
                sorted(
                    top_levels.items()
                )
            ),
        "extension_counts":
            dict(
                sorted(
                    extensions.items()
                )
            ),
        "content_hash_scope":
            (
                "metadata fingerprint; "
                "source content identity remains "
                "the canonical sdump sha256 projection"
            ),
    }


def package_state(
    targets: list[Path],
) -> list[
    dict[str, Any]
]:
    records = []

    for (
        root,
        path,
    ) in _iter_target_files(
        targets
    ):
        if (
            path.name.casefold()
            not in package_names
        ):
            continue

        try:
            relative = (
                path.relative_to(
                    root
                ).as_posix()
            )

            info = path.stat()

        except OSError:
            continue

        records.append(
            {
                "target":
                    str(
                        root
                    ),
                "path":
                    relative,
                "size":
                    info.st_size,
                "mtime_ns":
                    info.st_mtime_ns,
                "sha256":
                    sha256_file(
                        path,
                        max_bytes=(
                            64
                            * 1024
                            * 1024
                        ),
                    ),
                "content_serialized_elsewhere_if_included":
                    True,
            }
        )

    return sorted(
        records,
        key=lambda item:
            (
                item[
                    "target"
                ],
                item[
                    "path"
                ].casefold(),
            ),
    )


def sqlite_state(
    targets: list[Path],
) -> list[
    dict[str, Any]
]:
    records = []

    for (
        root,
        path,
    ) in _iter_target_files(
        targets
    ):
        if (
            path.suffix.casefold()
            not in sqlite_suffixes
            or _is_secret_path(
                path
            )
        ):
            continue

        try:
            relative = (
                path.relative_to(
                    root
                ).as_posix()
            )

            info = path.stat()

        except OSError:
            continue

        record: dict[
            str,
            Any,
        ] = {
            "target":
                str(
                    root
                ),
            "path":
                relative,
            "size":
                info.st_size,
            "mtime_ns":
                info.st_mtime_ns,
            "sha256":
                sha256_file(
                    path,
                    max_bytes=(
                        64
                        * 1024
                        * 1024
                    ),
                ),
            "sample_sha256":
                sample_sha256(
                    path
                ),
            "content_serialized":
                False,
            "open_mode":
                "read-only",
            "authority_effect":
                "none",
        }

        wal = path.with_name(
            path.name
            + "-wal"
        )

        shm = path.with_name(
            path.name
            + "-shm"
        )

        record[
            "wal_size"
        ] = (
            wal.stat().st_size
            if wal.is_file()
            else 0
        )

        record[
            "shm_size"
        ] = (
            shm.stat().st_size
            if shm.is_file()
            else 0
        )

        try:
            connection = sqlite3.connect(
                (
                    f"file:{path}"
                    "?mode=ro"
                ),
                uri=True,
                timeout=1.0,
            )

            try:
                tables = [
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
                            "AND name NOT LIKE "
                            "'sqlite_%' "
                            "ORDER BY name"
                        )
                    )
                ]

                user_version = (
                    connection.execute(
                        "PRAGMA user_version"
                    ).fetchone()
                )

                schema_version = (
                    connection.execute(
                        "PRAGMA schema_version"
                    ).fetchone()
                )

                page_count = (
                    connection.execute(
                        "PRAGMA page_count"
                    ).fetchone()
                )

                page_size = (
                    connection.execute(
                        "PRAGMA page_size"
                    ).fetchone()
                )

                record.update(
                    {
                        "tables":
                            tables,
                        "table_count":
                            len(
                                tables
                            ),
                        "user_version":
                            (
                                int(
                                    user_version[
                                        0
                                    ]
                                )
                                if user_version
                                else None
                            ),
                        "schema_version":
                            (
                                int(
                                    schema_version[
                                        0
                                    ]
                                )
                                if schema_version
                                else None
                            ),
                        "page_count":
                            (
                                int(
                                    page_count[
                                        0
                                    ]
                                )
                                if page_count
                                else None
                            ),
                        "page_size":
                            (
                                int(
                                    page_size[
                                        0
                                    ]
                                )
                                if page_size
                                else None
                            ),
                    }
                )

            finally:
                connection.close()

        except sqlite3.Error as error:
            record[
                "inspection_error"
            ] = type(
                error
            ).__name__

        records.append(
            record
        )

    return sorted(
        records,
        key=lambda item:
            (
                item[
                    "target"
                ],
                item[
                    "path"
                ].casefold(),
            ),
    )


def _locate_record_path(
    relative: str,
    targets: list[Path],
) -> Path | None:
    if len(
        targets
    ) == 1:
        candidate = (
            targets[
                0
            ]
            / relative
            if targets[
                0
            ].is_dir()
            else targets[
                0
            ]
        )

        return (
            candidate
            if candidate.exists()
            else None
        )

    first, separator, rest = (
        relative.partition(
            "/"
        )
    )

    if not separator:
        return None

    for target in targets:
        if target.name != first:
            continue

        candidate = (
            target
            / rest
            if target.is_dir()
            else target
        )

        return (
            candidate
            if candidate.exists()
            else None
        )

    return None


def projection_gap_state(
    projection: Projection,
    targets: list[Path],
) -> dict[str, Any]:
    reason_counts = Counter(
        item.reason
        for item
        in projection.skipped
    )

    oversized = []

    for item in projection.skipped:
        if (
            item.reason
            != "max_file_bytes_exceeded"
        ):
            continue

        path = _locate_record_path(
            item.path,
            targets,
        )

        record: dict[
            str,
            Any,
        ] = {
            "path":
                item.path,
            "size":
                item.size,
            "reason":
                item.reason,
            "content_serialized":
                False,
        }

        if (
            path is not None
            and path.is_file()
            and not _is_secret_path(
                path
            )
        ):
            try:
                record[
                    "mtime_ns"
                ] = (
                    path.stat().st_mtime_ns
                )

            except OSError:
                record[
                    "mtime_ns"
                ] = None

            record[
                "sample_sha256"
            ] = sample_sha256(
                path
            )

            record[
                "sha256"
            ] = sha256_file(
                path,
                max_bytes=(
                    16
                    * 1024
                    * 1024
                ),
            )

        oversized.append(
            record
        )

    return {
        "skipped_count":
            len(
                projection.skipped
            ),
        "failure_count":
            len(
                projection.failures
            ),
        "skipped_by_reason":
            dict(
                sorted(
                    reason_counts.items()
                )
            ),
        "oversized_metadata":
            oversized,
        "oversized_full_hash_limit_bytes":
            16
            * 1024
            * 1024,
        "oversized_sample_hash_semantics":
            (
                "sha256(first 64 KiB + "
                "last 64 KiB + decimal size)"
            ),
        "omitted_content_remains_unknown":
            True,
    }


def living_state_reference(
    runtime: Path,
) -> dict[str, Any]:
    root = (
        runtime
        / "runtime"
        / "living-state"
    )

    current = (
        root
        / "current.json"
    )

    health = (
        root
        / "health.json"
    )

    result: dict[
        str,
        Any,
    ] = {
        "available":
            current.is_file(),
        "path":
            str(
                current
            ),
        "authority_effect":
            "none",
    }

    if current.is_file():
        result[
            "sha256"
        ] = sha256_file(
            current,
            max_bytes=(
                64
                * 1024
                * 1024
            ),
        )

        try:
            payload = json.loads(
                current.read_text(
                    encoding="utf-8"
                )
            )

            if isinstance(
                payload,
                dict,
            ):
                for field in (
                    "schema",
                    "sequence",
                    "snapshot_hash",
                    "generated_at_unix_ns",
                    "previous_snapshot_hash",
                ):
                    result[
                        field
                    ] = payload.get(
                        field
                    )

        except (
            OSError,
            json.JSONDecodeError,
        ):
            result[
                "readable"
            ] = False

    if health.is_file():
        result[
            "health_sha256"
        ] = sha256_file(
            health,
            max_bytes=(
                4
                * 1024
                * 1024
            ),
        )

    return result


def deployment_state() -> dict[str, Any]:
    paths = [
        Path(
            "/usr/local/bin/sdump"
        ),
        Path(
            "/usr/local/bin/savant-state"
        ),
    ]

    records = []

    for path in paths:
        if not path.exists():
            records.append(
                {
                    "path":
                        str(
                            path
                        ),
                    "exists":
                        False,
                }
            )

            continue

        try:
            resolved = path.resolve(
                strict=True
            )

        except OSError:
            resolved = path.resolve(
                strict=False
            )

        records.append(
            {
                "path":
                    str(
                        path
                    ),
                "exists":
                    True,
                "resolved":
                    str(
                        resolved
                    ),
                "sha256":
                    (
                        sha256_file(
                            resolved,
                            max_bytes=(
                                16
                                * 1024
                                * 1024
                            ),
                        )
                        if resolved.is_file()
                        else None
                    ),
            }
        )

    return {
        "entrypoints":
            records,
    }


def host_state() -> dict[str, Any]:
    disk = shutil.disk_usage(
        "/"
    )

    memory: dict[
        str,
        int,
    ] = {}

    try:
        for line in Path(
            "/proc/meminfo"
        ).read_text(
            encoding="utf-8"
        ).splitlines():
            key, separator, value = (
                line.partition(
                    ":"
                )
            )

            if not separator:
                continue

            token = (
                value.strip()
                .split()[
                    0
                ]
            )

            if token.isdigit():
                memory[
                    key
                ] = (
                    int(
                        token
                    )
                    * 1024
                )

    except OSError:
        pass

    try:
        uptime = float(
            Path(
                "/proc/uptime"
            ).read_text(
                encoding="utf-8"
            ).split()[
                0
            ]
        )

    except (
        OSError,
        ValueError,
        IndexError,
    ):
        uptime = None

    try:
        load = os.getloadavg()

    except OSError:
        load = (
            None,
            None,
            None,
        )

    return {
        "hostname":
            socket.gethostname(),
        "kernel":
            os.uname().release,
        "machine":
            os.uname().machine,
        "uptime_seconds":
            uptime,
        "load_average":
            {
                "1m":
                    load[
                        0
                    ],
                "5m":
                    load[
                        1
                    ],
                "15m":
                    load[
                        2
                    ],
            },
        "disk_root":
            {
                "total":
                    disk.total,
                "used":
                    disk.used,
                "free":
                    disk.free,
            },
        "memory":
            memory,
    }


def projection_fingerprint(
    projection: Projection,
) -> dict[str, Any]:
    records = [
        {
            "path":
                record.path,
            "source_sha256":
                record.source_sha256,
            "rendered_sha256":
                record.rendered_sha256,
            "content_id":
                record.content_id,
            "included":
                record.included,
            "reason":
                record.reason,
        }
        for record
        in projection.records
    ]

    return {
        "snapshot_hash":
            projection.snapshot_hash,
        "record_merkle_root":
            stable_hash(
                records
            ),
        "record_count":
            len(
                records
            ),
        "included_count":
            sum(
                bool(
                    record.included
                )
                for record
                in projection.records
            ),
    }


def _module_available(
    name: str,
) -> bool:
    try:
        __import__(
            name
        )

        return True

    except ImportError:
        return False


def build_state_capsule(
    manifest: Mapping[str, Any],
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

    runtime = Path(
        "/root/savant-runtime"
    ).resolve(
        strict=False
    )

    started = time.monotonic()

    capsule: dict[
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
        "targets":
            [
                str(
                    path
                )
                for path
                in targets
            ],
        "projection":
            projection_fingerprint(
                projection
            ),
        "filesystem_fingerprint":
            filesystem_fingerprint(
                targets
            ),
        "projection_gaps":
            projection_gap_state(
                projection,
                targets,
            ),
        "environment":
            environment_state(
                runtime
            ),
        "services":
            service_state(),
        "nginx":
            nginx_state(),
        "processes":
            process_state(
                runtime
            ),
        "network":
            network_state(),
        "toolchain":
            toolchain_state(),
        "packages":
            package_state(
                targets
            ),
        "sqlite":
            sqlite_state(
                targets
            ),
        "living_state":
            living_state_reference(
                runtime
            ),
        "deployment":
            deployment_state(),
        "host":
            host_state(),
        "capabilities":
            {
                "orjson":
                    _module_available(
                        "orjson"
                    ),
                "blake3":
                    _module_available(
                        "blake3"
                    ),
                "pathspec":
                    _module_available(
                        "pathspec"
                    ),
                "watchfiles":
                    _module_available(
                        "watchfiles"
                    ),
                "psutil":
                    _module_available(
                        "psutil"
                    ),
                "boto3":
                    _module_available(
                        "boto3"
                    ),
                "zstandard":
                    _module_available(
                        "zstandard"
                    ),
                "environment_values_serialized":
                    False,
                "process_arguments_serialized":
                    False,
                "remote_connection_inventory_serialized":
                    False,
                "sqlite_content_serialized":
                    False,
            },
    }

    capsule[
        "build_duration_seconds"
    ] = round(
        (
            time.monotonic()
            - started
        ),
        6,
    )

    hash_material = dict(
        capsule
    )

    hash_material.pop(
        "build_duration_seconds",
        None,
    )

    capsule[
        "capsule_sha256"
    ] = stable_hash(
        hash_material
    )

    return capsule
