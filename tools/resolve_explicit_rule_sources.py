#!/usr/bin/env python3

from __future__ import annotations

import hashlib
import json
import re
import sqlite3
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterator


ARCHIVE_ROOT = Path(
    "/root/savant-runtime/audit/archive-rule-extraction/"
    "ae2420cc26989b23f18f3dd579c69f2c9c8d9d107d90793173cf4f8fe74af1af"
)

DATABASE = ARCHIVE_ROOT / "reduced/reduction.sqlite3"
MANIFEST = ARCHIVE_ROOT / "manifest.jsonl"
TEXT_ROOT = ARCHIVE_ROOT / "text"

OUTPUT_ROOT = ARCHIVE_ROOT / "resolved-sources"
OUTPUT_JSONL = OUTPUT_ROOT / "explicit_rule_sources.jsonl"
SUMMARY_JSON = OUTPUT_ROOT / "summary.json"

METADATA_FILES = (
    "library_files.json",
    "conversation_asset_file_names.json",
)

MAX_SIGNATURE_CHARS = 8192
MAX_METADATA_MATCHES = 100

TITLE_PATTERNS = (
    re.compile(
        r'(?im)^\s*#\s+(.{1,240})\s*$'
    ),
    re.compile(
        r'(?im)^\s*title\s*[:=]\s*["\']?(.{1,240}?)[\'"]?\s*$'
    ),
    re.compile(
        r'(?i)"title"\s*:\s*"([^"]{1,240})"'
    ),
    re.compile(
        r'(?i)"name"\s*:\s*"([^"]{1,240})"'
    ),
)

AUTHORITY_TERMS = {
    "accepted_authority": re.compile(
        r"\baccepted\s+authority\b",
        re.IGNORECASE,
    ),
    "accepted_decision": re.compile(
        r"\baccepted\s+decision(?:s)?\b",
        re.IGNORECASE,
    ),
    "constitutional": re.compile(
        r"\bconstitutional\b|\bconstitution\b",
        re.IGNORECASE,
    ),
    "canonical": re.compile(
        r"\bcanonical\b|\bcanon\b",
        re.IGNORECASE,
    ),
    "authoritative": re.compile(
        r"\bauthoritative\b|\bauthority\b",
        re.IGNORECASE,
    ),
    "proposed": re.compile(
        r"\bproposed\b|\bdraft\b|\bcandidate\b",
        re.IGNORECASE,
    ),
    "historical": re.compile(
        r"\bhistorical\b|\blegacy\b|\bdeprecated\b|\bsuperseded\b",
        re.IGNORECASE,
    ),
}

SAVANT_TERMS = {
    "savant": re.compile(
        r"\bsavant\b",
        re.IGNORECASE,
    ),
    "glyph": re.compile(
        r"\bglyph\b",
        re.IGNORECASE,
    ),
    "exile": re.compile(
        r"\bexile\b",
        re.IGNORECASE,
    ),
    "niche": re.compile(
        r"\bniche\b",
        re.IGNORECASE,
    ),
    "coda": re.compile(
        r"\bcoda\b",
        re.IGNORECASE,
    ),
    "notary": re.compile(
        r"\bnotary\b",
        re.IGNORECASE,
    ),
    "urge": re.compile(
        r"\burge\b",
        re.IGNORECASE,
    ),
    "palaver": re.compile(
        r"\bpalaver\b",
        re.IGNORECASE,
    ),
    "opus": re.compile(
        r"\bopus\b",
        re.IGNORECASE,
    ),
    "envoy": re.compile(
        r"\benvoy\b",
        re.IGNORECASE,
    ),
    "scrybe": re.compile(
        r"\bscrybe\b",
        re.IGNORECASE,
    ),
    "fluid_canon": re.compile(
        r"\bfluid[- ]canon\b",
        re.IGNORECASE,
    ),
    "lexicon": re.compile(
        r"\blexicon\b",
        re.IGNORECASE,
    ),
    "temper": re.compile(
        r"\btemper\b",
        re.IGNORECASE,
    ),
    "skein": re.compile(
        r"\bskein\b",
        re.IGNORECASE,
    ),
}

DOCUMENT_HINTS = re.compile(
    r"""
    \b(
        constitution |
        doctrine |
        masterplan |
        master\s+plan |
        structure |
        architecture |
        canon |
        ruleset |
        rule\s+set |
        specification |
        spec |
        ledger |
        terminology |
        lexicon |
        decision |
        authority
    )\b
    """,
    re.IGNORECASE | re.VERBOSE,
)

CONVERSATION_PATH_RE = re.compile(
    r"^conversations-\d+\.json$",
    re.IGNORECASE,
)

OPAQUE_FILE_RE = re.compile(
    r"^(?:file_[0-9a-f]+|file-[A-Za-z0-9_-]+)\.dat$"
)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def read_jsonl(path: Path) -> Iterator[dict[str, Any]]:
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

            yield value


def get_explicit_sources(
    connection: sqlite3.Connection,
) -> dict[str, dict[str, int]]:
    result: dict[str, dict[str, int]] = {}

    rows = connection.execute(
        """
        SELECT
            representative_path,
            COUNT(*) AS groups,
            SUM(occurrence_count) AS occurrences
        FROM groups
        WHERE strength = 'explicit_normative'
        GROUP BY representative_path
        ORDER BY representative_path
        """
    )

    for path, groups, occurrences in rows:
        result[str(path)] = {
            "explicit_normative_groups": int(groups or 0),
            "representative_occurrences": int(occurrences or 0),
        }

    return result


def load_manifest() -> dict[str, dict[str, Any]]:
    records: dict[str, dict[str, Any]] = {}

    for record in read_jsonl(MANIFEST):
        archive_path = record.get("archive_path")

        if isinstance(archive_path, str):
            records[archive_path] = record

    return records


def extracted_path_for(
    manifest_record: dict[str, Any],
) -> Path | None:
    value = manifest_record.get("extracted_path")

    if not isinstance(value, str) or not value:
        return None

    path = ARCHIVE_ROOT / value

    if path.is_file():
        return path

    return None


def text_signature(
    path: Path | None,
) -> tuple[str, int]:
    if path is None:
        return "", 0

    with path.open(
        "r",
        encoding="utf-8",
        errors="replace",
    ) as handle:
        text = handle.read(MAX_SIGNATURE_CHARS)

    return text, len(text)


def clean_title(value: str) -> str:
    value = re.sub(r"\s+", " ", value).strip()
    return value[:240]


def infer_title(text: str) -> str | None:
    if not text:
        return None

    for pattern in TITLE_PATTERNS:
        match = pattern.search(text)

        if match:
            title = clean_title(match.group(1))

            if title:
                return title

    for line in text.splitlines():
        line = clean_title(line)

        if not line:
            continue

        if len(line) <= 240:
            return line

    return None


def term_counts(
    text: str,
    patterns: dict[str, re.Pattern[str]],
) -> dict[str, int]:
    return {
        name: len(pattern.findall(text))
        for name, pattern in patterns.items()
        if pattern.search(text)
    }


def recursively_find_strings(
    value: Any,
    needle: str,
    location: str = "$",
) -> Iterator[dict[str, Any]]:
    if isinstance(value, dict):
        for key, child in value.items():
            child_location = f"{location}.{key}"

            if isinstance(child, str):
                if needle in child:
                    yield {
                        "location": child_location,
                        "key": str(key),
                        "value": child[:1000],
                    }
            else:
                yield from recursively_find_strings(
                    child,
                    needle,
                    child_location,
                )

    elif isinstance(value, list):
        for index, child in enumerate(value):
            child_location = f"{location}[{index}]"

            if isinstance(child, str):
                if needle in child:
                    yield {
                        "location": child_location,
                        "key": None,
                        "value": child[:1000],
                    }
            else:
                yield from recursively_find_strings(
                    child,
                    needle,
                    child_location,
                )


def load_metadata_documents() -> dict[str, Any]:
    result: dict[str, Any] = {}

    for name in METADATA_FILES:
        manifest_records = load_manifest()

        record = manifest_records.get(name)

        if record is None:
            continue

        extracted = extracted_path_for(record)

        if extracted is None:
            continue

        try:
            result[name] = json.loads(
                extracted.read_text(
                    encoding="utf-8",
                    errors="replace",
                )
            )
        except json.JSONDecodeError:
            continue

    return result


def metadata_matches_for(
    archive_path: str,
    metadata_documents: dict[str, Any],
) -> list[dict[str, Any]]:
    needles = {
        archive_path,
        Path(archive_path).name,
        Path(archive_path).stem,
    }

    matches: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str]] = set()

    for document_name, document in metadata_documents.items():
        for needle in sorted(needles):
            if not needle:
                continue

            for match in recursively_find_strings(
                document,
                needle,
            ):
                identity = (
                    document_name,
                    match["location"],
                    match["value"],
                )

                if identity in seen:
                    continue

                seen.add(identity)

                matches.append(
                    {
                        "metadata_source": document_name,
                        **match,
                    }
                )

                if len(matches) >= MAX_METADATA_MATCHES:
                    return matches

    return matches


def classify_source_shape(
    archive_path: str,
    title: str | None,
    text: str,
) -> list[str]:
    classes: list[str] = []

    if CONVERSATION_PATH_RE.match(archive_path):
        classes.append("conversation_export")

    if archive_path == "chat.html":
        classes.append("conversation_export")

    if OPAQUE_FILE_RE.match(archive_path):
        classes.append("opaque_uploaded_file")

    if archive_path in METADATA_FILES:
        classes.append("archive_metadata")

    combined = " ".join(
        value
        for value in (
            archive_path,
            title or "",
            text[:4096],
        )
        if value
    )

    if DOCUMENT_HINTS.search(combined):
        classes.append("rule_document_candidate")

    if not classes:
        classes.append("unclassified")

    return classes


def authority_indicators(
    title: str | None,
    text: str,
) -> dict[str, int]:
    combined = "\n".join(
        value
        for value in (
            title or "",
            text,
        )
        if value
    )

    return term_counts(
        combined,
        AUTHORITY_TERMS,
    )


def source_record(
    archive_path: str,
    counts: dict[str, int],
    manifest_record: dict[str, Any],
    metadata_documents: dict[str, Any],
) -> dict[str, Any]:
    extracted_path = extracted_path_for(
        manifest_record
    )

    signature, signature_chars = text_signature(
        extracted_path
    )

    title = infer_title(signature)

    savant_counts = term_counts(
        signature,
        SAVANT_TERMS,
    )

    indicators = authority_indicators(
        title,
        signature,
    )

    metadata_matches = metadata_matches_for(
        archive_path,
        metadata_documents,
    )

    return {
        "archive_path": archive_path,
        **counts,
        "manifest": {
            "classification": manifest_record.get(
                "classification"
            ),
            "sha256": manifest_record.get("sha256"),
            "compressed_size": manifest_record.get(
                "compressed_size"
            ),
            "uncompressed_size": manifest_record.get(
                "uncompressed_size"
            ),
            "encoding_detected": manifest_record.get(
                "encoding_detected"
            ),
            "extracted": manifest_record.get(
                "extracted"
            ),
            "extracted_path": manifest_record.get(
                "extracted_path"
            ),
        },
        "title_candidate": title,
        "source_shape": classify_source_shape(
            archive_path,
            title,
            signature,
        ),
        "authority_indicators": indicators,
        "savant_term_counts": savant_counts,
        "signature_chars_examined": signature_chars,
        "metadata_matches": metadata_matches,
        "metadata_match_count": len(metadata_matches),
        "authority_status": "unresolved",
        "authority_note": (
            "content and filename indicators are evidence only; "
            "this resolver does not grant authority"
        ),
    }


def write_jsonl(
    path: Path,
    records: list[dict[str, Any]],
) -> str:
    digest = hashlib.sha256()

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

    return digest.hexdigest()


def main() -> int:
    required = (
        DATABASE,
        MANIFEST,
    )

    for path in required:
        if not path.is_file():
            print(
                f"required input does not exist: {path}",
                file=sys.stderr,
            )
            return 1

    OUTPUT_ROOT.mkdir(
        parents=True,
        exist_ok=True,
    )

    connection = sqlite3.connect(
        str(DATABASE)
    )

    try:
        explicit_sources = get_explicit_sources(
            connection
        )
    except sqlite3.Error as exc:
        print(
            f"database query failed: {exc}",
            file=sys.stderr,
        )
        connection.close()
        return 1

    finally:
        connection.close()

    manifest = load_manifest()
    metadata_documents = load_metadata_documents()

    records: list[dict[str, Any]] = []
    missing_manifest: list[str] = []

    for archive_path in sorted(explicit_sources):
        manifest_record = manifest.get(
            archive_path
        )

        if manifest_record is None:
            missing_manifest.append(
                archive_path
            )
            continue

        records.append(
            source_record(
                archive_path,
                explicit_sources[archive_path],
                manifest_record,
                metadata_documents,
            )
        )

    records.sort(
        key=lambda record: (
            -record["explicit_normative_groups"],
            -record["representative_occurrences"],
            record["archive_path"],
        )
    )

    output_sha256 = write_jsonl(
        OUTPUT_JSONL,
        records,
    )

    source_shapes: defaultdict[str, int] = defaultdict(int)
    authority_indicator_sources = 0
    metadata_resolved_sources = 0
    savant_sources = 0
    rule_document_candidates = 0

    for record in records:
        for shape in record["source_shape"]:
            source_shapes[shape] += 1

        if record["authority_indicators"]:
            authority_indicator_sources += 1

        if record["metadata_match_count"] > 0:
            metadata_resolved_sources += 1

        if record["savant_term_counts"]:
            savant_sources += 1

        if (
            "rule_document_candidate"
            in record["source_shape"]
        ):
            rule_document_candidates += 1

    summary = {
        "database": str(DATABASE),
        "manifest": str(MANIFEST),
        "explicit_sources_expected": len(
            explicit_sources
        ),
        "sources_resolved": len(records),
        "missing_manifest_sources": missing_manifest,
        "missing_manifest_source_count": len(
            missing_manifest
        ),
        "metadata_documents_loaded": sorted(
            metadata_documents
        ),
        "metadata_resolved_sources": (
            metadata_resolved_sources
        ),
        "sources_with_authority_indicators": (
            authority_indicator_sources
        ),
        "sources_with_savant_terms": savant_sources,
        "rule_document_candidates": (
            rule_document_candidates
        ),
        "source_shape_counts": dict(
            sorted(source_shapes.items())
        ),
        "output": {
            "path": str(OUTPUT_JSONL),
            "records": len(records),
            "bytes": OUTPUT_JSONL.stat().st_size,
            "sha256": output_sha256,
        },
        "authority_effect": "none",
        "authority_note": (
            "resolution records source evidence only; "
            "no archive source is promoted by this pass"
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
