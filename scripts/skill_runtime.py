"""Shared helpers for skill/profile-style script runtimes."""

from __future__ import annotations

from typing import Any


class SkillRuntimeError(ValueError):
    """Raised when skill/profile runtime inputs are invalid."""


def parse_kv_items(items: list[str], *, flag_name: str = "--param") -> dict[str, str]:
    params: dict[str, str] = {}
    for item in items:
        if "=" not in item:
            raise SkillRuntimeError(f"Invalid {flag_name} format: {item}; expected key=value")
        key, value = item.split("=", 1)
        key = key.strip()
        value = value.strip()
        if not key:
            raise SkillRuntimeError(f"Invalid {flag_name} key in: {item}")
        params[key] = value
    return params


def apply_declared_defaults(params: dict[str, str], schema: dict[str, Any]) -> dict[str, str]:
    merged = dict(params)
    for section in ("required", "optional"):
        for item in schema.get(section, []):
            name = item.get("name")
            default = item.get("default")
            if name and default is not None and name not in merged:
                merged[name] = str(default)
    return merged


def validate_required_params(params: dict[str, str], required_names: list[str]) -> None:
    missing = [name for name in required_names if name not in params]
    if missing:
        raise SkillRuntimeError(f"Missing required params: {', '.join(missing)}")


def build_node_overrides(mapping: list[dict[str, Any]], params: dict[str, str]) -> list[dict[str, str]]:
    overrides: list[dict[str, str]] = []
    for item in mapping:
        param = item.get("param")
        node_id = item.get("nodeId")
        field_name = item.get("fieldName")
        mode = item.get("valueMode", item.get("mode", "literal"))

        if not param or not node_id or not field_name:
            raise SkillRuntimeError("Invalid mapping entry: missing param/nodeId/fieldName")
        if param not in params:
            continue

        raw_value = str(params[param])
        field_value = f"@upload:{raw_value}" if mode == "upload" else raw_value

        overrides.append(
            {
                "nodeId": str(node_id),
                "fieldName": str(field_name),
                "fieldValue": field_value,
            }
        )

    return overrides
