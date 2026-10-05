#!/usr/bin/env python3

from __future__ import annotations

import hashlib
import json
import sys
from typing import Any, Mapping, Sequence

try:
    from .trait_mesh import trait_requirement
except ImportError:
    from trait_mesh import trait_requirement


schema = "savant://runtime/opus/ideal-self-bridge/1.0.0"
owner = "opus"
authority_effect = "none"

envoy_request_schema = (
    "savant.envoy.ideal-self-opus-request.v1"
)

supported_traits = frozenset(
    {
        "analysis",
        "skepticism",
        "divergence",
        "falsification",
        "integration",
        "reasoning",
        "verification",
        "research",
        "memory",
        "planning",
        "counterfactual",
        "creativity",
        "precision",
        "restraint",
        "uncertainty",
        "communication",
    }
)

trait_aliases = {
    "reasoning": "analysis",
    "verification": "falsification",
    "research": "analysis",
    "memory": "integration",
    "planning": "analysis",
    "counterfactual": "divergence",
    "creativity": "divergence",
    "skepticism": "skepticism",
    "precision": "falsification",
    "restraint": "integration",
    "uncertainty": "skepticism",
    "communication": "integration",
}

trait_purposes = {
    "analysis": (
        "Construct rigorous reasoning while "
        "preserving the user's accepted "
        "identity and relevant context."
    ),
    "skepticism": (
        "Pressure-test assumptions, "
        "rationalizations, confidence, and "
        "unsupported conclusions without "
        "rewriting the user's identity."
    ),
    "divergence": (
        "Generate materially different "
        "possibilities, counterfactuals, and "
        "creative alternatives without "
        "premature convergence."
    ),
    "falsification": (
        "Verify consequential claims, seek "
        "counterexamples, and identify "
        "conditions that could invalidate "
        "the current conclusion."
    ),
    "integration": (
        "Integrate cognitive contributions "
        "while preserving identity, dissent, "
        "uncertainty, provenance, and the "
        "user's accepted aspirations."
    ),
}


class ideal_self_bridge_error(
    RuntimeError
):
    pass


def canonical_json(
    value: Any,
) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
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


def bounded_float(
    value: Any,
    *,
    default: float = 1.0,
) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError):
        result = default

    return max(
        0.0,
        min(
            1.0,
            result,
        ),
    )


def normalized_strings(
    values: Any,
) -> tuple[str, ...]:
    if not isinstance(
        values,
        (list, tuple, set),
    ):
        return ()

    return tuple(
        sorted(
            {
                str(value).strip()
                for value in values
                if str(value).strip()
            }
        )
    )


def validate_envoy_request(
    request: Mapping[str, Any],
) -> None:
    if not isinstance(
        request,
        Mapping,
    ):
        raise ideal_self_bridge_error(
            "ideal-self request must be "
            "an object"
        )

    if (
        request.get("schema")
        != envoy_request_schema
    ):
        raise ideal_self_bridge_error(
            "unsupported envoy ideal-self "
            "request schema"
        )

    if request.get("owner") not in (
        "envoy",
        "exile:envoy",
    ):
        raise ideal_self_bridge_error(
            "ideal-self request owner must "
            "be envoy"
        )

    if (
        request.get("execution_owner")
        != owner
    ):
        raise ideal_self_bridge_error(
            "ideal-self request must preserve "
            "opus execution ownership"
        )

    if (
        request.get("authority_effect")
        != "none"
    ):
        raise ideal_self_bridge_error(
            "ideal-self request must not "
            "create authority"
        )

    if request.get(
        "projection_only"
    ) is not True:
        raise ideal_self_bridge_error(
            "ideal-self request must be "
            "projection-only"
        )

    persona_id = str(
        request.get("persona_id") or ""
    ).strip()

    if not persona_id:
        raise ideal_self_bridge_error(
            "ideal-self request lacks "
            "persona_id"
        )

    ideal_digest = str(
        request.get(
            "ideal_self_digest"
        )
        or ""
    ).strip()

    if not ideal_digest:
        raise ideal_self_bridge_error(
            "ideal-self request lacks "
            "ideal_self_digest"
        )

    constraints = request.get(
        "constraints"
    )

    if not isinstance(
        constraints,
        Mapping,
    ):
        raise ideal_self_bridge_error(
            "ideal-self request lacks "
            "constraints"
        )

    required_true = (
        "preserve_identity",
        "preserve_values",
        "preserve_voice",
        "preserve_humor",
        "preserve_sarcasm",
        "preserve_idiosyncrasy",
        "accepted_corrections_only",
    )

    for field in required_true:
        if constraints.get(
            field
        ) is not True:
            raise ideal_self_bridge_error(
                "required ideal-self "
                f"constraint missing: {field}"
            )

    if (
        constraints.get(
            "provider_selection_owner"
        )
        != owner
    ):
        raise ideal_self_bridge_error(
            "provider selection ownership "
            "must remain opus"
        )

    if (
        constraints.get(
            "model_selection_owner"
        )
        != owner
    ):
        raise ideal_self_bridge_error(
            "model selection ownership "
            "must remain opus"
        )

    traits = request.get(
        "required_cognitive_traits"
    )

    if not isinstance(
        traits,
        list,
    ):
        raise ideal_self_bridge_error(
            "required_cognitive_traits "
            "must be a list"
        )


def normalize_trait(
    value: Mapping[str, Any],
) -> dict[str, Any]:
    source_trait = str(
        value.get("trait") or ""
    ).strip().lower()

    if not source_trait:
        raise ideal_self_bridge_error(
            "cognitive trait lacks trait id"
        )

    if source_trait not in supported_traits:
        raise ideal_self_bridge_error(
            "unsupported ideal-self "
            f"cognitive trait: {source_trait}"
        )

    opus_trait = trait_aliases.get(
        source_trait,
        source_trait,
    )

    if opus_trait not in trait_purposes:
        raise ideal_self_bridge_error(
            "ideal-self trait has no bounded "
            f"opus projection: {source_trait}"
        )

    reason = str(
        value.get("reason") or ""
    ).strip()

    if not reason:
        raise ideal_self_bridge_error(
            "cognitive trait lacks reason"
        )

    return {
        "source_trait": source_trait,
        "opus_trait": opus_trait,
        "strength": bounded_float(
            value.get("strength"),
            default=1.0,
        ),
        "reason": reason,
        "personality_trait_refs": (
            normalized_strings(
                value.get(
                    "personality_trait_refs"
                )
            )
        ),
        "evidence_refs": (
            normalized_strings(
                value.get(
                    "evidence_refs"
                )
            )
        ),
    }


def merge_traits(
    traits: Sequence[
        Mapping[str, Any]
    ],
) -> tuple[dict[str, Any], ...]:
    merged: dict[
        str,
        dict[str, Any],
    ] = {}

    for value in traits:
        normalized = normalize_trait(
            value
        )

        opus_trait = normalized[
            "opus_trait"
        ]

        state = merged.setdefault(
            opus_trait,
            {
                "trait_id": opus_trait,
                "source_traits": set(),
                "strength": 0.0,
                "reasons": set(),
                "personality_trait_refs": set(),
                "evidence_refs": set(),
            },
        )

        state["source_traits"].add(
            normalized["source_trait"]
        )

        state["strength"] = max(
            state["strength"],
            normalized["strength"],
        )

        state["reasons"].add(
            normalized["reason"]
        )

        state[
            "personality_trait_refs"
        ].update(
            normalized[
                "personality_trait_refs"
            ]
        )

        state["evidence_refs"].update(
            normalized["evidence_refs"]
        )

    result = []

    for trait_id in sorted(merged):
        state = merged[trait_id]

        result.append(
            {
                "trait_id": trait_id,
                "source_traits": sorted(
                    state["source_traits"]
                ),
                "strength": round(
                    state["strength"],
                    6,
                ),
                "reasons": sorted(
                    state["reasons"]
                ),
                "personality_trait_refs": (
                    sorted(
                        state[
                            "personality_trait_refs"
                        ]
                    )
                ),
                "evidence_refs": sorted(
                    state["evidence_refs"]
                ),
            }
        )

    return tuple(result)


def project_requirements(
    request: Mapping[str, Any],
) -> dict[str, Any]:
    validate_envoy_request(
        request
    )

    raw_traits = request[
        "required_cognitive_traits"
    ]

    merged = merge_traits(
        tuple(
            item
            for item in raw_traits
            if isinstance(
                item,
                Mapping,
            )
        )
    )

    requirements = []

    for item in merged:
        trait_id = item["trait_id"]

        requirement = trait_requirement(
            trait_id=trait_id,
            purpose=(
                trait_purposes[
                    trait_id
                ]
                + "\n\n"
                + "Ideal-self reason: "
                + "; ".join(
                    item["reasons"]
                )
            ),
            required_capabilities=(),
            required_layers=(),
            weight=item["strength"],
            independence_required=(
                trait_id
                in {
                    "analysis",
                    "skepticism",
                    "divergence",
                    "falsification",
                }
            ),
            adversarial=(
                trait_id
                in {
                    "skepticism",
                    "falsification",
                }
            ),
        )

        requirements.append(
            {
                "requirement": (
                    requirement
                ),
                "projection": (
                    requirement.projection()
                ),
                "source_traits": (
                    item["source_traits"]
                ),
                "personality_trait_refs": (
                    item[
                        "personality_trait_refs"
                    ]
                ),
                "evidence_refs": (
                    item["evidence_refs"]
                ),
            }
        )

    identity = {
        "persona_id": request[
            "persona_id"
        ],
        "ideal_self_digest": request[
            "ideal_self_digest"
        ],
        "domains": list(
            normalized_strings(
                request.get("domains")
            )
        ),
        "signals": list(
            normalized_strings(
                request.get("signals")
            )
        ),
        "requirements": [
            item["projection"]
            for item in requirements
        ],
        "lineage": [
            {
                "trait_id": (
                    item["projection"][
                        "trait_id"
                    ]
                ),
                "source_traits": (
                    item["source_traits"]
                ),
                "personality_trait_refs": (
                    item[
                        "personality_trait_refs"
                    ]
                ),
                "evidence_refs": (
                    item["evidence_refs"]
                ),
            }
            for item in requirements
        ],
    }

    return {
        "schema": schema,
        "owner": owner,
        "authority_effect": (
            authority_effect
        ),
        "projection_only": True,
        "bridge_id": stable_id(
            "opus-ideal-self-bridge",
            identity,
        ),
        "persona_id": request[
            "persona_id"
        ],
        "ideal_self_digest": request[
            "ideal_self_digest"
        ],
        "domains": identity[
            "domains"
        ],
        "signals": identity[
            "signals"
        ],
        "requirements": [
            item["projection"]
            for item in requirements
        ],
        "requirement_objects": [
            item["requirement"]
            for item in requirements
        ],
        "lineage": identity[
            "lineage"
        ],
        "boundaries": {
            "creates_authority": False,
            "changes_persona_authority": (
                False
            ),
            "changes_provider_registry": (
                False
            ),
            "changes_model_registry": False,
            "opus_selects_provider": False,
            "opus_trait_mesh_selects_provider": (
                False
            ),
            "resilient_text_retains_provider_selection": (
                True
            ),
            "envoy_selects_provider": False,
            "envoy_selects_model": False,
            "envoy_accesses_credentials": False,
            "accepted_corrections_only": True,
            "identity_preserved": True,
        },
        "projection_digest": digest(
            identity
        ),
    }


def mesh_arguments(
    request: Mapping[str, Any],
) -> dict[str, Any]:
    projection = project_requirements(
        request
    )

    return {
        "requirements": list(
            projection[
                "requirement_objects"
            ]
        ),
        "context": {
            "ideal_self": {
                "schema": schema,
                "bridge_id": projection[
                    "bridge_id"
                ],
                "persona_id": projection[
                    "persona_id"
                ],
                "ideal_self_digest": (
                    projection[
                        "ideal_self_digest"
                    ]
                ),
                "domains": projection[
                    "domains"
                ],
                "signals": projection[
                    "signals"
                ],
                "lineage": projection[
                    "lineage"
                ],
                "authority_effect": (
                    authority_effect
                ),
                "projection_only": True,
            }
        },
    }


def selftest() -> dict[str, Any]:
    request = {
        "schema": envoy_request_schema,
        "owner": "exile:envoy",
        "execution_owner": "opus",
        "authority_effect": "none",
        "projection_only": True,
        "persona_id": "persona:selftest",
        "ideal_self_digest": (
            "ideal-self-test-digest"
        ),
        "domains": [
            "analysis",
            "conversation",
        ],
        "signals": [
            "reason",
            "verify",
        ],
        "required_cognitive_traits": [
            {
                "trait": "restraint",
                "strength": 0.85,
                "reason": (
                    "retain directness with "
                    "greater restraint"
                ),
                "personality_trait_refs": [
                    "trait:restraint:"
                    "aspiration"
                ],
                "evidence_refs": [
                    "evidence:restraint"
                ],
            },
            {
                "trait": "verification",
                "strength": 0.9,
                "reason": (
                    "verify consequential "
                    "claims before commitment"
                ),
                "personality_trait_refs": [
                    "trait:verification:"
                    "aspiration"
                ],
                "evidence_refs": [
                    "evidence:verification"
                ],
            },
            {
                "trait": "counterfactual",
                "strength": 0.8,
                "reason": (
                    "consider materially "
                    "different outcomes"
                ),
                "personality_trait_refs": [
                    "trait:deliberation:"
                    "aspiration"
                ],
                "evidence_refs": [
                    "evidence:deliberation"
                ],
            },
        ],
        "constraints": {
            "preserve_identity": True,
            "preserve_values": True,
            "preserve_voice": True,
            "preserve_humor": True,
            "preserve_sarcasm": True,
            "preserve_idiosyncrasy": True,
            "accepted_corrections_only": True,
            "provider_selection_owner": (
                "opus"
            ),
            "model_selection_owner": (
                "opus"
            ),
        },
    }

    first = project_requirements(
        request
    )

    second = project_requirements(
        request
    )

    comparable_first = {
        key: value
        for key, value in first.items()
        if key != "requirement_objects"
    }

    comparable_second = {
        key: value
        for key, value in second.items()
        if key != "requirement_objects"
    }

    if (
        comparable_first
        != comparable_second
    ):
        raise ideal_self_bridge_error(
            "bridge projection is not "
            "deterministic"
        )

    trait_ids = [
        item["trait_id"]
        for item in first[
            "requirements"
        ]
    ]

    expected = [
        "divergence",
        "falsification",
        "integration",
    ]

    if trait_ids != expected:
        raise ideal_self_bridge_error(
            "trait projection failed: "
            f"{trait_ids!r}"
        )

    arguments = mesh_arguments(
        request
    )

    objects = arguments[
        "requirements"
    ]

    if not all(
        isinstance(
            item,
            trait_requirement,
        )
        for item in objects
    ):
        raise ideal_self_bridge_error(
            "trait mesh requirement "
            "projection failed"
        )

    boundaries = first[
        "boundaries"
    ]

    if boundaries[
        "creates_authority"
    ]:
        raise ideal_self_bridge_error(
            "bridge created authority"
        )

    if boundaries[
        "envoy_selects_provider"
    ]:
        raise ideal_self_bridge_error(
            "envoy provider boundary failed"
        )

    if boundaries[
        "envoy_selects_model"
    ]:
        raise ideal_self_bridge_error(
            "envoy model boundary failed"
        )

    if not boundaries[
        "resilient_text_retains_provider_selection"
    ]:
        raise ideal_self_bridge_error(
            "provider-selection ownership "
            "was not preserved"
        )

    return {
        "schema": schema,
        "owner": owner,
        "ok": True,
        "deterministic": True,
        "envoy_request_schema": (
            envoy_request_schema
        ),
        "projected_traits": (
            trait_ids
        ),
        "trait_requirement_compatible": (
            True
        ),
        "identity_preserved": True,
        "accepted_corrections_only": True,
        "envoy_provider_authority": False,
        "envoy_model_authority": False,
        "provider_selection_owner": (
            "resilient_text"
        ),
        "authority_effect": (
            authority_effect
        ),
        "digest": first[
            "projection_digest"
        ],
    }


def main(
    argv: list[str],
) -> int:
    if (
        len(argv) != 2
        or argv[1] != "--selftest"
    ):
        print(
            "usage: ideal_self_bridge.py "
            "--selftest",
            file=sys.stderr,
        )
        return 2

    print(
        json.dumps(
            selftest(),
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main(sys.argv)
    )
