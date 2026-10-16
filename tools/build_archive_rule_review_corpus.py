#!/usr/bin/env python3

from __future__ import annotations

import hashlib
import json
import re
import sqlite3
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterator


ARCHIVE_ROOT = Path(
    "/root/savant-runtime/audit/archive-rule-extraction/"
    "ae2420cc26989b23f18f3dd579c69f2c9c8d9d107d90793173cf4f8fe74af1af"
)

DATABASE = ARCHIVE_ROOT / "reduced/reduction.sqlite3"

SOURCE_RESOLUTION = (
    ARCHIVE_ROOT
    / "resolved-sources"
    / "explicit_rule_sources.jsonl"
)

OUTPUT_ROOT = (
    ARCHIVE_ROOT
    / "review-corpus"
)

REVIEW_JSONL = (
    OUTPUT_ROOT
    / "rule_review_corpus.jsonl"
)

CONFLICT_JSONL = (
    OUTPUT_ROOT
    / "potential_conflicts.jsonl"
)

SUMMARY_JSON = (
    OUTPUT_ROOT
    / "summary.json"
)

SCHEMA_VERSION = "1.0.0"

MAX_TEXT_CHARS = 65536
MAX_SOURCE_OCCURRENCES = 100

NEGATION_RE = re.compile(
    r"""
    \b(
        not |
        never |
        no |
        cannot |
        can't |
        must\s+not |
        shall\s+not |
        should\s+not |
        prohibited |
        forbidden |
        disallow |
        disallowed |
        reject |
        rejected |
        remove |
        removed |
        delete |
        deleted
    )\b
    """,
    re.IGNORECASE | re.VERBOSE,
)

MODAL_RE = re.compile(
    r"""
    \b(
        must |
        shall |
        should |
        may |
        can |
        cannot |
        never |
        always |
        only |
        required |
        prohibited |
        forbidden |
        preserve |
        supersede |
        immutable |
        deterministic
    )\b
    """,
    re.IGNORECASE | re.VERBOSE,
)

WORD_RE = re.compile(
    r"[a-z][a-z0-9_-]{2,}",
    re.IGNORECASE,
)

STOP_WORDS = {
    "the",
    "and",
    "for",
    "that",
    "this",
    "with",
    "from",
    "into",
    "are",
    "was",
    "were",
    "been",
    "being",
    "have",
    "has",
    "had",
    "will",
    "would",
    "could",
    "should",
    "must",
    "shall",
    "may",
    "might",
    "can",
    "cannot",
    "not",
    "never",
    "always",
    "only",
    "all",
    "any",
    "each",
    "every",
    "its",
    "their",
    "there",
    "then",
    "than",
    "when",
    "where",
    "which",
    "while",
    "what",
    "who",
    "how",
    "why",
    "you",
    "your",
    "they",
    "them",
    "our",
    "out",
    "use",
    "used",
    "using",
    "make",
    "made",
    "does",
    "did",
    "done",
    "same",
    "such",
    "also",
    "more",
    "most",
    "other",
    "over",
    "under",
    "between",
    "within",
    "without",
    "before",
    "after",
    "because",
    "through",
    "about",
}

CORE_TERMS = {
    "authority",
    "authoritative",
    "precedence",
    "decision",
    "decisions",
    "constitutional",
    "constitution",
    "canon",
    "canonical",
    "evidence",
    "admission",
    "admitted",
    "provenance",
    "lineage",
    "immutable",
    "supersede",
    "superseded",
    "glyph",
    "instance",
    "instances",
    "composition",
    "compose",
    "projection",
    "project",
    "segue",
    "segues",
    "dependency",
    "dependencies",
    "owner",
    "ownership",
    "responsibility",
    "mutation",
    "migration",
    "validation",
    "verification",
    "deterministic",
    "determinism",
    "savant",
    "coda",
    "palaver",
    "opus",
    "envoy",
    "scrybe",
    "niche",
    "notary",
    "urge",
    "lexicon",
    "exile",
    "tactic",
    "engine",
    "temper",
    "skein",
    "inversa",
    "fate",
    "rote",
    "context",
    "content",
    "programming",
    "utility",
    "identity",
    "shade",
    "natal",
    "centra",
    "cyphor",
    "replete",
    "kindred",
    "shatter",
    "shattercore",
}

SOURCE_SHAPE_WEIGHTS = {
    "rule_document_candidate": 8,
    "opaque_uploaded_file": 2,
    "archive_metadata": -6,
    "conversation_export": -8,
    "unclassified": -2,
}


def sha256_text(value: str) -> str:
    return hashlib.sha256(
        value.encode("utf-8")
    ).hexdigest()


def read_jsonl(
    path: Path,
) -> Iterator[dict[str, Any]]:
    with path.open(
        "r",
        encoding="utf-8",
    ) as handle:
        for line_number, line in enumerate(
            handle,
            start=1,
        ):
            line = line.strip()

            if not line:
                continue

            try:
                value = json.loads(line)
            except json.JSONDecodeError as exc:
                raise RuntimeError(
                    f"invalid json at "
                    f"{path}:{line_number}: {exc}"
                ) from exc

            if not isinstance(value, dict):
                raise RuntimeError(
                    f"non-object json at "
                    f"{path}:{line_number}"
                )

            yield value


def load_sources() -> dict[str, dict[str, Any]]:
    sources: dict[str, dict[str, Any]] = {}

    for record in read_jsonl(
        SOURCE_RESOLUTION
    ):
        path = record.get("archive_path")

        if not isinstance(path, str):
            continue

        sources[path] = record

    return sources


def tokenize(
    text: str,
) -> set[str]:
    result: set[str] = set()

    for match in WORD_RE.finditer(
        text.lower()
    ):
        word = match.group(0)

        if word in STOP_WORDS:
            continue

        result.add(word)

    return result


def core_terms(
    text: str,
) -> list[str]:
    words = tokenize(text)

    return sorted(
        word
        for word in words
        if word in CORE_TERMS
    )


def semantic_signature(
    text: str,
) -> str:
    text = text.lower()

    text = re.sub(
        r"`([^`]*)`",
        r"\1",
        text,
    )

    text = re.sub(
        r"[*_~#>]",
        " ",
        text,
    )

    text = re.sub(
        r"\bshall\s+not\b",
        "must not",
        text,
    )

    text = re.sub(
        r"\bshall\b",
        "must",
        text,
    )

    text = re.sub(
        r"\bmay\s+not\b",
        "must not",
        text,
    )

    text = re.sub(
        r"\bcan\s+not\b",
        "cannot",
        text,
    )

    text = re.sub(
        r"\bis\s+required\s+to\b",
        "must",
        text,
    )

    text = re.sub(
        r"\bare\s+required\s+to\b",
        "must",
        text,
    )

    text = re.sub(
        r"\s+",
        " ",
        text,
    ).strip()

    return text


def modal_signature(
    text: str,
) -> list[str]:
    return sorted(
        {
            match.group(0).lower()
            for match in MODAL_RE.finditer(
                text
            )
        }
    )


def source_shape_score(
    source: dict[str, Any],
) -> int:
    score = 0

    shapes = source.get(
        "source_shape",
        [],
    )

    if isinstance(shapes, list):
        for shape in shapes:
            score += SOURCE_SHAPE_WEIGHTS.get(
                str(shape),
                0,
            )

    return score


def source_evidence_score(
    source: dict[str, Any],
) -> int:
    score = source_shape_score(
        source
    )

    authority_indicators = source.get(
        "authority_indicators",
        {},
    )

    if isinstance(
        authority_indicators,
        dict,
    ):
        score += min(
            10,
            sum(
                int(value)
                for value in (
                    authority_indicators.values()
                )
                if isinstance(value, int)
            ),
        )

    savant_counts = source.get(
        "savant_term_counts",
        {},
    )

    if isinstance(
        savant_counts,
        dict,
    ):
        score += min(
            8,
            len(savant_counts),
        )

    if source.get(
        "metadata_match_count",
        0,
    ):
        score += 2

    return score


def representative_source_score(
    source: dict[str, Any],
    group_score: int,
    source_count: int,
    occurrence_count: int,
) -> int:
    score = group_score

    score += source_evidence_score(
        source
    )

    if source_count > 1:
        score += min(
            5,
            source_count - 1,
        )

    if occurrence_count > 1:
        score += min(
            4,
            occurrence_count.bit_length() - 1,
        )

    return score


def get_explicit_groups(
    connection: sqlite3.Connection,
) -> Iterator[dict[str, Any]]:
    cursor = connection.execute(
        """
        SELECT
            normalized_sha256,
            semantic_sha256,
            representative_text,
            representative_path,
            representative_member_sha256,
            representative_line_start,
            representative_line_end,
            representative_window,
            occurrence_count,
            source_count,
            domains_json,
            historical_hint,
            score
        FROM groups
        WHERE strength = 'explicit_normative'
        ORDER BY
            score DESC,
            source_count DESC,
            occurrence_count DESC,
            normalized_sha256 ASC
        """
    )

    for row in cursor:
        yield {
            "normalized_sha256": row[0],
            "semantic_sha256": row[1],
            "text": row[2],
            "representative_path": row[3],
            "representative_member_sha256": row[4],
            "representative_line_start": row[5],
            "representative_line_end": row[6],
            "representative_window": row[7],
            "occurrence_count": row[8],
            "source_count": row[9],
            "domains": json.loads(row[10]),
            "historical_hint": bool(row[11]),
            "group_score": row[12],
        }


def occurrence_sources(
    connection: sqlite3.Connection,
    normalized_sha256: str,
) -> list[dict[str, Any]]:
    rows = connection.execute(
        """
        SELECT
            archive_path,
            member_sha256,
            line_start,
            line_end,
            window
        FROM occurrences
        WHERE normalized_sha256 = ?
        ORDER BY
            archive_path ASC,
            line_start ASC,
            line_end ASC,
            window ASC
        LIMIT ?
        """,
        (
            normalized_sha256,
            MAX_SOURCE_OCCURRENCES,
        ),
    )

    return [
        {
            "archive_path": row[0],
            "member_sha256": row[1],
            "line_start": row[2],
            "line_end": row[3],
            "window": row[4],
        }
        for row in rows
    ]


def choose_best_source(
    occurrences: list[dict[str, Any]],
    sources: dict[str, dict[str, Any]],
    group_score: int,
    source_count: int,
    occurrence_count: int,
) -> tuple[
    dict[str, Any] | None,
    dict[str, Any] | None,
    int,
]:
    best_occurrence = None
    best_source = None
    best_score = -10**9

    for occurrence in occurrences:
        path = occurrence["archive_path"]
        source = sources.get(path)

        if source is None:
            continue

        score = representative_source_score(
            source,
            group_score,
            source_count,
            occurrence_count,
        )

        identity = (
            score,
            path,
            occurrence["line_start"],
        )

        best_identity = (
            best_score,
            (
                best_occurrence[
                    "archive_path"
                ]
                if best_occurrence
                else "\uffff"
            ),
            (
                best_occurrence[
                    "line_start"
                ]
                if best_occurrence
                else 10**18
            ),
        )

        if (
            score > best_score
            or (
                score == best_score
                and identity[1:]
                < best_identity[1:]
            )
        ):
            best_score = score
            best_occurrence = occurrence
            best_source = source

    return (
        best_occurrence,
        best_source,
        best_score,
    )


def review_class(
    source: dict[str, Any] | None,
    score: int,
    historical_hint: bool,
) -> str:
    if source is None:
        return "unresolved_source"

    shapes = set(
        str(value)
        for value in source.get(
            "source_shape",
            []
        )
    )

    if shapes & {
        "conversation_export",
        "archive_metadata",
    }:
        return "historical_context"

    if historical_hint:
        return "historical_candidate"

    if (
        "rule_document_candidate"
        in shapes
        and score >= 18
    ):
        return "strong_rule_evidence"

    if score >= 12:
        return "rule_evidence"

    return "weak_rule_evidence"


def build_review_record(
    connection: sqlite3.Connection,
    group: dict[str, Any],
    sources: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    occurrences = occurrence_sources(
        connection,
        group["normalized_sha256"],
    )

    (
        best_occurrence,
        best_source,
        evidence_score,
    ) = choose_best_source(
        occurrences,
        sources,
        group["group_score"],
        group["source_count"],
        group["occurrence_count"],
    )

    text = str(
        group["text"]
    )[:MAX_TEXT_CHARS]

    terms = core_terms(text)
    signature = semantic_signature(
        text
    )

    source_summary = None

    if best_source is not None:
        source_summary = {
            "archive_path": (
                best_source.get(
                    "archive_path"
                )
            ),
            "title_candidate": (
                best_source.get(
                    "title_candidate"
                )
            ),
            "source_shape": (
                best_source.get(
                    "source_shape",
                    []
                )
            ),
            "metadata_match_count": (
                best_source.get(
                    "metadata_match_count",
                    0,
                )
            ),
            "authority_indicators": (
                best_source.get(
                    "authority_indicators",
                    {},
                )
            ),
            "savant_term_counts": (
                best_source.get(
                    "savant_term_counts",
                    {},
                )
            ),
            "authority_status": "unresolved",
        }

    return {
        "normalized_sha256": (
            group["normalized_sha256"]
        ),
        "semantic_sha256": (
            group["semantic_sha256"]
        ),
        "review_signature_sha256": (
            sha256_text(signature)
        ),
        "text": text,
        "core_terms": terms,
        "modal_signature": (
            modal_signature(text)
        ),
        "negated": bool(
            NEGATION_RE.search(text)
        ),
        "domains": group["domains"],
        "historical_hint": (
            group["historical_hint"]
        ),
        "occurrence_count": (
            group["occurrence_count"]
        ),
        "source_count": (
            group["source_count"]
        ),
        "group_score": (
            group["group_score"]
        ),
        "evidence_score": (
            evidence_score
        ),
        "review_class": review_class(
            best_source,
            evidence_score,
            group["historical_hint"],
        ),
        "representative_occurrence": (
            best_occurrence
        ),
        "representative_source": (
            source_summary
        ),
        "sample_occurrences": (
            occurrences
        ),
        "sample_occurrences_truncated": (
            group["occurrence_count"]
            > len(occurrences)
        ),
        "authority_effect": "none",
    }


def conflict_key(
    record: dict[str, Any],
) -> str | None:
    terms = record.get(
        "core_terms",
        [],
    )

    if not terms:
        return None

    domains = record.get(
        "domains",
        [],
    )

    payload = {
        "terms": terms,
        "domains": sorted(
            str(value)
            for value in domains
        ),
    }

    return sha256_text(
        json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
        )
    )


def write_jsonl(
    path: Path,
    records: Iterator[dict[str, Any]],
) -> tuple[int, str, int]:
    digest = hashlib.sha256()
    count = 0
    byte_count = 0

    with path.open(
        "wb",
    ) as handle:
        for record in records:
            encoded = (
                json.dumps(
                    record,
                    ensure_ascii=False,
                    sort_keys=True,
                    separators=(",", ":"),
                )
                + "\n"
            ).encode("utf-8")

            handle.write(encoded)
            digest.update(encoded)

            count += 1
            byte_count += len(encoded)

    return (
        count,
        digest.hexdigest(),
        byte_count,
    )


def iter_conflicts(
    conflict_groups: dict[
        str,
        list[dict[str, Any]],
    ],
) -> Iterator[dict[str, Any]]:
    for key in sorted(
        conflict_groups
    ):
        records = conflict_groups[key]

        if len(records) < 2:
            continue

        has_negated = any(
            record["negated"]
            for record in records
        )

        has_positive = any(
            not record["negated"]
            for record in records
        )

        if not (
            has_negated
            and has_positive
        ):
            continue

        yield {
            "conflict_key": key,
            "status": "potential_conflict",
            "authority_effect": "none",
            "reason": (
                "records share core terminology "
                "and domains but differ in negation; "
                "semantic conflict is not automatically resolved"
            ),
            "members": [
                {
                    "normalized_sha256": (
                        record[
                            "normalized_sha256"
                        ]
                    ),
                    "text": (
                        record["text"]
                    ),
                    "negated": (
                        record["negated"]
                    ),
                    "review_class": (
                        record[
                            "review_class"
                        ]
                    ),
                    "representative_occurrence": (
                        record[
                            "representative_occurrence"
                        ]
                    ),
                    "representative_source": (
                        record[
                            "representative_source"
                        ]
                    ),
                }
                for record in records
            ],
        }


def main() -> int:
    required = (
        DATABASE,
        SOURCE_RESOLUTION,
    )

    for path in required:
        if not path.is_file():
            print(
                "required input does not exist: "
                f"{path}",
                file=sys.stderr,
            )
            return 1

    OUTPUT_ROOT.mkdir(
        parents=True,
        exist_ok=True,
    )

    sources = load_sources()

    connection = sqlite3.connect(
        str(DATABASE)
    )

    review_records: list[
        dict[str, Any]
    ] = []

    review_counts: Counter[str] = Counter()
    domain_counts: Counter[str] = Counter()
    conflict_groups: defaultdict[
        str,
        list[dict[str, Any]],
    ] = defaultdict(list)

    try:
        for group in get_explicit_groups(
            connection
        ):
            record = build_review_record(
                connection,
                group,
                sources,
            )

            review_records.append(
                record
            )

            review_counts[
                record["review_class"]
            ] += 1

            for domain in record[
                "domains"
            ]:
                domain_counts[
                    str(domain)
                ] += 1

            key = conflict_key(
                record
            )

            if key is not None:
                conflict_groups[
                    key
                ].append(
                    record
                )

    except Exception as exc:
        connection.close()

        print(
            "review corpus construction "
            f"failed: {type(exc).__name__}: "
            f"{exc}",
            file=sys.stderr,
        )

        return 1

    finally:
        try:
            connection.close()
        except Exception:
            pass

    review_records.sort(
        key=lambda record: (
            -record["evidence_score"],
            -record["source_count"],
            -record["occurrence_count"],
            record["normalized_sha256"],
        )
    )

    (
        review_count,
        review_sha256,
        review_bytes,
    ) = write_jsonl(
        REVIEW_JSONL,
        iter(review_records),
    )

    conflict_records = list(
        iter_conflicts(
            conflict_groups
        )
    )

    (
        conflict_count,
        conflict_sha256,
        conflict_bytes,
    ) = write_jsonl(
        CONFLICT_JSONL,
        iter(conflict_records),
    )

    strong_count = sum(
        1
        for record in review_records
        if record["review_class"]
        == "strong_rule_evidence"
    )

    rule_evidence_count = sum(
        1
        for record in review_records
        if record["review_class"]
        in {
            "strong_rule_evidence",
            "rule_evidence",
        }
    )

    historical_count = sum(
        1
        for record in review_records
        if record["review_class"]
        in {
            "historical_context",
            "historical_candidate",
        }
    )

    unresolved_source_count = sum(
        1
        for record in review_records
        if record[
            "review_class"
        ] == "unresolved_source"
    )

    summary = {
        "schema_version": (
            SCHEMA_VERSION
        ),
        "database": str(
            DATABASE
        ),
        "source_resolution": str(
            SOURCE_RESOLUTION
        ),
        "resolved_source_records": (
            len(sources)
        ),
        "explicit_normative_input_groups": (
            len(review_records)
        ),
        "review_class_counts": dict(
            sorted(
                review_counts.items()
            )
        ),
        "domain_counts": dict(
            sorted(
                domain_counts.items()
            )
        ),
        "strong_rule_evidence_groups": (
            strong_count
        ),
        "rule_evidence_groups": (
            rule_evidence_count
        ),
        "historical_groups": (
            historical_count
        ),
        "unresolved_source_groups": (
            unresolved_source_count
        ),
        "potential_conflict_groups": (
            conflict_count
        ),
        "outputs": {
            "rule_review_corpus": {
                "path": str(
                    REVIEW_JSONL
                ),
                "records": (
                    review_count
                ),
                "bytes": (
                    review_bytes
                ),
                "sha256": (
                    review_sha256
                ),
            },
            "potential_conflicts": {
                "path": str(
                    CONFLICT_JSONL
                ),
                "records": (
                    conflict_count
                ),
                "bytes": (
                    conflict_bytes
                ),
                "sha256": (
                    conflict_sha256
                ),
            },
        },
        "authority_effect": "none",
        "authority_note": (
            "scores and classes prioritize "
            "historical evidence for review; "
            "they do not admit, supersede, "
            "or reconcile savant authority"
        ),
    }

    SUMMARY_JSON.write_text(
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
