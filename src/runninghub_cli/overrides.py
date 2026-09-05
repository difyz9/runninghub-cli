"""Node override parsing and upload resolution helpers."""

from __future__ import annotations

import json
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from runninghub_sdk import RunningHubClient, modify_nodes

UPLOAD_PREFIX = "@upload:"
UPLOAD_URL_PREFIX = "@upload-url:"

MEDIA_KIND_BY_FIELD = {
    "image": "image",
    "img": "image",
    "video": "video",
    "audio": "audio",
    "file": "file",
}

MEDIA_KIND_BY_SUFFIX = {
    ".apng": "image",
    ".avif": "image",
    ".bmp": "image",
    ".gif": "image",
    ".jpeg": "image",
    ".jpg": "image",
    ".png": "image",
    ".webp": "image",
    ".mov": "video",
    ".mp4": "video",
    ".mpeg": "video",
    ".mpg": "video",
    ".webm": "video",
    ".m4a": "audio",
    ".mp3": "audio",
    ".ogg": "audio",
    ".wav": "audio",
}


def parse_overrides(value: str | Path | list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    if value is None:
        return []
    if isinstance(value, list):
        return value

    text = str(value).strip()
    if not text:
        return []

    maybe_path = Path(text)
    if maybe_path.exists():
        text = maybe_path.read_text(encoding="utf-8")

    parsed = json.loads(text)
    if isinstance(parsed, dict) and "node_overrides" in parsed:
        parsed = parsed["node_overrides"]
    if not isinstance(parsed, list):
        raise ValueError("node_overrides 必须是 JSON 数组，或包含 node_overrides 的 JSON 对象")
    return parsed


def parse_node_shorthand(shorthand: str) -> dict[str, str]:
    """解析 'nodeId:fieldName=value' 格式的参数为 dict。"""
    error_msg = f"节点参数格式错误: '{shorthand}'，应为 nodeId:fieldName=value"
    colon_idx = shorthand.find(":")
    if colon_idx == -1:
        raise ValueError(error_msg)
    node_id = shorthand[:colon_idx]
    rest = shorthand[colon_idx + 1 :]
    eq_idx = rest.find("=")
    if eq_idx == -1:
        raise ValueError(error_msg)
    return {
        "nodeId": node_id,
        "fieldName": rest[:eq_idx],
        "fieldValue": rest[eq_idx + 1 :],
    }


def build_modifier(overrides: Iterable[dict[str, Any]]):
    modifier = modify_nodes()
    for item in overrides:
        node_id = item.get("nodeId") or item.get("node_id")
        field_name = item.get("fieldName") or item.get("field_name")
        if not node_id or not field_name:
            raise ValueError(f"无效 node override: {item}")
        field_value = item.get("fieldValue") if "fieldValue" in item else item.get("field_value")
        modifier.set(str(node_id), str(field_name), field_value)
    return modifier


def _field_value_key(item: dict[str, Any]) -> str:
    return "fieldValue" if "fieldValue" in item else "field_value"


def _field_name(item: dict[str, Any]) -> str:
    return str(item.get("fieldName") or item.get("field_name") or "")


def _node_id(item: dict[str, Any]) -> str:
    return str(item.get("nodeId") or item.get("node_id") or "")


def infer_upload_kind(item: dict[str, Any], path: Path) -> str:
    field_kind = MEDIA_KIND_BY_FIELD.get(_field_name(item).strip().lower())
    if field_kind:
        return field_kind
    return MEDIA_KIND_BY_SUFFIX.get(path.suffix.lower(), "file")


def _resolve_upload_path(raw_path: str) -> Path:
    path = Path(raw_path.strip()).expanduser()
    if not path.is_absolute():
        path = Path.cwd() / path
    path = path.resolve()
    if not path.exists() or not path.is_file():
        raise FileNotFoundError(f"上传文件不存在: {path}")
    return path


def _upload_result_data(upload_result: Any, kind: str) -> dict[str, str]:
    if isinstance(upload_result, dict):
        file_name = upload_result.get("fileName") or upload_result.get("file_name") or ""
        download_url = upload_result.get("downloadUrl") or upload_result.get("download_url") or ""
    else:
        file_name = getattr(upload_result, "file_name", "") or getattr(upload_result, "fileName", "")
        download_url = getattr(upload_result, "download_url", "") or getattr(upload_result, "downloadUrl", "")
    return {"kind": kind, "fileName": file_name, "downloadUrl": download_url}


def upload_with_client(client: RunningHubClient, path: Path, kind: str) -> dict[str, str]:
    if kind == "image":
        return _upload_result_data(client.upload_image(path), kind)
    return _upload_result_data(client.upload_file(path), kind)


def process_upload_overrides(
    client: RunningHubClient,
    overrides: Iterable[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
    processed: list[dict[str, Any]] = []
    uploads: list[dict[str, str]] = []

    for item in overrides:
        copied = dict(item)
        value_key = _field_value_key(copied)
        field_value = copied.get(value_key)
        if not isinstance(field_value, str):
            processed.append(copied)
            continue

        wants_url = False
        if field_value.startswith(UPLOAD_URL_PREFIX):
            raw_path = field_value.removeprefix(UPLOAD_URL_PREFIX)
            wants_url = True
        elif field_value.startswith(UPLOAD_PREFIX):
            raw_path = field_value.removeprefix(UPLOAD_PREFIX)
        else:
            processed.append(copied)
            continue

        path = _resolve_upload_path(raw_path)
        kind = infer_upload_kind(copied, path)
        upload_data = upload_with_client(client, path, kind)
        replacement = upload_data["downloadUrl"] if wants_url else upload_data["fileName"]
        if not replacement:
            target = "downloadUrl" if wants_url else "fileName"
            raise RuntimeError(f"上传成功但返回缺少 {target}: {path}")

        copied[value_key] = replacement
        uploads.append(
            {
                "nodeId": _node_id(copied),
                "fieldName": _field_name(copied),
                "kind": kind,
                "path": str(path),
                "fileName": upload_data["fileName"],
                "downloadUrl": upload_data["downloadUrl"],
                "used": "downloadUrl" if wants_url else "fileName",
            }
        )
        processed.append(copied)

    return processed, uploads
