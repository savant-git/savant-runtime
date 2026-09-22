from __future__ import annotations

from collections import Counter, defaultdict
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile
from typing import Any, Iterable, Mapping

from .model import Projection


schema = "savant.sdump.palaver-render.v4"
border = "=" * 88
sub_border = "-" * 88


environment_patterns = (
    re.compile(
        r"""os\.getenv\(\s*["']([A-Za-z_][A-Za-z0-9_]*)["']"""
    ),
    re.compile(
        r"""os\.environ(?:\.get)?\(\s*["']([A-Za-z_][A-Za-z0-9_]*)["']"""
    ),
    re.compile(
        r"""os\.environ\[\s*["']([A-Za-z_][A-Za-z0-9_]*)["']\s*\]"""
    ),
    re.compile(
        r"""process\.env\.([A-Za-z_][A-Za-z0-9_]*)"""
    ),
    re.compile(
        r"""process\.env\[\s*["']([A-Za-z_][A-Za-z0-9_]*)["']\s*\]"""
    ),
    re.compile(
        r"""\$\{([A-Za-z_][A-Za-z0-9_]*)\}"""
    ),
)


python_import_pattern = re.compile(
    r"""^\s*(?:from|import)\s+([A-Za-z_][A-Za-z0-9_.]*)""",
    re.MULTILINE,
)

javascript_import_patterns = (
    re.compile(
        r"""(?:from\s+|import\s*\()\s*["']([^"']+)["']"""
    ),
    re.compile(
        r"""require\(\s*["']([^"']+)["']\s*\)"""
    ),
)


package_manifests = {
    "package.json",
    "package-lock.json",
    "pnpm-lock.yaml",
    "yarn.lock",
    "pyproject.toml",
    "requirements.txt",
    "requirements-dev.txt",
    "poetry.lock",
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


class LineWriter:
    def __init__(
        self,
        handle: Any,
    ) -> None:
        self.handle = handle
        self.line = 1

    def write(
        self,
        value: str,
    ) -> None:
        self.handle.write(
            value
        )
        self.line += value.count(
            "\n"
        )


def _json(
    value: Any,
    pretty: bool = False,
) -> str:
    if not pretty:
        try:
            import orjson

            return orjson.dumps(
                value,
                option=orjson.OPT_SORT_KEYS,
            ).decode(
                "utf-8"
            )
        except ImportError:
            pass

    if pretty:
        return json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            indent=2,
        )

    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(
            ",",
            ":",
        ),
    )


def _stable_sha256(
    value: Any,
) -> str:
    encoded = _json(
        value,
        pretty=False,
    ).encode(
        "utf-8"
    )

    return hashlib.sha256(
        encoded
    ).hexdigest()


def _optional_blake3(
    value: bytes,
) -> str | None:
    try:
        import blake3
    except ImportError:
        return None

    return blake3.blake3(
        value
    ).hexdigest()


def _sha256_file(
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


def _content_metrics(
    path: Path,
) -> dict[str, int]:
    characters = 0
    lines = 0
    bytes_seen = 0
    last_character = ""

    with path.open(
        "r",
        encoding="utf-8",
        errors="strict",
        newline="",
    ) as handle:
        while True:
            chunk = handle.read(
                1024 * 1024
            )

            if not chunk:
                break

            characters += len(
                chunk
            )

            lines += chunk.count(
                "\n"
            )

            bytes_seen += len(
                chunk.encode(
                    "utf-8"
                )
            )

            last_character = chunk[
                -1:
            ]

    if characters > 0 and last_character != "\n":
        lines += 1

    return {
        "bytes": bytes_seen,
        "characters": characters,
        "lines": lines,
    }


def _content_text(
    path: Path,
) -> str:
    return path.read_text(
        encoding="utf-8",
        errors="strict",
    )


def _record_dict(
    record: Any,
) -> dict[str, Any]:
    return {
        "path": record.path,
        "target_id": record.target_id,
        "category": record.category,
        "language": record.language,
        "source_bytes": record.size,
        "mode": record.mode,
        "mtime_ns": record.mtime_ns,
        "source_sha256": record.source_sha256,
        "rendered_sha256": record.rendered_sha256,
        "content_id": record.content_id,
        "duplicate_of": record.duplicate_of,
        "encoding": record.encoding,
        "redactions": record.redactions,
        "authoritative": record.authoritative,
        "included": record.included,
        "reason": record.reason,
    }


def _record_id(
    record: Any,
) -> str:
    digest = hashlib.sha256(
        (
            str(
                record.target_id
            )
            + "\0"
            + str(
                record.path
            )
            + "\0"
            + str(
                record.source_sha256
            )
        ).encode(
            "utf-8"
        )
    ).hexdigest()

    return (
        "sdump-file-"
        + digest[:24]
    )


def _content_records(
    projection: Projection,
) -> dict[str, list[Any]]:
    grouped: dict[
        str,
        list[Any],
    ] = defaultdict(
        list
    )

    for record in projection.records:
        if (
            record.included
            and record.content_id
        ):
            grouped[
                record.content_id
            ].append(
                record
            )

    return dict(
        sorted(
            grouped.items(),
            key=lambda item: item[
                0
            ],
        )
    )


def _is_executable(
    record: Any,
) -> bool:
    try:
        return bool(
            int(
                str(
                    record.mode
                ),
                8,
            )
            & 0o111
        )
    except (
        TypeError,
        ValueError,
    ):
        return False


def _runtime_state_index(
    projection: Projection,
) -> dict[str, Any]:
    included = [
        record
        for record
        in projection.records
        if record.included
    ]

    executable_entrypoints = []
    systemd_units = []
    nginx_surfaces = []
    manifests = []
    tests = []
    canon_paths = []
    palaver_paths = []
    envoy_paths = []
    opus_paths = []

    for record in included:
        path = str(
            record.path
        )

        lower = path.casefold()
        name = Path(
            path
        ).name.casefold()

        if _is_executable(
            record
        ):
            executable_entrypoints.append(
                path
            )

        if name.endswith(
            ".service"
        ):
            systemd_units.append(
                path
            )

        if (
            "nginx" in lower
            or "sites-enabled" in lower
            or "sites-available" in lower
        ):
            nginx_surfaces.append(
                path
            )

        if name in package_manifests:
            manifests.append(
                path
            )

        if (
            "/test" in lower
            or "/tests/" in lower
            or name.startswith(
                "test_"
            )
            or name.endswith(
                "_test.py"
            )
            or name.endswith(
                ".test.ts"
            )
            or name.endswith(
                ".test.tsx"
            )
            or name.endswith(
                ".spec.ts"
            )
            or name.endswith(
                ".spec.tsx"
            )
        ):
            tests.append(
                path
            )

        if "canon" in lower:
            canon_paths.append(
                path
            )

        if "palaver" in lower:
            palaver_paths.append(
                path
            )

        if "envoy" in lower:
            envoy_paths.append(
                path
            )

        if "opus" in lower:
            opus_paths.append(
                path
            )

    return {
        "derived_projection": True,
        "authority_effect": "none",
        "executables": sorted(
            executable_entrypoints
        ),
        "systemd_units": sorted(
            systemd_units
        ),
        "nginx_surfaces": sorted(
            nginx_surfaces
        ),
        "package_manifests": sorted(
            manifests
        ),
        "tests": sorted(
            tests
        ),
        "canon_paths": sorted(
            canon_paths
        ),
        "palaver_path_count": len(
            palaver_paths
        ),
        "envoy_path_count": len(
            envoy_paths
        ),
        "opus_path_count": len(
            opus_paths
        ),
    }


def _derived_source_index(
    projection: Projection,
) -> dict[str, Any]:
    environment_names: set[
        str
    ] = set()

    python_dependencies: Counter[
        str
    ] = Counter()

    javascript_dependencies: Counter[
        str
    ] = Counter()

    for content_id, path in sorted(
        projection.unique_content_paths.items()
    ):
        if not path.is_file():
            continue

        try:
            text = _content_text(
                path
            )
        except (
            OSError,
            UnicodeError,
        ):
            continue

        for pattern in environment_patterns:
            for match in pattern.finditer(
                text
            ):
                environment_names.add(
                    match.group(
                        1
                    )
                )

        for match in python_import_pattern.finditer(
            text
        ):
            module = match.group(
                1
            ).split(
                "."
            )[
                0
            ]

            if module:
                python_dependencies[
                    module
                ] += 1

        for pattern in javascript_import_patterns:
            for match in pattern.finditer(
                text
            ):
                module = match.group(
                    1
                )

                if module.startswith(
                    "."
                ):
                    continue

                if module.startswith(
                    "@"
                ):
                    parts = module.split(
                        "/"
                    )

                    module = "/".join(
                        parts[:2]
                    )

                else:
                    module = module.split(
                        "/"
                    )[
                        0
                    ]

                if module:
                    javascript_dependencies[
                        module
                    ] += 1

    return {
        "derived_heuristic": True,
        "authority_effect": "none",
        "environment_variable_names_only": sorted(
            environment_names
        ),
        "python_import_roots": dict(
            python_dependencies.most_common()
        ),
        "javascript_import_roots": dict(
            javascript_dependencies.most_common()
        ),
    }


def _tree_lines(
    paths: Iterable[str],
) -> list[str]:
    root: dict[
        str,
        dict[str, Any],
    ] = {}

    for original in sorted(
        set(
            paths
        ),
        key=str.casefold,
    ):
        parts = [
            part
            for part
            in Path(
                original
            ).parts
            if part not in {
                "",
                ".",
            }
        ]

        if not parts:
            continue

        node = root

        for part in parts:
            node = node.setdefault(
                part,
                {},
            )

    lines = [
        "."
    ]

    def visit(
        node: dict[str, Any],
        prefix: str,
    ) -> None:
        names = sorted(
            node,
            key=str.casefold,
        )

        for index, name in enumerate(
            names
        ):
            last = (
                index
                == len(
                    names
                )
                - 1
            )

            branch = (
                "└── "
                if last
                else "├── "
            )

            child = node[
                name
            ]

            suffix = (
                "/"
                if child
                else ""
            )

            lines.append(
                prefix
                + branch
                + name
                + suffix
            )

            if child:
                visit(
                    child,
                    prefix
                    + (
                        "    "
                        if last
                        else "│   "
                    ),
                )

    visit(
        root,
        "",
    )

    return lines


def _structural_statistics(
    projection: Projection,
) -> dict[str, Any]:
    included = [
        record
        for record
        in projection.records
        if record.included
    ]

    languages = Counter(
        record.language
        for record
        in included
    )

    categories = Counter(
        record.category
        for record
        in included
    )

    extensions = Counter(
        (
            Path(
                record.path
            ).suffix.casefold()
            or "[none]"
        )
        for record
        in included
    )

    largest = sorted(
        included,
        key=lambda record: (
            -int(
                record.size
            ),
            str(
                record.path
            ).casefold(),
        ),
    )[:50]

    directories: set[
        str
    ] = set()

    for record in included:
        path = Path(
            record.path
        )

        parent = path.parent

        while str(
            parent
        ) not in {
            "",
            ".",
        }:
            directories.add(
                str(
                    parent
                )
            )

            parent = parent.parent

    return {
        "files": len(
            included
        ),
        "directories": len(
            directories
        ),
        "symlinks": len(
            projection.symlinks
        ),
        "source_bytes": sum(
            int(
                record.size
            )
            for record
            in included
        ),
        "unique_contents": len(
            {
                record.content_id
                for record
                in included
                if record.content_id
            }
        ),
        "duplicate_files": sum(
            1
            for record
            in included
            if record.duplicate_of
            is not None
        ),
        "languages": dict(
            sorted(
                languages.items()
            )
        ),
        "categories": dict(
            sorted(
                categories.items()
            )
        ),
        "extensions": dict(
            sorted(
                extensions.items()
            )
        ),
        "largest_files": [
            {
                "path": record.path,
                "bytes": record.size,
            }
            for record
            in largest
        ],
    }


def _write_json_section(
    writer: LineWriter,
    name: str,
    value: Any,
    pretty: bool = True,
) -> tuple[int, int]:
    begin = writer.line

    writer.write(
        f"{border}\n"
        f"{name}\n"
        f"{border}\n"
    )

    writer.write(
        _json(
            value,
            pretty=pretty,
        )
    )

    writer.write(
        "\n"
    )

    end = writer.line - 1

    return (
        begin,
        end,
    )


def write_bundle(
    output: Path,
    manifest: Mapping[str, Any],
    projection: Projection,
    pretty_manifest: bool = False,
) -> None:
    output.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{output.name}.",
        suffix=".partial",
        dir=str(
            output.parent
        ),
    )

    temporary = Path(
        temporary_name
    )

    included_records = [
        record
        for record
        in projection.records
        if record.included
    ]

    content_records = _content_records(
        projection
    )

    expected_content_ids = sorted(
        content_records
    )

    source_paths = sorted(
        {
            record.path
            for record
            in included_records
        },
        key=str.casefold,
    )

    structural = _structural_statistics(
        projection
    )

    runtime_state = _runtime_state_index(
        projection
    )

    derived_source = _derived_source_index(
        projection
    )

    skipped_ledger = [
        item.to_dict()
        for item
        in projection.skipped
    ]

    failure_ledger = [
        item.to_dict()
        for item
        in projection.failures
    ]

    ingestion_contract = {
        "schema": schema,
        "consumer": "palaver and other ai ingestion systems",
        "projection_only": True,
        "authority_effect": "none",
        "source_section_semantics": (
            "all included source content is represented; "
            "identical rendered content is emitted once and "
            "all paths referencing it are explicitly enumerated"
        ),
        "deduplication_is_not_truncation": True,
        "expected_included_files": len(
            included_records
        ),
        "expected_unique_content_bodies": len(
            expected_content_ids
        ),
        "expected_tree_files": len(
            source_paths
        ),
        "skipped_records": len(
            projection.skipped
        ),
        "failure_records": len(
            projection.failures
        ),
        "symlink_records": len(
            projection.symlinks
        ),
        "silent_truncation_permitted": False,
        "cumulative_content_budget": "unbounded by default in v4",
        "per_file_profile_limit_preserved": True,
        "redaction_semantics": (
            "redacted rendered content is projection; "
            "redacted values must not be inferred"
        ),
        "unknown_semantics": (
            "skipped, excluded, binary, undecodable, "
            "failed, or redacted information remains unknown"
        ),
        "ordering": "stable path/content ordering",
        "terminal_completion_marker": (
            "end sdump enterprise v4 complete"
        ),
    }

    file_index = []

    for record in included_records:
        item = _record_dict(
            record
        )

        item[
            "record_id"
        ] = _record_id(
            record
        )

        item[
            "content_body_emitted"
        ] = bool(
            record.content_id
        )

        item[
            "content_is_duplicate"
        ] = (
            record.duplicate_of
            is not None
        )

        file_index.append(
            item
        )

    section_index: dict[
        str,
        dict[str, Any],
    ] = {}

    content_section_index = []

    written_content_ids: list[
        str
    ] = []

    try:
        with os.fdopen(
            descriptor,
            "w",
            encoding="utf-8",
            newline="",
        ) as handle:
            writer = LineWriter(
                handle
            )

            writer.write(
                "sdump enterprise v4\n"
            )

            writer.write(
                "palaver optimized complete source projection\n"
            )

            writer.write(
                "projection_only true\n"
                "authority_effect none\n"
                f"snapshot_sha256 {projection.snapshot_hash}\n"
            )

            begin, end = _write_json_section(
                writer,
                "00 ai ingestion contract",
                ingestion_contract,
            )

            section_index[
                "00_ai_ingestion_contract"
            ] = {
                "begin_line": begin,
                "end_line": end,
            }

            begin, end = _write_json_section(
                writer,
                "01 snapshot manifest",
                manifest,
                pretty=pretty_manifest,
            )

            section_index[
                "01_snapshot_manifest"
            ] = {
                "begin_line": begin,
                "end_line": end,
            }

            begin, end = _write_json_section(
                writer,
                "02 source file index",
                {
                    "count": len(
                        file_index
                    ),
                    "files": file_index,
                },
            )

            section_index[
                "02_source_file_index"
            ] = {
                "begin_line": begin,
                "end_line": end,
            }

            source_begin = writer.line

            writer.write(
                f"{border}\n"
                "03 complete source contents\n"
                f"{border}\n"
            )

            writer.write(
                "source completeness contract:\n"
                f"included_file_records={len(included_records)}\n"
                f"unique_content_bodies_expected={len(expected_content_ids)}\n"
                "identical bodies are emitted once by sha256 content address;\n"
                "every path sharing a body is listed in that body's metadata.\n"
                "absence of a duplicate body is deduplication, not truncation.\n"
                f"{sub_border}\n"
            )

            for content_id in expected_content_ids:
                records = content_records[
                    content_id
                ]

                store_path = (
                    projection.unique_content_paths.get(
                        content_id
                    )
                )

                if (
                    store_path is None
                    or not store_path.is_file()
                ):
                    raise RuntimeError(
                        "missing content store object: "
                        + content_id
                    )

                metrics = _content_metrics(
                    store_path
                )

                paths = sorted(
                    {
                        record.path
                        for record
                        in records
                    },
                    key=str.casefold,
                )

                canonical = next(
                    (
                        record
                        for record
                        in records
                        if record.duplicate_of
                        is None
                    ),
                    records[
                        0
                    ],
                )

                section_begin = writer.line

                metadata = {
                    "content_id": content_id,
                    "canonical_path": canonical.path,
                    "represented_paths": paths,
                    "represented_path_count": len(
                        paths
                    ),
                    "rendered_sha256": (
                        canonical.rendered_sha256
                    ),
                    "source_sha256": (
                        canonical.source_sha256
                    ),
                    "language": canonical.language,
                    "encoding": canonical.encoding,
                    "redactions": canonical.redactions,
                    "rendered_metrics": metrics,
                    "authority_effect": "none",
                }

                writer.write(
                    "\n"
                    "<<<sdump-content-begin>>>\n"
                )

                writer.write(
                    _json(
                        metadata,
                        pretty=False,
                    )
                )

                writer.write(
                    "\n"
                    "<<<sdump-source-body-begin>>>\n"
                )

                with store_path.open(
                    "r",
                    encoding="utf-8",
                    errors="strict",
                    newline="",
                ) as source:
                    while True:
                        chunk = source.read(
                            1024 * 1024
                        )

                        if not chunk:
                            break

                        writer.write(
                            chunk
                        )

                if (
                    metrics[
                        "characters"
                    ]
                    and not _ends_with_newline(
                        store_path
                    )
                ):
                    writer.write(
                        "\n"
                    )

                writer.write(
                    "<<<sdump-source-body-end>>>\n"
                    "<<<sdump-content-end>>>\n"
                )

                section_end = (
                    writer.line - 1
                )

                content_section_index.append(
                    {
                        "content_id": content_id,
                        "canonical_path": canonical.path,
                        "represented_paths": paths,
                        "begin_line": section_begin,
                        "end_line": section_end,
                        "rendered_bytes": metrics[
                            "bytes"
                        ],
                        "rendered_characters": metrics[
                            "characters"
                        ],
                        "rendered_lines": metrics[
                            "lines"
                        ],
                    }
                )

                written_content_ids.append(
                    content_id
                )

            source_end = (
                writer.line - 1
            )

            section_index[
                "03_complete_source_contents"
            ] = {
                "begin_line": source_begin,
                "end_line": source_end,
                "unique_content_bodies": len(
                    written_content_ids
                ),
            }

            source_receipt = {
                "included_file_records_expected": len(
                    included_records
                ),
                "included_file_records_indexed": len(
                    file_index
                ),
                "unique_content_bodies_expected": len(
                    expected_content_ids
                ),
                "unique_content_bodies_written": len(
                    written_content_ids
                ),
                "expected_content_ids_sha256": _stable_sha256(
                    expected_content_ids
                ),
                "written_content_ids_sha256": _stable_sha256(
                    written_content_ids
                ),
                "all_expected_content_bodies_written": (
                    expected_content_ids
                    == written_content_ids
                ),
                "silent_truncation_detected": (
                    expected_content_ids
                    != written_content_ids
                ),
            }

            begin, end = _write_json_section(
                writer,
                "04 source completeness receipt",
                source_receipt,
            )

            section_index[
                "04_source_completeness_receipt"
            ] = {
                "begin_line": begin,
                "end_line": end,
            }

            tree_begin = writer.line

            writer.write(
                f"{border}\n"
                "05 same-scope file tree\n"
                f"{border}\n"
            )

            writer.write(
                f"tree_file_count {len(source_paths)}\n"
                "tree_scope included source file records only\n"
                "tree_source same immutable projection used by source contents\n"
                f"{sub_border}\n"
            )

            for line in _tree_lines(
                source_paths
            ):
                writer.write(
                    line
                    + "\n"
                )

            tree_end = (
                writer.line - 1
            )

            section_index[
                "05_same_scope_file_tree"
            ] = {
                "begin_line": tree_begin,
                "end_line": tree_end,
                "file_count": len(
                    source_paths
                ),
            }

            begin, end = _write_json_section(
                writer,
                "06 structural statistics",
                structural,
            )

            section_index[
                "06_structural_statistics"
            ] = {
                "begin_line": begin,
                "end_line": end,
            }

            begin, end = _write_json_section(
                writer,
                "07 savant runtime state index",
                runtime_state,
            )

            section_index[
                "07_savant_runtime_state_index"
            ] = {
                "begin_line": begin,
                "end_line": end,
            }

            begin, end = _write_json_section(
                writer,
                "08 derived dependency and environment-name index",
                derived_source,
            )

            section_index[
                "08_derived_dependency_index"
            ] = {
                "begin_line": begin,
                "end_line": end,
            }

            duplicates = []

            for record in included_records:
                if record.duplicate_of is None:
                    continue

                duplicates.append(
                    {
                        "path": record.path,
                        "duplicate_of": record.duplicate_of,
                        "content_id": record.content_id,
                        "source_sha256": record.source_sha256,
                    }
                )

            begin, end = _write_json_section(
                writer,
                "09 content-addressed duplicate index",
                {
                    "algorithm": "sha256",
                    "duplicate_count": len(
                        duplicates
                    ),
                    "duplicates": duplicates,
                },
            )

            section_index[
                "09_duplicate_index"
            ] = {
                "begin_line": begin,
                "end_line": end,
            }

            begin, end = _write_json_section(
                writer,
                "10 symlink index",
                {
                    "count": len(
                        projection.symlinks
                    ),
                    "symlinks": projection.symlinks,
                },
            )

            section_index[
                "10_symlink_index"
            ] = {
                "begin_line": begin,
                "end_line": end,
            }

            begin, end = _write_json_section(
                writer,
                "11 exclusions and failures ledger",
                {
                    "skipped_count": len(
                        skipped_ledger
                    ),
                    "failure_count": len(
                        failure_ledger
                    ),
                    "skipped": skipped_ledger,
                    "failures": failure_ledger,
                    "unknown_semantics": (
                        "excluded/skipped/failed content "
                        "is not represented and must not be inferred"
                    ),
                },
            )

            section_index[
                "11_exclusions_failures"
            ] = {
                "begin_line": begin,
                "end_line": end,
            }

            begin, end = _write_json_section(
                writer,
                "12 content retrieval index",
                {
                    "index_type": "stable line spans",
                    "content_sections": content_section_index,
                },
            )

            section_index[
                "12_content_retrieval_index"
            ] = {
                "begin_line": begin,
                "end_line": end,
            }

            begin, end = _write_json_section(
                writer,
                "13 section index",
                section_index,
            )

            section_index[
                "13_section_index"
            ] = {
                "begin_line": begin,
                "end_line": end,
            }

            handle.flush()
            os.fsync(
                handle.fileno()
            )

            pre_receipt_sha256 = (
                _sha256_file(
                    temporary
                )
            )

            pre_receipt_bytes = (
                temporary.stat().st_size
            )

            blake3_digest = (
                _optional_blake3(
                    temporary.read_bytes()
                )
            )

            final_receipt = {
                "schema": schema,
                "snapshot_sha256": (
                    projection.snapshot_hash
                ),
                "manifest_sha256": _stable_sha256(
                    manifest
                ),
                "pre_receipt_sha256": (
                    pre_receipt_sha256
                ),
                "pre_receipt_blake3": (
                    blake3_digest
                ),
                "pre_receipt_bytes": (
                    pre_receipt_bytes
                ),
                "included_files": len(
                    included_records
                ),
                "tree_files": len(
                    source_paths
                ),
                "unique_content_bodies_expected": len(
                    expected_content_ids
                ),
                "unique_content_bodies_written": len(
                    written_content_ids
                ),
                "source_complete": (
                    expected_content_ids
                    == written_content_ids
                ),
                "tree_matches_included_scope": (
                    len(
                        source_paths
                    )
                    == len(
                        {
                            record.path
                            for record
                            in included_records
                        }
                    )
                ),
                "silent_truncation": False,
                "projection_only": True,
                "authority_effect": "none",
                "artifact_sha256_note": (
                    "final artifact sha256 is calculated by "
                    "the existing sdump cli after this receipt "
                    "is written"
                ),
            }

            _write_json_section(
                writer,
                "14 final integrity receipt",
                final_receipt,
            )

            writer.write(
                f"{border}\n"
                "end sdump enterprise v4 complete\n"
                f"snapshot_sha256 {projection.snapshot_hash}\n"
                f"included_files {len(included_records)}\n"
                f"unique_content_bodies {len(written_content_ids)}\n"
                f"tree_files {len(source_paths)}\n"
                "silent_truncation false\n"
                "projection_only true\n"
                "authority_effect none\n"
                f"{border}\n"
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
            output,
        )

        directory_fd = os.open(
            output.parent,
            os.O_DIRECTORY,
        )

        try:
            os.fsync(
                directory_fd
            )

        finally:
            os.close(
                directory_fd
            )

    finally:
        if temporary.exists():
            temporary.unlink()


def _ends_with_newline(
    path: Path,
) -> bool:
    size = path.stat().st_size

    if size == 0:
        return True

    with path.open(
        "rb"
    ) as handle:
        handle.seek(
            -1,
            os.SEEK_END,
        )

        return handle.read(
            1
        ) in {
            b"\n",
            b"\r",
        }
