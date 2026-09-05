#!/usr/bin/env python3
"""Standalone storyboard CLI using DeepSeek + RunningHub.

Single-file script with no project-internal imports.

Dependencies:
    pip install runninghub-sdk
    pip install openai  # optional, only needed when generating prompt via DeepSeek

Usage:
    python storyboard_standalone.py --idea "探险故事"
    python storyboard_standalone.py --prompt-file my_storyboard.txt
    python storyboard_standalone.py --idea "太空冒险" --dry-run

Environment variables:
    RUNNINGHUB_API_KEY                required for RunningHub submission
    DEEPSEEK_API_KEY                  required for DeepSeek generation
    OPENAI_API_KEY                    fallback for DeepSeek generation
    RUNNINGHUB_FENJING_WORKFLOW_ID    optional workflow id override
    RUNNINGHUB_STORYBOARD_PROMPT_NODE_IDS  optional comma-separated prompt node ids
"""

from __future__ import annotations

import argparse
import datetime
import json
import os
import sys
from pathlib import Path
from typing import Any

from runninghub_sdk import RunningHubClient

DEFAULT_WORKFLOW_ID = "2013908081847046145"
DEFAULT_NEGATIVE_PROMPT = "低质量，模糊，错误透视，人物崩坏，手部异常，额外肢体，画面拥挤，构图混乱，风格漂移"
DEFAULT_SYSTEM_PROMPT = """You are a senior storyboard designer for comic and anime previsualization.
Return valid JSON only.

Create a production-ready storyboard prompt payload. The JSON schema must be:
{
  "title": "short title",
  "global_style": "one concise global style line in Chinese",
  "story_summary": "2-4 sentences summarizing the scene progression in Chinese",
  "storyboard_prompt": "multi-line Chinese storyboard prompt using Slot format",
  "negative_prompt": "one concise negative prompt in Chinese"
}

Rules:
- Return JSON only, no markdown fences.
- storyboard_prompt must use this exact structure:
  Slot 1 (缓冲帧):
  ...

  Slot 2 (剧情帧):
  ...

  Slot 3 (剧情帧):
  ...
- There must be a blank line between every Slot block.
- Include exactly 6 slots total: Slot 1 is a pure black buffer frame, Slots 2-6 are story frames.
- The storyboard_prompt must be directly usable as input for a storyboard image workflow.
- Each story frame should mention environment, subject, action, mood, and camera shot.
"""


def log(msg: str) -> None:
    print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] {msg}")


def section(title: str) -> None:
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print(f"{'=' * 60}")


def load_env_file(path: Path) -> None:
    if not path.exists():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip("\"'"))


def bootstrap_env() -> None:
    load_env_file(Path.cwd() / ".env")
    for parent in Path.cwd().parents:
        if (parent / "pyproject.toml").exists() or (parent / "scripts").exists():
            load_env_file(parent / ".env")
            break


def get_env(name: str, default: str = "") -> str:
    return os.getenv(name, "").strip() or default


def get_env_float(name: str, default: float = 0.0) -> float:
    raw = os.getenv(name, "").strip()
    return float(raw) if raw else default


def resolve_api_key(api_key: str | None = None) -> str:
    if api_key:
        return api_key
    value = os.getenv("RUNNINGHUB_API_KEY", "").strip()
    if value:
        return value
    print("Error: RUNNINGHUB_API_KEY not set. Provide --api-key or set environment variable.", file=sys.stderr)
    sys.exit(1)


def make_output_dir(base: str | None, subdir: str) -> Path:
    root = Path(base).expanduser().resolve() if base else Path.cwd() / "outputs"
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    out = root / f"{subdir}_{ts}"
    out.mkdir(parents=True, exist_ok=True)
    return out


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="rh-storyboard-standalone",
        description="Generate storyboard prompts and images via DeepSeek + RunningHub",
        epilog="Examples:\n"
        "  python storyboard_standalone.py --idea '主角深夜误入荒废寺庙'\n"
        "  python storyboard_standalone.py --idea '太空探险' --style '赛博朋克, 霓虹色调'\n"
        "  python storyboard_standalone.py --idea '校园故事' --dry-run\n"
        "  python storyboard_standalone.py --prompt-file my_prompt.txt\n"
        "  python storyboard_standalone.py --prompt 'Slot 1...\\nSlot 2...'",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    gen = p.add_argument_group("Storyboard Generation (Phase 1)")
    gen.add_argument(
        "--idea",
        default=get_env(
            "RUNNINGHUB_STORYBOARD_IDEA",
            "主角深夜误入荒废寺庙，在恐惧中逐步发现庙内异样，气氛持续升级。",
        ),
        help="High-level story idea (Chinese)",
    )
    gen.add_argument(
        "--style",
        default=get_env("RUNNINGHUB_STORYBOARD_STYLE", "国漫分镜，电影感构图，悬疑惊悚，强氛围光影"),
        help="Visual style guidance",
    )
    gen.add_argument(
        "--characters",
        default=get_env("RUNNINGHUB_STORYBOARD_CHARACTERS", "主角：年轻男性，谨慎、紧张、易受惊。"),
        help="Character and cast description",
    )
    gen.add_argument("--model", default=get_env("RUNNINGHUB_STORYBOARD_MODEL", "deepseek-chat"), help="DeepSeek model")
    gen.add_argument("--api-key-deepseek", help="DeepSeek API key (default: DEEPSEEK_API_KEY)")

    rh = p.add_argument_group("RunningHub Workflow (Phase 2)")
    rh.add_argument("--api-key", help="RunningHub API key (default: RUNNINGHUB_API_KEY)")
    rh.add_argument(
        "--workflow-id",
        default=get_env("RUNNINGHUB_FENJING_WORKFLOW_ID", DEFAULT_WORKFLOW_ID),
        help=f"Fenjing workflow ID (default: {DEFAULT_WORKFLOW_ID})",
    )

    manual = p.add_argument_group("Manual Prompt (skip DeepSeek)")
    manual.add_argument("--prompt", help="Direct storyboard prompt string")
    manual.add_argument("--prompt-file", help="Read storyboard prompt from file")
    manual.add_argument("--skip-llm", action="store_true", help="Skip DeepSeek prompt generation")

    p.add_argument("--dry-run", action="store_true", help="Only generate prompt JSON")
    p.add_argument("--output-dir", default=get_env("RUNNINGHUB_STORYBOARD_OUTPUT_DIR"), help="Output directory")
    p.add_argument(
        "--prompt-output",
        default=get_env("RUNNINGHUB_STORYBOARD_PROMPT_OUTPUT", "storyboard_prompt.json"),
        help="Save generated prompt JSON",
    )
    p.add_argument(
        "--poll-interval",
        type=float,
        default=get_env_float("RUNNINGHUB_STORYBOARD_POLL_INTERVAL", 3.0),
        help="Poll interval in seconds (default: 3)",
    )
    p.add_argument(
        "--timeout",
        type=float,
        default=get_env_float("RUNNINGHUB_STORYBOARD_TIMEOUT", 600),
        help="Timeout in seconds (default: 600)",
    )
    return p


def load_deepseek_client(api_key_override: str | None = None):
    try:
        from openai import OpenAI
    except ImportError:
        print("Error: openai package is required for DeepSeek mode. Install with: pip install openai", file=sys.stderr)
        sys.exit(1)

    api_key = api_key_override or get_env("DEEPSEEK_API_KEY") or get_env("OPENAI_API_KEY")
    if not api_key:
        print("Error: DEEPSEEK_API_KEY or OPENAI_API_KEY must be set.", file=sys.stderr)
        sys.exit(1)

    return OpenAI(api_key=api_key, base_url="https://api.deepseek.com")


def generate_storyboard_prompt(args: argparse.Namespace) -> dict[str, Any]:
    section("Phase 1: Generate Storyboard Prompt")
    log(f"Idea:  {args.idea}")
    log(f"Style: {args.style}")
    log(f"Model: {args.model}")

    client = load_deepseek_client(args.api_key_deepseek)
    user_prompt = (
        "Generate a storyboard payload with these constraints:\n"
        f"- Core story idea: {args.idea}\n"
        f"- Visual style: {args.style}\n"
        f"- Characters: {args.characters}\n"
        "- Output language: Chinese\n"
        "- The storyboard_prompt must be directly usable for a RunningHub storyboard workflow\n"
        "- Keep the scene progression coherent and cinematic\n"
    )

    try:
        response = client.chat.completions.create(
            model=args.model,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": DEFAULT_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.9,
        )
    except Exception as exc:
        name = exc.__class__.__name__
        if name == "AuthenticationError":
            print("Error: DeepSeek authentication failed. Check DEEPSEEK_API_KEY.", file=sys.stderr)
        else:
            print(f"Error: DeepSeek request failed: {exc}", file=sys.stderr)
        sys.exit(1)

    content = response.choices[0].message.content
    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        print(f"Error: DeepSeek returned invalid JSON:\n{content}", file=sys.stderr)
        sys.exit(1)

    required = {"title", "global_style", "story_summary", "storyboard_prompt"}
    missing = sorted(required.difference(data))
    if missing:
        print(f"Error: DeepSeek response missing keys: {missing}", file=sys.stderr)
        sys.exit(1)

    if not data.get("negative_prompt"):
        data["negative_prompt"] = DEFAULT_NEGATIVE_PROMPT

    prompt_path = Path(args.prompt_output)
    prompt_path.parent.mkdir(parents=True, exist_ok=True)
    prompt_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    log(f"Prompt JSON saved to: {prompt_path.resolve()}")
    return data


def load_manual_prompt(args: argparse.Namespace) -> dict[str, Any]:
    if args.prompt_file:
        prompt_file = Path(args.prompt_file).expanduser().resolve()
        if not prompt_file.exists():
            print(f"Error: Prompt file not found: {prompt_file}", file=sys.stderr)
            sys.exit(1)
        content = prompt_file.read_text(encoding="utf-8")
        section("Phase 1: Manual Prompt")
        log(f"Loaded from: {prompt_file}")
        return {
            "title": prompt_file.stem.replace("_", " ").title(),
            "global_style": "custom",
            "story_summary": "Manual storyboard prompt",
            "storyboard_prompt": content,
            "negative_prompt": DEFAULT_NEGATIVE_PROMPT,
        }

    if args.prompt:
        section("Phase 1: Manual Prompt")
        return {
            "title": "Custom Storyboard",
            "global_style": "custom",
            "story_summary": "Inline storyboard prompt",
            "storyboard_prompt": args.prompt,
            "negative_prompt": DEFAULT_NEGATIVE_PROMPT,
        }

    return {}


def resolve_prompt_node_ids(client: RunningHubClient, workflow_id: str) -> list[str]:
    configured = get_env("RUNNINGHUB_STORYBOARD_PROMPT_NODE_IDS")
    if configured:
        return [s.strip() for s in configured.split(",") if s.strip()]

    log("Scanning workflow for storyboard prompt nodes...")
    try:
        workflow_json = client.get_workflow_json_parsed(workflow_id)
    except Exception as exc:
        log(f"Could not parse workflow JSON, fallback to node 1: {exc}")
        return ["1"]

    resolved: list[str] = []
    if isinstance(workflow_json, dict):
        for node_id, node_data in workflow_json.items():
            if not isinstance(node_data, dict):
                continue
            if node_data.get("class_type") == "CR Prompt Text":
                prompt_value = str(node_data.get("inputs", {}).get("prompt", "")).strip()
                if "Slot" in prompt_value:
                    resolved.append(str(node_id))
                    log(f"  Found prompt node: {node_id}")

    return resolved or ["1"]


def submit_and_wait(
    client: RunningHubClient,
    workflow_id: str,
    node_info_list: list[dict[str, Any]],
    poll_interval: float,
    timeout: float,
) -> Any:
    section("Phase 2: Submit to RunningHub")
    task = client.run(
        workflow_id=workflow_id,
        node_info_list=node_info_list,
        add_metadata=True,
        instance_type="default",
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


def download_results(client: RunningHubClient, outputs: Any, output_dir: Path) -> list[Path]:
    section("Downloading Results")
    paths = client.download_outputs(outputs, output_dir)
    for path in paths:
        size = path.stat().st_size
        size_str = f"{size / 1024 / 1024:.1f} MB" if size > 1024 * 1024 else f"{size / 1024:.0f} KB"
        log(f"saved: {path} ({size_str})")
    return paths


def submit_storyboard(
    client: RunningHubClient,
    workflow_id: str,
    prompt_json: dict[str, Any],
    output_dir: Path,
    poll_interval: float,
    timeout: float,
) -> list[Path]:
    from runninghub_sdk import modify_nodes

    storyboard_prompt = prompt_json.get("storyboard_prompt", "")
    if not storyboard_prompt:
        print("Error: storyboard_prompt is empty.", file=sys.stderr)
        sys.exit(1)

    prompt_node_ids = resolve_prompt_node_ids(client, workflow_id)
    modifier = modify_nodes()
    for node_id in prompt_node_ids:
        modifier.set(node_id, "prompt", storyboard_prompt)

    node_info_list = modifier.to_dict_list()
    log(f"Workflow ID: {workflow_id}")
    log(f"Prompt nodes: {prompt_node_ids}")

    outputs = submit_and_wait(client, workflow_id, node_info_list, poll_interval, timeout)
    return download_results(client, outputs, output_dir)


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    bootstrap_env()

    has_manual = bool(args.prompt or args.prompt_file)
    if not has_manual and args.skip_llm:
        print("Error: --skip-llm requires --prompt or --prompt-file.", file=sys.stderr)
        return 1

    prompt_json = load_manual_prompt(args) if has_manual else generate_storyboard_prompt(args)

    section("Storyboard Summary")
    log(f"Title: {prompt_json.get('title', 'N/A')}")
    log(f"Prompt length: {len(prompt_json.get('storyboard_prompt', ''))} chars")
    print()
    print(prompt_json.get("storyboard_prompt", "")[:500])
    print()

    if args.dry_run:
        log("Dry run enabled: skip RunningHub submission.")
        return 0

    api_key = resolve_api_key(args.api_key)
    output_dir = make_output_dir(args.output_dir, "storyboard")

    try:
        with RunningHubClient(api_key=api_key) as client:
            submit_storyboard(
                client=client,
                workflow_id=args.workflow_id,
                prompt_json=prompt_json,
                output_dir=output_dir,
                poll_interval=args.poll_interval,
                timeout=args.timeout,
            )
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    section("Done")
    log(f"Storyboard images saved to: {output_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
