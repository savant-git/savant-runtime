#!/usr/bin/env python3

"""
translucent runtime package.

this package initializer owns no executable translucent semantics.

canonical behavior remains in the concrete translucent runtime modules,
including svg and datrix_language. keeping this surface thin prevents
duplicate authority and duplicate implementation.
"""

from __future__ import annotations


schema = "savant.translucent.package.v1"
owner = "savant"
authority_effect = "none"

exact_source_recovery = False
reconstruction_basis = "verified package-boundary contract"


def manifest() -> dict[str, object]:
    return {
        "schema":
            schema,

        "owner":
            owner,

        "kind":
            "translucent-runtime-package",

        "behavior_owner":
            "concrete-runtime-modules",

        "duplicates_behavior":
            False,

        "exact_source_recovery":
            exact_source_recovery,

        "reconstruction_basis":
            reconstruction_basis,

        "authority_effect":
            authority_effect,
    }


__all__ = [
    "authority_effect",
    "manifest",
    "owner",
    "schema",
]
