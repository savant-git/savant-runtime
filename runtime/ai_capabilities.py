#!/usr/bin/env python3

from __future__ import annotations

import argparse
import hashlib
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

import yaml


ROOT = Path("/root/savant-runtime")
DEFAULT_CONFIG = ROOT / "config" / "ai_capabilities.yaml"


class AICapabilityError(RuntimeError):
    pass


def _stable_json(value: Any) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )


def _digest(value: Any) -> str:
    return hashlib.sha256(
        _stable_json(value).encode("utf-8")
    ).hexdigest()


@dataclass(frozen=True, slots=True)
class ProviderState:
    provider: str
    configured: bool
    usable: bool
    capabilities: tuple[str, ...]
    secret_names: tuple[str, ...]
    reason: str

    def public(self) -> dict[str, Any]:
        return {
            "provider": self.provider,
            "configured": self.configured,
            "usable": self.usable,
            "capabilities": list(self.capabilities),
            "secret_names": list(self.secret_names),
            "reason": self.reason,
        }


class AICapabilityRegistry:
    """
    Provider-neutral AI capability discovery.

    Invariants:
    - no API key value is returned, persisted, logged, or hashed;
    - zero providers is a valid native Savant state;
    - provider presence augments capability only;
    - AI availability creates no authority or mutation right;
    - consumers depend on capabilities, not provider names.
    """

    def __init__(
        self,
        config_path: Path | str = DEFAULT_CONFIG,
        environ: Mapping[str, str] | None = None,
    ) -> None:
        self.config_path = Path(config_path).resolve()
        self.environ = dict(os.environ if environ is None else environ)
        self.config = self._load()
        self._validate()

    def _load(self) -> dict[str, Any]:
        if not self.config_path.exists():
            raise AICapabilityError(
                f"AI capability config not found: {self.config_path}"
            )

        with self.config_path.open("r", encoding="utf-8") as handle:
            data = yaml.safe_load(handle)

        if not isinstance(data, dict):
            raise AICapabilityError(
                "AI capability configuration must be an object"
            )

        return data

    def _validate(self) -> None:
        policy = self.config.get("policy")
        providers = self.config.get("providers")
        eligibility = self.config.get("eligibility")

        if not isinstance(policy, dict):
            raise AICapabilityError("policy must be an object")

        if policy.get("activation") != "auto":
            raise AICapabilityError(
                "AI activation must remain auto for this contract"
            )

        if policy.get("native_fallback") != "required":
            raise AICapabilityError(
                "native fallback must remain required"
            )

        if policy.get("authority_from_ai") != "forbidden":
            raise AICapabilityError(
                "AI must not manufacture authority"
            )

        if policy.get("mutation_from_ai") != "forbidden":
            raise AICapabilityError(
                "AI availability must not grant mutation"
            )

        if not isinstance(providers, dict) or not providers:
            raise AICapabilityError(
                "providers must be a non-empty object"
            )

        if not isinstance(eligibility, dict):
            raise AICapabilityError(
                "eligibility must be an object"
            )

        for name, provider in providers.items():
            if not isinstance(provider, dict):
                raise AICapabilityError(
                    f"provider must be an object: {name}"
                )

            secret_env = provider.get("secret_env", [])
            capabilities = provider.get("capabilities", [])

            if not isinstance(secret_env, list) or not secret_env:
                raise AICapabilityError(
                    f"secret_env required: {name}"
                )

            if not isinstance(capabilities, list):
                raise AICapabilityError(
                    f"capabilities must be a list: {name}"
                )

    def _secret_present(self, name: str) -> bool:
        return bool(str(self.environ.get(name, "")).strip())

    def provider_state(self, name: str) -> ProviderState:
        providers = self.config["providers"]

        if name not in providers:
            raise AICapabilityError(
                f"unknown AI provider: {name}"
            )

        provider = providers[name]
        secret_names = tuple(
            str(value)
            for value in provider.get("secret_env", [])
        )

        secret_policy = str(
            provider.get("secret_policy", "all")
        ).lower()

        present = [
            self._secret_present(secret)
            for secret in secret_names
        ]

        if secret_policy == "any":
            configured = any(present)
        elif secret_policy == "all":
            configured = all(present)
        else:
            raise AICapabilityError(
                f"invalid secret_policy for {name}: {secret_policy}"
            )

        enabled = provider.get("enabled", "auto")

        if enabled is False:
            usable = False
            reason = "disabled"
        elif enabled not in (True, "auto"):
            raise AICapabilityError(
                f"invalid enabled value for {name}"
            )
        elif configured:
            usable = True
            reason = "credential-present"
        else:
            usable = False
            reason = "credential-absent"

        return ProviderState(
            provider=name,
            configured=configured,
            usable=usable,
            capabilities=tuple(
                sorted(
                    {
                        str(value)
                        for value in provider.get(
                            "capabilities",
                            [],
                        )
                    }
                )
            ),
            secret_names=secret_names,
            reason=reason,
        )

    def provider_states(self) -> dict[str, ProviderState]:
        return {
            name: self.provider_state(name)
            for name in sorted(self.config["providers"])
        }

    def usable_providers(self) -> tuple[str, ...]:
        return tuple(
            name
            for name, state in self.provider_states().items()
            if state.usable
        )

    def capabilities(self) -> tuple[str, ...]:
        values: set[str] = set()

        for state in self.provider_states().values():
            if state.usable:
                values.update(state.capabilities)

        return tuple(sorted(values))

    def providers_for(
        self,
        capability: str,
    ) -> tuple[str, ...]:
        capability = str(capability).strip()

        return tuple(
            name
            for name, state in self.provider_states().items()
            if state.usable
            and capability in state.capabilities
        )

    def mode(self) -> str:
        count = len(self.usable_providers())

        if count == 0:
            return "native"
        if count == 1:
            return "augmented"
        return "orchestrated"

    def element_contract(
        self,
        *,
        opus_ready: bool,
        capabilities: list[str] | tuple[str, ...] = (),
    ) -> dict[str, Any]:
        profile_name = "opus_ready" if opus_ready else "default"
        profile = dict(self.config["eligibility"][profile_name])

        requested = tuple(
            sorted({str(value) for value in capabilities})
        )

        available = set(self.capabilities())

        return {
            "eligible": bool(profile.get("eligible", False)),
            "requested_capabilities": list(requested),
            "available_capabilities": [
                value
                for value in requested
                if value in available
            ],
            "missing_capabilities": [
                value
                for value in requested
                if value not in available
            ],
            "authority_effect": profile.get(
                "authority_effect",
                "none",
            ),
            "mutation_effect": profile.get(
                "mutation_effect",
                "none",
            ),
            "native_fallback": profile.get(
                "native_fallback",
                "required",
            ),
            "provider_neutral": bool(
                profile.get("provider_neutral", True)
            ),
        }

    def projection(self) -> dict[str, Any]:
        providers = {
            name: state.public()
            for name, state in self.provider_states().items()
        }

        projection = {
            "schema": "savant.ai-capabilities.v1",
            "mode": self.mode(),
            "activation": self.config["policy"]["activation"],
            "native_fallback": True,
            "authority_effect": "none",
            "mutation_effect": "none",
            "usable_providers": list(self.usable_providers()),
            "capabilities": list(self.capabilities()),
            "providers": providers,
        }

        projection["projection_sha256"] = _digest(projection)
        return projection


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="savant-ai-capabilities"
    )
    parser.add_argument(
        "--config",
        default=str(DEFAULT_CONFIG),
    )

    sub = parser.add_subparsers(
        dest="command",
        required=True,
    )

    sub.add_parser("status")

    providers = sub.add_parser("providers")
    providers.add_argument("capability")

    args = parser.parse_args()

    try:
        registry = AICapabilityRegistry(args.config)

        if args.command == "status":
            print(
                json.dumps(
                    registry.projection(),
                    indent=2,
                    sort_keys=True,
                )
            )
            return 0

        if args.command == "providers":
            print(
                json.dumps(
                    {
                        "capability": args.capability,
                        "providers": list(
                            registry.providers_for(
                                args.capability
                            )
                        ),
                    },
                    indent=2,
                    sort_keys=True,
                )
            )
            return 0

    except (AICapabilityError, OSError, ValueError) as exc:
        print(
            json.dumps(
                {
                    "valid": False,
                    "error": str(exc),
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 1

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
