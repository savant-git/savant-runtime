#!/usr/bin/env python3

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping


VALID_AUTHORITY_EFFECTS = frozenset({"none"})
VALID_MUTATION_EFFECTS = frozenset({"none"})


class AIContractError(ValueError):
    pass


def _normalized(values: Iterable[str]) -> tuple[str, ...]:
    return tuple(
        sorted(
            {
                str(value).strip()
                for value in values
                if str(value).strip()
            }
        )
    )


@dataclass(frozen=True, slots=True)
class AIContract:
    eligible: bool = False
    capabilities: tuple[str, ...] = field(default_factory=tuple)
    required_capabilities: tuple[str, ...] = field(default_factory=tuple)
    preferred_capabilities: tuple[str, ...] = field(default_factory=tuple)
    authority_effect: str = "none"
    mutation_effect: str = "none"
    native_fallback: bool = True
    provider_neutral: bool = True
    graceful_degradation: bool = True
    receipt_policy: str = "projected"
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "capabilities",
            _normalized(self.capabilities),
        )
        object.__setattr__(
            self,
            "required_capabilities",
            _normalized(self.required_capabilities),
        )
        object.__setattr__(
            self,
            "preferred_capabilities",
            _normalized(self.preferred_capabilities),
        )

        if self.authority_effect not in VALID_AUTHORITY_EFFECTS:
            raise AIContractError(
                "AI contracts may not grant authority"
            )

        if self.mutation_effect not in VALID_MUTATION_EFFECTS:
            raise AIContractError(
                "AI contracts may not grant mutation rights"
            )

        if self.eligible and not self.native_fallback:
            raise AIContractError(
                "AI-eligible Savant elements require native fallback"
            )

        if self.eligible and not self.graceful_degradation:
            raise AIContractError(
                "AI-eligible Savant elements require graceful degradation"
            )

        required = set(self.required_capabilities)
        declared = set(self.capabilities)

        if not required.issubset(declared):
            raise AIContractError(
                "required capabilities must be declared capabilities"
            )

        preferred = set(self.preferred_capabilities)

        if not preferred.issubset(declared):
            raise AIContractError(
                "preferred capabilities must be declared capabilities"
            )

    @classmethod
    def native(cls) -> "AIContract":
        return cls()

    @classmethod
    def eligible_contract(
        cls,
        capabilities: Iterable[str],
        *,
        required: Iterable[str] = (),
        preferred: Iterable[str] = (),
        metadata: Mapping[str, Any] | None = None,
    ) -> "AIContract":
        return cls(
            eligible=True,
            capabilities=_normalized(capabilities),
            required_capabilities=_normalized(required),
            preferred_capabilities=_normalized(preferred),
            authority_effect="none",
            mutation_effect="none",
            native_fallback=True,
            provider_neutral=True,
            graceful_degradation=True,
            receipt_policy="projected",
            metadata=dict(metadata or {}),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "eligible": self.eligible,
            "capabilities": list(self.capabilities),
            "required_capabilities": list(
                self.required_capabilities
            ),
            "preferred_capabilities": list(
                self.preferred_capabilities
            ),
            "authority_effect": self.authority_effect,
            "mutation_effect": self.mutation_effect,
            "native_fallback": self.native_fallback,
            "provider_neutral": self.provider_neutral,
            "graceful_degradation": self.graceful_degradation,
            "receipt_policy": self.receipt_policy,
            "metadata": dict(self.metadata),
        }


def contract_from_mapping(
    value: Mapping[str, Any] | None,
    *,
    opus_ready: bool = False,
) -> AIContract:
    if not value:
        if opus_ready:
            return AIContract.eligible_contract(())
        return AIContract.native()

    eligible = bool(
        value.get(
            "eligible",
            opus_ready,
        )
    )

    if not eligible:
        return AIContract.native()

    return AIContract(
        eligible=True,
        capabilities=_normalized(
            value.get("capabilities", ())
        ),
        required_capabilities=_normalized(
            value.get(
                "required_capabilities",
                (),
            )
        ),
        preferred_capabilities=_normalized(
            value.get(
                "preferred_capabilities",
                (),
            )
        ),
        authority_effect=str(
            value.get(
                "authority_effect",
                "none",
            )
        ),
        mutation_effect=str(
            value.get(
                "mutation_effect",
                "none",
            )
        ),
        native_fallback=bool(
            value.get(
                "native_fallback",
                True,
            )
        ),
        provider_neutral=bool(
            value.get(
                "provider_neutral",
                True,
            )
        ),
        graceful_degradation=bool(
            value.get(
                "graceful_degradation",
                True,
            )
        ),
        receipt_policy=str(
            value.get(
                "receipt_policy",
                "projected",
            )
        ),
        metadata=dict(
            value.get(
                "metadata",
                {},
            )
        ),
    )
