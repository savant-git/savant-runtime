from __future__ import annotations

import hashlib
import json
import os
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


class StreamDumpError(RuntimeError):
    pass


def sha256_file(
    path: Path,
    chunk_size: int = 1024 * 1024,
) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as handle:
        while True:
            chunk = handle.read(
                chunk_size
            )

            if not chunk:
                break

            digest.update(
                chunk
            )

    return digest.hexdigest()


def authoritative_candidate(
    path: Path,
    profile: Any,
    mode: int,
) -> bool:
    name = path.name.casefold()
    suffix = path.suffix.casefold()

    if (
        name in profile.include_filenames
        or suffix in profile.include_extensions
    ):
        return True

    return bool(
        mode
        & stat.S_IXUSR
    )


def output_path(
    target: Path,
) -> Path:
    from datetime import (
        datetime,
        timezone,
    )

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

    return source.as_posix()


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

    matcher = IgnoreMatcher(
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
    included_bytes = 0
    rendered_bytes = 0
    skipped_files = 0
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
            "sqlite_consulted":
                False,
            "bounded_memory":
                True,
            "strict":
                True,
            "source_datrix_health":
                "ok",
            "source_datrix_current_revisions":
                len(
                    current
                ),
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
                skipped_files += 1
                continue

            path = (
                target
                / relative
            )

            payload = record.get(
                "payload"
            )

            if not isinstance(
                payload,
                dict,
            ):
                skipped_files += 1
                continue

            if payload.get(
                "deleted",
                False,
            ):
                skipped_files += 1
                continue

            reason = matcher.skip_reason(
                path,
                relative,
                False,
            )

            if reason is not None:
                skipped_files += 1
                continue

            try:
                file_stat = path.stat()

            except OSError:
                stale_files += 1
                continue

            if not stat.S_ISREG(
                file_stat.st_mode
            ):
                skipped_files += 1
                continue

            if not authoritative_candidate(
                path,
                profile,
                file_stat.st_mode,
            ):
                skipped_files += 1
                continue

            if (
                file_stat.st_size
                > profile.max_file_bytes
            ):
                skipped_files += 1
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

            file_rendered = 0

            with path.open(
                "r",
                encoding="utf-8",
                errors="replace",
                newline=None,
            ) as source:
                while True:
                    chunk = source.read(
                        1024 * 1024
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

                    file_rendered += len(
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

            included_files += 1
            included_bytes += (
                file_stat.st_size
            )
            rendered_bytes += (
                file_rendered
            )

        footer = {
            "schema":
                schema,
            "included_files":
                included_files,
            "included_source_bytes":
                included_bytes,
            "rendered_content_bytes":
                rendered_bytes,
            "skipped_files":
                skipped_files,
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
            "usage: sdump-stream TARGET"
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
