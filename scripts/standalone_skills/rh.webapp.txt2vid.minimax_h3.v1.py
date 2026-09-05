#!/usr/bin/env python3
"""Auto-generated standalone script from rh.webapp.txt2vid.minimax_h3.v1.json.

Skill: rh.webapp.txt2vid.minimax_h3.v1
Description: MiniMax H3 加速版 图文一键生视频（文生视频模式）。纯文本提示词生成视频，不传首尾帧图。支持分辨率、时长、画面比例调节。

Dependencies:
  pip install runninghub-sdk

Usage example:
  python rh.webapp.txt2vid.minimax_h3.v1.py --prompt_text 'prompt_text_value'
"""

from __future__ import annotations

import argparse
import datetime
import os
import sys
from pathlib import Path
from typing import Any

from runninghub_sdk import RunningHubClient, modify_nodes

SKILL_NAME = 'rh.webapp.txt2vid.minimax_h3.v1'
RESOURCE_ID = '2084968440439336962'
RESOURCE_TYPE = 'webapp'
MAPPING = [{'param': 'prompt_text', 'nodeId': '134', 'fieldName': 'prompt', 'valueMode': 'literal'}, {'param': 'aspect_ratio', 'nodeId': '115', 'fieldName': 'aspect_ratio', 'valueMode': 'literal'}, {'param': 'resolution', 'nodeId': '225', 'fieldName': 'select', 'valueMode': 'literal'}, {'param': 'duration', 'nodeId': '205', 'fieldName': 'select', 'valueMode': 'literal'}]
DEFAULT_INSTANCE_TYPE = 'default'
DEFAULT_TIMEOUT = 1500
DEFAULT_POLL_INTERVAL = 15
DEFAULT_OUTPUT_SUBDIR = 'rh.webapp.txt2vid.minimax_h3.v1_outputs'
INPUTS = {'required': [{'name': 'prompt_text', 'type': 'string', 'description': '文生视频提示词。建议写清镜头运动、主体、动作、光线、色彩风格与质感，中文效果最好。'}], 'optional': [{'name': 'aspect_ratio', 'type': 'string', 'default': '16:9 (Widescreen)', 'description': '画面比例。可选：1:1 (Square)、2:3 (Portrait Photo)、3:2 (Photo)、3:4 (Portrait Standard)、4:3 (Standard)、9:16 (Portrait Widescreen)、16:9 (Widescreen)、21:9 (Ultrawide)。横屏视频推荐 16:9 (Widescreen)。'}, {'name': 'resolution', 'type': 'string', 'default': '2', 'description': '分辨率档位：2=720P（默认，质量更高），1=480P。'}, {'name': 'duration', 'type': 'string', 'default': '6', 'description': '时长档位 1-11，分别对应 5 到 15 秒。例如 1=5s、6=10s（默认）、11=15s。'}]}
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
    p = argparse.ArgumentParser(prog='rh-rh.webapp.txt2vid.minimax_h3.v1', description='MiniMax H3 加速版 图文一键生视频（文生视频模式）。纯文本提示词生成视频，不传首尾帧图。支持分辨率、时长、画面比例调节。')
    p.add_argument("--api-key", help="RunningHub API key (default: RUNNINGHUB_API_KEY)")
    p.add_argument("--instance-type", default=DEFAULT_INSTANCE_TYPE, help="RunningHub instance type")
    p.add_argument("--poll-interval", type=float, default=DEFAULT_POLL_INTERVAL, help="Polling interval in seconds")
    p.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT, help="Task timeout in seconds")
    p.add_argument("--output-dir", default=None, help="Base output dir (default: ./outputs)")
    p.add_argument('--prompt_text', required=True, help='文生视频提示词。建议写清镜头运动、主体、动作、光线、色彩风格与质感，中文效果最好。')
    p.add_argument('--aspect_ratio', default='16:9 (Widescreen)', help='画面比例。可选：1:1 (Square)、2:3 (Portrait Photo)、3:2 (Photo)、3:4 (Portrait Standard)、4:3 (Standard)、9:16 (Portrait Widescreen)、16:9 (Widescreen)、21:9 (Ultrawide)。横屏视频推荐 16:9 (Widescreen)。')
    p.add_argument('--resolution', default='2', help='分辨率档位：2=720P（默认，质量更高），1=480P。')
    p.add_argument('--duration', default='6', help='时长档位 1-11，分别对应 5 到 15 秒。例如 1=5s、6=10s（默认）、11=15s。')
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
