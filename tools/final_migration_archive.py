#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import tarfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path("/root/savant-runtime")
PACKET_ROOT = ROOT / "exports" / "final-migration"
PACKET_JSON = PACKET_ROOT / "savant-final-migration.json"

SCHEMA = "savant://migration/final-archive/1.0.0"


class MigrationArchiveError(RuntimeError):
    pass


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()

    with path.open("rb") as handle:
        for chunk in iter(
            lambda: handle.read(1024 * 1024),
            b"",
        ):
            h.update(chunk)

    return h.hexdigest()


def load_packet() -> dict[str, Any]:
    if not PACKET_JSON.is_file():
        raise MigrationArchiveError(
            f"migration packet missing: {PACKET_JSON}"
        )

    try:
        value = json.loads(
            PACKET_JSON.read_text(
                encoding="utf-8"
            )
        )
    except Exception as exc:
        raise MigrationArchiveError(
            f"unable to read migration packet: {exc}"
        ) from exc

    if not isinstance(value, dict):
        raise MigrationArchiveError(
            "migration packet root must be an object"
        )

    if value.get("schema") != (
        "savant://migration/final-packet/1.0.0"
    ):
        raise MigrationArchiveError(
            "unexpected migration packet schema"
        )

    return value


def resolve_relative(value: str) -> Path:
    path = (ROOT / value).resolve()

    try:
        path.relative_to(ROOT.resolve())
    except ValueError as exc:
        raise MigrationArchiveError(
            f"path escapes runtime root: {value}"
        ) from exc

    return path


def source_paths(
    packet: dict[str, Any],
) -> list[Path]:
    paths: dict[str, Path] = {}

    for entry in packet.get(
        "manifest",
        [],
    ):
        value = entry.get("path")

        if not isinstance(value, str):
            continue

        path = resolve_relative(value)

        if not path.is_file():
            raise MigrationArchiveError(
                f"manifest source missing: {value}"
            )

        actual = sha256_file(path)
        expected = entry.get("sha256")

        if actual != expected:
            raise MigrationArchiveError(
                "manifest source changed since "
                f"packet generation: {value}"
            )

        paths[value] = path

    for name in (
        "savant-final-migration.json",
        "savant-final-migration.md",
    ):
        path = PACKET_ROOT / name

        if not path.is_file():
            raise MigrationArchiveError(
                f"packet output missing: {path}"
            )

        paths[
            path.relative_to(ROOT).as_posix()
        ] = path

    reconciliation = packet.get(
        "authority_reconciliation"
    )

    if isinstance(reconciliation, dict):
        value = reconciliation.get("path")

        if isinstance(value, str):
            path = resolve_relative(value)

            if not path.is_file():
                raise MigrationArchiveError(
                    "reconciliation receipt "
                    f"missing: {value}"
                )

            expected = reconciliation.get(
                "sha256"
            )

            actual = sha256_file(path)

            if expected and actual != expected:
                raise MigrationArchiveError(
                    "reconciliation receipt "
                    f"changed: {value}"
                )

            paths[value] = path

    return [
        paths[key]
        for key in sorted(paths)
    ]


def main() -> int:
    packet = load_packet()
    paths = source_paths(packet)

    stamp = datetime.now(
        timezone.utc
    ).strftime("%Y%m%dT%H%M%SZ")

    semantic = str(
        packet.get(
            "semantic_digest",
            "unknown",
        )
    )[:16]

    archive_name = (
        f"{stamp}__{semantic}"
        "__savant-final-migration.tar.gz"
    )

    archive_path = (
        PACKET_ROOT / archive_name
    )

    with tarfile.open(
        archive_path,
        mode="w:gz",
        format=tarfile.PAX_FORMAT,
    ) as archive:
        for path in paths:
            arcname = Path(
                "savant-runtime"
            ) / path.relative_to(ROOT)

            archive.add(
                path,
                arcname=arcname.as_posix(),
                recursive=False,
            )

    archive_sha256 = sha256_file(
        archive_path
    )

    receipt = {
        "schema": SCHEMA,
        "authority_effect": "none",
        "passed": True,
        "archive": {
            "path": archive_path.relative_to(
                ROOT
            ).as_posix(),
            "bytes": archive_path.stat().st_size,
            "sha256": archive_sha256,
            "file_count": len(paths),
        },
        "source_packet": {
            "path": PACKET_JSON.relative_to(
                ROOT
            ).as_posix(),
            "semantic_digest": packet.get(
                "semantic_digest"
            ),
            "sha256": sha256_file(
                PACKET_JSON
            ),
        },
    }

    receipt_path = (
        PACKET_ROOT
        / "savant-final-migration-archive.json"
    )

    receipt_path.write_text(
        json.dumps(
            receipt,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    print(
        json.dumps(
            receipt,
            indent=2,
            sort_keys=True,
        )
    )

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except MigrationArchiveError as exc:
        print(
            json.dumps(
                {
                    "schema": SCHEMA,
                    "passed": False,
                    "error": str(exc),
                },
                indent=2,
                sort_keys=True,
            )
        )
        raise SystemExit(1)
