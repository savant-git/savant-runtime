#!/usr/bin/env python3

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from typing import Any, Callable, Mapping, Sequence

from configuration import (
    configuration_current,
    configuration_error,
    recipe,
)


schema = (
    "savant://runtime/sieve/"
    "recipe-execution/1.0.0"
)

selftest_schema = (
    "savant://runtime/sieve/"
    "recipe-execution-selftest/1.0.0"
)

owner = "sieve"
authority_effect = "none"


class recipe_execution_error(
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
        default=str,
    )


def digest(
    value: Any,
) -> str:
    return hashlib.sha256(
        canonical_json(
            value
        ).encode(
            "utf-8"
        )
    ).hexdigest()


@dataclass(
    frozen=True,
    slots=True,
)
class execution_step:
    column: str
    option: str
    parameters: Mapping[
        str,
        Any,
    ]
    ordinal: int

    def projection(
        self,
    ) -> dict[str, Any]:
        return {
            "column":
                self.column,
            "option":
                self.option,
            "parameters":
                dict(
                    self.parameters
                ),
            "ordinal":
                self.ordinal,
        }


@dataclass(
    frozen=True,
    slots=True,
)
class execution_plan:
    definition_digest: str
    recipe_digest: str
    steps: tuple[
        execution_step,
        ...
    ]
    lineage: Mapping[
        str,
        Any,
    ]
    provenance: Mapping[
        str,
        Any,
    ]
    authoritative: bool = False
    rebuildable: bool = True

    def substance(
        self,
    ) -> dict[str, Any]:
        return {
            "schema":
                schema,
            "owner":
                owner,
            "authority_effect":
                authority_effect,
            "authoritative":
                self.authoritative,
            "rebuildable":
                self.rebuildable,
            "definition_digest":
                self.definition_digest,
            "recipe_digest":
                self.recipe_digest,
            "steps": [
                step.projection()
                for step in self.steps
            ],
            "lineage":
                dict(
                    self.lineage
                ),
            "provenance":
                dict(
                    self.provenance
                ),
        }

    @property
    def plan_digest(
        self,
    ) -> str:
        return digest(
            self.substance()
        )

    def projection(
        self,
    ) -> dict[str, Any]:
        value = self.substance()

        value[
            "plan_digest"
        ] = self.plan_digest

        return value


@dataclass(
    frozen=True,
    slots=True,
)
class execution_receipt:
    plan_digest: str
    recipe_digest: str
    definition_digest: str
    result_digests: tuple[
        str,
        ...
    ]
    lineage: Mapping[
        str,
        Any,
    ]
    authoritative: bool = False
    rebuildable: bool = True

    def substance(
        self,
    ) -> dict[str, Any]:
        return {
            "schema":
                "savant://runtime/sieve/"
                "recipe-execution-receipt/"
                "1.0.0",
            "owner":
                owner,
            "authority_effect":
                authority_effect,
            "authoritative":
                self.authoritative,
            "rebuildable":
                self.rebuildable,
            "plan_digest":
                self.plan_digest,
            "recipe_digest":
                self.recipe_digest,
            "definition_digest":
                self.definition_digest,
            "result_digests":
                list(
                    self.result_digests
                ),
            "lineage":
                dict(
                    self.lineage
                ),
        }

    @property
    def receipt_digest(
        self,
    ) -> str:
        return digest(
            self.substance()
        )

    def projection(
        self,
    ) -> dict[str, Any]:
        value = self.substance()

        value[
            "receipt_digest"
        ] = self.receipt_digest

        return value


handler = Callable[
    [
        execution_step,
        Any,
    ],
    Any,
]


def build_plan(
    definition:
        configuration_current,
    selected_recipe:
        recipe,
) -> execution_plan:
    if (
        selected_recipe.definition_digest
        != definition.definition_digest
    ):
        raise recipe_execution_error(
            "recipe definition digest "
            "does not match configuration"
        )

    if selected_recipe.authoritative:
        raise recipe_execution_error(
            "authoritative recipes cannot "
            "be executed as projections"
        )

    if not selected_recipe.rebuildable:
        raise recipe_execution_error(
            "recipe must be rebuildable"
        )

    try:
        normalized = (
            definition.validate(
                selected_recipe.selections,
                complete=True,
            )
        )
    except configuration_error as exc:
        raise recipe_execution_error(
            f"invalid recipe: {exc}"
        ) from exc

    steps: list[
        execution_step
    ] = []

    ordinal = 0

    for selected in normalized:
        for option_id in selected.options:
            steps.append(
                execution_step(
                    column=
                        selected.column,
                    option=
                        option_id,
                    parameters=dict(
                        selected.parameters.get(
                            option_id,
                            {},
                        )
                    ),
                    ordinal=
                        ordinal,
                )
            )

            ordinal += 1

    return execution_plan(
        definition_digest=
            definition.definition_digest,
        recipe_digest=
            selected_recipe.recipe_digest,
        steps=tuple(
            steps
        ),
        lineage={
            "recipe_digest":
                selected_recipe.recipe_digest,
            "definition_digest":
                definition.definition_digest,
            "recipe_lineage":
                dict(
                    selected_recipe.lineage
                ),
        },
        provenance={
            "recipe_provenance":
                dict(
                    selected_recipe.provenance
                ),
            "configuration_owner":
                definition.owner,
        },
    )


def execute_plan(
    plan: execution_plan,
    handlers: Mapping[
        tuple[str, str],
        handler,
    ],
    *,
    initial: Any = None,
) -> tuple[
    Any,
    execution_receipt,
]:
    state = initial

    result_digests: list[
        str
    ] = []

    for step in plan.steps:
        key = (
            step.column,
            step.option,
        )

        selected_handler = (
            handlers.get(
                key
            )
        )

        if selected_handler is None:
            raise recipe_execution_error(
                "no execution handler for "
                f"{step.column}."
                f"{step.option}"
            )

        state = selected_handler(
            step,
            state,
        )

        result_digests.append(
            digest(
                state
            )
        )

    receipt = execution_receipt(
        plan_digest=
            plan.plan_digest,
        recipe_digest=
            plan.recipe_digest,
        definition_digest=
            plan.definition_digest,
        result_digests=tuple(
            result_digests
        ),
        lineage={
            "plan_digest":
                plan.plan_digest,
            "step_count":
                len(
                    plan.steps
                ),
        },
    )

    return (
        state,
        receipt,
    )


def execute_recipe(
    definition:
        configuration_current,
    selected_recipe:
        recipe,
    handlers: Mapping[
        tuple[str, str],
        handler,
    ],
    *,
    initial: Any = None,
) -> tuple[
    Any,
    execution_plan,
    execution_receipt,
]:
    plan = build_plan(
        definition,
        selected_recipe,
    )

    (
        result,
        receipt,
    ) = execute_plan(
        plan,
        handlers,
        initial=initial,
    )

    return (
        result,
        plan,
        receipt,
    )


def selftest(
) -> dict[str, Any]:
    definition = (
        configuration_current.from_mapping(
            {
                "columns": [
                    {
                        "id":
                            "action",
                        "options": [
                            "audit",
                        ],
                    },
                    {
                        "id":
                            "depth",
                        "options": [
                            {
                                "id":
                                    "focused",
                                "parameters": [
                                    {
                                        "id":
                                            "limit",
                                        "type":
                                            "integer",
                                        "required":
                                            True,
                                    }
                                ],
                            },
                        ],
                    },
                    {
                        "id":
                            "output",
                        "options": [
                            "json",
                        ],
                    },
                ],
                "lineage": {
                    "source":
                        "recipe-execution-selftest"
                },
                "provenance": {
                    "source":
                        "recipe-execution-selftest"
                },
            }
        )
    )

    selected_recipe = (
        definition.build_recipe(
            (
                __selection(
                    "action",
                    "audit",
                ),
                __selection(
                    "depth",
                    "focused",
                    {
                        "limit": 3
                    },
                ),
                __selection(
                    "output",
                    "json",
                ),
            ),
            lineage={
                "source":
                    "recipe-execution-selftest"
            },
            provenance={
                "source":
                    "recipe-execution-selftest"
            },
        )
    )

    def audit_handler(
        step: execution_step,
        state: Any,
    ) -> dict[str, Any]:
        return {
            "action":
                step.option,
            "previous":
                state,
        }

    def focused_handler(
        step: execution_step,
        state: Any,
    ) -> dict[str, Any]:
        return {
            "action":
                state[
                    "action"
                ],
            "limit":
                step.parameters[
                    "limit"
                ],
        }

    def json_handler(
        step: execution_step,
        state: Any,
    ) -> dict[str, Any]:
        return {
            "action":
                state[
                    "action"
                ],
            "limit":
                state[
                    "limit"
                ],
            "output":
                step.option,
        }

    handlers = {
        (
            "action",
            "audit",
        ):
            audit_handler,
        (
            "depth",
            "focused",
        ):
            focused_handler,
        (
            "output",
            "json",
        ):
            json_handler,
    }

    (
        first_result,
        first_plan,
        first_receipt,
    ) = execute_recipe(
        definition,
        selected_recipe,
        handlers,
    )

    (
        second_result,
        second_plan,
        second_receipt,
    ) = execute_recipe(
        definition,
        selected_recipe,
        handlers,
    )

    missing_handler_rejected = (
        False
    )

    try:
        execute_recipe(
            definition,
            selected_recipe,
            {},
        )
    except recipe_execution_error:
        missing_handler_rejected = (
            True
        )

    wrong_definition = (
        configuration_current.from_mapping(
            {
                "columns": [
                    {
                        "id":
                            "different",
                        "options": [
                            "value",
                        ],
                    }
                ]
            }
        )
    )

    digest_mismatch_rejected = (
        False
    )

    try:
        build_plan(
            wrong_definition,
            selected_recipe,
        )
    except recipe_execution_error:
        digest_mismatch_rejected = (
            True
        )

    checks = {
        "three_steps":
            len(
                first_plan.steps
            )
            == 3,
        "ordered_steps":
            [
                (
                    step.column,
                    step.option,
                )
                for step
                in first_plan.steps
            ]
            == [
                (
                    "action",
                    "audit",
                ),
                (
                    "depth",
                    "focused",
                ),
                (
                    "output",
                    "json",
                ),
            ],
        "parameter_carried":
            first_plan.steps[
                1
            ].parameters[
                "limit"
            ]
            == 3,
        "result_correct":
            first_result
            == {
                "action":
                    "audit",
                "limit":
                    3,
                "output":
                    "json",
            },
        "plan_deterministic":
            first_plan.plan_digest
            == second_plan.plan_digest,
        "result_deterministic":
            first_result
            == second_result,
        "receipt_deterministic":
            first_receipt.receipt_digest
            == second_receipt.receipt_digest,
        "receipt_chained":
            first_receipt.plan_digest
            == first_plan.plan_digest,
        "definition_chained":
            first_plan.definition_digest
            == definition.definition_digest,
        "recipe_chained":
            first_plan.recipe_digest
            == selected_recipe.recipe_digest,
        "authority_none":
            first_plan.substance()[
                "authority_effect"
            ]
            == "none",
        "plan_non_authoritative":
            first_plan.authoritative
            is False,
        "plan_rebuildable":
            first_plan.rebuildable
            is True,
        "receipt_non_authoritative":
            first_receipt.authoritative
            is False,
        "receipt_rebuildable":
            first_receipt.rebuildable
            is True,
        "missing_handler_rejected":
            missing_handler_rejected,
        "digest_mismatch_rejected":
            digest_mismatch_rejected,
    }

    return {
        "schema":
            selftest_schema,
        "ok":
            all(
                checks.values()
            ),
        "checks":
            checks,
        "definition_digest":
            definition.definition_digest,
        "recipe_digest":
            selected_recipe.recipe_digest,
        "plan_digest":
            first_plan.plan_digest,
        "receipt_digest":
            first_receipt.receipt_digest,
    }


def __selection(
    column_id: str,
    option_id: str,
    parameters: Mapping[
        str,
        Any,
    ] | None = None,
):
    from configuration import selection

    return selection(
        column=column_id,
        options=(
            option_id,
        ),
        parameters=(
            {
                option_id:
                    dict(
                        parameters
                    )
            }
            if parameters
            is not None
            else {}
        ),
    )


def main() -> int:
    result = selftest()

    print(
        json.dumps(
            result,
            ensure_ascii=False,
            sort_keys=True,
            indent=2,
        )
    )

    return (
        0
        if result[
            "ok"
        ]
        else 1
    )


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
