#!/usr/bin/env python3

from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from copy import deepcopy
from pathlib import Path
from types import ModuleType
from typing import Any, Callable, Mapping


schema = "savant.coda.datrix-commit.v1"
owner = "coda"
authority_effect = "none"

ROOT = Path("/root/savant-runtime").resolve()
MUTATION_PATH = (
    ROOT
    / "ontology/obelisks/_template/segue/gates/_template/segue/innates/_template/segue/exiles/coda/runtime/mutation.py"
)


class CodaDatrixCommitError(RuntimeError):
    pass


class CodaDatrixConflict(CodaDatrixCommitError):
    pass


def _canonical(value: Any) -> str:
    try:
        return json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
    except (TypeError, ValueError) as exc:
        raise CodaDatrixCommitError(
            f"capsule is not canonical-json compatible: {exc}"
        ) from exc


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _module_sha256(module: ModuleType) -> str | None:
    raw = getattr(module, "__file__", None)
    if not raw:
        return None
    path = Path(str(raw))
    if not path.is_file():
        return None
    return _sha256_bytes(path.read_bytes())


def _load_mutation_module(path: Path = MUTATION_PATH) -> ModuleType:
    module_name = "savant_coda_runtime_mutation"
    existing = sys.modules.get(module_name)
    if existing is not None:
        return existing
    if not path.is_file():
        raise CodaDatrixCommitError(f"coda mutation runtime is missing: {path}")
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise CodaDatrixCommitError("unable to load coda mutation runtime")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    try:
        spec.loader.exec_module(module)
    except Exception:
        sys.modules.pop(module_name, None)
        raise
    return module


def _default_capsule_validator(capsule: Mapping[str, Any]) -> dict[str, Any]:
    from runtime.straub.registry import StraubRegistry

    recovered = StraubRegistry.from_capsule(capsule)
    normalized = recovered.export_capsule()
    supplied_digest = str(capsule.get("digest") or "")
    if not supplied_digest or normalized.get("digest") != supplied_digest:
        raise CodaDatrixCommitError("straub capsule validation changed capsule digest")
    return normalized


def serialize_capsule(capsule: Mapping[str, Any]) -> str:
    return _canonical(capsule) + "\n"


class CodaDatrixCommitter:
    """Coda-owned durable commit boundary for one Straub capsule file."""

    def __init__(
        self,
        *,
        root: str | Path = ROOT,
        mutation_module: ModuleType | None = None,
        capsule_validator: Callable[[Mapping[str, Any]], Mapping[str, Any]] | None = None,
    ) -> None:
        self.root = Path(root).resolve()
        self._mutation = mutation_module or _load_mutation_module()
        self._capsule_validator = capsule_validator or _default_capsule_validator
        self._validate_contract()

    def _validate_contract(self) -> None:
        required = (
            "inspect_path",
            "replace_text",
            "create_text",
            "restore_backup",
            "delete_file",
            "status",
        )
        missing = [name for name in required if not callable(getattr(self._mutation, name, None))]
        if missing:
            raise CodaDatrixCommitError(
                f"coda mutation runtime is missing required operations: {missing!r}"
            )
        status = self._mutation.status()
        if not isinstance(status, Mapping):
            raise CodaDatrixCommitError("coda status must be a mapping")
        if str(status.get("owner") or "") != "coda" or status.get("ready") is not True:
            raise CodaDatrixCommitError("coda mutation runtime is not ready")

    def _relative_path(self, raw: str | Path) -> str:
        path = Path(raw).resolve()
        try:
            return str(path.relative_to(self.root))
        except ValueError as exc:
            raise CodaDatrixCommitError("datrix path escapes savant runtime root") from exc

    def inspect(self, path: str | Path) -> dict[str, Any]:
        result = self._mutation.inspect_path(self._relative_path(path))
        if not isinstance(result, Mapping):
            raise CodaDatrixCommitError("coda inspect_path returned invalid result")
        return deepcopy(dict(result))

    def commit_capsule(
        self,
        path: str | Path,
        capsule: Mapping[str, Any],
        *,
        expected_file_digest: str | None,
        requester: str = "translucent:datrix",
        intent: str = "commit straub datrix capsule",
    ) -> dict[str, Any]:
        normalized = deepcopy(dict(self._capsule_validator(capsule)))
        content = serialize_capsule(normalized)
        encoded = content.encode("utf-8")
        target_digest = _sha256_bytes(encoded)
        relative = self._relative_path(path)
        before = self.inspect(path)
        before_digest = before.get("digest")

        if before_digest != expected_file_digest:
            raise CodaDatrixConflict(
                "datrix capsule changed since open: "
                f"expected {expected_file_digest!r}, got {before_digest!r}"
            )

        try:
            if before.get("exists"):
                mutation = self._mutation.replace_text(
                    relative,
                    content,
                    expected_digest=expected_file_digest,
                    requester=requester,
                    intent=intent,
                )
            else:
                if expected_file_digest is not None:
                    raise CodaDatrixConflict(
                        "datrix capsule disappeared since open"
                    )
                mutation = self._mutation.create_text(
                    relative,
                    content,
                    requester=requester,
                    intent=intent,
                )
        except CodaDatrixCommitError:
            raise
        except Exception as exc:
            after_error = self.inspect(path)
            if after_error.get("digest") == target_digest:
                raise CodaDatrixCommitError(
                    "coda reached target capsule bytes but did not return a complete commit receipt"
                ) from exc
            raise CodaDatrixCommitError(f"coda datrix commit failed: {exc}") from exc

        if not isinstance(mutation, Mapping):
            raise CodaDatrixCommitError("coda commit receipt is invalid")
        after = self.inspect(path)
        if after.get("digest") != target_digest:
            raise CodaDatrixCommitError("coda post-commit file digest verification failed")

        result = {
            "schema": schema,
            "owner": owner,
            "path": relative,
            "capsule_digest": normalized.get("digest"),
            "before_file_digest": before_digest,
            "after_file_digest": target_digest,
            "mutation_receipt": deepcopy(dict(mutation)),
            "mutation_receipt_ref": mutation.get("receipt"),
            "reversible": bool(mutation.get("reversible")),
            "backup": mutation.get("backup"),
            "coda_runtime_sha256": _module_sha256(self._mutation),
            "single_capsule_atomic": True,
            "multi_capsule_atomic": False,
            "authority_effect": authority_effect,
        }
        result["digest"] = _sha256_bytes(_canonical(result).encode("utf-8"))
        return result

    def rollback(
        self,
        path: str | Path,
        commit: Mapping[str, Any],
        *,
        expected_file_digest: str | None,
        requester: str = "translucent:datrix",
        intent: str = "rollback straub datrix capsule",
    ) -> dict[str, Any]:
        if str(commit.get("schema") or "") != schema:
            raise CodaDatrixCommitError("rollback reference is not a coda datrix commit")
        relative = self._relative_path(path)
        if str(commit.get("path") or "") != relative:
            raise CodaDatrixCommitError("rollback reference targets another datrix capsule")
        backup = str(commit.get("backup") or "").strip()
        current = self.inspect(path)
        if current.get("digest") != expected_file_digest:
            raise CodaDatrixConflict("datrix capsule changed since rollback was requested")
        expected_restored = commit.get("before_file_digest")
        try:
            if backup:
                mutation = self._mutation.restore_backup(
                    relative,
                    backup,
                    expected_digest=expected_file_digest,
                    requester=requester,
                    intent=intent,
                )
            elif expected_restored is None:
                mutation = self._mutation.delete_file(
                    relative,
                    expected_digest=expected_file_digest,
                    requester=requester,
                    intent=intent,
                )
            else:
                raise CodaDatrixCommitError(
                    "commit has neither a coda backup nor a new-file rollback path"
                )
        except CodaDatrixCommitError:
            raise
        except Exception as exc:
            raise CodaDatrixCommitError(f"coda datrix rollback failed: {exc}") from exc
        if not isinstance(mutation, Mapping):
            raise CodaDatrixCommitError("coda rollback receipt is invalid")
        after = self.inspect(path)
        if after.get("digest") != expected_restored:
            raise CodaDatrixCommitError("coda rollback digest verification failed")
        result = {
            "schema": "savant.coda.datrix-rollback.v1",
            "owner": owner,
            "path": relative,
            "restored_file_digest": after.get("digest"),
            "rolled_back_commit_digest": commit.get("digest"),
            "mutation_receipt": deepcopy(dict(mutation)),
            "mutation_receipt_ref": mutation.get("receipt"),
            "authority_effect": authority_effect,
        }
        result["digest"] = _sha256_bytes(_canonical(result).encode("utf-8"))
        return result

    def status(self) -> dict[str, Any]:
        coda_status = deepcopy(dict(self._mutation.status()))
        result = {
            "schema": schema,
            "owner": owner,
            "purpose": "coda-owned durable commit of one canonical straub datrix capsule",
            "coda": coda_status,
            "coda_runtime_sha256": _module_sha256(self._mutation),
            "optimistic_concurrency": True,
            "single_capsule_atomic": True,
            "multi_capsule_atomic": False,
            "rollback": True,
            "new_file_rollback": True,
            "authority_effect": authority_effect,
        }
        result["digest"] = _sha256_bytes(_canonical(result).encode("utf-8"))
        return result


__all__ = [
    "CodaDatrixCommitError",
    "CodaDatrixCommitter",
    "CodaDatrixConflict",
    "authority_effect",
    "owner",
    "schema",
    "serialize_capsule",
]
