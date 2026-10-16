#!/usr/bin/env python3

from __future__ import annotations

import argparse
import codecs
import hashlib
import json
import mimetypes
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, BinaryIO, Iterator


ROOT = Path(
    os.environ.get(
        "SAVANT_ROOT",
        "/root/savant-runtime",
    )
).resolve()

VAULT_SOURCE_ROOT = ROOT / "vault" / "source-intelligence"
MANIFEST_ROOT = VAULT_SOURCE_ROOT / "manifests"
CHECKPOINT_ROOT = (
    ROOT
    / "runtime"
    / "source-intelligence"
    / "checkpoints"
)

SCHEMA = "savant://runtime/source-intelligence/1.1.0"
MANIFEST_SCHEMA = "savant://vault/source-manifest/1.0.0"
INGEST_SCHEMA = "savant://runtime/source-intelligence/ingest/1.0.0"
RECORD_SCHEMA = "savant://runtime/source-intelligence/record/1.0.0"
CHECKPOINT_SCHEMA = "savant://runtime/source-intelligence/checkpoint/1.0.0"

CHUNK_SIZE = 1024 * 1024


class SourceIntelligenceError(RuntimeError):
    pass


def canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )


def digest_value(value: Any) -> str:
    return hashlib.sha256(
        canonical_json(value).encode("utf-8")
    ).hexdigest()


def utc_now() -> str:
    return (
        datetime.now(timezone.utc)
        .isoformat()
        .replace("+00:00", "Z")
    )


def atomic_json(
    path: Path,
    payload: Any,
) -> None:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    temporary = path.with_name(
        path.name + ".tmp"
    )

    data = (
        json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            indent=2,
            default=str,
        )
        + "\n"
    )

    with temporary.open(
        "w",
        encoding="utf-8",
        newline="\n",
    ) as handle:
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())

    os.replace(
        temporary,
        path,
    )


def stream_bytes(
    handle: BinaryIO,
    *,
    chunk_size: int = CHUNK_SIZE,
) -> Iterator[bytes]:
    if chunk_size <= 0:
        raise SourceIntelligenceError(
            "chunk_size must be positive"
        )

    while True:
        chunk = handle.read(chunk_size)

        if not chunk:
            return

        yield chunk


def hash_file(
    path: Path,
    *,
    chunk_size: int = CHUNK_SIZE,
) -> tuple[str, int]:
    sha256 = hashlib.sha256()
    byte_size = 0

    with path.open("rb") as handle:
        for chunk in stream_bytes(
            handle,
            chunk_size=chunk_size,
        ):
            sha256.update(chunk)
            byte_size += len(chunk)

    return sha256.hexdigest(), byte_size


def decoded_digest(
    path: Path,
    *,
    chunk_size: int = CHUNK_SIZE,
) -> tuple[str | None, str | None]:
    decoder = codecs.getincrementaldecoder(
        "utf-8"
    )(
        errors="strict"
    )

    sha256 = hashlib.sha256()

    try:
        with path.open("rb") as handle:
            for chunk in stream_bytes(
                handle,
                chunk_size=chunk_size,
            ):
                text = decoder.decode(
                    chunk,
                    final=False,
                )

                sha256.update(
                    text.encode("utf-8")
                )

            tail = decoder.decode(
                b"",
                final=True,
            )

            sha256.update(
                tail.encode("utf-8")
            )

    except UnicodeDecodeError:
        return None, None

    return sha256.hexdigest(), "utf-8"


def media_type_for(path: Path) -> str:
    media_type, _ = mimetypes.guess_type(
        path.name
    )

    return (
        media_type
        or "application/octet-stream"
    )


def parse_capability_for(
    path: Path,
    media_type: str,
) -> str:
    suffix = path.suffix.casefold()

    if suffix == ".jsonl":
        return "stream-jsonl"

    if suffix == ".json":
        return "stream-json"

    if (
        media_type.startswith("text/")
        or suffix
        in {
            ".md",
            ".markdown",
            ".txt",
            ".py",
            ".js",
            ".ts",
            ".tsx",
            ".jsx",
            ".html",
            ".css",
            ".yaml",
            ".yml",
            ".toml",
            ".ini",
            ".cfg",
            ".csv",
        }
    ):
        return "stream-text"

    return "raw-only"


def code_fence_digest(
    raw: bytes,
) -> str | None:
    if b"```" not in raw:
        return None

    return hashlib.sha256(
        raw
    ).hexdigest()


class SourceIntelligence:
    schema = SCHEMA

    def __init__(
        self,
        root: Path = ROOT,
    ) -> None:
        self.root = root.resolve()

        self.vault_root = (
            self.root
            / "vault"
            / "source-intelligence"
        )

        self.manifest_root = (
            self.vault_root
            / "manifests"
        )

        self.checkpoint_root = (
            self.root
            / "runtime"
            / "source-intelligence"
            / "checkpoints"
        )

    def inspect(
        self,
        source: str | Path,
        *,
        custody_class: str = "source",
        provenance: Any = None,
        acquired_at: str | None = None,
    ) -> dict[str, Any]:
        path = Path(source).resolve()

        if not path.is_file():
            raise SourceIntelligenceError(
                "source is not a regular file: "
                + str(path)
            )

        raw_sha256, byte_size = hash_file(
            path
        )

        rendered_sha256, encoding = (
            decoded_digest(path)
        )

        media_type = media_type_for(
            path
        )

        source_id = (
            "sha256:"
            + raw_sha256
        )

        manifest = {
            "schema": MANIFEST_SCHEMA,
            "source_id": source_id,
            "content_id": source_id,
            "raw_sha256": raw_sha256,
            "rendered_sha256": rendered_sha256,
            "byte_size": byte_size,
            "media_type": media_type,
            "encoding": encoding,
            "source_uri_or_path": str(path),
            "acquired_at": (
                acquired_at
                or utc_now()
            ),
            "custody_class": custody_class,
            "custody_owner": "vault",
            "parse_capability": (
                parse_capability_for(
                    path,
                    media_type,
                )
            ),
            "provenance": (
                provenance
                if provenance is not None
                else {
                    "kind": "filesystem",
                    "location": str(path),
                }
            ),
            "authority_state": "custodied-source",
            "projection_authoritative": False,
            "source_mutated": False,
            "rebuildable_projections": True,
        }

        manifest["manifest_digest"] = (
            digest_value(manifest)
        )

        manifest["manifest_id"] = (
            "source-manifest:"
            + manifest["manifest_digest"]
        )

        return manifest

    def manifest_path(
        self,
        source_id: str,
    ) -> Path:
        prefix = "sha256:"

        if not source_id.startswith(
            prefix
        ):
            raise SourceIntelligenceError(
                "unsupported source identity"
            )

        value = source_id[
            len(prefix):
        ]

        if (
            len(value) != 64
            or any(
                character
                not in "0123456789abcdef"
                for character in value
            )
        ):
            raise SourceIntelligenceError(
                "invalid SHA-256 source identity"
            )

        return (
            self.manifest_root
            / value[:2]
            / (value + ".json")
        )

    def admit_custody(
        self,
        source: str | Path,
        *,
        custody_class: str = "source",
        provenance: Any = None,
        acquired_at: str | None = None,
    ) -> dict[str, Any]:
        manifest = self.inspect(
            source,
            custody_class=custody_class,
            provenance=provenance,
            acquired_at=acquired_at,
        )

        destination = self.manifest_path(
            manifest["source_id"]
        )

        if destination.is_file():
            existing = json.loads(
                destination.read_text(
                    encoding="utf-8"
                )
            )

            immutable_keys = (
                "source_id",
                "content_id",
                "raw_sha256",
                "rendered_sha256",
                "byte_size",
                "media_type",
                "encoding",
            )

            for key in immutable_keys:
                if (
                    existing.get(key)
                    != manifest.get(key)
                ):
                    raise SourceIntelligenceError(
                        "custody identity collision "
                        f"for {key}"
                    )

            result = dict(existing)
            result["custody_reused"] = True
            return result

        atomic_json(
            destination,
            manifest,
        )

        result = dict(manifest)
        result["custody_reused"] = False

        return result

    def checkpoint_path(
        self,
        source_id: str,
    ) -> Path:
        identity = source_id.replace(
            ":",
            "_",
        )

        return (
            self.checkpoint_root
            / (identity + ".json")
        )

    def load_checkpoint(
        self,
        source_id: str,
    ) -> dict[str, Any] | None:
        path = self.checkpoint_path(
            source_id
        )

        if not path.is_file():
            return None

        value = json.loads(
            path.read_text(
                encoding="utf-8"
            )
        )

        if (
            value.get("source_id")
            != source_id
        ):
            raise SourceIntelligenceError(
                "checkpoint source identity mismatch"
            )

        return value

    def save_checkpoint(
        self,
        *,
        source_id: str,
        adapter: str,
        sequence: int,
        byte_offset: int | None,
        record_digest: str | None,
    ) -> dict[str, Any]:
        payload = {
            "schema": CHECKPOINT_SCHEMA,
            "source_id": source_id,
            "adapter": adapter,
            "sequence": sequence,
            "byte_offset": byte_offset,
            "record_digest": record_digest,
            "updated_at": utc_now(),
        }

        payload["checkpoint_digest"] = (
            digest_value(payload)
        )

        atomic_json(
            self.checkpoint_path(
                source_id
            ),
            payload,
        )

        return payload

    def _record(
        self,
        *,
        source_id: str,
        adapter: str,
        sequence: int,
        value: Any,
        raw: bytes | None = None,
        byte_start: int | None = None,
        byte_end: int | None = None,
        malformed: bool = False,
        error: str | None = None,
    ) -> dict[str, Any]:
        payload = {
            "schema": RECORD_SCHEMA,
            "source_id": source_id,
            "adapter": adapter,
            "sequence": sequence,
            "byte_start": byte_start,
            "byte_end": byte_end,
            "value": value,
            "malformed": malformed,
            "error": error,
            "authoritative": False,
        }

        if raw is not None:
            payload["raw_sha256"] = (
                hashlib.sha256(
                    raw
                ).hexdigest()
            )

            payload["raw_byte_size"] = (
                len(raw)
            )

            fence_digest = (
                code_fence_digest(
                    raw
                )
            )

            if fence_digest is not None:
                payload[
                    "exact_code_candidate_sha256"
                ] = fence_digest

        payload["record_digest"] = (
            digest_value(payload)
        )

        return payload

    def stream_jsonl(
        self,
        path: Path,
        source_id: str,
        *,
        resume: bool = False,
    ) -> Iterator[dict[str, Any]]:
        checkpoint = (
            self.load_checkpoint(
                source_id
            )
            if resume
            else None
        )

        resume_sequence = (
            int(
                checkpoint.get(
                    "sequence",
                    0,
                )
            )
            if checkpoint
            else 0
        )

        with path.open("rb") as handle:
            sequence = 0

            while True:
                byte_start = handle.tell()
                raw = handle.readline()

                if not raw:
                    return

                byte_end = handle.tell()

                if not raw.strip():
                    continue

                sequence += 1

                if sequence <= resume_sequence:
                    continue

                try:
                    text = raw.decode(
                        "utf-8"
                    )

                    value = json.loads(
                        text
                    )

                    record = self._record(
                        source_id=source_id,
                        adapter="jsonl",
                        sequence=sequence,
                        value=value,
                        raw=raw,
                        byte_start=byte_start,
                        byte_end=byte_end,
                    )

                except (
                    UnicodeDecodeError,
                    json.JSONDecodeError,
                ) as exc:
                    record = self._record(
                        source_id=source_id,
                        adapter="jsonl",
                        sequence=sequence,
                        value=None,
                        raw=raw,
                        byte_start=byte_start,
                        byte_end=byte_end,
                        malformed=True,
                        error=(
                            f"{type(exc).__name__}: "
                            f"{exc}"
                        ),
                    )

                self.save_checkpoint(
                    source_id=source_id,
                    adapter="jsonl",
                    sequence=sequence,
                    byte_offset=byte_end,
                    record_digest=(
                        record[
                            "record_digest"
                        ]
                    ),
                )

                yield record

    def stream_text(
        self,
        path: Path,
        source_id: str,
        *,
        resume: bool = False,
    ) -> Iterator[dict[str, Any]]:
        checkpoint = (
            self.load_checkpoint(
                source_id
            )
            if resume
            else None
        )

        resume_sequence = (
            int(
                checkpoint.get(
                    "sequence",
                    0,
                )
            )
            if checkpoint
            else 0
        )

        with path.open("rb") as handle:
            sequence = 0

            while True:
                byte_start = handle.tell()
                raw = handle.readline()

                if not raw:
                    return

                byte_end = handle.tell()
                sequence += 1

                if sequence <= resume_sequence:
                    continue

                try:
                    value = raw.decode(
                        "utf-8"
                    )

                    record = self._record(
                        source_id=source_id,
                        adapter="text",
                        sequence=sequence,
                        value=value,
                        raw=raw,
                        byte_start=byte_start,
                        byte_end=byte_end,
                    )

                except UnicodeDecodeError as exc:
                    record = self._record(
                        source_id=source_id,
                        adapter="text",
                        sequence=sequence,
                        value=None,
                        raw=raw,
                        byte_start=byte_start,
                        byte_end=byte_end,
                        malformed=True,
                        error=(
                            f"{type(exc).__name__}: "
                            f"{exc}"
                        ),
                    )

                self.save_checkpoint(
                    source_id=source_id,
                    adapter="text",
                    sequence=sequence,
                    byte_offset=byte_end,
                    record_digest=(
                        record[
                            "record_digest"
                        ]
                    ),
                )

                yield record

    def stream_json(
        self,
        path: Path,
        source_id: str,
        *,
        resume: bool = False,
    ) -> Iterator[dict[str, Any]]:
        checkpoint = (
            self.load_checkpoint(
                source_id
            )
            if resume
            else None
        )

        resume_sequence = (
            int(
                checkpoint.get(
                    "sequence",
                    0,
                )
            )
            if checkpoint
            else 0
        )

        sequence = 0

        try:
            import ijson
        except ImportError:
            ijson = None

        try:
            if ijson is not None:
                with path.open("rb") as handle:
                    first = next(
                        ijson.parse(handle),
                        None,
                    )

                if first is None:
                    return

                prefix, event, _ = first

                if (
                    prefix == ""
                    and event == "start_array"
                ):
                    expression = "item"
                elif (
                    prefix == ""
                    and event == "start_map"
                ):
                    expression = ""
                else:
                    raise SourceIntelligenceError(
                        "JSON root must be "
                        "array or object"
                    )

                with path.open("rb") as handle:
                    values = ijson.items(
                        handle,
                        expression,
                    )

                    for value in values:
                        sequence += 1

                        if sequence <= resume_sequence:
                            continue

                        record = self._record(
                            source_id=source_id,
                            adapter="json",
                            sequence=sequence,
                            value=value,
                        )

                        self.save_checkpoint(
                            source_id=source_id,
                            adapter="json",
                            sequence=sequence,
                            byte_offset=None,
                            record_digest=(
                                record[
                                    "record_digest"
                                ]
                            ),
                        )

                        yield record

                return

            with path.open(
                "r",
                encoding="utf-8",
            ) as handle:
                root = json.load(handle)

            if isinstance(root, list):
                values = root
            elif isinstance(root, dict):
                values = (root,)
            else:
                raise SourceIntelligenceError(
                    "JSON root must be "
                    "array or object"
                )

            for value in values:
                sequence += 1

                if sequence <= resume_sequence:
                    continue

                record = self._record(
                    source_id=source_id,
                    adapter="json",
                    sequence=sequence,
                    value=value,
                )

                self.save_checkpoint(
                    source_id=source_id,
                    adapter="json",
                    sequence=sequence,
                    byte_offset=None,
                    record_digest=(
                        record[
                            "record_digest"
                        ]
                    ),
                )

                yield record

        except Exception as exc:
            if isinstance(
                exc,
                SourceIntelligenceError,
            ):
                raise

            sequence += 1

            yield self._record(
                source_id=source_id,
                adapter="json",
                sequence=sequence,
                value=None,
                malformed=True,
                error=(
                    f"{type(exc).__name__}: "
                    f"{exc}"
                ),
            )

    def ingest(
        self,
        source: str | Path,
        *,
        resume: bool = False,
    ) -> Iterator[dict[str, Any]]:
        path = Path(source).resolve()

        manifest = self.admit_custody(
            path
        )

        source_id = manifest[
            "source_id"
        ]

        capability = manifest[
            "parse_capability"
        ]

        if capability == "stream-jsonl":
            yield from self.stream_jsonl(
                path,
                source_id,
                resume=resume,
            )
            return

        if capability == "stream-json":
            yield from self.stream_json(
                path,
                source_id,
                resume=resume,
            )
            return

        if capability == "stream-text":
            yield from self.stream_text(
                path,
                source_id,
                resume=resume,
            )
            return

        raise SourceIntelligenceError(
            "no ingestion adapter for "
            + capability
        )

    def ingest_summary(
        self,
        source: str | Path,
        *,
        resume: bool = False,
    ) -> dict[str, Any]:
        path = Path(source).resolve()

        manifest = self.admit_custody(
            path
        )

        count = 0
        malformed = 0
        digest_chain = hashlib.sha256()

        for record in self.ingest(
            path,
            resume=resume,
        ):
            count += 1

            if record["malformed"]:
                malformed += 1

            digest_chain.update(
                record[
                    "record_digest"
                ].encode("ascii")
            )

        result = {
            "schema": INGEST_SCHEMA,
            "source_id": (
                manifest["source_id"]
            ),
            "parse_capability": (
                manifest[
                    "parse_capability"
                ]
            ),
            "record_count": count,
            "malformed_count": malformed,
            "record_chain_sha256": (
                digest_chain.hexdigest()
            ),
            "source_mutated": False,
            "bounded_streaming": True,
            "deterministic_ordering": True,
            "parser_failure_isolation": True,
            "authoritative": False,
        }

        result["digest"] = (
            digest_value(result)
        )

        return result

    def verify(
        self,
        source: str | Path,
        source_id: str,
    ) -> dict[str, Any]:
        path = Path(source).resolve()

        raw_sha256, byte_size = (
            hash_file(path)
        )

        actual = (
            "sha256:"
            + raw_sha256
        )

        return {
            "schema": (
                "savant://assurance/"
                "source-intelligence/"
                "verification/1.0.0"
            ),
            "source_id": source_id,
            "actual_source_id": actual,
            "byte_size": byte_size,
            "valid": (
                actual == source_id
            ),
            "source_mutated": False,
        }

    def profile(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "workflow": "source-intelligence",
            "authority_state": "composed-profile",
            "source_custody_owner": "vault",
            "canon_store": "fluid-canon",
            "projection_authoritative": False,
            "duplicate_canon_store": False,
            "si_1": {
                "stable_source_identity": True,
                "raw_byte_digest": True,
                "decoded_digest": True,
                "byte_size": True,
                "media_type": True,
                "source_path_or_uri": True,
                "acquisition_timestamp": True,
                "provenance": True,
                "custody_class": True,
                "parse_capability": True,
                "immutable_manifest": True,
                "implementation_state": "implemented",
            },
            "si_2": {
                "streaming_json": True,
                "streaming_jsonl": True,
                "streaming_text": True,
                "bounded_memory": True,
                "malformed_node_isolation": True,
                "deterministic_ordering": True,
                "resume_checkpoints": True,
                "source_mutation": False,
                "exact_raw_record_hashing": True,
                "code_candidate_hashing": True,
                "implementation_state": "implemented",
            },
        }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Savant Source Intelligence "
            "custody and streaming ingestion"
        )
    )

    commands = parser.add_subparsers(
        dest="command",
        required=True,
    )

    commands.add_parser(
        "profile"
    )

    inspect_parser = commands.add_parser(
        "inspect"
    )
    inspect_parser.add_argument(
        "source"
    )

    custody_parser = commands.add_parser(
        "custody"
    )
    custody_parser.add_argument(
        "source"
    )
    custody_parser.add_argument(
        "--custody-class",
        default="source",
    )
    custody_parser.add_argument(
        "--provenance",
    )

    verify_parser = commands.add_parser(
        "verify"
    )
    verify_parser.add_argument(
        "source"
    )
    verify_parser.add_argument(
        "source_id"
    )

    ingest_parser = commands.add_parser(
        "ingest"
    )
    ingest_parser.add_argument(
        "source"
    )
    ingest_parser.add_argument(
        "--resume",
        action="store_true",
    )
    ingest_parser.add_argument(
        "--summary",
        action="store_true",
    )

    return parser


def main() -> int:
    arguments = (
        build_parser()
        .parse_args()
    )

    engine = SourceIntelligence()

    if arguments.command == "profile":
        result = engine.profile()
        print(
            json.dumps(
                result,
                indent=2,
                sort_keys=True,
                default=str,
            )
        )
        return 0

    if arguments.command == "inspect":
        result = engine.inspect(
            arguments.source
        )
        print(
            json.dumps(
                result,
                indent=2,
                sort_keys=True,
                default=str,
            )
        )
        return 0

    if arguments.command == "custody":
        result = engine.admit_custody(
            arguments.source,
            custody_class=(
                arguments.custody_class
            ),
            provenance=(
                arguments.provenance
            ),
        )
        print(
            json.dumps(
                result,
                indent=2,
                sort_keys=True,
                default=str,
            )
        )
        return 0

    if arguments.command == "verify":
        result = engine.verify(
            arguments.source,
            arguments.source_id,
        )
        print(
            json.dumps(
                result,
                indent=2,
                sort_keys=True,
                default=str,
            )
        )
        return (
            0
            if result["valid"]
            else 1
        )

    if arguments.command == "ingest":
        if arguments.summary:
            result = engine.ingest_summary(
                arguments.source,
                resume=arguments.resume,
            )

            print(
                json.dumps(
                    result,
                    indent=2,
                    sort_keys=True,
                    default=str,
                )
            )

            return 0

        for record in engine.ingest(
            arguments.source,
            resume=arguments.resume,
        ):
            print(
                canonical_json(
                    record
                )
            )

        return 0

    raise SourceIntelligenceError(
        "unsupported command"
    )


if __name__ == "__main__":
    try:
        raise SystemExit(
            main()
        )
    except (
        OSError,
        ValueError,
        KeyError,
        json.JSONDecodeError,
        SourceIntelligenceError,
    ) as exc:
        print(
            (
                "ERROR: "
                f"{type(exc).__name__}: "
                f"{exc}"
            ),
            file=sys.stderr,
        )

        raise SystemExit(1)
