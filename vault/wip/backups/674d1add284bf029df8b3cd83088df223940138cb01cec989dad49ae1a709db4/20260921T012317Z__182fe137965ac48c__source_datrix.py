#!/usr/bin/env python3

from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import signal
import sys
import time
from typing import Any, Iterable

from .datrix import StraubDatrix


schema = "savant.carbon.straub.source-datrix.v1"
owner = "carbon"
module = "straub"
authority_effect = "none"

runtime_root = Path(
    "/root/savant-runtime"
).resolve()

state_root = (
    runtime_root
    / "runtime"
    / "straub"
    / "source-datrix-state"
)

datrix_path = (
    state_root
    / "source.datrix.json"
)

status_path = (
    state_root
    / "status.json"
)

projection_path = (
    state_root
    / "current.json"
)

poll_seconds = 1.0

source_extensions = frozenset(
    {
        ".py",
        ".pyi",
        ".js",
        ".jsx",
        ".mjs",
        ".cjs",
        ".ts",
        ".tsx",
        ".mts",
        ".cts",
        ".go",
        ".rs",
        ".java",
        ".kt",
        ".kts",
        ".c",
        ".cc",
        ".cpp",
        ".cxx",
        ".h",
        ".hh",
        ".hpp",
        ".hxx",
        ".cs",
        ".rb",
        ".php",
        ".lua",
        ".pl",
        ".r",
        ".sh",
        ".bash",
        ".zsh",
        ".fish",
        ".ps1",
        ".sql",
        ".graphql",
        ".gql",
        ".json",
        ".jsonl",
        ".yaml",
        ".yml",
        ".toml",
        ".ini",
        ".cfg",
        ".conf",
        ".properties",
        ".xml",
        ".xsd",
        ".html",
        ".htm",
        ".css",
        ".scss",
        ".sass",
        ".less",
        ".vue",
        ".svelte",
        ".tf",
        ".tfvars",
        ".gradle",
    }
)

source_filenames = frozenset(
    {
        "dockerfile",
        "containerfile",
        "makefile",
        "procfile",
        "rakefile",
        "gemfile",
        "gemfile.lock",
        "pipfile",
        "pipfile.lock",
        "justfile",
        "requirements.txt",
        "requirements-dev.txt",
        "requirements-test.txt",
        "constraints.txt",
        "package.json",
        "package-lock.json",
        "yarn.lock",
        "pnpm-lock.yaml",
        "bun.lock",
        "cargo.toml",
        "cargo.lock",
        "go.mod",
        "go.sum",
        "pom.xml",
        "build.gradle",
        "settings.gradle",
        "composer.json",
        "composer.lock",
        "pyproject.toml",
        "tsconfig.json",
        "jsconfig.json",
    }
)

hard_excluded_directory_names = frozenset(
    {
        ".git",
        ".hg",
        ".svn",
        "__pycache__",
        ".pytest_cache",
        ".hypothesis",
        ".mypy_cache",
        ".ruff_cache",
        ".tox",
        ".nox",
        ".cache",
        ".next",
        ".nuxt",
        ".svelte-kit",
        ".turbo",
        ".vercel",
        ".parcel-cache",
        ".vite",
        "node_modules",
        "site-packages",
        "vendor",
        "dist",
        "build",
        "coverage",
        "target",
        "out",
        "obj",
    }
)

generated_path_prefixes = (
    "runtime/straub/source-datrix-state/",
    "savant-sdump-output/",
)

backup_suffix_markers = (
    ".save",
    ".bak",
    ".backup",
    ".old",
    ".orig",
    ".rej",
    ".previous",
)

backup_name_markers = (
    ".before-",
    ".pre-",
    ".previous-",
)

secret_names = frozenset(
    {
        ".env",
        "credentials.json",
        "id_rsa",
        "id_ed25519",
    }
)


@dataclass(frozen=True)
class SourceObservation:
    path: str
    size: int
    mtime_ns: int
    mode: int
    digest: str
    content: str
    encoding: str


def utc_now() -> str:
    return (
        datetime.now(
            timezone.utc
        )
        .isoformat()
        .replace(
            "+00:00",
            "Z",
        )
    )


def atomic_json(
    path: Path,
    value: Any,
) -> None:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    payload = (
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(
                ",",
                ":",
            ),
        )
        + "\n"
    )

    temporary = path.with_name(
        f".{path.name}.{os.getpid()}.tmp"
    )

    with temporary.open(
        "w",
        encoding="utf-8",
    ) as handle:
        handle.write(
            payload
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


def sha256_bytes(
    value: bytes,
) -> str:
    return hashlib.sha256(
        value
    ).hexdigest()


def stable_id(
    prefix: str,
    *values: str,
) -> str:
    material = "\x00".join(
        values
    ).encode(
        "utf-8"
    )

    return (
        prefix
        + "."
        + sha256_bytes(
            material
        )[:32]
    )


def relative_path(
    path: Path,
) -> str:
    return (
        path.resolve()
        .relative_to(
            runtime_root
        )
        .as_posix()
    )


def excluded_directory(
    name: str,
) -> bool:
    lowered = name.casefold()

    if (
        lowered
        in hard_excluded_directory_names
    ):
        return True

    if lowered.startswith(
        ".venv"
    ):
        return True

    if lowered == "venv":
        return True

    if lowered.startswith(
        "venv-"
    ):
        return True

    return False


def generated_path(
    relative: str,
) -> bool:
    lowered = relative.casefold()

    return any(
        lowered.startswith(
            prefix.casefold()
        )
        for prefix
        in generated_path_prefixes
    )


def backup_path(
    path: Path,
) -> bool:
    lowered = path.name.casefold()

    if any(
        lowered.endswith(
            marker
        )
        for marker
        in backup_suffix_markers
    ):
        return True

    return any(
        marker
        in lowered
        for marker
        in backup_name_markers
    )


def secret_path(
    path: Path,
) -> bool:
    lowered = path.name.casefold()

    if lowered in secret_names:
        return True

    if lowered.startswith(
        ".env."
    ):
        return True

    if lowered.endswith(
        ".pem"
    ):
        return True

    if lowered.endswith(
        ".key"
    ):
        return True

    return False


def has_program_shebang(
    path: Path,
) -> bool:
    try:
        with path.open(
            "rb"
        ) as handle:
            first = handle.readline(
                512
            )
    except OSError:
        return False

    if not first.startswith(
        b"#!"
    ):
        return False

    lowered = first.lower()

    interpreters = (
        b"python",
        b"node",
        b"deno",
        b"bun",
        b"bash",
        b"/sh",
        b"zsh",
        b"fish",
        b"ruby",
        b"perl",
        b"php",
        b"lua",
        b"pwsh",
        b"powershell",
    )

    return any(
        token in lowered
        for token
        in interpreters
    )


def admitted(
    path: Path,
) -> bool:
    try:
        relative = relative_path(
            path
        )
    except ValueError:
        return False

    if generated_path(
        relative
    ):
        return False

    if backup_path(
        path
    ):
        return False

    if secret_path(
        path
    ):
        return False

    lowered_name = (
        path.name.casefold()
    )

    if (
        lowered_name
        in source_filenames
    ):
        return True

    if (
        path.suffix.casefold()
        in source_extensions
    ):
        return True

    return has_program_shebang(
        path
    )


def walk_source_paths() -> Iterable[
    Path
]:
    for (
        directory,
        directories,
        filenames,
    ) in os.walk(
        runtime_root,
        topdown=True,
        followlinks=False,
    ):
        directories[:] = sorted(
            name
            for name
            in directories
            if not excluded_directory(
                name
            )
        )

        base = Path(
            directory
        )

        for filename in sorted(
            filenames
        ):
            path = (
                base
                / filename
            )

            try:
                if (
                    path.is_symlink()
                    or not path.is_file()
                ):
                    continue
            except OSError:
                continue

            if admitted(
                path
            ):
                yield path


def observe(
    path: Path,
) -> SourceObservation:
    stat_result = path.stat()

    raw = path.read_bytes()

    try:
        content = raw.decode(
            "utf-8"
        )

        encoding = "utf-8"

    except UnicodeDecodeError:
        content = raw.decode(
            "utf-8",
            errors="replace",
        )

        encoding = (
            "utf-8-replacement"
        )

    return SourceObservation(
        path=relative_path(
            path
        ),
        size=len(
            raw
        ),
        mtime_ns=(
            stat_result.st_mtime_ns
        ),
        mode=(
            stat_result.st_mode
            & 0o7777
        ),
        digest=sha256_bytes(
            raw
        ),
        content=content,
        encoding=encoding,
    )


def observation_index() -> dict[
    str,
    SourceObservation,
]:
    result: dict[
        str,
        SourceObservation,
    ] = {}

    for path in walk_source_paths():
        try:
            item = observe(
                path
            )
        except (
            FileNotFoundError,
            PermissionError,
            OSError,
        ):
            continue

        result[
            item.path
        ] = item

    return result


def datrix() -> StraubDatrix:
    state_root.mkdir(
        parents=True,
        exist_ok=True,
    )

    return StraubDatrix.open(
        datrix_path
    )


def revision_record(
    observation: SourceObservation,
    *,
    predecessor: str | None,
    event: str,
) -> dict[str, Any]:
    revision_id = stable_id(
        "source-revision",
        observation.path,
        observation.digest,
    )

    dependencies = (
        [predecessor]
        if predecessor
        else []
    )

    lineage = {
        "predecessor": predecessor,
        "event": event,
    }

    return {
        "id":
            revision_id,
        "kind":
            "source.revision",
        "status":
            "active",
        "authority":
            {
                "authority_effect":
                    "none",
                "filesystem_presence_establishes_authority":
                    False,
                "semantic_authority":
                    None,
            },
        "payload":
            {
                "path":
                    observation.path,
                "sha256":
                    observation.digest,
                "size":
                    observation.size,
                "mtime_ns":
                    observation.mtime_ns,
                "mode":
                    observation.mode,
                "encoding":
                    observation.encoding,
                "content":
                    observation.content,
            },
        "metadata":
            {
                "schema":
                    schema,
                "owner":
                    owner,
                "module":
                    module,
                "source_kind":
                    "regular_file",
                "projection_only":
                    False,
            },
        "dependencies":
            dependencies,
        "relationships":
            [],
        "provenance":
            {
                "source":
                    str(
                        runtime_root
                    ),
                "path":
                    observation.path,
                "observed_at":
                    utc_now(),
                "observer":
                    "straub.source-datrix",
            },
        "lineage":
            lineage,
    }


def deletion_record(
    path: str,
    *,
    predecessor: str | None,
) -> dict[str, Any]:
    event_time = utc_now()

    deletion_id = stable_id(
        "source-deletion",
        path,
        predecessor or "",
        event_time,
    )

    return {
        "id":
            deletion_id,
        "kind":
            "source.deletion",
        "status":
            "active",
        "authority":
            {
                "authority_effect":
                    "none",
                "filesystem_presence_establishes_authority":
                    False,
            },
        "payload":
            {
                "path":
                    path,
                "deleted":
                    True,
            },
        "metadata":
            {
                "schema":
                    schema,
                "owner":
                    owner,
                "module":
                    module,
            },
        "dependencies":
            (
                [predecessor]
                if predecessor
                else []
            ),
        "relationships":
            [],
        "provenance":
            {
                "source":
                    str(
                        runtime_root
                    ),
                "path":
                    path,
                "observed_at":
                    event_time,
                "observer":
                    "straub.source-datrix",
            },
        "lineage":
            {
                "predecessor":
                    predecessor,
                "event":
                    "delete",
            },
    }


def registry_subjects(
    source_datrix: StraubDatrix,
) -> list[
    dict[str, Any]
]:
    projection = (
        source_datrix
        .registry
        .isotope()
    )

    subjects = projection.get(
        "subjects",
        []
    )

    if not isinstance(
        subjects,
        list,
    ):
        return []

    return [
        item
        for item
        in subjects
        if isinstance(
            item,
            dict,
        )
    ]


def current_from_datrix(
    source_datrix: StraubDatrix,
) -> dict[
    str,
    dict[str, Any],
]:
    current: dict[
        str,
        dict[str, Any],
    ] = {}

    subjects = registry_subjects(
        source_datrix
    )

    for subject in subjects:
        kind = subject.get(
            "kind"
        )

        payload = subject.get(
            "payload"
        )

        if not isinstance(
            payload,
            dict,
        ):
            continue

        path = payload.get(
            "path"
        )

        if not isinstance(
            path,
            str,
        ):
            continue

        provenance = subject.get(
            "provenance"
        )

        observed_at = ""

        if isinstance(
            provenance,
            dict,
        ):
            observed_at = str(
                provenance.get(
                    "observed_at"
                )
                or ""
            )

        candidate = {
            "id":
                subject.get(
                    "id"
                ),
            "kind":
                kind,
            "path":
                path,
            "observed_at":
                observed_at,
            "payload":
                payload,
        }

        previous = current.get(
            path
        )

        if (
            previous is None
            or (
                candidate[
                    "observed_at"
                ],
                str(
                    candidate[
                        "id"
                    ]
                ),
            )
            > (
                previous[
                    "observed_at"
                ],
                str(
                    previous[
                        "id"
                    ]
                ),
            )
        ):
            current[
                path
            ] = candidate

    return {
        path: item
        for (
            path,
            item,
        ) in current.items()
        if (
            item[
                "kind"
            ]
            == "source.revision"
            and not item[
                "payload"
            ].get(
                "deleted",
                False,
            )
        )
    }


def write_projection(
    source_datrix: StraubDatrix,
) -> dict[str, Any]:
    current = current_from_datrix(
        source_datrix
    )

    files: list[
        dict[str, Any]
    ] = []

    total_bytes = 0

    for path in sorted(
        current
    ):
        item = current[
            path
        ]

        payload = item[
            "payload"
        ]

        size = int(
            payload.get(
                "size",
                0,
            )
        )

        total_bytes += size

        files.append(
            {
                "path":
                    path,
                "revision_id":
                    item[
                        "id"
                    ],
                "sha256":
                    payload.get(
                        "sha256"
                    ),
                "size":
                    size,
                "mtime_ns":
                    payload.get(
                        "mtime_ns"
                    ),
                "mode":
                    payload.get(
                        "mode"
                    ),
                "encoding":
                    payload.get(
                        "encoding"
                    ),
                "content":
                    payload.get(
                        "content",
                        "",
                    ),
            }
        )

    projection = {
        "schema":
            "savant.carbon.straub."
            "source-datrix-projection.v1",
        "authority_effect":
            "none",
        "projection_only":
            True,
        "filesystem_presence_establishes_authority":
            False,
        "source_datrix":
            str(
                datrix_path
            ),
        "root":
            str(
                runtime_root
            ),
        "generated_at":
            utc_now(),
        "file_count":
            len(
                files
            ),
        "source_bytes":
            total_bytes,
        "files":
            files,
    }

    atomic_json(
        projection_path,
        projection,
    )

    return projection


def checkpoint_with_retry(
    source_datrix: StraubDatrix,
) -> None:
    try:
        source_datrix.checkpoint()

    except Exception:
        source_datrix.reload()
        raise


def reconcile(
    source_datrix: StraubDatrix,
) -> dict[str, Any]:
    started = time.monotonic()

    observed = observation_index()

    current = current_from_datrix(
        source_datrix
    )

    created = 0
    modified = 0
    deleted = 0
    unchanged = 0

    changed = False

    for path in sorted(
        observed
    ):
        item = observed[
            path
        ]

        existing = current.get(
            path
        )

        predecessor = (
            str(
                existing[
                    "id"
                ]
            )
            if existing
            else None
        )

        previous_digest = (
            existing[
                "payload"
            ].get(
                "sha256"
            )
            if existing
            else None
        )

        if (
            previous_digest
            == item.digest
        ):
            unchanged += 1
            continue

        event = (
            "create"
            if existing is None
            else "modify"
        )

        source_datrix.registry.substantiate(
            revision_record(
                item,
                predecessor=(
                    predecessor
                ),
                event=event,
            )
        )

        changed = True

        if event == "create":
            created += 1
        else:
            modified += 1

    observed_paths = set(
        observed
    )

    for path in sorted(
        set(
            current
        )
        - observed_paths
    ):
        existing = current[
            path
        ]

        source_datrix.registry.substantiate(
            deletion_record(
                path,
                predecessor=str(
                    existing[
                        "id"
                    ]
                ),
            )
        )

        deleted += 1
        changed = True

    if changed:
        checkpoint_with_retry(
            source_datrix
        )

    projection = write_projection(
        source_datrix
    )

    elapsed = (
        time.monotonic()
        - started
    )

    result = {
        "schema":
            "savant.carbon.straub."
            "source-datrix-reconcile.v1",
        "authority_effect":
            "none",
        "root":
            str(
                runtime_root
            ),
        "datrix":
            str(
                datrix_path
            ),
        "projection":
            str(
                projection_path
            ),
        "observed_files":
            len(
                observed
            ),
        "current_files":
            projection[
                "file_count"
            ],
        "source_bytes":
            projection[
                "source_bytes"
            ],
        "created":
            created,
        "modified":
            modified,
        "deleted":
            deleted,
        "unchanged":
            unchanged,
        "changed":
            changed,
        "elapsed_seconds":
            round(
                elapsed,
                6,
            ),
        "completed_at":
            utc_now(),
    }

    return result


class SourceDatrixDaemon:
    def __init__(
        self,
        interval: float,
    ) -> None:
        self.interval = max(
            0.25,
            float(
                interval
            ),
        )

        self.running = True

        self.source_datrix = (
            datrix()
        )

    def stop(
        self,
        *_: Any,
    ) -> None:
        self.running = False

    def status(
        self,
        *,
        state: str,
        reconciliation: (
            dict[str, Any]
            | None
        ) = None,
        error: str | None = None,
    ) -> None:
        payload = {
            "schema":
                "savant.carbon.straub."
                "source-datrix-status.v1",
            "authority_effect":
                "none",
            "state":
                state,
            "pid":
                os.getpid(),
            "root":
                str(
                    runtime_root
                ),
            "datrix":
                str(
                    datrix_path
                ),
            "projection":
                str(
                    projection_path
                ),
            "poll_seconds":
                self.interval,
            "updated_at":
                utc_now(),
            "reconciliation":
                reconciliation,
            "error":
                error,
        }

        atomic_json(
            status_path,
            payload,
        )

    def run(
        self,
    ) -> int:
        signal.signal(
            signal.SIGTERM,
            self.stop,
        )

        signal.signal(
            signal.SIGINT,
            self.stop,
        )

        self.status(
            state="starting"
        )

        while self.running:
            try:
                result = reconcile(
                    self.source_datrix
                )

                self.status(
                    state="watching",
                    reconciliation=(
                        result
                    ),
                )

            except Exception as exc:
                self.status(
                    state="error",
                    error=(
                        f"{type(exc).__name__}: "
                        f"{exc}"
                    ),
                )

                return 1

            deadline = (
                time.monotonic()
                + self.interval
            )

            while (
                self.running
                and time.monotonic()
                < deadline
            ):
                time.sleep(
                    min(
                        0.25,
                        max(
                            0.0,
                            deadline
                            - time.monotonic(),
                        ),
                    )
                )

        self.status(
            state="stopped"
        )

        return 0


def print_json(
    value: Any,
) -> None:
    print(
        json.dumps(
            value,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )


def command_reconcile() -> int:
    source_datrix = datrix()

    result = reconcile(
        source_datrix
    )

    print_json(
        result
    )

    return 0


def command_status() -> int:
    if not status_path.is_file():
        print_json(
            {
                "schema":
                    "savant.carbon.straub."
                    "source-datrix-status.v1",
                "state":
                    "unknown",
                "status_file":
                    str(
                        status_path
                    ),
                "authority_effect":
                    "none",
            }
        )

        return 1

    print(
        status_path.read_text(
            encoding="utf-8"
        ),
        end="",
    )

    return 0


def command_project() -> int:
    source_datrix = datrix()

    projection = write_projection(
        source_datrix
    )

    print_json(
        {
            "schema":
                "savant.carbon.straub."
                "source-datrix-project.v1",
            "projection":
                str(
                    projection_path
                ),
            "file_count":
                projection[
                    "file_count"
                ],
            "source_bytes":
                projection[
                    "source_bytes"
                ],
            "authority_effect":
                "none",
        }
    )

    return 0


def command_export(
    output: Path,
) -> int:
    source_datrix = datrix()

    projection = write_projection(
        source_datrix
    )

    output = output.resolve()

    output.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    temporary = output.with_name(
        f".{output.name}.{os.getpid()}.tmp"
    )

    digest = hashlib.sha256()

    with temporary.open(
        "wb"
    ) as handle:
        for item in projection[
            "files"
        ]:
            header = (
                "\n"
                "<<<savant-source-begin>>>\n"
                + json.dumps(
                    {
                        "path":
                            item[
                                "path"
                            ],
                        "sha256":
                            item[
                                "sha256"
                            ],
                        "size":
                            item[
                                "size"
                            ],
                        "encoding":
                            item[
                                "encoding"
                            ],
                        "revision_id":
                            item[
                                "revision_id"
                            ],
                        "authority_effect":
                            "none",
                    },
                    sort_keys=True,
                    separators=(
                        ",",
                        ":",
                    ),
                )
                + "\n"
                "<<<savant-source-body-begin>>>\n"
            ).encode(
                "utf-8"
            )

            body = str(
                item[
                    "content"
                ]
            ).encode(
                "utf-8"
            )

            footer = (
                "\n"
                "<<<savant-source-body-end>>>\n"
                "<<<savant-source-end>>>\n"
            ).encode(
                "utf-8"
            )

            for block in (
                header,
                body,
                footer,
            ):
                handle.write(
                    block
                )

                digest.update(
                    block
                )

        handle.flush()

        os.fsync(
            handle.fileno()
        )

    os.replace(
        temporary,
        output,
    )

    print_json(
        {
            "schema":
                "savant.carbon.straub."
                "source-datrix-export.v1",
            "output":
                str(
                    output
                ),
            "sha256":
                digest.hexdigest(),
            "file_count":
                projection[
                    "file_count"
                ],
            "source_bytes":
                projection[
                    "source_bytes"
                ],
            "authority_effect":
                "none",
        }
    )

    return 0


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(
        prog="source-datrix",
    )

    commands = (
        result.add_subparsers(
            dest="command",
            required=True,
        )
    )

    daemon_parser = (
        commands.add_parser(
            "daemon"
        )
    )

    daemon_parser.add_argument(
        "--interval",
        type=float,
        default=poll_seconds,
    )

    commands.add_parser(
        "reconcile"
    )

    commands.add_parser(
        "status"
    )

    commands.add_parser(
        "project"
    )

    export_parser = (
        commands.add_parser(
            "export"
        )
    )

    export_parser.add_argument(
        "output",
        type=Path,
    )

    return result


def main() -> int:
    arguments = (
        parser()
        .parse_args()
    )

    if (
        arguments.command
        == "daemon"
    ):
        return SourceDatrixDaemon(
            arguments.interval
        ).run()

    if (
        arguments.command
        == "reconcile"
    ):
        return command_reconcile()

    if (
        arguments.command
        == "status"
    ):
        return command_status()

    if (
        arguments.command
        == "project"
    ):
        return command_project()

    if (
        arguments.command
        == "export"
    ):
        return command_export(
            arguments.output
        )

    return 2


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
