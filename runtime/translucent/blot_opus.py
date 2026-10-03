#!/usr/bin/env python3

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping

from runtime.opus_ai_adapter import (
    OpusAIAdapter,
    OpusAIAdapterError,
    OpusProviderSelection,
)
from runtime.translucent.blot_reconstruction import (
    Candidate,
    OpusWorkUnit,
    ReconstructionPipeline,
    StageResult,
    all_stages,
)


name = "blot."
schema = "savant.translucent.blot.opus.v2"
authority_effect = "none"
mutation_effect = "none"
projection_only = True

execution_owner = "opus"
routing_owner = "opus"

max_receipts = 8192
max_results = 8192
max_counterfactuals = 16


class BlotOpusError(RuntimeError):
    pass


def _canonical(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def _digest(value: Any) -> str:
    if isinstance(value, bytes):
        raw = value
    elif isinstance(value, str):
        raw = value.encode("utf-8")
    else:
        raw = _canonical(value).encode("utf-8")

    return hashlib.sha256(raw).hexdigest()


def _text(
    value: Any,
    field_name: str,
) -> str:
    result = str(value or "").strip()

    if not result:
        raise BlotOpusError(
            f"{field_name} is required"
        )

    return result


def _unique_text(
    values: Iterable[Any],
) -> tuple[str, ...]:
    return tuple(
        dict.fromkeys(
            str(value).strip()
            for value in values
            if str(value).strip()
        )
    )


def _selection_dict(
    selection: OpusProviderSelection,
) -> dict[str, Any]:
    body = selection.to_dict()

    return {
        "capability":
            _text(
                body.get("capability"),
                "capability",
            ),

        "providers":
            list(
                _unique_text(
                    body.get(
                        "providers",
                        (),
                    )
                )
            ),

        "selected":
            (
                str(
                    body["selected"]
                ).strip()
                if body.get(
                    "selected"
                )
                else None
            ),

        "mode":
            _text(
                body.get(
                    "mode",
                    "native",
                ),
                "mode",
            ),

        "native_fallback":
            bool(
                body.get(
                    "native_fallback",
                    True,
                )
            ),
    }


@dataclass(frozen=True, slots=True)
class TypedSegue:
    kind: str
    source: str
    target: str
    payload_digest: str
    lineage: tuple[str, ...] = ()
    provenance: tuple[str, ...] = ()

    def normalized(self) -> dict[str, Any]:
        body = {
            "schema":
                f"{schema}.typed-segue",

            "kind":
                _text(
                    self.kind,
                    "kind",
                ),

            "source":
                _text(
                    self.source,
                    "source",
                ),

            "target":
                _text(
                    self.target,
                    "target",
                ),

            "payload_digest":
                _text(
                    self.payload_digest,
                    "payload_digest",
                ),

            "lineage":
                list(
                    _unique_text(
                        self.lineage
                    )
                ),

            "provenance":
                list(
                    _unique_text(
                        self.provenance
                    )
                ),

            "authority_effect":
                "none",

            "mutation_effect":
                "none",
        }

        body["segue_id"] = (
            "blot-opus-segue-"
            + _digest(body)[:24]
        )

        body["digest"] = _digest(body)

        return body


@dataclass(frozen=True, slots=True)
class SelectionReceipt:
    work_id: str
    stage_id: str
    capability: str
    request_digest: str
    selection: OpusProviderSelection

    def normalized(self) -> dict[str, Any]:
        selection = _selection_dict(
            self.selection
        )

        capability = _text(
            self.capability,
            "capability",
        )

        if (
            selection[
                "capability"
            ]
            != capability
        ):
            raise BlotOpusError(
                "selection capability does not "
                "match work capability"
            )

        body = {
            "schema":
                f"{schema}.selection-receipt",

            "work_id":
                _text(
                    self.work_id,
                    "work_id",
                ),

            "stage_id":
                _text(
                    self.stage_id,
                    "stage_id",
                ),

            "capability":
                capability,

            "request_digest":
                _text(
                    self.request_digest,
                    "request_digest",
                ),

            "selection":
                selection,

            "selection_owner":
                "opus",

            "execution_owner":
                execution_owner,

            "routing_owner":
                routing_owner,

            "authority_effect":
                "none",

            "mutation_effect":
                "none",
        }

        body["digest"] = _digest(body)

        return body


@dataclass(frozen=True, slots=True)
class WorkReceipt:
    work_id: str
    stage_id: str
    request_digest: str
    selection_digest: str
    status: str
    result_digest: str
    provider: str | None = None
    mode: str = "native"
    provenance: tuple[str, ...] = ()

    def normalized(self) -> dict[str, Any]:
        if self.status not in {
            "accepted",
            "rejected",
            "blocked",
            "ambiguous",
        }:
            raise BlotOpusError(
                f"invalid work status: "
                f"{self.status}"
            )

        body = {
            "schema":
                f"{schema}.work-receipt",

            "work_id":
                _text(
                    self.work_id,
                    "work_id",
                ),

            "stage_id":
                _text(
                    self.stage_id,
                    "stage_id",
                ),

            "request_digest":
                _text(
                    self.request_digest,
                    "request_digest",
                ),

            "selection_digest":
                _text(
                    self.selection_digest,
                    "selection_digest",
                ),

            "status":
                self.status,

            "result_digest":
                _text(
                    self.result_digest,
                    "result_digest",
                ),

            "provider":
                (
                    str(
                        self.provider
                    ).strip()
                    if self.provider
                    else None
                ),

            "mode":
                _text(
                    self.mode,
                    "mode",
                ),

            "provenance":
                list(
                    _unique_text(
                        self.provenance
                    )
                ),

            "execution_owner":
                execution_owner,

            "routing_owner":
                routing_owner,

            "authority_effect":
                "none",

            "mutation_effect":
                "none",
        }

        body["digest"] = _digest(body)

        return body


@dataclass(frozen=True, slots=True)
class Counterfactual:
    candidate_id: str
    strategy: str
    blockers: tuple[str, ...]
    predicted_cost: Mapping[str, float]
    predicted_quality: Mapping[str, float]
    primitive_ids: tuple[str, ...] = ()
    segue_ids: tuple[str, ...] = ()

    @classmethod
    def from_candidate(
        cls,
        candidate: Candidate,
    ) -> "Counterfactual":
        data = candidate.normalized()

        return cls(
            candidate_id=data[
                "candidate_id"
            ],
            strategy=data[
                "strategy"
            ],
            blockers=tuple(
                data[
                    "blockers"
                ]
            ),
            predicted_cost=dict(
                data[
                    "predicted_cost"
                ]
            ),
            predicted_quality=dict(
                data[
                    "predicted_quality"
                ]
            ),
            primitive_ids=tuple(
                data[
                    "primitive_ids"
                ]
            ),
            segue_ids=tuple(
                data[
                    "segue_ids"
                ]
            ),
        )

    def normalized(self) -> dict[str, Any]:
        body = {
            "schema":
                f"{schema}.counterfactual",

            "candidate_id":
                _text(
                    self.candidate_id,
                    "candidate_id",
                ),

            "strategy":
                _text(
                    self.strategy,
                    "strategy",
                ),

            "blockers":
                list(
                    _unique_text(
                        self.blockers
                    )
                ),

            "predicted_cost":
                {
                    str(key):
                        float(value)
                    for key, value
                    in sorted(
                        self.predicted_cost.items()
                    )
                },

            "predicted_quality":
                {
                    str(key):
                        float(value)
                    for key, value
                    in sorted(
                        self.predicted_quality.items()
                    )
                },

            "primitive_ids":
                list(
                    _unique_text(
                        self.primitive_ids
                    )
                ),

            "segue_ids":
                list(
                    _unique_text(
                        self.segue_ids
                    )
                ),

            "authority_effect":
                "none",
        }

        body["digest"] = _digest(body)

        return body


@dataclass(frozen=True, slots=True)
class SelectionPolicy:
    quality_weights: Mapping[
        str,
        float
    ] = field(
        default_factory=lambda: {
            "fidelity": 1.0,
            "structural": 1.0,
            "editability": 1.0,
            "economy": 1.0,
            "compatibility": 1.0,
        }
    )
    cost_weights: Mapping[
        str,
        float
    ] = field(
        default_factory=lambda: {
            "paths": 0.01,
            "anchors": 0.001,
            "gradients": 0.01,
            "masks": 0.02,
            "clips": 0.02,
            "filters": 0.05,
        }
    )

    def normalized(self) -> dict[str, Any]:
        body = {
            "quality_weights":
                {
                    str(key):
                        float(value)
                    for key, value
                    in sorted(
                        self.quality_weights.items()
                    )
                },

            "cost_weights":
                {
                    str(key):
                        float(value)
                    for key, value
                    in sorted(
                        self.cost_weights.items()
                    )
                },
        }

        body["digest"] = _digest(body)

        return body


class CounterfactualSelector:
    """
    Selects among reconstruction constructions only.

    It does not select AI providers, models, retries,
    fallbacks, execution routes, cost policy, or latency
    policy. Those remain owned by Opus.
    """

    def __init__(
        self,
        policy: SelectionPolicy | None = None,
    ) -> None:
        self.policy = (
            policy
            or SelectionPolicy()
        )

    def score(
        self,
        counterfactual: Counterfactual,
    ) -> tuple[
        int,
        float,
        str,
    ]:
        data = counterfactual.normalized()
        policy = self.policy.normalized()

        blocker_count = len(
            data["blockers"]
        )

        quality = sum(
            float(
                data[
                    "predicted_quality"
                ].get(
                    key,
                    0.0,
                )
            )
            * float(weight)
            for key, weight
            in policy[
                "quality_weights"
            ].items()
        )

        cost = sum(
            float(
                data[
                    "predicted_cost"
                ].get(
                    key,
                    0.0,
                )
            )
            * float(weight)
            for key, weight
            in policy[
                "cost_weights"
            ].items()
        )

        return (
            blocker_count,
            -(quality - cost),
            data[
                "candidate_id"
            ],
        )

    def select(
        self,
        counterfactuals: Iterable[
            Counterfactual
        ],
    ) -> Counterfactual:
        candidates = tuple(
            counterfactuals
        )

        if not candidates:
            raise BlotOpusError(
                "at least one reconstruction "
                "counterfactual is required"
            )

        if (
            len(candidates)
            > max_counterfactuals
        ):
            raise BlotOpusError(
                "counterfactual limit exceeded"
            )

        return min(
            candidates,
            key=self.score,
        )

    def manifest(
        self,
    ) -> dict[str, Any]:
        body = {
            "schema":
                f"{schema}.counterfactual-selector",

            "domain":
                "reconstruction-strategy",

            "provider_selection":
                False,

            "model_selection":
                False,

            "execution_routing":
                False,

            "retry_policy":
                False,

            "fallback_policy":
                False,

            "policy":
                self.policy.normalized(),

            "authority_effect":
                "none",

            "mutation_effect":
                "none",
        }

        body["digest"] = _digest(body)

        return body


class BlotOpusBridge:
    """
    Reconstruction-to-Opus boundary.

    Blot owns reconstruction work specification, stage
    state, typed reconstruction segues and deterministic
    receipts.

    Opus owns provider/model routing, execution, retries,
    fallback, cost policy, latency policy and multi-agent
    execution.
    """

    def __init__(
        self,
        pipeline: ReconstructionPipeline,
        adapter: OpusAIAdapter | None = None,
    ) -> None:
        self.pipeline = pipeline
        self.adapter = (
            adapter
            or OpusAIAdapter()
        )

        self._requests: dict[
            str,
            dict[str, Any],
        ] = {}

        self._selections: dict[
            str,
            SelectionReceipt,
        ] = {}

        self._results: dict[
            str,
            dict[str, Any],
        ] = {}

        self._receipts: dict[
            str,
            WorkReceipt,
        ] = {}

        self._segues: dict[
            str,
            TypedSegue,
        ] = {}

        self._stage_ids = {
            stage.stage_id
            for stage in all_stages
        }

    def request_for(
        self,
        work: OpusWorkUnit,
    ) -> dict[str, Any]:
        data = work.normalized()

        body = {
            "schema":
                f"{schema}.work-request",

            "owner":
                "blot.",

            "orchestrator":
                "opus",

            "work":
                data,

            "capability":
                data[
                    "capability"
                ],

            "preferred_providers":
                list(
                    data[
                        "preferred_providers"
                    ]
                ),

            "execution_owner":
                execution_owner,

            "routing_owner":
                routing_owner,

            "authority_effect":
                "none",

            "mutation_effect":
                "none",

            "projection_only":
                True,
        }

        body["digest"] = _digest(body)

        work_id = data[
            "work_id"
        ]

        existing = self._requests.get(
            work_id
        )

        if (
            existing is not None
            and existing != body
        ):
            raise BlotOpusError(
                "work request identity conflict: "
                f"{work_id}"
            )

        self._requests[
            work_id
        ] = body

        return body

    def requests_for_rung(
        self,
        rung: int,
    ) -> tuple[
        dict[str, Any],
        ...
    ]:
        return tuple(
            self.request_for(work)
            for work
            in self.pipeline.opus_plan(
                rung
            )
        )

    def select_for(
        self,
        work: OpusWorkUnit,
    ) -> SelectionReceipt:
        request = self.request_for(
            work
        )

        try:
            selection = self.adapter.select(
                request[
                    "capability"
                ],
                preferred_providers=(
                    request[
                        "preferred_providers"
                    ]
                ),
            )
        except OpusAIAdapterError as exc:
            raise BlotOpusError(
                str(exc)
            ) from exc

        receipt = SelectionReceipt(
            work_id=(
                request[
                    "work"
                ][
                    "work_id"
                ]
            ),
            stage_id=(
                request[
                    "work"
                ][
                    "stage_id"
                ]
            ),
            capability=(
                request[
                    "capability"
                ]
            ),
            request_digest=(
                request[
                    "digest"
                ]
            ),
            selection=selection,
        )

        normalized = (
            receipt.normalized()
        )

        work_id = normalized[
            "work_id"
        ]

        existing = self._selections.get(
            work_id
        )

        if (
            existing is not None
            and existing.normalized()
            != normalized
        ):
            raise BlotOpusError(
                "selection receipt identity "
                f"conflict: {work_id}"
            )

        self._selections[
            work_id
        ] = receipt

        return receipt

    def selection_packet(
        self,
        work: OpusWorkUnit,
    ) -> dict[str, Any]:
        request = self.request_for(
            work
        )

        selection = self.select_for(
            work
        ).normalized()

        body = {
            "schema":
                f"{schema}.selection-packet",

            "request":
                request,

            "selection":
                selection,

            "execution_owner":
                execution_owner,

            "routing_owner":
                routing_owner,

            "provider_execution":
                False,

            "authority_effect":
                "none",

            "mutation_effect":
                "none",
        }

        body["digest"] = _digest(body)

        return body

    def record_external_result(
        self,
        work: OpusWorkUnit,
        *,
        status: str,
        output: Mapping[str, Any],
        attempt: int = 1,
        confidence: float = 1.0,
        causal_stage_id: str | None = None,
        provider: str | None = None,
        mode: str | None = None,
        provenance: Iterable[str] = (),
    ) -> WorkReceipt:
        if (
            len(self._receipts)
            >= max_receipts
        ):
            raise BlotOpusError(
                "work receipt limit exceeded"
            )

        if (
            len(self._results)
            >= max_results
        ):
            raise BlotOpusError(
                "result limit exceeded"
            )

        request = self.request_for(
            work
        )

        work_data = request[
            "work"
        ]

        work_id = work_data[
            "work_id"
        ]

        selection_receipt = (
            self._selections.get(
                work_id
            )
        )

        if selection_receipt is None:
            selection_receipt = (
                self.select_for(
                    work
                )
            )

        selection_data = (
            selection_receipt
            .normalized()
        )

        selected_provider = (
            selection_data[
                "selection"
            ][
                "selected"
            ]
        )

        if (
            provider is not None
            and selected_provider
            is not None
            and str(provider).strip()
            != selected_provider
        ):
            raise BlotOpusError(
                "recorded provider does not "
                "match Opus selection"
            )

        result_provider = (
            str(provider).strip()
            if provider is not None
            else selected_provider
        )

        result_mode = (
            str(mode).strip()
            if mode is not None
            and str(mode).strip()
            else selection_data[
                "selection"
            ][
                "mode"
            ]
        )

        result_body = {
            "schema":
                f"{schema}.external-result",

            "work_id":
                work_id,

            "stage_id":
                work_data[
                    "stage_id"
                ],

            "status":
                _text(
                    status,
                    "status",
                ),

            "output":
                dict(output),

            "provider":
                result_provider,

            "mode":
                result_mode,

            "attempt":
                int(attempt),

            "confidence":
                float(confidence),

            "causal_stage_id":
                causal_stage_id,

            "provenance":
                list(
                    _unique_text(
                        provenance
                    )
                ),

            "execution_owner":
                execution_owner,

            "routing_owner":
                routing_owner,

            "recorded_by":
                "blot.",

            "authority_effect":
                "none",

            "mutation_effect":
                "none",
        }

        result_body[
            "digest"
        ] = _digest(
            result_body
        )

        stage_result = StageResult(
            stage_id=(
                work_data[
                    "stage_id"
                ]
            ),
            attempt=int(attempt),
            status=status,
            output=dict(output),
            input_digest=(
                work_data[
                    "input_digest"
                ]
                or request[
                    "digest"
                ]
            ),
            confidence=float(
                confidence
            ),
            causal_stage_id=(
                causal_stage_id
            ),
            provenance=tuple(
                _unique_text(
                    provenance
                )
            ),
        )

        self.pipeline.record_stage_result(
            stage_result
        )

        receipt = WorkReceipt(
            work_id=work_id,
            stage_id=(
                work_data[
                    "stage_id"
                ]
            ),
            request_digest=(
                request[
                    "digest"
                ]
            ),
            selection_digest=(
                selection_data[
                    "digest"
                ]
            ),
            status=status,
            result_digest=(
                result_body[
                    "digest"
                ]
            ),
            provider=result_provider,
            mode=result_mode,
            provenance=tuple(
                _unique_text(
                    provenance
                )
            ),
        )

        receipt_data = (
            receipt.normalized()
        )

        existing_result = (
            self._results.get(
                work_id
            )
        )

        if (
            existing_result is not None
            and existing_result
            != result_body
        ):
            raise BlotOpusError(
                "external result identity "
                f"conflict: {work_id}"
            )

        existing_receipt = (
            self._receipts.get(
                work_id
            )
        )

        if (
            existing_receipt is not None
            and existing_receipt
            .normalized()
            != receipt_data
        ):
            raise BlotOpusError(
                "work receipt identity "
                f"conflict: {work_id}"
            )

        self._results[
            work_id
        ] = result_body

        self._receipts[
            work_id
        ] = receipt

        return receipt

    def relate(
        self,
        *,
        kind: str,
        source: str,
        target: str,
        payload: Mapping[
            str,
            Any
        ],
        lineage: Iterable[str] = (),
        provenance: Iterable[str] = (),
    ) -> str:
        source = _text(
            source,
            "source",
        )

        target = _text(
            target,
            "target",
        )

        segue = TypedSegue(
            kind=kind,
            source=source,
            target=target,
            payload_digest=_digest(
                dict(payload)
            ),
            lineage=tuple(
                _unique_text(
                    lineage
                )
            ),
            provenance=tuple(
                _unique_text(
                    provenance
                )
            ),
        )

        data = segue.normalized()
        segue_id = data[
            "segue_id"
        ]

        existing = self._segues.get(
            segue_id
        )

        if (
            existing is not None
            and existing.normalized()
            != data
        ):
            raise BlotOpusError(
                "typed segue identity conflict"
            )

        self._segues[
            segue_id
        ] = segue

        return segue_id

    def replay_manifest(
        self,
    ) -> dict[str, Any]:
        requests = [
            self._requests[
                key
            ]
            for key in sorted(
                self._requests
            )
        ]

        selections = [
            self._selections[
                key
            ].normalized()
            for key in sorted(
                self._selections
            )
        ]

        results = [
            self._results[
                key
            ]
            for key in sorted(
                self._results
            )
        ]

        receipts = [
            self._receipts[
                key
            ].normalized()
            for key in sorted(
                self._receipts
            )
        ]

        segues = [
            self._segues[
                key
            ].normalized()
            for key in sorted(
                self._segues
            )
        ]

        body = {
            "schema":
                f"{schema}.replay-manifest",

            "name":
                name,

            "pipeline":
                self.pipeline.manifest(),

            "opus_adapter":
                self.adapter.status(),

            "requests":
                requests,

            "selections":
                selections,

            "external_results":
                results,

            "receipts":
                receipts,

            "typed_segues":
                segues,

            "request_count":
                len(requests),

            "selection_count":
                len(selections),

            "result_count":
                len(results),

            "receipt_count":
                len(receipts),

            "segue_count":
                len(segues),

            "provider_registry_owned":
                False,

            "provider_execution_owned":
                False,

            "provider_retry_owned":
                False,

            "provider_fallback_owned":
                False,

            "provider_cost_policy_owned":
                False,

            "provider_latency_policy_owned":
                False,

            "execution_owner":
                execution_owner,

            "routing_owner":
                routing_owner,

            "deterministic_receipts":
                True,

            "authority_effect":
                authority_effect,

            "mutation_effect":
                mutation_effect,

            "projection_only":
                projection_only,
        }

        body["digest"] = _digest(body)

        return body


def stage_index() -> dict[
    str,
    dict[str, Any],
]:
    return {
        stage.stage_id:
            stage.normalized()
        for stage in all_stages
    }


def manifest() -> dict[str, Any]:
    body = {
        "schema":
            schema,

        "name":
            name,

        "purpose":
            (
                "blot reconstruction work "
                "handoff to opus"
            ),

        "execution_owner":
            execution_owner,

        "routing_owner":
            routing_owner,

        "provider_registry_owned":
            False,

        "provider_execution_owned":
            False,

        "provider_selection_policy_owned":
            False,

        "provider_retry_owned":
            False,

        "provider_fallback_owned":
            False,

        "provider_cost_policy_owned":
            False,

        "provider_latency_policy_owned":
            False,

        "reconstruction_strategy_selection":
            True,

        "typed_segues":
            True,

        "deterministic_receipts":
            True,

        "authority_effect":
            authority_effect,

        "mutation_effect":
            mutation_effect,

        "projection_only":
            projection_only,
    }

    body["digest"] = _digest(body)

    return body


def selftest() -> dict[str, Any]:
    pipeline = ReconstructionPipeline(
        "blot-opus-selftest"
    )

    work = pipeline.opus_plan(
        1
    )[0]

    class _SelftestAdapter:
        def select(
            self,
            capability: str,
            *,
            preferred_providers:
                Iterable[str] = (),
        ) -> OpusProviderSelection:
            del preferred_providers

            return OpusProviderSelection(
                capability=capability,
                providers=(),
                selected=None,
                mode="native",
                native_fallback=True,
            )

        def status(
            self,
        ) -> dict[str, Any]:
            return {
                "schema":
                    "savant.opus-ai-adapter.v1",

                "owner":
                    "opus",

                "mode":
                    "native",

                "usable_providers":
                    [],

                "capabilities":
                    [],

                "native_fallback":
                    True,

                "authority_effect":
                    "none",

                "mutation_effect":
                    "none",

                "execution_owner":
                    "opus",

                "routing_owner":
                    "opus",
            }

    bridge = BlotOpusBridge(
        pipeline,
        adapter=_SelftestAdapter(),
    )

    request_a = bridge.request_for(
        work
    )

    request_b = bridge.request_for(
        work
    )

    selection = bridge.select_for(
        work
    )

    receipt = bridge.record_external_result(
        work,
        status="accepted",
        output={
            "normalized":
                True,
        },
        provenance=(
            "selftest",
        ),
    )

    segue_id = bridge.relate(
        kind="projection-handoff",
        source=work.work_id,
        target=work.stage_id,
        payload={
            "result":
                receipt.normalized()[
                    "result_digest"
                ],
        },
        provenance=(
            "selftest",
        ),
    )

    replay_a = (
        bridge.replay_manifest()
    )

    replay_b = (
        bridge.replay_manifest()
    )

    selector = (
        CounterfactualSelector()
    )

    selected = selector.select(
        (
            Counterfactual(
                candidate_id="dense",
                strategy="dense-paths",
                blockers=(),
                predicted_cost={
                    "paths": 100,
                    "anchors": 1000,
                },
                predicted_quality={
                    "fidelity": 0.95,
                    "structural": 0.5,
                    "editability": 0.3,
                    "economy": 0.1,
                    "compatibility": 0.8,
                },
            ),
            Counterfactual(
                candidate_id="semantic",
                strategy="semantic-ribbons",
                blockers=(),
                predicted_cost={
                    "paths": 3,
                    "anchors": 18,
                },
                predicted_quality={
                    "fidelity": 0.94,
                    "structural": 1.0,
                    "editability": 1.0,
                    "economy": 1.0,
                    "compatibility": 1.0,
                },
            ),
        )
    )

    checks = {
        "name_exact":
            name == "blot.",

        "authority_none":
            authority_effect
            == "none",

        "mutation_none":
            mutation_effect
            == "none",

        "projection_only":
            projection_only is True,

        "execution_owned_by_opus":
            execution_owner
            == "opus",

        "routing_owned_by_opus":
            routing_owner
            == "opus",

        "request_deterministic":
            request_a
            == request_b,

        "native_selection_recorded":
            selection.normalized()[
                "selection"
            ][
                "mode"
            ]
            == "native",

        "result_recorded":
            receipt.normalized()[
                "status"
            ]
            == "accepted",

        "typed_segue":
            segue_id.startswith(
                "blot-opus-segue-"
            ),

        "replay_deterministic":
            replay_a
            == replay_b,

        "no_provider_registry":
            replay_a[
                "provider_registry_owned"
            ]
            is False,

        "no_provider_execution":
            replay_a[
                "provider_execution_owned"
            ]
            is False,

        "no_retry_ownership":
            replay_a[
                "provider_retry_owned"
            ]
            is False,

        "no_fallback_ownership":
            replay_a[
                "provider_fallback_owned"
            ]
            is False,

        "semantic_counterfactual":
            selected.candidate_id
            == "semantic",

        "stage_result_recorded":
            len(
                pipeline.manifest()[
                    "stage_results"
                ]
            )
            == 1,
    }

    result = {
        "schema":
            f"{schema}.selftest",

        "ok":
            all(
                checks.values()
            ),

        "checks":
            checks,

        "manifest":
            manifest(),

        "replay_digest":
            replay_a[
                "digest"
            ],

        "authority_effect":
            authority_effect,

        "mutation_effect":
            mutation_effect,
    }

    result["digest"] = _digest(result)

    return result


__all__ = [
    "BlotOpusBridge",
    "BlotOpusError",
    "Counterfactual",
    "CounterfactualSelector",
    "SelectionPolicy",
    "SelectionReceipt",
    "TypedSegue",
    "WorkReceipt",
    "authority_effect",
    "execution_owner",
    "manifest",
    "max_counterfactuals",
    "max_receipts",
    "max_results",
    "mutation_effect",
    "name",
    "projection_only",
    "routing_owner",
    "schema",
    "selftest",
    "stage_index",
]


if __name__ == "__main__":
    print(
        json.dumps(
            selftest(),
            indent=2,
            sort_keys=True,
        )
    )
