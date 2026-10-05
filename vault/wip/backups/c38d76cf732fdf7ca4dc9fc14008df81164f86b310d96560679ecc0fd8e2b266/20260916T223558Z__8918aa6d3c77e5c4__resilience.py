#!/usr/bin/env python3

from __future__ import annotations

import fcntl
import os
from pathlib import Path
from typing import Any, Mapping

from .model import StraubValidationError
from .persistence import AtomicCapsulePersistence


schema = "savant.straub.resilience.v1"
owner = "savant"
authority_effect = "none"


class _FileLock:
    def __init__(
        self,
        path: str | Path,
        *,
        exclusive: bool,
    ) -> None:
        self.path = Path(path).resolve()
        self.exclusive = bool(exclusive)
        self._fd: int | None = None

    def __enter__(
        self,
    ) -> "_FileLock":
        self.path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        self._fd = os.open(
            str(self.path),
            os.O_CREAT | os.O_RDWR,
            0o600,
        )

        os.fchmod(
            self._fd,
            0o600,
        )

        operation = (
            fcntl.LOCK_EX
            if self.exclusive
            else fcntl.LOCK_SH
        )

        fcntl.flock(
            self._fd,
            operation,
        )

        return self

    def __exit__(
        self,
        exc_type: Any,
        exc: Any,
        traceback: Any,
    ) -> None:
        if self._fd is None:
            return

        try:
            fcntl.flock(
                self._fd,
                fcntl.LOCK_UN,
            )
        finally:
            os.close(
                self._fd
            )
            self._fd = None


class ResilientCapsulePersistence:
    """
    Locked redundant custody for Straub capsules.

    The adapter is durable and recoverable but never
    semantic authority. The canonical capsule remains
    the substance being preserved.
    """

    engine_id = "resilient-atomic-capsule"
    durable = True
    authoritative = False
    storage_engine_selected = False

    def __init__(
        self,
        path: str | Path,
    ) -> None:
        self.path = Path(path).resolve()

        self.backup_path = self.path.with_name(
            self.path.name + ".bak"
        )

        self.lock_path = self.path.with_name(
            self.path.name + ".lock"
        )

        self._primary = AtomicCapsulePersistence(
            self.path
        )

        self._backup = AtomicCapsulePersistence(
            self.backup_path
        )

        self._last_recovery_source: str | None = None

    def save_capsule(
        self,
        capsule: Mapping[str, Any],
    ) -> None:
        with _FileLock(
            self.lock_path,
            exclusive=True,
        ):
            self._primary.save_capsule(
                capsule
            )

            verified = self._primary.load_capsule()

            if verified is None:
                raise StraubValidationError(
                    "primary capsule disappeared "
                    "after durable save"
                )

            self._backup.save_capsule(
                verified
            )

            backup_verified = (
                self._backup.load_capsule()
            )

            if backup_verified is None:
                raise StraubValidationError(
                    "backup capsule disappeared "
                    "after durable save"
                )

            if (
                backup_verified.get("digest")
                != verified.get("digest")
            ):
                raise StraubValidationError(
                    "primary and backup capsule "
                    "digests differ"
                )

            self._last_recovery_source = "primary"

    def load_capsule(
        self,
    ) -> Mapping[str, Any] | None:
        with _FileLock(
            self.lock_path,
            exclusive=False,
        ):
            primary_error: Exception | None = None

            try:
                primary = self._primary.load_capsule()
            except Exception as exc:
                primary = None
                primary_error = exc

            if primary is not None:
                self._last_recovery_source = "primary"
                return primary

            try:
                backup = self._backup.load_capsule()
            except Exception as exc:
                if primary_error is not None:
                    raise StraubValidationError(
                        "both primary and backup "
                        "straub capsules are invalid"
                    ) from exc

                raise

            if backup is not None:
                self._last_recovery_source = "backup"
                return backup

            if primary_error is not None:
                raise StraubValidationError(
                    "primary straub capsule invalid "
                    "and no recovery capsule exists"
                ) from primary_error

            self._last_recovery_source = None
            return None

    def repair_primary_from_backup(
        self,
    ) -> bool:
        with _FileLock(
            self.lock_path,
            exclusive=True,
        ):
            backup = self._backup.load_capsule()

            if backup is None:
                return False

            self._primary.save_capsule(
                backup
            )

            verified = self._primary.load_capsule()

            if verified is None:
                raise StraubValidationError(
                    "primary repair failed"
                )

            if (
                verified.get("digest")
                != backup.get("digest")
            ):
                raise StraubValidationError(
                    "repaired primary digest mismatch"
                )

            self._last_recovery_source = "primary"

            return True

    def health(
        self,
    ) -> dict[str, Any]:
        primary_present = self.path.exists()
        backup_present = self.backup_path.exists()
        lock_present = self.lock_path.exists()

        primary_mode = (
            oct(
                self.path.stat().st_mode
                & 0o777
            )
            if primary_present
            else None
        )

        backup_mode = (
            oct(
                self.backup_path.stat().st_mode
                & 0o777
            )
            if backup_present
            else None
        )

        return {
            "schema":
                schema,
            "adapter":
                self.engine_id,
            "durable":
                True,
            "authoritative":
                False,
            "storage_engine_selected":
                False,
            "primary_present":
                primary_present,
            "backup_present":
                backup_present,
            "lock_present":
                lock_present,
            "primary_mode":
                primary_mode,
            "backup_mode":
                backup_mode,
            "interprocess_locking":
                True,
            "shared_read_lock":
                True,
            "exclusive_write_lock":
                True,
            "redundant_capsule":
                True,
            "last_recovery_source":
                self._last_recovery_source,
            "authority_effect":
                authority_effect,
        }
