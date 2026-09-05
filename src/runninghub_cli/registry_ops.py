"""Registry/config operations for RunningHub workflow payload metadata."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml

REGISTRY_FILE = Path(__file__).resolve().parent.parent.parent / "registry" / "workflows.yaml"
PAYLOAD_DIR = Path(__file__).resolve().parent.parent.parent / "registry" / "payloads"

QUALITY_ICONS = {
    "verified": "✅",
    "experimental": "🧪",
    "unstable": "⚠️",
    "broken": "❌",
}

QUALITY_ORDER: dict[str, int] = {"verified": 0, "experimental": 1, "unstable": 2, "broken": 3}


def _load_registry() -> dict[str, Any]:
    """加载并解析 workflows.yaml 注册表"""
    reg_path = REGISTRY_FILE
    if not reg_path.exists():
        raise FileNotFoundError(f"注册表文件不存在: {reg_path}")
    with open(reg_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def _iter_all_entries() -> list[dict[str, Any]]:
    """扫描 payloads/ 目录获取所有注册条目（不再依赖 YAML 列表）"""
    entries: list[dict[str, Any]] = []
    if not PAYLOAD_DIR.exists():
        return entries
    for f in sorted(PAYLOAD_DIR.glob("*.json")):
        eid = f.stem
        quality = _get_payload_field(eid, "quality", "unknown")
        entries.append({"id": eid, "quality": quality})
    return entries


def _find_entry_by_id(registry: dict[str, Any] | None, entry_id: str) -> dict[str, Any] | None:
    """按 ID 查找条目（通过 payload JSON 是否存在判断）"""
    del registry  # retained for compatibility
    if _has_payload(entry_id):
        quality = _get_payload_field(entry_id, "quality", "unknown")
        return {"id": entry_id, "quality": quality}
    return None


def _get_payload_field(entry_id: str, field: str, default: Any = None) -> Any:
    """从 payload JSON 读取指定字段，不存在则返回 default。"""
    payload = _load_payload(entry_id)
    if payload:
        return payload.get(field, default)
    return default


def _payload_path(entry_id: str) -> Path:
    """获取 payload JSON 文件路径 (convention: payloads/{id}.json)"""
    return PAYLOAD_DIR / f"{entry_id}.json"


def _has_payload(entry_id: str) -> bool:
    """检查指定 ID 是否有独立的 payload JSON 文件"""
    return _payload_path(entry_id).exists()


def _load_payload(entry_id: str) -> dict[str, Any] | None:
    """加载指定 ID 的完整 payload JSON（含 api_params）"""
    path = _payload_path(entry_id)
    if not path.exists():
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def get_registry_summary() -> list[dict[str, Any]]:
    """获取注册表摘要（不含节点详情）"""
    entries = _iter_all_entries()
    summary = []
    for e in entries:
        eid = e.get("id", "")
        payload = _load_payload(eid)
        node_list = (payload or {}).get("api_params", {}).get("nodeInfoList", [])
        examples = (payload or {}).get("examples", [])
        has_guide = bool(payload and payload.get("call_guide"))
        summary.append(
            {
                "id": eid,
                "name": (payload or {}).get("template_name", eid),
                "type": (payload or {}).get("type", "workflow"),
                "group": (payload or {}).get("group_name", ""),
                "quality": e.get("quality", "unknown"),
                "outputType": (payload or {}).get("outputType", "?"),
                "nodeCount": len(node_list),
                "exampleCount": len(examples),
                "hasGuide": has_guide,
                "hasPayload": _has_payload(eid),
            }
        )
    return summary


def get_verified_entries() -> list[dict[str, Any]]:
    """仅获取已验证的条目"""
    entries = _iter_all_entries()
    result = []
    for e in entries:
        if e.get("quality") != "verified":
            continue
        eid = e.get("id", "")
        payload = _load_payload(eid)
        node_defs = (payload or {}).get("api_params", {}).get("nodeInfoList", [])
        result.append(
            {
                "id": eid,
                "name": (payload or {}).get("template_name", eid),
                "type": (payload or {}).get("type", "workflow"),
                "outputType": (payload or {}).get("outputType", "?"),
                "nodeCount": len(node_defs),
            }
        )
    return result


def get_defaults() -> dict[str, str]:
    """获取默认工作流映射"""
    registry = _load_registry()
    defaults = registry.get("defaults", {})
    if isinstance(defaults, dict):
        return defaults
    return {}


def set_default(task_type: str, entry_id: str) -> dict[str, Any]:
    """设置默认工作流映射"""
    registry = _load_registry()
    if "defaults" not in registry:
        registry["defaults"] = {}
    registry["defaults"][task_type] = entry_id
    _save_registry(registry)
    return {"task_type": task_type, "entry_id": entry_id, "message": "默认映射已更新"}


def _save_registry(registry: dict[str, Any]) -> None:
    """保存注册表到文件"""
    REGISTRY_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(REGISTRY_FILE, "w", encoding="utf-8") as f:
        yaml.dump(registry, f, allow_unicode=True, indent=2, sort_keys=False, default_flow_style=False)


def get_tiktok_remake_ids() -> dict[str, str]:
    """获取抖音复刻玩法 → 工作流 ID 映射"""
    registry = _load_registry()
    tiktok_map = registry.get("tiktok", {})
    if isinstance(tiktok_map, dict):
        return tiktok_map
    return {}


def check_quality(identifier: str, min_quality: str = "verified") -> dict[str, Any]:
    """检查指定 ID 是否满足最低质量要求"""
    icons = {"verified": "✅", "experimental": "🧪", "unstable": "⚠️", "broken": "❌"}
    order = {"verified": 0, "experimental": 1, "unstable": 2, "broken": 3, "unknown": 99}

    entry = _find_entry_by_id(None, identifier)
    if not entry:
        name = _get_payload_field(identifier, "template_name", identifier)
        quality = _get_payload_field(identifier, "quality", "unknown")
        return {
            "ok": False,
            "id": identifier,
            "name": name,
            "quality": quality,
            "icon": icons.get(quality, "❓"),
            "reason": f"未在 payloads/ 目录中找到 {identifier}.json，无法验证质量等级",
        }

    quality = entry["quality"]
    if order.get(quality, 99) <= order.get(min_quality, 0):
        return {
            "ok": True,
            "id": identifier,
            "name": _get_payload_field(identifier, "template_name", identifier),
            "quality": quality,
            "icon": icons.get(quality, "❓"),
        }
    return {
        "ok": False,
        "id": identifier,
        "name": _get_payload_field(identifier, "template_name", identifier),
        "quality": quality,
        "icon": icons.get(quality, "❓"),
        "reason": f"质量等级 '{quality}' 低于最低要求 '{min_quality}'",
    }


def set_entry_quality(entry_id: str, level: str) -> dict[str, Any]:
    """设置指定 ID 的质量等级"""
    if level not in QUALITY_ICONS:
        return {"ok": False, "error": f"无效的质量等级: {level}，可选: {', '.join(QUALITY_ICONS.keys())}"}

    path = _payload_path(entry_id)
    if not path.exists():
        return {"ok": False, "error": f"未找到 payload 文件: {path}"}

    with open(path, "r", encoding="utf-8") as f:
        payload = json.load(f)

    payload["quality"] = level
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    return {"ok": True, "id": entry_id, "quality": level, "icon": QUALITY_ICONS[level], "message": f"质量等级已更新为 {level}"}
