from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from .creative_orchestration import (
    creative_policy,
)
from .image_renderer import (
    binding as image_renderer_binding,
)
from .logo_intelligence import (
    project as project_logo_intelligence,
)
from .renderer_slot import (
    project as project_renderer,
)
from .workbench_projection import (
    project as project_workbench,
)


SCHEMA = "savant://runtime/urge/praxis/1.1.0"
STEP_SCHEMA = "savant://runtime/urge/praxis-step/1.1.0"
OWNER = "exile:urge"

CAPABILITY = "exile:urge:praxis-step"

MIN_ITERATIONS = 1
MAX_ITERATIONS = 250
MIN_INTERVAL_MS = 0
MAX_INTERVAL_MS = 86_400_000


class praxis_error(
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
        raise praxis_error(
            "praxis projection must be "
            "canonical-json serializable"
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
        raise praxis_error(
            f"{field} must be a mapping"
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
        value = (
            value,
        )

    if not isinstance(
        value,
        Sequence,
    ):
        raise praxis_error(
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


def _bounded_int(
    value: Any,
    *,
    field: str,
    minimum: int,
    maximum: int,
) -> int:
    try:
        number = int(
            value
        )
    except (
        TypeError,
        ValueError,
    ) as exc:
        raise praxis_error(
            f"{field} must be an integer"
        ) from exc

    if (
        number < minimum
        or number > maximum
    ):
        raise praxis_error(
            f"{field} must be between "
            f"{minimum} and {maximum}"
        )

    return number


def _normalize_baseline(
    value: Any,
) -> dict[str, Any] | None:
    if value is None:
        return None

    baseline = _mapping(
        value,
        field="baseline",
    )

    kind = str(
        baseline.get(
            "kind",
            "image",
        )
    ).strip().lower()

    if kind != "image":
        raise praxis_error(
            "baseline kind must be image"
        )

    source = str(
        baseline.get(
            "source",
            "",
        )
    ).strip()

    if not source:
        raise praxis_error(
            "baseline source is required"
        )

    name = str(
        baseline.get(
            "name",
            "baseline",
        )
    ).strip() or "baseline"

    media_type = str(
        baseline.get(
            "media_type",
            "",
        )
    ).strip().lower()

    if not media_type.startswith(
        "image/"
    ):
        raise praxis_error(
            "baseline media_type must be image/*"
        )

    digest = str(
        baseline.get(
            "digest",
            "",
        )
    ).strip()

    if not digest:
        digest = hashlib.sha256(
            source.encode(
                "utf-8"
            )
        ).hexdigest()

    return {
        "kind": "image",
        "name": name,
        "media_type":
            media_type,
        "source": source,
        "digest": digest,
    }


@dataclass(
    frozen=True,
    slots=True,
)
class praxis_parameters:
    objective: str
    name: str
    iterations: int
    interval_ms: int
    baseline: dict[
        str,
        Any,
    ] | None
    constraints: tuple[
        str,
        ...,
    ]
    invariants: tuple[
        str,
        ...,
    ]
    cliches: tuple[
        str,
        ...,
    ]
    context: dict[
        str,
        Any,
    ]
    creative_policy: dict[
        str,
        Any,
    ]

    def public_projection(
        self,
    ) -> dict[str, Any]:
        baseline = None

        if (
            self.baseline
            is not None
        ):
            baseline = {
                key:
                    deepcopy(
                        value
                    )
                for key, value
                in self.baseline.items()
                if key != "source"
            }

        return {
            "objective":
                self.objective,
            "name":
                self.name,
            "iterations":
                self.iterations,
            "interval_ms":
                self.interval_ms,
            "baseline":
                baseline,
            "constraints":
                list(
                    self.constraints
                ),
            "invariants":
                list(
                    self.invariants
                ),
            "cliches":
                list(
                    self.cliches
                ),
            "context":
                deepcopy(
                    self.context
                ),
            "creative_policy":
                deepcopy(
                    self.creative_policy
                ),
        }


def normalize_parameters(
    payload: Mapping[
        str,
        Any,
    ],
) -> praxis_parameters:
    if not isinstance(
        payload,
        Mapping,
    ):
        raise praxis_error(
            "payload must be a mapping"
        )

    objective = str(
        payload.get(
            "objective",
            "",
        )
    ).strip()

    if not objective:
        raise praxis_error(
            "objective is required"
        )

    name = str(
        payload.get(
            "name",
            "",
        )
    ).strip()

    if not name:
        raise praxis_error(
            "logo name is required"
        )

    iterations = _bounded_int(
        payload.get(
            "iterations",
            8,
        ),
        field="iterations",
        minimum=MIN_ITERATIONS,
        maximum=MAX_ITERATIONS,
    )

    interval_ms = _bounded_int(
        payload.get(
            "interval_ms",
            1500,
        ),
        field="interval_ms",
        minimum=MIN_INTERVAL_MS,
        maximum=MAX_INTERVAL_MS,
    )

    return praxis_parameters(
        objective=objective,
        name=name,
        iterations=iterations,
        interval_ms=interval_ms,
        baseline=(
            _normalize_baseline(
                payload.get(
                    "baseline"
                )
            )
        ),
        constraints=_strings(
            payload.get(
                "constraints"
            ),
            field="constraints",
        ),
        invariants=_strings(
            payload.get(
                "invariants"
            ),
            field="invariants",
        ),
        cliches=_strings(
            payload.get(
                "cliches"
            ),
            field="cliches",
        ),
        context=_mapping(
            payload.get(
                "context"
            ),
            field="context",
        ),
        creative_policy=_mapping(
            payload.get(
                "creative_policy"
            ),
            field="creative_policy",
        ),
    )


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
        set(
            values
        )
        - allowed
    )

    if unknown:
        names = ", ".join(
            sorted(
                unknown
            )
        )

        raise praxis_error(
            "unknown creative policy "
            f"fields: {names}"
        )

    try:
        return creative_policy(
            **dict(
                values
            )
        )
    except (
        TypeError,
        ValueError,
    ) as exc:
        raise praxis_error(
            "invalid creative policy: "
            f"{exc}"
        ) from exc


def _previous_baselines(
    previous: Mapping[
        str,
        Any,
    ] | None,
) -> tuple[str, ...]:
    if previous is None:
        return ()

    values: list[str] = []

    digest = str(
        previous.get(
            "digest",
            "",
        )
    ).strip()

    if digest:
        values.append(
            "praxis-iteration:"
            + digest
        )

    workbench = previous.get(
        "workbench"
    )

    if isinstance(
        workbench,
        Mapping,
    ):
        workbench_digest = str(
            workbench.get(
                "digest",
                "",
            )
        ).strip()

        if workbench_digest:
            values.append(
                "workbench:"
                + workbench_digest
            )

    return tuple(
        values
    )


def _baseline_references(
    parameters:
        praxis_parameters,
) -> tuple[str, ...]:
    if (
        parameters.baseline
        is None
    ):
        return ()

    return (
        "baseline-image:"
        + parameters.baseline[
            "digest"
        ],
    )


def _iteration_context(
    *,
    parameters:
        praxis_parameters,
    index: int,
    previous: Mapping[
        str,
        Any,
    ] | None,
) -> dict[str, Any]:
    context = deepcopy(
        parameters.context
    )

    context.update({
        "surface":
            context.get(
                "surface",
                "splyce",
            ),
        "mode":
            "logo",
        "praxis":
            True,
        "praxis_iteration":
            index,
        "praxis_iterations":
            parameters.iterations,
        "praxis_interval_ms":
            parameters.interval_ms,
        "praxis_start":
            (
                "baseline"
                if (
                    parameters.baseline
                    is not None
                )
                else "scratch"
            ),
    })

    if (
        parameters.baseline
        is not None
    ):
        context[
            "baseline_image"
        ] = {
            key:
                deepcopy(
                    value
                )
            for key, value
            in parameters
            .baseline
            .items()
            if key != "source"
        }

    if previous is not None:
        context[
            "previous_iteration"
        ] = {
            "index":
                previous.get(
                    "index"
                ),
            "digest":
                previous.get(
                    "digest"
                ),
        }

    return context


def _iteration_objective(
    *,
    parameters:
        praxis_parameters,
    index: int,
) -> str:
    if index == 1:
        pressure = (
            "Establish a strong initial "
            "design direction."
        )
    else:
        pressure = (
            "Treat the preceding iteration "
            "as evidence, preserve what is "
            "working, reject weak or generic "
            "choices, and make a materially "
            "better design."
        )

    return (
        f"{parameters.objective}\n\n"
        f"Urge praxis iteration "
        f"{index} of "
        f"{parameters.iterations}. "
        f"{pressure} "
        "Do not merely restyle the prior "
        "result. Improve concept, "
        "distinctiveness, semantic density, "
        "legibility, reproduction, "
        "memorability, and system potential."
    )


def execute_step(
    payload: Mapping[
        str,
        Any,
    ],
) -> dict[str, Any]:
    if not isinstance(
        payload,
        Mapping,
    ):
        raise praxis_error(
            "payload must be a mapping"
        )

    parameters_payload = (
        payload.get(
            "parameters",
            payload,
        )
    )

    if not isinstance(
        parameters_payload,
        Mapping,
    ):
        raise praxis_error(
            "parameters must be a mapping"
        )

    parameters = (
        normalize_parameters(
            parameters_payload
        )
    )

    index = _bounded_int(
        payload.get(
            "index",
            1,
        ),
        field="index",
        minimum=1,
        maximum=(
            parameters.iterations
        ),
    )

    previous_raw = (
        payload.get(
            "previous"
        )
    )

    previous = (
        _mapping(
            previous_raw,
            field="previous",
        )
        if (
            previous_raw
            is not None
        )
        else None
    )

    policy = _policy(
        parameters.creative_policy
    )

    baselines = (
        _baseline_references(
            parameters
        )
        + _previous_baselines(
            previous
        )
    )

    objective = (
        _iteration_objective(
            parameters=parameters,
            index=index,
        )
    )

    context = (
        _iteration_context(
            parameters=parameters,
            index=index,
            previous=previous,
        )
    )

    brief = {
        "name":
            parameters.name,
        "context":
            context,
        "praxis": {
            "iteration":
                index,
            "iterations":
                parameters.iterations,
            "start":
                (
                    "baseline"
                    if (
                        parameters.baseline
                        is not None
                    )
                    else "scratch"
                ),
        },
    }

    logo = (
        project_logo_intelligence(
            name=parameters.name,
            brief=brief,
            objective=objective,
            constraints=(
                parameters.constraints
            ),
            protected_invariants=(
                parameters.invariants
            ),
            known_cliches=(
                parameters.cliches
            ),
            references_to_avoid=(
                baselines
            ),
            run_policy=policy,
        )
    )

    creative = logo[
        "creative_projection"
    ]

    renderer = project_renderer(
        candidate=logo,
        binding=(
            image_renderer_binding(
                baseline=(
                    parameters.baseline
                )
            )
        ),
        context={
            "urge_capability":
                CAPABILITY,
            "mode":
                "logo",
            "praxis":
                True,
            "iteration":
                index,
            "iterations":
                parameters.iterations,
            "objective":
                parameters.objective,
        },
    )

    workbench = (
        project_workbench(
            creative=creative,
            logo=logo,
            renderer=renderer,
        )
    )

    result = {
        "schema":
            STEP_SCHEMA,
        "owner":
            OWNER,
        "capability":
            CAPABILITY,
        "index":
            index,
        "iterations":
            parameters.iterations,
        "complete":
            (
                index
                == parameters.iterations
            ),
        "parameters":
            parameters
            .public_projection(),
        "creative":
            creative,
        "logo":
            logo,
        "renderer":
            renderer,
        "workbench":
            workbench,
        "lineage": {
            "previous_digest":
                (
                    previous.get(
                        "digest"
                    )
                    if (
                        previous
                        is not None
                    )
                    else None
                ),
            "baseline_digest":
                (
                    parameters
                    .baseline[
                        "digest"
                    ]
                    if (
                        parameters.baseline
                        is not None
                    )
                    else None
                ),
            "creative_digest":
                creative.get(
                    "digest"
                ),
            "logo_digest":
                logo.get(
                    "digest"
                ),
            "renderer_digest":
                renderer.get(
                    "digest"
                ),
            "workbench_digest":
                workbench.get(
                    "digest"
                ),
        },
        "ownership": {
            "iteration":
                OWNER,
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
            "owns_renderer":
                False,
            "projection_only":
                True,
        },
    }

    result[
        "digest"
    ] = _digest(
        result
    )

    return result


def project_praxis(
    payload: Mapping[
        str,
        Any,
    ],
) -> dict[str, Any]:
    parameters = (
        normalize_parameters(
            payload
        )
    )

    result = {
        "schema":
            SCHEMA,
        "owner":
            OWNER,
        "capability":
            CAPABILITY,
        "parameters":
            parameters
            .public_projection(),
        "execution": {
            "mode":
                "client-paced",
            "step_capability":
                CAPABILITY,
            "iterations":
                parameters.iterations,
            "interval_ms":
                parameters.interval_ms,
            "live_projection":
                True,
            "resume_supported":
                True,
            "renderer":
                "openai:gpt-image-2",
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
            "owns_renderer":
                False,
            "projection_only":
                True,
        },
    }

    result[
        "digest"
    ] = _digest(
        result
    )

    return result


def register(
    dispatcher: Any,
) -> str:
    if not hasattr(
        dispatcher,
        "register",
    ):
        raise praxis_error(
            "dispatcher does not expose register"
        )

    dispatcher.register(
        CAPABILITY,
        execute_step,
    )

    return CAPABILITY


__all__ = [
    "CAPABILITY",
    "MAX_INTERVAL_MS",
    "MAX_ITERATIONS",
    "MIN_INTERVAL_MS",
    "MIN_ITERATIONS",
    "OWNER",
    "SCHEMA",
    "STEP_SCHEMA",
    "execute_step",
    "normalize_parameters",
    "praxis_error",
    "praxis_parameters",
    "project_praxis",
    "register",
]
