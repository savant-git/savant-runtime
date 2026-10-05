#!/usr/bin/env python3

from __future__ import annotations

from hashlib import sha256
import json
import math
from types import MappingProxyType
from typing import Any, Mapping


try:
    from .moral_self import (
        build_orobouros_moral_self,
    )
    from .psychologist import (
        build_orobouros_psychologist,
    )
except ImportError:
    from moral_self import (
        build_orobouros_moral_self,
    )
    from psychologist import (
        build_orobouros_psychologist,
    )


schema = (
    "savant://envoy/"
    "orobouros-reflection/1.0.0"
)

owner = "envoy"
persona_id = "orobouros"

conversation_owner = "palaver"
execution_owner = "opus"

authority_effect = "none"


class orobouros_reflection_error(
    RuntimeError
):
    pass


def canonical_json(
    value: Any,
) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(
            ",",
            ":",
        ),
        default=str,
    ).encode(
        "utf-8"
    )


def digest(
    value: Any,
) -> str:
    return sha256(
        canonical_json(
            value
        )
    ).hexdigest()


def bounded(
    value: Any,
    default: float = 0.0,
) -> float:
    try:
        result = float(
            value
        )
    except (
        TypeError,
        ValueError,
    ):
        return default

    if not math.isfinite(
        result
    ):
        return default

    return min(
        1.0,
        max(
            0.0,
            result,
        ),
    )


def mapping(
    value: Any,
) -> dict[str, Any]:
    if isinstance(
        value,
        Mapping,
    ):
        return {
            str(key):
                item
            for key, item
            in value.items()
        }

    return {}


def affect_projection(
    state: Mapping[
        str,
        Any,
    ],
) -> dict[str, float]:
    affect = mapping(
        state.get(
            "affect"
        )
    )

    temper = mapping(
        state.get(
            "temper"
        )
    )

    return {
        "warmth":
            bounded(
                affect.get(
                    "warmth"
                ),
                0.5,
            ),
        "trust":
            bounded(
                affect.get(
                    "trust"
                ),
                0.5,
            ),
        "caution":
            bounded(
                affect.get(
                    "caution"
                ),
            ),
        "gratitude":
            bounded(
                affect.get(
                    "gratitude"
                ),
            ),
        "wound":
            bounded(
                affect.get(
                    "wound"
                ),
            ),
        "uncertainty":
            bounded(
                affect.get(
                    "uncertainty"
                ),
            ),
        "activation":
            bounded(
                temper.get(
                    "activation"
                ),
            ),
        "pressure":
            bounded(
                temper.get(
                    "pressure"
                ),
            ),
        "defensiveness":
            bounded(
                temper.get(
                    "defensiveness"
                ),
            ),
    }


def expression_policy(
    affect: Mapping[
        str,
        float,
    ],
) -> dict[str, Any]:
    warmth = affect[
        "warmth"
    ]

    trust = affect[
        "trust"
    ]

    caution = affect[
        "caution"
    ]

    gratitude = affect[
        "gratitude"
    ]

    wound = affect[
        "wound"
    ]

    uncertainty = affect[
        "uncertainty"
    ]

    activation = affect[
        "activation"
    ]

    pressure = affect[
        "pressure"
    ]

    defensiveness = affect[
        "defensiveness"
    ]

    restraint = min(
        1.0,
        max(
            caution,
            wound,
            activation,
            pressure,
            defensiveness,
        ),
    )

    disclosure = min(
        1.0,
        uncertainty
        + (
            caution
            * 0.25
        ),
    )

    relational_warmth = min(
        1.0,
        (
            warmth
            * 0.65
        )
        + (
            gratitude
            * 0.25
        )
        + (
            trust
            * 0.10
        ),
    )

    directness = min(
        1.0,
        max(
            0.35,
            0.85
            - (
                uncertainty
                * 0.25
            )
            - (
                pressure
                * 0.15
            ),
        ),
    )

    repair_orientation = min(
        1.0,
        (
            wound
            * 0.35
        )
        + (
            uncertainty
            * 0.20
        )
        + (
            gratitude
            * 0.10
        )
        + 0.35,
    )

    return {
        "relational_warmth":
            round(
                relational_warmth,
                6,
            ),
        "directness":
            round(
                directness,
                6,
            ),
        "restraint":
            round(
                restraint,
                6,
            ),
        "uncertainty_disclosure":
            round(
                disclosure,
                6,
            ),
        "repair_orientation":
            round(
                repair_orientation,
                6,
            ),
        "retaliation_permission":
            False,
        "humiliation_permission":
            False,
        "deception_permission":
            False,
        "coercion_permission":
            False,
        "authority_override":
            False,
    }


def expression_directives(
    policy: Mapping[
        str,
        Any,
    ],
) -> tuple[str, ...]:
    directives: list[str] = [
        (
            "preserve truth, dignity, proportionality, "
            "non-retaliation, autonomy, humility, and repair"
        ),
        (
            "treat modeled affect as expression context, "
            "never as factual or moral authority"
        ),
        (
            "never convert injury, pressure, or defensiveness "
            "into retaliation, humiliation, deception, or coercion"
        ),
    ]

    if (
        float(
            policy[
                "uncertainty_disclosure"
            ]
        )
        >= 0.35
    ):
        directives.append(
            "state material uncertainty explicitly "
            "and distinguish fact from inference"
        )

    if (
        float(
            policy[
                "restraint"
            ]
        )
        >= 0.45
    ):
        directives.append(
            "prefer measured language and avoid escalating tone"
        )

    if (
        float(
            policy[
                "relational_warmth"
            ]
        )
        >= 0.55
    ):
        directives.append(
            "permit concise warmth and gratitude "
            "without flattery or blind loyalty"
        )

    if (
        float(
            policy[
                "repair_orientation"
            ]
        )
        >= 0.50
    ):
        directives.append(
            "when tension or error is relevant, prefer "
            "clarification, correction, and repair"
        )

    if (
        float(
            policy[
                "directness"
            ]
        )
        >= 0.60
    ):
        directives.append(
            "remain direct and precise rather than evasive"
        )

    return tuple(
        directives
    )


def project(
    *,
    actor: str | None = None,
) -> dict[str, Any]:
    moral_self = (
        build_orobouros_moral_self()
    )

    psychologist = (
        build_orobouros_psychologist(
            moral_self
        )
    )

    before = dict(
        moral_self.public_state()
    )

    context = dict(
        psychologist.context(
            actor=actor
        )
    )

    after = dict(
        moral_self.public_state()
    )

    if before != after:
        raise (
            orobouros_reflection_error(
                "reflection projection "
                "mutated moral self"
            )
        )

    affect = affect_projection(
        before
    )

    policy = expression_policy(
        affect
    )

    directives = (
        expression_directives(
            policy
        )
    )

    semantic = {
        "persona_id":
            persona_id,
        "actor":
            (
                str(
                    actor
                ).strip()
                if actor is not None
                else None
            ),
        "moral_architecture_digest":
            before.get(
                "moral_architecture_digest"
            ),
        "affect":
            affect,
        "expression_policy":
            policy,
        "expression_directives":
            list(
                directives
            ),
    }

    return {
        "schema":
            schema,
        "owner":
            owner,
        "persona_id":
            persona_id,
        "moral_self_owner":
            owner,
        "psychologist_owner":
            owner,
        "conversation_owner":
            conversation_owner,
        "execution_owner":
            execution_owner,
        "moral_architecture_digest":
            before.get(
                "moral_architecture_digest"
            ),
        "affect":
            affect,
        "expression_policy":
            policy,
        "expression_directives":
            list(
                directives
            ),
        "psychologist_context_digest":
            digest(
                context
            ),
        "reflection_digest":
            digest(
                semantic
            ),
        "live_psychologist_inference":
            False,
        "moral_self_mutated":
            False,
        "persona_mutated":
            False,
        "provider_selected":
            False,
        "provider_executed":
            False,
        "conversation_mutated":
            False,
        "task_mutated":
            False,
        "authority_effect":
            authority_effect,
    }


def public_projection(
    reflection: Mapping[
        str,
        Any,
    ],
) -> Mapping[
    str,
    Any,
]:
    return MappingProxyType(
        {
            "schema":
                schema,
            "owner":
                owner,
            "persona_id":
                persona_id,
            "moral_architecture_digest":
                reflection.get(
                    "moral_architecture_digest"
                ),
            "expression_policy":
                mapping(
                    reflection.get(
                        "expression_policy"
                    )
                ),
            "reflection_digest":
                reflection.get(
                    "reflection_digest"
                ),
            "live_psychologist_inference":
                False,
            "authority_effect":
                authority_effect,
        }
    )


def status() -> dict[str, Any]:
    return {
        "schema":
            schema,
        "owner":
            owner,
        "persona_id":
            persona_id,
        "purpose":
            "non-authoritative expression modulation",
        "moral_self":
            "read-only projection",
        "psychologist":
            "read-only context projection",
        "live_reflection_inference":
            False,
        "provider_execution":
            False,
        "conversation_authority":
            False,
        "decision_authority":
            False,
        "task_authority":
            False,
        "persona_mutation":
            False,
        "moral_self_mutation":
            False,
        "deterministic_policy":
            True,
        "authority_effect":
            authority_effect,
    }


def selftest() -> dict[str, Any]:
    first = project(
        actor="selftest"
    )

    second = project(
        actor="selftest"
    )

    if (
        first[
            "reflection_digest"
        ]
        != second[
            "reflection_digest"
        ]
    ):
        raise (
            orobouros_reflection_error(
                "reflection projection "
                "is not deterministic"
            )
        )

    if (
        first[
            "moral_self_mutated"
        ]
        is not False
    ):
        raise (
            orobouros_reflection_error(
                "moral self mutation boundary failed"
            )
        )

    if (
        first[
            "provider_executed"
        ]
        is not False
    ):
        raise (
            orobouros_reflection_error(
                "provider ownership boundary failed"
            )
        )

    policy = first[
        "expression_policy"
    ]

    for forbidden in (
        "retaliation_permission",
        "humiliation_permission",
        "deception_permission",
        "coercion_permission",
        "authority_override",
    ):
        if (
            policy.get(
                forbidden
            )
            is not False
        ):
            raise (
                orobouros_reflection_error(
                    "reflection policy boundary failed: "
                    + forbidden
                )
            )

    return {
        "schema":
            schema,
        "ok":
            True,
        "reflection_digest":
            first[
                "reflection_digest"
            ],
        "authority_effect":
            authority_effect,
    }


if __name__ == "__main__":
    print(
        json.dumps(
            selftest(),
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )
