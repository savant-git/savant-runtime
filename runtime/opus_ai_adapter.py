#!/usr/bin/env python3

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable


ROOT = Path("/root/savant-runtime")

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from runtime.ai_capabilities import AICapabilityRegistry
from runtime.ai_eligibility import AIEligibility


class OpusAIAdapterError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class OpusProviderSelection:
    capability: str
    providers: tuple[str, ...]
    selected: str | None
    mode: str
    native_fallback: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "capability": self.capability,
            "providers": list(self.providers),
            "selected": self.selected,
            "mode": self.mode,
            "native_fallback": self.native_fallback,
        }


class OpusAIAdapter:
    """
    Provider-neutral capability adapter for Opus.

    This adapter owns no provider execution and no routing policy.

    It answers only:

        - which configured providers expose a capability;
        - whether a named provider is usable;
        - which provider is the deterministic first candidate when
          no higher-order Opus routing policy is supplied;
        - whether an element's AI contract can currently be satisfied.

    Current Opus remains owner of actual provider/model selection,
    execution, retries, fallback, cost policy and latency policy.
    """

    def __init__(
        self,
        registry: AICapabilityRegistry | None = None,
    ) -> None:
        self.registry = (
            registry
            or AICapabilityRegistry()
        )

        self.eligibility = AIEligibility(
            self.registry
        )

    def mode(self) -> str:
        return self.registry.mode()

    def has_provider(
        self,
        provider: str,
    ) -> bool:
        state = self.registry.provider_state(
            str(provider).strip()
        )

        return state.usable

    def has_capability(
        self,
        capability: str,
    ) -> bool:
        return bool(
            self.providers_for(
                capability
            )
        )

    def providers_for(
        self,
        capability: str,
    ) -> tuple[str, ...]:
        return self.registry.providers_for(
            str(capability).strip()
        )

    def select(
        self,
        capability: str,
        *,
        preferred_providers: Iterable[str] = (),
    ) -> OpusProviderSelection:
        capability = str(
            capability
        ).strip()

        if not capability:
            raise OpusAIAdapterError(
                "capability is required"
            )

        available = self.providers_for(
            capability
        )

        available_set = set(
            available
        )

        preferred = tuple(
            dict.fromkeys(
                str(provider).strip()
                for provider in preferred_providers
                if str(provider).strip()
            )
        )

        selected: str | None = None

        for provider in preferred:
            if provider in available_set:
                selected = provider
                break

        if (
            selected is None
            and available
        ):
            selected = available[0]

        return OpusProviderSelection(
            capability=capability,
            providers=available,
            selected=selected,
            mode=(
                self.registry.mode()
                if selected
                else "native"
            ),
            native_fallback=True,
        )

    def resolve_element(
        self,
        record: dict[str, Any],
    ) -> dict[str, Any]:
        return self.eligibility.resolve(
            record
        )

    def status(
        self,
    ) -> dict[str, Any]:
        return {
            "schema": (
                "savant.opus-ai-adapter.v1"
            ),
            "owner": "opus",
            "mode": self.mode(),
            "usable_providers": list(
                self.registry.usable_providers()
            ),
            "capabilities": list(
                self.registry.capabilities()
            ),
            "native_fallback": True,
            "authority_effect": "none",
            "mutation_effect": "none",
            "execution_owner": "opus",
            "routing_owner": "opus",
        }


def main() -> int:
    adapter = OpusAIAdapter()

    print(
        json.dumps(
            adapter.status(),
            indent=2,
            sort_keys=True,
        )
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
