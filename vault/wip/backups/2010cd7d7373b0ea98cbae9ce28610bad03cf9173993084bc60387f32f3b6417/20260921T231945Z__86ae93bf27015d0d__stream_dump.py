from __future__ import annotations

import fnmatch
import gzip
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
import stat
import sys
from typing import Any

from .profiles import load_profile
from .scan import language
from .util import now_iso

from straub.source_datrix import (
    current_from_datrix,
    datrix,
)


schema = "savant.sdump.stream.v2"
default_profile = "code"
chunk_size = 1024 * 1024
gzip_level = 9


class StreamDumpError(RuntimeError):
    pass


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
        "venv",
        ".venv",
        "env",
        ".envdir",
        "tmp",
        "temp",
        "backups",
        "repair_backups",
    }
)


hard_excluded_path_patterns = (
    "source/sdump-*/**",
    "savant-sdump-output/**",
    "exports/**",
    "relics/**",
    "s3_downloads/**",
    "vault/wip/backups/**",
    "vault/wip/receipts/**",
    "vault/kindred-preview/**",
    "vault/web_chats/**",
    "recovery/sqlite-corruption-*/**",
    "state/earmark-projection/**",
    "runtime/recovery/**",
    "**/generated-audit/**",
    "**/generated-audit-*/**",
    "**/generated-dry-run*/**",
)


hard_excluded_suffix_patterns = (
    "*.save",
    "*.bak",
    "*.old",
    "*.orig",
    "*.rej",
    "*.previous",
    "*.backup",
    "*.snapshot",
    "*.copy",
    "*.tmp",
    "*.temp",
    "*.log",
    "*.wal",
    "*.shm",
)


def sha256_file(
    path: Path,
    read_size: int = chunk_size,
) -> str:
    digest = hashlib.sha256()

    with path.open(
        "rb"
    ) as handle:
        while True:
            chunk = handle.read(
                read_size
            )

            if not chunk:
                break

            digest.update(
                chunk
            )

    return digest.hexdigest()


def output_path(
    target: Path,
) -> Path:
    stamp = datetime.now(
        timezone.utc
    ).strftime(
        "%Y%m%dT%H%M%S%fZ"
    ).lower()

    root = (
        target
        / "source"
        / f"sdump-{stamp}"
    )

    root.mkdir(
        parents=True,
        exist_ok=False,
    )

    return (
        root
        / (
            f"sdump_{target.name}_"
            f"{stamp}.txt.gz"
        )
    )


def relative_under_target(
    source_path: str,
    target: Path,
) -> str | None:
    source = Path(
        source_path
    )

    if source.is_absolute():
        try:
            return (
                source
                .resolve(
                    strict=False
                )
                .relative_to(
                    target
                )
                .as_posix()
            )

        except ValueError:
            return None

    normalized = Path(
        source_path
    )

    if (
        normalized.is_absolute()
        or ".." in normalized.parts
    ):
        return None

    return normalized.as_posix()


def normalized_relative(
    relative: str,
) -> str:
    return (
        relative
        .replace(
            "\\",
            "/",
        )
        .lstrip(
            "/"
        )
    )


def path_has_hard_excluded_directory(
    relative: str,
) -> bool:
    parts = tuple(
        part.casefold()
        for part in Path(
            relative
        ).parts[:-1]
    )

    return any(
        part
        in hard_excluded_directory_names
        for part in parts
    )


def path_matches_hard_exclusion(
    relative: str,
) -> bool:
    normalized = normalized_relative(
        relative
    )

    lowered = normalized.casefold()

    if path_has_hard_excluded_directory(
        normalized
    ):
        return True

    for pattern in (
        hard_excluded_path_patterns
    ):
        if fnmatch.fnmatch(
            lowered,
            pattern.casefold(),
        ):
            return True

    filename = Path(
        lowered
    ).name

    for pattern in (
        hard_excluded_suffix_patterns
    ):
        if fnmatch.fnmatch(
            filename,
            pattern.casefold(),
        ):
            return True

    return False


def secret_file(
    relative: str,
    profile: Any,
) -> bool:
    normalized = normalized_relative(
        relative
    )

    filename = Path(
        normalized
    ).name.casefold()

    lowered = normalized.casefold()

    for pattern in (
        profile.secret_file_patterns
    ):
        candidate = (
            pattern.casefold()
        )

        if (
            fnmatch.fnmatch(
                filename,
                candidate,
            )
            or fnmatch.fnmatch(
                lowered,
                candidate,
            )
        ):
            return True

    return False


def recognized_program_source(
    path: Path,
    profile: Any,
    mode: int,
) -> bool:
    filename = (
        path.name.casefold()
    )

    suffix = (
        path.suffix.casefold()
    )

    if (
        filename
        in profile.include_filenames
    ):
        return True

    if (
        suffix
        in profile.include_extensions
    ):
        return True

    return bool(
        mode
        & stat.S_IXUSR
    )


def source_required(
    relative: str,
    path: Path,
    profile: Any,
    mode: int,
) -> bool:
    if path_matches_hard_exclusion(
        relative
    ):
        return False

    if secret_file(
        relative,
        profile,
    ):
        return False

    if (
        path.name.casefold()
        in profile.exclude_file_names
    ):
        return False

    if (
        path.suffix.casefold()
        in profile.exclude_extensions
        and path.name.casefold()
        not in profile.include_filenames
    ):
        return False

    return recognized_program_source(
        path,
        profile,
        mode,
    )


def write_json_line(
    handle: Any,
    value: dict[str, Any],
    digest: Any | None = None,
) -> int:
    rendered = (
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

    handle.write(
        rendered
    )

    encoded = rendered.encode(
        "utf-8"
    )

    if digest is not None:
        digest.update(
            encoded
        )

    return len(
        encoded
    )


def write_text(
    handle: Any,
    value: str,
    digest: Any | None = None,
) -> int:
    handle.write(
        value
    )

    encoded = value.encode(
        "utf-8"
    )

    if digest is not None:
        digest.update(
            encoded
        )

    return len(
        encoded
    )


def write_file_record(
    handle: Any,
    path: Path,
    relative: str,
    record: dict[str, Any],
    payload: dict[str, Any],
    file_stat: os.stat_result,
    actual_sha: str,
    artifact_digest: Any,
) -> int:
    metadata = {
        "path":
            relative,
        "source_revision_id":
            record.get(
                "id"
            ),
        "sha256":
            actual_sha,
        "size":
            file_stat.st_size,
        "mode":
            oct(
                stat.S_IMODE(
                    file_stat.st_mode
                )
            ),
        "language":
            language(
                path
            ),
        "observed_at":
            record.get(
                "observed_at"
            ),
        "datrix_payload_sha256":
            payload.get(
                "sha256"
            ),
    }

    rendered_bytes = 0

    rendered_bytes += write_text(
        handle,
        "=== file ===\n",
        artifact_digest,
    )

    rendered_bytes += write_json_line(
        handle,
        metadata,
        artifact_digest,
    )

    rendered_bytes += write_text(
        handle,
        "=== content ===\n",
        artifact_digest,
    )

    with path.open(
        "r",
        encoding="utf-8",
        errors="replace",
        newline=None,
    ) as source:
        while True:
            chunk = source.read(
                chunk_size
            )

            if not chunk:
                break

            handle.write(
                chunk
            )

            encoded = chunk.encode(
                "utf-8"
            )

            artifact_digest.update(
                encoded
            )

            rendered_bytes += len(
                encoded
            )

    rendered_bytes += write_text(
        handle,
        (
            "\n=== /content ===\n"
            "=== /file ===\n\n"
        ),
        artifact_digest,
    )

    return rendered_bytes


def stream_dump(
    target_raw: str,
    profile_name: str = default_profile,
) -> Path:
    target = (
        Path(
            target_raw
        )
        .expanduser()
        .resolve(
            strict=True
        )
    )

    if not target.is_dir():
        raise StreamDumpError(
            "streaming sdump requires "
            "a directory target"
        )

    profile = load_profile(
        profile_name
    )

    source_datrix = datrix()

    health = source_datrix.health()

    if (
        health.get(
            "status"
        )
        != "ok"
    ):
        raise StreamDumpError(
            "straub source datrix "
            "health is not ok"
        )

    current = current_from_datrix(
        source_datrix
    )

    output = output_path(
        target
    )

    included_files = 0
    included_source_bytes = 0
    rendered_bytes = 0

    required_source_files = 0
    required_source_bytes = 0

    excluded_non_source = 0
    excluded_non_source_bytes = 0

    excluded_hard = 0
    excluded_hard_bytes = 0

    excluded_secret = 0
    excluded_secret_bytes = 0

    outside_target = 0
    invalid_payload = 0
    deleted_records = 0
    non_regular_files = 0
    stale_files = 0
    changed_files = 0
    oversized_required_files = 0
    required_not_written = 0

    artifact_digest = (
        hashlib.sha256()
    )

    with gzip.open(
        output,
        mode="wt",
        encoding="utf-8",
        newline="\n",
        compresslevel=gzip_level,
    ) as handle:
        write_text(
            handle,
            "=== sdump manifest ===\n",
            artifact_digest,
        )

        write_json_line(
            handle,
            {
                "schema":
                    schema,
                "generated_at":
                    now_iso(),
                "target":
                    str(
                        target
                    ),
                "profile":
                    profile.id,
                "semantic_source":
                    "straub-source-datrix",
                "semantic_source_is_sqlite":
                    False,
                "sqlite_consulted":
                    False,
                "bounded_memory":
                    True,
                "strict":
                    True,
                "gzip":
                    True,
                "gzip_level":
                    gzip_level,
                "source_datrix_health":
                    "ok",
                "source_datrix_current_revisions":
                    len(
                        current
                    ),
                "source_admission":
                    (
                        "recognized-program-source-"
                        "before-path-policy"
                    ),
                "source_completeness_invariant":
                    True,
                "filesystem_presence_establishes_authority":
                    False,
                "authority_effect":
                    "none",
            },
            artifact_digest,
        )

        write_text(
            handle,
            (
                "=== /sdump manifest ===\n\n"
            ),
            artifact_digest,
        )

        for (
            source_path,
            record,
        ) in sorted(
            current.items(),
            key=lambda item: (
                item[0].casefold(),
                item[0],
            ),
        ):
            relative = (
                relative_under_target(
                    source_path,
                    target,
                )
            )

            if relative is None:
                outside_target += 1
                continue

            payload = record.get(
                "payload"
            )

            if not isinstance(
                payload,
                dict,
            ):
                invalid_payload += 1
                continue

            if payload.get(
                "deleted",
                False,
            ):
                deleted_records += 1
                continue

            path = (
                target
                / relative
            )

            payload_size = (
                payload.get(
                    "size"
                )
            )

            known_size = (
                payload_size
                if isinstance(
                    payload_size,
                    int,
                )
                else 0
            )

            if path_matches_hard_exclusion(
                relative
            ):
                excluded_hard += 1
                excluded_hard_bytes += (
                    known_size
                )
                continue

            if secret_file(
                relative,
                profile,
            ):
                excluded_secret += 1
                excluded_secret_bytes += (
                    known_size
                )
                continue

            try:
                file_stat = (
                    path.stat()
                )

            except OSError:
                stale_files += 1
                continue

            if not stat.S_ISREG(
                file_stat.st_mode
            ):
                non_regular_files += 1
                continue

            required = source_required(
                relative=relative,
                path=path,
                profile=profile,
                mode=file_stat.st_mode,
            )

            if not required:
                excluded_non_source += 1
                excluded_non_source_bytes += (
                    file_stat.st_size
                )
                continue

            required_source_files += 1
            required_source_bytes += (
                file_stat.st_size
            )

            if (
                file_stat.st_size
                > profile.max_file_bytes
            ):
                oversized_required_files += 1
                required_not_written += 1
                continue

            expected_sha = str(
                payload.get(
                    "sha256"
                )
                or ""
            )

            actual_sha = sha256_file(
                path
            )

            if (
                not expected_sha
                or actual_sha
                != expected_sha
            ):
                changed_files += 1
                required_not_written += 1
                continue

            rendered_bytes += (
                write_file_record(
                    handle=handle,
                    path=path,
                    relative=relative,
                    record=record,
                    payload=payload,
                    file_stat=file_stat,
                    actual_sha=actual_sha,
                    artifact_digest=artifact_digest,
                )
            )

            included_files += 1
            included_source_bytes += (
                file_stat.st_size
            )

        if (
            included_files
            != required_source_files
        ):
            required_not_written = max(
                required_not_written,
                (
                    required_source_files
                    - included_files
                ),
            )

        summary = {
            "schema":
                schema,
            "required_source_files":
                required_source_files,
            "required_source_bytes":
                required_source_bytes,
            "included_files":
                included_files,
            "included_source_bytes":
                included_source_bytes,
            "rendered_bytes":
                rendered_bytes,
            "required_not_written":
                required_not_written,
            "excluded_non_source":
                excluded_non_source,
            "excluded_non_source_bytes":
                excluded_non_source_bytes,
            "excluded_hard":
                excluded_hard,
            "excluded_hard_bytes":
                excluded_hard_bytes,
            "excluded_secret":
                excluded_secret,
            "excluded_secret_bytes":
                excluded_secret_bytes,
            "outside_target":
                outside_target,
            "invalid_payload":
                invalid_payload,
            "deleted_records":
                deleted_records,
            "non_regular_files":
                non_regular_files,
            "stale_files":
                stale_files,
            "changed_since_datrix_observation":
                changed_files,
            "oversized_required_files":
                oversized_required_files,
            "source_completeness":
                (
                    "complete"
                    if (
                        required_not_written
                        == 0
                        and included_files
                        == required_source_files
                    )
                    else "failed"
                ),
            "content_stream_sha256":
                artifact_digest.hexdigest(),
            "authority_effect":
                "none",
        }

        write_text(
            handle,
            "=== sdump summary ===\n",
        )

        write_json_line(
            handle,
            summary,
        )

        write_text(
            handle,
            "=== /sdump summary ===\n",
        )

    failures: list[str] = []

    if stale_files:
        failures.append(
            f"{stale_files} stale datrix paths"
        )

    if changed_files:
        failures.append(
            (
                f"{changed_files} required source "
                "files changed since datrix observation"
            )
        )

    if oversized_required_files:
        failures.append(
            (
                f"{oversized_required_files} required "
                "source files exceeded max_file_bytes"
            )
        )

    if required_not_written:
        failures.append(
            (
                f"{required_not_written} required "
                "source files were not written"
            )
        )

    if (
        included_files
        != required_source_files
    ):
        failures.append(
            (
                "included source count does not "
                "equal required source count"
            )
        )

    if failures:
        raise StreamDumpError(
            "strict source completeness failed: "
            + "; ".join(
                failures
            )
            + "; partial artifact retained at "
            + str(
                output
            )
        )

    return output


def main(
    argv: list[str] | None = None,
) -> int:
    arguments = list(
        sys.argv[1:]
        if argv is None
        else argv
    )

    if len(
        arguments
    ) != 1:
        raise StreamDumpError(
            "usage: sdump TARGET"
        )

    artifact = stream_dump(
        arguments[0]
    )

    print(
        f"output: {artifact}"
    )

    print(
        (
            "compressed_size: "
            f"{artifact.stat().st_size}"
        )
    )

    print(
        (
            "sha256: "
            + sha256_file(
                artifact
            )
        )
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
