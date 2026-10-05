#!/usr/bin/env python3

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


PALAVER_ROOT = Path(
    "/root/savant-runtime/ontology/obelisks/_template/segue/gates/"
    "_template/segue/innates/_template/segue/exiles/palaver"
)

CONTRACT_MANIFEST = (
    PALAVER_ROOT
    / "interface"
    / "contracts"
    / "contracts.json"
)

OWNER = "palaver"

EXPECTED_MANIFEST_ID = (
    "palaver.contracts"
)

EXPECTED_MANIFEST_TYPE = (
    "interface_contract_manifest"
)


class ContractError(
    RuntimeError
):
    pass


class ContractManifestError(
    ContractError
):
    pass


class ContractNotFoundError(
    ContractError
):
    pass


class ContractValidationError(
    ContractError
):
    pass


def _load_manifest() -> dict[str, Any]:
    if not CONTRACT_MANIFEST.is_file():
        raise ContractManifestError(
            "Palaver contract manifest missing: "
            + str(CONTRACT_MANIFEST)
        )

    try:
        value = json.loads(
            CONTRACT_MANIFEST.read_text(
                encoding="utf-8"
            )
        )
    except json.JSONDecodeError as exc:
        raise ContractManifestError(
            "Palaver contract manifest is invalid JSON: "
            + str(exc)
        ) from exc

    if not isinstance(
        value,
        dict,
    ):
        raise ContractManifestError(
            "Palaver contract manifest root "
            "must be an object"
        )

    if value.get(
        "id"
    ) != EXPECTED_MANIFEST_ID:
        raise ContractManifestError(
            "Palaver contract manifest identity mismatch"
        )

    if value.get(
        "owner"
    ) != OWNER:
        raise ContractManifestError(
            "Palaver contract manifest owner mismatch"
        )

    if value.get(
        "type"
    ) != EXPECTED_MANIFEST_TYPE:
        raise ContractManifestError(
            "Palaver contract manifest type mismatch"
        )

    contracts = value.get(
        "contracts"
    )

    if not isinstance(
        contracts,
        list,
    ):
        raise ContractManifestError(
            "Palaver contract manifest contracts "
            "must be a list"
        )

    return value


def registry() -> dict[str, dict[str, Any]]:
    manifest = _load_manifest()

    result: dict[
        str,
        dict[str, Any],
    ] = {}

    for raw in manifest[
        "contracts"
    ]:
        if not isinstance(
            raw,
            dict,
        ):
            raise ContractManifestError(
                "Palaver contract entry "
                "must be an object"
            )

        contract_id = str(
            raw.get(
                "id",
                "",
            )
            or ""
        ).strip()

        if not contract_id:
            raise ContractManifestError(
                "Palaver contract entry missing id"
            )

        if contract_id in result:
            raise ContractManifestError(
                "Duplicate Palaver contract id: "
                + contract_id
            )

        result[
            contract_id
        ] = raw

    return result


def contract(
    contract_id: str,
) -> dict[str, Any]:
    selected = str(
        contract_id
        or ""
    ).strip()

    if not selected:
        raise ContractNotFoundError(
            "Palaver contract id is required"
        )

    contracts = registry()

    if selected not in contracts:
        raise ContractNotFoundError(
            "Unknown Palaver contract: "
            + selected
        )

    return contracts[
        selected
    ]


def _required_fields(
    declaration: dict[str, Any],
    side: str,
) -> tuple[str, ...]:
    section = declaration.get(
        side
    )

    if section is None:
        return ()

    if not isinstance(
        section,
        dict,
    ):
        raise ContractManifestError(
            f"Palaver contract {side} "
            "declaration must be an object"
        )

    raw_required = section.get(
        "required",
        [],
    )

    if not isinstance(
        raw_required,
        list,
    ):
        raise ContractManifestError(
            f"Palaver contract {side}.required "
            "must be a list"
        )

    required: list[str] = []

    for raw in raw_required:
        field = str(
            raw
            or ""
        ).strip()

        if not field:
            raise ContractManifestError(
                f"Palaver contract {side}.required "
                "contains an empty field"
            )

        required.append(
            field
        )

    return tuple(
        required
    )


def validate(
    contract_id: str,
    payload: Any,
    *,
    side: str = "input",
) -> dict[str, Any]:
    if side not in {
        "input",
        "output",
    }:
        raise ContractValidationError(
            "Palaver contract validation side "
            "must be input or output"
        )

    declaration = contract(
        contract_id
    )

    if not isinstance(
        payload,
        dict,
    ):
        raise ContractValidationError(
            f"{contract_id} {side} "
            "payload must be an object"
        )

    required = _required_fields(
        declaration,
        side,
    )

    missing = [
        field
        for field in required
        if field not in payload
    ]

    if missing:
        raise ContractValidationError(
            f"{contract_id} {side} missing "
            "required field(s): "
            + ", ".join(
                missing
            )
        )

    return payload


def validate_input(
    contract_id: str,
    payload: Any,
) -> dict[str, Any]:
    return validate(
        contract_id,
        payload,
        side="input",
    )


def validate_output(
    contract_id: str,
    payload: Any,
) -> dict[str, Any]:
    return validate(
        contract_id,
        payload,
        side="output",
    )


def status() -> dict[str, Any]:
    contracts = registry()

    return {
        "owner": OWNER,
        "manifest": str(
            CONTRACT_MANIFEST
        ),
        "manifest_id": (
            EXPECTED_MANIFEST_ID
        ),
        "contract_count": len(
            contracts
        ),
        "contracts": sorted(
            contracts
        ),
        "authority_effect": "none",
        "runtime_enforcement": (
            "explicit_invocation"
        ),
        "route_mapping": False,
    }


def selftest() -> dict[str, Any]:
    validate_input(
        "palaver.read.v1",
        {
            "path": "runtime/server.py",
        },
    )

    rejected = False

    try:
        validate_input(
            "palaver.read.v1",
            {},
        )
    except ContractValidationError:
        rejected = True

    if not rejected:
        raise ContractValidationError(
            "Missing required field "
            "was not rejected"
        )

    validate_output(
        "palaver.read.v1",
        {
            "path": "runtime/server.py",
            "content": "",
        },
    )

    return {
        "ok": True,
        **status(),
        "valid_read_accepted": True,
        "invalid_read_rejected": True,
        "valid_read_output_accepted": True,
    }


if __name__ == "__main__":
    print(
        json.dumps(
            selftest(),
            indent=2,
            sort_keys=True,
        )
    )
