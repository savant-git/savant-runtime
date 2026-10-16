from __future__ import annotations

import json
import sys

from cognitive_benchmark_evaluator import (
    evaluate_suite,
)
from cognitive_benchmark_runner import (
    run_suite,
)
from router import execute_text_request


def main() -> int:
    raw = run_suite(
        execute_text_request
    )

    evaluation = evaluate_suite(
        raw
    )

    result = {
        "raw": raw,
        "evaluation": evaluation,
    }

    print(
        json.dumps(
            result,
            sort_keys=True,
            indent=2,
            ensure_ascii=False,
        )
    )

    basic_failures = [
        item
        for item in raw[
            "results"
        ]
        if not item[
            "basic"
        ][
            "ok"
        ]
    ]

    opus_failures = [
        item
        for item in raw[
            "results"
        ]
        if not item[
            "opus"
        ][
            "ok"
        ]
    ]

    if basic_failures:
        return 2

    if opus_failures:
        return 3

    return 0


if __name__ == "__main__":
    sys.exit(
        main()
    )
