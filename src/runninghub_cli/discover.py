"""Discover, test, and export RunningHub workflows and AI Apps as Hermes skills."""

from __future__ import annotations

import json
import time
from dataclasses import is_dataclass
from enum import Enum
from pathlib import Path
from typing import Any

from runninghub_sdk import (
    PortalTemplateListRequest,
    RunningHubClient,
    WebappListRequest,
    modify_nodes,
)
from runninghub_sdk.exceptions import RunningHubError, TimeoutError

# ── Helpers ─────────────────────────────────────────────────


def to_plain(value: Any) -> Any:
    if is_dataclass(value):
        return {
            k: to_plain(getattr(value, k))
            for k in (f.name for f in value.__dataclass_fields__.values())
        }
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, list):
        return [to_plain(v) for v in value]
    if isinstance(value, dict):
        return {k: to_plain(v) for k, v in value.items()}
    return value


def slugify(name: str) -> str:
    """Generate a clean ASCII snake_case skill name."""
    ZH_MAP = {
        "文生图": "txt2img", "图生视频": "img2vid", "视频生成": "vid_gen",
        "首尾帧过渡": "first2last", "分镜": "storyboard",
        "舞蹈": "dance", "风格融合": "style_fusion", "打斗": "combat",
        "提取": "extract", "人物": "person", "衣服": "clothes",
        "国风": "chinese_fantasy", "剑仙": "sword_fairy",
        "通用": "general", "一键": "oneclick", "视频": "video",
        "图片": "image", "模型": "model", "工作流": "wf",
    }
    for zh, en in ZH_MAP.items():
        if zh in name:
            name = name.replace(zh, en)
    result = []
    for ch in name.lower():
        if "a" <= ch <= "z" or "0" <= ch <= "9":
            result.append(ch)
        elif ch in (" ", "_", "-", "·", "(", ")", "+", "&", "：", ":"):
            result.append("_")
    s = "".join(result)
    while "__" in s:
        s = s.replace("__", "_")
    s = s.strip("_")
    if not s:
        s = "untitled"
    if s[0].isdigit():
        s = "wf_" + s
    return s[:64]


# ── Search / Browse ─────────────────────────────────────────


def search_portal(
    client: RunningHubClient,
    *,
    keyword: str = "",
    page: int = 1,
    size: int = 20,
    sort: str = "RECOMMEND",
) -> dict[str, Any]:
    """Search portal templates (workflows)."""
    req = PortalTemplateListRequest(
        size=size, current=page, search=keyword, sort=sort
    )
    result = client.list_portal_templates(req)
    return to_plain(result)


def search_webapps(
    client: RunningHubClient,
    *,
    keyword: str = "",
    page: int = 1,
    size: int = 20,
    sort: str = "RECOMMEND",
) -> dict[str, Any]:
    """Search webapps (AI Apps)."""
    req = WebappListRequest(
        size=size, current=page, search=keyword, sort=sort
    )
    result = client.list_webapps(req)
    return to_plain(result)


# ── Inspect ─────────────────────────────────────────────────


def inspect_item(client: RunningHubClient, identifier: str) -> dict[str, Any]:
    """Detect type and return detailed inspection."""
    # Try webapp first
    try:
        demo = client.get_ai_app_api_demo(identifier)
        nodes = [
            {
                "nodeId": n.node_id,
                "nodeName": n.node_name,
                "fieldName": n.field_name,
                "fieldValue": n.field_value,
                "fieldType": n.field_type,
                "fieldData": n.field_data,
                "description": n.description,
            }
            for n in demo.node_info_list
        ]
        return {
            "id": identifier,
            "type": "webapp",
            "name": demo.webapp_name,
            "nodeCount": len(nodes),
            "nodes": nodes,
            "accessEncrypted": demo.access_encrypted,
        }
    except Exception:
        pass

    # Try workflow
    try:
        wf = client.get_workflow_json_parsed(identifier)
        if not isinstance(wf, dict):
            raise RuntimeError("Non-standard workflow JSON")
        by_type: dict[str, list[str]] = {}
        editable: list[dict[str, Any]] = []
        for node_id, node in wf.items():
            cls_type = node.get("class_type", "?")
            inputs = node.get("inputs", {})
            by_type.setdefault(cls_type, []).append(str(node_id))
            if isinstance(inputs, dict):
                editable.append({
                    "nodeId": str(node_id),
                    "classType": cls_type,
                    "fields": list(inputs.keys()),
                })

        return {
            "id": identifier,
            "type": "workflow",
            "nodeCount": len(wf),
            "byType": {
                ct: {"count": len(nids), "nodeIds": nids[:20]}
                for ct, nids in sorted(by_type.items())
            },
            "nodes": editable,
        }
    except Exception as exc:
        return {"id": identifier, "error": str(exc)}


# ── Auto-test ──────────────────────────────────────────────


def smart_generate_test_input(
    item_info: dict[str, Any],
    user_prompt: str = "",
) -> list[dict[str, Any]]:
    """Automatically build a test node override payload from inspection data."""
    overrides: list[dict[str, Any]] = []

    # For webapps/AI Apps, use the API demo's node_info_list defaults directly
    if item_info.get("type") == "webapp":
        for node in item_info.get("nodes", []):
            val = user_prompt if (node.get("fieldType") in ("string", "") and not node.get("fieldValue")) else (node.get("fieldValue") or "")
            if val:
                overrides.append({
                    "nodeId": node["nodeId"],
                    "fieldName": node["fieldName"],
                    "fieldValue": val,
                })
        return overrides

    # For workflows, try to detect prompt/text nodes and fill with defaults
    for node in item_info.get("nodes", []):
        fields_lower = [f.lower() for f in node.get("fields", [])]
        class_type = node.get("classType", "").lower()
        node_id = node["nodeId"]

        if "prompt" in class_type or any("prompt" in f for f in fields_lower):
            pf = next((f for f in node.get("fields", []) if "prompt" in f.lower()), None)
            if pf:
                overrides.append({
                    "nodeId": node_id,
                    "fieldName": pf,
                    "fieldValue": user_prompt or "test prompt, cinematic quality, 4K",
                })
        elif "text" in class_type or any("text" in f for f in fields_lower):
            tf = next((f for f in node.get("fields", []) if "text" in f.lower()), None)
            if tf:
                overrides.append({
                    "nodeId": node_id,
                    "fieldName": tf,
                    "fieldValue": user_prompt or "test prompt",
                })
        elif "primitive" in class_type:
            vf = next((f for f in node.get("fields", []) if f in ("value", "text")), "value")
            overrides.append({
                "nodeId": node_id,
                "fieldName": vf,
                "fieldValue": user_prompt or "test",
            })

    return overrides


def test_run(
    client: RunningHubClient,
    identifier: str,
    *,
    item_type: str = "auto",
    overrides: list[dict[str, Any]] | None = None,
    timeout: float = 300,
    poll_interval: float = 5,
    user_prompt: str = "",
) -> dict[str, Any]:
    """Run a test against a workflow or AI App and return structured results."""
    # Auto-detect type
    if item_type == "auto":
        info = inspect_item(client, identifier)
        item_type = info.get("type", "workflow")

    # Build test overrides if not provided
    if not overrides:
        info = inspect_item(client, identifier)
        overrides = smart_generate_test_input(info, user_prompt)

    start = time.time()
    modifier = modify_nodes()
    for ov in overrides:
        modifier.set(str(ov["nodeId"]), str(ov["fieldName"]), ov["fieldValue"])

    try:
        if item_type == "webapp":
            task = client.run_ai_app_with_modifier(
                webapp_id=identifier, modifier=modifier
            )
        else:
            task = client.run_with_modifier(
                workflow_id=identifier, modifier=modifier, add_metadata=True
            )

        task_id = task.task_id
        outputs = client.wait_for_completion(
            task_id,
            poll_interval=poll_interval,
            timeout=timeout,
        )
        elapsed = time.time() - start
        return {
            "ok": True,
            "taskId": task_id,
            "type": item_type,
            "duration": round(elapsed, 1),
            "outputCount": len(outputs),
            "outputTypes": list({getattr(o, "file_type", o.get("fileType", "unknown")) for o in outputs}),
            "overrides": overrides,
        }
    except TimeoutError:
        return {"ok": False, "error": f"Timeout after {timeout}s", "type": item_type}
    except RunningHubError as exc:
        return {"ok": False, "error": str(exc), "type": item_type}


# ── Export SKILL.md ────────────────────────────────────────


def generate_skill_md(
    identifier: str,
    *,
    item_type: str = "workflow",
    name: str = "",
    description: str = "",
    verified_overrides: list[dict[str, Any]] | None = None,
    output_dir: str = ".",
) -> Path:
    """Generate a Hermes Agent SKILL.md file for a verified workflow."""
    skill_name = slugify(name) if name else slugify(identifier)
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    filepath = out_dir / f"{skill_name}.md"

    # Build the example overrides block
    override_lines = []
    if verified_overrides:
        for ov in verified_overrides:
            val = json.dumps(ov["fieldValue"], ensure_ascii=False)
            override_lines.append(
                f'      {{"nodeId": "{ov["nodeId"]}", "fieldName": "{ov["fieldName"]}", "fieldValue": {val}}}'
            )

    overrides_json = (
        "[\n" + ",\n".join(override_lines) + "\n    ]" if override_lines else "[]"
    )

    rh_type_flag = "webapp" if item_type == "webapp" else "workflow"

    md = f"""---
name: {skill_name}
title: {name or identifier}
description: >-
  {description or f"RunningHub {item_type}: {identifier}"}
outputType: media
runninghubId: {identifier}
runninghubType: {item_type}
---

# {name or identifier}

{description or f"Auto-discovered RunningHub {item_type}"}

**RunningHub ID**: `{identifier}` · **类型**: `{item_type}`

---

## 运行命令

```bash
# 需要安装 runninghub-cli 并配置 RUNNINGHUB_API_KEY
runninghub run {identifier} \\
  --type {rh_type_flag} \\
  --node-overrides '{overrides_json}' \\
  --output-dir ./outputs/{skill_name}
```

---

## 已验证的请求载荷

```json
{overrides_json}
```

---

## 注意事项

- 图片类型字段支持 `@upload:/path/to/file` 自动上传
- 任务超时默认 1800 秒，可通过 `--timeout` 调整
- 输出文件下载到 `--output-dir` 指定目录

---

> 由 `runninghub discover` 自动生成 · {time.strftime("%Y-%m-%d")}
"""
    filepath.write_text(md, encoding="utf-8")
    return filepath
