#!/usr/bin/env python3
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from guise import (
    CategorySubstantiation,
    Evidence,
    Guise,
    GuiseError,
    SourceReference,
    TemporalScope,
    canonical_json,
    digest,
)


class GuiseExtractionError(
    GuiseError
):
    pass


@dataclass(frozen=True)
class ExtractionCandidate:
    domain: str
    category: str
    observation: str
    formulation: str
    epistemic_class: str = (
        "weak_inference"
    )
    confidence: str = "unknown"
    location: str | None = None
    alternatives: tuple[str, ...] = ()
    tags: tuple[str, ...] = ()

    @classmethod
    def from_mapping(
        cls,
        value: Mapping[str, Any],
    ) -> "ExtractionCandidate":
        alternatives = tuple(
            str(item).strip()
            for item in value.get(
                "alternatives",
                [],
            )
            if str(item).strip()
        )

        tags = tuple(
            str(item).strip()
            for item in value.get(
                "tags",
                [],
            )
            if str(item).strip()
        )

        return cls(
            domain=str(
                value.get(
                    "domain",
                    "",
                )
            ).strip(),
            category=str(
                value.get(
                    "category",
                    "",
                )
            ).strip(),
            observation=str(
                value.get(
                    "observation",
                    "",
                )
            ).strip(),
            formulation=str(
                value.get(
                    "formulation",
                    "",
                )
            ).strip(),
            epistemic_class=str(
                value.get(
                    "epistemic_class",
                    "weak_inference",
                )
            ).strip(),
            confidence=str(
                value.get(
                    "confidence",
                    "unknown",
                )
            ).strip(),
            location=(
                str(
                    value.get(
                        "location",
                        "",
                    )
                ).strip()
                or None
            ),
            alternatives=alternatives,
            tags=tags,
        )


class ExtractionNormalizer:
    def __init__(
        self,
        guise: Guise,
    ) -> None:
        self.guise = guise

        self.allowed_epistemic = set(
            guise.manifest[
                "epistemic_classes"
            ]
        )

        self.domains = {
            domain: set(categories)
            for domain, categories
            in guise.manifest[
                "domains"
            ].items()
        }

    def validate_candidate(
        self,
        candidate: ExtractionCandidate,
    ) -> None:
        if candidate.domain not in (
            self.domains
        ):
            raise GuiseExtractionError(
                f"unknown domain: "
                f"{candidate.domain}"
            )

        if candidate.category not in (
            self.domains[
                candidate.domain
            ]
        ):
            raise GuiseExtractionError(
                f"category "
                f"{candidate.category} "
                f"is not a member of "
                f"{candidate.domain}"
            )

        if not candidate.observation:
            raise GuiseExtractionError(
                "candidate observation "
                "is required"
            )

        if not candidate.formulation:
            raise GuiseExtractionError(
                "candidate formulation "
                "is required"
            )

        if (
            candidate.epistemic_class
            not in self.allowed_epistemic
        ):
            raise GuiseExtractionError(
                "invalid epistemic class: "
                f"{candidate.epistemic_class}"
            )

        if candidate.epistemic_class in {
            "canon",
            "superseded",
        }:
            raise GuiseExtractionError(
                "extraction providers may not "
                "assign authoritative canon or "
                "supersession"
            )

    def normalize(
        self,
        *,
        graph: Any,
        source_id: str,
        source_kind: str,
        source_digest: str,
        candidates: Sequence[
            Mapping[str, Any]
        ],
    ) -> dict[str, Any]:
        created_evidence = []
        created_categories = []
        rejected = []

        for index, raw in enumerate(
            candidates
        ):
            try:
                candidate = (
                    ExtractionCandidate
                    .from_mapping(raw)
                )

                self.validate_candidate(
                    candidate
                )

                source = SourceReference(
                    source_id=source_id,
                    location=(
                        candidate.location
                    ),
                    source_kind=source_kind,
                    authority_class=(
                        "source"
                    ),
                    content_digest=(
                        source_digest
                    ),
                )

                evidence = graph.add_evidence(
                    Evidence(
                        subject_id=(
                            graph.character_id
                        ),
                        observation=(
                            candidate.observation
                        ),
                        source=source,
                        epistemic_class=(
                            "observation"
                        ),
                        tags=(
                            candidate.tags
                        ),
                    )
                )

                category = (
                    graph.add_category(
                        CategorySubstantiation(
                            character_id=(
                                graph.character_id
                            ),
                            domain=(
                                candidate.domain
                            ),
                            category=(
                                candidate.category
                            ),
                            formulation=(
                                candidate.formulation
                            ),
                            epistemic_class=(
                                candidate
                                .epistemic_class
                            ),
                            evidence_refs=(
                                evidence.id,
                            ),
                            alternative_explanations=(
                                candidate
                                .alternatives
                            ),
                            confidence=(
                                candidate
                                .confidence
                            ),
                        )
                    )
                )

                created_evidence.append(
                    evidence.id
                )
                created_categories.append(
                    category.id
                )

            except (
                GuiseError,
                TypeError,
                ValueError,
            ) as exc:
                rejected.append(
                    {
                        "index": index,
                        "reason": str(exc),
                        "candidate": (
                            dict(raw)
                            if isinstance(
                                raw,
                                Mapping,
                            )
                            else {
                                "value": repr(
                                    raw
                                )
                            }
                        ),
                    }
                )

        result = {
            "operation": (
                "normalize_extraction"
            ),
            "character_id": (
                graph.character_id
            ),
            "source_id": source_id,
            "created_evidence": (
                created_evidence
            ),
            "created_categories": (
                created_categories
            ),
            "accepted_count": len(
                created_categories
            ),
            "rejected": rejected,
            "rejected_count": len(
                rejected
            ),
            "automatic_canonization": False,
            "authority_effect": "none",
        }

        result["result_digest"] = (
            digest(result)
        )

        return result


class MappingExtractionProvider:
    provider_id = (
        "guise.mapping-extraction-provider"
    )

    def __init__(
        self,
        extractor: Any,
    ) -> None:
        if not callable(extractor):
            raise GuiseExtractionError(
                "extractor must be callable"
            )

        self.extractor = extractor

    def extract(
        self,
        *,
        character_id: str,
        text: str,
        source: SourceReference,
        manifest: Mapping[str, Any],
    ) -> Mapping[str, Any]:
        value = self.extractor(
            character_id=character_id,
            text=text,
            source=source.projection(),
            manifest=dict(manifest),
        )

        if not isinstance(
            value,
            Mapping,
        ):
            raise GuiseExtractionError(
                "extractor must return "
                "a mapping"
            )

        candidates = value.get(
            "candidates",
            []
        )

        if not isinstance(
            candidates,
            list,
        ):
            raise GuiseExtractionError(
                "extractor candidates "
                "must be a list"
            )

        return {
            "provider_id": (
                self.provider_id
            ),
            "candidates": candidates,
            "provider_metadata": dict(
                value.get(
                    "metadata",
                    {},
                )
            ),
            "authority_effect": "none",
            "automatic_canonization": False,
        }
