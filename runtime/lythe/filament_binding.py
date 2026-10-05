#!/usr/bin/env python3

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence


ROOT = Path("/root/savant-runtime")

FILAMENT_ROOT = (
    ROOT
    / "ontology/obelisks/_template/segue/gates/_template/segue/"
    "innates/_template/segue/exiles/filament"
).resolve()

FILAMENT_CONTRACT = (
    FILAMENT_ROOT
    / "interface/contracts/projection_engine_contract.json"
)

FILAMENT_MANIFEST = (
    FILAMENT_ROOT
    / "registry/manifests/projection_engine.json"
)

OWNER = "living:lythe"
EXECUTION_OWNER = "filament"

SCHEMA = "savant://runtime/lythe/filament-binding/1.0.0"


class LytheFilamentBindingError(RuntimeError):
    pass


def canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )


def digest(value: Any) -> str:
    return hashlib.sha256(
        canonical_json(value).encode("utf-8")
    ).hexdigest()


def normalized_identifier(
    value: Any,
) -> str | None:
    if value is None:
        return None

    text = str(value).strip()

    return text or None


def normalized_sequence(
    value: Any,
) -> tuple[str, ...]:
    if value is None:
        return ()

    if isinstance(value, str):
        item = normalized_identifier(value)
        return (item,) if item else ()

    if isinstance(value, Mapping):
        source = value.keys()
    else:
        try:
            source = iter(value)
        except TypeError:
            source = (value,)

    result = {
        normalized
        for normalized in (
            normalized_identifier(item)
            for item in source
        )
        if normalized
    }

    return tuple(sorted(result))


def load_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise LytheFilamentBindingError(
            f"missing Filament contract surface: {path}"
        )

    try:
        value = json.loads(
            path.read_text(
                encoding="utf-8"
            )
        )
    except json.JSONDecodeError as exc:
        raise LytheFilamentBindingError(
            f"invalid JSON: {path}"
        ) from exc

    if not isinstance(value, dict):
        raise LytheFilamentBindingError(
            f"expected JSON object: {path}"
        )

    return value


@dataclass(
    frozen=True,
    slots=True,
)
class ProjectionSpecification:
    projection_id: str
    source_identity: str
    projection_type: str
    inputs: tuple[str, ...]
    outputs: tuple[str, ...]
    lineage: Any
    provenance: Any
    dependencies: tuple[str, ...]
    policy: Any
    deterministic: bool = True

    def projection(
        self,
    ) -> dict[str, Any]:
        payload = {
            "schema": (
                "savant://runtime/lythe/"
                "projection-specification/1.0.0"
            ),
            "owner": OWNER,
            "execution_owner": EXECUTION_OWNER,
            "projection_id": self.projection_id,
            "source_identity": self.source_identity,
            "projection_type": self.projection_type,
            "inputs": list(self.inputs),
            "outputs": list(self.outputs),
            "lineage": self.lineage,
            "provenance": self.provenance,
            "dependencies": list(
                self.dependencies
            ),
            "policy": self.policy,
            "deterministic": (
                self.deterministic
            ),
            "execution_requested": False,
            "executed": False,
            "filesystem_mutated": False,
            "authority_effect": "none",
            "authoritative": False,
            "rebuildable": True,
        }

        payload["digest"] = digest(
            payload
        )

        return payload


@dataclass(
    frozen=True,
    slots=True,
)
class FilamentProjectionPacket:
    specification: ProjectionSpecification
    filament_contract_id: str
    filament_runtime_path: str
    accepted_inputs: tuple[str, ...]
    supported_outputs: tuple[str, ...]

    def projection(
        self,
    ) -> dict[str, Any]:
        specification = (
            self.specification.projection()
        )

        payload = {
            "schema": (
                "savant://runtime/lythe/"
                "filament-projection-packet/1.0.0"
            ),
            "owner": OWNER,
            "execution_owner": EXECUTION_OWNER,
            "specification": specification,
            "filament_contract_id": (
                self.filament_contract_id
            ),
            "filament_runtime_path": (
                self.filament_runtime_path
            ),
            "accepted_inputs": list(
                self.accepted_inputs
            ),
            "supported_outputs": list(
                self.supported_outputs
            ),
            "ready_for_execution": True,
            "executed": False,
            "filesystem_mutated": False,
            "authoritative": False,
            "authority_effect": "none",
            "rebuildable": True,
        }

        payload["digest"] = digest(
            payload
        )

        return payload


class LytheFilamentBinding:
    """
    Lythe derives deterministic projection specifications.

    Filament retains projection execution, projection runtime,
    projection workers, and generated-file emission.
    """

    def __init__(
        self,
        *,
        contract_path: Path = FILAMENT_CONTRACT,
        manifest_path: Path = FILAMENT_MANIFEST,
    ) -> None:
        self.contract_path = (
            contract_path.resolve()
        )

        self.manifest_path = (
            manifest_path.resolve()
        )

        self.contract = load_json(
            self.contract_path
        )

        self.manifest = load_json(
            self.manifest_path
        )

        self._validate_filament_contract()

    def _validate_filament_contract(
        self,
    ) -> None:
        if (
            self.contract.get("owner")
            != "filament"
        ):
            raise LytheFilamentBindingError(
                "Filament projection contract "
                "owner is not filament"
            )

        if (
            self.contract.get("function")
            != "projection"
        ):
            raise LytheFilamentBindingError(
                "Filament projection contract "
                "does not declare projection function"
            )

        runtime_path = (
            self.manifest.get(
                "runtime_path"
            )
        )

        if not normalized_identifier(
            runtime_path
        ):
            raise LytheFilamentBindingError(
                "Filament projection manifest "
                "has no runtime path"
            )

    @property
    def accepted_inputs(
        self,
    ) -> tuple[str, ...]:
        return normalized_sequence(
            self.contract.get(
                "inputs"
            )
        )

    @property
    def supported_outputs(
        self,
    ) -> tuple[str, ...]:
        return normalized_sequence(
            self.contract.get(
                "outputs"
            )
        )

    @property
    def filament_runtime_path(
        self,
    ) -> str:
        return str(
            self.manifest[
                "runtime_path"
            ]
        )

    def derive(
        self,
        *,
        projection_id: str,
        source_identity: str,
        projection_type: str,
        inputs: Sequence[str],
        outputs: Sequence[str],
        lineage: Any = None,
        provenance: Any = None,
        dependencies: Sequence[str] = (),
        policy: Any = None,
    ) -> ProjectionSpecification:
        identity = normalized_identifier(
            projection_id
        )

        source = normalized_identifier(
            source_identity
        )

        projection_kind = (
            normalized_identifier(
                projection_type
            )
        )

        if not identity:
            raise LytheFilamentBindingError(
                "projection_id is required"
            )

        if not source:
            raise LytheFilamentBindingError(
                "source_identity is required"
            )

        if not projection_kind:
            raise LytheFilamentBindingError(
                "projection_type is required"
            )

        normalized_inputs = (
            normalized_sequence(
                inputs
            )
        )

        normalized_outputs = (
            normalized_sequence(
                outputs
            )
        )

        unsupported_inputs = (
            set(normalized_inputs)
            - set(
                self.accepted_inputs
            )
        )

        if unsupported_inputs:
            raise LytheFilamentBindingError(
                "unsupported Filament input(s): "
                + ", ".join(
                    sorted(
                        unsupported_inputs
                    )
                )
            )

        unsupported_outputs = (
            set(normalized_outputs)
            - set(
                self.supported_outputs
            )
        )

        if unsupported_outputs:
            raise LytheFilamentBindingError(
                "unsupported Filament output(s): "
                + ", ".join(
                    sorted(
                        unsupported_outputs
                    )
                )
            )

        return ProjectionSpecification(
            projection_id=identity,
            source_identity=source,
            projection_type=projection_kind,
            inputs=normalized_inputs,
            outputs=normalized_outputs,
            lineage=lineage,
            provenance=provenance,
            dependencies=normalized_sequence(
                dependencies
            ),
            policy=policy,
            deterministic=True,
        )

    def packet(
        self,
        specification: ProjectionSpecification,
    ) -> FilamentProjectionPacket:
        return FilamentProjectionPacket(
            specification=specification,
            filament_contract_id=str(
                self.contract.get(
                    "id",
                    "contract.filament.projection_engine",
                )
            ),
            filament_runtime_path=(
                self.filament_runtime_path
            ),
            accepted_inputs=(
                self.accepted_inputs
            ),
            supported_outputs=(
                self.supported_outputs
            ),
        )

    def status(
        self,
    ) -> dict[str, Any]:
        payload = {
            "schema": SCHEMA,
            "owner": OWNER,
            "governing_verb": "derives",
            "execution_owner": (
                EXECUTION_OWNER
            ),
            "filament_contract": (
                str(
                    self.contract_path
                )
            ),
            "filament_manifest": (
                str(
                    self.manifest_path
                )
            ),
            "filament_runtime_path": (
                self.filament_runtime_path
            ),
            "accepted_inputs": list(
                self.accepted_inputs
            ),
            "supported_outputs": list(
                self.supported_outputs
            ),
            "lythe_derives": True,
            "lythe_executes": False,
            "lythe_emits_files": False,
            "lythe_owns_workers": False,
            "filament_executes": True,
            "filament_emits_files": True,
            "filament_owns_workers": True,
            "deterministic_specifications": True,
            "authority_effect": "none",
            "authoritative": False,
            "rebuildable": True,
        }

        payload["digest"] = digest(
            payload
        )

        return payload


def bind_filament() -> LytheFilamentBinding:
    return LytheFilamentBinding()


def main() -> int:
    binding = bind_filament()

    specification = binding.derive(
        projection_id=(
            "projection:test:"
            "lythe:filament"
        ),
        source_identity=(
            "instance:test:"
            "lythe:filament"
        ),
        projection_type="json",
        inputs=(
            "authority_db",
            "instances",
        ),
        outputs=(
            "json_projections",
        ),
        provenance={
            "source": (
                "focused-integration-check"
            ),
        },
    )

    packet = binding.packet(
        specification
    )

    result = {
        "status": binding.status(),
        "packet": packet.projection(),
    }

    print(
        json.dumps(
            result,
            ensure_ascii=False,
            sort_keys=True,
            indent=2,
            default=str,
        )
    )

    return (
        0
        if (
            result["status"][
                "lythe_executes"
            ]
            is False
            and result["status"][
                "filament_executes"
            ]
            is True
            and result["packet"][
                "executed"
            ]
            is False
        )
        else 1
    )


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
