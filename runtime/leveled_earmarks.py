from __future__ import annotations

import argparse
import hashlib
import json
import os
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


runtime_root = Path("/root/savant-runtime")
state_root = runtime_root / "state" / "leveled-earmarks"
registry_path = state_root / "registry.json"
history_path = state_root / "history.jsonl"

schema_id = "savant.leveled-earmarks.registry.v1"


class earmark_error(RuntimeError):
    pass


class earmark_not_found(earmark_error):
    pass


class earmark_conflict(earmark_error):
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


def digest(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def semantic_id(namespace: str, seed: str) -> str:
    material = f"{namespace}\x00{seed}"
    return f"earmark:{hashlib.sha256(material.encode('utf-8')).hexdigest()}"


def harmony_id(level: int, members: Iterable[str]) -> str:
    normalized = tuple(members)
    material = {
        "kind": "harmony",
        "level": level,
        "members": normalized,
    }
    return f"harmony:{digest(material)}"


def atomic_write(path: Path, payload: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    fd, temporary = tempfile.mkstemp(
        prefix=f".{path.name}.",
        suffix=".tmp",
        dir=str(path.parent),
    )

    temporary_path = Path(temporary)

    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())

        os.chmod(temporary_path, 0o600)
        os.replace(temporary_path, path)

        directory_fd = os.open(path.parent, os.O_DIRECTORY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
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
        "version": 1,
        "glyphs": {},
        "earmarks": {},
        "harmonies": {},
        "dependencies": {},
        "dependents": {},
        "updated_at": None,
    }


def load_registry() -> dict[str, Any]:
    if not registry_path.exists():
        return empty_registry()

    with registry_path.open("r", encoding="utf-8") as handle:
        value = json.load(handle)

    if value.get("schema") != schema_id:
        raise earmark_error(
            f"unsupported registry schema: {value.get('schema')!r}"
        )

    return value


def save_registry(registry: dict[str, Any]) -> None:
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


@dataclass(frozen=True)
class resolved_earmark:
    id: str
    level: int
    value: str
    revision: int
    harmony: str
    members: tuple[str, ...]


class leveled_earmark_registry:
    def __init__(self) -> None:
        self.registry = load_registry()

    def save(self) -> None:
        save_registry(self.registry)

    def ensure_glyph(self, glyph: str) -> str:
        if len(glyph) != 1:
            raise earmark_error("a glyph must contain exactly one unicode character")

        glyph_id = f"glyph:{ord(glyph):x}"

        existing = self.registry["glyphs"].get(glyph_id)
        if existing is not None:
            if existing["value"] != glyph:
                raise earmark_conflict(glyph_id)
            return glyph_id

        self.registry["glyphs"][glyph_id] = {
            "id": glyph_id,
            "kind": "glyph",
            "value": glyph,
            "substantiated": True,
            "created_at": utc_now(),
        }

        return glyph_id

    def ensure_glyphs(self, value: str) -> list[str]:
        return [self.ensure_glyph(character) for character in value]

    def _record_harmony(
        self,
        *,
        level: int,
        members: list[str],
    ) -> str:
        identity = harmony_id(level, members)

        if identity not in self.registry["harmonies"]:
            self.registry["harmonies"][identity] = {
                "id": identity,
                "kind": "harmony",
                "level": level,
                "members": members,
                "created_at": utc_now(),
            }

        return identity

    def _add_dependency(self, parent: str, child: str) -> None:
        dependencies = self.registry["dependencies"].setdefault(child, [])
        dependents = self.registry["dependents"].setdefault(parent, [])

        if parent not in dependencies:
            dependencies.append(parent)
            dependencies.sort()

        if child not in dependents:
            dependents.append(child)
            dependents.sort()

    def _remove_dependency(self, parent: str, child: str) -> None:
        dependencies = self.registry["dependencies"].get(child, [])
        dependents = self.registry["dependents"].get(parent, [])

        if parent in dependencies:
            dependencies.remove(parent)

        if child in dependents:
            dependents.remove(child)

    def establish_level_zero(
        self,
        *,
        namespace: str,
        value: str,
        identity_seed: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        if not value:
            raise earmark_error("level 0 earmark value cannot be empty")

        seed = identity_seed if identity_seed is not None else value
        identity = semantic_id(namespace, seed)

        existing = self.registry["earmarks"].get(identity)
        if existing is not None:
            if existing["level"] != 0:
                raise earmark_conflict(identity)
            return identity

        glyph_members = self.ensure_glyphs(value)
        harmony = self._record_harmony(
            level=0,
            members=glyph_members,
        )

        timestamp = utc_now()

        self.registry["earmarks"][identity] = {
            "id": identity,
            "kind": "earmark",
            "level": 0,
            "namespace": namespace,
            "identity_seed": seed,
            "substantiated": False,
            "current_revision": 1,
            "current_harmony": harmony,
            "revisions": [
                {
                    "revision": 1,
                    "harmony": harmony,
                    "members": glyph_members,
                    "value": value,
                    "effective_at": timestamp,
                    "supersedes": None,
                    "metadata": metadata or {},
                }
            ],
            "created_at": timestamp,
            "updated_at": timestamp,
        }

        for member in glyph_members:
            self._add_dependency(member, identity)

        append_history(
            {
                "event": "earmark.established",
                "earmark": identity,
                "level": 0,
                "revision": 1,
                "harmony": harmony,
                "value": value,
                "timestamp": timestamp,
            }
        )

        self.save()
        return identity

    def establish_emergent(
        self,
        *,
        namespace: str,
        level: int,
        members: list[str],
        identity_seed: str,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        if level < 1:
            raise earmark_error("emergent earmark level must be at least 1")

        if not members:
            raise earmark_error("emergent earmark requires members")

        for member in members:
            record = self.registry["earmarks"].get(member)
            if record is None:
                raise earmark_not_found(member)

            if record["level"] != level - 1:
                raise earmark_error(
                    f"{member} is level {record['level']}; "
                    f"level {level} harmony requires level {level - 1} members"
                )

        identity = semantic_id(namespace, identity_seed)

        if identity in self.registry["earmarks"]:
            raise earmark_conflict(identity)

        harmony = self._record_harmony(
            level=level,
            members=members,
        )

        timestamp = utc_now()

        self.registry["earmarks"][identity] = {
            "id": identity,
            "kind": "earmark",
            "level": level,
            "namespace": namespace,
            "identity_seed": identity_seed,
            "substantiated": False,
            "current_revision": 1,
            "current_harmony": harmony,
            "revisions": [
                {
                    "revision": 1,
                    "harmony": harmony,
                    "members": members,
                    "effective_at": timestamp,
                    "supersedes": None,
                    "metadata": metadata or {},
                }
            ],
            "created_at": timestamp,
            "updated_at": timestamp,
        }

        for member in members:
            self._add_dependency(member, identity)

        append_history(
            {
                "event": "earmark.established",
                "earmark": identity,
                "level": level,
                "revision": 1,
                "harmony": harmony,
                "members": members,
                "timestamp": timestamp,
            }
        )

        self.save()
        return identity

    def supersede_level_zero(
        self,
        identity: str,
        new_value: str,
        *,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        record = self.registry["earmarks"].get(identity)

        if record is None:
            raise earmark_not_found(identity)

        if record["level"] != 0:
            raise earmark_error(
                "supersede_level_zero can only change level 0 earmarks"
            )

        if not new_value:
            raise earmark_error("new value cannot be empty")

        previous_revision = record["revisions"][-1]
        previous_members = list(previous_revision["members"])

        new_members = self.ensure_glyphs(new_value)
        new_harmony = self._record_harmony(
            level=0,
            members=new_members,
        )

        if (
            previous_revision["value"] == new_value
            and previous_revision["harmony"] == new_harmony
        ):
            return {
                "changed": False,
                "earmark": identity,
                "revision": record["current_revision"],
                "value": new_value,
                "affected": self.transitive_dependents(identity),
            }

        for member in previous_members:
            self._remove_dependency(member, identity)

        for member in new_members:
            self._add_dependency(member, identity)

        revision_number = int(record["current_revision"]) + 1
        timestamp = utc_now()

        revision = {
            "revision": revision_number,
            "harmony": new_harmony,
            "members": new_members,
            "value": new_value,
            "effective_at": timestamp,
            "supersedes": previous_revision["revision"],
            "metadata": metadata or {},
        }

        record["revisions"].append(revision)
        record["current_revision"] = revision_number
        record["current_harmony"] = new_harmony
        record["updated_at"] = timestamp

        affected = self.transitive_dependents(identity)

        append_history(
            {
                "event": "earmark.superseded",
                "earmark": identity,
                "level": 0,
                "revision": revision_number,
                "supersedes": previous_revision["revision"],
                "previous_value": previous_revision["value"],
                "value": new_value,
                "harmony": new_harmony,
                "affected": affected,
                "timestamp": timestamp,
            }
        )

        self.save()

        return {
            "changed": True,
            "earmark": identity,
            "revision": revision_number,
            "previous_value": previous_revision["value"],
            "value": new_value,
            "affected": affected,
        }

    def transitive_dependents(self, identity: str) -> list[str]:
        discovered: set[str] = set()
        pending = list(self.registry["dependents"].get(identity, []))

        while pending:
            current = pending.pop()

            if current in discovered:
                continue

            discovered.add(current)
            pending.extend(self.registry["dependents"].get(current, []))

        return sorted(discovered)

    def resolve(self, identity: str) -> resolved_earmark:
        record = self.registry["earmarks"].get(identity)

        if record is None:
            raise earmark_not_found(identity)

        revision = record["revisions"][-1]
        level = int(record["level"])

        if level == 0:
            value = revision["value"]
        else:
            pieces = [
                self.resolve(member).value
                for member in revision["members"]
            ]
            value = "".join(pieces)

        return resolved_earmark(
            id=identity,
            level=level,
            value=value,
            revision=int(record["current_revision"]),
            harmony=record["current_harmony"],
            members=tuple(revision["members"]),
        )

    def resolve_at_revision(
        self,
        identity: str,
        revision_number: int,
    ) -> dict[str, Any]:
        record = self.registry["earmarks"].get(identity)

        if record is None:
            raise earmark_not_found(identity)

        for revision in record["revisions"]:
            if int(revision["revision"]) == revision_number:
                return {
                    "earmark": identity,
                    "level": record["level"],
                    **revision,
                }

        raise earmark_not_found(
            f"{identity} revision {revision_number}"
        )

    def describe(self, identity: str) -> dict[str, Any]:
        resolved = self.resolve(identity)
        record = self.registry["earmarks"][identity]

        return {
            "id": resolved.id,
            "kind": "earmark",
            "level": resolved.level,
            "substantiated": False,
            "value": resolved.value,
            "revision": resolved.revision,
            "harmony": resolved.harmony,
            "members": list(resolved.members),
            "dependencies": self.registry["dependencies"].get(identity, []),
            "dependents": self.registry["dependents"].get(identity, []),
            "transitive_dependents": self.transitive_dependents(identity),
            "namespace": record["namespace"],
            "identity_seed": record["identity_seed"],
            "created_at": record["created_at"],
            "updated_at": record["updated_at"],
        }

    def verify(self) -> dict[str, Any]:
        failures: list[str] = []

        for identity, record in self.registry["earmarks"].items():
            level = int(record["level"])

            if record.get("substantiated") is not False:
                failures.append(
                    f"{identity}: non-glyph earmark marked substantiated"
                )

            if not record.get("revisions"):
                failures.append(f"{identity}: no revisions")
                continue

            current = record["revisions"][-1]

            if current["revision"] != record["current_revision"]:
                failures.append(
                    f"{identity}: current revision mismatch"
                )

            if current["harmony"] != record["current_harmony"]:
                failures.append(
                    f"{identity}: current harmony mismatch"
                )

            for member in current["members"]:
                if level == 0:
                    glyph = self.registry["glyphs"].get(member)
                    if glyph is None:
                        failures.append(
                            f"{identity}: missing glyph {member}"
                        )
                    elif glyph.get("substantiated") is not True:
                        failures.append(
                            f"{identity}: glyph {member} not substantiated"
                        )
                else:
                    child = self.registry["earmarks"].get(member)

                    if child is None:
                        failures.append(
                            f"{identity}: missing earmark {member}"
                        )
                    elif int(child["level"]) != level - 1:
                        failures.append(
                            f"{identity}: member {member} has level "
                            f"{child['level']}, expected {level - 1}"
                        )

                if identity not in self.registry["dependents"].get(member, []):
                    failures.append(
                        f"{identity}: missing reverse dependency from {member}"
                    )

        return {
            "schema": schema_id,
            "passed": not failures,
            "glyph_count": len(self.registry["glyphs"]),
            "earmark_count": len(self.registry["earmarks"]),
            "harmony_count": len(self.registry["harmonies"]),
            "failures": failures,
        }


def print_json(value: Any) -> None:
    print(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2))


def command_establish(args: argparse.Namespace) -> int:
    registry = leveled_earmark_registry()

    identity = registry.establish_level_zero(
        namespace=args.namespace,
        value=args.value,
        identity_seed=args.identity,
    )

    print_json(registry.describe(identity))
    return 0


def command_supersede(args: argparse.Namespace) -> int:
    registry = leveled_earmark_registry()

    result = registry.supersede_level_zero(
        args.earmark,
        args.value,
    )

    print_json(result)
    return 0


def command_resolve(args: argparse.Namespace) -> int:
    registry = leveled_earmark_registry()
    print_json(registry.describe(args.earmark))
    return 0


def command_verify(_: argparse.Namespace) -> int:
    registry = leveled_earmark_registry()
    result = registry.verify()
    print_json(result)
    return 0 if result["passed"] else 1


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(
        prog="leveled-earmarks",
        description="savant leveled earmark and harmony runtime",
    )

    commands = root.add_subparsers(dest="command", required=True)

    establish = commands.add_parser("establish")
    establish.add_argument("namespace")
    establish.add_argument("value")
    establish.add_argument("--identity")
    establish.set_defaults(function=command_establish)

    supersede = commands.add_parser("supersede")
    supersede.add_argument("earmark")
    supersede.add_argument("value")
    supersede.set_defaults(function=command_supersede)

    resolve = commands.add_parser("resolve")
    resolve.add_argument("earmark")
    resolve.set_defaults(function=command_resolve)

    verify = commands.add_parser("verify")
    verify.set_defaults(function=command_verify)

    return root


def main() -> int:
    arguments = parser().parse_args()

    try:
        return int(arguments.function(arguments))
    except earmark_error as error:
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
