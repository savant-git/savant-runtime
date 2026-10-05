#!/usr/bin/env python3

from __future__ import annotations

import csv
import gzip
import hashlib
import html
from html.parser import HTMLParser
import io
import json
import mailbox
import mimetypes
import os
from pathlib import Path
import tarfile
import tempfile
from typing import Any, Iterable, Iterator, Mapping
import zipfile


schema = "savant://runtime/extr/importer/1.0.0"
owner = "extr"
authority_effect = "none"


class importer_error(RuntimeError):
    pass


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as handle:
        while True:
            block = handle.read(
                1024 * 1024
            )

            if not block:
                break

            digest.update(block)

    return digest.hexdigest()


def canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )


def stable_id(prefix: str, value: Any) -> str:
    return (
        prefix
        + ":"
        + hashlib.sha256(
            canonical_json(
                value
            ).encode("utf-8")
        ).hexdigest()
    )


def safe_text(
    path: Path,
) -> str:
    raw = path.read_bytes()

    for encoding in (
        "utf-8",
        "utf-8-sig",
        "utf-16",
        "latin-1",
    ):
        try:
            return raw.decode(
                encoding
            )
        except UnicodeDecodeError:
            continue

    return raw.decode(
        "utf-8",
        errors="replace",
    )


class html_text_parser(
    HTMLParser
):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []
        self._ignored = 0

    def handle_starttag(
        self,
        tag: str,
        attrs: list[
            tuple[str, str | None]
        ],
    ) -> None:
        if tag in (
            "script",
            "style",
        ):
            self._ignored += 1

        if tag in (
            "p",
            "br",
            "div",
            "li",
            "h1",
            "h2",
            "h3",
            "h4",
            "tr",
        ):
            self.parts.append("\n")

    def handle_endtag(
        self,
        tag: str,
    ) -> None:
        if (
            tag in (
                "script",
                "style",
            )
            and self._ignored
        ):
            self._ignored -= 1

    def handle_data(
        self,
        data: str,
    ) -> None:
        if not self._ignored:
            self.parts.append(data)

    def text(self) -> str:
        return html.unescape(
            "".join(
                self.parts
            )
        ).strip()


def base_record(
    path: Path,
    *,
    source_digest: str,
    kind: str,
    locator: str,
    content: Any,
    metadata: Mapping[
        str,
        Any,
    ] | None = None,
) -> dict[str, Any]:
    identity = {
        "source_digest":
            source_digest,
        "locator":
            locator,
        "kind":
            kind,
    }

    return {
        "schema":
            "savant://runtime/extr/"
            "imported-datum/1.0.0",
        "id":
            stable_id(
                "extr:datum",
                identity,
            ),
        "owner": owner,
        "authority_effect":
            authority_effect,
        "authoritative": False,
        "source": {
            "path": str(path),
            "sha256":
                source_digest,
            "locator":
                locator,
        },
        "kind": kind,
        "content": content,
        "metadata":
            dict(metadata or {}),
        "lineage": {
            "source_sha256":
                source_digest,
            "source_locator":
                locator,
        },
    }


def import_json(
    path: Path,
    digest: str,
) -> Iterator[
    dict[str, Any]
]:
    value = json.loads(
        safe_text(path)
    )

    if isinstance(value, list):
        for index, item in enumerate(
            value
        ):
            yield base_record(
                path,
                source_digest=digest,
                kind="json",
                locator=f"$[{index}]",
                content=item,
            )
    else:
        yield base_record(
            path,
            source_digest=digest,
            kind="json",
            locator="$",
            content=value,
        )


def import_jsonl(
    path: Path,
    digest: str,
) -> Iterator[
    dict[str, Any]
]:
    with path.open(
        "r",
        encoding="utf-8",
        errors="replace",
    ) as handle:
        for line_number, line in enumerate(
            handle,
            1,
        ):
            line = line.strip()

            if not line:
                continue

            try:
                value = json.loads(
                    line
                )
                metadata = {}
            except Exception as exc:
                value = line
                metadata = {
                    "parse_error":
                        str(exc)
                }

            yield base_record(
                path,
                source_digest=digest,
                kind="jsonl",
                locator=(
                    f"line:{line_number}"
                ),
                content=value,
                metadata=metadata,
            )


def import_csv_like(
    path: Path,
    digest: str,
    delimiter: str,
) -> Iterator[
    dict[str, Any]
]:
    with path.open(
        "r",
        encoding="utf-8-sig",
        errors="replace",
        newline="",
    ) as handle:
        reader = csv.DictReader(
            handle,
            delimiter=delimiter,
        )

        for row_number, row in enumerate(
            reader,
            2,
        ):
            yield base_record(
                path,
                source_digest=digest,
                kind="table-row",
                locator=(
                    f"row:{row_number}"
                ),
                content=dict(row),
            )


def import_html(
    path: Path,
    digest: str,
) -> Iterator[
    dict[str, Any]
]:
    parser = html_text_parser()
    parser.feed(
        safe_text(path)
    )

    yield base_record(
        path,
        source_digest=digest,
        kind="text",
        locator="document",
        content=parser.text(),
        metadata={
            "source_format":
                "html"
        },
    )


def import_text(
    path: Path,
    digest: str,
) -> Iterator[
    dict[str, Any]
]:
    yield base_record(
        path,
        source_digest=digest,
        kind="text",
        locator="document",
        content=safe_text(path),
        metadata={
            "mime":
                mimetypes.guess_type(
                    path.name
                )[0]
        },
    )


def import_eml(
    path: Path,
    digest: str,
) -> Iterator[
    dict[str, Any]
]:
    from email import policy
    from email.parser import BytesParser

    message = BytesParser(
        policy=policy.default
    ).parsebytes(
        path.read_bytes()
    )

    parts = []

    if message.is_multipart():
        for part in message.walk():
            if (
                part.get_content_type()
                == "text/plain"
            ):
                try:
                    parts.append(
                        part.get_content()
                    )
                except Exception:
                    pass
    else:
        try:
            parts.append(
                message.get_content()
            )
        except Exception:
            pass

    yield base_record(
        path,
        source_digest=digest,
        kind="email",
        locator="message",
        content="\n".join(
            str(part)
            for part in parts
        ),
        metadata={
            "subject":
                message.get(
                    "subject"
                ),
            "from":
                message.get("from"),
            "to":
                message.get("to"),
            "date":
                message.get("date"),
            "message_id":
                message.get(
                    "message-id"
                ),
        },
    )


def import_mbox(
    path: Path,
    digest: str,
) -> Iterator[
    dict[str, Any]
]:
    box = mailbox.mbox(
        str(path),
        create=False,
    )

    try:
        for index, message in enumerate(
            box
        ):
            payload = message.get_payload(
                decode=True
            )

            if isinstance(payload, bytes):
                content = payload.decode(
                    "utf-8",
                    errors="replace",
                )
            else:
                content = str(
                    message.get_payload()
                )

            yield base_record(
                path,
                source_digest=digest,
                kind="email",
                locator=(
                    f"message:{index}"
                ),
                content=content,
                metadata={
                    "subject":
                        message.get(
                            "subject"
                        ),
                    "from":
                        message.get(
                            "from"
                        ),
                    "to":
                        message.get(
                            "to"
                        ),
                    "date":
                        message.get(
                            "date"
                        ),
                    "message_id":
                        message.get(
                            "message-id"
                        ),
                },
            )
    finally:
        box.close()


def import_docx(
    path: Path,
    digest: str,
) -> Iterator[
    dict[str, Any]
]:
    with zipfile.ZipFile(
        path
    ) as archive:
        try:
            xml = archive.read(
                "word/document.xml"
            ).decode(
                "utf-8",
                errors="replace",
            )
        except KeyError as exc:
            raise importer_error(
                "invalid docx"
            ) from exc

    text = re_xml_text(xml)

    yield base_record(
        path,
        source_digest=digest,
        kind="text",
        locator="document",
        content=text,
        metadata={
            "source_format":
                "docx"
        },
    )


def re_xml_text(
    xml: str,
) -> str:
    import xml.etree.ElementTree as ET

    root = ET.fromstring(xml)

    parts = []

    for element in root.iter():
        if element.text:
            parts.append(
                element.text
            )

        if element.tag.endswith(
            "}p"
        ):
            parts.append("\n")

    return "".join(
        parts
    ).strip()


def import_xlsx(
    path: Path,
    digest: str,
) -> Iterator[
    dict[str, Any]
]:
    import xml.etree.ElementTree as ET

    with zipfile.ZipFile(
        path
    ) as archive:
        shared: list[str] = []

        if (
            "xl/sharedStrings.xml"
            in archive.namelist()
        ):
            root = ET.fromstring(
                archive.read(
                    "xl/sharedStrings.xml"
                )
            )

            for item in root:
                shared.append(
                    "".join(
                        node.text or ""
                        for node
                        in item.iter()
                        if node.tag.endswith(
                            "}t"
                        )
                    )
                )

        sheets = sorted(
            name
            for name
            in archive.namelist()
            if name.startswith(
                "xl/worksheets/sheet"
            )
            and name.endswith(
                ".xml"
            )
        )

        for sheet_name in sheets:
            root = ET.fromstring(
                archive.read(
                    sheet_name
                )
            )

            for row_index, row in enumerate(
                (
                    node
                    for node in root.iter()
                    if node.tag.endswith(
                        "}row"
                    )
                ),
                1,
            ):
                cells = []

                for cell in row:
                    if not cell.tag.endswith(
                        "}c"
                    ):
                        continue

                    value_node = next(
                        (
                            node
                            for node
                            in cell
                            if node.tag.endswith(
                                "}v"
                            )
                        ),
                        None,
                    )

                    value = (
                        value_node.text
                        if value_node
                        is not None
                        else ""
                    )

                    if (
                        cell.attrib.get(
                            "t"
                        )
                        == "s"
                        and value
                    ):
                        try:
                            value = shared[
                                int(value)
                            ]
                        except Exception:
                            pass

                    cells.append(
                        {
                            "reference":
                                cell.attrib.get(
                                    "r"
                                ),
                            "value":
                                value,
                        }
                    )

                yield base_record(
                    path,
                    source_digest=digest,
                    kind="table-row",
                    locator=(
                        f"{sheet_name}:"
                        f"row:{row_index}"
                    ),
                    content=cells,
                    metadata={
                        "sheet":
                            sheet_name
                    },
                )


def import_pdf(
    path: Path,
    digest: str,
) -> Iterator[
    dict[str, Any]
]:
    try:
        from pypdf import PdfReader
    except ImportError as exc:
        raise importer_error(
            "pdf extraction requires "
            "the existing pypdf dependency"
        ) from exc

    reader = PdfReader(
        str(path)
    )

    for page_number, page in enumerate(
        reader.pages,
        1,
    ):
        text = page.extract_text() or ""

        yield base_record(
            path,
            source_digest=digest,
            kind="text",
            locator=(
                f"page:{page_number}"
            ),
            content=text,
            metadata={
                "source_format":
                    "pdf",
                "page":
                    page_number,
            },
        )


def archive_members(
    path: Path,
) -> Iterator[
    tuple[str, bytes]
]:
    suffix = path.suffix.lower()

    if suffix == ".zip":
        with zipfile.ZipFile(
            path
        ) as archive:
            for info in archive.infolist():
                if info.is_dir():
                    continue

                yield (
                    info.filename,
                    archive.read(info),
                )

        return

    if (
        suffix in (
            ".tar",
            ".tgz",
        )
        or path.name.lower().endswith(
            ".tar.gz"
        )
    ):
        with tarfile.open(
            path,
            "r:*",
        ) as archive:
            for member in archive:
                if not member.isfile():
                    continue

                extracted = archive.extractfile(
                    member
                )

                if extracted is None:
                    continue

                yield (
                    member.name,
                    extracted.read(),
                )

        return

    if suffix == ".gz":
        with gzip.open(
            path,
            "rb",
        ) as handle:
            yield (
                path.stem,
                handle.read(),
            )

        return

    raise importer_error(
        f"unsupported archive: {path}"
    )


def import_archive(
    path: Path,
    digest: str,
    *,
    depth: int,
    max_depth: int,
) -> Iterator[
    dict[str, Any]
]:
    if depth >= max_depth:
        yield base_record(
            path,
            source_digest=digest,
            kind="archive",
            locator="archive",
            content=None,
            metadata={
                "reason":
                    "maximum archive "
                    "depth reached"
            },
        )
        return

    with tempfile.TemporaryDirectory(
        prefix="extr-import-"
    ) as temporary:
        root = Path(temporary)

        for index, (
            member_name,
            payload,
        ) in enumerate(
            archive_members(path)
        ):
            safe_name = (
                Path(member_name).name
                or f"member-{index}"
            )

            member_path = (
                root
                / f"{index}-{safe_name}"
            )

            member_path.write_bytes(
                payload
            )

            for record in import_path(
                member_path,
                depth=depth + 1,
                max_depth=max_depth,
            ):
                projected = dict(record)

                projected[
                    "archive"
                ] = {
                    "container":
                        str(path),
                    "container_sha256":
                        digest,
                    "member":
                        member_name,
                }

                yield projected


def binary_fallback(
    path: Path,
    digest: str,
) -> Iterator[
    dict[str, Any]
]:
    yield base_record(
        path,
        source_digest=digest,
        kind="binary",
        locator="file",
        content=None,
        metadata={
            "size":
                path.stat().st_size,
            "mime":
                mimetypes.guess_type(
                    path.name
                )[0],
            "extension":
                path.suffix.lower(),
        },
    )


def import_path(
    path: Path,
    *,
    depth: int = 0,
    max_depth: int = 4,
) -> Iterator[
    dict[str, Any]
]:
    path = path.resolve()

    if not path.is_file():
        raise importer_error(
            f"not a file: {path}"
        )

    digest = sha256_file(path)
    suffix = path.suffix.lower()
    lower_name = path.name.lower()

    if suffix == ".json":
        yield from import_json(
            path,
            digest,
        )
        return

    if suffix in (
        ".jsonl",
        ".ndjson",
    ):
        yield from import_jsonl(
            path,
            digest,
        )
        return

    if suffix == ".csv":
        yield from import_csv_like(
            path,
            digest,
            ",",
        )
        return

    if suffix == ".tsv":
        yield from import_csv_like(
            path,
            digest,
            "\t",
        )
        return

    if suffix in (
        ".html",
        ".htm",
    ):
        yield from import_html(
            path,
            digest,
        )
        return

    if suffix == ".eml":
        yield from import_eml(
            path,
            digest,
        )
        return

    if suffix == ".mbox":
        yield from import_mbox(
            path,
            digest,
        )
        return

    if suffix == ".docx":
        yield from import_docx(
            path,
            digest,
        )
        return

    if suffix == ".xlsx":
        yield from import_xlsx(
            path,
            digest,
        )
        return

    if suffix == ".pdf":
        yield from import_pdf(
            path,
            digest,
        )
        return

    if (
        suffix in (
            ".zip",
            ".tar",
            ".tgz",
            ".gz",
        )
        or lower_name.endswith(
            ".tar.gz"
        )
    ):
        yield from import_archive(
            path,
            digest,
            depth=depth,
            max_depth=max_depth,
        )
        return

    if suffix in (
        ".txt",
        ".md",
        ".markdown",
        ".rst",
        ".log",
        ".xml",
        ".yaml",
        ".yml",
        ".toml",
        ".rtf",
    ):
        yield from import_text(
            path,
            digest,
        )
        return

    yield from binary_fallback(
        path,
        digest,
    )


def selftest() -> dict[str, Any]:
    with tempfile.TemporaryDirectory(
        prefix="extr-import-test-"
    ) as temporary:
        root = Path(temporary)

        text_path = (
            root / "test.txt"
        )

        text_path.write_text(
            "savant test",
            encoding="utf-8",
        )

        json_path = (
            root / "test.json"
        )

        json_path.write_text(
            json.dumps(
                [
                    {"a": 1},
                    {"b": 2},
                ]
            ),
            encoding="utf-8",
        )

        text_records = list(
            import_path(
                text_path
            )
        )

        json_records = list(
            import_path(
                json_path
            )
        )

        checks = {
            "text_imported":
                len(text_records)
                == 1,
            "json_expanded":
                len(json_records)
                == 2,
            "source_hashed":
                bool(
                    text_records[0][
                        "source"
                    ]["sha256"]
                ),
            "lineage":
                text_records[0][
                    "lineage"
                ][
                    "source_sha256"
                ]
                == text_records[0][
                    "source"
                ]["sha256"],
            "no_authority":
                text_records[0][
                    "authority_effect"
                ]
                == "none",
        }

        return {
            "schema":
                "savant://runtime/extr/"
                "importer-selftest/1.0.0",
            "ok": all(
                checks.values()
            ),
            "checks": checks,
        }


if __name__ == "__main__":
    print(
        json.dumps(
            selftest(),
            sort_keys=True,
            indent=2,
        )
    )
