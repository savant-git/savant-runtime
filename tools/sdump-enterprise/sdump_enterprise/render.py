from __future__ import annotations

import json
import os
from pathlib import Path
import tempfile
from typing import Any, Mapping

from .model import Projection


BORDER = "=" * 76
SUB_BORDER = "-" * 76


def _compact_json(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def write_bundle(
    output: Path,
    manifest: Mapping[str, Any],
    projection: Projection,
    pretty_manifest: bool = False,
) -> None:
    """
    Write the deterministic sdump projection.

    The manifest remains the authoritative inventory/lineage projection.
    Source content is emitted exactly once for each unique content_id.

    Per-content metadata already represented in manifest["files"] is not
    redundantly serialized beside the source body.
    """
    output.parent.mkdir(parents=True, exist_ok=True)

    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{output.name}.",
        suffix=".partial",
        dir=str(output.parent),
    )
    temporary = Path(temporary_name)

    try:
        with os.fdopen(
            descriptor,
            "w",
            encoding="utf-8",
            newline="",
        ) as handle:
            handle.write("sdump enterprise v3\n")

            handle.write("manifest\n")
            if pretty_manifest:
                handle.write(
                    json.dumps(
                        manifest,
                        ensure_ascii=False,
                        sort_keys=True,
                        indent=2,
                    )
                )
            else:
                handle.write(_compact_json(manifest))
            handle.write("\n")

            handle.write("contents\n")

            for record in projection.records:
                if (
                    not record.included
                    or record.duplicate_of is not None
                    or not record.content_id
                ):
                    continue

                store_path = projection.unique_content_paths.get(
                    record.content_id
                )

                if store_path is None or not store_path.is_file():
                    raise RuntimeError(
                        f"missing content store object: {record.content_id}"
                    )

                # The manifest contains path/category/language/source size,
                # source hash, rendered hash, encoding, redactions,
                # duplicate relationships, and content_id. Only the stable
                # content address is required here to bind this body back
                # to that complete record.
                handle.write(f"\ncontent {record.content_id}\n")

                with store_path.open(
                    "r",
                    encoding="utf-8",
                    errors="strict",
                    newline="",
                ) as source:
                    while True:
                        chunk = source.read(1024 * 1024)
                        if not chunk:
                            break
                        handle.write(chunk)

                if (
                    store_path.stat().st_size
                    and not _ends_with_newline(store_path)
                ):
                    handle.write("\n")

                handle.write("end content\n")

            handle.write(
                f"snapshot_sha256 {projection.snapshot_hash}\n"
            )
            handle.write("end sdump enterprise v3\n")

            handle.flush()
            os.fsync(handle.fileno())

        os.chmod(temporary, 0o600)
        os.replace(temporary, output)

        directory_fd = os.open(output.parent, os.O_DIRECTORY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)

    finally:
        if temporary.exists():
            temporary.unlink()


def _ends_with_newline(path: Path) -> bool:
    size = path.stat().st_size
    if size == 0:
        return True

    with path.open("rb") as handle:
        handle.seek(-1, os.SEEK_END)
        return handle.read(1) in {b"\n", b"\r"}


def compress_zstd(
    source: Path,
    level: int = 10,
    threads: int = 0,
) -> Path:
    try:
        import zstandard
    except ImportError as error:
        raise RuntimeError(
            "zstandard is required for --compress zstd"
        ) from error

    destination = source.with_suffix(source.suffix + ".zst")
    temporary = destination.with_name(
        f".{destination.name}.partial"
    )

    compressor = zstandard.ZstdCompressor(
        level=level,
        threads=threads,
    )

    try:
        with source.open("rb") as input_handle, temporary.open(
            "wb"
        ) as output_handle:
            compressor.copy_stream(
                input_handle,
                output_handle,
            )
            output_handle.flush()
            os.fsync(output_handle.fileno())

        os.chmod(temporary, 0o600)
        os.replace(temporary, destination)

    finally:
        if temporary.exists():
            temporary.unlink()

    return destination
