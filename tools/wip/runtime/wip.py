#!/usr/bin/env python3

from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys
import tempfile
import time
from typing import Any


program = "wip"
version = "2.0.0"

real_nano = Path("/usr/bin/nano")

runtime_root = Path("/root/savant-runtime")
vault_root = runtime_root / "vault" / "wip"
backup_root = vault_root / "backups"
receipt_root = vault_root / "receipts"
lock_root = vault_root / "locks"

sensitive_suffixes = {
    ".pem",
    ".key",
    ".p12",
    ".pfx",
}

sensitive_names = {
    ".env",
    "credentials",
    "credentials.json",
    "id_rsa",
    "id_ed25519",
}

authority_markers = (
    "/authority/",
    "/canon/",
    "/canon-system/",
    "/decisions/",
)

binary_sample_size = 65536
backup_retention_per_file = 25


def now_stamp() -> str:
    return time.strftime(
        "%Y%m%dT%H%M%SZ",
        time.gmtime(),
    )


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as handle:
        while True:
            chunk = handle.read(1024 * 1024)

            if not chunk:
                break

            digest.update(chunk)

    return digest.hexdigest()


def atomic_json(
    path: Path,
    payload: dict[str, Any],
) -> None:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    descriptor, name = tempfile.mkstemp(
        prefix=f".{path.name}.",
        dir=str(path.parent),
    )

    temporary = Path(name)

    try:
        with os.fdopen(
            descriptor,
            "w",
            encoding="utf-8",
        ) as handle:
            json.dump(
                payload,
                handle,
                ensure_ascii=False,
                sort_keys=True,
                indent=2,
            )

            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())

        os.chmod(
            temporary,
            0o600,
        )

        os.replace(
            temporary,
            path,
        )

    finally:
        if temporary.exists():
            temporary.unlink()


def append_receipt(
    payload: dict[str, Any],
) -> Path:
    receipt_root.mkdir(
        parents=True,
        exist_ok=True,
    )

    identity = hashlib.sha256(
        json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()[:16]

    path = receipt_root / (
        f"{now_stamp()}__"
        f"{identity}.json"
    )

    atomic_json(
        path,
        payload,
    )

    return path


def is_binary(path: Path) -> bool:
    try:
        with path.open("rb") as handle:
            sample = handle.read(
                binary_sample_size
            )

    except OSError:
        return False

    if not sample:
        return False

    return b"\x00" in sample


def display_path(path: Path) -> str:
    try:
        return str(
            path.resolve(
                strict=False
            )
        )

    except OSError:
        return str(path)


def authority_sensitive(path: Path) -> bool:
    value = (
        "/"
        + str(
            path.resolve(
                strict=False
            )
        ).strip("/")
        + "/"
    ).casefold()

    return any(
        marker in value
        for marker in authority_markers
    )


def secret_sensitive(path: Path) -> bool:
    return (
        path.name.casefold()
        in sensitive_names
        or path.suffix.casefold()
        in sensitive_suffixes
    )


def human_size(size: int) -> str:
    value = float(size)

    for unit in (
        "b",
        "kib",
        "mib",
        "gib",
        "tib",
    ):
        if value < 1024.0:
            return f"{value:.2f} {unit}"

        value /= 1024.0

    return f"{value:.2f} pib"


def preview(
    path: Path,
    lines: int = 12,
) -> None:
    if is_binary(path):
        print(
            "wip: preview unavailable "
            "(binary content)"
        )
        return

    try:
        content = path.read_text(
            encoding="utf-8",
            errors="replace",
        ).splitlines()

    except OSError:
        return

    if not content:
        return

    print("--- preview ---")

    for line in content[:lines]:
        print(line[:240])

    if len(content) > lines:
        print(
            f"... {len(content) - lines} "
            "additional lines"
        )

    print("--- end preview ---")


def git_context(path: Path) -> dict[str, Any]:
    directory = (
        path.parent
        if path.parent.exists()
        else Path.cwd()
    )

    try:
        root = subprocess.run(
            [
                "git",
                "-C",
                str(directory),
                "rev-parse",
                "--show-toplevel",
            ],
            capture_output=True,
            text=True,
            check=False,
            timeout=2,
        )

    except Exception:
        return {
            "repository": False,
        }

    if root.returncode != 0:
        return {
            "repository": False,
        }

    repository = Path(
        root.stdout.strip()
    )

    try:
        relative = path.resolve(
            strict=False
        ).relative_to(
            repository.resolve()
        )

    except ValueError:
        return {
            "repository": True,
            "root": str(repository),
            "tracked": False,
        }

    tracked = subprocess.run(
        [
            "git",
            "-C",
            str(repository),
            "ls-files",
            "--error-unmatch",
            str(relative),
        ],
        capture_output=True,
        text=True,
        check=False,
        timeout=2,
    )

    dirty = subprocess.run(
        [
            "git",
            "-C",
            str(repository),
            "status",
            "--porcelain",
            "--",
            str(relative),
        ],
        capture_output=True,
        text=True,
        check=False,
        timeout=2,
    )

    return {
        "repository": True,
        "root": str(repository),
        "tracked":
            tracked.returncode == 0,
        "dirty":
            bool(
                dirty.stdout.strip()
            ),
    }


def lock_for(path: Path) -> int:
    lock_root.mkdir(
        parents=True,
        exist_ok=True,
    )

    identity = hashlib.sha256(
        str(
            path.resolve(
                strict=False
            )
        ).encode("utf-8")
    ).hexdigest()

    lock_path = (
        lock_root
        / f"{identity}.lock"
    )

    descriptor = os.open(
        lock_path,
        os.O_CREAT | os.O_RDWR,
        0o600,
    )

    try:
        fcntl.flock(
            descriptor,
            fcntl.LOCK_EX
            | fcntl.LOCK_NB,
        )

    except BlockingIOError as error:
        os.close(descriptor)

        raise RuntimeError(
            "another wip operation "
            "already owns this file"
        ) from error

    return descriptor


def backup_directory(path: Path) -> Path:
    identity = hashlib.sha256(
        str(
            path.resolve(
                strict=False
            )
        ).encode("utf-8")
    ).hexdigest()

    return backup_root / identity


def create_backup(
    path: Path,
) -> tuple[Path, str]:
    directory = backup_directory(
        path
    )

    directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    source_hash = sha256_file(
        path
    )

    destination = directory / (
        f"{now_stamp()}__"
        f"{source_hash[:16]}__"
        f"{path.name}"
    )

    shutil.copy2(
        path,
        destination,
        follow_symlinks=True,
    )

    return (
        destination,
        source_hash,
    )


def prune_backups(path: Path) -> None:
    directory = backup_directory(
        path
    )

    if not directory.is_dir():
        return

    backups = sorted(
        (
            candidate
            for candidate
            in directory.iterdir()
            if candidate.is_file()
        ),
        key=lambda candidate:
            candidate.stat().st_mtime_ns,
        reverse=True,
    )

    for candidate in backups[
        backup_retention_per_file:
    ]:
        try:
            candidate.unlink()

        except OSError:
            pass


def wipe_regular_file(
    path: Path,
) -> dict[str, Any]:
    before = path.stat()

    backup, before_hash = (
        create_backup(
            path
        )
    )

    with path.open(
        "r+b"
    ) as handle:
        handle.truncate(0)
        handle.flush()
        os.fsync(
            handle.fileno()
        )

    after = path.stat()

    prune_backups(path)

    receipt = {
        "schema":
            "savant.wip.wipe-receipt.v1",
        "projection_only":
            True,
        "authority_effect":
            "none",
        "operation":
            "wipe",
        "timestamp":
            now_stamp(),
        "path":
            str(path),
        "resolved_path":
            display_path(path),
        "source_sha256":
            before_hash,
        "source_size":
            before.st_size,
        "source_mode":
            stat.S_IMODE(
                before.st_mode
            ),
        "source_uid":
            before.st_uid,
        "source_gid":
            before.st_gid,
        "source_links":
            before.st_nlink,
        "backup":
            str(backup),
        "result_size":
            after.st_size,
        "restorable":
            True,
    }

    receipt_path = append_receipt(
        receipt
    )

    receipt["receipt"] = str(
        receipt_path
    )

    return receipt


def latest_backup(
    path: Path,
) -> Path | None:
    directory = backup_directory(
        path
    )

    if not directory.is_dir():
        return None

    backups = sorted(
        (
            candidate
            for candidate
            in directory.iterdir()
            if candidate.is_file()
        ),
        key=lambda candidate:
            candidate.stat().st_mtime_ns,
        reverse=True,
    )

    return (
        backups[0]
        if backups
        else None
    )


def restore_latest(path: Path) -> int:
    backup = latest_backup(
        path
    )

    if backup is None:
        print(
            "wip: no backup available",
            file=sys.stderr,
        )
        return 1

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    shutil.copy2(
        backup,
        path,
    )

    print(
        f"wip: restored {backup}"
    )

    return 0


def history(path: Path) -> int:
    directory = backup_directory(
        path
    )

    if not directory.is_dir():
        print("wip: no history")
        return 0

    backups = sorted(
        (
            candidate
            for candidate
            in directory.iterdir()
            if candidate.is_file()
        ),
        key=lambda candidate:
            candidate.stat().st_mtime_ns,
        reverse=True,
    )

    for backup in backups:
        print(str(backup))

    return 0


def prompt_wipe(path: Path) -> bool:
    metadata = path.stat()

    print()
    print(
        f"wip: {display_path(path)}"
    )
    print(
        f"size: {human_size(metadata.st_size)}"
    )
    print(
        "modified_ns: "
        f"{metadata.st_mtime_ns}"
    )

    if path.is_symlink():
        print(
            "warning: symbolic link"
        )
        print(
            f"target: {display_path(path)}"
        )

    if metadata.st_nlink > 1:
        print(
            "warning: file has "
            f"{metadata.st_nlink} hard links"
        )

    if authority_sensitive(path):
        print(
            "warning: authority/canon "
            "surface detected"
        )

    if secret_sensitive(path):
        print(
            "warning: sensitive filename "
            "detected"
        )

    context = git_context(path)

    if context.get("repository"):
        print(
            "git: "
            f"tracked={context.get('tracked')} "
            f"dirty={context.get('dirty')}"
        )

    preview(path)

    print()
    print(
        "wipe contents before editing?"
    )
    print(
        "[y] yes  [n] keep  "
        "[b] backup only  [q] abort"
    )

    while True:
        try:
            answer = input(
                "wip> "
            ).strip().casefold()

        except EOFError:
            return False

        if answer in {
            "",
            "n",
            "no",
        }:
            return False

        if answer in {
            "q",
            "quit",
            "abort",
        }:
            raise KeyboardInterrupt

        if answer in {
            "b",
            "backup",
        }:
            backup, _ = create_backup(
                path
            )

            prune_backups(path)

            print(
                f"wip: backup {backup}"
            )

            return False

        if answer in {
            "y",
            "yes",
        }:
            if is_binary(path):
                print(
                    "wip: binary file; "
                    "automatic wipe refused"
                )

                return False

            return True


def extract_simple_targets(
    arguments: list[str],
) -> list[Path]:
    if not arguments:
        return []

    if "--" in arguments:
        index = arguments.index("--")

        return [
            Path(value)
            for value
            in arguments[index + 1:]
        ]

    if any(
        value.startswith("-")
        for value
        in arguments
    ):
        return []

    return [
        Path(value)
        for value
        in arguments
    ]


def prepare_target(path: Path) -> None:
    if path.exists():
        return

    parent = path.parent

    if (
        parent != Path(".")
        and not parent.exists()
    ):
        parent.mkdir(
            parents=True,
            exist_ok=True,
        )


def process_target(path: Path) -> None:
    prepare_target(path)

    if not path.exists():
        return

    if path.is_dir():
        return

    if not path.is_file():
        return

    if path.stat().st_size == 0:
        return

    if not sys.stdin.isatty():
        return

    descriptor = lock_for(path)

    try:
        if prompt_wipe(path):
            receipt = wipe_regular_file(
                path
            )

            print(
                "wip: wiped; backup="
                f"{receipt['backup']}"
            )

    finally:
        os.close(descriptor)


def launch_nano(
    arguments: list[str],
) -> int:
    if not real_nano.is_file():
        print(
            "wip: real nano missing: "
            f"{real_nano}",
            file=sys.stderr,
        )
        return 127

    targets = extract_simple_targets(
        arguments
    )

    for target in targets:
        process_target(target)

    process = subprocess.run(
        [
            str(real_nano),
            *arguments,
        ],
        check=False,
    )

    return process.returncode


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser(
        prog=program,
        add_help=True,
    )

    value.add_argument(
        "--version",
        action="version",
        version=f"{program} {version}",
    )

    value.add_argument(
        "--history",
        metavar="FILE",
    )

    value.add_argument(
        "--restore",
        metavar="FILE",
    )

    value.add_argument(
        "--real-nano",
        action="store_true",
    )

    value.add_argument(
        "nano_arguments",
        nargs=argparse.REMAINDER,
    )

    return value


def main() -> int:
    arguments = parser().parse_args()

    vault_root.mkdir(
        parents=True,
        exist_ok=True,
    )

    os.chmod(
        vault_root,
        0o700,
    )

    if arguments.history:
        return history(
            Path(arguments.history)
        )

    if arguments.restore:
        return restore_latest(
            Path(arguments.restore)
        )

    if arguments.real_nano:
        return subprocess.run(
            [
                str(real_nano),
                *arguments.nano_arguments,
            ],
            check=False,
        ).returncode

    return launch_nano(
        arguments.nano_arguments
    )


if __name__ == "__main__":
    raise SystemExit(main())
