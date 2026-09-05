"""CLI tool: Complete video pipeline orchestrator.

Combines text-to-image, image-to-video, first-to-last transitions,
and video merging into one end-to-end pipeline.

Usage:
    rh-pipeline --config scenes.json [--output-dir ./outputs]
    rh-pipeline --config scenes.json --skip-transitions

Config JSON format:
    {
      "title": "My Video Project",
      "scenes": [
        {
          "prompt": "A cinematic sunset over the ocean",
          "duration": 5,
          "image": "optional/existing/image.png"
        },
        {
          "prompt": "A mountain landscape at dawn",
          "duration": 8
        }
      ]
    }

Environment variables:
    RUNNINGHUB_API_KEY  (required)

Examples from the runninghub-sdk project:
    examples/first2last/run_batch_first2last_from_downloads.py
    examples/run_doubao_video_from_deepseek_prompt.py
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
    log,
    make_output_dir,
    resolve_api_key,
    section,
    submit_and_wait,
)

# Default workflow IDs
DEFAULT_TXT2IMG_WORKFLOW = "2037071836214730753"   # Popular Aesthetics
DEFAULT_IMG2VID_WORKFLOW = "2037036284312559617"    # Seedance 2.0
DEFAULT_FIRST2LAST_WORKFLOW = "2011275998205054977"  # Wan 2.2

# Node IDs for default workflows
TXT2IMG_PROMPT_NODE = "57"
TXT2IMG_SAMPLER_NODE = "51"
TXT2IMG_LATENT_NODE = "39"
IMG2VID_IMAGE_NODE = "2"
IMG2VID_VIDEO_NODE = "1"
F2L_FIRST_FRAME_NODE = "43"
F2L_LAST_FRAME_NODE = "44"


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="rh-pipeline",
        description="End-to-end video generation pipeline: txt2img → img2vid → transitions → merge",
        epilog="Examples:\n"
        "  rh-pipeline --config scenes.json\n"
        "  rh-pipeline --config scenes.json --output-dir ./my_video\n"
        "  rh-pipeline --config scenes.json --skip-txt2img --skip-transitions\n"
        "  rh-pipeline --config scenes.json --skip-img2vid --skip-merge",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("--config", required=True,
                   help="Path to pipeline config JSON file")
    p.add_argument("--api-key", help="RunningHub API key (default: RUNNINGHUB_API_KEY)")

    # Workflow overrides
    p.add_argument("--txt2img-workflow",
                   default="RUNNINGHUB_TXT2IMG_WORKFLOW",
                   help="Text-to-image workflow ID")
    p.add_argument("--img2vid-workflow",
                   default="RUNNINGHUB_IMG2VID_WORKFLOW",
                   help="Image-to-video workflow ID")
    p.add_argument("--first2last-workflow",
                   default="RUNNINGHUB_FIRST2LAST_WORKFLOW",
                   help="First-to-last transition workflow ID")

    # Step toggles
    p.add_argument("--skip-txt2img", action="store_true",
                   help="Skip text-to-image (use existing images)")
    p.add_argument("--skip-img2vid", action="store_true",
                   help="Skip image-to-video (only generate images)")
    p.add_argument("--skip-transitions", action="store_true",
                   help="Skip transition videos between scenes")
    p.add_argument("--skip-merge", action="store_true",
                   help="Skip final merge (keep individual clips)")

    # Options
    p.add_argument("--output-dir", default="",
                   help="Output directory (default: ./outputs/pipeline_*)")
    p.add_argument("--poll-interval", type=float, default=3.0,
                   help="Poll interval in seconds (default: 3)")
    p.add_argument("--timeout", type=float, default=600,
                   help="Timeout per task in seconds (default: 600)")
    p.add_argument("--dry-run", action="store_true",
                   help="Validate config and print plan without executing")
    return p


def load_config(path: str) -> Dict[str, Any]:
    p = Path(path).expanduser().resolve()
    if not p.exists():
        print(f"Error: Config file not found: {p}", file=sys.stderr)
        sys.exit(1)
    with open(p, encoding="utf-8") as f:
        config = json.load(f)

    scenes = config.get("scenes", [])
    if not scenes:
        print(f"Error: No scenes found in config file: {p}", file=sys.stderr)
        sys.exit(1)

    for i, scene in enumerate(scenes):
        if "prompt" not in scene and "image" not in scene:
            print(f"Error: Scene {i + 1} must have 'prompt' or 'image' field", file=sys.stderr)
            sys.exit(1)

    return config


def resolve_workflow_id(key: str, default: str) -> str:
    """Resolve a workflow ID from env var, or use the default."""
    import os
    env_key = key.upper().replace("-", "_")
    return os.getenv(env_key, default)


# ==================== Step 1: Text-to-Image ====================


def step_txt2img(client: RunningHubClient, scenes: List[Dict[str, Any]],
                 output_dir: Path, poll_interval: float, timeout: float,
                 workflow_id: str) -> List[Path]:
    """Generate images for each scene prompt."""
    from runninghub_sdk import modify_nodes

    section("Step 1/4: Text-to-Image")
    image_dir = output_dir / "01_images"
    image_dir.mkdir(parents=True, exist_ok=True)
    image_paths: List[Path] = []

    for i, scene in enumerate(scenes, 1):
        # Skip if image is already provided
        if scene.get("image"):
            img_path = Path(scene["image"]).expanduser().resolve()
            if img_path.exists():
                log(f"[{i}/{len(scenes)}] Using existing image: {img_path}")
                image_paths.append(img_path)
                continue
            else:
                log(f"[{i}/{len(scenes)}] Warning: image '{img_path}' not found, generating...")

        prompt = scene.get("prompt", "")
        if not prompt:
            log(f"[{i}/{len(scenes)}] Skipping: no prompt available")
            image_paths.append(None)  # type: ignore
            continue

        log(f"[{i}/{len(scenes)}] Generating image for: {prompt[:50]}...")

        modifier = modify_nodes()
        modifier.set(TXT2IMG_PROMPT_NODE, "text", prompt)
        modifier.set(TXT2IMG_SAMPLER_NODE, "steps", 25)
        modifier.size(TXT2IMG_LATENT_NODE, 1024, 1024, 1)

        outputs = submit_and_wait(
            client, "workflow", workflow_id,
            modifier.to_dict_list(),
            poll_interval, timeout,
        )
        paths = client.download_outputs(outputs, image_dir)
        if paths:
            image_paths.append(paths[0])
            log(f"  -> {paths[0].name}")
        else:
            log("  -> No output downloaded")
            image_paths.append(None)  # type: ignore

    return [p for p in image_paths if p is not None]


# ==================== Step 2: Image-to-Video ====================


def step_img2vid(client: RunningHubClient, images: List[Path], scenes: List[Dict[str, Any]],
                 output_dir: Path, poll_interval: float, timeout: float,
                 workflow_id: str) -> List[Path]:
    """Convert each image to a video clip."""
    from runninghub_sdk import modify_nodes

    section("Step 2/4: Image-to-Video")
    video_dir = output_dir / "02_videos"
    video_dir.mkdir(parents=True, exist_ok=True)
    video_paths: List[Path] = []

    for i, (img_path, scene) in enumerate(zip(images, scenes, strict=False), 1):
        if not img_path:
            log(f"[{i}/{len(images)}] Skipping: no image available")
            video_paths.append(None)  # type: ignore
            continue

        log(f"[{i}/{len(images)}] Generating video from: {img_path.name}")

        uploaded = client.upload_image(str(img_path))

        modifier = modify_nodes()
        modifier.image(IMG2VID_IMAGE_NODE, uploaded["fileName"])

        prompt = scene.get("video_prompt") or scene.get("prompt", "")
        if prompt:
            modifier.set(IMG2VID_VIDEO_NODE, "prompt", prompt)

        outputs = submit_and_wait(
            client, "workflow", workflow_id,
            modifier.to_dict_list(),
            poll_interval, timeout,
        )
        paths = client.download_outputs(outputs, video_dir)
        if paths:
            video_paths.append(paths[0])
            log(f"  -> {paths[0].name}")
        else:
            log("  -> No video output")
            video_paths.append(None)  # type: ignore

    return [p for p in video_paths if p is not None]


# ==================== Step 3: First-to-Last Transitions ====================


def step_first2last(client: RunningHubClient, videos: List[Path],
                    output_dir: Path, poll_interval: float, timeout: float,
                    workflow_id: str) -> List[Path]:
    """Create transition videos between consecutive clips.

    For each adjacent pair (videos[i], videos[i+1]), creates a transition
    using the first frame of videos[i] and the last frame that we'd want
    to be the first frame of videos[i+1].

    Since we don't have actual first/last frames, we use the images that
    generated the videos (which are already in 01_images/ or we skip).
    This step uses the video output files and references them as images
    by extracting frames.
    """
    if len(videos) < 2:
        log("Step 3/4: Less than 2 videos, skipping transitions")
        return []

    section("Step 3/4: First-to-Last Transitions")
    trans_dir = output_dir / "03_transitions"
    trans_dir.mkdir(parents=True, exist_ok=True)
    transition_paths: List[Path] = []

    for i in range(len(videos) - 1):
        # Extract the last frame of the current video as an image
        current_video = videos[i]
        if not current_video:
            continue

        log(f"[{i + 1}/{len(videos) - 1}] Creating transition between clip {i + 1} and {i + 2}")

        # Extract last frame of current video
        last_frame = trans_dir / f"frame_last_{i + 1}.png"
        _extract_frame(str(current_video), str(last_frame), "last")

        # Extract first frame of next video
        next_video = videos[i + 1]
        if not next_video:
            continue
        first_frame = trans_dir / f"frame_first_{i + 2}.png"
        _extract_frame(str(next_video), str(first_frame), "first")

        if not last_frame.exists() or not first_frame.exists():
            log("  Skipping transition: could not extract frames")
            continue

        # Upload frames
        f2_uploaded = client.upload_image(str(last_frame))
        l2_uploaded = client.upload_image(str(first_frame))

        # Submit first2last workflow
        from runninghub_sdk import modify_nodes
        modifier = modify_nodes()
        modifier.image(F2L_FIRST_FRAME_NODE, f2_uploaded["fileName"])
        modifier.image(F2L_LAST_FRAME_NODE, l2_uploaded["fileName"])
        modifier.set("30", "positive_prompt", "smooth transition, seamless")

        outputs = submit_and_wait(
            client, "workflow", workflow_id,
            modifier.to_dict_list(),
            poll_interval, timeout,
        )
        paths = client.download_outputs(outputs, trans_dir)
        if paths:
            transition_paths.append(paths[0])
            log(f"  -> {paths[0].name}")
        else:
            log("  -> No transition output")

    return transition_paths


def _extract_frame(video_path: str, output_path: str, position: str = "first") -> None:
    """Extract first or last frame from a video file."""
    import subprocess
    try:
        if position == "last":
            # Get duration first
            dur_cmd = [
                "ffprobe", "-v", "error", "-show_entries",
                "format=duration", "-of", "default=noprint_wrappers=1:nokey=1",
                video_path,
            ]
            result = subprocess.run(dur_cmd, capture_output=True, text=True, timeout=30)
            duration = float(result.stdout.strip()) if result.stdout else 0
            seek = max(0, duration - 0.1)
        else:
            seek = 0

        cmd = [
            "ffmpeg", "-y",
            "-ss", str(seek),
            "-i", video_path,
            "-vframes", "1",
            "-q:v", "2",
            output_path,
        ]
        subprocess.run(cmd, capture_output=True, timeout=30, check=True)
    except Exception:
        pass  # best-effort frame extraction


# ==================== Step 4: Merge ====================


def step_merge(videos: List[Path], transitions: List[Path],
               output_dir: Path, title: str) -> Path | None:
    """Merge all video clips and transitions into one final video."""
    section("Step 4/4: Merge Videos")

    if not videos:
        log("No videos to merge")
        return None

    # Build interleaved list: video[0], transition[0], video[1], transition[1], ...
    all_clips: List[Path] = []
    for i, v in enumerate(videos):
        all_clips.append(v)
        if i < len(transitions):
            all_clips.append(transitions[i])

    log(f"Merging {len(all_clips)} clips into final video...")

    # Create ffmpeg concat file
    safe_title = "".join(c if c.isalnum() or c in " _-" else "_" for c in title).strip()
    safe_title = safe_title or "output"
    output_path = output_dir / f"{safe_title}.mp4"

    # Write concat list
    concat_file = output_dir / "concat_list.txt"
    with open(concat_file, "w") as f:
        for clip in all_clips:
            if clip and clip.exists():
                f.write(f"file '{clip.resolve()}'\n")

    import subprocess
    cmd = [
        "ffmpeg", "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", str(concat_file),
        "-c", "copy",
        str(output_path),
    ]

    log("Running: ffmpeg concat...")
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=3600)
    if result.returncode != 0:
        log("Merge failed (maybe codec mismatch), trying re-encode...")
        # Fallback: re-encode for compatibility
        cmd = [
            "ffmpeg", "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", str(concat_file),
            "-c:v", "libx264",
            "-preset", "medium",
            "-crf", "22",
            "-c:a", "aac",
            str(output_path),
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=3600)
        if result.returncode != 0:
            log(f"Merge error: {result.stderr[-200:]}")
            return None

    if output_path.exists():
        size = output_path.stat().st_size
        log(f"  -> {output_path} ({size / 1024 / 1024:.1f} MB)")
        return output_path
    return None


# ==================== Main entry point ====================


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    config = load_config(args.config)
    scenes: List[Dict[str, Any]] = config["scenes"]
    title = config.get("title", "video_pipeline")

    bootstrap_env()
    api_key = resolve_api_key(args.api_key)

    # Resolve workflow IDs from env or defaults
    txt2img_wf = resolve_workflow_id(args.txt2img_workflow, DEFAULT_TXT2IMG_WORKFLOW)
    img2vid_wf = resolve_workflow_id(args.img2vid_workflow, DEFAULT_IMG2VID_WORKFLOW)
    f2l_wf = resolve_workflow_id(args.first2last_workflow, DEFAULT_FIRST2LAST_WORKFLOW)

    output_dir = Path(args.output_dir).expanduser().resolve() if args.output_dir \
        else make_output_dir("", "pipeline")

    # Print pipeline plan
    section("Pipeline Plan")
    log(f"Title:      {title}")
    log(f"Scenes:     {len(scenes)}")
    log(f"Output:     {output_dir}")
    log("Steps:")
    log(f"  1. Text-to-Image:      {'SKIP' if args.skip_txt2img else 'ENABLED'}")
    log(f"  2. Image-to-Video:     {'SKIP' if args.skip_img2vid else 'ENABLED'}")
    log(f"  3. First-to-Last:      {'SKIP' if args.skip_transitions else 'ENABLED'}")
    log(f"  4. Merge:              {'SKIP' if args.skip_merge else 'ENABLED'}")

    for i, scene in enumerate(scenes, 1):
        prompt = scene.get("prompt", scene.get("image", "(image only)"))
        duration = scene.get("duration", "auto")
        log(f"  Scene {i}: [{duration}s] {prompt[:60]}")

    if args.dry_run:
        log("\nDry run mode. Set RUNNINGHUB_API_KEY and remove --dry-run to execute.")
        return 0

    log("\nStarting pipeline execution...")

    try:
        with RunningHubClient(api_key=api_key) as client:
            images: List[Path] = []

            # Step 1: Text-to-Image
            if not args.skip_txt2img:
                images = step_txt2img(client, scenes, output_dir,
                                      args.poll_interval, args.timeout, txt2img_wf)
            else:
                # Use existing images from config
                images = []
                for scene in scenes:
                    if scene.get("image"):
                        img_path = Path(scene["image"]).expanduser().resolve()
                        images.append(img_path if img_path.exists() else None)  # type: ignore
                    else:
                        images.append(None)  # type: ignore
                images = [p for p in images if p is not None]

            # Step 2: Image-to-Video
            videos: List[Path] = []
            if not args.skip_img2vid and images:
                videos = step_img2vid(client, images, scenes, output_dir,
                                      args.poll_interval, args.timeout, img2vid_wf)
            elif not args.skip_img2vid:
                log("Warning: No images available for video generation")
            else:
                log("Image-to-Video skipped by user")

            # Step 3: First-to-Last Transitions
            transitions: List[Path] = []
            if not args.skip_transitions and videos:
                transitions = step_first2last(client, videos, output_dir,
                                              args.poll_interval, args.timeout, f2l_wf)
            elif not args.skip_transitions:
                log("Warning: No videos available for transitions")

            # Step 4: Merge
            final_video: Path | None = None
            if not args.skip_merge and videos:
                final_video = step_merge(videos, transitions, output_dir, title)
            elif not args.skip_merge:
                log("Warning: No videos available for merging")

    except Exception as e:
        print(f"\nPipeline error: {e}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\nPipeline interrupted by user.", file=sys.stderr)
        return 1

    # Summary
    section("Pipeline Complete")
    log(f"Output directory: {output_dir}")
    if final_video:
        log(f"Final video: {final_video}")
    log("Intermediate files saved in output directory.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
