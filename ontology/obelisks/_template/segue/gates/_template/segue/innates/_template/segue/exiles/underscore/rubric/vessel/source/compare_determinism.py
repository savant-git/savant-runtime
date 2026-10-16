#!/usr/bin/env python3

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from typing import Any


production_stable_path = Path(
    "/root/savant-runtime/"
    "ontology/obelisks/_template/segue/gates/_template/"
    "segue/innates/_template/segue/exiles/underscore/"
    "rubric/vessel/source/production_stable.py"
)


def load_module() -> Any:
    if not production_stable_path.is_file():
        raise RuntimeError(
            "production stable module unavailable: "
            + str(
                production_stable_path
            )
        )

    spec = importlib.util.spec_from_file_location(
        "savant_underscore_production_stable_compare",
        production_stable_path,
    )

    if (
        spec is None
        or spec.loader is None
    ):
        raise RuntimeError(
            "unable to load production stable module"
        )

    module = importlib.util.module_from_spec(
        spec
    )

    sys.modules[
        spec.name
    ] = module

    spec.loader.exec_module(
        module
    )

    return module


def preview(
    value: Any,
    limit: int = 300,
) -> str:
    rendered = repr(
        value
    )

    if len(
        rendered
    ) <= limit:
        return rendered

    return (
        rendered[
            :limit
        ]
        + "..."
    )


def compare(
    left: Any,
    right: Any,
    *,
    path: str = "$",
    differences: list[
        dict[str, Any]
    ],
) -> None:
    if type(
        left
    ) is not type(
        right
    ):
        differences.append(
            {
                "path": path,
                "reason": "type",
                "left_type": (
                    type(
                        left
                    ).__name__
                ),
                "right_type": (
                    type(
                        right
                    ).__name__
                ),
                "left": preview(
                    left
                ),
                "right": preview(
                    right
                ),
            }
        )

        return

    if isinstance(
        left,
        dict,
    ):
        keys = sorted(
            set(
                left
            )
            | set(
                right
            )
        )

        for key in keys:
            child_path = (
                f"{path}.{key}"
            )

            if key not in left:
                differences.append(
                    {
                        "path": (
                            child_path
                        ),
                        "reason": (
                            "missing-left"
                        ),
                        "left": (
                            "<missing>"
                        ),
                        "right": (
                            preview(
                                right[
                                    key
                                ]
                            )
                        ),
                    }
                )

                continue

            if key not in right:
                differences.append(
                    {
                        "path": (
                            child_path
                        ),
                        "reason": (
                            "missing-right"
                        ),
                        "left": (
                            preview(
                                left[
                                    key
                                ]
                            )
                        ),
                        "right": (
                            "<missing>"
                        ),
                    }
                )

                continue

            compare(
                left[
                    key
                ],
                right[
                    key
                ],
                path=child_path,
                differences=(
                    differences
                ),
            )

        return

    if isinstance(
        left,
        list,
    ):
        if len(
            left
        ) != len(
            right
        ):
            differences.append(
                {
                    "path": path,
                    "reason": "length",
                    "left_length": len(
                        left
                    ),
                    "right_length": len(
                        right
                    ),
                }
            )

        for index, (
            left_value,
            right_value,
        ) in enumerate(
            zip(
                left,
                right,
            )
        ):
            compare(
                left_value,
                right_value,
                path=(
                    f"{path}[{index}]"
                ),
                differences=(
                    differences
                ),
            )

        return

    if isinstance(
        left,
        tuple,
    ):
        if len(
            left
        ) != len(
            right
        ):
            differences.append(
                {
                    "path": path,
                    "reason": "length",
                    "left_length": len(
                        left
                    ),
                    "right_length": len(
                        right
                    ),
                }
            )

        for index, (
            left_value,
            right_value,
        ) in enumerate(
            zip(
                left,
                right,
            )
        ):
            compare(
                left_value,
                right_value,
                path=(
                    f"{path}[{index}]"
                ),
                differences=(
                    differences
                ),
            )

        return

    if left != right:
        differences.append(
            {
                "path": path,
                "reason": "value",
                "left": preview(
                    left
                ),
                "right": preview(
                    right
                ),
            }
        )


def main() -> int:
    module = load_module()

    pipeline = (
        module.fixture_pipeline(
            recurse_unresolved=False
        )
    )

    payload = (
        module.production
        .fixture_payload()
    )

    first_raw = (
        pipeline.pipeline.execute(
            payload
        )
    )

    second_raw = (
        pipeline.pipeline.execute(
            payload
        )
    )

    first = (
        module
        .deterministic_projection(
            first_raw
        )
    )

    second = (
        module
        .deterministic_projection(
            second_raw
        )
    )

    differences: list[
        dict[str, Any]
    ] = []

    compare(
        first,
        second,
        differences=differences,
    )

    result = {
        "schema": (
            "savant.underscore.vessel."
            "determinism-comparison.v1"
        ),
        "authority_effect": "none",
        "first_projection_digest": (
            module.digest(
                first
            )
        ),
        "second_projection_digest": (
            module.digest(
                second
            )
        ),
        "equal": (
            first
            == second
        ),
        "difference_count": len(
            differences
        ),
        "differences": (
            differences[
                :100
            ]
        ),
        "truncated": (
            len(
                differences
            )
            > 100
        ),
    }

    print(
        json.dumps(
            result,
            ensure_ascii=False,
            indent=2,
        )
    )

    return (
        0
        if differences
        else 0
    )


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
