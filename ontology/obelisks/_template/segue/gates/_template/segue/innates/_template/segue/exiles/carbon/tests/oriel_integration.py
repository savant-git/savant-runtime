#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import sys

from pathlib import Path
from typing import Any, Mapping


carbon_root = Path(
    "/root/savant-runtime/"
    "ontology/obelisks/_template/"
    "segue/gates/_template/segue/"
    "innates/_template/segue/"
    "exiles/carbon"
)

runtime_root = (
    carbon_root
    / "runtime"
)

if str(runtime_root) not in sys.path:
    sys.path.insert(
        0,
        str(runtime_root),
    )


from oriel_boundary import (  # noqa: E402
    selftest as boundary_selftest,
)

from oriel_canon import (  # noqa: E402
    selftest as canon_selftest,
)

from oriel_capabilities import (  # noqa: E402
    collect as collect_capabilities,
)

from oriel_observatory import (  # noqa: E402
    status as observatory_status,
)

from oriel_simulation import (  # noqa: E402
    selftest as simulation_selftest,
)


schema = "savant.carbon.oriel-integration-test.v1"
owner = "carbon"
component = "oriel-integration-test"
authority_effect = "none"


class oriel_integration_error(
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


def load_json(
    path: Path,
) -> dict[str, Any]:
    try:
        value = json.loads(
            path.read_text(
                encoding="utf-8"
            )
        )

    except OSError as exc:
        raise oriel_integration_error(
            (
                "cannot read "
                + str(path)
                + ": "
                + str(exc)
            )
        ) from exc

    except json.JSONDecodeError as exc:
        raise oriel_integration_error(
            (
                "invalid json in "
                + str(path)
                + ": "
                + str(exc)
            )
        ) from exc

    if not isinstance(
        value,
        dict,
    ):
        raise oriel_integration_error(
            (
                "expected json object: "
                + str(path)
            )
        )

    return value


def require_true(
    value: Mapping[str, Any],
    field: str,
    label: str,
) -> None:
    if value.get(
        field
    ) is not True:
        raise oriel_integration_error(
            (
                label
                + " did not prove "
                + field
            )
        )


def validate_declared_json(
    policy: Mapping[str, Any],
) -> list[dict[str, Any]]:
    rows = []

    for relative_path in policy.get(
        "required_json",
        [],
    ):
        relative = str(
            relative_path
        ).strip()

        if not relative:
            continue

        path = (
            carbon_root
            / relative
        )

        value = load_json(
            path
        )

        rows.append(
            {
                "path":
                    relative,

                "id":
                    value.get(
                        "id"
                    ),

                "valid":
                    True,
            }
        )

    return rows


def run() -> dict[str, Any]:
    policy = load_json(
        carbon_root
        / "validation/oriel.json"
    )

    if policy.get(
        "id"
    ) != "carbon.validation.oriel":
        raise oriel_integration_error(
            "unexpected validation policy"
        )

    json_checks = validate_declared_json(
        policy
    )

    simulation = simulation_selftest()

    if not isinstance(
        simulation,
        Mapping,
    ):
        raise oriel_integration_error(
            (
                "oriel simulation selftest "
                "did not return an object"
            )
        )

    require_true(
        simulation,
        "ok",
        "oriel simulation selftest",
    )

    boundary = boundary_selftest()

    if not isinstance(
        boundary,
        Mapping,
    ):
        raise oriel_integration_error(
            (
                "oriel boundary selftest "
                "did not return an object"
            )
        )

    require_true(
        boundary,
        "ok",
        "oriel boundary selftest",
    )

    canon = canon_selftest()

    if not isinstance(
        canon,
        Mapping,
    ):
        raise oriel_integration_error(
            (
                "oriel canon selftest "
                "did not return an object"
            )
        )

    require_true(
        canon,
        "ok",
        "oriel canon selftest",
    )

    observatory = observatory_status()

    if not isinstance(
        observatory,
        Mapping,
    ):
        raise oriel_integration_error(
            (
                "oriel observatory status "
                "did not return an object"
            )
        )

    if observatory.get(
        "ready"
    ) is not True:
        raise oriel_integration_error(
            (
                "oriel observatory "
                "is not ready"
            )
        )

    observed_state = str(
        observatory.get(
            "observed_state",
            "",
        )
    ).strip().lower()

    allowed_states = {
        str(value).strip().lower()
        for value
        in policy.get(
            "closure_check",
            {},
        ).get(
            "allowed_states",
            [],
        )
    }

    if (
        observed_state
        not in allowed_states
    ):
        raise oriel_integration_error(
            (
                "oriel observatory state "
                "is not closure-compatible: "
                + observed_state
            )
        )

    capabilities = collect_capabilities()

    if not isinstance(
        capabilities,
        Mapping,
    ):
        raise oriel_integration_error(
            (
                "oriel capability collection "
                "did not return an object"
            )
        )

    unavailable = list(
        capabilities.get(
            "unavailable_modules",
            [],
        )
    )

    unmanifested = list(
        capabilities.get(
            "unmanifested_modules",
            [],
        )
    )

    provider_errors = list(
        capabilities.get(
            "provider_errors",
            [],
        )
    )

    if unavailable:
        raise oriel_integration_error(
            (
                "unavailable oriel providers: "
                + ", ".join(
                    str(value)
                    for value
                    in unavailable
                )
            )
        )

    if unmanifested:
        raise oriel_integration_error(
            (
                "unmanifested oriel providers: "
                + ", ".join(
                    str(value)
                    for value
                    in unmanifested
                )
            )
        )

    if provider_errors:
        raise oriel_integration_error(
            (
                "oriel provider errors: "
                + canonical_json(
                    provider_errors
                )
            )
        )

    invariant_packets = (
        simulation,
        boundary,
        canon,
        observatory,
        capabilities,
    )

    for packet in invariant_packets:
        if packet.get(
            "authority_transfer",
            False,
        ) is not False:
            raise oriel_integration_error(
                "authority transfer detected"
            )

    result = {
        "schema":
            schema,

        "kind":
            "focused-integration-test",

        "owner":
            owner,

        "component":
            component,

        "authority_effect":
            authority_effect,

        "ok":
            True,

        "json_documents_valid":
            True,

        "json_document_count":
            len(
                json_checks
            ),

        "reality_bound_simulation_operational":
            True,

        "authority_boundary_valid":
            True,

        "canon_boundary_valid":
            True,

        "observatory_ready":
            True,

        "observed_state":
            observed_state,

        "capability_surface_resolved":
            True,

        "unavailable_module_count":
            0,

        "unmanifested_module_count":
            0,

        "provider_error_count":
            0,

        "historical_oriel_not_restored":
            (
                boundary.get(
                    (
                        "historical_oriel_"
                        "not_reactivated"
                    )
                )
                is True
            ),

        "carbon_remains_general_simulation_owner":
            True,

        "quantum_remains_carbon_owned":
            (
                boundary.get(
                    "quantum_remains_carbon_owned"
                )
                is True
            ),

        "causal_simulation_remains_carbon_owned":
            (
                boundary.get(
                    (
                        "causal_simulation_"
                        "remains_carbon_owned"
                    )
                )
                is True
            ),

        "historical_reality_remains_external":
            (
                boundary.get(
                    (
                        "historical_reality_"
                        "remains_external"
                    )
                )
                is True
            ),

        "source_state_mutated":
            False,

        "canon_effect":
            "none",

        "evidence_admission":
            False,

        "authority_transfer":
            False,

        "json_checks":
            json_checks,
    }

    required_final = (
        "historical_oriel_not_restored",
        "quantum_remains_carbon_owned",
        "causal_simulation_remains_carbon_owned",
        "historical_reality_remains_external",
    )

    failed_final = [
        field
        for field
        in required_final
        if result.get(
            field
        )
        is not True
    ]

    if failed_final:
        raise oriel_integration_error(
            (
                "closure invariants failed: "
                + ", ".join(
                    failed_final
                )
            )
        )

    result[
        "digest"
    ] = digest(
        {
            key:
                value
            for key, value
            in result.items()
            if key != "digest"
        }
    )

    return result


def main() -> int:
    try:
        output = run()

    except Exception as exc:
        print(
            json.dumps(
                {
                    "schema":
                        schema,

                    "kind":
                        "focused-integration-test",

                    "owner":
                        owner,

                    "component":
                        component,

                    "authority_effect":
                        authority_effect,

                    "ok":
                        False,

                    "error":
                        str(exc),

                    "authority_transfer":
                        False,
                },
                indent=2,
                sort_keys=True,
            )
        )

        return 1

    print(
        json.dumps(
            output,
            indent=2,
            ensure_ascii=False,
            sort_keys=True,
        )
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
