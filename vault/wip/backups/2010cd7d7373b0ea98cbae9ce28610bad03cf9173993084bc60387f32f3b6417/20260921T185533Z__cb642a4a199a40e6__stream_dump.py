from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
import stat
import sys
from typing import Any

from .ignore import IgnoreMatcher
from .profiles import load_profile
from .scan import language
from .util import now_iso

from straub.source_datrix import (
    current_from_datrix,
    datrix,
)


schema = "savant.sdump.stream.v1"
default_profile = "code"
chunk_size = 1024 * 1024


class StreamDumpError(RuntimeError):
    pass


def sha256_file(
    path: Path,
    read_size: int = chunk_size,
) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as handle:
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
            f"{stamp}.txt"
        )
    )


def write_json_line(
    handle: Any,
    value: dict[str, Any],
) -> None:
    handle.write(
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(
                ",",
                ":",
            ),
        )
    )

    handle.write(
        "\n"
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


def build_matcher(
    target: Path,
    profile: Any,
) -> IgnoreMatcher:
    return IgnoreMatcher(
        profile=profile,
        target_root=target,
        absolute_excluded_roots=(
            target / "source",
            target / "exports",
            target / "audit",
            target / "_reports",
            target / "repair_backups",
            target / "relics",
            target
            / "vault"
            / "kindred-preview",
        ),
        include_hidden=False,
        include_secrets=False,
        extra_patterns=(),
        respect_gitignore=False,
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

    marker = (
        "=== file ===\n"
        + json.dumps(
            metadata,
            ensure_ascii=False,
            sort_keys=True,
            separators=(
                ",",
                ":",
            ),
        )
        + "\n"
        + "=== content ===\n"
    )

    handle.write(
        marker
    )

    artifact_digest.update(
        marker.encode(
            "utf-8"
        )
    )

    rendered_bytes = 0

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

    ending = (
        "\n=== /content ===\n"
        "=== /file ===\n\n"
    )

    handle.write(
        ending
    )

    artifact_digest.update(
        ending.encode(
            "utf-8"
        )
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
            "streaming sdump currently "
            "requires a directory target"
        )

    profile = load_profile(
        profile_name
    )

    matcher = build_matcher(
        target,
        profile,
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
    rendered_content_bytes = 0

    excluded_by_profile = 0
    excluded_by_profile_bytes = 0

    outside_target = 0
    invalid_payload = 0
    deleted_records = 0
    non_regular_files = 0
    oversized_files = 0
    oversized_bytes = 0
    stale_files = 0
    changed_files = 0

    artifact_digest = hashlib.sha256()

    with output.open(
        "w",
        encoding="utf-8",
        newline="\n",
    ) as handle:
        header = {
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
            "filesystem_presence_establishes_authority":
                False,
            "sqlite_consulted":
                False,
            "bounded_memory":
                True,
            "strict":
                True,
            "source_content_duplicated":
                False,
            "source_datrix_health":
                "ok",
            "source_datrix_current_revisions":
                len(
                    current
                ),
            "authority_effect":
                "none",
        }

        handle.write(
            "=== sdump manifest ===\n"
        )

        write_json_line(
            handle,
            header,
        )

        handle.write(
            "=== /sdump manifest ===\n\n"
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
            relative = relative_under_target(
                source_path,
                target,
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

            reason = matcher.skip_reason(
                path,
                relative,
                False,
            )

            if reason is not None:
                excluded_by_profile += 1

                payload_size = payload.get(
                    "size"
                )

                if isinstance(
                    payload_size,
                    int,
                ):
                    excluded_by_profile_bytes += (
                        payload_size
                    )

                continue

            try:
                file_stat = path.stat()

            except OSError:
                stale_files += 1
                continue

            if not stat.S_ISREG(
                file_stat.st_mode
            ):
                non_regular_files += 1
                continue

            if (
                file_stat.st_size
                > profile.max_file_bytes
            ):
                oversized_files += 1
                oversized_bytes += (
                    file_stat.st_size
                )
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
                expected_sha
                and actual_sha
                != expected_sha
            ):
                changed_files += 1
                continue

            file_rendered_bytes = (
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

            rendered_content_bytes += (
                file_rendered_bytes
            )

        footer = {
            "schema":
                schema,
            "included_files":
                included_files,
            "included_source_bytes":
                included_source_bytes,
            "rendered_content_bytes":
                rendered_content_bytes,
            "excluded_by_profile":
                excluded_by_profile,
            "excluded_by_profile_bytes":
                excluded_by_profile_bytes,
            "outside_target":
                outside_target,
            "invalid_payload":
                invalid_payload,
            "deleted_records":
                deleted_records,
            "non_regular_files":
                non_regular_files,
            "oversized_files":
                oversized_files,
            "oversized_bytes":
                oversized_bytes,
            "stale_files":
                stale_files,
            "changed_since_datrix_observation":
                changed_files,
            "content_stream_sha256":
                artifact_digest.hexdigest(),
            "authority_effect":
                "none",
        }

        handle.write(
            "=== sdump summary ===\n"
        )

        write_json_line(
            handle,
            footer,
        )

        handle.write(
            "=== /sdump summary ===\n"
        )

        handle.flush()

        os.fsync(
            handle.fileno()
        )

    if stale_files:
        raise StreamDumpError(
            "strict streaming dump found "
            f"{stale_files} datrix paths "
            "missing from the filesystem; "
            f"partial artifact retained at {output}"
        )

    if changed_files:
        raise StreamDumpError(
            "strict streaming dump found "
            f"{changed_files} files changed "
            "since source datrix observation; "
            f"partial artifact retained at {output}"
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
        f"size: {artifact.stat().st_size}"
    )

    print(
        "sha256: "
        + sha256_file(
            artifact
        )
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
