"""CLI tool: Merge multiple videos into one using ffmpeg.

Supports direct concatenation of same-codec videos and crossfade transitions.

Usage:
    rh-merge --input video1.mp4 video2.mp4 --output merged.mp4
    rh-merge --input scene1.mp4 scene2.mp4 scene3.mp4 --output final.mp4 --transition crossfade
    rh-merge --file-list videos.txt --output merged.mp4

Environment variables:
    None required (local ffmpeg tool)
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import List


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="rh-merge",
        description="Merge multiple video files into one using ffmpeg",
        epilog="Examples:\n"
        "  rh-merge -i clip1.mp4 clip2.mp4 -o merged.mp4\n"
        "  rh-merge -i intro.mp4 scene.mp4 outro.mp4 -o final.mp4 --transition crossfade\n"
        "  rh-merge -f videos.txt -o merged.mp4",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("--input", "-i", nargs="*", default=[],
                   help="Input video files to merge")
    p.add_argument("--file-list", "-f",
                   help="Text file with one video path per line")
    p.add_argument("--output", "-o", default="merged.mp4",
                   help="Output video path (default: merged.mp4)")
    p.add_argument("--transition", choices=["none", "crossfade"], default="none",
                   help="Transition effect between clips (default: none = concat)")
    p.add_argument("--transition-duration", type=float, default=0.5,
                   help="Crossfade duration in seconds (default: 0.5)")
    p.add_argument("--keep-temp", action="store_true",
                   help="Keep temporary files for debugging")
    return p


def check_ffmpeg() -> None:
    try:
        subprocess.run(
            ["ffmpeg", "-version"],
            capture_output=True,
            check=True,
        )
    except (FileNotFoundError, subprocess.CalledProcessError):
        print("Error: ffmpeg not found. Install ffmpeg to use rh-merge.", file=sys.stderr)
        print("  macOS: brew install ffmpeg", file=sys.stderr)
        print("  Ubuntu/Debian: sudo apt install ffmpeg", file=sys.stderr)
        print("  Windows: choco install ffmpeg", file=sys.stderr)
        sys.exit(1)


def resolve_inputs(args: argparse.Namespace) -> List[Path]:
    paths: List[Path] = []
    if args.file_list:
        file_list_path = Path(args.file_list)
        if not file_list_path.exists():
            print(f"Error: File list not found: {file_list_path}", file=sys.stderr)
            sys.exit(1)
        with open(file_list_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    p = Path(line)
                    if not p.is_absolute():
                        p = file_list_path.parent / p
                    paths.append(p.resolve())
    if args.input:
        paths.extend(Path(p).expanduser().resolve() for p in args.input)

    if not paths:
        print("Error: No input files specified. Use --input or --file-list.", file=sys.stderr)
        sys.exit(1)

    for p in paths:
        if not p.exists():
            print(f"Error: Input file not found: {p}", file=sys.stderr)
            sys.exit(1)

    return paths


def merge_concat(inputs: List[Path], output: Path) -> None:
    """Merge with concat demuxer (fast, no re-encode, same codec required)."""
    print("[rh-merge] Using concat demuxer (fast mode)")

    filelist = tempfile.NamedTemporaryFile(
        mode="w", suffix=".txt", delete=False, prefix="rh_merge_"
    )
    try:
        for p in inputs:
            filelist.write(f"file '{p}'\n")
        filelist.close()

        cmd = [
            "ffmpeg", "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", filelist.name,
            "-c", "copy",
            str(output),
        ]
        print(f"[rh-merge] Running: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print("[rh-merge] Concat failed, stderr:", file=sys.stderr)
            print(result.stderr, file=sys.stderr)
            sys.exit(1)
    finally:
        Path(filelist.name).unlink(missing_ok=True)


def merge_crossfade(inputs: List[Path], output: Path, duration: float) -> None:
    """Merge with crossfade transitions (re-encodes, works across codecs)."""
    print(f"[rh-merge] Using crossfade transitions ({duration}s fade)")

    # Build the filter_complex for crossfading multiple inputs
    # Uses the ffmpeg crossfade filter: [0][1]crossfade=d=duration[tmp1];[tmp1][2]crossfade...
    filter_parts: List[str] = []
    for i in range(len(inputs) - 1):
        if i == 0:
            filter_parts.append(f"[0:v][1:v]crossfade=d={duration}[f{i}]")
        else:
            filter_parts.append(f"[f{i-1}][{i+1}:v]crossfade=d={duration}[f{i}]")

    filter_complex = ";".join(filter_parts)

    concat_inputs: List[str] = []
    for p in inputs:
        concat_inputs.extend(["-i", str(p)])

    cmd = [
        "ffmpeg", "-y",
        *concat_inputs,
        "-filter_complex", filter_complex,
        "-map", f"[f{len(inputs) - 2}]",
        str(output),
    ]
    print("[rh-merge] Running ffmpeg with crossfade...")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print("[rh-merge] Crossfade failed, stderr:", file=sys.stderr)
        # Show last 20 lines of stderr
        lines = result.stderr.strip().split("\n")
        for line in lines[-20:]:
            print(f"  {line}", file=sys.stderr)
        sys.exit(1)


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    check_ffmpeg()
    inputs = resolve_inputs(args)

    output = Path(args.output).expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)

    print(f"[rh-merge] Merging {len(inputs)} videos:")
    for i, p in enumerate(inputs, 1):
        size = p.stat().st_size
        size_str = f"{size / 1024 / 1024:.1f} MB" if size > 1024 * 1024 else f"{size / 1024:.0f} KB"
        print(f"  [{i}] {p.name} ({size_str})")

    if args.transition == "crossfade":
        merge_crossfade(inputs, output, args.transition_duration)
    else:
        merge_concat(inputs, output)

    if output.exists():
        size = output.stat().st_size
        size_str = f"{size / 1024 / 1024:.1f} MB" if size > 1024 * 1024 else f"{size / 1024:.0f} KB"
        print(f"\n[rh-merge] Done! Merged video: {output} ({size_str})")
    else:
        print("\n[rh-merge] Error: Output file was not created.", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
