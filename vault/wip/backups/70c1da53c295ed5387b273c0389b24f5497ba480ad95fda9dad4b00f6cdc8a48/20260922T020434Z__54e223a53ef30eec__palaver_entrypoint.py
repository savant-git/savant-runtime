from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import stat
import sys
from typing import Any, Iterable

from . import cli
from . import palaver_render as render_v4_module
from . import scan as scan_module
from .model import SkipRecord
from .render_v5 import write_bundle
from .upload import (
    upload_verified as base_upload_verified,
)
from .github import push_current_head


schema = "savant.sdump.bundle.v5"


runtime_projection_roots = (
    Path(
        "/root/savant-runtime/runtime/living-state"
    ).resolve(strict=False),
    Path(
        "/root/savant-runtime/runtime/living-fabric"
    ).resolve(strict=False),
)


runtime_projection_generated_names = frozenset(
    {
        "current.json",
        "health.json",
        "journal.jsonl",
        "history.jsonl",
        "cache.json",
        "receipt.json",
        "engine.lock",
    }
)


runtime_ephemeral_suffixes = frozenset(
    {
        ".pyc",
        ".pyo",
        ".swp",
        ".swo",
        ".tmp",
        ".temp",
        ".bak",
        ".old",
        ".orig",
        ".rej",
        ".log",
        ".pid",
        ".lock",
        ".wal",
        ".shm",
    }
)


runtime_ephemeral_names = frozenset(
    {
        ".ds_store",
        "thumbs.db",
    }
)


runtime_ephemeral_directory_names = frozenset(
    {
        "__pycache__",
        ".pytest_cache",
        ".mypy_cache",
        ".ruff_cache",
        ".coverage",
        ".cache",
        "node_modules",
    }
)


lockfile_names = frozenset(
    {
        "package-lock.json",
        "pnpm-lock.yaml",
        "yarn.lock",
        "bun.lock",
        "cargo.lock",
        "poetry.lock",
        "pipfile.lock",
        "composer.lock",
        "gemfile.lock",
    }
)


strong_program_extensions = frozenset(
    {
        ".py", ".pyi", ".js", ".jsx", ".mjs", ".cjs",
        ".ts", ".tsx", ".mts", ".cts", ".go", ".rs",
        ".java", ".kt", ".kts", ".c", ".cc", ".cpp",
        ".cxx", ".h", ".hh", ".hpp", ".hxx", ".cs",
        ".rb", ".php", ".lua", ".pl", ".r", ".sh",
        ".bash", ".zsh", ".fish", ".ps1", ".sql",
        ".graphql", ".gql", ".proto", ".rego", ".cue",
        ".hcl", ".nix", ".cmake", ".mk", ".tf",
        ".tfvars", ".gradle", ".vue", ".svelte",
        ".html", ".htm", ".css", ".scss", ".sass",
        ".less",
    }
)


large_data_limit_bytes = (
    16
    * 1024
    * 1024
)


base_profile_with_overrides = (
    cli._profile_with_overrides
)

base_manifest = (
    cli._manifest
)

base_discover = (
    scan_module.discover
)

base_source_candidate = (
    scan_module._authoritative_candidate
)

base_record_dict = (
    render_v4_module._record_dict
)

base_runtime_generated_roots = (
    cli._runtime_generated_roots
)

base_run_dump = (
    cli.run_dump
)


def _within_root(
    path: Path,
    root: Path,
) -> bool:
    try:
        resolved = path.resolve(
            strict=False
        )
        resolved.relative_to(root)
        return True

    except (
        OSError,
        ValueError,
    ):
        return False


def _generated_runtime_projection_path(
    path: Path,
) -> bool:
    if (
        path.name.casefold()
        not in runtime_projection_generated_names
    ):
        return False

    return any(
        _within_root(
            path,
            root,
        )
        for root in runtime_projection_roots
    )


def _runtime_ephemeral_path(
    path: Path,
) -> bool:
    lowered_name = (
        path.name.casefold()
    )

    if (
        lowered_name
        in runtime_ephemeral_names
    ):
        return True

    if any(
        part.casefold()
        in runtime_ephemeral_directory_names
        for part in path.parts
    ):
        return True

    lowered_suffix = (
        path.suffix.casefold()
    )

    if (
        lowered_suffix
        in runtime_ephemeral_suffixes
    ):
        return True

    return False


def discover(
    targets: list[Path],
    profile: Any,
    absolute_excluded_roots: Iterable[Path],
    include_hidden: bool,
    include_secrets: bool,
    extra_patterns: Iterable[str],
    respect_gitignore: bool | None,
):
    (
        candidates,
        skipped,
        failures,
        symlinks,
        stats,
    ) = base_discover(
        targets=targets,
        profile=profile,
        absolute_excluded_roots=(
            absolute_excluded_roots
        ),
        include_hidden=(
            True
            if profile.id.casefold() == "code"
            else include_hidden
        ),
        include_secrets=include_secrets,
        extra_patterns=extra_patterns,
        respect_gitignore=(
            False
            if profile.id.casefold() == "code"
            else respect_gitignore
        ),
    )

    retained = []

    for candidate in candidates:
        path = (
            candidate.absolute_path
        )

        if (
            profile.id.casefold() == "code"
            and candidate.size
            > large_data_limit_bytes
            and path.suffix.casefold()
            not in strong_program_extensions
            and path.name.casefold()
            not in lockfile_names
            and not _shebang_source(path)
        ):
            skipped.append(
                SkipRecord(
                    candidate.relative_path,
                    "large_nonprogram_data",
                    candidate.size,
                )
            )
            continue

        if (
            _generated_runtime_projection_path(
                path
            )
        ):
            skipped.append(
                SkipRecord(
                    candidate.relative_path,
                    (
                        "dynamic_runtime_"
                        "projection"
                    ),
                    candidate.size,
                )
            )
            continue

        if (
            _runtime_ephemeral_path(
                path
            )
        ):
            skipped.append(
                SkipRecord(
                    candidate.relative_path,
                    (
                        "ephemeral_runtime_"
                        "artifact"
                    ),
                    candidate.size,
                )
            )
            continue

        retained.append(
            candidate
        )

    skipped.sort(
        key=lambda item: (
            item.path.casefold(),
            item.reason,
        )
    )

    stats.candidates = len(
        retained
    )

    stats.skipped = len(
        skipped
    )

    if profile.id.casefold() == "code":
        program_skips = [
            item
            for item in skipped
            if (
                Path(item.path).suffix.casefold()
                in strong_program_extensions
                or Path(item.path).name.casefold()
                in lockfile_names
            )
        ]

        if program_skips:
            examples = "; ".join(
                f"{item.path}: {item.reason}"
                for item in program_skips[:10]
            )

            raise scan_module.ScanError(
                "code completeness invariant failed: "
                f"{len(program_skips)} recognized program "
                "files would be skipped: "
                f"{examples}"
            )

    return (
        retained,
        skipped,
        failures,
        symlinks,
        stats,
    )


def _shebang_source(
    path: Path,
) -> bool:
    try:
        if not path.is_file():
            return False

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

    lowered = first.decode(
        "utf-8",
        errors="ignore",
    ).casefold()

    return any(
        token in lowered
        for token
        in (
            "python",
            "bash",
            "sh",
            "node",
            "deno",
            "ruby",
            "perl",
            "php",
            "lua",
        )
    )


def source_candidate(
    path: Path,
    profile: Any,
    mode: int,
) -> bool:
    if base_source_candidate(
        path,
        profile,
        mode,
    ):
        return True

    if (
        path.name.casefold()
        in lockfile_names
    ):
        return True

    if _shebang_source(
        path
    ):
        return True

    return False


def profile_with_overrides(
    profile: Any,
    args: Any,
) -> Any:
    resolved = (
        base_profile_with_overrides(
            profile,
            args,
        )
    )

    updates: dict[
        str,
        Any,
    ] = {}

    if (
        getattr(
            args,
            "max_total_mb",
            None,
        )
        is None
    ):
        updates[
            "max_total_content_bytes"
        ] = sys.maxsize

    if (
        getattr(
            args,
            "max_file_mb",
            None,
        )
        is None
        and resolved.max_file_bytes
        < (
            16
            * 1024
            * 1024
        )
    ):
        updates[
            "max_file_bytes"
        ] = (
            16
            * 1024
            * 1024
        )

    include_filenames = set(
        resolved.include_filenames
    )

    include_filenames.update(
        lockfile_names
    )

    updates[
        "include_filenames"
    ] = frozenset(
        include_filenames
    )

    exclude_file_names = set(
        resolved.exclude_file_names
    )

    exclude_file_names.difference_update(
        lockfile_names
    )

    updates[
        "exclude_file_names"
    ] = frozenset(
        exclude_file_names
    )

    if resolved.id.casefold() == "code":
        unsafe_directory_patterns = {
            "source/**",
            "exports/**",
            "audit/**",
            "_reports/**",
            "repair_backups/**",
            "relics/**",
            "imports/**",
            "vault/kindred-preview/**",
        }

        updates[
            "exclude_patterns"
        ] = tuple(
            pattern
            for pattern
            in resolved.exclude_patterns
            if pattern
            not in unsafe_directory_patterns
        )

        updates[
            "respect_gitignore"
        ] = False

        if getattr(
            args,
            "max_file_mb",
            None,
        ) is None:
            updates[
                "max_file_bytes"
            ] = sys.maxsize

    return replace(
        resolved,
        **updates,
    )


def _evidence_class(
    path: str,
) -> str:
    normalized = (
        "/"
        + path.casefold().strip(
            "/"
        )
        + "/"
    )

    if (
        "/runtime/living-state/"
        in normalized
    ):
        return (
            "live_state_projection"
        )

    if (
        "/runtime/living-fabric/"
        in normalized
    ):
        return (
            "living_fabric_projection"
        )

    if (
        "/backup/"
        in normalized
        or "/backups/"
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
        return (
            "imported_or_"
            "historical_evidence"
        )

    if (
        "/vault/"
        in normalized
    ):
        return "vault_evidence"

    if any(
        token in normalized
        for token
        in (
            "/authority/",
            "/canon/",
            "/canon-system/",
        )
    ):
        return "authority_candidate"

    if (
        "/runtime/"
        in normalized
    ):
        return (
            "runtime_projection_or_state"
        )

    return (
        "implementation_evidence"
    )


def record_dict(
    record: Any,
) -> dict[str, Any]:
    value = base_record_dict(
        record
    )

    value.pop(
        "authoritative",
        None,
    )

    value[
        "evidence_class"
    ] = _evidence_class(
        str(
            record.path
        )
    )

    value[
        "authority_effect"
    ] = "none"

    value[
        "filesystem_presence_establishes_authority"
    ] = False

    return value


def manifest(
    *args: Any,
    **kwargs: Any,
) -> dict[str, Any]:
    value = base_manifest(
        *args,
        **kwargs,
    )

    value[
        "schema"
    ] = schema

    value[
        "projection_only"
    ] = True

    value[
        "authority_effect"
    ] = "none"

    value[
        "filesystem_presence_establishes_authority"
    ] = False

    profile = value.get(
        "profile"
    )

    if isinstance(
        profile,
        dict,
    ):
        if (
            profile.get(
                "max_total_content_bytes"
            )
            == sys.maxsize
        ):
            profile[
                "max_total_content_bytes"
            ] = None

            profile[
                "max_total_content_bytes_semantics"
            ] = (
                "unbounded unless "
                "explicitly overridden"
            )

        profile[
            "default_max_file_bytes_v5"
        ] = (
            16
            * 1024
            * 1024
        )

        profile[
            "dependency_lockfiles_admitted"
        ] = sorted(
            lockfile_names
        )

        profile[
            "shebang_source_recognition"
        ] = True

        profile[
            "compact_runtime_projection_policy"
        ] = {
            "projection_roots":
                [
                    str(root)
                    for root
                    in runtime_projection_roots
                ],
            "generated_files_excluded_from_source_scan":
                sorted(
                    runtime_projection_generated_names
                ),
            "ephemeral_suffixes_excluded":
                sorted(
                    runtime_ephemeral_suffixes
                ),
            "ephemeral_directories_excluded":
                sorted(
                    runtime_ephemeral_directory_names
                ),
            "source_implementations_preserved":
                True,
            "generated_state_regenerable":
                True,
            "strict_scan_weakened":
                False,
            "compression_used":
                False,
            "text_transport_preserved":
                True,
        }

    files = value.get(
        "files"
    )

    if isinstance(
        files,
        list,
    ):
        for record in files:
            if not isinstance(
                record,
                dict,
            ):
                continue

            record.pop(
                "authoritative",
                None,
            )

            path = str(
                record.get(
                    "path",
                    "",
                )
            )

            record[
                "evidence_class"
            ] = _evidence_class(
                path
            )

            record[
                "authority_effect"
            ] = "none"

            record[
                "filesystem_presence_establishes_authority"
            ] = False

    projection = (
        kwargs.get("projection")
        if "projection" in kwargs
        else (
            args[2]
            if len(args) > 2
            else None
        )
    )

    recognized_program_skips = []

    if projection is not None:
        for item in projection.skipped:
            path = Path(item.path)

            if (
                path.suffix.casefold()
                in strong_program_extensions
                or path.name.casefold()
                in lockfile_names
            ):
                recognized_program_skips.append(
                    item.to_dict()
                )

    value[
        "source_completeness_policy"
    ] = {
        "code_profile_respects_gitignore": False,
        "code_profile_hidden_source_visible": True,
        "broad_path_exclusions_removed": True,
        "dependency_lockfiles_admitted": True,
        "shebang_source_recognition": True,
        "large_nonprogram_data_limit_bytes": large_data_limit_bytes,
        "program_source_size_limit": None,
        "recognized_program_files_skipped": len(
            recognized_program_skips
        ),
        "recognized_program_skip_records": recognized_program_skips,
    }

    value[
        "format"
    ] = {
        "generation":
            5,
        "consumer_optimized_for":
            "palaver",
        "v4_source_transport_compatible":
            True,
        "source_before_tree":
            True,
        "same_scope_tree":
            True,
        "explicit_source_completeness_receipt":
            True,
        "v5_state_capsule_appended":
            True,
        "dynamic_state_scan_isolation":
            True,
        "strict_source_race_detection":
            True,
        "silent_truncation_permitted":
            False,
        "compression":
            "none",
        "transport":
            "plain_text",
        "terminal_marker":
            (
                "end sdump "
                "enterprise v5 complete"
            ),
    }

    value[
        "authority_semantics"
    ] = {
        "dump_is_authority":
            False,
        "filesystem_presence_is_authority":
            False,
        "state_capsule_is_authority":
            False,
        "authority_resolution":
            (
                "accepted authoritative graph, "
                "accepted decisions, "
                "constitutional canon, "
                "then verified implementation"
            ),
    }

    value[
        "ai_ingestion"
    ] = {
        "complete_document_requires_terminal_marker":
            (
                "end sdump "
                "enterprise v5 complete"
            ),
        "v4_terminal_marker_closes_compatibility_transport_only":
            True,
        "do_not_infer_excluded_material":
            True,
        "do_not_promote_evidence_to_authority":
            True,
        "use_content_id_to_resolve_duplicate_paths":
            True,
        "source_line_indexes_remain_relative_to_document_start":
            True,
        "state_capsule_follows_v4_compatibility_payload":
            True,
        "dynamic_runtime_projection_files_are_not_source_failures":
            True,
        "secret_values_are_not_serialized":
            True,
    }

    return value


def upload_verified(
    *args: Any,
    **kwargs: Any,
) -> Any:
    metadata = dict(
        kwargs.get(
            "metadata"
        )
        or {}
    )

    metadata[
        "schema"
    ] = "savant-sdump-v5"

    kwargs[
        "metadata"
    ] = metadata

    kwargs[
        "prefix"
    ] = ""

    result = base_upload_verified(
        *args,
        **kwargs,
    )

    push_current_head(
        Path(
            "/root/savant-runtime"
        )
    )

    return result


def runtime_generated_roots(
    runtime: Path,
    output_root: Path,
) -> tuple[Path, ...]:
    return (
        output_root.resolve(
            strict=False
        ),
    )


def run_dump(
    args: Any,
    plan_only: bool = False,
) -> int:
    if (
        not plan_only
        and not getattr(
            args,
            "output_dir",
            None,
        )
    ):
        args.output_dir = (
            "/root/savant-sdump-output"
        )

    if (
        not plan_only
        and getattr(
            args,
            "compress",
            "none",
        ) == "none"
    ):
        args.compress = "zstd"

        if getattr(
            args,
            "zstd_level",
            10,
        ) == 10:
            args.zstd_level = 15

    return base_run_dump(
        args,
        plan_only=plan_only,
    )


def install() -> None:
    cli.SCHEMA = schema

    scan_module._authoritative_candidate = (
        source_candidate
    )

    render_v4_module._record_dict = (
        record_dict
    )

    cli.discover = discover

    cli._profile_with_overrides = (
        profile_with_overrides
    )

    cli._manifest = manifest

    cli.write_bundle = (
        write_bundle
    )

    cli.upload_verified = (
        upload_verified
    )

    cli._runtime_generated_roots = (
        runtime_generated_roots
    )

    cli.run_dump = (
        run_dump
    )


def entrypoint() -> None:
    install()

    cli.entrypoint()


if __name__ == "__main__":
    entrypoint()
