#!/usr/bin/env python3

from __future__ import annotations

import argparse
import csv
import hashlib
import html
from html.parser import HTMLParser
import io
import json
import os
from pathlib import Path
import re
import sys
import unicodedata
from typing import Any, Iterable, Iterator, Mapping


schema = "savant.extr.universal.v1"

text_suffixes = frozenset(
    {
        ".txt",
        ".text",
        ".md",
        ".markdown",
        ".rst",
        ".log",
        ".cfg",
        ".conf",
        ".ini",
        ".env",
        ".toml",
        ".yaml",
        ".yml",
        ".csv",
        ".tsv",
        ".json",
        ".jsonl",
        ".ndjson",
        ".json5",
        ".html",
        ".htm",
        ".xml",
        ".xhtml",
        ".svg",
        ".rtf",
        ".sql",
        ".py",
        ".js",
        ".jsx",
        ".ts",
        ".tsx",
        ".java",
        ".c",
        ".h",
        ".cpp",
        ".hpp",
        ".rs",
        ".go",
        ".sh",
        ".bash",
        ".zsh",
        ".fish",
        ".ps1",
        ".properties",
        ".csv",
        ".tsv",
    }
)

json_suffixes = frozenset(
    {
        ".json",
        ".jsonl",
        ".ndjson",
        ".json5",
    }
)

zero_width = re.compile(
    "[\u200b\u200c\u200d\u2060\ufeff]"
)

horizontal_space = re.compile(
    r"[^\S\r\n]+"
)

excess_blank_lines = re.compile(
    r"\n{4,}"
)

fenced_json = re.compile(
    r"```(?:json|json5)?\s*(.*?)```",
    re.IGNORECASE | re.DOTALL,
)

obvious_noise_lines = (
    re.compile(r"^\s*$"),
    re.compile(r"^\s*[-_=*#]{8,}\s*$"),
)

repeated_punctuation = re.compile(
    r"([!?.,;:])\1{4,}"
)

token_pattern = re.compile(
    r"[\w][\w'-]{1,}",
    re.UNICODE,
)


try:
    from charset_normalizer import (
        from_bytes as charset_from_bytes,
    )
except Exception:
    charset_from_bytes = None


try:
    import ftfy
except Exception:
    ftfy = None


try:
    import orjson
except Exception:
    orjson = None


try:
    import json5
except Exception:
    json5 = None


try:
    from rapidfuzz import fuzz
except Exception:
    fuzz = None


class TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__(
            convert_charrefs=True
        )
        self.parts: list[str] = []
        self.hidden_depth = 0

    def handle_starttag(
        self,
        tag: str,
        attrs: list[
            tuple[str, str | None]
        ],
    ) -> None:
        del attrs

        lowered = tag.casefold()

        if lowered in {
            "script",
            "style",
            "noscript",
            "template",
        }:
            self.hidden_depth += 1

        if lowered in {
            "p",
            "div",
            "br",
            "li",
            "tr",
            "section",
            "article",
            "header",
            "footer",
            "h1",
            "h2",
            "h3",
            "h4",
            "h5",
            "h6",
        }:
            self.parts.append(
                "\n"
            )

    def handle_endtag(
        self,
        tag: str,
    ) -> None:
        lowered = tag.casefold()

        if (
            lowered
            in {
                "script",
                "style",
                "noscript",
                "template",
            }
            and self.hidden_depth > 0
        ):
            self.hidden_depth -= 1

        if lowered in {
            "p",
            "div",
            "li",
            "tr",
            "section",
            "article",
        }:
            self.parts.append(
                "\n"
            )

    def handle_data(
        self,
        data: str,
    ) -> None:
        if self.hidden_depth == 0:
            self.parts.append(
                data
            )

    def text(self) -> str:
        return "".join(
            self.parts
        )


def sha256_bytes(
    value: bytes,
) -> str:
    return hashlib.sha256(
        value
    ).hexdigest()


def stable_json(
    value: Any,
) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )


def stable_digest(
    value: Any,
) -> str:
    return sha256_bytes(
        stable_json(
            value
        ).encode(
            "utf-8"
        )
    )


def decode_bytes(
    raw: bytes,
) -> tuple[
    str,
    str,
    float | None,
]:
    if not raw:
        return (
            "",
            "utf-8",
            1.0,
        )

    if raw.startswith(
        b"\xef\xbb\xbf"
    ):
        return (
            raw.decode(
                "utf-8-sig",
                errors="strict",
            ),
            "utf-8-sig",
            1.0,
        )

    for encoding in (
        "utf-8",
        "utf-16",
        "utf-32",
    ):
        try:
            return (
                raw.decode(
                    encoding,
                    errors="strict",
                ),
                encoding,
                1.0,
            )
        except UnicodeDecodeError:
            pass

    if charset_from_bytes is not None:
        try:
            matches = charset_from_bytes(
                raw
            )

            best = matches.best()

            if best is not None:
                return (
                    str(best),
                    str(
                        best.encoding
                        or "unknown"
                    ),
                    (
                        float(
                            1.0
                            - best.percent_chaos
                            / 100.0
                        )
                        if hasattr(
                            best,
                            "percent_chaos",
                        )
                        else None
                    ),
                )
        except Exception:
            pass

    return (
        raw.decode(
            "utf-8",
            errors="replace",
        ),
        "utf-8-replacement",
        None,
    )


def repair_unicode(
    value: str,
) -> tuple[str, bool]:
    original = value

    if ftfy is not None:
        try:
            value = ftfy.fix_text(
                value
            )
        except Exception:
            pass

    value = unicodedata.normalize(
        "NFC",
        value,
    )

    value = zero_width.sub(
        "",
        value,
    )

    return (
        value,
        value != original,
    )


def normalize_text(
    value: str,
) -> str:
    value = value.replace(
        "\r\n",
        "\n",
    ).replace(
        "\r",
        "\n",
    )

    value = horizontal_space.sub(
        " ",
        value,
    )

    lines = [
        line.rstrip()
        for line in value.splitlines()
    ]

    value = "\n".join(
        lines
    )

    value = excess_blank_lines.sub(
        "\n\n\n",
        value,
    )

    value = repeated_punctuation.sub(
        lambda match:
            match.group(1) * 3,
        value,
    )

    return value.strip()


def strip_html(
    value: str,
) -> str:
    parser = TextExtractor()

    try:
        parser.feed(
            value
        )
        parser.close()

        result = parser.text()

        if result.strip():
            return html.unescape(
                result
            )
    except Exception:
        pass

    return value


def strip_simple_rtf(
    value: str,
) -> str:
    value = re.sub(
        r"\\'[0-9a-fA-F]{2}",
        " ",
        value,
    )

    value = re.sub(
        r"\\[a-zA-Z]+-?\d* ?",
        " ",
        value,
    )

    value = value.replace(
        "{",
        " ",
    ).replace(
        "}",
        " ",
    )

    return value


def json_loads(
    value: str,
) -> Any:
    if orjson is not None:
        try:
            return orjson.loads(
                value
            )
        except Exception:
            pass

    return json.loads(
        value
    )


def parse_json_strict(
    value: str,
) -> tuple[
    list[Any],
    str,
]:
    parsed = json_loads(
        value
    )

    return (
        [parsed],
        "json",
    )


def parse_json5(
    value: str,
) -> tuple[
    list[Any],
    str,
]:
    if json5 is None:
        raise ValueError(
            "json5 unavailable"
        )

    return (
        [
            json5.loads(
                value
            )
        ],
        "json5",
    )


def parse_json_lines(
    value: str,
) -> tuple[
    list[Any],
    str,
]:
    records: list[Any] = []

    for line_number, line in enumerate(
        value.splitlines(),
        start=1,
    ):
        candidate = line.strip()

        if not candidate:
            continue

        try:
            parsed = json_loads(
                candidate
            )
        except Exception as error:
            raise ValueError(
                f"invalid jsonl line "
                f"{line_number}: {error}"
            ) from error

        records.append(
            parsed
        )

    if not records:
        raise ValueError(
            "empty jsonl"
        )

    return (
        records,
        "jsonl",
    )


def parse_concatenated_json(
    value: str,
) -> tuple[
    list[Any],
    str,
]:
    decoder = json.JSONDecoder()
    records: list[Any] = []
    index = 0
    length = len(value)

    while index < length:
        while (
            index < length
            and value[index].isspace()
        ):
            index += 1

        if index >= length:
            break

        parsed, end = (
            decoder.raw_decode(
                value,
                index,
            )
        )

        records.append(
            parsed
        )

        index = end

    if len(records) < 2:
        raise ValueError(
            "not concatenated json"
        )

    return (
        records,
        "concatenated-json",
    )


def parse_fenced_json(
    value: str,
) -> tuple[
    list[Any],
    str,
]:
    records = []

    for match in fenced_json.finditer(
        value
    ):
        candidate = (
            match.group(1).strip()
        )

        if not candidate:
            continue

        try:
            records.append(
                json_loads(
                    candidate
                )
            )
            continue
        except Exception:
            pass

        if json5 is not None:
            try:
                records.append(
                    json5.loads(
                        candidate
                    )
                )
            except Exception:
                pass

    if not records:
        raise ValueError(
            "no parseable fenced json"
        )

    return (
        records,
        "fenced-json",
    )


def parse_any_json(
    value: str,
) -> tuple[
    list[Any],
    str,
    list[str],
]:
    errors: list[str] = []

    parsers = (
        parse_json_strict,
        parse_json_lines,
        parse_concatenated_json,
        parse_json5,
        parse_fenced_json,
    )

    for parser in parsers:
        try:
            records, mode = parser(
                value
            )

            return (
                records,
                mode,
                errors,
            )
        except Exception as error:
            errors.append(
                f"{parser.__name__}: "
                f"{type(error).__name__}"
            )

    raise ValueError(
        "no supported json representation"
    )


def flatten_json(
    value: Any,
    *,
    path: str = "$",
) -> Iterator[
    tuple[str, str]
]:
    if value is None:
        return

    if isinstance(
        value,
        str,
    ):
        candidate = value.strip()

        if candidate:
            yield (
                path,
                candidate,
            )

        return

    if isinstance(
        value,
        (
            int,
            float,
            bool,
        ),
    ):
        yield (
            path,
            str(value),
        )
        return

    if isinstance(
        value,
        Mapping,
    ):
        preferred = (
            "text",
            "content",
            "body",
            "message",
            "description",
            "title",
            "name",
            "value",
            "result",
        )

        visited = set()

        for key in preferred:
            if key in value:
                visited.add(key)

                yield from flatten_json(
                    value[key],
                    path=(
                        f"{path}.{key}"
                    ),
                )

        for key in sorted(
            value,
            key=lambda item:
                str(item).casefold(),
        ):
            if key in visited:
                continue

            yield from flatten_json(
                value[key],
                path=(
                    f"{path}.{key}"
                ),
            )

        return

    if isinstance(
        value,
        Iterable,
    ) and not isinstance(
        value,
        (
            bytes,
            bytearray,
        ),
    ):
        for index, item in enumerate(
            value
        ):
            yield from flatten_json(
                item,
                path=(
                    f"{path}[{index}]"
                ),
            )


def parse_delimited(
    value: str,
    delimiter: str,
) -> list[
    dict[str, str]
]:
    handle = io.StringIO(
        value
    )

    reader = csv.DictReader(
        handle,
        delimiter=delimiter,
    )

    return [
        {
            str(key):
                str(item or "")
            for key, item
            in row.items()
        }
        for row in reader
    ]


def probable_binary(
    raw: bytes,
) -> bool:
    if not raw:
        return False

    if b"\x00" in raw[:65536]:
        if not (
            raw.startswith(
                (
                    b"\xff\xfe",
                    b"\xfe\xff",
                    b"\xff\xfe\x00\x00",
                    b"\x00\x00\xfe\xff",
                )
            )
        ):
            return True

    sample = raw[:65536]

    controls = sum(
        1
        for byte in sample
        if (
            byte < 9
            or 13 < byte < 32
        )
    )

    return (
        controls
        / max(
            1,
            len(sample),
        )
        > 0.08
    )


def detect_kind(
    path: Path,
    text: str,
) -> str:
    suffix = path.suffix.casefold()
    stripped = text.lstrip()

    if suffix in json_suffixes:
        return "json"

    if suffix in {
        ".html",
        ".htm",
        ".xhtml",
    }:
        return "html"

    if suffix == ".rtf":
        return "rtf"

    if suffix == ".csv":
        return "csv"

    if suffix == ".tsv":
        return "tsv"

    if (
        stripped.startswith(
            ("{", "[")
        )
        or stripped.startswith(
            "```json"
        )
    ):
        return "json"

    if re.search(
        r"<(?:html|body|article|div|p|h[1-6])\b",
        stripped[:8192],
        re.IGNORECASE,
    ):
        return "html"

    return "text"


def segment_text(
    value: str,
) -> list[str]:
    paragraphs = re.split(
        r"\n\s*\n",
        value,
    )

    result = []

    for paragraph in paragraphs:
        paragraph = paragraph.strip()

        if not paragraph:
            continue

        if any(
            pattern.match(
                paragraph
            )
            for pattern
            in obvious_noise_lines
        ):
            continue

        result.append(
            paragraph
        )

    return result


def normalized_for_hash(
    value: str,
) -> str:
    value = unicodedata.normalize(
        "NFKC",
        value,
    ).casefold()

    value = re.sub(
        r"\s+",
        " ",
        value,
    ).strip()

    return value


def text_fingerprint(
    value: str,
) -> str:
    return stable_digest(
        normalized_for_hash(
            value
        )
    )


def simhash64(
    value: str,
) -> int:
    tokens = token_pattern.findall(
        normalized_for_hash(
            value
        )
    )

    if not tokens:
        return 0

    vector = [0] * 64

    for token in tokens:
        digest = hashlib.blake2b(
            token.encode(
                "utf-8"
            ),
            digest_size=8,
        ).digest()

        number = int.from_bytes(
            digest,
            "big",
        )

        for bit in range(64):
            vector[bit] += (
                1
                if number
                & (1 << bit)
                else -1
            )

    result = 0

    for bit, weight in enumerate(
        vector
    ):
        if weight >= 0:
            result |= (
                1 << bit
            )

    return result


def hamming_distance(
    left: int,
    right: int,
) -> int:
    return (
        left ^ right
    ).bit_count()


def near_duplicate(
    value: str,
    previous: str,
) -> bool:
    left = simhash64(
        value
    )

    right = simhash64(
        previous
    )

    if hamming_distance(
        left,
        right,
    ) <= 3:
        return True

    if fuzz is not None:
        try:
            return (
                fuzz.ratio(
                    value,
                    previous,
                )
                >= 97
            )
        except Exception:
            pass

    return False


def load_project_profiles(
    path: Path | None,
) -> dict[
    str,
    dict[str, Any]
]:
    if path is None:
        return {}

    if not path.is_file():
        return {}

    try:
        payload = json.loads(
            path.read_text(
                encoding="utf-8"
            )
        )
    except Exception:
        return {}

    projects = payload.get(
        "projects",
        {}
    )

    return (
        projects
        if isinstance(
            projects,
            dict,
        )
        else {}
    )


def classify_project(
    text: str,
    profiles: Mapping[
        str,
        Mapping[str, Any]
    ],
) -> dict[str, Any]:
    normalized = normalized_for_hash(
        text
    )

    scores = []

    for project, profile in (
        profiles.items()
    ):
        signals = profile.get(
            "signals",
            []
        )

        if not isinstance(
            signals,
            list,
        ):
            continue

        hits = []

        for signal in signals:
            candidate = (
                str(signal)
                .casefold()
                .strip()
            )

            if (
                candidate
                and candidate
                in normalized
            ):
                hits.append(
                    candidate
                )

        score = len(
            set(hits)
        )

        if score:
            scores.append(
                (
                    score,
                    str(project),
                    sorted(
                        set(hits)
                    ),
                )
            )

    scores.sort(
        key=lambda row:
            (
                -row[0],
                row[1],
            )
    )

    if not scores:
        return {
            "project":
                "unclassified",
            "confidence":
                0.0,
            "signals":
                [],
            "alternatives":
                [],
        }

    winner = scores[0]

    denominator = sum(
        score
        for score, _, _
        in scores
    )

    confidence = (
        winner[0]
        / max(
            1,
            denominator,
        )
    )

    return {
        "project":
            winner[1],
        "confidence":
            round(
                confidence,
                6,
            ),
        "signals":
            winner[2],
        "alternatives": [
            {
                "project":
                    project,
                "score":
                    score,
                "signals":
                    hits,
            }
            for score, project, hits
            in scores[1:4]
        ],
    }


def prepare_segments(
    path: Path,
    text: str,
    kind: str,
) -> tuple[
    list[
        tuple[str, str]
    ],
    dict[str, Any],
]:
    metadata: dict[str, Any] = {
        "kind": kind,
    }

    if kind == "json":
        records, mode, errors = (
            parse_any_json(
                text
            )
        )

        metadata[
            "json_mode"
        ] = mode

        metadata[
            "json_parser_failures_before_success"
        ] = errors

        segments = []

        for index, record in enumerate(
            records
        ):
            for json_path, value in (
                flatten_json(
                    record,
                    path=f"$[{index}]",
                )
            ):
                segments.append(
                    (
                        json_path,
                        value,
                    )
                )

        return (
            segments,
            metadata,
        )

    if kind == "html":
        cleaned = strip_html(
            text
        )

    elif kind == "rtf":
        cleaned = strip_simple_rtf(
            text
        )

    elif kind == "csv":
        rows = parse_delimited(
            text,
            ",",
        )

        segments = []

        for index, row in enumerate(
            rows
        ):
            segments.append(
                (
                    f"$[{index}]",
                    " | ".join(
                        f"{key}: {value}"
                        for key, value
                        in row.items()
                        if value.strip()
                    ),
                )
            )

        return (
            segments,
            metadata,
        )

    elif kind == "tsv":
        rows = parse_delimited(
            text,
            "\t",
        )

        segments = []

        for index, row in enumerate(
            rows
        ):
            segments.append(
                (
                    f"$[{index}]",
                    " | ".join(
                        f"{key}: {value}"
                        for key, value
                        in row.items()
                        if value.strip()
                    ),
                )
            )

        return (
            segments,
            metadata,
        )

    else:
        cleaned = text

    return (
        [
            (
                f"$[{index}]",
                paragraph,
            )
            for index, paragraph
            in enumerate(
                segment_text(
                    cleaned
                )
            )
        ],
        metadata,
    )


def extract(
    input_path: Path,
    output_path: Path,
    profile_path: Path | None,
) -> dict[str, Any]:
    raw = input_path.read_bytes()

    if probable_binary(
        raw
    ):
        raise RuntimeError(
            "input appears binary rather than text"
        )

    decoded, encoding, confidence = (
        decode_bytes(
            raw
        )
    )

    repaired, repaired_unicode = (
        repair_unicode(
            decoded
        )
    )

    kind = detect_kind(
        input_path,
        repaired,
    )

    try:
        segments, parser_metadata = (
            prepare_segments(
                input_path,
                repaired,
                kind,
            )
        )
    except Exception as error:
        if kind == "json":
            parser_metadata = {
                "kind":
                    "text",
                "json_salvage_failed":
                    f"{type(error).__name__}: "
                    f"{error}",
            }

            segments = [
                (
                    f"$[{index}]",
                    paragraph,
                )
                for index, paragraph
                in enumerate(
                    segment_text(
                        repaired
                    )
                )
            ]

            kind = "text-salvage"

        else:
            raise

    profiles = load_project_profiles(
        profile_path
    )

    exact_seen: set[str] = set()

    recent_text: list[str] = []

    output_rows = []

    duplicate_count = 0
    near_duplicate_count = 0
    debris_count = 0

    for ordinal, (
        source_path,
        raw_segment,
    ) in enumerate(
        segments
    ):
        cleaned = normalize_text(
            raw_segment
        )

        if not cleaned:
            debris_count += 1
            continue

        fingerprint = text_fingerprint(
            cleaned
        )

        if fingerprint in exact_seen:
            duplicate_count += 1
            continue

        exact_seen.add(
            fingerprint
        )

        near_match = any(
            near_duplicate(
                cleaned,
                previous,
            )
            for previous
            in recent_text[-64:]
        )

        if near_match:
            near_duplicate_count += 1
            continue

        recent_text.append(
            cleaned
        )

        classification = (
            classify_project(
                cleaned,
                profiles,
            )
        )

        row = {
            "schema":
                schema,
            "source": {
                "path":
                    str(
                        input_path.resolve()
                    ),
                "sha256":
                    sha256_bytes(
                        raw
                    ),
                "encoding":
                    encoding,
                "encoding_confidence":
                    confidence,
                "kind":
                    kind,
                "source_path":
                    source_path,
                "ordinal":
                    ordinal,
            },
            "text":
                cleaned,
            "fingerprint":
                fingerprint,
            "project":
                classification,
            "quality": {
                "unicode_repaired":
                    repaired_unicode,
                "exact_duplicate":
                    False,
                "near_duplicate":
                    False,
                "debris_removed":
                    False,
                "recovered":
                    True,
            },
            "authority_effect":
                "none",
            "authoritative":
                False,
            "rebuildable":
                True,
        }

        output_rows.append(
            row
        )

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    temporary = (
        output_path.with_name(
            "."
            + output_path.name
            + ".tmp"
        )
    )

    with temporary.open(
        "wb"
    ) as handle:
        for row in output_rows:
            payload = (
                orjson.dumps(
                    row
                )
                if orjson is not None
                else json.dumps(
                    row,
                    ensure_ascii=False,
                    separators=(",", ":"),
                    default=str,
                ).encode(
                    "utf-8"
                )
            )

            handle.write(
                payload
            )
            handle.write(
                b"\n"
            )

        handle.flush()
        os.fsync(
            handle.fileno()
        )

    os.replace(
        temporary,
        output_path,
    )

    receipt = {
        "schema":
            "savant.extr.universal.receipt.v1",
        "authority_effect":
            "none",
        "authoritative":
            False,
        "rebuildable":
            True,
        "source": {
            "path":
                str(
                    input_path.resolve()
                ),
            "sha256":
                sha256_bytes(
                    raw
                ),
            "bytes":
                len(raw),
            "encoding":
                encoding,
            "encoding_confidence":
                confidence,
            "kind":
                kind,
        },
        "parser":
            parser_metadata,
        "statistics": {
            "segments_seen":
                len(
                    segments
                ),
            "segments_written":
                len(
                    output_rows
                ),
            "exact_duplicates_removed":
                duplicate_count,
            "near_duplicates_removed":
                near_duplicate_count,
            "debris_removed":
                debris_count,
        },
        "capabilities": {
            "format_detection":
                True,
            "encoding_detection":
                True,
            "unicode_repair":
                True,
            "strict_json":
                True,
            "jsonl":
                True,
            "ndjson":
                True,
            "json5":
                json5
                is not None,
            "concatenated_json":
                True,
            "fenced_json_salvage":
                True,
            "recursive_json_text_projection":
                True,
            "html_text_projection":
                True,
            "rtf_text_projection":
                True,
            "csv_projection":
                True,
            "tsv_projection":
                True,
            "plain_text_fallback":
                True,
            "exact_deduplication":
                True,
            "near_deduplication":
                True,
            "simhash":
                True,
            "rapidfuzz":
                fuzz
                is not None,
            "project_profiles":
                True,
            "project_confidence":
                True,
            "classification_alternatives":
                True,
            "source_lineage":
                True,
            "stable_fingerprints":
                True,
            "atomic_output":
                True,
            "binary_refusal":
                True,
            "debris_suppression":
                True,
            "raw_fallback_on_json_corruption":
                True,
            "authority_neutral":
                True,
        },
    }

    receipt[
        "digest"
    ] = stable_digest(
        receipt
    )

    receipt_path = (
        output_path.with_suffix(
            output_path.suffix
            + ".receipt.json"
        )
    )

    receipt_path.write_text(
        json.dumps(
            receipt,
            ensure_ascii=False,
            sort_keys=True,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    return receipt


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="extr-universal"
    )

    parser.add_argument(
        "input"
    )

    parser.add_argument(
        "output"
    )

    parser.add_argument(
        "--profiles",
        default=(
            "/root/savant-runtime/"
            "tools/extr-enterprise/"
            "config/projects.json"
        ),
    )

    return parser


def main() -> int:
    args = build_parser().parse_args()

    input_path = Path(
        os.path.expanduser(
            os.path.expandvars(
                args.input
            )
        )
    ).resolve()

    output_path = Path(
        os.path.expanduser(
            os.path.expandvars(
                args.output
            )
        )
    ).resolve()

    profile_path = Path(
        args.profiles
    ).resolve()

    if not input_path.is_file():
        print(
            f"extr-universal: input unavailable: "
            f"{input_path}",
            file=sys.stderr,
        )
        return 1

    try:
        receipt = extract(
            input_path,
            output_path,
            profile_path,
        )
    except Exception as error:
        print(
            f"extr-universal: "
            f"{type(error).__name__}: "
            f"{error}",
            file=sys.stderr,
        )
        return 1

    print(
        json.dumps(
            receipt,
            ensure_ascii=False,
            sort_keys=True,
            indent=2,
        )
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
