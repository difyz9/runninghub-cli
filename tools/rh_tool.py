#!/usr/bin/env python3
"""
Portable RunningHub tool runner.

Goal:
- Single-file helper for reusing verified RunningHub interfaces in any project
- Minimal dependencies: Python stdlib + `runninghub` CLI installed

Usage examples:
  python tools/rh_tool.py list
  python tools/rh_tool.py run --profile krea2_txt2img --set prompt_text='A realistic portrait' --output-dir ./outputs
  python tools/rh_tool.py run --profile minimax_h3_dance --set image_path=003.jpg --set video_path=002.mp4 --output-dir ./outputs
  python tools/rh_tool.py run --profile minimax_music3 --set style_text='Mandopop' --set lyrics_text='[Verse]\nHello' --dry-run
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any


PROFILES: dict[str, dict[str, Any]] = {
    "krea2_txt2img": {
        "id": "2082295063975120897",
        "type": "webapp",
        "description": "Krea2 photorealistic text-to-image",
        "required": ["prompt_text"],
        "optional_defaults": {},
        "mapping": [
            {"param": "prompt_text", "nodeId": "64", "fieldName": "text", "mode": "literal"},
        ],
    },
    "one_image_tryon": {
        "id": "2084829959834660866",
        "type": "webapp",
        "description": "Single-image outfit adjustment",
        "required": ["image_path"],
        "optional_defaults": {},
        "mapping": [
            {"param": "image_path", "nodeId": "207", "fieldName": "image", "mode": "upload"},
        ],
    },
    "minimax_h3_img2vid": {
        "id": "2084535715072929793",
        "type": "webapp",
        "description": "MiniMax H3 image-to-video",
        "required": ["image_path"],
        "optional_defaults": {
            "prompt_text": "Keep subject identity stable, subtle motion, natural lighting, steady camera.",
        },
        "mapping": [
            {"param": "image_path", "nodeId": "4", "fieldName": "image", "mode": "upload"},
            {"param": "prompt_text", "nodeId": "7", "fieldName": "prompt", "mode": "literal"},
        ],
    },
    "minimax_h3_firstlast": {
        "id": "2086547118222827522",
        "type": "webapp",
        "description": "MiniMax H3 first-last frame video",
        "required": ["first_image_path", "last_image_path"],
        "optional_defaults": {
            "aspect_ratio": "16:9",
            "duration_seconds": "6",
            "prompt_text": "Use image 1 as first frame and image 2 as last frame; smooth transition and consistent lighting.",
        },
        "mapping": [
            {"param": "first_image_path", "nodeId": "4", "fieldName": "image", "mode": "upload"},
            {"param": "last_image_path", "nodeId": "6", "fieldName": "image", "mode": "upload"},
            {"param": "aspect_ratio", "nodeId": "7", "fieldName": "aspect_ratio", "mode": "literal"},
            {"param": "duration_seconds", "nodeId": "7", "fieldName": "duration_seconds", "mode": "literal"},
            {"param": "prompt_text", "nodeId": "8", "fieldName": "prompt", "mode": "literal"},
        ],
    },
    "storyboard_auto12": {
        "id": "2084512072087465985",
        "type": "webapp",
        "description": "Auto storyboard (12 images)",
        "required": ["image_path"],
        "optional_defaults": {
            "prompt_text": "Generate 12 coherent storyboard frames from this image with varied camera language.",
        },
        "mapping": [
            {"param": "image_path", "nodeId": "22", "fieldName": "image", "mode": "upload"},
            {"param": "prompt_text", "nodeId": "24", "fieldName": "text", "mode": "literal"},
        ],
    },
    "image_edit_tryon": {
        "id": "2086630550139392001",
        "type": "webapp",
        "description": "Image editing / virtual try-on",
        "required": ["source_image_path", "garment_image_path"],
        "optional_defaults": {
            "prompt_text": "Keep identity and hairstyle stable while replacing clothing naturally.",
            "max_edge": "1280",
        },
        "mapping": [
            {"param": "source_image_path", "nodeId": "570", "fieldName": "image", "mode": "upload"},
            {"param": "garment_image_path", "nodeId": "548", "fieldName": "image", "mode": "upload"},
            {"param": "prompt_text", "nodeId": "558", "fieldName": "text", "mode": "literal"},
            {"param": "max_edge", "nodeId": "539", "fieldName": "value", "mode": "literal"},
        ],
    },
    "minimax_h3_dance": {
        "id": "2085591413194059778",
        "type": "webapp",
        "description": "MiniMax H3 dance motion transfer",
        "required": ["image_path", "video_path"],
        "optional_defaults": {
            "prompt_text": "Use the person in picture 1 and replicate dance motion from video 1, with natural continuity.",
            "resolution_select": "1",
        },
        "mapping": [
            {"param": "image_path", "nodeId": "137", "fieldName": "image", "mode": "upload"},
            {"param": "video_path", "nodeId": "181", "fieldName": "video", "mode": "upload"},
            {"param": "prompt_text", "nodeId": "138", "fieldName": "value", "mode": "literal"},
            {"param": "resolution_select", "nodeId": "165", "fieldName": "select", "mode": "literal"},
        ],
    },
    "anime_motion_transfer_150f": {
        "id": "1937150585009283074",
        "type": "webapp",
        "description": "Anime 150-frame body-shape motion transfer",
        "required": ["image_path", "video_path"],
        "optional_defaults": {
            "ratio_select": "4",
            "duration_seconds": "5",
            "trim_duration": "8",
            "face_enhance_select": "1",
            "glasses_select": "1",
        },
        "mapping": [
            {"param": "video_path", "nodeId": "429", "fieldName": "video", "mode": "upload"},
            {"param": "image_path", "nodeId": "430", "fieldName": "image", "mode": "upload"},
            {"param": "ratio_select", "nodeId": "442", "fieldName": "select", "mode": "literal"},
            {"param": "duration_seconds", "nodeId": "431", "fieldName": "int", "mode": "literal"},
            {"param": "trim_duration", "nodeId": "428", "fieldName": "int", "mode": "literal"},
            {"param": "face_enhance_select", "nodeId": "448", "fieldName": "select", "mode": "literal"},
            {"param": "glasses_select", "nodeId": "449", "fieldName": "select", "mode": "literal"},
        ],
    },
    "minimax_music3": {
        "id": "2088378137674604546",
        "type": "webapp",
        "description": "MiniMax Music3 text-to-song",
        "required": ["style_text", "lyrics_text"],
        "optional_defaults": {
            "reserved_text": "Do not modify this placeholder.",
        },
        "mapping": [
            {"param": "style_text", "nodeId": "52", "fieldName": "text", "mode": "literal"},
            {"param": "lyrics_text", "nodeId": "53", "fieldName": "text", "mode": "literal"},
            {"param": "reserved_text", "nodeId": "888", "fieldName": "text", "mode": "literal"},
        ],
    },
}


def parse_set(items: list[str]) -> dict[str, str]:
    params: dict[str, str] = {}
    for item in items:
        if "=" not in item:
            raise ValueError(f"Invalid --set value: {item}; expected key=value")
        k, v = item.split("=", 1)
        k = k.strip()
        if not k:
            raise ValueError(f"Empty key in --set: {item}")
        params[k] = v
    return params


def build_overrides(profile: dict[str, Any], user_params: dict[str, str]) -> list[dict[str, str]]:
    merged = dict(profile.get("optional_defaults", {}))
    merged.update(user_params)

    missing = [name for name in profile.get("required", []) if name not in merged]
    if missing:
        raise ValueError("Missing required params: " + ", ".join(missing))

    overrides: list[dict[str, str]] = []
    for m in profile.get("mapping", []):
        p = m["param"]
        if p not in merged:
            continue
        raw_value = str(merged[p])
        if m.get("mode") == "upload":
            field_value = "@upload:" + raw_value
        else:
            field_value = raw_value
        overrides.append(
            {
                "nodeId": str(m["nodeId"]),
                "fieldName": str(m["fieldName"]),
                "fieldValue": field_value,
            }
        )
    return overrides


def run_profile(args: argparse.Namespace) -> int:
    if shutil.which("runninghub") is None:
        print(json.dumps({"ok": False, "error": "runninghub command not found in PATH"}, ensure_ascii=False))
        return 2

    if args.profile not in PROFILES:
        print(json.dumps({"ok": False, "error": f"Unknown profile: {args.profile}"}, ensure_ascii=False))
        return 2

    profile = PROFILES[args.profile]
    params = parse_set(args.set)
    overrides = build_overrides(profile, params)

    timeout = args.timeout if args.timeout > 0 else 1800
    poll = args.poll_interval if args.poll_interval > 0 else 15
    instance_type = args.instance_type or "default"

    plan = {
        "profile": args.profile,
        "resource": {"id": profile["id"], "type": profile["type"]},
        "overrides": overrides,
        "runtime": {
            "instance_type": instance_type,
            "timeout": timeout,
            "poll_interval": poll,
        },
        "output_dir": args.output_dir or "",
    }

    if args.dry_run:
        print(json.dumps({"ok": True, "dry_run": True, "plan": plan}, ensure_ascii=False, indent=2))
        return 0

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8") as tmp:
        json.dump(overrides, tmp, ensure_ascii=False, indent=2)
        tmp_path = tmp.name

    cmd = [
        "runninghub",
        "run",
        str(profile["id"]),
        "--type",
        str(profile["type"]),
        "--node-overrides",
        tmp_path,
        "--instance-type",
        instance_type,
        "--timeout",
        str(timeout),
        "--poll-interval",
        str(poll),
    ]

    if args.output_dir:
        cmd.extend(["--output-dir", args.output_dir])
    if args.api_key:
        cmd.extend(["--api-key", args.api_key])
    if args.env_file:
        cmd.extend(["--env-file", args.env_file])

    return subprocess.run(cmd, check=False).returncode


def list_profiles() -> int:
    out = {
        "ok": True,
        "profiles": [
            {
                "name": name,
                "id": cfg["id"],
                "type": cfg["type"],
                "description": cfg["description"],
                "required": cfg.get("required", []),
            }
            for name, cfg in PROFILES.items()
        ],
    }
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Portable RunningHub profile runner (single-file tool)")
    sub = parser.add_subparsers(dest="command", required=True)

    p_list = sub.add_parser("list", help="List built-in profiles")
    p_list.set_defaults(func=lambda _args: list_profiles())

    p_run = sub.add_parser("run", help="Run a built-in profile")
    p_run.add_argument("--profile", required=True, help="Profile name from `list` output")
    p_run.add_argument("--set", action="append", default=[], help="Parameter key=value, can repeat")
    p_run.add_argument("--instance-type", default="", help="RunningHub instance type, e.g. default or plus")
    p_run.add_argument("--timeout", type=float, default=1800, help="Timeout seconds")
    p_run.add_argument("--poll-interval", type=float, default=15, help="Polling interval seconds")
    p_run.add_argument("--output-dir", default="", help="Output directory")
    p_run.add_argument("--api-key", default="", help="Optional explicit API key")
    p_run.add_argument("--env-file", default="", help="Optional .env path")
    p_run.add_argument("--dry-run", action="store_true", help="Print resolved plan without execution")
    p_run.set_defaults(func=run_profile)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        return args.func(args)
    except Exception as exc:
        print(json.dumps({"ok": False, "error_type": type(exc).__name__, "error": str(exc)}, ensure_ascii=False))
        return 1


if __name__ == "__main__":
    sys.exit(main())
