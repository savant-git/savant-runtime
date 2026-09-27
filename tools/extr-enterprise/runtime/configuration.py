#!/usr/bin/env python3

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import json
from typing import Any, Mapping, Sequence

from utility_edifice import (
    accepted_decision as utility_accepted_decision,
    edifice_projection as utility_edifice_projection,
    levels as utility_edifice,
)


schema = "savant://runtime/sieve/configuration/3.0.0"
recipe_schema = "savant://runtime/sieve/recipe/3.0.0"
selftest_schema = (
    "savant://runtime/sieve/configuration-selftest/3.0.0"
)

concept_owner = "sieve"
compatibility_owner = "extr"
authority_effect = "none"

# The lost verified implementation classified configuration at the
# superseded utility level "current". Current authority explicitly
# forbids translating that classification by ordinal position.
#
# None therefore means "not yet semantically reclassified", not
# "outside the utility edifice".
utility_level: str | None = None
superseded_utility_level = "current"


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


def normalized_values(
    values: Sequence[str],
) -> tuple[str, ...]:
    return tuple(
        dict.fromkeys(
            str(value)
            for value in values
        )
    )


def require_identifier(
    value: Any,
    *,
    field_name: str,
) -> str:
    candidate = str(value or "").strip()

    if not candidate:
        raise configuration_error(
            f"{field_name} cannot be empty"
        )

    return candidate


@dataclass(frozen=True, slots=True)
class utility_identity:
    level: str | None = utility_level
    superseded_level: str | None = (
        superseded_utility_level
    )

    @property
    def current(self) -> bool:
        return (
            self.level is not None
            and self.level in utility_edifice
        )

    @property
    def ordinal(self) -> int | None:
        if not self.current:
            return None

        return utility_edifice.index(
            self.level
        )

    def projection(self) -> dict[str, Any]:
        return {
            "accepted_decision":
                utility_accepted_decision,
            "current":
                self.current,
            "level":
                self.level,
            "ordinal":
                self.ordinal,
            "superseded_level":
                self.superseded_level,
            "semantic_reclassification_required":
                not self.current,
        }


@dataclass(frozen=True, slots=True)
class parameter_definition:
    id: str
    type: str = "string"
    required: bool = False
    default: Any = None
    choices: tuple[Any, ...] = ()

    def __post_init__(self) -> None:
        require_identifier(
            self.id,
            field_name="parameter id",
        )

        if self.type not in {
            "string",
            "integer",
            "number",
            "boolean",
            "array",
            "object",
        }:
            raise configuration_error(
                f"unsupported parameter type: {self.type}"
            )

        if self.choices:
            for value in self.choices:
                self.validate(value)

        if self.default is not None:
            self.validate(self.default)

    def validate(self, value: Any) -> Any:
        if value is None:
            if self.required:
                raise configuration_error(
                    f"parameter {self.id} is required"
                )

            return value

        valid = False

        if self.type == "string":
            valid = isinstance(value, str)

        elif self.type == "integer":
            valid = (
                isinstance(value, int)
                and not isinstance(value, bool)
            )

        elif self.type == "number":
            valid = (
                isinstance(value, (int, float))
                and not isinstance(value, bool)
            )

        elif self.type == "boolean":
            valid = isinstance(value, bool)

        elif self.type == "array":
            valid = isinstance(
                value,
                (list, tuple),
            )

        elif self.type == "object":
            valid = isinstance(value, Mapping)

        if not valid:
            raise configuration_error(
                f"parameter {self.id} requires "
                f"type {self.type}"
            )

        if (
            self.choices
            and value not in self.choices
        ):
            raise configuration_error(
                f"parameter {self.id} must be one of "
                f"{list(self.choices)}"
            )

        return value

    def projection(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "type": self.type,
            "required": self.required,
            "default": self.default,
            "choices": list(self.choices),
        }


@dataclass(frozen=True, slots=True)
class option:
    id: str
    label: str | None = None
    description: str | None = None
    parameters: tuple[
        parameter_definition,
        ...
    ] = ()

    def __post_init__(self) -> None:
        require_identifier(
            self.id,
            field_name="option id",
        )

        parameter_ids = [
            parameter.id
            for parameter in self.parameters
        ]

        if len(parameter_ids) != len(
            set(parameter_ids)
        ):
            raise configuration_error(
                f"duplicate parameter in option {self.id}"
            )

    def parameter(
        self,
        parameter_id: str,
    ) -> parameter_definition:
        for parameter in self.parameters:
            if parameter.id == parameter_id:
                return parameter

        raise configuration_error(
            f"unknown parameter "
            f"{self.id}.{parameter_id}"
        )

    def validate_parameters(
        self,
        values: Mapping[str, Any] | None,
    ) -> dict[str, Any]:
        supplied = dict(values or {})

        known = {
            parameter.id
            for parameter in self.parameters
        }

        unknown = (
            set(supplied)
            - known
        )

        if unknown:
            raise configuration_error(
                f"unknown parameters for {self.id}: "
                f"{sorted(unknown)}"
            )

        result: dict[str, Any] = {}

        for parameter in self.parameters:
            if parameter.id in supplied:
                result[
                    parameter.id
                ] = parameter.validate(
                    supplied[parameter.id]
                )

            elif parameter.default is not None:
                result[
                    parameter.id
                ] = parameter.validate(
                    parameter.default
                )

            elif parameter.required:
                raise configuration_error(
                    f"parameter "
                    f"{self.id}.{parameter.id} "
                    f"is required"
                )

        return result

    def projection(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "label": self.label,
            "description": self.description,
            "parameters": [
                parameter.projection()
                for parameter in self.parameters
            ],
        }


@dataclass(frozen=True, slots=True)
class column:
    id: str
    options: tuple[option, ...]
    selection: str = "single"
    minimum: int = 1
    maximum: int | None = 1
    label: str | None = None
    description: str | None = None

    def __post_init__(self) -> None:
        require_identifier(
            self.id,
            field_name="column id",
        )

        if self.selection not in {
            "single",
            "multiple",
        }:
            raise configuration_error(
                f"invalid selection mode: "
                f"{self.selection}"
            )

        if self.minimum < 0:
            raise configuration_error(
                "column minimum cannot be negative"
            )

        if (
            self.maximum is not None
            and self.maximum < self.minimum
        ):
            raise configuration_error(
                "column maximum cannot be less "
                "than minimum"
            )

        if (
            self.selection == "single"
            and self.maximum not in {
                1,
                None,
            }
        ):
            raise configuration_error(
                "single-selection column maximum "
                "must be 1"
            )

        option_ids = [
            value.id
            for value in self.options
        ]

        if not option_ids:
            raise configuration_error(
                f"column {self.id} requires options"
            )

        if len(option_ids) != len(
            set(option_ids)
        ):
            raise configuration_error(
                f"duplicate option in column {self.id}"
            )

    def option(
        self,
        option_id: str,
    ) -> option:
        for value in self.options:
            if value.id == option_id:
                return value

        raise configuration_error(
            f"unknown option {self.id}.{option_id}"
        )

    def projection(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "label": self.label,
            "description": self.description,
            "selection": self.selection,
            "minimum": self.minimum,
            "maximum": self.maximum,
            "options": [
                value.projection()
                for value in self.options
            ],
        }


@dataclass(frozen=True, slots=True)
class constraint:
    source_column: str
    source_option: str
    target_column: str
    relation: str
    target_options: tuple[str, ...]

    def __post_init__(self) -> None:
        if self.relation not in {
            "allow",
            "exclude",
            "require",
        }:
            raise configuration_error(
                f"invalid constraint relation: "
                f"{self.relation}"
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
            "target_column":
                self.target_column,
            "relation":
                self.relation,
            "target_options":
                list(self.target_options),
        }


@dataclass(frozen=True, slots=True)
class selection:
    column: str
    options: tuple[str, ...]
    parameters: Mapping[
        str,
        Mapping[str, Any],
    ] = field(
        default_factory=dict
    )

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "options",
            normalized_values(
                self.options
            ),
        )

        object.__setattr__(
            self,
            "parameters",
            {
                str(option_id): dict(values)
                for option_id, values
                in self.parameters.items()
            },
        )

    def projection(self) -> dict[str, Any]:
        return {
            "column": self.column,
            "options": list(self.options),
            "parameters": {
                option_id: dict(values)
                for option_id, values
                in sorted(
                    self.parameters.items()
                )
            },
        }


@dataclass(frozen=True, slots=True)
class recipe:
    definition_digest: str
    selections: tuple[selection, ...]
    lineage: Mapping[str, Any]
    provenance: Mapping[str, Any]
    schema: str = recipe_schema
    owner: str = concept_owner
    authority_effect: str = authority_effect
    authoritative: bool = False
    rebuildable: bool = True

    def substance(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "owner": self.owner,
            "authority_effect":
                self.authority_effect,
            "authoritative":
                self.authoritative,
            "rebuildable":
                self.rebuildable,
            "definition_digest":
                self.definition_digest,
            "selections": [
                value.projection()
                for value in self.selections
            ],
            "lineage":
                dict(self.lineage),
            "provenance":
                dict(self.provenance),
        }

    @property
    def recipe_digest(self) -> str:
        return digest(
            self.substance()
        )

    def projection(self) -> dict[str, Any]:
        value = self.substance()

        value[
            "recipe_digest"
        ] = self.recipe_digest

        return value


@dataclass(frozen=True, slots=True)
class configuration_current:
    columns: tuple[column, ...]
    constraints: tuple[
        constraint,
        ...
    ] = ()
    lineage: Mapping[str, Any] = field(
        default_factory=dict
    )
    provenance: Mapping[str, Any] = field(
        default_factory=dict
    )
    schema: str = schema
    owner: str = concept_owner
    compatibility_owner: str = (
        compatibility_owner
    )
    authority_effect: str = authority_effect

    def __post_init__(self) -> None:
        column_ids = [
            value.id
            for value in self.columns
        ]

        if not column_ids:
            raise configuration_error(
                "configuration requires columns"
            )

        if len(column_ids) != len(
            set(column_ids)
        ):
            raise configuration_error(
                "configuration contains "
                "duplicate columns"
            )

        positions = {
            column_id: index
            for index, column_id
            in enumerate(column_ids)
        }

        for rule in self.constraints:
            if (
                rule.source_column
                not in positions
            ):
                raise configuration_error(
                    "constraint references unknown "
                    f"source column "
                    f"{rule.source_column}"
                )

            if (
                rule.target_column
                not in positions
            ):
                raise configuration_error(
                    "constraint references unknown "
                    f"target column "
                    f"{rule.target_column}"
                )

            if (
                positions[
                    rule.target_column
                ]
                <= positions[
                    rule.source_column
                ]
            ):
                raise configuration_error(
                    "constraints must project "
                    "forward"
                )

            source = self.column(
                rule.source_column
            )

            source.option(
                rule.source_option
            )

            target = self.column(
                rule.target_column
            )

            for option_id in (
                rule.target_options
            ):
                target.option(
                    option_id
                )

    @property
    def utility(self) -> utility_identity:
        return utility_identity()

    def column(
        self,
        column_id: str,
    ) -> column:
        for value in self.columns:
            if value.id == column_id:
                return value

        raise configuration_error(
            f"unknown column: {column_id}"
        )

    def definition_substance(
        self,
    ) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "owner": self.owner,
            "compatibility_owner":
                self.compatibility_owner,
            "authority_effect":
                self.authority_effect,
            "utility":
                self.utility.projection(),
            "utility_edifice":
                utility_edifice_projection(),
            "columns": [
                value.projection()
                for value in self.columns
            ],
            "constraints": [
                value.projection()
                for value in self.constraints
            ],
            "lineage":
                dict(self.lineage),
            "provenance":
                dict(self.provenance),
        }

    @property
    def definition_digest(self) -> str:
        return digest(
            self.definition_substance()
        )

    def projection(
        self,
    ) -> dict[str, Any]:
        value = self.definition_substance()

        value[
            "definition_digest"
        ] = self.definition_digest

        return value

    def normalized_selections(
        self,
        values: Sequence[
            selection,
        ],
    ) -> tuple[
        selection,
        ...
    ]:
        by_column: dict[
            str,
            selection,
        ] = {}

        for value in values:
            if value.column in by_column:
                raise configuration_error(
                    f"column selected twice: "
                    f"{value.column}"
                )

            by_column[
                value.column
            ] = value

        normalized: list[
            selection
        ] = []

        for definition in self.columns:
            if definition.id not in by_column:
                continue

            supplied = by_column[
                definition.id
            ]

            option_ids = normalized_values(
                supplied.options
            )

            if (
                len(option_ids)
                < definition.minimum
            ):
                raise configuration_error(
                    f"column {definition.id} "
                    f"requires at least "
                    f"{definition.minimum} option(s)"
                )

            if (
                definition.maximum is not None
                and len(option_ids)
                > definition.maximum
            ):
                raise configuration_error(
                    f"column {definition.id} "
                    f"allows at most "
                    f"{definition.maximum} option(s)"
                )

            if (
                definition.selection
                == "single"
                and len(option_ids) > 1
            ):
                raise configuration_error(
                    f"column {definition.id} "
                    f"is single-selection"
                )

            validated_parameters: dict[
                str,
                Mapping[str, Any],
            ] = {}

            for option_id in option_ids:
                definition.option(
                    option_id
                )

                supplied_parameters = (
                    supplied.parameters.get(
                        option_id,
                        {},
                    )
                )

                validated_parameters[
                    option_id
                ] = (
                    definition.option(
                        option_id
                    ).validate_parameters(
                        supplied_parameters
                    )
                )

            unknown_parameter_options = (
                set(
                    supplied.parameters
                )
                - set(option_ids)
            )

            if unknown_parameter_options:
                raise configuration_error(
                    f"parameters supplied for "
                    f"unselected options in "
                    f"{definition.id}: "
                    f"{sorted(unknown_parameter_options)}"
                )

            normalized.append(
                selection(
                    column=definition.id,
                    options=option_ids,
                    parameters=
                        validated_parameters,
                )
            )

        unknown_columns = (
            set(by_column)
            - {
                value.id
                for value in self.columns
            }
        )

        if unknown_columns:
            raise configuration_error(
                f"unknown selected columns: "
                f"{sorted(unknown_columns)}"
            )

        return tuple(normalized)

    def state(
        self,
        values: Sequence[
            selection,
        ],
    ) -> dict[
        str,
        tuple[str, ...],
    ]:
        normalized = (
            self.normalized_selections(
                values
            )
        )

        return {
            value.column:
                value.options
            for value in normalized
        }

    def option_projection(
        self,
        column_id: str,
        values: Sequence[
            selection,
        ] = (),
    ) -> dict[str, Any]:
        target = self.column(
            column_id
        )

        state = self.state(
            values
        )

        allowed = {
            value.id
            for value in target.options
        }

        required: set[str] = set()

        explanations: list[
            dict[str, Any]
        ] = []

        for rule in self.constraints:
            if (
                rule.target_column
                != column_id
            ):
                continue

            selected = state.get(
                rule.source_column,
                (),
            )

            if (
                rule.source_option
                not in selected
            ):
                continue

            options = set(
                rule.target_options
            )

            if rule.relation == "allow":
                allowed &= options

            elif (
                rule.relation
                == "exclude"
            ):
                allowed -= options

            elif (
                rule.relation
                == "require"
            ):
                required |= options

            explanations.append(
                rule.projection()
            )

        if not required.issubset(
            allowed
        ):
            raise configuration_error(
                f"constraints make "
                f"{column_id} impossible: "
                "required option excluded"
            )

        return {
            "column": column_id,
            "allowed": [
                value.id
                for value in target.options
                if value.id in allowed
            ],
            "required": [
                value.id
                for value in target.options
                if value.id in required
            ],
            "explanations":
                explanations,
        }

    def next_column_projection(
        self,
        values: Sequence[
            selection,
        ] = (),
    ) -> dict[str, Any] | None:
        state = self.state(
            values
        )

        for definition in self.columns:
            if definition.id in state:
                continue

            projection = (
                self.option_projection(
                    definition.id,
                    values,
                )
            )

            projection.update(
                {
                    "selection":
                        definition.selection,
                    "minimum":
                        definition.minimum,
                    "maximum":
                        definition.maximum,
                    "label":
                        definition.label,
                    "description":
                        definition.description,
                }
            )

            return projection

        return None

    def validate(
        self,
        values: Sequence[
            selection,
        ],
        *,
        complete: bool = False,
    ) -> tuple[
        selection,
        ...
    ]:
        normalized = (
            self.normalized_selections(
                values
            )
        )

        state = {
            value.column:
                value.options
            for value in normalized
        }

        prefix: list[
            selection
        ] = []

        for definition in self.columns:
            selected = state.get(
                definition.id
            )

            if selected is None:
                if (
                    complete
                    and definition.minimum > 0
                ):
                    raise configuration_error(
                        f"column {definition.id} "
                        "requires a selection"
                    )

                continue

            projection = (
                self.option_projection(
                    definition.id,
                    prefix,
                )
            )

            allowed = set(
                projection["allowed"]
            )

            required = set(
                projection["required"]
            )

            if not set(
                selected
            ).issubset(
                allowed
            ):
                raise configuration_error(
                    f"invalid option combination "
                    f"for column {definition.id}"
                )

            if not required.issubset(
                set(selected)
            ):
                raise configuration_error(
                    f"required option missing "
                    f"from column {definition.id}"
                )

            prefix.append(
                next(
                    value
                    for value in normalized
                    if value.column
                    == definition.id
                )
            )

        return normalized

    def build_recipe(
        self,
        values: Sequence[
            selection,
        ],
        *,
        lineage: Mapping[
            str,
            Any,
        ] | None = None,
        provenance: Mapping[
            str,
            Any,
        ] | None = None,
    ) -> recipe:
        normalized = self.validate(
            values,
            complete=True,
        )

        return recipe(
            definition_digest=
                self.definition_digest,
            selections=normalized,
            lineage=dict(
                lineage or {}
            ),
            provenance=dict(
                provenance or {}
            ),
        )

    def explain(
        self,
        values: Sequence[
            selection,
        ] = (),
    ) -> dict[str, Any]:
        normalized = self.validate(
            values,
            complete=False,
        )

        return {
            "schema":
                "savant://runtime/sieve/"
                "configuration-explanation/"
                "3.0.0",
            "definition_digest":
                self.definition_digest,
            "state": {
                value.column:
                    list(value.options)
                for value in normalized
            },
            "next":
                self.next_column_projection(
                    normalized
                ),
            "authority_effect":
                self.authority_effect,
            "utility":
                self.utility.projection(),
        }

    @classmethod
    def from_mapping(
        cls,
        value: Mapping[
            str,
            Any,
        ],
    ) -> configuration_current:
        raw_columns = value.get(
            "columns"
        )

        if not isinstance(
            raw_columns,
            list,
        ):
            raise configuration_error(
                "configuration mapping "
                "requires columns array"
            )

        columns: list[column] = []

        for raw_column in raw_columns:
            if not isinstance(
                raw_column,
                Mapping,
            ):
                raise configuration_error(
                    "column must be an object"
                )

            raw_options = raw_column.get(
                "options"
            )

            if not isinstance(
                raw_options,
                list,
            ):
                raise configuration_error(
                    "column options must "
                    "be an array"
                )

            options: list[option] = []

            for raw_option in raw_options:
                if isinstance(
                    raw_option,
                    str,
                ):
                    raw_option = {
                        "id": raw_option
                    }

                if not isinstance(
                    raw_option,
                    Mapping,
                ):
                    raise configuration_error(
                        "option must be "
                        "a string or object"
                    )

                parameters: list[
                    parameter_definition
                ] = []

                raw_parameters = (
                    raw_option.get(
                        "parameters",
                        [],
                    )
                )

                if not isinstance(
                    raw_parameters,
                    list,
                ):
                    raise configuration_error(
                        "option parameters "
                        "must be an array"
                    )

                for raw_parameter in (
                    raw_parameters
                ):
                    if not isinstance(
                        raw_parameter,
                        Mapping,
                    ):
                        raise configuration_error(
                            "parameter must "
                            "be an object"
                        )

                    parameters.append(
                        parameter_definition(
                            id=require_identifier(
                                raw_parameter.get(
                                    "id"
                                ),
                                field_name=
                                    "parameter id",
                            ),
                            type=str(
                                raw_parameter.get(
                                    "type",
                                    "string",
                                )
                            ),
                            required=bool(
                                raw_parameter.get(
                                    "required",
                                    False,
                                )
                            ),
                            default=
                                raw_parameter.get(
                                    "default"
                                ),
                            choices=tuple(
                                raw_parameter.get(
                                    "choices",
                                    (),
                                )
                            ),
                        )
                    )

                options.append(
                    option(
                        id=require_identifier(
                            raw_option.get(
                                "id"
                            ),
                            field_name=
                                "option id",
                        ),
                        label=raw_option.get(
                            "label"
                        ),
                        description=
                            raw_option.get(
                                "description"
                            ),
                        parameters=tuple(
                            parameters
                        ),
                    )
                )

            selection_mode = str(
                raw_column.get(
                    "selection",
                    "single",
                )
            )

            default_maximum = (
                1
                if selection_mode
                == "single"
                else None
            )

            raw_maximum = (
                raw_column.get(
                    "maximum",
                    default_maximum,
                )
            )

            columns.append(
                column(
                    id=require_identifier(
                        raw_column.get(
                            "id"
                        ),
                        field_name=
                            "column id",
                    ),
                    options=tuple(
                        options
                    ),
                    selection=
                        selection_mode,
                    minimum=int(
                        raw_column.get(
                            "minimum",
                            1,
                        )
                    ),
                    maximum=(
                        None
                        if raw_maximum
                        is None
                        else int(
                            raw_maximum
                        )
                    ),
                    label=raw_column.get(
                        "label"
                    ),
                    description=
                        raw_column.get(
                            "description"
                        ),
                )
            )

        constraints: list[
            constraint
        ] = []

        raw_constraints = value.get(
            "constraints",
            [],
        )

        if not isinstance(
            raw_constraints,
            list,
        ):
            raise configuration_error(
                "constraints must be an array"
            )

        for raw_rule in raw_constraints:
            if not isinstance(
                raw_rule,
                Mapping,
            ):
                raise configuration_error(
                    "constraint must be an object"
                )

            raw_targets = (
                raw_rule.get(
                    "target_options",
                    (),
                )
            )

            if isinstance(
                raw_targets,
                str,
            ):
                raw_targets = (
                    raw_targets,
                )

            constraints.append(
                constraint(
                    source_column=
                        require_identifier(
                            raw_rule.get(
                                "source_column"
                            ),
                            field_name=
                                "source column",
                        ),
                    source_option=
                        require_identifier(
                            raw_rule.get(
                                "source_option"
                            ),
                            field_name=
                                "source option",
                        ),
                    target_column=
                        require_identifier(
                            raw_rule.get(
                                "target_column"
                            ),
                            field_name=
                                "target column",
                        ),
                    relation=
                        require_identifier(
                            raw_rule.get(
                                "relation"
                            ),
                            field_name=
                                "constraint relation",
                        ),
                    target_options=
                        normalized_values(
                            tuple(
                                raw_targets
                            )
                        ),
                )
            )

        return cls(
            columns=tuple(columns),
            constraints=tuple(
                constraints
            ),
            lineage=dict(
                value.get(
                    "lineage",
                    {},
                )
            ),
            provenance=dict(
                value.get(
                    "provenance",
                    {},
                )
            ),
        )


# Compatibility alias retained from the lost verified implementation.
configuration = configuration_current


def selftest() -> dict[str, Any]:
    definition = (
        configuration_current.from_mapping(
            {
                "columns": [
                    {
                        "id": "action",
                        "options": [
                            "audit",
                            "extract",
                        ],
                    },
                    {
                        "id": "depth",
                        "options": [
                            {
                                "id":
                                    "focused",
                                "parameters": [
                                    {
                                        "id":
                                            "limit",
                                        "type":
                                            "integer",
                                        "required":
                                            True,
                                    }
                                ],
                            },
                            "exhaustive",
                        ],
                    },
                    {
                        "id": "output",
                        "options": [
                            "markdown",
                            "json",
                        ],
                    },
                ],
                "constraints": [
                    {
                        "source_column":
                            "action",
                        "source_option":
                            "audit",
                        "target_column":
                            "depth",
                        "relation":
                            "allow",
                        "target_options": [
                            "focused",
                            "exhaustive",
                        ],
                    },
                    {
                        "source_column":
                            "depth",
                        "source_option":
                            "exhaustive",
                        "target_column":
                            "output",
                        "relation":
                            "require",
                        "target_options": [
                            "markdown"
                        ],
                    },
                    {
                        "source_column":
                            "action",
                        "source_option":
                            "extract",
                        "target_column":
                            "output",
                        "relation":
                            "exclude",
                        "target_options": [
                            "markdown"
                        ],
                    },
                ],
                "lineage": {
                    "reconstruction":
                        "lost-verified-configuration"
                },
                "provenance": {
                    "authority":
                        "verified-behavioral-contract"
                },
            }
        )
    )

    audit = selection(
        column="action",
        options=("audit",),
    )

    focused = selection(
        column="depth",
        options=("focused",),
        parameters={
            "focused": {
                "limit": 25
            }
        },
    )

    exhaustive = selection(
        column="depth",
        options=("exhaustive",),
    )

    markdown = selection(
        column="output",
        options=("markdown",),
    )

    recipe_one = (
        definition.build_recipe(
            (
                audit,
                exhaustive,
                markdown,
            ),
            lineage={
                "source": "selftest"
            },
            provenance={
                "source": "selftest"
            },
        )
    )

    recipe_two = (
        definition.build_recipe(
            (
                audit,
                exhaustive,
                markdown,
            ),
            lineage={
                "source": "selftest"
            },
            provenance={
                "source": "selftest"
            },
        )
    )

    invalid_rejected = False

    try:
        definition.build_recipe(
            (
                selection(
                    column="action",
                    options=("extract",),
                ),
                exhaustive,
                markdown,
            )
        )
    except configuration_error:
        invalid_rejected = True

    bad_parameter_rejected = False

    try:
        definition.validate(
            (
                audit,
                selection(
                    column="depth",
                    options=("focused",),
                    parameters={
                        "focused": {
                            "limit":
                                "not-an-integer"
                        }
                    },
                ),
            )
        )
    except configuration_error:
        bad_parameter_rejected = True

    focused_validated = False

    try:
        definition.validate(
            (
                audit,
                focused,
            )
        )
        focused_validated = True
    except configuration_error:
        focused_validated = False

    first_projection = (
        definition.projection()
    )

    second_projection = (
        definition.projection()
    )

    explanation = (
        definition.explain(
            (audit,)
        )
    )

    utility = definition.utility

    checks = {
        "audit_projection":
            explanation[
                "state"
            ].get(
                "action"
            )
            == ["audit"],
        "authority_none":
            definition.authority_effect
            == "none",
        "compatibility_alias":
            configuration
            is configuration_current,
        "configuration_is_current":
            isinstance(
                definition,
                configuration_current,
            ),
        "current_projection":
            first_projection[
                "schema"
            ]
            == schema,
        "definition_deterministic":
            first_projection
            == second_projection,
        "explanation_available":
            explanation["next"]
            is not None,
        "invalid_combination_rejected":
            invalid_rejected,
        "parameter_validated":
            (
                focused_validated
                and bad_parameter_rejected
            ),
        "recipe_deterministic":
            recipe_one.recipe_digest
            == recipe_two.recipe_digest,
        "recipe_non_authoritative":
            recipe_one.authoritative
            is False,
        "recipe_rebuildable":
            recipe_one.rebuildable
            is True,
        "require_projection":
            definition.option_projection(
                "output",
                (
                    audit,
                    exhaustive,
                ),
            )["required"]
            == ["markdown"],
        "utility_edifice_exact":
            tuple(
                utility_edifice_projection()[
                    "levels"
                ]
            )
            == utility_edifice,
        "utility_unclassified":
            (
                utility.level is None
                and utility.ordinal is None
                and utility.current
                is False
                and utility.superseded_level
                == "current"
            ),
        "no_ordinal_migration":
            utility.projection()[
                "semantic_reclassification_required"
            ]
            is True,
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
            definition.definition_digest,
        "recipe_digest":
            recipe_one.recipe_digest,
        "utility_edifice_digest":
            utility_edifice_projection()[
                "projection_digest"
            ],
        "reconstruction": {
            "exact_source_recovery":
                False,
            "basis":
                "verified behavioral contract",
            "superseded_definition_digest":
                "a88dacdb83098c4a183c7c0d39b0a31a15dbfa674c266493c65e1e962f7110b6",
        },
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
