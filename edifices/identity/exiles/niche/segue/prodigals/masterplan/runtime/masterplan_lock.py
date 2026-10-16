#!/usr/bin/env python3
from __future__ import annotations

import contextlib
import datetime as dt
import errno
import fcntl
import hashlib
import json
import os
import socket
import tempfile
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator


ROOT = Path("/root/savant-runtime")

GRAPH_PATH = (
    ROOT
    / "authority"
    / "task-graph"
    / "masterplan.json"
)

LOCK_ROOT = (
    ROOT
    / "runtime"
    / "masterplan"
    / "locks"
)

REPORT_ROOT = (
    ROOT
    / "reports"
    / "niche"
    / "masterplan"
    / "locks"
)

DEFAULT_LOCK_PATH = (
    LOCK_ROOT
    / "masterplan.lock"
)

DEFAULT_METADATA_PATH = (
    LOCK_ROOT
    / "masterplan.lock.json"
)

VOLATILE_FIELDS = {
    "generated_at",
    "acquired_at",
    "released_at",
    "heartbeat_at",
    "expires_at",
    "started_at",
    "finished_at",
    "duration_seconds",
    "elapsed_seconds",
    "wall_clock_seconds",
    "timestamp",
}


class MasterplanLockError(RuntimeError):
    pass


class MasterplanLockTimeout(MasterplanLockError):
    pass


class MasterplanStaleWriteError(MasterplanLockError):
    pass


class MasterplanLockOwnershipError(MasterplanLockError):
    pass


@dataclass(frozen=True)
class LockPaths:
    lock: Path
    metadata: Path


@dataclass
class MasterplanLock:
    owner: str
    operation: str
    expected_graph_digest: str | None = None
    timeout_seconds: float = 30.0
    poll_seconds: float = 0.1
    lease_seconds: int = 300
    paths: LockPaths = LockPaths(
        lock=DEFAULT_LOCK_PATH,
        metadata=DEFAULT_METADATA_PATH,
    )

    _handle: Any = None
    _lock_id: str | None = None
    _acquired_at: str | None = None
    _pre_graph_digest: str | None = None

    def acquire(self) -> "MasterplanLock":
        self.paths.lock.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        self.paths.metadata.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        self._handle = self.paths.lock.open(
            "a+",
            encoding="utf-8",
        )

        deadline = (
            time.monotonic()
            + self.timeout_seconds
        )

        while True:
            try:
                fcntl.flock(
                    self._handle.fileno(),
                    (
                        fcntl.LOCK_EX
                        | fcntl.LOCK_NB
                    ),
                )

                break

            except BlockingIOError:
                if (
                    time.monotonic()
                    >= deadline
                ):
                    holder = self.current_holder()

                    self._close_handle()

                    raise MasterplanLockTimeout(
                        json.dumps(
                            {
                                "code": (
                                    "masterplan.lock.timeout"
                                ),
                                "owner": self.owner,
                                "operation": self.operation,
                                "timeout_seconds": (
                                    self.timeout_seconds
                                ),
                                "holder": holder,
                            },
                            ensure_ascii=False,
                            sort_keys=True,
                        )
                    )

                time.sleep(
                    self.poll_seconds
                )

            except OSError as exc:
                self._close_handle()

                raise MasterplanLockError(
                    (
                        "Unable to acquire "
                        f"Masterplan lock: {exc}"
                    )
                ) from exc

        self._lock_id = (
            "lock-"
            + uuid.uuid4().hex
        )

        self._acquired_at = utc_now()

        self._pre_graph_digest = (
            graph_digest(
                GRAPH_PATH
            )
            if GRAPH_PATH.is_file()
            else None
        )

        if (
            self.expected_graph_digest
            is not None
            and self._pre_graph_digest
            != self.expected_graph_digest
        ):
            actual = self._pre_graph_digest

            self.release(
                passed=False,
                failure_code=(
                    "masterplan.write."
                    "stale_precondition"
                ),
            )

            raise MasterplanStaleWriteError(
                json.dumps(
                    {
                        "code": (
                            "masterplan.write."
                            "stale_precondition"
                        ),
                        "expected_graph_digest": (
                            self.expected_graph_digest
                        ),
                        "actual_graph_digest": (
                            actual
                        ),
                        "owner": self.owner,
                        "operation": self.operation,
                    },
                    ensure_ascii=False,
                    sort_keys=True,
                )
            )

        self._write_metadata(
            state="held",
        )

        self._write_report(
            operation="acquire",
            passed=True,
            payload={
                "lock_id": self._lock_id,
                "owner": self.owner,
                "guarded_operation": (
                    self.operation
                ),
                "graph_digest": (
                    self._pre_graph_digest
                ),
            },
        )

        return self

    def heartbeat(self) -> None:
        self._assert_owned()

        metadata = self._metadata_payload(
            state="held",
        )

        metadata[
            "heartbeat_at"
        ] = utc_now()

        metadata[
            "expires_at"
        ] = (
            dt.datetime.now(
                dt.timezone.utc
            )
            + dt.timedelta(
                seconds=self.lease_seconds
            )
        ).replace(
            microsecond=0
        ).isoformat()

        atomic_write_json(
            self.paths.metadata,
            metadata,
        )

    def validate_graph_precondition(
        self,
    ) -> str | None:
        self._assert_owned()

        actual = (
            graph_digest(
                GRAPH_PATH
            )
            if GRAPH_PATH.is_file()
            else None
        )

        if (
            actual
            != self._pre_graph_digest
        ):
            raise MasterplanStaleWriteError(
                json.dumps(
                    {
                        "code": (
                            "masterplan.write."
                            "graph_changed_while_locked"
                        ),
                        "expected_graph_digest": (
                            self._pre_graph_digest
                        ),
                        "actual_graph_digest": (
                            actual
                        ),
                        "lock_id": self._lock_id,
                    },
                    ensure_ascii=False,
                    sort_keys=True,
                )
            )

        return actual

    def release(
        self,
        *,
        passed: bool,
        post_graph_digest: str | None = None,
        failure_code: str | None = None,
    ) -> None:
        if self._handle is None:
            return

        metadata = self._metadata_payload(
            state="released",
        )

        metadata[
            "released_at"
        ] = utc_now()

        metadata[
            "passed"
        ] = passed

        metadata[
            "post_graph_digest"
        ] = post_graph_digest

        metadata[
            "failure_code"
        ] = failure_code

        try:
            atomic_write_json(
                self.paths.metadata,
                metadata,
            )

            self._write_report(
                operation="release",
                passed=passed,
                payload={
                    "lock_id": self._lock_id,
                    "owner": self.owner,
                    "guarded_operation": (
                        self.operation
                    ),
                    "pre_graph_digest": (
                        self._pre_graph_digest
                    ),
                    "post_graph_digest": (
                        post_graph_digest
                    ),
                    "failure_code": (
                        failure_code
                    ),
                },
            )

        finally:
            try:
                fcntl.flock(
                    self._handle.fileno(),
                    fcntl.LOCK_UN,
                )

            finally:
                self._close_handle()

    def current_holder(
        self,
    ) -> dict[str, Any] | None:
        if not self.paths.metadata.is_file():
            return None

        try:
            value = load_json(
                self.paths.metadata
            )

        except Exception:
            return {
                "state": "unreadable",
                "path": str(
                    self.paths.metadata
                ),
            }

        return value

    def _assert_owned(self) -> None:
        if (
            self._handle is None
            or self._lock_id is None
        ):
            raise MasterplanLockOwnershipError(
                "Masterplan lock is not held."
            )

        try:
            fcntl.flock(
                self._handle.fileno(),
                (
                    fcntl.LOCK_EX
                    | fcntl.LOCK_NB
                ),
            )

        except OSError as exc:
            raise MasterplanLockOwnershipError(
                "Masterplan lock ownership was lost."
            ) from exc

    def _metadata_payload(
        self,
        *,
        state: str,
    ) -> dict[str, Any]:
        acquired_at = (
            self._acquired_at
            or utc_now()
        )

        expires_at = (
            dt.datetime.fromisoformat(
                acquired_at
            )
            + dt.timedelta(
                seconds=self.lease_seconds
            )
        ).replace(
            microsecond=0
        ).isoformat()

        payload = {
            "schema": (
                "savant://niche/masterplan/"
                "mutation-lock/1.0.0"
            ),
            "lock_id": self._lock_id,
            "state": state,
            "owner": self.owner,
            "operation": self.operation,
            "pid": os.getpid(),
            "process_group_id": (
                os.getpgrp()
            ),
            "host": socket.gethostname(),
            "acquired_at": acquired_at,
            "heartbeat_at": utc_now(),
            "expires_at": expires_at,
            "lease_seconds": (
                self.lease_seconds
            ),
            "lock_path": relative_path(
                self.paths.lock
            ),
            "metadata_path": relative_path(
                self.paths.metadata
            ),
            "expected_graph_digest": (
                self.expected_graph_digest
            ),
            "pre_graph_digest": (
                self._pre_graph_digest
            ),
        }

        payload[
            "semantic_digest"
        ] = digest(
            deterministic_projection(
                payload
            )
        )

        return payload

    def _write_metadata(
        self,
        *,
        state: str,
    ) -> None:
        atomic_write_json(
            self.paths.metadata,
            self._metadata_payload(
                state=state,
            ),
        )

    def _write_report(
        self,
        *,
        operation: str,
        passed: bool,
        payload: dict[str, Any],
    ) -> None:
        REPORT_ROOT.mkdir(
            parents=True,
            exist_ok=True,
        )

        report = {
            "schema": (
                "savant://niche/masterplan/"
                "mutation-lock-receipt/1.0.0"
            ),
            "operation": (
                f"masterplan_lock_{operation}"
            ),
            "generated_at": utc_now(),
            "passed": passed,
            **payload,
        }

        report[
            "semantic_digest"
        ] = digest(
            deterministic_projection(
                report
            )
        )

        run_id = (
            timestamp()
            + "__"
            + str(
                self._lock_id
                or "unknown"
            )
            + "__"
            + operation
        )

        atomic_write_json(
            REPORT_ROOT
            / f"{run_id}.json",
            report,
        )

        atomic_write_json(
            REPORT_ROOT
            / "latest.json",
            report,
        )

    def _close_handle(self) -> None:
        if self._handle is None:
            return

        with contextlib.suppress(
            Exception
        ):
            self._handle.close()

        self._handle = None

    def __enter__(
        self,
    ) -> "MasterplanLock":
        return self.acquire()

    def __exit__(
        self,
        exception_type: Any,
        exception: Any,
        traceback: Any,
    ) -> bool:
        passed = (
            exception_type is None
        )

        failure_code = (
            None
            if passed
            else (
                "masterplan.lock."
                "guarded_operation_failed"
            )
        )

        post_digest = (
            graph_digest(
                GRAPH_PATH
            )
            if GRAPH_PATH.is_file()
            else None
        )

        self.release(
            passed=passed,
            post_graph_digest=(
                post_digest
            ),
            failure_code=(
                failure_code
            ),
        )

        return False


@contextlib.contextmanager
def guarded_masterplan_mutation(
    *,
    owner: str,
    operation: str,
    expected_graph_digest: str | None = None,
    timeout_seconds: float = 30.0,
    poll_seconds: float = 0.1,
    lease_seconds: int = 300,
) -> Iterator[MasterplanLock]:
    lock = MasterplanLock(
        owner=owner,
        operation=operation,
        expected_graph_digest=(
            expected_graph_digest
        ),
        timeout_seconds=(
            timeout_seconds
        ),
        poll_seconds=poll_seconds,
        lease_seconds=lease_seconds,
    )

    lock.acquire()

    try:
        yield lock

    except Exception:
        post_digest = (
            graph_digest(
                GRAPH_PATH
            )
            if GRAPH_PATH.is_file()
            else None
        )

        lock.release(
            passed=False,
            post_graph_digest=(
                post_digest
            ),
            failure_code=(
                "masterplan.mutation.failed"
            ),
        )

        raise

    else:
        post_digest = (
            graph_digest(
                GRAPH_PATH
            )
            if GRAPH_PATH.is_file()
            else None
        )

        lock.release(
            passed=True,
            post_graph_digest=(
                post_digest
            ),
        )


def utc_now() -> str:
    return (
        dt.datetime.now(
            dt.timezone.utc
        )
        .replace(
            microsecond=0
        )
        .isoformat()
    )


def timestamp() -> str:
    return dt.datetime.now(
        dt.timezone.utc
    ).strftime(
        "%Y%m%dT%H%M%SZ"
    )


def canonical_bytes(
    value: Any,
) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def digest(
    value: Any,
) -> str:
    return hashlib.sha256(
        canonical_bytes(
            value
        )
    ).hexdigest()


def deterministic_projection(
    value: Any,
) -> Any:
    if isinstance(
        value,
        dict,
    ):
        return {
            key: deterministic_projection(
                child
            )
            for key, child in sorted(
                value.items(),
                key=lambda item: item[
                    0
                ],
            )
            if key
            not in VOLATILE_FIELDS
        }

    if isinstance(
        value,
        list,
    ):
        return [
            deterministic_projection(
                child
            )
            for child in value
        ]

    if isinstance(
        value,
        tuple,
    ):
        return tuple(
            deterministic_projection(
                child
            )
            for child in value
        )

    return value


def load_json(
    path: Path,
) -> dict[str, Any]:
    value = json.loads(
        path.read_text(
            encoding="utf-8",
        )
    )

    if not isinstance(
        value,
        dict,
    ):
        raise ValueError(
            f"Expected JSON object: {path}"
        )

    return value


def graph_digest(
    path: Path = GRAPH_PATH,
) -> str:
    return digest(
        deterministic_projection(
            load_json(
                path
            )
        )
    )


def atomic_write_text(
    path: Path,
    value: str,
    mode: int = 0o644,
) -> None:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    descriptor, temporary_name = tempfile.mkstemp(
        prefix=(
            f".{path.name}."
        ),
        suffix=".tmp",
        dir=str(
            path.parent
        ),
    )

    temporary_path = Path(
        temporary_name
    )

    try:
        with os.fdopen(
            descriptor,
            "w",
            encoding="utf-8",
        ) as handle:
            handle.write(
                value
            )

            handle.flush()

            os.fsync(
                handle.fileno()
            )

        os.chmod(
            temporary_path,
            mode,
        )

        os.replace(
            temporary_path,
            path,
        )

    finally:
        if temporary_path.exists():
            temporary_path.unlink()


def atomic_write_json(
    path: Path,
    value: Any,
    mode: int = 0o644,
) -> None:
    atomic_write_text(
        path,
        json.dumps(
            value,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        mode=mode,
    )


def relative_path(
    path: Path,
) -> str:
    try:
        return path.relative_to(
            ROOT
        ).as_posix()

    except ValueError:
        return str(
            path
        )
