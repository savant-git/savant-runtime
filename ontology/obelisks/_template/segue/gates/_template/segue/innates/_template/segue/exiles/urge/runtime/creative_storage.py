from __future__ import annotations

import json
import os
import tempfile
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from . import creative_session


schema = "savant://runtime/urge/creative-storage/1.0.0"
owner = "exile:urge"


class creative_storage_error(RuntimeError):
    pass


def _root(directory: str | Path) -> Path:
    path = Path(directory).resolve()

    if not path.is_dir():
        raise creative_storage_error(
            "storage directory does not exist"
        )

    return path


def _name(session_id: str) -> str:
    if not isinstance(session_id, str):
        raise creative_storage_error(
            "session_id must be a string"
        )

    if not session_id:
        raise creative_storage_error(
            "session_id is required"
        )

    if any(
        character not in
        "abcdefghijklmnopqrstuvwxyz"
        "0123456789-_"
        for character in session_id
    ):
        raise creative_storage_error(
            "session_id contains invalid characters"
        )

    return session_id + ".json"


def _validated(
    session: Mapping[str, Any],
) -> dict[str, Any]:
    return creative_session._session(session)


def save(
    directory: str | Path,
    session: Mapping[str, Any],
) -> Path:
    current = _validated(session)

    root = _root(directory)

    destination = (
        root / _name(current["session_id"])
    )

    encoded = json.dumps(
        current,
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")

    temporary = None

    try:
        with tempfile.NamedTemporaryFile(
            mode="wb",
            prefix=".creative-",
            suffix=".tmp",
            dir=root,
            delete=False,
        ) as stream:
            temporary = Path(stream.name)
            stream.write(encoded)
            stream.flush()
            os.fsync(stream.fileno())

        os.replace(
            temporary,
            destination,
        )

        directory_fd = os.open(
            root,
            os.O_RDONLY,
        )

        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)

    finally:
        if (
            temporary is not None
            and temporary.exists()
        ):
            temporary.unlink()

    return destination


def load(
    directory: str | Path,
    session_id: str,
) -> dict[str, Any]:
    path = (
        _root(directory)
        / _name(session_id)
    )

    try:
        with path.open(
            "r",
            encoding="utf-8",
        ) as stream:
            data = json.load(stream)
    except (OSError, ValueError) as exc:
        raise creative_storage_error(
            "unable to load session"
        ) from exc

    session = _validated(data)

    if session["session_id"] != session_id:
        raise creative_storage_error(
            "session identity mismatch"
        )

    return session


def exists(
    directory: str | Path,
    session_id: str,
) -> bool:
    return (
        _root(directory)
        / _name(session_id)
    ).is_file()


def create(
    directory: str | Path,
    *,
    brief: str,
    session_id: str,
    continuity: bool = True,
) -> dict[str, Any]:
    if exists(directory, session_id):
        raise creative_storage_error(
            "session already exists"
        )

    session = creative_session.create(
        brief=brief,
        session_id=session_id,
        continuity=continuity,
    )

    save(
        directory,
        session,
    )

    return session
