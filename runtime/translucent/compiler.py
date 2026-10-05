#!/usr/bin/env python3

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Iterable, Mapping
from xml.etree import ElementTree as ET

from lexicon.semantic_identity import SemanticIdentityRegistry, semantic_identity
from runtime.translucent.svg import TL_NS, TranslucentSVGError, TranslucentSVGRuntime, svg_runtime


schema = "savant.translucent.compiler.v3"
authority_effect = "none"


class TranslucentCompileError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class CompileLimits:
    max_operations: int = 10_000
    max_operation_depth: int = 64
    max_operation_attributes: int = 128
    max_literal_chars: int = 1_000_000
    max_identifier_chars: int = 256


_ALLOWED_MINIMUM_TRUTH = frozenset({"unknown", "claimed", "supported", "verified"})


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
        raise TranslucentCompileError(f"value is not canonical-json compatible: {exc}") from exc


def _digest(value: Any) -> str:
    if isinstance(value, str):
        raw = value.encode("utf-8")
    else:
        raw = _canonical(value).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _split_tag(tag: str) -> tuple[str, str]:
    if tag.startswith("{") and "}" in tag:
        namespace, local = tag[1:].split("}", 1)
        return namespace, local
    return "", tag


def _local(tag: str) -> str:
    return _split_tag(tag)[1]


def _truth_minimum(value: Any, field: str) -> str:
    state = str(value or "unknown").strip().casefold()
    if state not in _ALLOWED_MINIMUM_TRUTH:
        raise TranslucentCompileError(
            f"{field} must be one of {sorted(_ALLOWED_MINIMUM_TRUTH)}, got {state!r}"
        )
    return state


def _normalize_attributes(node: ET.Element) -> dict[str, str]:
    return {
        _local(name): str(value)
        for name, value in sorted(node.attrib.items(), key=lambda item: item[0])
    }


def _normalize_string_set_map(
    value: Mapping[str, Iterable[str]] | None,
) -> dict[str, frozenset[str]] | None:
    if value is None:
        return None
    return {
        str(key).strip(): frozenset(
            str(item).strip() for item in items if str(item).strip()
        )
        for key, items in value.items()
        if str(key).strip()
    }


def _normalize_cardinality(
    value: Mapping[str, Mapping[str, tuple[int, int | None]]] | None,
) -> dict[str, dict[str, tuple[int, int | None]]] | None:
    if value is None:
        return None
    result: dict[str, dict[str, tuple[int, int | None]]] = {}
    for parent, children in value.items():
        parent_key = str(parent).strip()
        if not parent_key:
            continue
        normalized_children: dict[str, tuple[int, int | None]] = {}
        for child, bounds in children.items():
            child_key = str(child).strip()
            if not child_key:
                continue
            if not isinstance(bounds, tuple) or len(bounds) != 2:
                raise TranslucentCompileError(
                    f"invalid child cardinality for {parent_key}.{child_key}"
                )
            minimum, maximum = bounds
            if minimum < 0 or (maximum is not None and maximum < minimum):
                raise TranslucentCompileError(
                    f"invalid child cardinality for {parent_key}.{child_key}: {bounds!r}"
                )
            normalized_children[child_key] = (int(minimum), maximum)
        result[parent_key] = normalized_children
    return result


class TranslucentCompiler:
    def __init__(
        self,
        *,
        svg: TranslucentSVGRuntime | None = None,
        semantic_registry: SemanticIdentityRegistry | None = None,
        limits: CompileLimits | None = None,
    ) -> None:
        self.semantic_registry = semantic_registry or semantic_identity
        self.svg = svg or svg_runtime
        self.limits = limits or CompileLimits()

    def semantic_terms(self) -> dict[str, str]:
        return self.semantic_registry.refs(
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
        )

    def manifest(self) -> dict[str, Any]:
        result = {
            "schema": schema,
            "stages": [
                "secure-svg-parse",
                "ast",
                "normalized-ir",
                "semantic-validation",
                "source-map",
                "diagnostics",
            ],
            "grammar_versions": ["1", "2"],
            "host_execution": "forbidden",
            "semantic_terms": self.semantic_terms(),
            "registry_digest": self.semantic_registry.registry_digest,
            "limits": {
                field: getattr(self.limits, field)
                for field in self.limits.__dataclass_fields__
            },
            "authority_effect": authority_effect,
        }
        result["digest"] = _digest(result)
        return result

    def _ast_node(
        self,
        node: ET.Element,
        *,
        path: str,
        depth: int,
        source_map: dict[str, dict[str, Any]],
        literal_counter: list[int],
        operation_counter: list[int],
        operator_children: Mapping[str, frozenset[str]] | None,
        operator_attributes: Mapping[str, frozenset[str]] | None,
        required_attributes: Mapping[str, frozenset[str]] | None,
        child_cardinality: Mapping[str, Mapping[str, tuple[int, int | None]]] | None,
        literal_operators: frozenset[str] | None,
    ) -> dict[str, Any]:
        if depth > self.limits.max_operation_depth:
            raise TranslucentCompileError(
                f"translucent operation tree exceeds depth {self.limits.max_operation_depth}"
            )

        namespace, local = _split_tag(node.tag)
        if namespace != TL_NS:
            raise TranslucentCompileError(
                f"executable translucent tree contains non-translucent element: {node.tag!r}"
            )

        operation_counter[0] += 1
        if operation_counter[0] > self.limits.max_operations:
            raise TranslucentCompileError(
                f"translucent program exceeds {self.limits.max_operations} executable nodes"
            )

        if len(node.attrib) > self.limits.max_operation_attributes:
            raise TranslucentCompileError(
                f"operator {local!r} exceeds {self.limits.max_operation_attributes} attributes"
            )

        attributes = _normalize_attributes(node)
        if operator_attributes is not None:
            admitted_attributes = operator_attributes.get(local)
            if admitted_attributes is None:
                raise TranslucentCompileError(
                    f"dialect attribute contract is missing operator {local!r}"
                )
            unexpected = sorted(set(attributes) - admitted_attributes)
            if unexpected:
                raise TranslucentCompileError(
                    f"operator {local!r} has unsupported attributes: {unexpected!r}"
                )
        if required_attributes is not None:
            required = required_attributes.get(local, frozenset())
            missing = sorted(required - set(attributes))
            if missing:
                raise TranslucentCompileError(
                    f"operator {local!r} is missing required attributes: {missing!r}"
                )

        raw_text = str(node.text or "")
        literal_counter[0] += len(raw_text)
        literal_counter[0] += sum(len(str(value)) for value in node.attrib.values())
        if literal_counter[0] > self.limits.max_literal_chars:
            raise TranslucentCompileError(
                f"translucent executable literals exceed {self.limits.max_literal_chars} characters"
            )

        if literal_operators is None:
            literal: str | None = raw_text.strip() or None
        elif local in literal_operators:
            literal = raw_text if raw_text != "" else None
        else:
            if raw_text.strip():
                raise TranslucentCompileError(
                    f"operator {local!r} does not admit literal text"
                )
            literal = None

        node_id = f"ast:{len(source_map):06d}"
        source_map[node_id] = {
            "path": path,
            "tag": local,
            "depth": depth,
            "source_kind": "svg-element-path",
        }

        children: list[dict[str, Any]] = []
        local_counts: dict[str, int] = {}
        for child in list(node):
            child_ns, child_local = _split_tag(child.tag)
            if child_ns != TL_NS:
                raise TranslucentCompileError(
                    f"operator {local!r} contains non-translucent child: {child.tag!r}"
                )
            if operator_children is not None:
                admitted_children = operator_children.get(local, frozenset())
                if child_local not in admitted_children:
                    raise TranslucentCompileError(
                        f"operator {local!r} does not admit child {child_local!r}"
                    )
            local_counts[child_local] = local_counts.get(child_local, 0) + 1
            child_path = f"{path}/tl:{child_local}[{local_counts[child_local]}]"
            children.append(
                self._ast_node(
                    child,
                    path=child_path,
                    depth=depth + 1,
                    source_map=source_map,
                    literal_counter=literal_counter,
                    operation_counter=operation_counter,
                    operator_children=operator_children,
                    operator_attributes=operator_attributes,
                    required_attributes=required_attributes,
                    child_cardinality=child_cardinality,
                    literal_operators=literal_operators,
                )
            )

        if child_cardinality is not None:
            constraints = child_cardinality.get(local, {})
            for child_local, (minimum, maximum) in sorted(constraints.items()):
                count = local_counts.get(child_local, 0)
                if count < minimum:
                    raise TranslucentCompileError(
                        f"operator {local!r} requires at least {minimum} child {child_local!r}"
                    )
                if maximum is not None and count > maximum:
                    raise TranslucentCompileError(
                        f"operator {local!r} allows at most {maximum} child {child_local!r}"
                    )

        return {
            "node_id": node_id,
            "tag": local,
            "attributes": attributes,
            "text": literal,
            "children": children,
        }

    def _normalize_ir_node(self, ast: Mapping[str, Any]) -> dict[str, Any]:
        attributes = dict(ast.get("attributes") or {})
        if "truth-minimum" in attributes:
            attributes["truth-minimum"] = _truth_minimum(
                attributes["truth-minimum"],
                f"{ast.get('node_id')}.truth-minimum",
            )
        children = [
            self._normalize_ir_node(child)
            for child in ast.get("children", [])
            if isinstance(child, Mapping)
        ]
        result = {
            "node_id": str(ast.get("node_id") or ""),
            "op": str(ast.get("tag") or ""),
            "attributes": dict(sorted(attributes.items())),
            "literal": ast.get("text"),
            "children": children,
        }
        result["digest"] = _digest(result)
        return result

    def compile_svg(
        self,
        source: str | bytes,
        *,
        dialect: str,
        allowed_operators: Iterable[str],
        operator_children: Mapping[str, Iterable[str]] | None = None,
        operator_attributes: Mapping[str, Iterable[str]] | None = None,
        required_attributes: Mapping[str, Iterable[str]] | None = None,
        child_cardinality: Mapping[str, Mapping[str, tuple[int, int | None]]] | None = None,
        literal_operators: Iterable[str] | None = None,
    ) -> dict[str, Any]:
        dialect_name = str(dialect or "").strip()
        if not dialect_name:
            raise TranslucentCompileError("dialect is required")

        try:
            root = self.svg.parse(source)
            program = self.svg.program(root)
            canonical_source = self.svg.canonicalize(root)
        except TranslucentSVGError as exc:
            raise TranslucentCompileError(str(exc)) from exc

        program_attributes = _normalize_attributes(program)
        admitted_program_attributes = {"id", "grammar-version", "grammar", "truth-minimum"}
        unexpected_program_attributes = sorted(
            set(program_attributes) - admitted_program_attributes
        )
        if unexpected_program_attributes:
            raise TranslucentCompileError(
                "program has unsupported attributes: "
                + repr(unexpected_program_attributes)
            )
        grammar_declared = program.get("grammar")
        grammar_version_declared = program.get("grammar-version")
        if (
            grammar_declared is not None
            and grammar_version_declared is not None
            and str(grammar_declared).strip() != str(grammar_version_declared).strip()
        ):
            raise TranslucentCompileError(
                "program grammar and grammar-version attributes conflict"
            )

        grammar_version = str(
            grammar_version_declared or grammar_declared or "1"
        ).strip()
        if grammar_version not in {"1", "2"}:
            raise TranslucentCompileError(
                f"unsupported translucent grammar version: {grammar_version!r}"
            )

        program_id = str(program.get("id") or "program").strip() or "program"
        if len(program_id) > self.limits.max_identifier_chars:
            raise TranslucentCompileError(
                f"program id exceeds {self.limits.max_identifier_chars} characters"
            )
        program_truth_minimum = _truth_minimum(
            program.get("truth-minimum"),
            "program.truth-minimum",
        )

        allowed = frozenset(
            str(item).strip() for item in allowed_operators if str(item).strip()
        )
        if not allowed:
            raise TranslucentCompileError("dialect must expose at least one top-level operator")

        child_contract = _normalize_string_set_map(operator_children)
        attribute_contract = _normalize_string_set_map(operator_attributes)
        required_contract = _normalize_string_set_map(required_attributes)
        cardinality_contract = _normalize_cardinality(child_cardinality)
        literal_contract = (
            None
            if literal_operators is None
            else frozenset(
                str(item).strip() for item in literal_operators if str(item).strip()
            )
        )

        if child_contract is not None:
            missing_parents = sorted(allowed - set(child_contract))
            if missing_parents:
                raise TranslucentCompileError(
                    "dialect child contract is missing top-level operators: "
                    + ", ".join(missing_parents)
                )
        if attribute_contract is not None:
            missing_attributes = sorted(allowed - set(attribute_contract))
            if missing_attributes:
                raise TranslucentCompileError(
                    "dialect attribute contract is missing top-level operators: "
                    + ", ".join(missing_attributes)
                )
        if required_contract is not None and attribute_contract is not None:
            for operator, required in required_contract.items():
                admitted = attribute_contract.get(operator)
                if admitted is not None and not required.issubset(admitted):
                    raise TranslucentCompileError(
                        f"required attributes for {operator!r} are not admitted by its attribute contract"
                    )

        contract = {
            "schema": "savant.translucent.dialect-contract.v1",
            "dialect": dialect_name,
            "top_level_operators": sorted(allowed),
            "children": (
                None
                if child_contract is None
                else {key: sorted(value) for key, value in sorted(child_contract.items())}
            ),
            "attributes": (
                None
                if attribute_contract is None
                else {key: sorted(value) for key, value in sorted(attribute_contract.items())}
            ),
            "required_attributes": (
                None
                if required_contract is None
                else {key: sorted(value) for key, value in sorted(required_contract.items())}
            ),
            "child_cardinality": (
                None
                if cardinality_contract is None
                else {
                    parent: {
                        child: [minimum, maximum]
                        for child, (minimum, maximum) in sorted(children.items())
                    }
                    for parent, children in sorted(cardinality_contract.items())
                }
            ),
            "literal_operators": None if literal_contract is None else sorted(literal_contract),
            "authority_effect": authority_effect,
        }
        contract["digest"] = _digest(contract)

        top_level = list(program)
        source_map: dict[str, dict[str, Any]] = {}
        literal_counter = [0]
        operation_counter = [0]
        ast_operations: list[dict[str, Any]] = []
        local_counts: dict[str, int] = {}
        diagnostics: list[dict[str, Any]] = []

        if grammar_version == "1":
            diagnostics.append(
                {
                    "code": "grammar-v1-compatibility",
                    "severity": "info",
                    "message": "grammar version 1 is accepted through compatibility semantics",
                }
            )

        for node in top_level:
            namespace, local = _split_tag(node.tag)
            if namespace != TL_NS:
                raise TranslucentCompileError(
                    f"program contains non-translucent executable element: {node.tag!r}"
                )
            if local not in allowed:
                raise TranslucentCompileError(
                    f"operator {local!r} is not admitted by dialect {dialect_name!r}"
                )
            local_counts[local] = local_counts.get(local, 0) + 1
            path = (
                f"/svg:svg/svg:metadata/tl:program/tl:{local}"
                f"[{local_counts[local]}]"
            )
            ast_operations.append(
                self._ast_node(
                    node,
                    path=path,
                    depth=1,
                    source_map=source_map,
                    literal_counter=literal_counter,
                    operation_counter=operation_counter,
                    operator_children=child_contract,
                    operator_attributes=attribute_contract,
                    required_attributes=required_contract,
                    child_cardinality=cardinality_contract,
                    literal_operators=literal_contract,
                )
            )

        ast = {
            "schema": "savant.translucent.ast.v3",
            "dialect": dialect_name,
            "grammar_version": grammar_version,
            "program_id": program_id,
            "truth_minimum": program_truth_minimum,
            "operation_count": operation_counter[0],
            "contract_digest": contract["digest"],
            "operations": ast_operations,
            "semantic_terms": self.semantic_terms(),
            "authority_effect": authority_effect,
        }
        ast["digest"] = _digest(ast)

        ir_operations = [self._normalize_ir_node(item) for item in ast_operations]
        ir = {
            "schema": "savant.translucent.ir.v3",
            "dialect": dialect_name,
            "grammar_version": grammar_version,
            "program_id": program_id,
            "truth_minimum": program_truth_minimum,
            "operation_count": operation_counter[0],
            "contract_digest": contract["digest"],
            "operations": ir_operations,
            "semantic_terms": self.semantic_terms(),
            "authority_effect": authority_effect,
        }
        ir["digest"] = _digest(ir)

        source_map_result = {
            "schema": "savant.translucent.source-map.v3",
            "kind": "svg-element-path",
            "entries": {key: source_map[key] for key in sorted(source_map)},
            "authority_effect": authority_effect,
        }
        source_map_result["digest"] = _digest(source_map_result)

        diagnostics_result = {
            "schema": "savant.translucent.diagnostics.v3",
            "count": len(diagnostics),
            "items": diagnostics,
            "authority_effect": authority_effect,
        }
        diagnostics_result["digest"] = _digest(diagnostics_result)

        compiler_manifest = self.manifest()
        semantic_terms_digest = _digest(self.semantic_terms())
        executable_digest = _digest(
            {
                "compiler_schema": schema,
                "contract_digest": contract["digest"],
                "ir_digest": ir["digest"],
                "semantic_terms_digest": semantic_terms_digest,
            }
        )

        result = {
            "schema": schema,
            "dialect": dialect_name,
            "grammar_version": grammar_version,
            "program_id": program_id,
            "source": {
                "kind": "svg+xml",
                "canonicalization": "xml-c14n-2.0",
                "digest": _digest(canonical_source),
            },
            "contract": contract,
            "executable_digest": executable_digest,
            "ast": ast,
            "ir": ir,
            "source_map": source_map_result,
            "diagnostics": diagnostics_result,
            "semantic_terms": self.semantic_terms(),
            "truth_policy": {
                "term_ref": self.semantic_registry.ref("truth"),
                "minimum": program_truth_minimum,
                "self_promotion": "forbidden",
            },
            "determinism": {
                "term_ref": self.semantic_registry.ref("determinism"),
                "claim": "semantic-reproducibility",
                "contract_digest": contract["digest"],
                "semantic_terms_digest": semantic_terms_digest,
                "registry_digest": self.semantic_registry.registry_digest,
                "compiler_manifest_digest": compiler_manifest["digest"],
                "incidental_execution_state_excluded": True,
            },
            "authority_effect": authority_effect,
        }
        result["digest"] = _digest(result)
        return result


def selftest(registry_path: str) -> dict[str, Any]:
    registry = SemanticIdentityRegistry(registry_path)
    svg = TranslucentSVGRuntime(semantic_registry=registry)
    compiler = TranslucentCompiler(svg=svg, semantic_registry=registry)
    source = f'''<svg xmlns="http://www.w3.org/2000/svg" xmlns:tl="{TL_NS}">
      <metadata>
        <tl:program id="p" grammar-version="2" truth-minimum="claimed">
          <tl:open ref="d" path="runtime/data" profiles="knowledge"/>
          <tl:health datrix="d" as="h"/>
        </tl:program>
      </metadata>
    </svg>'''
    allowed = {"open", "health"}
    child_contract = {"open": (), "health": ()}
    attribute_contract = {
        "open": ("ref", "path", "profiles"),
        "health": ("datrix", "as"),
    }
    required_contract = {
        "open": ("ref", "path"),
        "health": ("datrix",),
    }
    cardinality = {"open": {}, "health": {}}
    compile_args = {
        "dialect": "datrix",
        "allowed_operators": allowed,
        "operator_children": child_contract,
        "operator_attributes": attribute_contract,
        "required_attributes": required_contract,
        "child_cardinality": cardinality,
        "literal_operators": (),
    }
    first = compiler.compile_svg(source, **compile_args)
    second = compiler.compile_svg(source, **compile_args)
    checks = {
        "stable_compile": first["digest"] == second["digest"],
        "stable_ir": first["ir"]["digest"] == second["ir"]["digest"],
        "stable_executable": first["executable_digest"] == second["executable_digest"],
        "ast_present": len(first["ast"]["operations"]) == 2,
        "all_operations_counted": first["ast"]["operation_count"] == 2,
        "source_map_present": len(first["source_map"]["entries"]) == 2,
        "diagnostics_empty": first["diagnostics"]["count"] == 0,
        "contract_bound": first["contract"]["digest"] == first["ir"]["contract_digest"],
        "truth_bound": first["semantic_terms"]["truth"] == "lex:core:truth",
        "determinism_bound": first["semantic_terms"]["determinism"] == "lex:core:determinism",
        "truth_minimum": first["truth_policy"]["minimum"] == "claimed",
        "authority_none": first["authority_effect"] == "none",
    }

    bad = source.replace("<tl:health", "<tl:execute-host")
    try:
        compiler.compile_svg(bad, **compile_args)
        checks["unknown_operator_rejected"] = False
    except TranslucentCompileError:
        checks["unknown_operator_rejected"] = True

    bad_attribute = source.replace('as="h"', 'as="h" typo="x"')
    try:
        compiler.compile_svg(bad_attribute, **compile_args)
        checks["unknown_attribute_rejected"] = False
    except TranslucentCompileError:
        checks["unknown_attribute_rejected"] = True

    missing_attribute = source.replace(' datrix="d" as="h"', ' as="h"')
    try:
        compiler.compile_svg(missing_attribute, **compile_args)
        checks["missing_required_attribute_rejected"] = False
    except TranslucentCompileError:
        checks["missing_required_attribute_rejected"] = True

    nested_bad = source.replace(
        '<tl:health datrix="d" as="h"/>',
        '<tl:health datrix="d" as="h"><tl:field name="x" value="1"/></tl:health>',
    )
    try:
        compiler.compile_svg(nested_bad, **compile_args)
        checks["unknown_nested_operator_rejected"] = False
    except TranslucentCompileError:
        checks["unknown_nested_operator_rejected"] = True

    text_bad = source.replace(
        '<tl:health datrix="d" as="h"/>',
        '<tl:health datrix="d" as="h">unexpected</tl:health>',
    )
    try:
        compiler.compile_svg(text_bad, **compile_args)
        checks["unexpected_literal_rejected"] = False
    except TranslucentCompileError:
        checks["unexpected_literal_rejected"] = True

    bad_program_attribute = source.replace(
        'truth-minimum="claimed"',
        'truth-minimum="claimed" typo="x"',
    )
    try:
        compiler.compile_svg(bad_program_attribute, **compile_args)
        checks["unknown_program_attribute_rejected"] = False
    except TranslucentCompileError:
        checks["unknown_program_attribute_rejected"] = True

    conflicting_grammar = source.replace(
        'grammar-version="2"',
        'grammar-version="2" grammar="1"',
    )
    try:
        compiler.compile_svg(conflicting_grammar, **compile_args)
        checks["conflicting_grammar_rejected"] = False
    except TranslucentCompileError:
        checks["conflicting_grammar_rejected"] = True

    try:
        _truth_minimum("contested", "selftest")
        checks["invalid_minimum_rejected"] = False
    except TranslucentCompileError:
        checks["invalid_minimum_rejected"] = True

    result = {
        "schema": "savant.translucent.compiler-selftest.v3",
        "ok": all(checks.values()),
        "checks": checks,
        "source_digest": first["source"]["digest"],
        "contract_digest": first["contract"]["digest"],
        "ast_digest": first["ast"]["digest"],
        "ir_digest": first["ir"]["digest"],
        "executable_digest": first["executable_digest"],
        "authority_effect": authority_effect,
    }
    result["digest"] = _digest(result)
    return result


compiler = TranslucentCompiler()


__all__ = [
    "CompileLimits",
    "TranslucentCompileError",
    "TranslucentCompiler",
    "compiler",
    "schema",
    "selftest",
]
