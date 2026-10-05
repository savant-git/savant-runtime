#!/usr/bin/env python3

from __future__ import annotations

import hashlib
import json
import math
import threading
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

from lexicon.semantic_identity import (
    SemanticIdentityRegistry,
    TruthError,
    require_truth,
    semantic_identity,
    truth_envelope,
    truth_state_from_value,
    truth_summary,
    truth_derive,
)
from runtime.straub.datrix_profiles import manifest as datrix_profile_manifest
from runtime.straub.interface import DatrixInterface
from runtime.translucent.compiler import (
    TranslucentCompileError,
    TranslucentCompiler,
)
from runtime.translucent.svg import TL_NS, TranslucentSVGError, TranslucentSVGRuntime, svg_runtime


schema = "savant.translucent.datrix-language.v3"
owner = "savant"
authority_effect = "none"

MAX_RESULTS = 100_000
MAX_WALK_DEPTH = 64

TOP_LEVEL_OPERATORS = (
    "open",
    "put",
    "segue",
    "select",
    "walk",
    "project",
    "union",
    "intersect",
    "diff",
    "aggregate",
    "assert",
    "truth-gate",
    "checkpoint",
    "health",
    "explain",
)
NESTED_OPERATORS = (
    "payload",
    "metadata",
    "field",
    "depends",
    "evidence-ref",
    "match",
    "where",
    "project",
    "order",
    "limit",
)
WHERE_OPERATORS = ("eq", "ne", "exists", "contains", "in", "prefix")

OPERATOR_ATTRIBUTES = {
    "open": ("ref", "path", "profiles"),
    "put": ("datrix", "id", "kind", "status", "truth-state", "as", "authority", "authority-type"),
    "segue": ("datrix", "id", "from", "to", "relation", "as"),
    "select": ("datrix", "as", "truth-minimum"),
    "walk": ("datrix", "from", "relation", "direction", "depth", "truth-minimum", "as"),
    "project": ("datrix", "type", "as", "fields"),
    "union": ("refs", "as"),
    "intersect": ("refs", "as"),
    "diff": ("refs", "as"),
    "aggregate": ("source", "by", "fn", "path", "as"),
    "assert": ("ref", "path", "op", "value", "type"),
    "truth-gate": ("ref", "minimum", "allow-empty", "as"),
    "checkpoint": ("datrix",),
    "health": ("datrix", "as"),
    "explain": ("ref",),
    "payload": (),
    "metadata": (),
    "field": ("name", "value", "type"),
    "depends": ("ref",),
    "evidence-ref": ("ref",),
    "match": ("kind",),
    "where": ("path", "op", "value", "type"),
    "order": ("by", "direction"),
    "limit": ("count",),
}

REQUIRED_ATTRIBUTES = {
    "open": ("ref", "path"),
    "put": ("datrix", "id", "kind"),
    "segue": ("datrix", "id", "from", "to", "relation"),
    "select": ("datrix",),
    "walk": ("datrix", "from"),
    "union": ("refs",),
    "intersect": ("refs",),
    "diff": ("refs",),
    "aggregate": ("source",),
    "assert": ("ref", "path"),
    "truth-gate": ("ref",),
    "checkpoint": ("datrix",),
    "health": ("datrix",),
    "explain": ("ref",),
    "field": ("name",),
    "depends": ("ref",),
    "evidence-ref": ("ref",),
    "match": ("kind",),
    "where": ("path",),
    "limit": ("count",),
}

CHILD_CARDINALITY = {
    "open": {},
    "put": {"payload": (0, 1), "metadata": (0, 1)},
    "segue": {},
    "select": {"project": (0, 1), "order": (0, 1), "limit": (0, 1)},
    "walk": {},
    "project": {},
    "union": {},
    "intersect": {},
    "diff": {},
    "aggregate": {},
    "assert": {},
    "truth-gate": {},
    "checkpoint": {},
    "health": {},
    "explain": {},
    "payload": {},
    "metadata": {},
    "field": {},
    "depends": {},
    "evidence-ref": {},
    "match": {},
    "where": {},
    "order": {},
    "limit": {},
}

LITERAL_OPERATORS = ("field",)

OPERATOR_CHILDREN = {
    "open": (),
    "put": ("payload", "metadata", "depends", "evidence-ref"),
    "segue": ("field",),
    "select": ("match", "where", "project", "order", "limit"),
    "walk": (),
    "project": (),
    "union": (),
    "intersect": (),
    "diff": (),
    "aggregate": (),
    "assert": (),
    "truth-gate": (),
    "checkpoint": (),
    "health": (),
    "explain": (),
    "payload": ("field",),
    "metadata": ("field",),
    "field": ("field",),
    "depends": (),
    "evidence-ref": (),
    "match": (),
    "where": (),
    "order": (),
    "limit": (),
}


class TranslucentDatrixError(ValueError):
    pass


def _canonical(value: Any) -> str:
    try:
        return json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
    except (TypeError, ValueError) as exc:
        raise TranslucentDatrixError(f"value is not canonical-json compatible: {exc}") from exc


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _clean(value: Any, field: str) -> str:
    result = str(value or "").strip()
    if not result:
        raise TranslucentDatrixError(f"{field} is required")
    return result


def _split(value: Any) -> tuple[str, ...]:
    return tuple(part.strip() for part in str(value or "").split(",") if part.strip())


def _boolean(value: Any, default: bool = False) -> bool:
    if value is None:
        return default
    normalized = str(value).strip().casefold()
    if normalized in {"true", "1", "yes"}:
        return True
    if normalized in {"false", "0", "no"}:
        return False
    raise TranslucentDatrixError(f"invalid boolean: {value!r}")


def _strict_json(value: str) -> Any:
    def reject_constant(raw: str) -> None:
        raise ValueError(f"non-finite json number is forbidden: {raw}")

    def unique_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, item in pairs:
            if key in result:
                raise ValueError(f"duplicate json object key: {key!r}")
            result[key] = item
        return result

    try:
        parsed = json.loads(
            value,
            parse_constant=reject_constant,
            object_pairs_hook=unique_pairs,
        )
        _canonical(parsed)
        return parsed
    except (json.JSONDecodeError, ValueError, TypeError) as exc:
        raise TranslucentDatrixError(f"invalid strict json scalar: {exc}") from exc


def _scalar(value: str | None, type_name: str | None = None) -> Any:
    if value is None:
        return None
    kind = str(type_name or "string").strip().casefold()
    if kind == "string":
        return value
    if kind == "integer":
        return int(value)
    if kind == "number":
        number = float(value)
        if not math.isfinite(number):
            raise TranslucentDatrixError("number scalar must be finite")
        return number
    if kind == "boolean":
        return _boolean(value)
    if kind == "null":
        return None
    if kind == "json":
        return _strict_json(value)
    raise TranslucentDatrixError(f"unsupported scalar type: {kind}")


def _attributes(node: Mapping[str, Any]) -> dict[str, str]:
    raw = node.get("attributes")
    if not isinstance(raw, Mapping):
        return {}
    return {str(key): str(value) for key, value in raw.items()}


def _children(node: Mapping[str, Any], op: str | None = None) -> list[dict[str, Any]]:
    raw = node.get("children")
    if not isinstance(raw, list):
        return []
    children = [dict(item) for item in raw if isinstance(item, Mapping)]
    if op is None:
        return children
    return [item for item in children if item.get("op") == op]


def _first_child(node: Mapping[str, Any], op: str) -> dict[str, Any] | None:
    matches = _children(node, op)
    return matches[0] if matches else None


def _payload(node: Mapping[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for field in _children(node, "field"):
        attrs = _attributes(field)
        name = _clean(attrs.get("name"), "field.name")
        if name in result:
            raise TranslucentDatrixError(f"duplicate payload field: {name!r}")
        nested = _children(field)
        literal = field.get("literal")
        has_value = "value" in attrs
        if has_value and nested:
            raise TranslucentDatrixError(
                f"field {name!r} cannot contain both value attribute and nested fields"
            )
        if has_value and literal is not None and str(literal).strip():
            raise TranslucentDatrixError(
                f"field {name!r} cannot contain both value attribute and literal text"
            )
        if nested:
            if literal is not None and str(literal).strip():
                raise TranslucentDatrixError(
                    f"field {name!r} cannot contain literal text with nested fields"
                )
            result[name] = _payload(field)
        elif has_value:
            result[name] = _scalar(attrs.get("value"), attrs.get("type"))
        else:
            result[name] = _scalar(
                "" if literal is None else str(literal),
                attrs.get("type"),
            )
    return result


def _truth_minimum(value: Any, default: str = "unknown") -> str:
    result = str(value or default).strip().casefold()
    if result not in {"unknown", "claimed", "supported", "verified"}:
        raise TranslucentDatrixError(f"unsupported minimum truth state: {result}")
    return result


def _semantic_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        is_open_operation = value.get("op") == "open"
        return {
            key: _semantic_value(item)
            for key, item in sorted(value.items())
            if not (is_open_operation and key == "path")
        }
    if isinstance(value, list):
        return [_semantic_value(item) for item in value]
    return value


def _semantic_execution_value(result: Mapping[str, Any]) -> dict[str, Any]:
    compile_info = result.get("compile") if isinstance(result.get("compile"), Mapping) else {}
    return {
        "schema": result.get("schema"),
        "kind": result.get("kind"),
        "program_id": result.get("program_id"),
        "grammar_version": result.get("grammar_version"),
        "operations": _semantic_value(result.get("operations", [])),
        "result_refs": list(result.get("result_refs", [])),
        "compile": {
            "contract_digest": compile_info.get("contract_digest"),
            "executable_digest": compile_info.get("executable_digest"),
            "ir_digest": compile_info.get("ir_digest"),
        },
        "semantic_terms": result.get("semantic_terms"),
        "truth": _semantic_value(result.get("truth")),
        "truth_policy": result.get("truth_policy"),
        "determinism": {
            key: result.get("determinism", {}).get(key)
            for key in (
                "term_ref",
                "claim",
                "contract_digest",
                "semantic_terms_digest",
                "incidental_execution_state_excluded",
                "scope",
            )
            if isinstance(result.get("determinism"), Mapping)
        },
        "authority_effect": result.get("authority_effect"),
    }


def language_manifest(
    *, semantic_registry: SemanticIdentityRegistry | None = None,
    svg: TranslucentSVGRuntime | None = None,
) -> dict[str, Any]:
    registry = semantic_registry or semantic_identity
    svg_engine = svg or svg_runtime
    result = {
        "schema": schema,
        "kind": "translucent.datrix-dialect",
        "host": "svg+xml",
        "namespace": TL_NS,
        "grammar_versions": ["1", "2"],
        "canonical_program_location": "svg/metadata/tl:program",
        "operators": list(TOP_LEVEL_OPERATORS),
        "nested_operators": list(NESTED_OPERATORS),
        "operator_children": {
            parent: list(children)
            for parent, children in sorted(OPERATOR_CHILDREN.items())
        },
        "operator_attributes": {
            operator: list(attributes)
            for operator, attributes in sorted(OPERATOR_ATTRIBUTES.items())
        },
        "required_attributes": {
            operator: list(attributes)
            for operator, attributes in sorted(REQUIRED_ATTRIBUTES.items())
        },
        "child_cardinality": {
            parent: {
                child: [minimum, maximum]
                for child, (minimum, maximum) in sorted(children.items())
            }
            for parent, children in sorted(CHILD_CARDINALITY.items())
        },
        "literal_operators": list(LITERAL_OPERATORS),
        "where_operators": list(WHERE_OPERATORS),
        "profile_family": datrix_profile_manifest(),
        "svg_runtime": svg_engine.manifest(),
        "semantic_terms": registry.refs(
            "truth",
            "determinism",
            "runtime",
            "relationship",
            "segue",
            "provenance",
            "lineage",
            "authority",
            "evidence",
            "canon",
            "projection",
            "instance",
            "interface",
            "graph",
        ),
        "truth_policy": {
            "source_states": ["unknown", "claimed"],
            "carried_states": [
                "unknown",
                "claimed",
                "supported",
                "contested",
                "contradicted",
                "verified",
            ],
            "verification_owner": "exile:notary",
            "self_promotion": "forbidden",
        },
        "security": {
            **svg_engine.manifest()["security"],
            "path_boundary": "/root/savant-runtime",
            "result_limit": MAX_RESULTS,
            "walk_depth_limit": MAX_WALK_DEPTH,
        },
        "semantic_rule": (
            "translucent source compiles through ast and normalized ir; svg presentation "
            "projects the same canonical identities but never becomes authority"
        ),
        "authority_effect": authority_effect,
    }
    result["digest"] = _digest(result)
    return result


class TranslucentDatrixRuntime:
    def __init__(
        self,
        *,
        root: str | Path = "/root/savant-runtime",
        semantic_registry: SemanticIdentityRegistry | None = None,
        svg: TranslucentSVGRuntime | None = None,
        datrix_factory: Callable[[Path, Sequence[str]], Any] | None = None,
    ) -> None:
        self.root = Path(root).resolve()
        self.semantic_registry = semantic_registry or semantic_identity
        self.svg = svg or svg_runtime
        self.compiler = TranslucentCompiler(
            svg=self.svg,
            semantic_registry=self.semantic_registry,
        )
        self._datrix_factory = datrix_factory or (
            lambda path, profiles: DatrixInterface.open(path, tuple(profiles))
        )
        self._datrixes: dict[str, Any] = {}
        self._results: dict[str, Any] = {}
        self._default_truth_minimum = "unknown"
        self._grammar_version = "2"
        self._execute_lock = threading.RLock()

    def _safe_path(self, raw: str) -> Path:
        candidate = Path(raw)
        if not candidate.is_absolute():
            candidate = self.root / candidate
        resolved = candidate.resolve()
        try:
            resolved.relative_to(self.root)
        except ValueError as exc:
            raise TranslucentDatrixError("datrix path escapes savant runtime root") from exc
        return resolved

    def _datrix(self, ref: Any) -> Any:
        key = _clean(ref, "datrix")
        try:
            return self._datrixes[key]
        except KeyError as exc:
            raise TranslucentDatrixError(f"unknown datrix reference: {key}") from exc

    def _store_result(self, ref: Any, value: Any) -> None:
        key = str(ref or "").strip()
        if not key:
            return
        if key in self._results:
            raise TranslucentDatrixError(f"result reference already bound: {key}")
        self._results[key] = value

    def _bounded_records(self, value: Any, label: str) -> list[dict[str, Any]]:
        if not isinstance(value, Mapping):
            raise TranslucentDatrixError(f"{label} result must be a mapping")
        raw = value.get("records")
        if raw is None:
            return []
        if not isinstance(raw, list):
            raise TranslucentDatrixError(f"{label} records must be a list")
        if len(raw) > MAX_RESULTS:
            raise TranslucentDatrixError(
                f"{label} produced {len(raw)} records; maximum is {MAX_RESULTS}"
            )
        records = [dict(item) for item in raw if isinstance(item, Mapping)]
        if len(records) != len(raw):
            raise TranslucentDatrixError(f"{label} records must contain mappings only")
        count = value.get("count")
        if isinstance(count, int) and count != len(records):
            raise TranslucentDatrixError(
                f"{label} count mismatch: declared {count}, actual {len(records)}"
            )
        return records

    def _open(self, node: Mapping[str, Any]) -> dict[str, Any]:
        attrs = _attributes(node)
        ref = _clean(attrs.get("ref"), "open.ref")
        if ref in self._datrixes:
            raise TranslucentDatrixError(f"datrix reference already bound: {ref}")
        path = self._safe_path(_clean(attrs.get("path"), "open.path"))
        profiles = _split(attrs.get("profiles")) or ("knowledge",)
        self._datrixes[ref] = self._datrix_factory(path, profiles)
        result = {
            "op": "open",
            "ref": ref,
            "path": str(path),
            "profiles": list(profiles),
            "authority_effect": authority_effect,
        }
        self._store_result(ref, result)
        return result

    def _put(self, node: Mapping[str, Any]) -> dict[str, Any]:
        attrs = _attributes(node)
        datrix = self._datrix(attrs.get("datrix"))
        requested_truth = str(attrs.get("truth-state") or "unknown").casefold()
        evidence_refs = [
            _clean(_attributes(child).get("ref"), "evidence-ref.ref")
            for child in _children(node, "evidence-ref")
        ]
        try:
            truth = truth_envelope(
                state=requested_truth,
                evidence_refs=evidence_refs,
                source_ref=str(node.get("node_id") or schema),
                semantic_registry=self.semantic_registry,
            )
        except TruthError as exc:
            raise TranslucentDatrixError(str(exc)) from exc

        record: dict[str, Any] = {
            "id": _clean(attrs.get("id"), "put.id"),
            "kind": _clean(attrs.get("kind"), "put.kind"),
            "status": str(attrs.get("status") or "active"),
            "payload": {},
            "metadata": {},
            "dependencies": [],
            "relationships": [],
            "provenance": {
                "source": schema,
                "source_node": str(node.get("node_id") or ""),
            },
            "lineage": {},
            "extensions": {
                "translucent": {
                    "source": "svg",
                    "grammar_version": self._grammar_version,
                    "semantic_terms": self.semantic_registry.refs(
                        "truth",
                        "determinism",
                        "provenance",
                        "lineage",
                        "instance",
                    ),
                },
                "truth": truth,
            },
        }
        payload_node = _first_child(node, "payload")
        if payload_node is not None:
            record["payload"] = _payload(payload_node)
        metadata_node = _first_child(node, "metadata")
        if metadata_node is not None:
            record["metadata"] = _payload(metadata_node)
        for dep in _children(node, "depends"):
            record["dependencies"].append(
                _clean(_attributes(dep).get("ref"), "depends.ref")
            )
        if "authority" in attrs:
            record["authority"] = _scalar(
                attrs.get("authority"),
                attrs.get("authority-type"),
            )
        created = datrix.substantiate(record)
        result = {
            "op": "put",
            "id": created["id"],
            "digest": created["digest"],
            "truth": truth,
            "authority_effect": authority_effect,
        }
        self._store_result(attrs.get("as"), created)
        return result

    def _segue(self, node: Mapping[str, Any]) -> dict[str, Any]:
        attrs = _attributes(node)
        datrix = self._datrix(attrs.get("datrix"))
        created = datrix.relate(
            segue_id=_clean(attrs.get("id"), "segue.id"),
            source_id=_clean(attrs.get("from"), "segue.from"),
            target_id=_clean(attrs.get("to"), "segue.to"),
            relation=_clean(attrs.get("relation"), "segue.relation"),
            payload=_payload(node),
            provenance={
                "source": schema,
                "source_node": str(node.get("node_id") or ""),
                "relationship_system_ref": self.semantic_registry.ref("relationship"),
                "semantic_ref": self.semantic_registry.ref("segue"),
            },
        )
        result = {
            "op": "segue",
            "id": created["id"],
            "digest": created["digest"],
            "semantic_ref": self.semantic_registry.ref("segue"),
            "relationship_system_ref": self.semantic_registry.ref("relationship"),
            "authority_effect": authority_effect,
        }
        self._store_result(attrs.get("as"), created)
        return result

    def _where(self, node: Mapping[str, Any]) -> dict[str, Any]:
        attrs = _attributes(node)
        op = str(attrs.get("op") or "eq").casefold()
        if op not in WHERE_OPERATORS:
            raise TranslucentDatrixError(f"unsupported where operator: {op}")
        raw = attrs.get("value")
        if op == "in":
            value: Any = [
                _scalar(part.strip(), attrs.get("type"))
                for part in str(raw or "").split(",")
                if part.strip()
            ]
        elif op == "exists":
            value = _scalar(str(raw or "true"), "boolean")
        else:
            value = _scalar(raw, attrs.get("type"))
        return {
            "path": _clean(attrs.get("path"), "where.path"),
            "op": op,
            "value": value,
        }

    def _select_parameters(self, node: Mapping[str, Any]) -> dict[str, Any]:
        attrs = _attributes(node)
        kinds: list[str] = []
        where: list[dict[str, Any]] = []
        fields: tuple[str, ...] = ()
        order_by = "id"
        direction = "asc"
        limit: int | None = None
        for child in _children(node):
            op = str(child.get("op") or "")
            child_attrs = _attributes(child)
            if op == "match":
                kinds.extend(_split(child_attrs.get("kind")))
            elif op == "where":
                where.append(self._where(child))
            elif op == "project":
                fields = _split(child_attrs.get("fields"))
            elif op == "order":
                order_by = str(child_attrs.get("by") or "id")
                direction = str(child_attrs.get("direction") or "asc")
            elif op == "limit":
                limit = int(_clean(child_attrs.get("count"), "limit.count"))
            else:
                raise TranslucentDatrixError(
                    f"unsupported select child operator: {op!r}"
                )
        if limit is not None and (limit < 0 or limit > MAX_RESULTS):
            raise TranslucentDatrixError(
                f"limit must be between 0 and {MAX_RESULTS}"
            )
        minimum = _truth_minimum(
            attrs.get("truth-minimum"),
            self._default_truth_minimum,
        )
        return {
            "kinds": kinds,
            "where": where,
            "fields": fields,
            "order_by": order_by,
            "direction": direction,
            "limit": limit,
            "minimum": minimum,
        }

    def _select(self, node: Mapping[str, Any]) -> dict[str, Any]:
        attrs = _attributes(node)
        datrix = self._datrix(attrs.get("datrix"))
        params = self._select_parameters(node)
        query_args = {
            "kinds": params["kinds"],
            "where": params["where"],
            "order_by": params["order_by"],
            "direction": params["direction"],
            "limit": params["limit"],
        }
        if params["minimum"] != "unknown" and params["fields"]:
            unprojected = datrix.select(**query_args, fields=())
            unprojected_records = self._bounded_records(unprojected, "select")
            try:
                gate = require_truth(
                    unprojected_records,
                    params["minimum"],
                    allow_empty=True,
                    semantic_registry=self.semantic_registry,
                )
            except TruthError as exc:
                raise TranslucentDatrixError(str(exc)) from exc
            result = datrix.select(**query_args, fields=params["fields"])
            self._bounded_records(result, "select")
        else:
            result = datrix.select(**query_args, fields=params["fields"])
            result_records = self._bounded_records(result, "select")
            try:
                gate = require_truth(
                    result_records,
                    params["minimum"],
                    allow_empty=True,
                    semantic_registry=self.semantic_registry,
                )
            except TruthError as exc:
                raise TranslucentDatrixError(str(exc)) from exc
        out = attrs.get("as")
        self._store_result(out, result)
        return {
            "op": "select",
            "as": out,
            "count": result["count"],
            "digest": result["digest"],
            "truth_gate": gate,
            "result": result,
            "authority_effect": authority_effect,
        }

    def _walk(self, node: Mapping[str, Any]) -> dict[str, Any]:
        attrs = _attributes(node)
        datrix = self._datrix(attrs.get("datrix"))
        depth = int(str(attrs.get("depth") or "1"))
        if depth < 0 or depth > MAX_WALK_DEPTH:
            raise TranslucentDatrixError(
                f"walk depth must be between 0 and {MAX_WALK_DEPTH}"
            )
        result = datrix.neighbors(
            _clean(attrs.get("from"), "walk.from"),
            relation=attrs.get("relation"),
            direction=str(attrs.get("direction") or "both"),
            depth=depth,
        )
        minimum = _truth_minimum(
            attrs.get("truth-minimum"),
            self._default_truth_minimum,
        )
        nodes = result.get("nodes") if isinstance(result, Mapping) else None
        if nodes is not None and not isinstance(nodes, list):
            raise TranslucentDatrixError("walk nodes must be a list")
        values = nodes if isinstance(nodes, list) else []
        if len(values) > MAX_RESULTS:
            raise TranslucentDatrixError(
                f"walk produced {len(values)} nodes; maximum is {MAX_RESULTS}"
            )
        if any(not isinstance(item, Mapping) for item in values):
            raise TranslucentDatrixError("walk nodes must contain mappings only")
        edges = result.get("edges") if isinstance(result, Mapping) else None
        if edges is not None:
            if not isinstance(edges, list):
                raise TranslucentDatrixError("walk edges must be a list")
            if len(edges) > MAX_RESULTS:
                raise TranslucentDatrixError(
                    f"walk produced {len(edges)} edges; maximum is {MAX_RESULTS}"
                )
            if any(not isinstance(item, Mapping) for item in edges):
                raise TranslucentDatrixError("walk edges must contain mappings only")
        try:
            gate = require_truth(
                values,
                minimum,
                allow_empty=True,
                semantic_registry=self.semantic_registry,
            )
        except TruthError as exc:
            raise TranslucentDatrixError(str(exc)) from exc
        out = attrs.get("as")
        self._store_result(out, result)
        return {
            "op": "walk",
            "as": out,
            "nodes": len(values),
            "digest": result["digest"],
            "truth_gate": gate,
            "result": result,
            "authority_effect": authority_effect,
        }

    def _project(self, node: Mapping[str, Any]) -> dict[str, Any]:
        attrs = _attributes(node)
        datrix = self._datrix(attrs.get("datrix"))
        projection = datrix.project(_clean(attrs.get("type"), "project.type"))
        if isinstance(projection, Mapping) and "records" in projection:
            self._bounded_records(projection, "project")
        out = attrs.get("as")
        self._store_result(out, projection)
        return {
            "op": "project",
            "as": out,
            "digest": projection["digest"],
            "semantic_ref": self.semantic_registry.ref("projection"),
            "result": projection,
            "authority_effect": authority_effect,
        }

    def _result_records(self, ref: Any) -> list[dict[str, Any]]:
        key = _clean(ref, "result.ref")
        if key not in self._results:
            raise TranslucentDatrixError(f"unknown result reference: {key}")
        value = self._results[key]
        if not (isinstance(value, Mapping) and isinstance(value.get("records"), list)):
            raise TranslucentDatrixError(f"result {key!r} is not a record set")
        return self._bounded_records(value, f"result {key!r}")

    def _set_operation(self, node: Mapping[str, Any], operation: str) -> dict[str, Any]:
        attrs = _attributes(node)
        refs = _split(attrs.get("refs"))
        if len(refs) < 2:
            raise TranslucentDatrixError(f"{operation} requires at least two refs")
        sets: list[set[str]] = []
        maps: list[dict[str, dict[str, Any]]] = []
        for ref in refs:
            records = self._result_records(ref)
            mapping = {_canonical(item): item for item in records}
            maps.append(mapping)
            sets.append(set(mapping))
        if operation == "union":
            keys = set().union(*sets)
        elif operation == "intersect":
            keys = set.intersection(*sets)
        elif operation == "diff":
            keys = sets[0].difference(*sets[1:])
        else:
            raise TranslucentDatrixError(f"unknown set operation: {operation}")
        combined: dict[str, dict[str, Any]] = {}
        for mapping in maps:
            combined.update(mapping)
        records = [combined[key] for key in sorted(keys)]
        if len(records) > MAX_RESULTS:
            raise TranslucentDatrixError(
                f"{operation} produced {len(records)} records; maximum is {MAX_RESULTS}"
            )
        result = {
            "schema": "savant.translucent.record-set.v3",
            "operation": operation,
            "refs": list(refs),
            "count": len(records),
            "records": records,
            "truth": truth_summary(records, semantic_registry=self.semantic_registry),
            "authority_effect": authority_effect,
        }
        result["digest"] = _digest(result)
        out = attrs.get("as")
        self._store_result(out, result)
        return {
            "op": operation,
            "as": out,
            "count": len(records),
            "digest": result["digest"],
            "result": result,
            "authority_effect": authority_effect,
        }

    def _aggregate(self, node: Mapping[str, Any]) -> dict[str, Any]:
        attrs = _attributes(node)
        source = _clean(attrs.get("source"), "aggregate.source")
        records = self._result_records(source)
        by = str(attrs.get("by") or "").strip()
        function = str(attrs.get("fn") or "count").strip().casefold()
        path = str(attrs.get("path") or "").strip()
        groups: dict[str, list[dict[str, Any]]] = {}
        if by:
            for record in records:
                value: Any = record
                for part in by.split("."):
                    value = value.get(part) if isinstance(value, Mapping) else None
                groups.setdefault(_canonical(value), []).append(record)
        else:
            groups["null"] = records
        rows: list[dict[str, Any]] = []
        for group_key in sorted(groups):
            group_records = groups[group_key]
            group_value = json.loads(group_key)
            values: list[float | int] = []
            if path:
                for record in group_records:
                    value: Any = record
                    for part in path.split("."):
                        value = value.get(part) if isinstance(value, Mapping) else None
                    if isinstance(value, (int, float)) and not isinstance(value, bool):
                        values.append(value)
            if function == "count":
                aggregate_value: Any = len(group_records)
            elif function == "sum":
                aggregate_value = sum(values)
            elif function == "min":
                aggregate_value = min(values) if values else None
            elif function == "max":
                aggregate_value = max(values) if values else None
            elif function == "avg":
                aggregate_value = (sum(values) / len(values)) if values else None
            else:
                raise TranslucentDatrixError(
                    f"unsupported aggregate function: {function}"
                )
            if (
                isinstance(aggregate_value, float)
                and not math.isfinite(aggregate_value)
            ):
                raise TranslucentDatrixError(
                    f"aggregate {function!r} produced a non-finite number"
                )
            if len(rows) >= MAX_RESULTS:
                raise TranslucentDatrixError(
                    f"aggregate produced more than {MAX_RESULTS} groups"
                )
            rows.append(
                {
                    "group": group_value,
                    "value": aggregate_value,
                    "count": len(group_records),
                    "truth": truth_derive(
                        group_records,
                        source_ref=f"aggregate:{source}:{function}:{group_key}",
                        semantic_registry=self.semantic_registry,
                    ),
                }
            )
        result = {
            "schema": "savant.translucent.aggregate.v3",
            "source": source,
            "by": by or None,
            "function": function,
            "path": path or None,
            "rows": rows,
            "truth": truth_derive(
                records,
                source_ref=f"aggregate:{source}:{function}",
                semantic_registry=self.semantic_registry,
            ),
            "authority_effect": authority_effect,
        }
        result["digest"] = _digest(result)
        out = attrs.get("as")
        self._store_result(out, result)
        return {
            "op": "aggregate",
            "as": out,
            "digest": result["digest"],
            "result": result,
            "authority_effect": authority_effect,
        }

    def _assert(self, node: Mapping[str, Any]) -> dict[str, Any]:
        attrs = _attributes(node)
        ref = _clean(attrs.get("ref"), "assert.ref")
        if ref not in self._results:
            raise TranslucentDatrixError(f"unknown result reference: {ref}")
        value = self._results[ref]
        path = _clean(attrs.get("path"), "assert.path")
        actual: Any = value
        for part in path.split("."):
            actual = actual.get(part) if isinstance(actual, Mapping) else None
        op = str(attrs.get("op") or "eq").strip().casefold()
        expected = _scalar(attrs.get("value"), attrs.get("type"))
        passed = False
        try:
            if op == "eq":
                passed = actual == expected
            elif op == "ne":
                passed = actual != expected
            elif op == "gte":
                passed = actual is not None and actual >= expected
            elif op == "lte":
                passed = actual is not None and actual <= expected
            elif op == "exists":
                passed = (actual is not None) == bool(expected)
            else:
                raise TranslucentDatrixError(f"unsupported assert operator: {op}")
        except TypeError as exc:
            raise TranslucentDatrixError(
                f"assertion operands are not comparable for {op!r}: "
                f"{type(actual).__name__} and {type(expected).__name__}"
            ) from exc
        if not passed:
            raise TranslucentDatrixError(
                f"assertion failed for {ref}.{path}: {actual!r} {op} {expected!r}"
            )
        return {
            "op": "assert",
            "ref": ref,
            "path": path,
            "passed": True,
            "truth_state": truth_state_from_value(
                value, semantic_registry=self.semantic_registry
            ),
            "authority_effect": authority_effect,
        }

    def _truth_gate(self, node: Mapping[str, Any]) -> dict[str, Any]:
        attrs = _attributes(node)
        ref = _clean(attrs.get("ref"), "truth-gate.ref")
        if ref not in self._results:
            raise TranslucentDatrixError(f"unknown result reference: {ref}")
        value = self._results[ref]
        if isinstance(value, Mapping) and isinstance(value.get("records"), list):
            values = self._bounded_records(value, f"truth-gate {ref!r}")
        else:
            values = [value]
        minimum = _truth_minimum(
            attrs.get("minimum"),
            self._default_truth_minimum,
        )
        allow_empty = _boolean(attrs.get("allow-empty"), False)
        try:
            gate = require_truth(
                values,
                minimum,
                allow_empty=allow_empty,
                semantic_registry=self.semantic_registry,
            )
        except TruthError as exc:
            raise TranslucentDatrixError(str(exc)) from exc
        out = attrs.get("as")
        self._store_result(out, gate)
        return {
            "op": "truth-gate",
            "ref": ref,
            "as": out,
            "minimum": minimum,
            "allow_empty": allow_empty,
            "passed": True,
            "digest": gate["digest"],
            "result": gate,
            "authority_effect": authority_effect,
        }

    def _checkpoint(self, node: Mapping[str, Any]) -> dict[str, Any]:
        attrs = _attributes(node)
        datrix = self._datrix(attrs.get("datrix"))
        result = datrix.checkpoint()
        return {
            "op": "checkpoint",
            "result": result,
            "authority_effect": authority_effect,
        }

    def _health(self, node: Mapping[str, Any]) -> dict[str, Any]:
        attrs = _attributes(node)
        datrix = self._datrix(attrs.get("datrix"))
        result = datrix.health()
        out = attrs.get("as")
        self._store_result(out, result)
        return {
            "op": "health",
            "as": out,
            "status": result["status"],
            "result": result,
            "authority_effect": authority_effect,
        }

    def _explain(self, node: Mapping[str, Any]) -> dict[str, Any]:
        attrs = _attributes(node)
        ref = _clean(attrs.get("ref"), "explain.ref")
        if ref not in self._results:
            raise TranslucentDatrixError(f"unknown result reference: {ref}")
        value = self._results[ref]
        if isinstance(value, Mapping) and isinstance(value.get("records"), list):
            values = self._bounded_records(value, f"explain {ref!r}")
        else:
            values = [value]
        result = {
            "schema": "savant.translucent.explanation.v3",
            "ref": ref,
            "value_digest": _digest(value),
            "truth": truth_summary(values, semantic_registry=self.semantic_registry),
            "semantic_terms": self.semantic_registry.refs(
                "truth", "evidence", "provenance", "lineage", "projection"
            ),
            "value": value,
            "authority_effect": authority_effect,
        }
        result["digest"] = _digest(result)
        return {"op": "explain", **result}

    def _dispatch(self, node: Mapping[str, Any]) -> dict[str, Any]:
        op = str(node.get("op") or "")
        handlers: dict[str, Callable[[Mapping[str, Any]], dict[str, Any]]] = {
            "open": self._open,
            "put": self._put,
            "segue": self._segue,
            "select": self._select,
            "walk": self._walk,
            "project": self._project,
            "union": lambda item: self._set_operation(item, "union"),
            "intersect": lambda item: self._set_operation(item, "intersect"),
            "diff": lambda item: self._set_operation(item, "diff"),
            "aggregate": self._aggregate,
            "assert": self._assert,
            "truth-gate": self._truth_gate,
            "checkpoint": self._checkpoint,
            "health": self._health,
            "explain": self._explain,
        }
        handler = handlers.get(op)
        if handler is None:
            raise TranslucentDatrixError(f"unsupported translucent operator: {op}")
        return handler(node)

    def _execute_once(self, source: str | bytes) -> dict[str, Any]:
        self._datrixes = {}
        self._results = {}
        try:
            compiled = self.compiler.compile_svg(
                source,
                dialect="datrix",
                allowed_operators=TOP_LEVEL_OPERATORS,
                operator_children=OPERATOR_CHILDREN,
                operator_attributes=OPERATOR_ATTRIBUTES,
                required_attributes=REQUIRED_ATTRIBUTES,
                child_cardinality=CHILD_CARDINALITY,
                literal_operators=LITERAL_OPERATORS,
            )
        except TranslucentCompileError as exc:
            raise TranslucentDatrixError(str(exc)) from exc
        ir = compiled["ir"]
        self._grammar_version = str(compiled["grammar_version"])
        self._default_truth_minimum = _truth_minimum(ir.get("truth_minimum"))
        operations = [self._dispatch(node) for node in ir["operations"]]
        result_values: list[Any] = []
        for key in sorted(self._results):
            value = self._results[key]
            if isinstance(value, Mapping) and isinstance(value.get("records"), list):
                records = self._bounded_records(value, f"result {key!r}")
                result_values.extend(records)
        result = {
            "schema": schema,
            "kind": "translucent.execution",
            "program_id": compiled["program_id"],
            "grammar_version": compiled["grammar_version"],
            "operation_count": len(operations),
            "operations": operations,
            "result_refs": sorted(self._results),
            "compile": {
                "digest": compiled["digest"],
                "contract_digest": compiled["contract"]["digest"],
                "executable_digest": compiled["executable_digest"],
                "source_digest": compiled["source"]["digest"],
                "ast_digest": compiled["ast"]["digest"],
                "ir_digest": compiled["ir"]["digest"],
                "source_map_digest": compiled["source_map"]["digest"],
                "diagnostics_digest": compiled["diagnostics"]["digest"],
            },
            "diagnostics": compiled["diagnostics"],
            "source_map": compiled["source_map"],
            "semantic_terms": compiled["semantic_terms"],
            "truth": truth_summary(result_values, semantic_registry=self.semantic_registry),
            "truth_policy": compiled["truth_policy"],
            "determinism": {
                **compiled["determinism"],
                "scope": "compiler-and-owner-declared-datrix-projections",
            },
            "authority_effect": authority_effect,
        }
        result["semantic_digest"] = _digest(_semantic_execution_value(result))
        result["digest"] = _digest(result)
        return result

    def execute(self, source: str | bytes) -> dict[str, Any]:
        with self._execute_lock:
            return self._execute_once(source)

    def render_execution_svg(
        self,
        execution: Mapping[str, Any],
        *,
        width: int = 1280,
        row_height: int = 40,
        renderer: str | None = None,
    ) -> str:
        try:
            return self.svg.render(
                "execution",
                execution,
                renderer=renderer,
                context={"width": width, "row_height": row_height},
            )
        except TranslucentSVGError as exc:
            raise TranslucentDatrixError(str(exc)) from exc


def execute_svg(
    source: str | bytes,
    *,
    root: str | Path = "/root/savant-runtime",
) -> dict[str, Any]:
    return TranslucentDatrixRuntime(root=root).execute(source)


def selftest(registry_path: str, *, root: str | Path = "/tmp/savant-translucent-selftest") -> dict[str, Any]:
    registry = SemanticIdentityRegistry(registry_path)
    svg = TranslucentSVGRuntime(semantic_registry=registry)

    class FakeDatrix:
        def __init__(self) -> None:
            self.items: dict[str, dict[str, Any]] = {}
            self.edges: dict[str, dict[str, Any]] = {}

        def substantiate(self, record: Mapping[str, Any]) -> dict[str, Any]:
            item = json.loads(_canonical(record))
            item["digest"] = _digest(item)
            existing = self.items.get(item["id"])
            if existing is not None and existing != item:
                raise ValueError("immutable conflict")
            self.items[item["id"]] = item
            return item

        def relate(self, **kwargs: Any) -> dict[str, Any]:
            edge = {
                "id": kwargs["segue_id"],
                "from": kwargs["source_id"],
                "to": kwargs["target_id"],
                "relation": kwargs["relation"],
                "payload": kwargs.get("payload") or {},
                "provenance": kwargs.get("provenance") or {},
            }
            edge["digest"] = _digest(edge)
            self.edges[edge["id"]] = edge
            return edge

        def select(
            self,
            *,
            kinds: Sequence[str],
            where: Sequence[Mapping[str, Any]],
            order_by: str,
            direction: str,
            limit: int | None,
            fields: Sequence[str],
        ) -> dict[str, Any]:
            rows = [
                item
                for _, item in sorted(self.items.items())
                if not kinds or item.get("kind") in set(kinds)
            ]
            if limit is not None:
                rows = rows[:limit]
            if fields:
                rows = [
                    {field: item.get(field) for field in fields}
                    for item in rows
                ]
            result = {
                "schema": "fake.select",
                "count": len(rows),
                "records": rows,
                "authority_effect": "none",
            }
            result["digest"] = _digest(result)
            return result

        def neighbors(
            self,
            source_id: str,
            *,
            relation: str | None,
            direction: str,
            depth: int,
        ) -> dict[str, Any]:
            nodes = [self.items[source_id]] if source_id in self.items else []
            result = {
                "schema": "fake.walk",
                "nodes": nodes,
                "edges": list(self.edges.values()),
                "authority_effect": "none",
            }
            result["digest"] = _digest(result)
            return result

        def project(self, kind: str) -> dict[str, Any]:
            result = {
                "schema": "fake.projection",
                "kind": kind,
                "records": list(self.items.values()),
                "authority_effect": "none",
            }
            result["digest"] = _digest(result)
            return result

        def checkpoint(self) -> dict[str, Any]:
            return {"schema": "fake.checkpoint", "authority_effect": "none"}

        def health(self) -> dict[str, Any]:
            return {"schema": "fake.health", "status": "ok", "authority_effect": "none"}

    def factory(path: Path, profiles: Sequence[str]) -> FakeDatrix:
        return FakeDatrix()

    source = f'''<svg xmlns="http://www.w3.org/2000/svg" xmlns:tl="{TL_NS}" viewBox="0 0 32 32">
      <metadata>
        <tl:program id="truth-proof" grammar-version="2">
          <tl:open ref="d" path="runtime/selftest" profiles="knowledge"/>
          <tl:put datrix="d" id="a" kind="fact" truth-state="claimed" as="a">
            <tl:evidence-ref ref="evidence:selftest"/>
            <tl:payload>
              <tl:field name="value" type="integer" value="7"/>
              <tl:field name="label" type="string">  exact text  </tl:field>
            </tl:payload>
          </tl:put>
          <tl:put datrix="d" id="b" kind="fact" truth-state="claimed" as="b">
            <tl:payload><tl:field name="value" type="integer" value="9"/></tl:payload>
          </tl:put>
          <tl:segue datrix="d" id="a-to-b" from="a" to="b" relation="supports"/>
          <tl:select datrix="d" as="facts" truth-minimum="claimed">
            <tl:match kind="fact"/>
            <tl:order by="id" direction="asc"/>
          </tl:select>
          <tl:truth-gate ref="facts" minimum="claimed" as="gate"/>
          <tl:aggregate source="facts" fn="count" as="count"/>
          <tl:walk datrix="d" from="a" depth="1" truth-minimum="claimed" as="walk"/>
          <tl:project datrix="d" type="records" as="projection"/>
          <tl:health datrix="d" as="health"/>
          <tl:explain ref="facts"/>
        </tl:program>
      </metadata>
    </svg>'''

    first_runtime = TranslucentDatrixRuntime(
        root=root,
        semantic_registry=registry,
        svg=svg,
        datrix_factory=factory,
    )
    second_runtime = TranslucentDatrixRuntime(
        root=root,
        semantic_registry=registry,
        svg=svg,
        datrix_factory=factory,
    )
    first = first_runtime.execute(source)
    second = second_runtime.execute(source)
    rendered_a = first_runtime.render_execution_svg(first)
    rendered_b = first_runtime.render_execution_svg(first)

    checks = {
        "stable_execution": first["semantic_digest"] == second["semantic_digest"],
        "compiled_ir": bool(first["compile"]["ir_digest"]),
        "contract_bound": bool(first["compile"]["contract_digest"]),
        "executable_bound": bool(first["compile"]["executable_digest"]),
        "source_map": first["source_map"]["entries"] != {},
        "truth_claimed_preserved": first["truth"]["state"] == "claimed",
        "truth_gate_passed": any(
            item.get("op") == "truth-gate" and item.get("passed")
            for item in first["operations"]
        ),
        "typed_segue": any(
            item.get("op") == "segue"
            and item.get("semantic_ref") == "lex:core:segue"
            for item in first["operations"]
        ),
        "projection_bound": any(
            item.get("op") == "project"
            and item.get("semantic_ref") == "lex:core:wavre"
            for item in first["operations"]
        ),
        "truth_bound": first["semantic_terms"]["truth"] == "lex:core:truth",
        "determinism_bound": first["semantic_terms"]["determinism"] == "lex:core:determinism",
        "authority_none": first["authority_effect"] == "none",
        "renderer_stable": rendered_a == rendered_b,
        "renderer_uses_symbols": "<symbol" in rendered_a and "<use" in rendered_a,
        "literal_whitespace_preserved": (
            first_runtime._results["a"]["payload"]["label"] == "  exact text  "
        ),
    }

    visual_source = source.replace(
        "</svg>",
        '<rect x="0" y="0" width="1" height="1"/></svg>',
    )
    visual_runtime = TranslucentDatrixRuntime(
        root=root,
        semantic_registry=registry,
        svg=svg,
        datrix_factory=factory,
    )
    visual_result = visual_runtime.execute(visual_source)
    checks["presentation_excluded_from_semantic_digest"] = (
        first["semantic_digest"] == visual_result["semantic_digest"]
        and first["digest"] != visual_result["digest"]
    )

    try:
        _scalar("nan", "number")
        checks["nonfinite_number_rejected"] = False
    except TranslucentDatrixError:
        checks["nonfinite_number_rejected"] = True

    try:
        _scalar('{"a":1,"a":2}', "json")
        checks["duplicate_json_key_rejected"] = False
    except TranslucentDatrixError:
        checks["duplicate_json_key_rejected"] = True

    duplicate_field = source.replace(
        '<tl:field name="value" type="integer" value="7"/>',
        '<tl:field name="value" type="integer" value="7"/>'
        '<tl:field name="value" type="integer" value="8"/>',
        1,
    )
    duplicate_field_runtime = TranslucentDatrixRuntime(
        root=root, semantic_registry=registry, svg=svg, datrix_factory=factory
    )
    try:
        duplicate_field_runtime.execute(duplicate_field)
        checks["duplicate_payload_field_rejected"] = False
    except TranslucentDatrixError:
        checks["duplicate_payload_field_rejected"] = True

    duplicate_ref = source.replace('as="health"', 'as="facts"', 1)
    duplicate_ref_runtime = TranslucentDatrixRuntime(
        root=root, semantic_registry=registry, svg=svg, datrix_factory=factory
    )
    try:
        duplicate_ref_runtime.execute(duplicate_ref)
        checks["duplicate_result_ref_rejected"] = False
    except TranslucentDatrixError:
        checks["duplicate_result_ref_rejected"] = True

    empty_gate = source.replace('<tl:match kind="fact"/>', '<tl:match kind="missing"/>', 1)
    empty_gate_runtime = TranslucentDatrixRuntime(
        root=root, semantic_registry=registry, svg=svg, datrix_factory=factory
    )
    try:
        empty_gate_runtime.execute(empty_gate)
        checks["empty_explicit_truth_gate_rejected"] = False
    except TranslucentDatrixError:
        checks["empty_explicit_truth_gate_rejected"] = True

    empty_gate_allowed = empty_gate.replace(
        '<tl:truth-gate ref="facts" minimum="claimed" as="gate"/>',
        '<tl:truth-gate ref="facts" minimum="claimed" allow-empty="true" as="gate"/>',
        1,
    )
    empty_allowed_runtime = TranslucentDatrixRuntime(
        root=root, semantic_registry=registry, svg=svg, datrix_factory=factory
    )
    try:
        empty_allowed_runtime.execute(empty_gate_allowed)
        checks["empty_truth_gate_explicit_override"] = True
    except TranslucentDatrixError:
        checks["empty_truth_gate_explicit_override"] = False

    bad = source.replace('truth-state="claimed"', 'truth-state="verified"', 1)
    bad_runtime = TranslucentDatrixRuntime(
        root=root,
        semantic_registry=registry,
        svg=svg,
        datrix_factory=factory,
    )
    try:
        bad_runtime.execute(bad)
        checks["truth_self_promotion_rejected"] = False
    except TranslucentDatrixError:
        checks["truth_self_promotion_rejected"] = True

    result = {
        "schema": "savant.translucent.datrix-language-selftest.v3",
        "ok": all(checks.values()),
        "checks": checks,
        "semantic_digest": first["semantic_digest"],
        "render_digest": hashlib.sha256(rendered_a.encode("utf-8")).hexdigest(),
        "authority_effect": authority_effect,
    }
    result["digest"] = _digest(result)
    return result


__all__ = [
    "MAX_RESULTS",
    "TOP_LEVEL_OPERATORS",
    "OPERATOR_CHILDREN",
    "OPERATOR_ATTRIBUTES",
    "REQUIRED_ATTRIBUTES",
    "CHILD_CARDINALITY",
    "LITERAL_OPERATORS",
    "TranslucentDatrixError",
    "TranslucentDatrixRuntime",
    "execute_svg",
    "language_manifest",
    "schema",
    "selftest",
]
