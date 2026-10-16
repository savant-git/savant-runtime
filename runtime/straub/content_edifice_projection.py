#!/usr/bin/env python3
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import sys
import time
from typing import Any


schema = (
    "savant.carbon.straub."
    "content-edifice-projection.v2"
)
owner = "carbon"
module = "straub"
authority_effect = "none"

runtime_root = Path(
    "/root/savant-runtime"
).resolve()

state_root = (
    runtime_root
    / "runtime"
    / "straub"
    / "source-datrix-state"
)

source_projection_path = (
    state_root
    / "current.json"
)

default_output_path = (
    state_root
    / "content-edifice.json"
)

working_database_path = (
    state_root
    / ".content-edifice-working.sqlite3"
)

content_edifice = (
    "character",
    "line",
    "snippet",
    "script",
    "module",
    "service",
    "application",
    "suite",
    "estate",
)

directly_projectable_tiers = (
    "character",
    "line",
    "script",
)

unresolved_tiers = (
    "snippet",
    "module",
    "service",
    "application",
    "suite",
    "estate",
)

progress_interval_seconds = 1.0


def utc_now() -> str:
    return (
        datetime.now(timezone.utc)
        .isoformat()
        .replace(
            "+00:00",
            "Z",
        )
    )


def sha256_bytes(
    value: bytes,
) -> str:
    return hashlib.sha256(
        value
    ).hexdigest()


def canonical_json_bytes(
    value: Any,
) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(
            ",",
            ":",
        ),
    ).encode(
        "utf-8"
    )


def atomic_json(
    path: Path,
    value: Any,
) -> None:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    payload = (
        canonical_json_bytes(
            value
        )
        + b"\n"
    )

    temporary = path.with_name(
        f".{path.name}.{os.getpid()}.tmp"
    )

    with temporary.open(
        "wb"
    ) as handle:
        handle.write(
            payload
        )
        handle.flush()
        os.fsync(
            handle.fileno()
        )

    os.chmod(
        temporary,
        0o600,
    )

    os.replace(
        temporary,
        path,
    )


def load_source_projection(
    path: Path,
) -> dict[str, Any]:
    value = json.loads(
        path.read_text(
            encoding="utf-8"
        )
    )

    if not isinstance(
        value,
        dict,
    ):
        raise ValueError(
            "source projection must be an object"
        )

    if not value.get(
        "projection_only"
    ):
        raise ValueError(
            "source input is not projection-only"
        )

    files = value.get(
        "files"
    )

    if not isinstance(
        files,
        list,
    ):
        raise ValueError(
            "source projection files must be a list"
        )

    return value


def safe_runtime_path(
    relative: str,
) -> Path | None:
    if not relative:
        return None

    candidate = (
        runtime_root
        / relative
    ).resolve()

    try:
        candidate.relative_to(
            runtime_root
        )
    except ValueError:
        return None

    return candidate


def human_bytes(
    value: int,
) -> str:
    amount = float(
        max(
            0,
            value,
        )
    )

    units = (
        "b",
        "kib",
        "mib",
        "gib",
        "tib",
    )

    unit = units[0]

    for candidate in units:
        unit = candidate

        if (
            amount < 1024.0
            or candidate == units[-1]
        ):
            break

        amount /= 1024.0

    if unit == "b":
        return (
            f"{int(amount)} {unit}"
        )

    return (
        f"{amount:.2f} {unit}"
    )


def elapsed_text(
    started: float,
) -> str:
    elapsed = max(
        0.0,
        time.monotonic()
        - started,
    )

    if elapsed < 60.0:
        return (
            f"{elapsed:.1f}s"
        )

    minutes = int(
        elapsed // 60
    )

    seconds = int(
        elapsed % 60
    )

    return (
        f"{minutes}m {seconds:02d}s"
    )


class TerminalProjection:
    def __init__(
        self,
        *,
        total: int,
    ) -> None:
        self.total = max(
            0,
            total,
        )

        self.started = (
            time.monotonic()
        )

        self.last_progress = 0.0

    def emit(
        self,
        label: str,
        value: str = "",
    ) -> None:
        if value:
            print(
                f"{label:<28} {value}",
                flush=True,
            )
        else:
            print(
                label,
                flush=True,
            )

    def begin(self) -> None:
        print(
            "",
            flush=True,
        )

        self.emit(
            "savant",
            "content-edifice projection",
        )

        self.emit(
            "owner",
            owner,
        )

        self.emit(
            "authority effect",
            authority_effect,
        )

        self.emit(
            "mode",
            "bounded streaming",
        )

        self.emit(
            "working index",
            "temporary sqlite",
        )

        self.emit(
            "source revisions",
            f"{self.total:,}",
        )

        print(
            "",
            flush=True,
        )

    def progress(
        self,
        *,
        processed: int,
        verified: int,
        unresolved: int,
        verified_bytes: int,
        force: bool = False,
    ) -> None:
        now = (
            time.monotonic()
        )

        if (
            not force
            and (
                now
                - self.last_progress
            )
            < progress_interval_seconds
        ):
            return

        self.last_progress = now

        percent = (
            (
                processed
                / self.total
            )
            * 100.0
            if self.total
            else 100.0
        )

        self.emit(
            "progress",
            (
                f"{processed:,}/{self.total:,} "
                f"({percent:6.2f}%)"
            ),
        )

        self.emit(
            "verified",
            f"{verified:,}",
        )

        self.emit(
            "unresolved",
            f"{unresolved:,}",
        )

        self.emit(
            "verified substance",
            human_bytes(
                verified_bytes
            ),
        )

        self.emit(
            "elapsed",
            elapsed_text(
                self.started
            ),
        )

        print(
            "",
            flush=True,
        )

    def complete(
        self,
        result: dict[str, Any],
    ) -> None:
        print(
            "",
            flush=True,
        )

        self.emit(
            "status",
            "complete",
        )

        self.emit(
            "verified scripts",
            f"{result['verified_script_count']:,}",
        )

        self.emit(
            "unresolved scripts",
            f"{result['unresolved_script_count']:,}",
        )

        self.emit(
            "verified source",
            human_bytes(
                result[
                    "verified_source_bytes"
                ]
            ),
        )

        self.emit(
            "unique characters",
            (
                f"{result['composition']['character']['canonical_count']:,}"
            ),
        )

        self.emit(
            "character instances",
            (
                f"{result['composition']['character']['instance_count']:,}"
            ),
        )

        self.emit(
            "unique lines",
            (
                f"{result['composition']['line']['canonical_count']:,}"
            ),
        )

        self.emit(
            "line instances",
            (
                f"{result['composition']['line']['instance_count']:,}"
            ),
        )

        self.emit(
            "line duplicate bytes",
            human_bytes(
                result[
                    "composition"
                ][
                    "line"
                ][
                    "duplicate_substance_bytes"
                ]
            ),
        )

        self.emit(
            "line reduction",
            (
                f"{result['composition']['line']['substance_reduction_percent']:.6f}%"
            ),
        )

        self.emit(
            "digest",
            result[
                "digest"
            ],
        )

        self.emit(
            "elapsed",
            elapsed_text(
                self.started
            ),
        )

        print(
            "",
            flush=True,
        )


def reset_working_database(
    path: Path,
) -> sqlite3.Connection:
    for candidate in (
        path,
        Path(
            str(path)
            + "-wal"
        ),
        Path(
            str(path)
            + "-shm"
        ),
    ):
        try:
            candidate.unlink()
        except FileNotFoundError:
            pass

    connection = sqlite3.connect(
        path
    )

    connection.execute(
        "PRAGMA journal_mode=WAL"
    )

    connection.execute(
        "PRAGMA synchronous=NORMAL"
    )

    connection.execute(
        "PRAGMA temp_store=FILE"
    )

    connection.execute(
        "PRAGMA cache_size=-8192"
    )

    connection.execute(
        """
        CREATE TABLE characters (
            digest TEXT PRIMARY KEY,
            value TEXT NOT NULL,
            utf8_bytes INTEGER NOT NULL,
            instances INTEGER NOT NULL
        )
        """
    )

    connection.execute(
        """
        CREATE TABLE lines (
            digest TEXT PRIMARY KEY,
            utf8_bytes INTEGER NOT NULL,
            instances INTEGER NOT NULL
        )
        """
    )

    connection.execute(
        """
        CREATE TABLE scripts (
            revision_id TEXT PRIMARY KEY,
            path TEXT NOT NULL,
            sha256 TEXT NOT NULL,
            source_bytes INTEGER NOT NULL,
            encoding TEXT NOT NULL,
            line_instances INTEGER NOT NULL
        )
        """
    )

    connection.execute(
        """
        CREATE TABLE unresolved (
            revision_id TEXT PRIMARY KEY,
            path TEXT NOT NULL,
            status TEXT NOT NULL,
            expected_sha256 TEXT,
            actual_sha256 TEXT,
            expected_size INTEGER,
            actual_size INTEGER
        )
        """
    )

    connection.commit()

    return connection


def character_digest(
    character: str,
) -> str:
    return sha256_bytes(
        character.encode(
            "utf-8"
        )
    )


def line_digest(
    line: str,
) -> str:
    return sha256_bytes(
        line.encode(
            "utf-8"
        )
    )


def record_character(
    connection: sqlite3.Connection,
    character: str,
) -> int:
    encoded = character.encode(
        "utf-8"
    )

    size = len(
        encoded
    )

    digest = sha256_bytes(
        encoded
    )

    connection.execute(
        """
        INSERT INTO characters (
            digest,
            value,
            utf8_bytes,
            instances
        )
        VALUES (?, ?, ?, 1)
        ON CONFLICT(digest)
        DO UPDATE SET
            instances = instances + 1
        """,
        (
            digest,
            character,
            size,
        ),
    )

    return size


def record_line(
    connection: sqlite3.Connection,
    line: str,
) -> int:
    encoded = line.encode(
        "utf-8"
    )

    size = len(
        encoded
    )

    digest = sha256_bytes(
        encoded
    )

    connection.execute(
        """
        INSERT INTO lines (
            digest,
            utf8_bytes,
            instances
        )
        VALUES (?, ?, 1)
        ON CONFLICT(digest)
        DO UPDATE SET
            instances = instances + 1
        """,
        (
            digest,
            size,
        ),
    )

    return size


def unresolved_record(
    connection: sqlite3.Connection,
    *,
    revision_id: str,
    path: str,
    status: str,
    expected_sha256: str,
    actual_sha256: str | None,
    expected_size: int,
    actual_size: int | None,
) -> None:
    connection.execute(
        """
        INSERT OR REPLACE INTO unresolved (
            revision_id,
            path,
            status,
            expected_sha256,
            actual_sha256,
            expected_size,
            actual_size
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            revision_id,
            path,
            status,
            expected_sha256,
            actual_sha256,
            expected_size,
            actual_size,
        ),
    )


def verify_live_source(
    item: dict[str, Any],
) -> tuple[
    str,
    bytes | None,
    str | None,
    int | None,
]:
    relative = str(
        item.get(
            "path",
            "",
        )
    )

    expected_digest = str(
        item.get(
            "sha256",
            "",
        )
    )

    expected_size = int(
        item.get(
            "size",
            0,
        )
        or 0
    )

    path = safe_runtime_path(
        relative
    )

    if path is None:
        return (
            "invalid-path",
            None,
            None,
            None,
        )

    try:
        if (
            path.is_symlink()
            or not path.is_file()
        ):
            return (
                "missing",
                None,
                None,
                None,
            )

        raw = path.read_bytes()
    except OSError:
        return (
            "unreadable",
            None,
            None,
            None,
        )

    actual_digest = (
        sha256_bytes(
            raw
        )
    )

    actual_size = len(
        raw
    )

    if (
        not expected_digest
        or actual_digest
        != expected_digest
    ):
        return (
            "digest-mismatch",
            None,
            actual_digest,
            actual_size,
        )

    if (
        actual_size
        != expected_size
    ):
        return (
            "size-mismatch",
            None,
            actual_digest,
            actual_size,
        )

    return (
        "verified",
        raw,
        actual_digest,
        actual_size,
    )


def decoded_lines(
    raw: bytes,
) -> tuple[
    str,
    Any,
]:
    try:
        text = raw.decode(
            "utf-8"
        )

        encoding = "utf-8"
    except UnicodeDecodeError:
        text = raw.decode(
            "utf-8",
            errors="replace",
        )

        encoding = (
            "utf-8-replacement"
        )

    return (
        encoding,
        text.splitlines(
            keepends=True
        ),
    )


def scalar(
    connection: sqlite3.Connection,
    query: str,
) -> int:
    row = connection.execute(
        query
    ).fetchone()

    if not row:
        return 0

    value = row[0]

    if value is None:
        return 0

    return int(
        value
    )


def database_measurements(
    connection: sqlite3.Connection,
) -> dict[str, Any]:
    character_canonical_count = (
        scalar(
            connection,
            "SELECT COUNT(*) FROM characters",
        )
    )

    character_instance_count = (
        scalar(
            connection,
            "SELECT COALESCE(SUM(instances), 0) FROM characters",
        )
    )

    character_canonical_bytes = (
        scalar(
            connection,
            "SELECT COALESCE(SUM(utf8_bytes), 0) FROM characters",
        )
    )

    character_fully_substantiated_bytes = (
        scalar(
            connection,
            """
            SELECT COALESCE(
                SUM(utf8_bytes * instances),
                0
            )
            FROM characters
            """,
        )
    )

    line_canonical_count = (
        scalar(
            connection,
            "SELECT COUNT(*) FROM lines",
        )
    )

    line_instance_count = (
        scalar(
            connection,
            "SELECT COALESCE(SUM(instances), 0) FROM lines",
        )
    )

    line_canonical_bytes = (
        scalar(
            connection,
            "SELECT COALESCE(SUM(utf8_bytes), 0) FROM lines",
        )
    )

    line_fully_substantiated_bytes = (
        scalar(
            connection,
            """
            SELECT COALESCE(
                SUM(utf8_bytes * instances),
                0
            )
            FROM lines
            """,
        )
    )

    script_count = (
        scalar(
            connection,
            "SELECT COUNT(*) FROM scripts",
        )
    )

    unresolved_count = (
        scalar(
            connection,
            "SELECT COUNT(*) FROM unresolved",
        )
    )

    character_duplicate_bytes = max(
        0,
        character_fully_substantiated_bytes
        - character_canonical_bytes,
    )

    line_duplicate_bytes = max(
        0,
        line_fully_substantiated_bytes
        - line_canonical_bytes,
    )

    character_reduction = (
        (
            character_duplicate_bytes
            / character_fully_substantiated_bytes
        )
        * 100.0
        if character_fully_substantiated_bytes
        else 0.0
    )

    line_reduction = (
        (
            line_duplicate_bytes
            / line_fully_substantiated_bytes
        )
        * 100.0
        if line_fully_substantiated_bytes
        else 0.0
    )

    return {
        "character": {
            "canonical_count": (
                character_canonical_count
            ),
            "instance_count": (
                character_instance_count
            ),
            "canonical_substance_bytes": (
                character_canonical_bytes
            ),
            "fully_substantiated_bytes": (
                character_fully_substantiated_bytes
            ),
            "duplicate_substance_bytes": (
                character_duplicate_bytes
            ),
            "substance_reduction_percent": round(
                character_reduction,
                6,
            ),
        },
        "line": {
            "canonical_count": (
                line_canonical_count
            ),
            "instance_count": (
                line_instance_count
            ),
            "canonical_substance_bytes": (
                line_canonical_bytes
            ),
            "fully_substantiated_bytes": (
                line_fully_substantiated_bytes
            ),
            "duplicate_substance_bytes": (
                line_duplicate_bytes
            ),
            "substance_reduction_percent": round(
                line_reduction,
                6,
            ),
        },
        "script": {
            "canonical_count": (
                script_count
            ),
            "instance_count": (
                script_count
            ),
            "unresolved_count": (
                unresolved_count
            ),
            "composition": (
                "verified source revision "
                "projected as ordered line instances"
            ),
        },
    }


def unresolved_counts(
    connection: sqlite3.Connection,
) -> dict[str, int]:
    rows = connection.execute(
        """
        SELECT status, COUNT(*)
        FROM unresolved
        GROUP BY status
        ORDER BY status
        """
    ).fetchall()

    return {
        str(status): int(
            count
        )
        for (
            status,
            count,
        ) in rows
    }


def projection_digest(
    value: dict[str, Any],
) -> str:
    material = dict(
        value
    )

    material.pop(
        "generated_at",
        None,
    )

    material.pop(
        "digest",
        None,
    )

    return sha256_bytes(
        canonical_json_bytes(
            material
        )
    )


def project(
    source: dict[str, Any],
    terminal: TerminalProjection,
) -> dict[str, Any]:
    files = [
        item
        for item in source[
            "files"
        ]
        if isinstance(
            item,
            dict,
        )
    ]

    files.sort(
        key=lambda item: str(
            item.get(
                "path",
                "",
            )
        )
    )

    connection = (
        reset_working_database(
            working_database_path
        )
    )

    verified_script_count = 0
    unresolved_script_count = 0
    verified_source_bytes = 0

    try:
        terminal.begin()

        for (
            index,
            item,
        ) in enumerate(
            files,
            start=1,
        ):
            path = str(
                item.get(
                    "path",
                    "",
                )
            )

            revision_id = str(
                item.get(
                    "revision_id",
                    "",
                )
            )

            expected_digest = str(
                item.get(
                    "sha256",
                    "",
                )
            )

            expected_size = int(
                item.get(
                    "size",
                    0,
                )
                or 0
            )

            (
                status,
                raw,
                actual_digest,
                actual_size,
            ) = verify_live_source(
                item
            )

            if (
                status
                != "verified"
                or raw is None
            ):
                unresolved_script_count += 1

                unresolved_record(
                    connection,
                    revision_id=revision_id,
                    path=path,
                    status=status,
                    expected_sha256=(
                        expected_digest
                    ),
                    actual_sha256=(
                        actual_digest
                    ),
                    expected_size=(
                        expected_size
                    ),
                    actual_size=(
                        actual_size
                    ),
                )

                if (
                    index % 100
                    == 0
                ):
                    connection.commit()

                terminal.progress(
                    processed=index,
                    verified=(
                        verified_script_count
                    ),
                    unresolved=(
                        unresolved_script_count
                    ),
                    verified_bytes=(
                        verified_source_bytes
                    ),
                )

                continue

            verified_script_count += 1
            verified_source_bytes += len(
                raw
            )

            (
                encoding,
                lines,
            ) = decoded_lines(
                raw
            )

            line_instances = 0

            for line in lines:
                line_instances += 1

                record_line(
                    connection,
                    line,
                )

                for character in line:
                    record_character(
                        connection,
                        character,
                    )

            connection.execute(
                """
                INSERT INTO scripts (
                    revision_id,
                    path,
                    sha256,
                    source_bytes,
                    encoding,
                    line_instances
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    revision_id,
                    path,
                    actual_digest,
                    len(
                        raw
                    ),
                    encoding,
                    line_instances,
                ),
            )

            if (
                index % 25
                == 0
            ):
                connection.commit()

            terminal.progress(
                processed=index,
                verified=(
                    verified_script_count
                ),
                unresolved=(
                    unresolved_script_count
                ),
                verified_bytes=(
                    verified_source_bytes
                ),
            )

        connection.commit()

        terminal.progress(
            processed=len(
                files
            ),
            verified=(
                verified_script_count
            ),
            unresolved=(
                unresolved_script_count
            ),
            verified_bytes=(
                verified_source_bytes
            ),
            force=True,
        )

        composition = (
            database_measurements(
                connection
            )
        )

        result: dict[
            str,
            Any,
        ] = {
            "schema": schema,
            "owner": owner,
            "module": module,
            "authority_effect": (
                authority_effect
            ),
            "projection_only": True,
            "semantic_authority": False,
            "filesystem_presence_establishes_authority": (
                False
            ),
            "generated_at": (
                utc_now()
            ),
            "source_projection": str(
                source_projection_path
            ),
            "source_projection_schema": (
                source.get(
                    "schema"
                )
            ),
            "source_file_count": len(
                files
            ),
            "source_metadata_bytes": int(
                source.get(
                    "source_bytes",
                    0,
                )
            ),
            "verified_script_count": (
                verified_script_count
            ),
            "unresolved_script_count": (
                unresolved_script_count
            ),
            "verified_source_bytes": (
                verified_source_bytes
            ),
            "verification": {
                "required": (
                    "live path bytes must "
                    "match source-datrix "
                    "sha256 and size"
                ),
                "all_current_scripts_verified": (
                    unresolved_script_count
                    == 0
                ),
                "unresolved_by_status": (
                    unresolved_counts(
                        connection
                    )
                ),
            },
            "content_edifice": list(
                content_edifice
            ),
            "directly_projectable_tiers": list(
                directly_projectable_tiers
            ),
            "unresolved_tiers": [
                {
                    "tier": tier,
                    "status": (
                        "unresolved"
                    ),
                    "reason": (
                        "no authoritative "
                        "deterministic composition "
                        "boundary is present in "
                        "current source-datrix "
                        "substance"
                    ),
                }
                for tier
                in unresolved_tiers
            ],
            "composition": (
                composition
            ),
            "working_storage": {
                "engine": (
                    "sqlite"
                ),
                "sqlite_version": (
                    sqlite3.sqlite_version
                ),
                "temporary": True,
                "authoritative": False,
                "authority_effect": (
                    "none"
                ),
                "retained_after_projection": (
                    False
                ),
            },
            "measurement_semantics": {
                "zero_kb_meaning": (
                    "zero duplicated "
                    "substantive bytes; "
                    "identities, references, "
                    "metadata, and physical "
                    "representation retain cost"
                ),
                "source_substance": (
                    "only live bytes whose "
                    "sha256 and size match the "
                    "current source-datrix "
                    "revision are measured"
                ),
                "character_measurement": (
                    "exact for verified decoded "
                    "current source substance"
                ),
                "line_measurement": (
                    "exact for verified decoded "
                    "current source substance "
                    "with line endings retained"
                ),
                "higher_tier_measurement": (
                    "not calculated until "
                    "authoritative composition "
                    "boundaries exist"
                ),
                "reference_overhead_included": (
                    False
                ),
            },
        }

        result[
            "digest"
        ] = projection_digest(
            result
        )

        return result
    finally:
        connection.close()

        for candidate in (
            working_database_path,
            Path(
                str(
                    working_database_path
                )
                + "-wal"
            ),
            Path(
                str(
                    working_database_path
                )
                + "-shm"
            ),
        ):
            try:
                candidate.unlink()
            except FileNotFoundError:
                pass


def command_project(
    source_path: Path,
    output_path: Path,
) -> int:
    source = (
        load_source_projection(
            source_path.resolve()
        )
    )

    terminal = (
        TerminalProjection(
            total=len(
                source[
                    "files"
                ]
            )
        )
    )

    result = project(
        source,
        terminal,
    )

    atomic_json(
        output_path.resolve(),
        result,
    )

    terminal.complete(
        result
    )

    return 0


def command_health() -> int:
    payload = {
        "schema": (
            "savant.carbon.straub."
            "content-edifice-health.v2"
        ),
        "status": "ok",
        "owner": owner,
        "module": module,
        "authority_effect": (
            "none"
        ),
        "projection_only": True,
        "source_projection": str(
            source_projection_path
        ),
        "source_projection_exists": (
            source_projection_path.is_file()
        ),
        "content_edifice": list(
            content_edifice
        ),
        "directly_projectable_tiers": list(
            directly_projectable_tiers
        ),
        "unresolved_tiers": list(
            unresolved_tiers
        ),
        "processing": (
            "bounded-streaming"
        ),
        "working_storage": {
            "engine": "sqlite",
            "version": (
                sqlite3.sqlite_version
            ),
            "temporary": True,
            "authoritative": False,
        },
    }

    print(
        json.dumps(
            payload,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )

    return (
        0
        if source_projection_path.is_file()
        else 1
    )


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(
        prog=(
            "straub-content-edifice"
        )
    )

    commands = (
        result.add_subparsers(
            dest="command",
            required=True,
        )
    )

    project_parser = (
        commands.add_parser(
            "project"
        )
    )

    project_parser.add_argument(
        "--source",
        type=Path,
        default=(
            source_projection_path
        ),
    )

    project_parser.add_argument(
        "--output",
        type=Path,
        default=(
            default_output_path
        ),
    )

    commands.add_parser(
        "health"
    )

    return result


def main() -> int:
    arguments = (
        parser().parse_args()
    )

    if (
        arguments.command
        == "project"
    ):
        return command_project(
            arguments.source,
            arguments.output,
        )

    if (
        arguments.command
        == "health"
    ):
        return command_health()

    return 2


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
