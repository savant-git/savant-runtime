#!/usr/bin/env python3

from __future__ import annotations

from pathlib import Path
from typing import Any

from .datrix import StraubDatrix


schema = "savant.carbon.straub.module.v1"
owner = "carbon"
module_name = "straub"
authority_effect = "none"


DATRIX_COMPONENTS = (
    "dyad",
    "umbra",
    "membrane",
    "radia",
    "isotopes",
)


class Straub:
    """
    Carbon-owned module responsible for creating,
    opening, and operating datrixes.

    Straub is not itself a datrix.

    A datrix is the semantic data structure created and
    managed by Straub. Datrix components include dyad,
    umbra, membrane, radia, isotopes, and additional
    Straub-defined components as they become authoritative.
    """

    exile = "carbon"
    name = "straub"
    product = "datrix"

    @classmethod
    def open_datrix(
        cls,
        path: str | Path,
    ) -> StraubDatrix:
        return StraubDatrix.open(
            path
        )

    @classmethod
    def create_datrix(
        cls,
        path: str | Path,
    ) -> StraubDatrix:
        """
        Create or open a datrix at the supplied custody path.

        StraubDatrix.open is intentionally idempotent:
        an absent capsule begins an empty datrix and an
        existing capsule replays the existing datrix.
        """
        return StraubDatrix.open(
            path
        )

    @classmethod
    def edifice(
        cls,
    ) -> dict[str, Any]:
        return {
            "schema":
                "savant.carbon.straub."
                "edifice.v1",
            "exile":
                "carbon",
            "module":
                "straub",
            "creates":
                "datrix",
            "datrix_components": [
                {
                    "name":
                        "dyad",
                    "membership":
                        "datrix",
                    "contract_state":
                        "implemented",
                },
                {
                    "name":
                        "umbra",
                    "membership":
                        "datrix",
                    "contract_state":
                        "implemented",
                },
                {
                    "name":
                        "membrane",
                    "membership":
                        "datrix",
                    "contract_state":
                        "implemented",
                },
                {
                    "name":
                        "radia",
                    "membership":
                        "datrix",
                    "contract_state":
                        "implemented",
                },
                {
                    "name":
                        "isotopes",
                    "membership":
                        "datrix",
                    "contract_state":
                        "semantics_pending",
                },
            ],
            "straub_is_datrix":
                False,
            "datrix_is_straub_module":
                False,
            "authority_effect":
                "none",
        }

    @classmethod
    def health(
        cls,
    ) -> dict[str, Any]:
        return {
            "schema":
                schema,
            "status":
                "ok",
            "exile":
                "carbon",
            "module":
                "straub",
            "role":
                "datrix system",
            "creates":
                "datrix",
            "straub_is_datrix":
                False,
            "datrix_component_names":
                list(
                    DATRIX_COMPONENTS
                ),
            "isotope_semantics":
                "pending_authoritative_contract",
            "authority_effect":
                authority_effect,
        }
