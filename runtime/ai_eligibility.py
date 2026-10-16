#!/usr/bin/env python3

from __future__ import annotations

from typing import Any, Mapping

from runtime.ai_capabilities import AICapabilityRegistry
from runtime.ai_contract import AIContract, contract_from_mapping


class AIEligibility:
    def __init__(
        self,
        capabilities: AICapabilityRegistry | None = None,
    ) -> None:
        self.capabilities = (
            capabilities
            or AICapabilityRegistry()
        )

    def contract_for(
        self,
        record: Mapping[str, Any],
    ) -> AIContract:
        orchestration = record.get(
            "orchestration",
            {},
        )

        if not isinstance(
            orchestration,
            Mapping,
        ):
            orchestration = {}

        opus_ready = (
            orchestration.get(
                "opus_ready"
            )
            is True
        )

        ai = record.get("ai")

        if ai is None:
            ai = orchestration.get("ai")

        if ai is not None and not isinstance(
            ai,
            Mapping,
        ):
            raise ValueError(
                "AI contract must be an object"
            )

        return contract_from_mapping(
            ai,
            opus_ready=opus_ready,
        )

    def resolve(
        self,
        record: Mapping[str, Any],
    ) -> dict[str, Any]:
        contract = self.contract_for(record)

        available = set(
            self.capabilities.capabilities()
        )

        declared = set(
            contract.capabilities
        )

        required = set(
            contract.required_capabilities
        )

        preferred = set(
            contract.preferred_capabilities
        )

        usable = declared & available
        missing_required = (
            required - available
        )

        providers: dict[
            str,
            list[str],
        ] = {}

        for capability in sorted(
            usable
        ):
            providers[capability] = list(
                self.capabilities.providers_for(
                    capability
                )
            )

        ai_active = bool(
            contract.eligible
            and usable
        )

        native_operational = bool(
            contract.native_fallback
        )

        return {
            "eligible": contract.eligible,
            "ai_active": ai_active,
            "mode": (
                self.capabilities.mode()
                if ai_active
                else "native"
            ),
            "native_operational": (
                native_operational
            ),
            "declared_capabilities": sorted(
                declared
            ),
            "usable_capabilities": sorted(
                usable
            ),
            "required_capabilities": sorted(
                required
            ),
            "missing_required_capabilities": sorted(
                missing_required
            ),
            "preferred_capabilities": sorted(
                preferred
            ),
            "providers": providers,
            "authority_effect": (
                contract.authority_effect
            ),
            "mutation_effect": (
                contract.mutation_effect
            ),
            "provider_neutral": (
                contract.provider_neutral
            ),
            "graceful_degradation": (
                contract.graceful_degradation
            ),
            "ready": bool(
                native_operational
                and not missing_required
            ),
        }
