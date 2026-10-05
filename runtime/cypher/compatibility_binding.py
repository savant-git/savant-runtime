#!/usr/bin/env python3

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Callable, Mapping

import yaml

from .engine import Cypher, CypherError


OWNER = "living:cypher"
SCHEMA = "savant://runtime/cypher/compatibility-binding/1.0.0"


class CypherCompatibilityBindingError(RuntimeError):
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


def normalize_identifier(value: Any) -> str | None:
    if value is None:
        return None

    text = str(value).strip()
    return text or None


@dataclass(frozen=True, slots=True)
class CompatibilityRequest:
    source_type: str
    target_type: str
    payload: Any
    authority: Any
    lineage: Any
    provenance: Any
    metadata: dict[str, Any]
    substance_owner: str | None
    transport_owner: str | None

    def projection(self) -> dict[str, Any]:
        payload = {
            "schema": (
                "savant://runtime/cypher/"
                "compatibility-request/1.0.0"
            ),
            "owner": OWNER,
            "source_type": self.source_type,
            "target_type": self.target_type,
            "payload": self.payload,
            "authority": self.authority,
            "lineage": self.lineage,
            "provenance": self.provenance,
            "metadata": self.metadata,
            "substance_owner": self.substance_owner,
            "transport_owner": self.transport_owner,
            "cypher_owns_substance": False,
            "cypher_owns_transport": False,
            "authority_effect": "none",
            "authoritative": False,
            "rebuildable": True,
        }

        payload["digest"] = digest(payload)
        return payload


@dataclass(frozen=True, slots=True)
class CompatibilityResult:
    request: CompatibilityRequest
    translation: Mapping[str, Any]

    def projection(self) -> dict[str, Any]:
        translated = dict(self.translation)

        payload = {
            "schema": (
                "savant://runtime/cypher/"
                "compatibility-result/1.0.0"
            ),
            "owner": OWNER,
            "request": self.request.projection(),
            "translation": translated,
            "source_type": self.request.source_type,
            "target_type": self.request.target_type,
            "substance_owner": self.request.substance_owner,
            "transport_owner": self.request.transport_owner,
            "authority_preserved": True,
            "lineage_preserved": True,
            "provenance_preserved": True,
            "cypher_owns_substance": False,
            "cypher_owns_transport": False,
            "transport_executed": False,
            "authority_effect": "none",
            "authoritative": False,
            "rebuildable": True,
        }

        payload["digest"] = digest(payload)
        return payload


class CypherCompatibilityBinding:
    """
    Compatibility and translation facade over Cypher.

    Cypher owns exchange interpretation mechanics only.

    It may:
      - normalize;
      - serialize and deserialize;
      - select registered adapters;
      - translate between typed interfaces;
      - adapt versions;
      - preserve unknown fields;
      - preserve authority, lineage, and provenance;
      - detect translation loss.

    It may not:
      - acquire ownership of translated substance;
      - acquire transport ownership;
      - execute network/message transport;
      - manufacture or mutate authority.
    """

    def __init__(
        self,
        *,
        cypher: Cypher | None = None,
    ) -> None:
        self.cypher = (
            cypher
            if cypher is not None
            else Cypher()
        )

    def register_adapter(
        self,
        source_type: str,
        target_type: str,
        adapter: Callable[[Any], Any],
    ) -> None:
        try:
            self.cypher.register_adapter(
                source_type,
                target_type,
                adapter,
            )
        except CypherError as exc:
            raise CypherCompatibilityBindingError(
                str(exc)
            ) from exc

    def request(
        self,
        *,
        source_type: str,
        target_type: str,
        payload: Any,
        authority: Any = None,
        lineage: Any = None,
        provenance: Any = None,
        metadata: Mapping[str, Any] | None = None,
        substance_owner: str | None = None,
        transport_owner: str | None = None,
    ) -> CompatibilityRequest:
        source = normalize_identifier(
            source_type
        )
        target = normalize_identifier(
            target_type
        )

        if not source:
            raise CypherCompatibilityBindingError(
                "source_type is required"
            )

        if not target:
            raise CypherCompatibilityBindingError(
                "target_type is required"
            )

        return CompatibilityRequest(
            source_type=source,
            target_type=target,
            payload=payload,
            authority=authority,
            lineage=lineage,
            provenance=provenance,
            metadata=dict(
                metadata or {}
            ),
            substance_owner=(
                normalize_identifier(
                    substance_owner
                )
            ),
            transport_owner=(
                normalize_identifier(
                    transport_owner
                )
            ),
        )

    def translate(
        self,
        request: CompatibilityRequest,
    ) -> CompatibilityResult:
        try:
            result = self.cypher.translate(
                request.payload,
                source_type=request.source_type,
                target_type=request.target_type,
                authority=request.authority,
                lineage=request.lineage,
                provenance=request.provenance,
                metadata={
                    **request.metadata,
                    "substance_owner": (
                        request.substance_owner
                    ),
                    "transport_owner": (
                        request.transport_owner
                    ),
                    "cypher_owns_substance": False,
                    "cypher_owns_transport": False,
                },
            )
        except CypherError as exc:
            raise CypherCompatibilityBindingError(
                str(exc)
            ) from exc

        if not isinstance(
            result,
            Mapping,
        ):
            raise CypherCompatibilityBindingError(
                "Cypher translation did not return "
                "a mapping projection"
            )

        return CompatibilityResult(
            request=request,
            translation=dict(result),
        )

    def explain(
        self,
        *,
        source_type: str,
        target_type: str,
    ) -> dict[str, Any]:
        try:
            explanation = (
                self.cypher.explain_route(
                    source_type,
                    target_type,
                )
            )
        except CypherError as exc:
            raise CypherCompatibilityBindingError(
                str(exc)
            ) from exc

        payload = {
            "schema": (
                "savant://runtime/cypher/"
                "compatibility-explanation/1.0.0"
            ),
            "owner": OWNER,
            "source_type": source_type,
            "target_type": target_type,
            "route": explanation,
            "cypher_owns_substance": False,
            "cypher_owns_transport": False,
            "authority_effect": "none",
            "authoritative": False,
            "rebuildable": True,
        }

        payload["digest"] = digest(payload)
        return payload

    def status(self) -> dict[str, Any]:
        health = self.cypher.health()
        validation = self.cypher.validate()

        payload = {
            "schema": SCHEMA,
            "owner": OWNER,
            "governing_verb": "translates",
            "health": health,
            "validation": validation,
            "routes": list(
                self.cypher.routes()
            ),
            "normalization": True,
            "serialization": True,
            "deserialization": True,
            "typed_translation": True,
            "adapter_selection": True,
            "version_adaptation": True,
            "unknown_field_preservation": True,
            "authority_preservation": True,
            "lineage_preservation": True,
            "provenance_preservation": True,
            "loss_detection": True,
            "cypher_owns_substance": False,
            "cypher_owns_transport": False,
            "cypher_executes_transport": False,
            "cypher_manufactures_authority": False,
            "cypher_mutates_authority": False,
            "authority_effect": "none",
            "authoritative": False,
            "rebuildable": True,
        }

        payload["digest"] = digest(payload)
        return payload


def bind_compatibility(
) -> CypherCompatibilityBinding:
    return CypherCompatibilityBinding()


def _json_to_yaml(value: Any) -> Any:
    serialized = yaml.safe_dump(
        value,
        allow_unicode=True,
        sort_keys=True,
    )

    return yaml.safe_load(
        serialized
    )


def main() -> int:
    binding = bind_compatibility()

    binding.register_adapter(
        "json",
        "yaml",
        _json_to_yaml,
    )

    request = binding.request(
        source_type="json",
        target_type="yaml",
        payload={
            "example": True,
        },
        authority={
            "class": "admitted-evidence",
        },
        lineage={
            "parent": "example:source",
        },
        provenance={
            "source": "focused-self-check",
        },
        substance_owner="example:owner",
        transport_owner="example:transport",
    )

    result = binding.translate(
        request
    ).projection()

    status = binding.status()

    assert result["translation"][
        "authority"
    ] == request.authority

    assert result["translation"][
        "lineage"
    ] == request.lineage

    assert result["translation"][
        "provenance"
    ] == request.provenance

    print(
        json.dumps(
            {
                "status": status,
                "result": result,
            },
            ensure_ascii=False,
            sort_keys=True,
            indent=2,
            default=str,
        )
    )

    return (
        0
        if (
            status["cypher_owns_substance"]
            is False
            and status["cypher_owns_transport"]
            is False
            and status["cypher_executes_transport"]
            is False
            and result["transport_executed"]
            is False
            and result["authority_effect"]
            == "none"
        )
        else 1
    )


if __name__ == "__main__":
    raise SystemExit(main())
