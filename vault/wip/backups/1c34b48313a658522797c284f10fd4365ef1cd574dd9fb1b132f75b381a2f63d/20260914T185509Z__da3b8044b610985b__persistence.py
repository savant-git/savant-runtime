#!/usr/bin/env python3

from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping, Protocol

from .model import (
    StraubValidationError,
)


schema = "savant.straub.persistence.v1"
owner = "savant"
authority_effect = "none"


class StraubPersistencePort(
    Protocol
):
    def save_capsule(
        self,
        capsule: Mapping[str, Any],
    ) -> None:
        ...

    def load_capsule(
        self,
    ) -> Mapping[str, Any] | None:
        ...


class MemoryPersistence:
    """
    Focused reference adapter.

    This proves the persistence contract without
    selecting a durable storage engine.
    """

    engine_id = "memory-reference"
    durable = False
    authoritative = False

    def __init__(
        self,
    ) -> None:
        self._capsule: (
            dict[str, Any]
            | None
        ) = None

    def save_capsule(
        self,
        capsule: Mapping[str, Any],
    ) -> None:
        if not isinstance(
            capsule,
            Mapping,
        ):
            raise StraubValidationError(
                "persistence capsule "
                "must be an object"
            )

        self._capsule = deepcopy(
            dict(capsule)
        )

    def load_capsule(
        self,
    ) -> Mapping[str, Any] | None:
        if self._capsule is None:
            return None

        return deepcopy(
            self._capsule
        )

    def health(
        self,
    ) -> dict[str, Any]:
        return {
            "schema":
                schema,
            "adapter":
                self.engine_id,
            "durable":
                self.durable,
            "authoritative":
                self.authoritative,
            "capsule_present":
                self._capsule
                is not None,
            "storage_engine_selected":
                False,
            "authority_effect":
                authority_effect,
        }
