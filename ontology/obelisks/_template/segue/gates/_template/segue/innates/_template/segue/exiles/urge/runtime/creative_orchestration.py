from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from ...opus.runtime.resilient_text import (
    execute_text_request_resilient,
)
from ...underscore.runtime.vessel.vessel import (
    Vessel,
    default_cliche_threshold,
    default_mmr_lambda,
    default_similarity_threshold,
)


schema = "savant://runtime/urge/creative-orchestration/1.0.0"
owner = "exile:urge"
opus_owner = "exile:opus"
underscore_owner = "exile:underscore"


class creative_orchestration_error(
    RuntimeError
):
    pass


def _canonical_json(
    value: Any,
) -> str:
    try:
        return json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
    except (
        TypeError,
        ValueError,
    ) as exc:
        raise creative_orchestration_error(
            "creative orchestration value "
            "must be canonical-json serializable"
        ) from exc


def _digest(
    value: Any,
) -> str:
    return hashlib.sha256(
        _canonical_json(
            value
        ).encode(
            "utf-8"
        )
    ).hexdigest()


def _strings(
    value: Any,
) -> tuple[str, ...]:
    if value is None:
        return ()

    if isinstance(
        value,
        str,
    ):
        value = (
            value,
        )

    if (
        isinstance(
            value,
            bytes,
        )
        or not isinstance(
            value,
            Sequence,
        )
    ):
        raise creative_orchestration_error(
            "expected a sequence"
        )

    output = []
    seen = set()

    for item in value:
        text = str(
            item
        ).strip()

        if (
            text
            and text not in seen
        ):
            seen.add(
                text
            )
            output.append(
                text
            )

    return tuple(
        output
    )


def _json_object(
    text: str,
) -> dict[str, Any]:
    value = str(
        text
    ).strip()

    if value.startswith(
        "```"
    ):
        lines = value.splitlines()

        if lines:
            lines = lines[
                1:
            ]

        if (
            lines
            and lines[-1].strip()
            == "```"
        ):
            lines = lines[
                :-1
            ]

        value = "\n".join(
            lines
        ).strip()

        if value.lower().startswith(
            "json\n"
        ):
            value = value[
                5:
            ].strip()

    try:
        parsed = json.loads(
            value
        )
    except json.JSONDecodeError as exc:
        raise creative_orchestration_error(
            "opus response was not valid json"
        ) from exc

    if not isinstance(
        parsed,
        dict,
    ):
        raise creative_orchestration_error(
            "opus response must be a json object"
        )

    return parsed


def _opus_text(
    *,
    message: str,
    system: str,
    context: Mapping[str, Any],
    required_capabilities: Sequence[str] = (),
    required_layers: Sequence[str] = (),
) -> dict[str, Any]:
    request = {
        "owner": owner,
        "message": message,
        "system": system,
        "context": _canonical_json(
            context
        ),
        "required_capabilities": list(
            _strings(
                required_capabilities
            )
        ),
        "required_layers": list(
            _strings(
                required_layers
            )
        ),
    }

    result = execute_text_request_resilient(
        request
    )

    if not isinstance(
        result,
        dict,
    ):
        raise creative_orchestration_error(
            "opus returned an invalid result"
        )

    text = str(
        result.get(
            "text",
            "",
        )
    ).strip()

    if not text:
        raise creative_orchestration_error(
            "opus returned no text"
        )

    return {
        "text": text,
        "lineage": result.get(
            "lineage",
            {},
        ),
        "provider": result.get(
            "provider"
        ),
        "model": result.get(
            "model"
        ),
        "usage": result.get(
            "usage",
            {},
        ),
    }


@dataclass(
    frozen=True,
    slots=True,
)
class creative_policy:
    divergence_passes: int = 4
    candidates_per_pass: int = 6
    frontier_size: int = 7
    mutation_depth: int = 2
    synthesis_candidates: int = 6
    cliche_threshold: float = (
        default_cliche_threshold
    )
    similarity_threshold: float = (
        default_similarity_threshold
    )
    mmr_lambda: float = (
        default_mmr_lambda
    )

    def __post_init__(
        self,
    ) -> None:
        if not (
            1
            <= self.divergence_passes
            <= 12
        ):
            raise creative_orchestration_error(
                "divergence_passes must lie within 1..12"
            )

        if not (
            2
            <= self.candidates_per_pass
            <= 24
        ):
            raise creative_orchestration_error(
                "candidates_per_pass must lie within 2..24"
            )

        if not (
            2
            <= self.frontier_size
            <= 24
        ):
            raise creative_orchestration_error(
                "frontier_size must lie within 2..24"
            )

        if not (
            0
            <= self.mutation_depth
            <= 4
        ):
            raise creative_orchestration_error(
                "mutation_depth must lie within 0..4"
            )

        if not (
            2
            <= self.synthesis_candidates
            <= 24
        ):
            raise creative_orchestration_error(
                "synthesis_candidates must lie within 2..24"
            )


_lenses = (
    {
        "id": "primitive-recomposition",
        "instruction": (
            "Reduce the problem to its smallest meaningful primitives. "
            "Recompose those primitives into mechanisms whose novelty "
            "comes from structure rather than styling."
        ),
    },
    {
        "id": "assumption-negative",
        "instruction": (
            "Identify the assumptions a conventional expert would "
            "silently preserve. Generate concepts by removing or "
            "reversing assumptions while preserving actual requirements."
        ),
    },
    {
        "id": "orthogonal-transfer",
        "instruction": (
            "Borrow mechanisms, not appearances, from distant domains. "
            "Translate useful causal structures into the target problem "
            "without visual quotation or genre imitation."
        ),
    },
    {
        "id": "emergent-compression",
        "instruction": (
            "Seek one compact mechanism that creates several desired "
            "properties simultaneously. Prefer emergence over a pile "
            "of independent features."
        ),
    },
    {
        "id": "negative-space",
        "instruction": (
            "Treat omission, absence, interval, boundary, interruption, "
            "and what is deliberately not represented as active design "
            "material."
        ),
    },
    {
        "id": "causal-inversion",
        "instruction": (
            "Invert cause and effect, producer and consumer, foreground "
            "and support, input and output, or expected direction of "
            "interaction where doing so remains coherent."
        ),
    },
    {
        "id": "temporal-depth",
        "instruction": (
            "Design for transformation through time rather than a single "
            "frozen answer. Look for concepts whose identity survives "
            "state changes and gains meaning from them."
        ),
    },
    {
        "id": "category-error",
        "instruction": (
            "Ask what becomes possible when the problem has been placed "
            "in the wrong conceptual category. Reframe it without "
            "discarding its real constraints."
        ),
    },
    {
        "id": "constraint-alchemy",
        "instruction": (
            "Treat the hardest constraint as generative material. Make "
            "the limitation produce the identity instead of merely "
            "surviving it."
        ),
    },
    {
        "id": "second-order-consequence",
        "instruction": (
            "Ignore the obvious first-order idea and reason from the "
            "consequences of consequences. Prefer concepts that reveal "
            "a coherent implication conventional ideation stops before."
        ),
    },
    {
        "id": "semantic-paradox",
        "instruction": (
            "Search for two apparently incompatible requirements that "
            "can be satisfied by one deeper mechanism rather than by "
            "compromise."
        ),
    },
    {
        "id": "interface-displacement",
        "instruction": (
            "Question where intelligence, control, feedback, and visible "
            "identity need to live. Move them across boundaries when the "
            "result becomes simpler and more intuitive."
        ),
    },
)


_system = """
you are executing one bounded ideation operation inside savant.

opus owns provider orchestration.
underscore owns hidden structural alignment and discrimination.
urge owns iteration and revision pressure.

your task is not to imitate an existing creator, studio, product, brand,
genre, or fashionable visual language.

do not expose hidden chain-of-thought. return only concise concept
descriptions, mechanisms, rationale summaries, risks, and structured
metadata.

avoid default ai ideation behavior:
- generic futurism
- glowing neural imagery
- brains
- circuit-board symbolism
- infinity marks
- generic monograms
- arbitrary gradients
- meaningless geometric abstraction
- generic luxury minimalism
- generic brutalism
- generic cyberpunk
- generic disruption metaphors
- puzzle pieces
- lightbulbs
- rockets
- fingerprints
- shields
- swooshes
- globes
- hexagons used merely because they look technical
- literal subject depiction when a structural solution exists
- surface novelty presented as conceptual novelty

a concept earns novelty only when its underlying mechanism differs.
complexity does not earn novelty.
obscurity does not earn novelty.
randomness does not earn novelty.
unusability does not earn novelty.

return strict json only.
""".strip()


def _candidate_text(
    value: Mapping[
        str,
        Any,
    ],
) -> str:
    parts = [
        str(
            value.get(
                "name",
                "",
            )
        ).strip(),
        str(
            value.get(
                "concept",
                "",
            )
        ).strip(),
        str(
            value.get(
                "mechanism",
                "",
            )
        ).strip(),
        str(
            value.get(
                "rationale",
                "",
            )
        ).strip(),
    ]

    return " | ".join(
        part
        for part in parts
        if part
    )


def _normalize_candidates(
    value: Any,
    *,
    source: str,
) -> list[
    dict[str, Any]
]:
    if not isinstance(
        value,
        list,
    ):
        raise creative_orchestration_error(
            "candidate set must be a list"
        )

    output = []
    seen = set()

    for index, item in enumerate(
        value
    ):
        if not isinstance(
            item,
            Mapping,
        ):
            raise creative_orchestration_error(
                "candidate must be an object"
            )

        candidate = dict(
            item
        )

        text = _candidate_text(
            candidate
        )

        if not text:
            continue

        identity = _digest(
            {
                "text": text.casefold(),
            }
        )

        if identity in seen:
            continue

        seen.add(
            identity
        )

        candidate[
            "candidate_id"
        ] = (
            f"creative:{identity[:24]}"
        )

        candidate[
            "source"
        ] = source

        candidate[
            "text"
        ] = text

        candidate[
            "source_index"
        ] = index

        output.append(
            candidate
        )

    return output


class creative_engine:
    def __init__(
        self,
        run_policy: creative_policy
        | None = None,
    ) -> None:
        self.policy = (
            run_policy
            or creative_policy()
        )

        self.vessel = Vessel(
            cliche_threshold=(
                self.policy.cliche_threshold
            ),
            similarity_threshold=(
                self.policy.similarity_threshold
            ),
            frontier_size=(
                self.policy.frontier_size
            ),
            mmr_lambda=(
                self.policy.mmr_lambda
            ),
        )

    def _diverge(
        self,
        *,
        objective: str,
        constraints: Sequence[str],
        invariants: Sequence[str],
        cliches: Sequence[str],
        baselines: Sequence[str],
        context: Mapping[str, Any],
    ) -> tuple[
        list[dict[str, Any]],
        list[dict[str, Any]],
    ]:
        candidates = []
        lineage = []

        for index in range(
            self.policy.divergence_passes
        ):
            lens = _lenses[
                index
                % len(
                    _lenses
                )
            ]

            message = (
                "Generate "
                f"{self.policy.candidates_per_pass} "
                "structurally distinct candidate concepts.\n\n"
                f"objective: {objective}\n"
                f"lens: {lens['id']}\n"
                f"lens instruction: {lens['instruction']}\n\n"
                "constraints and invariants are binding. "
                "Known clichés and baselines are negative references, "
                "not ingredients.\n\n"
                "Return exactly this shape:\n"
                "{"
                "\"candidates\":[{"
                "\"name\":\"\","
                "\"concept\":\"\","
                "\"mechanism\":\"\","
                "\"rationale\":\"\","
                "\"assumption_broken\":\"\","
                "\"structural_difference\":\"\","
                "\"risk\":\"\","
                "\"test\":\"\""
                "}]"
                "}"
            )

            result = _opus_text(
                message=message,
                system=_system,
                context={
                    "objective": objective,
                    "constraints": list(
                        constraints
                    ),
                    "invariants": list(
                        invariants
                    ),
                    "cliches": list(
                        cliches
                    ),
                    "baselines": list(
                        baselines
                    ),
                    "context": dict(
                        context
                    ),
                },
            )

            parsed = _json_object(
                result[
                    "text"
                ]
            )

            batch = _normalize_candidates(
                parsed.get(
                    "candidates",
                    [],
                ),
                source=(
                    f"opus:{lens['id']}"
                ),
            )

            candidates.extend(
                batch
            )

            lineage.append(
                {
                    "stage": "divergence",
                    "lens": lens[
                        "id"
                    ],
                    "provider": result.get(
                        "provider"
                    ),
                    "model": result.get(
                        "model"
                    ),
                    "opus_lineage": result.get(
                        "lineage",
                        {},
                    ),
                    "candidate_ids": [
                        item[
                            "candidate_id"
                        ]
                        for item in batch
                    ],
                }
            )

        return (
            candidates,
            lineage,
        )

    def _discriminate(
        self,
        *,
        objective: str,
        candidates: Sequence[
            Mapping[str, Any]
        ],
        constraints: Sequence[str],
        cliches: Sequence[str],
        baselines: Sequence[str],
    ) -> dict[str, Any]:
        payload = {
            "subject": objective,
            "baselines": list(
                baselines
            ),
            "cliches": list(
                cliches
            ),
            "constraints": {
                "required": list(
                    constraints
                ),
                "forbidden": list(
                    cliches
                ),
            },
            "candidates": [
                {
                    "text": item[
                        "text"
                    ],
                    "source": item.get(
                        "source",
                        "opus",
                    ),
                    "lineage": [
                        item[
                            "candidate_id"
                        ]
                    ],
                }
                for item in candidates
            ],
        }

        return self.vessel.analyze(
            payload
        )

    def _frontier_candidates(
        self,
        *,
        candidates: Sequence[
            Mapping[str, Any]
        ],
        discrimination: Mapping[
            str,
            Any,
        ],
    ) -> list[
        dict[str, Any]
    ]:
        by_text = {
            item[
                "text"
            ]: dict(
                item
            )
            for item in candidates
        }

        ranked = discrimination.get(
            "ranked_candidates",
            []
        )

        ranked_by_id = {
            str(
                item.get(
                    "candidate_id",
                    "",
                )
            ): item
            for item in ranked
            if isinstance(
                item,
                Mapping,
            )
        }

        output = []

        for frontier in discrimination.get(
            "divergent_frontier",
            []
        ):
            if not isinstance(
                frontier,
                Mapping,
            ):
                continue

            vessel_id = str(
                frontier.get(
                    "candidate_id",
                    "",
                )
            )

            score = ranked_by_id.get(
                vessel_id
            )

            if not isinstance(
                score,
                Mapping,
            ):
                continue

            text = str(
                score.get(
                    "text",
                    "",
                )
            )

            original = by_text.get(
                text
            )

            if original is None:
                continue

            original[
                "underscore"
            ] = {
                "candidate_id": (
                    vessel_id
                ),
                "survivability_score": (
                    frontier.get(
                        "survivability_score"
                    )
                ),
                "subversion_score": (
                    frontier.get(
                        "subversion_score"
                    )
                ),
                "divergence_score": (
                    frontier.get(
                        "divergence_score"
                    )
                ),
                "cliche_risk": (
                    frontier.get(
                        "cliche_risk"
                    )
                ),
                "discriminants": (
                    score.get(
                        "discriminants",
                        [],
                    )
                ),
            }

            output.append(
                original
            )

        return output

    def _synthesize(
        self,
        *,
        objective: str,
        frontier: Sequence[
            Mapping[str, Any]
        ],
        constraints: Sequence[str],
        invariants: Sequence[str],
        cliches: Sequence[str],
        context: Mapping[str, Any],
    ) -> tuple[
        list[dict[str, Any]],
        dict[str, Any],
    ]:
        message = (
            "Perform adversarial synthesis on the surviving frontier. "
            "Do not merely combine candidates. Determine why each "
            "survived, identify incompatible strengths, identify "
            "compatible mechanisms, and create a new generation that "
            "is structurally farther from cliché while remaining more "
            "coherent and usable.\n\n"
            f"Generate {self.policy.synthesis_candidates} candidates.\n\n"
            "At least half must descend from one frontier mechanism "
            "through a non-cosmetic transformation. The remainder may "
            "combine mechanisms only when the combination creates a "
            "new causal structure.\n\n"
            "Return exactly:\n"
            "{"
            "\"candidates\":[{"
            "\"name\":\"\","
            "\"concept\":\"\","
            "\"mechanism\":\"\","
            "\"rationale\":\"\","
            "\"assumption_broken\":\"\","
            "\"structural_difference\":\"\","
            "\"risk\":\"\","
            "\"test\":\"\","
            "\"parents\":[]"
            "}]"
            "}"
        )

        result = _opus_text(
            message=message,
            system=_system,
            context={
                "objective": objective,
                "constraints": list(
                    constraints
                ),
                "invariants": list(
                    invariants
                ),
                "cliches": list(
                    cliches
                ),
                "frontier": list(
                    frontier
                ),
                "context": dict(
                    context
                ),
            },
        )

        parsed = _json_object(
            result[
                "text"
            ]
        )

        candidates = _normalize_candidates(
            parsed.get(
                "candidates",
                [],
            ),
            source="opus:synthesis",
        )

        lineage = {
            "stage": "synthesis",
            "provider": result.get(
                "provider"
            ),
            "model": result.get(
                "model"
            ),
            "opus_lineage": result.get(
                "lineage",
                {},
            ),
            "candidate_ids": [
                item[
                    "candidate_id"
                ]
                for item in candidates
            ],
        }

        return (
            candidates,
            lineage,
        )

    def project(
        self,
        *,
        objective: str,
        constraints: Sequence[str] = (),
        invariants: Sequence[str] = (),
        cliches: Sequence[str] = (),
        baselines: Sequence[str] = (),
        context: Mapping[
            str,
            Any,
        ] | None = None,
    ) -> dict[str, Any]:
        objective = str(
            objective
        ).strip()

        if not objective:
            raise creative_orchestration_error(
                "objective is required"
            )

        normalized_constraints = _strings(
            constraints
        )

        normalized_invariants = _strings(
            invariants
        )

        normalized_cliches = _strings(
            cliches
        )

        normalized_baselines = _strings(
            baselines
        )

        normalized_context = dict(
            context
            or {}
        )

        first_generation, lineage = (
            self._diverge(
                objective=objective,
                constraints=(
                    normalized_constraints
                ),
                invariants=(
                    normalized_invariants
                ),
                cliches=(
                    normalized_cliches
                ),
                baselines=(
                    normalized_baselines
                ),
                context=(
                    normalized_context
                ),
            )
        )

        if len(
            first_generation
        ) < 2:
            raise creative_orchestration_error(
                "divergence produced fewer than two candidates"
            )

        first_discrimination = (
            self._discriminate(
                objective=objective,
                candidates=(
                    first_generation
                ),
                constraints=(
                    normalized_constraints
                ),
                cliches=(
                    normalized_cliches
                ),
                baselines=(
                    normalized_baselines
                ),
            )
        )

        first_frontier = (
            self._frontier_candidates(
                candidates=(
                    first_generation
                ),
                discrimination=(
                    first_discrimination
                ),
            )
        )

        if not first_frontier:
            raise creative_orchestration_error(
                "underscore produced no surviving frontier"
            )

        synthesis, synthesis_lineage = (
            self._synthesize(
                objective=objective,
                frontier=(
                    first_frontier
                ),
                constraints=(
                    normalized_constraints
                ),
                invariants=(
                    normalized_invariants
                ),
                cliches=(
                    normalized_cliches
                ),
                context=(
                    normalized_context
                ),
            )
        )

        lineage.append(
            synthesis_lineage
        )

        combined = [
            *first_frontier,
            *synthesis,
        ]

        second_discrimination = (
            self._discriminate(
                objective=objective,
                candidates=combined,
                constraints=(
                    normalized_constraints
                ),
                cliches=(
                    normalized_cliches
                ),
                baselines=(
                    normalized_baselines
                ),
            )
        )

        final_frontier = (
            self._frontier_candidates(
                candidates=combined,
                discrimination=(
                    second_discrimination
                ),
            )
        )

        projection = {
            "schema": schema,
            "owner": owner,
            "authority_effect": "none",
            "projection_only": True,
            "objective": objective,
            "constraints": list(
                normalized_constraints
            ),
            "invariants": list(
                normalized_invariants
            ),
            "cliches": list(
                normalized_cliches
            ),
            "baselines": list(
                normalized_baselines
            ),
            "context": (
                normalized_context
            ),
            "first_generation": (
                first_generation
            ),
            "first_discrimination": (
                first_discrimination
            ),
            "first_frontier": (
                first_frontier
            ),
            "synthesis": synthesis,
            "final_discrimination": (
                second_discrimination
            ),
            "frontier": (
                final_frontier
            ),
            "lineage": lineage,
            "ownership": {
                "provider_orchestration": (
                    opus_owner
                ),
                "structural_discrimination": (
                    underscore_owner
                ),
                "iteration": owner,
            },
            "enhancements": [
                "multi-pass structural divergence",
                "orthogonal cognitive lenses",
                "primitive recomposition",
                "assumption inversion",
                "cross-domain mechanism transfer",
                "emergent compression",
                "negative-space reasoning",
                "causal inversion",
                "temporal reframing",
                "category-error probing",
                "constraint-driven identity",
                "second-order consequence search",
                "semantic paradox search",
                "interface displacement",
                "explicit cliche baselines",
                "sibling similarity pressure",
                "false-diversity rejection",
                "survivability scoring",
                "subversion scoring",
                "divergence scoring",
                "maximum marginal relevance frontier",
                "pareto-aware discrimination",
                "adversarial synthesis",
                "mechanism-before-surface selection",
                "provider fallback through opus",
                "provider lineage preservation",
                "candidate lineage preservation",
                "deterministic candidate identity",
                "bounded candidate generation",
                "non-authoritative projections",
            ],
            "boundaries": {
                "creates_authority": False,
                "mutates_canon": False,
                "mutates_source": False,
                "owns_provider_routing": False,
                "owns_underscore": False,
                "owns_iteration": True,
                "exposes_hidden_chain_of_thought": False,
            },
        }

        projection[
            "digest"
        ] = _digest(
            projection
        )

        return projection


__all__ = [
    "creative_engine",
    "creative_orchestration_error",
    "creative_policy",
]
