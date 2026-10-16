
#!/usr/bin/env python3

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sqlite3
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator


DEFAULT_ROOT = Path(
    "/root/savant-runtime/audit/archive-rule-extraction/"
    "ae2420cc26989b23f18f3dd579c69f2c9c8d9d107d90793173cf4f8fe74af1af"
)

DEFAULT_INPUT = DEFAULT_ROOT / "rule_candidates.jsonl"
DEFAULT_OUTPUT = DEFAULT_ROOT / "reduced"
DEFAULT_DATABASE = DEFAULT_OUTPUT / "reduction.sqlite3"

SCHEMA_VERSION = "1.0.0"

MAX_EXCERPT_CHARS = 65536

SPACE_RE = re.compile(r"[ \t]+")
BLANK_RE = re.compile(r"\n{3,}")
MARKDOWN_PREFIX_RE = re.compile(
    r"(?m)^\s*(?:#{1,6}|[-*+]|>\s*|\d+[.)])\s*"
)

EXPLICIT_NORMATIVE_RE = re.compile(
    r"""
    \b(
        must |
        must\s+not |
        shall |
        shall\s+not |
        required |
        requires |
        requirement |
        prohibited |
        forbidden |
        may\s+not |
        cannot |
        can\s+not |
        never |
        always |
        only |
        invariant |
        immutable |
        mandatory |
        authoritative |
        authority\s+precedence |
        supersede |
        supersedes |
        superseded |
        preserve |
        preserves |
        retained |
        retain |
        do\s+not |
        does\s+not |
        cannot\s+be |
        must\s+be
    )\b
    """,
    re.IGNORECASE | re.VERBOSE,
)

ADVISORY_RE = re.compile(
    r"""
    \b(
        should |
        should\s+not |
        recommended |
        recommend |
        prefer |
        preferred |
        preferably |
        ought |
        guidance |
        guideline |
        convention |
        best\s+practice
    )\b
    """,
    re.IGNORECASE | re.VERBOSE,
)

AUTHORITY_RE = re.compile(
    r"""
    \b(
        authority |
        authoritative |
        precedence |
        constitutional |
        constitution |
        canon |
        canonical |
        accepted\s+decision |
        accepted\s+decisions |
        admitted\s+evidence |
        evidence |
        immutable |
        supersede |
        superseded |
        provenance |
        lineage
    )\b
    """,
    re.IGNORECASE | re.VERBOSE,
)

ARCHITECTURE_RE = re.compile(
    r"""
    \b(
        glyph |
        instance |
        instances |
        composition |
        compose |
        composed |
        projection |
        project |
        projected |
        segue |
        segues |
        typed\s+segue |
        typed\s+segues |
        lineage |
        provenance |
        dependency |
        dependencies |
        dependent |
        dependents |
        deterministic |
        determinism |
        owner |
        ownership |
        responsibility |
        mutation |
        coda |
        palaver |
        opus |
        envoy |
        scrybe |
        niche |
        notary |
        urge |
        fluid-canon |
        fluid\s+canon |
        lexicon |
        exile |
        tactic |
        engine |
        shade |
        natal |
        centra |
        cyphor |
        temper |
        skein |
        inversa |
        fate |
        rote
    )\b
    """,
    re.IGNORECASE | re.VERBOSE,
)

VALIDATION_RE = re.compile(
    r"""
    \b(
        validation |
        validate |
        verification |
        verify |
        test |
        testing |
        compile |
        compilation |
        regression |
        compatibility |
        startup |
        integration |
        failure |
        failures |
        retry |
        retries |
        pivot |
        evidence
    )\b
    """,
    re.IGNORECASE | re.VERBOSE,
)

MUTATION_RE = re.compile(
    r"""
    \b(
        mutation |
        mutate |
        write |
        writer |
        persistent |
        persistence |
        durable |
        coda |
        admission |
        admitted |
        notary |
        authority |
        rollback |
        reversible |
        migration
    )\b
    """,
    re.IGNORECASE | re.VERBOSE,
)

LEXICON_RE = re.compile(
    r"""
    \b(
        terminology |
        lexicon |
        lexical |
        rename |
        renamed |
        supersede |
        superseded |
        alias |
        aliases |
        canonical\s+term |
        canonical\s+terminology |
        historical\s+term |
        historical\s+terminology |
        cyphor
    )\b
    """,
    re.IGNORECASE | re.VERBOSE,
)

SECURITY_RE = re.compile(
    r"""
    \b(
        credential |
        credentials |
        secret |
        secrets |
        password |
        passwords |
        token |
        tokens |
        api\s+key |
        access\s+key |
        authorization |
        authentication |
        permission |
        permissions |
        privilege |
        privileges
    )\b
    """,
    re.IGNORECASE | re.VERBOSE,
)

HISTORICAL_HINT_RE = re.compile(
    r"""
    \b(
        historical |
        history |
        obsolete |
        deprecated |
        superseded |
        legacy |
        previous |
        formerly |
        old\s+version |
        prior\s+version |
        archive |
        archived
    )\b
    """,
    re.IGNORECASE | re.VERBOSE,
)

SOURCE_PRIORITY_HINTS = (
    "constitution",
    "constitutional",
    "master_doctrine",
    "master-doctrine",
    "doctrine",
    "accepted",
    "decision",
    "authority",
    "canon",
    "rules",
    "rule",
    "architecture",
    "masterplan",
    "structure",
    "lexicon",
    "terminology",
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def normalize_text(value: str) -> str:
    value = value.replace("\r\n", "\n").replace("\r", "\n")
    value = MARKDOWN_PREFIX_RE.sub("", value)
    value = SPACE_RE.sub(" ", value)
    value = "\n".join(line.strip() for line in value.splitlines())
    value = BLANK_RE.sub("\n\n", value)
    return value.strip()


def semantic_normalize(value: str) -> str:
    value = normalize_text(value).lower()

    replacements = (
        (r"\bshall\s+not\b", "must not"),
        (r"\bmay\s+not\b", "must not"),
        (r"\bcan\s+not\b", "cannot"),
        (r"\bshall\b", "must"),
        (r"\bis\s+required\s+to\b", "must"),
        (r"\bare\s+required\s+to\b", "must"),
        (r"\bis\s+required\b", "must"),
        (r"\bare\s+required\b", "must"),
        (r"\bmust\s+always\b", "must"),
        (r"\bshould\s+always\b", "should"),
    )

    for pattern, replacement in replacements:
        value = re.sub(pattern, replacement, value)

    value = re.sub(r"[`*_~]", "", value)
    value = re.sub(r"\s+", " ", value)
    value = re.sub(r"\s+([,.;:!?])", r"\1", value)

    return value.strip()


def source_priority(path: str) -> int:
    lower = path.lower()
    score = 0

    for hint in SOURCE_PRIORITY_HINTS:
        if hint in lower:
            score += 1

    if lower.endswith(".md"):
        score += 2
    elif lower.endswith(".txt"):
        score += 1

    if "chat.html" in lower:
        score -= 1

    return score


def classify(text: str) -> dict[str, Any]:
    explicit = bool(EXPLICIT_NORMATIVE_RE.search(text))
    advisory = bool(ADVISORY_RE.search(text))
    authority = bool(AUTHORITY_RE.search(text))
    architecture = bool(ARCHITECTURE_RE.search(text))
    validation = bool(VALIDATION_RE.search(text))
    mutation = bool(MUTATION_RE.search(text))
    lexicon = bool(LEXICON_RE.search(text))
    security = bool(SECURITY_RE.search(text))
    historical_hint = bool(HISTORICAL_HINT_RE.search(text))

    if explicit:
        strength = "explicit_normative"
    elif advisory:
        strength = "advisory"
    else:
        strength = "contextual"

    domains: list[str] = []

    if authority:
        domains.append("authority")

    if architecture:
        domains.append("architecture")

    if mutation:
        domains.append("mutation")

    if validation:
        domains.append("validation")

    if lexicon:
        domains.append("lexicon")

    if security:
        domains.append("security")

    if not domains:
        domains.append("other")

    score = 0

    if explicit:
        score += 10

    if advisory:
        score += 3

    if authority:
        score += 6

    if architecture:
        score += 5

    if mutation:
        score += 5

    if validation:
        score += 3

    if lexicon:
        score += 4

    if security:
        score += 2

    if historical_hint:
        score -= 2

    return {
        "strength": strength,
        "domains": domains,
        "historical_hint": historical_hint,
        "score": score,
    }


def connect_database(path: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(str(path))
    connection.execute("PRAGMA journal_mode=WAL")
    connection.execute("PRAGMA synchronous=NORMAL")
    connection.execute("PRAGMA temp_store=FILE")
    connection.execute("PRAGMA cache_size=-65536")

    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS meta (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS groups (
            normalized_sha256 TEXT PRIMARY KEY,
            semantic_sha256 TEXT NOT NULL,
            normalized_text TEXT NOT NULL,
            semantic_text TEXT NOT NULL,
            representative_text TEXT NOT NULL,
            representative_path TEXT NOT NULL,
            representative_member_sha256 TEXT NOT NULL,
            representative_line_start INTEGER NOT NULL,
            representative_line_end INTEGER NOT NULL,
            representative_window INTEGER NOT NULL,
            representative_priority INTEGER NOT NULL,
            occurrence_count INTEGER NOT NULL DEFAULT 0,
            source_count INTEGER NOT NULL DEFAULT 0,
            strength TEXT NOT NULL,
            domains_json TEXT NOT NULL,
            historical_hint INTEGER NOT NULL,
            score INTEGER NOT NULL
        );

        CREATE TABLE IF NOT EXISTS occurrences (
            normalized_sha256 TEXT NOT NULL,
            archive_path TEXT NOT NULL,
            member_sha256 TEXT NOT NULL,
            line_start INTEGER NOT NULL,
            line_end INTEGER NOT NULL,
            window INTEGER NOT NULL,
            PRIMARY KEY (
                normalized_sha256,
                archive_path,
                member_sha256,
                line_start,
                line_end,
                window
            )
        );

        CREATE INDEX IF NOT EXISTS idx_occurrences_group
        ON occurrences(normalized_sha256);

        CREATE INDEX IF NOT EXISTS idx_groups_semantic
        ON groups(semantic_sha256);

        CREATE INDEX IF NOT EXISTS idx_groups_score
        ON groups(score DESC);
        """
    )

    return connection


def reset_database(connection: sqlite3.Connection) -> None:
    connection.executescript(
        """
        DELETE FROM occurrences;
        DELETE FROM groups;
        DELETE FROM meta;
        """
    )
    connection.commit()


def iter_jsonl(path: Path) -> Iterator[tuple[int, dict[str, Any]]]:
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            line = line.strip()

            if not line:
                continue

            try:
                value = json.loads(line)
            except json.JSONDecodeError as exc:
                raise RuntimeError(
                    f"invalid json at {path}:{line_number}: {exc}"
                ) from exc

            if not isinstance(value, dict):
                raise RuntimeError(
                    f"non-object json at {path}:{line_number}"
                )

            yield line_number, value


def validate_record(
    source_line: int,
    record: dict[str, Any],
) -> tuple[str, str, int, int, int, str]:
    required = (
        "archive_path",
        "member_sha256",
        "line_start",
        "line_end",
        "window",
        "text",
    )

    missing = [
        key for key in required
        if key not in record
    ]

    if missing:
        raise RuntimeError(
            f"candidate line {source_line} missing fields: "
            + ", ".join(missing)
        )

    archive_path = str(record["archive_path"])
    member_sha256 = str(record["member_sha256"])
    line_start = int(record["line_start"])
    line_end = int(record["line_end"])
    window = int(record["window"])
    text = str(record["text"])

    return (
        archive_path,
        member_sha256,
        line_start,
        line_end,
        window,
        text,
    )


def ingest(
    connection: sqlite3.Connection,
    input_path: Path,
) -> dict[str, int]:
    stats = {
        "input_records": 0,
        "empty_after_normalization": 0,
        "exact_duplicate_occurrences": 0,
    }

    insert_occurrence = connection.cursor()
    select_group = connection.cursor()
    insert_group = connection.cursor()
    update_group = connection.cursor()

    connection.execute("BEGIN")

    try:
        for source_line, record in iter_jsonl(input_path):
            stats["input_records"] += 1

            (
                archive_path,
                member_sha256,
                line_start,
                line_end,
                window,
                text,
            ) = validate_record(
                source_line,
                record,
            )

            normalized = normalize_text(text)

            if not normalized:
                stats["empty_after_normalization"] += 1
                continue

            semantic = semantic_normalize(normalized)
            normalized_hash = sha256_text(normalized)
            semantic_hash = sha256_text(semantic)

            classification = classify(normalized)
            priority = source_priority(archive_path)

            occurrence_result = insert_occurrence.execute(
                """
                INSERT OR IGNORE INTO occurrences (
                    normalized_sha256,
                    archive_path,
                    member_sha256,
                    line_start,
                    line_end,
                    window
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    normalized_hash,
                    archive_path,
                    member_sha256,
                    line_start,
                    line_end,
                    window,
                ),
            )

            if occurrence_result.rowcount == 0:
                stats["exact_duplicate_occurrences"] += 1
                continue

            existing = select_group.execute(
                """
                SELECT
                    representative_priority,
                    representative_path,
                    representative_line_start
                FROM groups
                WHERE normalized_sha256 = ?
                """,
                (normalized_hash,),
            ).fetchone()

            if existing is None:
                insert_group.execute(
                    """
                    INSERT INTO groups (
                        normalized_sha256,
                        semantic_sha256,
                        normalized_text,
                        semantic_text,
                        representative_text,
                        representative_path,
                        representative_member_sha256,
                        representative_line_start,
                        representative_line_end,
                        representative_window,
                        representative_priority,
                        occurrence_count,
                        source_count,
                        strength,
                        domains_json,
                        historical_hint,
                        score
                    ) VALUES (
                        ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, 1, ?, ?, ?, ?
                    )
                    """,
                    (
                        normalized_hash,
                        semantic_hash,
                        normalized,
                        semantic,
                        text[:MAX_EXCERPT_CHARS],
                        archive_path,
                        member_sha256,
                        line_start,
                        line_end,
                        window,
                        priority,
                        classification["strength"],
                        json.dumps(
                            classification["domains"],
                            separators=(",", ":"),
                        ),
                        int(classification["historical_hint"]),
                        classification["score"],
                    ),
                )
            else:
                current_priority = int(existing[0])
                current_path = str(existing[1])
                current_line = int(existing[2])

                replace_representative = (
                    priority > current_priority
                    or (
                        priority == current_priority
                        and (
                            archive_path,
                            line_start,
                        )
                        < (
                            current_path,
                            current_line,
                        )
                    )
                )

                if replace_representative:
                    update_group.execute(
                        """
                        UPDATE groups
                        SET
                            representative_text = ?,
                            representative_path = ?,
                            representative_member_sha256 = ?,
                            representative_line_start = ?,
                            representative_line_end = ?,
                            representative_window = ?,
                            representative_priority = ?
                        WHERE normalized_sha256 = ?
                        """,
                        (
                            text[:MAX_EXCERPT_CHARS],
                            archive_path,
                            member_sha256,
                            line_start,
                            line_end,
                            window,
                            priority,
                            normalized_hash,
                        ),
                    )

        connection.commit()

    except Exception:
        connection.rollback()
        raise

    connection.execute(
        """
        UPDATE groups
        SET occurrence_count = (
            SELECT COUNT(*)
            FROM occurrences
            WHERE occurrences.normalized_sha256 =
                  groups.normalized_sha256
        )
        """
    )

    connection.execute(
        """
        UPDATE groups
        SET source_count = (
            SELECT COUNT(DISTINCT archive_path)
            FROM occurrences
            WHERE occurrences.normalized_sha256 =
                  groups.normalized_sha256
        )
        """
    )

    connection.commit()

    return stats


def write_jsonl(
    path: Path,
    records: Iterator[dict[str, Any]],
) -> tuple[int, str]:
    digest = hashlib.sha256()
    count = 0

    with path.open("wb") as handle:
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

    return count, digest.hexdigest()


def iter_reduced_groups(
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
            strength,
            domains_json,
            historical_hint,
            score
        FROM groups
        ORDER BY
            score DESC,
            source_count DESC,
            occurrence_count DESC,
            normalized_sha256 ASC
        """
    )

    for row in cursor:
        normalized_hash = row[0]

        sources = connection.execute(
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
            """,
            (normalized_hash,),
        ).fetchall()

        yield {
            "normalized_sha256": normalized_hash,
            "semantic_sha256": row[1],
            "text": row[2],
            "representative": {
                "archive_path": row[3],
                "member_sha256": row[4],
                "line_start": row[5],
                "line_end": row[6],
                "window": row[7],
            },
            "occurrence_count": row[8],
            "source_count": row[9],
            "strength": row[10],
            "domains": json.loads(row[11]),
            "historical_hint": bool(row[12]),
            "score": row[13],
            "sources": [
                {
                    "archive_path": source[0],
                    "member_sha256": source[1],
                    "line_start": source[2],
                    "line_end": source[3],
                    "window": source[4],
                }
                for source in sources
            ],
        }


def iter_explicit_groups(
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
            "representative": {
                "archive_path": row[3],
                "member_sha256": row[4],
                "line_start": row[5],
                "line_end": row[6],
                "window": row[7],
            },
            "occurrence_count": row[8],
            "source_count": row[9],
            "domains": json.loads(row[10]),
            "historical_hint": bool(row[11]),
            "score": row[12],
        }


def iter_semantic_clusters(
    connection: sqlite3.Connection,
) -> Iterator[dict[str, Any]]:
    cursor = connection.execute(
        """
        SELECT
            semantic_sha256,
            COUNT(*) AS variant_count,
            SUM(occurrence_count) AS occurrence_count,
            SUM(source_count) AS summed_source_count,
            MAX(score) AS max_score
        FROM groups
        GROUP BY semantic_sha256
        HAVING COUNT(*) > 1
        ORDER BY
            max_score DESC,
            variant_count DESC,
            occurrence_count DESC,
            semantic_sha256 ASC
        """
    )

    for row in cursor:
        semantic_hash = row[0]

        variants = connection.execute(
            """
            SELECT
                normalized_sha256,
                representative_text,
                representative_path,
                representative_member_sha256,
                representative_line_start,
                representative_line_end,
                occurrence_count,
                source_count,
                strength,
                domains_json,
                historical_hint,
                score
            FROM groups
            WHERE semantic_sha256 = ?
            ORDER BY
                score DESC,
                source_count DESC,
                occurrence_count DESC,
                normalized_sha256 ASC
            """,
            (semantic_hash,),
        ).fetchall()

        yield {
            "semantic_sha256": semantic_hash,
            "variant_count": row[1],
            "occurrence_count": row[2],
            "summed_source_count": row[3],
            "max_score": row[4],
            "variants": [
                {
                    "normalized_sha256": variant[0],
                    "text": variant[1],
                    "representative": {
                        "archive_path": variant[2],
                        "member_sha256": variant[3],
                        "line_start": variant[4],
                        "line_end": variant[5],
                    },
                    "occurrence_count": variant[6],
                    "source_count": variant[7],
                    "strength": variant[8],
                    "domains": json.loads(variant[9]),
                    "historical_hint": bool(variant[10]),
                    "score": variant[11],
                }
                for variant in variants
            ],
        }


def collect_statistics(
    connection: sqlite3.Connection,
) -> dict[str, Any]:
    total_groups = connection.execute(
        "SELECT COUNT(*) FROM groups"
    ).fetchone()[0]

    total_occurrences = connection.execute(
        "SELECT COUNT(*) FROM occurrences"
    ).fetchone()[0]

    explicit_groups = connection.execute(
        """
        SELECT COUNT(*)
        FROM groups
        WHERE strength = 'explicit_normative'
        """
    ).fetchone()[0]

    advisory_groups = connection.execute(
        """
        SELECT COUNT(*)
        FROM groups
        WHERE strength = 'advisory'
        """
    ).fetchone()[0]

    contextual_groups = connection.execute(
        """
        SELECT COUNT(*)
        FROM groups
        WHERE strength = 'contextual'
        """
    ).fetchone()[0]

    historical_groups = connection.execute(
        """
        SELECT COUNT(*)
        FROM groups
        WHERE historical_hint = 1
        """
    ).fetchone()[0]

    semantic_groups = connection.execute(
        """
        SELECT COUNT(DISTINCT semantic_sha256)
        FROM groups
        """
    ).fetchone()[0]

    semantic_multi_variant = connection.execute(
        """
        SELECT COUNT(*)
        FROM (
            SELECT semantic_sha256
            FROM groups
            GROUP BY semantic_sha256
            HAVING COUNT(*) > 1
        )
        """
    ).fetchone()[0]

    source_count = connection.execute(
        """
        SELECT COUNT(DISTINCT archive_path)
        FROM occurrences
        """
    ).fetchone()[0]

    domain_counts: Counter[str] = Counter()

    for (domains_json,) in connection.execute(
        "SELECT domains_json FROM groups"
    ):
        for domain in json.loads(domains_json):
            domain_counts[domain] += 1

    return {
        "unique_normalized_groups": total_groups,
        "unique_semantic_groups": semantic_groups,
        "semantic_multi_variant_groups": semantic_multi_variant,
        "retained_occurrences": total_occurrences,
        "source_paths_with_candidates": source_count,
        "explicit_normative_groups": explicit_groups,
        "advisory_groups": advisory_groups,
        "contextual_groups": contextual_groups,
        "historical_hint_groups": historical_groups,
        "domain_counts": dict(
            sorted(domain_counts.items())
        ),
    }


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as handle:
        while True:
            chunk = handle.read(1024 * 1024)

            if not chunk:
                break

            digest.update(chunk)

    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "deduplicate and semantically reduce savant "
            "archive rule evidence while retaining source provenance"
        )
    )

    parser.add_argument(
        "--input",
        type=Path,
        default=DEFAULT_INPUT,
    )

    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
    )

    parser.add_argument(
        "--database",
        type=Path,
        default=DEFAULT_DATABASE,
    )

    args = parser.parse_args()

    if not args.input.is_file():
        print(
            f"input does not exist: {args.input}",
            file=sys.stderr,
        )
        return 1

    args.output.mkdir(
        parents=True,
        exist_ok=True,
    )

    args.database.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    started_at = utc_now()
    input_sha256 = file_sha256(args.input)

    connection = connect_database(
        args.database
    )

    try:
        reset_database(connection)

        connection.execute(
            """
            INSERT INTO meta(key, value)
            VALUES('schema_version', ?)
            """,
            (SCHEMA_VERSION,),
        )

        connection.execute(
            """
            INSERT INTO meta(key, value)
            VALUES('input_sha256', ?)
            """,
            (input_sha256,),
        )

        connection.commit()

        ingest_stats = ingest(
            connection,
            args.input,
        )

        reduction_stats = collect_statistics(
            connection
        )

        reduced_path = (
            args.output / "reduced_candidates.jsonl"
        )

        explicit_path = (
            args.output / "explicit_normative.jsonl"
        )

        clusters_path = (
            args.output / "semantic_clusters.jsonl"
        )

        reduced_count, reduced_sha256 = write_jsonl(
            reduced_path,
            iter_reduced_groups(connection),
        )

        explicit_count, explicit_sha256 = write_jsonl(
            explicit_path,
            iter_explicit_groups(connection),
        )

        cluster_count, clusters_sha256 = write_jsonl(
            clusters_path,
            iter_semantic_clusters(connection),
        )

        completed_at = utc_now()

        summary = {
            "schema_version": SCHEMA_VERSION,
            "started_at": started_at,
            "completed_at": completed_at,
            "input": str(args.input),
            "input_sha256": input_sha256,
            "database": str(args.database),
            "input_records": ingest_stats[
                "input_records"
            ],
            "empty_after_normalization": ingest_stats[
                "empty_after_normalization"
            ],
            "exact_duplicate_occurrences": ingest_stats[
                "exact_duplicate_occurrences"
            ],
            **reduction_stats,
            "outputs": {
                "reduced_candidates": {
                    "path": str(reduced_path),
                    "records": reduced_count,
                    "sha256": reduced_sha256,
                    "bytes": reduced_path.stat().st_size,
                },
                "explicit_normative": {
                    "path": str(explicit_path),
                    "records": explicit_count,
                    "sha256": explicit_sha256,
                    "bytes": explicit_path.stat().st_size,
                },
                "semantic_clusters": {
                    "path": str(clusters_path),
                    "records": cluster_count,
                    "sha256": clusters_sha256,
                    "bytes": clusters_path.stat().st_size,
                },
            },
        }

        summary_path = (
            args.output / "summary.json"
        )

        summary_path.write_text(
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

    except Exception as exc:
        print(
            "reduction failed: "
            f"{type(exc).__name__}: {exc}",
            file=sys.stderr,
        )
        return 1

    finally:
        connection.close()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

