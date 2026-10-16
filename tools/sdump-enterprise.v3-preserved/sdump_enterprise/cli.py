from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
from typing import Any

from . import __version__
from .model import Profile, Projection, UploadResult
from .profiles import ProfileError, list_profiles, load_profile
from .receipt import write_receipt
from .render import compress_zstd, write_bundle
from .scan import ScanError, build_projection, discover, normalized_targets
from .upload import UploadError, upload_verified
from .util import (
    exclusive_lock,
    git_info,
    host_metadata,
    human_bytes,
    load_environment,
    now_iso,
    now_stamp,
    runtime_root,
    safe_slug,
    sha256_file,
    stable_hash,
)


SCHEMA = "savant.sdump.bundle.v3"


class SdumpError(RuntimeError):
    pass


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="sdump",
        description="Create a compact, deterministic, deduplicated, secret-safe source and canon projection.",
    )
    parser.add_argument("--version", action="version", version=f"sdump {__version__}")
    subparsers = parser.add_subparsers(dest="command")

    def add_dump_arguments(command: argparse.ArgumentParser) -> None:
        command.add_argument("targets", nargs="+")
        command.add_argument("--profile", default="compact")
        command.add_argument("--include-hidden", action="store_true")
        command.add_argument("--include-secrets", action="store_true")
        command.add_argument("--respect-gitignore", dest="respect_gitignore", action="store_true", default=None)
        command.add_argument("--no-respect-gitignore", dest="respect_gitignore", action="store_false")
        command.add_argument("--exclude", action="append", default=[])
        command.add_argument("--max-file-mb", type=float)
        command.add_argument("--max-total-mb", type=float)
        command.add_argument("--max-files", type=int)
        command.add_argument("--workers", type=int, default=max(2, min(16, (os.cpu_count() or 2) * 2)))
        command.add_argument("--output-dir")
        command.add_argument("--no-upload", action="store_true")
        command.add_argument("--keep-local", action="store_true")
        command.add_argument("--delete-after-upload", dest="delete_after_upload", action="store_true", default=True)
        command.add_argument("--no-delete-after-upload", dest="delete_after_upload", action="store_false")
        command.add_argument("--s3-prefix")
        command.add_argument("--upload-concurrency", type=int, default=4)
        command.add_argument("--compress", choices=("none", "zstd"), default="none")
        command.add_argument("--zstd-level", type=int, default=10)
        command.add_argument("--pretty-manifest", action="store_true")
        command.add_argument("--strict", action="store_true", default=True)
        command.add_argument("--no-strict", dest="strict", action="store_false")
        command.add_argument("--json-summary", action="store_true")

    dump_parser = subparsers.add_parser(
        "dump",
        help="create, upload, verify, and optionally purge a dump",
    )
    add_dump_arguments(dump_parser)

    plan_parser = subparsers.add_parser(
        "plan",
        help="scan and report without creating or uploading a dump",
    )
    add_dump_arguments(plan_parser)
    plan_parser.set_defaults(
        no_upload=True,
        keep_local=True,
    )

    subparsers.add_parser(
        "profiles",
        help="list installed profiles",
    )
    subparsers.add_parser(
        "self-test",
        help="run the installed regression tests",
    )

    return parser


def _backward_compatible_argv(argv: list[str]) -> list[str]:
    commands = {
        "dump",
        "plan",
        "profiles",
        "self-test",
    }

    if not argv:
        return argv

    if (
        argv[0] in commands
        or argv[0].startswith("-")
    ):
        return argv

    return [
        "dump",
        *argv,
    ]


def _profile_with_overrides(
    profile: Profile,
    args: argparse.Namespace,
) -> Profile:
    from dataclasses import replace

    updates: dict[str, Any] = {}

    if args.max_file_mb is not None:
        if args.max_file_mb <= 0:
            raise SdumpError(
                "--max-file-mb must be positive"
            )

        updates[
            "max_file_bytes"
        ] = int(
            args.max_file_mb
            * 1024
            * 1024
        )

    if args.max_total_mb is not None:
        if args.max_total_mb <= 0:
            raise SdumpError(
                "--max-total-mb must be positive"
            )

        updates[
            "max_total_content_bytes"
        ] = int(
            args.max_total_mb
            * 1024
            * 1024
        )

    if args.max_files is not None:
        if args.max_files <= 0:
            raise SdumpError(
                "--max-files must be positive"
            )

        updates[
            "max_files"
        ] = args.max_files

    return replace(
        profile,
        **updates,
    )


def _runtime_generated_roots(
    runtime: Path,
    output_root: Path,
) -> tuple[Path, ...]:
    return (
        output_root,
        runtime / "source",
        runtime / "exports",
        runtime / "audit",
        runtime / "_reports",
        runtime / "repair_backups",
        runtime / "relics",
        runtime / "vault" / "kindred-preview",
    )


def _target_name(
    targets: list[Path],
) -> str:
    return (
        safe_slug(
            targets[0].name
        )
        if len(targets) == 1
        else "multi"
    )


def _output_timestamp() -> str:
    return datetime.now(
        timezone.utc
    ).strftime(
        "%Y%m%dT%H%M%S%fZ"
    ).lower()


def _manifest(
    profile: Profile,
    targets: list[Path],
    projection: Projection,
    output_name: str,
    registry_hash: str | None,
    diagnostics_limit: int = 50,
) -> dict[str, Any]:
    languages = Counter(
        record.language
        for record
        in projection.records
        if record.included
    )

    categories = Counter(
        record.category
        for record
        in projection.records
        if record.included
    )

    skipped_reasons = Counter(
        item.reason
        for item
        in projection.skipped
    )

    failure_reasons = Counter(
        item.reason
        for item
        in projection.failures
    )

    git_records: list[
        dict[str, Any]
    ] = []

    for target in targets:
        record = git_info(
            target
        )

        if (
            record
            and record
            not in git_records
        ):
            git_records.append(
                record
            )

    stable_profile = {
        "id":
            profile.id,
        "description":
            profile.description,
        "max_file_bytes":
            profile.max_file_bytes,
        "max_total_content_bytes":
            profile.max_total_content_bytes,
        "max_files":
            profile.max_files,
        "respect_gitignore":
            profile.respect_gitignore,
        "redact_secrets":
            profile.redact_secrets,
        "exclude_patterns":
            list(
                profile.exclude_patterns
            ),
    }

    return {
        "schema":
            SCHEMA,
        "tool":
            "sdump-enterprise",
        "version":
            __version__,
        "projection_only":
            True,
        "authoritative_source_preserved_by_sha256":
            True,
        "generated_at":
            now_iso(),
        "snapshot_hash":
            projection.snapshot_hash,
        "output_name":
            output_name,
        "targets":
            [
                str(
                    target
                )
                for target
                in targets
            ],
        "profile":
            stable_profile,
        "profile_hash":
            stable_hash(
                stable_profile
            ),
        "composition_registry_hash":
            registry_hash,
        "host":
            host_metadata(),
        "git":
            git_records,
        "counts":
            projection.stats.to_dict(),
        "languages":
            dict(
                sorted(
                    languages.items()
                )
            ),
        "categories":
            dict(
                sorted(
                    categories.items()
                )
            ),
        "files":
            [
                record.to_dict()
                for record
                in projection.records
            ],
        "symlinks":
            projection.symlinks[
                :diagnostics_limit
            ],
        "diagnostics": {
            "skipped_by_reason":
                dict(
                    sorted(
                        skipped_reasons.items()
                    )
                ),
            "failures_by_reason":
                dict(
                    sorted(
                        failure_reasons.items()
                    )
                ),
            "skipped_examples":
                [
                    item.to_dict()
                    for item
                    in projection.skipped[
                        :diagnostics_limit
                    ]
                ],
            "failure_examples":
                [
                    item.to_dict()
                    for item
                    in projection.failures[
                        :diagnostics_limit
                    ]
                ],
            "diagnostics_limit":
                diagnostics_limit,
        },
        "deduplication": {
            "algorithm":
                "sha256",
            "content_stored_once":
                True,
            "duplicate_paths_use_duplicate_of":
                True,
            "duplicate_bytes_avoided":
                projection.stats.duplicate_bytes_avoided,
        },
        "secrets": {
            "secret_filenames_excluded_by_default":
                True,
            "content_redaction_enabled":
                profile.redact_secrets,
            "redactions":
                projection.stats.redactions,
        },
        "lineage": {
            "instances":
                "files",
            "segues":
                "duplicate_of and target_id",
            "source_hash":
                "source_sha256",
            "rendered_hash":
                "rendered_sha256",
            "content_address":
                "content_id",
        },
    }


def _registry_hash() -> str | None:
    path = (
        Path(
            __file__
        ).resolve().parent.parent
        / "registry"
        / "snippets.json"
    )

    return (
        sha256_file(
            path
        )
        if path.is_file()
        else None
    )


def _summary(
    profile: Profile,
    projection: Projection,
    artifact: Path | None,
    artifact_hash: str | None,
    upload: UploadResult | None,
    receipt: Path | None,
    local_deleted: bool,
) -> dict[str, Any]:
    return {
        "tool":
            "sdump-enterprise",
        "version":
            __version__,
        "profile":
            profile.id,
        "snapshot_hash":
            projection.snapshot_hash,
        "counts":
            projection.stats.to_dict(),
        "artifact":
            (
                str(
                    artifact
                )
                if artifact
                else None
            ),
        "artifact_size":
            (
                artifact.stat().st_size
                if (
                    artifact
                    and artifact.exists()
                )
                else (
                    upload.size
                    if upload
                    else None
                )
            ),
        "artifact_sha256":
            artifact_hash,
        "upload":
            (
                upload.to_dict()
                if upload
                else None
            ),
        "receipt":
            (
                str(
                    receipt
                )
                if receipt
                else None
            ),
        "local_deleted":
            local_deleted,
    }


def _print_summary(
    summary: dict[str, Any],
    json_summary: bool,
) -> None:
    if json_summary:
        print(
            json.dumps(
                summary,
                ensure_ascii=False,
                sort_keys=True,
            )
        )
        return

    counts = summary[
        "counts"
    ]

    print(
        f"profile: {summary['profile']}"
    )
    print(
        f"snapshot_hash: {summary['snapshot_hash']}"
    )
    print(
        f"files_seen: {counts['files_seen']}"
    )
    print(
        f"included_files: {counts['included_files']}"
    )
    print(
        f"unique_contents: {counts['unique_contents']}"
    )
    print(
        f"duplicate_files: {counts['duplicate_files']}"
    )
    print(
        (
            "rendered_bytes: "
            f"{counts['rendered_bytes']} "
            f"({human_bytes(counts['rendered_bytes'])})"
        )
    )
    print(
        (
            "duplicate_bytes_avoided: "
            f"{counts['duplicate_bytes_avoided']} "
            f"({human_bytes(counts['duplicate_bytes_avoided'])})"
        )
    )
    print(
        f"redactions: {counts['redactions']}"
    )
    print(
        f"failures: {counts['failures']}"
    )
    print(
        f"output: {summary['artifact']}"
    )
    print(
        f"size: {summary['artifact_size']}"
    )
    print(
        f"sha256: {summary['artifact_sha256']}"
    )
    print(
        (
            "s3: "
            + json.dumps(
                summary[
                    "upload"
                ],
                ensure_ascii=False,
                sort_keys=True,
            )
        )
    )
    print(
        (
            "local_deleted: "
            + str(
                summary[
                    "local_deleted"
                ]
            ).lower()
        )
    )
    print(
        f"receipt: {summary['receipt']}"
    )


def _cleanup_run_dir(
    run_dir: Path,
) -> None:
    if not run_dir.exists():
        return

    for child in list(
        run_dir.iterdir()
    ):
        if (
            child.is_dir()
            and child.name.startswith(
                ".staging"
            )
        ):
            shutil.rmtree(
                child,
                ignore_errors=True,
            )

    try:
        run_dir.rmdir()

    except OSError:
        pass


def run_dump(
    args: argparse.Namespace,
    plan_only: bool = False,
) -> int:
    runtime = runtime_root()

    runtime.mkdir(
        parents=True,
        exist_ok=True,
    )

    load_environment(
        runtime
    )

    profile = _profile_with_overrides(
        load_profile(
            args.profile
        ),
        args,
    )

    targets = normalized_targets(
        args.targets
    )

    output_root = (
        Path(
            args.output_dir
        ).expanduser().resolve(
            strict=False
        )
        if args.output_dir
        else (
            runtime
            / "source"
        ).resolve(
            strict=False
        )
    )

    receipt_root = (
        runtime
        / "vault"
        / "sdump-receipts"
    ).resolve(
        strict=False
    )

    lock_path = (
        runtime
        / "vault"
        / "sdump"
        / "sdump.lock"
    )

    output_root.mkdir(
        parents=True,
        exist_ok=True,
    )

    with exclusive_lock(
        lock_path
    ):
        temporary_parent: tempfile.TemporaryDirectory[
            str
        ] | None = None

        run_dir: Path | None = None

        run_stamp = _output_timestamp()

        if plan_only:
            temporary_parent = tempfile.TemporaryDirectory(
                prefix="sdump-plan-"
            )

            staging_root = Path(
                temporary_parent.name
            )

        else:
            run_dir = (
                output_root
                / f"sdump-{run_stamp}"
            )

            run_dir.mkdir(
                parents=True,
                exist_ok=False,
            )

            staging_root = (
                run_dir
                / ".staging"
            )

            staging_root.mkdir(
                parents=True,
                exist_ok=False,
            )

        try:
            (
                candidates,
                skipped,
                failures,
                symlinks,
                stats,
            ) = discover(
                targets=targets,
                profile=profile,
                absolute_excluded_roots=_runtime_generated_roots(
                    runtime,
                    output_root,
                ),
                include_hidden=args.include_hidden,
                include_secrets=args.include_secrets,
                extra_patterns=args.exclude,
                respect_gitignore=args.respect_gitignore,
            )

            projection = build_projection(
                candidates=candidates,
                skipped=skipped,
                failures=failures,
                symlinks=symlinks,
                stats=stats,
                profile=profile,
                content_store=(
                    staging_root
                    / "content"
                ),
                workers=args.workers,
                include_secrets=args.include_secrets,
            )

            if (
                args.strict
                and projection.failures
            ):
                examples = "; ".join(
                    (
                        f"{item.path}: "
                        f"{item.reason}"
                    )
                    for item
                    in projection.failures[
                        :10
                    ]
                )

                raise SdumpError(
                    (
                        "strict scan failed with "
                        f"{len(projection.failures)} "
                        "failures: "
                        f"{examples}"
                    )
                )

            if plan_only:
                summary = _summary(
                    profile,
                    projection,
                    None,
                    None,
                    None,
                    None,
                    False,
                )

                _print_summary(
                    summary,
                    args.json_summary,
                )

                return 0

            assert run_dir is not None

            output = (
                run_dir
                / (
                    "sdump_"
                    f"{_target_name(targets)}_"
                    f"{run_stamp}.txt"
                )
            )

            manifest = _manifest(
                profile=profile,
                targets=targets,
                projection=projection,
                output_name=output.name,
                registry_hash=_registry_hash(),
            )

            write_bundle(
                output,
                manifest,
                projection,
                pretty_manifest=args.pretty_manifest,
            )

            shutil.rmtree(
                staging_root,
                ignore_errors=True,
            )

            artifact = output

            if (
                args.compress
                == "zstd"
            ):
                artifact = compress_zstd(
                    output,
                    level=args.zstd_level,
                    threads=args.workers,
                )

            artifact_hash = (
                sha256_file(
                    artifact
                )
            )

            upload: UploadResult | None = None
            receipt: Path | None = None
            local_deleted = False

            if not args.no_upload:
                upload = upload_verified(
                    artifact,
                    prefix=args.s3_prefix,
                    metadata={
                        "snapshot-hash":
                            projection.snapshot_hash,
                        "profile":
                            profile.id,
                        "schema":
                            "savant-sdump-v3",
                    },
                    concurrency=args.upload_concurrency,
                )

                should_delete = (
                    args.delete_after_upload
                    and not args.keep_local
                    and upload.verified
                )

                if should_delete:
                    if artifact.exists():
                        artifact.unlink()

                    if (
                        artifact != output
                        and output.exists()
                    ):
                        output.unlink()

                    local_deleted = True

                receipt = write_receipt(
                    receipt_root=receipt_root,
                    artifact=artifact,
                    artifact_sha256=artifact_hash,
                    snapshot_hash=projection.snapshot_hash,
                    profile=profile.id,
                    counts=projection.stats.to_dict(),
                    upload=upload,
                    local_deleted=local_deleted,
                )

                if local_deleted:
                    _cleanup_run_dir(
                        run_dir
                    )

            summary = _summary(
                profile,
                projection,
                artifact,
                artifact_hash,
                upload,
                receipt,
                local_deleted,
            )

            _print_summary(
                summary,
                args.json_summary,
            )

            return 0

        finally:
            if (
                temporary_parent
                is not None
            ):
                temporary_parent.cleanup()


def run_profiles() -> int:
    for name in list_profiles():
        profile = load_profile(
            name
        )

        print(
            (
                f"{profile.id}\t"
                f"{profile.description}"
            )
        )

    return 0


def run_self_test() -> int:
    import unittest

    root = (
        Path(
            __file__
        ).resolve().parent.parent
    )

    suite = (
        unittest.defaultTestLoader.discover(
            str(
                root
                / "tests"
            )
        )
    )

    result = (
        unittest.TextTestRunner(
            verbosity=2
        ).run(
            suite
        )
    )

    return (
        0
        if result.wasSuccessful()
        else 1
    )


def main(
    argv: list[str] | None = None,
) -> int:
    raw = list(
        sys.argv[
            1:
        ]
        if argv is None
        else argv
    )

    parser = _parser()

    args = parser.parse_args(
        _backward_compatible_argv(
            raw
        )
    )

    if (
        args.command
        == "profiles"
    ):
        return run_profiles()

    if (
        args.command
        == "self-test"
    ):
        return run_self_test()

    if (
        args.command
        == "plan"
    ):
        return run_dump(
            args,
            plan_only=True,
        )

    if (
        args.command
        == "dump"
    ):
        return run_dump(
            args,
            plan_only=False,
        )

    parser.print_help()

    return 2


def entrypoint() -> None:
    try:
        raise SystemExit(
            main()
        )

    except (
        ProfileError,
        ScanError,
        UploadError,
        SdumpError,
        RuntimeError,
    ) as error:
        print(
            f"sdump error: {error}",
            file=sys.stderr,
        )

        raise SystemExit(
            1
        )
