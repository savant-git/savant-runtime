from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
import fcntl
import getpass
import hashlib
import json
import os
from pathlib import Path
import re
import socket
import subprocess
import tempfile
from typing import Any, Iterator, Mapping


CHUNK_SIZE = 1024 * 1024


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace(
        "+00:00", "Z"
    )


def now_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def now_filename_date() -> str:
    return datetime.now(timezone.utc).strftime("%m%d%y")


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def stable_hash(value: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(CHUNK_SIZE), b""):
            digest.update(chunk)
    return digest.hexdigest()


def atomic_write_text(path: Path, text: str, mode: int = 0o600) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent)
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temporary, mode)
        os.replace(temporary, path)
        directory_fd = os.open(path.parent, os.O_DIRECTORY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    finally:
        if temporary.exists():
            temporary.unlink()


def atomic_write_json(path: Path, value: Mapping[str, Any], mode: int = 0o600) -> None:
    atomic_write_text(
        path,
        json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        mode=mode,
    )


def safe_slug(value: str, limit: int = 100) -> str:
    normalized = re.sub(r"[^A-Za-z0-9._-]+", "-", value.strip()).strip("-._")
    return (normalized or "target")[:limit]


def human_bytes(value: int) -> str:
    size = float(value)
    for unit in ("B", "KiB", "MiB", "GiB", "TiB"):
        if size < 1024.0 or unit == "TiB":
            return f"{size:.2f} {unit}"
        size /= 1024.0
    return f"{value} B"


def is_within(path: Path, root: Path) -> bool:
    path = path.resolve(strict=False)
    root = root.resolve(strict=False)
    return path == root or root in path.parents


def load_env_file(path: Path) -> None:
    if not path.is_file():
        return
    for raw_line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if value and value[:1] == value[-1:] and value[0] in {"'", '"'}:
            value = value[1:-1]
        if key:
            os.environ.setdefault(key, value)


def load_environment(runtime_root: Path) -> None:
    configured = os.environ.get("SDUMP_ENV_FILE")
    candidates = [
        Path(configured).expanduser() if configured else None,
        Path("/root/.env"),
        runtime_root / ".env",
        Path.home() / ".env",
        Path.home() / ".config" / "savant" / ".env",
    ]
    seen: set[Path] = set()
    for candidate in candidates:
        if candidate is None:
            continue
        resolved = candidate.resolve(strict=False)
        if resolved in seen:
            continue
        seen.add(resolved)
        load_env_file(candidate)


def runtime_root() -> Path:
    candidates = [
        os.environ.get("SAVANT_RUNTIME"),
        os.environ.get("SAVANT_ROOT"),
        "/root/savant-runtime",
        str(Path.home() / "savant-runtime"),
    ]
    for candidate in candidates:
        if not candidate:
            continue
        path = Path(candidate).expanduser().resolve(strict=False)
        if path.exists():
            return path
    return Path("/root/savant-runtime").resolve(strict=False)


def host_metadata() -> dict[str, Any]:
    return {
        "hostname": socket.gethostname(),
        "user": getpass.getuser(),
        "pid": os.getpid(),
        "python": os.sys.version.split()[0],
        "platform": os.uname().sysname + " " + os.uname().release,
    }


def git_info(target: Path) -> dict[str, Any] | None:
    probe = target if target.is_dir() else target.parent
    try:
        root = subprocess.check_output(
            ["git", "-C", str(probe), "rev-parse", "--show-toplevel"],
            stderr=subprocess.DEVNULL,
            text=True,
        ).strip()
        branch = subprocess.check_output(
            ["git", "-C", str(probe), "branch", "--show-current"],
            stderr=subprocess.DEVNULL,
            text=True,
        ).strip()
        commit = subprocess.check_output(
            ["git", "-C", str(probe), "rev-parse", "HEAD"],
            stderr=subprocess.DEVNULL,
            text=True,
        ).strip()
        dirty = (
            subprocess.call(
                ["git", "-C", str(probe), "diff", "--quiet"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            != 0
        )
        return {
            "root": root,
            "branch": branch,
            "commit": commit,
            "dirty": dirty,
        }
    except Exception:
        return None


@contextmanager
def exclusive_lock(path: Path) -> Iterator[None]:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a+", encoding="utf-8") as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
