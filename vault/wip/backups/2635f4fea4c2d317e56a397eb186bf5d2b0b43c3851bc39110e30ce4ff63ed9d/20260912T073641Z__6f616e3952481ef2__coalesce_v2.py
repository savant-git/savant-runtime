#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


RUNTIME_ROOT = Path(
    "/root/savant-runtime/ontology/obelisks/_template/segue/gates/"
    "_template/segue/innates/_template/segue/exiles/modus/segue/"
    "prodigals/coalesce/runtime"
).resolve()

if str(RUNTIME_ROOT) not in sys.path:
    sys.path.insert(
        0,
        str(RUNTIME_ROOT),
    )


from coalesce_composer import (
    CoalesceComposer,
    composer,
)
from mode_engine import (
    CoalesceModeEngine,
    CoalesceModeError,
    mode_engine,
)


OWNER = "prodigal:modus:coalesce"

SCHEMA = "savant://coalesce/runtime/2"


class CoalesceRuntime:
    def __init__(
        self,
        engine: CoalesceComposer | None = None,
        modes: CoalesceModeEngine | None = None,
    ) -> None:
        self.engine = (
            engine
            or composer()
        )

        self.modes = (
            modes
            or mode_engine()
        )

    def status(
        self,
    ) -> dict[str, Any]:
        return {
            "ok": True,
            "schema": SCHEMA,
            "owner": OWNER,
            "runtime": "coalesce-v2",
            "composer": (
                self.engine.status()
            ),
            "modes": (
                self.modes.status()
            ),
            "primary_modes": [
                "auto",
                "manual",
            ],
            "operations": [
                "status",
                "capabilities",
                "plan",
                "plan-recipe",
                "compose",
                "compose-recipe",
                "auto",
                "manual",
            ],
            "maximum_alloys": 3,
            "maximum_slivers_per_alloy": 9,
            "legacy_runtime_preserved": True,
            "reference_composition": True,
            "minimum_sufficient": True,
            "authoritative": False,
            "authority_effect": "none",
        }

    def dispatch(
        self,
        operation: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        action = str(
            operation
            or ""
        ).strip()

        if action == "status":
            return self.status()

        if action in {
            "auto",
            "manual",
        }:
            prompt = str(
                payload.get(
                    "prompt",
                    "",
                )
                or ""
            ).strip()

            try:
                return self.modes.build(
                    mode=action,
                    prompt=prompt,
                )
            except CoalesceModeError as exc:
                return {
                    "ok": False,
                    "owner": OWNER,
                    "mode": action,
                    "error": str(exc),
                }

        return self.engine.dispatch(
            action,
            payload,
        )


def runtime() -> CoalesceRuntime:
    return CoalesceRuntime()


def load_payload(
    value: str,
) -> dict[str, Any]:
    try:
        payload = json.loads(
            value
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

    return payload


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="coalesce-v2"
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
            "auto",
            "manual",
        ),
    )

    parser.add_argument(
        "--payload",
        default="{}",
    )

    parser.add_argument(
        "--prompt",
        default=None,
    )

    args = parser.parse_args()

    payload = load_payload(
        args.payload
    )

    if (
        args.prompt is not None
        and args.operation
        in {
            "auto",
            "manual",
        }
    ):
        payload[
            "prompt"
        ] = args.prompt

    result = (
        runtime()
        .dispatch(
            args.operation,
            payload,
        )
    )

    print(
        json.dumps(
            result,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
            default=str,
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
