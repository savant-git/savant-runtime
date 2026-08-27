#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
from typing import Any

from application_service import (
    ApplicationService,
    service,
)


OWNER = "prodigal:modus:coalesce"

SCHEMA = (
    "savant://coalesce/"
    "composer/1"
)


class CoalesceComposer:
    def __init__(
        self,
        application_service: (
            ApplicationService
            | None
        ) = None,
    ) -> None:
        self.service = (
            application_service
            or service()
        )

    def status(
        self,
    ) -> dict[str, Any]:
        service_status = (
            self.service.status()
        )

        return {
            "ok": True,
            "schema": SCHEMA,
            "owner": OWNER,
            "role": (
                "application-composition-"
                "intelligence"
            ),
            "source_language": (
                "capability-intent"
            ),
            "intermediate_representation": (
                "alloy-plan"
            ),
            "target": "alloy",
            "pipeline": [
                "capability-resolution",
                "sliver-selection",
                "minimum-sufficient-set",
                "configuration-binding",
                "interface-binding",
                "segue-binding",
                "composition-graph",
                "alloy-projection",
            ],
            "sliver_range": [
                1,
                9,
            ],
            "fixed_sliver_pool_size": (
                False
            ),
            "reference_composition": (
                True
            ),
            "canonical_substance_copied": (
                False
            ),
            "exile_embedding": False,
            "external_access": (
                "authorized-interface-only"
            ),
            "authoritative": False,
            "authority_effect": "none",
            "service": service_status,
        }

    def capabilities(
        self,
    ) -> dict[str, Any]:
        return (
            self.service.safe_dispatch(
                "slivers"
            )
        )

    def plan(
        self,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        return (
            self.service.safe_dispatch(
                "plan",
                payload,
            )
        )

    def plan_recipe(
        self,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        return (
            self.service.safe_dispatch(
                "plan-recipe",
                payload,
            )
        )

    def compose(
        self,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        return (
            self.service.safe_dispatch(
                "project",
                payload,
            )
        )

    def compose_recipe(
        self,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        return (
            self.service.safe_dispatch(
                "project-recipe",
                payload,
            )
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

        if operation == "status":
            return self.status()

        if operation == "capabilities":
            return self.capabilities()

        if operation == "plan":
            return self.plan(
                data
            )

        if operation == "plan-recipe":
            return self.plan_recipe(
                data
            )

        if operation == "compose":
            return self.compose(
                data
            )

        if operation == "compose-recipe":
            return self.compose_recipe(
                data
            )

        return {
            "ok": False,
            "error": (
                "unknown Coalesce "
                f"operation: {operation}"
            ),
            "owner": OWNER,
        }


def composer() -> CoalesceComposer:
    return CoalesceComposer()


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="coalesce-composer"
    )

    parser.add_argument(
        "operation",
        nargs="?",
        default="status",
        choices=(
            "status",
            "capabilities",
            "plan",
            "plan-recipe",
            "compose",
            "compose-recipe",
        ),
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

    if not isinstance(
        payload,
        dict,
    ):
        raise SystemExit(
            "payload must be a JSON object"
        )

    result = (
        composer()
        .dispatch(
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
            "ok",
            True,
        )
        else 1
    )


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
