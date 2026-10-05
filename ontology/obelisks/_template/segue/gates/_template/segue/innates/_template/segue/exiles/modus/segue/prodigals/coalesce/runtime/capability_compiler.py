#!/usr/bin/env python3

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from sliver_pool import (
    SliverPool,
    SliverPoolError,
    build_pool,
)


COALESCE_ROOT = Path(
    "/root/savant-runtime/ontology/obelisks/_template/segue/gates/"
    "_template/segue/innates/_template/segue/exiles/modus/segue/"
    "prodigals/coalesce"
).resolve()

OWNER = "prodigal:modus:coalesce"

COMPILER_SCHEMA = (
    "savant://coalesce/"
    "capability-compiler/1"
)

ALLOY_PLAN_SCHEMA = (
    "savant://coalesce/"
    "alloy-plan/1"
)

DEFAULT_MAX_SLIVERS = 9


class CapabilityCompilerError(
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


def normalize_text(
    value: Any,
) -> str:
    return str(
        value
        or ""
    ).strip()


def normalize_tokens(
    values: Iterable[Any],
) -> tuple[str, ...]:
    result = {
        normalize_text(
            value
        )
        for value
        in values
    }

    result.discard(
        ""
    )

    return tuple(
        sorted(
            result
        )
    )


@dataclass(
    frozen=True,
    slots=True,
)
class CapabilityRequirement:
    capability: str
    source: str

    def projection(
        self,
    ) -> dict[str, str]:
        return {
            "capability": (
                self.capability
            ),
            "source": self.source,
        }


@dataclass(
    frozen=True,
    slots=True,
)
class AlloyPlan:
    alloy_id: str
    sliver_ids: tuple[str, ...]
    requirements: tuple[
        CapabilityRequirement,
        ...
    ]
    source: str
    owner: str = OWNER

    def projection(
        self,
    ) -> dict[str, Any]:
        payload = {
            "schema": (
                ALLOY_PLAN_SCHEMA
            ),
            "id": self.alloy_id,
            "owner": self.owner,
            "source": self.source,
            "slivers": list(
                self.sliver_ids
            ),
            "sliver_count": len(
                self.sliver_ids
            ),
            "requirements": [
                requirement
                .projection()
                for requirement
                in self.requirements
            ],
            "minimum_sufficient": True,
            "canonical_substance": (
                "reference-only"
            ),
            "authoritative": False,
            "rebuildable": True,
            "authority_effect": "none",
        }

        payload[
            "digest"
        ] = digest(
            payload
        )

        return payload


class CapabilityCompiler:
    def __init__(
        self,
        pool: SliverPool | None = None,
        *,
        max_slivers: int = (
            DEFAULT_MAX_SLIVERS
        ),
    ) -> None:
        self.pool = (
            pool
            or build_pool()
        )

        if max_slivers < 1:
            raise CapabilityCompilerError(
                "max_slivers must be "
                "positive"
            )

        self.max_slivers = (
            int(
                max_slivers
            )
        )

        self._capability_index = {
            sliver.capability:
                sliver.sliver_id
            for sliver
            in self.pool.slivers
        }

    def capabilities(
        self,
    ) -> tuple[str, ...]:
        return tuple(
            sorted(
                self._capability_index
            )
        )

    def resolve_capabilities(
        self,
        capabilities: Iterable[Any],
    ) -> tuple[str, ...]:
        requested = normalize_tokens(
            capabilities
        )

        unresolved = tuple(
            capability
            for capability
            in requested
            if capability
            not in self._capability_index
        )

        if unresolved:
            raise CapabilityCompilerError(
                "unresolved capabilities: "
                + ", ".join(
                    unresolved
                )
            )

        selected = tuple(
            sorted(
                {
                    self._capability_index[
                        capability
                    ]
                    for capability
                    in requested
                }
            )
        )

        if len(
            selected
        ) > self.max_slivers:
            raise CapabilityCompilerError(
                "composition requires "
                f"{len(selected)} slivers; "
                f"maximum is "
                f"{self.max_slivers}"
            )

        return selected

    def compile_requirements(
        self,
        *,
        alloy_id: str,
        capabilities: Iterable[Any],
        source: str = (
            "explicit-capability-request"
        ),
    ) -> AlloyPlan:
        identity = normalize_text(
            alloy_id
        )

        if not identity:
            raise CapabilityCompilerError(
                "alloy_id is required"
            )

        normalized = normalize_tokens(
            capabilities
        )

        slivers = (
            self.resolve_capabilities(
                normalized
            )
        )

        requirements = tuple(
            CapabilityRequirement(
                capability=capability,
                source=source,
            )
            for capability
            in normalized
        )

        return AlloyPlan(
            alloy_id=identity,
            sliver_ids=slivers,
            requirements=requirements,
            source=source,
        )

    def compile_recipe(
        self,
        application_id: str,
    ) -> AlloyPlan:
        identity = normalize_text(
            application_id
        )

        if not identity:
            raise CapabilityCompilerError(
                "application_id is required"
            )

        try:
            sliver_ids = (
                self.pool
                .application_slivers(
                    identity
                )
            )
        except SliverPoolError as exc:
            raise CapabilityCompilerError(
                str(
                    exc
                )
            ) from exc

        if len(
            sliver_ids
        ) > self.max_slivers:
            raise CapabilityCompilerError(
                "historical recipe "
                f"{identity} resolves to "
                f"{len(sliver_ids)} slivers; "
                f"maximum is "
                f"{self.max_slivers}"
            )

        requirements = tuple(
            CapabilityRequirement(
                capability=(
                    self.pool.get(
                        sliver_id
                    ).capability
                ),
                source=(
                    "historical-recipe:"
                    + identity
                ),
            )
            for sliver_id
            in sliver_ids
        )

        return AlloyPlan(
            alloy_id=identity,
            sliver_ids=sliver_ids,
            requirements=requirements,
            source=(
                "historical-recipe:"
                + identity
            ),
        )

    def status(
        self,
    ) -> dict[str, Any]:
        payload = {
            "schema": (
                COMPILER_SCHEMA
            ),
            "owner": OWNER,
            "pool_sliver_count": len(
                self.pool.slivers
            ),
            "historical_slab_count": (
                len(
                    self.pool
                    .historical_slabs
                )
            ),
            "max_slivers_per_alloy": (
                self.max_slivers
            ),
            "minimum_sufficient_selection": (
                True
            ),
            "deduplicated_selection": (
                True
            ),
            "unknown_capabilities_fail": (
                True
            ),
            "fixed_pool_size": False,
            "canonical_substance": (
                "reference-only"
            ),
            "authoritative": False,
            "rebuildable": True,
            "authority_effect": "none",
        }

        payload[
            "digest"
        ] = digest(
            payload
        )

        return payload


def compiler() -> CapabilityCompiler:
    return CapabilityCompiler()


def main() -> int:
    engine = compiler()

    print(
        json.dumps(
            engine.status(),
            indent=2,
            sort_keys=True,
        )
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
