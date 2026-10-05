#!/usr/bin/env python3

from __future__ import annotations

import fcntl
import json
import os
import pty
import re
import select
import signal
import struct
import termios
import threading
import time
import uuid
from collections import deque
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import parse_qs, urlparse


bind_host = "127.0.0.1"
bind_port = int(os.getenv("PALAVER_TERMINAL_PORT", "8788"))

default_cwd = "/root/savant-runtime"
default_shell = os.getenv("SHELL", "/bin/bash")

max_body_bytes = 1024 * 1024
max_output_chunks = 4096
idle_timeout_seconds = 14400

loopback_origin = re.compile(
    r"^https?://(?:127\.0\.0\.1|localhost)(?::\d+)?$"
)


class terminal_session:
    def __init__(
        self,
        *,
        cwd: str = default_cwd,
        cols: int = 120,
        rows: int = 34,
    ) -> None:
        self.id = uuid.uuid4().hex
        self.cwd = cwd
        self.cols = max(20, min(int(cols), 500))
        self.rows = max(5, min(int(rows), 200))
        self.created_at = time.time()
        self.last_activity_at = self.created_at
        self.closed = False
        self.exit_code: int | None = None
        self.sequence = 0
        self.output: deque[tuple[int, str]] = deque(
            maxlen=max_output_chunks
        )
        self.lock = threading.RLock()

        pid, master_fd = pty.fork()

        if pid == 0:
            try:
                os.chdir(self.cwd)
            except OSError:
                os.chdir(default_cwd)

            environment = dict(os.environ)
            environment["TERM"] = "xterm-256color"
            environment["COLORTERM"] = "truecolor"
            environment["PALAVER_TERMINAL"] = "1"

            os.execvpe(
                default_shell,
                [default_shell, "-l"],
                environment,
            )

        self.pid = pid
        self.master_fd = master_fd

        os.set_blocking(
            self.master_fd,
            False,
        )

        self.resize(
            self.cols,
            self.rows,
        )

        self.reader = threading.Thread(
            target=self._read_loop,
            name=f"palaver-terminal-{self.id}",
            daemon=True,
        )
        self.reader.start()

    def _append_output(
        self,
        text: str,
    ) -> None:
        with self.lock:
            self.sequence += 1
            self.output.append(
                (
                    self.sequence,
                    text,
                )
            )
            self.last_activity_at = time.time()

    def _read_loop(self) -> None:
        while not self.closed:
            try:
                ready, _, _ = select.select(
                    [self.master_fd],
                    [],
                    [],
                    0.25,
                )

                if not ready:
                    self._refresh_process()
                    continue

                data = os.read(
                    self.master_fd,
                    65536,
                )

                if not data:
                    break

                self._append_output(
                    data.decode(
                        "utf-8",
                        errors="replace",
                    )
                )

            except BlockingIOError:
                continue
            except OSError:
                break

        self._refresh_process(
            force=True
        )

    def _refresh_process(
        self,
        *,
        force: bool = False,
    ) -> None:
        if self.closed and not force:
            return

        try:
            pid, status = os.waitpid(
                self.pid,
                os.WNOHANG,
            )
        except ChildProcessError:
            self.closed = True
            return

        if pid == 0:
            return

        if os.WIFEXITED(status):
            self.exit_code = os.WEXITSTATUS(
                status
            )
        elif os.WIFSIGNALED(status):
            self.exit_code = (
                128
                + os.WTERMSIG(status)
            )

        self.closed = True

    def write(
        self,
        data: str,
    ) -> None:
        if self.closed:
            raise RuntimeError(
                "terminal session is closed"
            )

        encoded = data.encode(
            "utf-8"
        )

        os.write(
            self.master_fd,
            encoded,
        )

        self.last_activity_at = time.time()

    def resize(
        self,
        cols: int,
        rows: int,
    ) -> None:
        if self.closed:
            return

        self.cols = max(
            20,
            min(int(cols), 500),
        )
        self.rows = max(
            5,
            min(int(rows), 200),
        )

        winsize = struct.pack(
            "HHHH",
            self.rows,
            self.cols,
            0,
            0,
        )

        fcntl.ioctl(
            self.master_fd,
            termios.TIOCSWINSZ,
            winsize,
        )

        self.last_activity_at = time.time()

    def read_since(
        self,
        cursor: int,
    ) -> dict[str, Any]:
        self._refresh_process()

        with self.lock:
            chunks = [
                {
                    "sequence": sequence,
                    "data": data,
                }
                for sequence, data
                in self.output
                if sequence > cursor
            ]

            return {
                "id": self.id,
                "cursor": self.sequence,
                "chunks": chunks,
                "closed": self.closed,
                "exit_code": self.exit_code,
                "cwd": self.cwd,
                "cols": self.cols,
                "rows": self.rows,
                "pid": self.pid,
            }

    def close(self) -> None:
        if self.closed:
            return

        self.closed = True

        try:
            os.kill(
                self.pid,
                signal.SIGHUP,
            )
        except ProcessLookupError:
            pass

        try:
            os.close(
                self.master_fd
            )
        except OSError:
            pass


sessions: dict[
    str,
    terminal_session,
] = {}

sessions_lock = threading.RLock()


def session_get(
    session_id: str,
) -> terminal_session | None:
    with sessions_lock:
        return sessions.get(
            session_id
        )


def session_create(
    *,
    cwd: str,
    cols: int,
    rows: int,
) -> terminal_session:
    candidate = os.path.abspath(
        cwd or default_cwd
    )

    if not os.path.isdir(
        candidate
    ):
        candidate = default_cwd

    session = terminal_session(
        cwd=candidate,
        cols=cols,
        rows=rows,
    )

    with sessions_lock:
        sessions[
            session.id
        ] = session

    return session


def session_close(
    session_id: str,
) -> bool:
    with sessions_lock:
        session = sessions.pop(
            session_id,
            None,
        )

    if session is None:
        return False

    session.close()
    return True


def cleanup_loop() -> None:
    while True:
        time.sleep(60)

        cutoff = (
            time.time()
            - idle_timeout_seconds
        )

        with sessions_lock:
            stale = [
                session_id
                for session_id, session
                in sessions.items()
                if (
                    session.closed
                    or session.last_activity_at
                    < cutoff
                )
            ]

        for session_id in stale:
            session_close(
                session_id
            )


class handler(
    BaseHTTPRequestHandler
):
    server_version = (
        "palaver-terminal/1.0"
    )

    def log_message(
        self,
        format: str,
        *args: Any,
    ) -> None:
        return

    def _origin_allowed(
        self,
    ) -> bool:
        origin = self.headers.get(
            "Origin",
            "",
        ).strip()

        if not origin:
            return True

        return bool(
            loopback_origin.fullmatch(
                origin
            )
        )

    def _headers(
        self,
        status: int = 200,
    ) -> None:
        self.send_response(
            status
        )

        origin = self.headers.get(
            "Origin",
            "",
        ).strip()

        if (
            origin
            and loopback_origin.fullmatch(
                origin
            )
        ):
            self.send_header(
                "Access-Control-Allow-Origin",
                origin,
            )
            self.send_header(
                "Vary",
                "Origin",
            )

        self.send_header(
            "Access-Control-Allow-Headers",
            "Content-Type",
        )
        self.send_header(
            "Access-Control-Allow-Methods",
            "GET, POST, OPTIONS",
        )
        self.send_header(
            "Cache-Control",
            "no-store",
        )
        self.send_header(
            "Content-Type",
            "application/json; charset=utf-8",
        )

    def _json(
        self,
        payload: dict[str, Any],
        status: int = 200,
    ) -> None:
        encoded = json.dumps(
            payload,
            separators=(",", ":"),
        ).encode(
            "utf-8"
        )

        self._headers(
            status
        )
        self.send_header(
            "Content-Length",
            str(len(encoded)),
        )
        self.end_headers()
        self.wfile.write(
            encoded
        )

    def _body(
        self,
    ) -> dict[str, Any]:
        length = int(
            self.headers.get(
                "Content-Length",
                "0",
            )
        )

        if (
            length < 0
            or length > max_body_bytes
        ):
            raise ValueError(
                "invalid request size"
            )

        if not length:
            return {}

        value = json.loads(
            self.rfile.read(
                length
            ).decode(
                "utf-8"
            )
        )

        if not isinstance(
            value,
            dict,
        ):
            raise ValueError(
                "request body must be an object"
            )

        return value

    def do_OPTIONS(
        self,
    ) -> None:
        if not self._origin_allowed():
            self._json(
                {
                    "ok": False,
                    "error": "origin rejected",
                },
                403,
            )
            return

        self._headers(
            204
        )
        self.end_headers()

    def do_GET(
        self,
    ) -> None:
        if not self._origin_allowed():
            self._json(
                {
                    "ok": False,
                    "error": "origin rejected",
                },
                403,
            )
            return

        parsed = urlparse(
            self.path
        )
        path = parsed.path
        query = parse_qs(
            parsed.query
        )

        if path == "/api/terminal/health":
            self._json(
                {
                    "ok": True,
                    "owner": "palaver",
                    "transport": "pty-http",
                    "bind_host": bind_host,
                    "session_count": len(
                        sessions
                    ),
                }
            )
            return

        if path == "/api/terminal/read":
            session_id = (
                query.get(
                    "id",
                    [""],
                )[0]
            )

            cursor_raw = (
                query.get(
                    "cursor",
                    ["0"],
                )[0]
            )

            try:
                cursor = int(
                    cursor_raw
                )
            except ValueError:
                cursor = 0

            session = session_get(
                session_id
            )

            if session is None:
                self._json(
                    {
                        "ok": False,
                        "error": (
                            "terminal session "
                            "not found"
                        ),
                    },
                    404,
                )
                return

            self._json(
                {
                    "ok": True,
                    **session.read_since(
                        cursor
                    ),
                }
            )
            return

        self._json(
            {
                "ok": False,
                "error": "not found",
            },
            404,
        )

    def do_POST(
        self,
    ) -> None:
        if not self._origin_allowed():
            self._json(
                {
                    "ok": False,
                    "error": "origin rejected",
                },
                403,
            )
            return

        parsed = urlparse(
            self.path
        )
        path = parsed.path

        try:
            body = self._body()
        except (
            ValueError,
            json.JSONDecodeError,
        ) as exc:
            self._json(
                {
                    "ok": False,
                    "error": str(exc),
                },
                400,
            )
            return

        if path == "/api/terminal/session":
            session = session_create(
                cwd=str(
                    body.get(
                        "cwd",
                        default_cwd,
                    )
                ),
                cols=int(
                    body.get(
                        "cols",
                        120,
                    )
                ),
                rows=int(
                    body.get(
                        "rows",
                        34,
                    )
                ),
            )

            self._json(
                {
                    "ok": True,
                    "id": session.id,
                    "pid": session.pid,
                    "cwd": session.cwd,
                    "owner": "palaver",
                    "command_authority": (
                        "human_operator"
                    ),
                }
            )
            return

        session_id = str(
            body.get(
                "id",
                "",
            )
        )

        session = session_get(
            session_id
        )

        if path == "/api/terminal/close":
            self._json(
                {
                    "ok": session_close(
                        session_id
                    ),
                }
            )
            return

        if session is None:
            self._json(
                {
                    "ok": False,
                    "error": (
                        "terminal session "
                        "not found"
                    ),
                },
                404,
            )
            return

        if path == "/api/terminal/input":
            data = body.get(
                "data",
                "",
            )

            if not isinstance(
                data,
                str,
            ):
                self._json(
                    {
                        "ok": False,
                        "error": (
                            "terminal input "
                            "must be text"
                        ),
                    },
                    400,
                )
                return

            session.write(
                data
            )

            self._json(
                {
                    "ok": True,
                }
            )
            return

        if path == "/api/terminal/resize":
            session.resize(
                int(
                    body.get(
                        "cols",
                        session.cols,
                    )
                ),
                int(
                    body.get(
                        "rows",
                        session.rows,
                    )
                ),
            )

            self._json(
                {
                    "ok": True,
                    "cols": session.cols,
                    "rows": session.rows,
                }
            )
            return

        self._json(
            {
                "ok": False,
                "error": "not found",
            },
            404,
        )


def main() -> None:
    cleanup = threading.Thread(
        target=cleanup_loop,
        name="palaver-terminal-cleanup",
        daemon=True,
    )
    cleanup.start()

    print(
        f"Palaver terminal bridge: "
        f"http://{bind_host}:{bind_port}"
    )

    ThreadingHTTPServer(
        (
            bind_host,
            bind_port,
        ),
        handler,
    ).serve_forever()


if __name__ == "__main__":
    main()
