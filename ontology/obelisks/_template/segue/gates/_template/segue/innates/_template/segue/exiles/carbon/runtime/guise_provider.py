#!/usr/bin/env python3
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Mapping, Protocol, Sequence

from guise import (
    OWNER,
    SCHEMA,
    SPECIALIZATION,
    CharacterGraph,
    Guise,
    GuiseError,
    SourceReference,
    digest,
)
from guise_extract import ExtractionNormalizer


class GuiseProviderError(GuiseError):
    pass


class GuiseProvider(Protocol):
    provider_id: str

    def interpret(
        self,
        *,
        character_id: str,
        text: str,
        source: Mapping[str, Any],
        manifest: Mapping[str, Any],
    ) -> Mapping[str, Any]:
        ...


@dataclass(frozen=True)
class ProviderReceipt:
    provider_id: str
    operation: str
    input_digest: str
    output_digest: str
    accepted_count: int
    rejected_count: int
    authoritative: bool = False

    def projection(self) -> dict[str, Any]:
        return {
            "schema": SCHEMA,
            "owner": OWNER,
            "specialization": SPECIALIZATION,
            "kind": "guise_provider_receipt",
            "provider_id": self.provider_id,
            "operation": self.operation,
            "input_digest": self.input_digest,
            "output_digest": self.output_digest,
            "accepted_count": self.accepted_count,
            "rejected_count": self.rejected_count,
            "authoritative": self.authoritative,
            "authority_effect": "none",
        }


class CallableProvider:
    def __init__(
        self,
        provider_id: str,
        callable_: Callable[..., Mapping[str, Any]],
    ) -> None:
        provider_id = str(provider_id).strip().lower()

        if not provider_id:
            raise GuiseProviderError(
                "provider_id is required"
            )

        if not callable(callable_):
            raise GuiseProviderError(
                "provider callable must be callable"
            )

        self.provider_id = provider_id
        self.callable = callable_

    def interpret(
        self,
        *,
        character_id: str,
        text: str,
        source: Mapping[str, Any],
        manifest: Mapping[str, Any],
    ) -> Mapping[str, Any]:
        result = self.callable(
            character_id=character_id,
            text=text,
            source=dict(source),
            manifest=dict(manifest),
        )

        if not isinstance(result, Mapping):
            raise GuiseProviderError(
                "provider must return a mapping"
            )

        return result


class GuiseProviderRegistry:
    def __init__(self) -> None:
        self._providers: dict[str, GuiseProvider] = {}

    def register(
        self,
        provider: GuiseProvider,
    ) -> None:
        provider_id = str(
            provider.provider_id
        ).strip().lower()

        if not provider_id:
            raise GuiseProviderError(
                "provider_id is required"
            )

        self._providers[provider_id] = provider

    def unregister(
        self,
        provider_id: str,
    ) -> None:
        self._providers.pop(
            str(provider_id).strip().lower(),
            None,
        )

    def get(
        self,
        provider_id: str,
    ) -> GuiseProvider:
        normalized = str(
            provider_id
        ).strip().lower()

        provider = self._providers.get(
            normalized
        )

        if provider is None:
            raise GuiseProviderError(
                f"unknown guise provider: {normalized}"
            )

        return provider

    def status(self) -> dict[str, Any]:
        return {
            "schema": SCHEMA,
            "owner": OWNER,
            "specialization": SPECIALIZATION,
            "kind": "guise_provider_registry",
            "providers": sorted(
                self._providers
            ),
            "provider_count": len(
                self._providers
            ),
            "authority_effect": "none",
        }


class GuiseCorpusInterpreter:
    def __init__(
        self,
        guise: Guise,
        registry: GuiseProviderRegistry,
    ) -> None:
        self.guise = guise
        self.registry = registry
        self.normalizer = ExtractionNormalizer(
            guise
        )

    def interpret(
        self,
        *,
        graph: CharacterGraph,
        provider_id: str,
        text: str,
        source: SourceReference,
    ) -> dict[str, Any]:
        if not isinstance(text, str):
            raise GuiseProviderError(
                "text must be a string"
            )

        if not text.strip():
            raise GuiseProviderError(
                "text must not be empty"
            )

        provider = self.registry.get(
            provider_id
        )

        provider_input = {
            "character_id": graph.character_id,
            "text": text,
            "source": source.projection(),
            "manifest": self.guise.manifest,
        }

        provider_result = provider.interpret(
            character_id=graph.character_id,
            text=text,
            source=source.projection(),
            manifest=self.guise.manifest,
        )

        candidates = provider_result.get(
            "candidates",
            []
        )

        if not isinstance(candidates, Sequence) or isinstance(
            candidates,
            (str, bytes, bytearray),
        ):
            raise GuiseProviderError(
                "provider candidates must be a sequence"
            )

        normalized = self.normalizer.normalize(
            graph=graph,
            source_id=source.source_id,
            source_kind=source.source_kind,
            source_digest=(
                source.content_digest
                or digest(text)
            ),
            candidates=list(candidates),
        )

        receipt = ProviderReceipt(
            provider_id=provider.provider_id,
            operation="interpret",
            input_digest=digest(
                provider_input
            ),
            output_digest=digest(
                dict(provider_result)
            ),
            accepted_count=normalized[
                "accepted_count"
            ],
            rejected_count=normalized[
                "rejected_count"
            ],
        )

        result = {
            "schema": SCHEMA,
            "owner": OWNER,
            "specialization": SPECIALIZATION,
            "operation": "corpus_interpretation",
            "character_id": graph.character_id,
            "provider_id": provider.provider_id,
            "provider_metadata": dict(
                provider_result.get(
                    "metadata",
                    {}
                )
            ),
            "normalization": normalized,
            "receipt": receipt.projection(),
            "source_authority_preserved": True,
            "automatic_canonization": False,
            "provider_output_authoritative": False,
            "character_mutated_only_by_derived_substantiation": True,
            "authority_effect": "none",
        }

        result["projection_digest"] = digest(
            result
        )

        return result
