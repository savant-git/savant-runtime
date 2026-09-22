from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from typing import Any, Mapping, Sequence

from runtime.noumenon.integration import (
    DevelopmentalIntegration,
    MECHANISMS,
)
from runtime.noumenon.integration_runtime import (
    IntegrationRuntimeResult,
)


SCHEMA = "savant://noumenon/completion/1"


def _canonical_json(
    value: Any,
) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def _digest(
    value: Any,
) -> str:
    return sha256(
        _canonical_json(value).encode("utf-8")
    ).hexdigest()


@dataclass(frozen=True, slots=True)
class CompletionReceipt:
    noumenon_id: str
    generation: int
    integration_ref: str
    present_mechanisms: tuple[str, ...]
    absent_mechanisms: tuple[str, ...]
    causal_refs: tuple[str, ...]
    complete: bool

    def projection(
        self,
    ) -> dict[str, Any]:
        body: dict[str, Any] = {
            "schema": SCHEMA,
            "noumenon_id": self.noumenon_id,
            "generation": self.generation,
            "integration_ref": (
                self.integration_ref
            ),
            "present_mechanisms": list(
                self.present_mechanisms
            ),
            "absent_mechanisms": list(
                self.absent_mechanisms
            ),
            "causal_refs": list(
                self.causal_refs
            ),
            "complete": self.complete,
            "completion_is_authority": False,
            "authority_transferred": False,
            "automatic_identity_mutation": False,
            "derived": True,
            "authoritative": False,
            "authority_effect": "none",
        }

        body["digest"] = _digest(body)
        return body


def completion_receipt(
    integration: DevelopmentalIntegration,
    *,
    required_mechanisms: Sequence[str] = (),
) -> CompletionReceipt:
    required = (
        frozenset(required_mechanisms)
        if required_mechanisms
        else MECHANISMS
    )

    unknown = required - MECHANISMS

    if unknown:
        raise ValueError(
            "unknown required mechanisms: "
            + ", ".join(sorted(unknown))
        )

    present = frozenset(
        item.mechanism
        for item in integration.mechanisms
    )

    absent = required - present

    integration_ref = str(
        integration.projection()["digest"]
    )

    return CompletionReceipt(
        noumenon_id=integration.noumenon_id,
        generation=integration.generation,
        integration_ref=integration_ref,
        present_mechanisms=tuple(
            sorted(present & required)
        ),
        absent_mechanisms=tuple(
            sorted(absent)
        ),
        causal_refs=tuple(
            dict.fromkeys(
                (
                    integration_ref,
                    *integration.causal_refs,
                )
            )
        ),
        complete=not absent,
    )


def validate_runtime_result(
    result: IntegrationRuntimeResult,
) -> bool:
    integration = result.integration
    transition = result.transition

    integration_ref = str(
        integration.projection()["digest"]
    )

    if (
        transition.successor_ref
        != integration_ref
    ):
        return False

    if (
        transition.noumenon_id
        != integration.noumenon_id
    ):
        return False

    if (
        transition.successor_generation
        != integration.generation
    ):
        return False

    if (
        integration_ref
        not in transition.causal_refs
    ):
        return False

    return True


def completion_projection(
    receipt: CompletionReceipt,
) -> Mapping[str, Any]:
    projection = receipt.projection()

    return {
        **projection,
        "persistent_individual": (
            receipt.noumenon_id
        ),
        "mechanism_coverage": len(
            receipt.present_mechanisms
        ),
        "missing_mechanism_count": len(
            receipt.absent_mechanisms
        ),
        "model_is_identity": False,
        "provider_is_identity": False,
        "derived_state_is_external_fact": False,
        "causal_continuity_required": True,
        "authority_isolation_preserved": True,
    }
