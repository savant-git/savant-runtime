from __future__ import annotations

import json
from typing import Any


def structured(objects: list[dict[str, Any]], graph: dict[str, Any]) -> Any: return {"objects":objects}
def graph_view(objects: list[dict[str, Any]], graph: dict[str, Any]) -> Any: return graph
def visualization(objects: list[dict[str, Any]], graph: dict[str, Any]) -> Any: return {"graph":graph,"hooks":graph["visualization_hooks"]}
def markdown(objects: list[dict[str, Any]], graph: dict[str, Any]) -> Any: return "\n".join(f"- `{o['id']}` ({o['kind']}): {o['description']}" for o in objects)
def yaml_view(objects: list[dict[str, Any]], graph: dict[str, Any]) -> Any:
    import yaml
    return yaml.safe_dump({"objects":objects}, sort_keys=True, allow_unicode=True)
def schema_view(objects: list[dict[str, Any]], graph: dict[str, Any]) -> Any:
    return {"type":"array","items":{"type":"object","required":sorted(objects[0]) if objects else []}}
def validation_view(objects: list[dict[str, Any]], graph: dict[str, Any]) -> Any:
    return {"valid":True,"object_count":len(objects),"edge_count":len(graph["edges"])}


PLUGINS = {
    "runtime": structured, "json": structured, "yaml": yaml_view,
    "markdown": markdown, "documentation": markdown, "graph": graph_view,
    "visualization": visualization, "future_visualization": visualization,
    "future_code_generation": structured,
    "schema": schema_view, "validation": validation_view,
    "implementation": structured, "future_tooling": structured,
    "future_ui": structured, "future_api": structured, "future_ide": structured,
}
