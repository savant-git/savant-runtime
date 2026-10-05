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


schema = "savant.sdump.bundle.v5"


living_state_root = Path(
    "/root/savant-runtime/runtime/living-state"
).resolve(
    strict=False
)


living_state_generated_names = frozenset(
    {
        "current.json",
        "health.json",
        "journal.jsonl",
        "cache.json",
        "engine.lock",
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


def _generated_living_state_path(
    path: Path,
) -> bool:
    if (
        path.name
        not in living_state_generated_names
    ):
        return False

    try:
        parent = path.parent.resolve(
            strict=False
        )

    except OSError:
        return False

    return (
        parent
        == living_state_root
    )


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
        include_hidden=include_hidden,
        include_secrets=include_secrets,
        extra_patterns=extra_patterns,
        respect_gitignore=(
            respect_gitignore
        ),
    )

    retained = []

    for candidate in candidates:
        if not _generated_living_state_path(
            candidate.absolute_path
        ):
            retained.append(
                candidate
            )

            continue

        skipped.append(
            SkipRecord(
                candidate.relative_path,
                (
                    "dynamic_living_state_"
                    "projection"
                ),
                candidate.size,
            )
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
            "dynamic_living_state_source_policy"
        ] = {
            "source_files_captured":
                [
                    "engine.py",
                    "query.py",
                ],
            "generated_files_excluded_from_source_scan":
                sorted(
                    living_state_generated_names
                ),
            "generated_state_preserved_by":
                (
                    "living-state projection "
                    "and v5 state capsule"
                ),
            "strict_scan_weakened":
                False,
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
        "dynamic_living_state_files_are_not_source_failures":
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

    return base_upload_verified(
        *args,
        **kwargs,
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


def entrypoint() -> None:
    install()

    cli.entrypoint()


if __name__ == "__main__":
    entrypoint()
