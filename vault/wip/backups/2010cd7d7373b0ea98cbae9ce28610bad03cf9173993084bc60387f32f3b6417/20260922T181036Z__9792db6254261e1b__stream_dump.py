from __future__ import annotations

import gzip
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
import shutil
import stat
import subprocess
import sys
import tempfile
from types import SimpleNamespace
from typing import Any, Iterable

from .profiles import load_profile
from .scan import (
    discover,
    language,
    normalized_targets,
)

from straub.source_datrix import (
    current_from_datrix,
    datrix,
)


schema = "savant.sdump.stream.v3"

default_profile = "code"

chunk_size = 1024 * 1024

gzip_level = 9

s3_bucket = "savant-ai-cluster"

github_owner = "savant-git"

github_repository = "savant-runtime"

github_remote = (
    "https://github.com/"
    f"{github_owner}/"
    f"{github_repository}.git"
)

default_env_path = Path(
    "/root/.env"
)


class StreamDumpError(
    RuntimeError
):
    pass


def canonical_json(
    value: Any,
) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(
            ",",
            ":",
        ),
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


def run(
    command: list[str],
    *,
    cwd: Path | None = None,
    env: dict[str, str] | None = None,
    capture: bool = True,
) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        command,
        cwd=(
            str(cwd)
            if cwd is not None
            else None
        ),
        env=env,
        text=True,
        stdout=(
            subprocess.PIPE
            if capture
            else None
        ),
        stderr=(
            subprocess.PIPE
            if capture
            else None
        ),
        check=False,
    )

    if result.returncode != 0:
        stdout = (
            result.stdout.strip()
            if result.stdout
            else ""
        )

        stderr = (
            result.stderr.strip()
            if result.stderr
            else ""
        )

        detail = (
            stderr
            or stdout
            or (
                "process exited "
                f"{result.returncode}"
            )
        )

        raise StreamDumpError(
            f"command failed: "
            f"{command[0]}: "
            f"{detail}"
        )

    return result


def require_executable(
    name: str,
) -> str:
    executable = shutil.which(
        name
    )

    if executable is None:
        raise StreamDumpError(
            "required executable "
            f"not found: {name}"
        )

    return executable


def load_env_file(
    path: Path = default_env_path,
) -> dict[str, str]:
    if not path.is_file():
        raise StreamDumpError(
            f"environment file "
            f"not found: {path}"
        )

    values: dict[
        str,
        str,
    ] = {}

    with path.open(
        "r",
        encoding="utf-8",
        errors="strict",
    ) as handle:
        for raw_line in handle:
            line = raw_line.strip()

            if (
                not line
                or line.startswith(
                    "#"
                )
            ):
                continue

            if line.startswith(
                "export "
            ):
                line = line[
                    len(
                        "export "
                    ):
                ].lstrip()

            key, separator, value = (
                line.partition(
                    "="
                )
            )

            if not separator:
                continue

            key = key.strip()

            if not key:
                continue

            value = value.strip()

            if (
                len(value) >= 2
                and value[0]
                == value[-1]
                and value[0]
                in {
                    "'",
                    '"',
                }
            ):
                value = value[
                    1:-1
                ]

            values[
                key
            ] = value

    return values

def now_iso() -> str:
    return (
        datetime.now(
            timezone.utc
        )
        .isoformat(
            timespec="microseconds"
        )
        .replace(
            "+00:00",
            "Z",
        )
    )

def publication_environment(
    env_path: Path = default_env_path,
) -> dict[str, str]:
    environment = dict(
        os.environ
    )

    environment.update(
        load_env_file(
            env_path
        )
    )

    required = (
        "AWS_ACCESS_KEY_ID",
        "AWS_SECRET_ACCESS_KEY",
    )

    missing = [
        key
        for key in required
        if not environment.get(
            key
        )
    ]

    if missing:
        raise StreamDumpError(
            "missing S3 credential "
            "environment variables in "
            f"{env_path}: "
            + ", ".join(
                missing
            )
        )

    return environment


def output_path(
    target: Path,
) -> Path:
    stamp = datetime.now(
        timezone.utc
    ).strftime(
        "%Y%m%dT%H%M%S%fZ"
    ).lower()

    output_root = (
        target
        / "source"
        / f"sdump-{stamp}"
    )

    output_root.mkdir(
        parents=True,
        exist_ok=False,
    )

    return (
        output_root
        / (
            f"sdump_{target.name}_"
            f"{stamp}.txt.gz"
        )
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


def write_json_line(
    handle: Any,
    value: dict[str, Any],
    digest: Any | None = None,
) -> int:
    return write_text(
        handle,
        canonical_json(
            value
        )
        + "\n",
        digest,
    )


def datrix_relative_index(
    current: dict[
        str,
        dict[str, Any],
    ],
    target: Path,
) -> dict[
    str,
    dict[str, Any],
]:
    result: dict[
        str,
        dict[str, Any],
    ] = {}

    for (
        source_path,
        record,
    ) in current.items():
        source = Path(
            source_path
        )

        if source.is_absolute():
            try:
                relative = (
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
                continue

        else:
            if (
                ".."
                in source.parts
            ):
                continue

            relative = (
                source.as_posix()
            )

        payload = record.get(
            "payload"
        )

        if not isinstance(
            payload,
            dict,
        ):
            continue

        if payload.get(
            "deleted",
            False,
        ):
            continue

        existing = result.get(
            relative
        )

        if existing is not None:
            existing_id = str(
                existing.get(
                    "id"
                )
                or ""
            )

            record_id = str(
                record.get(
                    "id"
                )
                or ""
            )

            if existing_id != record_id:
                raise StreamDumpError(
                    "multiple current Datrix "
                    "records resolve to "
                    f"{relative}"
                )

        result[
            relative
        ] = record

    return result


def discover_authoritative_source(
    target: Path,
    profile: Any,
) -> tuple[
    list[Any],
    dict[str, Any],
]:
    (
        candidates,
        skipped,
        failures,
        symlinks,
        stats,
    ) = discover(
        targets=normalized_targets(
            [
                str(
                    target
                )
            ]
        ),
        profile=profile,
        absolute_excluded_roots=(),
        include_hidden=False,
        include_secrets=False,
        extra_patterns=(),
        respect_gitignore=None,
    )

    if failures:
        sample = [
            {
                "path":
                    item.path,
                "reason":
                    item.reason,
            }
            for item
            in failures[
                :20
            ]
        ]

        raise StreamDumpError(
            "authoritative profile "
            "discovery failed: "
            + canonical_json(
                sample
            )
        )

    candidates = sorted(
        candidates,
        key=lambda candidate: (
            candidate
            .relative_path
            .casefold(),
            candidate.relative_path,
        ),
    )

    metadata = {
        "candidate_count":
            len(
                candidates
            ),
        "candidate_bytes":
            sum(
                candidate.size
                for candidate
                in candidates
            ),
        "skipped_count":
            len(
                skipped
            ),
        "symlink_count":
            len(
                symlinks
            ),
        "files_seen":
            stats.files_seen,
    }

    return (
        candidates,
        metadata,
    )


def freeze_candidate(
    *,
    candidate: Any,
    snapshot_root: Path,
    datrix_index: dict[str, dict[str, Any]],
) -> tuple[Any, dict[str, Any], os.stat_result, str, bool]:
    relative = candidate.relative_path
    source = candidate.absolute_path
    destination = snapshot_root / relative
    destination.parent.mkdir(parents=True, exist_ok=True)

    try:
        before = source.stat()
        if not stat.S_ISREG(before.st_mode):
            raise StreamDumpError(
                f"profile-admitted source is no longer regular: {relative}"
            )

        digest = hashlib.sha256()
        size = 0

        with source.open("rb") as reader, destination.open("wb") as writer:
            while True:
                block = reader.read(chunk_size)
                if not block:
                    break
                writer.write(block)
                digest.update(block)
                size += len(block)

            writer.flush()
            os.fsync(writer.fileno())

        after = source.stat()

    except OSError as error:
        raise StreamDumpError(
            f"unable to freeze profile-admitted source {relative}: {error}"
        ) from error

    if (
        before.st_dev != after.st_dev
        or before.st_ino != after.st_ino
        or before.st_size != after.st_size
        or before.st_mtime_ns != after.st_mtime_ns
        or size != before.st_size
    ):
        raise StreamDumpError(
            f"profile-admitted source changed while snapshotting: {relative}"
        )

    os.chmod(destination, stat.S_IMODE(before.st_mode))
    actual_sha = digest.hexdigest()

    record = datrix_index.get(relative)
    datrix_matches = False

    if isinstance(record, dict):
        payload = record.get("payload")
        if isinstance(payload, dict):
            datrix_matches = (
                str(payload.get("sha256") or "") == actual_sha
            )
        else:
            record = {}
    else:
        record = {}

    frozen = SimpleNamespace(
        relative_path=relative,
        absolute_path=destination,
        size=size,
    )

    return frozen, record, before, actual_sha, datrix_matches

def write_file_record(
    *,
    handle: Any,
    candidate: Any,
    record: dict[str, Any],
    file_stat: os.stat_result,
    actual_sha: str,
    artifact_digest: Any,
) -> int:
    payload = record.get("payload")
    if not isinstance(payload, dict):
        payload = {}

    relative = (
        candidate.relative_path
    )

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
                candidate.absolute_path
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

    rendered = 0

    rendered += write_text(
        handle,
        "=== file ===\n",
        artifact_digest,
    )

    rendered += write_json_line(
        handle,
        metadata,
        artifact_digest,
    )

    rendered += write_text(
        handle,
        "=== content ===\n",
        artifact_digest,
    )

    with candidate.absolute_path.open(
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

            rendered += write_text(
                handle,
                chunk,
                artifact_digest,
            )

    rendered += write_text(
        handle,
        (
            "\n=== /content ===\n"
            "=== /file ===\n\n"
        ),
        artifact_digest,
    )

    return rendered


def stream_dump(
    target_raw: str,
    profile_name: str = default_profile,
) -> tuple[Path, list[Any], dict[str, Any]]:
    target = Path(target_raw).expanduser().resolve(strict=True)

    if not target.is_dir():
        raise StreamDumpError("sdump target must be a directory")

    profile = load_profile(profile_name)
    candidates, discovery = discover_authoritative_source(target, profile)

    source_datrix = datrix()
    health = source_datrix.health()
    if health.get("status") != "ok":
        raise StreamDumpError("straub source Datrix health is not ok")

    current = current_from_datrix(source_datrix)
    datrix_index = datrix_relative_index(current, target)

    candidate_paths = {candidate.relative_path for candidate in candidates}

    output = output_path(target)
    snapshot_root = output.parent / "snapshot"
    snapshot_root.mkdir(parents=True, exist_ok=False)

    frozen: list[
        tuple[Any, dict[str, Any], os.stat_result, str, bool]
    ] = []

    try:
        for candidate in candidates:
            frozen.append(
                freeze_candidate(
                    candidate=candidate,
                    snapshot_root=snapshot_root,
                    datrix_index=datrix_index,
                )
            )
    except Exception:
        raise

    frozen_candidates = [item[0] for item in frozen]
    frozen_paths = {candidate.relative_path for candidate in frozen_candidates}

    if frozen_paths != candidate_paths:
        raise StreamDumpError(
            "profile admission and frozen source sets differ"
        )

    frozen_bytes = sum(item[2].st_size for item in frozen)
    if (
        len(frozen) != len(candidates)
        or frozen_bytes != discovery["candidate_bytes"]
    ):
        raise StreamDumpError(
            "frozen source snapshot does not equal profile admission"
        )

    datrix_matched = sum(1 for item in frozen if item[4])
    datrix_unmatched = len(frozen) - datrix_matched

    artifact_digest = hashlib.sha256()
    included_files = 0
    included_source_bytes = 0
    rendered_bytes = 0

    with gzip.open(
        output,
        mode="wt",
        encoding="utf-8",
        newline="\n",
        compresslevel=gzip_level,
    ) as handle:
        write_text(handle, "=== sdump manifest ===\n", artifact_digest)
        write_json_line(
            handle,
            {
                "schema": schema,
                "generated_at": now_iso(),
                "target": str(target),
                "profile": profile.id,
                "semantic_source": "straub-source-datrix",
                "semantic_source_is_sqlite": False,
                "sqlite_consulted": False,
                "source_admission": "authoritative-profile-discover",
                "source_admission_module": "sdump_enterprise.scan.discover",
                "source_snapshot": "immutable-transaction-local",
                "source_datrix_role": "provenance-context",
                "source_datrix_health": "ok",
                "source_datrix_current_revisions": len(current),
                "source_datrix_matching_files": datrix_matched,
                "source_datrix_nonmatching_or_missing_files": datrix_unmatched,
                "profile_admitted_files": len(candidates),
                "profile_admitted_bytes": discovery["candidate_bytes"],
                "strict": True,
                "bounded_file_streaming": True,
                "gzip": True,
                "gzip_level": gzip_level,
                "filesystem_presence_establishes_authority": False,
                "authority_effect": "none",
            },
            artifact_digest,
        )
        write_text(
            handle,
            "=== /sdump manifest ===\n\n",
            artifact_digest,
        )

        for candidate, record, file_stat, actual_sha, _ in frozen:
            rendered_bytes += write_file_record(
                handle=handle,
                candidate=candidate,
                record=record,
                file_stat=file_stat,
                actual_sha=actual_sha,
                artifact_digest=artifact_digest,
            )
            included_files += 1
            included_source_bytes += file_stat.st_size

        complete = (
            included_files == len(candidates)
            and included_source_bytes == discovery["candidate_bytes"]
            and frozen_paths == candidate_paths
        )

        summary = {
            "schema": schema,
            "profile_admitted_files": len(candidates),
            "profile_admitted_bytes": discovery["candidate_bytes"],
            "frozen_files": len(frozen),
            "frozen_source_bytes": frozen_bytes,
            "datrix_matching_files": datrix_matched,
            "datrix_nonmatching_or_missing_files": datrix_unmatched,
            "included_files": included_files,
            "included_source_bytes": included_source_bytes,
            "rendered_bytes": rendered_bytes,
            "required_not_written": len(candidates) - included_files,
            "profile_equals_frozen": candidate_paths == frozen_paths,
            "profile_equals_serialized": included_files == len(candidate_paths),
            "source_completeness": "complete" if complete else "failed",
            "content_stream_sha256": artifact_digest.hexdigest(),
            "authority_effect": "none",
        }

        write_text(handle, "=== sdump summary ===\n")
        write_json_line(handle, summary)
        write_text(handle, "=== /sdump summary ===\n")

    if not complete:
        raise StreamDumpError(
            "strict source completeness failed; partial artifact "
            f"retained at {output}"
        )

    return (
        output,
        frozen_candidates,
        {
            "target": target,
            "profile": profile,
            "discovery": discovery,
            "source_datrix_health": health,
            "snapshot_root": snapshot_root,
            "datrix_matched": datrix_matched,
            "datrix_unmatched": datrix_unmatched,
        },
    )

def s3_object_key(
    artifact: Path,
    environment: dict[str, str],
) -> str:
    prefix = (
        environment.get(
            "SDUMP_S3_PREFIX",
            "sdump",
        )
        .strip()
        .strip(
            "/"
        )
    )

    if prefix:
        return (
            f"{prefix}/"
            f"{artifact.name}"
        )

    return artifact.name


def upload_to_s3(
    artifact: Path,
    environment: dict[str, str],
) -> dict[str, str]:
    aws = require_executable(
        "aws"
    )

    key = s3_object_key(
        artifact,
        environment,
    )

    destination = (
        f"s3://{s3_bucket}/"
        f"{key}"
    )

    run(
        [
            aws,
            "s3",
            "cp",
            str(
                artifact
            ),
            destination,
            "--only-show-errors",
        ],
        env=environment,
    )

    verification = run(
        [
            aws,
            "s3api",
            "head-object",
            "--bucket",
            s3_bucket,
            "--key",
            key,
            "--query",
            "ContentLength",
            "--output",
            "text",
        ],
        env=environment,
    )

    remote_size_text = (
        verification.stdout
        .strip()
    )

    try:
        remote_size = int(
            remote_size_text
        )

    except ValueError as error:
        raise StreamDumpError(
            "S3 upload verification "
            "returned invalid size"
        ) from error

    local_size = (
        artifact.stat().st_size
    )

    if remote_size != local_size:
        raise StreamDumpError(
            "S3 upload verification "
            "size mismatch"
        )

    return {
        "bucket":
            s3_bucket,
        "key":
            key,
        "uri":
            destination,
    }


def git_identity(
    git: str,
) -> tuple[str, str]:
    name = run(
        [
            git,
            "config",
            "--global",
            "--get",
            "user.name",
        ]
    ).stdout.strip()

    email = run(
        [
            git,
            "config",
            "--global",
            "--get",
            "user.email",
        ]
    ).stdout.strip()

    if not name:
        raise StreamDumpError(
            "global git user.name "
            "is not configured"
        )

    if not email:
        raise StreamDumpError(
            "global git user.email "
            "is not configured"
        )

    return (
        name,
        email,
    )


def clean_checkout_contents(
    checkout: Path,
) -> None:
    for child in checkout.iterdir():
        if child.name == ".git":
            continue

        if child.is_dir():
            shutil.rmtree(
                child
            )

        else:
            child.unlink()


def copy_authoritative_source(
    *,
    checkout: Path,
    candidates: Iterable[Any],
) -> None:
    for candidate in candidates:
        destination = (
            checkout
            / candidate.relative_path
        )

        destination.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        shutil.copy2(
            candidate.absolute_path,
            destination,
        )


def push_source_to_github(
    *,
    candidates: list[Any],
    environment: dict[str, str],
) -> dict[str, Any]:
    git = require_executable(
        "git"
    )

    git_identity(
        git
    )

    branch = (
        environment.get(
            "SDUMP_GITHUB_BRANCH",
            "main",
        )
        .strip()
        or "main"
    )

    with tempfile.TemporaryDirectory(
        prefix="savant-sdump-git-"
    ) as temporary:
        checkout = Path(
            temporary
        ) / "repository"

        run(
            [
                git,
                "clone",
                "--branch",
                branch,
                "--single-branch",
                github_remote,
                str(
                    checkout
                ),
            ],
            env=environment,
        )

        clean_checkout_contents(
            checkout
        )

        copy_authoritative_source(
            checkout=checkout,
            candidates=candidates,
        )

        run(
            [
                git,
                "add",
                "--all",
            ],
            cwd=checkout,
            env=environment,
        )

        status = run(
            [
                git,
                "status",
                "--porcelain",
            ],
            cwd=checkout,
            env=environment,
        ).stdout

        changed = bool(
            status.strip()
        )

        if changed:
            commit_message = (
                "sdump: synchronize "
                "authoritative source"
            )

            run(
                [
                    git,
                    "commit",
                    "-m",
                    commit_message,
                ],
                cwd=checkout,
                env=environment,
            )

        run(
            [
                git,
                "push",
                "origin",
                branch,
            ],
            cwd=checkout,
            env=environment,
        )

        local_head = run(
            [
                git,
                "rev-parse",
                "HEAD",
            ],
            cwd=checkout,
            env=environment,
        ).stdout.strip()

        remote_head = run(
            [
                git,
                "ls-remote",
                "--heads",
                "origin",
                (
                    "refs/heads/"
                    + branch
                ),
            ],
            cwd=checkout,
            env=environment,
        ).stdout.strip()

        if not remote_head:
            raise StreamDumpError(
                "GitHub branch verification "
                "returned no remote head"
            )

        remote_commit = (
            remote_head.split()[0]
        )

        if remote_commit != local_head:
            raise StreamDumpError(
                "GitHub push verification "
                "head mismatch"
            )

        return {
            "repository":
                (
                    f"{github_owner}/"
                    f"{github_repository}"
                ),
            "branch":
                branch,
            "commit":
                local_head,
            "changed":
                changed,
            "verified":
                True,
        }


def delete_local_artifact(
    artifact: Path,
) -> None:
    artifact.unlink()

    parent = artifact.parent

    try:
        parent.rmdir()

    except OSError:
        pass

    if artifact.exists():
        raise StreamDumpError(
            "local sdump artifact "
            "could not be deleted"
        )


def publish(
    *,
    artifact: Path,
    candidates: list[Any],
    environment: dict[str, str],
    snapshot_root: Path,
) -> dict[str, Any]:
    s3_result = upload_to_s3(
        artifact,
        environment,
    )

    github_result = (
        push_source_to_github(
            candidates=candidates,
            environment=environment,
        )
    )

    shutil.rmtree(snapshot_root)

    delete_local_artifact(
        artifact
    )

    return {
        "schema":
            "savant.sdump.publish.v1",
        "s3":
            s3_result,
        "github":
            github_result,
        "local_artifact_deleted":
            True,
        "authority_effect":
            "none",
    }


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

    target_raw = (
        arguments[0]
    )

    environment = (
        publication_environment()
    )

    (
        artifact,
        candidates,
        metadata,
    ) = stream_dump(
        target_raw
    )

    artifact_sha256 = (
        sha256_file(
            artifact
        )
    )

    artifact_size = (
        artifact.stat().st_size
    )

    try:
        publication = publish(
            artifact=artifact,
            candidates=candidates,
            environment=environment,
            snapshot_root=metadata["snapshot_root"],
        )

    except Exception as error:
        raise StreamDumpError(
            "publication failed; "
            "local sdump retained at "
            f"{artifact}: {error}"
        ) from error

    result = {
        "schema":
            "savant.sdump.command.v3",
        "status":
            "ok",
        "target":
            str(
                metadata[
                    "target"
                ]
            ),
        "profile":
            metadata[
                "profile"
            ].id,
        "source_files":
            len(
                candidates
            ),
        "source_bytes":
            metadata[
                "discovery"
            ][
                "candidate_bytes"
            ],
        "artifact_sha256":
            artifact_sha256,
        "artifact_compressed_bytes":
            artifact_size,
        "s3":
            publication[
                "s3"
            ],
        "github":
            publication[
                "github"
            ],
        "local_artifact_deleted":
            publication[
                "local_artifact_deleted"
            ],
        "authority_effect":
            "none",
    }

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
