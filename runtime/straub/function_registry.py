#!/usr/bin/env python3

from __future__ import annotations

from typing import Any, Mapping, Sequence

from .model import (
    StraubValidationError,
)
from .step import (
    execution_trace,
    function_instance,
    function_step,
    step_execution,
    validate_function_steps,
)


schema = "savant.straub.function-registry.v1"
owner = "savant"
authority_effect = "none"


class StraubFunctionRegistry:
    """
    Composition helper over StraubRegistry.

    It does not own execution. It creates and
    projects first-class function and step identity.
    """

    def __init__(
        self,
        registry: Any,
    ) -> None:
        required = (
            "substantiate",
            "instance",
            "export_capsule",
        )

        for method in required:
            if not callable(
                getattr(
                    registry,
                    method,
                    None,
                )
            ):
                raise StraubValidationError(
                    "invalid straub registry"
                )

        self._registry = registry

    def define_step(
        self,
        *,
        instance_id: str,
        label: str,
        operation: str,
        ordinal: int,
        input_contract: Mapping[str, Any] | None = None,
        output_contract: Mapping[str, Any] | None = None,
        dependencies: Sequence[str] | None = None,
        owner_id: str | None = None,
        deterministic: bool = True,
        side_effect_class: str = "none",
        provenance: Mapping[str, Any] | None = None,
        lineage: Mapping[str, Any] | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        return self._registry.substantiate(
            function_step(
                instance_id=instance_id,
                label=label,
                operation=operation,
                ordinal=ordinal,
                input_contract=input_contract,
                output_contract=output_contract,
                dependencies=dependencies,
                owner_id=owner_id,
                deterministic=deterministic,
                side_effect_class=(
                    side_effect_class
                ),
                provenance=provenance,
                lineage=lineage,
                metadata=metadata,
            )
        )

    def define_function(
        self,
        *,
        instance_id: str,
        label: str,
        step_ids: Sequence[str],
        purpose: str = "",
        owner_id: str | None = None,
        dependencies: Sequence[str] | None = None,
        provenance: Mapping[str, Any] | None = None,
        lineage: Mapping[str, Any] | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        for step_id in step_ids:
            record = self._registry.instance(
                str(
                    step_id
                )
            )

            if (
                record.get(
                    "kind"
                )
                != "function.step"
            ):
                raise StraubValidationError(
                    "function member is not "
                    "function.step"
                )

        record = function_instance(
            instance_id=instance_id,
            label=label,
            step_ids=step_ids,
            purpose=purpose,
            owner_id=owner_id,
            dependencies=dependencies,
            provenance=provenance,
            lineage=lineage,
            metadata=metadata,
        )

        stored = (
            self._registry.substantiate(
                record
            )
        )

        self.steps(
            stored[
                "id"
            ]
        )

        return stored

    def record_step_execution(
        self,
        *,
        instance_id: str,
        step_id: str,
        execution_id: str,
        status: str,
        input_digest: str | None = None,
        output_digest: str | None = None,
        previous_execution_id: str | None = None,
        dependencies: Sequence[str] | None = None,
        provenance: Mapping[str, Any] | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        step_record = (
            self._registry.instance(
                step_id
            )
        )

        if (
            step_record.get(
                "kind"
            )
            != "function.step"
        ):
            raise StraubValidationError(
                "step execution target "
                "is not function.step"
            )

        if previous_execution_id:
            previous = (
                self._registry.instance(
                    previous_execution_id
                )
            )

            if (
                previous.get(
                    "kind"
                )
                != "function.step.execution"
            ):
                raise StraubValidationError(
                    "previous execution is not "
                    "function.step.execution"
                )

        return self._registry.substantiate(
            step_execution(
                instance_id=instance_id,
                step_id=step_id,
                execution_id=execution_id,
                status=status,
                input_digest=input_digest,
                output_digest=output_digest,
                previous_execution_id=(
                    previous_execution_id
                ),
                dependencies=dependencies,
                provenance=provenance,
                metadata=metadata,
            )
        )

    def _instances(
        self,
    ) -> dict[
        str,
        dict[str, Any],
    ]:
        capsule = (
            self._registry.export_capsule()
        )

        result: dict[
            str,
            dict[str, Any],
        ] = {}

        for record in capsule[
            "instances"
        ]:
            result[
                record[
                    "id"
                ]
            ] = record

        return result

    def steps(
        self,
        function_id: str,
    ) -> dict[str, Any]:
        instances = self._instances()

        function_record = instances.get(
            function_id
        )

        if function_record is None:
            raise StraubValidationError(
                "function missing: "
                f"{function_id}"
            )

        return validate_function_steps(
            function_record=(
                function_record
            ),
            instances=instances,
        )

    def trace(
        self,
        *,
        function_id: str,
        execution_id: str,
    ) -> dict[str, Any]:
        return execution_trace(
            function_id=function_id,
            execution_id=execution_id,
            instances=self._instances(),
        )
