#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


ROOT = Path("/root/savant-runtime")

REPORT_PATH = (
    ROOT
    / "reports"
    / "niche"
    / "masterplan"
    / "decision-acceptance"
    / "latest.json"
)


def load_json(
    path: Path,
) -> dict[str, Any]:
    value = json.loads(
        path.read_text(
            encoding="utf-8",
        )
    )

    if not isinstance(
        value,
        dict,
    ):
        raise ValueError(
            f"Expected JSON object: {path}"
        )

    return value


def resolve_decision_id(
    value: dict[str, Any],
) -> str:
    identifier = value.get(
        "id"
    )

    if isinstance(
        identifier,
        str,
    ) and identifier:
        return identifier

    identifier = value.get(
        "decision_id"
    )

    if isinstance(
        identifier,
        str,
    ) and identifier:
        return identifier

    decision = value.get(
        "decision"
    )

    if isinstance(
        decision,
        dict,
    ):
        identifier = decision.get(
            "id"
        )

        if isinstance(
            identifier,
            str,
        ) and identifier:
            return identifier

    raise ValueError(
        "Accepted decision report contains no decision identifier."
    )


def main() -> int:
    if not REPORT_PATH.is_file():
        raise SystemExit(
            f"ERROR: accepted decision report does not exist: {REPORT_PATH}"
        )

    try:
        report = load_json(
            REPORT_PATH
        )

        identifier = resolve_decision_id(
            report
        )

    except Exception as exc:
        raise SystemExit(
            f"ERROR: {exc}"
        ) from exc

    print(
        identifier
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
