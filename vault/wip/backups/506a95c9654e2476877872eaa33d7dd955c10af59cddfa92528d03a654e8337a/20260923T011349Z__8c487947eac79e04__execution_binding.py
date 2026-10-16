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
from .renderer_slot import (
    project as project_renderer,
    renderer_binding,
)
from .workbench_projection import (
    project_workbench,
)


CAPABILITY = "exile:urge:iterate"

SCHEMA = (
    "savant://runtime/urge/"
    "execution-binding/1.0.0"
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
            f"{field} must be a mapping"
        )

    return deepcopy(
        dict(value)
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
        value = (
            value,
        )

    if not isinstance(
        value,
        (
            list,
            tuple,
        ),
    ):
        raise urge_execution_error(
            f"{field} must be a sequence"
        )

    output: list[str] = []
    seen: set[str] = set()

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

    mode = str(
        payload.get(
            "mode",
            "job",
        )
    ).strip().lower()

    if mode not in {
        "job",
        "logo",
    }:
        raise urge_execution_error(
            "mode must be job or logo"
        )

    name = str(
        payload.get(
            "name",
            "",
        )
    ).strip()

    brief = _mapping(
        payload.get(
            "brief",
        ),
        field="brief",
    )

    if mode == "logo":
        if not name:
            name = str(
                brief.get(
                    "name",
                    "",
                )
            ).strip()

        if not name:
            raise urge_execution_error(
                "name is required "
                "for logo mode"
            )

    return {
        "objective":
            objective,
        "mode":
            mode,
        "name":
            name,
        "brief":
            brief,
        "constraints":
            _strings(
                payload.get(
                    "constraints",
                ),
                field="constraints",
            ),
        "invariants":
            _strings(
                payload.get(
                    "invariants",
                ),
                field="invariants",
            ),
        "cliches":
            _strings(
                payload.get(
                    "cliches",
                ),
                field="cliches",
            ),
        "baselines":
            _strings(
                payload.get(
                    "baselines",
                ),
                field="baselines",
            ),
        "context":
            _mapping(
                payload.get(
                    "context",
                ),
                field="context",
            ),
        "creative_policy":
            _mapping(
                payload.get(
                    "creative_policy",
                ),
                field="creative_policy",
            ),
        "renderer":
            payload.get(
                "renderer"
            ),
    }


def _policy(
    values: Mapping[
        str,
        Any,
    ],
) -> creative_policy:
    allowed = {
        "divergence_passes",
        "candidates_per_pass",
        "frontier_size",
        "mutation_depth",
        "synthesis_candidates",
        "cliche_threshold",
        "similarity_threshold",
        "mmr_lambda",
    }

    unknown = (
        set(values)
        - allowed
    )

    if unknown:
        names = ", ".join(
            sorted(
                unknown
            )
        )

        raise urge_execution_error(
            "unknown creative policy "
            f"fields: {names}"
        )

    try:
        return creative_policy(
            **dict(values)
        )
    except (
        TypeError,
        ValueError,
    ) as exc:
        raise urge_execution_error(
            "invalid creative policy: "
            f"{exc}"
        ) from exc


def _renderer_binding(
    value: Any,
) -> renderer_binding | None:
    if value is None:
        return None

    if isinstance(
        value,
        renderer_binding,
    ):
        return value

    raise urge_execution_error(
        "renderer must be a "
        "renderer_binding instance"
    )


def _creative_projection(
    *,
    request: Mapping[
        str,
        Any,
    ],
    policy: creative_policy,
) -> dict[str, Any]:
    engine = creative_engine(
        policy
    )

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

    policy = _policy(
        request[
            "creative_policy"
        ]
    )

    if (
        request[
            "mode"
        ]
        == "logo"
    ):
        logo = _logo_projection(
            request=request,
            policy=policy,
        )

        creative = logo[
            "creative_projection"
        ]

        renderer_candidate = logo

    else:
        logo = None

        creative = (
            _creative_projection(
                request=request,
                policy=policy,
            )
        )

        renderer_candidate = (
            creative
        )

    renderer = project_renderer(
        candidate=(
            renderer_candidate
        ),
        binding=_renderer_binding(
            request[
                "renderer"
            ]
        ),
        context={
            "urge_capability":
                CAPABILITY,
            "mode":
                request[
                    "mode"
                ],
            "objective":
                request[
                    "objective"
                ],
        },
    )

    workbench = project_workbench(
        creative=creative,
        logo=logo,
        renderer=renderer,
    )

    public_request = {
        key: deepcopy(
            value
        )
        for key, value
        in request.items()
        if key != "renderer"
    }

    return {
        "schema":
            SCHEMA,
        "owner":
            OWNER,
        "capability":
            CAPABILITY,
        "request":
            public_request,
        "creative":
            creative,
        "logo":
            logo,
        "renderer":
            renderer,
        "workbench":
            workbench,
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

    return CAPABILITY


__all__ = [
    "CAPABILITY",
    "OWNER",
    "SCHEMA",
    "execute",
    "normalize_request",
    "register",
    "urge_execution_error",
]
