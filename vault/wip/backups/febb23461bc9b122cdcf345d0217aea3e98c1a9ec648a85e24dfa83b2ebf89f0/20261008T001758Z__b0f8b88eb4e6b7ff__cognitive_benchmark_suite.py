from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Mapping, Sequence


@dataclass(frozen=True)
class BenchmarkCase:
    case_id: str
    category: str
    prompt: str
    system: str
    required_capabilities: tuple[str, ...]
    authority_sensitive: bool
    requires_verification: bool
    requires_relationship_reasoning: bool
    requires_historical_reconciliation: bool
    expected_constraints: tuple[str, ...]
    forbidden_claims: tuple[str, ...]

    def as_dict(self) -> Dict[str, Any]:
        return {
            "case_id": self.case_id,
            "category": self.category,
            "prompt": self.prompt,
            "system": self.system,
            "required_capabilities": list(
                self.required_capabilities
            ),
            "authority_sensitive":
                self.authority_sensitive,
            "requires_verification":
                self.requires_verification,
            "requires_relationship_reasoning":
                self.requires_relationship_reasoning,
            "requires_historical_reconciliation":
                self.requires_historical_reconciliation,
            "expected_constraints": list(
                self.expected_constraints
            ),
            "forbidden_claims": list(
                self.forbidden_claims
            ),
        }


CASES = (
    BenchmarkCase(
        case_id="authority_precedence",
        category="authority",
        prompt=(
            "Two sources conflict. Current accepted authority "
            "states that the canonical primitive is shade. "
            "Historical implementation calls it instance. "
            "Determine which term governs current implementation "
            "and preserve the historical term only as lineage."
        ),
        system=(
            "Apply authority precedence. Do not reconcile conflicting "
            "authority by invention."
        ),
        required_capabilities=("text",),
        authority_sensitive=True,
        requires_verification=True,
        requires_relationship_reasoning=False,
        requires_historical_reconciliation=True,
        expected_constraints=(
            "shade",
            "historical",
            "lineage",
        ),
        forbidden_claims=(
            "instance is current",
            "both are equally authoritative",
        ),
    ),
    BenchmarkCase(
        case_id="relationship_reasoning",
        category="relationship",
        prompt=(
            "Kindred is the canonical relationship methodology. "
            "Kinship is the active service that compiles functional "
            "relationship planes and depends on Kindred. Explain the "
            "direction of dependency without collapsing the two."
        ),
        system=(
            "Preserve distinct ownership and dependency direction."
        ),
        required_capabilities=("text",),
        authority_sensitive=True,
        requires_verification=False,
        requires_relationship_reasoning=True,
        requires_historical_reconciliation=False,
        expected_constraints=(
            "kindred",
            "kinship",
            "depends",
        ),
        forbidden_claims=(
            "kindred depends on kinship",
            "kindred and kinship are the same",
        ),
    ),
    BenchmarkCase(
        case_id="unsupported_claim_control",
        category="factuality",
        prompt=(
            "A component manifest says status is stub and exposes no "
            "capabilities. State what can be concluded about its "
            "production readiness."
        ),
        system=(
            "Do not infer unverified implementation or production "
            "readiness."
        ),
        required_capabilities=("text",),
        authority_sensitive=True,
        requires_verification=True,
        requires_relationship_reasoning=False,
        requires_historical_reconciliation=False,
        expected_constraints=(
            "stub",
            "cannot",
        ),
        forbidden_claims=(
            "production ready",
            "fully implemented",
        ),
    ),
    BenchmarkCase(
        case_id="constraint_satisfaction",
        category="constraints",
        prompt=(
            "Return exactly three lowercase identifiers, one per line, "
            "with no numbering or explanation: shade, segue, projection."
        ),
        system=(
            "Follow output constraints exactly."
        ),
        required_capabilities=("text",),
        authority_sensitive=False,
        requires_verification=False,
        requires_relationship_reasoning=False,
        requires_historical_reconciliation=False,
        expected_constraints=(
            "shade",
            "segue",
            "projection",
        ),
        forbidden_claims=(),
    ),
    BenchmarkCase(
        case_id="historical_reconciliation",
        category="terminology",
        prompt=(
            "Historical records use instance. Current accepted Lexicon "
            "authority says shade supersedes instance. Describe the "
            "current term and the historical relationship without "
            "rewriting history."
        ),
        system=(
            "Preserve supersession and provenance."
        ),
        required_capabilities=("text",),
        authority_sensitive=True,
        requires_verification=False,
        requires_relationship_reasoning=True,
        requires_historical_reconciliation=True,
        expected_constraints=(
            "shade",
            "instance",
            "supersed",
        ),
        forbidden_claims=(
            "instance remains canonical",
        ),
    ),
)


def cases() -> list[Dict[str, Any]]:
    return [
        case.as_dict()
        for case in CASES
    ]


def case(
    case_id: str,
) -> Dict[str, Any]:
    target = str(
        case_id
    ).strip()

    for value in CASES:
        if value.case_id == target:
            return value.as_dict()

    raise KeyError(
        f"unknown benchmark case: {target}"
    )
