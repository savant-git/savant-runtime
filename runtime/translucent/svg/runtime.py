#!/usr/bin/env python3

from __future__ import annotations

import hashlib
import json
import math
import re
import threading
from dataclasses import dataclass
from typing import Any, Mapping, Protocol
from xml.etree import ElementTree as ET

from lexicon.semantic_identity import SemanticIdentityRegistry, semantic_identity

try:
    from defusedxml import ElementTree as DET  # type: ignore
except Exception:  # pragma: no cover - optional hardening only
    DET = None


schema = "savant.translucent.svg.v3"
authority_effect = "none"

SVG_NS = "http://www.w3.org/2000/svg"
TL_NS = "urn:savant:translucent"
XLINK_NS = "http://www.w3.org/1999/xlink"
XML_NS = "http://www.w3.org/XML/1998/namespace"
NS = {"svg": SVG_NS, "tl": TL_NS}

ET.register_namespace("", SVG_NS)
ET.register_namespace("tl", TL_NS)


class TranslucentSVGError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class SVGLimits:
    max_source_bytes: int = 2_000_000
    max_nodes: int = 20_000
    max_depth: int = 128
    max_attributes: int = 128_000
    max_text_chars: int = 2_000_000
    max_attribute_chars: int = 4_000_000
    max_render_operations: int = 10_000


class RendererBackend(Protocol):
    def __call__(
        self,
        kind: str,
        payload: Mapping[str, Any],
        context: Mapping[str, Any],
        runtime: "TranslucentSVGRuntime",
    ) -> str: ...


_FORBIDDEN_DECLARATIONS = re.compile(r"<!\s*(?:DOCTYPE|ENTITY)\b", re.IGNORECASE)
_URL_RE = re.compile(r"url\((.*?)\)", re.IGNORECASE)
_ID_RE = re.compile(r"[^a-zA-Z0-9_.:-]+")

_FORBIDDEN_SVG_ELEMENTS = frozenset({"script", "foreignObject", "iframe", "object", "embed", "style"})
_REFERENCE_ATTRIBUTES = frozenset({"href", f"{{{XLINK_NS}}}href"})
_URL_ATTRIBUTES = frozenset(
    {
        "clip-path",
        "cursor",
        "fill",
        "filter",
        "marker",
        "marker-end",
        "marker-mid",
        "marker-start",
        "mask",
        "stroke",
        "style",
    }
)


def _canonical_json(value: Any) -> str:
    try:
        return json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
    except (TypeError, ValueError) as exc:
        raise TranslucentSVGError(f"value is not canonical-json compatible: {exc}") from exc


def _digest(value: Any) -> str:
    if isinstance(value, bytes):
        data = value
    elif isinstance(value, str):
        data = value.encode("utf-8")
    else:
        data = _canonical_json(value).encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def _split_tag(tag: str) -> tuple[str, str]:
    if tag.startswith("{") and "}" in tag:
        namespace, local = tag[1:].split("}", 1)
        return namespace, local
    return "", tag


def _local_name(name: str) -> str:
    return _split_tag(name)[1]


def _safe_id(value: Any, *, prefix: str = "tl") -> str:
    raw = _ID_RE.sub("-", str(value or "").strip()).strip("-.:_")
    if not raw:
        raw = "item"
    if not (raw[0].isalpha() or raw[0] == "_"):
        raw = f"{prefix}-{raw}"
    return raw[:160]


def _is_fragment_ref(value: str) -> bool:
    stripped = value.strip()
    return bool(stripped) and stripped.startswith("#") and len(stripped) > 1


def _urls_are_local(value: str) -> bool:
    for match in _URL_RE.finditer(value):
        target = match.group(1).strip().strip("'\"")
        if not _is_fragment_ref(target):
            return False
    return True


def _fragment_targets(value: str) -> tuple[str, ...]:
    targets: list[str] = []
    stripped = value.strip()
    if _is_fragment_ref(stripped):
        targets.append(stripped[1:])
    for match in _URL_RE.finditer(value):
        target = match.group(1).strip().strip("'\"")
        if _is_fragment_ref(target):
            targets.append(target[1:])
    return tuple(targets)


def _bounded_int(value: Any, *, default: int, minimum: int, maximum: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        parsed = default
    return max(minimum, min(maximum, parsed))


def _finite_number(value: Any, default: float = 0.0) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    return number if math.isfinite(number) else default


def _escape_text(value: Any) -> str:
    return str(value or "")


class TranslucentSVGRuntime:
    def __init__(
        self,
        *,
        limits: SVGLimits | None = None,
        semantic_registry: SemanticIdentityRegistry | None = None,
    ) -> None:
        self.limits = limits or SVGLimits()
        self.semantic_registry = semantic_registry or semantic_identity
        self._renderers: dict[str, RendererBackend] = {}
        self._renderer_lock = threading.RLock()
        self.register_renderer("projection", _projection_renderer, replace=True)
        self.register_renderer("advanced", _advanced_renderer, replace=True)

    def register_renderer(
        self,
        name: str,
        renderer: RendererBackend,
        *,
        replace: bool = False,
    ) -> None:
        key = str(name or "").strip().casefold()
        if not key:
            raise TranslucentSVGError("renderer name is required")
        if not callable(renderer):
            raise TranslucentSVGError("renderer must be callable")
        with self._renderer_lock:
            if key in self._renderers and not replace:
                raise TranslucentSVGError(f"renderer already registered: {key}")
            self._renderers[key] = renderer

    def renderer_names(self) -> list[str]:
        with self._renderer_lock:
            return sorted(self._renderers)

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
            "namespace": TL_NS,
            "svg_namespace": SVG_NS,
            "parser": "defusedxml.ElementTree" if DET is not None else "xml.etree.ElementTree",
            "canonicalization": "xml-c14n-2.0",
            "canonical_program_location": "svg/metadata/tl:program",
            "renderers": self.renderer_names(),
            "security": {
                "doctype": "forbidden",
                "entities": "forbidden",
                "script": "forbidden",
                "foreignObject": "forbidden",
                "event_handlers": "forbidden",
                "external_references": "forbidden-by-default",
                "unresolved_internal_references": "forbidden",
                "cyclic_use_references": "forbidden",
                "foreign_attribute_namespaces": "forbidden",
                "external_css": "forbidden",
                "host_execution": "forbidden",
            },
            "limits": {
                field: getattr(self.limits, field)
                for field in self.limits.__dataclass_fields__
            },
            "semantic_terms": self.semantic_terms(),
            "authority_effect": authority_effect,
        }
        result["digest"] = _digest(result)
        return result

    def parse(self, source: str | bytes) -> ET.Element:
        if isinstance(source, bytes):
            raw = source
            try:
                text = raw.decode("utf-8")
            except UnicodeDecodeError as exc:
                raise TranslucentSVGError("translucent svg source must be utf-8") from exc
        else:
            text = str(source)
            raw = text.encode("utf-8")
        if len(raw) > self.limits.max_source_bytes:
            raise TranslucentSVGError(
                f"svg source exceeds {self.limits.max_source_bytes} bytes"
            )
        if _FORBIDDEN_DECLARATIONS.search(text):
            raise TranslucentSVGError("doctype and entity declarations are forbidden")
        try:
            if DET is not None:
                root = DET.fromstring(
                    text,
                    forbid_dtd=True,
                    forbid_entities=True,
                    forbid_external=True,
                )
            else:
                root = ET.fromstring(text)
        except Exception as exc:
            raise TranslucentSVGError(f"invalid svg+xml: {exc}") from exc
        self.validate(root)
        return root

    def validate(self, root: ET.Element) -> None:
        namespace, local = _split_tag(root.tag)
        if namespace != SVG_NS or local != "svg":
            raise TranslucentSVGError("root element must be svg in the SVG namespace")

        count = 0
        attribute_count = 0
        text_chars = 0
        attribute_chars = 0
        ids: set[str] = set()
        programs: list[ET.Element] = []
        fragment_refs: list[tuple[str, str]] = []
        reference_graph: dict[str, set[str]] = {}

        stack: list[tuple[ET.Element, int, bool, str | None]] = [(root, 1, False, None)]
        while stack:
            node, depth, inside_metadata, inherited_owner = stack.pop()
            count += 1
            if count > self.limits.max_nodes:
                raise TranslucentSVGError(f"svg exceeds {self.limits.max_nodes} nodes")
            if depth > self.limits.max_depth:
                raise TranslucentSVGError(f"svg exceeds depth {self.limits.max_depth}")

            node_ns, node_local = _split_tag(node.tag)
            now_in_metadata = inside_metadata or (
                node_ns == SVG_NS and node_local == "metadata"
            )

            if node_ns == SVG_NS:
                if node_local in _FORBIDDEN_SVG_ELEMENTS:
                    raise TranslucentSVGError(f"forbidden svg element: {node_local}")
            elif node_ns == TL_NS:
                if not now_in_metadata:
                    raise TranslucentSVGError(
                        f"translucent element {node_local!r} is only permitted inside svg metadata"
                    )
                if node_local == "program":
                    programs.append(node)
            else:
                raise TranslucentSVGError(
                    f"unsupported foreign namespace for {node_local!r}: {node_ns!r}"
                )

            attribute_count += len(node.attrib)
            if attribute_count > self.limits.max_attributes:
                raise TranslucentSVGError(
                    f"svg exceeds {self.limits.max_attributes} attributes"
                )

            node_id = node.get("id")
            if node_id:
                if node_id in ids:
                    raise TranslucentSVGError(f"duplicate svg id: {node_id}")
                ids.add(node_id)
            if node_id and inherited_owner and node_id != inherited_owner:
                reference_graph.setdefault(inherited_owner, set()).add(node_id)
            owner_id = node_id or inherited_owner
            reference_owner = inherited_owner or node_id

            for attr_name, attr_value in node.attrib.items():
                attr_ns, local_attr = _split_tag(attr_name)
                if attr_ns not in {"", XLINK_NS, XML_NS}:
                    raise TranslucentSVGError(
                        f"unsupported foreign attribute namespace on {local_attr!r}: {attr_ns!r}"
                    )
                lower_attr = local_attr.casefold()
                attribute_chars += len(attr_name) + len(attr_value)
                if attribute_chars > self.limits.max_attribute_chars:
                    raise TranslucentSVGError(
                        f"svg attributes exceed {self.limits.max_attribute_chars} characters"
                    )
                if lower_attr.startswith("on"):
                    raise TranslucentSVGError(
                        f"svg event-handler attribute is forbidden: {local_attr}"
                    )
                if attr_name in _REFERENCE_ATTRIBUTES or lower_attr == "href":
                    if not _is_fragment_ref(attr_value):
                        raise TranslucentSVGError(
                            f"external svg reference is forbidden: {attr_value!r}"
                        )
                    target = attr_value.strip()[1:]
                    fragment_refs.append((f"{node_local}.{local_attr}", target))
                    if node_local == "use" and reference_owner:
                        reference_graph.setdefault(reference_owner, set()).add(target)
                if lower_attr in _URL_ATTRIBUTES and "url(" in attr_value.casefold():
                    if not _urls_are_local(attr_value):
                        raise TranslucentSVGError(
                            f"external url() reference is forbidden in {local_attr}"
                        )
                    for target in _fragment_targets(attr_value):
                        fragment_refs.append((f"{node_local}.{local_attr}", target))

            text_chars += len(node.text or "") + len(node.tail or "")
            if text_chars > self.limits.max_text_chars:
                raise TranslucentSVGError(
                    f"svg text exceeds {self.limits.max_text_chars} characters"
                )

            children = list(node)
            for child in reversed(children):
                stack.append((child, depth + 1, now_in_metadata, owner_id))

        if len(programs) > 1:
            raise TranslucentSVGError("svg may contain only one translucent program")

        for context, target in fragment_refs:
            if target not in ids:
                raise TranslucentSVGError(
                    f"unresolved internal svg reference in {context}: #{target}"
                )

        visiting: set[str] = set()
        visited: set[str] = set()

        def visit(node_id: str, path: tuple[str, ...]) -> None:
            if node_id in visiting:
                cycle = " -> ".join((*path, node_id))
                raise TranslucentSVGError(f"cyclic svg use reference: {cycle}")
            if node_id in visited:
                return
            visiting.add(node_id)
            for target in sorted(reference_graph.get(node_id, ())):
                if target in reference_graph:
                    visit(target, (*path, node_id))
            visiting.remove(node_id)
            visited.add(node_id)

        for node_id in sorted(reference_graph):
            visit(node_id, ())

    def program(self, root: ET.Element) -> ET.Element:
        self.validate(root)
        matches: list[ET.Element] = []
        for metadata in root.findall(f"{{{SVG_NS}}}metadata"):
            matches.extend(metadata.findall(f"{{{TL_NS}}}program"))
        if len(matches) != 1:
            raise TranslucentSVGError(
                "svg must contain exactly one direct metadata/tl:program element"
            )
        return matches[0]

    def canonicalize(self, source_or_root: str | bytes | ET.Element) -> str:
        if isinstance(source_or_root, ET.Element):
            self.validate(source_or_root)
            source = ET.tostring(source_or_root, encoding="unicode")
        else:
            root = self.parse(source_or_root)
            source = ET.tostring(root, encoding="unicode")
        try:
            return ET.canonicalize(
                xml_data=source,
                with_comments=False,
                strip_text=False,
                rewrite_prefixes=True,
            )
        except Exception as exc:
            raise TranslucentSVGError(f"svg canonicalization failed: {exc}") from exc

    def canonical_digest(self, source_or_root: str | bytes | ET.Element) -> str:
        return _digest(self.canonicalize(source_or_root))

    def render(
        self,
        kind: str,
        payload: Mapping[str, Any],
        *,
        renderer: str | None = None,
        context: Mapping[str, Any] | None = None,
    ) -> str:
        if not isinstance(payload, Mapping):
            raise TranslucentSVGError("renderer payload must be a mapping")
        operations = payload.get("operations")
        operation_count = payload.get("operation_count")
        if kind == "execution":
            if isinstance(operation_count, int) and operation_count > self.limits.max_render_operations:
                raise TranslucentSVGError(
                    f"render operation count exceeds {self.limits.max_render_operations}"
                )
            if isinstance(operations, list) and len(operations) > self.limits.max_render_operations:
                raise TranslucentSVGError(
                    f"render operations exceed {self.limits.max_render_operations}"
                )
        selected = str(
            renderer or ("advanced" if kind == "execution" else "projection")
        ).casefold()
        with self._renderer_lock:
            backend = self._renderers.get(selected)
        if backend is None:
            raise TranslucentSVGError(f"unknown svg renderer: {selected}")
        try:
            rendered = backend(kind, payload, dict(context or {}), self)
        except TranslucentSVGError:
            raise
        except Exception as exc:
            raise TranslucentSVGError(
                f"svg renderer {selected!r} failed: {exc.__class__.__name__}: {exc}"
            ) from exc
        if not isinstance(rendered, str):
            raise TranslucentSVGError(f"svg renderer {selected!r} must return text")
        self.parse(rendered)
        return rendered


def register_renderer(
    name: str,
    renderer: RendererBackend,
    *,
    replace: bool = False,
) -> None:
    svg_runtime.register_renderer(name, renderer, replace=replace)


def svg_manifest() -> dict[str, Any]:
    return svg_runtime.manifest()


def _projection_metadata(
    root: ET.Element,
    *,
    runtime: TranslucentSVGRuntime,
    kind: str,
    payload: Mapping[str, Any],
    renderer: str,
) -> None:
    metadata = ET.SubElement(root, f"{{{SVG_NS}}}metadata")
    projection = ET.SubElement(
        metadata,
        f"{{{TL_NS}}}projection",
        {
            "schema": schema,
            "kind": kind,
            "renderer": renderer,
            "authority-effect": authority_effect,
            "source-digest": str(payload.get("digest") or _digest(payload)),
        },
    )
    terms = runtime.semantic_terms()
    for token, lexeme_id in sorted(terms.items()):
        ET.SubElement(
            projection,
            f"{{{TL_NS}}}term",
            {"token": token, "ref": lexeme_id},
        )


def _document_root(width: int, height: int, title: str, description: str) -> ET.Element:
    root = ET.Element(
        f"{{{SVG_NS}}}svg",
        {
            "viewBox": f"0 0 {width} {height}",
            "width": str(width),
            "height": str(height),
            "role": "img",
            "aria-labelledby": "tl-title tl-desc",
        },
    )
    ET.SubElement(root, f"{{{SVG_NS}}}title", {"id": "tl-title"}).text = title
    ET.SubElement(root, f"{{{SVG_NS}}}desc", {"id": "tl-desc"}).text = description
    return root


def _operation_symbol(defs: ET.Element, op: str) -> str:
    symbol_id = _safe_id(f"tl-op-{op}-{_digest(op)[:10]}")
    symbol = ET.SubElement(
        defs,
        f"{{{SVG_NS}}}symbol",
        {"id": symbol_id, "viewBox": "0 0 28 28"},
    )
    ET.SubElement(
        symbol,
        f"{{{SVG_NS}}}path",
        {
            "d": "M4 14 C4 7 10 4 14 4 C18 4 24 7 24 14 C24 21 18 24 14 24 C10 24 4 21 4 14 Z",
            "fill": "none",
            "stroke": "currentColor",
            "stroke-width": "1.7",
            "stroke-linecap": "round",
            "stroke-linejoin": "round",
        },
    )
    code = int(_digest(op)[:4], 16)
    angle = (code % 120) - 60
    x2 = 14 + math.cos(math.radians(angle)) * 7
    y2 = 14 + math.sin(math.radians(angle)) * 7
    ET.SubElement(
        symbol,
        f"{{{SVG_NS}}}path",
        {
            "d": f"M8 18 Q14 7 {x2:.3f} {y2:.3f}",
            "fill": "none",
            "stroke": "currentColor",
            "stroke-width": "2.2",
            "stroke-linecap": "round",
        },
    )
    return symbol_id


def _advanced_renderer(
    kind: str,
    payload: Mapping[str, Any],
    context: Mapping[str, Any],
    runtime: TranslucentSVGRuntime,
) -> str:
    if kind != "execution":
        return _projection_renderer(kind, payload, context, runtime)
    operations = payload.get("operations")
    if not isinstance(operations, list):
        operations = []
    width = _bounded_int(context.get("width"), default=1280, minimum=480, maximum=4096)
    row_height = _bounded_int(context.get("row_height"), default=40, minimum=28, maximum=96)
    height = max(180, 112 + row_height * max(1, len(operations)))
    root = _document_root(
        width,
        height,
        "Translucent execution projection",
        "A non-authoritative, rebuildable SVG projection of a Translucent execution result.",
    )
    _projection_metadata(root, runtime=runtime, kind=kind, payload=payload, renderer="advanced")
    defs = ET.SubElement(root, f"{{{SVG_NS}}}defs")

    present_ops = sorted(
        {
            str(item.get("op") or "operation")
            for item in operations
            if isinstance(item, Mapping)
        }
    )
    symbols = {op: _operation_symbol(defs, op) for op in present_ops}

    background = ET.SubElement(root, f"{{{SVG_NS}}}g", {"id": "tl-background"})
    ET.SubElement(
        background,
        f"{{{SVG_NS}}}rect",
        {"x": "0", "y": "0", "width": str(width), "height": str(height), "fill": "#0b0d10"},
    )

    heading = ET.SubElement(root, f"{{{SVG_NS}}}g", {"id": "tl-heading"})
    ET.SubElement(
        heading,
        f"{{{SVG_NS}}}text",
        {"x": "30", "y": "38", "fill": "#f1e7c7", "font-size": "18", "font-family": "ui-monospace, monospace"},
    ).text = "translucent / datrix"
    ET.SubElement(
        heading,
        f"{{{SVG_NS}}}text",
        {"x": "30", "y": "62", "fill": "#8c949e", "font-size": "11", "font-family": "ui-monospace, monospace"},
    ).text = f"projection · authority-effect=none · digest={str(payload.get('digest') or _digest(payload))[:24]}"

    rows = ET.SubElement(root, f"{{{SVG_NS}}}g", {"id": "tl-operations"})
    for index, operation in enumerate(operations):
        if not isinstance(operation, Mapping):
            continue
        op = str(operation.get("op") or "operation")
        y = 92 + index * row_height
        row = ET.SubElement(
            rows,
            f"{{{SVG_NS}}}g",
            {
                "id": _safe_id(f"tl-row-{index}-{op}"),
                "data-op": op,
                "data-instance": str(index),
            },
        )
        ET.SubElement(
            row,
            f"{{{SVG_NS}}}rect",
            {
                "x": "22",
                "y": str(y - 20),
                "width": str(width - 44),
                "height": str(row_height - 4),
                "rx": "9",
                "fill": "#11151a",
                "stroke": "#27313a",
                "stroke-width": "1",
            },
        )
        ET.SubElement(
            row,
            f"{{{SVG_NS}}}use",
            {
                "href": f"#{symbols[op]}",
                "x": "31",
                "y": str(y - 17),
                "width": "24",
                "height": "24",
                "color": "#d9b44a",
            },
        )
        ET.SubElement(
            row,
            f"{{{SVG_NS}}}text",
            {
                "x": "67",
                "y": str(y),
                "fill": "#e8eaf0",
                "font-size": "12",
                "font-family": "ui-monospace, monospace",
            },
        ).text = op
        detail = operation.get("as") or operation.get("id") or operation.get("ref")
        if detail:
            ET.SubElement(
                row,
                f"{{{SVG_NS}}}text",
                {
                    "x": "190",
                    "y": str(y),
                    "fill": "#9ba7b3",
                    "font-size": "11",
                    "font-family": "ui-monospace, monospace",
                },
            ).text = _escape_text(detail)[:160]
        digest = operation.get("digest")
        if digest:
            ET.SubElement(
                row,
                f"{{{SVG_NS}}}text",
                {
                    "x": str(max(300, width - 260)),
                    "y": str(y),
                    "fill": "#596571",
                    "font-size": "10",
                    "font-family": "ui-monospace, monospace",
                },
            ).text = str(digest)[:24]

    return ET.tostring(root, encoding="unicode", short_empty_elements=True)


def _projection_renderer(
    kind: str,
    payload: Mapping[str, Any],
    context: Mapping[str, Any],
    runtime: TranslucentSVGRuntime,
) -> str:
    width = _bounded_int(context.get("width"), default=960, minimum=360, maximum=4096)
    height = _bounded_int(context.get("height"), default=360, minimum=180, maximum=4096)
    root = _document_root(
        width,
        height,
        "Translucent projection",
        "A deterministic, non-authoritative projection of normalized Translucent substance.",
    )
    _projection_metadata(root, runtime=runtime, kind=kind, payload=payload, renderer="projection")
    defs = ET.SubElement(root, f"{{{SVG_NS}}}defs")
    symbol_id = _operation_symbol(defs, "projection")
    ET.SubElement(
        root,
        f"{{{SVG_NS}}}rect",
        {"x": "0", "y": "0", "width": str(width), "height": str(height), "fill": "#0b0d10"},
    )
    ET.SubElement(
        root,
        f"{{{SVG_NS}}}use",
        {"href": f"#{symbol_id}", "x": "34", "y": "42", "width": "72", "height": "72", "color": "#d9b44a"},
    )
    ET.SubElement(
        root,
        f"{{{SVG_NS}}}text",
        {"x": "132", "y": "76", "fill": "#f1e7c7", "font-size": "18", "font-family": "ui-monospace, monospace"},
    ).text = f"translucent {kind} projection"
    ET.SubElement(
        root,
        f"{{{SVG_NS}}}text",
        {"x": "132", "y": "102", "fill": "#8c949e", "font-size": "11", "font-family": "ui-monospace, monospace"},
    ).text = f"source {str(payload.get('digest') or _digest(payload))[:32]}"
    return ET.tostring(root, encoding="unicode", short_empty_elements=True)


def selftest(registry_path: str) -> dict[str, Any]:
    registry = SemanticIdentityRegistry(registry_path)
    runtime = TranslucentSVGRuntime(semantic_registry=registry)
    source = f'''<svg xmlns="{SVG_NS}" xmlns:tl="{TL_NS}" viewBox="0 0 10 10">
      <metadata><tl:program id="p"><tl:health datrix="d"/></tl:program></metadata>
      <defs><symbol id="dot"><circle cx="1" cy="1" r="1"/></symbol></defs>
      <use href="#dot" x="2" y="2"/>
    </svg>'''
    root = runtime.parse(source)
    canonical_a = runtime.canonicalize(source)
    canonical_b = runtime.canonicalize(root)
    execution = {
        "schema": "selftest",
        "operation_count": 2,
        "operations": [
            {"op": "health", "status": "ok", "digest": "a" * 64},
            {"op": "health", "status": "ok", "digest": "b" * 64},
        ],
        "authority_effect": "none",
    }
    execution["digest"] = _digest(execution)
    render_a = runtime.render("execution", execution, renderer="advanced")
    render_b = runtime.render("execution", execution, renderer="advanced")
    checks = {
        "program_found": runtime.program(root).get("id") == "p",
        "canonical_stable": canonical_a == canonical_b,
        "canonical_digest_stable": runtime.canonical_digest(source) == _digest(canonical_a),
        "advanced_registered": "advanced" in runtime.manifest()["renderers"],
        "projection_registered": "projection" in runtime.manifest()["renderers"],
        "renderer_registry_single_owner": runtime.renderer_names() == ["advanced", "projection"],
        "render_stable": render_a == render_b,
        "symbol_reused": render_a.count("<symbol") >= 1 and render_a.count("<use") == 2,
        "truth_bound": runtime.semantic_terms()["truth"] == "lex:core:truth",
        "determinism_bound": runtime.semantic_terms()["determinism"] == "lex:core:determinism",
        "authority_none": authority_effect == "none",
    }
    try:
        runtime.parse(
            f'<svg xmlns="{SVG_NS}"><image href="https://example.com/x.png"/></svg>'
        )
        checks["external_reference_rejected"] = False
    except TranslucentSVGError:
        checks["external_reference_rejected"] = True
    try:
        runtime.parse(f'<svg xmlns="{SVG_NS}" onclick="x()"></svg>')
        checks["event_handler_rejected"] = False
    except TranslucentSVGError:
        checks["event_handler_rejected"] = True
    try:
        runtime.parse(
            f'<svg xmlns="{SVG_NS}"><use href="#missing"/></svg>'
        )
        checks["unresolved_fragment_rejected"] = False
    except TranslucentSVGError:
        checks["unresolved_fragment_rejected"] = True
    try:
        runtime.parse(
            f'<svg xmlns="{SVG_NS}"><defs>'
            '<g id="a"><use href="#b"/></g>'
            '<g id="b"><use href="#a"/></g>'
            '</defs><use href="#a"/></svg>'
        )
        checks["cyclic_use_rejected"] = False
    except TranslucentSVGError:
        checks["cyclic_use_rejected"] = True
    try:
        runtime.render("projection", {}, context={"width": "not-a-number"})
        checks["invalid_context_bounded"] = True
    except TranslucentSVGError:
        checks["invalid_context_bounded"] = False
    result = {
        "schema": "savant.translucent.svg-selftest.v3",
        "ok": all(checks.values()),
        "checks": checks,
        "canonical_digest": runtime.canonical_digest(source),
        "render_digest": _digest(render_a),
        "authority_effect": authority_effect,
    }
    result["digest"] = _digest(result)
    return result


svg_runtime = TranslucentSVGRuntime()


__all__ = [
    "NS",
    "SVG_NS",
    "TL_NS",
    "RendererBackend",
    "SVGLimits",
    "TranslucentSVGError",
    "TranslucentSVGRuntime",
    "register_renderer",
    "selftest",
    "svg_manifest",
    "svg_runtime",
]
