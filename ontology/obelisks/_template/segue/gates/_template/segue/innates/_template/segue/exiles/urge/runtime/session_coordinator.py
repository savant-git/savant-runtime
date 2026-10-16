
from __future__ import annotations

from copy import deepcopy
from threading import RLock, Thread
from typing import Any, Callable

from .iteration import engine, job
from .session_control import controller
from .session_execution import execute


schema = "savant://runtime/urge/session-coordinator/1.0.0"
owner = "exile:urge"


class session_coordinator_error(ValueError):
    pass


class coordinator:
    def __init__(
        self,
        *,
        max_sessions: int = 64,
    ) -> None:
        if (
            isinstance(max_sessions, bool)
            or not isinstance(max_sessions, int)
            or max_sessions < 1
        ):
            raise session_coordinator_error(
                "max_sessions must be a positive integer"
            )

        self._lock = RLock()
        self._max_sessions = max_sessions
        self._sessions: dict[str, dict[str, Any]] = {}

    def _entry(self, session_id: str) -> dict[str, Any]:
        if not isinstance(session_id, str):
            raise session_coordinator_error(
                "session_id must be a string"
            )

        entry = self._sessions.get(session_id)

        if entry is None:
            raise session_coordinator_error(
                "unknown session"
            )

        return entry

    def start(
        self,
        *,
        session_id: str,
        work: job,
        runner: engine,
        initial_payload: Any = None,
        on_iteration: Callable[..., Any] | None = None,
    ) -> dict[str, Any]:
        if (
            not isinstance(session_id, str)
            or not session_id.strip()
            or session_id != session_id.strip()
        ):
            raise session_coordinator_error(
                "session_id must be a nonempty canonical string"
            )

        if not isinstance(work, job):
            raise session_coordinator_error(
                "work must be an urge job"
            )

        if not isinstance(runner, engine):
            raise session_coordinator_error(
                "runner must be an urge engine"
            )

        if (
            on_iteration is not None
            and not callable(on_iteration)
        ):
            raise session_coordinator_error(
                "on_iteration must be callable"
            )

        with self._lock:
            if session_id in self._sessions:
                raise session_coordinator_error(
                    "session identity already exists"
                )

            if len(self._sessions) >= self._max_sessions:
                raise session_coordinator_error(
                    "session capacity reached"
                )

            control = controller()

            entry: dict[str, Any] = {
                "id": session_id,
                "control": control,
                "result": None,
                "error": None,
                "iterations": [],
                "finished": False,
                "thread": None,
            }

            self._sessions[session_id] = entry

            def observe(value: Any) -> None:
                with self._lock:
                    entry["iterations"].append(
                        deepcopy(value)
                    )

                if on_iteration is not None:
                    on_iteration(deepcopy(value))

            def run() -> None:
                try:
                    result = execute(
                        message_id=session_id,
                        work=work,
                        runner=runner,
                        initial_payload=initial_payload,
                        on_iteration=observe,
                        control=control,
                    )

                    with self._lock:
                        entry["result"] = deepcopy(result)

                except BaseException as exc:
                    with self._lock:
                        entry["error"] = {
                            "type": type(exc).__name__,
                            "message": str(exc),
                        }

                finally:
                    with self._lock:
                        entry["finished"] = True

            thread = Thread(
                target=run,
                name=f"urge-session-{session_id}",
                daemon=True,
            )

            entry["thread"] = thread

            try:
                thread.start()
            except Exception:
                del self._sessions[session_id]
                raise

            return self._snapshot(entry)

    def _snapshot(
        self,
        entry: dict[str, Any],
    ) -> dict[str, Any]:
        control_state = entry["control"].projection()
        result = entry["result"]

        return {
            "schema": schema,
            "owner": owner,
            "session_id": entry["id"],
            "status": control_state["status"],
            "finished": entry["finished"],
            "control": deepcopy(control_state),
            "iterations": deepcopy(entry["iterations"]),
            "iteration_count": len(entry["iterations"]),
            "selected": (
                deepcopy(result.get("selected"))
                if isinstance(result, dict)
                else None
            ),
            "timeline": (
                deepcopy(result.get("timeline"))
                if isinstance(result, dict)
                else None
            ),
            "error": deepcopy(entry["error"]),
        }

    def snapshot(
        self,
        session_id: str,
    ) -> dict[str, Any]:
        with self._lock:
            return self._snapshot(
                self._entry(session_id)
            )

    def pause(
        self,
        session_id: str,
    ) -> dict[str, Any]:
        with self._lock:
            entry = self._entry(session_id)
            entry["control"].pause()
            return self._snapshot(entry)

    def resume(
        self,
        session_id: str,
    ) -> dict[str, Any]:
        with self._lock:
            entry = self._entry(session_id)
            entry["control"].resume()
            return self._snapshot(entry)

    def cancel(
        self,
        session_id: str,
    ) -> dict[str, Any]:
        with self._lock:
            entry = self._entry(session_id)
            entry["control"].cancel()
            return self._snapshot(entry)

    def wait(
        self,
        session_id: str,
        *,
        timeout: float | None = None,
    ) -> dict[str, Any]:
        with self._lock:
            entry = self._entry(session_id)
            thread = entry["thread"]

        if thread is None:
            raise session_coordinator_error(
                "session thread is unavailable"
            )

        thread.join(timeout=timeout)

        return self.snapshot(session_id)

    def release(
        self,
        session_id: str,
    ) -> None:
        with self._lock:
            entry = self._entry(session_id)

            if not entry["finished"]:
                raise session_coordinator_error(
                    "cannot release an active session"
                )

            del self._sessions[session_id]

    def sessions(self) -> list[str]:
        with self._lock:
            return sorted(self._sessions)
