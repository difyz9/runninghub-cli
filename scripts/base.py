"""Shared utilities for RunningHub CLI tools."""

from __future__ import annotations

import datetime
import os
import sys
from pathlib import Path
from typing import Any, Dict, List

# ==================== Env helpers ====================


def load_env_file(filepath: Path) -> None:
    """Load key=value pairs from a .env file (delegates to runninghub_cli.service)."""
    from runninghub_cli.service import load_env_file as _load
    _load(filepath)


def bootstrap_env() -> None:
    """Load .env files from cwd and repo root (if in repo)."""
    load_env_file(Path.cwd() / ".env")
    # walk up looking for repo root
    for parent in Path.cwd().parents:
        if (parent / "pyproject.toml").exists() or (parent / "src" / "runninghub_sdk" / "__init__.py").exists():
            load_env_file(parent / ".env")
            break


def get_required_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        print(f"Error: Required environment variable {name} is not set.", file=sys.stderr)
        sys.exit(1)
    return value


def get_env(name: str, default: str = "") -> str:
    return os.getenv(name, "").strip() or default


def get_env_int(name: str, default: int = 0) -> int:
    raw = os.getenv(name, "").strip()
    return int(raw) if raw else default


def get_env_float(name: str, default: float = 0.0) -> float:
    raw = os.getenv(name, "").strip()
    return float(raw) if raw else default


# ==================== Output directory ====================


def make_output_dir(base: str | None, subdir: str) -> Path:
    """Create and return an output directory with timestamp."""
    root = Path(base).expanduser().resolve() if base else Path.cwd() / "outputs"
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    out = root / f"{subdir}_{ts}"
    out.mkdir(parents=True, exist_ok=True)
    return out


# ==================== Printing helpers ====================


def log(msg: str) -> None:
    print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] {msg}")


def section(title: str) -> None:
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print(f"{'=' * 60}")


# ==================== API key helpers ====================


def resolve_api_key(api_key: str | None = None) -> str:
    if api_key:
        return api_key
    key = os.getenv("RUNNINGHUB_API_KEY", "").strip()
    if key:
        return key
    print("Error: RUNNINGHUB_API_KEY not set. Provide --api-key or set the environment variable.", file=sys.stderr)
    sys.exit(1)


# ==================== Workflow / AI App helpers ====================


def create_node_info_list(overrides: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """DEPRECATED: Use `runninghub_cli.service.parse_overrides()` + `build_modifier()` instead.

    Build a node_info_list payload from simple override dicts.
    Retained for backward compatibility with external scripts.
    """
    return [
        {
            "nodeId": item["node_id"],
            "fieldName": item["field_name"],
            "fieldValue": item["field_value"],
        }
        for item in overrides
    ]


def print_request_summary(method: str, identifier: str, nodes: List[Dict[str, Any]]) -> None:
    section("Request Preview")
    print(f"  method:       {method}")
    print(f"  identifier:   {identifier}")
    print(f"  node_count:   {len(nodes)}")
    for n in nodes:
        print(f"    nodeId={n['nodeId']} | {n['fieldName']}={n['fieldValue']}")


# ==================== Unified Runner helpers ====================


UPLOAD_PREFIX = "@upload:"


def process_uploads(client: Any, nodes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Upload images for values prefixed with @upload: and replace with fileName.

    The @upload: path can be:
      - @upload:./relative/path.png
      - @upload:/absolute/path.png
      - @upload:path/to/file.png (relative to CWD)
    """
    for item in nodes:
        value = item.get("fieldValue", "")
        if not isinstance(value, str) or not value.startswith(UPLOAD_PREFIX):
            continue

        path_str = value[len(UPLOAD_PREFIX):].strip()
        img_path = Path(path_str)
        if not img_path.is_absolute():
            img_path = Path.cwd() / path_str
        img_path = img_path.resolve()

        if not img_path.exists():
            print(f"Error: Upload image not found: {img_path}", file=sys.stderr)
            sys.exit(1)

        log(f"Uploading image for node {item['nodeId']}.{item['fieldName']}: {img_path}")
        uploaded = client.upload_image(str(img_path))
        item["fieldValue"] = uploaded["fileName"]
        log(f"  -> {uploaded['fileName']}")

    return nodes


def submit_and_wait(
    client: Any,
    mode: str,
    resource_id: str,
    nodes: List[Dict[str, Any]],
    poll_interval: float,
    timeout: float,
) -> Any:
    """Submit a task (workflow or AI app) and wait for completion.

    Args:
        client: RunningHubClient instance
        mode: "workflow" → client.run(), "ai-app" → client.run_ai_app()
        resource_id: workflow_id or webapp_id
        nodes: node_info_list payload
        poll_interval: seconds between polls
        timeout: max wait in seconds
    """
    section("Submitting Task")

    if mode == "workflow":
        section("Resource Info")
        log("  type:        Workflow")
        log(f"  workflow_id: {resource_id}")

        task = client.run(
            workflow_id=resource_id,
            node_info_list=nodes,
            add_metadata=True,
            instance_type="default",
            use_personal_queue=False,
        )
    else:
        section("Resource Info")
        log("  type:       AI App")
        log(f"  webapp_id:  {resource_id}")

        task = client.run_ai_app(
            webapp_id=resource_id,
            node_info_list=nodes,
            add_metadata=True,
        )

    log(f"task_id: {task.task_id}")
    log(f"status:  {task.task_status}")

    if not task.task_id:
        print("Error: task_id is empty", file=sys.stderr)
        sys.exit(1)

    # Wait for completion
    section("Waiting for Completion")
    last_status: Any = None

    def on_status_change(status: Any) -> None:
        nonlocal last_status
        if status != last_status:
            log(f"status -> {status}")
            last_status = status

    outputs = client.wait_for_completion(
        task_id=task.task_id,
        poll_interval=poll_interval,
        timeout=timeout,
        on_status_change=on_status_change,
    )

    return outputs


def download_results(client: Any, outputs: Any, output_dir: Path) -> List[Path]:
    """Download all output files from a completed task."""
    section("Downloading Results")
    paths = client.download_outputs(outputs, output_dir)
    for p in paths:
        size = p.stat().st_size
        size_str = f"{size / 1024 / 1024:.1f} MB" if size > 1024 * 1024 else f"{size / 1024:.0f} KB"
        log(f"saved: {p} ({size_str})")
    return paths
