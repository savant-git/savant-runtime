#!/usr/bin/env python3

from __future__ import annotations

from dataclasses import dataclass
import csv
import gzip
import hashlib
import html
from io import BytesIO, StringIO
import json
from pathlib import Path
import re
import tarfile
from typing import Any, Iterator, Mapping
import zipfile


schema = "savant://utility/epiphany/universal-parser/1.0.0"
owner = "utility"
authority_effect = "none"
utility_level = "epiphany"
utility_ordinal = 4
universally_reusable = True


class universal_parser_error(RuntimeError):
    pass


@dataclass(
    frozen=True,
    slots=True,
)
class parsed_record:
    source: str
    ordinal: int
    media_type: str
    format: str
    text: str | None
    byte_size: int
    source_digest: str
    record_digest: str
    metadata: Mapping[str, Any]

    def projection(self) -> dict[str, Any]:
        return {
            "schema": schema,
            "source": self.source,
            "ordinal": self.ordinal,
            "media_type": self.media_type,
            "format": self.format,
            "text": self.text,
            "byte_size": self.byte_size,
            "source_digest": self.source_digest,
            "record_digest": self.record_digest,
            "metadata": dict(self.metadata),
        }


@dataclass(
    frozen=True,
    slots=True,
)
class parse_result:
    source: str
    source_digest: str
    byte_size: int
    format: str
    media_type: str
    records: tuple[parsed_record, ...]
    warnings: tuple[str, ...]

    def projection(self) -> dict[str, Any]:
        return {
            "schema": schema,
            "owner": owner,
            "authority_effect": authority_effect,
            "utility_level": utility_level,
            "utility_ordinal": utility_ordinal,
            "universally_reusable": universally_reusable,
            "source": self.source,
            "source_digest": self.source_digest,
            "byte_size": self.byte_size,
            "format": self.format,
            "media_type": self.media_type,
            "record_count": len(self.records),
            "warnings": list(self.warnings),
            "records": [
                record.projection()
                for record in self.records
            ],
        }


text_suffixes = frozenset(
    {
        ".txt",
        ".md",
        ".markdown",
        ".rst",
        ".log",
        ".ini",
        ".cfg",
        ".conf",
        ".toml",
        ".yaml",
        ".yml",
        ".xml",
        ".svg",
        ".css",
        ".js",
        ".mjs",
        ".cjs",
        ".ts",
        ".tsx",
        ".jsx",
        ".py",
        ".sh",
        ".bash",
        ".zsh",
        ".fish",
        ".c",
        ".h",
        ".cc",
        ".cpp",
        ".hpp",
        ".java",
        ".kt",
        ".kts",
        ".go",
        ".rs",
        ".rb",
        ".php",
        ".sql",
    }
)

html_suffixes = frozenset(
    {
        ".html",
        ".htm",
    }
)

json_suffixes = frozenset(
    {
        ".json",
    }
)

jsonl_suffixes = frozenset(
    {
        ".jsonl",
        ".ndjson",
    }
)

csv_suffixes = frozenset(
    {
        ".csv",
        ".tsv",
    }
)

gzip_suffixes = frozenset(
    {
        ".gz",
        ".gzip",
    }
)

zip_suffixes = frozenset(
    {
        ".zip",
    }
)

tar_suffixes = frozenset(
    {
        ".tar",
        ".tgz",
        ".tbz",
        ".tbz2",
        ".txz",
    }
)


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


def digest_bytes(
    value: bytes,
) -> str:
    return hashlib.sha256(
        value
    ).hexdigest()


def digest_value(
    value: Any,
) -> str:
    return hashlib.sha256(
        canonical_json(
            value
        ).encode(
            "utf-8"
        )
    ).hexdigest()


def decode_text(
    payload: bytes,
) -> tuple[str, str]:
    if payload.startswith(
        b"\xef\xbb\xbf"
    ):
        return (
            payload.decode(
                "utf-8-sig",
                errors="replace",
            ),
            "utf-8-sig",
        )

    if payload.startswith(
        b"\xff\xfe"
    ):
        return (
            payload.decode(
                "utf-16-le",
                errors="replace",
            ),
            "utf-16-le",
        )

    if payload.startswith(
        b"\xfe\xff"
    ):
        return (
            payload.decode(
                "utf-16-be",
                errors="replace",
            ),
            "utf-16-be",
        )

    try:
        return (
            payload.decode(
                "utf-8"
            ),
            "utf-8",
        )
    except UnicodeDecodeError:
        return (
            payload.decode(
                "utf-8",
                errors="replace",
            ),
            "utf-8-replacement",
        )


def looks_textual(
    payload: bytes,
) -> bool:
    if not payload:
        return True

    sample = payload[
        : min(
            len(payload),
            65536,
        )
    ]

    if b"\x00" in sample:
        return False

    control = 0

    for value in sample:
        if (
            value < 9
            or (
                13 < value < 32
            )
        ):
            control += 1

    return (
        control
        / max(
            len(sample),
            1,
        )
        < 0.02
    )


def strip_html(
    value: str,
) -> str:
    value = re.sub(
        r"(?is)<script\b[^>]*>.*?</script>",
        " ",
        value,
    )

    value = re.sub(
        r"(?is)<style\b[^>]*>.*?</style>",
        " ",
        value,
    )

    value = re.sub(
        r"(?s)<[^>]+>",
        " ",
        value,
    )

    value = html.unescape(
        value
    )

    value = re.sub(
        r"[ \t]+",
        " ",
        value,
    )

    value = re.sub(
        r"\n\s*\n\s*\n+",
        "\n\n",
        value,
    )

    return value.strip()


def flatten_json(
    value: Any,
) -> str:
    fragments: list[str] = []

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
            for key, nested in item.items():
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


def record(
    *,
    source: str,
    ordinal: int,
    media_type: str,
    format: str,
    text: str | None,
    byte_size: int,
    source_digest: str,
    substance: Any,
    metadata: Mapping[str, Any] | None = None,
) -> parsed_record:
    return parsed_record(
        source=source,
        ordinal=ordinal,
        media_type=media_type,
        format=format,
        text=text,
        byte_size=byte_size,
        source_digest=source_digest,
        record_digest=digest_value(
            substance
        ),
        metadata=dict(
            metadata
            or {}
        ),
    )


def parse_json_payload(
    *,
    source: str,
    payload: bytes,
    source_digest: str,
) -> tuple[
    tuple[parsed_record, ...],
    tuple[str, ...],
]:
    text, encoding = decode_text(
        payload
    )

    try:
        value = json.loads(
            text
        )
    except json.JSONDecodeError:
        return (
            (
                record(
                    source=source,
                    ordinal=1,
                    media_type="text/plain",
                    format="text",
                    text=text,
                    byte_size=len(payload),
                    source_digest=source_digest,
                    substance=text,
                    metadata={
                        "encoding": encoding,
                        "json_decode_failed": True,
                    },
                ),
            ),
            (
                "json-decode-failed",
            ),
        )

    values = (
        value
        if isinstance(
            value,
            list,
        )
        else [
            value
        ]
    )

    records = tuple(
        record(
            source=source,
            ordinal=ordinal,
            media_type="application/json",
            format="json",
            text=flatten_json(
                item
            ),
            byte_size=len(
                canonical_json(
                    item
                ).encode(
                    "utf-8"
                )
            ),
            source_digest=source_digest,
            substance=item,
            metadata={
                "encoding": encoding,
            },
        )
        for ordinal, item in enumerate(
            values,
            1,
        )
    )

    return (
        records,
        (),
    )


def parse_jsonl_payload(
    *,
    source: str,
    payload: bytes,
    source_digest: str,
) -> tuple[
    tuple[parsed_record, ...],
    tuple[str, ...],
]:
    text, encoding = decode_text(
        payload
    )

    records: list[
        parsed_record
    ] = []

    warnings: list[
        str
    ] = []

    ordinal = 0

    for line_number, line in enumerate(
        text.splitlines(),
        1,
    ):
        stripped = line.strip()

        if not stripped:
            continue

        ordinal += 1

        try:
            value = json.loads(
                stripped
            )

            records.append(
                record(
                    source=source,
                    ordinal=ordinal,
                    media_type="application/x-ndjson",
                    format="jsonl",
                    text=flatten_json(
                        value
                    ),
                    byte_size=len(
                        line.encode(
                            "utf-8"
                        )
                    ),
                    source_digest=source_digest,
                    substance=value,
                    metadata={
                        "encoding": encoding,
                        "line": line_number,
                    },
                )
            )
        except json.JSONDecodeError:
            records.append(
                record(
                    source=source,
                    ordinal=ordinal,
                    media_type="text/plain",
                    format="text",
                    text=line,
                    byte_size=len(
                        line.encode(
                            "utf-8"
                        )
                    ),
                    source_digest=source_digest,
                    substance=line,
                    metadata={
                        "encoding": encoding,
                        "line": line_number,
                        "json_decode_failed": True,
                    },
                )
            )

            warnings.append(
                f"jsonl-decode-failed:{line_number}"
            )

    return (
        tuple(
            records
        ),
        tuple(
            warnings
        ),
    )


def parse_csv_payload(
    *,
    source: str,
    payload: bytes,
    source_digest: str,
    delimiter: str,
) -> tuple[
    tuple[parsed_record, ...],
    tuple[str, ...],
]:
    text, encoding = decode_text(
        payload
    )

    reader = csv.DictReader(
        StringIO(
            text
        ),
        delimiter=delimiter,
    )

    records: list[
        parsed_record
    ] = []

    for ordinal, row in enumerate(
        reader,
        1,
    ):
        normalized = {
            str(
                key
            ): value
            for key, value in row.items()
        }

        records.append(
            record(
                source=source,
                ordinal=ordinal,
                media_type="text/csv",
                format=(
                    "tsv"
                    if delimiter == "\t"
                    else "csv"
                ),
                text=flatten_json(
                    normalized
                ),
                byte_size=len(
                    canonical_json(
                        normalized
                    ).encode(
                        "utf-8"
                    )
                ),
                source_digest=source_digest,
                substance=normalized,
                metadata={
                    "encoding": encoding,
                },
            )
        )

    return (
        tuple(
            records
        ),
        (),
    )


def parse_text_payload(
    *,
    source: str,
    payload: bytes,
    source_digest: str,
    format: str = "text",
    media_type: str = "text/plain",
) -> tuple[
    tuple[parsed_record, ...],
    tuple[str, ...],
]:
    text, encoding = decode_text(
        payload
    )

    if format == "html":
        text = strip_html(
            text
        )

    return (
        (
            record(
                source=source,
                ordinal=1,
                media_type=media_type,
                format=format,
                text=text,
                byte_size=len(payload),
                source_digest=source_digest,
                substance=text,
                metadata={
                    "encoding": encoding,
                },
            ),
        ),
        (),
    )


def parse_binary_payload(
    *,
    source: str,
    payload: bytes,
    source_digest: str,
) -> tuple[
    tuple[parsed_record, ...],
    tuple[str, ...],
]:
    return (
        (
            record(
                source=source,
                ordinal=1,
                media_type="application/octet-stream",
                format="binary",
                text=None,
                byte_size=len(payload),
                source_digest=source_digest,
                substance={
                    "digest": source_digest,
                    "size": len(payload),
                },
                metadata={
                    "semantic_decode": False,
                },
            ),
        ),
        (
            "binary-preserved-without-semantic-decoding",
        ),
    )


def parse_payload(
    *,
    source: str,
    payload: bytes,
    suffix: str,
) -> parse_result:
    source_digest = digest_bytes(
        payload
    )

    normalized_suffix = suffix.lower()

    if normalized_suffix in json_suffixes:
        records, warnings = (
            parse_json_payload(
                source=source,
                payload=payload,
                source_digest=source_digest,
            )
        )

        format = "json"
        media_type = "application/json"

    elif normalized_suffix in jsonl_suffixes:
        records, warnings = (
            parse_jsonl_payload(
                source=source,
                payload=payload,
                source_digest=source_digest,
            )
        )

        format = "jsonl"
        media_type = "application/x-ndjson"

    elif normalized_suffix in csv_suffixes:
        delimiter = (
            "\t"
            if normalized_suffix
            == ".tsv"
            else ","
        )

        records, warnings = (
            parse_csv_payload(
                source=source,
                payload=payload,
                source_digest=source_digest,
                delimiter=delimiter,
            )
        )

        format = (
            "tsv"
            if delimiter == "\t"
            else "csv"
        )

        media_type = "text/csv"

    elif normalized_suffix in html_suffixes:
        records, warnings = (
            parse_text_payload(
                source=source,
                payload=payload,
                source_digest=source_digest,
                format="html",
                media_type="text/html",
            )
        )

        format = "html"
        media_type = "text/html"

    elif (
        normalized_suffix
        in text_suffixes
        or looks_textual(
            payload
        )
    ):
        records, warnings = (
            parse_text_payload(
                source=source,
                payload=payload,
                source_digest=source_digest,
            )
        )

        format = "text"
        media_type = "text/plain"

    else:
        records, warnings = (
            parse_binary_payload(
                source=source,
                payload=payload,
                source_digest=source_digest,
            )
        )

        format = "binary"
        media_type = "application/octet-stream"

    return parse_result(
        source=source,
        source_digest=source_digest,
        byte_size=len(payload),
        format=format,
        media_type=media_type,
        records=records,
        warnings=warnings,
    )


def parse_gzip(
    path: Path,
) -> parse_result:
    try:
        with gzip.open(
            path,
            "rb",
        ) as handle:
            payload = handle.read()
    except OSError as exc:
        raise universal_parser_error(
            f"gzip-read-failed: {path}"
        ) from exc

    inner = Path(
        path.stem
    )

    result = parse_payload(
        source=str(path),
        payload=payload,
        suffix=inner.suffix,
    )

    return parse_result(
        source=result.source,
        source_digest=result.source_digest,
        byte_size=result.byte_size,
        format=f"gzip:{result.format}",
        media_type=result.media_type,
        records=result.records,
        warnings=result.warnings,
    )


def iter_zip_members(
    path: Path,
) -> Iterator[
    parsed_record
]:
    with zipfile.ZipFile(
        path,
        "r",
    ) as archive:
        ordinal = 0

        for info in archive.infolist():
            if info.is_dir():
                continue

            ordinal += 1

            payload = archive.read(
                info
            )

            member_source = (
                f"{path}!/{info.filename}"
            )

            parsed = parse_payload(
                source=member_source,
                payload=payload,
                suffix=Path(
                    info.filename
                ).suffix,
            )

            for child in parsed.records:
                yield parsed_record(
                    source=child.source,
                    ordinal=ordinal,
                    media_type=child.media_type,
                    format=child.format,
                    text=child.text,
                    byte_size=child.byte_size,
                    source_digest=child.source_digest,
                    record_digest=child.record_digest,
                    metadata={
                        **dict(
                            child.metadata
                        ),
                        "container": str(
                            path
                        ),
                        "member": info.filename,
                        "member_ordinal": child.ordinal,
                    },
                )


def parse_zip(
    path: Path,
) -> parse_result:
    payload = path.read_bytes()

    try:
        records = tuple(
            iter_zip_members(
                path
            )
        )
    except (
        OSError,
        zipfile.BadZipFile,
        RuntimeError,
    ) as exc:
        raise universal_parser_error(
            f"zip-read-failed: {path}"
        ) from exc

    return parse_result(
        source=str(path),
        source_digest=digest_bytes(
            payload
        ),
        byte_size=len(payload),
        format="zip",
        media_type="application/zip",
        records=records,
        warnings=(),
    )


def parse_tar(
    path: Path,
) -> parse_result:
    payload = path.read_bytes()

    records: list[
        parsed_record
    ] = []

    try:
        with tarfile.open(
            path,
            "r:*",
        ) as archive:
            ordinal = 0

            for member in archive:
                if not member.isfile():
                    continue

                handle = archive.extractfile(
                    member
                )

                if handle is None:
                    continue

                ordinal += 1

                member_payload = (
                    handle.read()
                )

                member_source = (
                    f"{path}!/{member.name}"
                )

                parsed = parse_payload(
                    source=member_source,
                    payload=member_payload,
                    suffix=Path(
                        member.name
                    ).suffix,
                )

                for child in parsed.records:
                    records.append(
                        parsed_record(
                            source=child.source,
                            ordinal=ordinal,
                            media_type=child.media_type,
                            format=child.format,
                            text=child.text,
                            byte_size=child.byte_size,
                            source_digest=child.source_digest,
                            record_digest=child.record_digest,
                            metadata={
                                **dict(
                                    child.metadata
                                ),
                                "container": str(
                                    path
                                ),
                                "member": member.name,
                                "member_ordinal": child.ordinal,
                            },
                        )
                    )
    except (
        OSError,
        tarfile.TarError,
    ) as exc:
        raise universal_parser_error(
            f"tar-read-failed: {path}"
        ) from exc

    return parse_result(
        source=str(path),
        source_digest=digest_bytes(
            payload
        ),
        byte_size=len(payload),
        format="tar",
        media_type="application/x-tar",
        records=tuple(
            records
        ),
        warnings=(),
    )


def parse_file(
    path: str | Path,
) -> parse_result:
    source = Path(
        path
    )

    if not source.is_file():
        raise universal_parser_error(
            f"file-unavailable: {source}"
        )

    suffix = source.suffix.lower()

    if suffix in zip_suffixes:
        return parse_zip(
            source
        )

    if (
        suffix in tar_suffixes
        or source.name.lower().endswith(
            (
                ".tar.gz",
                ".tar.bz2",
                ".tar.xz",
            )
        )
    ):
        return parse_tar(
            source
        )

    if suffix in gzip_suffixes:
        return parse_gzip(
            source
        )

    try:
        payload = source.read_bytes()
    except OSError as exc:
        raise universal_parser_error(
            f"file-read-failed: {source}"
        ) from exc

    return parse_payload(
        source=str(
            source
        ),
        payload=payload,
        suffix=suffix,
    )


def iter_path(
    path: str | Path,
) -> Iterator[
    parse_result
]:
    source = Path(
        path
    )

    if source.is_file():
        yield parse_file(
            source
        )
        return

    if not source.is_dir():
        raise universal_parser_error(
            f"path-unavailable: {source}"
        )

    for item in sorted(
        (
            candidate
            for candidate
            in source.rglob("*")
            if candidate.is_file()
        ),
        key=str,
    ):
        yield parse_file(
            item
        )


def selftest() -> dict[str, Any]:
    payload = json.dumps(
        [
            {
                "name": "savant",
                "kind": "test",
            },
            {
                "name": "sieve",
                "kind": "test",
            },
        ]
    ).encode(
        "utf-8"
    )

    result = parse_payload(
        source="selftest.json",
        payload=payload,
        suffix=".json",
    )

    checks = {
        "authority_none":
            authority_effect
            == "none",
        "level_04":
            utility_ordinal
            == 4,
        "universally_reusable":
            universally_reusable
            is True,
        "record_count":
            len(
                result.records
            )
            == 2,
        "deterministic_digest":
            result.source_digest
            == digest_bytes(
                payload
            ),
        "text_projection":
            "savant"
            in (
                result.records[
                    0
                ].text
                or ""
            ),
    }

    return {
        "schema":
            "savant://utility/epiphany/"
            "universal-parser-selftest/1.0.0",
        "ok": all(
            checks.values()
        ),
        "checks": checks,
    }


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(
        description=(
            "Parse heterogeneous files into "
            "normalized rebuildable records."
        )
    )

    parser.add_argument(
        "source",
        nargs="?",
    )

    parser.add_argument(
        "--selftest",
        action="store_true",
    )

    arguments = parser.parse_args()

    if arguments.selftest:
        print(
            json.dumps(
                selftest(),
                ensure_ascii=False,
                sort_keys=True,
                indent=2,
            )
        )
        return 0

    if not arguments.source:
        raise universal_parser_error(
            "source is required"
        )

    for result in iter_path(
        arguments.source
    ):
        print(
            json.dumps(
                result.projection(),
                ensure_ascii=False,
                sort_keys=True,
            )
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
