#!/usr/bin/env python3

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any, Mapping

from .migration import (
    validate_keyed_representation,
)
from .model import (
    StraubValidationError,
)


schema = "savant.straub.representation-store.v1"
owner = "savant"
authority_effect = "none"


class AtomicRepresentationStore:
    durable = True
    authoritative = False
    projection_only = True

    def __init__(
        self,
        path: str | Path,
    ) -> None:
        self.path = Path(
            path
        ).resolve()

    def save(
        self,
        representation: Mapping[str, Any],
    ) -> None:
        validate_keyed_representation(
            representation
        )

        self.path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        os.chmod(
            self.path.parent,
            0o700,
        )

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
                    dict(
                        representation
                    ),
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

        finally:
            if temporary_path.exists():
                temporary_path.unlink()

    def load(
        self,
    ) -> dict[str, Any] | None:
        try:
            raw = self.path.read_text(
                encoding="utf-8"
            )
        except FileNotFoundError:
            return None
        except OSError as exc:
            raise StraubValidationError(
                "unable to read straub "
                "representation"
            ) from exc

        try:
            representation = json.loads(
                raw
            )
        except json.JSONDecodeError as exc:
            raise StraubValidationError(
                "stored straub representation "
                "is invalid json"
            ) from exc

        validate_keyed_representation(
            representation
        )

        return representation

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

        return {
            "schema":
                schema,
            "adapter":
                "atomic-representation-store",
            "durable":
                self.durable,
            "authoritative":
                self.authoritative,
            "projection_only":
                self.projection_only,
            "present":
                exists,
            "file_mode":
                (
                    oct(
                        mode
                    )
                    if mode is not None
                    else None
                ),
            "authority_effect":
                authority_effect,
        }
