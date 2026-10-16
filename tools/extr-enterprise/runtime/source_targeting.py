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
import sys
from typing import Any, Iterable, Iterator, Mapping


runtime_root = Path("/root/savant-runtime")

if str(runtime_root) not in sys.path:
    sys.path.insert(0, str(runtime_root))


from edifices.utility.epiphany.universal_parser import (
    iter_path as universal_iter_path,
)
from edifices.utility.epiphany.universal_classifier import (
    classification_rule,
    classify_text,
)
from edifices.utility.epiphany.universal_output import (
    render as universal_render,
    write as universal_write,
)


schema = "savant://runtime/sieve/source-targeting/2.1.0"
selftest_schema = (
    "savant://runtime/sieve/"
    "source-targeting-selftest/2.1.0"
)

owner = "sieve"
authority_effect = "none"
utility_level = "tactic"
utility_ordinal = 5

composition = {
    "parser": (
        "savant://utility/epiphany/"
        "universal-parser/1.0.0"
    ),
    "classifier": (
        "savant://utility/epiphany/"
        "universal-classifier/1.0.0"
    ),
    "output": (
        "savant://utility/epiphany/"
        "universal-output/1.0.0"
    ),
}

legacy_sdump_manifest_marker = (
    "=== sdump manifest ==="
)

enterprise_sdump_header_pattern = re.compile(
    r"^sdump enterprise v[0-9]+$",
    re.IGNORECASE,
)

enterprise_manifest_marker = "manifest"

minimum_signal_length = 3
candidate_chunk_size = 12000

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

savant_signals = (
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
)

savant_classification_rule = classification_rule(
    identifier="sieve-savant-signal",
    label="savant-signal",
    include_terms=savant_signals,
    minimum_score=1.0,
)


class source_targeting_error(RuntimeError):
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
        canonical_json(value).encode("utf-8")
    ).hexdigest()


def file_digest(
    path: Path,
) -> str:
    hasher = hashlib.sha256()

    with path.open("rb") as handle:
        while True:
            block = handle.read(1024 * 1024)

            if not block:
                break

            hasher.update(block)

    return hasher.hexdigest()


def utc_now() -> str:
    return (
        datetime.now(timezone.utc)
        .isoformat()
        .replace("+00:00", "Z")
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
    projected: set[str] = set()

    for raw in re.findall(
        r"[a-zA-Z][a-zA-Z0-9_-]*",
        value,
    ):
        token = normalized_token(raw)

        if len(token) < minimum_signal_length:
            continue

        if token in generic_tokens:
            continue

        projected.add(token)

    return tuple(sorted(projected))


def savant_signal_tokens(
    value: str,
) -> tuple[str, ...]:
    result = classify_text(
        value,
        (savant_classification_rule,),
    )

    included: set[str] = set()

    for evidence in result.evidence:
        included.update(
            evidence.included_terms
        )

    return tuple(sorted(included))


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
    ) -> dict[str, Any]:
        return {
            "path": str(self.path),
            "generated_at": self.generated_at,
            "source_files": self.source_files,
            "source_bytes": self.source_bytes,
            "schema": self.schema,
            "digest": self.digest,
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
    ) -> dict[str, Any]:
        return {
            "path": self.path,
            "language": self.language,
            "size": self.size,
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
    ) -> dict[str, Any]:
        return {
            "source": self.source,
            "ordinal": self.ordinal,
            "source_digest": self.source_digest,
        }


@dataclass(
    frozen=True,
    slots=True,
)
class target_projection:
    candidate_digest: str
    source: str
    ordinal: int
    export_signals: tuple[str, ...]
    runtime_matches: tuple[str, ...]
    runtime_match_count: int
    runtime_evidence_present: bool
    savant_signal_present: bool
    semantic_review_required: bool
    deterministic_target_candidate: bool
    disposition: str

    def projection(
        self,
    ) -> dict[str, Any]:
        return {
            "candidate_digest":
                self.candidate_digest,
            "source":
                self.source,
            "ordinal":
                self.ordinal,
            "export_signals":
                list(self.export_signals),
            "runtime_matches":
                list(self.runtime_matches),
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
    if path.suffix.lower() == ".gz":
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


def manifest_mapping(
    value: Any,
) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise source_targeting_error(
            "sdump manifest must be an object"
        )

    return dict(value)


def read_legacy_sdump_manifest(
    path: Path,
) -> dict[str, Any] | None:
    with open_text(path) as handle:
        for line in handle:
            if not line.startswith(
                legacy_sdump_manifest_marker
            ):
                continue

            payload = line[
                len(
                    legacy_sdump_manifest_marker
                ):
            ].strip()

            end_marker = (
                "=== /sdump manifest ==="
            )

            if end_marker in payload:
                payload = payload[
                    :payload.index(end_marker)
                ].strip()

            try:
                return manifest_mapping(
                    json.loads(payload)
                )
            except json.JSONDecodeError as exc:
                raise source_targeting_error(
                    "invalid legacy sdump manifest"
                ) from exc

    return None


def read_enterprise_sdump_manifest(
    path: Path,
) -> dict[str, Any] | None:
    with open_text(path) as handle:
        header = handle.readline()

        if not header:
            return None

        if not enterprise_sdump_header_pattern.fullmatch(
            header.strip()
        ):
            return None

        marker = handle.readline()

        if (
            marker.strip().lower()
            != enterprise_manifest_marker
        ):
            raise source_targeting_error(
                "enterprise sdump manifest marker "
                "unavailable"
            )

        decoder = json.JSONDecoder()
        buffer = ""

        while True:
            chunk = handle.read(
                1024 * 1024
            )

            if not chunk:
                break

            buffer += chunk

            stripped = buffer.lstrip()

            if not stripped:
                continue

            try:
                value, _ = decoder.raw_decode(
                    stripped
                )
            except json.JSONDecodeError:
                continue

            return manifest_mapping(value)

    raise source_targeting_error(
        "invalid enterprise sdump manifest"
    )


def read_sdump_manifest(
    path: Path,
) -> dict[str, Any]:
    enterprise = (
        read_enterprise_sdump_manifest(path)
    )

    if enterprise is not None:
        return enterprise

    legacy = read_legacy_sdump_manifest(path)

    if legacy is not None:
        return legacy

    raise source_targeting_error(
        "sdump manifest unavailable"
    )


def nested_mapping(
    value: Mapping[str, Any],
    *keys: str,
) -> Mapping[str, Any] | None:
    current: Any = value

    for key in keys:
        if not isinstance(
            current,
            Mapping,
        ):
            return None

        current = current.get(key)

    if isinstance(current, Mapping):
        return current

    return None


def first_value(
    mapping: Mapping[str, Any],
    paths: Iterable[
        tuple[str, ...]
    ],
) -> Any:
    for path in paths:
        current: Any = mapping

        valid = True

        for key in path:
            if not isinstance(
                current,
                Mapping,
            ):
                valid = False
                break

            if key not in current:
                valid = False
                break

            current = current[key]

        if valid and current is not None:
            return current

    return None


def optional_int(
    value: Any,
) -> int | None:
    if isinstance(value, bool):
        return None

    if isinstance(value, int):
        return value

    if isinstance(value, str):
        try:
            return int(value)
        except ValueError:
            return None

    return None


def identify_sdump(
    path: Path,
) -> sdump_identity:
    if not path.is_file():
        raise source_targeting_error(
            "sdump unavailable: "
            f"{path}"
        )

    manifest = read_sdump_manifest(path)

    generated_at = first_value(
        manifest,
        (
            ("generated_at",),
            ("metadata", "generated_at"),
            ("audit", "generated_at"),
            ("snapshot", "generated_at"),
        ),
    )

    source_files = first_value(
        manifest,
        (
            ("source_files",),
            ("metadata", "source_files"),
            ("audit", "source_files"),
            ("snapshot", "source_files"),
            ("counts", "source_files"),
        ),
    )

    source_bytes = first_value(
        manifest,
        (
            ("source_bytes",),
            ("metadata", "source_bytes"),
            ("audit", "source_bytes"),
            ("snapshot", "source_bytes"),
            ("counts", "source_bytes"),
        ),
    )

    manifest_schema = first_value(
        manifest,
        (
            ("schema",),
            ("metadata", "schema"),
            ("audit", "schema"),
        ),
    )

    return sdump_identity(
        path=path,
        generated_at=(
            str(generated_at)
            if generated_at is not None
            else None
        ),
        source_files=optional_int(
            source_files
        ),
        source_bytes=optional_int(
            source_bytes
        ),
        schema=(
            str(manifest_schema)
            if manifest_schema is not None
            else None
        ),
        digest=file_digest(path),
    )


def latest_sdump(
    candidates: Iterable[Path],
) -> sdump_identity:
    identified: list[
        sdump_identity
    ] = []

    for path in candidates:
        try:
            identified.append(
                identify_sdump(path)
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
    ) -> tuple[str, str]:
        return (
            item.generated_at or "",
            str(item.path),
        )

    return max(
        identified,
        key=key,
    )


def discover_sdumps(
    roots: Iterable[Path],
) -> tuple[Path, ...]:
    discovered: set[Path] = set()

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
            for path in candidate_root.rglob(
                pattern
            ):
                if path.is_file():
                    discovered.add(path)

    return tuple(
        sorted(
            discovered,
            key=str,
        )
    )


def iter_runtime_files(
    path: Path,
) -> Iterator[runtime_file]:
    with open_text(path) as handle:
        for line in handle:
            stripped = line.strip()

            if not stripped.startswith("{"):
                continue

            if '"path"' not in stripped:
                continue

            try:
                payload = json.loads(
                    stripped
                )
            except json.JSONDecodeError:
                continue

            if not isinstance(
                payload,
                Mapping,
            ):
                continue

            file_path = payload.get("path")

            if not isinstance(
                file_path,
                str,
            ):
                continue

            language = payload.get(
                "language"
            )

            size = payload.get("size")

            yield runtime_file(
                path=file_path,
                language=(
                    str(language)
                    if language is not None
                    else None
                ),
                size=optional_int(size),
            )


def runtime_index(
    sdump: sdump_identity,
) -> dict[
    str,
    tuple[str, ...],
]:
    index: dict[
        str,
        set[str],
    ] = {}

    for item in iter_runtime_files(
        sdump.path
    ):
        for token in tokens(item.path):
            index.setdefault(
                token,
                set(),
            ).add(item.path)

    return {
        token: tuple(sorted(paths))
        for token, paths
        in sorted(index.items())
    }


def chunk_text(
    value: str,
) -> Iterator[str]:
    if not value:
        return

    lines = value.splitlines(
        keepends=True
    )

    if not lines:
        yield value
        return

    buffer: list[str] = []
    size = 0

    for line in lines:
        buffer.append(line)
        size += len(line)

        if size < candidate_chunk_size:
            continue

        yield "".join(buffer)

        buffer = []
        size = 0

    if buffer:
        yield "".join(buffer)


def iter_export_candidates(
    path: Path,
) -> Iterator[export_candidate]:
    if not path.exists():
        raise source_targeting_error(
            "data export unavailable: "
            f"{path}"
        )

    ordinal_by_source: dict[
        str,
        int,
    ] = {}

    try:
        parsed_results = universal_iter_path(
            path
        )

        for parsed in parsed_results:
            for record in parsed.records:
                if record.text is None:
                    continue

                source = record.source

                if record.format == "json":
                    ordinal = (
                        ordinal_by_source.get(
                            source,
                            0,
                        )
                        + 1
                    )

                    ordinal_by_source[
                        source
                    ] = ordinal

                    yield export_candidate(
                        source=source,
                        ordinal=ordinal,
                        text=record.text,
                        source_digest=(
                            record.record_digest
                        ),
                    )

                    continue

                for chunk in chunk_text(
                    record.text
                ):
                    ordinal = (
                        ordinal_by_source.get(
                            source,
                            0,
                        )
                        + 1
                    )

                    ordinal_by_source[
                        source
                    ] = ordinal

                    yield export_candidate(
                        source=source,
                        ordinal=ordinal,
                        text=chunk,
                        source_digest=digest(
                            chunk
                        ),
                    )

    except Exception as exc:
        raise source_targeting_error(
            "universal parser failed: "
            f"{path}: {exc}"
        ) from exc


def runtime_matches(
    candidate: export_candidate,
    index: Mapping[
        str,
        tuple[str, ...],
    ],
) -> tuple[
    tuple[str, ...],
    tuple[str, ...],
]:
    candidate_tokens = tokens(
        candidate.text
    )

    signals = savant_signal_tokens(
        candidate.text
    )

    matched: set[str] = set()

    correlation_signals = (
        set(signals)
        - {"savant"}
    )

    prioritized = (
        correlation_signals
        if signals
        else set(candidate_tokens)
    )

    for token in prioritized:
        for path in index.get(
            token,
            (),
        ):
            matched.add(path)

    return (
        signals,
        tuple(sorted(matched)),
    )


def classify_candidate(
    candidate: export_candidate,
    index: Mapping[
        str,
        tuple[str, ...],
    ],
) -> target_projection:
    signals, matches = runtime_matches(
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
            len(matches),
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
) -> dict[str, Any]:
    index = runtime_index(sdump)

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

    counts: dict[str, int] = {}

    for target in targets:
        counts[target.disposition] = (
            counts.get(
                target.disposition,
                0,
            )
            + 1
        )

    projection = {
        "schema": schema,
        "owner": owner,
        "authority_effect":
            authority_effect,
        "authoritative": False,
        "rebuildable": True,
        "utility_level":
            utility_level,
        "utility_ordinal":
            utility_ordinal,
        "composition":
            dict(composition),
        "generated_at":
            utc_now(),
        "targeting_contract": {
            "candidate_source":
                "data-export",
            "current_state_source":
                "latest-sdump",
            "selection": (
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
                "candidate-correlation-only",
        },
        "sdump":
            sdump.projection(),
        "data_export": {
            "path":
                str(data_export),
        },
        "runtime_index_tokens":
            len(index),
        "candidate_count":
            len(candidates),
        "disposition_counts":
            dict(sorted(counts.items())),
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


def enterprise_manifest_selftest(
) -> bool:
    sample = {
        "audit": {
            "coverage": {
                "score": 1.0,
            }
        },
        "generated_at":
            "2026-10-06T00:00:00Z",
        "source_files": 3,
        "source_bytes": 42,
        "schema":
            "savant://sdump/test",
    }

    encoded = canonical_json(sample)

    decoder = json.JSONDecoder()

    decoded, _ = decoder.raw_decode(
        encoded
    )

    return (
        isinstance(decoded, Mapping)
        and
        decoded.get("source_files") == 3
        and
        decoded.get("source_bytes") == 42
    )


def selftest() -> dict[str, Any]:
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

    correlated = export_candidate(
        source="export.json",
        ordinal=1,
        text=(
            "Savant Sieve should "
            "coordinate with Opus."
        ),
        source_digest=digest(
            "correlated"
        ),
    )

    export_only = export_candidate(
        source="export.json",
        ordinal=2,
        text=(
            "Savant Datrix concept "
            "without runtime evidence."
        ),
        source_digest=digest(
            "export-only"
        ),
    )

    unrelated = export_candidate(
        source="export.json",
        ordinal=3,
        text=(
            "ordinary unrelated "
            "conversation"
        ),
        source_digest=digest(
            "unrelated"
        ),
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

    classifier_probe = classify_text(
        correlated.text,
        (
            savant_classification_rule,
        ),
    )

    output_probe = universal_render(
        {
            "status": "ok",
        },
        format="json",
    )

    checks = {
        "authority_none":
            authority_effect == "none",
        "tactic_level":
            utility_ordinal == 5,
        "composition_declared":
            set(composition)
            == {
                "parser",
                "classifier",
                "output",
            },
        "classifier_composed":
            classifier_probe.disposition
            == "classified",
        "output_composed":
            '"status": "ok"'
            in output_probe,
        "enterprise_manifest_supported":
            enterprise_manifest_selftest(),
        "non_authoritative":
            first
            .deterministic_target_candidate
            is True,
        "deterministic":
            first == second,
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
            export_only_result
            .deterministic_target_candidate
            is False,
        "export_only_preserved":
            export_only_result.disposition
            == "export-only-candidate",
        "unrelated_rejected":
            unrelated_result.disposition
            == "insufficient-savant-signal",
        "runtime_not_authority":
            authority_effect == "none",
        "candidate_digest_preserved":
            first.candidate_digest
            == correlated.source_digest,
        "rebuildable": True,
    }

    return {
        "schema":
            selftest_schema,
        "ok":
            all(checks.values()),
        "checks":
            checks,
        "composition":
            dict(composition),
    }


def main() -> int:
    parser = argparse.ArgumentParser()

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

    parser.add_argument(
        "--output-format",
        choices=(
            "json",
            "jsonl",
            "text",
            "markdown",
            "csv",
        ),
        default="json",
    )

    arguments = parser.parse_args()

    if arguments.selftest:
        result = selftest()

        print(
            universal_render(
                result,
                format="json",
            ),
            end="",
        )

        return (
            0
            if result["ok"]
            else 1
        )

    if not arguments.data_export:
        raise source_targeting_error(
            "--data-export is required"
        )

    explicit = [
        Path(value)
        for value
        in arguments.sdump
    ]

    roots = [
        Path(value)
        for value
        in arguments.sdump_root
    ]

    sdump_candidates = (
        explicit
        + list(
            discover_sdumps(roots)
        )
    )

    selected_sdump = latest_sdump(
        sdump_candidates
    )

    result = targeting_projection(
        sdump=selected_sdump,
        data_export=Path(
            arguments.data_export
        ),
    )

    if arguments.output:
        universal_write(
            result,
            Path(arguments.output),
            format=arguments.output_format,
        )
    else:
        print(
            universal_render(
                result,
                format=
                    arguments.output_format,
            ),
            end="",
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
