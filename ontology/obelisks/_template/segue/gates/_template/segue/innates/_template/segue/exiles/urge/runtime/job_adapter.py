from __future__ import annotations

import hashlib
import inspect
import json
from dataclasses import dataclass
from typing import Any, Callable, Mapping, Sequence

from .iteration import assessment, proposal


schema = "savant://runtime/urge/job-adapter/1.0.0"
owner = "exile:urge"


class job_adapter_error(ValueError):
    pass


def _canonical_json(value: Any) -> str:
    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        )
    except (TypeError, ValueError) as exc:
        raise job_adapter_error(
            "adapter values must be canonical-json serializable"
        ) from exc


def _digest(value: Any) -> str:
    return hashlib.sha256(
        _canonical_json(value).encode("utf-8")
    ).hexdigest()


def _invoke(
    function: Callable[..., Any],
    *args: Any,
) -> Any:
    value = function(*args)

    if inspect.isawaitable(value):
        raise job_adapter_error(
            "async execution must terminate outside urge"
        )

    return value


def _strings(
    values: Any,
) -> tuple[str, ...]:
    if values is None:
        return ()

    if isinstance(values, str):
        values = (values,)

    if (
        isinstance(values, bytes)
        or not isinstance(values, Sequence)
    ):
        raise job_adapter_error(
            "expected a sequence of strings"
        )

    result = []
    seen = set()

    for value in values:
        text = str(value).strip()

        if text and text not in seen:
            seen.add(text)
            result.append(text)

    return tuple(result)


@dataclass(frozen=True, slots=True)
class execution_boundary:
    evaluate: Callable[
        [Mapping[str, Any]], Mapping[str, Any]
    ]
    revise: Callable[
        [Mapping[str, Any]], Sequence[Mapping[str, Any]]
    ]
    identity: str = "external-execution-boundary"

    def __post_init__(self) -> None:
        if not callable(self.evaluate):
            raise job_adapter_error(
                "evaluate boundary must be callable"
            )

        if not callable(self.revise):
            raise job_adapter_error(
                "revise boundary must be callable"
            )

        if not str(self.identity).strip():
            raise job_adapter_error(
                "execution boundary identity is required"
            )


class adapter:
    def __init__(
        self,
        boundary: execution_boundary,
    ) -> None:
        if not isinstance(
            boundary,
            execution_boundary,
        ):
            raise job_adapter_error(
                "boundary must be an execution_boundary"
            )

        self.boundary = boundary

    def evaluator(
        self,
        payload: Any,
        context: Mapping[str, Any],
    ) -> assessment:
        request = {
            "schema": schema,
            "operation": "evaluate",
            "owner": owner,
            "boundary": self.boundary.identity,
            "payload": payload,
            "context": dict(context),
            "requirements": {
                "return_scores_for_every_criterion": True,
                "scores_range": [
                    0.0,
                    1.0,
                ],
                "preserve_evidence": True,
                "do_not_create_authority": True,
            },
        }

        request["digest"] = _digest(request)

        response = _invoke(
            self.boundary.evaluate,
            request,
        )

        if not isinstance(response, Mapping):
            raise job_adapter_error(
                "evaluate boundary must return a mapping"
            )

        scores = response.get("scores")

        if not isinstance(scores, Mapping):
            raise job_adapter_error(
                "evaluate response requires scores"
            )

        metadata = response.get(
            "metadata",
            {},
        )

        if not isinstance(metadata, Mapping):
            metadata = {}

        return assessment(
            scores=dict(scores),
            findings=_strings(
                response.get(
                    "findings",
                    (),
                )
            ),
            evidence=_strings(
                response.get(
                    "evidence",
                    (),
                )
            ),
            metadata={
                **dict(metadata),
                "boundary": self.boundary.identity,
                "request_digest": request[
                    "digest"
                ],
                "response_digest": _digest(
                    response
                ),
            },
        )

    def reviser(
        self,
        payload: Any,
        pressure: Mapping[str, Any],
    ) -> Sequence[proposal]:
        request = {
            "schema": schema,
            "operation": "revise",
            "owner": owner,
            "boundary": self.boundary.identity,
            "payload": payload,
            "pressure": dict(pressure),
            "requirements": {
                "preserve_job_identity": True,
                "respond_to_revision_pressure": True,
                "return_distinct_candidates": True,
                "do_not_create_authority": True,
            },
        }

        request["digest"] = _digest(request)

        response = _invoke(
            self.boundary.revise,
            request,
        )

        if (
            isinstance(response, (str, bytes))
            or not isinstance(response, Sequence)
        ):
            raise job_adapter_error(
                "revise boundary must return a sequence"
            )

        result = []

        for index, item in enumerate(response):
            if not isinstance(item, Mapping):
                raise job_adapter_error(
                    "revision candidates must be mappings"
                )

            if "payload" not in item:
                raise job_adapter_error(
                    "revision candidate requires payload"
                )

            metadata = item.get(
                "metadata",
                {},
            )

            if not isinstance(metadata, Mapping):
                metadata = {}

            result.append(
                proposal(
                    payload=item["payload"],
                    rationale=_strings(
                        item.get(
                            "rationale",
                            (),
                        )
                    ),
                    provenance=(
                        *(
                            _strings(
                                item.get(
                                    "provenance",
                                    (),
                                )
                            )
                        ),
                        (
                            f"boundary:"
                            f"{self.boundary.identity}"
                        ),
                    ),
                    metadata={
                        **dict(metadata),
                        "boundary": self.boundary.identity,
                        "request_digest": request[
                            "digest"
                        ],
                        "response_digest": _digest(
                            item
                        ),
                        "branch_index": index,
                    },
                )
            )

        return tuple(result)


__all__ = [
    "adapter",
    "execution_boundary",
    "job_adapter_error",
]
