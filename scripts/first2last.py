"""CLI tool: First-to-Last frame video generation via RunningHub.

Generates a transition video from a start frame and an end frame image.

Usage:
    rh-first2last --first-frame start.png --last-frame end.png [--prompt "..."]
    rh-first2last --first-frame a.png --last-frame b.png --workflow-type fusionx

Environment variables:
    RUNNINGHUB_API_KEY                       (required)
    RUNNINGHUB_FIRST2LAST_WORKFLOW_ID        (overrides default workflow)
    RUNNINGHUB_FIRST2LAST_POLL_INTERVAL
    RUNNINGHUB_FIRST2LAST_TIMEOUT

Examples from the runninghub-sdk project:
    examples/first2last/run_workflow_wan22_first2last_video.py
    examples/first02/run_workflow_dasiwa_first2last_video.py
    examples/demo02/run_workflow_fusionx_first2last_video.py
"""

from __future__ import annotations

import argparse
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
    print_request_summary,
    resolve_api_key,
    section,
    submit_and_wait,
)

# Default workflow: Wan 2.2 first-to-last-frame video
DEFAULT_WORKFLOW_ID = "2011275998205054977"

# Node IDs for Wan 2.2 workflow
WAN22_FIRST_FRAME_NODE = "43"
WAN22_LAST_FRAME_NODE = "44"
WAN22_TEXT_NODE = "30"
WAN22_HIGH_NOISE_SAMPLER = "27"
WAN22_LOW_NOISE_SAMPLER = "28"


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="rh-first2last",
        description="Generate a transition video from first and last frame images via RunningHub",
        epilog="Examples:\n"
        "  rh-first2last --first-frame start.png --last-frame end.png\n"
        "  rh-first2last -f scene1.png -l scene2.png --prompt 'smooth camera pan'\n"
        "  rh-first2last -f a.png -l b.png --workflow-type fusionx\n"
        "  rh-first2last -f a.png -l b.png --batch-dir ./frames/",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("--first-frame", "-f", default=get_env("RUNNINGHUB_FIRST2LAST_FIRST_FRAME"),
                   help="Path to the first frame image")
    p.add_argument("--last-frame", "-l", default=get_env("RUNNINGHUB_FIRST2LAST_LAST_FRAME"),
                   help="Path to the last frame image")
    p.add_argument("--prompt", default=get_env("RUNNINGHUB_FIRST2LAST_PROMPT",
                                                ""),
                   help="Positive prompt for the transition")
    p.add_argument("--negative-prompt", default=get_env("RUNNINGHUB_FIRST2LAST_NEGATIVE_PROMPT",
                                                         ""),
                   help="Negative prompt")

    p.add_argument("--api-key", help="RunningHub API key (default: RUNNINGHUB_API_KEY)")
    p.add_argument("--workflow-id",
                   default=get_env("RUNNINGHUB_FIRST2LAST_WORKFLOW_ID", DEFAULT_WORKFLOW_ID),
                   help=f"Workflow ID (default: {DEFAULT_WORKFLOW_ID})")
    p.add_argument("--workflow-type", choices=["wan22", "dasiwa", "fusionx"], default="wan22",
                   help="Workflow type (default: wan22)")

    p.add_argument("--seed", type=int, help="Shared seed for high & low noise samplers")
    p.add_argument("--duration", type=int, default=0,
                   help="Video duration in seconds (workflow-dependent)")

    p.add_argument("--output-dir", default=get_env("RUNNINGHUB_FIRST2LAST_OUTPUT_DIR"),
                   help="Output directory (default: ./outputs/first2last_*)")
    p.add_argument("--poll-interval", type=float,
                   default=get_env_float("RUNNINGHUB_FIRST2LAST_POLL_INTERVAL", 3.0),
                   help="Poll interval in seconds (default: 3)")
    p.add_argument("--timeout", type=float,
                   default=get_env_float("RUNNINGHUB_FIRST2LAST_TIMEOUT", 600),
                   help="Timeout in seconds (default: 600)")
    return p


def build_modifier(client: RunningHubClient, args: argparse.Namespace) -> List[Dict[str, Any]]:
    """Upload both frames and build node overrides."""
    from runninghub_sdk import modify_nodes

    # Validate frame paths
    first_path = Path(args.first_frame).expanduser().resolve()
    last_path = Path(args.last_frame).expanduser().resolve()
    if not first_path.exists():
        print(f"Error: First frame not found: {first_path}", file=sys.stderr)
        sys.exit(1)
    if not last_path.exists():
        print(f"Error: Last frame not found: {last_path}", file=sys.stderr)
        sys.exit(1)

    log(f"Uploading first frame: {first_path}")
    first_uploaded = client.upload_image(str(first_path))
    log(f"  -> {first_uploaded['fileName']}")

    log(f"Uploading last frame: {last_path}")
    last_uploaded = client.upload_image(str(last_path))
    log(f"  -> {last_uploaded['fileName']}")

    modifier = modify_nodes()

    if args.workflow_type == "wan22":
        modifier.image(WAN22_FIRST_FRAME_NODE, first_uploaded["fileName"])
        modifier.image(WAN22_LAST_FRAME_NODE, last_uploaded["fileName"])
        if args.prompt:
            modifier.set(WAN22_TEXT_NODE, "positive_prompt", args.prompt)
        if args.negative_prompt:
            modifier.set(WAN22_TEXT_NODE, "negative_prompt", args.negative_prompt)
        if args.seed is not None:
            modifier.seed(WAN22_HIGH_NOISE_SAMPLER, args.seed)
            modifier.seed(WAN22_LOW_NOISE_SAMPLER, args.seed)
    elif args.workflow_type == "fusionx":
        # Fusion X: first frame = node 1, last frame = node 2
        modifier.image("1", first_uploaded["fileName"])
        modifier.image("2", last_uploaded["fileName"])
        if args.prompt:
            modifier.set("52", "prompt", args.prompt)
        if args.negative_prompt:
            modifier.set("53", "prompt", args.negative_prompt)
        if args.duration > 0:
            modifier.set("58", "value", args.duration)
        if args.seed is not None:
            modifier.seed("8", args.seed)
    else:
        # DaSiWa / generic: first frame = node 110, last = 111
        modifier.image("110", first_uploaded["fileName"])
        modifier.image("111", last_uploaded["fileName"])
        if args.prompt:
            modifier.set("66", "text", args.prompt)
        if args.negative_prompt:
            modifier.set("67", "text", args.negative_prompt)
        if args.duration > 0:
            modifier.set("41", "frame_count", args.duration * 16)  # 16fps
        if args.seed is not None:
            modifier.seed("79", args.seed)

    return modifier.to_dict_list()


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    if not args.first_frame or not args.last_frame:
        parser.print_help()
        print("\nError: --first-frame and --last-frame are required.", file=sys.stderr)
        return 1

    bootstrap_env()
    api_key = resolve_api_key(args.api_key)

    try:
        with RunningHubClient(api_key=api_key) as client:
            nodes = build_modifier(client, args)
            print_request_summary("RunningHubClient.run", args.workflow_id, nodes)

            outputs = submit_and_wait(
                client, "workflow", args.workflow_id, nodes,
                args.poll_interval, args.timeout,
            )
            output_dir = make_output_dir(args.output_dir, "first2last")
            download_results(client, outputs, output_dir)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    section("Done")
    log(f"Video saved to: {output_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
