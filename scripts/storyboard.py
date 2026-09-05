"""CLI tool: Storyboard generation via DeepSeek + RunningHub.

Two-phase pipeline:
  Phase 1 — Generate a storyboard prompt using DeepSeek (or provide your own)
  Phase 2 — Submit the prompt to the RunningHub fenjing workflow and download images

Usage:
    rh-storyboard --idea "探险故事" --style "国漫悬疑"
    rh-storyboard --prompt-file my_storyboard.txt
    rh-storyboard --idea "太空冒险" --dry-run         # generate prompt only

Environment variables:
    RUNNINGHUB_API_KEY          (required for phase 2)
    DEEPSEEK_API_KEY            (required for phase 1 via DeepSeek)
    RUNNINGHUB_FENJING_WORKFLOW_ID

Examples from the runninghub-sdk project:
    examples/fenjing/run_fenjing_from_deepseek_prompt.py
    examples/fenjing/deepseek_storyboard_prompt.py
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List

from runninghub_sdk import RunningHubClient

from .base import (
    bootstrap_env,
    download_results,
    get_env,
    get_env_float,
    log,
    make_output_dir,
    resolve_api_key,
    section,
    submit_and_wait,
)

# Default workflow ID from the fenjing workflow
DEFAULT_WORKFLOW_ID = "2013908081847046145"

# Storyboard slot prompt template for manual input
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

DEFAULT_NEGATIVE_PROMPT = "低质量，模糊，错误透视，人物崩坏，手部异常，额外肢体，画面拥挤，构图混乱，风格漂移"


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="rh-storyboard",
        description="Generate storyboard prompts and images via DeepSeek + RunningHub",
        epilog="Examples:\n"
        "  rh-storyboard --idea '主角深夜误入荒废寺庙'\n"
        "  rh-storyboard --idea '太空探险' --style '赛博朋克, 霓虹色调'\n"
        "  rh-storyboard --idea '校园故事' --dry-run           # only generate prompt\n"
        "  rh-storyboard --prompt-file my_prompt.txt            # use existing prompt\n"
        "  rh-storyboard --prompt 'Slot 1...\\nSlot 2...'       # inline prompt",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    # Phase 1: Storyboard generation
    gen = p.add_argument_group("Storyboard Generation (Phase 1)")
    gen.add_argument("--idea", default=get_env("RUNNINGHUB_STORYBOARD_IDEA",
                                                "主角深夜误入荒废寺庙，在恐惧中逐步发现庙内异样，气氛持续升级。"),
                      help="High-level story idea (Chinese)")
    gen.add_argument("--style", default=get_env("RUNNINGHUB_STORYBOARD_STYLE",
                                                 "国漫分镜，电影感构图，悬疑惊悚，强氛围光影"),
                      help="Visual style guidance")
    gen.add_argument("--characters", default=get_env("RUNNINGHUB_STORYBOARD_CHARACTERS",
                                                      "主角：年轻男性，谨慎、紧张、易受惊。"),
                      help="Character and cast description")
    gen.add_argument("--model", default=get_env("RUNNINGHUB_STORYBOARD_MODEL", "deepseek-chat"),
                      help="DeepSeek model name (default: deepseek-chat)")
    gen.add_argument("--api-key-deepseek",
                      help="DeepSeek API key (default: DEEPSEEK_API_KEY)")

    # Phase 2: RunningHub workflow
    rh = p.add_argument_group("RunningHub Workflow (Phase 2)")
    rh.add_argument("--api-key", help="RunningHub API key (default: RUNNINGHUB_API_KEY)")
    rh.add_argument("--workflow-id",
                     default=get_env("RUNNINGHUB_FENJING_WORKFLOW_ID", DEFAULT_WORKFLOW_ID),
                     help=f"Fenjing workflow ID (default: {DEFAULT_WORKFLOW_ID})")

    # Manual prompt overrides
    manual = p.add_argument_group("Manual Prompt (skip DeepSeek)")
    manual.add_argument("--prompt", help="Direct storyboard prompt string (skips DeepSeek)")
    manual.add_argument("--prompt-file", help="Read storyboard prompt from file (skips DeepSeek)")
    manual.add_argument("--skip-llm", action="store_true",
                         help="Skip DeepSeek prompt generation (alias for using --prompt-file)")

    # Output control
    p.add_argument("--dry-run", action="store_true",
                    help="Only generate the prompt JSON, skip workflow submission")
    p.add_argument("--output-dir", default=get_env("RUNNINGHUB_STORYBOARD_OUTPUT_DIR"),
                    help="Output directory (default: ./outputs/storyboard_*)")
    p.add_argument("--prompt-output",
                    default=get_env("RUNNINGHUB_STORYBOARD_PROMPT_OUTPUT",
                                     "storyboard_prompt.json"),
                    help="Save generated prompt JSON to this file")
    p.add_argument("--poll-interval", type=float,
                    default=get_env_float("RUNNINGHUB_STORYBOARD_POLL_INTERVAL", 3.0),
                    help="Poll interval in seconds (default: 3)")
    p.add_argument("--timeout", type=float,
                    default=get_env_float("RUNNINGHUB_STORYBOARD_TIMEOUT", 600),
                    help="Timeout per task in seconds (default: 600)")
    return p


# ==================== Phase 1: Storyboard Prompt Generation ====================


def load_deepseek_client(api_key_override: str | None = None):
    """Create an OpenAI-compatible client pointed at DeepSeek."""
    try:
        from openai import OpenAI
    except ImportError:
        print("Error: The 'openai' package is required for DeepSeek integration.", file=sys.stderr)
        print("Install it: pip install openai", file=sys.stderr)
        sys.exit(1)

    api_key = api_key_override or get_env("DEEPSEEK_API_KEY") or get_env("OPENAI_API_KEY")
    if not api_key:
        print("Error: DEEPSEEK_API_KEY or OPENAI_API_KEY must be set.", file=sys.stderr)
        sys.exit(1)

    return OpenAI(api_key=api_key, base_url="https://api.deepseek.com")


def generate_storyboard_prompt(args: argparse.Namespace) -> Dict[str, Any]:
    """Call DeepSeek to generate a storyboard prompt JSON."""
    section("Phase 1: Generating Storyboard Prompt via DeepSeek")
    log(f"Idea:  {args.idea}")
    log(f"Style: {args.style}")
    log(f"Model: {args.model}")

    client = load_deepseek_client(args.api_key_deepseek)

    user_prompt = (
        f"Generate a storyboard payload with these constraints:\n"
        f"- Core story idea: {args.idea}\n"
        f"- Visual style: {args.style}\n"
        f"- Characters: {args.characters}\n"
        f"- Output language: Chinese\n"
        f"- The storyboard_prompt must be directly usable for a RunningHub storyboard workflow\n"
        f"- Keep the scene progression coherent and cinematic\n"
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
    except Exception as e:
        error_name = e.__class__.__name__
        error_text = str(e)
        if error_name == "AuthenticationError":
            print("Error: DeepSeek authentication failed. Check DEEPSEEK_API_KEY.", file=sys.stderr)
        else:
            print(f"Error: DeepSeek request failed: {error_text}", file=sys.stderr)
        sys.exit(1)

    content = response.choices[0].message.content
    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        print(f"Error: DeepSeek returned invalid JSON:\n{content}", file=sys.stderr)
        sys.exit(1)

    # Validate required keys
    required_keys = {"title", "global_style", "story_summary", "storyboard_prompt"}
    missing_keys = required_keys.difference(data)
    if missing_keys:
        print(f"Error: DeepSeek response missing keys: {sorted(missing_keys)}", file=sys.stderr)
        sys.exit(1)

    if not data.get("negative_prompt"):
        data["negative_prompt"] = DEFAULT_NEGATIVE_PROMPT

    # Save prompt JSON
    prompt_path = Path(args.prompt_output)
    prompt_path.parent.mkdir(parents=True, exist_ok=True)
    prompt_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    log(f"Prompt JSON saved to: {prompt_path.resolve()}")

    log(f"Title: {data['title']}")
    log(f"Global Style: {data['global_style']}")
    log(f"Story Summary: {data['story_summary']}")
    log(f"Prompt length: {len(data['storyboard_prompt'])} chars")

    return data


def load_manual_prompt(args: argparse.Namespace) -> Dict[str, Any]:
    """Load or create storyboard data from manual input."""
    if args.prompt_file:
        pf = Path(args.prompt_file).expanduser().resolve()
        if not pf.exists():
            print(f"Error: Prompt file not found: {pf}", file=sys.stderr)
            sys.exit(1)
        content = pf.read_text(encoding="utf-8")
        section("Phase 1: Using Manual Storyboard Prompt")
        log(f"Loaded from: {pf}")
        return {
            "title": pf.stem.replace("_", " ").title(),
            "global_style": "custom",
            "story_summary": "Manual storyboard prompt",
            "storyboard_prompt": content,
            "negative_prompt": DEFAULT_NEGATIVE_PROMPT,
        }
    elif args.prompt:
        section("Phase 1: Using Inline Storyboard Prompt")
        return {
            "title": "Custom Storyboard",
            "global_style": "custom",
            "story_summary": "Inline storyboard prompt",
            "storyboard_prompt": args.prompt,
            "negative_prompt": DEFAULT_NEGATIVE_PROMPT,
        }
    return {}


# ==================== Phase 2: RunningHub Workflow ====================


def resolve_prompt_node_ids(client: RunningHubClient, workflow_id: str) -> List[str]:
    """Find CR Prompt Text nodes that contain 'Slot' in their prompt value."""
    configured = get_env("RUNNINGHUB_STORYBOARD_PROMPT_NODE_IDS")
    if configured:
        return [n.strip() for n in configured.split(",") if n.strip()]

    log("Scanning workflow for storyboard prompt nodes...")
    try:
        workflow_json = client.get_workflow_json_parsed(workflow_id)
    except Exception as e:
        log(f"Could not parse workflow JSON (will use default node): {e}")
        return ["1"]

    resolved: List[str] = []
    if isinstance(workflow_json, dict):
        for node_id, node_data in workflow_json.items():
            if not isinstance(node_data, dict):
                continue
            if node_data.get("class_type") == "CR Prompt Text":
                prompt_value = str(node_data.get("inputs", {}).get("prompt", "")).strip()
                if "Slot" in prompt_value:
                    resolved.append(str(node_id))
                    log(f"  Found CR Prompt Text node: {node_id}")

    if not resolved:
        log("No CR Prompt Text nodes with 'Slot' found, using default node 1")
        resolved = ["1"]

    return resolved


def submit_storyboard(client: RunningHubClient, workflow_id: str,
                      prompt_json: Dict[str, Any],
                      output_dir: Path, poll_interval: float, timeout: float) -> List[Path]:
    """Submit storyboard prompt to RunningHub and download results."""
    from runninghub_sdk import modify_nodes

    section("Phase 2: Submitting to RunningHub Workflow")
    storyboard_prompt = prompt_json.get("storyboard_prompt", "")
    if not storyboard_prompt:
        print("Error: storyboard_prompt is empty.", file=sys.stderr)
        sys.exit(1)

    # Resolve prompt nodes
    prompt_node_ids = resolve_prompt_node_ids(client, workflow_id)
    modifier = modify_nodes()
    for node_id in prompt_node_ids:
        if node_id:
            modifier.set(node_id, "prompt", storyboard_prompt)

    nodes = modifier.to_dict_list()
    log(f"Workflow ID: {workflow_id}")
    log(f"Prompt nodes: {prompt_node_ids}")
    log(f"Storyboard prompt:\n{storyboard_prompt[:200]}...")

    outputs = submit_and_wait(client, "workflow", workflow_id, nodes,
                              poll_interval, timeout)
    return download_results(client, outputs, output_dir)


# ==================== Main ====================


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    bootstrap_env()

    # Check if user wants to skip DeepSeek and use a manual prompt
    has_manual = bool(args.prompt or args.prompt_file)

    if not has_manual and args.skip_llm:
        print("Error: --skip-llm requires --prompt or --prompt-file.", file=sys.stderr)
        return 1

    # Phase 1: Get storyboard prompt
    prompt_json = load_manual_prompt(args) if has_manual else generate_storyboard_prompt(args)

    # If applicable, save prompt JSON
    if not has_manual and args.prompt_output:
        prompt_path = Path(args.prompt_output)
        if not args.dry_run:
            # Already saved in generate_storyboard_prompt, but double-check
            if not prompt_path.exists():
                prompt_path.parent.mkdir(parents=True, exist_ok=True)
                prompt_path.write_text(
                    json.dumps(prompt_json, ensure_ascii=False, indent=2),
                    encoding="utf-8",
                )

    # Show the prompt summary
    section("Storyboard Summary")
    log(f"Title: {prompt_json.get('title', 'N/A')}")
    log(f"Prompt length: {len(prompt_json.get('storyboard_prompt', ''))} chars")
    print()
    print(prompt_json.get("storyboard_prompt", "")[:500])
    print()

    if args.dry_run:
        log("Dry run — skipping workflow submission.")
        log("Remove --dry-run and set RUNNINGHUB_API_KEY to execute.")
        return 0

    # Phase 2: Submit to RunningHub
    api_key = resolve_api_key(args.api_key)
    output_dir = make_output_dir(args.output_dir, "storyboard")

    try:
        with RunningHubClient(api_key=api_key) as client:
            submit_storyboard(client, args.workflow_id, prompt_json,
                              output_dir, args.poll_interval, args.timeout)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    section("Done")
    log(f"Storyboard images saved to: {output_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
