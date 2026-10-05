#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
from typing import Any

from composition_adapter import (
    CompositionAdapter,
    CompositionAdapterError,
    adapter,
)


OWNER = "prodigal:modus:coalesce"

SERVICE_SCHEMA = (
    "savant://coalesce/"
    "application-service/1"
)


class ApplicationServiceError(
    RuntimeError
):
    pass


class ApplicationService:
    def __init__(
        self,
        composition: (
            CompositionAdapter
            | None
        ) = None,
    ) -> None:
        self.composition = (
            composition
            or adapter()
        )

    def dispatch(
        self,
        operation: str,
        payload: (
            dict[str, Any]
            | None
        ) = None,
    ) -> dict[str, Any]:
        data = (
            payload
            or {}
        )

        if not isinstance(
            data,
            dict,
        ):
            raise ApplicationServiceError(
                "payload must be an object"
            )

        action = str(
            operation
            or ""
        ).strip()

        try:
            if action == "status":
                return self.status()

            if action == "slivers":
                return (
                    self.composition
                    .list_slivers()
                )

            if action == "plan":
                return {
                    "ok": True,
                    "result": (
                        self.composition
                        .plan(
                            alloy_id=str(
                                data.get(
                                    "alloy_id",
                                    "",
                                )
                            ),
                            capabilities=(
                                data.get(
                                    "capabilities",
                                    (),
                                )
                            ),
                        )
                    ),
                }

            if action == "plan-recipe":
                return {
                    "ok": True,
                    "result": (
                        self.composition
                        .plan_recipe(
                            str(
                                data.get(
                                    "application_id",
                                    "",
                                )
                            )
                        )
                    ),
                }

            if action == "project":
                return {
                    "ok": True,
                    "result": (
                        self.composition
                        .assemble(
                            alloy_id=str(
                                data.get(
                                    "alloy_id",
                                    "",
                                )
                            ),
                            capabilities=(
                                data.get(
                                    "capabilities",
                                    (),
                                )
                            ),
                            configuration=(
                                data.get(
                                    "configuration"
                                )
                            ),
                            authorized_interfaces=(
                                data.get(
                                    "authorized_interfaces"
                                )
                            ),
                            segues=(
                                data.get(
                                    "segues"
                                )
                            ),
                        )
                    ),
                }

            if action == "project-recipe":
                return {
                    "ok": True,
                    "result": (
                        self.composition
                        .assemble_recipe(
                            str(
                                data.get(
                                    "application_id",
                                    "",
                                )
                            ),
                            configuration=(
                                data.get(
                                    "configuration"
                                )
                            ),
                            authorized_interfaces=(
                                data.get(
                                    "authorized_interfaces"
                                )
                            ),
                            segues=(
                                data.get(
                                    "segues"
                                )
                            ),
                        )
                    ),
                }

        except CompositionAdapterError as exc:
            raise ApplicationServiceError(
                str(exc)
            ) from exc

        raise ApplicationServiceError(
            f"unknown operation: {action}"
        )

    def safe_dispatch(
        self,
        operation: str,
        payload: (
            dict[str, Any]
            | None
        ) = None,
    ) -> dict[str, Any]:
        try:
            result = self.dispatch(
                operation,
                payload,
            )

            if (
                isinstance(
                    result,
                    dict,
                )
                and "ok"
                not in result
            ):
                return {
                    "ok": True,
                    "result": result,
                }

            return result

        except ApplicationServiceError as exc:
            return {
                "ok": False,
                "error": str(exc),
                "owner": OWNER,
            }

    def status(
        self,
    ) -> dict[str, Any]:
        return {
            "ok": True,
            "schema": SERVICE_SCHEMA,
            "owner": OWNER,
            "operations": [
                "status",
                "slivers",
                "plan",
                "plan-recipe",
                "project",
                "project-recipe",
            ],
            "composition": (
                self.composition
                .status()
            ),
            "minimum_sufficient": True,
            "alloy_sliver_range": [
                1,
                9,
            ],
            "reference_composition": (
                True
            ),
            "exile_embedding": False,
            "authoritative": False,
            "authority_effect": "none",
        }


def service() -> ApplicationService:
    return ApplicationService()


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="coalesce-application-service"
    )

    parser.add_argument(
        "operation",
        nargs="?",
        default="status",
    )

    parser.add_argument(
        "--payload",
        default="{}",
    )

    args = parser.parse_args()

    try:
        payload = json.loads(
            args.payload
        )
    except json.JSONDecodeError as exc:
        raise SystemExit(
            f"invalid JSON payload: {exc}"
        ) from exc

    result = (
        service()
        .safe_dispatch(
            args.operation,
            payload,
        )
    )

    print(
        json.dumps(
            result,
            indent=2,
            sort_keys=True,
        )
    )

    return (
        0
        if result.get(
            "ok"
        )
        else 1
    )


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
