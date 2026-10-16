#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List

from router import execute_text_request


ROOT = Path(
    "/root/savant-runtime"
).resolve()

OPUS_ROOT = (
    ROOT
    / "ontology"
    / "obelisks"
    / "_template"
    / "segue"
    / "gates"
    / "_template"
    / "segue"
    / "innates"
    / "_template"
    / "segue"
    / "exiles"
    / "opus"
).resolve()

POLICY_PATH = (
    OPUS_ROOT
    / "registry"
    / "policies"
    / "unique_orchestration_policy.json"
).resolve()

SCHEMA = "savant://opus/unique-orchestration/1"
OWNER = "opus"


class UniqueOrchestrationError(
    RuntimeError
):
    pass


def canonical_json(
    value: Any,
) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )


def digest(
    value: Any,
) -> str:
    return hashlib.sha256(
        canonical_json(value).encode(
            "utf-8"
        )
    ).hexdigest()


def stable_id(
    prefix: str,
    value: Any,
) -> str:
    return (
        f"{prefix}:"
        f"{digest(value)[:24]}"
    )


def load_policy() -> Dict[str, Any]:
    with POLICY_PATH.open(
        "r",
        encoding="utf-8",
    ) as handle:
        policy = json.load(handle)

    if (
        policy.get("owner")
        != OWNER
    ):
        raise UniqueOrchestrationError(
            "unique orchestration policy "
            "owner must be opus"
        )

    if (
        policy.get(
            "authority_effect"
        )
        != "none"
    ):
        raise UniqueOrchestrationError(
            "unique orchestration policy "
            "must not create authority"
        )

    return policy


def normalized_strings(
    values: Iterable[Any] | None,
) -> List[str]:
    if values is None:
        return []

    return sorted(
        {
            str(value).strip()
            for value in values
            if str(value).strip()
        }
    )


@dataclass(frozen=True)
class InferencePass:
    pass_id: str
    role: str
    stage: str
    response: Dict[str, Any]

    def projection(
        self,
    ) -> Dict[str, Any]:
        return {
            "pass_id": self.pass_id,
            "role": self.role,
            "stage": self.stage,
            "response": self.response,
        }


class UniqueOrchestrator:
    def __init__(
        self,
    ) -> None:
        self.policy = load_policy()

    def _limits(
        self,
    ) -> Dict[str, int]:
        raw = self.policy.get(
            "limits",
            {},
        )

        return {
            key: int(value)
            for key, value
            in raw.items()
        }

    def _role_prompt(
        self,
        *,
        role: str,
        task: str,
        context: Dict[str, Any],
    ) -> str:
        role_data = next(
            (
                item
                for item
                in self.policy.get(
                    "roles",
                    []
                )
                if item.get("id")
                == role
            ),
            {},
        )

        purpose = role_data.get(
            "purpose",
            role,
        )

        return (
            "You are one bounded reasoning "
            "instance participating in an "
            "Opus orchestration.\n\n"
            f"Role: {role}\n"
            f"Role purpose: {purpose}\n\n"
            "Rules:\n"
            "- Treat supplied authority as "
            "authority, not model output.\n"
            "- Distinguish facts, evidence, "
            "inference, hypothesis, "
            "speculation, and unknown.\n"
            "- Do not manufacture missing "
            "facts.\n"
            "- Preserve contradictions.\n"
            "- Prefer falsifiable reasoning.\n"
            "- Do not assume consensus.\n"
            "- Return only reasoning useful "
            "to the requested role.\n\n"
            f"Task:\n{task}\n\n"
            "Context:\n"
            f"{canonical_json(context)}"
        )

    def _execute(
        self,
        *,
        role: str,
        stage: str,
        task: str,
        context: Dict[str, Any],
        required_capabilities: (
            Iterable[str] | None
        ) = None,
        required_layers: (
            Iterable[str] | None
        ) = None,
    ) -> InferencePass:
        request = {
            "owner": OWNER,
            "operation": (
                "unique_orchestration_pass"
            ),
            "stage": stage,
            "role": role,
            "prompt": self._role_prompt(
                role=role,
                task=task,
                context=context,
            ),
            "required_capabilities": (
                normalized_strings(
                    required_capabilities
                )
            ),
            "required_layers": (
                normalized_strings(
                    required_layers
                )
            ),
            "authority_effect": "none",
        }

        pass_id = stable_id(
            "opus-pass",
            request,
        )

        response = execute_text_request(
            request
        )

        return InferencePass(
            pass_id=pass_id,
            role=role,
            stage=stage,
            response=response,
        )

    def _response_content(
        self,
        inference_pass: InferencePass,
    ) -> Any:
        response = (
            inference_pass.response
        )

        for key in (
            "text",
            "content",
            "output",
            "response",
            "result",
        ):
            if key in response:
                return response[key]

        return response

    def _pass_context(
        self,
        passes: Iterable[
            InferencePass
        ],
    ) -> List[Dict[str, Any]]:
        return [
            {
                "pass_id": item.pass_id,
                "role": item.role,
                "stage": item.stage,
                "content": (
                    self._response_content(
                        item
                    )
                ),
                "lineage": (
                    item.response.get(
                        "lineage"
                    )
                ),
            }
            for item in passes
        ]

    def deliberate(
        self,
        *,
        task: str,
        context: (
            Dict[str, Any] | None
        ) = None,
        independent_passes: (
            int | None
        ) = None,
        critique_rounds: (
            int | None
        ) = None,
        required_capabilities: (
            Iterable[str] | None
        ) = None,
        required_layers: (
            Iterable[str] | None
        ) = None,
    ) -> Dict[str, Any]:
        context = dict(
            context or {}
        )

        limits = self._limits()

        pass_count = (
            independent_passes
            if independent_passes
            is not None
            else limits[
                "default_independent_passes"
            ]
        )

        pass_count = max(
            1,
            min(
                int(pass_count),
                limits[
                    "maximum_independent_passes"
                ],
            ),
        )

        rounds = (
            critique_rounds
            if critique_rounds
            is not None
            else limits[
                "default_critique_rounds"
            ]
        )

        rounds = max(
            0,
            min(
                int(rounds),
                limits[
                    "maximum_critique_rounds"
                ],
            ),
        )

        maximum_calls = limits[
            "maximum_total_inference_calls"
        ]

        calls = 0
        passes: List[
            InferencePass
        ] = []

        independent_roles = [
            "analyst",
            "skeptic",
            "alternativist",
            "falsifier",
        ]

        for index in range(
            pass_count
        ):
            if calls >= maximum_calls:
                break

            role = independent_roles[
                index
                % len(independent_roles)
            ]

            item = self._execute(
                role=role,
                stage=(
                    "independent_inference"
                ),
                task=task,
                context=context,
                required_capabilities=(
                    required_capabilities
                ),
                required_layers=(
                    required_layers
                ),
            )

            passes.append(item)
            calls += 1

        critique_passes: List[
            InferencePass
        ] = []

        for round_index in range(
            rounds
        ):
            if calls >= maximum_calls:
                break

            critique_context = {
                "original_context": context,
                "candidate_passes": (
                    self._pass_context(
                        passes
                        + critique_passes
                    )
                ),
                "critique_round": (
                    round_index + 1
                ),
            }

            item = self._execute(
                role="skeptic",
                stage="cross_examination",
                task=(
                    "Critique the candidate "
                    "reasoning for the original "
                    f"task:\n{task}"
                ),
                context=critique_context,
                required_capabilities=(
                    required_capabilities
                ),
                required_layers=(
                    required_layers
                ),
            )

            critique_passes.append(
                item
            )
            calls += 1

            if calls >= maximum_calls:
                break

            falsification = self._execute(
                role="falsifier",
                stage="falsification",
                task=(
                    "Attempt to falsify the "
                    "strongest candidate "
                    "conclusions for the "
                    f"original task:\n{task}"
                ),
                context={
                    "original_context": (
                        context
                    ),
                    "candidate_passes": (
                        self._pass_context(
                            passes
                            + critique_passes
                        )
                    ),
                },
                required_capabilities=(
                    required_capabilities
                ),
                required_layers=(
                    required_layers
                ),
            )

            critique_passes.append(
                falsification
            )
            calls += 1

        all_pre_synthesis = (
            passes
            + critique_passes
        )

        if calls >= maximum_calls:
            return self._bounded_result(
                task=task,
                context=context,
                passes=all_pre_synthesis,
                calls=calls,
                status="budget_exhausted",
                synthesis=None,
                synthesis_critique=None,
                final=None,
            )

        synthesis = self._execute(
            role="integrator",
            stage="synthesis",
            task=(
                "Synthesize the strongest "
                "supported answer to the "
                "original task while "
                "preserving material dissent, "
                "counterevidence, uncertainty, "
                "and unresolved alternatives."
                f"\n\nOriginal task:\n{task}"
            ),
            context={
                "original_context": context,
                "candidate_passes": (
                    self._pass_context(
                        all_pre_synthesis
                    )
                ),
            },
            required_capabilities=(
                required_capabilities
            ),
            required_layers=(
                required_layers
            ),
        )

        calls += 1

        synthesis_critique = None

        if calls < maximum_calls:
            synthesis_critique = (
                self._execute(
                    role="skeptic",
                    stage=(
                        "synthesis_critique"
                    ),
                    task=(
                        "Attack the proposed "
                        "synthesis. Identify "
                        "unsupported collapse of "
                        "uncertainty, erased "
                        "dissent, false "
                        "consensus, hidden "
                        "assumptions, and "
                        "stronger alternatives."
                    ),
                    context={
                        "original_task": task,
                        "synthesis": (
                            self._pass_context(
                                [synthesis]
                            )[0]
                        ),
                        "prior_passes": (
                            self._pass_context(
                                all_pre_synthesis
                            )
                        ),
                    },
                    required_capabilities=(
                        required_capabilities
                    ),
                    required_layers=(
                        required_layers
                    ),
                )
            )

            calls += 1

        final = synthesis

        if (
            synthesis_critique
            is not None
            and calls < maximum_calls
        ):
            final = self._execute(
                role="integrator",
                stage="final_projection",
                task=(
                    "Produce the final derived "
                    "answer to the original "
                    "task. Incorporate valid "
                    "critique without forcing "
                    "agreement. Explicitly "
                    "preserve unresolved "
                    "unknowns and material "
                    "dissent."
                    f"\n\nOriginal task:\n{task}"
                ),
                context={
                    "original_context": context,
                    "synthesis": (
                        self._pass_context(
                            [synthesis]
                        )[0]
                    ),
                    "synthesis_critique": (
                        self._pass_context(
                            [
                                synthesis_critique
                            ]
                        )[0]
                    ),
                },
                required_capabilities=(
                    required_capabilities
                ),
                required_layers=(
                    required_layers
                ),
            )

            calls += 1

        return self._bounded_result(
            task=task,
            context=context,
            passes=all_pre_synthesis,
            calls=calls,
            status="complete",
            synthesis=synthesis,
            synthesis_critique=(
                synthesis_critique
            ),
            final=final,
        )

    def _bounded_result(
        self,
        *,
        task: str,
        context: Dict[str, Any],
        passes: List[
            InferencePass
        ],
        calls: int,
        status: str,
        synthesis: (
            InferencePass | None
        ),
        synthesis_critique: (
            InferencePass | None
        ),
        final: (
            InferencePass | None
        ),
    ) -> Dict[str, Any]:
        request_identity = {
            "task": task,
            "context": context,
            "policy_digest": digest(
                self.policy
            ),
        }

        result = {
            "schema": SCHEMA,
            "owner": OWNER,
            "operation": (
                "unique_orchestration"
            ),
            "orchestration_id": (
                stable_id(
                    "opus-orchestration",
                    request_identity,
                )
            ),
            "status": status,
            "task_digest": digest(
                task
            ),
            "context_digest": digest(
                context
            ),
            "policy_digest": digest(
                self.policy
            ),
            "inference_calls": calls,
            "passes": [
                item.projection()
                for item in passes
            ],
            "synthesis": (
                synthesis.projection()
                if synthesis
                else None
            ),
            "synthesis_critique": (
                synthesis_critique.projection()
                if synthesis_critique
                else None
            ),
            "final": (
                final.projection()
                if final
                else None
            ),
            "final_content": (
                self._response_content(
                    final
                )
                if final
                else None
            ),
            "epistemic_state": {
                "consensus_is_authority": (
                    False
                ),
                "confidence_is_authority": (
                    False
                ),
                "unknown_preserved": True,
                "dissent_preserved": True,
                "counterevidence_preserved": (
                    True
                ),
            },
            "replay": {
                "task": task,
                "context": context,
                "policy_ref": str(
                    POLICY_PATH
                ),
                "deterministic_structure": (
                    True
                ),
                "provider_outputs_are_not_"
                "assumed_deterministic": True,
            },
            "authority_effect": "none",
        }

        result[
            "projection_digest"
        ] = digest(result)

        return result


def health() -> Dict[str, Any]:
    policy = load_policy()
    limits = policy.get(
        "limits",
        {},
    )

    return {
        "status": "ok",
        "owner": OWNER,
        "schema": SCHEMA,
        "policy": policy["id"],
        "roles": [
            role["id"]
            for role
            in policy.get(
                "roles",
                []
            )
        ],
        "stages": list(
            policy.get(
                "stages",
                []
            )
        ),
        "maximum_total_inference_calls": (
            limits.get(
                "maximum_total_inference_calls"
            )
        ),
        "bounded_recursion": True,
        "dissent_preserved": True,
        "unknown_preserved": True,
        "consensus_creates_authority": (
            False
        ),
        "authority_effect": "none",
    }


if __name__ == "__main__":
    print(
        json.dumps(
            health(),
            indent=2,
            sort_keys=True,
        )
    )
