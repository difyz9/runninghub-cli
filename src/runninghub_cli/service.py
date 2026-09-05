"""Reusable service functions backed by runninghub-sdk."""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any

from runninghub_sdk import RunningHubClient, TaskStatus
from runninghub_sdk.exceptions import RunningHubError, TaskError, TimeoutError, ValidationError

from . import auth_store as _auth_store
from . import execution_ops as _execution_ops
from . import overrides as _overrides
from . import registry_ops as _registry_ops

_execution_run = _execution_ops.run
_execution_status = _execution_ops.status
_execution_submit = _execution_ops.submit
_execution_task_detail = _execution_ops.task_detail
_execution_task_detail_with_client = _execution_ops.task_detail_with_client
_execution_upload = _execution_ops.upload
_execution_wait_download = _execution_ops.wait_download

# Backward-compatible exports for callers still using `runninghub_cli.service`.
login = _auth_store.login
logout = _auth_store.logout
_resolve_auth = _auth_store._resolve_auth
_resolve_bearer = _auth_store._resolve_bearer

UPLOAD_PREFIX = _overrides.UPLOAD_PREFIX
UPLOAD_URL_PREFIX = _overrides.UPLOAD_URL_PREFIX
_field_name = _overrides._field_name
_field_value_key = _overrides._field_value_key
_node_id = _overrides._node_id
parse_overrides = _overrides.parse_overrides
parse_node_shorthand = _overrides.parse_node_shorthand
build_modifier = _overrides.build_modifier
infer_upload_kind = _overrides.infer_upload_kind
process_upload_overrides = _overrides.process_upload_overrides
upload_with_client = _overrides.upload_with_client

REGISTRY_FILE = _registry_ops.REGISTRY_FILE
PAYLOAD_DIR = _registry_ops.PAYLOAD_DIR
QUALITY_ICONS = _registry_ops.QUALITY_ICONS
QUALITY_ORDER = _registry_ops.QUALITY_ORDER

_load_registry = _registry_ops._load_registry
_iter_all_entries = _registry_ops._iter_all_entries
_find_entry_by_id = _registry_ops._find_entry_by_id
_get_payload_field = _registry_ops._get_payload_field
_payload_path = _registry_ops._payload_path
_has_payload = _registry_ops._has_payload
_load_payload = _registry_ops._load_payload
_save_registry = _registry_ops._save_registry

get_registry_summary = _registry_ops.get_registry_summary
get_verified_entries = _registry_ops.get_verified_entries
get_defaults = _registry_ops.get_defaults
set_default = _registry_ops.set_default
get_tiktok_remake_ids = _registry_ops.get_tiktok_remake_ids
check_quality = _registry_ops.check_quality
set_entry_quality = _registry_ops.set_entry_quality

DEFAULT_OUTPUT_ROOT = Path.cwd() / "runninghub_outputs"
DEFAULT_REPO_URL = "https://gitee.com/difyz/runninghub-cli.git"


# 关键节点类型映射 — inspect 输出中会高亮标注这些节点，
# 方便 agent 分析工作流时快速定位需要定制的参数。
KEY_NODE_TYPES: dict[str, str] = {
    "LoadImage": "图片输入",
    "LoadVideo": "视频输入",
    "VHS_LoadVideo": "视频输入",
    "VHS_LoadAudioUpload": "音频输入",
    "LoadAudio": "音频输入",
    "SaveImage": "图片输出",
    "SaveVideo": "视频输出",
    "CR Prompt Text": "文本提示词",
    "PrimitiveStringMultiline": "文本输入",
    "easy positive": "正向提示词",
    "easy negative": "负向提示词",
    "CLIPTextEncode": "文本编码(含提示词)",
    "Seed": "随机种子",
}

# ComfyUI 内部管道节点 — 这些是模型加载、采样器、数学运算等基础设施，
# 用户一般不需要定制。inspect 输出中会将它们归入 plumbing_nodes。
PLUMBING_TYPES: set[str] = {
    # 模型加载
    "CLIPLoader", "UNETLoader", "VAELoader", "CheckpointLoader",
    "DualCFGLoader", "GLIGENLoader", "HypernetworkLoader",
    "LoraLoader", "ControlNetLoader", "DiffControlNetLoader",
    "StyleModelLoader", "CLIPVisionLoader", "IPAdapterLoader",
    "InstructPixToPixConditioning",
    # 采样器基础设施
    "KSampler", "KSamplerSelect", "BasicScheduler", "SamplerCustomAdvanced",
    "CFGGuider", "Flux2Scheduler", "Sampler", "Guider",
    "RandomNoise",
    # VAE 管道
    "VAEEncode", "VAEDecode",
    # 数学/常量/辅助
    "INTConstant", "FloatConstant", "SomethingToString",
    "Split String", "StringFunction|pysssss", "ShowText|pysssss",
    "ShowAnything|pysssss", "PreviewImage",
    # 文本处理/批处理
    "CR Text Concatenate", "List of strings [Crystools]",
    "PromptBatchQueue",
    # 图层工具
    "ReferenceLatent", "GetImageSize", "ImageScale",
    # Latent 操作
    "EmptyLatentImage", "EmptyFlux2LatentImage",
    "LatentUpscale", "LatentUpscaleBy", "LatentComposite",
    "LatentBatch", "LatentFromBatch",
}
# 以上集合中部分条目是前缀匹配（如 "ImageScale" 匹配 "ImageScaleByAspectRatio V2"）
# 使用 is_plumbing_type() 函数进行精确匹配

# 关键节点中值得关注的 input field key — 忽略常规控制参数
KEY_FIELD_KEYS: dict[str, set[str]] = {
    "LoadImage": {"image"},
    "LoadVideo": {"video"},
    "VHS_LoadVideo": {"video"},
    "VHS_LoadAudioUpload": {"audio"},
    "LoadAudio": {"audio"},
    "SaveImage": {"images", "filename_prefix"},
    "SaveVideo": {"filename_prefix"},
    "CR Prompt Text": {"text", "prompt"},
    "PrimitiveStringMultiline": {"string", "text"},
    "easy positive": {"positive", "pos", "text"},
    "easy negative": {"negative", "neg", "text"},
    "CLIPTextEncode": {"text"},
    "Seed": {"seed", "value", "noise_seed"},
}


def _is_plumbing(class_type: str) -> bool:
    """判断节点类型是否为 ComfyUI 内部管道节点（用户不需定制）。"""
    if not class_type:
        return True
    # 精确匹配
    if class_type in PLUMBING_TYPES:
        return True
    # 前缀匹配 — 如 "LayerUtility: ImageScale..." → PLUMBING_TYPES 中 "ImageScale" 命中
    for prefix in PLUMBING_TYPES:
        if class_type.startswith(prefix):
            return True
    # LayerUtility 全家桶都是管道节点
    return bool(class_type.startswith("LayerUtility:") or class_type.startswith("layer_utility:"))


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


def bootstrap_env() -> None:
    """Load .env from cwd, then walk up looking for repo root.

    Script-friendly: called by scripts/ tools so they find .env
    whether run from the repo root or a subdirectory.
    """
    load_env_file(Path.cwd() / ".env")
    for parent in Path.cwd().parents:
        if (parent / "pyproject.toml").exists() or (parent / "src" / "runninghub_cli" / "__init__.py").exists():
            load_env_file(parent / ".env")
            break


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
    if lowered in {"auto", ""}:
        return "auto"
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
    type_: str = "auto",
    verbose: bool = False,
    api_key: str | None = None,
    env_file: str | Path | None = None,
) -> dict[str, Any]:
    target_type = normalize_type(type_)
    with create_client(api_key, env_file) as client:
        if target_type == "webapp":
            return _inspect_webapp(identifier, client)

        if target_type == "auto":
            # Auto-detect: try webapp first, then workflow
            try:
                return _inspect_webapp(identifier, client)
            except Exception:
                target_type = "workflow"

        # workflow (explicit or auto-detect fallback)
        workflow = client.get_workflow_json_parsed(identifier)
        if not isinstance(workflow, dict):
            raise RuntimeError("非标准工作流结构")

        by_type: dict[str, list[str]] = {}
        user_nodes: list[dict[str, Any]] = []
        all_editable: list[dict[str, Any]] = []
        plumbing_count = 0
        for node_id, node in workflow.items():
            class_type = node.get("class_type", "?")
            inputs = node.get("inputs", {})
            by_type.setdefault(class_type, []).append(str(node_id))
            if not isinstance(inputs, dict):
                continue
            entry = {
                "nodeId": str(node_id),
                "classType": class_type,
                "fields": list(inputs.keys()),
            }
            all_editable.append(entry)
            if _is_plumbing(class_type):
                plumbing_count += 1
            else:
                user_nodes.append(entry)

        result: dict[str, Any] = {
            "id": identifier,
            "type": "workflow",
            "node_count": len(workflow),
        }
        if verbose:
            result["nodes"] = all_editable
            result["by_type"] = {
                class_type: {
                    "count": len(node_ids),
                    "node_ids": node_ids[:20],
                    "is_plumbing": _is_plumbing(class_type),
                }
                for class_type, node_ids in sorted(by_type.items())
            }
        else:
            result["plumbing_count"] = plumbing_count

        # 关键节点 — 对 agent 而言唯一需要关注的区域：nodeId + 标签 + 可覆盖字段 + 当前值
        key_nodes = _collect_workflow_key_nodes(workflow)
        if key_nodes:
            result["key_nodes"] = key_nodes

        return result


def _collect_workflow_key_nodes(workflow: dict[str, Any]) -> list[dict[str, Any]]:
    """从工作流节点图中收集关键节点及其关键参数。"""
    collected: list[dict[str, Any]] = []

    for node_id, node in workflow.items():
        class_type = node.get("class_type", "?")
        label = KEY_NODE_TYPES.get(class_type)
        if label is None:
            continue

        inputs = node.get("inputs", {})
        if not isinstance(inputs, dict):
            inputs = {}

        # 提取该类型中值得关注的 input field 及其实际值
        interesting_keys = KEY_FIELD_KEYS.get(class_type, set())
        params: dict[str, Any] = {}
        for key in sorted(inputs.keys()):
            if interesting_keys and key in interesting_keys:
                params[key] = inputs[key]
            elif not interesting_keys:
                # 没有特别标注时，拿所有非链接/常规控制参数
                val = inputs[key]
                if isinstance(val, str) and len(val) > 120:
                    val = val[:120] + "..."
                if key not in ("seed_num", "seed", "steps", "cfg", "sampler_name", "scheduler", "denoise"):
                    params[key] = val

        collected.append({
            "nodeId": str(node_id),
            "classType": class_type,
            "label": label,
            "fields": list(inputs.keys()),
            "params": params,
        })

    # 按 label 分组排序，同类节点排在一起
    collected.sort(key=lambda x: (x["label"], x["nodeId"]))
    return collected


def _inspect_webapp(identifier: str, client: Any) -> dict[str, Any]:
    demo = client.get_ai_app_api_demo(identifier)
    nodes = [
        {
            "nodeId": node.node_id,
            "nodeName": node.node_name,
            "fieldName": node.field_name,
            "fieldType": node.field_type,
            "fieldValue": node.field_value,
            "fieldData": node.field_data,
            "description": node.description,
            "descriptionEn": node.description_en,
        }
        for node in demo.node_info_list
    ]

    result: dict[str, Any] = {
        "id": identifier,
        "type": "webapp",
        "name": demo.webapp_name,
        "node_count": len(nodes),
        "nodes": nodes,
    }

    # AI App 也尝试标注关键节点（按 fieldName 模糊匹配）
    key_nodes = _collect_webapp_key_nodes(nodes)
    if key_nodes:
        result["key_nodes"] = key_nodes

    return result


def _collect_webapp_key_nodes(nodes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """从 AI App 节点列表中标注关键节点。"""
    # 反向索引：从 KEY_NODE_TYPES 中找 fieldName 可能对应的关键标签
    collected: list[dict[str, Any]] = []

    for node in nodes:
        field_name = (node.get("fieldName") or "").strip().lower()
        node_name = (node.get("nodeName") or "").strip().lower()
        match_label = None

        for class_type, label in KEY_NODE_TYPES.items():
            ct_lower = class_type.lower()
            if ct_lower in field_name or ct_lower in node_name:
                match_label = label
                break

        # 额外的启发式匹配
        if match_label is None:
            if field_name in ("text", "prompt", "positive", "negative"):
                match_label = "文本提示词"
            elif field_name in ("image", "img"):
                match_label = "图片输入"
            elif field_name in ("video",):
                match_label = "视频输入"
            elif field_name == "seed":
                match_label = "随机种子"

        if match_label:
            collected.append({
                "nodeId": node["nodeId"],
                "fieldName": node.get("fieldName"),
                "fieldValue": node.get("fieldValue"),
                "label": match_label,
            })

    collected.sort(key=lambda x: (x["label"], x["nodeId"]))
    return collected


def submit(
    identifier: str,
    type_: str = "workflow",
    overrides: list[dict[str, Any]] | None = None,
    *,
    api_key: str | None = None,
    env_file: str | Path | None = None,
    instance_type: str = "default",
    use_personal_queue: bool = False,
    access_password: str | None = None,
) -> dict[str, Any]:
    return _execution_submit(
        identifier,
        type_,
        overrides,
        api_key=api_key,
        env_file=env_file,
        instance_type=instance_type,
        use_personal_queue=use_personal_queue,
        access_password=access_password,
        create_client_fn=create_client,
        normalize_type_fn=normalize_type,
        process_upload_overrides_fn=process_upload_overrides,
        build_modifier_fn=build_modifier,
    )


def status(task_id: str, api_key: str | None = None, env_file: str | Path | None = None) -> dict[str, Any]:
    return _execution_status(
        task_id,
        api_key=api_key,
        env_file=env_file,
        create_client_fn=create_client,
    )


def task_detail_with_client(client: RunningHubClient, task_id: str) -> dict[str, Any]:
    return _execution_task_detail_with_client(
        client,
        task_id,
        to_plain_fn=to_plain,
    )


def task_detail(task_id: str, api_key: str | None = None, env_file: str | Path | None = None) -> dict[str, Any]:
    return _execution_task_detail(
        task_id,
        api_key=api_key,
        env_file=env_file,
        create_client_fn=create_client,
        task_detail_with_client_fn=task_detail_with_client,
    )


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
    return _execution_wait_download(
        identifier,
        task_id,
        api_key=api_key,
        env_file=env_file,
        output_dir=output_dir,
        poll_interval=poll_interval,
        timeout=timeout,
        default_output_root=DEFAULT_OUTPUT_ROOT,
        create_client_fn=create_client,
        task_detail_with_client_fn=task_detail_with_client,
    )


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
    access_password: str | None = None,
) -> dict[str, Any]:
    return _execution_run(
        identifier,
        type_,
        overrides,
        api_key=api_key,
        env_file=env_file,
        output_dir=output_dir,
        poll_interval=poll_interval,
        timeout=timeout,
        instance_type=instance_type,
        use_personal_queue=use_personal_queue,
        access_password=access_password,
        submit_fn=submit,
        wait_download_fn=wait_download,
    )


def upload(
    file_path: str | Path,
    *,
    kind: str = "file",
    api_key: str | None = None,
    env_file: str | Path | None = None,
) -> dict[str, Any]:
    return _execution_upload(
        file_path,
        kind=kind,
        api_key=api_key,
        env_file=env_file,
        create_client_fn=create_client,
    )


def _run_git(args: list[str], cwd: Path) -> str:
    proc = subprocess.run(
        ["git", *args],
        cwd=str(cwd),
        text=True,
        capture_output=True,
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
        capture_output=True,
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
        capture_output=True,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or proc.stdout.strip() or "pip install -e . failed")

    result["to_commit"] = _run_git(["rev-parse", "HEAD"], root)
    result["installed"] = True
    return result


# ── New SDK 1.1.9+ APIs ──────────────────────────────────────


def get_account_status(
    api_key: str | None = None,
    env_file: str | Path | None = None,
) -> dict[str, Any]:
    """查询账户状态（剩余额度、当前任务数等）。"""
    with create_client(api_key, env_file) as client:
        status = client.get_account_status()
        return {
            "remain_coins": status.remain_coins,
            "current_task_counts": status.current_task_counts,
            "remain_money": status.remain_money,
            "currency": status.currency,
            "api_type": status.api_type,
        }


def get_queue_status(
    api_key: str | None = None,
    env_file: str | Path | None = None,
) -> dict[str, Any]:
    """查询队列状态（运行中/排队中的任务数）。"""
    with create_client(api_key, env_file) as client:
        q = client.get_queue_status()
        return {
            "api_key_type": q.api_key_type,
            "concurrent_limit": q.concurrent_limit,
            "running_count": int(q.running_count),
            "queued_count": int(q.queued_count),
            "total_current_tasks": int(q.total_current_tasks),
        }


def get_task_history(
    status: str | None = None,
    task_type: str | None = None,
    size: int = 20,
    page: int = 1,
    api_key: str | None = None,
    env_file: str | Path | None = None,
) -> dict[str, Any]:
    """查询任务历史记录。"""
    import httpx
    from runninghub_sdk.typedefs.output_history import OutputHistoryV2Request

    req = OutputHistoryV2Request(
        size=size,
        current=page,
        has_output=True,
        from_id="",
        task_name="",
        reload_data=False,
    )
    if status:
        req.status = [s.strip() for s in status.split(",")]
    if task_type:
        req.task_type = [t.strip() for t in task_type.split(",")]

    with create_client(api_key, env_file) as client:
        bearer = _resolve_bearer(client)
        if not bearer:
            raise ValidationError(
                "查询历史记录需要用户认证。请先运行:\n"
                "  runninghub login --username <手机号> --password <密码>",
                field="access_token",
            )
        # API /api/output/v2/history 返回 data 为纯数组，
        # SDK OutputHistoryV2Response 无法处理，直接调用 httpx
        resp = httpx.post(
            f"{RunningHubClient.BASE_URL}/api/output/v2/history",
            json=req.to_dict(),
            headers={"Authorization": f"Bearer {bearer}", "Content-Type": "application/json"},
            timeout=30,
        )
        resp.raise_for_status()
        body = resp.json()
        records = body.get("data") if isinstance(body.get("data"), list) else []
        if not isinstance(records, list):
            records = []

        return {
            "records": records,
            "total": len(records),
            "page": page,
            "size": size,
            "has_next": len(records) >= size,
        }


def get_call_log_detail(
    task_id: str,
    user_id: str | None = None,
    api_key: str | None = None,
    env_file: str | Path | None = None,
) -> dict[str, Any]:
    """获取任务的详细调用日志（请求参数、响应详情、费用等）。"""
    with create_client(api_key, env_file) as client:
        bearer_token = _resolve_bearer(client)
        if not bearer_token:
            raise ValidationError(
                "查询调用日志需要用户认证。请先运行:\n"
                "  runninghub login --username <手机号> --password <密码>",
                field="access_token",
            )

        # 如果未提供 user_id，尝试从 JWT 中提取
        resolved_user_id = user_id
        if not resolved_user_id:
            auth = _resolve_auth()
            if auth and auth.get("user_id"):
                resolved_user_id = auth["user_id"]
        if not resolved_user_id:
            try:
                parts = bearer_token.split(".")
                if len(parts) == 3:
                    import base64
                    padded = parts[1] + "=" * (4 - len(parts[1]) % 4)
                    try:
                        payload = json.loads(base64.urlsafe_b64decode(padded))
                        if "identify" in payload:
                            resolved_user_id = str(payload["identify"])
                    except Exception:
                        pass
            except Exception:
                pass

        if not resolved_user_id:
            raise ValidationError(
                "需要 user_id 才能查询调用日志。请先运行:\n"
                "  runninghub login --username <手机号> --password <密码>\n"
                "或在命令中传入 --user-id <用户ID>",
                field="user_id",
            )

        detail = client.get_call_log_detail(
            task_id, resolved_user_id, access_token=bearer_token,
        )

        result: dict[str, Any] = {}

        if detail.basic_info:
            b = detail.basic_info
            result["basic_info"] = {
                "task_id": b.task_id,
                "api_name": b.api_name,
                "api_type": b.api_type,
                "api_key_type": b.api_key_type,
                "status": b.task_status,
                "call_time": b.call_time,
                "duration": b.duration,
                "amount": b.amount,
                "coin_num": b.coin_num,
            }

        if detail.cost_info:
            c = detail.cost_info
            result["cost_info"] = {"amount": c.amount, "coin_num": c.coin_num}

        if detail.request_info:
            result["request_params"] = detail.request_info.api_request_params

        if detail.response_info:
            r = detail.response_info
            resp_info: dict[str, Any] = {
                "task_id": r.task_id,
                "status": r.status,
                "error_code": r.error_code,
                "error_message": r.error_message,
                "failed_reason": r.failed_reason,
                "client_id": r.client_id,
                "prompt_tips": r.prompt_tips,
            }
            if r.results:
                resp_info["results"] = [
                    {
                        "node_id": o.node_id,
                        "output_type": o.output_type,
                        "url": o.url,
                        "text": o.text,
                    }
                    for o in r.results
                ]
            if r.usage:
                resp_info["usage"] = {
                    "consume_money": r.usage.consume_money,
                    "consume_coins": r.usage.consume_coins,
                    "task_cost_time": r.usage.task_cost_time,
                    "third_party_consume_money": r.usage.third_party_consume_money,
                }
            result["response_info"] = resp_info

        if detail.outputs:
            result["outputs"] = [
                {
                    "output_name": o.output_name,
                    "output_type": o.output_type,
                    "file_url": o.file_url,
                    "file_preview_url": o.file_preview_url,
                }
                for o in detail.outputs
            ]

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
    task_detail = getattr(exc, "task_detail", None)
    if task_detail:
        payload["task_detail"] = task_detail
    return payload
