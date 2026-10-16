#!/usr/bin/env python3

from __future__ import annotations

from pathlib import Path
from typing import Any

from .datrix import StraubDatrix


schema = "savant.carbon.straub.module.v2"
owner = "carbon"
module_name = "straub"
authority_effect = "none"


DATRIX_COMPONENTS = (
    "dyad",
    "umbra",
    "membrane",
    "isotope",
)


class Straub:
    """
    Carbon-owned module responsible for creating,
    opening, and operating datrixes.

    Straub is not itself a datrix.

    A datrix is the semantic data structure created and
    managed by Straub.

    Isotopes are deterministic projections derived from
    canonical datrix substance.
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
                "edifice.v2",
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
                        "isotope",
                    "membership":
                        "datrix",
                    "contract_state":
                        "implemented",
                    "meaning":
                        "deterministic projection",
                },
            ],
            "projection_primitive":
                "isotope",
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
            "projection_primitive":
                "isotope",
            "isotope_semantics":
                "deterministic projection",
            "authority_effect":
                authority_effect,
        }
