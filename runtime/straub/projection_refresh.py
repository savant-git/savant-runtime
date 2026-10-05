#!/usr/bin/env python3

from __future__ import annotations

import fcntl
import os
from pathlib import Path
from typing import Any, Mapping

from .materialized import (
    AtomicIsotopeCache,
    StraubIsotopeIndex,
)
from .model import (
    StraubValidationError,
)


schema = "savant.straub.projection-refresh.v1"
owner = "savant"
authority_effect = "none"


class _ProjectionLock:
    def __init__(
        self,
        path: str | Path,
        *,
        exclusive: bool,
    ) -> None:
        self.path = Path(
            path
        ).resolve()

        self.exclusive = bool(
            exclusive
        )

        self._fd: int | None = None

    def __enter__(
        self,
    ) -> "_ProjectionLock":
        self.path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        self._fd = os.open(
            str(
                self.path
            ),
            os.O_CREAT
            | os.O_RDWR,
            0o600,
        )

        os.fchmod(
            self._fd,
            0o600,
        )

        fcntl.flock(
            self._fd,
            (
                fcntl.LOCK_EX
                if self.exclusive
                else fcntl.LOCK_SH
            ),
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


class ContentionSafeIsotope:
    """
    Inter-process synchronization around rebuildable isotope.

    Lock state is operational only. It never participates
    in Straub semantic identity, authority, or projection
    digests.
    """

    authoritative = False
    projection_only = True

    def __init__(
        self,
        path: str | Path,
    ) -> None:
        self.path = Path(
            path
        ).resolve()

        self.lock_path = (
            self.path.with_name(
                self.path.name
                + ".lock"
            )
        )

        self._cache = AtomicIsotopeCache(
            self.path
        )

    def load(
        self,
        *,
        capsule_digest: str,
    ) -> dict[str, Any] | None:
        with _ProjectionLock(
            self.lock_path,
            exclusive=False,
        ):
            return self._cache.load(
                capsule_digest=(
                    capsule_digest
                )
            )

    def refresh(
        self,
        capsule: Mapping[str, Any],
    ) -> dict[str, Any]:
        capsule_digest = str(
            capsule.get(
                "digest"
            )
            or ""
        )

        if not capsule_digest:
            raise StraubValidationError(
                "isotope refresh requires "
                "capsule digest"
            )

        with _ProjectionLock(
            self.lock_path,
            exclusive=True,
        ):
            current = self._cache.load(
                capsule_digest=(
                    capsule_digest
                )
            )

            if (
                current is not None
                and current[
                    "status"
                ][
                    "fresh"
                ]
                is True
            ):
                return {
                    "schema":
                        schema,
                    "action":
                        "reuse",
                    "source_capsule_digest":
                        capsule_digest,
                    "projection":
                        current[
                            "projection"
                        ],
                    "fresh":
                        True,
                    "mutation_performed":
                        False,
                    "semantic_mutation":
                        False,
                    "projection_only":
                        True,
                    "authority_effect":
                        "none",
                }

            projection = (
                StraubIsotopeIndex(
                    capsule
                ).materialize()
            )

            self._cache.save(
                projection
            )

            verified = self._cache.load(
                capsule_digest=(
                    capsule_digest
                )
            )

            if (
                verified is None
                or verified[
                    "status"
                ][
                    "fresh"
                ]
                is not True
            ):
                raise StraubValidationError(
                    "isotope refresh verification "
                    "failed"
                )

            if (
                verified[
                    "projection"
                ][
                    "digest"
                ]
                != projection[
                    "digest"
                ]
            ):
                raise StraubValidationError(
                    "isotope refresh digest mismatch"
                )

            return {
                "schema":
                    schema,
                "action":
                    "rebuild",
                "source_capsule_digest":
                    capsule_digest,
                "projection":
                    projection,
                "fresh":
                    True,
                "mutation_performed":
                    True,
                "semantic_mutation":
                    False,
                "projection_only":
                    True,
                "authority_effect":
                    "none",
            }

    def status(
        self,
        *,
        capsule_digest: str,
    ) -> dict[str, Any]:
        loaded = self.load(
            capsule_digest=(
                capsule_digest
            )
        )

        if loaded is None:
            return {
                "schema":
                    "savant.straub."
                    "projection-refresh-status.v1",
                "present":
                    False,
                "fresh":
                    False,
                "rebuild_required":
                    True,
                "projection_digest":
                    None,
                "interprocess_locking":
                    True,
                "projection_only":
                    True,
                "authority_effect":
                    "none",
            }

        return {
            "schema":
                "savant.straub."
                "projection-refresh-status.v1",
            "present":
                True,
            "fresh":
                loaded[
                    "status"
                ][
                    "fresh"
                ],
            "rebuild_required":
                loaded[
                    "status"
                ][
                    "rebuild_required"
                ],
            "projection_digest":
                loaded[
                    "projection"
                ][
                    "digest"
                ],
            "interprocess_locking":
                True,
            "projection_only":
                True,
            "authority_effect":
                "none",
        }

