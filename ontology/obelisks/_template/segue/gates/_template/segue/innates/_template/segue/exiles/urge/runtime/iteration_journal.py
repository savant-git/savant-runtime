
from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any, Mapping

from iteration_controller import (
    canonical,
    digest,
    verify,
)


class journal_error(RuntimeError):
    pass


class iteration_journal:
    def __init__(self, directory: str | Path) -> None:
        self.directory = Path(directory).resolve()

        if not self.directory.is_dir():
            raise journal_error(
                "journal directory must already exist"
            )

    @staticmethod
    def _identifier(session_id: str) -> str:
        if not isinstance(session_id, str) or not session_id:
            raise journal_error("invalid session identifier")

        return digest({"session_id": session_id})

    def _path(self, session_id: str) -> Path:
        identifier = self._identifier(session_id)
        return self.directory / f"{identifier}.json"

    def save(
        self,
        session: Mapping[str, Any],
    ) -> Path:
        validated = verify(session)
        target = self._path(validated["session_id"])

        previous = None

        if target.exists():
            previous = self.load(validated["session_id"])

        if previous is not None:
            immutable = (
                "schema",
                "session_id",
                "goal",
                "iteration_limit",
                "interval_seconds",
                "created_at",
            )

            for field in immutable:
                if previous[field] != validated[field]:
                    raise journal_error(
                        f"immutable session field changed: {field}"
                    )

            old_history = previous["history"]
            new_history = validated["history"]

            if new_history[:len(old_history)] != old_history:
                raise journal_error(
                    "recorded history cannot be rewritten"
                )

        payload = canonical(validated).encode("utf-8")

        descriptor = None
        temporary = None

        try:
            descriptor, temporary = tempfile.mkstemp(
                prefix=".urge-",
                suffix=".tmp",
                dir=str(self.directory),
            )

            os.fchmod(descriptor, 0o600)

            with os.fdopen(descriptor, "wb") as stream:
                descriptor = None
                stream.write(payload)
                stream.flush()
                os.fsync(stream.fileno())

            os.replace(temporary, target)
            temporary = None

            directory_descriptor = os.open(
                str(self.directory),
                os.O_RDONLY,
            )

            try:
                os.fsync(directory_descriptor)
            finally:
                os.close(directory_descriptor)

        finally:
            if descriptor is not None:
                os.close(descriptor)

            if temporary is not None:
                try:
                    os.unlink(temporary)
                except FileNotFoundError:
                    pass

        return target

    def load(self, session_id: str) -> dict[str, Any]:
        path = self._path(session_id)

        try:
            with path.open("r", encoding="utf-8") as stream:
                data = json.load(stream)
        except (OSError, ValueError) as exc:
            raise journal_error(
                "unable to read session"
            ) from exc

        validated = verify(data)

        if validated["session_id"] != session_id:
            raise journal_error("session identity mismatch")

        return validated

    def exists(self, session_id: str) -> bool:
        return self._path(session_id).is_file()
