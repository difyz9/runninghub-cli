#!/usr/bin/env python3
"""Auto-generated standalone script from rh.webapp.img2vid.minimax_h3_fl2va_oss.v1.json.

Skill: rh.webapp.img2vid.minimax_h3_fl2va_oss.v1
Description: MiniMax H3 FL2VA open-source edition image-to-video webapp. Uses one reference image and a motion prompt to generate a short video.

Dependencies:
  pip install runninghub-sdk

Usage example:
  python rh.webapp.img2vid.minimax_h3_fl2va_oss.v1.py --reference_image_path /path/to/reference_image_path
"""

from __future__ import annotations

import argparse
import datetime
import os
import sys
from pathlib import Path
from typing import Any

from runninghub_sdk import RunningHubClient, modify_nodes

SKILL_NAME = 'rh.webapp.img2vid.minimax_h3_fl2va_oss.v1'
RESOURCE_ID = '2089409319493263361'
RESOURCE_TYPE = 'webapp'
MAPPING = [{'param': 'reference_image_path', 'nodeId': '4', 'fieldName': 'image', 'valueMode': 'upload'}, {'param': 'prompt_text', 'nodeId': '7', 'fieldName': 'prompt', 'valueMode': 'literal'}]
DEFAULT_INSTANCE_TYPE = 'default'
DEFAULT_TIMEOUT = 1800
DEFAULT_POLL_INTERVAL = 15
DEFAULT_OUTPUT_SUBDIR = 'rh.webapp.img2vid.minimax_h3_fl2va_oss.v1_outputs'
INPUTS = {'required': [{'name': 'reference_image_path', 'type': 'image', 'description': 'Local input image path'}], 'optional': [{'name': 'prompt_text', 'type': 'string', 'default': '保持人物主体一致，生成5秒轻微动作视频，镜头平稳，光线自然，画面清晰。', 'description': 'Prompt describing motion and style'}]}
INPUT_TYPES = {item["name"]: item.get("type", "string") for item in INPUTS.get("required", []) + INPUTS.get("optional", [])}
DOWNLOAD_POLICY = 'all'


def log(msg: str) -> None:
    print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] {msg}")


def section(title: str) -> None:
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print(f"{'=' * 60}")


def resolve_api_key(value: str | None) -> str:
    if value:
        return value
    key = os.getenv("RUNNINGHUB_API_KEY", "").strip()
    if key:
        return key
    print("Error: RUNNINGHUB_API_KEY not set. Use --api-key or env var.", file=sys.stderr)
    sys.exit(1)


def make_output_dir(base: str | None, subdir: str) -> Path:
    root = Path(base).expanduser().resolve() if base else Path.cwd() / "outputs"
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    out = root / f"{subdir}_{ts}"
    out.mkdir(parents=True, exist_ok=True)
    return out


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog='rh-rh.webapp.img2vid.minimax_h3_fl2va_oss.v1', description='MiniMax H3 FL2VA open-source edition image-to-video webapp. Uses one reference image and a motion prompt to generate a short video.')
    p.add_argument("--api-key", help="RunningHub API key (default: RUNNINGHUB_API_KEY)")
    p.add_argument("--instance-type", default=DEFAULT_INSTANCE_TYPE, help="RunningHub instance type")
    p.add_argument("--poll-interval", type=float, default=DEFAULT_POLL_INTERVAL, help="Polling interval in seconds")
    p.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT, help="Task timeout in seconds")
    p.add_argument("--output-dir", default=None, help="Base output dir (default: ./outputs)")
    p.add_argument('--reference_image_path', required=True, help='Local input image path')
    p.add_argument('--prompt_text', default='保持人物主体一致，生成5秒轻微动作视频，镜头平稳，光线自然，画面清晰。', help='Prompt describing motion and style')
    return p


def build_nodes(args: argparse.Namespace, client: RunningHubClient) -> list[dict[str, Any]]:
    modifier = modify_nodes()

    for m in MAPPING:
        param = m["param"]
        node_id = m["nodeId"]
        field_name = m["fieldName"]
        mode = m.get("valueMode", "literal")

        value = getattr(args, param)

        if mode == "upload":
            path = Path(str(value)).expanduser().resolve()
            if not path.exists():
                print(f"Error: file not found for {param}: {path}", file=sys.stderr)
                sys.exit(1)
            log(f"Uploading {param}: {path}")
            if INPUT_TYPES.get(param) == "image":
                uploaded = client.upload_image(str(path))
                value = uploaded["fileName"]
            else:
                uploaded = client.upload_file(str(path))
                value = uploaded.file_name
            log(f"Uploaded as: {value}")

        modifier.set(node_id, field_name, value)

    return modifier.to_dict_list()


def submit_and_wait(client: RunningHubClient, node_info_list: list[dict[str, Any]], instance_type: str, poll_interval: float, timeout: float) -> Any:
    section("Submitting Task")

    if RESOURCE_TYPE == "webapp":
        task = client.run_ai_app(
            webapp_id=RESOURCE_ID,
            node_info_list=node_info_list,
            add_metadata=True,
            instance_type=instance_type,
        )
    else:
        task = client.run(
            workflow_id=RESOURCE_ID,
            node_info_list=node_info_list,
            add_metadata=True,
            instance_type=instance_type,
            use_personal_queue=False,
        )

    log(f"task_id: {task.task_id}")
    log(f"status: {task.task_status}")

    if not task.task_id:
        print("Error: task_id is empty", file=sys.stderr)
        sys.exit(1)

    section("Waiting for Completion")
    last_status: Any = None

    def on_status_change(status: Any) -> None:
        nonlocal last_status
        if status != last_status:
            log(f"status -> {status}")
            last_status = status

    return client.wait_for_completion(
        task_id=task.task_id,
        poll_interval=poll_interval,
        timeout=timeout,
        on_status_change=on_status_change,
    )


def filter_outputs_by_policy(outputs: list[Any], policy: str) -> list[Any]:
    """Pick which outputs to download.

    'all' keeps everything. 'keep_smallest' / 'keep_largest' keep a single
    output ranked by the remote file size (a cheap HEAD request; falls back
    to list order when sizes are unknown).
    """
    if policy == "all" or len(outputs) <= 1:
        return list(outputs)

    import urllib.request

    def remote_size(output: Any) -> int:
        try:
            req = urllib.request.Request(output.file_url, method="HEAD")
            with urllib.request.urlopen(req, timeout=10) as resp:
                return int(resp.headers.get("Content-Length") or 0)
        except Exception:
            return 0

    sized = [(remote_size(out), out) for out in outputs]
    if all(size == 0 for size, _ in sized):
        log(f"could not determine output sizes; keeping first output for policy '{policy}'")
        return outputs[:1]
    sized.sort(key=lambda item: item[0])
    return [sized[0][1]] if policy == "keep_smallest" else [sized[-1][1]]


def download_outputs(client: RunningHubClient, outputs: Any, out_dir: Path) -> list[Path]:
    section("Downloading Outputs")
    selected = filter_outputs_by_policy(outputs, DOWNLOAD_POLICY)
    if len(selected) < len(outputs):
        log(f"download policy '{DOWNLOAD_POLICY}': keeping {len(selected)} of {len(outputs)} outputs")
    paths = client.download_outputs(selected, out_dir)
    for p in paths:
        size = p.stat().st_size
        size_str = f"{size / 1024 / 1024:.1f} MB" if size > 1024 * 1024 else f"{size / 1024:.0f} KB"
        log(f"saved: {p} ({size_str})")
    return paths


def main() -> int:
    args = build_parser().parse_args()
    api_key = resolve_api_key(args.api_key)

    out_dir = make_output_dir(args.output_dir, DEFAULT_OUTPUT_SUBDIR)
    section("Skill Info")
    log(f"skill: {SKILL_NAME}")
    log(f"resource_type: {RESOURCE_TYPE}")
    log(f"resource_id: {RESOURCE_ID}")
    log(f"instance_type: {args.instance_type}")

    try:
        with RunningHubClient(api_key=api_key) as client:
            node_info_list = build_nodes(args, client)
            outputs = submit_and_wait(client, node_info_list, args.instance_type, args.poll_interval, args.timeout)
            download_outputs(client, outputs, out_dir)
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    section("Done")
    log(f"outputs saved to: {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
