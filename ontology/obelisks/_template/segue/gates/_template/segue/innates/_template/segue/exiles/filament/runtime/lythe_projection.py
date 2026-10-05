#!/usr/bin/env python3

from __future__ import annotations

import hashlib
import importlib.util
import json
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType
from typing import Any, Mapping


ROOT = Path("/root/savant-runtime").resolve()

FILAMENT_ROOT = (
    ROOT
    / "ontology/obelisks/_template/segue/gates/_template/segue/"
    "innates/_template/segue/exiles/filament"
).resolve()

CONTRACT_PATH = (
    FILAMENT_ROOT
    / "interface/contracts/projection_engine_contract.json"
)

MANIFEST_PATH = (
    FILAMENT_ROOT
    / "registry/manifests/projection_engine.json"
)

OWNER = "filament"
DERIVATION_OWNER = "living:lythe"

SCHEMA = "savant://runtime/filament/lythe-projection/1.0.0"


class FilamentLytheProjectionError(RuntimeError):
    pass


def canonical_json(
    value: Any,
) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )


def digest(
    value: Any,
) -> str:
    return hashlib.sha256(
        canonical_json(
            value
        ).encode(
            "utf-8"
        )
    ).hexdigest()


def load_json(
    path: Path,
) -> dict[str, Any]:
    if not path.is_file():
        raise FilamentLytheProjectionError(
            f"missing Filament projection surface: {path}"
        )

    try:
        payload = json.loads(
            path.read_text(
                encoding="utf-8"
            )
        )
    except json.JSONDecodeError as exc:
        raise FilamentLytheProjectionError(
            f"invalid JSON: {path}"
        ) from exc

    if not isinstance(
        payload,
        dict,
    ):
        raise FilamentLytheProjectionError(
            f"expected JSON object: {path}"
        )

    return payload


def normalize_string(
    value: Any,
) -> str | None:
    if value is None:
        return None

    text = str(value).strip()

    return text or None


def normalize_strings(
    value: Any,
) -> tuple[str, ...]:
    if value is None:
        return ()

    if isinstance(
        value,
        str,
    ):
        normalized = normalize_string(
            value
        )

        return (
            (normalized,)
            if normalized
            else ()
        )

    if isinstance(
        value,
        Mapping,
    ):
        values = value.keys()
    else:
        try:
            values = iter(value)
        except TypeError:
            values = (value,)

    result = {
        normalized
        for normalized in (
            normalize_string(item)
            for item in values
        )
        if normalized
    }

    return tuple(
        sorted(result)
    )


@dataclass(
    frozen=True,
    slots=True,
)
class FilamentExecutionRequest:
    projection_id: str
    source_identity: str
    projection_type: str
    inputs: tuple[str, ...]
    outputs: tuple[str, ...]
    lineage: Any
    provenance: Any
    dependencies: tuple[str, ...]
    policy: Any
    specification_digest: str

    def projection(
        self,
    ) -> dict[str, Any]:
        payload = {
            "schema": (
                "savant://runtime/filament/"
                "execution-request/1.0.0"
            ),
            "owner": OWNER,
            "derivation_owner": (
                DERIVATION_OWNER
            ),
            "projection_id": (
                self.projection_id
            ),
            "source_identity": (
                self.source_identity
            ),
            "projection_type": (
                self.projection_type
            ),
            "inputs": list(
                self.inputs
            ),
            "outputs": list(
                self.outputs
            ),
            "lineage": self.lineage,
            "provenance": (
                self.provenance
            ),
            "dependencies": list(
                self.dependencies
            ),
            "policy": self.policy,
            "specification_digest": (
                self.specification_digest
            ),
            "execution_owner": OWNER,
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


class FilamentLytheProjection:
    """
    Filament-owned intake for deterministic Lythe projection
    specifications.

    Lythe derives projection specifications.
    Filament validates execution compatibility and owns any
    actual projection execution, workers, runtime activity,
    and generated-file emission.
    """

    def __init__(
        self,
        *,
        contract_path: Path = CONTRACT_PATH,
        manifest_path: Path = MANIFEST_PATH,
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

        self._validate_surface()

    def _validate_surface(
        self,
    ) -> None:
        if (
            self.contract.get("owner")
            != OWNER
        ):
            raise FilamentLytheProjectionError(
                "projection contract owner "
                "must be filament"
            )

        if (
            self.contract.get("function")
            != "projection"
        ):
            raise FilamentLytheProjectionError(
                "projection contract function "
                "must be projection"
            )

        if (
            self.manifest.get("owner")
            != OWNER
        ):
            raise FilamentLytheProjectionError(
                "projection manifest owner "
                "must be filament"
            )

        runtime_path = normalize_string(
            self.manifest.get(
                "runtime_path"
            )
        )

        if not runtime_path:
            raise FilamentLytheProjectionError(
                "projection manifest has no runtime_path"
            )

    @property
    def accepted_inputs(
        self,
    ) -> tuple[str, ...]:
        return normalize_strings(
            self.contract.get(
                "inputs"
            )
        )

    @property
    def supported_outputs(
        self,
    ) -> tuple[str, ...]:
        return normalize_strings(
            self.contract.get(
                "outputs"
            )
        )

    @property
    def projection_runtime_path(
        self,
    ) -> Path:
        relative = Path(
            str(
                self.manifest[
                    "runtime_path"
                ]
            )
        )

        if relative.is_absolute():
            path = relative.resolve()
        else:
            path = (
                FILAMENT_ROOT
                / relative
            ).resolve()

        try:
            path.relative_to(
                FILAMENT_ROOT
            )
        except ValueError as exc:
            raise FilamentLytheProjectionError(
                "projection runtime escapes "
                "Filament ownership root"
            ) from exc

        return path

    def _extract_specification(
        self,
        packet: Mapping[str, Any],
    ) -> Mapping[str, Any]:
        specification = packet.get(
            "specification"
        )

        if not isinstance(
            specification,
            Mapping,
        ):
            raise FilamentLytheProjectionError(
                "Lythe packet has no "
                "projection specification"
            )

        if (
            specification.get("owner")
            != DERIVATION_OWNER
        ):
            raise FilamentLytheProjectionError(
                "projection specification "
                "must be owned by living:lythe"
            )

        if (
            specification.get(
                "execution_owner"
            )
            != OWNER
        ):
            raise FilamentLytheProjectionError(
                "projection specification "
                "does not delegate execution "
                "to Filament"
            )

        if (
            specification.get(
                "deterministic"
            )
            is not True
        ):
            raise FilamentLytheProjectionError(
                "Lythe specification must "
                "declare deterministic derivation"
            )

        if (
            specification.get(
                "executed"
            )
            is not False
        ):
            raise FilamentLytheProjectionError(
                "Lythe may not submit an "
                "already-executed specification"
            )

        if (
            specification.get(
                "filesystem_mutated"
            )
            is not False
        ):
            raise FilamentLytheProjectionError(
                "Lythe specification may not "
                "claim filesystem mutation"
            )

        return specification

    def accept(
        self,
        packet: Mapping[str, Any],
    ) -> FilamentExecutionRequest:
        if not isinstance(
            packet,
            Mapping,
        ):
            raise FilamentLytheProjectionError(
                "packet must be a mapping"
            )

        if (
            packet.get("owner")
            != DERIVATION_OWNER
        ):
            raise FilamentLytheProjectionError(
                "packet owner must be living:lythe"
            )

        if (
            packet.get(
                "execution_owner"
            )
            != OWNER
        ):
            raise FilamentLytheProjectionError(
                "packet execution owner "
                "must be filament"
            )

        if (
            packet.get(
                "executed"
            )
            is not False
        ):
            raise FilamentLytheProjectionError(
                "incoming packet must not "
                "claim prior execution"
            )

        specification = (
            self._extract_specification(
                packet
            )
        )

        projection_id = (
            normalize_string(
                specification.get(
                    "projection_id"
                )
            )
        )

        source_identity = (
            normalize_string(
                specification.get(
                    "source_identity"
                )
            )
        )

        projection_type = (
            normalize_string(
                specification.get(
                    "projection_type"
                )
            )
        )

        if not projection_id:
            raise FilamentLytheProjectionError(
                "projection_id is required"
            )

        if not source_identity:
            raise FilamentLytheProjectionError(
                "source_identity is required"
            )

        if not projection_type:
            raise FilamentLytheProjectionError(
                "projection_type is required"
            )

        inputs = normalize_strings(
            specification.get(
                "inputs"
            )
        )

        outputs = normalize_strings(
            specification.get(
                "outputs"
            )
        )

        unsupported_inputs = (
            set(inputs)
            - set(
                self.accepted_inputs
            )
        )

        if unsupported_inputs:
            raise FilamentLytheProjectionError(
                "unsupported Filament input(s): "
                + ", ".join(
                    sorted(
                        unsupported_inputs
                    )
                )
            )

        unsupported_outputs = (
            set(outputs)
            - set(
                self.supported_outputs
            )
        )

        if unsupported_outputs:
            raise FilamentLytheProjectionError(
                "unsupported Filament output(s): "
                + ", ".join(
                    sorted(
                        unsupported_outputs
                    )
                )
            )

        specification_digest = (
            normalize_string(
                specification.get(
                    "digest"
                )
            )
        )

        if not specification_digest:
            raise FilamentLytheProjectionError(
                "Lythe specification digest "
                "is required"
            )

        return FilamentExecutionRequest(
            projection_id=projection_id,
            source_identity=source_identity,
            projection_type=projection_type,
            inputs=inputs,
            outputs=outputs,
            lineage=specification.get(
                "lineage"
            ),
            provenance=specification.get(
                "provenance"
            ),
            dependencies=normalize_strings(
                specification.get(
                    "dependencies"
                )
            ),
            policy=specification.get(
                "policy"
            ),
            specification_digest=(
                specification_digest
            ),
        )

    def load_projection_runtime(
        self,
    ) -> ModuleType:
        path = (
            self.projection_runtime_path
        )

        if not path.is_file():
            raise FilamentLytheProjectionError(
                f"Filament projection runtime missing: {path}"
            )

        module_name = (
            "filament_projection_engine"
        )

        spec = (
            importlib.util
            .spec_from_file_location(
                module_name,
                path,
            )
        )

        if (
            spec is None
            or spec.loader is None
        ):
            raise FilamentLytheProjectionError(
                "unable to load Filament "
                "projection runtime"
            )

        module = (
            importlib.util
            .module_from_spec(
                spec
            )
        )

        spec.loader.exec_module(
            module
        )

        return module

    def status(
        self,
    ) -> dict[str, Any]:
        runtime_path = (
            self.projection_runtime_path
        )

        payload = {
            "schema": SCHEMA,
            "owner": OWNER,
            "derivation_owner": (
                DERIVATION_OWNER
            ),
            "contract_id": (
                self.contract.get(
                    "id"
                )
            ),
            "manifest_id": (
                self.manifest.get(
                    "id"
                )
            ),
            "accepted_inputs": list(
                self.accepted_inputs
            ),
            "supported_outputs": list(
                self.supported_outputs
            ),
            "projection_runtime_path": (
                str(runtime_path)
            ),
            "projection_runtime_present": (
                runtime_path.is_file()
            ),
            "lythe_derives": True,
            "lythe_executes": False,
            "filament_accepts_specifications": True,
            "filament_executes": True,
            "filament_owns_workers": True,
            "filament_emits_files": True,
            "authority_effect": "none",
            "authoritative": False,
            "rebuildable": True,
        }

        payload["digest"] = digest(
            payload
        )

        return payload


def lythe_projection(
) -> FilamentLytheProjection:
    return FilamentLytheProjection()


def main() -> int:
    runtime = lythe_projection()

    status = runtime.status()

    print(
        json.dumps(
            status,
            ensure_ascii=False,
            sort_keys=True,
            indent=2,
            default=str,
        )
    )

    return (
        0
        if (
            status[
                "projection_runtime_present"
            ]
            and status[
                "lythe_executes"
            ]
            is False
            and status[
                "filament_executes"
            ]
            is True
        )
        else 1
    )


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
