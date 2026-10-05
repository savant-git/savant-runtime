#!/usr/bin/env python3
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any, Iterable


schema = (
    "savant.carbon.straub."
    "content-edifice-projection.v1"
)
owner = "carbon"
module = "straub"
authority_effect = "none"

runtime_root = Path(
    "/root/savant-runtime"
).resolve()

source_projection_path = (
    runtime_root
    / "runtime"
    / "straub"
    / "source-datrix-state"
    / "current.json"
)

default_output_path = (
    runtime_root
    / "runtime"
    / "straub"
    / "source-datrix-state"
    / "content-edifice.json"
)

content_edifice = (
    "character",
    "line",
    "snippet",
    "script",
    "module",
    "service",
    "application",
    "suite",
    "estate",
)

directly_projectable_tiers = (
    "character",
    "line",
    "script",
)

unresolved_tiers = (
    "snippet",
    "module",
    "service",
    "application",
    "suite",
    "estate",
)


def utc_now() -> str:
    return (
        datetime.now(timezone.utc)
        .isoformat()
        .replace(
            "+00:00",
            "Z",
        )
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


def canonical_json_bytes(
    value: Any,
) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(
            ",",
            ":",
        ),
    ).encode(
        "utf-8"
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
        canonical_json_bytes(
            value
        )
        + b"\n"
    )

    temporary = path.with_name(
        "."
        + path.name
        + ".tmp"
    )

    with temporary.open(
        "wb"
    ) as handle:
        handle.write(
            payload
        )
        handle.flush()

    temporary.replace(
        path
    )


def load_source_projection(
    path: Path,
) -> dict[str, Any]:
    value = json.loads(
        path.read_text(
            encoding="utf-8"
        )
    )

    if not isinstance(
        value,
        dict,
    ):
        raise ValueError(
            "source projection must be an object"
        )

    if not value.get(
        "projection_only"
    ):
        raise ValueError(
            "source input is not projection-only"
        )

    files = value.get(
        "files"
    )

    if not isinstance(
        files,
        list,
    ):
        raise ValueError(
            "source projection files must be a list"
        )

    return value


def safe_runtime_path(
    relative: str,
) -> Path | None:
    if not relative:
        return None

    candidate = (
        runtime_root
        / relative
    ).resolve()

    try:
        candidate.relative_to(
            runtime_root
        )
    except ValueError:
        return None

    return candidate


def verified_source(
    item: dict[str, Any],
) -> dict[str, Any]:
    relative = str(
        item.get(
            "path",
            "",
        )
    )

    expected_digest = str(
        item.get(
            "sha256",
            "",
        )
    )

    expected_size = int(
        item.get(
            "size",
            0,
        )
        or 0
    )

    path = safe_runtime_path(
        relative
    )

    base = {
        "path": relative,
        "expected_sha256": (
            expected_digest
        ),
        "expected_size": (
            expected_size
        ),
        "authority_effect": (
            "none"
        ),
    }

    if path is None:
        return {
            **base,
            "status": (
                "invalid-path"
            ),
            "verified": False,
        }

    try:
        if (
            path.is_symlink()
            or not path.is_file()
        ):
            return {
                **base,
                "status": (
                    "missing"
                ),
                "verified": False,
            }

        raw = path.read_bytes()
    except OSError as exc:
        return {
            **base,
            "status": (
                "unreadable"
            ),
            "verified": False,
            "error": (
                type(exc).__name__
            ),
        }

    actual_digest = (
        sha256_bytes(
            raw
        )
    )

    actual_size = len(
        raw
    )

    if (
        not expected_digest
        or actual_digest
        != expected_digest
    ):
        return {
            **base,
            "status": (
                "digest-mismatch"
            ),
            "verified": False,
            "actual_sha256": (
                actual_digest
            ),
            "actual_size": (
                actual_size
            ),
        }

    if (
        expected_size
        != actual_size
    ):
        return {
            **base,
            "status": (
                "size-mismatch"
            ),
            "verified": False,
            "actual_sha256": (
                actual_digest
            ),
            "actual_size": (
                actual_size
            ),
        }

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

    return {
        **base,
        "status": "verified",
        "verified": True,
        "actual_sha256": (
            actual_digest
        ),
        "actual_size": (
            actual_size
        ),
        "encoding": encoding,
        "content": content,
    }


def split_lines(
    content: str,
) -> list[str]:
    return content.splitlines(
        keepends=True
    )


def character_id(
    character: str,
) -> str:
    return stable_id(
        "content-character",
        character,
    )


def line_id(
    line: str,
) -> str:
    return stable_id(
        "content-line",
        line,
    )


def script_id(
    path: str,
    revision_id: str,
    line_ids: Iterable[str],
) -> str:
    return stable_id(
        "content-script",
        path,
        revision_id,
        *line_ids,
    )


def utf8_size(
    value: str,
) -> int:
    return len(
        value.encode(
            "utf-8"
        )
    )


def projection_digest(
    value: dict[str, Any],
) -> str:
    material = dict(
        value
    )

    material.pop(
        "generated_at",
        None,
    )

    material.pop(
        "digest",
        None,
    )

    return sha256_bytes(
        canonical_json_bytes(
            material
        )
    )


def project(
    source: dict[str, Any],
) -> dict[str, Any]:
    files = source[
        "files"
    ]

    character_counts: Counter[str] = (
        Counter()
    )

    line_counts: Counter[str] = (
        Counter()
    )

    character_values: dict[
        str,
        str,
    ] = {}

    line_values: dict[
        str,
        str,
    ] = {}

    line_character_ids: dict[
        str,
        tuple[str, ...],
    ] = {}

    scripts: list[
        dict[str, Any]
    ] = []

    unresolved_scripts: list[
        dict[str, Any]
    ] = []

    verification_counts: Counter[
        str
    ] = Counter()

    physical_character_bytes = 0
    physical_line_bytes = 0
    verified_source_bytes = 0

    ordered_files = sorted(
        (
            item
            for item in files
            if isinstance(
                item,
                dict,
            )
        ),
        key=lambda value: str(
            value.get(
                "path",
                "",
            )
        ),
    )

    for item in ordered_files:
        verification = (
            verified_source(
                item
            )
        )

        status = str(
            verification.get(
                "status",
                "unknown",
            )
        )

        verification_counts[
            status
        ] += 1

        path = str(
            item.get(
                "path",
                "",
            )
        )

        revision_id = str(
            item.get(
                "revision_id",
                "",
            )
        )

        if not verification.get(
            "verified"
        ):
            unresolved_scripts.append(
                {
                    "path": path,
                    "source_revision_id": (
                        revision_id
                    ),
                    "status": status,
                    "expected_sha256": (
                        verification.get(
                            "expected_sha256"
                        )
                    ),
                    "actual_sha256": (
                        verification.get(
                            "actual_sha256"
                        )
                    ),
                    "expected_size": (
                        verification.get(
                            "expected_size"
                        )
                    ),
                    "actual_size": (
                        verification.get(
                            "actual_size"
                        )
                    ),
                    "authority_effect": (
                        "none"
                    ),
                }
            )

            continue

        content = str(
            verification.get(
                "content",
                "",
            )
        )

        verified_source_bytes += int(
            verification.get(
                "actual_size",
                0,
            )
            or 0
        )

        script_line_ids: list[
            str
        ] = []

        for line in split_lines(
            content
        ):
            current_line_id = (
                line_id(
                    line
                )
            )

            line_counts[
                current_line_id
            ] += 1

            line_values.setdefault(
                current_line_id,
                line,
            )

            physical_line_bytes += (
                utf8_size(
                    line
                )
            )

            current_character_ids: list[
                str
            ] = []

            for character in line:
                current_character_id = (
                    character_id(
                        character
                    )
                )

                character_counts[
                    current_character_id
                ] += 1

                character_values.setdefault(
                    current_character_id,
                    character,
                )

                physical_character_bytes += (
                    utf8_size(
                        character
                    )
                )

                current_character_ids.append(
                    current_character_id
                )

            line_character_ids.setdefault(
                current_line_id,
                tuple(
                    current_character_ids
                ),
            )

            script_line_ids.append(
                current_line_id
            )

        current_script_id = script_id(
            path,
            revision_id,
            script_line_ids,
        )

        scripts.append(
            {
                "id": (
                    current_script_id
                ),
                "kind": (
                    "content.script"
                ),
                "path": path,
                "source_revision_id": (
                    revision_id
                ),
                "source_sha256": (
                    verification[
                        "actual_sha256"
                    ]
                ),
                "source_bytes": (
                    verification[
                        "actual_size"
                    ]
                ),
                "encoding": (
                    verification[
                        "encoding"
                    ]
                ),
                "line_instances": len(
                    script_line_ids
                ),
                "line_ids": (
                    script_line_ids
                ),
                "authority_effect": (
                    "none"
                ),
            }
        )

    characters: list[
        dict[str, Any]
    ] = []

    canonical_character_bytes = 0

    for current_id in sorted(
        character_values
    ):
        value = character_values[
            current_id
        ]

        size = utf8_size(
            value
        )

        canonical_character_bytes += (
            size
        )

        characters.append(
            {
                "id": current_id,
                "kind": (
                    "content.character"
                ),
                "value": value,
                "utf8_bytes": size,
                "instances": (
                    character_counts[
                        current_id
                    ]
                ),
                "authority_effect": (
                    "none"
                ),
            }
        )

    lines: list[
        dict[str, Any]
    ] = []

    canonical_line_bytes = 0

    for current_id in sorted(
        line_values
    ):
        value = line_values[
            current_id
        ]

        size = utf8_size(
            value
        )

        canonical_line_bytes += (
            size
        )

        lines.append(
            {
                "id": current_id,
                "kind": (
                    "content.line"
                ),
                "utf8_bytes": size,
                "instances": (
                    line_counts[
                        current_id
                    ]
                ),
                "character_ids": list(
                    line_character_ids[
                        current_id
                    ]
                ),
                "authority_effect": (
                    "none"
                ),
            }
        )

    line_duplicate_bytes = max(
        0,
        physical_line_bytes
        - canonical_line_bytes,
    )

    character_duplicate_bytes = max(
        0,
        physical_character_bytes
        - canonical_character_bytes,
    )

    line_reduction_percent = (
        (
            line_duplicate_bytes
            / physical_line_bytes
        )
        * 100.0
        if physical_line_bytes
        else 0.0
    )

    character_reduction_percent = (
        (
            character_duplicate_bytes
            / physical_character_bytes
        )
        * 100.0
        if physical_character_bytes
        else 0.0
    )

    result: dict[
        str,
        Any,
    ] = {
        "schema": schema,
        "owner": owner,
        "module": module,
        "authority_effect": (
            authority_effect
        ),
        "projection_only": True,
        "semantic_authority": False,
        "filesystem_presence_establishes_authority": (
            False
        ),
        "generated_at": utc_now(),
        "source_projection": str(
            source_projection_path
        ),
        "source_projection_schema": (
            source.get(
                "schema"
            )
        ),
        "source_file_count": len(
            ordered_files
        ),
        "source_metadata_bytes": int(
            source.get(
                "source_bytes",
                0,
            )
        ),
        "verified_script_count": len(
            scripts
        ),
        "unresolved_script_count": len(
            unresolved_scripts
        ),
        "verified_source_bytes": (
            verified_source_bytes
        ),
        "verification": {
            "required": (
                "live path bytes must match "
                "source-datrix sha256 and size"
            ),
            "counts": dict(
                sorted(
                    verification_counts.items()
                )
            ),
            "all_current_scripts_verified": (
                len(
                    unresolved_scripts
                )
                == 0
            ),
        },
        "content_edifice": list(
            content_edifice
        ),
        "directly_projectable_tiers": list(
            directly_projectable_tiers
        ),
        "unresolved_tiers": [
            {
                "tier": tier,
                "status": (
                    "unresolved"
                ),
                "reason": (
                    "no authoritative deterministic "
                    "composition boundary is present "
                    "in the current source-datrix "
                    "projection"
                ),
            }
            for tier in unresolved_tiers
        ],
        "composition": {
            "character": {
                "canonical_count": len(
                    characters
                ),
                "instance_count": sum(
                    character_counts.values()
                ),
                "canonical_substance_bytes": (
                    canonical_character_bytes
                ),
                "fully_substantiated_bytes": (
                    physical_character_bytes
                ),
                "duplicate_substance_bytes": (
                    character_duplicate_bytes
                ),
                "substance_reduction_percent": round(
                    character_reduction_percent,
                    6,
                ),
            },
            "line": {
                "canonical_count": len(
                    lines
                ),
                "instance_count": sum(
                    line_counts.values()
                ),
                "canonical_substance_bytes": (
                    canonical_line_bytes
                ),
                "fully_substantiated_bytes": (
                    physical_line_bytes
                ),
                "duplicate_substance_bytes": (
                    line_duplicate_bytes
                ),
                "substance_reduction_percent": round(
                    line_reduction_percent,
                    6,
                ),
            },
            "script": {
                "canonical_count": len(
                    scripts
                ),
                "instance_count": len(
                    scripts
                ),
                "unresolved_count": len(
                    unresolved_scripts
                ),
                "composition": (
                    "ordered line-instance references"
                ),
            },
        },
        "measurement_semantics": {
            "zero_kb_meaning": (
                "zero duplicated substantive bytes; "
                "identities, references, metadata, "
                "and projection representation retain "
                "physical storage cost"
            ),
            "source_substance": (
                "only live bytes whose sha256 and size "
                "match the current source-datrix "
                "revision are measured"
            ),
            "character_measurement": (
                "exact for verified decoded current "
                "source substance"
            ),
            "line_measurement": (
                "exact for verified decoded current "
                "source substance using splitlines "
                "with line endings retained"
            ),
            "higher_tier_measurement": (
                "not calculated until authoritative "
                "composition boundaries exist"
            ),
            "reference_overhead_included": (
                False
            ),
        },
        "characters": characters,
        "lines": lines,
        "scripts": scripts,
        "unresolved_scripts": (
            unresolved_scripts
        ),
    }

    result[
        "digest"
    ] = projection_digest(
        result
    )

    return result


def command_project(
    source_path: Path,
    output_path: Path,
) -> int:
    source_path = (
        source_path.resolve()
    )

    output_path = (
        output_path.resolve()
    )

    source = (
        load_source_projection(
            source_path
        )
    )

    result = project(
        source
    )

    atomic_json(
        output_path,
        result,
    )

    summary = {
        "schema": (
            "savant.carbon.straub."
            "content-edifice-project.v1"
        ),
        "authority_effect": (
            "none"
        ),
        "projection_only": True,
        "output": str(
            output_path
        ),
        "digest": result[
            "digest"
        ],
        "source_file_count": result[
            "source_file_count"
        ],
        "source_metadata_bytes": result[
            "source_metadata_bytes"
        ],
        "verified_script_count": result[
            "verified_script_count"
        ],
        "unresolved_script_count": result[
            "unresolved_script_count"
        ],
        "verified_source_bytes": result[
            "verified_source_bytes"
        ],
        "verification": result[
            "verification"
        ],
        "directly_projectable_tiers": (
            result[
                "directly_projectable_tiers"
            ]
        ),
        "unresolved_tiers": [
            item[
                "tier"
            ]
            for item in result[
                "unresolved_tiers"
            ]
        ],
        "character": result[
            "composition"
        ][
            "character"
        ],
        "line": result[
            "composition"
        ][
            "line"
        ],
        "script": result[
            "composition"
        ][
            "script"
        ],
    }

    print(
        json.dumps(
            summary,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )

    return 0


def command_health() -> int:
    payload = {
        "schema": (
            "savant.carbon.straub."
            "content-edifice-health.v1"
        ),
        "status": "ok",
        "owner": owner,
        "module": module,
        "authority_effect": (
            "none"
        ),
        "projection_only": True,
        "source_projection": str(
            source_projection_path
        ),
        "source_projection_exists": (
            source_projection_path.is_file()
        ),
        "content_edifice": list(
            content_edifice
        ),
        "directly_projectable_tiers": list(
            directly_projectable_tiers
        ),
        "unresolved_tiers": list(
            unresolved_tiers
        ),
        "rehydration_policy": (
            "sha256-and-size-verified"
        ),
    }

    print(
        json.dumps(
            payload,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )

    return (
        0
        if source_projection_path.is_file()
        else 1
    )


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(
        prog=(
            "straub-content-edifice"
        )
    )

    commands = (
        result.add_subparsers(
            dest="command",
            required=True,
        )
    )

    project_parser = (
        commands.add_parser(
            "project"
        )
    )

    project_parser.add_argument(
        "--source",
        type=Path,
        default=(
            source_projection_path
        ),
    )

    project_parser.add_argument(
        "--output",
        type=Path,
        default=(
            default_output_path
        ),
    )

    commands.add_parser(
        "health"
    )

    return result


def main() -> int:
    arguments = (
        parser().parse_args()
    )

    if (
        arguments.command
        == "project"
    ):
        return command_project(
            arguments.source,
            arguments.output,
        )

    if (
        arguments.command
        == "health"
    ):
        return command_health()

    return 2


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
