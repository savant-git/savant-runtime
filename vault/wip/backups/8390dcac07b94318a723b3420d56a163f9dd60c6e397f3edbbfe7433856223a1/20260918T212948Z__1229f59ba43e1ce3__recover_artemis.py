#!/usr/bin/env python3

import hashlib
import json
import os
import shutil
from pathlib import Path


RECEIPT_ROOT = Path("/root/savant-runtime/vault/wip/receipts")
ARTEMIS_ROOT = Path("/artemis")
PRESERVED_ROOT = Path("/root/artemis-recovery-preserved")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)

    return digest.hexdigest()


def collect_latest_backups():
    latest = {}
    receipt_count = 0

    for receipt in sorted(RECEIPT_ROOT.glob("*.json")):
        try:
            data = json.loads(receipt.read_text(encoding="utf-8"))
        except Exception:
            continue

        path = data.get("resolved_path") or data.get("path")
        backup = data.get("backup")
        timestamp = data.get("timestamp", "")

        if not isinstance(path, str):
            continue

        if not (
            path == "/artemis"
            or path.startswith("/artemis/")
        ):
            continue

        if data.get("restorable") is not True:
            continue

        if not isinstance(backup, str):
            continue

        source = Path(backup)

        if not source.is_file():
            continue

        receipt_count += 1

        candidate = {
            "timestamp": timestamp,
            "backup": source,
            "sha256": data.get("source_sha256"),
            "mode": data.get("source_mode"),
            "receipt": receipt,
        }

        previous = latest.get(path)

        if previous is None or timestamp > previous["timestamp"]:
            latest[path] = candidate

    return latest, receipt_count


def preserve_current_tree():
    if not ARTEMIS_ROOT.exists():
        return False

    if PRESERVED_ROOT.exists():
        shutil.rmtree(PRESERVED_ROOT)

    shutil.copytree(
        ARTEMIS_ROOT,
        PRESERVED_ROOT,
        symlinks=True,
        ignore_dangling_symlinks=True,
    )

    return True


def restore(latest):
    restored = []
    failures = []

    for destination_text, record in sorted(latest.items()):
        destination = Path(destination_text)
        source = record["backup"]

        try:
            expected_sha = record["sha256"]
            source_sha = sha256_file(source)

            if expected_sha and source_sha != expected_sha:
                failures.append(
                    {
                        "path": str(destination),
                        "reason": "backup checksum mismatch",
                        "expected": expected_sha,
                        "actual": source_sha,
                        "backup": str(source),
                    }
                )
                continue

            destination.parent.mkdir(
                parents=True,
                exist_ok=True,
            )

            shutil.copy2(
                source,
                destination,
            )

            mode = record["mode"]

            if isinstance(mode, int):
                os.chmod(destination, mode)

            restored_sha = sha256_file(destination)

            if restored_sha != source_sha:
                failures.append(
                    {
                        "path": str(destination),
                        "reason": "post-restore checksum mismatch",
                        "expected": source_sha,
                        "actual": restored_sha,
                        "backup": str(source),
                    }
                )
                continue

            restored.append(
                {
                    "path": str(destination),
                    "timestamp": record["timestamp"],
                    "backup": str(source),
                    "receipt": str(record["receipt"]),
                    "sha256": restored_sha,
                }
            )

        except Exception as exc:
            failures.append(
                {
                    "path": str(destination),
                    "reason": str(exc),
                    "backup": str(source),
                }
            )

    return restored, failures


def print_tree():
    print()
    print("RECOVERED ARTEMIS TREE")
    print("======================")

    if not ARTEMIS_ROOT.exists():
        print("/artemis does not exist")
        return

    files = sorted(
        path
        for path in ARTEMIS_ROOT.rglob("*")
        if path.is_file()
    )

    for path in files:
        print(path)


def print_npm_scripts():
    package_path = ARTEMIS_ROOT / "package.json"

    print()
    print("NPM SCRIPTS")
    print("===========")

    if not package_path.is_file():
        print("package.json was not recovered")
        return

    try:
        package = json.loads(
            package_path.read_text(encoding="utf-8")
        )
    except Exception as exc:
        print(f"unable to read package.json: {exc}")
        return

    scripts = package.get("scripts", {})

    if not scripts:
        print("no npm scripts declared")
        return

    for name, command in scripts.items():
        print(f"{name}: {command}")


def main():
    latest, receipt_count = collect_latest_backups()

    if not latest:
        raise SystemExit(
            "ERROR: no restorable /artemis backups were found."
        )

    preserved = preserve_current_tree()

    restored, failures = restore(latest)

    print()
    print("ARTEMIS RECOVERY")
    print("================")
    print(f"restorable receipts examined: {receipt_count}")
    print(f"unique recoverable paths:     {len(latest)}")
    print(f"successfully restored:        {len(restored)}")
    print(f"failures:                     {len(failures)}")

    if preserved:
        print(
            "pre-recovery tree preserved at: "
            f"{PRESERVED_ROOT}"
        )
    else:
        print(
            "no existing /artemis tree required preservation"
        )

    print()
    print("RESTORED FILES")
    print("==============")

    for item in restored:
        print(item["path"])
        print(f"  version: {item['timestamp']}")
        print(f"  backup:  {item['backup']}")
        print(f"  receipt: {item['receipt']}")
        print(f"  sha256:  {item['sha256']}")

    if failures:
        print()
        print("FAILURES")
        print("========")

        for failure in failures:
            print(json.dumps(failure, indent=2))

    print_tree()
    print_npm_scripts()

    if failures:
        raise SystemExit(1)

    print()
    print(
        "Recovery completed successfully for every "
        "restorable Artemis path represented in the WIP receipts."
    )


if __name__ == "__main__":
    main()
