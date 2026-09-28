#!/usr/bin/env python3

from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime, timezone
import gzip
import hashlib
import json
from pathlib import Path
import re
from typing import Any, Iterable, Iterator, Mapping


schema = (
    "savant://runtime/sieve/"
    "source-targeting/1.0.0"
)

selftest_schema = (
    "savant://runtime/sieve/"
    "source-targeting-selftest/1.0.0"
)

owner = "sieve"
authority_effect = "none"

sdump_manifest_marker = (
    "=== sdump manifest ==="
)

sdump_file_marker = (
    "=== file ==="
)

sdump_content_marker = (
    "=== content ==="
)

sdump_end_file_marker = (
    "=== /file ==="
)

minimum_signal_length = 3

generic_tokens = frozenset(
    {
        "about",
        "after",
        "again",
        "also",
        "another",
        "because",
        "before",
        "being",
        "between",
        "could",
        "does",
        "each",
        "from",
        "have",
        "into",
        "more",
        "must",
        "only",
        "other",
        "should",
        "some",
        "such",
        "than",
        "that",
        "their",
        "there",
        "these",
        "they",
        "this",
        "those",
        "through",
        "under",
        "using",
        "very",
        "what",
        "when",
        "where",
        "which",
        "while",
        "with",
        "would",
    }
)


class source_targeting_error(
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
        separators=(",", ":"),
        default=str,
    )


def digest(
    value: Any,
) -> str:
    return hashlib.sha256(
        canonical_json(
            value
        ).encode(
            "utf-8"
        )
    ).hexdigest()


def file_digest(
    path: Path,
) -> str:
    hasher = hashlib.sha256()

    with path.open(
        "rb"
    ) as handle:
        while True:
            block = handle.read(
                1024 * 1024
            )

            if not block:
                break

            hasher.update(
                block
            )

    return hasher.hexdigest()


def utc_now(
) -> str:
    return (
        datetime.now(
            timezone.utc
        )
        .isoformat()
        .replace(
            "+00:00",
            "Z",
        )
    )


def normalized_token(
    value: str,
) -> str:
    return re.sub(
        r"[^a-z0-9_-]+",
        "",
        value.lower(),
    )


def tokens(
    value: str,
) -> tuple[str, ...]:
    projected: set[
        str
    ] = set()

    for raw in re.findall(
        r"[a-zA-Z][a-zA-Z0-9_-]*",
        value,
    ):
        token = normalized_token(
            raw
        )

        if (
            len(token)
            < minimum_signal_length
        ):
            continue

        if token in generic_tokens:
            continue

        projected.add(
            token
        )

    return tuple(
        sorted(
            projected
        )
    )


def savant_signal_tokens(
    value: str,
) -> tuple[str, ...]:
    projected = set(
        tokens(
            value
        )
    )

    explicit = {
        "savant",
        "sieve",
        "datrix",
        "opus",
        "niche",
        "palaver",
        "envoy",
        "urge",
        "praxis",
        "praxi",
        "rigor",
        "thrust",
        "modus",
        "lexicon",
        "glyph",
        "iota",
        "spasm",
        "vagary",
        "epiphany",
        "tactic",
        "artifice",
        "agenda",
        "oeuvre",
        "edifice",
        "segue",
        "exile",
        "prodigal",
        "obelisks",
    }

    return tuple(
        sorted(
            projected
            & explicit
        )
    )


@dataclass(
    frozen=True,
    slots=True,
)
class sdump_identity:
    path: Path
    generated_at: str | None
    source_files: int | None
    source_bytes: int | None
    schema: str | None
    digest: str

    def projection(
        self,
    ) -> dict[
        str,
        Any,
    ]:
        return {
            "path":
                str(
                    self.path
                ),
            "generated_at":
                self.generated_at,
            "source_files":
                self.source_files,
            "source_bytes":
                self.source_bytes,
            "schema":
                self.schema,
            "digest":
                self.digest,
        }


@dataclass(
    frozen=True,
    slots=True,
)
class runtime_file:
    path: str
    language: str | None
    size: int | None

    def projection(
        self,
    ) -> dict[
        str,
        Any,
    ]:
        return {
            "path":
                self.path,
            "language":
                self.language,
            "size":
                self.size,
        }


@dataclass(
    frozen=True,
    slots=True,
)
class export_candidate:
    source: str
    ordinal: int
    text: str
    source_digest: str

    def projection(
        self,
    ) -> dict[
        str,
        Any,
    ]:
        return {
            "source":
                self.source,
            "ordinal":
                self.ordinal,
            "source_digest":
                self.source_digest,
        }


@dataclass(
    frozen=True,
    slots=True,
)
class target_projection:
    candidate_digest: str
    source: str
    ordinal: int
    export_signals: tuple[
        str,
        ...,
    ]
    runtime_matches: tuple[
        str,
        ...,
    ]
    runtime_match_count: int
    runtime_evidence_present: bool
    savant_signal_present: bool
    semantic_review_required: bool
    deterministic_target_candidate: bool
    disposition: str

    def projection(
        self,
    ) -> dict[
        str,
        Any,
    ]:
        return {
            "candidate_digest":
                self.candidate_digest,
            "source":
                self.source,
            "ordinal":
                self.ordinal,
            "export_signals":
                list(
                    self.export_signals
                ),
            "runtime_matches":
                list(
                    self.runtime_matches
                ),
            "runtime_match_count":
                self.runtime_match_count,
            "runtime_evidence_present":
                self.runtime_evidence_present,
            "savant_signal_present":
                self.savant_signal_present,
            "semantic_review_required":
                self.semantic_review_required,
            "deterministic_target_candidate":
                self.deterministic_target_candidate,
            "disposition":
                self.disposition,
        }


def open_text(
    path: Path,
):
    if (
        path.suffix.lower()
        == ".gz"
    ):
        return gzip.open(
            path,
            "rt",
            encoding="utf-8",
            errors="replace",
        )

    return path.open(
        "r",
        encoding="utf-8",
        errors="replace",
    )


def read_sdump_manifest(
    path: Path,
) -> dict[
    str,
    Any,
]:
    with open_text(
        path
    ) as handle:
        for line in handle:
            if not line.startswith(
                sdump_manifest_marker
            ):
                continue

            payload = line[
                len(
                    sdump_manifest_marker
                ):
            ].strip()

            if payload.endswith(
                "=== /sdump manifest ==="
            ):
                payload = payload[
                    :payload.index(
                        "=== /sdump manifest ==="
                    )
                ].strip()

            try:
                value = json.loads(
                    payload
                )
            except json.JSONDecodeError as exc:
                raise source_targeting_error(
                    "invalid sdump manifest"
                ) from exc

            if not isinstance(
                value,
                Mapping,
            ):
                raise source_targeting_error(
                    "sdump manifest must "
                    "be an object"
                )

            return dict(
                value
            )

    raise source_targeting_error(
        "sdump manifest unavailable"
    )


def identify_sdump(
    path: Path,
) -> sdump_identity:
    if not path.is_file():
        raise source_targeting_error(
            "sdump unavailable: "
            f"{path}"
        )

    manifest = (
        read_sdump_manifest(
            path
        )
    )

    generated_at = (
        manifest.get(
            "generated_at"
        )
    )

    source_files = (
        manifest.get(
            "source_files"
        )
    )

    source_bytes = (
        manifest.get(
            "source_bytes"
        )
    )

    manifest_schema = (
        manifest.get(
            "schema"
        )
    )

    return sdump_identity(
        path=path,
        generated_at=(
            str(
                generated_at
            )
            if generated_at
            is not None
            else None
        ),
        source_files=(
            int(
                source_files
            )
            if isinstance(
                source_files,
                int,
            )
            else None
        ),
        source_bytes=(
            int(
                source_bytes
            )
            if isinstance(
                source_bytes,
                int,
            )
            else None
        ),
        schema=(
            str(
                manifest_schema
            )
            if manifest_schema
            is not None
            else None
        ),
        digest=file_digest(
            path
        ),
    )


def latest_sdump(
    candidates: Iterable[
        Path
    ],
) -> sdump_identity:
    identified: list[
        sdump_identity
    ] = []

    for path in candidates:
        try:
            identified.append(
                identify_sdump(
                    path
                )
            )
        except (
            OSError,
            source_targeting_error,
        ):
            continue

    if not identified:
        raise source_targeting_error(
            "no valid sdump candidates"
        )

    def key(
        item: sdump_identity,
    ) -> tuple[
        str,
        str,
    ]:
        return (
            item.generated_at
            or "",
            str(
                item.path
            ),
        )

    return max(
        identified,
        key=key,
    )


def discover_sdumps(
    roots: Iterable[
        Path
    ],
) -> tuple[
    Path,
    ...,
]:
    discovered: set[
        Path
    ] = set()

    for candidate_root in roots:
        if candidate_root.is_file():
            discovered.add(
                candidate_root
            )
            continue

        if not candidate_root.is_dir():
            continue

        for pattern in (
            "sdump*.txt",
            "sdump*.txt.gz",
        ):
            for path in (
                candidate_root.glob(
                    pattern
                )
            ):
                if path.is_file():
                    discovered.add(
                        path
                    )

    return tuple(
        sorted(
            discovered,
            key=str,
        )
    )


def iter_runtime_files(
    path: Path,
) -> Iterator[
    runtime_file
]:
    with open_text(
        path
    ) as handle:
        for line in handle:
            if not line.startswith(
                "{"
            ):
                continue

            if (
                '"path"'
                not in line
            ):
                continue

            try:
                payload = json.loads(
                    line
                )
            except json.JSONDecodeError:
                continue

            if not isinstance(
                payload,
                Mapping,
            ):
                continue

            file_path = payload.get(
                "path"
            )

            if not isinstance(
                file_path,
                str,
            ):
                continue

            language = payload.get(
                "language"
            )

            size = payload.get(
                "size"
            )

            yield runtime_file(
                path=file_path,
                language=(
                    str(
                        language
                    )
                    if language
                    is not None
                    else None
                ),
                size=(
                    int(
                        size
                    )
                    if isinstance(
                        size,
                        int,
                    )
                    else None
                ),
            )


def runtime_index(
    sdump: sdump_identity,
) -> dict[
    str,
    tuple[
        str,
        ...,
    ],
]:
    index: dict[
        str,
        set[
            str
        ],
    ] = {}

    for item in iter_runtime_files(
        sdump.path
    ):
        for token in tokens(
            item.path
        ):
            index.setdefault(
                token,
                set(),
            ).add(
                item.path
            )

    return {
        token: tuple(
            sorted(
                paths
            )
        )
        for (
            token,
            paths,
        )
        in sorted(
            index.items()
        )
    }


def text_from_json(
    value: Any,
) -> str:
    fragments: list[
        str
    ] = []

    def visit(
        item: Any,
    ) -> None:
        if isinstance(
            item,
            str,
        ):
            fragments.append(
                item
            )
            return

        if isinstance(
            item,
            Mapping,
        ):
            for (
                key,
                nested,
            ) in item.items():
                fragments.append(
                    str(
                        key
                    )
                )
                visit(
                    nested
                )
            return

        if isinstance(
            item,
            list,
        ):
            for nested in item:
                visit(
                    nested
                )
            return

        if item is not None:
            fragments.append(
                str(
                    item
                )
            )

    visit(
        value
    )

    return "\n".join(
        fragments
    )


def iter_json_candidates(
    path: Path,
) -> Iterator[
    export_candidate
]:
    try:
        value = json.loads(
            path.read_text(
                encoding="utf-8",
                errors="replace",
            )
        )
    except (
        OSError,
        json.JSONDecodeError,
    ):
        return

    records: list[
        Any
    ]

    if isinstance(
        value,
        list,
    ):
        records = value
    else:
        records = [
            value
        ]

    for ordinal, record in enumerate(
        records,
        1,
    ):
        text = text_from_json(
            record
        )

        yield export_candidate(
            source=str(
                path
            ),
            ordinal=ordinal,
            text=text,
            source_digest=digest(
                record
            ),
        )


def iter_text_candidates(
    path: Path,
) -> Iterator[
    export_candidate
]:
    try:
        with path.open(
            "r",
            encoding="utf-8",
            errors="replace",
        ) as handle:
            ordinal = 0
            buffer: list[
                str
            ] = []
            size = 0

            for line in handle:
                buffer.append(
                    line
                )
                size += len(
                    line
                )

                if size < 12000:
                    continue

                ordinal += 1

                text = "".join(
                    buffer
                )

                yield export_candidate(
                    source=str(
                        path
                    ),
                    ordinal=ordinal,
                    text=text,
                    source_digest=digest(
                        text
                    ),
                )

                buffer = []
                size = 0

            if buffer:
                ordinal += 1

                text = "".join(
                    buffer
                )

                yield export_candidate(
                    source=str(
                        path
                    ),
                    ordinal=ordinal,
                    text=text,
                    source_digest=digest(
                        text
                    ),
                )

    except OSError:
        return


def iter_export_candidates(
    path: Path,
) -> Iterator[
    export_candidate
]:
    if not path.exists():
        raise source_targeting_error(
            "data export unavailable: "
            f"{path}"
        )

    paths: list[
        Path
    ]

    if path.is_file():
        paths = [
            path
        ]
    else:
        paths = sorted(
            (
                item
                for item
                in path.rglob("*")
                if item.is_file()
            ),
            key=str,
        )

    for item in paths:
        suffix = (
            item.suffix.lower()
        )

        if suffix == ".json":
            yield from (
                iter_json_candidates(
                    item
                )
            )
            continue

        if suffix in {
            ".txt",
            ".md",
            ".jsonl",
            ".html",
            ".htm",
            ".csv",
            ".yaml",
            ".yml",
        }:
            yield from (
                iter_text_candidates(
                    item
                )
            )


def runtime_matches(
    candidate: export_candidate,
    index: Mapping[
        str,
        tuple[
            str,
            ...,
        ],
    ],
) -> tuple[
    tuple[
        str,
        ...,
    ],
    tuple[
        str,
        ...,
    ],
]:
    candidate_tokens = tokens(
        candidate.text
    )

    signals = (
        savant_signal_tokens(
            candidate.text
        )
    )

    matched: set[
        str
    ] = set()

    prioritized = (
        set(
            signals
        )
        or set(
            candidate_tokens
        )
    )

    for token in prioritized:
        for path in index.get(
            token,
            (),
        ):
            matched.add(
                path
            )

    return (
        signals,
        tuple(
            sorted(
                matched
            )
        ),
    )


def classify_candidate(
    candidate: export_candidate,
    index: Mapping[
        str,
        tuple[
            str,
            ...,
        ],
    ],
) -> target_projection:
    (
        signals,
        matches,
    ) = runtime_matches(
        candidate,
        index,
    )

    savant_signal_present = bool(
        signals
    )

    runtime_evidence_present = bool(
        matches
    )

    deterministic_target_candidate = (
        savant_signal_present
        and runtime_evidence_present
    )

    if deterministic_target_candidate:
        disposition = (
            "runtime-correlated-candidate"
        )
    elif savant_signal_present:
        disposition = (
            "export-only-candidate"
        )
    else:
        disposition = (
            "insufficient-savant-signal"
        )

    return target_projection(
        candidate_digest=
            candidate.source_digest,
        source=
            candidate.source,
        ordinal=
            candidate.ordinal,
        export_signals=
            signals,
        runtime_matches=
            matches,
        runtime_match_count=
            len(
                matches
            ),
        runtime_evidence_present=
            runtime_evidence_present,
        savant_signal_present=
            savant_signal_present,
        semantic_review_required=
            deterministic_target_candidate,
        deterministic_target_candidate=
            deterministic_target_candidate,
        disposition=
            disposition,
    )


def targeting_projection(
    *,
    sdump: sdump_identity,
    data_export: Path,
) -> dict[
    str,
    Any,
]:
    index = runtime_index(
        sdump
    )

    candidates = list(
        iter_export_candidates(
            data_export
        )
    )

    targets = [
        classify_candidate(
            candidate,
            index,
        )
        for candidate
        in candidates
    ]

    counts: dict[
        str,
        int,
    ] = {}

    for target in targets:
        counts[
            target.disposition
        ] = (
            counts.get(
                target.disposition,
                0,
            )
            + 1
        )

    projection = {
        "schema":
            schema,
        "owner":
            owner,
        "authority_effect":
            authority_effect,
        "authoritative":
            False,
        "rebuildable":
            True,
        "generated_at":
            utc_now(),
        "targeting_contract": {
            "candidate_source":
                "data-export",
            "current_state_source":
                "latest-sdump",
            "selection":
                (
                    "data-export-candidates"
                    "-cross-referenced-with-"
                    "latest-sdump"
                ),
            "data_export_alone_sufficient":
                False,
            "sdump_alone_sufficient":
                False,
            "semantic_targeting":
                "requires-verified-opus-binding",
            "deterministic_stage":
                (
                    "candidate-correlation-only"
                ),
        },
        "sdump":
            sdump.projection(),
        "data_export": {
            "path":
                str(
                    data_export
                ),
        },
        "runtime_index_tokens":
            len(
                index
            ),
        "candidate_count":
            len(
                candidates
            ),
        "disposition_counts":
            dict(
                sorted(
                    counts.items()
                )
            ),
        "targets": [
            target.projection()
            for target
            in targets
        ],
    }

    digest_projection = dict(
        projection
    )

    digest_projection.pop(
        "generated_at",
        None,
    )

    projection[
        "projection_digest"
    ] = digest(
        digest_projection
    )

    return projection


def selftest(
) -> dict[
    str,
    Any,
]:
    index = {
        "savant": (
            "runtime/savant.py",
        ),
        "sieve": (
            "tools/sieve.py",
        ),
        "opus": (
            "edifices/identity/"
            "exiles/opus/runtime.py",
        ),
    }

    correlated = (
        export_candidate(
            source="export.json",
            ordinal=1,
            text=(
                "Savant Sieve should "
                "coordinate with Opus."
            ),
            source_digest=
                digest(
                    "correlated"
                ),
        )
    )

    export_only = (
        export_candidate(
            source="export.json",
            ordinal=2,
            text=(
                "Savant Datrix concept "
                "without runtime evidence."
            ),
            source_digest=
                digest(
                    "export-only"
                ),
        )
    )

    unrelated = (
        export_candidate(
            source="export.json",
            ordinal=3,
            text=(
                "ordinary unrelated "
                "conversation"
            ),
            source_digest=
                digest(
                    "unrelated"
                ),
        )
    )

    first = classify_candidate(
        correlated,
        index,
    )

    second = classify_candidate(
        correlated,
        index,
    )

    export_only_result = (
        classify_candidate(
            export_only,
            index,
        )
    )

    unrelated_result = (
        classify_candidate(
            unrelated,
            index,
        )
    )

    checks = {
        "authority_none":
            authority_effect
            == "none",
        "non_authoritative":
            first.projection()[
                "deterministic_target_candidate"
            ]
            is True,
        "deterministic":
            first
            == second,
        "dual_evidence":
            (
                first.savant_signal_present
                and
                first.runtime_evidence_present
            ),
        "runtime_correlated":
            first.disposition
            == (
                "runtime-correlated-candidate"
            ),
        "semantic_review_required":
            first.semantic_review_required
            is True,
        "export_only_not_final":
            (
                export_only_result
                .deterministic_target_candidate
                is False
            ),
        "export_only_preserved":
            export_only_result.disposition
            == "export-only-candidate",
        "unrelated_rejected":
            unrelated_result.disposition
            == "insufficient-savant-signal",
        "runtime_not_authority":
            authority_effect
            == "none",
        "candidate_digest_preserved":
            first.candidate_digest
            == correlated.source_digest,
        "rebuildable":
            True,
    }

    return {
        "schema":
            selftest_schema,
        "ok":
            all(
                checks.values()
            ),
        "checks":
            checks,
    }


def main() -> int:
    parser = (
        argparse.ArgumentParser()
    )

    parser.add_argument(
        "--selftest",
        action="store_true",
    )

    parser.add_argument(
        "--sdump",
        action="append",
        default=[],
    )

    parser.add_argument(
        "--sdump-root",
        action="append",
        default=[],
    )

    parser.add_argument(
        "--data-export",
    )

    parser.add_argument(
        "--output",
    )

    arguments = (
        parser.parse_args()
    )

    if arguments.selftest:
        result = selftest()

        print(
            json.dumps(
                result,
                ensure_ascii=False,
                sort_keys=True,
                indent=2,
            )
        )

        return (
            0
            if result[
                "ok"
            ]
            else 1
        )

    if not arguments.data_export:
        raise source_targeting_error(
            "--data-export is required"
        )

    explicit = [
        Path(
            value
        )
        for value
        in arguments.sdump
    ]

    roots = [
        Path(
            value
        )
        for value
        in arguments.sdump_root
    ]

    sdump_candidates = (
        explicit
        + list(
            discover_sdumps(
                roots
            )
        )
    )

    selected_sdump = (
        latest_sdump(
            sdump_candidates
        )
    )

    result = (
        targeting_projection(
            sdump=selected_sdump,
            data_export=Path(
                arguments.data_export
            ),
        )
    )

    encoded = json.dumps(
        result,
        ensure_ascii=False,
        sort_keys=True,
        indent=2,
    )

    if arguments.output:
        output = Path(
            arguments.output
        )

        output.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        output.write_text(
            encoded + "\n",
            encoding="utf-8",
        )
    else:
        print(
            encoded
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
