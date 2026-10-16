#!/usr/bin/env python3

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from typing import Any

from alloy_assembler import (
    AlloyAssembler,
    AlloyAssemblerError,
    assembler,
)
from capability_compiler import (
    CapabilityCompiler,
    CapabilityCompilerError,
    compiler,
)
from sliver_pool import (
    SliverPool,
    SliverPoolError,
    build_pool,
)


OWNER = "prodigal:modus:coalesce"
SCHEMA = "savant://coalesce/modes/1"

AUTO_MODE = "auto"
MANUAL_MODE = "manual"

MAX_ALLOYS = 3
MAX_SLIVERS_PER_ALLOY = 9
MAX_TOTAL_SLIVERS = MAX_ALLOYS * MAX_SLIVERS_PER_ALLOY


class CoalesceModeError(RuntimeError):
    pass


def canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )


def digest(value: Any) -> str:
    return hashlib.sha256(
        canonical_json(value).encode("utf-8")
    ).hexdigest()


def normalize(value: Any) -> str:
    return " ".join(
        str(value or "")
        .strip()
        .lower()
        .split()
    )


def tokens(value: Any) -> frozenset[str]:
    return frozenset(
        token
        for token in re.findall(
            r"[a-z0-9]+",
            normalize(value),
        )
        if len(token) > 1
    )


@dataclass(
    frozen=True,
    slots=True,
)
class CapabilityEvidence:
    capability: str
    score: int
    evidence: tuple[str, ...]

    def projection(self) -> dict[str, Any]:
        return {
            "capability": self.capability,
            "score": self.score,
            "evidence": list(self.evidence),
        }


class CoalesceModeEngine:
    def __init__(
        self,
        *,
        pool: SliverPool | None = None,
        capability_compiler: CapabilityCompiler | None = None,
        alloy_assembler: AlloyAssembler | None = None,
    ) -> None:
        self.pool = pool or build_pool()
        self.compiler = capability_compiler or compiler()
        self.assembler = alloy_assembler or assembler()
        self._descriptors = self._build_descriptors()

    def _build_descriptors(
        self,
    ) -> dict[str, frozenset[str]]:
        descriptors: dict[str, frozenset[str]] = {}

        for sliver in self.pool.slivers:
            words = set(
                tokens(sliver.capability)
            )

            for slab_id in sliver.historical_slabs:
                words.update(
                    tokens(
                        slab_id
                        .replace(":", " ")
                        .replace("-", " ")
                    )
                )

            descriptors[
                sliver.capability
            ] = frozenset(words)

        return descriptors

    def _rank_capabilities(
        self,
        prompt: str,
    ) -> tuple[CapabilityEvidence, ...]:
        normalized_prompt = normalize(prompt)
        prompt_words = tokens(prompt)

        if not prompt_words:
            raise CoalesceModeError(
                "prompt is required"
            )

        rows: list[
            CapabilityEvidence
        ] = []

        for capability, descriptor in (
            self._descriptors.items()
        ):
            overlap = (
                prompt_words
                & descriptor
            )

            score = len(overlap)

            normalized_capability = normalize(
                capability
            )

            if (
                normalized_capability
                and normalized_capability
                in normalized_prompt
            ):
                score += 4

            if score > 0:
                rows.append(
                    CapabilityEvidence(
                        capability=capability,
                        score=score,
                        evidence=tuple(
                            sorted(overlap)
                        ),
                    )
                )

        return tuple(
            sorted(
                rows,
                key=lambda row: (
                    -row.score,
                    row.capability,
                ),
            )
        )

    def _manual_capabilities(
        self,
        prompt: str,
    ) -> tuple[CapabilityEvidence, ...]:
        ranked = self._rank_capabilities(
            prompt
        )

        if not ranked:
            raise CoalesceModeError(
                "manual prompt did not resolve "
                "to any known Coalesce capability"
            )

        return ranked

    def _auto_capabilities(
        self,
        prompt: str,
    ) -> tuple[CapabilityEvidence, ...]:
        ranked = self._rank_capabilities(
            prompt
        )

        if ranked:
            return ranked

        raise CoalesceModeError(
            "auto mode could not resolve the "
            "requested functionality from the "
            "current Sliver Pool"
        )

    def _partition(
        self,
        capabilities: tuple[
            CapabilityEvidence,
            ...
        ],
    ) -> tuple[
        tuple[
            CapabilityEvidence,
            ...
        ],
        ...
    ]:
        unique: list[
            CapabilityEvidence
        ] = []

        seen: set[str] = set()

        for row in capabilities:
            if row.capability in seen:
                continue

            seen.add(
                row.capability
            )
            unique.append(row)

        if not unique:
            raise CoalesceModeError(
                "no capabilities were resolved"
            )

        if len(unique) > MAX_TOTAL_SLIVERS:
            raise CoalesceModeError(
                "requested functionality requires "
                f"more than {MAX_ALLOYS} Alloys"
            )

        groups = []

        for offset in range(
            0,
            len(unique),
            MAX_SLIVERS_PER_ALLOY,
        ):
            groups.append(
                tuple(
                    unique[
                        offset:
                        offset
                        + MAX_SLIVERS_PER_ALLOY
                    ]
                )
            )

        return tuple(
            groups[:MAX_ALLOYS]
        )

    def _assemble_groups(
        self,
        *,
        mode: str,
        prompt: str,
        groups: tuple[
            tuple[
                CapabilityEvidence,
                ...
            ],
            ...
        ],
    ) -> tuple[
        dict[str, Any],
        ...
    ]:
        alloys = []

        prompt_digest = digest(
            {
                "mode": mode,
                "prompt": prompt,
            }
        )[:12]

        for index, group in enumerate(
            groups,
            start=1,
        ):
            capabilities = tuple(
                row.capability
                for row in group
            )

            alloy_id = (
                "alloy:coalesce:"
                f"{mode}:"
                f"{prompt_digest}:"
                f"{index}"
            )

            try:
                plan = (
                    self.compiler
                    .compile_requirements(
                        alloy_id=alloy_id,
                        capabilities=capabilities,
                        source=f"{mode}-prompt",
                    )
                )

                alloy = (
                    self.assembler
                    .assemble(plan)
                )

            except (
                CapabilityCompilerError,
                AlloyAssemblerError,
                SliverPoolError,
            ) as exc:
                raise CoalesceModeError(
                    str(exc)
                ) from exc

            alloy["mode"] = mode
            alloy[
                "prompt_digest"
            ] = prompt_digest
            alloy[
                "capability_evidence"
            ] = [
                row.projection()
                for row in group
            ]

            alloys.append(alloy)

        return tuple(alloys)

    def build(
        self,
        *,
        mode: str,
        prompt: str,
    ) -> dict[str, Any]:
        selected_mode = normalize(
            mode
        )

        text = str(
            prompt or ""
        ).strip()

        if selected_mode not in {
            AUTO_MODE,
            MANUAL_MODE,
        }:
            raise CoalesceModeError(
                "mode must be auto or manual"
            )

        if not text:
            raise CoalesceModeError(
                "prompt is required"
            )

        if selected_mode == AUTO_MODE:
            capabilities = (
                self._auto_capabilities(
                    text
                )
            )
        else:
            capabilities = (
                self._manual_capabilities(
                    text
                )
            )

        groups = self._partition(
            capabilities
        )

        alloys = self._assemble_groups(
            mode=selected_mode,
            prompt=text,
            groups=groups,
        )

        payload = {
            "ok": True,
            "schema": SCHEMA,
            "owner": OWNER,
            "mode": selected_mode,
            "prompt": text,
            "alloy_count": len(alloys),
            "maximum_alloys": MAX_ALLOYS,
            "maximum_slivers_per_alloy": (
                MAX_SLIVERS_PER_ALLOY
            ),
            "alloys": list(alloys),
            "behavior": {
                "auto": (
                    "evaluate user need and "
                    "compose the minimum sufficient "
                    "set of up to three Alloys"
                ),
                "manual": (
                    "resolve explicitly prompted "
                    "functionality and compose the "
                    "minimum sufficient set of up "
                    "to three Alloys"
                ),
                "manual_accuracy": (
                    "increases with prompt specificity"
                ),
            },
            "authoritative": False,
            "authority_effect": "none",
            "rebuildable": True,
        }

        payload["digest"] = digest(
            payload
        )

        return payload

    def auto(
        self,
        prompt: str,
    ) -> dict[str, Any]:
        return self.build(
            mode=AUTO_MODE,
            prompt=prompt,
        )

    def manual(
        self,
        prompt: str,
    ) -> dict[str, Any]:
        return self.build(
            mode=MANUAL_MODE,
            prompt=prompt,
        )

    def status(
        self,
    ) -> dict[str, Any]:
        return {
            "ok": True,
            "schema": SCHEMA,
            "owner": OWNER,
            "modes": {
                "auto": {
                    "evaluates_need": True,
                    "maximum_alloys": 3,
                },
                "manual": {
                    "prompt_driven": True,
                    "maximum_alloys": 3,
                    "specificity_improves_accuracy": True,
                },
            },
            "maximum_slivers_per_alloy": 9,
            "minimum_sufficient": True,
            "reference_composition": True,
            "authoritative": False,
            "authority_effect": "none",
        }


def mode_engine() -> CoalesceModeEngine:
    return CoalesceModeEngine()


def main() -> int:
    print(
        json.dumps(
            mode_engine().status(),
            ensure_ascii=False,
            sort_keys=True,
            indent=2,
            default=str,
        )
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
