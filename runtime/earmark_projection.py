from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from runtime.leveled_earmarks import (
    earmark_error,
    earmark_not_found,
    leveled_earmark_registry,
)


runtime_root = Path("/root/savant-runtime")
state_root = runtime_root / "state" / "earmark-projection"
registry_path = state_root / "registry.json"
history_path = state_root / "history.jsonl"

schema_id = "savant.earmark-projection.registry.v1"

token_pattern = re.compile(
    r"\{\{earmark:(earmark:[0-9a-f]{64})\}\}"
)

protected_roots = (
    runtime_root / ".git",
    runtime_root / "audit",
    runtime_root / "backups",
    runtime_root / "vault" / "backups",
)

protected_fragments = (
    "/node_modules/",
    "/.venv/",
    "/.venv-",
    "/__pycache__/",
)


class projection_error(RuntimeError):
    pass


class projection_conflict(projection_error):
    pass


class projection_not_found(projection_error):
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


def empty_registry() -> dict[str, Any]:
    return {
        "schema": schema_id,
        "version": 1,
        "projections": {},
        "dependencies": {},
        "updated_at": None,
    }


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


def load_projection_registry() -> dict[str, Any]:
    if not registry_path.exists():
        return empty_registry()

    with registry_path.open("r", encoding="utf-8") as handle:
        value = json.load(handle)

    if value.get("schema") != schema_id:
        raise projection_error(
            f"unsupported projection schema: {value.get('schema')!r}"
        )

    return value


def save_projection_registry(registry: dict[str, Any]) -> None:
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


def normalize_target(value: str) -> Path:
    candidate = Path(value)

    if not candidate.is_absolute():
        candidate = runtime_root / candidate

    candidate = candidate.resolve(strict=False)
    root = runtime_root.resolve()

    try:
        candidate.relative_to(root)
    except ValueError as error:
        raise projection_error(
            f"projection target is outside savant runtime: {candidate}"
        ) from error

    text = str(candidate)

    for protected in protected_roots:
        protected_text = str(protected.resolve(strict=False))

        if text == protected_text or text.startswith(protected_text + "/"):
            raise projection_error(
                f"projection target is protected: {candidate}"
            )

    for fragment in protected_fragments:
        if fragment in text:
            raise projection_error(
                f"projection target is protected: {candidate}"
            )

    return candidate


def projection_id(target: Path) -> str:
    relative = target.relative_to(runtime_root).as_posix()
    return f"projection:{sha256_text(relative)}"


def extract_dependencies(template: str) -> list[str]:
    return sorted(set(token_pattern.findall(template)))


class earmark_projection_registry:
    def __init__(self) -> None:
        self.earmarks = leveled_earmark_registry()
        self.registry = load_projection_registry()

    def save(self) -> None:
        save_projection_registry(self.registry)

    def render_template(self, template: str) -> str:
        def replace(match: re.Match[str]) -> str:
            identity = match.group(1)
            return self.earmarks.resolve(identity).value

        return token_pattern.sub(replace, template)

    def register(
        self,
        *,
        target: str,
        template: str,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        target_path = normalize_target(target)
        identity = projection_id(target_path)
        dependencies = extract_dependencies(template)

        for dependency in dependencies:
            self.earmarks.resolve(dependency)

        existing = self.registry["projections"].get(identity)

        if existing is not None:
            if existing["target"] != str(target_path):
                raise projection_conflict(identity)

            if existing["template"] != template:
                raise projection_conflict(
                    f"{identity} already exists with a different template"
                )

            return self.describe(identity)

        timestamp = utc_now()

        record = {
            "id": identity,
            "kind": "filament",
            "target": str(target_path),
            "template": template,
            "template_sha256": sha256_text(template),
            "dependencies": dependencies,
            "metadata": metadata or {},
            "created_at": timestamp,
            "updated_at": timestamp,
            "last_rendered_at": None,
            "last_rendered_sha256": None,
        }

        self.registry["projections"][identity] = record

        for dependency in dependencies:
            dependent_list = self.registry["dependencies"].setdefault(
                dependency,
                []
            )

            if identity not in dependent_list:
                dependent_list.append(identity)
                dependent_list.sort()

        self.save()

        append_history(
            {
                "event": "projection.registered",
                "projection": identity,
                "target": str(target_path),
                "dependencies": dependencies,
                "timestamp": timestamp,
            }
        )

        return self.describe(identity)

    def register_file(
        self,
        *,
        target: str,
        template_file: str,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        template_path = normalize_target(template_file)

        if not template_path.is_file():
            raise projection_not_found(str(template_path))

        template = template_path.read_text(encoding="utf-8")

        return self.register(
            target=target,
            template=template,
            metadata=metadata,
        )

    def render(self, identity: str) -> dict[str, Any]:
        record = self.registry["projections"].get(identity)

        if record is None:
            raise projection_not_found(identity)

        target = normalize_target(record["target"])
        rendered = self.render_template(record["template"])
        rendered_sha256 = sha256_text(rendered)

        previous_sha256 = None

        if target.is_file():
            previous_sha256 = sha256_text(
                target.read_text(encoding="utf-8")
            )

        changed = previous_sha256 != rendered_sha256

        if changed:
            atomic_write(target, rendered)

        timestamp = utc_now()

        record["last_rendered_at"] = timestamp
        record["last_rendered_sha256"] = rendered_sha256
        record["updated_at"] = timestamp

        self.save()

        append_history(
            {
                "event": "projection.rendered",
                "projection": identity,
                "target": str(target),
                "changed": changed,
                "previous_sha256": previous_sha256,
                "sha256": rendered_sha256,
                "timestamp": timestamp,
            }
        )

        return {
            "projection": identity,
            "target": str(target),
            "changed": changed,
            "sha256": rendered_sha256,
            "dependencies": record["dependencies"],
        }

    def render_for_earmark(self, identity: str) -> dict[str, Any]:
        self.earmarks.resolve(identity)

        direct = list(
            self.registry["dependencies"].get(identity, [])
        )

        rendered: list[dict[str, Any]] = []

        for projection in direct:
            rendered.append(self.render(projection))

        return {
            "earmark": identity,
            "projection_count": len(rendered),
            "projections": rendered,
        }

    def render_for_earmarks(
        self,
        identities: list[str],
    ) -> dict[str, Any]:
        projections: set[str] = set()

        for identity in identities:
            self.earmarks.resolve(identity)
            projections.update(
                self.registry["dependencies"].get(identity, [])
            )

        rendered = [
            self.render(identity)
            for identity in sorted(projections)
        ]

        return {
            "earmarks": sorted(set(identities)),
            "projection_count": len(rendered),
            "projections": rendered,
        }

    def render_all(self) -> dict[str, Any]:
        rendered = [
            self.render(identity)
            for identity in sorted(self.registry["projections"])
        ]

        return {
            "projection_count": len(rendered),
            "projections": rendered,
        }

    def describe(self, identity: str) -> dict[str, Any]:
        record = self.registry["projections"].get(identity)

        if record is None:
            raise projection_not_found(identity)

        return {
            **record,
            "resolved_dependencies": {
                dependency: self.earmarks.resolve(dependency).value
                for dependency in record["dependencies"]
            },
        }

    def verify(self) -> dict[str, Any]:
        failures: list[str] = []

        earmark_verification = self.earmarks.verify()

        if not earmark_verification["passed"]:
            failures.extend(
                f"earmark: {failure}"
                for failure in earmark_verification["failures"]
            )

        expected_reverse_dependencies: dict[str, list[str]] = {}

        for identity, record in self.registry["projections"].items():
            try:
                target = normalize_target(record["target"])
            except projection_error as error:
                failures.append(f"{identity}: {error}")
                continue

            expected_identity = projection_id(target)

            if expected_identity != identity:
                failures.append(
                    f"{identity}: target identity mismatch"
                )

            template = record.get("template")

            if not isinstance(template, str):
                failures.append(
                    f"{identity}: template is not text"
                )
                continue

            expected_template_sha256 = sha256_text(template)

            if record.get("template_sha256") != expected_template_sha256:
                failures.append(
                    f"{identity}: template hash mismatch"
                )

            dependencies = extract_dependencies(template)

            if dependencies != record.get("dependencies", []):
                failures.append(
                    f"{identity}: dependency list mismatch"
                )

            for dependency in dependencies:
                try:
                    self.earmarks.resolve(dependency)
                except earmark_error as error:
                    failures.append(
                        f"{identity}: unresolved dependency "
                        f"{dependency}: {error}"
                    )

                expected_reverse_dependencies.setdefault(
                    dependency,
                    []
                ).append(identity)

        normalized_expected = {
            key: sorted(set(value))
            for key, value in expected_reverse_dependencies.items()
        }

        normalized_actual = {
            key: sorted(set(value))
            for key, value in self.registry["dependencies"].items()
            if value
        }

        if normalized_expected != normalized_actual:
            failures.append(
                "projection reverse dependency index mismatch"
            )

        return {
            "schema": schema_id,
            "passed": not failures,
            "projection_count": len(
                self.registry["projections"]
            ),
            "dependency_count": len(
                normalized_actual
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


def command_register(args: argparse.Namespace) -> int:
    registry = earmark_projection_registry()

    result = registry.register_file(
        target=args.target,
        template_file=args.template,
    )

    print_json(result)
    return 0


def command_render(args: argparse.Namespace) -> int:
    registry = earmark_projection_registry()
    print_json(registry.render(args.projection))
    return 0


def command_render_earmark(args: argparse.Namespace) -> int:
    registry = earmark_projection_registry()
    print_json(registry.render_for_earmark(args.earmark))
    return 0


def command_render_all(_: argparse.Namespace) -> int:
    registry = earmark_projection_registry()
    print_json(registry.render_all())
    return 0


def command_describe(args: argparse.Namespace) -> int:
    registry = earmark_projection_registry()
    print_json(registry.describe(args.projection))
    return 0


def command_verify(_: argparse.Namespace) -> int:
    registry = earmark_projection_registry()
    result = registry.verify()
    print_json(result)
    return 0 if result["passed"] else 1


def build_parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(
        prog="earmark-projection",
        description=(
            "deterministic savant filament projection from "
            "leveled earmark originals"
        ),
    )

    commands = root.add_subparsers(
        dest="command",
        required=True,
    )

    register = commands.add_parser("register")
    register.add_argument("target")
    register.add_argument("template")
    register.set_defaults(function=command_register)

    render = commands.add_parser("render")
    render.add_argument("projection")
    render.set_defaults(function=command_render)

    render_earmark = commands.add_parser("render-earmark")
    render_earmark.add_argument("earmark")
    render_earmark.set_defaults(
        function=command_render_earmark
    )

    render_all = commands.add_parser("render-all")
    render_all.set_defaults(function=command_render_all)

    describe = commands.add_parser("describe")
    describe.add_argument("projection")
    describe.set_defaults(function=command_describe)

    verify = commands.add_parser("verify")
    verify.set_defaults(function=command_verify)

    return root


def main() -> int:
    arguments = build_parser().parse_args()

    try:
        return int(arguments.function(arguments))
    except (
        earmark_error,
        projection_error,
        OSError,
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
