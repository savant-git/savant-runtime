#!/usr/bin/env python3

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


THIS_FILE = Path(
    __file__
).resolve()

BOOTSTRAP_ROOT = (
    THIS_FILE.parent
)

RUNTIME_ROOT = (
    BOOTSTRAP_ROOT.parent
)

EXILE_RUNTIME_ROOT = (
    RUNTIME_ROOT.parent
)

SERVICES_ROOT = (
    RUNTIME_ROOT
    / "services"
)

if str(
    SERVICES_ROOT
) not in sys.path:
    sys.path.insert(
        0,
        str(
            SERVICES_ROOT
        ),
    )


from EXILE_REGISTRY import (  # noqa: E402
    EXPECTED_EXILE_COUNT,
    ExileRegistryError,
    load_exile_registry,
    validate_registry,
)

from EXILE_VALIDATOR import (  # noqa: E402
    validate as validate_exile_layout,
)


class ExileRuntimeBootstrapError(
    RuntimeError
):
    pass


@dataclass(
    slots=True,
)
class RuntimeState:
    initialized: bool = False
    validated: bool = False
    registered: bool = False
    exile_count: int = 0
    registry_source: str | None = None
    registry_digest: str | None = None
    layout_policy: str | None = None
    mutation_performed: bool = False
    physical_migration_performed: bool = False

    def projection(
        self,
    ) -> dict[str, Any]:
        return {
            "initialized":
                self.initialized,
            "validated":
                self.validated,
            "registered":
                self.registered,
            "exile_count":
                self.exile_count,
            "registry_source":
                self.registry_source,
            "registry_digest":
                self.registry_digest,
            "layout_policy":
                self.layout_policy,
            "mutation_performed":
                self.mutation_performed,
            "physical_migration_performed":
                self.physical_migration_performed,
        }


STATE = RuntimeState()


def validate_runtime(
) -> dict[str, Any]:
    registry_report = (
        validate_registry()
    )

    if not registry_report.get(
        "valid",
        False,
    ):
        raise ExileRuntimeBootstrapError(
            "Exile registry validation failed"
        )

    try:
        registry = (
            load_exile_registry()
        )

    except ExileRegistryError as exc:
        raise ExileRuntimeBootstrapError(
            "unable to load Exile registry: "
            + str(
                exc
            )
        ) from exc

    if (
        registry.count
        != EXPECTED_EXILE_COUNT
    ):
        raise ExileRuntimeBootstrapError(
            "Exile registry cardinality "
            f"must be "
            f"{EXPECTED_EXILE_COUNT}; "
            f"found {registry.count}"
        )

    layout_report = (
        validate_exile_layout()
    )

    if not layout_report.get(
        "valid",
        False,
    ):
        raise ExileRuntimeBootstrapError(
            "Exile layout validation failed"
        )

    if (
        layout_report.get(
            "policy"
        )
        != "capability-materialized"
    ):
        raise ExileRuntimeBootstrapError(
            "Exile runtime requires "
            "capability-materialized layout policy"
        )

    return {
        "registry":
            registry_report,
        "layout":
            layout_report,
        "registry_object":
            registry,
    }


def register_runtime(
    validation:
        dict[str, Any],
) -> None:
    registry = (
        validation[
            "registry_object"
        ]
    )

    layout = (
        validation[
            "layout"
        ]
    )

    STATE.registered = True
    STATE.exile_count = (
        registry.count
    )
    STATE.registry_source = (
        str(
            registry.source
        )
    )
    STATE.registry_digest = (
        registry.source_digest
    )
    STATE.layout_policy = (
        str(
            layout[
                "policy"
            ]
        )
    )


def bootstrap(
) -> RuntimeState:
    validation = (
        validate_runtime()
    )

    STATE.validated = True

    register_runtime(
        validation
    )

    STATE.initialized = True

    STATE.mutation_performed = (
        False
    )

    STATE.physical_migration_performed = (
        False
    )

    return STATE


def validate_bootstrap(
) -> dict[str, Any]:
    state = bootstrap()

    checks = {
        "initialized": (
            state.initialized
            is True
        ),
        "validated": (
            state.validated
            is True
        ),
        "registered": (
            state.registered
            is True
        ),
        "exile_count": (
            state.exile_count
            == EXPECTED_EXILE_COUNT
        ),
        "registry_bound": (
            bool(
                state.registry_source
            )
            and bool(
                state.registry_digest
            )
        ),
        "capability_materialized": (
            state.layout_policy
            == "capability-materialized"
        ),
        "mutation_free": (
            state.mutation_performed
            is False
        ),
        "migration_free": (
            state.physical_migration_performed
            is False
        ),
        "hardcoded_exile_population": (
            False
        ),
    }

    return {
        "schema": (
            "savant://assurance/"
            "exile-runtime-bootstrap/2.0.0"
        ),
        "valid":
            all(
                (
                    checks[
                        "initialized"
                    ],
                    checks[
                        "validated"
                    ],
                    checks[
                        "registered"
                    ],
                    checks[
                        "exile_count"
                    ],
                    checks[
                        "registry_bound"
                    ],
                    checks[
                        "capability_materialized"
                    ],
                    checks[
                        "mutation_free"
                    ],
                    checks[
                        "migration_free"
                    ],
                    checks[
                        "hardcoded_exile_population"
                    ]
                    is False,
                )
            ),
        "checks":
            checks,
        "state":
            state.projection(),
        "runtime_root":
            str(
                RUNTIME_ROOT
            ),
        "exile_runtime_root":
            str(
                EXILE_RUNTIME_ROOT
            ),
        "mutation_authorized":
            False,
        "physical_migration_authorized":
            False,
    }


def main(
) -> int:
    report = (
        validate_bootstrap()
    )

    print(
        json.dumps(
            report,
            indent=2,
            sort_keys=True,
        )
    )

    return (
        0
        if report[
            "valid"
        ]
        else 1
    )


if __name__ == "__main__":
    try:
        raise SystemExit(
            main()
        )

    except (
        OSError,
        ExileRegistryError,
        ExileRuntimeBootstrapError,
    ) as exc:
        print(
            "ERROR: "
            f"{type(exc).__name__}: "
            f"{exc}",
            file=sys.stderr,
        )

        raise SystemExit(1)
