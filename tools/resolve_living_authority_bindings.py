#!/usr/bin/env python3

from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any, Iterator


ROOT = Path("/root/savant-runtime")

LIVING_STATE = (
    ROOT
    / "runtime"
    / "living-state"
    / "current.json"
)

DOCTRINE_CANDIDATE = (
    ROOT
    / "canon"
    / "living"
    / "savant_bible.md"
)

OUTPUT_ROOT = (
    ROOT
    / "audit"
    / "authority-input-resolution"
)

OUTPUT_JSON = (
    OUTPUT_ROOT
    / "living_authority_bindings.json"
)

MAX_MATCHES_PER_TARGET = 500

TARGETS = {
    "master_doctrine": (
        "master_doctrine",
        "master-doctrine",
        "master doctrine",
        "savant_bible",
        "savant bible",
    ),
    "construction_constitution": (
        "construction_constitution",
        "construction-constitution",
        "construction constitution",
        "chat_rules",
        "chat-rules",
        "chat rules",
    ),
}

PATH_RE = re.compile(
    r"""
    (?:
        /
        [A-Za-z0-9._()\-]+
    )+
    |
    (?:
        [A-Za-z0-9._()\-]+/
    )+
    [A-Za-z0-9._()\-]+
    """,
    re.VERBOSE,
)


def sha256_file(
    path: Path,
) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as handle:
        while True:
            chunk = handle.read(
                1024 * 1024
            )

            if not chunk:
                break

            digest.update(chunk)

    return digest.hexdigest()


def load_json(
    path: Path,
) -> Any:
    with path.open(
        "r",
        encoding="utf-8",
    ) as handle:
        return json.load(handle)


def normalized(
    value: str,
) -> str:
    return re.sub(
        r"\s+",
        " ",
        value.lower(),
    ).strip()


def contains_target_term(
    value: str,
    terms: tuple[str, ...],
) -> list[str]:
    haystack = normalized(value)

    return [
        term
        for term in terms
        if normalized(term) in haystack
    ]


def path_candidates_from_string(
    value: str,
) -> list[str]:
    candidates: list[str] = []

    for match in PATH_RE.finditer(
        value
    ):
        candidate = match.group(0).strip()

        if not candidate:
            continue

        if candidate not in candidates:
            candidates.append(candidate)

    return candidates


def resolve_path_candidate(
    candidate: str,
) -> dict[str, Any]:
    original = candidate

    path = Path(candidate)

    possibilities: list[Path] = []

    if path.is_absolute():
        possibilities.append(path)

    else:
        possibilities.append(
            ROOT / path
        )

    resolved_existing = None

    for possibility in possibilities:
        try:
            if possibility.is_file():
                resolved_existing = possibility
                break
        except OSError:
            continue

    result: dict[str, Any] = {
        "reported": original,
        "resolved_existing_file": None,
        "bytes": None,
        "sha256": None,
    }

    if resolved_existing is not None:
        result[
            "resolved_existing_file"
        ] = str(
            resolved_existing
        )

        stat = resolved_existing.stat()

        result["bytes"] = stat.st_size
        result["sha256"] = sha256_file(
            resolved_existing
        )

    return result


def walk(
    value: Any,
    location: str = "$",
) -> Iterator[
    tuple[str, str | None, Any]
]:
    if isinstance(value, dict):
        for key, child in value.items():
            child_location = (
                f"{location}.{key}"
            )

            yield (
                child_location,
                str(key),
                child,
            )

            yield from walk(
                child,
                child_location,
            )

    elif isinstance(value, list):
        for index, child in enumerate(
            value
        ):
            child_location = (
                f"{location}[{index}]"
            )

            yield (
                child_location,
                None,
                child,
            )

            yield from walk(
                child,
                child_location,
            )


def scalar_text(
    value: Any,
) -> str | None:
    if isinstance(value, str):
        return value

    if isinstance(
        value,
        (
            int,
            float,
            bool,
        ),
    ):
        return str(value)

    return None


def target_matches(
    document: Any,
    terms: tuple[str, ...],
) -> list[dict[str, Any]]:
    matches: list[dict[str, Any]] = []

    seen: set[
        tuple[str, str, str]
    ] = set()

    for location, key, value in walk(
        document
    ):
        key_text = key or ""
        value_text = scalar_text(
            value
        )

        key_hits = contains_target_term(
            key_text,
            terms,
        )

        value_hits: list[str] = []

        if value_text is not None:
            value_hits = contains_target_term(
                value_text,
                terms,
            )

        if not key_hits and not value_hits:
            continue

        rendered_value: Any

        if value_text is not None:
            rendered_value = value_text[
                :4000
            ]
        elif isinstance(value, dict):
            rendered_value = {
                str(k): (
                    v[:1000]
                    if isinstance(v, str)
                    else v
                )
                for k, v in list(
                    value.items()
                )[:30]
                if isinstance(
                    v,
                    (
                        str,
                        int,
                        float,
                        bool,
                        type(None),
                    ),
                )
            }
        elif isinstance(value, list):
            rendered_value = [
                item[:1000]
                if isinstance(item, str)
                else item
                for item in value[:30]
                if isinstance(
                    item,
                    (
                        str,
                        int,
                        float,
                        bool,
                        type(None),
                    ),
                )
            ]
        else:
            rendered_value = (
                str(value)[:4000]
            )

        paths: list[
            dict[str, Any]
        ] = []

        path_source_strings = [
            key_text,
        ]

        if value_text is not None:
            path_source_strings.append(
                value_text
            )

        for source_string in (
            path_source_strings
        ):
            for candidate in (
                path_candidates_from_string(
                    source_string
                )
            ):
                resolved = (
                    resolve_path_candidate(
                        candidate
                    )
                )

                if resolved not in paths:
                    paths.append(
                        resolved
                    )

        identity = (
            location,
            ",".join(
                sorted(
                    set(
                        key_hits
                        + value_hits
                    )
                )
            ),
            json.dumps(
                rendered_value,
                ensure_ascii=False,
                sort_keys=True,
                default=str,
            ),
        )

        if identity in seen:
            continue

        seen.add(identity)

        matches.append(
            {
                "location": location,
                "key": key,
                "matched_terms": sorted(
                    set(
                        key_hits
                        + value_hits
                    )
                ),
                "value": rendered_value,
                "path_candidates": paths,
            }
        )

        if (
            len(matches)
            >= MAX_MATCHES_PER_TARGET
        ):
            break

    return matches


def direct_candidate_record(
    path: Path,
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "path": str(path),
        "exists": path.is_file(),
        "bytes": None,
        "sha256": None,
        "authority_status": (
            "unresolved"
        ),
    }

    if path.is_file():
        result["bytes"] = (
            path.stat().st_size
        )
        result["sha256"] = (
            sha256_file(path)
        )

    return result


def collect_existing_paths(
    matches: list[
        dict[str, Any]
    ],
) -> list[
    dict[str, Any]
]:
    results: dict[
        str,
        dict[str, Any],
    ] = {}

    for match in matches:
        for candidate in match.get(
            "path_candidates",
            [],
        ):
            resolved = candidate.get(
                "resolved_existing_file"
            )

            if not isinstance(
                resolved,
                str,
            ):
                continue

            if resolved in results:
                continue

            results[resolved] = {
                "path": resolved,
                "bytes": candidate.get(
                    "bytes"
                ),
                "sha256": candidate.get(
                    "sha256"
                ),
                "authority_status": (
                    "unresolved"
                ),
            }

    return [
        results[key]
        for key in sorted(results)
    ]


def main() -> int:
    if not LIVING_STATE.is_file():
        print(
            "living-state projection "
            f"does not exist: {LIVING_STATE}",
            file=sys.stderr,
        )
        return 1

    try:
        document = load_json(
            LIVING_STATE
        )

    except (
        OSError,
        json.JSONDecodeError,
    ) as exc:
        print(
            "unable to read living-state "
            f"projection: {exc}",
            file=sys.stderr,
        )
        return 1

    target_results: dict[
        str,
        dict[str, Any],
    ] = {}

    for target, terms in (
        TARGETS.items()
    ):
        matches = target_matches(
            document,
            terms,
        )

        target_results[target] = {
            "match_count": len(
                matches
            ),
            "matches": matches,
            "existing_files_referenced": (
                collect_existing_paths(
                    matches
                )
            ),
        }

    summary = {
        "schema_version": "1.0.0",
        "living_state": {
            "path": str(
                LIVING_STATE
            ),
            "bytes": (
                LIVING_STATE.stat().st_size
            ),
            "sha256": sha256_file(
                LIVING_STATE
            ),
        },
        "known_doctrine_candidate": (
            direct_candidate_record(
                DOCTRINE_CANDIDATE
            )
        ),
        "targets": target_results,
        "authority_effect": "none",
        "authority_note": (
            "this report resolves explicit "
            "living-state references and "
            "existing filesystem targets. "
            "it does not grant authority "
            "based on filesystem presence."
        ),
    }

    OUTPUT_ROOT.mkdir(
        parents=True,
        exist_ok=True,
    )

    OUTPUT_JSON.write_text(
        json.dumps(
            summary,
            indent=2,
            ensure_ascii=False,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    print(
        json.dumps(
            summary,
            indent=2,
            ensure_ascii=False,
            sort_keys=True,
        )
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
