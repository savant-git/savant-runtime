from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

from .creative_orchestration import (
    creative_engine,
    creative_policy,
)
from .logo_intelligence import (
    project as project_logo_intelligence,
)
from .praxis import (
    CAPABILITY as PRAXIS_CAPABILITY,
    execute_step as execute_praxis_step,
)
from .praxis_live import (
    CAPABILITY as PRAXIS_LIVE_CAPABILITY,
    execute as execute_praxis_rigor,
)
from .renderer_slot import (
    project as project_renderer,
    renderer_binding,
)
from .workbench_projection import (
    project as project_workbench,
)


CAPABILITY = "exile:urge:iterate"

SCHEMA = (
    "savant://runtime/urge/"
    "execution-binding/1.2.0"
)

OWNER = "exile:urge"


class urge_execution_error(
    RuntimeError
):
    pass


def _mapping(
    value: Any,
    *,
    field: str,
) -> dict[str, Any]:
    if value is None:
        return {}

    if not isinstance(
        value,
        Mapping,
    ):
        raise urge_execution_error(
            field
            + " must be a mapping"
        )

    return deepcopy(
        dict(
            value
        )
    )


def _strings(
    value: Any,
    *,
    field: str,
) -> tuple[str, ...]:
    if value is None:
        return ()

    if isinstance(
        value,
        str,
    ):
        values = value.splitlines()
    elif isinstance(
        value,
        (
            list,
            tuple,
        ),
    ):
        values = value
    else:
        raise urge_execution_error(
            field
            + " must be text or a sequence"
        )

    return tuple(
        str(
            item
        ).strip()
        for item in values
        if str(
            item
        ).strip()
    )


def _policy(
    value: Any,
) -> creative_policy:
    if value is None:
        return creative_policy()

    if isinstance(
        value,
        creative_policy,
    ):
        return value

    if not isinstance(
        value,
        Mapping,
    ):
        raise urge_execution_error(
            "creative_policy must be "
            "a mapping"
        )

    allowed = {
        "candidate_count",
        "minimum_score",
        "maximum_rounds",
        "divergence_pressure",
        "adversarial_pressure",
        "convergence_pressure",
    }

    unknown = (
        set(
            value
        )
        - allowed
    )

    if unknown:
        raise urge_execution_error(
            "unknown creative_policy fields: "
            + ", ".join(
                sorted(
                    unknown
                )
            )
        )

    return creative_policy(
        **{
            key:
                value[
                    key
                ]
            for key in allowed
            if key in value
        }
    )


def normalize_request(
    payload: Mapping[
        str,
        Any,
    ],
) -> dict[str, Any]:
    if not isinstance(
        payload,
        Mapping,
    ):
        raise urge_execution_error(
            "payload must be a mapping"
        )

    mode = str(
        payload.get(
            "mode",
            "creative",
        )
    ).strip().lower()

    if mode not in {
        "creative",
        "logo",
    }:
        raise urge_execution_error(
            "mode must be creative or logo"
        )

    objective = str(
        payload.get(
            "objective",
            "",
        )
    ).strip()

    if not objective:
        raise urge_execution_error(
            "objective is required"
        )

    name = str(
        payload.get(
            "name",
            "",
        )
    ).strip()

    if (
        mode == "logo"
        and not name
    ):
        raise urge_execution_error(
            "name is required for logo mode"
        )

    constraints = _strings(
        payload.get(
            "constraints"
        ),
        field="constraints",
    )

    invariants = _strings(
        payload.get(
            "invariants"
        ),
        field="invariants",
    )

    cliches = _strings(
        payload.get(
            "cliches"
        ),
        field="cliches",
    )

    baselines = _strings(
        payload.get(
            "baselines"
        ),
        field="baselines",
    )

    brief = _mapping(
        payload.get(
            "brief"
        ),
        field="brief",
    )

    context = _mapping(
        payload.get(
            "context"
        ),
        field="context",
    )

    renderer = payload.get(
        "renderer"
    )

    if (
        renderer is not None
        and not isinstance(
            renderer,
            renderer_binding,
        )
    ):
        raise urge_execution_error(
            "renderer must be a "
            "renderer_binding"
        )

    return {
        "mode":
            mode,
        "objective":
            objective,
        "name":
            name,
        "constraints":
            constraints,
        "invariants":
            invariants,
        "cliches":
            cliches,
        "baselines":
            baselines,
        "brief":
            brief,
        "context":
            context,
        "creative_policy":
            _policy(
                payload.get(
                    "creative_policy"
                )
            ),
        "renderer":
            renderer,
    }


def _creative_projection(
    *,
    request: Mapping[
        str,
        Any,
    ],
    policy: creative_policy,
) -> dict[str, Any]:
    context = deepcopy(
        request[
            "context"
        ]
    )

    context.setdefault(
        "mode",
        request[
            "mode"
        ],
    )

    engine = creative_engine(
        policy
    )

    return engine.project(
        objective=request[
            "objective"
        ],
        constraints=request[
            "constraints"
        ],
        invariants=request[
            "invariants"
        ],
        cliches=request[
            "cliches"
        ],
        baselines=request[
            "baselines"
        ],
        context=context,
    )


def _logo_projection(
    *,
    request: Mapping[
        str,
        Any,
    ],
    policy: creative_policy,
) -> dict[str, Any]:
    brief = deepcopy(
        request[
            "brief"
        ]
    )

    if request[
        "context"
    ]:
        brief.setdefault(
            "context",
            deepcopy(
                request[
                    "context"
                ]
            ),
        )

    return project_logo_intelligence(
        name=request[
            "name"
        ],
        brief=brief,
        objective=request[
            "objective"
        ],
        constraints=request[
            "constraints"
        ],
        protected_invariants=request[
            "invariants"
        ],
        known_cliches=request[
            "cliches"
        ],
        references_to_avoid=request[
            "baselines"
        ],
        run_policy=policy,
    )


def execute(
    payload: Mapping[
        str,
        Any,
    ],
) -> dict[str, Any]:
    request = normalize_request(
        payload
    )

    policy = request[
        "creative_policy"
    ]

    if request[
        "mode"
    ] == "logo":
        logo = _logo_projection(
            request=request,
            policy=policy,
        )

        creative = logo[
            "creative_projection"
        ]
    else:
        logo = None

        creative = _creative_projection(
            request=request,
            policy=policy,
        )

    renderer = project_renderer(
        candidate=(
            logo
            if logo is not None
            else creative
        ),
        binding=request[
            "renderer"
        ],
        context={
            **request[
                "context"
            ],
            "urge_capability":
                CAPABILITY,
            "mode":
                request[
                    "mode"
                ],
        },
    )

    workbench = project_workbench(
        creative=creative,
        logo=logo,
        renderer=renderer,
    )

    return {
        "schema":
            SCHEMA,
        "owner":
            OWNER,
        "capability":
            CAPABILITY,
        "mode":
            request[
                "mode"
            ],
        "creative":
            creative,
        "logo":
            logo,
        "renderer":
            renderer,
        "workbench":
            workbench,
        "ownership": {
            "creative_pressure":
                OWNER,
            "provider_orchestration":
                "exile:opus",
            "renderer":
                renderer.get(
                    "renderer",
                    {},
                ).get(
                    "owner"
                ),
        },
        "boundaries": {
            "creates_authority":
                False,
            "mutates_canon":
                False,
            "mutates_source":
                False,
            "owns_provider_routing":
                False,
            "owns_discrimination":
                False,
            "owns_renderer":
                False,
            "iteration_owner":
                OWNER,
        },
    }


def register(
    dispatcher: Any,
) -> str:
    if not hasattr(
        dispatcher,
        "register",
    ):
        raise urge_execution_error(
            "dispatcher does not expose "
            "register"
        )

    dispatcher.register(
        CAPABILITY,
        execute,
    )

    dispatcher.register(
        PRAXIS_CAPABILITY,
        execute_praxis_step,
    )

    dispatcher.register(
        PRAXIS_LIVE_CAPABILITY,
        execute_praxis_rigor,
    )

    return CAPABILITY


__all__ = [
    "CAPABILITY",
    "OWNER",
    "PRAXIS_CAPABILITY",
    "PRAXIS_LIVE_CAPABILITY",
    "SCHEMA",
    "execute",
    "execute_praxis_rigor",
    "execute_praxis_step",
    "normalize_request",
    "register",
    "urge_execution_error",
]
