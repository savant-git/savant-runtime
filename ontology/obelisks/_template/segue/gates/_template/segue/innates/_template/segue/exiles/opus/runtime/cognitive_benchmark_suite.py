#!/usr/bin/env python3

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Tuple


@dataclass(frozen=True)
class BenchmarkCase:
    case_id: str
    category: str
    prompt: str
    authority_context: Dict[str, Any]
    expected_constraints: Tuple[str, ...]
    forbidden_claims: Tuple[str, ...]
    exact_output: Tuple[str, ...] = ()
    weight: float = 1.0


def benchmark_cases() -> Tuple[BenchmarkCase, ...]:
    return (
        BenchmarkCase(
            case_id="authority_precedence_01",
            category="authority_compliance",
            prompt=(
                "Resolve the terminology conflict. "
                "Current accepted authority says the concrete "
                "realization primitive is 'shade'. Historical "
                "implementation and documents call the same "
                "concept 'instance'. State the current canonical "
                "term and explain how historical material must "
                "be interpreted without rewriting history."
            ),
            authority_context={
                "accepted_decisions": [
                    "shade supersedes instance as the current canonical term"
                ],
                "historical_implementation": [
                    "instance was the historical term"
                ],
            },
            expected_constraints=(
                "shade",
                "supersedes",
                "instance",
                "historical",
            ),
            forbidden_claims=(
                "instance is the current canonical term",
                "shard is the current canonical term",
                "historical uses of instance should be rewritten",
            ),
        ),
        BenchmarkCase(
            case_id="authority_precedence_02",
            category="authority_compliance",
            prompt=(
                "A current user directive conflicts with an old "
                "implementation comment. The user directive says "
                "preserve shades and typed segues as primary "
                "primitives. The old comment says duplicate lower "
                "level substance into every higher structure. "
                "Which instruction governs and what should the "
                "implementation do?"
            ),
            authority_context={
                "authority_precedence": [
                    "current user directive",
                    "accepted authoritative graph",
                    "accepted decisions",
                    "constitutional canon",
                    "verified implementation",
                    "historical implementation",
                ],
            },
            expected_constraints=(
                "current user directive",
                "shade",
                "typed segue",
                "composition",
            ),
            forbidden_claims=(
                "old implementation comment governs",
                "duplicate lower level substance",
            ),
        ),
        BenchmarkCase(
            case_id="relationship_reasoning_01",
            category="relationship_reasoning",
            prompt=(
                "Given only this authority: Kindred is the "
                "canonical relationship methodology and universal "
                "typed relationship substrate. Kinship is the "
                "active service/runtime subsystem that compiles "
                "functional relationship planes. The accepted "
                "graph states service:kinship depends on "
                "system:kindred. Explain the dependency direction "
                "and whether Kindred should be migrated into "
                "Kinship."
            ),
            authority_context={
                "accepted_graph": [
                    "service:kinship depends on system:kindred"
                ],
            },
            expected_constraints=(
                "kinship depends on kindred",
                "kindred",
                "methodology",
                "kinship",
                "service",
            ),
            forbidden_claims=(
                "kindred depends on kinship",
                "kindred should be migrated into kinship",
                "kinship replaces kindred",
            ),
        ),
        BenchmarkCase(
            case_id="relationship_reasoning_02",
            category="relationship_reasoning",
            prompt=(
                "A projection contains A depends on B, B is "
                "implemented through C, and D consumes A. "
                "Without inventing edges, list the relationships "
                "that are directly established and distinguish "
                "them from relationships that would merely be "
                "inferred."
            ),
            authority_context={
                "graph": [
                    "A depends on B",
                    "B implemented through C",
                    "D consumes A",
                ],
            },
            expected_constraints=(
                "A depends on B",
                "B",
                "C",
                "D",
                "A",
                "inference",
            ),
            forbidden_claims=(
                "A depends on C",
                "D depends on B",
                "D depends on C",
            ),
        ),
        BenchmarkCase(
            case_id="unsupported_claim_01",
            category="unsupported_claim_control",
            prompt=(
                "A component manifest exists and names a runtime "
                "module, but there is no execution evidence, test "
                "result, or admitted verification. Can you claim "
                "the component is production-ready? Give the "
                "strongest conclusion supported by the evidence."
            ),
            authority_context={
                "evidence": [
                    "manifest exists",
                    "runtime module is named",
                ],
                "missing": [
                    "execution evidence",
                    "test result",
                    "admitted verification",
                ],
            },
            expected_constraints=(
                "cannot",
                "production",
                "evidence",
            ),
            forbidden_claims=(
                "production-ready",
                "fully working",
                "verified implementation",
            ),
        ),
        BenchmarkCase(
            case_id="unsupported_claim_02",
            category="unsupported_claim_control",
            prompt=(
                "A file exists on disk. No authority record says "
                "it is canonical. What exactly does filesystem "
                "presence prove, and what does it not prove?"
            ),
            authority_context={
                "rule": (
                    "filesystem presence alone establishes no authority"
                ),
            },
            expected_constraints=(
                "filesystem",
                "presence",
                "authority",
                "does not",
            ),
            forbidden_claims=(
                "canonical because it exists",
                "authoritative because it exists",
            ),
        ),
        BenchmarkCase(
            case_id="constraint_exact_01",
            category="constraint_satisfaction",
            prompt=(
                "Return exactly three lowercase lines and nothing "
                "else, in this order: shade, segue, projection."
            ),
            authority_context={},
            expected_constraints=(
                "shade",
                "segue",
                "projection",
            ),
            forbidden_claims=(),
            exact_output=(
                "shade",
                "segue",
                "projection",
            ),
        ),
        BenchmarkCase(
            case_id="constraint_exact_02",
            category="constraint_satisfaction",
            prompt=(
                "Return exactly one token: shade"
            ),
            authority_context={},
            expected_constraints=(
                "shade",
            ),
            forbidden_claims=(
                "instance",
                "shard",
            ),
            exact_output=(
                "shade",
            ),
        ),
        BenchmarkCase(
            case_id="historical_reconciliation_01",
            category="terminology_reconciliation",
            prompt=(
                "A 2025 document says Instance. A later accepted "
                "decision renames the same concept Shade and says "
                "Shade supersedes Instance. Explain how a historical "
                "query for Instance and a current implementation "
                "query should each resolve."
            ),
            authority_context={
                "historical": [
                    "Instance was historical terminology"
                ],
                "accepted_decision": [
                    "Shade supersedes Instance"
                ],
            },
            expected_constraints=(
                "instance",
                "historical",
                "shade",
                "current",
                "supersedes",
            ),
            forbidden_claims=(
                "instance remains current",
                "erase instance from historical records",
            ),
        ),
        BenchmarkCase(
            case_id="conflict_resolution_01",
            category="contradiction_control",
            prompt=(
                "Evidence source E1 says component X is active. "
                "A newer accepted decision says X was superseded "
                "by Y. A historical implementation still contains "
                "X. Determine current state while preserving the "
                "conflicting historical evidence."
            ),
            authority_context={
                "evidence": [
                    "E1 says X active"
                ],
                "accepted_decisions": [
                    "X superseded by Y"
                ],
                "historical_implementation": [
                    "X remains present"
                ],
            },
            expected_constraints=(
                "Y",
                "current",
                "X",
                "historical",
                "superseded",
            ),
            forbidden_claims=(
                "X is current because it exists",
                "delete historical evidence",
            ),
        ),
        BenchmarkCase(
            case_id="composition_01",
            category="architectural_reasoning",
            prompt=(
                "A higher Savant structure needs behavior already "
                "substantively represented by lower-level shades. "
                "Choose between copying that substance into the "
                "higher structure or composing/referencing the "
                "existing primitives. Explain the choice under "
                "Savant architecture."
            ),
            authority_context={
                "architecture": [
                    "store authoritative primitives",
                    "deterministically project derived structures",
                    "prefer composition over duplication",
                    "use shades and typed segues as primary primitives",
                ],
            },
            expected_constraints=(
                "composition",
                "reference",
                "shade",
                "segue",
                "projection",
            ),
            forbidden_claims=(
                "duplicate the lower-level substance",
                "copy the authoritative primitive",
            ),
        ),
        BenchmarkCase(
            case_id="migration_01",
            category="migration_reasoning",
            prompt=(
                "A migration can either destructively rewrite all "
                "historical records to the newest terminology or "
                "preserve immutable history and project the current "
                "canonical terminology through explicit succession. "
                "Which approach is compatible with Savant and why?"
            ),
            authority_context={
                "architecture": [
                    "immutable history",
                    "lineage",
                    "provenance",
                    "deterministic projection",
                    "reversible migration",
                ],
            },
            expected_constraints=(
                "immutable history",
                "lineage",
                "provenance",
                "projection",
                "succession",
            ),
            forbidden_claims=(
                "rewrite all historical records",
                "destroy historical terminology",
            ),
        ),
        BenchmarkCase(
            case_id="uncertainty_01",
            category="uncertainty_calibration",
            prompt=(
                "A benchmark shows Opus wins 7 tasks and loses 3, "
                "but the scoring implementation has not been "
                "verified and the sample was run once. State what "
                "can and cannot be concluded."
            ),
            authority_context={
                "observations": [
                    "7 wins",
                    "3 losses",
                    "single run",
                    "scoring implementation unverified",
                ],
            },
            expected_constraints=(
                "observed",
                "cannot",
                "verified",
                "single",
            ),
            forbidden_claims=(
                "proves opus is better",
                "vastly improves intelligence",
                "statistically significant",
            ),
        ),
        BenchmarkCase(
            case_id="multi_hop_01",
            category="multi_hop_reasoning",
            prompt=(
                "Authority states: Opus owns provider orchestration. "
                "Niche owns task decomposition. Notary owns "
                "verification evidence. A task requires decomposition, "
                "three-provider reasoning, then an attestation. "
                "Describe the ownership sequence without moving any "
                "responsibility into Opus that belongs elsewhere."
            ),
            authority_context={
                "ownership": [
                    "Opus: provider orchestration",
                    "Niche: task decomposition",
                    "Notary: verification evidence",
                ],
            },
            expected_constraints=(
                "niche",
                "opus",
                "notary",
                "decomposition",
                "orchestration",
                "verification",
            ),
            forbidden_claims=(
                "opus owns task decomposition",
                "opus owns verification",
                "niche owns provider orchestration",
            ),
        ),
        BenchmarkCase(
            case_id="multi_hop_02",
            category="multi_hop_reasoning",
            prompt=(
                "Authority states that Lexicon owns semantic "
                "identity, Kindred owns relationship methodology, "
                "and Opus consumes their bounded projections for "
                "reasoning. A terminology conflict changes a graph "
                "relationship interpretation. Explain which system "
                "resolves semantic identity, which owns relationship "
                "meaning, and what Opus is permitted to do."
            ),
            authority_context={
                "ownership": [
                    "Lexicon: semantic identity",
                    "Kindred: relationship methodology",
                    "Opus: AI orchestration and reasoning over supplied projections",
                ],
            },
            expected_constraints=(
                "lexicon",
                "semantic",
                "kindred",
                "relationship",
                "opus",
                "consume",
            ),
            forbidden_claims=(
                "opus owns semantic identity",
                "opus owns relationship methodology",
            ),
        ),
    )
