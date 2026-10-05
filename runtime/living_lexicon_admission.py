from __future__ import annotations

import argparse
import hashlib
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from runtime.earmark_projection import earmark_projection_registry
from runtime.leveled_earmarks import leveled_earmark_registry
from runtime.living_lexicon import living_lexicon


runtime_root = Path("/root/savant-runtime")
state_root = runtime_root / "state" / "living-lexicon-admission"
registry_path = state_root / "registry.json"
history_path = state_root / "history.jsonl"

schema_id = "savant.living-lexicon-admission.v2"

excluded_top_level = {
    ".git",
    "audit",
    "backups",
}

excluded_names = {
    "__pycache__",
    "node_modules",
}

excluded_prefixes = (
    ".venv",
)

excluded_suffixes = (
    ".pyc",
    ".pyo",
    ".so",
    ".a",
    ".o",
    ".class",
    ".jar",
    ".zip",
    ".gz",
    ".zst",
    ".tar",
    ".tgz",
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".webp",
    ".ico",
    ".pdf",
    ".sqlite",
    ".sqlite3",
    ".db",
)

text_suffixes = {
    "",
    ".py",
    ".sh",
    ".md",
    ".txt",
    ".json",
    ".jsonl",
    ".yaml",
    ".yml",
    ".toml",
    ".ini",
    ".cfg",
    ".conf",
    ".service",
    ".socket",
    ".target",
    ".timer",
    ".path",
    ".html",
    ".css",
    ".scss",
    ".js",
    ".jsx",
    ".ts",
    ".tsx",
    ".mjs",
    ".cjs",
    ".sql",
    ".xml",
    ".svg",
}


class admission_error(RuntimeError):
    pass


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "z")


def canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def absolute_without_resolution(path: Path) -> Path:
    if path.is_absolute():
        return path

    return runtime_root / path


def relative_without_resolution(path: Path) -> str:
    absolute = absolute_without_resolution(path)

    try:
        return absolute.relative_to(runtime_root).as_posix()
    except ValueError as error:
        raise admission_error(
            f"path outside savant runtime: {absolute}"
        ) from error


def atomic_write(path: Path, payload: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    descriptor, temporary = tempfile.mkstemp(
        prefix=f".{path.name}.",
        suffix=".tmp",
        dir=str(path.parent),
    )

    temporary_path = Path(temporary)

    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())

        os.chmod(temporary_path, 0o600)
        os.replace(temporary_path, path)

        directory_descriptor = os.open(path.parent, os.O_DIRECTORY)

        try:
            os.fsync(directory_descriptor)
        finally:
            os.close(directory_descriptor)
    finally:
        if temporary_path.exists():
            temporary_path.unlink()


def append_history(record: dict[str, Any]) -> None:
    history_path.parent.mkdir(parents=True, exist_ok=True)

    with history_path.open("a", encoding="utf-8") as handle:
        handle.write(canonical_json(record))
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())

    os.chmod(history_path, 0o600)


def empty_registry() -> dict[str, Any]:
    return {
        "schema": schema_id,
        "version": 2,
        "files": {},
        "updated_at": None,
    }


def load_registry() -> dict[str, Any]:
    if not registry_path.exists():
        return empty_registry()

    with registry_path.open("r", encoding="utf-8") as handle:
        value = json.load(handle)

    schema = value.get("schema")

    if schema == "savant.living-lexicon-admission.v1":
        value["schema"] = schema_id
        value["version"] = 2
        return value

    if schema != schema_id:
        raise admission_error(
            f"unsupported admission registry schema: {schema!r}"
        )

    return value


def save_registry(registry: dict[str, Any]) -> None:
    registry["schema"] = schema_id
    registry["version"] = 2
    registry["updated_at"] = utc_now()

    atomic_write(
        registry_path,
        json.dumps(
            registry,
            ensure_ascii=False,
            sort_keys=True,
            indent=2,
        )
        + "\n",
    )


def relative_path(path: Path) -> str:
    return relative_without_resolution(path)


def path_has_symlink_component(path: Path) -> bool:
    absolute = absolute_without_resolution(path)

    try:
        relative = absolute.relative_to(runtime_root)
    except ValueError:
        return True

    cursor = runtime_root

    for part in relative.parts:
        cursor = cursor / part

        try:
            if cursor.is_symlink():
                return True
        except OSError:
            return True

    return False


def is_excluded(path: Path) -> bool:
    absolute = absolute_without_resolution(path)
    relative = relative_without_resolution(absolute)
    parts = Path(relative).parts

    if not parts:
        return True

    if path_has_symlink_component(absolute):
        return True

    if parts[0] in excluded_top_level:
        return True

    for part in parts:
        if part in excluded_names:
            return True

        if any(
            part.startswith(prefix)
            for prefix in excluded_prefixes
        ):
            return True

    suffix = absolute.suffix.lower()

    if suffix in excluded_suffixes:
        return True

    if suffix not in text_suffixes:
        return True

    if relative.startswith("vault/backups/"):
        return True

    return False


def read_text(path: Path) -> str | None:
    if path_has_symlink_component(path):
        return None

    try:
        raw = path.read_bytes()
    except (
        OSError,
        RuntimeError,
    ):
        return None

    if b"\x00" in raw:
        return None

    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        return None


class living_lexicon_admission:
    def __init__(self) -> None:
        self.lexicon = living_lexicon()
        self.earmarks = leveled_earmark_registry()
        self.projections = earmark_projection_registry()
        self.registry = load_registry()

    def historical_terms(self) -> dict[str, set[str]]:
        values: dict[str, set[str]] = {}

        for identity, record in self.earmarks.registry[
            "earmarks"
        ].items():
            if int(record["level"]) != 0:
                continue

            if record.get("namespace") != "terminology":
                continue

            bucket = values.setdefault(identity, set())

            resolved = self.earmarks.resolve(identity)

            if resolved.value:
                bucket.add(resolved.value)

            for revision in record.get("revisions", []):
                value = revision.get("value")

                if isinstance(value, str) and value:
                    bucket.add(value)

        return values

    def tokenize_template(
        self,
        text: str,
    ) -> tuple[str, list[str]]:
        historical = self.historical_terms()
        candidates: list[tuple[str, str]] = []

        for identity, values in historical.items():
            for value in values:
                candidates.append((value, identity))

        candidates.sort(
            key=lambda item: len(item[0]),
            reverse=True,
        )

        output = text
        dependencies: set[str] = set()

        for value, identity in candidates:
            marker = f"{{{{earmark:{identity}}}}}"

            if marker in output:
                dependencies.add(identity)
                continue

            start = 0
            pieces: list[str] = []

            while True:
                index = output.find(value, start)

                if index < 0:
                    pieces.append(output[start:])
                    break

                before = output[index - 1] if index > 0 else ""
                after_index = index + len(value)

                after = (
                    output[after_index]
                    if after_index < len(output)
                    else ""
                )

                left_boundary = not (
                    before.isalnum()
                    or before == "_"
                )

                right_boundary = not (
                    after.isalnum()
                    or after == "_"
                )

                if left_boundary and right_boundary:
                    pieces.append(output[start:index])
                    pieces.append(marker)
                    dependencies.add(identity)
                    start = after_index
                else:
                    pieces.append(output[start:after_index])
                    start = after_index

            output = "".join(pieces)

        return output, sorted(dependencies)

    def update_existing_projection(
        self,
        *,
        projection_identity: str,
        path: Path,
        template: str,
        dependencies: list[str],
    ) -> None:
        existing = self.projections.registry[
            "projections"
        ][projection_identity]

        if existing["target"] != str(path):
            raise admission_error(
                f"projection target conflict: {path}"
            )

        if existing["template"] == template:
            return

        old_dependencies = set(
            existing.get("dependencies", [])
        )
        new_dependencies = set(dependencies)

        for dependency in old_dependencies - new_dependencies:
            reverse = self.projections.registry[
                "dependencies"
            ].get(dependency, [])

            if projection_identity in reverse:
                reverse.remove(projection_identity)

            if not reverse:
                self.projections.registry[
                    "dependencies"
                ].pop(dependency, None)

        for dependency in new_dependencies:
            reverse = self.projections.registry[
                "dependencies"
            ].setdefault(dependency, [])

            if projection_identity not in reverse:
                reverse.append(projection_identity)
                reverse.sort()

        existing["template"] = template
        existing["template_sha256"] = sha256_text(template)
        existing["dependencies"] = dependencies
        existing["updated_at"] = utc_now()

        self.projections.save()

    def admit_file(self, path: Path) -> dict[str, Any]:
        path = absolute_without_resolution(path)

        relative = relative_without_resolution(path)

        if path_has_symlink_component(path):
            return {
                "path": str(path),
                "admitted": False,
                "reason": "symlink",
            }

        if not path.is_file():
            raise admission_error(f"not a file: {path}")

        if is_excluded(path):
            return {
                "path": str(path),
                "admitted": False,
                "reason": "excluded",
            }

        text = read_text(path)

        if text is None:
            return {
                "path": str(path),
                "admitted": False,
                "reason": "non-text",
            }

        template, dependencies = self.tokenize_template(text)

        if not dependencies:
            self.registry["files"][relative] = {
                "path": str(path),
                "source_sha256": sha256_text(text),
                "template_sha256": sha256_text(template),
                "dependencies": [],
                "projection": None,
                "admitted_at": utc_now(),
            }

            save_registry(self.registry)

            return {
                "path": str(path),
                "admitted": True,
                "managed": False,
                "dependencies": [],
            }

        projection_identity = (
            f"projection:{sha256_text(relative)}"
        )

        existing = self.projections.registry[
            "projections"
        ].get(projection_identity)

        if existing is None:
            self.projections.register(
                target=str(path),
                template=template,
                metadata={
                    "owner": "living-lexicon",
                    "admission": "automatic",
                    "source_path": relative,
                },
            )
        else:
            self.update_existing_projection(
                projection_identity=projection_identity,
                path=path,
                template=template,
                dependencies=dependencies,
            )

        self.registry["files"][relative] = {
            "path": str(path),
            "source_sha256": sha256_text(text),
            "template_sha256": sha256_text(template),
            "dependencies": dependencies,
            "projection": projection_identity,
            "admitted_at": utc_now(),
        }

        save_registry(self.registry)

        append_history(
            {
                "event": "file.admitted",
                "path": relative,
                "projection": projection_identity,
                "dependencies": dependencies,
                "timestamp": utc_now(),
            }
        )

        return {
            "path": str(path),
            "admitted": True,
            "managed": True,
            "projection": projection_identity,
            "dependencies": dependencies,
        }

    def reconcile(self) -> dict[str, Any]:
        admitted = 0
        managed = 0
        excluded = 0
        symlinks = 0
        non_text = 0
        failures: list[dict[str, str]] = []

        for root, directories, filenames in os.walk(
            runtime_root,
            topdown=True,
            followlinks=False,
        ):
            root_path = Path(root)
            retained_directories: list[str] = []

            for directory in directories:
                candidate = root_path / directory

                try:
                    if candidate.is_symlink():
                        symlinks += 1
                        continue

                    if is_excluded(candidate):
                        excluded += 1
                        continue

                    retained_directories.append(directory)

                except (
                    OSError,
                    RuntimeError,
                    admission_error,
                ):
                    excluded += 1

            directories[:] = retained_directories

            for filename in filenames:
                path = root_path / filename

                try:
                    if path.is_symlink():
                        symlinks += 1
                        continue

                    result = self.admit_file(path)

                except (
                    OSError,
                    RuntimeError,
                    UnicodeError,
                    admission_error,
                ) as error:
                    failures.append(
                        {
                            "path": str(path),
                            "error": str(error),
                        }
                    )
                    continue

                if result.get("admitted"):
                    admitted += 1

                    if result.get("managed"):
                        managed += 1

                elif result.get("reason") == "symlink":
                    symlinks += 1

                elif result.get("reason") == "excluded":
                    excluded += 1

                else:
                    non_text += 1

        append_history(
            {
                "event": "reconciliation.completed",
                "admitted": admitted,
                "managed": managed,
                "excluded": excluded,
                "symlinks": symlinks,
                "non_text": non_text,
                "failure_count": len(failures),
                "timestamp": utc_now(),
            }
        )

        return {
            "passed": not failures,
            "admitted": admitted,
            "managed": managed,
            "excluded": excluded,
            "symlinks": symlinks,
            "non_text": non_text,
            "failure_count": len(failures),
            "failures": failures,
        }

    def verify(self) -> dict[str, Any]:
        lexicon_result = self.lexicon.verify()
        failures = list(lexicon_result["failures"])

        for relative, record in self.registry[
            "files"
        ].items():
            path = Path(record["path"])

            if path_has_symlink_component(path):
                failures.append(
                    f"{relative}: admitted path became symlinked"
                )
                continue

            try:
                actual_relative = relative_path(path)
            except (
                OSError,
                RuntimeError,
                admission_error,
            ) as error:
                failures.append(
                    f"{relative}: invalid path: {error}"
                )
                continue

            if actual_relative != relative:
                failures.append(
                    f"{relative}: path identity mismatch"
                )

            projection = record.get("projection")

            if projection is None:
                continue

            projection_record = self.projections.registry[
                "projections"
            ].get(projection)

            if projection_record is None:
                failures.append(
                    f"{relative}: missing projection {projection}"
                )
                continue

            if projection_record["target"] != str(path):
                failures.append(
                    f"{relative}: projection target mismatch"
                )

            if sorted(
                projection_record.get("dependencies", [])
            ) != sorted(record.get("dependencies", [])):
                failures.append(
                    f"{relative}: dependency mismatch"
                )

        return {
            "schema": schema_id,
            "passed": not failures,
            "admitted_file_count": len(
                self.registry["files"]
            ),
            "managed_file_count": sum(
                1
                for record in self.registry["files"].values()
                if record.get("projection") is not None
            ),
            "failures": failures,
        }


def print_json(value: Any) -> None:
    print(
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            indent=2,
        )
    )


def command_admit(args: argparse.Namespace) -> int:
    engine = living_lexicon_admission()
    result = engine.admit_file(Path(args.path))
    print_json(result)
    return 0


def command_reconcile(_: argparse.Namespace) -> int:
    engine = living_lexicon_admission()
    result = engine.reconcile()
    print_json(result)
    return 0 if result["passed"] else 1


def command_verify(_: argparse.Namespace) -> int:
    engine = living_lexicon_admission()
    result = engine.verify()
    print_json(result)
    return 0 if result["passed"] else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="living-lexicon-admission",
        description=(
            "admit active savant text representations as "
            "earmark-backed deterministic projections without "
            "following symbolic links"
        ),
    )

    commands = parser.add_subparsers(
        dest="command",
        required=True,
    )

    admit = commands.add_parser("admit")
    admit.add_argument("path")
    admit.set_defaults(function=command_admit)

    reconcile = commands.add_parser("reconcile")
    reconcile.set_defaults(function=command_reconcile)

    verify = commands.add_parser("verify")
    verify.set_defaults(function=command_verify)

    return parser


def main() -> int:
    arguments = build_parser().parse_args()

    try:
        return int(arguments.function(arguments))
    except (
        admission_error,
        OSError,
        RuntimeError,
        UnicodeError,
    ) as error:
        print_json(
            {
                "passed": False,
                "error": type(error).__name__,
                "message": str(error),
            }
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
