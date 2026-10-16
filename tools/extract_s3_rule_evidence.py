#!/usr/bin/env python3

from __future__ import annotations

import argparse
import hashlib
import io
import json
import re
import shutil
import subprocess
import sys
import urllib.request
import zipfile
from collections import OrderedDict
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath


S3_URI = (
    "s3://savant-ai-cluster/portable/"
    "ae2420cc26989b23f18f3dd579c69f2c9c8d9d107d90793173cf4f8fe74af1af"
    "-2026-09-25-06-40-32-854ab2a06c234c1d943dc3e42990ac00.zip"
)

DEFAULT_ROOT = Path(
    "/root/savant-runtime/audit/archive-rule-extraction/"
    "ae2420cc26989b23f18f3dd579c69f2c9c8d9d107d90793173cf4f8fe74af1af"
)

BLOCK_SIZE = 8 * 1024 * 1024
MAX_CACHE_BLOCKS = 16

# chat.html is 392,433,174 bytes uncompressed.
# 512 MiB admits it while retaining a bounded per-member ceiling.
MAX_TEXT_MEMBER = 512 * 1024 * 1024

TEXT_EXTENSIONS = {
    ".txt",
    ".md",
    ".markdown",
    ".rst",
    ".adoc",
    ".json",
    ".jsonl",
    ".yaml",
    ".yml",
    ".toml",
    ".xml",
    ".html",
    ".htm",
    ".css",
    ".scss",
    ".js",
    ".mjs",
    ".cjs",
    ".ts",
    ".tsx",
    ".jsx",
    ".py",
    ".pyi",
    ".sh",
    ".bash",
    ".zsh",
    ".fish",
    ".ps1",
    ".bat",
    ".cmd",
    ".c",
    ".h",
    ".cc",
    ".cpp",
    ".hpp",
    ".cs",
    ".java",
    ".kt",
    ".kts",
    ".go",
    ".rs",
    ".rb",
    ".php",
    ".pl",
    ".pm",
    ".sql",
    ".graphql",
    ".gql",
    ".ini",
    ".cfg",
    ".conf",
    ".properties",
    ".env",
    ".service",
    ".timer",
    ".socket",
    ".gitignore",
    ".dockerignore",
}

TEXT_BASENAMES = {
    "dockerfile",
    "makefile",
    "license",
    "readme",
    "changelog",
    "manifest",
}

RULE_TERMS = re.compile(
    r"""
    \b(
        must |
        must\ not |
        shall |
        shall\ not |
        should |
        should\ not |
        required |
        requirement |
        invariant |
        rule |
        law |
        canon |
        constitutional |
        authority |
        authoritative |
        prohibited |
        forbidden |
        never |
        always |
        only |
        preserve |
        immutable |
        deterministic |
        determinism |
        provenance |
        lineage |
        supersede |
        superseded |
        precedence |
        constraint |
        contract |
        ownership |
        owner |
        responsibility |
        admission |
        admitted |
        evidence |
        validation |
        compatibility |
        migration |
        mutation |
        projection |
        composition |
        compose |
        instance |
        segue |
        glyph |
        temper |
        skein |
        inversa |
        fate |
        rote
    )\b
    """,
    re.IGNORECASE | re.VERBOSE,
)

HEADING_RE = re.compile(
    r"(?m)^(?:"
    r"#{1,6}\s+.+|"
    r"[A-Z][A-Z0-9 _:/().,'\-]{5,}|"
    r"\d+(?:\.\d+)*[.)]?\s+.+"
    r")$"
)

SECRET_RE = re.compile(
    r"""
    (
        aws_access_key_id |
        aws_secret_access_key |
        aws_session_token |
        api[_-]?key |
        secret[_-]?key |
        password |
        passwd |
        bearer |
        authorization
    )
    \s*[:=]\s*
    ([^\s"'`]+)
    """,
    re.IGNORECASE | re.VERBOSE,
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def safe_relative_path(name: str) -> Path:
    path = PurePosixPath(name)
    clean_parts: list[str] = []

    for part in path.parts:
        if part in ("", ".", "/"):
            continue

        if part == "..":
            clean_parts.append("__parent__")
            continue

        clean_parts.append(part.replace("\x00", "_"))

    if not clean_parts:
        clean_parts = ["__unnamed__"]

    return Path(*clean_parts)


def redact_secrets(text: str) -> tuple[str, int]:
    count = 0

    def replacement(match: re.Match[str]) -> str:
        nonlocal count
        count += 1
        return f"{match.group(1)}=[redacted]"

    return SECRET_RE.sub(replacement, text), count


def looks_textual(name: str, sample: bytes) -> bool:
    path = Path(name.lower())
    suffix = path.suffix
    basename = path.name

    if suffix in TEXT_EXTENSIONS:
        return True

    if basename in TEXT_BASENAMES:
        return True

    if not sample:
        return True

    if b"\x00" in sample:
        return False

    printable = 0

    for byte in sample:
        if byte in (9, 10, 13) or 32 <= byte <= 126 or byte >= 128:
            printable += 1

    return printable / len(sample) >= 0.88


def decode_text(data: bytes) -> tuple[str, str]:
    encodings = (
        "utf-8",
        "utf-8-sig",
        "utf-16",
        "utf-16-le",
        "utf-16-be",
        "latin-1",
    )

    for encoding in encodings:
        try:
            return data.decode(encoding), encoding
        except UnicodeDecodeError:
            continue

    return (
        data.decode("utf-8", errors="replace"),
        "utf-8-replacement",
    )


def extract_candidate_windows(text: str) -> list[dict]:
    lines = text.splitlines()
    candidate_lines: set[int] = set()

    for index, line in enumerate(lines):
        if RULE_TERMS.search(line):
            candidate_lines.add(index)

    windows: list[dict] = []
    consumed: set[int] = set()

    for index in sorted(candidate_lines):
        if index in consumed:
            continue

        start = max(0, index - 3)
        end = min(len(lines), index + 4)

        while (
            start > 0
            and lines[start - 1].strip()
            and index - start < 10
        ):
            if HEADING_RE.match(lines[start - 1]):
                start -= 1
                break

            start -= 1

        while (
            end < len(lines)
            and lines[end].strip()
            and end - index < 10
        ):
            end += 1

        for line_number in range(start, end):
            consumed.add(line_number)

        excerpt = "\n".join(lines[start:end]).strip()

        if excerpt:
            windows.append(
                {
                    "line_start": start + 1,
                    "line_end": end,
                    "text": excerpt,
                }
            )

    return windows


class RemoteRangeReader(io.RawIOBase):
    def __init__(
        self,
        url: str,
        block_size: int = BLOCK_SIZE,
        max_blocks: int = MAX_CACHE_BLOCKS,
    ):
        super().__init__()

        self.url = url
        self.block_size = block_size
        self.max_blocks = max_blocks
        self.position = 0
        self.cache: OrderedDict[int, bytes] = OrderedDict()
        self.size = self._discover_size()

    def _request(
        self,
        start: int | None = None,
        end: int | None = None,
    ):
        request = urllib.request.Request(self.url)

        if start is not None:
            if end is None:
                request.add_header(
                    "Range",
                    f"bytes={start}-",
                )
            else:
                request.add_header(
                    "Range",
                    f"bytes={start}-{end}",
                )

        return urllib.request.urlopen(
            request,
            timeout=120,
        )

    def _discover_size(self) -> int:
        request = urllib.request.Request(
            self.url,
            method="HEAD",
        )

        try:
            with urllib.request.urlopen(
                request,
                timeout=120,
            ) as response:
                value = response.headers.get(
                    "Content-Length"
                )

                if value is not None:
                    return int(value)
        except Exception:
            pass

        with self._request(0, 0) as response:
            content_range = response.headers.get(
                "Content-Range"
            )

            if content_range and "/" in content_range:
                return int(
                    content_range.rsplit("/", 1)[1]
                )

            data = response.read()
            content_length = response.headers.get(
                "Content-Length"
            )

            if (
                response.status == 200
                and content_length
            ):
                return int(content_length)

            if response.status == 200:
                return len(data)

        raise RuntimeError(
            "unable to determine remote object size"
        )

    def readable(self) -> bool:
        return True

    def seekable(self) -> bool:
        return True

    def tell(self) -> int:
        return self.position

    def seek(
        self,
        offset: int,
        whence: int = io.SEEK_SET,
    ) -> int:
        if whence == io.SEEK_SET:
            new_position = offset
        elif whence == io.SEEK_CUR:
            new_position = self.position + offset
        elif whence == io.SEEK_END:
            new_position = self.size + offset
        else:
            raise ValueError("invalid whence")

        if new_position < 0:
            raise ValueError(
                "negative seek position"
            )

        self.position = min(
            new_position,
            self.size,
        )

        return self.position

    def _get_block(
        self,
        block_index: int,
    ) -> bytes:
        if block_index in self.cache:
            data = self.cache.pop(block_index)
            self.cache[block_index] = data
            return data

        start = block_index * self.block_size

        if start >= self.size:
            return b""

        end = min(
            self.size - 1,
            start + self.block_size - 1,
        )

        with self._request(
            start,
            end,
        ) as response:
            data = response.read()

        expected = end - start + 1

        if len(data) != expected:
            if (
                len(data) == self.size
                and start == 0
            ):
                data = data[:expected]
            else:
                raise IOError(
                    "range read length mismatch: "
                    f"requested={expected} "
                    f"received={len(data)} "
                    f"range={start}-{end}"
                )

        self.cache[block_index] = data

        while len(self.cache) > self.max_blocks:
            self.cache.popitem(last=False)

        return data

    def read(
        self,
        size: int = -1,
    ) -> bytes:
        if self.position >= self.size:
            return b""

        if size is None or size < 0:
            size = self.size - self.position
        else:
            size = min(
                size,
                self.size - self.position,
            )

        remaining = size
        chunks: list[bytes] = []

        while remaining > 0:
            block_index = (
                self.position // self.block_size
            )
            offset = (
                self.position % self.block_size
            )

            block = self._get_block(
                block_index
            )

            if not block:
                break

            take = min(
                remaining,
                len(block) - offset,
            )

            if take <= 0:
                break

            chunks.append(
                block[offset:offset + take]
            )

            self.position += take
            remaining -= take

        return b"".join(chunks)


def get_presigned_url(
    s3_uri: str,
    expires: int,
) -> str:
    aws = shutil.which("aws")

    if not aws:
        raise RuntimeError(
            "aws cli is not installed or "
            "is not available on PATH"
        )

    result = subprocess.run(
        [
            aws,
            "s3",
            "presign",
            s3_uri,
            "--expires-in",
            str(expires),
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    url = result.stdout.strip()

    if not url.startswith("https://"):
        raise RuntimeError(
            "aws cli did not return an "
            "https presigned url"
        )

    return url


def process_archive(
    s3_uri: str,
    output_root: Path,
    expires: int,
) -> dict:
    output_root.mkdir(
        parents=True,
        exist_ok=True,
    )

    text_root = output_root / "text"
    text_root.mkdir(
        parents=True,
        exist_ok=True,
    )

    manifest_path = (
        output_root / "manifest.jsonl"
    )
    candidate_path = (
        output_root / "rule_candidates.jsonl"
    )
    summary_path = (
        output_root / "summary.json"
    )

    presigned_url = get_presigned_url(
        s3_uri,
        expires,
    )

    remote = RemoteRangeReader(
        presigned_url
    )

    stats = {
        "archive_uri": s3_uri,
        "started_at": utc_now(),
        "remote_size_bytes": remote.size,
        "members_total": 0,
        "directories": 0,
        "text_members": 0,
        "binary_members": 0,
        "oversize_text_members": 0,
        "member_errors": 0,
        "uncompressed_bytes_accounted": 0,
        "text_bytes_accounted": 0,
        "candidate_windows": 0,
        "redactions": 0,
    }

    with zipfile.ZipFile(
        remote,
        "r",
    ) as archive:
        infos = archive.infolist()

        stats["members_total"] = len(infos)

        with (
            manifest_path.open(
                "w",
                encoding="utf-8",
            ) as manifest_handle,
            candidate_path.open(
                "w",
                encoding="utf-8",
            ) as candidate_handle,
        ):
            for ordinal, info in enumerate(
                infos,
                start=1,
            ):
                base_record = {
                    "ordinal": ordinal,
                    "archive_path": info.filename,
                    "compressed_size": (
                        info.compress_size
                    ),
                    "uncompressed_size": (
                        info.file_size
                    ),
                    "crc32": f"{info.CRC:08x}",
                    "compression_type": (
                        info.compress_type
                    ),
                    "is_directory": (
                        info.is_dir()
                    ),
                }

                stats[
                    "uncompressed_bytes_accounted"
                ] += info.file_size

                if info.is_dir():
                    stats["directories"] += 1

                    record = {
                        **base_record,
                        "classification": (
                            "directory"
                        ),
                    }

                    manifest_handle.write(
                        json.dumps(
                            record,
                            ensure_ascii=False,
                            sort_keys=True,
                        )
                        + "\n"
                    )

                    continue

                try:
                    with archive.open(
                        info,
                        "r",
                    ) as member:
                        sample = member.read(
                            min(
                                info.file_size,
                                65536,
                            )
                        )

                    textual = looks_textual(
                        info.filename,
                        sample,
                    )

                    if (
                        textual
                        and info.file_size
                        > MAX_TEXT_MEMBER
                    ):
                        stats[
                            "oversize_text_members"
                        ] += 1

                        record = {
                            **base_record,
                            "classification": (
                                "text_oversize"
                            ),
                            "sha256": None,
                            "extracted": False,
                            "reason": (
                                "text member exceeds "
                                "bounded extraction limit "
                                f"of {MAX_TEXT_MEMBER} "
                                "bytes"
                            ),
                        }

                        manifest_handle.write(
                            json.dumps(
                                record,
                                ensure_ascii=False,
                                sort_keys=True,
                            )
                            + "\n"
                        )

                        continue

                    hasher = hashlib.sha256()
                    chunks: list[bytes] = []

                    with archive.open(
                        info,
                        "r",
                    ) as member:
                        while True:
                            chunk = member.read(
                                1024 * 1024
                            )

                            if not chunk:
                                break

                            hasher.update(chunk)

                            if textual:
                                chunks.append(
                                    chunk
                                )

                    digest = (
                        hasher.hexdigest()
                    )

                    if not textual:
                        stats[
                            "binary_members"
                        ] += 1

                        record = {
                            **base_record,
                            "classification": (
                                "binary"
                            ),
                            "sha256": digest,
                            "extracted": False,
                        }

                        manifest_handle.write(
                            json.dumps(
                                record,
                                ensure_ascii=False,
                                sort_keys=True,
                            )
                            + "\n"
                        )

                        continue

                    raw = b"".join(chunks)

                    stats[
                        "text_members"
                    ] += 1

                    stats[
                        "text_bytes_accounted"
                    ] += len(raw)

                    text, encoding = (
                        decode_text(raw)
                    )

                    (
                        redacted_text,
                        redactions,
                    ) = redact_secrets(text)

                    stats[
                        "redactions"
                    ] += redactions

                    safe_path = (
                        safe_relative_path(
                            info.filename
                        )
                    )

                    destination = (
                        text_root / safe_path
                    )

                    if destination.suffix:
                        destination = (
                            destination.with_suffix(
                                destination.suffix
                                + ".txt"
                            )
                        )
                    else:
                        destination = Path(
                            str(destination)
                            + ".txt"
                        )

                    destination.parent.mkdir(
                        parents=True,
                        exist_ok=True,
                    )

                    destination.write_text(
                        redacted_text,
                        encoding="utf-8",
                    )

                    windows = (
                        extract_candidate_windows(
                            redacted_text
                        )
                    )

                    record = {
                        **base_record,
                        "classification": "text",
                        "sha256": digest,
                        "encoding_detected": (
                            encoding
                        ),
                        "redactions": redactions,
                        "extracted": True,
                        "extracted_path": str(
                            destination.relative_to(
                                output_root
                            )
                        ),
                        "candidate_windows": len(
                            windows
                        ),
                    }

                    manifest_handle.write(
                        json.dumps(
                            record,
                            ensure_ascii=False,
                            sort_keys=True,
                        )
                        + "\n"
                    )

                    for (
                        window_index,
                        window,
                    ) in enumerate(
                        windows,
                        start=1,
                    ):
                        candidate = {
                            "archive_path": (
                                info.filename
                            ),
                            "member_sha256": (
                                digest
                            ),
                            "window": (
                                window_index
                            ),
                            **window,
                        }

                        candidate_handle.write(
                            json.dumps(
                                candidate,
                                ensure_ascii=False,
                                sort_keys=True,
                            )
                            + "\n"
                        )

                        stats[
                            "candidate_windows"
                        ] += 1

                except Exception as exc:
                    stats[
                        "member_errors"
                    ] += 1

                    record = {
                        **base_record,
                        "classification": (
                            "error"
                        ),
                        "error_type": (
                            type(exc).__name__
                        ),
                        "error": str(exc),
                    }

                    manifest_handle.write(
                        json.dumps(
                            record,
                            ensure_ascii=False,
                            sort_keys=True,
                        )
                        + "\n"
                    )

    stats["completed_at"] = utc_now()

    stats["manifest_sha256"] = (
        hashlib.sha256(
            manifest_path.read_bytes()
        ).hexdigest()
    )

    stats["rule_candidates_sha256"] = (
        hashlib.sha256(
            candidate_path.read_bytes()
        ).hexdigest()
    )

    summary_path.write_text(
        json.dumps(
            stats,
            indent=2,
            ensure_ascii=False,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    return stats


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "extract provenance-preserving "
            "textual evidence and rule "
            "candidates from the savant "
            "portable s3 archive"
        )
    )

    parser.add_argument(
        "--s3-uri",
        default=S3_URI,
    )

    parser.add_argument(
        "--output-root",
        type=Path,
        default=DEFAULT_ROOT,
    )

    parser.add_argument(
        "--presign-seconds",
        type=int,
        default=21600,
    )

    args = parser.parse_args()

    try:
        stats = process_archive(
            args.s3_uri,
            args.output_root,
            args.presign_seconds,
        )
    except Exception as exc:
        print(
            "extraction failed: "
            f"{type(exc).__name__}: {exc}",
            file=sys.stderr,
        )

        return 1

    print(
        json.dumps(
            stats,
            indent=2,
            sort_keys=True,
        )
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
