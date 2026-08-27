#!/usr/bin/env python3

from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(
    "/root/savant-runtime"
)

if str(ROOT) not in sys.path:
    sys.path.insert(
        0,
        str(ROOT),
    )


from runtime.living_substrates import (  # noqa: E402
    SLOT_TO_SUBSTRATE,
    LivingBinding,
    LivingSlotFabric,
)


def main() -> int:
    fabric = LivingSlotFabric()

    structure = LivingBinding(
        binding_id=(
            "binding:test:"
            "structure"
        ),
        owner_id=(
            "instance:test"
        ),
        slot="structure",
        substrate="scyon",
        substrate_instance=(
            "scyon:test"
        ),
        authority_state=(
            "proposed"
        ),
        enabled=False,
        version="1.0.0",
        specialization={
            "focal":
                "focal:test",
            "overlay":
                None,
            "mask":
                None,
            "policy":
                None,
        },
        parameters={
            "test":
                True
        },
        dependencies=(),
        lineage={
            "supersedes": [],
            "superseded_by": [],
        },
        provenance={
            "source":
                "focused-validator"
        },
        compatibility={
            "minimum_substrate_version":
                None,
            "adapter":
                None,
            "reversible":
                True,
        },
    )

    assurance = LivingBinding(
        binding_id=(
            "binding:test:"
            "assurance"
        ),
        owner_id=(
            "instance:test"
        ),
        slot="assurance",
        substrate="thryce",
        substrate_instance=(
            "thryce:test"
        ),
        authority_state=(
            "proposed"
        ),
        enabled=False,
        version="1.0.0",
        specialization={
            "focal":
                None,
            "overlay":
                "overlay:test",
            "mask":
                None,
            "policy":
                None,
        },
        parameters={},
        dependencies=(
            "binding:test:"
            "structure",
        ),
        lineage={
            "supersedes": [],
            "superseded_by": [],
        },
        provenance={
            "source":
                "focused-validator"
        },
        compatibility={
            "minimum_substrate_version":
                None,
            "adapter":
                None,
            "reversible":
                True,
        },
    )

    fabric.add(
        structure
    )

    fabric.add(
        assurance
    )

    validation = (
        fabric.validate()
    )

    health = (
        fabric.health()
    )

    owner = (
        fabric.owner_projection(
            "instance:test"
        )
    )

    dependencies = (
        fabric.dependency_report()
    )

    expected_order = [
        "binding:test:structure",
        "binding:test:assurance",
    ]

    focused = {
        "nine_slots": (
            len(
                SLOT_TO_SUBSTRATE
            )
            == 9
        ),
        "twenty_seven_enhancements": (
            fabric.enhancement_count
            == 27
        ),
        "binding_validation": (
            validation["valid"]
        ),
        "health": (
            health["healthy"]
        ),
        "owner_binding_count": (
            len(
                owner["bindings"]
            )
            == 2
        ),
        "dependency_order": (
            dependencies[
                "topological_order"
            ]
            == expected_order
        ),
        "mutation_authorized": (
            validation[
                "mutation_authorized"
            ]
            is False
        ),
        "physical_migration_authorized": (
            validation[
                "physical_migration_authorized"
            ]
            is False
        ),
        "projections_non_authoritative": (
            owner[
                "authoritative"
            ]
            is False
        ),
    }

    report = {
        "schema": (
            "savant://assurance/"
            "living-slot-fabric/"
            "focused/1.0.0"
        ),
        "valid": all(
            focused.values()
        ),
        "checks":
            focused,
        "validation":
            validation,
        "health":
            health,
        "dependency_report":
            dependencies,
    }

    print(
        json.dumps(
            report,
            indent=2,
            sort_keys=True,
        )
    )

    return (
        0
        if report["valid"]
        else 1
    )


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
