"""Reusable service functions backed by runninghub-sdk."""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any, Iterable

from runninghub_sdk import RunningHubClient, TaskStatus, modify_nodes
from runninghub_sdk.exceptions import RunningHubError, TaskError, TimeoutError, ValidationError

DEFAULT_OUTPUT_ROOT = Path.cwd() / "runninghub_outputs"
DEFAULT_REPO_URL = "https://github.com/difyz9/runninghub-cli.git"
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


def load_env_file(path: str | Path | None = None) -> None:
    env_path = Path(path or ".env")
    if not env_path.exists():
        return
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip("\"'"))


def get_api_key(api_key: str | None = None, env_file: str | Path | None = None) -> str:
    load_env_file(env_file)
    key = (api_key or os.getenv("RUNNINGHUB_API_KEY", "")).strip()
    if not key:
        raise ValidationError("RUNNINGHUB_API_KEY 未设置", field="RUNNINGHUB_API_KEY")
    return key


def create_client(api_key: str | None = None, env_file: str | Path | None = None) -> RunningHubClient:
    return RunningHubClient(api_key=get_api_key(api_key, env_file))


def normalize_type(type_: str) -> str:
    lowered = (type_ or "workflow").strip().lower()
    if lowered in {"webapp", "ai-app", "ai_app", "app"}:
        return "webapp"
    return "workflow"


def to_plain(value: Any) -> Any:
    if is_dataclass(value):
        return {k: to_plain(v) for k, v in asdict(value).items()}
    if isinstance(value, TaskStatus):
        return value.value
    if isinstance(value, list):
        return [to_plain(v) for v in value]
    if isinstance(value, dict):
        return {k: to_plain(v) for k, v in value.items()}
    return value


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


def doctor(api_key: str | None = None, env_file: str | Path | None = None) -> dict[str, Any]:
    load_env_file(env_file)
    info: dict[str, Any] = {
        "env": {"RUNNINGHUB_API_KEY": bool((api_key or os.getenv("RUNNINGHUB_API_KEY", "")).strip())},
        "sdk": {},
        "checks": {},
    }

    try:
        import runninghub_sdk

        info["sdk"]["version"] = getattr(runninghub_sdk, "__version__", "unknown")
    except Exception as exc:
        info["sdk"]["error"] = str(exc)

    if not info["env"]["RUNNINGHUB_API_KEY"]:
        info["checks"]["api_key"] = {"ok": False, "error": "RUNNINGHUB_API_KEY 未设置"}
        return info

    try:
        with create_client(api_key, env_file) as client:
            info["checks"]["api_key"] = {"ok": client.validate_api_key()}
            info["checks"]["queue"] = to_plain(client.get_queue_status())
    except Exception as exc:
        info["checks"]["api_key"] = {"ok": False, "error": str(exc)}

    return info


def detect(identifier: str, api_key: str | None = None, env_file: str | Path | None = None) -> dict[str, Any]:
    with create_client(api_key, env_file) as client:
        try:
            demo = client.get_ai_app_api_demo(identifier)
            return {
                "id": identifier,
                "type": "webapp",
                "name": demo.webapp_name,
                "node_count": len(demo.node_info_list),
            }
        except Exception as webapp_error:
            webapp_message = str(webapp_error)

        try:
            workflow = client.get_workflow_json_parsed(identifier)
            if isinstance(workflow, dict) and workflow:
                return {"id": identifier, "type": "workflow", "node_count": len(workflow)}
        except Exception as workflow_error:
            raise RuntimeError(
                f"无法识别 {identifier}: webapp={webapp_message}; workflow={workflow_error}"
            ) from workflow_error

    raise RuntimeError(f"无法识别 {identifier}")


def inspect_target(
    identifier: str,
    type_: str = "workflow",
    api_key: str | None = None,
    env_file: str | Path | None = None,
) -> dict[str, Any]:
    target_type = normalize_type(type_)
    with create_client(api_key, env_file) as client:
        if target_type == "webapp":
            demo = client.get_ai_app_api_demo(identifier)
            return {
                "id": identifier,
                "type": "webapp",
                "name": demo.webapp_name,
                "node_count": len(demo.node_info_list),
                "nodes": [
                    {
                        "nodeId": node.node_id,
                        "nodeName": node.node_name,
                        "fieldName": node.field_name,
                        "fieldType": node.field_type,
                        "fieldValue": node.field_value,
                        "description": node.description,
                    }
                    for node in demo.node_info_list
                ],
            }

        workflow = client.get_workflow_json_parsed(identifier)
        if not isinstance(workflow, dict):
            raise RuntimeError("非标准工作流结构")

        by_type: dict[str, list[str]] = {}
        editable: list[dict[str, Any]] = []
        for node_id, node in workflow.items():
            class_type = node.get("class_type", "?")
            inputs = node.get("inputs", {})
            by_type.setdefault(class_type, []).append(str(node_id))
            if isinstance(inputs, dict):
                editable.append(
                    {
                        "nodeId": str(node_id),
                        "classType": class_type,
                        "fields": list(inputs.keys()),
                    }
                )

        return {
            "id": identifier,
            "type": "workflow",
            "node_count": len(workflow),
            "by_type": {
                class_type: {"count": len(node_ids), "node_ids": node_ids[:20]}
                for class_type, node_ids in sorted(by_type.items())
            },
            "nodes": editable,
        }


def submit(
    identifier: str,
    type_: str = "workflow",
    overrides: list[dict[str, Any]] | None = None,
    *,
    api_key: str | None = None,
    env_file: str | Path | None = None,
    instance_type: str = "default",
    use_personal_queue: bool = False,
) -> dict[str, Any]:
    target_type = normalize_type(type_)
    node_overrides = overrides or []

    with create_client(api_key, env_file) as client:
        node_overrides, uploads = process_upload_overrides(client, node_overrides)
        modifier = build_modifier(node_overrides)

        if target_type == "webapp":
            task = client.run_ai_app_with_modifier(
                webapp_id=identifier,
                modifier=modifier,
                instance_type=instance_type,
            )
        else:
            task = client.run_with_modifier(
                workflow_id=identifier,
                modifier=modifier,
                add_metadata=True,
                instance_type=instance_type,
                use_personal_queue=use_personal_queue,
            )

    return {
        "id": identifier,
        "type": target_type,
        "task_id": task.task_id,
        "task_status": task.task_status.value,
        "client_id": task.client_id,
        "prompt_tips": task.prompt_tips,
        "node_overrides": node_overrides,
        "uploads": uploads,
    }


def status(task_id: str, api_key: str | None = None, env_file: str | Path | None = None) -> dict[str, Any]:
    with create_client(api_key, env_file) as client:
        task_status = client.get_status(task_id)
    return {"task_id": task_id, "status": task_status.value}


def wait_download(
    identifier: str,
    task_id: str,
    *,
    api_key: str | None = None,
    env_file: str | Path | None = None,
    output_dir: str | Path | None = None,
    poll_interval: float = 15,
    timeout: float = 1800,
) -> dict[str, Any]:
    out_dir = Path(output_dir) if output_dir else DEFAULT_OUTPUT_ROOT / identifier / task_id
    with create_client(api_key, env_file) as client:
        outputs = client.wait_for_completion(
            task_id,
            poll_interval=poll_interval,
            timeout=timeout,
        )
        paths = client.download_outputs(outputs, out_dir)

    files = [
        {
            "path": str(path),
            "name": path.name,
            "suffix": path.suffix.lower(),
            "size_bytes": path.stat().st_size,
            "size_mb": round(path.stat().st_size / 1024 / 1024, 2),
        }
        for path in paths
    ]
    return {
        "id": identifier,
        "task_id": task_id,
        "status": "SUCCESS",
        "output_dir": str(out_dir),
        "output_count": len(files),
        "output_files": files,
    }


def run(
    identifier: str,
    type_: str = "workflow",
    overrides: list[dict[str, Any]] | None = None,
    *,
    api_key: str | None = None,
    env_file: str | Path | None = None,
    output_dir: str | Path | None = None,
    poll_interval: float = 15,
    timeout: float = 1800,
    instance_type: str = "default",
    use_personal_queue: bool = False,
) -> dict[str, Any]:
    submitted = submit(
        identifier,
        type_,
        overrides,
        api_key=api_key,
        env_file=env_file,
        instance_type=instance_type,
        use_personal_queue=use_personal_queue,
    )
    downloaded = wait_download(
        identifier,
        submitted["task_id"],
        api_key=api_key,
        env_file=env_file,
        output_dir=output_dir,
        poll_interval=poll_interval,
        timeout=timeout,
    )
    return {**submitted, **downloaded}


def upload(
    file_path: str | Path,
    *,
    kind: str = "file",
    api_key: str | None = None,
    env_file: str | Path | None = None,
) -> dict[str, Any]:
    path = Path(file_path).expanduser()
    if not path.exists() or not path.is_file():
        raise FileNotFoundError(f"文件不存在: {path}")

    upload_kind = (kind or "file").strip().lower()
    with create_client(api_key, env_file) as client:
        if upload_kind == "image":
            result = client.upload_image(path)
            data = {
                "fileName": result.get("fileName", ""),
                "downloadUrl": result.get("downloadUrl", ""),
            }
        else:
            uploaded = client.upload_file(path)
            data = {
                "fileName": uploaded.file_name,
                "downloadUrl": uploaded.download_url,
            }

    return {
        "kind": upload_kind,
        "path": str(path),
        **data,
    }


def _run_git(args: list[str], cwd: Path) -> str:
    proc = subprocess.run(
        ["git", *args],
        cwd=str(cwd),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or proc.stdout.strip() or f"git {' '.join(args)} failed")
    return proc.stdout.strip()


def _version_key(tag: str) -> tuple[int, ...]:
    cleaned = tag.strip().removeprefix("refs/tags/").removeprefix("v")
    parts = re.findall(r"\d+", cleaned)
    return tuple(int(part) for part in parts) if parts else (0,)


def latest_remote_tag(repo_url: str = DEFAULT_REPO_URL) -> str:
    proc = subprocess.run(
        ["git", "ls-remote", "--tags", "--refs", repo_url],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or f"无法读取远程 tags: {repo_url}")

    tags = []
    for line in proc.stdout.splitlines():
        parts = line.split()
        if len(parts) >= 2 and parts[1].startswith("refs/tags/"):
            tags.append(parts[1].removeprefix("refs/tags/"))
    if not tags:
        raise RuntimeError(f"远程仓库没有 tag: {repo_url}")
    return sorted(tags, key=_version_key)[-1]


def self_update(
    *,
    repo_dir: str | Path | None = None,
    repo_url: str = DEFAULT_REPO_URL,
    tag: str | None = None,
    remote: str = "origin",
    dry_run: bool = False,
) -> dict[str, Any]:
    root = Path(repo_dir).expanduser().resolve() if repo_dir else Path(__file__).resolve().parents[2]
    if not (root / ".git").exists():
        raise RuntimeError(f"当前路径不是 runninghub-cli git 仓库: {root}")

    current_ref = _run_git(["rev-parse", "--abbrev-ref", "HEAD"], root)
    current_commit = _run_git(["rev-parse", "HEAD"], root)
    target_tag = tag or latest_remote_tag(repo_url)

    result = {
        "repo_dir": str(root),
        "repo_url": repo_url,
        "remote": remote,
        "from_ref": current_ref,
        "from_commit": current_commit,
        "target_tag": target_tag,
        "dry_run": dry_run,
    }
    if dry_run:
        return result

    _run_git(["fetch", "--tags", remote], root)
    _run_git(["checkout", target_tag], root)

    proc = subprocess.run(
        [sys.executable, "-m", "pip", "install", "-e", "."],
        cwd=str(root),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or proc.stdout.strip() or "pip install -e . failed")

    result["to_commit"] = _run_git(["rev-parse", "HEAD"], root)
    result["installed"] = True
    return result


def error_payload(exc: Exception) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "ok": False,
        "error_type": type(exc).__name__,
        "error": str(exc),
    }
    if isinstance(exc, RunningHubError):
        payload["code"] = getattr(exc, "code", None)
    if isinstance(exc, TaskError):
        payload["task_id"] = getattr(exc, "task_id", None)
        payload["failed_reason"] = getattr(exc, "failed_reason", None)
    if isinstance(exc, TimeoutError):
        payload["task_id"] = getattr(exc, "task_id", None)
        payload["timeout"] = getattr(exc, "timeout", None)
    return payload
