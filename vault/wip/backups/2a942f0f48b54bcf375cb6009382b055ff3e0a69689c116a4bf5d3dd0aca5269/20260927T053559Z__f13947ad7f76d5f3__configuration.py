#!/usr/bin/env python3

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import re
from types import MappingProxyType
from typing import Any, Iterable, Mapping, Sequence


schema = "savant://runtime/sieve/configuration/2.0.0"
recipe_schema = "savant://runtime/sieve/recipe/2.0.0"
selftest_schema = "savant://runtime/sieve/configuration-selftest/2.0.0"

concept_owner = "sieve"
compatibility_owner = "extr"
authority_effect = "none"

utility_hierarchy = (
    "glyph",
    "droplet",
    "stream",
    "flow",
    "current",
    "tide",
    "surge",
    "torrent",
    "sea",
)

utility_level = "current"


class configuration_error(RuntimeError):
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


def stable_id(prefix: str, value: Any) -> str:
    return f"{prefix}:{digest(value)}"


def normalized_id(value: str) -> str:
    result = re.sub(
        r"[^a-z0-9]+",
        "_",
        str(value).strip().lower(),
    ).strip("_")

    if not result:
        raise configuration_error(
            "identifier cannot be empty"
        )

    return result


def normalized_tuple(
    values: Iterable[str],
) -> tuple[str, ...]:
    return tuple(
        dict.fromkeys(
            normalized_id(value)
            for value in values
        )
    )


def frozen_mapping(
    value: Mapping[str, Any] | None,
) -> Mapping[str, Any]:
    return MappingProxyType(
        dict(value or {})
    )


@dataclass(frozen=True, slots=True)
class utility_identity:
    id: str
    level: str
    substance_digest: str
    lineage: tuple[str, ...] = ()
    provenance: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "id",
            normalized_id(self.id),
        )

        if self.level not in utility_hierarchy:
            raise configuration_error(
                f"unknown utility level: {self.level}"
            )

        if not self.substance_digest:
            raise configuration_error(
                "utility identity requires substance digest"
            )

    @property
    def ordinal(self) -> int:
        return utility_hierarchy.index(
            self.level
        )

    def projection(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "level": self.level,
            "ordinal": self.ordinal,
            "substance_digest":
                self.substance_digest,
            "lineage":
                list(self.lineage),
            "provenance":
                list(self.provenance),
        }


@dataclass(frozen=True, slots=True)
class parameter_definition:
    id: str
    kind: str = "string"
    required: bool = False
    default: Any = None
    minimum: float | None = None
    maximum: float | None = None
    choices: tuple[Any, ...] = ()
    pattern: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "id",
            normalized_id(self.id),
        )

        if self.kind not in {
            "string",
            "integer",
            "number",
            "boolean",
            "enum",
        }:
            raise configuration_error(
                f"unsupported parameter kind: {self.kind}"
            )

        if (
            self.minimum is not None
            and self.maximum is not None
            and self.minimum > self.maximum
        ):
            raise configuration_error(
                "parameter minimum exceeds maximum"
            )

        if (
            self.kind == "enum"
            and not self.choices
        ):
            raise configuration_error(
                "enum parameter requires choices"
            )

        if self.pattern is not None:
            re.compile(self.pattern)

        if self.default is not None:
            self.validate(self.default)

    def validate(self, value: Any) -> Any:
        if value is None:
            if self.required:
                raise configuration_error(
                    f"{self.id} is required"
                )
            return value

        if self.kind == "string":
            if not isinstance(value, str):
                raise configuration_error(
                    f"{self.id} requires string"
                )

            if (
                self.pattern is not None
                and re.fullmatch(
                    self.pattern,
                    value,
                )
                is None
            ):
                raise configuration_error(
                    f"{self.id} violates pattern"
                )

        elif self.kind == "integer":
            if (
                not isinstance(value, int)
                or isinstance(value, bool)
            ):
                raise configuration_error(
                    f"{self.id} requires integer"
                )

        elif self.kind == "number":
            if (
                not isinstance(
                    value,
                    (int, float),
                )
                or isinstance(value, bool)
            ):
                raise configuration_error(
                    f"{self.id} requires number"
                )

        elif self.kind == "boolean":
            if not isinstance(value, bool):
                raise configuration_error(
                    f"{self.id} requires boolean"
                )

        elif self.kind == "enum":
            if value not in self.choices:
                raise configuration_error(
                    f"{self.id} requires one of "
                    f"{self.choices}"
                )

        if (
            isinstance(value, (int, float))
            and not isinstance(value, bool)
        ):
            if (
                self.minimum is not None
                and value < self.minimum
            ):
                raise configuration_error(
                    f"{self.id} below minimum"
                )

            if (
                self.maximum is not None
                and value > self.maximum
            ):
                raise configuration_error(
                    f"{self.id} above maximum"
                )

        return value

    def projection(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "kind": self.kind,
            "required": self.required,
            "default": self.default,
            "minimum": self.minimum,
            "maximum": self.maximum,
            "choices": list(self.choices),
            "pattern": self.pattern,
        }


@dataclass(frozen=True, slots=True)
class option:
    id: str
    label: str
    parameters: tuple[
        parameter_definition,
        ...,
    ] = ()
    metadata: Mapping[str, Any] | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "id",
            normalized_id(self.id),
        )

        if not self.label.strip():
            raise configuration_error(
                "option label cannot be empty"
            )

        parameter_ids = [
            parameter.id
            for parameter in self.parameters
        ]

        if len(parameter_ids) != len(
            set(parameter_ids)
        ):
            raise configuration_error(
                "duplicate option parameter"
            )

        object.__setattr__(
            self,
            "metadata",
            frozen_mapping(self.metadata),
        )

    def projection(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "label": self.label,
            "parameters": [
                parameter.projection()
                for parameter in self.parameters
            ],
            "metadata":
                dict(self.metadata),
        }


@dataclass(frozen=True, slots=True)
class column:
    id: str
    label: str
    ordinal: int
    options: tuple[option, ...]
    selection_mode: str = "single"
    minimum_selections: int = 0
    maximum_selections: int | None = 1

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "id",
            normalized_id(self.id),
        )

        if self.ordinal < 0:
            raise configuration_error(
                "column ordinal cannot be negative"
            )

        if not self.label.strip():
            raise configuration_error(
                "column label cannot be empty"
            )

        if self.selection_mode not in {
            "single",
            "multiple",
        }:
            raise configuration_error(
                "selection mode must be single or multiple"
            )

        if self.minimum_selections < 0:
            raise configuration_error(
                "minimum selections cannot be negative"
            )

        if (
            self.maximum_selections is not None
            and self.maximum_selections
            < self.minimum_selections
        ):
            raise configuration_error(
                "maximum selections below minimum"
            )

        if (
            self.selection_mode == "single"
            and self.maximum_selections
            not in {None, 1}
        ):
            raise configuration_error(
                "single-selection maximum must be one"
            )

        option_ids = [
            item.id
            for item in self.options
        ]

        if len(option_ids) != len(
            set(option_ids)
        ):
            raise configuration_error(
                "duplicate option id"
            )

    def option_map(
        self,
    ) -> Mapping[str, option]:
        return MappingProxyType(
            {
                item.id: item
                for item in self.options
            }
        )

    def projection(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "label": self.label,
            "ordinal": self.ordinal,
            "selection_mode":
                self.selection_mode,
            "minimum_selections":
                self.minimum_selections,
            "maximum_selections":
                self.maximum_selections,
            "options": [
                item.projection()
                for item in self.options
            ],
        }


@dataclass(frozen=True, slots=True)
class constraint:
    source_column: str
    source_option: str
    relation: str
    target_column: str
    target_options: tuple[str, ...]

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "source_column",
            normalized_id(
                self.source_column
            ),
        )
        object.__setattr__(
            self,
            "source_option",
            normalized_id(
                self.source_option
            ),
        )
        object.__setattr__(
            self,
            "target_column",
            normalized_id(
                self.target_column
            ),
        )
        object.__setattr__(
            self,
            "target_options",
            normalized_tuple(
                self.target_options
            ),
        )

        if self.relation not in {
            "allow",
            "exclude",
            "require",
        }:
            raise configuration_error(
                "constraint relation must be "
                "allow, exclude, or require"
            )

        if not self.target_options:
            raise configuration_error(
                "constraint requires target options"
            )

    def projection(self) -> dict[str, Any]:
        return {
            "source_column":
                self.source_column,
            "source_option":
                self.source_option,
            "relation":
                self.relation,
            "target_column":
                self.target_column,
            "target_options":
                list(self.target_options),
        }


@dataclass(frozen=True, slots=True)
class selection:
    column_id: str
    option_ids: tuple[str, ...]
    parameters: Mapping[
        str,
        Mapping[str, Any],
    ] | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "column_id",
            normalized_id(
                self.column_id
            ),
        )

        object.__setattr__(
            self,
            "option_ids",
            normalized_tuple(
                self.option_ids
            ),
        )

        projected = {}

        for (
            option_id,
            values,
        ) in (
            self.parameters
            or {}
        ).items():
            projected[
                normalized_id(option_id)
            ] = MappingProxyType(
                dict(values)
            )

        object.__setattr__(
            self,
            "parameters",
            MappingProxyType(projected),
        )

    def projection(self) -> dict[str, Any]:
        return {
            "column_id":
                self.column_id,
            "option_ids":
                list(self.option_ids),
            "parameters": {
                option_id:
                    dict(values)
                for (
                    option_id,
                    values,
                ) in self.parameters.items()
            },
        }


@dataclass(frozen=True, slots=True)
class recipe:
    selections: tuple[selection, ...]
    definition_digest: str
    lineage: tuple[str, ...] = ()
    provenance: tuple[str, ...] = ()

    def projection(self) -> dict[str, Any]:
        body = {
            "schema":
                recipe_schema,
            "definition_digest":
                self.definition_digest,
            "selections": [
                item.projection()
                for item in self.selections
            ],
            "lineage":
                list(self.lineage),
            "provenance":
                list(self.provenance),
            "authority_effect":
                "none",
            "authoritative":
                False,
            "rebuildable":
                True,
        }

        body["recipe_digest"] = digest(
            body
        )

        return body


class configuration_current:
    def __init__(
        self,
        columns: Sequence[column],
        constraints: Sequence[
            constraint
        ] = (),
    ) -> None:
        ordered = tuple(
            sorted(
                columns,
                key=lambda item: (
                    item.ordinal,
                    item.id,
                ),
            )
        )

        if not ordered:
            raise configuration_error(
                "configuration requires at least one column"
            )

        column_ids = [
            item.id
            for item in ordered
        ]

        if len(column_ids) != len(
            set(column_ids)
        ):
            raise configuration_error(
                "duplicate column id"
            )

        ordinals = [
            item.ordinal
            for item in ordered
        ]

        if len(ordinals) != len(
            set(ordinals)
        ):
            raise configuration_error(
                "duplicate column ordinal"
            )

        self._columns = ordered
        self._column_map = MappingProxyType(
            {
                item.id: item
                for item in ordered
            }
        )
        self._constraints = tuple(
            constraints
        )

        self._validate_constraints()

        substance = {
            "columns": [
                item.projection()
                for item in self._columns
            ],
            "constraints": [
                item.projection()
                for item in self._constraints
            ],
        }

        self._definition_digest = digest(
            substance
        )

        self._utility_identity = (
            utility_identity(
                id="configuration",
                level="current",
                substance_digest=
                    self._definition_digest,
                provenance=(
                    "accepted-user-authority:"
                    "utility-hierarchy",
                ),
            )
        )

    @property
    def columns(
        self,
    ) -> tuple[column, ...]:
        return self._columns

    @property
    def constraints(
        self,
    ) -> tuple[constraint, ...]:
        return self._constraints

    @property
    def definition_digest(
        self,
    ) -> str:
        return self._definition_digest

    @property
    def utility(
        self,
    ) -> utility_identity:
        return self._utility_identity

    def _validate_constraints(
        self,
    ) -> None:
        for rule in self._constraints:
            if (
                rule.source_column
                not in self._column_map
            ):
                raise configuration_error(
                    "constraint source column does not exist"
                )

            if (
                rule.target_column
                not in self._column_map
            ):
                raise configuration_error(
                    "constraint target column does not exist"
                )

            source = self._column_map[
                rule.source_column
            ]
            target = self._column_map[
                rule.target_column
            ]

            if (
                rule.source_option
                not in source.option_map()
            ):
                raise configuration_error(
                    "constraint source option does not exist"
                )

            missing = (
                set(rule.target_options)
                - set(
                    target.option_map()
                )
            )

            if missing:
                raise configuration_error(
                    "constraint target option does not exist: "
                    + ", ".join(
                        sorted(missing)
                    )
                )

            if (
                target.ordinal
                <= source.ordinal
            ):
                raise configuration_error(
                    "constraints must project forward"
                )

    def projection(self) -> dict[str, Any]:
        return {
            "schema":
                schema,
            "concept_owner":
                concept_owner,
            "compatibility_owner":
                compatibility_owner,
            "authority_effect":
                authority_effect,
            "authoritative":
                False,
            "utility_hierarchy":
                list(utility_hierarchy),
            "utility":
                self.utility.projection(),
            "definition_digest":
                self.definition_digest,
            "columns": [
                item.projection()
                for item in self._columns
            ],
            "constraints": [
                item.projection()
                for item in self._constraints
            ],
        }

    def _selection_map(
        self,
        selections: Sequence[
            selection
        ],
    ) -> Mapping[str, selection]:
        result = {}

        for item in selections:
            if item.column_id in result:
                raise configuration_error(
                    "column selected more than once"
                )

            if (
                item.column_id
                not in self._column_map
            ):
                raise configuration_error(
                    f"unknown selected column: "
                    f"{item.column_id}"
                )

            result[
                item.column_id
            ] = item

        return MappingProxyType(
            result
        )

    def allowed_options(
        self,
        column_id: str,
        selections: Sequence[
            selection
        ],
    ) -> tuple[str, ...]:
        column_id = normalized_id(
            column_id
        )

        if (
            column_id
            not in self._column_map
        ):
            raise configuration_error(
                "unknown column"
            )

        target = self._column_map[
            column_id
        ]

        allowed = set(
            target.option_map()
        )

        selected = self._selection_map(
            selections
        )

        allow_sets = []
        excluded = set()

        for rule in self._constraints:
            if (
                rule.target_column
                != column_id
            ):
                continue

            source_selection = (
                selected.get(
                    rule.source_column
                )
            )

            if (
                source_selection is None
                or rule.source_option
                not in
                source_selection.option_ids
            ):
                continue

            targets = set(
                rule.target_options
            )

            if rule.relation == "allow":
                allow_sets.append(
                    targets
                )

            elif (
                rule.relation
                == "exclude"
            ):
                excluded.update(
                    targets
                )

        for allowed_set in allow_sets:
            allowed.intersection_update(
                allowed_set
            )

        allowed.difference_update(
            excluded
        )

        return tuple(
            option_id
            for option_id
            in target.option_map()
            if option_id in allowed
        )

    def required_options(
        self,
        column_id: str,
        selections: Sequence[
            selection
        ],
    ) -> tuple[str, ...]:
        column_id = normalized_id(
            column_id
        )

        selected = self._selection_map(
            selections
        )

        required = set()

        for rule in self._constraints:
            if (
                rule.target_column
                != column_id
                or rule.relation
                != "require"
            ):
                continue

            source_selection = (
                selected.get(
                    rule.source_column
                )
            )

            if (
                source_selection is not None
                and rule.source_option
                in
                source_selection.option_ids
            ):
                required.update(
                    rule.target_options
                )

        return tuple(
            sorted(required)
        )

    def validate_selection(
        self,
        item: selection,
        prior: Sequence[
            selection
        ],
    ) -> None:
        target = self._column_map[
            item.column_id
        ]

        allowed = set(
            self.allowed_options(
                item.column_id,
                prior,
            )
        )

        selected = set(
            item.option_ids
        )

        unknown = (
            selected
            - set(
                target.option_map()
            )
        )

        if unknown:
            raise configuration_error(
                "unknown options: "
                + ", ".join(
                    sorted(unknown)
                )
            )

        incompatible = (
            selected
            - allowed
        )

        if incompatible:
            raise configuration_error(
                "incompatible options: "
                + ", ".join(
                    sorted(incompatible)
                )
            )

        if (
            target.selection_mode
            == "single"
            and len(selected) > 1
        ):
            raise configuration_error(
                "single-selection column received multiple options"
            )

        if (
            len(selected)
            < target.minimum_selections
        ):
            raise configuration_error(
                "selection below minimum"
            )

        if (
            target.maximum_selections
            is not None
            and len(selected)
            > target.maximum_selections
        ):
            raise configuration_error(
                "selection above maximum"
            )

        required = set(
            self.required_options(
                item.column_id,
                prior,
            )
        )

        missing_required = (
            required
            - selected
        )

        if missing_required:
            raise configuration_error(
                "required options missing: "
                + ", ".join(
                    sorted(
                        missing_required
                    )
                )
            )

        option_map = (
            target.option_map()
        )

        for option_id in item.option_ids:
            selected_option = (
                option_map[
                    option_id
                ]
            )

            values = dict(
                item.parameters.get(
                    option_id,
                    {},
                )
            )

            parameter_map = {
                parameter.id:
                    parameter
                for parameter
                in selected_option.parameters
            }

            unknown_parameters = (
                set(values)
                - set(parameter_map)
            )

            if unknown_parameters:
                raise configuration_error(
                    "unknown parameters for "
                    f"{option_id}: "
                    + ", ".join(
                        sorted(
                            unknown_parameters
                        )
                    )
                )

            for (
                parameter_id,
                parameter,
            ) in parameter_map.items():
                if parameter_id in values:
                    parameter.validate(
                        values[
                            parameter_id
                        ]
                    )

                elif (
                    parameter.required
                    and parameter.default
                    is None
                ):
                    raise configuration_error(
                        "required parameter missing: "
                        f"{parameter_id}"
                    )

    def validate(
        self,
        selections: Sequence[
            selection
        ],
        complete: bool = False,
    ) -> tuple[selection, ...]:
        selection_map = (
            self._selection_map(
                selections
            )
        )

        ordered = []

        for target in self._columns:
            item = selection_map.get(
                target.id
            )

            if item is None:
                if (
                    complete
                    and target.minimum_selections
                    > 0
                ):
                    raise configuration_error(
                        "required column missing: "
                        f"{target.id}"
                    )

                continue

            self.validate_selection(
                item,
                ordered,
            )

            ordered.append(item)

        return tuple(ordered)

    def next_column(
        self,
        selections: Sequence[
            selection
        ],
    ) -> dict[str, Any] | None:
        validated = self.validate(
            selections,
            complete=False,
        )

        selected_ids = {
            item.column_id
            for item in validated
        }

        for target in self._columns:
            if target.id in selected_ids:
                continue

            allowed = (
                self.allowed_options(
                    target.id,
                    validated,
                )
            )

            required = (
                self.required_options(
                    target.id,
                    validated,
                )
            )

            if (
                not allowed
                and target.minimum_selections
                == 0
            ):
                continue

            return {
                "column":
                    target.projection(),
                "allowed_options":
                    list(allowed),
                "required_options":
                    list(required),
                "state_digest":
                    digest(
                        [
                            item.projection()
                            for item
                            in validated
                        ]
                    ),
                "utility_level":
                    "current",
            }

        return None

    def explain(
        self,
        column_id: str,
        option_id: str,
        selections: Sequence[
            selection
        ],
    ) -> dict[str, Any]:
        column_id = normalized_id(
            column_id
        )
        option_id = normalized_id(
            option_id
        )

        allowed = set(
            self.allowed_options(
                column_id,
                selections,
            )
        )

        selected = self._selection_map(
            selections
        )

        reasons = []

        for rule in self._constraints:
            if (
                rule.target_column
                != column_id
                or option_id
                not in
                rule.target_options
            ):
                continue

            source = selected.get(
                rule.source_column
            )

            active = (
                source is not None
                and rule.source_option
                in source.option_ids
            )

            reasons.append(
                {
                    "relation":
                        rule.relation,
                    "source_column":
                        rule.source_column,
                    "source_option":
                        rule.source_option,
                    "active":
                        active,
                }
            )

        return {
            "column_id":
                column_id,
            "option_id":
                option_id,
            "allowed":
                option_id in allowed,
            "reasons":
                reasons,
        }

    def build_recipe(
        self,
        selections: Sequence[
            selection
        ],
        lineage: Sequence[str] = (),
        provenance: Sequence[str] = (),
    ) -> recipe:
        validated = self.validate(
            selections,
            complete=True,
        )

        return recipe(
            selections=validated,
            definition_digest=
                self.definition_digest,
            lineage=tuple(lineage),
            provenance=tuple(
                provenance
            ),
        )


configuration = configuration_current


def from_mapping(
    value: Mapping[str, Any],
) -> configuration_current:
    raw_columns = value.get(
        "columns"
    )

    if not isinstance(
        raw_columns,
        list,
    ):
        raise configuration_error(
            "configuration requires columns array"
        )

    columns = []

    for raw_column in raw_columns:
        if not isinstance(
            raw_column,
            Mapping,
        ):
            raise configuration_error(
                "column must be object"
            )

        options = []

        for raw_option in (
            raw_column.get(
                "options",
                [],
            )
        ):
            if not isinstance(
                raw_option,
                Mapping,
            ):
                raise configuration_error(
                    "option must be object"
                )

            parameters = []

            for raw_parameter in (
                raw_option.get(
                    "parameters",
                    [],
                )
            ):
                parameters.append(
                    parameter_definition(
                        id=
                            raw_parameter[
                                "id"
                            ],
                        kind=
                            raw_parameter.get(
                                "kind",
                                "string",
                            ),
                        required=
                            bool(
                                raw_parameter.get(
                                    "required",
                                    False,
                                )
                            ),
                        default=
                            raw_parameter.get(
                                "default"
                            ),
                        minimum=
                            raw_parameter.get(
                                "minimum"
                            ),
                        maximum=
                            raw_parameter.get(
                                "maximum"
                            ),
                        choices=
                            tuple(
                                raw_parameter.get(
                                    "choices",
                                    [],
                                )
                            ),
                        pattern=
                            raw_parameter.get(
                                "pattern"
                            ),
                    )
                )

            options.append(
                option(
                    id=
                        raw_option["id"],
                    label=
                        raw_option.get(
                            "label",
                            raw_option["id"],
                        ),
                    parameters=
                        tuple(parameters),
                    metadata=
                        raw_option.get(
                            "metadata",
                            {},
                        ),
                )
            )

        maximum = raw_column.get(
            "maximum_selections",
            1,
        )

        if maximum is not None:
            maximum = int(maximum)

        columns.append(
            column(
                id=
                    raw_column["id"],
                label=
                    raw_column.get(
                        "label",
                        raw_column["id"],
                    ),
                ordinal=
                    int(
                        raw_column[
                            "ordinal"
                        ]
                    ),
                options=
                    tuple(options),
                selection_mode=
                    raw_column.get(
                        "selection_mode",
                        "single",
                    ),
                minimum_selections=
                    int(
                        raw_column.get(
                            "minimum_selections",
                            0,
                        )
                    ),
                maximum_selections=
                    maximum,
            )
        )

    constraints = []

    for raw_constraint in value.get(
        "constraints",
        [],
    ):
        constraints.append(
            constraint(
                source_column=
                    raw_constraint[
                        "source_column"
                    ],
                source_option=
                    raw_constraint[
                        "source_option"
                    ],
                relation=
                    raw_constraint[
                        "relation"
                    ],
                target_column=
                    raw_constraint[
                        "target_column"
                    ],
                target_options=
                    tuple(
                        raw_constraint[
                            "target_options"
                        ]
                    ),
            )
        )

    return configuration_current(
        columns=tuple(columns),
        constraints=
            tuple(constraints),
    )


def selftest() -> dict[str, Any]:
    definition = {
        "columns": [
            {
                "id": "action",
                "label": "action",
                "ordinal": 0,
                "minimum_selections": 1,
                "options": [
                    {
                        "id": "audit",
                        "label": "audit",
                    },
                    {
                        "id": "extract",
                        "label": "extract",
                    },
                ],
            },
            {
                "id": "target",
                "label": "target",
                "ordinal": 1,
                "minimum_selections": 1,
                "options": [
                    {
                        "id": "concept",
                        "label": "concept",
                    },
                    {
                        "id": "code",
                        "label": "code",
                    },
                    {
                        "id": "text",
                        "label": "text",
                    },
                ],
            },
            {
                "id": "depth",
                "label": "depth",
                "ordinal": 2,
                "minimum_selections": 1,
                "options": [
                    {
                        "id": "normal",
                        "label": "normal",
                    },
                    {
                        "id": "exhaustive",
                        "label": "exhaustive",
                        "parameters": [
                            {
                                "id":
                                    "minimum_confidence",
                                "kind":
                                    "number",
                                "minimum":
                                    0.0,
                                "maximum":
                                    1.0,
                                "default":
                                    0.8,
                            }
                        ],
                    },
                ],
            },
        ],
        "constraints": [
            {
                "source_column":
                    "action",
                "source_option":
                    "audit",
                "relation":
                    "allow",
                "target_column":
                    "target",
                "target_options": [
                    "concept",
                    "code",
                ],
            },
            {
                "source_column":
                    "action",
                "source_option":
                    "extract",
                "relation":
                    "exclude",
                "target_column":
                    "target",
                "target_options": [
                    "concept",
                ],
            },
            {
                "source_column":
                    "target",
                "source_option":
                    "concept",
                "relation":
                    "require",
                "target_column":
                    "depth",
                "target_options": [
                    "exhaustive",
                ],
            },
        ],
    }

    first = from_mapping(
        definition
    )

    second = from_mapping(
        definition
    )

    audit = selection(
        column_id="action",
        option_ids=("audit",),
    )

    target = selection(
        column_id="target",
        option_ids=("concept",),
    )

    depth = selection(
        column_id="depth",
        option_ids=("exhaustive",),
        parameters={
            "exhaustive": {
                "minimum_confidence":
                    0.9,
            }
        },
    )

    next_after_audit = (
        first.next_column(
            (audit,)
        )
    )

    next_after_target = (
        first.next_column(
            (
                audit,
                target,
            )
        )
    )

    recipe_one = (
        first.build_recipe(
            (
                audit,
                target,
                depth,
            ),
            provenance=(
                "selftest",
            ),
        )
    )

    recipe_two = (
        first.build_recipe(
            (
                audit,
                target,
                depth,
            ),
            provenance=(
                "selftest",
            ),
        )
    )

    invalid_rejected = False

    try:
        first.build_recipe(
            (
                audit,
                target,
                selection(
                    column_id="depth",
                    option_ids=(
                        "normal",
                    ),
                ),
            )
        )

    except configuration_error:
        invalid_rejected = True

    checks = {
        "authority_none":
            authority_effect
            == "none",
        "utility_hierarchy_exact":
            utility_hierarchy
            == (
                "glyph",
                "droplet",
                "stream",
                "flow",
                "current",
                "tide",
                "surge",
                "torrent",
                "sea",
            ),
        "configuration_is_current":
            first.utility.level
            == "current",
        "utility_ordinal":
            first.utility.ordinal
            == 4,
        "definition_deterministic":
            first.definition_digest
            == second.definition_digest,
        "audit_projection":
            next_after_audit[
                "allowed_options"
            ]
            == [
                "concept",
                "code",
            ],
        "require_projection":
            next_after_target[
                "required_options"
            ]
            == [
                "exhaustive",
            ],
        "invalid_combination_rejected":
            invalid_rejected,
        "recipe_deterministic":
            recipe_one.projection()[
                "recipe_digest"
            ]
            == recipe_two.projection()[
                "recipe_digest"
            ],
        "recipe_rebuildable":
            recipe_one.projection()[
                "rebuildable"
            ]
            is True,
        "recipe_non_authoritative":
            recipe_one.projection()[
                "authoritative"
            ]
            is False,
        "parameter_validated":
            recipe_one.selections[
                2
            ].parameters[
                "exhaustive"
            ][
                "minimum_confidence"
            ]
            == 0.9,
        "explanation_available":
            first.explain(
                "target",
                "concept",
                (audit,),
            )[
                "allowed"
            ]
            is True,
        "compatibility_alias":
            configuration
            is configuration_current,
        "current_projection":
            first.projection()[
                "utility"
            ][
                "level"
            ]
            == "current",
    }

    return {
        "schema":
            selftest_schema,
        "ok":
            all(
                checks.values()
            ),
        "checks":
            checks,
        "definition_digest":
            first.definition_digest,
        "recipe_digest":
            recipe_one.projection()[
                "recipe_digest"
            ],
    }


def main() -> int:
    result = selftest()

    print(
        json.dumps(
            result,
            ensure_ascii=False,
            sort_keys=True,
            indent=2,
        )
    )

    return (
        0
        if result["ok"]
        else 1
    )


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
