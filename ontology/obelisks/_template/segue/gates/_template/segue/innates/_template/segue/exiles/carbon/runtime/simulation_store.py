#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any, Mapping

from simulation import (
    OWNER,
    SCHEMA,
    SimulationError,
    canonical_json,
    digest,
)


ROOT = Path("/root/savant-runtime").resolve()

STORE_ROOT = (
    ROOT
    / "runtime"
    / "carbon"
    / "simulations"
).resolve()

DEFINITIONS_ROOT = STORE_ROOT / "definitions"
INSTANCES_ROOT = STORE_ROOT / "instances"
CHECKPOINTS_ROOT = STORE_ROOT / "checkpoints"
RECEIPTS_ROOT = STORE_ROOT / "receipts"


class SimulationStoreError(SimulationError):
    pass


class SimulationStoreConflict(
    SimulationStoreError
):
    pass


class SimulationStoreNotFound(
    SimulationStoreError
):
    pass


def _safe_component(value: str) -> str:
    normalized = str(value or "").strip()

    if not normalized:
        raise SimulationStoreError(
            "storage identity is required"
        )

    if normalized in {".", ".."}:
        raise SimulationStoreError(
            "invalid storage identity"
        )

    if "/" in normalized or "\\" in normalized:
        raise SimulationStoreError(
            "storage identity cannot contain "
            "path separators"
        )

    if "\x00" in normalized:
        raise SimulationStoreError(
            "storage identity cannot contain null"
        )

    return normalized


def _ensure_roots() -> None:
    for path in (
        DEFINITIONS_ROOT,
        INSTANCES_ROOT,
        CHECKPOINTS_ROOT,
        RECEIPTS_ROOT,
    ):
        path.mkdir(
            parents=True,
            exist_ok=True,
        )


def _atomic_json_write(
    destination: Path,
    payload: Mapping[str, Any],
) -> None:
    destination.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    descriptor, temporary_name = (
        tempfile.mkstemp(
            prefix=f".{destination.name}.",
            suffix=".tmp",
            dir=str(destination.parent),
        )
    )

    temporary = Path(temporary_name)

    try:
        with os.fdopen(
            descriptor,
            "w",
            encoding="utf-8",
        ) as handle:
            json.dump(
                dict(payload),
                handle,
                ensure_ascii=False,
                sort_keys=True,
                indent=2,
            )
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())

        os.replace(
            temporary,
            destination,
        )

        directory_descriptor = os.open(
            destination.parent,
            os.O_RDONLY,
        )

        try:
            os.fsync(directory_descriptor)
        finally:
            os.close(directory_descriptor)

    except Exception:
        temporary.unlink(
            missing_ok=True
        )
        raise


def _read_json(
    path: Path,
) -> dict[str, Any]:
    if not path.is_file():
        raise SimulationStoreNotFound(
            f"simulation artifact not found: {path}"
        )

    try:
        value = json.loads(
            path.read_text(
                encoding="utf-8"
            )
        )
    except (
        OSError,
        json.JSONDecodeError,
    ) as exc:
        raise SimulationStoreError(
            f"cannot read simulation artifact: "
            f"{path}"
        ) from exc

    if not isinstance(value, dict):
        raise SimulationStoreError(
            f"simulation artifact is not a "
            f"mapping: {path}"
        )

    return value


def _projection_digest(
    payload: Mapping[str, Any],
) -> str:
    material = dict(payload)
    material.pop(
        "storage_digest",
        None,
    )
    return digest(material)


def _envelope(
    payload: Mapping[str, Any],
    *,
    artifact_type: str,
) -> dict[str, Any]:
    value = dict(payload)

    artifact_id = _safe_component(
        str(value.get("id") or "")
    )

    envelope = {
        "schema": (
            "savant://carbon/"
            "simulation-storage/1"
        ),
        "owner": OWNER,
        "artifact_type": artifact_type,
        "artifact_id": artifact_id,
        "simulation_schema": value.get(
            "schema",
            SCHEMA,
        ),
        "payload": value,
        "authority_effect": "none",
        "authoritative": False,
    }

    envelope["storage_digest"] = digest(
        envelope
    )

    return envelope


def _verify_envelope(
    envelope: Mapping[str, Any],
) -> dict[str, Any]:
    value = dict(envelope)

    expected = str(
        value.get("storage_digest")
        or ""
    ).strip()

    if not expected:
        raise SimulationStoreError(
            "stored artifact lacks storage digest"
        )

    material = dict(value)
    material.pop(
        "storage_digest",
        None,
    )

    actual = digest(material)

    if actual != expected:
        raise SimulationStoreError(
            "stored artifact digest mismatch"
        )

    payload = value.get("payload")

    if not isinstance(payload, dict):
        raise SimulationStoreError(
            "stored simulation payload is invalid"
        )

    return dict(payload)


class SimulationStore:
    def __init__(
        self,
        root: Path = STORE_ROOT,
    ) -> None:
        self.root = root.resolve()

        if self.root == STORE_ROOT:
            self.definitions_root = (
                DEFINITIONS_ROOT
            )
            self.instances_root = INSTANCES_ROOT
            self.checkpoints_root = (
                CHECKPOINTS_ROOT
            )
            self.receipts_root = RECEIPTS_ROOT
        else:
            self.definitions_root = (
                self.root / "definitions"
            )
            self.instances_root = (
                self.root / "instances"
            )
            self.checkpoints_root = (
                self.root / "checkpoints"
            )
            self.receipts_root = (
                self.root / "receipts"
            )

        for path in (
            self.definitions_root,
            self.instances_root,
            self.checkpoints_root,
            self.receipts_root,
        ):
            path.mkdir(
                parents=True,
                exist_ok=True,
            )

    @staticmethod
    def _artifact_path(
        root: Path,
        artifact_id: str,
    ) -> Path:
        identity = _safe_component(
            artifact_id
        )
        return root / f"{identity}.json"

    def save_definition(
        self,
        projection: Mapping[str, Any],
    ) -> dict[str, Any]:
        envelope = _envelope(
            projection,
            artifact_type=(
                "simulation_definition"
            ),
        )

        path = self._artifact_path(
            self.definitions_root,
            envelope["artifact_id"],
        )

        self._write_versioned(
            path,
            envelope,
        )

        return {
            "artifact_id": (
                envelope["artifact_id"]
            ),
            "artifact_type": (
                envelope["artifact_type"]
            ),
            "path": str(
                path.relative_to(ROOT)
                if ROOT in path.parents
                else path
            ),
            "storage_digest": (
                envelope["storage_digest"]
            ),
            "persisted": True,
            "authority_effect": "none",
        }

    def load_definition(
        self,
        definition_id: str,
    ) -> dict[str, Any]:
        path = self._artifact_path(
            self.definitions_root,
            definition_id,
        )
        return _verify_envelope(
            _read_json(path)
        )

    def save_instance(
        self,
        projection: Mapping[str, Any],
    ) -> dict[str, Any]:
        envelope = _envelope(
            projection,
            artifact_type=(
                "simulation_instance"
            ),
        )

        path = self._artifact_path(
            self.instances_root,
            envelope["artifact_id"],
        )

        _atomic_json_write(
            path,
            envelope,
        )

        return {
            "artifact_id": (
                envelope["artifact_id"]
            ),
            "artifact_type": (
                envelope["artifact_type"]
            ),
            "path": str(
                path.relative_to(ROOT)
                if ROOT in path.parents
                else path
            ),
            "storage_digest": (
                envelope["storage_digest"]
            ),
            "persisted": True,
            "authority_effect": "none",
        }

    def load_instance(
        self,
        instance_id: str,
    ) -> dict[str, Any]:
        path = self._artifact_path(
            self.instances_root,
            instance_id,
        )
        return _verify_envelope(
            _read_json(path)
        )

    def save_checkpoint(
        self,
        projection: Mapping[str, Any],
    ) -> dict[str, Any]:
        envelope = _envelope(
            projection,
            artifact_type=(
                "simulation_checkpoint"
            ),
        )

        path = self._artifact_path(
            self.checkpoints_root,
            envelope["artifact_id"],
        )

        self._write_immutable(
            path,
            envelope,
        )

        return {
            "artifact_id": (
                envelope["artifact_id"]
            ),
            "artifact_type": (
                envelope["artifact_type"]
            ),
            "path": str(
                path.relative_to(ROOT)
                if ROOT in path.parents
                else path
            ),
            "storage_digest": (
                envelope["storage_digest"]
            ),
            "persisted": True,
            "immutable": True,
            "authority_effect": "none",
        }

    def load_checkpoint(
        self,
        checkpoint_id: str,
    ) -> dict[str, Any]:
        path = self._artifact_path(
            self.checkpoints_root,
            checkpoint_id,
        )
        return _verify_envelope(
            _read_json(path)
        )

    def append_receipt(
        self,
        projection: Mapping[str, Any],
    ) -> dict[str, Any]:
        envelope = _envelope(
            projection,
            artifact_type=(
                "simulation_receipt"
            ),
        )

        path = self._artifact_path(
            self.receipts_root,
            envelope["artifact_id"],
        )

        self._write_immutable(
            path,
            envelope,
        )

        return {
            "artifact_id": (
                envelope["artifact_id"]
            ),
            "artifact_type": (
                envelope["artifact_type"]
            ),
            "path": str(
                path.relative_to(ROOT)
                if ROOT in path.parents
                else path
            ),
            "storage_digest": (
                envelope["storage_digest"]
            ),
            "persisted": True,
            "immutable": True,
            "authority_effect": "none",
        }

    def load_receipt(
        self,
        receipt_id: str,
    ) -> dict[str, Any]:
        path = self._artifact_path(
            self.receipts_root,
            receipt_id,
        )
        return _verify_envelope(
            _read_json(path)
        )

    def list_artifacts(
        self,
        artifact_type: str,
    ) -> list[str]:
        roots = {
            "simulation_definition": (
                self.definitions_root
            ),
            "simulation_instance": (
                self.instances_root
            ),
            "simulation_checkpoint": (
                self.checkpoints_root
            ),
            "simulation_receipt": (
                self.receipts_root
            ),
        }

        try:
            root = roots[artifact_type]
        except KeyError as exc:
            raise SimulationStoreError(
                f"unsupported artifact type: "
                f"{artifact_type}"
            ) from exc

        return sorted(
            path.stem
            for path in root.glob("*.json")
            if path.is_file()
        )

    def verify(
        self,
        artifact_type: str,
        artifact_id: str,
    ) -> dict[str, Any]:
        roots = {
            "simulation_definition": (
                self.definitions_root
            ),
            "simulation_instance": (
                self.instances_root
            ),
            "simulation_checkpoint": (
                self.checkpoints_root
            ),
            "simulation_receipt": (
                self.receipts_root
            ),
        }

        try:
            root = roots[artifact_type]
        except KeyError as exc:
            raise SimulationStoreError(
                f"unsupported artifact type: "
                f"{artifact_type}"
            ) from exc

        path = self._artifact_path(
            root,
            artifact_id,
        )

        envelope = _read_json(path)
        payload = _verify_envelope(
            envelope
        )

        return {
            "artifact_type": artifact_type,
            "artifact_id": artifact_id,
            "storage_digest": (
                envelope["storage_digest"]
            ),
            "payload_digest": (
                _projection_digest(payload)
            ),
            "verified": True,
            "authority_effect": "none",
        }

    @staticmethod
    def _write_immutable(
        path: Path,
        envelope: Mapping[str, Any],
    ) -> None:
        if path.exists():
            existing = _read_json(path)

            if canonical_json(existing) == (
                canonical_json(envelope)
            ):
                return

            raise SimulationStoreConflict(
                f"immutable simulation artifact "
                f"already exists: {path}"
            )

        _atomic_json_write(
            path,
            envelope,
        )

    @staticmethod
    def _write_versioned(
        path: Path,
        envelope: Mapping[str, Any],
    ) -> None:
        if path.exists():
            existing = _read_json(path)

            existing_payload = (
                _verify_envelope(existing)
            )

            incoming_payload = (
                _verify_envelope(envelope)
            )

            if canonical_json(
                existing_payload
            ) != canonical_json(
                incoming_payload
            ):
                raise SimulationStoreConflict(
                    "simulation definition identity "
                    "collision"
                )

            return

        _atomic_json_write(
            path,
            envelope,
        )


_ensure_roots()

store = SimulationStore()


def status() -> dict[str, Any]:
    return {
        "schema": (
            "savant://carbon/"
            "simulation-storage/1"
        ),
        "owner": OWNER,
        "root": str(STORE_ROOT),
        "persistence": "atomic_json",
        "definition_identity": "immutable",
        "checkpoint_identity": "immutable",
        "receipt_identity": "immutable",
        "instance_projection": "replaceable",
        "digest_verification": True,
        "authority_effect": "none",
    }


if __name__ == "__main__":
    print(
        json.dumps(
            status(),
            indent=2,
            sort_keys=True,
        )
    )
