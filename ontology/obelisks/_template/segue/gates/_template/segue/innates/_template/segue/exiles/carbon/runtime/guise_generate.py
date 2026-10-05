#!/usr/bin/env python3
from __future__ import annotations

from typing import Any, Mapping, Sequence

from guise import (
    OWNER,
    SCHEMA,
    SPECIALIZATION,
    CharacterGraph,
    Guise,
    GuiseError,
    digest,
)
from guise_provider import (
    GuiseProviderRegistry,
)


class GuiseGenerationError(GuiseError):
    pass


class GuiseGenerator:
    def __init__(
        self,
        guise: Guise,
        registry: GuiseProviderRegistry,
    ) -> None:
        self.guise = guise
        self.registry = registry

    def generate(
        self,
        *,
        graph: CharacterGraph,
        provider_id: str,
        request: Mapping[str, Any],
    ) -> dict[str, Any]:
        provider = self.registry.get(
            provider_id
        )

        request_value = dict(request)

        prompt_packet = {
            "mode": "character_generation",
            "character_id": graph.character_id,
            "request": request_value,
            "manifest": self.guise.manifest,
            "rules": {
                "do_not_assert_generated_material_as_fact": True,
                "do_not_mutate_accepted_authority": True,
                "preserve_unknowns": True,
                "preserve_alternatives": True,
                "preserve_contradictions": True,
                "avoid_diagnostic_overreach": True,
                "avoid_trait_determinism": True,
                "avoid_cliche_compression": True,
                "require_author_acceptance": True,
            },
        }

        provider_result = provider.interpret(
            character_id=graph.character_id,
            text="",
            source={
                "kind": "generation_request",
                "authority_effect": "none",
            },
            manifest={
                **self.guise.manifest,
                "generation_request": request_value,
                "generation_rules": (
                    prompt_packet["rules"]
                ),
            },
        )

        hypotheses = provider_result.get(
            "hypotheses",
            provider_result.get(
                "candidates",
                [],
            ),
        )

        if not isinstance(hypotheses, Sequence) or isinstance(
            hypotheses,
            (str, bytes, bytearray),
        ):
            raise GuiseGenerationError(
                "provider hypotheses must be a sequence"
            )

        normalized = []

        for index, hypothesis in enumerate(
            hypotheses
        ):
            if not isinstance(
                hypothesis,
                Mapping,
            ):
                normalized.append(
                    {
                        "id": f"hypothesis:{index}",
                        "value": repr(
                            hypothesis
                        ),
                        "status": "rejected",
                        "reason": (
                            "hypothesis must be a mapping"
                        ),
                    }
                )
                continue

            item = dict(hypothesis)

            item["authoritative"] = False
            item["accepted"] = False
            item["requires_acceptance"] = True
            item["authority_effect"] = "none"

            normalized.append(item)

        result = {
            "schema": SCHEMA,
            "owner": OWNER,
            "specialization": SPECIALIZATION,
            "operation": "character_generation",
            "character_id": graph.character_id,
            "provider_id": provider.provider_id,
            "request": request_value,
            "hypotheses": normalized,
            "hypothesis_count": len(
                normalized
            ),
            "character_mutated": False,
            "automatic_canonization": False,
            "requires_author_acceptance": True,
            "authority_effect": "none",
        }

        result["projection_digest"] = digest(
            result
        )

        return result
