#!/usr/bin/env python3

from __future__ import annotations

import json
import os
import tempfile
from copy import deepcopy
from pathlib import Path
from typing import Any, Mapping, Protocol

from .model import (
    StraubValidationError,
    content_digest,
)


schema = "savant.straub.persistence.v2"
owner = "savant"
authority_effect = "none"


class StraubPersistencePort(
    Protocol
):
    def save_capsule(
        self,
        capsule: Mapping[str, Any],
    ) -> None:
        ...

    def load_capsule(
        self,
    ) -> Mapping[str, Any] | None:
        ...


def _validate_capsule(
    capsule: Mapping[str, Any],
) -> dict[str, Any]:
    if not isinstance(
        capsule,
        Mapping,
    ):
        raise StraubValidationError(
            "persistence capsule "
            "must be an object"
        )

    schema_id = str(
        capsule.get(
            "schema"
        )
        or ""
    )

    if schema_id not in {
        "savant.straub.capsule.v1",
        "savant.straub.capsule.v2",
    }:
        raise StraubValidationError(
            "unsupported persisted "
            "straub capsule"
        )

    supplied_digest = str(
        capsule.get(
            "digest"
        )
        or ""
    )

    if not supplied_digest:
        raise StraubValidationError(
            "persisted capsule digest missing"
        )

    unsigned = deepcopy(
        dict(
            capsule
        )
    )

    unsigned.pop(
        "digest",
        None,
    )

    calculated_digest = (
        content_digest(
            unsigned
        )
    )

    if (
        calculated_digest
        != supplied_digest
    ):
        raise StraubValidationError(
            "persisted capsule "
            "digest mismatch"
        )

    return deepcopy(
        dict(
            capsule
        )
    )


class MemoryPersistence:
    engine_id = "memory-reference"
    durable = False
    authoritative = False

    def __init__(
        self,
    ) -> None:
        self._capsule: (
            dict[str, Any]
            | None
        ) = None

    def save_capsule(
        self,
        capsule: Mapping[str, Any],
    ) -> None:
        self._capsule = (
            _validate_capsule(
                capsule
            )
        )

    def load_capsule(
        self,
    ) -> Mapping[str, Any] | None:
        if self._capsule is None:
            return None

        return deepcopy(
            self._capsule
        )

    def health(
        self,
    ) -> dict[str, Any]:
        return {
            "schema":
                schema,
            "adapter":
                self.engine_id,
            "durable":
                self.durable,
            "authoritative":
                self.authoritative,
            "capsule_present":
                self._capsule
                is not None,
            "storage_engine_selected":
                False,
            "authority_effect":
                authority_effect,
        }


class AtomicCapsulePersistence:
    """
    Durable canonical-capsule adapter.

    This is a persistence mechanism, not a
    second source of semantic authority.

    Parent-directory policy:

    - an existing parent directory is preserved
      exactly as owned and permissioned by its
      existing authority;
    - a parent directory created by this adapter
      is created restrictively and normalized to
      mode 0700;
    - the capsule itself remains mode 0600.
    """

    engine_id = "atomic-json-capsule"
    durable = True
    authoritative = False

    def __init__(
        self,
        path: str | Path,
    ) -> None:
        self.path = Path(
            path
        ).resolve()

    def _ensure_parent_directory(
        self,
    ) -> bool:
        parent = self.path.parent

        if parent.exists():
            if not parent.is_dir():
                raise StraubValidationError(
                    "straub persistence parent "
                    "is not a directory"
                )

            return False

        try:
            parent.mkdir(
                mode=0o700,
                parents=True,
                exist_ok=False,
            )
        except FileExistsError:
            if not parent.is_dir():
                raise StraubValidationError(
                    "straub persistence parent "
                    "is not a directory"
                )

            return False
        except OSError as exc:
            raise StraubValidationError(
                "unable to create straub "
                "persistence parent"
            ) from exc

        try:
            os.chmod(
                parent,
                0o700,
            )
        except OSError as exc:
            raise StraubValidationError(
                "unable to secure created "
                "straub persistence parent"
            ) from exc

        return True

    def _sync_directory(
        self,
    ) -> None:
        directory_fd = os.open(
            str(
                self.path.parent
            ),
            os.O_RDONLY,
        )

        try:
            os.fsync(
                directory_fd
            )
        finally:
            os.close(
                directory_fd
            )

    def save_capsule(
        self,
        capsule: Mapping[str, Any],
    ) -> None:
        validated = (
            _validate_capsule(
                capsule
            )
        )

        self._ensure_parent_directory()

        fd, temporary_name = (
            tempfile.mkstemp(
                prefix=(
                    "."
                    + self.path.name
                    + "."
                ),
                suffix=".tmp",
                dir=str(
                    self.path.parent
                ),
                text=True,
            )
        )

        temporary_path = Path(
            temporary_name
        )

        try:
            os.fchmod(
                fd,
                0o600,
            )

            with os.fdopen(
                fd,
                "w",
                encoding="utf-8",
            ) as handle:
                json.dump(
                    validated,
                    handle,
                    sort_keys=True,
                    separators=(
                        ",",
                        ":",
                    ),
                    ensure_ascii=False,
                )

                handle.write(
                    "\n"
                )

                handle.flush()

                os.fsync(
                    handle.fileno()
                )

            os.replace(
                temporary_path,
                self.path,
            )

            os.chmod(
                self.path,
                0o600,
            )

            self._sync_directory()

        finally:
            if temporary_path.exists():
                temporary_path.unlink()

    def load_capsule(
        self,
    ) -> Mapping[str, Any] | None:
        try:
            raw = self.path.read_text(
                encoding="utf-8"
            )
        except FileNotFoundError:
            return None
        except OSError as exc:
            raise StraubValidationError(
                "unable to read persisted "
                "straub capsule"
            ) from exc

        try:
            value = json.loads(
                raw
            )
        except json.JSONDecodeError as exc:
            raise StraubValidationError(
                "persisted straub capsule "
                "is invalid json"
            ) from exc

        return _validate_capsule(
            value
        )

    def delete_for_test(
        self,
    ) -> None:
        try:
            self.path.unlink()
        except FileNotFoundError:
            return

    def health(
        self,
    ) -> dict[str, Any]:
        exists = self.path.exists()

        mode: int | None = None

        if exists:
            mode = (
                self.path.stat().st_mode
                & 0o777
            )

        parent_exists = (
            self.path.parent.exists()
        )

        parent_mode: int | None = None

        if parent_exists:
            parent_mode = (
                self.path.parent.stat().st_mode
                & 0o777
            )

        return {
            "schema":
                schema,
            "adapter":
                self.engine_id,
            "durable":
                self.durable,
            "authoritative":
                self.authoritative,
            "path":
                str(
                    self.path
                ),
            "capsule_present":
                exists,
            "file_mode":
                (
                    oct(
                        mode
                    )
                    if mode is not None
                    else None
                ),
            "parent_directory_present":
                parent_exists,
            "parent_directory_mode":
                (
                    oct(
                        parent_mode
                    )
                    if parent_mode is not None
                    else None
                ),
            "preserves_existing_parent_mode":
                True,
            "created_parent_mode":
                "0o700",
            "atomic_replace":
                True,
            "file_fsync":
                True,
            "directory_fsync":
                True,
            "storage_engine_selected":
                False,
            "authority_effect":
                authority_effect,
        }
