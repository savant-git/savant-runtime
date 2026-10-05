#!/usr/bin/env python3

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping

import yaml


ROOT = Path("/root/savant-runtime")

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from lexicon.kindred.relationship_resolver import (
    KindredRelationshipResolutionError,
    KindredRelationshipResolver,
)


KINDRED_ROOT = Path(__file__).resolve().parent
DEFAULT_REGISTRY = (
    KINDRED_ROOT
    / "discipline_registry.yaml"
)


class DisciplineError(Exception):
    pass


def _stable_json(
    value: Any,
) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )


def _stable_id(
    prefix: str,
    payload: Mapping[str, Any],
) -> str:
    digest = hashlib.sha256(
        _stable_json(
            dict(payload)
        ).encode("utf-8")
    ).hexdigest()

    return (
        f"{prefix}:"
        f"{digest[:24]}"
    )


@dataclass(
    frozen=True,
    slots=True,
)
class KindredEdge:
    subject: str
    relation: str
    object: str
    basis: str
    authority_state: str = "projected"
    valid_from: str | None = None
    valid_until: str | None = None
    provenance: Mapping[str, Any] | None = None
    metadata: Mapping[str, Any] | None = None
    id: str | None = None

    def to_dict(
        self,
    ) -> dict[str, Any]:
        payload = {
            "subject": self.subject,
            "relation": self.relation,
            "object": self.object,
            "basis": self.basis,
            "authority_state": (
                self.authority_state
            ),
            "valid_from": self.valid_from,
            "valid_until": (
                self.valid_until
            ),
            "provenance": dict(
                self.provenance or {}
            ),
            "metadata": dict(
                self.metadata or {}
            ),
        }

        payload["id"] = (
            self.id
            or _stable_id(
                "kindred-edge",
                {
                    "subject": (
                        self.subject
                    ),
                    "relation": (
                        self.relation
                    ),
                    "object": (
                        self.object
                    ),
                    "basis": (
                        self.basis
                    ),
                    "valid_from": (
                        self.valid_from
                    ),
                    "valid_until": (
                        self.valid_until
                    ),
                },
            )
        )

        return payload


class DisciplineEngine:
    def __init__(
        self,
        registry_path: (
            Path | str
        ) = DEFAULT_REGISTRY,
    ) -> None:
        self.registry_path = Path(
            registry_path
        ).expanduser().resolve()

        self.data = self._load_yaml(
            self.registry_path
        )

        self.disciplines: dict[
            str,
            dict[str, Any],
        ] = {}

        self.relations: dict[
            str,
            dict[str, Any],
        ] = {}

        self.relationships = (
            KindredRelationshipResolver(
                discipline_registry=(
                    self.registry_path
                )
            )
        )

        self._build_indexes()
        self._validate_registry()

    @staticmethod
    def _load_yaml(
        path: Path,
    ) -> dict[str, Any]:
        if not path.exists():
            raise DisciplineError(
                f"Registry not found: {path}"
            )

        with path.open(
            "r",
            encoding="utf-8",
        ) as handle:
            data = yaml.safe_load(
                handle
            )

        if not isinstance(
            data,
            dict,
        ):
            raise DisciplineError(
                "Discipline registry root "
                "must be an object."
            )

        return data

    def _build_indexes(
        self,
    ) -> None:
        raw_disciplines = (
            self.data.get(
                "disciplines",
                [],
            )
        )

        raw_relations = (
            self.data.get(
                "relations",
                {},
            )
        )

        if not isinstance(
            raw_disciplines,
            list,
        ):
            raise DisciplineError(
                "disciplines must be a list"
            )

        if not isinstance(
            raw_relations,
            dict,
        ):
            raise DisciplineError(
                "relations must be an object"
            )

        for record in raw_disciplines:
            if not isinstance(
                record,
                dict,
            ):
                raise DisciplineError(
                    "discipline record "
                    "must be an object"
                )

            discipline_id = str(
                record.get(
                    "id",
                    "",
                )
            ).strip()

            if not discipline_id:
                raise DisciplineError(
                    "discipline id is required"
                )

            if discipline_id in (
                self.disciplines
            ):
                raise DisciplineError(
                    "duplicate discipline: "
                    f"{discipline_id}"
                )

            self.disciplines[
                discipline_id
            ] = record

        for (
            relation_id,
            record,
        ) in raw_relations.items():
            if not isinstance(
                record,
                dict,
            ):
                raise DisciplineError(
                    "relation definition "
                    "must be an object: "
                    f"{relation_id}"
                )

            relation_id = str(
                relation_id
            ).strip()

            if relation_id in (
                self.relations
            ):
                raise DisciplineError(
                    "duplicate relation: "
                    f"{relation_id}"
                )

            self.relations[
                relation_id
            ] = record

    def _validate_registry(
        self,
    ) -> None:
        if len(
            self.disciplines
        ) != 18:
            raise DisciplineError(
                "exactly 18 disciplines "
                "required; found "
                f"{len(self.disciplines)}"
            )

        names: set[str] = set()

        for (
            discipline_id,
            record,
        ) in self.disciplines.items():
            canonical = str(
                record.get(
                    "canonical",
                    "",
                )
            ).strip()

            steward = str(
                record.get(
                    "steward",
                    "",
                )
            ).strip()

            if not discipline_id.startswith(
                "discipline:"
            ):
                raise DisciplineError(
                    "invalid discipline id: "
                    f"{discipline_id}"
                )

            if not canonical:
                raise DisciplineError(
                    "canonical name missing: "
                    f"{discipline_id}"
                )

            folded = canonical.casefold()

            if folded in names:
                raise DisciplineError(
                    "duplicate canonical "
                    "discipline name: "
                    f"{canonical}"
                )

            names.add(
                folded
            )

            if not steward:
                raise DisciplineError(
                    "steward missing: "
                    f"{discipline_id}"
                )

            declared = record.get(
                "relations",
                [],
            )

            if not isinstance(
                declared,
                list,
            ):
                raise DisciplineError(
                    "relations must be a list: "
                    f"{discipline_id}"
                )

            for relation_id in declared:
                relation_id = str(
                    relation_id
                )

                definition = (
                    self.relations.get(
                        relation_id
                    )
                )

                if definition is None:
                    raise DisciplineError(
                        "unknown relation "
                        f"{relation_id} in "
                        f"{discipline_id}"
                    )

                if (
                    definition.get(
                        "discipline"
                    )
                    != discipline_id
                ):
                    raise DisciplineError(
                        "relation discipline "
                        "mismatch: "
                        f"{relation_id}"
                    )

        for (
            relation_id,
            record,
        ) in self.relations.items():
            discipline_id = str(
                record.get(
                    "discipline",
                    "",
                )
            ).strip()

            if discipline_id not in (
                self.disciplines
            ):
                raise DisciplineError(
                    "unknown discipline for "
                    f"{relation_id}: "
                    f"{discipline_id}"
                )

            try:
                self.relationships.resolve(
                    relation_id
                )
            except (
                KindredRelationshipResolutionError
            ) as exc:
                raise DisciplineError(
                    str(exc)
                ) from exc

            inverse = record.get(
                "inverse"
            )

            if inverse:
                inverse = str(
                    inverse
                )

                inverse_record = (
                    self.relations.get(
                        inverse
                    )
                )

                if inverse_record is None:
                    raise DisciplineError(
                        "unknown inverse "
                        f"{inverse} for "
                        f"{relation_id}"
                    )

                back = inverse_record.get(
                    "inverse"
                )

                if (
                    back
                    and str(back)
                    != relation_id
                ):
                    raise DisciplineError(
                        "inverse mismatch: "
                        f"{relation_id} "
                        f"<-> {inverse}"
                    )

            directionality = str(
                record.get(
                    "directionality",
                    "directed",
                )
            )

            if directionality not in {
                "directed",
                "symmetric",
            }:
                raise DisciplineError(
                    "invalid directionality "
                    f"for {relation_id}"
                )

            if (
                directionality
                == "symmetric"
                and inverse
                != relation_id
            ):
                raise DisciplineError(
                    "symmetric relation must "
                    "self-invert: "
                    f"{relation_id}"
                )

    def discipline(
        self,
        discipline_id: str,
    ) -> dict[str, Any]:
        try:
            return self.disciplines[
                discipline_id
            ]
        except KeyError as exc:
            raise DisciplineError(
                "unknown discipline: "
                f"{discipline_id}"
            ) from exc

    def relation(
        self,
        relation_id: str,
    ) -> dict[str, Any]:
        try:
            local = self.relations[
                relation_id
            ]
        except KeyError as exc:
            raise DisciplineError(
                "unknown relation: "
                f"{relation_id}"
            ) from exc

        resolved = (
            self.relationships.resolve(
                relation_id
            )
        )

        return {
            **local,
            "relationship_resolution": (
                resolved
            ),
        }

    def validate_edge(
        self,
        edge: KindredEdge,
    ) -> None:
        if not edge.subject.strip():
            raise DisciplineError(
                "edge subject is required"
            )

        if not edge.object.strip():
            raise DisciplineError(
                "edge object is required"
            )

        relation = self.relation(
            edge.relation
        )

        if (
            edge.subject
            == edge.object
            and relation.get(
                "cycle_policy"
            )
            == "forbid"
        ):
            raise DisciplineError(
                "self-edge forbidden for "
                f"{edge.relation}"
            )

        if not edge.basis.strip():
            raise DisciplineError(
                "edge basis is required"
            )

    def normalize_edge(
        self,
        edge: KindredEdge,
    ) -> dict[str, Any]:
        self.validate_edge(
            edge
        )

        payload = edge.to_dict()

        relation = self.relation(
            edge.relation
        )

        discipline_id = str(
            relation["discipline"]
        )

        discipline = self.discipline(
            discipline_id
        )

        resolution = relation[
            "relationship_resolution"
        ]

        payload[
            "discipline"
        ] = discipline_id

        payload[
            "steward"
        ] = discipline[
            "steward"
        ]

        payload[
            "directionality"
        ] = relation.get(
            "directionality",
            "directed",
        )

        payload[
            "inverse"
        ] = relation.get(
            "inverse"
        )

        payload[
            "derived"
        ] = False

        payload[
            "relationship_authority"
        ] = resolution[
            "authority"
        ]

        payload[
            "relationship_authoritative"
        ] = resolution[
            "authoritative"
        ]

        payload[
            "constitutional_relationship"
        ] = resolution[
            "constitutional_id"
        ]

        return payload

    def inverse_edge(
        self,
        edge: KindredEdge,
    ) -> dict[str, Any] | None:
        direct = self.normalize_edge(
            edge
        )

        relation = self.relation(
            edge.relation
        )

        inverse = relation.get(
            "inverse"
        )

        if not inverse:
            return None

        if (
            relation.get(
                "directionality"
            )
            == "symmetric"
            and edge.subject
            == edge.object
        ):
            return None

        inverse_edge = KindredEdge(
            subject=edge.object,
            relation=str(
                inverse
            ),
            object=edge.subject,
            basis=(
                "derived_inverse:"
                f"{direct['id']}"
            ),
            authority_state=(
                "projected"
            ),
            valid_from=(
                edge.valid_from
            ),
            valid_until=(
                edge.valid_until
            ),
            provenance={
                "derived_from": (
                    direct["id"]
                ),
            },
            metadata={
                "projection": (
                    "inverse"
                ),
            },
        )

        payload = self.normalize_edge(
            inverse_edge
        )

        payload["derived"] = True

        payload["derivation"] = {
            "type": "inverse",
            "source_edge": (
                direct["id"]
            ),
        }

        return payload

    def project_edges(
        self,
        edges: Iterable[
            KindredEdge
        ],
        include_inverses: bool = True,
    ) -> list[dict[str, Any]]:
        projected: dict[
            str,
            dict[str, Any],
        ] = {}

        for edge in edges:
            direct = self.normalize_edge(
                edge
            )

            projected[
                direct["id"]
            ] = direct

            if include_inverses:
                inverse = self.inverse_edge(
                    edge
                )

                if inverse is not None:
                    projected.setdefault(
                        inverse["id"],
                        inverse,
                    )

        return [
            projected[key]
            for key in sorted(
                projected
            )
        ]

    def registry_projection(
        self,
    ) -> dict[str, Any]:
        return {
            "registry_id": (
                self.data.get(
                    "registry_id"
                )
            ),
            "version": (
                self.data.get(
                    "version"
                )
            ),
            "discipline_count": len(
                self.disciplines
            ),
            "relation_count": len(
                self.relations
            ),
            "relationship_resolution": (
                self.relationships.projection()
            ),
            "disciplines": [
                self.disciplines[key]
                for key in sorted(
                    self.disciplines
                )
            ],
            "relations": {
                key: self.relation(
                    key
                )
                for key in sorted(
                    self.relations
                )
            },
        }


def _edge_from_mapping(
    record: Mapping[str, Any],
) -> KindredEdge:
    return KindredEdge(
        id=record.get("id"),
        subject=str(
            record.get(
                "subject",
                "",
            )
        ),
        relation=str(
            record.get(
                "relation",
                "",
            )
        ),
        object=str(
            record.get(
                "object",
                "",
            )
        ),
        basis=str(
            record.get(
                "basis",
                "",
            )
        ),
        authority_state=str(
            record.get(
                "authority_state",
                "projected",
            )
        ),
        valid_from=record.get(
            "valid_from"
        ),
        valid_until=record.get(
            "valid_until"
        ),
        provenance=(
            record.get(
                "provenance"
            )
            or {}
        ),
        metadata=(
            record.get(
                "metadata"
            )
            or {}
        ),
    )


def _load_edge_file(
    path: Path,
) -> list[KindredEdge]:
    with path.open(
        "r",
        encoding="utf-8",
    ) as handle:
        data = json.load(
            handle
        )

    if isinstance(
        data,
        dict,
    ):
        data = data.get(
            "edges",
            [],
        )

    if not isinstance(
        data,
        list,
    ):
        raise DisciplineError(
            "edge input must be a list "
            "or {'edges': [...]}"
        )

    return [
        _edge_from_mapping(
            record
        )
        for record in data
        if isinstance(
            record,
            Mapping,
        )
    ]


def _print(
    payload: Any,
) -> None:
    print(
        json.dumps(
            payload,
            indent=2,
            sort_keys=True,
            ensure_ascii=False,
        )
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="kindred-discipline"
    )

    parser.add_argument(
        "--registry",
        default=str(
            DEFAULT_REGISTRY
        ),
    )

    sub = parser.add_subparsers(
        dest="command",
        required=True,
    )

    sub.add_parser(
        "validate"
    )

    sub.add_parser(
        "registry"
    )

    discipline_parser = (
        sub.add_parser(
            "discipline"
        )
    )

    discipline_parser.add_argument(
        "discipline_id"
    )

    relation_parser = (
        sub.add_parser(
            "relation"
        )
    )

    relation_parser.add_argument(
        "relation_id"
    )

    project_parser = (
        sub.add_parser(
            "project"
        )
    )

    project_parser.add_argument(
        "edge_file"
    )

    project_parser.add_argument(
        "--no-inverses",
        action="store_true",
    )

    args = parser.parse_args()

    try:
        engine = DisciplineEngine(
            args.registry
        )

        if args.command == "validate":
            _print(
                {
                    "valid": True,
                    "discipline_count": len(
                        engine.disciplines
                    ),
                    "relation_count": len(
                        engine.relations
                    ),
                    "relationship_resolution": (
                        engine.relationships.projection()
                    ),
                }
            )
            return 0

        if args.command == "registry":
            _print(
                engine.registry_projection()
            )
            return 0

        if args.command == "discipline":
            _print(
                engine.discipline(
                    args.discipline_id
                )
            )
            return 0

        if args.command == "relation":
            _print(
                engine.relation(
                    args.relation_id
                )
            )
            return 0

        if args.command == "project":
            edges = _load_edge_file(
                Path(
                    args.edge_file
                ).expanduser().resolve()
            )

            _print(
                {
                    "edges": (
                        engine.project_edges(
                            edges,
                            include_inverses=(
                                not args.no_inverses
                            ),
                        )
                    )
                }
            )

            return 0

    except (
        DisciplineError,
        KindredRelationshipResolutionError,
        OSError,
        ValueError,
        json.JSONDecodeError,
    ) as exc:
        _print(
            {
                "valid": False,
                "error": str(
                    exc
                ),
            }
        )
        return 1

    return 1


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
