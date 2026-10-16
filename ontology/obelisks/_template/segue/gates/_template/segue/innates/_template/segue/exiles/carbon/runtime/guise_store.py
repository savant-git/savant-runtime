#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any, Mapping

from guise import (
    OWNER,
    SCHEMA,
    SPECIALIZATION,
    GuiseError,
    canonical_json,
    digest,
)


ROOT = Path("/root/savant-runtime").resolve()

DEFAULT_STORE_ROOT = (
    ROOT
    / "runtime"
    / "state"
    / "carbon"
    / "guise"
).resolve()


class GuiseStoreError(GuiseError):
    pass


def _safe_component(value: str) -> str:
    normalized = str(value or "").strip().lower()

    if not normalized:
        raise GuiseStoreError(
            "storage identifier is required"
        )

    allowed = set(
        "abcdefghijklmnopqrstuvwxyz"
        "0123456789"
        "-_."
    )

    if any(
        character not in allowed
        for character in normalized
    ):
        raise GuiseStoreError(
            "storage identifiers may contain only "
            "lowercase letters, digits, dash, "
            "underscore, and period"
        )

    if normalized in {".", ".."}:
        raise GuiseStoreError(
            "invalid storage identifier"
        )

    return normalized


def _atomic_write_json(
    path: Path,
    payload: Mapping[str, Any],
) -> None:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    encoded = (
        json.dumps(
            dict(payload),
            ensure_ascii=False,
            sort_keys=True,
            indent=2,
        )
        + "\n"
    )

    descriptor, temporary_name = (
        tempfile.mkstemp(
            prefix=f".{path.name}.",
            suffix=".tmp",
            dir=str(path.parent),
            text=True,
        )
    )

    temporary = Path(temporary_name)

    try:
        with os.fdopen(
            descriptor,
            "w",
            encoding="utf-8",
        ) as handle:
            handle.write(encoded)
            handle.flush()
            os.fsync(handle.fileno())

        os.replace(
            temporary,
            path,
        )

    finally:
        if temporary.exists():
            temporary.unlink()


class GuiseStore:
    def __init__(
        self,
        root: Path | str = DEFAULT_STORE_ROOT,
    ) -> None:
        self.root = Path(root).resolve()

    def character_root(
        self,
        character_id: str,
    ) -> Path:
        identifier = _safe_component(
            character_id
        )

        path = (
            self.root
            / "characters"
            / identifier
        ).resolve()

        expected_parent = (
            self.root
            / "characters"
        ).resolve()

        if expected_parent not in path.parents:
            raise GuiseStoreError(
                "character path escaped store root"
            )

        return path

    def head_path(
        self,
        character_id: str,
    ) -> Path:
        return (
            self.character_root(character_id)
            / "head.json"
        )

    def versions_root(
        self,
        character_id: str,
    ) -> Path:
        return (
            self.character_root(character_id)
            / "versions"
        )

    def version_path(
        self,
        character_id: str,
        projection_digest: str,
    ) -> Path:
        version = _safe_component(
            projection_digest
        )

        return (
            self.versions_root(character_id)
            / f"{version}.json"
        )

    def exists(
        self,
        character_id: str,
    ) -> bool:
        return self.head_path(
            character_id
        ).is_file()

    def save_projection(
        self,
        projection: Mapping[str, Any],
    ) -> dict[str, Any]:
        value = dict(projection)

        character_id = str(
            value.get(
                "character_id",
                "",
            )
        ).strip()

        if not character_id:
            raise GuiseStoreError(
                "projection character_id "
                "is required"
            )

        if value.get(
            "authority_effect"
        ) != "none":
            raise GuiseStoreError(
                "guise store accepts only "
                "non-authoritative projections"
            )

        projection_digest = str(
            value.get(
                "projection_digest",
                "",
            )
        ).strip()

        calculated = digest(
            {
                key: item
                for key, item in value.items()
                if key != "projection_digest"
            }
        )

        if not projection_digest:
            projection_digest = calculated
            value[
                "projection_digest"
            ] = calculated

        elif projection_digest != calculated:
            raise GuiseStoreError(
                "projection digest mismatch"
            )

        version_path = self.version_path(
            character_id,
            projection_digest,
        )

        if not version_path.exists():
            _atomic_write_json(
                version_path,
                value,
            )

        head = {
            "schema": SCHEMA,
            "owner": OWNER,
            "specialization": SPECIALIZATION,
            "kind": "character_projection_head",
            "character_id": character_id,
            "projection_digest": (
                projection_digest
            ),
            "version_path": str(
                version_path
            ),
            "authority_effect": "none",
        }

        _atomic_write_json(
            self.head_path(character_id),
            head,
        )

        return {
            "status": "saved",
            "character_id": character_id,
            "projection_digest": (
                projection_digest
            ),
            "head_path": str(
                self.head_path(character_id)
            ),
            "version_path": str(
                version_path
            ),
            "authority_effect": "none",
        }

    def load_head(
        self,
        character_id: str,
    ) -> dict[str, Any]:
        path = self.head_path(
            character_id
        )

        if not path.is_file():
            raise GuiseStoreError(
                f"character not found: "
                f"{character_id}"
            )

        try:
            head = json.loads(
                path.read_text(
                    encoding="utf-8"
                )
            )
        except json.JSONDecodeError as exc:
            raise GuiseStoreError(
                "character head is invalid json"
            ) from exc

        version_path = Path(
            head["version_path"]
        ).resolve()

        versions_root = self.versions_root(
            character_id
        ).resolve()

        if versions_root not in (
            version_path.parents
        ):
            raise GuiseStoreError(
                "stored version path escaped "
                "character repository"
            )

        try:
            projection = json.loads(
                version_path.read_text(
                    encoding="utf-8"
                )
            )
        except FileNotFoundError as exc:
            raise GuiseStoreError(
                "character head references "
                "missing version"
            ) from exc
        except json.JSONDecodeError as exc:
            raise GuiseStoreError(
                "character version is invalid json"
            ) from exc

        calculated = digest(
            {
                key: item
                for key, item
                in projection.items()
                if key
                != "projection_digest"
            }
        )

        if calculated != head[
            "projection_digest"
        ]:
            raise GuiseStoreError(
                "stored character projection "
                "failed digest verification"
            )

        return projection

    def versions(
        self,
        character_id: str,
    ) -> list[str]:
        root = self.versions_root(
            character_id
        )

        if not root.is_dir():
            return []

        return sorted(
            path.stem
            for path in root.glob(
                "*.json"
            )
            if path.is_file()
        )

    def status(self) -> dict[str, Any]:
        characters_root = (
            self.root
            / "characters"
        )

        characters = []

        if characters_root.is_dir():
            characters = sorted(
                path.name
                for path
                in characters_root.iterdir()
                if (
                    path.is_dir()
                    and (
                        path
                        / "head.json"
                    ).is_file()
                )
            )

        return {
            "schema": SCHEMA,
            "owner": OWNER,
            "specialization": SPECIALIZATION,
            "kind": "guise_store_status",
            "root": str(self.root),
            "characters": characters,
            "character_count": len(
                characters
            ),
            "authority_effect": "none",
        }
