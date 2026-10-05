#!/usr/bin/env python3

from __future__ import annotations

import inspect
import json

from runtime.pryme import Pryme


TARGET_NAMES = (
    "discover",
    "records",
    "compare",
    "resolve",
    "precedence",
    "precedence_map",
    "health",
    "validate",
    "status",
    "project",
)


def main() -> int:
    pryme = Pryme()

    rows = []

    for name in TARGET_NAMES:
        candidate = getattr(
            pryme,
            name,
            None,
        )

        if not callable(
            candidate
        ):
            continue

        try:
            signature = str(
                inspect.signature(
                    candidate
                )
            )
        except Exception:
            signature = "unknown"

        try:
            source = inspect.getsource(
                getattr(
                    type(pryme),
                    name,
                )
            )
        except Exception:
            source = ""

        rows.append(
            {
                "name": name,
                "signature": signature,
                "source": source,
            }
        )

    print(
        json.dumps(
            {
                "schema": getattr(
                    pryme,
                    "schema",
                    None,
                ),
                "instance_id": (
                    pryme.instance.get(
                        "instance_id"
                    )
                    if isinstance(
                        pryme.instance,
                        dict,
                    )
                    else None
                ),
                "precedence_source": str(
                    getattr(
                        pryme,
                        "precedence_source",
                        "",
                    )
                ),
                "precedence": list(
                    getattr(
                        pryme,
                        "precedence",
                        (),
                    )
                ),
                "methods": rows,
            },
            indent=2,
            sort_keys=True,
        )
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
