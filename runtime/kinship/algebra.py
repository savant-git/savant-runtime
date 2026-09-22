#!/usr/bin/env python3
from __future__ import annotations

from collections import deque
from dataclasses import replace
from typing import Iterable

from .graph import KindredGraph
from .model import (
    DirectLineageEdge,
    KindredDetermination,
    PathStep,
)
from .registry import KindredRegistry


def _step_up(
    edge: DirectLineageEdge,
) -> PathStep:
    return PathStep(
        edge_id=edge.id,
        source=edge.child,
        target=edge.parent,
        direction="parent",
        role=edge.role,
        domain=edge.domain,
        parent_profile=(
            edge.parent_profile
        ),
        child_profile=(
            edge.child_profile
        ),
    )


def _step_down(
    edge: DirectLineageEdge,
) -> PathStep:
    return PathStep(
        edge_id=edge.id,
        source=edge.parent,
        target=edge.child,
        direction="child",
        role=edge.role,
        domain=edge.domain,
        parent_profile=(
            edge.parent_profile
        ),
        child_profile=(
            edge.child_profile
        ),
    )


class KindredAlgebra:
    def __init__(
        self,
        graph: KindredGraph,
        registry: KindredRegistry,
    ) -> None:
        self.graph = graph
        self.registry = registry

    def ancestor_paths(
        self,
        identifier: str,
        *,
        max_depth: int = 8,
        active_only: bool = True,
        domain: str | None = None,
    ) -> dict[
        str,
        tuple[PathStep, ...],
    ]:
        start = self.graph.resolve_node_id(
            identifier
        )

        queue = deque([
            (
                start,
                tuple(),
            )
        ])

        paths: dict[
            str,
            tuple[PathStep, ...],
        ] = {}

        visited_depth = {
            start: 0
        }

        while queue:
            current, path = (
                queue.popleft()
            )

            if len(
                path
            ) >= max_depth:
                continue

            for edge in (
                self.graph.incoming_edges(
                    current,
                    active_only=active_only,
                    domain=domain,
                )
            ):
                step = _step_up(
                    edge
                )

                next_path = (
                    *path,
                    step,
                )

                ancestor = edge.parent
                next_depth = len(
                    next_path
                )

                previous_depth = (
                    visited_depth.get(
                        ancestor
                    )
                )

                if (
                    previous_depth is not None
                    and previous_depth
                    <= next_depth
                ):
                    continue

                visited_depth[
                    ancestor
                ] = next_depth

                paths[
                    ancestor
                ] = next_path

                queue.append(
                    (
                        ancestor,
                        next_path,
                    )
                )

        return paths

    def descendant_paths(
        self,
        identifier: str,
        *,
        max_depth: int = 8,
        active_only: bool = True,
        domain: str | None = None,
    ) -> dict[
        str,
        tuple[PathStep, ...],
    ]:
        start = self.graph.resolve_node_id(
            identifier
        )

        queue = deque([
            (
                start,
                tuple(),
            )
        ])

        paths: dict[
            str,
            tuple[PathStep, ...],
        ] = {}

        visited_depth = {
            start: 0
        }

        while queue:
            current, path = (
                queue.popleft()
            )

            if len(
                path
            ) >= max_depth:
                continue

            for edge in (
                self.graph.outgoing_edges(
                    current,
                    active_only=active_only,
                    domain=domain,
                )
            ):
                step = _step_down(
                    edge
                )

                next_path = (
                    *path,
                    step,
                )

                descendant = edge.child
                next_depth = len(
                    next_path
                )

                previous_depth = (
                    visited_depth.get(
                        descendant
                    )
                )

                if (
                    previous_depth is not None
                    and previous_depth
                    <= next_depth
                ):
                    continue

                visited_depth[
                    descendant
                ] = next_depth

                paths[
                    descendant
                ] = next_path

                queue.append(
                    (
                        descendant,
                        next_path,
                    )
                )

        return paths

    def _parent_signature(
        self,
        identifier: str,
        *,
        active_only: bool,
        domain: str | None,
    ) -> dict[
        str,
        tuple[
            str,
            str,
            str,
        ],
    ]:
        return {
            edge.parent: (
                edge.parent_profile,
                edge.role,
                edge.domain,
            )
            for edge
            in self.graph.incoming_edges(
                identifier,
                active_only=active_only,
                domain=domain,
            )
        }

    def sibling_determinations(
        self,
        identifier: str,
        *,
        active_only: bool = True,
        domain: str | None = None,
    ) -> list[
        KindredDetermination
    ]:
        subject = self.graph.resolve_node_id(
            identifier
        )

        subject_signature = (
            self._parent_signature(
                subject,
                active_only=active_only,
                domain=domain,
            )
        )

        results: list[
            KindredDetermination
        ] = []

        for relative in (
            self.graph.sibling_candidates(
                subject,
                active_only=active_only,
                domain=domain,
            )
        ):
            relative_signature = (
                self._parent_signature(
                    relative,
                    active_only=active_only,
                    domain=domain,
                )
            )

            shared = sorted(
                set(
                    subject_signature
                ).intersection(
                    relative_signature
                )
            )

            if not shared:
                continue

            full = (
                subject_signature
                == relative_signature
            )

            profiles = {
                subject_signature[
                    parent
                ][0]
                for parent in shared
            }

            domains = sorted({
                subject_signature[
                    parent
                ][2]
                for parent in shared
            })

            generation_events = {
                edge.generation_event
                for edge
                in self.graph.incoming_edges(
                    subject,
                    active_only=active_only,
                    domain=domain,
                )
                if edge.parent in shared
                and edge.generation_event
            }

            relative_events = {
                edge.generation_event
                for edge
                in self.graph.incoming_edges(
                    relative,
                    active_only=active_only,
                    domain=domain,
                )
                if edge.parent in shared
                and edge.generation_event
            }

            if (
                generation_events
                and generation_events
                .intersection(
                    relative_events
                )
            ):
                relationship = "twin"

            elif full:
                relationship = (
                    "full_sibling"
                )

            else:
                relationship = (
                    "half_sibling"
                )

            results.append(
                KindredDetermination(
                    subject=subject,
                    relative=relative,
                    relationship=(
                        relationship
                    ),
                    generation_offset=0,
                    domains=tuple(
                        domains
                    ),
                    shared_parents=tuple(
                        shared
                    ),
                    confidence=1.0,
                    rule=(
                        "compare_complete_"
                        "direct_parent_"
                        "signatures"
                    ),
                    operational_meaning=(
                        self.registry.meaning(
                            relationship
                        )
                    ),
                    metadata={
                        "shared_parent_profiles": (
                            sorted(
                                profiles
                            )
                        ),
                        "subject_parent_count": (
                            len(
                                subject_signature
                            )
                        ),
                        "relative_parent_count": (
                            len(
                                relative_signature
                            )
                        ),
                    },
                )
            )

            # Twinhood refines, rather than replaces, the complete-parent
            # sibling relation.
            if relationship == "twin" and full:
                results.append(replace(results[-1], relationship="full_sibling",
                    rule="compare_complete_direct_parent_signatures",
                    operational_meaning=self.registry.meaning("full_sibling")))

            if "mother" in profiles:
                results.append(
                    KindredDetermination(
                        subject=subject,
                        relative=relative,
                        relationship=(
                            "maternal_sibling"
                        ),
                        generation_offset=0,
                        domains=tuple(
                            domains
                        ),
                        shared_parents=tuple(
                            shared
                        ),
                        confidence=1.0,
                        rule=(
                            "shared_mother_"
                            "profile_parent"
                        ),
                        operational_meaning=(
                            self.registry.meaning(
                                "maternal_sibling"
                            )
                        ),
                    )
                )

            if "father" in profiles:
                results.append(
                    KindredDetermination(
                        subject=subject,
                        relative=relative,
                        relationship=(
                            "paternal_sibling"
                        ),
                        generation_offset=0,
                        domains=tuple(
                            domains
                        ),
                        shared_parents=tuple(
                            shared
                        ),
                        confidence=1.0,
                        rule=(
                            "shared_father_"
                            "profile_parent"
                        ),
                        operational_meaning=(
                            self.registry.meaning(
                                "paternal_sibling"
                            )
                        ),
                    )
                )

        return results

    def determine(
        self,
        subject_identifier: str,
        relative_identifier: str,
        *,
        max_depth: int = 8,
        active_only: bool = True,
        domain: str | None = None,
    ) -> list[
        KindredDetermination
    ]:
        subject = self.graph.resolve_node_id(
            subject_identifier
        )

        relative = self.graph.resolve_node_id(
            relative_identifier
        )

        if subject == relative:
            return [
                KindredDetermination(
                    subject=subject,
                    relative=relative,
                    relationship="self",
                    generation_offset=0,
                    confidence=1.0,
                    rule="identity",
                    operational_meaning=(
                        "The subject and "
                        "relative are the "
                        "same authoritative "
                        "node."
                    ),
                )
            ]

        results: list[
            KindredDetermination
        ] = []

        incoming = (
            self.graph.incoming_edges(
                subject,
                active_only=active_only,
                domain=domain,
            )
        )

        for edge in incoming:
            if edge.parent != relative:
                continue

            results.append(
                KindredDetermination(
                    subject=subject,
                    relative=relative,
                    relationship=(
                        edge.parent_profile
                    ),
                    generation_offset=-1,
                    domains=(
                        edge.domain,
                    ),
                    path=(
                        _step_up(
                            edge
                        ),
                    ),
                    confidence=1.0,
                    rule=(
                        "direct_parent_profile"
                    ),
                    operational_meaning=(
                        self.registry.meaning(
                            edge.parent_profile
                        )
                    ),
                    metadata={
                        "role": edge.role,
                        "axis": edge.axis,
                        "edge_id": edge.id,
                    },
                )
            )

        outgoing = (
            self.graph.outgoing_edges(
                subject,
                active_only=active_only,
                domain=domain,
            )
        )

        for edge in outgoing:
            if edge.child != relative:
                continue

            results.append(
                KindredDetermination(
                    subject=subject,
                    relative=relative,
                    relationship=(
                        edge.child_profile
                    ),
                    generation_offset=1,
                    domains=(
                        edge.domain,
                    ),
                    path=(
                        _step_down(
                            edge
                        ),
                    ),
                    confidence=1.0,
                    rule=(
                        "direct_child_profile"
                    ),
                    operational_meaning=(
                        self.registry.meaning(
                            edge.child_profile
                        )
                    ),
                    metadata={
                        "role": edge.role,
                        "axis": edge.axis,
                        "edge_id": edge.id,
                    },
                )
            )

        for alliance in (
            self.graph.alliance_contracts(
                subject,
                active_only=active_only,
            )
        ):
            if relative not in alliance.partners:
                continue

            results.append(
                KindredDetermination(
                    subject=subject,
                    relative=relative,
                    relationship=(
                        alliance.profile
                    ),
                    generation_offset=0,
                    domains=(
                        alliance.domains
                    ),
                    alliance_ids=(
                        alliance.id,
                    ),
                    confidence=1.0,
                    rule=(
                        "direct_alliance_"
                        "contract"
                    ),
                    operational_meaning=(
                        self.registry.meaning(
                            alliance.profile
                        )
                    ),
                    metadata={
                        "contract": dict(
                            alliance.contract
                        )
                    },
                )
            )

        ancestors = self.ancestor_paths(
            subject,
            max_depth=max_depth,
            active_only=active_only,
            domain=domain,
        )

        ancestor_path = ancestors.get(
            relative
        )

        if ancestor_path:
            depth = len(
                ancestor_path
            )

            if depth == 2:
                profile = (
                    ancestor_path[
                        -1
                    ].parent_profile
                )

                relationship = {
                    "mother": (
                        "grandmother"
                    ),
                    "father": (
                        "grandfather"
                    ),
                }.get(
                    profile,
                    "grandparent",
                )

            elif depth > 2:
                relationship = (
                    "great_"
                    * (
                        depth
                        - 2
                    )
                    + "grandparent"
                )

            else:
                relationship = (
                    ancestor_path[
                        0
                    ].parent_profile
                )

            results.append(
                KindredDetermination(
                    subject=subject,
                    relative=relative,
                    relationship=(
                        relationship
                    ),
                    generation_offset=(
                        -depth
                    ),
                    domains=tuple(
                        sorted({
                            step.domain
                            for step
                            in ancestor_path
                        })
                    ),
                    path=ancestor_path,
                    confidence=1.0,
                    rule=(
                        "transitive_parent_"
                        "path"
                    ),
                    operational_meaning=(
                        self.registry.meaning(
                            "grandparent"
                            if depth == 2
                            else "ancestor"
                        )
                    ),
                )
            )

        descendants = (
            self.descendant_paths(
                subject,
                max_depth=max_depth,
                active_only=active_only,
                domain=domain,
            )
        )

        descendant_path = (
            descendants.get(
                relative
            )
        )

        if descendant_path:
            depth = len(
                descendant_path
            )

            if depth == 2:
                last_profile = (
                    descendant_path[
                        -1
                    ].child_profile
                )

                relationship = {
                    "daughter": (
                        "granddaughter"
                    ),
                    "son": (
                        "grandson"
                    ),
                }.get(
                    last_profile,
                    "grandchild",
                )

            elif depth > 2:
                relationship = (
                    "great_"
                    * (
                        depth
                        - 2
                    )
                    + "grandchild"
                )

            else:
                relationship = (
                    descendant_path[
                        0
                    ].child_profile
                )

            results.append(
                KindredDetermination(
                    subject=subject,
                    relative=relative,
                    relationship=(
                        relationship
                    ),
                    generation_offset=depth,
                    domains=tuple(
                        sorted({
                            step.domain
                            for step
                            in descendant_path
                        })
                    ),
                    path=descendant_path,
                    confidence=1.0,
                    rule=(
                        "transitive_child_"
                        "path"
                    ),
                    operational_meaning=(
                        self.registry.meaning(
                            "grandchild"
                            if depth == 2
                            else "descendant"
                        )
                    ),
                )
            )

        sibling_results = {
            determination.relative: []
            for determination
            in self.sibling_determinations(
                subject,
                active_only=active_only,
                domain=domain,
            )
        }

        for determination in (
            self.sibling_determinations(
                subject,
                active_only=active_only,
                domain=domain,
            )
        ):
            sibling_results[
                determination.relative
            ].append(
                determination
            )

        results.extend(
            sibling_results.get(
                relative,
                []
            )
        )

        parent_ids = self.graph.parents(
            subject,
            active_only=active_only,
            domain=domain,
        )

        for parent in parent_ids:
            parent_siblings = {
                determination.relative
                for determination
                in self.sibling_determinations(
                    parent,
                    active_only=active_only,
                    domain=domain,
                )
            }

            if relative in parent_siblings:
                results.append(
                    KindredDetermination(
                        subject=subject,
                        relative=relative,
                        relationship=(
                            "aunt_or_uncle"
                        ),
                        generation_offset=-1,
                        shared_parents=tuple(
                            self.graph.parents(
                                parent,
                                active_only=active_only,
                                domain=domain,
                            )
                        ),
                        confidence=1.0,
                        rule=(
                            "sibling_of_direct_"
                            "parent"
                        ),
                        operational_meaning=(
                            self.registry.meaning(
                                "aunt_or_uncle"
                            )
                        ),
                        metadata={
                            "through_parent": (
                                parent
                            )
                        },
                    )
                )

        relative_parents = (
            self.graph.parents(
                relative,
                active_only=active_only,
                domain=domain,
            )
        )

        subject_siblings = {
            determination.relative
            for determination
            in self.sibling_determinations(
                subject,
                active_only=active_only,
                domain=domain,
            )
        }

        through_siblings = sorted(
            subject_siblings.intersection(
                relative_parents
            )
        )

        if through_siblings:
            results.append(
                KindredDetermination(
                    subject=subject,
                    relative=relative,
                    relationship=(
                        "niece_or_nephew"
                    ),
                    generation_offset=1,
                    confidence=1.0,
                    rule=(
                        "child_of_subject_"
                        "sibling"
                    ),
                    operational_meaning=(
                        self.registry.meaning(
                            "niece_or_nephew"
                        )
                    ),
                    metadata={
                        "through_siblings": (
                            through_siblings
                        )
                    },
                )
            )

        subject_ancestors = (
            self.ancestor_paths(
                subject,
                max_depth=max_depth,
                active_only=active_only,
                domain=domain,
            )
        )

        relative_ancestors = (
            self.ancestor_paths(
                relative,
                max_depth=max_depth,
                active_only=active_only,
                domain=domain,
            )
        )

        common_ancestors = sorted(
            set(
                subject_ancestors
            ).intersection(
                relative_ancestors
            )
        )

        cousin_candidates: list[
            tuple[
                int,
                int,
                str,
            ]
        ] = []

        for ancestor in common_ancestors:
            left_depth = len(
                subject_ancestors[
                    ancestor
                ]
            )

            right_depth = len(
                relative_ancestors[
                    ancestor
                ]
            )

            if (
                left_depth >= 2
                and right_depth >= 2
            ):
                cousin_candidates.append(
                    (
                        left_depth,
                        right_depth,
                        ancestor,
                    )
                )

        if cousin_candidates:
            left_depth, right_depth, ancestor = min(
                cousin_candidates,
                key=lambda item: (
                    max(
                        item[0],
                        item[1],
                    ),
                    item[0]
                    + item[1],
                    item[2],
                ),
            )

            degree = min(
                left_depth,
                right_depth,
            ) - 1

            removal = abs(
                left_depth
                - right_depth
            )

            results.append(
                KindredDetermination(
                    subject=subject,
                    relative=relative,
                    relationship="cousin",
                    generation_offset=(
                        right_depth
                        - left_depth
                    ),
                    shared_ancestors=(
                        ancestor,
                    ),
                    domains=tuple(
                        sorted({
                            step.domain
                            for step in (
                                *subject_ancestors[
                                    ancestor
                                ],
                                *relative_ancestors[
                                    ancestor
                                ],
                            )
                        })
                    ),
                    confidence=1.0,
                    rule=(
                        "nearest_common_"
                        "ancestor_cousin_"
                        "formula"
                    ),
                    operational_meaning=(
                        self.registry.meaning(
                            "cousin"
                        )
                    ),
                    metadata={
                        "degree": degree,
                        "removal": removal,
                        "subject_distance": (
                            left_depth
                        ),
                        "relative_distance": (
                            right_depth
                        ),
                    },
                )
            )

        for parent in parent_ids:
            for partner in (
                self.graph.partners(
                    parent,
                    active_only=active_only,
                )
            ):
                if partner == relative:
                    results.append(
                        KindredDetermination(
                            subject=subject,
                            relative=relative,
                            relationship=(
                                "step_parent"
                            ),
                            generation_offset=-1,
                            confidence=1.0,
                            rule=(
                                "alliance_partner_"
                                "of_direct_parent"
                            ),
                            operational_meaning=(
                                self.registry.meaning(
                                    "step_parent"
                                )
                            ),
                            metadata={
                                "through_parent": (
                                    parent
                                )
                            },
                        )
                    )

        for partner in self.graph.partners(
            subject,
            active_only=active_only,
        ):
            partner_relations = (
                self.determine(
                    partner,
                    relative,
                    max_depth=max(
                        1,
                        max_depth
                        - 1,
                    ),
                    active_only=active_only,
                    domain=domain,
                )
                if partner != relative and max_depth > 1
                else []
            )

            if partner_relations:
                alliance_ids = tuple(
                    alliance.id
                    for alliance
                    in self.graph
                    .alliance_contracts(
                        subject,
                        active_only=(
                            active_only
                        ),
                    )
                    if partner
                    in alliance.partners
                )

                results.append(
                    KindredDetermination(
                        subject=subject,
                        relative=relative,
                        relationship="in_law",
                        generation_offset=(
                            partner_relations[
                                0
                            ]
                            .generation_offset
                        ),
                        alliance_ids=(
                            alliance_ids
                        ),
                        confidence=1.0,
                        rule=(
                            "one_alliance_"
                            "crossing_plus_"
                            "lineage"
                        ),
                        operational_meaning=(
                            self.registry.meaning(
                                "in_law"
                            )
                        ),
                        metadata={
                            "through_partner": (
                                partner
                            ),
                            "partner_relationship": (
                                partner_relations[
                                    0
                                ]
                                .relationship
                            ),
                        },
                    )
                )

                break

        deduplicated: dict[
            tuple[
                str,
                int,
                tuple[str, ...],
                tuple[str, ...],
            ],
            KindredDetermination,
        ] = {}

        for result in results:
            signature = (
                result.relationship,
                result.generation_offset,
                result.shared_parents,
                result.shared_ancestors,
            )

            existing = deduplicated.get(
                signature
            )

            if (
                existing is None
                or result.confidence
                > existing.confidence
            ):
                deduplicated[
                    signature
                ] = result

        return sorted(
            deduplicated.values(),
            key=lambda item: (
                abs(
                    item.generation_offset
                ),
                item.relationship,
                item.relative,
                item.deterministic_hash,
            ),
        )

    def family_determinations(
        self,
        identifier: str,
        *,
        max_depth: int = 3,
        active_only: bool = True,
        domain: str | None = None,
        include_extended: bool = True,
    ) -> list[
        KindredDetermination
    ]:
        subject = self.graph.resolve_node_id(
            identifier
        )

        relatives: set[str] = set()

        relatives.update(
            self.ancestor_paths(
                subject,
                max_depth=max_depth,
                active_only=active_only,
                domain=domain,
            )
        )

        relatives.update(
            self.descendant_paths(
                subject,
                max_depth=max_depth,
                active_only=active_only,
                domain=domain,
            )
        )

        relatives.update(
            self.graph.sibling_candidates(
                subject,
                active_only=active_only,
                domain=domain,
            )
        )

        relatives.update(
            self.graph.partners(
                subject,
                active_only=active_only,
            )
        )

        if include_extended:
            direct_parents = (
                self.graph.parents(
                    subject,
                    active_only=active_only,
                    domain=domain,
                )
            )

            for parent in direct_parents:
                relatives.update(
                    determination.relative
                    for determination
                    in self.sibling_determinations(
                        parent,
                        active_only=active_only,
                        domain=domain,
                    )
                )

            direct_siblings = {
                determination.relative
                for determination
                in self.sibling_determinations(
                    subject,
                    active_only=active_only,
                    domain=domain,
                )
            }

            for sibling in direct_siblings:
                relatives.update(
                    self.graph.children(
                        sibling,
                        active_only=active_only,
                        domain=domain,
                    )
                )

            subject_ancestors = (
                self.ancestor_paths(
                    subject,
                    max_depth=max_depth,
                    active_only=active_only,
                    domain=domain,
                )
            )

            for candidate in self.graph.nodes:
                if candidate == subject:
                    continue

                candidate_ancestors = (
                    self.ancestor_paths(
                        candidate,
                        max_depth=max_depth,
                        active_only=active_only,
                        domain=domain,
                    )
                )

                if set(
                    subject_ancestors
                ).intersection(
                    candidate_ancestors
                ):
                    relatives.add(
                        candidate
                    )

        results: list[
            KindredDetermination
        ] = []

        for relative in sorted(
            relatives
        ):
            results.extend(
                self.determine(
                    subject,
                    relative,
                    max_depth=max_depth,
                    active_only=active_only,
                    domain=domain,
                )
            )

        return sorted(
            results,
            key=lambda item: (
                item.generation_offset,
                item.relationship,
                item.relative,
                item.deterministic_hash,
            ),
        )


__all__ = [
    "KindredAlgebra",
]
